# RESEARCH — #17: V1 "Symbol-Tight" layout for `wahlaufruf-postkarte-a6-quer`

**Status:** synthesized from two parallel research dimensions (codebase / pitfalls). Confidence high — every claim traced to file:line. ISSUE.md contains 4 errors that this RESEARCH corrects.

**Per-dimension reports:** `research/codebase.md`, `research/pitfalls.md`. Read for line-level evidence.

---

## Executive summary

ISSUE.md prescribes V1 "Symbol-Tight" with detailed slot-delta tables, a new ParaStyle set, and a CONSTRAINTS list. Three of those constraints **fail at the prescribed coordinates** — `same_x/same_y` on halo+symbol checks corners not centers (1mm corner drift > 0.5mm tol), and the QR aligned_below stack uses gaps that don't match the prescribed y values. The CONSTRAINTS list also lacks 4 declarations needed once `brand:undeclared_alignment_drift` is unsuppressed (the W-Frage stacks + qr_label-to-logo_back).

Both research dimensions converged on locked decisions for these issues plus 4 ISSUE.md errors:

1. ISSUE.md acceptance bullet "absence of `meta.yml::previews_for_sla`" is wrong — the field IS present and gates `bin/check-stale-previews`. Should say "absence of `original_sla`".
2. ISSUE.md says "Hellgrün-Halo `Polygon x=43 y=17 Ø=62`" — must explicitly use `shape='ellipse'` (Polygon defaults to rectangle).
3. ISSUE.md prescribes anname casing inconsistently (some snake_case, some Title-Case). Existing brand rule `brand:wahlkreuz_colored_bg` matches case-sensitive substring `"Wahlkreuz"` — must keep that anname capitalized OR patch the rule.
4. ISSUE.md says "letter-spacing 0.15em" — DSL has no `em` field; translate to `kern≈2.1` (pt) on the ParaStyle.

