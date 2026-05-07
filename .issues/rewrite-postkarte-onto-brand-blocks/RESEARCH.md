# RESEARCH — Rewrite Postkarte A6 onto Brand + blocks

**Researched:** 2026-05-07
**Issue:** rewrite-postkarte-onto-brand-blocks (id 6, depends on merged #5)
**Confidence:** HIGH (all numbers measured; no library/network research needed)

## Summary

The converter's issue-#5 changes already do the heavy lifting: re-running `tools/sla_to_dsl.py` against the unchanged `templates/postkarte-a6-kampagne/template.sla` emits a **383-LOC** build.py — 54 LOC below the current 437, **103 LOC above the 280 target**. Brand-emission, pt-geometry stripping, and `clip_edit=True` rect-collapse are all working as advertised; `extra_doc_attrs` is at exactly **23 keys** (criterion ≤23 → met) and `extra_pdf_attrs` is at **12 keys** (criterion ≤11 → 1 over). Visual_diff against the committed baseline.pdf is byte-clean (exit 0). The blocker is **not** rendering — it is **`bin/validate --ci`'s `sla_diff --strict`**: switching to `Brand` injects 3 extra layers and 8 `ci/*` paragraph styles into the rebuilt SLA, producing 11 strict-mode warnings on Postkarte alone (issue #5's own test_sla_to_dsl.py already documents and tolerates this regression). The plan must either (a) loosen `bin/validate`'s `--strict` to allow brand-injected `extra-style`/`extra-layer` warnings, or (b) explicitly suppress them at the build.py layer, before the rewrite can land green. Block substitution is small but real: PageBackground × 2 fits cleanly via `PageBackground.for_page(...)`, ContactBlock and Impressum each have idiom gaps that should keep them as primitives this round.

**Primary recommendation:** Phase the work — (1) regenerate build.py via converter; (2) hand-edit only the 2 PageBackground polygons into block calls; (3) hand-add explicit `layers=[DocumentLayer('Hintergrund', ...)]` to suppress 3 extra-layer warnings; (4) drop the 1 redundant pdf attr; (5) decide and implement the `ci/*` extra-style policy in `bin/validate` / `sla_diff` (separate task, needed before any of the three Brand migrations can satisfy the validate-strict criterion).

## Current Postkarte build.py inventory (437 LOC committed)

Per-section ranges in the **current committed** `templates/postkarte-a6-kampagne/build.py`:

| Lines | Section | Notes |
|------:|---------|-------|
| 1–13  | Imports + sys.path bootstrap | unchanged across templates |
| 15–33 | `Document(...)` constructor | line 28 = `extra_doc_attrs` (113 keys, 2862 chars), line 29 = `extra_pdf_attrs` (34 keys), line 30–32 = `layers=[DocumentLayer(...)]` |
| 35–42 | `doc.add_color(...)` × 8 | Black, Dunkelgrün, Gelb, Green, Hellgrün, Magenta, Registration, White |
| 44–45 | `add_char_style(...)` × 2 | Default Character Style (+ ‘(2)’) |
| 46–54 | `add_para_style(...)` × 9 | Default, Fließtext, Impressum, Default(2), Schrift rosa Kreis, Headline sehr wichtig, Kontaktmöglichkeiten, Vollkorn Headline sehr wichtig, Unterüberschrift |
| 56–66 | `doc.add_master(name='Normal', ...)` | single master |
| 68–87 | `doc.add_page(...)` × 2 | page0 + page1 |
| 89–214 | **page0** items (5) | see frame table below |
| 216–434 | **page1** items (10) | see frame table below |
| 436–437 | `doc.save(...)` + print | unchanged |

### Frame inventory (15 page items, both pages)

`B` = block-substitutable; `P` = stays primitive.

| Line range | Idiom | Maps to | Notes |
|----:|---|---|---|
| 89–103 | `Polygon` full-bleed `Dunkelgrün` rect at layer 0 | **B → `PageBackground.for_page(105, 148, color='Dunkelgrün', line_color='Black', line_width_pt=1)`** | clean fit; needs `for_page` factory because postkarte size ≠ block default (220×310) |
| 105–117 | `ImageFrame` empty placeholder hero (line_width_pt=3.835) | P (primitive) | not a block — Postkarte-specific hero slot |
| 119–135 | `ImageFrame` with inline_image_data (line 129 = 87 537 chars base64) — Logo | P | logo image, no block fits |
| 137–158 | `TextFrame` 4-line headline ("Bei dir wachsen…") with `soft_shadow=`, mixed para_styles | P | legacy `Headline4Line` block was deprecated — no current block matches mixed-style 4-line headlines |
| 160–176 | `TextFrame` "Jetzt Petition unterschreiben!" — Unterüberschrift | P | single-line CTA, no block fits |
| 178–193 | `Polygon` magenta ellipse Störer (rotation_deg=351) | P | legacy `StoererBadge` was deprecated; magenta ellipse stays primitive |
| 195–214 | `TextFrame` Störer text 3-line (rotation_deg=351) | P | rotated text in Störer-circle, no block |
| 216–230 | `Polygon` full-bleed `Dunkelgrün` rect (page1) | **B → `PageBackground.for_page(105, 148, color='Dunkelgrün', line_color='Black', line_width_pt=1)`** | identical block call to page0 |
| 232–258 | `TextFrame` 11-run body story (page1, headline + Fließtext + Unterüberschrift mix) | P | not a block — single-frame mixed-style body, no link_to chain |
| 260–281 | `TextFrame` ContactBlock candidate — 4 contact lines via `separator='breakline'`, `default_style_attrs={'ALIGN':'0','LINESP':'10'}`, `text_align=0` | **GAP → P** | see Gap #1 below — ContactBlock hardcodes `'para'` separator + no LINESP/ALIGN override surface |
| 283–300 | `TextFrame` Impressum — 2 runs (Bold "Impressum:" + Book body), `trail_style='Impressum'` | **GAP → P** | see Gap #2 below — Impressum block emits single Run, can't carry mixed-font two-run idiom |
| 302–320 | `ImageFrame` with `corner_radius_mm` + `custom_path` + inline image (Mail icon) | P | rounded-corner contact-icon; no block |
| 322–340 | `ImageFrame` rounded contact icon | P | identical pattern to 302 |
| 342–360 | `ImageFrame` rounded contact icon (different `corner_radius_mm=0.824`) | P | non-uniform corner radius variant |
| 362–380 | `ImageFrame` rounded contact icon (4th) | P | identical pattern to 302 |
| 382–398 | `ImageFrame` larger inline image (logo on back, 19.92 mm sq) | P | back-side logo |
| 400–416 | `TextFrame` URL "https://gruene.at/superreichebesteuern/" | P | one-line link, no block fits |
| 418–434 | `ImageFrame` small inline-image asset (URL underline?) | P | tail decorator |

**Block-substitutable count: 2 of 17** (the two PageBackground polygons). Everything else stays primitive — Postkarte simply doesn't have the Zeitung's repeating PageNumber / ColumnTextStory chains, and its Impressum + ContactBlock idioms diverge from the block APIs.

## Converter regeneration baseline

**CLI invocation (executor will run):**
```
python3 tools/sla_to_dsl.py \
    templates/postkarte-a6-kampagne/template.sla \
    templates/postkarte-a6-kampagne/build.py \
    --template-id postkarte-a6-kampagne \
    --assets-dir templates/postkarte-a6-kampagne/assets/
```
(Research used `/tmp/postkarte-regenerated.py` and a `/tmp` assets dir to avoid mutating committed artifacts.)

### Measured numbers

| Metric | Current build.py | Regenerated | Target | Status |
|---|---:|---:|---:|---|
| LOC | 437 | **383** | ≤280 | -54 LOC; **103 over target** |
| `extra_doc_attrs` keys | 113 | **23** | ≤23 | exact match (criterion met) |
| `extra_pdf_attrs` keys | 34 | **12** | ≤11 | 1 over (criterion missed by 1) |
| `add_color(...)` lines | 8 | 1 (`Green` only — 7 brand colors filtered) | — | improvement |
| `add_para_style(...)` lines | 9 | 9 (none filtered — postkarte uses German names not `ci/*`) | — | unchanged |
| `add_char_style(...)` lines | 2 | 2 (none filtered) | — | unchanged |
| `DocumentLayer` lines | 1 (in constructor) | 0 (brand auto-injects 4 layers) | — | **regression vs sla_diff** |
| `palette_replaces_ci=True` emitted | yes | **no** (Brand path forces it) | — | improvement |
| `clip_edit=True` auto-emitted | n/a | yes (both PageBackground polygons) | — | working |

### Why the LOC target is hard to hit (280 vs 383)

The remaining 383 LOC is dominated by:
- **9 ParaStyle declarations × ~40–50 chars each** = ~9 lines (already minimal — these are not `ci/*` and so must be template-local)
- **2 CharStyle declarations × ~470 chars each on single lines** = 2 lines (already minimal)
- **15 page items × avg ~22 lines each** = ~330 lines of frame DSL
- **Document(...) constructor + masters + page wiring** = ~30 lines

The frame DSL is already as tight as the converter knows how to emit. Block substitution of the 2 PageBackground polygons saves at most **~20 LOC** (each 11-line Polygon → 1-line block call). That gets us from 383 → ~365. Other achievable savings the planner should plan for:

| Lever | Estimated LOC saved |
|---|---:|
| 2× PageBackground via block | ~20 |
| Drop the `extra_pdf_attrs` 12th key (one-line saving inside the dict) — e.g. revisit `_normalize` for the one differing pdf key, or accept ≤12 per #5 emit | 0 (just compliance) |
| Inline single-attr Polygons / TextFrames onto fewer lines (style choice, not converter) | ~30–60 if planner accepts dense style |
| Move the 9 ParaStyle lines into a list-comprehension or shared helper | -3 to +5 (probably not worth it) |
| Drop unused `default_linesp_mode=2` and similar trail args where converter is over-emitting | small |

**Realistic LOC after planned hand-edits: ~330–360, NOT ≤280.** The 280-LOC target was an estimate from issue triage that did not account for: (a) Postkarte's 9 template-local para styles all needing explicit registration because none match `ci/*` names; (b) 5 contact-icon ImageFrames each with `inline_image_data=` taking up ~17 LOC each (~85 LOC total) that no block can collapse. The planner should propose **either reset the LOC target to ~340–360, OR mark "≤280" as a non-goal and document why** in EXECUTION.md per the issue's "verify and document the actual number" wording.

### Residual converter quirks (not blockers)

- The 5 contact-icon ImageFrames + the back-side logo ImageFrame (lines 252, 272, 292, 312, 332, 364, 418 of regen) still emit `xpos_pt`/`ypos_pt`/`width_pt`/`height_pt` because the converter's "drop pt-geometry" logic only fires when the mm/pt values agree to within tolerance — these icons have `corner_radius_mm` + `custom_path` non-axis-aligned paths, so the rect-path detection at sla_to_dsl.py:66 declines to drop them. Acceptable — those are baseline-fidelity-critical paths.
- One pdf key (likely `useDocBleeds` or similar) survives Brand filtering because `shared/ci-defaults.yml` doesn't list it. Planner can either widen ci-defaults (touches issue #5 surface) or accept 12 keys (1 over criterion).

## Block-substitution plan

For each of the 5 evidence-driven blocks landed in #5:

### PageBackground — 2 substitutions (clean fit)

**Where in regen:** lines 79–89 (page0) and 182–192 (page1). Identical kwargs except `y_mm` (-3 vs -3, equivalent) and parent page.

**Current pattern (11 LOC each):**
```python
page0.add(Polygon(
    x_mm=-2.9999999999999942,
    y_mm=-2.9999999999999942,
    w_mm=111.00000000000014,
    h_mm=153.99999999999994,
    layer=0,
    clip_edit=True,
    fill='Dunkelgrün',
    line_color='Black',
    line_width_pt=1,
))
```

**Proposed substitution (1 LOC each via block):**
```python
page0.add(PageBackground.for_page(105, 148, color='Dunkelgrün',
                                   line_color='Black', line_width_pt=1))
```

The `_SizedPageBackground` factory at `tools/sla_lib/builder/blocks.py:187–201` accepts `page_w_mm`, `page_h_mm`, `color`, `bleed_mm`, `layer`. **GAP**: the factory does NOT accept `line_color` or `line_width_pt` — but the dataclass `PageBackground` itself does (lines 154–155). Use `PageBackground(...)` directly with explicit `bleed_mm=3` and the polygon's `w_mm`/`h_mm` derived in-line, OR widen `for_page()` to forward `line_color`/`line_width_pt` (a 2-line edit at `blocks.py:198-201` — this IS in scope for this issue per the constraint that block-API gaps go back to issue #5 successors, not this issue).

**Recommendation to planner:** Use `PageBackground(...)` direct (not `for_page`) with explicit `bleed_mm` + sized derived w_mm/h_mm. Will produce identical Polygon coordinates because `PageBackground.emit()` does the math `x=-bleed, w=page_w+2*bleed`.

```python
# Equivalent with current block API:
page0.add(PageBackground(color='Dunkelgrün', bleed_mm=3,
                          line_color='Black', line_width_pt=1, layer=0))
# But the default x/y/w/h are 220×310 hardcoded — wrong for A6.
# Use _SizedPageBackground via for_page() but PR-fix it to forward line args.
```

The cleanest path is **widen `for_page()` to accept `line_color` and `line_width_pt`** — this is a 2-line addition to `blocks.py` and stays inside this issue's scope (it's a tiny block-API completion, not a redesign).

### Impressum — 0 substitutions (idiom gap)

**Where in regen:** lines 237–250 (page1, the `trail_style='Impressum'` frame).

**Why no substitution:** the regen frame has TWO runs:
```python
runs=[
    Run(text='Impressum:', font='Gotham Narrow Bold', fcolor='White', features='inherit', fshade=100),
    Run(text=' Medieninhaber und Herausgeber: Die Grünen Niederösterreich, ...'),
],
```
The `Impressum` block at `blocks.py:113-124` emits a single Run with `Impressum`'s `text=` argument as the body — it cannot carry the bold "Impressum:" prefix run. **Stays as primitive.** Plan a P2 follow-up to widen `Impressum` to accept either a `prefix_runs` argument or a `runs=` override (out of this issue's scope).

