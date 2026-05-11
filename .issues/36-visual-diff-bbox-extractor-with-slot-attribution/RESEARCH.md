# RESEARCH — Issue 36: Visual-diff bbox extractor with slot attribution

**Confidence: HIGH.** Three parallel forks converged on the algorithm and
attribution model; one important divergence (cv2 vs. ImageMagick for
connected-components) needs an explicit planner decision. Five corrections
to the original ISSUE.md surfaced — most consequential: ImageMagick's delta
PNG is **red-on-white RGBA**, not grayscale as the issue body claimed.

Sub-reports: [research/codebase.md](research/codebase.md) ·
[research/ecosystem.md](research/ecosystem.md) ·
[research/pitfalls.md](research/pitfalls.md)

---

## User Constraints

None in CONTEXT.md. Repo-wide constraints from prior issues + CLAUDE.md:

- **Tests use `unittest.TestCase`**, not pytest. Run via
  `python3 -m unittest discover tools/sla_lib/tests` (or directly).
  Pytest is installed but not idiomatic.
- **Strict mode philosophy** carries over from issue #35 / issue #2:
  unknown inputs should raise loudly, not silently no-op.
- **Determinism** is a load-bearing repo property — every artifact in
  `templates/` is SHA-pinned via `previews_for_sla:`. Output JSON must
  be byte-identical for byte-identical input.

---

## Summary

Build `tools/diff_bbox_extract.py`, a post-processor on
`tools/visual_diff.py`'s existing output dir. It reads each
`diff-page-NN.png` (the ImageMagick `compare` delta) and emits
`diff_bboxes.json` listing each cluster of mismatched pixels as
`{page, bbox_px, bbox_mm, mismatch_px, mismatch_pct_in_bbox,
attributed_slot, attribution_overlap_pct, attribution_candidates}`.

Three architectural decisions for the planner:

1. **Connected-components implementation — open question (default: ImageMagick).**
   The ecosystem fork recommends `opencv-python-headless==4.13.0.92` + `numpy==2.4.4`
   (+ ~51 MB image growth, byte-deterministic, clean API).
   The pitfalls fork found that **ImageMagick 7.1.1 is already installed and
   ships `-connected-components 8 -define connected-components:verbose=true`**,
   which prints parseable bbox lines (`id: WxH+x+y centroid area mean-color`).
   Recommended default: **ImageMagick**, because (a) zero new deps, (b) the
   repo already shells out to IM for `compare` + `montage` + `convert -crop`,
   (c) text-format output is stable across IM versions. Fall back to cv2 only
   if IM's output format proves unstable.

2. **Slot attribution metric — `coverage_of_diff_inside_slot`, not raw IoU.**
   Both ecosystem and pitfalls forks independently flagged this. A 5 mm²
   portrait shift inside a 50×70 mm slot has IoU ≈ 0.001 (looks like no
   match) but `area_intersect / area_diff_bbox` = 1.0 (correct attribution).
   Tie-break among slots with coverage ≥ threshold: prefer the slot with
   smaller area (more specific attribution; stops headline drifts being
   attributed to band-polygons underneath). Emit `attribution_candidates`
   list with top-3 when confidence is in the 50–80% suspicion zone.

3. **Threshold target the actual delta PNG format, not the issue body's claim.**
   Real artifacts at `build/validation/postkarte-a6-kampagne/diff-page-01.png`
   are mode **RGBA** with mismatched pixels rendered as `(199, 23, 35, 255)`
   (IM7 default `-highlight-color red`). Matched pixels are NOT white — they
   are the baseline *lightened by alpha overlay* (luminance ~220). The
   naïve "threshold at 128 of `.convert('L')`" classifies most of the page
   as mismatch. Use threshold ~200 on red channel, OR check IM's
   `mean-color` column directly when using the connected-components path.

**Out of scope (confirmed across all three forks):** auto-generating
`diff.yml` per_region blocks (separate follow-up), vision-model invocation
on the cropped bboxes (consumed by `visual_review.py` later), replacing
visual_diff.py's composite/montage outputs (those stay), rewriting the
diff pixel arithmetic.

**Recommended ordering:** ship the standalone extractor first
(`tools/diff_bbox_extract.py` + tests on synthetic fixtures), then add the
`visual_diff.py --extract-bboxes` flag wiring. That way the extractor is
testable without touching the slower visual_diff.py path.

---

## Codebase Analysis

### Anatomy of `tools/visual_diff.py`

