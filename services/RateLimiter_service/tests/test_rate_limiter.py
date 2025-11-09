import os
import sys
import time
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.RateLimiter import RateLimiter
from src.RateLimiterManager import RateLimiterManager


class RateLimiterTests(unittest.TestCase):
    def test_cleanup_removes_stale_client_entries(self):
        limiter = RateLimiter(
            max_clients=5,
            window_size_in_millis=50,
            cleanup_interval_in_millis=10,
        )
        try:
            limiter.allowRequest("client-a")
            deadline = time.time() + 0.5
            # Wait for the cleanup loop to purge the client once the window elapses.
            while (
                time.time() < deadline
                and limiter.client_counts.get("client-a") is not None
            ):
                time.sleep(0.01)
            self.assertIsNone(limiter.client_counts.get("client-a"))
            self.assertIsNone(limiter.client_window_start.get("client-a"))
            self.assertIsNone(limiter.client_last_seen.get("client-a"))
        finally:
            limiter.shutdown()

    def test_shutdown_signals_background_worker(self):
        limiter = RateLimiter(
            max_clients=1,
            window_size_in_millis=100,
            cleanup_interval_in_millis=10,
        )
        limiter.shutdown()
        self.assertTrue(limiter._cleanup_stop.is_set())
        self.assertTrue(limiter.executor._shutdown)

    def test_manager_delegates_allow_request(self):
        config = {
            "max_clients": 2,
            "window_size_in_millis": 100,
            "cleanup_interval_in_millis": 50,
        }
        manager = RateLimiterManager.get_instance(RateLimiter, config)
        try:
            self.assertTrue(manager.allow_request("client-a"))
        finally:
            manager.shutdown()

    def test_manager_is_singleton(self):
        config = {
            "max_clients": 2,
            "window_size_in_millis": 100,
            "cleanup_interval_in_millis": 50,
        }
        manager1 = RateLimiterManager.get_instance(RateLimiter, config)
        try:
            manager2 = RateLimiterManager.get_instance()
            self.assertIs(manager1, manager2)
        finally:
            manager1.shutdown()

        # After shutdown a fresh instance can be created.
        manager3 = RateLimiterManager.get_instance(RateLimiter, config)
        try:
            self.assertIsNot(manager1, manager3)
        finally:
            manager3.shutdown()

    def test_rate_limit_enforced_when_capacity_reached(self):
        limiter = RateLimiter(
            max_clients=1,
            window_size_in_millis=100,
            cleanup_interval_in_millis=50,
        )
        try:
            self.assertTrue(limiter.allowRequest("client-a"))
            self.assertFalse(limiter.allowRequest("client-b"))
        finally:
            limiter.shutdown()


if __name__ == "__main__":
    unittest.main()
