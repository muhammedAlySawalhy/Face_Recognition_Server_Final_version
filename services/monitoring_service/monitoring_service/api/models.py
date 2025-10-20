from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class CollectorHealth(BaseModel):
    name: str
    last_ok: Optional[float] = None
    last_error: Optional[str] = None


class SystemMetrics(BaseModel):
    cpu: Dict[str, object]
    memory: Dict[str, object]
    disk: Dict[str, object]
    network: Dict[str, object]
    gpu: List[Dict[str, object]]
    timestamp: float


class ClientMetrics(BaseModel):
    active_count: int
    paused_count: int
    blocked_count: int
    deactivated_count: int
    active_clients: List[str]
    paused_clients: List[str]
    blocked_clients: List[str]
    deactivated_clients: List[str]


class BucketSummary(BaseModel):
    name: str
    created: str


class StorageMetrics(BaseModel):
    bucket_count: int
    buckets: List[BucketSummary]
    live: bool
    ready: bool
    endpoint: str
