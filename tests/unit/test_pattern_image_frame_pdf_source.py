"""Unit tests for image_frame_pdf_source_for_vectors pattern."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from idml_to_dsl_patterns.image_frame_pdf_source_for_vectors import (  # noqa: E402
    ImageFramePdfSourceForVectors,
)


# ---------------------------------------------------------------------------
# Test 1 — .ai link with manifest vector_output => image=<pdf path>.
# ---------------------------------------------------------------------------
def test_ai_with_vector_output_sets_image_to_pdf():
    pat = ImageFramePdfSourceForVectors()
    link = etree.fromstring(
        '<Link LinkResourceURI="file:Links/logo.ai"/>'.encode()
    )
    context = {
        "links_manifest": {
            "logo.ai": {
                "output": "shared/assets/x/logo.png",
                "kind": "vector_ai",
                "recipe": "pdftocairo",
                "vector_output": "shared/assets/x/logo.pdf",
            }
        }
    }
    kwargs: dict = {}
    pat.apply(kwargs, link, context=context)
    assert kwargs["image"] == "shared/assets/x/logo.pdf"


# ---------------------------------------------------------------------------
# Test 2 — manifest without vector_output => no image mutation, no TODO.
# ---------------------------------------------------------------------------
def test_ai_without_vector_output_leaves_image_unchanged():
    pat = ImageFramePdfSourceForVectors()
    link = etree.fromstring('<Link LinkResourceURI="file:Links/logo.ai"/>'.encode())
    context = {
        "links_manifest": {
            "logo.ai": {
                "output": "shared/assets/x/logo.png",
                "kind": "vector_ai",
                "recipe": "",
            }
        }
    }
    kwargs: dict = {}
    pat.apply(kwargs, link, context=context)
    assert "image" not in kwargs


# ---------------------------------------------------------------------------
# Test 3 — .png link => matches() False, no mutation.
# ---------------------------------------------------------------------------
def test_png_link_does_not_match():
    pat = ImageFramePdfSourceForVectors()
    link = etree.fromstring('<Link LinkResourceURI="file:Links/photo.png"/>'.encode())
    assert pat.matches(link) is False
    kwargs: dict = {}
    pat.apply(kwargs, link, context={"links_manifest": {}})
    assert kwargs == {}


# ---------------------------------------------------------------------------
# Test 4 — missing context emits TODO marker.
# ---------------------------------------------------------------------------
def test_missing_context_emits_todo():
    pat = ImageFramePdfSourceForVectors()
    link = etree.fromstring('<Link LinkResourceURI="file:Links/logo.ai"/>'.encode())
    kwargs: dict = {}
    pat.apply(kwargs, link, context=None)
    assert "_todo" in kwargs


# ---------------------------------------------------------------------------
# Test 5 — pattern metadata.
# ---------------------------------------------------------------------------
def test_pattern_metadata():
    pat = ImageFramePdfSourceForVectors()
    assert pat.id == "image_frame_pdf_source_for_vectors"
    assert pat.applies_to == "ImageFrame"


# ---------------------------------------------------------------------------
# Test 6 — registered in PATTERNS.
# ---------------------------------------------------------------------------
def test_registered():
    from idml_to_dsl_patterns import pattern_by_id
    assert pattern_by_id("image_frame_pdf_source_for_vectors") is not None
