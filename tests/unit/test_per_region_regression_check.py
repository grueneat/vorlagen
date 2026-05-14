"""Unit tests for tools/per_region_regression_check.py.

Covers:
- F-021: --line-spacing-threshold and --visibility-threshold CLI flags
- F-022: --compare-main mode (reads `git show origin/main:<path>`)
- Existing detect_regressions logic, append_history, load_previous

The pipeline-integration is exercised separately in the integration
suite via `bin/render-gallery --audit`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import per_region_regression_check as prr  # noqa: E402


# ---------------------------------------------------------------------------
# detect_regressions — threshold knobs (F-021)
# ---------------------------------------------------------------------------


def test_default_thresholds_match_legacy_constants():
    """Smoke: default values match the pre-F-021 constants exactly."""
    # Drift increased by exactly 0.5 → fires at default threshold.
    regs = prr.detect_regressions(
        prev_line_spacing={"u1": 1.0},
        curr_line_spacing={"u1": 1.5},
        prev_visibility={},
        curr_visibility={},
    )
    assert any(r["kind"] == "line_spacing_drift_increased" for r in regs)
    # Visibility drop ≥0.10 (use 0.85 → 0.74 to avoid float-rep noise on
    # 0.9 - 0.8). Default threshold 0.10 fires.
    regs = prr.detect_regressions(
        prev_line_spacing={},
        curr_line_spacing={},
        prev_visibility={"u2": 0.85},
        curr_visibility={"u2": 0.74},
    )
    assert any(r["kind"] == "image_visibility_dropped" for r in regs)


def test_line_spacing_threshold_raised_suppresses_small_regression():
    """F-021: with --line-spacing-threshold=2.0 a 0.5pt drift increase
    no longer fires."""
    regs = prr.detect_regressions(
        prev_line_spacing={"u1": 1.0},
        curr_line_spacing={"u1": 1.5},
        prev_visibility={},
        curr_visibility={},
        line_spacing_threshold_pt=2.0,
    )
    assert not regs


def test_line_spacing_threshold_lowered_surfaces_tiny_regression():
    """Conversely, a tighter threshold surfaces a 0.1pt drift."""
    regs = prr.detect_regressions(
        prev_line_spacing={"u1": 1.0},
        curr_line_spacing={"u1": 1.1},
        prev_visibility={},
        curr_visibility={},
        line_spacing_threshold_pt=0.05,
    )
    assert any(r["kind"] == "line_spacing_drift_increased" for r in regs)


def test_visibility_threshold_tunable():
    """F-021: visibility_threshold knob suppresses / surfaces drops."""
    # 0.05 drop, default 0.10 → no regression
    regs = prr.detect_regressions(
        prev_line_spacing={},
        curr_line_spacing={},
        prev_visibility={"u1": 0.9},
        curr_visibility={"u1": 0.85},
    )
    assert not regs
    # Same drop, lowered threshold to 0.04 → regression
    regs = prr.detect_regressions(
        prev_line_spacing={},
        curr_line_spacing={},
        prev_visibility={"u1": 0.9},
        curr_visibility={"u1": 0.85},
        visibility_threshold=0.04,
    )
    assert any(r["kind"] == "image_visibility_dropped" for r in regs)


# ---------------------------------------------------------------------------
# load_main_branch_entry — F-022
# ---------------------------------------------------------------------------


def test_compare_main_loads_last_entry_via_git_show(tmp_path, monkeypatch):
    """F-022: load_main_branch_entry reads `git show <ref>:<path>` and
    returns the LAST parseable JSON row."""
    entry_a = {
        "timestamp": "2026-05-01T00:00:00+00:00",
        "line_spacing_max_drift_pt": {"u1": 1.0},
        "image_visibility_ratio": {"u2": 0.9},
    }
    entry_b = {
        "timestamp": "2026-05-12T12:00:00+00:00",
        "line_spacing_max_drift_pt": {"u1": 0.5},
        "image_visibility_ratio": {"u2": 0.95},
    }
    fake_stdout = json.dumps(entry_a) + "\n" + json.dumps(entry_b) + "\n"

    class _R:
        returncode = 0
        stdout = fake_stdout

    called = {}

    def fake_run(cmd, **kw):
        called["cmd"] = cmd
        called["cwd"] = kw.get("cwd")
        return _R()

    monkeypatch.setattr(prr.subprocess, "run", fake_run)
    # Use a real repo_root that resolves under tmp_path so relative_to works.
    history_dir = tmp_path / "templates"
    (history_dir / "myslug").mkdir(parents=True)
    out = prr.load_main_branch_entry(
        "myslug",
        history_dir=history_dir,
        repo_root=tmp_path,
        main_ref="origin/main",
    )
    assert out == entry_b
    assert called["cmd"][:2] == ["git", "show"]
    assert "origin/main:" in called["cmd"][2]
    assert called["cmd"][2].endswith("templates/myslug/per_region_history.jsonl")


def test_compare_main_returns_none_when_git_missing(tmp_path, monkeypatch):
    """No git binary on $PATH → return None (caller falls back to seed)."""
    def fake_run(*a, **k):
        raise FileNotFoundError("git")
    monkeypatch.setattr(prr.subprocess, "run", fake_run)
    history_dir = tmp_path / "templates"
    (history_dir / "myslug").mkdir(parents=True)
    out = prr.load_main_branch_entry(
        "myslug",
        history_dir=history_dir,
        repo_root=tmp_path,
    )
    assert out is None


def test_compare_main_returns_none_when_ref_missing(tmp_path, monkeypatch):
    """git show exits non-zero (ref not found) → return None."""
    class _R:
        returncode = 128
        stdout = ""
    monkeypatch.setattr(prr.subprocess, "run", lambda *a, **k: _R())
    history_dir = tmp_path / "templates"
    (history_dir / "myslug").mkdir(parents=True)
    out = prr.load_main_branch_entry(
        "myslug",
        history_dir=history_dir,
        repo_root=tmp_path,
    )
    assert out is None


def test_compare_main_returns_none_when_file_empty(tmp_path, monkeypatch):
    """git show succeeded but the file at that ref has no JSON rows."""
    class _R:
        returncode = 0
        stdout = ""
    monkeypatch.setattr(prr.subprocess, "run", lambda *a, **k: _R())
    history_dir = tmp_path / "templates"
    (history_dir / "myslug").mkdir(parents=True)
    out = prr.load_main_branch_entry(
        "myslug",
        history_dir=history_dir,
        repo_root=tmp_path,
    )
    assert out is None


def test_compare_main_skips_malformed_rows(tmp_path, monkeypatch):
    """Malformed JSON rows are skipped — last VALID row wins."""
    good = {"timestamp": "T1", "line_spacing_max_drift_pt": {"u1": 1.0}}
    fake_stdout = json.dumps(good) + "\nnot-json-here\n"

    class _R:
        returncode = 0
        stdout = fake_stdout
    monkeypatch.setattr(prr.subprocess, "run", lambda *a, **k: _R())
    history_dir = tmp_path / "templates"
    (history_dir / "myslug").mkdir(parents=True)
    out = prr.load_main_branch_entry(
        "myslug",
        history_dir=history_dir,
        repo_root=tmp_path,
    )
    assert out == good


# ---------------------------------------------------------------------------
# main() end-to-end — F-021 + F-022 wired through argparse
# ---------------------------------------------------------------------------


def _seed_audit_yamls(val_dir: Path, slug: str, *, drift: dict, visibility: dict):
    base = val_dir / slug
    base.mkdir(parents=True, exist_ok=True)
    (base / "line_spacing_pixel_audit.yml").write_text(
        "rows:\n"
        + "".join(
            f"- anname: {an}\n  max_drift_pt: {d}\n"
            for an, d in drift.items()
        )
    )
    (base / "image_frame_visibility_audit.yml").write_text(
        "rows:\n"
        + "".join(
            f"- anname: {an}\n  visibility_ratio: {v}\n"
            for an, v in visibility.items()
        )
    )


def test_main_compare_main_falls_back_to_seed_on_missing_ref(tmp_path, monkeypatch, capsys):
    """F-022: when origin/main has no history entry, main() reports
    seeded and does not raise."""
    slug = "myslug"
    val_dir = tmp_path / "build" / "validation"
    history_dir = tmp_path / "templates"
    _seed_audit_yamls(val_dir, slug, drift={"u1": 1.0}, visibility={"u2": 0.9})

    # No git → load_main_branch_entry returns None.
    monkeypatch.setattr(prr, "load_main_branch_entry", lambda *a, **k: None)

    rc = prr.main([
        "--slug", slug,
        "--validation-dir", str(val_dir),
        "--history-dir", str(history_dir),
        "--compare-main",
        "--out-yaml", str(tmp_path / "out.yml"),
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "seeded" in captured.err
    assert "origin/main" in captured.err
    # And history was still appended.
    assert (history_dir / slug / "per_region_history.jsonl").exists()


def test_main_compare_main_uses_main_entry_when_present(tmp_path, monkeypatch, capsys):
    """F-022: when origin/main has an entry, main() compares against it
    and surfaces the timestamp in the messaging."""
    slug = "myslug"
    val_dir = tmp_path / "build" / "validation"
    history_dir = tmp_path / "templates"
    _seed_audit_yamls(val_dir, slug, drift={"u1": 2.5}, visibility={"u2": 0.7})

    main_entry = {
        "timestamp": "2026-05-01T00:00:00+00:00",
        "line_spacing_max_drift_pt": {"u1": 1.0},
        "image_visibility_ratio": {"u2": 0.9},
    }
    monkeypatch.setattr(prr, "load_main_branch_entry", lambda *a, **k: main_entry)

    rc = prr.main([
        "--slug", slug,
        "--validation-dir", str(val_dir),
        "--history-dir", str(history_dir),
        "--compare-main",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    # The 2.5 vs 1.0 drift increase (delta=+1.5) exceeds the default 0.5
    # threshold → regression.
    assert "regression" in captured.err.lower()
    assert "origin/main" in captured.err
    assert "2026-05-01T00:00:00+00:00" in captured.err


def test_main_cli_thresholds_change_behaviour(tmp_path, monkeypatch, capsys):
    """F-021: CLI threshold flags actually flow through to detect_regressions."""
    slug = "myslug"
    val_dir = tmp_path / "build" / "validation"
    history_dir = tmp_path / "templates"
    _seed_audit_yamls(val_dir, slug, drift={"u1": 1.5}, visibility={"u2": 0.9})

    # Seed local history so we have a prev row to compare.
    (history_dir / slug).mkdir(parents=True)
    (history_dir / slug / "per_region_history.jsonl").write_text(
        json.dumps({
            "timestamp": "T0",
            "line_spacing_max_drift_pt": {"u1": 1.0},
            "image_visibility_ratio": {"u2": 0.9},
        }) + "\n"
    )

    # Run 1: default threshold (0.5) → 0.5pt drift increase fires.
    rc = prr.main([
        "--slug", slug,
        "--validation-dir", str(val_dir),
        "--history-dir", str(history_dir),
    ])
    assert rc == 0
    err = capsys.readouterr().err
    assert "regression" in err.lower()

    # Reset history (the previous run appended) and rerun with a higher
    # threshold to confirm it suppresses.
    (history_dir / slug / "per_region_history.jsonl").write_text(
        json.dumps({
            "timestamp": "T0",
            "line_spacing_max_drift_pt": {"u1": 1.0},
            "image_visibility_ratio": {"u2": 0.9},
        }) + "\n"
    )
    rc = prr.main([
        "--slug", slug,
        "--validation-dir", str(val_dir),
        "--history-dir", str(history_dir),
        "--line-spacing-threshold", "2.0",
    ])
    assert rc == 0
    err = capsys.readouterr().err
    assert "OK" in err  # No regression at threshold 2.0
