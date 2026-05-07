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
    from sla_lib.builder import TextFrame, ImageFrame, Polygon, Line, Run
    from sla_lib.builder import ParaStyle, CharStyle, DocumentLayer, SoftShadow

Usage:
    doc = Document(title="Test", template_id="smoke")
    page = doc.add_page(size="A6", orientation="portrait", bleed_mm=3)
    page.add(TextFrame(x_mm=20, y_mm=20, w_mm=60, h_mm=20, text="Hello"))
    doc.save("out.sla")

New typed APIs introduced for the round-trip pipeline (issue #2):

- ``Run`` — typed per-run text formatting (font, fontsize, fcolor, fshade,
  features, kern, char_style, separator, var=`pgno`); supersedes the old
  ``(text, dict, sep)`` tuple form (still accepted for migration).
- ``ParaStyle`` / ``CharStyle`` — per-document styles registered via
  ``Document.add_para_style()`` / ``add_char_style()``; PARENT inheritance is
  preserved by emitting only non-``None`` attributes.
- ``DocumentLayer`` — per-document layer stack via ``Document(layers=[...])``;
  overrides the CI brand layer stack.
- ``SoftShadow`` — frame-level soft-shadow effect (``_Frame.soft_shadow=...``).
- ``TextFrame.link_to`` — chain text frames via NEXTITEM/BACKITEM; the
  emitter pre-allocates ItemIDs in chain order so links resolve correctly.
- ``_Frame.custom_path`` / ``_Frame.fill_rule`` — emit FRTYPE=3 with arbitrary
  path data (Scribus's path/copath verbatim).
- ``_Frame.corner_radius_mm`` — rounded-corner rectangles (FRTYPE=2 / RADRECT).
- ``Document.add_color`` — register document-local CMYK or RGB color.

Note: soft-hyphen passthrough (``\\xad``) is supported as an escape hatch for
words Scribus's German hyph dict gets wrong; it is not the recommended
authoring approach for routine line-break control.
"""
from __future__ import annotations

from .ci import Color, Style, load_ci
from .document import Document, Page
from .primitives import TextFrame, ImageFrame, Polygon, Line, Anchor, Run
from .styles import DocumentLayer, ParaStyle, CharStyle, SoftShadow
from .brand import Brand
from . import blocks

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
    "Run",
    "ParaStyle",
    "CharStyle",
    "DocumentLayer",
    "SoftShadow",
    "load_ci",
    "Brand",
    "blocks",
]
