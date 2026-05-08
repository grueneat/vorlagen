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

    from sla_lib.builder import Document, Page, Color, Style, Brand
    from sla_lib.builder import TextFrame, ImageFrame, Polygon, Run
    from sla_lib.builder import ParaStyle, CharStyle, DocumentLayer, SoftShadow
    from sla_lib.builder import Anchor  # canonical: Anchor(h=, v=, margin_mm=)

Usage:
    doc = Document(brand=Brand.gruene_noe(), title="Test", template_id="smoke")
    page = doc.add_page(size="A6", orientation="portrait", bleed_mm=3)
    page.add(TextFrame(x_mm=20, y_mm=20, w_mm=60, h_mm=20, text="Hello"))
    doc.save("out.sla")

Deprecated but still available (emit DeprecationWarning on use):

- ``Line`` — use ``Polygon(custom_path=..., line_color=..., fill='None')`` for
  round-trip-stable lines. The SLA converter emits Polygon, not Line. Line is
  kept for spec-input authoring only and will raise on ``to_pageobject()``.
- ``Run`` tuple form ``(text, dict, sep)`` — use ``Run(text=..., fcolor=..., ...)``
- ``Anchor`` string/tuple form ``"bottom-20"`` — use ``Anchor(v="bottom", margin_mm=20)``
- ``TextFrame(text_align=...)`` — use ``TextFrame(vertical_text_align=...)``

New typed APIs introduced in issue #2 and #5:

- ``Brand`` — brand profile bundling palette, styles, layers, and Scribus defaults.
  Pass to ``Document(brand=Brand.gruene_noe())`` to inject all CI brand state.
- ``Run`` — typed per-run text formatting (font, fontsize, fcolor, fshade,
  features, kern, char_style, separator, var=`pgno`).
- ``Anchor(h=, v=, margin_mm=)`` — canonical named-args anchor form.
- ``ParaStyle`` / ``CharStyle`` — per-document styles; PARENT inheritance preserved.
- ``DocumentLayer`` — per-document layer stack override.
- ``SoftShadow`` — frame-level soft-shadow effect.
- ``TextFrame.link_to`` — chain text frames via NEXTITEM/BACKITEM.
- ``_Frame.custom_path`` / ``_Frame.fill_rule`` — FRTYPE=3 verbatim path data.
- ``_Frame.corner_radius_mm`` — rounded rectangles (FRTYPE=2 / RADRECT).
- ``Document.add_color`` — register document-local CMYK or RGB color.

Note: soft-hyphen passthrough (``\\xad``) is supported as an escape hatch for
words Scribus's German hyph dict gets wrong; it is not the recommended
authoring approach for routine line-break control.
"""
from __future__ import annotations

from .ci import Color, Style, load_ci
from .document import Document, Page
from .primitives import TextFrame, ImageFrame, Polygon, Line, Anchor, Run, pack_inline_image
from .styles import DocumentLayer, ParaStyle, CharStyle, SoftShadow
from .brand import Brand
from . import blocks
from . import library

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
    "pack_inline_image",
    "ParaStyle",
    "CharStyle",
    "DocumentLayer",
    "SoftShadow",
    "load_ci",
    "Brand",
    "blocks",
    "library",
]
