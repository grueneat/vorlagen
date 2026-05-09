---
id: '14'
title: 'Constraint DSL: page-bounds, aligned_below, SpreadImage utility'
status: done
priority: high
labels:
- dsl
- architecture
- test
source: github
source_id: 29
source_url: https://github.com/GrueneAT/vorlagen/issues/29
---

# Foundational: extend constraint DSL with page-bounds, vertical-alignment, and SpreadImage utility

## Why

The current constraint DSL (`tools/sla_lib/builder/constraints.py`) catches *intra-page* alignment drift (`same_y`, `mirrored_x`, `inside`, `equal_gap`, …) but cannot catch the most damaging class of layout bug we have: **frames whose bbox crosses a page boundary**. Direct evidence in `templates/zeitung-a4-grun/build.py` (built from the upstream Scribus original — round-trip-faithful):

- Print page 10 has `ImageFrame "P9 Spread"` placed at `x=210 mm, w=210 mm` on a 210-mm-wide page → the frame is **entirely past the right edge** of its own page (≥207 mm overflow). It is intended as the spread image for pages 10/11 but is attached to the wrong page in the SLA.
- Print page 12 has an unnamed `ImageFrame` at `x=210, y=−0.18, w=210.8, h=297.2` → an **entire A4 image attached to the wrong page**.

`structural_check --all` reports zero failures because no rule today inspects per-frame bbox vs. page+bleed. The fixes belong in code (per Brief §5: *fixes encoded as constraints, not as one-off render diffs*) so that future drift in any template surfaces mechanically.

This issue lays the foundation; per-template fixes (#16 Zeitung overflow, #17–#21 layout V1 implementations) depend on it.

## Scope

1. **`inside_page` constraint** in `tools/sla_lib/builder/constraints.py`:
   - Each frame's axis-aligned bbox (after `rotation_deg`) must be inside its own page's `[−bleed, w+bleed] × [−bleed, h+bleed]`.
   - Tolerance: 0.5 mm (matches existing constraint default).
   - Severity: `error` for overflows > 0.5 mm; `warning` only for ≤ 0.5 mm bleed-edge nudges (very common in Scribus exports).
2. **Wire `inside_page` into the global brand-constraints sweep** (`tools/sla_lib/builder/brand_constraints.py`) so it runs on every template under `--all` without requiring per-template `CONSTRAINTS=[…]` opt-in. Templates may add a single `meta.yml::brand_overrides` entry to skip with reason (existing override mechanism).
3. **`aligned_below(image_anname, text_anname, gap_mm, tolerance_mm=0.5)` constraint**:
   - `image.y_mm == text.y_mm + text.h_mm + gap_mm` (within tolerance) **and** `image.x_mm == text.x_mm` (within tolerance) — the standard "image hangs from the text above on the same left axis" pattern.
   - Lets templates declare e.g. `aligned_below("P5 Hero", "P5 Body Column 1", gap_mm=4)` to lock the relationship that today drifts silently.
4. **`SpreadImage` block utility** in `tools/sla_lib/builder/blocks.py`:
   - Inputs: left page, right page, image src, full-spread `w_mm × h_mm`, optional gutter offset.
   - Emits **two `ImageFrame`s**, one per page, both anchored to their respective page-local origins, sharing a single image src split via `local_offset_mm` so the rendered halves form one continuous picture across the spread.
   - Both halves get matched `anname` like `"<base> · left"` and `"<base> · right"`; `inside_page` then automatically catches misuse.
   - Replaces the today-broken pattern of putting one image at `x=210, w=210` on the left page (which `inside_page` will now flag as an error).
5. **Tests**:
   - Unit tests for `inside_page` (pass / overflow on each side / rotation handling) in `tools/sla_lib/tests/test_constraints_inside_page.py`.
   - Unit test for `aligned_below` (pass / x drift / y drift).
   - Unit test for `SpreadImage` builder (emits two frames, both `inside_page` clean, image offsets are mirror-pair).
   - Integration: snapshot of `python3 -m sla_lib.builder.structural_check --all` in `--json` mode showing exactly the *expected* set of `inside_page` failures (currently 2: `P9 Spread`, page-12 unnamed image — both will move into `meta.yml::brand_overrides` with reason in #16 and stay listed until that issue lands).
6. **Docs**:
   - Add `inside_page`, `aligned_below`, `SpreadImage` to `templates/_specs/SCHEMA.md` §6 (Constraint catalogue) and `shared/brand/SPEC-WRITING-GUIDE.md` §4 (Constraint examples).
   - Document the `SpreadImage` migration recipe (one frame at `x=page_w` → `SpreadImage(left, right, src, w=2×page_w)`).

## Acceptance Criteria

- [ ] `inside_page` exists as a public factory in `tools/sla_lib/builder/constraints.py` and has unit tests covering the 5 directions × rotation cases.
- [ ] `inside_page` runs on every template under `python3 -m sla_lib.builder.structural_check --all` without per-template opt-in; warnings vs. errors split by 0.5 mm tolerance.
- [ ] Running `--all` today reports **exactly two** `inside_page` errors (`P9 Spread` on Zeitung print page 10, unnamed full-page image on Zeitung print page 12). Any third or extra report is investigated and added to this issue's findings before merge.
- [ ] `aligned_below` exists, tested, documented.
- [ ] `SpreadImage` builder exists, emits two `inside_page`-clean frames, has tests, has a migration recipe in the spec-writing guide.
- [ ] `meta.yml::brand_overrides` mechanism still works for skipping `inside_page` per template (verified by adding then removing a fake skip on one template).
- [ ] CI: `pages.yml` already wires `structural_check --all`; this issue must keep `--all` green by *not* introducing the Zeitung errors here. The Zeitung errors will be deliberately accepted as `brand_overrides` entries here with comment `"see issue #16"` and removed by #16 once the fix lands.

## Out of scope

- Actually fixing the Zeitung spread (that's #16).
- Implementing V1 layouts for the five new templates (#17–#21).
- Rendering / pixel-diff: this issue is *constraint-system only*, no .sla regen, no PNG comparison.

## Dependencies

None — this is the foundation. Blocks: #16, #17, #18, #19, #20, #21.

## Labels

design-system, constraint-dsl, infrastructure