After this V1 lands, **3 stale `meta.yml::brand_overrides` entries** must be removed: `brand:undeclared_alignment_drift` (so the rule audits the new layout), `brand:logo_size_3M` (V1 fixes both logos to exactly 3×M = 18.9 mm), and possibly `brand:line_spacing_0.9` (V1's new ParaStyles all sit within tolerance — planner judgment).

---

## Locked decisions (planner: do NOT re-litigate)

| # | Decision | Reason |
|---|---|---|
| 1 | **Halo+symbol constraints use `mirrored_x`/`mirrored_y`, not `same_x`/`same_y`.** Halo at `(43,17,62,62)` and Wahlkreuz at `(44,18,60,60)` share centers (74, 48) but corners differ by 1mm. `same_x` checks corner = fail. `mirrored_x("wahlkreuz_halo", "wahlkreuz", axis_mm=74.0)` averages center-x; passes. Same for y axis 48.0. | Pitfalls B1; constraints.py:230-275, 433-450. |
| 2 | **QR stack y values: `qr_label.y=24, qr_code.y=31, qr_url.y=71`** (not ISSUE.md's 24/30/68). With `aligned_below(qr_code, qr_label, gap_mm=2)`: `qr_label.bottom=24+5=29` + 2 = 31 ✓. With `aligned_below(qr_url, qr_code, gap_mm=4)`: `qr_code.bottom=31+36=67` + 4 = 71 ✓. | Pitfalls B2/B3; aligned_below requires `below.y == above.y + above.h + gap`. |
| 3 | **Halo Polygon must use `shape='ellipse'`.** ISSUE.md's "Ø=62" notation implies circle but Polygon default is rectangle. | Pitfalls H3. |
| 4 | **anname casing: keep existing capitalization where brand rules depend on it.** `Wahlkreuz` stays capitalized (case-sensitive substring match in `brand:wahlkreuz_colored_bg` at brand_constraints.py:347). New annames added by V1 use snake_case as ISSUE.md specifies (`wahlkreuz_halo`, `headline_datum`, `headline_cta`, `frage_*_*`, `qr_label`, `qr_url`, `seitenhintergrund_back_left`, `impressum_strip_bg`). Existing kept-frames retain current annames. | Codebase agent §1; brand_constraints.py:347. |
| 5 | **`wahlaufruf/cell-body` migration: parallel new style `wahlaufruf/cell-body-on-green`** (don't mutate existing). | ISSUE.md (implicit) — V1 of this template "establishes the `*-on-green` ParaStyle migration pattern that #18-#21 reuse" → pattern must be visible. Pitfalls M2. |
| 6 | **`letter-spacing: 0.15em` → `kern=2.1`** on `wahlaufruf/headline-cta` ParaStyle (14pt × 0.15em × 1pt/em = 2.1 pt of per-glyph expansion). DSL has no `em` unit. | Codebase agent §2 + pitfalls. |
| 7 | **Add 4 missing CONSTRAINTS declarations** so `brand:undeclared_alignment_drift` reports zero warnings post-V1: `aligned_below("frage_was_body", "frage_was_headline", gap_mm=1.0)` plus the same for warum and wann; `aligned_below("qr_label", "logo_back", gap_mm=10.3)`. | Pitfalls H1. |
| 8 | **Acceptance bullet correction:** "absence of `meta.yml::original_sla`" (not `previews_for_sla`). The `previews_for_sla` SHA IS present on this template — `bin/render-gallery` must be run + SHA bumped + regen artifacts committed. | Codebase agent §6 / pitfalls L6. |
| 9 | **Remove 3 stale `meta.yml::brand_overrides` entries after V1 is green:** `brand:undeclared_alignment_drift` (audit the new layout), `brand:logo_size_3M` (both logos now Print-Soll), `brand:line_spacing_0.9` (V1's new ParaStyles within tolerance — confirm by re-running rule). | Codebase agent §10. |
| 10 | **Smoke test `test_back_has_2x2_grid` must be rewritten** for the new W-Fragen layout. Add halo + datum/cta + qr_label/url assertions. | Codebase agent §8. |
| 11 | **Update `meta.yml::ci_overrides.non_ci_styles`** — extend with the 3 new ParaStyles + the new `cell-body-on-green` variant. Optionally remove orphaned `wahlaufruf/headline` and `wahlaufruf/cell-headline` after deletion. | Codebase agent §10. |
| 12 | **No INJECT_MAP needed.** All V1-added text frames have hardcoded demo strings; logos and QR are inlined via `pack_inline_image`, not `library.inject_into_frame`. | Codebase agent §4. |
| 13 | **`templates/_specs/wahlaufruf-postkarte-a6-quer.md` rewrite is in scope.** ISSUE.md doesn't have an explicit acceptance bullet for it but skipping leaves long-term spec drift. | Codebase agent §7. |

---

## Scope changes vs. ISSUE.md

| ISSUE.md | Status | Why |
|---|---|---|
| `same_x("wahlkreuz_halo","wahlkreuz")` + `same_y(...)` | **REPLACED** by `mirrored_x` + `mirrored_y` (locked decision #1). |
| QR y values 24/30/68 | **CORRECTED** to 24/31/71 (locked decision #2). |
| Hellgrün-Halo Polygon | **CORRECTED**: explicit `shape='ellipse'` (locked decision #3). |
| `wahlaufruf/cell-body fcolor: Black→White` | **CHANGED** to NEW `wahlaufruf/cell-body-on-green` style (locked decision #5). Original kept for orphan-ish-styles policy parity. |
| "absence of `meta.yml::previews_for_sla`" | **CORRECTED** to "absence of `original_sla`" (locked decision #8). |
| Acceptance "structural_check passes" | **EXPANDED**: also assert `brand:undeclared_alignment_drift` reports zero warnings on this template after override removal (locked decisions #7 + #9). |
| (no mention) | **ADDED**: smoke test rewrite, spec rewrite, ci_overrides update, brand_overrides removal, regen + SHA bump, brief §10 row, design-doc Resulting-issue link (locked decisions #10–#13 + housekeeping). |

---

## User constraints

- **No image rendering** — code-only verification: `structural_check`, `bin/audit-alignment`, unit + smoke tests, `bin/check-stale-previews`.
- **Atomic PR** — all V1 build.py edits + style migration + CONSTRAINTS list + override removals + smoke-test rewrite + spec rewrite + render regen + meta.yml SHA bump must land together.
- **No new dependencies.**
- **Use `bin/audit-alignment wahlaufruf-postkarte-a6-quer` as the verification gate.** Pre-V1 it shows 1 page-1 + 8 page-2 suspicious adjacencies (the things V1 deletes/replaces). Post-V1 must show 0.

---

## Codebase Analysis — interfaces

<interfaces>

### `Constraint` factories used by V1 CONSTRAINTS list

```
file: tools/sla_lib/builder/constraints.py
- mirrored_x(left, right, axis_mm: float, tolerance_mm: float = 0.5, name: str = "")
    → averages left.x+w/2 and right.x+w/2; checks midpoint ≈ axis_mm.
    USE FOR: halo+symbol center alignment.
- mirrored_y(top, bottom, axis_mm: float, ...)
    → analogous for y centers.
- aligned_below(below, above, gap_mm: float, tolerance_mm: float = 0.5, name: str = "")
    → asserts below.x == above.x AND below.y == above.y + above.h + gap_mm.
    USE FOR: QR stack, W-Frage stacks, logo→qr_label.
- same_x(*targets, ...)
    → asserts all targets share the same x_mm (corner, not center).
    USE FOR: column-axis sharing across W-Fragen headlines, bodies; QR vertical axis.
- inside(child, parent, tolerance_mm: float = 0.5, name: str = "")
    → child bbox ⊆ parent bbox + tolerance.
    USE FOR: halo_contains_symbol.
- distance_y(a, b, equals: float, ...)
    → |b.y - a.y| ≈ equals.
    USE FOR: datum→cta vertical hierarchy.
```

### Brand-rule interactions for this template

```
file: tools/sla_lib/builder/brand_constraints.py
- brand:inside_page (rule 9, from #14): every frame's rotation+anchor-aware bbox
  must be inside [-bleed, w+bleed] × [-bleed, h+bleed]. V1's new polygons
  all sit within bounds (verified arithmetically).
- brand:spine_safety (rule 10, from #22): no-op on this template (single page,
  facing_pages=False).
- brand:undeclared_alignment_drift (rule 11, from #22): currently SKIPPED via
  meta.yml::brand_overrides[brand:undeclared_alignment_drift] with reason
  "see #17 V1 layout work". REMOVE after V1 CONSTRAINTS list is complete + green.
- brand:wahlkreuz_colored_bg: case-sensitive substring "Wahlkreuz" match.
  V1 keeps the anname capitalized.
- brand:logo_size_3M: case-INSENSITIVE \\bLogo\\b match. V1's renamed
  logos (logo_back lowercased) still trigger the rule. After V1 both logos are
  exactly 3×M = 18.9 mm; brand_overrides[brand:logo_size_3M] becomes stale +
  unnecessary. REMOVE.
- brand:hl_sl_distance_x2: looks for headline+subline pair; no V1 anname
  contains "subline" → rule no-op. The new alignment hierarchy is enforced
  by the per-template CONSTRAINTS list (distance_y).
- brand:text_on_green: only fires for re.match(r"^ci/(h|headline)", style).
  V1's new styles start with "wahlaufruf/" → rule no-op.
```

### `meta.yml` shape (current → post-V1)

```yaml
# meta.yml::brand_overrides — REMOVE all 3 entries:
brand_overrides:
  - id: brand:line_spacing_0.9     # ← REMOVE (verify V1 styles all within 0.9 tol first)
  - id: brand:logo_size_3M         # ← REMOVE (V1 makes both logos = 3×M)
  - id: brand:undeclared_alignment_drift  # ← REMOVE (V1 declares all adjacencies)

# meta.yml::ci_overrides.non_ci_styles — UPDATE:
ci_overrides:
  non_ci_styles:
    - "wahlaufruf/cell-body"          # keep (still exists)
    - "wahlaufruf/cell-body-on-green" # NEW
    - "wahlaufruf/headline-emphasis"  # NEW
    - "wahlaufruf/headline-cta"       # NEW
    - "wahlaufruf/cell-headline-yellow"  # NEW
    - "wahlaufruf/impressum"          # keep
    # consider removing "wahlaufruf/headline" + "wahlaufruf/cell-headline" if orphaned

# meta.yml::previews_for_sla — UPDATE to new sha256(template.sla) after regen.
```

### Frames touched (concise; full inventory in research/codebase.md §1)

```
PAGE 0 (front):
  Polygon "Seitenhintergrund (front)" (kept)
  ImageFrame "Logo Grüne (weiss)" — w 35→18.9, h 10→5.7, local_scale 0.240→0.130
  Polygon "wahlkreuz_halo" — NEW, x=43 y=17 w=62 h=62 shape='ellipse' fill=Hellgrün, layer=0
  ImageFrame "Wahlkreuz" — x 46.5→44, y 16→18, w 55→60, h 55→60 (anname kept capitalized)
  TextFrame "Headline-Wahlaufruf" — DELETE
  TextFrame "headline_datum" — NEW, x=10 y=82 w=128 h=10, style=headline-emphasis
  TextFrame "headline_cta" — NEW, x=10 y=92 w=128 h=10, style=headline-cta

PAGE 1 (back):
  Polygon "seitenhintergrund_back_left" — NEW, x=-3 y=-3 w=93 h=111 fill=Dunkelgrün, layer=0
  Polygon "impressum_strip_bg" — NEW, x=0 y=96 w=148 h=9 fill=White, layer=0
  ImageFrame "logo_back" — was "Logo Grüne (Bund-Dunkel)"; replace asset with gruene-weiss.png,
    x=96 y=8 w=18.9 h=5.7 local_scale=(0.130, 0.130)
  TextFrame "Cell N — Headline/Body" loop — DELETE entire AlignedRow block (8 frames + 4 wrappers)
  TextFrame "frage_was_headline" + "frage_was_body" at (6, 12-30) — NEW
  TextFrame "frage_warum_headline" + "frage_warum_body" at (6, 40-60) — NEW
  TextFrame "frage_wann_headline" + "frage_wann_body" at (6, 68-88) — NEW
  TextFrame "qr_label" — NEW, x=96 y=24 w=36 h=5, "WO INFORMIEREN"
  ImageFrame "qr_code" — was "QR-Code (back)"; x 115→96, y 62→31, w 27→36, h 27→36
  TextFrame "qr_url" — NEW, x=96 y=71 w=36 h=5, "gruene-noe.at"
  TextFrame "Impressum" — y 96→101.5, h 6→4 (style fontsize 6→5)
```

</interfaces>

---

## Standard Stack (verified)

| Item | Value |
|---|---|
| Python | 3.13 |
| Test runner | `python3 -m unittest discover tools/sla_lib/tests` + `python3 -m unittest templates._smoke.test_wahlaufruf_postkarte_a6_quer` |
| Build | `python3 templates/wahlaufruf-postkarte-a6-quer/build.py` |
| Regen | `bin/render-gallery wahlaufruf-postkarte-a6-quer` |
| Audit | `bin/audit-alignment wahlaufruf-postkarte-a6-quer` (target: 0 suspicious) |
| Stale check | `bin/check-stale-previews` (must exit 0 after regen + meta.yml SHA bump) |
| New deps | none |

---

## Don't Hand-Roll

- All factories from #14 — `mirrored_x/y`, `aligned_below`, `same_x/y`, `inside`, `distance_y` — already exist.
- `bin/render-gallery` regenerates template.sla + page-NN.png + preview.pdf + meta.yml SHA + site/public mirror.
- `bin/audit-alignment` runs the audit tool; consume its skeleton suggestions to seed the V1 CONSTRAINTS list.
- `pack_inline_image` already in use for the Wahlkreuz and logo assets.

---

## Architecture Patterns

### V1 CONSTRAINTS list (final, post-locked-decisions)

```python
CONSTRAINTS = [
    # Front: halo + symbol share centers (both axes), and halo contains symbol
    mirrored_x("wahlkreuz_halo", "Wahlkreuz", axis_mm=74.0, name="halo_x_centered"),
    mirrored_y("wahlkreuz_halo", "Wahlkreuz", axis_mm=48.0, name="halo_y_centered"),
    inside("Wahlkreuz", "wahlkreuz_halo", name="halo_contains_symbol"),
    # Front: headline stack vertical hierarchy (datum -> cta gap = 10mm)
    distance_y("headline_datum", "headline_cta", equals=10.0, name="datum_to_cta"),
    # Back: 3 W-Fragen share x-axis (left edge x=6) for headlines and bodies
    same_x("frage_was_headline", "frage_warum_headline", "frage_wann_headline",
           name="fragen_left_axis"),
    same_x("frage_was_body", "frage_warum_body", "frage_wann_body",
           name="bodies_left_axis"),
    # Back: per-W-Frage stack (body hangs from headline, gap=1mm, same x)
    aligned_below("frage_was_body", "frage_was_headline", gap_mm=1.0,
                  name="was_stack"),
    aligned_below("frage_warum_body", "frage_warum_headline", gap_mm=1.0,
                  name="warum_stack"),
    aligned_below("frage_wann_body", "frage_wann_headline", gap_mm=1.0,
                  name="wann_stack"),
    # Back: QR block right-axis + label-above + url-below
    same_x("qr_label", "qr_code", "qr_url", name="qr_axis"),
    aligned_below("qr_code", "qr_label", gap_mm=2.0, name="qr_label_anchors_code"),
    aligned_below("qr_url", "qr_code", gap_mm=4.0, name="qr_url_below_code"),
    # Back: qr_label hangs from logo_back (stacking on the right column)
    aligned_below("qr_label", "logo_back", gap_mm=10.3, name="logo_back_anchors_qr"),
]
```

### V1 ParaStyle additions

```python
# Pattern: parallel new styles, leave existing untouched (locked decision #5)
ParaStyle(name="wahlaufruf/headline-emphasis",
          font="Vollkorn Black Italic", fontsize=26, linesp=23,
          fcolor="Gelb", language="de", align=1)
ParaStyle(name="wahlaufruf/headline-cta",
          font="Gotham Narrow Bold", fontsize=14, linesp=13,
          fcolor="White", language="de", align=1, kern=2.1)  # 0.15em → 2.1pt
ParaStyle(name="wahlaufruf/cell-headline-yellow",
          font="Vollkorn Black Italic", fontsize=18, linesp=16,
          fcolor="Gelb", language="de", align=0)
ParaStyle(name="wahlaufruf/cell-body-on-green",
          font="Gotham Narrow Book", fontsize=9, linesp=11,
          fcolor="White", language="de", align=0)
# Existing wahlaufruf/cell-body (Black) UNCHANGED.
# Existing wahlaufruf/impressum: fontsize 6→5, recompute linesp = 5 × 0.9 ≈ 4.5
```

### Halo polygon

```python
# Locked decision #3: explicit shape='ellipse' (Polygon defaults to rectangle)
Polygon(x_mm=43, y_mm=17, w_mm=62, h_mm=62,
        fill="Hellgrün", layer=0,
        anname="wahlkreuz_halo", shape="ellipse")
```

---

## Common Pitfalls (consolidated)

### Must-handle (HIGH severity)

1. **Halo+symbol corner-vs-center** (locked decision #1) — use `mirrored_x/y`, NOT `same_x/y`.
2. **QR stack y arithmetic** (locked decision #2) — `aligned_below` constraints fail at ISSUE.md's prescribed 24/30/68. Use 24/31/71.
3. **`back logo_back` requires explicit `local_scale=(0.130, 0.130)`** — defaults to (1.0, 1.0) which renders 5.5× scale.
4. **`brand_overrides` removal ordering** — remove only AFTER V1 CONSTRAINTS green AND `bin/audit-alignment` reports 0 suspicious. Reverse order = `--all` red.
5. **`bin/render-gallery` + meta.yml SHA bump are mandatory** — `bin/check-stale-previews` blocks CI otherwise.
6. **Smoke test `test_back_has_2x2_grid`** hard-pins deleted `Cell N — *` annames — must be rewritten.

### Worth knowing (MEDIUM)

7. **`wahlkreuz_halo` Polygon needs `shape='ellipse'`** (Polygon defaults to rectangle).
8. **`brand:wahlkreuz_colored_bg` is case-sensitive** for "Wahlkreuz" substring — keep capitalized.
9. **Spec rewrite for `_specs/wahlaufruf-postkarte-a6-quer.md`** — not gated by CI but leaving stale degrades long-term value.
10. **`meta.yml::ci_overrides.non_ci_styles`** must be extended with the 4 new styles or `tools/check_ci.py` flags drift.

### Informational

11. ISSUE.md acceptance "absence of `meta.yml::previews_for_sla`" was wrong — should be `original_sla`. Field IS present and is the SHA gate.
12. `letter-spacing 0.15em` → `kern=2.1` (DSL has no em unit).
13. No INJECT_MAP needed — all V1 frames are hardcoded text or pack_inline_image.

---

## Suggested PR shape (planner refines)

~12 commits across 8-10 tasks:

1. `feat(wahlaufruf-postkarte): add 4 new ParaStyles (headline-emphasis, headline-cta, cell-headline-yellow, cell-body-on-green)`
2. `feat(wahlaufruf-postkarte): V1 front layout — halo + symbol + datum/cta stack`
3. `feat(wahlaufruf-postkarte): V1 back layout — split-half bg + 3 W-Fragen + QR stack + logo swap`
4. `feat(wahlaufruf-postkarte): V1 CONSTRAINTS list with mirrored_x/y for halo, aligned_below for stacks`
5. `chore(wahlaufruf-postkarte): meta.yml — extend ci_overrides.non_ci_styles for new ParaStyles`
6. `chore(wahlaufruf-postkarte): regenerate template.sla + gallery via bin/render-gallery`
7. `chore(wahlaufruf-postkarte): meta.yml — remove 3 stale brand_overrides (logo_size_3M, line_spacing_0.9, undeclared_alignment_drift)`
8. `test(wahlaufruf-postkarte): rewrite smoke test for V1 W-Fragen layout`
9. `docs(wahlaufruf-postkarte): rewrite _specs/ for V1 layout`
10. `docs(brand): append session-history row to DESIGN-SYSTEM-BRIEF.md §10`

Plus the artifact commits (RESEARCH.md, PLAN.md, EXECUTION.md).

Next: `/issue:plan` turns this into XML-tagged tasks for the executor.
