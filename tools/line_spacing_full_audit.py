#!/usr/bin/env python3
"""Exhaustive line-spacing audit — IDML → build.py → SLA → preview.pdf.

For every paragraph in the IDML, resolves the effective authored
leading using InDesign's inheritance rules (CSR > ParaStyle > document
auto-leading × point size), then locates the matching emission in
build.py and the SLA, and finally measures the baseline-to-baseline
gap actually rendered in preview.pdf and baseline.pdf via pdfplumber.

Produces a per-paragraph table with: IDML expected | build.py emitted
| SLA emitted | preview measured | baseline measured | deltas |
classification.

Usage:

    python3 tools/line_spacing_full_audit.py \\
        --slug 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover \\
        --templates-dir /workspace/templates \\
        --originals-dir /workspace/originals \\
        --out-yaml build/validation/<slug>/line_spacing_full_audit.yml \\
        --out-md build/validation/<slug>/line_spacing_full_audit.md
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import statistics
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import yaml

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

_MM_TO_PT = 72.0 / 25.4
_PT_TO_MM = 25.4 / 72.0
_AKI_BELOW_MULTIPLIER = 1.45  # converter's empirical inflation for LeadingModelAkiBelow
_AUTO_LEADING_DEFAULT_PCT = 120  # InDesign default; verified in IDML Preferences.xml


# ---------------------------------------------------------------------------
# IDML side


@dataclass
class IdmlParagraphStyle:
    """A normalised view of a ParagraphStyle from Resources/Styles.xml."""
    self_id: str
    name: str
    based_on: Optional[str]
    point_size: Optional[float]
    leading_pt: Optional[float]      # None = "Auto" or unset
    leading_model: Optional[str]
    grid_alignment: Optional[str]
    applied_font: Optional[str]
    justification: Optional[str]


@dataclass
class IdmlRun:
    """One paragraph's effective values, after IDML inheritance.

    A 'run' here is one ParagraphStyleRange (i.e. one paragraph) — not a
    CharacterStyleRange. Line spacing applies to paragraphs, not chars.
    """
    story_id: str
    paragraph_idx: int
    text_excerpt: str               # first ~60 chars of joined CSR content
    text_full: str                  # full joined text (for matching)
    paragraph_style_name: Optional[str]
    point_size_pt: Optional[float]
    leading_pt_authored: Optional[float]   # raw value or None for Auto
    leading_model: Optional[str]
    grid_alignment: Optional[str]
    effective_leading_pt: float            # post-inheritance, post-auto-leading
    leading_source: str                    # "csr" | "pstyle" | "auto"
    font: Optional[str]


# ---------------------------------------------------------------------------
# build.py / SLA / PDF side


@dataclass
class BuildPyRun:
    """One Run() invocation pulled from build.py's AST."""
    text: str
    fontsize_pt: Optional[float]
    linesp_pt: Optional[float]
    linespmode: Optional[int]
    parastyle_ref: Optional[str]
    frame_anname: Optional[str]      # nearest enclosing TextFrame anname


@dataclass
class SlaItext:
    """One ITEXT element pulled from the SLA."""
    pageobject_anname: Optional[str]
    text: str
    fontsize_pt: Optional[float]
    linesp_pt: Optional[float]
    linespmode: Optional[int]
    parent_style: Optional[str]


@dataclass
class SlaFrameParaSummary:
    """Per-frame paragraph break summary — what every <para>/<trail> says."""
    anname: str
    para_count: int                                   # total para+trail elements
    trail_linesp: Optional[float]                    # the closing trail's LINESP
    trail_linespmode: Optional[int]
    intermediate_para_count_auto: int                # <para> with LINESPMode=1
    intermediate_para_count_fixed: int               # <para> with LINESPMode=2
    inconsistent_pattern: bool                       # True if mid-paras differ from trail


@dataclass
class PdfLinespMeasurement:
    """Measured baseline-to-baseline gap for a frame in a rendered PDF."""
    anname: str
    page_idx: int
    bbox_mm: tuple
    line_count: int
    median_gap_pt: Optional[float]


@dataclass
class AuditRow:
    """One row of the final output table."""
    anname: Optional[str]
    paragraph_style: Optional[str]
    page_idx: Optional[int]
    text_excerpt: str
    idml_point_size_pt: Optional[float]
    idml_leading_authored_pt: Optional[float]
    idml_effective_leading_pt: Optional[float]
    idml_leading_model: Optional[str]
    idml_leading_source: Optional[str]
    build_py_linesp_pt: Optional[float]
    build_py_linespmode: Optional[int]
    sla_linesp_pt: Optional[float]
    sla_linespmode: Optional[int]
    baseline_pdf_gap_pt: Optional[float]
    preview_pdf_gap_pt: Optional[float]
    delta_baseline_vs_idml_pt: Optional[float]
    delta_preview_vs_baseline_pt: Optional[float]
    delta_preview_vs_idml_pt: Optional[float]
    classification: str             # match | drift_minor | drift_major | unmatched_*
    notes: str


# ---------------------------------------------------------------------------
# IDML parsing


def _idml_load_doc_defaults(zf: zipfile.ZipFile) -> dict:
    """Return document-level defaults: auto_leading_pct, default_leading_model."""
    try:
        with zf.open("Resources/Preferences.xml") as fh:
            txt = fh.read().decode("utf-8", errors="replace")
    except KeyError:
        return {"auto_leading_pct": _AUTO_LEADING_DEFAULT_PCT, "leading_model": None}
    out: dict = {"auto_leading_pct": _AUTO_LEADING_DEFAULT_PCT, "leading_model": None}
    m = re.search(r'AutoLeading="([0-9.]+)"', txt)
    if m:
        out["auto_leading_pct"] = float(m.group(1))
    m = re.search(r'LeadingModel="([^"]+)"', txt)
    if m:
        out["leading_model"] = m.group(1)
    return out


