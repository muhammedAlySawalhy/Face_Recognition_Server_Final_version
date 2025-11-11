#!/usr/bin/env python3.10
"""
Locust load test that exercises the gateway WebSocket endpoint.

The client understands two dataset layouts:
  1. Legacy directory structure: Data/test_images/<user>/<label>/<frame>.jpg
  2. Manifest file (preferred): Data/test_images/manifest.json describing each sample.

Environment overrides:
  LOCUST_WS_DATASET_DIR         Base directory for samples (default Data/test_images; falls back to Data/Users_DataBase)
  LOCUST_WS_MANIFEST_PATH       Explicit manifest path (default <dataset>/manifest.json)
  LOCUST_WS_TASKS               Comma separated task filter (face_recognition,object_detection,face_detection)
  LOCUST_WS_LABELS              Comma separated label filter (e.g. genuine,spoof)
  LOCUST_WS_UNKNOWN_USERS       Comma separated synthetic user ids to test unknown enrolments
  LOCUST_WS_INCLUDE_MISMATCHES  "true" to add extra wrong-user payloads on the fly
  LOCUST_WS_WAIT_MIN            Minimum wait-time between requests (seconds, default 1.0)
  LOCUST_WS_WAIT_MAX            Maximum wait-time between requests (seconds, default 3.0)
  LOCUST_WS_HOST                Gateway host (default 127.0.0.1)
  LOCUST_WS_PORT                Gateway port (default 8001)
  LOCUST_WS_PATH                Gateway endpoint (default /ws)
  LOCUST_WS_IMAGE_EXTS          Legacy glob extensions for directory mode (default jpg,jpeg,png)
  LOCUST_WS_RECV_TIMEOUT        Seconds to wait for gateway responses (default 15.0)
  LOCUST_WS_DRAIN_ALL_MESSAGES  "true" to read all pending responses before returning to Locust
  LOCUST_WS_DISABLE_CACHE       "true" to rebuild encoded samples for every Locust user (default false)
  LOCUST_WS_CACHE_BUSTER        Optional string; change value to force reload of cached samples
"""

from __future__ import annotations

import base64
import itertools
import json
import os
import random
import time
from datetime import datetime
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from locust import User, between, events, task
from websocket import (
    WebSocket,
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
    create_connection,
)
from PIL import Image, ImageDraw


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

DISABLE_SAMPLE_CACHE = _str_to_bool(os.getenv("LOCUST_WS_DISABLE_CACHE"), False)
CACHE_BUSTER = os.getenv("LOCUST_WS_CACHE_BUSTER") or None
DEFAULT_DATASET_SUBDIRS: Tuple[str, ...] = ("test_images", "Users_DataBase")
SYNTHETIC_SAMPLE_DEFINITIONS: Tuple[Dict[str, object], ...] = (
    {
        "user_name": "client_genuine",
        "label": "genuine",
        "task": "face_recognition",
        "expected_outcome": "allow",
        "text": "Client 001\nGenuine",
        "background": (16, 84, 53),
        "accent": (220, 255, 220),
        "overlay": "face",
    },
    {
        "user_name": "client_spoof",
        "label": "spoof",
        "task": "face_recognition",
        "expected_outcome": "deny",
        "text": "Spoof",
        "background": (120, 0, 0),
        "accent": (255, 222, 89),
        "overlay": "spoof",
    },
    {
        "user_name": "client_mismatch",
        "label": "genuine",
        "task": "face_recognition",
        "expected_outcome": "allow",
        "text": "Client 002",
        "background": (0, 51, 102),
        "accent": (200, 229, 255),
        "overlay": "face",
    },
    {
        "user_name": "client_phone",
        "label": "phone_positive",
        "task": "object_detection",
        "expected_outcome": "deny",
        "text": "Phone",
        "background": (20, 20, 20),
        "accent": (0, 200, 255),
        "overlay": "phone",
    },
    {
        "user_name": "client_phone",
        "label": "phone_negative",
        "task": "object_detection",
        "expected_outcome": None,
        "text": "No Phone",
        "background": (45, 45, 45),
        "accent": (150, 150, 150),
        "overlay": None,
    },
    {
        "user_name": "client_no_face",
        "label": "no_face",
        "task": "face_detection",
        "expected_outcome": "deny",
        "text": "No Face",
        "background": (64, 32, 96),
        "accent": (241, 169, 255),
        "overlay": None,
    },
)


def _dataset_has_images(dataset_dir: Path) -> bool:
    if not dataset_dir.exists():
        return False
    for _ in dataset_dir.rglob("*.jpg"):
        return True
    for _ in dataset_dir.rglob("*.jpeg"):
        return True
    for _ in dataset_dir.rglob("*.png"):
        return True
    return False


