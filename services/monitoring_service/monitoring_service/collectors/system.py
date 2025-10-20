from __future__ import annotations

import math
import time
from typing import Any, Dict, Optional

import psutil

from ..config import Settings
from ..registry import MetricRegistry
from .base import BaseCollector

try:
    import pynvml as _pynvml
except ImportError:  # pragma: no cover - optional dependency
    _pynvml = None  # type: ignore


class SystemCollector(BaseCollector):
    namespace = "system"

    def __init__(self, registry: MetricRegistry, settings: Settings) -> None:
        super().__init__(registry, interval_seconds=settings.system_collector.interval_seconds)
        self.settings = settings
        self._last_net: Optional[Dict[str, Any]] = None
        self._nvml_available = False
        if _pynvml is not None:
            try:
                _pynvml.nvmlInit()
                self._nvml_available = True
            except Exception:  # pragma: no cover - NVML init failure
                self._nvml_available = False

    async def collect(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=None)
        load1, load5, load15 = psutil.getloadavg()
        core_count = psutil.cpu_count() or 1
        normalized_load = {
            "1m": load1 / core_count,
            "5m": load5 / core_count,
            "15m": load15 / core_count,
        }

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage("/")

        net = psutil.net_io_counters()
        now = time.time()
        net_rates = {}
        if self._last_net:
            delta_t = max(now - self._last_net["timestamp"], 1e-6)
            net_rates = {
                "bytes_sent_per_sec": (net.bytes_sent - self._last_net["bytes_sent"]) / delta_t,
                "bytes_recv_per_sec": (net.bytes_recv - self._last_net["bytes_recv"]) / delta_t,
            }
        self._last_net = {
            "timestamp": now,
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
        }

        gpu_metrics = self._collect_gpu() if self._nvml_available else []

        return {
            "cpu": {
                "percent": cpu_percent,
                "load": normalized_load,
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(),
            },
            "memory": {
                "total": memory.total,
                "used": memory.used,
                "percent": memory.percent,
                "available": memory.available,
                "swap_used": swap.used,
                "swap_percent": swap.percent,
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "percent": disk.percent,
                "free": disk.free,
            },
            "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            **net_rates,
        },
            "gpu": gpu_metrics,
            "timestamp": now,
        }

    def _collect_gpu(self) -> list:
        devices = []
        if not self._nvml_available or _pynvml is None:
            return devices
        try:
            device_count = _pynvml.nvmlDeviceGetCount()
        except _pynvml.NVMLError:  # pragma: no cover - GPU unavailable
            return devices

        indices = self.settings.gpu_devices or list(range(device_count))
        for index in indices:
            if index >= device_count:
                continue
            handle = _pynvml.nvmlDeviceGetHandleByIndex(index)
            memory = _pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = _pynvml.nvmlDeviceGetUtilizationRates(handle)
            temperature = None
            try:
                temperature = _pynvml.nvmlDeviceGetTemperature(handle, _pynvml.NVML_TEMPERATURE_GPU)
            except _pynvml.NVMLError:
                temperature = math.nan

            devices.append(
                {
                    "index": index,
                    "name": _pynvml.nvmlDeviceGetName(handle).decode("utf-8"),
                    "memory_total": memory.total,
                    "memory_used": memory.used,
                    "memory_percent": (memory.used / memory.total * 100.0) if memory.total else 0.0,
                    "utilization_gpu": utilization.gpu,
                    "utilization_mem": utilization.memory,
                    "temperature": temperature,
                }
            )
        return devices
