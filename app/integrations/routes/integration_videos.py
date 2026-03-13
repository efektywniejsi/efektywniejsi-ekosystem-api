from typing import Literal
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.courses.services.mux_service import MuxService, get_mux_service
from app.db.session import get_db
from app.integrations.models.integration import Integration

logger = structlog.get_logger(__name__)

router = APIRouter()


class UploadURLResponse(BaseModel):
    upload_url: str
    asset_id: str


class UploadStatusResponse(BaseModel):
    status: Literal["waiting_for_upload", "preparing", "ready", "errored"]
    playback_id: str | None = None
    duration: float | None = None
    error_message: str | None = None


@router.post(
    "/integrations/{integration_id}/upload-url",
    response_model=UploadURLResponse,
    status_code=status.HTTP_200_OK,
)
async def create_integration_upload_url(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    mux_service: MuxService = Depends(get_mux_service),
) -> UploadURLResponse:
    """Create a Mux direct upload URL for an integration video."""
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integracja nie znaleziona",
        )

    # Delete old asset if it exists
    if integration.mux_asset_id:
        try:
            mux_service.delete_asset(integration.mux_asset_id)
        except Exception as e:
            logger.warning("Could not delete old Mux asset: %s", e)

    try:
        upload = mux_service.create_direct_upload()

        integration.mux_asset_id = upload.asset_id
        integration.mux_playback_id = None
        db.commit()

        logger.info(
            "Created upload URL for integration %s, asset_id: %s",
            integration_id,
            upload.asset_id,
        )

        return UploadURLResponse(
            upload_url=upload.upload_url,
            asset_id=upload.asset_id,
        )

    except Exception as e:
        db.rollback()
        logger.error("Failed to create upload URL: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nie udało się utworzyć URL przesyłania",
        ) from e


@router.get(
    "/integrations/{integration_id}/upload-status",
    response_model=UploadStatusResponse,
)
async def get_integration_upload_status(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    mux_service: MuxService = Depends(get_mux_service),
) -> UploadStatusResponse:
    """Get the status of video upload/processing for an integration."""
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integracja nie znaleziona",
        )

    if not integration.mux_asset_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brak trwającego przesyłania wideo dla tej integracji",
        )

    try:
        asset_status = mux_service.get_asset_status(integration.mux_asset_id)

        if asset_status.status == "ready" and asset_status.playback_id:
            integration.mux_playback_id = asset_status.playback_id
            db.commit()
            logger.info(
                "Updated integration %s with playback_id: %s",
                integration_id,
                asset_status.playback_id,
            )

        return UploadStatusResponse(
            status=asset_status.status,
            playback_id=asset_status.playback_id,
            duration=asset_status.duration,
            error_message=asset_status.error_message,
        )

    except Exception as e:
        logger.error("Error getting upload status: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nie udało się pobrać statusu przesyłania",
        ) from e


@router.delete(
    "/integrations/{integration_id}/video",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_integration_video(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    mux_service: MuxService = Depends(get_mux_service),
) -> None:
    """Delete the video associated with an integration."""
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integracja nie znaleziona",
        )

    if integration.mux_asset_id:
        try:
            mux_service.delete_asset(integration.mux_asset_id)
        except Exception as e:
            logger.warning("Could not delete Mux asset: %s", e)

    integration.mux_asset_id = None
    integration.mux_playback_id = None
    db.commit()
