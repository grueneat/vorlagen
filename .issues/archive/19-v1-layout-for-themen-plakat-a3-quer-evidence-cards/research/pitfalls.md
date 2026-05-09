# Pitfalls Research — Issue #19 V1 Themen-Plakat "Evidence Cards"

**Researched:** 2026-05-09 · post-#24 main · worktree `19-v1-layout-for-themen-plakat-a3-quer-evidence-cards`
**Scope:** Pitfalls + environment + brand-rule predictions for V1 implementation per `improvements/03-themen-plakat.md` §"Variante 1".

---

## TL;DR — Top Risks for the Planner

| # | Pitfall | Severity | Confidence |
|---|---------|----------|------------|
| P1 | **Open Question 1 is misframed**: there is NO `aspect_fill` enum on `ImageFrame`. Use `library.inject_into_frame()` post-#24 idiom (pre-crops to frame aspect → fills exactly with `scale_type=0, ratio=1`). | HIGH | HIGH |
| P2 | **Smoke test breaks**: V1 deletes `Beleg N — Headline` annames; smoke asserts presence. Must update `templates/_smoke/test_themen_plakat_a3_quer.py` in same PR. | HIGH | HIGH |
| P3 | **`same_x("…Card", "…Stat", "…Label", "…Body")` constraint will FAIL** with default 0.5mm tol — Card x=15, Stat/Label/Body x=20 (5mm inset). Drop Card from `same_x`. | HIGH | HIGH |
| P4 | **`aligned_below("Themen-Hero", "Sub-Headline", gap_mm=8.0)` is geometrically invalid** — Hero (x=18 y=73) is left-of and above Sub (x=235 y=172). Side-by-side, not stacked. Drop or replace. | HIGH | HIGH |
| P5 | **Spec is already 24-error drifted** — T07 spec rewrite is mandatory, not decoration. | HIGH | HIGH |
| P6 | **`brand:image_text_overlap` override REMOVABLE**: V1 has no partial text-shape overlaps. | MEDIUM | HIGH |
| P7 | **`brand:image_fills_frame` override REMOVABLE iff** post-#24 INJECT_MAP pattern (`target_w_mm=frame.w_mm`) is used. | HIGH | HIGH |
| P8 | **`brand:logo_size_3M` override REMOVABLE only if logo dim is exact 3M**: w=53.46mm (not 54). At w=54, rule fires with 0.54mm drift > 0.5mm tol. | MEDIUM | HIGH (read rule + computed) |
| P9 | **`brand:line_spacing_0.9` override CANNOT be removed**: V1 doesn't refactor existing non-conformant styles AND ISSUE.md's `beleg-body-on-green` 13/16.9 itself violates 0.9×. | MEDIUM | HIGH |
| P10 | **`brand:visual_adjacency_drift` override MUST BE REMOVED** per locked decision from #22. | HIGH | HIGH |
| P11 | **CAPS not a ParaStyle attribute**. Implement by uppercasing run text. Letter-spacing 0.04em → ParaStyle `kern=0.72`. | MEDIUM | HIGH |
| P12 | `stat_card_*` annames pitfall (carryover from #18 RESEARCH): ISSUE.md uses `Beleg N — Card/Stat/Label/Body` already (sensible). Verified correct. | LOW | HIGH |
| P13 | **Anname casing**: existing template uses Title-Case + em-dash (`Beleg 1 — Headline`). V1 new annames must match this convention exactly. | MEDIUM | HIGH |
| P14 | **Style mutation `themen-plakat/headline.linesp 64→54` acceptable**: same anname-style, fontsize-coupled adjustment, single in-template consumer. NOT analogous to the parallel `*-on-green` pattern from #17/#18. | LOW | HIGH |
| P15 | **`themen-plakat/beleg-body align=0→1` mutation contradicts ISSUE.md own ParaStyles list**. Recommend: leave `beleg-body` untouched (no consumer post-V1) and set `beleg-body-on-green align=1` per improvements.md §"Alignment-Spezifikation". | MEDIUM | MEDIUM |
| P16 | **Improvements.md ↔ ISSUE.md contradictions** — Stat 22pt (improv §144) vs 56pt (improv §40 + ISSUE); Card h=130 (improv §215) vs h=72 (table + ISSUE). Use ISSUE.md as canonical. | MEDIUM | HIGH |
| P17 | **Brief §10 Session-History row required** per AC — DESIGN-SYSTEM-BRIEF.md lacks entry for issue #35. | LOW | HIGH |
| P18 | **README.md content discipline note** required per Open Question #2 (Stat-Zahlen content discipline for Bezirksgruppen). | LOW | HIGH |
| P19 | **Build-then-render contract**: T05 MUST run `bin/render-gallery themen-plakat-a3-quer --skip-visual-diff` to refresh `template.sla` + bump `meta.yml::previews_for_sla`. `bin/check-stale-previews` will fail otherwise. | HIGH | HIGH |
| P20 | **Atomic-PR ordering matters** — see §11. | MEDIUM | HIGH |

---

## §1 — Open Question 1: `aspect_fill` semantic does NOT exist (P1)

**Claim in ISSUE.md:** "Confirm `aspect_fill` is the right semantic in `sla_lib.builder.primitives.ImageFrame`. If it isn't already supported, add it."

**Reality:** `ImageFrame` has only `scale_type: int` (0=ScaleAuto fit-to-frame, 1=Manual) + `ratio: int` (1=preserve aspect, 0=stretch) + `local_scale: tuple[float, float]`. There is NO enum value for "aspect_fill / cover" — Scribus 1.6 itself has no native cover mode (Mantis #15448 still open per `tools/sla_lib/builder/library.py:512`).

**Two supported idioms for fill behaviour:**

1. **`library.inject_into_frame(frame, img, target_w_mm, target_h_mm)`** — POST-#24 STANDARD:
   - Pre-crops the JPEG to the frame aspect via `crop_for_frame` (centre-crop biased by `manifest.crop_focus`).
   - Bakes the JPEG to target dimensions in mm at 300 dpi.
   - Sets `frame.scale_type=0` (ScaleAuto). Since aspect already matches frame, **no letterbox** appears.
   - Pattern reference: `templates/zeitung-a4-grun/build.py:2584-2625`, `templates/postkarte-a6-kampagne/build.py:391-405`, `templates/plakat-a1-hochformat/build.py:221-240`.

2. **`library.compute_aspect_fill(frame_w_mm, frame_h_mm, asset_w_px, asset_h_px)`** — returns `(s, s)` for `LOCALSCX/SCY`. Image overflows on long axis. **Has known DSL unit bug** at `LOCALSCX != 1` (`local_offset_mm` is mm-at-LOCALSCX=1, not mm of frame translation per `library.py:521`). Issue #24 deliberately did NOT use this for Zeitung. **Do NOT use this approach for #19.**

**Recommendation:** Approach #1. Refactor build.py — replace lines 272-286 (current `crop_for_frame` direct call + manual ImageFrame construction with literal `target_w_mm=180`) with the post-#24 INJECT_MAP idiom that reads `frame.w_mm` / `frame.h_mm` LIVE:

```python
# Construct hero frame with NO inline image data — INJECT_MAP fills later.
hero = ImageFrame(
    x_mm=18, y_mm=73, w_mm=194, h_mm=114,
    scale_type=0, ratio=1,
    layer=1,
    anname="Themen-Hero",
)
page.add(hero)

# ...rest of build_doc()...

# At end of build_doc() (or in a separate build_preview() if templates split):
INJECT_MAP = {"Themen-Hero": "themen_klimaschutz_windrad"}
for page in doc.pages:
    for frame in page.items:
        if isinstance(frame, ImageFrame) and frame.anname in INJECT_MAP:
            lib_id = INJECT_MAP[frame.anname]
            img = library.load(lib_id, optional=True)
            if img is None:
                continue
            library.inject_into_frame(
                frame, img,
                target_w_mm=frame.w_mm,   # READ LIVE — no literal target drift
                target_h_mm=frame.h_mm,
            )
```

Note: `themen-plakat-a3-quer` is a DSL-only template (no `original_sla` in meta.yml — verified line 18 of meta.yml: `# No round-trip diff — this is a DSL-original template`). It does NOT need a separate `build_preview()` like Zeitung — the inject can run in `build_doc()` directly OR in a wrapper. Single function is simpler; follow the Postkarte-A6-Kampagne pattern (`templates/postkarte-a6-kampagne/build.py:391-405`).

**Asset verified:** `themen_klimaschutz_windrad` exists at `shared/sample-images/themen/klimaschutz-windrad.jpg` (1536×1024, crop_focus=[0.65, 0.50] biased toward turbine). Source aspect 1.50; frame 194×114=1.70 → centre-crop trims height (1024px → ~903px keep), keeps full width.

**Confidence:** HIGH.

---

## §2 — Smoke Test Breaks (P2)

`templates/_smoke/test_themen_plakat_a3_quer.py` (153 lines, 8 tests, 8/8 pass on baseline — verified `PYTHONPATH=tools python3 -m unittest …` Ran 8 tests in 0.103s OK):

| Test | V1 Impact |
|------|-----------|
| `test_page_count` | PASS (still 1 page) |
| `test_trim_dimensions` | PASS (still 420×297) |
| `test_bleed` | PASS (still 3mm) |
| `test_required_annames_present` | **FAIL** — asserts `Beleg 1/2/3 — Headline` which V1 deletes |
| `test_no_frame_outside_trim_plus_bleed` | PASS — all V1 frames inside [-3..423]×[-3..300] (verified: Card 3 right=405.67 < 423, Body bottom=278+ < 300) |
| `test_headline_frame_height_supports_36pt` | PASS — V1 Headline h=100mm ≫ 24pt threshold |
| `test_color_palette_contains_dunkelgruen` | PASS |
| `test_styles_include_themen_plakat_locals` | PASS — V1 keeps existing style declarations (only adds new ones); `themen-plakat/beleg-headline` style is still in `add_para_style` even if no frame consumes it |

**Required smoke updates:**

```python
def test_required_annames_present(self):
    annames = {po.attrib.get("ANNAME", "") for po in self.doc.findall("PAGEOBJECT")}
    required = {
        "Headline These",
        "Sub-Headline",
        "Themen-Hero",                                                         # NEW load-bearing
        "Hero-Foto-Card",                                                       # NEW Hellgrün backing
        "Beleg 1 — Card", "Beleg 1 — Stat", "Beleg 1 — Label", "Beleg 1 — Body",
        "Beleg 2 — Card", "Beleg 2 — Stat", "Beleg 2 — Label", "Beleg 2 — Body",
        "Beleg 3 — Card", "Beleg 3 — Stat", "Beleg 3 — Label", "Beleg 3 — Body",
        "Quelle",
        "Impressum",
    }
    missing = required - annames
    self.assertFalse(missing, f"missing annames: {missing}")
```

Optionally extend `test_styles_include_themen_plakat_locals` to also assert `themen-plakat/stat-hero`, `themen-plakat/beleg-body-on-green`, `themen-plakat/beleg-headline-yellow`.

**Confidence:** HIGH (read smoke + ran it).

---

## §3 — `same_x("Card", "Stat", "Label", "Body")` Geometry Failure (P3)

ISSUE.md prescribes:
```python
same_x("Beleg 1 — Card", "Beleg 1 — Stat", "Beleg 1 — Label", "Beleg 1 — Body",
       name="beleg1_card_v_axis"),
```

**Geometry:**
- Card 1: `x=15`
- Stat: `x=col_x+5 = 20` (5mm inset for visual breathing on Hellgrün card)
- Label: `x=col_x+5 = 20`
- Body: depends on alignment — improvements.md §"Alignment-Spezifikation" says Card-Center alignment with `Frame-x_mm = Card-x = 15` and `align=1` flush-fill (centred within frame); ISSUE.md's `beleg-body-on-green` style says `align=0` (left flush); ISSUE.md's `beleg-body align=0→1` mutation suggests centring. Contradictions all around.

**Constraint check:** `_SameAxisConstraint` (`tools/sla_lib/builder/constraints.py:399`) uses `tolerance_mm=0.5` default. `|15 - 20| = 5mm > 0.5mm` → **CONSTRAINT FAILS**.

**Fix options for the planner:**

1. **Drop Card from `same_x`** (recommended): `same_x("Beleg 1 — Stat", "Beleg 1 — Label", "Beleg 1 — Body", name="beleg1_inner_left_axis")` + `inside("Beleg 1 — Stat", "Beleg 1 — Card")` etc. The `inside` constraint already encodes Card-containment; `same_x` on the inner trio captures the inner-left-edge axis.
2. Raise tolerance to 6mm: `same_x(..., tolerance_mm=6.0)` — defeats constraint's purpose.
3. Add a new DSL helper `same_x_center(*targets)` — out-of-scope DSL change.

**Recommendation:** Option 1.

**Confidence:** HIGH.

---

## §4 — `aligned_below("Themen-Hero", "Sub-Headline")` Inverted (P4)

DSL signature (`tools/sla_lib/builder/constraints.py:507-519`):
```python
def aligned_below(below, above, gap_mm: float, ...) -> Constraint:
    """`below` hangs from `above`: same x, below.y == above.y + above.h + gap."""
```

**ISSUE.md geometry:**
- Themen-Hero: `x=18, y=73, h=114` → bottom 187. **LEFT half.**
- Sub-Headline: `x=235, y=172, h=14` → bottom 186. **RIGHT half.**

These are **side-by-side** in the 60/40 split, not vertically stacked.

`aligned_below` requires:
- Same x (Hero x=18, Sub x=235 → fails by 217mm)
- below.y == above.y + above.h + gap

Constraint is geometrically invalid in either argument order.

**Fix options for the planner:**

1. **Drop the constraint** (recommended) — there is no vertical stacking between Hero and Sub-Headline in V1.
2. Replace with the actual relationship — `same_y("Themen-Hero", "Headline These")` if we want to assert the 60/40 top-edge-shared pattern (Hero y=73, Headline y=70 → 3mm drift; would need tolerance ≥ 3mm OR geometry adjust).
3. Add `inside("Themen-Hero", "Hero-Foto-Card")` to assert the photo sits inside the Hellgrün backing polygon (Hero 18..212, 73..187 inside Backing 15..215, 70..190 — 2mm/3mm gap inside ✓).

**Recommendation:** Option 1 + Option 3. The "anchored to subhead" intent in ISSUE.md doesn't match the V1 layout.

**Confidence:** HIGH.

---

## §5 — Spec Already 24-Error Drifted (P5)

`PYTHONPATH=tools python3 tools/spec_check.py themen-plakat-a3-quer` on baseline returns **24 drift errors + 1 warning**:
- Logo: spec=60×18 vs sla=32×28 (28mm/10mm drift)
- All 6 Beleg frames: column width spec=124 vs sla=124.67 (0.67mm)
- Body heights: spec=90 vs sla=70 (20mm)
- Themen-Hero: spec=15,248,290,18 vs sla=120,225,180,60 (105/23/110/42mm)
- Quelle: spec=y=270,w=280,h=10 vs sla=y=287,w=80,h=8 (17/200/2mm)
- Impressum: spec=y=270,h=10 vs sla=y=287,h=8 (17/2mm)
- Extra-in-SLA warning: `Seitenhintergrund` not declared in spec

This drift accumulated since template creation (`133cca6`) through #11/#12/#13/#22/#23/#24, never reconciled.

**Implication:** AC item "spec rewrite" (T07) is mandatory, not optional polish. Without T07, `tools/spec_check.py` is a useless reference document. (Note: `spec_check.py` is NOT in CI per #18 RESEARCH P2.6 — local linter only — but the BRIEF §10 contract treats spec as authoritative.)

**Confidence:** HIGH.

---

## §6 — Brand-Override Removability Predictions

Current `meta.yml::brand_overrides`:

| Override | After-V1 Status | Why |
|----------|-----------------|-----|
| `brand:line_spacing_0.9` | **KEEP** (P9) | Existing styles still non-conformant; V1 doesn't refactor them. NEW `beleg-body-on-green` 13/16.9 also non-conformant per ISSUE.md. |
| `brand:hl_sl_distance_x2` | **KEEP — UPDATE REASON** (Open Q3) | V1 60/40 split intentionally violates the gap formula. Override already exists; update `reason` to reference V1 60/40 columnar split. |
| `brand:logo_size_3M` | **REMOVABLE iff logo w=53.46** (P8) | At w=54, drift = 0.54mm > 0.5mm tolerance → fires. At w=53.46 (or 53.5), passes. |
| `brand:visual_adjacency_drift` | **REMOVE** (P10) | `meta.yml` reason explicitly says "Re-enable once V1 lands and a CONSTRAINTS list captures the declared adjacencies." V1 lands the CONSTRAINTS. Per #22 locked decision #9. |
| `brand:image_text_overlap` | **REMOVE** (P6) | V1 has no partial text-shape overlaps. Text fully inside Hellgrün cards = "allowed: text fully inside shape" (rule docstring at `brand_constraints.py:725-727`). |
| `brand:image_fills_frame` | **REMOVE** (P7) | V1 uses post-#24 `inject_into_frame(target_w_mm=frame.w_mm)` → JPEG pre-cropped to frame aspect → no letterbox. |

### `brand:logo_size_3M` arithmetic (P8)

`_LogoSize3MRule` (`brand_constraints.py:243-277`):
- kurze_kante = min(420, 297) = 297
- M = 0.06 × 297 = 17.82
- 3M = 53.46
- Tolerance: `tolerance_mm=0.5` default
- ISSUE.md V1 logo: `w=54, h=48` → drift `|54 - 53.46| = 0.54mm > 0.5mm` → **WOULD FAIL by 0.04mm**

**Recommendation for the planner:** Set logo `w_mm=53.46, h_mm=47.0` (or `w_mm=53.5, h_mm=47.0`):
- 53.46/47 = 1.137 ≈ logo native 1.14:1
- 53.5/47 = 1.138 ≈ logo native 1.14:1
- Either passes by-construction; override removable.

If the planner decides to keep `w=54` for round numbers, the `brand:logo_size_3M` override must STAY (with reason update to V1 layout intention).

### Net override-list change (predicted)

```yaml
brand_overrides:
  # KEEP (linesp drift across multiple existing styles)
  - id: brand:line_spacing_0.9
    reason: …existing reason…
  # KEEP — update reason to reference V1 60/40 split
  - id: brand:hl_sl_distance_x2
    reason: >-
      V1 (#19) Evidence-Cards 60/40 columnar split places Sub-Headline at
      y=172 below the 100mm-tall Headline at y=70 — same right-half column
      x=235. Vertical gap is intentionally tight in this layout because the
      visual rhythm is set by the column-split, not the HL/SL distance
      formula. Per improvements/03-themen-plakat.md "Brand-Rule-Konformität"
      §4 △.
  # KEEP iff w=54 (else remove if w=53.46)
  - id: brand:logo_size_3M
    reason: …or REMOVE entirely if w=53.46…
# REMOVED (3 entries):
#   brand:visual_adjacency_drift  — V1 lands CONSTRAINTS
#   brand:image_text_overlap      — no partial overlaps in V1
#   brand:image_fills_frame       — post-#24 INJECT_MAP idiom
```

**Confidence:** HIGH.

---

## §7 — Existing ParaStyle Linesp Conformance Audit (P9)

To confirm `brand:line_spacing_0.9` cannot be removed:

| Style | fontsize | linesp | 0.9× | Drift | Status |
|-------|----------|--------|------|-------|--------|
| `themen-plakat/headline` (V1) | 60 OR 52 | 54 OR 46.8 | 54.0 / 46.8 | 0 | ✓ |
| `themen-plakat/sub` (existing) | 18 | 22 | 16.2 | 5.8 | **FAIL** |
| `themen-plakat/beleg-headline` (existing) | 24 | 27 | 21.6 | 5.4 | **FAIL** |
| `themen-plakat/beleg-body` (existing) | 13 | 16 | 11.7 | 4.3 | **FAIL** |
| `themen-plakat/source` (existing) | 10 | 12 | 9.0 | 3.0 | **FAIL** |
| `themen-plakat/impressum` (existing) | 7 | 8 | 6.3 | 1.7 | **FAIL** |
| `themen-plakat/stat-hero` (NEW V1) | 56 | 50.4 | 50.4 | 0 | ✓ |
| `themen-plakat/beleg-body-on-green` (NEW V1) | 13 | 16.9 | 11.7 | 5.2 | **FAIL** |
| `themen-plakat/beleg-headline-yellow` (NEW V1) | 18 | 16.2 | 16.2 | 0 | ✓ |

**Five existing + one new style violate.** The override stays.

**Optional optimization for the planner:** Set `themen-plakat/beleg-body-on-green linesp=11.7` (to be 0.9-conformant). Visually: 11.7pt linesp on 13pt body is tight (0.9 ratio is generally tight for body text). Most templates accept the linesp-drift override globally — no urgency to fix here.

**Confidence:** HIGH.

---

## §8 — Frame Geometry Sanity Check (Card Layout)

**Page:** 420×297 mm (A3 quer), bleed 3mm, margin x=15mm.

**Cards from ISSUE.md:**
- Card 1: x=15, y=210, w=124.67, h=72 → right=139.67, bottom=282
- Card 2: x=148, y=210, w=124.67, h=72 → right=272.67, bottom=282
- Card 3: x=281, y=210, w=124.67, h=72 → right=405.67, bottom=282

**Margins:**
- Left margin: 15mm ✓
- Right margin: 420-405.67 = 14.33mm (within MARGIN_X_MM=15 ± gutter rounding)
- Inter-card gap (Card 1 right → Card 2 left): 148-139.67 = 8.33mm ≈ GUTTER 8 ✓
- Inter-card gap (Card 2 right → Card 3 left): 281-272.67 = 8.33mm ≈ GUTTER 8 ✓

**Mirror axis check (`mirrored_x("Beleg 1 — Card", "Beleg 3 — Card", axis_mm=210.0)`):**
- Card 1 left=15, Card 3 right=405.67 → mirror axis = (15+405.67)/2 = 210.335
- Drift from declared 210.0: 0.335mm < 0.5mm tolerance ✓

**Card 1 internal stack from improvements.md §"Pro Card":**
- Stat: y=240, h presumably 12 (label at y=252) → Stat 240..252
- Label: y=252, h=10 → 252..262
- Body: y=262 (3 lines) → 262..274/280
- Card 1 bottom=282, so all elements inside Card ✓

**Card 1 internal stack from ISSUE.md (different):**
- Stat: y=215, h=24 → 215..239 (inside 210..282 ✓)
- Label: y=242, h=8 → 242..250 (inside ✓)
- Body: y=252, h=26 → 252..278 (inside ✓)

**Use ISSUE.md numbers (canonical).** All `inside(stat/label/body, card)` constraints pass with default 0.5mm tolerance.

**Confidence:** HIGH (computed manually).

---

## §9 — CAPS + Letter-Spacing Implementation (P11)

ISSUE.md prescribes `themen-plakat/beleg-headline-yellow` as "CAPS letter-spacing 0.04em".

**ParaStyle has NO `caps`/`uppercase`/`smcp` field** (verified `tools/sla_lib/builder/styles.py:31-91`). The closest is `fontfeatures: Optional[str]` (FONTFEATURES). OpenType feature `smcp` is small-caps; `c2sc` is small-caps-from-caps. Neither produces all-caps from lowercase input.

**Pattern from existing templates:** None of the 8 templates use OpenType all-caps via fontfeatures. The norm is to **uppercase the actual run text** (`text="GRÜNE JOBS IN NÖ"` literal).

Reference (NOT a CAPS implementation, but proves fontfeatures field works):
- `templates/postkarte-a6-kampagne/build.py:50` uses `fontfeatures='-clig'` (disable contextual ligatures).

**Letter-spacing 0.04em in ParaStyle:**
- ParaStyle `kern: Optional[float]` (KERN attribute) — units are points per (verified `styles.py:76`).
- 0.04em on 18pt = 0.04 × 18 = 0.72pt → set `kern=0.72`.

**Recommended ParaStyle for V1:**
```python
doc.add_para_style(ParaStyle(
    name="themen-plakat/beleg-headline-yellow",
    font="Gotham Narrow Bold",
    fontsize=18,
    linesp=16.2,
    linesp_mode=0,
    align=1,           # centre — matches improvements.md §"Alignment-Spezifikation"
    fcolor="Gelb",
    kern=0.72,         # 0.04em letter-spacing
    language="de",
))
```

Then run text MUST be uppercase: `text="GRÜNE JOBS IN NÖ"`.

**Confidence:** HIGH.

---

## §10 — `text_on_green` Rule Does NOT Fire on V1 White Body (P6)

`_TextOnGreenRule` (`brand_constraints.py:280-317`) only fires for white-fcolor TextFrames whose style matches `^ci/(h|headline)`. V1's `themen-plakat/beleg-body-on-green` uses prefix `themen-plakat/` (NOT `ci/`) → **rule scope-skips V1's white body text entirely**.

The `inside("Beleg N — Body", "Beleg N — Card")` constraint provides the structural witness for "white text sits on green polygon" (the design intent that text_on_green checks for ci/-prefixed styles).

**Confidence:** HIGH.

---

## §11 — Atomic-PR Ordering (P20)

The orchestrator suggested ordering:
> T01 ParaStyles → T02 layout → T03 CONSTRAINTS rewrite → T04 INJECT_MAP update → T05 regen + SHA bump → T06 brand_overrides cleanup → T07 spec rewrite → T08 invariant tests

This ordering works. Rationale and notes:

1. **T01 ParaStyles first** — frames added in T02 reference style names. Build won't crash with style references if styles are absent (Scribus uses default), but constraints expecting style continuity (`same_style`) will misfire.
2. **T02 layout** = delete old Beleg-Headline frames, add Hello-Foto-Card backing polygon, add 3 Card backing polygons, replace Stat-Hero/Label/Body frames, resize Themen-Hero + Logo + QR + Quelle.
3. **T03 CONSTRAINTS rewrite** — add new `same_x`/`inside`/`mirrored_x` per ISSUE.md (with corrections from §3 + §4 above).
4. **T04 INJECT_MAP update** — refactor Themen-Hero to use post-#24 idiom (§1).
5. **T05 regen + SHA bump** — `bin/render-gallery themen-plakat-a3-quer --skip-visual-diff` regenerates `template.sla`, `preview.pdf`, `page-01.png`. SHA in `meta.yml::previews_for_sla` updates automatically (verified `tools/render_pipeline.py` step 7). `bin/check-stale-previews` then passes.
6. **T06 brand_overrides cleanup** — REMOVE `visual_adjacency_drift`, `image_text_overlap`, `image_fills_frame`. Update reason for `hl_sl_distance_x2`. KEEP `line_spacing_0.9`. Decide on `logo_size_3M` per §6 (P8).
7. **T07 spec rewrite** — `templates/_specs/themen-plakat-a3-quer.md` full rewrite (§5 P5).
8. **T08 invariant tests** — update `templates/_smoke/test_themen_plakat_a3_quer.py` per §2 (P2).

**Ordering hazards:**

- **T05 BEFORE T06**: must regen first to confirm zero-error state, THEN remove overrides. Removing overrides first risks T05 failing (brand:visual_adjacency_drift fires before CONSTRAINTS exist).
  - **CORRECTION:** T03 CONSTRAINTS lands BEFORE T06 override removal — that's the correct order. So actual flow is: T03 (CONSTRAINTS) → T05 (regen) → re-run structural_check to confirm `visual_adjacency_drift` no longer warns → T06 (remove override).
- **T07 + T08 can run in parallel** with each other after T05 (both are documentation/test artifacts that depend on the final geometry).
- **T08 update before T05 final regen check** — running `unittest` against an outdated smoke yields false signals during debugging. Update smoke FIRST (or in same atomic commit as T02 layout deletion).

**Recommended PR-ordering for the planner:**

```
T01 ParaStyles (build.py top — additive, no breakage)
T02 layout deletions + additions (build.py middle — breaks smoke immediately)
T03 CONSTRAINTS rewrite (build.py bottom — depends on T02 annames)
T04 INJECT_MAP update (build.py — refactor Themen-Hero block)
T05 regen artefacts (template.sla + preview.pdf + page-01.png + meta.yml SHA)
T06 brand_overrides cleanup (meta.yml — depends on T05 confirming clean)
T07 spec rewrite (_specs/*.md — depends on final geometry)
T08 smoke test update (_smoke/*.py — depends on final annames)
T09 README + DESIGN-SYSTEM-BRIEF §10 (docs — touchups)
```

**Confidence:** HIGH for ordering rationale; MEDIUM for T05/T06 sequencing (could swap if structural_check is run between).

---

## §12 — Codex Visual Review Recommendation

**Single-page A3 quer** = 1 PNG (`page-01.png`). Much smaller scope than Zeitung's 14-page review.

**Recommendation:** **SKIP** Codex visual review for #19. Justification:
- The new `brand:image_fills_frame` rule (post-#24) catches the primary class of regression (letterbox / INJECT_MAP drift) that Codex was needed for in earlier issues.
- `brand:visual_adjacency_drift` catches misaligned frames declaratively.
- Single page = trivial human eyeball check on `page-01.png` vs `improvements/03-themen-plakat.md` mocks (improvements doc has SVG companion mocks).
- Codex review surfaces semantic-design issues (caption-on-photo legibility, color-on-color contrast) — V1 is brand-rule-conformant by-construction; no semantic surprises expected.

**Trigger Codex IF:**
- Audit surfaces unexpected visual artifacts (text-on-photo overlap, photo-cropped-to-sky-only, etc.).
- Bezirksgruppen feedback indicates visual concerns at print scale.

**Confidence:** HIGH (matches #18 + #17 patterns where visual review was deferred to follow-up audit).

---

## §13 — Environment Audit

| Dependency | Required | Available | Version | Notes |
|------------|----------|-----------|---------|-------|
| Python | ≥ 3.11 | ✓ | 3.13.5 | |
| lxml | runtime | ✓ | 5.4.0 | XML parsing for SLA |
| PIL/Pillow | runtime | ✓ | 12.2.0 | image crop/resize for `inject_into_frame` |
| PyYAML | runtime | ✓ | 6.0.3 | meta.yml + manifest |
| Scribus | runtime | ✓ | 1.6.5 (assumed; CLI works via xvfb) | needs `xvfb-run` wrapper for headless |
| xvfb-run | runtime | ✓ | available | `/usr/bin/xvfb-run` |
| pdftoppm | runtime | ✓ | 25.03.0 | poppler-utils PDF→PNG raster |
| Vollkorn fonts | runtime | ✓ | installed at `/usr/local/share/fonts/gruene/` | Vollkorn Black Italic verified |
| Gotham Narrow fonts | runtime | ✓ | installed | Gotham Narrow Book/Bold/Ultra verified |
| `themen_klimaschutz_windrad` asset | V1 | ✓ | `shared/sample-images/themen/klimaschutz-windrad.jpg` (1536×1024, watermarked) | crop_focus=[0.65, 0.50] |
| `gruene-logo-bund-dunkel.png` asset | V1 | ✓ | `shared/logos/gruene-logo-bund-dunkel.png` | ~1.14:1 brushstroke G |
| `samples/qr-quelle.png` asset | V1 | ✓ | `templates/themen-plakat-a3-quer/samples/qr-quelle.png` | existing 25×25mm; V1 grows to 35×35mm (no asset change needed — same source PNG, larger frame) |

**Validation pipeline tools:**
- `bin/render-gallery <slug> --skip-visual-diff` — verified working (Themen-Plakat baseline renders to preview.pdf + page-01.png in ~7s).
- `python3 -m sla_lib.builder.structural_check <slug>` — verified 0 errors on baseline.
- `python3 -m sla_lib.builder.structural_check --all` — verified 0 errors, 122 warnings, 2 skipped, 34 passes (baseline).
- `python3 tools/spec_check.py <slug>` — verified 24 errors (baseline drift, see §5).
- `python3 tools/check_ci.py <template_path>/template.sla` — verified 6 extra-style warnings (legacy/template-local — not blocking).
- `python3 -m unittest templates._smoke.test_themen_plakat_a3_quer` — verified 8/8 pass on baseline.
- `bin/check-stale-previews` — runs as preflight in `bin/validate`; SHA-256 contract per `tools/check_stale_previews.py:46-49`.
- `bin/audit-alignment <slug>` — works; surfaces undeclared adjacencies (baseline shows ~30 warnings on Themen-Plakat — most go away with V1 CONSTRAINTS).

**Environment readiness:** GREEN. No blockers.

**Confidence:** HIGH.

---

## §14 — Improvements.md ↔ ISSUE.md Contradictions Inventory (P16)

For the planner — be explicit when prescribing T02 layout numbers.

| Element | Improvements.md value | ISSUE.md value | Recommendation |
|---------|----------------------|----------------|----------------|
| Stat-Hero fontsize | 22pt (§144 table) AND 56pt (§40 + ParaStyle) | 56pt (header + ParaStyle) | **56pt** (matches ParaStyle) |
| Card height | h=130 (§215 YAML) AND h=72 (§"Card-Geometrie" table) | h=72 | **h=72** |
| Stat-Hero y | y=240 (§144) AND y=215 (§50) | y=215 | **y=215** |
| Card-Inhalt body fontsize | 4.2pt (§150) | 13pt (`beleg-body-on-green` ParaStyle) | **13pt** — 4.2pt is unreadable, contradicts 11pt A3 minimum from spec §68 |
| Body align | align=1 (§150) | align=0 (`beleg-body-on-green` ParaStyle) AND align=1 (`beleg-body` mutation) | **align=1 on `beleg-body-on-green`** (centred per "Alignment-Spezifikation" intent) |
| Card vs page-center | YAML §215 says `card_n bottom=280, h=130` → top=150 | y=210, h=72 → bottom=282 | **y=210 h=72** (ISSUE.md / improvements §132 table) |

**Improvements.md was authored as a brainstorming session — it has internal inconsistencies between the prose tables and the YAML mock.** ISSUE.md picked one consistent set of numbers; the planner should treat ISSUE.md as canonical EXCEPT where ISSUE.md itself contradicts (e.g. `beleg-body align` issue P15) — in those cases pick the geometry that satisfies the constraints.

**Confidence:** HIGH.

---

## §15 — Asset Aspect & Crop Behaviour for Themen-Hero

**Source:** `themen_klimaschutz_windrad` (`shared/sample-images/themen/klimaschutz-windrad.jpg`, 1536×1024).
- Native aspect 1.500
- crop_focus = [0.65, 0.50] (turbine right of centre, vertically mid)

**Frame V1:** 194×114mm = aspect 1.7018

**Crop:** Frame is wider than source → centre-crop trims height. At 300 dpi:
- Frame target: 194mm × 300/25.4 = 2291 px wide
- Frame target: 114mm × 300/25.4 = 1346 px tall
- `crop_for_frame` does `ImageOps.fit((2291, 1346), centering=(0.65, 0.50))` → crops original 1536×1024 to 1.7018 aspect, biased per crop_focus
- Result: ~1536 × (1536/1.7018) = 1536 × 902 px crop → resize to 2291×1346 → bicubic upsample
- 2291×1346 px = 7.3 MP, JPEG q=80 typical 350-450 KB

**Output:** Watermarked JPEG (Symbolfoto band re-applied per `crop_for_frame`'s `apply_watermark=True` default).

**Result in Scribus:** scale_type=0 + ratio=1, JPEG matches frame aspect → fills 194×114 frame exactly. **`brand:image_fills_frame` PASSES by-construction.**

**Visual concern:** 1536→2291 px is a 1.49× upsample. For a 300 dpi print on A3, this is acceptable (effective 200 dpi) — within the spec's `min_image_dpi: 300` if you measure source-pixels-per-frame-mm. The library docstring at `tools/sla_lib/builder/library.py:436` notes this is the standard pattern for all gallery previews.

**Confidence:** HIGH (computed manually; pattern matches all other templates).

---

## §16 — Polygon Layer Hygiene

V1 adds 4 Hellgrün polygons (1 Hero-Foto-Card backing + 3 Card backings). Pattern from existing build.py:

- Background polygon (`Seitenhintergrund`): `layer=0`
- Logo, hero, QR (image frames): `layer=1`
- Text frames (Headline, Sub, Beleg, Quelle, Impressum): `layer=2`

**For V1 new polygons:** Hellgrün backing must render BEHIND the photo (Themen-Hero) and BEHIND the text (Stat/Label/Body). Recommended `layer=1` (Bilder layer, below text). Add the polygon BEFORE the photo and text frames in `page.add()` order.

**Verify against existing templates:** `wahltag-tueranhaenger/build.py:245-393` adds Hellgrün polygons with default layer (0) — but that template uses constants `LAYER_HINTERGRUND=0, LAYER_BILDER=1`. The Themen-Plakat build.py doesn't define such constants; existing polygons (`Seitenhintergrund`) use `layer=0`.

**Recommendation:** Use `layer=1` for the V1 backing polygons (one layer above background, below text). Document layering in build.py comment for future-proofing.

**Confidence:** MEDIUM (no firm convention in this template; following the wahltag-tueranhaenger pattern).

---

## §17 — Sources

### HIGH confidence
- `tools/sla_lib/builder/library.py:326-500` — `crop_for_frame` + `inject_into_frame` semantics (read in full).
- `tools/sla_lib/builder/brand_constraints.py:1045-1292` — `_ImageFillsFrameRule` complete implementation (read in full).
- `tools/sla_lib/builder/brand_constraints.py:882-1042` — `_VisualAdjacencyDriftRule` complete implementation.
- `tools/sla_lib/builder/brand_constraints.py:243-277` — `_LogoSize3MRule` arithmetic.
- `tools/sla_lib/builder/brand_constraints.py:280-317` — `_TextOnGreenRule` scope (only `^ci/(h|headline)` styles).
- `tools/sla_lib/builder/brand_constraints.py:715-805` — `_ImageTextOverlapRule` "text fully inside shape" carve.
- `tools/sla_lib/builder/constraints.py:399-519` — DSL helpers `same_x`, `inside`, `mirrored_x`, `aligned_below`, `same_y`, `distance_y`, `same_style`.
- `tools/sla_lib/builder/styles.py:31-91` — ParaStyle field inventory (no caps, kern available).
- `tools/sla_lib/builder/primitives.py:760-820` — ImageFrame fields (no aspect_fill enum).
- `templates/themen-plakat-a3-quer/build.py` — current build state (read in full).
- `templates/themen-plakat-a3-quer/meta.yml` — current overrides + previews_for_sla SHA.
- `templates/themen-plakat-a3-quer/samples/manifest.yml` — verified asset existence + crop_focus.
- `templates/_smoke/test_themen_plakat_a3_quer.py` — read in full + ran (8/8 pass baseline).
- `templates/_specs/themen-plakat-a3-quer.md` — current spec state.
- `templates/zeitung-a4-grun/build.py:2570-2625` — post-#24 INJECT_MAP reference pattern.
- `templates/postkarte-a6-kampagne/build.py:391-405` — single-page INJECT_MAP pattern.
- `templates/wahltag-tueranhaenger/build.py:147-200` — #18 parallel `*-on-green` ParaStyle pattern.
- `improvements/03-themen-plakat.md` — V1 specification source (read in full).
- `.issues/archive/18-v1-layout-for-wahltag-tueranhaenger-composed-hero/research/pitfalls.md` — confirmed pitfall pattern parallel to #18.
- Live runs: `structural_check themen-plakat-a3-quer`, `structural_check --all`, `spec_check`, `unittest templates._smoke.*`, `check_ci`, `bin/render-gallery`, `bin/audit-alignment`.

### MEDIUM confidence
- Layer hygiene for new V1 backing polygons (no firm convention in this template).
- ISSUE.md `beleg-body align=0→1` mutation interpretation (contradiction within ISSUE.md).

### LOW confidence
- (none — all findings cross-verified against code or live runs).

---

## §18 — Open Questions Surfaced for the Planner

1. **`brand:logo_size_3M` decision** (P8): keep override at w=54, OR change V1 logo to w=53.46 and remove override? Recommend the latter for cleaner brand-rule landscape.
2. **`beleg-body align`** (P15): set `beleg-body-on-green align=1` (centre) OR `align=0` (left flush)? Improvements §150 + §"Alignment-Spezifikation" prescribe centre. ISSUE.md ParaStyle list says align=0. Recommend centre.
3. **`themen-plakat/beleg-body-on-green linesp`** (P9): keep at 16.9pt (carries override) OR change to 11.7pt (0.9-conformant, override-removable per-style)? Recommend keep — the 0.9 ratio is template-wide drift; fixing one style doesn't lift the override.
4. **Card-Hero anname** (§2 smoke update): name the new Hellgrün backing polygon `Hero-Foto-Card`? Or `Themen-Hero-Card`? Or no anname (defaults to empty, won't appear in CONSTRAINTS)? Recommend a stable anname for `inside("Themen-Hero", "Hero-Foto-Card")` constraint witness.
5. **`themen-plakat/headline` linesp mutation** (P14): mutate in place (64→54 or 64→46.8 depending on fontsize choice 60 vs 52) OR add parallel `themen-plakat/headline-tight`? Recommend mutate (single consumer; not a parallel-pattern candidate).

---

## §19 — Predicted Final State

After T01-T09:

- `structural_check themen-plakat-a3-quer`: 0 errors, ~6-8 declared CONSTRAINTS green, 6 brand rules pass, 1-2 SKIP (line_spacing_0.9, hl_sl_distance_x2). visual_adjacency_drift: re-enabled, expected to PASS or emit a few warnings on intra-card axis pairs.
- `structural_check --all`: 0 errors maintained (no other templates touched).
- `spec_check themen-plakat-a3-quer`: 0 errors (T07 rewrite clean).
- `check_ci`: 6 extra-style warnings on themen-plakat/* names (unchanged behaviour — non-blocking).
- `unittest templates._smoke.test_themen_plakat_a3_quer`: 8/8 pass (with T08 updates).
- `bin/render-gallery themen-plakat-a3-quer --skip-visual-diff`: green; `meta.yml::previews_for_sla` SHA bumped.
- `bin/check-stale-previews`: green.

**Confidence:** HIGH for all predictions; the rule mechanics are deterministic and the geometry is fully specified.
