"""Mux video service for direct uploads and asset management."""

import logging
from typing import Literal

import mux_python
from mux_python.rest import ApiException

from app.core.config import settings

logger = logging.getLogger(__name__)


class MuxAssetStatus:
    """Mux asset status information."""

    def __init__(
        self,
        status: Literal["preparing", "ready", "errored"],
        playback_id: str | None = None,
        duration: float | None = None,
        error_message: str | None = None,
    ):
        self.status = status
        self.playback_id = playback_id
        self.duration = duration
        self.error_message = error_message


class MuxDirectUpload:
    """Mux direct upload information."""

    def __init__(self, upload_url: str, asset_id: str):
        self.upload_url = upload_url
        self.asset_id = asset_id


class MuxService:
    """Service for interacting with Mux API."""

    def __init__(self) -> None:
        """Initialize Mux service with credentials from settings."""
        self.configuration = mux_python.Configuration()
        self.configuration.username = settings.MUX_TOKEN_ID
        self.configuration.password = settings.MUX_TOKEN_SECRET

    def create_direct_upload(self) -> MuxDirectUpload:
        """
        Create a Mux direct upload URL.

        Returns:
            MuxDirectUpload with upload URL and asset ID

        Raises:
            ApiException: If Mux API call fails
        """
        with mux_python.ApiClient(self.configuration) as api_client:
            direct_uploads_api = mux_python.DirectUploadsApi(api_client)

            try:
                create_upload_request = mux_python.CreateUploadRequest(
                    cors_origin=settings.FRONTEND_URL,
                    new_asset_settings=mux_python.CreateAssetRequest(
                        playback_policy=[mux_python.PlaybackPolicy.PUBLIC],
                    ),
                )

                upload_response = direct_uploads_api.create_direct_upload(create_upload_request)

                upload_id = upload_response.data.id
                asset_id = (
                    upload_response.data.asset_id if upload_response.data.asset_id else upload_id
                )

                return MuxDirectUpload(
                    upload_url=upload_response.data.url,
                    asset_id=asset_id,
                )

            except ApiException as e:
                raise RuntimeError(f"Failed to create Mux direct upload: {e}") from e

    def get_asset_status(self, upload_or_asset_id: str) -> MuxAssetStatus:
        """
        Get the status of a Mux upload/asset.

        Args:
            upload_or_asset_id: The Mux upload ID or asset ID

        Returns:
            MuxAssetStatus with current status and metadata

        Raises:
            ApiException: If Mux API call fails
        """
        with mux_python.ApiClient(self.configuration) as api_client:
            direct_uploads_api = mux_python.DirectUploadsApi(api_client)
            assets_api = mux_python.AssetsApi(api_client)

            try:
                upload = direct_uploads_api.get_direct_upload(upload_or_asset_id)

                if upload.data.status != "asset_created":
                    return MuxAssetStatus(status="preparing")

                asset_id = upload.data.asset_id
                if not asset_id:
                    return MuxAssetStatus(status="preparing")

                asset = assets_api.get_asset(asset_id)

                mux_status = asset.data.status

                if mux_status == "ready":
                    playback_id = None
                    if asset.data.playback_ids:
                        playback_id = asset.data.playback_ids[0].id

                    duration = asset.data.duration

                    return MuxAssetStatus(
                        status="ready",
                        playback_id=playback_id,
                        duration=duration,
                    )
                elif mux_status == "errored":
                    error_messages = asset.data.errors.messages if asset.data.errors else []
                    error_message = "; ".join(error_messages) if error_messages else "Unknown error"

                    return MuxAssetStatus(
                        status="errored",
                        error_message=error_message,
                    )
                else:
                    return MuxAssetStatus(status="preparing")

            except ApiException as e:
                try:
                    asset = assets_api.get_asset(upload_or_asset_id)
                    mux_status = asset.data.status

                    if mux_status == "ready":
                        playback_id = None
                        if asset.data.playback_ids:
                            playback_id = asset.data.playback_ids[0].id
                        duration = asset.data.duration
                        return MuxAssetStatus(
                            status="ready",
                            playback_id=playback_id,
                            duration=duration,
                        )
                    elif mux_status == "errored":
                        error_messages = asset.data.errors.messages if asset.data.errors else []
                        error_message = (
                            "; ".join(error_messages) if error_messages else "Unknown error"
                        )
                        return MuxAssetStatus(
                            status="errored",
                            error_message=error_message,
                        )
                    else:
                        return MuxAssetStatus(status="preparing")
                except ApiException as e2:
                    raise RuntimeError(f"Failed to get Mux upload/asset status: {e}, {e2}") from e

    def delete_asset(self, asset_id: str) -> None:
        """
        Delete a Mux asset.

        Args:
            asset_id: The Mux asset ID

        Raises:
            ApiException: If Mux API call fails
        """
        with mux_python.ApiClient(self.configuration) as api_client:
            assets_api = mux_python.AssetsApi(api_client)

            try:
                assets_api.delete_asset(asset_id)
            except ApiException as e:
                logger.warning("Failed to delete Mux asset %s: %s", asset_id, e)


def get_mux_service() -> MuxService:
    """Get an instance of MuxService."""
    return MuxService()
