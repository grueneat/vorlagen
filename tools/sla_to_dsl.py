#!/usr/bin/env python3
"""SLA -> DSL converter (one-shot bootstrap; not run in CI).

Reads an existing Scribus 1.6 SLA file, emits a Python ``build.py`` script
that uses the typed DSL (``tools/sla_lib/builder``) to recreate it. The
emitted script is the source of truth thereafter — humans edit it directly.

Strict mode (D6): the converter raises ``UnhandledElement`` on any element
or attribute it doesn't know how to translate. Better to fail loudly than
silently emit a build.py that renders something subtly different.

Inline images: extracted to sidecar PNG files under
``<assets-dir>/<safe_anname>_<idx>.<ext>``; emitted as ``ImageFrame(image=...)``.
The qCompress wrapper (4-byte big-endian length prefix + zlib stream) is
stripped during extraction.

Usage:
    python3 tools/sla_to_dsl.py \\
        postkarte-vorlage-original.sla \\
        templates/postkarte-a6-kampagne/build.py \\
        --template-id postkarte-a6-kampagne \\
        --assets-dir templates/postkarte-a6-kampagne/assets/
"""
from __future__ import annotations

import argparse
import re
import sys
import textwrap
from base64 import b64decode
from pathlib import Path
from typing import Optional
import zlib

import yaml
from lxml import etree

# Make tools/sla_lib importable when running directly from the worktree.
_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent))

from sla_lib import SLADocument  # noqa: E402

ROOT = _THIS.parent.parent
CI_YAML = ROOT / "shared" / "ci.yml"

PT_PER_MM = 72.0 / 25.4


# ---------------------------------------------------------------------------
class UnhandledElement(Exception):
    """Raised by the strict-mode converter when an element or attribute has no
    typed DSL counterpart. The traceback identifies what to add to Phase 1.
    """


# ---------------------------------------------------------------------------
def _load_ci_color_names() -> set[str]:
    with open(CI_YAML) as f:
        data = yaml.safe_load(f)
    return set(data.get("colors", {}).keys())


def _safe_filename(s: str) -> str:
    """Make a filename component out of an arbitrary string. Keeps letters,
    digits, ``-`` and ``_``; replaces everything else with ``_``."""
    s = s or "frame"
    return re.sub(r"[^A-Za-z0-9_-]", "_", s)[:60] or "frame"


