# Research: PITFALLS for issue #16

**Domain:** Zeitung-A4 frame-overflow fixes; SpreadImage migration; brand_overrides removal; CI ordering.
**Date:** 2026-05-09
**Confidence:** HIGH (all claims verified against source files in this worktree).

---

## Executive summary

This issue is mostly a textual edit in `templates/zeitung-a4-grun/build.py`, but it sits on a chain of CI gates that will all go red simultaneously the moment build.py changes:

1. `tools/sla_diff.py --strict` (against upstream `gruene-zeitung-vorlage-original.sla`) — has **no per-frame ignore** mechanism. Any geometry move surfaces as a critical / warning issue.
2. `bin/check-stale-previews` — recomputes `sha256(template.sla)` and compares against `meta.yml::previews_for_sla`. Build.py edits invalidate this hash.
3. `tools/sla_lib.builder.structural_check --all` — runs `brand:inside_page` (added by #14). Removing the meta.yml override is the explicit goal of this issue, but it surfaces a 3rd overflow (`u2950`) that was silenced by the same override.
4. The `INJECT_MAP` and `CONSTRAINTS` list inside build.py *itself* both reference the anname `"P9 Spread"`. Renaming the frame breaks gallery preview injection AND structural-check anchor resolution.
5. `library.inject_into_frame` is *incompatible by design* with `SpreadImage`'s left+right-half geometry — SpreadImage assumes a source image 2× page-width wide; inject_into_frame crops to one-frame-width.

These are not show-stoppers, but every one of them must be addressed in the SAME PR or the PR will fail CI mid-review. The atomic-PR requirement called out in the prompt is real and load-bearing.

---

## P-1 (CRITICAL) — `tools/sla_diff.py` has NO per-frame ignore mechanism

**What goes wrong:** The moment we move/replace either of the two right-edge spread frames, `sla_diff` flags the changes against the upstream original SLA. CI invokes it with `--strict --allow-brand-extras` (see `.github/workflows/pages.yml` line ~106 + `tools/render_pipeline.py:392-402`). `--strict` causes warning-level findings to also exit 1.

**Source of truth:** `tools/sla_diff.py:1188-1245` (CLI). The only filtering mechanism is `--allow-brand-extras` which gates exactly four codes: `extra-style`, `extra-layer`, `extra-color` (limited to 7 brand color names hardcoded at line 49-52), and `missing-layer` (limited to 1 legacy layer name `Ebene 1` at line 57-58). Geometry deltas on PAGEOBJECTs (`position-drift`, `size-drift`, `extra-pageobject`, `missing-pageobject`, `page-item-count-mismatch`) are NOT filterable.

**What sla_diff will report after the edits:**

For the P9-Spread → `SpreadImage` migration (option A):
- `extra-pageobject` (severity=critical) — a NEW frame appears (we go from 1 frame to 2 frames on the spread).
- `missing-pageobject` OR `position-drift` (severity=critical/warning) — the original right-edge-overflow frame is gone or moved.
- `page-item-count-mismatch` (severity=critical) on the affected page count.
- Multiple `position-drift` / `size-drift` on the new SpreadImage frames.

For the page-12 unnamed frame move:
- `position-drift` (warning, > 0.5pt) on the moved frame (XPOS goes from 595pt → 0pt).
- Possibly `page-item-count-mismatch` if the move crosses to a different OwnPage value.

For the 0.8 mm width trims (lines 1955, 2064, 2283):
- `size-drift` (warning, since 0.8mm = 2.27pt > 0.5pt SIZE_TOLERANCE_PT at line 66).

**ALL of the above will fail CI.** `sla_diff.py` does not consult `templates/<id>/diff.yml` at all (verified — `grep "diff.yml" tools/sla_diff.py` returns 0 hits). `diff.yml` is **only** the per-pixel raster tolerance for `tools/visual_diff.py`, which CI does not invoke.

**Resolution options:**
1. **Drop `--strict` from `_run_sla_diff_strict`** (`tools/render_pipeline.py:397`) — the safest, smallest delta; warnings stop being fatal but `critical`-level issues still fail. The `extra-pageobject` from SpreadImage migration is *critical*, so this alone is insufficient.
2. **Add a `--ignore-pageobject-by-anname` flag to `tools/sla_diff.py`** — surgical, future-proof. Pass `--ignore-pageobject-by-anname "P9 Spread"`. Schema parallels `--allow-brand-extras`.
3. **Document the divergence in commit body + `templates/zeitung-a4-grun/README.md`**, but accept that CI will go red; merge requires admin override. ANTI-PATTERN — defeats the purpose of the gate.
4. **Stop running sla_diff on zeitung in CI** — too aggressive; loses the round-trip protection for unrelated parts of the SLA.

**Recommendation for the planner:** **Option 2.** Add a CLI flag to `sla_diff.py` (`--ignore-pageobject-by-anname` accepts repeated values), filter at report-generation time after issue creation. Minimal: ~25 LoC + 2 unit tests in `tools/sla_lib/tests/test_sla_diff.py`. Then in `tools/render_pipeline.py:_run_sla_diff_strict`, read the new `meta.yml` field `sla_diff_overrides.ignore_pageobjects: ["P9 Spread", ...]` and pass-through. Then `meta.yml` documents *exactly* which frames are intentionally diverged, paralleling the `brand_overrides` schema.

**Acceptance test:** Without the new flag, `python3 tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right templates/zeitung-a4-grun/template.sla --strict --allow-brand-extras` exits 0 today. After build.py edits (no flag added), exits 1. After flag added + meta.yml entry, exits 0 again.

**Counter-argument the planner should weigh:** ISSUE.md §"Acceptance Criteria" explicitly says `tools/sla_diff.py` "produces a diff limited to: (a) the two moved frames, (b) the 0.8 mm width corrections — with each documented in the commit body and `diff.yml`." This phrasing reads as **"a non-empty diff is acceptable"**, not "we add an ignore mechanism". The planner has to decide: does CI need to stay green (option 2), or is a documented red diff acceptable (option 3)? The conservative read of the prompt is that CI must stay green — the prompt explicitly says "All changes must land in one PR or `--all` will go red mid-PR" (focus area #6).

---

## P-2 (HIGH) — `previews_for_sla` SHA must be updated; gallery-preview pipeline needs to re-run

**What goes wrong:** `meta.yml::previews_for_sla` (zeitung-a4-grun/meta.yml:19) records the SHA-256 of the *built* `template.sla` bytes (verified: 9e914ec... matches `sha256sum templates/zeitung-a4-grun/template.sla`). `bin/check-stale-previews` (`tools/check_stale_previews.py:124`) is invoked in CI (`pages.yml` line ~104) and exits 1 on hash mismatch. Build.py edits change the bytes; the hash must be regenerated.

**Resolution:** The executor must run `bin/render-gallery` locally after editing build.py. `tools/render_pipeline.py:494-495` invokes `_update_meta_hash()` to rewrite the `previews_for_sla` field. The executor must also stage the regenerated `template.sla`, `template-preview.sla`, `preview.pdf`, all `page-NN.png`, AND the `site/public/templates/zeitung-a4-grun/*` mirrors (`tools/render_pipeline.py:496` calls `_mirror_to_site_public`).

**Pitfall:** The render pipeline depends on Scribus 1.6.5 being installed (verified: `/usr/bin/scribus` exists in this worktree) AND on `xvfb` for headless export. In a Docker dev container, `xvfb-run -a scribus ...` is the invocation. If Scribus isn't reachable, `bin/render-gallery` fails noisily.

**Pitfall:** The pipeline ALSO runs `_run_sla_diff_strict` (`render_pipeline.py:484`) which kills the run if sla_diff is non-zero. So P-1 is a HARD blocker for `bin/render-gallery` AS WELL — without resolving P-1, the executor cannot even regenerate the SHA.

**Resolution chain:** Resolve P-1 first → run `bin/render-gallery` → `template.sla`, hash, mirror, PNGs all update → commit.

**Pitfall — `template-preview.sla` will likely fail to inject `P9 Spread`:** If we rename to `"P9 Spread · left"` / `"P9 Spread · right"`, the `INJECT_MAP` lookup at `templates/zeitung-a4-grun/build.py:2511` returns no match for those new annames. The library photo `themen_klimaschutz_solar` no longer lands on the spread frame. The gallery preview PNGs for pages 10/11 lose the photo. See P-5 for the planner's required INJECT_MAP fix.

**Visual_diff in CI:** Verified: `pages.yml` does NOT run `tools/visual_diff.py` (it's only invoked by `tools/render_pipeline.py` locally). So the ~150-dpi raster compare against `baseline.pdf` is not a CI gate. However, `bin/render-gallery` runs visual_diff by default unless `--skip-visual-diff` is passed (`tools/render_pipeline.py:489-491`); after our edits the preview will visually differ from baseline.pdf, and the local pipeline will fail. The executor must EITHER re-baseline `baseline.pdf` (per `docs/render-fidelity.md` "Rebaselining a template's baseline.pdf") OR run with `--skip-visual-diff` (and the human PR reviewer rebaselines manually, per ISSUE.md acceptance criterion 4 which already says PNGs are reviewed by the human).

**Recommendation for the planner:** Run `bin/render-gallery --skip-visual-diff` to update template.sla + previews_for_sla + page-NN.png, BUT explicitly leave `baseline.pdf` untouched. The PR reviewer then runs `bin/render-gallery` (with visual_diff) to validate the new pages match a fresh Scribus export — and re-stages `baseline.pdf` if accepted.

---

## P-3 (HIGH) — `brand_overrides` is rule-level only; removing it surfaces `u2950`

**Verified:** `tools/sla_lib/builder/meta_schema.py:23-40` — the `brand_overrides` JSON-Schema accepts `[{id, reason}]` only. There is NO per-frame `targets` field. The override silences the *entire rule* across all frames.

**Verified by execution:** With the override removed, the inside_page rule reports 3 errors today (run via direct `_InsidePageRule().check()` instantiation, bypassing the override):
```
[error] frame 'u2950' bbox (-4.08, 155.57)-(216.41, 304.17) ... worst overshoot 4.17mm
[error] frame 'P9 Spread' bbox (210.00, 0.00)-(420.00, 126.14) ... worst overshoot 207.00mm
[error] frame '<unnamed ImageFrame>' bbox (210.00, -0.18)-(420.80, 297.00) ... worst overshoot 207.80mm
```

After this issue's fix lands (assume both spread frames go away), `u2950` (the rotated cover-page Dunkelgrün polygon at `templates/zeitung-a4-grun/build.py:246-256`) remains. It's a 148.6×220.5 mm polygon at (216.41, 155.57) rotated 90° CCW; its rotation-aware bbox extends ~4.17 mm below page-bottom-bleed. That single error fails `structural_check --all` (exit 1).

**Decision tree (the prompt's focus area #7), enumerated for the planner:**

- **Option A — Fix u2950 in this issue.** Out of scope per ISSUE.md "fix the two named frames" and "Out of scope: Layout redesign of Zeitung pages". REJECT. The cover-page polygon is a real layout element (full-bleed Dunkelgrün accent — visible in `templates/zeitung-a4-grun/page-01.png`). Touching its geometry without visual validation risks breaking the cover. This is a separate visual-design call.

- **Option B — File u2950 as follow-up issue and add a per-frame override.** **Not possible with current schema.** `brand_overrides` is rule-level (verified above). Sub-options:
  - **B.1** — Extend `meta_schema.py` to accept `{id, reason, targets: [anname...]}` with new optional `targets` field. Then `_InsidePageRule.check()` skips violations whose `Violation.targets` overlap with the override's `targets`. Added complexity: ~20 LoC + 3 tests. Future-proof and clean.
  - **B.2** — Keep the rule-level override but with a NEW reason text mentioning the new follow-up issue ID. Pragmatic but defeats the spirit of #16 (we're literally removing the rule-level override).

- **Option C — Carry the rule-level override forward verbatim.** Same as B.2 but without filing a follow-up. Worst option — silently re-silences a real bug.

**Recommendation for the planner:** **Option B.1** if the schema extension fits the scope. Otherwise **Option B.2** with a tightly-scoped follow-up issue filed before this one merges. **Pre-emptively REJECT Option A and Option C.**

**Schema-extension cost (Option B.1):** Roughly ~30 LoC across `meta_schema.py` (new `targets` array in schema), `structural_check.py` (apply `targets` filter when emitting brand_issues from the rule), tests in `test_meta_schema.py` and `test_structural_check.py` (or wherever the override flow is tested). Cheap.

**Open question for the planner:** Does scope of #16 include the meta_schema extension? If yes, this issue grows by ~1-2 hours. If no, **B.2** is the fallback — a new follow-up issue filed against zeitung covering u2950, and the rule-level override stays with reason `"u2950 cover polygon overflow tracked in #N (see EXECUTION.md '#14 Discovered Issues')"`.

---

## P-4 (HIGH) — `test_zeitung_overflow.py` expects exactly 3 errors; must be updated atomically

**File:** `tools/sla_lib/tests/test_zeitung_overflow.py` (114 lines).

**Current assertion** (line 74-81):
```python
self.assertEqual(
    len(errors), 3,
    msg=("expected exactly 3 inside_page errors today (P9 Spread, "
         "unnamed page-12 image, rotated u2950 polygon) ...
```

**After this issue lands:** errors must be 1 (just `u2950`) IF Option B.2 / C from P-3 (rule-level override with u2950 reason). Errors must be 0 IF Option A (also fix u2950, which we recommend AGAINST) OR if Option B.1 (new per-frame override of u2950).

**Pitfall:** The test docstring (lines 1-27) and per-error assertion at line 84 (`self.assertIn("P9 Spread", targets)`) and line 86-91 (asserts unnamed-ImageFrame error) will both fail after fix. The planner must ALSO update the docstring + drop the now-incorrect per-error assertions.

**Pitfall:** The second test (line 96-109) `test_inside_page_passes_with_override` asserts that `inside_page` is in `skipped_brand_rules`. That test will FAIL after we remove the override — because the rule will no longer be skipped. The whole test must either be deleted or restructured to test the (single) remaining `u2950` violation.

**Recommendation for the planner:** **Delete `test_inside_page_passes_with_override` entirely**, since after this fix there is no rule-level override to test. Replace `test_inside_page_finds_the_known_overflows_without_override` with `test_inside_page_zero_errors_after_fix` that runs the rule via the production pipeline (`structural_check.check_template`) and asserts zero errors. If Option B.2 is chosen, retain a guard test that asserts `u2950` is still the only violation (so we don't regress).

---

## P-5 (CRITICAL) — `INJECT_MAP` and `CONSTRAINTS` reference `"P9 Spread"`

**Verified:**
- `INJECT_MAP` at `templates/zeitung-a4-grun/build.py:2497-2508`: key `"P9 Spread": ("themen_klimaschutz_solar", 210, 126.1)` (line 2504).
- `CONSTRAINTS` at `templates/zeitung-a4-grun/build.py:2542-2556`: `same_size("P9 Spread", name="p9_spread_anchor")` (line 2555).

**`SpreadImage.emit()` anname pattern** (`tools/sla_lib/builder/blocks.py:722, 731`): when `base_anname="P9 Spread"`, the two emitted frames get annames `"P9 Spread · left"` and `"P9 Spread · right"` (middle-dot separator).

**What breaks:**

1. **Gallery preview injection silently drops the photo:** `build_preview()` iterates frames and looks up `frame.anname in INJECT_MAP` (line 2511). Neither new anname matches `"P9 Spread"` → the library photo is never injected → preview pages 10/11 render as empty rectangles. Visual_diff (local-only) and the human reviewer (per acceptance criterion 4) catch this, but the planner should pre-emptively fix.

2. **Structural check warns "missing anname":** `same_size("P9 Spread", ...)` resolves to a missing-anname. Per `tools/sla_lib/builder/structural_check.py:168-174`, this surfaces as a `warning`-level `CheckIssue` (severity="warning"), NOT an error. CI's structural-check exit gate is errors-only (`structural_check.py:67-69`), so this is non-fatal — but it pollutes the report.

**Pitfall (subtle):** The `_SameSizeConstraint` with a single target is functionally a presence-witness only (`constraints.py:142-149` — single target means no pairwise comparison; orphan warning is the only failure mode). The replacement should be a presence-witness for BOTH halves: `same_size("P9 Spread · left", "P9 Spread · right")` would also assert size equivalence between the two halves (both 210×126.14 by construction), which is a useful regression on the SpreadImage emit.

**Recommendation for the planner:**
- Update `INJECT_MAP`: replace key `"P9 Spread"` with `"P9 Spread · left"` AND `"P9 Spread · right"`, both pointing at the same library entry. This requires P-9 (see below) — `inject_into_frame` cannot natively handle spread halves.
- Update `CONSTRAINTS`: replace `same_size("P9 Spread", ...)` with `same_size("P9 Spread · left", "P9 Spread · right", name="p9_spread_anchor_pair")` — gets us a real cross-half assertion AND keeps the anchor witness.

---

## P-6 (HIGH, load-bearing) — `local_offset_mm` sign for the right half

**Verified:** `tools/sla_lib/builder/blocks.py:729` — `local_offset_mm=(-self.page_w_mm, 0.0)` (NEGATIVE x). The docstring at `blocks.py:690-692` and the test `test_right_half_local_offset_is_negative_x` (`tools/sla_lib/tests/test_spread_image.py:38-42`) both encode this contract.

**Consequence if planner gets it wrong** (either by hand-rolling vs. using `SpreadImage.emit()`, or by passing `page_w_mm` via the wrong code path): the right half displays the LEFT half of the source image — same content as the left frame, no spread effect. The frames pass `inside_page` (each at x=0 on its own page), but the visual is wrong. The PR reviewer's manual page-10/11 PDF check (acceptance criterion 4) will catch this — but the planner should make sure the migration *uses* `SpreadImage.place(left_page, right_page)` and not a hand-rolled pair of `ImageFrame()` calls.

**Mandate for the planner:** Specify the migration call as `SpreadImage(image="", page_w_mm=210.0, page_h_mm=297.0, h_mm=126.13945871829057, base_anname="P9 Spread").place(page9, page10)`. Do NOT allow the executor to hand-roll the two ImageFrame calls. The block exists *because* the geometry is fragile.

**Open issue: y_mm.** The current `P9 Spread` frame has `y_mm=0`. SpreadImage default is `y_mm=0.0`. Match. The h_mm extracted exactly from line 1806 — preserve to full precision (the trailing `...871829057`) so the round-trip diff is byte-stable on dimensions. Don't round it.

---

## P-7 (MEDIUM) — `scale_type=0` is hard-pinned; visual delta requires PR reviewer

**Verified:** `tools/sla_lib/builder/blocks.py:711` — `scale_type: int = 0`. Hard-pinned to 0 (Scribus "manual scale" / fit-to-frame manual). The current `P9 Spread` frame at `templates/zeitung-a4-grun/build.py:1802-1811` does NOT pass `scale_type=` — so it uses `ImageFrame`'s default `scale_type = 1` (`tools/sla_lib/builder/primitives.py:772` — `scale_type: int = 1`).

**SLA emission contract** (`primitives.py:810`): `"SCALETYPE": str(self.scale_type)`. Today: SCALETYPE="1". After SpreadImage migration: SCALETYPE="0".

**Why the pin matters** (`blocks.py:695-697`): "the default 1 (auto-fit) breaks the spread because each half auto-fits independently." Visual consequence in Scribus: with SCALETYPE=1, each half scales the full image to fit its 210×126 frame independently — both halves show the full image, no spread.

**Pitfall:** sla_diff considers `SCALETYPE` a default-equivalent attribute (`tools/sla_diff.py:81` — `"SCALETYPE": "1"` in DEFAULT_EQUIVALENTS) — meaning SCALETYPE="1" is dropped before compare, so a SCALETYPE="1" → SCALETYPE="0" change emits as `extra-attr`-style report or position-drift-style change. Verified the strip happens at `sla_diff.py:313-342`.

**Acceptance dependency:** The user's prompt explicitly forbids visual diff by Claude (focus area #11). The PR reviewer must visually verify pages 10-11 (and 12-13 if option-A migration is chosen) render correctly. ISSUE.md's acceptance criterion 4 already locks this in — the human reviews `page-10.png`, `page-11.png`, etc. after `bin/render-gallery` regenerates them.

---

## P-8 (HIGH) — Page-12 unnamed frame: spread vs. wrong-page is empirically verifiable, but with caveats

**Verified frame** at `templates/zeitung-a4-grun/build.py:2061-2071`: `page11.add(ImageFrame(x_mm=210, y_mm=-0.18, w_mm=210.799, h_mm=297.18, image='', fill='Dunkelgrün', local_offset_mm=(0.33, -0.33)))`.

**Critical observation:** This frame has `image=''` AND `fill='Dunkelgrün'`. It is a green-rectangle decorative fill, NOT a content image. There is no library injection anchor for it (no anname, not in INJECT_MAP).

**`pdfimages -list templates/zeitung-a4-grun/preview.pdf` output (verified):**
- Print page 12 has image objects 21 (2480×984, ~210×83mm) and others.
- Print page 13 has image object 22 (2480×984, also ~210×83mm).

**Interpretation:** The pdfimages-listed photos on print pages 12-13 do NOT come from the page-12 unnamed frame — they come from `P11 Bottom` and `P13 Hero` (both real injection anchors). The page-12 unnamed frame is a green decorative rectangle that, due to its `x=210, w=210.8` geometry, currently renders ON print page 13 (the right half of a facing-page spread, physical-canvas position).

**Pitfall:** ISSUE.md says "Belongs on page 13" — but "page 13" in ISSUE.md is in the print-page numbering (13 = 1-indexed = 0-indexed `page12`). The build.py 0-indexed name for print page 13 is `page12`. The fix per ISSUE.md is: move from `page11.add(...)` to `page12.add(ImageFrame(x_mm=0, y_mm=-0.2, w_mm=210.8, h_mm=297.2, ...fill='Dunkelgrün'...))`. **DO NOT** wrap this in `SpreadImage` — it's a single decorative rectangle, not a continuous spread image. SpreadImage requires `image=` to be non-empty (and the inject machinery to know about the SpreadImage halves).

**Wrong-page interpretation IS the right call here**, NOT spread. The PDF inspection per ISSUE.md was meant for the planner to confirm; the answer is: this is a green rectangle, no image content, simple page-attribution fix.

**Pitfall:** When moved to `page12` (print page 13), the frame at `x=0, y=-0.18, w=210.799, h=297.18` STILL has `w=210.799` (0.799 mm too wide). The `inside_page` rule (`brand_constraints.py:469-477`):
- `over_r = (0 + 210.799) - (210 + 3) = -2.2` → no overflow, frame is within bleed envelope.
- `over_t = (-3) - (-0.18) = -2.82` → no overflow.
- `over_b = (-0.18 + 297.18) - (210 + 3 ... no that's pw_mm) → over_b = 297.0 - 300 = -3.0` → no overflow.

So the move to page12 ALONE makes inside_page pass without trimming. The 0.8 mm width doesn't cause inside_page to fail (it's within the bleed envelope). **The "trim to w=210" recommendation in ISSUE.md is cosmetic, not correctness-driven** — and trimming triggers `size-drift` warnings in sla_diff (~2.27pt > 0.5pt SIZE_TOLERANCE_PT).

**Recommendation for the planner:** **Skip the 0.8 mm trim** for this frame — it doesn't fix any rule violation and just adds noise to the sla_diff report. ISSUE.md §"Open questions / risks" itself softens this: *"If the round-trip diff complains, revert these two tiny fixes — we keep the core P9/P11 fix."* Pre-emptively follow that revert path.

**Pitfall on `local_offset_mm`:** When moving to page12 at `x_mm=0`, the existing `local_offset_mm=(0.33, -0.33)` becomes meaningless (it was a manual nudge to compensate for the 210mm x-overflow). Planner should specify `local_offset_mm=(0.0, 0.0)` for the moved frame, or omit (default).

---

## P-9 (HIGH) — `library.inject_into_frame` is incompatible with `SpreadImage` halves

**Verified:** `tools/sla_lib/builder/library.py:485-500`. The helper:
1. Calls `crop_for_frame(img, target_w_mm, target_h_mm, ...)` which crops the source image to the SINGLE frame's aspect.
2. Sets `frame.scale_type = 0` (overwrites whatever was there).
3. Writes `frame.inline_image_data` and `frame.inline_image_ext`.

**Why this breaks for SpreadImage halves:** SpreadImage's design uses a source image of width `2 × page_w_mm`. The right half uses `local_offset_mm=(-page_w_mm, 0)` to slide the image so the right half of the image shows. If `inject_into_frame(left_half, img, target_w_mm=210, target_h_mm=126)` is called, `crop_for_frame` produces a 210x126 crop — the source image is now ONE-frame-width, not TWO-frame-width. The right half's `local_offset_mm=(-210, 0)` then slides the (already-cropped) ONE-frame-width image off the visible region — the right half renders empty / black / shows inappropriate edge content.

**Verified:** `inject_into_frame` does NOT touch `local_offset_mm` (no assignment in `library.py:485-500`). So the SpreadImage's original `local_offset_mm=(0,0)` left and `(-210,0)` right are preserved AFTER inject — but the source image is cropped wrong, so the offsets miss.

**Resolution options:**
1. **Add a `crop_offset_mm` parameter to `inject_into_frame`** that pre-shifts the crop window. For left half: `crop_offset_mm=(0, 0)`. For right half: `crop_offset_mm=(page_w_mm, 0)`. Internal `crop_for_frame` widens its target to `2 × page_w_mm` and then takes the appropriate half. Requires extending `crop_for_frame` semantics — not a 5-LoC change.
2. **Add a sibling helper `inject_spread_image(left, right, img, page_w_mm, page_h_mm, h_mm, ...)`** that does the right thing in one call. Cleaner API; ~30 LoC + tests in `test_library.py`.
3. **In `build_preview()`, manually crop the image to 2x width and inject directly into the two halves with bypass of `inject_into_frame`.** Brittle, lots of hand-coded byte plumbing. AVOID.
4. **Defer the inject** — leave the `image=''` placeholders in the SpreadImage halves and accept that gallery preview pages 10-11 render as empty in this PR. File a follow-up to wire up the spread-image inject helper.

**Recommendation for the planner:** **Option 4** for THIS issue, **Option 2** as a follow-up. Issue #16 is already a multi-system change; adding a new library helper signature is scope creep. The gallery preview PNGs for pages 10-11 will lose the photo content but will be `inside_page`-clean (the issue's primary acceptance criterion). The PR reviewer is already on the hook for visual review (acceptance criterion 4); they accept the placeholder appearance and the follow-up commits the inject helper later.

If the planner disagrees with Option 4 and wants to wire inject in this PR, **Option 2** is the right shape. Specify the new function signature explicitly so the executor doesn't drift into Option 3 territory.

---

## P-10 (MEDIUM) — `SpreadImage.place(page_left, page_right)` adds to BOTH pages; OwnPage attribution

**Verified:** `tools/sla_lib/builder/blocks.py:735-740`:
```python
def place(self, page_left, page_right) -> tuple[ImageFrame, ImageFrame]:
    l, r = self.emit()
    page_left.add(l)
    page_right.add(r)
    return l, r
```

**OwnPage attribution flows through `Page.add(frame)`** which does NOT mutate frame.x_mm/y_mm — coordinates stay page-local. `inside_page` checks each frame against ITS OWN page's bounds (`brand_constraints.py:462-468`), which means both halves at `x=0, w=210` pass on their respective A4 pages.

**Pitfall:** `page_left` and `page_right` MUST be sequential pages in the document. `SpreadImage` does not enforce this; the planner must specify which page-pair to use. For `P9 Spread` migration: the spread is intended across pages 10-11 (1-indexed). In build.py 0-indexed, that's `page9` and `page10`. Migration call: `SpreadImage(...).place(page9, page10)`. NOT `(page8, page9)` or `(page10, page11)`.

**Cross-check:** The current overflow frame is `page9.add(ImageFrame(x_mm=210, ...))`, on `page9` 0-indexed = print page 10. Its right-edge overflow lands on print page 11. So the spread is 10-11 print = `page9`-`page10` 0-indexed. ✓.

---

## P-11 (LOW) — The 0.8 mm "warnings" in ISSUE.md don't actually exist as warnings

**Verified by execution** (see P-3): `_InsidePageRule().check(...)` returns 3 errors and 0 warnings. The 0.8mm-wider frames at lines 1955 (page-12 fill polygon) and 2283 (page-14 fill polygon) do NOT trigger inside_page — their bbox sits within `[-bleed, page_w + bleed]` because `0 + 210.799 < 213`. The "warning" in ISSUE.md §"Why" is an incorrect prediction.

**Consequence:** ISSUE.md's framing "trim them anyway so `--all` is truly clean" is moot — `--all` is ALREADY clean on these frames (modulo the rule-level override). The "warning-vs-error tolerance carve-out" the planner is supposedly avoiding doesn't exist.

**What trimming achieves:** Cosmetic — aligns the frame width with the page trim width. Cost: 3 sla_diff `size-drift` warnings (one per trimmed frame), all of which fail `--strict`.

**Recommendation for the planner:** **Drop the 0.8mm trim from scope.** It's pure cosmetic, doesn't fix any constraint failure, and adds 3 unnecessary sla_diff warnings to handle. ISSUE.md §"Open questions / risks" already acknowledges this: *"If the round-trip diff complains, revert these two tiny fixes."* Cut the rope before pulling.

If the planner wants to keep the trim for pristine round-trip: it's a separate question per frame, and each trim must be paired with an entry in the new `sla_diff_overrides.ignore_pageobjects` mechanism from P-1 option 2.

---

## P-12 (HIGH) — Atomic-PR ordering requirement

**Per the prompt's focus area #6:** All changes (frame moves + override removal + test update + INJECT_MAP/CONSTRAINTS update + render-gallery regeneration) MUST land in a single PR or `structural_check --all` AND `sla_diff` AND `bin/check-stale-previews` will go red mid-PR.

**Specific ordering risks:**

1. **Don't commit "remove brand_overrides skip" alone.** That single commit alone fails `structural_check --all` (3 errors surface, including u2950).
2. **Don't commit "edit build.py" alone.** That alone fails `bin/check-stale-previews` (template.sla SHA mismatch).
3. **Don't commit "regenerate template.sla + previews" alone.** That alone might fail `sla_diff --strict` (build.py change → SLA bytes shift → diff against original SLA shows changes).
4. **Don't commit "update test_zeitung_overflow.py" alone.** That alone might fail (the test depends on build.py being already-fixed AND override being already-removed).

**The whole change must be a single commit (or a clean commit chain that arrives green at every intermediate state).** Recommended commit ordering for cleanest review:
1. **Commit A:** Add `--ignore-pageobject-by-anname` to `tools/sla_diff.py` + tests (P-1 prerequisite). PASSES CI.
2. **Commit B:** Extend `meta_schema.py` for per-frame `targets` field, if Option B.1 from P-3 is chosen (P-3 prerequisite). PASSES CI.
3. **Commit C:** The actual zeitung edits — move/replace frames in build.py + update INJECT_MAP + update CONSTRAINTS + update meta.yml (remove rule-level override OR replace with per-frame targeted override OR add sla_diff overrides) + run `bin/render-gallery` + commit regenerated `template.sla`, `template-preview.sla`, `preview.pdf`, `page-NN.png`, `meta.yml::previews_for_sla` SHA, and `site/public/templates/zeitung-a4-grun/*` mirrors. UPDATE `test_zeitung_overflow.py` in same commit. PASSES CI.

Each commit individually green. Reviewer can split-review.

If the planner chooses Option B.2 from P-3 (no schema extension), drop commit B.

---

## P-13 (LOW) — Anname-collision risk: "P9 Spread · left" / " · right" middle-dot

**Verified:** `blocks.py:722, 731` use the literal middle-dot character " · " (U+00B7 surrounded by ASCII spaces). Confirmed in `test_spread_image.py:29` (`"Cover · left"`).

**Pitfall:** If the executor types a hyphen or em-dash by mistake, the anname mismatch silently breaks INJECT_MAP lookups. Use the SpreadImage block's `base_anname` parameter — never hand-construct the anname.

**Search collision risk:** `grep "P9 Spread"` in build.py finds the constants. After migration, `grep "P9 Spread"` matches the substring inside `"P9 Spread · left"` and `"P9 Spread · right"`. The CONSTRAINTS update should use these full annames; INJECT_MAP keys should also use them. No collision with other annames in the doc (verified — `grep "Spread" templates/zeitung-a4-grun/build.py` shows only `P9 Spread`, `P4 Foto-Spread` — different strings).

---

## P-14 (LOW) — `image=''` on the SpreadImage emission

**Pitfall:** `SpreadImage(image="", ...)` emits two ImageFrames with `image=''`. The current `P9 Spread` frame at line 1808 is `image=''`. So the SLA-emit contract for `template.sla` (the round-trip-faithful, no-injects build) is unchanged — both before and after migration, the frame's PFILE is empty.

For `template-preview.sla` (with library injects), the inject must happen on BOTH frames, which P-9 covers.

For round-trip vs. original SLA: the original frame at `OwnPage=9` has no PFILE; the new frames at `OwnPage=9` and `OwnPage=10` also have no PFILE. The diff is a structural one (frame count delta), not a PFILE one.

---

## P-15 (LOW) — Visual diff baseline is stale after edits

**Verified:** `templates/zeitung-a4-grun/baseline.pdf` exists (1.3 MB, dated May 9). It is the frozen Scribus PDF export from before this issue; once frames move, it no longer matches. Per `docs/render-fidelity.md:108-118` "Rebaselining is NOT casual" — only re-baseline after verifying against a fresh user-exported reference PDF.

**Per ISSUE.md acceptance criterion 4**, the human PR reviewer rebaselines (the agent must NOT). Plan must explicitly carry this forward — "do not regenerate baseline.pdf in this issue's commit".

**Pitfall:** `bin/render-gallery` (default invocation) runs visual_diff and FAILS on baseline drift, blocking the SHA-update step in the same pipeline. Use `bin/render-gallery --skip-visual-diff` to update everything except the visual_diff gate.

---

## P-16 (LOW) — Dependency check / environment

**Verified in this worktree:**
- Python 3.13.5
- lxml 5.4.0, PyYAML 6.0.3, jsonschema 4.26.0
- pdfimages 25.03.0 (poppler), pdftotext, pdftoppm
- ImageMagick `compare` (used by visual_diff, but visual_diff is local-only)
- scribus 1.6.5 (`/usr/bin/scribus`)
- `gruene-zeitung-vorlage-original.sla` exists (the upstream)
- `templates/zeitung-a4-grun/template.sla` exists
- `templates/zeitung-a4-grun/template-preview.sla` exists
- `templates/zeitung-a4-grun/baseline.pdf` exists

**No new dependencies needed.** All work is stdlib + existing deps.

**Test framework:** `unittest` only (verified — `test_zeitung_overflow.py:32`). Per CI workflow line ~98: `python3 -m unittest discover tools/sla_lib/tests`. New tests must follow the existing conventions (sys.path insert at top, ROOT navigation 4 levels up). Do NOT introduce `pytest` for this issue.

---

## P-17 (LOW) — `Document.iter_all_primitives()` skips master-page items

**Verified:** `_InsidePageRule.check` (`brand_constraints.py:457-495`) iterates `doc.pages` and `page.is_master` skips. Master items are NOT subject to the rule. The cover-page polygon `u2950` is on `page0` (NOT a master), so it IS checked — confirming the bbox math is correct.

**Pitfall (informational):** If a future `P9 Spread`-class fix involves moving frames to a master-page, the inside_page rule will silently stop checking them. Don't do that.

---

## P-18 (LOW) — `build.py` is 2563 LoC; surgical edits only

The file is generated from upstream Scribus via `tools/sla_to_dsl.py` (verified in commit history — `b8792e5 14: Constraint DSL...` and earlier). Manual hand-edits to round-trip-generated files risk being clobbered by future regeneration. **Recommended:** Add a hand-edit marker comment near each modified line (e.g. `# issue #16 — moved from page9 right-edge spread overflow`), so future `tools/sla_to_dsl.py` runs (if any) can detect the divergence.

The two right-edge overflow frames have existing `# issue #13` comments — same pattern. New comments should follow: `# issue #16 — SpreadImage migration` at the spread; `# issue #16 — moved from page11 right-edge` at the relocated unnamed frame.

**No regeneration in scope:** This issue does NOT re-run `tools/sla_to_dsl.py` against the upstream SLA. The upstream is treated as immutable input (per ISSUE.md "Out of scope: Any change to gruene-zeitung-vorlage-original.sla").

---

## P-19 (MEDIUM) — `build.py` is in `_load_build_module()` cache; run isolation

**Verified:** `tools/sla_lib/builder/structural_check.py:113-115` — `sys.modules.pop(mod_name, None)` is called before each `_load_build_module`. So `--all` re-evaluates each template's build.py freshly, no cross-contamination. Safe.

**However:** Two tests in this repo load build.py via `importlib`:
- `tools/sla_lib/tests/test_zeitung_overflow.py` (loads via `_load_zeitung_doc`)
- Any test that calls `structural_check.check_template`

If `unittest discover` runs both in the same process, `sys.modules` cache might cause stale `INJECT_MAP` references. The current test does `importlib.util.spec_from_file_location` which creates a new module — should be safe. **But** if the executor adds new tests that import `from templates.zeitung_a4_grun.build import ...`, the import-time mutation issue might surface. **Stick to `_load_zeitung_doc`-style importlib pattern** for any new tests.

---

## P-20 (LOW) — Tests in `tools/sla_lib/tests/` discovered automatically

**Verified:** `tools/sla_lib/tests/test_zeitung_overflow.py` — file naming convention is `test_*.py`. New tests follow same pattern. CI's `python3 -m unittest discover tools/sla_lib/tests` picks them up. **Do not add tests outside this directory** — they won't run in CI.

**Test runtime budget:** The existing `test_inside_page_finds_the_known_overflows_without_override` runs `build_doc()` which is the full 2563-LoC build.py (currently ~0.6s on this hardware per `time` invocation). New tests should also load via `_load_zeitung_doc` rather than re-building from scratch. Per ISSUE.md acceptance: <2s budget for the regression test is realistic.

---

## P-21 (NEGATIVE FINDING) — `templates/zeitung-a4-grun/diff.yml` does NOT have a per-frame ignore mechanism

**Verified:** `cat templates/zeitung-a4-grun/diff.yml` — schema is `visual_diff: {max_pixel_mismatch_pct, fuzz_pct}`. NO frame-level overrides; NO sla_diff section. The `diff.yml` is consumed only by `tools/visual_diff.py` (verified — `grep diff.yml tools/sla_diff.py` is empty).

**Implication:** The prompt's hopeful question "Whether `diff.yml` has a per-frame ignore mechanism (so the moved frames can be excluded from the strict diff)" — answer is **NO**. The mechanism does not exist; we either build it (P-1 option 2) or accept the diff failure (P-1 option 3).

---

## Security surface

**None.** This is a static-asset / template-build issue, no auth or data flow change. No new dependencies.

---

## Summary of recommendations to feed into the planner

| # | Issue | Recommended action | Severity |
|---|-------|-------------------|----------|
| P-1 | sla_diff has no per-frame ignore | Add `--ignore-pageobject-by-anname` flag + meta.yml `sla_diff_overrides` field | CRITICAL |
| P-2 | previews_for_sla SHA invalidates | Run `bin/render-gallery --skip-visual-diff`, commit regenerated artifacts | HIGH |
| P-3 | Removing rule-level override surfaces u2950 | Option B.2: keep override with new reason mentioning new follow-up issue (FILE the follow-up before merge) | HIGH |
| P-4 | test_zeitung_overflow.py expects 3 errors | Rewrite both tests in the same commit as the build.py edits | HIGH |
| P-5 | INJECT_MAP + CONSTRAINTS reference "P9 Spread" | Update both to use new "P9 Spread · left" / " · right" | CRITICAL |
| P-6 | local_offset_mm sign | Use `SpreadImage.place()` exclusively, never hand-roll the two ImageFrames | HIGH |
| P-7 | scale_type=0 vs default 1 | Trust `SpreadImage.scale_type` default; PR reviewer manually verifies pages 10-11 | MEDIUM |
| P-8 | Page-12 unnamed frame interpretation | Move to page12 (0-indexed); SKIP the 0.8 mm width trim | HIGH |
| P-9 | inject_into_frame incompatible with SpreadImage halves | Defer (Option 4): leave `image=''` in spread halves; file follow-up for spread-inject helper | HIGH |
| P-10 | place() arguments | Migration call exactly: `SpreadImage(...).place(page9, page10)` | MEDIUM |
| P-11 | 0.8 mm "warnings" don't exist | DROP the 0.8 mm trim from scope entirely | LOW |
| P-12 | Atomic-PR ordering | 3-commit chain: A=sla_diff flag, B=meta_schema (only if B.1), C=zeitung edits + tests | HIGH |
| P-13 | Middle-dot anname | Use `base_anname` parameter; never hand-construct anname | LOW |
| P-15 | baseline.pdf is stale | Do NOT regenerate; PR reviewer rebaselines | LOW |
| P-18 | build.py is generated | Add `# issue #16` markers near edits | LOW |
| P-19 | importlib cache | New tests use `_load_zeitung_doc`-style importlib loader | MEDIUM |
| P-21 | diff.yml has no sla_diff section | Build the mechanism (P-1) — `diff.yml` is NOT the answer | NEGATIVE FINDING |

---

## What the planner should specifically prevent the executor from doing

1. Hand-rolling two `ImageFrame()` calls instead of `SpreadImage().place()` (silent right-half-shows-left-half bug, P-6).
2. Trimming the 0.8 mm widths "to be tidy" (3 unnecessary sla_diff failures, no constraint benefit, P-8 + P-11).
3. Fixing `u2950` "while we're in there" (out of scope per ISSUE.md, breaks visual cover, requires separate visual review, P-3 Option A).
4. Removing the `brand:inside_page` override entirely without filing a follow-up for u2950 (silent regression, P-3).
5. Forgetting to update `INJECT_MAP` / `CONSTRAINTS` (gallery preview broken + structural-check warning, P-5).
6. Forgetting to regenerate `template.sla` / `previews_for_sla` SHA via `bin/render-gallery` (CI red, P-2).
7. Regenerating `baseline.pdf` (acceptance criterion 4 forbids; P-15).
8. Splitting commits in any order other than: (A) sla_diff flag → (B) optional meta_schema extension → (C) atomic zeitung edits + tests + render-gallery output (CI red mid-PR, P-12).
9. Visually inspecting `page-NN.png` files to verify correctness (forbidden per prompt focus area #11; PR reviewer's job).
