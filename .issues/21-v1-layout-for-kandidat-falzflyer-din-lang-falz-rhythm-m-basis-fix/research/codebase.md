# Codebase research — #21 V1 "Falz-Rhythm" for kandidat-falzflyer-din-lang

Live verification (2026-05-09):
- `python3 templates/kandidat-falzflyer-din-lang/build.py` → wrote template.sla cleanly.
- `python3 -m unittest templates._smoke.test_kandidat_falzflyer_din_lang` → 11/11 OK.
- `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang` → 0 errors / 0 warnings / 6 skipped (= 6 brand_overrides) / 19 passes.
- `PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_infostand_tent_card_geometry` → 21/21 OK (#20 baseline).

## 1. Current build.py inventory (`templates/kandidat-falzflyer-din-lang/build.py`, 684 lines)

### 1.1 Constants (L43–54)
```
TRIM_W_MM = 297.0
TRIM_H_MM = 210.0
BLEED_MM = 3.0
PANEL_W_MM = 99.0
FOLD_X1_MM = 99.0
FOLD_X2_MM = 198.0
LAYER_HINTERGRUND = 0
LAYER_BILDER = 1
LAYER_TEXT = 2
LAYER_FALZ = 3
```

### 1.2 ParaStyles registered (L57–178) — 12 styles, all `align=0`, all `linesp_mode=0`

| L | name | font | size | linesp | align | fcolor |
|---|---|---|---|---|---|---|
| 59  | `falzflyer/cand-name`        | Vollkorn Black Italic | 24 | 27 | 0 | Dunkelgrün |
| 69  | `falzflyer/slogan`           | Gotham Narrow Bold    | 14 | 17 | 0 | Black |
| 79  | `falzflyer/teaser-headline`  | Gotham Narrow Bold    | 18 | 22 | 0 | Dunkelgrün |
| 89  | `falzflyer/teaser-body`      | Gotham Narrow Book    | 11 | 14 | 0 | Black |
| 99  | `falzflyer/closer-headline`  | Gotham Narrow Bold    | 22 | 26 | 0 | White |
| 109 | `falzflyer/closer-datum`     | Vollkorn Black Italic | 14 | 18 | 0 | Gelb |
| 119 | `falzflyer/closer-url`       | Gotham Narrow Bold    | 11 | 14 | 0 | White |
| 129 | `falzflyer/thema-headline`   | Gotham Narrow Bold    | 16 | 20 | 0 | Dunkelgrün |
| 139 | `falzflyer/thema-body`       | Gotham Narrow Book    |  9 | 11 | 0 | Black |
| 149 | `falzflyer/contact-headline` | Gotham Narrow Bold    | 16 | 20 | 0 | Dunkelgrün |
| 159 | `falzflyer/contact-body`     | Gotham Narrow Book    | 10 | 12 | 0 | Black |
| 169 | `falzflyer/impressum`        | Gotham Narrow Book    |  6 |  8 | 0 | Black |

Note 1: spec ISSUE.md uses spelling `falzflyer/themen-*` (plural with "n") but the code has `falzflyer/thema-*` (singular). The CONSTRAINTS in ISSUE.md (`p4_thema_a_*`) are coord-stub names not anname references — to disambiguate, the planner must use the REAL annames `P4 Thema 1 — Headline` etc. (em-dash, see L382 etc.).

Note 2: ISSUE.md mentions `falzflyer/contact-label` as one of the 9 align flips. **No such style exists today**; either (a) treat as NEW style, or (b) reuse `contact-body` for label rows. Cleanest: ADD a NEW `falzflyer/contact-label` (small Caps) — see locked decisions in RESEARCH.md.

### 1.3 Frame inventory — Front (page0, `_add_front`, L181–350)

| L  | anname                | type      | x   | y   | w  | h   | layer       | fill / asset |
|----|-----------------------|-----------|-----|-----|----|-----|-------------|--------------|
|184 | `P3 Hintergrund`      | Polygon   | 198 | -3  | 102| 216 | HINTERGRUND | Dunkelgrün full-bleed |
|204 | `P1 Logo Grüne`       | ImageFrame|   6 |  10 | 20 |  18 | BILDER      | gruene-logo-bund-dunkel.png |
|223 | `P1 Kandidat-Portrait`| ImageFrame|   6 |  28 | 87 | 105 | BILDER      | library `portrait_maria` (optional, crop_for_frame) |
|232 | `P1 Kandidat-Name`    | TextFrame |   6 | 138 | 87 |  18 | TEXT        | style=falzflyer/cand-name |
|241 | `P1 Slogan`           | TextFrame |   6 | 158 | 87 |  40 | TEXT        | style=falzflyer/slogan, 2 paras |
|255 | `P2 Teaser-Headline`  | TextFrame | 105 |  20 | 87 |  22 | TEXT        | style=falzflyer/teaser-headline |
|263 | `P2 Teaser-Body`      | TextFrame | 105 |  44 | 87 | 130 | TEXT        | style=falzflyer/teaser-body, 2 paras |
|283 | `P2 Logo (klein)`     | ImageFrame| 105 | 188 | 16 |  14 | BILDER      | gruene-logo-bund-dunkel.png |
|297 | `P3 Wahlkreuz`        | ImageFrame| 222 |  30 | 50 |  50 | BILDER      | shared/assets/wahlkreuz.png |
|307 | `P3 Closer-Headline`  | TextFrame | 204 |  90 | 87 |  32 | TEXT        | style=falzflyer/closer-headline, 2 paras |
|320 | `P3 Datum-Akzent`     | TextFrame | 204 | 125 | 87 |  22 | TEXT        | style=falzflyer/closer-datum |
|329 | `P3 URL`              | TextFrame | 204 | 175 | 87 |  12 | TEXT        | style=falzflyer/closer-url |
|339 | `Falz x=99 (Front)`   | FoldLine  |  99 |   0 |  0 | 210 | FALZ        | (block) |
|345 | `Falz x=198 (Front)`  | FoldLine  | 198 |   0 |  0 | 210 | FALZ        | (block) |

### 1.4 Frame inventory — Back (page1, `_add_back`, L353–575)

```python
THEMEN_LIBRARY_IDS = {
    "klimaschutz": "themen_klimaschutz_solar",
    "soziales":    "themen_soziales_kaffeehaus",
    "bildung":     "themen_bildung_volksschule",
}
THEMEN_FRAME_W_MM = 87.0    # L364
THEMEN_FRAME_H_MM = 24.0    # L365
```

`_photo_inline(name)` calls `library.crop_for_frame(img, target_w_mm=87, target_h_mm=24)` → produces 3.625:1 horizontal slabs from 1.5:1 source = "halb-leer Streifen" issue cited in spec.

| L   | anname                  | type      | x   | y   | w  | h  | layer | fill / asset |
|-----|-------------------------|-----------|-----|-----|----|----|-------|--------------|
|377  | `P4 Thema 1 — Headline` | TextFrame |   6 |  20 | 87 | 14 | TEXT  | style=falzflyer/thema-headline |
|385  | `P4 Thema 1 — Photo`    | ImageFrame|   6 |  36 | 87 | 24 | BILDER| library `themen_klimaschutz_solar` |
|393  | `P4 Thema 1 — Body`     | TextFrame |   6 |  62 | 87 | 32 | TEXT  | style=falzflyer/thema-body |
|404  | `P4 Thema 2 — Headline` | TextFrame |   6 | 105 | 87 | 14 | TEXT  | style=falzflyer/thema-headline |
|412  | `P4 Thema 2 — Photo`    | ImageFrame|   6 | 121 | 87 | 24 | BILDER| library `themen_soziales_kaffeehaus` |
|420  | `P4 Thema 2 — Body`     | TextFrame |   6 | 147 | 87 | 32 | TEXT  | style=falzflyer/thema-body |
|432  | `P5 Thema 3 — Headline` | TextFrame | 105 |  20 | 87 | 14 | TEXT  | style=falzflyer/thema-headline |
|440  | `P5 Thema 3 — Photo`    | ImageFrame| 105 |  36 | 87 | 24 | BILDER| library `themen_bildung_volksschule` |
|448  | `P5 Thema 3 — Body`     | TextFrame | 105 |  62 | 87 | 32 | TEXT  | style=falzflyer/thema-body |
|459  | `P5 Thema 4 — Headline` | TextFrame | 105 | 105 | 87 | 14 | TEXT  | style=falzflyer/thema-headline |
|466  | `P5 Thema 4 — Body`     | TextFrame | 105 | 121 | 87 | 58 | TEXT  | style=falzflyer/thema-body — taller body, no photo today |
|479  | `P6 Kontakt-Headline`   | TextFrame | 204 |  20 | 87 | 14 | TEXT  | style=falzflyer/contact-headline |
|486  | `P6 Kontakt-Adresse`    | TextFrame | 204 |  36 | 87 | 20 | TEXT  | style=falzflyer/contact-body, 2 paras |
|497  | `P6 Kontakt-Email-Tel`  | TextFrame | 204 |  58 | 87 | 20 | TEXT  | style=falzflyer/contact-body, 2 paras |
|522  | `P6 QR-Code (mitmachen)`| ImageFrame| 210 |  85 | 30 | 30 | BILDER| samples/qr-mitmachen.png (optional) |
|530  | `P6 QR-Code (termine)`  | ImageFrame| 246 |  85 | 30 | 30 | BILDER| samples/qr-termine.png (optional) |
|544  | `P6 Logo Grüne`         | ImageFrame| 204 | 130 | 17 | 15 | BILDER| gruene-logo-bund-dunkel.png |
|552  | `P6 Impressum`          | TextFrame | 204 | 145 | 87 | 60 | TEXT  | style=falzflyer/impressum |
|564  | `Falz x=99 (Back)`      | FoldLine  |  99 |   0 |  0 |210 | FALZ  | (block) |
|570  | `Falz x=198 (Back)`     | FoldLine  | 198 |   0 |  0 |210 | FALZ  | (block) |

### 1.5 Document setup (L578–611) and `build()` wrapper (L614–618)

- `Document` uses `Brand.gruene_noe()`, 4 layers (Hintergrund/Bilder/Text/Falz), Falz spot color CMYK(100,0,0,0).
- 1 master ("Normal", 297×210, bleed 3, margins 0/0/0/0), 2 pages.
- **No `build_template`/`build_preview` split today**. Issue #20 introduces that split via `INJECT_MAP`. Decision for #21: ADD the split (lock).
- `build()` saves to default `HERE / "template.sla"`.

### 1.6 CONSTRAINTS list (L628–678) — 9 entries

```python
same_style("P4 Thema 1 — Headline", "P4 Thema 2 — Headline",
           "P5 Thema 3 — Headline", "P5 Thema 4 — Headline",
           name="thema_headline_style_consistent"),
same_style("P4 Thema 1 — Body", "P4 Thema 2 — Body",
           "P5 Thema 3 — Body", "P5 Thema 4 — Body",
           name="thema_body_style_consistent"),
same_y("P4 Thema 1 — Headline", "P5 Thema 3 — Headline",
       name="thema_top_row_y"),
same_y("P4 Thema 2 — Headline", "P5 Thema 4 — Headline",
       name="thema_bottom_row_y"),
same_x("P4 Thema 1 — Photo", "P4 Thema 2 — Photo",
       name="p4_themen_left_edge"),
same_x("P4 Thema 1 — Headline", "P4 Thema 2 — Headline",
       name="p4_themen_hd_left_edge"),
distance_y("P4 Thema 1 — Headline", "P4 Thema 1 — Body", equals=42.0,
           name="thema1_hd_to_body"),
same_size("P4 Thema 1 — Photo", "P4 Thema 2 — Photo", "P5 Thema 3 — Photo",
          axis="both", name="thema_photos_uniform_size"),
distance_y("P4 Thema 1 — Headline", "P4 Thema 2 — Headline", equals=85.0,
           name="p4_thema_vertical_stride"),
```

V1 needs to REPLACE most of these — distance_y values change with the new y deltas; thema photo size becomes 87×44 not 87×24; new top-band/grüne-Klammer constraints land.

## 2. meta.yml inventory (`templates/kandidat-falzflyer-din-lang/meta.yml`, 188 lines)

- L18 `previews_for_sla:` SHA — auto-bumped by render-gallery.
- L21–58 `brand_overrides:` 6 entries:
  - `brand:line_spacing_0.9` (KEEP — narrow-panel readability rationale stays valid)
  - `brand:logo_size_3M` (REMOVE post-V1: V1 logos resize to 38mm = 3M Trim-konform)
  - `brand:visual_adjacency_drift` (REMOVE post-V1 once V1 CONSTRAINTS list captures adjacencies — locked per #22 decision #9)
  - `brand:image_text_overlap` (REMOVE post-V1 — Top-Bands + Backings make all overlaps intentional)
  - `brand:image_fills_frame` (REMOVE post-V1 — V1 Photo h=44 nearly matches native 1.5:1 + library.crop_for_frame already pre-crops)
  - `brand:band_consistency` (KEEP for now — body_block_margins spec authoring is a separate effort, deferred)
- L59–76 `ci_overrides.non_ci_styles:` 12 styles. V1 EXTENDS to add `falzflyer/top-title`, `falzflyer/themen-eyebrow`, `falzflyer/slogan-on-green`, `falzflyer/quote-on-green`, `falzflyer/contact-label` (the new ones).
- L78–173 `slots:` block with 23 anname entries. V1 EXTENDS to ~36+ entries.
- L175–177 `example_pages:` 2 pages, page labels can be retained.
- L183–187 `preflight:` bleed_mm=3, fold_mm=[99, 198], cmyk_only=true, min_image_dpi=300 — KEEP as-is.

## 3. Smoke test current state (`templates/_smoke/test_kandidat_falzflyer_din_lang.py`, 161 lines)

11 assertions: page count, trim dim, Falz layer/spot color, 4 fold lines (4 anname strings), P3 Dunkelgrün bg, Wahlkreuz on P3, **18+ slot annames** (will grow to ~36+ in V1), per-panel content w ≤ 88.5mm. Also 2 round-trip safety assertions on postkarte + plakat.

V1 will:
- Keep all 11 existing assertions (still pass post-V1).
- ADD V1-specific assertions: top-bands present (×6), Logo asset is `gruene-weiss.png` (P1 + P6), `gruene-logo-bund-dunkel.png` removed from P2 (P2 logo deleted), P1 Name-Card polygon present, P3 Hintergrund extended OR replaced with vollflächig P6 Kontakt-Hintergrund analog, etc.
- Update `test_panel_content_within_safe_width` filter (top-band polygons are full-bleed so should be excluded by the existing "Hintergrund" filter, but new "Top-Band" polygons need similar exemption).

## 4. Existing geometry test patterns

### 4.1 `tools/sla_lib/tests/test_infostand_tent_card_geometry.py` (#20, 21 invariants)

Pattern blueprint for #21:
- `setUpClass` builds doc once, indexes `items_by_anname`, also saves to tmp SLA + parses XML for ParaStyle/Falz-layer assertions via lxml.
- Helpers: `_f(anname)`, `_bbox_center`, `_right`, `_bottom`, `_assert_inside`.
- TOL_MM=0.6.
- Invariant categories: cross-pair mirror around axis, same-size pairs, intra-panel containment, baseline+height, logo width = 3M, ParaStyle existence (positive + negative), logo asset identity, Falz layer integrity (only ONE PAGEOBJECT on LAYER=3 — Mittelfalz), rotation contract.

### 4.2 `tools/sla_lib/tests/test_tueranhaenger_geometry.py` (#18, 12 invariants)

Pattern: brand_bar mirror, akzent touches band (gap=0), wahlkreuz centered on panel x=52.5, containment chain, vertical order preserved, full-bleed polygon extent ≥ outer trim ± tol, Logo size = 3M (kurze_kante=105 → 18.9 mm).

#21 will combine BOTH patterns: 6-panel uniform-band model (#20-style cross-pair tests × 6) + intra-panel containment (#18-style) + 3M logo verification with kurze_kante=210 → 38mm + an across-templates regression test for the M-Basis rule.

## 5. Constraint factory surface (`tools/sla_lib/builder/constraints.py`)

Live factories used by V1:
- `same_y(*targets, tolerance_mm=0.5, name="")` — L399
- `same_x(*targets, tolerance_mm=0.5, name="")` — L408
- `same_size(*targets, axis="both"|"w"|"h", tolerance_mm=0.5, name="")` — L417
- `mirrored_x(left, right, axis_mm, tolerance_mm=0.5, name="")` — L433 — vertical mirror line at x=axis_mm; centers average to axis_mm
- `mirrored_y(top, bottom, axis_mm, tolerance_mm=0.5, name="")` — L443
- `inside(child, parent, tolerance_mm=0.5, name="")` — L453 — raw bbox containment
- `aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="")` — L507 — REQUIRES same x_mm AND below.y == above.y + above.h + gap; rotated frames return warning (skipped)
- `same_style(*targets, name="")` — L481 — rotation-invariant
- `distance_y(a, b, equals, tolerance_mm=0.5, name="")` — L489
- `distance_x(a, b, equals, tolerance_mm=0.5, name="")` — L498

NO `Group`, NO `same_y_top`/`same_y_bottom`, NO `same_x_center`. Resolver matches `anname` exactly (`_to_anname`).

`_InsideConstraint.check` (L198–223) uses raw bbox; with `rotation_deg=0` everywhere on this template (no cross-fold rotation contract in 6-panel zickzack — UNLIKE #20 tent-card), `inside` works for ALL pairs including cross-panel.

## 6. BRAND_CONSTRAINTS — `brand:logo_size_3M` rule (`tools/sla_lib/builder/brand_constraints.py`)

L249–282:
```python
@dataclass(frozen=True)
class _LogoSize3MRule(BrandRule):
    factor: float = 3.0
    tolerance_mm: float = 0.5

    def check(self, primitives: list, doc, constraints=None) -> list:
        ...
        page = doc.pages[0]
        page_w_mm = page.width_pt * PT_TO_MM
        page_h_mm = page.height_pt * PT_TO_MM
        kurze_kante = min(page_w_mm, page_h_mm)   # ALREADY trim-based (no Panel-W ambiguity in code)
        m = 0.06 * kurze_kante
        expected = self.factor * m
        for p in primitives:
            if not isinstance(p, ImageFrame): continue
            anname = getattr(p, "anname", "") or ""
            if not re.search(r"\blogo\b", anname, re.IGNORECASE): continue
            if abs(p.w_mm - expected) > self.tolerance_mm:
                violations.append(Violation(...message=f"logo {anname!r} w_mm={p.w_mm} != 3*M ({expected:.2f}mm) ..."))
```

**This rule already implements the Trim-konsistent definition.** No change required in `tools/sla_lib/builder/brand_constraints.py` itself.

The **only thing the spec/issue calls "M-Basis-Konflikt"** is the comment-in-build.py drift, where `templates/kandidat-falzflyer-din-lang/build.py` L195–199 says:
```
# On DIN-lang (kurze Kante=105) Quickguide Print target = 3×M = 18.9 mm —
# 20 mm sits at 106 %, well within tolerance.
```
This comment is INCORRECT: the page object is the FULL A4 sheet (297×210), so the rule's `kurze_kante` is **210 mm**, M=12.6, **3M=37.8 mm** — and the current 20mm logo is at 53% of soll. The fix is:
1. Update the comment in build.py to reflect Trim-M = 12.6 mm / 3M = 37.8 mm.
2. Resize 3 logos in build.py: P1 20→38mm, P2 16→delete (Top-Band replaces it), P6 17→38 mm.
3. Drop the `brand:logo_size_3M` override from meta.yml.
4. Add geometry test asserting logo width = 37.8 ± 0.5 mm on P1 + P6.

## 7. The "tools/check_ci.py" mention in ISSUE.md is misleading

ISSUE.md Open Question 1 says "Update `tools/check_ci.py` to enforce M = `0.06 × min(trim_w, trim_h)`". But `tools/check_ci.py` (266 lines) only contains the brand-color/style drift validator (CMYK/RGB+font checks); it does NOT contain any M-Basis rule. The M-Basis rule lives in `tools/sla_lib/builder/brand_constraints.py` (above, §6) and is ALREADY trim-konform.

**Empirical verification** (live, 2026-05-09):
```
PYTHONPATH=tools python3 -c "<run brand:logo_size_3M against each template>" produces:
  wahlaufruf-postkarte-a6-quer:        PASS (logo 18.9mm, kurze_kante=105, 3M=18.9)
  wahltag-tueranhaenger:               PASS (×2 logos at 18.9mm)
  themen-plakat-a3-quer:               PASS (logo 53.46mm, kurze_kante=297, 3M=53.46)
  infostand-tent-card-a5-quer:         PASS (×2 logos at 38mm vs 3M=37.8 — within ±0.5 tol)
  kandidat-falzflyer-din-lang:         FAIL ×3 — P1 20mm, P2 16mm, P6 17mm vs 3M=37.8 (kurze_kante=210)
```

Conclusion: **No change needed in any tool**. The "M-Basis-Konflikt" reduces to a build.py comment drift on kandidat-falzflyer + the 3 actual logo resizes which V1 already plans. The other 4 V1 templates are ALREADY trim-konform under the existing rule. No regression risk for them.

## 8. Logo asset inventory (`shared/logos/`)

| File | Size | Notes |
|---|---|---|
| `gruene-cmyk.png` | 413×118 RGB (3.5:1 wordmark) | older brand_book |
| `gruene-logo-bund-dunkel.png` | 499×445 RGBA (1.12:1 brushstroke G + tag) | currently used on falzflyer P1+P2+P6 |
| `gruene-logo-bund-dunkel.svg` | vector | not used in current build |
| `gruene-weiss.png` | 413×118 RGB (3.5:1 wordmark, white-on-transparent) | used on infostand-tent-card V1; spec calls for it on P1+P6 of falzflyer V1 |
| `sonnenblume-circle.png` | — | n/a here |

**No `gruene-bund-weiss.png` exists**. Issue spec mentions "weiße Variante" for full Print-Soll 38×22 — meaning the wordmark `gruene-weiss.png` (already 3.5:1). Frame at 38×22 mm has aspect 1.73:1; with `scale_type=0, ratio=1` Scribus auto-fits preserving aspect → image renders width-bound at 38×(38/3.5)=10.86 mm tall, vertically centered in the 22 mm frame (~5.6 mm padding above + below). **Rule fires on frame.w_mm**: frame `w=38` ≈ 3M=37.8 within ±0.5 ✓. This is the same situation #20 already accepted (#20 RESEARCH addendum).

Spec ISSUE.md line 39 says "Logo (weiß) `38×34` at footer" for P6 — that's a taller frame. But spec text §"Universal Top-Band" line 28 says "Logo (white, P1 + P6 only — full Print-Soll 38×22 mm)". So:
- P1 logo frame: 38×22 mm in Top-Band (w_mm=38 → rule passes).
- P6 logo frame in spec table: `w 17→38, h 15→34` (so 38×34 at footer). w_mm=38 → rule passes.

For consistency, the geometry test should assert P1.w_mm == P6.w_mm == 38 ± 0.5.

## 9. Library + sample assets

- **`portrait_maria`** — `shared/sample-images/portraits/maria-beispiel.jpg` (manifest L30). crop_focus [0.50, 0.32]. EXISTS.
- **`themen_klimaschutz_solar`** — `themen/klimaschutz-solar.jpg`. crop_focus [0.55, 0.45]. EXISTS.
- **`themen_soziales_kaffeehaus`** — `themen/soziales-kaffeehaus.jpg`. crop_focus [0.42, 0.55]. EXISTS.
- **`themen_bildung_volksschule`** — `themen/bildung-volksschule.jpg`. crop_focus [0.50, 0.60]. EXISTS.
- **`themen_wirtschaft_handwerk`** — `themen/wirtschaft-handwerk.jpg`. crop_focus [0.50, 0.55]. EXISTS.
- `templates/kandidat-falzflyer-din-lang/samples/qr-mitmachen.png` + `qr-termine.png` — both exist.

**Spec quote: "P5 Thema 4 gets a photo (asset `samples/themen-wirtschaft.jpg` — flag for #13)".** This is OUTDATED — the asset is in the central library at `shared/sample-images/themen/wirtschaft-handwerk.jpg` (manifest id `themen_wirtschaft_handwerk`). NO NEW ASSET CREATION NEEDED. Just extend the build.py THEMEN_LIBRARY_IDS dict with `"wirtschaft": "themen_wirtschaft_handwerk"` and call `_photo_inline("wirtschaft")` for P5 Thema 4.

## 10. tools/check_ci.py review

`tools/check_ci.py` validates brand-color hex/cmyk values + flags non-CI styles. It does NOT check logo dimensions, alignment, or any M-Basis rule. **No edit required there**. The ISSUE.md framing is misleading — the M-Basis rule lives in `tools/sla_lib/builder/brand_constraints.py` and is already trim-correct.

## 11. Audit runs

- `bin/render-gallery kandidat-falzflyer-din-lang --skip-visual-diff` — regenerates template.sla + page-01.png + page-02.png + preview.pdf + meta.yml SHA. Use this in T10 (artifact regen).
- `bin/audit-alignment kandidat-falzflyer-din-lang` — alignment audit (suggestions for missing CONSTRAINTS).
- `bin/check-stale-previews` — verifies meta.yml `previews_for_sla:` SHA matches current template.sla.

## 12. Top-Band geometry calculation

For 6 panels on A4 quer (297×210), `Polygon` with `y_mm=-3, h_mm=31` gives top-band visible 28mm + 3mm trim-bleed.

Per ISSUE.md ("outer panels P1, P3, P4, P6 get +6mm bleed extension"; per spec text "P1 x=-3 w=105; P2 x=99 w=99; P3 vollflächig"):

| Panel | page | x_mm | w_mm | Right edge | Notes |
|---|---|---|---|---|---|
| P1 | 0 | -3 | 105 | 102 | -3..0 = 3mm trim-bleed (left); 0..99 = panel; 99..102 = 3mm overshoot across fold (intentional — visual continuity) |
| P2 | 0 | 99  | 99  | 198 | flush both folds |
| P3 | 0 | (no separate top-band — `P3 Hintergrund` polygon is already vollflächig at -3..-3, w=102, h=216 covering the whole panel including top-band area) |
| P4 | 1 | -3  | 105 | 102 | mirror of P1 |
| P5 | 1 | 99  | 99  | 198 | mirror of P2 |
| P6 | 1 | (NEW vollflächig polygon analogous to P3 Hintergrund: x=198, y=-3, w=102, h=216, fill=Dunkelgrün — replaces the need for a separate Top-Band) |

So new Polygons added: 4 Top-Bands (P1, P2, P4, P5) + 1 Hintergrund (P6 vollflächig). P3 stays as-is. Plus 1 NEW `P1 Name-Card` (Dunkelgrün vollbleed bottom under Portrait), 1 NEW `P2 Body-Backing` (Hellgrün), 2 NEW `P4 T1-T2 Trenner` (Hellgrün 3mm strips), 2 NEW `P5 T3-T4 Trenner` (Hellgrün 3mm strips). Total NEW polygons in V1: 4 + 1 + 1 + 1 + 2 + 2 = **11 new Polygons**.

The "uniform top-band height" CONSTRAINTS list in ISSUE.md uses 6 anname stubs `p1_top_band` … `p6_top_band`. Reality: for P3 + P6 vollflächig replaces the band — there's NO separate top-band polygon there. The constraint must be adapted: either same_size on `[P1 Top-Band, P2 Top-Band, P4 Top-Band, P5 Top-Band]` (4 polygons; P3 + P6 vollflächig don't have a top-band as a separate primitive), OR introduce explicit small `P3 Top-Band` / `P6 Top-Band` polygons (h=31) on top of the vollflächig backgrounds. **Locked in RESEARCH.md: 4-way same_size on the 4 explicit top-band polygons only; rely on `inside(P3 Top-Title, P3 Hintergrund)` and `inside(P6 Top-Title, P6 Hintergrund-vollflächig)` to anchor P3+P6 visual-band positions.**

## 13. Sample assets final

- `templates/kandidat-falzflyer-din-lang/samples/qr-mitmachen.png` — exists.
- `templates/kandidat-falzflyer-din-lang/samples/qr-termine.png` — exists.
- New mini-labels `"MITMACHEN"` and `"TERMINE"` are TextFrames (not assets) — Bold White 9pt.

## 14. Round-trip safety / structural_check

Current state: 0 errors, 0 warnings, 6 skipped, 19 passes. Goal post-V1: 0 errors, 0 warnings, 1-2 skipped (only `brand:line_spacing_0.9` if narrow-panel rationale still holds; everything else REMOVED), 25+ passes.

## 15. Files touched (inventory)

| File | Reason | Touch type |
|---|---|---|
| `templates/kandidat-falzflyer-din-lang/build.py` | V1 layout + ParaStyle changes + Top-Band/Backing polygons + INJECT_MAP scaffold + CONSTRAINTS rewrite + header-comment fix | major rewrite |
| `templates/kandidat-falzflyer-din-lang/meta.yml` | ci_overrides extend (5 new ParaStyles), brand_overrides cleanup (REMOVE 4 + KEEP 2 with reason update), slots extend, previews_for_sla SHA bump | moderate |
| `templates/kandidat-falzflyer-din-lang/template.sla` | Regen via build.py | regen |
| `templates/kandidat-falzflyer-din-lang/page-01.png` | Regen via render-gallery | regen |
| `templates/kandidat-falzflyer-din-lang/page-02.png` | Regen via render-gallery | regen |
| `templates/kandidat-falzflyer-din-lang/preview.pdf` | Regen | regen |
| `templates/kandidat-falzflyer-din-lang/README.md` | Reference V1 patterns / decisions; document M-Basis comment fix | new content |
| `templates/_specs/kandidat-falzflyer-din-lang.md` | Full V1 rewrite — match V1 layout, ParaStyle table, slot table, constraints prose, layout-philosophie | rewrite |
| `templates/_smoke/test_kandidat_falzflyer_din_lang.py` | Add V1-specific assertions (top-bands present, vollflächig polygons, correct logo asset, P2 logo deleted, etc.) | extend |
| `tools/sla_lib/tests/test_kandidat_falzflyer_geometry.py` | NEW geometry test (≥18 invariants, M-Basis cross-template regression bundled in) | new |
| `templates/kandidat-falzflyer-din-lang/build.py` header-comment | Correct M-Basis annotation (kurze Kante=210, 3M=37.8) | fix in same file |
| `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 | Session-history row | append |
| `improvements/HANDOFF.md` | Mark V1 rollout complete (#15 last item) | append/edit |
| `site/public/kandidat-falzflyer-din-lang/` | Mirror via render-gallery | regen |
| `.issues/<slug>/EXECUTION.md` | Per-task execution log | new |

**Other templates touched (regression check — no code changes expected):**
- `templates/wahlaufruf-postkarte-a6-quer/` — verify `brand:logo_size_3M` PASSes (already does at 18.9mm).
- `templates/wahltag-tueranhaenger/` — verify (already PASSes ×2 at 18.9mm).
- `templates/themen-plakat-a3-quer/` — verify (already PASSes at 53.46mm).
- `templates/infostand-tent-card-a5-quer/` — verify (already PASSes ×2 at 38mm vs 37.8 within tol).

These are READ-ONLY in #21 (verification only, no code changes). The geometry test should include a parametric regression assertion that runs `brand:logo_size_3M` against all 5 V1 templates.

## 16. Pending decisions for RESEARCH.md to lock

1. M-Basis-Konflikt resolution path (above §6, §7).
2. ParaStyle migration strategy (mutate vs parallel) — per ISSUE.md L84: "Add a new `falzflyer/slogan-on-green` (parallel) rather than mutating". For align flips on the 8 existing styles + fcolor flips, MUTATE in place (smaller diff, consistent with #19 precedent). For NEW on-green variants needed alongside existing white/dark variants (slogan-on-green, quote-on-green), CREATE PARALLEL.
3. P3+P6 vollflächig vs explicit Top-Band polygon (above §12).
4. P5 Thema 4 photo — use existing library `themen_wirtschaft_handwerk` directly (above §9). NOT a #13 dependency.
5. Body fontsize Thema 9pt → 10pt (ISSUE.md open Q3) — accept; reduce body text by ~1 line per topic.
6. Impressum on Dunkelgrün at 6pt (ISSUE.md open Q4) — keep at 6pt White; spec says fcolor White on Dunkelgrün. 6pt is print-acceptable for impressum.
7. Spec rewrite vs incremental edit — full rewrite (per #19 precedent).
8. Codex visual review — SKIP (per #20 precedent — single-page-per-side multi-panel template; brand:image_fills_frame + geometry tests + smoke + structural_check are the regression-detection floor).

