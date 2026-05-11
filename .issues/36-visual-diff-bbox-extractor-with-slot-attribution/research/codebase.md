# Codebase Research — Issue #36 (visual-diff bbox extractor)

## Summary

- `tools/visual_diff.py` (366 LOC) already produces every raster artifact the new bbox extractor needs (`diff-page-NN.png`, `visual_diff.json` with `dpi` recorded). No rewrite required; the new tool is a pure post-processor.
- The slot-bbox helper (`tools/sla_lib/builder/bbox.py::frame_bbox_mm`) and the load-build-module idiom (`tools/audit_alignment.py::audit_template`) together already implement the exact `{anname: bbox_mm}` pattern the slot-attribution step needs — no new infrastructure, just a thin wrapper.
- `tools/sla_diff.py` is purely XML/structural — irrelevant to this issue beyond "do not touch".
- `tools/visual_review.py` does NOT currently invoke `visual_diff.py`; the integration hook called out as "out of scope" in ISSUE.md genuinely does not exist yet.
- **`cv2`, `numpy`, and `scikit-image` are NOT installed** in the Claude container or in CI. Only Pillow 12.2.0 is available. The ISSUE.md examples (`cv2.threshold`, `cv2.findContours`, `cv2.boundingRect`) are aspirational — the planner must decide whether to (a) add `opencv-python-headless` + `numpy` as new deps in `Dockerfile.claude` and the CI install step in `.github/workflows/pages.yml`, or (b) implement the morphology + connected-components pipeline with Pillow alone (slower but no new deps).
- `visual_diff.py` is **not run in CI today** (only `bin/validate` invokes it locally). So the bbox extractor needs unit tests that don't require Scribus/pdftoppm; integration tests against committed fixtures (or generated synthetic PNGs) are the practical regression bar.
- CI test runner is `python3 -m unittest discover tools/sla_lib/tests` (NOT pytest). Tests are `unittest.TestCase` subclasses in `tools/sla_lib/tests/test_*.py`.
- Issue #35 (IDML→DSL converter) is on a separate branch; **this worktree's branch (`issue/36-…`) is exactly 1 commit ahead of `origin/main`** (the ISSUE.md creation commit), so none of #35's code is present. Confirmed via `git log origin/main..HEAD`.

## visual_diff.py Anatomy

### CLI (visual_diff.py:344-362)

```
python3 tools/visual_diff.py <template_sla> \
    --baseline <baseline.pdf> \
    [--tolerance <diff.yml>] \
    [--dpi 150 | --ci] \
    [--out build/visual_diff/]
```

- `--ci` is a shortcut for `--dpi 96` (visual_diff.py:353,358).
- Exit 0 if every page (and region) is within tolerance, 1 otherwise (visual_diff.py:20-21, 362).
- Default `--out` = `build/visual_diff/` (visual_diff.py:355).

### Output filenames (all relative to `--out`)

| Filename pattern | Source | Notes |
|---|---|---|
| `dsl.pdf` | visual_diff.py:219 | DSL-rendered PDF |
| `baseline-page-<NN>.png` | visual_diff.py:221 via rasterise() | `pdftoppm` zero-padded to 2 digits when ≥10 pages |
| `dsl-page-<NN>.png` | visual_diff.py:222 | same |
| `diff-page-<NN>.png` | visual_diff.py:231 | **THIS IS THE BBOX EXTRACTOR'S INPUT** — 1-indexed, zero-padded to 2 digits (`f"diff-page-{idx+1:02d}.png"`) |
| `composite-page-<NN>.png` | visual_diff.py:232 | 3-up montage baseline\|dsl\|diff |
| `region-page-<NN>-<X>-<Y>.png` | visual_diff.py:248 | per_region crop; X,Y are bbox_mm integer rounding |
| `<dsl|baseline>-page-NN.region_<x>_<y>_<w>x<h>.png` | visual_diff.py:211 | per_region crops of source rasters |
| `visual_diff.json` | visual_diff.py:307 | summary + per-page records |
| `visual_diff.html` | visual_diff.py:341 | review index |

### `TemplateTolerance` dataclass (visual_diff.py:42-83)

