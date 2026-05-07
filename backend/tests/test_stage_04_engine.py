from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import api.v1.agent as agent_api
from app.main import app
from app.schemas import ChatEvent
from app.security import create_access_token
from database.connection import TenantContext, tenant_connection
from engine.bootstrap import AgentInstanceNotFound, RunBootstrap
from engine.executor import AgentExecutor
from engine.llm_client import LLMProviderError
from engine.session_lock import SessionLock, SessionLockConflict


async def test_run_bootstrap_loads_instance_and_active_capabilities(db_connection: psycopg.Connection) -> None:
    setup = _seed_engine_tenant(db_connection, uuid4().hex)
    _seed_linked_agent(db_connection, setup, "handoff_billing")

    async with tenant_connection(TenantContext(tenant_id=setup["tenant_id"])) as connection:
        state = await RunBootstrap(connection).prepare(
            tenant_id=setup["tenant_id"],
            instance_id=setup["instance_id"],
            session_id=uuid4(),
            channel="api",
        )

    assert state["tenant_id"] == str(setup["tenant_id"])
    assert state["instance_id"] == str(setup["instance_id"])
    assert state["available_skills"] == [setup["skill_slug"]]
    assert state["available_tools"] == [setup["tool_slug"]]
    assert state["linked_agents"][0]["transfer_tool_name"] == "handoff_billing"
    assert state["tool_schemas"][-1]["name"] == "handoff_billing"
    assert "secret_ref" not in str(state)


async def test_run_bootstrap_rejects_instance_from_other_tenant(db_connection: psycopg.Connection) -> None:
    tenant_a = _seed_engine_tenant(db_connection, f"{uuid4().hex}a")
    tenant_b = _seed_engine_tenant(db_connection, f"{uuid4().hex}b")

    async with tenant_connection(TenantContext(tenant_id=tenant_a["tenant_id"])) as connection:
        try:
            await RunBootstrap(connection).prepare(
                tenant_id=tenant_a["tenant_id"],
                instance_id=tenant_b["instance_id"],
                session_id=uuid4(),
                channel="api",
            )
        except AgentInstanceNotFound:
            rejected = True
        else:
            rejected = False

    assert rejected is True


async def test_session_lock_acquire_conflict_and_safe_release() -> None:
    redis = _FakeRedis()
    lock = SessionLock(redis)
    tenant_id = uuid4()
    session_id = uuid4()

    await lock.acquire(tenant_id=tenant_id, session_id=session_id, run_id="run-1")
    try:
        await lock.acquire(tenant_id=tenant_id, session_id=session_id, run_id="run-2")
    except SessionLockConflict:
        conflicted = True
    else:
        conflicted = False

    await lock.release(tenant_id=tenant_id, session_id=session_id, run_id="wrong-run")
    assert redis.values[SessionLock._key(tenant_id, session_id)] == "run-1"

    assert await lock.renew(tenant_id=tenant_id, session_id=session_id, run_id="wrong-run") is False
    assert await lock.renew(tenant_id=tenant_id, session_id=session_id, run_id="run-1") is True
    assert redis.expires[SessionLock._key(tenant_id, session_id)] == lock.ttl_seconds

    await lock.release(tenant_id=tenant_id, session_id=session_id, run_id="run-1")

    assert conflicted is True
    assert SessionLock._key(tenant_id, session_id) not in redis.values


async def test_agent_executor_persists_messages_in_order(db_connection: psycopg.Connection, monkeypatch) -> None:
    import engine.base_graph as bg

    async def fake_llm(state):
        return {"final_response": "Fake LLM response."}

    monkeypatch.setattr(bg, "llm_node", fake_llm)

    setup = _seed_engine_tenant(db_connection, uuid4().hex)

    async with tenant_connection(TenantContext(tenant_id=setup["tenant_id"])) as connection:
        executor = AgentExecutor(connection, lock=SessionLock(_FakeRedis()))
        events = await executor.run(
            tenant_id=setup["tenant_id"],
            instance_id=setup["instance_id"],
            message="hello",
            channel="api",
            user_ref=str(setup["user_id"]),
        )
        rows = (
            await connection.execute(
                text(
                    """
                    SELECT role, sequence_no, content
                    FROM messages
                    WHERE tenant_id = :tenant_id AND session_id = :session_id
                    ORDER BY sequence_no
                    """
                ),
                {"tenant_id": setup["tenant_id"], "session_id": events[0].session_id},
            )
        ).fetchall()

    assert [event.event for event in events] == ["message.persisted", "assistant.delta", "run.completed"]
    assert [(row.role, row.sequence_no) for row in rows] == [("user", 1), ("assistant", 2)]
    assert rows[1].content == "Fake LLM response."


