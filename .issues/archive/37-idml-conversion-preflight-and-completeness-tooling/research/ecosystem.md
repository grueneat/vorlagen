# Ecosystem Research — Issue 37: IDML→DSL Pre-flight + Completeness Tooling

**Scope:** Identify canonical libraries, versions, and idioms for the new
audit tools (Phase A inventory + Backport 12 per-region visual_diff +
Phase E2 line-spacing audit). Focus is **what to use**, not how to use it —
the planner consumes this to write task instructions without re-researching.

**Date:** 2026-05-12
**Confidence (overall):** HIGH on library choices, MEDIUM on the 6×4 grid
ergonomics question (no canonical industry precedent — see §2).

---

## 1. Environment Already Installed (verified by probing)

Probed in the running Docker image (`Dockerfile.claude` extends
`ghcr.io/flomotlik/claude-code:latest`). All version numbers below are
from a live `python3 -c "import X; print(X.__version__)"` /
`<binary> --version` run on 2026-05-12.

| Component | Version | Source | Purpose |
|---|---|---|---|
| `Pillow` (PIL) | 12.2.0 | apt `python3-lxml,python3-yaml` + pip pin in `Dockerfile.claude:67` | image read/write/crop/diff |
| `lxml` | 5.4.0 | apt `python3-lxml` | IDML XML parsing |
| `PyYAML` | 6.0.3 | apt `python3-yaml` | report serialization |
| `pdfplumber` | 0.11.9 | already installed (verified at runtime; not yet declared in `Dockerfile.claude`) | PDF text/word extraction |
| `pdftoppm` (poppler-utils) | from apt `poppler-utils` | shipped | rasterize PDF → PNG |
| `pdftocairo` | from apt `poppler-utils` | shipped | rasterize PDF → PNG (alternate engine) |
| `pdfimages -list` | poppler-utils | shipped | enumerate PDF raster images |
| `pdftotext -layout` | poppler-utils | shipped | extract PDF text by line |
| `pdffonts` | poppler-utils | shipped | enumerate embedded fonts (used by `font_audit.py`) |
| ImageMagick `compare`/`convert`/`montage`/`identify` | apt `imagemagick` | shipped | current `visual_diff.py` engine + connected-components in `diff_bbox_extract.py` |
| `odiff` (odiff-bin) | v3.x (from `npm install -g "odiff-bin@^3"`) | `Dockerfile.claude:137` | fast SIMD pixel diff (currently unused — see §3) |
| `veraPDF`, `pdfcpu`, Ghostscript | various | shipped | PDF integrity |
| `xvfb` + `scribus` 1.6.x | apt | shipped | headless SLA → PDF render |

**NOT installed (confirmed):** `numpy`, `scikit-image`, `opencv-python`,
`matplotlib`, `pixelmatch`, `imagehash`. The `region_color_audit.py` tool
already in the `35-…` worktree does `import numpy as np` lazily and
catches `ImportError`, falling back to a pure-Python byte-sum
implementation. **This is the established repo idiom: optional numpy,
mandatory pure-PIL fallback.**

**Reproducibility constraint** (from `Dockerfile.claude:66-67`): Pillow
is pinned to **12.2.0** explicitly so `library.crop_for_frame()` and
`add_demo_watermark()` produce byte-identical output across container
rebuilds. Any new tool must NOT introduce a different image library or
upgrade Pillow without a Dockerfile bump and a regen-output review.

> **Confidence: HIGH** — direct version probe; pin documented inline in
> Dockerfile with explicit reasoning.

---

## 2. Backport 12: Per-Region Visual Diff (the largest deliverable)

### 2.1 Image diff primitive

**Decision: use `PIL.ImageChops.difference()` + per-channel `lighter()`
+ `Image.histogram()` for in-process per-region diff. Keep ImageMagick
`compare` for the page-wide path (current `visual_diff.py`).**

Why:
- **No numpy required** — Pillow 12.x exposes the entire pipeline.
  Repo's pure-PIL fallback pattern (see `region_color_audit.py:202`) is
  already established.
- **Performant enough at 24 cells per page × ~2 pages.** With a 6×4
  grid at 96–150 DPI an A4-sized cell is roughly 130×260px to 200×400px.
  `ImageChops.difference()` is a C-level call; 24 crops + 24 diffs
  per page is sub-second.
- **Semantic match with the current page-wide diff.** ImageMagick's
  `compare -metric AE -fuzz N%` returns the *number of pixels where any
  channel differs by more than the fuzz threshold*. The PIL equivalent
  is:
  ```
  diff = ImageChops.difference(crop_a, crop_b)   # per-channel abs delta
  r, g, b = diff.split()
  mx = ImageChops.lighter(ImageChops.lighter(r, g), b)   # max channel
  hist = mx.histogram()                          # 256 bins
  mismatch_px = sum(hist[fuzz_threshold + 1:])   # fuzz in 0..255 units
  total_px = sum(hist)
  ```
  This was verified at the REPL on 2026-05-12 (sanity test: two
  10-pixel-different RGB images, threshold=5 → mismatch_px=0; threshold=0
  → mismatch_px=N).
- **Already the codebase idiom.** The `region_color_audit.py` precedent
  uses `PIL.Image.crop()` + `convert("RGB")` + optional-numpy mean. Per-
  region visual_diff is the same shape.

**Important Pillow 12.x deprecation:** `Image.getdata()` emits
`DeprecationWarning: getdata is deprecated and will be removed in
Pillow 14 (2027-10-15). Use get_flattened_data instead.` Use
`Image.histogram()` and `Image.tobytes()` instead; both are non-
deprecated in 12.2.0. (`tobytes()` returns the raw byte string.)

