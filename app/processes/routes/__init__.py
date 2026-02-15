from app.processes.routes.admin_processes import router as admin_router
from app.processes.routes.processes import router as public_router

__all__ = ["public_router", "admin_router"]
