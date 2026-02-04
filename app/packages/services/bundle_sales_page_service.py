"""Service for managing bundle sales page sections."""

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.courses.schemas.sales_page import (
    SECTION_CONFIG_MAP,
    SalesPageData,
)
from app.packages.models.package import Package


def get_bundle_sales_page(db: Session, bundle_id: UUID) -> dict[str, Any] | None:
    bundle = (
        db.query(Package)
        .filter(Package.id == bundle_id, Package.is_bundle == True)  # noqa: E712
        .first()
    )
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        )
    result: dict[str, Any] | None = bundle.sales_page_sections
    return result


def update_bundle_sales_page(db: Session, bundle_id: UUID, data: SalesPageData) -> dict[str, Any]:
    bundle = (
        db.query(Package)
        .filter(Package.id == bundle_id, Package.is_bundle == True)  # noqa: E712
        .first()
    )
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        )

    # Validate each section's config against its type schema
    for section in data.sections:
        config_cls = SECTION_CONFIG_MAP.get(section.type)
        if config_cls:
            try:
                config_cls.model_validate(section.config)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid config for section '{section.type}' (id={section.id}): {e}",
                ) from e

    serialized: dict[str, Any] = data.model_dump()
    bundle.sales_page_sections = serialized

    db.commit()
    db.refresh(bundle)

    result: dict[str, Any] = bundle.sales_page_sections  # type: ignore[assignment]
    return result
