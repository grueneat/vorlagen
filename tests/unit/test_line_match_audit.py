"""Unit tests for tools/line_match_audit.py — Phase D8b strict per-line audit.

Covers:
1. _cluster_lines groups words into y-clustered, x-sorted lines.
2. _pair_lines LCS alignment isolates a single wrap difference (no cascade).
3. _check_line — strict first-word-x and baseline-y; minimal inter-word.
4. _drop_offpage removes words outside the page media box.
5. run_audit end-to-end with synthetic word records → ok / findings.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from line_match_audit import (  # noqa: E402
    _cluster_lines,
    _pair_lines,
    _check_line,
    _drop_offpage,
    _rotate_words_to_frame_space,
)


def _w(text: str, x0: float, top: float, width: float = 20.0,
       page: int = 0) -> dict:
    """Synthetic word record."""
    return {
        "page": page, "text": text,
        "x0_pt": x0, "y0_pt": top,
        "x1_pt": x0 + width, "y1_pt": top + 11.0,
    }


# ---------------------------------------------------------------------------
# _cluster_lines
# ---------------------------------------------------------------------------
def test_cluster_lines_groups_by_y_and_sorts_by_x():
    words = [
        _w("world", 60, 100), _w("Hello", 20, 100.5),  # same line (Δ0.5pt)
        _w("Second", 20, 130),
    ]
    lines = _cluster_lines(words)
    assert len(lines) == 2
    # line 1 sorted left-to-right despite input order
    assert [x["text"] for x in lines[0]] == ["Hello", "world"]
    assert [x["text"] for x in lines[1]] == ["Second"]


def test_cluster_lines_separates_far_y():
    words = [_w("A", 20, 100), _w("B", 20, 110)]  # 10pt apart > cluster tol
    assert len(_cluster_lines(words)) == 2


# ---------------------------------------------------------------------------
# _pair_lines — LCS alignment
# ---------------------------------------------------------------------------
def test_pair_lines_identical():
    base = [[_w("one", 20, 100)], [_w("two", 20, 114)]]
    prev = [[_w("one", 20, 100)], [_w("two", 20, 114)]]
    pairs = _pair_lines(base, prev)
    assert len(pairs) == 2
    assert all(b is not None and p is not None for b, p in pairs)


def test_pair_lines_single_wrap_difference_no_cascade():
    """One differently-wrapped line must NOT cascade into a frame-wide
    mismatch — the LCS keeps the surrounding identical lines aligned."""
    base = [
        [_w("Line", 20, 100)],
        [_w("alpha beta", 20, 114)],   # differs
        [_w("Tail", 20, 128)],
        [_w("End", 20, 142)],
    ]
    prev = [
        [_w("Line", 20, 100)],
        [_w("alpha", 20, 114)],        # differs (wrapped)
        [_w("Tail", 20, 128)],
        [_w("End", 20, 142)],
    ]
    pairs = _pair_lines(base, prev)
    # "Line", "Tail", "End" must each pair with their identical twin.
    matched = sum(
        1 for b, p in pairs
        if b and p and [w["text"] for w in b] == [w["text"] for w in p]
    )
    assert matched == 3


# ---------------------------------------------------------------------------
# _check_line — strict thresholds
# ---------------------------------------------------------------------------
def test_check_line_identical_passes():
    line = [_w("Hello", 20, 100), _w("world", 60, 100)]
    assert _check_line(line, line, 0, 1.0, 2.0) is None


def test_check_line_first_word_x_strict():
    base = [_w("Hello", 20, 100)]
    prev = [_w("Hello", 24, 100)]  # 4pt x drift > 1pt tol
    f = _check_line(base, prev, 0, 1.0, 2.0)
    assert f is not None and f["kind"] == "first_word_x"


def test_check_line_baseline_y_strict():
    base = [_w("Hello", 20, 100)]
    prev = [_w("Hello", 20, 104)]  # 4pt y drift > 1pt tol
    f = _check_line(base, prev, 0, 1.0, 2.0)
    assert f is not None and f["kind"] == "baseline_y"


def test_check_line_wrap_when_first_word_differs():
    base = [_w("Alpha", 20, 100)]
    prev = [_w("Beta", 20, 100)]
    f = _check_line(base, prev, 0, 1.0, 2.0)
    assert f is not None and f["kind"] == "wrap"


def test_check_line_inter_word_space_has_small_tolerance():
    # Same words, same first-word x/y, gap stretched 1.5pt → within 2pt tol.
    base = [_w("Hello", 20, 100, width=20), _w("world", 44, 100)]
    prev = [_w("Hello", 20, 100, width=20), _w("world", 45.5, 100)]
    assert _check_line(base, prev, 0, 1.0, 2.0) is None
    # Gap stretched 4pt → exceeds tol.
    prev_bad = [_w("Hello", 20, 100, width=20), _w("world", 48.5, 100)]
    f = _check_line(base, prev_bad, 0, 1.0, 2.0)
    assert f is not None and f["kind"] == "inter_word_space"


# ---------------------------------------------------------------------------
# _drop_offpage
# ---------------------------------------------------------------------------
def test_drop_offpage_removes_negative_y():
    words = [_w("OnPage", 20, 100), _w("Parked", 20, -200)]
    kept = _drop_offpage(words, {0: (300.0, 420.0)})
    assert [w["text"] for w in kept] == ["OnPage"]


def test_drop_offpage_keeps_bleed_edge():
    # A word a few pt past the trim edge (bleed) is kept.
    words = [_w("Bleed", 20, 418)]
    kept = _drop_offpage(words, {0: (300.0, 420.0)})
    assert len(kept) == 1


# ---------------------------------------------------------------------------
# _rotate_words_to_frame_space — rotated-frame measurement
# ---------------------------------------------------------------------------
def test_rotate_words_zero_rotation_is_passthrough():
    """An un-rotated frame must leave word boxes byte-identical."""
    words = [_w("Hello", 20, 100), _w("world", 60, 100)]
    out = _rotate_words_to_frame_space(words, 0.0)
    assert out == words


def test_rotate_words_minus_90_makes_vertical_text_horizontal():
    """A -90° frame: text that runs DOWN the page (each word below the
    previous, same page-x) must, after the transform, run left-to-right
    on a single rotated-space line — i.e. share one y and differ in x."""
    # Two words stacked vertically (a ttb column): same page-x, word 2
    # sits 30pt below word 1.
    w1 = _w("First", 280, 100, width=6)   # page box 280..286 x, 100..111 y
    w2 = _w("Second", 280, 130, width=6)  # 30pt lower
    out = _rotate_words_to_frame_space([w1, w2], -90.0)
    # After undoing a -90° frame the two words land on ONE rotated line.
    lines = _cluster_lines(out)
    assert len(lines) == 1, f"expected 1 rotated-space line, got {len(lines)}"
    # And they are ordered along the rotated x-axis (reading order).
    o1, o2 = (r for r in out)
    assert o1["y0_pt"] == o2["y0_pt"], "rotated words must share a baseline"
    # The word that was higher on the page becomes the LATER word in
    # rotated x; the lower one comes first — both are simply distinct x.
    assert o1["x0_pt"] != o2["x0_pt"]


def test_rotate_words_drift_along_reading_axis_is_preserved():
    """A real along-the-reading-axis drift in a rotated frame must survive
    the transform as a first-word-x delta — NOT be hidden in the y-axis."""
    # Baseline word and a preview word shifted 5pt DOWN the page (i.e.
    # along the reading axis of a -90° frame).
    base = _w("Wort", 280, 200, width=6)
    prev = _w("Wort", 280, 205, width=6)  # 5pt later along the column
    rb = _rotate_words_to_frame_space([base], -90.0)[0]
    rp = _rotate_words_to_frame_space([prev], -90.0)[0]
    # The 5pt page-y shift becomes a 5pt rotated-x shift (reading axis),
    # and the rotated-y (baseline) is unchanged.
    assert abs((rp["x0_pt"] - rb["x0_pt"])) - 5.0 < 0.01
    assert abs(rp["y0_pt"] - rb["y0_pt"]) < 0.01
    # Fed through the strict line check it surfaces as first_word_x.
    f = _check_line([rb], [rp], 0, 1.0, 2.0)
    assert f is not None and f["kind"] == "first_word_x"


def test_rotate_words_cross_axis_shift_becomes_baseline_y():
    """A shift PERPENDICULAR to the reading axis of a rotated frame must
    surface as a baseline_y finding, not first_word_x."""
    # In a -90° frame the cross-axis is page-x. Shift the preview word
    # 4pt in page-x.
    base = _w("Wort", 280, 200, width=6)
    prev = _w("Wort", 284, 200, width=6)
    rb = _rotate_words_to_frame_space([base], -90.0)[0]
    rp = _rotate_words_to_frame_space([prev], -90.0)[0]
    # First-word x (reading axis) unchanged; baseline y carries the shift.
    assert abs(rp["x0_pt"] - rb["x0_pt"]) < 0.01
    assert abs(abs(rp["y0_pt"] - rb["y0_pt"]) - 4.0) < 0.01
    f = _check_line([rb], [rp], 0, 1.0, 2.0)
    assert f is not None and f["kind"] == "baseline_y"


def test_rotate_words_no_relaxed_tolerance_for_rotated_frames():
    """Rotated frames are held to the SAME strict 1pt bar — a 1.5pt
    along-axis drift must still fail after the transform."""
    base = _w("Wort", 280, 200, width=6)
    prev = _w("Wort", 280, 201.5, width=6)  # 1.5pt > 1pt strict tol
    rb = _rotate_words_to_frame_space([base], -90.0)[0]
    rp = _rotate_words_to_frame_space([prev], -90.0)[0]
    f = _check_line([rb], [rp], 0, 1.0, 2.0)
    assert f is not None and f["kind"] == "first_word_x"


def test_rotate_words_plus_90_round_trips_box_extent():
    """The transform preserves a word box's extent (width/height swap for
    a 90° multiple) so spacing checks stay meaningful."""
    w = _w("Box", 100, 50, width=20)  # page box 20 wide, 11 tall
    out = _rotate_words_to_frame_space([w], 90.0)[0]
    rw = out["x1_pt"] - out["x0_pt"]
    rh = out["y1_pt"] - out["y0_pt"]
    # 90° rotation swaps the box dimensions.
    assert abs(rw - 11.0) < 0.01 and abs(rh - 20.0) < 0.01
