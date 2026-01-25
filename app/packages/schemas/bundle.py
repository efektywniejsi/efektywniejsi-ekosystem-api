"""Bundle schemas - marketing-friendly format for bundles."""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BundleListResponse(BaseModel):
    """Bundle response with marketing-friendly field names."""

    id: str
    slug: str
    name: str  # maps from title
    shortDescription: str  # maps from description
    pricing: dict[str, Any]  # {"regular": price, "currency": currency}
    features: list[str]  # parsed from processes
    popular: bool  # maps from is_featured
    badge: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    @classmethod
    def from_orm(cls, package: Any) -> "BundleListResponse":
        """Create BundleListResponse from Package ORM model."""
        # Parse tools from JSON string
        tools = []
        if package.tools:
            try:
                tools = (
                    json.loads(package.tools) if isinstance(package.tools, str) else package.tools
                )
            except (json.JSONDecodeError, TypeError):
                tools = []

        # Build features list from processes (if any)
        features = []
        if hasattr(package, "processes") and package.processes:
            features = [p.name for p in package.processes]

        # If no processes, use tools as features
        if not features and tools:
            features = tools

        # Determine badge based on pricing or other criteria
        badge = None
        if package.original_price and package.original_price > package.price:
            discount = int((1 - package.price / package.original_price) * 100)
            badge = f"-{discount}%"
        elif package.is_featured:
            badge = "Polecane"

        return cls(
            id=str(package.id),
            slug=package.slug,
            name=package.title,  # title -> name
            shortDescription=package.description,  # description -> shortDescription
            pricing={
                "regular": package.price / 100,  # Convert grosz to PLN
                "currency": package.currency,
            },
            features=features,
            popular=package.is_featured,
            badge=badge,
        )


class BundleCourseItemResponse(BaseModel):
    """Bundle course item response."""

    id: str
    course_id: str
    sort_order: int

    @field_validator("id", "course_id", mode="before")
    @classmethod
    def validate_uuid(cls, v: Any) -> str:
        return str(v)

    model_config = ConfigDict(from_attributes=True)


class BundleDetailResponse(BaseModel):
    """Bundle with full content (packages + courses)."""

    id: str
    slug: str
    name: str
    shortDescription: str
    pricing: dict[str, Any]
    popular: bool
    badge: str | None = None

    # Content
    packages: list[Any] = Field(default_factory=list)  # Will be PackageListResponse
    courses: list[Any] = Field(default_factory=list)  # Will be CourseResponse

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v: Any) -> str:
        return str(v)

    model_config = ConfigDict(from_attributes=True)


class BundleCreateRequest(BaseModel):
    """Admin: Create bundle."""

    slug: str
    name: str
    description: str
    category: str
    price: int  # w groszach
    original_price: int | None = None
    currency: str = "PLN"
    difficulty: str
    total_time_saved: str | None = None
    is_featured: bool = False

    # Content IDs
    package_ids: list[str] = Field(default_factory=list)
    course_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_not_empty(self) -> "BundleCreateRequest":
        """Validate that bundle contains at least one package or course."""
        if not self.package_ids and not self.course_ids:
            raise ValueError("Bundle must contain at least one package or course")
        return self


class BundleUpdateRequest(BaseModel):
    """Admin: Update bundle."""

    name: str | None = None
    description: str | None = None
    price: int | None = None
    original_price: int | None = None
    is_featured: bool | None = None
    package_ids: list[str] | None = None
    course_ids: list[str] | None = None