### ContactBlock — 0 substitutions (idiom gap)

**Where in regen:** lines 218–235 (page1, `trail_style='Kontaktmöglichkeiten'`).

**Why no substitution:** three mismatches between block and frame:
1. Frame uses `separator='breakline'` (Run-level soft line break); block hardcodes `'para'` (paragraph break) at `blocks.py:273`.
2. Frame carries `default_style_attrs={'ALIGN': '0', 'LINESP': '10'}` and `text_align=0`; block has no surface for either.
3. Frame's runs each carry `fcolor='White', fshade=100`; block accepts a single `fcolor=` but no `fshade`.

**Stays as primitive.** Plan a P2 follow-up to extend ContactBlock with `separator=`, `default_style_attrs=`, and `vertical_text_align=` passthrough — out of this issue's scope.

### PageNumber — 0 substitutions

Postkarte has no `pgno` variable frames. Block doesn't apply.

### ColumnTextStory — 0 substitutions

Postkarte has no linked-frame text-flow chains. Block doesn't apply.

### Net block savings

**~20 LOC** saved by 2× PageBackground substitution. Everything else stays primitive. **383 → ~363 LOC** before any other hand-tightening.

## DSL gaps surfaced (P2 follow-ups, NOT in this issue)

Document these in EXECUTION.md so future researchers pick them up:

1. **`PageBackground.for_page()` factory missing `line_color`/`line_width_pt` passthrough.** 2-line fix at `blocks.py:198-201` — small enough that planner could include in this issue's scope, but cleaner as a separate P2 if the planner wants strict isolation. The planner should make a call.

2. **`Impressum` block can carry only a single Run.** All three production templates need the bold "Impressum:" prefix. Widen to accept `prefix_text=` + `prefix_font=`, or a full `runs=` override.

3. **`ContactBlock` doesn't support `separator='breakline'`, `default_style_attrs=`, or per-run `fshade=`.** Postkarte's only contact frame uses all three. The block as-shipped fits the *defaulted* contact frame but not the corpus instance.

4. **`extra_pdf_attrs` ≤11 criterion is 1 key over.** The brand defaults at `shared/ci-defaults.yml` are missing one PDF attribute the Postkarte original carries. Audit and add it to the defaults yml — or accept 12 keys and revise the criterion.

## Visual-diff verification flow

The full executor flow (must run in this exact order):

```bash
# 1. Regenerate build.py from current template.sla
python3 tools/sla_to_dsl.py \
    templates/postkarte-a6-kampagne/template.sla \
    templates/postkarte-a6-kampagne/build.py \
    --template-id postkarte-a6-kampagne \
    --assets-dir templates/postkarte-a6-kampagne/assets/

# 2. Hand-edit build.py: substitute the 2 PageBackground polygons,
#    add explicit layers=[DocumentLayer('Hintergrund', ...)] to suppress
#    the 3 extra-layer warnings, drop redundant pdf attr if possible.

# 3. Rebuild template.sla from the new build.py
cd templates/postkarte-a6-kampagne && python3 build.py && cd -

# 4. Visual byte-clean check (THIS is the rendering acceptance gate)
python3 tools/visual_diff.py \
    templates/postkarte-a6-kampagne/template.sla \
    --baseline templates/postkarte-a6-kampagne/baseline.pdf \
    --tolerance templates/postkarte-a6-kampagne/diff.yml \
    --dpi 96 \
    --out build/validation/postkarte-a6-kampagne/

# 5. Structural diff (ON ITS OWN — this is what fails strict)
python3 tools/sla_diff.py \
    --left postkarte-vorlage-original.sla \
    --right templates/postkarte-a6-kampagne/template.sla
# (without --strict: critical=0 expected; with --strict: 8 ci/* extra-style warnings)

# 6. CI compliance check (already passing)
python3 tools/check_ci.py templates/postkarte-a6-kampagne/template.sla

# 7. Regenerate gallery previews + previews_for_sla hash
bin/render-gallery
git add templates/postkarte-a6-kampagne/{template.sla,build.py,page-*.png,preview.pdf,meta.yml}

# 8. Full validation (the criterion gate)
bin/validate --ci
```