# ---------------------------------------------------------------------------
class PythonRepr:
    """Lightweight code-emitter. Tracks indentation; helps emit Black-style
    Python (4-space indent, double quotes, trailing commas)."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.indent = 0

    def line(self, text: str = "") -> None:
        if text:
            self.lines.append("    " * self.indent + text)
        else:
            self.lines.append("")

    def open_block(self, header: str) -> None:
        self.line(header)
        self.indent += 1

    def close_block(self) -> None:
        self.indent = max(0, self.indent - 1)

    def render(self) -> str:
        return "\n".join(self.lines).rstrip() + "\n"


def _py_value(v) -> str:
    """Format a Python literal the way Black would."""
    if v is None:
        return "None"
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, (int, float)):
        # Avoid scientific notation for ints; trim trailing zeros for floats
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        if isinstance(v, float):
            s = f"{v:.6f}".rstrip("0").rstrip(".")
            return s if s else "0"
        return str(v)
    if isinstance(v, str):
        # Use a repr that prefers double quotes when no double quotes inside.
        if '"' not in v and "'" in v:
            return '"' + v + '"'
        return repr(v)
    if isinstance(v, tuple):
        return "(" + ", ".join(_py_value(x) for x in v) + ("," if len(v) == 1 else "") + ")"
    if isinstance(v, list):
        return "[" + ", ".join(_py_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{_py_value(k)}: {_py_value(val)}" for k, val in v.items()) + "}"
    raise TypeError(f"Cannot serialise {v!r}")


def _kwarg(name: str, value) -> str:
    return f"{name}={_py_value(value)}"


# ---------------------------------------------------------------------------
def _extract_inline_image(elem: etree._Element, assets_dir: Path,
                           safe_anname: str, idx_counter: list[int]) -> str:
    """Decode an inline image (qCompress + base64 + PNG/etc.) to a sidecar
    file under ``assets_dir`` and return the relative path written into
    ``ImageFrame(image=...)``."""
    blob = elem.attrib.get("ImageData", "")
    ext = elem.attrib.get("inlineImageExt", "png")
    raw = b64decode(blob)
    if len(raw) < 4:
        raise UnhandledElement("ImageData too short to contain qCompress prefix")
    # qCompress: 4-byte big-endian uncompressed length + zlib stream
    decompressed = zlib.decompress(raw[4:])
    assets_dir.mkdir(parents=True, exist_ok=True)
    idx_counter[0] += 1
    name = f"{safe_anname}_{idx_counter[0]:02d}.{ext}"
    out = assets_dir / name
    out.write_bytes(decompressed)
    return f"assets/{name}"


# ---------------------------------------------------------------------------
def _convert_color(elem: etree._Element) -> tuple[str, dict]:
    name = elem.attrib.get("NAME", "")
    space = elem.attrib.get("SPACE", "CMYK")
    if space == "CMYK":
        c = int(elem.attrib.get("C", "0"))
        m = int(elem.attrib.get("M", "0"))
        y = int(elem.attrib.get("Y", "0"))
        k = int(elem.attrib.get("K", "0"))
        kwargs = {"cmyk": (c, m, y, k)}
    elif space == "RGB":
        r = int(elem.attrib.get("R", "0"))
        g = int(elem.attrib.get("G", "0"))
        b = int(elem.attrib.get("B", "0"))
        kwargs = {"rgb": (r, g, b)}
    else:
        raise UnhandledElement(f"COLOR space {space!r} on {name!r}")
    if elem.attrib.get("Spot") == "1":
        kwargs["spot"] = True
    if elem.attrib.get("Register") == "1":
        kwargs["register"] = True
    return name, kwargs


# Mapping from STYLE attribute name -> ParaStyle keyword name.
PARA_ATTR_MAP_STR = {
    "FONT": "font",
    "FCOLOR": "fcolor",
    "LANGUAGE": "language",
    "BCOLOR": "bcolor",
    "FONTFEATURES": "fontfeatures",
    "FEATURES": "features",
    "Bullet": "bullet",
    "PARENT": "parent",
}
PARA_ATTR_MAP_FLOAT = {
    "FONTSIZE": "fontsize",
    "LINESP": "linesp",
    "VOR": "space_before_pt",
    "NACH": "space_after_pt",
    "FIRST": "first_indent_pt",
    "INDENT": "left_indent_pt",
    "RMARGIN": "right_indent_pt",
    "MinWordTrack": "min_word_track",
    "MinGlyphShrink": "min_glyph_shrink",
    "MaxGlyphExtend": "max_glyph_extend",
    "KERN": "kern",
    "ParagraphEffectOffset": "paragraph_effect_offset",
    "TXTULP": "txt_underline_pos",
    "TXTULW": "txt_underline_width",
    "TXTSTP": "txt_strike_pos",
    "TXTSTW": "txt_strike_width",
}
PARA_ATTR_MAP_INT = {
    "ALIGN": "align",
    "LINESPMode": "linesp_mode",
    "DROPLIN": "drop_lines",
    "HyphenConsecutiveLines": "hyph_consecutive_lines",
    "HyphenWordMin": "hyph_word_min",
    "KeepLinesStart": "keep_lines_start",
    "DIRECTION": "direction",
    "BSHADE": "bshade",
    "SCALEV": "scalev",
    "FSHADE": "fshade",
    "TXTSHX": "txt_shadow_x",
    "TXTSHY": "txt_shadow_y",
    "TXTOUT": "txt_outline",
    "BASEO": "baseline_offset",
    "Numeration": "numeration",
}
PARA_ATTR_MAP_BOOL = {
    "DROP": "drop_cap",
    "KeepTogether": "keep_together",
}
PARA_ATTR_HANDLED = (set(PARA_ATTR_MAP_STR) | set(PARA_ATTR_MAP_FLOAT)
                     | set(PARA_ATTR_MAP_INT) | set(PARA_ATTR_MAP_BOOL)
                     | {"NAME", "DefaultStyle"})


def _convert_style(elem: etree._Element) -> tuple[str, dict, bool]:
    name = elem.attrib.get("NAME", "")
    kwargs: dict = {}
    for src, dst in PARA_ATTR_MAP_STR.items():
        if src in elem.attrib:
            kwargs[dst] = elem.attrib[src]
    for src, dst in PARA_ATTR_MAP_FLOAT.items():
        if src in elem.attrib:
            kwargs[dst] = float(elem.attrib[src])
    for src, dst in PARA_ATTR_MAP_INT.items():
        if src in elem.attrib:
            kwargs[dst] = int(elem.attrib[src])
    for src, dst in PARA_ATTR_MAP_BOOL.items():
        if src in elem.attrib:
            kwargs[dst] = (elem.attrib[src] == "1")
    is_default = (elem.attrib.get("DefaultStyle") == "1")
    # Detect any unhandled attribute (D6 strict mode)
    for k in elem.attrib.keys():
        if k not in PARA_ATTR_HANDLED:
            raise UnhandledElement(f"STYLE {name!r} carries unhandled attribute {k!r}")
    return name, kwargs, is_default


CHAR_ATTR_MAP_STR = {"FONT": "font", "FCOLOR": "fcolor",
                     "FONTFEATURES": "fontfeatures", "FEATURES": "features",
                     "LANGUAGE": "language",
                     "SCOLOR": "scolor", "BGCOLOR": "bgcolor"}
CHAR_ATTR_MAP_FLOAT = {"FONTSIZE": "fontsize", "KERN": "kern",
                       "TXTULP": "txt_underline_pos",
                       "TXTULW": "txt_underline_width",
                       "TXTSTP": "txt_strike_pos",
                       "TXTSTW": "txt_strike_width"}
CHAR_ATTR_MAP_INT = {"FSHADE": "fshade",
                     "HyphenWordMin": "hyph_word_min",
                     "SSHADE": "sshade", "BGSHADE": "bgshade",
                     "TXTSHX": "txt_shadow_x", "TXTSHY": "txt_shadow_y",
                     "TXTOUT": "txt_outline",
                     "SCALEH": "scaleh", "SCALEV": "scalev",
                     "BASEO": "baseline_offset"}
CHAR_ATTR_HANDLED = (set(CHAR_ATTR_MAP_STR) | set(CHAR_ATTR_MAP_FLOAT)
                     | set(CHAR_ATTR_MAP_INT) | {"CNAME", "DefaultStyle"})


def _convert_charstyle(elem: etree._Element) -> tuple[str, dict, bool]:
    name = elem.attrib.get("CNAME", "")
    kwargs: dict = {}
    for src, dst in CHAR_ATTR_MAP_STR.items():
        if src in elem.attrib:
            kwargs[dst] = elem.attrib[src]
    for src, dst in CHAR_ATTR_MAP_FLOAT.items():
        if src in elem.attrib:
            kwargs[dst] = float(elem.attrib[src])
    for src, dst in CHAR_ATTR_MAP_INT.items():
        if src in elem.attrib:
            kwargs[dst] = int(elem.attrib[src])
    is_default = (elem.attrib.get("DefaultStyle") == "1")
    for k in elem.attrib.keys():
        if k not in CHAR_ATTR_HANDLED:
            raise UnhandledElement(f"CHARSTYLE {name!r} carries unhandled attribute {k!r}")
    return name, kwargs, is_default


# ---------------------------------------------------------------------------
# PAGEOBJECT attribute taxonomy. Anything not in HANDLED is rejected (D6).
PAGEOBJECT_HANDLED_PRIM = {
    "ItemID", "PTYPE", "FRTYPE",
    "OwnPage", "OnMasterPage",
    "XPOS", "YPOS", "WIDTH", "HEIGHT", "ROT",
    "ANNAME",
    "LAYER",
    # rendering / clipping
    "CLIPEDIT", "PWIDTH", "PLINEART",
    "LOCALSCX", "LOCALSCY", "LOCALX", "LOCALY", "LOCALROT",
    "PICART", "SCALETYPE", "RATIO",
    "PFILE", "PFILE2", "PFILE3", "PRFILE", "EPROF", "IRENDER", "EMBEDDED",
    "isInlineImage", "inlineImageExt", "ImageData",
    # color
    "PCOLOR", "PCOLOR2", "SHADE", "SHADE2",
    # rounded rect
    "RADRECT",
    # text frame
    "COLUMNS", "COLGAP", "AUTOTEXT", "EXTRA", "TEXTRA", "BEXTRA", "REXTRA",
    "VAlign", "FLOP", "PLTSHOW", "BASEOF",
    "textPathType", "textPathFlipped",
    "ALIGN",
    # path
    "path", "copath", "fillRule",
    # group / bbox
    "gXpos", "gYpos", "gWidth", "gHeight",
    # chain
    "NEXTITEM", "BACKITEM",
    # soft-shadow
    "HASSOFTSHADOW", "SOFTSHADOWCOLOR", "SOFTSHADOWBLURRADIUS",
    "SOFTSHADOWXOFFSET", "SOFTSHADOWYOFFSET", "SOFTSHADOWBLENDMODE",
    "SOFTSHADOWOPACITY", "SOFTSHADOWSHADE", "SOFTSHADOWERASE",
    "SOFTSHADOWOBJTRANS",
    # page-item misc — accepted as defaults, no DSL impact
    "TXTFILL", "TXTFILLSHADE", "TXTSTROKE", "TXTSTROKESHADE", "TXTSTRSH",
    "TXTSCALE", "TXTSCALEV", "TXTBASE", "TXTKERN",
    "WeldSource", "WeldID",
    "OnMasterPage",  # already listed
    # MASTERPAGE-bound items have OnMasterPage instead of OwnPage; both ok.
    # Stops/path-text fields not used by our originals; if they appear, raise.
    "startArrowIndex", "endArrowIndex", "startArrowScale", "endArrowScale",
    "PSTYLE", "PROTECT",
    "TextflowMode",
    "FRTYPE",
    "TextDist", "TextDistTop", "TextDistBottom", "TextDistLeft", "TextDistRight",
    "MASKTYPE", "GROUPS", "NUMTEXT", "GROUPC", "POSITION",
    "LANGUAGE", "isAnnotation", "ImageClip", "TXTSHX", "TXTSHY", "TXTOUT",
    "DASHS", "DASHOFF", "NUMDASH",
    "Pagenumber",  # image page reference (=0 = none)
    "EMBEDDED",    # 1 means inline image embedded; complementary to isInlineImage
}


def _resolve_xy_mm(elem: etree._Element, page_origin_pt: tuple[float, float]) -> tuple[float, float, float, float]:
    """Return (x_mm, y_mm, w_mm, h_mm) given a PAGEOBJECT and its owning
    page's PAGEXPOS/PAGEYPOS in points."""
    ox, oy = page_origin_pt
    xpos = float(elem.attrib.get("XPOS", "0")) - ox
    ypos = float(elem.attrib.get("YPOS", "0")) - oy
    w = float(elem.attrib.get("WIDTH", "0"))
    h = float(elem.attrib.get("HEIGHT", "0"))
    return xpos / PT_PER_MM, ypos / PT_PER_MM, w / PT_PER_MM, h / PT_PER_MM


