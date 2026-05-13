"""TextFrame h_mm widening pattern.

Scribus clips text lines when the frame height is too small to render
them; InDesign silently overflows. The converter compensates by
widening h_mm to the minimum required by the text content (three
sub-cases: can't-show-one-line, explicit-line-count, multi-line-overset).

This Pattern wraps the existing _maybe_widen_frame_h helper at
tools/idml_to_dsl.py:469 so future call sites can iterate the registry
uniformly. The current inline call site continues to invoke the helper
directly to preserve byte-identity for the existing emitted templates.
"""
from __future__ import annotations

from .base import Pattern


class TextFrameHeightWidening:
    id = "text_frame_height_widening"
    description = (
        "Widen TextFrame h_mm when smaller than required text-content height "
        "(three sub-cases: one-line overset, explicit-line-count, multi-line)"
    )
    applies_to = "TextFrame"

    def matches(self, idml_element) -> bool:
        if not isinstance(idml_element, dict):
            return False
        # Pattern is applicable when the caller has measured text content;
        # the heuristic only fires when max_fontsize_pt is present.
        return idml_element.get("max_fontsize_pt") is not None

    def apply(
        self,
        kwargs: dict,
        idml_element,
        context: dict | None = None,
    ) -> None:
        if not isinstance(idml_element, dict):
            return
        # Lazy import to avoid circular references at module load time.
        from idml_to_dsl import _maybe_widen_frame_h  # type: ignore
        idml_h_mm = idml_element.get("h_mm")
        if idml_h_mm is None:
            return
        h_mm, comment = _maybe_widen_frame_h(
            idml_h_mm=float(idml_h_mm),
            max_fontsize_pt=idml_element.get("max_fontsize_pt"),
            leading_pt=idml_element.get("leading_pt"),
            total_text_chars=int(idml_element.get("total_text_chars") or 0),
            frame_w_mm=float(idml_element.get("frame_w_mm") or 0.0),
            explicit_line_count=int(idml_element.get("explicit_line_count") or 0),
        )
        if comment is not None:
            kwargs["h_mm"] = h_mm
            kwargs.setdefault("_height_widening_comment", comment)
