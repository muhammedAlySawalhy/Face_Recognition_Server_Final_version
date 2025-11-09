#!/usr/bin/env python3.10
"""
Seed the workspace with synthetic-yet-structured samples for end-to-end testing.

The script prepares reference enrolment images plus stress-test frames covering
the three main tasks handled by the security pipeline:
  * Face recognition (genuine, spoof, mismatch)
  * Face detection edge cases (no-face/occlusion)
  * Object detection (phone present / phone absent)

The resulting dataset is written under `Data/` and accompanied by a manifest that
describes each sample. The manifest is consumed by the Locust load tests to
exercise a balanced mix of scenarios.

Run:
    python3 scripts/seed_face_dataset.py

The command is idempotent; files are recreated on every run to keep the content
fresh and deterministic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import itertools
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import requests
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
USERS_DB_DIR = ROOT / "Data" / "Users_DataBase"
SAMPLES_DIR = ROOT / "Data" / "test_images"
MANIFEST_PATH = SAMPLES_DIR / "manifest.json"
PLACEHOLDER_PREFIX = "placeholder://"


def _download_file(url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    target_path.write_bytes(response.content)


def _hash_token(value: str) -> str:
    return hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]


def _seed_rng(seed_token: str) -> random.Random:
    return random.Random(_hash_token(seed_token))


def _draw_phone_positive(target_path: Path, seed_token: str) -> None:
    rng = _seed_rng(seed_token)
    img = Image.new("RGB", (512, 512), color=(235, 236, 240))
    draw = ImageDraw.Draw(img)

    # Background gradient stripes
    for idx in range(0, 512, 32):
        tone = 210 + (idx // 32) % 2 * 10
        draw.rectangle([0, idx, 512, idx + 31], fill=(tone, tone, tone + 3))

    # Stylised silhouette
    head_color = (207, 179, 150)
    draw.ellipse([176, 40, 336, 200], fill=head_color)
    draw.rectangle([192, 190, 320, 380], fill=(80, 120, 170))
    draw.rounded_rectangle([192, 380, 320, 500], radius=60, fill=(65, 95, 135))

    # Smartphone in hand
    phone_body = (30, 30, 35)
    screen_color = (rng.randint(60, 130), rng.randint(60, 130), rng.randint(60, 130))
    draw.rounded_rectangle([330, 250, 420, 450], radius=35, fill=phone_body)
    draw.rectangle([344, 270, 406, 412], fill=screen_color)
    draw.ellipse([365, 430, 381, 446], fill=(210, 210, 215))

    img.save(target_path, format="JPEG", quality=95)


def _draw_phone_negative(target_path: Path, seed_token: str) -> None:
    rng = _seed_rng(seed_token)
    img = Image.new("RGB", (512, 512), color=(222, 230, 235))
    draw = ImageDraw.Draw(img)

    draw.ellipse([156, 70, 356, 270], fill=(200, 180, 150))
    draw.rectangle([170, 260, 340, 430], fill=(92, 132, 188))
    draw.rounded_rectangle([150, 430, 360, 510], radius=50, fill=(72, 110, 162))

    # Empty hand raised without a phone
    hand_color = (215, 189, 160)
    draw.rounded_rectangle([340, 250, 400, 420], radius=45, fill=hand_color)
    for offset in range(0, 70, 14):
        draw.ellipse([340 + offset, 220, 358 + offset, 250], fill=hand_color)

    # Decorative badge to mirror the positive sample layout
    hue = rng.randint(120, 180)
    draw.ellipse([60, 360, 160, 460], fill=(hue, 180, 200))

    img.save(target_path, format="JPEG", quality=95)


def _draw_no_face(target_path: Path, seed_token: str) -> None:
    rng = _seed_rng(seed_token)
    img = Image.new("RGB", (512, 512), color=(240, 240, 245))
    draw = ImageDraw.Draw(img)

    for _ in range(12):
        color = (rng.randint(120, 200), rng.randint(120, 200), rng.randint(120, 200))
        x1, y1 = rng.randint(10, 420), rng.randint(10, 420)
        x2, y2 = x1 + rng.randint(40, 80), y1 + rng.randint(40, 80)
        draw.rectangle([x1, y1, x2, y2], fill=color, outline=(90, 90, 90))
        draw.line([x1, y1, x2, y2], fill=(255, 255, 255), width=2)

    img.save(target_path, format="JPEG", quality=95)


PLACEHOLDER_GENERATORS = {
    "phone_positive": _draw_phone_positive,
    "phone_negative": _draw_phone_negative,
    "no_face": _draw_no_face,
}


@dataclass
class SampleGroup:
    user_name: str
    reference: str
    genuine: List[str] = field(default_factory=list)
    spoof: List[str] = field(default_factory=list)
    mismatch: List[str] = field(default_factory=list)
    extra_labels: Dict[str, List[str]] = field(default_factory=dict)

    def reference_path(self) -> Path:
        return USERS_DB_DIR / self.user_name / f"{self.user_name}_1.jpg"

    def iter_labels(self) -> Iterable[Tuple[str, List[str]]]:
        if self.genuine:
            yield "genuine", self.genuine
        if self.spoof:
            yield "spoof", self.spoof
        if self.mismatch:
            yield "mismatch", self.mismatch
        for label, urls in self.extra_labels.items():
            if urls:
                yield label, urls

    def target_paths(self, label: str, urls: Iterable[str]) -> List[Path]:
        base_dir = SAMPLES_DIR / self.user_name / label
        paths: List[Path] = []
        for idx, url in enumerate(urls, start=1):
            token = _hash_token(f"{self.user_name}-{label}-{idx}-{url}")
            filename = f"{self.user_name}_{label}_{idx:02}_{token}.jpg"
            paths.append(base_dir / filename)
        return paths


LABEL_METADATA = {
    "genuine": ("face_recognition", ["face", "match"], "allow"),
    "spoof": ("face_recognition", ["face", "spoof"], "deny"),
    "mismatch": ("face_recognition", ["face", "mismatch"], "deny"),
    "phone_positive": ("object_detection", ["phone", "positive"], None),
    "phone_negative": ("object_detection", ["phone", "negative"], None),
    "no_face": ("face_detection", ["no_face", "background"], None),
}


DATASET: List[SampleGroup] = [
    SampleGroup(
        user_name="obama",
        reference="https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/knn_examples/train/obama/obama.jpg",
        genuine=[
            "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/knn_examples/train/obama/obama2.jpg",
        ],
        spoof=[
            "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/knn_examples/train/obama/obama.jpg",
        ],
        extra_labels={
            "phone_positive": [f"{PLACEHOLDER_PREFIX}phone_positive"],
            "phone_negative": [f"{PLACEHOLDER_PREFIX}phone_negative"],
            "no_face": [f"{PLACEHOLDER_PREFIX}no_face"],
        },
    ),
    SampleGroup(
        user_name="biden",
        reference="https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/knn_examples/train/biden/biden.jpg",
        genuine=[
            "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/knn_examples/train/biden/biden2.jpg",
        ],
        spoof=[
            "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/knn_examples/train/biden/biden.jpg",
        ],
        extra_labels={
            "phone_positive": [f"{PLACEHOLDER_PREFIX}phone_positive"],
            "phone_negative": [f"{PLACEHOLDER_PREFIX}phone_negative"],
            "no_face": [f"{PLACEHOLDER_PREFIX}no_face"],
        },
    ),
    SampleGroup(
        user_name="rose_leslie",
        reference="https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/knn_examples/train/rose_leslie/img1.jpg",
        genuine=[
            "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/knn_examples/train/rose_leslie/img2.jpg",
        ],
        spoof=[
            "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/knn_examples/train/rose_leslie/img1.jpg",
        ],
        extra_labels={
            "phone_positive": [f"{PLACEHOLDER_PREFIX}phone_positive"],
            "phone_negative": [f"{PLACEHOLDER_PREFIX}phone_negative"],
            "no_face": [f"{PLACEHOLDER_PREFIX}no_face"],
        },
    ),
]


def build_dataset(
    base_groups: Sequence[SampleGroup],
    *,
    synthetic_clients: int = 0,
    target_clients: Optional[int] = None,
    prefix: str = "synthetic",
) -> List[SampleGroup]:
    groups = [SampleGroup(
        user_name=group.user_name,
        reference=group.reference,
        genuine=list(group.genuine),
        spoof=list(group.spoof),
        mismatch=list(group.mismatch),
        extra_labels={label: list(urls) for label, urls in group.extra_labels.items()},
    ) for group in base_groups]

    if target_clients is not None:
        synthetic_clients = max(synthetic_clients, max(0, target_clients - len(groups)))

    if synthetic_clients <= 0:
        return groups

    template_cycle = itertools.cycle(base_groups)
    for idx in range(1, synthetic_clients + 1):
        template = next(template_cycle)
        user_name = f"{prefix}_{idx:03d}"
        groups.append(
            SampleGroup(
                user_name=user_name,
                reference=template.reference,
                genuine=list(template.genuine),
                spoof=list(template.spoof),
                mismatch=[],  # populated later
                extra_labels={
                    label: list(urls) for label, urls in template.extra_labels.items()
                },
            )
        )
    return groups


def populate_mismatch_sets(groups: List[SampleGroup]) -> None:
    for group in groups:
        others = [g for g in groups if g.user_name != group.user_name]
        group.mismatch = [other.reference for other in others[:2]]


def _materialize_sample(
    url: str, target_path: Path, seed_token: str
) -> Tuple[str, str]:
    if url.startswith(PLACEHOLDER_PREFIX):
        kind = url[len(PLACEHOLDER_PREFIX) :]
        generator = PLACEHOLDER_GENERATORS.get(kind)
        if generator is None:
            raise ValueError(f"Unknown placeholder kind '{kind}' for {target_path}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        generator(target_path, seed_token)
        return "placeholder", kind

    try:
        _download_file(url, target_path)
        return "download", url
    except Exception as exc:  # pylint: disable=broad-except
        raise RuntimeError(
            f"Failed to download '{url}' -> {target_path}: {exc}"
        ) from exc


def _label_metadata(label: str) -> Tuple[str, List[str], Optional[str]]:
    task, tags, expected = LABEL_METADATA.get(label, ("unspecified", [label], None))
    return task, list(tags), expected


def seed_dataset(groups: List[SampleGroup]) -> Tuple[List[dict], Counter]:
    populate_mismatch_sets(groups)
    manifest_entries: List[dict] = []
    label_counts: Counter = Counter()

    for group in groups:
        print(f"[+] Seeding user '{group.user_name}'")
        _download_file(group.reference, group.reference_path())

        for label, urls in group.iter_labels():
            targets = group.target_paths(label, urls)
            for url, target_path in zip(urls, targets):
                source_type, origin = _materialize_sample(
                    url, target_path, seed_token=str(target_path)
                )
                task, tags, expected_outcome = _label_metadata(label)
                manifest_entries.append(
                    {
                        "user_name": group.user_name,
                        "label": label,
                        "task": task,
                        "tags": tags,
                        "expected_outcome": expected_outcome,
                        "path": str(target_path.relative_to(SAMPLES_DIR)),
                        "absolute_path": str(target_path),
                        "source": {"type": source_type, "origin": origin},
                    }
                )
                label_counts[label] += 1
    return manifest_entries, label_counts


def _write_manifest(entries: List[dict], counts: Counter) -> None:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_dir": str(SAMPLES_DIR.relative_to(ROOT)),
        "total_samples": len(entries),
        "label_counts": dict(counts),
        "entries": entries,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed or expand the synthetic face-recognition dataset.",
    )
    parser.add_argument(
        "--synthetic-clients",
        type=int,
        default=0,
        help="Number of additional synthetic client identities to generate.",
    )
    parser.add_argument(
        "--target-clients",
        type=int,
        default=None,
        help="Desired total number of client identities (overrides --synthetic-clients when larger).",
    )
    parser.add_argument(
        "--synthetic-prefix",
        type=str,
        default="synthetic",
        help="Prefix used for auto-generated client identifiers (default: 'synthetic').",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    USERS_DB_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    try:
        dataset = build_dataset(
            DATASET,
            synthetic_clients=args.synthetic_clients,
            target_clients=args.target_clients,
            prefix=args.synthetic_prefix,
        )
        entries, counts = seed_dataset(dataset)
        _write_manifest(entries, counts)
    except requests.HTTPError as exc:
        print(f"[!] HTTP error while downloading dataset: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[!] Failed to seed dataset: {exc}", file=sys.stderr)
        return 1

    print("[+] Dataset seeding completed successfully.")
    for label, total in sorted(counts.items()):
        print(f"    - {label}: {total}")
    print(f"[+] Manifest written to {MANIFEST_PATH}")
    print(f"[+] Total unique clients provisioned: {len(dataset)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
