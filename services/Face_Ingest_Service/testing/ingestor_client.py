import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path

import numpy as np
import cv2


def generate_fake_image(width: int, height: int, seed: int | None = None) -> np.ndarray:
    """Create a deterministic random RGB image for testing."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)


def encode_image_bytes(image: np.ndarray) -> str:
    """Encode image to PNG bytes then base64 for transport."""
    success, buf = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError("Failed to encode image")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def save_image(image: np.ndarray, path: Path) -> None:
    """Persist image as a raw .bin file for later reuse."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(image.tobytes())


def post_ingest(base_url: str, b64_image: str, metadata: dict[str, str]) -> tuple[int, str]:
    payload = {"client_image": b64_image, "metadata": metadata}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/ingest_image/",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except urllib.error.URLError as e:
        return 0, f"connection error: {e.reason}"


def get_execute(base_url: str, destination: str) -> tuple[int, str]:
    req = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/execute_pipeline/?destination={urllib.parse.quote(destination)}",
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except urllib.error.URLError as e:
        return 0, f"connection error: {e.reason}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple client for Face Image Ingestor.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Ingestor service base URL")
    parser.add_argument("--mode", choices=["fake", "real"], default="fake", help="Use generated fake images or real files")
    parser.add_argument("--image-dir", type=Path, default=Path("testing/images"), help="Directory of real images (for --mode real)")
    parser.add_argument("--count", type=int, default=3, help="Number of fake images to send (for --mode fake)")
    parser.add_argument("--width", type=int, default=64, help="Fake image width (for --mode fake)")
    parser.add_argument("--height", type=int, default=64, help="Fake image height (for --mode fake)")
    parser.add_argument("--seed", type=int, default=42, help="Seed for deterministic images (for --mode fake)")
    parser.add_argument("--save-dir", type=Path, default=Path("testing/fake_images"), help="Where to save raw fake images")
    parser.add_argument("--destination", default="./Output", help="Destination directory for pipeline output")
    args = parser.parse_args()

    if args.mode == "fake":
        for idx in range(args.count):
            img = generate_fake_image(args.width, args.height, seed=args.seed + idx if args.seed is not None else None)
            save_image(img, args.save_dir / f"fake_{idx}.bin")
            b64_img = encode_image_bytes(img)
            status, body = post_ingest(args.base_url, b64_img, metadata={"id": f"fake-{idx}"})
            print(f"[ingest #{idx}] status={status} body={body}")
    else:
        images = sorted(
            [p for p in args.image_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
        )
        if not images:
            print(f"No images found in {args.image_dir} (expected .jpg/.jpeg/.png)")
            return 1
        for idx, img_path in enumerate(images):
            b64_img = base64.b64encode(img_path.read_bytes()).decode("ascii")
            status, body = post_ingest(args.base_url, b64_img, metadata={"client_name": img_path.stem})
            print(f"[ingest real #{idx} {img_path.name}] status={status} body={body}")

    status, body = get_execute(args.base_url, args.destination)
    print(f"[execute_pipeline] status={status} body={body}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
