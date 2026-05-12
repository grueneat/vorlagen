#!/usr/bin/env python3
"""tools/text_render_audit.py — Phase D7 render-side text presence audit.

Catches text that build.py emitted to Scribus but Scribus silently suppressed
at render time: frame-too-small clipping, off-page overflow, color-on-color
invisibility, z-order occlusion, threaded-frame overflow, hidden layers, etc.

Approach: run ``pdftotext -layout`` on both preview.pdf and baseline.pdf,
normalise Unicode (NFC + ligature folding) and lowercase, tokenise into
per-word Counters, then diff. Words in baseline but missing (or under-counted)
in preview are surfaced as ``missing_in_preview``.

Output schema (text_render_audit.yml):
    template: kandidat-falzflyer-din-lang-gruenes-cover-v2
    baseline_word_count: 384
    preview_word_count: 312
    missing_in_preview:
      diegruenen: 2
      diegruenenaustria: 1
    extra_in_preview: {}
    ok: false

CLI:
    python3 tools/text_render_audit.py \\
      --preview  templates/<slug>/preview.pdf \\
      --baseline templates/<slug>/baseline.pdf \\
      --template <slug> \\
      --out build/validation/<slug>/text_render_audit.yml

Exit code: 0 always (informational tool; --audit-strict controls CI gating).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Unicode ligature folding table
# ---------------------------------------------------------------------------

# pdftotext may output Latin ligature characters (U+FB00–U+FB06) from PDFs
# that embed them as single glyphs (e.g. ﬃ → ffi). The counterpart PDF may
# have the decomposed sequence. Fold all ligatures before NFC so both forms
# map to identical tokens and are not treated as different words.
_LIGATURE_FOLD: dict[str, str] = {
    "ﬀ": "ff",   # ﬀ
    "ﬁ": "fi",   # ﬁ
    "ﬂ": "fl",   # ﬂ
    "ﬃ": "ffi",  # ﬃ
    "ﬄ": "ffl",  # ﬄ
    "ﬅ": "st",   # ﬅ
    "ﬆ": "st",   # ﬆ
}


def _normalize_text(s: str) -> str:
    """NFC-normalise + fold Latin ligatures (U+FB00–U+FB06) + lowercase."""
    s = unicodedata.normalize("NFC", s)
    for lig, plain in _LIGATURE_FOLD.items():
        s = s.replace(lig, plain)
    return s.lower()


# ---------------------------------------------------------------------------
# Core extraction + audit logic
# ---------------------------------------------------------------------------

def extract_pdf_words(pdf_path: Path) -> Counter:
    """Return a Counter of normalised words extracted from all pages of pdf_path.

    Uses ``pdftotext -layout`` to preserve multi-column spatial order.
    Words are lowercased, Unicode-NFC-normalised, and Latin ligatures are
    folded (ﬃ → ffi, ﬁ → fi, etc.) so baseline and preview tokenise
    identically regardless of whether the PDF embeds ligature glyphs.
    Token definition: runs of \\w, @, ., - (covers handles, domains, names).
    """
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    text = _normalize_text(result.stdout)
    words = re.findall(r"[\w@.\-]+", text)
    return Counter(words)


def run_text_render_audit(
    preview_pdf: Path,
    baseline_pdf: Path,
    template: str = "",
) -> dict[str, Any]:
    """Diff word-level presence between preview_pdf and baseline_pdf.

    Returns a report dict with keys:
        template, baseline_pdf, preview_pdf,
        baseline_word_count, preview_word_count,
        missing_in_preview, extra_in_preview, ok.

    ``ok`` is True only when missing_in_preview is empty (every baseline word
    appears at least as many times in preview as in baseline).
    """
    base = extract_pdf_words(baseline_pdf)
    prev = extract_pdf_words(preview_pdf)

    # Words present MORE OFTEN in baseline → suppressed in preview.
    missing = {
        w: base[w] - prev[w]
        for w in base
        if base[w] > prev[w]
    }
    # Words present MORE OFTEN in preview → extra content (informational).
    extra = {
        w: prev[w] - base[w]
        for w in prev
        if prev[w] > base[w]
    }

    return {
        "template": template,
        "baseline_pdf": str(baseline_pdf),
        "preview_pdf": str(preview_pdf),
        "baseline_word_count": sum(base.values()),
        "preview_word_count": sum(prev.values()),
        "missing_in_preview": dict(
            sorted(missing.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "extra_in_preview": dict(
            sorted(extra.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "ok": not missing,
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
        prog="text_render_audit",
        description=(
            "Phase D7: diff word-level presence between preview.pdf "
            "and baseline.pdf to catch Scribus render-side suppression."
        ),
    )
    parser.add_argument("--preview", required=True, type=Path,
                        help="Path to preview.pdf (Scribus-rendered output)")
    parser.add_argument("--baseline", required=True, type=Path,
                        help="Path to baseline.pdf (InDesign/reference ground-truth)")
    parser.add_argument("--template", default="", help="Template slug (for report label)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write YAML report to this path (prints to stdout if omitted)")
    args = parser.parse_args(argv)

    if not args.preview.exists():
        print(f"ERROR: preview PDF not found: {args.preview}", file=sys.stderr)
        return 1
    if not args.baseline.exists():
        print(f"ERROR: baseline PDF not found: {args.baseline}", file=sys.stderr)
        return 1

    report = run_text_render_audit(args.preview, args.baseline, template=args.template)
    yaml_text = _yaml_dump(report)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(yaml_text, encoding="utf-8")

    print(yaml_text, end="")

    missing = report["missing_in_preview"]
    if missing:
        n_missing = sum(missing.values())
        n_unique = len(missing)
        print(
            f"[{args.template or args.preview.name}] text_render_audit: "
            f"{n_unique} unique words missing ({n_missing} occurrences) "
            f"— silent suppression → FAIL",
            file=sys.stderr,
        )
        return 1

    print(f"[{args.template or args.preview.name}] text_render_audit: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
