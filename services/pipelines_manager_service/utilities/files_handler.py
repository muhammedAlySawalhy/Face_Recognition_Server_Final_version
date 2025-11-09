#!/usr/bin/env python3.10

import os
import re
from typing import Tuple,Dict,Set
import cv2
import time
import numpy as np
from functools import lru_cache
from utilities.Datatypes import Action,Reason
from common_utilities import get_root_path,get_paths,get_namespace
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
