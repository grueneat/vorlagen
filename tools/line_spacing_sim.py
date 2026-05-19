#!/usr/bin/env python3
"""Render-and-measure simulator for one TextFrame's leading attributes.

Given an anname, an SLA, and a list of (LINESPMode, LINESP) candidates,
mutates the SLA in /tmp to set those attrs on every <para>/<trail>
inside the PAGEOBJECT, renders to PDF via Scribus, measures the actual
baseline-to-baseline gap, restores the SLA, and reports a table.

This is the empirical "what would N look like" probe the audit alone
can't answer — Scribus's rendering is not predictable from authored
values for sub-metric leadings (issue #40 follow-up).

Usage:
    python3 tools/line_spacing_sim.py \\
        --slug 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover \\
        --anname u1b0 \\
        --candidates '0:20,1:,2:20,2:24,2:27,2:30'

Each candidate is ``mode:linesp`` where empty ``linesp`` means omit.
Output: table of (mode, linesp) → rendered_gap_pt → drift_vs_baseline.
"""
from __future__ import annotations

import argparse
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

import pdfplumber


def _measure_frame_gap(
    pdf: Path,
    bbox_pt: tuple,
    page_idx: int,
    expected_words: list[str] | None = None,
    fontsize_pt: float | None = None,
) -> tuple[list[float], list[dict]]:
    """Return (consecutive gaps in pt, line dicts) inside the frame bbox.

    When ``expected_words`` is provided, keeps only lines whose first
    word matches one of the expected tokens (case-insensitive substring).
    This prevents the crop from contaminating the measurement with
    adjacent-frame body text. Also drops the leading gap from the crop's
    top edge to the first real line.

    ``fontsize_pt`` (if given) is used to drop pathological gaps outside
    ``[fontsize × 0.5, fontsize × 2.5]``.
    """
    with pdfplumber.open(pdf) as doc:
        if page_idx >= len(doc.pages):
            return [], []
        page = doc.pages[page_idx]
        x0, y0, w, h = bbox_pt
        # ``bbox_pt`` comes from build.py — trim-origin (0,0) coordinates.
        # A baseline.pdf cropped out of a marks-on InDesign export carries
        # a MediaBox whose lower-left is NOT the origin (e.g. (29.5, -38.53)
        # for an A6 trim). ``page.crop`` works in the page's own bbox space,
        # so the trim-origin crop rect must be shifted by the page bbox's
        # lower-left corner (page.bbox = (llx, top_of_box, urx, bottom)).
        # For a normal (0,0) MediaBox this is a no-op.
        px0, ptop, _, _ = page.bbox
        ox, oy = float(px0), float(ptop)
        crop = page.crop((
            max(ox, x0 - 2 + ox),
            max(ptop, y0 - 2 + oy),
            min(page.bbox[2], x0 + w + 2 + ox),
            min(page.bbox[3], y0 + h + 2 + oy),
        ))
        words = sorted(
            crop.extract_words(use_text_flow=True),
            key=lambda w: (round(w["top"], 1), w["x0"]),
        )
    lines: list[dict] = []
    for w in words:
        if lines and abs(w["top"] - lines[-1]["top_pt"]) <= 0.5:
            lines[-1]["text"] += " " + w["text"]
            lines[-1]["x_min"] = min(lines[-1]["x_min"], w["x0"])
        else:
            lines.append({
                "top_pt": w["top"],
                "text": w["text"],
                "x_min": w["x0"],
            })
    # Filter by expected text content if provided
    if expected_words:
        expected_lower = [t.lower() for t in expected_words if t]
        lines = [
            ln for ln in lines
            if any(tok in ln["text"].lower() for tok in expected_lower)
        ]
    gaps = [
        round(lines[i + 1]["top_pt"] - lines[i]["top_pt"], 3)
        for i in range(len(lines) - 1)
    ]
    if fontsize_pt:
        lo = fontsize_pt * 0.5
        hi = fontsize_pt * 2.5
        gaps = [g for g in gaps if lo <= g <= hi]
    return gaps, lines


