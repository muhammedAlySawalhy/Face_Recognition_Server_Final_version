import tensorflow as tf
from torchvision import transforms
import torch
import numpy as np
from typing import Dict,Union
from common_utilities import LOGGER,LOG_LEVEL
from .VGGFace import VggFace
from .model import iresnet_inference,IResNet
from .inception_resnet_v1 import InceptionResnetV1
class RecognitionFace:
    def __init__(self,model_weights_path: str=None,
                Model_device: str = "cpu",
                model_name="r100",
                Recognition_Threshold=0.25,
                Recognition_Metric="cosine_similarity",
                logger:Union[LOGGER,str]=None):
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
        self.recognition_threshold=Recognition_Threshold
        self.recognition_metric=Recognition_Metric
        self.input_size=None
        self.recognition_model:Union[IResNet,VggFace,InceptionResnetV1]= self.__recognition_models(model_name=model_name)
        self.__cache_models()
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __del__(self):
        if hasattr(self, "recognition_model"):
            del self.recognition_model
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __cache_models(self):
        """
        
        """
        dummy_input = np.random.randn(240, 240, 3).astype(np.float32)
        self.__find_image_embedding(dummy_input)
        self.logs.write_logs("'RecognitionFace' Model is Cached !!",LOG_LEVEL.INFO)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def recognize_face(self,ref_image: np.ndarray,face_image: np.ndarray,)-> bool:
        """
        """
        __check =self.__verify_face(face_image,ref_image)
        # self.logs.write_logs(f"{__check}",LOG_LEVEL.DEBUG)
        return __check['verified']
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __recognition_models(self,model_name:str)-> Union[IResNet,VggFace,InceptionResnetV1]:
        def _setup_model(model, input_size):
            self.input_size = input_size
            return model
        
        # Factory functions that create models only when called
        __recognition_models: Dict[str, Dict[str, callable]] = {
            "deepface": {
                "VGG_Face": lambda: _setup_model(
                    model=VggFace(self.model_weights_path, self.device), 
                    input_size=(224, 224)
                ),
                "r18": lambda: _setup_model(
                    model=iresnet_inference("r18", self.model_weights_path, self.device),
                    input_size=(112, 112)
                ),
                "r34": lambda: _setup_model(
                    model=iresnet_inference("r34", self.model_weights_path, self.device),
                    input_size=(112, 112)
                ),
                "r50": lambda: _setup_model(
                    model=iresnet_inference("r50", self.model_weights_path, self.device),
                    input_size=(112, 112)
                ),
                "r100": lambda: _setup_model(
                    model=iresnet_inference("r100", self.model_weights_path, self.device),
                    input_size=(112, 112)
                ),
            },
            "facenet": {
                "vggface2": lambda: _setup_model(
                    model=InceptionResnetV1(self.model_weights_path, pretrained="vggface2").eval().to(self.device),
                    input_size=(120, 120)
                ),
                "casia-webface": lambda: _setup_model(
                    model=InceptionResnetV1(self.model_weights_path, pretrained="casia-webface").eval().to(self.device),
                    input_size=(120, 120)
                ),
            }
        }
        
        # Add error handling
        try:
            model_lib, model_architecture = model_name.split("__")
        except ValueError:
            self.logs.write_logs(f"Invalid model_name format: {model_name}. Expected format: 'library__architecture'", LOG_LEVEL.ERROR)
            raise ValueError(f"Invalid model_name format: {model_name}. Expected format: 'library__architecture'")
        
        if model_lib not in __recognition_models:
            self.logs.write_logs(f"Unsupported model library: {model_lib}. Available: {list(__recognition_models.keys())}", LOG_LEVEL.ERROR)
            raise ValueError(f"Unsupported model library: {model_lib}. Available: {list(__recognition_models.keys())}")
        
        if model_architecture not in __recognition_models[model_lib]:
            self.logs.write_logs(f"Unsupported architecture '{model_architecture}' for library '{model_lib}'. Available: {list(__recognition_models[model_lib].keys())}", LOG_LEVEL.ERROR)
            raise ValueError(f"Unsupported architecture '{model_architecture}' for library '{model_lib}'. Available: {list(__recognition_models[model_lib].keys())}")
        
        # Create and return the model instance
        _model: Union[IResNet, VggFace, InceptionResnetV1] = __recognition_models[model_lib][model_architecture]()
        return _model
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __find_image_embedding(self, image: np.ndarray) -> np.ndarray:
        #------------------------------------------------------------------- IResNet -------------------
        if isinstance(self.recognition_model, IResNet):
            # IResNet preprocessing (112x112, normalized [-1,1])
            preprocess = transforms.Compose([
                transforms.ToPILImage(mode="RGB"),
                transforms.Resize(self.input_size),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
            ])
            image_input = preprocess(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                emb_img_face = self.recognition_model(image_input).cpu().numpy()
                emb_img_face = emb_img_face / np.linalg.norm(emb_img_face)
            return emb_img_face
        #------------------------------------------------------------------- VGGFace -------------------
        elif isinstance(self.recognition_model, VggFace): 
            # VggFace preprocessing (224x224)
            emb_img_face = self.recognition_model.predict(image)
            if hasattr(emb_img_face, 'numpy'):
                emb_img_face = emb_img_face.numpy()
            return emb_img_face
        #------------------------------------------------------------- InceptionResnetV1 -------------------
        elif isinstance(self.recognition_model, InceptionResnetV1):
            # InceptionResnetV1 preprocessing (160x160, normalized [-1,1])
            preprocess = transforms.Compose([
                transforms.ToPILImage(mode="RGB"),
                transforms.Resize(self.input_size, antialias=True),  # InceptionResnetV1 expects 160x160
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
            ])
            image_input = preprocess(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                emb_img_face = self.recognition_model.forward(image_input).detach().cpu()
                emb_img_face = emb_img_face / np.linalg.norm(emb_img_face)
            return emb_img_face
        #------------------------------------------------------------- Unsupported Model -------------------
        else:
            self.logs.write_logs(f"Unsupported model type: {type(self.recognition_model)}", LOG_LEVEL.ERROR)
            raise ValueError(f"Unsupported model type: {type(self.recognition_model)}")
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __verify_face(self,image:np.ndarray,ref_image:np.ndarray):
        embedding_image=self.__find_image_embedding(image)
        embedding_ref_image=self.__find_image_embedding(ref_image)
        
        # Ensure we're working with NumPy arrays
        if hasattr(embedding_image, 'numpy'):
            embedding_image = embedding_image.numpy()
        if hasattr(embedding_ref_image, 'numpy'):
            embedding_ref_image = embedding_ref_image.numpy()
            
        # Flatten embeddings to 1D if they're not already
        embedding_image = embedding_image.flatten()
        embedding_ref_image = embedding_ref_image.flatten()
        
        if self.recognition_metric == "euclidean":
            min_distance = np.linalg.norm(embedding_image - embedding_ref_image)
            threshold = self.recognition_threshold  # Adjust based on dataset
            verified=(min_distance <= threshold)
        elif self.recognition_metric == "cosine_similarity":  # Default to cosine similarity
            # Calculate cosine similarity properly
            score = np.dot(embedding_image, embedding_ref_image) / (np.linalg.norm(embedding_image) * np.linalg.norm(embedding_ref_image))
            min_distance = score  # Convert similarity to distance
            threshold = self.recognition_threshold  # Adjust threshold
            verified=(min_distance >= threshold)
        return {"threshold":threshold,
                "distance":min_distance,
                "verified":verified}
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////