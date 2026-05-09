# PITFALLS — Issue #17 V1 Symbol-Tight

**Researched:** 2026-05-09
**Scope:** Pitfalls dimension only (codebase + ecosystem covered separately)
**Worktree:** `/root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight/`

---

## Summary

I executed structural_check + audit_alignment against the current baseline,
inspected every BRAND_CONSTRAINTS rule the new V1 frames will encounter,
verified asset and bleed math, and replayed the prescribed CONSTRAINTS list
against the prescribed coordinates. Three SHIP-BLOCKERS surfaced — two are
geometric (the prescribed coords don't satisfy two of the prescribed
constraints; one constraint encodes "centered" using `same_x` which checks
top-left corner, not center). One ordering pitfall (`brand_overrides`
removal) is correctly captured by ISSUE.md's "remove only after green".
Several MEDIUM pitfalls (audit will flag headline→body adjacency in the 3
W-Frage-Blocks; the meta.yml `slots:` inventory will go stale; the spec MD
will go stale) need to be either added to CONSTRAINTS or accepted as
out-of-scope by the planner.

**Primary finding:** ISSUE.md's prescribed CONSTRAINTS list and prescribed
mm-coordinates do not all line up. The planner MUST reconcile before
implementation.

---

## SHIP-BLOCKERS (must resolve before merge)

### B1. `same_x("wahlkreuz_halo", "wahlkreuz")` and `same_y(...)` will FAIL

ISSUE.md prescribes:
- `wahlkreuz_halo`: `Polygon x=43 y=17 Ø=62` (so w=h=62, top-left at 43,17)
- `wahlkreuz`: ImageFrame `x=44 y=18 w=60 h=60`

Both `same_x` and `same_y` enforce `frame.x_mm` (top-left corner) match within
0.5mm tolerance (see `tools/sla_lib/builder/constraints.py::_SameAxisConstraint`).
- halo.x = 43, wk.x = 44 → 1mm drift → **FAIL** (>0.5mm tol).
- halo.y = 17, wk.y = 18 → 1mm drift → **FAIL**.

**Why the geometry is "right" anyway:** the symbol IS centered inside the
halo by design — halo center = (43+31, 17+31) = (74, 48); wk center =
(44+30, 18+30) = (74, 48). The `inside("wahlkreuz", "wahlkreuz_halo")`
constraint correctly captures the containment.

**The bug:** `same_x`/`same_y` are not "center alignment" predicates. There
is no `same_center_x` factory in `constraints.py` (verified — only
`same_x`, `same_y`, `mirrored_x(left, right, axis_mm)`, `mirrored_y`,
`inside`, `equal_gap`, `aligned_below`, `distance_x`, `distance_y`,
`hierarchy`, `same_size`, `same_style`).

**Resolution options for the planner:**
1. **Recommended:** Replace `same_x("wahlkreuz_halo", "wahlkreuz")` with
   `mirrored_x("wahlkreuz_halo", "wahlkreuz", axis_mm=74.0, name="halo_x_center")`
   and same for y at axis_mm=48.0. This passes — `mirrored_x` averages the
   center-x of both frames and compares to axis_mm.
2. Drop `same_x`/`same_y` entirely and rely solely on `inside(...)` plus a
   pair of `distance_x`/`distance_y` from the page edge (or the polygon
   shape). Less expressive than option 1.
3. Move the symbol to halo.x_mm, halo.y_mm exactly (no centering offset) —
   but this defeats the design intent of a halo around the symbol.

The planner should pick option 1 and update the CONSTRAINTS list verbatim
in PLAN.md.

### B2. `aligned_below("qr_code", "qr_label", gap_mm=2.0)` will FAIL

ISSUE.md prescribes:
- `qr_label`: `x=96 y=24 w=36 h=5` (bottom edge y = 24+5 = 29)
- `qr_code`:  `x=96 y=30 w=36 h=36`

`aligned_below(below, above, gap_mm)` requires
`below.y_mm == above.y_mm + above.h_mm + gap_mm` within 0.5mm
(`tools/sla_lib/builder/constraints.py:319-357`).

Required: qr_code.y == 24 + 5 + 2.0 = **31**
Prescribed: qr_code.y = **30** → 1.0mm drift → **FAIL** (>0.5mm tol).

**Resolution:** EITHER set `qr_code.y_mm = 31` (recommended; preserves the
declared 2mm gap) OR change `gap_mm=2.0 → gap_mm=1.0`. The planner should
pick the y-coord change so the constraint reads cleanly.

### B3. `aligned_below("qr_url", "qr_code", gap_mm=4.0)` will FAIL

ISSUE.md prescribes:
- `qr_code`: `x=96 y=30 w=36 h=36` (bottom edge y = 66)
- `qr_url`:  `x=96 y=68 w=36 h=5`

