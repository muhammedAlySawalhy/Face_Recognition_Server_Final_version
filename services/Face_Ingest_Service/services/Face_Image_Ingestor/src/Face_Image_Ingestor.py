import sys
import os
from pathlib import Path

import numpy as np
import cv2
import torch
import ultralytics
from fastapi import FastAPI, HTTPException, Body
import base64
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.Face_Image_Ingestor.src.face_image_ingestor_interface import FaceImageIngestorInterface
from services.Pipeline import PipelineBuilder
from services.Storage_Writer.src.Storage_Writer import StorageWriter

pipeline = PipelineBuilder.PipelineBuilder()
storage_writer = StorageWriter()


def _decode_image(client_image: str | bytes) -> np.ndarray | None:
    """Decode incoming payload (base64 or raw bytes) into a cv2 image."""
    if client_image is None:
        return None
    try:
        if isinstance(client_image, str):
            cleaned = client_image
            if cleaned.startswith("data:image"):
                cleaned = cleaned.split(",", 1)[-1]
            image_bytes = base64.b64decode(cleaned)
        else:
            image_bytes = client_image
        decoded = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return None
    return decoded


class PhoneDetector:
    """YOLO-based phone detector for reuse by the ingestion service."""

    def __init__(
        self,
        weights_path: str,
        class_id: int = 67,
        confidence_threshold: float = 0.35,
        device: str = "cpu",
    ):
        self.weights_path = weights_path
        self.class_id = class_id
        self.confidence_threshold = confidence_threshold
        self.device = self._resolve_device(device)
        self._model: ultralytics.YOLO | None = None

    def _resolve_device(self, requested: str) -> torch.device:
        normalised = (requested or "cpu").lower().strip()
        if normalised.startswith("gpu"):
            normalised = f"cuda{normalised[3:]}"
        try:
            resolved = torch.device(normalised)
        except Exception:
            resolved = torch.device("cpu")
        if resolved.type == "cuda" and not torch.cuda.is_available():
            return torch.device("cpu")
        return resolved

    def _ensure_model(self) -> ultralytics.YOLO:
        if self._model is None:
            model = ultralytics.YOLO(self.weights_path, verbose=False).to(self.device, dtype=torch.float32)
            model.overrides["half"] = False
            model.model.float()
            dummy_input = torch.randn(1, 3, 224, 224, device=self.device, dtype=torch.float32) / 255
            _ = model(dummy_input, verbose=False)
            self._model = model
        return self._model

    def detect_phone(self, image: np.ndarray):
        model = self._ensure_model()
        results = model(image, verbose=False)
        best_bbox = None
        best_conf = None
        for cls_result in results[0]:
            cls_boxes = cls_result.boxes
            cls = cls_boxes.cls.item()
            conf = float(cls_boxes.conf.item())
            if cls == self.class_id and conf >= self.confidence_threshold:
                x1, y1, x2, y2 = map(int, cls_boxes.xyxy[0])
                if best_conf is None or conf > best_conf:
                    best_conf = conf
                    best_bbox = [x1, y1, x2, y2]
        if best_bbox is None:
            return None
        return {"phone_bbox": best_bbox, "phone_confidence": best_conf}


class FaceImageIngestor(FaceImageIngestorInterface):
    def ingest_image(self, client_image: str | bytes, metadata: dict[str, str]) -> bool:
        decoded = _decode_image(client_image)
        if decoded is None:
            return False

        pipeline.add_image(image_data=decoded, metadata=metadata)

        print(f"Image ingested with metadata: {metadata}")
        return True

    def detect_and_align(self, client_image: str | bytes, metadata: dict[str, str] | None = None):
        decoded = _decode_image(client_image)
        if decoded is None:
            raise ValueError("Unable to decode image payload")

        result = pipeline.pipeline.process_image(decoded, metadata or {})
        if not result or not result.get("aligned_face"):
            raise ValueError("No face detected in image")

        face_box = result.get("face_data", {})
        face_box = {
            "x": int(face_box.get("x", 0)),
            "y": int(face_box.get("y", 0)),
            "w": int(face_box.get("w", 0)),
            "h": int(face_box.get("h", 0)),
        }
        aligned_bytes = result["aligned_face"].image
        if not aligned_bytes:
            raise ValueError("Aligned face payload missing")

        return {
            "aligned_face_bytes": aligned_bytes,
            "face_bbox": face_box,
            "metadata": metadata or {},
        }


app = FastAPI()
ingestor = FaceImageIngestor()
phone_detector_weights = os.getenv("PHONE_DETECTION_WEIGHTS", "Models_Weights/phone_detection/phone_detection.pt")
phone_detector_class = int(os.getenv("PHONE_DETECTION_CLASS", "67"))
phone_detector_conf = float(os.getenv("PHONE_DETECTION_THRESHOLD", "0.35"))
phone_detector_device = os.getenv("PHONE_DETECTION_DEVICE", "cpu")
phone_detector: PhoneDetector | None = None
if Path(phone_detector_weights).exists():
    phone_detector = PhoneDetector(
        weights_path=phone_detector_weights,
        class_id=phone_detector_class,
        confidence_threshold=phone_detector_conf,
        device=phone_detector_device,
    )


@app.post("/ingest_image/")
async def ingest_image_endpoint(
    client_image: str | bytes = Body(..., description="Base64 or raw bytes image"),
    metadata: dict[str, str] = Body({}, description="Arbitrary metadata"),
):
    try:
        success = ingestor.ingest_image(client_image, metadata)
        if not success:
            raise ValueError("Failed to decode or process image")
        return {"success": success}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid image payload: {exc}")


@app.post("/detect")
async def detect_face_endpoint(
    payload: dict = Body(..., description="Payload containing base64 image and optional metadata")
):
    client_image = payload.get("image") or payload.get("client_image")
    metadata = payload.get("metadata") or {}
    try:
        result = ingestor.detect_and_align(client_image, metadata)
        encoded_face = base64.b64encode(result["aligned_face_bytes"]).decode("utf-8")
        return {
            "aligned_face_b64": encoded_face,
            "face_bbox": result["face_bbox"],
            "metadata": result["metadata"],
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/detect_phone")
async def detect_phone_endpoint(payload: dict = Body(..., description="Payload containing base64 image")):
    if phone_detector is None:
        raise HTTPException(status_code=503, detail="Phone detector unavailable")
    client_image = payload.get("image") or payload.get("client_image")
    decoded = _decode_image(client_image)
    if decoded is None:
        raise HTTPException(status_code=400, detail="Unable to decode image payload")
    result = phone_detector.detect_phone(decoded)
    if result is None:
        raise HTTPException(status_code=404, detail="No phone detected")
    return result


@app.get("/execute_pipeline/")
async def execute_pipeline(destination: str):
    try:
        results = pipeline.run_pipeline()
        for result in results:
                storage_writer.write_data(result, destination)
        return {"results":[str(r) for r in results]}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
