"""Falzflyer DIN-lang variant scaffold (issue #29).

This module is the experimental-only entry point for rendering structurally
different P2 ("Mein Plan") variants. Production rendering lives in
`build.py` and is byte-stable — `variant_scaffold` does NOT modify it.

Variants override only Panel 2 of the front page. Everything else (P1
Cover, P3 Wahltag, fold lines, back page wiring) reuses the production
output of `build.build_template()` verbatim by:

  1. Building the full 2-page Document via `build.build_template()`.
  2. Stripping items whose ``anname`` begins with ``"P2 "`` from page 0.
  3. Invoking the variant's ``render_p2(doc, page0)`` callable, which
     re-adds the P2 items in whatever new shape the hypothesis dictates.

Variant authors keep the ``"P2 "`` anname prefix on their PAGEOBJECTs so
audit-alignment / spec_check do not false-positive.

Brand-rule policy (per issue #29 PLAN.md resolved uncertainty #4):
  - ``BRAND_CONSTRAINTS`` are NOT auto-applied. Some hypotheses
    (asymmetric-balance, italic-emphasis, off-grid accents) deliberately
    violate brand rules — that is the whole point of the experiment.
  - ``inside_page`` enforcement is the responsibility of the variant
    render orchestrator (`tools/experiment_render.py`). Variants that
    overflow the page bbox are dropped from the bag with a clear log
    message; voting only happens on variants that fit on the page.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
# build.py lives next to this file; add HERE so `import build` resolves
# regardless of the caller's cwd or which entry point loaded us.
sys.path.insert(0, str(HERE))

# Reuse production helpers verbatim. We deliberately import from build.py
# so the P1/P3/back-page geometry stays in lockstep with production —
# no duplication, no drift.
import build as _falzflyer_build  # noqa: E402

from sla_lib.builder import (  # noqa: E402
    Document,
    Page,
    Polygon,
    Run,
    TextFrame,
)


P2_ANNAME_PREFIX = "P2 "


def render_p2_default(doc: Document, page: Page) -> None:
    """Re-emit the production P2 PAGEOBJECTs verbatim.

    Used as the default ``p2_render_fn`` for ``build_variant_front`` so
    the scaffold's no-override path round-trips a Document equivalent to
    the production front page.

    The five PAGEOBJECTs lifted unchanged from build.py:432-491:
      - ``P2 Top-Band``       Polygon Dunkelgrün  (99, -3, 99, 31)
      - ``P2 Top-Title``      TextFrame "Mein Plan"
      - ``P2 Teaser-Headline`` TextFrame "Was ich für Mödling will"
      - ``P2 Body-Backing``   Polygon Hellgrün
      - ``P2 Teaser-Body``    5 Schlagwort paragraphs
    """
    page.add(_falzflyer_build._top_band(1))

    page.add(TextFrame(
        x_mm=105, y_mm=8, w_mm=87, h_mm=14,
        layer=_falzflyer_build.LAYER_TEXT,
        style="falzflyer/top-title",
        runs=[Run(text="Mein Plan",
                  paragraph_style="falzflyer/top-title")],
        anname="P2 Top-Title",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=38, w_mm=87, h_mm=22,
        layer=_falzflyer_build.LAYER_TEXT,
        style="falzflyer/teaser-headline",
        runs=[Run(text="Was ich für Mödling will",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))

    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün",
        layer=_falzflyer_build.LAYER_HINTERGRUND,
        anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=72, w_mm=87, h_mm=130,
        layer=_falzflyer_build.LAYER_TEXT,
        style="falzflyer/schlagwort",
        runs=[
            Run(text="Klimaplan jetzt.", separator="para",
                paragraph_style="falzflyer/schlagwort"),
            Run(text="Leistbares Wohnen.", separator="para",
                paragraph_style="falzflyer/schlagwort"),
            Run(text="Bildung vor Ort.", separator="para",
                paragraph_style="falzflyer/schlagwort"),
            Run(text="Lokale Wirtschaft.", separator="para",
                paragraph_style="falzflyer/schlagwort"),
            Run(text="Bürgernähe statt Klüngel.",
                paragraph_style="falzflyer/schlagwort"),
        ],
        anname="P2 Teaser-Body",
    ))


def _strip_p2_items(page: Page) -> None:
    """Remove every PAGEOBJECT whose anname starts with ``"P2 "``."""
    page.items = [
        item for item in page.items
        if not (getattr(item, "anname", "") or "").startswith(P2_ANNAME_PREFIX)
    ]


def build_variant_front(
    p2_render_fn: Callable[[Document, Page], None] = render_p2_default,
) -> Document:
    """Build a 2-page falzflyer Document with P2 replaced by the variant.

    Production P1/P3/back wiring is preserved unmodified — the variant
    only re-emits Panel 2 on the front page.

    Args:
        p2_render_fn: callable taking ``(doc, page0)`` that re-adds P2
            PAGEOBJECTs (Polygons, TextFrames, etc.) using the DSL.
            Defaults to ``render_p2_default`` which re-emits the
            production P2 verbatim.

    Returns:
        A fully-built ``Document``. The caller saves the SLA via
        ``doc.save(<path>)``.
    """
    doc = _falzflyer_build.build_template()
    page0 = doc.pages[0]
    _strip_p2_items(page0)
    p2_render_fn(doc, page0)
    return doc
