#!/usr/bin/env python3.10
"""
Shared System Initialization Module
Handles path setup, directory creation, and environment configuration
that was originally in main.py
"""

import os
import json
import yaml

from common_utilities import (
    ConfigManager,
    build_storage_client,
    LOGGER,
    LOG_LEVEL,
    get_root_path,
    set_namespace,
    set_paths,
)
from utilities import create_Models_Weights_Directory
from deepface.commons.folder_utils import (
    initialize_folder as deepface_initialize_folder,
)


def initialize_system_paths(service_file_path):
    """
    Initialize system paths based on the service location
    Returns the paths dictionary
    """
    # Calculate root path from service location (go up to main directory)
    root_path = get_root_path(service_file_path, "pipeline_worker.py")

    __APP_DIRS_PATHS__ = dict()
    __APP_DIRS_PATHS__["APPLICATION_ROOT_PATH"] = root_path
    __APP_DIRS_PATHS__["MODELS_WEIGHTS_ROOT_PATH"] = os.path.join(root_path, "Models_Weights")
    __APP_DIRS_PATHS__["LOGS_ROOT_PATH"] = root_path
    __APP_DIRS_PATHS__["USERS_DATABASE_ROOT_PATH"] = os.path.join(root_path, "Data", "Users_DataBase")
    __APP_DIRS_PATHS__["ACTIONS_ROOT_PATH"] = os.path.join(root_path, "Data", "Actions")
    __APP_DIRS_PATHS__["SERVER_DATA_ROOT_PATH"] = os.path.join(root_path, "Data", "Server_Data")

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


def create_required_directories():
    """
    Create all required directories
    """
    create_Models_Weights_Directory()
    deepface_initialize_folder()


def get_models_parameters(models_weights_root_path):
    """
    Get the models parameters configuration
    """
    global service_logger
    default_models_parameters = {
        # Models Weights Parameters
        "Models_Weights_dir": "Models_Weights",
        "ObjectDetection_model_weights": "phone_detection.pt",
        "FaceDetection_model_weights": "yolov8_model.pt",
        "FaceRecognition_model_weights": "vgg_face_weights.h5",
        "FaceSpoofChecker_model_weights": None,
        # GPU Device Parameters
        "Object_Detection_Models_device": "cuda:0",
        "Face_Detection_Model_device": "cuda:0",
        "Face_Recognition_Model_device": "GPU:0",
        "spoof_Models_device": "cuda:0",
        # Recognition Parameters
        "Recognition_model_name": "VGG-Face",
        "Recognition_Metric": "cosine_similarity",
        # Phone Detection Parameters
        "Object_class_number": 67,
        # Models Threshold Parameters
        "Recognition_Threshold": 0.3,
        "Object_threshold": 65,
        "Anti_Spoof_threshold": 0.99,
    }
    config_file_path = os.path.join(models_weights_root_path, "models_settings.yaml")
    if not os.path.exists(config_file_path):
        service_logger.write_logs(
            f"Models parameters configuration file not found at {config_file_path}. Using default parameters.",
            LOG_LEVEL.WARNING,
        )
        return default_models_parameters
    with open(config_file_path, "r") as config_file:
        try:
            models_parameters = yaml.safe_load(config_file)
            service_logger.write_logs(
                f"Models parameters loaded from {config_file_path}", LOG_LEVEL.INFO
            )
            return models_parameters
        except yaml.YAMLError as e:
            service_logger.write_logs(
                f"Error loading models parameters from {config_file_path}: {e}",
                LOG_LEVEL.ERROR,
            )
            service_logger.write_logs(
                "Using default models parameters.", LOG_LEVEL.WARNING
            )
            return default_models_parameters


def full_system_initialization(service_file_path, service_name):
    """Complete system initialization for a pipeline worker microservice."""
    global service_logger
    paths = initialize_system_paths(service_file_path)
    service_logger = LOGGER(service_name)
    service_logger.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
    service_logger.create_File_logger(
        f"{service_name}_Logs", log_levels=["DEBUG", "ERROR", "CRITICAL", "WARNING"]
    )

    config_manager = ConfigManager.instance()
    storage_client = build_storage_client(
        config_manager.storage, logger=service_logger
    )

    create_required_directories()
    models_parameters = get_models_parameters(paths["MODELS_WEIGHTS_ROOT_PATH"])

    service_logger.write_logs(
        f"System initialization completed for {service_name}", LOG_LEVEL.INFO
    )
    service_logger.write_logs(
        f"Application root path: {paths['APPLICATION_ROOT_PATH']}", LOG_LEVEL.DEBUG
    )

    describe = config_manager.describe()
    service_logger.write_logs(
        f"Worker profile '{describe['profile']}' targeting {describe['pipeline']['pipelines_per_server']} pipelines/server",
        LOG_LEVEL.INFO,
    )
    service_logger.write_logs(
        f"Storage provider '{storage_client.provider}' bucket '{storage_client.frames_bucket}'",
        LOG_LEVEL.INFO,
    )

    return paths, models_parameters, service_logger, config_manager, storage_client


def get_environment_config():
    """Get environment configuration with defaults derived from the deployment profile."""
    config_manager = ConfigManager.instance()
    pipeline_cfg = config_manager.pipeline
    service_settings = config_manager.service_settings("pipeline_worker")

    return {
        "MaxClientPerPipeline": pipeline_cfg.max_clients_per_pipeline,
        "MaxPipeline": pipeline_cfg.pipelines_per_server,
        "PIPELINES_TOTAL": pipeline_cfg.total_pipelines,
        "WARMUP_BATCH": bool(service_settings.get("warmup_batch", False)),
        "CONFIG_PROFILE": config_manager.profile_name,
    }
