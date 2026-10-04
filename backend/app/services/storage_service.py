# storage_service.py
"""
Storage Service.
Handles interactions with Supabase Storage for uploading and retrieving document files.
"""
import logging

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service responsible for interacting with Supabase Storage.
    """

    def __init__(self) -> None:
        """
        Initializes the Supabase client and checks/creates the storage bucket.
        """
        self.bucket_name = "documents"

        # Don't try to initialize if keys are missing (useful for mock tests)
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            self.client = None
            logger.warning("Supabase credentials missing. StorageService initialized in mock mode.")
            return

        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """
        Helper to check if the 'documents' bucket exists, creating it if not.
        """
        if not self.client:
            return
        try:
            buckets = self.client.storage.list_buckets()
            exists = any(b.name == self.bucket_name for b in buckets)
            if not exists:
                self.client.storage.create_bucket(self.bucket_name, options={"public": False})
        except Exception as e:
            # Catch bucket exists or permission errors gracefully
            logger.warning("Bucket check/creation warning: %s", e)

    def upload_file(self, file_data: bytes, file_path: str, content_type: str) -> str:
        """
        Upload raw file bytes to Supabase storage.

        Args:
            file_data (bytes): The raw content of the file.
            file_path (str): The destination path in the bucket (e.g. 'uuid/filename.pdf').
            content_type (str): The MIME type of the file.

        Returns:
            str: The storage file path reference.
        """
        if not self.client:
            logger.info("StorageService in mock mode. Skipping upload.")
            return f"{self.bucket_name}/{file_path}"

        # Upload options
        file_options = {
            "content-type": content_type,
            "x-upsert": "true"
        }

        # Upload the file
        self.client.storage.from_(self.bucket_name).upload(
            path=file_path,
            file=file_data,
            file_options=file_options
        )

        return f"{self.bucket_name}/{file_path}"

    def get_public_url(self, file_path: str) -> str:
        """
        Get public URL for a file in Supabase storage.
        """
        if not self.client:
            return f"/storage/v1/object/public/{self.bucket_name}/{file_path}"
        try:
            return self.client.storage.from_(self.bucket_name).get_public_url(file_path)
        except Exception:
            return f"/storage/v1/object/public/{self.bucket_name}/{file_path}"
