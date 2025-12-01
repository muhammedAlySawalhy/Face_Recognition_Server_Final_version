import numpy as np
from .src import Face_Aligner
def main():
    image = np.zeros((640, 480, 3), dtype=np.uint8)
    face_aligner = Face_Aligner.FaceAligner(image)
    aligned_face = face_aligner.align_image(image, 324, 324)
    if aligned_face:
        print(f"Aligned face at: {aligned_face.x}, {aligned_face.y}, {aligned_face.w}, {aligned_face.h}")
    else:
        print("No face aligned.")
    