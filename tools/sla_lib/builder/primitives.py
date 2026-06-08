"""Low-level frame primitives that emit valid PAGEOBJECT XML.

Each primitive accepts mm coordinates and an optional anchor for sugar.
Internally everything converts to pt and adds the page's scratch-canvas
offset (page_xpos_pt + page_ypos_pt) to produce the absolute XPOS/YPOS that
Scribus expects.

PTYPE values from `pageitem.h::ItemType`:
  2 = ImageFrame, 4 = TextFrame, 5 = Line, 6 = Polygon, 7 = PolyLine.
"""
from __future__ import annotations
import base64
import struct
import warnings
import zlib
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

# ---------------------------------------------------------------------------
# Anchor — canonical named-args form + legacy string/tuple adapters
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Anchor:
    """Canonical position anchor for frame placement.

    Use the named-args form for new code:

        Anchor(h="center", v="bottom", margin_mm=20)

    Accepted values:
      h: "left" | "center" | "right"  (horizontal)
      v: "top"  | "center" | "bottom" (vertical)
      margin_mm: float  (offset from the h/v edge, default 0)

    Legacy forms still work (with a DeprecationWarning):
      - string: ``"bottom-20"`` → ``Anchor.from_legacy("bottom-20")``
      - tuple:  ``("center", 30)`` → ``Anchor.from_legacy(("center", 30))``

    The legacy ``_LegacyAnchor`` union type alias is kept for internal
    backward-compat in ``resolve_anchor()``.
    """
    h: str = "left"   # "left" | "center" | "right"
    v: str = "top"    # "top"  | "center" | "bottom"
    margin_mm: float = 0.0

    def __post_init__(self) -> None:
        if self.h not in ("left", "center", "right"):
            raise ValueError(f"Anchor h= must be 'left', 'center', or 'right'; got {self.h!r}")
        if self.v not in ("top", "center", "bottom"):
            raise ValueError(f"Anchor v= must be 'top', 'center', or 'bottom'; got {self.v!r}")

    @staticmethod
    def from_legacy(spec: "Union[str, tuple]") -> "Anchor":
        """Parse the legacy string/tuple anchor form and return an ``Anchor``.

        Emits a DeprecationWarning.  Supported legacy forms:
          - ``"bottom-20"`` → ``Anchor(v="bottom", margin_mm=20)``
          - ``"center"``   → ``Anchor(h="center", v="center")``
          - ``"top-left"`` → ``Anchor(h="left", v="top")``
          - ``(h_spec, v_spec)`` tuple where each component is a string or mm float
        """
        warnings.warn(
            f"Anchor legacy form {spec!r} is deprecated; use "
            f"Anchor(h=..., v=..., margin_mm=...) instead.",
            DeprecationWarning, stacklevel=2,
        )
        return _parse_legacy_anchor(spec)

    @classmethod
    def from_page(cls, where: str, x_offset_mm: float = 0, y_offset_mm: float = 0) -> "Anchor":
        """DEPRECATED: Create anchor from page corner with optional offsets."""
        # For simplicity, we just use the (x, y) tuple legacy form
        return cls.from_legacy((x_offset_mm, y_offset_mm))


def _parse_legacy_anchor(spec: "Union[str, tuple]") -> Anchor:
    """Internal parser for legacy anchor specs (no warning emitted here)."""
    if isinstance(spec, str):
        if spec == "center":
            return Anchor(h="center", v="center")
        parts = spec.split("-")
        if len(parts) == 2:
            first, second = parts
            # Try to interpret as "v-h" (e.g. "top-left", "bottom-center")
            v_map = {"top": "top", "bottom": "bottom", "center": "center"}
            h_map = {"left": "left", "right": "right", "center": "center"}
            if first in v_map and second in h_map:
                return Anchor(h=h_map[second], v=v_map[first])
            # "bottom-20" style: first=edge, second=mm margin
            try:
                margin = float(second)
                if first in ("bottom", "top"):
                    return Anchor(v=first, margin_mm=margin)
                if first in ("left", "right"):
                    return Anchor(h=first, margin_mm=margin)
            except ValueError:
                pass
        raise ValueError(f"Unknown legacy anchor string: {spec!r}")
    if isinstance(spec, tuple):
        # (h_spec, v_spec) — both can be mm floats or alignment strings
        if len(spec) != 2:
            raise ValueError(f"Anchor tuple must be (h_spec, v_spec); got {spec!r}")
        return _Anchor_from_tuple(spec)
    raise ValueError(f"Unsupported anchor spec: {spec!r}")


