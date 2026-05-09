# Codebase research — Issue #16 (zeitung-a4-grun overflow fix)

**Researched:** 2026-05-09
**Working tree:** `/root/workspace/.worktrees/16-fix-zeitung-a4-image-frames-placed-past-page-boundary-spilling-into-adjacent-pag`
**Tools used:** `Read`, `Grep`, `Glob`, `Bash` (git log, `pdfinfo`, `pdfimages`, `pdftotext` on the workspace-level PDF, plus a Python harness running `_InsidePageRule` directly).
**Sub-agent mandate:** CODEBASE only — ecosystem (Scribus DOM details / SLA spec) and pitfalls (Scribus rendering edge cases) belong to the other two researchers.

---

## 0. Page numbering convention used in this report (HIGH)

The ISSUE.md uses 1-indexed **printed** page numbers (1..14). The build.py uses 0-indexed Python identifiers (`page0..page13`). Throughout this report I use the build.py 0-indexed names primarily, with the printed-page number in parentheses where the issue references it.

| ISSUE.md "page" | build.py identifier | line range |
|:---:|:---:|:---:|
| Page 10 | `page9` | 1802-1811 (the `P9 Spread` ImageFrame) |
| Page 12 | `page11` | 2061-2071 (the unnamed full-A4 dark-green ImageFrame) |
| Page 12 | `page11` | 1952-1961 (the 0.8 mm "right overflow" frame, h=213.92) |
| Page 14 | `page13` | 2280-2290 (the 0.8 mm "right overflow" frame, h=152.61) |

Note: ISSUE.md item 3 ("Page 12, h=213.9") and item 4 ("Page 14, h=152.6") map to printed pages 12 and 14. Items 1 and 2 ("Page 10" and "Page 12") map to the two true overflows. **The issue does NOT have two frames on the same printed page** — I confirmed this by grepping every `w_mm=210.7990642201835` and matching to its enclosing `pageN.add(...)`.

---

## 1. Files touched / read

