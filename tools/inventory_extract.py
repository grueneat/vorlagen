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
    2. Glob ``<originals_dir>/*<slug-stem>*/*.idml`` requiring an exact
       basename-prefix match against the full slug stem.

    The fallback (#2) is intentionally strict (review fix F11). The previous
    implementation matched on ``slug.split()[0]`` (i.e. "26" for slug
    "26-03-leporello-..."), which would happily match a different template
    "26-04-foo-bar/foo.idml". Worse, when nothing matched it returned
    ``candidates[0]`` — silently the wrong IDML.

    We now require the IDML's basename (lowercased, hyphen-normalised) to
    start with the slug's leading numeric prefix AND share at least the
    first three slug words. If nothing matches, raise FileNotFoundError.
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

    # Fallback: glob originals/*/*.idml. Require a meaningful overlap
    # between the slug and the candidate basename — not just the first
    # space-delimited word.
    candidates = sorted(originals_dir.glob("*/*.idml"))
    if not candidates:
        raise FileNotFoundError(
            f"Could not resolve IDML for slug {slug!r}: "
            f"meta.yml missing/empty AND no .idml files under {originals_dir}"
        )

    def _norm(s: str) -> str:
        return s.lower().replace("-", " ").replace("_", " ")

    slug_words = _norm(slug).split()
    # Need at least the first 3 tokens to align (e.g. "26 03 leporello").
    min_prefix = " ".join(slug_words[:3]) if len(slug_words) >= 3 else _norm(slug)
    for c in candidates:
        cand_norm = _norm(c.stem)
        # cand_norm e.g. "26 03 leporello z falz 99x210 6 seitig zweigeteiltes cover"
        if cand_norm.startswith(min_prefix):
            return c
    raise FileNotFoundError(
        f"Could not resolve IDML for slug {slug!r}: no IDML in "
        f"{originals_dir} matches slug prefix {min_prefix!r}. "
        f"Set meta.yml::idml_source or rename the IDML to match the slug."
    )


def _join_text_runs(idml_inv: Inventory, build_data: dict, sla_data: dict,
                    pdf_words: WordsBlock) -> TextRunBucket:
    """Populate (idml_count, build_py_count, sla_itext_count, pdf_word_count)
    per paragraph-style bucket and compute set-equality flag.

    Normalisation contract (review fix F2 + F3):
    - IDML buckets are keyed on ``ParagraphStyle/<Self>`` names; we slugify
      via ``_idml_paragraph_style_slug`` so they line up with the
      ``idml/<slug>`` names build.py and the SLA both use.
    - build.py and SLA buckets are already keyed on ``idml/<slug>`` so they
      pass through verbatim.
    - The bucket emitted to YAML keeps the IDML name as ``style`` (it's the
      first-class identity per the schema), but the merge happens on the
      slugified form.
    """
    # Normalise every IDML bucket by mapping its IDML name → slug. We keep the
    # original IDML-side display name as the bucket's ``style`` field because
    # that's the ground-truth identity for the gate.
    norm_idml: dict[str, TextRunByStyle] = {}
    for b in idml_inv.text_runs.by_paragraph_style:
        slug = _idml_paragraph_style_slug(b.style)
        norm_idml[slug] = b

    # build.py side: count Run entries per paragraph_style (already slugified)
    # and remember the per-style text content for set-equality reporting.
    bp_counts: dict[str, int] = {}
    bp_texts: dict[str, set[str]] = {}
    for r in build_data.get("text_runs", []):
        ps = r.get("paragraph_style") or ""
        bp_counts[ps] = bp_counts.get(ps, 0) + 1
        bp_texts.setdefault(ps, set()).add(r.get("text", ""))

    # SLA-side: per-pstyle ITEXT count from walk_sla, keyed on ``idml/<slug>``.
    sla_counts = sla_data.get("itext_by_pstyle", {})

    # Merge by slug, but emit the IDML display name as ``style``.
    all_slugs = set(norm_idml) | set(bp_counts) | set(sla_counts)
    by_style: list[TextRunByStyle] = []
    for slug in sorted(all_slugs):
        idml_bucket = norm_idml.get(slug)
        style_label = idml_bucket.style if idml_bucket else slug
        entry = TextRunByStyle(
            style=style_label,
            idml_count=idml_bucket.idml_count if idml_bucket else 0,
            build_py_count=bp_counts.get(slug, 0),
            sla_itext_count=sla_counts.get(slug, 0),
            pdf_word_count=0,  # per-style PDF word join is v2 territory
        )
        by_style.append(entry)

    # Set-equality: per the contract, every IDML-side text-run's text content
    # must also exist in build.py. The font + fontsize tuple would be ideal,
    # but the IDML walker reads font family only (e.g. "Gotham Narrow") while
    # build.py's Run() carries "family + style" (e.g. "Gotham Narrow Ultra"),
    # so a strict (text, font, fontsize) subset would always fail.
    # The set-equality check therefore runs on the canonicalised TEXT content
    # — which is what catches the "agent dropped a word" failure mode. The
    # full tuples are still exposed via ``idml_runs`` / ``build_py_runs`` so
    # downstream tools can do tighter checks if/when the font normalisation
    # converges. See issue #40 review F3.
    idml_runs_list = list(idml_inv.text_runs.idml_runs) if hasattr(
        idml_inv.text_runs, "idml_runs"
    ) else []

    def _normalize_text(s: str) -> str:
        # Collapse runs of whitespace AND strip the layout glyphs IDML packs
        # into a single <Content> (tabs around bullets, no-break spaces) so
        # an IDML "\t•\tLia vellam" doesn't false-mismatch against build.py's
        # split Run('•') + Run('', sep='tab') + Run('Lia vellam').
        s = (s or "").replace("\t", " ").replace(" ", " ")
        return " ".join(s.split())

    def _word_tokens(s: str) -> frozenset:
        # Last-resort containment: every non-bullet word from the IDML run
        # must appear somewhere in build.py's concatenated text. Used as a
        # subset check when whole-string equality fails because IDML packs
        # tabs/bullets into one Content but build.py splits them across Runs.
        return frozenset(
            tok for tok in _normalize_text(s).split()
            if tok and tok not in {"•", "·", "-", "–", "—"}
        )

    idml_texts_set = {_normalize_text(r.text if hasattr(r, "text") else r.get("text", ""))
                      for r in idml_runs_list}
    idml_texts_set.discard("")
    bp_texts_set = {_normalize_text(r.get("text", ""))
                    for r in build_data.get("text_runs", [])}
    bp_texts_set.discard("")
    bp_concat_text = " ".join(bp_texts_set)
    if idml_texts_set:
        # Primary: strict whole-string subset.
        if idml_texts_set.issubset(bp_texts_set):
            every_idml_present = True
        else:
            # Fall back to word-level containment for IDML runs that bundle
            # multiple build.py-side Runs into one Content (tab/bullet/Br
            # boundaries). Each IDML run is "present" if all of its content
            # words appear in build.py's concatenated text pool. This still
            # catches "agent dropped a word" because the word-token set on
            # the build.py side would no longer cover it.
            bp_token_pool = _word_tokens(bp_concat_text)
            every_idml_present = all(
                _word_tokens(t).issubset(bp_token_pool)
                for t in idml_texts_set
            )
    else:
        # Fallback when the walker doesn't supply per-run tuples (e.g. legacy
        # snapshots loaded from disk): preserve the old count heuristic.
        every_idml_present = (
            idml_inv.text_runs.total_idml > 0
            and sum(bp_counts.values()) >= idml_inv.text_runs.total_idml
        )

    # Flattened build_py runs for the comparator's mutation gate.
    from tools.walkers.schema import TextRun as _TextRun
    build_py_runs = [
        _TextRun(
            text=r.get("text", ""),
            font=r.get("font", "") or "",
            fontsize=float(r.get("fontsize") or 0),
            fcolor=r.get("fcolor", "") or "",
            paragraph_style=r.get("paragraph_style", "") or "",
            text_source=r.get("text_source") or "build_py",
        )
        for r in build_data.get("text_runs", [])
    ]

    return TextRunBucket(
        total_idml=idml_inv.text_runs.total_idml,
        by_paragraph_style=by_style,
        every_idml_run_present_in_build_py=every_idml_present,
        build_py_runs=build_py_runs,
        idml_runs=idml_runs_list,
    )


def _join_frames(idml_inv: Inventory, build_data: dict, sla_data: dict,
                 pdf_images: list[dict]) -> Frames:
    """Merge frame rows from each side keyed by ``anname`` (= IDML Self ID).

    For frames that ALSO appear in build.py with the same anname we expose
    both bbox positions. When the anname is missing on either side (a
    re-export drifted Self IDs, or build.py omitted the anname), we fall
    back to a (kind, round(mm_position, 1)) position index — see issue #40
    review F8.
    """

    sla_by_anname = sla_data.get("by_anname", {})

    def _round_pos(p: Optional[list[float]]) -> Optional[tuple]:
        if not p or len(p) < 4:
            return None
        return tuple(round(x, 1) for x in p)

    # Secondary-key join: per RESEARCH.md pitfall #1, IDML Self IDs are not
    # stable across re-exports, so we ALSO build a (kind, mm_position) index
    # for fallback when anname doesn't match between IDML and build.py.
    def _build_pos_index(rows: list[dict]) -> dict[tuple, dict]:
        idx: dict[tuple, dict] = {}
        for r in rows:
            pos = _round_pos(r.get("position_mm"))
            if pos is None:
                continue
            idx[pos] = r
        return idx

    # build.py rows indexed by anname (primary) and position (secondary).
    bp_text = {r["anname"]: r for r in build_data["frames"]["text_frames"] if r.get("anname")}
    bp_text_pos = _build_pos_index(build_data["frames"]["text_frames"])
    bp_image = {r["anname"]: r for r in build_data["frames"]["image_frames"] if r.get("anname")}
    bp_image_pos = _build_pos_index(build_data["frames"]["image_frames"])
    bp_polygon = {r["anname"]: r for r in build_data["frames"]["polygon_frames"] if r.get("anname")}
    bp_polygon_pos = _build_pos_index(build_data["frames"]["polygon_frames"])
    bp_polyline_rows = build_data["frames"].get("polyline_frames", [])

    def _bp_lookup(primary: dict, secondary: dict, anname: str,
                   pos_mm: Optional[list[float]]) -> Optional[dict]:
        """Anname lookup first; fall back to rounded-position lookup.

        Fallback fires when the anname lookup misses (IDML Self drift on
        re-export, or build.py used a synthetic anname). Position rounding
        to 0.1 mm tolerates float wobble across the IDML→DSL transform.
        """
        row = primary.get(anname)
        if row is not None:
            return row
        pos_key = _round_pos(pos_mm)
        return secondary.get(pos_key) if pos_key else None

    # Per-frame ``pdf_image_present`` (review fix F4) — match pdfimages rows
    # to image frames by page + millimetre footprint. The doc-wide
    # "pdf_has_images" boolean previously copied into every row failed to
    # detect "agent dropped one raster placement"; per-frame matching
    # localises the failure to the affected frame.
    pdf_has_images = len(pdf_images) > 0
    # Build per-page lists of (w_mm, h_mm) footprints from pdfimages.
    pdf_footprints_by_page: dict[int, list[tuple[float, float]]] = {}
    for pi in pdf_images:
        x_ppi = pi.get("x_ppi") or 0
        y_ppi = pi.get("y_ppi") or 0
        if not x_ppi or not y_ppi:
            continue
        w_mm = (pi["width"] / x_ppi) * 25.4
        h_mm = (pi["height"] / y_ppi) * 25.4
        pdf_footprints_by_page.setdefault(pi["page"], []).append((w_mm, h_mm))

    # Set of pages that have at least one rastered image.
    pdf_pages_with_images: set[int] = {pi["page"] for pi in pdf_images}

    def _frame_page(frame_pos_mm: Optional[list[float]],
                    page_w_mm: float = 297.0,
                    page_h_mm: float = 210.0) -> Optional[int]:
        """Map a build.py [x,y,w,h] in mm to a 1-indexed PDF page number.

        Anchor template ships landscape A4 (297×210mm) pages. Pages are
        laid out left-to-right along x; one page per 297mm column. Y is
        used as a tiebreaker for multi-row templates (uncommon).
        """
        if not frame_pos_mm or len(frame_pos_mm) < 4:
            return None
        x_mm, y_mm = frame_pos_mm[0], frame_pos_mm[1]
        col = max(0, int(x_mm // page_w_mm))
        row = max(0, int(y_mm // page_h_mm)) if y_mm >= 0 else 0
        # 2-page anchor: col 0 → page 1, col 1 → page 2; multi-row is row*cols+col+1.
        return col + row + 1

    def _match_pdf_image(frame_pos_mm: Optional[list[float]]) -> bool:
        """Return True iff the frame's PDF page contains at least one image.

        This is per-frame (not doc-wide) so the gate catches "agent dropped
        every image on page 2" regressions: the page no longer reports any
        rastered image and pdf_image_present flips to False on every frame
        nominally placed on that page. Geometry-precise matching via
        pdfimages footprints would require placement-on-page metadata that
        pdfimages does not expose; ±2pt size tolerance was tried but the
        rasters carry their intrinsic resolution dimensions (e.g. 4390×2927
        at 167 ppi → 668mm), not their crop-to-frame footprint.
        """
        if not pdf_has_images or not frame_pos_mm:
            return False
        page = _frame_page(frame_pos_mm)
        if page is None:
            return False
        return page in pdf_pages_with_images

    text_frames: list[TextFrame] = []
    for tf in idml_inv.frames.text_frames:
        bp = _bp_lookup(bp_text, bp_text_pos, tf.anname, tf.idml_position_mm)
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
        bp = _bp_lookup(bp_image, bp_image_pos, img.anname, img.idml_position_mm)
        sla_row = sla_by_anname.get(img.anname, {})
        bp_pos = bp.get("position_mm") if bp else None
        image_frames.append(ImageFrame(
            anname=img.anname,
            idml_self=img.idml_self,
            idml_link=img.idml_link,
            idml_position_mm=img.idml_position_mm,
            build_py_image_ref=bp.get("image") if bp else None,
            build_py_position_mm=bp_pos,
            sla_pageobject_present=bool(sla_row.get("present")),
            sla_pfile_present=bool(sla_row.get("pfile")),
            pdf_image_present=_match_pdf_image(bp_pos),
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
            pdf_image_present=_match_pdf_image(bp.get("position_mm")),
            source="build_py",
        ))

    polygon_frames: list[PolygonFrame] = []
    for poly in idml_inv.frames.polygon_frames:
        bp = _bp_lookup(bp_polygon, bp_polygon_pos, poly.anname, poly.idml_position_mm)
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


def _idml_paragraph_style_slug(idml_self: str) -> str:
    """Slugify an IDML ParagraphStyle Self ID to its build.py emit name.

    Mirrors ``tools.idml_to_dsl._idml_style_slug`` exactly so the join lines
    up with the names build.py uses. We strip the leading ``ParagraphStyle/``
    container, then defer to the converter so umlauts (ä→ae etc.), the
    ``$ID/`` InDesign prefix, and the lowercase + alphanum-hyphen rules all
    match build.py 1:1. Returns e.g. ``idml/aufzaehlungen-auf-gruenem-hintergrund``.
    """
    name = idml_self
    # Strip the IDML container prefix; the converter expects the bare name.
    if "/" in name:
        name = name.split("/", 1)[1]
    # Reuse the canonical slugifier so we are byte-identical with build.py.
    from tools.idml_to_dsl import _idml_style_slug
    return _idml_style_slug(name)


def _join_paragraph_styles(idml_inv: Inventory, build_data: dict,
                           sla_data: dict) -> list[ParagraphStyleEntry]:
    """For each IDML ParagraphStyle, report build_py + SLA presence.

    Identity normalisation rules (review fix F2):
    - IDML side is named ``ParagraphStyle/Aufzählungen auf grünem Hintergrund``
      or ``ParagraphStyle/$ID/NormalParagraphStyle``.
    - build.py side emits ``idml/aufzaehlungen-auf-gruenem-hintergrund`` and
      ``idml/normalparagraphstyle`` via ``tools.idml_to_dsl._idml_style_slug``.
    - SLA side stores the build.py name verbatim on ``<trail PARENT=...>``
      elements (e.g. ``idml/aufzaehlungen-auf-gruenem-hintergrund``).

    The old code used ``str.isalnum`` which kept ``ü/ö/ä/ß`` as-is and used
    substring matching against build.py — so an IDML style "Aufzählungen..."
    never matched the ASCII-folded build.py emit. Defer to the converter's
    canonical slugifier for a byte-identical match.
    """
    bp_set = set(build_data.get("add_para_style_names", []))
    sla_set = sla_data.get("sla_styles", set())
    # SLA-side: the iter_styles set includes ``<STYLE NAME="idml/...">`` names
    # AND the PARENT references on ``<trail>`` elements that walk_sla now
    # surfaces. Either source is sufficient for "present in SLA".
    sla_pstyle_refs = set(sla_data.get("itext_by_pstyle", {}).keys())
    sla_combined = {s.lower() for s in sla_set} | {s.lower() for s in sla_pstyle_refs}
    out: list[ParagraphStyleEntry] = []
    for ps in idml_inv.paragraph_styles:
        emitted_slug = _idml_paragraph_style_slug(ps.idml)
        bp_match: Optional[str] = None
        if emitted_slug in bp_set:
            bp_match = emitted_slug
        sla_present = emitted_slug.lower() in sla_combined
        out.append(ParagraphStyleEntry(
            idml=ps.idml,
            build_py=bp_match,
            build_py_extra_pstyle=bp_match is not None,
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
    """Aggregate ``referenced_from_frames`` per asset basename.

    Two reference paths exist on the build.py side:

    1. **External**: frame carries ``image='..../<basename>'`` — join is a
       direct basename lookup against the IDML walker's asset list.
    2. **Embedded**: frame carries ``inline_image_data='<base64...>'`` (the
       walker hashes the payload into ``inline_image_data_sha256``). Match
       the on-disk asset by hashing its bytes and looking up the resulting
       sha256 in the frame map. Without this join every embedded asset
       (gruene-logo-bund-weiss-cmyk.png, bluesky-weiss.png, …) ships with
       ``referenced_from_frames: []`` and the gate can't detect "agent
       stopped emitting the logo" — see review fix F5.
    """
    # Build basename → [anname,...] map from build.py image frames whose
    # ``image=`` kwarg names a file directly.
    refs: dict[str, list[str]] = {}
    # Track the full ``image=`` path per basename so build.py-only assets
    # (e.g. the geometry-derived crops/ derivatives the converter emits) can
    # be checked on disk. The path is authored relative to templates/<slug>/.
    ref_paths: dict[str, str] = {}
    for img in build_data["frames"]["image_frames"]:
        ref = img.get("image") or ""
        anname = img.get("anname") or ""
        if not ref or not anname:
            continue
        basename = Path(ref).name
        refs.setdefault(basename, []).append(anname)
        ref_paths.setdefault(basename, ref)
    # Composite-AI split refs come from the split manifest, not from build.py
    # (the splits enter the document via inline_image_data, no image= ref).
    for basename, annames in _composite_ai_refs(slug, repo_root).items():
        refs.setdefault(basename, []).extend(annames)

    # Embedded-asset join (review fix F5): frames that enter via
    # ``inline_image_data=`` don't carry the asset basename in build.py — but
    # the IDML side knows ``idml_link`` (e.g. "Grüne Logo Bund weiss CMYK.ai")
    # which the links_export.yml manifest maps to the on-disk derivative
    # (e.g. "gruene-logo-bund-weiss-cmyk.png"). We walk IDML image frames
    # that DO have an idml_link, resolve the disk basename via the manifest,
    # and join those annames into the asset row.
    #
    # Read links_export to map original IDML link names → output basenames.
    inline_anname_to_basename: dict[str, str] = {}
    manifest_path = repo_root / "shared" / "assets" / slug / "links_export.yml"
    link_to_outputs: dict[str, list[str]] = {}
    if manifest_path.exists():
        try:
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            for original_name, entry in (manifest.get("assets") or {}).items():
                outputs: list[str] = []
                for k in ("output", "vector_output"):
                    val = (entry or {}).get(k)
                    if val:
                        outputs.append(Path(val).name)
                link_to_outputs[original_name] = outputs
        except Exception:
            link_to_outputs = {}

    from urllib.parse import unquote
    import unicodedata

    # Normalise the manifest's keys to NFC for matching — IDML links come
    # back in NFD form after URL-decoding %CC%88-style combining-diacritic
    # escapes.
    link_to_outputs_nfc = {
        unicodedata.normalize("NFC", k): v for k, v in link_to_outputs.items()
    }

    def _resolve_idml_link(link: str) -> Optional[list[str]]:
        if not link:
            return None
        # URL-decode IDML link (e.g. Gru%CC%88ne -> Grüne).
        cand = unquote(link)
        # Most IDML refs are "file:Links/<name>" — strip Links/ prefix.
        for prefix in ("file:", "file://", "Links/", "./Links/"):
            if cand.startswith(prefix):
                cand = cand[len(prefix):]
        # Strip leading slashes / dot-segments.
        cand = cand.lstrip("/").lstrip("./")
        # IDML links from %CC%88-style escapes decode to NFD form ("u" +
        # combining-diaeresis), while the manifest stores NFC ("ü"). Match
        # case-sensitively in NFC space to bridge the two.
        cand_nfc = unicodedata.normalize("NFC", cand)
        outputs = link_to_outputs_nfc.get(cand_nfc)
        if outputs:
            return outputs
        # Some IDML manifests use the basename only; try basename lookup.
        return link_to_outputs_nfc.get(Path(cand_nfc).name)

    # IDML image frames that are referenced via inline_image_data on the
    # build.py side: those frames have an anname but no `image=` kwarg in
    # build.py. We attribute them to the asset basename via idml_link.
    bp_anname_image_ref: dict[str, Optional[str]] = {}
    bp_anname_inline_sha: dict[str, Optional[str]] = {}
    for img in build_data["frames"]["image_frames"]:
        an = img.get("anname") or ""
        if not an:
            continue
        bp_anname_image_ref[an] = img.get("image")
        bp_anname_inline_sha[an] = img.get("inline_image_data_sha256")

    inline_refs: dict[str, list[str]] = {}
    for img in idml_inv.frames.image_frames:
        an = img.anname
        if not an:
            continue
        # Only consider frames whose build.py side uses inline_image_data
        # (no ``image=`` kwarg). Direct image= refs are already handled above.
        if bp_anname_image_ref.get(an):
            continue
        if not bp_anname_inline_sha.get(an):
            continue
        outputs = _resolve_idml_link(img.idml_link or "")
        if not outputs:
            continue
        for basename in outputs:
            inline_refs.setdefault(basename, []).append(an)

    out: list[AssetEntry] = []
    seen: set[str] = set()
    for a in idml_inv.assets:
        joined = list(refs.get(a.basename, []))
        for an in inline_refs.get(a.basename, []):
            if an not in joined:
                joined.append(an)
        out.append(AssetEntry(
            basename=a.basename,
            on_disk=a.on_disk,
            classified=a.classified,
            referenced_from_frames=joined,
            parent_composite=a.parent_composite,
            sha256=a.sha256,
            byte_length=a.byte_length,
        ))
        seen.add(a.basename)
    # Any build.py-referenced assets we didn't already catch from the manifest.
    # These include the converter's geometry-derived crops/ derivatives, which
    # are real files on disk — resolve the ``image=`` path (authored relative
    # to templates/<slug>/) and check it rather than assuming on_disk=False.
    templates_dir = repo_root / "templates" / slug
    for basename, annames in refs.items():
        if basename in seen:
            continue
        ref = ref_paths.get(basename, "")
        on_disk = False
        if ref:
            candidate = (templates_dir / ref).resolve()
            on_disk = candidate.is_file()
        out.append(AssetEntry(
            basename=basename,
            on_disk=on_disk,
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
            "Where to write the YAML. '-' or 'stdout' writes to stdout "
            "(this is also the default — review fix F10). Pass an explicit "
            "path to write a file; passing the canonical baseline path "
            "(<templates-dir>/<slug>/SCAFFOLD_INVENTORY.yml) overwrites the "
            "committed calibration."
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
    # Review fix F10: default is now stdout. Previously default wrote to
    # <templates-dir>/<slug>/SCAFFOLD_INVENTORY.yml — the same path used as
    # the comparator's --expected baseline. A user running
    # `python3 tools/inventory_extract.py --slug X` to "check the state"
    # silently overwrote the calibrated truth, then the subsequent
    # `inventory_compare --expected ... --actual <fresh>` trivially exited
    # 0. Callers who want to write a file MUST now pass --output explicitly.
    if args.output is None or str(args.output) in ("-", "stdout"):
        sys.stdout.write(yaml_text)
        return 0
    out_path = args.output

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml_text, encoding="utf-8")
    print(f"inventory written → {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
