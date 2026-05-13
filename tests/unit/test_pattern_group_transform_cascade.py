"""Unit tests for group_transform_cascade pattern."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from idml_to_dsl_patterns.group_transform_cascade import (  # noqa: E402
    GroupTransformCascade,
)


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

_IDENTITY = "1 0 0 1 0 0"


def _payload(**overrides) -> dict:
    base = {
        "item_transform": _IDENTITY,
        "anchors": [(0.0, 0.0), (100.0, 100.0)],
        "ancestor_transforms": [],
        "spread_item_transform": _IDENTITY,
        "page_item_transform": _IDENTITY,
        "page_geometric_bounds": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test 1 — matches() True when ancestor_transforms present.
# ---------------------------------------------------------------------------
def test_matches_with_ancestor_transforms():
    pat = GroupTransformCascade()
    assert pat.matches(_payload(ancestor_transforms=[_IDENTITY])) is True


def test_matches_false_without_ancestors():
    pat = GroupTransformCascade()
    assert pat.matches(_payload()) is False


# ---------------------------------------------------------------------------
# Test 2 — identity transform cascade => x=0, y=0.
# ---------------------------------------------------------------------------
def test_identity_cascade_produces_zero_origin():
    pat = GroupTransformCascade()
    payload = _payload(ancestor_transforms=[_IDENTITY])
    kwargs: dict = {}
    pat.apply(kwargs, payload)
    # Identity cascade leaves the anchors untouched relative to spread origin.
    assert kwargs["x_pt"] == pytest.approx(0.0, abs=1e-3)
    assert kwargs["y_pt"] == pytest.approx(0.0, abs=1e-3)
    assert kwargs["w_pt"] == pytest.approx(100.0, abs=1e-3)
    assert kwargs["h_pt"] == pytest.approx(100.0, abs=1e-3)


# ---------------------------------------------------------------------------
# Test 3 — translation cascade shifts the origin.
# ---------------------------------------------------------------------------
def test_translation_cascade_shifts_origin():
    pat = GroupTransformCascade()
    # Outer Group translates by (50, 30).
    payload = _payload(ancestor_transforms=["1 0 0 1 50 30"])
    kwargs: dict = {}
    pat.apply(kwargs, payload)
    assert kwargs["x_pt"] == pytest.approx(50.0, abs=1e-3)
    assert kwargs["y_pt"] == pytest.approx(30.0, abs=1e-3)


# ---------------------------------------------------------------------------
# Test 4 — pattern metadata.
# ---------------------------------------------------------------------------
def test_pattern_metadata():
    pat = GroupTransformCascade()
    assert pat.id == "group_transform_cascade"
    assert pat.applies_to == "Group"


# ---------------------------------------------------------------------------
# Test 5 — missing required keys => noop.
# ---------------------------------------------------------------------------
def test_missing_required_keys_noop():
    pat = GroupTransformCascade()
    kwargs: dict = {}
    pat.apply(kwargs, {"ancestor_transforms": ["1 0 0 1 0 0"]})
    assert kwargs == {}


# ---------------------------------------------------------------------------
# Test 6 — non-dict argument => noop.
# ---------------------------------------------------------------------------
def test_non_dict_arg_noop():
    pat = GroupTransformCascade()
    kwargs: dict = {}
    pat.apply(kwargs, "not a dict")
    assert kwargs == {}


# ---------------------------------------------------------------------------
# Test 7 — registered.
# ---------------------------------------------------------------------------
def test_registered():
    from idml_to_dsl_patterns import pattern_by_id
    assert pattern_by_id("group_transform_cascade") is not None
