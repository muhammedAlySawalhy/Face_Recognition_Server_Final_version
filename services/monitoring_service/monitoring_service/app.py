from __future__ import annotations

from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI

from .api import router
from .collectors import BaseCollector, RedisCollector, StorageCollector, SystemCollector
from .config import get_settings
from .registry import MetricRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    intervals: List[float] = []
    if settings.system_collector.enabled:
        intervals.append(settings.system_collector.interval_seconds)
    if settings.redis_collector.enabled:
        intervals.append(settings.redis_collector.interval_seconds)
    if settings.storage_collector.enabled:
        intervals.append(settings.storage_collector.interval_seconds)
    base_interval = intervals[0] if intervals else settings.system_collector.interval_seconds
    history_size = max(int(settings.history_window_minutes * 60 / base_interval), 12)
    registry = MetricRegistry(history_size=history_size)
    app.state.registry = registry

    collectors: List[BaseCollector] = []
    if settings.system_collector.enabled:
        collectors.append(SystemCollector(registry, settings))
    if settings.redis_collector.enabled:
        collectors.append(RedisCollector(registry, settings))
    if settings.storage_collector.enabled:
        collectors.append(StorageCollector(registry, settings))

    for collector in collectors:
        await collector.start()

    try:
        yield
    finally:
        for collector in collectors:
            await collector.stop()


app = FastAPI(title="Face Recognition Monitoring Service", lifespan=lifespan)
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"service": get_settings().service_name, "status": "ok"}