```python
@dataclass
class TemplateTolerance:
    max_pixel_mismatch_pct: float = 1.0      # global default
    fuzz_pct: float = 25.0                   # NOTE: load() at L73 falls back to 2.0 not 25.0 — inconsistency
    per_page: dict = {}                       # int -> {max_pixel_mismatch_pct?, fuzz_pct?}
    per_region: list = []                     # [{page, bbox_mm: {x,y,w,h}, max_pixel_mismatch_pct?, fuzz_pct?}]
```

- `load(path)` reads YAML under either top-level `visual_diff:` block OR root (visual_diff.py:63-64).
- Tolerance cascade: **template default → per_page override → per_region override** (page passes only if ALL regions pass; visual_diff.py:251,261-262).
- `for_page(idx)` returns `(threshold_pct, fuzz_pct)` per-page tuple (visual_diff.py:78-83).

### `PageResult` dataclass (visual_diff.py:86-97)

```python
page_index, mismatch_pixels, total_pixels, mismatch_pct,
threshold_pct, fuzz_pct, composite (str path), delta_png (str path),
pass_ (bool), region_results (list of dicts)
```

### visual_diff.json schema (visual_diff.py:284-306)

```json
{
  "template_sla": "...", "baseline_pdf": "...",
  "dpi": 96,                                  // <-- DPI IS recorded; needed for px→mm conversion
  "default_threshold_pct": 1.0,
  "default_fuzz_pct": 25.0,
  "pass": true,
  "pages": [
    {
      "page": 0,                              // 0-indexed
      "mismatch_pixels": 1842,
      "total_pixels": 8294400,
      "mismatch_pct": 0.0222,
      "threshold_pct": 1.0, "fuzz_pct": 25.0,
      "composite": "composite-page-01.png",   // 1-indexed in filename
      "delta_png": "diff-page-01.png",
      "pass": true,
      "regions": [
        { "bbox_mm": {...}, "mismatch_pixels": ..., "total_pixels": ...,
          "mismatch_pct": ..., "threshold_pct": ..., "fuzz_pct": ..., "pass": ... }
      ]
    }
  ]
}
```

### ImageMagick command lines (verbatim from code)

| Purpose | Command | Source |
|---|---|---|
| Per-page diff | `compare -metric AE -fuzz <fuzz_pct>% <baseline> <dsl> <diff_path>` | visual_diff.py:166-169 |
| Montage 3-up | `montage <baseline> <dsl> <diff> -tile 3x1 -geometry +4+4 <out>` | visual_diff.py:190-195 |
| Region crop | `convert <image> -crop <w_px>x<h_px>+<x_px>+<y_px> +repage <out>` | visual_diff.py:212 |
| Pixel count | `identify -format "%w %h" <baseline>` | visual_diff.py:182 |
| Raster | `pdftoppm -r <dpi> -png <pdf> <prefix>` | visual_diff.py:149 |
| DSL render | `xvfb-run -a --server-args=-screen\ 0\ 1024x768x24 scribus -g -ns -py tools/_export_pdf.py <sla_abs> <pdf_abs>` | visual_diff.py:132-138 |

### px↔mm conversion math (visual_diff.py:206)

```python
px_per_mm = dpi / 25.4         # e.g. 96/25.4 ≈ 3.78 px/mm
# Inverse for the new tool:
mm_per_px = 25.4 / dpi
```

The new extractor reads `dpi` from `visual_diff.json` (already written at L287) — no need to re-pass on the CLI.

### Diff PNG color convention

ImageMagick `compare` writes **mismatched pixels in red, matched pixels in white** by default — NOT "white = match, dark = mismatch" as the ISSUE.md context-section claims. The new tool should thresh the **non-white** (or, more precisely, the red channel + low brightness) regions. Verify empirically against a real `diff-page-NN.png` before locking the threshold.

## Slot-bbox API

<interfaces>
// From tools/sla_lib/builder/bbox.py
def rotated_bbox(
    x: float, y: float, w: float, h: float, deg: float,
) -> tuple[float, float, float, float]:
    """Axis-aligned bbox of a w×h rect rotated CCW by deg around top-left.
    Returns (min_x, min_y, max_x, max_y) in same units as inputs."""

