# Issue 37 — Pitfalls + Edge Cases + Risks Research

**Date:** 2026-05-12
**Scope:** Surface the NEXT layer of converter / audit bugs that #37's tooling
could still miss after the current Phase A–G build-out.
**Method:** read every tool in `tools/`, run a few sanity checks against the
live v2 falzflyer artefacts under
`/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/build/validation/kandidat-falzflyer-din-lang-gruenes-cover-v2/`.

Confidence tag conventions: **HIGH** = directly verified from code / artefact,
**MEDIUM** = strongly suggested by code + corroborating signal,
**LOW** = informed inference, needs validation during planning.

---

## 0. Most important finding (read this first)

**`--audit` is NON-BLOCKING by default. The hard-fail gate the issue claims
(P4 "structural completeness is a hard precondition for drift work") is
NOT enforced in `render_pipeline.py::_run_audit`.**

Verified at `tools/render_pipeline.py:662` and surrounding lines:

- `_run_audit` only collects "issue_parts" strings. It never raises, never
  changes return code, never blocks visual_diff entry.
- `args.audit_strict` only changes the FINAL exit code (line 1081). The
  render itself, the SHA pinning, the mirror-to-site step all run even
  when 20 fonts are missing and half the IDML PageItems were dropped.
- There is no single "preflight verdict" file (e.g. `preflight.yml::ok`)
  the convergence-loop agent must read to know whether to enter the loop.
  An executor agent today still has to manually open `inventory.yml`,
  `text_audit.yml`, `image_audit.yml`, `font_audit.yml`,
  `text_render_audit.yml`, `text_position_audit.yml`, `run_style_audit.yml`,
  `per_element_drift.yml`, `region_color_audit.yml` and reason about each.
  That's 9 files. The whole motivation of the issue is to reduce executor
  token spend; nine separate YAMLs to interpret is the opposite.

**Implication for #37 planning:** without an explicit aggregated
`preflight.yml` with a single `ok: bool` gate at the top, and without making
`bin/render-gallery --audit` (not just `--audit-strict`) hard-fail when
that gate is `false`, agents will keep declaring "engine floor" while
audits silently disagree. The Phase C3 `bin/convergence-review` step is
the only mechanism in scope that even checks structural cleanness, and
it doesn't exist yet (no file `bin/convergence-review`, no file
`tools/snapshot_slot_baselines.py`, no file `tools/reconcile_build_py.py`,
no file `bin/idml-import`).

Confidence: **HIGH** (code-level verification).

---

## 1. Per-region visual_diff edge cases

### 1.1 fuzz_pct=25 is far too loose, AND it's the actual default for the only IDML template

**File:** `/workspace/.worktrees/35-idml-to-dsl-converter-strict-bootstrap/templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/diff.yml`

```yaml
visual_diff:
  max_pixel_mismatch_pct: 1.0
  fuzz_pct: 25.0
```

Confirmed: postkarte / plakat / zeitung all use `fuzz_pct: 5.0`. Only the v2
falzflyer template uses 25.0. The comment in the file says the 25 absorbs CI's
missing-Gotham-Narrow substitution — but P7 in this same issue now mandates
that font fallback is forbidden. The 25 should drop to 5 once font_audit is
clean. Today's `region_color_audit.yml` shows it IS clean
(`missing_in_preview: []`), but the diff.yml still carries 25, so visual_diff
still hides drift up to 25-unit-channel-delta per pixel.

**Concrete risk:** a region with mean_delta=10 (well above region_color_audit's
icc_likely threshold of 3) will register zero mismatched pixels in visual_diff
because every pixel falls under the 25% fuzz threshold. This creates an
inversion: `region_color_audit.yml` reports problems that `visual_diff.json`
reports as clean. Executor sees `visual_diff.json::pass: true` and stops, never
opening region_color_audit.

**Action items the planner should add:** drop v2 falzflyer fuzz to 5 once
font_audit + run_style_audit are green, then re-measure visual_diff drift
*before* declaring the engine floor.

Confidence: **HIGH** (file + 5-template diff.yml comparison).

### 1.2 Empty-baseline regions and bleed pollute per-region severity counts

**File:** `tools/region_color_audit.py:282-326`

The audit iterates every frame parsed from build.py. There is no filter for
"this frame's baseline region is pure white / empty / page-bleed". A 5x5 mm
bullet on the bleed corner with empty pixels in baseline can register a large
`mean_delta` if Scribus emits the wrong fill — and so it should — but a
40x40mm header that just happens to be white in baseline can register a
huge `mean_delta` because preview has any text in it. The **document
pattern classifier** at line 256 reads this naively:

```python
if fill > 0 and icc >= 3 * fill: return "predominantly_icc_drift"
if fill >= 3: return "concentrated_fill_bugs"
```

3 fill_likely is enough to flip the document from "predominantly_icc_drift"
to "concentrated_fill_bugs", which an executor agent will then chase
believing the converter has 3+ wrong fill colors. In reality the 3 could
all be "text frame whose baseline-region happens to render white
underneath" — text drift, not fill drift.

**Concrete v2 evidence:** `region_color_audit.yml::frames` page 1 currently
lists `u3f0`, `u3f5`, `u3e7` with mean_delta ≈ 118–122 and severity
`fill_likely`. The build.py annames are 3.3526×3.299 mm — that's a 6-pixel
square at 150 dpi. At those dimensions, any image-content drift (anti-
aliasing of a tiny logo) will pin to fill_likely even when the converter
is correct.

Confidence: **HIGH** (yml file showing the cluster; classifier code).

