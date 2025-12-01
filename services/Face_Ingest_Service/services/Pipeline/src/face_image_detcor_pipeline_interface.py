from abc import ABC
class FaceImageDetectorPipelineInterface(ABC):
    def process_image(self, image_data: bytes, metadata: dict[str, str]) -> bool:
        pass
