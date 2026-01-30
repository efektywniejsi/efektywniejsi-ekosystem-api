import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis

from app.admin.routes import admin_statistics
from app.ai.routes import brand_guidelines as brand_guidelines_routes
from app.ai.routes import sales_page_ai
from app.auth.routes import admin, auth, password
from app.auth.routes import settings as settings_routes
from app.core import redis as redis_module
from app.core.config import settings
from app.courses.routes import (
    admin as courses_admin,
)
from app.courses.routes import (
    admin_enrollments,
    attachments,
    certificates,
    courses,
    enrollment,
    gamification,
    lessons,
    progress,
    sales_page,
    webhooks,
)
from app.notifications.routes import notifications as notifications_routes
from app.packages.routes import (
    bundle_sales_page_router,
    bundles_router,
    checkout_router,
    enrollments_router,
    orders_router,
    packages_router,
    sales_windows_router,
    webhooks_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    print("Connecting to Redis...")
    redis_module.redis_client = Redis.from_url(
        settings.REDIS_URL, decode_responses=True, encoding="utf-8"
    )

    try:
        if redis_module.redis_client:
            await redis_module.redis_client.ping()
            print("✓ Connected to Redis successfully")
    except Exception as e:
        print(f"✗ Failed to connect to Redis: {e}")

    yield

    print("Closing Redis connection...")
    if redis_module.redis_client:
        await redis_module.redis_client.close()
    print("✓ Redis connection closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    description="Backend API for Efektywniejsi Ekosystem with JWT authentication",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files (avatars, etc.)
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["authentication"])
app.include_router(
    password.router, prefix=f"{settings.API_V1_PREFIX}/password", tags=["password-reset"]
)
app.include_router(
    settings_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/settings",
    tags=["settings"],
)
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["admin"])
app.include_router(
    admin_statistics.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["admin-statistics"]
)

app.include_router(courses.router, prefix=settings.API_V1_PREFIX, tags=["courses"])
app.include_router(enrollment.router, prefix=settings.API_V1_PREFIX, tags=["enrollments"])
app.include_router(lessons.router, prefix=settings.API_V1_PREFIX, tags=["lessons"])
app.include_router(progress.router, prefix=settings.API_V1_PREFIX, tags=["progress"])
app.include_router(gamification.router, prefix=settings.API_V1_PREFIX, tags=["gamification"])
app.include_router(attachments.router, prefix=settings.API_V1_PREFIX, tags=["attachments"])
app.include_router(certificates.router, prefix=settings.API_V1_PREFIX, tags=["certificates"])
app.include_router(
    courses_admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["admin-courses"]
)
app.include_router(
    admin_enrollments.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["admin-enrollments"],
)
app.include_router(webhooks.router, prefix=settings.API_V1_PREFIX, tags=["webhooks"])
app.include_router(sales_page.router, prefix=settings.API_V1_PREFIX, tags=["sales-page"])

# Package commerce routes
app.include_router(
    bundle_sales_page_router, prefix=settings.API_V1_PREFIX, tags=["bundle-sales-page"]
)
app.include_router(bundles_router, prefix=settings.API_V1_PREFIX, tags=["bundles"])
app.include_router(packages_router, prefix=settings.API_V1_PREFIX, tags=["packages"])
app.include_router(checkout_router, prefix=settings.API_V1_PREFIX, tags=["checkout"])
app.include_router(webhooks_router, prefix=settings.API_V1_PREFIX, tags=["payment-webhooks"])
app.include_router(enrollments_router, prefix=settings.API_V1_PREFIX, tags=["package-enrollments"])
app.include_router(orders_router, prefix=settings.API_V1_PREFIX, tags=["orders"])
app.include_router(
    sales_windows_router, prefix=f"{settings.API_V1_PREFIX}/sales-windows", tags=["sales-windows"]
)

# Notification routes
app.include_router(
    notifications_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["admin-notifications"],
)

# AI routes
app.include_router(sales_page_ai.router, prefix=settings.API_V1_PREFIX, tags=["ai-sales-page"])
app.include_router(
    brand_guidelines_routes.router, prefix=settings.API_V1_PREFIX, tags=["brand-guidelines"]
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Efektywniejsi Ekosystem Auth API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    redis_status = "unknown"

    try:
        if redis_module.redis_client:
            await redis_module.redis_client.ping()
            redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    return {"status": "healthy" if redis_status == "healthy" else "degraded", "redis": redis_status}