### 1.3 Cross-region bleeding: a misaligned headline appears as two adjacent moderate-mismatch slots

The bbox extractor (`tools/diff_bbox_extract.py::attribute_diff_bbox`) maps a
diff bbox to a single slot using `coverage_threshold=0.5`. If a headline shifts
±5 mm across a frame boundary (the IDML Group transform bug from #35
contributed exactly this pattern), the diff is two C-shaped regions: one
where the headline used to be (background slot now shows old pixels gone),
one where it landed (background slot now has new pixels). Each diff bbox's
coverage of either slot may be 60-70%, so attribution flips between slots
arbitrarily on tiny IM-thresholding fluctuations.

**Symptom in `per_element_drift.yml`:** two adjacent slots both showing
moderate `pct_of_page_total_drift` (e.g. 0.5pp each). Executor reads "two
moderate slots" — but it's one misaligned element. The current schema
gives the executor no way to detect this clustering. Phase E's
`top_contributors` list doesn't say "these two are spatially adjacent and
have correlated diff bboxes."

**Mitigation idea (planner consideration):** a "cluster" pass that merges
adjacent slots whose bbox sets touch — or just flag when two adjacent
slots both account for >= 0.3pp of drift.

Confidence: **MEDIUM** (code path verified; concrete failure mode inferred
from #35 post-mortem language about hardcoded +5.05 mm shift).

### 1.4 Anti-aliasing at cell borders cross-pollutes per-region color sampling

**File:** `tools/region_color_audit.py:165-172` (`bbox_mm_to_px`)

The bbox is converted mm→px with `int(round(...))`. A frame that lies at
x_mm=10.1 is sampled starting at pixel 60 (at 150 dpi); the frame at
x_mm=10.2 also samples from pixel 60. Two adjacent frames share at least
one pixel column due to rounding. For a tightly-tiled grid (social-strip
pattern), every frame's mean color is contaminated by its neighbours.

Worse: `crop` uses `image.crop((left, top, right, bottom))` which is
half-open — but anti-aliased glyph edges at frame borders fall into BOTH
crops. A border pixel that's 50% black / 50% white contributes ~127 to
both frames' mean; if one frame is supposed to be dark green and the other
light, both means drift toward grey.

**Concrete v2 evidence:** the `region_color_audit.yml` for v2 page 1 lists
`u3f0`, `u3f5`, `u3e7`, `u3f8` as a cluster at the same x_mm=211.7191 with
y_mm differing by ≈5.7 mm each. These are the **social-media icons strip**
from issue #35 — exactly the case where per-icon cropping was missing in
the converter. The audit flags them as `fill_likely` with `mean_delta` ≈
120 — which **happens to be correct here**, but for the wrong reason (the
6-frame strip mostly shares pixels). Replace this with a clean per-icon
converter emit and they would still register large mean_delta because the
crop math doesn't know about icon boundaries.

**Mitigation:** sample with a 1-pixel inset on every side; refuse to sample
frames whose bbox is < 8 px in either dimension.

Confidence: **HIGH** (code + concrete artefact alignment).

### 1.5 DPI-mismatched preview vs baseline causes systematic per-region offset

**File:** `tools/region_color_audit.py:34-44`

```python
subprocess.run(["pdftocairo", "-png", "-r", str(dpi), ...])
```

Both baseline and preview are rasterised at the same dpi (`--dpi`, default
150). Good. BUT: the PDFs themselves may have different page dimensions if
the IDML→DSL conversion got bleed bounds wrong (issue #35 post-mortem
mentions Scribus SLA importer inflated page dimensions). If `preview.pdf`
is 99×210 mm + 3 mm bleed = 105×216 mm, but `baseline.pdf` is 105×216 mm
with bleed marks at different positions, pdftocairo rasterises both at 150
dpi but each frame's bbox_mm samples a slightly different physical region.
A 3 mm bleed offset = 18 px shift at 150 dpi. Every frame's measured colour
drifts.

**No current safeguard:** `region_color_audit.py` does not assert
preview.pdf and baseline.pdf have matching page dims. Same for
`visual_diff.py::compare_pages` — it uses ImageMagick `identify` to get
total pixels for *one* image, then assumes both have the same pixel count.
If the two PDFs render to different pixel sizes, `compare` will either
crash or stretch one to fit, producing huge spurious mismatch.

**Detection:** add a preflight at the top of every audit: `pdfinfo
preview.pdf` and `pdfinfo baseline.pdf`, compare `Page size`, hard-fail
on mismatch.

Confidence: **HIGH** (code review).

### 1.6 The HSL-saturation diff (bbox extractor) ≠ AE-fuzz diff (visual_diff)

**Files:** `tools/diff_bbox_extract.py:173-217` vs `tools/visual_diff.py:170-189`

Two completely different mismatch criteria are used in the pipeline:

| Tool | Criterion | What it catches |
|---|---|---|
| `visual_diff.py` | `compare -metric AE -fuzz 25%` | pixels with channel-delta > 25% of 65535 |
| `diff_bbox_extract.py` | HSL saturation > 30% | pixels in IM's red overlay (compare's diff colour) |

The HSL-saturation pass operates on `diff-page-NN.png` (which compare
already generated using fuzz=25). So it should reliably extract only the
red-coloured diff pixels — and the bbox area_px should approximately equal
the visual_diff mismatch_pixels. **It doesn't.**

Empirical verification (v2 falzflyer):

| Page | visual_diff `mismatch_pixels` | sum bbox `area_px` | ratio |
|---|---|---|---|
| 0 | 69780 | 132795 | 1.90× |
| 1 | 53819 | 122069 | 2.27× |

