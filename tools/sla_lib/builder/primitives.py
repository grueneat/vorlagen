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
from .document import mm_to_pt

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

    def _xy_pt(self, page) -> tuple[float, float]:
        """Return absolute XPOS/YPOS in scratch canvas space."""
        if self.anchor is not None:
            local_x, local_y = resolve_anchor(self.anchor, page.width_pt, page.height_pt,
                                              mm_to_pt(self.w_mm), mm_to_pt(self.h_mm))
        else:
            local_x = mm_to_pt(self.x_mm)
            local_y = mm_to_pt(self.y_mm)
        return page.page_xpos_pt + local_x, page.page_ypos_pt + local_y


# ---------------------------------------------------------------------------
# TextFrame
# ---------------------------------------------------------------------------
@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""           # paragraph style name (e.g. Style.BODY_12)
    fcolor: str = ""          # override color (e.g. Color.WHITE)
    runs: Optional[list] = None  # list of (text, style_override) tuples for multi-run
    columns: int = 1
    col_gap_mm: float = 4

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = mm_to_pt(self.w_mm), mm_to_pt(self.h_mm)
        attrs = {
            "XPOS": f"{x:.6f}", "YPOS": f"{y:.6f}",
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "4",
            "WIDTH": f"{w_pt:.6f}", "HEIGHT": f"{h_pt:.6f}",
            "FRTYPE": "0", "CLIPEDIT": "0", "PWIDTH": "0",
            "PLINEART": "1", "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "PICART": "1", "SCALETYPE": "1", "RATIO": "1",
            "COLUMNS": str(self.columns), "COLGAP": f"{mm_to_pt(self.col_gap_mm):.6f}",
            "AUTOTEXT": "0", "EXTRA": "0", "TEXTRA": "0", "BEXTRA": "0", "REXTRA": "0",
            "VAlign": "0", "FLOP": "1", "PLTSHOW": "0", "BASEOF": "0",
            "textPathType": "0", "textPathFlipped": "0",
            "path": f"M0 0 L{w_pt:.3f} 0 L{w_pt:.3f} {h_pt:.3f} L0 {h_pt:.3f} L0 0 Z",
            "copath": f"M0 0 L{w_pt:.3f} 0 L{w_pt:.3f} {h_pt:.3f} L0 {h_pt:.3f} L0 0 Z",
            "gXpos": f"{x:.6f}", "gYpos": f"{y:.6f}",
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": f"{self.rotation_deg:.6f}",
        }
        if self.anname:
            attrs["ANNAME"] = self.anname
        po = etree.Element("PAGEOBJECT", attrib=attrs)
        story = etree.SubElement(po, "StoryText")
        ds = etree.SubElement(story, "DefaultStyle")
        if self.style:
            ds.set("PARENT", self.style)
        ds.set("LINESPMode", "2")

        # Emit ITEXT runs
        if self.runs:
            # multi-run: list of (text, optional style override) tuples
            for i, run in enumerate(self.runs):
                if isinstance(run, tuple):
                    text, override = run[0], run[1] if len(run) > 1 else None
                else:
                    text, override = run, None
                it = etree.SubElement(story, "ITEXT")
                it.set("CH", text)
                if override:
                    if "fcolor" in override:
                        it.set("FCOLOR", override["fcolor"])
                    if "fontsize" in override:
                        it.set("FONTSIZE", str(override["fontsize"]))
                if i < len(self.runs) - 1:
                    if isinstance(run, tuple) and len(run) > 2 and run[2] == "para":
                        para = etree.SubElement(story, "para")
                        if self.style:
                            para.set("PARENT", self.style)
                    else:
                        etree.SubElement(story, "breakline")
        else:
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
    layer: int = 1            # default Bilder layer

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = mm_to_pt(self.w_mm), mm_to_pt(self.h_mm)
        attrs = {
            "XPOS": f"{x:.6f}", "YPOS": f"{y:.6f}",
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "2",
            "WIDTH": f"{w_pt:.6f}", "HEIGHT": f"{h_pt:.6f}",
            "FRTYPE": "0", "CLIPEDIT": "0", "PWIDTH": "0",
            "PLINEART": "1", "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "PICART": "1", "SCALETYPE": "1", "RATIO": "1",
            "PFILE": self.src,
            "PRFILE": "sRGB display profile (ICC v2.2)",
            "IRENDER": "0",
            "path": f"M0 0 L{w_pt:.3f} 0 L{w_pt:.3f} {h_pt:.3f} L0 {h_pt:.3f} L0 0 Z",
            "copath": f"M0 0 L{w_pt:.3f} 0 L{w_pt:.3f} {h_pt:.3f} L0 {h_pt:.3f} L0 0 Z",
            "gXpos": f"{x:.6f}", "gYpos": f"{y:.6f}",
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": f"{self.rotation_deg:.6f}",
        }
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

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = mm_to_pt(self.w_mm), mm_to_pt(self.h_mm)
        if self.shape == "ellipse":
            # 4-bezier-arc ellipse approximation
            path = self._ellipse_path(w_pt, h_pt)
            frtype = "1"  # FRTYPE=1 = ellipse
        else:
            path = f"M0 0 L{w_pt:.3f} 0 L{w_pt:.3f} {h_pt:.3f} L0 {h_pt:.3f} L0 0 Z"
            frtype = "0"  # rectangle
        attrs = {
            "XPOS": f"{x:.6f}", "YPOS": f"{y:.6f}",
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "6",
            "WIDTH": f"{w_pt:.6f}", "HEIGHT": f"{h_pt:.6f}",
            "FRTYPE": frtype, "CLIPEDIT": "0",
            "PCOLOR": self.fill,
            "PCOLOR2": self.line_color,
            "PWIDTH": f"{self.line_width_pt:.6f}",
            "PLINEART": "1", "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "PICART": "1", "SCALETYPE": "1", "RATIO": "1",
            "path": path, "copath": path,
            "gXpos": f"{x:.6f}", "gYpos": f"{y:.6f}",
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": f"{self.rotation_deg:.6f}",
        }
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
