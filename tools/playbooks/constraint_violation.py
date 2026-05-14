"""Defined remediation playbook for structural_check failures.

Handles the constraint-violation class. Reads
`build/validation/<slug>/structural_check.yml` and per violation:

  - same_rotation: adopt the reference (first target) rotation onto
    the offender(s). Deterministic.
  - same_x / same_y / same_size: adopt the median value across all
    targets. Deterministic when median is unambiguous.
  - distance_y / equal_gap_y: ESCALATE — fixing means choosing which
    frame moves, which is layout intent the playbook can't decide.
  - inside: ESCALATE — moving to fit requires layout decision.

Returns (n_changes, log_lines).
"""
from __future__ import annotations

import re
import statistics
from pathlib import Path

import yaml


def _frame_rotation(build_text: str, anname: str) -> tuple[float | None, str]:
    """Find rotation_deg for a frame; returns (value, frame_kind)."""
    pat = re.compile(
        r"add\((\w+)\(\s*\n((?:.|\n)*?\n\s*\)\)\n)",
        re.MULTILINE,
    )
    for m in pat.finditer(build_text):
        kind = m.group(1)
        body = m.group(2)
        if f"anname='{anname}'" not in body:
            continue
        rot_m = re.search(r"rotation_deg=(-?\d+(?:\.\d+)?)", body)
        if rot_m:
            return float(rot_m.group(1)), kind
        return 0.0, kind
    return None, ""


def _set_frame_rotation(build_path: Path, anname: str, new_rot: float) -> bool:
    """Set rotation_deg on a frame; insert if missing."""
    text = build_path.read_text()
    pat = re.compile(
        r"(^[ \t]*page\d+\.add\(\w+\(\s*\n(?:.|\n)*?anname='" + re.escape(anname) +
        r"'(?:.|\n)*?\n[ \t]*\)\)\n)", re.MULTILINE,
    )
    m = pat.search(text)
    if not m:
        return False
    block = m.group(1)
    if "rotation_deg=" in block:
        new_block = re.sub(
            r"rotation_deg=-?\d+(?:\.\d+)?",
            f"rotation_deg={new_rot}",
            block,
        )
    else:
        # Insert after layer=N line
        new_block = re.sub(
            r"(layer=\d+,\n)",
            r"\1        # rotation_deg restored by playbook (constraint_violation)\n"
            f"        rotation_deg={new_rot},\n",
            block,
            count=1,
        )
    if new_block == block:
        return False
    text = text.replace(block, new_block, 1)
    build_path.write_text(text)
    return True


def apply(slug: str, repo: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    log: list[str] = []
    sc_path = repo / "build" / "validation" / slug / "structural_check.yml"
    if not sc_path.exists():
        return 0, ["structural_check.yml not found"]
    data = yaml.safe_load(sc_path.read_text()) or {}
    constraint_errors = data.get("constraint_errors") or []
    if not constraint_errors:
        return 0, ["no constraint_errors"]

    build_path = repo / "templates" / slug / "build.py"
    if not build_path.exists():
        return 0, [f"build.py not found at {build_path}"]

    n_changes = 0
    for err in constraint_errors:
        rule = err.get("rule", "")
        location = err.get("location", "")
        message = err.get("message", "")

        if rule.startswith("same_rotation:"):
            # Parse "rotation drift: reference=-18.0°, offenders=[('u186', -9.0)], tolerance=±0.1°"
            ref_m = re.search(r"reference=(-?[\d.]+)", message)
            offenders_m = re.findall(r"\('(u[0-9a-f]+)',\s*(-?[\d.]+)\)", message)
            if not ref_m or not offenders_m:
                log.append(f"{rule}: could not parse — skipping")
                continue
            ref_rot = float(ref_m.group(1))
            log.append(f"{rule}: reference={ref_rot}°, offenders={offenders_m}")
            if dry_run:
                continue
            for anname, _ in offenders_m:
                if _set_frame_rotation(build_path, anname, ref_rot):
                    log.append(f"  {anname}: rotation_deg={ref_rot}° applied")
                    n_changes += 1
                else:
                    log.append(f"  {anname}: write failed")
            continue

        # Other constraint classes — ESCALATE
        if rule.startswith(("distance_y:", "distance_x:", "equal_gap_y:",
                            "equal_gap_x:", "inside:")):
            log.append(f"{rule}: ESCALATE — layout intent decision (not deterministic). "
                       f"Location {location}: {message[:100]}")
            continue

        if rule.startswith(("same_x:", "same_y:", "same_size:")):
            log.append(f"{rule}: ESCALATE — needs median-vs-reference choice. "
                       f"Location {location}: {message[:100]}")
            continue

        log.append(f"{rule}: no playbook recipe — ESCALATE. {message[:100]}")

    return n_changes, log
