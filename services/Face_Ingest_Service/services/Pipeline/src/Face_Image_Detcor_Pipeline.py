from .face_image_detcor_pipeline_interface import FaceImageDetectorPipelineInterface
from services.Face_Detector.src.Face_Detector import Face_Detector,FaceBox
from services.Face_Aligner.src.Face_Aligner import FaceAligner
import numpy as np


class FaceImageDetectorPipeline(FaceImageDetectorPipelineInterface):
    def __init__(self):
        self.__Face_Detector = Face_Detector()
        self.__Face_Aligner = FaceAligner()

    def _crop_square(
        self,
        image_data: np.ndarray,
        face_data: FaceBox,
        pad_scale: float = 1.05,
        upward_bias: float = 0.1,
    ):
        """
        Crop a square around the detected face with gentle padding so hair/ears remain.
        The aligned output is later resized to 340x340 by the aligner.
        """
        h, w, _ = image_data.shape
        cx = int(face_data.x + face_data.w / 2)
        cy = int(face_data.y + face_data.h / 2)

        # Base crop on the larger face dimension, add small padding
        size = int(max(face_data.w, face_data.h) * pad_scale)
        size = max(1, min(size, min(h, w)))  # stay within image bounds

        half = size // 2
        x0 = max(0, cx - half)
        # Bias crop upward to reduce torso inclusion while keeping hair
        y0 = max(0, int(cy - half - upward_bias * size))
        x1 = x0 + size
        y1 = y0 + size

        # Adjust if we hit image borders
        if x1 > w:
            shift = x1 - w
            x0 = max(0, x0 - shift)
            x1 = w
        if y1 > h:
            shift = y1 - h
            y0 = max(0, y0 - shift)
            y1 = h

        face_crop = image_data[y0:y1, x0:x1]
        return face_crop, {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)}

    def process_image(self, image_data: np.ndarray, metadata: dict[str, str]) -> bool:
        face_data = self.__Face_Detector.detect_one(image=image_data)
        if face_data is None:
            return False

        face_crop, face_box = self._crop_square(image_data, face_data, pad_scale=1.1)
        if face_crop.size == 0:
            return False

        aligned_face = self.__Face_Aligner.align_image(face_crop, face_crop.shape[1], face_crop.shape[0])
        if aligned_face is None:
            return False
        return {
            "aligned_face": aligned_face,
            "client_name": metadata.get("client_name", ""),
            "face_data": face_box,
        }