async def test_agent_executor_releases_lock_on_error(db_connection: psycopg.Connection, monkeypatch) -> None:
    setup = _seed_engine_tenant(db_connection, uuid4().hex)
    redis = _FakeRedis()

    async def fail_prepare(self, **_kwargs):
        raise AgentInstanceNotFound("boom")

    monkeypatch.setattr(RunBootstrap, "prepare", fail_prepare)

    async with tenant_connection(TenantContext(tenant_id=setup["tenant_id"])) as connection:
        executor = AgentExecutor(connection, lock=SessionLock(redis))
        try:
            await executor.run(
                tenant_id=setup["tenant_id"],
                instance_id=setup["instance_id"],
                message="hello",
                channel="api",
                user_ref=str(setup["user_id"]),
            )
        except AgentInstanceNotFound:
            raised = True
        else:
            raised = False

    assert raised is True
    assert redis.values == {}


async def test_chat_endpoint_streams_sse_and_conflict(db_connection: psycopg.Connection, monkeypatch) -> None:
    setup = _seed_engine_tenant(db_connection, uuid4().hex)
    token = create_access_token(user_id=setup["user_id"], email=setup["email"])
    run = _FakeRun([ChatEvent(event="run.completed", session_id=uuid4(), sequence_no=1)])

    class FakeExecutor:
        def __init__(self, _connection) -> None:
            pass

        async def start_stream(self, **_kwargs):
            return run

        @staticmethod
        def encode_sse(event: ChatEvent) -> str:
            return AgentExecutor.encode_sse(event)

    monkeypatch.setattr(agent_api, "AgentExecutor", FakeExecutor)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/agent/instances/{setup['instance_id']}/chat",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"message": "hello"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "run.completed" in response.text
    assert run.closed is True

    class ConflictExecutor(FakeExecutor):
        async def start_stream(self, **_kwargs):
            raise SessionLockConflict("busy")

    monkeypatch.setattr(agent_api, "AgentExecutor", ConflictExecutor)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        conflict_response = await client.post(
            f"/api/v1/agent/instances/{setup['instance_id']}/chat",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"message": "hello"},
        )

    assert conflict_response.status_code == 409

    class ProviderErrorExecutor(FakeExecutor):
        async def start_stream(self, **_kwargs):
            raise LLMProviderError("provider failed")

    monkeypatch.setattr(agent_api, "AgentExecutor", ProviderErrorExecutor)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        provider_response = await client.post(
            f"/api/v1/agent/instances/{setup['instance_id']}/chat",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"message": "hello"},
        )

    assert provider_response.status_code == 502


async def test_chat_endpoint_cancels_stream_on_disconnect(db_connection: psycopg.Connection, monkeypatch) -> None:
    setup = _seed_engine_tenant(db_connection, uuid4().hex)
    run = _FakeRun(
        [
            ChatEvent(event="message.persisted", session_id=uuid4(), sequence_no=1),
            ChatEvent(event="run.completed", session_id=uuid4(), sequence_no=2),
        ]
    )

    class DisconnectingRequest:
        async def is_disconnected(self):
            return True

    class FakeExecutor:
        def __init__(self, _connection) -> None:
            pass

        async def start_stream(self, **_kwargs):
            return run

        @staticmethod
        def encode_sse(event: ChatEvent) -> str:
            return AgentExecutor.encode_sse(event)

    monkeypatch.setattr(agent_api, "AgentExecutor", FakeExecutor)
    response = await agent_api.chat(
        setup["instance_id"],
        body=agent_api.ChatRequest(message="hello"),
        request=DisconnectingRequest(),
        context=TenantContext(tenant_id=setup["tenant_id"], user_id=setup["user_id"], role="tenant_admin"),
    )
    chunks = [chunk async for chunk in response.body_iterator]

    assert chunks == []
    assert run.cancelled is True
    assert run.closed is True


