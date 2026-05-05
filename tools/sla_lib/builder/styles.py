"""Typed style and layer dataclasses for per-document overrides.

These types let templates declare document-local layers, paragraph styles,
character styles, and soft-shadow effects without polluting ``shared/ci.yml``
or relying on a ``raw_attrs`` escape hatch (CONTEXT.md D2).

Each field is ``Optional`` (``None`` = inherit from parent / default). The
emitter writes only attributes whose value is not ``None``, so STYLE
inheritance is preserved correctly.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DocumentLayer:
    """A single LAYERS element. Use ``Document(layers=[...])`` to override the
    default 4-layer brand stack (Hintergrund / Bilder / Text / Hilfslinien)."""
    name: str
    visible: bool = True
    printable: bool = True
    editable: bool = True
    flow: bool = True
    transparent: float = 1.0
    blend: int = 0
    outline: bool = False
    layer_color: str = "#000000"


@dataclass(frozen=True)
class ParaStyle:
    """A paragraph style (Scribus ``<STYLE>`` element).

    Every field except ``name`` is optional. ``None`` means inherit from the
    parent style (or rely on Scribus's default). The emitter writes only
    attributes whose value is not ``None`` so PARENT inheritance works.
    """
    name: str
    parent: Optional[str] = None
    font: Optional[str] = None
    fontsize: Optional[float] = None
    fcolor: Optional[str] = None
    align: Optional[int] = None
    linesp: Optional[float] = None
    linesp_mode: Optional[int] = None
    language: Optional[str] = None
    # Paragraph spacing
    space_before_pt: Optional[float] = None  # VOR
    space_after_pt: Optional[float] = None   # NACH
    # Indent
    first_indent_pt: Optional[float] = None  # FIRST
    left_indent_pt: Optional[float] = None   # INDENT
    right_indent_pt: Optional[float] = None  # RMARGIN
    # Hyphenation
    hyph_consecutive_lines: Optional[int] = None
    hyph_word_min: Optional[int] = None
    # Drop cap
    drop_cap: Optional[bool] = None          # DROP
    drop_lines: Optional[int] = None         # DROPLIN
    # Tracking
    min_word_track: Optional[float] = None   # MinWordTrack
    min_glyph_shrink: Optional[float] = None # MinGlyphShrink
    max_glyph_extend: Optional[float] = None # MaxGlyphExtend
    # Keep
    keep_together: Optional[bool] = None     # KeepTogether
    keep_lines_start: Optional[int] = None   # KeepLinesStart
    # Direction
    direction: Optional[int] = None          # DIRECTION
    # Background
    bcolor: Optional[str] = None             # BCOLOR
    bshade: Optional[int] = None             # BSHADE
    # Char-style passthrough on the para's default char style
    fontfeatures: Optional[str] = None       # FONTFEATURES
    features: Optional[str] = None           # FEATURES
    kern: Optional[float] = None             # KERN
    scalev: Optional[int] = None             # SCALEV (vertical scale, integer percent)
    fshade: Optional[int] = None             # FSHADE
    txt_underline_pos: Optional[int] = None  # TXTULP
    txt_underline_width: Optional[int] = None  # TXTULW
    txt_strike_pos: Optional[int] = None     # TXTSTP
    txt_strike_width: Optional[int] = None   # TXTSTW
    txt_shadow_x: Optional[int] = None       # TXTSHX
    txt_shadow_y: Optional[int] = None       # TXTSHY
    txt_outline: Optional[int] = None        # TXTOUT
    baseline_offset: Optional[int] = None    # BASEO
    paragraph_effect_offset: Optional[float] = None  # ParagraphEffectOffset
    bullet: Optional[str] = None             # Bullet
    numeration: Optional[int] = None         # Numeration
    is_default: bool = False                 # DefaultStyle="1"


@dataclass(frozen=True)
class CharStyle:
    """A character style (Scribus ``<CHARSTYLE>`` element)."""
    name: str
    font: Optional[str] = None
    fontsize: Optional[float] = None
    fcolor: Optional[str] = None
    fshade: Optional[int] = None
    fontfeatures: Optional[str] = None
    features: Optional[str] = None
    kern: Optional[float] = None
    is_default: bool = False


@dataclass(frozen=True)
class SoftShadow:
    """Frame-level soft-shadow effect. ``None`` -> no shadow on the frame."""
    color: str = "Black"
    blur_radius_pt: float = 8.504
    x_offset_pt: float = 1.984
    y_offset_pt: float = 1.984
    blend_mode: int = 1
    opacity: float = 0.0
    shade: int = 100
    erase: bool = False
    object_trans: bool = False
