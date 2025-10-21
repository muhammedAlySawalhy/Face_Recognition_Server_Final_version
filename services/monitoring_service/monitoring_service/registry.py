from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Optional


@dataclass
class MetricSnapshot:
    collected_at: float
    data: Dict[str, Any]


@dataclass
class CollectorStatus:
    name: str
    last_ok: Optional[float] = None
    last_error: Optional[str] = None

    def mark_ok(self) -> None:
        self.last_ok = time.time()
        self.last_error = None

    def mark_error(self, message: str) -> None:
        self.last_error = message


class MetricRegistry:
    """In-memory registry storing latest metrics and small history windows."""

    def __init__(self, history_size: int = 180) -> None:
        self._history: Dict[str, Deque[MetricSnapshot]] = {}
        self._latest: Dict[str, MetricSnapshot] = {}
        self._collector_status: Dict[str, CollectorStatus] = {}
        self._lock = asyncio.Lock()
        self._history_size = history_size

    async def update(self, namespace: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            snapshot = MetricSnapshot(collected_at=time.time(), data=payload)
            self._latest[namespace] = snapshot
            history = self._history.setdefault(namespace, deque(maxlen=self._history_size))
            history.append(snapshot)

    async def get_latest(self, namespace: str) -> Optional[MetricSnapshot]:
        async with self._lock:
            return self._latest.get(namespace)

    async def get_history(self, namespace: str) -> Deque[MetricSnapshot]:
        async with self._lock:
            history = self._history.get(namespace)
            if history is None:
                return deque()
            return deque(history)

    async def upsert_collector_status(self, name: str, *, error: Optional[str] = None) -> None:
        async with self._lock:
            status = self._collector_status.setdefault(name, CollectorStatus(name=name))
            if error:
                status.mark_error(error)
            else:
                status.mark_ok()

    async def snapshot_collector_status(self) -> Dict[str, CollectorStatus]:
        async with self._lock:
            return {name: CollectorStatus(name=v.name, last_ok=v.last_ok, last_error=v.last_error)
                    for name, v in self._collector_status.items()}