def _idml_load_styles(zf: zipfile.ZipFile) -> dict[str, IdmlParagraphStyle]:
    """Return {style_self_id: IdmlParagraphStyle} for every ParagraphStyle."""
    out: dict[str, IdmlParagraphStyle] = {}
    with zf.open("Resources/Styles.xml") as fh:
        root = ET.parse(fh).getroot()
    for ps in root.iter("ParagraphStyle"):
        self_id = ps.get("Self", "")
        name = ps.get("Name", "")
        props = ps.find("Properties")
        leading_pt = None
        leading_model = ps.get("LeadingModel")  # rarely present as attr
        applied_font = None
        based_on = None
        if props is not None:
            leading_el = props.find("Leading")
            if leading_el is not None and leading_el.text:
                txt = leading_el.text.strip()
                if txt.lower() not in ("auto", ""):
                    try:
                        leading_pt = float(txt)
                    except ValueError:
                        pass
            # LeadingModel can be a child element
            lm_el = props.find("LeadingModel")
            if lm_el is not None and lm_el.text:
                leading_model = lm_el.text.strip()
            af_el = props.find("AppliedFont")
            if af_el is not None and af_el.text:
                applied_font = af_el.text.strip()
            bo_el = props.find("BasedOn")
            if bo_el is not None and bo_el.text:
                based_on = bo_el.text.strip()
        ptsize_attr = ps.get("PointSize")
        try:
            point_size = float(ptsize_attr) if ptsize_attr else None
        except ValueError:
            point_size = None
        out[self_id] = IdmlParagraphStyle(
            self_id=self_id,
            name=name,
            based_on=based_on,
            point_size=point_size,
            leading_pt=leading_pt,
            leading_model=leading_model,
            grid_alignment=ps.get("GridAlignment"),
            applied_font=applied_font,
            justification=ps.get("Justification"),
        )
    return out


def _resolve_para_style(
    styles: dict[str, IdmlParagraphStyle], self_id: Optional[str]
) -> Optional[IdmlParagraphStyle]:
    """Walk BasedOn chain to find inherited values."""
    if not self_id:
        return None
    seen = set()
    while self_id and self_id not in seen:
        seen.add(self_id)
        st = styles.get(self_id)
        if not st:
            break
        if (
            st.leading_pt is not None
            or st.point_size is not None
            or st.applied_font is not None
        ):
            return st
        self_id = st.based_on
    return styles.get(self_id) if self_id else None


def _idml_walk_story(
    zf: zipfile.ZipFile,
    story_path: str,
    styles: dict[str, IdmlParagraphStyle],
    doc_defaults: dict,
) -> list[IdmlRun]:
    """Return one IdmlRun per ParagraphStyleRange in the story."""
    out: list[IdmlRun] = []
    story_id = Path(story_path).stem.replace("Story_", "")
    with zf.open(story_path) as fh:
        root = ET.parse(fh).getroot()
    para_idx = 0
    for story in root.iter("Story"):
        for psr in story.iter("ParagraphStyleRange"):
            para_idx += 1
            pstyle_ref = psr.get("AppliedParagraphStyle", "")
            resolved = styles.get(pstyle_ref) or _resolve_para_style(
                styles, pstyle_ref
            )
            csrs = list(psr.iter("CharacterStyleRange"))
            text_parts = []
            csr_pointsize = None
            csr_leading = None
            csr_font = None
            for csr in csrs:
                if csr.get("PointSize") and csr_pointsize is None:
                    try:
                        csr_pointsize = float(csr.get("PointSize"))
                    except ValueError:
                        pass
                # CSR Leading lives in Properties/Leading (child element), not as attr
                props = csr.find("Properties")
                if props is not None:
                    if csr_leading is None:
                        lead_el = props.find("Leading")
                        if lead_el is not None and lead_el.text:
                            txt = lead_el.text.strip()
                            if txt.lower() not in ("auto", ""):
                                try:
                                    csr_leading = float(txt)
                                except ValueError:
                                    pass
                    if csr_font is None:
                        af = props.find("AppliedFont")
                        if af is not None and af.text:
                            csr_font = af.text.strip()
                for content in csr.iter("Content"):
                    if content.text:
                        text_parts.append(content.text)
                # treat <Br/> as soft break for excerpt readability
                for child in csr:
                    if child.tag == "Br":
                        text_parts.append(" ↵ ")
            text_full = "".join(text_parts)
            if not text_full.strip():
                continue  # skip empty paragraphs

            pstyle_pointsize = resolved.point_size if resolved else None
            point_size = csr_pointsize or pstyle_pointsize
            leading_authored = csr_leading
            leading_source = "csr" if leading_authored is not None else None
            if leading_authored is None and resolved is not None:
                leading_authored = resolved.leading_pt
                if leading_authored is not None:
                    leading_source = "pstyle"
            if leading_authored is None:
                # auto-leading
                if point_size is not None:
                    leading_authored = None  # mark unset; effective computed below
                leading_source = "auto"

            leading_model = (resolved.leading_model if resolved else None) or doc_defaults.get(
                "leading_model"
            )

            # Effective leading (what InDesign renders)
            if leading_authored is not None:
                effective = leading_authored
            else:
                pct = doc_defaults.get("auto_leading_pct", _AUTO_LEADING_DEFAULT_PCT)
                effective = (point_size or 0.0) * pct / 100.0

            out.append(
                IdmlRun(
                    story_id=story_id,
                    paragraph_idx=para_idx,
                    text_excerpt=text_full[:80].replace("\n", "·"),
                    text_full=text_full,
                    paragraph_style_name=resolved.name if resolved else (
                        pstyle_ref.split("/")[-1] if pstyle_ref else None
                    ),
                    point_size_pt=point_size,
                    leading_pt_authored=leading_authored,
                    leading_model=leading_model,
                    grid_alignment=resolved.grid_alignment if resolved else None,
                    effective_leading_pt=effective,
                    leading_source=leading_source or "auto",
                    font=csr_font
                    or (resolved.applied_font if resolved else None),
                )
            )
    return out


def _idml_load_textframe_to_story(
    zf: zipfile.ZipFile,
) -> dict[str, dict]:
    """Map TextFrame self → {story_self, page_idx, bbox_pt}.

    Bbox derived from TextFrame ItemTransform + PathPointArray.
    """
    out: dict[str, dict] = {}
    spread_paths = sorted(
        n for n in zf.namelist() if n.startswith("Spreads/Spread_")
    )
    for spread_idx, sp in enumerate(spread_paths):
        with zf.open(sp) as fh:
            root = ET.parse(fh).getroot()
        for spread in root.iter("Spread"):
            for tf in spread.iter("TextFrame"):
                self_id = tf.get("Self", "")
                story_id = tf.get("ParentStory", "")
                # Geometry: rough bbox from path points (Y normalized)
                pts: list[tuple[float, float]] = []
                for pp in tf.iter("PathPointType"):
                    a = pp.get("Anchor", "0 0").split()
                    if len(a) == 2:
                        try:
                            pts.append((float(a[0]), float(a[1])))
                        except ValueError:
                            pass
                if pts:
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    bbox_pt = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
                else:
                    bbox_pt = (0.0, 0.0, 0.0, 0.0)
                out[self_id] = {
                    "story_self": story_id,
                    "page_idx": spread_idx,
                    "bbox_pt": bbox_pt,
                }
    return out


