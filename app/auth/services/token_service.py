from app.core import redis as redis_module
from app.core import security
from app.core.config import settings


class TokenService:
    """Service for managing refresh tokens in Redis"""

    async def store_refresh_token(self, token: str, user_id: str) -> None:
        """Store refresh token hash in Redis with TTL"""
        token_hash = security.hash_token(token)
        ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        await redis_module.store_refresh_token(token_hash, user_id, ttl_seconds)

    async def validate_refresh_token(self, token: str) -> dict | None:
        """Check if refresh token exists in Redis and is not revoked"""
        token_hash = security.hash_token(token)
        return await redis_module.get_refresh_token(token_hash)

    async def revoke_refresh_token(self, token: str) -> None:
        """Revoke refresh token by removing from Redis"""
        token_hash = security.hash_token(token)
        await redis_module.revoke_refresh_token(token_hash)


token_service = TokenService()
