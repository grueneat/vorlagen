#!/usr/bin/env python3
"""tools/render_pipeline.py — local render pipeline library (issue #4).

This module implements the per-template gallery render orchestration that
bin/render-gallery exposes as a CLI. Keeping the logic here makes the helpers
unit-testable without invoking the bin shim.

Per-template pipeline (for templates/<id>/ with meta.yml::original_sla):
  1. python3 templates/<id>/build.py             → templates/<id>/template.sla
  2. render_sla_to_pdf(template.sla, preview.pdf) → templates/<id>/preview.pdf
  3. _scrub_pdf_metadata(preview.pdf)             → byte-deterministic PDF
  4. pdftoppm -r <dpi> -png preview.pdf page     → templates/<id>/page-NN.png
  5. tools/sla_diff.py --strict <orig> <template.sla> (subprocess; FAIL on diff)
  6. tools/visual_diff.py against baseline.pdf       (subprocess; FAIL on diff)
  7. SHA256(template.sla) → meta.yml::previews_for_sla
  8. cp artifacts → site/public/templates/<id>/

For family templates (plakat), steps 2-4 and 7 run per-size SLA.

Idempotent: running twice produces no git diff (PDF metadata is byte-scrubbed
via length-preserving regex substitution on CreationDate/ModDate/ID fields).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from visual_diff import render_sla_to_pdf, rasterise, compare_pages, montage_composite  # noqa: E402

DEFAULT_DPI = 50
# Hi-res rasterise pass for the gallery's click-through preview (Issue #28).
# 150 dpi = 3× the thumbnail dpi → ~1240×1754 px on A4 portrait. Stored
# alongside thumbnails as page-NN-hires.png; the Astro template wraps each
# thumbnail in an anchor pointing at the hires variant.
HIRES_DPI = 150

# Fixed replacement values — all length-preserving (PDF spec requires fixed widths).
EPOCH_DATE = b"D:20000101000000Z"   # 16 bytes; same as D:YYYYMMDDhhmmssZ
FIXED_PDF_ID = b"00000000000000000000000000000000"  # 32 hex chars


def _is_renderable(meta: dict) -> bool:
    """Return True when this template should be touched by the render pipeline.

    Two flavours qualify:
      - ``original_sla:`` — round-trip templates (build.py output is sla_diffed
        against a hand-authored original SLA).
      - ``previews_for_sla:`` — DSL-only templates with no upstream original;
        still emit gallery previews and pin a SHA for stale-check.

    Templates without either (smoke fixtures, in-flight scaffolding) are
    intentionally skipped. This widens the issue #4 filter to admit the 5 new
    DSL-only templates from PR #20.
    """
    if not isinstance(meta, dict):
        return False
    return bool(meta.get("original_sla")) or bool(meta.get("previews_for_sla"))


# ---------------------------------------------------------------------------
# PDF byte-scrub for idempotent renders
# ---------------------------------------------------------------------------

def _scrub_pdf_metadata(p: Path) -> None:
    """Replace non-deterministic PDF metadata with fixed length-preserving values.

    Scribus 1.6.x embeds non-deterministic data in two locations:

    1. PDF Info dict (in the object stream near the start):
       - /CreationDate (D:YYYYMMDDhhmmssZ)
       - /ModDate      (D:YYYYMMDDhhmmssZ)
       - /ID [<32hex><32hex>]  (in the trailer)

    2. XMP metadata packet (present for documents with metadata):
       - xmp:CreateDate="YYYY-MM-DDThh:mm:ssZ"
       - xmp:ModifyDate="YYYY-MM-DDThh:mm:ssZ"
       - xmp:MetadataDate="YYYY-MM-DDThh:mm:ssZ"
       - xmpMM:DocumentID="uuid:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    All substitutions are byte-length-preserving:
    - PDF dates: "D:YYYYMMDDhhmmssZ" = 16 bytes
    - ISO 8601 XMP dates: "YYYY-MM-DDThh:mm:ssZ" = 20 bytes
    - UUID: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" = 36 bytes
    - PDF ID hex: 32 hex chars each
    - XMP packet itself is padded to a fixed size for in-place editing.

    The XMP attribute ORDER can also differ between renders (Scribus does not
    guarantee attribute order for non-deterministic fields). However, since each
    field has a unique name/length, the individual regex substitutions work even
    if the order changes — they match the field regardless of position.

    Empirically verified: postkarte (no XMP) and plakat/zeitung (with XMP)
    both produce byte-identical output after this scrub.
    """
    data = p.read_bytes()
    data = re.sub(
        rb"/CreationDate \(D:\d{14}Z\)",
        b"/CreationDate (" + EPOCH_DATE + b")",
        data,
    )
    data = re.sub(
        rb"/ModDate \(D:\d{14}Z\)",
        b"/ModDate (" + EPOCH_DATE + b")",
        data,
    )
    data = re.sub(
        rb"/ID \[<[0-9A-Fa-f]{32}><[0-9A-Fa-f]{32}>\]",
        b"/ID [<" + FIXED_PDF_ID + b"><" + FIXED_PDF_ID + b">]",
        data,
    )
    # Scribus also embeds an XMP metadata packet for some documents. The
    # non-deterministic parts are timestamps AND the attribute ORDER within
    # rdf:Description elements (Scribus doesn't guarantee ordering). Simple
    # value substitution is insufficient because different attribute orders
    # produce different bytes even with the same values. We canonicalize the
    # full XMP packet content while preserving its total byte length
    # (the packet is padded by Scribus for exactly this purpose).
    data = _scrub_xmp_packet(data)
    p.write_bytes(data)


def _scrub_xmp_packet(data: bytes) -> bytes:
    """Canonicalize the XMP metadata packet to eliminate non-determinism.

    Scribus 1.6.x embeds an XMP packet in some documents (not all). The packet
    contains timestamps (xmp:CreateDate, xmp:ModifyDate, xmp:MetadataDate) and a
    DocumentID UUID that vary per render, AND the attributes within rdf:Description
    elements are randomly ordered. Both issues are resolved by replacing the entire
    packet content with a canonical version that has:
    - Fixed epoch timestamps
    - Fixed all-zeros UUID
    - Fixed canonical attribute order
    - Preserved document-specific content (dc:title, dc:creator, dc:description)

    The replacement is byte-length-preserving: the XMP packet is padded by Scribus
    so its total size is fixed. We adjust the padding whitespace to compensate for
    any size change in the XML content.

    If no XMP packet is present (e.g. postkarte-a6-kampagne), returns data unchanged.
    """
    xmp_start = data.find(b'<?xpacket begin')
    if xmp_start == -1:
        return data  # No XMP packet; nothing to scrub.

    # Find the end of the XMP packet.
    end_marker_start = data.find(b'<?xpacket end', xmp_start)
    end_marker_end = data.find(b'?>', end_marker_start) + 2
    original_length = end_marker_end - xmp_start

    # Decode the XMP XML content.
    xmpmeta_end = data.find(b'</x:xmpmeta>', xmp_start)
    xmp_xml = data[xmp_start:xmpmeta_end + len(b'</x:xmpmeta>')].decode('utf-8', errors='replace')

    # Extract the dc: block (title/author/description — stable child elements).
    dc_block_match = re.search(
        r'<rdf:Description[^>]*dc:format="application/pdf"[^>]*>(.*?)</rdf:Description>',
        xmp_xml,
        re.DOTALL,
    )
    dc_inner = dc_block_match.group(1) if dc_block_match else ""

    # Extract pdf:Producer value (may differ by Scribus version).
    pdf_producer_match = re.search(r'pdf:Producer="([^"]*)"', xmp_xml)
    pdf_producer = pdf_producer_match.group(1) if pdf_producer_match else "Scribus PDF Library 1.6.3"

    # Build canonical XMP content with fixed attribute order.
    canonical = (
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Scribus PDF Library 1.6.3">\n'
        '    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '        <rdf:Description'
        ' rdf:about=""'
        ' xmlns:xmp="http://ns.adobe.com/xap/1.0/"'
        ' xmp:CreateDate="2000-01-01T00:00:00Z"'
        ' xmp:CreatorTool="Scribus 1.6.3"'
        ' xmp:MetadataDate="2000-01-01T00:00:00Z"'
        ' xmp:ModifyDate="2000-01-01T00:00:00Z"'
        '/>\n'
        '        <rdf:Description'
        ' rdf:about=""'
        ' xmlns:pdf="http://ns.adobe.com/pdf/1.3/"'
        f' pdf:Keywords=""'
        f' pdf:Producer="{pdf_producer}"'
        ' pdf:Trapped="False"'
        '/>\n'
    )
    if dc_inner:
        canonical += (
            '        <rdf:Description'
            ' rdf:about=""'
            ' dc:format="application/pdf"'
            ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
            '>\n'
            + dc_inner +
            '        </rdf:Description>\n'
        )
    canonical += (
        '        <rdf:Description'
        ' rdf:about=""'
        ' xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/"'
        ' xmpMM:DocumentID="uuid:00000000-0000-0000-0000-000000000000"'
        ' xmpMM:RenditionClass="default"'
        ' xmpMM:VersionID="1"'
        '/>\n'
        '    </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    )
    canonical_bytes = canonical.encode('utf-8')

    # Pad with spaces to preserve the original packet length.
    # (Scribus pads with lines of 100 spaces; we use the same style.)
    end_marker = b"<?xpacket end='w'?>"
    padding_needed = original_length - len(canonical_bytes) - len(end_marker)
    if padding_needed < 0:
        # Should not happen; log a warning but don't crash.
        import sys as _sys
        print(
            f"WARNING: canonicalized XMP is larger than original by {-padding_needed} bytes; "
            "truncating (idempotency may be affected).",
            file=_sys.stderr,
        )
        canonical_bytes = canonical_bytes[:original_length - len(end_marker)]
        padding_needed = 0

    # Build padding: 100-space lines.
    full_lines = padding_needed // 101  # 100 spaces + newline = 101 chars
    remainder = padding_needed - full_lines * 101
    padding = (b' ' * 100 + b'\n') * full_lines
    if remainder > 1:
        padding += b' ' * (remainder - 1) + b'\n'
    elif remainder == 1:
        padding += b'\n'

    full_canonical = canonical_bytes + padding + end_marker
    assert len(full_canonical) == original_length, (
        f"XMP scrub length mismatch: {len(full_canonical)} != {original_length}"
    )

    return data[:xmp_start] + full_canonical + data[end_marker_end:]


# ---------------------------------------------------------------------------
# Brand-font check
# ---------------------------------------------------------------------------

def _verify_brand_fonts() -> None:
    """Verify brand fonts are registered; exit loudly if not.

    Refuses to render if fewer than 5 Gotham Narrow / Vollkorn face entries
    are found in fc-list output, because Scribus would silently fall back to
    DejaVu Sans, producing visually wrong output without any error.
    See shared/fonts/README.md for font installation instructions.
    """
    out = subprocess.run(
        ["fc-list"], capture_output=True, text=True, check=True
    ).stdout
    n = sum(
        1 for line in out.splitlines()
        if re.search(r"gotham narrow|vollkorn", line, re.I)
    )
    if n < 5:
        sys.exit(
            f"FATAL: only {n} brand-font face(s) registered in fc-list (expected >= 5).\n"
            "Refusing to render — Scribus would fall back to DejaVu Sans and produce\n"
            "visually incorrect output without raising an error.\n"
            "Install brand fonts first. See shared/fonts/README.md for instructions."
        )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _sha256_of(p: Path) -> str:
    """Return SHA256 hex digest of the raw bytes of file p."""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _read_template_meta(tdir: Path) -> dict:
    """Load and return the parsed meta.yml for a template directory."""
    return yaml.safe_load((tdir / "meta.yml").read_text(encoding="utf-8"))


def _update_meta_hash(meta_path: Path, value) -> None:
    """Write (or replace) the previews_for_sla: field in meta_path.

    value may be:
    - str  → single-line: ``previews_for_sla: <hash>``
    - dict → multi-line mapping (sorted keys):
              ``previews_for_sla:``
              ``  a0: <hash>``
              …

    Uses a regex find-and-replace on the raw text to avoid disturbing key
    order, YAML comments, or Unicode characters that yaml.safe_dump would
    escape.  Inserts below the original_sla: line if the field is absent.
    """
    text = meta_path.read_text(encoding="utf-8")

    if isinstance(value, str):
        block = f"previews_for_sla: {value}"
    else:
        # dict — build multi-line YAML block
        lines = ["previews_for_sla:"]
        for k in sorted(value.keys()):
            lines.append(f"  {k}: {value[k]}")
        block = "\n".join(lines)

    if re.search(r"^previews_for_sla:", text, re.M):
        # Replace the existing block (str or multi-line dict).
        # The pattern matches from 'previews_for_sla:' up to the next
        # top-level key (non-indented non-empty line) or end-of-string.
        text = re.sub(
            r"^previews_for_sla:.*?(?=^[^\s#]|\Z)",
            block + "\n",
            text,
            flags=re.M | re.S,
        )
    else:
        # Insert directly below the original_sla: line.
        text = re.sub(
            r"^(original_sla:.*)$",
            r"\1\n" + block,
            text,
            count=1,
            flags=re.M,
        )

    meta_path.write_text(text, encoding="utf-8")


def _zero_pad_pngs(tdir: Path, prefix: str) -> None:
    """Rename single-digit ``<prefix>-N.png`` → ``<prefix>-0N.png``.

    pdftoppm uses single-digit suffixes when the PDF has ≤9 pages. The new
    pipeline standardises on zero-padded 2-digit suffixes (``page-01.png``,
    ``page-09.png``, ``page-14.png``). This is a no-op for PDFs that
    pdftoppm already zero-padded (>9 pages).
    """
    for p in sorted(tdir.glob(f"{prefix}-?.png")):
        n = p.stem.rsplit("-", 1)[-1]
        target = p.parent / f"{prefix}-0{n}.png"
        if not target.exists():
            p.rename(target)


def _mirror_to_site_public(tdir: Path, public_dir: Path, *, family: bool) -> None:
    """Copy committed artifacts from tdir/ to site/public/templates/<id>/.

    For non-family: template.sla, preview.pdf, page-*.png.
    For family: *.sla, *.pdf, *-page-*.png.

    Wipes regular files in public_dir first so stale renamed files don't linger.
    """
    public_dir.mkdir(parents=True, exist_ok=True)
    # Remove stale regular files (not subdirs — none expected but be safe).
    for f in public_dir.iterdir():
        if f.is_file():
            f.unlink()

    if family:
        for pat in ("*.sla", "*.pdf", "*-page-*.png"):
            for src in sorted(tdir.glob(pat)):
                shutil.copy(src, public_dir / src.name)
    else:
        for name in ("template.sla", "preview.pdf"):
            src = tdir / name
            if src.exists():
                shutil.copy(src, public_dir / name)
        # Mirror BOTH the thumbnail (page-NN.png) AND the hires
        # click-through (page-NN-hires.png) variants for the Astro
        # gallery (Issue #28).
        for src in sorted(tdir.glob("page-*.png")):
            shutil.copy(src, public_dir / src.name)


# ---------------------------------------------------------------------------
# sla_diff + visual_diff subprocess helpers
# ---------------------------------------------------------------------------

def _run_sla_diff_strict(tid: str, tdir: Path, meta: dict) -> int:
    """Run tools/sla_diff.py --strict against original_sla. Returns exit code."""
    original_rel = meta.get("original_sla", "")
    if not original_rel:
        print(f"[{tid}] skipping sla_diff — no original_sla in meta.yml", file=sys.stderr)
        return 0
    if not meta.get("sla_diff_strict", True):
        print(
            f"[{tid}] skipping strict sla_diff — meta.yml::sla_diff_strict=false "
            f"(template intentionally diverges from upstream; see issue #16)",
            file=sys.stderr,
        )
        return 0
    original_abs = (tdir / original_rel).resolve()
    template_sla = tdir / "template.sla"
    r = subprocess.run(
        [
            "python3", str(ROOT / "tools" / "sla_diff.py"),
            "--left", str(original_abs),
            "--right", str(template_sla),
            "--strict",
            "--allow-brand-extras",
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(
            f"[{tid}] sla_diff FAILED:\n{r.stdout}{r.stderr}",
            file=sys.stderr,
        )
    return r.returncode


def _run_visual_diff(tid: str, tdir: Path, args) -> int:
    """Run tools/visual_diff.py against baseline.pdf. Returns exit code (0 = pass or skip).

    When meta.yml::reference_sla is set, also runs a second diff lane comparing
    the DSL preview.pdf against the Scribus-imported reference SLA rendered to PDF.
    The second lane is informational only (P3) — its exit code does NOT propagate.
    """
    baseline = tdir / "baseline.pdf"
    diff_yml = tdir / "diff.yml"
    if not (baseline.exists() and diff_yml.exists()):
        print(f"[{tid}] visual_diff: SKIPPED (no baseline.pdf or diff.yml)")
        return 0
    template_sla = tdir / "template.sla"
    out_dir = ROOT / "build" / "validation" / tid
    out_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [
            "python3", str(ROOT / "tools" / "visual_diff.py"),
            str(template_sla),
            "--baseline", str(baseline),
            "--tolerance", str(diff_yml),
            "--dpi", "150",
            "--out", str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(
            f"[{tid}] visual_diff FAILED:\n{r.stdout}{r.stderr}",
            file=sys.stderr,
        )
    else:
        print(f"[{tid}] visual_diff (150dpi): PASS")

    # Print lane 1 summary from the written JSON.
    vd_json = out_dir / "visual_diff.json"
    lane1_pass, lane1_pcts = _summarise_diff_json(vd_json)
    _print_lane_summary(tid, "visual_diff  ", "(cross-engine vs baseline.pdf)", lane1_pcts, lane1_pass)

    # Lane 2: reference_sla diff (informational, P3 — does NOT affect return code).
    meta = _read_template_meta(tdir)
    _run_reference_diff_lane(tid, tdir, meta, out_dir)

    return r.returncode


def _summarise_diff_json(json_path: Path) -> tuple[bool, list[float]]:
    """Parse a visual_diff.json and return (overall_pass, [mismatch_pct_per_page])."""
    if not json_path.exists():
        return False, []
    try:
        import json
        data = json.loads(json_path.read_text(encoding="utf-8"))
        overall_pass = bool(data.get("pass", False))
        pcts = [float(p.get("mismatch_pct", 0.0)) for p in data.get("pages", [])]
        return overall_pass, pcts
    except Exception:
        return False, []


def _print_lane_summary(tid: str, lane_label: str, context: str,
                         pcts: list[float], overall_pass: bool) -> None:
    """Print a single-line lane summary in the canonical format."""
    verdict = "PASS" if overall_pass else "FAIL"
    if not pcts:
        print(f"[{tid}] {lane_label} {context}: n/a ({verdict})")
        return
    pct_parts = " ".join(f"p{i+1}={v:.2f}%" for i, v in enumerate(pcts))
    print(f"[{tid}] {lane_label} {context}: {pct_parts} ({verdict})")


def _run_reference_diff_lane(tid: str, tdir: Path, meta: dict, out_dir: Path) -> None:
    """Render reference_sla → PDF, then diff preview.pdf vs reference-scribus.pdf.

    Writes reference_diff/reference_diff.json (same schema as visual_diff.json).
    Errors are printed but never propagate — this lane is informational (P3).
    """
    import json
    import time

    ref_sla_rel = meta.get("reference_sla", "")
    if not ref_sla_rel:
        return

    ref_sla_abs = (tdir / ref_sla_rel).resolve()
    if not ref_sla_abs.exists():
        print(
            f"[{tid}] reference_diff: SKIPPED (reference_sla not found: {ref_sla_abs})",
            file=sys.stderr,
        )
        return

    ref_dir = out_dir / "reference_diff"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_pdf = out_dir / "reference-scribus.pdf"

    # Step 1: render the Scribus SLA to PDF.
    print(f"[{tid}] reference_diff: rendering reference SLA → reference-scribus.pdf …")
    t0 = time.monotonic()
    try:
        render_sla_to_pdf(ref_sla_abs, ref_pdf)
        elapsed = time.monotonic() - t0
        print(f"[{tid}] reference_diff: reference SLA rendered in {elapsed:.1f}s")
    except Exception as exc:
        print(
            f"[{tid}] reference_diff: FAILED to render reference SLA: {exc}",
            file=sys.stderr,
        )
        return

    # Step 2: rasterise both PDFs (preview.pdf = DSL output, reference-scribus.pdf).
    preview_pdf = tdir / "preview.pdf"
    if not preview_pdf.exists():
        print(
            f"[{tid}] reference_diff: SKIPPED (no preview.pdf — render must precede diff)",
            file=sys.stderr,
        )
        return

    dpi = 150
    try:
        ref_pages = rasterise(ref_pdf, ref_dir / "ref-page", dpi)
        dsl_pages = rasterise(preview_pdf, ref_dir / "dsl-page", dpi)
    except Exception as exc:
        print(f"[{tid}] reference_diff: rasterise failed: {exc}", file=sys.stderr)
        return

    if len(ref_pages) != len(dsl_pages):
        print(
            f"[{tid}] reference_diff: page count mismatch "
            f"(ref={len(ref_pages)}, dsl={len(dsl_pages)})",
            file=sys.stderr,
        )
        return

    # Step 3: compare pages.
    fuzz_pct = 2.0  # no template-specific tolerance for the reference lane
    results = []
    overall_pass = True
    for idx, (r_png, d_png) in enumerate(zip(ref_pages, dsl_pages)):
        diff_png = ref_dir / f"diff-page-{idx + 1:02d}.png"
        composite_png = ref_dir / f"composite-page-{idx + 1:02d}.png"
        try:
            mismatch, total = compare_pages(d_png, r_png, diff_png, fuzz_pct)
            montage_composite(r_png, d_png, diff_png, composite_png)
        except Exception as exc:
            print(f"[{tid}] reference_diff: compare page {idx+1} failed: {exc}", file=sys.stderr)
            overall_pass = False
            results.append({
                "page": idx,
                "mismatch_pixels": -1,
                "total_pixels": -1,
                "mismatch_pct": 100.0,
                "pass": False,
            })
            continue
        mismatch_pct = (mismatch / total * 100.0) if total else 0.0
        # Use same threshold as default visual_diff tolerance (1.0%).
        page_pass = mismatch_pct <= 1.0
        if not page_pass:
            overall_pass = False
        results.append({
            "page": idx,
            "mismatch_pixels": mismatch,
            "total_pixels": total,
            "mismatch_pct": round(mismatch_pct, 4),
            "pass": page_pass,
            "composite": str(composite_png.relative_to(ref_dir)),
            "delta_png": str(diff_png.relative_to(ref_dir)),
        })

    # Step 4: write reference_diff.json.
    summary = {
        "template_sla": str(tdir / "template.sla"),
        "reference_sla": str(ref_sla_abs),
        "baseline_pdf": str(ref_pdf),
        "dpi": dpi,
        "pass": overall_pass,
        "pages": results,
    }
    ref_json = ref_dir / "reference_diff.json"
    ref_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    pcts = [p["mismatch_pct"] for p in results]
    _print_lane_summary(tid, "reference_diff", "(same-engine vs reference.sla)", pcts, overall_pass)


# ---------------------------------------------------------------------------
# Per-template orchestration
# ---------------------------------------------------------------------------

def _select_render_source(template_dir: Path) -> Path:
    """Prefer template-preview.sla (gallery render) over template.sla.

    Production templates emit a separate preview-SLA (issue #13, D3) so the
    round-trip-stable template.sla stays clean. Gallery renders use the
    preview when present; SHA tracking and sla_diff still target template.sla.
    """
    preview = template_dir / "template-preview.sla"
    if preview.exists():
        return preview
    return template_dir / "template.sla"


def _orchestrate_single(tdir: Path, meta: dict, public_dir: Path, args) -> int:
    """Render a single-SLA template (postkarte, zeitung).

    Steps: build.py already called by _orchestrate_template. Here:
    render → scrub → rasterise → zero-pad → sla_diff → visual_diff → hash → mirror.
    """
    tid = meta["id"]
    template_sla = tdir / "template.sla"
    render_source = _select_render_source(tdir)
    preview_pdf = tdir / "preview.pdf"
    dpi = int(meta.get("preview_dpi", DEFAULT_DPI))

    print(f"[{tid}] rendering {render_source.name} → preview.pdf …")
    render_sla_to_pdf(render_source, preview_pdf)
    _scrub_pdf_metadata(preview_pdf)
    print(f"[{tid}] rasterising at {dpi} dpi (thumbnail) "
          f"+ {HIRES_DPI} dpi (hires) …")

    # Clean stale PNGs before rasterising (removes old single-digit relics too).
    for stale in list(tdir.glob("page-*.png")):
        stale.unlink()

    # Thumbnail pass.
    rasterise(preview_pdf, tdir / "page", dpi)
    _zero_pad_pngs(tdir, "page")
    # Hi-res pass (Issue #28). Renders into page-NN-hires.png. Same
    # zero-pad convention as the thumbnails.
    rasterise(preview_pdf, tdir / "hires", HIRES_DPI)
    _zero_pad_pngs(tdir, "hires")
    # Rename `hires-NN.png` → `page-NN-hires.png` for the Astro template's
    # naming convention (lookup by stripping `.png` and adding `-hires.png`).
    for src in sorted(tdir.glob("hires-*.png")):
        suffix = src.name[len("hires-"):]   # NN.png
        target = tdir / f"page-{suffix.replace('.png', '-hires.png')}"
        src.rename(target)

    rc = _run_sla_diff_strict(tid, tdir, meta)
    if rc != 0:
        return rc

    if not args.skip_visual_diff:
        rc = _run_visual_diff(tid, tdir, args)
        if rc != 0:
            return rc

    if not args.dry_run:
        h = _sha256_of(template_sla)
        _update_meta_hash(tdir / "meta.yml", h)
        _mirror_to_site_public(tdir, public_dir, family=False)

    # Count only thumbnails (exclude `*-hires.png` so the page total
    # reflects the document's actual page count, not 2× page count).
    pngs = sorted(p for p in tdir.glob("page-*.png")
                  if not p.stem.endswith("-hires"))
    hires = sorted(tdir.glob("page-*-hires.png"))
    print(
        f"[{tid}] OK — {len(pngs)} page(s) at {dpi} dpi (thumbnail) "
        f"+ {len(hires)} hires at {HIRES_DPI} dpi"
    )
    return 0


def _orchestrate_family(tdir: Path, meta: dict, public_dir: Path, args) -> int:
    """Render a family template (plakat per-size: a0, a1, a2, a3).

    Each size SLA (committed input) is rendered to its own PDF, rasterised
    to a single page PNG, and hashed. Per-size hashes are recorded as a dict
    in meta.yml::previews_for_sla.

    Note: per-size SLAs (a0.sla…a3.sla) are committed inputs — NOT regenerated
    by build.py. The pipeline treats them as canonical and renders/copies them
    unchanged (RESEARCH.md §Potential Conflicts).
    """
    tid = meta["id"]
    sizes = meta.get("sizes", [])
    if not sizes:
        print(f"[{tid}] ERROR: family template has no sizes in meta.yml", file=sys.stderr)
        return 1

    dpi = int(meta.get("preview_dpi", DEFAULT_DPI))

    # Clean stale per-size PNGs (old hand-named relics + current names).
    for pattern in ("*-preview-*.png", "*-page-*.png"):
        for stale in list(tdir.glob(pattern)):
            stale.unlink()

    hashes: dict[str, str] = {}
    overall_rc = 0

    for size in sizes:
        code = size["code"]
        sla = tdir / f"{code}.sla"
        pdf = tdir / f"{code}.pdf"

        if not sla.exists():
            print(f"[{tid}/{code}] ERROR: {sla} not found", file=sys.stderr)
            overall_rc = 1
            continue

        print(f"[{tid}/{code}] rendering {code}.sla → {code}.pdf …")
        render_sla_to_pdf(sla, pdf)
        _scrub_pdf_metadata(pdf)
        print(f"[{tid}/{code}] rasterising at {dpi} dpi …")
        rasterise(pdf, tdir / f"{code}-page", dpi)
        _zero_pad_pngs(tdir, f"{code}-page")
        hashes[code] = _sha256_of(sla)

    if overall_rc != 0:
        return overall_rc

    # sla_diff and visual_diff fire against template.sla (the DSL-built aggregate
    # that covers all sizes structurally — see RESEARCH.md §Potential Conflicts).
    rc = _run_sla_diff_strict(tid, tdir, meta)
    if rc != 0:
        return rc

    if not args.skip_visual_diff:
        rc = _run_visual_diff(tid, tdir, args)
        if rc != 0:
            return rc

    if not args.dry_run:
        _update_meta_hash(tdir / "meta.yml", hashes)
        _mirror_to_site_public(tdir, public_dir, family=True)

    for size in sizes:
        code = size["code"]
        pngs = sorted(tdir.glob(f"{code}-page-*.png"))
        print(f"[{tid}/{code}] OK — {len(pngs)} page(s) at {dpi} dpi")
    return 0


def _orchestrate_template(tdir: Path, args) -> int:
    """Orchestrate one template directory end-to-end.

    1. Read meta and determine family vs single.
    2. Run build.py to regenerate template.sla.
    3. Dispatch to _orchestrate_single or _orchestrate_family.
    """
    meta = _read_template_meta(tdir)
    tid = meta["id"]
    is_family = meta.get("type") == "family"

    site_public_dir = ROOT / "site" / "public" / "templates" / tid
    site_public_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: regenerate template.sla from build.py.
    build_py = tdir / "build.py"
    if build_py.exists():
        print(f"[{tid}] running build.py …")
        env = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
        }
        r = subprocess.run(
            ["python3", str(build_py)],
            check=False,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(
                f"[{tid}] build.py FAILED:\n{r.stdout}{r.stderr}",
                file=sys.stderr,
            )
            return r.returncode

    if is_family:
        return _orchestrate_family(tdir, meta, site_public_dir, args)
    else:
        return _orchestrate_single(tdir, meta, site_public_dir, args)


# ---------------------------------------------------------------------------
# main() — CLI entry point
# ---------------------------------------------------------------------------

def _run_audit(tdir: Path, meta: dict, args) -> tuple[int, str]:
    """Run A1 (idml_inventory) + A2 (baseline_text_audit) + A3 (baseline_image_audit).

    Returns (audit_issue_count, summary_line).
    Reports are written to build/validation/<slug>/{inventory,text_audit,image_audit}.yml.

    Audit failure does NOT block the render — just surfaces the reports.
    When --audit-strict is set the caller uses the issue count to set exit code.
    """
    tid = meta["id"]
    out_dir = ROOT / "build" / "validation" / tid
    out_dir.mkdir(parents=True, exist_ok=True)

    issue_parts: list[str] = []

    # A1: IDML inventory (requires an IDML source)
    idml_source = None
    for key in ("idml_source", "original_idml"):
        val = meta.get(key, "")
        if val:
            candidate = (tdir / val).resolve()
            if candidate.exists():
                idml_source = candidate
                break
    # Also try a common originals path pattern
    if idml_source is None:
        # Search originals/ for an .idml matching the template's source dir
        for candidate in sorted((ROOT / "originals").rglob("*.idml")):
            idml_source = candidate
            break

    inventory_path = out_dir / "inventory.yml"
    if idml_source is not None and (tdir / "build.py").exists():
        try:
            from idml_inventory import run_inventory, _yaml_dump as _inv_yaml
            report = run_inventory(idml_source, tdir / "build.py", template=tid)
            inventory_path.write_text(_inv_yaml(report), encoding="utf-8")
            # Count dropped elements across all spreads
            dropped = sum(
                len(s.get("elements_dropped", []))
                for s in report.get("spreads", [])
            )
            if dropped:
                issue_parts.append(f"{dropped} dropped element(s)")
        except Exception as exc:
            print(f"[{tid}] audit A1 (inventory) error: {exc}", file=sys.stderr)
    else:
        print(
            f"[{tid}] audit A1 (inventory): skipped (no IDML source found)",
            file=sys.stderr,
        )

    # A2: baseline text audit
    text_audit_path = out_dir / "text_audit.yml"
    baseline = tdir / "baseline.pdf"
    build_py = tdir / "build.py"
    if baseline.exists() and build_py.exists():
        try:
            from baseline_text_audit import run_text_audit, _yaml_dump as _txt_yaml
            report = run_text_audit(baseline, build_py, template=tid)
            text_audit_path.write_text(_txt_yaml(report), encoding="utf-8")
            unmatched = sum(
                len(p.get("lines_unmatched", []))
                for p in report.get("pages", [])
            )
            if unmatched:
                issue_parts.append(f"{unmatched} unmatched text line(s)")
        except Exception as exc:
            print(f"[{tid}] audit A2 (text) error: {exc}", file=sys.stderr)
    else:
        print(
            f"[{tid}] audit A2 (text): skipped (no baseline.pdf or build.py)",
            file=sys.stderr,
        )

    # A3: baseline image audit
    image_audit_path = out_dir / "image_audit.yml"
    if baseline.exists() and build_py.exists():
        try:
            from baseline_image_audit import run_image_audit, _yaml_dump as _img_yaml
            report = run_image_audit(baseline, build_py, template=tid)
            image_audit_path.write_text(_img_yaml(report), encoding="utf-8")
            vector_delta_total = sum(
                p.get("vector_paths", {}).get("delta", 0)
                for p in report.get("pages", [])
                if p.get("vector_paths", {}).get("delta", 0) > 0
            )
            strip_count = len(report.get("composite_strips", []))
            if vector_delta_total:
                issue_parts.append(f"{vector_delta_total} vector-path delta")
            if strip_count:
                issue_parts.append(f"{strip_count} composite-strip issue(s)")
        except Exception as exc:
            print(f"[{tid}] audit A3 (image) error: {exc}", file=sys.stderr)
    else:
        print(
            f"[{tid}] audit A3 (image): skipped (no baseline.pdf or build.py)",
            file=sys.stderr,
        )

    # Phase D4: 3-way Venn audit (IDML / Scribus-SLA / build.py)
    # Requires: inventory.yml (already written above) + sla_inventory.yml (from reference_sla)
    three_way_path = out_dir / "three_way_audit.yml"
    sla_inventory_path = out_dir / "sla_inventory.yml"
    reference_sla_rel = meta.get("reference_sla", "")
    if reference_sla_rel:
        reference_sla_abs = (tdir / reference_sla_rel).resolve()
        if not reference_sla_abs.exists():
            print(
                f"[{tid}] audit D4 (three_way): skipped (reference_sla not found at {reference_sla_abs})",
                file=sys.stderr,
            )
        elif not inventory_path.exists():
            print(
                f"[{tid}] audit D4 (three_way): skipped (inventory.yml not produced by A1)",
                file=sys.stderr,
            )
        elif not (tdir / "build.py").exists():
            print(
                f"[{tid}] audit D4 (three_way): skipped (no build.py)",
                file=sys.stderr,
            )
        else:
            try:
                from sla_inventory import run_sla_inventory, _yaml_dump as _sla_yaml
                from three_way_audit import run_three_way_audit, _yaml_dump as _twa_yaml

                # Step 1: produce sla_inventory.yml if absent or stale.
                sla_report = run_sla_inventory(reference_sla_abs, template=tid)
                sla_inventory_path.write_text(_sla_yaml(sla_report), encoding="utf-8")

                # Step 2: run 3-way audit.
                twa_report = run_three_way_audit(
                    inventory_path,
                    sla_inventory_path,
                    tdir / "build.py",
                    template=tid,
                )
                three_way_path.write_text(_twa_yaml(twa_report), encoding="utf-8")

                s = twa_report["summary"]
                twa_line = (
                    f"[{tid}] three_way_audit: "
                    f"{s['converter_bug']} converter_bug, "
                    f"{s['geometry_drift']} geometry_drift, "
                    f"{s['suspicious_emit']} suspicious_emit"
                )
                print(twa_line)
                if s["converter_bug"] or s["suspicious_emit"]:
                    twa_line += " → REVIEW"
                    issue_parts.append(
                        f"{s['converter_bug']} converter_bug / {s['suspicious_emit']} suspicious_emit"
                    )
            except Exception as exc:
                print(f"[{tid}] audit D4 (three_way) error: {exc}", file=sys.stderr)
    else:
        print(
            f"[{tid}] audit D4 (three_way): skipped (no reference_sla in meta.yml)",
            file=sys.stderr,
        )

    # Phase D6: pdffonts font audit (preview vs baseline embedded font sets).
    preview_pdf = tdir / "preview.pdf"
    font_audit_path = out_dir / "font_audit.yml"
    if preview_pdf.exists() and baseline.exists():
        try:
            from font_audit import run_font_audit, _yaml_dump as _fa_yaml
            fa_report = run_font_audit(preview_pdf, baseline, template=tid)
            font_audit_path.write_text(_fa_yaml(fa_report), encoding="utf-8")
            missing = fa_report.get("missing_in_preview", [])
            fa_ok = fa_report.get("ok", False)
            if missing:
                fa_line = (
                    f"[{tid}] font_audit: {len(missing)} missing variant(s) "
                    f"({', '.join(missing)}) → FAIL"
                )
                print(fa_line)
                issue_parts.append(f"{len(missing)} missing font variant(s)")
            else:
                print(f"[{tid}] font_audit: OK")
        except Exception as exc:
            print(f"[{tid}] audit D6 (font_audit) error: {exc}", file=sys.stderr)
    else:
        print(
            f"[{tid}] audit D6 (font_audit): skipped (no preview.pdf or baseline.pdf)",
            file=sys.stderr,
        )

    if issue_parts:
        summary = f"[{tid}] audit: {', '.join(issue_parts)} → REVIEW REQUIRED"
    else:
        summary = f"[{tid}] audit: clean"

    return len(issue_parts), summary


def main(argv=None) -> int:
    """Entry point for bin/render-gallery."""
    parser = argparse.ArgumentParser(
        prog="render-gallery",
        description=(
            "Local render pipeline: rebuild template.sla, render PDF, rasterise PNGs,\n"
            "run sla_diff + visual_diff, update meta.yml hash, mirror to site/public/.\n\n"
            "Run from the dev container (brand fonts must be installed).\n"
            "See shared/fonts/README.md and docs/render-fidelity.md."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "template_id",
        nargs="?",
        default=None,
        help="Render a single template by ID (e.g. postkarte-a6-kampagne). "
             "Omit to render all templates.",
    )
    parser.add_argument(
        "--skip-visual-diff",
        action="store_true",
        help="Skip the visual_diff step (faster iteration; sla_diff still runs).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and validate but do NOT write meta.yml hash or mirror to site/public/.",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help=(
            "After render+visual_diff, run A1 (idml_inventory) + A2 (baseline_text_audit) "
            "+ A3 (baseline_image_audit) and write reports to "
            "build/validation/<slug>/{inventory,text_audit,image_audit}.yml. "
            "Prints a per-template audit summary. Informational only (use --audit-strict "
            "to fail on audit issues)."
        ),
    )
    parser.add_argument(
        "--audit-strict",
        action="store_true",
        help=(
            "Same as --audit but exits non-zero if any audit issues are found. "
            "Implies --audit. Intended for CI."
        ),
    )

    args = parser.parse_args(argv)
    # --audit-strict implies --audit
    if args.audit_strict:
        args.audit = True

    # Preflight: brand fonts.
    _verify_brand_fonts()

    templates_dir = ROOT / "templates"
    if args.template_id is not None:
        tdir = templates_dir / args.template_id
        if not tdir.is_dir():
            print(
                f"no such template directory: {tdir}", file=sys.stderr
            )
            return 1
        candidates = [tdir]
    else:
        candidates = sorted(
            d for d in templates_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        )

    # Filter to only renderable directories. A template is renderable if its
    # meta.yml has either:
    #   - `original_sla:` — the round-trip path (build → diff against original)
    #   - `previews_for_sla:` — DSL-only templates that have no original to
    #     round-trip against, but still track a SHA pin for stale-check.
    # Either qualifies; templates without both (smoke fixtures, scaffolding
    # stubs, etc.) are skipped.
    work = []
    for tdir in candidates:
        meta_path = tdir / "meta.yml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        if not _is_renderable(meta):
            continue
        work.append(tdir)

    if not work:
        print("No renderable templates found (need original_sla or previews_for_sla).", file=sys.stderr)
        return 1

    results: dict[str, int] = {}
    audit_summaries: list[str] = []
    audit_issue_count_total = 0
    for tdir in work:
        tid = tdir.name
        meta = yaml.safe_load((tdir / "meta.yml").read_text(encoding="utf-8"))
        try:
            rc = _orchestrate_template(tdir, args)
        except Exception as exc:
            print(f"[{tid}] EXCEPTION: {exc}", file=sys.stderr)
            rc = 1
        results[tid] = rc

        # Run audit AFTER render (non-blocking by default).
        if getattr(args, "audit", False):
            try:
                n_issues, summary = _run_audit(tdir, meta, args)
                print(summary)
                audit_summaries.append(summary)
                audit_issue_count_total += n_issues
            except Exception as exc:
                print(f"[{tid}] audit EXCEPTION: {exc}", file=sys.stderr)

    # Summary.
    sep = "=" * 64
    print(f"\n{sep}")
    label = "render-gallery summary"
    if args.dry_run:
        label += " (dry-run — no files written)"
    print(f"{label}: {len(results)} template(s)")
    for tid, rc in results.items():
        status = "OK" if rc == 0 else "FAIL"
        print(f"  {tid:<42} {status}")
    if getattr(args, "audit", False) and audit_summaries:
        print()
        print("Audit summaries:")
        for s in audit_summaries:
            print(f"  {s}")
    print(sep)

    overall = 0 if all(rc == 0 for rc in results.values()) else 1
    # --audit-strict: fail if any audit issues found
    if getattr(args, "audit_strict", False) and audit_issue_count_total > 0:
        print(
            f"AUDIT STRICT: {audit_issue_count_total} audit issue category(ies) found "
            f"across {len(work)} template(s) — exiting non-zero.",
            file=sys.stderr,
        )
        overall = 1
    return overall


if __name__ == "__main__":
    sys.exit(main())
