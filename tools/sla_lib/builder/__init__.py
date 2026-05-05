"""DSL for emitting valid Scribus 1.6 SLA XML.

The builder package is the *only* path that writes new SLA files. It hides
the format quirks documented in `.research/01-sla-format.md` and
`.research/04-scribus-multipage-masters.md`:

- ItemID generation (qHash-unstable across reloads → monotonic IDs at emit time)
- Style PARENT inheritance (implicit-by-absence → never re-emit parent values)
- Coordinate scratch-space vs page-relative (DSL accepts mm, internally pt)
- MASTERPAGE / PAGE / MASTEROBJECT / PAGEOBJECT element ordering
- PageSets requirement (loader hard-fails without all four)
- Layer stack defaults (Hintergrund / Bilder / Text / Hilfslinien)

Public surface:

    from sla_lib.builder import Document, Page, Color, Style
    from sla_lib.builder import TextFrame, ImageFrame, Polygon, Line

Usage:
    doc = Document(title="Test", template_id="smoke")
    page = doc.add_page(size="A6", orientation="portrait", bleed_mm=3)
    page.add(TextFrame(x_mm=20, y_mm=20, w_mm=60, h_mm=20, text="Hello"))
    doc.save("out.sla")
"""
from __future__ import annotations

from .ci import Color, Style, load_ci
from .document import Document, Page
from .primitives import TextFrame, ImageFrame, Polygon, Line, Anchor

__all__ = [
    "Document",
    "Page",
    "Color",
    "Style",
    "TextFrame",
    "ImageFrame",
    "Polygon",
    "Line",
    "Anchor",
    "load_ci",
]
