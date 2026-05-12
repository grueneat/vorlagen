"""Integration tests for line_spacing_audit against v2 falzflyer
(Issue #37 P3 task 14)."""
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

from line_spacing_audit import run_line_spacing_audit  # noqa: E402

SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
V2 = ROOT / "templates" / SLUG


@pytest.mark.skipif(
    not (V2 / "baseline.pdf").exists(),
    reason="v2 falzflyer baseline.pdf missing",
)
@pytest.mark.skipif(
    not (V2 / "build.py").exists(),
    reason="v2 falzflyer build.py missing",
)
def test_v2_audit_runs_without_crash():
    """Smoke: run_line_spacing_audit against real v2 falzflyer artifacts.

    Acceptance per ISSUE.md: the audit must complete without crashing. The
    actual drift count depends on the current state of preview.pdf — if v2
    has converged since pitfalls capture, ok=true; otherwise drift entries
    surface.
    """
    preview = V2 / "preview.pdf"
    if not preview.exists():
        pytest.skip("v2 preview.pdf not generated")
    report = run_line_spacing_audit(
        preview_pdf=preview,
        baseline_pdf=V2 / "baseline.pdf",
        build_py=V2 / "build.py",
        template=SLUG,
    )
    assert report["template"] == SLUG
    assert "line_spacing_drift" in report
    assert "line_spacing_drift_count" in report
    assert isinstance(report["line_spacing_drift_count"], int)
    assert isinstance(report["ok"], bool)


def test_synthetic_14_3_vs_16_0_flagged(tmp_path, monkeypatch):
    """#37 P3 task 14 acceptance: synthetic 14.3pt-rendered preview vs
    16.0pt-rendered baseline produces 1 drift entry with delta ≈ -1.7."""
    import line_spacing_audit as lsa

    page = SimpleNamespace(
        items=[
            SimpleNamespace(
                anname="u_fliesstext",
                x_mm=10.0, y_mm=20.0, w_mm=80.0, h_mm=120.0,
                rotation_deg=0.0,
                anchor=None,
                text="body",
                runs=[SimpleNamespace(text="x", paragraph_style="idml/fliesstext")],
            ),
        ],
        width_pt=595.0,
        height_pt=842.0,
    )
    doc = SimpleNamespace(pages=[page])
    module = SimpleNamespace(
        build_template=lambda: doc,
        build_preview=lambda: doc,
        build_doc=lambda: doc,
    )

    iters = iter([
        [100.0, 116.0, 132.0],   # baseline → 16.0pt
        [100.0, 114.3, 128.6],   # preview  → 14.3pt
    ])
    monkeypatch.setattr(lsa, "_extract_line_tops_per_frame",
                        lambda *a, **k: next(iters))
    import sla_lib.builder.template_loader as tloader
    monkeypatch.setattr(tloader, "load_build_module", lambda slug: module)

    build_py = tmp_path / "fake" / "build.py"
    build_py.parent.mkdir()
    build_py.write_text("# stub", encoding="utf-8")
    report = run_line_spacing_audit(
        preview_pdf=tmp_path / "preview.pdf",
        baseline_pdf=tmp_path / "baseline.pdf",
        build_py=build_py,
        template="test",
        threshold_pt=0.5,
    )
    assert report["line_spacing_drift_count"] == 1
    drift = report["line_spacing_drift"][0]
    assert drift["anname"] == "u_fliesstext"
    assert drift["para_style"] == "idml/fliesstext"
    assert drift["delta_pt"] == -1.7
    assert drift["baseline_linesp_pt"] == 16.0
    assert drift["preview_linesp_pt"] == 14.3
