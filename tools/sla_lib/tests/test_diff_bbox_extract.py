"""Tests for tools/diff_bbox_extract.py (Issue #36).

Conventions match ``test_audit_alignment.py``:
- ``unittest.TestCase`` (not pytest), per locked decision 6.
- ``tempfile.mkdtemp()`` + try/finally rmtree.
- ``sys.path.insert(0, ROOT / "tools")`` bootstrap.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import diff_bbox_extract  # noqa: E402
from diff_bbox_extract import (  # noqa: E402
    DiffBBoxError, attribute_diff_bbox, coverage_of_diff_inside_slot,
    extract_all, extract_bboxes_px, load_dpi, load_template_slots,
    px_to_mm_bbox, write_json, write_overlay_png,
)


def _build_synthetic_out_dir(
    tmpdir: Path, page_rects: list[list[tuple[int, int, int, int]]],
    *, dpi: int = 96, delta_filenames: list[str] | None = None,
    with_dsl_pngs: bool = False, dsl_size: tuple[int, int] = (200, 200),
) -> Path:
    """Build a fake visual_diff.py output directory in ``tmpdir``.

    ``page_rects`` is a list (one entry per page) of rectangles
    ``(x, y, w, h)`` in pixels to draw red on the delta PNG. Returns the
    tmpdir path for convenience.

    When ``with_dsl_pngs=True``, also writes a plain-white
    ``dsl-page-{idx+1}.png`` (unpadded — matches pdftoppm's behaviour for
    <=9-page documents) per page so the overlay writer has a source.
    """
    pages_meta = []
    for idx, rects in enumerate(page_rects):
        fname = (
            delta_filenames[idx] if delta_filenames
            else f"diff-page-{idx + 1:02d}.png"
        )
        _draw_delta(tmpdir / fname, (200, 200), rects)
        if with_dsl_pngs:
            dsl_img = Image.new("RGBA", dsl_size, (255, 255, 255, 255))
            dsl_img.save(tmpdir / f"dsl-page-{idx + 1}.png", format="PNG")
        pages_meta.append({"page": idx, "delta_png": fname})
    (tmpdir / "visual_diff.json").write_text(
        json.dumps({"dpi": dpi, "pages": pages_meta}, indent=2),
        encoding="utf-8",
    )
    return tmpdir


def _draw_delta(path: Path, size: tuple[int, int],
                rects: list[tuple[int, int, int, int]]) -> None:
    """Synthesise a delta PNG: white RGBA background + red (199,23,35,255) rectangles.

    ``rects`` is a list of ``(x, y, w, h)`` tuples in pixels.
    """
    im = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(im)
    for x, y, w, h in rects:
        # ImageDraw.rectangle is inclusive on both ends, so subtract 1 to
        # land an exactly w x h pixel block.
        draw.rectangle([x, y, x + w - 1, y + h - 1],
                       fill=(199, 23, 35, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG")


class ExtractBBoxesPxTests(unittest.TestCase):
    """Synthetic-fixture tests for ``extract_bboxes_px``."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="diff_bbox_t_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_synthetic_red_rect_one_bbox(self) -> None:
        png = self.tmpdir / "delta.png"
        _draw_delta(png, (200, 200), [(50, 60, 30, 20)])
        out = extract_bboxes_px(png, threshold=200, min_area_px=10)
        self.assertEqual(len(out), 1, f"expected 1 bbox, got {out}")
        b = out[0]
        self.assertEqual(b["x_px"], 50)
        self.assertEqual(b["y_px"], 60)
        self.assertEqual(b["w_px"], 30)
        self.assertEqual(b["h_px"], 20)
        self.assertEqual(b["area_px"], 600)

    def test_two_separated_rects_two_bboxes(self) -> None:
        png = self.tmpdir / "delta.png"
        # Two rects far enough apart that 8-connectivity does not merge them.
        _draw_delta(png, (300, 300), [(20, 30, 25, 25), (200, 150, 40, 40)])
        out = extract_bboxes_px(png, threshold=200, min_area_px=10)
        self.assertEqual(len(out), 2)
        # Sorted by (y, x); first rect has lower y.
        self.assertEqual((out[0]["x_px"], out[0]["y_px"]), (20, 30))
        self.assertEqual((out[1]["x_px"], out[1]["y_px"]), (200, 150))

    def test_below_min_area_filtered(self) -> None:
        png = self.tmpdir / "delta.png"
        _draw_delta(png, (100, 100), [(10, 10, 3, 3)])  # area 9
        out = extract_bboxes_px(png, threshold=200, min_area_px=100)
        self.assertEqual(out, [])

    def test_missing_delta_raises_DiffBBoxError(self) -> None:
        with self.assertRaises(DiffBBoxError) as ctx:
            extract_bboxes_px(self.tmpdir / "nope.png")
        self.assertIn("missing delta PNG", str(ctx.exception))