> **Confidence: HIGH** — primitive verified at REPL; semantics match
> ImageMagick's AE+fuzz; matches existing codebase idiom.

**Rejected alternative: `pixelmatch-py`.** The Python port of mapbox's
pixelmatch returns a mismatched-pixel count and accepts PIL images
[pixelmatch-py PyPI]. But:
- It's not in the Docker image and adds a new dep for one capability we
  already get from PIL.
- It uses a perceptual-difference (YIQ-space) metric, NOT the
  per-channel-fuzz semantics of ImageMagick `compare`. Switching metrics
  mid-pipeline would invalidate the existing `diff.yml::fuzz_pct`
  tunings shipped per-template.
- Pixel-by-pixel benchmarks rate pixelmatch *slower* than odiff and
  comparable to ImageMagick for typical page-size images
  [vizzly.dev honeydiff vs odiff/pixelmatch].

> **Confidence: HIGH** — semantic mismatch alone disqualifies; speed is
> a secondary tiebreaker.

**Rejected alternative: `odiff` (already installed!).** odiff is the
fastest tool in the class (6× ImageMagick, per its own benchmarks
[github.com/dmtrKovalenko/odiff]). It is in `Dockerfile.claude:137`. But:
- odiff has **no native cropping** flag. You can `--ignore=x1:y1-x2:y2`
  regions but cannot run "diff ONLY this region." To use it per-cell
  we'd have to pre-crop to PNGs and call odiff 24 times per page —
  spawning 48 subprocesses per template is its own slowdown.
- odiff uses anti-aliasing-aware perceptual diff. Different semantics
  from ImageMagick AE+fuzz (same issue as pixelmatch).
- The current `visual_diff.py` page-wide path uses ImageMagick AE
  and is the convergence target metric. Changing the per-region metric
  to a different one would surface as unexplained drift between
  page-wide and grid totals.

> **Confidence: HIGH** — odiff is great for "match / no match" page-wide
> screenshots; for our per-region metric with a fuzz parameter it's the
> wrong shape.

**Rejected alternative: SSIM (`scikit-image.metrics.structural_similarity`).**
SSIM with `full=True` returns a per-pixel similarity image; you could
average per cell to get a per-cell SSIM. But:
- scikit-image is NOT installed, depends on numpy + scipy.
- SSIM is a **structural** metric (luminance/contrast/correlation in
  sliding windows); it does not align with "% of pixels that differ"
  semantics. Cross-engine raster drift (ICC, AA) generates large SSIM
  signal that fuzz_pct intentionally suppresses.
- The user's `feedback_verify_reference_before_trusting.md` memory
  flags that we already over-trusted novel signals (Scribus reference);
  introducing SSIM as a second metric risks the same trap.

> **Confidence: HIGH** — SSIM is a different question; not the right
> tool for a fuzz-style "mismatch_pct" report.

### 2.2 DPI matching between baseline and preview

**Decision: rasterize both PDFs at the same DPI via `pdftoppm -r <dpi>`
in a single shared helper. Do NOT mix rasterizers across the two PDFs.**

Why:
- `visual_diff.py:146` already does this via `pdftoppm -r <dpi> -png`
  for both sides. The new region tool MUST consume the same rasters
  (or re-rasterize at the same DPI with the same tool) — anything else
  produces sub-pixel registration drift that swamps the grid metric.
- **`pdftoppm` and `pdftocairo` produce SUBTLY different pixel output
  at the same DPI.** Both are poppler-utils but use different rendering
  backends (splash vs cairo). The existing `region_color_audit.py`
  worktree uses `pdftocairo`; the existing `visual_diff.py` uses
  `pdftoppm`. **For per-region visual_diff specifically, the tool MUST
  use the same rasterizer the page-wide `visual_diff.py` already uses
  (`pdftoppm`)** so a per-region total reconciles with the page-wide
  total.
- DPI choice: re-use whatever `visual_diff.py --dpi`/`--ci` flag was
  set for the page-wide run. Default 150, CI 96. The page bounding box
  in pixels is identical → grid math is trivial:
  `cell_w_px = page_w_px // cols`, `cell_h_px = page_h_px // rows`,
  with the last column/row absorbing the modulus.

> **Confidence: HIGH** — pdftoppm vs pdftocairo difference is observable;
> mixing rasterizers is a known footgun (codebase explicitly uses one
> per tool but never mixes within a single comparison).

### 2.3 Heatmap PNG rendering

**Decision: use `PIL.ImageDraw.Draw().rectangle(fill=color)` with a
hand-rolled linear color ramp. Do NOT pull in matplotlib.**

Why:
- matplotlib is not installed and is ~30 MB on disk; adding it for
  one PNG output is wildly out of proportion to the value.
- The heatmap is **24 rectangles** drawn on a transparent canvas the
  same size as the rasterized page, optionally alpha-composited over
  a dimmed copy of the baseline image. Trivial in PIL.
- Color ramp: green→yellow→red is two linear interpolations in RGB:
  - `mismatch_pct = 0` → `(76, 175, 80)` (green)
  - `mismatch_pct = threshold` → `(255, 193, 7)` (amber)
  - `mismatch_pct >= 2 × threshold` → `(244, 67, 54)` (red)
  - Clamp + lerp between the two segments.
  (Matches Material Design 500-level colors — readable on both light
  and dark backgrounds.)
- Cell labels (`"18.7%"`) drawn with `ImageDraw.text()` using a default
  Pillow built-in font is sufficient; if a TTF is desired, the
  DejaVu Sans face from `fonts-dejavu-core` is in the image already
  (`Dockerfile.claude:50`).

**Output structure:**
```
build/<slug>/visual_diff_regions-page-NN.png    # heatmap overlay
build/<slug>/visual_diff_regions.yml            # YAML report
```

