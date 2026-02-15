"""API routes for implementation packages."""

import json
import logging
import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.auth.services.email_service import build_welcome_email, get_email_service
from app.core import security
from app.core.config import settings
from app.core.constants import THUMBNAIL_ALLOWED_MIME_TYPES, THUMBNAIL_MAX_SIZE_BYTES
from app.core.rate_limit import limiter
from app.courses.models import LessonStatus, Module
from app.courses.schemas.course import (
    CourseDetailResponse,
    LessonResponse,
    ModuleCreate,
    ModuleReorderRequest,
    ModuleResponse,
    ModuleWithLessonsResponse,
)
from app.courses.schemas.sales_page import (
    SalesPageData,
    SalesPageResponse,
    SalesPageUpdateRequest,
)
from app.db.session import get_db
from app.implementation_packages.models.implementation_package import (
    ImplementationPackage,
    ImplementationPackageEnrollment,
    ImplementationPackageProcess,
)
from app.implementation_packages.schemas import (
    CurriculumLessonSummary,
    CurriculumModuleSummary,
    ImplPackageCreateRequest,
    ImplPackageDetailResponse,
    ImplPackageEnrollmentCreateRequest,
    ImplPackageEnrollmentListResponse,
    ImplPackageEnrollmentResponse,
    ImplPackageEnrollmentUpdateRequest,
    ImplPackageListResponse,
    ImplPackageUpdateRequest,
    PackageCurriculumResponse,
    ProcessCreateRequest,
    ProcessUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/implementation-packages", tags=["implementation-packages"])


# --- Public endpoints ---


@router.get("", response_model=list[ImplPackageListResponse])
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
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")
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
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")
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
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")

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
        difficulty=pkg.difficulty,
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
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")

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


@router.post("", response_model=ImplPackageDetailResponse, status_code=201)
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
        raise HTTPException(status_code=400, detail=f"Pakiet ze slugiem '{data.slug}' już istnieje")

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
        difficulty=data.difficulty,
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
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")

    update_data = data.model_dump(exclude_unset=True)

    if "slug" in update_data and update_data["slug"] != pkg.slug:
        existing = (
            db.query(ImplementationPackage)
            .filter(ImplementationPackage.slug == update_data["slug"])
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail=f"Pakiet ze slugiem '{update_data['slug']}' już istnieje"
            )

    if "tools" in update_data:
        update_data["tools"] = json.dumps(update_data["tools"])

    for field, value in update_data.items():
        setattr(pkg, field, value)

    pkg.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(pkg)
    return ImplPackageDetailResponse.model_validate(pkg)


@router.delete("/{package_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_package(
    request: Request,
    package_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")
    db.delete(pkg)
    db.commit()


# --- Process management ---


@router.post("/{package_id}/processes", response_model=dict, status_code=201)
@limiter.limit("30/minute")
async def create_process(
    request: Request,
    package_id: uuid.UUID,
    data: ProcessCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")

    process = ImplementationPackageProcess(
        id=uuid.uuid4(),
        package_id=package_id,
        name=data.name,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.add(process)
    db.commit()
    db.refresh(process)
    return {
        "id": str(process.id),
        "name": process.name,
        "description": process.description,
        "sort_order": process.sort_order,
    }


@router.patch("/processes/{process_id}", response_model=dict)
@limiter.limit("30/minute")
async def update_process(
    request: Request,
    process_id: uuid.UUID,
    data: ProcessUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    process = (
        db.query(ImplementationPackageProcess)
        .filter(ImplementationPackageProcess.id == process_id)
        .first()
    )
    if not process:
        raise HTTPException(status_code=404, detail="Proces nie został znaleziony")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(process, field, value)

    db.commit()
    db.refresh(process)
    return {
        "id": str(process.id),
        "name": process.name,
        "description": process.description,
        "sort_order": process.sort_order,
    }


@router.delete("/processes/{process_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_process(
    request: Request,
    process_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    process = (
        db.query(ImplementationPackageProcess)
        .filter(ImplementationPackageProcess.id == process_id)
        .first()
    )
    if not process:
        raise HTTPException(status_code=404, detail="Proces nie został znaleziony")
    db.delete(process)
    db.commit()


# --- Module management ---


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
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")

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
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")

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
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")

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


# --- Enrollment management ---


def _enrollment_to_response(
    enrollment: ImplementationPackageEnrollment,
) -> ImplPackageEnrollmentResponse:
    return ImplPackageEnrollmentResponse(
        id=str(enrollment.id),
        user_id=str(enrollment.user_id),
        package_id=str(enrollment.package_id),
        user_name=enrollment.user.name if enrollment.user else None,
        user_email=enrollment.user.email if enrollment.user else "",
        enrolled_at=enrollment.enrolled_at,
        expires_at=enrollment.expires_at,
        is_expired=enrollment.is_expired,
    )


@router.get(
    "/{package_id}/enrollments",
    response_model=ImplPackageEnrollmentListResponse,
)
@limiter.limit("60/minute")
async def list_package_enrollments(
    request: Request,
    package_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImplPackageEnrollmentListResponse:
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")

    query = (
        db.query(ImplementationPackageEnrollment)
        .options(joinedload(ImplementationPackageEnrollment.user))
        .filter(ImplementationPackageEnrollment.package_id == package_id)
    )
    total = (
        db.query(ImplementationPackageEnrollment)
        .filter(ImplementationPackageEnrollment.package_id == package_id)
        .count()
    )
    enrollments = query.offset(skip).limit(limit).all()

    return ImplPackageEnrollmentListResponse(
        total=total,
        enrollments=[_enrollment_to_response(e) for e in enrollments],
    )


@router.post(
    "/{package_id}/enrollments",
    response_model=ImplPackageEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def create_package_enrollment(
    request: Request,
    package_id: uuid.UUID,
    data: ImplPackageEnrollmentCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImplPackageEnrollmentResponse:
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Pakiet nie został znaleziony")

    user = db.query(User).filter(User.email == data.email).first()
    send_welcome = False
    temp_password = ""

    if not user:
        temp_password = secrets.token_urlsafe(12)
        user = User(
            email=data.email,
            name=data.name or data.email.split("@")[0],
            hashed_password=security.get_password_hash(temp_password),
            role="paid",
            is_active=True,
        )
        db.add(user)
        db.flush()
        send_welcome = True

    existing = (
        db.query(ImplementationPackageEnrollment)
        .filter(
            ImplementationPackageEnrollment.user_id == user.id,
            ImplementationPackageEnrollment.package_id == package_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Użytkownik jest już zapisany do tego pakietu",
        )

    enrollment = ImplementationPackageEnrollment(
        user_id=user.id,
        package_id=package_id,
        enrolled_at=datetime.now(UTC),
        expires_at=data.expires_at,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    if send_welcome:
        try:
            email_service = get_email_service()
            email_message = build_welcome_email(
                name=str(user.name),
                email=str(user.email),
                temp_password=temp_password,
            )
            await email_service.send_email(email_message)
        except Exception as e:
            logger.warning("Could not send welcome email: %s", e)

    return _enrollment_to_response(enrollment)


@router.patch(
    "/{package_id}/enrollments/{enrollment_id}",
    response_model=ImplPackageEnrollmentResponse,
)
@limiter.limit("30/minute")
async def update_package_enrollment(
    request: Request,
    package_id: uuid.UUID,
    enrollment_id: uuid.UUID,
    data: ImplPackageEnrollmentUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ImplPackageEnrollmentResponse:
    enrollment = (
        db.query(ImplementationPackageEnrollment)
        .options(joinedload(ImplementationPackageEnrollment.user))
        .filter(
            ImplementationPackageEnrollment.id == enrollment_id,
            ImplementationPackageEnrollment.package_id == package_id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment nie został znaleziony")

    enrollment.expires_at = data.expires_at
    db.commit()
    db.refresh(enrollment)

    return _enrollment_to_response(enrollment)


@router.delete(
    "/{package_id}/enrollments/{enrollment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def delete_package_enrollment(
    request: Request,
    package_id: uuid.UUID,
    enrollment_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    enrollment = (
        db.query(ImplementationPackageEnrollment)
        .filter(
            ImplementationPackageEnrollment.id == enrollment_id,
            ImplementationPackageEnrollment.package_id == package_id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment nie został znaleziony")

    db.delete(enrollment)
    db.commit()


# --- Thumbnail management ---


@router.post("/{package_id}/learning-thumbnail")
@limiter.limit("30/minute")
async def upload_package_learning_thumbnail(
    request: Request,
    package_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload a learning thumbnail image for an implementation package (admin only)."""
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pakiet nie został znaleziony",
        )

    if file.content_type not in THUMBNAIL_ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nieprawidłowy typ pliku. Dozwolone: PNG, JPG, WebP. "
            f"Otrzymano: {file.content_type}",
        )

    file_content = await file.read()
    if len(file_content) > THUMBNAIL_MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Rozmiar pliku przekracza maksymalny dozwolony rozmiar 5MB",
        )

    file_extension = Path(file.filename or "image.jpg").suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    upload_dir = Path(settings.UPLOAD_DIR) / "thumbnails"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Remove old thumbnail file if it exists
    if pkg.learning_thumbnail_url:
        old_path = upload_dir / Path(pkg.learning_thumbnail_url).name
        if old_path.exists():
            old_path.unlink()

    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(file_content)

    thumbnail_url = (
        f"{settings.API_V1_PREFIX}/implementation-packages/{package_id}"
        f"/learning-thumbnail/{unique_filename}"
    )
    pkg.learning_thumbnail_url = thumbnail_url

    db.commit()
    db.refresh(pkg)

    return {
        "learning_thumbnail_url": thumbnail_url,
    }


@router.get("/{package_id}/learning-thumbnail/{filename}")
async def serve_package_learning_thumbnail(
    package_id: uuid.UUID,
    filename: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Serve a learning thumbnail image for an implementation package."""
    upload_root = (Path(settings.UPLOAD_DIR) / "thumbnails").resolve()
    file_path = (upload_root / filename).resolve()

    # Security check: prevent path traversal
    if not str(file_path).startswith(str(upload_root)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowa nazwa pliku",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Miniaturka nie znaleziona",
        )

    media_type = "image/jpeg"
    suffix = file_path.suffix.lower()
    if suffix == ".png":
        media_type = "image/png"
    elif suffix == ".webp":
        media_type = "image/webp"

    return FileResponse(path=str(file_path), media_type=media_type)


# --- Sales page management ---


SALES_PAGE_ALLOWED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"]


@router.get(
    "/{package_id}/sales-page",
    response_model=SalesPageResponse,
)
@limiter.limit("60/minute")
async def get_impl_package_sales_page(
    request: Request,
    package_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SalesPageResponse:
    """Get sales page configuration for an implementation package (admin only)."""
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pakiet nie został znaleziony",
        )

    if pkg.sales_page_sections is not None:
        return SalesPageResponse(
            sales_page_sections=SalesPageData.model_validate(pkg.sales_page_sections)
        )
    return SalesPageResponse(sales_page_sections=None)


@router.put(
    "/{package_id}/sales-page",
    response_model=SalesPageResponse,
)
@limiter.limit("30/minute")
async def update_impl_package_sales_page(
    request: Request,
    package_id: uuid.UUID,
    payload: SalesPageUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SalesPageResponse:
    """Update sales page configuration for an implementation package (admin only)."""
    from app.courses.schemas.sales_page import SECTION_CONFIG_MAP

    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pakiet nie został znaleziony",
        )

    for section in payload.sales_page_sections.sections:
        config_cls = SECTION_CONFIG_MAP.get(section.type)
        if config_cls:
            try:
                config_cls.model_validate(section.config)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid config for section '{section.type}' (id={section.id}): {e}",
                ) from e

    pkg.sales_page_sections = payload.sales_page_sections.model_dump()
    db.commit()
    db.refresh(pkg)

    return SalesPageResponse(
        sales_page_sections=SalesPageData.model_validate(pkg.sales_page_sections)
    )


@router.post("/{package_id}/sales-page/upload-image")
@limiter.limit("30/minute")
async def upload_impl_package_sales_page_image(
    request: Request,
    package_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Upload an image for an implementation package sales page section (admin only)."""
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pakiet nie został znaleziony",
        )

    if file.content_type not in SALES_PAGE_ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Nieprawidłowy typ pliku. Dozwolone: PNG, JPG, WebP."
                f" Otrzymano: {file.content_type}"
            ),
        )

    max_size_bytes = 5 * 1024 * 1024  # 5 MB
    file_content = await file.read()
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Rozmiar pliku przekracza maksymalny dozwolony rozmiar 5MB",
        )

    file_extension = Path(file.filename or "image.jpg").suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    upload_dir = Path(settings.UPLOAD_DIR) / "sales-page"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(file_content)

    image_url = (
        f"{settings.API_V1_PREFIX}/implementation-packages/{package_id}"
        f"/sales-page/images/{unique_filename}"
    )

    return {"image_url": image_url}


@router.get("/{package_id}/sales-page/images/{filename}")
async def serve_impl_package_sales_page_image(
    package_id: uuid.UUID,
    filename: str,
) -> FileResponse:
    """Serve an implementation package sales page image."""
    upload_root = (Path(settings.UPLOAD_DIR) / "sales-page").resolve()
    file_path = (upload_root / filename).resolve()

    if not str(file_path).startswith(str(upload_root)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowa nazwa pliku",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    media_type = "image/jpeg"
    suffix = file_path.suffix.lower()
    if suffix == ".png":
        media_type = "image/png"
    elif suffix == ".webp":
        media_type = "image/webp"

    return FileResponse(path=str(file_path), media_type=media_type)
