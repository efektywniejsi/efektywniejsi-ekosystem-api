"""
Pydantic schemas for packages.
"""

import json
import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.datetime_utils import UTCDatetime


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
    is_published: bool = True
    tools: list[str] = Field(default_factory=list)
    created_at: UTCDatetime | None = None

    class Config:
        from_attributes = True

    @field_validator("tools", mode="before")
    @classmethod
    def parse_tools_json(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            parsed: list[str] = json.loads(v)
            return parsed
        return list(v)


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
    sales_page_sections: dict[str, Any] | None = None
    created_at: UTCDatetime
    updated_at: UTCDatetime

    class Config:
        from_attributes = True

    @field_validator("tools", mode="before")
    @classmethod
    def parse_tools_json(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            parsed: list[str] = json.loads(v)
            return parsed
        return list(v)


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
    is_published: bool | None = None
    package_ids: list[str] | None = None  # Update child packages if is_bundle=True
