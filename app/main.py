import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.admin.routes import admin_statistics
from app.ai.routes import brand_guidelines as brand_guidelines_routes
from app.ai.routes import sales_page_ai
from app.auth.routes import admin, auth, password
from app.auth.routes import settings as settings_routes
from app.community.routes import admin_threads as admin_community_routes
from app.community.routes import thread_attachments as community_attachments_routes
from app.community.routes import threads as community_routes
from app.core import redis as redis_module
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.log_config import RequestLoggingMiddleware, setup_logging
from app.core.rate_limit import limiter
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
    modules,
    progress,
    sales_page,
    webhooks,
)
from app.db.session import SessionLocal
from app.messaging.routes import admin_messages as admin_messages_routes
from app.messaging.routes import messages as messages_routes
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

setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("connecting_to_redis")
    redis_module.redis_client = Redis.from_url(
        settings.REDIS_URL, decode_responses=True, encoding="utf-8"
    )

    try:
        if redis_module.redis_client:
            await redis_module.redis_client.ping()
            logger.info("redis_connected")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))

    yield

    logger.info("closing_redis")
    if redis_module.redis_client:
        await redis_module.redis_client.close()
    logger.info("redis_closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    description="Backend API for Efektywniejsi Ekosystem with JWT authentication",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

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
app.include_router(modules.router, prefix=settings.API_V1_PREFIX, tags=["modules"])
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

app.include_router(
    notifications_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["admin-notifications"],
)

app.include_router(sales_page_ai.router, prefix=settings.API_V1_PREFIX, tags=["ai-sales-page"])
app.include_router(
    brand_guidelines_routes.router, prefix=settings.API_V1_PREFIX, tags=["brand-guidelines"]
)

app.include_router(
    community_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/community",
    tags=["community"],
)
app.include_router(
    community_attachments_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/community",
    tags=["community-attachments"],
)
app.include_router(
    admin_community_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["admin-community"],
)

app.include_router(
    messages_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/messages",
    tags=["messages"],
)
app.include_router(
    admin_messages_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/admin/messages",
    tags=["admin-messages"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Efektywniejsi Ekosystem Auth API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    redis_status = "unknown"
    db_status = "unknown"

    try:
        if redis_module.redis_client:
            await redis_module.redis_client.ping()
            redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_status = "healthy"
        finally:
            db.close()
    except Exception:
        db_status = "unhealthy"

    all_healthy = redis_status == "healthy" and db_status == "healthy"
    overall = "healthy" if all_healthy else "degraded"

    return {"status": overall, "redis": redis_status, "database": db_status}
