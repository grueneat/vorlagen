---
id: '19'
title: V1 layout for themen-plakat-a3-quer (Evidence Cards)
status: done
priority: medium
labels:
- templates
- enhancement
source: github
source_id: 35
source_url: https://github.com/GrueneAT/vorlagen/issues/35
---

# V1 layout for `themen-plakat-a3-quer` — "Evidence Cards"

## Why

Per `improvements/03-themen-plakat.md` §"Variante 1 · Evidence Cards". Third of five V1 implementations. Fixes the half-leer hero photo, lifts the body off white, gives the three Belege real visual weight.

## Scope

Implement V1 "Evidence Cards" exactly as specified in `improvements/03-themen-plakat.md` §"Variante 1". Highlights:

- Logo: `w 32→54, h 28→48` (Print-Soll 3M = 53.5 mm on A3).
- Headline These: `x 15→235, y 40→70, w 390→170, h 50→100, fontsize 60→52, linesp 64→46.8` (60/40 right-half placement).
- Sub-Headline: `x 15→235, y 92→172, w 390→170`.
- New Hellgrün Hero-Foto-Card backing `Polygon x=15 y=70 w=200 h=120`.
- Themen-Hero photo: `x 120→18, y 225→73, w 180→194, h 60→114` + `scale_type=aspect_fill` to fix the today-half-leer rendering.
- Three Beleg-cards: each with new Hellgrün backing `Polygon x=col_x y=210 w=124.67 h=72`.
- Beleg-Stat hero (NEW frames): Vollkorn Black Italic 56pt Gelb at `x=col_x+5 y=215 w=114 h=24`.
- Beleg-Headlines (existing): replaced by stat-hero — frames deleted.
- Beleg-Labels (NEW): caps Bold Gelb 18pt at `x=col_x+5 y=242 w=114 h=8`.
- Beleg-Bodies: style `beleg-body → beleg-body-on-green`, `y 152→252, h 70→26`, fcolor White.
- QR: `w 25→35, h 25→35, x 380→370`.
- Quelle: `w 80→200`.

**ParaStyles:**
- NEW `themen-plakat/stat-hero` Vollkorn Black Italic 56pt linesp 50.4 fcolor=Gelb align=0.
- NEW `themen-plakat/beleg-body-on-green` Gotham Narrow Book 13pt linesp 16.9 fcolor=White align=0.
- NEW `themen-plakat/beleg-headline-yellow` Gotham Narrow Bold 18pt linesp 16.2 fcolor=Gelb CAPS letter-spacing 0.04em.
- CHANGE `themen-plakat/headline` linesp `64→54` (formula-konform).
- Existing `themen-plakat/beleg-body` `align=0 → align=1` per .md §"Alignment-Spezifikation" (cards center-aligned).

**CONSTRAINTS extension** (the existing list already has `same_y`, `distance_y`, `same_style`):

```python
# Add to existing CONSTRAINTS:
same_x("Beleg 1 — Card", "Beleg 1 — Stat", "Beleg 1 — Label", "Beleg 1 — Body",
       name="beleg1_card_v_axis"),
same_x("Beleg 2 — Card", "Beleg 2 — Stat", "Beleg 2 — Label", "Beleg 2 — Body",
       name="beleg2_card_v_axis"),
same_x("Beleg 3 — Card", "Beleg 3 — Stat", "Beleg 3 — Label", "Beleg 3 — Body",
       name="beleg3_card_v_axis"),
inside("Beleg 1 — Stat",   "Beleg 1 — Card", name="b1_stat_in_card"),
inside("Beleg 1 — Label",  "Beleg 1 — Card", name="b1_label_in_card"),
inside("Beleg 1 — Body",   "Beleg 1 — Card", name="b1_body_in_card"),
# (repeat for cards 2 + 3)
mirrored_x("Beleg 1 — Card", "Beleg 3 — Card", axis_mm=210.0,
           name="cards_mirror_around_page_center"),
# NEW from #14
aligned_below("Themen-Hero", "Sub-Headline", gap_mm=8.0,
              name="hero_anchored_to_subhead"),
```

## Open questions to resolve in this issue

1. **`scale_type=aspect_fill` vs. `ratio=1`** for `Themen-Hero` — current `ratio=1` is the cause of "halb-leerer Frame" today. Confirm `aspect_fill` is the right semantic in `sla_lib.builder.primitives.ImageFrame`. If it isn't already supported, add it.
2. **Stat-Zahlen as new Headline-Inhalt** — V1 replaces "12 700 grüne Jobs" headline with a big number + caps label. Requires content-discipline from Bezirksgruppen. Not blocking implementation, but flag in `templates/themen-plakat-a3-quer/README.md`.
3. **HL/Sub-Gap formula** (`60×2 = 42 mm`) is intentionally violated by the 60/40 split layout. Add `meta.yml::brand_overrides` with reason "60/40 column-split layout — gap unfolds across columns, not lines".

## Acceptance Criteria

- [ ] V1 deltas applied in `templates/themen-plakat-a3-quer/build.py` in one commit.
- [ ] `build.py` regenerates `template.sla` cleanly.
- [ ] `structural_check` zero errors, all CONSTRAINTS green (existing + new).
- [ ] `--all` stays green.
- [ ] `check_ci.py` passes.
- [ ] `aspect_fill` works on `Themen-Hero` — verified by reading the emitted `template.sla` and confirming the right Scribus `SCALETYPE`/`SCALE` attributes (no PNG inspection).
- [ ] HL/Sub-Gap exception logged as `brand_overrides` entry.
- [ ] Brief §10 gets the Session-History row.

## Out of scope

- V2 "Hero Photo Plakat" (full-bleed photo half).
- V3 "Argument Stack" (foto-loses Backup with horizontal Bänder).

## Dependencies

Blocked by: **#14** and **#17** (ParaStyle migration template).

## Labels

design, layout, themen-plakat, iter-4, v1
