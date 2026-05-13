"""Unit tests for .claude/skills/idml-import/ structure (Task 15, issue #38)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / ".claude" / "skills" / "idml-import"


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
# Test 1 — SKILL.md exists.
# ---------------------------------------------------------------------------
def test_skill_md_exists():
    skill = SKILL_DIR / "SKILL.md"
    assert skill.exists(), f"missing {skill}"


# ---------------------------------------------------------------------------
# Test 2 — SKILL.md has parseable YAML frontmatter with required keys.
# ---------------------------------------------------------------------------
def test_frontmatter_has_required_keys():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert fm is not None, "frontmatter is missing or unparseable"
    assert fm.get("name") == "idml-import"
    assert isinstance(fm.get("description"), str) and fm["description"]


# ---------------------------------------------------------------------------
# Test 3 — four progressive-disclosure files exist.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "fname",
    [
        "classification.md",
        "pattern_library.md",
        "tolerance_protocol.md",
        "inject_protocol.md",
    ],
)
def test_disclosure_file_exists(fname):
    assert (SKILL_DIR / fname).exists(), f"missing .claude/skills/idml-import/{fname}"


# ---------------------------------------------------------------------------
# Test 4 — SKILL.md mentions the P1-P10 SOP.
# ---------------------------------------------------------------------------
def test_skill_md_references_sop_commitments():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for token in ("P1.", "P5.", "P10."):
        assert token in text, f"SKILL.md missing SOP marker {token}"


# ---------------------------------------------------------------------------
# Test 5 — banned-phrases section exists.
# ---------------------------------------------------------------------------
def test_banned_phrases_section_exists():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "Banned phrases" in text or "banned phrases" in text.lower()
    # The skill lists the phrases as MENTIONS (not as a usage); the
    # sop_lint scope intentionally excludes .claude/ for this file —
    # wait, actually .claude/ IS in the lint scope. Verify the file
    # passes the lint by running it.


# ---------------------------------------------------------------------------
# Test 6 — SKILL.md is <= 500 LOC.
# ---------------------------------------------------------------------------
def test_skill_md_within_500_lines():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) <= 500, f"SKILL.md has {len(lines)} lines (>500)"


# ---------------------------------------------------------------------------
# Test 7 — sop_lint passes on the new skill files.
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
