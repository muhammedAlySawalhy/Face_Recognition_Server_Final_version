import cv2
import mediapipe as mp
import numpy as np

from .face_detect_interface import FaceDetector, FaceBox


class Face_Detector(FaceDetector):
    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence
        self.detector = mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=min_confidence
        )
    def detect_one(self, image: np.ndarray) -> FaceBox | None:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result = self.detector.process(rgb)
        if not result.detections:
            return None

        best = max(result.detections, key=lambda d: d.score[0] if d.score else 0.0)
        score = best.score[0] if best.score else 0.0
        if score < self.min_confidence:
            return None

        h, w, _ = image.shape
        bbox = best.location_data.relative_bounding_box
        x0 = max(0, int(bbox.xmin * w))
        y0 = max(0, int(bbox.ymin * h))
        x1 = min(w, int((bbox.xmin + bbox.width) * w))
        y1 = min(h, int((bbox.ymin + bbox.height) * h))
        width = max(0, x1 - x0)
        height = max(0, y1 - y0)
        if width == 0 or height == 0:
            return None

        return FaceBox(x=x0, y=y0, w=width, h=height)
