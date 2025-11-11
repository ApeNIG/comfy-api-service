"""
Abstract storage provider interface

Defines the contract for all storage backends (Google Drive, MinIO, S3).
This enables swapping storage providers without changing business logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, BinaryIO, List
from datetime import datetime


@dataclass
class StorageFile:
    """
    Represents a file in storage.

    This is a unified representation across all storage providers.
    """

    id: str  # Unique file identifier (Drive file ID, MinIO object key, etc.)
    name: str  # File name
    size: Optional[int] = None  # File size in bytes
    mime_type: Optional[str] = None  # MIME type (e.g., "image/png")
    created_at: Optional[datetime] = None  # Creation timestamp
    modified_at: Optional[datetime] = None  # Last modified timestamp
    parent_id: Optional[str] = None  # Parent folder ID (for Drive)
    url: Optional[str] = None  # Public URL (if available)
    thumbnail_url: Optional[str] = None  # Thumbnail URL (if available)


class StorageProvider(ABC):
    """
    Abstract interface for storage providers.

    All storage backends (Google Drive, MinIO, S3) must implement this interface.

    This allows the Creator product to be storage-agnostic:
    - Development: Use MinIO locally
    - Production: Use Google Drive for user files
    - Archive: Use S3 for long-term storage

    Usage:
        # Business logic doesn't care about storage backend
        provider = get_storage_provider()  # Returns Drive or MinIO
        file = await provider.upload_file(data, "image.png")
        content = await provider.download_file(file.id)
    """

    @abstractmethod
    async def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        mime_type: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> StorageFile:
        """
        Upload a file to storage.

        Args:
            file_data: Binary file data
            file_name: Name for the file
            mime_type: MIME type (optional, will be inferred if not provided)
            folder_id: Parent folder ID (for Drive) or path prefix (for MinIO)

        Returns:
            StorageFile with metadata

        Example:
            >>> with open("image.png", "rb") as f:
            ...     file = await provider.upload_file(f, "image.png", "image/png")
            >>> print(file.id, file.url)
        """
        pass

    @abstractmethod
    async def download_file(self, file_id: str) -> bytes:
        """
        Download a file from storage.

        Args:
            file_id: File identifier

        Returns:
            File content as bytes

        Example:
            >>> content = await provider.download_file("1ABC...")
            >>> with open("downloaded.png", "wb") as f:
            ...     f.write(content)
        """
        pass

    @abstractmethod
    async def get_file(self, file_id: str) -> StorageFile:
        """
        Get file metadata without downloading content.

        Args:
            file_id: File identifier

        Returns:
            StorageFile with metadata

        Example:
            >>> file = await provider.get_file("1ABC...")
            >>> print(f"File: {file.name}, Size: {file.size}")
        """
        pass

    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from storage.

        Args:
            file_id: File identifier

        Returns:
            True if deleted successfully

        Example:
            >>> success = await provider.delete_file("1ABC...")
            >>> print(f"Deleted: {success}")
        """
        pass

    @abstractmethod
    async def list_files(
        self,
        folder_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[StorageFile]:
        """
        List files in storage.

        Args:
            folder_id: Filter by folder (for Drive) or prefix (for MinIO)
            mime_type: Filter by MIME type (e.g., "image/*")
            limit: Maximum number of files to return

        Returns:
            List of StorageFile objects

        Example:
            >>> files = await provider.list_files(folder_id="1ABC...", mime_type="image/*")
            >>> for file in files:
            ...     print(f"{file.name}: {file.size} bytes")
        """
        pass

    @abstractmethod
    async def get_download_url(
        self,
        file_id: str,
        expiration: int = 3600,
    ) -> str:
        """
        Get a temporary download URL for a file.

        Args:
            file_id: File identifier
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL for downloading

        Example:
            >>> url = await provider.get_download_url("1ABC...", expiration=3600)
            >>> print(f"Download from: {url}")
        """
        pass

    @abstractmethod
    async def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in storage.

        Args:
            folder_name: Name for the folder
            parent_id: Parent folder ID (optional)

        Returns:
            Folder ID

        Example:
            >>> folder_id = await provider.create_folder("My Outputs", parent_id="1ABC...")
            >>> print(f"Created folder: {folder_id}")
        """
        pass

    @abstractmethod
    async def watch_folder(
        self,
        folder_id: str,
        webhook_url: str,
        expiration: Optional[int] = None,
    ) -> dict:
        """
        Set up webhook notifications for folder changes (Drive-specific).

        Args:
            folder_id: Folder to watch
            webhook_url: URL to receive notifications
            expiration: Webhook expiration in seconds (optional)

        Returns:
            Webhook metadata (channel ID, expiration, etc.)

        Example:
            >>> webhook = await provider.watch_folder(
            ...     folder_id="1ABC...",
            ...     webhook_url="https://api.example.com/webhooks/drive"
            ... )
            >>> print(f"Watching folder with channel: {webhook['id']}")

        Notes:
            - Only applicable for Google Drive
            - MinIO implementation returns empty dict
        """
        pass

    @abstractmethod
    async def stop_watch(self, channel_id: str, resource_id: str) -> bool:
        """
        Stop watching folder for changes (Drive-specific).

        Args:
            channel_id: Webhook channel ID
            resource_id: Resource ID from watch_folder response

        Returns:
            True if stopped successfully

        Example:
            >>> success = await provider.stop_watch(
            ...     channel_id="abc-123",
            ...     resource_id="xyz-456"
            ... )
        """
        pass
