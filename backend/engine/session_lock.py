from uuid import UUID

from redis.exceptions import RedisError

from app.cache import redis_client


class SessionLockConflict(RuntimeError):
    pass


class SessionLockUnavailable(RuntimeError):
    pass


class SessionLock:
    ttl_seconds = 45

    def __init__(self, redis=redis_client) -> None:
        self.redis = redis

    async def acquire(self, *, tenant_id: UUID, session_id: UUID, run_id: str) -> None:
        try:
            acquired = await self.redis.set(self._key(tenant_id, session_id), run_id, nx=True, ex=self.ttl_seconds)
        except (RedisError, RuntimeError) as exc:
            raise SessionLockUnavailable("Session lock backend unavailable") from exc
        if not acquired:
            raise SessionLockConflict("Session already has an active run")

    async def release(self, *, tenant_id: UUID, session_id: UUID, run_id: str) -> None:
        script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        end
        return 0
        """
        try:
            await self.redis.eval(script, 1, self._key(tenant_id, session_id), run_id)
        except (RedisError, RuntimeError) as exc:
            raise SessionLockUnavailable("Session lock backend unavailable") from exc

    async def renew(self, *, tenant_id: UUID, session_id: UUID, run_id: str) -> bool:
        script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("EXPIRE", KEYS[1], ARGV[2])
        end
        return 0
        """
        try:
            renewed = await self.redis.eval(script, 1, self._key(tenant_id, session_id), run_id, self.ttl_seconds)
        except (RedisError, RuntimeError) as exc:
            raise SessionLockUnavailable("Session lock backend unavailable") from exc
        return bool(renewed)

    @staticmethod
    def _key(tenant_id: UUID, session_id: UUID) -> str:
        return f"session:{tenant_id}:{session_id}:lock"
