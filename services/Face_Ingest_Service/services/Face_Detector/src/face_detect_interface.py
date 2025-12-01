import numpy as np
from abc import ABC 
class FaceBox(ABC):
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.confidence = 1.0  

class FaceDetector(ABC):
    def detect_one(image: np.ndarray) -> FaceBox | None:
        pass