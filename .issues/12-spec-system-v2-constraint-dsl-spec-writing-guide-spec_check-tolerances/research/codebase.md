# Codebase Research — Issue #12 Spec-System v2

Date: 2026-05-08
Worktree: `/root/workspace/.worktrees/12-spec-system-v2-constraint-dsl-spec-writing-guide-spec_check-tolerances/`
Mandate: codebase dimension only (DSL surface, build patterns, validators, tests, CI).

---

## 1. DSL surface map (line-numbered)

### `tools/sla_lib/builder/__init__.py` (83 LoC)

Public re-exports — the **stable API surface** every build.py imports. The plan
must add new symbols here without breaking the existing list.

| Symbol | Source | Notes |
|---|---|---|
| `Document, Page` | `.document` | line 58 |
| `Color, Style, load_ci` | `.ci` | line 57 |
| `TextFrame, ImageFrame, Polygon, Line, Anchor, Run, pack_inline_image` | `.primitives` | line 59 |
| `DocumentLayer, ParaStyle, CharStyle, SoftShadow` | `.styles` | line 60 |
| `Brand` | `.brand` | line 61 |
| `blocks` (submodule) | `.` | line 62 — ALL block dataclasses live here |

`__all__` (lines 64-83) is the public contract. Per CONTEXT.md D1+D2, new
exports needed: `AlignedRow, AlignedColumn, MirroredPair, EqualGapStack,
GridCell, HierarchyBlock` (composites) plus `same_y, same_x, same_size,
mirrored_x, mirrored_y, inside, same_style, distance_y, distance_x, equal_gap,
hierarchy` (free-form constraints). Open question for plan: split into
`composites` + `constraints` submodules, or fold all into existing `blocks`.

### `tools/sla_lib/builder/primitives.py` (979 LoC)

The atomic frame types. Composition currently happens at `page.add()`-time
(see `Page.add` in document.py line 124-134 — anything with an `emit()` method
is unwrapped immediately into the flat `page.items` list).

| Class | Lines | Role |
|---|---|---|
| `Anchor` (frozen dc) | 113-165 | Position helper; `h ∈ {left,center,right}`, `v ∈ {top,center,bottom}`, `margin_mm` |
| `Run` (frozen dc) | 293-353 | Per-run text formatting (font, fontsize, fcolor, separator, var, var_attrs) |
| `_Frame` (dc) | 433-487 | **Common base** for primitives — holds `x_mm/y_mm/w_mm/h_mm/anchor/rotation_deg/layer/anname/custom_path/fill_rule/corner_radius_mm/soft_shadow/clip_edit/xpos_pt/ypos_pt/width_pt/height_pt`. Implements `_xy_pt(page)` (canvas-space) and `_wh_pt()`. |
| `TextFrame` | 540-744 | Extends `_Frame`. Adds `text/style/fcolor/runs/columns/col_gap_mm/vertical_text_align/text_align/default_linesp_mode/trail_style/trail_attrs/fill/line_color/line_width_pt/default_style_attrs/next_item`. Carries `_preallocated_id`. Has `link_to(other)` method (line 607-611) for chained text-flow. |
| `ImageFrame` | 764-841 | Extends `_Frame`. Adds `src/image/local_scale/local_offset_mm/local_rotation_deg/scale_type/ratio/pic_art/fill/line_color/inline_image_data/inline_image_ext`. |
| `Polygon` | 847-911 | Extends `_Frame`. Adds `fill/line_color/line_width_pt/shape ('rectangle'|'ellipse')/fill_shade/dash_pattern`. |
| `Line` (DEPRECATED) | 917-979 | Round-trip-unstable; converter prefers `Polygon`. Will warn on use. |

**Composition today:** None at primitive level. Every primitive is "leaf" — nothing wraps multiple frames. `_Frame` has `to_pageobject(idgen, page) -> etree._Element` (used by `Document._emit_page_item`, line 1071).

### `tools/sla_lib/builder/blocks.py` (909 LoC)

Existing block patterns. Each block is a `@dataclass` with an `emit()` method
returning an iterable of primitives. **Pattern signature varies:** some take
`emit(self)` (no page arg), some take `emit(self, page=None)`.

| Block | Lines | `emit()` signature | Yields |
|---|---|---|---|
| `PageNumber` | 68-131 | `emit(self)` | 1 `TextFrame` |
| `Impressum` | 139-174 | `emit(self)` | 1 `TextFrame` |
| `PageBackground` | 183-256 | `emit(self)` | 1 `Polygon` (oversize). Has `for_page(w, h, …)` factory at line 237-255 returning `_SizedPageBackground`. |
| `_SizedPageBackground` | 258-282 | `emit(self)` | 1 `Polygon` (page-correct dims) |
| `ContactBlock` | 290-340 | `emit(self)` | 1 `TextFrame` (multi-Run) |
| `ColumnTextStory` | 348-384 | `emit(self)` | N linked TextFrames via `link_to` |
| `WahlkreuzSymbol` | 391-455 | `emit(self, page=None)` | 1 `Polygon` (bg) + 1 `ImageFrame`. **Enforces D12** (lines 410-416): `ValueError` if `background_color in {"White","Gelb"}`. |
| `FoldLine` | 462-501 | `emit(self, page=None)` | 1 `Polygon` (custom_path on `Falz` layer) |
| `DieCut` | 508-544 | `emit(self, page=None)` | 1 `Polygon` (custom_path on `Stanzkontur` layer) |
| `FoldedPanel` | 550-581 | `emit(self, page=None)` | children + 1 `FoldLine` |
| `DoorHangerCutout` | 588-624 | `emit(self, page=None)` | 2 `DieCut` (outer + hole) |
| `TableTentFold` | 631-650 | `emit(self, page=None)` | 1 `FoldLine` |
| `legacy.*` (deprecated) | 654-909 | various | aspirational old blocks; lazy-loaded via `_LegacyProxy` (line 899-906) |

**Critical observation for D1:** `Page.add` (document.py:124-134) calls
`item.emit()` with NO arguments — but several blocks accept `emit(page=None)`.
So `page=None` works because of the default. Composite blocks per D1 should
follow `emit(self, page=None)` to match the existing widening pattern, AND
because composites that contain children need `page` for nested resolves
(`PageBackground.for_page` is the workaround; composites can do better).

**No `library.py` file exists yet** — the issue prompt mentioned it but it does
not exist in this worktree. `pack_inline_image` (primitives.py:750-761) is the
existing inline-image helper. (The prompt's mention of "Issue #13 — Centralized
library / LibraryImage / inject_into_frame" describes a target state not yet
in code. CONTEXT.md cross-refs Issue #13 as merged but no library.py is
present in this branch — confirm with planner before assuming.)

### `tools/sla_lib/builder/document.py` (1088 LoC)

The orchestrator. Key surfaces for D2 (constraint resolution):

| Surface | Lines | Notes |
|---|---|---|
| `Document.__init__` | 143-244 | `brand=`, `layers=`, `extra_doc_attrs=`, `extra_pdf_attrs=` etc. |
| `Document.add_color/add_para_style/add_char_style` | 247-271 | doc-local registrations |
| `Document.add_master/add_page` | 281-404 | returns `Page` |
| `Document.save(path)` | 407-410 | writes XML |
| `Document._build_xml` | 464-542 | builds the lxml tree (NOT idempotent — calls `_idgen = _IdGen()` reset at line 468) |
| `Page.add(item)` | 124-134 | **PRIMARY EXTENSION POINT.** If item has `emit()` it iterates and appends raw primitives to `self.items`. Otherwise appends item itself. Returns self. |
| `Page.items` | 116 | flat `list` of primitives (post-emit) |
| `Document.pages, Document.masters` | 165-166 | `list[Page]` |
| `_preallocate_chain_ids` | 412-461 | walks all `TextFrame`s in pages+masters, assigns IDs for `link_to` chains |

**No `Document.iter_all_primitives()` exists today.** The plan must either
(a) add it, or (b) have `structural_check.py` walk `[…doc.masters, …doc.pages]`
and concat each `.items` list (matches D2 requirement that constraint walker
sees the post-emit primitive list).

**Idiom for primitive iteration (recommended for new code):**
```python
def iter_all_primitives(doc) -> Iterable[_Frame]:
    for page in doc.masters + doc.pages:
        yield from page.items
```

Adding this as a `Document.iter_all_primitives()` method is a small, additive
change that keeps `structural_check.py` free of internal-list spelunking.

### `tools/sla_lib/builder/ci.py` (181 LoC)

Reads `shared/ci.yml`. Public:

| Symbol | Lines | Role |
|---|---|---|
| `BrandColor` | 29-52 | name, cmyk, spot, register, role, rgb_native; `cmyk_hex8` property |
| `BrandStyle` | 58-67 | name, font, fontsize, align, parent, linesp, fcolor, language |
| `BrandLayer` | 70-76 | name, level, visible, printable, editable |
| `_CI` (singleton) | 84-124 | loads ci.yml. Exposes `colors: dict[str, BrandColor]`, `fonts: list[str]`, `styles: dict[str, BrandStyle]`, `layers: list[BrandLayer]` |
| `load_ci(path)` | 130-135 | cached loader |
| `Color` | 140-157 | enum-like: `BLACK/WHITE/REGISTRATION/DUNKELGRUEN/HELLGRUEN/GELB/MAGENTA`. Class method `Color.all() -> list[str]`, `Color.get(name) -> BrandColor` |
| `Style` | 160-181 | enum-like: `HEADLINE_ULTRA/HEADLINE_VOLLKORN/BODY_12/BODY_11/IMPRESSUM/STOERER/CTA`. Methods `.all()` and `.get(name)` |

**Key insight for brand_constraints.py:** `Color.all()` and `Style.all()` give
the canonical allow-lists. `load_ci().fonts` gives the canonical font list.
These are the inputs for `rule_color_palette_only`, `rule_font_family_only`.

### `tools/sla_lib/builder/brand.py` (149 LoC)

`Brand.gruene_noe()` returns a `Brand` dataclass (line 41-149). When passed to
`Document(brand=...)`, all colors/styles/layers/doc/pdf attrs get auto-wired.
Brand-Constraints will run **after** `doc = build_template()` returns, so any
brand-loaded styles/colors are already in `doc._extra_para_styles`,
`doc._extra_colors`, `doc.ci.colors`, etc.

---

## 2. Build.py iteration patterns — refactor opportunities per template

