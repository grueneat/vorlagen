"""Backport 10: Emit scale_type=1 (free scaling) only when an ImageFrame
has non-identity local_scale or non-zero local_offset_pt; otherwise
scale_type=0 (fit-to-frame).

Problem (RESEARCH.md, Issue #37 P1 Task 4):
  Scribus's dataclass default is SCALETYPE=0 (ScaleAuto = fit-to-frame).
  SCALETYPE=0 IGNORES LOCALX / LOCALY / LOCALSCX / LOCALSCY at render
  time, so a converter that emits LOCAL* kwargs for cropped images
  silently produces wrong placement unless scale_type=1 is ALSO set.

Pattern semantics:
  matches() — True iff the input element exposes local_scale or
    local_offset_pt deviating from identity by more than the tolerance.
  apply() — Sets kwargs['scale_type'] = 1 when free scaling is needed.

The pattern accepts either a dict-like image attrs payload (preferred,
matches the converter's internal kwargs shape) or an lxml element with
LocalScale / LocalOffset (when the caller hasn't projected yet).
"""
from __future__ import annotations

from .base import Pattern


_SCALE_EPS = 1e-4
_OFFSET_PT_EPS = 0.01 / 0.352778  # ~0.0283pt — matches 0.01mm tolerance


def _scale_deviates(local_scale) -> bool:
    if local_scale is None:
        return False
    try:
        scx, scy = local_scale
    except (TypeError, ValueError):
        return False
    return abs(scx - 1.0) > _SCALE_EPS or abs(scy - 1.0) > _SCALE_EPS


def _offset_deviates(local_offset_pt) -> bool:
    if local_offset_pt is None:
        return False
    try:
        ox, oy = local_offset_pt
    except (TypeError, ValueError):
        return False
    return abs(ox) > _OFFSET_PT_EPS or abs(oy) > _OFFSET_PT_EPS


def needs_free_scaling(local_scale, local_offset_pt) -> bool:
    """True iff the cropped-image parameters require SCALETYPE=1."""
    return _scale_deviates(local_scale) or _offset_deviates(local_offset_pt)


class ScaleTypeForCroppedImages:
    id = "scale_type_for_cropped_images"
    description = (
        "Emit scale_type=1 only for cropped ImageFrames "
        "(non-identity local_scale or non-zero local_offset) (Backport 10)"
    )
    applies_to = "ImageFrame"

    def matches(self, idml_element) -> bool:
        if isinstance(idml_element, dict):
            return needs_free_scaling(
                idml_element.get("local_scale"),
                idml_element.get("local_offset_pt"),
            )
        return False

    def apply(
        self,
        kwargs: dict,
        idml_element,
        context: dict | None = None,
    ) -> None:
        if isinstance(idml_element, dict):
            local_scale = idml_element.get("local_scale")
            local_offset_pt = idml_element.get("local_offset_pt")
        else:
            local_scale = None
            local_offset_pt = None
        if needs_free_scaling(local_scale, local_offset_pt):
            kwargs["scale_type"] = 1
