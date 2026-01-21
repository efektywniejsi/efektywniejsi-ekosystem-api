"""Admin routes for video upload and lesson management."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.courses.models import Lesson
from app.courses.services.mux_service import MuxService, get_mux_service
from app.db.session import get_db

router = APIRouter()


class UploadURLResponse(BaseModel):
    """Response with Mux direct upload URL."""

    upload_url: str
    asset_id: str


class UploadStatusResponse(BaseModel):
    """Response with video upload/processing status."""

    status: Literal["preparing", "ready", "errored"]
    playback_id: str | None = None
    duration: float | None = None
    error_message: str | None = None


@router.post(
    "/lessons/{lesson_id}/upload-url",
    response_model=UploadURLResponse,
    status_code=status.HTTP_200_OK,
)
async def create_upload_url(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    mux_service: MuxService = Depends(get_mux_service),
) -> UploadURLResponse:
    """
    Create a Mux direct upload URL for a lesson.

    This endpoint generates a pre-signed URL that the frontend can use
    to upload video directly to Mux.
    """
    # Check if lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    # Delete old asset if it exists (skip placeholders)
    if lesson.mux_asset_id and not lesson.mux_asset_id.startswith("PLACEHOLDER_"):
        try:
            mux_service.delete_asset(lesson.mux_asset_id)
        except Exception as e:
            # Log but continue - old asset might already be deleted
            print(f"Warning: Could not delete old Mux asset: {e}")

    # Create new direct upload
    try:
        upload = mux_service.create_direct_upload()

        # Store the asset ID in the lesson
        lesson.mux_asset_id = upload.asset_id
        lesson.mux_playback_id = None  # Clear old playback_id
        db.commit()

        print(f"Created upload URL for lesson {lesson_id}, asset_id: {upload.asset_id}")

        return UploadURLResponse(
            upload_url=upload.upload_url,
            asset_id=upload.asset_id,
        )

    except Exception as e:
        db.rollback()  # Rollback on error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create upload URL: {str(e)}",
        ) from e


@router.get(
    "/lessons/{lesson_id}/upload-status",
    response_model=UploadStatusResponse,
)
async def get_upload_status(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    mux_service: MuxService = Depends(get_mux_service),
) -> UploadStatusResponse:
    """
    Get the status of video upload/processing for a lesson.

    Returns the current Mux asset status and updates the lesson
    with playback ID and duration when ready.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    print(f"Checking upload status for lesson {lesson_id}, mux_asset_id: {lesson.mux_asset_id}")

    if not lesson.mux_asset_id or lesson.mux_asset_id.startswith("PLACEHOLDER_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No video upload in progress for this lesson",
        )

    try:
        asset_status = mux_service.get_asset_status(lesson.mux_asset_id)

        # If asset is ready, update lesson with playback ID and duration
        if asset_status.status == "ready" and asset_status.playback_id:
            lesson.mux_playback_id = asset_status.playback_id
            if asset_status.duration:
                lesson.duration_seconds = int(asset_status.duration)
            db.commit()
            print(f"Updated lesson {lesson_id} with playback_id: {asset_status.playback_id}")

        return UploadStatusResponse(
            status=asset_status.status,
            playback_id=asset_status.playback_id,
            duration=asset_status.duration,
            error_message=asset_status.error_message,
        )

    except Exception as e:
        print(f"Error getting upload status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get upload status: {str(e)}",
        ) from e


@router.delete(
    "/lessons/{lesson_id}/video",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_lesson_video(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    mux_service: MuxService = Depends(get_mux_service),
) -> None:
    """Delete the video associated with a lesson."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    if lesson.mux_asset_id:
        try:
            mux_service.delete_asset(lesson.mux_asset_id)
        except Exception as e:
            print(f"Warning: Could not delete Mux asset: {e}")

        # Clear video fields
        lesson.mux_asset_id = None
        lesson.mux_playback_id = ""
        lesson.duration_seconds = 0
        db.commit()
