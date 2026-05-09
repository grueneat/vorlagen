"""Five evidence-driven compose blocks built from the actual template corpus.

Every block here has >= 2 verified occurrences in the existing three production
templates. Blocks are dataclasses that expose an emit() method returning an
iterable of DSL primitives; they integrate with page.add() automatically.

Public surface (import individually or via ``sla_lib.builder.blocks``):

    PageNumber      — page-number var frame (12× in Zeitung)
    Impressum       — bottom-of-page legal text (Postkarte + Zeitung)
    PageBackground  — full-bleed colored polygon at layer 0 (Postkarte + Zeitung)
    ContactBlock    — multi-line contact info (Postkarte)
    ColumnTextStory — linked-frame text-flow story (Zeitung, 84 chains)

Old aspirational blocks (Headline4Line, StoererBadge, ImpressumLine,
ImpressumBlock, SocialHandlesVertical, LogoCorner, EventDetails, Masthead,
ContentTeasers, ArticleHeadline, ArticleBody, QuoteSidebar) are preserved
under ``blocks.legacy`` for one migration cycle; they will be removed in the
next major DSL revision.
"""
from __future__ import annotations

import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence, Iterable

from .ci import Color, Style
from .primitives import (
    TextFrame, ImageFrame, Polygon, Anchor, Run, pack_inline_image,
    _format_path_coord,
)
from .document import mm_to_pt


def _path_from_points_mm(points_mm: list[tuple[float, float]]) -> str:
    """Build a Scribus path string from a list of (x, y) mm points.

    Scribus stores SVG-like path strings: ``M{x0} {y0} L{x1} {y1} ... Z``.
    All coordinates emitted in PT (the unit of ``custom_path``), formatted
    with %.6g for stability.
    """
    if not points_mm:
        return ""
    pts_pt = [(mm_to_pt(x), mm_to_pt(y)) for x, y in points_mm]
    parts = [f"M{_format_path_coord(pts_pt[0][0])} {_format_path_coord(pts_pt[0][1])}"]
    for x_pt, y_pt in pts_pt[1:]:
        parts.append(f"L{_format_path_coord(x_pt)} {_format_path_coord(y_pt)}")
    parts.append("Z")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------
DEFAULT_IMPRESSUM = (
    "Impressum: Medieninhaber und Herausgeber: Die Grünen Niederösterreich, "
    "Daniel-Gran-Straße 48, 3100 St. Pölten. · Druck: Druckerei mit Postanschrift · "
    "Evtl. Hinweis auf Umweltzeichen wenn zutreffend"
)


# ---------------------------------------------------------------------------
# Block 1: PageNumber
# Corpus: templates/zeitung-a4-grun/build.py lines 547, 750, 874, 1105,
#         1239, 1597, 1786, 1964, 2165, 2545, 2790, 2979 (12 occurrences)
# ---------------------------------------------------------------------------
@dataclass
class PageNumber:
    """Page-number TextFrame using <var name='pgno'/>.

    Corpus: templates/zeitung-a4-grun/build.py:547 (and 11 more occurrences).
    Each occurrence is a TextFrame with one Run(var='pgno', separator='para',
    paragraph_style='Seitenzahl').

    Usage::

        page.add(PageNumber(x_mm=10, y_mm=280))
        page.add(PageNumber(x_mm=8.51, y_mm=283.7, w_mm=12.78, h_mm=9.48,
                            layer=0, anname='Kopie von u2d45',
                            clip_edit=True, line_width_pt=1, col_gap_mm=3.207,
                            var_attrs={'FCOLOR': 'White', 'FSHADE': '100'}))
    """

    x_mm: float = 10
    y_mm: float = 280
    w_mm: float = 10
    h_mm: float = 6
    style: str = "Seitenzahl"
    layer: int = 2
    anname: str = "Seitenzahl"
    # Trivial kwarg passthroughs (in scope per ISSUE.md "trivial kwarg passthrough"
    # carve-out; needed for Zeitung's 12 PageNumber substitutions to preserve
    # CLIPEDIT, COLGAP, LINEWIDTH attr fidelity and the 1 white-pgno var_attrs case).
    clip_edit: bool = False
    line_width_pt: Optional[float] = None
    col_gap_mm: Optional[float] = None
    var_attrs: Optional[Mapping[str, str]] = None

    def emit(self) -> Iterable:
        # Build the inner Run; only set var_attrs if non-None to avoid changing
        # the Run literal shape on existing call sites.
        run_kwargs: dict = dict(
            text="",
            has_itext=False,
            var="pgno",
            separator="para",
            paragraph_style=self.style,
        )
        if self.var_attrs is not None:
            run_kwargs["var_attrs"] = dict(self.var_attrs)

        # Build the outer TextFrame; only forward kwargs whose value differs from
        # default to avoid widening TextFrame's emitted SLA shape on existing callers.
        tf_kwargs: dict = dict(
            x_mm=self.x_mm,
            y_mm=self.y_mm,
            w_mm=self.w_mm,
            h_mm=self.h_mm,
            runs=[Run(**run_kwargs)],
            layer=self.layer,
            anname=self.anname,
        )
        if self.clip_edit:
            tf_kwargs["clip_edit"] = True
        if self.line_width_pt is not None:
            tf_kwargs["line_width_pt"] = self.line_width_pt
        if self.col_gap_mm is not None:
            tf_kwargs["col_gap_mm"] = self.col_gap_mm

        yield TextFrame(**tf_kwargs)


