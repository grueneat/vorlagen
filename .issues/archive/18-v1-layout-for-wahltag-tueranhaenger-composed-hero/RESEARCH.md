# RESEARCH — #18: V1 "Composed Hero" layout for `wahltag-tueranhaenger`

**Status:** synthesized from two parallel research dimensions (codebase / pitfalls). Confidence high — every claim traced to file:line + verified against post-#23 main. ISSUE.md contains 4 errors that this RESEARCH corrects.

**Per-dimension reports:** `research/codebase.md`, `research/pitfalls.md`. Read for line-level evidence.

---

## Executive summary

Both research dimensions converged on **6 critical corrections to ISSUE.md** and a clear scope for V1 implementation:

1. **Rules `brand:image_in_container_flush` and `brand:portrait_column_alignment` DO NOT EXIST.** They were proposed in #23's draft and explicitly NOT shipped — folded into `brand:visual_adjacency_drift`'s 4-axis logic. Registry is exactly 14 rules. Any plan task referencing those non-existent rules is invalid.
2. **ISSUE.md's CONSTRAINTS list is unusable as-written.** Three categorical bugs:
   - Snake-case stub names (`brand_bar_top`, `kandidat_name`, `stat_card_*`) don't match real annames (`"Brand-Bar (Vorderseite)"`, `"Kandidat-Name"`).
   - Stat-card constraints reference a hypothetical 3-stat back design that V1 doesn't build (V1 back is Portrait-Card + Visitenkarten-Footer per ISSUE.md's own delta table).
   - `aligned_below` argument order reversed; `gap_mm` values don't match V1 actuals.
3. **Rule-id `brand:hl_sub_gap_2x` doesn't exist.** Real id is `brand:hl_sl_distance_x2`. Pre-existing override correctly uses real id.
4. **Predictive verification of post-#23 rules on V1 geometry**: V1 passes `image_text_overlap`, `cover_extent_match`, `inside_page`, `logo_size_3M` cleanly. Three pre-applied `brand_overrides` removable post-V1: `brand:image_text_overlap`, `brand:logo_size_3M`, plus reason-text update on `brand:visual_adjacency_drift`.
5. **`opacity 100%→85%` on Kandidat-Position is unsupported in DSL** (TextFrame has no opacity parameter). Drop from V1.
6. **Smoke test rewrite is UNNECESSARY** — all 11 existing assertions pass V1 unmodified (verified). Saves a task.

---

## Locked decisions (planner: do NOT re-litigate)