def _seed_engine_tenant(db_connection: psycopg.Connection, suffix: str) -> dict:
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Engine Tenant') RETURNING id",
            (f"engine-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        email = f"engine-user-{suffix}@example.com"
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Engine User', 'hash', 'active')
            RETURNING id
            """,
            (email,),
        )
        user_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO memberships (user_id, tenant_id, role, status)
            VALUES (%s, %s, 'tenant_admin', 'active')
            """,
            (user_id, tenant_id),
        )
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(tenant_id),))
        cursor.execute(
            """
            INSERT INTO agent_instances (tenant_id, name, core_prompt, created_by, status)
            VALUES (%s, 'Engine Agent', 'You are an engine test agent.', %s, 'active')
            RETURNING id
            """,
            (tenant_id, user_id),
        )
        instance_id = cursor.fetchone()[0]
        skill_slug = f"engine_skill_{suffix}"
        tool_slug = f"engine_tool_{suffix}"
        cursor.execute(
            """
            INSERT INTO skill_definitions
              (slug, name, prompt_block, tool_schema, executor, input_schema, output_schema, is_active)
            VALUES (%s, 'Engine Skill', 'Use engine skill.', '{"name": "engine_skill"}',
                    'skills.engine', '{}', '{}', true)
            RETURNING id
            """,
            (skill_slug,),
        )
        skill_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO tool_definitions (slug, name, prompt_block, schema, executor, is_builtin)
            VALUES (%s, 'Engine Tool', 'Use engine tool.', '{"name": "engine_tool"}', 'tools.engine', true)
            RETURNING id
            """,
            (tool_slug,),
        )
        tool_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO agent_instance_skills (tenant_id, instance_id, skill_id, is_enabled, config)
            VALUES (%s, %s, %s, true, '{}')
            """,
            (tenant_id, instance_id, skill_id),
        )
        cursor.execute(
            """
            INSERT INTO agent_instance_tools (tenant_id, instance_id, tool_id, is_enabled, config)
            VALUES (%s, %s, %s, true, '{}')
            """,
            (tenant_id, instance_id, tool_id),
        )
        cursor.execute("RESET app.current_tenant_id")
        db_connection.commit()

    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "email": email,
        "instance_id": instance_id,
        "skill_slug": skill_slug,
        "tool_slug": tool_slug,
    }


def _seed_linked_agent(db_connection: psycopg.Connection, setup: dict, transfer_tool_name: str) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            """
            INSERT INTO agent_instances (tenant_id, name, core_prompt, created_by, status)
            VALUES (%s, 'Billing Agent', 'You handle billing transfers.', %s, 'active')
            RETURNING id
            """,
            (setup["tenant_id"], setup["user_id"]),
        )
        target_instance_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO agent_links
              (tenant_id, source_instance_id, target_instance_id, transfer_tool_name, trigger_description)
            VALUES (%s, %s, %s, %s, 'Transfer when billing context is required.')
            """,
            (setup["tenant_id"], setup["instance_id"], target_instance_id, transfer_tool_name),
        )
        cursor.execute("RESET app.current_tenant_id")
        db_connection.commit()


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expires: dict[str, int] = {}

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        if ex is not None:
            self.expires[key] = ex
        return True

    async def eval(self, script: str, _key_count: int, key: str, run_id: str, ttl: int | None = None):
        if "EXPIRE" in script and self.values.get(key) == run_id and ttl is not None:
            self.expires[key] = ttl
            return 1
        if "DEL" in script and self.values.get(key) == run_id:
            self.values.pop(key, None)
            self.expires.pop(key, None)
            return 1
        return 0


class _FakeRun:
    def __init__(self, events: list[ChatEvent]) -> None:
        self._events = events
        self.cancelled = False
        self.closed = False

    async def events(self):
        for event in self._events:
            yield event

    async def cancel(self) -> None:
        self.cancelled = True
        await self.close()

    async def close(self) -> None:
        self.closed = True
