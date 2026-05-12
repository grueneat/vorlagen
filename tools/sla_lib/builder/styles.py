"""Typed style and layer dataclasses for per-document overrides.

These types let templates declare document-local layers, paragraph styles,
character styles, and soft-shadow effects without polluting ``shared/ci.yml``
or relying on a ``raw_attrs`` escape hatch (CONTEXT.md D2).

Each field is ``Optional`` (``None`` = inherit from parent / default). The
emitter writes only attributes whose value is not ``None``, so STYLE
inheritance is preserved correctly.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple


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
    txt_underline_pos: Optional[float] = None  # TXTULP
    txt_underline_width: Optional[float] = None  # TXTULW
    txt_strike_pos: Optional[float] = None     # TXTSTP
    txt_strike_width: Optional[float] = None   # TXTSTW
    txt_shadow_x: Optional[int] = None       # TXTSHX
    txt_shadow_y: Optional[int] = None       # TXTSHY
    txt_outline: Optional[int] = None        # TXTOUT
    baseline_offset: Optional[int] = None    # BASEO
    paragraph_effect_offset: Optional[float] = None  # ParagraphEffectOffset
    bullet: Optional[str] = None             # Bullet (Scribus stores codepoint
                                              # number as string; we treat as opaque)
    numeration: Optional[int] = None         # Numeration
    is_default: bool = False                 # DefaultStyle="1"
    # Tab stops — list of (position_pt, type) tuples.
    # type: 0=left, 1=right, 2=center, 3=decimal (matches Scribus Tabs Type attr).
    # Emitted as child <Tabs Type="..." Pos="..." Fill=""/> elements of <STYLE>.
    # None (default) = no custom tab stops (Scribus uses document default tab width).
    tab_stops: Optional[Tuple[Tuple[float, int], ...]] = None


@dataclass(frozen=True)
class CharStyle:
    """A character style (Scribus ``<CHARSTYLE>`` element).

    Scribus's CHARSTYLE carries far more attributes than an ITEXT does (it
    is the *default* character style applied to every paragraph). Optional
    fields cover everything used in our originals.
    """
    name: str
    font: Optional[str] = None
    fontsize: Optional[float] = None
    fcolor: Optional[str] = None
    fshade: Optional[int] = None
    fontfeatures: Optional[str] = None
    features: Optional[str] = None
    kern: Optional[float] = None
    language: Optional[str] = None       # LANGUAGE
    hyph_word_min: Optional[int] = None  # HyphenWordMin
    scolor: Optional[str] = None         # SCOLOR (stroke color)
    sshade: Optional[int] = None         # SSHADE
    bgcolor: Optional[str] = None        # BGCOLOR (background)
    bgshade: Optional[int] = None        # BGSHADE
    txt_shadow_x: Optional[int] = None   # TXTSHX
    txt_shadow_y: Optional[int] = None   # TXTSHY
    txt_outline: Optional[int] = None    # TXTOUT
    txt_underline_pos: Optional[float] = None    # TXTULP
    txt_underline_width: Optional[float] = None  # TXTULW
    txt_strike_pos: Optional[float] = None       # TXTSTP
    txt_strike_width: Optional[float] = None     # TXTSTW
    scaleh: Optional[int] = None         # SCALEH (horizontal scale %)
    scalev: Optional[int] = None         # SCALEV (vertical scale %)
    baseline_offset: Optional[int] = None  # BASEO
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
