# Gate 3 — Visual QA: themen-plakat-a3-quer

**Date:** 2026-05-07
**Render:** `templates/themen-plakat-a3-quer/page-01.png` at 100 DPI (post-logo-fix).
**Iterations:** 2 (iter-1 build pass without logo, iter-2 with logo embedded).

## Iter-1 → Iter-2 vorher/nachher

| | Iter-1 | Iter-2 |
|---|---|---|
| Logo | none (placeholder skipped) | DIE GRÜNEN green-on-white top-left |
| Headline | Vollkorn 60pt Dunkelgrün | unchanged |
| Body | Gotham Book 13pt Black | unchanged |

## Final State

- **merge_ready: yes** (all reviewers reach consensus per Claude+Codex synthesis).
- **comparison_to_existing:** Themen-Plakat occupies a different category than the
  existing 3 (argument vs campaign). Within its category, the typography (Vollkorn 60pt
  Dunkelgrün headline + Gotham 13pt body) is brand-consistent and the 3-column grid is
  cleaner than what the Zeitung achieves on a single page. **Better than the existing
  3 for Sachthemen-Aufhang** because the existing 3 have no didactic structure.
- **hierarchy_readability:** 1-second test passes — "Klimaschutz ist Wirtschaftspolitik"
  reads instantly, supported by 3 evidence headlines.
- **brand_consistency:** Pass. Dunkelgrün + Gotham + Vollkorn = Grünen NÖ feel.
- **print_risks:** None — 12mm margins clear, Quelle and Impressum bottom strip clear.
- **wahlkreuz_background_color_check:** N/A (no Wahlkreuz on this template).

## Where it's better than the existing 3

The Themen-Plakat is the **first template with explicit argumentation structure** —
These → Belege → Quelle. The existing 3 templates carry implicit structures (Postkarte =
Hauptbotschaft + Stoerer; Plakat = Veranstaltung; Zeitung = News-Mix). Themen-Plakat
teaches authors to argue with sourced evidence — a didactic value the existing 3 lack.

## Three concrete improvements (deferred)

1. Replace placeholder logo with brand-quality vector logo (out of scope for this issue).
2. Consider a Hellgrün hairline (1pt) above the 3 columns at y=125 to visually
   separate Sub-Headline from Belege.
3. Add a Magenta dot or thin vertical accent next to the Quelle to balance the bottom
   visually.

**Final consensus:** merge-ready as the calibration template. The argument-mode design
is intentional and lands. Logo placeholder is acceptable for ship; brand-quality logo
swap is out of scope.
