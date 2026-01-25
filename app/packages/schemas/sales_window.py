"""Pydantic schemas for Sales Window endpoints."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class SalesWindowBase(BaseModel):
    """Base schema for sales window with common fields."""

    id: str
    name: str
    status: Literal["upcoming", "active", "closed"]
    startsAt: datetime = Field(..., validation_alias="starts_at")
    endsAt: datetime = Field(..., validation_alias="ends_at")
    landingPage: dict[str, Any] = Field(..., validation_alias="landing_page_config")
    earlyBird: dict[str, Any] | None = Field(None, validation_alias="early_bird_config")
    bundleIds: list[str] = Field(..., validation_alias="bundle_ids")

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v: Any) -> str:
        """Convert UUID to string."""
        return str(v)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> str:
        """Convert enum to string value before validation."""
        if hasattr(v, "value"):
            return str(v.value)
        return str(v).lower()

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class SalesWindowResponse(SalesWindowBase):
    """Response schema for sales window (includes audit fields)."""

    createdAt: datetime = Field(..., validation_alias="created_at")
    updatedAt: datetime = Field(..., validation_alias="updated_at")
    createdBy: str | None = Field(None, validation_alias="created_by")
    updatedBy: str | None = Field(None, validation_alias="updated_by")

    @field_validator("createdBy", "updatedBy", mode="before")
    @classmethod
    def validate_uuid_fields(cls, v: Any) -> str | None:
        """Convert UUID to string for audit fields."""
        if v is None:
            return None
        return str(v)


class SalesWindowUpdate(BaseModel):
    """Schema for updating a sales window (admin only)."""

    status: Literal["upcoming", "active", "closed"] | None = None
    startsAt: datetime | None = None
    endsAt: datetime | None = None

    @field_validator("endsAt")
    @classmethod
    def validate_ends_at(cls, v: datetime | None, info: ValidationInfo) -> datetime | None:
        """Validate that endsAt is after startsAt."""
        if v is not None and info.data.get("startsAt") is not None:
            starts_at = info.data["startsAt"]
            if v <= starts_at:
                raise ValueError("endsAt must be after startsAt")
        return v


class SalesWindowCreate(BaseModel):
    """Schema for creating a new sales window (admin only)."""

    id: str
    name: str
    status: Literal["upcoming", "active", "closed"] = "upcoming"
    startsAt: datetime
    endsAt: datetime
    landingPage: dict[str, Any]  # {"slug": "...", "title": "...", "subtitle": "...", "hero": {...}}
    earlyBird: dict[str, Any] | None = None
    bundleIds: list[str]

    @field_validator("endsAt")
    @classmethod
    def validate_ends_after_starts(cls, v: datetime, info: ValidationInfo) -> datetime:
        """Validate that endsAt is after startsAt."""
        starts_at = info.data.get("startsAt")
        if starts_at and v <= starts_at:
            raise ValueError("endsAt must be after startsAt")
        return v

    @field_validator("bundleIds")
    @classmethod
    def validate_bundle_ids_not_empty(cls, v: list[str]) -> list[str]:
        """Validate that at least one bundle ID is provided."""
        if not v or len(v) == 0:
            raise ValueError("At least one bundle ID must be provided")
        return v

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class SalesWindowListResponse(BaseModel):
    """Response schema for list of sales windows."""

    salesWindows: list[SalesWindowResponse]


class SalesWindowDetailResponse(BaseModel):
    """Response schema for single sales window."""

    salesWindow: SalesWindowResponse


class SalesWindowUpdateResponse(BaseModel):
    """Response schema for update operation."""

    salesWindow: SalesWindowResponse
    message: str


class ActiveSalesWindowResponse(BaseModel):
    """Response schema for active sales window (public endpoint)."""

    salesWindow: SalesWindowResponse | None = None
