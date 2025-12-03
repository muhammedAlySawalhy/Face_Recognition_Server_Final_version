import sys
import os
from pathlib import Path

import numpy as np
import cv2
import torch
import ultralytics
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
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




class FaceImageIngestor(FaceImageIngestorInterface):
    def ingest_image(self, client_image: str | bytes, metadata: dict[str, str]) -> bool:
        decoded = _decode_image(client_image)
        if decoded is None:
            return False

        pipeline.add_image(image_data=decoded, metadata=metadata)

        print(f"Image ingested with metadata: {metadata}")
        return True

   

app = FastAPI()
ingestor = FaceImageIngestor()

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





@app.get("/execute_pipeline/")
async def execute_pipeline(destination: str):
    errors = []
    written = []

    try:
        results = pipeline.run_pipeline()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"pipeline failure: {exc}")

    if not results:
        raise HTTPException(
            status_code=400,
            detail="no queued images to process; call /ingest_image/ first"
        )

    for idx, result in enumerate(results):
        client_name = ""
        try:
            if not result or result is False:
                errors.append({"index": idx, "error": "face detection/align failed"})
                continue

            if not isinstance(result, dict):
                errors.append({"index": idx, "error": f"unexpected pipeline result type: {type(result)}"})
                continue

            client_name = result.get("client_name", "output")
            storage_writer.write_data(result, destination)
            written.append({"index": idx, "client_name": client_name})
        except Exception as exc:
            errors.append({"index": idx, "client_name": client_name, "error": str(exc)})

    status_code = 200
    if errors and written:
        status_code = 207  # Multi-Status: partial success
    elif errors and not written:
        status_code = 400

    return JSONResponse(
        {
            "written": written,
            "errors": errors,
            "results_count": len(results),
        },
        status_code=status_code,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