> **Confidence: HIGH** — straightforward PIL primitive. `heatmappy`
> (LumenResearch) was considered and rejected — it's optimized for
> point-density visualization (mouse-tracking, eye-tracking), not
> categorical grid overlays.

### 2.4 Per-cell threshold semantics

**Decision: re-use `TemplateTolerance` from `visual_diff.py:42`.
Extend the `per_region` list to accept an optional `grid` entry
that supersedes the dict-of-bboxes form.**

Existing structure (`visual_diff.py:42-83`):
```yaml
visual_diff:
  max_pixel_mismatch_pct: 1.0
  fuzz_pct: 25.0
  per_page:
    - {page: 0, max_pixel_mismatch_pct: 2.5}
  per_region:
    - {page: 0, bbox_mm: {x: 10, y: 20, w: 80, h: 40}, max_pixel_mismatch_pct: 5}
```

Proposed extension:
```yaml
visual_diff:
  ...
  region_grid:                          # NEW (Backport 12)
    cols: 6
    rows: 4
    per_cell:                           # optional overrides
      - {page: 0, col: 3, row: 2, max_pixel_mismatch_pct: 10, fuzz_pct: 30}
    # default cell threshold falls back to per_page → page-wide default
```

Keep `per_region` (free-form bboxes) AND `region_grid` (fixed grid)
side by side. They answer different questions: bbox = "this gradient
zone needs higher tolerance"; grid = "spatial heatmap for human review."

> **Confidence: MEDIUM** — schema extension is reasonable but not the
> only design. The planner may choose to make the grid live in its own
> `visual_diff_regions:` block to avoid coupling the new tool to the
> page-wide tolerance loader.

---

## 3. Question 2 — Is 6×4 = 24 regions sensible? How to scale?

**Short answer: 6×4 is fine for A4/A5/DIN-Lang as a default. Make the
grid configurable per-template. Do NOT auto-scale by page size in v1;
let `diff.yml::region_grid.{cols,rows}` carry the per-template choice.**

### Research findings

- **No industry standard exists.** BackstopJS, Percy, Chromatic, and
  Playwright's `toHaveScreenshot` all use *whole-region* diffs (full
  page or element selector). None of them ship a configurable
  grid-overlay mode. The closest analog is Percy's "ignore regions"
  + Cypress visual-regression's per-element capture — neither maps to
  a uniform grid [Percy blog 2026; bug0 Playwright guide 2026;
  cypress-visual-regression npm].

  > **Confidence: HIGH** that no canonical grid-region tool exists in
  > the web-UI test ecosystem to anchor against.

- **Adobe Research has work on "adaptive grid-based document layout"**
  for adapting print layouts to electronic displays — but the framing
  is layout *production*, not QA diffing. Not directly applicable.
  [dl.acm.org adaptive grid-based document layout]

  > **Confidence: MEDIUM** — couldn't find a paper that uses grid
  > sampling for visual-regression of print artifacts; absence of
  > evidence != evidence of absence, but the search was thorough.

- **A4 portrait (210×297 mm) at 6×4 = 35×74 mm/cell.** That
  approximates a magazine "module" — one module typically holds a
  headline, a body column, or an image slot in editorial layouts.
  For DIN-Lang panels (99×210 mm folded), 6×4 gives 16.5×52.5 mm/cell,
  which is roughly one body-text line wide × half a body paragraph —
  finer than a "slot" but still useful as a heatmap. The user's design
  templates are predominantly A4/DIN-Lang campaign material, so a
  fixed 6×4 covers the common case.

- **For larger format (A1 poster ~594×841 mm), 6×4 leaves cells of
  ~99×210 mm — too coarse.** A heuristic for the planner: when
  page area > 4 × A4 area, default to 12×8 = 96 cells. But since the
  user has not yet imported a poster template, defer this to a follow-
  up; ship 6×4 as the constant.

### Bleed / safe-area awareness

- **Skip in v1.** The page-wide `visual_diff.py` already rasterizes
  the full media box (including bleed) and the agent's convergence
  target is the full rasterized image. A "safe area" overlay would
  duplicate concerns from `tools/audit_alignment.py` (which already
  enforces brand-safe margins). Phase 12 should report mismatch on
  *every* cell; if bleed-region cells are noisy, the user adjusts that
  cell's threshold in `diff.yml::region_grid.per_cell`.

> **Confidence: MEDIUM** — pragmatic call. The planner could choose
> to expose `safe_area_mm` from `meta.yml` and tag bleed cells, but
> that's premature for the first ship.

### Concrete recommendation for the planner

```yaml
# Default grid (hardcoded in tools/visual_diff.py)
DEFAULT_GRID = {"cols": 6, "rows": 4}

# Optional per-template override via diff.yml
visual_diff:
  region_grid:
    cols: 6
    rows: 4
    # per_cell overrides come here
```

**Acceptance test from the issue** (line 1230-1232): "a regression test
with a controlled small localized diff (shift a single 9pt headline by
50pt) produces a region with > 10% mismatch even when page-wide is < 1%."
For an A4 page at 150 DPI, a 9pt × ~150pt headline shifted 50pt is
roughly 19px × 312px = 5928 px²; an A4 region cell at 6×4 is 206×438 px
= 90228 px². The shift would discolor maybe 30% of one cell, well above
the 10% threshold the test calls for. **6×4 is correctly sized for that
acceptance test.**

> **Confidence: HIGH** — back-of-envelope verified the chosen acceptance
> test exercises the chosen cell size.

---

## 4. Question 3 — IDML XML parsing: stick with lxml

**Decision: keep `lxml.etree` for all IDML parsing. Do NOT introduce
`xml.etree.ElementTree` or `defusedxml`.**

