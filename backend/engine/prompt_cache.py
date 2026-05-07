from __future__ import annotations

from uuid import UUID

from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncConnection

from app.cache import redis_client
from engine.prompt_schema import SystemPrompt


class PromptCache:
    ttl_seconds = 600

    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def get(self, *, tenant_id: UUID, instance_id: UUID) -> SystemPrompt | None:
        key = self._key(tenant_id, instance_id)
        try:
            cached = await redis_client.get(key)
        except (RedisError, RuntimeError):
            cached = None

        if cached:
            try:
                return SystemPrompt.model_validate_json(cached)
            except Exception:
                return None
        return None

    async def set(self, *, tenant_id: UUID, instance_id: UUID, prompt: SystemPrompt) -> None:
        key = self._key(tenant_id, instance_id)
        try:
            await redis_client.setex(key, self.ttl_seconds, prompt.model_dump_json())
        except (RedisError, RuntimeError):
            pass

    async def invalidate(self, *, tenant_id: UUID, instance_id: UUID) -> None:
        try:
            await redis_client.delete(self._key(tenant_id, instance_id))
        except (RedisError, RuntimeError):
            pass

    @staticmethod
    def _key(tenant_id: UUID, instance_id: UUID) -> str:
        return f"tenant:{tenant_id}:instance:{instance_id}:system_prompt"
