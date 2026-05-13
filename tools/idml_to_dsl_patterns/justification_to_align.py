"""Backport 9: IDML Justification attribute -> Scribus ALIGN integer.

Sources:
  - IDML ParagraphStyle / ParagraphStyleRange Justification attribute.
    Values: LeftAlign, CenterAlign, RightAlign, FullyJustified,
    LeftJustified, RightJustified, CenterJustified.
  - Scribus SLA: ALIGN attribute on PARAGRAPHSTYLE / paragraph_attrs
    (0 left, 1 center, 2 right, 3 block).

Pattern semantics:
  matches() — True iff idml_element has a Justification attribute that
    lives in JUSTIFICATION_MAP. Accepts either a dict-like attrs mapping
    or an lxml element (both implement .get).
  apply() — Sets kwargs['ALIGN'] (string-form) and kwargs['align']
    (int-form) so callers that prefer either spelling can use the
    pattern uniformly.
"""
from __future__ import annotations

from .base import Pattern


JUSTIFICATION_MAP: dict[str, int] = {
    "LeftAlign": 0,
    "CenterAlign": 1,
    "RightAlign": 2,
    "FullyJustified": 3,
    "LeftJustified": 3,
    "RightJustified": 3,
    "CenterJustified": 3,
}


class JustificationToAlign:
    id = "justification_to_align"
    description = "Map IDML Justification to Scribus ALIGN integer (Backport 9)"
    applies_to = "ParaStyle"

    def matches(self, idml_element) -> bool:
        if hasattr(idml_element, "get"):
            return idml_element.get("Justification") in JUSTIFICATION_MAP
        return False

    def apply(
        self,
        kwargs: dict,
        idml_element,
        context: dict | None = None,
    ) -> None:
        j = idml_element.get("Justification")
        if j in JUSTIFICATION_MAP:
            value = JUSTIFICATION_MAP[j]
            kwargs["ALIGN"] = str(value)
            kwargs["align"] = value
