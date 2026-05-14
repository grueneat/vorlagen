"""Unit tests for tools/line_spacing_audit.py (Issue #37 P3 task 13)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from line_spacing_audit import (  # noqa: E402
    _cluster_threshold_for_fontsize,
    _frame_fontsize_pt,
    _has_text_content,
    _median_baseline_gap,
    _yaml_dump,
    run_line_spacing_audit,
)


def test_median_baseline_gap_3_evenly_spaced_lines():
    """[100, 116, 132] → median(16, 16) = 16."""
    assert _median_baseline_gap([100.0, 116.0, 132.0]) == 16.0


def test_median_baseline_gap_single_line_returns_none():
    """A single line top has no gap to measure."""
    assert _median_baseline_gap([100.0]) is None


def test_median_baseline_gap_uses_median_not_mean():
    """[100, 116, 132, 145.5] gaps are [16, 16, 13.5] → median=16."""
    assert _median_baseline_gap([100.0, 116.0, 132.0, 145.5]) == 16.0


def test_median_baseline_gap_empty_returns_none():
    assert _median_baseline_gap([]) is None


def test_has_text_content_with_runs():
    fr = SimpleNamespace(runs=[SimpleNamespace(text="x")], text=None)
    assert _has_text_content(fr) is True


def test_has_text_content_with_text_field():
    fr = SimpleNamespace(runs=None, text="hello")
    assert _has_text_content(fr) is True


def test_has_text_content_empty():
    fr = SimpleNamespace(runs=None, text=None)
    assert _has_text_content(fr) is False


# ---------------------------------------------------------------------------
# Full run_line_spacing_audit — mock pdfplumber + build module
# ---------------------------------------------------------------------------

def _make_synthetic_module(*, frames: list, w_pt: float = 595, h_pt: float = 842):
    """Build a minimal module-like object that mimics build_template/preview."""
    page = SimpleNamespace(
        items=frames,
        width_pt=w_pt,
        height_pt=h_pt,
    )
    doc = SimpleNamespace(pages=[page])
    module = SimpleNamespace(
        build_template=lambda: doc,
        build_preview=lambda: doc,
        build_doc=lambda: doc,
    )
    return module


def _frame(anname="u1", x_mm=10.0, y_mm=20.0, w_mm=80.0, h_mm=60.0):
    """Synthesise a TextFrame-like dataclass for the audit."""
    return SimpleNamespace(
        anname=anname,
        x_mm=x_mm, y_mm=y_mm, w_mm=w_mm, h_mm=h_mm,
        rotation_deg=0.0,
        anchor=None,
        text="body text",
        runs=[SimpleNamespace(text="hello", paragraph_style="idml/normal")],
    )


def test_drift_reported_when_delta_exceeds_threshold(tmp_path, monkeypatch):
    """Baseline 3 lines spaced 16pt, preview spaced 14.3pt → delta -1.7pt → flagged."""
    import line_spacing_audit as lsa
    module = _make_synthetic_module(frames=[_frame()])
    # Two calls per frame: baseline first, then preview.
    side_effects = [
        [100.0, 116.0, 132.0],   # baseline → 16.0pt
        [100.0, 114.3, 128.6],   # preview  → 14.3pt
    ]
    iters = iter(side_effects)
    monkeypatch.setattr(lsa, "_extract_line_tops_per_frame",
                        lambda *a, **k: next(iters))
    import sla_lib.builder.template_loader as tloader
    monkeypatch.setattr(tloader, "load_build_module", lambda slug: module)

    build_py = tmp_path / "fake-slug" / "build.py"
    build_py.parent.mkdir()
    build_py.write_text("# stub", encoding="utf-8")
    report = run_line_spacing_audit(
        preview_pdf=tmp_path / "preview.pdf",
        baseline_pdf=tmp_path / "baseline.pdf",
        build_py=build_py,
        template="t",
        threshold_pt=0.5,
    )
    assert report["line_spacing_drift_count"] == 1
    drift = report["line_spacing_drift"][0]
    assert drift["anname"] == "u1"
    assert drift["baseline_linesp_pt"] == 16.0
    assert drift["preview_linesp_pt"] == 14.3
    assert drift["delta_pt"] == -1.7
    assert "override ParaStyle linesp to 16.0" in drift["recommendation"]
    assert report["ok"] is False


def test_no_drift_when_delta_below_threshold(tmp_path, monkeypatch):
    """0.4pt delta < threshold=0.5 → no drift reported, ok=True."""
    import line_spacing_audit as lsa
    module = _make_synthetic_module(frames=[_frame()])
    side_effects = [
        [100.0, 116.0, 132.0],   # baseline → 16.0
        [100.0, 116.4, 132.8],   # preview  → 16.4 (delta = +0.4)
    ]
    iters = iter(side_effects)
    monkeypatch.setattr(lsa, "_extract_line_tops_per_frame",
                        lambda *a, **k: next(iters))
    import sla_lib.builder.template_loader as tloader
    monkeypatch.setattr(tloader, "load_build_module", lambda slug: module)
    build_py = tmp_path / "slug" / "build.py"
    build_py.parent.mkdir()
    build_py.write_text("# stub", encoding="utf-8")
    report = run_line_spacing_audit(
        preview_pdf=tmp_path / "preview.pdf",
        baseline_pdf=tmp_path / "baseline.pdf",
        build_py=build_py,
        template="t",
    )
    assert report["line_spacing_drift_count"] == 0
    assert report["ok"] is True


def test_single_line_frame_skipped(tmp_path, monkeypatch):
    """Frame with <3 line tops on either pdf → skipped silently."""
    import line_spacing_audit as lsa
    module = _make_synthetic_module(frames=[_frame()])
    iters = iter([
        [100.0, 116.0],  # baseline → only 2 lines
        [100.0, 114.3, 128.6],  # preview → 3 lines
    ])
    monkeypatch.setattr(lsa, "_extract_line_tops_per_frame",
                        lambda *a, **k: next(iters))
    import sla_lib.builder.template_loader as tloader
    monkeypatch.setattr(tloader, "load_build_module", lambda slug: module)
    build_py = tmp_path / "slug" / "build.py"
    build_py.parent.mkdir()
    build_py.write_text("# stub", encoding="utf-8")
    report = run_line_spacing_audit(
        preview_pdf=tmp_path / "preview.pdf",
        baseline_pdf=tmp_path / "baseline.pdf",
        build_py=build_py,
        template="t",
    )
    assert report["line_spacing_drift_count"] == 0
    assert report["ok"] is True


# ---------------------------------------------------------------------------
# F-014: fontsize-scaled clustering threshold
# ---------------------------------------------------------------------------


def test_cluster_threshold_clamps_to_floor_for_small_fonts():
    """6pt body text → fontsize * 0.4 = 2.4 → clamped to ceiling 2.0pt
    (used to fall straight on the legacy fixed 2pt — F-014 keeps the
    ceiling but raises smaller-font behaviour too)."""
    assert _cluster_threshold_for_fontsize(6.0) == 2.0
    # 1pt fontsize → 0.4 → clamped to floor 0.6
    assert _cluster_threshold_for_fontsize(1.0) == 0.6


def test_cluster_threshold_scales_with_fontsize():
    """4pt fontsize → 1.6pt threshold (within [0.6, 2.0] range)."""
    assert _cluster_threshold_for_fontsize(4.0) == 1.6
    # 3pt → 1.2pt
    assert _cluster_threshold_for_fontsize(3.0) == pytest.approx(1.2)


def test_cluster_threshold_handles_missing_fontsize():
    """When the audit can't extract the frame's fontsize, fall back to
    the legacy 2pt ceiling so behaviour stays the same as pre-F-014
    for frames without a numeric Run.fontsize."""
    assert _cluster_threshold_for_fontsize(None) == 2.0
    assert _cluster_threshold_for_fontsize(0) == 2.0
    assert _cluster_threshold_for_fontsize(-1) == 2.0


def test_cluster_threshold_clamps_to_ceiling_for_huge_fonts():
    """80pt headline → fontsize * 0.4 = 32 → clamped to ceiling 2.0pt
    so adjacent drifted lines (e.g. 2.5pt apart) don't accidentally
    fuse into one cluster."""
    assert _cluster_threshold_for_fontsize(80.0) == 2.0


def test_frame_fontsize_pt_from_first_run():
    """The first Run with a numeric fontsize wins."""
    fr = SimpleNamespace(
        runs=[
            SimpleNamespace(fontsize=None),
            SimpleNamespace(fontsize=12.5),
            SimpleNamespace(fontsize=14.0),
        ],
    )
    assert _frame_fontsize_pt(fr) == 12.5


def test_frame_fontsize_pt_returns_none_when_no_runs():
    fr = SimpleNamespace(runs=None)
    assert _frame_fontsize_pt(fr) is None
    fr = SimpleNamespace(runs=[])
    assert _frame_fontsize_pt(fr) is None


def test_frame_fontsize_pt_ignores_non_numeric():
    fr = SimpleNamespace(
        runs=[
            SimpleNamespace(fontsize="not-a-number"),
            SimpleNamespace(fontsize=8.0),
        ],
    )
    assert _frame_fontsize_pt(fr) == 8.0


def test_small_font_threshold_used_in_audit_path(tmp_path, monkeypatch):
    """End-to-end: 6pt body frame routes fontsize_pt=6.0 into the
    extractor; we capture the threshold the extractor would have used.

    This is the F-014 regression guard — without per-frame scaling
    the 6pt Impressum frame would silently report 0 drift.
    """
    import line_spacing_audit as lsa

    captured: dict = {}

    def fake_extract(pdf, bbox, page_idx, *, fontsize_pt=None):
        captured.setdefault("fontsize", fontsize_pt)
        # Return enough lines so the audit doesn't early-skip
        return [100.0, 116.0, 132.0]

    monkeypatch.setattr(lsa, "_extract_line_tops_per_frame", fake_extract)
    # 6pt body run on a real-ish frame (matches _frame() helper shape).
    frame_6pt = SimpleNamespace(
        anname="u347",
        x_mm=10.0, y_mm=20.0, w_mm=80.0, h_mm=60.0,
        rotation_deg=0.0,
        anchor=None,
        text="Impressum",
        runs=[
            SimpleNamespace(
                text="Impressum",
                paragraph_style="idml/normal",
                fontsize=6.0,
            )
        ],
    )
    module = _make_synthetic_module(frames=[frame_6pt])
    import sla_lib.builder.template_loader as tloader
    monkeypatch.setattr(tloader, "load_build_module", lambda slug: module)

    build_py = tmp_path / "slug" / "build.py"
    build_py.parent.mkdir()
    build_py.write_text("# stub", encoding="utf-8")
    run_line_spacing_audit(
        preview_pdf=tmp_path / "preview.pdf",
        baseline_pdf=tmp_path / "baseline.pdf",
        build_py=build_py,
        template="t",
    )
    assert captured.get("fontsize") == 6.0


def test_yaml_dump_deterministic():
    payload = {
        "template": "t",
        "threshold_pt": 0.5,
        "line_spacing_drift_count": 1,
        "line_spacing_drift": [
            {
                "anname": "u1",
                "page": 0,
                "para_style": "idml/normal",
                "baseline_linesp_pt": 16.0,
                "preview_linesp_pt": 14.3,
                "delta_pt": -1.7,
                "recommendation": "override ParaStyle linesp to 16.0",
            },
        ],
        "ok": False,
    }
    a = _yaml_dump(payload)
    b = _yaml_dump(payload)
    assert a == b
    # Top-level keys sorted alphabetically
    top_keys = [
        line.split(":", 1)[0]
        for line in a.splitlines()
        if line and line[0].isalpha() and ":" in line
    ]
    assert top_keys == sorted(top_keys)
