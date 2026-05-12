"""Unit tests for compare_grid (Issue #37 P2 task 8 / Backport 12)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from visual_diff import compare_grid  # noqa: E402


def _save(img: Image.Image, path: Path) -> Path:
    img.save(path)
    return path


def test_identical_images_all_cells_zero(tmp_path):
    """Two identical white images → every cell has 0 mismatch."""
    a = Image.new("RGB", (60, 40), "white")
    p_a = _save(a, tmp_path / "a.png")
    p_b = _save(a.copy(), tmp_path / "b.png")
    cells = compare_grid(p_a, p_b, cols=6, rows=4, fuzz_pct=25.0)
    assert len(cells) == 24  # 6×4 cells
    for c in cells:
        assert c["mismatch_pixels"] == 0
        assert c["mismatch_pct"] == 0.0


def test_localized_diff_only_one_cell_hot(tmp_path):
    """A 10×10 colored patch at col=1,row=0 → exactly that cell shows mismatch."""
    base = Image.new("RGB", (60, 40), "white")
    prev = base.copy()
    # Cell (col=1, row=0) at integer 6×4 split is x=10..20, y=0..10.
    # Paste a black 10×10 patch into preview only.
    patch = Image.new("RGB", (10, 10), "black")
    prev.paste(patch, (10, 0))
    p_a = _save(base, tmp_path / "a.png")
    p_b = _save(prev, tmp_path / "b.png")
    cells = compare_grid(p_a, p_b, cols=6, rows=4, fuzz_pct=0.0)
    hot = [c for c in cells if c["mismatch_pixels"] > 0]
    assert len(hot) == 1
    assert hot[0]["col"] == 1
    assert hot[0]["row"] == 0
    assert hot[0]["mismatch_pixels"] == 100  # full patch


def test_global_diff_fuzz_zero_all_mismatched(tmp_path):
    """Pure-red vs pure-white with fuzz=0 → every cell 100 % mismatch."""
    red = Image.new("RGB", (60, 40), "red")
    white = Image.new("RGB", (60, 40), "white")
    p_a = _save(red, tmp_path / "a.png")
    p_b = _save(white, tmp_path / "b.png")
    cells = compare_grid(p_a, p_b, cols=6, rows=4, fuzz_pct=0.0)
    for c in cells:
        assert c["mismatch_pct"] == 100.0


def test_global_diff_fuzz_high_all_passing(tmp_path):
    """Pure-red vs pure-white with fuzz=99 → max-channel-delta=255, threshold=
    round(255*0.99)=252; 255>252 still counts as mismatch. Use fuzz=100 to
    swallow everything."""
    red = Image.new("RGB", (60, 40), "red")
    white = Image.new("RGB", (60, 40), "white")
    p_a = _save(red, tmp_path / "a.png")
    p_b = _save(white, tmp_path / "b.png")
    cells = compare_grid(p_a, p_b, cols=6, rows=4, fuzz_pct=100.0)
    for c in cells:
        assert c["mismatch_pct"] == 0.0


def test_size_mismatch_raises(tmp_path):
    """Different image dimensions → ValueError."""
    a = Image.new("RGB", (60, 40), "white")
    b = Image.new("RGB", (50, 40), "white")
    p_a = _save(a, tmp_path / "a.png")
    p_b = _save(b, tmp_path / "b.png")
    with pytest.raises(ValueError, match="image size mismatch"):
        compare_grid(p_a, p_b, cols=6, rows=4)


def test_modulus_absorbed_by_last_column(tmp_path):
    """65×40 image, 6×4 grid → cell widths [10,10,10,10,10,15]."""
    a = Image.new("RGB", (65, 40), "white")
    p_a = _save(a, tmp_path / "a.png")
    p_b = _save(a.copy(), tmp_path / "b.png")
    cells = compare_grid(p_a, p_b, cols=6, rows=4)
    # Inspect row 0 cells, col 0..5
    row0 = [c for c in cells if c["row"] == 0]
    widths = [c["bbox_px"]["w"] for c in row0]
    assert widths == [10, 10, 10, 10, 10, 15]


def test_determinism(tmp_path):
    """Two runs on the same images produce identical dict output."""
    base = Image.new("RGB", (60, 40), "white")
    prev = base.copy()
    prev.paste(Image.new("RGB", (5, 5), "black"), (12, 22))
    p_a = _save(base, tmp_path / "a.png")
    p_b = _save(prev, tmp_path / "b.png")
    r1 = compare_grid(p_a, p_b, cols=6, rows=4)
    r2 = compare_grid(p_a, p_b, cols=6, rows=4)
    assert r1 == r2