| Template | LoC | Type | `build()` callable? | Composite-API fitness |
|---|---|---|---|---|
| `themen-plakat-a3-quer` | 301 | DSL-only | YES (line 44 — returns `out_path`) | **HIGH** — Phase 2 vorzeige per D9. Clear 3-column layout. |
| `wahlaufruf-postkarte-a6-quer` | 259 | DSL-only | YES (line 40) | HIGH — symmetric 2×2 cell grid; obvious `EqualGapStack`. |
| `wahltag-tueranhaenger` | 412 | DSL-only | YES (line 46) | MEDIUM — strict vertical, single column. Hierarchy-Block fits. |
| `infostand-tent-card-a5-quer` | 366 | DSL-only | YES (line 54) | MEDIUM — 2-panel symmetry around fold (MirroredPair around y=105). |
| `kandidat-falzflyer-din-lang` | 600 | DSL-only | YES (line 562) — split into `_add_styles/_add_front/_add_back` | HIGH — 6-panel grid; obvious AlignedRow on themen pairs (P4 t1+t2 share x=6, P4 t3+t4 share x=105). |
| `postkarte-a6-kampagne` | 369 | Production (round-trip) | **NO** — module-level `doc.save(...)` at end | **LOW for refactor.** Auto-generated by `sla_to_dsl.py`. Round-trip byte-stable required. |
| `plakat-a1-hochformat` | 198 | Production (round-trip) | **NO** | LOW. Auto-generated. |
| `zeitung-a4-grun` | 2463 | Production (round-trip) | **NO** | LOW. 3205-line auto-generated, 12 PageNumber blocks. |

### Key constraint per CONTEXT.md D10

For 3 production templates: SLA bytes must be byte-identical pre/post refactor.
This means composite-block use on production is essentially READ-ONLY — adding
CONSTRAINTS lists is fine (pure metadata), but reorganizing `page.add(...)`
sequences must produce IDENTICAL `page.items` order so emitted ItemIDs and
NEXTITEM/BACKITEM relations stay the same.

For 5 DSL-only templates: `previews_for_sla` SHA must remain stable. Same emit
order requirement.

### Refactor-target sketch — `themen-plakat-a3-quer/build.py` (Phase 2 vorzeige, per D9)

Current structure (build.py lines 130-292, 19 page.add calls):
```
1. page.add(Polygon "Seitenhintergrund" white full-bleed)
2. page.add(ImageFrame "Logo Grüne (top-left)" 15,10,32×28)
3. page.add(TextFrame "Headline These" 15,40,390×50)
4. page.add(TextFrame "Sub-Headline" 15,92,390×16)
5. for i,(hd,body,label) in enumerate(belege): 3× iterations →
   page.add(TextFrame "Beleg N — Headline" col_x,130,124×20)
   page.add(TextFrame "Beleg N — Body" col_x,152,124×70)
6. page.add(ImageFrame "Themen-Hero" 120,225,180×60)
7. page.add(ImageFrame "QR-Code (quelle)" 380,8,25×25)
8. page.add(TextFrame "Quelle" 15,287,80×8)
9. page.add(TextFrame "Impressum" 305,287,100×8)
```

Target (composite-refactored):
```python
# Construct frames first as named locals so CONSTRAINTS can reference them.
logo = ImageFrame(x_mm=15, y_mm=10, w_mm=32, h_mm=28, anname="Logo …")
qr   = ImageFrame(x_mm=380, y_mm=8, w_mm=25, h_mm=25, anname="QR-Code (quelle)")
headline = TextFrame(x_mm=15, y_mm=40, w_mm=390, h_mm=50, …, anname="Headline These")
sub      = TextFrame(x_mm=15, y_mm=92, w_mm=390, h_mm=16, …, anname="Sub-Headline")
beleg_hds = [TextFrame(x_mm=col_x_for(i), y_mm=130, w_mm=COL_W_MM, h_mm=20,
                       anname=f"Beleg {i+1} — Headline", style="…") for i in range(3)]
beleg_bds = [TextFrame(x_mm=col_x_for(i), y_mm=152, w_mm=COL_W_MM, h_mm=70,
                       anname=f"Beleg {i+1} — Body", style="…") for i in range(3)]
hero = ImageFrame(x_mm=120, y_mm=225, w_mm=180, h_mm=60, …)
quelle = TextFrame(x_mm=15, y_mm=287, w_mm=80, h_mm=8, …)
impressum = TextFrame(x_mm=305, y_mm=287, w_mm=100, h_mm=8, …)

# Compose with constraints (pure-deklarativ).
page.add(Polygon(…, anname="Seitenhintergrund", fill="White"))  # bg first
page.add(logo)
page.add(qr)
page.add(AlignedRow(y_mm=130, children=beleg_hds))   # forces y_mm on all 3
page.add(AlignedRow(y_mm=152, children=beleg_bds))   # forces y_mm on all 3
# OR: page.add(EqualGapStack(axis="x", gap_mm=8.0, children=beleg_hds))
page.add(headline)
page.add(sub)
page.add(hero)
page.add(quelle)
page.add(impressum)

CONSTRAINTS = [
    same_y(*beleg_hds, name="beleg_headlines_row"),
    same_y(*beleg_bds, name="beleg_bodies_row"),
    distance_y(headline, sub, equals=52.0, name="hl_to_sub"),  # 92-40=52
    distance_y(beleg_hds[0], beleg_bds[0], equals=22.0, name="beleg_hd_to_body"),
    same_style(*beleg_hds, name="beleg_hd_style_consistent"),
    same_style(*beleg_bds, name="beleg_body_style_consistent"),
    inside(qr, page),  # not actually needed — covered by page bounds. Skip.
]
```

**ASCII sketch of composite-refactor target:**

```
themen-plakat-a3-quer/build.py (post-refactor):

   ┌─────────────────── 420mm ───────────────────┐
   │ [logo]                       [qr]            │
   │                                              │
   │  AlignedRow(y_mm=40)  → headline (single)    │
   │  AlignedRow(y_mm=92)  → sub (single)         │
   │                                              │
   │  AlignedRow(y_mm=130) → [hd1] [hd2] [hd3]    │ ← composite #1
   │  AlignedRow(y_mm=152) → [bd1] [bd2] [bd3]    │ ← composite #2
   │                                              │
   │            [    themen-hero (centered)    ]  │
   │                                              │
   │  [quelle]                       [impressum]  │
   └──────────────────────────────────────────────┘

   CONSTRAINTS = [
       same_y(beleg_hds…),                    # redundant (composite enforces)
       same_y(beleg_bds…),                    # redundant
       distance_y(beleg_hds[0], beleg_bds[0], equals=22),
       same_style(beleg_hds, "themen-plakat/beleg-headline"),
       same_style(beleg_bds, "themen-plakat/beleg-body"),
   ]
```

For the OTHER 4 DSL templates, refactor naturalness:

- **wahlaufruf-postkarte-a6-quer:** front headline aligned center (single).
  Back has 4 cells in a 2×2 grid — `AlignedRow(y=22, children=[c1_hd, c2_hd])`,
  `AlignedRow(y=62, children=[c3_hd, c4_hd])`, plus `AlignedColumn(x=6,…)` and
  `AlignedColumn(x=78,…)` for the columns. Many natural composites.
- **wahltag-tueranhaenger:** strictly vertical column. `HierarchyBlock(headline,
  sub, body)` would assert font-size ordering between
  `tueranhaenger/headline (28pt)` > `tueranhaenger/sub (18pt)` > `tueranhaenger/body (11pt)`.
  Fewer alignment composites; mostly free-form constraints.
- **infostand-tent-card-a5-quer:** Two panels, A (y=0..105) and B (y=105..210, rotated).
  `MirroredPair(left=panel_A_hd, right=panel_B_hd, axis_mm=105.0)` would assert the
  vertical-mirror relationship around y=105 (the fold line). Awkward fit because Panel B
  is rotated 180° — the mirror is more semantic than geometric.
- **kandidat-falzflyer-din-lang:** Beautiful target. `AlignedRow(y_mm=20, children=[
  p4_t1_hd, p5_t3_hd, p6_kontakt_hd])` enforces "all panel-top headlines share y=20".
  Plus `AlignedColumn(x_mm=6, …)` for left-of-panel slots, etc. Many natural composites.
  The 2 themen-photos in P4 share `y_mm=36` (klimaschutz at y=36) and `y_mm=121`
  (soziales) — they form an `EqualGapStack(axis="y", gap_mm=85, …)` candidate.

### Awkward refactor cases

- **Production templates:** essentially can't refactor without breaking byte-stability. CONSTRAINTS list can still be added (pure metadata, no SLA bytes change).
- **Dynamic kandidat-falzflyer themen loops:** `for sname, photo, body, name_idx in (...)`-style loops should stay as loops; the resulting frames CAN feed an `AlignedRow` after construction (works because `AlignedRow.children` is a list).
- **Conditional inclusion** (e.g. `if portrait_path.exists()` in wahltag-tueranhaenger:309-322): composite must accept `None`-able children OR builds skip the composite when child missing. Plan should pick a convention.

---

## 3. structural_check.py orchestration — design notes

Reference pieces:

- **`tools/check_ci.py` (266 LoC)**: brand validator. Pattern:
  - argparse with `targets nargs="+"` + `--ci-file` + `--json` + `--strict` (lines 236-261)
  - Loads ci.yml dict (line 63-68), parses each SLA via lxml (line 197), calls `_scan_colors`/`_scan_styles` (lines 116-191)
  - Exit code: 1 on critical, 0 otherwise; --strict also fails on warnings (line 256-260)
  - Output formats: `format_report_text` (line 211-222) + `format_report_json` (line 225-233)
  - **Reuse:** Issue/CIDriftReport dataclass shape (lines 38-60) is exactly what structural_check needs.

- **`tools/sla_diff.py` (1250 LoC)**: differential validator. Pattern:
  - Markdown report writer `report_to_markdown` at line 1153-1182 — TEMPLATE for structural_check Markdown output.
  - Severity sort: `_SEVERITY_ORDER = {"critical":0, "warning":1, "info":2}` line 47.
  - Tolerance constants at top (lines 65-69): `POSITION_TOLERANCE_PT = 0.5`, etc.
  - Issue dataclass (lines 146-166).

- **`tools/spec_check.py` (212 LoC)**: spec ↔ build drift. Pattern:
  - Slug-keyed argparse: `slug` positional + `--all` flag (lines 175-179).
  - Iterates specs under `templates/_specs/*.md` (line 183-188).
  - Default tolerance `0.1mm` today (lines 178-179) — **NOTE: mismatch vs ISSUE.md text "1mm" — ISSUE description says "today 1mm" but code is `0.1`.** See §5 below.
  - Exit code per spec: drift→exit 1.

- **`tools/visual_review.py` (302 LoC)**: vision-review orchestrator. NOT CI; local-only. Imports modules dynamically? No — uses fixed list `ALL_TEMPLATES` (line 32-41). Composite via ImageMagick `montage` (line 82-93).

### Recommended structure for `tools/sla_lib/builder/structural_check.py`

Because it's an orchestrator that imports build.py modules and walks
emitted primitives, it should live as a script accessible from the repo root,
not buried inside `sla_lib`. The CONTEXT.md D3 path is
`tools/sla_lib/builder/brand_constraints.py` (the **rule set** module) and
the orchestrator should be `tools/structural_check.py` — co-located with
`tools/check_ci.py`, `tools/spec_check.py`, `tools/sla_diff.py`.

