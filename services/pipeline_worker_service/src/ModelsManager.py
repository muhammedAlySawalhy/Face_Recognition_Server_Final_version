#!/usr/bin/env python3.10
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
import torch
import gc
from common_utilities import LOGGER,LOG_LEVEL
from typing import Union
from .Object_Detection_Task.PhoneDetection import PhoneDetection
from .Face_Recognition_Anti_Spoof_Task.FaceDetectionRecognition  import FaceDetectionRecognition
class ModelsManager:
    __IS_INITIALIZE=False
    def __init__(self,
                # Models Weights
                Models_Weights_dir:str="Models_Weights",
                ObjectDetection_model_weights:str="phone_detection.pt",
                FaceDetection_model_weights:str="yolov8_model.pt",
                FaceRecognition_model_weights:str="arcface_r100.pth",
                FaceSpoofChecker_model_weights:str= None,
                #Models Devices
                Object_Detection_Models_device:str="cuda:0",
                Face_Detection_Model_device:str="GPU:0",
                Face_Recognition_Model_device:str="GPU:0",
                spoof_Models_device:str="cuda:0",
                #models_parameters
                Recognition_model_name:str="r100",
                Recognition_Threshold=0.25,
                Anti_Spoof_threshold:int=65,
                Recognition_Metric="cosine_similarity",
                Object_class_number:int=67,
                Object_threshold:int=65,
                #Logger
                logger:Union[str]=None,
                storage_client=None
                ):
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
        self.__phone_model = PhoneDetection(
                                # Models Weights
                                Models_Weights_dir=Models_Weights_dir,
                                ObjectDetection_model_weights=ObjectDetection_model_weights,
                                #Models Devices
                                torch_Models_device=Object_Detection_Models_device,
                                #models_parameters
                                Object_class_number=Object_class_number,
                                Object_threshold=Object_threshold,
                                #Logger
                                logger=self.logs
                                )
        #--------------------------------------------
        self.__face_model = FaceDetectionRecognition(
                                # Models Weights
                                Models_Weights_dir=Models_Weights_dir,
                                Detection_model_weights=FaceDetection_model_weights,
                                Recognition_model_weights=FaceRecognition_model_weights,
                                SpoofChecker_model_weights= FaceSpoofChecker_model_weights,
                                #Models Devices
                                Detection_Model_device=Face_Detection_Model_device,
                                Recognition_Model_device=Face_Recognition_Model_device,
                                Spoof_Model_device=spoof_Models_device,
                                #models_parameters
                                Recognition_model_name=Recognition_model_name,
                                Recognition_Threshold=Recognition_Threshold,
                                Recognition_Metric=Recognition_Metric,
                                Anti_Spoof_threshold=Anti_Spoof_threshold,
                                #Logger
                                logger=self.logs,
                                storage_client=storage_client
                                
                                )
        #_________________________________________________________________________#
        self.__IS_INITIALIZE=True
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __del__(self):
        if hasattr(self, "__phone_model"):
            del self.__phone_model
        if hasattr(self, "__face_model"):
            del self.__face_model
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        tf.keras.backend.clear_session()
        gc.collect()
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def phone_model_pipeline(self,client_data:dict):
        return self.__phone_model.pipeline(client_data)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def face_model_pipeline(self,client_data:dict):
        return self.__face_model.pipeline(client_data)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def models_pipeline(self,client_data:dict):
        pipeline_result=dict()
        p_pipeline_result =self.phone_model_pipeline(client_data)
        f_pipeline_result =self.face_model_pipeline(client_data)
        pipeline_result={**f_pipeline_result,**p_pipeline_result,**client_data}
        return pipeline_result
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    @property
    def IS_INITIALIZE(self):
        return self.__IS_INITIALIZE
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