class DpiAndUnitsTests(unittest.TestCase):
    """Tests for ``load_dpi`` + ``px_to_mm_bbox`` (Issue #36 task 3)."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="diff_bbox_dpi_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_dpi_reads_value(self) -> None:
        (self.tmpdir / "visual_diff.json").write_text(
            json.dumps({"dpi": 96, "pages": []}), encoding="utf-8",
        )
        self.assertEqual(load_dpi(self.tmpdir), 96)

    def test_load_dpi_missing_file_raises(self) -> None:
        with self.assertRaises(DiffBBoxError) as ctx:
            load_dpi(self.tmpdir)
        self.assertIn("missing visual_diff.json", str(ctx.exception))

    def test_load_dpi_missing_key_raises(self) -> None:
        (self.tmpdir / "visual_diff.json").write_text(
            json.dumps({"pages": []}), encoding="utf-8",
        )
        with self.assertRaises(DiffBBoxError) as ctx:
            load_dpi(self.tmpdir)
        self.assertIn("missing 'dpi'", str(ctx.exception))

    def test_px_to_mm_at_96dpi(self) -> None:
        # 25.4 mm/inch / 96 dpi => 0.2645833... mm/px
        # 96 px -> 25.4 mm; 192 -> 50.8; 48 -> 12.7; 24 -> 6.35 -> 6.3 (banker)
        b = px_to_mm_bbox(
            {"x_px": 96, "y_px": 192, "w_px": 48, "h_px": 24}, dpi=96,
        )
        self.assertEqual(b["x"], 25.4)
        self.assertEqual(b["y"], 50.8)
        self.assertEqual(b["w"], 12.7)
        # 6.35 rounds to 6.3 under Python's round-half-to-even; either is
        # within the documented 0.1 mm tolerance.
        self.assertAlmostEqual(b["h"], 6.35, delta=0.1)

    def test_px_to_mm_at_150dpi(self) -> None:
        # Same input at 150 dpi scales by 96/150 = 0.64 relative to the
        # 96-dpi case (i.e. (25.4/150) mm/px).
        b96 = px_to_mm_bbox(
            {"x_px": 96, "y_px": 192, "w_px": 48, "h_px": 24}, dpi=96,
        )
        b150 = px_to_mm_bbox(
            {"x_px": 96, "y_px": 192, "w_px": 48, "h_px": 24}, dpi=150,
        )
        scale = 96.0 / 150.0
        for k in ("x", "y", "w", "h"):
            self.assertAlmostEqual(b150[k], b96[k] * scale, delta=0.15)


class SlotLoaderTests(unittest.TestCase):
    """Tests for ``load_template_slots`` (Issue #36 task 4)."""

    def test_load_slots_postkarte(self) -> None:
        slots = load_template_slots("postkarte-a6-kampagne")
        # postkarte-a6-kampagne has 2 pages; both have at least the
        # background slot, so both indices should appear.
        self.assertIn(0, slots)
        self.assertIn(1, slots)
        # Every slot bbox is a dict with float x/y/w/h.
        for page_idx, page_slots in slots.items():
            self.assertTrue(page_slots, f"page {page_idx} has no slots")
            for anname, bbox in page_slots.items():
                self.assertEqual(set(bbox.keys()), {"x", "y", "w", "h"})
                for k, v in bbox.items():
                    self.assertIsInstance(
                        v, float, f"page {page_idx} slot {anname!r} key {k} is {type(v)}",
                    )

    def test_load_slots_unknown_template_warns_and_returns_empty(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = load_template_slots("definitely-does-not-exist")
        self.assertEqual(result, {})
        self.assertGreaterEqual(len(caught), 1)
        self.assertTrue(
            any("attribution skipped" in str(w.message) for w in caught),
            f"no skip-warning in captured: {[str(w.message) for w in caught]}",
        )


class AttributionMathTests(unittest.TestCase):
    """Tests for ``coverage_of_diff_inside_slot`` + ``attribute_diff_bbox``
    (Issue #36 task 5)."""

    def test_coverage_full_overlap(self) -> None:
        d = {"x": 10, "y": 10, "w": 5, "h": 5}
        s = {"x": 0, "y": 0, "w": 50, "h": 50}
        self.assertAlmostEqual(coverage_of_diff_inside_slot(d, s), 1.0)

    def test_coverage_no_overlap(self) -> None:
        d = {"x": 100, "y": 100, "w": 10, "h": 10}
        s = {"x": 0, "y": 0, "w": 50, "h": 50}
        self.assertAlmostEqual(coverage_of_diff_inside_slot(d, s), 0.0)

    def test_coverage_partial_50pct(self) -> None:
        # Diff is 10x10; slot covers the left 5x10 half => coverage = 0.5
        d = {"x": 0, "y": 0, "w": 10, "h": 10}
        s = {"x": 0, "y": 0, "w": 5, "h": 10}
        self.assertAlmostEqual(coverage_of_diff_inside_slot(d, s), 0.5)

    def test_coverage_zero_area_diff_returns_zero(self) -> None:
        d = {"x": 0, "y": 0, "w": 0, "h": 0}
        s = {"x": 0, "y": 0, "w": 10, "h": 10}
        self.assertEqual(coverage_of_diff_inside_slot(d, s), 0.0)

    def test_attribute_picks_smaller_slot_on_tie(self) -> None:
        # Two slots both cover the diff 100%; tie-break prefers smaller area.
        d = {"x": 10, "y": 10, "w": 5, "h": 5}
        page_slots = {
            "Bg": {"x": 0, "y": 0, "w": 30, "h": 30},        # area 900
            "Headline": {"x": 5, "y": 5, "w": 10, "h": 10},  # area 100
        }
        name, overlap, cands = attribute_diff_bbox(d, page_slots, 0.5)
        self.assertEqual(name, "Headline")
        self.assertEqual(overlap, 100.0)
        # candidates[0] is the winner; candidates[1] is the loser.
        self.assertEqual(cands[0]["slot"], "Headline")
        self.assertEqual(cands[1]["slot"], "Bg")

    def test_attribute_no_match_below_threshold(self) -> None:
        d = {"x": 0, "y": 0, "w": 10, "h": 10}
        page_slots = {
            "Far": {"x": 9, "y": 9, "w": 10, "h": 10},  # coverage 0.01
        }
        name, overlap, cands = attribute_diff_bbox(d, page_slots, 0.5)
        self.assertIsNone(name)
        self.assertEqual(overlap, 0.0)
        # Candidates list still populated so consumer sees the alternative.
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["slot"], "Far")

    def test_candidates_top3_only(self) -> None:
        d = {"x": 0, "y": 0, "w": 10, "h": 10}
        # Five slots that all overlap the diff, distinct coverages.
        page_slots = {
            "A": {"x": 0, "y": 0, "w": 10, "h": 10},   # cov 1.0, area 100
            "B": {"x": 0, "y": 0, "w": 10, "h": 9},    # cov 0.9, area 90
            "C": {"x": 0, "y": 0, "w": 10, "h": 8},    # cov 0.8, area 80
            "D": {"x": 0, "y": 0, "w": 10, "h": 7},    # cov 0.7, area 70
            "E": {"x": 0, "y": 0, "w": 10, "h": 6},    # cov 0.6, area 60
        }
        _, _, cands = attribute_diff_bbox(d, page_slots, 0.5)
        self.assertEqual(len(cands), 3)
        # Sorted descending by coverage_pct.
        self.assertEqual([c["slot"] for c in cands], ["A", "B", "C"])
        # coverage_pct values rounded to 1 decimal.
        self.assertEqual(cands[0]["coverage_pct"], 100.0)
        self.assertAlmostEqual(cands[1]["coverage_pct"], 90.0)

    def test_empty_page_slots_returns_none_attribution(self) -> None:
        d = {"x": 0, "y": 0, "w": 10, "h": 10}
        name, overlap, cands = attribute_diff_bbox(d, {}, 0.5)
        self.assertIsNone(name)
        self.assertEqual(overlap, 0.0)
        self.assertEqual(cands, [])


class ExtractAllPipelineTests(unittest.TestCase):
    """Tests for ``extract_all`` + ``write_json`` (Issue #36 task 6)."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="diff_bbox_extract_all_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_extract_all_deterministic_byte_equal(self) -> None:
        out_dir = _build_synthetic_out_dir(
            self.tmpdir / "vd",
            page_rects=[
                [(50, 60, 30, 20)],
                [(20, 30, 40, 40), (120, 110, 25, 25)],
            ],
        )
        payload_a = extract_all(out_dir, min_area_px=10)
        payload_b = extract_all(out_dir, min_area_px=10)
        out_a = self.tmpdir / "a.json"
        out_b = self.tmpdir / "b.json"
        write_json(payload_a, out_a)
        write_json(payload_b, out_b)
        self.assertEqual(
            out_a.read_bytes(), out_b.read_bytes(),
            "diff_bboxes.json must be byte-identical across runs",
        )

    def test_extract_all_sorts_bboxes_by_y_then_x(self) -> None:
        out_dir = _build_synthetic_out_dir(
            self.tmpdir / "vd",
            page_rects=[[
                (150, 50, 20, 20),   # rect at low y
                (10, 150, 25, 25),   # rect at high y (sorted last)
                (130, 50, 15, 15),   # same y as the first, but lower x
            ]],
        )
        payload = extract_all(out_dir, min_area_px=10)
        rects = payload["pages"][0]["bboxes"]
        self.assertEqual(len(rects), 3)
        ys = [r["bbox_mm"]["y"] for r in rects]
        self.assertEqual(ys, sorted(ys), f"not sorted by y: {ys}")
        # Two share y; the lower-x one comes first.
        same_y = [r for r in rects if r["bbox_mm"]["y"] == ys[0]]
        if len(same_y) == 2:
            self.assertLess(same_y[0]["bbox_mm"]["x"], same_y[1]["bbox_mm"]["x"])

    def test_extract_all_no_template_slug_unattributed(self) -> None:
        out_dir = _build_synthetic_out_dir(
            self.tmpdir / "vd", page_rects=[[(50, 60, 30, 20)]],
        )
        payload = extract_all(out_dir, template_slug=None, min_area_px=10)
        for page in payload["pages"]:
            for bbox in page["bboxes"]:
                self.assertIsNone(bbox["attributed_slot"])
                self.assertEqual(bbox["attribution_candidates"], [])
                self.assertEqual(bbox["attribution_overlap_pct"], 0.0)

    def test_extract_all_uses_recorded_delta_filename(self) -> None:
        # Use a non-default delta_png name to prove extract_all reads
        # the field from visual_diff.json instead of re-deriving from
        # the page index (e.g. f"diff-page-{idx+1:02d}.png").
        out_dir = _build_synthetic_out_dir(
            self.tmpdir / "vd",
            page_rects=[[(50, 60, 30, 20)]],
            delta_filenames=["diff-page-99.png"],
        )
        payload = extract_all(out_dir, min_area_px=10)
        self.assertEqual(
            payload["pages"][0]["delta_png"], "diff-page-99.png",
        )
        self.assertEqual(len(payload["pages"][0]["bboxes"]), 1)

    def test_overlay_writes_png_with_correct_dimensions(self) -> None:
        # Create a 400x300 plain-white DSL page and call write_overlay_png
        # with one bbox at (10, 20, 30, 40). The output PNG should be RGBA,
        # same dimensions, with at least one fully-red pixel on the outline.
        src = self.tmpdir / "src.png"
        dst = self.tmpdir / "out.png"
        Image.new("RGBA", (400, 300), (255, 255, 255, 255)).save(src, "PNG")
        write_overlay_png(src, [{
            "x_px": 10, "y_px": 20, "w_px": 30, "h_px": 40,
        }], dst)
        with Image.open(dst) as out_img:
            self.assertEqual(out_img.mode, "RGBA")
            self.assertEqual(out_img.size, (400, 300))
            # Outline must contain a fully-saturated red pixel somewhere
            # within the rectangle's bounding box.
            found_red = False
            for px in range(10, 41):
                for py in range(20, 61):
                    if out_img.getpixel((px, py)) == (255, 0, 0, 255):
                        found_red = True
                        break
                if found_red:
                    break
            self.assertTrue(found_red, "no red outline pixel found in overlay")

    def test_extract_all_overlay_off_by_default(self) -> None:
        out_dir = _build_synthetic_out_dir(
            self.tmpdir / "vd",
            page_rects=[[(50, 60, 30, 20)]],
            with_dsl_pngs=True,
        )
        extract_all(out_dir, min_area_px=10)  # overlay_out=False
        overlay = out_dir / "diff-page-01-overlay.png"
        self.assertFalse(overlay.exists())

    def test_extract_all_overlay_on_creates_files(self) -> None:
        out_dir = _build_synthetic_out_dir(
            self.tmpdir / "vd",
            page_rects=[
                [(50, 60, 30, 20)],
                [(20, 30, 40, 40)],
            ],
            with_dsl_pngs=True,
        )
        extract_all(out_dir, min_area_px=10, overlay_out=True)
        for n in (1, 2):
            overlay = out_dir / f"diff-page-{n:02d}-overlay.png"
            self.assertTrue(overlay.exists(), f"missing {overlay}")
            # Dimensions match the source dsl page
            with Image.open(overlay) as im:
                self.assertEqual(im.size, (200, 200))

    def test_extract_all_schema_keys(self) -> None:
        out_dir = _build_synthetic_out_dir(
            self.tmpdir / "vd", page_rects=[[(50, 60, 30, 20)]],
        )
        payload = extract_all(out_dir, min_area_px=10)
        # Top-level keys (after _strip_internal):
        write_json(payload, self.tmpdir / "out.json")
        clean = json.loads((self.tmpdir / "out.json").read_text())
        self.assertEqual(set(clean.keys()), {"dpi", "template_slug", "pages"})
        page = clean["pages"][0]
        self.assertEqual(set(page.keys()), {"page", "delta_png", "bboxes"})
        bbox = page["bboxes"][0]
        self.assertEqual(set(bbox.keys()), {
            "bbox_px", "bbox_mm", "area_px", "mismatch_pct_in_bbox",
            "attributed_slot", "attribution_overlap_pct",
            "attribution_candidates",
        })
        self.assertEqual(set(bbox["bbox_px"].keys()), {"x", "y", "w", "h"})
        self.assertEqual(set(bbox["bbox_mm"].keys()), {"x", "y", "w", "h"})


class VisualDiffWiringTests(unittest.TestCase):
    """Tests that tools/visual_diff.py's --extract-bboxes flag merges the
    extractor's per-page bboxes into visual_diff.json without breaking the
    existing schema (Issue #36 task 9)."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="vd_wiring_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_visual_diff_no_flag_default(self) -> None:
        # Import the visual_diff module + parse a minimal arg list; assert
        # extract_bboxes is False by default and template_slug is None.
        import visual_diff  # noqa: E402 — sys.path was prepped at module load
        ap = visual_diff.main.__wrapped__ if hasattr(visual_diff.main, "__wrapped__") else None
        _ = ap  # not used; we inspect via argparse directly below
        # Smoke: --help should mention extract-bboxes
        # (We don't run main() — that would require scribus.)
        # Instead, instantiate the parser the same way main() does:
        # since visual_diff.main doesn't expose its parser, we do a
        # subprocess --help check.
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "visual_diff.py"), "--help"],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("--extract-bboxes", result.stdout)
        self.assertIn("--template-slug", result.stdout)

    def test_merge_function_adds_bboxes_field(self) -> None:
        # Synthesise a minimal visual_diff output + delta PNG, then call
        # the merge helper directly. Verify pages[0]["bboxes"] is now
        # populated and existing keys are preserved.
        _draw_delta(self.tmpdir / "diff-page-01.png", (200, 200),
                    [(50, 60, 30, 20)])
        vd = {
            "dpi": 96,
            "pages": [{
                "page": 0,
                "delta_png": "diff-page-01.png",
                "mismatch_pixels": 600,
                "total_pixels": 40000,
            }],
        }
        (self.tmpdir / "visual_diff.json").write_text(
            json.dumps(vd), encoding="utf-8",
        )
        import visual_diff  # noqa: E402
        visual_diff._merge_bboxes_into_visual_diff(self.tmpdir, None)
        merged = json.loads(
            (self.tmpdir / "visual_diff.json").read_text(encoding="utf-8"),
        )
        # Existing keys preserved
        self.assertEqual(merged["pages"][0]["page"], 0)
        self.assertEqual(merged["pages"][0]["delta_png"], "diff-page-01.png")
        self.assertEqual(merged["pages"][0]["mismatch_pixels"], 600)
        # New bboxes field present and non-empty
        self.assertIsInstance(merged["pages"][0]["bboxes"], list)
        self.assertGreaterEqual(len(merged["pages"][0]["bboxes"]), 1)
        # Standalone diff_bboxes.json also written
        self.assertTrue((self.tmpdir / "diff_bboxes.json").exists())

    def test_merge_unknown_template_slug_warns_no_raise(self) -> None:
        # Template slug pointing at a non-existent template emits a warning
        # internally but still completes successfully; bboxes are written
        # with attributed_slot=None.
        _draw_delta(self.tmpdir / "diff-page-01.png", (200, 200),
                    [(50, 60, 30, 20)])
        vd = {
            "dpi": 96,
            "pages": [{
                "page": 0,
                "delta_png": "diff-page-01.png",
            }],
        }
        (self.tmpdir / "visual_diff.json").write_text(
            json.dumps(vd), encoding="utf-8",
        )
        import visual_diff  # noqa: E402
        # Should not raise; subprocess stderr will contain the warning but
        # _run() only raises on non-zero returncode.
        visual_diff._merge_bboxes_into_visual_diff(
            self.tmpdir, "definitely-does-not-exist",
        )
        merged = json.loads(
            (self.tmpdir / "visual_diff.json").read_text(encoding="utf-8"),
        )
        for bbox in merged["pages"][0]["bboxes"]:
            self.assertIsNone(bbox["attributed_slot"])