- CLI (visual_diff.py:argparse): `<template.sla> --baseline <pdf> --tolerance <yml> --dpi <int> --out <dir>` + `--ci` shortcut for `--dpi 96`
- `TemplateTolerance` dataclass (visual_diff.py:42-83): `max_pixel_mismatch_pct`, `fuzz_pct`, `per_page` dict, `per_region` list with `bbox_mm:{x,y,w,h}`
- `PageResult` dataclass (visual_diff.py:86-97): per-page result with `page_index`, `mismatch_pixels`, `total_pixels`, `mismatch_pct`, `threshold_pct`, `fuzz_pct`, `composite`, `delta_png`, `pass_`, `region_results`
- Output files in `out/`:
  - `baseline-page-N.png` — **variable-padded** (1-digit for ≤9-page docs, 2-digit otherwise)
  - `dsl-page-N.png` — same padding as baseline
  - `diff-page-NN.png` — **always 2-digit, zero-padded** (hardcoded `:02d` at visual_diff.py:231)
  - `composite-page-NN.png` — 2-digit
  - `region-page-NN-X-Y.png` — per-region crops
  - `visual_diff.json` — includes `dpi` field at the top level (visual_diff.py:287)
  - `visual_diff.html` — HTML review index
- ImageMagick commands used verbatim (read these as authoritative for our delta PNG format):
  - `compare -metric AE -fuzz <pct>% baseline.png dsl.png diff.png` (returns AE on stderr)
  - `montage baseline.png dsl.png diff.png -tile 3x1 -geometry +5+5 composite.png`
  - `convert input.png -crop <W>x<H>+<X>+<Y> region.png`

### Slot-bbox API — `tools/sla_lib/builder/bbox.py`

<interfaces>
def rotated_bbox(x: float, y: float, w: float, h: float, deg: float
                ) -> tuple[float, float, float, float]:
    """Axis-aligned bbox of a rotated rectangle. Returns (x, y, w, h) mm."""

def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]:
    """Page-local mm bbox of a built-DSL frame, honouring anchor + rotation.
    Returns (min_x, min_y, max_x, max_y) — NOT (x, y, w, h). Callers must convert.
    Returns None for primitives without spatial extent.
    NOTE: ignores xpos_pt/width_pt verbatim overrides (bbox.py:13-16)."""
</interfaces>

### Attribution pattern — already used by `audit_alignment.py`

```python
# audit_alignment.py:240-254 — the load+iterate idiom
mod = load_build_module(slug)
doc = mod.build_preview() or mod.build_doc()
for page in doc.pages:
    if page.is_master:
        continue
    for item in page.items:
        if not item.anname:
            continue
        bbox = frame_bbox_mm(item, page)  # → (min_x, min_y, max_x, max_y)
        slots[item.anname] = bbox
```

This is the exact mechanism the bbox extractor's attribution step needs —
no new helper required, just import and reuse.

### `diff.yml` schema (existing, not yet used in templates today)

```yaml
visual_diff:
  max_pixel_mismatch_pct: 1.0
  fuzz_pct: 25.0
  per_page:
    - page: 0
      max_pixel_mismatch_pct: 0.5
      fuzz_pct: 30
  per_region:
    - page: 1
      bbox_mm: { x: 10, y: 100, w: 50, h: 60 }
      max_pixel_mismatch_pct: 5.0
      fuzz_pct: 30
```

The bbox extractor's output must be paste-compatible into `per_region:` —
keys `page`, `bbox_mm:{x,y,w,h}`, `max_pixel_mismatch_pct`, `fuzz_pct`.

### Integration test fixture

`templates/postkarte-a6-kampagne/` — 191 KB SLA, 666 KB baseline, 2
A6 pages. Smallest viable target with `template.sla` + `baseline.pdf`
both committed. Real diff PNG exists at
`build/validation/postkarte-a6-kampagne/diff-page-01.png`.

**Tests do NOT run visual_diff.py in CI** (the codebase fork confirmed
this — visual_diff is local-only via `bin/validate`). The integration
test should use **synthetic fixture diff PNGs** committed to
`tests/fixtures/`, not invoke the real pipeline.

### Test conventions

- `unittest.TestCase` (not pytest), `tempfile.mkdtemp()` + `try/finally: shutil.rmtree`
- No `conftest.py`, no `pytest.ini`
- Import bootstrap: `sys.path.insert(0, ROOT/"tools")` at top of test files
- Run: `python3 -m unittest discover tools/sla_lib/tests` is the canonical entry; individual files via `python3 -m unittest tests.unit.test_diff_bbox`