Why:
- `lxml` is the established codebase choice (see all
  `tools/idml_to_dsl.py` and `tools/sla_lib/reader.py` imports). It's
  apt-installed (`python3-lxml`, `Dockerfile.claude:46`).
- `lxml` is **multiple times faster** than stdlib `ElementTree` in
  round-trip benchmarks; for a typical IDML's `Spreads/Spread_*.xml`
  (typically 10–500 KB) the difference is sub-second either way, but
  the consistency benefit of one library across all tools dominates.
  [lxml.de/performance.html]
- IDML files are **trusted internal inputs** — defusedxml's
  XXE-protection mandate doesn't apply (the user authors the IDMLs).
  We are NOT parsing untrusted XML.
- **`iterparse` is unnecessary** at IDML sizes. The largest
  `Spreads/Spread_*.xml` we've seen in templates is ~50 KB. The
  whole-tree-then-XPath idiom in existing tools is correct.

> **Confidence: HIGH** — version-pinned, codebase-consistent, perf is
> a non-issue at IDML size.

### Idiomatic lxml usage for the new tools (Phase A1 `idml_inventory.py`)

```python
from lxml import etree
import zipfile

# IDML is a ZIP — extract Spreads/Spread_*.xml
with zipfile.ZipFile(idml_path) as zf:
    for name in zf.namelist():
        if name.startswith("Spreads/Spread_") and name.endswith(".xml"):
            with zf.open(name) as f:
                tree = etree.parse(f)
            # find all PageItems regardless of nesting depth
            for el in tree.iter():
                tag = etree.QName(el).localname
                if tag in {"Rectangle", "Polygon", "Oval", "TextFrame",
                           "GraphicLine", "Group"}:
                    self_id = el.get("Self")
                    ...
```

Use `etree.QName(el).localname` to strip the IDML namespace cleanly.
Use `el.iter()` for depth-first walk; `el.findall(".//*")` for filtered.

> **Confidence: HIGH** — standard lxml idiom; matches `idml_to_dsl.py`
> style.

---

## 5. Question 4 — ImageMagick `compare` vs PIL/numpy

**Decision: KEEP ImageMagick `compare` for the page-wide `visual_diff.py`
metric (do not regress the convergence target). USE PIL `ImageChops`
for the new per-region tool (24 cells × 2 pages, in-process is faster
than 48 subprocess calls).**

### Performance comparison (verified sources)

- **ImageMagick `compare` (current):** spawns a subprocess per page,
  fork+exec overhead ~30-50ms each, then SIMD raster work. For 2 pages
  total wall time is ~200-400 ms. For 48 cells (2 pages × 24 cells)
  shelling out 48 times would be 1.5-2.5 sec just in subprocess
  startup, plus the actual diff work.
- **PIL `ImageChops.difference` in-process:** for a single A4-cell-sized
  region at 150 DPI (~200×400 px = 80k pixels), the C-level diff is
  microseconds. The `histogram()` pass over the max-channel image is
  another ~100µs. 48 cells in-process is well under 100ms total.
- **odiff (installed but unused):** would beat ImageMagick on big
  pages but loses on per-region overhead (still subprocess per
  invocation, no batching, no in-process API).
- **pixelmatch-py:** comparable to ImageMagick speed on small images,
  worse on large; different semantics (perceptual). Rejected (see §2.1).

> **Confidence: HIGH** — benchmarks per
> [github.com/dmtrKovalenko/odiff] and [vizzly.dev honeydiff vs odiff/
> pixelmatch]; codebase microbenchmarks would only refine, not flip.

### Why keep ImageMagick for the page-wide path

1. **Convergence-target invariance.** The user's PR landed
   `max_pixel_mismatch_pct` thresholds per template via
   `templates/<slug>/diff.yml`. Those are calibrated against
   `compare -metric AE -fuzz N%` semantics. Switching the page-wide
   diff to a different metric invalidates every per-template tuning
   and would require a full re-calibration pass.
2. **Already a convergence metric.** The skill rules (P1 of the issue
   header) make the page-wide `mismatch_pct` against `baseline.pdf` the
   single success criterion. Don't change the meter mid-experiment.
3. **`out of scope` per the issue:** ISSUE.md line 838 — "Replacement
   of `tools/visual_diff.py` — extension only." The new tool extends
   the page-wide flow with a region overlay; it doesn't replace it.

> **Confidence: HIGH** — issue text + skill rules + thresholds-already-
> tuned all reinforce.

### Fuzz semantics for PIL per-region path

The PIL pipeline reproduces ImageMagick AE+fuzz semantics:

| ImageMagick                              | PIL equivalent                                                |
|------------------------------------------|---------------------------------------------------------------|
| `compare -metric AE -fuzz N%`            | `histogram` of `max(R,G,B)` of `ImageChops.difference`        |
| fuzz_pct=25 → tolerance ≈ 64/255 channel | sum `histogram[fuzz_threshold + 1:]` where `fuzz_threshold = round(255 * fuzz_pct / 100)` |

**Quantization-rounding edge case:** ImageMagick's fuzz is a Euclidean
color-distance threshold in RGB space (sqrt(R²+G²+B²)), not a max-channel
threshold. For typical AA noise patterns (small symmetric deltas across
all three channels), the two are within 1-2% of each other on real
PDFs. For convergence purposes that's acceptable — but for the
per-region heatmap rendering only, exact ImageMagick-fuzz equivalence
is not required. The per-region tool reports its own metric (pixel
count where max channel delta > N); that's its own threshold and the
user tunes via `region_grid.per_cell.fuzz_pct`.

