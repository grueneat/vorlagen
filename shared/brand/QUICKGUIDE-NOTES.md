# Die Grünen — CD Quickguide Notes

Repo-internal summary of `shared/brand/CD-Quickguide.pdf` (DIE GRÜNEN
Corporate Design Quickstart, Adobe InDesign 21.2 export from 2026-03-13,
2 A4 pages, ~566 KB). The PDF is the canonical source — this Markdown
is a cross-referenceable digest for build.py authors and reviewers.

## Farben

The four brand colors with all values (Digital RGB+HEX, Print CMYK+Pantone).
**Cross-check vs `shared/ci.yml`:** all CMYK values match — no drift. The
RGB/HEX/Pantone values are NOT yet in `ci.yml` (DSL is print-first;
digital values are documented here for future digital-asset work).

| Name        | Role            | RGB         | HEX     | CMYK         | Pantone | `ci.yml`             |
|-------------|-----------------|-------------|---------|--------------|---------|----------------------|
| Dunkelgrün  | brand-primary   | 37/118/57   | #257639 | 85/35/95/10  | 2465 C  | match                |
| Hellgrün    | brand-secondary | 86/175/49   | #56af31 | 69/0/100/0   | 3501 C  | match                |
| Gelb        | brand-accent    | 255/240/0   | #ffed00 | 0/0/100/0    | 102 C   | match                |
| Magenta     | brand-stoerer   | 225/0/120   | #e6007e | 0/100/0/0    | 225 C   | match                |

`ci.yml` additionally defines `Black`, `White`, `Registration` — these are
non-brand utility colors and not part of the Quickguide's chromatic palette.

## Schriften

Three faces, one role each. **Cross-check vs `shared/ci.yml::fonts`:**
`Gotham Narrow Ultra`, `Gotham Narrow Book`, and `Vollkorn Black Italic`
are all listed. `ci.yml` additionally lists `Gotham Narrow Bold` and
`Gotham Narrow Black` — these are not in the Quickguide's three-face
core but are valid weight-pair extensions used for sub-headlines and
CTAs in our templates.

| Face                  | Role per Quickguide                       |
|-----------------------|-------------------------------------------|
| Gotham Narrow Ultra   | Headlines                                 |
| Gotham Narrow Book    | Sublines, Copytexte (body)                |
| Vollkorn Black Italic | Hervorhebungen in Headlines und Zitate    |

**Weight-pairing (per Quickguide layout examples):**

- Headline (Gotham Ultra) + emphasis word (Vollkorn Black Italic) on
  separate line. Yellow underline or Yellow circle accents the emphasis
  (see Gestaltungselemente).
- Subline (Gotham Book) directly below headline.
- Copytext (Gotham Book) below subline.

Repo extension: `Gotham Narrow Bold` is the canonical sub-headline /
CTA face for templates that need a weight between Book and Ultra
(e.g. `tueranhaenger/sub`, `tueranhaenger/url`, `ci/cta`).

## Schriftgrundlagen

Hard typography rules — these are formulas, not preferences. `X` denotes
the headline font size in pt.

| Rule                         | Formula                                      |
|------------------------------|----------------------------------------------|
| Headline-Zeilenabstand       | `linesp = Schriftgröße × 0.9`                |
| HL → SL Abstand (vertikal)   | `gap = X × 2`                                |
| HL → Copy Abstand (vertikal) | `gap = X × 2`                                |
| Fließtext Größe              | format-bound (Quickguide refers to `Tabelle S. 38` of the full CI manual; not in this 2-page Quickstart) |
| Fließtext Zeilenabstand (ZA) | `linesp = Schriftgröße × 1.3`                |

**Worked example.** A 28 pt Headline (Vollkorn Italic) at our Türanhänger:

- Headline-Zeilenabstand: `28 × 0.9 = 25.2 pt` (rounded to ~25–26 pt).
  Our build sets `linesp=30` (loose). **Drift flag — could tighten.**
- HL → SL gap: `28 × 2 = 56 pt ≈ 19.8 mm`. Our build positions Sub at
  y=160 mm under Headline at y=128 mm/h=28 mm → gap = 160 − 156 = 4 mm
  baseline-to-baseline. **Drift flag — sub is much closer than Quickguide
  suggests.** May be intentional for the narrow Türanhänger column.
- Fließtext (11 pt body): `linesp = 11 × 1.3 = 14.3 pt`. Our build sets
  `linesp=14` (Türanhänger body) — match within 0.3 pt. ✓

## Mindestabstände + Logogrößen

`M` is the universal protective margin. Always derived from the **kurze
Kante** (shorter side of the trim).