def parse_idml(idml_path: Path) -> tuple[
    list[IdmlRun], dict[str, IdmlParagraphStyle], dict, dict[str, dict]
]:
    with zipfile.ZipFile(idml_path) as zf:
        doc_defaults = _idml_load_doc_defaults(zf)
        styles = _idml_load_styles(zf)
        frame_map = _idml_load_textframe_to_story(zf)
        story_paths = sorted(
            n for n in zf.namelist() if n.startswith("Stories/Story_")
        )
        all_runs: list[IdmlRun] = []
        for sp in story_paths:
            all_runs.extend(_idml_walk_story(zf, sp, styles, doc_defaults))
    return all_runs, styles, doc_defaults, frame_map


# ---------------------------------------------------------------------------
# build.py AST walk


def _ast_kw(call: ast.Call, name: str):
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _ast_literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return None


def _walk_para_styles(tree: ast.AST) -> dict[str, dict]:
    """Map ParaStyle name → {linesp, fontsize, parent} from add_para_style calls."""
    out: dict[str, dict] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = ""
        if isinstance(node.func, ast.Name):
            fn = node.func.id
        elif isinstance(node.func, ast.Attribute):
            fn = node.func.attr
        if fn != "ParaStyle":
            continue
        name = _ast_literal(_ast_kw(node, "name"))
        if not isinstance(name, str):
            continue
        out[name] = {
            "linesp": _ast_literal(_ast_kw(node, "linesp")),
            "fontsize": _ast_literal(_ast_kw(node, "fontsize")),
            "parent": _ast_literal(_ast_kw(node, "parent")),
            "font": _ast_literal(_ast_kw(node, "font")),
            "align": _ast_literal(_ast_kw(node, "align")),
        }
    return out


def _resolve_parastyle_linesp(name: str, registry: dict[str, dict]) -> Optional[float]:
    """Walk parent chain to find first linesp set."""
    seen = set()
    cur = name
    while cur and cur not in seen:
        seen.add(cur)
        st = registry.get(cur)
        if not st:
            return None
        if st.get("linesp") is not None:
            return float(st["linesp"])
        cur = st.get("parent")
    return None


def parse_build_py(
    build_py: Path,
) -> tuple[list[BuildPyRun], dict[str, dict]]:
    """Walk build.py for Run() calls + ParaStyle registry."""
    out: list[BuildPyRun] = []
    text = build_py.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out, {}
    parent_map = {child: parent for parent in ast.walk(tree)
                  for child in ast.iter_child_nodes(parent)}
    para_styles = _walk_para_styles(tree)
    # Map TextFrame call → anname
    textframe_by_id: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ""
            if isinstance(node.func, ast.Name):
                fn = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fn = node.func.attr
            if fn == "TextFrame":
                anname_val = _ast_kw(node, "anname")
                if anname_val is not None:
                    name = _ast_literal(anname_val) or ""
                    textframe_by_id[id(node)] = name
    # Walk Run() — paragraph_style kwarg gives us linesp via the registry
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ""
            if isinstance(node.func, ast.Name):
                fn = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fn = node.func.attr
            if fn != "Run":
                continue
            text_kw = _ast_kw(node, "text")
            run_text = _ast_literal(text_kw) if text_kw else ""
            if not run_text or not isinstance(run_text, str):
                continue
            fontsize = _ast_literal(_ast_kw(node, "fontsize"))
            parastyle = _ast_literal(_ast_kw(node, "paragraph_style"))
            paragraph_attrs = _ast_literal(_ast_kw(node, "paragraph_attrs")) or {}
            linespmode_attr = paragraph_attrs.get("LINESPMode") if isinstance(paragraph_attrs, dict) else None
            linesp_attr = paragraph_attrs.get("LINESP") if isinstance(paragraph_attrs, dict) else None
            # Resolve linesp: paragraph_attrs override > parastyle registry
            linesp_resolved = None
            if linesp_attr is not None:
                try:
                    linesp_resolved = float(linesp_attr)
                except (ValueError, TypeError):
                    pass
            if linesp_resolved is None and isinstance(parastyle, str):
                linesp_resolved = _resolve_parastyle_linesp(parastyle, para_styles)
            # Walk up to find enclosing TextFrame call
            cur = parent_map.get(node)
            frame_anname = None
            while cur is not None:
                if isinstance(cur, ast.Call) and id(cur) in textframe_by_id:
                    frame_anname = textframe_by_id[id(cur)]
                    break
                cur = parent_map.get(cur)
            out.append(BuildPyRun(
                text=run_text,
                fontsize_pt=float(fontsize) if fontsize is not None else None,
                linesp_pt=linesp_resolved,
                linespmode=int(linespmode_attr) if linespmode_attr is not None else None,
                parastyle_ref=parastyle if isinstance(parastyle, str) else None,
                frame_anname=frame_anname,
            ))
    return out, para_styles


# ---------------------------------------------------------------------------
# SLA walk


def _sla_load_styles(root: ET.Element) -> dict[str, dict]:
    """Map STYLE NAME → {LINESP, LINESPMode, FONTSIZE} for SLA-defined pstyles."""
    out: dict[str, dict] = {}
    for s in root.iter("STYLE"):
        name = s.get("NAME") or ""
        if not name:
            continue
        out[name] = {
            "linesp": (
                float(s.get("LINESP")) if s.get("LINESP") else None
            ),
            "linespmode": (
                int(s.get("LINESPMode")) if s.get("LINESPMode") else None
            ),
            "fontsize": (
                float(s.get("FONTSIZE")) if s.get("FONTSIZE") else None
            ),
        }
    return out


