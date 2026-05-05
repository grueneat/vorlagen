"""Low-level frame primitives that emit valid PAGEOBJECT XML.

Each primitive accepts mm coordinates and an optional anchor for sugar.
Internally everything converts to pt and adds the page's scratch-canvas
offset (page_xpos_pt + page_ypos_pt) to produce the absolute XPOS/YPOS that
Scribus expects.

PTYPE values from `pageitem.h::ItemType`:
  2 = ImageFrame, 4 = TextFrame, 5 = Line, 6 = Polygon, 7 = PolyLine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Optional, Union

from lxml import etree

from .ci import Color, Style
from .document import mm_to_pt, _fmt_num, MM_TO_PT
from .styles import SoftShadow


def _format_path_coord(value: float) -> str:
    """Format a path coordinate the way Scribus does on save.

    Scribus's path/copath attribute uses ``%.6g`` formatting (6 significant
    digits, rounded). Frame WIDTH/HEIGHT carry full float precision, but
    the rectangle path that Scribus regenerates on save is intentionally
    coarser — the path is a clip-region hint, not a coordinate. Matching
    that format exactly avoids spurious 5th/6th-decimal drift in the
    rebuilt path that Scribus would re-round on the next save anyway.
    """
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{float(value):.6g}"


def _format_rect_path(w_pt: float, h_pt: float) -> str:
    """Build the canonical Scribus rectangle path for a frame of (w_pt, h_pt)."""
    w = _format_path_coord(w_pt)
    h = _format_path_coord(h_pt)
    return f"M0 0 L{w} 0 L{w} {h} L0 {h} L0 0 Z"

# Closed set of per-paragraph attribute overrides the DSL accepts on a
# <para>/<trail> element beyond PARENT (the paragraph style name, which has
# its own kwarg). Originals encountered so far carry only ALIGN, LINESP and
# LINESPMode here; anything else must extend this set explicitly so silent
# drops cannot happen again. Per CONTEXT.md D2 we keep this typed (a closed
# enum-keyed thing), not a free-form raw_attrs escape hatch.
PARAGRAPH_OVERRIDE_ATTRS: frozenset[str] = frozenset({
    "ALIGN",        # per-paragraph horizontal alignment override (0..3)
    "LINESP",       # explicit line spacing in pt (used with LINESPMode=2)
    "LINESPMode",   # 0=auto, 1=fixed, 2=baseline, 3=baseline-grid
})

# Closed set of attributes the DSL accepts on <DefaultStyle>. The
# DefaultStyle element sits at the top of every StoryText and carries the
# frame-level paragraph defaults; PARENT is exposed as ``TextFrame.style``
# while everything else flows through ``TextFrame.default_style_attrs``.
# Originals encountered so far carry up to ALIGN/FONT/FONTSIZE/FCOLOR/
# LINESP/LINESPMode — extend explicitly when something new appears so we
# never re-introduce the silent-drop pattern.
DEFAULTSTYLE_OVERRIDE_ATTRS: frozenset[str] = frozenset({
    "ALIGN",        # frame-default horizontal alignment
    "FONT",         # frame-default font face (used when no para/ITEXT override)
    "FONTSIZE",     # frame-default font size in pt
    "FCOLOR",       # frame-default font color name
    "LANGUAGE",     # frame-default hyphenation language
    "FONTFEATURES", # OpenType feature string
    "FEATURES",     # legacy feature string
    "LINESP",       # frame-default line spacing in pt
    "LINESPMode",   # frame-default line-spacing mode (0..3)
})

# Closed set of attributes the DSL accepts on a ``<var/>`` element beyond
# ``name``. Scribus treats var as an inline element and styles it with the
# usual character-style attribute set; one Zeitung page-number frame
# carries ``<var name="pgno" FCOLOR="White" FSHADE="100"/>``.
VAR_OVERRIDE_ATTRS: frozenset[str] = frozenset({
    "FCOLOR", "FSHADE", "FONT", "FONTSIZE",
    "FONTFEATURES", "FEATURES", "KERN",
    "TXTULP", "TXTSTP", "CPARENT",
})


def _validate_paragraph_attrs(attrs: Optional[Mapping[str, str]]) -> None:
    if not attrs:
        return
    bad = sorted(set(attrs) - PARAGRAPH_OVERRIDE_ATTRS)
    if bad:
        raise ValueError(
            f"paragraph_attrs contains unsupported keys {bad!r}; "
            f"allowed keys are {sorted(PARAGRAPH_OVERRIDE_ATTRS)!r}"
        )


def _validate_defaultstyle_attrs(attrs: Optional[Mapping[str, str]]) -> None:
    if not attrs:
        return
    bad = sorted(set(attrs) - DEFAULTSTYLE_OVERRIDE_ATTRS)
    if bad:
        raise ValueError(
            f"default_style_attrs contains unsupported keys {bad!r}; "
            f"allowed keys are {sorted(DEFAULTSTYLE_OVERRIDE_ATTRS)!r}"
        )

# Anchor type: either a string name or (x, y) where each can be a number (mm)
# or "left"|"right"|"center"|"top"|"bottom" or "bottom-N" / "right-N" (margin)
Anchor = Union[str, tuple]


def resolve_anchor(anchor: Anchor, page_w_pt: float, page_h_pt: float,
                   item_w_pt: float, item_h_pt: float) -> tuple[float, float]:
    """Resolve an anchor spec to (local_x_pt, local_y_pt) on the page.
    Anchor can be:
      - "top-left" | "top-center" | "top-right"
      - "center-left" | "center" | "center-right"
      - "bottom-left" | "bottom-center" | "bottom-right"
      - (x, y) where x,y are mm or strings like "center", "bottom-20"
    """
    if isinstance(anchor, str):
        if anchor == "center":
            return (page_w_pt - item_w_pt) / 2, (page_h_pt - item_h_pt) / 2
        parts = anchor.split("-")
        if len(parts) == 2:
            v, h = parts
            x = {"left": 0, "center": (page_w_pt - item_w_pt) / 2, "right": page_w_pt - item_w_pt}[h]
            y = {"top": 0, "center": (page_h_pt - item_h_pt) / 2, "bottom": page_h_pt - item_h_pt}[v]
            return x, y
        raise ValueError(f"Unknown anchor: {anchor!r}")
    # Tuple
    x_spec, y_spec = anchor
    x = _resolve_axis(x_spec, page_w_pt, item_w_pt, axis="x")
    y = _resolve_axis(y_spec, page_h_pt, item_h_pt, axis="y")
    return x, y


def _resolve_axis(spec, page_size_pt: float, item_size_pt: float, axis: str) -> float:
    if isinstance(spec, (int, float)):
        return mm_to_pt(spec)
    if isinstance(spec, str):
        if spec == "center":
            return (page_size_pt - item_size_pt) / 2
        if spec in ("left", "top"):
            return 0
        if spec in ("right", "bottom"):
            return page_size_pt - item_size_pt
        # "bottom-20" / "right-15"
        if "-" in spec:
            base, off = spec.split("-", 1)
            offset = mm_to_pt(float(off))
            base_pt = page_size_pt - item_size_pt if base in ("right", "bottom") else 0
            return base_pt - offset if base in ("right", "bottom") else base_pt + offset
    raise ValueError(f"Unknown axis spec: {spec!r}")


# ---------------------------------------------------------------------------
# Run — typed per-run text formatting
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Run:
    """A single position-aware StoryText segment.

    Each Run emits, in this exact order:

    1. An ``<ITEXT CH="..."/>`` (only when ``has_itext=True``; default).
       The CH attribute carries ``text``; per-run formatting attributes
       (``font``, ``fontsize``, ``fcolor``, ...) are written here.
    2. A ``<var name="..."/>`` element when ``var`` is set. This emits
       BEFORE the separator so the original page-number shape
       ``<var name="pgno"/><para PARENT="Seitenzahl"/>`` round-trips
       byte-faithfully — the previous order (separator first, then var)
       caused Scribus to attach the var to a non-existent next paragraph
       and silently dropped page numbers on every page.
    3. A separator element when ``separator`` is set: ``"para"`` -> <para/>,
       ``"breakline"`` -> <breakline/>, ``"tab"`` -> <tab/>, ``"breakcol"`` ->
       <breakcol/>, ``"breakframe"`` -> <breakframe/>.

    ``has_itext=False`` represents a Run that contributes only a separator
    and/or a var with no preceding text. The converter sets it when the
    original StoryText has consecutive control elements
    (``<para/><para/>``, ``<para/><breakline/>``, ``<var/><para/>``) so the
    rebuilt SLA does not invent a spurious empty ``<ITEXT CH=""/>``. A
    spurious empty ITEXT is a structural difference Scribus renders
    distinctly from the original (the listicle-bullet drift bug).
    """
    text: str = ""
    has_itext: bool = True
    font: Optional[str] = None
    fontsize: Optional[float] = None
    fcolor: Optional[str] = None
    fshade: Optional[int] = None
    fontfeatures: Optional[str] = None
    features: Optional[str] = None
    kern: Optional[float] = None
    underline_position: Optional[int] = None  # TXTULP
    strike_position: Optional[int] = None     # TXTSTP
    char_style: Optional[str] = None          # CPARENT
    paragraph_style: Optional[str] = None     # PARENT on the trailing <para/> element
    # Per-paragraph attribute overrides (e.g. {"ALIGN": "0"}, {"LINESPMode": "1"}).
    # Emitted on the trailing <para/> alongside PARENT. Keys must come from
    # PARAGRAPH_OVERRIDE_ATTRS (currently ALIGN / LINESP / LINESPMode); the
    # converter raises UnhandledElement if an original carries anything else.
    paragraph_attrs: Optional[dict] = None
    separator: Optional[str] = None           # "para" | "breakline" | "tab" | ...
    var: Optional[str] = None                 # "pgno"
    # Character-style attributes attached directly to the <var/> element
    # (Scribus accepts FCOLOR/FSHADE/FONT/FONTSIZE/etc. on var to style the
    # rendered substitution). Same closed key set as ITEXT per-run attrs.
    var_attrs: Optional[dict] = None

    def __post_init__(self) -> None:
        _validate_paragraph_attrs(self.paragraph_attrs)
        if self.var_attrs is not None:
            bad = sorted(set(self.var_attrs) - VAR_OVERRIDE_ATTRS)
            if bad:
                raise ValueError(
                    f"var_attrs contains unsupported keys {bad!r}; "
                    f"allowed keys are {sorted(VAR_OVERRIDE_ATTRS)!r}"
                )


_RUN_ATTR_MAP_INT = (
    ("fshade", "FSHADE"),
    ("underline_position", "TXTULP"),
    ("strike_position", "TXTSTP"),
)

_RUN_ATTR_MAP_NUM = (
    ("fontsize", "FONTSIZE"),
    ("kern", "KERN"),
)

_RUN_ATTR_MAP_STR = (
    ("font", "FONT"),
    ("fcolor", "FCOLOR"),
    ("fontfeatures", "FONTFEATURES"),
    ("features", "FEATURES"),
    ("char_style", "CPARENT"),
)


def _apply_run_attrs(it: etree._Element, run: Run) -> None:
    """Set ITEXT attributes from a Run dataclass; only non-None fields write."""
    for kw, attr in _RUN_ATTR_MAP_STR:
        v = getattr(run, kw)
        if v is not None:
            it.set(attr, v)
    for kw, attr in _RUN_ATTR_MAP_NUM:
        v = getattr(run, kw)
        if v is not None:
            it.set(attr, _fmt_num(v))
    for kw, attr in _RUN_ATTR_MAP_INT:
        v = getattr(run, kw)
        if v is not None:
            it.set(attr, str(v))


def _normalise_run(item) -> Run:
    """Accept the legacy ``(text, dict, sep)`` tuple form too. Returns a Run."""
    if isinstance(item, Run):
        return item
    if isinstance(item, tuple):
        text = item[0]
        override = item[1] if len(item) > 1 else None
        sep = item[2] if len(item) > 2 else None
        kwargs = {"text": text, "separator": sep}
        if override:
            for src_key, dst_key in (
                ("fcolor", "fcolor"),
                ("fontsize", "fontsize"),
                ("font", "font"),
                ("fshade", "fshade"),
                ("features", "features"),
                ("kern", "kern"),
                ("fontfeatures", "fontfeatures"),
                ("char_style", "char_style"),
            ):
                if src_key in override:
                    kwargs[dst_key] = override[src_key]
        return Run(**kwargs)
    if isinstance(item, str):
        return Run(text=item)
    raise TypeError(f"Unsupported run item: {item!r}")


# ---------------------------------------------------------------------------
# Common base for primitives
# ---------------------------------------------------------------------------
@dataclass
class _Frame:
    x_mm: float = 0
    y_mm: float = 0
    w_mm: float = 50
    h_mm: float = 30
    anchor: Optional[Anchor] = None
    rotation_deg: float = 0
    layer: int = 2  # default Text layer
    anname: str = ""
    custom_path: Optional[str] = None
    fill_rule: Optional[int] = None
    corner_radius_mm: float = 0
    soft_shadow: Optional[SoftShadow] = None

    def _xy_pt(self, page) -> tuple[float, float]:
        """Return absolute XPOS/YPOS in scratch canvas space."""
        if self.anchor is not None:
            local_x, local_y = resolve_anchor(self.anchor, page.width_pt, page.height_pt,
                                              mm_to_pt(self.w_mm), mm_to_pt(self.h_mm))
        else:
            local_x = mm_to_pt(self.x_mm)
            local_y = mm_to_pt(self.y_mm)
        return page.page_xpos_pt + local_x, page.page_ypos_pt + local_y


def _apply_shape_attrs(attrs: dict, frame: _Frame, w_pt: float, h_pt: float,
                        default_path: str, default_frtype: str) -> None:
    """Set FRTYPE, RADRECT, path/copath, fillRule based on the frame's
    ``custom_path`` / ``corner_radius_mm`` / ``fill_rule`` configuration.

    ``default_path`` and ``default_frtype`` describe the shape the primitive
    would emit when none of those override fields are set.

    Precedence: when ``corner_radius_mm > 0`` is set, FRTYPE=2 always wins
    (rounded rectangle). ``custom_path`` is then taken as the verbatim path
    Scribus stored — typically a bezier-rounded-rect path. If ``custom_path``
    alone is set (no corner radius), FRTYPE=3.
    """
    if frame.corner_radius_mm > 0:
        radrect_pt = mm_to_pt(frame.corner_radius_mm)
        attrs["FRTYPE"] = "2"
        attrs["RADRECT"] = _fmt_num(radrect_pt)
        path = frame.custom_path if frame.custom_path is not None else default_path
        attrs["path"] = path
        attrs["copath"] = path
    elif frame.custom_path is not None:
        attrs["FRTYPE"] = "3"
        attrs["path"] = frame.custom_path
        attrs["copath"] = frame.custom_path
    else:
        attrs["FRTYPE"] = default_frtype
        attrs["path"] = default_path
        attrs["copath"] = default_path
    if frame.fill_rule is not None:
        attrs["fillRule"] = str(frame.fill_rule)


def _apply_soft_shadow(attrs: dict, ss: Optional[SoftShadow]) -> None:
    if ss is None:
        return
    attrs["HASSOFTSHADOW"] = "1"
    attrs["SOFTSHADOWCOLOR"] = ss.color
    attrs["SOFTSHADOWBLURRADIUS"] = _fmt_num(ss.blur_radius_pt)
    attrs["SOFTSHADOWXOFFSET"] = _fmt_num(ss.x_offset_pt)
    attrs["SOFTSHADOWYOFFSET"] = _fmt_num(ss.y_offset_pt)
    attrs["SOFTSHADOWBLENDMODE"] = str(ss.blend_mode)
    attrs["SOFTSHADOWOPACITY"] = _fmt_num(ss.opacity)
    attrs["SOFTSHADOWSHADE"] = str(ss.shade)
    attrs["SOFTSHADOWERASE"] = "1" if ss.erase else "0"
    attrs["SOFTSHADOWOBJTRANS"] = "1" if ss.object_trans else "0"


# ---------------------------------------------------------------------------
# TextFrame
# ---------------------------------------------------------------------------
@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""           # paragraph style name (e.g. Style.BODY_12)
    fcolor: str = ""          # override color (e.g. Color.WHITE)
    runs: Optional[list] = None  # list of Run, or legacy (text, dict, sep) tuples
    columns: int = 1
    col_gap_mm: float = 4
    text_align: Optional[int] = None  # ALIGN attribute (vertical text align override)
    default_linesp_mode: Optional[int] = None  # DefaultStyle LINESPMode attribute
    trail_style: Optional[str] = None  # PARENT on the closing <trail/> element
                                       # (style for the final unterminated paragraph)
    # Per-paragraph attribute overrides on the closing <trail/> element
    # (ALIGN, LINESP, LINESPMode). Same closed key set as Run.paragraph_attrs.
    # Originals carry these on the trail of the final unterminated paragraph
    # (e.g. <trail PARENT="..." ALIGN="1"/>); dropping them silently centers
    # text the layout intends to be left-aligned.
    trail_attrs: Optional[dict] = None
    fill: Optional[str] = None        # PCOLOR (frame background fill)
    line_color: Optional[str] = None  # PCOLOR2 (frame border color)
    line_width_pt: float = 0          # PWIDTH
    # Frame-default StoryText DefaultStyle attributes beyond PARENT (which is
    # the ``style`` kwarg). Keys must come from DEFAULTSTYLE_OVERRIDE_ATTRS:
    # currently ALIGN/FONT/FONTSIZE/FCOLOR/LANGUAGE/FONTFEATURES/FEATURES/
    # LINESP/LINESPMode. Originals like the Zeitung's Titelseite hero frame
    # carry e.g. ``<DefaultStyle ALIGN="1" FONT="Gotham Narrow Book"
    # FONTSIZE="30" FCOLOR="White"/>``; without this typed channel they were
    # silently dropped to ``<DefaultStyle/>`` and the rendered hero text
    # drifted in size and alignment.
    default_style_attrs: Optional[dict] = None
    next_item: Optional["TextFrame"] = field(default=None, repr=False, compare=False)
    # Internal: pre-allocated ItemID for chain ordering. Set by Document._build_xml.
    _preallocated_id: Optional[int] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate_paragraph_attrs(self.trail_attrs)
        _validate_defaultstyle_attrs(self.default_style_attrs)

    def link_to(self, other: "TextFrame") -> "TextFrame":
        """Chain self -> other. Returns ``other`` for fluent chains
        (``a.link_to(b).link_to(c)``)."""
        self.next_item = other
        return other

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = mm_to_pt(self.w_mm), mm_to_pt(self.h_mm)
        item_id = self._preallocated_id if self._preallocated_id is not None else idgen.next()
        rect_path = _format_rect_path(w_pt, h_pt)
        attrs = {
            "XPOS": _fmt_num(x), "YPOS": _fmt_num(y),
            "OwnPage": str(page.own_page),
            "ItemID": str(item_id),
            "PTYPE": "4",
            "WIDTH": _fmt_num(w_pt), "HEIGHT": _fmt_num(h_pt),
            "CLIPEDIT": "0",
            "PWIDTH": _fmt_num(self.line_width_pt),
            "PLINEART": "1", "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "PICART": "1", "SCALETYPE": "1", "RATIO": "1",
            "COLUMNS": str(self.columns), "COLGAP": _fmt_num(mm_to_pt(self.col_gap_mm)),
            "AUTOTEXT": "0", "EXTRA": "0", "TEXTRA": "0", "BEXTRA": "0", "REXTRA": "0",
            "VAlign": "0", "FLOP": "1", "PLTSHOW": "0", "BASEOF": "0",
            "textPathType": "0", "textPathFlipped": "0",
            "gXpos": _fmt_num(x), "gYpos": _fmt_num(y),
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": _fmt_num(self.rotation_deg),
        }
        _apply_shape_attrs(attrs, self, w_pt, h_pt,
                            default_path=rect_path, default_frtype="0")
        _apply_soft_shadow(attrs, self.soft_shadow)
        if self.fill is not None:
            attrs["PCOLOR"] = self.fill
        if self.line_color is not None:
            attrs["PCOLOR2"] = self.line_color
        if self.text_align is not None:
            attrs["ALIGN"] = str(self.text_align)
        if self.anname:
            attrs["ANNAME"] = self.anname
        po = etree.Element("PAGEOBJECT", attrib=attrs)
        story = etree.SubElement(po, "StoryText")
        ds = etree.SubElement(story, "DefaultStyle")
        if self.style:
            ds.set("PARENT", self.style)
        if self.default_linesp_mode is not None:
            ds.set("LINESPMode", str(self.default_linesp_mode))
        # Frame-default DefaultStyle overrides (ALIGN, FONT, FONTSIZE, etc.).
        # These were silently dropped before the verbatim-StoryText fix and
        # caused the Titelseite hero text to render at the wrong size and
        # alignment on round-trip.
        if self.default_style_attrs:
            for k, v in self.default_style_attrs.items():
                # default_linesp_mode kwarg already handles LINESPMode; if the
                # caller set both, the explicit dict entry wins (matches
                # Scribus's last-write-wins attribute semantics).
                ds.set(k, str(v))

        # Emit Runs as ITEXT (optional) → var (optional) → separator (optional).
        # Variable element MUST come BEFORE the separator: the original Zeitung
        # page-number frame is `<var name="pgno"/><para PARENT="Seitenzahl"/>`,
        # and Scribus attaches the var to the paragraph it precedes. Emitting
        # var after the separator lost the page number on every page.
        run_list: list[Run] = []
        if self.runs:
            run_list = [_normalise_run(r) for r in self.runs]
            for r in run_list:
                if r.has_itext:
                    it = etree.SubElement(story, "ITEXT")
                    it.set("CH", r.text)
                    _apply_run_attrs(it, r)
                # Variable insert (e.g. <var name="pgno"/>) — emit BEFORE
                # the separator so the var attaches to THIS paragraph.
                if r.var is not None:
                    var = etree.SubElement(story, "var")
                    var.set("name", r.var)
                    if r.var_attrs:
                        for k, v in r.var_attrs.items():
                            var.set(k, str(v))
                # Separator between this run and the next paragraph
                if r.separator == "para":
                    para = etree.SubElement(story, "para")
                    style_attr = r.paragraph_style or self.style
                    if style_attr:
                        para.set("PARENT", style_attr)
                    # Per-paragraph attribute overrides (ALIGN, LINESPMode,
                    # LINESP). Validated in Run.__post_init__.
                    if r.paragraph_attrs:
                        for k, v in r.paragraph_attrs.items():
                            para.set(k, str(v))
                elif r.separator == "breakline":
                    etree.SubElement(story, "breakline")
                elif r.separator == "tab":
                    etree.SubElement(story, "tab")
                elif r.separator == "breakcol":
                    etree.SubElement(story, "breakcol")
                elif r.separator == "breakframe":
                    etree.SubElement(story, "breakframe")
        elif self.text:
            it = etree.SubElement(story, "ITEXT")
            it.set("CH", self.text)
            if self.fcolor:
                it.set("FCOLOR", self.fcolor)
        # Trail terminates StoryText, but only when there's a final
        # *unterminated* paragraph for it to describe. When the last run
        # already ends with separator='para' (or there are no runs at all
        # and no plain text), the StoryText has no trailing unterminated
        # paragraph and the original SLAs omit <trail/> entirely. Emitting
        # it anyway adds a phantom empty paragraph at the end of the frame
        # which the diff (correctly) reports as a structural mismatch.
        last_is_para_terminated = bool(run_list) and run_list[-1].separator == "para"
        if not last_is_para_terminated:
            trail = etree.SubElement(story, "trail")
            trail_parent = self.trail_style if self.trail_style is not None else self.style
            if trail_parent:
                trail.set("PARENT", trail_parent)
            if self.trail_attrs:
                for k, v in self.trail_attrs.items():
                    trail.set(k, str(v))
        return po


# ---------------------------------------------------------------------------
# ImageFrame
# ---------------------------------------------------------------------------
@dataclass
class ImageFrame(_Frame):
    src: str = ""             # PFILE path (absolute or relative-to-SLA)
    image: str = ""           # alias for src; converter prefers `image=`
    layer: int = 1            # default Bilder layer
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    scale_type: int = 1       # SCALETYPE
    ratio: int = 1            # RATIO
    pic_art: int = 1          # PICART (1=visible)
    fill: Optional[str] = None        # PCOLOR (frame background fill)
    line_color: Optional[str] = None  # PCOLOR2 (frame border)
    line_width_pt: float = 0          # PWIDTH
    # Verbatim inline-image round-trip channel. When the original SLA carried
    # an embedded image (``isInlineImage="1"``, ``ImageData="<base64>"``,
    # ``inlineImageExt="png"``) the converter captures the ImageData blob
    # without decoding/re-encoding it, and the emitter writes it back into
    # PAGEOBJECT verbatim. The previous "extract to sidecar PNG" round-trip
    # was not byte-clean (qCompress↔PNG-on-disk lost ~1px in rendering on
    # every inline-image-bearing page), so we now keep the bytes identical
    # in the rebuilt SLA — Scribus then renders byte-identical output.
    inline_image_data: Optional[str] = None
    inline_image_ext: Optional[str] = None  # e.g. "png", "jpg"

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = mm_to_pt(self.w_mm), mm_to_pt(self.h_mm)
        rect_path = _format_rect_path(w_pt, h_pt)
        is_inline = self.inline_image_data is not None
        pfile = "" if is_inline else (self.image or self.src)
        scx, scy = self.local_scale
        lx_mm, ly_mm = self.local_offset_mm
        attrs = {
            "XPOS": _fmt_num(x), "YPOS": _fmt_num(y),
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "2",
            "WIDTH": _fmt_num(w_pt), "HEIGHT": _fmt_num(h_pt),
            "CLIPEDIT": "0",
            "PWIDTH": _fmt_num(self.line_width_pt),
            "PLINEART": "1",
            "LOCALSCX": _fmt_num(scx), "LOCALSCY": _fmt_num(scy),
            "LOCALX": _fmt_num(mm_to_pt(lx_mm)), "LOCALY": _fmt_num(mm_to_pt(ly_mm)),
            "LOCALROT": _fmt_num(self.local_rotation_deg),
            "PICART": str(self.pic_art),
            "SCALETYPE": str(self.scale_type),
            "RATIO": str(self.ratio),
            "PFILE": pfile,
            "PRFILE": "sRGB display profile (ICC v2.2)",
            "IRENDER": "0",
            "gXpos": _fmt_num(x), "gYpos": _fmt_num(y),
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": _fmt_num(self.rotation_deg),
        }
        if is_inline:
            attrs["isInlineImage"] = "1"
            attrs["inlineImageExt"] = self.inline_image_ext or "png"
            attrs["ImageData"] = self.inline_image_data
            attrs["EMBEDDED"] = "0"
        if self.fill is not None:
            attrs["PCOLOR"] = self.fill
        if self.line_color is not None:
            attrs["PCOLOR2"] = self.line_color
        _apply_shape_attrs(attrs, self, w_pt, h_pt,
                            default_path=rect_path, default_frtype="0")
        _apply_soft_shadow(attrs, self.soft_shadow)
        if self.anname:
            attrs["ANNAME"] = self.anname
        return etree.Element("PAGEOBJECT", attrib=attrs)


# ---------------------------------------------------------------------------
# Polygon (rectangle / circle / arbitrary path)
# ---------------------------------------------------------------------------
@dataclass
class Polygon(_Frame):
    fill: str = "Black"               # color name from Color enum, mapped to PCOLOR
    line_color: Optional[str] = None  # PCOLOR2 (default omitted, matches originals)
    line_width_pt: float = 0
    layer: int = 0                    # default Hintergrund
    shape: str = "rectangle"          # 'rectangle' | 'ellipse'
    fill_shade: int = 100             # SHADE — emitted when != 100

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = mm_to_pt(self.w_mm), mm_to_pt(self.h_mm)
        if self.shape == "ellipse":
            default_path = self._ellipse_path(w_pt, h_pt)
            default_frtype = "1"  # FRTYPE=1 = ellipse
        else:
            default_path = _format_rect_path(w_pt, h_pt)
            default_frtype = "0"
        attrs = {
            "XPOS": _fmt_num(x), "YPOS": _fmt_num(y),
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "6",
            "WIDTH": _fmt_num(w_pt), "HEIGHT": _fmt_num(h_pt),
            "CLIPEDIT": "0",
            "PCOLOR": self.fill,
            "PWIDTH": _fmt_num(self.line_width_pt),
            "PLINEART": "1", "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "PICART": "1", "SCALETYPE": "1", "RATIO": "1",
            "gXpos": _fmt_num(x), "gYpos": _fmt_num(y),
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": _fmt_num(self.rotation_deg),
        }
        _apply_shape_attrs(attrs, self, w_pt, h_pt,
                            default_path=default_path, default_frtype=default_frtype)
        _apply_soft_shadow(attrs, self.soft_shadow)
        if self.line_color is not None:
            attrs["PCOLOR2"] = self.line_color
        if self.fill_shade != 100:
            attrs["SHADE"] = str(self.fill_shade)
        if self.anname:
            attrs["ANNAME"] = self.anname
        return etree.Element("PAGEOBJECT", attrib=attrs)

    @staticmethod
    def _ellipse_path(w: float, h: float) -> str:
        # Bezier ellipse approximation with kappa = 0.5522847498
        kx = w * 0.5 * 0.5522847498
        ky = h * 0.5 * 0.5522847498
        cx, cy = w / 2, h / 2
        return (
            f"M{cx:.3f} 0 "
            f"C{cx + kx:.3f} 0 {w:.3f} {cy - ky:.3f} {w:.3f} {cy:.3f} "
            f"C{w:.3f} {cy + ky:.3f} {cx + kx:.3f} {h:.3f} {cx:.3f} {h:.3f} "
            f"C{cx - kx:.3f} {h:.3f} 0 {cy + ky:.3f} 0 {cy:.3f} "
            f"C0 {cy - ky:.3f} {cx - kx:.3f} 0 {cx:.3f} 0 Z"
        )


# ---------------------------------------------------------------------------
# Line
# ---------------------------------------------------------------------------
@dataclass
class Line:
    x1_mm: float
    y1_mm: float
    x2_mm: float
    y2_mm: float
    color: str = "Black"
    width_pt: float = 1.0
    layer: int = 2
    anname: str = ""

    def to_pageobject(self, idgen, page) -> etree._Element:
        x1, y1 = mm_to_pt(self.x1_mm), mm_to_pt(self.y1_mm)
        x2, y2 = mm_to_pt(self.x2_mm), mm_to_pt(self.y2_mm)
        # Scribus stores lines as a frame with origin at min(x,y); width = dx, height = 0
        x_origin = min(x1, x2) + page.page_xpos_pt
        y_origin = min(y1, y2) + page.page_ypos_pt
        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        import math
        angle = math.degrees(math.atan2(dy, dx))
        attrs = {
            "XPOS": _fmt_num(x_origin), "YPOS": _fmt_num(y_origin),
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "5",
            "WIDTH": _fmt_num(length), "HEIGHT": "1",
            "FRTYPE": "3", "CLIPEDIT": "0",
            "PCOLOR": "None", "PCOLOR2": self.color,
            "PWIDTH": _fmt_num(self.width_pt),
            "PLINEART": "1", "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "ROT": _fmt_num(angle),
            "path": f"M0 0 L{_format_path_coord(length)} 0",
            "copath": f"M0 0 L{_format_path_coord(length)} 0",
            "gXpos": _fmt_num(x_origin), "gYpos": _fmt_num(y_origin),
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
        }
        if self.anname:
            attrs["ANNAME"] = self.anname
        return etree.Element("PAGEOBJECT", attrib=attrs)