Diff thresholds (`templates/postkarte-a6-kampagne/diff.yml`):
- `max_pixel_mismatch_pct: 1.0`
- `fuzz_pct: 5.0` (project cap)
- No per-page or per-region overrides — both pages must come in under 1% mismatch (research observation: actual mismatch is ~0.0001%).

## Risks and unknowns

| # | Risk | Severity | Evidence | Mitigation |
|---|---|---|---|---|
| R1 | **`bin/validate --ci`'s `sla_diff --strict` will fail** because Brand auto-injects 4 layers + 8 `ci/*` para styles into the SLA, producing 11 `extra-layer`/`extra-style` warnings that strict mode rejects. | **HIGH** (acceptance criterion blocker) | Measured: see `python3 tools/sla_diff.py --left postkarte-vorlage-original.sla --right <regen>.sla --strict` returns exit=1 with 11 warnings. `tools/sla_lib/tests/test_sla_to_dsl.py:99–106` already documents and tolerates the same regression in unit-test land via a code-level allowlist; the same allowlist does NOT exist in `bin/validate` or `tools/sla_diff.py`. | **Plan task: extend `tools/sla_diff.py` with an `--allow-brand-extras` flag** (or equivalent allowlist by code/name pattern) and have `bin/validate` pass it. Alternative: switch `bin/validate` to drop `--strict` and only check critical (less safe). Either way, the planner MUST schedule this before the rewrite can land green. |
| R2 | LOC target ≤280 is **not achievable** with the current block surface. | MEDIUM (criterion blocker) | Measured: regenerated = 383, optimistic post-blocks ≈ 363. Postkarte has 9 template-local ParaStyles + 5 contact-icon ImageFrames that no block collapses. | Plan task: relax target to ~360 in EXECUTION.md OR widen `Impressum` + `ContactBlock` blocks to absorb more idioms (P2, out of this issue). The 280 figure was a triage estimate; the issue's "verify and document the actual number" wording in acceptance criteria suggests the planner can document an honest number. |
| R3 | `extra_pdf_attrs` ≤11 is **1 over** (12 measured). | LOW | Measured. | Plan task: audit the missing key (likely `useDocBleeds` or `bleedMarks`) in `shared/ci-defaults.yml` and add it; verifies symbolically that all 3 templates' identical pdf attrs are hoisted. |
| R4 | Stale-preview gate (`bin/check-stale-previews`) will fail after rebuild because `meta.yml::previews_for_sla` SHA256 will no longer match. | MEDIUM (preflight blocker) | Measured: `tools/check_stale_previews.py:106-118` recomputes SHA of the regenerated `template.sla` against `meta.yml::previews_for_sla` and emits "stale: …; SLA hash mismatch" otherwise. | Plan task (mandatory): run `bin/render-gallery` after rebuild and commit the new `previews_for_sla` SHA + page PNGs + preview.pdf. |
| R5 | The `templates/postkarte-a6-kampagne/baseline.pdf` is the canonical pixel oracle; it was generated from the current `template.sla` (sha256 in meta.yml). If the regenerated SLA renders even a 1-pixel different glyph, visual_diff at 1% threshold absorbs it; if it renders > 1% different, baseline is stale and rebaselining is required. Research measured visual_diff exit 0 on the regen, so this is **not currently a risk** — flagged for awareness. | LOW | `bin/validate --ci` exit 0 on current main; visual_diff exit 0 on regen-without-blocks; both confirm baseline is fresh. | Watch the visual_diff per-page mismatch numbers; if they jump after block substitution, suspect a polygon-coords rounding regression in the `PageBackground` block emit math. |
| R6 | The `for_page()` factory of PageBackground doesn't pass through `line_color`/`line_width_pt`. | LOW | `tools/sla_lib/builder/blocks.py:187-201` — kwargs not forwarded. | Either widen the factory (recommended; 2-line fix; in scope for this issue), or use `PageBackground(...)` direct with custom `x_mm/y_mm/w_mm/h_mm`. |
| R7 | Non-determinism in inline_image_data round-trip. | LOW | sla_to_dsl.py:11-20 deliberately keeps inline images verbatim base64 to avoid PNG-encode drift. The 4 contact icons + logo + URL underline = 6 inline images, sized 5–87k bytes each, all preserved as the converter copies the base64 string literally. | None needed — issue #5 already proved this is byte-clean. |