def _Anchor_from_tuple(spec: tuple) -> Anchor:
    h_spec, v_spec = spec
    h = "left"
    v = "top"
    margin_mm = 0.0
    if isinstance(h_spec, str):
        h_map = {"left": "left", "center": "center", "right": "right",
                 "top": "center", "bottom": "center"}
        if h_spec in h_map:
            h = h_map[h_spec]
        elif "-" in h_spec:
            base, off = h_spec.split("-", 1)
            h = base if base in ("left", "center", "right") else "left"
            margin_mm = float(off)
    elif isinstance(h_spec, (int, float)):
        # Absolute mm position: encode as left with a margin
        h = "left"
        margin_mm = float(h_spec)
    if isinstance(v_spec, str):
        v_map = {"top": "top", "center": "center", "bottom": "bottom"}
        if v_spec in v_map:
            v = v_map[v_spec]
        elif "-" in v_spec:
            base, off = v_spec.split("-", 1)
            v = base if base in ("top", "center", "bottom") else "top"
    elif isinstance(v_spec, (int, float)):
        v = "top"
    return Anchor(h=h, v=v, margin_mm=margin_mm)


# Legacy union type alias kept for backward compat in resolve_anchor signature.
_LegacyAnchor = Union[str, tuple]


def resolve_anchor(anchor: "Union[Anchor, str, tuple]",
                   page_w_pt: float, page_h_pt: float,
                   item_w_pt: float, item_h_pt: float) -> tuple[float, float]:
    """Resolve an anchor spec to (local_x_pt, local_y_pt) on the page.

    Accepts:
      - ``Anchor(h=, v=, margin_mm=)`` — canonical form
      - Legacy string: ``"top-center"``, ``"bottom-20"`` — deprecated
      - Legacy tuple: ``("center", 30)`` — deprecated
    """
    # Normalise to canonical Anchor dataclass.
    if isinstance(anchor, Anchor):
        a = anchor
    elif isinstance(anchor, (str, tuple)):
        # No warning here — caller (blocks / template) may have emitted one already.
        a = _parse_legacy_anchor(anchor)
    else:
        raise ValueError(f"Unsupported anchor type: {type(anchor)!r}")

    # Resolve horizontal component.
    if a.h == "center":
        x = (page_w_pt - item_w_pt) / 2
    elif a.h == "right":
        x = page_w_pt - item_w_pt - mm_to_pt(a.margin_mm)
    else:  # "left"
        x = mm_to_pt(a.margin_mm)

    # Resolve vertical component.
    if a.v == "center":
        y = (page_h_pt - item_h_pt) / 2
    elif a.v == "bottom":
        y = page_h_pt - item_h_pt - mm_to_pt(a.margin_mm)
    else:  # "top"
        y = mm_to_pt(a.margin_mm)

    return x, y


def _resolve_axis(spec, page_size_pt: float, item_size_pt: float, axis: str) -> float:
    """Legacy axis resolver — kept for backward compat with old tuple-form callers."""
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

# Project-wide default manual tracking (Scribus KERN, in %) applied to every
# ITEXT run that does not set its own ``kern``. The brand switched to Raleway,
# which runs loose; -3 % tightens letter and word spacing uniformly (the
# "Raleway -3" decision). Set to None to disable the default.
DEFAULT_KERN: float | None = -3.0

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
    # Uniform brand tracking: when a run sets no explicit KERN, apply the
    # project default (Raleway -3) so every text run is tracked consistently.
    if DEFAULT_KERN is not None and it.get("KERN") is None:
        it.set("KERN", _fmt_num(DEFAULT_KERN))


