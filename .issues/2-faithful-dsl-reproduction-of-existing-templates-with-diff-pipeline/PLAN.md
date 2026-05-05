---
issue: 2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline
phase: plan
generated: 2026-05-05
---

# PLAN — Faithful DSL reproduction with diff pipeline

## Executor briefing

You are rebuilding three existing Scribus templates (Postkarte A6, Plakat A1, Grüne Zeitung A4) as DSL `build.py` scripts, byte-equivalent up to documented tolerances, plus a structural diff (`tools/sla_diff.py`) and a visual diff (`tools/visual_diff.py`) that prove equivalence and gate CI.

**Read first, in order:**
1. `.issues/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/ISSUE.md` — scope and acceptance criteria.
2. `.issues/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/CONTEXT.md` — six locked decisions (D1–D6); these are non-negotiable.
3. `.issues/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/RESEARCH.md` — 1250 lines of measured inventory and gap analysis. Authoritative.
4. `.research/01-sla-format.md` — Scribus SLA format reference (PAGEOBJECT/STYLE/inheritance rules).
5. `.research/04-scribus-multipage-masters.md` — multi-page + master rules (relevant for Zeitung).

**Load-bearing source (extend, don't rewrite):**
- `tools/sla_lib/builder/{__init__.py,document.py,primitives.py,blocks.py,ci.py}` — DSL emitter.
- `tools/sla_lib/reader.py` — SLA parser; needed by converter and `sla_diff`.
- `tools/check_ci.py` — `Issue` / `CIDriftReport` dataclass shape; mirror it in `sla_diff`.
- `tools/render.py`, `tools/_export_pdf.py` — sanctioned headless PDF render.
- `tools/sla_lib/tests/` — extend with new test modules per phase.
- `.github/workflows/pages.yml` — extend with `validate-reproductions` step.

**Originals (immutable, ground truth at workspace root):**
- `postkarte-vorlage-original.sla`
- `plakat-a1-hochformat-original.sla`
- `gruene-zeitung-vorlage-original.sla`

**Template directories (current placeholders, you will replace their `build.py` and add `baseline.pdf` + `diff.yml`):**
- `templates/postkarte-a6-kampagne/`
- `templates/plakat-event/` — **rename to `templates/plakat-a1-hochformat/`** in Phase 7.
- `templates/zeitung-a4-grun/`

**Resolved open questions** (do not re-surface to the user; bake in):
- Mapping `templates/<id>` ↔ original SLA: add `original_sla:` key (path relative to repo root) to each `templates/<id>/meta.yml`.
- Inline-image handling: **Option A** — converter extracts to sidecar PNG under `templates/<id>/assets/<frame_anname>_<idx>.png`; emits `ImageFrame(image='assets/...png', ...)`.
- Orphan-scratch FRAMEOBJECTs (`OwnPage=-1`): converter drops silently; `sla_diff` treats their presence as `info`.
- `check_ci.py` per-template allowlist lives in `templates/<id>/meta.yml` under `ci_overrides: { non_ci_styles: [...], non_ci_colors: [...] }`.
- Diff exit codes: `sla_diff` exit 1 on `critical` (page-count, missing/added frame, wrong PTYPE), exit 0 otherwise; `--strict` exits 1 on `warning` too. `visual_diff` exits 1 on any per-page or per-region threshold breach.
- `tools/sla_to_dsl.py` is a **one-shot bootstrap** generator. Run manually to seed `build.py`; thereafter `build.py` is hand-edited and is the source of truth. The converter is **NOT** run in CI.
- Soft-hyphens are an **escape hatch** for words Scribus's hyphen dict gets wrong; document this in the `tools/sla_lib/builder/__init__.py` module docstring (or a new `docs/dsl-reference.md` excerpt).
- `templates/<id>/diff.yml` schema: bless RESEARCH.md §visual_diff schema verbatim. Document in new `docs/diff-tolerance.md`.

**Commit format:** Conventional commits, no issue prefix (no `.issues/config.yaml` exists). Examples: `feat(dsl): add Run dataclass with per-run formatting`, `feat(sla_diff): add structural diff tool`, `test(converter): round-trip postkarte`.

**No "claude" attribution** in commits, code, or filenames (per user memory).

## Phase gates summary

| Phase | Goal | Gate (must be GREEN to advance) |
|---|---|---|
| 0 | `sla_diff` foundation | All synthetic-fixture unit tests pass; running `sla_diff` on each original against itself reports zero critical and zero warning. |
| 1 | DSL extensions (typed APIs) | All new typed DSL primitives have unit tests; `python -m unittest discover tools/sla_lib/tests` passes. |
| 2 | Postkarte reproduction | `python templates/postkarte-a6-kampagne/build.py` produces `template.sla`; `sla_diff` against original reports zero critical and zero warning. |
| 3 | Plakat A1 reproduction | Same as Phase 2 for Plakat. Soft-hyphens (7 occurrences) round-trip verbatim. |
| 4 | Zeitung reproduction | Same as Phase 2 for Zeitung; **all 14 linked chains intact** (chain hash matches); 12 `<var pgno/>` round-trip; LANGUAGE-on-STYLE inheritance matches original. |
| 5 | `visual_diff` foundation + baselines | All three `templates/<id>/baseline.pdf` committed; `visual_diff` against each baseline < 1% mismatch per page (per-region tolerances tuned where required). |
| 6 | CI integration | `validate-reproductions` workflow step green on a deliberately-clean branch; deliberate-drift branch fails CI; total job runtime < 5 min at 96 dpi. |
| 7 | Cleanup & cutover | Gallery serves only DSL-built `template.sla`; originals removed from `site/public/`; `templates/plakat-event/` renamed; README + `docs/` updated. |

Each phase's tasks are below. **Do not advance past a phase whose gate is red.** Treat `risk="high"` tasks as needing explicit verification before marking done.

## Phases

<phase id="0" name="sla_diff foundation">

Build the structural diff first so every subsequent converter iteration has a fast go/no-go signal. RESEARCH.md §sla_diff strategy (lines 832–897) is the authoritative spec.

<task id="0.1" name="Add reader extensions for diff & converter">
**File:** `tools/sla_lib/reader.py`
**Action:** Add five iterators to `SLADocument` so converter and `sla_diff` don't re-parse XML: `iter_pages()`, `iter_masters()`, `iter_layers()`, `iter_colors()`, `iter_styles()`, `iter_charstyles()`. Each returns lxml elements in document order. Reuse the existing parsed tree (`self._tree`); do not re-open the file. Match the signature/style of the existing `iter_itext(frame)` and `pages()` methods.
**Verify:** `python -m unittest tools.sla_lib.tests.test_reader -v` plus a new test in `test_reader.py` asserting that for each of the three originals, the iterator counts match RESEARCH.md §Per-original inventory (e.g. Zeitung `iter_styles` returns 23, Postkarte `iter_colors` returns 8).
**Done:**
- All six iterators added with type hints.
- New tests in `test_reader.py` for each iterator on all three originals.
</task>

<task id="0.2" name="Implement sla_diff normalisation pipeline">
**File:** `tools/sla_diff.py` (new)
**Action:** Implement the 10-step normalisation pipeline from RESEARCH.md §sla_diff strategy (lines 834–855). Steps in order:
1. Parse with `XMLParser(remove_blank_text=False, strip_cdata=False)`.
2. Strip volatile doc-level attrs: `DOCSAVED`, `DOCDATE`, `currentProfile`, autosave timestamps.
3. Renumber ItemIDs sequentially starting at 100_000_000 in document order across PAGEOBJECT + MASTEROBJECT (drop FRAMEOBJECTs first); update every `NEXTITEM`/`BACKITEM`/`WeldSource`/`WeldID` reference via the old→new map in lockstep.
4. Drop FRAMEOBJECTs (orphan scratch; resolved decision).
5. Sort PAGEOBJECTs by `(int(OwnPage), float(YPOS), float(XPOS))`; MASTEROBJECTs by `(OnMasterPage, YPOS, XPOS)`.
6. Round all float-shaped attrs to 6 decimals (use regex `^-?\d+\.\d+$`); also round each coordinate inside `path=`/`copath=` via a path tokeniser.
7. Sort element attribute order alphabetically before serialise.
8. Drop default-equivalent attrs: `LOCALSCX/LOCALSCY=1`, `LOCALX/LOCALY=0`, `LOCALROT=0`, `SCALETYPE=1`, `RATIO=1`, `PICART=1`, `ROT=0`, `NEXTITEM=-1`, `BACKITEM=-1`, `LINESPMode=2`, `LINESP=15`, `gXpos/gYpos == XPOS/YPOS`, `gWidth=0`, `gHeight=0`.
9. Strip `PAGEXPOS`/`PAGEYPOS` from PAGE/MASTERPAGE; re-base every PAGEOBJECT XPOS/YPOS to page-local coords.
10. Sort COLOR / STYLE / CHARSTYLE / LAYERS lists by NAME.
**Verify:** Each step has a focused unit test in `tools/sla_lib/tests/test_sla_diff.py` using a small synthetic SLA fixture (build via the DSL itself). E.g. `test_renumbering_preserves_chain_links`, `test_path_coords_rounded`, `test_pagexpos_dropped`.
**Done:**
- `normalise(tree) -> tree` callable.
- 10 unit tests, one per pipeline step, all green.
- Deterministic output (same input → same normalised output bytes).
</task>

<task id="0.3" name="Implement diff comparator with severity rules" risk="high">
**File:** `tools/sla_diff.py`
**Action:** On top of `normalise`, implement comparator. Mirror `Issue` / `CIDriftReport` dataclass shape from `tools/check_ci.py` (RESEARCH.md §Reusable Components). Severity table from RESEARCH.md §Severity rules (lines 856–863):
- **critical**: ANZPAGES differs; PAGEWIDTH/HEIGHT differ > 0.01 pt; bleed differs; missing PAGE for an MNAM; PAGEOBJECT count per OwnPage differs; PTYPE mismatch; FRTYPE mismatch (after rectangle-equivalence rule); chain topology hash mismatch.
- **warning**: XPOS/YPOS drift > 0.5 pt (after page-local norm); WIDTH/HEIGHT drift > 0.5 pt; FONTSIZE drift > 0.5 pt on STYLE or ITEXT; FCOLOR / PCOLOR mismatch; ROT > 0.5°; missing/extra COLOR or STYLE; LAYER ID differs.
- **info**: ItemID literal value differs after renumber (should be silent); ANNAME differs; default-equivalent attr drift; FRAMEOBJECT count differs; PageSets default-content differs.
Implement the **rectangle-equivalence rule** (RESEARCH.md lines 865–869): a frame is "rectangular" if `path=` matches `M0 0 L<W> 0 L<W> <H> L0 <H> L0 0 Z` (CW) or `M0 0 L0 <H> L<W> <H> L<W> 0 L0 0 Z` (CCW); if both sides rectangular and `(WIDTH, HEIGHT)` match within 6-decimal tolerance, FRTYPE 0 vs 3 → info.
Implement **linked-chain comparison** (lines 871–876): walk BACKITEM=-1 → NEXTITEM chains; SHA256 over `(OwnPage, page-local XPOS, page-local YPOS, WIDTH, HEIGHT)` tuples; mismatched chain → critical.
Treat `isInlineImage` + `ImageData` on one side and `PFILE` on the other as equivalent if decoded image SHA256 matches (RESEARCH.md pitfall: Embedded PNG round-trip drift, lines 1138–1141); else info.
**Verify:** `tools/sla_lib/tests/test_sla_diff.py` adds:
- `test_self_diff_clean`: each of the three originals diffed against itself reports `critical=0, warning=0`.
- `test_synthetic_position_drift`: ±0.6 pt YPOS shift → warning; ±0.4 pt → info.
- `test_synthetic_page_count_mismatch` → critical.
- `test_rectangle_equivalence_FRTYPE_0_vs_3` → info.
- `test_chain_topology_break` → critical.
- `test_inline_image_pfile_equivalence` → info.
**Done:**
- `diff(left_path, right_path) -> CIDriftReport`-shaped object.
- Unit tests above all green.
- `python tools/sla_diff.py --left <orig> --right <orig>` exits 0 on each original.
</task>

<task id="0.4" name="CLI surface, JSON + Markdown reporters">
**File:** `tools/sla_diff.py`
**Action:** Add `argparse` CLI: `--left PATH`, `--right PATH`, `--json [PATH]`, `--markdown [PATH]`, `--strict` (exit 1 also on warning). Default reporter prints Markdown to stdout. JSON shape matches RESEARCH.md §Output formats (lines 877–893). Exit codes per resolved decision: `0` = no critical (and no warning if `--strict`); `1` otherwise. Emit machine-readable JSON for CI consumption with the schema:
```
{
  "left": "<path>",
  "right": "<path>",
  "summary": {"critical": <int>, "warning": <int>, "info": <int>},
  "issues": [{"severity": "...", "code": "...", "path": "...", "attr": "...", "left": "...", "right": "...", "detail": "..."}]
}
```
**Verify:** `python tools/sla_diff.py --left postkarte-vorlage-original.sla --right postkarte-vorlage-original.sla --json` emits `{"summary":{"critical":0,"warning":0,"info":...}}` and exits 0. With `--strict` flag also exits 0. Run on each of the three originals against itself.
**Done:**
- CLI runnable.
- Self-diff on all three originals: exit 0, summary clean.
</task>

<gate>
- `python -m unittest tools.sla_lib.tests.test_sla_diff` green.
- `python tools/sla_diff.py --left <orig> --right <orig>` exits 0 for all three originals.
- Synthetic fixtures cover every severity rule.
**Do not start Phase 1 until the gate passes.**
</gate>

</phase>

<phase id="1" name="DSL extensions (typed APIs)">

Add every typed primitive the converter will need. RESEARCH.md §DSL gap analysis (lines 568–831) is the authoritative gap list. Each gap is closed with a typed addition (no `raw_attrs` in public API; CONTEXT.md D2). Order is dependency-driven: document-level (1.1–1.4) before frame-level (2.1–2.10). Ship every new API with unit tests on synthetic fixtures.

<task id="1.1" name="DocumentLayer + per-document layer override">
**Files:** `tools/sla_lib/builder/document.py`, `tools/sla_lib/builder/__init__.py` (re-export).
**Action:** Add frozen dataclass `DocumentLayer(name, visible=True, printable=True, editable=True, flow=True, transparent=1.0, blend=0, outline=False, layer_color="#000000")` — RESEARCH.md §1.1 (lines 574–593). Extend `Document.__init__` with `layers: list[DocumentLayer] | None = None`. When set, `_emit_layers()` (currently `document.py:402`-ish) emits the override list and skips the CI 4-layer stack. Default behaviour (when `layers=None`) is unchanged.
**Verify:** New test in `tools/sla_lib/tests/test_dsl_extensions.py`: `test_document_layer_override` builds a Document with `layers=[DocumentLayer(name="Hintergrund")]`, saves, asserts the emitted SLA has exactly one `<LAYERS>` element and that NUMMER=0 NAME="Hintergrund".
**Done:**
- `DocumentLayer` exported from `tools/sla_lib/builder/__init__.py`.
- `_emit_layers` honours override.
- Unit test green.
</task>

<task id="1.2" name="Document.add_color for per-doc custom colors">
**File:** `tools/sla_lib/builder/document.py`, `ci.py` (extend `BrandColor` to accept native RGB).
**Action:** RESEARCH.md §1.2 (lines 596–605). Add `Document.add_color(name, *, rgb=None, cmyk=None, spot=False, register=False)` storing in `self._extra_colors: dict[str, BrandColor]`. Extend `BrandColor` with optional `rgb: tuple[int,int,int] | None = None`; when set, `_emit_colors` emits `SPACE="RGB"` and `<R><G><B>` integer values; otherwise CMYK as today. `_emit_colors` first emits CI palette, then `_extra_colors` in insertion order. `Postkarte` and `Zeitung` both have a `Green` colour with **different RGB triples** — must round-trip per-document.
**Verify:** `test_dsl_extensions.test_add_color_rgb`: build a doc, call `doc.add_color("Green", rgb=(153,102,51))`, save, parse with lxml, assert COLOR element has `SPACE="RGB"`, `R="153"`, `G="102"`, `B="51"`. Negative test: cannot pass both `rgb=` and `cmyk=`.
**Done:**
- `Document.add_color` works for both RGB and CMYK.
- Unit tests green.
</task>

<task id="1.3" name="ParaStyle + CharStyle dataclasses + emit-only-non-None" risk="high">
**Files:** `tools/sla_lib/builder/ci.py` (or new `tools/sla_lib/builder/styles.py`), `document.py`, `__init__.py`.
**Action:** RESEARCH.md §1.3 (lines 607–667). Add `ParaStyle` frozen dataclass with the 31 optional fields enumerated in lines 614–653 (font, fontsize, fcolor, align, parent, linesp, linesp_mode, language, space_before_pt/space_after_pt, first/left/right indents, hyphenation, drop cap, tracking, keep, direction, background, char-style passthrough fontfeatures/features/kern/scalev/fshade, is_default). Add `CharStyle(name, font?, fontsize?, fcolor?, is_default=False)`. Add `Document.add_para_style(s)` and `Document.add_char_style(s)` storing on `self._extra_styles` / `self._extra_charstyles`. Rewrite `_emit_styles` so it **only emits an attribute when the value is not None**: per RESEARCH.md pitfall "STYLE inheritance silently broken" (lines 1127–1131), the current emitter unconditionally writes every default and overrides parent inheritance. Honour `parent`: never emit a value equal to the parent's value. The CI brand styles continue to emit unchanged (they pass through a `BrandStyle → ParaStyle` shim).
**Verify:** `test_dsl_extensions.py`:
- `test_para_style_inheritance_drops_redundant_attr`: parent has fontsize=12; child has parent="parent" and fontsize=None → child's STYLE element has NO FONTSIZE attribute.
- `test_para_style_emits_all_31_attributes` covers each long-tail attr (NACH, VOR, DROP, DROPLIN, INDENT, RMARGIN, FIRST, MinWordTrack, MinGlyphShrink, MaxGlyphExtend, KeepTogether, KeepLinesStart, DIRECTION, BCOLOR, BSHADE, FONTFEATURES, FEATURES, KERN, SCALEV, FSHADE, TXTULP, TXTSTP, TXTSHX, TXTSHY, TXTOUT, TXTULW, TXTSTW, BASEO, ParagraphEffectOffset, Bullet, Numeration, HyphenConsecutiveLines, HyphenWordMin, LINESPMode).
- `test_char_style_emit`.
- `test_default_style_marker_is_default`.
**Done:**
- `ParaStyle`, `CharStyle` exported.
- `_emit_styles` emits only non-None attrs and respects parent inheritance.
- Tests green.
</task>

<task id="1.4" name="Document constructor extras: facing pages, column gap, AUTOTEXT">
**File:** `tools/sla_lib/builder/document.py`.
**Action:** RESEARCH.md §1.4 (lines 670–680). Add to `Document.__init__`: `facing_pages: bool = False`, `column_gap_default_pt: float = 11.0`, `unit: str = "mm"`, `deffont: str = "Gotham Narrow Book"`, `defsize: float = 12`, `first_page_num: int = 1`. Wire `facing_pages` to set BOOK="1" in DOCUMENT (Zeitung needs this). Wire `column_gap_default_pt` to ABSTSPALTEN (Zeitung uses 12, default is 11).

Also fix the **implicit "Normal" auto-master injection** (RESEARCH.md "Potential Conflicts" line 220): `Document._build_xml()` currently injects a `Normal` master if no master named `Normal` exists; change to "inject Normal **only if** `self.masters` is empty" — Zeitung has two masters, neither named `Normal`, and must not get a third.

Also suppress the magenta `BEISPIELSEITE — <label>` text frame when `label=""` (already the case if not set; RESEARCH.md §1.5). Add explicit `Page(suppress_label=True)` if a future template wants to override.
**Verify:** `test_dsl_extensions.py`:
- `test_facing_pages_emits_BOOK_1`.
- `test_column_gap_default_pt_to_ABSTSPALTEN`.
- `test_no_normal_master_injection_when_other_masters_present`.
- `test_no_label_frame_when_label_empty`.
**Done:**
- Constructor extras wired.
- Master auto-injection fixed.
- Tests green.
</task>

<task id="1.5" name="Run dataclass for per-run text formatting" risk="high">
**File:** `tools/sla_lib/builder/primitives.py`.
**Action:** RESEARCH.md §2.1 (lines 690–712). Add frozen dataclass `Run(text, font?, fontsize?, fcolor?, fshade?, fontfeatures?, features?, kern?, underline_position?, strike_position?, char_style?, separator?, var?)` where `separator ∈ {None, "para", "breakline", "tab", "breakcol", "breakframe"}` and `var ∈ {None, "pgno"}`. `TextFrame.runs` accepts `list[Run]` (preferred) and continues to accept the legacy `(text, dict, sep)` tuple for migration but the converter only emits `Run(...)`. Wire into `TextFrame.to_pageobject`: each Run becomes an `<ITEXT>` with overrides; `var="pgno"` emits `<var name="pgno"/>` after the ITEXT/separator; `separator="para"` → `<para/>`, `breakline` → `<breakline/>`, etc.

**Soft-hyphen passthrough (§2.2, lines 715)**: confirm Run.text and TextFrame.text pass `\xad` through verbatim. Add a regression test that builds a frame with `Run(text="ei\xadne gro\xadße")`, saves, parses back, asserts the emitted SLA bytes (read as bytes) contain `b"ei\xadne"`. **Plakat A1 has 7 occurrences** that must round-trip.
**Verify:** `test_dsl_extensions.py`:
- `test_run_per_run_fcolor_fontsize_font_fshade_features_kern`: every CharStyle override emits the corresponding ITEXT attribute.
- `test_run_var_pgno_emits_var_element`.
- `test_run_separators_para_breakline_tab_breakcol_breakframe`.
- `test_soft_hyphen_passthrough` (file-bytes assertion as above).
**Done:**
- `Run` exported.
- All separator and override types emit correctly.
- Soft-hyphen test green.
</task>

<task id="1.6" name="Custom path + fillRule on _Frame" risk="high">
**File:** `tools/sla_lib/builder/primitives.py`.
**Action:** RESEARCH.md §2.4 (lines 728–740). Add to `_Frame`: `custom_path: str | None = None` and `fill_rule: int | None = None`. When `custom_path` is set, primitive emits `FRTYPE="3"` and `path=<custom_path>` and `copath=<custom_path>` (Scribus duplicates path/copath); WIDTH/HEIGHT remain the bbox. `fill_rule` emits as `fillRule` attribute when not None. Without these, the Zeitung's 86 FRTYPE=3 frames cannot round-trip.
**Verify:** `test_dsl_extensions.py`:
- `test_custom_path_sets_FRTYPE_3_and_path_attrs`.
- `test_fill_rule_emitted_when_set`.
- `test_default_path_unchanged_when_custom_path_None` (rect/ellipse paths still computed).
**Done:**
- `custom_path` and `fill_rule` round-trip.
- Tests green.
</task>

<task id="1.7" name="Linked text-frame chains via TextFrame.link_to" risk="high">
**Files:** `tools/sla_lib/builder/primitives.py`, `tools/sla_lib/builder/document.py`.
**Action:** RESEARCH.md §2.5 (lines 742–771) plus RESEARCH.md pitfall "ItemID renumbering breaks linked chains" (lines 1121–1125). Add `TextFrame.next_item: TextFrame | None = None` and method `TextFrame.link_to(other) -> other` (returns `other` for fluent `a.link_to(b).link_to(c)`).

Implement an **ID pre-allocation pass** in `Document._build_xml()` BEFORE `to_pageobject` is called per item:
1. Walk all pages, all items; collect every TextFrame.
2. For each TextFrame whose `next_item is not None`, walk back via the inverse map to find the chain head (BACKITEM=-1). Each chain has exactly one head.
3. Allocate ItemIDs depth-first per chain, head first.
4. Stash the assigned ID on the item (e.g. `item._preallocated_id`). Modify `to_pageobject` to consume it instead of allocating fresh.
5. Emit NEXTITEM/BACKITEM using the pre-allocated map; both ends valid (head BACKITEM=-1, tail NEXTITEM=-1).

Verify the existing `_IdGen` continues to allocate sequential IDs for non-chained items.
**Verify:** `test_dsl_extensions.py`:
- `test_link_to_chain_of_three_emits_NEXTITEM_BACKITEM`: build A→B→C; saved SLA has A.NEXTITEM = B.ItemID, B.BACKITEM = A.ItemID, B.NEXTITEM = C.ItemID, C.BACKITEM = B.ItemID, A.BACKITEM = -1, C.NEXTITEM = -1.
- `test_chain_ids_are_preallocated_before_emit` (no late-binding).
- `test_chain_round_trip_through_sla_diff`: saved chain → `sla_diff` against itself → critical=0.
**Done:**
- `link_to` works.
- Pre-allocation pass robust.
- Round-trip diff clean.
</task>

<task id="1.8" name="Long-tail frame attrs: corner_radius, soft_shadow, text_align, fill_shade">
**File:** `tools/sla_lib/builder/primitives.py`.
**Action:** RESEARCH.md §§2.6–2.10 (lines 773–823).
- Add `_Frame.corner_radius_mm: float = 0`. When > 0, emit FRTYPE=2 and `RADRECT=<pt>` (1 mm = 2.834645669 pt). For round-trip fidelity, the converter passes the original SLA's path verbatim via `custom_path` (Task 1.6) — RADRECT alone doesn't suffice; Scribus stores both.
- Add `_Frame.soft_shadow: SoftShadow | None = None` with `SoftShadow(color, blur_radius_pt=8.504, x_offset_pt=1.984, y_offset_pt=1.984, blend_mode=1, opacity=0.0, shade=100, erase=False, object_trans=False)`. Emit `HASSOFTSHADOW="1"` and 9 `SOFTSHADOW*` attrs only when set.
- Add `TextFrame.text_align: int | None = None` → emits `ALIGN` attribute on PAGEOBJECT (RESEARCH.md "LOW confidence" note line 1204 — verify at implementation time whether this is horizontal or vertical via Scribus source; either way emit verbatim from converter).
- Add `Polygon.fill_shade: int = 100`; emit `SHADE` only when != 100.
**Verify:** `test_dsl_extensions.py`:
- `test_corner_radius_emits_RADRECT_and_FRTYPE_2`.
- `test_soft_shadow_emits_all_9_attrs`.
- `test_text_align_emits_ALIGN_on_pageobject`.
- `test_fill_shade_polygon_omits_when_default`.
**Done:**
- All long-tail attrs round-trip.
- Tests green.
</task>

<gate>
- `python -m unittest discover tools/sla_lib/tests` green.
- Every new typed API has at least one direct test.
- No `raw_attrs` parameter exposed in public DSL surface (`tools/sla_lib/builder/__init__.py` exports inspected by hand).
**Do not start Phase 2 until the gate passes.**
</gate>

</phase>

<phase id="2" name="Converter for Postkarte (smallest, no chains, no var)">

Build the converter skeleton and prove it on the simplest original. Postkarte: 18 frames, 1 RGB Green, 9 styles, 4 RADRECT, 1 soft-shadow, 0 chains. RESEARCH.md §Postkarte (lines 236–331).

<task id="2.1" name="sla_to_dsl skeleton + dispatch + strict UnhandledElement">
**File:** `tools/sla_to_dsl.py` (new).
**Action:** Implement skeleton:
- CLI: `sla_to_dsl.py <original.sla> <out_build.py> --template-id <id> --assets-dir <path>`.
- Parse via `SLADocument`.
- Define typed exception `UnhandledElement(Exception)` carrying element-tag, attribute name, and source-context for D6 strict mode.
- Dispatch by element type: `<COLOR>`, `<STYLE>`, `<CHARSTYLE>`, `<LAYERS>`, `<MASTERPAGE>`, `<PAGE>`, `<PAGEOBJECT>` (by PTYPE), `<MASTEROBJECT>` (none in our originals), `<FRAMEOBJECT>` (drop silently per resolved decision), `<Sections>`.
- For each PAGEOBJECT, dispatch by `(PTYPE, FRTYPE)`:
  - PTYPE=2 → `ImageFrame(...)` (with `corner_radius_mm` if FRTYPE=2/RADRECT)
  - PTYPE=4 → `TextFrame(runs=[...])` reading `<StoryText>` ITEXT/para/breakline/tab/trail/var elements in order
  - PTYPE=5 → `Line(...)`
  - PTYPE=6 with FRTYPE=1 → `Polygon(shape="ellipse")`
  - PTYPE=6 with FRTYPE=0 → `Polygon(shape="rectangle")`
  - PTYPE=6 with FRTYPE=3 → `Polygon(custom_path=<verbatim path>, fill_rule=<from fillRule attr>)`
  - PTYPE=4 with FRTYPE=3 → `TextFrame(custom_path=<verbatim>, fill_rule=...)`
- Emit a Python script that imports the DSL, instantiates `Document(...)`, calls `add_color` / `add_para_style` / `add_char_style` (per task 2.2), then `Page` + frames in order, then `doc.save(...)`.
- **Every attribute the converter encounters in the original** must be either consumed by a typed kwarg OR raise `UnhandledElement`. No silent drops.
- Convert XPOS/YPOS from scratch-space to page-local (subtract owning page's PAGEXPOS/PAGEYPOS) and then to mm (1 mm = 2.834645669 pt) for the DSL kwargs.
- Use Black-style formatting (4-space indent, double quotes, trailing comma) for the emitted `build.py` for diff-friendliness.
**Verify:** `python tools/sla_to_dsl.py postkarte-vorlage-original.sla /tmp/postkarte_build.py --template-id postkarte-a6-kampagne --assets-dir /tmp/assets/` runs without `UnhandledElement` after Phase 1's DSL surface is in place. Manual scan: emitted file imports compile (`python -m py_compile /tmp/postkarte_build.py`).
**Done:**
- Converter runs end-to-end on Postkarte without raising.
- Emitted file is syntactically valid Python.
</task>

<task id="2.2" name="Converter: emit Document with custom layers, colors, styles">
**File:** `tools/sla_to_dsl.py`.
**Action:** Read `<COLOR>` elements via `SLADocument.iter_colors()`; emit `doc.add_color(name, rgb=(R,G,B))` for each colour NOT in `shared/ci.yml`'s palette (compare by NAME — load `shared/ci.yml` once at converter start). Emit `doc.add_para_style(ParaStyle(name=..., ...))` for each `<STYLE>` via `iter_styles()`, mapping all 31 STYLE attribute names from RESEARCH.md §Zeitung styles table to the corresponding `ParaStyle` field. Emit `doc.add_char_style(CharStyle(...))` for each CHARSTYLE.

Emit `Document(..., layers=[DocumentLayer(name="Hintergrund")])` reading from `iter_layers()`. For Postkarte/Plakat the LAYERS NAME is `Hintergrund`; for Zeitung it's `Ebene 1` — converter reads it verbatim.

For inheritance: read STYLE's `PARENT` attribute and **only set `ParaStyle.parent` to it**; do NOT copy parent attributes into the child — the DSL emitter (Task 1.3) handles inheritance.
**Verify:** Run converter on Postkarte; emitted `build.py` (a) imports `DocumentLayer`, `ParaStyle`, `CharStyle`; (b) registers exactly 1 extra colour `Green` with `rgb=(153, 102, 51)`; (c) registers 9 paragraph styles; (d) `python /tmp/postkarte_build.py` produces `/tmp/postkarte.sla`.
**Done:**
- Emitted Postkarte build.py registers correct colours, styles, layers.
- Build.py runs and emits a valid SLA.
</task>

<task id="2.3" name="Converter: per-PAGEOBJECT translation incl. soft-shadow + RADRECT">
**File:** `tools/sla_to_dsl.py`.
**Action:** For each PAGEOBJECT:
- Resolve `(x_mm, y_mm, w_mm, h_mm)` from XPOS/YPOS/WIDTH/HEIGHT minus owning page's PAGEXPOS/PAGEYPOS, divided by 2.834645669.
- Read `LAYER` (always 0 in originals) → `layer=0`.
- Read `ROT` → `rotation_deg=`.
- Read `ANNAME` → `anname=` (verbatim where present; preserve `Kopie von ...` and `u29b9` style auto-IDs).
- For PTYPE=4 / TextFrame:
  - Read `<StoryText>` children in order; for each `<DefaultStyle>`, the following ITEXTs use that paragraph style as base; for each `<ITEXT>` build `Run(text=CH, fcolor=...if present..., fontsize=..., font=..., fshade=..., features=..., kern=..., fontfeatures=..., char_style=CPARENT...if present..., separator=<from following sibling>)`.
  - Map sibling `<para/>` → `separator="para"`; `<breakline/>` → `"breakline"`; `<tab/>` → `"tab"`; `<var name="pgno"/>` → set `Run.var="pgno"` on the preceding ITEXT (or emit a zero-width Run with var only). `<trail/>` is the StoryText terminator — converter consumes silently (the DSL emitter regenerates it).
  - Preserve `\xad` byte-for-byte in `text=`.
- For PTYPE=2 / ImageFrame:
  - If `isInlineImage="1"`: extract `ImageData` → base64-decode → strip the qCompress 4-byte big-endian length prefix → zlib-decompress → write bytes to `templates/<id>/assets/<safe_anname>_<idx>.<ext>` (use `inlineImageExt` for extension); emit `ImageFrame(image="assets/<filename>", ...)`. (Resolved decision: Option A.)
  - Else: read `PFILE` → `image=PFILE` verbatim.
  - If `FRTYPE=2`: emit `corner_radius_mm=RADRECT/2.834645669` AND `custom_path=<verbatim path>` (the bezier-rounded-rect path Scribus emitted).
  - If `LOCALSCX/LOCALSCY/LOCALX/LOCALY/LOCALROT/SCALETYPE/RATIO/PICART` differ from defaults: extend ImageFrame with typed kwargs (and add to Phase 1 retroactively if missing — D6 strict).
- For PTYPE=6 / Polygon: read `PCOLOR` → `fill=`, `PCOLOR2` → `line_color=`, `PWIDTH` → `line_width_pt=`, `SHADE` → `fill_shade=`.
- Read `HASSOFTSHADOW="1"` + `SOFTSHADOW*` attrs → `soft_shadow=SoftShadow(...)` with all 9 fields verbatim.
- `fillRule` → `fill_rule=int(value)`.
- `ALIGN` → `text_align=int(value)`.
**Verify:** Run converter on Postkarte; emitted `build.py` references the correct number of frames per type (RESEARCH.md Postkarte distribution: 7 PTYPE=4-FRTYPE=0, 4 PTYPE=2-FRTYPE=0, 4 PTYPE=2-FRTYPE=2, 2 PTYPE=6-FRTYPE=0, 1 PTYPE=6-FRTYPE=1). One soft-shadow on a TextFrame. `python /tmp/postkarte_build.py` produces `/tmp/postkarte.sla`.
**Done:**
- Per-PTYPE dispatch handles every Postkarte frame.
- Inline-image extraction writes 7 sidecar PNGs.
- No `UnhandledElement` raised.
</task>

<task id="2.4" name="Round-trip: Postkarte build.py → sla_diff against original" risk="high">
**Files:** `templates/postkarte-a6-kampagne/build.py` (replace placeholder), `templates/postkarte-a6-kampagne/meta.yml` (add `original_sla:` and `ci_overrides:` keys), `templates/postkarte-a6-kampagne/assets/*.png` (committed sidecar inline images), `tools/sla_lib/tests/test_sla_to_dsl.py` (new).
**Action:**
1. Run converter: `python tools/sla_to_dsl.py postkarte-vorlage-original.sla templates/postkarte-a6-kampagne/build.py --template-id postkarte-a6-kampagne --assets-dir templates/postkarte-a6-kampagne/assets/`
2. Run the emitted build: `python templates/postkarte-a6-kampagne/build.py` → produces `templates/postkarte-a6-kampagne/template.sla`
3. Run `python tools/sla_diff.py --left postkarte-vorlage-original.sla --right templates/postkarte-a6-kampagne/template.sla --markdown`
4. **Iterate**: every critical/warning issue → fix in converter (Task 2.3) or DSL (Phase 1) → re-run.
5. Update `meta.yml` to add: `original_sla: ../../postkarte-vorlage-original.sla`, `ci_overrides: { non_ci_styles: [<the 9 names>], non_ci_colors: [Green] }`.
6. Add `test_sla_to_dsl.test_postkarte_round_trip_clean`: runs converter + build + sla_diff in a tmp dir; asserts `report.summary["critical"] == 0` and `report.summary["warning"] == 0`.
**Verify:** `python -m unittest tools.sla_lib.tests.test_sla_to_dsl.PostkarteRoundTrip` green. Manual `python tools/sla_diff.py --left postkarte-vorlage-original.sla --right templates/postkarte-a6-kampagne/template.sla` exits 0.
**Done:**
- Postkarte template.sla round-trips clean (zero critical, zero warning).
- Test in CI-runnable form.
- meta.yml updated.
- Inline-image PNGs committed.
</task>

<gate>
- `sla_diff` Postkarte: 0 critical, 0 warning.
- `python templates/postkarte-a6-kampagne/build.py` runs without errors.
- `test_sla_to_dsl.PostkarteRoundTrip` green.
**Do not start Phase 3 until the gate passes.**
</gate>

</phase>

<phase id="3" name="Plakat A1 reproduction (soft-hyphens, 90° rotation)">

Plakat: 9 frames, 7 soft-hyphens, 5 styles, 1 PTYPE=4 with `ROT=270`, 0 chains, 0 var. RESEARCH.md §Plakat A1 (lines 333–391).

<task id="3.1" name="Run converter on Plakat; surface gaps">
**Files:** `templates/plakat-event/build.py` (replace), `templates/plakat-event/meta.yml`, `templates/plakat-event/assets/*.png`.
**Action:** Run `python tools/sla_to_dsl.py plakat-a1-hochformat-original.sla templates/plakat-event/build.py --template-id plakat-event --assets-dir templates/plakat-event/assets/`. Likely surfaces:
- `PAGESIZE="Custom"` (A1 isn't a Scribus preset) — converter emits `Document(...)` with explicit `(width_pt, height_pt)` tuple to `add_page(size=(1683.78, 2383.94), ...)`.
- `BORDER` of 40 pt all sides → `margins_mm=(14.11, ...)`.
- `ROT=270` on the 1 rotated frame → already supported.
- Soft-hyphens in 3 ITEXT runs (`'ei\xadne gro\xadße '`, `'vier\xadzei\xadli\xadge '`, `'Ü\xadber\xadschrift '`) — Run.text must preserve `\xad` byte-for-byte.

If converter raises `UnhandledElement` for anything new, add the typed extension to Phase 1 retroactively, re-run.
**Verify:** Converter completes without raising. `python templates/plakat-event/build.py` produces `templates/plakat-event/template.sla`.
**Done:**
- Converter handles Plakat.
- Build.py emits a SLA.
</task>

<task id="3.2" name="Round-trip: Plakat build.py → sla_diff" risk="high">
**Files:** `tools/sla_lib/tests/test_sla_to_dsl.py`.
**Action:** Run `python tools/sla_diff.py --left plakat-a1-hochformat-original.sla --right templates/plakat-event/template.sla --markdown`. Iterate to clean. Add `test_plakat_round_trip_clean` mirroring Postkarte's. Add a second test `test_plakat_soft_hyphens_byte_preserved`: read `templates/plakat-event/template.sla` as bytes, assert `b"ei\xadne"`, `b"vier\xadzei\xadli\xadge"`, `b"\xc3\x9c\xadber\xadschrift"` (UTF-8 encoded Ü plus `\xad`) all appear.

Update `meta.yml`: `original_sla: ../../plakat-a1-hochformat-original.sla`, `ci_overrides: { non_ci_styles: [Headlineweiß, Überschrift gelb, Fließtext, Impressum] }`.
**Verify:** Both tests green. Manual diff exits 0.
**Done:**
- Plakat template.sla round-trips clean.
- Soft-hyphens byte-preserved (test asserts file bytes).
</task>

<gate>
- `sla_diff` Plakat: 0 critical, 0 warning.
- Soft-hyphens present in `templates/plakat-event/template.sla` as raw `\xad` bytes.
- `test_sla_to_dsl.PlakatRoundTrip` green.
**Do not start Phase 4 until the gate passes.**
</gate>

</phase>

<phase id="4" name="Zeitung reproduction (the hard one)">

Zeitung: 14 pages, 140 frames, 14 linked chains (42 frames), 23 paragraph styles with 31 distinct attribute names, 12 `<var pgno/>`, 86 fillRule on FRTYPE=3, 4 ALIGN-on-PAGEOBJECT, 1 SHADE on Polygon, 6 inline images, 0 soft-hyphens (Scribus's hyph engine handles it), 2 master pages, facing-pages, RGB `Green=(0,255,0)`, layer named `Ebene 1`. RESEARCH.md §Zeitung (lines 392–566).

<task id="4.1" name="Multi-master + facing pages emit">
**Files:** `tools/sla_to_dsl.py`, `tools/sla_lib/builder/document.py`.
**Action:** Converter emits `Document(facing_pages=True, column_gap_default_pt=12, ...)`. For each `<MASTERPAGE>` in the original, emit `doc.add_master(name=<MNAM>, size=(595.276, 841.890), facing="left" if LEFT==1 else "right")`. For each `<PAGE>`, emit `doc.add_page(size=..., master=<MNAM verbatim>, label="")`. Note: master-NAME has German umlauts and spaces (`Neue Musterseite rechts`, `Neue Musterseite links`); ensure the DSL accepts arbitrary string master names (it should already — `Document.add_master(name=...)` is `str`).
**Verify:** Converter on Zeitung emits a build.py that calls `add_master` twice and `add_page` 14 times. `python <build.py>` produces `templates/zeitung-a4-grun/template.sla` with two `<MASTERPAGE>` elements.
**Done:**
- Both masters emitted in order.
- 14 PAGEs emitted with verbatim MNAM.
- `BOOK="1"` and `ABSTSPALTEN="12"` in DOCUMENT.
</task>

<task id="4.2" name="ParaStyle long-tail attrs for Zeitung's 23 styles" risk="high">
**File:** `tools/sla_to_dsl.py`, possibly `tools/sla_lib/builder/document.py:_emit_styles`.
**Action:** Walk Zeitung's 23 STYLE elements via `iter_styles()`; map every present attribute to its `ParaStyle` field. Cover all 31 attribute names listed in RESEARCH.md lines 458–490. Verify inheritance: `Einleitungstext` has `PARENT="Zwischenüberschrift"` — converter emits `ParaStyle(name="Einleitungstext", parent="Zwischenüberschrift", font="Gotham Narrow Black")` only; FONTSIZE/ALIGN/etc. omitted.

Open question §6 (resolved via verification task in Phase 4): the Zeitung emits LANGUAGE on only 13 of 23 styles. The DSL emitter (Task 1.3) only emits LANGUAGE when `ParaStyle.language is not None` — so the converter passes `language=None` for the 10 styles that lack LANGUAGE. **Verification task in Phase 4.4** confirms this doesn't drift hyphenation; if it does, the converter switches to `language="de"` everywhere.
**Verify:** Emitted Zeitung build.py registers exactly 23 ParaStyle. After save, `iter_styles` on `templates/zeitung-a4-grun/template.sla` returns 23 STYLEs whose attribute presence matches the original (use `sla_diff` to verify).
**Done:**
- All 23 styles round-trip via `sla_diff` with severity ≤ info.
- Long-tail attrs (NACH, VOR, DROP, DROPLIN, INDENT, RMARGIN, FIRST, MinWordTrack, etc.) all present where original has them.
</task>

<task id="4.3" name="Linked chain detection + emit (14 chains, 42 frames)" risk="high">
**File:** `tools/sla_to_dsl.py`.
**Action:** Walk PAGEOBJECTs; build forward map `next_item_id_by_id[ItemID] = NEXTITEM` and inverse `back_map[NEXTITEM] = ItemID`. For each frame whose `BACKITEM=-1` and `NEXTITEM != -1`, traverse forward to assemble a chain (head, ..., tail). For each chain, emit converter code:
```
frame_a = TextFrame(...)
frame_b = TextFrame(...)
frame_c = TextFrame(...)
frame_a.link_to(frame_b)
frame_b.link_to(frame_c)
page.add(frame_a)
page.add(frame_b)
page.add(frame_c)
```
Frames must be added to the page in chain order so the pre-allocation pass (Task 1.7) sees them correctly. **All 14 Zeitung chains** are 3 frames each, all on a single page — single-page chains, no cross-page linking.

If a frame ANNAME is `Kopie von u2da1` etc., preserve it verbatim — chain identity in `sla_diff` uses positions/sizes, not ANNAME.
**Verify:** Emitted build.py contains 14 `link_to` invocations. Run `tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right templates/zeitung-a4-grun/template.sla` — chain-topology issues report 0 critical (chain hash matches per chain).
**Done:**
- 14 chains detected and emitted in order.
- `sla_diff` chain-topology check: 0 critical.
</task>

<task id="4.4" name="Verify Zeitung LANGUAGE-on-STYLE inheritance via render" risk="high">
**Files:** `templates/zeitung-a4-grun/template.sla` (built), reference render.
**Action:** Resolved decision: LANGUAGE inheritance must be verified by visual comparison of hyphenation in the original PDF vs reproduction PDF (RESEARCH.md open question §6, lines 1216).
1. Render original: `xvfb-run -a scribus -g -ns -py tools/_export_pdf.py gruene-zeitung-vorlage-original.sla /tmp/zeitung-orig.pdf`.
2. Render reproduction: `xvfb-run -a scribus -g -ns -py tools/_export_pdf.py templates/zeitung-a4-grun/template.sla /tmp/zeitung-dsl.pdf`.
3. Open both PDFs; pick a long-paragraph article (e.g. page 3 or 4 body text); screenshot the same paragraph from each at the same zoom.
4. Compare: do the hyphenation breaks match line-for-line? If yes, the omitted-LANGUAGE-styles inherit correctly. If no, the converter must emit `language="de"` on ALL 23 styles regardless of original (and `_emit_styles` continues to honour None-omission for greenfield paths).
5. Document the outcome in `templates/zeitung-a4-grun/README.md` ("LANGUAGE inheritance verified: <observed behaviour>").
**Verify:** Manual visual check — paragraph hyphenation matches in both PDFs (or differs systematically, in which case fix and re-run).
**Done:**
- Hyphenation drift either confirmed absent or fixed.
- README note added.
</task>

<task id="4.5" name="var pgno + ALIGN-on-frame + fillRule + 6 inline images for Zeitung">
**File:** `tools/sla_to_dsl.py`.
**Action:**
- For each `<var name="pgno"/>` in StoryText (12 occurrences across the Zeitung): emit `Run(var="pgno")` (potentially as a zero-text run between ITEXTs).
- For each PAGEOBJECT with `ALIGN` attribute (4 occurrences, values 1/3/3/3 on linked-chain text frames): emit `text_align=<int>`.
- For each PTYPE=4 with FRTYPE=3 (79 frames) or PTYPE=6 with FRTYPE=3 (6 frames) or PTYPE=2 with FRTYPE=3 (1 frame): emit `custom_path=<verbatim path>` and `fill_rule=<int>` (`fillRule="0"` everywhere = 0).
- For 6 inline images: extract via Option A as in Postkarte; sidecar files under `templates/zeitung-a4-grun/assets/`.
- For 1 polygon with `SHADE`: emit `fill_shade=<int>`.
**Verify:** Emitted Zeitung build.py contains 12 `var="pgno"`, 4 `text_align=`, 86 `custom_path=` plus `fill_rule=`, 6 `image="assets/..."`, 1 `fill_shade=`. `python <build.py>` produces a 14-page SLA.
**Done:**
- All long-tail Zeitung attrs round-trip.
- Inline images extracted and committed.
</task>

<task id="4.6" name="Round-trip: Zeitung build.py → sla_diff" risk="high">
**Files:** `templates/zeitung-a4-grun/build.py` (replace), `templates/zeitung-a4-grun/meta.yml`, `templates/zeitung-a4-grun/assets/*.png`, `tools/sla_lib/tests/test_sla_to_dsl.py`.
**Action:** Run converter, run build, run `sla_diff`. Iterate to clean. Each remaining critical/warning identifies either a converter dispatch bug or a Phase 1 DSL gap that survived; fix in source, never patch the emitted build.py by hand. Add `test_zeitung_round_trip_clean` to test suite.

Update meta.yml: `original_sla: ../../gruene-zeitung-vorlage-original.sla`, `ci_overrides: { non_ci_styles: [<all 23 names>], non_ci_colors: [Green] }`.

Specifically expect to debug: the 14 chains' chain-hash, the 12 `<var pgno/>` placement order vs ITEXT separators, the FRTYPE=3 path normalisation rule (originals' CCW path order vs converter's emitted path).
**Verify:** `python -m unittest tools.sla_lib.tests.test_sla_to_dsl.ZeitungRoundTrip` green. `tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right templates/zeitung-a4-grun/template.sla` exits 0 (no critical, no warning).
**Done:**
- Zeitung template.sla round-trips clean.
- 14 chains intact.
- 12 var pgno round-trip.
- Test green.
</task>

<gate>
- `sla_diff` Zeitung: 0 critical, 0 warning.
- All three template SLAs (Postkarte, Plakat, Zeitung) round-trip clean.
- All 14 Zeitung chains intact (chain hash matches per chain via `sla_diff` linked-chain check).
- LANGUAGE inheritance verified (Task 4.4).
**Do not start Phase 5 until the gate passes.**
</gate>

</phase>

<phase id="5" name="visual_diff foundation + frozen baselines">

By here, all three SLAs round-trip cleanly. Now build the visual validator and freeze the per-template baselines per CONTEXT.md D3. RESEARCH.md §visual_diff strategy (lines 899–977).

<task id="5.1" name="Freeze baseline.pdf for each template (D3)">
**Files:** `templates/postkarte-a6-kampagne/baseline.pdf`, `templates/plakat-event/baseline.pdf`, `templates/zeitung-a4-grun/baseline.pdf`. `.gitattributes` (add `*.pdf binary`).
**Action:** Per CONTEXT.md D3: render each ORIGINAL once locally with the current Scribus 1.6.5 toolchain, commit the PDF. Note the rendering target: per CONTEXT.md D3 the baseline is rendered from the ORIGINAL SLA, so future visual_diff compares the DSL build against this committed baseline (NOT against a re-render).
For each:
```
xvfb-run -a scribus -g -ns -py tools/_export_pdf.py \
  postkarte-vorlage-original.sla templates/postkarte-a6-kampagne/baseline.pdf
```
Repeat for plakat and zeitung. Commit. Add `*.pdf binary` to `.gitattributes` if not already present (RESEARCH.md line 972).
**Verify:** Three baseline.pdf files in repo. `pdfinfo` on each reports correct page count (2, 1, 14).
**Done:**
- Three baseline PDFs committed.
- .gitattributes flag set.
</task>

<task id="5.2" name="Implement visual_diff.py">
**File:** `tools/visual_diff.py` (new).
**Action:** Implement the pipeline from RESEARCH.md §visual_diff strategy (lines 913–941):
1. CLI: `tools/visual_diff.py <template_sla> --baseline <baseline.pdf> --dpi <int> --tolerance <diff.yml> --out <build_dir>`. Add `--ci` shortcut → `--dpi=96`.
2. Render the DSL SLA: `xvfb-run -a scribus -g -ns -py tools/_export_pdf.py <template_sla> <out_dir>/dsl.pdf`.
3. Rasterise both: `pdftoppm -r <dpi> -png <pdf> <out_dir>/<prefix>-page` (Poppler, NOT Ghostscript — RESEARCH.md line 911).
4. Per-page compare: `compare -metric AE -fuzz <fuzz_pct>% baseline-N.png dsl-N.png diff-N.png 2> mismatch.txt`. Parse mismatch pixel count.
5. Composite: `montage baseline-N.png dsl-N.png diff-N.png -tile 3x1 -geometry +4+4 composite-N.png`.
6. Apply per-region tolerance from `diff.yml`: a region's `bbox_mm` clips the compare into a sub-rectangle (via ImageMagick `-crop`) before threshold check.
7. Output: `<out_dir>/visual_diff.json` (machine-readable summary + per-page mismatch_pct), `<out_dir>/visual_diff.html` (links to composites for human review).
8. Exit code: 0 if every page (and every region) passes its tolerance; 1 otherwise.
**Verify:** New tests in `tools/sla_lib/tests/test_visual_diff.py` use a tiny 2-page DSL document built two ways (identical vs deliberately-shifted text) and assert exit codes / mismatch percentages. Mock external tools (`pdftoppm`, `compare`, `montage`) via subprocess stubs OR call them for real if Scribus + ImageMagick are available in the test environment.
**Done:**
- `visual_diff.py` runs end-to-end on a sample template.
- Tests cover both clean and drifted cases.
- JSON + HTML outputs generated.
</task>

<task id="5.3" name="Per-template diff.yml tolerance configs">
**Files:** `templates/postkarte-a6-kampagne/diff.yml`, `templates/plakat-event/diff.yml`, `templates/zeitung-a4-grun/diff.yml`, `docs/diff-tolerance.md` (new).
**Action:** Create per-template `diff.yml` per the schema in RESEARCH.md lines 945–957 (resolved decision: schema as proposed). Defaults: `max_pixel_mismatch_pct: 1.0`, `fuzz_pct: 2`. Run `tools/visual_diff.py` on each template at 96 dpi; for any page exceeding 1%, add a `per_page` override; for body-text-heavy regions of the Zeitung exceeding 1% but visually identical to the human eye (RESEARCH.md pitfall "sub-pixel font hinting", lines 1153–1156), add a `per_region` override with `max_pixel_mismatch_pct` up to 5%.

Document the schema in `docs/diff-tolerance.md` (new file): YAML keys, semantics, rebaselining workflow excerpt from RESEARCH.md lines 960–973.
**Verify:** `tools/visual_diff.py` exits 0 on all three templates at 96 dpi. Document the tuning rationale in each `diff.yml` as YAML comments above any region overrides.
**Done:**
- Three `diff.yml` files committed.
- `docs/diff-tolerance.md` created.
- All three pass visual diff at 96 dpi.
</task>

<task id="5.4" name="Verify all three templates pass visual_diff at 150 dpi (local)" risk="high">
**Action:** Per CONTEXT.md D4 ("Local: 150 dpi rasters, full coverage"), run `tools/visual_diff.py --dpi 150 ...` on each template. Tolerances may need different per-region values at 150 dpi than 96 dpi (more pixels = more font-edge jitter visible). If any page fails at 150 dpi but passes at 96 dpi, document the discrepancy in `diff.yml` via separate `per_page` overrides keyed by dpi (extend the schema if needed).

Best practice: tune fuzz_pct first (loosen color tolerance) before loosening mismatch_pct (which would hide real layout drift).
**Verify:** All three templates: visual_diff exit 0 at both 96 and 150 dpi.
**Done:**
- 150 dpi visual diff clean for all three.
- diff.yml updated if tolerances differ between dpi levels.
</task>

<gate>
- Three baseline.pdf committed.
- `tools/visual_diff.py` implemented and exits 0 on all three templates at 96 dpi.
- Tolerance configs in place.
- Unit tests for visual_diff pass.
**Do not start Phase 6 until the gate passes.**
</gate>

</phase>

<phase id="6" name="CI integration">

Wire the validators into `.github/workflows/pages.yml`. RESEARCH.md §CI integration (lines 980–1045).

<task id="6.1" name="Extend pages.yml with validate-reproductions step">
**File:** `.github/workflows/pages.yml`.
**Action:** Insert a `Validate reproductions` step in the `build` job AFTER `Run unit tests` (or current equivalent) and BEFORE `actions/upload-pages-artifact`. Workflow excerpt per RESEARCH.md lines 985–1005:
```yaml
- name: Validate reproductions (sla_diff + visual_diff)
  run: |
    set -euo pipefail
    for tdir in templates/postkarte-a6-kampagne templates/plakat-a1-hochformat templates/zeitung-a4-grun; do
      tid=$(basename "$tdir")
      original=$(python3 -c "import yaml,sys; m=yaml.safe_load(open(f'$tdir/meta.yml')); print(m['original_sla'])")
      python3 tools/sla_diff.py --left "$original" --right "$tdir/template.sla" --json > "build/$tid/sla_diff.json"
      python3 tools/visual_diff.py "$tdir/template.sla" \
        --baseline "$tdir/baseline.pdf" \
        --dpi 96 \
        --tolerance "$tdir/diff.yml" \
        --out "build/$tid/"
    done
```
Read the original SLA path from `meta.yml`'s `original_sla:` key (resolved decision).

Add `imagemagick` to the apt-get install line (RESEARCH.md line 1173 — current line installs xvfb, poppler-utils, ghostscript, python3-lxml, python3-yaml; add `imagemagick`).

Add Scribus AppImage caching (RESEARCH.md lines 1014): `actions/cache@v3` keyed by `SCRIBUS_VERSION`, restore path `/opt/squashfs-root`.

Add path-filtered PR triggers (RESEARCH.md lines 1020–1033):
```yaml
on:
  push:
    branches: [main]
  pull_request:
    paths:
      - 'tools/**'
      - 'templates/**'
      - 'shared/**'
      - '.github/workflows/pages.yml'
  workflow_dispatch:
```

On failure, upload `build/*/composite-page-*.png` as workflow artifacts so reviewers can inspect the delta:
```yaml
- name: Upload visual diff artifacts on failure
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: visual-diff-composites
    path: build/*/composite-page-*.png
```
**Verify:** Push a branch with the workflow change. The `build` job runs `validate-reproductions`. Total runtime within 5 min (RESEARCH.md line 1045 estimates ~80s).
**Done:**
- Workflow file extended.
- Path-filtered triggers in place.
- ImageMagick installed in CI.
- Artifacts uploaded on failure.
</task>

<task id="6.2" name="Verify CI runtime + green on main" risk="high">
**Action:** Push to a test branch; observe `validate-reproductions` runtime. If > 5 min:
- Profile: which template / which step dominates?
- Mitigations in priority order (RESEARCH.md "CI runtime balloons" risk row, line 84):
  1. Cache Scribus AppImage between runs.
  2. Parallelise per-template (matrix strategy).
  3. Last resort: visual_diff only on PRs that touch `templates/**`, sla_diff always.
Once CI is green on the test branch, merge to main; observe one full run on main.
**Verify:** Test branch CI green. Main branch CI green after merge. Runtime ≤ 5 min.
**Done:**
- CI green on main.
- Runtime documented.
</task>

<task id="6.3" name="Drift-detection one-time verification" risk="high">
**Action:** Resolved decision: confirm CI fails on deliberately-introduced drift (RESEARCH.md test strategy: "CI workflow fails the build on a deliberately-introduced drift in a test branch").
1. On a throwaway branch, edit `templates/postkarte-a6-kampagne/build.py` to shift one frame's YPOS by 5 mm (deliberate drift).
2. Push; observe that `validate-reproductions` fails with `sla_diff` reporting a `position-drift` warning at minimum.
3. Run `--strict`-equivalent: confirm `sla_diff` exit code 1 in CI when warning is present (the workflow above passes warnings cleanly by default — choose explicitly: should warnings fail CI? Yes, given CONTEXT.md "must pass" expectation. Run `sla_diff` with `--strict` in the workflow.)
4. Update CI step to use `--strict` for `sla_diff`.
5. Throw away the test branch.
6. Document the drift-detection verification in a new `EXECUTION.md` in the issue dir, dated.
**Verify:** Deliberate drift → CI fails. Reverting drift → CI passes.
**Done:**
- `--strict` flag wired into CI.
- Drift-detection verified once and documented.
</task>

<gate>
- `validate-reproductions` step green on main.
- Drift-detection verified and documented in `EXECUTION.md`.
- Total CI runtime ≤ 5 min.
- ImageMagick installed.
- Path-filtered triggers in place.
**Do not start Phase 7 until the gate passes.**
</gate>

</phase>

<phase id="7" name="Cleanup & cutover">

Replace placeholder DSL output with the faithful reproductions and remove vestigial originals from the gallery output. CONTEXT.md D5: gallery serves only DSL templates.

<task id="7.1" name="Rename templates/plakat-event → templates/plakat-a1-hochformat">
**Files:** `templates/plakat-event/` (move), `templates/plakat-a1-hochformat/` (target), Astro frontmatter in `site/`.
**Action:** Resolved decision: rename. `git mv templates/plakat-event templates/plakat-a1-hochformat`. Update any path references:
- `tools/gallery_build.py` is content-driven (it scans `templates/<id>/`) — verify it still picks up the renamed dir.
- Astro pages under `site/src/` may have explicit references — grep for `plakat-event` and replace with `plakat-a1-hochformat`.
- Update `templates/plakat-a1-hochformat/meta.yml`'s `original_sla:` path (still resolves correctly).
- Update CI workflow (Task 6.1) to reference the new dir.
**Verify:** `grep -r plakat-event` in repo returns no hits (except possibly in committed PDFs which are binary). Site builds locally without 404. `tools/gallery_build.py` finds 3 templates.
**Done:**
- Directory renamed.
- All references updated.
- Gallery still builds.
</task>

<task id="7.2" name="Remove originals from site/public; gallery serves only DSL output">
**Files:** `site/public/` (remove any `*-original.sla` references), `tools/gallery_build.py` (verify).
**Action:** CONTEXT.md D5: originals stay in repo at workspace root as the diff baseline only — they are NOT copied into `site/public/` and NOT referenced from gallery pages. Audit:
- `grep -r "vorlage-original.sla" site/` → expect zero hits.
- `find site/public -name "*-original.sla"` → expect empty.
- `tools/gallery_build.py` should consume `templates/<id>/template.sla` (DSL build) only.

If any references remain, remove them. Confirm the gallery preview PDFs/PNGs are regenerated from the DSL `template.sla`, not the originals.
**Verify:** Search-and-confirm. Run `python tools/gallery_build.py` locally and inspect generated `site/public/*` — only DSL outputs.
**Done:**
- Zero references to originals in `site/`.
- Gallery serves DSL outputs.
</task>

<task id="7.3" name="README + docs updates">
**Files:** `README.md`, `docs/dsl-reference.md` (new — soft-hyphen escape-hatch note), `docs/diff-tolerance.md` (already created in 5.3).
**Action:**
- Add a "Round-trip validation" section to top-level `README.md`: explain `sla_diff` and `visual_diff`, `make validate` (or equivalent local entry point — add a tiny shell script `bin/validate` if no Makefile exists), the per-template `baseline.pdf` + `diff.yml` schema, and the rebaselining workflow (RESEARCH.md lines 960–973).
- Add the note: "the converter `tools/sla_to_dsl.py` is a one-shot bootstrap; thereafter `templates/<id>/build.py` is the source of truth and the converter is NOT run in CI" (resolved decision).
- New `docs/dsl-reference.md` (or extend an existing reference doc): document soft-hyphens (`\xad`) as an "escape hatch for words Scribus's German hyph dict gets wrong; not for routine use" (resolved decision §7).
- `tools/sla_lib/builder/__init__.py` module docstring: short bullet list of new typed APIs (`Run`, `ParaStyle`, `CharStyle`, `DocumentLayer`, `SoftShadow`, `link_to`, `add_color`).
**Verify:** Manual review. README mentions the round-trip validation pipeline in the project intro. `docs/dsl-reference.md` exists and covers soft-hyphens.
**Done:**
- README updated.
- `docs/dsl-reference.md` created.
- `__init__.py` docstring updated.
</task>

<task id="7.4" name="Final cross-check: acceptance crosswalk validation">
**Action:** Walk every acceptance criterion in ISSUE.md (§Acceptance Criteria) against the current state of the repo:
1. `tools/sla_to_dsl.py` runs cleanly on all three originals → verify by running each.
2. DSL `raw_attrs`-free typed surface, `custom_path`, per-run formatting, linked frames, soft-hyphens implemented and tested → verify Phase 1 tests green.
3. `tools/sla_diff.py` reports zero critical/warning between each original and reproduction → verify with three `sla_diff` runs.
4. `tools/visual_diff.py` reports < 1% per page → verify with three `visual_diff` runs at both 96 and 150 dpi.
5. Three `templates/<id>/template.sla` are DSL-built and faithful → file-modification timestamps + sla_diff confirm.
6. CI workflow includes the validation step; passes on main → verify GitHub Actions UI.
7. Pages gallery serves the faithful templates → site preview locally; confirm DSL output is what's served.
8. Unit tests for converter + diff tools, all green → `python -m unittest discover` exits 0.
9. README updated → manual read.

If any criterion is red, identify which task (any phase) failed to deliver it and re-open that task.
**Verify:** All 9 acceptance criteria green. Issue can be closed.
**Done:**
- Issue acceptance criteria all met.
</task>

<gate>
- All ISSUE.md acceptance criteria green.
- `templates/plakat-event/` renamed to `templates/plakat-a1-hochformat/`.
- Gallery serves only DSL output.
- README + docs updated.
- One final pass: `python -m unittest discover && python tools/sla_diff.py ...all three... && python tools/visual_diff.py ...all three...` all exit 0.
**Issue is done when this gate passes.**
</gate>

</phase>

## Files touched (manifest)

**New files:**
- `tools/sla_diff.py`
- `tools/sla_to_dsl.py`
- `tools/visual_diff.py`
- `tools/sla_lib/tests/test_sla_diff.py`
- `tools/sla_lib/tests/test_dsl_extensions.py`
- `tools/sla_lib/tests/test_sla_to_dsl.py`
- `tools/sla_lib/tests/test_visual_diff.py`
- `templates/postkarte-a6-kampagne/baseline.pdf`
- `templates/postkarte-a6-kampagne/diff.yml`
- `templates/postkarte-a6-kampagne/assets/*.png` (extracted inline images, 7 files)
- `templates/plakat-a1-hochformat/baseline.pdf` (after rename in Task 7.1)
- `templates/plakat-a1-hochformat/diff.yml`
- `templates/plakat-a1-hochformat/assets/*.png` (2 files)
- `templates/zeitung-a4-grun/baseline.pdf`
- `templates/zeitung-a4-grun/diff.yml`
- `templates/zeitung-a4-grun/assets/*.png` (6 files)
- `docs/dsl-reference.md`
- `docs/diff-tolerance.md`
- `bin/validate` (optional shell entry point for `make validate` equivalent)
- `.gitattributes` (extend with `*.pdf binary` if not already)
- `.issues/2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline/EXECUTION.md` (drift verification log; created in Task 6.3)

**Modified files:**
- `tools/sla_lib/reader.py` (Task 0.1: add iterators)
- `tools/sla_lib/builder/document.py` (Tasks 1.1, 1.2, 1.3, 1.4)
- `tools/sla_lib/builder/primitives.py` (Tasks 1.5, 1.6, 1.7, 1.8)
- `tools/sla_lib/builder/ci.py` (Task 1.2 — `BrandColor` accepts native RGB; Task 1.3 — relocate or add `ParaStyle`/`CharStyle`)
- `tools/sla_lib/builder/__init__.py` (re-exports for new typed APIs)
- `tools/sla_lib/tests/test_reader.py` (Task 0.1: iterator tests)
- `templates/postkarte-a6-kampagne/build.py` (Task 2.4: replace placeholder)
- `templates/postkarte-a6-kampagne/meta.yml` (Task 2.4: add `original_sla:` and `ci_overrides:`)
- `templates/plakat-event/build.py` → `templates/plakat-a1-hochformat/build.py` (Tasks 3.1, 3.2, 7.1)
- `templates/plakat-event/meta.yml` → `templates/plakat-a1-hochformat/meta.yml`
- `templates/zeitung-a4-grun/build.py` (Task 4.6: replace placeholder)
- `templates/zeitung-a4-grun/meta.yml` (Task 4.6: add keys)
- `templates/zeitung-a4-grun/README.md` (Task 4.4: LANGUAGE inheritance note)
- `.github/workflows/pages.yml` (Task 6.1: validate-reproductions step, ImageMagick install, path-filtered triggers, AppImage cache)
- `README.md` (Task 7.3)
- Astro pages under `site/src/` referencing `plakat-event` (Task 7.1: rename references)

**Deleted (renamed via `git mv`):** `templates/plakat-event/` → `templates/plakat-a1-hochformat/` (Task 7.1).

**Untouched (CONTEXT.md constraints):**
- The three originals at workspace root are immutable.
- `shared/ci.yml` — D2 says document-local styles live in `build.py`, not in shared CI.
- `tools/render.py`, `tools/_export_pdf.py` — sanctioned headless render, reused unchanged.
- `tools/sla_lib/blocks.py` — block library stays for greenfield future templates; this issue's reproductions don't use it.

## Out of scope (preserved from CONTEXT.md)

- Bundled fonts and ICC profiles (separate deferred issue).
- LLM authoring tooling (deferred).
- Block-extraction tools (deferred).
- Visual-regression baseline-blessing UI (deferred).
- `raw_attrs={}` escape hatch in public DSL surface (D2: typed primitives only).
- Mutating `*-original.sla` files (immutable).
- Replacing the headless render pipeline (CONTEXT.md constraint: `xvfb-run -a scribus -g -ns -py tools/_export_pdf.py` is fixed).
- Adding `odiff` or any new image-diff dependency (RESEARCH.md §Tool selection: ImageMagick `compare` is sufficient at our 1% tolerance; `feedback_working_over_theoretical.md` supports keeping the working tool).

## Acceptance crosswalk

Maps each ISSUE.md acceptance criterion to the phase/task that delivers it.

| ISSUE.md acceptance criterion | Delivered by |
|---|---|
| `tools/sla_to_dsl.py` runs cleanly on all three originals, emits valid `build.py` files | Tasks 2.1, 2.2, 2.3 (Postkarte); 3.1 (Plakat); 4.1, 4.2, 4.3, 4.5 (Zeitung) |
| DSL `raw_attrs`, `custom_path`, per-run formatting, linked frames, soft-hyphens implemented and tested | Phase 1 entire (specifically: `custom_path` 1.6; per-run formatting 1.5; linked frames 1.7; soft-hyphens 1.5; ParaStyle/CharStyle 1.3). Note: per CONTEXT.md D2, `raw_attrs` is **not** added to the public surface; the criterion is satisfied by the typed APIs that replace it. |
| `tools/sla_diff.py` reports zero critical/warning differences between each original and its DSL reproduction | Phase 0 (sla_diff impl), Tasks 2.4 (Postkarte), 3.2 (Plakat), 4.6 (Zeitung) |
| `tools/visual_diff.py` reports < 1% pixel mismatch per page (configurable per template) | Phase 5 entire (impl in 5.2, baselines in 5.1, tolerances in 5.3, 150 dpi verify in 5.4) |
| All three `templates/<id>/template.sla` files are now DSL-built and faithful to their originals | Tasks 2.4, 3.2, 4.6 |
| CI workflow includes the validation step; it passes on `main` | Tasks 6.1, 6.2, 6.3 |
| Pages gallery now serves the faithful templates instead of the lookalike DSL output | Task 7.2 (audit + remove originals from `site/public/`) |
| Unit tests added for converter + diff tools, all green | `test_sla_diff.py` (Phase 0), `test_dsl_extensions.py` (Phase 1), `test_sla_to_dsl.py` (Phases 2–4), `test_visual_diff.py` (Phase 5) |
| README updated to describe the round-trip validation | Task 7.3 |

| CONTEXT.md "What done looks like" extras | Delivered by |
|---|---|
| `templates/<id>/build.py` exists for all three IDs; running `python build.py` produces a `template.sla` whose `sla_diff` against the original is clean | Tasks 2.4, 3.2, 4.6 |
| `templates/<id>/baseline.pdf` is committed; `visual_diff` against it is < 1% per page | Tasks 5.1, 5.3, 5.4 |
| `make validate` (or equivalent) runs the full pipeline locally | Task 7.3 (`bin/validate` shell entry point) |
| CI's `validate-reproductions` step is green on `main`; pages-deploy depends on it | Tasks 6.1, 6.2 |
| The DSL has typed expressions for every concept used in the originals; no `raw_attrs` escape hatches in user-visible API | Phase 1 entire; gate 1 verifies no `raw_attrs` in public exports |
| The site at `vorlagen.gruene.at` serves the DSL-built templates only | Task 7.2 |

## Final verification (run after Phase 7 closes)

```
# Round-trip structural check
python tools/sla_diff.py --left postkarte-vorlage-original.sla --right templates/postkarte-a6-kampagne/template.sla --strict
python tools/sla_diff.py --left plakat-a1-hochformat-original.sla --right templates/plakat-a1-hochformat/template.sla --strict
python tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right templates/zeitung-a4-grun/template.sla --strict

# Visual check (96 dpi for CI parity, 150 dpi for full coverage)
python tools/visual_diff.py templates/postkarte-a6-kampagne/template.sla --baseline templates/postkarte-a6-kampagne/baseline.pdf --dpi 150 --tolerance templates/postkarte-a6-kampagne/diff.yml --out build/postkarte/
python tools/visual_diff.py templates/plakat-a1-hochformat/template.sla --baseline templates/plakat-a1-hochformat/baseline.pdf --dpi 150 --tolerance templates/plakat-a1-hochformat/diff.yml --out build/plakat/
python tools/visual_diff.py templates/zeitung-a4-grun/template.sla --baseline templates/zeitung-a4-grun/baseline.pdf --dpi 150 --tolerance templates/zeitung-a4-grun/diff.yml --out build/zeitung/

# Test suite
python -m unittest discover tools/sla_lib/tests
```

All seven commands must exit 0.