**Recommendation for plan:** clarify with planner:
- `tools/sla_lib/builder/brand_constraints.py` — module of `BRAND_CONSTRAINTS` rule predicates (per D3).
- `tools/structural_check.py` — CLI orchestrator (per existing tools/ convention).
- The CONTEXT.md text "tools/sla_lib/builder/structural_check.py" reads more naturally as the **rules-evaluator helper module**, with the CLI living as `tools/structural_check.py` mirroring `tools/spec_check.py`.

If the plan really wants both at `tools/sla_lib/builder/`, that's fine too — both are importable.

### Build-import strategy for D2 — the production-template asymmetry

| Template | How structural_check imports |
|---|---|
| 5 DSL-only (themen-plakat, wahlaufruf, wahltag, infostand, falzflyer) | `mod = importlib.import_module("templates.<slug>.build")` then `out = mod.build(out_path=tmp_sla)` returns the path. Doc is rebuilt fresh. **But:** structural_check needs the `Document` object, not the SLA file. Refactor build.py to expose `build_doc() -> Document` returning the unsaved doc, then `build(out_path)` calls `build_doc()` then `doc.save(out_path)`. |
| 3 production (postkarte, plakat-a1, zeitung) | Currently module-level `doc = Document(...); ...; doc.save(HERE/"template.sla")` — IMPORTING TRIGGERS THE FILESYSTEM WRITE. Plan must refactor: wrap module-level body in a `def build_doc() -> Document: ...; return doc` function. Move `doc.save()` into a `build(out_path)` function or under `if __name__ == "__main__":`. |

This refactor is a **PREREQUISITE** for structural_check.py. It does NOT change SLA bytes (the doc construction is identical) but changes the import side-effects. Plan must call out this refactor as Phase 1 step.

### Constraint resolver pseudocode (per D2 + D3)

```python
# tools/structural_check.py
import importlib

def check_template(slug: str) -> CheckReport:
    mod = importlib.import_module(f"templates.{slug}.build")
    if not hasattr(mod, "build_doc"):
        return CheckReport(slug, error=f"build.py missing build_doc() callable")
    doc = mod.build_doc()                          # Document, not saved
    primitives = list(_iter_all_primitives(doc))   # masters + pages, post-emit

    issues: list[Issue] = []
    # Brand-constraints (auto-applied unless meta.yml.brand_overrides lists rule.id)
    overrides = _load_meta_overrides(slug)
    for rule in BRAND_CONSTRAINTS:
        if rule.id in overrides:
            continue
        violations = rule(primitives, doc)
        for v in violations:
            issues.append(Issue("error", rule.id, …, v.detail))

    # Template-local CONSTRAINTS list
    for c in getattr(mod, "CONSTRAINTS", []):
        violations = c.check(primitives)
        for v in violations:
            issues.append(Issue("error", c.id, …, v.detail))
    return CheckReport(slug, issues=issues)


def _iter_all_primitives(doc) -> Iterable[_Frame]:
    for page in (*doc.masters, *doc.pages):
        yield from page.items
```

CLI surface mirrors spec_check.py:

```bash
tools/structural_check.py SLUG               # one template
tools/structural_check.py --all              # every renderable template
tools/structural_check.py --json out.json    # JSON output
tools/structural_check.py --markdown out.md  # Markdown report (default to stdout)
```

---

## 4. Brand-Constraints — quickguide rules in code (D3)

`shared/brand/QUICKGUIDE-NOTES.md` (2026-03-13, 226 LoC) — content already
mapped. Each rule below lists: source predicate, primitive walk, tolerance,
validation site.

### `rule_color_palette_only` (D3 rule 1)

**Quickguide source:** "all_colors ∈ ci.yml palette". `Color.all() = [Black,
White, Registration, Dunkelgrün, Hellgrün, Gelb, Magenta]`.
**Doc source:** all colors registered via `doc.add_color(...)` (e.g. spot colors
`Falz`, `Stanzkontur`) PLUS brand colors from `brand=Brand.gruene_noe()`.
**Walk:** every primitive's `fill`, `line_color`, `fcolor`. Plus all paragraph styles' `fcolor`. Plus all char styles' `fcolor`/`scolor`/`bgcolor`.
**Allow-list:** `Color.all() ∪ doc._extra_colors.keys()`.
**Tolerance:** none — discrete check.
**Sketch:**

```python
def rule_color_palette_only(primitives, doc) -> list[Violation]:
    allowed = set(Color.all()) | set(doc._extra_colors.keys()) | {"None"}
    violations = []
    for p in primitives:
        for attr in ("fill", "line_color", "fcolor"):
            v = getattr(p, attr, None)
            if v and v not in allowed:
                violations.append(Violation(p, attr, v, f"color {v!r} not in palette"))
    for ps in doc._extra_para_styles.values():
        if ps.fcolor and ps.fcolor not in allowed:
            violations.append(...)
    return violations
```

### `rule_font_family_only` (D3 rule 2)

**Quickguide:** "all_fonts ∈ {Gotham Narrow Ultra/Book/Bold/Black, Vollkorn Black Italic}".
**Doc source:** `load_ci().fonts` returns the brand list. Plus per-doc
ParaStyle/CharStyle `font` attrs.
**Walk:** every Run's `font`, every ParaStyle's `font`, every CharStyle's `font`,
every TextFrame's `default_style_attrs.get("FONT")`.
**Allow-list:** `load_ci().fonts ∪ {None}` (None = inherit).
**Tolerance:** none. Italic variants OK if base name matches (e.g.
"Gotham Narrow Book Italic" — needs to be in ci.yml fonts list).

```python
def rule_font_family_only(primitives, doc) -> list[Violation]:
    allowed = set(load_ci().fonts)
    violations = []
    for p in primitives:
        if isinstance(p, TextFrame):
            for r in (p.runs or []):
                if r.font and r.font not in allowed:
                    violations.append(...)
            if p.default_style_attrs and (f := p.default_style_attrs.get("FONT")):
                if f not in allowed:
                    violations.append(...)
    for ps in doc._extra_para_styles.values():
        if ps.font and ps.font not in allowed:
            violations.append(...)
    # Same for char styles
    return violations
```

**Note:** `Gotham Narrow Book Italic` is used in some templates
(`tueranhaenger/cand-pos`). It's NOT in `shared/ci.yml.fonts` (line 47-52).
Either add to ci.yml or this rule would warn. Plan must decide.

### `rule_line_spacing_factor_0_9` (D3 rule 3)

**Quickguide:** "linesp = Schriftgröße × 0.9" (Headlines) /
"linesp = Schriftgröße × 1.3" (body). The rule needs to disambiguate which
styles are headlines vs body.
**Walk:** every ParaStyle. Determine if it's a "headline-ish" style by name
heuristic (`fontsize >= 18pt OR name contains "headline"`).
**Predicate:** for headline styles: `linesp ≈ fontsize × 0.9` ± epsilon (~10%
relative tolerance). For body: `linesp ≈ fontsize × 1.3`.
**Tolerance:** ±10% relative (the Quickguide explicitly tolerates rounded
values like 28×0.9=25.2 → "rounded to 25-26 pt").

```python
def rule_line_spacing_factor_0_9(primitives, doc) -> list[Violation]:
    violations = []
    for ps in doc._extra_para_styles.values():
        if ps.fontsize is None or ps.linesp is None: continue
        is_headline = ps.fontsize >= 18 or "headline" in ps.name.lower()
        target_factor = 0.9 if is_headline else 1.3
        ratio = ps.linesp / ps.fontsize
        if abs(ratio - target_factor) / target_factor > 0.10:
            violations.append(Violation(ps.name, "linesp", ps.linesp,
                f"linesp/fontsize = {ratio:.2f}; expected {target_factor} ± 10%"))
    return violations
```

**Note:** QUICKGUIDE-NOTES line 67-68 already flags Türanhänger headline
linesp=30 for 28pt Vollkorn (ratio 1.07, target 0.9) as a known drift.
This rule will flag that drift — which is EXACTLY the pre-existing bug
this audit catches.

### `rule_hl_sl_distance_x2` (D3 rule 4)

**Quickguide:** `gap_HL_to_SL = X × 2` (X = Headline fontsize in pt).
**Walk:** find HL and SL frames. **Disambiguation challenge:** which TextFrame
is the headline vs the subline? Two strategies:
1. **By style name pattern:** `style.endswith("/headline") AND style2.endswith("/sub")`. Works for the 5 new templates (`themen-plakat/headline` + `themen-plakat/sub`).
2. **By anname pattern:** `anname starts with "Headline"` and `anname starts with "Sub"`.

Both patterns are fragile. **Recommendation for plan:** require explicit pairing
via a **`hierarchy(headline, subline, body, name="…")`** free-form constraint
that the build.py author writes, instead of auto-detection. Then this brand
rule is per-template-opt-in, but still exposed as a brand-rule helper.

OR: heuristic-based with structured violation messages so the user knows
WHERE to add the explicit pairing.

```python
def rule_hl_sl_distance_x2(primitives, doc) -> list[Violation]:
    # Pair by style-name pattern: x/headline + x/sub
    paras = doc._extra_para_styles
    pairs = []  # (hl_style, sl_style)
    for hname, hps in paras.items():
        if "/headline" in hname:
            base = hname.replace("/headline", "/")
            for sname, sps in paras.items():
                if sname.startswith(base) and "/sub" in sname:
                    pairs.append((hps, sps))
    # For each pair, find frames using each style and compute distance
    violations = []
    for hps, sps in pairs:
        hl_frames = [p for p in primitives if isinstance(p, TextFrame) and p.style == hps.name]
        sl_frames = [p for p in primitives if isinstance(p, TextFrame) and p.style == sps.name]
        if len(hl_frames) != 1 or len(sl_frames) != 1:
            continue  # ambiguous, skip
        target_gap_mm = (hps.fontsize * 2) / MM_TO_PT  # convert pt to mm
        actual_gap_mm = sl_frames[0].y_mm - (hl_frames[0].y_mm + hl_frames[0].h_mm)
        if abs(actual_gap_mm - target_gap_mm) / target_gap_mm > 0.20:
            violations.append(Violation(...,
                f"HL→SL gap = {actual_gap_mm:.1f}mm; target {target_gap_mm:.1f}mm (±20%)"))
    return violations
```

**Tolerance:** ±20% relative. The Quickguide flags Türanhänger (target 19.8mm,
actual 4mm) at "much closer than Quickguide suggests" — this rule would flag.

### `rule_logo_size_3M` (D3 rule 5)