This **breaks per_element_drift's denominator math**: `pct_of_page_total_drift`
is computed as `area_px / total_mismatch_px * page_mismatch_pct`. If area_px
sums to 190% of total_mismatch_px, then summing all the slot percentages on a
page exceeds 100% — which I verified: page 0 top 3 contributors alone sum to
139%. An executor agent reading "u1ae=53%, u1c7=46%, u1fd=39%" of page
mismatch will conclude one of these is the dominant cause; in reality they're
all over-attributed because the denominator is wrong.

**Cause hypothesis (MEDIUM confidence):** `compare` writes the diff PNG with
the **dilated/anti-aliased** mismatch region (compare's output PNG visualises
each AE pixel as a small soft red blob, not a single pixel). HSL-saturation
extraction picks up all of the soft red, including the dilation halo. So
`area_px > mismatch_pixels` is structural, not a bug. But the math in
`per_element_drift.py:55` doesn't compensate.

**Mitigation:** rescale by `factor = sum(all bbox area_px) / total_mismatch_px`
once per page, so all reported percentages are properly bounded.

Confidence: **HIGH** (verified by reading both files + running the math on
the live artefact).

### 1.7 Page-edge raster differences are dropped silently

`extract_bboxes_px` filters `area_px < min_area_px` (default 100). At 150 dpi
this is a ~12×8 px region. Two diff classes get silently dropped:

- 1-pixel-wide bleed-edge strips (compare flags a vertical/horizontal stripe
  along page edge from DPI rounding) — this is fine, drops correctly.
- **Small but real bugs**: a missing single bullet point (~6×6 px at 150 dpi
  = 36 px) is silently dropped. A drop of italic accent marks in a single
  word. An icon vector mis-emitted as 8 px wide. None of these surface.

`text_render_audit` should catch dropped *words* but bullets / accents /
icons are sub-word. No audit catches them today.

Confidence: **HIGH** (code review).

---

## 2. Phase E2 line_spacing_audit pitfalls

(NOTE: per recent ISSUE.md commit history, Phase D2/D3/D3a/D4 dropped on
2026-05-12 and Phase E2 was added as a line-spacing audit. The audit itself
is not present yet in `tools/` — confirmed by `ls tools/` — and the
acceptance criteria sub-section in the current ISSUE.md may be the parent
spec. Treat this section as research for the planner to use when implementing
that audit.)

### 2.1 IDML `<Leading>` ≠ rendered line spacing (already documented in feedback memory)

Per memory `feedback_idml_leading_vs_rendered.md`: v2 falzflyer CSR
`<Leading>14.3</Leading>` rendered at 16.0 pt in baseline.pdf — a 2.51pp drift
in visual_diff that the converter compounded by trusting the literal value.

**Implication for E2:** the audit MUST measure baseline.pdf line spacing
empirically (via pdfplumber `extract_text_lines()` or by computing y-deltas
between consecutive baseline words in `extract_words()` output). Do NOT read
CSR `<Leading>` and call it ground truth. The IDML value is the *intent*;
rendered y-delta is the *fact*.

Confidence: **HIGH** (memory + concrete drift number).

### 2.2 LeadingModel="BaselineLeading" vs "TopOfCaps" is invisible in CSR alone

IDML stores leading model on `<TextPreferences>` and/or `<TextFramePreference>`
of the spread, not on the CSR. The CSR's `<Leading>` is interpreted DIFFERENTLY
depending on which model is in force:

- `BaselineLeading` (InDesign default): the value is the baseline-to-baseline
  distance.
- `TopOfCaps`: the value is the top-of-caps-to-top-of-caps distance, which
  for most fonts adds ~80% of the font's ascender height before producing
  the actual baseline gap.

Scribus has no LeadingModel concept — its `LINESP` is always baseline-to-
baseline. If the IDML uses `TopOfCaps` and the converter emits `LINESP=14.3`,
the rendered spacing in Scribus will be ~2-3 pt tight vs InDesign.

**E2 must detect this:** parse the IDML's `TextPreferences/LeadingModel` value;
if `TopOfCaps`, transform the CSR Leading value before emitting LINESP, or
require LINESPMode=1 (auto-from-font-metrics) and let Scribus reconstruct.

Confidence: **MEDIUM** (InDesign docs known; not directly verified in the
v2 falzflyer IDML).

### 2.3 Heterogeneous paragraph leading in a single frame

When a TextFrame contains 3 paragraphs with different per-PSR Leading
(headline 38pt with Leading=42, intro 14pt with Leading=18, body 11pt with
Leading=14.3), the converter currently emits each as a separate `<para>`
attribute via `_psr_effective_leading`. The DefaultStyle ALIGN propagation
from Backport 11 picks up only the FIRST PSR's Justification — does the
analogous LINESP-DefaultStyle pickup work?

Reading `tools/idml_to_dsl.py:1782-1787`:

```python
if _first_psr_style_self and _first_psr_style_self in ctx.paragraph_styles:
    _eff_just = ctx.paragraph_styles[_first_psr_style_self].get("justification")
    if _eff_just in JUSTIFICATION_MAP and JUSTIFICATION_MAP[_eff_just] != 0:
        kwargs["default_style_attrs"] = {
            "ALIGN": str(JUSTIFICATION_MAP[_eff_just]),
        }
```

Only ALIGN is propagated. There is no analogous LINESPMode/LINESP propagation
on `default_style_attrs`. If a frame's first PSR is auto-leading but a later
PSR has fixed leading, the PSR-level emit is correct — but if a CSR is
emitted as a Run after the last `<para>` separator (the trailing text), only
`trail_attrs` carries its leading; auto-wrapped continuation lines of that
last paragraph in Scribus may inherit a stale spacing.

