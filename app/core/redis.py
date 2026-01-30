import json
from datetime import datetime
from typing import Any

from redis.asyncio import Redis

redis_client: Redis | None = None


async def get_redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client


async def store_refresh_token(token_hash: str, user_id: str, ttl_seconds: int) -> None:
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    key = f"refresh_token:{token_hash}"
    value = json.dumps({"user_id": user_id, "created_at": datetime.utcnow().isoformat()})
    await redis_client.setex(key, ttl_seconds, value)


async def get_refresh_token(token_hash: str) -> dict[Any, Any] | None:
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    key = f"refresh_token:{token_hash}"
    data = await redis_client.get(key)
    if data:
        result: dict[Any, Any] = json.loads(data)
        return result
    return None


async def revoke_refresh_token(token_hash: str) -> None:
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    key = f"refresh_token:{token_hash}"
    await redis_client.delete(key)
