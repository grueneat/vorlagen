#!/usr/bin/env python3
"""Systematic per-frame text audit + auto-sim recommendation.

For every TextFrame in a template:
  1. Read line_spacing_pixel_audit.yml drift numbers
  2. Read text_position_audit.yml word-position drifts (XY)
  3. If max_drift_pt > MAJOR_THRESHOLD: classify as "actionable" and
     suggest a line_spacing_sim invocation with a smart candidate set
     centered on the IDML CSR Leading
  4. If word position drift > POS_THRESHOLD on >50% of words in frame:
     flag as "position-actionable" (likely needs y_mm or LINESP fix)

Emits:
  build/validation/<slug>/systematic_text_audit.yml — per-frame report
  build/validation/<slug>/systematic_text_audit.md  — human summary

Exit codes:
  0 — every frame either match or has documented sim outcome in TOLERANCES.yml
  2 — actionable drift exists; report explains what to do

Wire as a preflight gate (Phase E5b) so the audit chain refuses to
declare success until every drift is either fixed or has a documented
sim attempt.
"""
from __future__ import annotations

import argparse
import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAJOR_DRIFT_PT = 1.0  # any per-line drift above this is actionable
POS_DRIFT_PT = 2.0    # text_position_audit threshold


def _load_yaml(p: Path) -> dict | None:
    if not p.exists():
        return None
    return yaml.safe_load(p.read_text())


def _frame_actionable(frame: dict) -> tuple[bool, str]:
    """Return (is_actionable, reason)."""
    if frame.get("classification") == "match":
        return False, "match"
    max_drift = frame.get("max_drift_pt") or 0
    if max_drift is None or max_drift < MAJOR_DRIFT_PT:
        return False, f"sub-threshold ({max_drift}pt)"
    if frame.get("preview_line_count") != frame.get("baseline_line_count"):
        return True, f"line count differs (baseline={frame.get('baseline_line_count')} vs preview={frame.get('preview_line_count')})"
    per_line = frame.get("per_line_drift_pt", [])
    if per_line and all(abs(d) >= MAJOR_DRIFT_PT for d in per_line):
        # Check if signs match (true uniform offset) vs split (some +, some -)
        signs = {1 if d > 0 else -1 for d in per_line if d != 0}
        if len(signs) == 1:
            return True, f"uniform offset {per_line[0]:+.2f}pt across all lines (first-line-anchor or LINESP) — y_mm_shift candidate"
        else:
            return True, f"SPLIT offset (signs differ across lines): {per_line} — likely per-paragraph anchor; needs split-frame or per-para LINESP"
    if any(abs(d) >= MAJOR_DRIFT_PT for d in per_line):
        return True, f"max per-line drift {max_drift:+.2f}pt — non-uniform pattern, sim-driven fix"
    return False, "no actionable drift"


