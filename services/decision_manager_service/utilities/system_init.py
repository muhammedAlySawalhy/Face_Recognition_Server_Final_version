#!/usr/bin/env python3.10
import os
import sys

def _add_to_python_path():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_file_dir, '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

_add_to_python_path()

from common_utilities import  get_root_path, LOGGER, set_paths, set_namespace, get_namespace, LOG_LEVEL, ConfigManager, build_storage_client

def initialize_system_paths():
    root_path=get_root_path(start=__file__,APP_HEAD="decision_manager.py")
    __APP_DIRS_PATHS__ = dict()
    __APP_DIRS_PATHS__["APPLICATION_ROOT_PATH"] = root_path
    __APP_DIRS_PATHS__["LOGS_ROOT_PATH"] = root_path

    __SYSTEM_NAMESPACE__ = os.getenv("NAMESPACE", default=os.getenv("HOSTNAME", default=None))
    set_paths(__APP_DIRS_PATHS__)
    set_namespace(__SYSTEM_NAMESPACE__)
    os.chdir(root_path)
    return __APP_DIRS_PATHS__


def full_system_initialization(service_name):
    paths = initialize_system_paths()
    service_logger = LOGGER(service_name)
    service_logger.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
    service_logger.create_File_logger(f"{service_name}_Logs", log_levels=["DEBUG", "INFO", "ERROR", "CRITICAL", "WARNING"])
    
    service_logger.write_logs(f"System initialization completed for {service_name}", LOG_LEVEL.INFO)
    service_logger.write_logs(f"Application root path: {paths['APPLICATION_ROOT_PATH']}", LOG_LEVEL.DEBUG)

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
 

    return paths, service_logger, storage_client