| Rule              | Formula                                |
|-------------------|----------------------------------------|
| Mindestabstand M  | `M = 0.06 × kurze_kante`               |
| Logo (Print)      | `Logo-Breite = 3 × M`                  |
| Logo (Digital)    | `Logo-Breite = 2.5 × M`                |
| Logo-Schutzzone   | `≥ M` clear of Logo (no element inside)|

**Pro-Format-Tabelle** (computed from current trim sizes):

| Template                          | Trim (mm)   | kurze Kante | M (mm) | Logo Print 3M (mm) | Logo Digital 2.5M (mm) |
|-----------------------------------|-------------|-------------|--------|--------------------|------------------------|
| postkarte-a6-kampagne (A6)        | 105 × 148   | 105         | 6.30   | 18.90              | 15.75                  |
| wahlaufruf-postkarte-a6-quer (A6) | 148 × 105   | 105         | 6.30   | 18.90              | 15.75                  |
| infostand-tent-card-a5-quer       | 297 × 210   | 210         | 12.60  | 37.80              | 31.50                  |
| kandidat-falzflyer-din-lang       | 297 × 210   | 210         | 12.60  | 37.80              | 31.50                  |
| wahltag-tueranhaenger             | 105 × 250   | 105         | 6.30   | 18.90              | 15.75                  |
| themen-plakat-a3-quer (A3 quer)   | 420 × 297   | 297         | 17.82  | 53.46              | 44.55                  |
| plakat-a1-hochformat (A1)         | 594 × 841   | 594         | 35.64  | 106.92             | 89.10                  |
| zeitung-a4-grun (A4)              | 210 × 297   | 210         | 12.60  | 37.80              | 31.50                  |

**Drift flags** (per build.py inspection — for the new bund-dunkel logo
audit in Delivery B):

- `wahltag-tueranhaenger` front Logo: 35×10 mm (target 18.9 mm Print).
  Currently ~85 % too wide. Falls in legacy "weiss" zone — re-evaluate
  after bund-dunkel migration.
- `kandidat-falzflyer` Cover Panel Logo: 35×10 mm (target 37.8 mm Print).
  ~7.4 % under, within 15 % tolerance. ✓
- `themen-plakat-a3-quer` top Logo: 60×18 mm (target 53.5 mm Print).
  ~12 % over, within 15 % tolerance. ✓
- `infostand-tent-card-a5-quer` panel Logos: 45×14 mm (target 37.8 mm).
  ~19 % over — **over the 15 % tolerance**, candidate for adjustment.
- `wahlaufruf-postkarte-a6-quer` Logo (back): 30×9 mm (target 18.9 mm).
  ~58 % over — **clearly over tolerance**, candidate for adjustment.
  The white front logo at 35×10 mm is also over (matches existing
  postkarte-a6-kampagne; legacy convention).

The Quickguide allows reduced "Digital" sizing (`2.5 × M`) — these
templates are print-deliverable PDFs so the Print rule (`3 × M`) applies.

## Layout-Grundprinzipien

**Zentrale Regel:** *"Typografie steht immer in Kombination mit Grün."*

Concrete enforcement:

1. Text is placed exclusively on a green Farbfläche (Dunkelgrün or
   Hellgrün). White or photo backgrounds are NOT valid for headline /
   subline / copytext placements — those must sit on a green panel.
2. Text on a person (photo) is allowed only if the person clearly
   stands against green: either freistellung (cutout) onto a green
   Farbfläche, or photographed in front of a green background.
3. Sujets können photo- oder Farbfläche-basiert sein — but rule (1) is
   independent of which.

This is the most prescriptive rule in the Quickguide and the one most
likely to be silently violated by builds that put copytext directly on
white card stock. **All 8 of our templates need an audit pass against
this rule** (see Per-Template-Anwendung below).

## Gestaltungselemente

Two yellow accent patterns highlighted in the Quickguide:

1. **Gelbe Unterstreichung** under a key word in the Headline (the
   "ist eine" example shows a yellow swoosh under "Headline").
2. **Gelber Kreis um ein Wort** in the Headline (the example shows a
   yellow oval drawn around "Das" with Vollkorn Italic emphasis on the
   adjacent word).

Both use **Gelb** (`0/0/100/0` CMYK / `#ffed00`) as the accent color.
The yellow circle pattern is currently NOT used in any of our 8 builds —
candidate Gestaltungselement for future iterations.

## Störer-Patterns

Three Magenta (`brand-stoerer`) störer types shown:

1. **Magenta-Kreis-Störer** (round) — small circle ø ~25 mm with
   `Hier steht ein Störer.` in Gotham Narrow Ultra, white fcolor,
   center-aligned. Used as a callout overlay on layouts.
