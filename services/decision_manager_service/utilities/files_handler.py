#!/usr/bin/env python3.10

import os
import re
import shutil
from typing import Tuple,Dict,Set
import cv2
import time
import numpy as np
from functools import lru_cache
from huggingface_hub import hf_hub_download
from utilities.Datatypes import Action,Reason
from common_utilities import get_root_path,get_paths,get_namespace,LOG_LEVEL
# Store last known DB folder modification time
_last_mtime = None  
_client_image_cache: Dict[str, cv2.Mat] = {}
_last_client_mtime: Dict[str, float] = {}


def __has_new_data() -> bool:
    """Check if the Users_DataBase directory has been modified."""
    global _last_mtime
    __PROPJET_PATHS=get_paths()
    db_path_dir = __PROPJET_PATHS["USERS_DATABASE_ROOT_PATH"]
    try:
        current_mtime = os.stat(db_path_dir).st_mtime  # Get the latest modification time
        if _last_mtime is None:  # First check, initialize mtime
            _last_mtime = current_mtime
            return False
        if current_mtime > _last_mtime:  # If modified, update _last_mtime
            _last_mtime = current_mtime
            return True
    except FileNotFoundError:
        return False  # Directory not found
    return False

def __read_client_image(client_name: str):
    __PROPJET_PATHS=get_paths()
    db_path_dir = __PROPJET_PATHS["USERS_DATABASE_ROOT_PATH"]
    image_path = os.path.join(db_path_dir, client_name, f"{client_name}_1.jpg")
    if os.path.exists(image_path):
        ref_img = cv2.imread(image_path)
    else:
        ref_img = None
    return ref_img

@lru_cache(maxsize=1)
def __get_available_users() -> Set[str]:
    """
    Ultra-fast directory scanning using low-level OS calls.
    Extremely efficient for large directories.
    Works best on Unix-like systems.
    """
    __PROPJET_PATHS=get_paths()
    db_path_dir = __PROPJET_PATHS["USERS_DATABASE_ROOT_PATH"]
    db = set()
    for entry in os.scandir(db_path_dir):
        try:
            if (entry.is_dir(follow_symlinks=True) and entry.name != "dummy"):
                db.add(entry.name)
        except Exception:
            continue
    return db


def get_available_users()-> Tuple[Set[str],int]:
    """Auto-refreshes cache if new data is detected."""
    if __has_new_data():
        __get_available_users.cache_clear()
        return __get_available_users()
    return __get_available_users()

def get_client_image(client_name: str) -> cv2.Mat:
    __PROPJET_PATHS=get_paths()
    client_dir = os.path.join(__PROPJET_PATHS["USERS_DATABASE_ROOT_PATH"], client_name)
    try:
        current_mtime = os.stat(client_dir).st_mtime
    except FileNotFoundError:
        return None
    # Check if cached and unchanged
    if (client_name in _client_image_cache and _last_client_mtime.get(client_name) == current_mtime):
        return _client_image_cache[client_name]
    # Either not cached, or file changed – refresh
    user_db = get_available_users()
    if client_name in user_db:
        client_img = __read_client_image(client_name)
        _client_image_cache[client_name] = client_img
        _last_client_mtime[client_name] = current_mtime
        return client_img
    return None
@lru_cache(maxsize=1)
def getServerDataDirectoryPath():
    __PROPJET_PATHS=get_paths()
    __NAMESPACE=get_namespace()
    Server_Data_path_dir = __PROPJET_PATHS["SERVER_DATA_ROOT_PATH"]
    if __NAMESPACE:
        Server_Data_path_dir = os.path.join(Server_Data_path_dir, __NAMESPACE)
    return Server_Data_path_dir

def create_Data_Directory():
    __PROPJET_PATHS=get_paths()
    data_path = os.path.join(__PROPJET_PATHS["APPLICATION_ROOT_PATH"], "Data")
    os.makedirs(data_path, exist_ok=True)
    create_Users_Database_Directory()
    create_Users_Actions_Directory()

def create_Users_Database_Directory():
    __PROPJET_PATHS=get_paths()
    db_path_dir = __PROPJET_PATHS["USERS_DATABASE_ROOT_PATH"]
    os.makedirs(db_path_dir, exist_ok=True)
    # dummy_user_dir = os.path.join(db_path_dir, "dummy")
    # os.makedirs(dummy_user_dir, exist_ok=True)
    # dummy_image = np.zeros((640, 640, 3), dtype=np.uint8)
    # cv2.imwrite(os.path.join(dummy_user_dir, "dummy_1.jpg"), dummy_image)

def create_server_Data_Directory():
    Server_Data_path = getServerDataDirectoryPath()
    os.makedirs(Server_Data_path, exist_ok=True)

def create_Users_Actions_Directory()->str:
    __PROPJET_PATHS=get_paths()
    actions_path_dir = __PROPJET_PATHS["ACTIONS_ROOT_PATH"]
    os.makedirs(actions_path_dir, exist_ok=True)

def save_User_Action(user_name:str,Action_Reason:Dict[str,int],Action_image:cv2.typing.MatLike)->None:
    __PROPJET_PATHS=get_paths()
    Action_name=Action_Reason['action']
    Reason_name=Action_Reason['reason']
    action_user_dir = os.path.join(__PROPJET_PATHS["ACTIONS_ROOT_PATH"], Action(Action_name).name.replace("ACTION_", "").capitalize(), user_name)
    os.makedirs(action_user_dir, exist_ok=True)
    action_time = time.localtime() 
    formatted_action_time = time.strftime("%d_%m_%Y-%H_%M", action_time)
    image_name="___".join([formatted_action_time,Action(Action_name).name.replace("ACTION_", "").capitalize(),Reason(Reason_name).name.replace("REASON_", "").capitalize()])
    image_name_path=os.path.join(action_user_dir,image_name+".jpg")
    cv2.imwrite(image_name_path,Action_image)

