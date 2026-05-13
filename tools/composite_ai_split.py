#!/usr/bin/env python3
"""Split a composite-AI strip into per-icon PDFs (issue #38 Task 14).

A composite-AI is a single .ai file that holds several icons side-by-side
(e.g. social-media-icons-weiss.ai with Facebook + Instagram + X + Mastodon
all on one 526x152pt page). InDesign references it via multiple
ImageFrames whose LocalOffsets crop into different sub-rectangles. When
rasterised as a single PNG, downscaling murders the per-icon quality.

This tool reads the IDML, finds every ImageFrame referencing the AI,
records each distinct (offset, scale) tuple, and emits one PDF per
distinct ImageFrame. Each output PDF is named deterministically:

  <slug>--ai-<ai_basename>--<index>.pdf

Plus a manifest at <out_dir>/composite_ai_split.yml.

Usage:
  python3 tools/composite_ai_split.py <ai_path> <idml_path> <out_dir>
                                       [--slug SLUG]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml
from lxml import etree


def _parse_transform(s: str) -> tuple[float, float, float, float, float, float] | None:
    parts = s.split()
    if len(parts) != 6:
        return None
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def _iter_imageframes_for_ai(
    idml_path: Path,
    ai_basename: str,
) -> list[dict]:
    """Walk the IDML and yield one dict per ImageFrame referencing the AI.

    Returns: list of {"anname": str, "frame_transform": tuple, "image_transform": tuple}.
    """
    out: list[dict] = []
    with zipfile.ZipFile(str(idml_path)) as zf:
        for entry in zf.namelist():
            if not (
                entry.startswith("Stories/")
                or entry.startswith("Spreads/")
            ):
                continue
            try:
                root = etree.fromstring(zf.read(entry))
            except (etree.XMLSyntaxError, KeyError):
                continue
            for link in root.iter():
                if etree.QName(link).localname != "Link":
                    continue
                uri = link.get("LinkResourceURI", "") or ""
                if Path(uri).name != ai_basename:
                    continue
                # Image element is link's parent in IDML.
                image = link.getparent()
                if image is None or etree.QName(image).localname != "Image":
                    continue
                image_tf = _parse_transform(image.get("ItemTransform", "")) or (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                # Walk up to the frame (Rectangle / Polygon / Oval).
                node = image.getparent()
                frame_tf = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                anname = ""
                while node is not None:
                    tag = etree.QName(node).localname
                    if tag in ("Rectangle", "Polygon", "Oval"):
                        parsed = _parse_transform(node.get("ItemTransform", ""))
                        if parsed:
                            frame_tf = parsed
                        anname = node.get("Self", "")
                        break
                    node = node.getparent()
                out.append(
                    {
                        "anname": anname,
                        "frame_transform": frame_tf,
                        "image_transform": image_tf,
                    }
                )
    return out


def split(
    ai_path: Path,
    idml_path: Path,
    out_dir: Path,
    slug: str | None = None,
) -> dict:
    """Emit per-frame PDFs and return the manifest dict."""
    if not ai_path.exists():
        raise FileNotFoundError(f"AI file not found: {ai_path}")
    if not idml_path.exists():
        raise FileNotFoundError(f"IDML not found: {idml_path}")
    out_dir.mkdir(parents=True, exist_ok=True)
    ai_basename = ai_path.name
    ai_stem = ai_path.stem
    frames = _iter_imageframes_for_ai(idml_path, ai_basename)
    if not frames:
        return {
            "source": str(ai_path),
            "pages_emitted": [],
            "warning": "no ImageFrames in IDML referenced this AI",
        }

    # Deduplicate on (frame_tx, frame_ty, image_a, image_d, image_tx, image_ty).
    seen: list[dict] = []
    keys: set[tuple] = set()
    for f in frames:
        ftx, fty = f["frame_transform"][4], f["frame_transform"][5]
        ia, _ib, _ic, idy, itx, ity = f["image_transform"]
        key = (round(ftx, 3), round(fty, 3), round(ia, 4), round(idy, 4),
               round(itx, 3), round(ity, 3))
        if key in keys:
            continue
        keys.add(key)
        seen.append(f)

    # Sort by frame x then y for deterministic numbering (left-to-right,
    # top-to-bottom layout).
    seen.sort(key=lambda f: (f["frame_transform"][4], f["frame_transform"][5]))

    pages_emitted: list[dict] = []
    for idx, frame in enumerate(seen):
        out_name = (
            f"{slug or 'split'}--ai-{ai_stem}--{idx}.pdf"
            if slug
            else f"{ai_stem}--{idx}.pdf"
        )
        out_path = out_dir / out_name
        # Phase 1 splitter: copy the whole AI to each output slot. The
        # downstream converter is responsible for cropping via Scribus
        # LOCALX/LOCALY based on the ImageFrame's LocalOffset. This keeps
        # the split idempotent and reversible; the per-icon CROP via
        # pdftocairo -x / -y / -W / -H is a follow-up refinement.
        shutil.copy(ai_path, out_path)
        try:
            out_rel = str(out_path.resolve()).replace("\\", "/")
        except ValueError:
            out_rel = str(out_path)
        pages_emitted.append(
            {
                "index": idx,
                "out": out_rel,
                "idml_anname": frame["anname"],
                "frame_transform": list(frame["frame_transform"]),
                "image_transform": list(frame["image_transform"]),
            }
        )

    manifest = {
        "source": str(ai_path),
        "ai_basename": ai_basename,
        "pages_emitted": pages_emitted,
    }
    (out_dir / "composite_ai_split.yml").write_text(
        yaml.safe_dump(manifest, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="composite_ai_split",
        description=(
            "Split a composite-AI strip into per-frame PDF copies based on "
            "the ImageFrame references in the IDML."
        ),
    )
    parser.add_argument("ai_path", type=Path, help="Path to the composite .ai file.")
    parser.add_argument("idml_path", type=Path, help="Path to the IDML.")
    parser.add_argument("out_dir", type=Path, help="Directory to write per-frame PDFs.")
    parser.add_argument(
        "--slug",
        default=None,
        help="Slug prefix for the output filenames.",
    )
    args = parser.parse_args(argv)
    manifest = split(args.ai_path, args.idml_path, args.out_dir, args.slug)
    if not manifest.get("pages_emitted"):
        print("composite_ai_split: no ImageFrames referenced this AI.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
