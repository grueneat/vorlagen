---
id: '37'
title: IDML→DSL pre-flight tooling + post-conversion completeness checks
status: open
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

### P2 — Three sources, three distinct roles. Never conflate.

| Source | Role | NEVER used as |
|---|---|---|
| `original.idml` | Authoring truth — what InDesign content exists | Visual reference |
| `baseline.pdf` | **Convergence target** (P1) — what the design SHOULD look like | Element extraction (lossy; positions are subpixel) |
| `reference.sla` (Scribus's own IDML import) | **Element extraction source** + informational converter-quality metric | Convergence target (not pixel-perfect; Scribus's importer has its own gaps) |

### P3 — Use `reference.sla` PRIMARILY for extraction, SECONDARILY for diff.

When an element is in IDML + in `reference.sla` but NOT in `build.py`:
copy the `<PAGEOBJECT>`'s `XPOS/YPOS/WIDTH/HEIGHT/ROT/FCOLOR/PCOLOR/LINESCOLOR`
directly into a DSL primitive. No path math, no transform investigation.
This is the fast path.

When `reference_diff` (preview vs reference-scribus.pdf) fails, our
converter is doing worse than Scribus's own importer — a clear bug to
fix or extract around. When `reference_diff` passes but `visual_diff`
still fails, the residual is shared with Scribus's importer and is
likely cross-engine — document, don't chase.

### P4 — Structural completeness is a hard precondition for drift work.