def _normalise_run(item, *, _internal: bool = False) -> Run:
    """Accept the legacy ``(text, dict, sep)`` tuple form too. Returns a Run.

    Non-internal callers passing a tuple receive a ``DeprecationWarning``.
    Pass ``_internal=True`` from blocks.py internals to suppress the warning.
    """
    if isinstance(item, Run):
        return item
    if isinstance(item, tuple):
        if not _internal:
            warnings.warn(
                "Run tuple form (text, dict, sep) is deprecated; "
                "use Run(text=..., fcolor=..., separator=...) instead.",
                DeprecationWarning, stacklevel=3,
            )
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
    # CLIPEDIT="1" in Scribus marks a frame whose clipping path has been
    # manually edited (Scribus then leaves the path alone on size change
    # instead of auto-regenerating it). Round-tripping this flag preserves
    # the original's clip-edit state — the Zeitung carries it on 87 of 146
    # frames, and Scribus subtly renormalises clip paths when the flag is
    # absent on load, which causes character-level glyph drift in the
    # rendered PDF.
    clip_edit: bool = False
    # Verbatim XPOS/YPOS/WIDTH/HEIGHT in pt overrides for byte-equivalent
    # round-trip. The default mm ↔ pt conversion (x_mm * MM_TO_PT) is
    # round-trip stable for most values, but a handful of inline-image
    # frames in the Zeitung carry HEIGHT="27.7755590551181" (13-digit
    # repr) while the round-trip through mm gives "27.775559055118098"
    # (17-digit). The values differ at sub-ulp (1e-15) level — invisible
    # in rendering but enough to make the rebuilt SLA non-byte-equivalent
    # at this attribute. The converter sets these to the original
    # attribute strings so the emit path skips mm ↔ pt entirely for
    # round-trip frames.
    xpos_pt: Optional[float] = None
    ypos_pt: Optional[float] = None
    width_pt: Optional[float] = None
    height_pt: Optional[float] = None
    # Per-frame opt-in for intentional full-bleed feature elements (cover
    # photos, edge-to-edge spread halves, back-cover treatments). Frames
    # with ``is_full_bleed=True`` are exempt from ``brand:band_consistency``
    # band/margin checks. Issue #25 — replaces the per-page
    # ``excluded_pages`` escape hatch with an explicit per-frame marker so
    # the rule still TESTS every page; only individual feature frames opt
    # out, and the opt-out is visible at the frame definition.
    is_full_bleed: bool = False
    # Object opacity in [0.0, 1.0] (1.0 = fully opaque, the default). ``None``
    # leaves the PAGEOBJECT fully opaque (no TransValue attribute emitted —
    # matches the original SLAs which omit it). A value < 1.0 is written as
    # Scribus's TransValue/TransValueS, which store *transparency*
    # (1 - opacity): InDesign's BlendingSetting/Opacity=70 → opacity 0.7 →
    # TransValue 0.3.
    fill_opacity: Optional[float] = None

    def _xy_pt(self, page) -> tuple[float, float]:
        """Return absolute XPOS/YPOS in scratch canvas space."""
        # Verbatim pt overrides bypass the mm ↔ pt round-trip entirely.
        if self.xpos_pt is not None and self.ypos_pt is not None:
            return self.xpos_pt, self.ypos_pt
        if self.anchor is not None:
            local_x, local_y = resolve_anchor(self.anchor, page.width_pt, page.height_pt,
                                              mm_to_pt(self.w_mm), mm_to_pt(self.h_mm))
        else:
            local_x = mm_to_pt(self.x_mm)
            local_y = mm_to_pt(self.y_mm)
        return page.page_xpos_pt + local_x, page.page_ypos_pt + local_y

    def _wh_pt(self) -> tuple[float, float]:
        """Return WIDTH/HEIGHT in pt, honouring verbatim overrides."""
        if self.width_pt is not None and self.height_pt is not None:
            return self.width_pt, self.height_pt
        return mm_to_pt(self.w_mm), mm_to_pt(self.h_mm)


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


