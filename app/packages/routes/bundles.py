"""Bundle API endpoints - simplified view of packages where is_bundle=True."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models.user import User
from app.courses.models.course import Course
from app.db.session import get_db
from app.implementation_packages.models.implementation_package import (
    ImplementationPackage,
)
from app.packages.models.bundle import BundleCourseItem, BundleImplementationPackageItem
from app.packages.models.order import Order, OrderItem, OrderStatus
from app.packages.models.package import Package, PackageBundleItem
from app.packages.schemas.bundle import (
    BundleCourseDetailItem,
    BundleCreateRequest,
    BundleDetailResponse,
    BundleImplPackageDetailItem,
    BundleListResponse,
    BundleUpdateRequest,
)
from app.packages.schemas.package import PackageListResponse

router = APIRouter(prefix="/bundles")


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
            Package.is_published == True,  # noqa: E712
            Package.is_bundle == True,  # noqa: E712
        )
        .order_by(Package.is_featured.desc(), Package.created_at.desc())
        .all()
    )

    return [BundleListResponse.from_orm(bundle) for bundle in bundles]


# NOTE: /store must be defined BEFORE /{bundle_id} to avoid FastAPI matching "store" as a UUID
@router.get("/store", response_model=list[BundleListResponse])
def list_store_bundles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BundleListResponse]:
    """
    Get published bundles that contain implementation packages.

    These are displayed in the store's Packages tab alongside individual impl packages.
    Requires authentication (store is only for logged-in users).
    """
    bundle_ids_with_impl = db.query(BundleImplementationPackageItem.bundle_id).distinct().subquery()

    bundles = (
        db.query(Package)
        .filter(
            Package.is_published == True,  # noqa: E712
            Package.is_bundle == True,  # noqa: E712
            Package.id.in_(bundle_ids_with_impl),
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
            Package.is_published == True,  # noqa: E712
            Package.is_bundle == True,  # noqa: E712
        )
        .first()
    )

    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Oferta bundlowa nie znaleziona"
        )

    return BundleListResponse.from_orm(bundle)


def _build_bundle_detail_response(db: Session, bundle: Package) -> BundleDetailResponse:
    """Build BundleDetailResponse with packages, courses, and implementation packages."""
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

    impl_pkg_items = (
        db.query(BundleImplementationPackageItem)
        .filter(BundleImplementationPackageItem.bundle_id == bundle.id)
        .order_by(BundleImplementationPackageItem.sort_order)
        .all()
    )

    implementation_packages: list[BundleImplPackageDetailItem] = []
    for item in impl_pkg_items:
        impl_pkg = (
            db.query(ImplementationPackage)
            .filter(ImplementationPackage.id == item.implementation_package_id)
            .first()
        )
        if impl_pkg:
            implementation_packages.append(
                BundleImplPackageDetailItem(
                    id=str(impl_pkg.id),
                    slug=impl_pkg.slug,
                    title=impl_pkg.title,
                    category=impl_pkg.category,
                    access_duration_days=item.access_duration_days,
                )
            )

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
            "regular": bundle.price,  # grosz — frontend converts for display
            "original": bundle.original_price if bundle.original_price else None,
            "currency": bundle.currency,
        },
        popular=bundle.is_featured,
        badge=badge,
        packages=packages,
        courses=courses,
        implementation_packages=implementation_packages,
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nieprawidłowy ID bundla"
        ) from None

    bundle = (
        db.query(Package)
        .filter(
            Package.id == bundle_uuid,
            Package.is_published == True,  # noqa: E712
            Package.is_bundle == True,  # noqa: E712
        )
        .first()
    )

    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Oferta bundlowa nie znaleziona"
        )

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
    existing = db.query(Package).filter(Package.slug == bundle_data.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pakiet ze slugiem '{bundle_data.slug}' już istnieje",
        )

    new_bundle = Package(
        slug=bundle_data.slug,
        title=bundle_data.name,
        description=bundle_data.description,
        category=bundle_data.category,
        price=bundle_data.price,
        original_price=bundle_data.original_price,
        currency=bundle_data.currency,
        total_time_saved=bundle_data.total_time_saved,
        tools="[]",
        is_published=True,
        is_featured=bundle_data.is_featured,
        is_bundle=True,
    )

    db.add(new_bundle)
    db.flush()

    for idx, package_id in enumerate(bundle_data.package_ids):
        try:
            pkg_uuid = uuid.UUID(package_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Nieprawidłowy ID pakietu: {package_id}",
            ) from None

        pkg = db.query(Package).filter(Package.id == pkg_uuid).first()
        if not pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Pakiet {package_id} nie znaleziony"
            )

        bundle_item = PackageBundleItem(
            bundle_id=new_bundle.id,
            child_package_id=pkg_uuid,
            sort_order=idx,
        )
        db.add(bundle_item)

    if bundle_data.course_items:
        for idx, ci in enumerate(bundle_data.course_items):
            try:
                course_uuid = uuid.UUID(ci.course_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Nieprawidłowy ID kursu: {ci.course_id}",
                ) from None

            course = db.query(Course).filter(Course.id == course_uuid).first()
            if not course:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Kurs {ci.course_id} nie znaleziony",
                )

            course_item = BundleCourseItem(
                bundle_id=new_bundle.id,
                course_id=course_uuid,
                sort_order=idx,
                access_duration_days=ci.access_duration_days,
            )
            db.add(course_item)
    else:
        for idx, course_id in enumerate(bundle_data.course_ids):
            try:
                course_uuid = uuid.UUID(course_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Nieprawidłowy ID kursu: {course_id}",
                ) from None

            course = db.query(Course).filter(Course.id == course_uuid).first()
            if not course:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"Kurs {course_id} nie znaleziony"
                )

            course_item = BundleCourseItem(
                bundle_id=new_bundle.id,
                course_id=course_uuid,
                sort_order=idx,
            )
            db.add(course_item)

    for idx, ipi in enumerate(bundle_data.implementation_package_items):
        try:
            impl_uuid = uuid.UUID(ipi.implementation_package_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Nieprawidłowy ID pakietu wdrożeniowego: {ipi.implementation_package_id}",
            ) from None

        impl_pkg = (
            db.query(ImplementationPackage).filter(ImplementationPackage.id == impl_uuid).first()
        )
        if not impl_pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pakiet wdrożeniowy {ipi.implementation_package_id} nie znaleziony",
            )

        impl_item = BundleImplementationPackageItem(
            bundle_id=new_bundle.id,
            implementation_package_id=impl_uuid,
            sort_order=idx,
            access_duration_days=ipi.access_duration_days,
        )
        db.add(impl_item)

    db.commit()
    db.refresh(new_bundle)

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nieprawidłowy ID bundla"
        ) from None

    bundle = (
        db.query(Package)
        .filter(Package.id == bundle_uuid, Package.is_bundle == True)  # noqa: E712
        .first()
    )

    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Oferta bundlowa nie znaleziona"
        )

    if bundle_data.name is not None:
        bundle.title = bundle_data.name
    if bundle_data.description is not None:
        bundle.description = bundle_data.description
    if bundle_data.price is not None:
        bundle.price = bundle_data.price
    if "original_price" in (bundle_data.model_dump(exclude_unset=True) or {}):
        bundle.original_price = bundle_data.original_price
    if bundle_data.is_featured is not None:
        bundle.is_featured = bundle_data.is_featured

    if bundle_data.package_ids is not None:
        db.query(PackageBundleItem).filter(PackageBundleItem.bundle_id == bundle_uuid).delete()

        for idx, package_id in enumerate(bundle_data.package_ids):
            pkg_uuid = uuid.UUID(package_id)
            bundle_item = PackageBundleItem(
                bundle_id=bundle_uuid,
                child_package_id=pkg_uuid,
                sort_order=idx,
            )
            db.add(bundle_item)

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
        db.query(BundleCourseItem).filter(BundleCourseItem.bundle_id == bundle_uuid).delete()

        for idx, course_id in enumerate(bundle_data.course_ids):
            course_uuid = uuid.UUID(course_id)
            course_item = BundleCourseItem(
                bundle_id=bundle_uuid,
                course_id=course_uuid,
                sort_order=idx,
            )
            db.add(course_item)

    if bundle_data.implementation_package_items is not None:
        db.query(BundleImplementationPackageItem).filter(
            BundleImplementationPackageItem.bundle_id == bundle_uuid
        ).delete()

        for idx, ipi in enumerate(bundle_data.implementation_package_items):
            impl_uuid = uuid.UUID(ipi.implementation_package_id)
            impl_item = BundleImplementationPackageItem(
                bundle_id=bundle_uuid,
                implementation_package_id=impl_uuid,
                sort_order=idx,
                access_duration_days=ipi.access_duration_days,
            )
            db.add(impl_item)

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nieprawidłowy ID bundla"
        ) from None

    bundle = (
        db.query(Package)
        .filter(Package.id == bundle_uuid, Package.is_bundle == True)  # noqa: E712
        .first()
    )

    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Oferta bundlowa nie znaleziona"
        )

    purchase_count = (
        db.query(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            OrderItem.package_id == bundle_uuid,
            Order.status == OrderStatus.COMPLETED,
        )
        .count()
    )
    if purchase_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nie można usunąć oferty — {purchase_count} użytkowników dokonało zakupu",
        )

    bundle.is_published = False
    db.commit()

    return None