Required: qr_url.y == 30 + 36 + 4.0 = **70**
Prescribed: qr_url.y = **68** → 2.0mm drift → **FAIL** (>0.5mm tol).

**Resolution:** Cascading from B2 — if qr_code.y becomes 31, then
qr_code.y1 = 67. Then qr_url.y must be 67 + 4 = **71** to satisfy
`gap_mm=4.0`. Adjust qr_url.y_mm = 71 (still leaves 30mm headroom above
the impressum strip at y=101.5). Alternatively, set gap_mm=1.0 (qr_url.y
stays 68 → 67+1=68 ✓), but the prescribed visual rhythm (~4mm air below
the QR) is the stronger design intent.

**Recommended cascade after B2/B3:** qr_label y=24, qr_code y=**31**,
qr_url y=**71**. All same_x=96. Distance from qr_url.y1=76 to impressum
top y=101.5 = 25.5mm — comfortable air for a 11pt URL.

---

## HIGH PITFALLS (will degrade quality even if not failing CI)

### H1. Audit will flag 3+ undeclared headline→body adjacencies once override removed

Once `brand:undeclared_alignment_drift` is un-overridden, the rule pairs
every named primitive on each page and flags pairs with axis-x drift in
(0.5, 5.0)mm, axis-y drift in (0.5, 5.0)mm, or P-above-Q with
gap_mm in (0.5, 12.0) AND axis-x-drift < 5mm
(`tools/sla_lib/builder/brand_constraints.py:594-706`).

For the V1 back side, EACH of the three W-Frage blocks has:
- `frage_X_headline` at (x=6, y=Y, w=84, h=8); bottom y1 = Y+8
- `frage_X_body` at (x=6, y=Y+9, w=84, h=20); top y0 = Y+9
- gap = 1mm; dx = 0 → **WILL FLAG as adjacency-y** (1mm in (0.5, 12.0)).

ISSUE.md's CONSTRAINTS list does NOT declare these pairs.

**Recommended addition to CONSTRAINTS:**
```python
aligned_below("frage_was_body",   "frage_was_headline",   gap_mm=1.0, name="frage_was_stack"),
aligned_below("frage_warum_body", "frage_warum_headline", gap_mm=1.0, name="frage_warum_stack"),
aligned_below("frage_wann_body",  "frage_wann_headline",  gap_mm=1.0, name="frage_wann_stack"),
```

Plus likely flagged on Page 1:
- `headline_datum` (x=10, y=82, h=10, y1=92) ↔ `headline_cta` (x=10, y=92, h=10):
  gap=0, dx=0 → adjacency-y triggers only at gap > 0.5, so 0 → **NOT
  flagged**. ✓
- However `same_x("headline_datum", "headline_cta")` is NOT declared but
  dx=0 → axis-x drift = 0 → also NOT flagged (heuristic only triggers
  in (0.5, 5.0) range). ✓ No action needed.
- `headline_datum` (x=10, y=82) ↔ `wahlkreuz` (x=44, y=18, y1=78): dx=34
  > 5 → adjacency-y check requires dx<5 → NOT flagged. ✓

