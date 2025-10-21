from __future__ import annotations

import pickle
from typing import Any, Dict, Optional

from redis import Redis

from ..config import Settings
from ..registry import MetricRegistry
from .base import BaseCollector


class RedisCollector(BaseCollector):
    namespace = "clients"

    def __init__(self, registry: MetricRegistry, settings: Settings) -> None:
        super().__init__(registry, interval_seconds=settings.redis_collector.interval_seconds)
        self.settings = settings
        self._client: Optional[Redis] = None

    def _get_client(self) -> Redis:
        if self._client is None:
            self._client = Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password,
                decode_responses=False,
            )
        return self._client

    async def collect(self) -> Dict[str, Any]:
        client = self._get_client()

        raw_clients_status = client.hgetall("Clients_status") or {}
        clients_status = {key.decode(): pickle.loads(value) for key, value in raw_clients_status.items()}

        active_clients = list(clients_status.get("active_clients", []))
        paused_clients = list(clients_status.get("paused_clients", []))
        blocked_clients = list(clients_status.get("blocked_clients", []))
        deactivated_clients = list(clients_status.get("deactivate_clients", []))

        # Fallback lists (legacy keys)
        if not paused_clients:
            paused_clients = [pickle.loads(item) for item in client.lrange("paused_clients", 0, -1) or []]
        if not blocked_clients:
            blocked_clients = [pickle.loads(item) for item in client.lrange("blocked_clients", 0, -1) or []]
        if not deactivated_clients:
            deactivated_clients = [pickle.loads(item) for item in client.lrange("deactivate_clients", 0, -1) or []]

        return {
            "active_count": len(active_clients),
            "paused_count": len(paused_clients),
            "blocked_count": len(blocked_clients),
            "deactivated_count": len(deactivated_clients),
            "active_clients": active_clients,
            "paused_clients": paused_clients,
            "blocked_clients": blocked_clients,
            "deactivated_clients": deactivated_clients,
        }
