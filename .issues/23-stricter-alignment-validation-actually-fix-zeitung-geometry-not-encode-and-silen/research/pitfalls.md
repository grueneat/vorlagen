# Research: Pitfalls dimension for issue 23

**Researched:** 2026-05-09
**Issue:** 23-stricter-alignment-validation-actually-fix-zeitung-geometry-not-encode-and-silen
**Author:** pitfalls specialist (sub-agent)

## Method

All findings below were verified against the live worktree at
`/root/workspace/.worktrees/23-…/` by:

- Reading source files directly (not relying on issue-summary text).
- Running the existing `tools/audit_alignment.py` and a synthetic
  bleed-coverage / image-text-overlap probe with proposed parameters,
  to count real violations on each existing template.
- Loading each template's `build.py` via the production
  `template_loader.load_build_module()` and walking
  `doc.iter_all_primitives()` with the same `bbox.frame_bbox_mm()`
  helper the planned rules will use. No simulation, no assumption.

Numbers in this report are the actual counts that the planner can use
to size the work and to pre-decide which templates need
`brand_overrides` entries before Phase 1 lands.

---

## Section A — Pitfalls validated against code

### A1. Encode-and-silence escape hatch is real but partially intractable

**Confirmed.** The `_AlignedBelowConstraint.check()` at
`tools/sla_lib/builder/constraints.py:319-357` errors out only when
`abs(below.y_mm - expected_y) > self.tolerance_mm`. The escape patterns
the executor used in #22 are:

1. **Match the actual gap exactly.**
   `aligned_below("u918", "Kopie von u2d5c (9)", gap_mm=4.00)` —
   actual: u918 at y=195, `Kopie von u2d5c (9)` ends at y=191.0, gap=4.0
   exactly. Constraint passes; `_UndeclaredDriftRule` skips because the
   pair is in `declared`.
2. **Widen `tolerance_mm`.** `same_y("u1529","u1544",tolerance_mm=4.0)`
   on page 4 declares "these baselines should match within 4 mm" because
   actual drift was 3.6 mm. There are 8 such widened-tolerance entries
   in zeitung CONSTRAINTS today (search: `tolerance_mm=` at
   `templates/zeitung-a4-grun/build.py:2656,2668,2693-2710,2719-2725`).

**Implication for Phase 1's "constraint declaration disagrees with
actual geometry by N mm" warning:** that warning is logically
unreachable for `_AlignedBelowConstraint` and `_SameAxisConstraint`
because they ALREADY error on tolerance breach — so the executor
never declares a "wrong" gap, they declare the actual measured gap.
The issue's framing is half right. To detect lazy declarations the
planner has two real options:

- **(a)** Add a separate audit-only finding: "constraint declaration
  with `tolerance_mm > 1.0 mm` is suspicious; investigate whether the
  geometry can be tightened." This lives in `audit_alignment.py`
  (`--strict` mode), not as a brand rule.
- **(b)** Geometric-outcome tests (Phase 3) — pin the FRAME positions
  directly, bypassing CONSTRAINTS. If the geometry is sloppy, the test
  fails regardless of how the CONSTRAINTS list is written.

Recommendation: **both**. (a) is a 10-line change in `_audit_doc()`;
(b) is the actual safety net.

### A2. `brand:bleed_coverage` `w > 0.7 × page_w` heuristic is FAR too loose

**Confirmed by enumeration.** With `0.7 × page_w` (=147 mm on A4) the
rule matches **29 frames in zeitung-a4-grun**. Of those 29 only 10 are
the actual outer-bleed-gap bugs. The other 19 are body-text frames at
x=20, w=170 (=81 % of page width) — they are at the 20 mm body
margin, intentionally inset on **both** sides. Examples:

- 12 unnamed text frames at `(x=20, y=20, w=170, h=28)` — page header
  region.
- u918 (page 8 Dunkelgrün card) at `(x=20, y=195, w=170, h=82)`.

With `w > 0.95 × page_w` (=199 mm on A4) the rule matches exactly the
**10 real bugs**:

```
page=1 rechts: 'Cover Hero'        bbox=(0.0, 0.0, 210.0, 155.6)
page=2 links: 'P1 Hero'           bbox=(0.0, 0.0, 207.0, 130.2)
page=5 rechts: 'P4 Foto-Spread'   bbox=(3.0, 188.9, 210.0, 297.0)
page=10 links: 'P9 Spread · left' bbox=(0.0, 0.0, 210.0, 126.1)
page=11 rechts: 'P9 Spread · right' bbox=(0.0, 0.0, 210.0, 126.1)
page=12 links: '<unnamed>'        bbox=(0.0, -0.2, 207.0, 213.7)
page=12 links: 'P11 Bottom'       bbox=(0.0, 213.7, 207.0, 297.0)
page=13 rechts: '<unnamed>'       bbox=(3.0, -0.2, 210.0, 297.0)
page=14 links: 'P13 Hero'         bbox=(0.0, 149.6, 207.0, 297.0)
page=14 links: '<unnamed>'        bbox=(0.0, -0.2, 207.0, 152.4)
```

**Recommendation to planner:** change the rule's "full-width" cutoff
from `0.7 × page_w` to `0.95 × page_w` (or `(page_w − 11 mm)` so that
A4-margin (=20 mm) inset frames never qualify). Document the cutoff in
the rule's docstring with the count of false-positives the loose
threshold would have surfaced.

This also dissolves pitfall #2 (per-frame `(no-bleed)` exemption tag) —
with the tighter cutoff, **u918 is no longer flagged** so no exemption
is needed. Strongly prefer this over inventing a new anname-suffix
convention.

### A3. `brand:image_text_overlap` scope is too narrow — misses the actual page-10 bug

