import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.packages.schemas.checkout import (
    CheckoutInitiateRequest,
    CheckoutInitiateResponse,
    OrderStatusResponse,
)
from app.packages.services.checkout_service import CheckoutService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post("/initiate", response_model=CheckoutInitiateResponse)
@limiter.limit("10/minute")
async def initiate_checkout(
    request: Request,
    checkout_request: CheckoutInitiateRequest,
    db: Session = Depends(get_db),
) -> CheckoutInitiateResponse:
    checkout_service = CheckoutService(db)

    try:
        client_ip = request.client.host if request.client else "127.0.0.1"

        result = await checkout_service.initiate_checkout(
            package_ids=checkout_request.package_ids,
            email=checkout_request.email,
            name=checkout_request.name,
            payment_provider=checkout_request.payment_provider,
            success_url=f"{settings.FRONTEND_URL}/zamowienie/sukces",
            cancel_url=f"{settings.FRONTEND_URL}/zamowienie/anulowano",
            customer_ip=client_ip,
            wants_invoice=checkout_request.wants_invoice,
            buyer_tax_no=checkout_request.buyer_tax_no,
            buyer_company_name=checkout_request.buyer_company_name,
            buyer_street=checkout_request.buyer_street,
            buyer_post_code=checkout_request.buyer_post_code,
            buyer_city=checkout_request.buyer_city,
        )

        return CheckoutInitiateResponse(
            payment_url=result["payment_url"],
            order_id=uuid.UUID(result["order_id"]),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Checkout failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Wystąpił błąd wewnętrzny") from e


@router.get("/order/{order_id}", response_model=OrderStatusResponse)
@limiter.limit("30/minute")
async def get_order_status(
    request: Request,
    order_id: str,
    db: Session = Depends(get_db),
) -> OrderStatusResponse:
    """Used by frontend to poll order status after payment redirect.

    Note: Invoice is sent automatically via Fakturownia email after payment.
    """
    checkout_service = CheckoutService(db)
    order = checkout_service.get_order_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Zamówienie nie znalezione")

    return OrderStatusResponse(
        order_id=order.id,
        order_number=order.order_number,
        status=order.status.value,
        total=order.total,
        currency=order.currency,
        webhook_processed=order.webhook_processed,
    )
