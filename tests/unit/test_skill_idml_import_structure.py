"""Unit tests for .claude/skills/idml-{import,scaffold,tune}/ structure.

Issue #38 introduced the idml-import skill; issue #40 split it into
idml-scaffold (Stage 1) + idml-tune (Stage 2). The old idml-import
SKILL.md is now a redirect stub but the directory and sub-docs stay
for back-compat. These tests validate both layouts.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
IMPORT_DIR = ROOT / ".claude" / "skills" / "idml-import"
SCAFFOLD_DIR = ROOT / ".claude" / "skills" / "idml-scaffold"
TUNE_DIR = ROOT / ".claude" / "skills" / "idml-tune"


def _parse_frontmatter(text: str) -> dict | None:
    """Parse YAML frontmatter delimited by '---' lines."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return None
    block = "\n".join(lines[1:end])
    return yaml.safe_load(block)


# ---------------------------------------------------------------------------
# Test 1 — every skill SKILL.md exists with parseable frontmatter.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "skill_dir,expected_name",
    [
        (IMPORT_DIR, "idml-import"),
        (SCAFFOLD_DIR, "idml-scaffold"),
        (TUNE_DIR, "idml-tune"),
    ],
)
def test_skill_md_frontmatter(skill_dir, expected_name):
    skill = skill_dir / "SKILL.md"
    assert skill.exists(), f"missing {skill}"
    fm = _parse_frontmatter(skill.read_text(encoding="utf-8"))
    assert fm is not None, f"{skill} frontmatter is missing or unparseable"
    assert fm.get("name") == expected_name
    assert isinstance(fm.get("description"), str) and fm["description"]


# ---------------------------------------------------------------------------
# Test 2 — back-compat sub-docs remain in idml-import/ after split.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "fname",
    [
        "classification.md",
        "pattern_library.md",
        "tolerance_protocol.md",
        "inject_protocol.md",
        "asset_policy.md",
    ],
)
def test_legacy_disclosure_file_exists(fname):
    assert (IMPORT_DIR / fname).exists(), (
        f"missing .claude/skills/idml-import/{fname} "
        f"(kept for back-compat per issue #40 Task 14)"
    )


# ---------------------------------------------------------------------------
# Test 3 — sub-docs redistributed into scaffold + tune.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "fname",
    [
        "classification.md",
        "pattern_library.md",
        "asset_policy.md",
    ],
)
def test_scaffold_subdoc_exists(fname):
    assert (SCAFFOLD_DIR / fname).exists(), (
        f"missing .claude/skills/idml-scaffold/{fname}"
    )


@pytest.mark.parametrize(
    "fname",
    [
        "inject_protocol.md",
        "tolerance_protocol.md",
        "forbidden_paths.md",
    ],
)
def test_tune_subdoc_exists(fname):
    assert (TUNE_DIR / fname).exists(), (
        f"missing .claude/skills/idml-tune/{fname}"
    )


# ---------------------------------------------------------------------------
# Test 4 — idml-scaffold/SKILL.md mentions the P1-P11 SOP commitments.
# ---------------------------------------------------------------------------
def test_scaffold_skill_md_references_sop_commitments():
    text = (SCAFFOLD_DIR / "SKILL.md").read_text(encoding="utf-8")
    for token in ("P1.", "P5.", "P10."):
        assert token in text, f"idml-scaffold/SKILL.md missing SOP marker {token}"


# ---------------------------------------------------------------------------
# Test 5 — idml-tune/SKILL.md references the inventory gate.
# ---------------------------------------------------------------------------
def test_tune_skill_md_references_inventory_gate():
    text = (TUNE_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "inventory_compare.py" in text
    assert "inventory_extract.py" in text
    assert "HARD precondition" in text


# ---------------------------------------------------------------------------
# Test 6 — idml-scaffold/SKILL.md mentions banned phrases.
# ---------------------------------------------------------------------------
def test_scaffold_banned_phrases_section_exists():
    text = (SCAFFOLD_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "Banned phrases" in text or "banned phrases" in text.lower()


# ---------------------------------------------------------------------------
# Test 7 — idml-import/SKILL.md is a redirect stub (<60 lines).
# ---------------------------------------------------------------------------
def test_idml_import_skill_is_redirect_stub():
    text = (IMPORT_DIR / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) < 60, (
        f"idml-import SKILL.md has {len(lines)} lines; "
        f"should be a redirect stub (<60) per issue #40 Task 14"
    )
    assert "idml-scaffold" in text
    assert "idml-tune" in text


# ---------------------------------------------------------------------------
# Test 8 — every SKILL.md is within 500 LOC.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("skill_dir", [IMPORT_DIR, SCAFFOLD_DIR, TUNE_DIR])
def test_skill_md_within_500_lines(skill_dir):
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) <= 500, f"{skill_dir/'SKILL.md'} has {len(lines)} lines (>500)"


# ---------------------------------------------------------------------------
# Test 9 — sop_lint passes on the new skill files.
# ---------------------------------------------------------------------------
def test_sop_lint_passes_on_skill_files():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "sop_lint.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, (
        f"sop_lint failed; stderr:\n{result.stderr}"
    )