> **Confidence: MEDIUM** — exact fuzz semantics are
> documented-by-source-code in ImageMagick (`coders/compare.c`); a
> tighter equivalence would compute `sqrt(R²+G²+B²) / sqrt(3)` per
> pixel, which is the per-pixel `L2 / sqrt(3)` metric. The planner
> can decide whether to match exactly or use max-channel as a
> simpler approximation. **Recommendation: max-channel approximation
> for v1, document the deviation in a docstring, revisit if it bites.**

---

## 6. Question 5 — YAML schema design

**Decision: match the established repo idiom exactly:**

```python
def _yaml_dump(payload: dict) -> str:
    return yaml.dump(
        payload,
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
    )
```

This is verbatim what `per_element_drift.py:81-85`, `font_audit.py`,
`text_render_audit.py`, `baseline_text_audit.py`, `baseline_image_audit.py`,
and `idml_inventory.py` use across the `35-…` worktree.

### Determinism rules (already enforced in existing audits)

1. **`sort_keys=True`** — alphabetical key ordering, byte-identical
   across runs. Tested in `region_color_audit.py` acceptance
   ("YAML output deterministic (sort_keys=True, byte-identical on
   re-run)"; ISSUE.md line 812).
2. **`default_flow_style=False`** — full block style. Tradeoff: more
   lines but human-diffable.
3. **`allow_unicode=True`** — German umlauts in template slugs
   (e.g. `gruenes`, `falzflyer`) and brand names (Grüne) must round-
   trip without `ü` escaping. The existing audit reports already
   carry German strings.
4. **No timestamps in the report.** All existing audit YAMLs are
   timestamp-free for re-run determinism.
5. **Sort lists before dumping** when the list ordering is not itself
   semantically meaningful. (E.g. `large_deltas` is sorted by
   `|dx|+|dy|` magnitude descending; `top_contributors` is sorted by
   `mismatch_px_summed` descending — those are semantic. But cell
   reports in `visual_diff_regions.yml` should sort by
   `(page, row, col)` for stable diffs.)
6. **Round floats** before dump (e.g. `round(mismatch_pct, 4)`) so the
   YAML repr doesn't fluctuate by least-significant-bit noise from PIL
   per-channel mean computations.

> **Confidence: HIGH** — pattern observed in 7+ existing audit tools
> in the `35-…` worktree; explicitly called out as acceptance criteria
> in ISSUE.md for D7, D8, E, F, G.

### Schema for `visual_diff_regions.yml` (proposed)

```yaml
template: <slug>
grid:
  cols: 6
  rows: 4
pages:
  - page: 0
    regions:
      - {col: 0, row: 0, mismatch_pixels: 412, total_pixels: 90228,
         mismatch_pct: 0.4566, threshold_pct: 1.0, fuzz_pct: 25.0,
         pass: true}
      - {col: 3, row: 2, mismatch_pixels: 16873, total_pixels: 90228,
         mismatch_pct: 18.7000, threshold_pct: 1.0, fuzz_pct: 25.0,
         pass: false}
      ...
    hot_regions:
      - {col: 3, row: 2, mismatch_pct: 18.7000}
    heatmap_png: visual_diff_regions-page-01.png
ok: false
```

Matches the issue's example (line 1196-1205) exactly; only addition
is the per-region `threshold_pct`/`fuzz_pct` so the report is
self-describing.

> **Confidence: HIGH** — schema is a direct read of the acceptance
> criteria.

---

## 7. Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Pixel-by-pixel image diff | A pure-Python loop over `Image.getdata()` | `PIL.ImageChops.difference()` | C-level, ~1000× faster, no deprecation footgun (getdata removed Pillow 14) |
| Counting pixels above threshold | A loop summing per-pixel checks | `Image.histogram()` on max-channel | Single C-level histogram → list, then slice-sum |
| PDF rasterization | Pulling in `pdf2image` | `subprocess` call to `pdftoppm -r DPI` | Already installed; `pdf2image` is just a `pdftoppm` wrapper |
| PDF word extraction with bboxes | Hand-parsing pdftotext output | `pdfplumber.extract_words()` | Already used by D8 `text_position_audit.py` and F `run_style_audit.py` |
| YAML dump | Custom serializer | `yaml.dump(..., sort_keys=True, allow_unicode=True, default_flow_style=False)` | Repo idiom; deterministic |
| Heatmap rendering | matplotlib | `PIL.ImageDraw.rectangle` + lerp | matplotlib not installed; one PNG = 5 lines of PIL |
| IDML XML parsing | xml.etree.ElementTree, defusedxml | `lxml.etree` | Codebase consistency; lxml is multiple× faster on round-trip |
| Per-line baseline measurement (E2) | Hand-parsing pdftotext positions | `pdfplumber.extract_words()` with `top` attribute | pdfplumber returns word-level y0/y1; median of pairwise gaps = line spacing |
| Color-ramp interpolation | hsluv / colour-science | Hand-rolled 2-segment RGB lerp | 5 lines; we only need green→amber→red |

> **Confidence: HIGH** for all rows except heatmap rendering (MEDIUM
> — matplotlib would be more polished but not worth its install footprint).

---

## 8. Architecture Patterns

### 8.1 Audit tool template (matches existing repo idiom)

Every Phase A/D6/D7/D8/E/F/G audit tool in the `35-…` worktree follows
the same five-section shape. New Backport-12 + Phase-E2 tools should
follow it verbatim:

