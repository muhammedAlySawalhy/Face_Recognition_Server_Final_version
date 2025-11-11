import threading
from typing import List, Union

import torch
import ultralytics
import ultralytics.engine
import ultralytics.engine.results

from common_utilities import LOGGER, LOG_LEVEL
class ObjectDetection:
    def __init__(
        self,
        model_weights_path: str,
        Model_device: str = "cpu",
        class_number:int=67,
        confidence_threshold:int=65,
        logger:Union[str,LOGGER]=None):
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
        self.class_number=class_number
        self.device = self._resolve_device(Model_device)
        self.confidence_threshold:float=float(confidence_threshold)/100.0 if int(confidence_threshold)<100 else 1.0
        self.model_weights_path = model_weights_path

        # Each worker thread gets its own YOLO instance so concurrent calls never share state.
        self._thread_local = threading.local()
        self._models_registry = []

        base_model = self._build_detection_model()
        self._thread_local.model = base_model
        self.logs.write_logs(
            f"Phone detection YOLO model running on '{self.device}'.",
            LOG_LEVEL.INFO,
        )

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
        model = (
            ultralytics.YOLO(self.model_weights_path, verbose=False)
            .to(self.device, dtype=torch.float32)
        )
        # Explicitly keep inference in FP32 to avoid CUDA misaligned address faults.
        model.overrides["half"] = False
        model.model.float()
        self.__cache_model(model)
        self._models_registry.append(model)
        return model

    def _get_thread_model(self) -> ultralytics.YOLO:
        model = getattr(self._thread_local, "model", None)
        if model is None:
            self.logs.write_logs(
                f"Initializing phone detection model for thread '{threading.current_thread().name}'.",
                LOG_LEVEL.DEBUG,
            )
            model = self._build_detection_model()
            self._thread_local.model = model
        return model

    def __cache_model(self, model: ultralytics.YOLO):
        dummy_input = torch.randn(1, 3, 224, 224, device=self.device, dtype=torch.float32) / 255
        # Warm up to populate CUDA kernels for this instance.
        _ = model(dummy_input, verbose=False)
        self.logs.write_logs("'ObjectDetection' Model is Cached !!",LOG_LEVEL.INFO)

    def detect_object(self, image):
        detection_model = self._get_thread_model()
        results: List[ultralytics.engine.results.Results] = detection_model(image, verbose=False)
        phone_data = {"phone_bbox": None, "phone_confidence": None}
        for cls_result in results[0]:
            cls_boxes = cls_result.boxes
            cls = cls_boxes.cls.item()
            confidence = cls_boxes.conf.item()
            x1, y1, x2, y2 = map(int, cls_boxes.xyxy[0])
            if (cls == self.class_number and confidence >= self.confidence_threshold):
                phone_data.update({"phone_bbox": [x1, y1, x2, y2], "phone_confidence": confidence})
        return phone_data