def parse_sla_frame_summaries(sla_path: Path) -> dict[str, SlaFrameParaSummary]:
    """Per-frame summary of <para>/<trail> LINESPMode/LINESP, to surface
    'intermediate auto-leading' bug pattern."""
    out: dict[str, SlaFrameParaSummary] = {}
    try:
        tree = ET.parse(sla_path)
    except ET.ParseError:
        return out
    root = tree.getroot()
    for po in root.iter("PAGEOBJECT"):
        anname = po.get("ANNAME") or ""
        if not anname:
            continue
        para_count = 0
        trail_linesp = None
        trail_linespmode = None
        inter_auto = 0
        inter_fixed = 0
        # Collect all para/trail in this PAGEOBJECT in order
        rows = []
        for child in po.iter():
            if child.tag in ("para", "trail"):
                rows.append(child)
        for i, child in enumerate(rows):
            para_count += 1
            lp = child.get("LINESP")
            lm = child.get("LINESPMode")
            is_last = (i == len(rows) - 1) and child.tag == "trail"
            if is_last:
                trail_linesp = float(lp) if lp else None
                trail_linespmode = int(lm) if lm else None
            else:
                if lm == "1":
                    inter_auto += 1
                elif lm == "2":
                    inter_fixed += 1
        inconsistent = (
            trail_linespmode == 2
            and trail_linesp is not None
            and inter_auto > 0  # mid-para uses auto while end uses fixed
        )
        if para_count == 0:
            continue
        out[anname] = SlaFrameParaSummary(
            anname=anname,
            para_count=para_count,
            trail_linesp=trail_linesp,
            trail_linespmode=trail_linespmode,
            intermediate_para_count_auto=inter_auto,
            intermediate_para_count_fixed=inter_fixed,
            inconsistent_pattern=inconsistent,
        )
    return out


def parse_sla(sla_path: Path) -> tuple[list[SlaItext], dict[str, dict]]:
    """Pull ITEXT rows; PAGEOBJECT LINESP overrides; STYLE registry for fallback."""
    out: list[SlaItext] = []
    try:
        tree = ET.parse(sla_path)
    except ET.ParseError as e:
        sys.stderr.write(f"SLA parse error: {e}\n")
        return out, {}
    root = tree.getroot()
    sla_styles = _sla_load_styles(root)
    for po in root.iter("PAGEOBJECT"):
        anname = po.get("ANNAME") or None
        po_linesp = po.get("LINESP")
        po_linespmode = po.get("LINESPMode")
        # Walk in document order. SLA places <para>/<trail> AFTER the run(s)
        # of a paragraph, so we accumulate ITEXTs and apply para/trail attrs
        # retroactively.
        pending: list[SlaItext] = []
        for child in list(po.iter()):
            if child.tag == "ITEXT":
                text = child.get("CH") or ""
                fontsize = child.get("FONTSIZE")
                pending.append(SlaItext(
                    pageobject_anname=anname,
                    text=text,
                    fontsize_pt=float(fontsize) if fontsize else None,
                    linesp_pt=(
                        float(child.get("LINESP")) if child.get("LINESP")
                        else (float(po_linesp) if po_linesp else None)
                    ),
                    linespmode=(
                        int(child.get("LINESPMode")) if child.get("LINESPMode")
                        else (int(po_linespmode) if po_linespmode else None)
                    ),
                    parent_style=child.get("PSTYLE"),
                ))
            elif child.tag in ("para", "trail"):
                parent = child.get("PARENT")
                p_linesp = child.get("LINESP")
                p_linespmode = child.get("LINESPMode")
                for run in pending:
                    if run.parent_style is None and parent:
                        run.parent_style = parent
                    if run.linesp_pt is None and p_linesp:
                        try:
                            run.linesp_pt = float(p_linesp)
                        except ValueError:
                            pass
                    if run.linespmode is None and p_linespmode:
                        try:
                            run.linespmode = int(p_linespmode)
                        except ValueError:
                            pass
                    if run.linesp_pt is None and run.parent_style in sla_styles:
                        lp = sla_styles[run.parent_style].get("linesp")
                        if lp is not None:
                            run.linesp_pt = lp
                    if run.linespmode is None and run.parent_style in sla_styles:
                        lm = sla_styles[run.parent_style].get("linespmode")
                        if lm is not None:
                            run.linespmode = lm
                out.extend(pending)
                pending = []
        # Orphan ITEXTs (rare — no closing para/trail in this PAGEOBJECT)
        for run in pending:
            if run.linesp_pt is None and run.parent_style in sla_styles:
                lp = sla_styles[run.parent_style].get("linesp")
                if lp is not None:
                    run.linesp_pt = lp
        out.extend(pending)
    return out, sla_styles


# ---------------------------------------------------------------------------
# PDF measurements


def measure_pdf_lines_direct(
    pdf: Path,
    frame_bbox_mm: tuple,
    page_idx: int,
) -> tuple[list[dict], list[float]]:
    """Direct word-position measurement (no clustering thresholds).

    Returns (lines, gaps_pt) where:
      lines = [{"top_pt": .., "bottom_pt": .., "x_min": .., "x_max": ..,
                "text": " ".join(words), "word_count": N}, …]
      gaps_pt = list of consecutive (line[i+1].top - line[i].top)

    Groups words by ``top`` coordinate with 0.5pt tolerance — words on the
    same visual line have the same ``top`` from pdfplumber for a given font
    rendering. Avoids the 2pt-gap clustering used by ``measure_pdf_line_gaps``
    which mis-merges adjacent lines of small fonts.
    """
    if pdfplumber is None:
        return [], []
    try:
        with pdfplumber.open(pdf) as doc:
            if page_idx >= len(doc.pages):
                return [], []
            page = doc.pages[page_idx]
            x0 = frame_bbox_mm[0] * _MM_TO_PT
            y0 = frame_bbox_mm[1] * _MM_TO_PT
            x1 = (frame_bbox_mm[0] + frame_bbox_mm[2]) * _MM_TO_PT
            y1 = (frame_bbox_mm[1] + frame_bbox_mm[3]) * _MM_TO_PT
            crop = page.crop((
                max(0, x0 - 2),
                max(0, y0 - 2),
                min(page.width, x1 + 2),
                min(page.height, y1 + 2),
            ))
            words = sorted(
                crop.extract_words(use_text_flow=True),
                key=lambda w: (round(w["top"], 1), w["x0"]),
            )
    except Exception:
        return [], []
    # Group by top with 0.5pt tolerance
    lines: list[dict] = []
    for w in words:
        if lines and abs(w["top"] - lines[-1]["top_pt"]) <= 0.5:
            lines[-1]["text"] += " " + w["text"]
            lines[-1]["x_min"] = min(lines[-1]["x_min"], w["x0"])
            lines[-1]["x_max"] = max(lines[-1]["x_max"], w["x1"])
            lines[-1]["bottom_pt"] = max(lines[-1]["bottom_pt"], w["bottom"])
            lines[-1]["word_count"] += 1
        else:
            lines.append({
                "top_pt": w["top"],
                "bottom_pt": w["bottom"],
                "x_min": w["x0"],
                "x_max": w["x1"],
                "text": w["text"],
                "word_count": 1,
            })
    gaps = [
        round(lines[i + 1]["top_pt"] - lines[i]["top_pt"], 3)
        for i in range(len(lines) - 1)
    ]
    return lines, gaps