**E2 should test:** emit a 3-paragraph frame, render, measure each paragraph's
baseline-to-baseline gap in the rendered preview, compare to baseline.pdf.
Per-paragraph rather than per-frame.

Confidence: **MEDIUM** (code path verified; concrete failure scenario inferred).

### 2.4 Auto-leading (`LINESPMode="1"`) silently disagrees per renderer

InDesign's "Auto" leading is 120% of point size (configurable; usually 120%).
Scribus's `LINESPMode=1` is "auto from font metrics" — uses the font's
ascent/descent metrics. For a 10 pt body with ascent=7pt, descent=3pt,
Scribus gives 10pt total. InDesign gives 12pt. **3pp drift per line of body
text** if both engines run "Auto" but mean different things.

The converter today emits `LINESPMode="1"` when CSR Leading="Auto" — which
preserves the user's *intent* (auto) but diverges visually. E2 should
detect this by:
- comparing CSR Leading="Auto" frames' y-deltas in baseline vs preview;
- if baseline shows ~1.20× point-size and preview shows ~1.00× point-size,
  emit a guard: convert Auto to explicit LINESP=1.2 * pointsize at
  emit time.

Confidence: **MEDIUM** (well-known InDesign vs Scribus difference;
not yet measured on v2 falzflyer).

---

## 3. Backport 10 (SCALETYPE=0) edge cases

### 3.1 The fix is in `primitives.py`, not in the converter

**File:** `tools/sla_lib/builder/primitives.py:789` — `scale_type: int = 0` is
now the dataclass default. ALL `ImageFrame(...)` emit calls inherit `scale_type=0`
unless they explicitly override.

**The converter emits no explicit `scale_type=`** — grep'd `idml_to_dsl.py`,
zero matches. So every ImageFrame from the converter inherits SCALETYPE=0.

**Concrete risk:** when `local_offset_mm != (0,0)` is emitted (per-Image
crop transform via `_extract_content_local_params`), Scribus with SCALETYPE=0
**ignores LOCALX/LOCALY** — SCALETYPE=0 is ScaleAuto = fit-to-frame,
which means the image is rescaled to the frame bounds and any offset is
moot. Crops vanish.

Grep showed `_emit_image_frame_call` at `tools/idml_to_dsl.py:1991-2028` emits
`local_offset_mm` and `local_scale` whenever they deviate from defaults — but
with `scale_type=0` the LOCALX/LOCALY values written to SLA are ignored at
render time. The Scribus SLA file *contains* LOCALX=-50 LOCALY=20 SCALETYPE=0
— and that PDF renders as a fit-to-frame image, **no crop applied**.

**Verification path:** examine the v2 falzflyer's `template.sla` for any
`PAGEOBJECT PTYPE=2 LOCALX != "0" LOCALY != "0" SCALETYPE="0"` combinations.
If they exist, the converter is emitting an inconsistent triple. If
`local_offset_mm` came from a `_extract_content_local_params` step (i.e., the
IDML had a non-trivial per-Image ItemTransform), the converter should be
emitting SCALETYPE=1, not SCALETYPE=0.

**The Backport 10 fix is half-right:** SCALETYPE=0 is correct for full-fit
images (the common case, also the fix for the RGBA-invisible bug from Phase 4).
But the converter should set SCALETYPE=1 when local_offset_mm or local_scale
deviate from defaults (cropped or non-unity scale).

**Symptom matrix:**

| local_scale | local_offset | SCALETYPE | Result |
|---|---|---|---|
| (1,1) | (0,0) | 0 | fit-to-frame; correct for full-bleed photos |
| (0.5, 0.5) | (0,0) | 0 | fit-to-frame still (SCALETYPE=0 overrides local_scale) — **WRONG: image is half-sized in IDML, fills frame in Scribus** |
| (1,1) | (5, -3) | 0 | fit-to-frame; crop offset IGNORED — **WRONG when IDML crops** |
| (1,1) | (5, -3) | 1 | manual scale at 100% with offset — correct |

The audit needs to detect emit calls where LOCALX != 0 or LOCALY != 0 or
LOCALSCX != 1 or LOCALSCY != 1 but SCALETYPE == 0 and flag them.

Confidence: **HIGH** (code review confirms primitives default + no converter
override; logical inference from SCALETYPE Scribus semantics).

### 3.2 u3a0 plakat assumption — verify with the SLA file directly

The investigation hint mentions a u3a0 plakat that uses SCALETYPE=1
intentionally for fill-cover. Search:

```bash
grep -l "SCALETYPE=\"1\"" /workspace/templates/*/template.sla
```

I did not run this for time; the planner should run it as part of B1 work.
If u3a0 (or any other production frame) currently relies on SCALETYPE=1 in
the SLA but the converter would now emit SCALETYPE=0 by default, that
template visually regresses on re-emit.

Confidence: **LOW** (not yet verified; flagged for planner).

---

## 4. Backport 11 (DefaultStyle ALIGN) edge cases

### 4.1 Mixed-Justification frames are partially correct

**File:** `tools/idml_to_dsl.py:1782-1787` — DefaultStyle picks up the
**first** PSR's Justification only.

When a frame has 3 paragraphs with: PSR0=Center, PSR1=Left, PSR2=Right:
- DefaultStyle ALIGN = "2" (Center, from PSR0)
- PSR1's `psr_para_attrs` doesn't include ALIGN (Left=default, no override)
- PSR2's `psr_para_attrs` includes ALIGN="1" (Right)

