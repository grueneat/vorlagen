---
id: '21'
title: V1 layout for kandidat-falzflyer-din-lang (Falz-Rhythm) + M-Basis fix
status: open
priority: medium
labels:
- templates
- enhancement
- migration
source: github
source_id: 37
source_url: https://github.com/GrueneAT/vorlagen/issues/37
---

# V1 layout for `kandidat-falzflyer-din-lang` — "Falz-Rhythm"

## Why

Per `improvements/05-kandidat-falzflyer.md` §"Variante 1 · Falz-Rhythm". Fifth and most complex V1 (6 panels, ~25 slots, 11 ParaStyles). Profits from every pattern landed in #17–#20.

## Scope

Implement V1 "Falz-Rhythm" exactly per the .md. Highlights:

**Universal Top-Band (all 6 panels):**
- `Polygon` 31 mm Dunkelgrün at top of each panel; outer panels (P1, P3, P4, P6) get +6 mm bleed extension.
- Logo (white, P1 + P6 only — full Print-Soll 38×22 mm).
- `top_title` text frames on P2/P3/P4/P5: Caps Bold White 11pt — `"Kandidatin"`, `"Mein Plan"`, `"Wahltag"`, `"Themen 1·2"`, `"Themen 3·4"`.

**Front:**
- P1 cover: Portrait `y 28→34, h 105→100`; new `Polygon "Name-Card"` Dunkelgrün vollbleed bottom; Name + Slogan on green (fcolor `White` / `Gelb`).
- P2 Mein Plan: delete kleines Logo (Top-Band ersetzt); Headline `y 20→38`; new `Polygon "Body-Backing"` Hellgrün; Body fcolor `Black→White`.
- P3 Wahltag: Wahlkreuz `y 30→44`; Closer-Headline `y 90→100`; Datum-Akzent `y 125→145` (gap closer to formula `22×2 ≈ 15 mm`); URL `y 175→185`; new `top_title` `"Wahltag"` Bold Gelb.

