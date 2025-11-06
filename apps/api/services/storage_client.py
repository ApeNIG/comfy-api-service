"""
Object storage client for artifact storage (MinIO/S3-compatible).

Handles uploading generated images and providing presigned URLs
for secure, time-limited access.
"""

from minio import Minio
from minio.error import S3Error
import io
from typing import BinaryIO, Optional
from datetime import timedelta
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class StorageClient:
    """
    S3-compatible storage client for artifacts.

    Uses MinIO for local development, can use AWS S3 in production.
    All operations are synchronous (MinIO client is not async).
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False
    ):
        """
        Initialize storage client.

        Args:
            endpoint: MinIO/S3 endpoint (e.g., "localhost:9000")
            access_key: Access key ID
            secret_key: Secret access key
            bucket: Bucket name for artifacts
            secure: Use HTTPS (True for S3, False for local MinIO)
        """
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created storage bucket: {self.bucket}")
            else:
                logger.info(f"Using existing bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload a file to storage.

        Args:
            object_name: Object key/path (e.g., "jobs/123/image_0.png")
            data: File-like object to upload
            length: Size of data in bytes
            content_type: MIME type

        Returns:
            S3 URI (e.g., "s3://bucket/jobs/123/image_0.png")

        Raises:
            S3Error: If upload fails
        """
        try:
            self.client.put_object(
                self.bucket,
                object_name,
                data,
                length,
                content_type=content_type
            )
            logger.info(f"Uploaded {object_name} ({length} bytes)")
            return f"s3://{self.bucket}/{object_name}"
        except S3Error as e:
            logger.error(f"Failed to upload {object_name}: {e}")
            raise

    def upload_bytes(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload bytes to storage (convenience method).

        Args:
            object_name: Object key/path
            data: Bytes to upload
            content_type: MIME type

        Returns:
            S3 URI
        """
        return self.upload_file(
            object_name,
            io.BytesIO(data),
            len(data),
            content_type
        )

    def upload_json(
        self,
        object_name: str,
        data: dict
    ) -> str:
        """
        Upload JSON data to storage.

        Args:
            object_name: Object key/path
            data: Dict to serialize as JSON

        Returns:
            S3 URI
        """
        import json
        json_bytes = json.dumps(data, indent=2).encode('utf-8')
        return self.upload_bytes(
            object_name,
            json_bytes,
            content_type="application/json"
        )

    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Generate presigned URL for temporary access.

        Args:
            object_name: Object key/path
            expires: URL validity duration

        Returns:
            Presigned URL (HTTP/HTTPS)

        Raises:
            S3Error: If URL generation fails
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=expires
            )
            logger.debug(f"Generated presigned URL for {object_name} (expires in {expires})")
            return url
        except S3Error as e:
            logger.error(f"Failed to generate URL for {object_name}: {e}")
            raise

    def delete_object(self, object_name: str) -> None:
        """
        Delete an object from storage.

        Args:
            object_name: Object key/path

        Raises:
            S3Error: If deletion fails
        """
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info(f"Deleted {object_name}")
        except S3Error as e:
            logger.error(f"Failed to delete {object_name}: {e}")
            raise

    def delete_prefix(self, prefix: str) -> None:
        """
        Delete all objects with a given prefix (e.g., "jobs/123/").

        Args:
            prefix: Object key prefix

        Raises:
            S3Error: If deletion fails
        """
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix)
            for obj in objects:
                self.client.remove_object(self.bucket, obj.object_name)
            logger.info(f"Deleted all objects with prefix: {prefix}")
        except S3Error as e:
            logger.error(f"Failed to delete prefix {prefix}: {e}")
            raise

    def object_exists(self, object_name: str) -> bool:
        """
        Check if object exists.

        Args:
            object_name: Object key/path

        Returns:
            True if object exists
        """
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False

    def get_object_info(self, object_name: str) -> Optional[dict]:
        """
        Get object metadata.

        Args:
            object_name: Object key/path

        Returns:
            Dict with size, etag, last_modified, etc. or None if not found
        """
        try:
            stat = self.client.stat_object(self.bucket, object_name)
            return {
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type
            }
        except S3Error:
            return None

    def health_check(self) -> bool:
        """
        Check if storage is accessible.

        Returns:
            True if storage is healthy
        """
        try:
            # Try to list bucket (lightweight operation)
            self.client.bucket_exists(self.bucket)
            return True
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return False


# Global instance
storage_client = StorageClient(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    bucket=settings.minio_bucket,
    secure=settings.minio_secure
)
