"""Unit tests for the reference_sla second diff lane in render_pipeline.py.

Covers:
- meta.yml reference_sla field parsing
- _run_reference_diff_lane argument plumbing (via mocks — no real Scribus)
- Graceful degradation when reference_sla is absent or the file doesn't exist
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import yaml

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import render_pipeline  # noqa: E402 — needs sys.path set above


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_meta(tmp_path: Path, extra: dict | None = None) -> Path:
    """Write a minimal meta.yml to tmp_path and return its Path."""
    base = {
        "id": "test-template",
        "version": "0.1.0",
        "title": "Test Template",
        "pages": 2,
        "preview_dpi": 100,
        "previews_for_sla": "abc123",
    }
    if extra:
        base.update(extra)
    meta_path = tmp_path / "meta.yml"
    meta_path.write_text(yaml.safe_dump(base), encoding="utf-8")
    return meta_path


# ---------------------------------------------------------------------------
# 1. meta.yml reference_sla field parsing
# ---------------------------------------------------------------------------

def test_meta_yml_reference_sla_parsed(tmp_path: Path):
    """reference_sla field survives a yaml.safe_load round-trip."""
    rel = "../../originals/some/file.sla"
    _write_meta(tmp_path, {"reference_sla": rel})
    meta = yaml.safe_load((tmp_path / "meta.yml").read_text(encoding="utf-8"))
    assert meta.get("reference_sla") == rel


def test_meta_yml_without_reference_sla(tmp_path: Path):
    """Absence of reference_sla is valid — field should be missing or empty."""
    _write_meta(tmp_path)
    meta = yaml.safe_load((tmp_path / "meta.yml").read_text(encoding="utf-8"))
    assert not meta.get("reference_sla")


# ---------------------------------------------------------------------------
# 2. Graceful degradation — no reference_sla
# ---------------------------------------------------------------------------

def test_reference_diff_lane_skips_when_absent(tmp_path: Path, capsys):
    """_run_reference_diff_lane is silent and does nothing when field is absent."""
    meta = {"id": "test-template"}
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    render_pipeline._run_reference_diff_lane("test-template", tmp_path, meta, out_dir)
    assert not (out_dir / "reference_diff" / "reference_diff.json").exists()


def test_reference_diff_lane_skips_when_file_missing(tmp_path: Path, capsys):
    """_run_reference_diff_lane is silent when reference_sla points at a missing file."""
    meta = {"id": "test-template", "reference_sla": "does-not-exist.sla"}
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    render_pipeline._run_reference_diff_lane("test-template", tmp_path, meta, out_dir)
    assert not (out_dir / "reference_diff" / "reference_diff.json").exists()


# ---------------------------------------------------------------------------
# 3. Second lane invokes render + compare with correct paths (mocked)
# ---------------------------------------------------------------------------

def test_reference_diff_lane_calls_render_and_compare(tmp_path: Path):
    """When reference_sla resolves, render_sla_to_pdf and compare_pages are called."""
    # Create a fake SLA file.
    sla_file = tmp_path / "ref.sla"
    sla_file.write_text("<Scribus/>", encoding="utf-8")

    # Create a fake preview.pdf so the lane can rasterise it.
    preview_pdf = tmp_path / "tdir" / "preview.pdf"
    preview_pdf.parent.mkdir(parents=True)
    preview_pdf.write_bytes(b"%PDF-1.4")  # minimal fake PDF

    tdir = preview_pdf.parent
    meta = {"id": "test-template", "reference_sla": str(sla_file)}
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    # Fake rasterise pages
    fake_ref_page = tmp_path / "ref_page.png"
    fake_dsl_page = tmp_path / "dsl_page.png"
    fake_ref_page.write_bytes(b"\x89PNG")
    fake_dsl_page.write_bytes(b"\x89PNG")

    with (
        patch.object(render_pipeline, "render_sla_to_pdf") as mock_render,
        patch.object(render_pipeline, "rasterise") as mock_rasterise,
        patch.object(render_pipeline, "compare_pages", return_value=(100, 10000)) as mock_compare,
        patch.object(render_pipeline, "montage_composite") as mock_montage,
    ):
        # rasterise returns one page for each call (ref + dsl)
        mock_rasterise.side_effect = [[fake_ref_page], [fake_dsl_page]]

        render_pipeline._run_reference_diff_lane("test-template", tdir, meta, out_dir)

    # render_sla_to_pdf called with resolved SLA path and reference-scribus.pdf
    mock_render.assert_called_once()
    render_call_args = mock_render.call_args
    assert render_call_args[0][0] == sla_file.resolve()
    ref_pdf_arg = render_call_args[0][1]
    assert ref_pdf_arg.name == "reference-scribus.pdf"

    # rasterise called twice (ref PDF + preview PDF)
    assert mock_rasterise.call_count == 2

    # compare_pages called once for the single page
    mock_compare.assert_called_once()

    # reference_diff.json written
    ref_json = out_dir / "reference_diff" / "reference_diff.json"
    assert ref_json.exists()
    data = json.loads(ref_json.read_text(encoding="utf-8"))
    assert "pass" in data
    assert "pages" in data
    assert len(data["pages"]) == 1
    page = data["pages"][0]
    assert "mismatch_pct" in page
    assert "pass" in page


def test_reference_diff_lane_render_failure_is_graceful(tmp_path: Path, capsys):
    """If render_sla_to_pdf raises, no crash and no reference_diff.json."""
    sla_file = tmp_path / "ref.sla"
    sla_file.write_text("<Scribus/>", encoding="utf-8")
    tdir = tmp_path / "tdir"
    tdir.mkdir()
    meta = {"id": "test-template", "reference_sla": str(sla_file)}
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    with patch.object(render_pipeline, "render_sla_to_pdf", side_effect=RuntimeError("scribus crashed")):
        render_pipeline._run_reference_diff_lane("test-template", tdir, meta, out_dir)

    assert not (out_dir / "reference_diff" / "reference_diff.json").exists()


# ---------------------------------------------------------------------------
# 4. _summarise_diff_json helper
# ---------------------------------------------------------------------------

def test_summarise_diff_json_parses_correctly(tmp_path: Path):
    data = {
        "pass": True,
        "pages": [
            {"page": 0, "mismatch_pct": 1.23},
            {"page": 1, "mismatch_pct": 4.56},
        ],
    }
    p = tmp_path / "visual_diff.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    overall_pass, pcts = render_pipeline._summarise_diff_json(p)
    assert overall_pass is True
    assert pcts == pytest.approx([1.23, 4.56])


def test_summarise_diff_json_missing_file(tmp_path: Path):
    overall_pass, pcts = render_pipeline._summarise_diff_json(tmp_path / "nonexistent.json")
    assert overall_pass is False
    assert pcts == []