**Confirmed.** The page-10 bug (issue text §"Page 10") is a partial
overlap of `Polygon(Dunkelgrün) Kopie von u1529` with two TextFrames
(`Kopie von u2d5c (13)`, `Kopie von u2da1 (16)`), each at 63 %
overlap. The proposed rule scope `(ImageFrame, TextFrame)` does not
fire because `Kopie von u1529` is a Polygon, not an ImageFrame.

Enumerating across all 8 templates with rotation-skip (skip pairs
where either frame has `rotation_deg != 0`) and the
`overlap_ratio = intersection / min(area_A, area_B)` formula in
`(0.05, 0.95)`:

| template                     | ImageFrame×Text | filled-Polygon×Text |
|------------------------------|-----------------|---------------------|
| zeitung-a4-grun              | 3               | 5                   |
| postkarte-a6-kampagne        | 3               | (not measured)      |
| plakat-a1-hochformat         | 3               | (not measured)      |
| infostand-tent-card-a5-quer  | 1               | (not measured)      |
| wahlaufruf-postkarte-a6-quer | 0               | —                   |
| kandidat-falzflyer-din-lang  | 0               | —                   |
| wahltag-tueranhaenger        | 0               | —                   |
| themen-plakat-a3-quer        | 0               | —                   |

The 5 zeitung Polygon×Text overlaps (full data from probe):

```
page1 : Polygon(Magenta)    '<unnamed>'        ↔ Text 'u2989'                 ratio=53%
page7 : Polygon(Dunkelgrün) 'u6ad'             ↔ Text '<unnamed>'             ratio=26%
page9 : Polygon(Dunkelgrün) 'Kopie von u6ad'   ↔ Text '<unnamed>'             ratio=22%
page10: Polygon(Dunkelgrün) 'Kopie von u1529'  ↔ Text 'Kopie von u2d5c (13)'  ratio=63%
page10: Polygon(Dunkelgrün) 'Kopie von u1529'  ↔ Text 'Kopie von u2da1 (16)'  ratio=63%
```

**Recommendation to planner:** widen the rule scope to
`(ImageFrame | filled Polygon, TextFrame)`. "Filled" = `fill not in
("None", "", None)` — excludes outline-only polygons (rare).

**Side effect:** Pages 12-13 of zeitung have a full-bleed Dunkelgrün
polygon backing the entire page (white text on green). All text on
those pages overlaps the polygon at near-100 % ratio, which falls in
the `> 0.95` "fully-contained" allowed band — they are NOT flagged.
Verified by inspection; the rule's contained-allowance correctly
classifies them as caption-on-image.

The 3 ImageFrame×Text cases on **postkarte / plakat / infostand** are
likely intentional captions; the planner must decide:

- Either pre-apply `brand_overrides[brand:image_text_overlap]` for
  those templates with `reason: "caption-on-photo by design"`, OR
- Tighten the "fully-contained" cutoff from 0.95 to ~0.85 so that
  postkarte's 91 % overlap (P1 Hero ↔ unnamed text) classifies as
  "contained" rather than "partial". Examined cases are at:
  - `postkarte-a6-kampagne` page 1: P1 Hero ↔ unnamed (91 %), small
    decorative ↔ small text (16 %), and small ↔ small (20 %).
  - `plakat-a1-hochformat` page 1: three frame pairs (77 %, 19 %,
    8 %).
  - `infostand-tent-card-a5-quer` page 1: rotated Logo Grüne (panel B)
    ↔ rotated Headline Panel B (63 %).

Recommendation: **keep 0.05/0.95 thresholds** and pre-apply
`brand_overrides` for the 3 affected templates. Justification: a 91 %
overlap with caption text bleeding outside the photo IS visually
sloppy and worth flagging for review even on postkarte. Deferring is
cheaper than re-tuning.

**Rotation pitfall:** the `infostand` case has both frames rotated
180°. The new rule MUST skip rotated frames (or use rotated bbox
honestly) — the current `_UndeclaredDriftRule` skips them at
`brand_constraints.py:665-667`; the new rule should mirror that.
`bbox.frame_bbox_mm()` already returns the rotated bbox correctly
(verified at `bbox.py:73-74`), so a simpler approach is to just use
the bbox without skipping — the AABB after rotation is correct.

### A4. `brand:cover_extent_match` is correctly narrow — only one pair flagged on zeitung

**Confirmed by enumeration.** With "vertically touching" defined as
`|A.bottom - B.top| < 0.5 mm`, the rule fires exactly **once** on
zeitung-a4-grun (the documented Cover Hero ↔ u2950 mismatch):

```
page1: 'Cover Hero' (x: 0.0..210.0) ↔ 'u2950' (x: -3.0..213.0)
```

P11 Bottom ↔ Dunkelgrün-band on page 12 OVERLAP by 0.18 mm rather than
TOUCH, so the rule (correctly) does not fire on them. Pitfall #4
(over-triggering) is **not realized in practice** with the proposed
"both frames must be `w > 0.7 × page_w` AND vertically touching"
gate.

Recommendation: keep the rule as proposed. Tightening the
full-width cutoff to `0.95 × page_w` (per A2) does not affect the one
real catch — both Cover Hero (100 %) and u2950 (102 %) qualify.

### A5. Rule rename `brand:undeclared_alignment_drift` → `brand:visual_adjacency_drift`

**No template currently lists `brand:undeclared_alignment_drift` in
its `brand_overrides`.** Verified by `grep -rn brand_overrides
templates/` and inspecting all 8 meta.yml files — the only override in
use is `brand:line_spacing_0.9`. So pitfall #5's concern about updating
existing per-template overrides is **moot for templates**.

The rename DOES require updating:

