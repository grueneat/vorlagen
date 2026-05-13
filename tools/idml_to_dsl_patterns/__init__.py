"""Pattern registry for tools/idml_to_dsl.py.

Order matters: later patterns can override kwargs set by earlier ones.

Tasks 10-14 (issue #38) populate this list with the six existing inline
backports extracted from idml_to_dsl.py plus the new
image_frame_pdf_source_for_vectors pattern.
"""
from __future__ import annotations

from typing import List

from .base import Pattern


PATTERNS: List[Pattern] = []


def pattern_by_id(pattern_id: str) -> Pattern | None:
    """Lookup a pattern by id. Returns None if not found."""
    for p in PATTERNS:
        if getattr(p, "id", None) == pattern_id:
            return p
    return None


__all__ = ["PATTERNS", "Pattern", "pattern_by_id"]
