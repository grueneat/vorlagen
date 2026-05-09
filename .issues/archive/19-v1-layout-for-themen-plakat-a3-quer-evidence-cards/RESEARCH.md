# RESEARCH — #19: V1 "Evidence Cards" layout for `themen-plakat-a3-quer`

**Status:** synthesized from two parallel research dimensions (codebase / pitfalls). Confidence high — every claim verified against post-#24 main + live tool runs. ISSUE.md contains 3 errors that this RESEARCH corrects.

**Per-dimension reports:** `research/codebase.md`, `research/pitfalls.md`. Read for line-level evidence.

---

## Executive summary

ISSUE.md prescribes V1 "Evidence Cards" — 3 Hellgrün cards with stat-hero numbers + caps labels + body text on a 60/40 hero-photo + headline-stack split. Both research dimensions converged on **3 ISSUE.md errors** to correct in synthesis:

1. **`scale_type=aspect_fill` is not a thing in the DSL.** ISSUE.md Open Question #1 is misframed. The post-#24 standard is `library.inject_into_frame(frame, img, target_w_mm=frame.w_mm, target_h_mm=frame.h_mm)` which pre-crops the JPEG to frame aspect → fills with no letterbox. **No DSL extension needed.**
2. **`same_x("Beleg N — Card", "Beleg N — Stat", "Beleg N — Label", "Beleg N — Body")` will FAIL** — Card.x = col_x but Stat/Label/Body.x = col_x+5 (5mm Hellgrün-card inset). Drop Card from the `same_x` declaration; rely on `inside()` containment.
3. **`aligned_below("Themen-Hero", "Sub-Headline", gap_mm=8.0)` is geometrically invalid** — Hero (x=18, y=73) is left of AND above Sub (x=235, y=172). They're side-by-side in the 60/40 split, NOT stacked. Drop or replace with `inside("Themen-Hero", "Hero-Foto-Card")`.

