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
        # Local YOLO-based detector avoids HTTP dependency on the face-ingestor service.
        self.base_url = None
        self.timeout = float(os.getenv("FACE_DETECTION_SERVICE_TIMEOUT", timeout))
        self.logger = logger
        self._session = None

    def detect_face(self, image: np.ndarray) -> Optional[Dict]:
        # Local detection is handled in FaceDetectionRecognition; this client no longer calls an HTTP service.
        return None

    def detect_phone(self, image: np.ndarray) -> Optional[Dict]:
        # Phone detection is handled locally by ObjectDetection; no HTTP call.
        return None
