"""Pattern base class for IDML to DSL converter extensions (issue #38).

Patterns mutate the kwargs dict that tools/idml_to_dsl.py passes to its
element emitters. They live in this package so the converter can iterate
them at the right emission points without growing further inline logic.

Ordering matters. Later patterns can override kwargs set by earlier
patterns. Document depends_on (informational; the registry does not enforce
topological order, but the maintainer is expected to register patterns in
the order their dependencies imply).
"""
from __future__ import annotations

from typing import Protocol


class Pattern(Protocol):
    """Protocol every pattern must satisfy.

    Attributes:
        id: Unique identifier, e.g. ``"justification_to_align"``.
        description: One-line human-readable description.
        applies_to: Element type the pattern matches. One of
            ``"TextFrame"``, ``"ImageFrame"``, ``"PolyLine"``,
            ``"ParaStyle"``, ``"DefaultStyle"``, ``"Group"``,
            ``"AllElements"``.

    Methods:
        matches: True iff the pattern is applicable to the given element.
        apply: Mutate kwargs in-place to inject the pattern's contribution.
    """

    id: str
    description: str
    applies_to: str

    def matches(self, idml_element) -> bool: ...

    def apply(
        self,
        kwargs: dict,
        idml_element,
        context: dict | None = None,
    ) -> None: ...
