---
id: '37'
title: IDML→DSL pre-flight tooling + post-conversion completeness checks
status: done
priority: high
labels:
- dsl
- templates
- tooling
- visual-qa
---

## Context

Issue #35 (IDML→DSL bootstrap) shipped the converter for the first IDML
template (`kandidat-falzflyer-din-lang-gruenes-cover-v2`). The convergence
loop that followed exposed a structural weakness in the workflow:

- **Two consecutive Sonnet executor agents (~5 hr combined runtime,
  ~1500 tool calls) declared an "engine floor" at page1=7.31% / page2=6.31%
  visual_diff mismatch and stopped.**
- **A 6-image visual review by a third reviewer surfaced 7 concrete
  converter bugs the executors had missed**, including a wind-turbine
  illustration absent from the cover, a missing attribution caption, broken
  per-icon cropping on the social-media-icons strip, and an IDML Group
  transform gap papered over with a hardcoded `+5.05mm` shift in `build.py`.
- The user explicitly flagged the social-media-icons issue **two messages
  before the executor loop started**, and the executor still didn't fix it
  — because the bbox JSON oracle alone cannot distinguish "element missing"
  from "element drifted."

Root cause: the convergence loop optimises for drift reduction, not
structural completeness. The bbox JSON shows mismatches on **what's
rendered**; it has no concept of **what should be there but isn't**. The
executor will happily declare an "engine floor" while large structural
omissions are attributed as background-color drift on the bare canvas.

This issue lands the tooling so future IDML imports converge in **one
session at <1 hr**, not 5 hr across multiple sessions, with **structural
completeness proven before any drift work begins**.

## Principles

These rules govern the IDML→DSL import workflow and must be encoded
verbatim in any downstream skill (`/idml-import`, `/convergence-loop`,
etc.) that drives this pipeline.

### P1 — `baseline.pdf` is THE convergence target. Only success criterion.

`templates/<slug>/baseline.pdf` is the InDesign-exported PDF supplied by
the design team. Drift convergence is measured against it via
`visual_diff.py`. Pass means `mismatch_pct <= diff.yml::max_pixel_mismatch_pct`
on every page. No other artifact is a convergence target.

### P2 — Two sources, two distinct roles. Never conflate.

| Source | Role | NEVER used as |
|---|---|---|
| `original.idml` | Authoring truth — what InDesign content exists | Visual reference |
| `baseline.pdf` | **Convergence target** (P1) — what the design SHOULD look like | Element extraction (lossy; positions are subpixel) |

### P3 — `baseline.pdf` is the only convergence reference. No mirroring of other importers' choices.

Don't introduce a "second importer's output" (e.g. Scribus's own IDML import) as a reference signal — empirically, that creates more cognitive overhead than value. Agents repeatedly fell into the trap of mirroring the alternative importer's choices (e.g. `LINESPMode="1"`) without verifying against `baseline.pdf`, and the alternative importer's render had its own drift gaps (page-dimension differences, wrong leading strategy). Stick to two sources: IDML (authoring truth) + baseline.pdf (convergence target).

**Post-mortem (2026-05-12):** the Scribus-imported SLA was added as a
`reference_sla:` field and wired into the pipeline. Empirical measurement
showed it was 3-5pp WORSE than our converter on `visual_diff` vs
`baseline.pdf` (9.77%/11.50% vs 6.84%/6.30%). Agents repeatedly fell into
the "trust Scribus's choice" trap — including for `LINESPMode="1"` (wrong
leading strategy) and page dimensions (bleed extents). The SLA was removed
from `originals/` and all tooling (sla_inventory, three_way_audit,
reference_diff lane) was deleted on 2026-05-12.

### P4 — Structural completeness is a hard precondition for drift work.

Phase A audits (`inventory.yml`, `text_audit.yml`, `image_audit.yml`) must
show every IDML PageItem is either emitted by `build.py` OR explicitly
skipped with a documented reason. Drift convergence work that starts before
this is provably clean burns tokens diagnosing structural gaps as positioning
bugs.

### P5 — Generator over artifact. Re-emit beats hand-patch.

When `build.py` is wrong because `tools/idml_to_dsl.py` is wrong, fix
the converter and re-emit. Hand-edits to `build.py` are last resort,
must be captured in `inject.yml` with a `reason:` field (D5), and must
survive a re-emit + reconciliation. The committed `build.py` should
always be reproducible by `python3 tools/idml_to_dsl.py <idml> ... +
tools/reconcile_build_py.py <inject.yml>` — if it can't, the divergence
is unintentional drift and must be resolved.

### P6 — Single up-front visual review at iteration 0. Not loop-time.

A human (or a Sonnet-tier agent budget-capped at 4 image reads)
produces a manifest of expected elements per page on the FIRST import
of a new template. The convergence loop then runs against audit
reports + bbox JSON only — no visual review during iterations except
as documented dead-end fallback (Phase C3 reviewer pass excepted).

### P7 — Font fidelity is non-negotiable. pdffonts of preview.pdf MUST match pdffonts of baseline.pdf.

Any glyph rendered with a font Scribus chose via silent fallback is
**permanent drift** in `visual_diff` against `baseline.pdf`. Cross-engine
artifacts (ICC, text shaping) are real and small (~0.1-1pp); silent
font fallback is large and converter-fixable (~2-4pp per missing
variant).

**Discovered during issue #35 Phase R4 work (2026-05-12):** the
committed `build.py` had `font='Black'` as a Phase 4 "engine quirk
workaround" — but `pdffonts preview.pdf` showed NO `GothamNarrow-Bold`
embedded, while `pdffonts baseline.pdf` showed it. Every Bold-weight
Run in the IDML was rendering in a different weight (Book or Black).
Root cause: the converter dropped CSR `FontStyle` attributes when
composing font names. The "Scribus quirk" framing was misdiagnosis —
the actual issue was a missing converter feature, and the apparent
~6-7% "engine floor" was substantially inflated by silent font
fallback in body-text regions.

**Mandatory checks (Phase D6 — `tools/font_audit.py`):**
- After every render, run `pdffonts <preview.pdf>` and `pdffonts <baseline.pdf>`
- Strip subset prefixes (e.g., `DAZTTR+`) before comparison
- Diff the two font-name sets
- Any variant in baseline but not in preview = silent fallback = converter bug
- Block "engine floor" / convergence-stop claims while any variant is missing
- Emit `font_audit.yml` alongside the other audit reports

**Skill-level rule** (must be lifted into `/idml-import` and
`/convergence-loop` skills verbatim): a convergence-loop iteration
MUST NOT declare success or "engine floor reached" while
`font_audit.yml::missing_in_preview` is non-empty. Silent fallback
must be fixed at the converter (CSR FontStyle composition,
ParaStyle inheritance, etc.) before any drift number is interpreted
as cross-engine.

**Font installation invariant:** `fc-list` must enumerate every
font face the IDML references (verified by enumerating `<AppliedFont>`
+ CSR `FontStyle` pairs in `Stories/*.xml`). If a referenced face
is not installed, the import workflow stops with a clear
human-actionable message — never proceeds with a different face.

### P8 — Render-side content fidelity is non-negotiable.

pdftotext over preview.pdf MUST contain every word that appears in baseline.pdf
(modulo hyphenation tolerance — count tokens, not lines). Any word in baseline
but not preview signals Scribus suppression (frame-too-small, off-page,
color-on-color, z-order, threaded overflow, hidden layer, etc.). The convergence
loop MUST NOT declare success while text_render_audit.yml::missing_in_preview
is non-empty. Fix the converter to prevent the class of suppression — don't
hand-patch the template.

### P9 — Content-level diff before visual diff.

When visual_diff shows drift, consult content-level audits FIRST:
text_render_audit (presence), text_position_audit (per-word position deltas),
font_audit (per-font embedding), run_style_audit (per-Run font/size/color —
catches wrong font per word even when the variant is embedded and the text is
present), image_audit (raster + vector counts), and per_element_drift (per-slot
mismatch pixel contribution — tells you which named template slot is responsible
for the largest share of page mismatch so fix dispatches target the highest-
leverage element first). These answer "what's different" mechanically. Visual
review answers "how it looks", which is a much narrower question. Reach for the
rendered images only when all structured audits are clean and residual drift is
sub-percent.

