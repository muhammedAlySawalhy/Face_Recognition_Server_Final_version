import torch
import ultralytics
from supervision import Detections
import numpy as np
from typing import Union
from common_utilities import LOGGER,LOG_LEVEL,crop_image_bbox

class DetectFaces:
    def __init__(self,
        model_weights_path: str,
        Model_device: str = "cpu",
        logger:Union[str,LOGGER]=None
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
        self.device=Model_device
        self.model_weights_path=model_weights_path
        # Load the YOLO face detection model with the specified weights.
        self.detection_model:ultralytics.YOLO = ultralytics.YOLO(model_weights_path, verbose=False).to(self.device)
        self.__cache_model()
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __del__(self):
        if hasattr(self, "detection_model"):
            del self.detection_model
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __cache_model(self):
        """
        Cache the face detection and recognition models by performing dummy inferences to avoid cold starts during actual use.
        """
        dummy_input = torch.randn(1, 3, 224, 224) / 255
        dummy_input.to(self.device)
        _ = self.detection_model(dummy_input,verbose=False)
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
        output = self.detection_model(image, verbose=False)
        results = Detections.from_ultralytics(output[0])
        # If a face is detected, crop and return the face region.
        if len(results.data["class_name"]) != 0:
            bbox:np.ndarray=None
            for bbox in results.xyxy:
                x1, y1, x2, y2 = map(int, bbox.tolist())
                cropped_img = crop_image_bbox(image, [x1, y1, x2, y2], 240)
                return {
                    "face_bbox": [x1, y1, x2, y2],
                    "face_image": cropped_img,
                }
        # If no face is detected, return None values.
        return {"face_bbox": None, "face_image": None}
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////