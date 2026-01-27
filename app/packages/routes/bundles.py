"""Bundle API endpoints - simplified view of packages where is_bundle=True."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.db.session import get_db
from app.packages.models.bundle import BundleCourseItem
from app.packages.models.package import Package, PackageBundleItem
from app.packages.schemas.bundle import (
    BundleCourseDetailItem,
    BundleCreateRequest,
    BundleDetailResponse,
    BundleListResponse,
    BundleUpdateRequest,
)

router = APIRouter(prefix="/bundles", tags=["bundles"])


@router.get("", response_model=list[BundleListResponse])
def list_bundles(
    db: Session = Depends(get_db),
) -> list[BundleListResponse]:
    """
    Get list of published bundles (packages where is_bundle=True).

    Returns:
        List of bundles with marketing-friendly format
    """
    bundles = (
        db.query(Package)
        .filter(
            Package.is_published.is_(True),  # noqa: E712
            Package.is_bundle.is_(True),  # noqa: E712
        )
        .order_by(Package.is_featured.desc(), Package.created_at.desc())
        .all()
    )

    return [BundleListResponse.from_orm(bundle) for bundle in bundles]


@router.get("/slug/{slug}", response_model=BundleListResponse)
def get_bundle_by_slug(
    slug: str,
    db: Session = Depends(get_db),
) -> BundleListResponse:
    """
    Get bundle details by slug.

    Args:
        slug: Bundle slug

    Returns:
        Bundle details

    Raises:
        404: Bundle not found or not published
    """
    bundle = (
        db.query(Package)
        .filter(
            Package.slug == slug,
            Package.is_published.is_(True),  # noqa: E712
            Package.is_bundle.is_(True),  # noqa: E712
        )
        .first()
    )

    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    return BundleListResponse.from_orm(bundle)


# Admin endpoints - require authentication


def _build_bundle_detail_response(db: Session, bundle: Package) -> BundleDetailResponse:
    """Build BundleDetailResponse with packages and courses."""
    from app.courses.models.course import Course
    from app.packages.schemas.package import PackageListResponse

    # Get child packages
    package_items = (
        db.query(PackageBundleItem)
        .filter(PackageBundleItem.bundle_id == bundle.id)
        .order_by(PackageBundleItem.sort_order)
        .all()
    )

    packages = []
    for item in package_items:
        pkg = db.query(Package).filter(Package.id == item.child_package_id).first()
        if pkg:
            packages.append(PackageListResponse.model_validate(pkg))

    # Get courses
    course_items = (
        db.query(BundleCourseItem)
        .filter(BundleCourseItem.bundle_id == bundle.id)
        .order_by(BundleCourseItem.sort_order)
        .all()
    )

    courses: list[BundleCourseDetailItem] = []
    for item in course_items:
        course = db.query(Course).filter(Course.id == item.course_id).first()
        if course:
            courses.append(
                BundleCourseDetailItem(
                    id=str(course.id),
                    slug=course.slug,
                    title=course.title,
                    category=course.category,
                    access_duration_days=item.access_duration_days,
                )
            )

    # Calculate badge
    badge = None
    if bundle.original_price and bundle.original_price > bundle.price:
        discount = int((1 - bundle.price / bundle.original_price) * 100)
        badge = f"-{discount}%"
    elif bundle.is_featured:
        badge = "Polecane"

    return BundleDetailResponse(
        id=str(bundle.id),
        slug=bundle.slug,
        name=bundle.title,
        shortDescription=bundle.description,
        pricing={
            "regular": bundle.price / 100,
            "currency": bundle.currency,
        },
        popular=bundle.is_featured,
        badge=badge,
        packages=packages,
        courses=courses,
        sales_page_sections=bundle.sales_page_sections,
    )


@router.get("/{bundle_id}", response_model=BundleDetailResponse)
def get_bundle_detail(
    bundle_id: str,
    db: Session = Depends(get_db),
) -> BundleDetailResponse:
    """Get bundle with full content (packages + courses)."""

    try:
        bundle_uuid = uuid.UUID(bundle_id)
    except ValueError:
        raise HTTPException(400, "Invalid bundle ID") from None

    bundle = (
        db.query(Package)
        .filter(
            Package.id == bundle_uuid,
            Package.is_published.is_(True),  # noqa: E712
            Package.is_bundle.is_(True),  # noqa: E712
        )
        .first()
    )

    if not bundle:
        raise HTTPException(404, "Bundle not found")

    return _build_bundle_detail_response(db, bundle)


@router.post(
    "",
    response_model=BundleDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bundle(
    bundle_data: BundleCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> BundleDetailResponse:
    """
    Create a new bundle (admin only).

    Bundle can contain:
    - Packages (via package_ids)
    - Courses (via course_items or course_ids for backward compatibility)
    - Or both
    """
    # Check if slug already exists
    existing = db.query(Package).filter(Package.slug == bundle_data.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Package with slug '{bundle_data.slug}' already exists",
        )

    # Create bundle package
    new_bundle = Package(
        slug=bundle_data.slug,
        title=bundle_data.name,
        description=bundle_data.description,
        category=bundle_data.category,
        price=bundle_data.price,
        original_price=bundle_data.original_price,
        currency=bundle_data.currency,
        difficulty=bundle_data.difficulty,
        total_time_saved=bundle_data.total_time_saved,
        tools="[]",  # Empty for bundles
        is_published=True,
        is_featured=bundle_data.is_featured,
        is_bundle=True,  # CRITICAL
    )

    db.add(new_bundle)
    db.flush()  # Get ID

    # Add package items
    for idx, package_id in enumerate(bundle_data.package_ids):
        try:
            pkg_uuid = uuid.UUID(package_id)
        except ValueError:
            raise HTTPException(400, f"Invalid package ID: {package_id}") from None

        # Verify package exists
        pkg = db.query(Package).filter(Package.id == pkg_uuid).first()
        if not pkg:
            raise HTTPException(404, f"Package {package_id} not found")

        bundle_item = PackageBundleItem(
            bundle_id=new_bundle.id,
            child_package_id=pkg_uuid,
            sort_order=idx,
        )
        db.add(bundle_item)

    # Add course items — prefer course_items, fallback to course_ids
    from app.courses.models.course import Course

    if bundle_data.course_items:
        for idx, ci in enumerate(bundle_data.course_items):
            try:
                course_uuid = uuid.UUID(ci.course_id)
            except ValueError:
                raise HTTPException(400, f"Invalid course ID: {ci.course_id}") from None

            course = db.query(Course).filter(Course.id == course_uuid).first()
            if not course:
                raise HTTPException(404, f"Course {ci.course_id} not found")

            course_item = BundleCourseItem(
                bundle_id=new_bundle.id,
                course_id=course_uuid,
                sort_order=idx,
                access_duration_days=ci.access_duration_days,
            )
            db.add(course_item)
    else:
        # Backward compatibility: use course_ids with no duration
        for idx, course_id in enumerate(bundle_data.course_ids):
            try:
                course_uuid = uuid.UUID(course_id)
            except ValueError:
                raise HTTPException(400, f"Invalid course ID: {course_id}") from None

            course = db.query(Course).filter(Course.id == course_uuid).first()
            if not course:
                raise HTTPException(404, f"Course {course_id} not found")

            course_item = BundleCourseItem(
                bundle_id=new_bundle.id,
                course_id=course_uuid,
                sort_order=idx,
            )
            db.add(course_item)

    db.commit()
    db.refresh(new_bundle)

    # Build response with full content
    return _build_bundle_detail_response(db, new_bundle)


@router.patch("/{bundle_id}", response_model=BundleDetailResponse)
def update_bundle(
    bundle_id: str,
    bundle_data: BundleUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> BundleDetailResponse:
    """Update bundle (admin only)."""

    try:
        bundle_uuid = uuid.UUID(bundle_id)
    except ValueError:
        raise HTTPException(400, "Invalid bundle ID") from None

    bundle = (
        db.query(Package)
        .filter(Package.id == bundle_uuid, Package.is_bundle.is_(True))  # noqa: E712
        .first()
    )

    if not bundle:
        raise HTTPException(404, "Bundle not found")

    # Update basic fields
    if bundle_data.name is not None:
        bundle.title = bundle_data.name
    if bundle_data.description is not None:
        bundle.description = bundle_data.description
    if bundle_data.price is not None:
        bundle.price = bundle_data.price
    if bundle_data.original_price is not None:
        bundle.original_price = bundle_data.original_price
    if bundle_data.is_featured is not None:
        bundle.is_featured = bundle_data.is_featured

    # Update package items
    if bundle_data.package_ids is not None:
        # Remove old items
        db.query(PackageBundleItem).filter(PackageBundleItem.bundle_id == bundle_uuid).delete()

        # Add new items
        for idx, package_id in enumerate(bundle_data.package_ids):
            pkg_uuid = uuid.UUID(package_id)
            bundle_item = PackageBundleItem(
                bundle_id=bundle_uuid,
                child_package_id=pkg_uuid,
                sort_order=idx,
            )
            db.add(bundle_item)

    # Update course items — prefer course_items, fallback to course_ids
    if bundle_data.course_items is not None:
        db.query(BundleCourseItem).filter(BundleCourseItem.bundle_id == bundle_uuid).delete()

        for idx, ci in enumerate(bundle_data.course_items):
            course_uuid = uuid.UUID(ci.course_id)
            course_item = BundleCourseItem(
                bundle_id=bundle_uuid,
                course_id=course_uuid,
                sort_order=idx,
                access_duration_days=ci.access_duration_days,
            )
            db.add(course_item)
    elif bundle_data.course_ids is not None:
        # Backward compatibility: use course_ids with no duration
        db.query(BundleCourseItem).filter(BundleCourseItem.bundle_id == bundle_uuid).delete()

        for idx, course_id in enumerate(bundle_data.course_ids):
            course_uuid = uuid.UUID(course_id)
            course_item = BundleCourseItem(
                bundle_id=bundle_uuid,
                course_id=course_uuid,
                sort_order=idx,
            )
            db.add(course_item)

    db.commit()
    db.refresh(bundle)

    return _build_bundle_detail_response(db, bundle)


@router.delete("/{bundle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bundle(
    bundle_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    """
    Delete bundle (admin only).

    Soft delete: sets is_published=False instead of actual deletion.
    """
    try:
        bundle_uuid = uuid.UUID(bundle_id)
    except ValueError:
        raise HTTPException(400, "Invalid bundle ID") from None

    bundle = (
        db.query(Package)
        .filter(Package.id == bundle_uuid, Package.is_bundle.is_(True))  # noqa: E712
        .first()
    )

    if not bundle:
        raise HTTPException(404, "Bundle not found")

    # Soft delete
    bundle.is_published = False
    db.commit()

    return None