Other suspect Page 2 pairs to verify after build:
- `qr_label` ↔ `logo_back`: both x=96 (same x → 0 dx, won't trigger axis).
  logo at (96, 8, 18.9, 5.7) y1=13.7; qr_label at y=24 → gap=10.3 in
  (0.5, 12.0), dx=0 → **WILL FLAG.** Either declare
  `aligned_below("qr_label", "logo_back", gap_mm=10.3, ...)` or accept
  as a non-design adjacency.
- The Hellgrün split-bg poly bbox is huge — pair-checks against most
  small frames will have dx > 5mm (poly x0=-3, frames at x=6 → dx=9 >
  5 → safe).
- The Impressum-strip white poly (x=0, y=96, w=148, h=9) bbox=(0, 96,
  148, 105) vs `impressum` text (x=6, y=101.5, w=136, h=4): dx=6 > 5 →
  axis safe; y_drift=5.5 > 5 → axis safe; impressum is BELOW poly
  (101.5 > 96), and impressum.y1=105.5 vs poly.y1=105 (impressum sits
  inside poly) — neither "above" the other → adjacency safe.

**Action:** Run audit_alignment after build to enumerate exact
suggestions and add to CONSTRAINTS. A worked example exists from the
current layout — see "audit_alignment baseline" appendix at end.

### H2. Logo asset `gruene-weiss.png` reuse — verify scale ratio

`shared/logos/gruene-weiss.png` is 413×118 px (verified via PIL).

- Front (existing, 35×10mm): `local_scale=(0.240, 0.240)`. Math: 413 × 0.240 = 99.12pt; 35mm = 99.21pt → ratio fits.
- Front (V1 target, 18.9×5.7mm): `local_scale=(0.130, 0.130)`. Math: 413 × 0.130 = 53.69pt; 18.9mm = 53.575pt → ratio fits within ~0.2% — **OK.**
- Back (V1 target, 18.9×5.7mm at x=96): same `local_scale=(0.130, 0.130)`. **OK.**

But: the existing back-side logo uses `gruene-logo-bund-dunkel.png` at
(18, 16) mm with no `local_scale` (i.e. 1.0). After V1 the back logo
becomes the white `gruene-weiss.png` at (18.9, 5.7) which requires
`local_scale=(0.130, 0.130)` to render correctly. **Pitfall**: forgetting
to set `local_scale` on the back logo will leave it at default (1.0, 1.0)
which renders the 413px image at native size → ~5.5× over-scale, clipped
by frame. The planner MUST include `local_scale=(0.130, 0.130)` in the
back logo construction.

### H3. `Polygon shape="ellipse"` required for the Hellgrün-Halo

ISSUE.md says "Hellgrün-Halo `Polygon` `x=43 y=17 Ø=62` (Kreis-Polygon)".
The DSL does not auto-detect circles from `w == h`. Without explicit
`shape="ellipse"`, the Polygon emits as a **rectangle** (default
`shape="rectangle"`, FRTYPE=0). Verified:
`tools/sla_lib/builder/primitives.py:848-911`.

Pattern in use elsewhere:
- `templates/postkarte-a6-kampagne/build.py:169` — `shape='ellipse'`
- `templates/zeitung-a4-grun/build.py:312, 2495` — `shape='ellipse'`

**Required:**
```python
Polygon(
    x_mm=43, y_mm=17, w_mm=62, h_mm=62,
    fill="Hellgrün",
    shape="ellipse",       # ← MUST set; default is "rectangle"
    layer=0,
    anname="wahlkreuz_halo",
)
```

### H4. `meta.yml::slots` inventory will go stale

Current `meta.yml` lists 12 slots: `headline_wahlaufruf`, `cell_1_headline`,
`cell_1_body`, … `cell_4_body`. After V1 these annames are deleted.

**Code path that consumes meta.yml::slots:** I found none — `spec_check.py`
reads slots from `templates/_specs/<slug>.md` (the spec MD), not meta.yml.
`structural_check.py` only reads `meta.yml::brand_overrides`.

**Conclusion:** meta.yml slots staleness will NOT fail CI. It IS a
documentation drift that future contributors will hit. ISSUE.md acceptance
criteria do not require updating meta.yml::slots, so this is **out of
scope** but worth flagging in the PLAN as a `// TODO follow-up` so the
planner can decide whether to include the slot rename in this commit or
defer.

The planner should choose ONE:
1. Rename slots inline with V1 (add `headline_datum`, `headline_cta`,
   `frage_was_*`, `qr_label`, `qr_url`, etc.; remove old) — small extra
   diff, full traceability.
2. Defer to a follow-up — strict scope adherence to ISSUE.md.

I lean to option 1 (slots are documentation; staleness reduces value).

### H5. `templates/_specs/wahlaufruf-postkarte-a6-quer.md` will go stale

The spec MD (430+ lines) describes the OLD 2×2 grid layout in detail.
After V1, the spec is wrong. `tools/spec_check.py` is NOT in CI (`grep`
of `.github/workflows/` confirms), so spec drift will not fail builds.

**Conclusion:** out-of-scope per ISSUE.md; flag for follow-up. The
planner should add a single-line note at the top of the spec MD ("Spec
deferred — see `improvements/01-…` for current V1 layout") if doing so
costs nothing, OR open a separate issue.

---

## MEDIUM PITFALLS

### M1. The order of brand_overrides removal — captured correctly by ISSUE.md

ISSUE.md acceptance criterion #14 (per the prompt): "REMOVE
`brand:undeclared_alignment_drift` override only AFTER all CONSTRAINTS are
green and the audit reports zero warnings." This is correct.

**Pitfall to surface in PLAN:** the order matters because removing
override BEFORE the CONSTRAINTS list is complete will surface ~8+
warnings that fail the "no `brand:undeclared_alignment_drift` warnings"
acceptance check (orphan-anname references). Even AFTER override removal,
warnings (not errors) don't fail CI — but they fail ISSUE.md's
acceptance criterion of "all green".

**Recommended sequence in PLAN:**
1. Edit build.py with all new frames + CONSTRAINTS list.
2. Run `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer` — fix any remaining errors (B1/B2/B3).
3. Run `PYTHONPATH=tools python3 tools/audit_alignment.py wahlaufruf-postkarte-a6-quer` — read the suggested-additional pairs.
4. Add missing pairs to CONSTRAINTS (e.g. the 3 frage_*_stack from H1).
5. Re-run structural_check — verify zero errors AND PASS-only output.
6. EDIT meta.yml: remove the `brand:undeclared_alignment_drift` entry.
7. Re-run structural_check — should still be zero errors zero warnings.
8. Run `bin/render-gallery wahlaufruf-postkarte-a6-quer --skip-visual-diff` (regenerates template.sla, page-NN.png, preview.pdf, updates meta.yml::previews_for_sla SHA).
9. Run `python3 -m sla_lib.builder.structural_check --all` — confirms no other-template regression.
10. Commit.

### M2. The existing `wahlaufruf/cell-body` ParaStyle mutation is safe (single-template scope)

ISSUE.md proposes changing `wahlaufruf/cell-body` `fcolor=Black → White`.
The prompt asked me to verify whether the style is referenced from any
other template.

```bash
grep -rn "wahlaufruf/cell-body" templates/ tools/ shared/
```

Output (deduplicated):
- `templates/wahlaufruf-postkarte-a6-quer/build.py` — declaration + 2 uses
- `templates/wahlaufruf-postkarte-a6-quer/template.sla` — the SLA reflection
- `templates/wahlaufruf-postkarte-a6-quer/meta.yml::ci_overrides::non_ci_styles`
- `templates/_specs/wahlaufruf-postkarte-a6-quer.md` — spec docs

**Conclusion:** the style is single-template scoped. Direct mutation of
`fcolor` is safe. The "create `wahlaufruf/cell-body-on-green` parallel
ParaStyle" pattern is a forward-looking convention for #18-#21 (per
ISSUE.md, this is "the first of five V1 implementations… establishes the
*-on-green ParaStyle migration pattern that #18-#21 reuse").

**Recommendation to planner:** Either approach satisfies #17.
- **Option A (ISSUE.md literal):** Mutate `wahlaufruf/cell-body` in
  place. Simplest. Sets a precedent of "mutate when single-scoped".
- **Option B (improvements/01 §H7 suggestion + per-prompt advice):**
  Add `wahlaufruf/cell-body-on-green` (Gotham Narrow Book 9pt linesp 11
  fcolor=White) and use it for the new frage_*_body frames. Leave the
  old `wahlaufruf/cell-body` untouched (technically dead-code after V1,
  since the cell-loop is deleted). Sets the parallel-migration pattern
  for #18-#21.

I lean to **Option B** because:
1. ISSUE.md explicitly says #17 "establishes the `*-on-green` ParaStyle
   migration pattern" → defining the pattern means USING it here.
2. The mutation in Option A ALSO leaves the original style entirely
   unused (the cell-loop that referenced it is deleted), so we get the
   worst of both worlds: a "modified" style nobody uses + the migration
   pattern is implicit, not visible.
3. Option B is cleanly reversible (drop the new style; old still works
   for any other consumer that appears).

Either way, the `meta.yml::ci_overrides::non_ci_styles` list must be
updated (add new style names; the old `wahlaufruf/cell-body` can stay
even if unused).

### M3. `brand:hl_sl_distance_x2` rule won't trigger on V1 (intentionally?)

The HL/SL distance rule (`brand_constraints.py:193-240`) pairs frames
matching `/headline/i` (excluding `/sub-headline|subline|sub headline/i`)
with the nearest frame matching `/sub|subline/i` BELOW it.

V1 anname inventory:
- `headline_datum`, `headline_cta` — both match `/headline/i`. Neither
  matches `/sub|subline/i`. → no pairs formed → rule passes silently.
- `frage_was_headline`, `frage_warum_headline`, `frage_wann_headline` —
  match `/headline/i`. Bodies match `frage_*_body` — NEITHER matches
  `/sub|subline/i`. → no pairs → rule passes silently.

This is a **silent green** — the rule provides zero protection for V1.
Not a blocker (the design intent is HL+CTA, not HL+SL pair).

**Note:** The prescribed `distance_y("headline_datum", "headline_cta",
equals=10.0)` aligns nicely with the rule's `baseline_mm × 2 = 5.4 × 2
= 10.8mm` target (1mm tolerance). So the design intent is captured even
without the rule. ✓ No action needed.

### M4. The `brand:logo_size_3M` override might warrant tightening — but defer

Current override reason: "Front logo (35mm) is intentionally larger than
3*M = 18.90mm to anchor the Wahlkreuz hero on the Vollbild front.
Back-side Bund-Dunkel logo (18mm) is 0.9mm under 3*M — also intentional".

After V1: BOTH logos are at 18.9mm (3*M exactly). The override would no
longer be needed. Removing it would tighten the contract.

ISSUE.md does NOT ask for this. **Conservative path:** leave the
override in place (no harm; passes silently). **Tighter path:** also
remove this override after V1 lands. The planner can decide. I lean to
LEAVING IT for #17 (smaller diff; one less moving part) and opening a
follow-up to remove it once V1 has shipped and stabilized.

### M5. QR ImageFrame `scale_type=0` + no `local_scale` — pre-existing pattern, may be wrong

The current build.py wraps the QR PNG (370×370 px) in an ImageFrame with
`scale_type=0, ratio=1` and no `local_scale`, so `local_scale=(1.0,
1.0)`. With `scale_type=0`, the PNG renders at NATIVE PIXEL SIZE: 370px
≈ 130mm. That's ~5× the prescribed 27mm frame — Scribus will clip.

**This is a pre-existing pattern from #11 — not introduced by #17.**

For V1 the QR frame becomes 36×36mm. Native render at 370px is still
~130mm → still clipped by frame. The QR PNG IS visible because the
frame is configured to display the top-left portion of the image, which
includes the QR pattern start. Whether this is INTENTIONAL or a bug is
outside #17's scope.

**Recommendation:** Leave the existing pattern (`scale_type=0, ratio=1`
with no `local_scale`) for V1. If the QR doesn't render correctly in
the rebuilt page-02.png, the planner should add `local_scale=(0.0973,
0.0973)` (36mm at 370px → 36×2.834646 / 370 = 0.276 — wait, that's the
wrong direction). Actually: `local_scale` applies to the image, not the
frame. To render 370px → 36mm: 36mm = 102.05pt; 370 * scale = 102.05 →
scale = 0.276. So `local_scale=(0.276, 0.276)` would fit the QR to the
36mm frame. **But:** this is speculation — visual review of the
regenerated page-02.png will tell. Suggest the planner FIRST re-render
without changing the QR scale parameters; if visually wrong, ADD
`local_scale=(0.276, 0.276)` and re-render. **Defer the decision to
post-render.**

### M6. The `wahlaufruf/impressum` ParaStyle change — `fontsize 6→5`, but `linesp` not specified

ISSUE.md says "fontsize 6→5". Current ParaStyle:
```python
fontsize=6, linesp=7
```

If `fontsize=5` and `linesp` is unchanged at 7: `brand:line_spacing_0.9`
would expect `linesp = 5 * 0.9 = 4.5`, with 0.5 tolerance → 7 vs 4.5 =
2.5pt drift → FAIL. **But** `brand:line_spacing_0.9` is overridden
template-wide for this template. So no rule violation.

**Recommendation:** the planner should ALSO drop `linesp=7→4.5` (or
`linesp=4.5`) in the same edit, both for consistency and so that if the
override is ever removed, the impressum style passes. Defensive edit;
costs nothing.

---

## LOW PITFALLS (worth knowing)

### L1. `brand:wahlkreuz_colored_bg` rule will pass — but the "halo" anname trips a subtle case

The rule (`brand_constraints.py:341-374`) selects ALL primitives whose
anname contains the substring "Wahlkreuz" (case-sensitive). This will
match BOTH:
- `Wahlkreuz` (the ImageFrame)
- `wahlkreuz_halo` — wait, lowercase 'w', the rule uses
  `"Wahlkreuz" in anname` (substring, case-sensitive). `"Wahlkreuz" in
  "wahlkreuz_halo"` is False (case-sensitive). So the halo polygon is
  NOT auto-selected by the rule. ✓

But: the loop then checks each "Wahlkreuz" frame against a list of all
Polygons (excluding self) and verifies an overlapping polygon has
fill ∈ {Dunkelgrün, Hellgrün, Magenta}. The Wahlkreuz at (44, 18, 60,
60) overlaps:
- The full-page `Seitenhintergrund (front)` Dunkelgrün (always overlaps).
- The new `wahlkreuz_halo` Hellgrün (designed to fully contain it).

Both fills are in the allowed set. **PASSES.** ✓

**Note:** If V1 ever renames the Wahlkreuz frame (e.g.
`wahlkreuz_symbol` to match the underscore convention of the other
new annames), the rule's substring match `"Wahlkreuz" in anname` will
NOT match `wahlkreuz_symbol` (lowercase). The rule would silently
skip — losing protection. ISSUE.md prescribes keeping anname `Wahlkreuz`
(capital W) — so safe AS PROPOSED. **Don't rename.**

### L2. `brand:text_on_green` rule won't catch V1's `wahlaufruf/headline-cta` on Hellgrün

The rule (`brand_constraints.py:280-317`) only inspects TextFrames whose
paragraph style matches `^ci/(h|headline)`. V1's new `wahlaufruf/headline-cta`
(White on Hellgrün/Dunkelgrün front bg) does NOT match this prefix.
Same for the back's `frage_*_body` (White text on Dunkelgrün). The rule
provides zero protection — but that's true of ALL templates that use
`<slug>/*` styles, not a V1-specific pitfall.

**No action needed for #17.** Worth surfacing to brand-team that the
rule should also key off the doc's `_extra_para_styles` to be useful —
but that's a separate brand-tooling issue.

### L3. `inside_page` math for the prescribed frames — verified safe

I computed `bbox` for every new frame against the page bounds
(-3, -3, 151, 108):

| Frame | bbox | worst overshoot | result |
|-------|------|-----------------|--------|
| `wahlkreuz_halo` | (43, 17, 105, 79) | -29 | PASS |
| `wahlkreuz` (60mm) | (44, 18, 104, 78) | -30 | PASS |
| `headline_datum` | (10, 82, 138, 92) | -16 | PASS |
| `headline_cta` | (10, 92, 138, 102) | -6 | PASS |
| `seitenhintergrund_back_left` | (-3, -3, 90, 108) | 0 (at-bleed) | PASS |
| `impressum_strip_bg` | (0, 96, 148, 105) | 0 | PASS |
| `logo_back` (V1) | (96, 8, 114.9, 13.7) | -36 | PASS |
| `frage_was_headline` | (6, 12, 90, 20) | -61 | PASS |
| `frage_was_body` | (6, 21, 90, 41) | -61 | PASS |
| `qr_label` | (96, 24, 132, 29) | -19 | PASS |
| `qr_code` (after B2 fix to y=31) | (96, 31, 132, 67) | -19 | PASS |
| `qr_url` (after B3 fix to y=71) | (96, 71, 132, 76) | -19 | PASS |
| `Impressum` (V1, y=101.5 h=4) | (6, 101.5, 142, 105.5) | -2.5 | PASS |

All within tolerance. The `inside_page` rule warning band is (0.5, 1.0)mm;
error >1.0mm — none of the new frames are anywhere close. ✓

### L4. The `Seitenhintergrund (front)` polygon already covers full bleed

The existing build.py emits a `Seitenhintergrund (front)` Polygon at
(-3, -3, 154, 111) (full page + bleed all sides). The new
`wahlkreuz_halo` and `Wahlkreuz` will sit on top via `layer` ordering.
Layer convention in this codebase: 0=Hintergrund, 1=Bilder, 2=Text.
Halo should use `layer=0` (background-tier polygon backing for the
symbol), Wahlkreuz already uses `layer=1`. Verify the planner emits
the halo BEFORE the Wahlkreuz in `page0.add(...)` order so byte-stable
interleave keeps z-order. The `layer` attribute is the Scribus-side
z-control, but emit-order also matters within the same layer.

### L5. `same_x` arity — accepts ≥2 targets

`same_x("frage_was_headline", "frage_warum_headline", "frage_wann_headline")`
correctly uses 3 targets. Verified `_SameAxisConstraint.check` iterates
all targets (`tools/sla_lib/builder/constraints.py:230-275`). ✓

Same for `same_x("qr_label", "qr_code", "qr_url")` — 3 targets. ✓

### L6. ISSUE.md acceptance criterion: "absence of `meta.yml::previews_for_sla`"

ISSUE.md says "No reference-SLA exists for this template (per HANDOFF #15
open question 6) — confirm by absence of `meta.yml::previews_for_sla`
field; layout changes are free."

This is **WRONG** as written. `meta.yml::previews_for_sla` IS PRESENT in
the current meta.yml (line 19): `previews_for_sla: 703b25...`. Its
PRESENCE pins a SHA for stale-check, not a reference SLA for diff. The
correct check is: "absence of `meta.yml::original_sla` field" — and
that one IS absent (verified). So the acceptance intent ("layout changes
are free, no diff to satisfy") is correct, but the citation is wrong.

`bin/check-stale-previews` WILL still fire on `previews_for_sla` SHA
mismatch — so after build.py edits, `bin/render-gallery` MUST be run
to update the SHA. Pitfall for the planner: do NOT misread ISSUE.md as
"previews_for_sla is absent" — it's present and gates CI. The
acceptance criterion needs a small correction in PLAN.md.

### L7. Layer assignment for new polygons

ISSUE.md prescribes new polygons but doesn't specify `layer=`. For
consistency with existing pattern (`Seitenhintergrund (front)` uses
`layer=0`):
- `seitenhintergrund_back_left` (Dunkelgrün split-half): `layer=0`
- `impressum_strip_bg` (White): `layer=0`
- `wahlkreuz_halo` (Hellgrün ellipse): `layer=0`

Text frames use `layer=2`. Image frames use `layer=1`. Verify the
planner inherits this convention.

### L8. Test impact: zero test files reference `wahlaufruf-postkarte-a6-quer`

`grep -rln "wahlaufruf" tools/sla_lib/tests/` returns nothing. Tests
won't break. ✓ However, `python3 -m unittest discover tools/sla_lib/tests`
runs in CI (`pages.yml:105`); a syntax error in build.py will fail
`python3 -m sla_lib.builder.structural_check --all` (`pages.yml:155`)
— so build.py must IMPORT cleanly and `build_doc()` must NOT raise.

### L9. `brand:spine_safety` — N/A for non-facing-pages

This template has `facing_pages=False` (verified at `build.py:54`). The
spine-safety rule short-circuits at `if not getattr(doc, "facing_pages",
False): return []` (`brand_constraints.py:507-509`). ✓

---

## Environment Audit

| Dependency | Required for | Available | Version | Notes |
|------------|-------------|-----------|---------|-------|
| Python | DSL build | YES | 3.13.5 | `python3 --version` |
| python-yaml | meta.yml read | YES | (stdlib via pip) | `import yaml` works |
| jsonschema | meta_schema validation | YES | — | already in requirements |
| lxml | SLA emission | YES | — | imported by primitives.py |
| Pillow (PIL) | image dim probe | YES | — | imported by qr_gen + render_pipeline |
| Scribus 1.6.5 | PDF render | YES | 1.6.5 | `/usr/bin/scribus` available |
| xvfb-run | headless Scribus | YES | — | `/usr/bin/xvfb-run` |
| pdftoppm (poppler) | PNG raster | YES | — | `/usr/bin/pdftoppm` |
| Brand fonts | Scribus render | YES | Gotham + Vollkorn registered | `fc-list` confirms |

**No new deps needed** for #17. Stack is stdlib + already-bundled libs.

---

## Verification Steps for the Planner

PLAN.md should embed these as a checklist the executor follows:

1. After build.py edit:
   ```bash
   PYTHONPATH=tools python3 templates/wahlaufruf-postkarte-a6-quer/build.py
   ```
   Should print "wrote …/template.sla" with no exception.

2. Run structural check:
   ```bash
   PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer
   ```
   Expected: "0 errors, 0 warnings, N skipped, M passes" (skipped = 1 if
   we leave `brand:line_spacing_0.9` and `brand:logo_size_3M`; 0 if we
   also remove the latter; PLAN-decision per M4).

3. Run audit:
   ```bash
   PYTHONPATH=tools python3 tools/audit_alignment.py wahlaufruf-postkarte-a6-quer
   ```
   Expected: zero suspicious-undeclared adjacencies. If non-zero, add
   the suggested constraints to CONSTRAINTS.

4. Re-render gallery (regenerates template.sla, page-NN.png,
   preview.pdf, updates meta.yml::previews_for_sla SHA, copies to
   site/public/):
   ```bash
   bin/render-gallery wahlaufruf-postkarte-a6-quer --skip-visual-diff
   ```

5. Verify staleness check passes:
   ```bash
   bin/check-stale-previews
   ```

6. Verify --all stays green:
   ```bash
   PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
   ```

7. Verify check_ci.py (non-strict default — extra-style WARNINGS are OK):
   ```bash
   python3 tools/check_ci.py templates/wahlaufruf-postkarte-a6-quer/template.sla
   ```

8. Update `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 with the row from
   `improvements/01-wahlaufruf-postkarte.md` §Session-History (line
   299-301). Replace the "_empty_ | _start of history_" stub row with
   the real entry. Update `Resulting issue` field with the GitHub URL
   for #17 (`https://github.com/GrueneAT/vorlagen/issues/33` per
   ISSUE.md frontmatter source_url).

9. Update `improvements/01-wahlaufruf-postkarte.md` §Session-History
   (line 301) with the same GitHub URL in `Resulting issue`.

10. Single-commit per ISSUE.md acceptance: build.py, meta.yml,
    DESIGN-SYSTEM-BRIEF.md, improvements/01-wahlaufruf-postkarte.md,
    template.sla, page-01.png, page-02.png, preview.pdf,
    site/public/templates/wahlaufruf-postkarte-a6-quer/* — all in one
    commit referencing #17.

---

## Out-of-Scope but Surfaced for the Planner's Awareness

- **Spec MD update** (`templates/_specs/wahlaufruf-postkarte-a6-quer.md`)
  describes the OLD layout. Spec_check.py is not in CI so this won't
  fail builds, but the spec will be LIE-after-V1. Suggest a follow-up
  issue for full spec rewrite (rather than touching it in #17 — the
  spec is 430+ lines and a rewrite blows the scope).

- **`meta.yml::slots`** inventory will go stale (12 old slot entries,
  none of the new V1 anname inventory). Same scope tradeoff — see H4.

- **`improvements/01-wahlaufruf-postkarte.md`** mentions
  `cell-body-on-green` in §"Was alle drei Varianten gemeinsam fixen"
  bullet 4: "wechselt von `fcolor=Black` auf `fcolor=White` bzw. wird
  per Variante durch `cell-body-on-green`-Variante ergänzt". This
  reinforces M2 Option B (parallel ParaStyle).

- The `gruene-zeitung-vorlage-original.sla`, `plakat-a1-hochformat-original.sla`,
  `postkarte-vorlage-original.sla` at the repo root are upstream original
  SLAs for sla_diff-validated templates. Not relevant to #17 (this
  template is DSL-only with no `original_sla:`).

---

## audit_alignment Baseline (Reference for Planner)

Run on the CURRENT layout (before V1 edits) — captures the format the
executor will see when running the audit:

```
# audit_alignment: wahlaufruf-postkarte-a6-quer
facing_pages: False
pages: 2

## Page 1 (master: 'Normal', side: n/a)
- primitives: 4
- declared pairs: 0
- suspicious-undeclared adjacencies (1):
  - axis-x drift 4.00mm: `Logo Grüne (weiss)` ↔ `Headline-Wahlaufruf`

## Page 2 (master: 'Normal', side: n/a)
- primitives: 11
- declared pairs: 12
- suspicious-undeclared adjacencies (8):
  - adjacency-y drift 9.00mm: `Logo Grüne (Bund-Dunkel)` ↔ `Cell 1 — Body`
  - adjacency-y drift 1.00mm: `Cell 1 — Headline` ↔ `Cell 1 — Body`
  - adjacency-y drift 1.00mm: `Cell 1 — Body` ↔ `Cell 3 — Headline`
  - adjacency-y drift 1.00mm: `Cell 2 — Headline` ↔ `Cell 2 — Body`
  - adjacency-y drift 1.00mm: `Cell 2 — Body` ↔ `Cell 4 — Headline`
  - adjacency-y drift 1.00mm: `Cell 3 — Headline` ↔ `Cell 3 — Body`
  - adjacency-y drift 5.00mm: `Cell 3 — Body` ↔ `Impressum`
  - adjacency-y drift 1.00mm: `Cell 4 — Headline` ↔ `Cell 4 — Body`
```

The 8 page-2 pairs disappear when the cell-loop is deleted. The 1 page-1
pair (Logo↔Headline-Wahlaufruf) disappears when Headline-Wahlaufruf is
deleted. NEW pairs introduced by V1 (per the H1 analysis):
- 3× `frage_X_headline` ↔ `frage_X_body` (each: gap=1mm, dx=0)
- 1× `logo_back` ↔ `qr_label` (gap=10.3mm, dx=0)

These are the additions to CONSTRAINTS that ISSUE.md missed.

---

## structural_check Baseline (Reference for Planner)

Run on the CURRENT layout:

```
## templates/wahlaufruf-postkarte-a6-quer
### CONSTRAINTS — 8 PASS (back-row1/row2/col1/col2 same_y/same_x/style)
### BRAND_CONSTRAINTS — 8 PASS, 3 SKIP
- SKIP brand:line_spacing_0.9
- SKIP brand:logo_size_3M
- SKIP brand:undeclared_alignment_drift
Result: 0 errors, 0 warnings, 3 skipped, 16 passes
```

Target after V1 (assuming M4 conservative, B1/B2/B3 fixed, H1 added):
- CONSTRAINTS: ~12 PASS (3 wahlkreuz + 1 distance_y + 2 same_x for
  fragen + 1 same_x for QR + 2 aligned_below for QR + 3 added stack
  aligned_below for fragen).
- BRAND_CONSTRAINTS: 8 PASS, 2 SKIP (line_spacing, logo_size_3M kept).
- 0 errors, 0 warnings.

If the planner picks M4 tighter path (also remove logo_size_3M
override): 1 SKIP, 9 PASS.

---

## Sources

### HIGH confidence (direct codebase verification)
- `tools/sla_lib/builder/constraints.py:230-519` — constraint factory + check semantics
- `tools/sla_lib/builder/brand_constraints.py:1-789` — BRAND_CONSTRAINTS rules + override mechanism
- `tools/sla_lib/builder/primitives.py:764-911` — ImageFrame + Polygon dataclass + ellipse shape
- `tools/sla_lib/builder/structural_check.py:118-204` — check_template flow
- `tools/sla_lib/builder/meta_schema.py:52-71` — load_brand_overrides
- `tools/audit_alignment.py:1-367` — audit CLI + algorithm
- `tools/render_pipeline.py:631-720` — render-gallery CLI
- `tools/check_stale_previews.py:74-128` — staleness gate
- `tools/check_ci.py:236-262` — exit-code semantics (non-strict by default)
- `.github/workflows/pages.yml:104-165` — CI gate composition
- Live runs of `structural_check` and `audit_alignment` on baseline (pre-V1)
- `shared/ci.yml` — fonts + colors verified
- `PIL.Image.open(gruene-weiss.png).size = (413, 118)` — verified scale math
- `fc-list | grep -iE "gotham|vollkorn"` — fonts registered

### MEDIUM confidence
- M5 QR ImageFrame scale_type=0 native-pixel rendering inference — based on
  reading `primitives.py:789-820` and Scribus SLA documentation; not visually
  verified post-render (visual review is a PR-review concern per ISSUE.md
  out-of-scope clause).

### LOW confidence
- None — all critical claims are traced to live tool runs or specific code lines.