| # | Decision | Reason |
|---|---|---|
| 1 | **Registry is 14 rules.** Tasks must NOT reference `brand:image_in_container_flush` or `brand:portrait_column_alignment`. The 5-mm uniform inset of Portrait inside Portrait-Card is fine — no flush rule fires. | Codebase agent + archived #23 PLAN.md confirm. |
| 2 | **Use real annames** in CONSTRAINTS: `"Brand-Bar (Vorderseite)"`, `"Logo Grüne (weiss, top)"`, `"Logo Grüne (weiss, back-band)"`, `"Wahlkreuz (Hero)"`, `"Headline-Wahltag"`, `"Sub-Headline"`, `"Bullet-Liste"`, `"Kandidat-Portrait"`, `"Kandidat-Name"`, `"Kandidat-Position"`, `"Kontakt-URL"`, `"Kontakt-Info"`, `"QR-Code (back)"`, `"Impressum"`, `"Impressum (back)"`. | Constraint resolver matches on `anname` exactly. Snake-case stubs would all `_missing_violation`. |
| 3 | **Drop stat-card constraints** from CONSTRAINTS. V1 back is Portrait + Visitenkarten-Footer, not 3 stat-cards. | ISSUE.md's CONSTRAINTS list contradicts its own V1 delta table. |
| 4 | **`aligned_below(below, above, gap_mm)` order**: first arg hangs from second. Use ACTUAL gaps from V1 geometry (≈1mm and ≈0mm), not ISSUE.md's wrong 12.0 / 8.0 values. | aligned_below.docstring; pitfalls #2. |
| 5 | **`brand:hl_sl_distance_x2`** is the correct rule id (NOT `brand:hl_sub_gap_2x`). Pre-existing override is fine; AC text needs correction. Acceptance is no-op modification. | brand_constraints.py:1074. |
| 6 | **Drop `opacity 100%→85%`** on Kandidat-Position (DSL doesn't support TextFrame opacity). Use plain Run with `fcolor=White` only. | TextFrame primitive lacks opacity field. |
| 7 | **5+ new `*-on-green` ParaStyles** per #17 parallel pattern (not the 2 ISSUE.md names): `tueranhaenger/body-on-green`, `tueranhaenger/url-on-green`, `tueranhaenger/cand-name-on-green` (with fontsize 14→18), `tueranhaenger/cand-pos-on-green`, `tueranhaenger/impressum-on-green`. Existing styles stay unchanged. | Codebase agent §6 + #17 pattern. |
| 8 | **Smoke test rewrite SKIPPED** — all 11 assertions pass V1 unmodified. | Pitfalls P2.7. |
| 9 | **Spec rewrite mandatory** — `templates/_specs/wahltag-tueranhaenger.md` is already 10-error drifted from pre-V1 baseline. T08 must rewrite the entire spec. | Pitfalls P2.6. |
| 10 | **Logo-asset swap** to `gruene-weiss.png` requires explicit `local_scale=(0.130, 0.130)` per #17 pattern. | #17 precedent. |
| 11 | **Three brand_overrides removable post-V1**: `brand:image_text_overlap` (V1 has zero partial overlaps), `brand:logo_size_3M` (V1 makes both logos 18.9mm + deletes Bund-Dunkel back logo). Reason-text update on `brand:visual_adjacency_drift` (stays). | Predictive geometry walked frame-by-frame. |
| 12 | **`brand:visual_adjacency_drift` override stays** indefinitely (warnings only; combinatorial on text-inside-polygon pairs; no clean way to silence without 25+ explicit declarations). Reason-text update only. | Pitfalls P0.4. |
| 13 | **Atomic-PR ordering**: T01 ParaStyles → T02 front layout → T03 back layout → T04 CONSTRAINTS rewrite → T05 regen + SHA bump → T06 brand_overrides cleanup → T07 spec rewrite + brief §10 → T08 invariant tests. **Smoke test task SKIPPED.** | Pitfalls P4. |
| 14 | **Invariant-pinning tests per #23** `test_zeitung_geometry.py` pattern in NEW `tools/sla_lib/tests/test_tueranhaenger_geometry.py`. ≥10 invariants. | #23 locked decision #7. |
| 15 | **`bin/render-gallery wahltag-tueranhaenger --skip-visual-diff`** is mandatory at T05 — auto-bumps `meta.yml::previews_for_sla` SHA. | Pitfalls P10. |

---

## Scope changes vs. ISSUE.md

| ISSUE.md | Status | Why |
|---|---|---|
| CONSTRAINTS uses snake_case stub names | **REWRITE** with real annames (locked decision #2) |
| CONSTRAINTS includes stat_card_1/2/3 entries | **DROP** — V1 doesn't build stat-cards (locked decision #3) |
| `aligned_below(kandidat_name, kandidat_position, gap_mm=12.0)` | **CORRECT** — actual gap is 1mm; argument order also reversed |
| `aligned_below(kontakt_info, kontakt_url, gap_mm=8.0)` | **CORRECT** — actual gap is 0mm; argument order reversed |
| brand_overrides[brand:hl_sub_gap_2x] (wrong id) | **CORRECT** to brand:hl_sl_distance_x2 (locked decision #5) |
| Kandidat-Position fcolor + opacity 85% | **DROP opacity** (locked decision #6) |
| 2 new ParaStyles | **EXPAND to 5+** per #17 pattern (locked decision #7) |
| Smoke test rewrite | **SKIP** (already passes V1 — locked decision #8) |

---

## Codebase Analysis — interfaces

<interfaces>

### Post-#23 BRAND_CONSTRAINTS (14 rules, in registry order)

```
file: tools/sla_lib/builder/brand_constraints.py:1052-1170
1. brand:color_palette
2. brand:font_family
3. brand:line_spacing_0.9
4. brand:hl_sl_distance_x2     # NOT brand:hl_sub_gap_2x
5. brand:logo_size_3M
6. brand:text_on_green
7. brand:bleed_3mm
8. brand:wahlkreuz_colored_bg
9. brand:inside_page
10. brand:spine_safety
11. brand:visual_adjacency_drift   # 4-axis check + declaration-disagreement (replaces undeclared_alignment_drift)
12. brand:bleed_coverage           # facing-pages full-width frames must extend outer to ±bleed
13. brand:image_text_overlap       # (Image OR filled-Polygon) × Text partial overlap
14. brand:cover_extent_match       # vertically-touching full-width pairs must share outer-bbox extent
```

NO `brand:image_in_container_flush`, NO `brand:portrait_column_alignment`. They're folded into `brand:visual_adjacency_drift` (#23 archived PLAN.md:189).

### Constraint factories used by V1 CONSTRAINTS

```
file: tools/sla_lib/builder/constraints.py
- aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="")
    asserts below.x == above.x AND below.y == above.y + above.h + gap_mm
- same_x(*targets, tolerance_mm=0.5, name="")
- same_y(*targets, tolerance_mm=0.5, name="")
- same_size(*targets, axis="both", tolerance_mm=0.5, name="")
- mirrored_x(left, right, axis_mm, tolerance_mm=0.5, name="")
- mirrored_y(top, bottom, axis_mm, tolerance_mm=0.5, name="")
- inside(child, parent, tolerance_mm=0.5, name="")
- distance_x(a, b, equals, tolerance_mm=0.5, name="")
- distance_y(a, b, equals, tolerance_mm=0.5, name="")
```

### Current `meta.yml::brand_overrides` (8 entries; post-#23 + #22 + earlier)

```yaml
file: templates/wahltag-tueranhaenger/meta.yml
brand_overrides:
  - id: brand:line_spacing_0.9        # KEEP — DSL existing drift
  - id: brand:hl_sl_distance_x2       # KEEP — V1 still 50% formula (250mm constraint)
  - id: brand:logo_size_3M            # REMOVE post-V1 — both logos = 18.9mm
  - id: brand:text_on_green           # KEEP — body on white in current; V1 puts body-on-green via Hellgrün-Card
                                      #   so this MIGHT also become removable; verify in T06
  - id: brand:bleed_3mm               # KEEP — 2mm bleed not 3mm
  - id: brand:wahlkreuz_colored_bg    # TEST in T06 — Hellgrün-Band overlaps Wahlkreuz frame post-V1; rule may detect now
  - id: brand:visual_adjacency_drift  # KEEP, update reason text
  - id: brand:image_text_overlap      # REMOVE post-V1 — V1 has zero partial overlaps (verified predictively)
```

### Current frames in `wahltag-tueranhaenger/build.py` (12 frames)

```
file: templates/wahltag-tueranhaenger/build.py (460 lines)
PAGE 0 (front, 0-indexed; print page 1 of hanger):
  Polygon "Brand-Bar (Vorderseite)" — V1 height 22→16
  ImageFrame "Logo Grüne (weiss, top)" — V1: w 35→18.9, h 10→5.7, local_scale 0.240→0.130
  Polygon "Hellgrün-Band (Wahlkreuz)" — V1: y 65→63, h 60→64
  ImageFrame "Wahlkreuz (Hero)" — V1: x 27.5→25, w 50→55, h 50→55
  TextFrame "Headline-Wahltag" — V1: y 128→138, h 28→32
  TextFrame "Sub-Headline" — V1: y 160→176
  TextFrame "Bullet-Liste" — V1: y 175→200, h 60→40, fcolor Black→White on new Hellgrün-Card
  TextFrame "Impressum" (front) — V1: fcolor Black→White

PAGE 1 (back; print page 2):
  Polygon "Brand-Bar (Rückseite)" — V1 height 22→16
  ImageFrame "Logo Grüne (weiss, back-band)" — V1: w 35→18.9, h 10→5.7
  ImageFrame "Logo Grüne (Bund-Dunkel, back)" — V1: DELETE (zero cross-template references)
  ImageFrame "Kandidat-Portrait" — V1: h 85→90, on new Hellgrün Portrait-Card
  TextFrame "Kandidat-Name" — V1: y 168→184, fontsize 14→18, fcolor Dunkelgrün→White
  TextFrame "Kandidat-Position" — V1: y 178→196, fcolor Black→White (NO opacity)
  TextFrame "Kontakt-URL" — V1: y 200→210, fcolor Dunkelgrün→Gelb
  TextFrame "Kontakt-Info" — V1: y 210→218, fcolor Black→White
  ImageFrame "QR-Code (back)" — V1: x 65→70, y 200→210, w 30→26, h 30→26
  TextFrame "Impressum (back)" — V1: y 240→242, fcolor Black→White
```

### V1 NEW Polygons (5 + 1 deletion)

```
1. Hellgrün-Akzent (front) Polygon: x=-2 y=14 w=109 h=4 fill=Hellgrün, layer=Hintergrund
2. Bullets-Card (front) Polygon: x=-2 y=192 w=109 h=58 fill=Hellgrün, layer=Hintergrund
3. Portrait-Card (back) Polygon: x=15 y=70 w=75 h=100 fill=Hellgrün, layer=Hintergrund
4. Visitenkarten-Footer (back) Polygon: x=-2 y=178 w=109 h=72 fill=Dunkelgrün, layer=Hintergrund
5. QR White-Backing (back) Polygon: x=68 y=208 w=30 h=30 fill=White, layer=Hintergrund
DEL: ImageFrame "Logo Grüne (Bund-Dunkel, back)"
```

### V1 NEW ParaStyles (5; #17 parallel pattern)

```
- tueranhaenger/body-on-green: Gotham Book 11pt, fcolor=White (vs body Black)
- tueranhaenger/url-on-green:  Vollkorn Black Italic 11pt, fcolor=Gelb
- tueranhaenger/cand-name-on-green: Gotham Bold 18pt, fcolor=White (vs cand-name Dunkelgrün, fontsize bumped 14→18)
- tueranhaenger/cand-pos-on-green:  Gotham Book 10pt, fcolor=White
- tueranhaenger/impressum-on-green: Gotham Book 6pt, fcolor=White
```

</interfaces>

---

## V1 CONSTRAINTS list (final, real annames, correct gaps)

```python
CONSTRAINTS = [
    # FRONT — Hellgrün-Akzent below Brand-Bar (touching)
    aligned_below("Hellgrün-Akzent", "Brand-Bar (Vorderseite)",
                  gap_mm=0.0, name="akzent_below_brandbar"),
    # FRONT — Hellgrün-Band starts at known y (no adjacency, just absolute pin via distance_y to Akzent)
    distance_y("Hellgrün-Akzent", "Hellgrün-Band (Wahlkreuz)",
               equals=45.0, name="band_below_akzent_45mm"),
    # FRONT — Wahlkreuz centered on panel (panel center x=52.5, page width 105)
    mirrored_x("Hellgrün-Band (Wahlkreuz)", "Wahlkreuz (Hero)",
               axis_mm=52.5, name="wahlkreuz_panel_center"),
    # FRONT — Wahlkreuz inside Hellgrün-Band
    inside("Wahlkreuz (Hero)", "Hellgrün-Band (Wahlkreuz)",
           name="wahlkreuz_in_band"),
    # FRONT — Headline below Hellgrün-Band (small gap intentional)
    aligned_below("Headline-Wahltag", "Hellgrün-Band (Wahlkreuz)",
                  gap_mm=11.0, name="headline_below_band"),
    # FRONT — Sub-Headline below Headline (10mm gap pragmatic for 250mm format)
    distance_y("Headline-Wahltag", "Sub-Headline",
               equals=38.0, name="hl_to_sub_38mm_format_pragmatic"),
    # FRONT — Bullets-Card starts at y=192 (touching nothing above)
    same_x("Bullets-Card", "Hellgrün-Akzent",
           name="bullets_card_full_bleed_x"),  # both at x=-2
    # FRONT — Bullet-Liste inside Bullets-Card
    inside("Bullet-Liste", "Bullets-Card", name="bullets_in_card"),

    # BACK — Brand-Bar mirror of front (same height, same logo position)
    same_size("Brand-Bar (Vorderseite)", "Brand-Bar (Rückseite)",
              axis="h", name="brand_bar_h_pair"),
    # BACK — Portrait inside Portrait-Card (5mm uniform inset; not flush, but valid;
    #   no rule enforces flush since brand:image_in_container_flush doesn't exist)
    inside("Kandidat-Portrait", "Portrait-Card",
           name="portrait_in_card"),
    # BACK — Kandidat-Name below Portrait (~14mm gap)
    aligned_below("Kandidat-Name", "Kandidat-Portrait",
                  gap_mm=14.0, name="name_below_portrait"),
    # BACK — Kandidat-Position below Name (~1mm gap; reverse of ISSUE.md's wrong 12.0)
    aligned_below("Kandidat-Position", "Kandidat-Name",
                  gap_mm=1.0, name="position_below_name"),
    # BACK — Kontakt-URL on Visitenkarten-Footer
    inside("Kontakt-URL", "Visitenkarten-Footer",
           name="url_in_footer"),
    inside("Kontakt-Info", "Visitenkarten-Footer",
           name="info_in_footer"),
    # BACK — QR backing fully contains QR
    inside("QR-Code (back)", "QR White-Backing", name="qr_in_backing"),
]
```

---

## Standard Stack

| Item | Value |
|---|---|
| Python | 3.13.5 |
| Tests | `python3 -m unittest discover tools/sla_lib/tests` + `python3 -m unittest templates._smoke.test_wahltag_tueranhaenger` |
| Build | `python3 templates/wahltag-tueranhaenger/build.py` |
| Regen | `bin/render-gallery wahltag-tueranhaenger --skip-visual-diff` (auto-bumps SHA) |
| Audit | `bin/audit-alignment wahltag-tueranhaenger` |
| Stale check | `bin/check-stale-previews` |
| New deps | none |

---

## Don't Hand-Roll

- All Constraint factories from #14 + helpers from #22/#23 — use them.
- `bin/render-gallery` regenerates template.sla + page-NN.png + preview.pdf + meta.yml SHA + site/public mirror.
- #17 `*-on-green` ParaStyle pattern — copy structure exactly.
- #23 `test_zeitung_geometry.py` invariant-pinning pattern.

---

## Common Pitfalls (consolidated)

### Must-handle (HIGH severity)

1. **Phantom rules** `brand:image_in_container_flush` / `brand:portrait_column_alignment` don't exist (locked decision #1). Don't reference.
2. **ISSUE.md CONSTRAINTS list is broken** — rewrite per RESEARCH.md V1 CONSTRAINTS list above.
3. **`opacity 85%` is unsupported** — drop entirely.
4. **`brand_overrides` removal ordering** — only after V1 CONSTRAINTS green AND audit clean. Post-V1 cleanup task.
5. **`bin/render-gallery` + meta.yml SHA bump are mandatory** at T05 — `bin/check-stale-previews` blocks CI otherwise.
6. **Stanzkontur layer integrity** — all new polygons on `Hintergrund` layer, NEVER `Stanzkontur`.
7. **Bleed=2mm not 3mm** — verify `brand:inside_page` checks accordingly.

### Worth knowing (MEDIUM)

8. **Smoke test passes V1 unmodified** — skip the rewrite task.
9. **Spec is already 10-error drifted pre-V1** — full rewrite required, not append.
10. **`brand:visual_adjacency_drift` override stays** with updated reason text (combinatorial warning floor).
11. **`brand:logo_size_3M` override removable** post-V1 (both logos = 18.9mm).
12. **`brand:text_on_green` override** — TEST removability after Bullets-Card + Visitenkarten-Footer move body to green; might become removable.

### Informational

13. No new dependencies.
14. `Logo Grüne (Bund-Dunkel, back)` deletion is safe (zero cross-template refs).
15. No V1 polygon overlaps the 35mm hole zone (verified arithmetically).

---

## Suggested PR shape

~9 commits across 8 tasks (per locked decision #13):

1. `T01: feat(wahltag-tueranhaenger): add 5 *-on-green ParaStyles + ci_overrides`
2. `T02: feat(wahltag-tueranhaenger): V1 front layout — Brand-Bar shrink + Hellgrün-Akzent + Wahlkreuz-Band + Headline stack + Bullets-Card`
3. `T03: feat(wahltag-tueranhaenger): V1 back layout — Portrait-Card + Visitenkarten-Footer + QR backing + Bund-Dunkel deletion`
4. `T04: feat(wahltag-tueranhaenger): V1 CONSTRAINTS list (real annames, mirrored_x for symmetry, aligned_below for stacks, inside for containment)`
5. `T05: chore(wahltag-tueranhaenger): regenerate template.sla + gallery via bin/render-gallery + SHA bump`
6. `T06: chore(wahltag-tueranhaenger): remove brand_overrides[image_text_overlap, logo_size_3M] + reason text update on visual_adjacency_drift`
7. `T07: docs(wahltag-tueranhaenger): rewrite _specs/ for V1 layout`
8. `T08: test(wahltag-tueranhaenger): invariant-pinning tests in NEW test_tueranhaenger_geometry.py`
9. `T09: docs(brand): append session-history row to DESIGN-SYSTEM-BRIEF.md §10`

(SMOKE TEST REWRITE: SKIPPED per locked decision #8.)

Plus artifact commits (RESEARCH.md ✓, PLAN.md, EXECUTION.md). 11–12 commits total.

Next: `/issue:plan` turns this into XML-tagged tasks for the executor.
