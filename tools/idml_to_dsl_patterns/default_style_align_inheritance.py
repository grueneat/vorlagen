"""Backport 11: Propagate ALIGN from DefaultStyle / AppliedParagraphStyle
to per-paragraph paragraph_attrs.

Problem (RESEARCH.md):
  Scribus's ALIGN-on-trail does NOT propagate to the paragraph it
  terminates; only DefaultStyle ALIGN does. Issue #35 surfaced this:
  inner Left paragraphs silently inherited a non-Left DefaultStyle on
  mixed-Justification frames because the converter only emitted ALIGN
  when its value was non-zero.

Pattern semantics:
  matches() — True iff the element is a ParagraphStyleRange or its
    AppliedParagraphStyle exposes a Justification that lives in
    JUSTIFICATION_MAP.
  apply() — Sets paragraph_attrs.ALIGN (string-form) on the kwargs dict
    EVEN when ALIGN==0. The PSR's inline Justification wins; if absent,
    falls back to AppliedParagraphStyle's justification via the
    context['paragraph_styles'] map.

The converter's inline call site (currently at
tools/idml_to_dsl.py:2306-2327) implements the same logic against the
same JUSTIFICATION_MAP. This pattern module exposes the rule as a
reusable unit for future emission points and for documentation /
classification (convergence_review references it by id).

Context dependency:
  context["paragraph_styles"]: dict mapping AppliedParagraphStyle Self
    id -> {"justification": <IDML Justification value>}. Required for
    the fallback path when PSR has no inline Justification.
"""
from __future__ import annotations

from .base import Pattern
from .justification_to_align import JUSTIFICATION_MAP


def resolve_paragraph_align(
    psr_element,
    paragraph_styles: dict | None,
) -> int | None:
    """Return the effective ALIGN integer for a ParagraphStyleRange.

    Returns None when no justification is resolvable.
    """
    if psr_element is None:
        return None
    psr_just = psr_element.get("Justification") if hasattr(psr_element, "get") else None
    if psr_just and psr_just in JUSTIFICATION_MAP:
        return JUSTIFICATION_MAP[psr_just]
    if paragraph_styles is None:
        return None
    ps_self = psr_element.get("AppliedParagraphStyle") if hasattr(psr_element, "get") else None
    if not ps_self or ps_self not in paragraph_styles:
        return None
    fallback = paragraph_styles[ps_self].get("justification")
    if fallback in JUSTIFICATION_MAP:
        return JUSTIFICATION_MAP[fallback]
    return None


class DefaultStyleAlignInheritance:
    id = "default_style_align_inheritance"
    description = (
        "Propagate DefaultStyle / AppliedParagraphStyle ALIGN to per-paragraph "
        "paragraph_attrs even when value is 0 (Backport 11)"
    )
    applies_to = "TextFrame"
    depends_on = ("justification_to_align",)

    def matches(self, idml_element) -> bool:
        if not hasattr(idml_element, "get"):
            return False
        if idml_element.get("Justification") in JUSTIFICATION_MAP:
            return True
        if idml_element.get("AppliedParagraphStyle"):
            return True
        return False

    def apply(
        self,
        kwargs: dict,
        idml_element,
        context: dict | None = None,
    ) -> None:
        paragraph_styles = (context or {}).get("paragraph_styles")
        align_int = resolve_paragraph_align(idml_element, paragraph_styles)
        if align_int is None:
            return
        para_attrs = kwargs.setdefault("paragraph_attrs", {})
        para_attrs["ALIGN"] = str(align_int)
