"""tools/experiment_render.py — variant rendering orchestrator (issue #29).

Mirrors the shape of tools/render_pipeline.py. For each hypothesis in
``experiments/<exp-id>/manifest.yml``:

  1. importlib.util loads the variant builder (looking for a callable
     ``render_p2(doc, page) -> None``).
  2. ``variant_scaffold.build_variant_front(variant.render_p2)`` builds
     the full 2-page Document.
  3. Constraint check: only ``brand:inside_page`` (per CONTEXT.md
     resolved uncertainty 4 — variants are research artifacts, brand
     rules are not enforced; structural fit-on-page is). Variants whose
     bbox overshoots the page are dropped from the bag with a clear
     'DROP <slug>: <reason>' log message.
  4. SLA → PDF via render_sla_to_pdf(); _scrub_pdf_metadata() for
     deterministic output.
  5. Rasterise at preview_dpi (=100 for falzflyer per meta.yml) → page-01.png.
     Rasterise at HIRES_DPI=150 → page-01-hires.png. Discard page-02.
  6. Mirror artifacts to site/public/experiments/<exp-id>/<slug>/.
  7. After all variants: write site/src/content/experiments/<exp-id>.md
     and refresh experiments/<exp-id>/manifest.json with _previews.

CLI:

    bin/experiment-render <exp-id> [--only <slug>] [--skip-fonts-check]

Exit codes:
  0  all rendered (or all-but-cleanly-dropped)
  3  brand-fonts gate failed
  4  manifest schema invalid
  5  variant module load error in --only mode
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from render_pipeline import (  # noqa: E402
    HIRES_DPI,
    _scrub_pdf_metadata,
    _verify_brand_fonts,
    _zero_pad_pngs,
)
from visual_diff import rasterise, render_sla_to_pdf  # noqa: E402

PREVIEW_DPI = 100  # falzflyer per templates/kandidat-falzflyer-din-lang/meta.yml:7
SCHEMA_PATH = ROOT / "experiments" / "_schema" / "manifest.schema.yaml"
VARIANT_SCAFFOLD_PATH = (
    ROOT / "templates" / "kandidat-falzflyer-din-lang" / "variant_scaffold.py"
)


# ---------------------------------------------------------------------------
# Manifest load + validation
# ---------------------------------------------------------------------------

def _load_manifest(exp_dir: Path) -> dict:
    yml = exp_dir / "manifest.yml"
    if not yml.exists():
        raise FileNotFoundError(f"manifest not found: {yml}")
    return yaml.safe_load(yml.read_text(encoding="utf-8"))


def _validate_manifest(manifest: dict) -> list[jsonschema.ValidationError]:
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    return sorted(
        jsonschema.Draft202012Validator(schema).iter_errors(manifest),
        key=lambda e: list(e.path),
    )


# ---------------------------------------------------------------------------
# Variant module load
# ---------------------------------------------------------------------------

def _load_variant_module(exp_dir: Path, hypothesis: dict, scaffold_module) -> Any:
    """Load the variant module by relative builder path; default to scaffold."""
    rel = hypothesis["builder"]
    py_path = exp_dir / rel
    if not py_path.exists():
        raise FileNotFoundError(
            f"variant builder not found: {py_path}. Run hypothesis "
            f"generation + variant codegen before render."
        )
    spec = importlib.util.spec_from_file_location(
        f"_variant_{hypothesis['slug']}", py_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Make the variant_scaffold importable from inside variant modules
    # without each one repeating the sys.path dance.
    sys.modules[f"_variant_{hypothesis['slug']}"] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "render_p2"):
        raise AttributeError(
            f"variant {hypothesis['slug']!r} module {rel!r} does not expose "
            f"render_p2(doc, page); add `def render_p2(doc, page): ...`."
        )
    return module


def _load_scaffold():
    spec = importlib.util.spec_from_file_location(
        "variant_scaffold", VARIANT_SCAFFOLD_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["variant_scaffold"] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# inside_page check (the only structural gate variants must clear)
# ---------------------------------------------------------------------------

def _inside_page_violations(doc) -> list:
    """Return any inside_page violations on the doc.

    Pulls the InsidePageRule out of BRAND_CONSTRAINTS by id so we don't
    re-implement the bbox math. Per CONTEXT.md resolved uncertainty 4
    no other brand rule runs on variants.
    """
    from sla_lib.builder import BRAND_CONSTRAINTS

    rule = next((r for r in BRAND_CONSTRAINTS if r.id == "brand:inside_page"), None)
    if rule is None:  # pragma: no cover - defensive
        return []
    primitives = list(doc.iter_all_primitives()) if hasattr(doc, "iter_all_primitives") else []
    return [v for v in rule.check(primitives, doc) if v.severity == "error"]


# ---------------------------------------------------------------------------
# Per-variant pipeline
# ---------------------------------------------------------------------------

def _build_variant_sla(
    *, hypothesis: dict, exp_dir: Path, scaffold,
) -> tuple[Path, list]:
    """Build the variant Document, run inside_page, save SLA. Pre-Scribus
    portion of the pipeline — kept separate so unit tests can exercise it
    without depending on Scribus + xvfb.

    Returns (sla_path, violations). If violations is non-empty the caller
    should DROP the variant.
    """
    variant_dir = exp_dir / "variants" / hypothesis["slug"]
    variant_dir.mkdir(parents=True, exist_ok=True)
    variant_module = _load_variant_module(exp_dir, hypothesis, scaffold)

    doc = scaffold.build_variant_front(variant_module.render_p2)
    violations = _inside_page_violations(doc)
    if violations:
        return variant_dir / "template.sla", violations

    sla_path = variant_dir / "template.sla"
    doc.save(sla_path)
    return sla_path, []


def _render_variant_pngs(
    *, sla_path: Path, variant_dir: Path,
) -> tuple[Path, Path]:
    """Run the SLA->PDF->PNG pipeline. Scribus-dependent."""
    pdf_path = variant_dir / "preview.pdf"
    render_sla_to_pdf(sla_path, pdf_path)
    _scrub_pdf_metadata(pdf_path)

    rasterise(pdf_path, variant_dir / "page", PREVIEW_DPI)
    rasterise(pdf_path, variant_dir / "page-hires", HIRES_DPI)
    _zero_pad_pngs(variant_dir, "page")
    _zero_pad_pngs(variant_dir, "page-hires")

    page1 = variant_dir / "page-01.png"
    page1_hires = variant_dir / "page-hires-01.png"
    final_hires = variant_dir / "page-01-hires.png"
    if page1_hires.exists() and not final_hires.exists():
        page1_hires.rename(final_hires)

    # Discard page-02 (per CONTEXT.md resolved uncertainty 1 we only
    # rasterise page-01; the SLA stays 2-page for full-document fidelity
    # but page-02 of the back side is not part of voting).
    for stale in variant_dir.glob("page-02*.png"):
        stale.unlink()
    for stale in variant_dir.glob("page-hires-02*.png"):
        stale.unlink()

    return page1, final_hires


def _mirror_to_public(variant_dir: Path, public_dir: Path) -> None:
    public_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("page-01.png", "page-01-hires.png"):
        src = variant_dir / fname
        if src.exists():
            shutil.copy2(src, public_dir / fname)


# ---------------------------------------------------------------------------
# Astro content collection mirror
# ---------------------------------------------------------------------------

def _write_content_md(
    *, exp_id: str, manifest_with_previews: dict, content_dir: Path,
) -> Path:
    content_dir.mkdir(parents=True, exist_ok=True)
    out = content_dir / f"{exp_id}.md"
    frontmatter = yaml.safe_dump(
        manifest_with_previews, sort_keys=False, allow_unicode=True,
    )
    body = (
        f"# {exp_id}\n\n"
        f"Auto-generated by `bin/experiment-render`. Do not hand-edit.\n"
    )
    out.write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# CLI orchestration
# ---------------------------------------------------------------------------

def run_render(
    *,
    exp_id: str,
    only: str | None = None,
    skip_fonts_check: bool = False,
    skip_scribus: bool = False,
) -> int:
    """Drive the full render. Returns process-style exit code.

    ``skip_scribus`` is a unit-test escape hatch: when True, the SLA is
    written but render_sla_to_pdf + rasterise are skipped, so the
    pre-Scribus pipeline (manifest validate + module load + SLA write +
    inside_page check) is exercised even on hosts without Scribus/xvfb.
    """
    exp_dir = ROOT / "experiments" / exp_id
    if not exp_dir.exists():
        print(f"FATAL: experiments/{exp_id}/ not found", file=sys.stderr)
        return 4

    manifest = _load_manifest(exp_dir)
    schema_errors = _validate_manifest(manifest)
    if schema_errors:
        for err in schema_errors[:10]:
            ptr = "/" + "/".join(str(p) for p in err.path)
            print(f"FATAL manifest schema: {ptr}: {err.message}", file=sys.stderr)
        return 4

    if not skip_fonts_check:
        _verify_brand_fonts()

    scaffold = _load_scaffold()

    public_root = ROOT / "site" / "public" / "experiments" / exp_id
    content_dir = ROOT / "site" / "src" / "content" / "experiments"

    rendered: list[dict] = []
    dropped: list[tuple[str, str]] = []
    started = time.monotonic()

    hypotheses = manifest["hypotheses"]
    if only:
        hypotheses = [h for h in hypotheses if h["slug"] == only]
        if not hypotheses:
            print(f"FATAL: --only {only!r} not in manifest", file=sys.stderr)
            return 5

    for h in hypotheses:
        slug = h["slug"]
        try:
            sla_path, violations = _build_variant_sla(
                hypothesis=h, exp_dir=exp_dir, scaffold=scaffold,
            )
        except Exception as e:  # noqa: BLE001 - per-variant tolerance
            print(f"DROP {slug}: build error — {e}", file=sys.stderr)
            dropped.append((slug, f"build error: {e}"))
            continue
        if violations:
            messages = "; ".join(v.message for v in violations[:3])
            print(f"DROP {slug}: inside_page — {messages}", file=sys.stderr)
            dropped.append((slug, f"inside_page: {messages}"))
            continue

        if skip_scribus:
            # SLA written, render skipped — used by integration tests on
            # hosts without Scribus.
            print(f"OK {slug}: SLA written (Scribus skipped)")
            enriched = dict(h)
            enriched["_previews"] = {
                "thumb": f"/experiments/{exp_id}/{slug}/page-01.png",
                "hires": f"/experiments/{exp_id}/{slug}/page-01-hires.png",
            }
            rendered.append(enriched)
            continue

        try:
            variant_dir = sla_path.parent
            page1, page1_hires = _render_variant_pngs(
                sla_path=sla_path, variant_dir=variant_dir,
            )
            _mirror_to_public(variant_dir, public_root / slug)
        except Exception as e:  # noqa: BLE001
            print(f"DROP {slug}: scribus/rasterise — {e}", file=sys.stderr)
            dropped.append((slug, f"render error: {e}"))
            continue

        enriched = dict(h)
        enriched["_previews"] = {
            "thumb": f"/experiments/{exp_id}/{slug}/page-01.png",
            "hires": f"/experiments/{exp_id}/{slug}/page-01-hires.png",
        }
        rendered.append(enriched)
        print(f"OK {slug}: {page1.relative_to(ROOT)} + hires")

    # Refresh manifest.json with previews on rendered variants only.
    manifest_out = dict(manifest)
    manifest_out["hypotheses"] = rendered
    manifest_out["_dropped"] = [
        {"slug": s, "reason": r} for (s, r) in dropped
    ]
    (exp_dir / "manifest.json").write_text(
        json.dumps(manifest_out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Astro content collection entry — only when not in --only mode (a
    # partial render shouldn't replace the whole experiment).
    if only is None:
        # Drop _dropped from the frontmatter; it's noise for the page.
        fm = {k: v for k, v in manifest_out.items() if k != "_dropped"}
        _write_content_md(
            exp_id=exp_id, manifest_with_previews=fm, content_dir=content_dir,
        )

    elapsed = time.monotonic() - started
    print(
        f"\nrender {exp_id}: {len(rendered)} ok, {len(dropped)} dropped, "
        f"{elapsed:.1f}s",
    )
    if dropped:
        print("dropped:")
        for slug, reason in dropped:
            print(f"  - {slug}: {reason}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="experiment-render",
        description="Render variant builders into PNG previews (issue #29).",
    )
    ap.add_argument("exp_id", nargs="?", help="Experiment id (kebab-case).")
    ap.add_argument("--only", help="Only render this slug.")
    ap.add_argument("--skip-fonts-check", action="store_true",
                    help="Skip _verify_brand_fonts (DANGEROUS — DejaVu fallback).")
    ap.add_argument("--skip-scribus", action="store_true",
                    help="Skip Scribus/PNG steps; only build SLA. For tests.")
    args = ap.parse_args(argv)

    if not args.exp_id:
        ap.print_help()
        return 0

    return run_render(
        exp_id=args.exp_id,
        only=args.only,
        skip_fonts_check=args.skip_fonts_check,
        skip_scribus=args.skip_scribus,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