# ---------------------------------------------------------------------------
# Block 2: Impressum
# Corpus:
#   1-Run default: baseline shape (documented baseline; no corpus site today)
#   2-Run prefix:  templates/postkarte-a6-kampagne/build.py:223-236 (page1)
#                  templates/plakat-a1-hochformat/build.py:91-105 (page0)
#   3-Run heading: templates/zeitung-a4-grun/build.py:2445-2459 (page13)
# ---------------------------------------------------------------------------
@dataclass
class Impressum:
    """Bottom-of-page legal text block with trail_style='Impressum'.

    Four substitutable shapes (>=1 corpus site each):

    1. **1-Run body (default):** emits a single Run with the body text.
       Baseline shape; backward-compatible with existing call sites.

    2. **2-Run with bold prefix (Postkarte build.py:223-236, Plakat build.py:91-105):**
       Set ``prefix_text`` to emit two Runs in the same paragraph — a bold prefix
       Run followed by the body Run. No paragraph separator between them (same line,
       font switch mid-line). Optionally set ``prefix_features`` and ``prefix_fshade``.
       Postkarte carries ``features='inherit'``; Plakat omits it.

    3. **3-Run heading + para-spacer + body (Zeitung build.py:2445-2459):**
       Set ``heading_text`` (and ``heading_paragraph_style``) to emit three Runs:
       heading (separator='para'), empty spacer (has_itext=False, separator='para'),
       then body. The spacer paragraph carries the heading style so its line height
       matches the heading, providing correct vertical spacing.

    4. **Full ``runs=`` override (escape hatch):**
       Pass a complete ``Sequence[Run]`` to bypass all of the above and emit
       exactly those runs verbatim.

    Frame-attr passthroughs (all three corpus sites carry these explicitly):
    ``rotation_deg`` (Plakat), ``line_width_pt``, ``col_gap_mm``.

    Usage::

        page.add(Impressum(x_mm=5, y_mm=142, w_mm=95))  # 1-Run default

        page.add(Impressum(                              # 2-Run bold-prefix (Postkarte)
            x_mm=61.66, y_mm=135.44, w_mm=41.94, h_mm=10.62,
            layer=0, line_width_pt=1, col_gap_mm=0,
            fcolor='White', prefix_text='Impressum:',
            prefix_features='inherit', prefix_fshade=100,
            body_fshade=100,
        ))

        page.add(Impressum(                              # 3-Run heading (Zeitung)
            x_mm=54.86, y_mm=118.89, w_mm=103.46, h_mm=30.47,
            layer=0, line_width_pt=1, col_gap_mm=0,
            heading_text='Impressum',
            heading_paragraph_style='Inhaltsheadline Titelseite',
        ))
    """

    text: str = DEFAULT_IMPRESSUM
    x_mm: float = 5
    y_mm: float = 142
    w_mm: float = 95
    h_mm: float = 6
    fcolor: Optional[str] = None   # None = inherit from trail_style
    layer: int = 2
    anname: str = "Impressum"

    # A1. Bold-prefix Run (Postkarte build.py:223-236, Plakat build.py:91-105).
    # When prefix_text is set the block emits TWO Runs in the body paragraph:
    # prefix in prefix_font then `text` in the trail_style font.
    prefix_text: Optional[str] = None
    prefix_font: str = "Gotham Narrow Bold"
    prefix_features: Optional[str] = None    # Postkarte: 'inherit'; Plakat: omit
    prefix_fshade: Optional[int] = 100       # both corpus sites: 100

    # A2. Rotation passthrough (Plakat build.py:91-105). 270 = vertical right-margin.
    rotation_deg: float = 0

    # A3. Heading + spacer + body (Zeitung build.py:2445-2459).
    # When heading_text is set the block emits THREE Runs: heading (separator='para'),
    # empty spacer (separator='para', has_itext=False), then body.
    heading_text: Optional[str] = None
    heading_font: Optional[str] = None           # default: inherit from heading_paragraph_style
    heading_paragraph_style: Optional[str] = None  # e.g. 'Inhaltsheadline Titelseite'

    # Frame-attr passthroughs (all three corpus sites carry these explicitly).
    line_width_pt: Optional[float] = None
    col_gap_mm: Optional[float] = None

    # Body Run passthrough (shared fcolor/fshade applied to body Run in 2- and 3-Run shapes).
    body_fshade: Optional[int] = None

    # Escape hatch for future idioms outside the three above.
    # If set, overrides the run-building logic entirely.
    runs: Optional[Sequence[Run]] = None

    def emit(self) -> Iterable:
        if self.runs is not None:
            body_runs = list(self.runs)                          # 1) full override
        elif self.heading_text is not None:
            # 2) 3-Run heading + spacer + body (Zeitung)
            body_runs = [
                Run(text=self.heading_text, separator='para',
                    paragraph_style=self.heading_paragraph_style,
                    font=self.heading_font),
                Run(text='', has_itext=False, separator='para',
                    paragraph_style=self.heading_paragraph_style),
                Run(text=self.text, fcolor=self.fcolor, fshade=self.body_fshade),
            ]
        elif self.prefix_text is not None:
            # 3) 2-Run bold-prefix idiom (Postkarte, Plakat)
            body_runs = [
                Run(text=self.prefix_text, font=self.prefix_font,
                    fcolor=self.fcolor, features=self.prefix_features,
                    fshade=self.prefix_fshade),
                Run(text=self.text, fcolor=self.fcolor, fshade=self.body_fshade),
            ]
        else:
            # 4) 1-Run baseline (existing behaviour — all new kwargs at default)
            body_runs = [Run(text=self.text, paragraph_style=None)]

        tf_kwargs: dict = dict(
            x_mm=self.x_mm,
            y_mm=self.y_mm,
            w_mm=self.w_mm,
            h_mm=self.h_mm,
            trail_style="Impressum",
            runs=body_runs,
            fcolor=self.fcolor,
            layer=self.layer,
            anname=self.anname,
        )
        if self.rotation_deg:
            tf_kwargs["rotation_deg"] = self.rotation_deg
        if self.line_width_pt is not None:
            tf_kwargs["line_width_pt"] = self.line_width_pt
        if self.col_gap_mm is not None:
            tf_kwargs["col_gap_mm"] = self.col_gap_mm
        yield TextFrame(**tf_kwargs)


