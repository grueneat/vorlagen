"""Unit tests for Pattern 9 — TextFrame h_mm auto-widening (issue 35, R7).

Scribus clips text when frame_h_pt < effective line height; InDesign
overflows silently. The converter widens h_mm to the required minimum so
the first line is always visible.

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

from idml_to_dsl import PT_TO_MM, _maybe_widen_frame_h, _required_text_frame_height_mm  # noqa: E402


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
    # point_size=10, auto-leading: required = 10*1.2*PT_TO_MM ≈ 4.23mm
    # frame_h=5.0mm > required → no widening.
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=5.0,
        max_fontsize_pt=10.0,
        leading_pt=None,
    )
    assert result_h == 5.0
    assert comment is None


def test_widens_when_leading_exceeds_frame_h() -> None:
    """Explicit leading=14.3pt, frame_h=3.10mm → widened to ~5.04mm."""
    # required_mm = 14.3 * PT_TO_MM ≈ 5.0389mm
    required = 14.3 * PT_TO_MM
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=3.10,
        max_fontsize_pt=11.0,
        leading_pt=14.3,
    )
    assert abs(result_h - required) < 1e-6
    assert comment is not None
    assert "3.1000mm" in comment or "3.10" in comment  # mentions original
    assert "leading=14.30pt" in comment


def test_widens_when_point_size_no_leading() -> None:
    """point_size=12, leading=None → required = 12*1.2*PT_TO_MM ≈ 5.08mm."""
    required = 12.0 * 1.2 * PT_TO_MM
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=2.0,
        max_fontsize_pt=12.0,
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
    # The max (14) should determine the required height.
    from sla_lib.builder import Run
    runs = [
        Run(text="small", fontsize=8.0),
        Run(text="large", fontsize=14.0),
    ]
    max_fs = max(r.fontsize for r in runs if r.fontsize is not None)
    required = max_fs * 1.2 * PT_TO_MM
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=2.0,
        max_fontsize_pt=max_fs,
        leading_pt=None,
    )
    assert abs(result_h - required) < 1e-6
    assert comment is not None


def test_epsilon_avoids_flapping() -> None:
    """Frame h_mm within epsilon (0.05mm) of required → no widening."""
    # required ≈ 14.3 * PT_TO_MM ≈ 5.0389mm; frame = 5.035mm (delta ≈ 0.004mm < epsilon)
    required = 14.3 * PT_TO_MM
    near_required = required - 0.04  # within epsilon
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=near_required,
        max_fontsize_pt=11.0,
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
    Required: 14.3 * PT_TO_MM ≈ 5.0447mm.
    """
    required = 14.3 * PT_TO_MM
    result_h, comment = _maybe_widen_frame_h(
        idml_h_mm=3.1044,
        max_fontsize_pt=11.0,
        leading_pt=14.3,
    )
    assert result_h > 3.1044
    assert abs(result_h - required) < 1e-6
    assert comment is not None
    assert "leading=14.30pt" in comment