**Quickguide:** `Logo-Breite = 3 × M`, `M = 0.06 × kurze_kante`. Print only;
digital is `2.5 × M`.
**Disambiguation:** find the "logo" ImageFrame. Heuristic: `anname` starts with
`Logo` (case-insensitive, German). All 8 templates use this convention
(checked: `Logo Grüne (top-left)`, `Logo Grüne (weiss)`, `Logo Grüne (Bund-Dunkel)`, …).
**Walk:** every ImageFrame whose `anname.lower().startswith("logo")`.
**Tolerance:** ±15% per QUICKGUIDE-NOTES line 102-117 ("within 15 % tolerance").

```python
def rule_logo_size_3M(primitives, doc) -> list[Violation]:
    page_w_mm, page_h_mm = _page_dims_mm(doc.pages[0])  # first page determines kurze_kante
    short_edge_mm = min(page_w_mm, page_h_mm)
    M = 0.06 * short_edge_mm
    target_w_mm = 3 * M
    violations = []
    for p in primitives:
        if not isinstance(p, ImageFrame): continue
        if not p.anname.lower().startswith("logo"): continue
        actual_w_mm = p.w_mm
        if abs(actual_w_mm - target_w_mm) / target_w_mm > 0.15:
            violations.append(Violation(p.anname, "w_mm", actual_w_mm,
                f"logo width {actual_w_mm:.1f}mm; target {target_w_mm:.1f}mm "
                f"(M={M:.2f}, kurze_kante={short_edge_mm}, ±15% tolerance)"))
    return violations
```

**Known violations (will flag pre-existing drift, per QUICKGUIDE-NOTES):**
- `wahltag-tueranhaenger` front Logo: 35×10mm, target 18.9mm → ~85% over
- `wahlaufruf-postkarte-a6-quer` back Logo: 30×9mm, target 18.9mm → ~58% over
- `infostand-tent-card-a5-quer` panel logos: 45×14mm, target 37.8mm → ~19% over

Plan must decide whether these existing violations get `meta.yml.brand_overrides`
to suppress, or get fixed in this issue (per CONTEXT.md "Refactor existierender
Templates auf Composite-Blöcke darf SLA-Output NICHT ändern" → likely
**suppress via override** for now; fix is separate hygiene issue).

### `rule_text_on_green` (D3 rule 6)

**Quickguide:** "Typografie steht immer in Kombination mit Grün" — text MUST sit
on Dunkelgrün or Hellgrün, NOT white.
**Disambiguation:** find each TextFrame using a CI brand style (`style.startswith("ci/")`
OR `style in {"Headline sehr wichtig", "Vollkorn Headline sehr wichtig", …}`); for each,
determine the "backing color" — the polygon directly under it on the same page
in `LAYER_HINTERGRUND` (or page background = white default).
**Walk:** for each TextFrame, find any Polygon on layer 0 whose bbox CONTAINS
the textframe's bbox.
**Predicate:** if backing fill ∈ {`Dunkelgrün`, `Hellgrün`, `Magenta`}: pass. Else (White, no backing): fail.

```python
def rule_text_on_green(primitives, doc) -> list[Violation]:
    violations = []
    bg_polys = [p for p in primitives if isinstance(p, Polygon) and p.layer == 0]
    for p in primitives:
        if not isinstance(p, TextFrame): continue
        if not _is_brand_typography(p.style): continue   # heuristic
        backing = _find_backing(p, bg_polys)
        if backing is None or backing.fill in {"White", "None", None}:
            violations.append(Violation(p.anname, "backing_color",
                backing.fill if backing else "White (default)",
                f"brand-typography frame on non-green backing"))
    return violations
```

**Known systemic violations** (per QUICKGUIDE-NOTES line 191-200): 4 of 8
templates have body-on-white. This rule will surface them en masse — most
likely needs `meta.yml.brand_overrides` per template.

### `rule_bleed_3mm` (D3 rule 7)

**Walk:** `doc.pages[0].bleed_mm` (and any add_page/add_master with custom bleed).
**Predicate:** `bleed_mm == 3.0`. Templates with stanze allowed `2.0` (e.g. wahltag-tueranhaenger).
**Allow-override:** `meta.yml.brand_overrides: [brand:bleed_3mm]` for stanze
templates, OR rule auto-detects `cut_type=die-cut` from meta.yml and accepts 2.0.

```python
def rule_bleed_3mm(primitives, doc) -> list[Violation]:
    violations = []
    for page in doc.pages + doc.masters:
        if abs(page.bleed_mm - 3.0) < 0.01:
            continue
        # OK if 2mm AND template has die-cut declared
        if abs(page.bleed_mm - 2.0) < 0.01 and _has_die_cut(doc):
            continue
        violations.append(Violation(f"page[{page.own_page}]", "bleed_mm",
            page.bleed_mm, "expected 3mm bleed (or 2mm with die-cut)"))
    return violations
```

### `rule_wahlkreuz_colored_bg` (D3 rule 8 — D12 from #10)

Already enforced in `WahlkreuzSymbol.emit()` (blocks.py:410-416) — `ValueError`
on `White`/`Gelb`. But that's CONSTRUCTION-time. The brand-rule walks emitted
primitives to verify no manual ImageFrame violates D12.
**Walk:** find every ImageFrame whose `anname.lower().contains("wahlkreuz")`. For
each, find any Polygon on layer 0 whose bbox CONTAINS the image. Predicate:
backing fill ∈ {`Dunkelgrün`, `Hellgrün`, `Magenta`}.

```python
def rule_wahlkreuz_colored_background(primitives, doc) -> list[Violation]:
    violations = []
    bg_polys = [p for p in primitives if isinstance(p, Polygon) and p.layer == 0]
    for p in primitives:
        if not isinstance(p, ImageFrame): continue
        if "wahlkreuz" not in p.anname.lower(): continue
        backing = _find_backing(p, bg_polys)
        if backing is None or backing.fill in {"White", "Gelb", "None", None}:
            violations.append(Violation(p.anname, "backing_color",
                backing.fill if backing else "White (default)",
                "Wahlkreuz must sit on Dunkelgrün/Hellgrün/Magenta (D12)"))
    return violations
```

### Summary table of D3 brand-rules

| Rule ID | Walk | Tolerance | Override-likely-needed (existing drift) |
|---|---|---|---|
| `brand:color_palette` | all primitives' fill/line_color/fcolor + ParaStyle.fcolor | none (discrete) | No (clean) |
| `brand:font_family` | Run.font + ParaStyle.font + CharStyle.font + default_style_attrs | none | Maybe (Gotham Narrow Book Italic not in ci.yml) |
| `brand:line_spacing_0.9` | all ParaStyles, classified by name/size | ±10% relative | Yes (Türanhänger) |
| `brand:hl_sl_distance_x2` | TextFrame pairs by style-name pattern | ±20% relative | Yes (Türanhänger) |
| `brand:logo_size_3M` | ImageFrame anname starts with "Logo" | ±15% relative | Yes (3 of 8 templates) |
| `brand:text_on_green` | TextFrame + bg-polygon containment | discrete fill check | Yes (4 of 8 templates) |
| `brand:bleed_3mm` | page.bleed_mm | discrete (3.0 ± 0.01, or 2.0 if die-cut) | Likely auto-handled |
| `brand:wahlkreuz_colored_bg` | ImageFrame anname contains "wahlkreuz" + bg containment | discrete | No (already construct-enforced) |

---

## 5. spec_check.py current state + needed changes (D8)

### Current state (`tools/spec_check.py`, 212 LoC)

| Aspect | Current | Target (D8) |
|---|---|---|
| Default tolerance | `0.1mm` (line 178-179) | `0.5mm` (per ISSUE.md "1mm → 0.5mm") |
| Drift classification | Single bin: drift exceeds tolerance → reported as `[drift]` (line 156-160) | TWO bins: under-tolerance → `[info]`; over → `[error]` |
| Slot YAML schema | Accepts ints AND floats (PyYAML `safe_load` returns `int` for `12`, `float` for `12.5`) — line 152 does `float(spec_v)` | Documented as "floats with 1 decimal" — accepted today already |
| Output | Markdown text via stdout (line 198-207) | Add `--json` + `--markdown` flags like sla_diff |
| Severity model | drift_count int + msgs list (line 168, line 196-208) | Replace with Issue-dataclass list (severity in {info,error}) |

### Note on the "1mm" claim in ISSUE.md

ISSUE.md line 38-40 says "heute zu strikt (1mm), flagged sub-mm-Refinements …".
But `tools/spec_check.py:178-179` shows default `--tolerance-mm 0.1` (i.e.
0.1mm). **Mismatch.** Likely the spec was written referring to a different
historical default, or the issue text is approximate. Plan must:
1. Confirm intended target is 0.5mm.
2. Define the info/error split as per D8: drift ≤ 0.5mm → `info`, drift > 0.5mm → `error`.

### Specific changes mapped to code

```diff
- ap.add_argument("--tolerance-mm", type=float, default=0.1,
+ ap.add_argument("--tolerance-mm", type=float, default=0.5,
                   help="Per-axis tolerance in mm (default 0.5)")

- if abs(spec_v - sla_v) > tolerance_mm:
-     msgs.append(f"  [drift] '{an}' {axis}: …")
-     drift += 1
+ delta = abs(spec_v - sla_v)
+ if delta > tolerance_mm:
+     issues.append(Issue("error", "slot-drift", an, axis, spec_v, sla_v, delta))
+ elif delta > 1e-6:
+     issues.append(Issue("info", "slot-minor-drift", an, axis, spec_v, sla_v, delta))
```

Plus exit-code logic:
- exit 0 if no `error`-severity issues
- exit 1 if any `error` (matches existing behavior intent)
- info-only is non-blocking (does NOT fail CI)

### Test impact

`tools/sla_lib/tests/` has no existing `test_spec_check.py`. New tests needed:
- Drift exactly at 0.5mm → info
- Drift at 0.51mm → error
- Drift at 5mm → error
- Floats in YAML (`x_mm: 12.5`) accepted

---

## 6. Spec-Writing-Guide — section structure proposal (§B)

### What current SCHEMA.md provides (templates/_specs/SCHEMA.md, 463 LoC)

| § | Topic | What it does |
|---|---|---|
| 1 | Pflichtfelder | Lists required YAML keys |
| 2 | Audience und Layout-Philosophie | Prose template |
| 3 | ASCII-Layout-Konvention | Box-drawing rules |
| 4 | Slot-Tabelle | Markdown table + embedded YAML |
| 5 | EPS / Image-Embedding | Wahlkreuz qcompress |
| 6 | Background-Color Contract für Wahlkreuz | D12 rule |
| 7 | Falz / Stanze | Coordinate-origin, spot colors |
| 8 | Brand-Hierarchy Contract | Min-fontsizes per format, palette, whitespace |
| 9 | Print-Hints | YAML print_hints block |
| 10 | Messaging-Legality | NRWO §53 Wahlanleitung |
| 11 | Drift-Policy | spec_check refs |

**SCHEMA.md is FORMAT.** It tells you the keys and conventions. It does NOT
explain HOW TO WRITE a good spec.

