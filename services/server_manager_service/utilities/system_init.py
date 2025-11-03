#!/usr/bin/env python3.10
import os
from common_utilities import (
    RedisHandler,
    get_root_path,
    LOGGER,
    set_paths,
    set_namespace,
    get_namespace,
    LOG_LEVEL,
    ConfigManager,
    build_storage_client,
)
from common_utilities.log_maintenance import start_log_cleanup_worker_from_paths
from .files_handler import create_server_Data_Directory, create_Users_Actions_Directory
from dotenv import load_dotenv

def initialize_system_paths(service_file_path):
    root_path = get_root_path(service_file_path,"server_manager.py")
    
    __APP_DIRS_PATHS__ = dict()
    __APP_DIRS_PATHS__["APPLICATION_ROOT_PATH"] = root_path
    __APP_DIRS_PATHS__["LOGS_ROOT_PATH"] = root_path
    __APP_DIRS_PATHS__["SERVER_DATA_ROOT_PATH"] = os.path.join(root_path, "Data", "Server_Data")
    __APP_DIRS_PATHS__["ACTIONS_ROOT_PATH"] = os.path.join(root_path, "Data", "Actions")
    __APP_DIRS_PATHS__["USERS_DATABASE_ROOT_PATH"] = os.path.join(root_path, "Data", "Users_DataBase")

    __SYSTEM_NAMESPACE__ = os.getenv("NAMESPACE", default=os.getenv("HOSTNAME", default=None))
    
    set_paths(__APP_DIRS_PATHS__)
    set_namespace(__SYSTEM_NAMESPACE__)
    
    load_dotenv(os.path.join(root_path, ".env"))
    
    os.chdir(root_path)
    
    return __APP_DIRS_PATHS__

def create_required_directories():
    create_server_Data_Directory()
    create_Users_Actions_Directory()


def full_system_initialization(service_file_path, service_name):
    paths = initialize_system_paths(service_file_path)
    
    create_required_directories()

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
    start_log_cleanup_worker_from_paths(
        paths,
        namespace=get_namespace(),
    )

    return paths, service_logger, storage_client

def get_environment_config():
    return {
        "GUI_BACKEND_IP": os.environ.get("GUI_BACKEND_IP", "0.0.0.0"),
        "GUI_BACKEND_PORT": int(os.environ.get("GUI_BACKEND_PORT", 6000)),
    }
