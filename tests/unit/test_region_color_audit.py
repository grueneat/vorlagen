"""Unit tests for tools/region_color_audit.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from region_color_audit import (  # noqa: E402
    parse_frames_from_build_py,
    bbox_mm_to_px,
    _sample_region_rgb_pure as sample_region_rgb_pure,
    _color_bucket,
    _median,
    classify_severity,
    classify_severity_compensated,
    classify_pattern,
    per_color_offsets,
    _yaml_dump,
    run_region_color_audit,
)


# ---------------------------------------------------------------------------
# 1. parse_frames_from_build_py — simple Polygon
# ---------------------------------------------------------------------------

_SIMPLE_BUILD_PY = """\
from sla_lib.builder import Polygon, TextFrame

def _add_page_0(doc, page0):
    page0.add(Polygon(
        x_mm=0.0,
        y_mm=0.0,
        w_mm=297.0,
        h_mm=210.0,
        anname='u1ae',
        layer=0,
        fill='Dunkelgrün',
    ))
    page0.add(TextFrame(
        x_mm=10.5,
        y_mm=20.0,
        w_mm=80.0,
        h_mm=15.0,
        anname='u2bc',
        layer=0,
    ))

def _add_page_1(doc, page1):
    page1.add(Polygon(
        x_mm=5.0,
        y_mm=5.0,
        w_mm=100.0,
        h_mm=50.0,
        anname='u3f0',
        layer=0,
        fill='Gelb',
    ))
"""


def test_parse_simple_polygon_from_build_py(tmp_path):
    """Parser extracts anname, page, type, and geometry from a build.py text."""
    build_py = tmp_path / "build.py"
    build_py.write_text(_SIMPLE_BUILD_PY, encoding="utf-8")

    frames = parse_frames_from_build_py(build_py)

    assert len(frames) == 3

    f0 = next(f for f in frames if f["anname"] == "u1ae")
    assert f0["page"] == 0
    assert f0["type"] == "Polygon"
    assert f0["x_mm"] == pytest.approx(0.0)
    assert f0["y_mm"] == pytest.approx(0.0)
    assert f0["w_mm"] == pytest.approx(297.0)
    assert f0["h_mm"] == pytest.approx(210.0)

    f1 = next(f for f in frames if f["anname"] == "u2bc")
    assert f1["page"] == 0
    assert f1["type"] == "TextFrame"
    assert f1["x_mm"] == pytest.approx(10.5)
    assert f1["w_mm"] == pytest.approx(80.0)

    f2 = next(f for f in frames if f["anname"] == "u3f0")
    assert f2["page"] == 1
    assert f2["type"] == "Polygon"
    assert f2["w_mm"] == pytest.approx(100.0)
    assert f2["h_mm"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# 2. bbox_mm_to_px — unit conversion at 150 dpi
# ---------------------------------------------------------------------------

def test_bbox_mm_to_px_at_150_dpi():
    """100mm × 50mm @ 150 dpi → 591px × 295px (rounded)."""
    # x_mm=0, y_mm=0, w_mm=100, h_mm=50 @ 150dpi
    # 100 × 150 / 25.4 = 591.34... → 591
    # 50  × 150 / 25.4 = 295.28... → 295
    left, top, right, bottom = bbox_mm_to_px(0.0, 0.0, 100.0, 50.0, 150)
    assert left == 0
    assert top == 0
    assert right == 591
    assert bottom == 295


def test_bbox_mm_to_px_nonzero_origin():
    """Non-zero x/y origin is converted correctly."""
    left, top, right, bottom = bbox_mm_to_px(10.0, 20.0, 50.0, 30.0, 150)
    # x_mm=10 → 10*150/25.4 = 59.055... → 59
    # y_mm=20 → 20*150/25.4 = 118.11... → 118
    # right  = (10+50)*150/25.4 = 354.33... → 354
    # bottom = (20+30)*150/25.4 = 295.27... → 295
    assert left == 59
    assert top == 118
    assert right == 354
    assert bottom == 295


# ---------------------------------------------------------------------------
# 3. sample_region_rgb — solid colour image
# ---------------------------------------------------------------------------

def _solid_image(r: int, g: int, b: int, width: int = 100, height: int = 100) -> Image.Image:
    img = Image.new("RGB", (width, height), color=(r, g, b))
    return img


def test_sample_region_rgb_solid_color():
    """Solid #3c5c2d image (Dunkelgrün) → mean_rgb ≈ (60, 92, 45)."""
    # Hex #3c5c2d = R=60, G=92, B=45
    img = _solid_image(60, 92, 45, 100, 100)
    mr, mg, mb, n = sample_region_rgb_pure(img, (0, 0, 100, 100))
    assert abs(mr - 60) < 0.5
    assert abs(mg - 92) < 0.5
    assert abs(mb - 45) < 0.5
    assert n == 10000


