from .Face_Aligner_interface import FaceAligner, FaceBoxAligned
import numpy as np
import cv2


class FaceAligner(FaceAligner):
    def __init__(self):
        pass

    def align_image(self, image: np.ndarray, w: int, h: int) -> FaceBoxAligned | None:
        if image is None:
            return None
        try:
            # Normalise the face crop to a fixed 340x340 square to match live detection crops.
            target_size = 340
            resized = cv2.resize(image, (target_size, target_size))
            bytes_image = cv2.imencode(".jpg", resized)[1].tobytes()
        except Exception:
            return None
        # Face detector returns relative coords; we already convert to pixels upstream.
        return FaceBoxAligned(x=0, y=0, w=target_size, h=target_size, image=bytes_image)
