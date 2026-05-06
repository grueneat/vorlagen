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

from visual_diff import render_sla_to_pdf, rasterise  # noqa: E402

DEFAULT_DPI = 50

# Fixed replacement values — all length-preserving (PDF spec requires fixed widths).
EPOCH_DATE = b"D:20000101000000Z"   # 16 bytes; same as D:YYYYMMDDhhmmssZ
FIXED_PDF_ID = b"00000000000000000000000000000000"  # 32 hex chars



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
    original_abs = (tdir / original_rel).resolve()
    template_sla = tdir / "template.sla"
    r = subprocess.run(
        [
            "python3", str(ROOT / "tools" / "sla_diff.py"),
            "--left", str(original_abs),
            "--right", str(template_sla),
            "--strict",
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
    """Run tools/visual_diff.py against baseline.pdf. Returns exit code (0 = pass or skip)."""
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
    return r.returncode


# ---------------------------------------------------------------------------
# Per-template orchestration
# ---------------------------------------------------------------------------

def _orchestrate_single(tdir: Path, meta: dict, public_dir: Path, args) -> int:
    """Render a single-SLA template (postkarte, zeitung).

    Steps: build.py already called by _orchestrate_template. Here:
    render → scrub → rasterise → zero-pad → sla_diff → visual_diff → hash → mirror.
    """
    tid = meta["id"]
    template_sla = tdir / "template.sla"
    preview_pdf = tdir / "preview.pdf"
    dpi = int(meta.get("preview_dpi", DEFAULT_DPI))

    print(f"[{tid}] rendering template.sla → preview.pdf …")
    render_sla_to_pdf(template_sla, preview_pdf)
    _scrub_pdf_metadata(preview_pdf)
    print(f"[{tid}] rasterising at {dpi} dpi …")

    # Clean stale PNGs before rasterising (removes old single-digit relics too).
    for stale in list(tdir.glob("page-*.png")):
        stale.unlink()

    rasterise(preview_pdf, tdir / "page", dpi)
    _zero_pad_pngs(tdir, "page")

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

    pngs = sorted(tdir.glob("page-*.png"))
    print(f"[{tid}] OK — {len(pngs)} page(s) at {dpi} dpi")
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

    args = parser.parse_args(argv)

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

    # Filter to only directories with meta.yml::original_sla (skip smoke, etc.).
    work = []
    for tdir in candidates:
        meta_path = tdir / "meta.yml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        if not meta.get("original_sla"):
            continue
        work.append(tdir)

    if not work:
        print("No templates with original_sla found.", file=sys.stderr)
        return 1

    results: dict[str, int] = {}
    for tdir in work:
        tid = tdir.name
        try:
            rc = _orchestrate_template(tdir, args)
        except Exception as exc:
            print(f"[{tid}] EXCEPTION: {exc}", file=sys.stderr)
            rc = 1
        results[tid] = rc

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
    print(sep)

    overall = 0 if all(rc == 0 for rc in results.values()) else 1
    return overall


if __name__ == "__main__":
    sys.exit(main())
