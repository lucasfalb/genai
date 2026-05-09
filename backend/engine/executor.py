import json
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncConnection

from app.schemas import ChatEvent
from database.repositories.sessions import SessionRepository
from engine.base_graph import create_base_graph
from engine.bootstrap import RunBootstrap
from engine.session_lock import SessionLock


@dataclass
class AgentRunStream:
    repository: SessionRepository
    lock: SessionLock
    tenant_id: UUID
    session_id: UUID
    run_id: str
    response: str
    user_event: ChatEvent
    _closed: bool = field(default=False, init=False)

    async def events(self):
        try:
            yield self.user_event
            assistant_message = await self.repository.append_message(
                tenant_id=self.tenant_id,
                session_id=self.session_id,
                role="assistant",
                content=self.response,
                metadata={"engine": "llm"},
            )
            yield ChatEvent(
                event="assistant.delta",
                session_id=self.session_id,
                sequence_no=assistant_message.sequence_no,
                content=self.response,
            )
            yield ChatEvent(
                event="run.completed",
                session_id=self.session_id,
                sequence_no=assistant_message.sequence_no,
                metadata={"run_id": self.run_id},
            )
        finally:
            await self.close()

    async def cancel(self) -> None:
        await self.close()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self.lock.release(tenant_id=self.tenant_id, session_id=self.session_id, run_id=self.run_id)


class AgentExecutor:
    def __init__(self, connection: AsyncConnection, *, lock: SessionLock | None = None) -> None:
        self.connection = connection
        self.lock = lock or SessionLock()

    async def run(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        message: str,
        session_id: UUID | None = None,
        channel: str = "api",
        user_ref: str | None = None,
        metadata: dict | None = None,
    ) -> list[ChatEvent]:
        run = await self.start_stream(
            tenant_id=tenant_id,
            instance_id=instance_id,
            message=message,
            session_id=session_id,
            channel=channel,
            user_ref=user_ref,
            metadata=metadata,
        )
        return [event async for event in run.events()]

    async def start_stream(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        message: str,
        session_id: UUID | None = None,
        channel: str = "api",
        user_ref: str | None = None,
        metadata: dict | None = None,
    ) -> AgentRunStream:
        repository = SessionRepository(self.connection)
        session = None
        if session_id is not None:
            session = await repository.get_session(tenant_id=tenant_id, session_id=session_id, instance_id=instance_id)
        if session is None:
            session = await repository.create_session(
                tenant_id=tenant_id,
                instance_id=instance_id,
                channel=channel,
                user_ref=user_ref,
                metadata=metadata,
            )

        run_id = str(uuid4())
        await self.lock.acquire(tenant_id=tenant_id, session_id=session.id, run_id=run_id)
        try:
            state = await RunBootstrap(self.connection).prepare(
                tenant_id=tenant_id,
                instance_id=instance_id,
                session_id=session.id,
                channel=channel,
            )
            user_message = await repository.append_message(
                tenant_id=tenant_id,
                session_id=session.id,
                role="user",
                content=message,
                metadata=metadata,
            )
            state["messages"].append({"role": "user", "content": message})

            graph = create_base_graph(connection=self.connection)
            result_state = await graph.ainvoke(state)
            response = result_state.get("final_response") or ""

            return AgentRunStream(
                repository=repository,
                lock=self.lock,
                tenant_id=tenant_id,
                session_id=session.id,
                run_id=run_id,
                response=response,
                user_event=ChatEvent(
                    event="message.persisted",
                    session_id=session.id,
                    sequence_no=user_message.sequence_no,
                ),
            )
        except Exception:
            await self.lock.release(tenant_id=tenant_id, session_id=session.id, run_id=run_id)
            raise

    @staticmethod
    def encode_sse(event: ChatEvent) -> str:
        return f"data: {json.dumps(event.model_dump(mode='json'), separators=(',', ':'))}\n\n"