def _apply_fill_opacity(attrs: dict, fill_opacity: Optional[float]) -> None:
    """Emit Scribus TransValue/TransValueS when the frame is not fully opaque.

    Scribus stores object *transparency* (TransValue for fill, TransValueS
    for stroke) as ``1 - opacity``: 0 = opaque, 1 = invisible. The original
    SLAs omit the attribute entirely for opaque objects, so ``None`` (or a
    value within an ulp of 1.0) emits nothing — keeping opaque frames
    byte-identical to the round-trip baseline.
    """
    if fill_opacity is None:
        return
    op = max(0.0, min(1.0, fill_opacity))
    if abs(op - 1.0) < 1e-6:
        return
    trans = 1.0 - op
    attrs["TransValue"] = _fmt_num(trans)
    attrs["TransValueS"] = _fmt_num(trans)


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
    # VAlign attribute: vertical text alignment within the frame (0=top,
    # 1=center, 2=bottom). Scribus stores vertical text justification in the
    # PAGEOBJECT ``VAlign`` attribute — NOT ``ALIGN`` (which is the paragraph
    # horizontal-alignment default and has no vertical-centring effect).
    # ``vertical_text_align`` is the canonical name.  ``text_align`` is kept as
    # a backward-compat alias — both map to the PAGEOBJECT ``VAlign`` attribute.
    vertical_text_align: Optional[int] = None
    text_align: Optional[int] = None  # deprecated alias for vertical_text_align
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
    # First-line offset mode (Scribus FLOP attribute): controls where the
    # first baseline sits relative to the frame top.
    #   0 = Maximum Ascent   1 = Font Ascent   2 = Line Spacing   3 = Baseline Grid
    # InDesign's default FirstBaselineOffset is "AscentOffset" — first
    # baseline at the font ascent below the frame top — which maps to
    # Scribus FLOP=1. FLOP=2 (the legacy default) places the first baseline
    # a full LINESP below the top, ~5-6pt too low for body text. The
    # converter sets this per-frame from the IDML's FirstBaselineOffset; a
    # template may override it. None → the builder's default (FLOP=1).
    first_line_offset: Optional[int] = None
    next_item: Optional["TextFrame"] = field(default=None, repr=False, compare=False)
    # Internal: pre-allocated ItemID for chain ordering. Set by Document._build_xml.
    _preallocated_id: Optional[int] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate_paragraph_attrs(self.trail_attrs)
        _validate_defaultstyle_attrs(self.default_style_attrs)
        # Backward-compat alias: if caller used the deprecated text_align= kwarg,
        # migrate the value to vertical_text_align and emit a warning.
        if self.text_align is not None:
            warnings.warn(
                "TextFrame text_align= is deprecated; use vertical_text_align= instead.",
                DeprecationWarning, stacklevel=2,
            )
            if self.vertical_text_align is None:
                object.__setattr__(self, "vertical_text_align", self.text_align)
        # Multi-style-channel warning: setting both style= (paragraph style name)
        # and default_style_attrs= on the same frame is ambiguous — both target the
        # <DefaultStyle> element. The style= kwarg sets PARENT; default_style_attrs=
        # sets other attributes (FONT, FONTSIZE, FCOLOR, ALIGN, etc.). Using both is
        # allowed but requires the caller to understand that default_style_attrs=
        # takes effect AFTER PARENT is applied and may conflict with the named style.
        if self.style and self.default_style_attrs:
            warnings.warn(
                "TextFrame: setting both style= and default_style_attrs= on the same "
                "frame is ambiguous. style= sets the <DefaultStyle PARENT=...> and "
                "default_style_attrs= sets additional attributes on the same element "
                "(FONT, FONTSIZE, ALIGN, etc.). The default_style_attrs values apply "
                "AFTER the parent style and may override it. Consider using only "
                "style= for the named paragraph style.",
                UserWarning, stacklevel=2,
            )

    def link_to(self, other: "TextFrame") -> "TextFrame":
        """Chain self -> other. Returns ``other`` for fluent chains
        (``a.link_to(b).link_to(c)``)."""
        self.next_item = other
        return other

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = self._wh_pt()
        # Scribus computes text-flow width from the WIDTH attribute BEFORE
        # applying ROT. For frames rotated ~±90° the IDML "long axis" is
        # HEIGHT, so a narrow tall frame (e.g. rotated Impressum, 10×53mm
        # @ -90°) wraps after ~WIDTH/glyph_width characters instead of
        # running along its visible long edge. Swap WIDTH/HEIGHT and shift
        # origin so visible placement is invariant. Rotation around the
        # unrotated top-left:
        #   -90°: visible TL = (XPOS,     YPOS - W);  new YPOS = YPOS - W + H
        #   +90°: visible TL = (XPOS - H, YPOS);      new XPOS = XPOS + W - H
        #
        # The swap is a TEXT-FLOW compensation only. An empty TextFrame (no
        # text, no runs) — used as a coloured background-fill rectangle — has
        # nothing to flow, so the swap serves no purpose; applying it merely
        # mis-places the rectangle (the swap is not perfectly placement-
        # invariant when WIDTH != HEIGHT). Skip it for empty frames so a
        # rotated full-bleed background lands exactly where the converter's
        # geometry model (un-rotated WIDTH/HEIGHT + pivot) intends.
        _is_empty = not self.text and not self.runs
        if (
            abs(abs(self.rotation_deg) - 90.0) < 0.5
            and self.custom_path is None
            and not _is_empty
        ):
            if self.rotation_deg < 0:
                y = y - w_pt + h_pt
            else:
                x = x + w_pt - h_pt
            w_pt, h_pt = h_pt, w_pt
        item_id = self._preallocated_id if self._preallocated_id is not None else idgen.next()
        rect_path = _format_rect_path(w_pt, h_pt)
        attrs = {
            "XPOS": _fmt_num(x), "YPOS": _fmt_num(y),
            "OwnPage": str(page.own_page),
            "ItemID": str(item_id),
            "PTYPE": "4",
            "WIDTH": _fmt_num(w_pt), "HEIGHT": _fmt_num(h_pt),
            "CLIPEDIT": "1" if self.clip_edit else "0",
            "PWIDTH": _fmt_num(self.line_width_pt),
            "PLINEART": "1", "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "PICART": "1", "SCALETYPE": "1", "RATIO": "1",
            "COLUMNS": str(self.columns), "COLGAP": _fmt_num(mm_to_pt(self.col_gap_mm)),
            "AUTOTEXT": "0", "EXTRA": "0", "TEXTRA": "0", "BEXTRA": "0", "REXTRA": "0",
            # FLOP (first-line offset): InDesign's default FirstBaselineOffset
            # is "AscentOffset" — first baseline at the font ascent below the
            # frame top — which is Scribus FLOP=1 ("Font Ascent"). FLOP=2
            # ("Line Spacing") places the first baseline a full LINESP below
            # the top, ~5-6pt too low for body text (measured on the A6 flyer
            # body frames). Default FLOP=1; per-frame override via
            # TextFrame.first_line_offset (the converter sets it from the
            # IDML FirstBaselineOffset).
            "VAlign": "0",
            "FLOP": str(self.first_line_offset if self.first_line_offset is not None else 1),
            "PLTSHOW": "0", "BASEOF": "0",
            "textPathType": "0", "textPathFlipped": "0",
            "gXpos": _fmt_num(x), "gYpos": _fmt_num(y),
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": _fmt_num(self.rotation_deg),
        }
        # When clip_edit=True with no explicit custom_path, TextFrame auto-generates
        # the canonical rectangle clip path with FRTYPE=3.  This is the standard
        # Scribus representation for clipped text frames (corpus: 79 of 86 zeitung
        # CLIPEDIT=1 frames are PTYPE=4 FRTYPE=3 with a verbatim rect path).
        # Callers no longer need custom_path= for this common case.
        # Note: Polygon frames with clip_edit=True use FRTYPE=0 (their default)
        # and are NOT affected by this TextFrame-specific auto-generation.
        if self.clip_edit and self.custom_path is None and self.corner_radius_mm == 0:
            _apply_shape_attrs(attrs, self, w_pt, h_pt,
                                default_path=rect_path, default_frtype="3")
        else:
            _apply_shape_attrs(attrs, self, w_pt, h_pt,
                                default_path=rect_path, default_frtype="0")
        _apply_soft_shadow(attrs, self.soft_shadow)
        _apply_fill_opacity(attrs, self.fill_opacity)
        if self.fill is not None:
            attrs["PCOLOR"] = self.fill
        if self.line_color is not None:
            attrs["PCOLOR2"] = self.line_color
        # vertical_text_align= is canonical; text_align= is the deprecated alias.
        # Both were validated and merged in __post_init__ (text_align migrated to
        # vertical_text_align).  Use vertical_text_align as the authoritative
        # source.  Scribus stores vertical justification in PAGEOBJECT VAlign
        # (0=top / 1=center / 2=bottom); the default written above is "0".
        _eff_valign = self.vertical_text_align
        if _eff_valign is not None:
            attrs["VAlign"] = str(_eff_valign)
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
                    tab_el = etree.SubElement(story, "tab")
                    tab_el.set("FEATURES", "inherit")
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
def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """Encode raster bytes for ImageFrame.inline_image_data (qCompress format).

    Scribus's inline ImageData attribute is qCompress-encoded:
    base64( 4-byte big-endian uncompressed-length prefix + zlib_compress(image_bytes) ).
    Naive base64 of raw bytes makes Scribus abort with qUncompress: Z_DATA_ERROR.

    Returns (qcompressed_b64, ext) — pass to ImageFrame as
    inline_image_data=..., inline_image_ext=ext.
    """
    blob = struct.pack(">I", len(image_bytes)) + zlib.compress(image_bytes, 6)
    return base64.b64encode(blob).decode("ascii"), ext


