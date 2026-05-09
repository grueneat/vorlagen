---
id: '20'
title: V1 layout for infostand-tent-card-a5-quer (Hero Band)
status: done
priority: medium
labels:
- templates
- enhancement
source: github
source_id: 36
source_url: https://github.com/GrueneAT/vorlagen/issues/36
---

# V1 layout for `infostand-tent-card-a5-quer` — "Hero Band"

## Why

Per `improvements/04-infostand-tent-card.md` §"Variante 1 · Hero Band". Fourth of five V1 implementations. First multi-panel template — establishes the rotation contract reused in #21 (kandidat-falzflyer).

## Scope

Implement V1 "Hero Band" exactly as specified. Highlights:

**Per panel** (Panel A DE + Panel B EN, mirror-pair via 180° rotation around panel-center `(148.5, 52.5)`):

- New `Polygon "Hero-Band Panel A"` `x=-3 y=-3 w=303 h=42 fill=Dunkelgrün` (top-band).
- Logo: asset swap to `gruene-weiss.png`, `x 12→12, y 10→6, w 36→38, h 32→30`.
- Headline: `x 62→55, y 12→9, w 223→230, h 24→18, fontsize 36→26, linesp 40→23.4, fcolor Dunkelgrün→White`.
- New `tent/payoff` ParaStyle (Vollkorn Italic 16pt linesp 14.4 fcolor=Gelb).
- New `Pay-off` TextFrame `"Konkret. Lokal. Jetzt."` at `x=55 y=27 w=230 h=8`.
- New `Polygon "Photo-Backing"` `x=-3 y=39 w=303 h=33 fill=Dunkelgrün` (sichert §7 falls Foto fehlt).
- Photo `Hintergrund-Mitmachen`: `x 12→0, y 44→39, w 44→297, h 33→33` (full-width) + `scale_type=aspect_fill`.
- New `tent/bullet` ParaStyle (Gotham Book 12pt linesp 15.6 fcolor=Black).
- Body bullets: `x 62→12, y 44→78, w 223→130, h 26→16, fontsize 14→12`.
- Delete `CTA Panel A` (Pay-off replaces functional CTA).
- Termine: `x 125→152, y 68→78, w 160→133, h 26→16` (right column, same baseline as bullets).
- New `Polygon "Footer-Strip"` Hellgrün `x=-3 y=95 w=303 h=10`.
- QR: `w 17→8, h 17→8` (footer-tiny) **OR** keep 17 mm and grow footer height — see open question.
- New CTA-Footer text frame `"gruene-noe.at/mitmachen"` Bold White inside footer strip.
- Impressum: `x 35→204, y 96→97, w 257→90, h 4→6, align=2 (right), fcolor White`.

**Panel B (EN)** — applies the **same lokale layout** with Pre-Rotation math (`pre_y = 210 − panel_a_y − h`) wrapped in a single `rotation=180` around `(148.5, 52.5)`.

**Rotation contract** — implement Panel A and Panel B via two builder functions `_panel_de()` and `_panel_en()` in `build.py` that produce identical local primitives, then wrap Panel A in `Group(rotation=180, around=(148.5, 52.5))`. The `Falz` spotcolor layer stays untouched (Brief §5 spot-color fidelity). All edits live on `Hintergrund` / `Bilder` / `Text` layers only.

**CONSTRAINTS** (depends on #14):

```python
CONSTRAINTS = [
    # Hero band fills full panel width
    inside("logo_panel_a", "hero_band_a", name="logo_in_band_a"),
    inside("hero_headline_a", "hero_band_a", name="headline_in_band_a"),
    inside("payoff_a", "hero_band_a", name="payoff_in_band_a"),
    # Photo band aspect contract
    inside("photo_band_a", "photo_backing_a", name="photo_in_backing_a"),
    # Bullets + Termine share top-y (same baseline)
    same_y("bullets_a", "termine_a", name="info_zone_baseline"),
    # Mirror Panel A ↔ Panel B around sheet apex
    mirrored_y("hero_band_a", "hero_band_b", axis_mm=105.0,
               name="hero_band_mirror_at_apex"),
    same_size("hero_band_a", "hero_band_b", name="hero_bands_same"),
    # Style consistency across DE/EN equivalent slots
    same_style("hero_headline_a", "hero_headline_b", name="hero_headline_style"),
    # NEW from #14
    aligned_below("photo_band_a", "hero_band_a", gap_mm=0.0, name="photo_anchored_to_band"),
]
```

## Open questions to resolve in this issue

1. **QR D1-Konformität in 14×14 mm footer** — at QR-v4 (33 modules) → 0.42 mm/module < 0.5 mm minimum. Either grow footer to 18 mm height (QR 16×16 = 0.485 mm, knapp), or reduce to QR-v3 (29 modules) and shorten URL slug. Decide before merge.
2. **CTA-Verlust** — V1 swaps the directive `"Mitmachen — Komm zu uns!"` for the slogan `"Konkret. Lokal. Jetzt."`. Confirm wording with brand stewardship; if the directive must remain, use it as the Pay-off text.
3. **Foto-Aspect of `hintergrund-mitmachen.jpg`** — V1 needs ~9:1 (297×33). Native aspect probably 1.5:1. Either crop the asset or add a new aspect-cropped variant; track in #13.
4. **Falz spot-color layer integrity** — verify by reading the emitted `template.sla` that Polygons added by V1 do not write into the `Falz` LAYER (must stay on `Hintergrund`).

## Acceptance criteria

- [ ] V1 deltas applied; Panel A + Panel B both implemented via the rotation-contract pattern (single source for both).
- [ ] `template.sla` regenerates cleanly.
- [ ] `structural_check` zero errors; all CONSTRAINTS green; mirror_y constraint specifically validates Panel A/B at apex.
- [ ] `--all` stays green.
- [ ] `check_ci.py` passes.
- [ ] `Falz` layer untouched (verified by SLA `LAYER` attribute scan in test).
- [ ] QR module-size decision documented in `templates/infostand-tent-card-a5-quer/README.md`.
- [ ] Brief §10 Session-History row added; .md Session-History `Resulting issue` updated.

## Out of scope

- V2 "Side-By-Side Pillar" (eliminates Termine slot).
- V3 "Pure Type" (foto-loser Backup).
- New asset cropping for `hintergrund-mitmachen.jpg` — covered by #13.

## Dependencies

Blocked by: **#14** and **#17** (ParaStyle pattern), benefits from **#19** (aspect_fill fix already verified).

## Labels

design, layout, infostand-tent-card, iter-4, v1, multi-panel