## Recommendations to the planner

This is mechanical. **Six tasks** (one of which — sla_diff allowlist — is a hard prerequisite that may force scope expansion):

1. **(MUST-FIX-FIRST) Add brand-extras allowlist to sla_diff or bin/validate.** Without this, `bin/validate --ci` cannot pass on the rewritten Postkarte. Cleanest: add `--allow-brand-extras` flag to `tools/sla_diff.py` that filters `extra-layer` and `extra-style` warnings whose right-hand value matches `ci/*` or is one of `{Bilder, Text, Hilfslinien}`; have `bin/validate` pass it. Verify by running `bin/validate --ci` on **current main** with the flag — should still pass. **Acceptance: existing 3 templates' validate-ci output unchanged; postkarte-with-Brand validates green.** This is potentially out of issue #6's intended scope but the issue's acceptance criteria can't be met without it.

2. **Regenerate build.py.** Run `python3 tools/sla_to_dsl.py templates/postkarte-a6-kampagne/template.sla templates/postkarte-a6-kampagne/build.py --template-id postkarte-a6-kampagne --assets-dir templates/postkarte-a6-kampagne/assets/`. Verify the new file is 383 LOC and parses as Python. **Acceptance: file exists, `python3 -c "import ast; ast.parse(open('build.py').read())"` exits 0.**