### Branch isolation

`git log origin/main..HEAD` = 1 commit (ISSUE.md). **Issue #35's IDML
converter is NOT on this branch.** This issue is independent — does not
depend on #35.

---

## Standard Stack

| Component | Version | License | Role | Confidence |
|---|---|---|---|---|
| **ImageMagick 7.1.1** | installed | Apache-2.0 (IM license) | Connected-components labelling via `-connected-components 8 -define connected-components:verbose=true` | HIGH — recommended path |
| **Pillow 12.2.0** | installed | MIT-CMU-style | Red-overlay PNG generation (`ImageDraw.rectangle`) + delta PNG mode inspection | HIGH |
| PyYAML | installed | MIT | diff.yml parsing (already used by visual_diff.py) | HIGH |
| (alternative) opencv-python-headless 4.13.0.92 | NOT installed | Apache-2.0 | findContours + dilate path | MEDIUM — fallback if IM proves insufficient |
| (alternative) numpy 2.4.4 | NOT installed | BSD-3 | accompanies cv2 | MEDIUM — fallback only |

**Recommended path:** ImageMagick. Zero new dependencies, the repo already
shells out to IM for compare/montage. The text output format is:

```
Objects (id: bounding-box centroid area mean-color):
  0: 1240x1754+0+0 619.5,876.7 2174960 srgba(255,255,255,1)    ← background, drop
  1: 12x18+340+512  345.5,520.5 216    srgba(199,23,35,1)       ← real diff
```

Parse with a simple regex; sort by `(page, y, x, w, h)` for determinism;
drop the always-present id-0 background object (full-page area, white).

---

## Don't-Hand-Roll List

- ❌ Connected-components labelling — ImageMagick already does it
- ❌ PNG decode — IM does it; or Pillow if we need mode/luminance probe
- ❌ Slot-bbox computation — `frame_bbox_mm` already exists
- ❌ Template loading — `audit_alignment.load_build_module` already does it
- ❌ IoU math — write inline (5 lines, no lib)
- ❌ JSON output — `json.dumps(sort_keys=True, indent=2)`
- ❌ A new test runner — `unittest` is the repo's idiom

---

## Architecture Patterns

### Algorithm (recommended path — ImageMagick connected-components)

```python
# Per page:
# 1. Detect non-white pixels in delta PNG via threshold:
#    convert diff-page-NN.png -threshold 90% -negate mask.png
#    (or use -fuzz around white directly)
# 2. Connected-components labelling:
#    convert mask.png -define connected-components:verbose=true \
#        -connected-components 8 -auto-level info:cc.txt
# 3. Parse output regex per line: r"^\s*(\d+):\s+(\d+)x(\d+)\+(\d+)\+(\d+)\s+([\d.]+),([\d.]+)\s+(\d+)\s+(.+)$"
#    Drop id=0 (background object — full page, white/near-white mean-color)
#    Drop area < min_area_px (default 100; absorbs page-edge AA noise)
# 4. Convert pixel bbox → mm bbox:
#    mm_per_px = 25.4 / dpi   (DPI read from visual_diff.json)
#    bbox_mm = {x: x_px * mm_per_px, y: y_px * mm_per_px, w: w_px * mm_per_px, h: h_px * mm_per_px}
#    Round to 0.1 mm for determinism.
# 5. For each bbox: cross-reference against slot bboxes for the page
#    (load build_module → iterate page.items with anname → frame_bbox_mm)
# 6. Attribution = highest coverage_of_diff_inside_slot ≥ threshold (0.5 default).
#    Tie-break: smaller slot area first.
#    Emit top-3 candidates if confidence is in [0.5, 0.8].
# 7. Output JSON, sorted by (page, y_mm, x_mm), with sort_keys=True.
```

### Algorithm (fallback — cv2 + numpy)

Used only if IM's connected-components proves unstable across versions.
Adds 51 MB to the container image; requires Dockerfile change:

```python
import cv2
delta = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
# Real delta is red-on-white-with-alpha. Convert RGBA→L manually,
# or split channels and use red channel (more discriminative).
inverted = cv2.bitwise_not(delta)
_, mask = cv2.threshold(inverted, 50, 255, cv2.THRESH_BINARY)
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
mask = cv2.dilate(mask, kernel)
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
bboxes = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) >= 100]
```

