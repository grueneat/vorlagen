"""Compose-level blocks built on top of the frame primitives.

Each block produces one or more PAGEOBJECTs configured for the brand:
- correct CI paragraph style applied
- ANNAME set to a human-readable hint visible in Scribus's Object Properties
- example content visible in Scribus so users see the slot purpose
- positioned via anchor or absolute mm coords

Public usage:
    page.add(Headline4Line(lines=["a","b","c","d"], pos=("center", 40)))
    page.add(StoererBadge(text=["Komm","mit","21.5."], pos=(75, 12), rotation_deg=8))
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Sequence, Iterable

from .ci import Color, Style
from .primitives import TextFrame, ImageFrame, Polygon, Line, Anchor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_pos(pos, x_mm, y_mm) -> tuple[Optional[Anchor], float, float]:
    """Either pos (anchor) or (x_mm, y_mm) absolute. Returns (anchor, x, y)."""
    if pos is not None:
        return pos, 0, 0
    return None, x_mm, y_mm


# ---------------------------------------------------------------------------
# Block: Headline4Line — alternating-color brand headline (white / yellow)
# ---------------------------------------------------------------------------
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
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        runs: list = []
        for i, (line, color) in enumerate(zip(self.lines, self.colors)):
            run = (line, {"fcolor": color}, "para")
            if i == len(self.lines) - 1:
                run = (line, {"fcolor": color})  # no trailing para
            runs.append(run)
        yield TextFrame(
            x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm,
            anchor=anchor, runs=runs, style=self.style,
            rotation_deg=self.rotation_deg, layer=2,
            anname="Headline 4-zeilig (Brand-Wechselfarbe)",
        )


# ---------------------------------------------------------------------------
# Block: StoererBadge — pink ellipse + 3-line rotated text
# ---------------------------------------------------------------------------
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
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        d = self.diameter_mm
        # Ellipse first (background), text overlay second
        yield Polygon(
            x_mm=x, y_mm=y, w_mm=d, h_mm=d,
            anchor=anchor, fill=self.color, shape="ellipse",
            rotation_deg=self.rotation_deg, layer=2,
            anname="Störer-Kreis",
        )
        # Text inset by ~5% of diameter for visual padding
        inset = d * 0.07
        yield TextFrame(
            x_mm=x + inset, y_mm=y + inset, w_mm=d - 2 * inset, h_mm=d - 2 * inset,
            anchor=anchor, runs=[(t, None, "para" if i < len(self.text) - 1 else None)
                                  for i, t in enumerate(self.text)],
            style=Style.STOERER, fcolor=Color.WHITE,
            rotation_deg=self.rotation_deg, layer=2,
            anname="Störer-Text 3-zeilig",
        )


# ---------------------------------------------------------------------------
# Block: ImpressumLine / ImpressumBlock
# ---------------------------------------------------------------------------
DEFAULT_IMPRESSUM = (
    "Impressum: Medieninhaber und Herausgeber: Die Grünen Niederösterreich, "
    "Daniel-Gran-Straße 48, 3100 St. Pölten. · Druck: Druckerei mit Postanschrift · "
    "Evtl. Hinweis auf Umweltzeichen wenn zutreffend"
)


@dataclass
class ImpressumLine:
    text: str = DEFAULT_IMPRESSUM
    pos: Optional[Anchor] = None
    x_mm: float = 8
    y_mm: float = 142   # near bottom of A6
    w_mm: float = 90
    h_mm: float = 6
    fcolor: str = Color.WHITE

    def emit(self) -> Iterable:
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(
            x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor,
            text=self.text, style=Style.IMPRESSUM, fcolor=self.fcolor,
            layer=2, anname="Impressum (1-zeilig)",
        )


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
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(
            x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor,
            text=self.text, style=Style.IMPRESSUM, fcolor=self.fcolor,
            layer=2, anname="Impressum (Block)",
        )


# ---------------------------------------------------------------------------
# Block: SocialHandlesVertical — 4 lines, each a handle
# ---------------------------------------------------------------------------
@dataclass
class SocialHandlesVertical:
    handles: Sequence[str] = (
        "Facebook: gruene.noe",
        "Instagram: @gruene_noe",
        "office@gruene-noe.at",
        "02742 / 90 230",
    )
    pos: Optional[Anchor] = None
    x_mm: float = 8
    y_mm: float = 130
    w_mm: float = 50
    h_mm: float = 18
    fcolor: str = Color.WHITE

    def emit(self) -> Iterable:
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        runs = [(h, {"fcolor": self.fcolor}, "para" if i < len(self.handles) - 1 else None)
                for i, h in enumerate(self.handles)]
        yield TextFrame(
            x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor,
            runs=runs, style=Style.IMPRESSUM, layer=2,
            anname="Social Handles (4-zeilig)",
        )


# ---------------------------------------------------------------------------
# Block: LogoCorner — placeholder square; users replace with shared/logos/...
# ---------------------------------------------------------------------------
@dataclass
class LogoCorner:
    corner: str = "top-right"           # top-left/top-right/bottom-left/bottom-right
    variant: str = "weiss"              # weiss/farbig — picks file in shared/logos/
    size_mm: float = 18
    margin_mm: float = 4
    src: str = ""                        # override; default = shared/logos/gruene-{variant}.png

    def emit(self) -> Iterable:
        # Anchor at corner with margin
        anchor_map = {
            "top-left": ("left", "top"),
            "top-right": ("right", "top"),
            "bottom-left": ("left", "bottom"),
            "bottom-right": ("right", "bottom"),
        }
        h, v = anchor_map[self.corner]
        x_spec = h if h == "left" else f"right-{self.margin_mm}"
        if h == "left":
            x_spec = self.margin_mm
        y_spec = v if v == "top" else f"bottom-{self.margin_mm}"
        if v == "top":
            y_spec = self.margin_mm

        src = self.src or f"shared/logos/gruene-{self.variant}.png"
        yield ImageFrame(
            anchor=(x_spec, y_spec), w_mm=self.size_mm, h_mm=self.size_mm,
            src=src, layer=1,
            anname=f"Logo ({self.corner}, {self.variant})",
        )


# ---------------------------------------------------------------------------
# Block: EventDetails — date / time / venue / address
# ---------------------------------------------------------------------------
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
    columns: int = 2     # 2-column layout: date+time on left, venue+address on right

    def emit(self) -> Iterable:
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        if self.columns == 2:
            half = self.w_mm / 2 - 2
            yield TextFrame(
                x_mm=x, y_mm=y, w_mm=half, h_mm=self.h_mm, anchor=anchor,
                runs=[(self.date, {"fcolor": self.fcolor}, "para"),
                      (self.time, {"fcolor": self.fcolor})],
                style=Style.BODY_12, layer=2,
                anname="Veranstaltung — Datum/Zeit",
            )
            yield TextFrame(
                x_mm=x + half + 4, y_mm=y, w_mm=half, h_mm=self.h_mm,
                runs=[(self.venue, {"fcolor": self.fcolor}, "para"),
                      (self.address, {"fcolor": self.fcolor})],
                style=Style.BODY_12, layer=2,
                anname="Veranstaltung — Ort/Adresse",
            )
        else:
            yield TextFrame(
                x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor,
                runs=[(self.date, {"fcolor": self.fcolor}, "para"),
                      (self.time, {"fcolor": self.fcolor}, "para"),
                      (self.venue, {"fcolor": self.fcolor}, "para"),
                      (self.address, {"fcolor": self.fcolor})],
                style=Style.BODY_12, layer=2,
                anname="Veranstaltungs-Details",
            )


# ---------------------------------------------------------------------------
# Block: Masthead — newspaper title + issue label
# ---------------------------------------------------------------------------
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
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(
            x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm * 0.7, anchor=anchor,
            text=self.zeitungsname, style=Style.HEADLINE_ULTRA, fcolor=Color.GELB,
            layer=2, anname="Zeitungsname",
        )
        yield TextFrame(
            x_mm=x, y_mm=y + self.h_mm * 0.7 + 1, w_mm=self.w_mm, h_mm=6,
            text=self.ausgabe, style=Style.IMPRESSUM, fcolor=Color.WHITE,
            layer=2, anname="Monat/Ausgabe",
        )


# ---------------------------------------------------------------------------
# Block: ContentTeasers — N-column grid of teaser articles
# ---------------------------------------------------------------------------
@dataclass
class ContentTeasers:
    items: Sequence[tuple[str, str]] = (
        ("[Teaser 1 Headline]", "[Teaser 1 Body — kurzer Anriss zum Artikel]"),
        ("[Teaser 2 Headline]", "[Teaser 2 Body — kurzer Anriss zum Artikel]"),
        ("[Teaser 3 Headline]", "[Teaser 3 Body — kurzer Anriss zum Artikel]"),
    )
    pos: Optional[Anchor] = None
    x_mm: float = 10
    y_mm: float = 80
    w_mm: float = 190
    h_mm: float = 60
    gap_mm: float = 6

    def emit(self) -> Iterable:
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        n = len(self.items)
        col_w = (self.w_mm - self.gap_mm * (n - 1)) / n
        for i, (head, body) in enumerate(self.items):
            cx = x + i * (col_w + self.gap_mm)
            head_h = 9
            yield TextFrame(
                x_mm=cx, y_mm=y, w_mm=col_w, h_mm=head_h, anchor=anchor if i == 0 else None,
                text=head, style=Style.CTA, fcolor=Color.GELB,
                layer=2, anname=f"Teaser {i+1} Headline",
            )
            yield TextFrame(
                x_mm=cx, y_mm=y + head_h + 1, w_mm=col_w, h_mm=self.h_mm - head_h - 1,
                text=body, style=Style.BODY_11, fcolor=Color.WHITE,
                layer=2, anname=f"Teaser {i+1} Body",
            )


# ---------------------------------------------------------------------------
# Block: ArticleHeadline + ArticleBody
# ---------------------------------------------------------------------------
@dataclass
class ArticleHeadline:
    text: str = "[Artikel-Headline]"
    pos: Optional[Anchor] = None
    x_mm: float = 10
    y_mm: float = 30
    w_mm: float = 190
    h_mm: float = 18
    fcolor: str = Color.BLACK   # inside-newspaper articles default to black on white

    def emit(self) -> Iterable:
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(
            x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor,
            text=self.text, style=Style.HEADLINE_ULTRA, fcolor=self.fcolor,
            layer=2, anname="Artikel-Headline",
        )


@dataclass
class ArticleBody:
    text: str = (
        "[Artikel-Body — Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi "
        "ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit "
        "in voluptate velit esse cillum dolore eu fugiat nulla pariatur.]"
    )
    columns: int = 3
    col_gap_mm: float = 4
    pos: Optional[Anchor] = None
    x_mm: float = 10
    y_mm: float = 50
    w_mm: float = 190
    h_mm: float = 200
    fcolor: str = Color.BLACK   # newspaper body default is black on white

    def emit(self) -> Iterable:
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(
            x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor,
            text=self.text, style=Style.BODY_11, fcolor=self.fcolor,
            columns=self.columns, col_gap_mm=self.col_gap_mm,
            layer=2, anname=f"Artikel-Body ({self.columns}-spaltig)",
        )


# ---------------------------------------------------------------------------
# Block: QuoteSidebar — large pull-quote in Vollkorn italic
# ---------------------------------------------------------------------------
@dataclass
class QuoteSidebar:
    text: str = "[Pull-Quote — markante Aussage in Vollkorn-Italic]"
    pos: Optional[Anchor] = None
    x_mm: float = 130
    y_mm: float = 60
    w_mm: float = 70
    h_mm: float = 60
    fcolor: str = Color.GELB

    def emit(self) -> Iterable:
        anchor, x, y = _resolve_pos(self.pos, self.x_mm, self.y_mm)
        yield TextFrame(
            x_mm=x, y_mm=y, w_mm=self.w_mm, h_mm=self.h_mm, anchor=anchor,
            text=self.text, style=Style.HEADLINE_VOLLKORN, fcolor=self.fcolor,
            layer=2, anname="Pull-Quote (Vollkorn-Italic)",
        )


# ---------------------------------------------------------------------------
# Helper: page.add() that knows how to flatten block emissions
# ---------------------------------------------------------------------------
def expand_blocks(items: Iterable):
    """Flatten any items that have an emit() method into their primitives."""
    for item in items:
        if hasattr(item, "emit"):
            yield from item.emit()
        else:
            yield item