def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]:
    """Page-local mm bbox of `item` on `page`, or None if no spatial extent
    (e.g. Run, ParaStyle).
    Returns (min_x, min_y, max_x, max_y) in mm — NOTE: this is (x0,y0,x1,y1),
    NOT (x,y,w,h). The ISSUE.md JSON example uses {x,y,w,h} so the new tool
    must convert: w = x1-x0, h = y1-y0.
    Honours anchor positioning + rotation_deg.
    LIMITATION: verbatim-pt overrides (xpos_pt/width_pt) NOT honoured;
    falls back to *_mm fields."""

// From tools/sla_lib/builder/document.py (relevant fields)
class Page:
    width_pt: float
    height_pt: float
    bleed_mm: float = 3.0
    margins_mm: tuple[float, float, float, float]  # L,R,T,B
    master_name: str
    items: list                       # primitives w/ x_mm, y_mm, w_mm, h_mm, anname
    own_page: int
    is_master: bool                   # MUST filter these out — see audit_alignment.py:241

class Document:
    pages: list[Page]
    masters: list[Page]
    facing_pages: bool
    def iter_all_primitives() -> Iterable  # walks doc + masters

PT_TO_MM = 25.4 / 72.0                 # for inverse conversion if needed
def mm_to_pt(value_mm: float) -> float

// From tools/sla_lib/builder/template_loader.py
def load_build_module(slug: str, root: Path = _REPO_ROOT):
    """Load templates/<slug>/build.py via importlib with unique module name
    (prevents sys.modules cross-contamination on multi-template iteration)."""
</interfaces>

## audit_alignment.py Pattern — the "load build.py → get anname bboxes" idiom

This is the **exact** pattern the bbox extractor's slot-attribution step must reuse. See audit_alignment.py:401-429.

```python
# 1. Load the template's build module
from sla_lib.builder.template_loader import load_build_module
mod = load_build_module(slug, root)

# 2. Build the document (prefer build_preview when available — has inline image bytes)
if hasattr(mod, "build_preview"):
    doc = mod.build_preview()
else:
    doc = mod.build_doc()

# 3. Walk pages + items, extract {anname: bbox_mm}
from sla_lib.builder.bbox import frame_bbox_mm
for idx, page in enumerate(doc.pages):
    if page.is_master:                      # SKIP masters (audit_alignment.py:241)
        continue
    for item in page.items:                 # FLAT list of primitives; blocks already expanded (document.py:128-131)
        an = getattr(item, "anname", "") or ""
        if not an:
            continue                        # skip unnamed frames
        bbox = frame_bbox_mm(item, page)    # returns (x0, y0, x1, y1) mm or None
        if bbox is None:
            continue                        # primitives without spatial extent (Run, ParaStyle)
        # Use `bbox` as the slot rectangle for IoU comparison with diff bboxes
```

**Caveats (must propagate into the extractor):**
- `frame_bbox_mm` returns `(min_x, min_y, max_x, max_y)`, not `(x, y, w, h)`. Document the conversion.
- Returns `None` for primitives without spatial extent (Run, ParaStyle, BrandRule references) — skip cleanly.
- Verbatim-pt overrides (`xpos_pt`/`width_pt`) NOT honoured. Known offenders in repo: "zeitung P9 Spread" and "unnamed page-12 image" (bbox.py:58-60). Not blocking today; widen if a future template uses overrides.
- Pages are 0-indexed in `doc.pages`; visual_diff filenames are 1-indexed. Mind the offset.

## diff.yml Schema

Documented in `docs/diff-tolerance.md` with this canonical example:

```yaml
visual_diff:
  max_pixel_mismatch_pct: 1.0      # global default
  fuzz_pct: 25                     # ImageMagick -fuzz
  per_page:
    - page: 0                      # 0-based
      max_pixel_mismatch_pct: 0.5
      fuzz_pct: 30
  per_region:                      # optional rectangular sub-regions in mm
    - page: 1
      bbox_mm: { x: 10, y: 100, w: 50, h: 60 }
      max_pixel_mismatch_pct: 5.0
      fuzz_pct: 30
```

**Real-world data: NO template currently uses `per_region:`.** All three committed `diff.yml` files (postkarte, plakat, zeitung) are minimal:

```yaml
# templates/postkarte-a6-kampagne/diff.yml (full file)
visual_diff:
  max_pixel_mismatch_pct: 1.0
  fuzz_pct: 5.0
```

The only test exercise of the `per_region:` shape is in `tools/sla_lib/tests/test_visual_diff.py:42-46`:

```yaml
per_region:
  - page: 1
    bbox_mm: { x: 10, y: 10, w: 50, h: 30 }
    max_pixel_mismatch_pct: 8
```

The new tool's emit-compatible JSON output (the `per_region:` seed-data path in the issue's acceptance criteria #5) MUST use this exact key shape: `{ page, bbox_mm: {x,y,w,h}, max_pixel_mismatch_pct, fuzz_pct }`.

## sla_diff.py — confirmed NOT raster

`tools/sla_diff.py` (1249 LOC) is purely an XML structural diff: parse → normalise (attribute order, ItemID renumber, float rounding, default-drop, page-local rebase) → emit per-element issues with severity. No pixel work. Listed in ISSUE.md as "do not duplicate"; the new bbox tool has zero overlap with it. (sla_diff.py:1-30)

## visual_review.py — current state

`tools/visual_review.py` (301 LOC, sonnet @ tools/visual_review.py:32-41) is a **multi-model orchestrator** that:

- Sends a template's `page-01.png` + a 4×2 grid of all 8 templates' hero PNGs to Codex / Gemini / Claude
- Writes `reviews/visual-qa-<slug>-iter-N.md`
- **Does NOT call visual_diff.py today** (grep confirms zero references). The "feed bboxes pre-cropped" idea in ISSUE.md is greenfield integration, which is out of scope per ISSUE.md L101-104.

Future integration would feed `diff_bboxes.json` + cropped overlays as additional `-i` images to `codex exec` / `gemini -p` (the existing tool already shells out exactly this way at visual_review.py:213-227).

## render_pipeline.py + bin/validate

- `tools/render_pipeline.py` (754 LOC): canonical "render template to PDF + PNG" entry point. Re-exports `render_sla_to_pdf` and `rasterise` from `visual_diff.py` (render_pipeline.py:39). The per-template pipeline (render_pipeline.py:6-21) goes: `build.py → render_sla_to_pdf → scrub PDF → pdftoppm → sla_diff (subprocess) → visual_diff (subprocess) → SHA-pin → copy to site/`.
- `bin/validate` (89 LOC bash): the local-only validation wrapper. **It is the only place `visual_diff.py` is invoked in the project (bin/validate:73-78).** CI does NOT run `bin/validate`.

```bash
# Pattern bin/validate uses for visual_diff (bin/validate:72-83)
if [ -f "${tdir}baseline.pdf" ] && [ -f "${tdir}diff.yml" ]; then
    python3 tools/visual_diff.py "${tdir}template.sla" \
        --baseline "${tdir}baseline.pdf" \
        --tolerance "${tdir}diff.yml" \
        --dpi "$DPI" \
        --out "$OUT_BASE/${tid}/"
fi
```

**CI status:** `.github/workflows/pages.yml` runs `python3 -m unittest discover tools/sla_lib/tests` (line 105) and `python3 tools/gallery_build.py` (line 80) — neither touches `visual_diff.py`. So the new bbox extractor has no CI regression target unless the planner adds one.

## Test Conventions

### Location & invocation

- All tests live under `tools/sla_lib/tests/test_*.py`. There is **no top-level `tests/` directory**.
- Tests are `unittest.TestCase` subclasses, NOT pytest functions (see `test_visual_diff.py:24,67`). Pytest is installed locally and *works* (`python3 -m pytest tools/sla_lib/tests/test_visual_diff.py` → 6 passed), but the canonical invocation is unittest discover.
- CI command: `python3 -m unittest discover tools/sla_lib/tests` (pages.yml:105).
- Manual single-file: `python3 -m unittest tools.sla_lib.tests.test_visual_diff` OR `python3 tools/sla_lib/tests/test_visual_diff.py`.

### conftest.py / fixtures

