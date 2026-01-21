"""
Package API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.models.package import Package, PackageBundleItem
from app.packages.schemas.package import (
    PackageDetailResponse,
    PackageListResponse,
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
    Get list of published packages.

    Query Parameters:
        - category: Filter by category (optional)
        - is_featured: Filter by featured status (optional)

    Returns:
        List of packages with basic info
    """
    query = db.query(Package).filter(Package.is_published == True)  # noqa: E712

    if category:
        query = query.filter(Package.category == category)

    if is_featured is not None:
        query = query.filter(Package.is_featured == is_featured)

    packages = query.order_by(Package.is_featured.desc(), Package.created_at.desc()).all()

    return [PackageListResponse.from_orm(pkg) for pkg in packages]


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
        raise HTTPException(status_code=400, detail="Invalid package ID format")

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

    import json

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