def probe_frame(
    anname: str,
    bp_frame_bboxes: dict[str, dict],
    preview: Path,
    baseline: Path,
) -> dict:
    """Direct per-line measurement for one frame; bypasses the clustering
    heuristic. Reports each line's top/bottom and consecutive gaps in
    both PDFs side by side. Used by ``--probe <anname>``."""
    if anname not in bp_frame_bboxes:
        return {"error": f"anname {anname!r} not found in build.py TextFrames"}
    info = bp_frame_bboxes[anname]
    bbox = info["bbox_mm"]
    page_idx = info.get("page", 0)
    out: dict = {
        "anname": anname,
        "bbox_mm": list(bbox),
        "page_idx": page_idx,
    }
    # Use the page assignment recovered from build.py
    for label, pdf in (("preview", preview), ("baseline", baseline)):
        if not pdf.exists():
            continue
        lines, gaps = measure_pdf_lines_direct(pdf, tuple(bbox), page_idx)
        out[f"{label}_lines"] = lines
        out[f"{label}_gaps_pt"] = gaps
        out[f"{label}_line_count"] = len(lines)
        if gaps:
            out[f"{label}_median_gap_pt"] = round(statistics.median(gaps), 3)
            out[f"{label}_mean_gap_pt"] = round(statistics.fmean(gaps), 3)
    if "preview_median_gap_pt" in out and "baseline_median_gap_pt" in out:
        out["delta_preview_vs_baseline_pt"] = round(
            out["preview_median_gap_pt"] - out["baseline_median_gap_pt"], 3
        )
    return out


def measure_pdf_line_gaps(
    pdf: Path,
    frame_bboxes_mm: dict[str, dict],  # anname → {page, bbox_mm}
) -> dict[str, PdfLinespMeasurement]:
    """For each frame, measure median baseline-to-baseline gap in PT."""
    if pdfplumber is None:
        return {}
    out: dict[str, PdfLinespMeasurement] = {}
    try:
        with pdfplumber.open(pdf) as doc:
            pages = doc.pages
            for anname, info in frame_bboxes_mm.items():
                page_idx = info.get("page", 0)
                bbox = info.get("bbox_mm", (0, 0, 0, 0))
                if page_idx >= len(pages):
                    continue
                page = pages[page_idx]
                x0_pt = bbox[0] * _MM_TO_PT
                y0_pt = bbox[1] * _MM_TO_PT
                x1_pt = (bbox[0] + bbox[2]) * _MM_TO_PT
                y1_pt = (bbox[1] + bbox[3]) * _MM_TO_PT
                # crop with small margin
                try:
                    cropped = page.crop(
                        (max(0, x0_pt - 2), max(0, y0_pt - 2),
                         min(page.width, x1_pt + 2),
                         min(page.height, y1_pt + 2))
                    )
                except Exception:
                    continue
                # Extract words; cluster by y position
                words = cropped.extract_words(use_text_flow=True)
                if not words:
                    continue
                # y-position of word top (pdfplumber 'top' coord)
                tops = sorted(w.get("top", 0.0) for w in words)
                # cluster by gaps ≥ 2pt
                clusters: list[float] = [tops[0]]
                for t in tops[1:]:
                    if t - clusters[-1] >= 2.0:
                        clusters.append(t)
                if len(clusters) < 2:
                    out[anname] = PdfLinespMeasurement(
                        anname=anname,
                        page_idx=page_idx,
                        bbox_mm=tuple(bbox),
                        line_count=len(clusters),
                        median_gap_pt=None,
                    )
                    continue
                gaps = [clusters[i+1] - clusters[i] for i in range(len(clusters)-1)]
                # Use median for robustness; clamp obvious outliers
                gaps_robust = [g for g in gaps if g <= max(gaps) * 1.5]
                median_gap = statistics.median(gaps_robust) if gaps_robust else None
                out[anname] = PdfLinespMeasurement(
                    anname=anname,
                    page_idx=page_idx,
                    bbox_mm=tuple(bbox),
                    line_count=len(clusters),
                    median_gap_pt=round(median_gap, 3) if median_gap else None,
                )
    except Exception as e:
        sys.stderr.write(f"pdfplumber error on {pdf}: {e}\n")
    return out


# ---------------------------------------------------------------------------
# Build.py geometry: anname → bbox_mm + page