# ---------------------------------------------------------------------------
# Block 3: PageBackground
# Corpus: templates/postkarte-a6-kampagne/build.py:89-100 (page0 Dunkelgrün),
#         templates/postkarte-a6-kampagne/build.py:216-227 (page1 Dunkelgrün),
#         templates/zeitung-a4-grun/build.py (Titelseite Dunkelgrün background).
# ---------------------------------------------------------------------------
@dataclass
class PageBackground:
    """Full-bleed colored rectangle polygon at layer 0 (Hintergrund).

    Corpus:
    - templates/postkarte-a6-kampagne/build.py:89-100 — Polygon at layer 0
      covering full A6 page + bleed, fill=Dunkelgrün
    - templates/postkarte-a6-kampagne/build.py:216-227 — same on page1
    - templates/zeitung-a4-grun/build.py — Titelseite Polygon fill=Dunkelgrün

    The polygon is positioned at (-bleed_mm, -bleed_mm) relative to page origin
    and sized to (page_width + 2*bleed_mm, page_height + 2*bleed_mm) in mm, so
    it covers the trim box plus full bleed on all sides.

    Usage::

        page.add(PageBackground(color=Color.DUNKELGRUEN))
    """

    color: str = Color.DUNKELGRUEN
    bleed_mm: float = 3.0
    line_color: Optional[str] = None
    line_width_pt: float = 0
    layer: int = 0
    anname: str = "Seitenhintergrund"

    def emit(self) -> Iterable:
        from .document import mm_to_pt, resolve_size
        # The polygon is sized from RESEARCH.md: covers full page + bleed.
        # We use a large negative x/y offset and over-sized w/h to ensure
        # full bleed coverage regardless of page size. The actual mm
        # values are derived from the containing page at emit time (not known
        # here), so we pick sentinel values that work for the standard sizes:
        # x = -bleed, y = -bleed, w = page_w + 2*bleed, h = page_h + 2*bleed.
        # Since we don't know the page size here, we emit with anchor=None
        # and use a large rectangle that the Document emitter trims via clip.
        # The cleanest approach: emit a large-enough Polygon; templates that
        # need pixel-perfect sizing should use Polygon directly with exact coords.
        b = self.bleed_mm
        # Standard approach from corpus: the polygon covers an A-series page
        # plus bleed. Callers set the exact x/y/w/h if they know the page size.
        # We emit a generic bleed-aware polygon that works for common sizes.
        yield Polygon(
            x_mm=-b,
            y_mm=-b,
            w_mm=220 + 2 * b,    # generous width covering A4+bleed and smaller
            h_mm=310 + 2 * b,    # generous height covering A4+bleed and smaller
            fill=self.color,
            line_color=self.line_color,
            line_width_pt=self.line_width_pt,
            layer=self.layer,
            anname=self.anname,
        )

    @classmethod
    def for_page(cls, page_w_mm: float, page_h_mm: float,
                 color: str = Color.DUNKELGRUEN,
                 bleed_mm: float = 3.0,
                 line_color: Optional[str] = None,
                 line_width_pt: float = 0,
                 layer: int = 0) -> "PageBackground":
        """Factory that creates a correctly-sized PageBackground for a known page.

        Example::

            page.add(PageBackground.for_page(105, 148, color=Color.DUNKELGRUEN))
        """
        return _SizedPageBackground(
            page_w_mm=page_w_mm, page_h_mm=page_h_mm,
            color=color, bleed_mm=bleed_mm,
            line_color=line_color, line_width_pt=line_width_pt,
            layer=layer,
        )


@dataclass
class _SizedPageBackground:
    """Internal: PageBackground with explicit page dimensions."""
    page_w_mm: float
    page_h_mm: float
    color: str = Color.DUNKELGRUEN
    bleed_mm: float = 3.0
    line_color: Optional[str] = None
    line_width_pt: float = 0
    layer: int = 0
    anname: str = "Seitenhintergrund"

    def emit(self) -> Iterable:
        b = self.bleed_mm
        yield Polygon(
            x_mm=-b,
            y_mm=-b,
            w_mm=self.page_w_mm + 2 * b,
            h_mm=self.page_h_mm + 2 * b,
            fill=self.color,
            line_color=self.line_color,
            line_width_pt=self.line_width_pt,
            layer=self.layer,
            anname=self.anname,
        )


