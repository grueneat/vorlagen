"""Defined remediation playbook for first-line y-anchor drift.

When `line_spacing_pixel_audit` reports a frame where ALL per-line
drifts are uniform (within UNIFORM_TOL_PT), the line SPACING is
correct but the FIRST-LINE position is off. The fix is a y_mm shift
on the frame, not a LINESPMode/LINESP change.

## The sign problem

The mapping from build.py `y_mm` to Scribus's rendered SLA YPOS depends
on the paragraph style's FirstBaselineOffset interpretation. Empirical
calibration on Portrait u155 vs u1c7 (same direction shift, opposite
outcomes) shows the sign is NOT GLOBAL.

This playbook does TWO things:

  1. **Empirical sign discovery**: applies a small `+CAL_MM` test shift
     to a test frame on a fresh build.py, re-renders, measures the
     resulting drift change. The sign of that change reveals whether
     `+y_mm → +drift_pt` or `+y_mm → -drift_pt` for this template.
     Cached in `build/playbook_cache/<slug>/y_mm_sign.txt`.

  2. **Apply when calibration is known**: with the cached sign, applies
     proportional shifts to all uniform-offset frames.

When code cannot calibrate (test frame ambiguous, no actionable
frames, etc.), emits LLM-actionable output describing the
candidate shift + the Edit instruction to apply manually.

ESCALATES with explicit Edit instructions when:
- Frame is rotated (y-axis math doesn't apply directly)
- Frame is in a known multi-line-count mismatch state (audit only
  measures first line; shift result is unreliable)
- Calibration test inconclusive
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from statistics import mean

import yaml

UNIFORM_TOL_PT = 0.6
PT_PER_MM = 25.4 / 72.0
CAL_MM = 0.5  # calibration shift in mm


def _load_pixel_audit(slug: str, repo: Path) -> list[dict]:
    p = repo / "build" / "validation" / slug / "line_spacing_pixel_audit.yml"
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text()) or {}
    return data.get("rows") or []


def _is_uniform_offset(per_line: list) -> tuple[bool, str]:
    """True if per-line drifts cluster tight enough that mean shift helps."""
    if not per_line:
        return False, "no per-line drift data"
    nums = [d for d in per_line if isinstance(d, (int, float))]
    if not nums:
        return False, "no numeric drifts"
    if len(nums) == 1:
        return True, "single-line frame — high uncertainty"
    spread = max(nums) - min(nums)
    if spread <= UNIFORM_TOL_PT:
        return True, f"per-line spread {spread:.2f}pt"
    return False, f"per-line spread {spread:.2f}pt > {UNIFORM_TOL_PT}pt"


def _shift_frame_y_mm(build_path: Path, anname: str, dy_mm: float, reason: str) -> tuple[bool, str]:
    """Shift a TextFrame's y_mm by dy_mm. Returns (wrote, message)."""
    text = build_path.read_text()
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
        return False, f"frame {anname} not found"
    block = m.group(1)
    if "rotation_deg=" in block and not re.search(r"rotation_deg=0[,.]?\b", block):
        return False, f"frame {anname} is rotated; y-shift math doesn't apply"
    y_m = re.search(r"y_mm=(-?\d+(?:\.\d+)?)", block)
    if not y_m:
        return False, f"frame {anname} has no y_mm"
    cur_y = float(y_m.group(1))
    new_y = round(cur_y + dy_mm, 4)
    new_block = block.replace(f"y_mm={y_m.group(1)}", f"y_mm={new_y}", 1)
    if new_block == block:
        return False, f"frame {anname} y_mm already at {new_y}"
    marker = f"    # P5/playbook y_mm_shift.py: y_mm {cur_y} → {new_y} ({reason})\n"
    text = text.replace(block, marker + new_block, 1)
    build_path.write_text(text)
    return True, f"frame {anname}: y_mm {cur_y} → {new_y} ({reason})"


def _cache_path(slug: str, repo: Path) -> Path:
    return repo / "build" / "playbook_cache" / slug / "y_mm_sign.txt"


def _read_sign(slug: str, repo: Path) -> int | None:
    """Return +1, -1, or None if uncalibrated."""
    p = _cache_path(slug, repo)
    if not p.exists():
        return None
    v = p.read_text().strip()
    if v in ("+1", "1"):
        return 1
    if v == "-1":
        return -1
    return None


def _write_sign(slug: str, repo: Path, sign: int) -> None:
    p = _cache_path(slug, repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"{sign}\n")


