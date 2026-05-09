"""Public bbox API for BrandRule + audit_alignment (Issue #22).

Extracted from brand_constraints.py L371-418. Two helpers:

- ``rotated_bbox(x, y, w, h, deg)``: axis-aligned bbox after CCW rotation
  around the top-left corner. Pivot convention matches Scribus ROT
  (CCW positive, top-left anchor; deduced from the plakat-a1-hochformat
  ROT=270 page-fit, verified against the rotated Impressum frame).
- ``frame_bbox_mm(item, page)``: page-local mm bbox honouring anchor +
  rotation. Returns ``None`` for primitives without spatial extent
  (e.g. ``Run``, ``ParaStyle``).

Limitation: verbatim-pt overrides (``xpos_pt`` / ``width_pt`` etc.) are
NOT honored — falls back to ``*_mm``. Carry the same caveat from the
original docstring.

Backwards compatibility: ``brand_constraints.py`` re-exports these as
``_rotated_bbox`` and ``_frame_bbox_mm`` so existing rule classes and
tests continue to work without churn.
"""
from __future__ import annotations

import math
from typing import Optional

from .document import PT_TO_MM, mm_to_pt
from .primitives import resolve_anchor


def rotated_bbox(
    x: float, y: float, w: float, h: float, deg: float,
) -> tuple[float, float, float, float]:
    """Axis-aligned bbox of a w×h rectangle rotated CCW by ``deg`` around
    its top-left corner ``(x, y)``.

    Returns ``(min_x, min_y, max_x, max_y)`` in the same units as the inputs.
    For ``deg == 0`` returns the un-rotated corners exactly (no float fuzz).
    """
    if deg == 0:
        return x, y, x + w, y + h
    rad = math.radians(deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    pts = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
    rx = [px * cos_a - py * sin_a for px, py in pts]
    ry = [px * sin_a + py * cos_a for px, py in pts]
    return x + min(rx), y + min(ry), x + max(rx), y + max(ry)


def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]:
    """Page-local mm bbox of ``item`` on ``page``, or ``None`` if the item
    has no spatial extent (e.g. ``Run``, ``ParaStyle``).

    Mirrors ``_Frame._xy_pt`` for anchor-positioned frames so the bbox
    reflects the SLA-emit-time position, not the dead ``x_mm/y_mm``.

    Limitation: verbatim-pt overrides (``xpos_pt`` / ``width_pt`` etc.) are
    NOT honored — falls back to ``*_mm``. The two known offenders
    (zeitung P9 Spread, unnamed page-12 image) use ``x_mm`` / ``w_mm``
    directly so this is safe today; widen if a future template exercises
    the override path.
    """
    if not all(hasattr(item, a) for a in ("x_mm", "y_mm", "w_mm", "h_mm")):
        return None
    if getattr(item, "anchor", None) is not None:
        x_pt, y_pt = resolve_anchor(
            item.anchor, page.width_pt, page.height_pt,
            mm_to_pt(item.w_mm), mm_to_pt(item.h_mm),
        )
        x_mm, y_mm = x_pt * PT_TO_MM, y_pt * PT_TO_MM
    else:
        x_mm, y_mm = float(item.x_mm), float(item.y_mm)
    w_mm, h_mm = float(item.w_mm), float(item.h_mm)
    rot = float(getattr(item, "rotation_deg", 0) or 0)
    return rotated_bbox(x_mm, y_mm, w_mm, h_mm, rot)