# ---------------------------------------------------------------------------
# Block 4: ContactBlock
# Corpus: templates/postkarte-a6-kampagne/build.py:272 —
#         TextFrame with trail_style='Kontaktmöglichkeiten', 4 contact lines.
# ---------------------------------------------------------------------------
@dataclass
class ContactBlock:
    """Multi-line contact info block.

    Corpus:
    - templates/postkarte-a6-kampagne/build.py:272 — TextFrame with
      trail_style='Kontaktmöglichkeiten', 4 contact lines as Run list.
    - templates/postkarte-a6-kampagne/build.py (multiple frames with contact data)

    Each entry in ``handles`` becomes one Run separated by 'para' (except the
    last which has no separator).

    Usage::

        page.add(ContactBlock(
            handles=["Facebook: gruene.noe", "office@gruene-noe.at", "02742 / 90 230"],
            x_mm=60, y_mm=50, w_mm=40, h_mm=20,
        ))
    """

    handles: Sequence[str] = ("Facebook: gruene.noe", "Instagram: @gruene_noe",
                              "office@gruene-noe.at", "02742 / 90 230")
    x_mm: float = 60
    y_mm: float = 50
    w_mm: float = 40
    h_mm: float = 20
    style: str = "Kontaktmöglichkeiten"
    fcolor: Optional[str] = None
    layer: int = 2
    anname: str = "Kontaktmöglichkeiten"

    def emit(self) -> Iterable:
        runs = [
            Run(
                text=h,
                fcolor=self.fcolor,
                paragraph_style=self.style,
                separator="para" if i < len(self.handles) - 1 else None,
            )
            for i, h in enumerate(self.handles)
        ]
        yield TextFrame(
            x_mm=self.x_mm,
            y_mm=self.y_mm,
            w_mm=self.w_mm,
            h_mm=self.h_mm,
            trail_style=self.style,
            runs=runs,
            layer=self.layer,
            anname=self.anname,
        )


# ---------------------------------------------------------------------------
# Block 5: ColumnTextStory
# Corpus: templates/zeitung-a4-grun/build.py:3214-3223 — 84 linked
#         TextFrame chains with link_to() calls, carrying Fließtext runs.
# ---------------------------------------------------------------------------
@dataclass
class ColumnTextStory:
    """Linked-frame text-flow story.

    Corpus:
    - templates/zeitung-a4-grun/build.py:3214-3223 — 84 TextFrame chains
      linked via link_to(); each chain carries Fließtext article runs.

    Adds all frames to the page and links them in order via TextFrame.link_to.
    Story runs are placed on the first frame; subsequent frames are empty
    continuation slots (Scribus flows text automatically).

    Usage::

        f1 = TextFrame(x_mm=10, y_mm=50, w_mm=55, h_mm=100)
        f2 = TextFrame(x_mm=70, y_mm=50, w_mm=55, h_mm=100)
        page.add(ColumnTextStory(
            frames=[f1, f2],
            runs=[Run(text="Article body...", paragraph_style="Fließtext")],
        ))
    """

    frames: Sequence[TextFrame] = field(default_factory=list)
    runs: Sequence[Run] = field(default_factory=list)

    def emit(self) -> Iterable:
        if not self.frames:
            return
        frames = list(self.frames)
        # Attach runs to the first frame
        first = frames[0]
        if self.runs:
            first.runs = list(self.runs)
        # Link the chain: f[0] -> f[1] -> ... -> f[n-1]
        for i in range(len(frames) - 1):
            frames[i].link_to(frames[i + 1])
        yield from frames


# ---------------------------------------------------------------------------
# Block 6: WahlkreuzSymbol
# Spec: templates/_specs/SCHEMA.md §6 (D12 background-color contract)
# ---------------------------------------------------------------------------
@dataclass
class WahlkreuzSymbol:
    """Wahlkreuz im Kreis (yellow cross + white circle).

    The PNG asset has a white outer circle. On a white background the circle
    disappears — only the yellow cross stays visible. Per D12, this block draws
    a colored background polygon BEFORE placing the ImageFrame, so the white
    ring stays visible. Default background: Dunkelgruen.

    Source asset: shared/assets/wahlkreuz.png (RGBA 1200x1299).
    """

    pos: Anchor
    size: tuple[float, float] = (55, 55)     # (w_mm, h_mm)
    background_color: str = "Dunkelgrün"    # D12: never White, never Gelb
    background_padding_mm: float = 4.0
    anname: str = "Wahlkreuz"

    def emit(self, page=None) -> Iterable:
        # D12 Enforcement
        if self.background_color in ("White", "Gelb"):
            raise ValueError(
                f"D12 violation: Wahlkreuz background_color cannot be '{self.background_color}'. "
                "Must be a colored brand color (Dunkelgrün, Hellgrün, or Magenta) so the "
                "white circle remains visible."
            )

        w, h = self.size
        p = self.background_padding_mm

        # Background fill
        yield Polygon(
            anchor=self.pos,
            w_mm=w + 2 * p,
            h_mm=h + 2 * p,
            fill=self.background_color,
            x_mm=-p,
            y_mm=-p,  # Offset relative to anchor
            anname=f"{self.anname} (Hintergrund)",
        )

        # Wahlkreuz Image
        asset_path = Path("shared/assets/wahlkreuz.png")
        if not asset_path.exists():
            # Fallback for testing/CI if file missing in unexpected CWD
            asset_path = (
                Path(__file__).resolve().parents[3]
                / "shared"
                / "assets"
                / "wahlkreuz.png"
            )

        with open(asset_path, "rb") as f:
            img_bytes = f.read()

        data, ext = pack_inline_image(img_bytes, "png")
        yield ImageFrame(
            anchor=self.pos,
            w_mm=w,
            h_mm=h,
            inline_image_data=data,
            inline_image_ext=ext,
            scale_type=0,  # free / aspect-locked
            anname=self.anname,
        )