### Slot attribution math

```python
def coverage_of_diff_inside_slot(diff_bbox, slot_bbox):
    """How much of the diff bbox lies inside the slot bbox.
    Better than IoU when slot is much larger than diff."""
    x_overlap = max(0, min(diff_bbox.x + diff_bbox.w, slot_bbox.x + slot_bbox.w)
                      - max(diff_bbox.x, slot_bbox.x))
    y_overlap = max(0, min(diff_bbox.y + diff_bbox.h, slot_bbox.y + slot_bbox.h)
                      - max(diff_bbox.y, slot_bbox.y))
    intersect = x_overlap * y_overlap
    diff_area = diff_bbox.w * diff_bbox.h
    return intersect / diff_area if diff_area > 0 else 0.0

# For each diff_bbox:
#   candidates = [(slot_name, coverage, slot_area)
#                  for slot_name, slot_bbox in slots.items()
#                  if coverage_of_diff_inside_slot(diff_bbox, slot_bbox) >= 0.5]
#   candidates.sort(key=lambda x: (-x[1], x[2]))   # high coverage first, small slot first
#   attributed = candidates[0] if candidates else (None, 0.0, None)
```

### `visual_diff.json` merge schema

```jsonc
// Existing keys preserved; add bboxes under per-page
{
  "dpi": 96,
  "pages": [
    {
      "page_index": 0,
      "mismatch_pixels": 1234,
      "...": "...",
      "delta_png": "diff-page-01.png",
      "bboxes": [                               // ← NEW (only when --extract-bboxes)
        {
          "bbox_px": {"x": 49, "y": 182, "w": 152, "h": 112},
          "bbox_mm": {"x": 12.3, "y": 45.6, "w": 38.0, "h": 28.0},
          "mismatch_px": 1842,
          "mismatch_pct_in_bbox": 8.3,
          "attributed_slot": "P1 Kandidat-Portrait",
          "attribution_overlap_pct": 92.0,
          "attribution_candidates": [
            {"slot": "P1 Kandidat-Portrait", "coverage_pct": 92.0, "slot_area_mm2": 8700},
            {"slot": "P1 Top-Band", "coverage_pct": 12.0, "slot_area_mm2": 3255}
          ]
        }
      ]
    }
  ]
}
```

---

## Common Pitfalls

### CRITICAL — must be handled in v1

| Pitfall | What goes wrong | Mitigation |
|---|---|---|
| **Delta PNG is RGBA red-on-white, not grayscale** | `convert('L')` + threshold-at-128 classifies most pixels as mismatch | Use threshold ~200 on red channel, or use IM connected-components which understands the mean-color column directly |
| **id=0 background object always emitted** | Without filtering, every bbox list includes the full page | Drop by area-ratio (≥80% of page) or by mean-color near-white |
| **Page-edge AA artifacts** | pdftoppm anti-aliasing creates 1×11 / 11×1 strips at corners | min_area_px default 100; documented in defaults, overridable via diff.yml |
| **Page-numbering split 3 ways** | baseline-page is 1-digit for ≤9 pages, diff-page is always 2-digit, JSON page_index is 0-indexed | **Use `visual_diff.json["pages"][i]["delta_png"]` for the file name; don't re-derive from page index** |
| **`frame_bbox_mm` ignores pt overrides** | If a template uses `xpos_pt` / `width_pt`, attribution will be off | Document limitation; emit `attribution_candidates` so reviewer sees alternatives. Issue #35-imported templates may hit this — note in the docstring. |
| **Stacked slots — band polygon + text frame on top** | Pure max-IoU attributes drift to band underneath | Use `coverage_of_diff_inside_slot` + tie-break by smaller area |
| **Determinism — three fixes needed** | findContours / IM output can subtly reorder; FP px→mm drifts | (1) Sort bboxes by `(page, y, x, w, h)`; (2) round mm to 0.1; (3) `json.dumps(sort_keys=True)` |

### LIKELY — design-decision territory

- **cv2 vs IM**: see decision #1 above. Default IM, fall back cv2.
- **Threshold/dilate defaults**: starting points `threshold=200`, `min_area_px=100`, `dilate_px=3` (IM kernel). These are **flag-exposed** and overridable via diff.yml `visual_diff.bbox.{threshold, min_area_px, dilate_px}` block. Iterate on a real template before locking.
- **Attribution confidence threshold**: 0.5 covers the common cases (a diff bbox is at least half inside the slot it represents). 0.8 may be too strict if slot bboxes are tighter than visual extent (e.g. text with descenders below the frame).