def parse_build_py_textframe_bboxes(build_py: Path) -> dict[str, dict]:
    """Return {anname: {page, bbox_mm}} for each TextFrame call.

    Page index is recovered by tracing the enclosing ``pageN.add(...)``
    call: the receiver name's trailing digits index the page (page0 → 0,
    page1 → 1, etc.). Falls back to page=0 when the receiver doesn't
    match the pageN pattern.
    """
    out: dict[str, dict] = {}
    text = build_py.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    parent_map = {child: parent for parent in ast.walk(tree)
                  for child in ast.iter_child_nodes(parent)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ""
            if isinstance(node.func, ast.Name):
                fn = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fn = node.func.attr
            if fn != "TextFrame":
                continue
            anname = _ast_literal(_ast_kw(node, "anname"))
            if not anname:
                continue
            x = _ast_literal(_ast_kw(node, "x_mm")) or _ast_literal(_ast_kw(node, "x"))
            y = _ast_literal(_ast_kw(node, "y_mm")) or _ast_literal(_ast_kw(node, "y"))
            w = _ast_literal(_ast_kw(node, "w_mm")) or _ast_literal(_ast_kw(node, "w"))
            h = _ast_literal(_ast_kw(node, "h_mm")) or _ast_literal(_ast_kw(node, "h"))
            if None in (x, y, w, h):
                continue
            # Walk up to find the enclosing pageN.add(...) call
            page = 0
            cur = parent_map.get(node)
            while cur is not None:
                if (
                    isinstance(cur, ast.Call)
                    and isinstance(cur.func, ast.Attribute)
                    and cur.func.attr == "add"
                    and isinstance(cur.func.value, ast.Name)
                ):
                    name = cur.func.value.id
                    if name.startswith("page") and name[4:].isdigit():
                        page = int(name[4:])
                        break
                cur = parent_map.get(cur)
            out[str(anname)] = {
                "page": page,
                "bbox_mm": (float(x), float(y), float(w), float(h)),
            }
    return out


# ---------------------------------------------------------------------------
# Matching


def _normalize_text(s: str) -> str:
    """Aggressive normalization for cross-source text matching."""
    s = s.replace("—", "-").replace("–", "-")
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("↵", "")
    s = s.replace("·", "")
    s = s.replace(" ", " ").replace(" ", " ")
    s = re.sub(r"\s+", " ", s).strip().lower()
    import unicodedata
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()  # collapse-and-strip again after punct removal
    return s


def match_runs(
    idml_runs: list[IdmlRun],
    build_runs: list[BuildPyRun],
    sla_items: list[SlaItext],
) -> list[tuple[Optional[IdmlRun], Optional[BuildPyRun], Optional[SlaItext]]]:
    """Match IDML run ↔ build.py run ↔ SLA itext by text containment.

    Strategy: for each IDML paragraph, find the build.py Run whose normalised
    text appears as a substring (or vice versa). A multi-CSR IDML paragraph
    (e.g. "Das ist die / dreizeilige / Headline") matches against the FIRST
    build.py Run whose text is contained in the IDML concatenation, then
    that build.py Run's enclosing TextFrame anname carries the match for
    the whole paragraph.
    """
    # Pre-normalise every source's text
    bp_norm = [(r, _normalize_text(r.text)) for r in build_runs if r.text]
    sla_norm = [(s, _normalize_text(s.text)) for s in sla_items if s.text]
    def _best_match(idml_text: str, candidates):
        """Pick the candidate with the longest matching prefix/substring.

        - Score 3: candidate text is a prefix of IDML text AND ≥ 8 chars
        - Score 2: IDML text is a prefix of candidate (text_excerpt was truncated)
        - Score 1: candidate text contains IDML text or vice versa (≥ 12 chars)
        Tiebreaker: longer match length wins, then first-seen.
        """
        best = None  # (score, length, item)
        for it, k in candidates:
            if not k:
                continue
            score = 0
            length = 0
            if len(k) >= 6 and idml_text.startswith(k[:min(40, len(k))]):
                score = 3
                length = min(len(k), 40)
            elif len(idml_text) >= 6 and k.startswith(idml_text[:min(40, len(idml_text))]):
                score = 2
                length = min(len(idml_text), 40)
            elif len(k) >= 12 and k in idml_text:
                score = 1
                length = len(k)
            elif len(idml_text) >= 12 and idml_text in k:
                score = 1
                length = len(idml_text)
            if score == 0:
                continue
            if best is None or (score, length) > (best[0], best[1]):
                best = (score, length, it)
        return best[2] if best else None

    matched: list = []
    for idml in idml_runs:
        idml_text = _normalize_text(idml.text_excerpt)
        bp_match = _best_match(idml_text, bp_norm)
        sla_match = _best_match(idml_text, sla_norm)
        matched.append((idml, bp_match, sla_match))
    return matched


# ---------------------------------------------------------------------------
# Audit assembly


def build_audit_rows(
    idml_runs: list[IdmlRun],
    build_runs: list[BuildPyRun],
    sla_items: list[SlaItext],
    preview_meas: dict[str, PdfLinespMeasurement],
    baseline_meas: dict[str, PdfLinespMeasurement],
) -> list[AuditRow]:
    rows: list[AuditRow] = []
    matches = match_runs(idml_runs, build_runs, sla_items)
    for idml, bp, sla in matches:
        anname = (
            (bp.frame_anname if bp else None)
            or (sla.pageobject_anname if sla else None)
        )
        baseline_gap = (
            baseline_meas[anname].median_gap_pt
            if anname and anname in baseline_meas
            else None
        )
        preview_gap = (
            preview_meas[anname].median_gap_pt
            if anname and anname in preview_meas
            else None
        )
        idml_eff = idml.effective_leading_pt if idml else None
        delta_b_vs_i = (
            round(baseline_gap - idml_eff, 3)
            if (baseline_gap and idml_eff)
            else None
        )
        delta_p_vs_b = (
            round(preview_gap - baseline_gap, 3)
            if (preview_gap and baseline_gap)
            else None
        )
        delta_p_vs_i = (
            round(preview_gap - idml_eff, 3)
            if (preview_gap and idml_eff)
            else None
        )
        # Classification
        cls = "match"
        if not bp and not sla:
            cls = "unmatched_idml_no_emit"
        elif preview_gap is None and baseline_gap is None:
            cls = "unmeasured"
        elif delta_p_vs_b is not None and abs(delta_p_vs_b) >= 1.0:
            cls = "drift_major" if abs(delta_p_vs_b) >= 3.0 else "drift_minor"
        elif delta_p_vs_i is not None and abs(delta_p_vs_i) >= 1.0:
            cls = "drift_minor"
        notes_parts = []
        if idml and idml.leading_model == "LeadingModelAkiBelow":
            notes_parts.append("AkiBelow → +12% rendered")
        if idml and idml.grid_alignment == "AlignBaseline":
            notes_parts.append("baseline-grid aligned")
        if idml and idml.leading_source == "auto":
            notes_parts.append(f"auto-leading × {_AUTO_LEADING_DEFAULT_PCT}%")
        rows.append(AuditRow(
            anname=anname,
            paragraph_style=idml.paragraph_style_name if idml else None,
            page_idx=(
                preview_meas[anname].page_idx if anname and anname in preview_meas
                else (baseline_meas[anname].page_idx if anname and anname in baseline_meas else None)
            ),
            text_excerpt=idml.text_excerpt if idml else (
                bp.text[:80] if bp else (sla.text[:80] if sla else "")
            ),
            idml_point_size_pt=idml.point_size_pt if idml else None,
            idml_leading_authored_pt=idml.leading_pt_authored if idml else None,
            idml_effective_leading_pt=round(idml.effective_leading_pt, 3) if idml else None,
            idml_leading_model=idml.leading_model if idml else None,
            idml_leading_source=idml.leading_source if idml else None,
            build_py_linesp_pt=round(bp.linesp_pt, 3) if (bp and bp.linesp_pt) else None,
            build_py_linespmode=bp.linespmode if bp else None,
            sla_linesp_pt=round(sla.linesp_pt, 3) if (sla and sla.linesp_pt) else None,
            sla_linespmode=sla.linespmode if sla else None,
            baseline_pdf_gap_pt=baseline_gap,
            preview_pdf_gap_pt=preview_gap,
            delta_baseline_vs_idml_pt=delta_b_vs_i,
            delta_preview_vs_baseline_pt=delta_p_vs_b,
            delta_preview_vs_idml_pt=delta_p_vs_i,
            classification=cls,
            notes="; ".join(notes_parts),
        ))
    return rows


# ---------------------------------------------------------------------------
# Output formatting


def write_yaml(
    rows: list[AuditRow],
    out_path: Path,
    sla_frame_summaries: dict[str, "SlaFrameParaSummary"] | None = None,
) -> None:
    payload = {
        "row_count": len(rows),
        "summary": _summary_counts(rows),
        "inconsistent_frames": (
            [s.anname for s in (sla_frame_summaries or {}).values() if s.inconsistent_pattern]
        ),
        "frame_para_summaries": {
            an: asdict(s) for an, s in (sla_frame_summaries or {}).items()
        },
        "rows": [asdict(r) for r in rows],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))


