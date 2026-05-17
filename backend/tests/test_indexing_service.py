"""TASK-084: backend-managed RAG indexing scheduling tests."""
import json
from uuid import uuid4

import pytest
from redis.exceptions import RedisError

from rag import indexing_service


@pytest.fixture(autouse=True)
def clean_database():
    yield


class FakeRedis:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.items: list[tuple[str, str]] = []

    async def rpush(self, key: str, value: str) -> None:
        if self.fail:
            raise RedisError("offline")
        self.items.append((key, value))

    async def ping(self) -> bool:
        if self.fail:
            raise RedisError("offline")
        return True


async def test_enqueue_indexing_job_writes_redis_payload() -> None:
    redis = FakeRedis()
    tenant_id = uuid4()
    collection_id = uuid4()
    document_id = uuid4()

    queued = await indexing_service.enqueue_indexing_job(
        tenant_id=tenant_id,
        collection_id=collection_id,
        document_id=document_id,
        redis=redis,
    )

    assert queued is True
    assert redis.items[0][0] == "rag:indexing_queue"
    payload = json.loads(redis.items[0][1])
    assert payload == {
        "document_id": str(document_id),
        "tenant_id": str(tenant_id),
        "collection_id": str(collection_id),
    }


async def test_enqueue_indexing_job_preserves_delete_action() -> None:
    redis = FakeRedis()
    tenant_id = uuid4()
    collection_id = uuid4()
    document_id = uuid4()

    queued = await indexing_service.enqueue_indexing_job(
        tenant_id=tenant_id,
        collection_id=collection_id,
        document_id=document_id,
        action="delete",
        redis=redis,
    )

    assert queued is True
    payload = json.loads(redis.items[0][1])
    assert payload["action"] == "delete"


async def test_schedule_indexing_job_falls_back_to_inline(monkeypatch) -> None:
    called: dict[str, object] = {}

    class FakeTask:
        def add_done_callback(self, callback) -> None:
            called["callback"] = callback

    def fake_schedule_inline_indexing_job(**kwargs):
        called.update(kwargs)
        return FakeTask()

    monkeypatch.setattr(
        indexing_service,
        "schedule_inline_indexing_job",
        fake_schedule_inline_indexing_job,
    )

    tenant_id = uuid4()
    collection_id = uuid4()
    document_id = uuid4()
    await indexing_service.schedule_indexing_job(
        tenant_id=tenant_id,
        collection_id=collection_id,
        document_id=document_id,
        redis=FakeRedis(fail=True),
    )

    assert called["tenant_id"] == tenant_id
    assert called["collection_id"] == collection_id
    assert called["document_id"] == document_id
    assert called["action"] == "index"
    assert "callback" in called


async def test_consumer_handle_does_not_start_when_redis_is_unavailable() -> None:
    handle = indexing_service.IndexingConsumerHandle(redis=FakeRedis(fail=True))

    started = await handle.start()

    assert started is False
    assert handle._task is None