def _render_synthetic_image(image_path: Path, sample: Dict[str, object]) -> None:
    background = sample.get("background", (32, 32, 32))
    accent = sample.get("accent", (255, 255, 255))
    image = Image.new("RGB", (240, 240), background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 230, 230), outline=accent, width=3)
    overlay = sample.get("overlay")
    if overlay == "face":
        draw.ellipse((70, 50, 170, 190), outline=accent, width=3)
        draw.ellipse((95, 90, 115, 110), fill=accent)
        draw.ellipse((125, 90, 145, 110), fill=accent)
        draw.arc((100, 130, 140, 170), 10, 170, fill=accent, width=3)
    elif overlay == "spoof":
        for offset in range(-240, 240, 25):
            draw.line((offset, 0, offset + 240, 240), fill=accent, width=4)
    elif overlay == "phone":
        draw.rectangle((90, 40, 150, 200), outline=accent, width=4)
        draw.rectangle((96, 46, 144, 194), fill=(0, 0, 0))
        draw.ellipse((117, 185, 123, 191), fill=accent)

    text = sample.get("text")
    if text:
        draw.text((14, 12), str(text), fill=accent)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(image_path, format="JPEG", quality=95)


def _generate_synthetic_dataset(dataset_dir: Path) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    entries: List[Dict[str, object]] = []
    for idx, sample in enumerate(SYNTHETIC_SAMPLE_DEFINITIONS):
        user = str(sample["user_name"])
        label = str(sample["label"])
        filename = f"{label}_{idx:02d}.jpg"
        relative_path = Path(user) / label / filename
        image_path = dataset_dir / relative_path
        if not image_path.exists():
            _render_synthetic_image(image_path, sample)
        entries.append(
            {
                "id": idx,
                "user_name": user,
                "label": label,
                "task": sample.get("task", "face_recognition"),
                "path": str(relative_path),
                "tags": list(sample.get("tags") or [label]),
                "expected_outcome": sample.get("expected_outcome"),
                "source": "synthetic",
            }
        )
    manifest_path = dataset_dir / "manifest.json"
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "entries": entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))


def _ensure_sample_dataset(dataset_dir: Path) -> None:
    dataset_override = os.getenv("LOCUST_WS_DATASET_DIR")
    if dataset_override:
        return
    if _dataset_has_images(dataset_dir):
        return
    _generate_synthetic_dataset(dataset_dir)


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


@dataclass(frozen=True)
class SampleLoaderConfig:
    dataset_dir: Path
    manifest_path: Optional[Path]
    manifest_mtime_ns: Optional[int]
    task_filter: Tuple[str, ...]
    label_filter: Tuple[str, ...]
    extensions: Tuple[str, ...]
    cache_buster: Optional[str]


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


def _parse_csv_env(var_name: str) -> Tuple[str, ...]:
    raw_value = os.getenv(var_name)
    if not raw_value:
        return tuple()
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())


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


def _resolve_dataset_dir() -> Path:
    dataset_override = os.getenv("LOCUST_WS_DATASET_DIR")
    if dataset_override:
        dataset_dir = Path(dataset_override).expanduser().resolve()
        if not dataset_dir.exists():
            raise FileNotFoundError(
                f"Samples directory override not found: {dataset_dir}"
            )
        return dataset_dir

    base_data_dir = Path(__file__).resolve().parents[2] / "Data"
    base_data_dir.mkdir(parents=True, exist_ok=True)
    for subdir in DEFAULT_DATASET_SUBDIRS:
        candidate = (base_data_dir / subdir).resolve()
        if candidate.exists():
            return candidate
    fallback = (base_data_dir / DEFAULT_DATASET_SUBDIRS[0]).resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

def _build_sample_loader_config(dataset_dir: Path) -> SampleLoaderConfig:
    manifest_env = os.getenv("LOCUST_WS_MANIFEST_PATH")
    manifest_path = (
        Path(manifest_env).expanduser().resolve()
        if manifest_env
        else (dataset_dir / "manifest.json")
    )
    manifest_exists = manifest_path.exists()
    manifest_mtime_ns = (
        manifest_path.stat().st_mtime_ns if manifest_exists else None
    )
    task_filter = _parse_csv_env("LOCUST_WS_TASKS")
    label_filter = _parse_csv_env("LOCUST_WS_LABELS")
    extensions = tuple(
        ext.strip().lower()
        for ext in os.getenv("LOCUST_WS_IMAGE_EXTS", "jpg,jpeg,png").split(",")
        if ext.strip()
    )
    if not extensions:
        extensions = ("jpg", "jpeg", "png")
    return SampleLoaderConfig(
        dataset_dir=dataset_dir,
        manifest_path=manifest_path if manifest_exists else None,
        manifest_mtime_ns=manifest_mtime_ns,
        task_filter=task_filter,
        label_filter=label_filter,
        extensions=extensions,
        cache_buster=CACHE_BUSTER,
    )


