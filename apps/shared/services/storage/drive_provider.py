"""
Google Drive storage provider

Enables seamless integration with user's Google Drive.

Features:
- Upload/download files to user's Drive
- Create folders for organization
- Watch folders for new file uploads
- Real-time webhook notifications

This is the core of the "drop file in Drive" UX.
"""

from typing import Optional, BinaryIO, List
from datetime import datetime
import mimetypes

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from io import BytesIO

from apps.shared.services.storage.base import StorageProvider, StorageFile
from apps.shared.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleDriveProvider(StorageProvider):
    """
    Google Drive storage provider.

    Requires OAuth credentials for accessing user's Drive.

    Usage:
        # Create provider with user's OAuth tokens
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

        provider = GoogleDriveProvider(credentials)
        file = await provider.upload_file(data, "result.png", folder_id="...")
    """

    def __init__(self, credentials: Credentials):
        """
        Initialize Google Drive client.

        Args:
            credentials: OAuth2 credentials for user's Drive
        """
        self.service = build("drive", "v3", credentials=credentials)
        self.credentials = credentials

        logger.info("drive_provider_initialized")

    async def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        mime_type: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> StorageFile:
        """Upload file to Google Drive."""
        # Infer MIME type if not provided
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_name)
            mime_type = mime_type or "application/octet-stream"

        # Build file metadata
        file_metadata = {"name": file_name}

        if folder_id:
            file_metadata["parents"] = [folder_id]

        # Create media upload
        media = MediaIoBaseUpload(file_data, mimetype=mime_type, resumable=True)

        try:
            # Upload to Drive
            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, name, size, mimeType, createdTime, modifiedTime, parents, webViewLink, thumbnailLink",
                )
                .execute()
            )

            logger.info(
                "drive_file_uploaded",
                file_id=file.get("id"),
                file_name=file.get("name"),
                size=file.get("size"),
            )

            return StorageFile(
                id=file.get("id"),
                name=file.get("name"),
                size=int(file.get("size", 0)),
                mime_type=file.get("mimeType"),
                created_at=self._parse_datetime(file.get("createdTime")),
                modified_at=self._parse_datetime(file.get("modifiedTime")),
                parent_id=file.get("parents", [None])[0],
                url=file.get("webViewLink"),
                thumbnail_url=file.get("thumbnailLink"),
            )

        except HttpError as e:
            logger.error(
                "drive_upload_failed",
                file_name=file_name,
                error=str(e),
                exc_info=True,
            )
            raise

    async def download_file(self, file_id: str) -> bytes:
        """Download file from Google Drive."""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = BytesIO()

            downloader = MediaIoBaseDownload(file_buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(
                        "drive_download_progress",
                        file_id=file_id,
                        progress=int(status.progress() * 100),
                    )

            logger.info("drive_file_downloaded", file_id=file_id)

            file_buffer.seek(0)
            return file_buffer.read()

        except HttpError as e:
            logger.error(
                "drive_download_failed",
                file_id=file_id,
                error=str(e),
            )
            raise

    async def get_file(self, file_id: str) -> StorageFile:
        """Get file metadata from Google Drive."""
        try:
            file = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, size, mimeType, createdTime, modifiedTime, parents, webViewLink, thumbnailLink",
                )
                .execute()
            )

            return StorageFile(
                id=file.get("id"),
                name=file.get("name"),
                size=int(file.get("size", 0)),
                mime_type=file.get("mimeType"),
                created_at=self._parse_datetime(file.get("createdTime")),
                modified_at=self._parse_datetime(file.get("modifiedTime")),
                parent_id=file.get("parents", [None])[0],
                url=file.get("webViewLink"),
                thumbnail_url=file.get("thumbnailLink"),
            )

        except HttpError as e:
            logger.error(
                "drive_get_file_failed",
                file_id=file_id,
                error=str(e),
            )
            raise

    async def delete_file(self, file_id: str) -> bool:
        """Delete file from Google Drive."""
        try:
            self.service.files().delete(fileId=file_id).execute()

            logger.info("drive_file_deleted", file_id=file_id)

            return True

        except HttpError as e:
            logger.error(
                "drive_delete_failed",
                file_id=file_id,
                error=str(e),
            )
            return False

    async def list_files(
        self,
        folder_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[StorageFile]:
        """List files in Google Drive."""
        try:
            # Build query
            query_parts = []

            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")

            if mime_type:
                if "*" in mime_type:
                    # Handle wildcard MIME types (e.g., "image/*")
                    base_type = mime_type.split("/")[0]
                    query_parts.append(f"mimeType contains '{base_type}/'")
                else:
                    query_parts.append(f"mimeType = '{mime_type}'")

            query_parts.append("trashed = false")

            query = " and ".join(query_parts)

            # List files
            results = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=limit,
                    fields="files(id, name, size, mimeType, createdTime, modifiedTime, parents, webViewLink, thumbnailLink)",
                )
                .execute()
            )

            files = []
            for file in results.get("files", []):
                files.append(
                    StorageFile(
                        id=file.get("id"),
                        name=file.get("name"),
                        size=int(file.get("size", 0)),
                        mime_type=file.get("mimeType"),
                        created_at=self._parse_datetime(file.get("createdTime")),
                        modified_at=self._parse_datetime(file.get("modifiedTime")),
                        parent_id=file.get("parents", [None])[0],
                        url=file.get("webViewLink"),
                        thumbnail_url=file.get("thumbnailLink"),
                    )
                )

            logger.info(
                "drive_files_listed",
                count=len(files),
                folder_id=folder_id,
            )

            return files

        except HttpError as e:
            logger.error(
                "drive_list_failed",
                error=str(e),
            )
            raise

    async def get_download_url(
        self,
        file_id: str,
        expiration: int = 3600,
    ) -> str:
        """
        Get download URL for Drive file.

        Note: Google Drive doesn't support presigned URLs like S3.
        This returns the webContentLink which requires authentication.
        """
        try:
            file = (
                self.service.files()
                .get(fileId=file_id, fields="webContentLink")
                .execute()
            )

            url = file.get("webContentLink")

            logger.info("drive_download_url_generated", file_id=file_id)

            return url

        except HttpError as e:
            logger.error(
                "drive_download_url_failed",
                file_id=file_id,
                error=str(e),
            )
            raise

    async def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """Create folder in Google Drive."""
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_id:
            file_metadata["parents"] = [parent_id]

        try:
            folder = (
                self.service.files()
                .create(body=file_metadata, fields="id")
                .execute()
            )

            folder_id = folder.get("id")

            logger.info(
                "drive_folder_created",
                folder_id=folder_id,
                folder_name=folder_name,
            )

            return folder_id

        except HttpError as e:
            logger.error(
                "drive_folder_creation_failed",
                folder_name=folder_name,
                error=str(e),
            )
            raise

    async def watch_folder(
        self,
        folder_id: str,
        webhook_url: str,
        expiration: Optional[int] = None,
    ) -> dict:
        """
        Watch folder for changes using Google Drive push notifications.

        This enables real-time detection of new file uploads.
        """
        from uuid import uuid4

        # Generate unique channel ID
        channel_id = str(uuid4())

        # Build watch request
        body = {
            "id": channel_id,
            "type": "web_hook",
            "address": webhook_url,
        }

        if expiration:
            # Convert seconds to milliseconds
            body["expiration"] = str((datetime.now().timestamp() + expiration) * 1000)

        try:
            response = (
                self.service.files()
                .watch(fileId=folder_id, body=body)
                .execute()
            )

            logger.info(
                "drive_folder_watch_started",
                folder_id=folder_id,
                channel_id=response.get("id"),
                resource_id=response.get("resourceId"),
            )

            return {
                "id": response.get("id"),
                "resource_id": response.get("resourceId"),
                "expiration": response.get("expiration"),
            }

        except HttpError as e:
            logger.error(
                "drive_watch_failed",
                folder_id=folder_id,
                error=str(e),
            )
            raise

    async def stop_watch(self, channel_id: str, resource_id: str) -> bool:
        """Stop watching folder for changes."""
        body = {
            "id": channel_id,
            "resourceId": resource_id,
        }

        try:
            self.service.channels().stop(body=body).execute()

            logger.info("drive_watch_stopped", channel_id=channel_id)

            return True

        except HttpError as e:
            logger.error(
                "drive_stop_watch_failed",
                channel_id=channel_id,
                error=str(e),
            )
            return False

    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse Google Drive datetime string to datetime object."""
        if not datetime_str:
            return None

        try:
            # Google Drive uses RFC 3339 format
            return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
