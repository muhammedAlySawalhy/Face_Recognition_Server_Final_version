#!/usr/bin/env python3.10
import os
import threading
import torch
import tensorflow as tf
from common_utilities import crop_image_center,LOGGER,LOG_LEVEL, get_paths
from utilities.files_handler import get_client_image
import cv2
import numpy as np
from .Face_Recognition_Task.DetectFaces import DetectFaces
from .Face_Recognition_Task.RecognitionFace import RecognitionFace
from .Face_Anti_Spoof_Task.SpoofChecker import SpoofChecker
from typing import List, Dict, Optional

class FaceDetectionRecognition:
    def __init__(
        self,
        Detection_model_weights: str=None,
        Recognition_model_weights: str=None,
        SpoofChecker_model_weights: str=None,
        Detection_Model_device: str = "cpu",
        Recognition_Model_device: str = "cpu",
        Spoof_Model_device: str = "cpu",
        Models_Weights_dir: str = "Models_Weights",
        Recognition_model_name:str="r100",
        Recognition_Threshold=0.25,
        Anti_Spoof_threshold=0.25,
        Recognition_Metric="cosine_similarity",
        logger: str = None,
    ):
        # Logger initialization: Create a file and stream logger if no logger is provided.
        #_________________________________________________________________________#
        if isinstance(logger,str):
            self.logs = LOGGER(logger)
            self.logs.create_File_logger(f"{logger}",log_levels=["DEBUG", "INFO", "ERROR", "CRITICAL", "WARNING"])
            self.logs.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
        elif isinstance(logger,LOGGER):
            self.logs=logger
        else:
            self.logs = LOGGER(None)
        #_________________________________________________________________________#
    #------------------------------------------------------------------------------------------------------------------#
        root_path=get_paths().get("APPLICATION_ROOT_PATH")
        #------------------------------------------------------
        if(Detection_model_weights is not None):
            Detection_model_weights_path=os.path.join(root_path,Models_Weights_dir,"face_detection",Detection_model_weights)
        else:
            Detection_model_weights_path=None
        #------------------------------------------------------
        if(Recognition_model_weights is not None):
            Recognition_model_weights_path=os.path.join(root_path,Models_Weights_dir,"face_recognition",Recognition_model_weights)
        else:
            Recognition_model_weights_path=None
        #------------------------------------------------------
        if(SpoofChecker_model_weights is not None):
            SpoofChecker_model_weights_path=os.path.join(root_path,Models_Weights_dir,"face_recognition",SpoofChecker_model_weights)
        else:
            SpoofChecker_model_weights_path=None
    #------------------------------------------------------------------------------------------------------------------#
        # Set the device for model inference (CPU/GPU based on availability).
        self.detection_model_device=Detection_Model_device
        self.recognition_model_device=Recognition_Model_device
        self.spoof_model_device=Spoof_Model_device
        # Set up TensorFlow GPU usage.
        gpus = tf.config.experimental.list_physical_devices("GPU")
        if gpus and all("gpu" not in device.lower() for device in [Detection_Model_device, Recognition_Model_device, Spoof_Model_device]):
            try:
                tf.config.experimental.set_visible_devices([], "GPU")
            except RuntimeError:
                pass
        if "gpu" in Detection_Model_device.lower():
            if gpus:
                try:
                    tf.config.experimental.set_visible_devices(gpus[int(Detection_Model_device[-1])], "GPU" )
                    tf.config.experimental.set_memory_growth(gpus[int(Detection_Model_device[-1])], True)
                    # tf.config.experimental.set_virtual_device_configuration(gpus[int(Detection_Model_device[-1])],[tf.config.experimental.VirtualDeviceConfiguration(memory_limit=4000)]) # MB
                    self.detection_model_device=f"/GPU:{int(Detection_Model_device[-1])}"
                except RuntimeError as e:
                    self.logs.write_logs(e,LOG_LEVEL.ERROR)
        if "gpu" in Recognition_Model_device.lower():
            if gpus:
                try:
                    tf.config.experimental.set_visible_devices(gpus[int(Recognition_Model_device[-1])], "GPU" )
                    tf.config.experimental.set_memory_growth(gpus[int(Recognition_Model_device[-1])], True)
                    # tf.config.experimental.set_virtual_device_configuration(gpus[int(Recognition_Model_device[-1])],[tf.config.experimental.VirtualDeviceConfiguration(memory_limit=4000)]) # MB
                    self.recognition_model_device=f"/GPU:{int(Recognition_Model_device[-1])}"
                except RuntimeError as e:
                    self.logs.write_logs(e,LOG_LEVEL.ERROR)
        if "gpu" in Spoof_Model_device.lower():
            if gpus:
                try:
                    tf.config.experimental.set_visible_devices(gpus[int(Spoof_Model_device[-1])], "GPU" )
                    tf.config.experimental.set_memory_growth(gpus[int(Spoof_Model_device[-1])], True)
                    # tf.config.experimental.set_virtual_device_configuration(gpus[int(Spoof_Model_device[-1])],[tf.config.experimental.VirtualDeviceConfiguration(memory_limit=4000)]) # MB
                    self.spoof_model_device=f"/GPU:{int(Spoof_Model_device[-1])}"
                except RuntimeError as e:
                    self.logs.write_logs(e,LOG_LEVEL.ERROR)
                    
        self.logs.write_logs(f"Using '{self.detection_model_device}' for the Detection Model",LOG_LEVEL.DEBUG)
        self.logs.write_logs(f"Using {self.recognition_model_device} for Recognition Model",LOG_LEVEL.DEBUG)
        self.logs.write_logs(f"Using {self.spoof_model_device} for Spoof Model",LOG_LEVEL.DEBUG)
        #------------------------------------------------------------------------------------------------------------------#
        self.Detect_Faces=DetectFaces(model_weights_path=Detection_model_weights_path,Model_device=self.detection_model_device)
        #------------------------------------------------------------------------------------------------------------------#
        self.Recognition_Face=RecognitionFace(model_weights_path=Recognition_model_weights_path,
                                              Model_device=self.recognition_model_device,
                                              model_name=Recognition_model_name,
                                              Recognition_Metric=Recognition_Metric,
                                              Recognition_Threshold=Recognition_Threshold,
                                              logger=self.logs)
        #------------------------------------------------------------------------------------------------------------------#
        self.Spoof_Checker=SpoofChecker(model_weights_path=SpoofChecker_model_weights_path,Model_device=self.spoof_model_device,Spoof_threshold=Anti_Spoof_threshold,logger=self.logs)
        #------------------------------------------------------------------------------------------------------------------#
        self._ref_cache_lock = threading.Lock()
        self._ref_embeddings: Dict[str, np.ndarray] = {}
        self._ref_versions: Dict[str, float] = {}
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __del__(self):
        if hasattr(self, "Detect_Faces"):
            del self.Detect_Faces
        if hasattr(self, "Recognition_Face"):
            del self.Recognition_Face
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __check_client(self, client_name: str,face_image: np.ndarray,face_bbox: List[int]) -> Dict[str, bool]:
        ref_embedding = self._get_reference_embedding(client_name)
        if ref_embedding is None:
            self.logs.write_logs(
                f"{client_name}-Reference embedding unavailable; skipping identity check",
                LOG_LEVEL.WARNING,
            )
            is_correct_client = False
        else:
            is_correct_client=self.Recognition_Face.recognize_face(
                face_image=face_image,
                ref_embedding=ref_embedding,
            )
        is_spoof=self.Spoof_Checker.check_spoof_face(face_image=face_image,face_bbox=face_bbox)
        return {"check_client": is_correct_client, "check_spoof": is_spoof}
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def pipeline(self, Clients_data):
        """
        Full face detection and recognition pipeline.

        Args:
            image (np.ndarray): Input image for processing.

        Returns:
            dict: A dictionary containing face detection and recognition results.
        """
        image=Clients_data["user_image"]
        client_name=Clients_data["client_name"]
        image=crop_image_center(Clients_data["user_image"],crop_width=640,crop_height=480)
        Clients_data["user_image"]=image
        # Initialize result dictionary for pipeline results
        pipeline_result = {
            "face_bbox":None,
            "face_image":None,
            "check_client": None,
            "check_spoof": None,
            "detection_success": False,
        }
        detection_result = self.Detect_Faces.detect_face(image)
        # Proceed with face recognition if a face was detected.
        face_image=detection_result["face_image"]
        if face_image is not None:
            pipeline_result["detection_success"] = True
            pipeline_result.update(detection_result)
        face_bbox=detection_result["face_bbox"]
        checking_result = self.__check_client(
            client_name=client_name,
            face_image=face_image,
            face_bbox=face_bbox
            )
        pipeline_result.update(checking_result)
        return pipeline_result
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def _get_reference_embedding(self, client_name: str) -> Optional[np.ndarray]:
        paths = get_paths()
        image_path = os.path.join(
            paths["USERS_DATABASE_ROOT_PATH"],
            client_name,
            f"{client_name}_1.jpg",
        )
        try:
            current_version = os.path.getmtime(image_path)
        except FileNotFoundError:
            self.logs.write_logs(
                f"{client_name}-Reference image not found at {image_path}",
                LOG_LEVEL.ERROR,
            )
            return None

        with self._ref_cache_lock:
            cached_version = self._ref_versions.get(client_name)
            if (
                cached_version is not None
                and cached_version >= current_version
                and client_name in self._ref_embeddings
            ):
                return self._ref_embeddings[client_name]

        ref_image = get_client_image(client_name)
        if ref_image is None or ref_image.size == 0:
            self.logs.write_logs(
                f"{client_name}-Reference image is empty or None",
                LOG_LEVEL.ERROR,
            )
            return None

        detection_result = self.Detect_Faces.detect_face(ref_image)
        ref_face = detection_result.get("face_image")
        if ref_face is None:
            # Fall back to centered crop if detection fails
            ref_face = crop_image_center(ref_image, crop_width=320, crop_height=320)

        try:
            embedding = self.Recognition_Face.get_embedding(ref_face)
        except Exception as exc:  # pylint: disable=broad-except
            self.logs.write_logs(
                f"{client_name}-Failed to compute reference embedding: {exc}",
                LOG_LEVEL.ERROR,
            )
            return None

        with self._ref_cache_lock:
            self._ref_embeddings[client_name] = embedding
            self._ref_versions[client_name] = current_version
        return embedding.copy()