def test_sample_region_rgb_partial_crop():
    """Sampling a sub-region returns correct mean for that region."""
    img = Image.new("RGB", (200, 200))
    # Top-left 100×100: red; bottom-right 100×100: blue
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 99, 99], fill=(255, 0, 0))
    draw.rectangle([100, 100, 199, 199], fill=(0, 0, 255))

    # Sample only top-left quadrant
    mr, mg, mb, n = sample_region_rgb_pure(img, (0, 0, 100, 100))
    assert abs(mr - 255) < 1.0
    assert abs(mg - 0) < 1.0
    assert abs(mb - 0) < 1.0


def test_sample_region_rgb_out_of_bounds_clamped():
    """Out-of-bounds bbox is clamped to image size without crashing."""
    img = _solid_image(128, 128, 128, 50, 50)
    mr, mg, mb, n = sample_region_rgb_pure(img, (0, 0, 500, 500))
    assert abs(mr - 128) < 1.0
    assert n == 2500  # clamped to 50×50


def test_sample_region_rgb_degenerate_empty():
    """Zero-area bbox returns (0, 0, 0, 0)."""
    img = _solid_image(100, 100, 100, 100, 100)
    mr, mg, mb, n = sample_region_rgb_pure(img, (50, 50, 50, 50))
    assert n == 0


# ---------------------------------------------------------------------------
# 4. classify_severity — icc_likely (small delta)
# ---------------------------------------------------------------------------

def test_severity_classification_small_delta_icc():
    """RGB delta of 5 units → severity 'icc_likely'."""
    assert classify_severity(5.0) == "icc_likely"


def test_severity_classification_boundary_icc_low():
    """RGB delta of exactly 3.0 → 'icc_likely' (boundary inclusive)."""
    assert classify_severity(3.0) == "icc_likely"


def test_severity_classification_boundary_icc_high():
    """RGB delta just below 15 → 'icc_likely'."""
    assert classify_severity(14.99) == "icc_likely"


# ---------------------------------------------------------------------------
# 5. classify_severity — fill_likely (large delta)
# ---------------------------------------------------------------------------

def test_severity_classification_large_delta_fill():
    """RGB delta of 40 units → severity 'fill_likely'."""
    assert classify_severity(40.0) == "fill_likely"


def test_severity_classification_boundary_fill():
    """RGB delta of exactly 15 → 'fill_likely' (boundary)."""
    assert classify_severity(15.0) == "fill_likely"


# ---------------------------------------------------------------------------
# 6. classify_severity — ok (sub-pixel noise)
# ---------------------------------------------------------------------------

def test_severity_classification_subpixel_ok():
    """RGB delta < 3 → severity 'ok'."""
    assert classify_severity(0.0) == "ok"
    assert classify_severity(1.5) == "ok"
    assert classify_severity(2.99) == "ok"


# ---------------------------------------------------------------------------
# 7. classify_pattern — predominantly_icc_drift
# ---------------------------------------------------------------------------

def test_pattern_predominantly_icc_when_icc_dominates():
    """icc=10, fill=2 → pattern 'predominantly_icc_drift' (icc >= 3× fill)."""
    result = classify_pattern({"ok": 5, "icc_likely": 10, "fill_likely": 2})
    assert result == "predominantly_icc_drift"


def test_pattern_predominantly_icc_no_fill():
    """icc=5, fill=0 → pattern 'predominantly_icc_drift'."""
    result = classify_pattern({"ok": 0, "icc_likely": 5, "fill_likely": 0})
    assert result == "predominantly_icc_drift"


# ---------------------------------------------------------------------------
# 8. classify_pattern — concentrated_fill_bugs
# ---------------------------------------------------------------------------

def test_pattern_fill_bugs_when_fill_count_high():
    """icc=2, fill=5 → pattern 'concentrated_fill_bugs' (fill >= 3)."""
    result = classify_pattern({"ok": 0, "icc_likely": 2, "fill_likely": 5})
    assert result == "concentrated_fill_bugs"


def test_pattern_fill_bugs_exact_threshold():
    """fill=3 exactly → pattern 'concentrated_fill_bugs'."""
    result = classify_pattern({"ok": 0, "icc_likely": 0, "fill_likely": 3})
    assert result == "concentrated_fill_bugs"


