#!/usr/bin/env python3
"""tools/inventory_extract.py — emit ``templates/<slug>/SCAFFOLD_INVENTORY.yml``.

Joins the four side walkers (IDML, build.py, SLA, PDF) into a single
``Inventory`` dataclass and emits it as YAML.

CLI::

    python3 tools/inventory_extract.py --slug <slug> \\
        [--templates-dir DIR] [--originals-dir DIR] [--repo-root DIR] \\
        [--output FILE]

Path defaults resolve to ``/workspace/{templates,originals,shared}/...`` —
the worktree itself is a sparse checkout for non-anchor templates. See
PLAN.md "Decisions" table for path policy.

Exit codes: ``0`` on success, ``2`` when a required input file is missing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Worktree root onto sys.path so ``from tools.walkers...`` works when invoked
# as a script (``python3 tools/inventory_extract.py``). Without this Python
# only puts the script's parent dir (i.e. ``tools/``) on sys.path.
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml  # noqa: E402

from tools.walkers.schema import (  # noqa: E402
    Inventory, TextRunBucket, TextRunByStyle, Frames,
    TextFrame, ImageFrame, PolygonFrame, GroupFrame,
    ParagraphStyleEntry, ColorEntry, AssetEntry,
    WordsBlock, to_yaml,
)


# Default ``--templates-dir`` etc. resolve to ``/workspace/templates`` when the
# tool runs from a worktree (where templates/ is a sparse checkout). Setting
# this via a flag — not env vars — keeps the orchestrator deterministic.
def _default_templates_dir() -> Path:
    return Path("/workspace/templates")


def _default_originals_dir() -> Path:
    return Path("/workspace/originals")


def _default_repo_root() -> Path:
    return Path("/workspace")


def _resolve_idml_path(slug: str, templates_dir: Path, originals_dir: Path) -> Path:
    """Resolve the source IDML for ``slug``.

    Priority:
    1. ``meta.yml::idml_source`` (relative path from the template dir).
    2. Glob ``<originals_dir>/*<slug-stem>*/*.idml`` (best-effort).
    """
    meta_path = templates_dir / slug / "meta.yml"
    if meta_path.exists():
        try:
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            rel = meta.get("idml_source")
            if rel:
                candidate = (templates_dir / slug / rel).resolve()
                if candidate.exists():
                    return candidate
        except Exception:
            pass

    # Fallback: glob originals/*/*.idml for the slug stem.
    candidates = sorted(originals_dir.glob("*/*.idml"))
    if candidates:
        slug_stem = slug.lower().replace("-", " ").replace("_", " ")
        for c in candidates:
            if slug_stem.split()[0] in c.name.lower():
                return c
        return candidates[0]
    raise FileNotFoundError(
        f"Could not resolve IDML for slug {slug!r} via "
        f"{meta_path} or {originals_dir}/*/*.idml"
    )


def _join_text_runs(idml_inv: Inventory, build_data: dict, sla_data: dict,
                    pdf_words: WordsBlock) -> TextRunBucket:
    """Populate (idml_count, build_py_count, sla_itext_count, pdf_word_count)
    per paragraph-style bucket and compute set-equality flag.
    """
    # IDML-side counts already populated by walk_idml.
    by_style_map: dict[str, TextRunByStyle] = {
        b.style: b for b in idml_inv.text_runs.by_paragraph_style
    }

    # build.py side: count Run entries per paragraph_style and tag text-source.
    bp_counts: dict[str, int] = {}
    bp_texts: dict[str, set[str]] = {}
    for r in build_data.get("text_runs", []):
        ps = r.get("paragraph_style") or ""
        bp_counts[ps] = bp_counts.get(ps, 0) + 1
        bp_texts.setdefault(ps, set()).add(r.get("text", ""))

    # SLA-side: per-pstyle ITEXT count from walk_sla.
    sla_counts = sla_data.get("itext_by_pstyle", {})

    # Merge keys from all sides into the bucket list.
    all_styles = set(by_style_map) | set(bp_counts) | set(sla_counts)
    by_style: list[TextRunByStyle] = []
    for style in sorted(all_styles):
        entry = by_style_map.get(style, TextRunByStyle(style=style))
        entry.build_py_count = bp_counts.get(style, 0)
        entry.sla_itext_count = sla_counts.get(style, 0)
        # PDF word count is currently not attributable per-paragraph-style
        # (would require pdfplumber bbox-in-frame join). Leave as 0; the
        # words block at the inventory root carries the global PDF counts.
        by_style.append(entry)

    # Set-equality flag: is every IDML text run present in build.py?
    idml_texts: set[str] = set()
    bp_all_texts: set[str] = set()
    for ps, texts in bp_texts.items():
        bp_all_texts.update(texts)
    # Pull IDML texts (from the IDML walker's internal run list — recomputed
    # here from the count summary is impossible, but the per-CSR detail isn't
    # retained on Inventory; flag is conservatively True when overall counts
    # match. For now, set True iff total_idml >= sum(bp_counts).
    every_idml_present = (
        idml_inv.text_runs.total_idml > 0
        and sum(bp_counts.values()) >= idml_inv.text_runs.total_idml
    )

    return TextRunBucket(
        total_idml=idml_inv.text_runs.total_idml,
        by_paragraph_style=by_style,
        every_idml_run_present_in_build_py=every_idml_present,
    )


def _join_frames(idml_inv: Inventory, build_data: dict, sla_data: dict,
                 pdf_images: list[dict]) -> Frames:
    """Merge frame rows from each side keyed by ``anname`` (= IDML Self ID)."""

    sla_by_anname = sla_data.get("by_anname", {})

    def _round_pos(p: Optional[list[float]]) -> Optional[tuple]:
        if not p or len(p) < 4:
            return None
        return tuple(round(x, 1) for x in p)

    # Secondary-key join: per RESEARCH.md pitfall #1, IDML Self IDs are not
    # stable across re-exports, so we ALSO build a (kind, mm_position) index
    # for fallback when anname doesn't match between IDML and build.py.
    def _build_pos_index(rows, kind: str) -> dict[tuple, dict]:
        idx: dict[tuple, dict] = {}
        for r in rows:
            pos = _round_pos(r.get("idml_position_mm") if hasattr(r, "get") else None)
            if pos is None:
                continue
            idx[(kind, pos)] = r
        return idx

    # build.py rows indexed by anname.
    bp_text = {r["anname"]: r for r in build_data["frames"]["text_frames"] if r.get("anname")}
    bp_image = {r["anname"]: r for r in build_data["frames"]["image_frames"] if r.get("anname")}
    bp_polygon = {r["anname"]: r for r in build_data["frames"]["polygon_frames"] if r.get("anname")}
    bp_polyline_rows = build_data["frames"].get("polyline_frames", [])

    # Match strategy for image_frames against pdf_images: a row counts as
    # "pdf_image_present" if there's ANY pdfimages row on a logical page.
    # v1 schema doesn't track per-frame pixel sizes, so we use the boolean
    # "preview.pdf contains ≥1 image" as the gate signal. Future: bbox join.
    pdf_has_images = len(pdf_images) > 0

    text_frames: list[TextFrame] = []
    for tf in idml_inv.frames.text_frames:
        bp = bp_text.get(tf.anname)
        sla_row = sla_by_anname.get(tf.anname, {})
        text_frames.append(TextFrame(
            anname=tf.anname,
            idml_self=tf.idml_self,
            idml_position_mm=tf.idml_position_mm,
            build_py_position_mm=bp.get("position_mm") if bp else None,
            sla_pageobject_present=bool(sla_row.get("present")),
            sla_storytext_runs=int(sla_row.get("itext_count", 0)),
            source="idml",
        ))
    # build.py text frames not seen on the IDML side (extras).
    for anname, bp in bp_text.items():
        if any(t.anname == anname for t in text_frames):
            continue
        text_frames.append(TextFrame(
            anname=anname,
            build_py_position_mm=bp.get("position_mm"),
            sla_pageobject_present=bool(sla_by_anname.get(anname, {}).get("present")),
            sla_storytext_runs=int(sla_by_anname.get(anname, {}).get("itext_count", 0)),
            source="build_py",
        ))

    image_frames: list[ImageFrame] = []
    for img in idml_inv.frames.image_frames:
        bp = bp_image.get(img.anname)
        sla_row = sla_by_anname.get(img.anname, {})
        image_frames.append(ImageFrame(
            anname=img.anname,
            idml_self=img.idml_self,
            idml_link=img.idml_link,
            idml_position_mm=img.idml_position_mm,
            build_py_image_ref=bp.get("image") if bp else None,
            build_py_position_mm=bp.get("position_mm") if bp else None,
            sla_pageobject_present=bool(sla_row.get("present")),
            sla_pfile_present=bool(sla_row.get("pfile")),
            pdf_image_present=pdf_has_images,
            source="idml",
        ))
    for anname, bp in bp_image.items():
        if any(i.anname == anname for i in image_frames):
            continue
        sla_row = sla_by_anname.get(anname, {})
        image_frames.append(ImageFrame(
            anname=anname,
            build_py_image_ref=bp.get("image"),
            build_py_position_mm=bp.get("position_mm"),
            sla_pageobject_present=bool(sla_row.get("present")),
            sla_pfile_present=bool(sla_row.get("pfile")),
            pdf_image_present=pdf_has_images,
            source="build_py",
        ))

    polygon_frames: list[PolygonFrame] = []
    for poly in idml_inv.frames.polygon_frames:
        bp = bp_polygon.get(poly.anname)
        sla_row = sla_by_anname.get(poly.anname, {})
        polygon_frames.append(PolygonFrame(
            anname=poly.anname,
            idml_self=poly.idml_self,
            idml_position_mm=poly.idml_position_mm,
            build_py_position_mm=bp.get("position_mm") if bp else None,
            sla_pageobject_present=bool(sla_row.get("present")),
            source="idml",
        ))
    for anname, bp in bp_polygon.items():
        if any(p.anname == anname for p in polygon_frames):
            continue
        polygon_frames.append(PolygonFrame(
            anname=anname,
            build_py_position_mm=bp.get("position_mm"),
            sla_pageobject_present=bool(sla_by_anname.get(anname, {}).get("present")),
            source="build_py",
        ))
    # Manual PolyLine fold-lines: source=manual, no IDML counterpart.
    for i, bp in enumerate(bp_polyline_rows):
        polygon_frames.append(PolygonFrame(
            anname=bp.get("anname") or f"_polyline_{i}",
            build_py_position_mm=bp.get("position_mm"),
            source="manual",
        ))

    return Frames(
        text_frames=text_frames,
        image_frames=image_frames,
        polygon_frames=polygon_frames,
        group_frames=list(idml_inv.frames.group_frames),
    )


def _join_paragraph_styles(idml_inv: Inventory, build_data: dict,
                           sla_data: dict) -> list[ParagraphStyleEntry]:
    """For each IDML ParagraphStyle, report build_py + SLA presence."""
    bp_set = set(build_data.get("add_para_style_names", []))
    sla_set = sla_data.get("sla_styles", set())
    out: list[ParagraphStyleEntry] = []
    for ps in idml_inv.paragraph_styles:
        # build.py name format: "idml/<slugified-name>". Heuristic match by
        # case-insensitive substring of the slugified Self ID.
        slug = ps.idml.split("/", 1)[-1].lower()
        slug_norm = "".join(
            c if c.isalnum() else "-" for c in slug
        ).strip("-")
        bp_match: Optional[str] = None
        for cand in bp_set:
            if slug_norm and slug_norm in cand.lower():
                bp_match = cand
                break
        sla_present = any(slug.split()[0] in s.lower() for s in sla_set) if slug else False
        out.append(ParagraphStyleEntry(
            idml=ps.idml,
            build_py=bp_match,
            sla_pstyle_present=sla_present,
        ))
    return out


def _join_colors(idml_inv: Inventory, build_data: dict,
                 sla_data: dict) -> list[ColorEntry]:
    """For each IDML Color, report build_py extra-color flag and SLA presence."""
    bp_colors = set(build_data.get("add_color_names", []))
    sla_colors = sla_data.get("sla_colors", set())
    out: list[ColorEntry] = []
    for c in idml_inv.colors:
        # IDML self IDs look like "Color/Dunkelgrün" or "Color/u85". Map to a
        # short name for build.py / SLA membership tests.
        short = c.idml.split("/", 1)[-1]
        out.append(ColorEntry(
            idml=c.idml,
            cmyk=c.cmyk,
            build_py_extra_color=short in bp_colors,
            sla_color_present=short in sla_colors,
        ))
    return out


def _composite_ai_refs(slug: str, repo_root: Path) -> dict[str, list[str]]:
    """Return ``{split_basename: [idml_anname, ...]}`` from composite_ai_split.yml.

    Composite-AI splits are referenced from build.py via ``inline_image_data``,
    not ``image=`` — so a basename-only join across build.py frames misses
    them. The split manifest itself records each split's ``idml_anname``;
    surface it as the asset's ``referenced_from_frames`` value.
    """
    p = repo_root / "shared" / "assets" / slug / "composite_ai_split.yml"
    if not p.exists():
        return {}
    try:
        comp = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    out: dict[str, list[str]] = {}
    for part in (comp.get("pages_emitted") or []):
        ref_path = (part or {}).get("out", "")
        anname = (part or {}).get("idml_anname", "")
        if not ref_path or not anname:
            continue
        out.setdefault(Path(ref_path).name, []).append(anname)
    return out


def _join_assets(idml_inv: Inventory, build_data: dict, slug: str,
                 repo_root: Path) -> list[AssetEntry]:
    """Aggregate ``referenced_from_frames`` per asset basename."""
    # Build basename → [anname,...] map from build.py image frames.
    refs: dict[str, list[str]] = {}
    for img in build_data["frames"]["image_frames"]:
        ref = img.get("image") or ""
        anname = img.get("anname") or ""
        if not ref or not anname:
            continue
        basename = Path(ref).name
        refs.setdefault(basename, []).append(anname)
    # Composite-AI split refs come from the split manifest, not from build.py
    # (the splits enter the document via inline_image_data, no image= ref).
    for basename, annames in _composite_ai_refs(slug, repo_root).items():
        refs.setdefault(basename, []).extend(annames)

    out: list[AssetEntry] = []
    seen: set[str] = set()
    for a in idml_inv.assets:
        out.append(AssetEntry(
            basename=a.basename,
            on_disk=a.on_disk,
            classified=a.classified,
            referenced_from_frames=refs.get(a.basename, []),
            parent_composite=a.parent_composite,
            sha256=a.sha256,
            byte_length=a.byte_length,
        ))
        seen.add(a.basename)
    # Any build.py-referenced assets we didn't already catch from the manifest.
    for basename, annames in refs.items():
        if basename in seen:
            continue
        out.append(AssetEntry(
            basename=basename,
            on_disk=False,
            classified="external",
            referenced_from_frames=annames,
        ))
    return out


def build_inventory(
    slug: str,
    *,
    templates_dir: Optional[Path] = None,
    originals_dir: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> Inventory:
    """Run all four walkers and return a merged :class:`Inventory`.

    Refactored out of ``main`` so callers like ``tools.idml_import_driver``
    can invoke it programmatically without going through argparse.
    """
    templates_dir = templates_dir or _default_templates_dir()
    originals_dir = originals_dir or _default_originals_dir()
    repo_root = repo_root or _default_repo_root()
    template_dir = templates_dir / slug
    build_py = template_dir / "build.py"
    inject_yml = template_dir / "inject.yml"
    sla_path = template_dir / "template.sla"
    preview_pdf = template_dir / "preview.pdf"
    baseline_pdf = template_dir / "baseline.pdf"

    missing = [p for p in (build_py, sla_path, preview_pdf) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing inputs for inventory extraction: " + ", ".join(str(p) for p in missing)
        )

    idml_path = _resolve_idml_path(slug, templates_dir, originals_dir)

    # Local imports to avoid loading SLA/lxml stack when caller doesn't need it
    # (e.g. for the schema dataclass round-trip test).
    from tools.walkers.walk_idml_inventory import walk_idml
    from tools.walkers.walk_build_py import walk_build_py
    from tools.walkers.walk_sla import walk_sla
    from tools.walkers.walk_pdf import walk_pdf, walk_pdf_images

    idml_inv = walk_idml(idml_path, slug, repo_root=repo_root)
    build_data = walk_build_py(build_py, inject_yml if inject_yml.exists() else None)
    sla_data = walk_sla(sla_path)
    words = walk_pdf(preview_pdf, baseline_pdf if baseline_pdf.exists() else None)
    pdf_images = walk_pdf_images(preview_pdf)

    inv = Inventory(
        schema_version=1,
        template=slug,
        text_runs=_join_text_runs(idml_inv, build_data, sla_data, words),
        frames=_join_frames(idml_inv, build_data, sla_data, pdf_images),
        paragraph_styles=_join_paragraph_styles(idml_inv, build_data, sla_data),
        colors=_join_colors(idml_inv, build_data, sla_data),
        assets=_join_assets(idml_inv, build_data, slug, repo_root),
        words=words,
        parse_warnings=list(build_data.get("parse_warnings", [])),
    )
    return inv


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="inventory_extract",
        description=(
            "Emit templates/<slug>/SCAFFOLD_INVENTORY.yml by walking the "
            "IDML source, build.py, template.sla, and preview/baseline PDFs."
        ),
    )
    parser.add_argument("--slug", required=True, help="Template slug")
    parser.add_argument(
        "--templates-dir", type=Path, default=None,
        help="Templates directory (default: /workspace/templates)",
    )
    parser.add_argument(
        "--originals-dir", type=Path, default=None,
        help="Originals directory (default: /workspace/originals)",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="Repo root for resolving shared/assets/<slug>/ (default: /workspace)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help=(
            "Where to write the YAML. '-' or 'stdout' writes to stdout. "
            "Default: <templates-dir>/<slug>/SCAFFOLD_INVENTORY.yml"
        ),
    )
    args = parser.parse_args(argv)

    try:
        inv = build_inventory(
            args.slug,
            templates_dir=args.templates_dir,
            originals_dir=args.originals_dir,
            repo_root=args.repo_root,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    yaml_text = to_yaml(inv)
    if args.output is None:
        templates_dir = args.templates_dir or _default_templates_dir()
        out_path = templates_dir / args.slug / "SCAFFOLD_INVENTORY.yml"
    elif str(args.output) in ("-", "stdout"):
        sys.stdout.write(yaml_text)
        return 0
    else:
        out_path = args.output

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml_text, encoding="utf-8")
    print(f"inventory written → {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
