---
id: '15'
title: 'Tracking: Layout-Improvements V1 rollout for 5 new templates'
status: open
priority: medium
labels:
- templates
- documentation
source: github
source_id: 31
source_url: https://github.com/GrueneAT/vorlagen/issues/31
---

# Tracking: Layout-Improvements V1 rollout for 5 new templates

## Why

Pattern-B audit (Brief §7B) of the five new templates shipped in Iter-3 (`improvements/HANDOFF.md`) surfaces three systemic violations across the suite plus per-template layout-quality bugs. Three Layout-variants per template were drafted (V1 strict / V2 mutig / V3 typografisch). **V1 is the recommended default for all five.** This issue tracks the rollout; per-template implementation issues are #17–#21.

## Three systemic findings (all five templates affected)

1. **§7-Verletzung "Typografie immer auf Grün"** — body text on white in 4/5 templates. Fix: light-green body backings as ParaStyle siblings.
2. **Logo-Drift gegen `3 × M` Print-Soll** — every logo is under-spec, some by >50%. Fix: frame resize on computed Print-Soll, asset swap to white-on-green where needed.
3. **HL/Sub-Gap-Formel `× 2` verletzt** — every template runs 70-95 % too tight. Fix: y-coord adjustment using formula-derived gap (`HL.fontsize × 2 × 0.353 mm/pt`).

## V1 rollout sequence (per HANDOFF §"Empfehlungs-Reihenfolge")

| Order | Template | Issue | Variant | Why this order |
|:---:|---|---|---|---|
| 1 | `wahlaufruf-postkarte-a6-quer` | #17 | "Symbol-Tight" | Smallest template, establishes the `*-on-green` ParaStyle migration that all four others reuse |
| 2 | `wahltag-tueranhaenger` | #18 | "Composed Hero" | Same A6 family, stat-card pattern is reused in #19 |
| 3 | `themen-plakat-a3-quer` | #19 | "Evidence Cards" | A3 standalone, photo-aspect-fill fix becomes the reference for #20 + #21 |
| 4 | `infostand-tent-card-a5-quer` | #20 | "Hero Band" | First multi-panel geometry, rotation contract for Panel A pattern reused in #21 |
| 5 | `kandidat-falzflyer-din-lang` | #21 | "Falz-Rhythm" | Most complex (6 panels, ~25 slots), benefits from every pattern landed in #17–#20 |

## V2 / V3 disposition

V2 + V3 of every template stay as alternative editions in `improvements/0X-*.md` and are **not turned into separate issues** in this rollout. Reasons:

- V1 cleans up §4/§6/§7 violations and the format-layout bugs that motivated the audit. V2/V3 add design *flavor* (Magenta-Banner-Störer, vertical stripe, manifesto typography) without fixing additional brand violations.
- New DSL blocks (`MagentaBannerStoerer`, `YellowUnderline`, rotated logo blocks) are introduced by V2/V3 but not load-bearing for compliance — premature to add until a Bezirksgruppe asks for the variant.
- Re-opening V2/V3 later costs only one new issue per chosen variant, with the .md file already drafted.

## Open questions to clear before starting #17–#21

(Lifted from HANDOFF §"Open Questions / Risks" — owner: this issue, not the per-template ones.)

1. **`kandidat-falzflyer` M-Basis-Konflikt** — Build-Code-Comment uses `kurze Kante=105` (panel width) → 18.9 mm Logo-Soll. Quickguide uses Trim-kurze-Kante=210 → 37.8 mm. Recommendation: Trim-konsistent. `check_ci.py` must enforce. **Decide before #21.**
2. **`infostand-tent-card` Falz-Spotcolor** — V1 dark-green hero band at apex; must not touch the spot-color `Falz` layer. Confirm V1 builder writes only to `Hintergrund`.
3. **`wahltag-tueranhaenger` Stanzkontur layer** — same question for the hanger-cutout spot layer.
4. **Asset gap** — `samples/themen-wirtschaft.jpg` for Falzflyer P5 Thema 4 missing; track in #13 (sample-manifest with Codex-prompts), do not block #21 — empty-slot conditional remains.
5. **ParaStyle migration policy** — V1 adds 1-3 new `*-on-green` styles per template. Recommendation: add new + mark old `deprecated`, remove in Iter-5. Confirm.
6. **Diff-Stabilität gegen Reference-SLAs** — only the 3 production templates have committed Reference-SLAs (postkarte-a6-kampagne, plakat-a1-hochformat, zeitung-a4-grun); the 5 new templates here have none → layout changes are free. Confirm.

## Acceptance criteria

- [ ] Open questions 1-6 above are answered (in this issue's comments) before any of #17–#21 enter `/issue:execute`.
- [ ] All five #17–#21 issues are merged with green `tools/spec_check.py`, `tools/check_ci.py`, and `python3 -m sla_lib.builder.structural_check --all`.
- [ ] `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 has one Session-History row per implemented template (lifted from each .md's §"Session-History").
- [ ] HANDOFF.md is updated after each per-template merge with the resulting GitHub issue link.

## Out of scope

- V2/V3 implementations (deferred — separate issues if/when requested).
- New DSL blocks not load-bearing for V1 (`MagentaBannerStoerer`, `YellowUnderline`, etc.).
- The Zeitung overflow fix (#16) and the constraint-system extension (#14) — separate concerns, listed only as dependencies.

## Dependencies

Blocks: nothing (tracking issue). Blocked by: #14 (constraint DSL) for the per-template constraint additions, then #17–#21 sequentially.

## Labels

tracking, design, layout, iter-4
