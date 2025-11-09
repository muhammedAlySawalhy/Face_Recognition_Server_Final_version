#!/usr/bin/env python3.10
import hashlib
import os
import threading
import torch
import tensorflow as tf
from common_utilities import crop_image_center,LOGGER,LOG_LEVEL, get_paths, get_namespace
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
        Detection_confidence: float = 0.15,
        logger: str = None,
        storage_client=None,
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
        self._storage_client = storage_client
        self._recognition_model_name = Recognition_model_name
        self._recognition_model_weights = Recognition_model_weights
        self.recognition_metric = Recognition_Metric
        self._embedding_signature = self._build_embedding_signature()
        self._namespace = get_namespace() or "default"
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
        self.Detect_Faces=DetectFaces(
            model_weights_path=Detection_model_weights_path,
            Model_device=self.detection_model_device,
            confidence=Detection_confidence,
        )
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
    def _current_namespace(self) -> str:
        namespace = get_namespace()
        if namespace:
            self._namespace = namespace
        return self._namespace

    def _build_embedding_signature(self) -> str:
        payload = "|".join(
            [
                self._recognition_model_name or "unknown",
                self._recognition_model_weights or "weights",
                self.recognition_metric or "metric",
            ]
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def _load_embedding_from_storage(
        self, client_name: str, source_mtime: float
    ) -> Optional[np.ndarray]:
        if not self._storage_client:
            return None
        record = self._storage_client.load_embedding(
            self._current_namespace(), self._embedding_signature, client_name
        )
        if not record:
            return None
        vector, metadata = record
        stored_mtime = metadata.get("source_mtime")
        if stored_mtime != source_mtime:
            return None
        return vector

    def _persist_embedding_to_storage(
        self, client_name: str, embedding: np.ndarray, source_mtime: float, image_path: str
    ) -> None:
        if not self._storage_client:
            return
        metadata = {
            "model_signature": self._embedding_signature,
            "model_name": self._recognition_model_name,
            "model_weights": self._recognition_model_weights,
            "metric": self.recognition_metric,
            "source_mtime": source_mtime,
            "source_image": image_path,
        }
        try:
            self._storage_client.save_embedding(
                self._current_namespace(),
                self._embedding_signature,
                client_name,
                embedding,
                metadata=metadata,
            )
            self.logs.write_logs(
                f"{client_name}-Reference embedding stored in MinIO cache",
                LOG_LEVEL.DEBUG,
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.logs.write_logs(
                f"{client_name}-Failed to persist embedding cache: {exc}",
                LOG_LEVEL.WARNING,
            )
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
            recognition_details = {
                "verified": False,
                "threshold": self.Recognition_Face.recognition_threshold,
                "distance": None,
            }
        else:
            recognition_details = self.Recognition_Face.recognize_face(
                face_image=face_image,
                ref_embedding=ref_embedding,
                return_details=True,
            )
            is_correct_client = bool(recognition_details.get("verified"))
            self.logs.write_logs(
                f"{client_name}-Recognition score={recognition_details.get('distance')} "
                f"threshold={recognition_details.get('threshold')} verified={is_correct_client}",
                LOG_LEVEL.DEBUG,
            )
        is_spoof=self.Spoof_Checker.check_spoof_face(face_image=face_image,face_bbox=face_bbox)
        self.logs.write_logs(
            f"{client_name}-Spoof check result={is_spoof}",
            LOG_LEVEL.DEBUG,
        )
        return {
            "check_client": is_correct_client,
            "check_spoof": is_spoof,
            "recognition_threshold": recognition_details.get("threshold"),
            "recognition_metric_value": recognition_details.get("distance"),
        }
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def pipeline(self, Clients_data):
        """
        Full face detection and recognition pipeline.

        Args:
            image (np.ndarray): Input image for processing.

        Returns:
            dict: A dictionary containing face detection and recognition results.
        """
        image = Clients_data.get("user_image")
        client_name = Clients_data.get("client_name", "unknown")
        # Initialize result dictionary for pipeline results
        pipeline_result = {
            "face_bbox":None,
            "face_image":None,
            "check_client": None,
            "check_spoof": None,
            "detection_success": False,
        }
        # Validate the incoming frame before any processing to avoid NoneType errors.
        if image is None:
            self.logs.write_logs(
                f"{client_name}-Received empty frame payload", LOG_LEVEL.WARNING
            )
            return pipeline_result
        if not isinstance(image, np.ndarray):
            self.logs.write_logs(
                f"{client_name}-Frame payload is not a numpy array ({type(image)})",
                LOG_LEVEL.WARNING,
            )
            return pipeline_result
        if image.size == 0:
            self.logs.write_logs(
                f"{client_name}-Received frame with zero size", LOG_LEVEL.WARNING
            )
            return pipeline_result
        image = crop_image_center(image, crop_width=960, crop_height=720)
        if image is None or image.size == 0:
            self.logs.write_logs(
                f"{client_name}-Cropping produced an empty frame", LOG_LEVEL.WARNING
            )
            return pipeline_result
        Clients_data["user_image"]=image
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
                self.logs.write_logs(
                    f"{client_name}-Using cached reference embedding (mtime={current_version})",
                    LOG_LEVEL.DEBUG,
                )
                return self._ref_embeddings[client_name]

        storage_embedding = self._load_embedding_from_storage(
            client_name, current_version
        )
        if storage_embedding is not None and storage_embedding.size:
            with self._ref_cache_lock:
                self._ref_embeddings[client_name] = storage_embedding
                self._ref_versions[client_name] = current_version
            self.logs.write_logs(
                f"{client_name}-Loaded reference embedding from MinIO cache",
                LOG_LEVEL.INFO,
            )
            return storage_embedding.copy()

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
        self._persist_embedding_to_storage(
            client_name, embedding, current_version, image_path
        )
        self.logs.write_logs(
            f"{client_name}-Reference embedding refreshed (mtime={current_version})",
            LOG_LEVEL.INFO,
        )
        return embedding.copy()