### What Spec-Writing-Guide must add (per ISSUE.md §B and what Issue #10/#11
showed was unclear)

Proposed structure for `shared/brand/SPEC-WRITING-GUIDE.md`:

```markdown
# Spec-Writing-Guide

## Welche Fragen MUSS eine Spec beantworten

### Pflicht — funktional
1. Zielgruppe? (1-3 Audience-Tags + 1-Satz-Persona pro Tag)
2. Verwendungs-Situation? (Wo, wann, in welchem Kontext)
3. Hauptbotschaft? (1 Satz, max 80 Zeichen)
4. Lesbarkeits-Kriterium / 1-Sek-Test? (Was muss in 1 Sekunde erkennbar sein)
5. Welche Aktion(en) soll Empfänger:in ausführen? (CTA explizit)
6. Druck-Output? (Format, Material, Stanzform, Falz, Auflage)

### Pflicht — visuell
7. Layout-Philosophie? (1-Satz: was die Komposition vermittelt)
8. Hierarchie-Order? (Welche 3-5 Elemente sind in welcher Reihenfolge dominant)
9. Hero-Brand-Farbe? (Dunkelgrün/Hellgrün/Magenta + welche Akzente)
10. Typo-Mischung? (Vollkorn-Italic-Highlight ja/nein, wo)
11. Wahlkreuz mit Hintergrund-Vertrag? (D12 — wenn ja, welche Hintergrund-Farbe)
12. Bilder Pflicht/optional/verboten?
13. Whitespace-Charakter? (großzügig / kompakt — qualitativ)

### Pflicht — strukturell
14. Trim + Bleed + Falz/Stanze in mm
15. Slot-Liste mit anname, Position, Maße, Style-Ref, Pflicht/optional, Max-Chars
16. Lese-Reihenfolge (welcher Slot wird in welcher Reihenfolge gelesen)
17. Cross-Element-Beziehungen in Prosa (Constraint-Refs per Code-Identifier)

### Pflicht — Constraints
18. Was gilt strukturell zwingend? (Prosa-Beschreibung WAS + WARUM)
19. Verweis auf Code-Constraints per Name (`siehe CONSTRAINTS["themen_row_alignment"]`)
20. Brand-Constraints-Abweichungen (falls Template `meta.yml.brand_overrides`)

### Empfohlen — Druckpraxis
21. Spot-Colors (wenn ja, welche)
22. Min-DPI für Bilder
23. Druckerei-Anforderungen (Papier, Farbprofil)

### Empfohlen — Endnutzer:innen-Workflow
24. Welche Slots werden am häufigsten ersetzt?
25. Welche Slots dürfen NICHT angefasst werden? (Brand-Anker)
26. Geschätzter Anpassungs-Aufwand (15min / 1h / 1d)
27. Realistische Text-Längen (Hauptheadline: 30-60 Zeichen; Body: 200-400 Zeichen)
28. Beispieltexte (3 thematische Varianten)

### Optional — Robustheit
29. Verhalten bei Übertext-Slot
30. Layout-brechende Slot-Combos
31. Anti-Patterns / häufige Fehler

### Optional — Provenance
32. Owner, Review-Datum, Version

## Pro Sektion

Pro Sektion: Mini-Anleitung + Beispiel aus den 8 existierenden Specs +
Anti-Pattern.

## Worked Example

End-to-end: Slot-Layout in der Spec → Code-Constraint mit Identifier →
Spec-Prosa die darauf verweist → was der Constraint-Checker prüft.

## Review-Checkliste

10-15 Fragen vor Implementation-Freigabe. Bullets, ja/nein.

## Common Pitfalls aus Issue #10/#11

[Liste der typischen Spec-Lücken aus erlebten Iterationen]
```

### Patterns observed in existing 5 specs (for inspiration)

Looking at `templates/_specs/themen-plakat-a3-quer.md` (302 LoC) — the well-written reference:

- Has explicit `## Brand-Hierarchy Contract` with table of fontsize+font+color per layer (lines 226-234). **Strong pattern.**
- Has `## Brand-Accent — bewusste Auslassung` (line 277-286) — **excellent — explicit reasoning for absence.**
- Has `## Style-Hygiene` (line 288-301) listing all template-local styles. **Strong pattern.**
- `## Constraints` section is THIN (lines 61-72) — only 6 bullet points. Spec-System v2 expands this to full prose + code-refs.

Looking at the 5 new specs as a class — observed inconsistencies:
- Some have `## Audience und Layout-Philosophie` (themen-plakat:16), others have `## Audience` + separate `## Layout-Philosophie`.
- Slot tables sometimes have `style_ref` referencing `shared/logos/...` paths (image source) instead of paragraph styles. SCHEMA.md allows this; spec-writing-guide should clarify.
- `## EPS / Image-Embedding-Strategie` is sometimes empty ("Keine") — in 4 of 5 new specs. SCHEMA.md says "Nur erforderlich" but writers fill in even when N/A.
- `## Background-Color Contract für Wahlkreuz` likewise often "Nicht zutreffend".

**Plan recommendation:** Spec-Writing-Guide should provide a "minimal-spec
template" (markdown skeleton) that authors fill in, omitting N/A sections
explicitly rather than including empty headers.

### Self-meta-consistency check (per CONSTRAINTS)

The Spec-Writing-Guide must follow its own schema. So the guide itself has:
- audience: spec authors (humans + LLMs)
- layout: prose document with tables and worked examples
- constraints: any spec must answer §B's questions
- brand: applies only obliquely (brand voice = direct, German, factual)

This satisfies "selbst dem eigenen Schema folgend" (CONTEXT.md D6).

---

## 7. Backward-Compatibility verification recipe (D10)

### How `previews_for_sla` SHA works

`tools/render_pipeline.py` (706 LoC):
- `_orchestrate_single` (line 447-486) calls `_sha256_of(template_sla)` (line 480)
  which is `hashlib.sha256(p.read_bytes()).hexdigest()` (helper at line 47-49 of
  `tools/check_stale_previews.py`).
- The hash is written to `meta.yml::previews_for_sla` via `_update_meta_hash`
  (line 291-...). The format is a single-line YAML key for non-family
  templates (line 307-308), or a multi-line dict for family.
- `tools/check_stale_previews.py:_check_template` (line 52-131) compares
  `_sha256_of(tdir/"template.sla")` against `meta["previews_for_sla"]`.
  Mismatch → exit 1.
- CI (.github/workflows/pages.yml:110) calls `bin/check-stale-previews` as
  preflight to validate.

### Byte-determinism contract

`Document._build_xml` (document.py:464-542):
- `_idgen = _IdGen()` reset at line 468 — IDs always start from 100_000_000.
- Pre-allocates chain IDs depth-first (line 470, `_preallocate_chain_ids` line 412-461).
- Then walks pages+masters in fixed order: masters first, doc pages second
  (lines 510-540).
- Within each page, items are emitted in `page.items` list order (line 539-540).

**Critical: composite-block emit ORDER must be deterministic.**
- `Page.add(item)` (line 124-134): if `hasattr(item, "emit")`, the emit yields
  primitives in order, and they're appended to `self.items` in yield order.
- A composite like `AlignedRow(children=[c1, c2, c3])` MUST yield c1 before c2
  before c3 — never shuffle. Plan should specify: `def emit(self): yield from self.children`.
- Same constraint for `EqualGapStack`, `MirroredPair`, `GridCell`.

### Round-trip diff verification (production templates)

For each of postkarte/plakat-a1/zeitung:
```bash
python3 tools/sla_diff.py \
    --left  <original.sla> \
    --right templates/<slug>/template.sla \
    --strict --allow-brand-extras
```
This must remain GREEN (exit 0) after refactor. The composite-blocks must
emit primitives whose `to_pageobject()` output is byte-equal to the manual
construction.

### Pre→post verification recipe (Phase 2 vorzeige refactor)

```bash
# BEFORE refactor — capture baseline
git rev-parse HEAD > /tmp/pre.commit
cp templates/themen-plakat-a3-quer/template.sla /tmp/pre.sla
sha256sum templates/themen-plakat-a3-quer/template.sla > /tmp/pre.sha

# Apply refactor (composite-blocks + CONSTRAINTS list)
# ... edit build.py ...

# AFTER refactor — rebuild
python3 templates/themen-plakat-a3-quer/build.py
sha256sum templates/themen-plakat-a3-quer/template.sla > /tmp/post.sha

# Compare
diff /tmp/pre.sha /tmp/post.sha
# IF identical: byte-stable refactor (preferred)
# IF different: run sla_diff in semantic mode
python3 tools/sla_diff.py --left /tmp/pre.sla \
    --right templates/themen-plakat-a3-quer/template.sla \
    --strict --allow-brand-extras
# Must exit 0 (no critical, no warning).

# Also verify visual rendering didn't change
python3 tools/visual_diff.py templates/themen-plakat-a3-quer/template.sla \
    --baseline templates/themen-plakat-a3-quer/baseline.pdf \
    --tolerance templates/themen-plakat-a3-quer/diff.yml
```

### previews_for_sla SHA stability per template

After a clean refactor:
- All 5 DSL-only templates' `meta.yml::previews_for_sla` SHA values must match the values currently on `main` after `bin/render-gallery` is rerun.
- All 3 production templates' template.sla bytes must be identical to current.

### Enforce in CI

CI already runs `bin/check-stale-previews` (workflow pages.yml:110). After the
refactor PR, if SHA values change, CI will fail with "Gallery previews are stale"
unless `bin/render-gallery` was rerun + committed. The plan should include:

- Run `bin/render-gallery` after refactor.
- If SHA values for 5 DSL-only changed → manual review (must verify the
  changes are SOLELY structural-metadata, e.g. `_preallocated_id` allocation
  shifted but no PAGEOBJECT XPOS/YPOS changed).
- If SHA values for 3 production changed → **STOP** and investigate. These
  must be byte-stable.

---

## 8. CI integration plan + performance budget

### Where existing tools run in CI (.github/workflows/pages.yml)

| Step | Line | Action |
|---|---|---|
| Build smoke | 73-82 | `for build in templates/_smoke/*/build.py; do python3 "$build"; done` (production templates NOT rebuilt) |
| Generate gallery | 85 | `python3 tools/gallery_build.py` (renders previews, hashes) |
| Run unit tests | 102 | `python3 -m unittest discover tools/sla_lib/tests` |
| Validate reproductions | 104-130 | `bin/check-stale-previews` + `tools/sla_diff.py --strict --allow-brand-extras` per of 3 production templates |
| Run brand validator | 132-136 | `tools/check_ci.py` per SLA |

### New step for structural_check (D11 budget: <5s/template)

Insert after "Run brand validator", before "upload-pages-artifact":