### Strict-mode UX

If a template's `meta.yml` declares no slots (`slots: null`) or the
build module fails to load, the bbox extractor should:
- Still emit bbox JSON without attribution (set `attributed_slot: null`)
- Log a warning, not raise — this is a post-processor, not a gate

But: if the delta PNG itself is missing or unreadable, raise loudly.

---

## Environment Availability

| Component | Status | Notes |
|---|---|---|
| Python 3.13 | ✅ in container | |
| Pillow 12.2.0 | ✅ in container | mode probe, red-overlay PNG drawing |
| ImageMagick 7.1.1 | ✅ in container | connected-components labelling — **the recommended path** |
| cv2 + numpy | ❌ not in container | fallback path only; ~51 MB Dockerfile addition if needed |
| pytest | installed but not idiomatic | Use `unittest` |
| Real delta PNG for fixture | ✅ `build/validation/postkarte-a6-kampagne/diff-page-01.png` | Verified mode `RGBA`, mismatch=(199,23,35,255) |
| Slot-bbox helper | ✅ `tools/sla_lib/builder/bbox.py` | `frame_bbox_mm` returns 4-tuple (min_x, min_y, max_x, max_y) — convert |
| Template loading helper | ✅ `tools/audit_alignment.load_build_module` | Reuse verbatim |

---

## Project Constraints

- **Worktree:** `/root/workspace/.worktrees/36-visual-diff-bbox-extractor-with-slot-attribution`
- **Branch:** `issue/36-visual-diff-bbox-extractor-with-slot-attribution` from `origin/main`
- **GitHub mirror:** https://github.com/GrueneAT/vorlagen/issues/73
- **Commit format:** `36: <type>(<scope>): <subject>` (conventional, id-prefixed) per `.issues/config.yaml`
- **Independent of issue #35** — no shared code, no shared branch
- **Tests use `unittest`** — no pytest dependence introduced

---

## Open Questions for Plan Stage

The forks converged on most decisions. Three remain for the planner:

1. **Connected-components: ImageMagick or cv2?**
   **Recommended default: ImageMagick.** Zero new deps. Falls back to cv2
   only if IM's text-output format proves unstable across versions
   we'll see in production.

2. **Threshold for non-white pixels in red-on-white RGBA delta.**
   **Recommended default: red channel ≥ 200, or equivalently `convert -threshold 90% -negate`.**
   Validate empirically against `build/validation/postkarte-a6-kampagne/diff-page-01.png`
   before locking.

3. **`visual_diff.py --extract-bboxes` flag wiring.**
   Either (a) `visual_diff.py` shells out to `diff_bbox_extract.py` after
   the page loop, or (b) the extractor is purely standalone and the user
   runs it as a second step. **Recommended default: (a) optional flag**,
   so the JSON ends up in one file. The extractor stays standalone-runnable
   for re-analysis of existing dirs.

---

## Sources

| Source | Confidence |
|---|---|
| `tools/visual_diff.py` (read in full) | HIGH |
| `tools/sla_lib/builder/bbox.py`, `tools/audit_alignment.py` | HIGH |
| `tools/sla_diff.py` (confirmed not relevant; structural diff, no raster) | HIGH |
| `build/validation/postkarte-a6-kampagne/diff-page-01.png` (real artifact, mode probed) | HIGH |
| [ImageMagick Connected Components Labeling](https://imagemagick.org/script/connected-components.php) | HIGH |
| [ImageMagick connected-components discussion #5163](https://github.com/ImageMagick/ImageMagick/discussions/5163) | MEDIUM |
| [Pillow 12.2 Image module docs](https://pillow.readthedocs.io/en/stable/reference/Image.html) | HIGH |
| [PyImageSearch IoU tutorial](https://pyimagesearch.com/2016/11/07/intersection-over-union-iou-for-object-detection/) | MEDIUM |
| [PyPI: opencv-python-headless 4.13.0.92](https://pypi.org/project/opencv-python-headless/) | HIGH — fallback path only |
| [OpenCV imgproc shape docs (4.x)](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html) | HIGH — fallback path only |
| [ImageMagick non-determinism discussion #3047](https://github.com/ImageMagick/ImageMagick/discussions/3047) | MEDIUM |

---

**Next:** `/issue:plan 36-visual-diff-bbox-extractor-with-slot-attribution`
