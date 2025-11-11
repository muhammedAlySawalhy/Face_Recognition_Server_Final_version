
from __future__ import annotations

import io
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from math import ceil
from typing import Optional

from minio import Minio
from minio.commonconfig import ENABLED
from minio.error import S3Error
from minio.lifecycleconfig import Expiration, Filter, LifecycleConfig, Rule

from common_utilities import LOGGER, LOG_LEVEL


@dataclass(frozen=True)
class StorageSettings:
    provider: str
    frames_bucket: str
    retention_hours: int


class StorageClient:

    def __init__(
        self,
        settings: StorageSettings,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
        region: Optional[str] = None,
        logger: Optional[LOGGER] = None,
    ):
        self.settings = settings
        self.logger = logger or LOGGER("StorageClient")
        self.logger.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING", "DEBUG"])

        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )
        
        # Ensure bucket exists
        self._ensure_bucket(settings.frames_bucket)
        
        # Decide cleanup strategy based on retention period
     

    @property
    def frames_bucket(self) -> str:
        return self.settings.frames_bucket

    @property
    def provider(self) -> str:
        return self.settings.provider

    def _ensure_bucket(self, bucket: str) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)
                self.logger.write_logs(
                    f"Created storage bucket '{bucket}'", LOG_LEVEL.INFO
                )
            else:
                self.logger.write_logs(
                    f"Storage bucket '{bucket}' already exists", LOG_LEVEL.DEBUG
                )
        except S3Error as exc:
            raise RuntimeError(
                f"Failed to verify/create bucket '{bucket}': {exc}"
            ) from exc

   

    def generate_frame_key(self, client_name: str) -> str:
        """Generate a unique object key for storing a client frame."""
        safe_client = client_name.replace(" ", "_").lower() or "client"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        unique = uuid.uuid4().hex[:12]
        return f"frames/{safe_client}/{timestamp}-{unique}.jpg"

    def store_frame(
        self, client_name: str, data: bytes, content_type: str = "image/jpeg"
    ) -> str:
        """
        Store a client frame in the bucket.
        
        Returns the object key that can be used to retrieve the frame later.
        The frame will be automatically deleted after the retention period.
        """
        key = self.generate_frame_key(client_name)
        return self.store_object(key, data, content_type=content_type)

    def store_object(
        self, object_key: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
        """Store arbitrary binary data in the bucket."""
        data_stream = io.BytesIO(data)
        length = len(data)
        
        try:
            self._client.put_object(
                self.frames_bucket,
                object_key,
                data_stream,
                length=length,
                content_type=content_type,
            )
            self.logger.write_logs(
                f"Stored object '{object_key}' ({length} bytes)",
                LOG_LEVEL.DEBUG,
            )
            return object_key
        except S3Error as exc:
            raise RuntimeError(
                f"Failed to upload object '{object_key}': {exc}"
            ) from exc

    def fetch_object(self, object_key: str) -> bytes:
        """Retrieve an object from the bucket."""
        try:
            response = self._client.get_object(self.frames_bucket, object_key)
            try:
                data = response.read()
                self.logger.write_logs(
                    f"Retrieved object '{object_key}' ({len(data)} bytes)",
                    LOG_LEVEL.DEBUG,
                )
                return data
            finally:
                response.close()
                response.release_conn()
        except S3Error as exc:
            raise RuntimeError(
                f"Failed to download object '{object_key}': {exc}"
            ) from exc


    def __del__(self):
        """Cleanup resources when the client is destroyed."""
        if hasattr(self, "_cleanup_stop_event"):
            self._cleanup_stop_event.set()
        if hasattr(self, "_cleanup_thread") and self._cleanup_thread:
            self._cleanup_thread.join(timeout=2)


def build_storage_client(
    settings: StorageSettings, logger: Optional[LOGGER] = None
) -> StorageClient:
    """
    Build a StorageClient from environment variables.
    
    Required environment variables:
    - STORAGE_ENDPOINT: MinIO server endpoint (default: "minio:9000")
    - STORAGE_ACCESS_KEY: MinIO access key (default: "minioadmin")
    - STORAGE_SECRET_KEY: MinIO secret key (default: "minioadmin")
    
    Optional environment variables:
    - STORAGE_SECURE: Use HTTPS (default: false)
    - STORAGE_REGION: MinIO region (optional)
    - STORAGE_CLEANUP_INTERVAL_SECONDS: Cleanup check interval for sub-day retention (default: 300)
    - STORAGE_CLEANUP_BATCH_SIZE: Max objects to delete per batch (default: 1000)
    """
    endpoint = os.getenv("STORAGE_ENDPOINT", "minio:9000")
    access_key = os.getenv("STORAGE_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("STORAGE_SECRET_KEY", "minioadmin")
    secure = os.getenv("STORAGE_SECURE", "false").strip().lower() in {"1", "true"}
    region = os.getenv("STORAGE_REGION")
    
    if not access_key or not secret_key:
        raise RuntimeError(
            "Storage credentials (STORAGE_ACCESS_KEY / STORAGE_SECRET_KEY) are required."
        )
    
    return StorageClient(
        settings=settings,
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
        region=region,
        logger=logger,
    )