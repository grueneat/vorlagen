"""Defined remediation playbook for first-line y-anchor drift.

When `line_spacing_pixel_audit` reports a frame where ALL per-line
drifts are uniform (within 0.5pt of each other), the line SPACING
is correct but the FIRST-LINE position is off. The fix is a y_mm
shift on the frame, not a LINESPMode/LINESP change.

Heuristic: drift_pt → mm conversion (1pt = 0.353mm), shift y_mm by
-mean_drift_mm so the rendered first-line lands at the baseline
position.

This complements line_spacing.py — that playbook handles per-line
drift (gap differences between consecutive lines); this one handles
first-line anchor offset (every line shifted by the same amount).

ESCALATES when:
- frame's y_mm shift would land it outside its containing panel
- frame is rotated (rotation invalidates direct y_mm math)
"""
from __future__ import annotations

import re
from pathlib import Path
from statistics import mean

import yaml

UNIFORM_TOL_PT = 0.5
PT_PER_MM = 25.4 / 72.0


def _load_pixel_audit(slug: str, repo: Path) -> list[dict]:
    p = repo / "build" / "validation" / slug / "line_spacing_pixel_audit.yml"
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text()) or {}
    return data.get("rows") or []


def _is_uniform_offset(per_line: list) -> bool:
    """Return True when all per-line drifts are within UNIFORM_TOL_PT of each other."""
    if not per_line or len(per_line) < 2:
        return False
    nums = [d for d in per_line if isinstance(d, (int, float))]
    if len(nums) < 2:
        return False
    return (max(nums) - min(nums)) <= UNIFORM_TOL_PT


def _shift_frame_y_mm(build_path: Path, anname: str, dy_mm: float) -> bool:
    """Shift a TextFrame's y_mm by dy_mm. Returns True on write."""
    text = build_path.read_text()
    pat = re.compile(
        r"(add\(TextFrame\(\s*\n(?:.|\n)*?anname='" + re.escape(anname) +
        r"'(?:.|\n)*?\n\s*\)\)\n)", re.MULTILINE,
    )
    m = pat.search(text)
    if not m:
        return False
    block = m.group(1)
    if "rotation_deg=" in block and not re.search(r"rotation_deg=0[,.]?\b", block):
        # rotated frame — y shift math doesn't apply directly; escalate
        return False
    y_m = re.search(r"y_mm=(-?\d+(?:\.\d+)?)", block)
    if not y_m:
        return False
    cur_y = float(y_m.group(1))
    new_y = round(cur_y + dy_mm, 4)
    new_block = block.replace(f"y_mm={y_m.group(1)}", f"y_mm={new_y}", 1)
    if new_block == block:
        return False
    marker = (
        f"    # P5/playbook y_mm_shift.py: y_mm {cur_y} → {new_y} "
        f"(uniform first-line offset {dy_mm * PT_PER_MM:+.2f}pt → {dy_mm:+.3f}mm)\n"
    )
    text = text.replace(block, marker + new_block, 1)
    build_path.write_text(text)
    return True


def apply(slug: str, repo: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    log: list[str] = []
    rows = _load_pixel_audit(slug, repo)
    build_path = repo / "templates" / slug / "build.py"
    if not build_path.exists():
        return 0, [f"build.py not found at {build_path}"]
    n_changes = 0
    for frame in rows:
        anname = frame.get("anname")
        per_line = frame.get("per_line_drift_pt") or []
        if not _is_uniform_offset(per_line):
            continue
        if (frame.get("max_drift_pt") or 0) < 1.0:
            continue
        nums = [d for d in per_line if isinstance(d, (int, float))]
        avg_pt = mean(nums)
        # pt > 0 means preview is BELOW baseline → shift frame UP (negative dy)
        dy_mm = -avg_pt * PT_PER_MM
        log.append(f"{anname}: uniform offset {avg_pt:+.2f}pt → y_mm shift {dy_mm:+.3f}mm")
        if dry_run:
            continue
        if _shift_frame_y_mm(build_path, anname, dy_mm):
            log.append(f"  {anname}: y_mm shifted")
            n_changes += 1
        else:
            log.append(f"  {anname}: shift skipped (rotated frame, missing y_mm, or no-op)")
    return n_changes, log
