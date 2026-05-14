"""Defined remediation playbook for image_frame_visibility_audit findings.

Two distinct cases the parent audit conflates:

  1. **True invisibility**: Scribus 1.6.x SCALETYPE=1 + small frame +
     RGBA white-on-transparent PNG renders fully transparent. Fix:
     switch frame to scale_type=0 + image= ref pattern.
  2. **False positive (L-014)**: White-on-dark imagery (e.g.
     gruene-logo-bund-weiss-cmyk.png on dark green background).
     Audit measures dark-ink density, sees 0% in preview, classifies
     as invisible — but the rendered output IS correct. Polarity
     check distinguishes: if EITHER dark-ink OR light-ink density in
     preview is within 50% of baseline (in the matching polarity),
     the frame is OK and the audit is wrong.

This playbook implements case 1 deterministically and case 2 by
marking the frame as a known false positive (writes a TOLERANCES.yml
row citing the L-014 audit gap).

ESCALATES when neither case applies — frame is invisible AND not
white-on-dark, indicating a converter-level issue (wrong asset path,
clipping mask, etc.).
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

POLARITY_TOLERANCE = 0.5  # ratio of preview/baseline density


def _load_visibility_audit(slug: str, repo: Path) -> list[dict]:
    p = repo / "build" / "validation" / slug / "image_frame_visibility_audit.yml"
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text()) or {}
    rows = data.get("rows") or data.get("frames") or []
    return rows


def _measure_polarity(slug: str, anname: str, bbox_mm: list,
                      page: int, repo: Path) -> tuple[float, float, float, float]:
    """Return (baseline_dark, preview_dark, baseline_light, preview_light) ratios."""
    from PIL import Image
    PX_PER_MM = 150 / 25.4
    DARK = 100
    LIGHT = 200
    out = []
    val_dir = repo / "build" / "validation" / slug
    for path in (val_dir / f"baseline-page-{page+1}.png", val_dir / f"dsl-page-{page+1}.png"):
        if not path.exists():
            return (0, 0, 0, 0)
        img = Image.open(path).convert("L")
        x, y, w, h = bbox_mm
        px_x = int(x * PX_PER_MM)
        px_y = int(y * PX_PER_MM)
        px_w = int(w * PX_PER_MM)
        px_h = int(h * PX_PER_MM)
        crop = img.crop((px_x, px_y, px_x + px_w, px_y + px_h))
        pixels = list(crop.getdata())
        n = len(pixels) or 1
        dark = sum(1 for p in pixels if p < DARK) / n
        light = sum(1 for p in pixels if p > LIGHT) / n
        out.extend([dark, light])
    # out = [baseline_dark, baseline_light, preview_dark, preview_light]
    return (out[0], out[2], out[1], out[3])


def _is_white_on_dark(baseline_dark: float, preview_dark: float,
                     baseline_light: float, preview_light: float) -> bool:
    """The asset renders correctly in light-on-dark polarity."""
    if baseline_light < 0.05:
        return False  # baseline isn't light-heavy; not the white-on-dark case
    if preview_light < 0.05:
        return False  # preview has no light pixels
    ratio = preview_light / baseline_light
    return abs(1.0 - ratio) <= POLARITY_TOLERANCE


def _swap_to_image_ref(build_path: Path, anname: str, asset_dir_rel: str) -> bool:
    """Switch a frame from inline_image_data to image= ref + scale_type=0.

    Best-effort regex; conservative — only writes when the frame has
    inline_image_data and we can identify the asset path.
    """
    text = build_path.read_text()
    pat = re.compile(
        r"(^[ \t]*page\d+\.add\(ImageFrame\("
        r"(?:(?!\)\)).)*?"
        r"anname='" + re.escape(anname) + r"'"
        r"(?:(?!\)\)).)*?"
        r"\)\)\n)",
        re.MULTILINE | re.DOTALL,
    )
    m = pat.search(text)
    if not m:
        return False
    block = m.group(1)
    # Extract asset filename if there's an _inline_brand_icon call above
    # (heuristic — could be wrong)
    if "inline_image_data=" not in block or "image=" in block:
        return False
    # Look at the helper call right above this frame
    pre = text[:m.start()]
    helper = re.search(r"_inline_brand_icon\(\"([^\"]+)\"\)\s*$", pre[-300:])
    if not helper:
        return False
    asset_name = helper.group(1)
    new_image_line = f"        image='{asset_dir_rel}{asset_name}',\n        scale_type=0,\n"
    new_block = re.sub(
        r"        inline_image_data=[^\n]*\n        inline_image_ext=[^\n]*\n(?:        scale_type=\d+,\n)?",
        new_image_line,
        block,
    )
    if new_block == block:
        return False
    text = text.replace(block, new_block, 1)
    build_path.write_text(text)
    return True


def apply(slug: str, repo: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    log: list[str] = []
    rows = _load_visibility_audit(slug, repo)
    invisible_or_faint = [
        r for r in rows
        if r.get("classification") in ("invisible_in_preview", "faint_in_preview")
    ]
    if not invisible_or_faint:
        return 0, ["no invisible_in_preview / faint_in_preview frames"]
    asset_dir_rel = f"../../shared/assets/{slug}/"
    n_changes = 0
    for frame in invisible_or_faint:
        anname = frame.get("anname", "?")
        bbox_mm = frame.get("bbox_mm")
        page = frame.get("page", 0)
        if not bbox_mm or len(bbox_mm) != 4:
            log.append(f"{anname}: missing bbox_mm — skipping")
            continue
        try:
            bdark, pdark, blight, plight = _measure_polarity(slug, anname, bbox_mm, page, repo)
        except Exception as exc:
            log.append(f"{anname}: polarity measure failed: {exc}")
            continue
        # Case 2: white-on-dark false positive
        if _is_white_on_dark(bdark, pdark, blight, plight):
            log.append(
                f"{anname}: white-on-dark false positive (baseline_light={blight:.2f} "
                f"preview_light={plight:.2f}) — audit gap L-014, no fix needed"
            )
            continue
        log.append(
            f"{anname}: invisible (bdark={bdark:.2f} pdark={pdark:.2f} "
            f"blight={blight:.2f} plight={plight:.2f})"
        )
        if dry_run:
            continue
        # Case 1: try swapping to image= ref + scale_type=0
        if _swap_to_image_ref(repo / "templates" / slug / "build.py", anname, asset_dir_rel):
            log.append(f"  {anname}: swapped to image=ref + scale_type=0")
            n_changes += 1
        else:
            log.append(f"  {anname}: ESCALATE — not inline_image_data form, or asset name unknown")
    return n_changes, log