def _check_unhandled_attrs(elem: etree._Element, ptype: str, label: str) -> None:
    for k in elem.attrib.keys():
        if k in PAGEOBJECT_HANDLED_PRIM:
            continue
        raise UnhandledElement(
            f"PAGEOBJECT (PTYPE={ptype}, {label}) carries unhandled attribute "
            f"{k!r}={elem.attrib[k]!r} — extend Phase 1 DSL to support it"
        )


def _soft_shadow_kwargs(elem: etree._Element) -> Optional[dict]:
    if elem.attrib.get("HASSOFTSHADOW") != "1":
        return None
    return {
        "color": elem.attrib.get("SOFTSHADOWCOLOR", "Black"),
        "blur_radius_pt": float(elem.attrib.get("SOFTSHADOWBLURRADIUS", "8.504")),
        "x_offset_pt": float(elem.attrib.get("SOFTSHADOWXOFFSET", "1.984")),
        "y_offset_pt": float(elem.attrib.get("SOFTSHADOWYOFFSET", "1.984")),
        "blend_mode": int(elem.attrib.get("SOFTSHADOWBLENDMODE", "1")),
        "opacity": float(elem.attrib.get("SOFTSHADOWOPACITY", "0")),
        "shade": int(elem.attrib.get("SOFTSHADOWSHADE", "100")),
        "erase": (elem.attrib.get("SOFTSHADOWERASEDBYOBJECT") == "1"),
        "object_trans": (elem.attrib.get("SOFTSHADOWOBJTRANS") == "1"),
    }


# Story-text element handlers
ITEXT_ATTR_MAP_STR = {
    "FONT": "font", "FCOLOR": "fcolor",
    "FONTFEATURES": "fontfeatures", "FEATURES": "features",
    "CPARENT": "char_style",
}
ITEXT_ATTR_MAP_FLOAT = {"FONTSIZE": "fontsize", "KERN": "kern"}
ITEXT_ATTR_MAP_INT = {"FSHADE": "fshade", "TXTULP": "underline_position",
                       "TXTSTP": "strike_position"}