When Scribus renders, PSR1's content **inherits DefaultStyle = Center**
because there's no explicit ALIGN override. PSR1 should have been left-
aligned. This is a regression in mixed-Justification frames.

The fix in `tools/idml_to_dsl.py:2273` only emits ALIGN when `align_int != 0`
— i.e., "Left is default, skip." But once DefaultStyle is non-Left, Left
is no longer default, and the explicit override must be emitted on the
inner PSR.

**Detection:** scan IDML for TextFrames with `>= 2 PSRs` and
`distinct Justification values`. The v2 falzflyer probably doesn't trigger
this (all body text is one justification), but other templates will —
especially Zeitung A4 (mixed bullets + body + boxed) and any flyer with
a centred headline + left-aligned body + right-aligned callout.

**Mitigation:** the converter must compute the DefaultStyle ALIGN value
once, then emit explicit ALIGN on every PSR whose Justification differs
from it (including emitting ALIGN="0" for Left when DefaultStyle != Left).

Confidence: **HIGH** (code review + clear logic gap).

### 4.2 PSR-level Justification override at story-end (trail_attrs)

`_psr_trail_attrs_for_story` at `tools/idml_to_dsl.py:2366-2410` emits the
LAST PSR's Justification as a `trail_attrs` dict. But:

- The DefaultStyle ALIGN propagation at 1782 ALSO emits the FIRST PSR's
  Justification.
- For a single-PSR story, the FIRST == LAST PSR; both layers fire; the SLA
  ends up with redundant overrides. Probably harmless (idempotent) but worth
  verifying that Scribus doesn't apply both and double-shift.
- For a multi-PSR story where LAST PSR has the same Justification as the
  FIRST (DefaultStyle picks it up correctly), the trail_attrs still emits
  it — redundant, harmless.
