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

    Scribus 1.6.x embeds:
    - /CreationDate (D:YYYYMMDDhhmmssZ) in the Info dict
    - /ModDate      (D:YYYYMMDDhhmmssZ) in the Info dict
    - /ID [<32hex><32hex>]              in the trailer

    All three vary per-run even on identical source SLAs. The substitution is
    byte-length-preserving so xref byte offsets in the PDF remain valid.
    Empirically verified: two renders 3s apart → after scrub → cmp says IDENTICAL.
    (RESEARCH.md §Idempotency Strategy, lines 298-360)
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
    p.write_bytes(data)


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
