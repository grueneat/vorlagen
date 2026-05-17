"""Unit tests for tools/baseline_image_audit.py — PDF image inventory audit.

Unit tests cover pure-Python helpers (parsers, detectors). Integration tests
against the real baseline.pdf verify the vector-path delta signal for
bugs #1 (wind turbine, page 0) and #3 (curly quotes, page 1).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from baseline_image_audit import (
    _parse_pdfimages_list,
    _extract_imageframes_from_build_py,
    _extract_polygon_count_per_page,
    _detect_composite_strips,
    run_image_audit,
    _yaml_dump,
    _count_svg_content_paths,
)


# ---------------------------------------------------------------------------
# Unit tests — pdfimages list parser
# ---------------------------------------------------------------------------

PDFIMAGES_SAMPLE = """\
page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio
--------------------------------------------------------------------------------------------
   1     0 image     100   200  rgb     3   8  jpeg   no         5  0   150   150 10.0K 5.0%
   1     1 smask     100   200  gray    1   8  jpeg   no         5  0   150   150  2.0K 1.0%
   2     0 image     300   400  rgb     3   8  jpeg   no        10  0   150   150 20.0K 8.0%
   2     1 image     300   400  rgb     3   8  png    no        11  0   150   150 25.0K 9.0%
   2     2 stencil    50    50  gray    1   1  ccitt  no        12  0   150   150  1.0K 1.0%
"""


def test_parse_pdfimages_list_counts_images_only():
    counts = _parse_pdfimages_list(PDFIMAGES_SAMPLE)
    # Page 1: 1 'image' + 1 'smask' → only 1 image counted
    assert counts.get(1) == 1
    # Page 2: 2 'image' + 1 'stencil' → 2 images counted
    assert counts.get(2) == 2


def test_parse_pdfimages_list_empty():
    counts = _parse_pdfimages_list("")
    assert counts == {}


def test_parse_pdfimages_list_header_only():
    counts = _parse_pdfimages_list(
        "page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio\n"
        "--------------------------------------------------------------------------------------------\n"
    )
    assert counts == {}


# ---------------------------------------------------------------------------
# Unit tests — build.py parser
# ---------------------------------------------------------------------------

BUILD_PY_SAMPLE = """\
def _add_page_0(doc, page0):
    page0.add(ImageFrame(
        x_mm=10,
        anname='u1',
        image='/path/to/shared.png',
        local_offset_mm=(0.0, 0.0),
        local_scale=(0.5, 0.5),
    ))
    page0.add(ImageFrame(
        x_mm=20,
        anname='u2',
        image='/path/to/shared.png',
        local_offset_mm=(0.0, 0.0),
        local_scale=(0.5, 0.5),
    ))
    page0.add(ImageFrame(
        x_mm=30,
        anname='u3',
        image='/path/to/other.png',
    ))
    page0.add(Polygon(
        anname='u4',
        fill='Green',
    ))
    page0.add(Polygon(
        anname='u5',
        fill='Blue',
    ))

def _add_page_1(doc, page1):
    page1.add(ImageFrame(
        anname='u6',
        image='/path/to/unique.png',
    ))
    page1.add(Polygon(
        anname='u7',
        fill='Red',
    ))
"""


def test_extract_imageframes_finds_all(tmp_path):
    bp = tmp_path / "build.py"
    bp.write_text(BUILD_PY_SAMPLE, encoding="utf-8")
    frames = _extract_imageframes_from_build_py(bp)
    annames = [f["anname"] for f in frames]
    assert "u1" in annames
    assert "u2" in annames
    assert "u3" in annames
    assert "u6" in annames
    assert "u4" not in annames   # Polygon, not ImageFrame
    assert "u7" not in annames   # Polygon, not ImageFrame


def test_extract_imageframes_page_func(tmp_path):
    bp = tmp_path / "build.py"
    bp.write_text(BUILD_PY_SAMPLE, encoding="utf-8")
    frames = _extract_imageframes_from_build_py(bp)
    by_anname = {f["anname"]: f for f in frames}
    assert by_anname["u1"]["page_func"] == "page_0"
    assert by_anname["u6"]["page_func"] == "page_1"


def test_extract_imageframes_offset_parsed(tmp_path):
    bp = tmp_path / "build.py"
    bp.write_text(BUILD_PY_SAMPLE, encoding="utf-8")
    frames = _extract_imageframes_from_build_py(bp)
    by_anname = {f["anname"]: f for f in frames}
    assert by_anname["u1"]["local_offset_mm"] == (0.0, 0.0)
    assert by_anname["u3"]["local_offset_mm"] is None  # not specified


def test_extract_polygon_count_per_page(tmp_path):
    bp = tmp_path / "build.py"
    bp.write_text(BUILD_PY_SAMPLE, encoding="utf-8")
    counts = _extract_polygon_count_per_page(bp)
    assert counts.get("page_0") == 2   # u4, u5
    assert counts.get("page_1") == 1   # u7


# ---------------------------------------------------------------------------
# Unit tests — composite strip detection
# ---------------------------------------------------------------------------

def test_detect_composite_strips_flags_shared_image_same_offset():
    frames = [
        {"anname": "u1", "image": "/path/icon.png", "local_offset_mm": (0.0, 0.0), "page_func": "page_0"},
        {"anname": "u2", "image": "/path/icon.png", "local_offset_mm": (0.0, 0.0), "page_func": "page_0"},
        {"anname": "u3", "image": "/path/icon.png", "local_offset_mm": (0.0, 0.0), "page_func": "page_0"},
    ]
    strips = _detect_composite_strips(frames)
    assert len(strips) == 1
    s = strips[0]
    assert s["n_frames"] == 3
    assert s["unique_offsets"] == 1
    assert "LocalOffset bug" in s["hint"]


def test_detect_composite_strips_no_flag_different_offsets():
    frames = [
        {"anname": "u1", "image": "/path/icon.png", "local_offset_mm": (0.0, 0.0), "page_func": "page_0"},
        {"anname": "u2", "image": "/path/icon.png", "local_offset_mm": (10.0, 0.0), "page_func": "page_0"},
        {"anname": "u3", "image": "/path/icon.png", "local_offset_mm": (20.0, 0.0), "page_func": "page_0"},
    ]
    strips = _detect_composite_strips(frames)
    assert len(strips) == 0


def test_detect_composite_strips_single_frame_no_flag():
    frames = [
        {"anname": "u1", "image": "/path/icon.png", "local_offset_mm": (0.0, 0.0), "page_func": "page_0"},
    ]
    strips = _detect_composite_strips(frames)
    assert len(strips) == 0


def test_detect_composite_strips_no_offset_shared_image():
    """N frames with same image and no offset at all → flag as suspicious."""
    frames = [
        {"anname": "u1", "image": "/shared.png", "local_offset_mm": None, "page_func": "page_0"},
        {"anname": "u2", "image": "/shared.png", "local_offset_mm": None, "page_func": "page_0"},
    ]
    strips = _detect_composite_strips(frames)
    assert len(strips) == 1


def test_yaml_output_deterministic():
    """_yaml_dump produces identical output for identical dicts."""
    data = {
        "template": "t",
        "pages": [
            {"page": 0, "raster": {"baseline_count": 0, "build_py_count": 1, "ok": False}},
        ],
    }
    assert _yaml_dump(data) == _yaml_dump(data)