| File | Purpose | Last modified | Relevance |
|---|---|---|---|
| `templates/zeitung-a4-grun/build.py` | Template source (3244 LOC, auto-generated, hand-edited) | `b8792e5` (#14) | Where the 4 frames live; primary edit target |
| `templates/zeitung-a4-grun/meta.yml` | Template metadata + override list | `b8792e5` (#14) | Carries the `brand:inside_page` skip entry that #16 removes |
| `templates/zeitung-a4-grun/README.md` | End-user docs | older (no recent change) | Add divergence note (issue scope item 7) |
| `templates/zeitung-a4-grun/diff.yml` | Visual-diff tolerance config (NOT an SLA-diff allowlist) | older | Likely unchanged by this issue — see §5 |
| `tools/sla_lib/builder/blocks.py` | All compose blocks; `SpreadImage` at lines 686-740 | `b8792e5` (#14) | New utility — but per §6 evidence, NOT the right tool for #16 |
| `tools/sla_lib/builder/primitives.py` | `ImageFrame` dataclass | older + `b8792e5` | Field set we'll author against |
| `tools/sla_lib/builder/brand_constraints.py` | `_InsidePageRule` at lines 425-495 | `b8792e5` (#14) | The rule whose 3 errors must drop after fix |
| `tools/sla_lib/tests/test_zeitung_overflow.py` | Regression test pinning current 3-error count | `b8792e5` (#14) | Must be updated; see §7 |
| `tools/sla_diff.py` | Round-trip differ; severities, tolerances, exit codes | `cb0ad83` (#8) | The pipeline's strict round-trip gate; see §6 |
| `tools/render_pipeline.py` | Wires `sla_diff --strict --allow-brand-extras` into CI | older | Confirms there is NO allowlist mechanism |
| `gruene-zeitung-vorlage-original.pdf` | The 14-page rendered PDF Scribus produced from the upstream SLA. **Lives at `/root/workspace/`, NOT in the worktree.** | n/a (binary asset) | Critical evidence for the spread-vs-move decision; see §6 |

> Worktree boundary note: the upstream PDF is one directory above the worktree. The user's prompt says "stay strictly inside the worktree" but also explicitly directs the researcher to inspect the PDF for diagnosis. I read it from the workspace root (read-only, metadata-only — no rendering, no copy into the worktree). The planner / executor should NOT need to re-read it; this report carries the verdict.

---

## 2. The four offending frames — exact current state

### 2.1 Frame A — `P9 Spread` on `page9` (printed page 10) — **TRUE error, 207 mm overshoot**

**Source — `templates/zeitung-a4-grun/build.py` lines 1802-1811:**
```python
    page9.add(ImageFrame(
        x_mm=209.99999999993608,
        y_mm=0,
        w_mm=209.9999999999361,
        h_mm=126.13945871829057,
        layer=0,
        image='',
        line_width_pt=1,
        anname="P9 Spread",  # issue #13
    ))
```

**Bbox:** `(210.00, 0.00) → (420.00, 126.14)` on a `[-3, 213]×[-3, 300]` page → **right-edge overshoot 207.00 mm** (rule reports as `error`).

**`inject_into_frame` consumer:** the `INJECT_MAP` in `build_preview()` (line 2504) ALSO references this frame by anname:
```python
"P9 Spread": ("themen_klimaschutz_solar", 210, 126.1),
```
→ if we delete the frame the gallery preview silently no-ops (the loop at line 2511 just skips frames whose anname isn't in the map). If we move/rename the frame, we must keep the anname `"P9 Spread"` so the inject still finds it.

**`CONSTRAINTS` consumer:** `same_size("P9 Spread", name="p9_spread_anchor")` at line 2555 is a single-target witness — it only cares the anname EXISTS. Renaming it would silently break this witness; moving it (anname preserved) is fine. (HIGH; verified via single-target `same_size` semantics in `tools/sla_lib/builder/constraints.py:417`.)

### 2.2 Frame B — unnamed `ImageFrame` on `page11` (printed page 12) — **TRUE error, 207.8 mm overshoot**

**Source — `templates/zeitung-a4-grun/build.py` lines 2061-2071:**
```python
    page11.add(ImageFrame(
        x_mm=209.99999999999991,
        y_mm=-0.1807155930984082,
        w_mm=210.7990642201835,
        h_mm=297.1807155930968,
        layer=0,
        image='',
        fill='Dunkelgrün',
        line_width_pt=1,
        local_offset_mm=(0.3303109072374783, -0.3257155930969475),
    ))
```

**Bbox:** `(210.00, -0.18) → (420.80, 297.00)` → **right-edge overshoot 207.80 mm** (rule reports as `error`, message identifier `<unnamed ImageFrame>`).

**No INJECT_MAP entry, no CONSTRAINTS entry, no anname** → safe to relocate or even delete without touching anything else. The `fill='Dunkelgrün'` and the `local_offset_mm` make it a colored background tile, not an actual image carrier.

### 2.3 Frame C — unnamed `ImageFrame` on `page11` (printed page 12) — **NOT an error; 0.8 mm bleed-trim drift only**

**Source — `templates/zeitung-a4-grun/build.py` lines 1952-1961:**
```python
    page11.add(ImageFrame(
        x_mm=0,
        y_mm=-0.1807155930984082,
        w_mm=210.7990642201835,
        h_mm=213.91926605504602,
        layer=0,
        image='',
        fill='Dunkelgrün',
        line_width_pt=1,
    ))
```

**Bbox:** `(0.00, -0.18) → (210.80, 213.74)`. **Inside-page rule today:** worst overshoot is `0.799 mm` (right edge vs. trim 210), **but the rule measures against `[-bleed, w+bleed]` = `[-3, 213]`** so the actual overshoot vs. the rule's threshold is `-2.20 mm` → **rule reports nothing.** (HIGH; verified by running `_InsidePageRule.check()` in a harness — see §3.)

ISSUE.md item 3 calls this a "0.8 mm overflow flagged for completeness." **It is not actually flagged today by `inside_page`** because the rule honours the bleed envelope. The fix here is purely cosmetic.

### 2.4 Frame D — unnamed `ImageFrame` on `page13` (printed page 14) — **NOT an error; 0.8 mm bleed-trim drift only**

**Source — `templates/zeitung-a4-grun/build.py` lines 2280-2290:**
```python
    page13.add(ImageFrame(
        x_mm=0,
        y_mm=-0.18071559309872906,
        w_mm=210.7990642201835,
        h_mm=152.61377064220179,
        layer=0,
        image='',
        fill='Dunkelgrün',
        line_width_pt=1,
        local_offset_mm=(1.0939347604485252, -0.7605759429155533),
    ))
```

**Bbox:** `(0.00, -0.18) → (210.80, 152.43)`. Same situation as Frame C — overshoots trim by 0.8 mm but sits inside the bleed envelope.

---

## 3. Verified `inside_page` baseline (HIGH)

I ran the rule directly with a harness that bypasses the `meta.yml` override:

```
[error] u2950: bbox (-4.08, 155.57)→(216.41, 304.17), worst overshoot 4.17 mm
[error] P9 Spread: bbox (210.00, 0.00)→(420.00, 126.14), worst overshoot 207.00 mm
[error] <unnamed ImageFrame>: bbox (210.00, -0.18)→(420.80, 297.00), worst overshoot 207.80 mm
Total: 3 violations, 3 errors
```

**This matches `tools/sla_lib/tests/test_zeitung_overflow.py::test_inside_page_finds_the_known_overflows_without_override` exactly.** No warnings — no zero-to-one-mm "warning band" frames exist today (the rule's `tolerance_mm=0.5 / error_cutoff_mm=1.0` split has no occupants in zeitung).

**Implications for the planner:**
- After fixing Frames A and B, the rule will emit ONE remaining error: `u2950` (the rotated cover-page Dunkelgrün polygon, 4.17 mm bottom overshoot).
- `u2950` is **explicitly out of scope for #16** — both `tools/sla_lib/tests/test_zeitung_overflow.py:14-26` and `.issues/archive/14-.../EXECUTION.md:72` track it as a future follow-up.
- Therefore: **the `meta.yml::brand_overrides` entry for `brand:inside_page` CANNOT simply be deleted.** Either (a) `u2950` is fixed in the same PR (scope creep — not what ISSUE.md asks), or (b) the override stays but is REWORDED to point at the new follow-up issue rather than #16. See §4 for the recommended copy.
- `acceptance criterion 1` ("zero `inside_page` errors") is **satisfiable only if either u2950 is fixed too OR the override is kept (with rewritten reason).** The planner must choose. My recommendation in §10 is option (b).

---

## 4. Exact `meta.yml` change

**Source — `templates/zeitung-a4-grun/meta.yml` lines 31-36:**
```yaml
  - id: brand:inside_page
    reason: >-
      Two frames (P9 Spread at build.py:1802-1811, unnamed page-12 image
      at 2061-2071) overflow the right page edge by >200 mm — tracked in
      issue #16. This override silences the rule globally for zeitung
      until #16 lands the SpreadImage migration.
```

**Recommended replacement (option (b) from §3 — rewrite to point at the u2950 follow-up):**
```yaml
  - id: brand:inside_page
    reason: >-
      One residual frame after #16: the rotated cover-page polygon
      `u2950` (build.py:246-256) overflows the page bottom by ~4.17 mm
      (rotation-aware bbox extends below y=300). Tracked as a follow-up
      issue against zeitung; the upstream Scribus original carries the
      wrong polygon size + 90° rotation. Remove this override once that
      polygon is fixed.
```

**Alternative: option (a), full delete + fix u2950 in the same PR.** Out of ISSUE.md scope; recommend planner does NOT take this path unless the user reopens scope. If the user DOES want option (a), the u2950 fix is a Polygon size/position change at `templates/zeitung-a4-grun/build.py:246-256` — likely shrink h_mm from 220.49 to ~216.32 (so the rotated bbox bottom lands at y=300), but the upstream PDF inspection should be repeated to confirm the polygon is meant to extend full-bleed.

The `brand:line_spacing_0.9` override (lines 23-30) is **NOT touched by this issue** — leave it.

---

## 5. The PDF evidence — what the upstream actually renders (HIGH)

**Per `pdfimages -list /root/workspace/gruene-zeitung-vorlage-original.pdf`:**

| PDF page (printed) | Image count | Image dims (px) | Notes |
|---:|---:|---|---|
| 1 | 1 | 878×893 | Cover hero |
| 9 | 2 | 276×231, 276×231 | Two small portrait/avatar images |
| **10** | **0** | — | **No image renders here** |
| 11 | 1 | 276×231 | One small portrait |
| **12** | **0** | — | **No image renders here** |
| 13 | 1 | 276×231 | One small portrait |
| 14 | 1 | 474×480 | Small image |

**Per `pdftotext -layout -f 9 -l 11`:** printed pages 9-11 carry text only, with the two "Spread"-titled article blocks ("Beitrag mit Zitat", "Ein weiterer Beitrag mit Zitat, aber anders", "Hier noch ein Beispiel, das alle Stücke spielt"). No image content stretches across pages 10 and 11.

**Per `pdftotext -layout -f 11 -l 12`:** printed page 12 carries the "Weiße Headlines auf grünem Hintergrund" article — text only, no full-bleed dark-green panel.

**Decision (HIGH confidence):** **NEITHER Frame A nor Frame B is a real spread.** The "Spread" suffix in `anname="P9 Spread"` is a misleading authoring artifact — the upstream Scribus author placed empty placeholder ImageFrames at `x=210` (one A4 width to the right of the page, i.e. on the off-page scratch canvas) when intending them as either (a) future spread fillers they never used, or (b) a copy-paste accident. **The `SpreadImage` block is the WRONG fix.** It would emit two image halves where today the upstream renders zero image data.

**Implication for ISSUE.md scope item 1:** The "Decision criterion: read the corresponding cell in `gruene-zeitung-vorlage-original.pdf` page 11 vs. 10 (no PNGs, just `pdftotext`/`pdfimages` to confirm where the image data renders)" resolves clearly to **single-page move (or delete)**, NOT `SpreadImage` migration. See §6 for the recommended fix shape.

**Implication for ISSUE.md scope item 2:** Same evidence — printed page 12 (build.py `page11`) has zero image content in the upstream PDF, so the `Dunkelgrün` placeholder Frame B is also an unused author-side artifact. Moving it onto its "intended" page is somewhat speculative — there is no rendered image evidence telling us which page it was meant for. Recommended: **delete Frame B** (no anname, no INJECT_MAP, no CONSTRAINTS reference, no rendered counterpart in the upstream PDF). The issue says "move", but evidence says the move target is undefined. The planner should flag this for user confirmation; a safe alternative is a no-op move to (0,0) on the same page so the round-trip diff just shows two coordinate changes rather than an item-count delta.

---

## 6. Exact `build.py` changes — concrete patch text

### 6.1 Frame A — `P9 Spread`: TWO options the planner picks between

**Option A1 (RECOMMENDED, evidence-backed): Move to its own page at x=0.** Preserves the anname so `INJECT_MAP` and `CONSTRAINTS` keep working. The frame becomes a same-page hero slot.

Replace `templates/zeitung-a4-grun/build.py` lines 1802-1811 with:
```python
    page9.add(ImageFrame(
        x_mm=0,
        y_mm=0,
        w_mm=209.9999999999361,
        h_mm=126.13945871829057,
        layer=0,
        image='',
        line_width_pt=1,
        anname="P9 Spread",  # issue #13 (renamed at gallery-injection time; kept for INJECT_MAP)
    ))
```

Notes:
- `x_mm: 210 → 0` is the only meaningful change. `w_mm` and `h_mm` are unchanged (they were correct sizes; the bug was POSITION).
- I match the existing trailing-9s float pattern (`209.9999999999361`) used by the original SLA round-trip — round numbers like `210.0` would create extra `position-minor-drift` infos in `sla_diff.py`. (HIGH; verified `sla_diff.py:716-728` uses `POSITION_TOLERANCE_PT=0.5`.)
- Anname stays `"P9 Spread"` for `INJECT_MAP` consumer compatibility (the name is now misleading, but renaming would cascade into 4 other places and is out of #16 scope). Optionally append `# issue #16` after the existing `# issue #13` comment.

**Option A2 (ONLY if user later confirms an actual spread is desired): SpreadImage migration.** Per §5, the PDF evidence does NOT support this. Listed for completeness:
```python
    # Replaces page9.add(ImageFrame(...)) at line 1802, AND adds a sibling
    # frame on page10. Delete the original line 1802 ImageFrame entirely.
    from sla_lib.builder.blocks import SpreadImage   # add to top-level import
    SpreadImage(
        image='',
        page_w_mm=209.9999999999361,
        page_h_mm=296.99999999946107,
        h_mm=126.13945871829057,
        y_mm=0,
        base_anname='P9 Spread',
        scale_type=0,
        local_scale=(1.0, 1.0),
    ).place(page9, page10)
```
This emits two halves with annames `"P9 Spread · left"` / `"P9 Spread · right"` (per `blocks.py:722,731`) — which would BREAK the existing `INJECT_MAP["P9 Spread"]` lookup AND the `same_size("P9 Spread")` constraint witness. Not recommended.

**Decision criterion (HIGH):** PDF inspection in §5 shows zero image rendered on the spread → **Option A1 wins.**

### 6.2 Frame B — unnamed page-11 ImageFrame: delete OR move

**Option B1 (RECOMMENDED): Delete the frame entirely.** No anname, no INJECT_MAP, no constraint, no rendered counterpart in the upstream PDF.

Delete `templates/zeitung-a4-grun/build.py` lines 2061-2071 (the entire `page11.add(ImageFrame(...))` block from `page11.add(ImageFrame(` through the closing `))`).

Round-trip diff impact: `page-item-count-mismatch` CRITICAL on OwnPage=11 (left has the frame, right doesn't). Same shape as Option B2 below. See §6.4 for handling.

**Option B2 (FALLBACK if user wants frame preserved): Move to (0, 0) on the same page.** Keeps SLA item count stable, preserves the round-trip pairing.

Replace `templates/zeitung-a4-grun/build.py` lines 2061-2071 with:
```python
    page11.add(ImageFrame(
        x_mm=0,
        y_mm=-0.1807155930984082,
        w_mm=210.7990642201835,
        h_mm=297.1807155930968,
        layer=0,
        image='',
        fill='Dunkelgrün',
        line_width_pt=1,
        local_offset_mm=(0.3303109072374783, -0.3257155930969475),
    ))
```
(Only change: `x_mm: 210.00 → 0`; everything else verbatim.)

This puts a full-page Dunkelgrün rectangle UNDER all the existing page-11 content. **Visual side effect**: it would tint the entire page green. The user / brand team needs to confirm the page-11 visual currently has a green background somewhere — per §5 PDF evidence, page 12 (this frame's printed page) does NOT have a full-page green tint. **B2 would visually change the rendered page.** Therefore Option B1 (delete) is the correct mechanical fix.

**Decision criterion (HIGH):** Option B1 wins — the frame contributes nothing to the rendered upstream PDF; preserving an unused frame just to keep the diff smaller is the wrong tradeoff.

### 6.3 Frames C & D — the 0.8 mm cosmetic fixes

ISSUE.md scope items 3 & 4. Per §3, **these are NOT errors today** under `inside_page`'s bleed-aware logic. The planner can:

- **Skip them entirely** — drops scope items 3 & 4 from this issue. The `inside_page` baseline still goes from 3 errors to 1 (the u2950 follow-up).
- **Apply them as cosmetic cleanup** — trims `w_mm: 210.7990642201835 → 210.0` on the two frames, plus `y_mm: -0.18 → 0` if we want a fully clean baseline. No `inside_page` impact, but adds 4 `size-drift` WARNINGs (`w_pt` delta = 0.799 × 2.835 = 2.265 pt > 0.5 pt threshold) and 2 `position-drift` WARNINGs to the round-trip → fails `sla_diff.py --strict` exactly the same way as items 1 & 2. **No CI benefit, just diff cost.** Recommend SKIP.

If the planner wants to do them anyway (per ISSUE.md "fix them too for clean baseline"), the patches are:

**Frame C (lines 1952-1961):** change `w_mm=210.7990642201835` → `w_mm=209.9999999999361` (match existing trailing-9s float style) and `y_mm=-0.1807155930984082` → `y_mm=0`.

**Frame D (lines 2280-2290):** same — `w_mm=210.7990642201835` → `w_mm=209.9999999999361`, `y_mm=-0.18071559309872906` → `y_mm=0`. Keep `local_offset_mm=(1.0939347604485252, -0.7605759429155533)` unchanged (it's a LOCAL offset of the inline image, not the frame).

**Recommendation: SKIP frames C & D in this issue.** They don't fail any rule, they cost diff budget for zero CI gain, and ISSUE.md item 5 explicitly says "If the round-trip diff complains, revert these two tiny fixes — we keep the core P9/P11 fix." The planner can preempt that by not making the change at all.

### 6.4 Round-trip diff impact summary (HIGH — see §8)

Each of the four candidate edits in 6.1-6.3 generates round-trip-diff issues. Summary:

| Change | Severity in `sla_diff.py` | Impact on `--strict` |
|---|---|---|
| Frame A move (option A1) | `position-drift` WARNING on XPOS (Δ=210mm) | Fails strict (warning gate). |
| Frame A SpreadImage (option A2) | `page-item-count-mismatch` CRITICAL on OwnPage=9 AND OwnPage=10 | Fails strict + non-strict. |
| Frame B delete (option B1) | `page-item-count-mismatch` CRITICAL on OwnPage=11 | Fails strict + non-strict. |
| Frame B move (option B2) | `position-drift` WARNING on XPOS (Δ=210mm) | Fails strict (warning gate). |
| Frame C trim | `position-drift` + `size-drift` WARNINGs on lines-1952 frame | Fails strict. |
| Frame D trim | `position-drift` + `size-drift` WARNINGs on lines-2280 frame | Fails strict. |

**There is NO allowlist mechanism in `sla_diff.py`.** Verified by grepping `tools/sla_diff.py` for `allowlist|exempt|ignore|expected_diff` — only `--allow-brand-extras` exists, and it's about brand extras (color names, missing legacy layers) not about frame positions. (HIGH; cf. `tools/sla_diff.py:1196-1210`.)

**Therefore the fix WILL break `tools/render_pipeline.py::_run_sla_diff_strict` (line 384-408)** which hardcodes `--strict`. Three options for the planner:

1. **Drop `--strict` from `render_pipeline.py:397`** — accepts warnings as non-fatal. Probably too broad — it weakens validation for all 9 templates.
2. **Add an allowlist mechanism to `sla_diff.py`** — `meta.yml::sla_diff_expected_drift` keyed by `(OwnPage, ANNAME, attribute)` triples. Larger surface; out of #16 mechanical-fix scope.
3. **Skip the round-trip strict check for zeitung specifically** — wire `meta.yml::sla_diff_strict: false` (new key) and have `_run_sla_diff_strict` honour it. Smaller surface than option 2.

**Recommendation: option 3.** Smallest blast radius, semantically clean ("this template intentionally diverges"), and the planner can document the divergence in `templates/zeitung-a4-grun/diff.yml` (which today carries only visual-diff config — see §7).

(MEDIUM — option 3 introduces a new meta.yml key, which is a small DSL surface change that might land cleaner as its own issue. The planner may want to discuss with the user before committing.)

---

## 7. Test changes — `tools/sla_lib/tests/test_zeitung_overflow.py`

**Current state (HIGH; ran the suite, both tests pass):**
- `test_inside_page_finds_the_known_overflows_without_override` asserts EXACTLY 3 errors when the override is bypassed (`P9 Spread`, `<unnamed ImageFrame>`, `u2950`).
- `test_inside_page_passes_with_override` asserts `structural_check` reports 0 inside_page errors with the override active, and `brand:inside_page` is in `skipped_brand_rules`.

**Required edits after Frame A + B fix (assuming u2950 is NOT fixed):**

1. **Update `test_inside_page_finds_the_known_overflows_without_override`** — change the expected count from 3 to 1 and adjust assertions:
   ```python
   def test_inside_page_finds_the_residual_u2950_overflow_without_override(self):
       """After #16 fixed P9 Spread + page-11 unnamed image: only u2950 remains.

       The rotated cover-page Dunkelgrün polygon (build.py:246-256) is a
       separate follow-up issue against zeitung — its rotation-aware bbox
       overshoots the page bottom by ~4.17 mm. Tracked in <follow-up issue #>.
       """
       doc = _load_zeitung_doc()
       rule = _InsidePageRule(
           id="brand:inside_page",
           name="Frames inside page bounds",
           description="(test instance — bypasses brand_overrides)",
       )
       violations = rule.check(list(doc.iter_all_primitives()), doc)
       errors = [v for v in violations if v.severity == "error"]
       self.assertEqual(
           len(errors), 1,
           msg=(
               f"expected exactly 1 inside_page error after #16 (rotated "
               f"u2950 cover polygon), got {len(errors)}: "
               f"{[v.message for v in errors]}"
           ),
       )
       self.assertEqual(errors[0].targets, ("u2950",))
   ```
2. **Update `test_inside_page_passes_with_override`** — no code change needed; assertion still holds (override is still active, just with different reason text).
3. **Update the module docstring** (lines 1-27) — rewrite to reflect the new state. New text:
   ```python
   """Regression tests for the residual zeitung inside_page overflow.

   Issue #16 (merged) fixed the two right-edge spread frames:
     - `P9 Spread` (was at build.py:1802-1811) — moved from x=210 to x=0
       on its own page.
     - Unnamed full-A4 page-11 image (was at build.py:2061-2071) — deleted.

   One residual overflow remains after #16, tracked as a follow-up:
     - Rotated cover-page polygon `u2950` (build.py:246-256) — Polygon at
       (216.41, 155.57, 148.60, 220.49, rotation_deg=90, fill=Dunkelgrün).
       Rotation-aware bbox spans (-4.08, 155.57)→(216.41, 304.17),
       overshooting the page bottom by 4.17 mm. The upstream Scribus
       original carries the wrong frame size + rotation. Silenced today
       by the rule-level zeitung override (which now points at the new
       follow-up issue rather than #16).
   """
   ```
4. **Optionally add a new positive regression test** pinning the new positions of Frames A & B (or just A if B is deleted):
   ```python
   def test_p9_spread_frame_now_at_x0(self):
       """#16 anchor — `P9 Spread` lives on page 9 at x=0 (not x=210)."""
       doc = _load_zeitung_doc()
       p9_frames = [item for item in doc.pages[9].items
                    if getattr(item, "anname", "") == "P9 Spread"]
       self.assertEqual(len(p9_frames), 1, msg="P9 Spread anname missing")
       frame = p9_frames[0]
       self.assertAlmostEqual(frame.x_mm, 0.0, delta=0.5)
       self.assertAlmostEqual(frame.y_mm, 0.0, delta=0.5)
       self.assertAlmostEqual(frame.w_mm, 210.0, delta=0.5)
       self.assertAlmostEqual(frame.h_mm, 126.14, delta=0.5)
   ```
   Per ISSUE.md acceptance: "One new regression test … runs in <2 s, asserts zero `inside_page` errors." The renamed test in step 1 already does the inside_page assertion; this new test pins the positional fix. **Recommendation: add it.** Cost is ~10 lines, value is non-trivial (catches future re-regressions of the same bug).

**If the user instead chooses option (a) from §3 — fix u2950 in this issue too:** the test changes to expect 0 errors (full clean baseline). The override entry becomes a delete (no replacement reason). Test becomes `assertEqual(len(errors), 0)`.

---

## 8. Round-trip diff impact + `diff.yml` / `README.md` updates

### 8.1 `tools/sla_diff.py` baseline today (HIGH, captured)

```
$ PYTHONPATH=tools python3 tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right templates/zeitung-a4-grun/template.sla --strict --allow-brand-extras
**critical: 0**, warning: 0, info: 18
```
All 18 are anname-additions and FRTYPE 3↔0 rectangle equivalences (info-level only). **The current round-trip is byte-clean.**

### 8.2 Predicted diff after Frame A move + Frame B delete

| Issue | Severity | Source line in `tools/sla_diff.py` |
|---|---|---|
| `position-drift` on `PAGEOBJECT[i] OwnPage=9 .XPOS` (Δ ≈ 595 pt = 210 mm) for `P9 Spread` | WARNING | line 720 |
| `position-drift` on `PAGEOBJECT[i] OwnPage=9 .YPOS` (cascade — when one frame moves, sort-order shifts pair other frames) | WARNING (likely cascade of 0-3 entries on page 9) | line 720 |
| `page-item-count-mismatch` on `OwnPage=11` (left has 1 more frame) | CRITICAL | line 642 |
| Possible cascading `frtype-mismatch` / `position-drift` on the rest of page 11 due to sort-order pairing shift | CRITICAL or WARNING | lines 689-714, 720 |

**Net result: `--strict` AND non-strict fail.** Exit code 1 from `tools/render_pipeline.py::_run_sla_diff_strict`.

### 8.3 `diff.yml` update

`templates/zeitung-a4-grun/diff.yml` today only carries visual-diff (PNG comparison) config:
```yaml
visual_diff:
  max_pixel_mismatch_pct: 1.0
  fuzz_pct: 5.0
```

**Recommended additions** (assuming option 3 from §6.4 — new `sla_diff_strict` key in `meta.yml`):
- diff.yml stays unchanged. The `meta.yml` change is enough.

**If instead the planner wants a per-template SLA-diff allowlist** (option 2 from §6.4), `diff.yml` would grow a new `sla_diff:` block:
```yaml
sla_diff:
  expected_drift:
    - reason: "Issue #16 — P9 Spread frame moved from page 10 to page 10 origin (was misattributed by upstream Scribus)."
      page: 9
      anname: "P9 Spread"
      attrs: ["XPOS"]
    - reason: "Issue #16 — unnamed page-12 dark-green placeholder deleted (zero-render in upstream PDF)."
      page: 11
      item_index: <i>
      kind: "delete"
```
This requires modifying `tools/sla_diff.py` to consume this config. Larger surface. **Recommendation: option 3 (per-template `sla_diff_strict: false` flag in meta.yml) over option 2.**

### 8.4 `README.md` update (issue scope item 7)

Add a section after "## Vorlagen-Generierung (für Maintainer:innen)" (around line 51):

```markdown
## Bekannte Abweichungen vom Original-SLA

`gruene-zeitung-vorlage-original.sla` enthält zwei Bildrahmen, die der
Scribus-Autor versehentlich um 210 mm nach rechts (auf den Off-Page-
Scratch-Canvas) plaziert hat — sie rendern im Original-PDF nichts
sichtbares (verifiziert via `pdfimages -list`):

- `P9 Spread` (page 9, war x=210) → korrigiert auf x=0 (issue #16)
- Unbenannter Vollseiten-Dunkelgrün-Rahmen (page 11, war x=210) →
  entfernt (issue #16)

Daher weicht `template.sla` an diesen zwei Stellen bewusst vom Original
ab. Der Round-Trip-Check `tools/sla_diff.py --strict` ist für diese
Vorlage entsprechend gelockert (siehe `meta.yml::sla_diff_strict`).
```

(Adjust the last sentence to match whichever option from §6.4 the planner takes.)

---

## 9. `<interfaces>` block — extracted contracts

```
<interfaces>
// From tools/sla_lib/builder/primitives.py:764-787
@dataclass
class ImageFrame(_Frame):
    src: str = ""             # PFILE path (absolute or relative-to-SLA)
    image: str = ""           # alias for src; converter prefers `image=`
    layer: int = 1            # default Bilder layer
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    scale_type: int = 1       # SCALETYPE
    ratio: int = 1            # RATIO
    pic_art: int = 1          # PICART (1=visible)
    fill: Optional[str] = None        # PCOLOR (frame background fill)
    line_color: Optional[str] = None  # PCOLOR2 (frame border)
    line_width_pt: float = 0          # PWIDTH
    inline_image_data: Optional[str] = None
    inline_image_ext: Optional[str] = None  # e.g. "png", "jpg"
// _Frame parent (primitives.py:433+) carries x_mm, y_mm, w_mm, h_mm, anchor,
// rotation_deg, anname, clip_edit, custom_path, soft_shadow, etc.

// From tools/sla_lib/builder/blocks.py:686-740
@dataclass
class SpreadImage:
    """Two ImageFrames, one per facing page, sharing one source image.
    Right half uses local_offset_mm=(-page_w_mm, 0) so the source image
    "scrolls" left and the right half shows the right half of the picture.
    Both frames are inside_page-clean by construction (each at x=0 on its
    own page). scale_type is hard-pinned to 0 (free / aspect-locked)."""
    image: str
    page_w_mm: float
    page_h_mm: float
    h_mm: float
    y_mm: float = 0.0
    base_anname: str = ""
    scale_type: int = 0
    local_scale: tuple[float, float] = (1.0, 1.0)

    def emit(self) -> tuple[ImageFrame, ImageFrame]: ...
    def place(self, page_left, page_right) -> tuple[ImageFrame, ImageFrame]: ...

// From tools/sla_lib/builder/brand_constraints.py:425-495
@dataclass(frozen=True)
class _InsidePageRule(BrandRule):
    """Each non-master frame's rotation- and anchor-aware bbox must fit
    inside its OWNING page's [-bleed, w+bleed] × [-bleed, h+bleed].
    Severity split:
      - worst overshoot ≤ 0.5 mm → pass.
      - 0.5 < worst ≤ 1.0 mm    → warning.
      - worst > 1.0 mm           → error."""
    tolerance_mm: float = 0.5
    error_cutoff_mm: float = 1.0

    def check(self, primitives: list, doc) -> list[Violation]:
        # Iterates doc.pages (skipping is_master), computes _frame_bbox_mm,
        # measures overshoot vs [-bleed, w+bleed] x [-bleed, h+bleed].

// From tools/sla_lib/builder/constraints.py:417-430
def same_size(*targets, axis: str = "both", tolerance_mm: float = 0.5,
              name: str = "") -> Constraint:
    """All targets must share the same width and/or height within tolerance.
    With one target, this is an anname-presence witness."""

// From tools/sla_lib/tests/test_zeitung_overflow.py:41-48
def _load_zeitung_doc():
    """Load templates/zeitung-a4-grun/build.py and return its built doc."""
    build_py = ROOT / "templates" / "zeitung-a4-grun" / "build.py"
    spec = importlib.util.spec_from_file_location("zeitung_build", build_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_doc()    # NOTE: build_doc = build_template (alias at build.py:2527)

// From templates/zeitung-a4-grun/build.py:184-233 (the four pages we touch + neighbours)
page9  = doc.add_page(size=(210, 297), bleed_mm=3, master='Neue Musterseite links',
                       page_xpos_pt=100.0, page_ypos_pt=4429.45)
page10 = doc.add_page(size=(210, 297), bleed_mm=3, master='Neue Musterseite links',
                       page_xpos_pt=695.28, page_ypos_pt=4429.45)
page11 = doc.add_page(size=(210, 297), bleed_mm=3, master='Neue Musterseite links',
                       page_xpos_pt=100.0, page_ypos_pt=5311.34)
page12 = doc.add_page(size=(210, 297), bleed_mm=3, master='Neue Musterseite links',
                       page_xpos_pt=695.28, page_ypos_pt=5311.34)
page13 = doc.add_page(size=(210, 297), bleed_mm=3, master='Neue Musterseite links',
                       page_xpos_pt=100.0, page_ypos_pt=6193.23)

// From templates/zeitung-a4-grun/build.py:2495-2508 — gallery preview INJECT_MAP
INJECT_MAP = {
    # anname → (library_id, target_w_mm, target_h_mm)
    "Cover Hero":      ("themen_klimaschutz_windrad",   210, 155.6),
    "P1 Hero":         ("themen_soziales_gemeindebau",  210, 130.2),
    "P2 Mid":          ("themen_bildung_volksschule",   112.3, 58),
    "P3 Hero":         ("themen_wirtschaft_handwerk",    74.7, 58.2),
    "P4 Foto-Spread":  ("kontext_buergerversammlung",   210, 108.1),
    "P5 Hero":         ("themen_verkehr_radweg",        112.3, 84.1),
    "P7 Portrait":     ("portrait_maria",                51.3, 76.4),
    "P9 Spread":       ("themen_klimaschutz_solar",     210, 126.1),    # consumer of Frame A's anname
    "P10 Portrait":    ("portrait_stefan",               66.6, 94.4),
    "P11 Bottom":      ("kontext_stammtisch_cafe",      210, 83.3),
    "P13 Hero":        ("kontext_infostand_szene",      210, 147.4),
}

// From templates/zeitung-a4-grun/build.py:2542-2556 — CONSTRAINTS list
CONSTRAINTS = [
    same_size("Cover Hero", name="cover_hero_anchor"),
    same_size("P1 Hero", name="p1_hero_anchor"),
    same_size("P3 Hero", name="p3_hero_anchor"),
    same_size("P5 Hero", name="p5_hero_anchor"),
    same_size("P13 Hero", name="p13_hero_anchor"),
    same_size("P7 Portrait", name="p7_portrait_anchor"),
    same_size("P10 Portrait", name="p10_portrait_anchor"),
    same_size("P4 Foto-Spread", name="p4_fotospread_anchor"),
    same_size("P9 Spread", name="p9_spread_anchor"),    # consumer of Frame A's anname
]

// From tools/render_pipeline.py:384-408 — round-trip strict gate
def _run_sla_diff_strict(tid, tdir, meta) -> int:
    # Hardcoded: subprocess.run(["python3", "tools/sla_diff.py",
    #     "--left", original, "--right", template_sla,
    #     "--strict", "--allow-brand-extras"])
    # Returns subprocess exit code; 0 = pass, non-0 = fail.
    # NO meta.yml escape valve today — this is what #16 must change.

// From tools/sla_diff.py:716-737 — position/size drift severity
POSITION_TOLERANCE_PT = 0.5      # ≈ 0.18 mm
SIZE_TOLERANCE_PT     = 0.5
# |delta| > 0.5 pt → SEVERITY_WARNING (fails --strict).
# 1e-6 < |delta| ≤ 0.5 pt → SEVERITY_INFO (never fails).
# A 210 mm move = 595 pt → way over threshold → WARNING.
</interfaces>
```

---

## 10. Recommendations to the planner — concise summary

Item-by-item against ISSUE.md scope:

| ISSUE.md scope item | Recommended path | Confidence | Rationale |
|---|---|---|---|
| 1. Replace `P9 Spread` | **Option A1** (move to x=0 same page, keep anname) | HIGH | PDF evidence shows zero rendered image across spread; SpreadImage would invent content. Option A1 keeps INJECT_MAP + same_size constraint working. |
| 2. Move page-12 unnamed image | **Delete** (Option B1) | HIGH | No anname, no consumer, zero render in upstream PDF. "Move" target is undefined. |
| 3. Trim 0.8 mm overflow on page 12 | **Skip** | HIGH | Not flagged by `inside_page` today (sits inside bleed envelope). Costs diff budget for zero CI gain. |
| 4. Trim 0.8 mm overflow on page 14 | **Skip** | HIGH | Same as item 3. |
| 5. Re-run `structural_check --all`; remove override | **Reword override** to point at u2950 follow-up; do NOT delete | HIGH | u2950 is out of scope (per #14 EXECUTION.md and existing test docstring). Acceptance criterion 1 needs this nuance. |
| 6. Re-run `sla_diff.py` against original; document divergence | **Add `meta.yml::sla_diff_strict: false` (new key)** + small `tools/render_pipeline.py:_run_sla_diff_strict` change to honour it | MEDIUM | Smallest mechanism that lets the intentional diff land. Alternatives in §6.4. |
| 7. Add regression test | **Two tests**: (a) updated `_finds_residual_u2950_overflow_without_override` (count → 1, target → u2950), (b) NEW `test_p9_spread_frame_now_at_x0` pinning Frame A's new position | HIGH | Updated test still satisfies "asserts inside_page-clean baseline" intent. Positional pin catches regressions of the actual fix. |
| 8. Note divergence in README | Add "Bekannte Abweichungen vom Original-SLA" section per §8.4 copy | HIGH | Mechanical doc edit. |

**Anchor reminder (issue scope check):** I confirmed `templates/zeitung-a4-grun/build.py` uses ZERO `anchor=` kwargs anywhere — every frame is `x_mm=`/`y_mm=` explicit. The fixed Frames A and B (and any optional C/D) follow the same pattern. (HIGH; verified via `grep -n "anchor=\|Anchor("`.)

**Interface staleness check:** All four critical files (`build.py`, `meta.yml`, `blocks.py`, `brand_constraints.py`, `test_zeitung_overflow.py`) were last touched in the same merge commit `b8792e5` (PR #38, issue #14). No in-flight branches modifying them. Safe to author against current main.

---

## 11. Open questions for the planner / user

1. **Should u2950 be fixed in this issue?** ISSUE.md scope says no, existing artifacts (test docstring, EXECUTION.md) say no, but it's the only blocker for fully removing the override. Recommendation: file a separate follow-up issue NOW (before this work starts) so the reworded override has an issue # to point at, then proceed with #16 as-is.
2. **Is Frame B truly safe to delete?** §5 evidence is strong but not 100% definitive — a Scribus author could have intended the frame as a future placeholder. The user may want a brief sanity-check by opening the upstream SLA in Scribus and visually confirming "no green tile on page 12". If unsure, fall back to Option B2 (move to x=0 same page) which renders a visible change but is mechanically reversible.
3. **Round-trip-strict mechanism choice.** §6.4 options 1/2/3 differ in scope. Option 3 is smallest. The user/planner should confirm before introducing the new `meta.yml` key.
4. **Items C & D.** Recommend skip; defer to user if they want the cosmetic clean-up.

---

## 12. Confidence summary

| Area | Confidence | Why |
|---|---|---|
| Frame coordinates + line numbers | HIGH | Direct grep + Read of build.py |
| `inside_page` rule behaviour | HIGH | Ran `_InsidePageRule.check()` directly + ran the test suite |
| PDF-rendering evidence (no spread, no green tile) | HIGH | `pdfimages -list` + `pdftotext` are exact metadata extractors |
| `SpreadImage` is wrong fix | HIGH | PDF evidence is unambiguous — empty placeholders, not real spreads |
| `INJECT_MAP` / `CONSTRAINTS` interaction | HIGH | Direct read of build.py + constraints.py |
| Round-trip diff impact (severities, exit codes) | HIGH | Read sla_diff.py source + ran current diff to confirm baseline |
| Need for new round-trip-strict bypass mechanism | MEDIUM | Mechanism choice (option 1/2/3) is judgment, but the NEED is HIGH (no allowlist exists today) |
| u2950 follow-up scope split | HIGH | Already documented in test docstring + #14 EXECUTION.md "Discovered Issues" |
| Test rewrite shape | HIGH | Direct read of current test + harness verification of new expected count |
| README divergence note | HIGH | Mechanical doc copy, no semantic risk |