3. **Hand-edit: substitute PageBackground × 2.** Replace lines ~79–89 and ~182–192 (regen line numbers) with `page0.add(PageBackground(...))` / `page1.add(PageBackground(...))`. Recommend widening `PageBackground.for_page()` at `tools/sla_lib/builder/blocks.py:198-201` to forward `line_color` and `line_width_pt` (2-line trivial edit) — keeps the build.py one-liners clean. **Acceptance: `python3 build.py` succeeds; resulting `template.sla` byte-identical at the layer-0 polygon XML attributes (compare via `tools/sla_diff.py` — should still report zero NEW critical/warning compared to baseline-of-step-2-output).**

4. **Hand-edit: add explicit `layers=[DocumentLayer('Hintergrund', ...)]` to `Document(...)`.** This kills the 3 `extra-layer` warnings. Use the exact kwargs from the current committed build.py line 31: `DocumentLayer(name='Hintergrund', visible=True, printable=True, editable=True, flow=True, transparent=1, blend=0, outline=False, layer_color='#000000')`. Adds ~3 LOC but is needed to keep sla_diff strict closer to clean. **Acceptance: regenerated SLA has exactly 1 `<LAYERS>` element matching the original.**

5. **Hand-edit: drop redundant `extra_pdf_attrs` keys (target ≤11).** Identify the 1 key over the criterion (likely `useDocBleeds` or `bleedMarks` — diff `differing_pdf_extras` against `Brand.gruene_noe().default_pdf_attrs`) and add it to `shared/ci-defaults.yml::default_pdf_attrs` so the converter filters it on next regen. **Acceptance: regenerated build.py's `extra_pdf_attrs` has ≤11 keys.**

