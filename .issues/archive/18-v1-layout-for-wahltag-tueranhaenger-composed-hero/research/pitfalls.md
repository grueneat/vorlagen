# Pitfalls Research — Issue 18 (V1 Composed Hero, wahltag-tueranhaenger)

**Date:** 2026-05-09
**Scope:** PITFALLS dimension. Predictive verification of every BrandRule
that could fire on the V1 layout, plus environment audit, ISSUE.md-vs-code
discrepancies, and ordering hazards.

---

## P0 — Orchestrator Prompt Inaccuracies (MUST resolve before planning)

### P0.1 — Two of the four "new BrandRules" the orchestrator names DO NOT EXIST

**What goes wrong:** The orchestrator's prompt says
> "#23 added 4 new BrandRules (registry now 14): `brand:bleed_coverage`,
> `brand:image_text_overlap`, `brand:cover_extent_match`,
> `brand:image_in_container_flush`, `brand:portrait_column_alignment`,
> `brand:visual_adjacency_drift` ..."

That is six rules, not four. Reality (verified by reading
`tools/sla_lib/builder/brand_constraints.py` lines 1052..1170):

| # | id | Source |
|---|----|--------|
| 1 | `brand:color_palette` | original |
| 2 | `brand:font_family` | original |
| 3 | `brand:line_spacing_0.9` | original |
| 4 | `brand:hl_sl_distance_x2` | original |
| 5 | `brand:logo_size_3M` | original |
| 6 | `brand:text_on_green` | original |
| 7 | `brand:bleed_3mm` | original |
| 8 | `brand:wahlkreuz_colored_bg` | original |
| 9 | `brand:inside_page` | #14 |
| 10 | `brand:spine_safety` | #22 |
| 11 | `brand:bleed_coverage` | **#23** |
| 12 | `brand:image_text_overlap` | **#23** |
| 13 | `brand:cover_extent_match` | **#23** |
| 14 | `brand:visual_adjacency_drift` | **#23** (replaces #22's `brand:undeclared_alignment_drift`) |

`brand:image_in_container_flush` and `brand:portrait_column_alignment`
were PROPOSED in archived `.issues/archive/23-stricter-alignment-…/ISSUE.md`
but the #23 PLAN.md explicitly chose NOT to ship them as separate rules
(quote from PLAN.md line 189: "**Do NOT add separate
_ImageInContainerFlush or _PortraitColumnAlignment rule classes** —
RESEARCH.md verified they would be Zeitung-specific without adding
generic detection power"). Their detection power was folded into the
4-axis `brand:visual_adjacency_drift`.

**How to avoid:** Planner MUST drop the orchestrator's "rewrite V1 vs.
add override for `brand:image_in_container_flush`" decision tree — that
rule does not exist. Same for `brand:portrait_column_alignment`. The
Portrait-inside-Hellgrün-Card 5-mm-uniform-inset is **not** a rule
violation in the current registry. It MAY surface as a
`brand:visual_adjacency_drift` warning (axis-x-left drift 5mm between
Portrait-Card x=15 and Portrait x=20), but that rule is already
overridden in this template's meta.yml and the override should stay.

**Confidence:** HIGH (read entire `brand_constraints.py`; ran
`structural_check wahltag-tueranhaenger` baseline — output confirms 14
rules, no `flush` or `column_alignment` rule).

### P0.2 — Orchestrator's prescribed CONSTRAINTS list references annames that don't exist in V1

**What goes wrong:** ISSUE.md (and orchestrator) prescribe:

```python
same_size("brand_bar_top", "brand_bar_back", axis="h", ...)
same_x("logo_weiss_front", "logo_weiss_back", ...)
same_x("stat_card_1", "stat_card_2", "stat_card_3", ...)
same_x("stat_card_1_eyebrow", "stat_card_1_hero", "stat_card_1_body", ...)
# ... and three more stat_card lines ...
aligned_below("kandidat_name", "kandidat_position", gap_mm=12.0, ...)
aligned_below("kontakt_info", "kontakt_url", gap_mm=8.0, ...)
```

Three categorical bugs:

1. **Snake-case names ≠ actual annames.** Constraint `_resolve()` matches
   on `anname` (the SLA `ANNAME` attribute). Real annames in build.py
   are: `"Brand-Bar (Vorderseite)"`, `"Brand-Bar (Rückseite)"`,
   `"Logo Grüne (weiss, top)"`, `"Logo Grüne (weiss, back-band)"`,
   `"Kandidat-Name"`, `"Kandidat-Position"`, etc. Snake-case lookups
   miss every frame → emit `severity=warning` "references missing
   anname(s)" via `_missing_violation` (constraints.py:102). ISSUE.md
   AC line "the CONSTRAINTS list is fully green" then fails.

2. **`stat_card_*` annames refer to a back-side design that V1 does
   NOT contain.** ISSUE.md's V1 BACK design (per the table on lines
   63..75) is **Portrait-Card + Visitenkarten-Footer**, NOT 3 stat
   cards. The 3-stat-stack appears only in the Alignment-YAML pseudo-spec
   on `improvements/02-wahltag-tueranhaenger.md` lines 240..272 — that
   YAML is V1's "ideal" structural spec, but the row-by-row table on
   lines 63..75 (the actually-prescribed V1 deltas) overrides it with a
   Portrait + Footer composition. ISSUE.md adopts the table version for
   layout but the YAML version for CONSTRAINTS — internally
   inconsistent.

