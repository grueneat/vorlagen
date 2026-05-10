"""Synthetic variant fixture (issue #29 T07).

Implements the minimum public API a real variant module exposes —
``render_p2(doc, page) -> None`` — so the experiment_render integration
test can exercise the full module-load + scaffold-call path without
authoring a hypothesis-specific design.
"""
from __future__ import annotations

# variant_scaffold is loaded by the orchestrator and lives in sys.modules.
# We import lazily inside render_p2 so the fixture stays import-safe even
# when the scaffold has not been pre-loaded.


def render_p2(doc, page) -> None:
    """Re-emit the production P2 verbatim via render_p2_default.

    Variants ordinarily author their own P2 from scratch; this fixture
    delegates so the resulting Document is known-valid for the
    inside_page check.
    """
    from variant_scaffold import render_p2_default

    render_p2_default(doc, page)