def _frame_bbox_from_sla(sla_text: str, anname: str) -> tuple[float, float, float, float, int]:
    """Return (x_pt, y_pt, w_pt, h_pt, page_idx) for a PAGEOBJECT.

    SLA coordinates are DOCUMENT-level — PAGE elements declare each
    page's PAGEXPOS/PAGEYPOS in the doc. To get pdfplumber page-local
    coordinates we use OwnPage (the SLA's own page-index attribute) and
    subtract that page's origin.
    """
    m = re.search(
        rf'<PAGEOBJECT[^>]*ANNAME="{re.escape(anname)}"[^>]*>',
        sla_text,
    )
    if not m:
        raise ValueError(f"PAGEOBJECT ANNAME={anname!r} not found")
    attrs = m.group(0)
    def f(key, src=attrs):
        mm = re.search(rf'{key}="([-\d.]+)"', src)
        return float(mm.group(1)) if mm else 0.0
    x = f("XPOS")
    y = f("YPOS")
    w = f("WIDTH")
    h = f("HEIGHT")
    own_page_m = re.search(r'OwnPage="(\d+)"', attrs)
    page = int(own_page_m.group(1)) if own_page_m else 0
    # Locate the matching PAGE element and subtract its origin
    page_origins: dict[int, tuple[float, float]] = {}
    for pm in re.finditer(r'<PAGE\s+([^/]+)/>', sla_text):
        page_attrs = pm.group(1)
        num_m = re.search(r'NUM="(\d+)"', page_attrs)
        if not num_m:
            continue
        num = int(num_m.group(1))
        page_origins[num] = (f("PAGEXPOS", page_attrs), f("PAGEYPOS", page_attrs))
    if page in page_origins:
        px, py = page_origins[page]
        x -= px
        y -= py
    return x, y, w, h, page


def _mutate_sla(sla_text: str, anname: str, mode: int, linesp: float | None) -> str:
    """Replace every <para>/<trail> inside the named PAGEOBJECT with the
    requested LINESPMode/LINESP. Preserves other attributes (PARENT, ALIGN)."""
    po_re = re.compile(
        rf'(<PAGEOBJECT[^>]*ANNAME="{re.escape(anname)}".*?</PAGEOBJECT>)',
        re.DOTALL,
    )

    def patch_attrs(elem_str: str) -> str:
        # remove existing LINESPMode/LINESP
        elem_str = re.sub(r'\s*LINESPMode="[^"]*"', "", elem_str)
        elem_str = re.sub(r'\s*LINESP="[^"]*"', "", elem_str)
        # insert new
        attrs_part = f' LINESPMode="{mode}"'
        if linesp is not None:
            attrs_part += f' LINESP="{linesp}"'
        # Insert before the closing /> or >
        if elem_str.endswith("/>"):
            return elem_str[:-2] + attrs_part + "/>"
        elif elem_str.endswith(">"):
            return elem_str[:-1] + attrs_part + ">"
        return elem_str

    def patch_po(m: re.Match) -> str:
        body = m.group(1)
        # Match self-closing <para .../> and <trail .../>. PARENT values
        # often contain '/' (e.g. "idml/normalparagraphstyle") so [^>]* is
        # the right exclusion, not [^/>].
        body = re.sub(
            r"<(para|trail)\b[^>]*?/?>",
            lambda em: patch_attrs(em.group(0)),
            body,
        )
        return body

    return po_re.sub(patch_po, sla_text)


def _render_sla(sla: Path, dest_pdf: Path) -> int:
    """Invoke Scribus to render SLA → PDF."""
    cmd = [
        "scribus",
        "-g",
        "-py", "tools/render_pipeline.py",
        "--",
        str(sla),
        str(dest_pdf),
    ]
    # Use the dedicated render helper if present; else direct scribus PDF export
    helper = Path("bin/render-one-sla")
    if helper.exists():
        result = subprocess.run(
            [str(helper), str(sla), str(dest_pdf)],
            capture_output=True, text=True,
        )
        return result.returncode
    # Fallback: scribus pdf export
    result = subprocess.run(
        ["scribus", "-g", "--no-gui", "-py", "-",  # script via stdin
         str(sla)],
        input=(
            "import scribus, sys\n"
            f"scribus.openDoc({str(sla)!r})\n"
            f"scribus.savePageAsPDF({str(dest_pdf)!r}, 1, [], 'Profile')\n"
            "scribus.closeDoc()\n"
        ),
        capture_output=True, text=True,
    )
    return result.returncode


def _render_sla_direct(sla: Path, dest_pdf: Path) -> int:
    """Render SLA via the existing bin/render-gallery infrastructure.

    Cheaper than spinning a new Scribus invocation per candidate — we
    just need a fresh PDF for the mutated SLA. The render-gallery
    contract assumes a template directory; here we copy the SLA into
    a tempdir-template and call into the same engine.
    """
    import os
    # Easier path: temporarily replace the template's SLA, invoke
    # bin/render-gallery slug --render-only --no-audit, capture the PDF
    # and restore. Done by the caller; this stub just runs scribus.
    cmd = ["scribus", "-g", "--no-gui", "--no-splash",
           "-py", "-",
           str(sla)]
    py = (
        "import scribus, sys, os\n"
        f"scribus.openDoc({str(sla)!r})\n"
        f"out = {str(dest_pdf)!r}\n"
        "pdf = scribus.PDFfile()\n"
        "pdf.file = out\n"
        "pdf.save()\n"
        "scribus.closeDoc()\n"
    )
    result = subprocess.run(cmd, input=py, capture_output=True, text=True, timeout=120)
    if not dest_pdf.exists():
        sys.stderr.write(f"render failed: rc={result.returncode}\nstdout={result.stdout[:400]}\nstderr={result.stderr[:400]}\n")
    return result.returncode