3. **`aligned_below` argument order is reversed.** Signature is
   `aligned_below(below, above, gap_mm)` per constraints.py:507. ISSUE.md
   passes `("kandidat_name", "kandidat_position")` — but Name (y=184)
   sits ABOVE Position (y=196) visually, so correct order is
   `aligned_below(Position, Name)`. The `gap_mm=12.0` is also wrong
   (actual V1 gap = 196 - (184+11) = 1mm, not 12mm). Same shape of
   error for `("kontakt_info", "kontakt_url")` (Info y=218 below URL
   y=210, actual gap 0mm given URL.h=8, not 8mm).

   Per `_AlignedBelowConstraint.check()`: it ALSO requires `same_x`
   (left edge) of below and above (line 348). Both pairs share x=10 in
   V1, so that check is fine — it's only the y-relationship and order
   that are broken.

**How to avoid:** The planner MUST rewrite the CONSTRAINTS list from
scratch using:
- Real annames from build.py (the strings inside `anname=` kwargs).
- V1's actually-prescribed BACK composition (Portrait + Footer, NOT
  stat-cards).
- Correct `aligned_below(below_anname, above_anname, gap_mm=actual_gap)`
  signature.
- Tight tolerance values that match actual V1 geometry within 0.5mm
  (the post-#23 `brand:visual_adjacency_drift` declaration-disagreement
  detector re-runs each constraint and surfaces declarations whose
  encoded tolerance is breached by actual geometry — encode-and-silence
  no longer escapes).

**Confidence:** HIGH (read constraint resolver, factory functions,
ISSUE.md, and design source doc end-to-end).

### P0.3 — ISSUE.md AC names a rule id that doesn't exist (`brand:hl_sub_gap_2x`)

**What goes wrong:** ISSUE.md AC bullet:
> "HL/Sub-Gap deviation (50% of formula) is logged as a
> meta.yml::brand_overrides entry referencing rule `brand:hl_sub_gap_2x`
> with reason ..."

The actual registered id is `brand:hl_sl_distance_x2` (constraints.py
line 1074). The pre-existing `meta.yml::brand_overrides` entry already
uses the correct id with appropriate reason (line 30-36 of meta.yml).

`tools/sla_lib/builder/meta_schema.py:108-118` only WARNS on unknown
rule ids in overrides — does not block CI. So a `brand:hl_sub_gap_2x`
typo override would be a no-op (no rule by that id exists, nothing
gets skipped). But it's still wrong.

**How to avoid:** Plan the AC as "verify the existing
`brand:hl_sl_distance_x2` override remains in place with a reason
referencing #18; do NOT add a new `brand:hl_sub_gap_2x` entry". The
reason text in the existing override can be updated to mention #18
explicitly if desired.

**Confidence:** HIGH.

---

## P1 — Predictive Verification of All Post-#23 Rules on V1 Geometry

### P1.1 — `brand:image_text_overlap` will PASS on V1

Filled-polygon set (FILLED_POLYGON_FILLS, line 714):
`("Dunkelgrün", "Hellgrün", "Magenta", "Gelb")`. White is NOT in this
set, so the new "QR backing white polygon" (x=68 y=208 w=30 h=30
fill=White) is **not** subject to this rule. Image-on-image and
polygon-on-polygon are also not subject (rule pairs (shape, text)
only, where text is `TextFrame`).

Walked every (shape × text) pair in V1 layout (assuming the planner
implements the table on ISSUE.md lines 27..47 verbatim, with white
backing not white-fill-rule-eligible):

| Shape | Text frame | Verdict |
|-------|-----------|---------|
| Brand-Bar (Vorderseite) Dunkelgrün (-2..107, -2..14) | none in y-range | OK (no overlap candidate) |
| Hellgrün-Akzent (-2..107, 14..18) | none | OK |
| Hellgrün-Band (Wahlkreuz) (-2..107, 63..127) | none (Headline starts at 138) | OK |
| Bullets-Card Hellgrün (-2..107, 192..250) | Bullet-Liste (10..95, 200..240) | text fully INSIDE polygon → SKIP |
| Bullets-Card Hellgrün | Impressum (10..95, 242..248) | text fully INSIDE polygon → SKIP (assuming Impressum.y=242 per ISSUE.md) |
| Wahlkreuz (Hero) image (25..80, 70..125) | none in y-range | OK |
| Brand-Bar (Rückseite) (-2..107, -2..14) | none | OK |
| Logo (weiss, back-band) image (10..28.9, 8..13.7) | none | OK |
| Portrait-Card Hellgrün (15..90, 70..170) | none in y-range | OK |
| Portrait image (20..85, 75..165) | none | OK |
| Visitenkarten-Footer Dunkelgrün (-2..107, 178..250) | Kandidat-Name (10..95, 184..195) | INSIDE → SKIP |
| Visitenkarten-Footer | Kandidat-Position (10..95, 196..204) | INSIDE → SKIP |
| Visitenkarten-Footer | Kontakt-URL (10..65, 210..218) | INSIDE → SKIP |
| Visitenkarten-Footer | Kontakt-Info (10..65, 218..238) | INSIDE → SKIP |
| Visitenkarten-Footer | Impressum (back) (10..95, 242..248) | INSIDE → SKIP |
| QR (image) (70..96, 210..236) | (no text on QR) | OK |

**Prediction:** PASS clean. The pre-applied
`brand_overrides[brand:image_text_overlap]` entry (meta.yml lines 67-71)
**can and should be removed** in T07 of the planner's task ordering.

**Confidence:** HIGH (rule code at lines 717-805 read in full; geometry
walked exhaustively).

### P1.2 — `brand:cover_extent_match` will PASS on V1

Rule: vertically TOUCHING (`|y_max_a - y_min_b| < 0.5mm`) full-width
(`w >= 0.95 * page_w = 99.75mm`) frames must share outer extents
(left/right within 0.5mm).

V1 full-width frame inventory (w >= 99.75mm) — bbox listed:

Front:
- Brand-Bar (Vorderseite): (-2, -2)..(107, 14), w=109
- Hellgrün-Akzent: (-2, 14)..(107, 18), w=109
- Hellgrün-Band (Wahlkreuz): (-2, 63)..(107, 127), w=109
- Bullets-Card: (-2, 192)..(107, 250), w=109