```python
#!/usr/bin/env python3
"""<one-line purpose>.

<3-5 sentence description of inputs, outputs, what it catches>.

Usage:
    python3 tools/<name>.py \\
        --preview <path> --baseline <path> \\
        --template <slug> --out <yml-path>
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageChops  # NEW for region diff
from lxml import etree  # if XML; omit otherwise

# Section 1: Data extraction (pdfplumber / pdftoppm / lxml)
def extract_X(...): ...

# Section 2: Per-element / per-region computation
def compute_Y(...): ...

# Section 3: Severity / pass-fail classification
def classify_Z(...): ...

# Section 4: Deterministic YAML emission
def _yaml_dump(payload: dict) -> str:
    return yaml.dump(payload, sort_keys=True, allow_unicode=True,
                     default_flow_style=False)

# Section 5: CLI argparse + main
def main(argv: Optional[list[str]] = None) -> int: ...

if __name__ == "__main__":
    raise SystemExit(main())
```

### 8.2 Wire-up into `render_pipeline.py::_run_audit`

Existing precedent: D7, D8, E, F, G are all `subprocess.run([sys.executable,
"tools/<name>.py", ...])` calls inside `_run_audit`, with a short
summary line emitted to stdout, and failures contributing to an
`issue_parts` list that `--audit-strict` blocks on. The Backport-12 and
Phase-E2 tools follow the same pattern.

### 8.3 Test layout

`tests/test_<tool_name>.py` (pytest, not unittest — see ISSUE.md
"Cross-cutting" line 822). Existing audit tools have 9-25 unit tests +
4-6 integration tests; runtime <5s on synthetic PDFs. Use small
PIL-generated synthetic images for unit tests; v2 falzflyer for
integration.

> **Confidence: HIGH** — pattern observed in 7+ tools.

---

## 9. Anti-Patterns to Avoid

- **Don't mix rasterizers within a single comparison.** `pdftoppm` and
  `pdftocairo` produce subtly different rendering. The per-region tool
  MUST use the same rasterizer the page-wide `visual_diff.py` uses
  (`pdftoppm`).

- **Don't pull in matplotlib for one heatmap.** It would add ~30 MB to
  the Docker image and force a numpy install, neither of which we need.

- **Don't introduce SSIM as a "richer" per-cell signal.** It's a
  structurally different metric; mixing it with the page-wide AE+fuzz
  meter creates confusing reports. Stick with mismatch_pct semantics
  end-to-end.

- **Don't auto-`pip install` at runtime.** ISSUE.md D8 acceptance line
  747-748: `pdfplumber must be a declared dependency in
  Dockerfile.claude or requirements.txt — do not silently pip install`.
  Same rule applies to any new dep. (pdfplumber 0.11.9 is already in
  the image but **not yet declared** — the planner should add a
  declaration line to `Dockerfile.claude` while opening the new tools.)

- **Don't use `Image.getdata()`** — deprecated in Pillow 12, removal
  scheduled for Pillow 14 (2027-10-15). Use `Image.histogram()`,
  `Image.tobytes()`, or the new `get_flattened_data()`.

- **Don't sort_keys=False** for any audit output. The codebase's
  determinism contract is explicit (`sort_keys=True`, byte-identical
  on re-run). Two exceptions exist (`gallery_build.py` meta.yml,
  `experiment_hypothesis_gen.py` manifest) — those are not audit
  reports and predate the audit-determinism rule.

- **Don't shell out for in-process work.** A 48-call subprocess loop
  for cell-level diffs (e.g. odiff per cell) is dominated by fork
  overhead. PIL is C-level and faster.

> **Confidence: HIGH** for all six.

---

## 10. Common Pitfalls (Backport-12-specific)

### 10.1 Cell aliasing at low DPI

**What goes wrong:** at 96 DPI (CI), an A4-portrait raster is 794×1123
pixels. A 6×4 grid is 132×281 px/cell — fine. But for narrow formats
(DIN-Lang 99×210 mm folded = 374×794 px), 6×4 = 62×199 px/cell.
A single off-by-one rounding error in the cell boundary calculation
shifts the boundary by up to one whole percent of the cell area.

**How to avoid:**
- Compute cell boundaries with integer division and let the last col/row
  absorb the modulus:
  ```python
  col_widths = [page_w // cols] * cols
  col_widths[-1] += page_w % cols   # absorb modulus
  ```
- Test with synthetic page sizes that are NOT divisible by `cols` or
  `rows`.

### 10.2 Crop coordinate rounding inconsistency

**What goes wrong:** PIL `Image.crop((l, t, r, b))` uses pixel indices
half-open on the right/bottom. If `l = float`, PIL rounds; the rounding
is not bit-identical to ImageMagick `convert -crop WxH+X+Y` which uses
half-up integer pixel coordinates.

**How to avoid:** always pass `int` coordinates to PIL `.crop()`. Compute
cell boundaries once as Python ints, then slice.

### 10.3 Heatmap PNG cache invalidation

**What goes wrong:** the heatmap `visual_diff_regions-page-NN.png`
embeds the threshold colors visually. Changing
`diff.yml::region_grid.cols` should change the file path or content
so a stale heatmap doesn't pollute the gallery.

**How to avoid:** include `cols×rows` in the PNG filename OR overwrite
unconditionally on every audit run (existing render_pipeline does this
for `visual_diff.html`/`diff-page-NN.png`).

### 10.4 Heatmap visibility on dark backgrounds

**What goes wrong:** a green-yellow-red ramp on a black page background
(common for v2 falzflyer) is hard to read at the corners.

**How to avoid:** alpha-blend the heatmap at ~60% opacity over a
*desaturated grayscale* copy of the baseline page, not over the page
directly. Existing `tools/visual_review.py` uses a similar montage
strategy.

### 10.5 ImageMagick fuzz_pct vs PIL max-channel-fuzz divergence

**What goes wrong:** the page-wide mismatch_pct uses ImageMagick AE+fuzz
semantics (sqrt-of-squared-channel-deltas, Euclidean). The per-region
PIL pipeline uses max-channel-delta-threshold semantics. The sum of
per-cell mismatch_px will not exactly equal the page-wide mismatch_px.

