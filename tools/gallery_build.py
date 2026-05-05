#!/usr/bin/env python3
"""Walk templates/, generate per-template gallery content for the Astro site.

For each templates/<id>/ folder:
  - Reads meta.yml
  - Renders preview PDF via tools/render.py (if not already there)
  - Generates per-page PNG thumbnails via pdftoppm
  - Writes site/src/content/templates/<id>.md with frontmatter from meta.yml
  - Copies preview PDF and PNGs to site/public/templates/<id>/
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
SITE_CONTENT = ROOT / "site" / "src" / "content" / "templates"
SITE_PUBLIC = ROOT / "site" / "public" / "templates"


def render_pdf(template_dir: Path, sla_path: Path, pdf_path: Path) -> bool:
    """Render an SLA to PDF if PDF is missing or older. Return True on success."""
    if pdf_path.exists() and pdf_path.stat().st_mtime > sla_path.stat().st_mtime:
        return True
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "xvfb-run", "-a", "--server-args=-screen 0 1024x768x24",
        "scribus", "-g", "-ns", "-py", str(ROOT / "tools" / "_export_pdf.py"),
        str(sla_path), str(pdf_path), "screen",
    ]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8",
           "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
    return pdf_path.exists()


def pdf_to_pngs(pdf_path: Path, out_prefix: Path, dpi: int = 80) -> list[Path]:
    """Convert PDF to per-page PNGs at given DPI. Returns sorted list of PNGs."""
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png", str(pdf_path), str(out_prefix)],
        check=False, capture_output=True,
    )
    return sorted(out_prefix.parent.glob(f"{out_prefix.name}-*.png"))


def process_template(tdir: Path) -> dict | None:
    """Process one template directory. Returns frontmatter dict or None on skip."""
    meta_path = tdir / "meta.yml"
    if not meta_path.exists():
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    tid = meta["id"]
    is_family = meta.get("type") == "family"

    public_dir = SITE_PUBLIC / tid
    public_dir.mkdir(parents=True, exist_ok=True)

    if is_family:
        # Family: render each size separately
        downloads = []
        previews = []
        for size in meta.get("sizes", []):
            code = size["code"]
            sla = tdir / f"{code}.sla"
            if not sla.exists():
                continue
            pdf = tdir / f"{code}.pdf"
            render_pdf(tdir, sla, pdf)
            shutil.copy(sla, public_dir / sla.name)
            shutil.copy(pdf, public_dir / pdf.name)
            png_prefix = public_dir / f"{code}-page"
            pngs = pdf_to_pngs(pdf, png_prefix, dpi=40)
            downloads.append({
                "label": f"{size['format']} ({size['mm'][0]}×{size['mm'][1]}mm)",
                "sla": f"/templates/{tid}/{code}.sla",
                "pdf": f"/templates/{tid}/{code}.pdf",
            })
            if pngs:
                previews.append({"label": size["format"],
                                  "src": f"/templates/{tid}/{pngs[0].name}"})
        meta["_downloads"] = downloads
        meta["_previews"] = previews
    else:
        sla = tdir / "template.sla"
        if not sla.exists():
            return None
        pdf = tdir / "preview.pdf"
        render_pdf(tdir, sla, pdf)
        shutil.copy(sla, public_dir / "template.sla")
        shutil.copy(pdf, public_dir / "preview.pdf")
        png_prefix = public_dir / "page"
        pngs = pdf_to_pngs(pdf, png_prefix, dpi=80)
        meta["_downloads"] = [{
            "label": "Vollständig (SLA + PDF)",
            "sla": f"/templates/{tid}/template.sla",
            "pdf": f"/templates/{tid}/preview.pdf",
        }]
        meta["_previews"] = [{"label": f"Seite {i+1}",
                               "src": f"/templates/{tid}/{p.name}"}
                              for i, p in enumerate(pngs)]
    return meta


def main() -> None:
    SITE_CONTENT.mkdir(parents=True, exist_ok=True)
    SITE_PUBLIC.mkdir(parents=True, exist_ok=True)

    for tdir in sorted(TEMPLATES_DIR.iterdir()):
        if not tdir.is_dir() or tdir.name.startswith("_"):
            continue
        meta = process_template(tdir)
        if meta is None:
            continue
        tid = meta["id"]
        # Write markdown content file with YAML frontmatter
        content_path = SITE_CONTENT / f"{tid}.md"
        with open(content_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.safe_dump(meta, f, allow_unicode=True, sort_keys=False)
            f.write("---\n\n")
            # Embed README.md if present
            readme = TEMPLATES_DIR / tid / "README.md"
            if readme.exists():
                f.write(readme.read_text(encoding="utf-8"))
        print(f"[gallery] {tid} → {content_path}")


if __name__ == "__main__":
    main()
