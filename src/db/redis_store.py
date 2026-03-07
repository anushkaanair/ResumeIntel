"""Redis-backed key-value store for pipeline results, canvas state, and sessions."""

from __future__ import annotations

import json
from typing import Any

import structlog

logger = structlog.get_logger()

_redis_client = None


def get_redis():
    """Return a shared async Redis client, initialised lazily."""
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        from src.config.settings import settings
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def rset(key: str, value: Any, ttl: int | None = None) -> None:
    from src.config.settings import settings
    r = get_redis()
    serialized = json.dumps(value, default=str)
    expire = ttl if ttl is not None else settings.redis_ttl_seconds
    await r.set(key, serialized, ex=expire)


async def rget(key: str) -> Any | None:
    r = get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def rdelete(key: str) -> None:
    r = get_redis()
    await r.delete(key)


async def rpush_list(key: str, item: Any, ttl: int | None = None) -> None:
    """Append item to a Redis list (used for version history)."""
    from src.config.settings import settings
    r = get_redis()
    await r.rpush(key, json.dumps(item, default=str))
    expire = ttl if ttl is not None else settings.redis_ttl_seconds
    await r.expire(key, expire)


async def rget_list(key: str) -> list[Any]:
    r = get_redis()
    items = await r.lrange(key, 0, -1)
    return [json.loads(i) for i in items]


async def rpublish(channel: str, message: dict[str, Any]) -> None:
    """Publish a message to a Redis pub/sub channel."""
    r = get_redis()
    await r.publish(channel, json.dumps(message, default=str))


async def rsubscribe(channel: str):
    """Return a pub/sub object subscribed to the given channel."""
    import redis.asyncio as aioredis
    from src.config.settings import settings
    # pub/sub needs its own connection
    r = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    return pubsub, r
