"""Unit tests for tools/idml_to_dsl_patterns scaffold (Task 9, issue #38)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from idml_to_dsl_patterns import PATTERNS, Pattern, pattern_by_id  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1 — PATTERNS is a list (possibly empty).
# ---------------------------------------------------------------------------
def test_patterns_is_a_list():
    assert isinstance(PATTERNS, list)


# ---------------------------------------------------------------------------
# Test 2 — every entry satisfies the Pattern protocol.
# ---------------------------------------------------------------------------
def test_each_entry_satisfies_protocol():
    for p in PATTERNS:
        assert hasattr(p, "id")
        assert isinstance(p.id, str) and p.id
        assert hasattr(p, "description")
        assert isinstance(p.description, str) and p.description
        assert hasattr(p, "applies_to")
        assert isinstance(p.applies_to, str) and p.applies_to
        assert hasattr(p, "matches") and callable(p.matches)
        assert hasattr(p, "apply") and callable(p.apply)


# ---------------------------------------------------------------------------
# Test 3 — pattern ids are unique.
# ---------------------------------------------------------------------------
def test_pattern_ids_unique():
    ids = [p.id for p in PATTERNS]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Test 4 — every registered pattern id is documented in INDEX.md.
# ---------------------------------------------------------------------------
def test_every_pattern_documented_in_index():
    index = (TOOLS / "idml_to_dsl_patterns" / "INDEX.md").read_text(encoding="utf-8")
    for p in PATTERNS:
        # The id must appear somewhere in the index (catalogue table row
        # or other reference). Substring match is intentional — the
        # catalogue may use the id verbatim or wrap it in backticks.
        assert p.id in index, f"pattern {p.id!r} not in INDEX.md"


# ---------------------------------------------------------------------------
# Test 5 — pattern_by_id helper round-trip.
# ---------------------------------------------------------------------------
def test_pattern_by_id_returns_match():
    for p in PATTERNS:
        assert pattern_by_id(p.id) is p


def test_pattern_by_id_returns_none_for_unknown():
    assert pattern_by_id("does_not_exist") is None


# ---------------------------------------------------------------------------
# Test 6 — base.py defines the Pattern Protocol.
# ---------------------------------------------------------------------------
def test_pattern_protocol_exists():
    from idml_to_dsl_patterns.base import Pattern as P
    assert P.__name__ == "Pattern"
