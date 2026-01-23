"""
Order API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.db.session import get_db
from app.packages.models.order import Order
from app.packages.schemas.order import OrderListResponse, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/me", response_model=list[OrderListResponse])
def get_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrderListResponse]:
    """
    Get current user's orders.

    Returns:
        List of user's orders with basic info

    Requires:
        Authentication
    """
    orders = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return [
        OrderListResponse(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            total=order.total,
            currency=order.currency,
            created_at=order.created_at,
            items_count=len(order.items),
        )
        for order in orders
    ]


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_details(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """
    Get order details.

    Args:
        order_id: Order UUID

    Returns:
        Full order details including items

    Requires:
        Authentication (user must own the order)

    Raises:
        403: User doesn't own this order
        404: Order not found
    """
    import uuid

    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format") from None

    order = db.query(Order).filter(Order.id == order_uuid).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Check ownership
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return OrderResponse.from_orm(order)
