"""API test fixtures: an in-memory Redis stand-in and a scripted LLM."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest


class FakeRedis:
    """Just enough of redis.asyncio for the routes under test."""

    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.published: list[tuple[str, str]] = []

    async def set(self, key, value, ex=None):
        self.kv[key] = value

    async def get(self, key):
        return self.kv.get(key)

    async def delete(self, key):
        self.kv.pop(key, None)

    async def publish(self, channel, message):
        self.published.append((channel, message))

    async def rpush(self, key, value):
        self.kv.setdefault(key, "[]")
        items = json.loads(self.kv[key])
        items.append(json.loads(value) if isinstance(value, str) else value)
        self.kv[key] = json.dumps(items)

    async def expire(self, key, ttl):
        return True


@pytest.fixture
def fake_redis():
    r = FakeRedis()
    with patch("src.db.redis_store.get_redis", return_value=r):
        yield r


@pytest.fixture
def scripted_llm():
    """Patch LLMClient everywhere routes construct it; set .generate.return_value per test."""
    llm = AsyncMock()
    llm.generate.return_value = "ok"
    with patch("src.llm.client.LLMClient", return_value=llm):
        yield llm