**Back:**
- P4 + P5 Themen: photos `h 24→44` (closer to native 1.5:1 aspect, fixes today's halb-leer Streifen); Hellgrün-3 mm-Trenner between Thema A and B.
- P5 Thema 4 gets a photo (asset `samples/themen-wirtschaft.jpg` — flag for #13).
- P4 Thema 2 Body deleted (headline + photo carries the message; tiefe via QR).
- P6 Kontakt: vollflächig Dunkelgrün; Headline `y 20→38, fcolor White`; Adresse + Email + Telefon + Sprechtag in 2-Spalten-Layout symmetrisch um `AXIS_P6_CENTER_X = 247.5`; QRs `30→24 mm` with new mini-labels `"MITMACHEN"` / `"TERMINE"`; Logo (white) `38×34` at footer; Impressum `h 60→8, fcolor White`.

**ParaStyles:** flip 9 styles from `align=0` → `align=1` (Cover-Name, Slogan, Contact-Headline/Label/Body, Themen-Body, Closer-Headline, URL); add NEW `falzflyer/quote-on-green` (`align=1`, Vollkorn Italic White on Hellgrün/Dunkelgrün). Keep `falzflyer/themen-eyebrow`, `falzflyer/themen-headline`, `falzflyer/teaser-body` at `align=0` (eyebrow/redaktioneller Charakter).

**CONSTRAINTS** (depends on #14):

```python
CONSTRAINTS = [
    # All 6 top-bands share height (uniform Falz-rhythm)
    same_size("p1_top_band", "p2_top_band", "p3_top_band",
              "p4_top_band", "p5_top_band", "p6_top_band",
              axis="h", name="top_bands_h"),
    # Mirror pair: Cover (P1) ↔ Kontakt (P6) — "grüne Klammer"
    same_size("p1_full_bg", "p6_full_bg", name="cover_kontakt_pair"),
    # P4/P5 Themen-Sub-Layouts — mirror_pair between thema_a and thema_b
    same_x("p4_thema_a_eyebrow", "p4_thema_b_eyebrow", name="p4_thema_x_axis"),
    same_x("p4_thema_a_headline", "p4_thema_b_headline", name="p4_thema_hl_axis"),
    same_size("p4_thema_a_photo", "p4_thema_b_photo", name="p4_photos_size"),
    # (repeat for P5)
    # P6 col_left / col_right symmetric around panel center
    mirrored_x("p6_col_left_adresse", "p6_col_right_telefon",
               axis_mm=247.5, name="p6_columns_mirror"),
    mirrored_x("p6_col_left_email", "p6_col_right_sprechtag",
               axis_mm=247.5, name="p6_columns_mirror_2"),
    same_y("p6_col_left_adresse", "p6_col_right_telefon", name="p6_baseline_1"),
    same_y("p6_col_left_email", "p6_col_right_sprechtag", name="p6_baseline_2"),
    # Logo Print-Soll consistency on P1 + P6
    same_size("p1_logo_weiss", "p6_logo_weiss_footer", name="logos_print_soll"),
    # NEW from #14 — image-aligned-to-text
    aligned_below("p4_thema_a_photo", "p4_thema_a_headline", gap_mm=4.0,
                  name="p4_a_photo_anchored"),
    aligned_below("p5_thema_c_photo", "p5_thema_c_headline", gap_mm=4.0,
                  name="p5_c_photo_anchored"),
]
```

## Open question — must resolve before this issue starts

**M-Basis-Konflikt** (per HANDOFF #15 Open Question 1, this issue's owner):
- Build-Code-Comment uses `kurze Kante=105` (panel width) → 18.9 mm Logo-Soll, today's 20 mm = "within tolerance".
- Quickguide uses `Trim-kurze-Kante=210` → 37.8 mm Soll, today's 20 mm = 53% of soll.
- **Recommendation: Trim-konsistent.** Update `templates/kandidat-falzflyer-din-lang/build.py` Header-Comment to clarify, update `tools/check_ci.py` to enforce M = `0.06 × min(trim_w, trim_h)`. The check must agree with the Quickguide on every existing template before this issue's V1 changes land — verify zero new Logo-violations on `wahlaufruf-postkarte`, `wahltag-tueranhaenger`, `themen-plakat`, `infostand-tent-card`. If the rule change introduces violations on those four (i.e. their logos were also under the Trim-M soll and we missed them in #17–#20), this issue is the place to fix that.

## Other open questions

- **Slogan-on-Green ParaStyle** — V1 needs `falzflyer/slogan` `fcolor` to switch from `Black` to `Gelb` for the on-green name-card placement. Add a new `falzflyer/slogan-on-green` (parallel) rather than mutating the existing style — preserves diff stability.
- **Sample asset `themen-wirtschaft.jpg`** — pre-condition for P5 Thema 4 photo. Track in #13. While missing, P5 Thema 4 keeps the empty-slot conditional as today.
- **Body-Schriftgröße auf Themen-Panelen** — V1 raises body from 9pt to 10pt (1 line shorter per topic). Confirm content-discipline can accommodate.
- **P6 Impressum on Dunkelgrün at 6pt** — readability check; 7pt may be required. Decide via test print or by reading the emitted `template.sla` for the actual rendered fontsize/fcolor combo.

## Acceptance criteria

- [ ] M-Basis-Konflikt is resolved (decision documented; `check_ci.py` updated; spot-checked against #17–#20 templates).
- [ ] All V1 deltas applied in `build.py` in atomic commits (header-comment + ParaStyle changes + per-panel slot changes can be 3-4 commits if it improves reviewability).
- [ ] `template.sla` regenerates cleanly.
- [ ] `structural_check` zero errors; all CONSTRAINTS green.
- [ ] `--all` stays green; the four other templates' Logo-checks stay green under the new M-Basis rule.
- [ ] `check_ci.py` passes with the new M = Trim rule.
- [ ] Brief §10 Session-History row added; .md Session-History `Resulting issue` updated.
- [ ] HANDOFF.md V1 rollout sequence (#15) marked complete after merge.

## Out of scope

- V2 "Cover Hero" (vollbleed Portrait — risky if Portrait quality is weak).
- V3 "Editorial Stripe" (5-mm-Akzent-Streifen).
- Asset creation `themen-wirtschaft.jpg` — covered by #13.

## Dependencies

Blocked by: **#14** (`aligned_below`), **#17** (ParaStyle migration template), **#20** (multi-panel rotation contract). Recommended order is "last in V1 series" to absorb the patterns from the earlier four.

## Labels

design, layout, kandidat-falzflyer, iter-4, v1, multi-panel, m-basis-fix
