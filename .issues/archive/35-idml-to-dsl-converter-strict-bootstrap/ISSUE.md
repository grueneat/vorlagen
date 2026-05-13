---
id: '35'
title: IDML to DSL converter — strict bootstrap (idml_to_dsl.py)
status: done
priority: medium
labels:
- templates
- dsl
- architecture
source: github
source_id: 72
source_url: https://github.com/GrueneAT/vorlagen/issues/72
---

## Context

The Grüne design team works in Adobe InDesign. They've delivered a new
Falzflyer variant — `originals/26-03-Leporello z-Falz 99x210 6-seitig
gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes
Cover 2.idml` — and want it integrated into the existing DSL pipeline.

The repo already has the inverse converter for Scribus: `tools/sla_to_dsl.py`
is the strict, one-shot bootstrap that produced every current `templates/*/build.py`
from the original `.sla` files. This issue is the analogue for InDesign.

The new file is the **same physical format** as the existing
`templates/kandidat-falzflyer-din-lang` (297×210 A4-quer, 3-fach Zickzackfalz,
6 panels à 99×210mm). So the DSL primitives and most of the slot schema
carry over — only the converter is new.

## Scope

**New tool: `tools/idml_to_dsl.py`** — strict, one-shot bootstrap.

- Reads an IDML (ZIP of XML) via `simple-idml` + `lxml`
- Walks Spreads / Stories / Resources / MasterSpreads
- Emits a typed-DSL `build.py` against `sla_lib.builder` primitives
  (`Document`, `DocumentLayer`, `TextFrame`, `ImageFrame`, `Polygon`,
  `Run`, `ParaStyle`, `Brand`, …)
- Strict mode: raises `UnhandledElement` on anything outside the corpus
  (same philosophy as `sla_to_dsl.py` D6)

**First target template:**
- `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/` with:
  - `build.py` (emitted by the converter)
  - `meta.yml` (slot schema cloned + adjusted from `kandidat-falzflyer-din-lang`)
  - `template.sla` (output of `build.py`)
  - `preview.pdf` (rendered)

## IDML → DSL mapping

| IDML element | DSL primitive |
| --- | --- |
| `DocumentPreference PageWidth/Height` | `Document(trim_mm=…)` |
| `Layer Name=…` | `DocumentLayer` |
| `Spread / Page` | document page |
| `Rectangle / Polygon` with FillColor | `Polygon` |
| `TextFrame` + ParentStory | `TextFrame` with `Run`s |
| `TextFrame` containing `Image` | `ImageFrame` + `pack_inline_image` |
| `ParagraphStyleRange / CharacterStyleRange` | `ParaStyle` + `Run` |
| `Resources/Graphic.xml Color` | `Brand` palette entry |

## Geometry

Each PageItem carries `ItemTransform="a b c d tx ty"` (affine) plus
`PathPointArray` of anchors in frame-inner space.

To get page-relative `(x_mm, y_mm, w_mm, h_mm)`:

1. Cascade parent-Group transforms top-down (matrix multiply)
2. Apply matrix to anchors: `x' = a·x + c·y + tx`, `y' = b·x + d·y + ty`
3. Bbox of transformed points → `(x, y, w, h)` in points
4. Subtract spread origin from `Spread/PageTransform` (spread-centered → page-top-left)
5. `pt × 25.4/72` → mm

## Known pitfalls (raise loudly, extend per-corpus)

- **Nested Groups** carry their own `ItemTransform` — cascade required
- **Rotated frames** (`b,c ≠ 0`) — bbox of transformed points, not raw w/h
- **Threaded TextFrames** — `NextTextFrame` / `PreviousTextFrame`; one Story across multiple frames
- **MasterSpread overrides** — base geometry in `MasterSpreads/`, overrides on spread
- **TextFrame inner origin is frame center**, not top-left (idiosyncratic)
- **Spread-centered origin** produces negative coords routinely

## Out of scope

- Multi-IDML batch import (one file at a time is enough for now)
- Round-trip DSL → IDML (one-way only)
- `.indd` binary format (only `.idml`)
- A general InDesign-feature renderer beyond what the existing DSL covers
- Visual-diff bbox extraction (separate issue, follow-up)

## Acceptance Criteria

- [ ] `tools/idml_to_dsl.py` exists; runs strict against the bundled IDML
- [ ] Emits a valid `build.py` for `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/`
- [ ] The emitted `build.py` runs and produces a `template.sla` that renders to a `preview.pdf`
- [ ] `meta.yml` is in place with slot schema (clone-adjusted from existing falzflyer)
- [ ] CI passes (spec_check, audit_alignment, visual_diff with sensible per-region tolerances if needed)
- [ ] Unknown IDML elements raise `UnhandledElement` with a clear hint pointing to where in the converter to extend
- [ ] README in `tools/idml_to_dsl.py` docstring documents the one-shot usage (same shape as `sla_to_dsl.py`)

## References

- Existing converter: `tools/sla_to_dsl.py` (philosophy, strict mode, output shape)
- Target sibling template: `templates/kandidat-falzflyer-din-lang/` (meta.yml + build.py reuse)
- DSL primitives: `tools/sla_lib/builder/`
- Source IDML: `originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/`
- SimpleIDML library: https://pypi.org/project/SimpleIDML/ (v1.2.0)
- IDML spec PDF: see RESEARCH.md (links surface during research stage)