- `tools/sla_lib/tests/test_brand_constraints.py:54` — hard-coded
  `assertEqual(len(BRAND_CONSTRAINTS), 11)` (still 11 if we replace,
  not add).
- `tools/sla_lib/tests/test_brand_constraints.py:69` — `expected = {…
  "brand:undeclared_alignment_drift" …}` set literal.
- `tools/sla_lib/tests/test_brand_constraints.py:29` — import of
  `_UndeclaredDriftRule`.
- `tools/sla_lib/tests/test_brand_undeclared_drift.py` — entire file
  uses the rule id; rename to `test_brand_visual_adjacency_drift.py`
  and update 11 occurrences of the id.
- `tools/sla_lib/tests/test_zeitung_overflow.py:107,19` — uses both
  the class name AND the id.
- `tools/audit_alignment.py:152` — comment references
  `_UndeclaredDriftRule` (cosmetic).
- `tools/sla_lib/builder/brand_constraints.py:71,592,786` — class,
  module-level comment, registry entry.
- `shared/brand/SPEC-WRITING-GUIDE.md:250,261` — documentation.

Recommend **rename the class** as well (`_UndeclaredDriftRule` →
`_VisualAdjacencyDriftRule`) for consistency. **All edits in one
atomic commit** so the test suite never sees a half-rename.

### A6. Pinning frame coordinates makes tests brittle — prefer invariants

**Confirmed.** ISSUE.md Phase 3 asks for `pin specific (x, y, w, h) for
the 11 detected outer-bleed-gap frames`. This is brittle in three
ways:

1. **Frame positions are float-imprecise.** Cover Hero has
   `w_mm=209.9999999999361` from SLA round-trip (`build.py:240`).
   Pinning `w_mm == 216.0` exactly will fail; the test must use
   `assertAlmostEqual(places=1)` or similar.
2. **Round-trip drift from regenerating build.py from upstream SLA.**
   The build.py was originally auto-generated from
   `gruene-zeitung-vorlage-original.sla` via `tools/sla_to_dsl.py`. If
   anyone regenerates it (e.g. for an upstream upstream-SLA change),
   coordinate pinning needs re-tuning. Not a concern today (zeitung is
   `sla_diff_strict: false`, see `meta.yml:20`) but worth a comment.
3. **Future legitimate edits** (Phase 4 itself!) become awkward to
   review — every test must be updated alongside the geometry.

**Recommendation:** pin **invariants**, not coordinates. For
the 10 outer-bleed-gap frames, the invariant is:

```python
def assert_outer_bleed(frame, page_w_mm, side):
    bb = frame_bbox_mm(frame, page)  # rotation-aware
    if side == "left":   assertAlmostEqual(bb[0], -3.0, places=1)
    if side == "right":  assertAlmostEqual(bb[2], page_w_mm + 3.0, places=1)
    if side == "both":   # cover, no spine
        assertAlmostEqual(bb[0], -3.0, places=1)
        assertAlmostEqual(bb[2], page_w_mm + 3.0, places=1)
```

For Cover Hero ↔ u2950: pin **`bb_cover[0] == bb_u2950[0]` and
`bb_cover[2] == bb_u2950[2]`** (same outer extents). Geometry can
shift to (-3, 213) or (-4, 214) or whatever the brand team prefers;
the invariant holds.

For Page-8 P7 Portrait ↔ u918: pin **`bb_portrait[2] == bb_u918[2]`
within 0.5 mm** (right edges aligned) and
**`bb_portrait[1] == bb_u918[1]` within 0.5 mm** (top edges aligned).

For Page-10 text columns ↔ green card: pin
**`bb_text[3] <= bb_card[1] + 0.5`** (text bottom is at-or-above card
top) AND `_PolygonImageOverlapRule` reports zero violations on this
pair.

This style of test is robust to any geometry edit that preserves the
INTENT, and only fails when the intent is broken. ACCEPTANCE
CRITERION still satisfiable with this style.

### A7. Phase ordering matters — wrong order = `--all` red mid-PR

**Confirmed.** ISSUE.md lists 7 phases. The dependency analysis for
atomic-commit ordering:

| step | why before next                                               |
|------|--------------------------------------------------------------|
| Phase 1 (rules)             | new rule classes + registry, no behavior change yet           |
| Phase 1 + Phase 6 overrides | new ERROR rules surface on postkarte/plakat — overrides MUST be in same commit as the rules, otherwise structural_check exits 1 |
| Phase 2 (audit thresholds)  | independent of everything; tightens informational tool        |
| Phase 5 (drop CONSTRAINTS)  | re-surfaces drift warnings — requires Phase 4 to silence them naturally |
| Phase 4 (geometry fix)      | actually moves frames; may break visual diff (sla_diff_strict=false saves us) but DOES bump previews_for_sla SHA |
| Phase 3 (geometric tests)   | MUST land AFTER Phase 4 — tests fail if geometry not yet fixed |
| Phase 7 (CI tweak)          | trivial; optional tail commit                                 |

Concretely the planner should sequence the tasks as:

1. T01 — add 3 new rules + replace drift rule (Phase 1) + pre-apply
   `brand_overrides` for postkarte/plakat/infostand (Phase 6
   `image_text_overlap` overrides) → atomic commit.
   `python3 -m sla_lib.builder.structural_check --all` exits 0.
2. T02 — audit-tool thresholds + `--strict` (Phase 2). Independent;
   commit alone.
3. T03 — Zeitung geometry fix (Phase 4) + drop encode-and-silence
   CONSTRAINTS (Phase 5). Atomic — geometry edits and CONSTRAINTS
   removal must coincide; otherwise structural_check between commits
   sees inconsistent state.
