"""PDF-side walker for SCAFFOLD_INVENTORY.

Two surfaces:

- :func:`walk_pdf` returns a :class:`tools.walkers.schema.WordsBlock` for the
  ``words`` section (preview + optional baseline counts, missing/extra sets).
- :func:`walk_pdf_images` returns a list of logical-image dicts collapsed from
  ``pdfimages -list`` rows so jpeg+smask pairs count as one image.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from tools.text_render_audit import extract_pdf_words
from tools.walkers.schema import WordsBlock


def walk_pdf(preview_pdf: Path, baseline_pdf: Optional[Path] = None) -> WordsBlock:
    """Return a WordsBlock for preview vs (optional) baseline.

    ``missing_from_preview`` = tokens present in baseline but absent in preview.
    ``extra_in_preview`` = tokens present in preview but absent in baseline.
    Each list is sorted to keep YAML diffs deterministic. Counts are
    raw token totals (not unique-token counts) so the comparator can
    threshold against build.py character count per the gate spec.
    """
    preview_words = extract_pdf_words(preview_pdf)
    preview_total = sum(preview_words.values())
    baseline_total = 0
    missing: list[str] = []
    extra: list[str] = []
    if baseline_pdf is not None and baseline_pdf.exists():
        baseline_words = extract_pdf_words(baseline_pdf)
        baseline_total = sum(baseline_words.values())
        preview_set = set(preview_words)
        baseline_set = set(baseline_words)
        missing = sorted(baseline_set - preview_set)
        extra = sorted(preview_set - baseline_set)
    return WordsBlock(
        baseline_pdf_count=baseline_total,
        preview_pdf_count=preview_total,
        missing_from_preview=missing,
        extra_in_preview=extra,
    )


def _parse_pdfimages_raw(output: str) -> list[dict]:
    """Parse every row of ``pdfimages -list`` into a dict.

    Differs from ``tools.baseline_image_audit._parse_pdfimages_list``: that
    helper returns only image-type counts per page. Here we keep smask / mask
    rows too so they can be paired with their parent image during grouping.
    Also surfaces x-ppi / y-ppi (column positions 12/13 in the standard
    pdfimages -list output) so the inventory can compute the rendered
    image's millimetre footprint for per-frame matching.
    """
    rows: list[dict] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("page") or line.startswith("---"):
            continue
        parts = line.split()
        if len(parts) < 9:
            continue
        try:
            page = int(parts[0])
            num = int(parts[1])
            kind = parts[2]
            width = int(parts[3])
            height = int(parts[4])
        except (ValueError, IndexError):
            continue
        # x-ppi / y-ppi columns vary slightly with pdfimages version; the
        # canonical poppler layout used in this repo's CI is:
        #   page num type width height color comp bpc enc interp object ID x-ppi y-ppi size ratio
        # i.e. indices 12 + 13 after the leading 12 columns. Be tolerant —
        # fall back to None when missing.
        x_ppi = None
        y_ppi = None
        try:
            x_ppi = float(parts[12])
            y_ppi = float(parts[13])
        except (IndexError, ValueError):
            pass
        rows.append({
            "page": page,
            "num": num,
            "kind": kind,
            "width": width,
            "height": height,
            "x_ppi": x_ppi,
            "y_ppi": y_ppi,
        })
    return rows


def walk_pdf_images(preview_pdf: Path) -> list[dict]:
    """Return one row per logical image in ``preview_pdf``.

    Groups raw ``pdfimages -list`` rows by ``(page, width, height)`` so that
    JPEG+smask pairs (same pixel dimensions on the same page, one as ``image``
    and one as ``smask``) collapse into a single logical-image entry.

    Each returned row::

        {
            "page": int,           # 1-indexed
            "width": int,          # pixels
            "height": int,         # pixels
            "rows_count": int,     # number of raw pdfimages rows in the group
            "kinds": [...],        # the raw kinds present (e.g. ["image","smask"])
        }
    """
    r = subprocess.run(
        ["pdfimages", "-list", str(preview_pdf)],
        capture_output=True, text=True,
    )
    rows = _parse_pdfimages_raw(r.stdout)
    grouped: dict[tuple, dict] = {}
    for row in rows:
        key = (row["page"], row["width"], row["height"])
        if key not in grouped:
            grouped[key] = {
                "page": row["page"],
                "width": row["width"],
                "height": row["height"],
                "rows_count": 0,
                "kinds": [],
                "x_ppi": row.get("x_ppi"),
                "y_ppi": row.get("y_ppi"),
            }
        grouped[key]["rows_count"] += 1
        grouped[key]["kinds"].append(row["kind"])
    return list(grouped.values())