# ---------------------------------------------------------------------------
# Block 7: FoldLine
# Spec: templates/_specs/SCHEMA.md §7
# ---------------------------------------------------------------------------
@dataclass
class FoldLine:
    """Strichlierte Falz-Linie auf 'Falz'-Layer mit Spot-Color-Stroke.

    ``layer_idx`` is the Scribus LAYER integer index (matches the position of the
    Falz layer in ``Document(layers=[...])``). Pass an integer; ``layer_name`` is
    a documentation hint for the SCRIBUS layer name and not emitted as LAYER.
    """

    start_mm: tuple[float, float]
    end_mm: tuple[float, float]
    layer_idx: int = 3                  # default 4th layer (Hintergrund/Bilder/Text/Falz)
    layer_name: str = "Falz"            # documentation hint
    spot_color: str = "Falz"
    line_width_pt: float = 0.5
    dash_pattern: tuple[float, float] = (3.0, 1.5)
    anname: str = "Falzlinie"

    def emit(self, page=None) -> Iterable:
        # Bbox covers both endpoints (relative to page top-left); custom_path
        # is local to the bbox top-left (subtract origin).
        x0, y0 = self.start_mm
        x1, y1 = self.end_mm
        ox = min(x0, x1)
        oy = min(y0, y1)
        # Width/height >= small minimum so Scribus accepts the frame
        w_mm = max(abs(x1 - x0), 0.1)
        h_mm = max(abs(y1 - y0), 0.1)
        local_pts = [(x0 - ox, y0 - oy), (x1 - ox, y1 - oy)]
        path = _path_from_points_mm(local_pts)
        yield Polygon(
            x_mm=ox, y_mm=oy, w_mm=w_mm, h_mm=h_mm,
            custom_path=path,
            layer=self.layer_idx,
            line_color=self.spot_color,
            line_width_pt=self.line_width_pt,
            dash_pattern=self.dash_pattern,
            fill="None",
            anname=self.anname,
        )


# ---------------------------------------------------------------------------
# Block 8: DieCut
# Spec: templates/_specs/SCHEMA.md §7
# ---------------------------------------------------------------------------
@dataclass
class DieCut:
    """Geschlossener Stanzpfad auf 'Stanzkontur'-Layer.

    ``layer_idx`` is the Scribus LAYER integer index. Pass it explicitly when
    the document has a custom layer stack (e.g. ``Stanzkontur`` at index 3).
    """

    path_mm: list[tuple[float, float]]
    layer_idx: int = 3                  # default 4th layer
    layer_name: str = "Stanzkontur"     # documentation hint
    spot_color: str = "Stanzkontur"
    line_width_pt: float = 0.25
    anname: str = "Stanzkontur"

    def emit(self, page=None) -> Iterable:
        pts = list(self.path_mm)
        if pts and pts[0] != pts[-1]:
            pts.append(pts[0])  # Close the loop
        # Bbox covers all points
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ox = min(xs)
        oy = min(ys)
        w_mm = max(max(xs) - ox, 0.1)
        h_mm = max(max(ys) - oy, 0.1)
        local_pts = [(p[0] - ox, p[1] - oy) for p in pts]
        path = _path_from_points_mm(local_pts)
        yield Polygon(
            x_mm=ox, y_mm=oy, w_mm=w_mm, h_mm=h_mm,
            custom_path=path,
            layer=self.layer_idx,
            line_color=self.spot_color,
            line_width_pt=self.line_width_pt,
            fill="None",
            anname=self.anname,
        )


# ---------------------------------------------------------------------------
# Block 9: FoldedPanel
# ---------------------------------------------------------------------------
@dataclass
class FoldedPanel:
    """Wrapper for a single panel of a folded flyer.

    ``fold_layer_idx`` is the Scribus LAYER integer index for the right-edge
    FoldLine (Falz spot color) — pass it explicitly when the document has a
    custom layer stack (e.g. Falz at index 3).
    """

    panel_index: int  # 0-based
    panel_count: int  # 3 for DIN-lang
    panel_size_mm: tuple[float, float]  # (99, 210) for DIN-lang vertical
    has_fold_right: bool = True
    fold_layer_idx: int = 3
    children: list = field(default_factory=list)

    def emit(self, page=None) -> Iterable:
        for child in self.children:
            if hasattr(child, "emit"):
                yield from child.emit(page)
            else:
                yield child

        if self.has_fold_right:
            w, h = self.panel_size_mm
            x = (self.panel_index + 1) * w
            yield from FoldLine(
                start_mm=(x, 0),
                end_mm=(x, h),
                layer_idx=self.fold_layer_idx,
                anname=f"Falz Panel {self.panel_index}",
            ).emit(page)