4. T04 — Geometric-outcome tests (Phase 3). After T03; tests now pass.
5. T05 — `bin/render-gallery zeitung-a4-grun` to regenerate
   `template.sla` + bump `previews_for_sla` SHA in `meta.yml` + mirror
   to `site/public/templates/zeitung-a4-grun/template.sla`. Without
   this, `bin/check-stale-previews` exits 1.
6. T06 — Phase 7 CI tweak (no-op informational stays informational).

**Pitfall:** within each task the order of edits matters — for T01,
add the new rule classes BEFORE the registry entry, otherwise import
fails. Standard Python module hygiene; planner should call this out.

### A8. SpreadImage outer-bleed extension is non-trivial

**Confirmed.** `SpreadImage.emit()` at
`tools/sla_lib/builder/blocks.py:714-733` produces:

- LEFT half: `x=0, w=page_w_mm, local_offset_mm=(0, 0)`
- RIGHT half: `x=0, w=page_w_mm, local_offset_mm=(-page_w_mm, 0)`

The right half's negative offset shifts the (page_w * 2)-wide source
image leftward so the right page shows the right portion. The math
assumes the source-image native width fits exactly `2 × page_w`.

**ISSUE.md Phase 4 asks:** "P9 Spread halves — each `(x=0, w=210)` —
extend outer edges. LEFT half: `(x=-3, w=213)`; RIGHT half:
`(x=0, w=213)` with the right edge in bleed."

If LEFT half becomes `(x=-3, w=213)` and RIGHT half becomes
`(x=0, w=213)` — the source image scroll for the right half should
**still** be `local_offset_mm=(-page_w_mm, 0)` ONLY IF the source
image is positioned at frame-local origin (0,0) on each half. With
`local_offset_mm=(0,0)` on LEFT and the LEFT frame extending to
x=-3 on its page, the source image's left edge sits at frame-local
(0,0) which is page-local (-3,0). So the source image is anchored
at (-3, 0) on the LEFT page. Its right edge is then at
(-3 + 2*page_w) = (-3 + 420) = 417 in continuous-spread coordinates,
which is the start of the bleed area on the RIGHT page (page_w + 3).

For the RIGHT half to display the remaining portion correctly, its
`local_offset_mm` must satisfy: source image's frame-local origin
shifted left by `(page_w + 3)` so the visible portion starts at
page_w in continuous coords. The math:

- Native source width assumption: `2 * page_w` mm.
- LEFT half: source origin at frame-local (0, 0) → source-image x
  range visible: 0 .. 213 (frame width). The picture's "page_w"-mark
  is at source-x = page_w = 210, which sits at frame-local x = 210
  = page-local x = 207 = 3 mm before LEFT frame's right edge at 210.
- For continuous spread: the source position at LEFT-frame's right
  edge (page-local x=210) is source-x = 213. The RIGHT page's left
  edge (page-local x=0) should display source-x = 213. So RIGHT
  half's `local_offset_mm.x` should be `-(page_w + 3) = -213` (not
  `-page_w = -210`).

**Recommendation:** update `SpreadImage` to take an optional
`outer_bleed_mm` parameter (default 0), and in
`templates/zeitung-a4-grun/build.py` instantiate with
`outer_bleed_mm=3.0`. The `emit()` math becomes:

```python
left  = ImageFrame(x_mm=-outer_bleed_mm,       y_mm=y_mm, w_mm=page_w_mm + outer_bleed_mm,  ...)
right = ImageFrame(x_mm=0,                     y_mm=y_mm, w_mm=page_w_mm + outer_bleed_mm,  ...,
                   local_offset_mm=(-(page_w_mm + outer_bleed_mm), 0))
```

The page-10/-11 (own_page=9/10) build.py block at lines 1845-1852
needs updating accordingly.

**Verification:** after T03, run `bin/render-gallery
zeitung-a4-grun --skip-visual-diff` and visually inspect
`page-10.png` + `page-11.png` for spread continuity. If the seam at
the spine is broken, the offset math is wrong — adjust `outer_bleed_mm`
accumulation.

### A9. Page-1 Cover semantics — RIGHT-alone, no facing LEFT

**Confirmed.** `tools/sla_lib/builder/document.py:376-378` and
`brand_constraints.py:514-520` both special-case `own_page == 0` for
facing-pages docs. The cover stands alone in the right column with no
facing left page.

For `brand:bleed_coverage`: the cover has BOTH outer edges (left and
right) — no spine. Cover Hero must extend to `(-3, page_w + 3)`
=`(-3, 213)`, NOT just `(-3, 210)`. The issue's Phase 4 already
states: "Page 1 Cover Hero: (x=0, w=210) → (x=-3, w=216) (full-bleed
match with u2950)" — which is exactly `(-3, +3 = 213)` extent.
**Verified the math is correct.** w=216 → x_extent = (-3, 213). ✓

**Pitfall to call out in plan:** the `bleed_coverage` rule's
side-detection (LEFT vs RIGHT via master_name regex) must skip
own_page=0 and treat both edges as outer. Mirror the
`_SpineSafetyRule.check()` pattern at `brand_constraints.py:519-520`.

### A10. Right-edge axis-alignment isn't checked by current
`_UndeclaredDriftRule`

**Confirmed by code inspection.** `_UndeclaredDriftRule.check()` at
`brand_constraints.py:629-692` only checks `dx = abs(px0 - qx0)` and
`dy = abs(py0 - qy0)` — i.e. left/top edges. The page-8 bug (P7
Portrait at x_right=186.6 vs u918 at x_right=190, drift 3.4 mm) is
invisible to the heuristic because their LEFT edges are at x=135.3
and x=20 respectively (drift 115 mm — far above any tolerance).

