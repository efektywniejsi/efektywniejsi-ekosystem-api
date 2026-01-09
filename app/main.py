from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.auth.routes import admin, auth, password
from app.core import redis as redis_module
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Connect to Redis
    print("Connecting to Redis...")
    redis_module.redis_client = Redis.from_url(
        settings.REDIS_URL, decode_responses=True, encoding="utf-8"
    )

    # Test Redis connection
    try:
        await redis_module.redis_client.ping()
        print("✓ Connected to Redis successfully")
    except Exception as e:
        print(f"✗ Failed to connect to Redis: {e}")

    yield

    # Shutdown: Close Redis connection
    print("Closing Redis connection...")
    if redis_module.redis_client:
        await redis_module.redis_client.close()
    print("✓ Redis connection closed")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    description="Backend API for Efektywniejsi Ekosystem with JWT authentication",
    version="1.0.0",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["authentication"])
app.include_router(password.router, prefix=f"{settings.API_V1_PREFIX}/password", tags=["password-reset"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["admin"])


# Health check endpoints
@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {"message": "Efektywniejsi Ekosystem Auth API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring"""
    redis_status = "unknown"

    try:
        if redis_module.redis_client:
            await redis_module.redis_client.ping()
            redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    return {"status": "healthy" if redis_status == "healthy" else "degraded", "redis": redis_status}