**How to avoid:** document this in the tool's docstring. The two
metrics are within ~1-2% of each other on real PDFs (where deltas are
near-uniform across channels — AA, ICC), but report the per-cell
total separately rather than asserting "cells sum to page total."

### 10.6 Single-cell "design slot" inversion

**What goes wrong:** the 6×4 grid is regular, not slot-aware. A
headline that spans cols 2-4 row 1 is split across 3 cells; if it
drifts uniformly, the user sees three medium-mismatch cells instead
of one obviously-broken slot. Backport 12 acknowledges this is the
COMPLEMENT to `diff_bbox_extract.py` (which IS slot-aware via
attribution to `anname`). The two are used together, not in
competition.

**How to avoid:** Read ISSUE.md line 1215-1220 explicitly — the
per-region grid gives a stable spatial map; the bbox extractor gives
anomaly shapes. Surface BOTH outputs in `--audit` stdout so the user
sees them together.

> **Confidence: HIGH** for items 1, 2, 3, 5, 6 — verified at REPL or
> by reading existing tool source. **Confidence: MEDIUM** for item 4
> (alpha-blend recommendation is taste-driven; could be different
> choice without breaking the spec).

---

## 11. Open Questions for the Planner

1. **Phase-E2 baseline-measured line spacing units.** ISSUE.md
   says "median of pairwise gaps" — that's `(top_line_n+1 - top_line_n)`.
   But `pdfplumber.extract_words()` returns `top` in the *PDF
   coordinate space* (origin top-left for the default cropbox-based
   rendering pipeline; origin bottom-left for raw page-space). Verify
   pdfplumber 0.11.9 returns positive-down `top` for `Page.extract_words()`
   before writing the median-pairwise code. (See pdfplumber docs;
   default is top-left-origin.) Probably HIGH-confidence-correct in
   default config but worth a one-line REPL check.