**Recommendation to planner:** the new
`_VisualAdjacencyDriftRule.check()` should ALSO test:

- `dx_right = abs(px1 - qx1)` (right-edge alignment)
- `dy_bottom = abs(py1 - qy1)` (bottom-edge alignment)

Otherwise the rename buys broader thresholds but still misses the
exact bug class the issue calls out.

### A11. Broader thresholds explode false-positive count on every template

**Verified.** Audit run on each template with proposed
`--axis-tol-mm 25 --adjacency-tol-mm 30`:

| template                     | suspicious-pairs (5/12 default) | suspicious-pairs (25/30 proposed) |
|------------------------------|---------------------------------|-----------------------------------|
| zeitung-a4-grun (output lines proxy) | 70 | 179 |
| wahlaufruf-postkarte-a6-quer | (low)                           | 38 just on the 2 pages (sample)   |

The 5x volume increase makes the audit report essentially noise —
margin-vs-body-vs-page-number frames are 8.5/11.5/13 mm apart, all in
the 0.5–25 mm range. Each will produce a "suggested same_x" stub.

**Mitigation choices:**

- (a) Pre-apply `brand_overrides[brand:visual_adjacency_drift]` for
  every existing template at the time of #23 landing, with reason
  "audited at time of #23 — re-enable in follow-up". Loses signal.
- (b) Keep severity=warning (per ISSUE.md Phase 1), accept the
  audit-report noise as "reviewer reads if interested". Since the rule
  is warning-only it doesn't fail CI.
- (c) Tighten the heuristic differently: only flag pairs that ALSO
  have small y-overlap (i.e. genuinely look adjacent in print), not
  just "left edges coincidentally near".

Recommendation to planner: **(b) for the rule, but document that
audit-output volume will be high after Phase 2's threshold tightening,
and that the audit step in CI stays `|| true` (informational) per
Phase 7**. Promotion to fatal is explicitly deferred per ISSUE.md.

### A12. `tools/check_ci.py` is orthogonal — verified

`check_ci.py` reads its own ParaStyle/CharStyle list from the SLA file
(`xml.etree`-based brand validator); it does not touch
`BRAND_CONSTRAINTS`. New brand rules cannot conflict with it.
Confirmed by `grep -n BRAND_CONSTRAINTS tools/check_ci.py` → 0
matches.

### A13. `templates/_smoke/` won't be affected

`structural_check.discover_template_slugs()` excludes `_smoke` and
`_specs` directories at `structural_check.py:210`. So Phase 1 / Phase
4 changes cannot break smoke tests.

`templates/_smoke/zeitung-mini/build.py` uses synthetic
`blocks.legacy.ContentTeasers / ArticleBody / ImpressumBlock` rather
than the real zeitung's auto-generated frames; its geometry is
authored fresh, not regenerated from upstream-SLA. Phase 4 cannot
shift its frames.

### A14. #17 (postkarte V1) re-audit deferred — out of scope confirmed

ISSUE.md "Out of scope" §1 explicitly defers this. With the new
broader thresholds and the new `image_text_overlap` rule, postkarte
will surface:

- 38+ axis-near pairs (most likely intentional — Seitenhintergrund
  vs. content frames at known offsets).
- 3 image-text partial overlaps.

For #23 to land green, postkarte needs:

- `brand_overrides[brand:image_text_overlap]` in
  `templates/postkarte-a6-kampagne/meta.yml` with reason
  "Production template auto-generated from
  postkarte-vorlage-original.sla; partial overlaps audited at time of
  #23 — re-enable after geometry review (#17 follow-up)".
- The drift rule stays warning-only so no override needed.

Same for plakat-a1-hochformat and infostand-tent-card-a5-quer.

### A15. `bin/render-gallery zeitung-a4-grun` is a hard CI gate

Without re-running `bin/render-gallery` after Phase 4 geometry edits
the workflow at `.github/workflows/pages.yml:113` calls
`bin/check-stale-previews` which compares
`previews_for_sla` SHA in meta.yml against the actual SHA of
`templates/zeitung-a4-grun/template.sla` (the one regenerated by
`build.py`). Phase 4 changes the bytes of `template.sla` → SHA
mismatches → CI exits 1.

**Procedure for the planner:** after Phase 4 + 5 commit lands,
the next commit MUST include:

```
bin/render-gallery zeitung-a4-grun --skip-visual-diff
git add templates/zeitung-a4-grun/template.sla \
       templates/zeitung-a4-grun/template-preview.sla \
       templates/zeitung-a4-grun/meta.yml \
       templates/zeitung-a4-grun/preview.pdf \
       templates/zeitung-a4-grun/page-*.png \
       templates/zeitung-a4-grun/baseline.pdf \
       site/public/templates/zeitung-a4-grun/template.sla \
       site/public/templates/zeitung-a4-grun/preview.pdf \
       site/public/templates/zeitung-a4-grun/page-*.png
git commit
```

The `--skip-visual-diff` flag is appropriate because zeitung is
`sla_diff_strict: false` (meta.yml:20). With strict=false,
`render-gallery` does not run sla_diff against the upstream SLA so
geometry edits are accepted.

**The dev-container has Scribus 1.6.5 + xvfb + brand fonts** (verified
`fc-list | grep -ci "gotham narrow|vollkorn"` = 42, well above the
5-face minimum at `render_pipeline.py:267`). `bin/render-gallery`
should succeed locally; if it crashes with `qt.qpa.xcb` errors, prefix
with `xvfb-run -a` (already done internally at `visual_diff.py:133`).

---

## Section B — Common pitfalls cataloged

### B1. Float-imprecise SLA round-trip