- No `conftest.py` anywhere in the repo.
- No `pytest.ini` / `pyproject.toml` / `tox.ini` / `setup.cfg`.
- Standard fixture pattern is `tempfile.mkdtemp()` + `try/finally: shutil.rmtree` (test_visual_diff.py:31,55) — NOT `tmp_path` (since there's no pytest config).

### Import bootstrap pattern (test_visual_diff.py:18-21)

```python
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import visual_diff as vd          # imports tools/visual_diff.py
```

The new test file should follow the same shape: insert `tools/` into `sys.path`, then `import diff_bbox_extract as dbe`.

### Image-comparison libraries in tests

- **Only Pillow** (PIL) is used by existing tests. Pinned to `12.2.0` for byte-deterministic library regen (Dockerfile.claude:66; pages.yml:55).
- `numpy`, `cv2`, `skimage` are NOT installed and NOT in any test.
- `tools/codex_image_gen.py` imports `PIL`; `test_codex_image_gen.py` uses it. That is the precedent for image-manipulation tests.

## Integration-test Fixture Candidates

Three templates have both `template.sla` and `baseline.pdf`:

| Template | SLA size | baseline.pdf size | Pages | Fit-for-integration-test? |
|---|---|---|---|---|
| `postkarte-a6-kampagne` | 191 KB | 666 KB | 2 (A6, two-sided) | **BEST** — smallest baseline, only 2 pages, byte-clean diff today |
| `plakat-a1-hochformat` | 228 KB | 747 KB | 1 (A1) | Single page; large pixel canvas at 150 dpi (~83 megapixels) |
| `zeitung-a4-grun` | 540 KB | 1.3 MB | 14 (A4) | Heavy — 14 pages × A4; do NOT use for unit tests |

**Recommendation:** Use `postkarte-a6-kampagne` as the canonical integration fixture (smallest, fastest, byte-clean). The fork should NOT actually re-run `visual_diff.py` end-to-end in tests (requires Scribus+pdftoppm and is slow); instead:

1. Either commit a tiny synthetic `diff-page-NN.png` + minimal `visual_diff.json` as a test fixture
2. Or generate one on the fly inside the test with Pillow (paint a few rectangles on a white canvas)

The build_doc / slot-bbox half can be unit-tested independently against `templates/postkarte-a6-kampagne/build.py::build_doc()` (loads in ~milliseconds, no Scribus).

## Issue #35 status

`git log origin/main..HEAD` in this worktree shows exactly one commit:

```
67e5c9e 36: docs(issues): create issue 36-visual-diff-bbox-extractor-with-slot-attribution
```

→ **None of issue #35's code is on this branch.** ISSUE.md L116-118 says #36 is independent of #35 — confirmed. The bbox extractor needs no upstream from #35; if #35 lands first, the bbox extractor still works against any template's existing baseline.

## File/Line Citations Index

- visual_diff CLI: tools/visual_diff.py:344-362
- visual_diff output filenames: tools/visual_diff.py:221-222, 231-232, 248
- visual_diff JSON schema: tools/visual_diff.py:284-306 (dpi at :287)
- TemplateTolerance: tools/visual_diff.py:42-83
- per_region iteration: tools/visual_diff.py:239-262
- ImageMagick command lines: tools/visual_diff.py:149, 166-169, 182, 190-195, 212
- px↔mm math: tools/visual_diff.py:206
- frame_bbox_mm: tools/sla_lib/builder/bbox.py:49-74
- rotated_bbox: tools/sla_lib/builder/bbox.py:30-46
- bbox.py limitation (xpos_pt overrides): tools/sla_lib/builder/bbox.py:14-19, 56-60
- audit pattern (build_doc → iterate pages → anname): tools/audit_alignment.py:240-254, 401-429
- load_build_module: tools/sla_lib/builder/template_loader.py:21-46
- Page/Document classes: tools/sla_lib/builder/document.py:107-134, 140-167
- iter_all_primitives: tools/sla_lib/builder/document.py:413
- diff.yml docs: docs/diff-tolerance.md:1-30
- diff.yml committed files: templates/{postkarte-a6-kampagne,plakat-a1-hochformat,zeitung-a4-grun}/diff.yml
- visual_diff test pattern: tools/sla_lib/tests/test_visual_diff.py (entire file)
- per_region test shape: tools/sla_lib/tests/test_visual_diff.py:42-46
- bin/validate visual_diff invocation: bin/validate:72-83
- CI test command: .github/workflows/pages.yml:105
- CI Pillow pin: .github/workflows/pages.yml:55
- Dockerfile.claude image deps: Dockerfile.claude:66 (only Pillow 12.2.0)
- visual_review.py model-orchestration pattern: tools/visual_review.py:213-227
- render_pipeline re-exports: tools/render_pipeline.py:39
- sla_diff (NOT raster): tools/sla_diff.py:1-30
- Branch isolation from #35: `git log origin/main..HEAD` → 1 commit (67e5c9e)
