# Design System Brief — Vorlagen Repo

**Audience:** Claude Design (web), other vision-capable agents, human design partners working remotely.
**Scope:** Layout iteration, brand audits, new template proposals for the Grünen-NÖ Vorlagen-System.
**Source-of-truth:** This brief is the **entry point**. It points at authoritative files; it does not duplicate their content. Always read the linked files yourself before producing recommendations — the brief is current as of last commit but specific values (colors, dimensions, slot tables) live in the canonical files.

---

## 1. What this repo is

Versioned, brand-consistent skeleton templates (postcards, posters, newspapers) for the Grünen Niederösterreich (Austria, federal-state Greens). Local groups (Bezirks-/Ortsgruppen) download the templates from the public gallery, open them in Scribus, fill their content, and print.

- **Live gallery:** https://grueneat.github.io/vorlagen/
- **Repo:** https://github.com/GrueneAT/vorlagen (public)
- **Authoring tool:** [Scribus 1.6](https://www.scribus.net/) — open-source desktop publishing
- **Format:** SLA (Scribus document). Templates are emitted from a Python DSL (`tools/sla_lib/builder/`) — see §6 if you need to read code.

---

## 2. Where to read the brand context

| File | What it says | When to read |
|---|---|---|
| [`shared/brand/CD-Quickguide.pdf`](../brand/CD-Quickguide.pdf) | Authoritative Corporate Identity quickguide PDF (2 pages, ~552 KB) | Always — primary source for brand rules |
| [`shared/brand/QUICKGUIDE-NOTES.md`](./QUICKGUIDE-NOTES.md) | Human-readable extraction of Quickguide rules: colors, fonts, font-relationships, M-margin formula, logo sizing, layout principles, Störer patterns | Always — fastest way to load brand rules into your context |
| [`shared/ci.yml`](../ci.yml) | Machine-readable color palette (CMYK + role tags), font list, paragraph styles | When proposing color or typography changes |
| [`shared/logos/`](../logos/) | Brand logos: G-brushstroke (`gruene-logo-bund-dunkel.png/.svg`, primary), white-on-green (`gruene-weiss.png`), Sonnenblume circle (`sonnenblume-circle.png`, used in QR centers) | When proposing logo placement |
| [`shared/sample-images/`](../sample-images/) (after merge of #13) | Centralized library of demo images (portraits, themen-photos, kontext-scenes) with manifest + Codex prompts. License: synthetic, demo-only. | When proposing image placement |

---

## 3. The 8 templates currently in the gallery

| Template | Format | Audience | Layout philosophy | 1-second-test (what reader sees first) |
|---|---|---|---|---|
| `postkarte-a6-kampagne` | A6 hochformat, 2-seitig | Bezirks-/Ortsgruppen | Symbol-zentriert, headline + Störer | "Hier steht eine vierzeilige Überschrift" |
| `plakat-a1-hochformat` | A1 hochformat | Alle Gruppen | Event-Plakat, große Headline | Event-Headline mit Datum |
| `zeitung-a4-grun` | A4 hochformat, 14-seitig | Bezirks-/Landesgruppen | Multi-Layout-Zeitung mit Master-Pages | Cover-Headline „Klimaschutz ist Wirtschaftspolitik" |
| `themen-plakat-a3-quer` | A3 quer, 1-seitig | Bezirks-/Ortsgruppen | Argumentation: These → 3 Belege → Quelle | Vollkorn-Italic-Headline („Klimaschutz ist Wirtschaftspolitik") |
| `wahlaufruf-postkarte-a6-quer` | A6 quer, 2-seitig | Ortsgruppen | Symbol-zentriert (Wahlkreuz), GOTV | Wahlkreuz im Zentrum + „Wähle Grün am 23. Mai" |
| `wahltag-tueranhaenger` | 105×250 mm vertikal mit Stanzform | Ortsgruppen | Schmal-vertikal Türanhänger | „Heute ist Wahltag." Vollkorn-Italic |
| `infostand-tent-card-a5-quer` | A4 quer gefalzt → A5-Tent | Bezirks-/Ortsgruppen | 3D-doppelseitig sichtbar (DE / EN) | „Klimaschutz konkret." mit Bullets |
| `kandidat-falzflyer-din-lang` | A4 quer 3-fach gefalzt → 6 Panele | Bezirks-/Ortsgruppen | Multi-Panel-Narrativ (Cover-Bio-Themen-Closer) | Kandidatin-Portrait + Slogan |

Each template lives at `templates/<slug>/` with `build.py` (DSL source), `meta.yml` (metadata), `README.md` (end-user-instructions), `template.sla` (build artifact, what end-users open), `preview.pdf` + `page-*.png` (gallery preview).

---

## 4. The 10 brand-rules (verbatim from Quickguide)

> Always cross-check against the full PDF/Notes — these are the most-applied rules, not exhaustive.

1. **Colors** — only from the brand palette: Dunkelgrün (`#257639` / CMYK 85/35/95/10), Hellgrün (`#56af31` / 69/0/100/0), Gelb (`#ffed00` / 0/0/100/0), Magenta-Störer (`#e6007e` / 0/100/0/0), plus Black, White, Registration. **No off-palette colors.**
2. **Fonts** — Gotham Narrow Ultra (Headlines), Gotham Narrow Book (Sublines + Copytext), Vollkorn Black Italic (Hervorhebungen + Zitate). No other typefaces.
3. **Line-spacing** — `Schriftgröße × 0.9` for headlines/sublines; Fließtext `× 1.3`.
4. **HL/SL Abstand und HL/Copy Abstand** — `X × 2`, where X is the baseline grid unit.
5. **Mindestabstand zum Formatrand:** `M = 0.06 × kurze_kante` (proportional to format short edge).
6. **Logogröße:** `3 × M` (print) / `2.5 × M` (digital). Logo-Schutzzone is `M` — no element may encroach.
7. **Layout-Grundprinzip:** **„Typografie steht IMMER in Kombination mit Grün."** Text only on Dunkelgrün or Hellgrün surfaces. Text on photos requires the person/subject to clearly stand against green (Freisteller or photo-on-green-background).
8. **Wahlkreuz-Hintergrundregel** — the Wahl-Kreuz-im-Kreis asset (yellow cross, white circle) must always sit on a colored background (Dunkelgrün / Hellgrün / Magenta). Never on white or yellow (cross or ring vanishes).
9. **Bleed:** 3 mm bleed all sides for print. CMYK-only output.
10. **Störer:** Magenta circles (`Hier steht ein Störer`) or Magenta date-banner with Wahlkreuz (`31.8. ✗ Grün`). Don't invent new Störer-Forms.

---

## 5. Hard constraints (must respect; non-negotiable)

- **EU AI Act Art 50 (in force 2026-08-02):** Synthetic / AI-generated images bear a visible "Symbolfoto — KI-generiert" watermark. The library auto-applies this; if you propose new synthetic imagery, the watermark must be present in the recommendation.
- **No-Claude-attribution:** End artifacts (templates, content, commits, generated content) never reference Claude / AI tooling explicitly. The user does not expose tooling to clients.
- **Spot-color fidelity:** `Falz` and `Stanzkontur` are spot-color overlays on dedicated layers (D4 of issue #10). Don't change their semantics.
- **Round-trip stability** — the 3 production templates (`postkarte-a6-kampagne`, `plakat-a1-hochformat`, `zeitung-a4-grun`) have committed reference SLAs that build outputs are diffed against. Layout changes that affect `template.sla` must preserve diff-stability OR produce a separate `template-preview.sla` (the gallery render path) leaving `template.sla` as the clean end-user version.
- **Slot-based contract:** Every Image-/Text-Frame in `template.sla` is a slot for end-users to fill. Demo content goes via the Library + `template-preview.sla` mechanism, never hardcoded into `template.sla`.

---

## 6. How the templates are built (skim if interested)

The templates are emitted from a Python DSL in `tools/sla_lib/builder/`:
- `primitives.py` — `TextFrame`, `ImageFrame`, `Polygon`, `Anchor`
- `blocks.py` — composition blocks (Wahlkreuz, Falz, DieCut, etc.)
- `document.py` — `Document`, master pages, layers, spot-colors
- `library.py` — *(after merge of issue #13)* `library.load("portrait_maria")` resolves a library image

Each template's `build.py` composes the layout in code. `python3 build.py` emits `template.sla` (idempotent, byte-deterministic). The repo intentionally keeps the layout-as-code so structural properties (alignment, hierarchy, grid) are reviewable.

You generally don't need to read the code to propose layouts — the rendered PNGs (`templates/<slug>/page-*.png`) plus the spec markdown (`templates/_specs/<slug>.md`) tell you what's there. If you want to be precise about coordinates, `meta.yml` has slot-tables in mm.

---

## 7. Use-case prompt patterns

These are templates you can copy-paste at the START of a Claude Design conversation, then add your specific request.

### A. Brand-Consistency-Audit

> Read `shared/brand/QUICKGUIDE-NOTES.md` as the binding design contract. Then, for each of the 8 templates listed in `shared/brand/DESIGN-SYSTEM-BRIEF.md` §3, look at `templates/<slug>/page-01.png` (and `page-02.png` if 2-seitig). For each template, check compliance against §4 of the Brief and report any violations or near-misses (font choice, color use, M-margin, logo size, "Typografie auf Grün" rule, Wahlkreuz background, Störer form). Output: severity-tagged Markdown table, sorted by severity.

### B. Layout-Variation für ein einzelnes Template

> Read `shared/brand/DESIGN-SYSTEM-BRIEF.md` for context. Read the spec at `templates/_specs/<slug>.md` and the current render at `templates/<slug>/page-*.png`. Propose **3 layout variations** for this template that improve [specific aspect — e.g. headline-subline-hierarchy, photo-text-balance, eye-flow-on-1-second-test]. Each variation must respect the §4 brand rules from the Brief. For each variation provide: title, rationale tied to a Quickguide rule, list of concrete changes (TextFrame mm-coords, font-size adjustments, color picks, slot-additions/removals), optional design-mock as Artifact.

### C. Hierarchy-Refinement

> Read `shared/brand/DESIGN-SYSTEM-BRIEF.md` for context. Look at `templates/<slug>/page-*.png`. The visual hierarchy is currently [describe what feels weak — e.g. "headline and subline read at the same intensity"]. Propose 2-3 hierarchy refinements respecting Brief §4 rule 3 + 4 (line-spacing × 0.9, HL/SL spacing X×2). Output as Markdown report with concrete changes.

### D. Cross-Template-Harmonization

> Read `shared/brand/DESIGN-SYSTEM-BRIEF.md` for context. Look at the page-01.png of all 8 templates listed in §3. Identify spacing / grid / typography / color-use inconsistencies across the set. Output: list of inconsistencies with severity, recommendation per inconsistency, plus an "if I had to fix one thing first" priority pick.

### E. Neues Template proposal

> Read `shared/brand/DESIGN-SYSTEM-BRIEF.md` for context. The repo currently has 8 templates listed in §3. We want a NEW template for: **audience X**, **use-case Y** (describe in detail). Propose: layout philosophy (one-liner), trim + bleed + falz/stanze in mm, slot inventory (≥10 slots with anname + dimensions), 1-second-test answer ("what does the reader see first"), brand-rule applications relevant to this format, ASCII layout sketch.

### F. Sample-Inhalts-Audit

> Read `shared/brand/DESIGN-SYSTEM-BRIEF.md` for context. After issue #13 merges, read `shared/sample-images/manifest.yml`. Check whether the demo content in each template's `page-*.png` (gallery render) is **brand-realistic** — does the photo look like Grünen NÖ campaign material, or generic stock? Report mismatches and propose better library entries (with new prompts) where needed.

---

## 8. Output you should produce

For any of the prompt patterns above, structure the output so it can flow back into the codebase via the issue system:

1. **Summary** (1-2 lines: what you found, what you propose)
2. **Per-template / per-variation section** with:
   - Title
   - Visual mockup (optional, if you have Artifact-rendering capability — render at template's actual aspect ratio)
   - Concrete changes (file:line references where you can; otherwise structural descriptions like "headline at y=28 mm, font-size 36 pt, color Dunkelgrün")
   - Rationale tied to a specific Brief §4 rule or accumulated learning
3. **Severity-or-priority tag** (`blocking | recommended | optional`) per finding/change
4. **Open questions / risks** — anything that needs human decision before implementation

The user takes the markdown report and creates a new issue (`/issue:new`) with it as the seed. The local executor then implements the changes via the DSL.

---

## 9. What NOT to propose (out of scope for design iterations)

- **DSL changes** (the underlying Python code) — that's the user's territory; design iterations focus on layout/visual.
- **New brand colors / fonts** — Quickguide is canonical; deviations need separate brand-discussion.
- **Logo redesigns** — the Grünen-G logo is given; only sizing / placement is in scope.
- **Removing the Wahlkreuz background rule** — D12 is non-negotiable.
- **Web-app / interactive features** — the gallery is a static read-only display.

---

## 10. Session history

This file logs Claude Design (or other vision-agent) sessions for traceability.

| Date | Session | Output | Resulting issue |
|---|---|---|---|
| 2026-05-08 | Pattern B · `wahlaufruf-postkarte-a6-quer` (Source: `improvements/01-wahlaufruf-postkarte.md`) | 3 Layout-Varianten (Symbol-Tight / Datum-Banner / Asymmetric Hero) mit build.py-line-targeted Slot-Änderungen + SVG-Companion-Mocks unter `improvements/01-wahlaufruf-postkarte.html` | https://github.com/GrueneAT/vorlagen/issues/33 (V1 only; V2/V3 backlog) |
| 2026-05-08 | Pattern B · `wahltag-tueranhaenger` (Source: `improvements/02-wahltag-tueranhaenger.md`) | 3 Layout-Varianten (Composed Hero / Vertical Stripe / Manifesto) mit build.py-line-targeted Slot-Änderungen + SVG-Companion-Mocks unter `improvements/02-wahltag-tueranhaenger.html` | https://github.com/GrueneAT/vorlagen/issues/34 (V1 only; V2/V3 backlog) |
| 2026-05-09 | Pattern B · `themen-plakat-a3-quer` (Source: `improvements/03-themen-plakat.md`) | 3 Layout-Varianten (Evidence Cards / Hero Photo / Argument Stack) mit build.py-line-targeted Slot-Änderungen | https://github.com/GrueneAT/vorlagen/issues/35 (V1 only; V2/V3 backlog) |
| 2026-05-09 | V1 · `infostand-tent-card-a5-quer` "Hero Band" (Source: `improvements/04-infostand-tent-card.md`) | Erstes Multi-Panel-Template: Rotation-Contract via `_panel_de` + `_panel_en` Helper (Panel A aufrecht DE, Panel B 180° EN). 3 neue Polygons (Hero-Band/Photo-Backing Dunkelgrün, Footer-Strip Hellgrün), 6 ParaStyles mutated/added (tent/payoff + tent/cta-footer neu, tent/cta gedroppt), 22 CONSTRAINTS (mirrored_y an y=105), 21 NEW geometry tests, brand_overrides cleanup (REMOVE 2 + KEEP 4 incl. empirisch restored brand:image_fills_frame für Logo-Letterbox). | https://github.com/GrueneAT/vorlagen/issues/36 (V1 only; V2/V3 backlog) |

When you (Claude Design) finish a session, append a row here in your output, so the user can paste it into the brief on the next commit.

---

## Appendix: Reading order

If you have only a few minutes, read in this order:
1. This file (you are here) — orient
2. `shared/brand/QUICKGUIDE-NOTES.md` — brand rules
3. `templates/<slug-of-interest>/page-*.png` — current state of the template
4. `templates/_specs/<slug-of-interest>.md` — slot details + intent
5. `shared/ci.yml` — exact color/font specs (only if proposing changes there)

For an exhaustive deep-dive: also `shared/brand/CD-Quickguide.pdf` (full PDF, the source-of-truth Notes was extracted from).
