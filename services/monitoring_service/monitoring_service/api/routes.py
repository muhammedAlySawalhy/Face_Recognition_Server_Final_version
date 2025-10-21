from fastapi import APIRouter, Depends, HTTPException

from ..registry import MetricRegistry
from .dependencies import get_registry
from .models import ClientMetrics, CollectorHealth, StorageMetrics, SystemMetrics

router = APIRouter()


@router.get("/healthz", response_model=list[CollectorHealth])
async def healthz(registry: MetricRegistry = Depends(get_registry)) -> list[CollectorHealth]:
    statuses = await registry.snapshot_collector_status()
    return [CollectorHealth(**status.__dict__) for status in statuses.values()]


@router.get("/metrics/system", response_model=SystemMetrics)
async def get_system_metrics(registry: MetricRegistry = Depends(get_registry)) -> SystemMetrics:
    snapshot = await registry.get_latest("system")
    if snapshot is None:
        raise HTTPException(status_code=503, detail="system metrics not available")
    return SystemMetrics(**snapshot.data)


@router.get("/metrics/clients", response_model=ClientMetrics)
async def get_client_metrics(registry: MetricRegistry = Depends(get_registry)) -> ClientMetrics:
    snapshot = await registry.get_latest("clients")
    if snapshot is None:
        raise HTTPException(status_code=503, detail="client metrics not available")
    return ClientMetrics(**snapshot.data)


@router.get("/metrics/storage", response_model=StorageMetrics)
async def get_storage_metrics(registry: MetricRegistry = Depends(get_registry)) -> StorageMetrics:
    snapshot = await registry.get_latest("storage")
    if snapshot is None:
        raise HTTPException(status_code=503, detail="storage metrics not available")
    return StorageMetrics(**snapshot.data)
