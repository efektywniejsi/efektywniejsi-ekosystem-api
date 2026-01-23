"""
Checkout API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.packages.schemas.checkout import (
    CheckoutInitiateRequest,
    CheckoutInitiateResponse,
    OrderStatusResponse,
)
from app.packages.services.checkout_service import CheckoutService

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post("/initiate", response_model=CheckoutInitiateResponse)
async def initiate_checkout(
    request: CheckoutInitiateRequest,
    db: Session = Depends(get_db),
) -> CheckoutInitiateResponse:
    """
    Initiate checkout process.

    Creates an order and returns payment URL for the selected provider.

    Steps:
    1. Validates all package IDs
    2. Creates Order with PENDING status
    3. Creates OrderItems
    4. Initiates payment session with provider
    5. Returns payment URL for redirect

    Request Body:
        - package_ids: List of package UUIDs to purchase
        - email: Customer email
        - name: Customer name
        - payment_provider: "stripe" or "payu"

    Returns:
        - payment_url: URL to redirect user for payment
        - order_id: Created order ID

    Raises:
        400: Invalid request (empty package_ids, invalid format)
        404: Package not found
        422: Validation error
    """
    checkout_service = CheckoutService(db)

    try:
        result = await checkout_service.initiate_checkout(
            package_ids=request.package_ids,
            email=request.email,
            name=request.name,
            payment_provider=request.payment_provider,
            success_url=f"{settings.FRONTEND_URL}/zamowienie/sukces",
            cancel_url=f"{settings.FRONTEND_URL}/zamowienie/anulowano",
        )

        import uuid

        return CheckoutInitiateResponse(
            payment_url=result["payment_url"],
            order_id=uuid.UUID(result["order_id"]),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)}") from e


@router.get("/order/{order_id}", response_model=OrderStatusResponse)
def get_order_status(
    order_id: str,
    db: Session = Depends(get_db),
) -> OrderStatusResponse:
    """
    Get order status.

    Used by frontend to poll order status after payment redirect.

    Args:
        order_id: Order UUID

    Returns:
        Order status information

    Raises:
        404: Order not found
    """
    checkout_service = CheckoutService(db)
    order = checkout_service.get_order_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderStatusResponse(
        order_id=order.id,
        order_number=order.order_number,
        status=order.status.value,
        total=order.total,
        currency=order.currency,
        webhook_processed=order.webhook_processed,
    )