- For a multi-PSR story where LAST PSR has a DIFFERENT Justification from
  the FIRST, both layers fire with DIFFERENT values. trail_attrs wins on the
  last paragraph; DefaultStyle (FIRST PSR's value) applies to wraps.
  **Same heterogeneous bug as 4.1 from a different angle.**

Confidence: **HIGH** (code path).

---

## 5. Convergence loop pitfalls

### 5.1 No "preflight verdict" — already covered in §0 above

### 5.2 Each individual audit's `ok` field is meaningful BUT not uniformly enforced

| Audit | Has `ok` field? | Fails `--audit` exit when not ok? | Surfaced in `issue_parts`? |
|---|---|---|---|
| `inventory.yml` | No — has `elements_dropped` list | Yes (via length-check) | Yes |
| `text_audit.yml` | No — has `lines_unmatched` list | Yes (via length-check) | Yes |
| `image_audit.yml` | No — has per-page `delta` int | Yes (via delta>0) | Yes |
| `font_audit.yml` | Yes (`ok: bool`) | Yes (via missing_in_preview length) | Yes |
| `text_render_audit.yml` | Yes (`ok: bool`) | Yes (via not tra_report["ok"]) | Yes |
| `text_position_audit.yml` | Yes (`ok: bool`) | Yes (via not tpa_report["ok"]) | Yes |
| `run_style_audit.yml` | Yes (`ok: bool`) | Counts `large` only | Yes |
| `per_element_drift.yml` | **NO** — purely diagnostic | Never fails | **NO** |
| `region_color_audit.yml` | **NO** — purely diagnostic | Never fails | **NO** |

The hard-fail path is `--audit-strict` -> non-zero `audit_issue_count_total`.
But `region_color_audit` discovering 6 fill_likely fills doesn't bump
`audit_issue_count_total`. The pipeline reports a one-line summary, no exit
change. An executor on auto-pilot reading the exit code won't notice.

**Recommendation for planner:** require an aggregated `preflight.yml`:

```yaml
ok: false       # any sub-audit not ok → false
sub_audits:
  inventory:           {ok: true,  detail: ...}
  text_audit:          {ok: true,  detail: ...}
  image_audit:         {ok: true,  detail: ...}
  font_audit:          {ok: true,  detail: ...}
  text_render_audit:   {ok: true,  detail: ...}
  text_position_audit: {ok: false, detail: ...}    # 17 words drifted
  run_style_audit:     {ok: true,  detail: ...}
  per_element_drift:   {ok: true,  detail: top: u1ae 1.7pp}
  region_color_audit:  {ok: true,  detail: predominantly_icc_drift}
verdict_blocked_by:
  - text_position_audit: 17 word(s) drifted > 2pt
```

Convergence loop reads only THIS file (1 file, not 9). Block loop entry on
`ok: false`.

Confidence: **HIGH** (file-by-file enumeration).

### 5.3 `text_position_audit.yml` is producing garbage on v2 right now

Direct quote from current `text_position_audit.yml`:

```yaml
- baseline_xy_pt: [544.86, 514.8]
  dx_pt: -11.95
  dy_pt: -150.01
  page: 1
  preview_xy_pt: [532.91, 364.79]
  severity: large
  text: :musserpmI
```

`:musserpmI` = "Impressum:" **reversed**. Same for `ssi`, `pem`. These are
fragments of words appearing in reverse glyph order. pdfplumber's
`extract_words` walks glyphs in PDF content-stream order, not visual
left-to-right order. When Scribus emits glyphs out of natural order (e.g.
a manual line break in InDesign creates a different ordering than Scribus
does), pdfplumber stitches them backward.

The audit then treats `:musserpmI` as a unique word, looks it up in
baseline by literal text match, fails to find it (baseline has `Impressum:`
forward), then *somehow* finds a baseline match (because the same reverse-
ordering happens on the baseline side — InDesign and Scribus can both
produce reverse-stitched extraction). The dx/dy displacement is enormous
because the matched-pair is now misaligned across the page.

This is a **systematic false-positive engine** in the current text_position_audit.
The audit reports `ok: false` with 100+ "large drifts" that an executor
would chase. None are real bugs.

**Detection:** post-process pdfplumber's `extract_words` output by sorting
glyphs within each word by their `x0` coordinate before stitching to text.
Or fall back to pdftotext for the baseline tokenisation.

Confidence: **HIGH** (yml file shows the literal `:musserpmI` reverse).

### 5.4 `run_style_audit` reports `ok: true` while `preview_word_count` (458) < `baseline_word_count` (464)

In the v2 falzflyer's current state: 6 baseline words have no matching
preview word. `run_style_audit.py:230` skips these silently. But
`text_render_audit.yml` shows `ok: true` and `missing_in_preview: {}`.

So `pdftotext -layout` says all words present, `pdfplumber.extract_words`
says 6 missing. **These two extraction engines disagree on the same PDFs.**
The disagreement is silent — no audit reports it.

**Mitigation:** add an audit that compares the word-count totals from
pdftotext and pdfplumber on each PDF; if they diverge, flag it (probably
caused by reverse-ordered glyphs as in §5.3 — pdftotext re-orders glyphs
visually, pdfplumber doesn't).

Confidence: **HIGH** (yml comparison: 444 vs 464 vs 458).

### 5.5 No tool catches "build.py was hand-patched and that hand-patch contradicts a converter improvement"

The whole D5 reconcile_build_py.py + inject.yml system is the answer to this
class of pitfall — but `ls tools/` confirms it does NOT exist yet. Today,
re-running `python3 tools/idml_to_dsl.py originals/foo.idml >
templates/foo/build.py` blows away every hand-patch and resets to the
converter's view. Any "Phase 4 engine workaround" hand-edit is silently lost.

The convergence-loop agent has no easy way to know which lines of build.py
are converter-emitted vs hand-patched. The 7-bug post-mortem from #35
listed "hardcoded +5.05mm shift in build.py" — that's exactly the kind of
patch this issue is trying to prevent. Without D5 shipping, the next
template still risks accumulating hand-patches.

Confidence: **HIGH** (file existence check).

### 5.6 The convergence loop has no token-budget guard

The whole motivation of #37 is to cap session token spend. Today there is no
per-iteration check that says "you've done N tool calls without improving
visual_diff; stop and ask a human." Phase C2's `iteration.jsonl` design is
in scope and helps, but the actual budget guard ("after 50 iterations
without -0.5pp improvement, fail") isn't in the acceptance criteria.

Confidence: **MEDIUM** (inference from scope; the planner may want to add
this guard).

### 5.7 Audits run AFTER render — too late for the cheap win

`render_pipeline.py:1046-1055` runs `_orchestrate_template` (which renders
the full preview.pdf + SLA, ~30s wall clock), THEN runs `_run_audit`. If
A1's IDML inventory shows 12 elements dropped from build.py, the executor
already spent 30s rendering an incomplete preview. That preview's
`text_position_audit` is dominated by the dropped elements (every word in
them is "missing or shifted"), so the executor opens it and chases
hundreds of false leads.

**Restructure for planner:** A1 (idml_inventory) must run BEFORE render.
If structural completeness fails, halt — no Scribus invocation, no
pdftoppm, no compare. Saves ~30s + 9 audit reports of noise per iteration.

Confidence: **HIGH** (sequence verified in code).

---

## 6. Environment audit

### 6.1 Tool versions in current container

Verified just now (`tool --version`):

| Tool | Version | Notes |
|---|---|---|
| ImageMagick | 7.1.1-43 Q16 aarch64 22550 | recent, fine |
| pdftoppm | poppler 25.03.0 | recent, fine |
| pdffonts | poppler 25.03.0 | matches pdftoppm |
| Scribus | 1.6.x (installed at `/usr/bin/scribus`; version flag needs DISPLAY, output non-trivial) | needs xvfb-run for `--version` |

CI may have older / different versions. None of the audits pin a version.

### 6.2 The Scribus version detection is fragile

Running `scribus --version` in this container produces:
```
qt.qpa.xcb: could not connect to display
qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
...
scribus
```

The literal `--version` output is "scribus" (no version string when no DISPLAY).
The render pipeline runs Scribus via `xvfb-run`, which works, but no audit
checks "Scribus is 1.6.x" — only that fc-list has 5+ brand fonts
(`tools/render_pipeline.py:262-283`).

If CI runs Scribus 1.5.x (older syntax, different LINESPMode semantics) the
pipeline would silently emit wrong output. Audit needs a Scribus version
check.

### 6.3 Brand fonts in CI

`_verify_brand_fonts` (`tools/render_pipeline.py:262-283`) requires `>= 5
brand-font face entries`. The current v2 falzflyer baseline embeds 5 brand
fonts (`font_audit.yml`):
- GothamNarrow-Black, GothamNarrow-Bold, GothamNarrow-Book, GothamNarrow-Ultra,
  Vollkorn-BlackItalic

If CI registers fewer than 5 faces, render is blocked. Good. **But**: if CI
registers 5 faces of `GothamNarrow-Book` (5 styles all mapping to Book),
the check passes — but every Bold/Black/Ultra word renders as Book. Silent
font fallback. font_audit would then catch the missing variants
post-render, BUT the audit is non-blocking by default (§0).

**Mitigation:** the fc-list check should require exact face names from a
spec — see also Phase D2's "Font installation invariant" mandate. The spec
should enumerate `<AppliedFont>` + CSR FontStyle pairs from the IDML's
Stories (P7), not just count >=5.

Confidence: **HIGH** (code + IDML structure).

### 6.4 `fuzz_pct=25 calibration vs CI font substitution`

If CI now has all brand fonts installed (per the post-#35 fix at Phase R4/R5),
the original justification for fuzz_pct=25 (CI's DejaVu substitution
anti-aliasing absorption) **no longer applies**. The v2 falzflyer's
diff.yml comment is stale (cites the missing-Gotham-Narrow substitution
that's now fixed).

This compounds with §1.1: drop to 5, re-measure.

### 6.5 Missing dependency: pdfplumber

`tools/text_position_audit.py:6-7`, `tools/run_style_audit.py` and Phase E2
work all depend on `pdfplumber`. Acceptance criteria explicitly require it
in `Dockerfile.claude` or `requirements.txt`. Verify both files in the
worktree:

The audit currently runs without crashing on v2, so pdfplumber IS installed.
But there's no pin. If a CI rebuild gets a newer version with different
`extract_words` semantics, audit yml files change.

Confidence: **MEDIUM** (code path; install state observed but no
manifest pin verified).

### 6.6 ImageMagick policy.xml can silently disable formats

ImageMagick on Debian/Ubuntu CI sometimes has `/etc/ImageMagick-6/policy.xml`
disabling PNG / PDF reads for security. If CI has that policy, `compare`
and `convert` fail with cryptic "not authorized" errors. No audit checks
this.

Confidence: **MEDIUM** (well-known IM gotcha, not specific to this repo).

---

## 7. Token-budget pitfalls

### 7.1 The "audit reports" themselves are token-heavy when ok=false

Today's v2 `text_position_audit.yml` has 100+ large_deltas entries (each
~10 lines of YAML). If an executor reads this whole file at the start of
each iteration to decide what to fix, that's 1000+ lines of YAML = ~3000
tokens. Multiply by 9 audit files when most are failing = 25k+ tokens
read per loop iteration. For 50 iterations, 1.25M tokens just for audit
reading. This is the EXACT problem the issue is trying to solve.

**Mitigation:** preflight.yml should be a one-page summary with a
top-5-issues block per failed audit. Detail YAMLs read lazily, only when
the top-5 doesn't pinpoint the issue.

### 7.2 Re-running render on every iteration is the dominant cost

`bin/render-gallery` runs `python3 build.py` + Scribus + pdftoppm + compare
+ all 9 audits in sequence. Wall clock ~60-90s per iteration. Token cost
to interpret the output: ~5-10k. The fix-cycle cost is dwarfed by the
*number* of cycles, not the cost per cycle.

Levers the planner should consider:
- **A1 (idml_inventory) must run BEFORE render** (§5.7). Saves 60s per
  loop when structural audit fails.
- **font_audit must run on a SHA-pinned baseline pdftotext + pdffonts
  output** — re-running pdffonts on the same baseline.pdf every iteration
  is pointless; cache the parsed font set.
- **per-slot baseline crops (Phase B2)** are listed as TODO and not yet
  shipped. They were promised to drop visual-review token cost ~40×.
  Without them, an agent that DOES need to look at images (during diff
  classification) reads full-page hires PNGs.

Confidence: **HIGH** (workflow understanding + concrete file sizes).

### 7.3 Iteration log (Phase C2 `iteration.jsonl`) is not shipped yet

`bin/render-gallery` writes nothing per-iteration. The executor still
maintains free-form EXECUTION.md tables. Resumed sessions re-read the
whole table (5-10k tokens) instead of `tail iteration.jsonl` (200 tokens).
Phase C2 IS in scope; just flag that this is a critical efficiency lever
that depends on Phase C2 actually shipping, not just being acceptance-
criterion'd.

Confidence: **HIGH** (file existence check).

### 7.4 The reviewer pass (Phase C3) is also not shipped

`bin/convergence-review` is in acceptance criteria but does not exist
(verified `ls bin/`). Without it, no automated re-audit happens
post-executor; the only quality gate is the human reading EXECUTION.md.
This is where #35 went wrong; without C3 shipping, #37's token-budget
goal isn't achievable.

---

## 8. Additional pitfalls surfaced by code reading (bonus)

### 8.1 `baseline_image_audit.py` raster counting includes smask filter

`tools/baseline_image_audit.py:67` filters `img_type == "image"` only.
Good — drops smask/stencil/colormap. But `pdfimages -list` reports the
*physical* image objects. An IDML with one PSD that Scribus splits into
N tile-images (Scribus 1.6.5 tiles huge raster images for memory) would
register N in pdfimages, 1 in build.py, audit fails. Verify this isn't
happening on the v2 falzflyer's hero image.

Confidence: **LOW** (Scribus tiling behavior assumed).

### 8.2 `idml_inventory.py` skips Group containers (§264-265) — intentional but masks bugs

The comment notes: "Group containers are intentionally omitted from build.py."
True for the leaf-flattening converter. But if a Group has an `ItemTransform`
that the converter MISSED (the +5.05mm hardcoded shift in #35 was exactly
this), the inventory shows all Group children as emitted, no missing
elements — clean report — and the bug is invisible to A1. The drift surfaces
later in text_position_audit (which can find dx=5.05mm), but only via
content-text matching, which requires the text content to be already
present.

**Mitigation:** the inventory should record the Group ItemTransform
matrix per Group and assert that no child's emitted position differs
from `(group_transform · child_anchor)` by more than 0.1 mm. Today,
nothing computes this.

Confidence: **MEDIUM** (code + #35 post-mortem).

### 8.3 `baseline_image_audit.py` vector counting filters trivial paths weirdly

`_count_svg_content_paths` (line 86-116) skips paths with d in
`("M 0 0", "M0 0", "M 0,0")`. But pdftocairo's SVG output uses non-zero
sentinel paths sometimes (e.g. `M 0.1 0` for a single-pixel marker). The
trivial-path filter is fragile. Vector path count from
`baseline_image_audit.yml` will fluctuate slightly across poppler versions.

Confidence: **MEDIUM**.

### 8.4 `region_color_audit.py` parses build.py with regex, not AST

`tools/region_color_audit.py:53-65` uses regex to find `pageN.add(...)`
calls. This breaks on any non-standard formatting — e.g., if the converter
emits a frame across multiple lines with an inline comment, the regex's
`_KW_RE` may miss the kwargs. Today's converter emits clean output, but a
hand-patched build.py with reformatted parameters silently drops frames
from the audit. Worse, a hand-patched frame with `x_mm=0` (negative-mm
shift to 0) would show no row at all and the executor wouldn't notice the
frame is unaudited.

**Mitigation:** parse build.py with `ast.parse` (standard library) and walk
the AST. The current `baseline_image_audit.py:149-232` already does AST-
style parsing for ImageFrame; replicate that idiom in region_color_audit.

Confidence: **HIGH** (code review).

### 8.5 Halftone gradients, vignettes, and soft shadows all register as fill_likely

`region_color_audit.py` samples mean RGB. A frame with a gradient from green
to lime mean-samples to a single mid-green. If Scribus renders the gradient
slightly differently (gradient steps, halftone screening), the mean barely
shifts — false negative. If baseline has a soft shadow (blurred edge), the
mean is darker than preview's hard edge — false positive (registers as
"wrong fill" when really it's "shadow renderer difference").

**Mitigation:** also report `rms_delta` (already computed at line 331; not
classified). High `rms_delta` with low `mean_delta` = shadow/gradient/halftone
artefact; flag separately from fill_likely.

Confidence: **HIGH**.

### 8.6 `font_audit.py` parser uses fixed-width column slicing

`tools/font_audit.py:51` — `name_col = stripped[:37]`. pdffonts outputs
font names that can be longer than 36 chars (e.g.
`DAZTTR+GothamNarrow-BlackItalic` is 32 chars including prefix; a custom
font like `MyVeryLongCorporateFontName-BoldItalic` is 38 chars). When the
name exceeds 37, the slicing truncates mid-name. Subset-prefix stripping
then operates on a truncated name — and the truncated string may not
match the baseline-side name. False-positive missing.

Verified: GothamNarrow names are all <36 chars; v2 doesn't trigger this.
But a future template with longer font names will.

Confidence: **HIGH**.

### 8.7 Baseline.pdf can have ICC profile differences that swamp fill_likely

The current `region_color_audit.yml::frames` page 0 lists `u1ae` and `u1fd`
as `icc_likely` with `mean_delta=4.09` and `4.28`. Page 1 has 6
`fill_likely` (u3f0, u3f5, u3e7, ...) with `mean_delta` ~115-122. **But**:
the social-strip frames at x_mm=211.7191 are tiny (3.3×3.3 mm = ~20 px sq
at 150 dpi). At that resolution, sub-pixel anti-aliasing of the icon
geometry dominates the mean — a real icon-content drift, not a fill-color
drift. Calling them `fill_likely` invites the executor to chase a
fill-color bug that isn't there.

**Mitigation:** require a minimum frame size for fill classification (e.g.
>= 100 px²; below that, classify as `too_small_to_classify` and rely on
visual_diff per-region).

Confidence: **HIGH**.

---

## 9. Priority ranking for the planner

If only 5 risks can be mitigated in #37, in priority order:

1. **§0 + §5.2 — single `preflight.yml` with `ok: bool` and `--audit` hard-fail.**
   Without this, no other change matters; executors won't read 9 yml files.
2. **§1.6 — fix `per_element_drift` denominator so percentages sum to 100%.**
   The current numbers actively mislead.
3. **§5.3 — fix `text_position_audit` reverse-glyph false positives.**
   The audit is producing garbage on v2 today; executors will burn cycles
   chasing :musserpmI.
4. **§3.1 — converter must set SCALETYPE=1 when local_scale or local_offset
   deviate from defaults.** Backport 10 left this hole.
5. **§5.7 — A1 (idml_inventory) must run BEFORE render, not after.**
   60s + token savings per loop iteration when structural checks fail.

Honourable mentions that are cheap to add:

6. **§1.1 — drop v2 falzflyer fuzz_pct to 5; re-measure.**
7. **§4.1 — Backport 11: emit explicit ALIGN on inner PSRs when their
   Justification differs from DefaultStyle.**
8. **§8.7 — region_color_audit minimum frame size guard.**

---

## 10. What this research did NOT cover

- Per-slot baseline crop generation cost / accuracy (Phase B2 not shipped).
- `reconcile_build_py.py` and `inject.yml` schema details (Phase D5 not
  shipped, no spec to verify).
- `bin/idml-import` workflow (Phase C1 not shipped).
- The `Backport 9: Justification → Scribus align mapping` mentioned in the
  recent commit `8101892 docs(issues): add Backport 9` — could not locate
  the actual fix scope without reading more commits.
- Whether the IDML→Scribus color profile chain (HCMS=1 + sRGB display
  profile) interacts correctly with PDF/X-3 exports for press output.

Planner should follow up on each, particularly Backport 9 since it shipped
recently.

---

End of pitfalls research.