def _load_base_payloads_direct(config: SampleLoaderConfig) -> List[SamplePayload]:
    if config.manifest_path is None:
        payloads = _load_from_directory(
            config.dataset_dir, config.extensions, config.label_filter
        )
        if not payloads:
            raise RuntimeError(f"No sample images available in {config.dataset_dir}")
        return payloads

    payloads = _load_from_manifest(
        config.manifest_path,
        config.dataset_dir,
        config.task_filter,
        config.label_filter,
    )
    seen_sources = {str(sample.source) for sample in payloads}
    label_set = {label.strip().lower() for label in config.label_filter if label.strip()}
    for image_path in _discover_candidate_paths(
        config.dataset_dir, config.extensions
    ):
        image_path = image_path.resolve()
        path_str = str(image_path)
        if path_str in seen_sources:
            continue
        user_name, label = _derive_user_and_label(config.dataset_dir, image_path)
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
        seen_sources.add(path_str)

    if not payloads:
        raise RuntimeError(f"No sample images available in {config.dataset_dir}")
    return payloads


@lru_cache(maxsize=4)
def _load_base_payloads_cached(config: SampleLoaderConfig) -> Tuple[SamplePayload, ...]:
    return tuple(_load_base_payloads_direct(config))


def _load_samples() -> List[SamplePayload]:
    dataset_dir = _resolve_dataset_dir()
    _ensure_sample_dataset(dataset_dir)
    config = _build_sample_loader_config(dataset_dir)
    if DISABLE_SAMPLE_CACHE:
        payloads = _load_base_payloads_direct(config)
    else:
        payloads = list(_load_base_payloads_cached(config))

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
        self.ws_connections: Dict[str, WebSocket] = {}
        if not self.payloads:
            raise RuntimeError("No payloads were discovered for Locust to send.")
        shuffled = random.sample(self.payloads, len(self.payloads))
        self._payload_cycle = itertools.cycle(shuffled)

    def on_stop(self) -> None:
        for client_name in list(self.ws_connections.keys()):
            self._reset_connection(client_name)

    def _ensure_connection(self, client_name: str) -> None:
        if client_name in self.ws_connections:
            return
        connect_start = time.perf_counter()
        try:
            ws = create_connection(self.ws_url, timeout=10)
            ws.settimeout(RECV_TIMEOUT)
        except Exception as exc:
            events.request.fire(
                request_type="WS",
                name="connect",
                response_time=(time.perf_counter() - connect_start) * 1000,
                response_length=0,
                context={"ws_url": self.ws_url, "client_name": client_name},
                exception=exc,
            )
            raise
        else:
            self.ws_connections[client_name] = ws
            events.request.fire(
                request_type="WS",
                name="connect",
                response_time=(time.perf_counter() - connect_start) * 1000,
                response_length=0,
                context={"ws_url": self.ws_url, "client_name": client_name},
            )

    def _reset_connection(self, client_name: str) -> None:
        ws = self.ws_connections.pop(client_name, None)
        if ws is None:
            return
        try:
            ws.close()
        except Exception:
            pass

    def _drain_gateway_messages(self, client_name: str, ws) -> List[str]:
        messages: List[str] = []
        deadline = time.perf_counter() + RECV_TIMEOUT
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break
            try:
                ws.settimeout(max(0.1, remaining))
                message = ws.recv()
            except WebSocketTimeoutException:
                break
            except WebSocketConnectionClosedException:
                self._reset_connection(client_name)
                raise
            except Exception:
                self._reset_connection(client_name)
                raise
            else:
                messages.append(message)
                if not DRAIN_ALL_MESSAGES:
                    break
        ws.settimeout(RECV_TIMEOUT)
        return messages

    @task
    def send_image(self) -> None:
        try:
            sample = next(self._payload_cycle)
        except AttributeError:
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
            self._ensure_connection(sample.user_name)
            ws = self.ws_connections[sample.user_name]
            ws.send(json.dumps(payload))
            responses = self._drain_gateway_messages(sample.user_name, ws)
            request_meta["response_length"] = len(payload["image"])
            request_meta["response_time"] = (time.perf_counter() - start_time) * 1000
            if responses:
                request_meta["context"]["gateway_responses"] = responses
            events.request.fire(**request_meta)
        except Exception as exc:  # Locust records the failure
            self._reset_connection(sample.user_name)
            request_meta["response_time"] = (time.perf_counter() - start_time) * 1000
            request_meta["exception"] = exc
            events.request.fire(**request_meta)