def _calibrate_sign(slug: str, repo: Path, test_anname: str,
                    pre_drift_pt: float) -> tuple[int | None, list[str]]:
    """Apply ±CAL_MM to test_anname, re-render, measure drift change.

    Returns (sign, log_lines). sign is +1 (drift moves with shift),
    -1 (drift moves opposite), or None (inconclusive).
    """
    build_path = repo / "templates" / slug / "build.py"
    log: list[str] = [f"calibrating sign on {test_anname} with pre-drift {pre_drift_pt:+.2f}pt"]

    # Apply +CAL_MM tentative
    wrote, msg = _shift_frame_y_mm(
        build_path, test_anname, +CAL_MM,
        f"calibration probe (+{CAL_MM}mm)",
    )
    if not wrote:
        return None, log + [f"  calibration probe write failed: {msg}"]
    log.append(f"  applied calibration probe: {msg}")

    # Re-render via tune-render --no-transactional (no rollback)
    cmd = [str(repo / "bin" / "tune-render"), slug, "--no-transactional"]
    log.append(f"  re-rendering: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Measure new drift
    rows = _load_pixel_audit(slug, repo)
    new_drift = None
    for r in rows:
        if r.get("anname") == test_anname:
            nums = [d for d in (r.get("per_line_drift_pt") or [])
                    if isinstance(d, (int, float))]
            if nums:
                new_drift = mean(nums)
            break
    if new_drift is None:
        return None, log + [f"  calibration probe: post-render drift not measurable"]

    delta = new_drift - pre_drift_pt
    log.append(f"  post-calibration drift {new_drift:+.2f}pt → delta {delta:+.2f}pt")

    # We applied +CAL_MM. If delta > 0 (drift increased), then +y_mm → +drift,
    # so to REDUCE positive drift we need NEGATIVE shifts → sign = -1.
    # If delta < 0 (drift decreased), +y_mm → -drift, → sign = +1.
    if abs(delta) < 0.5:
        return None, log + ["  delta too small to determine sign"]
    sign = -1 if delta > 0 else +1
    _write_sign(slug, repo, sign)
    log.append(f"  calibrated sign = {sign} ({'+y_mm increases drift' if sign == -1 else '+y_mm decreases drift'})")
    return sign, log


def _llm_actionable_recommendation(frame_info: dict) -> str:
    """Render an LLM-actionable Edit recommendation for one frame."""
    anname = frame_info["anname"]
    avg_pt = frame_info["avg_pt"]
    cur_y = frame_info["cur_y_mm"]
    candidate_dy_mm = abs(avg_pt) * PT_PER_MM
    new_y_pos = round(cur_y + candidate_dy_mm, 4)
    new_y_neg = round(cur_y - candidate_dy_mm, 4)
    return (
        f"  LLM ACTION for {anname} (drift {avg_pt:+.2f}pt, fontsize/style ambiguous):\n"
        f"    Tentative shift |dy| = {candidate_dy_mm:.4f}mm\n"
        f"    Edit templates/<slug>/build.py:\n"
        f"      find:    y_mm={cur_y}\n"
        f"      replace: y_mm={new_y_pos}  (or {new_y_neg} for opposite direction)\n"
        f"    Run bin/tune-render <slug> and check the new drift; reverse if worse."
    )


def apply(slug: str, repo: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    log: list[str] = []
    rows = _load_pixel_audit(slug, repo)
    build_path = repo / "templates" / slug / "build.py"
    if not build_path.exists():
        return 0, [f"build.py not found at {build_path}"]

    # Collect uniform-offset frames
    uniform = []
    for frame in rows:
        anname = frame.get("anname")
        per_line = frame.get("per_line_drift_pt") or []
        ok, note = _is_uniform_offset(per_line)
        if not ok:
            continue
        if (frame.get("max_drift_pt") or 0) < 1.0:
            continue
        nums = [d for d in per_line if isinstance(d, (int, float))]
        avg_pt = mean(nums)
        uniform.append({
            "anname": anname,
            "avg_pt": avg_pt,
            "note": note,
            "baseline_line_count": frame.get("baseline_line_count"),
            "preview_line_count": frame.get("preview_line_count"),
            "cur_y_mm": _frame_y_mm(build_path.read_text(), anname),
        })

    if not uniform:
        return 0, ["no uniform-offset actionable frames"]

    log.append(f"found {len(uniform)} uniform-offset frame(s)")

    # Get or discover sign
    sign = _read_sign(slug, repo)
    if sign is None:
        if dry_run:
            log.append("no cached sign; calibration deferred (dry-run)")
        else:
            # Pick frame with biggest |drift| and reliable line-count match
            best = sorted(
                [u for u in uniform if u["baseline_line_count"] == u["preview_line_count"]],
                key=lambda u: -abs(u["avg_pt"]),
            )
            if not best:
                log.append("no reliable calibration frame (no line-count match) — "
                           "emitting LLM-actionable recommendations")
                for u in uniform:
                    log.append(_llm_actionable_recommendation(u))
                return 0, log
            test = best[0]
            sign, cal_log = _calibrate_sign(slug, repo, test["anname"], test["avg_pt"])
            log.extend(cal_log)
            if sign is None:
                log.append("calibration inconclusive — emitting LLM-actionable recommendations")
                for u in uniform:
                    log.append(_llm_actionable_recommendation(u))
                return 0, log

    if dry_run:
        return 0, log + [f"would apply sign={sign} to {len(uniform)} frame(s)"]

    # Re-read uniform list — calibration may have updated test frame
    rows = _load_pixel_audit(slug, repo)
    uniform = []
    for frame in rows:
        anname = frame.get("anname")
        per_line = frame.get("per_line_drift_pt") or []
        ok, _ = _is_uniform_offset(per_line)
        if not ok:
            continue
        if (frame.get("max_drift_pt") or 0) < 1.0:
            continue
        nums = [d for d in per_line if isinstance(d, (int, float))]
        avg_pt = mean(nums)
        uniform.append({"anname": anname, "avg_pt": avg_pt})

    n_changes = 0
    for u in uniform:
        dy_mm = sign * u["avg_pt"] * PT_PER_MM
        wrote, msg = _shift_frame_y_mm(
            build_path, u["anname"], dy_mm,
            f"uniform +{u['avg_pt']:+.2f}pt × sign={sign} → {dy_mm:+.4f}mm",
        )
        if wrote:
            n_changes += 1
            log.append(f"  {msg}")
        else:
            log.append(f"  {u['anname']}: {msg}")
    return n_changes, log


def _frame_y_mm(text: str, anname: str) -> float | None:
    """Read current y_mm of a frame from build.py text."""
    pat = re.compile(
        r"^[ \t]*page\d+\.add\(TextFrame\("
        r"(?:(?!\)\)).)*?"
        r"y_mm=(-?\d+(?:\.\d+)?)"
        r"(?:(?!\)\)).)*?"
        r"anname='" + re.escape(anname) + r"'",
        re.MULTILINE | re.DOTALL,
    )
    m = pat.search(text)
    return float(m.group(1)) if m else None
