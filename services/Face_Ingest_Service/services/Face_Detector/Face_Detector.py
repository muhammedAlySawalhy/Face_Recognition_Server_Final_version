from src.Face_Detector import Face_Detector
import numpy as np
def main():
    image = np.zeros((640, 480, 3), dtype=np.uint8)
    face_detector = Face_Detector(image)
    face_box = face_detector.detect_one(image)
    if face_box:
        print(f"Face detected at: {face_box.x}, {face_box.y}, {face_box.w}, {face_box.h}, confidence: {face_box.confidence}")
    else:
        print("No face detected.")
