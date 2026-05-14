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

Oracle stack: IDML (authoring truth) + baseline.pdf (convergence target).
No Scribus-imported SLA is used — the reference_sla tooling was removed
2026-05-12 after empirical measurement showed our converter already beats
Scribus's importer on visual_diff vs baseline.pdf.
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

def _run_global_sop_gates() -> None:
    """Run repo-wide SOP gates that don't take a template id.

    These are CI-only today (.github/workflows/ci.yml::"SOP gates" step).
    Running them locally before any rendering keeps the pipeline honest:
    if a developer broke an SOP rule (sop_lint), drifted from inject.yml
    (lint_inject_consistency across all templates), or grew brand
    overrides past the merge-base limit (check_overrides_growth), they
    learn now instead of after pushing.

    Hard fail on sop_lint + check_no_absolute_paths_in_sla (those are
    invariants the project never wants to ship). Warn for
    check_overrides_growth (matches CI's transitional ``|| true``).
    """
    gates: list[tuple[str, list[str], bool]] = [
        ("sop_lint", [sys.executable, str(ROOT / "tools" / "sop_lint.py")], True),
        ("check_no_absolute_paths_in_sla",
         [sys.executable, str(ROOT / "tools" / "check_no_absolute_paths_in_sla.py")],
         True),
        # check_overrides_growth needs a base-ref. Local dev usually
        # works against origin/main but the fetch may be shallow; mirror
        # CI's ``|| true`` semantics — informational only.
        ("check_overrides_growth",
         [sys.executable, str(ROOT / "tools" / "check_overrides_growth.py"),
          "--base-ref", "origin/main"],
         False),
    ]
    for name, cmd, hard_fail in gates:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        if r.returncode == 0:
            print(f"[global] {name}: OK")
        else:
            tag = "FAIL" if hard_fail else "WARN"
            sys.stderr.write(
                f"[global] {name}: {tag} "
                f"(exit={r.returncode})\n"
                f"{r.stdout}{r.stderr}\n"
            )
            if hard_fail:
                sys.stderr.write(
                    f"[global] {name} is a hard SOP gate — "
                    "fix the violation before re-rendering.\n"
                )
                raise SystemExit(2)


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

    Always emits ``build/validation/<tid>/diff-page-NN.png`` +
    ``composite-page-NN.png`` so the operator can inspect drift after every
    render. When ``--visual-diff-warning-only`` is set (the /idml-tune
    Stage-2 default), a non-zero exit is downgraded to a warning so the
    audit chain still gets a chance to run — the per-region audits are the
    authoritative drift gate during tuning iterations.
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
        msg = f"[{tid}] visual_diff DRIFT (diff PNGs in build/validation/{tid}/):\n{r.stdout}{r.stderr}"
        if getattr(args, "visual_diff_warning_only", False):
            print(msg, file=sys.stderr)
            print(f"[{tid}] visual_diff: WARNING (warning-only mode; continuing)",
                  file=sys.stderr)
            return 0
        print(msg, file=sys.stderr)
    else:
        print(f"[{tid}] visual_diff (150dpi): PASS")

    return r.returncode


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
        # meta.yml::previews_for_sla is already updated in
        # _orchestrate_template (F-020) right after build.py succeeds.
        # No need to recompute here.
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
    3. Auto-update meta.yml::previews_for_sla so the pin always tracks the
       just-emitted SLA (F-020). Done immediately after build.py succeeds —
       before any diff/audit phase — so the hash stays in sync even when
       downstream phases (visual_diff, audits) flag a regression. This
       removes the manual "compute sha256 + edit meta.yml" step that was
       easy to forget.
    4. Dispatch to _orchestrate_single or _orchestrate_family.
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

    # F-020: auto-update meta.yml::previews_for_sla immediately after the
    # SLA is (re)written by build.py. For single templates the pin tracks
    # template.sla; for family templates each per-size SLA is committed
    # and unchanged by build.py — those hashes still update inside
    # _orchestrate_family via the existing per-size loop. We skip family
    # here because the per-size SLAs may not all exist until that loop.
    if not getattr(args, "dry_run", False) and not is_family:
        template_sla = tdir / "template.sla"
        if template_sla.exists():
            try:
                h = _sha256_of(template_sla)
                _update_meta_hash(tdir / "meta.yml", h)
            except OSError as exc:
                print(
                    f"[{tid}] meta.yml hash auto-update skipped: {exc}",
                    file=sys.stderr,
                )

    if is_family:
        return _orchestrate_family(tdir, meta, site_public_dir, args)
    else:
        return _orchestrate_single(tdir, meta, site_public_dir, args)


# ---------------------------------------------------------------------------
# main() — CLI entry point
# ---------------------------------------------------------------------------

def _record_phase_error(
    phase_errors: dict[str, str],
    phase_key: str,
    label: str,
    exc: BaseException,
    tid: str,
) -> None:
    """Record an audit-phase exception in BOTH the human log AND the
    structured `phase_errors` dict that gets surfaced in preflight.yml.

    Without this dict, an exception during e.g. line_spacing_pixel_audit
    only prints to stderr — the rollup looks 'clean' to anyone reading
    preflight.yml, masking the failure. Audit-reliability review item 2.
    """
    msg = f"{type(exc).__name__}: {exc}"
    print(f"[{tid}] audit {label} error: {msg}", file=sys.stderr)
    phase_errors[phase_key] = msg


