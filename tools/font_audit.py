"""tools/font_audit.py — Phase D6 pdffonts audit.

Runs ``pdffonts`` on a preview PDF and a baseline PDF, strips subset
prefixes (e.g. ``DAZTTR+``), diffs the embedded-font name sets, and
writes a ``font_audit.yml`` report.

Usage (standalone):
    python3 tools/font_audit.py <preview.pdf> <baseline.pdf> [--out font_audit.yml]

Used by render_pipeline._run_audit as part of the per-template audit chain.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Pattern that matches the subset prefix, e.g. "DAZTTR+" before the real name.
_SUBSET_PREFIX_RE = re.compile(r"^[A-Z]{6}\+")


def _parse_pdffonts_output(raw: str) -> list[str]:
    """Parse the tabular output of ``pdffonts`` and return deduplicated font names.

    Handles the two-line header:
        name   type   encoding   emb sub uni object ID
        -----  -----  ---------  --- --- --- ---------

    Returns a sorted list of unique font names with subset prefix stripped.
    Returns an empty list on malformed / empty output.
    """
    lines = raw.splitlines()
    # Find the separator line (dashes) to locate where data starts.
    data_lines = []
    past_header = False
    for line in lines:
        if not past_header:
            if re.match(r"^-{4}", line):
                past_header = True
            continue
        stripped = line.strip()
        if not stripped:
            continue
        # Each data line starts with the font name; columns are separated by
        # whitespace.  The name itself may contain spaces, so we can't simply
        # split().  pdffonts uses fixed-width columns: name is in cols 0-36,
        # type in cols 37-53, etc.  We take everything up to col 36 and strip.
        name_col = stripped[:37].strip() if len(stripped) >= 37 else stripped.split()[0] if stripped else ""
        if not name_col:
            continue
        # Strip subset prefix (e.g. "DAZTTR+GothamNarrow-Bold" → "GothamNarrow-Bold").
        name_col = _SUBSET_PREFIX_RE.sub("", name_col)
        if name_col:
            data_lines.append(name_col)
    return sorted(set(data_lines))


def _run_pdffonts(pdf_path: Path) -> tuple[list[str], str | None]:
    """Shell out to ``pdffonts`` and return (font_names, error_message).

    Returns ([], error_str) if pdffonts is not installed or fails.
    Returns (names, None) on success.
    """
    if not shutil.which("pdffonts"):
        return [], "pdffonts not installed (install poppler-utils)"
    try:
        result = subprocess.run(
            ["pdffonts", str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return [], f"pdffonts exit {result.returncode}: {result.stderr.strip()}"
        return _parse_pdffonts_output(result.stdout), None
    except subprocess.TimeoutExpired:
        return [], "pdffonts timed out after 30s"
    except Exception as exc:  # noqa: BLE001
        return [], f"pdffonts error: {exc}"


def run_font_audit(
    preview_pdf: Path,
    baseline_pdf: Path,
    template: str = "",
) -> dict[str, Any]:
    """Compare embedded fonts between preview_pdf and baseline_pdf.

    Returns a report dict with keys:
        template, baseline_fonts, preview_fonts,
        missing_in_preview, extra_in_preview, ok, error (optional).
    """
    report: dict[str, Any] = {"template": template}

    baseline_fonts, baseline_err = _run_pdffonts(baseline_pdf)
    preview_fonts, preview_err = _run_pdffonts(preview_pdf)

    errors = []
    if baseline_err:
        errors.append(f"baseline: {baseline_err}")
    if preview_err:
        errors.append(f"preview: {preview_err}")

    report["baseline_fonts"] = baseline_fonts
    report["preview_fonts"] = preview_fonts

    baseline_set = set(baseline_fonts)
    preview_set = set(preview_fonts)

    missing = sorted(baseline_set - preview_set)
    extra = sorted(preview_set - baseline_set)

    report["missing_in_preview"] = missing
    report["extra_in_preview"] = extra

    if errors:
        report["error"] = "; ".join(errors)
        report["ok"] = False
    else:
        report["ok"] = len(missing) == 0

    return report


def _yaml_dump(report: dict[str, Any]) -> str:
    """Minimal YAML serialiser (no external deps)."""
    lines = [f"template: {report.get('template', '')}"]

    for key in ("baseline_fonts", "preview_fonts", "missing_in_preview", "extra_in_preview"):
        val = report.get(key, [])
        if val:
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: []")

    ok_val = report.get("ok", False)
    lines.append(f"ok: {'true' if ok_val else 'false'}")

    if "error" in report:
        lines.append(f"error: {report['error']}")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="font_audit",
        description="Diff pdffonts output between preview and baseline PDFs.",
    )
    parser.add_argument("preview_pdf", type=Path)
    parser.add_argument("baseline_pdf", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="Write YAML report here.")
    parser.add_argument("--template", default="")
    args = parser.parse_args(argv)

    report = run_font_audit(args.preview_pdf, args.baseline_pdf, template=args.template)
    yaml_text = _yaml_dump(report)

    if args.out:
        args.out.write_text(yaml_text, encoding="utf-8")

    print(yaml_text, end="")
    missing = report.get("missing_in_preview", [])
    if missing:
        print(
            f"[{args.template or args.preview_pdf.name}] font_audit: "
            f"{len(missing)} missing variant(s) (silent fallback) → FAIL",
            file=sys.stderr,
        )
        return 1
    print(f"[{args.template or args.preview_pdf.name}] font_audit: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