def simulate(
    slug: str,
    anname: str,
    candidates: list[tuple[int, float | None]],
    templates_dir: Path = Path("/workspace/templates"),
    expected_words: list[str] | None = None,
    fontsize_pt: float | None = None,
) -> list[dict]:
    template = templates_dir / slug
    sla_orig = template / "template.sla"
    sla_text_orig = sla_orig.read_text(encoding="utf-8")
    x, y, w, h, page = _frame_bbox_from_sla(sla_text_orig, anname)
    bbox_pt = (x, y, w, h)
    baseline_pdf = template / "baseline.pdf"
    base_gaps, base_lines = _measure_frame_gap(
        baseline_pdf, bbox_pt, page, expected_words, fontsize_pt
    )
    base_median = statistics.median(base_gaps) if base_gaps else None
    results = []
    # Reuse the existing headless Scribus invocation from visual_diff so
    # we get xvfb-run + the proven _export_pdf.py contract.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from visual_diff import render_sla_to_pdf

    tmpdir = Path(tempfile.mkdtemp())
    for mode, linesp in candidates:
        mutated = _mutate_sla(sla_text_orig, anname, mode, linesp)
        sla_tmp = tmpdir / f"sim_{mode}_{linesp}.sla"
        sla_tmp.write_text(mutated, encoding="utf-8")
        pdf_tmp = tmpdir / f"sim_{mode}_{linesp}.pdf"
        try:
            render_sla_to_pdf(sla_tmp, pdf_tmp)
        except Exception as exc:
            sys.stderr.write(
                f"[sim] render failed for mode={mode} linesp={linesp}: {exc!r}\n"
            )
            results.append({
                "mode": mode, "linesp": linesp,
                "preview_gaps": [], "preview_median_pt": None,
                "baseline_median_pt": base_median,
                "drift_vs_baseline_pt": None,
                "render_failed": True,
            })
            continue
        preview_gaps, preview_lines = _measure_frame_gap(
            pdf_tmp, bbox_pt, page, expected_words, fontsize_pt
        )
        preview_median = statistics.median(preview_gaps) if preview_gaps else None
        drift = (
            round(preview_median - base_median, 3)
            if (preview_median is not None and base_median is not None)
            else None
        )
        results.append({
            "mode": mode,
            "linesp": linesp,
            "preview_gaps": preview_gaps,
            "preview_median_pt": preview_median,
            "baseline_median_pt": base_median,
            "drift_vs_baseline_pt": drift,
        })
    shutil.rmtree(tmpdir, ignore_errors=True)
    return results


def _parse_candidates(s: str) -> list[tuple[int, float | None]]:
    out: list[tuple[int, float | None]] = []
    for tok in s.split(","):
        tok = tok.strip()
        if not tok:
            continue
        parts = tok.split(":", 1)
        mode = int(parts[0])
        if len(parts) == 1 or not parts[1].strip():
            out.append((mode, None))
        else:
            out.append((mode, float(parts[1])))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--anname", required=True)
    ap.add_argument("--candidates", required=True,
                    help="comma-separated mode:linesp pairs, e.g. '1:,2:27,2:24,0:27'")
    ap.add_argument("--templates-dir", default="/workspace/templates")
    ap.add_argument(
        "--expected-words",
        help="Comma-separated tokens; only lines whose text contains one of "
             "these tokens are counted. Prevents adjacent-frame contamination.",
    )
    ap.add_argument(
        "--fontsize-pt",
        type=float,
        help="Frame's font size; gaps outside [0.5x, 2.5x] are dropped.",
    )
    args = ap.parse_args(argv)
    expected_words = [
        s.strip() for s in (args.expected_words or "").split(",") if s.strip()
    ] or None
    results = simulate(
        args.slug, args.anname,
        _parse_candidates(args.candidates),
        Path(args.templates_dir),
        expected_words=expected_words,
        fontsize_pt=args.fontsize_pt,
    )
    print(f"# Simulation for {args.anname} on {args.slug}")
    if not results:
        return 1
    base = results[0].get("baseline_median_pt")
    print(f"# baseline_median_pt = {base}")
    print()
    print("| LINESPMode | LINESP | preview_median_pt | drift_vs_baseline_pt | preview_gaps |")
    print("|---:|---:|---:|---:|---|")
    for r in results:
        ls = r["linesp"] if r["linesp"] is not None else "—"
        print(
            f"| {r['mode']} | {ls} | "
            f"{r['preview_median_pt']} | {r['drift_vs_baseline_pt']} | "
            f"{r['preview_gaps']} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
