#!/usr/bin/env python3.10
"""
Locust load test that exercises the gateway WebSocket endpoint.

The client understands two dataset layouts:
  1. Legacy directory structure: Data/test_images/<user>/<label>/<frame>.jpg
  2. Manifest file (preferred): Data/test_images/manifest.json describing each sample.

Environment overrides:
  LOCUST_WS_DATASET_DIR         Base directory for samples (default Data/test_images)
  LOCUST_WS_MANIFEST_PATH       Explicit manifest path (default <dataset>/manifest.json)
  LOCUST_WS_TASKS               Comma separated task filter (face_recognition,object_detection,face_detection)
  LOCUST_WS_LABELS              Comma separated label filter (e.g. genuine,spoof)
  LOCUST_WS_UNKNOWN_USERS       Comma separated synthetic user ids to test unknown enrolments
  LOCUST_WS_INCLUDE_MISMATCHES  "true" to add extra wrong-user payloads on the fly
  LOCUST_WS_WAIT_MIN            Minimum wait-time between requests (seconds, default 1.0)
  LOCUST_WS_WAIT_MAX            Maximum wait-time between requests (seconds, default 3.0)
  LOCUST_WS_HOST                Gateway host (default 127.0.0.1)
  LOCUST_WS_PORT                Gateway port (default 8000)
  LOCUST_WS_PATH                Gateway endpoint (default /ws)
  LOCUST_WS_IMAGE_EXTS          Legacy glob extensions for directory mode (default jpg,jpeg,png)
  LOCUST_WS_RECV_TIMEOUT        Seconds to wait for gateway responses (default 15.0)
  LOCUST_WS_DRAIN_ALL_MESSAGES  "true" to read all pending responses before returning to Locust
"""

from __future__ import annotations

import base64
import json
import os
import random
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from locust import User, between, events, task
from websocket import (
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
    create_connection,
)
from PIL import Image


