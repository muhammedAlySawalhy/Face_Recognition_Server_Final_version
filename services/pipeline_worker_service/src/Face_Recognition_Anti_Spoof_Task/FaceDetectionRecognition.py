#!/usr/bin/env python3.10
import os
import threading
import tensorflow as tf
import cv2
from common_utilities import LOGGER,LOG_LEVEL, get_paths
from utilities.files_handler import get_client_image
import numpy as np
from .Face_Recognition_Task.RecognitionFace import RecognitionFace
from .Face_Anti_Spoof_Task.SpoofChecker import SpoofChecker
from typing import List, Dict, Optional
from utilities.detection_service import DetectionServiceClient
from .Face_Recognition_Task.DetectFaces import DetectFaces

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
        Detection_service_url: str | None = None,
        Detection_service_timeout: float = 1.5,
        Recognition_model_name:str="r100",
        Recognition_Threshold=0.25,
        Anti_Spoof_threshold=0.25,
        Recognition_Metric="cosine_similarity",
        Detection_confidence: float = 0.15,
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
        # Local YOLO face detector (no HTTP dependency)
        # Local YOLO face detector (no HTTP dependency)
        detection_weights = Detection_model_weights_path if "Detection_model_weights_path" in locals() else None
        self._detect_faces = DetectFaces(
            model_weights_path=detection_weights or Detection_model_weights_path,
            Model_device=self.detection_model_device,
            confidence=0.15,
            logger=self.logs,
        )
        self._detection_client = DetectionServiceClient(
            base_url=None,
            timeout=Detection_service_timeout,
            logger=self.logs,
        )
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __del__(self):
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

        detection_result = self._detect_faces.detect_face_bbox(image)
        fallback_used = False
        if detection_result is None:
            self.logs.write_logs(
                f"{client_name}-Local detection did not return a face; falling back to center crop",
                LOG_LEVEL.WARNING,
            )
            face_image, face_bbox = self._fallback_center_crop(image, target_size=340)
            fallback_used = True if face_image is not None else False
        else:
            face_bbox = detection_result.get("face_bbox") or detection_result.get("bbox")
            face_image, face_bbox = self._crop_square_face(image, face_bbox, target_size=340)

        if face_image is None:
            return pipeline_result

        pipeline_result["detection_success"] = True
        if fallback_used:
            pipeline_result["fallback_crop"] = True
        pipeline_result.update(
            {
                "face_image": face_image,
                "face_bbox": face_bbox,
            }
        )
        checking_result = self.__check_client(
            client_name=client_name,
            face_image=face_image,
            face_bbox=face_bbox
            )
        pipeline_result.update(checking_result)
        return pipeline_result
    #//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def _crop_square_face(self, image: np.ndarray, bbox: List[int], target_size: int = 340):
        if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
            return None, None
        h, w, _ = image.shape
        x0, y0, x1, y1 = bbox
        cx = int((x0 + x1) / 2)
        cy = int((y0 + y1) / 2)
        half = target_size // 2
        new_x0 = max(0, cx - half)
        new_y0 = max(0, cy - half)
        new_x1 = new_x0 + target_size
        new_y1 = new_y0 + target_size
        if new_x1 > w:
            shift = new_x1 - w
            new_x0 = max(0, new_x0 - shift)
            new_x1 = w
        if new_y1 > h:
            shift = new_y1 - h
            new_y0 = max(0, new_y0 - shift)
            new_y1 = h
        face_crop = image[new_y0:new_y1, new_x0:new_x1]
        if face_crop.size == 0:
            return None, None
        resized = cv2.resize(face_crop, (target_size, target_size))
        return resized, [new_x0, new_y0, new_x1, new_y1]

    def _fallback_center_crop(self, image: np.ndarray, target_size: int = 340):
        """
        When detection fails on full-body frames, take a centered crop near the top of the frame.
        This avoids dropping the payload completely while still producing a face-sized patch.
        """
        h, w, _ = image.shape
        half = target_size // 2
        cx = w // 2
        # Bias toward the upper third of the frame where faces usually appear.
        cy = max(half, int(h * 0.25))
        x0 = max(0, cx - half)
        y0 = max(0, cy - half)
        x1 = min(w, x0 + target_size)
        y1 = min(h, y0 + target_size)
        # Re-adjust if we hit borders
        if x1 - x0 < target_size:
            x0 = max(0, x1 - target_size)
        if y1 - y0 < target_size:
            y0 = max(0, y1 - target_size)
        crop = image[y0:y1, x0:x1]
        if crop.size == 0:
            return None, None
        resized = cv2.resize(crop, (target_size, target_size))
        return resized, [x0, y0, x1, y1]

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

        ref_image = get_client_image(client_name)
        if ref_image is None or ref_image.size == 0:
            self.logs.write_logs(
                f"{client_name}-Reference image is empty or None",
                LOG_LEVEL.ERROR,
            )
            return None

        # Reference images are assumed to be pre-cropped/aligned faces.
        ref_face = ref_image

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
        self.logs.write_logs(
            f"{client_name}-Reference embedding refreshed (mtime={current_version})",
            LOG_LEVEL.INFO,
        )
        return embedding.copy()