**What goes wrong:** zeitung's auto-generated build.py contains
`w_mm=209.9999999999361` and similar near-but-not-equal-to-page-width
values. Pinning `assertEqual(w_mm, 210.0)` will fail.

**Why it happens:** the SLA stores values as PT (1pt = 0.3527... mm);
mm↔pt round-trip introduces float-imprecision on the order of 10⁻¹³.

**How to avoid:** use `assertAlmostEqual(actual, expected, places=1)`
or `places=2` for all coordinate assertions in Phase 3 tests. Tolerance
of `0.05 mm` is sufficient.

**Warning signs:** test fails with diff like
"209.9999999999361 != 210.0" — the test is too strict.

### B2. Master-page vs. content-page confusion

**What goes wrong:** `_InsidePageRule` and `_SpineSafetyRule` skip
`page.is_master`. New rules must mirror this. Skipping master pages
is correct because masters are abstract layout grids that
legitimately carry full-bleed background polygons.

**How to avoid:** every new BrandRule's `check()` loop should start
with `if page.is_master: continue`.

### B3. Anonymous frames have no anname

**What goes wrong:** `_UndeclaredDriftRule` skips items without
`anname` because the heuristic produces "declare with `same_x("?",
"?", …)`" which is useless. New rules need similar care:

- `bleed_coverage` should still flag anonymous frames (geometry is
  the bug regardless of name), with `targets=("<unnamed
  ImageFrame>",)`.
- `image_text_overlap` should similarly flag anonymous frames; report
  message uses class name + bbox to identify.

**Examples in zeitung:** 9 of the 10 outer-bleed-gap frames are
named, but page 12 has unnamed Dunkelgrün full-bleed band — the rule
must catch it.

### B4. `Page.is_left` is hardcoded False — use master_name regex

**What goes wrong:** `tools/sla_lib/builder/document.py:391-393`
hardcodes `is_left = False` on every doc page in facing-pages mode.
Templates that need to know "left vs right" use master_name regex
instead.

**How to avoid:** new `bleed_coverage` rule MUST use the same
`SIDE_RX = re.compile(r"\b(links|rechts)\b", re.IGNORECASE)`
imported from `brand_constraints.py:466` (or the planner can re-use
the regex). DO NOT call `page.is_left`.

**Pre-existing precedent:** `_SpineSafetyRule` does this correctly at
`brand_constraints.py:521-522`.

### B5. Rotated frames break naive bbox math

**What goes wrong:** `bbox.frame_bbox_mm()` does the rotation-aware
math correctly (returns AABB after rotation around top-left). But the
heuristic-style rules currently SKIP rotated pairs. The new
`image_text_overlap` rule MUST decide: skip rotated, or trust the
AABB.

**Recommendation:** trust the AABB. The rotation-aware bbox is
correct; partial-overlap detection on the AABB is a safe
over-approximation. If the rule false-positives on a rotated frame
(infostand's 180° rotated logo+headline), the per-template
`brand_overrides` is the escape — same as for non-rotated cases.

### B6. `palette_replaces_ci` doc-extras gotcha

**What goes wrong:** `_TextOnGreenRule` queries `getattr(p, "fcolor",
"")` and matches against `"White" / "white"`. Templates that override
the CI palette via `palette_replaces_ci=True` may not have White.
Existing rule handles this correctly (see `brand_constraints.py:88`).

**Implication for new rules:** `image_text_overlap` and
`cover_extent_match` don't query colors directly, so this doesn't
apply. `bleed_coverage` doesn't either. Safe.

### B7. `_AlignedBelowConstraint` skips rotated frames silently

**What goes wrong:** `constraints.py:336-343` returns a single
"warning" Violation when either frame is rotated, then `return`s
without checking. So `aligned_below("u2950", "Cover Hero")` would not
catch the bug — u2950 is rotated 90°.

**Implication:** the planner should NOT recommend that the executor
"declare aligned_below(Cover Hero, u2950)" — it'll skip silently.
Geometric-outcome tests (Phase 3) are the only safe way to encode the
relationship for rotated u2950.

### B8. Constraint `referenced_annames()` symmetry

The `_UndeclaredDriftRule` builds `declared` as a set of
`frozenset({a, b})` — symmetric. New rules that declare-skip must use
the same convention. `_audit_doc()` at `audit_alignment.py:85-101`
already does this.

### B9. SLA round-trip fidelity vs. geometry edits

**What goes wrong:** changing `Cover Hero` from `(0, 0, 210, 155.567)`
to `(-3, 0, 216, 155.567)` will change the bytes of the emitted
template.sla AND the upstream-SLA-comparison output of `sla_diff`. With
zeitung's `sla_diff_strict: false`, sla_diff is informational and CI
won't fail. But `bin/render-gallery` updates the SHA in
`previews_for_sla:` (verified at
`render_pipeline.py:_update_meta_hash`) so check-stale-previews
passes only AFTER the SHA update commit.

### B10. `local_offset_mm` direction confusion

**What goes wrong:** SpreadImage's right-half `local_offset_mm.x` is
NEGATIVE — the math is "shift the source image origin LEFT so the
visible portion is the RIGHT half of the source". Easy to get the sign
wrong when extending bleed. See Section A8.

### B11. `Polygon.fill` can be empty string or None

**What goes wrong:** the proposed scope-widening to
`(ImageFrame|filled Polygon, TextFrame)` needs an explicit
"is filled" check. `Polygon` instances may have `fill=None` (outline
only) or `fill=""`. Check `if poly.fill not in (None, "", "None"):`.

**Verification:** `tools/sla_lib/builder/primitives.py` Polygon
dataclass; `fill` defaults to `"Black"` so most polygons are
filled. None polygons exist (decorative outlines in plakat) but are
rare.

---

## Section C — Security concerns

None applicable. This issue is internal-templates plumbing — no user
input, no network, no auth. The only external surfaces touched are
read-only template files. No security pitfalls.

---

## Section D — Edge cases

### D1. Cover Hero is at y=0 — does inside_page complain?

`_InsidePageRule` allows y=-3 to y=297+3=300. y=0 is well within.
After Phase 4 changing Cover Hero to `(-3, 0, 216, 155.567)`, the
bbox extends from x=-3 to x=213 — also within `[-3, 213]` page bounds
for an A4 page with 3 mm bleed. No new inside_page violation.

### D2. P9 Spread halves with outer-bleed extension

Per A8, after extension the LEFT half is `(-3, 0, 213, 126.14)` and
RIGHT half is `(0, 0, 213, 126.14)`. inside_page bounds for A4:
x ∈ [-3, 213], y ∈ [-3, 300]. LEFT half right-edge x=210 ≤ 213 ✓ but
LEFT half left-edge x=-3 = -bleed exactly ✓. RIGHT half right-edge
x=213 = page_w + bleed ✓. Both halves remain inside_page-clean.

### D3. Page numbers (`Kopie von u2d45 (n)`) drift detection

The columns of page numbers across pages have very different x
positions (depending on left/right master). With broader heuristic
thresholds these will surface as suspicious-pair drift. Already
showed up in audit output at "axis-x drift 11.49mm: Kopie von u2d45
(3) ↔ Kopie von u2d5c (4)". As warning-only this is tolerable but
adds noise.

### D4. Cover-only "RIGHT alone" — facing_pages but no spine

Issue Phase 4: Cover Hero extends to (-3, 213). `_SpineSafetyRule`
already skips own_page=0 (`brand_constraints.py:519-520`). New
`bleed_coverage` rule must do the same OR special-case to require
both outer edges. Either works.

### D5. Spread image: what if outer_bleed_mm is unset?

If the planner adds `outer_bleed_mm` parameter to SpreadImage with
default 0, ALL existing callers (zeitung's P9 Spread today) keep
working unchanged. Then zeitung's call site adds `outer_bleed_mm=3.0`
explicitly. No breakage to other templates that use SpreadImage (none
exist today; verified `grep -rn SpreadImage templates/` → only
zeitung).

### D6. structural_check `--all` performance after rule additions

3 new rules + 1 replaced rule = 12 rules total. Each rule iterates
`primitives` (zeitung has ~870). The most expensive new rule
(`image_text_overlap`) is O(n_images × n_texts) per page. Zeitung
page-10 has 3 images × 6 texts = 18 pair checks. Across 14 pages,
expected ~250 pair checks per template. Total `structural_check
--all` time should stay well under 5 seconds. Verified empirically
that `audit_alignment.py --all` (which does a similar walk) completes
in 1-2 seconds on this hardware.

---

## Section E — Environment availability

Audited the dev container at the worktree root.

| dependency           | required by                          | available | version  |
|----------------------|--------------------------------------|-----------|----------|
| Python               | all sla_lib + tools                  | yes       | 3.13.5   |
| stdlib `unittest`    | tests                                | yes       | n/a      |
| stdlib `dataclasses` | brand rules                          | yes       | n/a      |
| `pyyaml`             | meta.yml parsing                     | yes       | n/a      |
| Scribus              | bin/render-gallery (visual_diff path) | yes      | 1.6.5    |
| xvfb-run             | Scribus headless wrapper             | yes       | /usr/bin/xvfb-run |
| Brand fonts (Gotham Narrow / Vollkorn) | render fidelity     | yes       | 42 face entries (≥ 5 required) |
| poppler-utils (pdftoppm) | render PNG rasterisation         | (assumed; CI installs it) | n/a |
| ghostscript          | sla_diff baseline rendering          | (assumed) | n/a      |

**No new dependencies required.** All work fits within Python stdlib +
existing pyyaml. The new BrandRule classes use the same dataclass
pattern as the existing 11 rules.

**Render-gallery wrinkle:** running `bin/render-gallery
zeitung-a4-grun` in this dev shell may work (xvfb-run is internal at
`visual_diff.py:133`). If it fails with Qt platform errors, the
correct invocation is what the script already does — no manual prefix
needed.

---

## Section F — Anti-patterns (DON'T do this)

### F1. Don't re-add CONSTRAINTS for any pair where geometry doesn't match

The planner MUST encode this as a hard rule for the executor. ISSUE.md
already says "All Zeitung CONSTRAINTS that previously silenced
misalignments are REMOVED. Re-encoded only for genuinely-intentional
adjacencies." The planner should phrase this in PLAN.md as:

> **Anti-rule for #23 executor:** if `brand:visual_adjacency_drift`
> warns about a pair, you have TWO options: (a) fix the geometry so
> the warning goes away, or (b) prove the adjacency is intentional
> (e.g. it's the design's chosen offset) and add a constraint with
> `tolerance_mm=0.5` (default) matching the actual relationship. NEVER
> set `tolerance_mm > 1.0` to absorb drift; that's encode-and-silence
> and contradicts the issue's purpose.

### F2. Don't pin absolute coordinates in Phase 3 tests

See A6. Pin invariants instead.

### F3. Don't extend `bleed_coverage` cutoff to cover the body-text grid

The 0.7 × page_w threshold from ISSUE.md is wrong (29 false positives
in zeitung). Use 0.95 × page_w (or `page_w − 2 × margin_mm` for the
page's actual margin). See A2.

### F4. Don't treat `image_text_overlap` and `polygon_text_overlap` as
separate rules

The page-10 bug is a Polygon×Text partial overlap; the proposed
ImageFrame×Text rule misses it. Widen the scope rather than splitting
into two rules — one rule, broader scope, single override id.

### F5. Don't promote audit-tool to fatal in this PR

ISSUE.md Phase 7 explicitly says "keep informational (`|| true`) for
now". Don't combine the rule strictness change with a CI gate
promotion — that's two unrelated risks in one PR.

### F6. Don't forget the `site/public/templates/zeitung-a4-grun/`
mirror

`bin/render-gallery` updates both the `templates/<slug>/` source
artifacts AND mirrors to `site/public/templates/<slug>/`. The git
commit must include both directories. See A15.

---

## Section G — Sources

### HIGH confidence (codebase analysis on current worktree)

- `/root/workspace/.worktrees/23-…/tools/sla_lib/builder/brand_constraints.py` — all 11 existing rules, fully read.
- `/root/workspace/.worktrees/23-…/tools/sla_lib/builder/bbox.py` — frame_bbox_mm + rotated_bbox.
- `/root/workspace/.worktrees/23-…/tools/sla_lib/builder/constraints.py` — Constraint factories + check methods.
- `/root/workspace/.worktrees/23-…/tools/sla_lib/builder/structural_check.py` — orchestrator.
- `/root/workspace/.worktrees/23-…/tools/sla_lib/builder/blocks.py:680-740` — SpreadImage emit math.
- `/root/workspace/.worktrees/23-…/tools/sla_lib/builder/document.py:360-393` — facing-pages cover semantics.
- `/root/workspace/.worktrees/23-…/tools/audit_alignment.py` — current audit tool.
- `/root/workspace/.worktrees/23-…/templates/zeitung-a4-grun/build.py` — relevant lines 245-263 (Cover Hero+u2950), 457-470 (P1 Hero), 978-987 (P4 Foto-Spread), 1348-1403 (u918+P7 Portrait), 1799-1808 (Kopie von u1529), 1845-1852 (P9 SpreadImage), 2101-2129 (P11 Bottom + page12 unnamed), 2620-2736 (CONSTRAINTS list).
- `/root/workspace/.worktrees/23-…/templates/zeitung-a4-grun/meta.yml` — brand_overrides + previews_for_sla SHA.
- `/root/workspace/.worktrees/23-…/templates/{wahlaufruf-postkarte-a6-quer,postkarte-a6-kampagne,plakat-a1-hochformat,infostand-tent-card-a5-quer,kandidat-falzflyer-din-lang,wahltag-tueranhaenger,themen-plakat-a3-quer}/meta.yml` — confirmed no template currently has brand:undeclared_alignment_drift override.
- `/root/workspace/.worktrees/23-…/.github/workflows/pages.yml:113,143-165` — CI step ordering.
- Live runs of `tools/audit_alignment.py` and a custom Polygon×Text overlap probe — empirical violation counts per template.

### MEDIUM confidence (cross-referenced but not exhaustively validated)

- The 0.95 × page_w cutoff for full-width detection is empirically the right value for THIS issue's 10 frames in zeitung. May need tuning for future templates with different margins (e.g. plakat A1 has different page proportions and margin conventions).
- The `outer_bleed_mm=3.0` SpreadImage math (Section A8) — reasoning is correct symbolically but unverified visually. Required visual inspection of `page-10.png` + `page-11.png` after Phase 4.

### LOW confidence (needs validation)

- The 0.05 / 0.95 threshold for `image_text_overlap` "partial" is heuristic — zeitung's 5 polygon-text cases distribute 22 % / 26 % / 53 % / 63 % / 63 %, and infostand's case is 63 %. The thresholds catch the real bugs but may need re-tuning when a brand designer pushes back on a flagged "intentional" overlap.

---

## Section H — Quick-summary table for the planner

| pitfall | severity | mitigation                                                                          |
|---------|----------|-------------------------------------------------------------------------------------|
| A1 encode-and-silence       | HIGH | Pin geometric outcomes (Phase 3), audit-flag tolerance_mm > 1.0           |
| A2 0.7 × page_w too loose   | HIGH | Use 0.95 × page_w cutoff in `bleed_coverage` rule                          |
| A3 Polygon×Text scope       | HIGH | Widen `image_text_overlap` to (ImageFrame|filled Polygon, TextFrame)       |
| A4 cover_extent_match noise | LOW  | Already narrow; no action                                                  |
| A5 rule rename atomic       | MED  | Single commit covers `_UndeclaredDriftRule` → `_VisualAdjacencyDriftRule` + 5 file edits |
| A6 coord-pinned tests       | HIGH | Use invariant-style assertions, not raw coordinates                        |
| A7 phase ordering           | HIGH | Sequence: rules+overrides (T01) → audit (T02) → geometry+drop (T03) → tests (T04) → render-gallery (T05) → CI (T06) |
| A8 SpreadImage offset       | MED  | Add `outer_bleed_mm` param, re-derive right-half `local_offset_mm`, visual-verify |
| A9 cover semantics          | LOW  | bleed_coverage skips own_page=0 OR treats both edges as outer              |
| A10 right-edge axis         | HIGH | New drift rule must check `dx_right` and `dy_bottom`, not just `dx`/`dy`   |
| A11 broader thresholds noise | MED | Keep severity=warning, audit-tool stays informational                      |
| A12 check_ci.py orthogonal  | LOW  | No conflict; no action                                                     |
| A13 _smoke unaffected       | LOW  | Skipped by structural_check; no action                                     |
| A14 #17 re-audit deferred   | MED  | Pre-apply brand_overrides for postkarte/plakat/infostand                   |
| A15 render-gallery + SHA bump | HIGH | Final commit MUST include `bin/render-gallery zeitung-a4-grun` artifacts |
