"""CRUD routes for implementation packages."""

import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models.user import User
from app.core.rate_limit import limiter
from app.courses.models import LessonStatus, Module
from app.courses.schemas.course import (
    CourseDetailResponse,
    LessonResponse,
    ModuleWithLessonsResponse,
)
from app.db.session import get_db
from app.implementation_packages.models.implementation_package import (
    ImplementationPackage,
    ImplementationPackageEnrollment,
)
from app.implementation_packages.schemas import (
    CurriculumLessonSummary,
    CurriculumModuleSummary,
    ImplPackageCreateRequest,
    ImplPackageDetailResponse,
    ImplPackageListResponse,
    ImplPackageUpdateRequest,
    PackageCurriculumResponse,
)

router = APIRouter()


@router.get("/", response_model=list[ImplPackageListResponse])
@limiter.limit("60/minute")
async def list_published_packages(
    request: Request,
    category: str | None = Query(default=None),
    is_featured: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ImplPackageListResponse]:
    query = db.query(ImplementationPackage).filter(
        ImplementationPackage.is_published == True  # noqa: E712
    )
    if category:
        query = query.filter(ImplementationPackage.category == category)
    if is_featured is not None:
        query = query.filter(ImplementationPackage.is_featured == is_featured)  # noqa: E712

    packages = query.order_by(ImplementationPackage.sort_order).all()
    return [ImplPackageListResponse.model_validate(pkg) for pkg in packages]


# NOTE: /all must come BEFORE /{slug} to avoid FastAPI matching "all" as a slug
@router.get("/all", response_model=list[ImplPackageListResponse])
@limiter.limit("60/minute")
async def list_all_packages(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ImplPackageListResponse]:
    packages = db.query(ImplementationPackage).order_by(ImplementationPackage.sort_order).all()
    return [ImplPackageListResponse.model_validate(pkg) for pkg in packages]


@router.get("/my", response_model=list[ImplPackageListResponse])
@limiter.limit("60/minute")
async def get_my_packages(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ImplPackageListResponse]:
    """Get published implementation packages the current user IS enrolled in.
    Admins own all published packages."""
    if current_user.role == "admin":
        packages = (
            db.query(ImplementationPackage)
            .filter(ImplementationPackage.is_published == True)  # noqa: E712
            .order_by(ImplementationPackage.sort_order)
            .all()
        )
        return [ImplPackageListResponse.model_validate(pkg) for pkg in packages]

    enrolled_package_ids = (
        db.query(ImplementationPackageEnrollment.package_id)
        .filter(ImplementationPackageEnrollment.user_id == current_user.id)
        .subquery()
    )

    packages = (
        db.query(ImplementationPackage)
        .filter(
            ImplementationPackage.is_published == True,  # noqa: E712
            ImplementationPackage.id.in_(enrolled_package_ids),
        )
        .order_by(ImplementationPackage.sort_order)
        .all()
    )

    return [ImplPackageListResponse.model_validate(pkg) for pkg in packages]


@router.get("/store", response_model=list[ImplPackageListResponse])
@limiter.limit("60/minute")
async def get_store_packages(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ImplPackageListResponse]:
    """Get published implementation packages the current user does NOT already own.
    Admins own everything, so this returns an empty list for them."""
    if current_user.role == "admin":
        return []

    owned_package_ids = (
        db.query(ImplementationPackageEnrollment.package_id)
        .filter(ImplementationPackageEnrollment.user_id == current_user.id)
        .subquery()
    )

    packages = (
        db.query(ImplementationPackage)
        .filter(
            ImplementationPackage.is_published == True,  # noqa: E712
            ImplementationPackage.id.notin_(owned_package_ids),
        )
        .order_by(ImplementationPackage.is_featured.desc(), ImplementationPackage.sort_order)
        .all()
    )

    return [ImplPackageListResponse.model_validate(pkg) for pkg in packages]


@router.get("/detail/{package_id}", response_model=ImplPackageDetailResponse)
@limiter.limit("60/minute")
async def get_package_by_id(
    request: Request,
    package_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImplPackageDetailResponse:
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )
    return ImplPackageDetailResponse.model_validate(pkg)


@router.get("/{slug}", response_model=ImplPackageDetailResponse)
@limiter.limit("60/minute")
async def get_package_by_slug(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
) -> ImplPackageDetailResponse:
    pkg = (
        db.query(ImplementationPackage)
        .filter(
            ImplementationPackage.slug == slug,
            ImplementationPackage.is_published == True,  # noqa: E712
        )
        .first()
    )
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )
    return ImplPackageDetailResponse.model_validate(pkg)


