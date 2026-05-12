#!/usr/bin/env python3
"""Per-Run style fidelity audit.

For each word in baseline.pdf, find the matching word in preview.pdf at the
same page+text and compare font, fontsize, and color. Surfaces:
- Wrong font assigned to a Run (e.g. Gotham where Vollkorn was expected)
- Wrong PointSize (fractional rounding artifacts)
- Wrong color (incorrect brand-color mapping)

Catches the class that D6 (font_audit, document-level) and D7
(text_render_audit, presence-only) miss: a Run that should be
Vollkorn Black Italic 38pt yellow accidentally emitted as
Gotham Narrow 38pt yellow passes both audits but has every glyph wrong.

Usage:
    python3 tools/run_style_audit.py \\
      --preview  templates/<slug>/preview.pdf \\
      --baseline templates/<slug>/baseline.pdf \\
      --template <slug> \\
      --out build/validation/<slug>/run_style_audit.yml

Exit code: 0 always (informational; --audit-strict controls CI gating).

Output schema (run_style_audit.yml):
    template: kandidat-falzflyer-din-lang-gruenes-cover-v2
    baseline_word_count: 444
    preview_word_count: 444
    threshold_size_pt: 0.5
    common_word_threshold: 5
    style_drift_count: 12
    suppressed_common_word_drifts_count: 0
    style_drifts:
      - text: "Headline"
        page: 0
        baseline: {fontname: "GothamNarrow-Ultra", size: 37.93, color: "#ffffff"}
        preview:  {fontname: "GothamNarrow-Black", size: 37.93, color: "#ffffff"}
        drift: {fontname: "diff", size_pt: 0.0, color: false}
        severity: large
    ok: false
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pdfplumber
import yaml

# Extra attributes to extract per word alongside coordinates.
EXTRA_ATTRS = ["fontname", "size", "non_stroking_color"]

# Severity thresholds
SIZE_LARGE_THRESHOLD_PT = 1.0   # size diff > 1.0pt → large
SIZE_SMALL_THRESHOLD_PT = 0.5   # size diff 0.5–1.0pt → small
COLOR_LARGE_THRESHOLD = 30      # RGB/gray Euclidean delta > 30 → large
COLOR_SMALL_THRESHOLD = 5       # RGB/gray Euclidean delta 5–30 → small


# ---------------------------------------------------------------------------
# Color normalisation
# ---------------------------------------------------------------------------

def _normalize_color(c: Any) -> str:
    """Normalise ``non_stroking_color`` to a stable string.

    pdfplumber returns one of:
    - ``None``            → ""
    - ``float``           → grayscale 0.0–1.0 → "gray:<0-255>"
    - ``(r, g, b)``       → "#rrggbb"
    - ``(c, m, y, k)``    → "cmyk:C,M,Y,K"
    """
    if c is None:
        return ""
    if isinstance(c, (int, float)):
        v = int(round(float(c) * 255))
        return f"gray:{v}"
    if isinstance(c, (list, tuple)):
        if len(c) == 3:
            return "#" + "".join(f"{int(round(x * 255)):02x}" for x in c)
        if len(c) == 4:
            return "cmyk:" + ",".join(f"{round(float(x), 3)}" for x in c)
    return str(c)


def _color_delta(a: str, b: str) -> float:
    """Euclidean distance in RGB/gray space between two normalised color strings.

    Returns 0.0 when the strings are identical or when either is empty
    (empty = renderer chose no explicit fill, can't compare reliably).
    Returns 0.0 for CMYK colors (no lossless RGB conversion attempted here;
    font/size drift is the primary signal for CMYK documents).
    """
    if a == b:
        return 0.0
    if not a or not b:
        return 0.0

    def _to_rgb(s: str) -> tuple[float, float, float] | None:
        if s.startswith("#") and len(s) == 7:
            r = int(s[1:3], 16)
            g = int(s[3:5], 16)
            b = int(s[5:7], 16)
            return (r, g, b)
        if s.startswith("gray:"):
            v = float(s[5:])
            return (v, v, v)
        return None  # CMYK or unknown — skip

    rgb_a = _to_rgb(a)
    rgb_b = _to_rgb(b)
    if rgb_a is None or rgb_b is None:
        return 0.0
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(rgb_a, rgb_b)))


# ---------------------------------------------------------------------------
# Word extraction
# ---------------------------------------------------------------------------

def _strip_subset_prefix(fontname: str) -> str:
    """Strip PDF subset prefix (e.g. 'DAZTTR+GothamNarrow-Bold' → 'GothamNarrow-Bold')."""
    if "+" in fontname:
        return fontname.split("+", 1)[1]
    return fontname


def extract_words_with_style(pdf_path: Path) -> list[dict[str, Any]]:
    """Extract per-word style records from all pages of ``pdf_path``.

    Each record contains:
        page (int), text (str),
        fontname (str, subset-prefix stripped),
        size (float, rounded to 2 dp),
        color (str, normalised).
    """
    records: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            for w in page.extract_words(extra_attrs=EXTRA_ATTRS):
                raw_font = w.get("fontname", "") or ""
                records.append({
                    "page": page_idx,
                    "text": w["text"],
                    "fontname": _strip_subset_prefix(raw_font),
                    "size": round(float(w.get("size", 0) or 0), 2),
                    "color": _normalize_color(w.get("non_stroking_color")),
                })
    return records


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------

def _classify_severity(
    font_differs: bool,
    size_diff: float,
    color_diff: float,
) -> str | None:
    """Classify a drift as 'large', 'small', or None (not reported).

    Rules (in order of precedence):
    - large: fontname differs OR size_diff > SIZE_LARGE_THRESHOLD_PT
             OR color_diff > COLOR_LARGE_THRESHOLD
    - small: size_diff in (SIZE_SMALL_THRESHOLD_PT, SIZE_LARGE_THRESHOLD_PT]
             OR color_diff in (COLOR_SMALL_THRESHOLD, COLOR_LARGE_THRESHOLD]
    - None:  everything within thresholds
    """
    if font_differs or size_diff > SIZE_LARGE_THRESHOLD_PT or color_diff > COLOR_LARGE_THRESHOLD:
        return "large"
    if size_diff > SIZE_SMALL_THRESHOLD_PT or color_diff > COLOR_SMALL_THRESHOLD:
        return "small"
    return None


# ---------------------------------------------------------------------------
# Main audit logic
# ---------------------------------------------------------------------------

def run_style_audit(
    preview_pdf: Path,
    baseline_pdf: Path,
    template: str = "",
    threshold_size_pt: float = SIZE_SMALL_THRESHOLD_PT,
    common_word_threshold: int = 5,
    text_render_audit_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Compare per-word style (font, size, color) between preview and baseline.

    For each word in baseline, find the matching word in preview at the same
    (page, text). When multiple matches exist, use a greedy first-available
    approach (consume one preview word per baseline word).

    Common-word filtering: words appearing >= ``common_word_threshold`` times
    on the same page in either PDF are excluded from style_drifts (ambiguous
    match; mirrors D8 logic).

    When ``text_render_audit_counts`` is supplied (shape: ``{"baseline": int,
    "preview": int}`` — Phase D7 totals from pdftotext), an
    ``extraction_engine_disagreement`` block is added to the report. If the
    pdfplumber word counts differ from the pdftotext counts by > 1 %, the
    block's ``warn`` flag is set to True. This surfaces silent engine
    disagreement (Issue #37 P1 task 3): pre-fix v2 falzflyer had pdftotext
    444/444 and pdfplumber 464/458, an issue no audit caught.

    Returns a dict with:
        template, baseline_word_count, preview_word_count,
        threshold_size_pt, common_word_threshold,
        style_drift_count, suppressed_common_word_drifts_count,
        style_drifts (list), ok (bool),
        extraction_engine_disagreement (dict, optional).
    """
    base_words = extract_words_with_style(baseline_pdf)
    prev_words = extract_words_with_style(preview_pdf)

    # Per-page frequency counters for common-word filter.
    base_freq: Counter[tuple[int, str]] = Counter(
        (r["page"], r["text"]) for r in base_words
    )
    prev_freq: Counter[tuple[int, str]] = Counter(
        (r["page"], r["text"]) for r in prev_words
    )

    # Build lookup: (page, text) → list of available preview records.
    prev_by_key: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for r in prev_words:
        key = (r["page"], r["text"])
        prev_by_key.setdefault(key, []).append(r)

    all_drifts: list[dict[str, Any]] = []

    for b in base_words:
        key = (b["page"], b["text"])
        candidates = prev_by_key.get(key)
        if not candidates:
            # Word absent from preview — D7 handles presence, skip here.
            continue

        # Greedy: consume the first available preview word for this (page, text).
        p = candidates.pop(0)

        font_b = b["fontname"]
        font_p = p["fontname"]
        font_differs = font_b != font_p

        size_diff = round(abs(b["size"] - p["size"]), 3)
        color_diff = _color_delta(b["color"], p["color"])
        color_changed = b["color"] != p["color"]

        severity = _classify_severity(font_differs, size_diff, color_diff)
        if severity is None:
            continue

        # Build human-readable color delta annotation.
        if color_changed and color_diff > 0:
            color_drift_str = f"delta_RGB_{int(round(color_diff))}"
        elif color_changed:
            color_drift_str = "delta_format"  # different format (e.g. gray vs rgb)
        else:
            color_drift_str = False  # type: ignore[assignment]

        all_drifts.append({
            "text": b["text"],
            "page": b["page"],
            "baseline": {
                "fontname": font_b,
                "size": b["size"],
                "color": b["color"],
            },
            "preview": {
                "fontname": font_p,
                "size": p["size"],
                "color": p["color"],
            },
            "drift": {
                "fontname": "diff" if font_differs else False,
                "size_pt": size_diff,
                "color": color_drift_str,
            },
            "severity": severity,
        })

    # Apply common-word filter.
    filtered_drifts = [
        d for d in all_drifts
        if base_freq.get((d["page"], d["text"]), 0) < common_word_threshold
        and prev_freq.get((d["page"], d["text"]), 0) < common_word_threshold
    ]
    suppressed_count = len(all_drifts) - len(filtered_drifts)

    # Sort: large-severity first, then by text for determinism.
    filtered_drifts.sort(key=lambda d: (0 if d["severity"] == "large" else 1, d["text"]))

    large_count = sum(1 for d in filtered_drifts if d["severity"] == "large")

    report: dict[str, Any] = {
        "template": template,
        "baseline_word_count": len(base_words),
        "preview_word_count": len(prev_words),
        "threshold_size_pt": threshold_size_pt,
        "common_word_threshold": common_word_threshold,
        "style_drift_count": len(filtered_drifts),
        "suppressed_common_word_drifts_count": suppressed_count,
        "style_drifts": filtered_drifts,
        "ok": large_count == 0,
    }

    # Issue #37 P1 task 3: cross-engine word-count sanity check. pdftotext is
    # the engine D7 trusts; pdfplumber is the engine F (this audit) trusts.
    # If they disagree by > 1 %, surface the disagreement so executors know
    # to investigate rather than silently trusting one engine over the other.
    if text_render_audit_counts is not None:
        base_pdftotext = int(text_render_audit_counts.get("baseline", 0) or 0)
        prev_pdftotext = int(text_render_audit_counts.get("preview", 0) or 0)
        base_plumber = len(base_words)
        prev_plumber = len(prev_words)
        baseline_delta_pct = round(
            abs(base_plumber - base_pdftotext) / max(base_pdftotext, 1) * 100, 2
        )
        preview_delta_pct = round(
            abs(prev_plumber - prev_pdftotext) / max(prev_pdftotext, 1) * 100, 2
        )
        eed = {
            "baseline_pdfplumber": base_plumber,
            "preview_pdfplumber": prev_plumber,
            "baseline_pdftotext": base_pdftotext,
            "preview_pdftotext": prev_pdftotext,
            "baseline_delta_pct": baseline_delta_pct,
            "preview_delta_pct": preview_delta_pct,
            "warn": baseline_delta_pct > 1.0 or preview_delta_pct > 1.0,
        }
        report["extraction_engine_disagreement"] = eed

    return report


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
        prog="run_style_audit",
        description=(
            "Phase F: per-Run font/size/color fidelity audit comparing preview.pdf "
            "to baseline.pdf using pdfplumber per-word style attributes."
        ),
    )
    parser.add_argument("--preview", required=True, type=Path,
                        help="Path to preview.pdf (Scribus-rendered output)")
    parser.add_argument("--baseline", required=True, type=Path,
                        help="Path to baseline.pdf (InDesign/reference ground-truth)")
    parser.add_argument("--template", default="", help="Template slug (for report label)")
    parser.add_argument("--threshold-size", type=float, default=SIZE_SMALL_THRESHOLD_PT,
                        help=f"Small-drift size threshold in PDF points (default: {SIZE_SMALL_THRESHOLD_PT}pt)")
    parser.add_argument("--common-word-threshold", type=int, default=5,
                        help="Words appearing >= this many times per page in either PDF "
                             "are excluded from style_drifts (default: 5)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write YAML report to this path (prints to stdout if omitted)")
    args = parser.parse_args(argv)

    if not args.preview.exists():
        print(f"ERROR: preview PDF not found: {args.preview}", file=sys.stderr)
        return 1
    if not args.baseline.exists():
        print(f"ERROR: baseline PDF not found: {args.baseline}", file=sys.stderr)
        return 1

    report = run_style_audit(
        args.preview, args.baseline,
        template=args.template,
        threshold_size_pt=args.threshold_size,
        common_word_threshold=args.common_word_threshold,
    )
    yaml_text = _yaml_dump(report)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(yaml_text, encoding="utf-8")

    print(yaml_text, end="")

    large = sum(1 for d in report["style_drifts"] if d["severity"] == "large")
    small = sum(1 for d in report["style_drifts"] if d["severity"] == "small")
    slug = args.template or args.preview.name

    if not report["ok"]:
        print(
            f"[{slug}] run_style_audit: {large} large style drifts, {small} small drifts → REVIEW",
            file=sys.stderr,
        )
        return 1

    if small:
        print(f"[{slug}] run_style_audit: 0 large drifts, {small} small drifts (ICC/rounding)")
    else:
        print(f"[{slug}] run_style_audit: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
