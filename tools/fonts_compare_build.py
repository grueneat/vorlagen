#!/usr/bin/env python3
"""Build the font-comparison artifacts for Issue 42.

Orchestrates the whole comparison pipeline for the flyer
``flyer-a6-hochformat-gruenes-cover`` against the five free SIL-OFL Gotham
alternatives in ``shared/fonts/alternatives.yml``:

  1. Install the bundled alternative fonts into the local fontconfig path
     and refresh the cache, so the renderer resolves them. The fonts are
     static per-weight TTFs (see tools/font_instantiate.py) and register
     under "<Family> <Weight>" names with no fontconfig alias needed.
  2. Generate one variant SLA per alternative (tools/font_variants.py).
  3. Render each variant SLA to PDF, then rasterise to per-page thumbnails
     and hi-res PNGs (the same render_sla_to_pdf / rasterise helpers the
     gallery pipeline uses).
  4. Place the artifacts under templates/<flyer>/fonts/<slug>/ and mirror
     the PNGs + PDF to site/public/schriften/<slug>/.
  5. Write site/src/data/schriften.json — the data source the comparison
     page (site/src/pages/schriften/index.astro) consumes.

Rendering needs Scribus. When ``scribus`` is not on PATH (CI / this
environment), steps 1–2 and 5 still run: the variant SLAs and the JSON data
file are produced, the JSON records that PNGs are absent, and steps 3–4 are
skipped. Rendering is then a maintainer step in the dev container
(``bin/render-gallery`` path) — exactly like tools/gallery_build.py is
copy-only. The comparison page works either way: with no PNG it links the
variant SLA instead.

CLI:
  python3 tools/fonts_compare_build.py
      Run the full pipeline (render if Scribus is available).
  python3 tools/fonts_compare_build.py --no-render
      Skip rendering even if Scribus is available (data + SLAs only).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import font_variants  # noqa: E402

# DPI constants mirror tools/render_pipeline.py (thumbnail + hi-res passes).
THUMB_DPI = 100
HIRES_DPI = 150

# Local fontconfig install path used by the dev container (see
# shared/fonts/README.md). The alternative fonts are copied here so the
# headless renderer resolves "<family> <weight>" lookups.
FONT_INSTALL_DIR = Path("/usr/local/share/fonts/gruene-alternatives")

ALTERNATIVES_DIR = ROOT / "shared" / "fonts" / "alternatives"
SITE_PUBLIC = ROOT / "site" / "public" / "schriften"
SITE_DATA = ROOT / "site" / "src" / "data" / "schriften.json"


def scribus_available() -> bool:
    """True when the ``scribus`` binary is on PATH."""
    return shutil.which("scribus") is not None


def install_fonts(data: dict) -> bool:
    """Copy the bundled alternative fonts into the fontconfig path.

    Returns True on success. When the install directory is not writable
    (no root / CI) the step is skipped and False is returned — rendering is
    then a maintainer step anyway.
    """
    try:
        FONT_INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print(
            f"[fonts_compare] cannot write {FONT_INSTALL_DIR} — "
            "skipping font install (maintainer step in the dev container)"
        )
        return False

    copied = 0
    for entry in data["fonts"]:
        src_dir = ALTERNATIVES_DIR / entry["slug"]
        for fname in entry["files"]:
            if not fname.lower().endswith((".ttf", ".otf", ".ttc")):
                continue
            src = src_dir / fname
            if src.exists():
                shutil.copy(src, FONT_INSTALL_DIR / src.name)
                copied += 1

    subprocess.run(["fc-cache", "-f", str(FONT_INSTALL_DIR)], check=False)
    print(f"[fonts_compare] installed {copied} font file(s) -> {FONT_INSTALL_DIR}")
    return True


def generate_variant_slas(data: dict, flyer_dir: Path) -> dict[str, Path]:
    """Generate one variant SLA per alternative. Returns {slug: sla_path}."""
    template_sla = flyer_dir / "template.sla"
    out: dict[str, Path] = {}
    for entry in data["fonts"]:
        slug = entry["slug"]
        sla = font_variants.variant_sla_path(template_sla, slug)
        n = font_variants.apply_font(template_sla, sla, entry)
        print(f"[fonts_compare] {slug}: variant SLA — {n} reference(s)")
        out[slug] = sla
    return out


def render_variant(slug: str, sla: Path, out_dir: Path) -> dict:
    """Render one variant SLA to PDF + per-page PNGs under ``out_dir``.

    Returns ``{"pdf": Path, "pages": {n: (thumb, hires)}}`` with repo-relative
    page numbers 1..N. Uses the gallery render helpers so output matches the
    existing pipeline.
    """
    from visual_diff import rasterise, render_sla_to_pdf

    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / f"{slug}.pdf"
    render_sla_to_pdf(sla, pdf)

    thumbs = rasterise(pdf, out_dir / f"{slug}-page", THUMB_DPI)
    hires = rasterise(pdf, out_dir / f"{slug}-hires", HIRES_DPI)

    pages: dict[int, tuple[Path, Path]] = {}
    for i, thumb in enumerate(thumbs, start=1):
        # Normalise to the gallery's <name>.png / <name>-hires.png pairing so
        # the page can derive the hi-res path by suffix swap.
        page_thumb = out_dir / f"{slug}-page-{i:02d}.png"
        page_hires = out_dir / f"{slug}-page-{i:02d}-hires.png"
        if thumb != page_thumb:
            thumb.replace(page_thumb)
        if i <= len(hires):
            hires[i - 1].replace(page_hires)
        pages[i] = (page_thumb, page_hires)
    print(f"[fonts_compare] {slug}: rendered {len(pages)} page(s)")
    return {"pdf": pdf, "pages": pages}


def _rel(path: Path) -> str:
    """Repo-relative POSIX path string."""
    return path.relative_to(ROOT).as_posix()


def mirror_to_public(slug: str, render: dict) -> None:
    """Copy a variant's PDF + PNGs into site/public/schriften/<slug>/."""
    dest = SITE_PUBLIC / slug
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(render["pdf"], dest / render["pdf"].name)
    for thumb, hires in render["pages"].values():
        shutil.copy(thumb, dest / thumb.name)
        if hires.exists():
            shutil.copy(hires, dest / hires.name)


