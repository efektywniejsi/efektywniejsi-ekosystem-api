"""Implementation packages routes — assembled from sub-modules."""

from fastapi import APIRouter

from app.implementation_packages.routes.enrollments import router as enrollments_router
from app.implementation_packages.routes.modules import router as modules_router
from app.implementation_packages.routes.packages import router as packages_router
from app.implementation_packages.routes.processes import router as processes_router
from app.implementation_packages.routes.sales_page import router as sales_page_router
from app.implementation_packages.routes.thumbnails import router as thumbnails_router

router = APIRouter(prefix="/implementation-packages")

router.include_router(packages_router)
router.include_router(processes_router)
router.include_router(modules_router)
router.include_router(enrollments_router)
router.include_router(thumbnails_router)
router.include_router(sales_page_router)
