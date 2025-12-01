#!/usr/bin/env python3.10
import base64
import os
from typing import Dict, Optional

import cv2
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common_utilities import LOG_LEVEL, LOGGER


class DetectionServiceClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 1.5,
        logger: LOGGER | None = None,
    ):
        self.base_url = (base_url or os.getenv("FACE_DETECTION_SERVICE_URL") or "http://face-ingestor:8010").rstrip("/")
        self.timeout = float(os.getenv("FACE_DETECTION_SERVICE_TIMEOUT", timeout))
        self.logger = logger
        self._session = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["POST"]),
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def detect_face(self, image: np.ndarray) -> Optional[Dict]:
        if image is None or image.size == 0:
            return None
        try:
            encoded_ok, buffer = cv2.imencode(".jpg", image)
            if not encoded_ok:
                return None
            payload = {"image": base64.b64encode(buffer.tobytes()).decode("utf-8")}
            response = self._session.post(
                f"{self.base_url}/detect",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
            face_b64 = body.get("aligned_face_b64")
            bbox = body.get("face_bbox") or body.get("face_data")
            if not face_b64 or not bbox:
                return None
            face_bytes = base64.b64decode(face_b64)
            face_image = cv2.imdecode(np.frombuffer(face_bytes, np.uint8), cv2.IMREAD_COLOR)
            if face_image is None:
                return None
            if isinstance(bbox, dict):
                x = int(bbox.get("x", 0))
                y = int(bbox.get("y", 0))
                w = int(bbox.get("w", 0))
                h = int(bbox.get("h", 0))
            else:
                x = int(bbox[0])
                y = int(bbox[1])
                w = int(bbox[2])
                h = int(bbox[3])
            bbox_list = [x, y, x + w, y + h]
            return {"face_image": face_image, "face_bbox": bbox_list}
        except requests.RequestException as exc:
            if self.logger:
                self.logger.write_logs(
                    f"Detection service error: {exc}",
                    LOG_LEVEL.WARNING,
                )
            return None
        except Exception as exc:  # pylint: disable=broad-except
            if self.logger:
                self.logger.write_logs(
                    f"Detection service failure: {exc}",
                    LOG_LEVEL.ERROR,
                )
            return None

    def detect_phone(self, image: np.ndarray) -> Optional[Dict]:
        """Call the detection service to locate phones; returns bbox and confidence when available."""
        if image is None or image.size == 0:
            return None
        try:
            encoded_ok, buffer = cv2.imencode(".jpg", image)
            if not encoded_ok:
                return None
            payload = {"image": base64.b64encode(buffer.tobytes()).decode("utf-8")}
            response = self._session.post(
                f"{self.base_url}/detect_phone",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
            bbox = body.get("phone_bbox")
            conf = body.get("phone_confidence")
            if not bbox:
                return None
            try:
                bbox_list = [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])]
            except Exception:
                return None
            return {"phone_bbox": bbox_list, "phone_confidence": conf}
        except requests.RequestException as exc:
            if self.logger:
                self.logger.write_logs(
                    f"Detection service error (phone): {exc}",
                    LOG_LEVEL.WARNING,
                )
            return None
        except Exception as exc:  # pylint: disable=broad-except
            if self.logger:
                self.logger.write_logs(
                    f"Detection service failure (phone): {exc}",
                    LOG_LEVEL.ERROR,
                )
            return None
