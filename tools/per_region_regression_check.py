#!/usr/bin/env python3
"""Per-region regression check — catches silent per-frame regressions.

The line_spacing_pixel_audit and image_frame_visibility_audit each
produce a snapshot of per-frame measurements (drift in pt, visibility
ratio). They compare against baseline.pdf within a single iteration,
but they do NOT compare against the PREVIOUS render's measurements.

That's a gap: a fix on frame A can silently regress frame B if the
aggregate rollup stays roughly constant. This tool closes the gap by
maintaining `build/<slug>/per_region_history.jsonl` (one row per
audit run) and on each invocation comparing the current state against
the previous row to surface per-frame regressions.

Flags:

- ``line_spacing_drift_increased`` — abs(drift) grew by ≥ 0.5pt
- ``image_visibility_dropped`` — visibility_ratio fell by ≥ 0.10
- ``frame_disappeared`` — frame in iter N-1 missing from iter N
  (e.g. converter renamed an anname or dropped an emission)

Usage (after Phase E4 + E5 have run and written their YAMLs):

    python3 tools/per_region_regression_check.py \\
        --slug <slug> \\
        --out-yaml build/validation/<slug>/per_region_regression.yml \\
        --out-md  build/validation/<slug>/per_region_regression.md

The first run on a slug seeds the history (no comparison possible).
Subsequent runs compare against the last committed entry.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml


_HISTORY_DEPTH = 20            # cap entries; older entries pruned
_LINE_SPACING_REGRESSION_PT = 0.5
_IMAGE_VISIBILITY_REGRESSION = 0.10


def _load_yaml(p: Path) -> dict:
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}


def _flatten_line_spacing(data: dict) -> dict[str, float]:
    """Return {anname: max_drift_pt} from line_spacing_pixel_audit."""
    out: dict[str, float] = {}
    for row in data.get("rows") or []:
        an = row.get("anname")
        d = row.get("max_drift_pt")
        if an is not None and isinstance(d, (int, float)):
            out[an] = float(d)
    return out


def _flatten_image_visibility(data: dict) -> dict[str, float]:
    """Return {anname: visibility_ratio} from image_frame_visibility_audit."""
    out: dict[str, float] = {}
    for row in data.get("rows") or []:
        an = row.get("anname")
        v = row.get("visibility_ratio")
        if an is not None and isinstance(v, (int, float)):
            out[an] = float(v)
    return out


def detect_regressions(
    prev_line_spacing: dict[str, float],
    curr_line_spacing: dict[str, float],
    prev_visibility: dict[str, float],
    curr_visibility: dict[str, float],
) -> list[dict]:
    """Return list of regression rows."""
    regressions: list[dict] = []
    # Line-spacing regressions
    for an, curr_d in sorted(curr_line_spacing.items()):
        prev_d = prev_line_spacing.get(an)
        if prev_d is None:
            continue  # new frame, nothing to compare
        if abs(curr_d) - abs(prev_d) >= _LINE_SPACING_REGRESSION_PT:
            regressions.append({
                "anname": an,
                "kind": "line_spacing_drift_increased",
                "prev_max_drift_pt": round(prev_d, 3),
                "curr_max_drift_pt": round(curr_d, 3),
                "delta_abs_pt": round(abs(curr_d) - abs(prev_d), 3),
            })
    # Frame-disappeared detection (anname was measured before, gone now)
    for an in sorted(set(prev_line_spacing) - set(curr_line_spacing)):
        regressions.append({
            "anname": an,
            "kind": "line_spacing_frame_disappeared",
            "prev_max_drift_pt": round(prev_line_spacing[an], 3),
            "curr_max_drift_pt": None,
        })
    # Image visibility regressions
    for an, curr_v in sorted(curr_visibility.items()):
        prev_v = prev_visibility.get(an)
        if prev_v is None:
            continue
        if (prev_v - curr_v) >= _IMAGE_VISIBILITY_REGRESSION:
            regressions.append({
                "anname": an,
                "kind": "image_visibility_dropped",
                "prev_visibility_ratio": round(prev_v, 3),
                "curr_visibility_ratio": round(curr_v, 3),
                "delta": round(curr_v - prev_v, 3),
            })
    for an in sorted(set(prev_visibility) - set(curr_visibility)):
        regressions.append({
            "anname": an,
            "kind": "image_visibility_frame_disappeared",
            "prev_visibility_ratio": round(prev_visibility[an], 3),
            "curr_visibility_ratio": None,
        })
    return regressions


def append_history(
    history_path: Path,
    line_spacing: dict[str, float],
    visibility: dict[str, float],
) -> None:
    """Append one JSONL row; cap file to _HISTORY_DEPTH."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    if history_path.exists():
        with history_path.open() as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    rows.append({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "line_spacing_max_drift_pt": line_spacing,
        "image_visibility_ratio": visibility,
    })
    # Keep last _HISTORY_DEPTH rows
    rows = rows[-_HISTORY_DEPTH:]
    with history_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def load_previous(history_path: Path) -> Optional[dict]:
    """Return the most recent entry from history, or None on first run."""
    if not history_path.exists():
        return None
    rows = []
    with history_path.open() as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows[-1] if rows else None