ITEXT_ATTR_HANDLED = (set(ITEXT_ATTR_MAP_STR) | set(ITEXT_ATTR_MAP_FLOAT)
                      | set(ITEXT_ATTR_MAP_INT) | {"CH"})


def _build_runs(story_elem: etree._Element) -> list[dict]:
    """Walk a StoryText and return a list of Run kwarg dicts.

    Separators (para/breakline/tab/breakcol/breakframe) attach to the
    *preceding* run; <var name="pgno"/> attaches to the preceding run. A
    dangling <var/>/<para/>/etc. with no prior ITEXT becomes a zero-text Run.
    """
    runs: list[dict] = []
    cur: Optional[dict] = None
    for child in story_elem:
        tag = child.tag
        if tag == "DefaultStyle":
            continue  # handled at the frame level via TextFrame.style
        if tag == "ITEXT":
            if cur is not None:
                runs.append(cur)
            cur = {"text": child.attrib.get("CH", "")}
            for src, dst in ITEXT_ATTR_MAP_STR.items():
                if src in child.attrib:
                    cur[dst] = child.attrib[src]
            for src, dst in ITEXT_ATTR_MAP_FLOAT.items():
                if src in child.attrib:
                    cur[dst] = float(child.attrib[src])
            for src, dst in ITEXT_ATTR_MAP_INT.items():
                if src in child.attrib:
                    cur[dst] = int(child.attrib[src])
            for k in child.attrib:
                if k not in ITEXT_ATTR_HANDLED:
                    raise UnhandledElement(f"ITEXT carries unhandled attribute {k!r}")
        elif tag in ("para", "breakline", "tab", "breakcol", "breakframe"):
            if cur is None:
                cur = {"text": ""}
            cur["separator"] = tag
            # The <para/> element may carry PARENT="<paragraph style>" specifying
            # the style for the paragraph that's just ending. We attach it to
            # the run as paragraph_style; the DSL emitter will copy it onto the
            # emitted <para PARENT=.../> element.
            if tag == "para":
                parent_attr = child.attrib.get("PARENT")
                if parent_attr is not None:
                    cur["paragraph_style"] = parent_attr
        elif tag == "var":
            varname = child.attrib.get("name")
            if cur is None:
                cur = {"text": ""}
            cur["var"] = varname
        elif tag == "trail":
            # Terminator; the DSL emitter regenerates it.
            continue
        else:
            raise UnhandledElement(f"StoryText element {tag!r}")
    if cur is not None:
        runs.append(cur)
    return runs


