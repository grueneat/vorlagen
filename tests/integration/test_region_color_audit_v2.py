"""Integration tests for region_color_audit against the real v2 falzflyer."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from region_color_audit import run_region_color_audit  # noqa: E402

SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
TEMPLATE_DIR = ROOT / "templates" / SLUG
BASELINE = TEMPLATE_DIR / "baseline.pdf"
PREVIEW = TEMPLATE_DIR / "preview.pdf"
BUILD_PY = TEMPLATE_DIR / "build.py"


def _skip_if_missing() -> None:
    for p in (BASELINE, PREVIEW, BUILD_PY):
        if not p.exists():
            pytest.skip(f"Required fixture not found: {p}")


def test_produces_by_severity_summary():
    """Audit produces a valid by_severity summary dict."""
    _skip_if_missing()
    result = run_region_color_audit(BUILD_PY, BASELINE, PREVIEW, SLUG)
    assert "by_severity" in result
    bs = result["by_severity"]
    assert set(bs.keys()) == {"ok", "icc_likely", "fill_likely"}
    assert all(isinstance(v, int) for v in bs.values())
    assert sum(bs.values()) >= 1


def test_u1ae_appears_in_frames():
    """u1ae (page background Polygon) appears in the frames list."""
    _skip_if_missing()
    result = run_region_color_audit(BUILD_PY, BASELINE, PREVIEW, SLUG)
    annames = {f["anname"] for f in result["frames"]}
    assert "u1ae" in annames, (
        f"u1ae not found in frames; got: {sorted(annames)[:10]}"
    )


def test_runtime_under_5s():
    """Full audit of v2 falzflyer completes in under 5 seconds."""
    _skip_if_missing()
    t0 = time.monotonic()
    run_region_color_audit(BUILD_PY, BASELINE, PREVIEW, SLUG)
    elapsed = time.monotonic() - t0
    assert elapsed < 5.0, f"region_color_audit took {elapsed:.1f}s (limit: 5s)"


def test_frames_have_required_keys():
    """Each frame entry has all required schema keys."""
    _skip_if_missing()
    result = run_region_color_audit(BUILD_PY, BASELINE, PREVIEW, SLUG)
    required = {"anname", "page", "type", "bbox_mm", "baseline_rgb",
                "preview_rgb", "mean_delta", "rms_delta", "severity"}
    for frame in result["frames"]:
        missing = required - set(frame.keys())
        assert not missing, f"Frame {frame.get('anname')} missing keys: {missing}"
