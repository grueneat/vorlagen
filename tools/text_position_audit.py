#!/usr/bin/env python3
"""tools/text_position_audit.py — Phase D8 per-word position drift audit.

Catches text that was rendered but mis-positioned: alignment drift, group-
transform-style coordinate gaps (e.g. the known +5.05mm x-shift on some
v2 falzflyer frames), off-by-margin bugs.

Approach: use ``pdfplumber.extract_words()`` to get bounding-box coordinates
for every word in both preview.pdf and baseline.pdf (per page). For each
baseline word, find the nearest matching preview word (same page, same text).
Compute (dx, dy) in points. Words whose displacement exceeds
``large_delta_threshold_pt`` (default 2.0pt ≈ 0.7mm) are reported as
positioning bugs. Sub-threshold displacements are filed as "AA noise / OK".

A greedy nearest-neighbour match avoids double-counting when the same word
appears multiple times on the page. Words present in baseline but absent from
preview are skipped (D7 catches presence; D8 only audits position).

Output schema (text_position_audit.yml):
    template: kandidat-falzflyer-din-lang-gruenes-cover-v2
    threshold_pt: 2.0
    large_deltas_count: 12
    large_deltas:
      - text: Leonore
        page: 1
        baseline_xy_pt: [659.8, 1004.4]
        preview_xy_pt: [645.5, 1004.4]
        dx_pt: -14.3
        dy_pt: 0.0
        severity: large
    ok: false

CLI:
    python3 tools/text_position_audit.py \\
      --preview  templates/<slug>/preview.pdf \\
      --baseline templates/<slug>/baseline.pdf \\
      --template <slug> \\
      --threshold 2.0 \\
      --out build/validation/<slug>/text_position_audit.yml

Exit code: 0 always (informational tool; --audit-strict controls CI gating).
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pdfplumber
import yaml


# ---------------------------------------------------------------------------
# Core extraction + audit logic
# ---------------------------------------------------------------------------

def extract_words_with_positions(pdf_path: Path) -> list[dict[str, Any]]:
    """Return a list of word records from all pages of pdf_path.

    Each record contains:
        page (0-indexed int), text (str),
        x0_pt, y0_pt, x1_pt, y1_pt (float, in PDF points, top-down origin).
    """
    records: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            for w in page.extract_words():
                records.append({
                    "page": page_idx,
                    "text": w["text"],
                    "x0_pt": round(float(w["x0"]), 2),
                    "y0_pt": round(float(w["top"]), 2),
                    "x1_pt": round(float(w["x1"]), 2),
                    "y1_pt": round(float(w["bottom"]), 2),
                })
    return records


def run_text_position_audit(
    preview_pdf: Path,
    baseline_pdf: Path,
    template: str = "",
    large_delta_threshold_pt: float = 2.0,
    common_word_threshold: int = 5,
) -> dict[str, Any]:
    """Compare per-word positions between preview_pdf and baseline_pdf.

    For each word in baseline, find the nearest-by-position matching word in
    preview (same page, same text content) and compute (dx, dy). Words with
    |dx| > threshold or |dy| > threshold are reported in ``large_deltas``.

    Common words (appearing >= common_word_threshold times on the same page
    in EITHER PDF) are excluded from ``large_deltas`` after matching. These
    high-frequency words (e.g. lorem ipsum "et", "ur", "modi") produce
    spurious large deltas because the greedy nearest-neighbour matcher
    cross-binds them across multi-column layouts. Unique words (candidate
    names, social handles) are reliably matched and are always reported.

    ``ok`` is True when the filtered ``large_deltas`` list is empty.

    The top 50 deltas by magnitude are included in the report (sufficient for
    human review; the full count is always reported in ``large_deltas_count``).
    ``suppressed_common_word_deltas_count`` records how many deltas were
    excluded by the common-word filter.
    """
    base_words = extract_words_with_positions(baseline_pdf)
    prev_words = extract_words_with_positions(preview_pdf)

    # Count word frequencies per page in each PDF for the common-word filter.
    base_freq: Counter[tuple[int, str]] = Counter(
        (r["page"], r["text"]) for r in base_words
    )
    prev_freq: Counter[tuple[int, str]] = Counter(
        (r["page"], r["text"]) for r in prev_words
    )

    # Build lookup: (page, text) → list of preview word records.
    prev_by_key: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for r in prev_words:
        key = (r["page"], r["text"])
        prev_by_key.setdefault(key, []).append(r)

    deltas: list[dict[str, Any]] = []

    for b in base_words:
        key = (b["page"], b["text"])
        candidates = prev_by_key.get(key)
        if not candidates:
            # Word absent from preview — D7 catches this; D8 skips.
            continue

        # Greedy nearest-by-position match (Euclidean distance on x0, y0).
        b_x, b_y = b["x0_pt"], b["y0_pt"]
        nearest = min(
            candidates,
            key=lambda c: (c["x0_pt"] - b_x) ** 2 + (c["y0_pt"] - b_y) ** 2,
        )
        dx = round(nearest["x0_pt"] - b_x, 2)
        dy = round(nearest["y0_pt"] - b_y, 2)

        if abs(dx) > large_delta_threshold_pt or abs(dy) > large_delta_threshold_pt:
            deltas.append({
                "text": b["text"],
                "page": b["page"],
                "baseline_xy_pt": [b["x0_pt"], b["y0_pt"]],
                "preview_xy_pt": [nearest["x0_pt"], nearest["y0_pt"]],
                "dx_pt": dx,
                "dy_pt": dy,
                "severity": "large",
            })

        # Greedy removal: prevent the same preview word from matching twice.
        candidates.remove(nearest)

    # Filter: exclude common words from large_deltas (ambiguous match).
    filtered_deltas = [
        d for d in deltas
        if base_freq.get((d["page"], d["text"]), 0) < common_word_threshold
        and prev_freq.get((d["page"], d["text"]), 0) < common_word_threshold
    ]
    suppressed_count = len(deltas) - len(filtered_deltas)

    # Sort by total displacement magnitude (descending), keep top 50.
    filtered_deltas.sort(key=lambda d: -(abs(d["dx_pt"]) + abs(d["dy_pt"])))
    top_deltas = filtered_deltas[:50]

    return {
        "template": template,
        "baseline_pdf": str(baseline_pdf),
        "preview_pdf": str(preview_pdf),
        "threshold_pt": large_delta_threshold_pt,
        "common_word_threshold": common_word_threshold,
        "large_deltas_count": len(filtered_deltas),
        "suppressed_common_word_deltas_count": suppressed_count,
        "large_deltas": top_deltas,
        "ok": not filtered_deltas,
    }


# ---------------------------------------------------------------------------
# YAML serialiser — deterministic, sorted keys
# ---------------------------------------------------------------------------

def _yaml_dump(report: dict[str, Any]) -> str:
    """Deterministic YAML output (sorted keys, no timestamps)."""
    return yaml.dump(
        report,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=True,
        width=120,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="text_position_audit",
        description=(
            "Phase D8: per-word position drift audit comparing preview.pdf "
            "to baseline.pdf using pdfplumber bounding boxes."
        ),
    )
    parser.add_argument("--preview", required=True, type=Path,
                        help="Path to preview.pdf (Scribus-rendered output)")
    parser.add_argument("--baseline", required=True, type=Path,
                        help="Path to baseline.pdf (InDesign/reference ground-truth)")
    parser.add_argument("--template", default="", help="Template slug (for report label)")
    parser.add_argument("--threshold", type=float, default=2.0,
                        help="Large-delta threshold in PDF points (default: 2.0pt ≈ 0.7mm)")
    parser.add_argument("--common-word-threshold", type=int, default=5,
                        help="Words appearing >= this many times per page in either PDF "
                             "are excluded from large_deltas (default: 5)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write YAML report to this path (prints to stdout if omitted)")
    args = parser.parse_args(argv)

    if not args.preview.exists():
        print(f"ERROR: preview PDF not found: {args.preview}", file=sys.stderr)
        return 1
    if not args.baseline.exists():
        print(f"ERROR: baseline PDF not found: {args.baseline}", file=sys.stderr)
        return 1

    report = run_text_position_audit(
        args.preview, args.baseline,
        template=args.template,
        large_delta_threshold_pt=args.threshold,
        common_word_threshold=args.common_word_threshold,
    )
    yaml_text = _yaml_dump(report)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(yaml_text, encoding="utf-8")

    print(yaml_text, end="")

    if not report["ok"]:
        print(
            f"[{args.template or args.preview.name}] text_position_audit: "
            f"{report['large_deltas_count']} word(s) drifted > {report['threshold_pt']}pt",
            file=sys.stderr,
        )
        return 1

    print(f"[{args.template or args.preview.name}] text_position_audit: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