## Scope

Five tools + two workflow changes, organised in three phases by
cost/leverage. Phases are independently shippable.

### Phase A — Pre-flight inventory (highest leverage, lowest cost)

**Three structural oracles that run before any convergence loop, all
token-free, all <1s wall-clock per template.**

#### A1. Spread-XML element inventory (`tools/idml_inventory.py`)

Parse `Spreads/Spread_*.xml` from the source IDML. Enumerate every
`PageItem` (`Rectangle`, `Polygon`, `Oval`, `TextFrame`, `Image`, `PDF`,
`Group`, `GraphicLine`) by `Self="uXXX"`. Diff against `anname='uXXX'` in
the emitted `build.py`. Emit a structural-completeness report:

```yaml
template: kandidat-falzflyer-din-lang-gruenes-cover-v2
spreads:
  - id: Spread_ueb
    page: 0
    elements_total: 47
    elements_emitted: 41
    elements_dropped:
      - {self: u3a8, type: Polygon, hint: "inline vector path, no <Image>/<PDF> child"}
      - {self: u3b1, type: TextFrame, hint: "story u3b3, 1 paragraph 'Leonore Gewessler'"}
      - ...
```

Catches dropped frames, dropped inline-vector elements, dropped TextFrames.

#### A2. PDF text inventory (`tools/baseline_text_audit.py`)

Run `pdftotext -layout baseline.pdf` per page, normalise whitespace, grep
each unique line against TextFrame `runs=` literal text in `build.py`.
Lines present in baseline but not in build.py = dropped text content.

Output: `text_audit.yml` per template with the unmatched-text list and the
nearest-match TextFrame anname (when a partial match exists).

Catches the Leonore Gewessler attribution case in one grep.

#### A3. PDF image inventory (`tools/baseline_image_audit.py`)

Run `pdfimages -list baseline.pdf` and `pdftocairo -svg` to enumerate
raster + vector content. Compare:
- Raster count vs `ImageFrame(image=…)` count in `build.py`
- Vector path count vs `Polygon` count in `build.py`
- Per-frame raster placement (when multiple `ImageFrame`s reference the
  same `image=` path with different `local_offset_mm`/`local_scale`):
  flag if N frames reference one image but only 1 unique offset → likely
  per-Image LocalOffset bug (the social-media-icons strip pattern).

Output: `image_audit.yml`.

Catches the wind-turbine pattern (vector in baseline, no Polygon emitted
for it) and the social-strip pattern (6 frames, same image, no per-frame
crop).

#### A4. Wire all three into `bin/render-gallery --audit`

New `--audit` flag runs A1+A2+A3 before the existing render+visual_diff
pipeline. Output landed next to `visual_diff.json`. Audit failures
**block** convergence loop entry — the executor must see structural
completeness before being allowed to fix drift.

### Phase B — Converter completeness + per-element baseline (medium cost, high leverage)

#### B1. `tools/idml_to_dsl.py` completeness assertion

The original D6 design raises `UnhandledElement` only on **unknown
tags**. It silently emits-nothing for known tags it can't handle (inline
vector paths, deeply nested groups, CSR bold inside ParaStyle Regular,
etc.). Change: at end of conversion, assert
`emitted_frame_count == idml_pageitem_count` and raise with the dropped
`Self` IDs listed.

The convertor author then either:
- Adds a code path for the new pattern (preferred), or
- Explicitly skips with a one-line `# IDML pattern <name>: skipped because
  <reason>` annotation that the assertion accepts.

#### B2. Per-slot baseline crops (`tools/snapshot_slot_baselines.py`)

