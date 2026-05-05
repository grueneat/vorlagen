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
from typing import Optional, Union

from lxml import etree

from .ci import Color, Style
from .document import mm_to_pt, _fmt_num, MM_TO_PT
from .styles import SoftShadow

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
    """A single ITEXT run with optional per-run style overrides.

    ``separator`` is the StoryText element placed AFTER this run (and before
    the next): ``"para"`` -> <para/>, ``"breakline"`` -> <breakline/>,
    ``"tab"`` -> <tab/>, ``"breakcol"`` -> <breakcol/>, ``"breakframe"`` -> <breakframe/>.
    ``var="pgno"`` emits a ``<var name="pgno"/>`` element after the run (and
    after any separator if both are set).
    """
    text: str = ""
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
    separator: Optional[str] = None           # "para" | "breakline" | "tab" | ...
    var: Optional[str] = None                 # "pgno"


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
    """
    if frame.custom_path is not None:
        attrs["FRTYPE"] = "3"
        attrs["path"] = frame.custom_path
        attrs["copath"] = frame.custom_path
    elif frame.corner_radius_mm > 0:
        radrect_pt = mm_to_pt(frame.corner_radius_mm)
        attrs["FRTYPE"] = "2"
        attrs["RADRECT"] = _fmt_num(radrect_pt)
        # When custom_path isn't passed, fall back to a plain rectangle path.
        # The converter will normally pass the original's bezier-rounded path
        # via custom_path so RADRECT alone is rare in round-trip mode.
        attrs["path"] = default_path
        attrs["copath"] = default_path
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
    attrs["SOFTSHADOWERASEDBYOBJECT"] = "1" if ss.erase else "0"
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
    next_item: Optional["TextFrame"] = field(default=None, repr=False, compare=False)
    # Internal: pre-allocated ItemID for chain ordering. Set by Document._build_xml.
    _preallocated_id: Optional[int] = field(default=None, repr=False, compare=False)

    def link_to(self, other: "TextFrame") -> "TextFrame":
        """Chain self -> other. Returns ``other`` for fluent chains
        (``a.link_to(b).link_to(c)``)."""
        self.next_item = other
        return other

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = mm_to_pt(self.w_mm), mm_to_pt(self.h_mm)
        item_id = self._preallocated_id if self._preallocated_id is not None else idgen.next()
        rect_path = f"M0 0 L{w_pt:.3f} 0 L{w_pt:.3f} {h_pt:.3f} L0 {h_pt:.3f} L0 0 Z"
        attrs = {
            "XPOS": f"{x:.6f}", "YPOS": f"{y:.6f}",
            "OwnPage": str(page.own_page),
            "ItemID": str(item_id),
            "PTYPE": "4",
            "WIDTH": f"{w_pt:.6f}", "HEIGHT": f"{h_pt:.6f}",
            "CLIPEDIT": "0", "PWIDTH": "0",
            "PLINEART": "1", "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "PICART": "1", "SCALETYPE": "1", "RATIO": "1",
            "COLUMNS": str(self.columns), "COLGAP": f"{mm_to_pt(self.col_gap_mm):.6f}",
            "AUTOTEXT": "0", "EXTRA": "0", "TEXTRA": "0", "BEXTRA": "0", "REXTRA": "0",
            "VAlign": "0", "FLOP": "1", "PLTSHOW": "0", "BASEOF": "0",
            "textPathType": "0", "textPathFlipped": "0",
            "gXpos": f"{x:.6f}", "gYpos": f"{y:.6f}",
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": f"{self.rotation_deg:.6f}",
        }
        _apply_shape_attrs(attrs, self, w_pt, h_pt,
                            default_path=rect_path, default_frtype="0")
        _apply_soft_shadow(attrs, self.soft_shadow)
        if self.text_align is not None:
            attrs["ALIGN"] = str(self.text_align)
        if self.anname:
            attrs["ANNAME"] = self.anname
        po = etree.Element("PAGEOBJECT", attrib=attrs)
        story = etree.SubElement(po, "StoryText")
        ds = etree.SubElement(story, "DefaultStyle")
        if self.style:
            ds.set("PARENT", self.style)

        # Emit ITEXT runs
        if self.runs:
            run_list = [_normalise_run(r) for r in self.runs]
            for r in run_list:
                # ITEXT element with the run's text and per-run overrides
                it = etree.SubElement(story, "ITEXT")
                it.set("CH", r.text)
                _apply_run_attrs(it, r)
                # Separator between this run and the next
                if r.separator == "para":
                    para = etree.SubElement(story, "para")
                    if self.style:
                        para.set("PARENT", self.style)
                elif r.separator == "breakline":
                    etree.SubElement(story, "breakline")
                elif r.separator == "tab":
                    etree.SubElement(story, "tab")
                elif r.separator == "breakcol":
                    etree.SubElement(story, "breakcol")
                elif r.separator == "breakframe":
                    etree.SubElement(story, "breakframe")
                # Variable insert (e.g. <var name="pgno"/>)
                if r.var is not None:
                    var = etree.SubElement(story, "var")
                    var.set("name", r.var)
        elif self.text:
            it = etree.SubElement(story, "ITEXT")
            it.set("CH", self.text)
            if self.fcolor:
                it.set("FCOLOR", self.fcolor)
        # Trail keeps Scribus happy (carries final paragraph style)
        trail = etree.SubElement(story, "trail")
        if self.style:
            trail.set("PARENT", self.style)
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

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = mm_to_pt(self.w_mm), mm_to_pt(self.h_mm)
        rect_path = f"M0 0 L{w_pt:.3f} 0 L{w_pt:.3f} {h_pt:.3f} L0 {h_pt:.3f} L0 0 Z"
        pfile = self.image or self.src
        scx, scy = self.local_scale
        lx_mm, ly_mm = self.local_offset_mm
        attrs = {
            "XPOS": f"{x:.6f}", "YPOS": f"{y:.6f}",
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "2",
            "WIDTH": f"{w_pt:.6f}", "HEIGHT": f"{h_pt:.6f}",
            "CLIPEDIT": "0", "PWIDTH": "0",
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
            "gXpos": f"{x:.6f}", "gYpos": f"{y:.6f}",
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": f"{self.rotation_deg:.6f}",
        }
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
    fill: str = "Black"           # color name from Color enum
    line_color: str = "None"
    line_width_pt: float = 0
    layer: int = 0                # default Hintergrund
    shape: str = "rectangle"      # 'rectangle' | 'ellipse'
    fill_shade: int = 100         # SHADE — emitted when != 100

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = mm_to_pt(self.w_mm), mm_to_pt(self.h_mm)
        if self.shape == "ellipse":
            default_path = self._ellipse_path(w_pt, h_pt)
            default_frtype = "1"  # FRTYPE=1 = ellipse
        else:
            default_path = f"M0 0 L{w_pt:.3f} 0 L{w_pt:.3f} {h_pt:.3f} L0 {h_pt:.3f} L0 0 Z"
            default_frtype = "0"
        attrs = {
            "XPOS": f"{x:.6f}", "YPOS": f"{y:.6f}",
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "6",
            "WIDTH": f"{w_pt:.6f}", "HEIGHT": f"{h_pt:.6f}",
            "CLIPEDIT": "0",
            "PCOLOR": self.fill,
            "PCOLOR2": self.line_color,
            "PWIDTH": f"{self.line_width_pt:.6f}",
            "PLINEART": "1", "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "PICART": "1", "SCALETYPE": "1", "RATIO": "1",
            "gXpos": f"{x:.6f}", "gYpos": f"{y:.6f}",
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": f"{self.rotation_deg:.6f}",
        }
        _apply_shape_attrs(attrs, self, w_pt, h_pt,
                            default_path=default_path, default_frtype=default_frtype)
        _apply_soft_shadow(attrs, self.soft_shadow)
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
            "XPOS": f"{x_origin:.6f}", "YPOS": f"{y_origin:.6f}",
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "5",
            "WIDTH": f"{length:.6f}", "HEIGHT": "1",
            "FRTYPE": "3", "CLIPEDIT": "0",
            "PCOLOR": "None", "PCOLOR2": self.color,
            "PWIDTH": f"{self.width_pt:.6f}",
            "PLINEART": "1", "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "ROT": f"{angle:.6f}",
            "path": f"M0 0 L{length:.3f} 0",
            "copath": f"M0 0 L{length:.3f} 0",
            "gXpos": f"{x_origin:.6f}", "gYpos": f"{y_origin:.6f}",
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
        }
        if self.anname:
            attrs["ANNAME"] = self.anname
        return etree.Element("PAGEOBJECT", attrib=attrs)
