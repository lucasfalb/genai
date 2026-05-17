import asyncio
import json
import logging
from contextlib import suppress
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.cache import redis_client
from rag.indexing_worker import IndexingJob, IndexingWorker

logger = logging.getLogger("rag.indexing_service")

INDEXING_QUEUE_KEY = "rag:indexing_queue"


async def enqueue_indexing_job(
    *,
    tenant_id: UUID,
    collection_id: UUID,
    document_id: UUID,
    action: str = "index",
    redis: Redis = redis_client,
) -> bool:
    payload = _job_payload(
        tenant_id=tenant_id,
        collection_id=collection_id,
        document_id=document_id,
        action=action,
    )
    try:
        await redis.rpush(INDEXING_QUEUE_KEY, payload)
    except (RedisError, RuntimeError) as exc:
        logger.warning(
            "Unable to enqueue RAG indexing job | action=%s tenant=%s collection=%s document=%s error=%s",
            action, tenant_id, collection_id, document_id, exc,
        )
        return False
    return True


def schedule_inline_indexing_job(
    *,
    tenant_id: UUID,
    collection_id: UUID,
    document_id: UUID,
    action: str = "index",
    worker: IndexingWorker | None = None,
) -> asyncio.Task[None]:
    job = IndexingJob(
        tenant_id=tenant_id,
        collection_id=collection_id,
        document_id=document_id,
        action=action,
    )
    return asyncio.create_task(_process_inline_job(job=job, worker=worker))


async def schedule_indexing_job(
    *,
    tenant_id: UUID,
    collection_id: UUID,
    document_id: UUID,
    action: str = "index",
    redis: Redis = redis_client,
) -> None:
    queued = await enqueue_indexing_job(
        tenant_id=tenant_id,
        collection_id=collection_id,
        document_id=document_id,
        action=action,
        redis=redis,
    )
    if queued:
        return

    task = schedule_inline_indexing_job(
        tenant_id=tenant_id,
        collection_id=collection_id,
        document_id=document_id,
        action=action,
    )
    task.add_done_callback(_log_background_failure)


async def run_indexing_consumer(redis: Redis = redis_client) -> None:
    logger.info("Backend RAG indexing consumer started | queue=%s", INDEXING_QUEUE_KEY)
    worker: IndexingWorker | None = None
    errors = 0
    while True:
        try:
            if worker is None:
                worker = IndexingWorker()
            item = await redis.blpop(INDEXING_QUEUE_KEY, timeout=5)
            if item is None:
                continue
            _, payload = item
            await worker.process_payload(payload)
            errors = 0
        except asyncio.CancelledError:
            logger.info("Backend RAG indexing consumer stopped")
            raise
        except Exception as exc:
            errors += 1
            logger.exception(
                "Backend RAG indexing consumer failed | errors=%d error=%s",
                errors, exc,
            )
            if errors >= 3:
                raise
            await asyncio.sleep(1)


class IndexingConsumerHandle:
    def __init__(self, *, redis: Redis = redis_client) -> None:
        self.redis = redis
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> bool:
        if self._task is not None and not self._task.done():
            return True
        try:
            await self.redis.ping()
        except (RedisError, RuntimeError) as exc:
            logger.warning(
                "Backend RAG indexing consumer disabled because Redis is unavailable | error=%s",
                exc,
            )
            return False
        self._task = asyncio.create_task(run_indexing_consumer(self.redis))
        self._task.add_done_callback(_log_consumer_failure)
        return True

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None


def _job_payload(
    *,
    tenant_id: UUID,
    collection_id: UUID,
    document_id: UUID,
    action: str,
) -> str:
    payload = {
        "document_id": str(document_id),
        "tenant_id": str(tenant_id),
        "collection_id": str(collection_id),
    }
    if action != "index":
        payload["action"] = action
    return json.dumps(payload)


async def _process_inline_job(*, job: IndexingJob, worker: IndexingWorker | None = None) -> None:
    indexing_worker = worker or IndexingWorker()
    await indexing_worker.process_job(job)


def _log_background_failure(task: asyncio.Task[None]) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Inline RAG indexing job failed")


def _log_consumer_failure(task: asyncio.Task[None]) -> None:
    if task.cancelled():
        return
    try:
        task.result()
    except Exception:
        logger.exception("Backend RAG indexing consumer stopped unexpectedly")
