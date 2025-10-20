
import numpy as np
from .FasNet import Fasnet
from typing import Union
from common_utilities import LOGGER,LOG_LEVEL
class SpoofChecker:
    def __init__(self,model_weights_path: str,Model_device: str = "cpu",Spoof_threshold=0.75,logger:Union[str,LOGGER]=None):
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
        self.Spoof_threshold=Spoof_threshold
        self.antispoof_model:Fasnet =self.__deepface_spoofing_models(model_name="Fasnet")
        self.__cache_models()
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __cache_models(self):
        dummy_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        dummy_facial_area = [50, 50, 100, 100]  # x, y, w, h
        self.antispoof_model.analyze(dummy_image,dummy_facial_area)
        self.logs.write_logs("'SpoofChecker' Model is Cached !!",LOG_LEVEL.INFO)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __del__(self):
        if hasattr(self, "antispoof_model"):
            del self.antispoof_model
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def check_spoof_face(self, face_image: np.ndarray, face_bbox: list) -> bool:
        """
        Perform anti-spoofing detection on the face image using DeepFace.
        Args:
            face_image (np.ndarray): The input face image.
        Returns:
            bool: True if the face is spoofed, False otherwise.
        """
        is_real, antispoof_score = self.antispoof_model.analyze(
            img=face_image,
            facial_area=(
                face_bbox[0],
                face_bbox[1],
                face_bbox[2] - face_bbox[0],
                face_bbox[3] - face_bbox[1],
            ),
        )
        return True if is_real == False and antispoof_score >= self.Spoof_threshold else False
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __deepface_spoofing_models(self,model_name):
        spoofing= {
            "Fasnet":Fasnet,
        }
        return spoofing[model_name](self.device)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////