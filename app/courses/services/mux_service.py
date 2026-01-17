"""Mux video service for direct uploads and asset management."""

from typing import Literal

import mux_python
from mux_python.rest import ApiException

from app.core.config import settings


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
                # Create a direct upload with MP4 standard input
                create_upload_request = mux_python.CreateUploadRequest(
                    cors_origin="*",
                    new_asset_settings=mux_python.CreateAssetRequest(
                        playback_policy=[mux_python.PlaybackPolicy.PUBLIC],
                    ),
                )

                upload_response = direct_uploads_api.create_direct_upload(create_upload_request)

                return MuxDirectUpload(
                    upload_url=upload_response.data.url,
                    asset_id=upload_response.data.asset_id or "",
                )

            except ApiException as e:
                raise RuntimeError(f"Failed to create Mux direct upload: {e}") from e

    def get_asset_status(self, asset_id: str) -> MuxAssetStatus:
        """
        Get the status of a Mux asset.

        Args:
            asset_id: The Mux asset ID

        Returns:
            MuxAssetStatus with current status and metadata

        Raises:
            ApiException: If Mux API call fails
        """
        with mux_python.ApiClient(self.configuration) as api_client:
            assets_api = mux_python.AssetsApi(api_client)

            try:
                asset = assets_api.get_asset(asset_id)

                # Map Mux status to our status
                mux_status = asset.data.status
                if mux_status == "ready":
                    # Get playback ID (first public one)
                    playback_id = None
                    if asset.data.playback_ids:
                        playback_id = asset.data.playback_ids[0].id

                    # Duration is in seconds
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
                    # preparing or other status
                    return MuxAssetStatus(status="preparing")

            except ApiException as e:
                raise RuntimeError(f"Failed to get Mux asset status: {e}") from e

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
                # Log but don't fail - asset might already be deleted
                print(f"Warning: Failed to delete Mux asset {asset_id}: {e}")


def get_mux_service() -> MuxService:
    """Get an instance of MuxService."""
    return MuxService()
