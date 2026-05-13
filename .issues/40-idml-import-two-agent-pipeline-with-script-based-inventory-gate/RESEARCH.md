# Research — Two-agent pipeline + inventory gate

**Researched:** 2026-05-13
**Issue:** 40-idml-import-two-agent-pipeline-with-script-based-inventory-gate
**Confidence:** HIGH (all findings grounded in on-disk evidence)
**Anchor template present:** `/workspace/templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/` (NOT in the worktree — only in main `/workspace/`; worktree is a sparse checkout listing 11 other templates).

## User Constraints (from CONTEXT.md)
**Locked**: full plan one PR; anchor=26-03 Leporello; comparison is a deterministic script (not LLM); Stage 2 forbidden paths = `tools/idml_to_dsl.py`, `tools/sla_lib/**`, shared converter code; Stage 2 permitted = `templates/<slug>/{build.py,inject.yml,meta.yml::brand_overrides,TOLERANCES.yml}`.
**Non-goals**: migrating other tuned templates; replacing `drift_p1`; rewriting the converter; CI/Slack of the gate; composite-AI splitter overhaul.

## Existing extractor/walker surface

### IDML walker (`tools/idml_to_dsl.py`, 3479 lines)
- Element types iterated at `_PAGE_ITEM_LEAF_TAGS` (line 2867): `{Rectangle, Polygon, Oval, TextFrame, Image, PDF, GraphicLine, Group}`. EPS is NOT in the leaf set (no leporello EPS — confirmed).
- `_walk_idml_pageitem_self_ids()` (line 2873) already returns the universe of `Self` IDs by walking every `spread.xml` with `root.iter()`. **This is exactly the surface walker the inventory needs.**
- `_walk_csr()` (line 2566) reads each `<CharacterStyleRange>`: pulls `AppliedFont` via `_csr_applied_font` (line 2317), `FontStyle`, `PointSize`, `FillColor`, walks direct children for `Content`, `Br`, `<?ACE 7?>`, and emits `Run` primitives. **Re-use verbatim**: family + size + color + text are exactly the `(text, font, fontsize)` tuple the inventory needs for set-equality.
- `_walk_story()` (line 2347) handles `<ParagraphStyleRange>` → `Justification`, `Leading` via `_psr_effective_leading`. Document order is preserved via lxml's `.iter()`.
- Walker order: `pkg.spreads` (designmap.xml order) → spread.xml → tree iter → leaf tag filter. Already what the gate needs.
- Conversion-completeness assertion (`_assert_conversion_completeness`, line 2896) already compares `ctx.emitted_self_ids` (populated at line 1580 inside `_emit_pageitem`) against the walked universe — **this is a half-built inventory gate**. Lifting it out into `walk_idml_inventory.py` is mostly mechanical.
- `tools/idml_inventory.py` (439 lines, separate from `idml_to_dsl.py`) is the closest existing prior art: walks `Spreads/Spread_*.xml`, filters by `Printable` layer via `designmap.xml`, returns `[{self, type, bbox_pt, hint, parent_groups}, ...]`. Already extracts annames from `build.py` via regex (line 282 `_extract_annames_from_build_py`). **Rename + extend** to become `tools/walkers/walk_idml_inventory.py`; do NOT write from scratch.

### SLA reader (`tools/sla_lib/reader.py`, 139 lines)
- `SLADocument` class wraps `lxml.etree.parse` of `.sla`. Already exposes `page_objects()` (line 56 — `findall("PAGEOBJECT")`), `iter_colors`, `iter_styles`, `iter_charstyles`, `iter_itext`, `find_by_anname`, `slots()` (with `ANNAME → Slot` and `PTYPE → human name` table at line 9 — `4=Text, 6=Polygon, 2=Image, 12=Group`).
- `frame_text(frame)` (line 128) returns concatenated `CH` attributes of all child `ITEXT` — the SLA-side equivalent of "what text reached the render". 
- PFILE: not exposed as a property on `SLADocument` but accessible via `frame.get("PFILE")` on any `PAGEOBJECT`. Builder emits PFILE in `primitives.py:829` for ImageFrame. **No SLA reader extension needed** — `walk_sla.py` is ~50 lines of glue over `SLADocument`.
- Confirmed counts in anchor SLA: PAGEOBJECT=83, STYLE=14, COLOR=10, ITEXT=69, PAGEOBJECT-with-PFILE=3.