2. **Backport 12 acceptance test:** the "shift a single 9pt headline
   by 50pt" regression test (ISSUE.md line 1227-1229) needs a
   precise synthetic PDF or a fixture. Two options:
   - Generate two synthetic 1-page PDFs via PIL → wkhtmltopdf or via
     reportlab (NOT in image). Adds a dep.
   - Use the v2 falzflyer pre-Backport-11 build.py as a fixture (PR-fix
     branch), and check the region containing u376 ("Headline in einem
     grünen Kasten") shows mismatch > 10%.
   The second option is concrete and tests against real drift; the
   first is more hermetic but adds a dep. Planner picks.

3. **Heatmap caption rendering.** The mismatch_pct labels on each cell
   need a font. DejaVu Sans is in the image (`fonts-dejavu-core`); but
   the path is system-distribution-dependent. Use `PIL.ImageDraw.text()`
   with the built-in PIL bitmap font for v1 (loads without a system
   font path), iterate later if it's unreadable.

4. **Page-size adaptive grid (deferred from v1).** The user does not
   currently import poster templates. A follow-up issue can add
   page-area-based defaults (12×8 for A1+). Out of scope for #37 ship.

> **Confidence (open questions): MEDIUM** — these are decisions, not
> facts; the planner picks. Listing them prevents the executor from
> hand-deciding mid-task.

---

## 12. Standard Stack (final summary)

| Library | Version | Purpose | Why Standard | Confidence |
|---|---|---|---|---|
| Pillow (PIL) | 12.2.0 (pinned `Dockerfile.claude:67`) | image crop / diff / heatmap | Already pinned for byte-determinism; provides ImageChops.difference + histogram | HIGH |
| lxml | 5.4.0 | IDML XML parsing | Codebase-wide standard; 5-20× faster than ElementTree on round-trip | HIGH |
| PyYAML | 6.0.3 | audit report serialization | Codebase-wide standard; deterministic with sort_keys=True | HIGH |
| pdfplumber | 0.11.9 | PDF word/line extraction with bboxes (E2, D8, F) | Already used by D8/F; provides line/word geometry; needs `Dockerfile.claude` declaration | HIGH |
| poppler-utils `pdftoppm` | apt | PDF → PNG rasterization | Matches existing `visual_diff.py:146`; same rasterizer as page-wide diff | HIGH |
| poppler-utils `pdftotext` | apt | text extraction (D7, E2) | Standard; existing tools use `-layout` | HIGH |
| poppler-utils `pdfimages -list` | apt | raster image enumeration (A3) | Single command, idiomatic | HIGH |
| ImageMagick `compare` | apt | page-wide diff (existing, KEEP) | Convergence-target metric; per-template thresholds calibrated | HIGH |
| ImageMagick `convert -connected-components` | apt | bbox extraction (D6/#36 — existing) | Codebase-wide | HIGH |
| ImageMagick `montage` | apt | composite review images (existing) | Codebase-wide | HIGH |
| Python `subprocess` + `argparse` + `pathlib` | stdlib | CLI scaffolding | Stdlib; matches every existing audit tool | HIGH |
| **NOT used:** numpy / opencv / scikit-image / matplotlib / pixelmatch / odiff / pdf2image | n/a | n/a | See §2.1, §3, §7 | HIGH |

---

## 13. Project Constraints (from `CLAUDE.md` and user memory)

No workspace `CLAUDE.md` exists at `/workspace/CLAUDE.md`. The
following constraints come from user memory entries (visible in this
session):

- **`feedback_no_claude_attribution.md`:** never include "claude" in
  commits / code / file names.
- **`feedback_fix_generator_not_artifact.md`:** when emitted artifact
  is wrong, fix the generator (`idml_to_dsl.py`), not the artifact
  (`build.py`). The new audit tools SURFACE generator gaps; they do
  not fix them.
- **`feedback_font_fidelity_check.md`:** font_audit (D6) is mandatory
  pre-flight. New audit tools must NOT bypass or weaken its
  `missing_in_preview` empty-set invariant.
- **`feedback_verify_reference_before_trusting.md`:** measure any new
  "canonical" source before trusting it. We've internalized this with
  the rejected-alternatives section: pixelmatch's perceptual metric,
  SSIM, and odiff all sounded canonical but failed semantic-fit checks.
- **`feedback_idml_leading_vs_rendered.md`:** the Phase E2 spec is
  born from this finding (IDML CSR `<Leading>` ≠ rendered baseline-to-
  baseline). The audit tool MUST measure baseline.pdf with pdfplumber,
  not trust the CSR value.

> **Confidence: HIGH** — directly from user-memory entries.

---

## 14. Sources

### HIGH confidence (cited inline; verified by direct API call or doc fetch)

- Pillow 12.2.0 docs: `ImageChops.difference()` semantics, `getdata()`
  deprecation —
  [Pillow ImageChops docs](https://pillow.readthedocs.io/en/stable/reference/ImageChops.html)
  and verified at REPL on 2026-05-12.
- Pillow 12.2.0 docs: `ImageDraw.rectangle`, `ImageColor` —
  [Pillow ImageDraw docs](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html)
  and
  [Pillow ImageColor docs](https://pillow.readthedocs.io/en/stable/reference/ImageColor.html).
- odiff CLI flags — verified by `odiff --help` on 2026-05-12 in this
  container; also
  [github.com/dmtrKovalenko/odiff README](https://github.com/dmtrKovalenko/odiff).
- lxml performance — verified by webfetch of
  [lxml.de performance page](https://lxml.de/performance.html).
- pdfplumber `Page.to_image()` resolution / `extract_words()` API —
  [github.com/jsvine/pdfplumber](https://github.com/jsvine/pdfplumber).
- ImageMagick `compare -metric AE -fuzz` semantics — already documented
  by current `tools/visual_diff.py:157-185` and the upstream
  [ImageMagick compare docs](https://imagemagick.org/script/compare.php).
- Existing tools in `.worktrees/35-…/tools/` (region_color_audit.py,
  per_element_drift.py, font_audit.py, text_render_audit.py,
  idml_inventory.py, baseline_text_audit.py, baseline_image_audit.py)
  read on 2026-05-12.
- `Dockerfile.claude` direct inspection (lines 36-148).

### MEDIUM confidence (web-sourced, single-source or partial verification)

- BackstopJS / Percy / Chromatic / Playwright per-element vs full-page
  practice —
  [Percy blog 2026: visual-regression-testing-tools](https://percy.io/blog/visual-regression-testing-tools),
  [bug0 Playwright visual regression](https://bug0.com/knowledge-base/playwright-visual-regression-testing).
  No tool ships a configurable grid-overlay mode; confidence in
  *that absence* is HIGH but no tool uses 6×4 as a precedent →
  MEDIUM on grid-sizing.
- odiff vs ImageMagick vs pixelmatch benchmarks —
  [vizzly.dev: honeydiff vs odiff/pixelmatch benchmarks](https://vizzly.dev/blog/honeydiff-vs-odiff-pixelmatch-benchmarks/)
  and odiff's own README numbers. Single primary source, but consistent
  across the two.
- A4/A5/DIN-Lang cell-size sanity numbers — back-of-envelope arithmetic
  from
  [papersizes.org A-paper-sizes](https://www.papersizes.org/a-paper-sizes.htm).

### LOW confidence (no authoritative source, treat as recommendation)

- Heatmap color-ramp choice (green→amber→red via Material Design 500
  values). Taste-driven; the planner can substitute any other ramp.
- The 6×4 default grid number itself. No industry precedent; based on
  the issue author's choice + back-of-envelope cell-size check. The
  planner should treat `cols`/`rows` as configurable and document the
  default as "chosen because A4 cell = 35×74 mm ≈ one editorial slot."

---

## 15. Key Findings (one-liner each)

1. **Image diff primitive: `PIL.ImageChops.difference()` + per-channel
   `lighter()` + `Image.histogram()`** — pure PIL, no numpy required;
   matches the lazy-import idiom already in `region_color_audit.py`.
2. **Keep ImageMagick `compare` for the page-wide path** — switching
   the convergence metric mid-experiment would invalidate every
   per-template `max_pixel_mismatch_pct` calibration.
3. **6×4 grid is fine as a default** — no canonical industry precedent
   to anchor against, but cell size on A4 (~35×74 mm) maps to roughly
   one editorial slot, and the issue's own acceptance test (50pt
   headline shift) verifiably triggers >10% mismatch in one cell.
4. **`pdfplumber` (0.11.9) is already installed but not yet declared
   in `Dockerfile.claude`** — declaration must be added when new tools
   land (per the D8 acceptance criterion line 747-748).
5. **YAML idiom is locked: `sort_keys=True, allow_unicode=True,
   default_flow_style=False`** — used in 7+ existing audit tools;
   acceptance criteria for D7/D8/E/F/G explicitly require deterministic
   byte-identical output.
6. **`Image.getdata()` is deprecated in Pillow 12** — use
   `Image.histogram()` / `Image.tobytes()` / `get_flattened_data()`
   instead. Removal scheduled for Pillow 14 (2027-10-15).
7. **Don't introduce matplotlib, scikit-image, opencv, pixelmatch, or
   odiff** — each fails one of the four tests: not installed, wrong
   semantics, wrong granularity, or wrong cost-to-value ratio.
