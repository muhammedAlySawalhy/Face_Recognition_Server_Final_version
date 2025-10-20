#!/usr/bin/env python3.10
"""
Shared System Initialization Module
Handles path setup, directory creation, and environment configuration
that was originally in main.py
"""
import os
from common_utilities import RedisHandler, get_root_path, LOGGER, set_paths, set_namespace, LOG_LEVEL
from .files_handler import (
    create_server_Data_Directory,
    create_Users_Actions_Directory
)
from dotenv import load_dotenv

def initialize_system_paths(service_file_path):
    """
    Initialize system paths based on the service location
    Returns the paths dictionary
    """
    # Calculate root path from service location (go up to main directory)
    root_path = get_root_path(service_file_path,"server_manager.py")
    
    __APP_DIRS_PATHS__ = dict()
    __APP_DIRS_PATHS__["APPLICATION_ROOT_PATH"] = root_path
    __APP_DIRS_PATHS__["LOGS_ROOT_PATH"] = root_path
    __APP_DIRS_PATHS__["SERVER_DATA_ROOT_PATH"] = os.path.join(root_path, "Data", "Server_Data")
    __APP_DIRS_PATHS__["ACTIONS_ROOT_PATH"] = os.path.join(root_path, "Data", "Actions")
    __APP_DIRS_PATHS__["USERS_DATABASE_ROOT_PATH"] = os.path.join(root_path, "Data", "Users_DataBase")

    # Set system namespace
    __SYSTEM_NAMESPACE__ = os.getenv("NAMESPACE", default=os.getenv("HOSTNAME", default=None))
    
    # Apply paths and namespace globally
    set_paths(__APP_DIRS_PATHS__)
    set_namespace(__SYSTEM_NAMESPACE__)
    
    # Load environment variables
    load_dotenv(os.path.join(root_path, ".env"))
    
    # Change to root directory
    os.chdir(root_path)
    
    return __APP_DIRS_PATHS__

def create_required_directories():
    """
    Create all required directories
    """
    create_server_Data_Directory()
    create_Users_Actions_Directory()


def full_system_initialization(service_file_path, service_name):
    """
    Complete system initialization for a microservice
    Returns: (paths_dict, models_parameters, redis_clients_status, redis_clients_data, service_logger)
    """
    # Initialize paths
    paths = initialize_system_paths(service_file_path)
    
    # Create directories
    create_required_directories()

    
    # Create service logger
    service_logger = LOGGER(service_name)
    service_logger.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
    service_logger.create_File_logger(f"{service_name}_Logs", log_levels=["DEBUG", "INFO", "ERROR", "CRITICAL", "WARNING"])
    
    service_logger.write_logs(f"System initialization completed for {service_name}", LOG_LEVEL.INFO)
    service_logger.write_logs(f"Application root path: {paths['APPLICATION_ROOT_PATH']}", LOG_LEVEL.DEBUG)
    
    return paths, service_logger

def get_environment_config():
    """
    Get environment configuration with defaults
    """
    return {
        "GUI_BACKEND_IP": os.environ.get("GUI_BACKEND_IP", "0.0.0.0"),
        "GUI_BACKEND_PORT": int(os.environ.get("GUI_BACKEND_PORT", 6000)),
    }