### build.py walker (proposed approach)
**Recommendation: AST-first, importlib-with-recorder for any ambiguous call.** Evidence:
- The leporello `build.py` is 1135 lines, 83 `anname=` literals, 23 `page0/1.add(TextFrame`, 10 `add(ImageFrame`, 16 `add(Polygon`, 34 `add(PolyLine`, 6 `add_para_style`, 3 `add_color`, 104 `Run(` constructions.
- All `page.add(...)` calls observed are pure kwarg-keyword calls with literal values — `x_mm=204.6586, y_mm=151.5858, w_mm=86.84, h_mm=16.3815, anname='u155', layer=0, style='idml/normalparagraphstyle', runs=[Run(...), Run(...)]`. No splats, no comprehensions, no conditionals around `page.add` in the anchor (see lines 174–300 quoted in evidence below). AST extraction with `ast.parse` + `ast.literal_eval` on each kwarg covers ≥95% of calls.
- Where AST fails (e.g. `runs=[Run(...)]` with nested Run calls): walk the AST further — Run constructors are also pure-kwarg. The leporello `runs=[...]` lists carry text + font + fontsize + fcolor + paragraph_style + paragraph_attrs (line 234, 246 in build.py): all literals.
- importlib fallback: import build.py with a monkey-patched `Document` whose `add_*` and `Page.add` are recorders. This evaluates conditionals/loops if any template grows them later. **But it executes side effects** (build.py reads `shared/assets/<slug>/` paths). Safer mode: AST-first, fallback only for files that fail AST extraction.
- `tools/baseline_image_audit.py::_extract_imageframes_from_build_py` (line 149) is already an AST-based ImageFrame extractor — **lift this pattern** for the inventory walker.
- `tools/idml_inventory.py::_extract_annames_from_build_py` (line 282) does pure regex over `anname='...'` literals and detects constructor type via regex context (`TextFrame|ImageFrame|Polygon|Oval|GraphicLine`). Regex is sufficient for the anname set; AST is needed only for positions and `runs=[...]`.
- **Pitfall**: leporello build.py uses widening comments like `# h_mm widened 34.7873mm→81.8444mm` (line 237). The walker must read the *literal* values in the call, not the comments. AST handles this trivially.