Phase A audits (`inventory.yml`, `text_audit.yml`, `image_audit.yml`,
and Phase D's `sla_inventory.yml`) must show every IDML PageItem is
either emitted by `build.py` OR explicitly skipped with a documented
reason. Drift convergence work that starts before this is provably
clean burns tokens diagnosing structural gaps as positioning bugs.

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

### Phase D — Multi-source convergence (strategic addition, 2026-05-12)

**Discovered during issue #35 reconciliation work.** Every IDML import has been treated as one source (the IDML), with one reference (the InDesign-exported `baseline.pdf`). That conflates two questions: "does our converter handle this IDML correctly?" and "how do Scribus and InDesign render the same content differently?" The answer to the second is a cross-engine artifact (~6-7% drift floor); the answer to the first is what we actually want to optimise. Without a same-engine reference, executors can't tell the two apart — issue #35 burned ~500K tokens because of this ambiguity.

**Solution:** treat the Scribus-imported SLA as an **additional reference**, NOT a replacement for any existing source. `baseline.pdf` remains the only convergence success criterion. The Scribus-SLA's most valuable role is per-element **extraction** for items our converter drops (the wind turbine `u2b0` is reportedly correctly placed there); its diff-target role is informational only.

| Source | Role | Used for |
|---|---|---|
| `original.idml` | Authoring truth | Structural audit (Phase A1) — element completeness |
| `baseline.pdf` | **Cross-engine ground truth — THE convergence target** | `preview.pdf` vs `baseline.pdf` — drift convergence (this is the only success criterion) |
| `reference.sla` (NEW) | **Extraction source** for dropped elements; **secondary diff target** for converter-quality metric | (a) Copy correct geometry/style of dropped elements into `build.py` or `inject.yml`; (b) `preview.pdf` vs `reference-scribus.pdf` as an informational quality metric |

The `reference.sla` is produced by a **one-time human GUI run** in Scribus (`File → Import → Get IDML File → Save As .sla`). Scribus headless cannot do this (verified 2026-05-12: `openDoc(idml)` via Scripter API hangs >14 min in `-g -ns` mode; IDML import plugin is GUI-only). The cost is ~5-10 min of human time per template at import; it eliminates a class of executor confusion that costs hours of agent runtime downstream.

**Critical framing — what the Scribus-SLA is and isn't:**
- **It is NOT pixel-perfect.** Scribus's own IDML importer has gaps too (it inherits the same `<Image>` LocalScale/LocalOffset issues that bit us on the social-media-icons strip). Do not use it as a convergence target.
- **It is NOT the design ground truth.** `baseline.pdf` (InDesign's own export) is the only source of "what the design should look like." Drift convergence is measured against `baseline.pdf`, period.
- **It IS a same-engine working import.** When Scribus's import correctly places an element (e.g. windmill `u2b0`), the SLA's PAGEOBJECT for that element gives us authoritative geometry/colors/transforms we can extract directly into our DSL — much faster than reverse-engineering the IDML's path/transform math from scratch.
- **It IS a useful informational diff target.** When `reference_diff` (preview vs reference-scribus) fails, our converter is doing worse than Scribus's own importer — that's a clear bug. When it passes but `visual_diff` (preview vs baseline) still fails, the residual is shared between us and Scribus's importer — likely cross-engine artifact, not actionable in our converter.

#### D1. `meta.yml` schema — `reference_sla:` field

```yaml
build:
  ...
reference_sla: ../../originals/<idml-name>/<file>.sla
```

Analogue to the existing `original_sla:` field used by V1 templates for round-trip validation. Documented in `shared/brand/SPEC-WRITING-GUIDE.md`.

#### D2. Import workflow — `bin/idml-import` adds human GUI step

`bin/idml-import` (the single entry point from Phase C1) checks for `originals/<idml-name>/<file>.sla` next to the IDML. If absent, it prints clear human instructions:

```
[idml-import] Scribus IDML reference not found at <path>
To produce it (one-time, ~5 min):
  1. Open Scribus 1.6 in GUI mode (not headless)
  2. File → Import → Get IDML File → select the IDML
  3. Wait for import to complete (large IDMLs take 2-5 min)
  4. File → Save As → <path>
  5. Re-run bin/idml-import
[idml-import] Continuing without reference; converter quality cannot be isolated from engine artifacts.
```

The reference is optional but recommended. Without it, the convergence loop has only the IDML + baseline.pdf signals and the cross-engine ambiguity returns.

#### D3. Render pipeline — second visual_diff lane

`tools/render_pipeline.py::_run_visual_diff` extended: when `reference_sla:` is set in meta.yml, render that SLA to PDF (using existing `tools/render.py` machinery) and run a second `visual_diff` with output `reference_diff.json` alongside `visual_diff.json`. New audit summary line:

```
[<slug>] reference_diff (same-engine): p1=0.84% p2=0.31% PASS  ← converter quality
[<slug>] visual_diff   (cross-engine): p1=7.31% p2=6.31% FAIL  ← engine floor
```

When `reference_diff` passes but `visual_diff` fails, the residual drift is the true engine floor — convergence work should stop. When `reference_diff` fails, our converter has work to do regardless of cross-engine artifacts.

#### D3a. Element extraction from Scribus-SLA — the primary value lane

When the 3-way audit (D4) flags an element as "in IDML, in Scribus-SLA, NOT in build.py", the fix path is:

1. Read the Scribus-SLA's `<PAGEOBJECT ANNAME="uXXX" ...>` for the missing element. It has `XPOS`/`YPOS`/`WIDTH`/`HEIGHT`/`ROT`/`FCOLOR`/`PCOLOR`/`LINESCOLOR` already worked out by Scribus's importer.
2. Translate that PAGEOBJECT into the corresponding DSL primitive call (`Polygon` / `ImageFrame` / `TextFrame`) — straight 1:1 mapping from Scribus's coordinate system to DSL mm.
3. Add to `inject.yml` as an explicit overlay keyed by anname, OR fix the converter handler if a generic pattern emerges.

This is the **fast path** for filling converter gaps — no path/transform math, no investigation of guards. The wind turbine `u2b0` is the canonical first case: Scribus reportedly placed it correctly, so its PAGEOBJECT gives us the right `Polygon(x_mm, y_mm, w_mm, h_mm, fill, line_color, line_width_pt, points=[...])` directly.

#### D4. `tools/sla_inventory.py` — Scribus-SLA element inventory

Parse Scribus's SLA XML (`SCRIBUSUTF8NEW` root → `DOCUMENT` → `PAGEOBJECT` elements). Each `PAGEOBJECT` has `ANNAME=`, `PTYPE=` (4=text, 2=image, 7=polygon, etc.), `XPOS/YPOS/WIDTH/HEIGHT`, `ROT`, `FCOLOR/PCOLOR`. Emit `sla_inventory.yml`:

```yaml
template: kandidat-falzflyer-din-lang-gruenes-cover-v2
reference_sla: ../../originals/.../<file>.sla
pageobjects_total: 101
pageobjects_by_anname:
  u184: {ptype: 12, bbox_mm: [...], fcolor: None, pcolor: None}
  u185: {ptype: 7, bbox_mm: [...], fcolor: "C=85 M=35 Y=95 K=10", pcolor: None}
  ...
```

Then extends the Phase A audit to a 3-way Venn report:

| In IDML | In Scribus-SLA | In build.py | Action |
|---|---|---|---|
| ✓ | ✓ | ✗ | **Converter bug** — Scribus did it, we didn't. PRIORITISE. |
| ✓ | ✗ | ✗ | Scribus also dropped — likely IDML feature both skip. Out of scope. |
| ✓ | ✓ | ✓ | Match — compare bbox; if drift, Scribus geometry is the reference. |
| ✓ | ✓ | ✓ (geom differs) | Geometry drift — diagnose. |
| ✗ | ✗ | ✓ | We emit something not in source — suspicious. |

The "converter bug" row is the highest-leverage executor input: each entry is "Scribus's IDML importer made this work — match it." Often the fix is direct extraction from Scribus's SLA geometry into our DSL.

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
       reason: "Phase 3 — Group transform u3a1 ascender correction (not Group cascade fix, verified via reference.sla)"
       overrides:
         x_mm_delta: 5.05
   ```
3. Apply overlay to fresh re-emit → reconciled `build.py`.
4. Commit reconciled build.py + the inject.yml separately.

After this, every converter change can be re-run via `bin/idml-import` and the result is a fresh re-emit with documented overlays — no silent drift, no lost hand-patches.

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

### Phase D — Multi-source convergence
- [ ] `meta.yml` schema accepts `reference_sla:` field; documented in
      `shared/brand/SPEC-WRITING-GUIDE.md`
- [ ] `bin/idml-import` checks for `reference.sla` next to the IDML and
      prints clear GUI-step instructions if absent; continues without it
      with a warning about lost engine-isolation
- [ ] `tools/render_pipeline.py` renders `reference_sla` (when present)
      to PDF and runs a second `visual_diff` lane (`preview.pdf` vs
      `reference-scribus.pdf`), emitting `reference_diff.json`
- [ ] Audit summary surfaces both lanes: `reference_diff (same-engine)`
      and `visual_diff (cross-engine)` with PASS/FAIL per lane
- [ ] `tools/sla_inventory.py` parses Scribus SLA PAGEOBJECTs and
      produces `sla_inventory.yml` with anname-keyed bbox/style data
- [ ] Phase A audit extended to a 3-way Venn (IDML / Scribus-SLA /
      build.py) with the "converter bug" row marked as highest priority
- [ ] `tools/reconcile_build_py.py` reads `templates/<slug>/inject.yml`,
      applies overlays to fresh converter emit, produces reconciled
      build.py with provenance comments
- [ ] V2 falzflyer template carries `reference_sla:` pointing at the
      Scribus-imported SLA already in `originals/26-03-Leporello.../`
- [ ] At least one inject.yml entry exists for v2 falzflyer documenting
      any genuine Scribus rendering quirks (verified via isolation
      experiment, NOT rationalized) — none from the Phase 4 Black-weight
      "workaround" since that turned out to be a CSR-FontStyle converter
      bug, not a real quirk

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