def write_yaml(
    regressions: list[dict],
    out_path: Path,
    seeded: bool,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seeded": seeded,
        "regression_count": len(regressions),
        "regressions": regressions,
    }
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))


def write_md(regressions: list[dict], out_path: Path, seeded: bool) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Per-region regression check\n"]
    if seeded:
        lines.append("First run on this slug — history seeded; no comparison performed.\n")
    elif not regressions:
        lines.append("**No regressions detected** since previous audit run.\n")
    else:
        lines.append(f"**{len(regressions)} regression(s) detected** since previous audit run.\n")
        lines.append("| Anname | Kind | Previous | Current | Δ |")
        lines.append("|---|---|---:|---:|---:|")
        for r in regressions:
            an = r["anname"]
            kind = r["kind"]
            if "line_spacing" in kind:
                prev_val = r.get("prev_max_drift_pt")
                curr_val = r.get("curr_max_drift_pt")
                delta = r.get("delta_abs_pt")
            else:
                prev_val = r.get("prev_visibility_ratio")
                curr_val = r.get("curr_visibility_ratio")
                delta = r.get("delta")
            lines.append(f"| {an} | {kind} | {prev_val} | {curr_val} | {delta} |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument(
        "--validation-dir",
        default="build/validation",
        help="Directory containing line_spacing_pixel_audit.yml and image_frame_visibility_audit.yml",
    )
    ap.add_argument(
        "--history-dir",
        default="templates",
        help="Directory containing <slug>/per_region_history.jsonl. "
             "Defaults to templates/ so history persists with the template "
             "(survives `rm -rf build/`) and is portable across machines.",
    )
    ap.add_argument("--out-yaml")
    ap.add_argument("--out-md")
    args = ap.parse_args(argv)

    val_dir = Path(args.validation_dir) / args.slug
    ls_pixel = _load_yaml(val_dir / "line_spacing_pixel_audit.yml")
    img_vis = _load_yaml(val_dir / "image_frame_visibility_audit.yml")
    if not ls_pixel and not img_vis:
        sys.stderr.write(
            f"per_region_regression_check: no audit YAMLs in {val_dir}\n"
            "Run line_spacing_pixel_audit and image_frame_visibility_audit first.\n"
        )
        return 2

    curr_ls = _flatten_line_spacing(ls_pixel)
    curr_vis = _flatten_image_visibility(img_vis)

    history_path = Path(args.history_dir) / args.slug / "per_region_history.jsonl"
    prev = load_previous(history_path)
    seeded = prev is None
    if seeded:
        regressions: list[dict] = []
    else:
        regressions = detect_regressions(
            prev_line_spacing=prev.get("line_spacing_max_drift_pt") or {},
            curr_line_spacing=curr_ls,
            prev_visibility=prev.get("image_visibility_ratio") or {},
            curr_visibility=curr_vis,
        )

    append_history(history_path, curr_ls, curr_vis)

    if args.out_yaml:
        write_yaml(regressions, Path(args.out_yaml), seeded)
    if args.out_md:
        write_md(regressions, Path(args.out_md), seeded)

    if seeded:
        print(
            f"per_region_regression: seeded history at {history_path} "
            f"({len(curr_ls)} line-spacing frames, {len(curr_vis)} image frames)",
            file=sys.stderr,
        )
    elif regressions:
        print(
            f"per_region_regression: {len(regressions)} regression(s) detected since previous run → REVIEW",
            file=sys.stderr,
        )
    else:
        print(
            f"per_region_regression: OK ({len(curr_ls)} line-spacing frames, "
            f"{len(curr_vis)} image frames; no regressions)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
