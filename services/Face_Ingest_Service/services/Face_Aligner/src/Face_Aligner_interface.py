import numpy as np
from abc import ABC 
class FaceBoxAligned(ABC):
    def __init__(self, x: int, y: int, w: int, h: int, image: bytes | None = None):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.image = image


class FaceAligner(ABC):
    def align_image(self, image: np.ndarray, w: int, h: int) -> FaceBoxAligned | None:
        pass