```yaml
- name: Run structural_check
  run: |
    set -euo pipefail
    for spec in templates/_specs/*.md; do
      slug=$(basename "$spec" .md)
      [ "$slug" = "SCHEMA" ] && continue
      [[ "$slug" = _existing-* ]] && continue
      echo "=== structural_check $slug ==="
      python3 tools/structural_check.py "$slug" --markdown "build/validation/${slug}-structural.md"
    done

- name: Run spec_check (with new tolerance)
  run: python3 tools/spec_check.py --all --tolerance-mm 0.5
```

OR via `bin/validate`:

```bash
# Add to bin/validate after the existing checks
echo "=== structural_check ==="
if ! python3 tools/structural_check.py --all; then
    EXIT=1
fi
echo "=== spec_check ==="
if ! python3 tools/spec_check.py --all; then
    EXIT=1
fi
```

### Performance budget per CONTEXT.md D11

- structural_check per template: <5s. Walk size for typical template:
  themen-plakat-a3-quer has 13 emitted primitives. Walking 13 primitives
  through 8 brand rules + ~5 template-local constraints = <100 ops. Easily <100ms.
- For Zeitung-A4-grun: 2463-line build.py emits ~870 primitives across 14 pages.
  Walking 870 through 8 brand rules = ~7000 ops. Likely <1s on Python+lxml.
  Well within budget.
- importlib import of build.py is the long-pole — building doc takes
  500-1500ms for the larger templates. With 8 templates at ~1.5s each = ~12s
  total CI time (one-time per CI run). Within D11's <30s total target.

### CI dependencies

No new pip deps needed (per CONTEXT.md). Pure-Python on existing PyYAML + lxml +
Pillow + qrcode + pyzbar (already installed at workflow line 53-55).

### Performance budget today (last main run, PR #27)

To estimate: existing CI run includes Scribus AppImage download (cached after
first run), unit tests (~50s typical), preview rendering (~3min — Scribus
xvfb-run is slow), sla_diff (~5s × 3 templates = ~15s). Total typical ~6-8min.

Adding structural_check + spec_check adds ~15-20s. Well within tolerance —
total run still <10min. **No CI optimization needed.**

---

## 9. Test infrastructure — pattern inventory

### `tools/sla_lib/tests/` directory (16 test files, 4961 total LoC)

| File | LoC | Pattern |
|---|---|---|
| `test_blocks.py` | 521 | unittest.TestCase subclasses, one per block. Helpers `_save(doc) → SLADocument` (parsed view) and `_save_to_str(doc) → str` (raw XML). 6+ tests per block. |
| `test_brand.py` | 192 | unittest pattern, `setUp()` instantiates Brand. |
| `test_builder.py` | 162 | basic Document + Page tests |
| `test_dsl_extensions.py` | 686 | extended DSL features |
| `test_check_ci.py` | 112 | tests for the brand validator |
| `test_sla_diff.py` | 986 | extensive diff tests |
| `test_render_pipeline.py` | 279 | render orchestration tests |

### Pattern for testing constraint-violations