# ---------------------------------------------------------------------------
def _convert_pageobject(po: etree._Element, page_origin_pt: tuple[float, float],
                         assets_dir: Path,
                         inline_idx: list[int]) -> tuple[str, str]:
    """Translate a PAGEOBJECT to a Python expression. Returns
    (code_str, var_name_or_empty). The var_name is used by chain emission."""
    ptype = po.attrib.get("PTYPE", "")
    frtype = po.attrib.get("FRTYPE", "0")
    anname = po.attrib.get("ANNAME", "")
    safe = _safe_filename(anname)
    x_mm, y_mm, w_mm, h_mm = _resolve_xy_mm(po, page_origin_pt)
    rot = float(po.attrib.get("ROT", "0"))
    layer = int(po.attrib.get("LAYER", "0"))

    common_kwargs: dict = {
        "x_mm": x_mm, "y_mm": y_mm, "w_mm": w_mm, "h_mm": h_mm,
        "layer": layer,
    }
    if rot:
        common_kwargs["rotation_deg"] = rot
    if anname:
        common_kwargs["anname"] = anname
    if frtype == "3":
        # Pass the original path verbatim for byte-equivalent round-trip.
        common_kwargs["custom_path"] = po.attrib.get("path", "")
        if "fillRule" in po.attrib:
            common_kwargs["fill_rule"] = int(po.attrib["fillRule"])
    if frtype == "2" and "RADRECT" in po.attrib:
        radrect_pt = float(po.attrib["RADRECT"])
        common_kwargs["corner_radius_mm"] = radrect_pt / PT_PER_MM
        common_kwargs["custom_path"] = po.attrib.get("path", "")
    ss = _soft_shadow_kwargs(po)
    if ss is not None:
        common_kwargs["soft_shadow"] = ss

    if ptype == "4":  # TextFrame
        _check_unhandled_attrs(po, ptype, f"ANNAME={anname!r}")
        story = po.find("StoryText")
        runs: list[dict] = []
        text_kwargs = dict(common_kwargs)
        if "PCOLOR" in po.attrib:
            text_kwargs["fill"] = po.attrib["PCOLOR"]
        if "PCOLOR2" in po.attrib:
            text_kwargs["line_color"] = po.attrib["PCOLOR2"]
        if "PWIDTH" in po.attrib:
            lw = float(po.attrib["PWIDTH"])
            if abs(lw) > 1e-6:
                text_kwargs["line_width_pt"] = lw
        if story is not None:
            ds = story.find("DefaultStyle")
            if ds is not None:
                if "PARENT" in ds.attrib:
                    text_kwargs["style"] = ds.attrib["PARENT"]
                if "LINESPMode" in ds.attrib:
                    text_kwargs["default_linesp_mode"] = int(ds.attrib["LINESPMode"])
            tr = story.find("trail")
            if tr is not None and "PARENT" in tr.attrib:
                text_kwargs["trail_style"] = tr.attrib["PARENT"]
            runs = _build_runs(story)
        if "ALIGN" in po.attrib:
            text_kwargs["text_align"] = int(po.attrib["ALIGN"])
        if "COLUMNS" in po.attrib and po.attrib["COLUMNS"] != "1":
            text_kwargs["columns"] = int(po.attrib["COLUMNS"])
        if "COLGAP" in po.attrib:
            colgap_pt = float(po.attrib["COLGAP"])
            colgap_mm = colgap_pt / PT_PER_MM
            if abs(colgap_mm - 4) > 0.001:
                text_kwargs["col_gap_mm"] = colgap_mm
        if runs:
            text_kwargs["runs"] = runs
        return _emit_textframe(text_kwargs, anname, safe), safe

    if ptype == "2":  # ImageFrame
        _check_unhandled_attrs(po, ptype, f"ANNAME={anname!r}")
        if po.attrib.get("isInlineImage") == "1":
            rel = _extract_inline_image(po, assets_dir, safe, inline_idx)
            common_kwargs["image"] = rel
        elif po.attrib.get("PFILE"):
            common_kwargs["image"] = po.attrib["PFILE"]
        else:
            common_kwargs["image"] = ""
        if "PCOLOR" in po.attrib:
            common_kwargs["fill"] = po.attrib["PCOLOR"]
        if "PCOLOR2" in po.attrib:
            common_kwargs["line_color"] = po.attrib["PCOLOR2"]
        if "PWIDTH" in po.attrib:
            lw = float(po.attrib["PWIDTH"])
            if abs(lw) > 1e-6:
                common_kwargs["line_width_pt"] = lw
        # LOCAL* if non-default
        for src, dst, default in (
            ("LOCALSCX", "lscx", 1.0),
            ("LOCALSCY", "lscy", 1.0),
            ("LOCALX", "lx", 0.0),
            ("LOCALY", "ly", 0.0),
            ("LOCALROT", "lrot", 0.0),
        ):
            pass  # handled below as one tuple
        scx = float(po.attrib.get("LOCALSCX", "1"))
        scy = float(po.attrib.get("LOCALSCY", "1"))
        if abs(scx - 1) > 1e-6 or abs(scy - 1) > 1e-6:
            common_kwargs["local_scale"] = (scx, scy)
        lx = float(po.attrib.get("LOCALX", "0"))
        ly = float(po.attrib.get("LOCALY", "0"))
        if abs(lx) > 1e-6 or abs(ly) > 1e-6:
            common_kwargs["local_offset_mm"] = (lx / PT_PER_MM, ly / PT_PER_MM)
        lrot = float(po.attrib.get("LOCALROT", "0"))
        if abs(lrot) > 1e-6:
            common_kwargs["local_rotation_deg"] = lrot
        return _emit_imageframe(common_kwargs, anname, safe), safe

    if ptype == "5":  # Line
        _check_unhandled_attrs(po, ptype, f"ANNAME={anname!r}")
        # Line frames in Scribus use FRTYPE=3 with a tiny path. The DSL's Line
        # primitive accepts (x1,y1,x2,y2). Reconstructing those from a single
        # rotated frame is a fool's errand, so emit as Polygon(custom_path=)
        # with line_color/line_width — visually equivalent.
        kwargs = dict(common_kwargs)
        kwargs["fill"] = "None"
        if "PCOLOR2" in po.attrib:
            kwargs["line_color"] = po.attrib["PCOLOR2"]
        if "PWIDTH" in po.attrib:
            lw = float(po.attrib["PWIDTH"])
            if abs(lw) > 1e-6:
                kwargs["line_width_pt"] = lw
        kwargs["custom_path"] = po.attrib.get("path", "")
        return _emit_polygon(kwargs, anname, safe), safe

    if ptype == "6":  # Polygon
        _check_unhandled_attrs(po, ptype, f"ANNAME={anname!r}")
        kwargs = dict(common_kwargs)
        kwargs["fill"] = po.attrib.get("PCOLOR", "Black")
        if "PCOLOR2" in po.attrib:
            kwargs["line_color"] = po.attrib["PCOLOR2"]
        if "PWIDTH" in po.attrib:
            lw = float(po.attrib["PWIDTH"])
            if abs(lw) > 1e-6:
                kwargs["line_width_pt"] = lw
        if frtype == "1":
            kwargs["shape"] = "ellipse"
        if "SHADE" in po.attrib:
            kwargs["fill_shade"] = int(po.attrib["SHADE"])
        return _emit_polygon(kwargs, anname, safe), safe

    raise UnhandledElement(f"PAGEOBJECT PTYPE={ptype} not supported")


def _emit_textframe(kwargs: dict, anname: str, safe: str) -> str:
    return _emit_call("TextFrame", kwargs)


def _emit_imageframe(kwargs: dict, anname: str, safe: str) -> str:
    return _emit_call("ImageFrame", kwargs)


def _emit_polygon(kwargs: dict, anname: str, safe: str) -> str:
    return _emit_call("Polygon", kwargs)


def _emit_call(cls: str, kwargs: dict) -> str:
    """Emit a multi-line constructor call."""
    parts = []
    # Special: runs is a list of dicts -> Run(...)
    runs = kwargs.pop("runs", None)
    soft_shadow = kwargs.pop("soft_shadow", None)
    for k, v in kwargs.items():
        parts.append(f"    {_kwarg(k, v)},")
    if soft_shadow is not None:
        ss_parts = ", ".join(f"{k}={_py_value(v)}" for k, v in soft_shadow.items())
        parts.append(f"    soft_shadow=SoftShadow({ss_parts}),")
    if runs is not None:
        parts.append("    runs=[")
        for r in runs:
            r_parts = ", ".join(f"{k}={_py_value(v)}" for k, v in r.items())
            parts.append(f"        Run({r_parts}),")
        parts.append("    ],")
    return cls + "(\n" + "\n".join(parts) + "\n)"


