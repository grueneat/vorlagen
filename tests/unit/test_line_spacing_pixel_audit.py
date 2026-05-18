"""Unit tests for tools/line_spacing_pixel_audit.py.

Covers the split mixed-font headline support added to close the headline
split mis-calibration blind spot:

1. parse_textframes_from_build_py captures Run fill colors + text.
2. detect_split_headline_groups groups <base>/<base>_lN frames.
3. _color_match — brand-fill colour classification (white / yellow strict).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from line_spacing_pixel_audit import (  # noqa: E402
    FrameInfo,
    detect_split_headline_groups,
    parse_textframes_from_build_py,
    _color_match,
    SPLIT_HEADLINE_TOL_PT,
)


# ---------------------------------------------------------------------------
# detect_split_headline_groups


def _fi(anname: str, page: int = 0) -> FrameInfo:
    return FrameInfo(anname=anname, page=page, bbox_mm=(0, 0, 10, 10))


def test_detect_split_headline_three_line_group():
    """A base frame plus _l2/_l3 siblings forms one 3-line group."""
    frames = {an: _fi(an) for an in ("u1175", "u1175_l2", "u1175_l3", "ux")}
    groups = detect_split_headline_groups(frames)
    assert ["u1175", "u1175_l2", "u1175_l3"] in groups
    # The lone frame ux is not a group.
    assert all("ux" not in g for g in groups)


def test_detect_split_headline_two_line_group():
    frames = {an: _fi(an) for an in ("u1214", "u1214_l2")}
    groups = detect_split_headline_groups(frames)
    assert groups == [["u1214", "u1214_l2"]]


def test_detect_split_headline_ordering_is_by_line_index():
    """Members are returned line-1 first regardless of dict insertion order."""
    frames = {
        "u1175_l3": _fi("u1175_l3"),
        "u1175": _fi("u1175"),
        "u1175_l2": _fi("u1175_l2"),
    }
    groups = detect_split_headline_groups(frames)
    assert groups == [["u1175", "u1175_l2", "u1175_l3"]]


def test_detect_split_headline_ignores_lone_base():
    """A base frame with no _lN siblings is an ordinary headline, not a
    split group."""
    frames = {"u1175": _fi("u1175")}
    assert detect_split_headline_groups(frames) == []


def test_detect_split_headline_l_suffix_not_a_group():
    """A frame literally named '..._l' or '..._lx' (non-numeric) is not a
    split member — only '_l<N>' with N>=2 counts."""
    frames = {"foo": _fi("foo"), "foo_lx": _fi("foo_lx")}
    groups = detect_split_headline_groups(frames)
    # foo_lx has no numeric suffix, so foo and foo_lx are separate bases,
    # each lone → no group.
    assert groups == []


# ---------------------------------------------------------------------------
# parse_textframes_from_build_py — fill color + text capture


def test_parse_textframes_captures_run_fill_and_text(tmp_path):
    build_py = tmp_path / "build.py"
    build_py.write_text(
        "def build(doc, page0):\n"
        "    page0.add(TextFrame(\n"
        "        x_mm=6.3, y_mm=90.1, w_mm=83.0, h_mm=24.2,\n"
        "        anname='u1175_l2',\n"
        "        runs=[Run(text='dreizeilige', font='Vollkorn Black Italic',\n"
        "                  fontsize=38, fcolor='Gelb')],\n"
        "    ))\n",
        encoding="utf-8",
    )
    frames = parse_textframes_from_build_py(build_py)
    assert "u1175_l2" in frames
    fi = frames["u1175_l2"]
    assert fi.fill_colors == ("Gelb",)
    assert fi.text == "dreizeilige"


def test_parse_textframes_handles_frame_without_runs(tmp_path):
    build_py = tmp_path / "build.py"
    build_py.write_text(
        "def build(doc, page0):\n"
        "    page0.add(TextFrame(\n"
        "        x_mm=1, y_mm=2, w_mm=3, h_mm=4, anname='empty', text=''))\n",
        encoding="utf-8",
    )
    frames = parse_textframes_from_build_py(build_py)
    assert frames["empty"].fill_colors == ()
    assert frames["empty"].text == ""


# ---------------------------------------------------------------------------
# _color_match — strict brand-fill classification


def test_color_match_white_is_strict():
    """Pure white matches; a gray photo highlight does NOT — otherwise the
    headline ink-top would be polluted by jacket highlights."""
    assert _color_match(255, 255, 255, "White")
    assert _color_match(240, 242, 238, "White")
    # Mid-gray jacket highlight — must be rejected.
    assert not _color_match(200, 205, 198, "White")
    assert not _color_match(180, 180, 180, "White")


def test_color_match_yellow_rejects_green():
    """Saturated yellow matches; a green photo background does not."""
    assert _color_match(255, 242, 0, "Gelb")
    assert _color_match(230, 210, 60, "Gelb")
    # Brand green — must be rejected.
    assert not _color_match(0, 95, 53, "Gelb")
    assert not _color_match(79, 175, 50, "Gelb")


def test_split_headline_tolerance_is_tight():
    """The split-headline gate must use a sub-2pt bar so a 5-8pt mis-spacing
    cannot pass."""
    assert SPLIT_HEADLINE_TOL_PT <= 2.0
