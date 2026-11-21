"""Export an approved Lovart PNG as a verified RGB JPEG (requires Pillow)."""
import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image

MAX_BYTES = 3_000_000


def parse_size(value):
    try:
        width, height = map(int, value.lower().split("x"))
        if min(width, height) > 0:
            return width, height
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("expected positive WIDTHxHEIGHT")


def export(source, target, source_size, delivery_size):
    if source.resolve() == target.resolve() or target.suffix.lower() not in (".jpg", ".jpeg"):
        raise ValueError("a separate JPEG destination is required")
    if source_size[0] * delivery_size[1] != source_size[1] * delivery_size[0]:
        raise ValueError("source and delivery aspect ratios differ")
    with Image.open(source) as original:
        if original.format != "PNG" or original.size != source_size or original.n_frames != 1:
            raise ValueError(f"unexpected input: {original.format} {original.size} frames={original.n_frames}")
        if original.getexif().get(274, 1) != 1:
            raise ValueError("input has an orientation transform; verify orientation before export")
        original.load()
        if "A" in original.getbands() or "transparency" in original.info:
            rgba = original.convert("RGBA")
            rgb = Image.new("RGB", original.size, "white")
            rgb.paste(rgba, mask=rgba.getchannel("A"))
        else:
            rgb = original.convert("RGB")
        profile = original.info.get("icc_profile")
    resized = rgb.resize(delivery_size, Image.Resampling.LANCZOS)
    attempts = []
    with NamedTemporaryFile(dir=target.parent, suffix=".jpg", delete=False) as temporary:
        candidate = Path(temporary.name)
    try:
        for quality in range(90, 74, -1):
            resized.save(candidate, "JPEG", quality=quality, optimize=True, icc_profile=profile)
            size_bytes = candidate.stat().st_size
            attempts.append({"quality": quality, "bytes": size_bytes})
            with Image.open(candidate) as check:
                check.load()
                if (check.format, check.mode, check.size) != ("JPEG", "RGB", delivery_size):
                    raise ValueError(f"invalid JPEG output: {check.format} {check.mode} {check.size}")
            if size_bytes < MAX_BYTES:
                os.replace(candidate, target)
                return {"status": "PASS", "source": str(source), "source_format": "PNG",
                        "source_size": source_size, "source_bytes": source.stat().st_size,
                        "output": str(target), "format": "JPEG", "mode": "RGB", "size": delivery_size,
                        "bytes": size_bytes, "quality": quality, "attempts": attempts}
        raise ValueError(f"JPEG size limit exceeded: {attempts}")
    finally:
        candidate.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--source-size", type=parse_size, default=(1536, 2048))
    parser.add_argument("--delivery-size", type=parse_size, default=(1200, 1600))
    args = parser.parse_args()
    try:
        print(json.dumps(export(args.source, args.target, args.source_size, args.delivery_size)))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}), file=sys.stderr)
        sys.exit(1)
