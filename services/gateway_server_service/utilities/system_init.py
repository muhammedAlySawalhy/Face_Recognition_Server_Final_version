#!/usr/bin/env python3.10
import os

from common_utilities import (
    ConfigManager,
    LOGGER,
    LOG_LEVEL,
    build_storage_client,
    get_root_path,
    get_namespace,
    set_namespace,
    set_paths,
)
from common_utilities.log_maintenance import start_log_cleanup_worker_from_paths


def initialize_system_paths(service_file_path):
    root_path = get_root_path(start=service_file_path, APP_HEAD="gateway_server.py")
    __APP_DIRS_PATHS__ = dict()
    __APP_DIRS_PATHS__["APPLICATION_ROOT_PATH"] = root_path
    __APP_DIRS_PATHS__["LOGS_ROOT_PATH"] = root_path
    __APP_DIRS_PATHS__["USERS_DATABASE_ROOT_PATH"] = os.path.join(
        root_path, "Data", "Users_DataBase"
    )
    __SYSTEM_NAMESPACE__ = os.getenv(
        "NAMESPACE", default=os.getenv("HOSTNAME", default=None)
    )
    set_paths(__APP_DIRS_PATHS__)
    set_namespace(__SYSTEM_NAMESPACE__)
    os.chdir(root_path)
    return __APP_DIRS_PATHS__


def full_system_initialization(service_file_path, service_name):
    paths = initialize_system_paths(service_file_path)
    service_logger = LOGGER(service_name)
    service_logger.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
    service_logger.create_File_logger(
        f"{service_name}_Logs",
        log_levels=["DEBUG", "INFO", "ERROR", "CRITICAL", "WARNING"],
    )

    service_logger.write_logs(
        f"System initialization completed for {service_name}", LOG_LEVEL.INFO
    )
    service_logger.write_logs(
        f"Application root path: {paths['APPLICATION_ROOT_PATH']}", LOG_LEVEL.DEBUG
    )
    config_manager = ConfigManager.instance()
    describe = config_manager.describe()
    service_logger.write_logs(
        f"Active deployment profile '{describe['profile']}' -> capacity {describe['capacity']}",
        LOG_LEVEL.INFO,
    )

    storage_client = build_storage_client(config_manager.storage, logger=service_logger)
    service_logger.write_logs(
        f"Storage provider set to '{storage_client.provider}' bucket '{storage_client.frames_bucket}'",
        LOG_LEVEL.INFO,
    )
    start_log_cleanup_worker_from_paths(
        paths,
        namespace=get_namespace(),
    )

    return paths, service_logger, config_manager, storage_client


def get_environment_config():
    config_manager = ConfigManager.instance()
    gateway_settings = config_manager.service_settings("gateway")
    websocket_settings = gateway_settings.get("websocket", {})
    rate_cfg = config_manager.rate_limiter

    return {
        "SERVER_IP": os.environ.get("SERVER_IP", "0.0.0.0"),
        "SERVER_PORT": int(os.environ.get("SERVER_PORT", 8000)),
        "ENDPOINT_PATH": os.environ.get("ENDPOINT_PATH", "/ws"),
        "RATE_LIMIT_MAX_CLIENTS": rate_cfg.max_clients,
        "RATE_LIMIT_WINDOW_MS": rate_cfg.window_ms,
        "RATE_LIMIT_CLEANUP_MS": rate_cfg.cleanup_ms,
        "CONFIG_PROFILE": config_manager.profile_name,
    }
