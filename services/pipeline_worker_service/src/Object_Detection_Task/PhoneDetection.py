#!/usr/bin/env python3.10
import os
from .ObjectDetection import ObjectDetection
from common_utilities import LOGGER
from common_utilities import get_paths



class PhoneDetection:
    def __init__(
        self,
        ObjectDetection_model_weights: str=None,
        torch_Models_device: str = "gpu",
        Models_Weights_dir: str = "Models_Weights",
        Object_class_number:int=67,
        Object_threshold:int=65,
        logger: str =None,
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
        root_path=get_paths().get("APPLICATION_ROOT_PATH")
        #------------------------------------------------------
        if(ObjectDetection_model_weights is not None):
            ObjectDetection_model_weights_path=os.path.join(root_path,Models_Weights_dir,"phone_detection",ObjectDetection_model_weights)
        else:
            ObjectDetection_model_weights_path=None
        #------------------------------------------------------------------------------------------------------------------#
        self.device=torch_Models_device
        #------------------------------------------------------------------------------------------------------------------#
        self.phone_detection=ObjectDetection(ObjectDetection_model_weights_path,torch_Models_device,class_number=Object_class_number,confidence_threshold=Object_threshold,logger=self.logs)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __del__(self):
        if hasattr(self, "phone_detection"):
            del self.phone_detection
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def pipeline(self, Clients_data):
        """
        Combines phone detection and action decision into a single pipeline.
        :param image: The input image where phones will be detected.
        :param client_name: The username of the user.
        :return: A dictionary with the action and reason.
        """
        image = Clients_data["user_image"]
        # Step 1: Detect phone in the image
        phone_data = self.phone_detection.detect_object(image)

        # Step 2: Prepare the data for action decision
        pipeline_result = {
            "phone_bbox": phone_data["phone_bbox"],
            "phone_confidence": phone_data["phone_confidence"],
        }
        return pipeline_result
