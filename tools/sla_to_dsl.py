#!/usr/bin/env python3
"""SLA -> DSL converter (one-shot bootstrap; not run in CI).

Reads an existing Scribus 1.6 SLA file, emits a Python ``build.py`` script
that uses the typed DSL (``tools/sla_lib/builder``) to recreate it. The
emitted script is the source of truth thereafter — humans edit it directly.

Strict mode (D6): the converter raises ``UnhandledElement`` on any element
or attribute it doesn't know how to translate. Better to fail loudly than
silently emit a build.py that renders something subtly different.

Inline images: round-tripped VERBATIM. The original PAGEOBJECT carries
``isInlineImage="1"`` plus an ``ImageData="<base64-of-qCompress-zlib-stream>"``
attribute; the converter captures that base64 string as-is and the DSL
emitter writes it back into the rebuilt SLA unchanged. We NEVER decode →
re-encode through PNG-on-disk: that round-trip is not byte-clean (Scribus's
qCompress wrapper writes ImageData with platform-dependent compression
parameters that don't survive a roundtrip through Pillow / libpng) and
the rendered PDF for pages with inline-image frames showed 3-15× more
pixel mismatch than non-image pages.

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
from pathlib import Path
from typing import Optional

import yaml
from lxml import etree

# Make tools/sla_lib importable when running directly from the worktree.
_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent))

from sla_lib import SLADocument  # noqa: E402
from sla_lib.builder import Brand  # noqa: E402
from sla_lib.builder.primitives import (  # noqa: E402
    PARAGRAPH_OVERRIDE_ATTRS as _PARA_OVERRIDE_ATTRS,
    DEFAULTSTYLE_OVERRIDE_ATTRS as _DEFAULTSTYLE_OVERRIDE_ATTRS,
    VAR_OVERRIDE_ATTRS as _VAR_OVERRIDE_ATTRS,
)

ROOT = _THIS.parent.parent
CI_YAML = ROOT / "shared" / "ci.yml"

PT_PER_MM = 72.0 / 25.4


# ---------------------------------------------------------------------------
class UnhandledElement(Exception):
    """Raised by the strict-mode converter when an element or attribute has no
    typed DSL counterpart. The traceback identifies what to add to Phase 1.
    """


# ---------------------------------------------------------------------------
def _is_rect_path(path: str, w_pt: float, h_pt: float) -> bool:
    """Return True if ``path`` is any axis-aligned rectangle path for a
    frame of (w_pt, h_pt), regardless of winding order or floating-point
    precision (tolerance: 0.015 pt ~ 0.005 mm).

    Scribus stores rectangle paths in compact form where the command letter
    is attached to the first coordinate: ``M0 0 Lx y Lx y Lx y Lx y Z``
    = 11 tokens.  Two winding orders appear in the corpus:

    - Right-first:    ``M0 0 L{w} 0 L{w} {h} L0 {h} L0 0 Z``
    - Vertical-first: ``M0 0 L0 {h} L{w} {h} L{w} 0 L0 0 Z``

    When True, the DSL auto-generates this path from ``clip_edit=True`` so the
    converter can omit ``custom_path=`` and ``fill_rule=``.
    """
    parts = path.split()
    # 5-corner rectangle: M0 0 Lx y Lx y Lx y Lx y Z = 11 tokens
    if len(parts) != 11 or parts[10] != "Z":
        return False
    # Parse the 5 points.  Tokens are: "M0", "0", "L<x>", "<y>", ..., "L<x>", "<y>"
    pts: list[tuple[float, float]] = []
    for pair_start in (0, 2, 4, 6, 8):
        cmd_coord = parts[pair_start]     # e.g. "M0" or "L314.646"
        y_str     = parts[pair_start + 1]  # e.g. "0" or "436.535"
        cmd = cmd_coord[0]
        x_str = cmd_coord[1:]
        if pair_start == 0:
            if cmd != "M":
                return False
        else:
            if cmd != "L":
                return False
        try:
            px, py = float(x_str), float(y_str)
        except ValueError:
            return False
        pts.append((px, py))
    # The path is a rectangle covering w_pt x h_pt if the set of x-coords is
    # {0, w_pt} (within tolerance) and the set of y-coords is {0, h_pt}.
    xs = {p[0] for p in pts}
    ys = {p[1] for p in pts}
    tol = 0.015  # 0.015 pt ≈ 0.005 mm — generous for Scribus %.4g path coords
    if len(xs) != 2 or len(ys) != 2:
        return False
    x_vals = sorted(xs)
    y_vals = sorted(ys)
    return (
        abs(x_vals[0]) < tol
        and abs(x_vals[1] - w_pt) < tol
        and abs(y_vals[0]) < tol
        and abs(y_vals[1] - h_pt) < tol
    )


# Module-level brand singleton: loaded once, shared across convert() calls.
# Using a mutable list as a simple "optional" container avoids a global= stmt.
_brand_cache: list[Brand] = []


def _get_brand() -> Brand:
    """Return the Grüne NÖ brand profile, loading it on first call."""
    if not _brand_cache:
        _brand_cache.append(Brand.gruene_noe())
    return _brand_cache[0]


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
    """Format a Python literal the way Black would.

    Floats use ``repr()`` so the emitted build.py is round-trip-stable: a
    LOCALSCX of ``0.0438778076573352`` round-trips to the same string and
    back to the same float on rebuild. Truncating to 6 decimals (the old
    behaviour) caused per-axis scaling drift on round-tripped inline image
    frames — visible as 1-2 px shifts at logo edges in the rendered PDF.
    """
    if v is None:
        return "None"
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        if isinstance(v, float):
            return repr(v)
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
def _capture_inline_image(elem: etree._Element) -> tuple[str, str]:
    """Return ``(base64_image_data, ext)`` for an inline-image PAGEOBJECT.

    The Scribus PAGEOBJECT carries ``ImageData`` as a base64-encoded
    qCompress payload (4-byte big-endian uncompressed length prefix + zlib
    stream around the original PNG/JPEG bytes). We do NOT decode it: the
    DSL stores the verbatim base64 string and emits it back unchanged so
    the rebuilt SLA is byte-identical to the original at this attribute.
    """
    blob = elem.attrib.get("ImageData", "")
    ext = elem.attrib.get("inlineImageExt", "png")
    if not blob:
        raise UnhandledElement("isInlineImage=1 PAGEOBJECT has empty ImageData")
    return blob, ext


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


def _resolve_xy_pt(elem: etree._Element) -> tuple[float, float, float, float]:
    """Return (xpos_pt, ypos_pt, width_pt, height_pt) verbatim from the
    PAGEOBJECT element. Used by the converter for byte-equivalent round-trip
    on frames where mm ↔ pt round-tripping introduces sub-ulp drift in
    the printed repr (e.g. inline images with HEIGHT="27.7755590551181")."""
    return (
        float(elem.attrib.get("XPOS", "0")),
        float(elem.attrib.get("YPOS", "0")),
        float(elem.attrib.get("WIDTH", "0")),
        float(elem.attrib.get("HEIGHT", "0")),
    )


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
    """Walk a StoryText and return a list of Run kwarg dicts that round-trip
    the element sequence verbatim.

    Each Run emits, in order: optional ITEXT → optional var → optional
    separator. The walker tracks whether the run "owns" an ITEXT (via
    ``has_itext``) so consecutive control elements (``<para/><para/>``,
    ``<para/><breakline/>``, ``<var/><para/>``) do NOT inject a phantom
    ``<ITEXT CH=""/>`` on the rebuilt side. A spurious empty ITEXT is the
    fingerprint of the previous merging walker — it caused page-numbers to
    disappear (var attached to a non-existent next paragraph), bullet
    listicles to drift, and headings to grow an extra empty line.

    Mapping rules:

    - ``<DefaultStyle .../>``: handled at the frame level (TextFrame.style
      / TextFrame.default_style_attrs). The walker skips it here.
    - ``<ITEXT CH="..." .../>``: starts a new Run with ``has_itext=True``
      and per-run formatting attributes; closes any pending Run first.
    - ``<para/>``: attaches a separator to the current Run (if it has
      space — i.e. has_itext True OR no separator yet OR var still
      pending). Otherwise opens a new Run with ``has_itext=False`` and
      attaches the separator there. PARENT becomes paragraph_style; ALIGN/
      LINESP/LINESPMode become paragraph_attrs.
    - ``<breakline/> / <tab/> / <breakcol/> / <breakframe/>``: same
      separator slot semantics as <para/> minus the PARENT/attrs handling.
    - ``<var name="..."/>``: attaches to the current Run via the ``var``
      slot. If the current Run already has a ``var`` set or a separator,
      a fresh Run with ``has_itext=False`` opens.
    - ``<trail/>``: terminator; emitter regenerates it from the trailing
      run state.
    """
    runs: list[dict] = []
    cur: Optional[dict] = None

    def _flush() -> None:
        nonlocal cur
        if cur is not None:
            runs.append(cur)
            cur = None

    def _ensure_open(*, has_itext: bool) -> None:
        """Make sure ``cur`` is an open run with the right has_itext flag.

        If ``cur`` is None, open a fresh run with the requested flag. If
        ``cur`` already exists with a *different* has_itext, leave it alone
        (the new fragment will overwrite the existing slot, and since we
        only call _ensure_open(has_itext=False) just before assigning a
        slot that's currently empty, the existing run still serves).
        """
        nonlocal cur
        if cur is None:
            cur = {"text": "", "has_itext": has_itext}

    for child in story_elem:
        tag = child.tag
        if tag == "DefaultStyle":
            # Handled at the frame level (see _convert_pageobject), not here.
            continue
        if tag == "ITEXT":
            # Always start a new ITEXT-owning run; flush any pending segment.
            _flush()
            cur = {"text": child.attrib.get("CH", ""), "has_itext": True}
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
            # If the current run already has a separator, the new separator
            # belongs to a fresh, ITEXT-less run (encoding empty-paragraph
            # vertical spacing or a bullet-list line break).
            if cur is None or cur.get("separator") is not None:
                _flush()
                _ensure_open(has_itext=False)
            cur["separator"] = tag
            if tag == "para":
                handled = {"PARENT"} | _PARA_OVERRIDE_ATTRS
                for k in child.attrib.keys():
                    if k not in handled:
                        raise UnhandledElement(
                            f"<para> carries unhandled attribute {k!r}={child.attrib[k]!r}; "
                            f"extend PARAGRAPH_OVERRIDE_ATTRS in tools/sla_lib/builder/primitives.py"
                        )
                parent_attr = child.attrib.get("PARENT")
                if parent_attr is not None:
                    cur["paragraph_style"] = parent_attr
                overrides = {k: v for k, v in child.attrib.items()
                              if k in _PARA_OVERRIDE_ATTRS}
                if overrides:
                    cur["paragraph_attrs"] = overrides
        elif tag == "var":
            varname = child.attrib.get("name")
            # var attaches to the current run UNLESS the current run already
            # has a var (consecutive var emission) or a separator (var must
            # come BEFORE the separator that ends its paragraph). In those
            # cases open a fresh, ITEXT-less run.
            if cur is None or cur.get("var") is not None or cur.get("separator") is not None:
                _flush()
                _ensure_open(has_itext=False)
            cur["var"] = varname
            handled_var = {"name"} | _VAR_OVERRIDE_ATTRS
            for k in child.attrib.keys():
                if k not in handled_var:
                    raise UnhandledElement(
                        f"<var> carries unhandled attribute {k!r}={child.attrib[k]!r}; "
                        f"extend VAR_OVERRIDE_ATTRS in tools/sla_lib/builder/primitives.py"
                    )
            var_overrides = {k: v for k, v in child.attrib.items()
                              if k in _VAR_OVERRIDE_ATTRS}
            if var_overrides:
                cur["var_attrs"] = var_overrides
        elif tag == "trail":
            # Terminator; the DSL emitter regenerates it from frame-level
            # trail_style/trail_attrs (set in _convert_pageobject).
            continue
        else:
            raise UnhandledElement(f"StoryText element {tag!r}")
    _flush()

    # Strip the redundant `has_itext=True` default from emitted run kwargs so
    # the resulting build.py is the same as before for the common case
    # (text-bearing runs). Only the new ``has_itext=False`` discriminator
    # surfaces, marking the bare-control-element runs.
    for r in runs:
        if r.get("has_itext", True) is True:
            r.pop("has_itext", None)
    return runs


# ---------------------------------------------------------------------------
def _convert_pageobject(po: etree._Element,
                         page_origin_pt: tuple[float, float]) -> tuple[str, str]:
    """Translate a PAGEOBJECT to a Python expression. Returns
    (code_str, var_name_or_empty). The var_name is used by chain emission.

    Inline images are captured verbatim into ``ImageFrame(inline_image_data=
    <base64>, inline_image_ext=<ext>)``; no sidecar PNG is written.
    """
    ptype = po.attrib.get("PTYPE", "")
    frtype = po.attrib.get("FRTYPE", "0")
    anname = po.attrib.get("ANNAME", "")
    safe = _safe_filename(anname)
    x_mm, y_mm, w_mm, h_mm = _resolve_xy_mm(po, page_origin_pt)
    xpos_pt, ypos_pt, width_pt, height_pt = _resolve_xy_pt(po)
    rot = float(po.attrib.get("ROT", "0"))
    layer = int(po.attrib.get("LAYER", "0"))

    # Task 5b: only carry verbatim pt overrides for inline image frames
    # where mm↔pt round-tripping introduces sub-ulp drift (e.g. HEIGHT=
    # '27.7755590551181' in Zeitung).  For all other frames, the mm coords
    # are sufficient — sla_diff normalises geometry semantically, not
    # byte-for-byte, so the small rounding delta is below the diff threshold.
    # Inline image frames are identified below (ptype=="2" + isInlineImage).
    # This flag is set True for those frames when we reach ptype=="2".
    _is_inline_image = (
        ptype == "2" and po.attrib.get("isInlineImage") == "1"
    )

    common_kwargs: dict = {
        "x_mm": x_mm, "y_mm": y_mm, "w_mm": w_mm, "h_mm": h_mm,
        "layer": layer,
    }
    if _is_inline_image:
        # Verbatim pt overrides for inline image frames only: preserves
        # LOCALSCX precision (e.g. 0.0438778076573352) and exact
        # XPOS/YPOS/WIDTH/HEIGHT bytes so the rebuilt SLA round-trips the
        # image scale without sub-ulp drift that causes 1-2 px shifts at
        # logo edges in the rendered PDF.
        common_kwargs["xpos_pt"] = xpos_pt
        common_kwargs["ypos_pt"] = ypos_pt
        common_kwargs["width_pt"] = width_pt
        common_kwargs["height_pt"] = height_pt
    if rot:
        common_kwargs["rotation_deg"] = rot
    if anname:
        common_kwargs["anname"] = anname
    if po.attrib.get("CLIPEDIT") == "1":
        common_kwargs["clip_edit"] = True
    if frtype == "3":
        # Task 5c: skip custom_path= when CLIPEDIT=1 and the path is a
        # rectangle matching the frame's dimensions.  The DSL auto-generates
        # the canonical rect path for TextFrame(clip_edit=True) without an
        # explicit custom_path=.  Any orientation and precision is accepted
        # (Scribus versions differ in winding order and decimal places).
        path = po.attrib.get("path", "")
        if po.attrib.get("CLIPEDIT") == "1" and _is_rect_path(path, width_pt, height_pt):
            # fillRule=0 is the Scribus default for FRTYPE=3 rect frames;
            # skip round-tripping it — DSL does not emit fillRule for the
            # auto-generated rect path.
            pass
        else:
            # Pass the original path verbatim for byte-equivalent round-trip.
            common_kwargs["custom_path"] = path
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
                # Capture every DefaultStyle attribute beyond PARENT/LINESPMode
                # (already mapped to dedicated kwargs). Originals like the
                # Zeitung Titelseite hero frame carry ``ALIGN="1" FONT="..."
                # FONTSIZE="30" FCOLOR="White"`` here; the previous walker
                # silently dropped them and the rebuilt SLA used the default
                # PARENT style's font/size/color/alignment instead.
                handled_ds = {"PARENT", "LINESPMode"} | _DEFAULTSTYLE_OVERRIDE_ATTRS
                for k in ds.attrib.keys():
                    if k not in handled_ds:
                        raise UnhandledElement(
                            f"<DefaultStyle> carries unhandled attribute "
                            f"{k!r}={ds.attrib[k]!r}; extend "
                            f"DEFAULTSTYLE_OVERRIDE_ATTRS in tools/sla_lib/builder/primitives.py"
                        )
                ds_overrides = {k: v for k, v in ds.attrib.items()
                                 if k in _DEFAULTSTYLE_OVERRIDE_ATTRS
                                 and k != "LINESPMode"}
                if ds_overrides:
                    text_kwargs["default_style_attrs"] = ds_overrides
            tr = story.find("trail")
            if tr is not None:
                # Strict-mode: the trail can carry PARENT plus the same
                # per-paragraph override attributes the <para> element does
                # (ALIGN/LINESP/LINESPMode). Any other attribute means we
                # found something unhandled — raise per CONTEXT.md D6.
                handled = {"PARENT"} | _PARA_OVERRIDE_ATTRS
                for k in tr.attrib.keys():
                    if k not in handled:
                        raise UnhandledElement(
                            f"<trail> carries unhandled attribute {k!r}={tr.attrib[k]!r}; "
                            f"extend PARAGRAPH_OVERRIDE_ATTRS in tools/sla_lib/builder/primitives.py"
                        )
                if "PARENT" in tr.attrib:
                    text_kwargs["trail_style"] = tr.attrib["PARENT"]
                trail_overrides = {k: v for k, v in tr.attrib.items()
                                    if k in _PARA_OVERRIDE_ATTRS}
                if trail_overrides:
                    text_kwargs["trail_attrs"] = trail_overrides
            runs = _build_runs(story)
        # Scribus stores vertical text justification in PAGEOBJECT VAlign
        # (0=top / 1=center / 2=bottom). ALIGN is not the vertical channel.
        # VAlign="0" is Scribus's default (top) — only surface a non-default
        # value so round-trips of top-aligned frames stay noise-free.
        if "VAlign" in po.attrib and po.attrib["VAlign"] != "0":
            text_kwargs["vertical_text_align"] = int(po.attrib["VAlign"])
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
            blob, ext = _capture_inline_image(po)
            common_kwargs["inline_image_data"] = blob
            common_kwargs["inline_image_ext"] = ext
            common_kwargs["image"] = ""
        elif po.attrib.get("PFILE"):
            common_kwargs["image"] = po.attrib["PFILE"]
        else:
            common_kwargs["image"] = ""
        # SCALETYPE controls image fit: 0=free / manual local-scale, 1=
        # fit-to-frame. Originals mix both; the DSL default is 1 (fit). When
        # the original explicitly sets 0, the rebuild must do the same — a
        # different SCALETYPE causes the image to render at a different size
        # inside the frame.
        if "SCALETYPE" in po.attrib:
            scale_type = int(po.attrib["SCALETYPE"])
            if scale_type != 1:
                common_kwargs["scale_type"] = scale_type
        # RATIO=1 keeps aspect ratio; 0 stretches independently. Originals
        # mostly carry 1; capture explicitly to round-trip the rare 0.
        if "RATIO" in po.attrib:
            ratio = int(po.attrib["RATIO"])
            if ratio != 1:
                common_kwargs["ratio"] = ratio
        # Pagenumber on image frames references another doc page used as the
        # image source (rare; default 0 = none). Originals carry 0
        # explicitly; emit it on the rebuilt SLA via extra_attrs to keep
        # byte-equivalence on this attribute.
        if "PICART" in po.attrib:
            pa = int(po.attrib["PICART"])
            if pa != 1:
                common_kwargs["pic_art"] = pa
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
    """Convert ``sla_path`` to ``out_path/build.py``.

    ``assets_dir`` is retained for API compatibility but no longer used by
    the converter itself: inline images are now round-tripped verbatim
    (``ImageFrame(inline_image_data=...)``), not extracted to sidecar PNGs.
    The directory is left untouched; callers may delete pre-existing
    sidecars after this converter runs.
    """
    del assets_dir  # no longer used
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
    # Set of DOCUMENT-level attributes the DSL emits authoritatively from
    # explicit Document(...) kwargs. Anything not in this set flows through
    # ``extra_doc_attrs`` verbatim so the rebuilt SLA preserves the
    # original's quirky doc-level fields (PENLINE / MARGC / GROUPC /
    # currentProfile / camelCase AutoSave variants / etc.) without the
    # DSL substituting its own hardcoded defaults.
    #
    # The reduced set here covers ONLY the attributes the DSL Document
    # constructor maps from explicit kwargs (page geometry, bleed,
    # facing-pages flag, default font/size, language, page color). Every
    # other doc-level attribute the original carries — including ones the
    # DSL also has hardcoded (PEN, BRUSH, PAGESIZE, AUTOMATIC, etc.) —
    # passes through extras and OVERRIDES the DSL hardcode.
    DSL_HANDLED_DOC_ATTRS = {
        "ANZPAGES", "PAGEWIDTH", "PAGEHEIGHT",
        "BORDERLEFT", "BORDERRIGHT", "BORDERTOP", "BORDERBOTTOM",
        "BleedTop", "BleedBottom", "BleedLeft", "BleedRight",
        "ORIENTATION", "FIRSTPAGENUM", "BOOK", "FIRSTLEFT",
        "AUTOSPALTEN", "ABSTSPALTEN", "UNITS",
        "TITLE", "AUTHOR", "COMMENTS", "KEYWORDS", "PUBLISHER",
        "DOCDATE", "DOCTYPE", "DOCFORMAT", "DOCIDENT", "DOCSOURCE",
        "DOCLANGINFO", "DOCRELATION", "DOCCOVER", "DOCRIGHTS", "DOCCONTRIB",
        "DEFFONT", "DEFSIZE", "DFONT", "DSIZE",
        "LANGUAGE", "HCMS", "showBleed", "FIRSTNUM",
        "PAGEC",
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
        # Closed set of PDF-element attributes the DSL emits authoritatively.
        # Anything outside this set flows through extra_pdf_attrs verbatim
        # so the rebuilt SLA's PDF block byte-matches the original. Keeping
        # this list small ensures we don't silently substitute different
        # render-affecting values (e.g. PicRes=300 instead of the
        # original's 600 — the picture-rendering resolution drives how
        # inline images rasterise on PDF export).
        DSL_HANDLED_PDF_ATTRS = {
            "Articles", "Bookmarks", "Compress", "Quality",
            "EmbedPDF", "Resolution", "Binding", "Grayscale",
            "MirrorH", "MirrorV", "openAction",
            # Bleed dimensions emitted from the page's bleed_mm; the rest of
            # the bleed-marks suite (useDocBleeds / cropMarks / bleedMarks /
            # colorMarks / etc.) flows through extras so we honour the
            # original's choice (some originals carry bleedMarks="0").
            "BBottom", "BLeft", "BRight", "BTop",
            "markLength", "markOffset",
        }
        for k, v in pdf_elem.attrib.items():
            if k in DSL_HANDLED_PDF_ATTRS:
                continue
            pdf_extras[k] = v

    # Task 5a: load Brand to filter out brand-default attrs and brand colors
    # from the generated build.py (they will be supplied by brand= instead).
    brand = _get_brand()
    brand_color_names: set[str] = set(brand.colors.keys())
    brand_default_doc_keys: set[str] = set(brand.default_doc_attrs.keys())
    brand_default_pdf_keys: set[str] = set(brand.default_pdf_attrs.keys())

    # Filter extras: keep only the keys that differ from brand defaults.
    differing_doc_extras: dict[str, str] = {
        k: v for k, v in extras.items() if k not in brand_default_doc_keys
    }
    differing_pdf_extras: dict[str, str] = {
        k: v for k, v in pdf_extras.items() if k not in brand_default_pdf_keys
    }

    code = PythonRepr()
    code.line("# Auto-generated from %s by tools/sla_to_dsl.py." % sla_path.name)
    code.line("# Hand-edit thereafter; this file is the source of truth.")
    code.line("")
    code.line("import sys")
    code.line("from pathlib import Path")
    code.line("")
    code.line("HERE = Path(__file__).resolve().parent")
    code.line("sys.path.insert(0, str(HERE.parents[1] / 'tools'))")
    code.line("")
    code.line("from sla_lib.builder import (  # noqa: E402")
    code.line("    Brand, Document, TextFrame, ImageFrame, Polygon, Run,")
    code.line("    ParaStyle, CharStyle, SoftShadow,")
    code.line(")")
    code.line("")

    # Task 5a: brand provides layers; no need to emit DocumentLayer list.
    # Brand also supplies the 113 identical extra_doc_attrs and 34 identical
    # extra_pdf_attrs — only the differing per-template keys are emitted below.

    # Build Document(...) constructor — brand= injects palette, styles, layers,
    # and the 113+34 identical default attrs.  No palette_replaces_ci= needed
    # (Brand sets it automatically).
    doc_kwargs = [
        f'    brand=Brand.gruene_noe(),',
        f'    title={_py_value(doc_elem.attrib.get("TITLE", ""))},',
        f'    template_id={_py_value(template_id)},',
        f'    author={_py_value(doc_elem.attrib.get("AUTHOR", "Die Grünen Niederösterreich"))},',
        f'    facing_pages={facing},',
        f'    column_gap_default_pt={_py_value(column_gap_pt)},',
        f'    deffont={_py_value(deffont)},',
        f'    defsize={_py_value(defsize)},',
        f'    first_page_num={first_page_num},',
        f'    hcms={hcms},',
        f'    doc_page_width_pt={_py_value(page_w_pt)},',
        f'    doc_page_height_pt={_py_value(page_h_pt)},',
    ]
    if differing_doc_extras:
        # Only the 23 per-template differing keys; brand defaults cover the rest.
        items = ", ".join(f"{_py_value(k)}: {_py_value(v)}"
                          for k, v in sorted(differing_doc_extras.items()))
        doc_kwargs.append(f"    extra_doc_attrs={{{items}}},")
    if differing_pdf_extras:
        # Only the 11 per-template differing keys; brand defaults cover the rest.
        items = ", ".join(f"{_py_value(k)}: {_py_value(v)}"
                          for k, v in sorted(differing_pdf_extras.items()))
        doc_kwargs.append(f"    extra_pdf_attrs={{{items}}},")
    code.line("doc = Document(")
    for line in doc_kwargs:
        code.line(line)
    code.line(")")
    code.line("")

    # Colors — emit only template-specific colors NOT already in brand.colors.
    # Brand.gruene_noe() registers all CI colors (Black, White, Dunkelgrün,
    # Hellgrün, Gelb, Magenta, Registration), so we skip those here.
    template_colors = [c for c in sla.iter_colors()
                       if c.attrib.get("NAME", "") not in brand_color_names]
    for c in template_colors:
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
    if template_colors:
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
        master_pagexpos = float(m.attrib.get("PAGEXPOS", "0"))
        master_pageypos = float(m.attrib.get("PAGEYPOS", "0"))
        master_origin[nam] = (master_pagexpos, master_pageypos)
        m_w_pt = float(m.attrib.get("PAGEWIDTH", page_w_pt))
        m_h_pt = float(m.attrib.get("PAGEHEIGHT", page_h_pt))
        size_pt = (m_w_pt / PT_PER_MM, m_h_pt / PT_PER_MM)
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
        # Pass PAGEXPOS/PAGEYPOS/width_pt/height_pt explicitly so the rebuilt
        # master sits at the same scratch-canvas coordinate as the original
        # — without these, the DSL's auto-computed offset rounds away the
        # ScratchLeft+PAGEWIDTH precision the original carries (e.g. 100.000629
        # + 595.275590551 vs the DSL's 100.0 + mm_to_pt(210)).
        code.line(f'doc.add_master(')
        code.line(f'    name={_py_value(nam)},')
        code.line(f'    size={_py_value(size_pt)},')
        code.line(f'    bleed_mm={_py_value(bleed_t / PT_PER_MM)},')
        code.line(f'    margins_mm={_py_value(master_margins)},')
        code.line(f'    facing={_py_value("left" if is_left else "right")},')
        code.line(f'    page_xpos_pt={_py_value(master_pagexpos)},')
        code.line(f'    page_ypos_pt={_py_value(master_pageypos)},')
        code.line(f'    width_pt={_py_value(m_w_pt)},')
        code.line(f'    height_pt={_py_value(m_h_pt)},')
        code.line(f')')

    if list(sla.iter_masters()):
        code.line("")

    # Pages
    page_origin_by_num: dict[int, tuple[float, float]] = {}
    page_var_names: list[str] = []
    for idx, p in enumerate(sla.iter_pages()):
        num = int(p.attrib.get("NUM", str(idx)))
        p_xpos = float(p.attrib.get("PAGEXPOS", "0"))
        p_ypos = float(p.attrib.get("PAGEYPOS", "0"))
        page_origin_by_num[num] = (p_xpos, p_ypos)
        p_w_pt = float(p.attrib.get("PAGEWIDTH", page_w_pt))
        p_h_pt = float(p.attrib.get("PAGEHEIGHT", page_h_pt))
        page_size_pt = (p_w_pt / PT_PER_MM, p_h_pt / PT_PER_MM)
        mnam = p.attrib.get("MNAM", "Normal")
        margins_mm = (
            float(p.attrib.get("BORDERLEFT", "0")) / PT_PER_MM,
            float(p.attrib.get("BORDERRIGHT", "0")) / PT_PER_MM,
            float(p.attrib.get("BORDERTOP", "0")) / PT_PER_MM,
            float(p.attrib.get("BORDERBOTTOM", "0")) / PT_PER_MM,
        )
        var = f"page{idx}"
        page_var_names.append(var)
        # Pass PAGEXPOS/PAGEYPOS/width_pt/height_pt explicitly so the rebuilt
        # page sits at the same scratch-canvas coordinate as the original
        # (so frame XPOS/YPOS round-trip with original precision instead of
        # picking up the SCRATCH_LEFT+w_pt mm-rounded approximation).
        code.line(f'{var} = doc.add_page(')
        code.line(f'    size={_py_value(page_size_pt)},')
        code.line(f'    bleed_mm={_py_value(bleed_t / PT_PER_MM)},')
        code.line(f'    margins_mm={_py_value(margins_mm)},')
        code.line(f'    master={_py_value(mnam)},')
        code.line(f'    page_xpos_pt={_py_value(p_xpos)},')
        code.line(f'    page_ypos_pt={_py_value(p_ypos)},')
        code.line(f'    width_pt={_py_value(p_w_pt)},')
        code.line(f'    height_pt={_py_value(p_h_pt)},')
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

    item_var_for_idx: dict[int, str] = {}

    for own_page, indices in sorted(by_page.items()):
        if own_page >= len(page_var_names):
            continue
        page_var = page_var_names[own_page]
        po_origin = page_origin_by_num.get(own_page, (0.0, 0.0))
        for i in indices:
            po = pos[i]
            code_str, _ = _convert_pageobject(po, po_origin)
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
