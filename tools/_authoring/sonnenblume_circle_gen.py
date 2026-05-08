#!/usr/bin/env python3
"""Re-generate shared/logos/sonnenblume-circle.png (Issue #11, one-shot).

Geometric placeholder: 8 elliptical petals around a center hub, all in
Dunkelgrün sRGB (28, 72, 33), on a fully-transparent inscribed-circle
canvas. 200×200 RGBA PNG. Deterministic across runs (Pillow ≥12.2).

D11 from CONTEXT.md defers brand-quality logos to a separate issue.
This is functional, not pretty; it's the minimum needed to satisfy
``embed_logo`` for ``tools/qr_gen.py`` while keeping QRs scannable at
ECC=H.

Run from the repo root::

    python3 tools/_authoring/sonnenblume_circle_gen.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
DST = ROOT / "shared" / "logos" / "sonnenblume-circle.png"

SIDE = 200
DUNKELGRUEN = (28, 72, 33, 255)
TRANSPARENT = (0, 0, 0, 0)
N_PETALS = 8


def build() -> Image.Image:
    img = Image.new("RGBA", (SIDE, SIDE), TRANSPARENT)
    draw = ImageDraw.Draw(img)

    cx, cy = SIDE / 2, SIDE / 2
    petal_w = SIDE * 0.18
    petal_h = SIDE * 0.42
    hub_radius = SIDE * 0.18

    for i in range(N_PETALS):
        angle_deg = i * (360 / N_PETALS)
        angle_rad = math.radians(angle_deg)

        layer = Image.new(
            "RGBA",
            (int(petal_w * 1.2), int(petal_h * 1.2)),
            TRANSPARENT,
        )
        layer_draw = ImageDraw.Draw(layer)
        lw, lh = layer.size
        layer_draw.ellipse(
            ((lw - petal_w) / 2, 0, (lw + petal_w) / 2, petal_h),
            fill=DUNKELGRUEN,
        )
        rotated = layer.rotate(
            -angle_deg,
            resample=Image.Resampling.BICUBIC,
            expand=True,
        )

        overlap = SIDE * 0.04
        offset = hub_radius + petal_h / 2 - overlap
        rw, rh = rotated.size
        px = cx + math.cos(angle_rad - math.pi / 2) * offset - rw / 2
        py = cy + math.sin(angle_rad - math.pi / 2) * offset - rh / 2
        img.paste(rotated, (int(px), int(py)), rotated)

    draw.ellipse(
        (cx - hub_radius, cy - hub_radius, cx + hub_radius, cy + hub_radius),
        fill=DUNKELGRUEN,
    )

    mask = Image.new("L", (SIDE, SIDE), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, SIDE - 1, SIDE - 1), fill=255)

    out = Image.new("RGBA", (SIDE, SIDE), TRANSPARENT)
    out.paste(img, (0, 0), mask)
    return out


def main() -> int:
    img = build()
    DST.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(DST), format="PNG", optimize=True)
    print(f"wrote {DST} ({DST.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
