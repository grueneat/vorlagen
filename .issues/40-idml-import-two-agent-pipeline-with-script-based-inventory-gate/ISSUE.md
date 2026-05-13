---
id: '40'
title: 'IDML import: two-agent pipeline with script-based inventory gate'
status: open
priority: high
labels:
- architecture
source: github
source_id: 87
source_url: https://github.com/GrueneAT/vorlagen/issues/87
---

## Context

Reflection from a long IDML→Scribus import session (template 26-03 Leporello z-Falz, see commit history on `main`).

Pattern observed across ~30 convergence iterations: every visual fix went into `tools/idml_to_dsl.py` (the shared converter), so each fix had to be correct for *every conceivable IDML*. Result was whack-a-mole — fixing one template's photo crop broke another template's icon rendering; tightening line spacing for headlines over-spaced quotes; per-font intrinsic floors helped Vollkorn and broke Gotham. A 916-line diff accumulated, of which ~200 lines were genuine converter improvements and ~700 lines were template-specific heuristics that should have been per-template overrides.

Root cause: **the converter is treated as if it must handle every edge case for every template**. Visual fidelity tuning is conflated with structural correctness.

## Proposal: two-agent pipeline

### Stage 1 — Scaffold agent (converter, single-shot)

- Runs `bin/idml-import --scaffold-only`
- Produces `templates/<slug>/{build.py,meta.yml,baseline.pdf}` + `shared/assets/<slug>/`
- Goal: **structurally complete output**, visually rough is acceptable
- Touches `tools/idml_to_dsl.py` only when a structural gate fails

### Stage 2 — Tuning agent (per-template, iterative)

- Reads `templates/<slug>/SCAFFOLD_INVENTORY.yml` (produced by Stage 1) as its source of truth for "what must remain"
- **Permitted edits**: `templates/<slug>/build.py`, `templates/<slug>/inject.yml`, `templates/<slug>/meta.yml::brand_overrides`, `templates/<slug>/TOLERANCES.yml`
- **Forbidden edits**: `tools/idml_to_dsl.py`, `tools/sla_lib/**`, any shared converter code
- Per iteration: render → audit (named-element gate) → pick worst element → edit build.py / inject.yml → re-render → confirm no regression on any named element
- Terminates: `preflight.ok=true` AND named-element gate passes, OR explicit `--accept-residual` with `human-review`/`authoring-bug` classifications

### Why this works

- Converter changes only happen when 1+ templates are *structurally* broken — visual fidelity is the tuning agent's problem
- Tuning can't regress because the named-element inventory gates each iteration
- The scaffold can run nightly as CI without breaking hand-tuned templates
- Converter PRs gate on "no template's scaffold inventory regresses"; tuning PRs gate on "that template's named elements all pass"

## Script-based inventory gate (the critical piece)

The inventory check must NOT be LLM-driven comparison. It must be a deterministic script that compares structural inventories between IDML source, build.py, rendered SLA, and rendered PDF — passing/failing on counts and structural identity, not visual similarity.

### Inventory schema

`templates/<slug>/SCAFFOLD_INVENTORY.yml`:

```yaml
schema_version: 1
template: 26-03-leporello-...

text_runs:
  total_idml: 437                  # count of <CharacterStyleRange>/<Content> with non-empty text
  by_paragraph_style:
    - style: ParagraphStyle/Fließtext
      idml_count: 23
      build_py_count: 23
      sla_itext_count: 23
      pdf_word_count: 213
  every_idml_run_present_in_build_py: true   # set-equality on (text, font, fontsize)

frames:
  text_frames:
    - anname: u1b0
      idml_position_mm: [110.5, 17.4, 75.0, 17.99]
      build_py_position_mm: [110.5, 17.4, 75.0, 24.69]   # h widened by Pattern-9
      sla_pageobject_present: true
      sla_storytext_runs: 3
  image_frames:
    - anname: u514
      idml_link: ziesel.jpg
      build_py_image_ref: "../../shared/assets/<slug>/ziesel.jpg"
      sla_pfile_present: true
      pdf_image_present: true          # found via pdfimages -list, matched by size/position
  polygon_frames: [...]
  group_frames: [...]

paragraph_styles:
  - idml: ParagraphStyle/Aufzählungen
    build_py: idml/aufzaehlungen-...
    sla_pstyle_present: true

colors:
  - idml: Color/Endformat
    cmyk: [0, 100, 100, 0]
    build_py_extra_color: true
    sla_color_present: true

assets:
  - basename: ziesel.jpg
    on_disk: true
    classified: external          # or "embedded"
    referenced_from_frames: [u514]

words:
  baseline_pdf_count: 444
  preview_pdf_count: 444
  missing_from_preview: []
  extra_in_preview: []
```

### Comparison script (`tools/inventory_compare.py`)

