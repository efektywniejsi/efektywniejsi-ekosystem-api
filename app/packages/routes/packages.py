"""
Package API endpoints.
"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.db.session import get_db
from app.packages.models.package import Package, PackageBundleItem
from app.packages.schemas.package import (
    PackageCreateRequest,
    PackageDetailResponse,
    PackageListResponse,
    PackageUpdateRequest,
    PackageWithChildrenResponse,
)

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_model=list[PackageListResponse])
def list_packages(
    category: str | None = Query(None, description="Filter by category"),
    is_featured: bool | None = Query(None, description="Filter by featured status"),
    db: Session = Depends(get_db),
) -> list[PackageListResponse]:
    """
    Get list of published packages (excludes bundles).

    Query Parameters:
        - category: Filter by category (optional)
        - is_featured: Filter by featured status (optional)

    Returns:
        List of packages with basic info
    """
    query = db.query(Package).filter(
        Package.is_published == True,  # noqa: E712
        Package.is_bundle == False,  # noqa: E712 - Exclude bundles
    )

    if category:
        query = query.filter(Package.category == category)

    if is_featured is not None:
        query = query.filter(Package.is_featured == is_featured)

    packages = query.order_by(Package.is_featured.desc(), Package.created_at.desc()).all()

    return [PackageListResponse.from_orm(pkg) for pkg in packages]


# Admin endpoints - require authentication


@router.get("/all", response_model=list[PackageListResponse])
def list_all_packages(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[PackageListResponse]:
    """
    Get all packages including unpublished (admin only).
    Excludes bundles - use /bundles/all for bundles.

    Returns:
        List of all packages
    """
    packages = (
        db.query(Package)
        .filter(Package.is_bundle == False)  # noqa: E712 - Exclude bundles
        .order_by(Package.created_at.desc())
        .all()
    )

    return [PackageListResponse.from_orm(pkg) for pkg in packages]


# Public endpoints with path parameters


@router.get("/{slug}", response_model=PackageDetailResponse)
def get_package_by_slug(
    slug: str,
    db: Session = Depends(get_db),
) -> PackageDetailResponse:
    """
    Get package details by slug.

    Args:
        slug: Package slug

    Returns:
        Package details including processes and bundle items

    Raises:
        404: Package not found or not published
    """
    package = (
        db.query(Package)
        .filter(Package.slug == slug, Package.is_published == True)  # noqa: E712
        .first()
    )

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    return PackageDetailResponse.from_orm(package)


@router.get("/{package_id}/bundle", response_model=PackageWithChildrenResponse)
def get_package_bundle_contents(
    package_id: str,
    db: Session = Depends(get_db),
) -> PackageWithChildrenResponse:
    """
    Get bundle contents (child packages).

    Args:
        package_id: Package UUID

    Returns:
        Bundle package with list of child packages

    Raises:
        404: Package not found or not a bundle
    """
    import uuid

    try:
        package_uuid = uuid.UUID(package_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid package ID format") from None

    package = (
        db.query(Package)
        .filter(
            Package.id == package_uuid,
            Package.is_published == True,  # noqa: E712
            Package.is_bundle == True,  # noqa: E712
        )
        .first()
    )

    if not package:
        raise HTTPException(status_code=404, detail="Bundle package not found")

    # Get child packages
    bundle_items = (
        db.query(PackageBundleItem)
        .filter(PackageBundleItem.bundle_id == package_uuid)
        .order_by(PackageBundleItem.sort_order)
        .all()
    )

    child_packages = []
    for bundle_item in bundle_items:
        child_pkg = db.query(Package).filter(Package.id == bundle_item.child_package_id).first()
        if child_pkg:
            child_packages.append(PackageListResponse.from_orm(child_pkg))

    tools = json.loads(package.tools) if isinstance(package.tools, str) else package.tools

    return PackageWithChildrenResponse(
        id=package.id,
        slug=package.slug,
        title=package.title,
        description=package.description,
        category=package.category,
        price=package.price,
        original_price=package.original_price,
        currency=package.currency,
        difficulty=package.difficulty,
        total_time_saved=package.total_time_saved,
        tools=tools,
        child_packages=child_packages,
    )


@router.post(
    "",
    response_model=PackageDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_package(
    package_data: PackageCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> PackageDetailResponse:
    """
    Create a new package (admin only).

    Args:
        package_data: Package creation data

    Returns:
        Created package details

    Raises:
        400: Slug already exists
    """
    # Check if slug already exists
    existing = db.query(Package).filter(Package.slug == package_data.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Package with slug '{package_data.slug}' already exists",
        )

    # Create package
    new_package = Package(
        slug=package_data.slug,
        title=package_data.title,
        description=package_data.description,
        category=package_data.category,
        price=package_data.price,
        original_price=package_data.original_price,
        currency=package_data.currency,
        difficulty=package_data.difficulty,
        total_time_saved=package_data.total_time_saved,
        tools=json.dumps(package_data.tools),  # Convert list to JSON string
        video_url=package_data.video_url,
        is_published=True,  # Auto-publish on creation
        is_featured=package_data.is_featured,
        is_bundle=package_data.is_bundle,  # Can be True or False
    )

    db.add(new_package)
    db.flush()  # Get ID before adding bundle items

    # If it's a bundle, add child packages
    if package_data.is_bundle and package_data.package_ids:
        for idx, package_id in enumerate(package_data.package_ids):
            try:
                pkg_uuid = uuid.UUID(package_id)
            except ValueError:
                raise HTTPException(400, f"Invalid package ID: {package_id}") from None

            # Verify child package exists
            child_pkg = db.query(Package).filter(Package.id == pkg_uuid).first()
            if not child_pkg:
                raise HTTPException(404, f"Package {package_id} not found")

            # Don't allow nested bundles
            if child_pkg.is_bundle:
                raise HTTPException(400, f"Cannot add bundle '{child_pkg.title}' to another bundle")

            # Create bundle item relationship
            bundle_item = PackageBundleItem(
                bundle_id=new_package.id,
                child_package_id=pkg_uuid,
                sort_order=idx,
            )
            db.add(bundle_item)

    db.commit()
    db.refresh(new_package)

    return PackageDetailResponse.from_orm(new_package)


@router.patch("/{package_id}", response_model=PackageDetailResponse)
def update_package(
    package_id: str,
    package_data: PackageUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> PackageDetailResponse:
    """
    Update package (admin only).

    Args:
        package_id: Package UUID
        package_data: Package update data

    Returns:
        Updated package details

    Raises:
        400: Invalid package ID
        404: Package not found
    """
    try:
        package_uuid = uuid.UUID(package_id)
    except ValueError:
        raise HTTPException(400, "Invalid package ID") from None

    package = db.query(Package).filter(Package.id == package_uuid).first()

    if not package:
        raise HTTPException(404, "Package not found")

    # Update fields
    if package_data.title is not None:
        package.title = package_data.title
    if package_data.description is not None:
        package.description = package_data.description
    if package_data.category is not None:
        package.category = package_data.category
    if package_data.price is not None:
        package.price = package_data.price
    if package_data.original_price is not None:
        package.original_price = package_data.original_price
    if package_data.difficulty is not None:
        package.difficulty = package_data.difficulty
    if package_data.total_time_saved is not None:
        package.total_time_saved = package_data.total_time_saved
    if package_data.tools is not None:
        package.tools = json.dumps(package_data.tools)
    if package_data.video_url is not None:
        package.video_url = package_data.video_url
    if package_data.is_featured is not None:
        package.is_featured = package_data.is_featured

    # Update child packages if this is a bundle
    if package.is_bundle and package_data.package_ids is not None:
        # Remove old bundle items
        db.query(PackageBundleItem).filter(PackageBundleItem.bundle_id == package_uuid).delete()

        # Add new bundle items
        for idx, package_id in enumerate(package_data.package_ids):
            try:
                pkg_uuid = uuid.UUID(package_id)
            except ValueError:
                raise HTTPException(400, f"Invalid package ID: {package_id}") from None

            child_pkg = db.query(Package).filter(Package.id == pkg_uuid).first()
            if not child_pkg:
                raise HTTPException(404, f"Package {package_id} not found")

            if child_pkg.is_bundle:
                raise HTTPException(400, f"Cannot add bundle '{child_pkg.title}' to another bundle")

            bundle_item = PackageBundleItem(
                bundle_id=package_uuid,
                child_package_id=pkg_uuid,
                sort_order=idx,
            )
            db.add(bundle_item)

    db.commit()
    db.refresh(package)

    return PackageDetailResponse.from_orm(package)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
    package_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    """
    Delete package (admin only).

    Soft delete: sets is_published=False instead of actual deletion.

    Args:
        package_id: Package UUID

    Raises:
        400: Invalid package ID
        404: Package not found
    """
    try:
        package_uuid = uuid.UUID(package_id)
    except ValueError:
        raise HTTPException(400, "Invalid package ID") from None

    package = db.query(Package).filter(Package.id == package_uuid).first()

    if not package:
        raise HTTPException(404, "Package not found")

    # Soft delete
    package.is_published = False
    db.commit()

    return None
