"""Unit tests for tools/squiggle_alignment_audit.py.

The hardened audit is a GROUND-TRUTH check: it pixel-scans the rendered
preview for the squiggle's actual yellow ink and independently verifies a
rendered word sits in the squiggle's vertical band. These tests exercise the
geometry helpers (`_carried_word`, `_polyline_box_mm`, `_is_yellow`) and the
`_scan_squiggle_ink` pixel scan against a synthetic image — no real render
needed — plus the no-anchors contract path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import squiggle_alignment_audit as audit  # noqa: E402

PT_PER_MM = 72.0 / 25.4


# ---------------------------------------------------------------------------
# _is_yellow — Gelb swatch detection
# ---------------------------------------------------------------------------

def test_is_yellow_accepts_gelb_swatch() -> None:
    # Pure Gelb (CMYK Y=100 -> RGB 255,255,0) and anti-alias fringe.
    assert audit._is_yellow(255, 255, 0)
    assert audit._is_yellow(230, 210, 80)


def test_is_yellow_rejects_green_and_white() -> None:
    # Grüne page background green, white headline text, black body text.
    assert not audit._is_yellow(20, 120, 60)
    assert not audit._is_yellow(255, 255, 255)
    assert not audit._is_yellow(0, 0, 0)


# ---------------------------------------------------------------------------
# _polyline_box_mm — squiggle box parsed from build.py
# ---------------------------------------------------------------------------

_BUILD_PY = """\
from sla_lib import PolyLine, TextFrame

def build():
    page1.add(PolyLine(
        x_mm=14.7994,
        y_mm=87.7776,
        w_mm=19.1982,
        h_mm=0.9961,
        sla_path='M0 0 L1 1 Z',
        line_color='None',
        anname='u11e3',
        fill='Gelb',
    ))
    page1.add(TextFrame(
        x_mm=15.0,
        y_mm=42.0,
        w_mm=75.0,
        h_mm=97.3,
        anname='u1242',
    ))
"""


def test_polyline_box_mm_reads_squiggle() -> None:
    box = audit._polyline_box_mm(_BUILD_PY, "u11e3")
    assert box == (14.7994, 87.7776, 19.1982, 0.9961)


def test_polyline_box_mm_missing_returns_none() -> None:
    assert audit._polyline_box_mm(_BUILD_PY, "u9999") is None


# ---------------------------------------------------------------------------
# _carried_word — does a rendered word sit in the squiggle ink's band?
# ---------------------------------------------------------------------------

def _word(text: str, x0_mm: float, top_mm: float, x1_mm: float,
          bottom_mm: float) -> dict:
    """A pdfplumber-style word dict; inputs in mm, stored in pt."""
    return {
        "text": text,
        "x0": x0_mm * PT_PER_MM,
        "x1": x1_mm * PT_PER_MM,
        "top": top_mm * PT_PER_MM,
        "bottom": bottom_mm * PT_PER_MM,
    }


def test_carried_word_underline_tucked_against_baseline() -> None:
    """An underline squiggle sits just below the word — vgap is ~0."""
    words = [_word("Lia", 15.0, 84.3, 19.9, 88.2),
             _word("vellam,", 22.5, 84.3, 34.2, 88.2)]
    # Squiggle ink underlines both words: x 14.9-33.8, y 87.8-88.6.
    carried = audit._carried_word(words, (14.9, 87.8, 33.8, 88.6))
    assert carried is not None
    text, hoverlap, vgap = carried
    # Picks the strongest horizontal overlap; ink overlaps the word band.
    assert text in ("Lia", "vellam,")
    assert hoverlap > 1.0
    assert vgap == pytest.approx(0.0, abs=0.01)


def test_carried_word_circle_overlaps_word_box() -> None:
    """A circle squiggle's ink span overlaps the word box -> vgap 0."""
    words = [_word("in", 82.2, 43.9, 85.2, 47.8),
             _word("et", 86.6, 43.9, 89.9, 47.8)]
    carried = audit._carried_word(words, (80.8, 43.7, 92.3, 47.4))
    assert carried is not None
    _, hoverlap, vgap = carried
    assert hoverlap > 1.0
    assert vgap == pytest.approx(0.0, abs=0.01)


