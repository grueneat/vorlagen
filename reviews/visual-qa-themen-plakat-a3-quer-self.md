# Self-Review (Mini-Gate-3) — themen-plakat-a3-quer

**Date:** 2026-05-07
**Reviewer:** Claude (this session)
**Render:** `templates/themen-plakat-a3-quer/page-01.png` at 100 DPI.
**Compared against:** `templates/postkarte-a6-kampagne/page-01.png`,
`templates/plakat-a1-hochformat/preview.pdf` (no committed page PNG yet),
`templates/zeitung-a4-grun/page-01.png`.

## Iteration 1 — First-pass critique

### What works
- **Vollkorn Black Italic 60 pt Dunkelgrün headline** anchors the layout — strong
  visual presence, exactly the brand-typical typography.
- **3-column grid** reads cleanly, columns visually balanced (124.7 mm each).
- **Color discipline:** Dunkelgrün for headline + sub + Beleg-headlines; Black for
  body; no random colors; no Magenta (deliberate per Spec Brand-Accent omission).
- **Whitespace rhythm:** 28 mm of clear space between Beleg-Body-end (~242 mm) and
  Quelle (270 mm) — the "Atempause" intended in the spec.
- **Source citation present** (Quelle: Statistik Austria…) anchors the credibility.

### What needs fixing
- **No logo:** the spec calls for a top-left Grünen-Logo, but
  `shared/logos/gruene-cmyk.png` doesn't exist in this repo. The build.py
  conditionally skips the logo when the file is missing — render works, but the
  brand-anchor is lost.
- **Flat layout overall:** compared to the Postkarte's Magenta-Stoerer + Wechsel-
  farb-Headline rhythm, this looks more academic-poster than campaign-poster. The
  spec deliberately omits a Magenta accent for argumentative mode — but a thinner
  Dunkelgrün-Akzent-Hairline or a small Brand-Mark could lift the visual energy.

### Comparison to existing baseline
- **Vs Postkarte:** Different category (argument vs campaign) — Postkarte is more
  visually intense; this is more cerebral. Both are on-brand. Themen-Plakat is
  better suited to its use-case (Sachthema Aufhang).
- **Vs Plakat A1:** Themen-Plakat has 3-column body grid which Plakat-A1 lacks. The
  Plakat-A1 has stronger distance-readability (giant Headline). Themen-Plakat has
  better close-reading usability — appropriate for its smaller format.
- **Vs Zeitung:** Themen-Plakat is a single-page version of what would be a
  Zeitung-Innenseite — same body-text style (Gotham Narrow Book 13 pt vs 11 pt),
  same Dunkelgrün-Headline pattern.

### "Where is it BETTER than the existing 3?"
- **Argument structure:** the These → Belege → Quelle pattern is **explicitly
  called out** as a teaching tool for Bezirksgruppen. The existing 3 templates all
  have implicit structures (Postkarte = Hauptbotschaft; Plakat = Veranstaltung;
  Zeitung = News-Mix). Themen-Plakat is the first template with a **didactic
  structure** that authors can replicate.
- **Source-citation discipline:** explicit Quelle slot teaches authors to cite.
- **Whitespace:** more breathing room than Zeitung 3-column layouts; similar
  density to Plakat A1 but with more semantic structure.

### Iteration 2 fix candidates (deferred to Gate 3)
1. Add a Dunkelgrün hairline (1 pt rule) above the 3 columns at y=125 to visually
   separate Sub-Headline from Belege.
2. Add a Magenta dot/accent next to the Quelle to anchor the bottom — small Brand
   moment without breaking the argument-mode aesthetic.
3. If `shared/logos/gruene-cmyk.png` becomes available, conditionally re-render.

## Decision

**Iteration 1: PASS** for now. The render is on-brand, hierarchy is clear,
typography uses the right Vollkorn-Black-Italic + Gotham-Narrow stack. The flatness
concern is documented for Gate-3 attention but is not blocking — the spec's
"argumentative mode without Stoerer" is a deliberate decision.

Next template (Wahlaufruf-Postkarte A6 quer) will inherit the calibration findings:
- Use `style=` AND `paragraph_style=` on every TextFrame
- Verify rendering with full color/font check before committing artifacts
- Commit page-01.png + preview.pdf + meta.yml SHA pin together.
