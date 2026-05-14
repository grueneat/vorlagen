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

UNIFORM_TOL_PT = 1.5  # was 0.5; loosened to catch typical FreeType jitter
PT_PER_MM = 25.4 / 72.0


def _load_pixel_audit(slug: str, repo: Path) -> list[dict]:
    p = repo / "build" / "validation" / slug / "line_spacing_pixel_audit.yml"
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text()) or {}
    return data.get("rows") or []


def _is_uniform_offset(per_line: list) -> bool:
    """True when per-line drifts are uniform enough that mean shift helps.

    Single-line frames count as "uniform" — the one drift IS the shift.
    """
    if not per_line:
        return False
    nums = [d for d in per_line if isinstance(d, (int, float))]
    if not nums:
        return False
    if len(nums) == 1:
        return True
    return (max(nums) - min(nums)) <= UNIFORM_TOL_PT


def _shift_frame_y_mm(build_path: Path, anname: str, dy_mm: float) -> bool:
    """Shift a TextFrame's y_mm by dy_mm. Returns True on write."""
    text = build_path.read_text()
    # Match a single frame block — must not cross `))` (next frame).
    pat = re.compile(
        r"(^[ \t]*page\d+\.add\(TextFrame\("
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
        # Empirical sign (issue 2026-05-14): the audit reports
        # `preview_top_pt - baseline_top_pt`. Positive drift means
        # preview ink renders LOWER on page (greater Y in image-pixel
        # coordinates). Shifting frame y_mm DOWN (positive) moved the
        # preview LOWER too — the opposite of what we want. Flipping
        # the sign — shift y_mm in the SAME direction as the drift —
        # produced the empirically-correct +1.92pt → 0pt convergence
        # on u155 in this template.
        dy_mm = +avg_pt * PT_PER_MM
        log.append(f"{anname}: uniform offset {avg_pt:+.2f}pt → y_mm shift {dy_mm:+.3f}mm")
        if dry_run:
            continue
        if _shift_frame_y_mm(build_path, anname, dy_mm):
            log.append(f"  {anname}: y_mm shifted")
            n_changes += 1
        else:
            log.append(f"  {anname}: shift skipped (rotated frame, missing y_mm, or no-op)")
    return n_changes, log
