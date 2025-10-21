from typing import Dict, Optional, Type

from .RateLimiterAbstract import AbstractRatelimiter


class RateLimiterManager:
    _instance: Optional["RateLimiterManager"] = None

    def __init__(self, rate_limiter_cls: Type[AbstractRatelimiter], config: Dict[str, int]):
        if getattr(self, "_rate_limiter", None) is not None:
            return

        if rate_limiter_cls is None:
            raise ValueError("rate_limiter_cls must be provided")
        if config is None:
            raise ValueError("config must be provided")

        self._rate_limiter = rate_limiter_cls(
            config.get("max_clients"),
            config.get("window_size_in_millis"),
            config.get("cleanup_interval_in_millis"),
        )

    @classmethod
    def get_instance(
        cls,
        rate_limiter_cls: Optional[Type[AbstractRatelimiter]] = None,
        config: Optional[Dict[str, int]] = None,
    ) -> "RateLimiterManager":
        if cls._instance is None:
            if rate_limiter_cls is None or config is None:
                raise ValueError("rate_limiter_cls and config must be provided for the initial get_instance call.")
            cls._instance = cls(rate_limiter_cls, config)
        return cls._instance

    def allow_request(self, client_id: str) -> bool:
        if getattr(self, "_rate_limiter", None) is None:
            raise RuntimeError("RateLimiter has not been initialized.")
        return self._rate_limiter.allowRequest(client_id)

    def shutdown(self) -> None:
        if getattr(self, "_rate_limiter", None) is not None:
            self._rate_limiter.shutdown()
            self._rate_limiter = None
        RateLimiterManager._instance = None