Tested via construction-then-walk pattern. Reference: `test_blocks.py` lines
84-87 (`test_pagenumber_round_trips_through_emit`):
- Build minimal doc with the constraint
- Emit the doc (just-in-memory; doesn't need to save)
- Assert primitives match expected layout

For new constraint tests:
```python
def test_same_y_passes_when_aligned(self):
    f1 = TextFrame(x_mm=0, y_mm=30, w_mm=20, h_mm=10)
    f2 = TextFrame(x_mm=30, y_mm=30, w_mm=20, h_mm=10)
    f3 = TextFrame(x_mm=60, y_mm=30, w_mm=20, h_mm=10)
    c = same_y(f1, f2, f3)
    self.assertEqual(c.check([f1, f2, f3]), [])  # no violations

def test_same_y_violates_when_misaligned(self):
    f1 = TextFrame(x_mm=0, y_mm=30, w_mm=20, h_mm=10)
    f2 = TextFrame(x_mm=30, y_mm=31, w_mm=20, h_mm=10)  # 1mm off
    c = same_y(f1, f2)
    violations = c.check([f1, f2])
    self.assertEqual(len(violations), 1)
```

### Existing convention for issue-coverage tests

Each acceptance criterion mentioned in CONTEXT.md has min test counts:
- D1 — Composites: "Min. 6 unit-tests pro Block" → ~36 tests
- D2 — Free-form: "Min. 4 unit-tests pro Constraint" → ~40 tests (10 constraints × 4)
- D3 — Brand-Constraints: "Min. 8 globale Brand-Constraints" + tests
- structural_check.py: ~5-10 integration tests
- spec_check.py changes: ~5 new tests

Total new tests: ~95+. Existing test count is in 1000s — easily absorbable.

---

## 10. Migration pitfalls + safety nets

### Pitfall 1: Production-template module-level imports
- 3 of 8 templates (postkarte, plakat-a1, zeitung) execute `doc.save()` at IMPORT TIME (line 368 of postkarte build.py: `doc.save(HERE / "template.sla")`).
- `importlib.import_module("templates.postkarte-a6-kampagne.build")` will TRIGGER A FILESYSTEM WRITE.
- structural_check.py would silently regenerate template.sla → SHA changes → check-stale-previews fails.
- **Fix:** wrap module-level body in `def build_doc() -> Document:` function. Add `if __name__ == "__main__":  build_doc().save(HERE/"template.sla")` guard.
- **Verify byte-stability:** rebuild after refactor; SHA must match.
- **Plan task:** "Refactor 3 production build.py to expose `build_doc()` callable".

### Pitfall 2: Composite-block emit-order non-determinism
- Composite must emit children in fixed order. `dict` is ordered in Python 3.7+ but `set` is NOT.
- `for child in self.children:` is correct.
- `for k, v in some_dict.items():` is correct.
- `for x in some_set:` is FORBIDDEN.
- **Plan task:** Lint check / code review for set-iteration in composite emit().

### Pitfall 3: Constraint identifier resolution via id() requires same instance
- D2 says Frame-Objekte werden über ihre `id()` (Python object identity) wiedergefunden.
- This works IF `same_y(f1, f2, f3)` and `page.add(f1)` reference THE SAME Python object.
- DOES NOT WORK if build.py constructs `f1 = TextFrame(...)`, then later constructs a `copy(f1)` for emission. (Composite-blocks that wrap-and-modify children may do this.)
- **Convention to enforce:** composites do NOT clone children. They emit them as-is.
- **Plan task:** AlignedRow.emit() must not modify children — the design says "force y_mm". This means MUTATING the child's `y_mm` attribute in-place. Frames are `@dataclass` (default mutable) — this works.
- **Risk:** mutation in `emit()` is surprising. Multiple `page.add(AlignedRow(...))` on the same children (rare) would re-mutate.
- **Decision for plan:** mutation in-place is acceptable IF it happens only in `emit()` (called once per page.add()). Document the convention.

### Pitfall 4: Brand-rule false positives on production templates
- Per QUICKGUIDE-NOTES, 4-5 of 8 templates have known existing drift (logo size, text-on-white, headline linesp). Brand-rules will surface these as violations.
- **CONSTRAINTS budget:** none of these are NEW bugs introduced by refactor — they're pre-existing.
- **Mitigation:** `meta.yml.brand_overrides: [brand:logo_size_3M, brand:text_on_green, ...]` per affected template, with a YAML comment explaining why.
- **Plan task:** During Phase 3 template-by-template refactor, add `brand_overrides` for each known drift, with comment citing QUICKGUIDE-NOTES.

### Pitfall 5: Spec-Writing-Guide refers to constraints that don't exist yet
- The guide cites `siehe CONSTRAINTS["themen_row_alignment"]` — but the
  example only works once the actual templates have CONSTRAINTS lists with
  named constraints.
- **Phase ordering:** Spec-Writing-Guide is Phase 4 (CONTEXT.md), AFTER template
  refactor in Phase 3. So this works — by Phase 4, real constraint identifiers
  exist to cite.

### Pitfall 6: spec_check tolerance change might silently mask existing drift
- Current tolerance is 0.1mm; new is 0.5mm. So drift between 0.1mm and 0.5mm
  that was previously flagged as `[drift]` and failed CI will now be `info`
  (non-blocking).
- This is intentional per ISSUE.md (sub-mm refinements are normal). But
  potential to silently regress.
- **Mitigation:** before tolerance change, run `tools/spec_check.py --all` and
  audit current drift. Any slot drift in 0.1mm < d < 0.5mm range gets
  documented as "sub-mm acceptance". Ideally fix the spec by aligning to
  the build (since the build is the source of truth per CONTEXT.md D6).
- **Plan task:** Phase 4 includes "audit current spec drift, align specs to
  builds where 0.1mm < drift < 0.5mm".

### Pitfall 7: visual_diff baseline staleness
- The 3 production templates have `baseline.pdf` files used by `tools/visual_diff.py`. If structural_check or spec_check induces ANY rebuild side-effect on production template.sla, the visual_diff will fail.
- **Mitigation:** Pitfall 1 fix (no import-time saves) + careful review.

### Pitfall 8: legacy blocks lazy-load via exec()
- `blocks.py:889-906` uses `exec(compile(_legacy_src, …))` to lazily load 12
  deprecated blocks. This means linting tools may not catch issues in legacy
  code.
- Composite-blocks should NOT live in legacy. They should live in
  `blocks.py` proper or a new `composites.py` module per CONTEXT.md.

### Safety-net: comprehensive test pass after refactor

```bash
# Full unit-test sweep
python3 -m unittest discover tools/sla_lib/tests

# Per-template structural_check
python3 tools/structural_check.py --all

# Per-spec spec_check (with new 0.5mm tolerance)
python3 tools/spec_check.py --all

# Round-trip diff for 3 production
bin/validate  # runs sla_diff + visual_diff per production template

# Stale-preview gate
bin/check-stale-previews
```

All five must exit 0 before merge.

---

## 11. Files relevant to this issue (line-numbered table)

| File | LoC | Relevance | Last touched |
|---|---|---|---|
| `tools/sla_lib/builder/__init__.py` | 83 | EXTEND: add composite + constraint exports | recent |
| `tools/sla_lib/builder/primitives.py` | 979 | READ-ONLY for D1/D2 (composite layer is built ABOVE primitives) | recent |
| `tools/sla_lib/builder/blocks.py` | 909 | EXTEND or sibling-module: add `AlignedRow/AlignedColumn/MirroredPair/EqualGapStack/GridCell/HierarchyBlock` | recent |
| `tools/sla_lib/builder/document.py` | 1088 | EXTEND: add `Document.iter_all_primitives()` | recent |
| `tools/sla_lib/builder/ci.py` | 181 | READ-ONLY (Color.all() / Style.all() / load_ci().fonts are inputs to brand_constraints) | older |
| `tools/sla_lib/builder/brand.py` | 149 | READ-ONLY | recent |
| `tools/sla_lib/builder/styles.py` | 140 | READ-ONLY | older |
| **NEW** `tools/sla_lib/builder/brand_constraints.py` | — | CREATE: 8 brand rules per D3 | — |
| **NEW** `tools/sla_lib/builder/constraints.py` (proposed) | — | CREATE: free-form constraint primitives (same_y, distance_y, etc.) | — |
| **NEW** `tools/sla_lib/builder/composites.py` (proposed) | — | CREATE: AlignedRow et al. (alternative: extend blocks.py) | — |
| **NEW** `tools/structural_check.py` | — | CREATE: orchestrator CLI per spec_check.py pattern | — |
| `tools/spec_check.py` | 212 | MODIFY: tolerance 0.1→0.5mm, info/error split, Issue dataclass | recent |
| `tools/check_ci.py` | 266 | READ-ONLY (reference for Issue/Report dataclass shape) | older |
| `tools/sla_diff.py` | 1250 | READ-ONLY (reference for markdown output) | recent |
| `tools/visual_review.py` | 302 | READ-ONLY (local-only, no changes here) | recent |
| `tools/render_pipeline.py` | 706 | READ-ONLY (SHA flow already correct) | recent |
| `tools/check_stale_previews.py` | 162 | READ-ONLY (preflight gate already correct) | recent |
| `templates/_specs/SCHEMA.md` | 463 | EXTEND: add §C constraint-prosa convention | recent |
| **NEW** `shared/brand/SPEC-WRITING-GUIDE.md` | — | CREATE: full §B authoring guide | — |
| `templates/themen-plakat-a3-quer/build.py` | 301 | REFACTOR Phase 2: composite use + CONSTRAINTS | recent |
| `templates/wahlaufruf-postkarte-a6-quer/build.py` | 259 | REFACTOR Phase 3 | recent |
| `templates/wahltag-tueranhaenger/build.py` | 412 | REFACTOR Phase 3 | recent |
| `templates/infostand-tent-card-a5-quer/build.py` | 366 | REFACTOR Phase 3 | recent |
| `templates/kandidat-falzflyer-din-lang/build.py` | 600 | REFACTOR Phase 3 | recent |
| `templates/postkarte-a6-kampagne/build.py` | 369 | REFACTOR (build_doc()-wrapping only, NO byte change) | recent |
| `templates/plakat-a1-hochformat/build.py` | 198 | REFACTOR (build_doc()-wrapping only) | recent |
| `templates/zeitung-a4-grun/build.py` | 2463 | REFACTOR (build_doc()-wrapping only) | recent |
| `templates/_specs/themen-plakat-a3-quer.md` | 302 | UPDATE Phase 4: reference to CONSTRAINTS | recent |
| `templates/_specs/<other 4 specs>.md` | various | UPDATE Phase 4: reference to CONSTRAINTS | recent |
| `templates/<each>/meta.yml` | <50 each | OPTIONAL UPDATE: `brand_overrides:` for known-drift-templates | recent |
| `bin/validate` | 90 | EXTEND: invoke structural_check + new spec_check | older |
| `.github/workflows/pages.yml` | 152 | OPTIONAL: explicit step for structural_check (or rely on bin/validate) | recent |
| `tools/sla_lib/tests/` | 4961 | EXTEND: tests for composites + constraints + brand-rules + structural_check + new spec_check | recent |

---

## 12. `<interfaces>` blocks

```python
# ============================================================================
# EXISTING — DSL primitives (READ-ONLY references for plan)
# tools/sla_lib/builder/primitives.py
# ============================================================================
@dataclass(frozen=True)
class Anchor:
    h: str = "left"            # "left" | "center" | "right"
    v: str = "top"             # "top"  | "center" | "bottom"
    margin_mm: float = 0.0

@dataclass(frozen=True)
class Run:
    text: str = ""
    has_itext: bool = True
    font: Optional[str] = None
    fontsize: Optional[float] = None
    fcolor: Optional[str] = None
    fshade: Optional[int] = None
    fontfeatures: Optional[str] = None
    features: Optional[str] = None
    kern: Optional[float] = None
    underline_position: Optional[int] = None
    strike_position: Optional[int] = None
    char_style: Optional[str] = None
    paragraph_style: Optional[str] = None
    paragraph_attrs: Optional[dict] = None
    separator: Optional[str] = None    # "para" | "breakline" | "tab" | "breakcol" | "breakframe"
    var: Optional[str] = None          # "pgno"
    var_attrs: Optional[dict] = None

@dataclass
class _Frame:
    x_mm: float = 0
    y_mm: float = 0
    w_mm: float = 50
    h_mm: float = 30
    anchor: Optional[Anchor] = None
    rotation_deg: float = 0
    layer: int = 2                     # default Text layer
    anname: str = ""
    custom_path: Optional[str] = None
    fill_rule: Optional[int] = None
    corner_radius_mm: float = 0
    soft_shadow: Optional[SoftShadow] = None
    clip_edit: bool = False
    xpos_pt: Optional[float] = None
    ypos_pt: Optional[float] = None
    width_pt: Optional[float] = None
    height_pt: Optional[float] = None

    def _xy_pt(self, page) -> tuple[float, float]:
        ...
    def _wh_pt(self) -> tuple[float, float]:
        ...

@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""            # paragraph style name
    fcolor: str = ""
    runs: Optional[list] = None
    columns: int = 1
    col_gap_mm: float = 4
    vertical_text_align: Optional[int] = None
    text_align: Optional[int] = None      # deprecated alias
    default_linesp_mode: Optional[int] = None
    trail_style: Optional[str] = None
    trail_attrs: Optional[dict] = None
    fill: Optional[str] = None            # PCOLOR
    line_color: Optional[str] = None      # PCOLOR2
    line_width_pt: float = 0
    default_style_attrs: Optional[dict] = None
    next_item: Optional["TextFrame"] = field(default=None, repr=False, compare=False)

    def link_to(self, other: "TextFrame") -> "TextFrame": ...
    def to_pageobject(self, idgen, page) -> etree._Element: ...

@dataclass
class ImageFrame(_Frame):
    src: str = ""
    image: str = ""
    layer: int = 1                     # default Bilder layer
    local_scale: tuple[float, float] = (1.0, 1.0)
    local_offset_mm: tuple[float, float] = (0.0, 0.0)
    local_rotation_deg: float = 0.0
    scale_type: int = 1                # 0=free/aspect-locked, 1=fit-to-frame
    ratio: int = 1
    pic_art: int = 1
    fill: Optional[str] = None
    line_color: Optional[str] = None
    line_width_pt: float = 0
    inline_image_data: Optional[str] = None
    inline_image_ext: Optional[str] = None  # "png" | "jpg"

    def to_pageobject(self, idgen, page) -> etree._Element: ...

@dataclass
class Polygon(_Frame):
    fill: str = "Black"
    line_color: Optional[str] = None
    line_width_pt: float = 0
    layer: int = 0                     # default Hintergrund
    shape: str = "rectangle"           # 'rectangle' | 'ellipse'
    fill_shade: int = 100
    dash_pattern: Optional[tuple[float, ...]] = None

    def to_pageobject(self, idgen, page) -> etree._Element: ...


# ============================================================================
# EXISTING — Document + Page
# tools/sla_lib/builder/document.py
# ============================================================================
@dataclass
class Page:
    width_pt: float
    height_pt: float
    bleed_mm: float = 3.0
    margins_mm: tuple[float, float, float, float] = (10, 10, 10, 10)
    master_name: str = ""
    label: str = ""
    items: list = field(default_factory=list)
    own_page: int = 0
    page_xpos_pt: float = 0
    page_ypos_pt: float = 0
    is_left: bool = False
    is_master: bool = False
    master_id: str = ""

    def add(self, item) -> "Page":
        """Anything with .emit() is unwrapped immediately into self.items."""

class Document:
    def __init__(self, title: str = "", template_id: str = "", *,
                 brand: Optional[Brand] = None,
                 layers: Optional[list[DocumentLayer]] = None,
                 facing_pages: bool = False, ...) -> None: ...

    def add_color(self, name: str, *, rgb=None, cmyk=None, spot=False, register=False) -> None: ...
    def add_para_style(self, style: ParaStyle) -> None: ...
    def add_char_style(self, style: CharStyle) -> None: ...
    def add_master(self, name: str = "Normal", size = "A4", ...) -> Page: ...
    def add_page(self, size = "A4", ...) -> Page: ...
    def save(self, path) -> None: ...

    # Public state queryable by structural_check:
    pages: list[Page]
    masters: list[Page]
    ci: _CI                            # has .colors, .fonts, .styles, .layers
    _extra_colors: dict[str, BrandColor]
    _extra_para_styles: dict[str, ParaStyle]
    _extra_char_styles: dict[str, CharStyle]


# ============================================================================
# PROPOSED — Composite blocks per D1
# tools/sla_lib/builder/composites.py  (or extend blocks.py)
# ============================================================================
@dataclass
class AlignedRow:
    """All children share a common y_mm. Constraint enforced at emit time."""
    y_mm: float
    children: list                     # any objects with x_mm/y_mm/w_mm/h_mm
    name: Optional[str] = None         # for structural_check report

    def emit(self, page=None) -> Iterable:
        for child in self.children:
            child.y_mm = self.y_mm     # forced — invariant
            yield child

@dataclass
class AlignedColumn:
    """All children share a common x_mm."""
    x_mm: float
    children: list
    name: Optional[str] = None

    def emit(self, page=None) -> Iterable: ...

@dataclass
class MirroredPair:
    """Two children mirrored around a vertical or horizontal axis."""
    left: object                       # primitive with x_mm/y_mm
    right: object
    axis_mm: float                     # mirror axis in mm
    axis: str = "x"                    # "x" = vertical mirror | "y" = horizontal
    name: Optional[str] = None

    def emit(self, page=None) -> Iterable:
        # Force right.x_mm = 2*axis_mm - left.x_mm - left.w_mm  (or analogous for axis="y")
        ...

@dataclass
class EqualGapStack:
    """Children spaced uniformly along axis with constant gap."""
    gap_mm: float
    axis: str                          # "y" | "x"
    children: list
    start_mm: Optional[float] = None   # if None: use first child's coord
    name: Optional[str] = None

    def emit(self, page=None) -> Iterable: ...

@dataclass
class GridCell:
    """One child placed at row/col of a GridSpec."""
    grid: "GridSpec"
    row: int
    col: int
    child: object
    name: Optional[str] = None

    def emit(self, page=None) -> Iterable:
        # Resolve x_mm, y_mm from grid; force on child; yield child.
        ...

@dataclass
class HierarchyBlock:
    """3-element hierarchy (headline > subline > body); enforces fontsize ordering."""
    headline: TextFrame
    subline: TextFrame
    body: TextFrame
    name: Optional[str] = None

    def emit(self, page=None) -> Iterable:
        yield self.headline
        yield self.subline
        yield self.body

@dataclass(frozen=True)
class GridSpec:
    """Helper for GridCell. Defines a regular grid in mm."""
    origin_mm: tuple[float, float]
    cell_w_mm: float
    cell_h_mm: float
    gutter_mm: float
    rows: int
    cols: int


# ============================================================================
# PROPOSED — Free-form Constraints per D2
# tools/sla_lib/builder/constraints.py  (or extend blocks.py)
# ============================================================================
@dataclass(frozen=True)
class Violation:
    constraint_id: str
    target: str                        # e.g. anname or "frame[1]"
    detail: str

class Constraint:
    """Base class for free-form constraints. Subclasses implement check()."""
    id: str
    name: Optional[str] = None
    def check(self, primitives: list) -> list[Violation]: ...

# Factory functions (NOT classes) — return Constraint instances:
def same_y(*frames: _Frame, name: Optional[str] = None,
           tolerance_mm: float = 0.5) -> Constraint:
    """All frames share a common y_mm within tolerance."""
def same_x(*frames: _Frame, name: Optional[str] = None,
           tolerance_mm: float = 0.5) -> Constraint: ...
def same_size(*frames: _Frame, name: Optional[str] = None,
              tolerance_mm: float = 0.5) -> Constraint: ...
def mirrored_x(left: _Frame, right: _Frame, axis_mm: float,
               name: Optional[str] = None,
               tolerance_mm: float = 0.5) -> Constraint: ...
def mirrored_y(top: _Frame, bottom: _Frame, axis_mm: float,
               name: Optional[str] = None) -> Constraint: ...
def inside(inner: _Frame, outer: _Frame,
           name: Optional[str] = None) -> Constraint: ...
def same_style(*frames: TextFrame, name: Optional[str] = None) -> Constraint: ...
def distance_y(a: _Frame, b: _Frame, *,
               equals: float, tolerance_mm: float = 0.5,
               name: Optional[str] = None) -> Constraint: ...
def distance_x(a: _Frame, b: _Frame, *,
               equals: float, tolerance_mm: float = 0.5,
               name: Optional[str] = None) -> Constraint: ...
def equal_gap(*frames: _Frame, axis: str, gap_mm: float,
              tolerance_mm: float = 0.5,
              name: Optional[str] = None) -> Constraint: ...
def hierarchy(headline: TextFrame, subline: TextFrame, body: TextFrame,
              name: Optional[str] = None) -> Constraint:
    """Asserts fontsize(headline) > fontsize(subline) >= fontsize(body)."""


# ============================================================================
# PROPOSED — Brand-Constraints per D3
# tools/sla_lib/builder/brand_constraints.py
# ============================================================================
from typing import Callable

# Each rule is a callable with the signature (primitives, doc) → list[Violation].
# Rules carry an `id` attribute for override resolution.

class BrandRule:
    id: str
    description: str
    def __call__(self, primitives: list, doc: Document) -> list[Violation]: ...

def rule_color_palette_only() -> BrandRule:
    """All colors used must be in load_ci().colors ∪ doc._extra_colors."""

def rule_font_family_only() -> BrandRule:
    """All fonts must be in load_ci().fonts."""

def rule_line_spacing_factor_0_9() -> BrandRule:
    """ParaStyle.linesp ≈ ParaStyle.fontsize × 0.9 (headlines) / × 1.3 (body)."""

def rule_hl_sl_distance_x2() -> BrandRule:
    """Distance from headline-bottom to subline-top ≈ headline_fontsize × 2."""

def rule_logo_size_3M() -> BrandRule:
    """ImageFrame named 'Logo*' has w_mm = 3 × 0.06 × min(page_w_mm, page_h_mm) ± 15%."""

def rule_text_on_green() -> BrandRule:
    """TextFrames using brand styles sit on Dunkelgrün/Hellgrün/Magenta backing."""

def rule_bleed_3mm() -> BrandRule:
    """page.bleed_mm == 3.0 (or 2.0 if template has die-cut)."""

def rule_wahlkreuz_colored_background() -> BrandRule:
    """ImageFrame named 'wahlkreuz*' on Dunkelgrün/Hellgrün/Magenta backing (D12)."""

# Module-level registry consumed by structural_check.py:
BRAND_CONSTRAINTS: list[BrandRule] = [
    rule_color_palette_only(),
    rule_font_family_only(),
    rule_line_spacing_factor_0_9(),
    rule_hl_sl_distance_x2(),
    rule_logo_size_3M(),
    rule_text_on_green(),
    rule_bleed_3mm(),
    rule_wahlkreuz_colored_background(),
]


# ============================================================================
# PROPOSED — structural_check orchestrator per D7
# tools/structural_check.py
# ============================================================================
@dataclass
class CheckIssue:
    severity: str                      # "error" | "info"
    rule_id: str
    target: str
    detail: str

@dataclass
class TemplateReport:
    slug: str
    issues: list[CheckIssue] = field(default_factory=list)

    @property
    def has_error(self) -> bool: ...
    @property
    def summary(self) -> dict[str, int]: ...

def check_template(slug: str, *, brand_overrides: list[str] | None = None
                   ) -> TemplateReport:
    """Import templates/<slug>/build.py, build doc, walk constraints."""

def report_to_markdown(report: TemplateReport) -> str: ...
def report_to_json(report: TemplateReport) -> str: ...

def main(argv=None) -> int:
    """CLI: structural_check.py SLUG | --all | --json | --markdown"""


# ============================================================================
# PROPOSED — build.py callable convention per D2 / Pitfall 1
# templates/<slug>/build.py
# ============================================================================
def build_doc() -> Document:
    """Return the constructed Document WITHOUT saving.
    
    structural_check.py imports this module and calls build_doc() to walk
    primitives. The doc is unsaved — no filesystem side-effect on import.
    """
    doc = Document(...)
    # ... add_para_style, add_master, add_page, page.add(...) ...
    return doc

# Module-level CONSTRAINTS list (per D2):
CONSTRAINTS: list[Constraint] = [
    same_y(...),
    distance_y(...),
    ...
]

def build(out_path: str | Path = HERE / "template.sla") -> Path:
    """Build and save. Used by gallery rendering."""
    doc = build_doc()
    doc.save(out_path)
    return out_path

if __name__ == "__main__":
    build()
```

---

## 13. Confidence assessment

| Area | Confidence | Reason |
|---|---|---|
| DSL surface map | HIGH | All code read line-numbered, tested at boundaries |
| Block-pattern inventory | HIGH | All 12 active blocks read; emit() signatures verified |
| Composite-API form | HIGH | D1 locks container-style; pattern is unambiguous |
| Free-form constraint API | HIGH-MEDIUM | D2 locks variable-reference + module-level CONSTRAINTS list. Open: factory-fn vs class. |
| Brand-rule mapping | HIGH | All 8 rules have concrete predicates over emitted primitives |
| Brand-rule false positives on existing templates | HIGH | QUICKGUIDE-NOTES already documents the drift |
| structural_check orchestration | HIGH | Patterns from check_ci.py + spec_check.py + sla_diff.py; D11 budget headroom large |
| Production-template build_doc() refactor | HIGH | Clear pattern; no SLA byte change needed |
| spec_check.py changes | HIGH | Single-file change; ~20 LoC delta |
| Spec-Writing-Guide structure | MEDIUM | Section structure proposed but actual content depends on Phase 4 author judgment |
| `library.py` references in prompt | LOW | Doesn't exist in this branch — confirm with planner. CONTEXT.md cross-refs may pre-date file presence. |
| `iter_all_primitives` discovery | HIGH | Confirmed not present in document.py; must be added |
| CI performance | HIGH | Existing budget large; structural_check estimated <5s/template easily |
| Backward-compat verification recipe | HIGH | render_pipeline + check_stale_previews mechanics are clear |

---

## 14. Open questions for planner

1. **Path of `brand_constraints.py`:** CONTEXT.md says
   `tools/sla_lib/builder/brand_constraints.py` (rule module). But the
   orchestrator CLI should likely live at `tools/structural_check.py` next to
   the other CLI tools. Plan must lock this.

2. **Composites: extend `blocks.py` or new `composites.py`?**
   `blocks.py` is already 909 LoC. Adding 6 composite dataclasses adds ~150 LoC.
   Splitting to `composites.py` aligns with semantic separation
   (block = single emit, composite = multi-child enforced relations).

3. **Free-form constraints: extend `blocks.py` or new `constraints.py`?**
   Same question. Recommended: `constraints.py` for clean separation.

4. **Constraint-class hierarchy:** dataclass-per-primitive vs shared
   `Constraint(check())` interface. CONTEXT.md "Claude's Discretion".
   Recommendation: factory-fn returning a single `Constraint` dataclass with
   a `check()` method. Pythonic, easy to test.

5. **Brand-rule extensibility (Claude's discretion in CONTEXT.md):** how does
   a new template-author add a brand-rule? Plugin-via-decorator vs a config
   file. Recommended: decorator-based with registration in BRAND_CONSTRAINTS.

6. **Override granularity (Claude's discretion):** per-brand-rule-id vs
   per-slot vs per-page. CONTEXT.md "Override-Mechanismus" sketches per-rule-id
   in `meta.yml.brand_overrides: [rule-id1]`. Plan must lock format.

7. **`Gotham Narrow Book Italic` not in ci.yml fonts:** add it to ci.yml,
   or accept-via-pattern in `rule_font_family_only` (e.g. accept any "<font> Italic"
   if "<font>" is in ci.yml).

8. **`library.py` referenced in prompt:** does NOT exist in this worktree at
   `tools/sla_lib/builder/`. Confirm whether (a) prompt is referring to a
   different branch's code, (b) the file was renamed/refactored, or (c) the
   plan should NOT depend on this file.

9. **Phase-2 vorzeige scope:** "themen-plakat-a3-quer" per D9. Should the
   Phase 2 PR also ship the brand-rule fixes for known drift on this one
   template (as a pilot), or is that deferred to Phase 3?

10. **spec_check tolerance migration:** 0.1mm → 0.5mm change might cause
    "info" entries that overwhelm log readers. Default output filter to
    suppress info, but `--show-info` flag to surface them?

---

## 15. Summary for plan

The codebase is in an unusually good state for this issue. The DSL primitives
are clean, the existing block pattern (`@dataclass` + `emit() -> Iterable`) is
exactly the shape composites need. The 5 new templates have a clean
`build()` entry-point convention; the 3 production templates need a small
refactor to expose `build_doc()`. The validators (check_ci, spec_check,
sla_diff) provide ready-made templates for structural_check.

The main complexity drivers are:
1. The 8 templates' refactor: byte-stable for 3 production, SHA-stable for 5 DSL-only.
2. Brand-rules will surface known-existing drift; needs override convention discipline.
3. structural_check needs build.py modules to be import-side-effect-free (build_doc() pattern).
4. Spec-Writing-Guide must reference real CONSTRAINTS identifiers — depends on Phase 3 completion.

No technical blockers. All 15 acceptance criteria from ISSUE.md decomposable
into ~25 plan tasks across 5 phases.
