#!/usr/bin/env python3.10
"""
Shared System Initialization Module
Handles path setup, directory creation, and environment configuration
that was originally in main.py
"""

import os

from common_utilities import (
    get_root_path,
    LOGGER,
    LOG_LEVEL,
    set_namespace,
    set_paths,
)

try:
    from common_utilities import ConfigManager  # type: ignore
except ImportError:  # pragma: no cover - fallback when ConfigManager not bundled
    ConfigManager = None  # type: ignore


def initialize_system_paths(service_file_path):
    """
    Initialize system paths based on the service location
    Returns the paths dictionary
    """
    # Calculate root path from service location (go up to main directory)
    root_path = get_root_path(service_file_path, "pipelines_manager.py")

    __APP_DIRS_PATHS__ = dict()
    __APP_DIRS_PATHS__["APPLICATION_ROOT_PATH"] = root_path
    __APP_DIRS_PATHS__["LOGS_ROOT_PATH"] = root_path

    # Set system namespace
    __SYSTEM_NAMESPACE__ = os.getenv(
        "NAMESPACE", default=os.getenv("HOSTNAME", default=None)
    )

    # Apply paths and namespace globally
    set_paths(__APP_DIRS_PATHS__)
    set_namespace(__SYSTEM_NAMESPACE__)

    # Change to root directory
    os.chdir(root_path)

    return __APP_DIRS_PATHS__


def full_system_initialization(service_file_path, service_name):
    """
    Complete system initialization for a microservice
    Returns: (paths_dict, models_parameters, redis_clients_status, redis_clients_data, service_logger)
    """
    # Initialize paths
    paths = initialize_system_paths(service_file_path)

    # Create service logger
    service_logger = LOGGER(service_name)
    service_logger.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
    service_logger.create_File_logger(
        f"{service_name}_Logs", log_levels=["DEBUG", "ERROR", "CRITICAL", "WARNING"]
    )

    service_logger.write_logs(
        f"System initialization completed for {service_name}", LOG_LEVEL.INFO
    )
    service_logger.write_logs(
        f"Application root path: {paths['APPLICATION_ROOT_PATH']}", LOG_LEVEL.DEBUG
    )

    config_manager = None
    if ConfigManager is not None:
        try:
            config_manager = ConfigManager.instance()
            describe = config_manager.describe()
            service_logger.write_logs(
                f"Pipelines manager using profile '{describe['profile']}' with {describe['pipeline']['pipelines_per_server']} pipelines/server",
                LOG_LEVEL.INFO,
            )
        except Exception as exc:  # pragma: no cover - graceful degradation
            service_logger.write_logs(
                f"Failed to initialise ConfigManager: {exc}. Falling back to environment defaults.",
                LOG_LEVEL.WARNING,
            )
            config_manager = None
    else:
        service_logger.write_logs(
            "ConfigManager module not available. Falling back to environment defaults.",
            LOG_LEVEL.WARNING,
        )

    return paths, service_logger, config_manager


def get_environment_config():
    """
    Get environment configuration with defaults
    """
    if ConfigManager is not None:
        config_manager = ConfigManager.instance()
        pipeline_cfg = config_manager.pipeline
        service_settings = config_manager.service_settings("pipelines_manager")

        return {
            "MaxClientPerPipeline": pipeline_cfg.max_clients_per_pipeline,
            "MaxPipeline": pipeline_cfg.pipelines_per_server,
            "PIPELINES_TOTAL": pipeline_cfg.total_pipelines,
            "MONITOR_GPU_UTILISATION": bool(
                service_settings.get("monitor_gpu_utilisation", False)
            ),
            "CONFIG_PROFILE": config_manager.profile_name,
        }

    # Fallback to environment overrides when ConfigManager is unavailable
    max_clients = int(os.getenv("PIPELINE_MAX_CLIENTS", os.getenv("MAX_CLIENTS_PER_PIPELINE", 10)))
    pipelines_per_server = int(os.getenv("PIPELINES_PER_SERVER", os.getenv("MAX_PIPELINE", 4)))
    total_pipelines = int(os.getenv("PIPELINES_TOTAL", pipelines_per_server))
    monitor_gpu = os.getenv("MONITOR_GPU_UTILISATION", "false").lower() in {"1", "true", "yes", "on"}
    profile = os.getenv("CONFIG_PROFILE", "prod-1gpu-24gb")

    return {
        "MaxClientPerPipeline": max_clients,
        "MaxPipeline": pipelines_per_server,
        "PIPELINES_TOTAL": total_pipelines,
        "MONITOR_GPU_UTILISATION": monitor_gpu,
        "CONFIG_PROFILE": profile,
    }
