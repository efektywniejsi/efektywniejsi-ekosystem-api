"""Webhook endpoints for Mux events."""

import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.courses.models import Lesson

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_mux_signature(payload_bytes: bytes, signature_header: str | None) -> None:
    """Verify Mux webhook signature. Raises HTTPException if invalid."""
    if not settings.MUX_WEBHOOK_SECRET:
        logger.warning("MUX_WEBHOOK_SECRET not configured, skipping signature verification")
        return

    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Mux-Signature header",
        )

    # Mux signature format: t=<timestamp>,v1=<signature>
    parts = dict(part.split("=", 1) for part in signature_header.split(",") if "=" in part)
    timestamp = parts.get("t", "")
    expected_sig = parts.get("v1", "")

    if not timestamp or not expected_sig:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Mux-Signature format",
        )

    signed_payload = f"{timestamp}.{payload_bytes.decode()}"
    computed_sig = hmac.new(
        settings.MUX_WEBHOOK_SECRET.encode(),
        signed_payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )


@router.post("/mux/webhook", status_code=status.HTTP_200_OK)
async def handle_mux_webhook(request: Request) -> dict[str, str]:
    """
    Handle Mux webhook events.

    This endpoint receives notifications from Mux when video assets
    are ready, errored, or deleted.

    Events handled:
    - video.asset.ready: Video is processed and ready to play
    - video.asset.errored: Video processing failed
    - video.asset.deleted: Video asset was deleted
    """
    try:
        payload_bytes = await request.body()

        _verify_mux_signature(
            payload_bytes,
            request.headers.get("Mux-Signature"),
        )

        payload = await request.json()

        event_type = payload.get("type")
        data = payload.get("data", {})

        logger.info("Received Mux webhook: %s", event_type)

        if event_type == "video.asset.ready":
            asset_id = data.get("id")
            playback_ids = data.get("playback_ids", [])
            duration = data.get("duration")

            if asset_id:
                from app.db.session import SessionLocal

                db: Session = SessionLocal()
                try:
                    lesson = db.query(Lesson).filter(Lesson.mux_asset_id == asset_id).first()

                    if lesson and playback_ids:
                        lesson.mux_playback_id = playback_ids[0].get("id", "")
                        if duration:
                            lesson.duration_seconds = int(duration)
                        db.commit()
                        logger.info("Updated lesson %s with playback ID", lesson.id)

                finally:
                    db.close()

        elif event_type == "video.asset.errored":
            asset_id = data.get("id")
            logger.warning("Video asset %s failed processing", asset_id)

        elif event_type == "video.asset.deleted":
            asset_id = data.get("id")
            logger.info("Video asset %s was deleted", asset_id)

        return {"status": "received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error processing Mux webhook: %s", e, exc_info=True)
        return {"status": "error", "message": "Internal processing error"}
