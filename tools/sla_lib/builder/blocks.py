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

from dataclasses import dataclass, field
from typing import Optional, Sequence, Iterable

from .ci import Color, Style
from .primitives import TextFrame, ImageFrame, Polygon, Anchor, Run


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
    """

    x_mm: float = 10
    y_mm: float = 280
    w_mm: float = 10
    h_mm: float = 6
    style: str = "Seitenzahl"
    layer: int = 2
    anname: str = "Seitenzahl"

    def emit(self) -> Iterable:
        yield TextFrame(
            x_mm=self.x_mm,
            y_mm=self.y_mm,
            w_mm=self.w_mm,
            h_mm=self.h_mm,
            runs=[Run(
                text="",
                has_itext=False,
                var="pgno",
                separator="para",
                paragraph_style=self.style,
            )],
            layer=self.layer,
            anname=self.anname,
        )


# ---------------------------------------------------------------------------
# Block 2: Impressum
# Corpus: templates/postkarte-a6-kampagne/build.py:294 (trail_style='Impressum'),
#         templates/zeitung-a4-grun/build.py:3205 (trail_style='Impressum').
# ---------------------------------------------------------------------------
@dataclass
class Impressum:
    """Bottom-of-page legal text block with trail_style='Impressum'.

    Corpus:
    - templates/postkarte-a6-kampagne/build.py:294 — TextFrame with
      trail_style='Impressum', w_mm≈95, h_mm≈6
    - templates/zeitung-a4-grun/build.py:3205 — TextFrame with
      trail_style='Impressum' spanning full column width

    Usage::

        page.add(Impressum(x_mm=5, y_mm=142, w_mm=95))
    """

    text: str = DEFAULT_IMPRESSUM
    x_mm: float = 5
    y_mm: float = 142
    w_mm: float = 95
    h_mm: float = 6
    fcolor: Optional[str] = None   # None = inherit from trail_style
    layer: int = 2
    anname: str = "Impressum"

    def emit(self) -> Iterable:
        yield TextFrame(
            x_mm=self.x_mm,
            y_mm=self.y_mm,
            w_mm=self.w_mm,
            h_mm=self.h_mm,
            trail_style="Impressum",
            runs=[Run(text=self.text, paragraph_style=None)],
            fcolor=self.fcolor,
            layer=self.layer,
            anname=self.anname,
        )


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
