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


async def revoke_all_user_tokens(user_id: str) -> int:
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    cursor = 0
    revoked_count = 0
    pattern = "refresh_token:*"

    while True:
        cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)

        for key in keys:
            data = await redis_client.get(key)
            if data:
                token_data = json.loads(data)
                if token_data.get("user_id") == user_id:
                    await redis_client.delete(key)
                    revoked_count += 1

        if cursor == 0:
            break

    return revoked_count
