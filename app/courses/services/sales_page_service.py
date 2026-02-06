"""Service for managing course sales page sections."""

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.courses.models.course import Course
from app.courses.schemas.sales_page import (
    SECTION_CONFIG_MAP,
    SalesPageData,
)


def get_sales_page(db: Session, course_id: UUID) -> dict[str, Any] | None:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    result: dict[str, Any] | None = course.sales_page_sections
    return result


def update_sales_page(db: Session, course_id: UUID, data: SalesPageData) -> dict[str, Any]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

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
    course.sales_page_sections = serialized

    db.commit()
    db.refresh(course)

    result: dict[str, Any] = course.sales_page_sections  # type: ignore[assignment]
    return result
