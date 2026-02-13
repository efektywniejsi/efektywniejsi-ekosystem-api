"""Sales Windows API routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.db.session import get_db
from app.packages.models import SalesWindow, SalesWindowStatus
from app.packages.schemas import (
    ActiveSalesWindowResponse,
    SalesWindowCreate,
    SalesWindowDetailResponse,
    SalesWindowListResponse,
    SalesWindowResponse,
    SalesWindowUpdate,
    SalesWindowUpdateResponse,
)
from app.packages.services.sales_window import SalesWindowService

router = APIRouter()


# Public endpoints - no authentication required


@router.get("/active", response_model=ActiveSalesWindowResponse, response_model_by_alias=True)
async def get_active_sales_window(
    db: Session = Depends(get_db),
) -> ActiveSalesWindowResponse:
    """
    Get the currently active sales window (public endpoint).

    Returns the sales window that is:
    - Status is 'active'
    - Current time is between starts_at and ends_at

    Returns:
        ActiveSalesWindowResponse with salesWindow or None
    """
    sales_window = SalesWindowService.get_active_sales_window(db)

    if sales_window:
        return ActiveSalesWindowResponse(
            salesWindow=SalesWindowResponse.model_validate(sales_window)
        )

    return ActiveSalesWindowResponse(salesWindow=None)


@router.get("/next", response_model=ActiveSalesWindowResponse, response_model_by_alias=True)
async def get_next_sales_window(
    db: Session = Depends(get_db),
) -> ActiveSalesWindowResponse:
    """
    Get the next upcoming sales window (public endpoint).

    Returns the next sales window that:
    - Status is 'upcoming'
    - starts_at is in the future

    Returns:
        ActiveSalesWindowResponse with salesWindow or None
    """
    now = datetime.now(UTC)

    sales_window = (
        db.query(SalesWindow)
        .filter(
            and_(
                SalesWindow.status == "upcoming",
                SalesWindow.starts_at > now,
            )
        )
        .order_by(SalesWindow.starts_at.asc())
        .first()
    )

    if sales_window:
        return ActiveSalesWindowResponse(
            salesWindow=SalesWindowResponse.model_validate(sales_window)
        )

    return ActiveSalesWindowResponse(salesWindow=None)


# Admin-only endpoints - require admin role


@router.get("", response_model=SalesWindowListResponse, response_model_by_alias=True)
async def get_all_sales_windows(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> SalesWindowListResponse:
    """
    Get all sales windows (admin only).

    Requires admin role.

    Returns:
        SalesWindowListResponse with list of all sales windows
    """
    sales_windows = SalesWindowService.get_all_sales_windows(db)

    return SalesWindowListResponse(
        salesWindows=[SalesWindowResponse.model_validate(sw) for sw in sales_windows]
    )


@router.post(
    "",
    response_model=SalesWindowDetailResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_sales_window(
    window_data: SalesWindowCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> SalesWindowDetailResponse:
    """
    Create a new sales window (admin only).

    Validation rules:
    - ID must be unique
    - endsAt must be after startsAt
    - Only one sales window can be 'active' at a time
    - bundleIds must not be empty

    Returns:
        SalesWindowDetailResponse with created sales window

    Raises:
        HTTPException: 400 if validation fails
    """
    # Check if ID already exists
    existing = SalesWindowService.get_sales_window_by_id(db, window_data.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sales window with id '{window_data.id}' already exists",
        )

    # If creating as 'active', check no other window is active
    if window_data.status == "active":
        existing_active = db.query(SalesWindow).filter(SalesWindow.status == "active").first()

        if existing_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot create active window: Another sales window "
                    f"'{existing_active.name}' is already active. "
                    f"Please close it first."
                ),
            )

    # Create new sales window
    new_window = SalesWindow(
        id=window_data.id,
        name=window_data.name,
        status=SalesWindowStatus(window_data.status),
        starts_at=window_data.startsAt,
        ends_at=window_data.endsAt,
        landing_page_config=window_data.landingPage,
        early_bird_config=window_data.earlyBird,
        bundle_ids=window_data.bundleIds,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by=admin.id,
        updated_by=admin.id,
    )

    db.add(new_window)
    db.commit()
    db.refresh(new_window)

    return SalesWindowDetailResponse(salesWindow=SalesWindowResponse.model_validate(new_window))


@router.get(
    "/{window_id}",
    response_model=SalesWindowDetailResponse,
    response_model_by_alias=True,
)
async def get_sales_window(
    window_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> SalesWindowDetailResponse:
    """
    Get a single sales window by ID (admin only).

    Requires admin role.

    Args:
        window_id: Sales window ID

    Returns:
        SalesWindowDetailResponse with the sales window

    Raises:
        HTTPException: 404 if sales window not found
    """
    sales_window = SalesWindowService.get_sales_window_by_id(db, window_id)

    if not sales_window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales window with id '{window_id}' not found",
        )

    return SalesWindowDetailResponse(salesWindow=SalesWindowResponse.model_validate(sales_window))


@router.patch(
    "/{window_id}",
    response_model=SalesWindowUpdateResponse,
    response_model_by_alias=True,
)
async def update_sales_window(
    window_id: str,
    update_data: SalesWindowUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> SalesWindowUpdateResponse:
    """
    Update a sales window (admin only).

    Allows updating:
    - status (upcoming, active, closed)
    - startsAt (start date/time)
    - endsAt (end date/time)

    Validation rules:
    - endsAt must be after startsAt
    - Only one sales window can be 'active' at a time

    Requires admin role.

    Args:
        window_id: Sales window ID
        update_data: Fields to update
        admin: Current admin user (from dependency)

    Returns:
        SalesWindowUpdateResponse with updated sales window and success message

    Raises:
        HTTPException: 404 if sales window not found
        HTTPException: 400 if validation fails
    """
    # Fetch the sales window
    sales_window = SalesWindowService.get_sales_window_by_id(db, window_id)

    if not sales_window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales window with id '{window_id}' not found",
        )

    # Track if any fields are being updated
    updated_fields: list[str] = []

    # Update status
    if update_data.status is not None:
        # If setting to 'active', check no other window is active
        if update_data.status == "active" and sales_window.status != "active":
            existing_active = (
                db.query(SalesWindow)
                .filter(
                    and_(
                        SalesWindow.status == "active",
                        SalesWindow.id != window_id,
                    )
                )
                .first()
            )

            if existing_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Cannot activate: Another sales window "
                        f"'{existing_active.name}' is already active. "
                        f"Please close it first."
                    ),
                )

        sales_window.status = SalesWindowStatus(update_data.status)
        updated_fields.append("status")

    # Update startsAt
    if update_data.startsAt is not None:
        sales_window.starts_at = update_data.startsAt
        updated_fields.append("startsAt")

    # Update endsAt
    if update_data.endsAt is not None:
        sales_window.ends_at = update_data.endsAt
        updated_fields.append("endsAt")

    # Validate dates after all updates
    if sales_window.ends_at <= sales_window.starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="endsAt must be after startsAt",
        )

    # Update audit fields
    sales_window.updated_at = datetime.now(UTC)
    sales_window.updated_by = admin.id

    # Commit changes
    db.commit()
    db.refresh(sales_window)

    # Build success message
    fields_str = ", ".join(updated_fields) if updated_fields else "no fields"
    message = f"Sales window updated successfully. Updated fields: {fields_str}"

    return SalesWindowUpdateResponse(
        salesWindow=SalesWindowResponse.model_validate(sales_window),
        message=message,
    )


@router.delete(
    "/{window_id}",
    response_model=SalesWindowDetailResponse,
    response_model_by_alias=True,
)
async def delete_sales_window(
    window_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> SalesWindowDetailResponse:
    """
    Delete (close) a sales window (admin only).

    Sets status to 'closed' (soft delete).

    Args:
        window_id: Sales window ID

    Returns:
        SalesWindowDetailResponse with closed sales window

    Raises:
        HTTPException: 404 if sales window not found
    """
    sales_window = SalesWindowService.get_sales_window_by_id(db, window_id)

    if not sales_window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales window with id '{window_id}' not found",
        )

    # Set status to closed
    sales_window.status = "closed"
    sales_window.updated_at = datetime.now(UTC)
    sales_window.updated_by = admin.id

    db.commit()
    db.refresh(sales_window)

    return SalesWindowDetailResponse(salesWindow=SalesWindowResponse.model_validate(sales_window))