def build_data(data: dict, renders: dict[str, dict], rendered: bool) -> dict:
    """Assemble the schriften.json payload for the comparison page.

    ``fonts`` carries metadata + per-font asset paths; ``pages`` is one entry
    per flyer page, each listing the per-font PNG paths (``null`` when not
    rendered). All paths are public-root absolute (served from site/public).
    """
    flyer_dir = ROOT / "templates" / data["flyer"]
    fonts_out = []
    page_count = 0

    for entry in data["fonts"]:
        slug = entry["slug"]
        render = renders.get(slug)
        variant_sla = font_variants.variant_sla_path(
            flyer_dir / "template.sla", slug
        )
        pdf_public = (
            f"/schriften/{slug}/{slug}.pdf" if render else None
        )
        fonts_out.append(
            {
                "slug": slug,
                "name": entry["name"],
                "license": entry["license"],
                "source": entry["source"],
                "family": entry["family"],
                "summary": entry["summary"].strip(),
                "weights": entry["weights"],
                "pdf": pdf_public,
                # The variant SLA is always available; the page falls back to
                # it as a download when no PDF was rendered.
                "sla": _rel(variant_sla),
            }
        )
        if render:
            page_count = max(page_count, len(render["pages"]))

    # When nothing rendered, derive the page count from the source flyer's
    # committed page PNGs so the page still lays out 6 rows.
    if page_count == 0:
        page_count = len(sorted(flyer_dir.glob("page-*.png")))

    pages = []
    for n in range(1, page_count + 1):
        per_font: dict[str, dict[str, str | None]] = {}
        for entry in data["fonts"]:
            slug = entry["slug"]
            render = renders.get(slug)
            if render and n in render["pages"]:
                per_font[slug] = {
                    "thumb": f"/schriften/{slug}/{slug}-page-{n:02d}.png",
                    "hires": f"/schriften/{slug}/{slug}-page-{n:02d}-hires.png",
                }
            else:
                per_font[slug] = {"thumb": None, "hires": None}
        pages.append({"page": n, "fonts": per_font})

    return {
        "target": data["target"],
        "flyer": data["flyer"],
        "rendered": rendered,
        "fonts": fonts_out,
        "pages": pages,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build font-comparison artifacts.")
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="skip Scribus rendering even when it is available",
    )
    args = parser.parse_args(argv)

    data = font_variants.load_alternatives()
    flyer_dir = ROOT / "templates" / data["flyer"]
    if not (flyer_dir / "template.sla").exists():
        print(f"FATAL: flyer template not found: {flyer_dir}", file=sys.stderr)
        return 1

    do_render = not args.no_render and scribus_available()
    if not do_render:
        reason = "--no-render" if args.no_render else "scribus not on PATH"
        print(
            f"[fonts_compare] rendering skipped ({reason}). "
            "Variant SLAs + schriften.json are still produced; run "
            "bin/render-gallery in the dev container to render the PDFs/PNGs."
        )
    else:
        install_fonts(data)

    slas = generate_variant_slas(data, flyer_dir)

    renders: dict[str, dict] = {}
    if do_render:
        for entry in data["fonts"]:
            slug = entry["slug"]
            out_dir = flyer_dir / "fonts" / slug
            render = render_variant(slug, slas[slug], out_dir)
            mirror_to_public(slug, render)
            renders[slug] = render

    payload = build_data(data, renders, rendered=do_render)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    with open(SITE_DATA, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[fonts_compare] wrote {_rel(SITE_DATA)} ({len(payload['pages'])} page(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
