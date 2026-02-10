from app.integrations.routes.admin_integrations import router as admin_router
from app.integrations.routes.integrations import router as public_router
from app.integrations.routes.proposals import router as proposals_router

__all__ = ["public_router", "admin_router", "proposals_router"]
