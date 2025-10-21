#!/usr/bin/env python3.10
"""
Storage helpers for binary artefacts (e.g., incoming client frames).

Currently supports MinIO (S3 compatible). The gateway uploads frames, and
pipeline workers download them on demand to avoid moving large images
through RabbitMQ payloads.
"""

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
    """Thin wrapper around MinIO client."""

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
        self.logger.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])

        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )
        self._ensure_bucket(settings.frames_bucket)
        # Background cleanup scheduler
        self._cleanup_interval = int(os.getenv("STORAGE_CLEANUP_INTERVAL_SECONDS", "3600"))
        self._cleanup_age_hours = int(os.getenv("STORAGE_CLEANUP_MAX_AGE_HOURS", "2"))
        self._cleanup_max_objects = int(os.getenv("STORAGE_CLEANUP_MAX_OBJECTS", "1000"))
        self._cleanup_stop_event = threading.Event()
        self._cleanup_thread: Optional[threading.Thread] = None
        if self._cleanup_interval > 0 and self._cleanup_age_hours > 0:
            self._cleanup_thread = threading.Thread(
                target=self._run_periodic_cleanup,
                name="minio_cleanup_thread",
                daemon=True,
            )
            self._cleanup_thread.start()

    @property
    def frames_bucket(self) -> str:
        return self.settings.frames_bucket

    @property
    def provider(self) -> str:
        return self.settings.provider

    def _ensure_bucket(self, bucket: str) -> None:
        try:
            bucket_created = False
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)
                bucket_created = True
                self.logger.write_logs(
                    f"Created storage bucket '{bucket}'", LOG_LEVEL.INFO
                )
        except S3Error as exc:
            raise RuntimeError(
                f"Failed to verify/create bucket '{bucket}': {exc}"
            ) from exc
        else:
            self._ensure_retention_policy(bucket, bucket_created)

    def _ensure_retention_policy(self, bucket: str, bucket_created: bool) -> None:
        """Apply/refresh lifecycle policy so MinIO prunes old frames automatically."""
        retention_hours = max(0, int(self.settings.retention_hours))
        if retention_hours <= 0:
            if bucket_created:
                self.logger.write_logs(
                    f"Retention disabled for bucket '{bucket}' (retention_hours <= 0)",
                    LOG_LEVEL.DEBUG,
                )
            return

        retention_days = max(1, ceil(retention_hours / 24))
        desired_rule = Rule(
            rule_id="auto-expire-frames",
            status=ENABLED,
            rule_filter=Filter(prefix="frames/"),
            expiration=Expiration(days=retention_days),
        )

        existing_rules = []
        try:
            lifecycle_config = self._client.get_bucket_lifecycle(bucket)
            if lifecycle_config and lifecycle_config.rules:
                existing_rules = list(lifecycle_config.rules)
        except S3Error as exc:
            # Ignore missing lifecycle configuration, but warn on other errors.
            if exc.code not in {
                "NoSuchLifecycleConfiguration",
                "NoSuchBucketLifecycleConfiguration",
            }:
                self.logger.write_logs(
                    f"Failed to read lifecycle policy for bucket '{bucket}': {exc}",
                    LOG_LEVEL.WARNING,
                )
                # Avoid overriding unknown existing policy on error.
                return

        updated_rules = list(existing_rules)
        changed = False
        for idx, rule in enumerate(existing_rules):
            if getattr(rule, "rule_id", None) == desired_rule.rule_id:
                current_days = getattr(getattr(rule, "expiration", None), "days", None)
                current_filter = getattr(rule, "rule_filter", None) or getattr(rule, "filter", None)
                current_prefix = getattr(current_filter, "prefix", "")
                if current_days == retention_days and (current_prefix or "") == "frames/":
                    # Rule already matches desired retention; nothing to do.
                    return
                updated_rules[idx] = desired_rule
                changed = True
                break

        if not changed:
            updated_rules.append(desired_rule)
            changed = True

        if not changed:
            return

        try:
            self._client.set_bucket_lifecycle(bucket, LifecycleConfig(updated_rules))
            self.logger.write_logs(
                f"Configured MinIO lifecycle for bucket '{bucket}': expire 'frames/' objects after {retention_days} day(s)",
                LOG_LEVEL.INFO,
            )
        except S3Error as exc:
            self.logger.write_logs(
                f"Failed to set lifecycle policy for bucket '{bucket}': {exc}",
                LOG_LEVEL.ERROR,
            )

    def generate_frame_key(self, client_name: str) -> str:
        safe_client = client_name.replace(" ", "_").lower() or "client"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        unique = uuid.uuid4().hex[:12]
        return f"frames/{safe_client}/{timestamp}-{unique}.jpg"

    def store_frame(
        self, client_name: str, data: bytes, content_type: str = "image/jpeg"
    ) -> str:
        key = self.generate_frame_key(client_name)
        return self.store_object(key, data, content_type=content_type)

    def store_object(
        self, object_key: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
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
            return object_key
        except S3Error as exc:
            raise RuntimeError(
                f"Failed to upload object '{object_key}': {exc}"
            ) from exc

    def fetch_object(self, object_key: str) -> bytes:
        try:
            response = self._client.get_object(self.frames_bucket, object_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as exc:
            raise RuntimeError(
                f"Failed to download object '{object_key}': {exc}"
            ) from exc

    def delete_object(self, object_key: str) -> None:
        try:
            self._client.remove_object(self.frames_bucket, object_key)
        except S3Error:
            # Non-critical; log and continue.
            self.logger.write_logs(
                f"Failed to delete object '{object_key}' from bucket '{self.frames_bucket}'",
                LOG_LEVEL.WARNING,
            )

    def _run_periodic_cleanup(self) -> None:
        while not self._cleanup_stop_event.wait(self._cleanup_interval):
            removed = self._cleanup_old_objects(
                hours=self._cleanup_age_hours,
                max_objects=self._cleanup_max_objects,
            )
            if removed:
                self.logger.write_logs(
                    f"Periodic MinIO cleanup removed {removed} objects older than {self._cleanup_age_hours} hour(s)",
                    LOG_LEVEL.INFO,
                )

    def _cleanup_old_objects(self, hours: int = 2, max_objects: int = 200) -> int:
        """Delete objects older than the provided threshold (in hours)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        removed = 0
        try:
            for obj in self._client.list_objects(
                self.frames_bucket, prefix="frames/", recursive=True
            ):
                last_modified = getattr(obj, "last_modified", None)
                if not last_modified or last_modified >= cutoff:
                    continue
                try:
                    self._client.remove_object(self.frames_bucket, obj.object_name)
                    removed += 1
                except S3Error as exc:
                    self.logger.write_logs(
                        f"Failed to remove old object '{obj.object_name}': {exc}",
                        LOG_LEVEL.WARNING,
                    )
                if removed >= max_objects:
                    break
        except S3Error as exc:
            self.logger.write_logs(
                f"Failed during MinIO cleanup: {exc}", LOG_LEVEL.ERROR
            )
        return removed

    def __del__(self):
        if hasattr(self, "_cleanup_stop_event"):
            self._cleanup_stop_event.set()
        if hasattr(self, "_cleanup_thread") and self._cleanup_thread:
            self._cleanup_thread.join(timeout=1)


def build_storage_client(
    settings: StorageSettings, logger: Optional[LOGGER] = None
) -> StorageClient:
    endpoint = os.getenv("STORAGE_ENDPOINT", "minio:9000")
    access_key = os.getenv("STORAGE_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("STORAGE_SECRET_KEY", "minioadmin")
    secure = os.getenv("STORAGE_SECURE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
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