def create_User_DB(user_name):
    root_path=get_root_path(__file__,",main.py")
    user_name=re.sub(r"\s+","_",user_name).lower()
    db_path_dir=os.path.join(root_path,"DataBase","Users")
    image_path_dir=os.path.join(db_path_dir,user_name,"Images")
    Action_path_dir=os.path.join(db_path_dir,user_name,"Action")
    os.makedirs(image_path_dir,exist_ok=True)
    os.makedirs(Action_path_dir,exist_ok=True)

def create_Models_Weights_Directory(logger=None):
    __PROPJET_PATHS=get_paths()
    models_weights_root = __PROPJET_PATHS["MODELS_WEIGHTS_ROOT_PATH"]
    phone_detection_file_name = {"phone_detection.pt": "phone_detection/phone_detection.pt"}
    face_detection_file_name = {"yolov8_model.pt": "face_detection/yolov8_model.pt"}
    deepface_models_name = {
        "2.7_80x80_MiniFASNetV2.pth": "face_recognition/.deepface/weights/2.7_80x80_MiniFASNetV2.pth",
        "4_0_0_80x80_MiniFASNetV1SE.pth": "face_recognition/.deepface/weights/4_0_0_80x80_MiniFASNetV1SE.pth",
        "vgg_face_weights.h5": "face_recognition/.deepface/weights/vgg_face_weights.h5",
        "yolov8n-face.pt": "face_recognition/.deepface/weights/yolov8n-face.pt",
        # "facenet512_weights.h5": "face_recognition/.deepface/weights/facenet512_weights.h5",
    }
    auto_download_enabled = os.getenv("ALLOW_MODEL_AUTO_DOWNLOAD", "true").lower() in {"1", "true", "yes", "on"}
    missing_files = []
    download_errors = {}
    hf_repo_id = os.getenv("MODEL_WEIGHTS_HF_REPO_ID")
    hf_revision = os.getenv("MODEL_WEIGHTS_HF_REVISION", "main")
    hf_token = os.getenv("HUGGINGFACE_TOKEN")

    def _ensure_dir(path: str):
        try:
            os.makedirs(path, exist_ok=True)
        except PermissionError as exc:
            message = f"Unable to create directory '{path}': {exc}."
            if logger:
                logger.write_logs(message, LOG_LEVEL.ERROR)
            raise

    def _download_file(destination_path: str, remote_path: str):
        if not auto_download_enabled:
            missing_files.append(destination_path)
            return
        if not hf_repo_id:
            download_errors[destination_path] = "MODEL_WEIGHTS_HF_REPO_ID environment variable is not set."
            missing_files.append(destination_path)
            return
        try:
            downloaded_path = hf_hub_download(
                repo_id=hf_repo_id,
                filename=remote_path,
                revision=hf_revision,
                token=hf_token or None,
            )
            shutil.copyfile(downloaded_path, destination_path)
        except Exception as exc:  # pylint: disable=broad-except
            download_errors[destination_path] = str(exc)
            missing_files.append(destination_path)

    def _handle_models(target_dir: str, models_map: Dict[str, str]):
        _ensure_dir(target_dir)
        for model_name, remote_path in models_map.items():
            destination_path = os.path.join(target_dir, model_name)
            if os.path.isfile(destination_path):
                continue
            _download_file(destination_path, remote_path)

    # Face detection
    face_detection_dir_path = os.path.join(models_weights_root, "face_detection")
    _handle_models(face_detection_dir_path, face_detection_file_name)

    # Phone detection
    phone_detection_dir_path = os.path.join(models_weights_root, "phone_detection")
    _handle_models(phone_detection_dir_path, phone_detection_file_name)

    # Face recognition
    face_recognition_dir_path = os.path.join(models_weights_root, "face_recognition", ".deepface", "weights")
    _handle_models(face_recognition_dir_path, deepface_models_name)
    os.environ["DEEPFACE_HOME"] = os.path.join(models_weights_root, "face_recognition")

    if missing_files:
        details = ", ".join(missing_files)
        base_message = (
            "Missing required model weights. "
            f"Ensure the following files exist inside 'Models_Weights': {details}."
        )
        if not auto_download_enabled:
            base_message += (
                " Automatic downloads are disabled (ALLOW_MODEL_AUTO_DOWNLOAD set to false). "
                "Download the files manually from Hugging Face and place them in the corresponding directories."
            )
        else:
            base_message += (
                " Automatic download from Hugging Face failed. Check your network connection, "
                "ensure MODEL_WEIGHTS_HF_REPO_ID (and optional MODEL_WEIGHTS_HF_REVISION/HUGGINGFACE_TOKEN) are set correctly, "
                "or download the files manually. You can disable auto-download by setting ALLOW_MODEL_AUTO_DOWNLOAD=false."
            )
            if download_errors:
                joined_errors = "; ".join(f"{path}: {error}" for path, error in download_errors.items())
                base_message += f" Errors: {joined_errors}"
        if logger:
            logger.write_logs(base_message, LOG_LEVEL.ERROR)
        raise RuntimeError(base_message)
    
