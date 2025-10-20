from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ..registry import MetricRegistry

logger = logging.getLogger("monitoring.collector")


class BaseCollector:
    """Base class for periodic collectors."""

    namespace: str = "default"

    def __init__(self, registry: MetricRegistry, interval_seconds: float = 5.0) -> None:
        self.registry = registry
        self.interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task[None]] = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        if self._task is None:
            self._stopped.clear()
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task:
            self._stopped.set()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stopped.is_set():
            try:
                payload = await self.collect()
                if payload is not None:
                    await self.registry.update(self.namespace, payload)
                    await self.registry.upsert_collector_status(self.namespace)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Collector %s failed", self.namespace)
                await self.registry.upsert_collector_status(self.namespace, error=str(exc))
            await asyncio.sleep(self.interval_seconds)

    async def collect(self) -> Optional[dict]:
        raise NotImplementedError
