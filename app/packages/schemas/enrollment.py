"""
Pydantic schemas for package enrollments.
"""

import uuid

from pydantic import BaseModel

from app.core.datetime_utils import UTCDatetime


class PackageEnrollmentResponse(BaseModel):
    """Package enrollment response schema."""

    id: uuid.UUID
    package_id: uuid.UUID
    enrolled_at: UTCDatetime
    last_accessed_at: UTCDatetime | None

    # Package details (nested)
    package: "PackageEnrollmentPackage"

    class Config:
        from_attributes = True


class PackageEnrollmentPackage(BaseModel):
    """Nested package info for enrollment response."""

    id: uuid.UUID
    slug: str
    title: str
    description: str
    category: str
    difficulty: str
    total_time_saved: str | None

    class Config:
        from_attributes = True