@dataclass
class ImageFrame(_Frame):
    src: str = ""             # PFILE path (absolute or relative-to-SLA)
    image: str = ""           # alias for src; converter prefers `image=`
    layer: int = 1            # default Bilder layer
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    # SCALETYPE: 0 = scale image to frame (fit-to-frame, preserves aspect),
    # 1 = free scaling (use LOCALSCX/LOCALSCY). Default 0 because
    #   (a) it matches the IDML convention (the image is sized to the frame
    #       and any explicit ItemTransform scale is conceptually a
    #       fit-to-frame adjustment Scribus reproduces automatically), and
    #   (b) Scribus 1.6.x has a CMYK conversion bug that turns
    #       white-on-transparent RGBA PNGs INVISIBLE when SCALETYPE=1 with a
    #       high downscale ratio (frame << source). Issue 37 Backport 10.
    scale_type: int = 0       # SCALETYPE
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
    image_profile: str = "sRGB display profile (ICC v2.2)"  # PRFILE per-frame

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = self._wh_pt()
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
            "CLIPEDIT": "1" if self.clip_edit else "0",
            "PWIDTH": _fmt_num(self.line_width_pt),
            "PLINEART": "1",
            "LOCALSCX": _fmt_num(scx), "LOCALSCY": _fmt_num(scy),
            "LOCALX": _fmt_num(mm_to_pt(lx_mm)), "LOCALY": _fmt_num(mm_to_pt(ly_mm)),
            "LOCALROT": _fmt_num(self.local_rotation_deg),
            "PICART": str(self.pic_art),
            "SCALETYPE": str(self.scale_type),
            "RATIO": str(self.ratio),
            "PFILE": pfile,
            "PRFILE": self.image_profile,
            "IRENDER": "0",
            "gXpos": _fmt_num(x), "gYpos": _fmt_num(y),
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": _fmt_num(self.rotation_deg),
        }
        if is_inline:
            # Pagenumber=0 explicitly emitted to match the original SLA's
            # full attribute set on inline image frames. Scribus reads this
            # before isInlineImage; emitting both preserves byte-equivalence
            # at this attribute (functionally a no-op since 0 is the
            # default for ImageFrame's "image-of-page" reference).
            attrs["Pagenumber"] = "0"
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
        _apply_fill_opacity(attrs, self.fill_opacity)
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
    dash_pattern: Optional[tuple[float, ...]] = None  # (dash, gap, ...) in pt

    def to_pageobject(self, idgen, page) -> etree._Element:
        x, y = self._xy_pt(page)
        w_pt, h_pt = self._wh_pt()
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
            "CLIPEDIT": "1" if self.clip_edit else "0",
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
        _apply_fill_opacity(attrs, self.fill_opacity)
        if self.line_color is not None:
            attrs["PCOLOR2"] = self.line_color
        if self.fill_shade != 100:
            attrs["SHADE"] = str(self.fill_shade)
        if self.dash_pattern:
            attrs["DASHS"] = " ".join(_fmt_num(v) for v in self.dash_pattern)
            attrs["NUMDASH"] = str(len(self.dash_pattern))
            attrs["DASHOFF"] = "0"
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
# PolyLine  (PTYPE=7 — complex open/mixed path with stroke only)
# ---------------------------------------------------------------------------

