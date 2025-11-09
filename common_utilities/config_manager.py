#!/usr/bin/env python3.10
"""
Centralised configuration manager for the Face Recognition platform.

The manager loads structured profiles from `config/profiles.yaml`, applies optional
environment overrides, and exposes strongly typed accessors to every service.

Patterns:
  * Singleton: configuration is loaded once and shared across the process.
  * Strategy: deployment profiles encapsulate tuning strategies (dev, prod, HA).

Environment overrides:
  * CONFIG_PROFILE                -> selects a profile (default: prod-1gpu-24gb)
  * CONFIG_PATH                   -> optional alternate YAML file
  * CFG__section__subsection=val  -> overrides nested fields (case-insensitive)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from .storage import StorageSettings
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

CONFIG_ROOT = Path(__file__).resolve().parents[1] / "config"
CONFIG_FILE = CONFIG_ROOT / "profiles.yaml"
ENV_PROFILE_KEY = "CONFIG_PROFILE"
ENV_CONFIG_PATH = "CONFIG_PATH"
ENV_OVERRIDE_PREFIX = "CFG__"


def _deep_merge(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge dictionaries (incoming overrides base)."""
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(dict(base[key]), value)
        else:
            base[key] = value
    return base


def _apply_override(target: Dict[str, Any], path: str, raw_value: str) -> None:
    segments = [segment for segment in path.split("__") if segment]
    cursor = target
    for segment in segments[:-1]:
        cursor = cursor.setdefault(segment, {})
    final_key = segments[-1]
    # Attempt type inference for simple scalars.
    normalised = raw_value.strip()
    if normalised.lower() in {"true", "false"}:
        value: Any = normalised.lower() == "true"
    else:
        try:
            value = int(normalised)
        except ValueError:
            try:
                value = float(normalised)
            except ValueError:
                value = raw_value
    cursor[final_key] = value


def _collect_env_overrides() -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(ENV_OVERRIDE_PREFIX):
            continue
        path = key[len(ENV_OVERRIDE_PREFIX) :].lower()
        _apply_override(overrides, path, value)
    return overrides


@dataclass(frozen=True)
class RateLimiterConfig:
    max_clients: int
    window_ms: int
    cleanup_ms: int


@dataclass(frozen=True)
class PipelineConfig:
    pipelines_per_server: int
    pipelines_per_gpu: int
    max_clients_per_pipeline: int
    total_pipelines: int
    total_capacity: int


@dataclass(frozen=True)
class HardwareProfile:
    servers: int
    gpus_per_server: int
    total_gpus: int
    gpu_memory_gb: int


class ConfigManager:
    """Singleton configuration manager."""

    _instance: Optional["ConfigManager"] = None

    def __init__(self, profile_name: str, profile_data: Dict[str, Any]):
        self.profile_name = profile_name
        self._raw = profile_data
        self._hardware = HardwareProfile(
            servers=int(profile_data["hardware"]["servers"]),
            gpus_per_server=int(profile_data["hardware"]["gpus_per_server"]),
            total_gpus=int(profile_data["hardware"]["total_gpus"]),
            gpu_memory_gb=int(profile_data["hardware"]["gpu_memory_gb"]),
        )
        pipeline = profile_data["pipeline"]
        pipelines_per_server = int(pipeline["pipelines_per_server"])
        total_pipelines = pipelines_per_server * self._hardware.servers
        max_clients_per_pipeline = int(pipeline["max_clients_per_pipeline"])
        total_capacity = total_pipelines * max_clients_per_pipeline
        # Honour explicit hard limit if defined
        hard_limit = profile_data.get("capacity", {}).get("hard_limit_clients")
        if hard_limit is not None:
            total_capacity = min(total_capacity, int(hard_limit))

        self._pipeline_config = PipelineConfig(
            pipelines_per_server=pipelines_per_server,
            pipelines_per_gpu=int(
                pipeline.get("pipelines_per_gpu", pipelines_per_server)
            ),
            max_clients_per_pipeline=max_clients_per_pipeline,
            total_pipelines=total_pipelines,
            total_capacity=total_capacity,
        )
        rate_cfg = profile_data["rate_limiter"]
        self._rate_limiter_config = RateLimiterConfig(
            max_clients=int(rate_cfg.get("max_clients", total_capacity)),
            window_ms=int(rate_cfg.get("window_ms", 6000)),
            cleanup_ms=int(rate_cfg.get("cleanup_ms", rate_cfg.get("window_ms", 6000))),
        )
        storage_cfg = profile_data.get("storage", {})
        self._storage_settings = StorageSettings(
            provider=str(storage_cfg.get("provider", "minio")),
            frames_bucket=str(storage_cfg.get("frames_bucket", "face-frames")),
            retention_hours=int(storage_cfg.get("retention_hours", 24)),
        )

    @classmethod
    def instance(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = cls._load()
        return cls._instance

    @classmethod
    def _load(cls) -> "ConfigManager":
        config_path = Path(os.environ.get(ENV_CONFIG_PATH) or CONFIG_FILE)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with config_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)

        if not payload or "profiles" not in payload:
            raise ValueError(f"Invalid configuration file: {config_path}")

        requested_profile = os.environ.get(ENV_PROFILE_KEY, "prod-1gpu-24gb")
        if requested_profile not in payload["profiles"]:
            raise KeyError(
                f"Profile '{requested_profile}' is not defined in {config_path}"
            )

        profile_data = payload["profiles"][requested_profile]
        overrides = _collect_env_overrides()
        if overrides:
            profile_data = _deep_merge(profile_data, overrides)

        return cls(profile_name=requested_profile, profile_data=profile_data)

    @property
    def hardware(self) -> HardwareProfile:
        return self._hardware

    @property
    def pipeline(self) -> PipelineConfig:
        return self._pipeline_config

    @property
    def rate_limiter(self) -> RateLimiterConfig:
        limit = max(
            self._rate_limiter_config.max_clients, self._pipeline_config.total_capacity
        )
        return RateLimiterConfig(
            max_clients=limit,
            window_ms=self._rate_limiter_config.window_ms,
            cleanup_ms=self._rate_limiter_config.cleanup_ms,
        )

    @property
    def storage(self) -> StorageSettings:
        return self._storage_settings

    def service_settings(self, service_name: str) -> Dict[str, Any]:
        service_key = service_name.lower()
        services = self._raw.get("services", {})
        return dict(services.get(service_key, {}))

    def describe(self) -> Dict[str, Any]:
        """Return a serialisable overview for diagnostics."""
        capacity = self._raw.get("capacity", {})
        return {
            "profile": self.profile_name,
            "description": self._raw.get("description"),
            "hardware": self._hardware.__dict__,
            "pipeline": self._pipeline_config.__dict__,
            "capacity": {
                "designed_clients": capacity.get(
                    "designed_clients", self._pipeline_config.total_capacity
                ),
                "hard_limit_clients": capacity.get(
                    "hard_limit_clients", self._pipeline_config.total_capacity
                ),
            },
            "rate_limiter": self.rate_limiter.__dict__,
            "storage": self._storage_settings.__dict__,
        }


def reset_config_cache() -> None:
    """Utility for tests to reload configuration between runs."""
    ConfigManager._instance = None