Front touch pairs:
- Brand-Bar.bottom=14 == Akzent.top=14 → touch. Extents -2..107 == -2..107. OK.
- Akzent.bottom=18, Band.top=63 → gap 45mm, no touch.
- Band.bottom=127, Bullets-Card.top=192 → gap 65mm, no touch.

Back:
- Brand-Bar (Rückseite): (-2, -2)..(107, 14), w=109
- Visitenkarten-Footer: (-2, 178)..(107, 250), w=109

Back touch pairs:
- Brand-Bar.bottom=14, Footer.top=178 → gap 164mm, no touch.

Note: Portrait-Card (15..90, 70..170) is NOT full-width (w=75 < 99.75)
→ excluded from this rule. Correct behavior.

**Prediction:** PASS clean. Rule already PASSES on baseline (today's
build has Brand-Bar h=22 → bottom y=20 with no touching neighbor).

**Confidence:** HIGH (rule code at lines 811-879 read in full).

### P1.3 — `brand:visual_adjacency_drift` will fire ~25-50 warnings on V1

Currently OVERRIDDEN in meta.yml (lines 61-66, with reason "V1 layout
work in #18 owns alignment encoding…"). The orchestrator hopes V1 +
CONSTRAINTS will silence the rule cleanly so the override can be lifted.

**Verdict: NOT POSSIBLE on V1.** Run `tools/audit_alignment.py
wahltag-tueranhaenger` on TODAY's build to baseline: 25 suspicious
adjacencies on page 1 alone, 9+ on page 2. The rule fires on ANY pair
of frames whose dx_left, dx_right, dy_top, or dy_bottom is in
[0.5mm, 25mm] — there's no y-overlap or proximity gating. With ~10-15
frames per page and the typical "text inside polygon" composition,
combinatorial explosion is guaranteed.

Specific V1-introduced offenders (when text-inside-polygon comparisons
fire on x-edges):

- `Kandidat-Name` (x=10) ↔ `Visitenkarten-Footer` (x=-2): dx_left=12mm,
  dx_right=22mm. Both in [0.5, 25] → fires.
- `Bullet-Liste` (x=10) ↔ `Bullets-Card` (x=-2): dx_left=12mm, fires.
- `Wahlkreuz (Hero)` (x=25 in V1) ↔ `Hellgrün-Band` (x=-2): dx_left=27mm
  → outside upper bound 25, doesn't fire. But if Wahlkreuz is at x=27
  (per "x 27.5→25" ISSUE.md, hard to read), depends on exact value.
- `Portrait` (x=20) ↔ `Portrait-Card` (x=15): dx_left=5mm, fires.
  (This is the "5mm uniform inset" the orchestrator predicted would
  fire `brand:image_in_container_flush` — but that rule doesn't exist.
  It DOES fire `visual_adjacency_drift` though.)
- Logo (x=10) ↔ Brand-Bar (x=-2): dx_left=12mm, fires (also exists in
  baseline).

To silence cleanly: encode `same_x_RIGHT` constraints between bleeding
polygons and inset texts — but `same_x_right` does not exist as a
helper (constraints.py exposes only `same_x`, `same_y`, `same_size`,
`mirrored_x/y`, `inside`, `equal_gap`, `hierarchy`, `same_style`,
`distance_x/y`, `aligned_below`). The visual_adjacency_drift rule
SUGGESTS `same_x_right` in its violation messages but that helper was
never built.

**Recommendation:** Keep `brand:visual_adjacency_drift` override.
Update the reason text from "Re-enable once V1 lands…" to "Heuristic
rule produces N false positives on text-inside-polygon compositions
(see audit_alignment output). CONSTRAINTS list captures intentional
adjacencies; the visual_adjacency_drift rule remains overridden until
its detection model gates on y-overlap and adds `same_x_right`/
`same_y_bottom` helpers."

**Alternative (more aggressive):** Plan a sub-task to ADD
`same_x_right` and `same_y_bottom` helpers to `constraints.py`, then
encode each text-inside-polygon as a same_x_right declaration. Out of
scope for #18 unless the planner accepts the scope creep.

**Confidence:** HIGH (rule code at lines 886-1042 read in full;
audit_alignment baseline run).

### P1.4 — `brand:bleed_coverage` and `brand:spine_safety` are no-ops

Both have `if not getattr(doc, "facing_pages", False): return []` early
return (lines 633 and 508). The doc has `facing_pages=False` (build.py
line 60). NO-OP. ✓

**Confidence:** HIGH.

### P1.5 — `brand:inside_page` predictive check on V1

Page bbox = `[-2, 107] × [-2, 252]` (trim 105×250 + 2mm bleed).

Worst-case V1 frame: Bullets-Card (x=-2 y=192 w=109 h=58) →
bbox right = 107, bbox bottom = 250. Right edge: 107 == 107+0 (no
overshoot). Bottom edge: 250 < 252 → 2mm of slack. Same for
Visitenkarten-Footer (-2..107, 178..250).

Hellgrün-Akzent (-2 y=14 w=109 h=4) → bbox 107..18. Same logic, fits.

Portrait (x=20 y=75 w=65 h=90) → 20..85, 75..165. Inside.

QR backing (x=68 y=208 w=30 h=30) → 68..98, 208..238. Inside.

Logo (x=10 y=8 w=18.9 h=5.7) → 10..28.9, 8..13.7. Inside Brand-Bar
y range (-2..14). Inside page.

**Prediction:** PASS clean.

**Confidence:** HIGH (rule code at 382-453 read; arithmetic verified).

### P1.6 — `brand:logo_size_3M` becomes CLEAN after V1 — pre-existing override removable

Rule expects `logo.w_mm == 3 * (0.06 * kurze_kante)` ± 0.5mm. With
page=105×250, kurze_kante=105, M=6.3, expected=18.9mm.

V1 changes:
- Logo (weiss, top): 35→18.9 ✓
- Logo (weiss, back-band): 35→18.9 ✓
- Logo (Bund-Dunkel, back): DELETED — no longer applies

**Prediction:** PASS clean for both remaining logos. The pre-existing
`brand_overrides[brand:logo_size_3M]` entry (meta.yml lines 37-42) can
be REMOVED in the same T07 step that removes the
`brand:image_text_overlap` override.

**Confidence:** HIGH (rule code at 244-277 read; arithmetic verified
with Python).

### P1.7 — `brand:hl_sl_distance_x2` will fire — pre-existing override stays

Rule: HL bottom → SL top distance must equal `2 × baseline_mm = 10.8mm`
± 1.0mm. (baseline_mm=5.4 hardcoded line 195).

V1: HL `Headline-Wahltag` y=138 h=32 → bottom 170. SL `Sub-Headline`
y=176. Gap = 6mm. |6 - 10.8| = 4.8 > 1.0 → FIRE.

Override already present (meta.yml lines 30-36) — no change needed.
ISSUE.md AC item "logged as `brand:hl_sub_gap_2x`" is a typo (the rule
id is `brand:hl_sl_distance_x2`); the existing override correctly uses
the real id. AC is effectively a no-op (override already in place).

**Confidence:** HIGH.

### P1.8 — `brand:line_spacing_0.9` audit on new ParaStyles

Rule: `linesp ≈ fontsize × 0.9` ± 0.5pt (lines 167-190).

New styles to add (per ISSUE.md):
- `tueranhaenger/body-on-green`: same as `tueranhaenger/body` but
  fcolor=White. Existing `body` has fontsize=11, linesp=14 →
  14 vs 9.9 → 4.1pt drift > 0.5pt. Same style → still drifts → FIRES.
- `tueranhaenger/url-on-green`: per ISSUE.md "Vollkorn Black Italic Gelb
  11pt". If linesp=14 (matching url), 14 vs 9.9 → 4.1pt drift → FIRES.

Pre-existing override (meta.yml lines 24-29) covers ALL drift in this
template's styles → both new styles inherit the silenced state. ✓

**Confidence:** HIGH.

### P1.9 — `brand:font_family` audit on new ParaStyles

Rule: every TextFrame's resolved font must be in `shared/ci.yml::fonts`.
Allowed list:
- "Gotham Narrow Book", "Gotham Narrow Bold", "Gotham Narrow Black",
  "Gotham Narrow Ultra", "Vollkorn Black Italic"

NOT in allowed: "Gotham Narrow Book Italic" (used by current
`tueranhaenger/cand-pos`). Pre-existing override exists.

ISSUE.md V1 changes don't mention font swaps → both new styles use
allowed fonts (`Gotham Narrow Book`, `Vollkorn Black Italic`). ✓

**Confidence:** HIGH.

### P1.10 — `brand:bleed_3mm` is permanently overridden — no change

Rule expects `page.bleed_mm == 3.0`. Doc uses 2mm. Override exists. ✓

**Confidence:** HIGH.

### P1.11 — `brand:wahlkreuz_colored_bg` will fire if Hellgrün-Band's anname renamed

Rule: every frame whose anname contains "Wahlkreuz" must overlap a
Polygon (other than itself) with fill in `("Dunkelgrün", "Hellgrün",
"Magenta")`.

Current Hellgrün-Band anname is `"Hellgrün-Band (Wahlkreuz)"` — the
"(Wahlkreuz)" suffix triggers the rule. The frame IS the Hellgrün
polygon, but rule excludes self-comparison (line 356) → no overlap
found → FIRES. Pre-existing override addresses this exact case.

V1 keeps both `Wahlkreuz (Hero)` (image, satisfied by Hellgrün-Band
overlap) AND `Hellgrün-Band (Wahlkreuz)` (polygon, self-only). The
override remains essential. ✓

**Confidence:** HIGH.

---

## P2 — V1 Implementation Hazards

### P2.1 — `opacity 100%→85%` on Kandidat-Position is unsupported in DSL

**What goes wrong:** ISSUE.md V1 row: `Kandidat-Position: y 178→196,
fcolor Black→White, opacity 100%→85%`.

Searched `tools/sla_lib/builder/primitives.py`: no `opacity` parameter
on `TextFrame`. Only `SOFTSHADOWOPACITY` (for soft-shadow blocks). No
`fill_opacity`, no `TransValue` exposed.

**How to avoid:** Either (a) skip the opacity change (recommended —
white-on-Dunkelgrün at 100% reads fine), or (b) add `opacity: float =
1.0` to TextFrame and emit it as `TransValue=` in the SLA writer (out
of scope for #18). Plan default: SKIP, document as "not implemented in
V1" in the spec section.

**Confidence:** HIGH.

### P2.2 — `tueranhaenger/body` style mutation breaks page-1 Impressum reading on Bullets-Card Hellgrün (and contrast quality)

ISSUE.md V1 prescribes `Impressum (front): fcolor Black→White` (sits on
Bullets-Card Hellgrün). White-on-Hellgrün has poor contrast (Hellgrün
luminance ≈ 0.55, white ≈ 1.00 → contrast ratio ≈ 1.7:1, well below
WCAG AA 4.5:1 for body text).

This is NOT a brand-rule violation but is a brand-quality concern. Note
for the planner: V1 may want Impressum on a Dunkelgrün strip OR move
Impressum off the Hellgrün card. Default: implement as ISSUE.md says
and surface the contrast concern in the spec section / open question.

**Confidence:** MEDIUM (brand-team would weigh in).

### P2.3 — Style mutation vs. parallel-style pattern from #17

Per #17 locked decision (build.py for `wahlaufruf-postkarte-a6-quer`
lines 104-148), the migration pattern when changing fcolor is:
1. ADD a new `*-on-green` style with the new fcolor.
2. Switch the affected TextFrame's `style=` and `paragraph_style=`
   references.
3. LEAVE the original style unchanged (other templates and existing
   spec references remain valid).

ISSUE.md correctly says "Add `tueranhaenger/body-on-green`" but its V1
table reads as if it's mutating fcolor on existing frames. The correct
implementation:
- Bullet-Liste: `style="tueranhaenger/body-on-green"`
- Impressum (front): `style="tueranhaenger/body-on-green"` OR
  `tueranhaenger/impressum-on-green` (separate small-font style)
- Kandidat-Name: switch to NEW `tueranhaenger/cand-name-on-green`
  (fcolor=White, fontsize=18 per ISSUE.md)
- Kandidat-Position: switch to NEW `tueranhaenger/cand-pos-on-green`
  (fcolor=White)
- Kontakt-URL: switch to NEW `tueranhaenger/url-on-green` (fcolor=Gelb)
- Kontakt-Info: `style="tueranhaenger/body-on-green"`
- Impressum (back): `style="tueranhaenger/impressum-on-green"`

**Pitfall:** ISSUE.md explicitly names only TWO new styles
(`body-on-green`, `url-on-green`). For Kandidat-Name (18pt) and
Kandidat-Position (10pt italic) the planner needs THREE more
on-green variants OR a hybrid: keep existing `cand-name`/`cand-pos`
styles and override fcolor at the Run level — but Run-level fcolor
override conflicts with how `paragraph_style` resolves. Cleanest
solution: 5-6 new on-green styles. The planner must decide.

**Confidence:** HIGH (read #17 build.py end-to-end).

### P2.4 — Logo aspect mismatch (5%): cosmetic stretch acceptable per #17 precedent

`gruene-weiss.png` is 413×118 px (aspect 3.500). New frame 18.9×5.7mm
(aspect 3.316). 5% horizontal squash. #17 uses identical numbers
(`wahlaufruf-postkarte-a6-quer/build.py:205-209`), so this is a
sanctioned drift. No action needed beyond keeping `local_scale=(0.130,
0.130)` exact (as ISSUE.md prescribes).

**Confidence:** HIGH.

### P2.5 — Frame deletion of `Logo Grüne (Bund-Dunkel, back)` is safe

Grep for the anname across all templates and tools: zero hits except
the build.py definition itself and the SLA snapshot. CONSTRAINTS list
in current build.py doesn't reference it. Smoke test
(`templates/_smoke/test_wahltag_tueranhaenger.py`) doesn't reference
it. Spec (`templates/_specs/wahltag-tueranhaenger.md`) doesn't include
it (already drifted). Safe to delete.

**Confidence:** HIGH.

### P2.6 — `templates/_specs/wahltag-tueranhaenger.md` is ALREADY DRIFTED — needs rewrite IN this issue

`PYTHONPATH=tools python3 tools/spec_check.py wahltag-tueranhaenger`
returns 10 errors and 6 warnings on TODAY's pre-V1 build:
- Brand-Bar coords drift (-2 vs spec 0; w=109 vs spec 105; etc.)
- Headline y=128 vs spec 130, h=28 vs spec 20
- Sub-Headline y=160 vs spec 152, h=12 vs spec 10
- Spec declares anname "Stanzkontur (Außen + Loch)" → SLA has split
  "Stanzkontur Außen" / "Stanzkontur Loch"
- Spec declares "Logo Grüne (cmyk, back)" — SLA has neither
- 6 extras (Brand-Bar Rückseite, Hellgrün-Band, Logo Grüne (Bund-Dunkel,
  back), Logo Grüne (weiss, back-band), Stanzkontur Außen, Stanzkontur
  Loch)

`spec_check` is NOT in CI (verified by grepping `.github/`); it's a
local linter. But ISSUE.md AC item "spec rewrite" + the §10
DESIGN-SYSTEM-BRIEF Session-History entry imply spec must be brought
into V1 alignment.

**Plan note:** T08 (spec rewrite) is necessary not just for V1
documentation but to UNBREAK existing baseline drift. Current spec is
useless reference.

**Confidence:** HIGH (ran `spec_check` against current build).

### P2.7 — Smoke test asserts page count, layer presence, Hellgrün polygon presence — survives V1 without changes

`templates/_smoke/test_wahltag_tueranhaenger.py` has 11 tests:
- Page count == 2 ✓
- Trim 105×250mm, bleed 2mm ✓
- Stanzkontur layer with DRUCKEN=0 ✓ (still present after V1)
- Stanzkontur top-of-stack ✓
- Stanzkontur Spot color ✓
- ≥4 Stanzkontur polygons ✓ (DoorHangerCutout still emits 4)
- Stanzkontur Loch has ≥36 segments ✓
- ≥1 Hellgrün polygon on front (test_wahlkreuz_on_hellgruen_band) — V1
  has 3 Hellgrün polygons on front (Akzent + Band + Bullets-Card) ✓
- Wahlkreuz inline image ✓
- Round-trip postkarte sla_diff ✓ (unrelated)

**Prediction:** All 11 tests pass after V1 implementation. NO smoke
test rewrite needed. The orchestrator's "T05 smoke test rewrite" is
likely unnecessary — verify before adding scope.

**Confidence:** HIGH (read entire smoke test; ran it on baseline).

### P2.8 — Stanzkontur layer reference is correct in build.py

ISSUE.md correctly does NOT add new polygons on the Stanzkontur layer
(it stays for `DoorHangerCutout` only). All new V1 polygons MUST use
`layer=LAYER_HINTERGRUND` (idx 0) for backgrounds OR `LAYER_BILDER`
(idx 1) for visual elements. Bullets-Card / Hellgrün-Akzent / Portrait-
Card / Visitenkarten-Footer / Hellgrün-Band — all backgrounds → use
`layer=LAYER_HINTERGRUND`. The QR backing white polygon: also background
to QR (renders behind it) → `layer=LAYER_HINTERGRUND`.

**Pitfall to avoid:** A polygon mistakenly placed on Stanzkontur layer
would be `printable=False` and invisible in print output. The
`test_stanzkontur_polygons_present_on_layer` smoke test counts polys
on Stanzkontur layer expecting exactly 4 (outer + hole on each page).
Adding a 5th would silently fail the printability of one polygon.

**Confidence:** HIGH.

### P2.9 — Existing `Logo Grüne (cmyk, back)` line in build.py refers to deleted asset

Spec mentions `Logo Grüne (cmyk, back)` (`_specs/wahltag-tueranhaenger.md`
expected anname). Build.py has no such frame today — the spec is stale.
Confirms #2.6 — spec rewrite is mandatory.

### P2.10 — Hole-zone non-overlap verified

Hole spans y=25..60 (`hole_top_offset=25`, `diameter=35`, center y=42.5).
V1 frames in y=20..70 range:
- Hellgrün-Band starts at y=63 (not 65 in V1) → no overlap (hole bottom
  at 60).
- Hellgrün-Akzent ends at y=18 → no overlap.
- All other V1 frames are above y=18 or below y=70.

**Prediction:** No frame overlaps the hole zone. Visual quality preserved.

**Confidence:** HIGH.

---

## P3 — Environment & Tooling

### P3.1 — Python + libraries available

| Tool | Version | Purpose |
|------|---------|---------|
| python3 | 3.13.5 | DSL builder, structural_check, spec_check |
| python3 stdlib (unittest, dataclasses, importlib, hashlib, json, re) | OK | Tests + helpers |
| python3-yaml | OK | meta.yml parsing |
| python3-lxml | OK | SLA parsing |
| jsonschema | 4.26.0 | meta_schema validation |
| Pillow | 12.2.0 | crop_for_frame, qr_gen |
| pyzbar | 0.1.9 | qr verification (optional) |

No new deps required for V1. `unittest` discovery via `python3 -m
unittest discover tools/sla_lib/tests` (CI form).

**Confidence:** HIGH.

### P3.2 — Scribus headless requires `xvfb-run` wrapper

`scribus --version` directly fails: `qt.qpa.xcb: could not connect to
display`. `QT_QPA_PLATFORM=offscreen scribus` ALSO fails — this Scribus
build doesn't ship the offscreen plugin.

Working invocation (from `tools/visual_diff.py:131-138`):
```
xvfb-run -a --server-args="-screen 0 1024x768x24" \
  scribus -g -ns -py tools/_export_pdf.py <sla> <pdf>
```

`bin/render-gallery wahltag-tueranhaenger --skip-visual-diff` invokes
this internally and pdftoppm for PNG previews. `xvfb-run` and
`pdftoppm` are both available in the dev environment (`/usr/bin/`).

**Pitfall:** If `bin/render-gallery` is run without xvfb-run env, it
spawns scribus that fails silently or hangs. Always go through
`bin/render-gallery` (which wraps it correctly) — never invoke scribus
directly.

**Confidence:** HIGH (probed env; read visual_diff.py).

### P3.3 — `previews_for_sla` SHA bump is automatic via `bin/render-gallery`

`render_pipeline._update_meta_hash` (line 290-335) handles SHA
maintenance via regex find-replace on `meta.yml`. Idempotent.
Single-line form: `previews_for_sla: <hex>`. The current value
`6a744dff...8d8be` will change automatically when V1 lands and
`bin/render-gallery` runs.

`bin/check-stale-previews` (run in CI per pages.yml line 113) verifies
SHA(template.sla) == meta.yml::previews_for_sla. Forgetting the SHA
bump → CI fail.

**Confidence:** HIGH.

### P3.4 — `tools/check_ci.py` is informational, not blocking

CI invokes it as `|| true` (pages.yml line 146). It already emits 8
warnings on the current build (extra-color Stanzkontur, 7 extra-styles
tueranhaenger/*) — V1 will add a few more (`body-on-green`, `url-on-
green`, possibly `cand-name-on-green`, etc.). All "warning"-level extras
are silent in CI.

ISSUE.md AC says "tools/check_ci.py passes" — interpret as "no
critical-severity issues" (current baseline already meets this). No
action required.

**Confidence:** HIGH.

### P3.5 — `structural_check --all` baseline is GREEN — V1 must keep it green

Current baseline (rerun today): `0 errors, 122 warnings, 2 skipped, 33
passes`. The 122 warnings are all from `brand:visual_adjacency_drift`
on Zeitung — which still runs there (not overridden) and emits warnings
intentionally. CI accepts warnings; ERRORS would fail.

V1 must produce zero ERRORS. Per P1.* analysis, V1 should produce zero
errors AND keep approximately the same warning count.

**Confidence:** HIGH.

---

## P4 — Atomic-PR Ordering

The orchestrator suggests T01..T08. Refined ordering with
dependency rationale:

| # | Task | Depends on | Why |
|---|------|------------|-----|
| T01 | Add new ParaStyles (`body-on-green`, `url-on-green`, +3 if needed for cand-name/pos/info) to `build.py` | — | Pure addition; doesn't change frames yet |
| T02 | Front layout: brand-bar shrink, akzent polygon, band y/h, Wahlkreuz x/w/h, headline y/h/linesp, sub y, Bullets-Card polygon, bullets y/h/style switch, impressum style switch, logo size+local_scale | T01 | All front-frame edits in one commit |
| T03 | Back layout: brand-bar shrink, logo size+local_scale, DELETE Bund-Dunkel logo, Portrait-Card polygon, Portrait h, Visitenkarten-Footer polygon, Kandidat-Name y/fontsize/style switch, Kandidat-Position y/style switch, Kontakt-URL y/w/style switch, Kontakt-Info y/w/style switch, QR x/y/w/h+backing polygon, Impressum y/style switch | T01 | All back-frame edits in one commit |
| T04 | Rewrite CONSTRAINTS list using REAL annames + correct aligned_below order + actual gap_mm values | T02, T03 | Verifies T02+T03 geometry |
| T05 | (Conditional — skip if smoke passes) Update smoke test only if `_smoke/test_wahltag_tueranhaenger.py` regresses | T02, T03 | Per P2.7, no rewrite expected |
| T06 | Run `bin/render-gallery wahltag-tueranhaenger --skip-visual-diff`; commit regenerated `template.sla` + `preview.pdf` + `page-NN.png` + bumped `meta.yml::previews_for_sla` | T02, T03 | Mandatory at end |
| T07 | Remove pre-applied overrides that V1 makes unnecessary: `brand:image_text_overlap` (per P1.1), `brand:logo_size_3M` (per P1.6). Update `brand:visual_adjacency_drift` reason text to reflect heuristic limitation (per P1.3). KEEP `brand:hl_sl_distance_x2`, `brand:line_spacing_0.9`, `brand:font_family`, `brand:bleed_3mm`, `brand:wahlkreuz_colored_bg` — all still needed | T02, T03, T06 | Override changes after geometry stable |
| T08 | Rewrite `templates/_specs/wahltag-tueranhaenger.md` to match V1 (currently 10-error drifted) + DESIGN-SYSTEM-BRIEF.md §10 row + improvements/02-…md Session-History GitHub URL update | T02, T03 | Documentation; can run in parallel with T06 |
| T09 (NEW) | Add invariant-pinning test `tools/sla_lib/tests/test_tueranhaenger_geometry.py` modeled on `test_zeitung_geometry.py`. Pin RELATIONSHIPS not coordinates (e.g., `Brand-Bar.bottom == Akzent.top`, `Portrait inside Portrait-Card`, `Footer extends to bleed`, `Bullets-Card top below Sub-Headline bottom`) | T02, T03 | Per #23 locked decision #7 — relationship-pinning survives float-imprecise SLA round-trip |

**Pitfall:** Doing T06 BEFORE T04 means CONSTRAINTS list still contains
the broken stat_card refs and `--skip-visual-diff` will not catch the
warning. Order T04 → T06.

**Pitfall:** Doing T07 BEFORE T06 means meta.yml SHA might bump
unrelated to the geometry change. Order T06 → T07.

---

## P5 — Test Strategy (Per #23 Locked Decision #7)

### P5.1 — Coordinate-pinning is BAD; relationship-pinning is GOOD

Float-imprecise round-trip via Scribus emit converts `w_mm=109` →
`WIDTH="308.97637795275594"` (pt) → reads back as `109.0000000...`
plus possible last-bit drift to `108.9999999...`. Coordinate equality
with `assertEqual(x_mm, 109.0)` fails. Use `assertAlmostEqual(x,
expected, delta=0.5)` for everything.

### P5.2 — Recommended invariant tests (T09)

Pattern: `_load_doc()` from `templates/wahltag-tueranhaenger/build.py`,
then assertion blocks per invariant. Each test should pin ONE
relationship.

Suggested invariants for V1:
- Brand-Bar bottom y == Hellgrün-Akzent top y (delta=0.5)
- Brand-Bar (front) and Brand-Bar (back) share h (delta=0.5)
- Logo (weiss, top) and Logo (weiss, back) share x and y (delta=0.5)
- Logo width == 18.9mm (delta=0.5) — pins `brand:logo_size_3M` compliance
- Wahlkreuz center == page center (delta=0.5)
- Hellgrün-Band contains Wahlkreuz (bbox containment ± 0.5)
- Portrait-Card contains Portrait (bbox containment ± 0.5)
- Visitenkarten-Footer contains Kandidat-Name, Position, URL, Info,
  Impressum (5 containment checks)
- Bullets-Card contains Bullet-Liste, Impressum (front)
- Visitenkarten-Footer right edge >= page_w + bleed - 0.5 (bleeds out)
- Bullets-Card right edge >= page_w + bleed - 0.5
- Hellgrün-Akzent right edge >= page_w + bleed - 0.5
- Brand-Bar (both pages) right edge >= page_w + bleed - 0.5
- Sub-Headline.y > Headline.y + Headline.h (vertical order)
- Bullets-Card.y > Sub-Headline.y + Sub-Headline.h
- Visitenkarten-Footer.y > Portrait-Card.y + Portrait-Card.h

These pinned relationships survive any future legitimate retuning that
preserves intent.

**Confidence:** HIGH (pattern lifted from `test_zeitung_geometry.py`
which already exists and runs in CI).

---

## P6 — Cross-Template Reference Audit

`grep -rn "tueranhaenger/" templates/ tools/` confirms:
- `tueranhaenger/headline`, `/sub`, `/body`, `/cand-name`, `/cand-pos`,
  `/url`, `/impressum` are referenced ONLY in
  `templates/wahltag-tueranhaenger/build.py` and
  `templates/_specs/wahltag-tueranhaenger.md`. Zero cross-template uses.
- New `*-on-green` styles will be introduced fresh; no risk of
  cross-template collision.

`grep -rn "Logo Grüne (Bund-Dunkel" templates/`: ONLY in
`templates/wahltag-tueranhaenger/build.py:308` and the SLA snapshot.
Zero cross-template uses. Deletion is safe.

`grep -rn "Brand-Bar (Vorderseite)"` etc. — annames are scoped to this
template, no collisions.

**Confidence:** HIGH.

---

## P7 — Open Questions for Planner

1. **Stat-cards vs. Portrait-Card:** ISSUE.md table (the actual V1 deltas)
   describes Portrait-Card; ISSUE.md's CONSTRAINTS list and the design
   doc's "Alignment-Beziehungen" YAML describe stat-cards. Pick ONE.
   Recommendation: Portrait-Card (matches the table; matches the
   "Composed Hero" name; stat-cards belong to a different variant).

2. **Number of new ParaStyles:** ISSUE.md names 2 (`body-on-green`,
   `url-on-green`) but V1 needs at least 5 if we follow the #17 parallel
   pattern strictly: `body-on-green`, `url-on-green`,
   `cand-name-on-green` (18pt White), `cand-pos-on-green` (10pt italic
   White), `impressum-on-green` (6pt White). Confirm scope.

3. **Opacity 85% on Kandidat-Position:** unsupported in DSL. Drop?
   Implement as a feature (out of scope)? Plan default: drop.

4. **White-on-Hellgrün impressum contrast:** WCAG fail. Brand-team
   review needed OR move impressum to Dunkelgrün strip OR keep on
   Bullets-Card with Dunkelgrün fcolor. Plan default: keep ISSUE.md
   spec, surface as a follow-up issue.

5. **`brand:visual_adjacency_drift` override stays?** Per P1.3, yes.
   But this contradicts the existing override's reason ("Re-enable once
   V1 lands"). Explicit decision needed.

6. **Spec rewrite scope:** spec is currently 10-error drifted from
   pre-V1. Rewriting in T08 means rewriting BOTH the V1 deltas AND the
   pre-V1 drift. ~50 lines of spec text. Confirm scope.

7. **Remove `brand:logo_size_3M` override?** P1.6 says yes. Confirm.

8. **Remove `brand:image_text_overlap` override?** P1.1 says yes.
   Confirm — this is the orchestrator's #23-mentioned scheduled audit
   completion.

---

## P8 — Risk Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| ISSUE.md CONSTRAINTS use phantom annames (P0.2) | BLOCKER | Plan rewrites CONSTRAINTS using actual annames + correct aligned_below order |
| Two phantom rules in orchestrator prompt (P0.1) | BLOCKER | Plan ignores `brand:image_in_container_flush` and `brand:portrait_column_alignment` decision trees |
| `brand:hl_sub_gap_2x` AC item is a typo (P0.3) | LOW | Use real id `brand:hl_sl_distance_x2`; existing override stays |
| `opacity 85%` unsupported (P2.1) | MEDIUM | Drop from V1 |
| White-on-Hellgrün impressum contrast (P2.2) | MEDIUM | Document as known issue, defer |
| Style mutation vs. parallel pattern confusion (P2.3) | HIGH | Follow #17 parallel-style pattern; add 5+ new on-green styles |
| Smoke test allegedly needs rewrite (orchestrator T05) | NONE | P2.7 verifies smoke passes V1 unmodified |
| `previews_for_sla` SHA stale (P3.3) | LOW | Always run `bin/render-gallery` last |
| Spec drift compounds (P2.6) | MEDIUM | T08 mandatory; rewrite full spec |
| `visual_adjacency_drift` cannot be silenced cleanly (P1.3) | MEDIUM | Keep override; refine reason text |
| Logo aspect 5% squash (P2.4) | NONE | Per #17 precedent, accepted |
| Stanzkontur layer pollution (P2.8) | LOW | Audit each new Polygon's `layer=` value |

---

## P9 — Metadata

**Sources verified:**
- `tools/sla_lib/builder/brand_constraints.py` — read in full (1171 lines)
- `tools/sla_lib/builder/constraints.py` — read in full (550+ lines)
- `tools/sla_lib/builder/structural_check.py` — read relevant sections
- `tools/sla_lib/builder/meta_schema.py` — read in full (~120 lines)
- `tools/sla_lib/builder/primitives.py` — searched for opacity / local_scale
- `tools/sla_lib/builder/blocks.py` — searched DoorHangerCutout
- `tools/sla_lib/tests/test_zeitung_geometry.py` — read full test patterns
- `templates/wahltag-tueranhaenger/build.py` — read in full (460 lines)
- `templates/wahltag-tueranhaenger/meta.yml` — read in full (164 lines)
- `templates/_smoke/test_wahltag_tueranhaenger.py` — read in full (148 lines)
- `templates/wahlaufruf-postkarte-a6-quer/build.py` — read #17 ParaStyle pattern
- `improvements/02-wahltag-tueranhaenger.md` — read Variante 1 + Alignment sections
- `shared/ci.yml` — read in full (allowed fonts/colors/styles)
- `.issues/archive/23-…/ISSUE.md` and `PLAN.md` — verified phantom rule status
- `.github/workflows/pages.yml` — verified CI gates
- `tools/render_pipeline.py` — checked SHA bump + scribus invocation
- `tools/visual_diff.py` — checked xvfb-run wrapping
- `tools/check_ci.py` — checked target syntax + severity model

**Live commands run:**
- `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger` — confirmed 14 rules, current baseline 0/0/8/10
- `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all` — 0/122/2/33 baseline
- `PYTHONPATH=tools python3 tools/spec_check.py wahltag-tueranhaenger` — confirmed 10-error spec drift
- `PYTHONPATH=tools python3 tools/audit_alignment.py wahltag-tueranhaenger` — confirmed 25+ adjacency warnings
- `PYTHONPATH=tools python3 -m unittest templates._smoke.test_wahltag_tueranhaenger` — confirmed 11/11 pass
- `python3 templates/wahltag-tueranhaenger/build.py` — confirmed clean baseline build
- `python3 -c "from PIL import Image; ..."` — confirmed logo asset 413×118 → aspect 3.500
- Env probe: python3 3.13.5, yaml/lxml/jsonschema/Pillow available, scribus + xvfb-run + pdftoppm available

**Confidence breakdown:** All findings HIGH except P2.2 (white-on-
hellgrün contrast — MEDIUM, brand-team judgment) and P7 open
questions (DEFERRED — require user decision).