6. **Rebuild + revalidate + regenerate gallery.** `cd templates/postkarte-a6-kampagne && python3 build.py && cd ../..; bin/render-gallery; bin/validate --ci`. Verify visual_diff under tolerance, sla_diff (with brand-extras allowlist from task 1) is clean, all three templates green. Update `meta.yml::previews_for_sla` and commit the new page-NN.png + preview.pdf alongside build.py and template.sla. **Acceptance: `bin/validate --ci` exits 0; `pytest tools/sla_lib/tests -x` exits 0; final build.py LOC documented in EXECUTION.md.**

### Order of operations + LOC arithmetic

| Step | Net LOC change | Cumulative LOC |
|---|---:|---:|
| Start (current committed) | — | 437 |
| 2. Regenerate via converter | -54 | 383 |
| 3. PageBackground × 2 substitution | -20 | 363 |
| 4. Add explicit layers=[Hintergrund] | +3 | 366 |
| 5. Drop 1 pdf attr (no LOC change in build.py; ci-defaults.yml gains 1 line) | 0 | 366 |
| **Final estimate** | — | **~366** |

**The planner should propose ≤370 as the realistic LOC target and document why ≤280 was unattainable** in EXECUTION.md per the issue's "verify and document the actual number" wording.

### Style of rewrite

