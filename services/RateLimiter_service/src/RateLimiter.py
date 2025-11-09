import atexit
import threading
from typing import Dict, Optional

from time import time
from concurrent.futures import ThreadPoolExecutor

from common_utilities import LOGGER, LOG_LEVEL

from .utils.syncdict import SynchronizedDict
from .RateLimiterAbstract import AbstractRatelimiter


class RateLimiter(AbstractRatelimiter):
    def __init__(self, max_clients: int, window_size_in_millis: int, cleanup_interval_in_millis: Optional[int] = None):
        self.max_clients: int = max_clients
        self.window_size: int = window_size_in_millis
        self._cleanup_interval_millis: int = (
            cleanup_interval_in_millis if cleanup_interval_in_millis is not None else window_size_in_millis
        )

        self.logger = LOGGER("RateLimiter")
        self.logger.create_Stream_logger(["DEBUG", "INFO", "WARNING", "ERROR"])

        self.client_counts: Dict[str, int] = SynchronizedDict()
        self.client_window_start: Dict[str, int] = SynchronizedDict()
        self.client_last_seen: Dict[str, int] = SynchronizedDict()

        self._cleanup_stop = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.executor.submit(self._cleanup_loop)
        atexit.register(self.shutdown)

    def _cleanup_loop(self) -> None:
        interval_millis = (
            self._cleanup_interval_millis if self._cleanup_interval_millis and self._cleanup_interval_millis > 0 else self.window_size
        )
        interval_seconds = interval_millis / 1000.0 if interval_millis and interval_millis > 0 else 0.1
        while not self._cleanup_stop.is_set():
            self._cleanup_old_entries()
            self._cleanup_stop.wait(interval_seconds)

    def _cleanup_old_entries(self) -> None:
        current_time = int(time() * 1000)
        removed = []
        for client_id in list(self.client_counts.keys()):
            window_start = self.client_window_start.get(client_id, 0)
            last_seen = self.client_last_seen.get(client_id, window_start)
            if current_time - max(window_start, last_seen) >= self.window_size:
                removed.append((client_id, self.client_counts.get(client_id, 0)))
                self.client_counts.pop(client_id, None)
                self.client_window_start.pop(client_id, None)
                self.client_last_seen.pop(client_id, None)
        if removed:
            summary = ", ".join(f"{cid}:{count}" for cid, count in removed)
            self.logger.write_logs(
                f"RateLimiter cleanup removed stale entries -> {summary}",
                LOG_LEVEL.DEBUG,
            )

    def shutdown(self) -> None:
        if not self._cleanup_stop.is_set():
            self._cleanup_stop.set()
        self.executor.shutdown(wait=True)

    def _is_client_active(self, client_id: str, current_time: int) -> bool:
        window_start = self.client_window_start.get(client_id)
        if window_start is None:
            return False
        last_seen = self.client_last_seen.get(client_id, window_start)
        return current_time - max(window_start, last_seen) < self.window_size

    def allowRequest(self, client_id: str) -> bool:
        current_time = int(time() * 1000)

        client_is_active = self._is_client_active(client_id, current_time)
        active_clients = sum(
            1 for cid in self.client_counts.keys() if self._is_client_active(cid, current_time)
        )

        if not client_is_active and active_clients >= self.max_clients:
            self.logger.write_logs(
                f"Request denied for client {client_id}. Active clients this window: {active_clients}",
                LOG_LEVEL.WARNING,
            )
            return False

        current_count = self.client_counts.get(client_id, 0)
        window_start = self.client_window_start.get(client_id)

        if window_start is None or not client_is_active:
            window_start = current_time
            current_count = 0

        self.client_counts[client_id] = current_count
        self.client_window_start[client_id] = window_start
        self.client_last_seen[client_id] = current_time

        self.client_counts[client_id] = current_count + 1
        self.logger.write_logs(
            f"Request allowed for client {client_id}. Active clients this window: {len(self.client_counts)}",
            LOG_LEVEL.DEBUG,
        )
        return True
