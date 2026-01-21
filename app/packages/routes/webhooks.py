"""
Webhook handlers for payment providers (CRITICAL!).

These endpoints process payment confirmation webhooks from Stripe and PayU.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.models.order import Order, PaymentProvider
from app.packages.services.email_service import (
    send_purchase_confirmation_email,
    send_welcome_with_package_email,
)
from app.packages.services.order_service import OrderService
from app.packages.services.payment_service import PaymentServiceFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Handle Stripe webhook events.

    CRITICAL: This endpoint handles payment confirmations and triggers:
    - User creation (if new)
    - Package enrollment creation
    - Email sending

    Stripe docs: https://stripe.com/docs/webhooks
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    # Get raw payload
    payload = await request.body()

    try:
        # Verify webhook signature
        stripe_service = PaymentServiceFactory.get_service(PaymentProvider.STRIPE)
        event = await stripe_service.verify_webhook(payload, stripe_signature)

        # Handle checkout.session.completed event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            payment_intent_id = session["id"]

            logger.info(f"Processing Stripe payment: {payment_intent_id}")

            # Find order by payment_intent_id
            order = db.query(Order).filter(Order.payment_intent_id == payment_intent_id).first()

            if not order:
                logger.error(f"Order not found for payment_intent_id: {payment_intent_id}")
                return {"status": "error", "message": "Order not found"}

            # Process payment
            result = await _process_payment_webhook(order, db)

            return {"status": "success", "order_id": str(order.id)}

        # Other event types - acknowledge but don't process
        logger.info(f"Received Stripe event: {event['type']}")
        return {"status": "acknowledged"}

    except ValueError as e:
        logger.error(f"Stripe webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stripe webhook processing error: {e}")
        # Return 200 to prevent retries
        return {"status": "error", "message": str(e)}


@router.post("/payu")
async def payu_webhook(
    request: Request,
    openpayu_signature: str = Header(None, alias="OpenPayu-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Handle PayU webhook events.

    CRITICAL: This endpoint handles payment confirmations and triggers:
    - User creation (if new)
    - Package enrollment creation
    - Email sending

    PayU docs: https://developers.payu.com/en/restapi.html#notifications
    """
    if not openpayu_signature:
        raise HTTPException(status_code=400, detail="Missing PayU signature")

    # Get raw payload
    payload = await request.body()

    try:
        # Verify webhook signature
        payu_service = PaymentServiceFactory.get_service(PaymentProvider.PAYU)
        event = await payu_service.verify_webhook(payload, openpayu_signature)

        # Handle order status updates
        if "order" in event:
            order_data = event["order"]
            payment_intent_id = order_data.get("orderId")
            status = order_data.get("status")

            logger.info(f"Processing PayU payment: {payment_intent_id}, status: {status}")

            # Only process COMPLETED payments
            if status != "COMPLETED":
                return {"status": "acknowledged"}

            # Find order by payment_intent_id
            order = db.query(Order).filter(Order.payment_intent_id == payment_intent_id).first()

            if not order:
                logger.error(f"Order not found for payment_intent_id: {payment_intent_id}")
                return {"status": "error", "message": "Order not found"}

            # Process payment
            result = await _process_payment_webhook(order, db)

            return {"status": "success", "order_id": str(order.id)}

        # Other event types - acknowledge but don't process
        logger.info(f"Received PayU event: {event.get('type', 'unknown')}")
        return {"status": "acknowledged"}

    except ValueError as e:
        logger.error(f"PayU webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"PayU webhook processing error: {e}")
        # Return 200 to prevent retries
        return {"status": "error", "message": str(e)}


async def _process_payment_webhook(order: Order, db: Session) -> dict[str, str]:
    """
    Core webhook processing logic (shared by both Stripe and PayU).

    Steps:
    1. Check idempotency (webhook_processed flag)
    2. Process payment with OrderService (creates user + enrollments)
    3. Send appropriate email (welcome or confirmation)

    Returns:
        Status dictionary
    """
    order_service = OrderService(db)

    # Process payment (creates user + enrollments)
    result = await order_service.process_successful_payment(order)

    if result["status"] == "already_processed":
        logger.info(f"Order {order.id} already processed, skipping")
        return {"status": "already_processed"}

    # Send email
    user = result["user"]
    enrollments = result["enrollments"]
    is_new_user = result["is_new_user"]

    try:
        if is_new_user:
            # Send welcome email with password setup link
            reset_token = result["reset_token"]
            await send_welcome_with_package_email(
                name=user.name,
                email=user.email,
                order=order,
                enrollments=enrollments,
                reset_token=reset_token,
            )
            logger.info(f"Sent welcome email to {user.email}")
        else:
            # Send purchase confirmation email
            await send_purchase_confirmation_email(
                name=user.name,
                email=user.email,
                order=order,
                enrollments=enrollments,
            )
            logger.info(f"Sent purchase confirmation email to {user.email}")

    except Exception as e:
        # Log email errors but don't fail the webhook
        logger.error(f"Failed to send email: {e}")

    logger.info(
        f"Successfully processed order {order.order_number}: {len(enrollments)} enrollments created"
    )

    return {"status": "success"}
