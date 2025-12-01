from queue import Queue
import numpy as np
from services.Pipeline.src.Face_Image_Detcor_Pipeline import FaceImageDetectorPipeline
class PipelineBuilder:
    def __init__(self):
        self.images_queue= Queue()
        self.pipeline = FaceImageDetectorPipeline()
    def add_image(self, image_data: np.ndarray, metadata: dict[str, str]):
        self.images_queue.put((image_data, metadata))
    def run_pipeline(self):
        results = []
        while not self.images_queue.empty():
            image_data, metadata = self.images_queue.get()
            result = self.pipeline.process_image(image_data, metadata)
            results.append(result)
        return results