### PDF extractors
All three are available and already used in the codebase:
- `/usr/bin/pdftotext` → `tools/text_render_audit.py::extract_pdf_words` (line 77) returns `Counter` of normalized words per PDF. Anchor preview.pdf = 450 words, baseline.pdf = 450 words.
- `/usr/bin/pdfimages -list` → `tools/baseline_image_audit.py::_parse_pdfimages_list` (line 44) returns `{page: image_count}`. Anchor preview shows 13 raster rows (incl. smasks) across 2 pages.
- `pdfplumber 0.11.9` (Python module) → `tools/line_spacing_audit.py:38` and `tools/text_position_audit.py::extract_words_with_positions` (line 61) → word-level (x, y, w, h) tuples. **Reuse for word-position diff if/when needed.** For the v1 schema, string-only word matching is enough (CONTEXT.md open question #2 already biased toward string-only).
- `lxml 5.4.0` and `pyyaml 6.0.3` installed.

## Skill split plan

**Current**: `.claude/skills/idml-import/` (229-line SKILL.md + 5 sub-docs: `asset_policy.md`, `classification.md`, `inject_protocol.md`, `pattern_library.md`, `tolerance_protocol.md`).

**Proposed layout** (matches CONTEXT.md decisions):
```
.claude/skills/
├── idml-scaffold/
│   ├── SKILL.md                # Stage 1: structural gate, may touch converter
│   ├── classification.md       # COPIED verbatim from idml-import/
│   ├── pattern_library.md      # COPIED verbatim
│   └── asset_policy.md         # COPIED verbatim (P11 still applies)
└── idml-tune/
    ├── SKILL.md                # Stage 2: per-template, forbidden-paths enforced
    ├── inject_protocol.md      # COPIED from idml-import/
    ├── tolerance_protocol.md   # COPIED from idml-import/
    └── forbidden_paths.md      # NEW: explicit list + enforcement script
.claude/skills/idml-import/SKILL.md  # → 30-line redirect stub pointing at scaffold + tune
```

**SKILL.md splits cleanly along existing section boundaries**:
- Steps 1–2 (asset extraction, first-render audit) → `idml-scaffold/`. Adds new step: emit `SCAFFOLD_INVENTORY.yml` after Step 1.
- Steps 3 (classification), 4 (converter-first), 5 (hand-patch inject.yml), 6 (tolerance growth), 7 (termination) → `idml-tune/`. Add inventory-gate check at the head of every iteration.
- Banned-phrases section and P1–P11 SOP → duplicated into both (they apply to both stages).
- The original "Step 6.5 (mandatory iteration discipline)" referenced in the issue does NOT exist verbatim in SKILL.md — the closest is the **Banned phrases** section (lines 165–183) plus the **SOP commitments P1–P10** block (lines 185–217). The ISSUE.md says "replaced by inventory-gate check that runs every iteration" — this replaces the banned-phrase-only deterrent with a deterministic check. Plan: keep banned phrases AND add inventory-gate as a hard precondition for any "loop continues" decision in `idml-tune`.

## SCAFFOLD_INVENTORY.yml extractor mapping

| Schema key | Source | Extractor (existing) | Extractor (new) |
| :--- | :--- | :--- | :--- |
| `text_runs.total_idml` | IDML Stories/*.xml | — | `walk_idml_inventory.py` — count CSR with non-empty `<Content>` (anchor: 36) |
| `text_runs.by_paragraph_style[].idml_count` | IDML PSR `AppliedParagraphStyle` | `_walk_story` (line 2347) | wrap as a counter |
| `text_runs.by_paragraph_style[].build_py_count` | build.py `runs=[Run(paragraph_style=...)]` | — | AST: walk `Run(...)` kwargs |
| `text_runs.by_paragraph_style[].sla_itext_count` | SLA `<ITEXT>` per PAGEOBJECT, grouped by `PSTYLE` | `iter_itext` (reader.py:125), `iter_styles` (reader.py:113) | thin wrapper |
| `text_runs.by_paragraph_style[].pdf_word_count` | preview.pdf | `text_render_audit.extract_pdf_words` (line 77) | per-frame: needs pdfplumber bbox-in-frame join |
| `text_runs.every_idml_run_present_in_build_py` | IDML CSR ↔ build.py Run | `_walk_csr` (line 2566) for IDML side | AST walker for build side; set equality on `(text, font, int(fontsize))` |
| `frames.text_frames[].anname/idml_position_mm` | IDML TextFrame, `ItemTransform` + `PathPointArray` | `idml_inventory._bbox_from_element` (line 143) returns `[x,y,w,h]` in pt; convert to mm via `_pt_to_mm` (idml_to_dsl.py:381) | — |
| `frames.text_frames[].build_py_position_mm` | build.py `x_mm/y_mm/w_mm/h_mm` kwargs | — | AST kwarg extraction |
| `frames.text_frames[].sla_pageobject_present` | SLA `ANNAME == anname` | `reader.find_by_anname` (line 62) | — |
| `frames.text_frames[].sla_storytext_runs` | SLA `ITEXT` count under PAGEOBJECT | `reader.iter_itext(frame)` (line 125) | — |
| `frames.image_frames[].idml_link` | IDML `<Image href="file:...">` basename | `tools/links_export.py` (existing manifest at `shared/assets/<slug>/links_export.yml`) | reuse manifest |
| `frames.image_frames[].build_py_image_ref` | build.py `image='...'` kwarg | `baseline_image_audit._extract_imageframes_from_build_py` (line 149) | reuse |
| `frames.image_frames[].sla_pfile_present` | SLA PAGEOBJECT `PFILE` attr | `frame.get("PFILE")` | trivial |
| `frames.image_frames[].pdf_image_present` | preview.pdf | `baseline_image_audit._parse_pdfimages_list` (line 44) | count by page; match by w×h within ±5% |
| `paragraph_styles[].idml` | IDML Resources/Styles.xml | `_read_paragraph_styles_from_xml` (idml_to_dsl.py:1076) | reuse |
| `paragraph_styles[].build_py` | build.py `add_para_style(ParaStyle(name=...))` | — | AST: walk `add_para_style` Call nodes |
| `paragraph_styles[].sla_pstyle_present` | SLA `<STYLE NAME=...>` | `reader.iter_styles` (line 113) | trivial |
| `colors[].idml` + `cmyk` | IDML Resources/Graphic.xml `<Color Space="CMYK" ...>` | `_emit_colors_from_xml` (idml_to_dsl.py:881) | reuse parse, drop emit |
| `colors[].build_py_extra_color` | `doc.add_color(name, cmyk=(...))` | — | AST |
| `colors[].sla_color_present` | SLA `<COLOR NAME=...>` | `reader.iter_colors` (line 108) | trivial |
| `assets[].basename/on_disk/classified` | `links_export.yml` + `meta.yml::asset_policy` (P11 embedded/external buckets) | `asset_extraction_audit.audit` (line 236) | reuse |
| `assets[].referenced_from_frames` | build.py `ImageFrame(image=...)` + `inline_image_data=` | — | join build.py extractor output |
| `words.baseline_pdf_count` / `preview_pdf_count` | both PDFs | `text_render_audit.extract_pdf_words` (line 77) | trivial; anchor=450/450 |
| `words.missing_from_preview` / `extra_in_preview` | set diff | — | trivial |

## Calibration baseline (26-03 Leporello, verbatim from disk)

IDML `originals/26-03-Leporello z-Falz 99x210 6-seitig zweigeteiltes Cover Ordner/...zweigeteiltes Cover.idml`:
- Elements: TextFrame=23, Rectangle=25, Polygon=34, Oval=1, GraphicLine=4, Group=14, Image=3, PDF=7, EPS=0, Link=10
- `<CharacterStyleRange>`=40 (of which 36 have non-empty `<Content>`); `<ParagraphStyleRange>`=25
- `Resources/` `<ParagraphStyle>`=6; `<Color>`=15
- (Note: ISSUE.md sample schema cited `text_runs.total_idml: 437`. The actual leporello count is 36 non-empty CSR runs across the spread. The 437 in ISSUE.md appears to be illustrative / from a different template — flag this for the planner; do NOT hard-code 437 as expected.)

build.py `templates/26-03-.../build.py` (1135 lines): 23 TextFrame, 10 ImageFrame, 16 Polygon, 34 PolyLine, 6 `add_para_style`, 3 `add_color`, 104 `Run(`, 83 `anname=`.

template.sla: 83 PAGEOBJECT, 14 STYLE, 10 COLOR, 69 ITEXT total, 3 PAGEOBJECT with PFILE.

baseline.pdf: 450 words. preview.pdf: 450 words. pdfimages reports 13 image rows (5 image + 4 smask + 4 jpeg-image variants) across 2 pages.

`shared/assets/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/` (anchor's external assets): `ziesel.jpg`, `green-pine-trees-covered-with-fog.jpg`, `plakat-dunkel-fuer-flyer.png`, `gruene-logo-bund-weiss-cmyk.{pdf,png}`, plus social-media icon family (`facebook/instagram/tiktok/x/bluesky-weiss/mail-weiss/website-weiss/social-media-icons-weiss` `.pdf` & `.png`) and composite-AI splits (`...--ai-Social Media Icons weiss--{0,1,2}.pdf`), `composite_ai_split.yml`, `links_export.yml`.

Verbatim sample of leporello `page.add(...)` calls (line 174–234), demonstrating pure-kwarg pattern AST can parse:
```python
    page0.add(Polygon(x_mm=-1.8236, y_mm=-1.8236, w_mm=300.8236, h_mm=213.6472,
                       anname='u1ae', layer=0, fill='Dunkelgrün'))
    page0.add(ImageFrame(x_mm=198, y_mm=-1.8, w_mm=101, h_mm=106.8,
                          anname='u514', layer=0,
                          image='../../shared/assets/26-03-.../ziesel.jpg',
                          local_scale=(0.430959, 0.430959), scale_type=1))
    page0.add(TextFrame(x_mm=204.6586, y_mm=151.5858, w_mm=86.84, h_mm=16.3815,
                         anname='u155', layer=0, style='idml/normalparagraphstyle',
                         runs=[Run(text='Mehrzeilige Subheadline –', font='Gotham Narrow Book',
                                   fontsize=18, fcolor='White', ...), ...],
                         trail_attrs={'LINESPMode': '2', 'LINESP': '18.96350262577446'}))
```
Inline-image `inline_image_data='...base64...'` (line 194 onward) is also literal-only — AST safe.

## CLI / entry-point plug

- `bin/idml-import` (13 lines) just `sys.exit(main(sys.argv[1:]))` of `tools/idml_import_driver.py::main`.
- Driver's `--scaffold-only` branch is `idml_import_driver.py:517–528`: runs render-gallery + convergence-review + writes import_report, then returns 0. **Insert inventory emission between lines 519 and 520** (after first render, before review write), call into `tools/inventory_extract.py` writing to `templates/<slug>/SCAFFOLD_INVENTORY.yml`.
- `_scaffold_template_dir` (line 187) is where meta.yml is written. The inventory needs build.py + template.sla + preview.pdf to all exist first, so emission belongs in the post-render path, not next to meta.yml.

## Standard stack (existing, no new deps)
| Library | Version | Purpose | Source |
| :--- | :--- | :--- | :--- |
| `lxml` | 5.4.0 | XML parse (IDML + SLA) | already in tools/idml_to_dsl.py, tools/sla_lib/reader.py |
| `pdfplumber` | 0.11.9 | word positions in PDF | tools/text_position_audit.py, tools/line_spacing_audit.py |
| `pyyaml` | 6.0.3 | YAML I/O | every audit tool |
| `pdftotext` | poppler | word text/count | tools/text_render_audit.py |
| `pdfimages` | poppler | raster placements | tools/baseline_image_audit.py |
| `ast` | stdlib | build.py walker | tools/baseline_image_audit.py:149 already uses it |

## Don't hand-roll
| Problem | Don't build | Use instead |
| :--- | :--- | :--- |
| IDML spread element walker | new tree-walker | extend `tools/idml_inventory.py::_collect_spread_items` |
| IDML CSR → (text, font, size) | new XML parser | call `_walk_csr` from `tools/idml_to_dsl.py` |
| SLA PAGEOBJECT lookup | new `lxml.parse` | use `tools/sla_lib/reader.py::SLADocument` |
| build.py ImageFrame extraction | new regex | reuse `baseline_image_audit._extract_imageframes_from_build_py` |
| PDF word count | new pdftotext wrapper | call `text_render_audit.extract_pdf_words` |
| pdfimages parsing | new regex | call `baseline_image_audit._parse_pdfimages_list` |
| Links manifest | new walk | read `shared/assets/<slug>/links_export.yml` (already on disk) |

## Common pitfalls

**1. IDML `Self` ID drift across re-exports.** ISSUE.md / CONTEXT.md risk #2: re-exporting the IDML in InDesign reissues `Self` attributes. Mitigation: secondary key `(kind, round(mm_position, 1))` — already used by `idml_inventory._bbox_from_element` (line 143). Schema must store both.

**2. pdfplumber word reordering across columns.** `pdftotext -layout` reads columns left-to-right; pdfplumber preserves PDF stream order. For "word in wrong frame" detection, use bbox-in-frame join, not word index. For v1 (string match), use sorted-set diff. Warning sign: `extra_in_preview == missing_from_preview` of same words (= reorder, not loss).

**3. Build.py emits `PolyLine` for falz/foldlines** (34 in anchor). These have NO `anname` and no IDML counterpart — they are manually added post-bootstrap (see build.py docstring lines 11–13 referencing `kandidat-falzflyer-din-lang/build.py`). Schema must mark these as "extra-by-design" and the gate must not flag them.

**4. pdfimages reports smasks separately.** Anchor preview has 13 pdfimages rows but only ~8 logical images (some are jpeg+smask pairs). When comparing `pdf_image_present`, group by `(page, x-ppi, y-ppi, w, h)` rather than counting rows.

**5. Composite-AI assets reference one physical file from N frames.** `shared/assets/.../composite_ai_split.yml` already records the split. Inventory: list the composite once under `assets[]`, list each split asset once with `parent_composite` field, and let `referenced_from_frames` carry the N annames.

**6. AST extraction of nested `Run(...)` inside `runs=[...]`.** The `runs` kwarg is a list of `Call(func=Name('Run'), keywords=...)` nodes. `ast.literal_eval` does NOT handle Call nodes — must walk manually. `baseline_image_audit._extract_imageframes_from_build_py` does the same dance for `image=...` and is a working template.

**7. `inline_image_data='AABBxH...'` strings are very large.** Don't carry the base64 payload in the inventory — hash it (sha256) and record the hash + byte-length only.

**8. `kandidat-falzflyer-din-lang-gruenes-cover-v2` shares an IDML bundle with the anchor.** Different slug, different build.py, same IDML source under `26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner`. Inventory is template-scoped (by slug), not IDML-scoped. The IDML path lives in `meta.yml` only; the inventory schema does not need to encode it.

**9. `idml-import` skill has banned-phrase list (lines 165–183).** Both scaffold and tune skills must inherit it. `tools/sop_lint.py` is the lint enforcer — verify it still runs on output from both new skills.

**10. P11 asset policy (embedded vs external) is a hard rule.** `meta.yml::asset_policy` has three buckets; `shipped:` MUST be empty. The inventory's `assets[].classified` field must read from this bucket assignment, not invent a new taxonomy. See `.claude/skills/idml-import/asset_policy.md`.

## Environment availability
| Dependency | Required by | Available | Version |
| :--- | :--- | :--- | :--- |
| `pdftotext` | walk_pdf word count | yes | `/usr/bin/pdftotext` (poppler) |
| `pdfimages` | walk_pdf image list | yes | `/usr/bin/pdfimages` (poppler) |
| `pdfplumber` | optional word positions | yes | 0.11.9 |
| `lxml` | walk_idml + walk_sla | yes | 5.4.0 |
| `pyyaml` | inventory I/O | yes | 6.0.3 |
| `simple_idml` | (only needed by `idml_to_dsl.py`, not the inventory walker) | yes (1.3.1, per Dockerfile.claude) | n/a |
| `scribus` | rendering during scaffold | required by `bin/idml-import`'s preflight | (assume installed; gate already enforces) |

## Project Constraints (from `/workspace/CLAUDE.md`)
No `CLAUDE.md` exists at `/workspace/` root (no project-level directives file). `.claude/skills/idml-import/SKILL.md` is the de-facto SOP for this surface. CONTEXT.md's "Stage 2 forbidden paths" constraint must be mechanically enforceable — recommend a pre-commit hook script `tools/check_stage2_forbidden_paths.py` that errors when a tune-agent commit touches `tools/idml_to_dsl.py` or `tools/sla_lib/**`.

## Risks & unknowns for the planner

1. **`SCAFFOLD_INVENTORY.yml` schema vs ISSUE.md's `total_idml: 437`.** The illustrative number does not match the anchor (36 non-empty CSR runs). The planner should treat the issue's YAML as schema-shape-only, not number-of-truth. Calibration step #2 in CONTEXT.md ("hand-verify every counted element is real") covers this.

2. **inject.yml ↔ build.py reconciliation.** CONTEXT.md open question #4: where does `inject.yml` live in the schema? `tools/reconcile_build_py.py <slug>` (`.claude/skills/idml-import/SKILL.md:121`) materializes inject.yml into build.py. Two options: (a) inventory walks the reconciled build.py only (treats inject.yml as transparent); (b) inventory records both the pre-inject build.py text and inject.yml deltas as separate columns. Option (a) is simpler and matches the "tuning edits build.py OR inject.yml" model — recommend (a).

3. **TOLERANCES.yml format and gate.** CONTEXT.md proposes `{anname: {axis: pixels, justification: str}}`. The inventory diff needs to read this to suppress expected per-element drift. Suggest gate logic: a Stage 2 diff is allowed iff every position-axis-delta is either ≤ TOLERANCES entry pixels OR within global `±0.5mm`.

4. **Falz/PolyLine emissions.** 34 PolyLine calls in anchor have no IDML counterpart. The inventory's `frames.polygon_frames` (per ISSUE.md schema) should include a `source: manual` flag for these to keep the gate honest. Otherwise the gate flags 34 false-positive "extras".

5. **`idml-import` skill deprecation surface.** `.claude/skills/idml-import/` has 6 files. Deprecation stub vs hard-delete: CONTEXT.md doesn't specify. Recommend keeping a 30-line `SKILL.md` redirect (Read tool still works) and moving the 5 sub-docs to whichever new skill owns them (asset_policy → scaffold; inject_protocol + tolerance_protocol → tune; classification + pattern_library → scaffold).

6. **`/workspace/templates/26-03-leporello-...` is NOT in the worktree.** The worktree at `/workspace/.worktrees/40-.../templates/` lists 11 other templates but not the anchor. Execution will need either to materialize it into the worktree, or run inventory tests pointing at the main workspace path. Planner: pick one and pin it.

## Sources
- HIGH: codebase analysis (`tools/idml_to_dsl.py`, `tools/idml_inventory.py`, `tools/sla_lib/reader.py`, `tools/sla_lib/builder/primitives.py`, `tools/idml_import_driver.py`, `tools/baseline_image_audit.py`, `tools/text_render_audit.py`, `tools/text_position_audit.py`, `tools/line_spacing_audit.py`, `.claude/skills/idml-import/SKILL.md`); on-disk anchor (`/workspace/templates/26-03-.../build.py`, `template.sla`, `preview.pdf`, `baseline.pdf`); IDML source (`/workspace/originals/.../zweigeteiltes Cover.idml`).
- MEDIUM: count parity preview.pdf ↔ baseline.pdf=450 (string-only word count via `pdftotext | wc -w` — pdfplumber may yield slightly different tokenization).

## Metadata
- Confidence: HIGH overall — every count and code reference is grounded in a read of the relevant file at the cited line.
- Sub-agents used: none (executed inline; the codebase questions were specific enough that direct reads were faster than dispatching).
- Raw research files: none separate; this RESEARCH.md is the synthesis directly.
