from abc import ABC
class FaceImageIngestorInterface(ABC):
    def ingest_image(self, client_data: dict[str, str | bytes], metadata: dict[str, str]) -> bool:
        pass