Plus 2 critical structural changes:
- **Build split required** (post-#24 pattern): `themen-plakat` doesn't use INJECT_MAP today — inlines `library.crop_for_frame(target_w_mm=180, target_h_mm=60)` in `build_doc()`. Must split into `build_template()` (clean, no photo bytes) + `build_preview()` (with INJECT_MAP using bare `lib_id` + live `frame.w_mm`/`frame.h_mm`). Without this split, photo bytes end up in round-trip-validated `template.sla`.
- **Smoke test breaks** — `test_required_annames_present` asserts `Beleg N — Headline` annames that V1 deletes. Update in same PR.

---

## Locked decisions (planner: do NOT re-litigate)

| # | Decision | Reason |
|---|---|---|
| 1 | **Use post-#24 INJECT_MAP pattern** for Themen-Hero photo: `build_doc → build_template + build_preview` split; INJECT_MAP value = bare `lib_id`; loop reads `target_w_mm=frame.w_mm`, `target_h_mm=frame.h_mm`. NO `aspect_fill` enum; the `crop_for_frame` pre-crop fills naturally. | Codebase agent §5; pitfalls P1. The post-#24 corrected pattern is canonical. |
| 2 | **CONSTRAINTS rewrite** — drop Card from `same_x` quad; use 3 separate per-row `same_x` (stats / labels / bodies) + 9 `inside()` for containment. Drop `aligned_below(Hero, Sub)`; use `inside(Hero, Hero-Foto-Card)` instead. | Pitfalls P3 + P4. The ISSUE.md formulations would fail at structural_check time. |
| 3 | **`Hero-Foto-Card` Polygon** is added in V1 (Hellgrün backing for the hero photo). ISSUE.md mentions it in scope without giving an anname. Use `Hero-Foto-Card` (German naming convention parity). | Codebase agent finding. |
| 4 | **ParaStyle parallel pattern (#17/#18)**: ADD `themen-plakat/stat-hero`, `themen-plakat/beleg-body-on-green`, `themen-plakat/beleg-headline-yellow`. CHANGE `themen-plakat/headline` linesp `64→54` (formula-conformant; same anname, no parallel needed). | Codebase agent §3. |
| 5 | **`brand:logo_size_3M` precision**: V1 sets logo `w=54`, M-margin = 0.06 × 297 = 17.82, 3M = 53.46. Drift = 0.54mm > 0.5mm tolerance. Set logo `w=53.46` (REMOVABLE override) OR keep logo `w=54` (KEEP override). **Recommend `w=53.46` for cleaner removal.** | Pitfalls P8. |
| 6 | **Codex visual review SKIPPED** for #19 — single-page A3 quer, `brand:image_fills_frame` is the primary detector for the regression class Codex was used for. Trigger Codex only if audit surfaces unexpected artifacts. | Pitfalls P-Codex. Saves a task. |
| 7 | **Brand-overrides removability post-V1**: REMOVE `brand:image_fills_frame` (post-#24 INJECT_MAP fills exactly), REMOVE `brand:image_text_overlap` (text fully inside cards = allowed), UPDATE reason on `brand:hl_sl_distance_x2` (V1 60/40 split rationale), KEEP `brand:line_spacing_0.9` (5 existing styles + 1 new violate), KEEP-or-REMOVE `brand:logo_size_3M` per locked decision #5. | Pitfalls "Brand-Override Removability Predictions" table. |
| 8 | **Smoke test rewrite required** — replace `Beleg N — Headline` with `Beleg N — Stat`, `Beleg N — Label`, `Beleg N — Body`, `Beleg N — Card`. Add `Themen-Hero`, `Hero-Foto-Card`. | Codebase agent §9. |
| 9 | **Spec rewrite required** — `templates/_specs/themen-plakat-a3-quer.md` is fully stale post-V1. Use #17/#18 V1-spec patterns as templates. | Codebase agent §8. |
| 10 | **Atomic-PR ordering**: T01 ParaStyles → T02 build split (build_template+build_preview) → T03 V1 layout → T04 INJECT_MAP (post-#24 pattern) → T05 CONSTRAINTS list → T06 regen + SHA bump → T07 brand_overrides cleanup → T08 smoke test rewrite → T09 spec rewrite → T10 invariant tests → T11 brief §10 + EXECUTION. | Pitfalls P-ordering. |
| 11 | **`bin/render-gallery themen-plakat-a3-quer --skip-visual-diff`** + meta.yml SHA bump mandatory at T06 (~7s per pitfalls verification). | Standard pattern. |
| 12 | **Invariant-pinning tests per #23 pattern** in NEW `tools/sla_lib/tests/test_themen_plakat_geometry.py`. Pin RELATIONSHIPS (3 cards share width, 3 cards share top, card N contents inside card N, hero left edge at MARGIN_X, headline-stack left edges share AXIS_HEADLINE_LEFT, card-3 right edge at page_w-margin). NOT absolute coordinates. | Codebase agent §9 + pitfalls. |
| 13 | **Registry test SKIP** — themen-plakat doesn't add a new BrandRule; registry stays at 15. | (no change needed) |

---

## Scope changes vs. ISSUE.md

| ISSUE.md | Status | Why |
|---|---|---|
| `scale_type=aspect_fill` mentioned in Open Question 1 | **DROPPED** — DSL doesn't have this. Use post-#24 INJECT_MAP pattern instead (locked #1). |
| `same_x("Beleg N — Card", "Beleg N — Stat", "Beleg N — Label", "Beleg N — Body")` | **REWRITE** — 3 per-row `same_x` + 9 `inside()` per locked #2. |
| `aligned_below("Themen-Hero", "Sub-Headline", gap_mm=8.0)` | **DROPPED** or replaced with `inside(Hero, Hero-Foto-Card)` per locked #2. |
| Logo `w=54` | **CORRECTED** to `w=53.46` per locked #5 (removability). |
| (no spec rewrite mentioned) | **ADDED** in scope per locked #9. |
| (no smoke test rewrite mentioned) | **ADDED** per locked #8. |
| (no build split mentioned) | **ADDED** per locked #1. |

---

## Codebase Analysis — interfaces

<interfaces>

### Post-#24 BRAND_CONSTRAINTS (15 rules; #19 doesn't add)

```
file: tools/sla_lib/builder/brand_constraints.py:1302-1443
1-9. baseline #14 + earlier
10. brand:spine_safety
11. brand:visual_adjacency_drift
12. brand:bleed_coverage
13. brand:image_text_overlap
14. brand:cover_extent_match
15. brand:image_fills_frame   # NEW from #24
```

### Constraint factories (#19 uses)

```
file: tools/sla_lib/builder/constraints.py
- same_x(*targets, ...)          L408
- same_y(*targets, ...)          L399
- inside(child, parent, ...)     L453
- mirrored_x(left, right, ...)   L433
- aligned_below(below, above, gap_mm, ...) L507
- distance_x(a, b, equals, ...)  L498
- distance_y(a, b, equals, ...)  L489
- same_size(*targets, ...)       L417
# NO same_x_right / same_y_bottom helpers exist
```

### Post-#24 INJECT_MAP pattern (Zeitung reference)

```python
# templates/zeitung-a4-grun/build.py:2584-2625
INJECT_MAP = {
    "Cover Hero":     "themen_klimaschutz_windrad",   # bare lib_id, NO targets
    "P1 Hero":        "themen_soziales_gemeindebau",
    # ...
}
def build_preview():
    doc = build_template()   # clean template, no photo bytes
    for page in doc.pages:
        for item in page.items:
            if isinstance(item, ImageFrame) and item.anname in INJECT_MAP:
                lib_id = INJECT_MAP[item.anname]
                img = library.load(lib_id, optional=True)
                if img:
                    library.inject_into_frame(item, img,
                        target_w_mm=item.w_mm, target_h_mm=item.h_mm)
    return doc

build_doc = build_template   # alias for structural_check
```

### `library.inject_into_frame` (sets scale_type=0; pre-crops to frame aspect)

```
file: tools/sla_lib/builder/library.py:436-500
def inject_into_frame(frame, img, *, target_w_mm, target_h_mm,
                       dpi=300, quality=80, apply_watermark=True):
    # crops img to (target_w_mm, target_h_mm) aspect via crop_for_frame
    # embeds as inline JPEG; sets frame.scale_type=0
```

### Current themen-plakat state

```
templates/themen-plakat-a3-quer/build.py
- Single function build_doc() (no split today)
- Inlines: library.load("themen_klimaschutz_windrad", optional=True)
           library.crop_for_frame(target_w_mm=180, target_h_mm=60)  # WRONG dims for V1
           pack_inline_image(...)
- 6 CONSTRAINTS in module-level CONSTRAINTS list (will be fully replaced)

templates/themen-plakat-a3-quer/meta.yml — 6 brand_overrides
```

</interfaces>

---

## Architecture patterns

### V1 build_template + build_preview split

```python
# templates/themen-plakat-a3-quer/build.py — replace current build_doc

def build_template() -> Document:
    """Clean A3 quer Themen-Plakat template — DSL-only, no photo bytes."""
    doc = Document(...)
    # ... ParaStyles + page setup
    # ... Headline These (right half), Sub-Headline, etc.
    # ... 3 Beleg cards (Hellgrün polygon + stat-hero + label + body)
    # ... Hero-Foto-Card Hellgrün backing polygon
    # ... Themen-Hero ImageFrame (NO inline_image_data; clean for round-trip)
    # ... Logo, QR, Quelle, Impressum
    return doc

def build_preview() -> Document:
    """Inject demo photo for gallery PNG render (#24 pattern)."""
    doc = build_template()
    for page in doc.pages:
        for item in page.items:
            if isinstance(item, ImageFrame) and item.anname in INJECT_MAP:
                lib_id = INJECT_MAP[item.anname]
                img = library.load(lib_id, optional=True)
                if img:
                    library.inject_into_frame(item, img,
                        target_w_mm=item.w_mm, target_h_mm=item.h_mm)
    return doc

INJECT_MAP = {
    "Themen-Hero": "themen_klimaschutz_windrad",
}

build_doc = build_template   # alias for structural_check
```

### V1 CONSTRAINTS list (corrected)

```python
CONSTRAINTS = [
    # Headline-stack vertical hierarchy (Sub below Headline These with formula gap)
    distance_y("Headline These", "Sub-Headline", equals=84.0,    # 60pt × 2 × 0.353 ≈ 42mm gap (or 8mm pragmatic)
               name="hl_to_sub"),
    # 3 Evidence cards share top y (row alignment)
    same_y("Beleg 1 — Card", "Beleg 2 — Card", "Beleg 3 — Card",
           name="cards_top_aligned"),
    same_size("Beleg 1 — Card", "Beleg 2 — Card", "Beleg 3 — Card",
              name="cards_same_size"),
    # 3 cards mirrored around page center (cards 1↔3)
    mirrored_x("Beleg 1 — Card", "Beleg 3 — Card", axis_mm=210.0,
               name="cards_mirror_around_page_center"),
    # Per-row column-axis sharing (3 stat-heros at col_x+5; 3 labels; 3 bodies)
    same_x("Beleg 1 — Stat", "Beleg 1 — Label", "Beleg 1 — Body",
           name="card1_v_axis"),
    same_x("Beleg 2 — Stat", "Beleg 2 — Label", "Beleg 2 — Body",
           name="card2_v_axis"),
    same_x("Beleg 3 — Stat", "Beleg 3 — Label", "Beleg 3 — Body",
           name="card3_v_axis"),
    # Per-card containment (NOT same_x with Card — Card x ≠ contents x)
    inside("Beleg 1 — Stat",  "Beleg 1 — Card", name="b1_stat_in_card"),
    inside("Beleg 1 — Label", "Beleg 1 — Card", name="b1_label_in_card"),
    inside("Beleg 1 — Body",  "Beleg 1 — Card", name="b1_body_in_card"),
    inside("Beleg 2 — Stat",  "Beleg 2 — Card", name="b2_stat_in_card"),
    inside("Beleg 2 — Label", "Beleg 2 — Card", name="b2_label_in_card"),
    inside("Beleg 2 — Body",  "Beleg 2 — Card", name="b2_body_in_card"),
    inside("Beleg 3 — Stat",  "Beleg 3 — Card", name="b3_stat_in_card"),
    inside("Beleg 3 — Label", "Beleg 3 — Card", name="b3_label_in_card"),
    inside("Beleg 3 — Body",  "Beleg 3 — Card", name="b3_body_in_card"),
    # Themen-Hero containment in Hero-Foto-Card (NOT aligned_below to Sub-Headline)
    inside("Themen-Hero", "Hero-Foto-Card", name="hero_in_card"),
    # Style consistency
    same_style("Beleg 1 — Stat", "Beleg 2 — Stat", "Beleg 3 — Stat",
               name="stat_style_consistent"),
    same_style("Beleg 1 — Body", "Beleg 2 — Body", "Beleg 3 — Body",
               name="body_style_consistent"),
]
```

---

## Common Pitfalls (consolidated)

### Must-handle (HIGH)

1. **`scale_type=aspect_fill` doesn't exist** — use post-#24 INJECT_MAP pattern.
2. **Build split required** for round-trip stability.
3. **`same_x` with Card + contents will fail** at structural_check.
4. **`aligned_below` Hero+Sub is geometrically invalid** (different x cols).
5. **Smoke test breaks** on `Beleg N — Headline` annames.
6. **Spec is fully stale** — full rewrite.
7. **Logo precision** (`w=54` vs `w=53.46`) determines override removability.

### Worth knowing (MEDIUM)

8. **6 brand_overrides** post-V1 disposition per locked #7.
9. **No new BrandRules** added in #19 — registry stays at 15.
10. **Codex skipped** for single-page A3.

### Informational

11. **Asset `themen_klimaschutz_windrad`** exists at correct path; `crop_focus=[0.65, 0.50]` works for V1's 1.7:1 hero frame.
12. **`bin/render-gallery themen-plakat-a3-quer --skip-visual-diff`** verified working in ~7s.
13. **No new dependencies.**

---

## Suggested PR shape

~12 commits across 11 tasks (per locked #10):

1. T01 ParaStyles
2. T02 build_template + build_preview split
3. T03 V1 layout (delete old frames + add new — Hero-Foto-Card, 3 cards, stat/label/body)
4. T04 INJECT_MAP (post-#24 pattern)
5. T05 CONSTRAINTS rewrite (corrected per locked #2)
6. T06 regen + SHA bump
7. T07 brand_overrides cleanup
8. T08 smoke test rewrite
9. T09 spec rewrite
10. T10 invariant tests in NEW test_themen_plakat_geometry.py
11. T11 brief §10 + EXECUTION

Plus artifact commits. ~14 commits total.

Next: `/issue:plan` turns this into XML-tagged tasks.
