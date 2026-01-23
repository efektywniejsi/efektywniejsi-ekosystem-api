# Import all models here for Alembic to detect them
from app.auth.models.user import User  # noqa: F401
from app.courses.models.attachment import Attachment  # noqa: F401
from app.courses.models.certificate import Certificate  # noqa: F401
from app.courses.models.course import Course, Lesson, Module  # noqa: F401
from app.courses.models.enrollment import Enrollment  # noqa: F401
from app.packages.models.enrollment import PackageEnrollment  # noqa: F401
from app.packages.models.order import Order, OrderItem  # noqa: F401
from app.packages.models.package import Package, PackageBundleItem, PackageProcess  # noqa: F401
