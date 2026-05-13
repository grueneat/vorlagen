"""Unit tests for tools/reconcile_build_py.py."""
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

import reconcile_build_py as rbp  # noqa: E402


_TEMPLATE_BUILD_PY = """\
from sla_lib.builder import Document, TextFrame, ImageFrame

def build():
    doc = Document(title='t', template_id='t1')
    page0 = doc.add_page(size='A4')
    page0.add(TextFrame(
        x_mm=10.0,
        y_mm=20.0,
        w_mm=80.0,
        h_mm=15.0,
        anname='u123',
        layer=0,
        ALIGN=0,
    ))
    page0.add(ImageFrame(
        x_mm=100.0,
        y_mm=50.0,
        w_mm=40.0,
        h_mm=40.0,
        anname='u456',
        layer=0,
        scale_type=0,
    ))
    return doc
"""


def _setup_template(tmp_path: Path, slug: str, inject_data: dict) -> Path:
    tdir = tmp_path / "templates" / slug
    tdir.mkdir(parents=True)
    (tdir / "build.py.generated").write_text(_TEMPLATE_BUILD_PY, encoding="utf-8")
    inject_yml = tdir / "inject.yml"
    inject_yml.write_text(yaml.safe_dump(inject_data, sort_keys=False), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Test 1 — set: replaces a field and inserts the inline comment.
# ---------------------------------------------------------------------------
def test_set_replaces_field_with_comment(tmp_path):
    inject = {
        "hand_patches": [
            {
                "target": {"element": "TextFrame", "anname": "u123"},
                "field": "ALIGN",
                "set": 1,
                "classification": "converter-bug",
                "reason": "Centered headline; converter emitted ALIGN=0 by default.",
            }
        ]
    }
    root = _setup_template(tmp_path, "t1", inject)
    output, warnings = rbp.reconcile("t1", repo_root=root, quiet=True)
    assert "ALIGN=1" in output
    assert "P5/inject (from inject.yml line" in output


# ---------------------------------------------------------------------------
# Test 2 — byte-stability: reconcile twice produces identical output.
# ---------------------------------------------------------------------------
def test_byte_stability_two_runs(tmp_path):
    inject = {
        "hand_patches": [
            {
                "target": {"element": "TextFrame", "anname": "u123"},
                "field": "ALIGN",
                "set": 1,
                "classification": "converter-bug",
                "reason": "Test fixture rationale text >= 10 chars.",
            }
        ]
    }
    root = _setup_template(tmp_path, "t1", inject)
    out_a, _ = rbp.reconcile("t1", repo_root=root, quiet=True)
    out_b, _ = rbp.reconcile("t1", repo_root=root, quiet=True)
    assert out_a == out_b


# ---------------------------------------------------------------------------
# Test 3 — redundancy warning when set value already equals generated value.
# ---------------------------------------------------------------------------
def test_redundancy_warning_when_set_equals_generated(tmp_path):
    inject = {
        "hand_patches": [
            {
                "target": {"element": "TextFrame", "anname": "u123"},
                "field": "ALIGN",
                "set": 0,  # same as generated
                "classification": "converter-bug",
                "reason": "Redundancy test; should fire warning.",
            }
        ]
    }
    root = _setup_template(tmp_path, "t1", inject)
    _output, warnings = rbp.reconcile("t1", repo_root=root, quiet=True)
    assert any("redundant" in w for w in warnings)


# ---------------------------------------------------------------------------
# Test 4 — delta: adds offset to numeric value.
# ---------------------------------------------------------------------------
def test_delta_adds_offset(tmp_path):
    inject = {
        "hand_patches": [
            {
                "target": {"element": "TextFrame", "anname": "u123"},
                "field": "y_mm",
                "delta": 1.884,
                "classification": "scribus-engine-bug",
                "reason": "FirstBaselineOffset compensation; engine bug.",
            }
        ]
    }
    root = _setup_template(tmp_path, "t1", inject)
    output, _warnings = rbp.reconcile("t1", repo_root=root, quiet=True)
    # 20.0 + 1.884 = 21.884
    assert "y_mm=21.884" in output


# ---------------------------------------------------------------------------
# Test 5 — order matters: last-wins on conflict.
# ---------------------------------------------------------------------------
def test_order_last_wins(tmp_path):
    inject = {
        "hand_patches": [
            {
                "target": {"element": "TextFrame", "anname": "u123"},
                "field": "ALIGN",
                "set": 1,
                "classification": "converter-bug",
                "reason": "First entry sets ALIGN to 1 for testing order.",
            },
            {
                "target": {"element": "TextFrame", "anname": "u123"},
                "field": "ALIGN",
                "set": 2,
                "classification": "converter-bug",
                "reason": "Second entry overrides to ALIGN=2; should win.",
            },
        ]
    }
    root = _setup_template(tmp_path, "t1", inject)
    output, _ = rbp.reconcile("t1", repo_root=root, quiet=True)
    # Both inline comments must be present; the second mutation wins.
    assert output.count("P5/inject") == 2
    # The last-applied value is 2.
    assert "ALIGN=2" in output


# ---------------------------------------------------------------------------
# Test 6 — --check passes when build.py matches reconciled output.
# ---------------------------------------------------------------------------
def test_check_mode_passes_on_match(tmp_path):
    inject = {
        "hand_patches": [
            {
                "target": {"element": "TextFrame", "anname": "u123"},
                "field": "ALIGN",
                "set": 1,
                "classification": "converter-bug",
                "reason": "Test fixture rationale long enough.",
            }
        ]
    }
    root = _setup_template(tmp_path, "t1", inject)
    output, _ = rbp.reconcile("t1", repo_root=root, quiet=True)
    (root / "templates" / "t1" / "build.py").write_text(output, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "reconcile_build_py.py"),
            "t1",
            "--check",
            "--repo-root",
            str(root),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_check_mode_fails_on_mismatch(tmp_path):
    inject = {
        "hand_patches": [
            {
                "target": {"element": "TextFrame", "anname": "u123"},
                "field": "ALIGN",
                "set": 1,
                "classification": "converter-bug",
                "reason": "Test fixture rationale long enough.",
            }
        ]
    }
    root = _setup_template(tmp_path, "t1", inject)
    (root / "templates" / "t1" / "build.py").write_text("wrong content", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "reconcile_build_py.py"),
            "t1",
            "--check",
            "--repo-root",
            str(root),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1


# ---------------------------------------------------------------------------
# Test 7 — invalid inject.yml raises ValueError.
# ---------------------------------------------------------------------------
def test_invalid_inject_yml_rejected(tmp_path):
    inject = {
        "hand_patches": [
            {
                # Missing required 'target', 'classification', 'reason'.
                "field": "ALIGN",
                "set": 1,
            }
        ]
    }
    root = _setup_template(tmp_path, "t1", inject)
    with pytest.raises(ValueError):
        rbp.reconcile("t1", repo_root=root, quiet=True)


# ---------------------------------------------------------------------------
# Test 8 — missing build.py.generated raises FileNotFoundError.
# ---------------------------------------------------------------------------
def test_missing_generated_raises(tmp_path):
    (tmp_path / "templates" / "t1").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        rbp.reconcile("t1", repo_root=tmp_path, quiet=True)
