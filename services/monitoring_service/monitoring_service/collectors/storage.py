from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from minio import Minio

from ..config import Settings
from ..registry import MetricRegistry
from .base import BaseCollector


class StorageCollector(BaseCollector):
    namespace = "storage"

    def __init__(self, registry: MetricRegistry, settings: Settings) -> None:
        super().__init__(registry, interval_seconds=settings.storage_collector.interval_seconds)
        self.settings = settings
        self._client: Optional[Minio] = None
        self._scheme, self._host = self._parse_endpoint(settings.minio_endpoint, settings.minio_secure)

    async def collect(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> Dict[str, Any]:
        client = self._get_client()
        buckets = client.list_buckets()
        bucket_summaries: List[Dict[str, Any]] = []

        for bucket in buckets:
            bucket_summaries.append(
                {
                    "name": bucket.name,
                    "created": bucket.creation_date.replace(tzinfo=dt.timezone.utc).isoformat()
                    if isinstance(bucket.creation_date, dt.datetime)
                    else bucket.creation_date.isoformat()
                    if hasattr(bucket.creation_date, "isoformat")
                    else str(bucket.creation_date),
                }
            )

        live = self._check_health("live")
        ready = self._check_health("ready")

        return {
            "bucket_count": len(bucket_summaries),
            "buckets": bucket_summaries,
            "live": live,
            "ready": ready,
            "endpoint": f"{self._scheme}://{self._host}",
        }

    def _get_client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                self._host,
                access_key=self.settings.minio_access_key,
                secret_key=self.settings.minio_secret_key,
                secure=self.settings.minio_secure,
                region=self.settings.minio_region,
            )
        return self._client

    def _check_health(self, probe: str) -> bool:
        health_url = f"{self._scheme}://{self._host}/minio/health/{probe}"
        request = Request(health_url, method="GET")
        try:
            with urlopen(request, timeout=self.settings.minio_health_timeout) as response:
                return 200 <= response.status < 300
        except Exception:
            return False

    @staticmethod
    def _parse_endpoint(endpoint: str, secure: bool) -> tuple[str, str]:
        parsed = urlsplit(endpoint if "://" in endpoint else f"http://{endpoint}")
        scheme = parsed.scheme or ("https" if secure else "http")
        host = parsed.netloc or parsed.path
        if not host:
            raise ValueError("Invalid MinIO endpoint")
        if secure and scheme == "http":
            scheme = "https"
        return scheme, host
