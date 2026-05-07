# ADR-001: Multi-input readiness for sla_lib DSL

## Status

Accepted — issue #5 (2026-05-07)

## Context

`tools/sla_lib/builder/` is the single sanctioned path for emitting Scribus SLA XML.
`build.py` files are **always AI-authored** (CONTEXT.md decision 1); the source input
may be:

1. **SLA** — current path via `tools/sla_to_dsl.py` (implemented)
2. **PDF** — per-glyph font/color extraction → frame inference (deferred)
3. **InDesign IDML** — named styles, spreads, linked stories (deferred)
4. **Spec brief** — a structured YAML file (`shared/template-spec.schema.yaml`) (deferred)

Converters for paths 2–4 are **not implemented in this issue** (CONTEXT.md decision 3).
This ADR captures the DSL-side contract each deferred converter can rely on, so future
converter issues reference this document instead of re-debating the contract.

Visual diff against committed `templates/<id>/baseline.pdf` (via `bin/validate --ci`)
is the correctness gate. Byte-equivalence of rebuilt SLA is not required unless the
`--strict-bytes` flag is passed to `tools/sla_to_dsl.py`.

---

## DSL contract for SLA input (current path)

These invariants must not regress across any future DSL change.

### Closed override sets stay closed

Four closed sets are validated in `tools/sla_lib/builder/primitives.py`:

| Set name | Location | Purpose |
|---|---|---|
| `PARAGRAPH_OVERRIDE_ATTRS` | `primitives.py:50` | Keys allowed on `_Frame.trail_attrs` / run-level para overrides |
| `DEFAULTSTYLE_OVERRIDE_ATTRS` | `primitives.py:63` | Keys allowed in `TextFrame.default_style_attrs` |
| `VAR_OVERRIDE_ATTRS` | `primitives.py:79` | Keys allowed in `Run.var_attrs` |
| `PAGEOBJECT_HANDLED_PRIM` | `sla_to_dsl.py:362` | PAGEOBJECT attributes the converter handles natively |

**Invariant:** converters MUST NOT drop unrecognised attributes silently. The SLA converter
raises `UnhandledElement` if a PAGEOBJECT attribute is outside `PAGEOBJECT_HANDLED_PRIM`.
Future converters must extend these sets via PR review — never work around them. No
`raw_attrs={}` escape hatch exists on frames, styles, or runs.

### Inline-image base64 round-trip preserved

`ImageFrame(inline_image_data=b"...")` encodes the binary blob in base64 and emits it as
`<IOBJ>` content. The converter reads it back verbatim. Sub-ulp precision image frames
(e.g. Zeitung frames with `HEIGHT='27.7755590551181'`) retain their exact pt values via
`xpos_pt=`/`ypos_pt=`/`width_pt=`/`height_pt=` opt-in kwargs.

### pt-geometry overrides are opt-in, not default

`xpos_pt`, `ypos_pt`, `width_pt`, `height_pt` on `_Frame` are opt-in overrides.
The SLA converter emits them only when `repr(mm_value * MM_TO_PT) != repr(pt_value)`
(non-recoverable float precision). The `--strict-bytes` CLI flag on `tools/sla_to_dsl.py`
reverts to always-emitting all 8 geometry kwargs (for callers that need byte-equivalent
output). Future converters: **emit mm only** unless sub-ulp precision is required.

### ItemID chain pre-allocation preserved

`TextFrame.link_to(other)` pre-allocates ItemIDs in chain order before XML emit so
`NEXTITEM` / `BACKITEM` attributes resolve correctly. Future converters that produce
linked-frame stories must call `link_to` in reading order before adding frames to a `Page`.

### HCMS / PDF ICC pass-through preserved

`Document(hcms=True)` plus `extra_doc_attrs={"CMSSettings": ..., "DefaultRGBColorProfile": ...}`
passes ICC profile names through to the SLA `DOCUMENT` element. Future converters must
not strip these keys; they control Scribus's colour management and PDF export intent.

### Clip-rect auto-generation

When `TextFrame(clip_edit=True)` is used without an explicit `custom_path=` and without
`corner_radius_mm`, the DSL auto-emits `FRTYPE=3` with a canonical axis-aligned rectangle
path matching the frame dimensions. Future converters may omit `custom_path=` for
rectangular clip frames; the DSL regenerates the path automatically.