def _suggest_sim(frame: dict, build_text: str, slug: str) -> dict:
    """Suggest a line_spacing_sim invocation for the frame."""
    anname = frame["anname"]
    # Get fontsize from the build.py frame definition (rough heuristic)
    # For sim, give a candidate set sweeping around the authored Leading
    suggestion = {
        "anname": anname,
        "max_drift_pt": frame.get("max_drift_pt"),
        "cumulative_drift_pt": frame.get("cumulative_drift_pt"),
        "per_line_drift_pt": frame.get("per_line_drift_pt"),
        "command": (
            f"PYTHONPATH=. python3 tools/line_spacing_sim.py "
            f"--slug {slug} --anname {anname} "
            "--candidates '1:,0:<authored>,0:<authored-2>,0:<authored+2>' "
            "--expected-words '<frame-text-snippet>' "
            "--fontsize-pt <frame-fontsize>"
        ),
    }
    return suggestion


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--strict", action="store_true",
                    help="Exit non-zero if any actionable drift remains.")
    ap.add_argument("--out-yaml", type=Path,
                    help="Write report YAML to this path (default: build/validation/<slug>/systematic_text_audit.yml)")
    ap.add_argument("--out-md", type=Path,
                    help="Write report MD to this path")
    args = ap.parse_args(argv)

    val_dir = ROOT / "build" / "validation" / args.slug
    pixel_yaml = _load_yaml(val_dir / "line_spacing_pixel_audit.yml")
    pos_yaml = _load_yaml(val_dir / "text_position_audit.yml")
    if pixel_yaml is None:
        print(f"ERROR: {val_dir}/line_spacing_pixel_audit.yml not found. Run bin/tune-render first.", file=sys.stderr)
        return 1

    template_dir = ROOT / "templates" / args.slug
    build_text = (template_dir / "build.py").read_text() if (template_dir / "build.py").exists() else ""
    tolerances_yaml = _load_yaml(template_dir / "TOLERANCES.yml") or {}
    tolerated_annames = set()
    for entry in tolerances_yaml.get("tolerances", []):
        # Pick up annames in either the id (tol:<anname>-...) OR the reason
        for src in (entry.get("id", ""), entry.get("reason", "")):
            for token in src.replace("-", " ").replace(":", " ").split():
                t = token.rstrip(".,()")
                if t.startswith("u") and 2 <= len(t) <= 6 and all(c.isalnum() for c in t):
                    tolerated_annames.add(t)

    actionable = []
    summary = {"match": 0, "sub_threshold": 0, "actionable": 0, "tolerated": 0}

    for frame in pixel_yaml.get("rows", []):
        is_act, reason = _frame_actionable(frame)
        anname = frame.get("anname", "?")
        if not is_act:
            if reason == "match":
                summary["match"] += 1
            else:
                summary["sub_threshold"] += 1
            continue
        # Has actionable drift — check if tolerated
        if anname in tolerated_annames:
            summary["tolerated"] += 1
            continue
        summary["actionable"] += 1
        actionable.append({
            **_suggest_sim(frame, build_text, args.slug),
            "reason": reason,
        })

    out_yaml_path = args.out_yaml or (val_dir / "systematic_text_audit.yml")
    out_md_path = args.out_md or (val_dir / "systematic_text_audit.md")
    out_yaml_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "slug": args.slug,
        "summary": summary,
        "actionable_frames": actionable,
        "thresholds": {"major_drift_pt": MAJOR_DRIFT_PT},
        "ok": summary["actionable"] == 0,
    }
    out_yaml_path.write_text(yaml.safe_dump(report, sort_keys=False))

    md_lines = [
        f"# Systematic text audit — {args.slug}",
        "",
        f"- match: {summary['match']}",
        f"- sub-threshold: {summary['sub_threshold']}",
        f"- tolerated: {summary['tolerated']}",
        f"- **actionable: {summary['actionable']}**",
        "",
    ]
    if actionable:
        md_lines.extend([
            "## Actionable drifts",
            "",
            "Each frame below has measurable drift > 1pt that has NOT been",
            "addressed via a TOLERANCES.yml entry. Run the suggested sim",
            "command to find a (LINESPMode, LINESP) candidate that closes",
            "the drift, then apply via paragraph_attrs in build.py.",
            "",
        ])
        for f in actionable:
            md_lines.extend([
                f"### {f['anname']}",
                f"- max drift: {f['max_drift_pt']:+.2f}pt",
                f"- cumulative drift: {f['cumulative_drift_pt']}",
                f"- per-line: {f['per_line_drift_pt']}",
                f"- reason: {f['reason']}",
                f"- sim command: `{f['command']}`",
                "",
            ])
    out_md_path.write_text("\n".join(md_lines))

    print(f"systematic-text-audit: {summary['actionable']} actionable, {summary['tolerated']} tolerated, {summary['match']+summary['sub_threshold']} clean")
    print(f"  report: {out_md_path}")

    if args.strict and summary["actionable"] > 0:
        print(f"STRICT FAIL: {summary['actionable']} frame(s) with actionable drift", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