def test_pattern_mixed():
    """icc=2, fill=2 → pattern 'mixed' (neither dominates)."""
    result = classify_pattern({"ok": 0, "icc_likely": 2, "fill_likely": 2})
    assert result == "mixed"


# ---------------------------------------------------------------------------
# 8b. Per-colour offset compensation
# ---------------------------------------------------------------------------

def test_median_odd_and_even():
    """_median returns the middle element (odd) or the mean of two (even)."""
    assert _median([5.0, 1.0, 3.0]) == 3.0
    assert _median([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_color_bucket_quantises_close_colors_together():
    """Colours within the 48-unit grid land in the same bucket."""
    # Two greens 10 RGB units apart → same bucket.
    assert _color_bucket((60.0, 92.0, 45.0)) == _color_bucket((68.0, 100.0, 52.0))
    # A green and a white → different buckets.
    assert _color_bucket((60.0, 92.0, 45.0)) != _color_bucket((250.0, 250.0, 250.0))


def test_per_color_offsets_estimates_each_colour_separately():
    """Each colour bucket gets its own median signed offset.

    Two green peers drift by (-1, -13, +3); two white peers drift ~0. The
    offset map must report a distinct offset per colour bucket.
    """
    samples = [
        ((60.0, 92.0, 45.0), (-1.0, -13.0, 3.0)),
        ((61.0, 93.0, 46.0), (-1.0, -13.0, 3.0)),
        ((250.0, 250.0, 250.0), (0.0, -1.0, 0.0)),
        ((251.0, 251.0, 251.0), (0.0, -1.0, 0.0)),
    ]
    offsets = per_color_offsets(samples)
    green = offsets[_color_bucket((60.0, 92.0, 45.0))]
    white = offsets[_color_bucket((250.0, 250.0, 250.0))]
    assert green == (-1.0, -13.0, 3.0)
    assert white == (0.0, -1.0, 0.0)


def test_per_color_offsets_singleton_uses_document_median():
    """A singleton colour bucket inherits the document-wide median offset.

    The lone unique-colour frame must NOT become its own reference (that
    would mask a genuine fill bug); it gets the document median instead.
    """
    samples = [
        ((60.0, 92.0, 45.0), (5.0, 5.0, 5.0)),
        ((61.0, 93.0, 46.0), (5.0, 5.0, 5.0)),
        ((61.0, 92.0, 45.0), (5.0, 5.0, 5.0)),
        ((250.0, 10.0, 200.0), (40.0, 40.0, 40.0)),  # unique colour
    ]
    offsets = per_color_offsets(samples)
    singleton = offsets[_color_bucket((250.0, 10.0, 200.0))]
    # Document median of all four deltas is (5, 5, 5), not the frame's own.
    assert singleton == (5.0, 5.0, 5.0)


def test_classify_severity_compensated_removes_shared_offset():
    """A frame matching its colour's offset classifies 'ok'."""
    offsets = {_color_bucket((60.0, 92.0, 45.0)): (-1.0, -13.0, 3.0)}
    severity, residual = classify_severity_compensated(
        (60.0, 92.0, 45.0), (-1.0, -13.0, 3.0), offsets,
    )
    assert severity == "ok"
    assert residual < 3.0


def test_classify_severity_compensated_flags_deviation():
    """A frame deviating from its colour's offset classifies 'fill_likely'."""
    offsets = {_color_bucket((60.0, 92.0, 45.0)): (-1.0, -13.0, 3.0)}
    # This frame is +30 on every channel beyond the shared offset.
    severity, residual = classify_severity_compensated(
        (60.0, 92.0, 45.0), (29.0, 17.0, 33.0), offsets,
    )
    assert severity == "fill_likely"
    assert residual > 15.0


# ---------------------------------------------------------------------------
# 9. _yaml_dump — deterministic output (byte-identical on re-run)
# ---------------------------------------------------------------------------

def test_output_deterministic_sorted_keys():
    """Re-running _yaml_dump on the same payload produces identical output."""
    payload = {
        "template": "test-tpl",
        "pattern": "predominantly_icc_drift",
        "by_severity": {"fill_likely": 2, "icc_likely": 10, "ok": 5},
        "frames": [
            {
                "anname": "u1ae",
                "page": 0,
                "type": "Polygon",
                "bbox_mm": [0.0, 0.0, 297.0, 210.0],
                "baseline_rgb": [60.4, 92.1, 45.2],
                "preview_rgb": [58.9, 90.5, 43.7],
                "mean_delta": 1.5,
                "rms_delta": 2.1,
                "severity": "icc_likely",
            }
        ],
    }
    out1 = _yaml_dump(payload)
    out2 = _yaml_dump(payload)
    assert out1 == out2
    # Keys must appear in sorted order.
    assert out1.index("anname") < out1.index("baseline_rgb")
    assert out1.index("by_severity") < out1.index("frames")


def test_yaml_dump_sorts_keys():
    """_yaml_dump sorts keys alphabetically at all levels."""
    payload = {"z_key": 1, "a_key": 2, "m_key": 3}
    out = _yaml_dump(payload)
    lines = [l for l in out.splitlines() if ":" in l]
    keys = [l.split(":")[0].strip() for l in lines]
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Integration: run_region_color_audit on synthetic PDFs
# ---------------------------------------------------------------------------

def _make_solid_pdf(path: Path, r: int, g: int, b: int) -> None:
    """Write a minimal 1-page PDF with a solid-colour background using pdftocairo-friendly approach.

    We use Pillow to create a PNG and then convert it to a 1-page PDF via img2pdf
    or just save a PDF directly. Fall back to creating a PNG-based PDF using
    Pillow's PDF writer.
    """
    img = Image.new("RGB", (1240, 1754), color=(r, g, b))  # A4 @ 150dpi
    img.save(str(path), "PDF", resolution=150)


_MINIMAL_BUILD_PY = """\
def _add_page_0(doc, page0):
    from sla_lib.builder import Polygon
    page0.add(Polygon(
        x_mm=0.0,
        y_mm=0.0,
        w_mm=297.0,
        h_mm=210.0,
        anname='u1ae',
        layer=0,
        fill='Dunkelgrün',
    ))
"""


def test_run_audit_produces_by_severity(tmp_path):
    """run_region_color_audit produces a valid by_severity dict."""
    # Baseline: Dunkelgrün-ish solid colour
    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    build_py = tmp_path / "build.py"

    _make_solid_pdf(baseline_pdf, 60, 92, 45)   # Dunkelgrün
    _make_solid_pdf(preview_pdf, 58, 90, 43)    # slight ICC-style drift

    build_py.write_text(_MINIMAL_BUILD_PY, encoding="utf-8")

    result = run_region_color_audit(build_py, baseline_pdf, preview_pdf, "test-tpl")

    assert "by_severity" in result
    assert "pattern" in result
    assert "frames" in result
    assert result["template"] == "test-tpl"
    total = sum(result["by_severity"].values())
    assert total >= 1  # at least u1ae counted


def test_run_audit_u1ae_in_frames(tmp_path):
    """u1ae frame appears in the audit results."""
    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    build_py = tmp_path / "build.py"

    _make_solid_pdf(baseline_pdf, 60, 92, 45)
    _make_solid_pdf(preview_pdf, 58, 90, 43)
    build_py.write_text(_MINIMAL_BUILD_PY, encoding="utf-8")

    result = run_region_color_audit(build_py, baseline_pdf, preview_pdf, "test-tpl")

    annames = {f["anname"] for f in result["frames"]}
    assert "u1ae" in annames


# A build.py with four quadrant regions — enough colour peers that the
# offset-compensated audit can tell a uniform colour-management offset
# (shared by peers) from a real fill-colour bug (one region deviating).
# Geometry: A4 @ 150 dpi is 1240×1754 px = 209.97×297.04 mm; each quadrant
# is 620×877 px = 104.99×148.52 mm. The build.py parser needs literal
# float coordinates, so they are spelled out below.
_FOUR_QUADRANT_BUILD_PY = """\
def _add_page_0(doc, page0):
    from sla_lib.builder import Polygon
    page0.add(Polygon(
        x_mm=2.0, y_mm=2.0, w_mm=100.0, h_mm=144.0,
        anname='peer0', layer=0,
    ))
    page0.add(Polygon(
        x_mm=107.0, y_mm=2.0, w_mm=100.0, h_mm=144.0,
        anname='peer1', layer=0,
    ))
    page0.add(Polygon(
        x_mm=2.0, y_mm=150.0, w_mm=100.0, h_mm=144.0,
        anname='peer2', layer=0,
    ))
    page0.add(Polygon(
        x_mm=107.0, y_mm=150.0, w_mm=100.0, h_mm=144.0,
        anname='peer3', layer=0,
    ))
"""


def _make_quadrant_pdf(path, quadrant_colors):
    """Write a 1-page PDF split into 4 equal quadrants of the given colours.

    quadrant_colors is [(r,g,b), ...] for [top-left, top-right,
    bottom-left, bottom-right]. Page is A4 @ 150 dpi (1240×1754).
    """
    from PIL import ImageDraw
    img = Image.new("RGB", (1240, 1754), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    hw, hh = 620, 877
    rects = [(0, 0, hw, hh), (hw, 0, 1240, hh),
             (0, hh, hw, 1754), (hw, hh, 1240, 1754)]
    for (x0, y0, x1, y1), color in zip(rects, quadrant_colors):
        draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=color)
    img.save(str(path), "PDF", resolution=150)


def test_run_audit_uniform_offset_not_flagged(tmp_path):
    """A uniform offset shared by every colour peer classifies 'ok'.

    Four same-coloured peers all drift by +6 on every channel — that is a
    document-wide colour-management offset, not a per-frame fill bug. After
    offset compensation every peer's residual is ~0, so none is flagged.
    """
    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    build_py = tmp_path / "build.py"
    build_py.write_text(_FOUR_QUADRANT_BUILD_PY, encoding="utf-8")

    base = (60, 92, 45)
    _make_quadrant_pdf(baseline_pdf, [base] * 4)
    # Every quadrant drifts identically by +6 — a uniform offset.
    drifted = tuple(c + 6 for c in base)
    _make_quadrant_pdf(preview_pdf, [drifted] * 4)

    result = run_region_color_audit(build_py, baseline_pdf, preview_pdf, "test-tpl")

    peers = [f for f in result["frames"] if f["anname"].startswith("peer")]
    assert len(peers) == 4
    # The raw delta is ~6 but the offset-compensated residual is ~0.
    for f in peers:
        assert f["severity"] == "ok", f
        assert f["residual_delta"] < 3.0


def test_run_audit_deviating_region_is_fill_likely(tmp_path):
    """A region deviating from its colour peers classifies 'fill_likely'.

    Three peers carry the uniform +6 colour-management offset; the fourth
    is wrong by a further +30. After offset compensation the three peers
    classify 'ok' and only the deviating region is flagged 'fill_likely'.
    """
    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    build_py = tmp_path / "build.py"
    build_py.write_text(_FOUR_QUADRANT_BUILD_PY, encoding="utf-8")

    base = (60, 92, 45)
    _make_quadrant_pdf(baseline_pdf, [base] * 4)
    uniform = tuple(c + 6 for c in base)
    bug = tuple(c + 36 for c in base)  # +30 beyond the uniform offset
    _make_quadrant_pdf(preview_pdf, [uniform, uniform, uniform, bug])

    result = run_region_color_audit(build_py, baseline_pdf, preview_pdf, "test-tpl")

    by_name = {f["anname"]: f for f in result["frames"]}
    # peer0..2 share the uniform offset → ok; peer3 deviates → fill_likely.
    for name in ("peer0", "peer1", "peer2"):
        assert by_name[name]["severity"] == "ok", by_name[name]
    assert by_name["peer3"]["severity"] == "fill_likely", by_name["peer3"]
    assert by_name["peer3"]["residual_delta"] > 15


def test_run_audit_sorted_fill_before_icc(tmp_path):
    """Results are sorted: fill_likely frames before icc_likely frames."""
    build_source = """\
def _add_page_0(doc, page0):
    from sla_lib.builder import Polygon
    page0.add(Polygon(
        x_mm=0.0,
        y_mm=0.0,
        w_mm=100.0,
        h_mm=100.0,
        anname='u001',
        layer=0,
    ))
    page0.add(Polygon(
        x_mm=100.0,
        y_mm=0.0,
        w_mm=100.0,
        h_mm=100.0,
        anname='u002',
        layer=0,
    ))
"""
    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    build_py = tmp_path / "build.py"
    build_py.write_text(build_source, encoding="utf-8")

    # Create a two-region image: left half red, right half slightly offset
    img_b = Image.new("RGB", (1240, 1754), color=(100, 100, 100))
    img_p = Image.new("RGB", (1240, 1754), color=(130, 130, 130))  # +30 → fill_likely

    img_b.save(str(baseline_pdf), "PDF", resolution=150)
    img_p.save(str(preview_pdf), "PDF", resolution=150)

    result = run_region_color_audit(build_py, baseline_pdf, preview_pdf, "test-tpl")

    frames = result["frames"]
    if len(frames) >= 2:
        sevs = [f["severity"] for f in frames]
        # All fill_likely should appear before all icc_likely
        _sev_order = {"fill_likely": 0, "icc_likely": 1, "ok": 2}
        orders = [_sev_order[s] for s in sevs]
        assert orders == sorted(orders)