def _str_to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(value: Optional[str], default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


WAIT_MIN = _parse_float(os.getenv("LOCUST_WS_WAIT_MIN"), 1.0)
WAIT_MAX = _parse_float(os.getenv("LOCUST_WS_WAIT_MAX"), 3.0)
if WAIT_MAX < WAIT_MIN:
    WAIT_MIN, WAIT_MAX = WAIT_MAX, WAIT_MIN

RECV_TIMEOUT = _parse_float(os.getenv("LOCUST_WS_RECV_TIMEOUT"), 15.0)
DRAIN_ALL_MESSAGES = _str_to_bool(os.getenv("LOCUST_WS_DRAIN_ALL_MESSAGES"), False)
LABEL_EXPECTATIONS: Dict[str, Optional[str]] = {
    "genuine": "allow",
    "spoof": "deny",
    "mismatch": "deny",
    "unknown_user": "deny",
    "phone_positive": None,
    "phone_negative": None,
    "no_face": None,
}


@dataclass
class SamplePayload:
    user_name: str
    label: str
    task: str
    tags: Tuple[str, ...]
    image_b64: str
    source: Path
    meta: Dict[str, object]
    expected_outcome: Optional[str] = None

    def as_request_payload(self) -> dict:
        return {"user_name": self.user_name, "image": self.image_b64}

    def context(self) -> Dict[str, object]:
        context = {
            "user_name": self.user_name,
            "label": self.label,
            "task": self.task,
            "tags": list(self.tags),
            "source": str(self.source),
        }
        if self.expected_outcome is not None:
            context["expected_outcome"] = self.expected_outcome
        for key, value in self.meta.items():
            context.setdefault(key, value)
        return context


def _encode_image_to_base64(image_path: Path, size: Tuple[int, int] = (240, 240)) -> str:
    """Load image, convert to RGB, resize, and return base64 encoded JPEG."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        if img.size != size:
            try:
                resample = Image.Resampling.LANCZOS  # Pillow >=9.1
            except AttributeError:
                resample = Image.LANCZOS  # Older Pillow fallback
            img = img.resize(size, resample)
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _discover_candidate_paths(
    dataset_dir: Path, extensions: Iterable[str]
) -> List[Path]:
    candidates: List[Path] = []
    for ext in extensions:
        ext = ext.strip().lower()
        if not ext:
            continue
        candidates.extend(dataset_dir.rglob(f"*.{ext}"))
    return sorted(candidates)


def _derive_user_and_label(samples_dir: Path, image_path: Path) -> Tuple[str, str]:
    rel_parts = image_path.relative_to(samples_dir).parts
    if len(rel_parts) >= 3:
        return rel_parts[0], rel_parts[1]
    if len(rel_parts) == 2:
        return rel_parts[0], "genuine"
    default_user = os.getenv(
        "LOCUST_WS_USERNAME", image_path.stem.split("_")[0] or "sample_user"
    )
    return default_user, "genuine"


def _expected_for_label(label: str) -> Optional[str]:
    return LABEL_EXPECTATIONS.get(label)


def _load_from_manifest(
    manifest_path: Path,
    dataset_dir: Path,
    task_filter: Sequence[str],
    label_filter: Sequence[str],
) -> List[SamplePayload]:
    manifest = json.loads(manifest_path.read_text())
    entries = manifest.get("entries", [])
    task_set = {task.strip().lower() for task in task_filter if task.strip()}
    label_set = {label.strip().lower() for label in label_filter if label.strip()}

    payloads: List[SamplePayload] = []
    for entry in entries:
        entry_label = str(entry.get("label") or "genuine")
        entry_task = str(entry.get("task") or "face_recognition")
        if task_set and entry_task.lower() not in task_set:
            continue
        if label_set and entry_label.lower() not in label_set:
            continue

        rel_path = entry.get("path")
        if not rel_path:
            continue
        image_path = (dataset_dir / rel_path).resolve()
        if not image_path.exists():
            continue

        encoded = _encode_image_to_base64(image_path)
        tags = tuple(str(tag) for tag in (entry.get("tags") or [entry_label]))
        payloads.append(
            SamplePayload(
                user_name=str(entry.get("user_name") or "unknown_user"),
                label=entry_label,
                task=entry_task,
                tags=tags,
                expected_outcome=entry.get(
                    "expected_outcome", _expected_for_label(entry_label)
                ),
                image_b64=encoded,
                source=image_path,
                meta={
                    "manifest_source": entry.get("source"),
                    "manifest_index": entry.get("id"),
                },
            )
        )
    return payloads


def _load_from_directory(
    dataset_dir: Path,
    extensions: Iterable[str],
    label_filter: Sequence[str],
) -> List[SamplePayload]:
    label_set = {label.strip().lower() for label in label_filter if label.strip()}
    payloads: List[SamplePayload] = []
    for image_path in _discover_candidate_paths(dataset_dir, extensions):
        user_name, label = _derive_user_and_label(dataset_dir, image_path)
        if label_set and label.lower() not in label_set:
            continue
        encoded = _encode_image_to_base64(image_path)
        payloads.append(
            SamplePayload(
                user_name=user_name,
                label=label,
                task="face_recognition",
                tags=(label,),
                expected_outcome=_expected_for_label(label),
                image_b64=encoded,
                source=image_path,
                meta={"manifest_source": None},
            )
        )
    return payloads


def _generate_mismatch_variants(
    payloads: Sequence[SamplePayload],
) -> List[SamplePayload]:
    face_samples = [sample for sample in payloads if sample.task == "face_recognition"]
    user_names = sorted({sample.user_name for sample in face_samples})
    if len(user_names) <= 1:
        return []

    variants: List[SamplePayload] = []
    for original in face_samples:
        alternatives = [u for u in user_names if u != original.user_name]
        if not alternatives:
            continue
        wrong_user = random.choice(alternatives)
        variant_meta = dict(original.meta)
        variant_meta["synthetic_variant_of"] = original.user_name
        variants.append(
            SamplePayload(
                user_name=wrong_user,
                label=f"mismatch:{original.user_name}->{wrong_user}",
                task=original.task,
                tags=tuple(sorted(set(original.tags) | {"synthetic_mismatch"})),
                expected_outcome="deny",
                image_b64=original.image_b64,
                source=original.source,
                meta=variant_meta,
            )
        )
    return variants


def _generate_unknown_user_payloads(
    payloads: Sequence[SamplePayload],
    unknown_users: Sequence[str],
) -> List[SamplePayload]:
    if not unknown_users:
        return []
    face_samples = [sample for sample in payloads if sample.task == "face_recognition"]
    if not face_samples:
        return []

    variants: List[SamplePayload] = []
    for user_id in unknown_users:
        sample = random.choice(face_samples)
        variant_meta = dict(sample.meta)
        variant_meta["synthetic_variant_of"] = sample.user_name
        variants.append(
            SamplePayload(
                user_name=user_id,
                label="unknown_user",
                task=sample.task,
                tags=tuple(sorted(set(sample.tags) | {"unknown_user"})),
                expected_outcome="deny",
                image_b64=sample.image_b64,
                source=sample.source,
                meta=variant_meta,
            )
        )
    return variants


def _load_samples() -> List[SamplePayload]:
    default_dataset = Path(__file__).resolve().parents[2] / "Data" / "test_images"
    dataset_dir = (
        Path(os.getenv("LOCUST_WS_DATASET_DIR", default_dataset)).expanduser().resolve()
    )
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Samples directory not found: {dataset_dir}")

    manifest_env = os.getenv("LOCUST_WS_MANIFEST_PATH")
    manifest_path = (
        Path(manifest_env).expanduser().resolve()
        if manifest_env
        else dataset_dir / "manifest.json"
    )
    task_filter = (
        os.getenv("LOCUST_WS_TASKS", "").split(",")
        if os.getenv("LOCUST_WS_TASKS")
        else []
    )
    label_filter = (
        os.getenv("LOCUST_WS_LABELS", "").split(",")
        if os.getenv("LOCUST_WS_LABELS")
        else []
    )

    extensions = os.getenv("LOCUST_WS_IMAGE_EXTS", "jpg,jpeg,png").split(",")
    payloads: List[SamplePayload] = []
    if manifest_path.exists():
        payloads.extend(
            _load_from_manifest(manifest_path, dataset_dir, task_filter, label_filter)
        )
    else:
        payloads.extend(_load_from_directory(dataset_dir, extensions, label_filter))

    # Enrich manifest-driven payloads with any additional samples found on disk so that
    # load tests can exercise every available user directory (e.g. other_user, sample_user).
    seen_sources = {str(sample.source) for sample in payloads}
    for extra_sample in _load_from_directory(dataset_dir, extensions, label_filter):
        if str(extra_sample.source) not in seen_sources:
            payloads.append(extra_sample)
            seen_sources.add(str(extra_sample.source))

    if not payloads:
        raise RuntimeError(f"No sample images available in {dataset_dir}")

    if _str_to_bool(os.getenv("LOCUST_WS_INCLUDE_MISMATCHES"), default=False):
        payloads.extend(_generate_mismatch_variants(payloads))

    unknown_users_raw = os.getenv("LOCUST_WS_UNKNOWN_USERS", "")
    if unknown_users_raw:
        unknown_users = [
            user.strip() for user in unknown_users_raw.split(",") if user.strip()
        ]
        payloads.extend(_generate_unknown_user_payloads(payloads, unknown_users))

    return payloads


class GatewayWebsocketUser(User):
    """Locust user that sends images over the gateway WebSocket endpoint."""

    wait_time = between(WAIT_MIN, WAIT_MAX)

    def on_start(self) -> None:
        self.payloads = _load_samples()
        ws_host = os.getenv("LOCUST_WS_HOST", "127.0.0.1")
        ws_port = os.getenv("LOCUST_WS_PORT", "8000")
        ws_path = os.getenv("LOCUST_WS_PATH", "/ws")
        self.ws_url = f"ws://{ws_host}:{ws_port}{ws_path}"
        self.ws = None
        self._ensure_connection()

    def on_stop(self) -> None:
        self._reset_connection()

    def _ensure_connection(self) -> None:
        if self.ws is not None:
            return
        connect_start = time.perf_counter()
        try:
            self.ws = create_connection(self.ws_url, timeout=10)
            self.ws.settimeout(RECV_TIMEOUT)
        except Exception as exc:
            events.request.fire(
                request_type="WS",
                name="connect",
                response_time=(time.perf_counter() - connect_start) * 1000,
                response_length=0,
                context={"ws_url": self.ws_url},
                exception=exc,
            )
            self._reset_connection()
            raise
        else:
            events.request.fire(
                request_type="WS",
                name="connect",
                response_time=(time.perf_counter() - connect_start) * 1000,
                response_length=0,
                context={"ws_url": self.ws_url},
            )

    def _reset_connection(self) -> None:
        if self.ws is None:
            return
        try:
            self.ws.close()
        except Exception:
            pass
        finally:
            self.ws = None

    def _drain_gateway_messages(self) -> List[str]:
        if self.ws is None:
            return []
        messages: List[str] = []
        deadline = time.perf_counter() + RECV_TIMEOUT
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break
            try:
                self.ws.settimeout(max(0.1, remaining))
                message = self.ws.recv()
            except WebSocketTimeoutException:
                break
            except WebSocketConnectionClosedException:
                self._reset_connection()
                raise
            except Exception:
                self._reset_connection()
                raise
            else:
                messages.append(message)
                if not DRAIN_ALL_MESSAGES:
                    break
        if self.ws is not None:
            self.ws.settimeout(RECV_TIMEOUT)
        return messages

    @task
    def send_image(self) -> None:
        sample = random.choice(self.payloads)
        payload = sample.as_request_payload()
        request_meta = {
            "request_type": "WS",
            "name": f"send_image[{sample.task}]",
            "response_time": 0,
            "response_length": 0,
            "context": sample.context(),
        }
        start_time = time.perf_counter()
        try:
            self._ensure_connection()
            assert self.ws is not None  # for type checkers
            self.ws.send(json.dumps(payload))
            responses = self._drain_gateway_messages()
            request_meta["response_length"] = len(payload["image"])
            request_meta["response_time"] = (time.perf_counter() - start_time) * 1000
            if responses:
                request_meta["context"]["gateway_responses"] = responses
            events.request.fire(**request_meta)
        except Exception as exc:  # Locust records the failure
            self._reset_connection()
            request_meta["response_time"] = (time.perf_counter() - start_time) * 1000
            request_meta["exception"] = exc
            events.request.fire(**request_meta)
