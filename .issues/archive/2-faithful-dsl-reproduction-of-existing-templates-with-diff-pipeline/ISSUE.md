---
id: '2'
title: Faithful DSL reproduction of existing templates with diff pipeline
status: done
ship_state: merged
priority: high
labels:
- dsl
- validation
- reproduction
- diff
---

## Goal

Build **byte-equivalent DSL reproductions** of the three existing templates (Postkarte, Plakat A1, Grüne Zeitung) plus a **comparison pipeline** that proves the DSL output matches the originals — both at the SLA structural level and at the rendered-PDF visual level.

Without this, the DSL has no validated baseline. Right now my Phase-1 DSL output looks like the brand but is layout-wise unrelated to the actual originals — the existing templates would be unusable on the gallery.

## Why

User feedback (PR-context): _"Wenn wir die SLAs nicht in der DSL nachbauen haben wir keine ahnung wie gut die DSL wirklich funktioniert, damit ist sie sinnlos. Wir brauchen einen exakten nachbau inklusive einer pipeline die einerseits einen vergleich der files macht und andererseits auch die pdfs rendert und einen vergleich macht."_

Two consequences:

1. The galleried templates must visually match what users have been using. DSL "lookalikes" don't qualify.
2. The DSL must be validated by reproducing real layouts. If a feature is missing it has to be added until the diff is clean.

## Scope

### A. Converter — `tools/sla_to_dsl.py`

Reads an existing SLA, emits a `build.py` Python script that uses the DSL to recreate it. Must handle:

- DOCUMENT attributes (page size, bleed, margins, units)
- All MASTERPAGE definitions, all PAGE assignments (NUM, MNAM, LEFT)
- Every PAGEOBJECT and MASTEROBJECT, by PTYPE:
  - 2 (Image) → `ImageFrame(..., raw_attrs=...)`
  - 4 (Text) → `TextFrame(runs=[...], raw_attrs=...)` preserving per-ITEXT formatting (FCOLOR, FONTSIZE, FFAMILY, FSHADE, etc.) and paragraph styles
  - 5 (Line) → `Line(...)`
  - 6 (Polygon) → `Polygon(custom_path=...)` for arbitrary FRTYPE=3 paths
  - Other PTYPEs → `RawFrame(...)` escape hatch
- StoryText structure: ITEXT runs + para + breakline + tab + trail elements, soft-hyphen `\xad` preservation
- COLOR palette (any custom colors not in `shared/ci.yml` get emitted as ad-hoc colors)
- Style + CharStyle definitions
- LAYERS list with all attributes
- NEXTITEM/BACKITEM linking chains (linked text frames in newspaper articles)
- Bleed, hyphen-exceptions, sections

### B. DSL extensions

Add what's missing. Likely needed:

- `raw_attrs={}` parameter on TextFrame/ImageFrame/Polygon/Line — overrides any default
- `custom_path` on Polygon for arbitrary path data (FRTYPE=3)
- `runs=[(text, attrs, separator)]` in TextFrame must support per-run FCOLOR + FSIZE + FFAMILY (charstyle override) — already partial, must complete
- Soft-hyphen passthrough in run text (no auto-stripping)
- Linked frame chains (`linked_to=other_frame`)
- Custom non-ci colors registrable on the document (so converter doesn't have to extend ci.yml)

### C. Structural diff — `tools/sla_diff.py`

Compare two SLAs, ignoring volatile fields. Reports semantic differences only.

- Normalise `ItemID` (renumber sequentially in document order on both sides)
- Normalise floating-point precision (round to 6 decimals for comparison)
- Normalise attribute order (XML attribute order is meaningless)
- Sort PAGEOBJECT order by `(OwnPage, YPOS, XPOS)` for stable comparison
- Output: per-element diff with severity (critical = different page count, warning = position diff > 0.5pt, info = stylistic-only)
- Exit 0 if identical-up-to-tolerance, 1 if drift

### D. Visual diff — `tools/visual_diff.py`

Render both SLAs to PDF, rasterise to PNG at 150dpi, compare per-page.

- ImageMagick `compare -metric AE -fuzz 2%` (or pixelmatch via `odiff` if available)
- Per-page report: pixel-mismatch count, percentage
- Output: side-by-side composite PNG (expected | actual | delta) for inspection
- Tolerance config per template (`templates/<id>/diff.yml`) — body text regions can have higher tolerance than headline regions

### E. Reproductions

For each of `postkarte-vorlage-original.sla`, `plakat-a1-hochformat-original.sla`, `gruene-zeitung-vorlage-original.sla`:

1. Run converter → `templates/<id>/build.py`
2. Run `build.py` → `templates/<id>/template.sla`
3. Run `sla_diff` against the original → must pass
4. Render and `visual_diff` against pre-rendered original PDF → must pass within tolerance
5. Replace the current placeholder DSL versions

The Zeitung is the hardest with 14 pages, 146 frames, multi-column text flow, 2 master pages. If features are missing, add them.

### F. Testing & CI

- Unit tests cover converter on all three originals (no exceptions during conversion)
- Unit tests cover sla_diff with synthetic differences
- A new GitHub Actions workflow step `validate-reproductions` runs both diffs against all templates, fails on drift
- Pages workflow blocks deploy if validations fail

## Acceptance Criteria

- [ ] `tools/sla_to_dsl.py` runs cleanly on all three originals, emits valid `build.py` files
- [ ] DSL `raw_attrs`, `custom_path`, per-run formatting, linked frames, soft-hyphens implemented and tested
- [ ] `tools/sla_diff.py` reports zero critical/warning differences between each original and its DSL reproduction
- [ ] `tools/visual_diff.py` reports < 1% pixel mismatch per page (configurable per template)
- [ ] All three `templates/<id>/template.sla` files are now DSL-built and faithful to their originals
- [ ] CI workflow includes the validation step; it passes on `main`
- [ ] Pages gallery now serves the faithful templates instead of the lookalike DSL output
- [ ] Unit tests added for converter + diff tools, all green
- [ ] README updated to describe the round-trip validation

## Out of Scope

- Bundled fonts and ICC profiles (separate issue, was discussed before this one)
- LLM authoring tooling (still deferred)
- Block-extraction tools (still deferred)
- Visual-regression baseline-blessing UI

## Notes / Pointers

- Originals at workspace root: `postkarte-vorlage-original.sla`, `plakat-a1-hochformat-original.sla`, `gruene-zeitung-vorlage-original.sla`
- Existing DSL builder under `tools/sla_lib/builder/` — extend, don't rewrite
- Existing reader under `tools/sla_lib/reader.py` — use for parsing originals
- Format pitfalls all documented in `.research/01-sla-format.md` and `.research/04-scribus-multipage-masters.md`
- Headless render proven: `xvfb-run -a scribus -g -ns -py tools/_export_pdf.py <sla> <pdf>`
- The gap is structural: my Phase-1 DSL output uses my own layouts, not the originals' layouts. Closing that gap is this issue's whole job.
