from redis.asyncio import Redis

from app.core.config import settings


class RefreshTokenStore:
    """Redis-backed allowlist for issued refresh-token ids."""

    def __init__(self) -> None:
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._client

    @staticmethod
    def _key(jti: str) -> str:
        return f"refresh_token:{jti}"

    @property
    def _ttl_seconds(self) -> int:
        return settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    async def store(self, jti: str, user_id: int) -> None:
        await self.client.set(self._key(jti), str(user_id), ex=self._ttl_seconds)

    async def consume(self, jti: str, user_id: int) -> bool:
        stored_user_id = await self.client.getdel(self._key(jti))
        return stored_user_id == str(user_id)


refresh_token_store = RefreshTokenStore()