@router.get("/{slug}/learning", response_model=CourseDetailResponse)
@limiter.limit("60/minute")
async def get_package_learning(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
) -> CourseDetailResponse:
    """Get implementation package in CourseDetail format for the learning view."""
    pkg = (
        db.query(ImplementationPackage)
        .options(joinedload(ImplementationPackage.modules).joinedload(Module.lessons))
        .filter(
            ImplementationPackage.slug == slug,
            ImplementationPackage.is_published == True,  # noqa: E712
        )
        .first()
    )
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )

    modules_data = []
    for m in sorted(pkg.modules, key=lambda x: x.sort_order):
        filtered_lessons = [
            lesson
            for lesson in sorted(m.lessons, key=lambda x: x.sort_order)
            if lesson.status != LessonStatus.UNAVAILABLE
        ]
        modules_data.append(
            ModuleWithLessonsResponse(
                id=str(m.id),
                course_id=None,
                implementation_package_id=str(m.implementation_package_id),
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
                    for lesson in filtered_lessons
                ],
            )
        )

    total_lessons = sum(len(m.lessons) for m in modules_data)
    total_duration = sum(lesson.duration_seconds for m in modules_data for lesson in m.lessons)

    return CourseDetailResponse(
        id=str(pkg.id),
        title=pkg.title,
        slug=pkg.slug,
        description=pkg.description,
        thumbnail_url=pkg.thumbnail_url,
        estimated_hours=pkg.estimated_hours,
        is_published=pkg.is_published,
        category=pkg.category,
        sort_order=pkg.sort_order,
        learning_title=pkg.learning_title,
        learning_description=pkg.learning_description,
        learning_thumbnail_url=pkg.learning_thumbnail_url,
        sales_page_sections=pkg.sales_page_sections,
        created_at=pkg.created_at,
        updated_at=pkg.updated_at,
        modules=modules_data,
        total_lessons=total_lessons,
        total_duration_seconds=total_duration,
    )


@router.get("/{slug}/curriculum", response_model=PackageCurriculumResponse)
@limiter.limit("60/minute")
async def get_package_curriculum(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
) -> PackageCurriculumResponse:
    """Get curriculum summary for a published implementation package (public)."""
    pkg = (
        db.query(ImplementationPackage)
        .filter(
            ImplementationPackage.slug == slug,
            ImplementationPackage.is_published == True,  # noqa: E712
        )
        .first()
    )
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )

    modules = (
        db.query(Module)
        .options(joinedload(Module.lessons))
        .filter(Module.implementation_package_id == pkg.id)
        .order_by(Module.sort_order)
        .all()
    )

    module_summaries = []
    total_lessons = 0
    total_duration = 0

    for m in modules:
        available_lessons = sorted(
            [lesson for lesson in m.lessons if lesson.status == LessonStatus.AVAILABLE],
            key=lambda x: x.sort_order,
        )
        module_duration = sum(lesson.duration_seconds for lesson in available_lessons)
        total_lessons += len(available_lessons)
        total_duration += module_duration

        module_summaries.append(
            CurriculumModuleSummary(
                title=m.title,
                description=m.description,
                sort_order=m.sort_order,
                lessons=[
                    CurriculumLessonSummary(
                        title=lesson.title,
                        duration_seconds=lesson.duration_seconds,
                        sort_order=lesson.sort_order,
                    )
                    for lesson in available_lessons
                ],
                lesson_count=len(available_lessons),
                total_duration_seconds=module_duration,
            )
        )

    return PackageCurriculumResponse(
        modules=module_summaries,
        total_lessons=total_lessons,
        total_duration_seconds=total_duration,
    )


@router.post("/", response_model=ImplPackageDetailResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_package(
    request: Request,
    data: ImplPackageCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImplPackageDetailResponse:
    existing = (
        db.query(ImplementationPackage).filter(ImplementationPackage.slug == data.slug).first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pakiet ze slugiem '{data.slug}' już istnieje",
        )

    now = datetime.now(UTC)
    pkg = ImplementationPackage(
        id=uuid.uuid4(),
        slug=data.slug,
        title=data.title,
        description=data.description,
        category=data.category,
        price=data.price,
        original_price=data.original_price,
        currency=data.currency,
        total_time_saved=data.total_time_saved,
        tools=json.dumps(data.tools),
        video_url=data.video_url,
        thumbnail_url=data.thumbnail_url,
        is_published=data.is_published,
        is_featured=data.is_featured,
        sort_order=data.sort_order,
        sales_page_sections=data.sales_page_sections,
        created_at=now,
        updated_at=now,
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return ImplPackageDetailResponse.model_validate(pkg)


@router.patch("/{package_id}", response_model=ImplPackageDetailResponse)
@limiter.limit("30/minute")
async def update_package(
    request: Request,
    package_id: uuid.UUID,
    data: ImplPackageUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImplPackageDetailResponse:
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )

    update_data = data.model_dump(exclude_unset=True)

    if "slug" in update_data and update_data["slug"] != pkg.slug:
        existing = (
            db.query(ImplementationPackage)
            .filter(ImplementationPackage.slug == update_data["slug"])
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Pakiet ze slugiem '{update_data['slug']}' już istnieje",
            )

    if "tools" in update_data:
        update_data["tools"] = json.dumps(update_data["tools"])

    for field, value in update_data.items():
        setattr(pkg, field, value)

    pkg.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(pkg)
    return ImplPackageDetailResponse.model_validate(pkg)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_package(
    request: Request,
    package_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )
    db.delete(pkg)
    db.commit()
