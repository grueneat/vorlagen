"""tools/experiment_generate/_check_hypothesis_text.py — per-run heuristic.

Scans manifest.yml::hypotheses[].rationale + .expected_outcome for
phrases that imply envelope violation (e.g. '5mm margin', '8pt body',
'text on white'). Surfaces matches as warnings — the authoritative
gate is at render-time (tools/experiment_envelope.py::run_envelope).

Per PLAN.md T15: this is a one-shot per-run tool, not a permanent
addition to the rendering pipeline.

CLI: python3 tools/experiment_generate/_check_hypothesis_text.py <exp_id>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


# Each pattern: (regex, rule_id, severity_tag)
TEXT_PATTERNS = [
    (re.compile(r"\b([0-9]+)\s*mm\s*margin", re.I), "layer1:margin", "margin floor 6mm"),
    (re.compile(r"\b([0-9])(?:\.\d+)?\s*pt\s*body", re.I), "layer1:body_min_pt", "body floor 10pt"),
    (re.compile(r"text\s+on\s+white", re.I), "brand:text_on_green", "type lives on green (CD §7)"),
    (re.compile(r"white\s+plate", re.I), "layer1:type_on_white_plate_forbidden", "type on white plate forbidden"),
    (re.compile(r"\bsans\s*serif|\bcomic|\barial\b", re.I), "brand:font_family", "font must be in shared/ci.yml::fonts"),
    (re.compile(r"\b(red|blue|orange)\b\s*(background|fill|panel)", re.I), "brand:color_palette", "non-brand color"),
]


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: _check_hypothesis_text.py <exp_id>", file=sys.stderr)
        return 2
    exp_id = argv[0]
    manifest_path = ROOT / "experiments" / exp_id / "manifest.yml"
    if not manifest_path.exists():
        print(f"FATAL: {manifest_path} not found", file=sys.stderr)
        return 2
    m = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    findings: list[tuple[str, str, str]] = []
    for h in m.get("hypotheses", []):
        text = " ".join([
            h.get("rationale", "") or "",
            h.get("expected_outcome", "") or "",
            h.get("name", "") or "",
        ])
        for pat, rid, hint in TEXT_PATTERNS:
            mt = pat.search(text)
            if mt:
                findings.append((h["slug"], rid, f"{hint}: matched {mt.group(0)!r}"))
    if findings:
        print(f"WARN: {len(findings)} text-level envelope concerns:", file=sys.stderr)
        for slug, rid, hint in findings:
            print(f"  - {slug}: {rid} — {hint}", file=sys.stderr)
        return 1
    print("OK: no text-level envelope concerns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
