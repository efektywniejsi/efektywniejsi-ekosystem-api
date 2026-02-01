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
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Brak sygnatury Stripe")

    payload = await request.body()

    try:
        stripe_service = PaymentServiceFactory.get_service(PaymentProvider.STRIPE)
        event = await stripe_service.verify_webhook(payload, stripe_signature)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            payment_intent_id = session["id"]

            logger.info(f"Processing Stripe payment: {payment_intent_id}")

            order = db.query(Order).filter(Order.payment_intent_id == payment_intent_id).first()

            if not order:
                logger.error(f"Order not found for payment_intent_id: {payment_intent_id}")
                return {"status": "error", "message": "Order not found"}

            await _process_payment_webhook(order, db)

            return {"status": "success", "order_id": str(order.id)}

        logger.info(f"Received Stripe event: {event['type']}")
        return {"status": "acknowledged"}

    except ValueError as e:
        logger.error(f"Stripe webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Stripe webhook processing error: {e}")
        # Return 200 to prevent retries from the payment provider
        return {"status": "error", "message": str(e)}


@router.post("/payu")
async def payu_webhook(
    request: Request,
    openpayu_signature: str = Header(None, alias="OpenPayu-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not openpayu_signature:
        raise HTTPException(status_code=400, detail="Brak sygnatury PayU")

    payload = await request.body()

    try:
        payu_service = PaymentServiceFactory.get_service(PaymentProvider.PAYU)
        event = await payu_service.verify_webhook(payload, openpayu_signature)

        if "order" in event:
            order_data = event["order"]
            payment_intent_id = order_data.get("orderId")
            payu_status = order_data.get("status")

            logger.info(f"Processing PayU payment: {payment_intent_id}, status: {payu_status}")

            if payu_status != "COMPLETED":
                return {"status": "acknowledged"}

            order = db.query(Order).filter(Order.payment_intent_id == payment_intent_id).first()

            if not order:
                logger.error(f"Order not found for payment_intent_id: {payment_intent_id}")
                return {"status": "error", "message": "Order not found"}

            await _process_payment_webhook(order, db)

            return {"status": "success", "order_id": str(order.id)}

        logger.info(f"Received PayU event: {event.get('type', 'unknown')}")
        return {"status": "acknowledged"}

    except ValueError as e:
        logger.error(f"PayU webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"PayU webhook processing error: {e}")
        # Return 200 to prevent retries from the payment provider
        return {"status": "error", "message": str(e)}


async def _process_payment_webhook(order: Order, db: Session) -> dict[str, str]:
    order_service = OrderService(db)

    result = await order_service.process_successful_payment(order)

    if result["status"] == "already_processed":
        logger.info(f"Order {order.id} already processed, skipping")
        return {"status": "already_processed"}

    user = result["user"]
    enrollments = result["enrollments"]
    is_new_user = result["is_new_user"]

    try:
        if is_new_user:
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
            await send_purchase_confirmation_email(
                name=user.name,
                email=user.email,
                order=order,
                enrollments=enrollments,
            )
            logger.info(f"Sent purchase confirmation email to {user.email}")

    except Exception as e:
        # Log but don't fail -- the payment was already processed successfully
        logger.error(f"Failed to send email: {e}")

    logger.info(
        f"Successfully processed order {order.order_number}: {len(enrollments)} enrollments created"
    )

    return {"status": "success"}