_INTEGRATION_REQUIRES = (
    shutil.which("scribus") is not None
    and shutil.which("pdftoppm") is not None
    and shutil.which("convert") is not None
)


@unittest.skipUnless(
    _INTEGRATION_REQUIRES,
    "integration test requires scribus + pdftoppm + ImageMagick on PATH",
)
class DiffBBoxIntegrationTests(unittest.TestCase):
    """End-to-end test against the postkarte-a6-kampagne fixture.

    Slow — runs scribus + pdftoppm + ImageMagick `compare` once in
    ``setUpClass`` to produce a real ``visual_diff.py`` output directory,
    then exercises the extractor against it. Per Issue #36 task 8.
    """

    tmpdir: Path
    vd_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="diff_bbox_integration_"))
        cls.vd_dir = cls.tmpdir / "vd"
        template_dir = ROOT / "templates" / "postkarte-a6-kampagne"
        subprocess.run(
            [
                sys.executable, str(ROOT / "tools" / "visual_diff.py"),
                str(template_dir / "template.sla"),
                "--baseline", str(template_dir / "baseline.pdf"),
                "--tolerance", str(template_dir / "diff.yml"),
                "--ci",
                "--out", str(cls.vd_dir),
            ],
            check=False,  # exits 1 on tolerance violation; artifacts still written
            capture_output=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_runs_against_real_output_dir_writes_json(self) -> None:
        rc = diff_bbox_extract.main([
            str(self.vd_dir),
            "--template-slug", "postkarte-a6-kampagne",
        ])
        self.assertEqual(rc, 0)
        json_path = self.vd_dir / "diff_bboxes.json"
        self.assertTrue(json_path.exists())
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(set(payload.keys()), {"dpi", "template_slug", "pages"})
        # Page count matches visual_diff.json's pages length
        vd = json.loads((self.vd_dir / "visual_diff.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["pages"]), len(vd["pages"]))

    def test_deterministic_on_real_dir(self) -> None:
        path_a = self.tmpdir / "a.json"
        path_b = self.tmpdir / "b.json"
        diff_bbox_extract.main([
            str(self.vd_dir),
            "--template-slug", "postkarte-a6-kampagne",
            "--json-out", str(path_a),
        ])
        diff_bbox_extract.main([
            str(self.vd_dir),
            "--template-slug", "postkarte-a6-kampagne",
            "--json-out", str(path_b),
        ])
        self.assertEqual(
            path_a.read_bytes(), path_b.read_bytes(),
            "Real-fixture diff_bboxes.json must be byte-identical across runs",
        )

    def test_overlay_files_produced(self) -> None:
        diff_bbox_extract.main([
            str(self.vd_dir),
            "--template-slug", "postkarte-a6-kampagne",
            "--overlay-out",
        ])
        self.assertTrue((self.vd_dir / "diff-page-01-overlay.png").exists())
        self.assertTrue((self.vd_dir / "diff-page-02-overlay.png").exists())

    def test_at_least_one_attributed_bbox(self) -> None:
        diff_bbox_extract.main([
            str(self.vd_dir),
            "--template-slug", "postkarte-a6-kampagne",
        ])
        payload = json.loads(
            (self.vd_dir / "diff_bboxes.json").read_text(encoding="utf-8"),
        )
        attributed = [
            b for p in payload["pages"]
            for b in p["bboxes"]
            if b["attributed_slot"] is not None
        ]
        self.assertGreater(
            len(attributed), 0,
            "expected at least one attributed bbox on postkarte-a6-kampagne",
        )


if __name__ == "__main__":
    unittest.main()