---

## DSL contract for PDF input (deferred converter)

**What PDF input carries:**

- Per-glyph font name, size, colour (post-ICC CMYK or RGB)
- Word/character bounding boxes (not frame extents)
- Image placement and pixel data
- No paragraph-style identity; no story-chain links; no named brand colours

**What PDF input loses:**

- Paragraph-style names → AI must infer style from font+size+colour clusters
- Frame extents → must be reconstructed by clustering glyph positions (pdfplumber / pymupdf)
- Linked text chains → not reliably recoverable from PDF; PDF input is recommended for
  single-frame layouts (posters, postcards) only; chained stories should use spec or IDML input
- Named brand colours → requires side-input brand profile for snap-to-nearest CMYK lookup

**DSL guarantees for PDF converter:**

- `style=None` + `default_style_attrs={'FONT': ..., 'FONTSIZE': ..., 'FCOLOR': ...}` is a
  **first-class path** on `TextFrame`. The converter does not need to match every glyph to a
  named brand style; absolute per-frame styling works.
- Absolute `x_mm / y_mm / w_mm / h_mm` is **sufficient** for every primitive; `anchor=` is
  optional. Confirmed by REVIEW.md Gemini C-1.
- `Anchor` form is irrelevant for PDF input — emit absolute mm coords only.
- Brand-colour snapping (`Color.DUNKELGRUEN` → CMYK 85/35/95/10) is the **converter's
  responsibility**; the DSL accepts any CMYK or RGB string that `Document.add_color()` has
  registered.
- Run-level formatting (`Run(font=..., fontsize=..., fcolor=...)`) is available for mixed-style
  text within a single frame.

**No DSL changes are needed for the PDF path.** The current surface is sufficient.

---

## DSL contract for InDesign IDML input (deferred converter)

**What IDML input carries:**

- Named paragraph styles and character styles (direct mapping to DSL)
- MasterSpreads (map to `Document.add_master()`)
- Stories with linked-frame chains (`ParentStory` + `NEXTITEM` linkage)
- `CharacterStyleRange` run-level formatting
- Drop caps, paragraph rules, baseline shift, paragraph effect offset

**DSL mapping table:**

| IDML construct | DSL construct | Notes |
|---|---|---|
| Named paragraph style | `Run.paragraph_style=` + `doc.add_para_style(ParaStyle(...))` | Converter provides a brand-style remap table |
| Named character style | `Run.char_style=` + `doc.add_char_style(CharStyle(...))` | Same remap table |
| MasterSpread | `doc.add_master(...)` + `Document.add_facing_pages_masters(...)` | Zeitung is the corpus reference |
| Linked story (`ParentStory`) | `TextFrame.link_to(other)` | Pre-allocate in reading order |
| `CharacterStyleRange` | `Run(font=..., fontsize=..., fcolor=...)` | DSL is ready |
| Drop cap | `ParaStyle(drop_cap=True, drop_lines=N)` at `styles.py:59-60` | Field exists |
| Baseline shift | `ParaStyle(baseline_offset=N)` at `styles.py:86` | Field exists |
| Paragraph effect | `ParaStyle(paragraph_effect_offset=N)` at `styles.py:87` | Field exists |

**Known gaps (P2):**

- Master-page text chain `NEXTITEM`/`BACKITEM` patching is **not applied** in
  `_emit_master_item()` (`document.py:967-976`). Chained text on master pages will not
  link correctly. Zeitung's masters carry no text chains so this does not affect current
  templates, but it blocks fully-linked master stories from IDML. Filed as P2 (REVIEW.md
  Codex B-2).
- InDesign paragraph rules (decorative rules above/below paragraphs) have no `ParaStyle`
  field. These are rare in the Grüne NÖ corpus; add field if encountered.

**DSL guarantees for IDML converter:**

- `style=` + `paragraph_style=` channels in `Run` are the canonical named-style path.
- `TextFrame.link_to()` handles story chains when called in document order.
- `doc.add_master()` / `doc.add_facing_pages_masters()` handles spread layout.

---

## DSL contract for spec input (deferred converter)

