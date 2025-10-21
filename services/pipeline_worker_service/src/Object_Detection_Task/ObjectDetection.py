import torch
import ultralytics
import ultralytics.engine
import ultralytics.engine.results
from typing import Union,List
from common_utilities import LOGGER,LOG_LEVEL
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
        self.device = Model_device
        self.confidence_threshold:float=float(confidence_threshold)/100.0 if int(confidence_threshold)<100 else 1.0
        self.detection_model = ultralytics.YOLO(model_weights_path, verbose=False).to(self.device)
        self.__cache_model()

    def __del__(self):
        if hasattr(self, "detection_model"):
            del self.detection_model

    def __cache_model(self):
        dummy_input = torch.randn(1, 3, 224, 224) / 255
        dummy_input.to(self.device)
        _ = self.detection_model(dummy_input,verbose=False)
        self.logs.write_logs("'ObjectDetection' Model is Cached !!",LOG_LEVEL.INFO)

    def detect_object(self, image):
        results: List[ultralytics.engine.results.Results] = self.detection_model(image, verbose=False)
        phone_data = {"phone_bbox": None, "phone_confidence": None}
        for cls_result in results[0]:
            cls_boxes = cls_result.boxes
            cls = cls_boxes.cls.item()
            confidence = cls_boxes.conf.item()
            x1, y1, x2, y2 = map(int, cls_boxes.xyxy[0])
            if (cls == self.class_number and confidence >= self.confidence_threshold):
                phone_data.update({"phone_bbox": [x1, y1, x2, y2], "phone_confidence": confidence})
        return phone_data