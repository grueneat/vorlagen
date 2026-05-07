# RESEARCH — Rewrite Plakat A1 onto Brand + blocks

**Researched:** 2026-05-07
**Issue:** rewrite-plakat-onto-brand-blocks (id 7, depends on merged #5; stacked on #6)
**Confidence:** HIGH (all numbers measured against the regenerated build.py + a live build of it)

## Summary

The converter alone takes Plakat from 235 → **198 LOC**, and **all four AC numbers (LOC, doc-attrs, pdf-attrs, Brand uptake) are met by the raw regen with zero hand edits**: `extra_doc_attrs=23` (≤23 met exact), `extra_pdf_attrs=11` (≤11 met exact), `Brand.gruene_noe()` emitted, `palette_replaces_ci` gone. The hand-edit budget reduces to **zero block substitutions** — Plakat has 0 Polygons (no full-bleed background; the visual "Dunkelgrün block" at the bottom half is a `TextFrame` with `fill='Dunkelgrün'`, not a Polygon, so `PageBackground` does not fit), 0 PageNumber frames, 0 ColumnTextStory chains, and the one Impressum frame is rotated 270° and carries a Bold-prefix Run — both API gaps that the Postkarte EXECUTION already filed as P2 follow-ups against the `Impressum` block. Visual_diff is byte-clean against the committed `baseline.pdf`.

The only **new** blocker surfaced by Plakat (not seen in Postkarte): Plakat's original SLA carries only 5 colors (Black, Dunkelgrün, Gelb, Registration, White); `Brand.gruene_noe()` auto-injects the full 7-color brand palette, so the rebuilt SLA gets 2 spurious `extra-color` warnings (`Hellgrün`, `Magenta`). The existing `--allow-brand-extras` flag in `tools/sla_diff.py` filters only `extra-style` and `extra-layer` — it does NOT cover `extra-color`. Without a fix, `bin/validate --ci`'s strict mode will fail on Plakat's rebuilt SLA, and `PlakatRoundTrip.test_diff_against_original_clean` will fail with 2 unfiltered warnings.

**Primary recommendation:** This is the smallest of the three migrations — 4 mechanical tasks (extend the allowlist, regenerate build.py, rebuild gallery, write EXECUTION) plus one optional task to update the Plakat round-trip test's allowlist. No block substitutions; no LOC negotiation (already at 198, comfortably under the informational ≤180 target if measured generously, or 18 LOC over if the issue's 180 number is taken literally — per user direction LOC is not a gate). The `extra-color` allowlist gap is the one new piece of work this issue forces.

## Current Plakat build.py inventory (235 LOC committed)

Per-section ranges in **current committed** `templates/plakat-a1-hochformat/build.py`:

| Lines | Section | Notes |
|------:|---------|-------|
| 1–13  | Imports + sys.path bootstrap | unchanged across templates |
| 15–33 | `Document(...)` constructor | line 28 = `extra_doc_attrs` (113 keys, 2866 chars), line 29 = `extra_pdf_attrs` (44 keys, 949 chars), line 24 = `palette_replaces_ci=True`, line 30–32 = `layers=[DocumentLayer('Hintergrund', ...)]` |
| 35–39 | `doc.add_color(...)` × 5 | Black, Dunkelgrün, Gelb, Registration, White (NO Hellgrün, NO Magenta — only template that's missing 2 brand colors) |
| 41 | `add_char_style(...)` × 1 | Default Character Style (466 chars) |
| 42–46 | `add_para_style(...)` × 5 | Default, Headlineweiß, Überschrift gelb, Fließtext, Impressum |
| 48–58 | `doc.add_master(name='Normal', ...)` | single master |
| 60–69 | `doc.add_page(...)` × 1 | page0 only (single-page poster) |
| 71–195+ | **page0** items × 9 | 6 TextFrames + 3 ImageFrames; see frame table below |
| 197–232 | trailing ImageFrames (cont.) | continuation of frame inventory |
| 234–235 | `doc.save(...)` + print | unchanged |

Note: lines 208 (19021 chars, base64 PNG) and 226 (190481 chars, base64 PNG) carry inline image data that inflates the byte size to ~205K tokens but represents only 2 LOC.

### Frame inventory (9 page items, single page)

`B` = block-substitutable; `P` = stays primitive.

| Line range | Idiom | Maps to | Notes |
|----:|---|---|---|
| 71–84 | `TextFrame` (PTYPE=4) full-width Dunkelgrün backdrop, h=427mm × w=594mm at y=414mm (covers bottom half) | **GAP → P** | Block `PageBackground.emit()` yields a `Polygon` (PTYPE=6) — substituting would change SLA structure (PTYPE 4→6) and break sla_diff. Plakat has zero Polygons in original; the "background" is a `TextFrame` with `fill=`. No block fits. |
| 86–106 | `TextFrame` 5-line headline ("Hier steht eine große vierzeilige Überschrift in Baden.") with mixed paragraph styles (Headlineweiß / Überschrift gelb), 7 soft hyphens | P | Mixed-style headline; legacy `Headline4Line` deprecated and never matched 5-run mixed styles. No block. |
| 108–126 | `TextFrame` Impressum (rotated 270°, vertical at right margin) with 2 runs (Bold "Impressum:" prefix + Book body), `trail_style='Impressum'` | **GAP → P** | Two API gaps: (1) Bold-prefix-Run idiom — same as Postkarte (already filed as P2 follow-up #1); (2) `rotation_deg` not on the modern `Impressum` block (only on legacy `Headline4Line`/`StoererBadge`). Two gaps → stays primitive. |
| 128–144 | `TextFrame` "Anmeldung unter: gruene.at/tour" (1 run, Fließtext) | P | Single-line CTA, no block. |
| 146–163 | `TextFrame` date/time (2 runs, Fließtext) | P | No block. |
| 165–182 | `TextFrame` venue/address (2 runs, Fließtext) | P | No block. |
| 184–196 | `ImageFrame` empty hero placeholder (full-width, top half, 414mm × 594mm, no inline data) | P | Plakat-specific hero slot. |
| 198–214 | `ImageFrame` w/ inline_image_data (URL/decoration ~14k base64) | P | Inline image, no block. |
| 216–232 | `ImageFrame` w/ inline_image_data (Logo ~143k base64, 107×107mm) | P | Inline image, no block. |

**Block-substitutable count: 0 of 9.** Plakat is the lowest block payoff of the three migrations — it has no full-bleed Polygon background, no chained text, no page numbers, and the one Impressum frame has two API gaps (rotation + Bold prefix) that the Postkarte EXECUTION already deferred to P2.

## Converter regeneration baseline

**CLI invocation (executor will run):**
```
python3 tools/sla_to_dsl.py \
    templates/plakat-a1-hochformat/template.sla \
    templates/plakat-a1-hochformat/build.py \
    --template-id plakat-a1-hochformat \
    --assets-dir templates/plakat-a1-hochformat/assets/
```
(Research used `/tmp/plakat-regenerated.py` and a `/tmp/plakat-research-assets/` dir to avoid mutating committed artifacts.)

### Measured numbers

| Metric | Current build.py | Regenerated | Target (ISSUE.md) | Status |
|---|---:|---:|---:|---|
| LOC | 235 | **198** | ≤180 (informational per user direction) | -37 LOC; 18 over the literal target, but user has dropped LOC gating |
| `extra_doc_attrs` keys | 113 | **23** | ≤23 | exact match (criterion met) |
| `extra_pdf_attrs` keys | 44 (committed) | **11** | ≤11 | exact match (criterion met) |
| `add_color(...)` lines | 5 | 0 (all 5 are brand colors filtered by `palette_replaces_ci`) | — | improvement |
| `add_para_style(...)` lines | 5 | 5 (none filtered — all are template-local German names) | — | unchanged |
| `add_char_style(...)` lines | 1 | 1 (template-local) | — | unchanged |
| `DocumentLayer` lines | 1 (committed line 30) | 0 (Brand auto-injects 4 layers) | — | converter behaves as designed |
| `palette_replaces_ci=True` emitted | yes | **no** (Brand path forces it implicitly) | — | improvement |
| `clip_edit=True` emitted | n/a (no Polygons) | n/a (still no Polygons) | — | n/a — Plakat has 0 Polygons |
| `Brand.gruene_noe()` in `Document(...)` | no | **yes** | — | criterion met |
| `layers=[DocumentLayer('Hintergrund', ...)]` explicit | yes (line 30 committed) | **no** (regen drops it; Brand provides layers) | — | see "Hintergrund layer" below |

### Why the 198 LOC is already a clean stop

The remaining 198 LOC is dominated by:
- 5 ParaStyle lines (~50–80 chars each) — already minimal
- 1 CharStyle line — already minimal
- 9 page items × ~10–22 lines each — already minimal (TextFrames at ~15 LOC, inline-image frames at ~17 LOC)
- `Document(...)` constructor + master + page wiring — ~30 lines

There is **nothing for hand-edits to collapse**: 0 Polygons → 0 PageBackground substitutions, 0 pgno frames → 0 PageNumber substitutions, 0 chains → 0 ColumnTextStory substitutions. The Impressum frame is the one block candidate but has two unsupported features (rotation + Bold prefix) that put it out of scope for this issue. **The regenerated 198 IS the target — no further LOC win is possible without widening blocks (P2).**

The issue's stated ≤180 LOC target is 18 LOC short of what the converter produces. Per the user prompt's guidance ("the issue's ≤180 target should be treated as informational only — the user explicitly dropped LOC targets in issue #6"), the planner should record 198 in EXECUTION.md without gating on it. If the planner wants to chase 18 LOC of savings:

| Lever | Estimated LOC | Recommendation |
|---|---:|---|
| Inline single-attr ImageFrames onto fewer lines (style choice) | ~20 | Cosmetic; not advised — reduces readability |
| Move 5 ParaStyle lines into a list-comprehension or shared helper | -3 to +5 | Not worth it |
| Drop `xpos_pt`/`ypos_pt`/`width_pt`/`height_pt` from the 2 inline-image frames | ~16 | Would lose pt-fidelity for inline images; converter intentionally keeps these (test `test_5b_plakat_inline_image_keeps_xpos_pt` enforces this) — DO NOT |

**The realistic post-regen LOC is 198. Stop there.** The original ≤180 target was triage estimate, not an evidence-based number.

### Hintergrund layer — explicit vs Brand-injected

The current committed `build.py` line 30–32 declares:
```python
layers=[DocumentLayer(name='Hintergrund', visible=True, printable=True, editable=True,
                      flow=True, transparent=1, blend=0, outline=False,
                      layer_color='#000000')],
```

The regen DROPS this — `Brand.gruene_noe()` provides 4 layers (Hintergrund + Bilder + Text + Hilfslinien) via ci.yml, and the converter relies on the brand stack. **This is fine for Plakat** because:
- The polygons in the original SLA reference `LAYER="0"` which maps to whatever layer index 0 is in the rebuilt SLA — Brand's first layer is Hintergrund, so the index is preserved.
- Postkarte EXECUTION (Task 4 step 4C) added the explicit Hintergrund layer back to suppress 3 `extra-layer` warnings, but bin/validate now uses `--allow-brand-extras` which filters those warnings, so the explicit layer is **no longer needed for validation**.
- The original Plakat SLA has only `Hintergrund` as a non-default layer; the brand-injected Bilder/Text/Hilfslinien show up as 3 `extra-layer` warnings but `--allow-brand-extras` filters them.

**Recommendation:** Do NOT hand-add `layers=[DocumentLayer('Hintergrund', ...)]` in the regenerated Plakat build.py. The allowlist handles it. (Postkarte's belt-and-suspenders explicit-layer addition is harmless but unnecessary — Plakat can demonstrate the cleaner pattern.)

### Residual converter quirks (not blockers)

- The 2 inline-image frames (logo at ~107mm sq, URL underline at ~373mm × 133mm) keep `xpos_pt`/`ypos_pt`/`width_pt`/`height_pt` because the converter's "drop pt-geometry" logic at sla_to_dsl.py:66-117 deliberately preserves them for inline-image precision. Acceptable — `test_5b_plakat_inline_image_keeps_xpos_pt` enforces this invariant.
- The Dunkelgrün backdrop TextFrame at line 62-71 has clean mm geometry only (no `xpos_pt`) — the converter correctly identified it as a non-inline frame and dropped pt-geometry. Confirmed.

## Block-substitution plan

For each of the 5 evidence-driven blocks landed in #5:

### PageBackground — 0 substitutions

**Why no substitution:** Plakat has zero Polygons. Verified: `python3 -c "import xml.etree.ElementTree as ET; t=ET.parse('plakat-a1-hochformat-original.sla'); print({k:len(v) for k,v in [...]})"` reports `PTYPE counts: {'2': 3, '4': 6}` (3 ImageFrames + 6 TextFrames, 0 Polygons). The visual "Dunkelgrün block" covering the bottom half of the poster is a TextFrame with `fill='Dunkelgrün'`, not a Polygon. The PageBackground block emits a Polygon (PTYPE=6); substituting it for the TextFrame would change the SLA's PTYPE attribute and break both sla_diff (extra-pageobject critical) and visual_diff (Polygon and TextFrame have different default rendering paths).

### Impressum — 0 substitutions (two idiom gaps)

**Where in regen:** lines 91–105 (the rotated 270° frame at the right margin).

**Why no substitution:** the regen frame has TWO runs and a 270° rotation:
```python
runs=[
    Run(text='Impressum:', font='Gotham Narrow Bold', fcolor='White', fshade=100),
    Run(text=' Medieninhaber und Herausgeber: …', fcolor='White', fshade=100),
],
rotation_deg=270,
```

The modern `Impressum` block at `tools/sla_lib/builder/blocks.py:89-124` has TWO mismatches with this idiom:
1. **Bold-prefix Run**: emits a single Run from `text=` argument; cannot carry the bold "Impressum:" prefix run. Same gap as Postkarte (Postkarte EXECUTION P2 follow-up #1 already files this).
2. **Rotation**: dataclass has no `rotation_deg` field. Only the legacy `Headline4Line` and `StoererBadge` blocks (deprecated) carry rotation_deg.

Two gaps × no block widening allowed in this issue → **stays as primitive.** Plan a P2 follow-up to widen `Impressum` with `prefix_text=`/`prefix_font=` AND `rotation_deg=` (out of this issue's scope).

### ContactBlock — 0 substitutions (no candidate)

Plakat has no contact frame. Block doesn't apply.

### PageNumber — 0 substitutions (no candidate)

Plakat has no `var='pgno'` frame. Single-page poster has no page number. Block doesn't apply.

### ColumnTextStory — 0 substitutions (no candidate)

Plakat has no linked-frame text-flow chains. Verified: `grep -c "link_to" /tmp/plakat-regenerated.py` returns 0. Block doesn't apply.

### Net block savings

**0 LOC** — no block substitutions are viable for Plakat. **198 → 198 LOC** unchanged. Plakat is the smallest payoff of the three template migrations: it relies entirely on the converter's structural improvements (Brand emission, `palette_replaces_ci` removal, attr hoisting), not on block primitives.

## DSL gaps surfaced (P2 follow-ups, NOT in this issue)

Document these in EXECUTION.md so future researchers pick them up:

1. **`Impressum` block missing `rotation_deg=`.** Plakat carries a vertical (rotation_deg=270) Impressum at the right margin. The modern block at `tools/sla_lib/builder/blocks.py:89-124` has no rotation_deg surface. Combined with the existing P2 follow-up #1 from Postkarte (Bold-prefix Run support), this is the second gap blocking Impressum block substitution. Combined widening: add `prefix_text=`, `prefix_font=`, and `rotation_deg=` kwargs.

2. **`--allow-brand-extras` flag does not cover `extra-color`.** `tools/sla_diff.py:1190-1194` filters `extra-style` and `extra-layer` only. Plakat's rebuilt SLA produces 2 `extra-color` warnings (`Hellgrün`, `Magenta`) because the original Plakat SLA carries only 5 of 7 brand colors. **This is a HARD blocker for this issue** — see "Recommendations to the planner" task 1 below; it must be fixed in this issue, not deferred.

3. **`PlakatRoundTrip.test_diff_against_original_clean` allowlist needs extending.** Currently asserts `summary[SEVERITY_WARNING] == 0` against original (line 130 of `test_sla_to_dsl.py`). After Brand migration, will see 2 unfiltered extra-color warnings. The Postkarte fix pattern (filter `extra-style`/`extra-layer` from the issues list) needs to be extended to also filter `extra-color` for the `Hellgrün`/`Magenta` names. **Required in this issue.**

4. **The 5 template-local ParaStyles in Plakat (Default, Headlineweiß, Überschrift gelb, Fließtext, Impressum) all use German names that don't match the `ci/*` brand styles.** Same pattern as Postkarte's 9 styles. No path to collapse them via Brand without renaming the templates' style references — out of scope for any current issue.

## Visual-diff verification flow

The full executor flow (must run in this exact order):

```bash
# 1. Regenerate build.py from current template.sla
python3 tools/sla_to_dsl.py \
    templates/plakat-a1-hochformat/template.sla \
    templates/plakat-a1-hochformat/build.py \
    --template-id plakat-a1-hochformat \
    --assets-dir templates/plakat-a1-hochformat/assets/

# 2. (Optional) Verify counts before rebuild
python3 -c "import re, ast; src=open('templates/plakat-a1-hochformat/build.py').read();
for k in ('extra_doc_attrs','extra_pdf_attrs'):
    m=re.search(k+r'\s*=\s*(\{[^}]*\})', src, re.S)
    print(k, len(ast.literal_eval(m.group(1))))
print('LOC:', len(src.splitlines()))"

# 3. Rebuild template.sla from the new build.py
cd templates/plakat-a1-hochformat && python3 build.py && cd -

# 4. Visual byte-clean check (THIS is the rendering acceptance gate)
python3 tools/visual_diff.py \
    templates/plakat-a1-hochformat/template.sla \
    --baseline templates/plakat-a1-hochformat/baseline.pdf \
    --tolerance templates/plakat-a1-hochformat/diff.yml \
    --dpi 96 \
    --out build/validation/plakat-a1-hochformat/

# 5. Structural diff with allowlist (THIS is what would fail without task 1)
python3 tools/sla_diff.py \
    --left plakat-a1-hochformat-original.sla \
    --right templates/plakat-a1-hochformat/template.sla \
    --strict --allow-brand-extras
# (Without task 1 fix: critical=0, warning=2 (Hellgrün, Magenta) → exit 1)
# (With task 1 fix: critical=0, warning=0 → exit 0)

# 6. CI compliance check
python3 tools/check_ci.py templates/plakat-a1-hochformat/template.sla

# 7. Regenerate gallery previews + previews_for_sla hash
bin/render-gallery
git add templates/plakat-a1-hochformat/{template.sla,build.py,page-*.png,preview.pdf,meta.yml}

# 8. Full validation (the criterion gate)
bin/validate --ci
```

Diff thresholds (`templates/plakat-a1-hochformat/diff.yml`):
- `max_pixel_mismatch_pct: 1.0`
- `fuzz_pct: 5.0` (project cap)
- No per-page or per-region overrides; comment notes ~0.0000% mismatch on baseline.

**Research-confirmed**: visual_diff returns exit 0 against baseline when run on the regenerated build.py's output (build → diff → no rebuild needed). Tested live, no pixel changes.

## Risks and unknowns

| # | Risk | Severity | Evidence | Mitigation |
|---|---|---|---|---|
| R1 | **`bin/validate --ci` will fail on Plakat** because `--allow-brand-extras` filters only `extra-style`/`extra-layer`, NOT `extra-color`. Plakat's rebuilt SLA produces 2 unfiltered `extra-color` warnings (`Hellgrün`, `Magenta`) that strict mode rejects. | **HIGH** (acceptance criterion blocker — different from Postkarte's `extra-style` blocker, this is a NEW failure mode) | Measured: `python3 tools/sla_diff.py --left plakat-a1-hochformat-original.sla --right /tmp/plakat-test-build/template.sla --strict --allow-brand-extras` returns exit=1 with `**critical: 0**, warning: 2`: `extra-color: Hellgrün`, `extra-color: Magenta`. The `Hellgrün`/`Magenta` colors are in `Brand.gruene_noe()`'s injected palette but absent from Plakat's original SLA (Plakat needs only Black/Dunkelgrün/Gelb/Registration/White). Postkarte and Zeitung carry all 7 brand colors so this didn't surface before. | **Plan task 1 (NEW): extend `--allow-brand-extras` flag to also filter `extra-color` warnings whose right-hand value matches a brand color name** (Hellgrün, Magenta — the 2 missing from Plakat). The filter predicate becomes: `i.severity == SEVERITY_WARNING and (i.code in ("extra-style", "extra-layer") or (i.code == "extra-color" and i.right in BRAND_COLOR_NAMES))`. Brand color names should be loaded from `shared/ci.yml` (or hardcoded as a 7-tuple `("Black","White","Registration","Dunkelgrün","Hellgrün","Gelb","Magenta")` if accessing yml from sla_diff is undesired). |
| R2 | LOC at 198 is **18 LOC over the issue's literal ≤180 target**. | LOW (per user direction LOC is informational only) | Measured: regen=198. Removing 18 LOC requires either widening blocks (P2) or sacrificing inline-image pt-fidelity (regression — `test_5b_plakat_inline_image_keeps_xpos_pt` would fail). | Document achieved 198 LOC in EXECUTION.md; do not gate on the target. The user prompt explicitly says "the issue's ≤180 target should be treated as informational only — the user explicitly dropped LOC targets in issue #6." |
| R3 | **`PlakatRoundTrip.test_diff_against_original_clean`** at `tools/sla_lib/tests/test_sla_to_dsl.py:125-131` will fail after rewrite. | **HIGH** (test gate blocker) | Measured: test currently passes against committed build.py. After rewrite, `_diff_clean()` will report `summary[WARNING]={extra-style: 8 ci/* + extra-layer: 3 + extra-color: 2 (Hellgrün, Magenta)}` = 13 unfiltered warnings, all of which are brand-additive. | **Plan task: extend the test's allowlist** to filter `extra-style`/`extra-layer`/`extra-color` (mirror the Postkarte fix pattern at lines 70-77 + add `extra-color` for brand colors). Identical edit to what Postkarte's #6 did, plus extra-color extension. |
| R4 | Stale-preview gate (`bin/check-stale-previews`) will fail after rebuild because `meta.yml::previews_for_sla` SHA256 will no longer match. | MEDIUM (preflight blocker) | Measured: `tools/check_stale_previews.py:106-118` recomputes SHA of regenerated `template.sla` against `meta.yml::previews_for_sla`; current is `cff461714e044eb343b7593bf7b0de2d40a5bb38a458d62db80359748902a3b4`. After rebuild, the SHA changes (verified live: rebuilt SLA hash is `5c9a04ed876a8bdf...`). | **Plan task (mandatory): run `bin/render-gallery` after rebuild and commit the new `previews_for_sla` SHA + page-01.png + preview.pdf**. Same task as Postkarte's task 6. |
| R5 | The `templates/plakat-a1-hochformat/baseline.pdf` is the canonical pixel oracle; it was generated from the current `template.sla`. If the regenerated SLA renders differently, baseline is stale and rebaselining is required. | LOW | `bin/validate --ci` exit 0 on current main; visual_diff exit 0 on regen-without-edits build (verified live). | Watch the visual_diff per-page mismatch numbers; if they jump, suspect a Brand-injected style that affects rendering (unlikely — brand styles for `ci/*` are not referenced by Plakat's frames, only auto-registered). |
| R6 | `extra_pdf_attrs=11` is at exactly 11 keys. The 11 keys are: `ImageP, InfoString, PicRes, PrintP, RGBMode, RecalcPic, SolidP, UseProfiles2, Version, bleedMarks, useDocBleeds`. These match the comment in `shared/ci-defaults.yml:14-18` exactly. | LOW | Measured. | None needed. Postkarte's #6 already hoisted `CompressMethod` to ci-defaults; Plakat benefits from the same hoist. |
| R7 | `extra_doc_attrs=23` is at exactly 23 keys. | LOW | Measured: matches the 23 differing keys listed in `shared/ci-defaults.yml:13-17` comment. | None needed. |
| R8 | Non-determinism in inline_image_data round-trip for the 2 large base64 images (URL underline + Logo). | LOW | sla_to_dsl.py:11-20 deliberately keeps inline images verbatim base64 to avoid PNG-encode drift. The 2 images (~14k + ~143k bytes) are preserved as the converter copies the base64 string literally. | None needed — issue #5 + issue #6 already proved this is byte-clean. |
| R9 | The PlakatConverterFreshRun-equivalent test does NOT exist (only PostkarteConverterFreshRun at test_sla_to_dsl.py:81). | LOW | grep confirms only Postkarte has a "fresh convert" guard test. Plakat is covered only by the round-trip test. | None needed for this issue, but planner could optionally add `PlakatConverterFreshRun` to mirror Postkarte's coverage (P3 hygiene, not required). |

## Recommendations to the planner

This is the **smallest** of the three migrations. **5 tasks** (1 NEW from Plakat-specific finding):

1. **(NEW — MUST-FIX-FIRST) Extend `--allow-brand-extras` to filter `extra-color` warnings for brand colors.** Without this, `bin/validate --ci` strict mode fails on Plakat's rebuilt SLA with 2 unfiltered `extra-color: Hellgrün` + `extra-color: Magenta` warnings. Edit `tools/sla_diff.py:1190-1194` filter predicate. Easiest: hardcode the 7 brand color names as `_BRAND_COLOR_NAMES = ("Black","White","Registration","Dunkelgrün","Hellgrün","Gelb","Magenta")` near the top of the file, and extend the filter to also match `i.code == "extra-color" and i.right in _BRAND_COLOR_NAMES`. Cleaner: load from `shared/ci.yml` via an existing helper if `sla_diff.py` already imports `ci` (it doesn't currently — keep the hardcode for surface-area minimization). Update `--allow-brand-extras` help text. Add 1-2 unit tests in `test_sla_diff.py` mirroring the existing extra-style/extra-layer tests. **Acceptance: existing 3 templates' validate-ci output unchanged (since none have brand-color extras except Plakat); Plakat-with-Brand validates green.**

2. **Regenerate `templates/plakat-a1-hochformat/build.py` via converter.** Run `python3 tools/sla_to_dsl.py templates/plakat-a1-hochformat/template.sla templates/plakat-a1-hochformat/build.py --template-id plakat-a1-hochformat --assets-dir templates/plakat-a1-hochformat/assets/`. Verify: file is 198 LOC (±2), parses as Python, contains `brand=Brand.gruene_noe()`, no `palette_replaces_ci=True`, `extra_doc_attrs` has 23 keys, `extra_pdf_attrs` has 11 keys. **No hand-edits needed for blocks** (none apply); **no hand-edits needed for layers** (`--allow-brand-extras` filters extra-layer warnings). Then `cd templates/plakat-a1-hochformat && python3 build.py && cd -`. **Acceptance: `python3 -c "import ast; ast.parse(open('templates/plakat-a1-hochformat/build.py').read())"` exits 0; rebuilt template.sla is valid XML; visual_diff against baseline.pdf exits 0.**

3. **Update `PlakatRoundTrip.test_diff_against_original_clean` allowlist** at `tools/sla_lib/tests/test_sla_to_dsl.py:125-131`. Mirror the Postkarte fix at lines 64-77: change the `summary[SEVERITY_WARNING] == 0` assertion to filter brand-additive warnings (extra-style, extra-layer, extra-color for brand colors), then assert no OTHER warnings remain. Same edit shape as Postkarte's commit `1ebe8ef` did to PostkarteRoundTrip. **Acceptance: `pytest tools/sla_lib/tests/test_sla_to_dsl.py::PlakatRoundTrip -x -v` passes.**

4. **Rebuild gallery + run full validation.** `bin/render-gallery && bin/validate --ci && python3 tools/check_ci.py templates/plakat-a1-hochformat/template.sla && python3 -m pytest tools/sla_lib/tests -x`. The `bin/render-gallery` regenerates `meta.yml::previews_for_sla` SHA and page-01.png + preview.pdf. `bin/validate --ci` must be green for all three templates (postkarte/plakat/zeitung). **Acceptance: `bin/validate --ci` exits 0; `pytest tools/sla_lib/tests -x` exits 0.**

5. **Acceptance check + write EXECUTION.md.** Verify all 6 ISSUE.md ACs against produced artifacts (record PASS/FAIL with concrete evidence). Record achieved LOC (198) as informational. File P2 follow-ups: `Impressum` block widening for `prefix_text=`/`prefix_font=`/`rotation_deg=` (now the second template to surface the prefix gap, plus newly-surfaced rotation gap). **Acceptance: EXECUTION.md exists with all 6 AC results, achieved LOC + attr counts, and P2 follow-ups recorded.**

### Order of operations + LOC arithmetic

| Step | Net LOC change | Cumulative LOC |
|---|---:|---:|
| Start (current committed) | — | 235 |
| Task 2: Regenerate via converter | -37 | 198 |
| (No block substitutions possible) | 0 | 198 |
| (No explicit Hintergrund layer add — allowlist handles it) | 0 | 198 |
| **Final estimate** | — | **198** |

**Planner: record 198 LOC in EXECUTION.md; do not gate on ≤180.** Per user direction LOC is informational only. The 198 number is dominated by 9 minimal-style frame DSLs that the converter cannot collapse further without widening blocks (out of scope per issue's "smallest local fixes" carve-out).

### Style of rewrite

**"Regenerate then ship"** — even slimmer than Postkarte. Postkarte needed 2 PageBackground hand-substitutions + 1 layer kwarg + 1 ci-defaults hoist. Plakat needs **zero hand edits to the regenerated build.py** — the converter alone meets all numeric ACs. The only code changes outside `templates/plakat-a1-hochformat/build.py` are:
1. `tools/sla_diff.py` — extend allowlist for brand colors (~5 LOC + tests)
2. `tools/sla_lib/tests/test_sla_to_dsl.py::PlakatRoundTrip` — update allowlist filter (~5 LOC)

This is a **3-commit migration** at the code level: (1) flag extension + tests, (2) regenerate build.py + rebuild SLA, (3) test allowlist update + render-gallery + EXECUTION.md.

### Comparison to Postkarte (#6) and outlook for Zeitung (#8)

| Migration | Current LOC | Regen LOC | Block subs | Hand edits | New blockers introduced |
|---|---:|---:|---:|---:|---|
| Postkarte (#6) | 437 | 383 | 2× PageBackground | 2 (substitution + explicit Hintergrund layer) | sla_diff `--allow-brand-extras` for extra-style/extra-layer; CompressMethod hoist; PageBackground.for_page() widening |
| **Plakat (#7) THIS ISSUE** | 235 | **198** | **0** | **0** (regen alone meets ACs) | sla_diff `--allow-brand-extras` extension for extra-color (Hellgrün/Magenta) |
| Zeitung (#8) | unknown | unknown | likely 12× PageNumber + 84× ColumnTextStory + 1 Impressum + 1 PageBackground | substantial — biggest payoff | likely none (all 7 brand colors present per measurement) |

Plakat is the **shortest** of the three migrations and the **only one** that surfaces no new block-substitution wins. Its value is proving the migration pattern works on a template the blocks don't fit at all — and surfacing the extra-color allowlist gap that Zeitung might not have caught.

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` file in the worktree root (`ls /root/workspace/.worktrees/rewrite-plakat-onto-brand-blocks/CLAUDE.md` → not found). No `.claude/skills/` directory either. The repo carries no project-level invariants beyond what ISSUE.md and the existing tests encode. **No additional constraints to honor.**

## Sources

### HIGH confidence (measured directly)
- `templates/plakat-a1-hochformat/build.py` — current 235 LOC, all 9 frame definitions read line-by-line.
- `tools/sla_to_dsl.py --help` and `tools/sla_to_dsl.py templates/plakat-a1-hochformat/template.sla /tmp/plakat-regenerated.py --template-id plakat-a1-hochformat --assets-dir /tmp/plakat-research-assets/` — converter run live; produced 198-LOC build.py.
- Live built SLA from regen: `python3 build.py` produced 228054-byte `template.sla` (smoke test passed).
- `python3 tools/sla_diff.py --left plakat-a1-hochformat-original.sla --right /tmp/plakat-test-build/template.sla --strict` — exit code 1 with 13 warnings (3 extra-layer, 8 extra-style, 2 extra-color).
- `python3 tools/sla_diff.py ... --strict --allow-brand-extras` — exit code 1 with 2 unfiltered extra-color warnings (Hellgrün, Magenta). **This is the proof of R1.**
- `python3 tools/visual_diff.py /tmp/plakat-test-build/template.sla --baseline templates/plakat-a1-hochformat/baseline.pdf --tolerance templates/plakat-a1-hochformat/diff.yml --dpi 96 --out /tmp/plakat-vd/` — exit 0.
- `tools/sla_lib/builder/blocks.py` — all 5 block APIs read; modern Impressum at lines 89-124 confirmed to lack rotation_deg and prefix-Run support.
- `tools/sla_lib/builder/brand.py` and `shared/ci.yml` — Brand.gruene_noe() injects 7 brand colors (Black, White, Registration, Dunkelgrün, Hellgrün, Gelb, Magenta).
- `tools/sla_diff.py:985-996` — `_compare_palette` is called with `SEVERITY_WARNING` for COLOR (line 1100), confirming `extra-color` is warning-severity (not info).
- `tools/sla_diff.py:1183-1194` — `--allow-brand-extras` filter predicate verified to exclude only `extra-style` and `extra-layer`.
- `tools/sla_lib/tests/test_sla_to_dsl.py:125-131` — `PlakatRoundTrip.test_diff_against_original_clean` confirmed to assert `summary[WARNING] == 0`.
- `tools/sla_lib/tests/test_sla_to_dsl.py:62-77` — Postkarte's allowlist fix pattern (filter extra-style + extra-layer) verified for replication.
- `bin/validate:60-69` — already passes `--allow-brand-extras` to sla_diff (from Postkarte #6 work).
- `python3 -c "import xml.etree.ElementTree as ET; t=ET.parse('plakat-a1-hochformat-original.sla'); ..."` — confirmed PTYPE counts: 6 TextFrames + 3 ImageFrames + 0 Polygons.
- `grep -E "<COLOR " plakat-a1-hochformat-original.sla` — confirmed 5 colors, no Hellgrün, no Magenta.
- `python3 -m pytest tools/sla_lib/tests/test_sla_to_dsl.py::PlakatRoundTrip -x -v` — 2 tests passing on current main.
- Postkarte EXECUTION.md (`/root/workspace/.worktrees/rewrite-postkarte-onto-brand-blocks/.issues/rewrite-postkarte-onto-brand-blocks/EXECUTION.md`) — confirmed Postkarte fix pattern, 369 final LOC, 6 commits, P2 follow-ups list.
- `git log --oneline -20` — confirmed Postkarte work (eff5ba7..1ebe8ef) is landed on this branch.

### MEDIUM confidence
- `extra_pdf_attrs=11` is the exact criterion target — was 12 before Postkarte's `CompressMethod` hoist; verified by inspection of `shared/ci-defaults.yml` post-hoist comment.

### LOW confidence (none load-bearing)
- Whether Zeitung (#8) will hit the same `extra-color` blocker — measured presence of all 7 brand colors in `gruene-zeitung-vorlage-original.sla` strongly suggests no, but not yet proven by Zeitung-side regen.

## Metadata

- **Sub-agents used:** None — this issue's research was done end-to-end in the orchestrator agent. Reasons: (a) codebase analysis required reading large inline-image base64 lines that would have busted sub-agent token budgets; (b) ecosystem analysis is pure stdlib + project-internal (no external libraries); (c) pitfalls analysis is internal (sla_diff allowlist semantics, stale-preview gate, extra-color severity); (d) the Postkarte EXECUTION.md provided 95% of the migration pattern, so the marginal value of multi-agent fan-out was low.
- **Research date:** 2026-05-07.
- **Confidence breakdown:**
  - Codebase audit: HIGH (every line of build.py + every page item categorized; PTYPE counts confirmed via XML parse).
  - Block fitness: HIGH (verified 0 of 5 blocks apply; both Impressum gaps measured against modern block dataclass).
  - LOC arithmetic: HIGH (regenerated live, 198 LOC measured).
  - Validate-strict regression: HIGH (reproduced live; 2 unfiltered extra-color warnings confirmed).
  - PlakatRoundTrip test failure prediction: HIGH (current passing, Brand emission would inject 13 warnings none of which are filtered by current test allowlist).
  - LOC ≤180 feasibility: HIGH that it is NOT achievable; recommendation is to drop the gate per user direction.
- **Raw research files:** None — no sub-agents, all findings are in this RESEARCH.md.
- **5-bullet summary** (for orchestrator return):
  1. Regenerated LOC: **198** (down from 235; -37). All 4 numeric ACs (LOC informational, doc-attrs ≤23, pdf-attrs ≤11, Brand uptake) met by raw regen with zero hand edits.
  2. Block substitutions identified: **0** — Plakat has 0 Polygons (no PageBackground fit), 0 chains, 0 pgno frames, and 1 Impressum frame with two API gaps (rotation_deg + Bold-prefix Run, the latter same as Postkarte P2 #1).
  3. DSL gaps flagged: **1 hard blocker** (`--allow-brand-extras` doesn't cover `extra-color` — Plakat's missing 2 brand colors trigger 2 unfiltered warnings) + **1 P2** (Impressum block needs `rotation_deg=` widening on top of Postkarte's already-filed prefix-Run gap).
  4. Visual-diff readiness: **CLEAN** — visual_diff against baseline.pdf exits 0 on the regenerated SLA (live-tested at /tmp build).
  5. Recommended PLAN.md task count: **5 tasks** — (1) extend `--allow-brand-extras` to cover `extra-color`, (2) regenerate build.py + rebuild SLA, (3) update PlakatRoundTrip test allowlist, (4) rebuild gallery + full validation, (5) acceptance + EXECUTION.md.