After `meta.yml` slot bboxes are written, crop `baseline.pdf` per slot at
the gallery rasterisation DPI (150) and write to
`templates/<slug>/baselines/slot-uXXX.png`. The convergence loop then
diffs `dsl-page-N.png` cropped to slot bbox vs the per-slot baseline —
isolates per-slot drift from full-page cross-engine AA noise (which is
what dominated the issue #35 "engine floor" framing).

Side benefit: a per-slot image read costs ~5 KB vs ~200 KB for a full
hires page. Visual-review token cost drops ~40×.

#### B3. Bbox JSON `drift_type` field (`tools/diff_bbox_extract.py`)

Add a classification step:
- **`missing`**: bbox attributed to a background slot (`u1ae`, `u1fd`,
  etc.) AND the corresponding baseline area shows non-background content.
  Signals a dropped element.
- **`extra`**: bbox attributed to background, baseline area is background,
  DSL area has content. Signals a hallucinated element.
- **`position`** / **`scale`** / **`rotation`** / **`color`** / **`text`**:
  slot matches but pixels differ — classify by which axis dominates the
  delta (centroid shift / area ratio / angle / mean color delta / Levenshtein
  on OCR'd text in the bbox).

The convergence loop then routes `missing` bboxes to the inventory tools
(Phase A) instead of frame-parameter tuning. Routes `position`/`scale` to
the `_extract_content_local_params` helper. Etc.

### Phase D — IDML-side audits + inject overlay

**Note on removed sections (D1/D2/D3/D3a/D4):** Sections D1 through D4
described a `reference_sla:` / Scribus-imported SLA strategy (meta.yml
field, import GUI step, second visual_diff lane, three-way Venn audit).
This strategy was removed on 2026-05-12. Empirical measurement showed
Scribus's own IDML importer was 3-5pp WORSE than our converter on
`visual_diff` vs `baseline.pdf`. Agents repeatedly fell into the trap of
mirroring Scribus's choices (including wrong leading strategy and inflated
page dimensions) without verifying against `baseline.pdf`. The SLA file
was removed from `originals/`; all tooling (sla_inventory.py,
three_way_audit.py, reference_diff lane) was deleted. The IDML +
baseline.pdf two-source oracle stack is sufficient.

#### D5. `tools/reconcile_build_py.py` — INJECT_MAP overlay system

The committed `build.py` accumulated 373 lines of hand-edits across issue #35's phases 3-6; some are legitimate Scribus rendering workarounds, some are wrong (they dropped converter-emitted elements like `u2b0`). Reconciliation tool:

1. Re-emit `build.py` from IDML → `/tmp/fresh.py`.
2. Read `templates/<slug>/inject.yml` — an overlay listing hand-patches keyed by anname:
   ```yaml
   inject:
     u3b4:
       reason: "Phase 4 — Scribus Gotham Narrow Black renders worse than fallback; keep generic Black weight"
       overrides:
         font: "Black"
     u3a2:
       reason: "Phase 3 — Group transform u3a1 ascender correction (not Group cascade fix)"
       overrides:
         x_mm_delta: 5.05
   ```
3. Apply overlay to fresh re-emit → reconciled `build.py`.
4. Commit reconciled build.py + the inject.yml separately.

After this, every converter change can be re-run via `bin/idml-import` and the result is a fresh re-emit with documented overlays — no silent drift, no lost hand-patches.

#### D7. `tools/text_render_audit.py` — render-side word presence audit (P8)

Runs `pdftotext -layout` on both `preview.pdf` and `baseline.pdf`. Normalises
Unicode (NFC + Latin ligature folding: ﬁ→fi, ﬃ→ffi, ﬂ→fl, ﬀ→ff, ﬄ→ffl,
ﬅ/ﬆ→st) and lowercases. Builds per-word Counter dicts. Diffs to find words
present in baseline but missing (or under-counted) in preview.

Ligature folding ensures that a baseline PDF embedding ﬃ (U+FB03) and a
preview PDF using the decomposed sequence `ffi` tokenise to the same word —
preventing false-positive missing-word reports from ligature encoding
differences between renderers.

Catches: text emitted to build.py but Scribus silently suppressed — frame-too-
small clipping, off-page overflow, color-on-color invisibility, z-order occlusion,
threaded-frame overflow, hidden layers.

**Output:** `build/validation/<slug>/text_render_audit.yml`
```yaml
template: kandidat-falzflyer-din-lang-gruenes-cover-v2
baseline_word_count: 384
preview_word_count: 312
missing_in_preview:
  diegruenen: 2
  diegruenenaustria: 1
extra_in_preview: {}
ok: false
```

Wired into `render_pipeline.py::_run_audit` after D6 (`font_audit`). Runs
when both `preview.pdf` and `baseline.pdf` exist. Surfaced in `--audit` output.

#### D8. `tools/text_position_audit.py` — per-word position drift audit

Uses `pdfplumber.extract_words()` to get per-word bounding boxes from both
`preview.pdf` and `baseline.pdf`. For each baseline word, finds the nearest
matching preview word (same page, same text content) via greedy nearest-neighbour.
Computes (dx, dy) displacement in PDF points.

Default threshold: 2.0pt (≈ 0.7mm). Words with |dx| > threshold or
|dy| > threshold are reported as positioning bugs. Sub-threshold displacements
are filed as AA noise / OK. Words absent from preview are skipped (D7 handles
presence; D8 only audits position). Top 50 deltas by magnitude are included in
the report.

**Common-word filtering (default threshold=5):** Words appearing ≥ 5 times on
the same page in either PDF are excluded from `large_deltas` after matching.
These high-frequency words (lorem ipsum `et`, `qui`, `ut`, etc.) produce
spurious large deltas because the greedy nearest-neighbour matcher cross-binds
them across multi-column layouts. Unique content (candidate names, social
handles) appears only once per page, making the match reliable. The
`suppressed_common_word_deltas_count` field tracks how many were filtered.

Catches: text rendered but mis-positioned — alignment drift, group-transform
gaps (e.g. dx ≈ ±14.3pt = ±5.05mm from a missing Group ItemTransform cascade),
off-by-margin bugs, panel-offset coordinate origin errors (dx ≈ ±59pt = ±20.8mm).

**Output:** `build/validation/<slug>/text_position_audit.yml`
```yaml
template: kandidat-falzflyer-din-lang-gruenes-cover-v2
threshold_pt: 2.0
common_word_threshold: 5
large_deltas_count: 12
suppressed_common_word_deltas_count: 0
large_deltas:
  - text: Leonore
    page: 1
    baseline_xy_pt: [659.8, 1004.4]
    preview_xy_pt: [645.5, 1004.4]
    dx_pt: -14.3
    dy_pt: 0.0
    severity: large
ok: false
```

Wired into `render_pipeline.py::_run_audit` after D7 (`text_render_audit`).
Runs when both `preview.pdf` and `baseline.pdf` exist. Surfaced in `--audit` output.

### Phase E — Per-element drift attribution (`tools/per_element_drift.py`)

**Aggregation layer over diff_bboxes.json.** The bbox extractor (D6/issue #36)
attributes each detected mismatch region to a named slot (`attributed_slot`).
Phase E sums those per-slot, expresses each as a fraction of the page's total
mismatch, and writes a ranked `per_element_drift.yml` so fix dispatches target
the highest-leverage slots first.

**Purpose:** answers "which template element is responsible for the most
visual_diff mismatch?" without reading a single image. Complements P9
(content-level diff before visual) — mismatch pixel distribution is a
content-level signal derived from the bbox JSON oracle.

**Output schema** (`build/validation/<slug>/per_element_drift.yml`):

```yaml
template: kandidat-falzflyer-din-lang-gruenes-cover-v2
pages:
  - page: 0
    total_mismatch_pct: 8.0916
    total_mismatch_px: 176130
    bbox_count: 327
    top_contributors:
      - slot: u1ae
        mismatch_px_summed: 36951
        pct_of_page_mismatch: 20.98   # fraction of page mismatch in this slot
        pct_of_page_total_drift: 1.70  # fixing this slot drops page drift by ~1.7pp
        bbox_count: 244
      - slot: __unattributed__         # bboxes with no matching anname (background)
        ...
  - page: 1
    ...
```

Key fields:
- `pct_of_page_mismatch` — rank by this to choose what to fix next.
- `pct_of_page_total_drift` — the leverage number: "fixing this slot drops
  page drift by Xpp." Uses `visual_diff.json`'s authoritative `mismatch_pixels`
  as denominator (not the sum of bbox areas, which can differ due to overlap).
- `__unattributed__` — bboxes that didn't match any named slot; often
  background-color drift or AA noise between large un-named areas.
- Top 20 per page (long tail is sub-1% and not actionable).

**Wire-up:** `render_pipeline.py::_run_audit` runs Phase E after D8 when
`diff_bboxes.json` + `visual_diff.json` both exist. Prints a summary line per page:

```
[<slug>] per_element_drift: top contributor page 1 is u1ae (1.7pp of page drift)
```

Diagnostic only — never fails the audit (pass/fail is D8's job).

### Phase F — Per-Run style fidelity (`tools/run_style_audit.py`)

**Gap that D6 and D7 both miss:** D6 (`font_audit`) confirms each font variant
is EMBEDDED in preview.pdf. D7 (`text_render_audit`) confirms each word's TEXT
is rendered. Neither tells us WHICH FONT each word is rendered with. If a Run
that should be Vollkorn Black Italic 38pt yellow is accidentally emitted as
Gotham Narrow 38pt yellow, both audits pass but every glyph of that Run is
wrong. Phase F catches that class.

**Approach:** use `pdfplumber.extract_words(extra_attrs=["fontname", "size",
"non_stroking_color"])` on both PDFs. For each baseline word, find the matching
preview word (same page+text) via greedy first-available. Compare fontname
(subset-prefix stripped), size (within tolerance), and color.

**Severity heuristic:**
- `large`: fontname differs (after stripping PDF subset prefix like `DAZTTR+`)
  OR size differs > 1.0pt OR color RGB delta > 30
- `small`: size differs 0.5–1.0pt OR color RGB delta 5–30 (likely ICC artifact)
- not reported: within threshold

**Common-word filter (default threshold=5):** Words appearing ≥ 5 times on a
page in either PDF are excluded from `style_drifts` — high-frequency words
produce ambiguous greedy matches. `suppressed_common_word_drifts_count` tracks
excluded count (mirrors D8 logic).

**`ok` flag:** `false` when any `large`-severity drift exists. Small drifts are
surfaced but do not fail the audit (likely ICC/rounding).

**Output schema** (`build/validation/<slug>/run_style_audit.yml`):

```yaml
template: kandidat-falzflyer-din-lang-gruenes-cover-v2
baseline_word_count: 464
preview_word_count: 458
threshold_size_pt: 0.5
common_word_threshold: 5
style_drift_count: 12
suppressed_common_word_drifts_count: 0
style_drifts:
  - text: "Headline"
    page: 0
    baseline: {fontname: "GothamNarrow-Ultra", size: 37.93, color: "#ffffff"}
    preview:  {fontname: "GothamNarrow-Black", size: 37.93, color: "#ffffff"}
    drift: {fontname: "diff", size_pt: 0.0, color: false}
    severity: large   # WRONG FONT — converter bug
ok: false  # any large-severity drift fails
```

**Wire-up:** `render_pipeline.py::_run_audit` runs Phase F after D8
(`text_position_audit`) when both `preview.pdf` and `baseline.pdf` exist.
Prints a one-line summary:

```
[<slug>] run_style_audit: 3 large style drifts, 9 small drifts → REVIEW
```

Large drifts are added to `issue_parts` so `--audit-strict` surfaces them.

### Phase G — Per-region ICC-vs-fill-bug classification (`tools/region_color_audit.py`)

**Separates engine-floor noise from fixable fill-color bugs.** After per-element
drift attribution identifies which slots account for the most mismatch, Phase G
answers the next question: *is the remaining colour delta in a given region due
to ICC profile rendering drift (unfixable engine floor) or a wrong fill-color
emitted by the converter (fixable bug)?*

**Motivation:** Page 1 of the v2 falzflyer shows `visual_diff` at 8.09%.
Per-element drift names `u1ae` (1.70pp) and `u1fd` (1.26pp) as top contributors.
Without Phase G, these can't be distinguished from ICC drift — the agent might
waste cycles "fixing" something that's irreducible. Phase G samples the mean RGB
of each frame's bounding box in both baseline.pdf and preview.pdf (at 150 dpi)
and classifies the delta magnitude.

**Classification rubric (RGB units, 0-255 scale):**
- `ok`:          mean_delta < 3   — within rasterisation noise floor
- `icc_likely`:  3 ≤ delta < 15  — uniform small offset consistent with
                 CMYK→sRGB ICC profile rendering drift; engine floor, unfixable
- `fill_likely`: delta ≥ 15      — large concentrated delta; likely wrong fill-color
                 emitted by the converter; fixable

**Document-level pattern:**
- `predominantly_icc_drift`: icc_likely count ≥ 3× fill_likely count
- `concentrated_fill_bugs`:  fill_likely count ≥ 3
- `mixed`:                   neither dominates

**Output schema** (`build/validation/<slug>/region_color_audit.yml`):

```yaml
template: kandidat-falzflyer-din-lang-gruenes-cover-v2
by_severity:
  ok: 16
  icc_likely: 15
  fill_likely: 5
pattern: predominantly_icc_drift
frames:
  - anname: u1ae
    page: 0
    type: Polygon
    bbox_mm: [-1.8236, -1.8236, 298.8236, 213.6472]
    baseline_rgb: [55.7, 124.3, 66.8]
    preview_rgb:  [60.7, 127.9, 70.5]
    mean_delta: 4.09     # icc_likely: small uniform offset → engine floor
    rms_delta: 7.17
    severity: icc_likely
  - anname: u4da
    page: 1
    type: Polygon
    baseline_rgb: [156.9, 188.0, 164.8]
    preview_rgb:  [45.0, 108.3, 58.5]
    mean_delta: 99.3     # fill_likely: large delta → wrong fill color
    severity: fill_likely
```

**Wire-up:** `render_pipeline.py::_run_audit` runs Phase G after Phase E when
`preview.pdf` and `baseline.pdf` both exist. Prints summary line:

```
[<slug>] region_color_audit: 16 ok, 15 icc_likely, 5 fill_likely — pattern: predominantly_icc_drift
```

Diagnostic only — never fails the audit.

**Acceptance criteria:**
- [x] `tools/region_color_audit.py` exists; takes `--build-py`, `--baseline`,
      `--preview`, `--template`, `--out`; emits `region_color_audit.yml`
- [x] Per-frame mean RGB delta computed from pdftocairo 150dpi rasterisation
- [x] Severity classification: ok / icc_likely / fill_likely per threshold rubric above
- [x] Document pattern: predominantly_icc_drift / concentrated_fill_bugs / mixed
- [x] Frames sorted: fill_likely first, then icc_likely, then ok; within each group
      descending by mean_delta; top 40 emitted
- [x] Wired into `render_pipeline.py::_run_audit`; runs when both PDFs exist
- [x] YAML output deterministic (sort_keys=True, byte-identical on re-run)
- [x] 25 unit tests + 4 integration tests; all pass; runtime <5s on synthetic PDFs
- [x] V2 falzflyer `region_color_audit.yml` produced; u1ae and u1fd classified as
      `icc_likely` (mean_delta ~4) — background drift confirmed as engine floor

**Note for P9:** Phase G completes the content-level diff suite alongside
per_element_drift (Phase E). Together they answer "which element, what severity,
and what root cause?" before any pixel-level investigation.

### Phase C — Workflow + agent discipline (low cost, high recall)

#### C1. Single up-front visual review on import (`bin/idml-import`)

Wrap `tools/idml_to_dsl.py` + `tools/links_export.py` + a one-time
visual-comparison pass into a single `bin/idml-import <idml-path>` entry
point. The visual-comparison pass:

1. Renders baseline.pdf at 100dpi.
2. Renders the freshly-emitted DSL preview.pdf at 100dpi.
3. Concatenates baseline + DSL side-by-side per page.
4. Outputs `import-review-page-N.png` for the human / agent to scan
   **once** before any convergence work.

This is the "look at what's there" pass that issue #35 should have done in
iteration 0. Cost: ~30 s of rendering + 2 image reads.

#### C2. Per-iteration JSON trace (`build/<slug>/iteration.jsonl`)

Replace free-form EXECUTION.md tables with append-only JSONL:

```jsonl
{"iter": 1, "fix": "u3a8 inline vector path", "locus": "tools/idml_to_dsl.py:1234", "before": {"p1": 7.31, "p2": 6.31, "missing": 7}, "after": {"p1": 6.85, "p2": 6.31, "missing": 6}, "sha": "abc1234"}
```

Cheaper to read on agent resume; bisectable; tooling-friendly.

#### C3. Reviewer-not-executor split

Add a `bin/convergence-review` post-loop step. The executor commits its
work, then a separate (different agent context, fresh eyes) reviewer:
1. Reads `iteration.jsonl` + the final structural audit.
2. Re-runs A1+A2+A3 on the final state.
3. Approves the "engine floor" claim only if structural audit is clean
   AND no `missing`/`extra`/`text` drift_type bboxes remain.
4. Otherwise rejects and writes `REVIEW.md` listing what the executor
   missed.

Both issue #35 executors would have failed this gate. Cheap (one extra
agent pass per template) but catches the class of issue we just hit.

#### C4. Pattern library (`tools/idml_to_dsl_patterns/README.md`)

As converter handlers are added (Phases A-C feed this), document each
pattern with:
- Source IDML XML structure (1-3 lines)
- Emitted DSL primitive
- Regression test path
- One-line "what to look for" if the pattern recurs

Patterns from issue #35 + Phase B fixes:
- `inline_vector_path` — Polygon/Path with stroke/fill, no Image child
- `group_transform_cascade` — child positions need parent Group ItemTransform applied
- `per_image_local_offset` — `<Image>` child carries crop transform inside `<Rectangle>`
- `csr_bold_in_paragraph` — CharacterStyleRange FontStyle="Bold" inside ParagraphStyleRange Regular
- `dropped_attribution_textframe` — TextFrame inside a Group that converter walks past
- `psd_icc_color` — CMYK PSD needs ICC-aware sRGB conversion via Pillow ImageCms
- `vector_ai_to_png` — `.ai` file rasterised via `pdftocairo -png -transp -r 600 -singlefile`

After 3-5 templates the library covers ~90% of IDML patterns; converter
gaps become rare instead of routine.

## Acceptance Criteria

### Phase A
- [ ] `tools/idml_inventory.py` exists, runs against any IDML, emits
      `inventory.yml` with element counts + dropped-element list
- [ ] `tools/baseline_text_audit.py` exists, runs against any baseline.pdf
      + build.py pair, emits `text_audit.yml` with unmatched-text list
- [ ] `tools/baseline_image_audit.py` exists, runs against any
      baseline.pdf + build.py pair, emits `image_audit.yml`
- [ ] `bin/render-gallery --audit` runs A1+A2+A3, blocks pipeline on
      audit failure
- [ ] Audit reports for `kandidat-falzflyer-din-lang-gruenes-cover-v2`
      surface ALL 7 bugs from issue #35 visual-review (turbine, bullets,
      curly quotes, attribution, social-strip, pine-forest, group-transform)

### Phase B
- [ ] `tools/idml_to_dsl.py` end-of-conversion assertion: emitted-frame
      count == IDML PageItem count (or each gap explicitly skipped with
      reason annotation)
- [ ] `tools/snapshot_slot_baselines.py` exists; per-slot PNG crops
      written under `templates/<slug>/baselines/`
- [ ] `tools/diff_bbox_extract.py` adds `drift_type` classification field
      with at least 6 categories (missing/extra/position/scale/color/text)
- [ ] Tests cover each classification path

### Phase C
- [ ] `bin/idml-import <idml-path>` single entry point: extracts links,
      runs converter, renders both PDFs, writes `import-review-page-N.png`
- [ ] `build/<slug>/iteration.jsonl` written by the convergence loop
      instead of free-form EXECUTION.md tables (EXECUTION.md still gets a
      summary section per phase)
- [ ] `bin/convergence-review` post-loop reviewer step exists; blocks
      "engine floor" claim if audit not clean
- [ ] `tools/idml_to_dsl_patterns/README.md` library exists with at least
      the 7 patterns listed above

### Phase D — Inject overlay
- [ ] `tools/reconcile_build_py.py` reads `templates/<slug>/inject.yml`,
      applies overlays to fresh converter emit, produces reconciled
      build.py with provenance comments

### Phase D6 — Font fidelity (P7 enforcement)
- [ ] `tools/font_audit.py` exists; takes `preview.pdf` + `baseline.pdf`
      paths, emits `font_audit.yml` with baseline/preview font sets,
      missing_in_preview list, extra_in_preview list, ok flag
- [ ] Subset prefixes (e.g. `DAZTTR+`) stripped before comparison
- [ ] Wired into `bin/render-gallery --audit` and runs alongside the
      structural audits; output: `font_audit.yml` next to
      `visual_diff.json`
- [ ] Audit summary line surfaces missing-variant count:
      `[<slug>] font_audit: N missing variant(s) (silent fallback) → FAIL`
- [ ] Pytest coverage: identical sets pass, missing variant fails,
      subset-prefix stripping, malformed pdffonts output handling
- [ ] `bin/idml-import` (Phase D2) checks `fc-list` for every
      `<AppliedFont>` + CSR `FontStyle` pair referenced in the IDML's
      Stories — stops with human-readable error if any face missing
- [ ] V2 falzflyer's `font_audit.yml` shows `ok: true` after the CSR
      FontStyle converter fix (Phase R5)

### Phase D7 — Render-side text presence (P8 enforcement)
- [ ] `tools/text_render_audit.py` exists; takes `preview.pdf` + `baseline.pdf`
      paths + `--template` slug, emits `text_render_audit.yml` with
      `baseline_word_count`, `preview_word_count`, `missing_in_preview` (dict),
      `extra_in_preview` (dict), `ok` flag
- [ ] Word extraction uses `pdftotext -layout`, NFC normalisation + Latin
      ligature folding (ﬁ→fi, ﬃ→ffi, ﬂ→fl, ﬀ→ff, ﬄ→ffl, ﬅ/ﬆ→st),
      lowercase; tokenisation regex `[\w@.\-]+`
- [ ] Ligature folding must be tested: baseline with ﬃ-ligature and preview
      with decomposed `ffi` must count as the same word (no false positive)
- [ ] `ok: true` iff `missing_in_preview` is empty
- [ ] Wired into `render_pipeline.py::_run_audit` after D6; runs when both
      `preview.pdf` and `baseline.pdf` exist; failure surfaces in `--audit` output
- [ ] YAML output is deterministic (byte-identical on re-run; `sort_keys=True`)
- [ ] Pytest coverage: identical PDFs pass; missing word fails; extra word
      reported but ok=True; NFC normalisation; case insensitivity; subprocess
      error on missing PDF raises CalledProcessError; ﬃ→ffi ligature folding;
      ﬁ→fi ligature folding; all 7 ligatures in U+FB00–U+FB06 range
- [ ] Convergence loop MUST NOT declare success while `missing_in_preview`
      is non-empty (P8) — surfaced as `issue_parts` entry in `--audit-strict`

### Phase D8 — Per-word position drift
- [ ] `tools/text_position_audit.py` exists; uses `pdfplumber.extract_words()`;
      takes `preview.pdf` + `baseline.pdf` paths + `--template` + `--threshold`
      (default 2.0pt) + `--common-word-threshold` (default 5);
      emits `text_position_audit.yml`
- [ ] Output keys: `template`, `baseline_pdf`, `preview_pdf`, `threshold_pt`,
      `common_word_threshold`, `large_deltas_count`,
      `suppressed_common_word_deltas_count`, `large_deltas` (list, max 50), `ok`
- [ ] Common-word filter: words appearing ≥ `common_word_threshold` times on the
      same page in either PDF are excluded from `large_deltas` after matching;
      `suppressed_common_word_deltas_count` records excluded count
- [ ] Common-word filter must be tested: word appearing ≥ threshold times
      excluded; unique words with large delta still reported
- [ ] Each `large_delta` entry: `text`, `page`, `baseline_xy_pt`, `preview_xy_pt`,
      `dx_pt`, `dy_pt`, `severity: large`
- [ ] Greedy nearest-neighbour match: one preview word is consumed at most once
      per baseline word (prevents double-counting when the same word repeats)
- [ ] Words absent from preview are skipped (D7 handles presence)
- [ ] `large_deltas` list sorted by total magnitude `|dx| + |dy|` (largest first)
- [ ] Wired into `render_pipeline.py::_run_audit` after D7; runs when both
      `preview.pdf` and `baseline.pdf` exist; failure surfaces in `--audit` output
- [ ] YAML output is deterministic (byte-identical on re-run; `sort_keys=True`)
- [ ] `pdfplumber` must be a declared dependency in `Dockerfile.claude` or
      `requirements.txt` — do not silently `pip install`
- [ ] Pytest coverage: identical positions pass; >threshold shift reported with
      correct dx/dy; <threshold not reported; missing word skipped; multiple
      instances of same word use greedy nearest-match without double-counting;
      common-word filter excludes high-frequency words; unique word with large
      delta still reported; `suppressed_common_word_deltas_count` matches count filtered
- [ ] V2 falzflyer `text_position_audit.yml` produced; `large_deltas_count`
      reported (non-zero count expected given current layout drift state;
      surfaced as signal for R8/R9 positioning fix work)

### Phase E — Per-element drift attribution
- [x] `tools/per_element_drift.py` exists; reads `diff_bboxes.json` + `visual_diff.json`;
      emits `per_element_drift.yml` with ranked per-slot `mismatch_px_summed`,
      `pct_of_page_mismatch`, `pct_of_page_total_drift`, `bbox_count`
- [x] Percentages use `visual_diff.json`'s authoritative `mismatch_pixels` as
      denominator (not summed bbox areas, which differ due to overlap)
- [x] Bboxes with null `attributed_slot` collected under `__unattributed__`
- [x] `top_contributors` sorted descending by `mismatch_px_summed`; capped at 20
- [x] Wired into `render_pipeline.py::_run_audit` after D8; runs when
      `diff_bboxes.json` + `visual_diff.json` both exist; diagnostic only (never fails audit)
- [x] Prints summary line per page: top contributor slot + pp contribution to page drift
- [x] V2 falzflyer `per_element_drift.yml` produced; top contributors on page 1 are
      u1ae/u1c7/u1fd; on page 2 are u2cd/u295/u265/u3a2 (known hotspots)
- [x] 9 unit tests + 4 integration tests; runtime <2s on v2 falzflyer data
- [x] Deterministic YAML output (sort_keys=True, no timestamps)

### Phase F — Per-Run style fidelity
- [x] `tools/run_style_audit.py` exists; uses `pdfplumber.extract_words()` with
      `extra_attrs=["fontname","size","non_stroking_color"]`; takes `preview.pdf` +
      `baseline.pdf` + `--template` + `--threshold-size` (default 0.5pt) +
      `--common-word-threshold` (default 5); emits `run_style_audit.yml`
- [x] Output keys: `template`, `baseline_word_count`, `preview_word_count`,
      `threshold_size_pt`, `common_word_threshold`, `style_drift_count`,
      `suppressed_common_word_drifts_count`, `style_drifts` (list), `ok`
- [x] Each `style_drift` entry: `text`, `page`, `baseline` (fontname/size/color),
      `preview` (fontname/size/color), `drift` (fontname/size_pt/color), `severity`
- [x] Subset-prefix stripping: `DAZTTR+GothamNarrow-Bold` → `GothamNarrow-Bold`
- [x] Color normalisation: RGB tuple → `#rrggbb`; gray float → `gray:N`; CMYK →
      `cmyk:C,M,Y,K`; None → `""`
- [x] Severity: large = fontname differs OR size_diff > 1.0pt OR RGB delta > 30;
      small = size diff 0.5–1.0pt OR RGB delta 5–30; None = sub-threshold
- [x] `ok: false` when any large-severity drift exists; small-only → ok=true
- [x] Common-word filter (same logic as D8): words >= threshold excluded;
      `suppressed_common_word_drifts_count` records count
- [x] Greedy match: each preview word consumed at most once per baseline word
- [x] Words absent from preview are skipped (D7 handles presence)
- [x] YAML output is deterministic (sort_keys=True, stable across two runs)
- [x] Wired into `render_pipeline.py::_run_audit` after D8; large drifts added
      to `issue_parts` for `--audit-strict`; runs when both PDFs exist
- [x] 15 unit tests + 6 integration tests; runtime <3s on v2 falzflyer
- [x] V2 falzflyer `run_style_audit.yml` produced; `ok: true` with 0 style
      drifts — confirms current font encoding is correct after R4/R5 fixes

### Phase G — Per-region ICC-vs-fill-bug classification
- [x] `tools/region_color_audit.py` exists; takes `--build-py`, `--baseline`,
      `--preview`, `--template`, `--dpi` (default 150), `--out`;
      emits `region_color_audit.yml`
- [x] Per-frame mean RGB delta computed from pdftocairo 150dpi rasterisation
- [x] Severity thresholds: ok (< 3), icc_likely (3-14), fill_likely (≥ 15)
- [x] Pattern classification: predominantly_icc_drift / concentrated_fill_bugs / mixed
- [x] Frames sorted fill_likely → icc_likely → ok; descending by mean_delta;
      top 40 emitted
- [x] Wired into `render_pipeline.py::_run_audit` after Phase E; diagnostic only
      (never fails audit); runs when preview.pdf + baseline.pdf + build.py exist
- [x] YAML output deterministic (sort_keys=True, byte-identical on re-run)
- [x] 25 unit tests + 4 integration tests; all pass
- [x] V2 falzflyer result: 16 ok, 15 icc_likely, 5 fill_likely;
      pattern: predominantly_icc_drift
- [x] u1ae (page 1 background): severity icc_likely, mean_delta=4.09 — engine floor
- [x] u1fd (page 1 overlay): severity icc_likely, mean_delta=4.28 — engine floor
- [x] The 1.7pp + 1.26pp background contribution to visual_diff is UNFIXABLE
      ICC drift, not a converter fill-color bug

### Cross-cutting
- [ ] All new tools have pytest coverage (repo idiom, not unittest —
      see Phase 2 EXECUTION.md note in issue #35)
- [ ] Re-run convergence on `kandidat-falzflyer-din-lang-gruenes-cover-v2`
      with the new tooling: total wall-clock under 1 hr, all 7 issue-#35
      bugs caught BEFORE the convergence loop starts (i.e., by Phase A
      audits or Phase C up-front review)

## Out of scope

- Auto-fixing the bugs the audits surface — converter handlers for
  inline-vector / group-transform / etc. are issue #35 follow-up work
  (the agent currently running on background ID `ab7ff5b39747dd8f2` is
  attacking those specifically). This issue ships the **detection** layer.
- General-purpose Indesign feature support beyond what the existing
  IDML→DSL converter targets
- A round-trip DSL→IDML exporter
- Replacement of `tools/visual_diff.py` — extension only
- Changes to `tools/sla_lib/builder/*` primitives — those are stable

## References

- Issue #35 (`IDML to DSL converter — strict bootstrap`) — the
  `EXECUTION.md` Phase 3 section + the convergence-loop post-mortem in
  this conversation surfaced every requirement here
- Issue #36 (`Visual-diff bbox extractor with slot attribution`) —
  Phase B3 extends `tools/diff_bbox_extract.py`
- `tools/sla_lib/builder/bbox.py` — slot-bbox computation reused by
  Phase B2 per-slot baseline crops
- `tools/audit_alignment.py` — same architectural shape as Phase A
  audit tools (per-template structural reports)
- IDML spec PDF: see issue #35 RESEARCH.md
- SimpleIDML library: https://pypi.org/project/SimpleIDML/

## Estimated effort

- Phase A: 1 day (3 small CLI tools, all use existing libraries)
- Phase B: 1 day (assertion + slot crops + drift_type classification)
- Phase C: 0.5 day (workflow wiring + pattern library scaffold)

**Total: 2.5 days for the full ship.** Phase A alone (1 day) would have
prevented the 5-hour multi-agent loss on issue #35; that's the
highest-priority ship.

## Phase E2 — Line-spacing reconciliation (added 2026-05-12 after v2 falzflyer work)

**Bug class** discovered: IDML CSR `<Leading>` value does NOT match the
actual line spacing InDesign renders. On v2 falzflyer, CSR `<Leading>14.3</Leading>`
on body text → InDesign renders at constant **16.00pt** baseline-to-baseline.
The 1.7pt-per-line difference accumulates to ~50pt drift by line 30, making
multi-line body paragraphs the largest convergence obstacle.

**Confirmed contributors** (none of these explain 16pt directly):
- `<TextDefault AutoLeading="120">` (120% would give 13.2pt for 11pt font)
- `<BaselineFrameGridIncrement="12">` with `UseCustomBaselineFrameGrid="false"`
- `<LeadingModel>LeadingModelAkiBelow</LeadingModel>` (Japanese aki-below model)

**Hypothesis**: the Fließtext ParagraphStyle has an implicit grid alignment
or `LeadingAki`/`TrailingAki` that compounds with the CSR Leading to produce
the rendered 16pt.

### Converter-detection signal (no visual review required)

The converter cannot rely on CSR `<Leading>` alone. **Detection mechanism**:

1. **Parse ParagraphStyle's effective Leading**: read `<Leading>` from the
   ParagraphStyle AND its `BasedOn` chain. If any ancestor explicitly
   overrides Leading, that wins.

2. **Read LeadingAki / TrailingAki**: in IDML CSR Properties, look for
   `<LeadingAki type="unit">N</LeadingAki>` and `<TrailingAki>` on the
   relevant ParagraphStyle and CSR. These add extra leading above/below
   the line. Effective leading = `<Leading>` + `<LeadingAki>` + `<TrailingAki>`
   (if positive, else 0).

3. **Read LeadingModel**: `LeadingModelAkiBelow` means aki applies AFTER
   the line (vs centered). Compute effective baseline-to-baseline distance:
   ```
   if LeadingModel == "LeadingModelAkiBelow":
       effective_linesp_pt = CSR.Leading + max(0, CSR.TrailingAki)
   else:  # Default "above" model
       effective_linesp_pt = CSR.Leading + max(0, CSR.LeadingAki)
   ```

4. **Pragmatic fallback** (when computation doesn't match observed):
   measure baseline.pdf's first 3 consecutive lines in a body-text frame
   via pdfplumber. Compute baseline-to-baseline gap. If gap differs from
   computed effective_linesp by >1pt, emit the measured value as
   `linesp_override_pt` in the ParaStyle.

### Skill-level rule for `/idml-import`

> When emitting body-text ParaStyles, the skill MUST verify the rendered
> line spacing matches the IDML's intent. Concretely: after the first
> `bin/render-gallery --audit` run on a new template, the skill compares
> the first body-text frame's measured line spacing (from pdfplumber on
> baseline.pdf) against the emitted `LINESP`. If they differ by >0.5pt,
> override the ParaStyle's `linesp` to match the baseline measurement
> and document it as a per-template injection in `inject.yml` (or
> equivalent) with the measurement evidence.

### New Phase E2 audit tool — `tools/line_spacing_audit.py`

Sibling to D7/D8/F/G. Per body-text frame:
- Extract first 3 consecutive word lines from baseline.pdf via pdfplumber
- Compute baseline-to-baseline pt gap (median of pairs)
- Compute same for preview.pdf
- Report frames where `|preview_linesp - baseline_linesp| > 0.5pt`
- For each flagged frame: report the frame's anname, ParaStyle, IDML CSR
  Leading, baseline measured spacing, preview measured spacing,
  recommendation (LINESP override value).

Output `line_spacing_audit.yml`:
```yaml
template: kandidat-falzflyer-din-lang-gruenes-cover-v2
line_spacing_drift:
  - anname: u1c7
    para_style: idml/fliesstext-auf-gruenem-hintergrund
    idml_csr_leading_pt: 14.3
    baseline_linesp_pt: 16.0
    preview_linesp_pt: 14.3
    delta_pt: 1.7
    recommendation: "override ParaStyle linesp to 16.0"
ok: false
```

**Acceptance**:
- `tools/line_spacing_audit.py` exists, runs in <2s
- Wired into `bin/render-gallery --audit`
- For each ParaStyle with `>0.5pt` drift, emits a clear override recommendation
- v2 falzflyer test: must flag the original 14.3pt mismatch before the fix

## Backport 9 — Justification → Scribus align mapping (added 2026-05-12)

**Bug class** discovered: converter emits `align=3` (Scribus "Justified",
fully-justified text filling each line) for body-text ParaStyles where
baseline.pdf renders left-aligned (ragged right). Adobe's H&J engine
produces different word spacing than Scribus's when both are "justified",
causing cumulative horizontal drift along each line — and the design
likely intends left-align anyway.

**Largest single-fix drift drop** of v2 falzflyer convergence session
(2026-05-12): `align 3→0` on `idml/fliesstext-auf-gruenem-hintergrund`
and `idml/absatzformat-1` cut page 1 drift by 1.18pp, page 2 by 1.29pp,
and reduced text_position_audit large_deltas by 141.

**Converter detection** (no visual review required):

1. Read the IDML ParagraphStyle's `Justification` attribute (and inherit
   through `BasedOn` chain if needed).
2. Map to Scribus `align`:
   - `LeftAlign` → `align=0`
   - `CenterAlign` → `align=1`
   - `RightAlign` → `align=2`
   - `LeftJustified` / `CenterJustified` / `RightJustified` / `FullyJustified`
     → `align=3` (or whichever Scribus enum matches — verify)
   - `ToBindingSide` / `AwayFromBindingSide` → `align=0` (treat as left)

3. Default if Justification is absent on the style: `align=0`.

**Acceptance**:
- `tools/idml_to_dsl.py` reads `<ParagraphStyle Justification="...">` from
  `Resources/Styles.xml` correctly (not just from PSR inline overrides).
- Regression test exercises the mapping for each Justification enum
  value.
- v2 falzflyer test: the `fliesstext-auf-gruenem-hintergrund` style must
  emit `align=0` (not 3), assuming the IDML's actual Justification is
  `LeftAlign` (verify before fixing — could be `LeftJustified` with
  design intent of left-align, in which case it's an IDML authoring
  issue rather than converter bug).

## Backport 10 — ImageFrame SCALETYPE default for small icon PNGs (added 2026-05-12)

**Bug class** discovered: small (< ~12pt frame) white-on-transparent RGBA
PNGs render as INVISIBLE in Scribus 1.6.x exported PDF when
`SCALETYPE="1"` (free scaling, the converter default via
`tools/sla_lib/builder/primitives.py:ImageFrame.scale_type=1`). The image
embeds as a CMYK JPEG + smask in the PDF stream, but the CMYK plane
encodes the visible glyph pixels at `(63, 86, 93, 13)` instead of white
`(0, 0, 0, 0)`, and the smask compositing produces no visible mark on
the page. Switching the same frame to `SCALETYPE="0"` (scale-image-to-
frame) renders the icon correctly white-on-transparent.

**Symptom on v2 falzflyer**: all 6 social-media icons (u3e7 Facebook,
u3f0 Instagram, u3f5 TikTok, u477 BlueSky, u4a2 website, u4da mail)
invisible in preview.pdf despite being correctly embedded as CMYK
images. Confirmed by pdfimages -list (6 cmyk 866×866/865×865 images
with smasks) and visual inspection at 600 DPI.

**Root cause**: Scribus's SCALETYPE=1 (free scaling) path applies a
different ICC color-management pipeline when the source image is
substantially larger than the destination frame (here, 866px source
into 9.5pt = ~79px @ 600dpi frame, ~11× downscale via LOCALSCX). The
SCALETYPE=0 path (auto fit-to-frame) avoids this pipeline and renders
white pixels as white CMYK.

Verified: same PNG renders correctly at SCALETYPE=0 with no other
changes. PRFILE manipulation (removing the ICC profile entirely),
re-cropping PNGs to match the working bluesky-weiss.png byte structure
(865×865 RGBA + sRGB chunk), converting to CMYK TIFF, and using the
source AI/PDF as ImageFrame all FAILED. Only SCALETYPE=0 fixed it.

**Workaround already shipped** (2026-05-12, v2 falzflyer build.py):
hand-patched `scale_type=0` on all 6 icon ImageFrames. P5/inject
comment placed inline on u3e7 explaining the bug; same fix repeated
verbatim on u3f0/u3f5/u477/u4a2/u4da.

**Converter detection** (no visual review required):

1. The IDML ItemTransform extraction in
   `_emit_image_content` already derives `local_scale`. When the
   derived `local_scale` falls below ~0.15 in either axis (i.e. the
   IDML intent is to downscale the source by more than ~6×), emit
   `scale_type=0` instead of relying on the SCALETYPE=1 default.
   Threshold tunable; v2 falzflyer values are 0.091589 (icons) and
   0.095788 (icons) — comfortably below 0.15.
2. ALTERNATIVE: flip the `ImageFrame` dataclass default in
   `tools/sla_lib/builder/primitives.py` from `scale_type=1` to
   `scale_type=0`. Inventory of v2 falzflyer + existing templates
   shows the vast majority of ImageFrames either already pass
   `scale_type=0` explicitly OR omit it entirely (in which case
   fit-to-frame is the intended behavior anyway). Only 1 of 60+
   ImageFrames across all templates explicitly uses `scale_type=1`
   (u3a0 plakat-dunkel in v2 falzflyer, which intentionally uses
   free scaling for a fill-cover crop). Switching the default
   would correctly capture the common case and isolate explicit
   free-scaling to its single legitimate user.

**Recommendation**: do BOTH — change the dataclass default to 0, AND
have the converter set `scale_type=0` explicitly when emitting
ImageFrames (so the SLA is explicit rather than relying on the
default). The dataclass default change is the safety net.

**Acceptance**:
- `tools/sla_lib/builder/primitives.py:ImageFrame.scale_type` defaults
  to 0.
- `tools/idml_to_dsl.py` emits `scale_type=0` explicitly in all
  ImageFrame calls (the IDML never expresses "free scaling vs fit-to-
  frame" as a distinct concept; the local_scale alone captures intent).
- Regression test renders a 10×10pt frame containing a 800×800 white-
  on-transparent RGBA PNG and verifies the rendered region contains
  white pixels (not dark CMYK invisibility).
- v2 falzflyer test: all 6 icon ANNAMEs (u3e7/u3f0/u3f5/u477/u4a2/u4da)
  emit `SCALETYPE="0"` in the generated SLA.

**Drift impact**: small numerically (~0.05pp on page 2 of v2 falzflyer)
but UX-critical — the icons are part of the contact-info row and are a
visible regression noticed during human review. Page 2 drift dropped
from 2.47% → 2.42% after the fix.

## Backport 11 — Multi-line center-aligned headlines need per-paragraph ALIGN markers (added 2026-05-12)

**Bug class**: when an IDML headline TextFrame contains a single
`<Content>` text long enough that Scribus auto-wraps it across 2+
lines AND the ParaStyle has `align=center` (Scribus `ALIGN="1"`),
only the LAST line of the rendered output is actually center-aligned.
Lines preceding the last (whether reached via auto-wrap OR explicit
`<breakline/>`) render left-aligned despite the DefaultStyle PARENT
declaring center alignment.

**Symptom on v2 falzflyer**: u376 "Headline in einem grünen Kasten"
wraps to 2 lines inside its 149.33pt-wide green box. Line 1
("Headline in einem grünen") renders left-aligned at x0 ≈ 61pt; line
2 ("Kasten") renders correctly centered at x0 ≈ 118pt. Baseline.pdf
centers both. Splitting the single Content into 2 ITEXTs separated
by `<breakline/>` did NOT fix it. Adding `trail_attrs={'ALIGN': '1'}`
also did not fix it (the trail only applies to the last unterminated
paragraph).

**Fix that works**: set `ALIGN="1"` on the `<DefaultStyle/>` element
of the StoryText. This is REQUIRED because the trail's ALIGN and the
last-paragraph `<para ALIGN="1"/>` attributes do NOT propagate to the
paragraph they terminate — only paragraphs that have been previously
CLOSED via `<para ALIGN=.../>` get the attribute. The DefaultStyle's
ALIGN attribute applies to every paragraph in the StoryText, fixing
both the first paragraph (auto-wrap line 1) AND the last paragraph
(line 2 "Kasten"). Tested 2026-05-12 on u376 — both lines render
centered with x0 = 67.97 / 117.42 (matching baseline 68.54 / 117.99
within rendering tolerance).

```python
# BEFORE — breakline-based, only line 2 centers
runs=[
    Run(text='Headline in einem grünen', ...),
    Run(text='', has_itext=False, separator='breakline'),
    Run(text='Kasten', ...),
],
trail_attrs={'ALIGN': '1'},

# AFTER — DefaultStyle ALIGN + per-paragraph ALIGN, both lines center
default_style_attrs={'ALIGN': '1'},
runs=[
    Run(text='Headline in einem grünen', ...,
        paragraph_style='idml/headline-in-gruenem-kasten',
        paragraph_attrs={'ALIGN': '1'},
        separator='para'),
    Run(text='Kasten', ...,
        paragraph_style='idml/headline-in-gruenem-kasten',
        paragraph_attrs={'ALIGN': '1'},
        separator='para'),
],
trail_attrs={'ALIGN': '1'},
```

The `default_style_attrs={'ALIGN': '1'}` is the critical fix; the
per-paragraph `paragraph_attrs={'ALIGN': '1'}` on each Run is
defense-in-depth (explicit-over-default).

**Converter detection** (no visual review required):

1. Read the IDML ParagraphStyle's `Justification` (and inherited
   defaults). Map the value (`CenterAlign`, `RightAlign`, etc.) to
   the Scribus ALIGN integer (see Backport 9 for the mapping).
2. ALWAYS emit the mapped ALIGN on the TextFrame's `<DefaultStyle/>`
   element. This is the most reliable mechanism for non-left
   alignment — covers single-paragraph auto-wrap, multi-paragraph
   stories, and edge cases the per-paragraph `<para/>` attributes
   don't cover.
3. ADDITIONALLY emit `paragraph_attrs={'ALIGN': N}` on each `<para/>`
   for any paragraph whose effective ALIGN differs from `LeftAlign`.
   Defense-in-depth — Scribus reads per-paragraph attrs first, then
   falls back to DefaultStyle; having both makes the SLA explicit
   and survives future Scribus refactors.

**Acceptance**:
- `tools/idml_to_dsl.py` emits `default_style_attrs={'ALIGN': N}` on
  every TextFrame whose ParaStyle's effective Justification maps to
  non-left alignment.
- ADDITIONALLY emits explicit `paragraph_attrs={'ALIGN': N}` per
  `<para/>` for any paragraph whose effective ALIGN is non-zero.
- Regression test: a 100pt-wide TextFrame containing a 150pt-wide
  string with center-aligned ParaStyle produces 2 lines, both
  center-aligned at x ≈ 25pt offset from frame left.
- v2 falzflyer test: u376 renders "Headline in einem grünen" and
  "Kasten" both centered (x0 of "Kasten" ≈ 118pt, ±2pt tolerance).

**Drift impact**: small numerically (within fuzz_pct=25 tolerance,
≈0.0pp on the page-wide diff metric) but UX-critical — the
left-aligned wrap is a visible authoring bug. This finding
motivates Backport 12 below (per-region visual_diff).

## Backport 12 — Per-region visual_diff (added 2026-05-12)

**Motivation**: the current `tools/visual_diff.py` reports a single
page-wide `mismatch_pct` per page. Localized fidelity issues get
washed out: the Kasten centering fix (Backport 11) and the icon
visibility fix (Backport 10) BOTH produced visually obvious before/
after differences that humans flagged on inspection, yet the
page-wide metric moved by 0.0pp and 0.05pp respectively. Without a
per-region signal it is hard to:

1. **Detect regressions whose absolute pixel footprint is small but
   whose semantic impact is large** (a misaligned headline, an
   invisible icon row, a missing inline glyph). These are exactly
   the issues human reviewers catch first.
2. **Attribute drift to specific design slots** during convergence
   loops. The existing per-element drift tooling
   (`tools/per_element_drift.py`) works at the IDML PageItem level,
   not at the rendered pixel level.
3. **Prioritise fixes**: if region (col 2, row 3) shows 18%
   mismatch and (col 1, row 1) shows 0.4%, the human knows where
   to look. Page-wide 2.42% gives no spatial signal.

**Proposed tool**: extend `tools/visual_diff.py` (or add a
companion `tools/visual_diff_regions.py`) that:

1. Renders preview and baseline at the same DPI (already done).
2. Splits each page into a configurable grid (default: 6 columns
   × 4 rows = 24 regions per page; tunable per-template via
   `diff.yml`). Region size chosen so each region is roughly a
   "design slot": headline, body column, image, contact row.
3. For each region: computes `mismatch_pixels`, `mismatch_pct`,
   plus the existing fuzz_pct tolerance check.
4. Emits a per-region heatmap PNG (24 cells colored by
   mismatch_pct) plus a per-region YAML report:
   ```yaml
   visual_diff_regions:
     page: 0
     grid: {cols: 6, rows: 4}
     regions:
       - {col: 0, row: 0, mismatch_pct: 0.4, pass: true}
       - {col: 3, row: 2, mismatch_pct: 18.7, pass: false}  # likely problem area
       - ...
     hot_regions: [{col: 3, row: 2, mismatch_pct: 18.7}, ...]
   ```
5. Per-region thresholds: optional `diff.yml` per-cell override
   (e.g. a region known to contain a halftone gradient can use
   higher fuzz). Default = same threshold as page-wide.

**Where it slots into Phase A**: this is a Phase A audit tool
(structural/visual oracle) — it consumes preview.pdf + baseline.pdf
and emits a YAML report. It runs AFTER per-element drift (which
attributes to IDML elements) and BEFORE manual visual review.

**Tie-in with `tools/diff_bbox_extract.py`** (issue #36/PR #75):
the bbox extractor identifies geometric regions in the diff.
Per-region visual_diff is the COMPLEMENT — it samples a regular
grid rather than extracting dynamic bboxes. The two should be used
together: bbox extractor surfaces ANOMALY shapes; grid sampling
gives a stable spatial map you can diff across builds.

**Acceptance**:
- `bin/render-gallery` (or a follow-up `--audit` flag) produces
  `visual_diff_regions.yml` alongside `visual_diff.json`.
- The heatmap PNG renders to `templates/<slug>/visual_diff_regions-page-NN.png`.
- A regression test with a controlled "small localized diff"
  (e.g. shift a single 9pt headline by 50pt) produces a region
  with > 10% mismatch even when page-wide is < 1%.
- Default grid: 6×4. Configurable via `diff.yml`.
- v2 falzflyer test (post-Backport 11 fix): the headline-Kasten
  region shows mismatch_pct ≈ 0; before the Backport 11 fix, the
  same region shows mismatch_pct > 5%. This demonstrates the
  tool catches the fix that the page-wide metric missed.

**Drift impact**: zero pixel impact (tool only); but unlocks the
ability to MEASURE the impact of UX-critical small fixes, which
is currently invisible to CI.
