"""Unit tests for tools/lint_inject_consistency.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import lint_inject_consistency as lic  # noqa: E402


def _setup(tmp_path: Path, slug: str, build_py: str, inject: dict | None) -> Path:
    tdir = tmp_path / "templates" / slug
    tdir.mkdir(parents=True)
    (tdir / "build.py").write_text(build_py, encoding="utf-8")
    if inject is not None:
        (tdir / "inject.yml").write_text(
            yaml.safe_dump(inject, sort_keys=False),
            encoding="utf-8",
        )
    return tmp_path


_VALID_ENTRY = {
    "target": {"element": "TextFrame", "anname": "u123"},
    "field": "ALIGN",
    "set": 0,
    "classification": "converter-bug",
    "reason": "test fixture rationale ten or more chars",
}


# ---------------------------------------------------------------------------
# Test 1 — state A (no inject + no comments) is clean.
# ---------------------------------------------------------------------------
def test_state_a_no_inject_no_comments_clean(tmp_path):
    root = _setup(tmp_path, "t1", "# pristine build.py\n", None)
    errs = lic.check_template("t1", root)
    assert errs == []


# ---------------------------------------------------------------------------
# Test 2 — state B (inject present, no inline comments) is clean.
# ---------------------------------------------------------------------------
def test_state_b_inject_only_clean(tmp_path):
    root = _setup(
        tmp_path,
        "t1",
        "# build.py without P5/inject inline comments\n",
        {"hand_patches": [_VALID_ENTRY]},
    )
    errs = lic.check_template("t1", root)
    assert errs == []


# ---------------------------------------------------------------------------
# Test 3 — state C with matching 1:1 mapping is clean.
# ---------------------------------------------------------------------------
def test_state_c_matched_mapping_clean(tmp_path):
    inject_data = {"hand_patches": [_VALID_ENTRY]}
    # The first hand_patches entry's '- target:' line is line 3 when
    # yaml.safe_dump produces "hand_patches:\n- target:..." -- let's
    # construct deterministically.
    inject_yaml_text = (
        "hand_patches:\n"
        "- target:\n"
        "    element: TextFrame\n"
        "    anname: u123\n"
        "  field: ALIGN\n"
        "  set: 0\n"
        "  classification: converter-bug\n"
        "  reason: test fixture rationale ten or more chars\n"
    )
    tdir = tmp_path / "templates" / "t1"
    tdir.mkdir(parents=True)
    (tdir / "inject.yml").write_text(inject_yaml_text, encoding="utf-8")
    # Line 2 of inject.yml is the '- target:' line. The build.py comment
    # must cite line 2.
    (tdir / "build.py").write_text(
        "# P5/inject (from inject.yml line 2): centered headline\n",
        encoding="utf-8",
    )
    errs = lic.check_template("t1", tmp_path)
    assert errs == []


# ---------------------------------------------------------------------------
# Test 4 — comment cites a line where inject.yml has no entry.
# ---------------------------------------------------------------------------
def test_comment_cites_missing_line(tmp_path):
    inject_text = "hand_patches:\n- target:\n    element: TextFrame\n    anname: u123\n  field: ALIGN\n  set: 0\n  classification: converter-bug\n  reason: rationale long enough\n"
    tdir = tmp_path / "templates" / "t1"
    tdir.mkdir(parents=True)
    (tdir / "inject.yml").write_text(inject_text, encoding="utf-8")
    (tdir / "build.py").write_text(
        "# P5/inject (from inject.yml line 999): wrong line\n",
        encoding="utf-8",
    )
    errs = lic.check_template("t1", tmp_path)
    assert any("line 999" in e for e in errs)


# ---------------------------------------------------------------------------
# Test 5 — inject entry without matching build.py comment (in state C).
# ---------------------------------------------------------------------------
def test_inject_entry_without_comment(tmp_path):
    inject_text = (
        "hand_patches:\n"
        "- target:\n"
        "    element: TextFrame\n"
        "    anname: u123\n"
        "  field: ALIGN\n"
        "  set: 0\n"
        "  classification: converter-bug\n"
        "  reason: rationale long enough\n"
        "- target:\n"
        "    element: TextFrame\n"
        "    anname: u456\n"
        "  field: y_mm\n"
        "  delta: 1.0\n"
        "  classification: scribus-engine-bug\n"
        "  reason: rationale long enough\n"
    )
    tdir = tmp_path / "templates" / "t1"
    tdir.mkdir(parents=True)
    (tdir / "inject.yml").write_text(inject_text, encoding="utf-8")
    # State C: one inline comment, citing the FIRST entry only.
    (tdir / "build.py").write_text(
        "# P5/inject (from inject.yml line 2): first entry only\n",
        encoding="utf-8",
    )
    errs = lic.check_template("t1", tmp_path)
    # Should flag the missing second entry.
    assert any("line 10" in e or "line 9" in e for e in errs), errs


# ---------------------------------------------------------------------------
# Test 6 — invalid schema flagged.
# ---------------------------------------------------------------------------
def test_invalid_schema_flagged(tmp_path):
    inject_text = (
        "hand_patches:\n"
        "- target:\n"
        "    element: TextFrame\n"
        "    anname: u123\n"
        "  field: ALIGN\n"
        # missing 'set' AND 'delta' => oneOf violation
        "  classification: converter-bug\n"
        "  reason: rationale long enough\n"
    )
    tdir = tmp_path / "templates" / "t1"
    tdir.mkdir(parents=True)
    (tdir / "inject.yml").write_text(inject_text, encoding="utf-8")
    (tdir / "build.py").write_text("", encoding="utf-8")
    errs = lic.check_template("t1", tmp_path)
    assert any("schema" in e for e in errs)


# ---------------------------------------------------------------------------
# Test 7 — --template flag limits the scan.
# ---------------------------------------------------------------------------
def test_template_flag_limits_scan(tmp_path):
    _setup(tmp_path, "good", "# clean\n", None)
    _setup(tmp_path, "bad", "# P5/inject (from inject.yml line 99): orphan\n", None)
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "lint_inject_consistency.py"),
            "--template", "good",
            "--repo-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Test 8 — CLI exits 0 against the current tree.
# ---------------------------------------------------------------------------
def test_cli_exits_zero_on_current_tree():
    result = subprocess.run(
        [sys.executable, str(TOOLS / "lint_inject_consistency.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}"
