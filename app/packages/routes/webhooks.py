"""Payment webhook routes using abstract handler pattern."""

import logging

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.services.payu_webhook_handler import get_payu_handler
from app.packages.services.stripe_webhook_handler import get_stripe_handler
from app.packages.services.webhook_handler import WebhookResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _result_to_response(result: WebhookResult) -> dict[str, str]:
    """Convert WebhookResult to API response dict."""
    response: dict[str, str] = {"status": result.status}
    if result.order_id:
        response["order_id"] = result.order_id
    if result.message:
        response["message"] = result.message
    return response


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Handle Stripe payment webhooks."""
    payload = await request.body()
    handler = get_stripe_handler(db)
    result = await handler.process(payload, stripe_signature or "")
    return _result_to_response(result)


@router.post("/payu")
async def payu_webhook(
    request: Request,
    openpayu_signature: str = Header(None, alias="OpenPayu-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Handle PayU payment webhooks."""
    payload = await request.body()
    handler = get_payu_handler(db)
    result = await handler.process(payload, openpayu_signature or "")
    return _result_to_response(result)
