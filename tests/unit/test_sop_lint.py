"""Unit tests for tools/sop_lint.py — banned-phrase guard.

The lint walks `git ls-files`, filters by scope, and greps for the
rendering-floor family of banned phrases. Tests construct an ephemeral
git repo under tmp_path so we can exercise the real subprocess call
without mocking.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import sop_lint  # noqa: E402


def _make_repo(tmp_path: Path) -> Path:
    """Create a fresh git repo with a single commit so git ls-files works."""
    subprocess.check_call(["git", "init", "-q"], cwd=tmp_path)
    subprocess.check_call(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path
    )
    subprocess.check_call(
        ["git", "config", "user.name", "test"], cwd=tmp_path
    )
    return tmp_path


def _track(repo: Path, rel: str, content: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    subprocess.check_call(["git", "add", rel], cwd=repo)
    subprocess.check_call(
        ["git", "commit", "-qm", f"add {rel}"], cwd=repo
    )


def _run_lint(repo: Path) -> int:
    """Invoke find_offenders from within the temp repo."""
    offenders = sop_lint.find_offenders(repo_root=repo)
    return 1 if offenders else 0


# ---------------------------------------------------------------------------
# Test 1 — positive: banned phrase in tracked tools/ file triggers exit 1.
# ---------------------------------------------------------------------------
def test_engine_floor_in_tracked_tools_file_triggers_failure(tmp_path):
    repo = _make_repo(tmp_path)
    _track(repo, "tools/foo.py", '"""This declares the engine floor."""\n')

    rc = _run_lint(repo)
    offenders = sop_lint.find_offenders(repo_root=repo)
    assert rc == 1
    assert len(offenders) == 1
    assert offenders[0][0] == "tools/foo.py"


# ---------------------------------------------------------------------------
# Test 2 — negative: same file with the rename passes.
# ---------------------------------------------------------------------------
def test_renamed_file_passes(tmp_path):
    repo = _make_repo(tmp_path)
    _track(
        repo,
        "tools/foo.py",
        '"""This is the icc_drift_uniform_small classifier."""\n',
    )

    rc = _run_lint(repo)
    assert rc == 0


# ---------------------------------------------------------------------------
# Test 3 — scope: untracked file with the phrase is ignored.
# ---------------------------------------------------------------------------
def test_untracked_file_is_ignored(tmp_path):
    repo = _make_repo(tmp_path)
    _track(repo, "tools/clean.py", "# clean file\n")
    # node_modules/foo.js exists in the repo dir but is NOT tracked.
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "foo.js").write_text(
        "// engine floor here\n", encoding="utf-8"
    )

    rc = _run_lint(repo)
    assert rc == 0


# ---------------------------------------------------------------------------
# Test 3b — scope: tracked but out-of-scope path is ignored.
# ---------------------------------------------------------------------------
def test_tracked_out_of_scope_path_is_ignored(tmp_path):
    repo = _make_repo(tmp_path)
    # .issues/ is intentionally NOT in scope — it preserves history.
    _track(
        repo,
        ".issues/archive/old.md",
        "Historical note: declared engine floor.\n",
    )

    rc = _run_lint(repo)
    assert rc == 0


# ---------------------------------------------------------------------------
# Test 4 — synonyms: engine ceiling + rendering floor both trigger.
# ---------------------------------------------------------------------------
def test_engine_ceiling_synonym_triggers(tmp_path):
    repo = _make_repo(tmp_path)
    _track(repo, "tools/foo.py", "# engine ceiling reached\n")

    offenders = sop_lint.find_offenders(repo_root=repo)
    assert len(offenders) == 1


def test_rendering_floor_synonym_triggers(tmp_path):
    repo = _make_repo(tmp_path)
    _track(repo, "tools/foo.py", "# the rendering floor is here\n")

    offenders = sop_lint.find_offenders(repo_root=repo)
    assert len(offenders) == 1


# ---------------------------------------------------------------------------
# Test 5 — case-insensitive matching.
# ---------------------------------------------------------------------------
def test_case_insensitive_matching(tmp_path):
    repo = _make_repo(tmp_path)
    _track(repo, "tools/foo.py", "# ENGINE FLOOR reached\n")

    offenders = sop_lint.find_offenders(repo_root=repo)
    assert len(offenders) == 1


# ---------------------------------------------------------------------------
# Test 6 — underscored variant engine_floor also triggers.
# ---------------------------------------------------------------------------
def test_underscore_variant_triggers(tmp_path):
    repo = _make_repo(tmp_path)
    _track(repo, "tools/foo.py", 'severity = "engine_floor"\n')

    offenders = sop_lint.find_offenders(repo_root=repo)
    assert len(offenders) == 1


# ---------------------------------------------------------------------------
# Test 7 — self-exclude: sop_lint.py and its tests are not flagged.
# ---------------------------------------------------------------------------
def test_self_exclude(tmp_path):
    repo = _make_repo(tmp_path)
    # Mirror the real path; content names the phrase.
    _track(
        repo,
        "tools/sop_lint.py",
        'BANNED = ["engine floor", "engine ceiling"]\n',
    )

    rc = _run_lint(repo)
    assert rc == 0


# ---------------------------------------------------------------------------
# Test 8 — README at repo root is in scope.
# ---------------------------------------------------------------------------
def test_top_level_readme_in_scope(tmp_path):
    repo = _make_repo(tmp_path)
    _track(repo, "README.md", "# Project\n\nDeclares engine floor.\n")

    offenders = sop_lint.find_offenders(repo_root=repo)
    assert len(offenders) == 1


# ---------------------------------------------------------------------------
# Test 9 — main() invoked as CLI returns 0 on clean tree.
# ---------------------------------------------------------------------------
def test_cli_invocation_clean(tmp_path):
    repo = _make_repo(tmp_path)
    _track(repo, "tools/clean.py", "# nothing here\n")

    result = subprocess.run(
        [sys.executable, str(TOOLS / "sop_lint.py")],
        cwd=repo,
        capture_output=True,
    )
    assert result.returncode == 0


def test_cli_invocation_dirty(tmp_path):
    repo = _make_repo(tmp_path)
    _track(repo, "tools/dirty.py", "# engine floor\n")

    result = subprocess.run(
        [sys.executable, str(TOOLS / "sop_lint.py")],
        cwd=repo,
        capture_output=True,
    )
    assert result.returncode == 1
    assert b"SOP-LINT FAILED" in result.stderr
