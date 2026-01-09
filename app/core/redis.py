import json
from datetime import datetime
from typing import Any

from redis.asyncio import Redis

# Global Redis client instance
redis_client: Redis | None = None


async def get_redis() -> Redis:
    """
    Get the Redis client instance.

    Returns:
        Redis client instance

    Raises:
        RuntimeError: If Redis client is not initialized
    """
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return redis_client


async def store_refresh_token(token_hash: str, user_id: str, ttl_seconds: int) -> None:
    """
    Store a refresh token in Redis with TTL.

    Args:
        token_hash: SHA-256 hash of the refresh token
        user_id: UUID of the user
        ttl_seconds: Time to live in seconds

    Example:
        await store_refresh_token("abc123...", "user-uuid", 604800)
    """
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    key = f"refresh_token:{token_hash}"
    value = json.dumps({"user_id": user_id, "created_at": datetime.utcnow().isoformat()})
    await redis_client.setex(key, ttl_seconds, value)


async def get_refresh_token(token_hash: str) -> dict[Any, Any] | None:
    """
    Retrieve refresh token data from Redis.

    Args:
        token_hash: SHA-256 hash of the refresh token

    Returns:
        Dictionary with user_id and created_at, or None if not found

    Example:
        data = await get_refresh_token("abc123...")
        # Returns: {"user_id": "uuid", "created_at": "2024-01-15T12:00:00"}
    """
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    key = f"refresh_token:{token_hash}"
    data = await redis_client.get(key)
    if data:
        result: dict[Any, Any] = json.loads(data)
        return result
    return None


async def revoke_refresh_token(token_hash: str) -> None:
    """
    Revoke (delete) a refresh token from Redis.
    Used during logout to invalidate the refresh token.

    Args:
        token_hash: SHA-256 hash of the refresh token

    Example:
        await revoke_refresh_token("abc123...")
    """
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    key = f"refresh_token:{token_hash}"
    await redis_client.delete(key)


async def revoke_all_user_tokens(user_id: str) -> int:
    """
    Revoke all refresh tokens for a specific user.
    Useful for "logout from all devices" functionality.

    Args:
        user_id: UUID of the user

    Returns:
        Number of tokens revoked

    Example:
        count = await revoke_all_user_tokens("user-uuid")
    """
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    # Scan for all refresh tokens
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
