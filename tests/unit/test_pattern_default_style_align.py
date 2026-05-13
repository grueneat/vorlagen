"""Unit tests for default_style_align_inheritance pattern (Backport 11)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from idml_to_dsl_patterns.default_style_align_inheritance import (  # noqa: E402
    DefaultStyleAlignInheritance,
    resolve_paragraph_align,
)


# ---------------------------------------------------------------------------
# Test 1 — PSR inline Justification wins.
# ---------------------------------------------------------------------------
def test_psr_inline_justification_wins():
    pat = DefaultStyleAlignInheritance()
    psr = etree.fromstring(
        '<ParagraphStyleRange Justification="CenterAlign" AppliedParagraphStyle="ps1"/>'.encode()
    )
    context = {"paragraph_styles": {"ps1": {"justification": "LeftAlign"}}}
    kwargs: dict = {}
    pat.apply(kwargs, psr, context=context)
    assert kwargs["paragraph_attrs"]["ALIGN"] == "1"  # center


# ---------------------------------------------------------------------------
# Test 2 — fallback to AppliedParagraphStyle when no PSR Justification.
# ---------------------------------------------------------------------------
def test_fallback_to_applied_paragraph_style():
    pat = DefaultStyleAlignInheritance()
    psr = etree.fromstring(
        '<ParagraphStyleRange AppliedParagraphStyle="ps1"/>'.encode()
    )
    context = {"paragraph_styles": {"ps1": {"justification": "RightAlign"}}}
    kwargs: dict = {}
    pat.apply(kwargs, psr, context=context)
    assert kwargs["paragraph_attrs"]["ALIGN"] == "2"  # right


# ---------------------------------------------------------------------------
# Test 3 — LeftAlign emitted explicitly (Backport 11's fix).
# ---------------------------------------------------------------------------
def test_left_align_emitted_explicitly():
    pat = DefaultStyleAlignInheritance()
    psr = etree.fromstring(
        '<ParagraphStyleRange Justification="LeftAlign"/>'.encode()
    )
    kwargs: dict = {}
    pat.apply(kwargs, psr)
    assert kwargs["paragraph_attrs"]["ALIGN"] == "0"


# ---------------------------------------------------------------------------
# Test 4 — no Justification + no AppliedParagraphStyle => apply is noop.
# ---------------------------------------------------------------------------
def test_no_justification_no_paragraph_style_noop():
    pat = DefaultStyleAlignInheritance()
    psr = etree.fromstring('<ParagraphStyleRange/>'.encode())
    kwargs: dict = {}
    pat.apply(kwargs, psr)
    assert kwargs == {}


# ---------------------------------------------------------------------------
# Test 5 — depends_on contract.
# ---------------------------------------------------------------------------
def test_depends_on_justification_to_align():
    pat = DefaultStyleAlignInheritance()
    assert "justification_to_align" in pat.depends_on


# ---------------------------------------------------------------------------
# Test 6 — pattern metadata.
# ---------------------------------------------------------------------------
def test_pattern_metadata():
    pat = DefaultStyleAlignInheritance()
    assert pat.id == "default_style_align_inheritance"
    assert pat.applies_to == "TextFrame"
    assert "Backport 11" in pat.description


# ---------------------------------------------------------------------------
# Test 7 — resolve_paragraph_align helper handles None gracefully.
# ---------------------------------------------------------------------------
def test_resolve_paragraph_align_none_element():
    assert resolve_paragraph_align(None, paragraph_styles={}) is None


def test_resolve_paragraph_align_unknown_justification():
    psr = etree.fromstring('<ParagraphStyleRange Justification="ZorkAlign"/>'.encode())
    assert resolve_paragraph_align(psr, paragraph_styles=None) is None


# ---------------------------------------------------------------------------
# Test 8 — registered in PATTERNS after JustificationToAlign.
# ---------------------------------------------------------------------------
def test_pattern_registered_after_justification():
    from idml_to_dsl_patterns import PATTERNS
    ids = [p.id for p in PATTERNS]
    assert "default_style_align_inheritance" in ids
    j_idx = ids.index("justification_to_align")
    d_idx = ids.index("default_style_align_inheritance")
    assert d_idx > j_idx, "DefaultStyleAlignInheritance must register after JustificationToAlign"
