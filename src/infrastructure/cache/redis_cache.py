"""Redis缓存服务"""
from typing import Any, Optional
import json
from redis import asyncio as aioredis
from ..config.settings import get_settings

settings = get_settings()


class RedisCache:
    """Redis缓存服务"""

    def __init__(self) -> None:
        self._redis: Optional[aioredis.Redis[str]] = None  # type: ignore[type-arg]

    async def connect(self) -> None:
        """连接Redis"""
        self._redis = await aioredis.from_url(  # type: ignore[no-untyped-call]
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )

    async def disconnect(self) -> None:
        """断开连接"""
        if self._redis:
            await self._redis.aclose()

    async def _ensure_connected(self) -> aioredis.Redis[str]:  # type: ignore[type-arg]
        """确保已连接，返回非空 Redis 实例"""
        if self._redis is None:
            await self.connect()
        assert self._redis is not None
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        redis = await self._ensure_connected()
        value = await redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        redis = await self._ensure_connected()
        effective_ttl: int = ttl if ttl is not None else settings.redis_cache_ttl
        await redis.setex(
            key,
            effective_ttl,
            json.dumps(value)
        )

    async def delete(self, key: str) -> None:
        """删除缓存"""
        redis = await self._ensure_connected()
        await redis.delete(key)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        redis = await self._ensure_connected()
        result = int(await redis.exists(key))
        return result > 0
