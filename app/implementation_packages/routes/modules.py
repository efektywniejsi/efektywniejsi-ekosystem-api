"""Routes for implementation package modules."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.core.rate_limit import limiter
from app.courses.models import Module
from app.courses.schemas.course import (
    LessonResponse,
    ModuleCreate,
    ModuleReorderRequest,
    ModuleResponse,
    ModuleWithLessonsResponse,
)
from app.db.session import get_db
from app.implementation_packages.models.implementation_package import ImplementationPackage

router = APIRouter()


@router.get(
    "/{package_id}/modules-with-lessons",
    response_model=list[ModuleWithLessonsResponse],
)
@limiter.limit("60/minute")
async def get_package_modules_with_lessons(
    request: Request,
    package_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ModuleWithLessonsResponse]:
    """Get all modules with their lessons for an implementation package (admin only)."""
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )

    modules = (
        db.query(Module)
        .options(joinedload(Module.lessons))
        .filter(Module.implementation_package_id == package_id)
        .order_by(Module.sort_order)
        .all()
    )

    return [
        ModuleWithLessonsResponse(
            id=str(m.id),
            course_id=str(m.course_id) if m.course_id else None,
            implementation_package_id=str(m.implementation_package_id)
            if m.implementation_package_id
            else None,
            title=m.title,
            description=m.description,
            sort_order=m.sort_order,
            created_at=m.created_at,
            updated_at=m.updated_at,
            lessons=[
                LessonResponse(
                    id=str(lesson.id),
                    module_id=str(lesson.module_id),
                    title=lesson.title,
                    description=lesson.description,
                    mux_playback_id=lesson.mux_playback_id,
                    mux_asset_id=lesson.mux_asset_id,
                    duration_seconds=lesson.duration_seconds,
                    status=lesson.status.value,
                    sort_order=lesson.sort_order,
                    created_at=lesson.created_at,
                    updated_at=lesson.updated_at,
                )
                for lesson in sorted(m.lessons, key=lambda x: x.sort_order)
            ],
        )
        for m in modules
    ]


@router.post(
    "/{package_id}/modules",
    response_model=ModuleResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def create_package_module(
    request: Request,
    package_id: uuid.UUID,
    data: ModuleCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ModuleResponse:
    """Add a module to an implementation package (admin only)."""
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )

    module = Module(
        implementation_package_id=package_id,
        title=data.title,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.add(module)
    db.commit()
    db.refresh(module)

    return ModuleResponse(
        id=str(module.id),
        course_id=None,
        implementation_package_id=str(module.implementation_package_id),
        title=module.title,
        description=module.description,
        sort_order=module.sort_order,
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


@router.put("/{package_id}/modules/reorder", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def reorder_package_modules(
    request: Request,
    package_id: uuid.UUID,
    data: ModuleReorderRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Reorder modules in an implementation package (admin only)."""
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )

    module_ids = [uuid.UUID(mid) for mid in data.module_ids]
    modules = db.query(Module).filter(Module.id.in_(module_ids)).all()

    if len(modules) != len(module_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jeden lub więcej identyfikatorów modułów jest nieprawidłowych",
        )

    for module in modules:
        if module.implementation_package_id != package_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Moduł {module.id} nie należy do tego pakietu",
            )

    for index, module_id in enumerate(module_ids):
        module = next(m for m in modules if m.id == module_id)
        module.sort_order = index

    db.commit()

    return {"message": "Kolejność modułów zmieniona"}