**What spec input carries:**

A structured YAML file (`shared/template-spec.schema.yaml`) describing page layout, brand
reference, content slots, and optional style overrides. See `docs/spec-input-schema.md` for
the full schema and worked example.

**DSL mapping:**

| Spec key | DSL construct |
|---|---|
| `brand: gruene-noe` | `Document(brand=Brand.gruene_noe())` |
| `styles.<name>.parent` | `doc.add_para_style(ParaStyle(name=..., PARENT=...))` |
| `pages[].layout=cover` | `Page` + `PageBackground` block + `Impressum` block |
| `pages[].headline.lines[]` | `TextFrame` with N `Run` children |
| `pages[].page_number` | `PageNumber` block |
| `pages[].body_columns` | `ColumnTextStory` block |
| Symbolic colour `brand.primary` | `Color.DUNKELGRUEN` (converter resolves at emit time) |

**DSL guarantees for spec converter:**

- Named layouts live in the template's `build.py` as plain Python functions taking a `Page`
  and emitting frames — no new DSL construct is needed for named layouts.
- Symbolic colour references (`brand.primary`) resolve to `Color.DUNKELGRUEN` style strings;
  the DSL accepts any registered colour name string.
- `Brand.gruene_noe()` is the entry point; no separate brand-initialisation call needed.
- The 5 evidence-driven blocks (`PageNumber`, `Impressum`, `PageBackground`, `ContactBlock`,
  `ColumnTextStory`) cover the recurring spec constructs from the existing corpus.

---

## Closed override sets — invariants

The four closed sets listed in the SLA contract section are **invariants for all input
paths**, not just SLA. Their purpose is to ensure the DSL remains a verifiable target for
LLM emission: if a set is exhaustive, an LLM emitter gets an error with the full allowed
list when it emits an unsupported key, and can recover.

**Rule:** Any new PAGEOBJECT attribute, paragraph-style key, default-style key, or var-key
that a converter needs to emit **must** be added to the appropriate closed set via a PR that
also adds a test. Never work around the set by accepting arbitrary dicts.

**`extra_doc_attrs`** is the one general-purpose pass-through and is intentionally narrow:
it only carries `DOCUMENT`-level attributes (locale defaults, ICC profile names, runtime
state). It does not allow per-frame or per-style ad-hoc attributes.

---

## Open gaps

The following gaps were flagged by the REVIEW.md (issue #5) and could not be closed
within this issue's scope. Each is P2 and is scheduled for a follow-up issue.

| Gap | Source | Priority | Follow-up |
|---|---|---|---|
| `load_ci()` global singleton is path-blind (first-call cache ignores subsequent path args) | REVIEW.md Codex B-1 (`ci.py:127-135`) | P2 | Separate issue |
| Master-page text chain `NEXTITEM`/`BACKITEM` links not emitted from `_emit_master_item()` | REVIEW.md Codex B-2 (`document.py:967-976`) | P2 | Separate issue |
| Soft-shadow erase round-trip: key mismatch between emit and re-read | REVIEW.md Codex B-3 | P2 | Separate issue |
| `unit` and `first_page_num` kwargs silently no-op in Document emit | REVIEW.md Claude A-12 | P3 | Separate issue |
| InDesign paragraph rules (above/below) have no `ParaStyle` field | This ADR analysis | P3 | Add if encountered |
| Named-layout versioning for spec input | `docs/spec-input-schema.md` | P3 | Separate issue |

---

## Consequences

1. **DSL changes are gated on multi-input compatibility.** Before adding or removing any
   public DSL field, check this ADR: does the change break a guaranteed contract for PDF,
   IDML, or spec input?

2. **Future input converter issues reference this ADR** rather than re-deriving the
   contract. The ADR sections above are the authoritative description of what each
   converter may rely on.

3. **Closed sets must be extended, never bypassed.** Any PR that adds a new Scribus
   attribute to a converter must simultaneously extend the relevant closed set and add a
   test. This keeps the DSL's LLM-emission error messages accurate.

4. **No DSL changes required before PDF or IDML converters land.** The current surface
   (after issue #5 P1 hardening) is sufficient for all three deferred paths. The blockers
   are the converter implementations themselves, not the DSL.