```bash
# Produces diff of named elements between two snapshots.
python3 tools/inventory_compare.py \
    --expected templates/<slug>/SCAFFOLD_INVENTORY.yml \
    --actual <(python3 tools/inventory_extract.py --slug <slug>) \
    --out build/validation/<slug>/inventory_diff.yml

# Exit codes:
#   0 = perfect match
#   2 = missing element (regression — block)
#   3 = unexpected element (new content drifted in)
```

`tools/inventory_extract.py` walks build.py + template.sla + preview.pdf and emits the same schema. Then `inventory_compare.py` is pure set/count comparison — no LLM.

### Specific extractors needed

| Source | Extractor | What it counts |
|---|---|---|
| IDML | `walk_idml_inventory.py` | `<CharacterStyleRange>` content runs, `<Rectangle/Polygon/Oval/TextFrame/Image/PDF/Group>` self-ids, `<ParagraphStyle>` names, `<Color>` definitions, `<Link>` URIs |
| build.py | `walk_build_py.py` (importlib + AST) | `doc.add_para_style(...)` calls, `doc.add_color(...)` calls, `page.add(TextFrame/ImageFrame/Polygon/...)` calls, anname attrs, position tuples |
| SLA | `walk_sla.py` | `<PAGEOBJECT>` elements by ANNAME, `<ITEXT>` runs, `<STYLE>` definitions, `<COLOR>` swatches, PFILE refs |
| PDF | `walk_pdf.py` | `pdfimages -list` for raster placements, `pdftotext` for word counts, `pdfplumber` for word positions |

### Gate rules

Stage 1 (scaffold) blocks if:
- Any IDML `<CharacterStyleRange>` text content is missing from build.py
- Any IDML frame's `Self` ID has no corresponding emit in build.py
- Any IDML paragraph style has no `add_para_style` call
- Any IDML Link basename isn't on disk
- `python3 build.py` exits non-zero
- `render_pipeline.py` exits non-zero
- Word count from preview.pdf differs from text-content-character count in build.py by > 5%

Stage 2 (tuning) blocks any iteration that:
- Changes a `count` field downward in inventory_diff.yml
- Removes an `anname` from any frame list
- Drops a word from `preview_pdf_words` that was present in the previous iteration's snapshot

## Lessons from this session (the full list)

1. **Plan + execute split** — produce inventory up-front, check it on every iteration
2. **Regression guard with named-item gates** — drift_p1 hides regressions of individual elements; the inventory diff is the canonical signal
3. **SLA semantics catalog** — Scribus attribute behavior (SCALETYPE, FLOP, LINESPMode, HCMS, PRFILE, LOCALSCX interpretation, EMBEDDED, frame rotation w/h swap) belongs in `docs/scribus-sla-attribute-semantics.md`, not lore re-derived each session
4. **Don't tune one frame to break another** — converter heuristic changes must pass the inventory gate on every prior-passing element
5. **Image handling is its own subdomain** — fill-vs-fit, LOCALSCX scale base, IDML translation, centering, DPI awareness, CMYK→sRGB, alpha, composite-AI all need separate empirical thresholds in a dedicated pattern catalog
6. **Visual-diff is a poor first-class signal** — pages where every element is correct can read worse than pages with content missing because the correct render had photo-edge mismatch; inventory passes first, visual diff is secondary
7. **Iteration discipline beyond banned phrases** — never stop without checking the inventory; the banned-phrase list catches symptoms not causes
8. **Agent delegation needs the inventory too** — subagents must receive the named-element matrix and explicitly report which elements their fix touches
9. **Calibrate against rendered baseline, not just IDML** — render one anchor template, compare pixel-positions of known elements between baseline.pdf and dsl render, tune converter params to align
10. **Trade-off pinning** — implicit visual trade-offs evaporate on re-roll; commit each one to `templates/<slug>/TOLERANCES.yml` with a justification line
11. **Converter target: "ballpark correct" not "pixel-perfect"** — the converter scaffolds; the tuning agent polishes; never the same agent for both
12. **Two-agent pipeline, not human handoff** — Stage 2 is another Claude process consuming the validated scaffold

## Skill changes

- `/idml-import` (existing) → split into `/idml-scaffold` (Stage 1, structural gate) and `/idml-tune` (Stage 2, per-template polish)
- New skill `/idml-tune <slug>` that operates strictly within one template's directory
- SOP rewrite for `.claude/skills/idml-import/SKILL.md`:
  - Step 6.5 (mandatory iteration discipline) → replaced by inventory-gate check that runs every iteration
  - Add tooling section: `tools/inventory_extract.py`, `tools/inventory_compare.py`
  - Add forbidden-paths list for Stage 2
- Add `docs/scribus-sla-attribute-semantics.md` capturing the corpus-tested behavior of every Scribus attribute we touch
