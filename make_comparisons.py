#!/usr/bin/env python3
"""Generate side-by-side baseline-vs-preview page comparisons for visual review.

For each template with both baseline.pdf and preview.pdf, rasterises every page
and writes a combined image (InDesign baseline next to the Scribus preview) into
review-comparisons/<slug>/page-NN.png. Landscape pages are stacked vertically.
Re-runnable: clears and rebuilds review-comparisons/ each time.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORKTREE = Path(__file__).resolve().parent
TEMPLATES = WORKTREE / "templates"
OUT = WORKTREE / "review-comparisons"
DPI = "200"

_TOOLS = WORKTREE / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from pdf_color import (  # noqa: E402
    pick_reference_cmyk_profile,
    rasterise_color_managed,
)

# Only the templates produced by this overnight batch (not pre-existing ones).
BATCH_SLUGS = [
    "flyer-a6-hochformat-portraet",
    "flyer-a6-hochformat-quadrat-im-bild",
    "flyer-a6-hochformat-gruenes-cover",
    "flyer-a6-hochformat-zweigeteilt",  # blocked — no preview, auto-skipped
    "flyer-a6-querformat-portraet",
    "flyer-a6-querformat-quadrat-im-bild",
    "flyer-a6-querformat-gruenes-cover",
    "flyer-a6-querformat-zweigeteilt",
    "falzflyer-z-falz-6-seitig-gruenes-cover",
]


def pagenum(p: Path) -> int:
    m = re.search(r"-(\d+)\.png$", p.name)
    return int(m.group(1)) if m else 0


def rasterise(pdf: Path, prefix: Path, cmyk_profile: str | None = None) -> list[Path]:
    """Rasterise a PDF to per-page PNGs through a colour-managed path.

    ``cmyk_profile`` is the shared CMYK ICC profile — the baseline and the
    preview of one comparison MUST be rasterised with the SAME profile so
    the side-by-side render is colour-consistent (InDesign's baseline is
    output-intent-converted CMYK; Scribus's preview is raw DeviceCMYK).
    """
    rasterise_color_managed(pdf, prefix, int(DPI), cmyk_profile)
    return sorted(prefix.parent.glob(f"{prefix.name}-*.png"), key=pagenum)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    templates = [
        TEMPLATES / s for s in BATCH_SLUGS
        if (TEMPLATES / s / "baseline.pdf").exists()
        and (TEMPLATES / s / "preview.pdf").exists()
    ]

    index = ["# Page comparisons — baseline (InDesign) vs preview (Scribus)", ""]
    for tdir in templates:
        slug = tdir.name
        dest = OUT / slug
        dest.mkdir()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cmyk_profile, _ = pick_reference_cmyk_profile(
                tdir / "baseline.pdf", tdir / "preview.pdf", tmp / "profiles",
            )
            base = rasterise(tdir / "baseline.pdf", tmp / "base", cmyk_profile)
            prev = rasterise(tdir / "preview.pdf", tmp / "prev", cmyk_profile)
            n = max(len(base), len(prev))
            for i in range(n):
                b = base[i] if i < len(base) else None
                p = prev[i] if i < len(prev) else None
                ref = b or p
                w, h = subprocess.run(
                    ["identify", "-format", "%w %h", str(ref)],
                    capture_output=True, text=True, check=True,
                ).stdout.split()
                tile = "1x2" if int(w) > int(h) else "2x1"
                args = ["montage"]
                args += (["-label", "BASELINE (InDesign)", str(b)] if b
                         else ["-label", "BASELINE (missing)", "xc:lightgray"])
                args += (["-label", "PREVIEW (Scribus)", str(p)] if p
                         else ["-label", "PREVIEW (missing)", "xc:lightgray"])
                args += ["-tile", tile, "-geometry", "+14+14", "-pointsize", "30",
                         "-background", "white", str(dest / f"page-{i + 1:02d}.png")]
                subprocess.run(args, check=True)
            index.append(f"- **{slug}** — {n} page(s)")
            print(f"{slug}: {n} page comparison(s)")

    index += [
        "",
        "Template `flyer-a6-hochformat-zweigeteilt` is omitted — it is "
        "blocked on a missing source image, so no preview was rendered.",
    ]
    (OUT / "README.md").write_text("\n".join(index) + "\n")
    print(f"\nDone. Output: {OUT}")


if __name__ == "__main__":
    main()