def test_carried_word_floating_squiggle_large_vgap() -> None:
    """A squiggle far below every word reports a large vertical gap."""
    words = [_word("headline", 15.0, 20.0, 60.0, 28.0)]
    # Ink at y 130-131 — 102mm below the only word.
    carried = audit._carried_word(words, (15.0, 130.0, 35.0, 131.0))
    assert carried is not None
    _, _, vgap = carried
    assert vgap > audit.MAX_VGAP_MM


def test_carried_word_no_horizontal_overlap_returns_none() -> None:
    """A squiggle with no horizontally-overlapping word -> None."""
    words = [_word("headline", 80.0, 20.0, 120.0, 28.0)]
    # Ink at x 15-35 — no horizontal overlap with the x 80-120 word.
    assert audit._carried_word(words, (15.0, 25.0, 35.0, 26.0)) is None


# ---------------------------------------------------------------------------
# _scan_squiggle_ink — pixel scan for the rendered yellow ink
# ---------------------------------------------------------------------------

def _yellow_strip_image(dpi: int):
    """A small RGB image: green field with a horizontal yellow ink strip."""
    Image = pytest.importorskip("PIL.Image")
    mm_px = dpi / 25.4
    w = int(60 * mm_px)
    h = int(60 * mm_px)
    img = Image.new("RGB", (w, h), (20, 120, 60))  # Grüne green
    px = img.load()
    # Yellow strip: x 15-35mm, y 30-31mm.
    for yy in range(int(30 * mm_px), int(31 * mm_px)):
        for xx in range(int(15 * mm_px), int(35 * mm_px)):
            px[xx, yy] = (255, 255, 0)
    return img


def test_scan_squiggle_ink_finds_rendered_strip() -> None:
    dpi = audit.SCAN_DPI
    img = _yellow_strip_image(dpi)
    # build.py places the squiggle box right over the strip.
    ink = audit._scan_squiggle_ink(img, (15.0, 30.0, 20.0, 1.0), dpi)
    assert ink is not None
    x0, y0, x1, y1 = ink
    assert x0 == pytest.approx(15.0, abs=0.3)
    assert x1 == pytest.approx(35.0, abs=0.3)
    assert y0 == pytest.approx(30.0, abs=0.3)


def test_scan_squiggle_ink_none_when_no_ink_near_box() -> None:
    """When the squiggle box is over empty (green) space -> no ink found."""
    dpi = audit.SCAN_DPI
    img = _yellow_strip_image(dpi)
    # Box far from the yellow strip (strip is at y 30; box at y 50).
    ink = audit._scan_squiggle_ink(img, (15.0, 50.0, 20.0, 1.0), dpi)
    assert ink is None


# ---------------------------------------------------------------------------
# run_squiggle_alignment_audit — preflight contract
# ---------------------------------------------------------------------------

def test_audit_no_anchors_file_is_ok(tmp_path: Path) -> None:
    """A template without squiggle_anchors.yml passes vacuously."""
    (tmp_path / "templates" / "demo").mkdir(parents=True)
    report = audit.run_squiggle_alignment_audit("demo", repo=tmp_path)
    assert report["ok"] is True
    assert report["issues"] == 0
    assert "ok" in report and "issues" in report and "detail" in report


def test_audit_missing_build_or_preview_skips(tmp_path: Path) -> None:
    """anchors present but build.py/preview.pdf absent -> skipped, ok."""
    tdir = tmp_path / "templates" / "demo"
    tdir.mkdir(parents=True)
    (tdir / "squiggle_anchors.yml").write_text(
        "anchors:\n- anname: u1\n  page: 0\n  word: x\n",
        encoding="utf-8",
    )
    report = audit.run_squiggle_alignment_audit("demo", repo=tmp_path)
    assert report["ok"] is True
    assert "skipped" in report["detail"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
