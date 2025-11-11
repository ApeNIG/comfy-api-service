"""
MinIO storage provider

S3-compatible object storage for local development and production.

Benefits:
- Self-hosted, no API quotas
- S3-compatible (easy migration to AWS S3)
- Fast for local development
- Cost-effective for production
"""

import mimetypes
from datetime import datetime, timedelta
from typing import Optional, BinaryIO, List
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from apps.shared.services.storage.base import StorageProvider, StorageFile
from apps.shared.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)


class MinIOProvider(StorageProvider):
    """
    MinIO storage provider implementation.

    Stores files in MinIO (S3-compatible object storage).

    Configuration (from settings):
        - MINIO_ENDPOINT: MinIO server endpoint (e.g., "localhost:9000")
        - MINIO_ACCESS_KEY: Access key
        - MINIO_SECRET_KEY: Secret key
        - MINIO_BUCKET_NAME: Bucket name
        - MINIO_SECURE: Use HTTPS (default: False for local dev)

    Usage:
        provider = MinIOProvider()
        file = await provider.upload_file(data, "image.png")
    """

    def __init__(self):
        """Initialize MinIO client."""
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        self.bucket_name = settings.MINIO_BUCKET_NAME

        # Ensure bucket exists
        self._ensure_bucket_exists()

        logger.info(
            "minio_provider_initialized",
            endpoint=settings.MINIO_ENDPOINT,
            bucket=self.bucket_name,
        )

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info("minio_bucket_created", bucket=self.bucket_name)
        except S3Error as e:
            logger.error("minio_bucket_creation_failed", error=str(e))
            raise

    async def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        mime_type: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> StorageFile:
        """Upload file to MinIO."""
        # Build object key (use folder_id as prefix)
        object_key = f"{folder_id}/{file_name}" if folder_id else file_name

        # Infer MIME type if not provided
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_name)
            mime_type = mime_type or "application/octet-stream"

        # Read file data into memory (MinIO needs size)
        file_bytes = file_data.read()
        file_size = len(file_bytes)
        file_stream = BytesIO(file_bytes)

        try:
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=file_stream,
                length=file_size,
                content_type=mime_type,
            )

            logger.info(
                "minio_file_uploaded",
                object_key=object_key,
                size=file_size,
                mime_type=mime_type,
            )

            # Get object stats for metadata
            stat = self.client.stat_object(self.bucket_name, object_key)

            return StorageFile(
                id=object_key,
                name=file_name,
                size=stat.size,
                mime_type=stat.content_type,
                created_at=stat.last_modified,
                modified_at=stat.last_modified,
                parent_id=folder_id,
            )

        except S3Error as e:
            logger.error(
                "minio_upload_failed",
                object_key=object_key,
                error=str(e),
                exc_info=True,
            )
            raise

    async def download_file(self, file_id: str) -> bytes:
        """Download file from MinIO."""
        try:
            response = self.client.get_object(self.bucket_name, file_id)
            data = response.read()
            response.close()
            response.release_conn()

            logger.info(
                "minio_file_downloaded",
                object_key=file_id,
                size=len(data),
            )

            return data

        except S3Error as e:
            logger.error(
                "minio_download_failed",
                object_key=file_id,
                error=str(e),
            )
            raise

    async def get_file(self, file_id: str) -> StorageFile:
        """Get file metadata from MinIO."""
        try:
            stat = self.client.stat_object(self.bucket_name, file_id)

            # Extract file name from object key
            file_name = file_id.split("/")[-1]

            return StorageFile(
                id=file_id,
                name=file_name,
                size=stat.size,
                mime_type=stat.content_type,
                created_at=stat.last_modified,
                modified_at=stat.last_modified,
            )

        except S3Error as e:
            logger.error(
                "minio_get_file_failed",
                object_key=file_id,
                error=str(e),
            )
            raise

    async def delete_file(self, file_id: str) -> bool:
        """Delete file from MinIO."""
        try:
            self.client.remove_object(self.bucket_name, file_id)

            logger.info("minio_file_deleted", object_key=file_id)

            return True

        except S3Error as e:
            logger.error(
                "minio_delete_failed",
                object_key=file_id,
                error=str(e),
            )
            return False

    async def list_files(
        self,
        folder_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[StorageFile]:
        """List files in MinIO."""
        try:
            # List objects with optional prefix
            prefix = f"{folder_id}/" if folder_id else None
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True,
            )

            files = []
            for obj in objects:
                # Skip if MIME type filter provided and doesn't match
                if mime_type and not obj.content_type.startswith(mime_type.replace("/*", "")):
                    continue

                file_name = obj.object_name.split("/")[-1]

                files.append(
                    StorageFile(
                        id=obj.object_name,
                        name=file_name,
                        size=obj.size,
                        mime_type=obj.content_type,
                        created_at=obj.last_modified,
                        modified_at=obj.last_modified,
                        parent_id=folder_id,
                    )
                )

                if len(files) >= limit:
                    break

            logger.info(
                "minio_files_listed",
                count=len(files),
                prefix=prefix,
            )

            return files

        except S3Error as e:
            logger.error(
                "minio_list_failed",
                error=str(e),
            )
            raise

    async def get_download_url(
        self,
        file_id: str,
        expiration: int = 3600,
    ) -> str:
        """Get presigned download URL."""
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=file_id,
                expires=timedelta(seconds=expiration),
            )

            logger.info(
                "minio_presigned_url_generated",
                object_key=file_id,
                expiration=expiration,
            )

            return url

        except S3Error as e:
            logger.error(
                "minio_presigned_url_failed",
                object_key=file_id,
                error=str(e),
            )
            raise

    async def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a 'folder' in MinIO.

        MinIO doesn't have real folders, but we create a .keep file
        to simulate folder creation.
        """
        # Build folder path
        folder_path = f"{parent_id}/{folder_name}" if parent_id else folder_name
        folder_path = folder_path.rstrip("/") + "/"

        # Create a .keep file to represent the folder
        keep_file_path = f"{folder_path}.keep"

        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=keep_file_path,
                data=BytesIO(b""),
                length=0,
            )

            logger.info("minio_folder_created", folder_path=folder_path)

            return folder_path

        except S3Error as e:
            logger.error(
                "minio_folder_creation_failed",
                folder_path=folder_path,
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
        MinIO doesn't support folder watching like Google Drive.

        Returns empty dict to satisfy interface.
        Use polling instead for MinIO.
        """
        logger.warning(
            "minio_watch_folder_not_supported",
            folder_id=folder_id,
            webhook_url=webhook_url,
        )

        return {}

    async def stop_watch(self, channel_id: str, resource_id: str) -> bool:
        """MinIO doesn't support watching. Always returns True."""
        return True