def _summary_counts(rows: list[AuditRow]) -> dict:
    cls_counts: dict[str, int] = {}
    for r in rows:
        cls_counts[r.classification] = cls_counts.get(r.classification, 0) + 1
    return cls_counts


def _write_csv(rows: list[AuditRow], out_path: Path) -> None:
    """Tab-separated table for spreadsheet import."""
    import csv
    fields = [
        "anname", "paragraph_style", "page_idx", "text_excerpt",
        "idml_point_size_pt", "idml_leading_authored_pt", "idml_effective_leading_pt",
        "idml_leading_model", "idml_leading_source",
        "build_py_linesp_pt", "build_py_linespmode",
        "sla_linesp_pt", "sla_linespmode",
        "baseline_pdf_gap_pt", "preview_pdf_gap_pt",
        "delta_baseline_vs_idml_pt", "delta_preview_vs_baseline_pt", "delta_preview_vs_idml_pt",
        "classification", "notes",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow({k: asdict(r).get(k, "") for k in fields})


def _fmt(v, prec=2):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{prec}f}"
    return str(v)


def write_md(
    rows: list[AuditRow],
    out_path: Path,
    sla_frame_summaries: dict[str, "SlaFrameParaSummary"] | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Line-spacing full audit — 26-03 Leporello z-Falz\n")
    lines.append(f"Total rows: **{len(rows)}**\n")
    summary = _summary_counts(rows)
    lines.append("## Summary by classification\n")
    lines.append("| Classification | Count |")
    lines.append("|---|---:|")
    for k, v in sorted(summary.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {k} | {v} |")
    lines.append("")

    # Frames flagged as "intermediate-para auto-leading despite explicit trail"
    if sla_frame_summaries:
        bad = [s for s in sla_frame_summaries.values() if s.inconsistent_pattern]
        if bad:
            lines.append("## Inconsistent `<para>`/`<trail>` pattern (CONVERTER BUG)\n")
            lines.append(
                "Frames below have a closing `<trail>` with explicit `LINESP=X` (LINESPMode=2)\n"
                "but intermediate `<para>` separators emit `LINESPMode=1` (auto/font-metric).\n"
                "Result: intermediate paragraphs render at Scribus's font-metric leading,\n"
                "not the authored value.\n"
            )
            lines.append("| Anname | Para count | Trail LINESP | Mid-paras (auto) | Mid-paras (fixed) |")
            lines.append("|---|---:|---:|---:|---:|")
            for s in bad:
                lines.append(
                    f"| {s.anname} | {s.para_count} | {s.trail_linesp:.2f} | "
                    f"{s.intermediate_para_count_auto} | {s.intermediate_para_count_fixed} |"
                )
            lines.append("")
    lines.append("## Per-paragraph table\n")
    lines.append(
        "| Anname | Page | Paragraph style | Pt | IDML lead | IDML eff | Lead model | Build linesp | SLA LINESP | Baseline gap | Preview gap | Δ p-vs-b | Δ p-vs-IDML | Class | Notes | Excerpt |"
    )
    lines.append(
        "|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|"
    )
    drift_first = sorted(
        rows,
        key=lambda r: (
            r.classification != "drift_major",
            r.classification != "drift_minor",
            -(abs(r.delta_preview_vs_baseline_pt or 0.0)),
            r.anname or "",
        ),
    )
    for r in drift_first:
        excerpt = (r.text_excerpt or "").replace("|", "/")[:60]
        lines.append(
            "| {an} | {pg} | {ps} | {pt} | {la} | {le} | {lm} | {bl} | {sl} | {bg} | {pg2} | {dpb} | {dpi} | {cls} | {nt} | {ex} |".format(
                an=r.anname or "—",
                pg=_fmt(r.page_idx),
                ps=(r.paragraph_style or "—")[:35],
                pt=_fmt(r.idml_point_size_pt),
                la=_fmt(r.idml_leading_authored_pt),
                le=_fmt(r.idml_effective_leading_pt),
                lm=(r.idml_leading_model or "—"),
                bl=_fmt(r.build_py_linesp_pt),
                sl=_fmt(r.sla_linesp_pt),
                bg=_fmt(r.baseline_pdf_gap_pt),
                pg2=_fmt(r.preview_pdf_gap_pt),
                dpb=_fmt(r.delta_preview_vs_baseline_pt),
                dpi=_fmt(r.delta_preview_vs_idml_pt),
                cls=r.classification,
                nt=(r.notes or ""),
                ex=excerpt,
            )
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# IDML source resolution


def _resolve_idml_source(
    slug: str, templates_dir: Path, originals_dir: Path
) -> Optional[Path]:
    """Resolve the source IDML for ``slug``.

    Priority:
      1. ``templates/<slug>/meta.yml::idml_source``. The value is a relative
         path authored by idml_import_driver, but the relative base depends
         on which worktree the import ran in (the Flyer slugs carry
         ``../../../../originals/...``, the leporello ``../../originals/...``).
         So we try several bases AND, if none resolve, fall back to looking
         up the IDML *basename* directly under ``originals_dir``.
      2. Strict slug-keyed glob of ``<originals_dir>/*/*.idml``: the IDML
         basename (hyphen/underscore-normalised, lowercased) must match the
         slug on its first three tokens.

    Returns the resolved Path, or ``None`` when nothing matches. The earlier
    implementation resolved (1) against ``originals_dir`` (wrong base) and
    hardcoded (2) to the leporello-zweigeteilt IDML, so every Flyer template
    silently audited against the wrong source.
    """
    def _norm(s: str) -> str:
        return s.lower().replace("-", " ").replace("_", " ")

    meta_path = templates_dir / slug / "meta.yml"
    if meta_path.exists():
        try:
            data = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            src = data.get("idml_source")
        except yaml.YAMLError:
            src = None
        if src:
            cand = Path(src)
            if cand.is_absolute() and cand.exists():
                return cand
            # Try resolving the relative path against several plausible
            # bases — the meta.yml value's base is worktree-dependent.
            tdir = (templates_dir / slug).resolve()
            bases = [
                tdir,
                templates_dir.resolve(),
                templates_dir.resolve().parent,
                tdir.parent.parent,
            ]
            for base in bases:
                resolved = (base / cand).resolve()
                if resolved.exists():
                    return resolved
            # Last resort for (1): the relative path is stale, but its
            # basename still names the real IDML — locate it by filename
            # under originals_dir (a unique basename per template).
            wanted = cand.name.lower()
            matches = [
                c for c in sorted(originals_dir.glob("*/*.idml"))
                if c.name.lower() == wanted
            ]
            if len(matches) == 1:
                return matches[0]

    # Fallback: strict slug-keyed glob. Match the IDML basename against the
    # first three slug tokens so a Flyer slug cannot resolve to a leporello.
    slug_words = _norm(slug).split()
    min_prefix = " ".join(slug_words[:3]) if len(slug_words) >= 3 else _norm(slug)
    for candidate in sorted(originals_dir.glob("*/*.idml")):
        if _norm(candidate.stem).startswith(min_prefix):
            return candidate
    return None


# ---------------------------------------------------------------------------
# CLI


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--templates-dir", default="/workspace/templates")
    ap.add_argument("--originals-dir", default="/workspace/originals")
    ap.add_argument("--out-yaml")
    ap.add_argument("--out-md")
    ap.add_argument(
        "--probe",
        help="Single-frame direct word-position measurement; prints JSON of "
             "per-line tops/bottoms/gaps in preview.pdf and baseline.pdf. "
             "Bypasses clustering. Argument is an anname (e.g. u1b0).",
    )
    args = ap.parse_args(argv)
    if args.probe and not args.out_yaml:
        args.out_yaml = "/dev/null"
    if args.probe and not args.out_md:
        args.out_md = "/dev/null"
    if not args.probe and (not args.out_yaml or not args.out_md):
        ap.error("--out-yaml and --out-md required unless --probe is set")

    templates_dir = Path(args.templates_dir)
    template_dir = templates_dir / args.slug
    if not template_dir.exists():
        ap.error(f"template dir not found: {template_dir}")

    # Resolve IDML — meta.yml::idml_source is relative to the TEMPLATE dir,
    # then a strict slug-keyed glob fallback. The previous implementation
    # resolved idml_source against --originals-dir (wrong base; e.g. the
    # flyer's '../../../../originals/...' became '/originals/...') AND its
    # glob fallback was hardcoded to ('leporello', 'zweigeteilt'), so every
    # Flyer template silently loaded the leporello IDML.
    idml_source = _resolve_idml_source(
        args.slug, templates_dir, Path(args.originals_dir)
    )
    if idml_source is None or not idml_source.exists():
        ap.error("could not resolve IDML source")
    print(f"IDML: {idml_source}", file=sys.stderr)

    build_py = template_dir / "build.py"
    sla = template_dir / "template.sla"
    preview = template_dir / "preview.pdf"
    baseline = template_dir / "baseline.pdf"

    # Parse all sources
    idml_runs, styles, doc_defaults, frame_map = parse_idml(idml_source)
    print(f"IDML paragraphs: {len(idml_runs)}", file=sys.stderr)
    build_runs, para_styles_bp = (
        parse_build_py(build_py) if build_py.exists() else ([], {})
    )
    print(
        f"build.py Run() calls: {len(build_runs)} | ParaStyle registry: {len(para_styles_bp)}",
        file=sys.stderr,
    )
    sla_items, sla_styles = parse_sla(sla) if sla.exists() else ([], {})
    sla_frame_summaries = (
        parse_sla_frame_summaries(sla) if sla.exists() else {}
    )
    inconsistent_frames = [
        s.anname for s in sla_frame_summaries.values() if s.inconsistent_pattern
    ]
    print(
        f"SLA ITEXT entries: {len(sla_items)} | STYLE registry: {len(sla_styles)} | "
        f"frames with inconsistent para-pattern: {len(inconsistent_frames)}",
        file=sys.stderr,
    )
    bp_frame_bboxes = parse_build_py_textframe_bboxes(build_py) if build_py.exists() else {}
    print(f"build.py TextFrame frames: {len(bp_frame_bboxes)}", file=sys.stderr)

    if args.probe:
        result = probe_frame(args.probe, bp_frame_bboxes, preview, baseline)
        import json
        print(json.dumps(result, indent=2, default=str))
        return 0

    # Page resolution: bbox-mm same on baseline and preview;
    # for now we fix page=0/1 by Y position (page 1 starts after page width)
    # … we'll let pdfplumber handle the per-page logic instead.
    # Try each page in PDF and assign frame to page with content.
    preview_meas: dict[str, PdfLinespMeasurement] = {}
    baseline_meas: dict[str, PdfLinespMeasurement] = {}
    if pdfplumber and preview.exists():
        # Test page 0 and page 1 — keep best (most lines)
        for anname, info in bp_frame_bboxes.items():
            best: Optional[PdfLinespMeasurement] = None
            for pg in (0, 1):
                m = measure_pdf_line_gaps(
                    preview, {anname: {"page": pg, "bbox_mm": info["bbox_mm"]}}
                ).get(anname)
                if m and (best is None or (m.line_count or 0) > (best.line_count or 0)):
                    best = m
            if best:
                preview_meas[anname] = best
    if pdfplumber and baseline.exists():
        for anname, info in bp_frame_bboxes.items():
            best: Optional[PdfLinespMeasurement] = None
            for pg in (0, 1):
                m = measure_pdf_line_gaps(
                    baseline, {anname: {"page": pg, "bbox_mm": info["bbox_mm"]}}
                ).get(anname)
                if m and (best is None or (m.line_count or 0) > (best.line_count or 0)):
                    best = m
            if best:
                baseline_meas[anname] = best

    rows = build_audit_rows(idml_runs, build_runs, sla_items, preview_meas, baseline_meas)
    write_yaml(rows, Path(args.out_yaml), sla_frame_summaries)
    write_md(rows, Path(args.out_md), sla_frame_summaries)
    # CSV side-output for filtering/sorting
    csv_path = Path(args.out_md).with_suffix(".csv")
    _write_csv(rows, csv_path)
    # Print a one-line summary so callers can grep
    summary = _summary_counts(rows)
    print(f"audit complete — {len(rows)} rows; summary: {summary}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
