"""
Database base module - imports all models for Alembic migration detection.

This module imports all SQLAlchemy models to ensure they are registered
with Alembic for automatic migration generation. While the imports appear
unused, they are essential for the migration system to work properly.
"""

from app.ai.models.ai_chat_session import AiChatSession
from app.ai.models.brand_guidelines import BrandGuidelines
from app.auth.models.user import User
from app.courses.models.attachment import Attachment
from app.courses.models.certificate import Certificate
from app.courses.models.course import Course, Lesson, Module
from app.courses.models.enrollment import Enrollment
from app.notifications.models.notification import Notification
from app.packages.models.enrollment import PackageEnrollment
from app.packages.models.order import Order, OrderItem
from app.packages.models.package import Package, PackageBundleItem, PackageProcess

# Export all models for Alembic
__all__ = [
    "AiChatSession",
    "BrandGuidelines",
    "User",
    "Attachment",
    "Certificate",
    "Course",
    "Lesson",
    "Module",
    "Enrollment",
    "PackageEnrollment",
    "Order",
    "OrderItem",
    "Package",
    "PackageBundleItem",
    "PackageProcess",
    "Notification",
]
