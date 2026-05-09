---
id: '17'
title: V1 layout for wahlaufruf-postkarte-a6-quer (Symbol-Tight)
status: done
priority: medium
labels:
- templates
- enhancement
source: github
source_id: 33
source_url: https://github.com/GrueneAT/vorlagen/issues/33
---

# V1 layout for `wahlaufruf-postkarte-a6-quer` — "Symbol-Tight"

## Why

Per `improvements/01-wahlaufruf-postkarte.md` (the design package authored 2026-05-08, full diagnose + 3 variants + per-build-line slot deltas + alignment specs). V1 is the recommended default, lowest aufwand, fixes §4 / §6 / §7 violations without new DSL blocks.

This is the **first** of the five V1 implementations (sequence per #15 tracking issue). Output of this issue establishes the `*-on-green` ParaStyle migration pattern that #18–#21 reuse.

## Scope

Implement V1 "Symbol-Tight" exactly as specified in `improvements/01-wahlaufruf-postkarte.md` §"Variante 1". Key deltas:

**Front:**
- Logo (white): `w 35→18.9, h 10→5.7, local_scale 0.240→0.130` (Print-Soll 3M).
- Wahlkreuz: `w 55→60, h 55→60, x 46.5→44, y 16→18` + new Hellgrün-Halo `Polygon` `x=43, y=17, Ø=62`.
- Delete `Headline-Wahlaufruf` frame; add two new frames: `headline_datum` (Vollkorn Black Italic 26pt Gelb, `x=10 y=82 w=128 h=10`) and `headline_cta` (Gotham Narrow Bold 14pt White CAPS, `x=10 y=92 w=128 h=10`).

**Back:**
- New full-page Polygons: `Dunkelgrün` left half (`x=−3 y=−3 w=93 h=111`) + `White` Impressum-strip (`x=0 y=96 w=148 h=9`).
- Logo: replace asset with `gruene-weiss.png`, place at `x=96 y=8 w=18.9 h=5.7`.
- Delete the 4-Cells loop. Add 3 W-Frage-Blocks (Was/Warum/Wann) at `y=12, 40, 68`, each = headline-yellow + body-white.
- QR: `x 115→96, y 62→30, w 27→36, h 27→36`. New label above (`"WO INFORMIEREN"` 12pt Gotham Bold Dunkelgrün) and URL below (`"gruene-noe.at"` 11pt Gotham Bold Dunkelgrün).
- Impressum: `y 96→101.5, h 6→4, fontsize 6→5`.

**ParaStyles to add / change** (in `templates/wahlaufruf-postkarte-a6-quer/build.py`):
- NEW `wahlaufruf/headline-emphasis` Vollkorn Black Italic 26pt linesp 23 fcolor=Gelb align=1.
- NEW `wahlaufruf/headline-cta` Gotham Narrow Bold 14pt linesp 13 fcolor=White align=1 letter-spacing 0.15em.
- NEW `wahlaufruf/cell-headline-yellow` Vollkorn Black Italic 18pt linesp 16 fcolor=Gelb align=0.
- CHANGE `wahlaufruf/cell-body` `fcolor Black → White` (verify no other template references this style first via `grep -r "wahlaufruf/cell-body" templates/`).

**Alignment / constraints (depends on #14):**

Add a `CONSTRAINTS = [...]` list to `build.py` that encodes the alignment-anchor contracts from `improvements/01-wahlaufruf-postkarte.md` §"Alignment-Beziehungen":

```python
CONSTRAINTS = [
    # Front: Wahlkreuz halo + symbol share center axes
    same_x("wahlkreuz_halo", "wahlkreuz", name="halo_x"),
    same_y("wahlkreuz_halo", "wahlkreuz", name="halo_y"),
    inside("wahlkreuz", "wahlkreuz_halo", name="halo_contains_symbol"),
    # Headline stack vertical hierarchy
    distance_y("headline_datum", "headline_cta", equals=10.0, name="datum_to_cta"),
    # Back: 3 W-Fragen share y-axis baselines (cells column-aligned)
    same_x("frage_was_headline", "frage_warum_headline", "frage_wann_headline",
           name="fragen_left_axis"),
    same_x("frage_was_body", "frage_warum_body", "frage_wann_body",
           name="bodies_left_axis"),
    # QR block: label above, URL below — single-column right axis
    same_x("qr_label", "qr_code", "qr_url", name="qr_axis"),
    # NEW from #14
    aligned_below("qr_code", "qr_label", gap_mm=2.0, name="qr_label_anchors_code"),
    aligned_below("qr_url", "qr_code", gap_mm=4.0, name="qr_url_below_code"),
]
```

`inside_page` runs globally via #14 — no per-template declaration needed.

## Acceptance Criteria

- [ ] All build.py edits land in a single commit; commit msg references this issue id.
- [ ] `python3 templates/wahlaufruf-postkarte-a6-quer/build.py` regenerates `template.sla` cleanly.
- [ ] `python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer` reports zero errors, `CONSTRAINTS` list shows all green.
- [ ] `python3 -m sla_lib.builder.structural_check --all` stays green (no regressions on other templates).
- [ ] `tools/check_ci.py` passes (no brand-color or style drift).
- [ ] No reference-SLA exists for this template (per HANDOFF #15 open question 6) — confirm by absence of `meta.yml::previews_for_sla` field; layout changes are free.
- [ ] Update `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 with the Session-History row from `improvements/01-wahlaufruf-postkarte.md` §"Session-History".
- [ ] Mark `improvements/01-wahlaufruf-postkarte.md` §"Session-History" `Resulting issue` with this issue's GitHub URL.

## Out of scope

- V2 "Datum-Banner" (introduces `MagentaBannerStoerer` block) — backlog.
- V3 "Asymmetric Hero" (introduces `YellowUnderline` block) — backlog.
- Sample/photo curation for the new front+back layouts — covered by #13 (sample manifest).
- Pretty-test pixel-diff: rendering + visual review happens in PR review by humans, not by the agent (token-budget constraint from the originating session).

## Dependencies

Blocked by: **#14** (needs `aligned_below`, optionally `inside_page` global sweep).

## Labels

design, layout, wahlaufruf-postkarte, iter-4, v1