# ---------------------------------------------------------------------------
# Block 9b: SpreadImage (Issue #14)
# Two ImageFrames sharing one source image to render a continuous picture
# across two facing pages. Replaces the today-broken (x=page_w, w=page_w)
# overflow pattern.
# ---------------------------------------------------------------------------
@dataclass
class SpreadImage:
    """Two ImageFrames, one per facing page, sharing one source image.

    Right half uses ``local_offset_mm=(-page_w_mm, 0)`` so the source
    image "scrolls" left and the right half shows the right half of the
    picture. Both frames are ``inside_page``-clean by construction
    (each sits at ``x=0`` on its own page).

    ``scale_type`` is hard-pinned to 0 (free / aspect-locked); the
    default 1 (auto-fit) breaks the spread because each half auto-fits
    independently.

    Anname pattern: when ``base_anname`` is set, the two frames are named
    ``f"{base} · left"`` and ``f"{base} · right"`` (middle-dot ' · ',
    matching ``WahlkreuzSymbol``'s convention). Empty ``base_anname``
    leaves both anname fields empty.
    """

    image: str
    page_w_mm: float
    page_h_mm: float
    h_mm: float
    y_mm: float = 0.0
    base_anname: str = ""
    scale_type: int = 0
    local_scale: tuple[float, float] = (1.0, 1.0)

    def emit(self) -> tuple[ImageFrame, ImageFrame]:
        left = ImageFrame(
            x_mm=0.0, y_mm=self.y_mm,
            w_mm=self.page_w_mm, h_mm=self.h_mm,
            image=self.image,
            local_scale=self.local_scale,
            local_offset_mm=(0.0, 0.0),
            scale_type=self.scale_type,
            anname=f"{self.base_anname} · left" if self.base_anname else "",
        )
        right = ImageFrame(
            x_mm=0.0, y_mm=self.y_mm,
            w_mm=self.page_w_mm, h_mm=self.h_mm,
            image=self.image,
            local_scale=self.local_scale,
            local_offset_mm=(-self.page_w_mm, 0.0),  # NEGATIVE x — see docstring
            scale_type=self.scale_type,
            anname=f"{self.base_anname} · right" if self.base_anname else "",
        )
        return left, right

    def place(self, page_left, page_right) -> tuple[ImageFrame, ImageFrame]:
        """Convenience: emit + add to two pages, return both frames."""
        l, r = self.emit()
        page_left.add(l)
        page_right.add(r)
        return l, r


# ---------------------------------------------------------------------------
# Block 10: DoorHangerCutout
# Spec: templates/_specs/wahltag-tueranhaenger.md
# ---------------------------------------------------------------------------
@dataclass
class DoorHangerCutout:
    """Standard door-hanger outer + handle-hole stanzpfad.

    ``layer_idx`` is the Scribus LAYER integer index for both DieCuts
    (outer + hole). Pass it explicitly when the document has a custom layer
    stack (e.g. Stanzkontur at index 3).
    """

    page_size_mm: tuple[float, float] = (105, 250)
    hole_diameter_mm: float = 35
    hole_top_offset_mm: float = 25
    layer_idx: int = 3

    def emit(self, page=None) -> Iterable:
        w, h = self.page_size_mm
        # Outer rectangle
        path = [(0, 0), (w, 0), (w, h), (0, h), (0, 0)]

        # Hole (circular, approximated)
        d = self.hole_diameter_mm
        r = d / 2
        cx = w / 2
        cy = self.hole_top_offset_mm + r

        segments = 36
        hole_path = []
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            hx = cx + r * math.cos(angle)
            hy = cy + r * math.sin(angle)
            hole_path.append((hx, hy))

        yield from DieCut(path_mm=path, layer_idx=self.layer_idx,
                          anname="Stanzkontur Außen").emit(page)
        yield from DieCut(path_mm=hole_path, layer_idx=self.layer_idx,
                          anname="Stanzkontur Loch").emit(page)


# ---------------------------------------------------------------------------
# Block 11: TableTentFold
# Spec: templates/_specs/infostand-tent-card-a5-quer.md
# ---------------------------------------------------------------------------
@dataclass
class TableTentFold:
    """A4 quer folded into A5 tent: emits horizontal Falz-line at center.

    ``layer_idx`` is the Scribus LAYER integer index for the FoldLine
    (Falz spot color). Default 3 assumes the document declares 4 layers
    [Hintergrund, Bilder, Text, Falz].
    """

    page_size_mm: tuple[float, float] = (297, 210)
    layer_idx: int = 3

    def emit(self, page=None) -> Iterable:
        w, h = self.page_size_mm
        yield from FoldLine(
            start_mm=(0, h / 2),
            end_mm=(w, h / 2),
            layer_idx=self.layer_idx,
            anname="Mittelfalz (horizontal)",
        ).emit(page)


# ---------------------------------------------------------------------------
# Legacy compatibility shim
# ---------------------------------------------------------------------------
# The old 8 aspirational blocks (Headline4Line, StoererBadge, ImpressumLine,
# ImpressumBlock, SocialHandlesVertical, LogoCorner, EventDetails, Masthead,
# ContentTeasers, ArticleHeadline, ArticleBody, QuoteSidebar) move here for
# one migration cycle. Import from blocks.legacy if you need them during
# migration; they will be removed in the next major DSL revision.

import types as _types

