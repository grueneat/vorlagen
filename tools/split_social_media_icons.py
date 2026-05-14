#!/usr/bin/env python3
"""Split the brand-source social-media icon composite into per-icon PNGs.

The brand team ships ``shared/logos/social-media-icons-weiss.png`` as a
single 4-up composite (X, Instagram, TikTok, Facebook left-to-right,
white-on-transparent). Templates that need an individual icon (the
26-03 Leporello does, three frames per side) used to alpha-bbox-crop
from per-template copies, which kept picking up slivers from the next
icon and non-square aspects (#issue/106 superseded). This script does
the split ONCE at the source level: each icon becomes its own
canonical square PNG in ``shared/logos/`` alongside the already-split
bluesky-weiss.png / mail-weiss.png / website-weiss.png.

Algorithm:

  1. Walk alpha-column runs in the composite. The composite has clean
     transparent gutters between icons, so the 4 runs map 1:1 to icons.
  2. For each run, find the tight (top, bottom) rows that contain
     opaque pixels.
  3. Crop to a SQUARE bbox centred on the icon (max of width/height,
     padded with transparent pixels) so all four outputs auto-fit
     identically in a square frame.
  4. Resize-down to 865×865 to match the other ``shared/logos/`` icons
     (bluesky/mail/website are already at that size).

Usage::

    python3 tools/split_social_media_icons.py

Idempotent — running again produces the same bytes unless the source
composite changes.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "shared" / "logos" / "social-media-icons-weiss.png"
OUTPUT_DIR = ROOT / "shared" / "logos"

# Left-to-right order in the composite, as a one-shot manual decision —
# the brand team's composite is fixed and the order doesn't change.
ICON_ORDER = ["x", "instagram", "tiktok", "facebook"]

TARGET_SIZE = 865  # matches bluesky-weiss / mail-weiss / website-weiss


def _alpha_column_runs(im: Image.Image) -> list[tuple[int, int]]:
    """Return inclusive (start_x, end_x) runs of columns that contain
    any opaque pixel. Subsamples rows for speed (icon edges are
    always tall enough that the subsample catches them)."""
    alpha = im.split()[-1]
    px = alpha.load()
    w, h = im.size
    runs: list[tuple[int, int]] = []
    in_run = False
    start = 0
    for x in range(w):
        has = False
        for y in range(0, h, 8):
            if px[x, y] > 0:
                has = True
                break
        if has and not in_run:
            start = x
            in_run = True
        elif not has and in_run:
            runs.append((start, x - 1))
            in_run = False
    if in_run:
        runs.append((start, w - 1))
    return runs


def _tight_rows(im: Image.Image, x0: int, x1: int) -> tuple[int, int]:
    """For columns x0..x1, return the inclusive (top, bottom) rows
    containing any opaque pixel."""
    alpha = im.split()[-1]
    px = alpha.load()
    _, h = im.size
    top = 0
    bottom = h - 1
    while top < h:
        if any(px[x, top] > 0 for x in range(x0, x1 + 1)):
            break
        top += 1
    while bottom > top:
        if any(px[x, bottom] > 0 for x in range(x0, x1 + 1)):
            break
        bottom -= 1
    return top, bottom


def _pad_to_square(im: Image.Image, target: int) -> Image.Image:
    """Centre ``im`` on a transparent square ``target×target`` canvas
    after resizing to fit. Output is always ``target×target``."""
    w, h = im.size
    scale = target / max(w, h)
    new_w = round(w * scale)
    new_h = round(h * scale)
    resized = im.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (target, target), (0, 0, 0, 0))
    canvas.paste(resized, ((target - new_w) // 2, (target - new_h) // 2))
    return canvas


def split_composite() -> list[Path]:
    if not SOURCE.exists():
        raise FileNotFoundError(f"brand source missing: {SOURCE}")
    composite = Image.open(SOURCE).convert("RGBA")
    runs = _alpha_column_runs(composite)
    if len(runs) != len(ICON_ORDER):
        raise RuntimeError(
            f"Expected {len(ICON_ORDER)} alpha-column runs in "
            f"{SOURCE.name}, got {len(runs)}: {runs}"
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for name, (x0, x1) in zip(ICON_ORDER, runs):
        top, bottom = _tight_rows(composite, x0, x1)
        cropped = composite.crop((x0, top, x1 + 1, bottom + 1))
        squared = _pad_to_square(cropped, TARGET_SIZE)
        out_path = OUTPUT_DIR / f"social-media-icon-{name}-weiss.png"
        squared.save(out_path, format="PNG", optimize=True)
        outputs.append(out_path)
        print(
            f"  {name}: source x={x0}..{x1} y={top}..{bottom} "
            f"({x1 - x0 + 1}×{bottom - top + 1}) "
            f"→ {out_path.relative_to(ROOT)} ({TARGET_SIZE}×{TARGET_SIZE})"
        )
    return outputs


def main() -> int:
    print(f"Splitting {SOURCE.relative_to(ROOT)}:")
    outputs = split_composite()
    print(f"OK — emitted {len(outputs)} per-icon PNG(s) in {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
