from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CollectorConfig(BaseModel):
    enabled: bool = True
    interval_seconds: float = Field(default=5.0, gt=0)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MONITORING_", env_file=".env", extra="ignore")

    service_name: str = "monitoring-service"
    host: str = "0.0.0.0"
    port: int = 8080

    rmq_url: Optional[str] = None
    redis_host: str = "Redis_Server"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    history_window_minutes: int = Field(default=15, gt=0)

    system_collector: CollectorConfig = CollectorConfig(interval_seconds=5.0)
    redis_collector: CollectorConfig = CollectorConfig(interval_seconds=5.0)
    rmq_collector: CollectorConfig = CollectorConfig(enabled=False, interval_seconds=5.0)
    storage_collector: CollectorConfig = CollectorConfig(enabled=True, interval_seconds=15.0)

    gpu_devices: Optional[List[int]] = None
    minio_endpoint: str = "minio:9000"
    minio_access_key: Optional[str] = "minioadmin"
    minio_secret_key: Optional[str] = "minioadmin"
    minio_secure: bool = False
    minio_region: Optional[str] = None
    minio_health_timeout: float = Field(default=3.0, gt=0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
