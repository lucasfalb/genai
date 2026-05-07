from uuid import UUID

from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncConnection

from app.cache import redis_client
from app.schemas import ToolMetadataResponse
from database.repositories.registry import RegistryRepository


class ToolMetadataCache:
    ttl_seconds = 600

    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def get(self, *, tenant_id: UUID, instance_id: UUID) -> ToolMetadataResponse:
        key = self._key(tenant_id, instance_id)
        try:
            cached = await redis_client.get(key)
        except (RedisError, RuntimeError):
            cached = None

        if cached:
            return ToolMetadataResponse.model_validate_json(cached)

        metadata = await RegistryRepository(self.connection).load_metadata(tenant_id=tenant_id, instance_id=instance_id)
        response = ToolMetadataResponse.model_validate(metadata)
        try:
            await redis_client.setex(key, self.ttl_seconds, response.model_dump_json())
        except (RedisError, RuntimeError):
            pass
        return response

    async def invalidate(self, *, tenant_id: UUID, instance_id: UUID) -> None:
        try:
            await redis_client.delete(self._key(tenant_id, instance_id))
        except (RedisError, RuntimeError):
            pass

    @staticmethod
    def _key(tenant_id: UUID, instance_id: UUID) -> str:
        return f"tenant:{tenant_id}:instance:{instance_id}:tool_metadata"
