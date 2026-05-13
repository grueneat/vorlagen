"""Unit tests for Pattern 9 — TextFrame h_mm auto-widening (issue 35, R7).

Scribus clips text when frame_h_pt < effective line height; InDesign
overflows silently. The converter widens h_mm to the required minimum so
the first line is always visible.

The single-line widening budget is descent-aware: the converter uses
``ascent_ratio*fs + descent_ratio*fs + safety_pt`` (where ratios cover the
deepest-metric font in the brand palette, Vollkorn Black Italic) as the
floor when the authored Leading underestimates the actual rendered line
height. This avoids clipping descenders that protrude below the cap height.

Rules tested:
- No widening when frame h_mm already meets the required minimum.
- Widening when explicit leading exceeds frame height.
- Widening using auto-leading (point_size * 1.2) when no explicit leading.
- No widening when runs list is empty (no text content).
- Max leading wins when multiple leading values are possible (via fontsize).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from idml_to_dsl import (  # noqa: E402
    PT_TO_MM,
    _FONT_ASCENT_RATIO,
    _FONT_DESCENT_RATIO,
    _FRAME_HEIGHT_SAFETY_PT,
    _maybe_widen_frame_h,
    _required_text_frame_height_mm,
)


def _one_line_budget_mm(fs_pt: float) -> float:
    """Descent-aware single-line budget the converter applies as a floor.

    Mirrors ``_maybe_widen_frame_h``'s sub-case A formula:
    ``ascent_ratio*fs + descent_ratio*fs + safety_pt`` → mm.
    """
    one_line_pt = (
        _FONT_ASCENT_RATIO * fs_pt
        + _FONT_DESCENT_RATIO * fs_pt
        + _FRAME_HEIGHT_SAFETY_PT
    )
    return one_line_pt * PT_TO_MM


# ---------------------------------------------------------------------------
# _required_text_frame_height_mm
# ---------------------------------------------------------------------------

def test_required_height_with_explicit_leading() -> None:
    """Explicit leading dominates over point_size × 1.2."""
    h = _required_text_frame_height_mm(point_size_pt=11.0, leading_pt=14.3)
    assert abs(h - 14.3 * PT_TO_MM) < 1e-6


def test_required_height_auto_leading() -> None:
    """Auto-leading (None) uses point_size × 1.2."""
    h = _required_text_frame_height_mm(point_size_pt=12.0, leading_pt=None)
    assert abs(h - 12.0 * 1.2 * PT_TO_MM) < 1e-6


# ---------------------------------------------------------------------------
# _maybe_widen_frame_h
# ---------------------------------------------------------------------------

def test_no_widening_when_frame_h_meets_required() -> None:
    """Frame already large enough — returns h_mm unchanged, no comment."""
    # point_size=10, auto-leading: descent-aware floor =
    # (1.15+0.55)*10 + 4.0 = 21.0pt ≈ 7.405mm.
    # frame_h = floor + 1mm → no widening.
    fs = 10.0
    safely_above = _one_line_budget_mm(fs) + 1.0
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=safely_above,
        max_fontsize_pt=fs,
        leading_pt=None,
    )
    assert result_h == safely_above
    assert comment is None


def test_widens_when_leading_exceeds_frame_h() -> None:
    """Explicit leading=14.3pt, frame_h=3.10mm → widened to descent-aware floor.

    Authored leading (14.3pt → 5.04mm) is smaller than the descent-aware
    one-line floor for an 11pt run (22.7pt → ~8.01mm), so the floor wins.
    """
    fs = 11.0
    required = _one_line_budget_mm(fs)
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=3.10,
        max_fontsize_pt=fs,
        leading_pt=14.3,
    )
    assert abs(result_h - required) < 1e-6
    assert comment is not None
    assert "3.1000mm" in comment or "3.10" in comment  # mentions original
    assert "leading=14.30pt" in comment


def test_widens_when_point_size_no_leading() -> None:
    """point_size=12, leading=None → widened to descent-aware floor.

    Auto-leading (12*1.2=14.4pt → 5.08mm) is below the descent-aware floor
    (1.7*12 + 4 = 24.4pt → ~8.61mm), so the floor wins.
    """
    fs = 12.0
    required = _one_line_budget_mm(fs)
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=2.0,
        max_fontsize_pt=fs,
        leading_pt=None,
    )
    assert abs(result_h - required) < 1e-6
    assert comment is not None
    assert "auto-leading" in comment


def test_no_widening_when_no_fontsize() -> None:
    """No max_fontsize_pt (no runs or no fontsize) → returns input unchanged."""
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=3.10,
        max_fontsize_pt=None,
        leading_pt=None,
    )
    assert result_h == 3.10
    assert comment is None


def test_largest_fontsize_wins_in_mixed_runs() -> None:
    """When multiple font sizes exist, the largest determines required height."""
    # Simulate two runs: fontsize=8 and fontsize=14 (no explicit leading).
    # The max (14) should determine the required height. Required is the
    # descent-aware floor for the largest fontsize.
    from sla_lib.builder import Run
    runs = [
        Run(text="small", fontsize=8.0),
        Run(text="large", fontsize=14.0),
    ]
    max_fs = max(r.fontsize for r in runs if r.fontsize is not None)
    required = _one_line_budget_mm(max_fs)
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=2.0,
        max_fontsize_pt=max_fs,
        leading_pt=None,
    )
    assert abs(result_h - required) < 1e-6
    assert comment is not None


def test_epsilon_avoids_flapping() -> None:
    """Frame h_mm within epsilon (0.05mm) of required → no widening."""
    # Required = descent-aware floor for 11pt run (~8.008mm).
    # Frame = floor - 0.04mm → delta < epsilon → no widening.
    fs = 11.0
    required = _one_line_budget_mm(fs)
    near_required = required - 0.04  # within 0.05mm epsilon
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=near_required,
        max_fontsize_pt=fs,
        leading_pt=14.3,
    )
    assert result_h == near_required
    assert comment is None


def test_exact_social_handle_case() -> None:
    """Concrete case from the v2 falzflyer: u40c/u412/u45b social handles.

    IDML h_mm = 3.1044mm. Style 'idml/absatzformat-1' resolves (via BasedOn
    chain) to point_size=11pt and explicit leading=14.3pt. The converter uses:
    - max_fontsize_pt=11 (from paragraph style, since runs have no explicit fontsize)
    - leading_pt=14.3 (from resolved paragraph style)
    Required: descent-aware floor for 11pt = 22.7pt ≈ 8.008mm (larger than
    14.3pt leading, so the floor wins to protect Vollkorn descenders).
    """
    fs = 11.0
    required = _one_line_budget_mm(fs)
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=3.1044,
        max_fontsize_pt=fs,
        leading_pt=14.3,
    )
    assert result_h > 3.1044
    assert abs(result_h - required) < 1e-6
    assert comment is not None
    assert "leading=14.30pt" in comment