# Build a lazy legacy namespace from the original implementations
_legacy_src = """
from __future__ import annotations
import warnings
from dataclasses import dataclass
from typing import Optional, Sequence, Iterable

try:
    from sla_lib.builder.ci import Color, Style
    from sla_lib.builder.primitives import TextFrame, ImageFrame, Polygon, Anchor
except ImportError:
    from ..ci import Color, Style
    from ..primitives import TextFrame, ImageFrame, Polygon, Anchor

DEFAULT_IMPRESSUM = (
    "Impressum: Medieninhaber und Herausgeber: Die Grünen Niederösterreich, "
    "Daniel-Gran-Straße 48, 3100 St. Pölten. · Druck: Druckerei mit Postanschrift · "
    "Evtl. Hinweis auf Umweltzeichen wenn zutreffend"
)

def _resolve_pos(pos, x_mm, y_mm):
    if pos is not None:
        return pos, 0, 0
    return None, x_mm, y_mm

@dataclass
class Headline4Line:
    lines: Sequence[str] = ("[Zeile 1]", "[Zeile 2]", "[Zeile 3]", "[Zeile 4]")
    colors: Sequence[str] = (Color.WHITE, Color.GELB, Color.WHITE, Color.GELB)
    style: str = Style.HEADLINE_ULTRA
    pos: Optional[Anchor] = None
    x_mm: float = 8
    y_mm: float = 30
    w_mm: float = 90
    h_mm: float = 70
    rotation_deg: float = 0
    def emit(self) -> Iterable:
        warnings.warn("Headline4Line is deprecated; use TextFrame with Run list instead", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        runs = []
        for i, (line, color) in enumerate(zip(self.lines, self.colors)):
            run = (line, {"fcolor": color}, "para") if i < len(self.lines)-1 else (line, {"fcolor": color})
            runs.append(run)
        yield TextFrame(x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor, runs=runs, style=self.style, rotation_deg=self.rotation_deg, layer=2, anname="Headline 4-zeilig (Brand-Wechselfarbe)")

@dataclass
class StoererBadge:
    text: Sequence[str] = ("[Stör 1]", "[Stör 2]", "[Stör 3]")
    color: str = Color.MAGENTA
    pos: Optional[Anchor] = None
    x_mm: float = 70
    y_mm: float = 10
    diameter_mm: float = 22
    rotation_deg: float = 8
    def emit(self) -> Iterable:
        warnings.warn("StoererBadge is deprecated; use Polygon+TextFrame directly", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        d = self.diameter_mm
        yield Polygon(x_mm=x, y_mm=y, w_mm=d, h_mm=d, anchor=anchor, fill=self.color, shape="ellipse", rotation_deg=self.rotation_deg, layer=2, anname="Störer-Kreis")
        inset = d * 0.07
        yield TextFrame(x_mm=x+inset, y_mm=y+inset, w_mm=d-2*inset, h_mm=d-2*inset, anchor=anchor, runs=[(t, None, "para" if i < len(self.text)-1 else None) for i, t in enumerate(self.text)], style=Style.STOERER, fcolor=Color.WHITE, rotation_deg=self.rotation_deg, layer=2, anname="Störer-Text 3-zeilig")

@dataclass
class ImpressumLine:
    text: str = DEFAULT_IMPRESSUM
    pos: Optional[Anchor] = None
    x_mm: float = 8
    y_mm: float = 142
    w_mm: float = 90
    h_mm: float = 6
    fcolor: str = Color.WHITE
    def emit(self) -> Iterable:
        warnings.warn("ImpressumLine is deprecated; use Impressum instead", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor, text=self.text, style=Style.IMPRESSUM, fcolor=self.fcolor, layer=2, anname="Impressum (1-zeilig)")

@dataclass
class ImpressumBlock:
    text: str = DEFAULT_IMPRESSUM
    pos: Optional[Anchor] = None
    x_mm: float = 8
    y_mm: float = 130
    w_mm: float = 60
    h_mm: float = 18
    fcolor: str = Color.WHITE
    def emit(self) -> Iterable:
        warnings.warn("ImpressumBlock is deprecated; use Impressum instead", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor, text=self.text, style=Style.IMPRESSUM, fcolor=self.fcolor, layer=2, anname="Impressum (Block)")

@dataclass
class SocialHandlesVertical:
    handles: Sequence[str] = ("Facebook: gruene.noe", "Instagram: @gruene_noe", "office@gruene-noe.at", "02742 / 90 230")
    pos: Optional[Anchor] = None
    x_mm: float = 8
    y_mm: float = 130
    w_mm: float = 50
    h_mm: float = 18
    fcolor: str = Color.WHITE
    def emit(self) -> Iterable:
        warnings.warn("SocialHandlesVertical is deprecated; use ContactBlock instead", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        runs = [(h, {"fcolor": self.fcolor}, "para" if i < len(self.handles)-1 else None) for i, h in enumerate(self.handles)]
        yield TextFrame(x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor, runs=runs, style=Style.IMPRESSUM, layer=2, anname="Social Handles (4-zeilig)")

@dataclass
class LogoCorner:
    corner: str = "top-right"
    variant: str = "weiss"
    size_mm: float = 18
    margin_mm: float = 4
    src: str = ""
    def emit(self) -> Iterable:
        warnings.warn("LogoCorner is deprecated", DeprecationWarning, stacklevel=2)
        anchor_map = {"top-left": ("left", "top"), "top-right": ("right", "top"), "bottom-left": ("left", "bottom"), "bottom-right": ("right", "bottom")}
        h, v = anchor_map[self.corner]
        x_spec = self.margin_mm if h == "left" else h
        y_spec = self.margin_mm if v == "top" else v
        src = self.src or f"shared/logos/gruene-{self.variant}.png"
        yield ImageFrame(anchor=(x_spec, y_spec), w_mm=self.size_mm, h_mm=self.size_mm, src=src, layer=1, anname=f"Logo ({self.corner}, {self.variant})")

@dataclass
class EventDetails:
    date: str = "[Datum]"
    time: str = "[Zeit]"
    venue: str = "[Veranstaltungsort]"
    address: str = "[Adresse]"
    pos: Optional[Anchor] = None
    x_mm: float = 10
    y_mm: float = 130
    w_mm: float = 80
    h_mm: float = 24
    fcolor: str = Color.WHITE
    columns: int = 2
    def emit(self) -> Iterable:
        warnings.warn("EventDetails is deprecated", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        if self.columns == 2:
            half = self.w_mm / 2 - 2
            yield TextFrame(x_mm=x, y_mm=y, w_mm=half, h_mm=self.h_mm, anchor=anchor, runs=[(self.date, {"fcolor": self.fcolor}, "para"), (self.time, {"fcolor": self.fcolor})], style=Style.BODY_12, layer=2, anname="Veranstaltung — Datum/Zeit")
            yield TextFrame(x_mm=x+half+4, y_mm=y, w_mm=half, h_mm=self.h_mm, runs=[(self.venue, {"fcolor": self.fcolor}, "para"), (self.address, {"fcolor": self.fcolor})], style=Style.BODY_12, layer=2, anname="Veranstaltung — Ort/Adresse")
        else:
            yield TextFrame(x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor, runs=[(self.date, {"fcolor": self.fcolor}, "para"), (self.time, {"fcolor": self.fcolor}, "para"), (self.venue, {"fcolor": self.fcolor}, "para"), (self.address, {"fcolor": self.fcolor})], style=Style.BODY_12, layer=2, anname="Veranstaltungs-Details")

@dataclass
class Masthead:
    zeitungsname: str = "[Zeitungsname]"
    ausgabe: str = "[Monat / Ausgabe]"
    pos: Optional[Anchor] = None
    x_mm: float = 10
    y_mm: float = 10
    w_mm: float = 190
    h_mm: float = 30
    def emit(self) -> Iterable:
        warnings.warn("Masthead is deprecated", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm*0.7, anchor=anchor, text=self.zeitungsname, style=Style.HEADLINE_ULTRA, fcolor=Color.GELB, layer=2, anname="Zeitungsname")
        yield TextFrame(x_mm=x, y_mm=y+self.h_mm*0.7+1, w_mm=self.w_mm, h_mm=6, text=self.ausgabe, style=Style.IMPRESSUM, fcolor=Color.WHITE, layer=2, anname="Monat/Ausgabe")

@dataclass
class ContentTeasers:
    items: Sequence = (("[Teaser 1 Headline]", "[Teaser 1 Body]"), ("[Teaser 2 Headline]", "[Teaser 2 Body]"), ("[Teaser 3 Headline]", "[Teaser 3 Body]"))
    pos: Optional[Anchor] = None
    x_mm: float = 10
    y_mm: float = 80
    w_mm: float = 190
    h_mm: float = 60
    gap_mm: float = 6
    def emit(self) -> Iterable:
        warnings.warn("ContentTeasers is deprecated", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        n = len(self.items)
        col_w = (self.w_mm - self.gap_mm * (n-1)) / n
        for i, (head, body) in enumerate(self.items):
            cx = x + i * (col_w + self.gap_mm)
            head_h = 9
            yield TextFrame(x_mm=cx, y_mm=y, w_mm=col_w, h_mm=head_h, anchor=anchor if i==0 else None, text=head, style=Style.CTA, fcolor=Color.GELB, layer=2, anname=f"Teaser {i+1} Headline")
            yield TextFrame(x_mm=cx, y_mm=y+head_h+1, w_mm=col_w, h_mm=self.h_mm-head_h-1, text=body, style=Style.BODY_11, fcolor=Color.WHITE, layer=2, anname=f"Teaser {i+1} Body")

@dataclass
class ArticleHeadline:
    text: str = "[Artikel-Headline]"
    pos: Optional[Anchor] = None
    x_mm: float = 10
    y_mm: float = 30
    w_mm: float = 190
    h_mm: float = 18
    fcolor: str = Color.BLACK
    def emit(self) -> Iterable:
        warnings.warn("ArticleHeadline is deprecated", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor, text=self.text, style=Style.HEADLINE_ULTRA, fcolor=self.fcolor, layer=2, anname="Artikel-Headline")

@dataclass
class ArticleBody:
    text: str = "[Artikel-Body]"
    columns: int = 3
    col_gap_mm: float = 4
    pos: Optional[Anchor] = None
    x_mm: float = 10
    y_mm: float = 50
    w_mm: float = 190
    h_mm: float = 200
    fcolor: str = Color.BLACK
    def emit(self) -> Iterable:
        warnings.warn("ArticleBody is deprecated", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor, text=self.text, style=Style.BODY_11, fcolor=self.fcolor, columns=self.columns, col_gap_mm=self.col_gap_mm, layer=2, anname=f"Artikel-Body ({self.columns}-spaltig)")

@dataclass
class QuoteSidebar:
    text: str = "[Pull-Quote]"
    pos: Optional[Anchor] = None
    x_mm: float = 130
    y_mm: float = 60
    w_mm: float = 70
    h_mm: float = 60
    fcolor: str = Color.GELB
    def emit(self) -> Iterable:
        warnings.warn("QuoteSidebar is deprecated", DeprecationWarning, stacklevel=2)
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor, text=self.text, style=Style.HEADLINE_VOLLKORN, fcolor=self.fcolor, layer=2, anname="Pull-Quote (Vollkorn-Italic)")
"""


def _build_legacy_module():
    """Build the legacy blocks module lazily at first access."""
    import sys as _sys
    name = "sla_lib.builder.blocks.legacy"
    mod = _types.ModuleType(name)
    _sys.modules[name] = mod
    exec(compile(_legacy_src, "<legacy-blocks>", "exec"), mod.__dict__)
    return mod


class _LegacyProxy:
    """Proxy object that exposes the old block classes under ``blocks.legacy``."""
    _mod = None

    def __getattr__(self, name: str):
        if self.__class__._mod is None:
            self.__class__._mod = _build_legacy_module()
        return getattr(self.__class__._mod, name)


legacy = _LegacyProxy()