@dataclass
class PolyLine:
    """A complex multi-segment polyline (PTYPE=7 in Scribus).

    Used for complex open or mixed-open/closed vector paths. Two shapes:

    * **stroked outline** — ``line_color`` set, ``fill`` left ``None``
      (PCOLOR stays ``"None"``). The canonical case is a wind turbine /
      logo / icon imported from an InDesign Polygon with multiple sub-paths.
    * **filled silhouette** — ``fill`` set to a colour name. PCOLOR emits
      the fill so closed bezier sub-paths paint as a solid shape. The
      canonical case is the Grüne yellow squiggle emphasis motif (a closed
      brush-stroke silhouette filled with Color/Yellow, drawn behind text).

    ``sla_path`` is a verbatim Scribus SLA SVG-like path string in **local
    points** (origin = frame top-left = 0,0). The frame bounding box
    (x_mm / y_mm / w_mm / h_mm) gives the page-relative position.

    Example::

        page.add(PolyLine(
            x_mm=123.507,
            y_mm=127.956,
            w_mm=48.986,
            h_mm=59.48,
            sla_path="M74.3 89.7 C80.8 89.7 ... L51.8 168.6",
            line_color="Gelb",
            line_width_pt=4.204,
            anname="u2b0",
        ))

    Filled-silhouette example (yellow squiggle, no stroke)::

        page.add(PolyLine(
            x_mm=14.8,
            y_mm=89.8,
            w_mm=19.2,
            h_mm=1.0,
            sla_path="M53.27 0.659 C46.44 0.318 ... Z",
            fill="Gelb",
            line_color="None",
            line_width_pt=0,
            anname="u11e3",
        ))
    """
    x_mm: float = 0
    y_mm: float = 0
    w_mm: float = 10
    h_mm: float = 10
    sla_path: str = "M0 0 L10 10"  # local-pt SVG path string
    line_color: str = "Black"
    line_width_pt: float = 1.0
    # Optional polygon fill (PCOLOR). When None the shape is stroke-only and
    # PCOLOR stays "None" — preserving the legacy stroked-outline behaviour.
    fill: Optional[str] = None
    layer: int = 0
    anname: str = ""
    rotation_deg: float = 0.0
    # Stroke cap/join styles map to Qt::PenCapStyle / Qt::PenJoinStyle values:
    #   PLINEEND: 0=FlatCap, 16=SquareCap, 32=RoundCap
    #   PLINEJOIN: 0=MiterJoin, 64=BevelJoin, 128=RoundJoin
    # IDML EndCap/EndJoin enum mapping (set by converter):
    #   "ButtEndCap" → 0, "ProjectingEndCap" → 16, "RoundEndCap" → 32
    #   "MiterEndJoin" → 0, "BevelEndJoin" → 64, "RoundEndJoin" → 128
    line_cap: Optional[int] = None   # PLINEEND; omitted from SLA when None
    line_join: Optional[int] = None  # PLINEJOIN; omitted from SLA when None

    def to_pageobject(self, idgen, page) -> etree._Element:
        x_pt = mm_to_pt(self.x_mm) + page.page_xpos_pt
        y_pt = mm_to_pt(self.y_mm) + page.page_ypos_pt
        w_pt = mm_to_pt(self.w_mm)
        h_pt = mm_to_pt(self.h_mm)
        attrs = {
            "XPOS": _fmt_num(x_pt),
            "YPOS": _fmt_num(y_pt),
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "7",
            "WIDTH": _fmt_num(w_pt),
            "HEIGHT": _fmt_num(h_pt),
            "FRTYPE": "3",
            "CLIPEDIT": "1",
            "PCOLOR": self.fill if self.fill is not None else "None",
            "PCOLOR2": self.line_color,
            "PWIDTH": _fmt_num(self.line_width_pt),
            "PLINEART": "1",
            "LOCALSCX": "1", "LOCALSCY": "1",
            "LOCALX": "0", "LOCALY": "0", "LOCALROT": "0",
            "PICART": "1", "SCALETYPE": "1", "RATIO": "1",
            "gXpos": _fmt_num(x_pt),
            "gYpos": _fmt_num(y_pt),
            "gWidth": "0", "gHeight": "0",
            "LAYER": str(self.layer),
            "NEXTITEM": "-1", "BACKITEM": "-1",
            "ROT": _fmt_num(self.rotation_deg),
            "path": self.sla_path,
            "copath": self.sla_path,
            "fillRule": "0",
        }
        if self.line_cap is not None:
            attrs["PLINEEND"] = str(self.line_cap)
        if self.line_join is not None:
            attrs["PLINEJOIN"] = str(self.line_join)
        if self.anname:
            attrs["ANNAME"] = self.anname
        return etree.Element("PAGEOBJECT", attrib=attrs)


