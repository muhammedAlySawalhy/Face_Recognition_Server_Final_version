from .storage_writer_interface import StorageWriterInterface
import os


class StorageWriter(StorageWriterInterface):
    def write_data(self, client_data: dict[str, str | bytes], destination: str) -> bool:
        try:
            os.makedirs(destination, exist_ok=True)
            client_name = client_data.get("client_name", "output")

            # Prefer the aligned face payload if present; fall back to any value with image bytes.
            aligned_value = client_data.get("aligned_face")
            if aligned_value is None:
                aligned_value = next(
                    (v for v in client_data.values() if hasattr(v, "image") or isinstance(v, bytes)), None
                )

            image_bytes = None
            if hasattr(aligned_value, "image"):
                image_bytes = getattr(aligned_value, "image")
            elif isinstance(aligned_value, bytes):
                image_bytes = aligned_value

            if not image_bytes:
                print("No aligned image bytes found in client_data")
                return False

            filename = os.path.join(destination, f"{client_name}_1.jpg")
            with open(filename, "wb") as img_file:
                img_file.write(image_bytes)

            return True
        except Exception as e:
            print(f"Error writing data: {e}")
            return False
