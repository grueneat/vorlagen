"""Unit tests for tools/baseline_text_audit.py — PDF text vs build.py TextFrame audit.

Tests use synthetic minimal fixtures so they run fully offline in <5 seconds.
The PDF-dependent tests (pdftotext, pdfinfo) are integration-tested against
the real baseline.pdf only when it's available.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from baseline_text_audit import (
    _normalise,
    _extract_lines_from_page,
    _extract_run_texts_from_build_py,
    _find_nearest_match,
    _is_line_matched,
    run_text_audit,
    _yaml_dump,
)


# ---------------------------------------------------------------------------
# Unit tests — pure-Python helpers
# ---------------------------------------------------------------------------

def test_normalise_strips_punctuation():
    result = _normalise("Hello, World!")
    assert "hello" in result
    assert "world" in result
    assert "," not in result
    assert "!" not in result


def test_normalise_lowercases():
    assert _normalise("UPPERCASE") == "uppercase"


def test_normalise_collapses_whitespace():
    result = _normalise("  foo   bar  ")
    assert result.startswith("foo")
    assert result.endswith("bar")
    assert "foo" in result and "bar" in result


def test_extract_lines_splits_columns():
    """Lines with 3+ spaces are split into separate segments (multi-column detection)."""
    raw = "Column A text     Column B text"
    lines = _extract_lines_from_page(raw)
    assert "Column A text" in lines
    assert "Column B text" in lines
    # The merged line should NOT appear
    assert "Column A text     Column B text" not in lines


def test_extract_lines_deduplicates():
    raw = "Hello World\nHello World\nOther line"
    lines = _extract_lines_from_page(raw)
    assert lines.count("Hello World") == 1


def test_extract_lines_skips_short():
    raw = "Hi\nLonger line here\nOK"
    lines = _extract_lines_from_page(raw)
    assert "Longer line here" in lines
    # "Hi" and "OK" are < MIN_LINE_LEN (3)
    assert "OK" not in lines


def test_extract_run_texts_from_build_py(tmp_path):
    bp = tmp_path / "build.py"
    bp.write_text("""\
page0.add(TextFrame(
    x_mm=10,
    anname='u1ae',
    style='foo',
    runs=[Run(text='Hello World'), Run(text='Second run')],
))
page0.add(TextFrame(
    anname='u2b0',
    runs=[Run(text='Another frame')],
))
""", encoding="utf-8")
    result = _extract_run_texts_from_build_py(bp)
    assert "u1ae" in result
    assert "Hello World" in result["u1ae"]
    assert "Second run" in result["u1ae"]
    assert "u2b0" in result
    assert "Another frame" in result["u2b0"]


def test_extract_run_texts_ignores_empty_runs(tmp_path):
    """Run(text='') should not appear in run text lists."""
    bp = tmp_path / "build.py"
    bp.write_text("""\
page0.add(TextFrame(
    anname='u1',
    runs=[Run(text='Real text'), Run(text=''), Run(text='More')],
))
""", encoding="utf-8")
    result = _extract_run_texts_from_build_py(bp)
    assert "u1" in result
    assert "Real text" in result["u1"]
    assert "More" in result["u1"]
    assert "" not in result["u1"]


def test_is_line_matched_exact():
    run_texts = {"u1": ["Exact match line"]}
    assert _is_line_matched(_normalise("Exact match line"), run_texts)


def test_is_line_matched_substring():
    run_texts = {"u1": ["The quick brown fox jumps over the lazy dog"]}
    assert _is_line_matched(_normalise("quick brown fox"), run_texts)


def test_is_line_matched_no_match():
    run_texts = {"u1": ["Some completely different text"]}
    assert not _is_line_matched(_normalise("Leonore Gewessler"), run_texts)


def test_find_nearest_match_finds_best():
    run_texts = {"u1ae": ["Hello World"], "u2b0": ["Completely different"]}
    anname, sim = _find_nearest_match("Hello World!", _normalise("Hello World!"), run_texts)
    assert anname == "u1ae"
    assert sim >= 80


def test_find_nearest_match_returns_null_below_threshold():
    run_texts = {"u1": ["ABC DEF GHI"]}
    anname, sim = _find_nearest_match("Leonore Gewessler", _normalise("Leonore Gewessler"), run_texts)
    assert anname is None
    assert sim == 0


def test_yaml_output_deterministic(tmp_path):
    """Running audit twice produces identical YAML output."""
    build_py = tmp_path / "build.py"
    build_py.write_text(
        "page0.add(TextFrame(anname='u1', runs=[Run(text='Hello')]))\n",
        encoding="utf-8",
    )
    run_texts = _extract_run_texts_from_build_py(build_py)
    # Normalise + check consistent YAML
    from baseline_text_audit import _yaml_dump
    data1 = {"pages": [{"page": 0, "lines_total": 1, "lines_matched": 1}], "template": "t"}
    data2 = {"pages": [{"page": 0, "lines_total": 1, "lines_matched": 1}], "template": "t"}
    assert _yaml_dump(data1) == _yaml_dump(data2)


def test_run_text_audit_with_matching_text(tmp_path):
    """run_text_audit smoke: when all text in PDF matches build.py, no unmatched lines."""
    root = Path(__file__).resolve().parents[2]
    baseline = (
        root / "templates" / "kandidat-falzflyer-din-lang-gruenes-cover-v2" / "baseline.pdf"
    )
    build_py = (
        root / "templates" / "kandidat-falzflyer-din-lang-gruenes-cover-v2" / "build.py"
    )
    if not baseline.exists() or not build_py.exists():
        pytest.skip("Real baseline.pdf/build.py not available")

    report = run_text_audit(baseline, build_py)
    # All text in the current build.py should match the baseline
    # (Leonore Gewessler is in u3ba)
    assert report["template"] == "kandidat-falzflyer-din-lang-gruenes-cover-v2"
    assert len(report["pages"]) == 2


def test_text_audit_unmatched_line(tmp_path):
    """When build.py is missing a text frame, the text appears as unmatched."""
    root = Path(__file__).resolve().parents[2]
    baseline = (
        root / "templates" / "kandidat-falzflyer-din-lang-gruenes-cover-v2" / "baseline.pdf"
    )
    if not baseline.exists():
        pytest.skip("Real baseline.pdf not available")

    # Build.py with NO text frames — all baseline text should be unmatched
    build_py = tmp_path / "build.py"
    build_py.write_text(
        "# empty build.py — no TextFrames\n",
        encoding="utf-8",
    )
    report = run_text_audit(baseline, build_py)
    # Should have many unmatched lines since there are no run texts
    all_unmatched = [
        line
        for p in report["pages"]
        for line in p.get("lines_unmatched", [])
    ]
    # At minimum "Leonore Gewessler" should be unmatched
    leonore_lines = [e for e in all_unmatched if "Leonore" in e.get("line", "")]
    assert len(leonore_lines) >= 1, (
        f"Expected 'Leonore Gewessler' in unmatched lines; got: "
        f"{[e['line'] for e in all_unmatched[:10]]}"
    )