# ---------------------------------------------------------------------------
# Line  (deprecated — kept for spec-input authoring only)
# ---------------------------------------------------------------------------
@dataclass
class Line:
    """A 2-point line primitive.

    .. deprecated::
        The SLA round-trip converter does NOT emit ``Line`` — it emits
        ``Polygon(custom_path=..., line_color=..., fill='None')`` instead,
        which is how Scribus represents lines internally (PTYPE=5 frames
        behave as a rotated polygon with a tiny path). Use ``Polygon`` for
        any programmatically authored line.

        ``Line`` is retained here for spec-input authoring contexts where a
        human-readable 2-point API is more expressive. Calling
        ``to_pageobject()`` emits a ``DeprecationWarning``.
    """
    x1_mm: float = 0
    y1_mm: float = 0
    x2_mm: float = 50
    y2_mm: float = 0
    color: str = "Black"
    width_pt: float = 1.0
    layer: int = 2
    anname: str = ""

    def to_pageobject(self, idgen, page) -> etree._Element:
        warnings.warn(
            "Line.to_pageobject() is deprecated. The SLA converter emits "
            "Polygon(custom_path=..., line_color=..., fill='None') instead. "
            "Use Polygon for round-trip-stable line output.",
            DeprecationWarning, stacklevel=2,
        )
        import math
        x1, y1 = mm_to_pt(self.x1_mm), mm_to_pt(self.y1_mm)
        x2, y2 = mm_to_pt(self.x2_mm), mm_to_pt(self.y2_mm)
        # Scribus stores lines as a frame with origin at min(x,y); width = dx, height = 0
        x_origin = min(x1, x2) + page.page_xpos_pt
        y_origin = min(y1, y2) + page.page_ypos_pt
        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        angle = math.degrees(math.atan2(dy, dx))
        attrs = {
            "XPOS": _fmt_num(x_origin), "YPOS": _fmt_num(y_origin),
            "OwnPage": str(page.own_page),
            "ItemID": str(idgen.next()),
            "PTYPE": "5",
            "WIDTH": _fmt_num(length), "HEIGHT": "1",
            "FRTYPE": "3", "CLIPEDIT": "0",  # Line has no clip-edit; fix AttributeError
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
