---
id: '18'
title: V1 layout for wahltag-tueranhaenger (Composed Hero)
status: done
priority: medium
labels:
- templates
- enhancement
source: github
source_id: 34
source_url: https://github.com/GrueneAT/vorlagen/issues/34
---

# V1 layout for `wahltag-tueranhaenger` — "Composed Hero"

## Why

Per `improvements/02-wahltag-tueranhaenger.md` §"Variante 1". Second of five V1 implementations (sequence per #15). Reuses the `*-on-green` ParaStyle pattern landed in #17, introduces the stat-card pattern that #19 will adopt.

## Scope

Implement V1 "Composed Hero" exactly as specified in `improvements/02-wahltag-tueranhaenger.md` §"Variante 1 · 'Composed Hero'". Highlights:

**Front:**
- Logo (white, top): `w 35→18.9, h 10→5.7, local_scale 0.240→0.130`.
- Brand-Bar height: `22→16` (logo y=5 fits in 14 mm visible band).
- New `Polygon` Hellgrün-Akzent 4 mm under brand-bar (`x=-2 y=14 w=109 h=4`).
- Hellgrün-Band (Wahlkreuz): `y 65→63, h 60→64`.
- Wahlkreuz: `x 27.5→25, y 70→70, w 50→55, h 50→55`.
- Headline-Wahltag: `y 128→138, h 28→32, linesp 30→25.2` (Quickguide-konform 0.9×).
- Sub-Headline: `y 160→176`.
- New `Polygon` Bullets-Card Hellgrün `x=-2 y=192 w=109 h=58`.
- Bullets text frame: `y 175→200, h 60→40, fcolor Black→White`.

**Back:**
- Brand-Bar height: `22→16`.
- Logo (white, back-band): `w 35→18.9, h 10→5.7, local_scale 0.240→0.130`.
- **Delete** `Logo Grüne (Bund-Dunkel, back)` (double-logo elimination).
- New Portrait-Card: `Polygon x=15 y=70 w=75 h=100 fill=Hellgrün`.
- Portrait: `h 85→90`.
- New Visitenkarten-Footer: `Polygon x=-2 y=178 w=109 h=72 fill=Dunkelgrün`.
- Kandidat-Name: `y 168→184, fontsize 14→18, fcolor Dunkelgrün→White`.
- Kandidat-Position: `y 178→196, fcolor Black→White, opacity→85%`.
- Kontakt-URL: `y 200→210, fcolor Dunkelgrün→Gelb`.
- Kontakt-Info: `y 210→218, fcolor Black→White`.
- QR: `x 65→70, y 200→210, w 30→26, h 30→26` + new white backing `Polygon x=68 y=208 w=30 h=30 fill=White`.
- Impressum (back): `y 240→242, fcolor Black→White`.

**ParaStyles:**
- Add `tueranhaenger/body-on-green` (variant of `tueranhaenger/body` with `fcolor=White`).
- Add `tueranhaenger/url-on-green` (Vollkorn Black Italic Gelb 11pt) for footer URL.

**CONSTRAINTS list** (depends on #14) — encode the contracts from §"Alignment-Beziehungen":

```python
CONSTRAINTS = [
    # Front-Back brand-bar mirror pair (same height + logo position)
    same_size("brand_bar_top", "brand_bar_back", axis="h", name="brand_bar_h_pair"),
    same_x("logo_weiss_front", "logo_weiss_back", name="logo_x_mirror"),
    # Stat-cards (back) on shared center axis
    same_x("stat_card_1", "stat_card_2", "stat_card_3", name="stat_cards_axis"),
    # Each stat-card's eyebrow → hero → body share h_center on card center
    same_x("stat_card_1_eyebrow", "stat_card_1_hero", "stat_card_1_body",
           name="stat_card_1_h_center"),
    same_x("stat_card_2_eyebrow", "stat_card_2_hero", "stat_card_2_body",
           name="stat_card_2_h_center"),
    same_x("stat_card_3_eyebrow", "stat_card_3_hero", "stat_card_3_body",
           name="stat_card_3_h_center"),
    # NEW from #14
    aligned_below("kandidat_name", "kandidat_position", gap_mm=12.0,
                  name="name_to_position"),
    aligned_below("kontakt_info", "kontakt_url", gap_mm=8.0,
                  name="url_to_info"),
]
```

## Open questions to resolve in this issue (lifted from .md)

1. **Doppel-Logo back-band** — V1 deletes the second logo. Confirm with brand stewardship before merging — was it deliberate Bund-migration display, or transitional artifact? Default assumption: artifact, deletion stands.
2. **HL/Sub-Gap formula** (`28×2 = 19.8 mm`) clashes with the 250-mm vertical format. V1 uses 50% of the formula gap (Sub-Top y=176 vs. formula-strict y=190). Document this as a *format-pragmatic* exception in the per-template `meta.yml::brand_overrides` with the rule id and reason.
3. **Bullets-Card Hellgrün height (58 mm)** — high ink coverage. If Druck-Kosten-Sensibilität is a current concern, revisit the height down to 38 mm before merge.

## Acceptance Criteria

- [ ] V1 deltas above are applied in `templates/wahltag-tueranhaenger/build.py` in one commit.
- [ ] `python3 templates/wahltag-tueranhaenger/build.py` regenerates `template.sla` cleanly.
- [ ] `python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger` shows zero errors; the CONSTRAINTS list is fully green.
- [ ] `python3 -m sla_lib.builder.structural_check --all` stays green.
- [ ] `tools/check_ci.py` passes.
- [ ] HL/Sub-Gap deviation (50% of formula) is logged as a `meta.yml::brand_overrides` entry referencing rule `brand:hl_sub_gap_2x` with reason "250 mm vertical format constraint — see issue #18".
- [ ] `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 gets the Session-History row from `improvements/02-wahltag-tueranhaenger.md`.
- [ ] `improvements/02-wahltag-tueranhaenger.md` Session-History `Resulting issue` is updated with the GitHub URL.

## Out of scope

- V2 "Vertical Stripe" (90°/270° rotated logos — would need a new `RotatedImageFrame` helper).
- V3 "Manifesto" (introduces `YellowUnderline` block).
- Pretty-test rendering — done in PR review by humans.

## Dependencies

Blocked by: **#14** and **#17** (#17 establishes the `*-on-green` ParaStyle migration template).

## Labels

design, layout, wahltag-tueranhaenger, iter-4, v1