2. **Magenta-Kreis-Störer (variant)** — same form, different word break;
   visual rhythm element.
3. **Magenta-Banner-Störer** with date + Wahlkreuz-im-Datum:
   `31.8. ✗ Grün` — Magenta tilted-banner shape, white Gotham Ultra
   text, the **Wahlkreuz** glyph (Yellow ✗ in Yellow circle) inserted
   inline between the date and the slogan. This combines our existing
   `shared/assets/wahlkreuz.png` (and EPS source) with a Magenta
   banner background.

Repo notes:

- The Magenta-Kreis-Störer is NOT yet implemented as a `shared/blocks/`
  primitive. Candidate refactor.
- The Magenta-Banner-Störer with Wahlkreuz reuses the existing Wahlkreuz
  asset already present at `shared/assets/wahlkreuz.png`.
- `wahltag-tueranhaenger` already uses the Wahlkreuz asset (large hero
  on Hellgrün band, p1 of front) — that is the Wahlkreuz alone, NOT the
  magenta-banner-with-date variant.
- No existing template uses a Störer overlay yet. The Quickguide
  explicitly shows the Störer as an **optional** layout element, so
  absence is correct, not a gap.

## Per-Template-Anwendung

Quick map of which Quickguide rules each of the 8 templates must honor
and where the current build may be at risk. "Risk" entries are
candidates for follow-up issues, not iter-3 blockers (out of scope per
Delivery A's note-only mandate).

| Template                          | Honors                                                                      | Risk                                                                                               |
|-----------------------------------|-----------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| postkarte-a6-kampagne             | Farben (Dunkelgrün), Schriften (Gotham Bold/Ultra), text-on-green ✓         | Logo size 18.9 mm target — currently within range                                                  |
| plakat-a1-hochformat              | Farben (Dunkelgrün/Hellgrün), Schriften, text-on-green ✓                    | Logo top-right 200 mm wide vs target 106.9 mm Print — legacy "Plakat-Hero" convention             |
| zeitung-a4-grun                   | Farben, Schriften ✓                                                         | Body text frequently sits on white newsprint — violates "Typografie steht immer mit Grün" rule. Legacy production template; out-of-scope |
| kandidat-falzflyer-din-lang       | Farben, Schriften, Cover (Dunkelgrün) text-on-green ✓                       | P4/P5 Themen panels mix copytext on white — partial violation. Logo size within tolerance        |
| infostand-tent-card-a5-quer       | Farben, Schriften ✓                                                         | Panel logos 19 % over Print target. Body text on white panel B — violates text-on-green rule    |
| wahlaufruf-postkarte-a6-quer      | Front Dunkelgrün + Wahlkreuz hero ✓                                         | Back logo 58 % over target. Back copytext on white — violates text-on-green                       |
| wahltag-tueranhaenger             | Brand-Bar Dunkelgrün front+back, Wahlkreuz hero on Hellgrün ✓               | Headline `28 pt × 0.9 = 25.2 pt` linesp target — currently 30 pt (loose). Back copytext on white. Logo 35 mm vs 18.9 mm target |
| themen-plakat-a3-quer             | Farben, Hero on green ✓                                                     | Logo 60×18 mm vs 53.5 mm target (within tolerance). Themen-hero photo currently small — addressed in Delivery C3 |

**Top 3 systemic risks** (deferred to follow-up issue):

1. *"Typografie steht immer mit Grün"* — body copytext on white violates
   this rule in 4 of 8 templates. Fixing requires adding Dunkelgrün/
   Hellgrün backing panels behind copytext frames, which is an
   intentional brand-strict refactor, not a Hygiene change.
2. Logo-Größen-Drift — 3 of 8 templates exceed `15 %` tolerance vs the
   `3 × M` Print target. Tightening requires resizing all `ImageFrame`s
   and re-rendering galleries.
3. Headline-Zeilenabstand drift — Quickguide formula `× 0.9` is tighter
   than current builds (e.g. Türanhänger uses 30 pt for 28 pt → ratio
   1.07, formula wants 0.9). Tightening requires per-template ParaStyle
   audit.

These are tracked here as observations, NOT as iter-3 work items. The
follow-up issue should reference this section.

## References

- Source PDF: `shared/brand/CD-Quickguide.pdf` (committed)
- CI source-of-truth: `shared/ci.yml`
- Wahlkreuz asset (existing, reused for Störer-Banner): `shared/assets/wahlkreuz.png`
- Sonnenblume center-embed (QR): `shared/logos/sonnenblume-circle.png`
- Brand logos (after Delivery B): `shared/logos/gruene-logo-bund-dunkel.{png,svg}`