**"Regenerate then hand-edit blocks + layers + pdf-attr"** — NOT a from-scratch rewrite. The converter does 95% of the work. Hand edits are surgical: 2 block substitutions + 1 layer override + 1 ci-defaults.yml addition. This same pattern transfers to issues #7 (Plakat) and #8 (Zeitung):
- Plakat will see similar 113+34 attrs hoisting and `palette_replaces_ci` removal; block substitutions likely zero (research not yet done — Plakat has no PageBackground / Impressum / ContactBlock matches per blocks.py corpus comments).
- Zeitung will see the largest block-substitution payoff (12× PageNumber + 84× ColumnTextStory chains + 1× Impressum + 1× PageBackground) — that's the issue where the LOC delta will be dramatic.

The Postkarte rewrite is the **smallest payoff** of the three but establishes the pattern. The planner should size EXECUTION.md expectations accordingly — this is mostly a "prove the converter works on a real template + close the validate-strict gap" issue, not a "huge LOC win" issue.

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` file in the worktree root (`ls /root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks/CLAUDE.md` → not found). No `.claude/skills/` directory either. The repo carries no project-level invariants beyond what ISSUE.md and the existing tests encode. **No additional constraints to honor.**

## Sources

### HIGH confidence (measured directly)
- `templates/postkarte-a6-kampagne/build.py` — current 437 LOC, all 17 frame definitions read line-by-line.
- `tools/sla_to_dsl.py` — converter source, lines 1054–1100 (Brand emit), 66–117 (rect-path detection).
- `tools/sla_lib/builder/blocks.py` — all 5 block APIs read; corpus references verified at lines 86–87, 129–131, 233–234.
- `tools/sla_lib/builder/brand.py` — Brand.gruene_noe() return shape inspected via Python repr.
- `tools/sla_lib/tests/test_sla_to_dsl.py:75–108` — pre-existing acknowledgement that brand auto-injection produces `extra-style`/`extra-layer` warnings that the test allowlist tolerates.
- `tools/sla_diff.py:1205–1209` — strict mode exit logic confirmed.
- `tools/check_stale_previews.py:106–118` — SHA-mismatch detection logic confirmed.
- `bin/validate` — full pipeline read.
- `templates/postkarte-a6-kampagne/diff.yml` — visual-diff thresholds.
- `docs/diff-tolerance.md` — schema and rebaseline workflow.
- Live measurement: `python3 tools/sla_to_dsl.py ...` produces 383-LOC build.py.
- Live measurement: `python3 build.py` on regen produces a valid SLA; `python3 tools/visual_diff.py ...` exits 0; `python3 tools/sla_diff.py ... --strict` exits 1 with 11 warnings.

### MEDIUM confidence
- LOC saving estimates per block-substitution step (extrapolated from line counts but not measured by actually performing the edit).
- Identification of the specific over-count key in `extra_pdf_attrs` (the planner needs to grep — research did not isolate which of the 12 keys is the surplus).

### LOW confidence (none load-bearing)
- Whether widening `PageBackground.for_page()` to forward `line_color`/`line_width_pt` is "in scope" or "out of scope" for this issue — judgment call for the planner. Research recommends in-scope (2-line edit, mechanical, no API breakage).

## Metadata

- **Sub-agents used:** None — this issue's research was done end-to-end in the orchestrator agent because the codebase analysis had to read full file contents (which would have exceeded sub-agent return-text budgets), the ecosystem analysis is pure stdlib + project-internal, and the pitfalls analysis is purely codebase-internal (sla_diff strict-mode, stale-preview gate). Spawning sub-agents would have multiplied tokens without adding signal.
- **Research date:** 2026-05-07.
- **Confidence breakdown:**
  - Codebase audit: HIGH (every line counted, every block API checked).
  - Block fitness: HIGH (corpus references verified against current frames).
  - LOC arithmetic: HIGH for the regenerator delta (measured), MEDIUM for the post-edit estimate (arithmetic).
  - Validate-strict regression: HIGH (reproduced live; flagged in #5's own tests).
  - LOC ≤280 feasibility: HIGH that it is NOT achievable; recommendation is to raise the target.
- **Raw research files:** None — no sub-agents, all findings are in this RESEARCH.md.
