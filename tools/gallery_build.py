#!/usr/bin/env python3
"""Walk templates/, copy gallery artifacts to site/public/templates/<id>/, and
write Astro frontmatter for each.

Issue #4: rendering moved to bin/render-gallery (which the maintainer runs
locally before committing). This script is now copy-only and fails loudly if
expected committed artifacts are missing for a template — that signals the
maintainer forgot to run bin/render-gallery before pushing.

For each templates/<id>/ directory:
  - Reads meta.yml
  - Globs committed preview.pdf + page-*.png (non-family) or per-size
    <code>.sla/.pdf/<code>-page-*.png (family) from templates/<id>/
  - Copies them to site/public/templates/<id>/
  - Writes site/src/content/templates/<id>.md with frontmatter from meta.yml
  - Embeds README.md in the content if present

If any expected artifact is missing, exits 1 with a clear FATAL message that
directs the maintainer to run bin/render-gallery locally first.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
SITE_CONTENT = ROOT / "site" / "src" / "content" / "templates"
SITE_PUBLIC = ROOT / "site" / "public" / "templates"


def _fail_missing(tid: str, sla: Path, pdf: Path, pngs: list) -> None:
    """Exit with a FATAL message when required gallery artifacts are missing."""
    sys.exit(
        f"FATAL: gallery artifacts missing for template '{tid}':\n"
        f"  SLA exists:  {sla.exists()}  ({sla})\n"
        f"  PDF exists:  {pdf.exists()}  ({pdf})\n"
        f"  PNG count:   {len(pngs)}  (glob: {sla.parent}/page-*.png)\n"
        f"\nThis script (tools/gallery_build.py) is copy-only after issue #4.\n"
        f"Run `bin/render-gallery` locally to produce these artifacts, then\n"
        f"`git add templates/ site/public/ && git commit`."
    )


def process_template(tdir: Path) -> dict | None:
    """Process one template directory. Returns frontmatter dict or None on skip."""
    meta_path = tdir / "meta.yml"
    if not meta_path.exists():
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    if not isinstance(meta, dict):
        return None
    tid = meta["id"]
    is_family = meta.get("type") == "family"

    public_dir = SITE_PUBLIC / tid
    public_dir.mkdir(parents=True, exist_ok=True)

    if is_family:
        downloads = []
        previews = []
        for size in meta.get("sizes", []):
            code = size["code"]
            sla = tdir / f"{code}.sla"
            pdf = tdir / f"{code}.pdf"
            page_pngs = sorted(tdir.glob(f"{code}-page-*.png"))
            if not (sla.exists() and pdf.exists() and page_pngs):
                _fail_missing(tid, sla, pdf, page_pngs)
            shutil.copy(sla, public_dir / sla.name)
            shutil.copy(pdf, public_dir / pdf.name)
            for p in page_pngs:
                shutil.copy(p, public_dir / p.name)
            downloads.append({
                "label": f"{size['format']} ({size['mm'][0]}×{size['mm'][1]}mm)",
                "sla": f"/templates/{tid}/{code}.sla",
                "pdf": f"/templates/{tid}/{code}.pdf",
            })
            previews.append({
                "label": size["format"],
                "src": f"/templates/{tid}/{page_pngs[0].name}",
            })
        meta["_downloads"] = downloads
        meta["_previews"] = previews
    else:
        sla = tdir / "template.sla"
        pdf = tdir / "preview.pdf"
        page_pngs = sorted(tdir.glob("page-*.png"))
        if not (sla.exists() and pdf.exists() and page_pngs):
            _fail_missing(tid, sla, pdf, page_pngs)
        shutil.copy(sla, public_dir / "template.sla")
        shutil.copy(pdf, public_dir / "preview.pdf")
        for p in page_pngs:
            shutil.copy(p, public_dir / p.name)
        meta["_downloads"] = [{
            "label": "Vollständig (SLA + PDF)",
            "sla": f"/templates/{tid}/template.sla",
            "pdf": f"/templates/{tid}/preview.pdf",
        }]
        meta["_previews"] = [
            {"label": f"Seite {i+1}", "src": f"/templates/{tid}/{p.name}"}
            for i, p in enumerate(page_pngs)
        ]
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
