import threading
from typing import Union

import numpy as np
import torch
import ultralytics
from supervision import Detections

from common_utilities import LOGGER, LOG_LEVEL, crop_image_bbox

class DetectFaces:
    def __init__(
        self,
        model_weights_path: str,
        Model_device: str = "cpu",
        confidence: float = 0.15,
        logger: Union[str, LOGGER] = None,
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
        self.device = self._resolve_device(Model_device)
        self.model_weights_path = model_weights_path
        self.confidence_threshold = max(0.0, min(1.0, confidence))
        self._thread_local = threading.local()
        self._models_registry = []

        base_model = self._build_detection_model()
        self._thread_local.model = base_model
        self.logs.write_logs(
            f"Face detection YOLO model running on '{self.device}'.",
            LOG_LEVEL.INFO,
        )
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __del__(self):
        if hasattr(self, "_models_registry"):
            for model in self._models_registry:
                try:
                    del model
                except Exception:
                    pass
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def _resolve_device(self, model_device: Union[str, torch.device, None]) -> torch.device:
        """
        Normalize the requested device string (cpu/gpu/cuda) and gracefully fall back to CPU if CUDA is unavailable.
        """
        if isinstance(model_device, torch.device):
            resolved_device = model_device
        else:
            requested = (model_device or "cpu").strip()
            normalized = requested.lower()
            if normalized.startswith("gpu"):
                requested = f"cuda{requested[3:]}"
            try:
                resolved_device = torch.device(requested)
            except (TypeError, ValueError, RuntimeError):
                self.logs.write_logs(
                    f"Invalid device '{model_device}'. Falling back to CPU.",
                    LOG_LEVEL.WARNING,
                )
                resolved_device = torch.device("cpu")
        if resolved_device.type == "cuda" and not torch.cuda.is_available():
            self.logs.write_logs(
                f"CUDA device '{resolved_device}' requested but CUDA is not available. Falling back to CPU.",
                LOG_LEVEL.WARNING,
            )
            return torch.device("cpu")
        return resolved_device

    def _build_detection_model(self) -> ultralytics.YOLO:
        detection_model:ultralytics.YOLO = (
            ultralytics.YOLO(self.model_weights_path, verbose=False)
            .to(self.device, dtype=torch.float32)
        )
        # Explicitly disable mixed-precision to avoid CUDA misaligned address faults.
        detection_model.overrides["half"] = False
        detection_model.model.float()
        self.__cache_model(detection_model)
        self._models_registry.append(detection_model)
        return detection_model

    def _get_thread_model(self) -> ultralytics.YOLO:
        model = getattr(self._thread_local, "model", None)
        if model is None:
            self.logs.write_logs(
                f"Initializing face detection model for thread '{threading.current_thread().name}'.",
                LOG_LEVEL.DEBUG,
            )
            model = self._build_detection_model()
            self._thread_local.model = model
        return model

    def __cache_model(self, model: ultralytics.YOLO):
        """
        Cache the face detection model by performing a dummy inference per-thread to avoid cold starts.
        """
        dummy_input = torch.randn(1, 3, 224, 224, device=self.device, dtype=torch.float32) / 255
        _ = model(dummy_input, verbose=False, conf=self.confidence_threshold)
        self.logs.write_logs("'DetectFaces' Model is Cached !!",LOG_LEVEL.INFO)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def detect_face(self, image):
        """
        Detect faces in an input image using the YOLO model.
        Args:
            image (np.ndarray): The input image for face detection.
        Returns:
            dict: A dictionary containing the bounding box of the detected face and the cropped face image.
        """
        detection_model = self._get_thread_model()
        output = detection_model(image, verbose=False, conf=self.confidence_threshold)
        results = Detections.from_ultralytics(output[0])
        # If a face is detected, crop and return the face region.
        if results.xyxy is not None and len(results.xyxy) > 0:
            for bbox in results.xyxy:
                x1, y1, x2, y2 = map(int, bbox.tolist())
                cropped_img = crop_image_bbox(image, [x1, y1, x2, y2], 340)
                return {
                    "face_bbox": [x1, y1, x2, y2],
                    "face_image": cropped_img,
                }
        # If no face is detected, return None values.
        return {"face_bbox": None, "face_image": None}

    def detect_face_bbox(self, image):
        """Convenience helper to return only bbox for downstream cropping."""
        result = self.detect_face(image)
        bbox = result.get("face_bbox") if isinstance(result, dict) else None
        if bbox is None:
            return None
        return {"face_bbox": bbox}
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
