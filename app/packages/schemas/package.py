"""
Pydantic schemas for packages.
"""

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PackageProcessResponse(BaseModel):
    """Package process response schema."""

    id: uuid.UUID
    name: str
    description: str | None
    sort_order: int

    class Config:
        from_attributes = True


class PackageBundleItemResponse(BaseModel):
    """Bundle item response schema."""

    id: uuid.UUID
    child_package_id: uuid.UUID
    sort_order: int

    class Config:
        from_attributes = True


class PackageListResponse(BaseModel):
    """Package list item response (minimal info for listing)."""

    id: uuid.UUID
    slug: str
    title: str
    description: str
    category: str
    price: int  # In grosz
    original_price: int | None
    currency: str
    difficulty: str
    total_time_saved: str | None
    video_url: str | None
    is_featured: bool
    is_bundle: bool
    tools: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: Any) -> "PackageListResponse":
        """Custom from_orm to parse JSON tools field."""
        # Parse tools JSON string to list
        tools = json.loads(obj.tools) if isinstance(obj.tools, str) else obj.tools  # type: ignore[attr-defined]
        return cls(
            id=obj.id,
            slug=obj.slug,
            title=obj.title,
            description=obj.description,
            category=obj.category,
            price=obj.price,
            original_price=obj.original_price,
            currency=obj.currency,
            difficulty=obj.difficulty,
            total_time_saved=obj.total_time_saved,
            video_url=obj.video_url,
            is_featured=obj.is_featured,
            is_bundle=obj.is_bundle,
            tools=tools,
        )


class PackageDetailResponse(BaseModel):
    """Package detail response (full info including processes)."""

    id: uuid.UUID
    slug: str
    title: str
    description: str
    category: str
    price: int  # In grosz
    original_price: int | None
    currency: str
    difficulty: str
    total_time_saved: str | None
    video_url: str | None
    is_featured: bool
    is_bundle: bool
    tools: list[str] = Field(default_factory=list)
    processes: list[PackageProcessResponse] = Field(default_factory=list)
    bundle_items: list[PackageBundleItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: Any) -> "PackageDetailResponse":
        """Custom from_orm to parse JSON tools field."""
        # Parse tools JSON string to list
        tools = json.loads(obj.tools) if isinstance(obj.tools, str) else obj.tools  # type: ignore[attr-defined]
        return cls(
            id=obj.id,
            slug=obj.slug,
            title=obj.title,
            description=obj.description,
            category=obj.category,
            price=obj.price,
            original_price=obj.original_price,
            currency=obj.currency,
            difficulty=obj.difficulty,
            total_time_saved=obj.total_time_saved,
            video_url=obj.video_url,
            is_featured=obj.is_featured,
            is_bundle=obj.is_bundle,
            tools=tools,
            processes=[PackageProcessResponse.from_orm(p) for p in obj.processes],
            bundle_items=[PackageBundleItemResponse.from_orm(b) for b in obj.bundle_items],
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class PackageWithChildrenResponse(BaseModel):
    """Package with child packages (for bundle display)."""

    id: uuid.UUID
    slug: str
    title: str
    description: str
    category: str
    price: int
    original_price: int | None
    currency: str
    difficulty: str
    total_time_saved: str | None
    tools: list[str] = Field(default_factory=list)
    child_packages: list[PackageListResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PackageCreateRequest(BaseModel):
    """Admin request to create package."""

    slug: str
    title: str
    description: str
    category: str
    price: int  # In grosz
    original_price: int | None = None
    currency: str = "PLN"
    difficulty: str
    total_time_saved: str | None = None
    tools: list[str] = Field(default_factory=list)
    video_url: str | None = None
    is_featured: bool = False
    is_bundle: bool = False
    package_ids: list[str] = Field(default_factory=list)  # Child packages if is_bundle=True


class PackageUpdateRequest(BaseModel):
    """Admin request to update package."""

    title: str | None = None
    description: str | None = None
    category: str | None = None
    price: int | None = None
    original_price: int | None = None
    difficulty: str | None = None
    total_time_saved: str | None = None
    tools: list[str] | None = None
    video_url: str | None = None
    is_featured: bool | None = None
    package_ids: list[str] | None = None  # Update child packages if is_bundle=True
