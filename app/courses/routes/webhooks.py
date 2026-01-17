"""Webhook endpoints for Mux events."""

from fastapi import APIRouter, Request, status
from sqlalchemy.orm import Session

from app.courses.models import Lesson

router = APIRouter()


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
        payload = await request.json()

        event_type = payload.get("type")
        data = payload.get("data", {})

        # Log the event
        print(f"Received Mux webhook: {event_type}")

        # Handle different event types
        if event_type == "video.asset.ready":
            asset_id = data.get("id")
            playback_ids = data.get("playback_ids", [])
            duration = data.get("duration")

            if asset_id:
                # Update lesson with playback ID and duration
                # Note: This uses synchronous DB access - in production, consider using async
                from app.db.session import SessionLocal

                db: Session = SessionLocal()
                try:
                    lesson = db.query(Lesson).filter(Lesson.mux_asset_id == asset_id).first()

                    if lesson and playback_ids:
                        lesson.mux_playback_id = playback_ids[0].get("id", "")
                        if duration:
                            lesson.duration_seconds = int(duration)
                        db.commit()
                        print(f"Updated lesson {lesson.id} with playback ID")

                finally:
                    db.close()

        elif event_type == "video.asset.errored":
            asset_id = data.get("id")
            print(f"Video asset {asset_id} failed processing")

        elif event_type == "video.asset.deleted":
            asset_id = data.get("id")
            print(f"Video asset {asset_id} was deleted")

        return {"status": "received"}

    except Exception as e:
        print(f"Error processing Mux webhook: {e}")
        return {"status": "error", "message": str(e)}
