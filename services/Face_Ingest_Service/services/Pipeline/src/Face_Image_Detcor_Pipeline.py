from .face_image_detcor_pipeline_interface import FaceImageDetectorPipelineInterface
from services.Face_Detector.src.Face_Detector import Face_Detector
from services.Face_Aligner.src.Face_Aligner import FaceAligner
import numpy as np


class FaceImageDetectorPipeline(FaceImageDetectorPipelineInterface):
    def __init__(self):
        self.__Face_Detector = Face_Detector()
        self.__Face_Aligner = FaceAligner()

    def _crop_square(self, image_data: np.ndarray, face_data: FaceBox, target_size: int = 340):
        h, w, _ = image_data.shape
        cx = int(face_data.x + face_data.w / 2)
        cy = int(face_data.y + face_data.h / 2)
        half = target_size // 2
        x0 = max(0, cx - half)
        y0 = max(0, cy - half)
        x1 = x0 + target_size
        y1 = y0 + target_size

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

        face_crop, face_box = self._crop_square(image_data, face_data, target_size=340)
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
