from abc import ABC
class StorageWriterInterface(ABC):
    def write_data(self, client_data: dict[str, str | bytes], destination: str) -> bool:
        pass
