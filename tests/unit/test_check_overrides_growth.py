"""Unit tests for tools/check_overrides_growth.py."""
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

import check_overrides_growth as cog  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers.
# ---------------------------------------------------------------------------

def _git_init(tmp_path: Path) -> Path:
    """Initialise a fresh git repo under tmp_path with deterministic identity."""
    subprocess.check_call(["git", "init", "-q"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.email", "t@x"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=tmp_path)
    return tmp_path


def _commit(repo: Path, msg: str) -> None:
    subprocess.check_call(["git", "add", "-A"], cwd=repo)
    subprocess.check_call(["git", "commit", "-qm", msg], cwd=repo)


def _branch_base(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo
    ).decode().strip()


def _write_meta(
    repo: Path,
    slug: str,
    brand_overrides: list[dict] | None = None,
    extra: dict | None = None,
) -> None:
    slug_dir = repo / "templates" / slug
    slug_dir.mkdir(parents=True, exist_ok=True)
    meta: dict = {"id": slug}
    if brand_overrides is not None:
        meta["brand_overrides"] = brand_overrides
    if extra:
        meta.update(extra)
    (slug_dir / "meta.yml").write_text(
        yaml.safe_dump(meta, sort_keys=True),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Test 1 — added entry without justification => exit 1.
# ---------------------------------------------------------------------------
def test_added_entry_without_justification_fails(tmp_path):
    repo = _git_init(tmp_path)
    _write_meta(repo, "t1", brand_overrides=[{"id": "brand:X", "reason": "..."}])
    _commit(repo, "base")
    base = _branch_base(repo)
    _write_meta(
        repo,
        "t1",
        brand_overrides=[
            {"id": "brand:X", "reason": "..."},
            {"id": "brand:Y", "reason": "..."},
        ],
    )
    _commit(repo, "add Y")

    violations = cog.check_growth(base, repo)
    assert len(violations) == 1
    slug, key, eid = violations[0]
    assert slug == "t1"
    assert key == "brand_overrides"
    assert eid == "brand:Y"


# ---------------------------------------------------------------------------
# Test 2 — added entry with TOLERANCE_LOG.md row passes.
# ---------------------------------------------------------------------------
def test_added_entry_with_tolerance_log_passes(tmp_path):
    repo = _git_init(tmp_path)
    _write_meta(repo, "t1", brand_overrides=[{"id": "brand:X", "reason": "..."}])
    _commit(repo, "base")
    base = _branch_base(repo)
    _write_meta(
        repo,
        "t1",
        brand_overrides=[
            {"id": "brand:X", "reason": "..."},
            {"id": "brand:Y", "reason": "..."},
        ],
    )
    (repo / "templates" / "t1" / "TOLERANCE_LOG.md").write_text(
        "# Tolerance Log — t1\n\n## brand:Y — 2026-05-13 — reason: ...\n",
        encoding="utf-8",
    )
    _commit(repo, "add Y + log")

    violations = cog.check_growth(base, repo)
    assert violations == []


# ---------------------------------------------------------------------------
# Test 3 — added entry with inject.yml hand_patch reason passes.
# ---------------------------------------------------------------------------
def test_added_entry_with_inject_entry_passes(tmp_path):
    repo = _git_init(tmp_path)
    _write_meta(repo, "t1", brand_overrides=[{"id": "brand:X", "reason": "..."}])
    _commit(repo, "base")
    base = _branch_base(repo)
    _write_meta(
        repo,
        "t1",
        brand_overrides=[
            {"id": "brand:X", "reason": "..."},
            {"id": "brand:Y", "reason": "..."},
        ],
    )
    inject = repo / "templates" / "t1" / "inject.yml"
    inject.write_text(
        yaml.safe_dump(
            {
                "hand_patches": [
                    {
                        "target": {"element": "ParaStyle", "anname": "u1"},
                        "field": "ALIGN",
                        "set": 0,
                        "classification": "converter-bug",
                        "reason": "Y override rationale tracks brand:Y from meta.yml.",
                    }
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _commit(repo, "add Y + inject")

    violations = cog.check_growth(base, repo)
    assert violations == []


# ---------------------------------------------------------------------------
# Test 4 — removal of an entry is always allowed.
# ---------------------------------------------------------------------------
def test_removal_is_always_allowed(tmp_path):
    repo = _git_init(tmp_path)
    _write_meta(
        repo,
        "t1",
        brand_overrides=[
            {"id": "brand:X", "reason": "..."},
            {"id": "brand:Y", "reason": "..."},
        ],
    )
    _commit(repo, "base")
    base = _branch_base(repo)
    _write_meta(repo, "t1", brand_overrides=[{"id": "brand:X", "reason": "..."}])
    _commit(repo, "drop Y")

    violations = cog.check_growth(base, repo)
    assert violations == []


# ---------------------------------------------------------------------------
# Test 5 — new template with no base meta.yml => every entry needs a log.
# ---------------------------------------------------------------------------
def test_new_template_requires_log_or_inject(tmp_path):
    repo = _git_init(tmp_path)
    # Base commit: an unrelated file.
    (repo / "README.md").write_text("# r\n", encoding="utf-8")
    _commit(repo, "base")
    base = _branch_base(repo)
    _write_meta(
        repo,
        "tnew",
        brand_overrides=[
            {"id": "brand:A", "reason": "..."},
            {"id": "brand:B", "reason": "..."},
        ],
    )
    _commit(repo, "add tnew")

    violations = cog.check_growth(base, repo)
    assert len(violations) == 2
    assert {v[2] for v in violations} == {"brand:A", "brand:B"}

    # Add a TOLERANCE_LOG.md row for A only — B still fails.
    (repo / "templates" / "tnew" / "TOLERANCE_LOG.md").write_text(
        "## brand:A — 2026-05-13 — reason: ...\n",
        encoding="utf-8",
    )
    _commit(repo, "log A")
    violations = cog.check_growth(base, repo)
    assert len(violations) == 1
    assert violations[0][2] == "brand:B"


# ---------------------------------------------------------------------------
# Test 6 — string-form entries (plain list) also work.
# ---------------------------------------------------------------------------
def test_string_form_entries(tmp_path):
    repo = _git_init(tmp_path)
    _write_meta(repo, "t1", brand_overrides=["brand:X"])
    _commit(repo, "base")
    base = _branch_base(repo)
    _write_meta(repo, "t1", brand_overrides=["brand:X", "brand:Y"])
    _commit(repo, "add Y")

    violations = cog.check_growth(base, repo)
    assert any(eid == "brand:Y" for _slug, _key, eid in violations)


# ---------------------------------------------------------------------------
# Test 7 — non_ci_styles list also gated.
# ---------------------------------------------------------------------------
def test_non_ci_styles_also_gated(tmp_path):
    repo = _git_init(tmp_path)
    _write_meta(repo, "t1", brand_overrides=[], extra={"non_ci_styles": ["weird"]})
    _commit(repo, "base")
    base = _branch_base(repo)
    _write_meta(
        repo,
        "t1",
        brand_overrides=[],
        extra={"non_ci_styles": ["weird", "weirder"]},
    )
    _commit(repo, "add weirder")

    violations = cog.check_growth(base, repo)
    assert any(
        key == "non_ci_styles" and eid == "weirder"
        for _slug, key, eid in violations
    )


# ---------------------------------------------------------------------------
# Test 8 — CLI invocation respects --base-ref and exits 0 on clean state.
# ---------------------------------------------------------------------------
def test_cli_clean_state_exits_zero(tmp_path):
    repo = _git_init(tmp_path)
    _write_meta(repo, "t1", brand_overrides=[{"id": "brand:X", "reason": "..."}])
    _commit(repo, "base")
    # No HEAD-vs-HEAD changes => clean.
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "check_overrides_growth.py"),
            "--base-ref",
            "HEAD",
            "--repo-root",
            str(repo),
        ],
        capture_output=True,
        cwd=repo,
    )
    assert result.returncode == 0


def test_cli_dirty_state_exits_one(tmp_path):
    repo = _git_init(tmp_path)
    _write_meta(repo, "t1", brand_overrides=[{"id": "brand:X", "reason": "..."}])
    _commit(repo, "base")
    base = _branch_base(repo)
    _write_meta(
        repo,
        "t1",
        brand_overrides=[
            {"id": "brand:X", "reason": "..."},
            {"id": "brand:Y", "reason": "..."},
        ],
    )
    _commit(repo, "add Y")
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "check_overrides_growth.py"),
            "--base-ref",
            base,
            "--repo-root",
            str(repo),
        ],
        capture_output=True,
        cwd=repo,
    )
    assert result.returncode == 1
    assert b"brand:Y" in result.stderr