# ---------------------------------------------------------------------------
def _detect_chains(pos: list[etree._Element]) -> list[list[int]]:
    """Return list of chains (each = list of indices into ``pos``)."""
    by_id: dict[str, int] = {}
    for idx, po in enumerate(pos):
        if po.attrib.get("PTYPE") == "4":
            by_id[po.attrib.get("ItemID", "")] = idx
    chains: list[list[int]] = []
    visited: set[int] = set()
    for idx, po in enumerate(pos):
        if po.attrib.get("PTYPE") != "4":
            continue
        back = po.attrib.get("BACKITEM", "-1")
        nxt = po.attrib.get("NEXTITEM", "-1")
        if back != "-1" or nxt == "-1":
            continue
        if idx in visited:
            continue
        chain: list[int] = []
        cur_idx: Optional[int] = idx
        while cur_idx is not None:
            if cur_idx in visited:
                break
            visited.add(cur_idx)
            chain.append(cur_idx)
            cur_po = pos[cur_idx]
            nxt_id = cur_po.attrib.get("NEXTITEM", "-1")
            cur_idx = by_id.get(nxt_id) if nxt_id != "-1" else None
        if len(chain) >= 2:
            chains.append(chain)
    return chains


# ---------------------------------------------------------------------------
def convert(sla_path: Path, out_path: Path, template_id: str,
             assets_dir: Path) -> None:
    sla = SLADocument(sla_path)
    doc_elem = sla.doc

    # Document-level metadata
    page_w_pt = float(doc_elem.attrib.get("PAGEWIDTH", "0"))
    page_h_pt = float(doc_elem.attrib.get("PAGEHEIGHT", "0"))
    bleed_t = float(doc_elem.attrib.get("BleedTop", "0"))
    margins = (
        float(doc_elem.attrib.get("BORDERLEFT", "0")) / PT_PER_MM,
        float(doc_elem.attrib.get("BORDERRIGHT", "0")) / PT_PER_MM,
        float(doc_elem.attrib.get("BORDERTOP", "0")) / PT_PER_MM,
        float(doc_elem.attrib.get("BORDERBOTTOM", "0")) / PT_PER_MM,
    )
    facing = (doc_elem.attrib.get("BOOK", "0") == "1")
    column_gap_pt = float(doc_elem.attrib.get("ABSTSPALTEN", "11"))
    # DEFFONT is the legacy DSL field; Scribus actually reads DFONT.
    deffont = (doc_elem.attrib.get("DFONT")
                or doc_elem.attrib.get("DEFFONT", "Gotham Narrow Book"))
    defsize = float(doc_elem.attrib.get("DSIZE",
                                          doc_elem.attrib.get("DEFSIZE", "12")))
    first_page_num = int(doc_elem.attrib.get("FIRSTPAGENUM",
                                                doc_elem.attrib.get("FIRSTNUM", "1")))
    hcms = (doc_elem.attrib.get("HCMS", "0") == "1")

    # Pass-through every DOCUMENT-level attribute the DSL doesn't construct
    # itself. Scribus expects a long tail of locale/runtime defaults
    # (ALAYER, AUTOL, BaseC, CPICT, DPIn*, etc.) to be present on first read;
    # without them, text frames render with broken paragraph styling and PDF
    # export silently drops content.
    DSL_HANDLED_DOC_ATTRS = {
        "ANZPAGES", "PAGEWIDTH", "PAGEHEIGHT",
        "BORDERLEFT", "BORDERRIGHT", "BORDERTOP", "BORDERBOTTOM",
        "BleedTop", "BleedBottom", "BleedLeft", "BleedRight",
        "ORIENTATION", "PAGESIZE", "FIRSTPAGENUM", "BOOK", "FIRSTLEFT",
        "AUTOSPALTEN", "ABSTSPALTEN", "UNITS",
        "TITLE", "AUTHOR", "COMMENTS", "KEYWORDS", "PUBLISHER",
        "DOCDATE", "DOCTYPE", "DOCFORMAT", "DOCIDENT", "DOCSOURCE",
        "DOCLANGINFO", "DOCRELATION", "DOCCOVER", "DOCRIGHTS", "DOCCONTRIB",
        "DEFFONT", "DEFSIZE", "DFONT", "DSIZE",
        "DSAVE", "AUTOSAVE", "AUTOSAVETIME", "AUTOSAVECOUNT", "AUTOSAVEKEEP",
        "AUTOSAVEINDOCDIR", "AUTOSAVEDIR",
        "AutoSave", "AutoSaveTime", "AutoSaveCount", "AutoSaveKeep",
        "AUtoSaveInDocDir", "AutoSaveDir",
        "ScratchTop", "ScratchLeft", "ScratchRight", "ScratchBottom",
        "GapHorizontal", "GapVertical",
        "PAGEC", "MARGC", "RANDF", "currentProfile",
        "LANGUAGE",
        "PEN", "BRUSH", "PENLINE", "PENTEXT", "PENSHADE", "BRUSHSHADE",
        "LINESHADE", "PICTSHADE",
        "AUTOMATIC", "AUTOCHECK", "BASEGRID", "BASEO", "STIL", "STILLINE",
        "WIDTH", "WIDTHLINE", "GROUPC", "HCMS", "showBleed", "FIRSTNUM",
        "FIRSTPAGENUM",
    }
    extras: dict[str, str] = {
        k: v for k, v in doc_elem.attrib.items()
        if k not in DSL_HANDLED_DOC_ATTRS
    }

    # Capture the original's <PDF> block attrs so the DSL emits the same
    # ICC profile state on PDF export. Without SolidP/ImageP/PrintP/Intent2/
    # RGBMode/UseSpotColors/Version, Scribus falls back to a naive CMYK→sRGB
    # conversion that mismatches the baseline rendering even when HCMS=1.
    pdf_extras: dict[str, str] = {}
    pdf_elem = doc_elem.find("PDF")
    if pdf_elem is not None:
        # The DSL already authoritatively emits these — don't override.
        DSL_HANDLED_PDF_ATTRS = {
            "Articles", "Bookmarks", "Compress", "CompressMethod", "Quality",
            "EmbedPDF", "Resolution", "Binding", "PicRes", "Grayscale",
            "MirrorH", "MirrorV", "openAction",
            # Bleed-emit guard set (also enforced server-side).
            "BBottom", "BLeft", "BRight", "BTop",
            "useDocBleeds", "cropMarks", "bleedMarks",
            "markLength", "markOffset",
        }
        for k, v in pdf_elem.attrib.items():
            if k in DSL_HANDLED_PDF_ATTRS:
                continue
            pdf_extras[k] = v

    ci_color_names = _load_ci_color_names()

    code = PythonRepr()
    code.line("# Auto-generated from %s by tools/sla_to_dsl.py." % sla_path.name)
    code.line("# Hand-edit thereafter; this file is the source of truth.")
    code.line("")
    code.line("from pathlib import Path")
    code.line("")
    code.line("from sla_lib.builder import (")
    code.line("    Document, TextFrame, ImageFrame, Polygon, Run,")
    code.line("    DocumentLayer, ParaStyle, CharStyle, SoftShadow,")
    code.line(")")
    code.line("")
    code.line("HERE = Path(__file__).resolve().parent")
    code.line("")

    # Layers (only the subset Scribus actually uses; usually one)
    layer_lines: list[str] = []
    for layer_el in sla.iter_layers():
        kwargs = {
            "name": layer_el.attrib.get("NAME", "Hintergrund"),
            "visible": (layer_el.attrib.get("SICHTBAR") == "1"),
            "printable": (layer_el.attrib.get("DRUCKEN") == "1"),
            "editable": (layer_el.attrib.get("EDIT") == "1"),
            "flow": (layer_el.attrib.get("FLOW", "1") == "1"),
            "transparent": float(layer_el.attrib.get("TRANS", "1")),
            "blend": int(layer_el.attrib.get("BLEND", "0")),
            "outline": (layer_el.attrib.get("OUTL") == "1"),
            "layer_color": layer_el.attrib.get("LAYERC", "#000000"),
        }
        layer_lines.append("DocumentLayer(" + ", ".join(
            f"{k}={_py_value(v)}" for k, v in kwargs.items()) + ")")

    # Build Document(...) constructor — palette_replaces_ci so the emitted
    # SLA's COLOR list exactly matches the original (no leaked CI colors).
    doc_kwargs = [
        f'    title={_py_value(doc_elem.attrib.get("TITLE", ""))},',
        f'    template_id={_py_value(template_id)},',
        f'    author={_py_value(doc_elem.attrib.get("AUTHOR", "Die Grünen Niederösterreich"))},',
        f'    facing_pages={facing},',
        f'    column_gap_default_pt={_py_value(column_gap_pt)},',
        f'    deffont={_py_value(deffont)},',
        f'    defsize={_py_value(defsize)},',
        f'    first_page_num={first_page_num},',
        f'    palette_replaces_ci=True,',
        f'    hcms={hcms},',
    ]
    if extras:
        # Sort for stable output across runs
        items = ", ".join(f"{_py_value(k)}: {_py_value(v)}"
                          for k, v in sorted(extras.items()))
        doc_kwargs.append(f"    extra_doc_attrs={{{items}}},")
    if pdf_extras:
        items = ", ".join(f"{_py_value(k)}: {_py_value(v)}"
                          for k, v in sorted(pdf_extras.items()))
        doc_kwargs.append(f"    extra_pdf_attrs={{{items}}},")
    if layer_lines:
        doc_kwargs.append("    layers=[")
        for ll in layer_lines:
            doc_kwargs.append("        " + ll + ",")
        doc_kwargs.append("    ],")
    code.line("doc = Document(")
    for line in doc_kwargs:
        code.line(line)
    code.line(")")
    code.line("")

    # Colors — emit every COLOR from the original (palette_replaces_ci=True
    # means the CI brand stack is suppressed; what we register here is what
    # gets written). Order matches the original.
    for c in sla.iter_colors():
        name, kwargs = _convert_color(c)
        rgb = kwargs.get("rgb")
        cmyk = kwargs.get("cmyk")
        extra = ""
        if kwargs.get("spot"):
            extra += ", spot=True"
        if kwargs.get("register"):
            extra += ", register=True"
        if rgb is not None:
            code.line(f'doc.add_color({_py_value(name)}, rgb={_py_value(rgb)}{extra})')
        else:
            code.line(f'doc.add_color({_py_value(name)}, cmyk={_py_value(cmyk)}{extra})')
    if list(sla.iter_colors()):
        code.line("")

    # Char styles
    for cs_el in sla.iter_charstyles():
        cname, kwargs, is_default = _convert_charstyle(cs_el)
        kw_str = ", ".join(f"{k}={_py_value(v)}" for k, v in kwargs.items())
        if is_default:
            kw_str = (kw_str + ", " if kw_str else "") + "is_default=True"
        code.line(f'doc.add_char_style(CharStyle(name={_py_value(cname)}'
                  f'{(", " + kw_str) if kw_str else ""}))')

    # Para styles
    for ps_el in sla.iter_styles():
        sname, kwargs, is_default = _convert_style(ps_el)
        kw_str = ", ".join(f"{k}={_py_value(v)}" for k, v in kwargs.items())
        if is_default:
            kw_str = (kw_str + ", " if kw_str else "") + "is_default=True"
        code.line(f'doc.add_para_style(ParaStyle(name={_py_value(sname)}'
                  f'{(", " + kw_str) if kw_str else ""}))')
    code.line("")

    # Master pages
    master_origin: dict[str, tuple[float, float]] = {}
    for m in sla.iter_masters():
        nam = m.attrib.get("NAM", "Normal")
        master_origin[nam] = (
            float(m.attrib.get("PAGEXPOS", "0")),
            float(m.attrib.get("PAGEYPOS", "0")),
        )
        size_pt = (
            float(m.attrib.get("PAGEWIDTH", page_w_pt)) / PT_PER_MM,
            float(m.attrib.get("PAGEHEIGHT", page_h_pt)) / PT_PER_MM,
        )
        master_margins = (
            float(m.attrib.get("BORDERLEFT", "0")) / PT_PER_MM,
            float(m.attrib.get("BORDERRIGHT", "0")) / PT_PER_MM,
            float(m.attrib.get("BORDERTOP", "0")) / PT_PER_MM,
            float(m.attrib.get("BORDERBOTTOM", "0")) / PT_PER_MM,
        )
        is_left = (m.attrib.get("LEFT", "0") == "1")
        # Skip the auto-injected "Normal" master if it's empty AND we're the only
        # master AND not declared in the original. We DO want to round-trip
        # masters present in the original.
        code.line(f'doc.add_master(')
        code.line(f'    name={_py_value(nam)},')
        code.line(f'    size={_py_value(size_pt)},')
        code.line(f'    bleed_mm={_py_value(bleed_t / PT_PER_MM)},')
        code.line(f'    margins_mm={_py_value(master_margins)},')
        code.line(f'    facing={_py_value("left" if is_left else "right")},')
        code.line(f')')

    if list(sla.iter_masters()):
        code.line("")

    # Pages
    page_origin_by_num: dict[int, tuple[float, float]] = {}
    page_var_names: list[str] = []
    for idx, p in enumerate(sla.iter_pages()):
        num = int(p.attrib.get("NUM", str(idx)))
        page_origin_by_num[num] = (
            float(p.attrib.get("PAGEXPOS", "0")),
            float(p.attrib.get("PAGEYPOS", "0")),
        )
        page_size_pt = (
            float(p.attrib.get("PAGEWIDTH", page_w_pt)) / PT_PER_MM,
            float(p.attrib.get("PAGEHEIGHT", page_h_pt)) / PT_PER_MM,
        )
        mnam = p.attrib.get("MNAM", "Normal")
        margins_mm = (
            float(p.attrib.get("BORDERLEFT", "0")) / PT_PER_MM,
            float(p.attrib.get("BORDERRIGHT", "0")) / PT_PER_MM,
            float(p.attrib.get("BORDERTOP", "0")) / PT_PER_MM,
            float(p.attrib.get("BORDERBOTTOM", "0")) / PT_PER_MM,
        )
        var = f"page{idx}"
        page_var_names.append(var)
        code.line(f'{var} = doc.add_page(')
        code.line(f'    size={_py_value(page_size_pt)},')
        code.line(f'    bleed_mm={_py_value(bleed_t / PT_PER_MM)},')
        code.line(f'    margins_mm={_py_value(margins_mm)},')
        code.line(f'    master={_py_value(mnam)},')
        code.line(f')')
    code.line("")

    # PAGEOBJECTs grouped by OwnPage. Detect chains so we can emit them with
    # explicit ``link_to`` after construction.
    pos = list(doc_elem.findall("PAGEOBJECT"))
    # Index by OwnPage
    by_page: dict[int, list[int]] = {}
    for i, po in enumerate(pos):
        try:
            own = int(po.attrib.get("OwnPage", "-1"))
        except ValueError:
            own = -1
        if own < 0:
            continue
        by_page.setdefault(own, []).append(i)

    chains = _detect_chains(pos)
    chain_member: dict[int, tuple[int, int]] = {}  # idx -> (chain_id, position in chain)
    for cid, chain in enumerate(chains):
        for posn, idx in enumerate(chain):
            chain_member[idx] = (cid, posn)

    inline_idx = [0]
    item_var_for_idx: dict[int, str] = {}

    for own_page, indices in sorted(by_page.items()):
        if own_page >= len(page_var_names):
            continue
        page_var = page_var_names[own_page]
        po_origin = page_origin_by_num.get(own_page, (0.0, 0.0))
        for i in indices:
            po = pos[i]
            code_str, _ = _convert_pageobject(po, po_origin, assets_dir, inline_idx)
            ptype = po.attrib.get("PTYPE", "")
            anname = po.attrib.get("ANNAME", "")
            if i in chain_member and ptype == "4":
                cid, posn = chain_member[i]
                var_name = f"_chain{cid}_{posn}"
                item_var_for_idx[i] = var_name
                code.line(f"{var_name} = {code_str}")
                code.line(f"{page_var}.add({var_name})")
            else:
                code.line(f"{page_var}.add({code_str})")
            code.line("")
    # Wire chains
    for cid, chain in enumerate(chains):
        for src_pos in range(len(chain) - 1):
            src = item_var_for_idx[chain[src_pos]]
            dst = item_var_for_idx[chain[src_pos + 1]]
            code.line(f"{src}.link_to({dst})")
    if chains:
        code.line("")

    code.line("doc.save(HERE / \"template.sla\")")
    code.line('print(f"OK: {HERE / \"template.sla\"}")')
    code.line("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(code.render(), encoding="utf-8")


# ---------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Convert a Scribus SLA into a DSL build.py.")
    ap.add_argument("source", type=Path, help="Input .sla file")
    ap.add_argument("output", type=Path, help="Path to write build.py")
    ap.add_argument("--template-id", required=True, help="Template ID baked into build.py")
    ap.add_argument("--assets-dir", required=True, type=Path,
                    help="Directory for extracted inline-image sidecars")
    args = ap.parse_args(argv)
    try:
        convert(args.source, args.output, args.template_id, args.assets_dir)
    except UnhandledElement as e:
        print(f"UnhandledElement: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