def _run_audit(tdir: Path, meta: dict, args) -> tuple[int, str]:
    """Run A1 (idml_inventory) + A2 (baseline_text_audit) + A3 (baseline_image_audit).

    Returns (audit_issue_count, summary_line).
    Reports are written to build/validation/<slug>/{inventory,text_audit,image_audit}.yml.

    Audit failure does NOT block the render — just surfaces the reports.
    When --audit-strict is set the caller uses the issue count to set exit code.

    Per-phase exceptions are captured into ``phase_errors`` (audit-
    reliability review item 2) so the final preflight.yml carries an
    `errors:` section instead of silently dropping the failure on the
    terminal log.
    """
    tid = meta["id"]
    out_dir = ROOT / "build" / "validation" / tid
    out_dir.mkdir(parents=True, exist_ok=True)

    issue_parts: list[str] = []
    phase_errors: dict[str, str] = {}

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

    # Phase E (Issue #38 Task 2): asset_extraction_audit runs FIRST so missing
    # links / composite-AI strips fail fast before downstream audits.
    asset_audit_path = out_dir / "asset_audit.yml"
    if idml_source is not None:
        # Locate the manifest. Convention: shared/assets/<slug>/links_export.yml.
        manifest_candidates = [
            ROOT / "shared" / "assets" / tid / "links_export.yml",
            idml_source.parent / "links_export.yml",
        ]
        manifest_path = next(
            (p for p in manifest_candidates if p.exists()), None
        )
        allow_composite_ai = bool(getattr(args, "allow_composite_ai", False))
        if manifest_path is not None:
            try:
                from asset_extraction_audit import audit as run_asset_audit
                report = run_asset_audit(
                    slug=tid,
                    idml_path=idml_source,
                    links_export_yml=manifest_path,
                    repo_root=ROOT,
                    allow_composite_ai=allow_composite_ai,
                    out_dir=out_dir,
                )
                if not report["ok"]:
                    issue_parts.append(
                        f"{len(report.get('links_missing', []))} missing link(s), "
                        f"{len(report.get('links_unconverted', []))} unconverted, "
                        f"{len(report.get('composite_ai_detected', []))} composite-AI"
                    )
                    print(
                        f"[{tid}] asset_extraction_audit: FAIL "
                        f"({len(report.get('links_missing', []))} missing, "
                        f"{len(report.get('links_unconverted', []))} unconverted, "
                        f"{len(report.get('composite_ai_detected', []))} composite-AI)",
                        file=sys.stderr,
                    )
                else:
                    print(f"[{tid}] asset_extraction_audit: OK")
            except Exception as exc:
                _record_phase_error(
                    phase_errors, "asset_extraction", "asset_extraction_audit",
                    exc, tid,
                )
        else:
            print(
                f"[{tid}] asset_extraction_audit: skipped "
                f"(no links_export.yml at shared/assets/{tid}/ or "
                f"alongside IDML)",
                file=sys.stderr,
            )
    else:
        print(
            f"[{tid}] asset_extraction_audit: skipped (no IDML source)",
            file=sys.stderr,
        )

    # Issue #39 Phase B — asset_policy audit (post-extraction, pre-A1).
    # Hard-fails on missing policy, shipped:-non-empty, or coverage drift.
    # Silent-skip when shared/assets/<slug>/ doesn't exist (8 of 9 templates today).
    try:
        from asset_policy_audit import run_asset_policy_audit
        policy_report = run_asset_policy_audit(
            tid, root=ROOT, out_dir=out_dir,
        )
        if policy_report.get("ok"):
            if policy_report.get("skipped"):
                print(
                    f"[{tid}] asset_policy_audit: skipped "
                    f"({policy_report.get('reason', 'no asset dir')})"
                )
            else:
                print(f"[{tid}] asset_policy_audit: OK")
        else:
            issue = policy_report.get("issue", "unknown")
            issue_parts.append(f"asset_policy: {issue}")
            print(
                f"[{tid}] asset_policy_audit: FAIL ({issue}): "
                f"{policy_report.get('message', '')}",
                file=sys.stderr,
            )
    except ValueError as exc:
        issue_parts.append(f"asset_policy: schema-error")
        print(
            f"[{tid}] asset_policy_audit: schema error: {exc}",
            file=sys.stderr,
        )

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
            _record_phase_error(
                phase_errors, "inventory", "A1 (inventory)", exc, tid,
            )
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
            _record_phase_error(
                phase_errors, "text_audit", "A2 (text)", exc, tid,
            )
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
            _record_phase_error(
                phase_errors, "image_audit", "A3 (image)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit A3 (image): skipped (no baseline.pdf or build.py)",
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
            _record_phase_error(
                phase_errors, "font_audit", "D6 (font_audit)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit D6 (font_audit): skipped (no preview.pdf or baseline.pdf)",
            file=sys.stderr,
        )

    # Phase D7: text presence audit (preview.pdf vs baseline.pdf).
    # Catches words emitted to Scribus but suppressed at render time
    # (frame clipping, off-page, color-on-color, hidden layer, etc.).
    text_render_audit_path = out_dir / "text_render_audit.yml"
    if preview_pdf.exists() and baseline.exists():
        try:
            from text_render_audit import run_text_render_audit, _yaml_dump as _tra_yaml
            tra_report = run_text_render_audit(preview_pdf, baseline, template=tid)
            text_render_audit_path.write_text(_tra_yaml(tra_report), encoding="utf-8")
            if not tra_report["ok"]:
                n_missing = sum(tra_report["missing_in_preview"].values())
                n_unique = len(tra_report["missing_in_preview"])
                print(
                    f"[{tid}] text_render_audit: {n_unique} unique words missing "
                    f"({n_missing} occurrences) — silent suppression → FAIL",
                    file=sys.stderr,
                )
                issue_parts.append(f"{n_unique} word(s) missing in render")
            else:
                print(f"[{tid}] text_render_audit: OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "text_render_audit",
                "D7 (text_render_audit)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit D7 (text_render_audit): skipped (no preview.pdf or baseline.pdf)",
            file=sys.stderr,
        )

    # Phase D8: text position audit (per-word bounding-box drift).
    # Catches words rendered but mis-positioned (alignment drift, group-transform
    # gaps, off-by-margin bugs). Threshold: 2.0pt ≈ 0.7mm.
    text_position_audit_path = out_dir / "text_position_audit.yml"
    if preview_pdf.exists() and baseline.exists():
        try:
            from text_position_audit import run_text_position_audit, _yaml_dump as _tpa_yaml
            tpa_report = run_text_position_audit(preview_pdf, baseline, template=tid)
            text_position_audit_path.write_text(_tpa_yaml(tpa_report), encoding="utf-8")
            if not tpa_report["ok"]:
                print(
                    f"[{tid}] text_position_audit: "
                    f"{tpa_report['large_deltas_count']} word(s) drifted "
                    f"> {tpa_report['threshold_pt']}pt",
                    file=sys.stderr,
                )
                issue_parts.append(
                    f"{tpa_report['large_deltas_count']} word(s) with position drift"
                )
            else:
                print(f"[{tid}] text_position_audit: OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "text_position_audit",
                "D8 (text_position_audit)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit D8 (text_position_audit): skipped (no preview.pdf or baseline.pdf)",
            file=sys.stderr,
        )

    # Phase F: run_style_audit — per-Run font/size/color fidelity.
    # Catches wrong font assigned to a Run (e.g. Gotham where Vollkorn was expected),
    # wrong PointSize (fractional rounding artifacts), wrong color (bad brand mapping).
    # D6 only checks embedding; D7 only checks presence; F checks per-word style.
    run_style_audit_path = out_dir / "run_style_audit.yml"
    if preview_pdf.exists() and baseline.exists():
        try:
            from run_style_audit import run_style_audit as _rsa_run
            from run_style_audit import _yaml_dump as _rsa_yaml
            # #37 P1 task 3: pass pdftotext word counts from D7 (if available)
            # so run_style_audit can surface engine-disagreement warnings.
            tra_counts: dict | None = None
            if text_render_audit_path.exists():
                try:
                    import yaml as _yaml_mod
                    tra_loaded = _yaml_mod.safe_load(
                        text_render_audit_path.read_text(encoding="utf-8")
                    ) or {}
                    tra_counts = {
                        "baseline": int(tra_loaded.get("baseline_word_count", 0) or 0),
                        "preview": int(tra_loaded.get("preview_word_count", 0) or 0),
                    }
                except Exception:
                    tra_counts = None
            rsa_report = _rsa_run(
                preview_pdf, baseline, template=tid,
                text_render_audit_counts=tra_counts,
            )
            run_style_audit_path.write_text(_rsa_yaml(rsa_report), encoding="utf-8")
            large = sum(1 for d in rsa_report["style_drifts"] if d["severity"] == "large")
            small = sum(1 for d in rsa_report["style_drifts"] if d["severity"] == "small")
            suppressed = rsa_report.get("suppressed_common_word_drifts_count", 0)
            if large:
                print(
                    f"[{tid}] run_style_audit: {large} large style drifts, "
                    f"{small} small drifts → REVIEW"
                )
                issue_parts.append(f"{large} word(s) with large style drift")
            elif small:
                print(
                    f"[{tid}] run_style_audit: 0 large drifts, {small} small drifts "
                    f"(ICC/rounding, suppressed={suppressed})"
                )
            else:
                print(f"[{tid}] run_style_audit: OK")
            # Surface text-extraction-engine disagreement (Issue #37 P1 task 3).
            eed = rsa_report.get("extraction_engine_disagreement")
            if eed and eed.get("warn"):
                print(
                    f"[{tid}] run_style_audit: extraction engines disagree "
                    f"({eed['preview_pdftotext']} vs "
                    f"{eed['preview_pdfplumber']} preview words; "
                    f"{eed['baseline_pdftotext']} vs "
                    f"{eed['baseline_pdfplumber']} baseline words)",
                    file=sys.stderr,
                )
                issue_parts.append(
                    f"text extraction engines disagree "
                    f"({eed['preview_pdftotext']} vs "
                    f"{eed['preview_pdfplumber']} preview words)"
                )
        except Exception as exc:
            _record_phase_error(
                phase_errors, "run_style_audit",
                "F (run_style_audit)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit F (run_style_audit): skipped (no preview.pdf or baseline.pdf)",
            file=sys.stderr,
        )

    # Phase E2: line_spacing_audit — per-TextFrame baseline-to-baseline drift.
    # F-017: DEPRECATED as a primary signal. E2 still runs (back-compat,
    # trend-watching) but its drift count is NO LONGER appended to
    # issue_parts. Authoritative line-spacing signal is E4
    # (line_spacing_pixel_audit) which measures pixel-level ink-top.
    line_spacing_audit_path = out_dir / "line_spacing_audit.yml"
    if preview_pdf.exists() and baseline.exists() and build_py.exists():
        try:
            from line_spacing_audit import (
                run_line_spacing_audit as _lsa_run,
                _yaml_dump as _lsa_yaml,
            )
            lsa_report = _lsa_run(preview_pdf, baseline, build_py, template=tid)
            line_spacing_audit_path.write_text(
                _lsa_yaml(lsa_report), encoding="utf-8",
            )
            if not lsa_report["ok"]:
                # F-017: print informational note only — do NOT append to
                # issue_parts. The E4 pixel audit is the canonical signal.
                print(
                    f"[{tid}] line_spacing_audit (E2, informational): "
                    f"{lsa_report['line_spacing_drift_count']} frame(s) with "
                    f"|delta| > {lsa_report['threshold_pt']}pt — "
                    f"see line_spacing_pixel_audit (E4) for the authoritative "
                    f"per-frame signal",
                    file=sys.stderr,
                )
            else:
                print(f"[{tid}] line_spacing_audit (E2, informational): OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "line_spacing_audit",
                "E2 (line_spacing_audit)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit E2 (line_spacing_audit): skipped "
            "(no preview.pdf, baseline.pdf, or build.py)",
            file=sys.stderr,
        )

    # Phase E3: line_spacing_full_audit — authored-vs-emitted-vs-rendered
    # per-paragraph table. Catches converter bugs (e.g. <para> emits
    # LINESPMode=1 while <trail> emits LINESPMode=2 + LINESP=X — issue #40
    # follow-up) that the rendered-PDF-only E2 audit can miss when both
    # baseline and preview drift in the same direction.
    line_spacing_full_path = out_dir / "line_spacing_full_audit.yml"
    line_spacing_full_md = out_dir / "line_spacing_full_audit.md"
    if build_py.exists() and (out_dir / "..").resolve().parent.exists():
        try:
            from line_spacing_full_audit import main as _lsfa_main
            slug = tid
            originals_dir = Path("/workspace/originals")
            templates_dir = Path("/workspace/templates")
            _lsfa_main([
                "--slug", slug,
                "--templates-dir", str(templates_dir),
                "--originals-dir", str(originals_dir),
                "--out-yaml", str(line_spacing_full_path),
                "--out-md", str(line_spacing_full_md),
            ])
            # Surface inconsistent-frame count to the rollup
            try:
                lsfa_data = yaml.safe_load(line_spacing_full_path.read_text(encoding="utf-8")) or {}
            except Exception:
                lsfa_data = {}
            bad_frames = lsfa_data.get("inconsistent_frames") or []
            summary = lsfa_data.get("summary") or {}
            n_major = summary.get("drift_major") or 0
            if bad_frames:
                issue_parts.append(
                    f"{len(bad_frames)} frame(s) with inconsistent <para>/<trail> pattern"
                )
                print(
                    f"[{tid}] line_spacing_full_audit: {len(bad_frames)} inconsistent "
                    f"frame(s) ({n_major} drift_major) → REVIEW",
                    file=sys.stderr,
                )
            elif n_major:
                print(
                    f"[{tid}] line_spacing_full_audit: {n_major} drift_major (no inconsistent frames)",
                    file=sys.stderr,
                )
            else:
                print(f"[{tid}] line_spacing_full_audit: OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "line_spacing_full_audit",
                "E3 (line_spacing_full_audit)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit E3 (line_spacing_full_audit): skipped (no build.py)",
            file=sys.stderr,
        )

    # Phase E4: line_spacing_pixel_audit — pixel-level ink-top measurement.
    # The authoritative per-frame drift signal. Bypasses pdfplumber's text-
    # matrix Y (which hides per-font-metric differences between InDesign
    # and Scribus rendering of the same font file). Issue #40 follow-up:
    # pdfplumber matches were misleading me into declaring fixes that
    # rendered visibly wrong; pixel scan caught the actual drift.
    line_spacing_pixel_path = out_dir / "line_spacing_pixel_audit.yml"
    line_spacing_pixel_md = out_dir / "line_spacing_pixel_audit.md"
    if preview_pdf.exists() and baseline.exists() and build_py.exists():
        try:
            from line_spacing_pixel_audit import main as _lspa_main
            templates_dir = Path("/workspace/templates")
            _lspa_main([
                "--slug", tid,
                "--templates-dir", str(templates_dir),
                "--dpi", "150",
                "--out-yaml", str(line_spacing_pixel_path),
                "--out-md", str(line_spacing_pixel_md),
                # render-gallery has just produced fresh artifacts in
                # sequence; the freshness gate doesn't apply here.
                "--skip-freshness",
            ])
            try:
                lspa_data = yaml.safe_load(line_spacing_pixel_path.read_text(encoding="utf-8")) or {}
            except Exception:
                lspa_data = {}
            summary = lspa_data.get("summary") or {}
            n_major = summary.get("major") or 0
            n_minor = summary.get("minor") or 0
            if n_major:
                issue_parts.append(
                    f"{n_major} frame(s) with pixel-level line-spacing major drift (>3pt)"
                )
                print(
                    f"[{tid}] line_spacing_pixel_audit: {n_major} major (>3pt), "
                    f"{n_minor} minor (1-3pt) → REVIEW",
                    file=sys.stderr,
                )
            elif n_minor:
                print(
                    f"[{tid}] line_spacing_pixel_audit: {n_minor} minor drift (1-3pt)",
                    file=sys.stderr,
                )
            else:
                print(f"[{tid}] line_spacing_pixel_audit: OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "line_spacing_pixel_audit",
                "E4 (line_spacing_pixel_audit)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit E4 (line_spacing_pixel_audit): skipped",
            file=sys.stderr,
        )

    # Phase E5: image_frame_visibility_audit — catches "embedded but
    # invisible" image frames. Counts ink pixel density inside each
    # ImageFrame bbox in baseline vs preview; flags frames where
    # preview is mostly background. Common cause: Scribus 1.6.x
    # SCALETYPE=1 + small-frame + RGBA white-on-transparent PNG bug
    # (see tools/sla_lib/builder/primitives.py:807-813). Pre-existing
    # image_audit reports count mismatches but doesn't catch this.
    image_visibility_path = out_dir / "image_frame_visibility_audit.yml"
    image_visibility_md = out_dir / "image_frame_visibility_audit.md"
    if preview_pdf.exists() and baseline.exists() and build_py.exists():
        try:
            from image_frame_visibility_audit import main as _ifv_main
            templates_dir = Path("/workspace/templates")
            _ifv_main([
                "--slug", tid,
                "--templates-dir", str(templates_dir),
                "--dpi", "150",
                "--out-yaml", str(image_visibility_path),
                "--out-md", str(image_visibility_md),
                "--skip-freshness",
            ])
            try:
                ifv_data = yaml.safe_load(image_visibility_path.read_text(encoding="utf-8")) or {}
            except Exception:
                ifv_data = {}
            summary = ifv_data.get("summary") or {}
            invisible = ifv_data.get("invisible_frames") or []
            n_invisible = summary.get("invisible_in_preview") or 0
            n_faint = summary.get("faint_in_preview") or 0
            if n_invisible:
                issue_parts.append(
                    f"{n_invisible} image frame(s) invisible in preview: {invisible}"
                )
                print(
                    f"[{tid}] image_frame_visibility_audit: {n_invisible} INVISIBLE "
                    f"frame(s): {invisible} → REVIEW",
                    file=sys.stderr,
                )
            elif n_faint:
                print(
                    f"[{tid}] image_frame_visibility_audit: {n_faint} faint (visibility 0.3-0.7)",
                    file=sys.stderr,
                )
            else:
                print(f"[{tid}] image_frame_visibility_audit: OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "image_frame_visibility_audit",
                "E5 (image_frame_visibility_audit)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit E5 (image_frame_visibility_audit): skipped",
            file=sys.stderr,
        )

    # Phase E6: per_region_regression_check — compares the just-emitted
    # E4 + E5 per-frame measurements against the previous render's
    # measurements (persisted in build/<slug>/per_region_history.jsonl).
    # Flags frames that regressed on either axis since the prior run.
    # E2-E5 each compare against baseline.pdf within ONE iteration; E6
    # ensures iteration-over-iteration we never silently make a frame
    # worse. Closes the "no history tracking for per-region drift" gap.
    per_region_regression_path = out_dir / "per_region_regression.yml"
    per_region_regression_md = out_dir / "per_region_regression.md"
    if line_spacing_pixel_path.exists() or image_visibility_path.exists():
        try:
            from per_region_regression_check import main as _prr_main
            _prr_main([
                "--slug", tid,
                "--validation-dir", str(out_dir.parent),
                "--history-dir", str(Path(__file__).resolve().parent.parent / "templates"),
                "--out-yaml", str(per_region_regression_path),
                "--out-md", str(per_region_regression_md),
            ])
            try:
                prr_data = yaml.safe_load(per_region_regression_path.read_text(encoding="utf-8")) or {}
            except Exception:
                prr_data = {}
            n_reg = prr_data.get("regression_count") or 0
            seeded = prr_data.get("seeded") or False
            if seeded:
                print(
                    f"[{tid}] per_region_regression: seeded history (first run)",
                    file=sys.stderr,
                )
            elif n_reg:
                regressions = prr_data.get("regressions") or []
                names = [r.get("anname") for r in regressions]
                issue_parts.append(
                    f"{n_reg} per-region regression(s) since previous render"
                )
                print(
                    f"[{tid}] per_region_regression: {n_reg} REGRESSION(s) since previous run: "
                    f"{names} → REVIEW",
                    file=sys.stderr,
                )
            else:
                print(f"[{tid}] per_region_regression: OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "per_region_regression",
                "E6 (per_region_regression)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit E6 (per_region_regression): skipped (no E4/E5 input)",
            file=sys.stderr,
        )

    # ── Phases E7–E12: thoroughness pack — every audit tool wired up so
    # bin/tune-render fails locally for the same reasons CI would, with
    # one-line stderr messages that name the failing check. Each phase
    # writes its own YML report under build/validation/<slug>/ for
    # downstream review.

    # Phase E7: structural_check — enforces module-level CONSTRAINTS and
    # global BRAND_CONSTRAINTS. Previously CI-only (.github/workflows/
    # pages.yml); 141 declared constraints across 9 templates were not
    # being checked locally so devs only saw failures after pushing.
    structural_check_path = out_dir / "structural_check.yml"
    try:
        import sys as _sys
        if str(ROOT / "tools") not in _sys.path:
            _sys.path.insert(0, str(ROOT / "tools"))
        from sla_lib.builder.structural_check import check_template as _sc_run
        sc_rep = _sc_run(tid, root=ROOT)
        sc_summary = {
            "slug": tid,
            "fatal_error": sc_rep.fatal_error,
            "constraint_errors": [
                {"rule": i.rule_id, "message": i.message, "location": i.location}
                for i in sc_rep.constraint_issues if i.severity == "error"
            ],
            "constraint_warnings": [
                {"rule": i.rule_id, "message": i.message, "location": i.location}
                for i in sc_rep.constraint_issues if i.severity == "warning"
            ],
            "brand_errors": [
                {"rule": i.rule_id, "message": i.message, "location": i.location}
                for i in sc_rep.brand_issues if i.severity == "error"
            ],
            "constraints_passed": sum(
                1 for i in sc_rep.constraint_issues if i.severity == "pass"
            ),
            "brand_passed": sum(
                1 for i in sc_rep.brand_issues if i.severity == "pass"
            ),
            "skipped_brand_rules": [
                {"rule_id": rid, "reason": reason}
                for rid, reason in sc_rep.skipped_brand_rules
            ],
            "ok": not sc_rep.has_errors,
        }
        structural_check_path.write_text(
            yaml.dump(sc_summary, sort_keys=True, allow_unicode=True,
                      default_flow_style=False),
            encoding="utf-8",
        )
        if sc_rep.fatal_error:
            issue_parts.append(f"structural_check fatal: {sc_rep.fatal_error}")
            print(f"[{tid}] structural_check: FATAL — {sc_rep.fatal_error}",
                  file=sys.stderr)
        elif sc_rep.has_errors:
            n_ce = len(sc_summary["constraint_errors"])
            n_be = len(sc_summary["brand_errors"])
            issue_parts.append(
                f"{n_ce} constraint + {n_be} brand-rule error(s)"
            )
            for e in sc_summary["constraint_errors"][:5]:
                print(f"[{tid}] structural_check FAIL ({e['rule']}): "
                      f"{e['message']}",
                      file=sys.stderr)
            for e in sc_summary["brand_errors"][:5]:
                print(f"[{tid}] brand_constraint FAIL ({e['rule']}): "
                      f"{e['message']}",
                      file=sys.stderr)
        else:
            print(
                f"[{tid}] structural_check: OK "
                f"({sc_summary['constraints_passed']} CONSTRAINTS, "
                f"{sc_summary['brand_passed']} brand rules)"
            )
    except Exception as exc:
        _record_phase_error(
            phase_errors, "structural_check",
            "E7 (structural_check)", exc, tid,
        )

    # Phase E8: check_no_absolute_paths_in_sla — guards against
    # developer-machine paths (``/Users/...``, ``/home/...``) leaking
    # into the committed SLA bytes. Previously CI-only
    # (.github/workflows/ci.yml SOP-gates step). Walks SLAs under this
    # template directory only (faster + scoped to current iteration).
    path_check_path = out_dir / "path_check.yml"
    try:
        from check_no_absolute_paths_in_sla import find_absolute_pfiles
        # find_absolute_pfiles walks all *.sla under the given root.
        # Scoping to ``tdir`` keeps the audit per-template.
        violations = find_absolute_pfiles(tdir)
        path_summary = {
            "slug": tid,
            "violations": [
                {
                    "sla": str(p.relative_to(ROOT)),
                    "lineno": lineno,
                    "pfile": pfile,
                }
                for (p, lineno, pfile) in violations
            ],
            "ok": not violations,
        }
        path_check_path.write_text(
            yaml.dump(path_summary, sort_keys=True, allow_unicode=True,
                      default_flow_style=False),
            encoding="utf-8",
        )
        if violations:
            issue_parts.append(
                f"{len(violations)} absolute path(s) in committed SLA"
            )
            for (p, lineno, pfile) in violations[:3]:
                print(
                    f"[{tid}] check_no_absolute_paths FAIL "
                    f"({p.name}:{lineno}): {pfile}",
                    file=sys.stderr,
                )
        else:
            print(f"[{tid}] check_no_absolute_paths_in_sla: OK")
    except Exception as exc:
        _record_phase_error(
            phase_errors, "path_check",
            "E8 (check_no_absolute_paths_in_sla)", exc, tid,
        )

    # Phase E9: check_ci — per-SLA brand-identity drift (colour palette,
    # layers, styles). Critical findings reject the SLA. Previously
    # CI-only (.github/workflows/pages.yml).
    check_ci_path = out_dir / "check_ci.yml"
    try:
        from check_ci import check_sla as _ci_check, load_ci as _ci_load
        ci_def = _ci_load(ROOT / "shared" / "ci.yml")
        report = _ci_check(tdir / "template.sla", ci_def)
        # CIDriftReport has .issues list with severity ∈ {critical,
        # warning, info}.
        critical = [i for i in report.issues if i.severity == "critical"]
        warning = [i for i in report.issues if i.severity == "warning"]
        ci_summary = {
            "slug": tid,
            "sla": str((tdir / "template.sla").relative_to(ROOT)),
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "message": i.message,
                }
                for i in report.issues
            ],
            "critical_count": len(critical),
            "warning_count": len(warning),
            "ok": not critical,
        }
        check_ci_path.write_text(
            yaml.dump(ci_summary, sort_keys=True, allow_unicode=True,
                      default_flow_style=False),
            encoding="utf-8",
        )
        if critical:
            issue_parts.append(
                f"{len(critical)} CI/brand-drift critical"
            )
            for d in critical[:3]:
                print(
                    f"[{tid}] check_ci FAIL ({d.code}): {d.message}",
                    file=sys.stderr,
                )
        elif warning:
            print(f"[{tid}] check_ci: {len(warning)} warning(s)")
        else:
            print(f"[{tid}] check_ci: OK")
    except Exception as exc:
        _record_phase_error(
            phase_errors, "check_ci",
            "E9 (check_ci)", exc, tid,
        )

    # Phase E10: spec_check — Spec-vs-Build drift detector (#issue/12).
    # Only runs when templates/_specs/<slug>.md exists with a slots
    # block. Informational unless drift > tolerance, then hard fail.
    spec_check_path = out_dir / "spec_check.yml"
    spec_md = ROOT / "templates" / "_specs" / f"{tid}.md"
    if spec_md.exists():
        try:
            from spec_check import check as _spec_run
            n_drift, messages = _spec_run(tid)
            spec_summary = {
                "slug": tid,
                "drift_count": n_drift,
                "messages": messages,
                "ok": n_drift == 0,
            }
            spec_check_path.write_text(
                yaml.dump(spec_summary, sort_keys=True, allow_unicode=True,
                          default_flow_style=False),
                encoding="utf-8",
            )
            if n_drift:
                issue_parts.append(f"{n_drift} spec-vs-build drift")
                for m in messages[:3]:
                    print(f"[{tid}] spec_check FAIL: {m}", file=sys.stderr)
            else:
                print(f"[{tid}] spec_check: OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "spec_check",
                "E10 (spec_check)", exc, tid,
            )
    else:
        print(f"[{tid}] audit E10 (spec_check): skipped (no _specs/{tid}.md)",
              file=sys.stderr)

    # Phase E11: lint_inject_consistency — inject.yml ↔ build.py #P5
    # comment correspondence. Only runs when inject.yml exists.
    inject_yml = tdir / "inject.yml"
    if inject_yml.exists():
        lint_inject_path = out_dir / "lint_inject_consistency.yml"
        try:
            from lint_inject_consistency import check_template as _lic_run
            messages = _lic_run(tdir)
            lic_summary = {
                "slug": tid,
                "violations": messages,
                "ok": not messages,
            }
            lint_inject_path.write_text(
                yaml.dump(lic_summary, sort_keys=True, allow_unicode=True,
                          default_flow_style=False),
                encoding="utf-8",
            )
            if messages:
                issue_parts.append("inject.yml ↔ build.py drift")
                for m in messages[:3]:
                    print(
                        f"[{tid}] lint_inject_consistency FAIL: {m}",
                        file=sys.stderr,
                    )
            else:
                print(f"[{tid}] lint_inject_consistency: OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "lint_inject_consistency",
                "E11 (lint_inject_consistency)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit E11 (lint_inject_consistency): skipped "
            "(no inject.yml)",
            file=sys.stderr,
        )

    # Phase E12b: reconcile_build_py --check — only when both
    # inject.yml and build.py.generated exist. Re-derives build.py from
    # build.py.generated + inject.yml hand_patches and diffs the result
    # against the committed build.py. Catches "edited build.py directly
    # without updating inject.yml" regressions. Previously CI-only
    # (.github/workflows/ci.yml SOP-gates step).
    generated_py = tdir / "build.py.generated"
    if inject_yml.exists() and generated_py.exists():
        reconcile_path = out_dir / "reconcile_build_py.yml"
        try:
            r = subprocess.run(
                [sys.executable,
                 str(ROOT / "tools" / "reconcile_build_py.py"),
                 tid, "--check"],
                capture_output=True, text=True, cwd=str(ROOT),
            )
            reconcile_path.write_text(
                yaml.dump({
                    "slug": tid,
                    "returncode": r.returncode,
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                    "ok": r.returncode == 0,
                }, sort_keys=True, allow_unicode=True,
                          default_flow_style=False),
                encoding="utf-8",
            )
            if r.returncode != 0:
                issue_parts.append(
                    "reconcile_build_py: build.py drifted from "
                    "build.py.generated + inject.yml"
                )
                print(
                    f"[{tid}] reconcile_build_py FAIL:\n"
                    f"{r.stdout}{r.stderr}",
                    file=sys.stderr,
                )
            else:
                print(f"[{tid}] reconcile_build_py: OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "reconcile_build_py",
                "E12b (reconcile_build_py)", exc, tid,
            )
    else:
        # Skip silently — the inject.yml + build.py.generated pair is
        # only required for the two-stage scaffold flow, not every template.
        pass

    # Phase E12: audit_alignment — heuristic alignment-pair suggester.
    # Informational only (matches CI's `|| true` semantics in
    # pages.yml). Surfaces "you might want a same_x / same_y here"
    # suggestions; never blocks the pipeline.
    align_audit_path = out_dir / "audit_alignment.yml"
    try:
        from audit_alignment import audit_template as _aa_audit
        rep = _aa_audit(tid)
        n_undecl = 0
        pages_payload = []
        for p in rep.pages:
            n_undecl += len(p.suspicious_pairs)
            pages_payload.append({
                "page": p.page_idx,
                "label": p.page_label,
                "declared_pairs": len(p.declared_pairs),
                "suspicious_pairs": [
                    {"kind": pp.kind, "a": pp.a, "b": pp.b,
                     "delta_mm": pp.delta_mm,
                     "suggested": pp.suggested}
                    for pp in p.suspicious_pairs
                ],
            })
        align_audit_path.write_text(
            yaml.dump({"slug": tid, "pages": pages_payload,
                       "suspicious_count": n_undecl},
                      sort_keys=True, allow_unicode=True,
                      default_flow_style=False),
            encoding="utf-8",
        )
        if n_undecl:
            print(
                f"[{tid}] audit_alignment: {n_undecl} undeclared adjacencies "
                f"(informational)"
            )
        else:
            print(f"[{tid}] audit_alignment: OK")
    except Exception as exc:
        _record_phase_error(
            phase_errors, "audit_alignment",
            "E12 (audit_alignment)", exc, tid,
        )

    # Phase E: per-element drift attribution.
    # Aggregates diff_bboxes.json into a per-slot contribution table so the next
    # fix dispatch can prioritise by leverage. Diagnostic only — never blocks audit.
    diff_bboxes_path = out_dir / "diff_bboxes.json"
    vd_json = out_dir / "visual_diff.json"
    if diff_bboxes_path.exists() and vd_json.exists():
        try:
            import json as _json
            from per_element_drift import aggregate_per_element as _ped_aggregate
            from per_element_drift import _yaml_dump as _ped_yaml

            _db = _json.loads(diff_bboxes_path.read_text(encoding="utf-8"))
            _vd = _json.loads(vd_json.read_text(encoding="utf-8"))
            _ped_result = _ped_aggregate(_db, _vd)
            ped_path = out_dir / "per_element_drift.yml"
            ped_path.write_text(_ped_yaml(_ped_result), encoding="utf-8")
            for _page in _ped_result.get("pages", []):
                _top = _page.get("top_contributors", [])
                if _top:
                    _leader = _top[0]
                    print(
                        f"[{tid}] per_element_drift: "
                        f"top contributor page {_page['page'] + 1} is "
                        f"{_leader['slot']} "
                        f"({_leader['pct_of_page_total_drift']:.1f}pp of page drift)"
                    )
        except Exception as exc:
            _record_phase_error(
                phase_errors, "per_element_drift",
                "E (per_element_drift)", exc, tid,
            )

    # Phase G: region_color_audit — per-region ICC-vs-fill-bug classification.
    # Runs when both preview.pdf and baseline.pdf exist. Diagnostic only (never
    # blocks audit). Writes region_color_audit.yml and prints a one-line summary.
    color_audit_path = out_dir / "region_color_audit.yml"
    preview_pdf_path = tdir / "preview.pdf"
    if preview_pdf_path.exists() and baseline.exists() and build_py.exists():
        try:
            from region_color_audit import run_region_color_audit as _rca_run
            from region_color_audit import _yaml_dump as _rca_yaml
            _rca_result = _rca_run(build_py, baseline, preview_pdf_path, tid)
            color_audit_path.write_text(_rca_yaml(_rca_result), encoding="utf-8")
            _bs = _rca_result["by_severity"]
            print(
                f"[{tid}] region_color_audit: "
                f"{_bs.get('ok', 0)} ok, "
                f"{_bs.get('icc_likely', 0)} icc_likely, "
                f"{_bs.get('fill_likely', 0)} fill_likely "
                f"— pattern: {_rca_result['pattern']}"
            )
        except Exception as exc:
            _record_phase_error(
                phase_errors, "region_color_audit",
                "G (region_color_audit)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit G (region_color_audit): skipped "
            f"(no preview.pdf or baseline.pdf or build.py)",
            file=sys.stderr,
        )

    # Phase H: per-region visual_diff (Backport 12 / Issue #37 P2).
    # Runs ONLY when the page-wide rasterised PNGs already exist
    # (baseline-page-N.png / dsl-page-N.png are produced by the page-wide
    # visual_diff in _orchestrate_template). Diagnostic + failable; failing
    # cells are surfaced to preflight via _build_preflight below.
    vd_region_path = out_dir / "visual_diff_regions.yml"
    if (out_dir / "baseline-page-1.png").exists() and (out_dir / "dsl-page-1.png").exists():
        try:
            from visual_diff import (
                run_region_grid_audit as _vdr_run,
                TemplateTolerance as _VDTol,
            )
            _vdr_tol = _VDTol.load(tdir / "diff.yml")
            _vdr_result = _vdr_run(
                baseline_png_dir=out_dir,
                preview_png_dir=out_dir,
                tolerance=_vdr_tol,
                out_dir=out_dir,
                template=tid,
            )
            vd_region_path.write_text(
                yaml.dump(
                    _vdr_result,
                    sort_keys=True,
                    allow_unicode=True,
                    default_flow_style=False,
                ),
                encoding="utf-8",
            )
            n_hot = sum(len(p["hot_regions"]) for p in _vdr_result["pages"])
            if not _vdr_result["ok"]:
                print(
                    f"[{tid}] visual_diff_regions: {n_hot} hot region(s) → REVIEW",
                    file=sys.stderr,
                )
                issue_parts.append(f"{n_hot} hot region(s)")
            else:
                print(f"[{tid}] visual_diff_regions: OK")
        except Exception as exc:
            _record_phase_error(
                phase_errors, "visual_diff_regions",
                "H (visual_diff_regions)", exc, tid,
            )
    else:
        print(
            f"[{tid}] audit H (visual_diff_regions): skipped "
            "(no baseline/dsl page PNGs)",
            file=sys.stderr,
        )

    # Issue #37 P1 task 6: aggregated preflight.yml — one canonical
    # "are all sub-audits ok?" file that bin/render-gallery --audit hard-fails on.
    # Audit-reliability review item 2: phase_errors flows through so each
    # exception is captured in preflight.yml::errors instead of vanishing
    # into stderr only.
    preflight = _build_preflight(
        out_dir, tid,
        inventory_path=inventory_path,
        text_audit_path=text_audit_path,
        image_audit_path=image_audit_path,
        font_audit_path=font_audit_path,
        text_render_audit_path=text_render_audit_path,
        text_position_audit_path=text_position_audit_path,
        run_style_audit_path=run_style_audit_path,
        color_audit_path=color_audit_path,
        visual_diff_regions_path=vd_region_path,
        line_spacing_audit_path=line_spacing_audit_path,
        asset_audit_path=asset_audit_path,
        phase_errors=phase_errors,
    )
    preflight_path = out_dir / "preflight.yml"
    preflight_path.write_text(
        yaml.dump(
            preflight,
            sort_keys=True,
            allow_unicode=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    if not preflight["ok"]:
        n_failed = sum(1 for a in preflight["audits"].values() if not a["ok"])
        issue_parts.append(f"preflight FAILED ({n_failed} sub-audit(s))")
    if phase_errors:
        issue_parts.append(
            f"{len(phase_errors)} audit phase(s) errored: "
            f"{', '.join(sorted(phase_errors.keys()))}"
        )

    if issue_parts:
        summary = f"[{tid}] audit: {', '.join(issue_parts)} → REVIEW REQUIRED"
    else:
        summary = f"[{tid}] audit: clean"

    return len(issue_parts), summary


def _build_preflight(
    out_dir: Path,
    tid: str,
    inventory_path: Path,
    text_audit_path: Path,
    image_audit_path: Path,
    font_audit_path: Path,
    text_render_audit_path: Path,
    text_position_audit_path: Path,
    run_style_audit_path: Path,
    color_audit_path: Path,
    visual_diff_regions_path: Path | None = None,
    line_spacing_audit_path: Path | None = None,
    asset_audit_path: Path | None = None,
    phase_errors: dict[str, str] | None = None,
) -> dict:
    """Aggregate every sub-audit yml into a single preflight dict (Issue #37 P1 task 6).

    Shape::
        {
          template: <slug>,
          ok: bool (AND of every sub-audit's ok AND no phase errors),
          audits: {
            <name>: {ok: bool, issues: int, detail: str},
            ...
          },
          errors: {<phase_key>: <exception_str>, ...},
          hot_issues: [
            {audit: <name>, issues: int, message: str},
            ...  # top 5 by issues count, failing only
          ],
        }

    Sub-audits that emit a yml ARE recorded; sub-audits whose yml is missing
    (audit skipped because preview.pdf/baseline.pdf not present) are silently
    omitted — they neither pass nor fail the preflight.

    Diagnostic-only audits (``per_element_drift``, ``region_color_audit``)
    are always recorded with ``ok=True``; they surface in ``hot_issues`` only
    if explicitly opted-in by a future schema bump.

    Audit-reliability review item 2: ``phase_errors`` carries per-phase
    exception strings captured by ``_record_phase_error`` during
    ``_run_audit``. Non-empty ``phase_errors`` always sets ``ok=False`` and
    surfaces in the output ``errors`` dict so an exception cannot silently
    leave preflight green.
    """
    def _load_yml(p: Path) -> dict | None:
        if not p.exists():
            return None
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:
            return None

    audits_summary: dict[str, dict] = {}

    def _record(name: str, ok: bool, issues: int, detail: str = "") -> None:
        audits_summary[name] = {
            "ok": bool(ok),
            "issues": int(issues),
            "detail": detail or "",
        }

    inv = _load_yml(inventory_path)
    if inv is not None:
        n_dropped = sum(
            len(s.get("elements_dropped", []))
            for s in inv.get("spreads", [])
        )
        _record("inventory", n_dropped == 0, n_dropped,
                f"{n_dropped} dropped element(s)" if n_dropped else "")

    ta = _load_yml(text_audit_path)
    if ta is not None:
        n_unmatched = sum(
            len(p.get("lines_unmatched", []))
            for p in ta.get("pages", [])
        )
        _record("text_audit", n_unmatched == 0, n_unmatched, "")

    ia = _load_yml(image_audit_path)
    if ia is not None:
        n_delta = sum(
            p.get("vector_paths", {}).get("delta", 0)
            for p in ia.get("pages", [])
            if p.get("vector_paths", {}).get("delta", 0) > 0
        )
        _record("image_audit", n_delta == 0, n_delta, "")

    fa = _load_yml(font_audit_path)
    if fa is not None:
        missing = fa.get("missing_in_preview", []) or []
        _record("font_audit", bool(fa.get("ok", False)), len(missing),
                ", ".join(missing) if missing else "")

    tra = _load_yml(text_render_audit_path)
    if tra is not None:
        missing = tra.get("missing_in_preview", {}) or {}
        _record("text_render_audit", bool(tra.get("ok", False)),
                len(missing), "")

    tpa = _load_yml(text_position_audit_path)
    if tpa is not None:
        _record("text_position_audit", bool(tpa.get("ok", False)),
                int(tpa.get("large_deltas_count", 0) or 0), "")

    rsa = _load_yml(run_style_audit_path)
    if rsa is not None:
        large = sum(
            1 for d in (rsa.get("style_drifts") or [])
            if d.get("severity") == "large"
        )
        _record("run_style_audit", bool(rsa.get("ok", False)) and large == 0,
                large, "")

    ped = _load_yml(out_dir / "per_element_drift.yml")
    if ped is not None:
        # diagnostic only — never fails preflight
        _record("per_element_drift", True, 0,
                "diagnostic; see top_contributors")

    rca = _load_yml(color_audit_path)
    if rca is not None:
        # diagnostic only — but record the pattern + fill_likely count
        fill_likely = int(
            (rca.get("by_severity") or {}).get("fill_likely", 0) or 0
        )
        _record("region_color_audit", True, fill_likely,
                str(rca.get("pattern", "")))

    # Phase H (Issue #37 P2 task 10): per-region visual_diff. Hot-region count
    # comes from the audit's hot_regions list (capped at 10 per page).
    if visual_diff_regions_path is not None:
        vdr = _load_yml(visual_diff_regions_path)
        if vdr is not None:
            n_hot = sum(
                len(p.get("hot_regions", []) or [])
                for p in (vdr.get("pages") or [])
            )
            _record(
                "visual_diff_regions",
                bool(vdr.get("ok", True)),
                n_hot,
                "",
            )

    # Phase E2 (Issue #37 P3 task 14): line_spacing_audit drift count.
    # F-017: when the YAML carries informational_only=true the audit is
    # recorded but always marked ok=true so it doesn't fail preflight.
    # Canonical signal is E4 (line_spacing_pixel_audit).
    if line_spacing_audit_path is not None:
        lsa = _load_yml(line_spacing_audit_path)
        if lsa is not None:
            informational = bool(lsa.get("informational_only", False))
            drift_count = int(lsa.get("line_spacing_drift_count", 0) or 0)
            detail = ""
            if informational and drift_count:
                detail = (
                    f"informational only ({drift_count} drift, see "
                    f"line_spacing_pixel_audit for canonical signal)"
                )
            _record(
                "line_spacing_audit",
                True if informational else bool(lsa.get("ok", True)),
                drift_count,
                detail,
            )

    # Phase E (Issue #38 Task 2): asset_extraction_audit must be FIRST in the
    # chain logically (missing links cascade into every other audit). We
    # record it last in this builder for ordering symmetry with the other
    # blocks; the audit itself runs first in _run_audit.
    if asset_audit_path is not None:
        aa = _load_yml(asset_audit_path)
        if aa is not None:
            missing = len(aa.get("links_missing", []) or [])
            unconv = len(aa.get("links_unconverted", []) or [])
            comp = len(aa.get("composite_ai_detected", []) or [])
            issues = missing + unconv + comp
            detail = (
                f"{missing} missing, {unconv} unconverted, "
                f"{comp} composite-AI"
                if issues
                else ""
            )
            _record(
                "asset_extraction",
                bool(aa.get("ok", True)),
                issues,
                detail,
            )

    errors = dict(phase_errors or {})
    preflight_ok = all(a["ok"] for a in audits_summary.values()) and not errors

    # Hot-issues list: top 5 failing audits by issue count.
    hot = sorted(
        ((name, info) for name, info in audits_summary.items()
         if not info["ok"]),
        key=lambda kv: -kv[1]["issues"],
    )[:5]
    hot_issues = [
        {
            "audit": name,
            "issues": info["issues"],
            "message": info["detail"] or f"{info['issues']} issue(s)",
        }
        for name, info in hot
    ]
    # Each errored phase becomes its own top-priority hot issue, so the
    # rollup surfaces "audit X errored" alongside the audit-issue table.
    for phase_key, exc_msg in sorted(errors.items()):
        hot_issues.insert(0, {
            "audit": phase_key,
            "issues": 1,
            "message": f"phase errored: {exc_msg}",
        })

    return {
        "template": tid,
        "ok": preflight_ok,
        "audits": audits_summary,
        "errors": errors,
        "hot_issues": hot_issues,
    }


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
        "--visual-diff-warning-only",
        action="store_true",
        help=(
            "Run visual_diff (emits diff-page-NN.png/composite-page-NN.png) but "
            "treat its non-zero exit as a warning so the audit chain still "
            "runs. Used by `bin/tune-render` during Stage-2 iteration when the "
            "template is expected to drift while being fixed."
        ),
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
            "After render+visual_diff, run every sub-audit (inventory, text, "
            "image, fonts, text-render, text-position, run-style, "
            "per-element-drift, region-color) and write reports to "
            "build/validation/<slug>/*.yml. Aggregates the sub-audits into a "
            "single preflight.yml. "
            "Hard-fails (exit non-zero) when any preflight.yml::ok == false. "
            "Use --audit-strict to additionally fail on any audit issue_parts."
        ),
    )
    parser.add_argument(
        "--audit-strict",
        action="store_true",
        help=(
            "Same as --audit but also exits non-zero if any audit-summary "
            "issue_parts are reported (a stricter superset of preflight failure). "
            "Implies --audit. Intended for CI."
        ),
    )
    parser.add_argument(
        "--allow-composite-ai",
        action="store_true",
        help=(
            "Downgrade asset_extraction_audit composite-AI findings to warnings "
            "instead of hard failures. Use when you have intentionally chosen "
            "raster fallback for a composite .ai strip (degraded vector quality). "
            "Issue #38 Task 14 introduces a per-page splitter that obsoletes this."
        ),
    )

    args = parser.parse_args(argv)
    # --audit-strict implies --audit
    if args.audit_strict:
        args.audit = True

    # Preflight: brand fonts.
    _verify_brand_fonts()

    # Global SOP gates (run once per render-gallery invocation). These
    # were previously CI-only (.github/workflows/ci.yml SOP-gates step).
    # Wiring them locally so a developer running bin/tune-render fails
    # for the same reasons CI would, with named errors pointing at the
    # exact violating tool. Errors here are HARD fail (return non-zero
    # before any rendering happens) so they catch the issue before
    # template artifacts are touched.
    _run_global_sop_gates()

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
    # Issue #37 P1 task 6: --audit (not just --audit-strict) hard-fails when
    # any per-template preflight.yml::ok == false.
    if getattr(args, "audit", False):
        preflight_failed: list[str] = []
        for tdir in work:
            tid = tdir.name
            preflight_p = ROOT / "build" / "validation" / tid / "preflight.yml"
            if preflight_p.exists():
                try:
                    pre = yaml.safe_load(
                        preflight_p.read_text(encoding="utf-8")
                    ) or {}
                except Exception:
                    pre = {}
                if pre.get("ok") is False:
                    preflight_failed.append(tid)
        if preflight_failed:
            print(
                f"AUDIT: preflight failed for {len(preflight_failed)} "
                f"template(s) — exiting non-zero: "
                f"{', '.join(preflight_failed)}",
                file=sys.stderr,
            )
            overall = 1
    # --audit-strict: additionally fail if any audit issue_parts reported
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
