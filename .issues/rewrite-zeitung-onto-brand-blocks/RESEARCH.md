# RESEARCH — Rewrite Zeitung A4 onto Brand + blocks

**Researched:** 2026-05-07
**Issue:** rewrite-zeitung-onto-brand-blocks (id 8, depends on merged #5; stacked on merged #7 / Plakat)
**Confidence:** HIGH (every count measured live against a regenerated build.py + a live build of it)

## Summary

The converter alone takes Zeitung from **3244 → 2526 LOC** (-718). All four numeric ACs in ISSUE.md (LOC ≤2400, doc-attrs ≤23, pdf-attrs ≤11, Brand uptake) are MET or close to met by the raw regen with **zero hand edits**: `extra_doc_attrs=23` (=23 met exact), `extra_pdf_attrs=11` (=11 met exact), `brand=Brand.gruene_noe()` emitted, `palette_replaces_ci=True` removed, `clip_edit=True` rect-paths auto-emitted with **0 `custom_path=`** for the 87 rect frames, all **14 chains × 3 frames = 42 chained TextFrames** preserved with **28 `link_to()` calls** (= 14 × 2 per-chain wirings), and the **12 `var='pgno'` PageNumber idioms** survive intact. LOC is at 2526 — **126 over the literal ≤2400 target**, but per ISSUE.md the LOC target is informational only.

Block substitutions identified: **PageNumber × 12** (clean fit, ~10 LOC saved each = ~120 LOC) and **ColumnTextStory × 14** (medium fit, ~5–10 LOC saved each = ~70–140 LOC after link_to-list collapse). PageBackground × 0 — Zeitung has 0 full-bleed Polygons (the 8 polygons in the regen are decorative inline shapes, NOT full-bleed page backgrounds). Impressum × 0 — Zeitung's Impressum has 3 runs (heading + empty + body), structurally different from the modern block's single-Run idiom and from Postkarte/Plakat's 2-run Bold-prefix idiom. ContactBlock × 0.

The only **new** blocker surfaced by Zeitung (not seen in Postkarte or Plakat): Zeitung's original SLA carries a single layer named **`Ebene 1`** ("Layer 1") — distinct from Postkarte/Plakat's `Hintergrund`. `Brand.gruene_noe()` injects the 4 brand layers (`Hintergrund`, `Bilder`, `Text`, `Hilfslinien`); none match `Ebene 1`. The rebuilt SLA produces a `missing-layer` warning (`left='Ebene 1', right='(absent)'`) that the existing `--allow-brand-extras` flag does NOT filter. Without a fix, `bin/validate --ci`'s strict mode fails on Zeitung. This is a 5-LOC extension to `tools/sla_diff.py` similar to the `extra-color` extension Plakat #7 added.

**Primary recommendation:** Six tasks. (1) extend `--allow-brand-extras` to filter `missing-layer` warnings whose left value is the original Zeitung layer name (`Ebene 1`); (2) regenerate `build.py`; (3) substitute `PageNumber × 12`; (4) substitute `ColumnTextStory × 14`; (5) update `ZeitungRoundTrip` test allowlist (currently asserts WARNING==0 — will fail with the brand-additive 13 warnings + 1 `missing-layer Ebene 1`); (6) rebuild gallery + full validation pipeline + EXECUTION.md. Estimated final LOC: ~2300 (after both block substitutions).

## Current Zeitung build.py inventory (3244 LOC committed)

Per-section ranges in **current committed** `templates/zeitung-a4-grun/build.py`:

| Lines | Section | Notes |
|------:|---------|-------|
| 1–13 | Imports + sys.path bootstrap | unchanged across templates |
| 15–33 | `Document(...)` constructor | line 28 = `extra_doc_attrs` (113 keys, ~3300 chars), line 29 = `extra_pdf_attrs` (44 keys, ~1300 chars), line 24 = `palette_replaces_ci=True`, line 30–32 = `layers=[DocumentLayer('Ebene 1', ...)]` |
| 35–42 | `doc.add_color(...)` × 8 | Black, Dunkelgrün, Gelb, Green, Hellgrün, Magenta, Registration, White |
| 44 | `add_char_style(...)` × 1 | Default Character Style |
| 45–67 | `add_para_style(...)` × 23 | Default + 22 template-locals (Titelseite Header, Monat/Ausgabe, Zustellerhinweis, Impressum, Copyright, Seitenzahl, Fließtext, Schrift Störer, etc.) |
| 69–90 | `doc.add_master(...)` × 2 | "Neue Musterseite rechts" (right master) + "Neue Musterseite links" (left master); both EMPTY (no items added at master-level) |
| 92–222 | `doc.add_page(...)` × 14 | page0 (Titelseite, no master = `Neue Musterseite rechts`) … page13 (last article spread); facing_pages=True alternates left/right master |
| 233–3211 | **per-page page items** × 140 | 112 TextFrames, 20 ImageFrames, 8 Polygons; chains use `_chain<N>_<idx>` named-variable pattern |
| 3214–3241 | `_chain<N>_0.link_to(_chain<N>_1)` etc. | 28 link_to calls = 14 chains × 2 wirings (chain length is 3) |
| 3243–3244 | `doc.save(...)` + print | unchanged |

### Frame inventory by page

Live-counted from current `templates/zeitung-a4-grun/build.py`. `B` = block-substitutable; `P` = stays primitive; `C` = chain member (substitutable via `ColumnTextStory`); `N` = page-number (substitutable via `PageNumber`).

| Page | Type | Items | TextFrame | ImageFrame | Polygon | PageNum | Chain frames | Notes |
|----:|---|---:|---:|---:|---:|---:|---:|---|
| 0 (Titelseite) | front | 14 | 11 | 1 | 2 | 0 | 0 | rotated 90° Dunkelgrün decorative box (NOT bleed), Magenta Störer ellipse, headlines |
| 1 | spread | 8 | 6 | 1 | 0 | 1 (N) | 3 (C) | Editorial: chain1 (3 frames) + headline + img + pgno |
| 2 | spread | 11 | 7 | 1 | 0 | 1 (N) | 6 (C) | 2× chain (chain0 + chain2) + headlines + img + pgno |
| 3 | spread | 9 | 5 | 1 | 1 | 1 (N) | 3 (C) | green box polygon + chain3 + img + pgno |
| 4 | spread | 5 | 1 | 1 | 0 | 1 (N) | 3 (C) | chain4 + headline + img + pgno |
| 5 | spread | 6 | 3 | 1 | 0 | 1 (N) | 3 (C) | chain5 + headlines + img + pgno |
| 6 | spread | 9 | 5 | 0 | 1 | 1 (N) | 3 (C) | chain6 + green box + headlines + pgno |
| 7 | spread | 8 | 4 | 1 | 1 | 1 (N) | 3 (C) | chain7 + green box + headlines + img + pgno |
| 8 | spread | 14 | 8 | 3 | 1 | 1 (N) | 3 (C) | chain8 + green box + multiple headlines + 3 imgs |
| 9 | spread | 12 | 6 | 1 | 1 | 1 (N) | 3 (C) | chain9 + green box + headlines + img + pgno |
| 10 | spread | 7 | 3 | 2 | 0 | 0 | 3 (C) | chain10 + 2 imgs + headlines (no pgno on this spread) |
| 11 | spread | 7 | 3 | 2 | 0 | 1 (N) | 3 (C) | chain11 + 2 imgs + pgno |
| 12 | spread | 11 | 7 | 1 | 0 | 1 (N) | 6 (C) | 2× chain (chain12 + chain13) + headlines + pgno |
| 13 (back) | back | 14 | 9 | 3 | 1 | 1 (N) | 0 | back page: Magenta Störer + Impressum + headlines + 3 imgs + pgno |
| **TOTAL** | | **140** | 78 | 20 | 8 | **12** | **42** | of which 14 chains × 3 frames; 6 inline images |

**Block-substitutable count: 26 of 140** (12 PageNumber + 14 ColumnTextStory chains, where each chain collapses 3 frames into one block call).

### Idiom counts (current build.py = `_committed_`; regen = `_regen_`)

| Idiom | _committed_ | _regen_ | Block? |
|---|---:|---:|---|
| TextFrame | 112 (78 inline + 34 chain ref) | 112 | (most stay primitive) |
| ImageFrame | 20 | 20 | P |
| Polygon | 8 | 8 | P (none full-bleed → no PageBackground fit) |
| `var='pgno'` Run | 12 | 12 | **B → PageNumber × 12** |
| `_chain<N>_<idx>` assignment | 42 | 42 | **B → ColumnTextStory × 14** (each chain) |
| `link_to(...)` call | 28 | 28 | preserved (block emits these) |
| `clip_edit=True` | 86 (PageNumber + chain + others) | 87 | converter auto-emits, no manual paths |
| `custom_path='M0 0 L...Z'` rect | 0 | 0 | converter strips (test_5c invariant) |
| `custom_path=` non-rect (bezier) | 0 | 0 | Zeitung has no bezier custom paths |
| `rotation_deg=` | 4 | 4 | P (decorative, no block fit) |
| `trail_style='Impressum'` | 1 | 1 | P (3-run, gap; see below) |
| `palette_replaces_ci=True` | 1 | 0 | converter drops (Brand path) |
| `DocumentLayer(...)` (explicit) | 1 (Ebene 1) | 0 | converter drops (Brand provides) |
| `add_color(...)` lines | 8 | 1 (`Green` only) | 7 brand colors filtered |
| `add_para_style(...)` lines | 23 | 23 | none filtered (all template-local German names) |
| `add_master(...)` items | 0 (masters are empty) | 0 | NO master-page items → Codex master-chain bug N/A |

**Important corrections vs the issue prompt's expected counts:**
- Prompt says "84 `runs=[ ]` frames with `link_to` chains" — actual is **42 chained TextFrames** (14 chains × 3 frames). The "84" likely double-counted the `runs=` item (each chain frame's runs list, plus the chain ref). Actual `link_to()` call count = **28** (14 × 2).
- Prompt says "86 `clip_edit=True` frames" — actual is **87** in regen (close — pages have 86 rect frames; the 87th may include a polygon with clip_edit which doesn't get rect-stripped).
- Prompt says "12 `var='pgno'` PageNumber" — confirmed **12** ✓.
- Prompt says "Possibly multiple `PageBackground` polygons (Titelseite has full-bleed)" — **WRONG.** Zeitung has **0 full-bleed PageBackground candidates**. The 2 page0 polygons are: (a) a 90°-rotated 148×220mm decorative Dunkelgrün box at (216, 156) — NOT a full-bleed of A4(210×297); (b) a Magenta ellipse Störer. The 6 polygons on pages 3–13 are all non-bleed inline-decorative green/magenta boxes.
- Prompt says "Possibly `Impressum` (with same gaps surfaced by Plakat: rotation_deg, bold prefix)" — **partially right.** Zeitung's Impressum is 0° rotation (no rotation_deg gap), but its 3-run structure (heading "Impressum" in `Inhaltsheadline Titelseite` style + empty para spacer + body in `Impressum` trail_style) is NOT supported by the modern `Impressum` block (single-Run only). Different gap from Plakat's 2-run Bold-prefix idiom — and worse: the Zeitung "heading" run uses a different paragraph_style than the body, which the block can't model.
- Prompt says "2 master pages (titelseite, artikel-3col)" — **WRONG.** The 2 masters are named "Neue Musterseite rechts" / "Neue Musterseite links" (right/left master pages of a facing-pages spread). They have NO items — just page geometry (margins, bleed, position). No master-page text chains exist; the Codex master-chain bug from #5 does NOT apply to Zeitung.

## Converter regeneration baseline

**CLI invocation (executor will run):**
```bash
python3 tools/sla_to_dsl.py \
    templates/zeitung-a4-grun/template.sla \
    templates/zeitung-a4-grun/build.py \
    --template-id zeitung-a4-grun \
    --assets-dir templates/zeitung-a4-grun/assets/
```
(Research used `/tmp/zeitung-regenerated.py` and `/tmp/zeitung-research-assets/` to avoid mutating committed artifacts.)

### Measured numbers

| Metric | Current build.py | Regenerated | Target (ISSUE.md) | Status |
|---|---:|---:|---:|---|
| LOC | 3244 | **2526** | ≤2400 (informational per user direction) | -718 LOC; 126 over literal target; LOC gating dropped per #6/#7 precedent |
| `extra_doc_attrs` keys | 113 | **23** | ≤23 | exact match (criterion met) |
| `extra_pdf_attrs` keys | 44 | **11** | ≤11 | exact match (criterion met) |
| `add_color(...)` lines | 8 | 1 (`Green` only) | — | improvement (7 brand colors filtered) |
| `add_para_style(...)` lines | 23 | 23 | — | unchanged (all template-local German names) |
| `add_char_style(...)` lines | 1 | 1 | — | unchanged |
| `add_master(...)` lines | 2 | 2 | — | unchanged (masters preserve geometry) |
| `add_page(...)` lines | 14 | 14 | — | unchanged |
| `DocumentLayer(...)` | 1 (Ebene 1) | 0 | — | converter drops (Brand provides) |
| `palette_replaces_ci=True` | 1 | 0 | — | converter drops (Brand path forces it implicitly) |
| `Brand.gruene_noe()` in `Document(...)` | 0 | **1** | — | criterion met |
| `var='pgno'` Run count | 12 | 12 | — | preserved |
| Chain `_chain<N>_<idx>` assignments | 42 | 42 | — | preserved |
| `link_to(...)` calls | 28 | 28 | — | preserved (== 14 × 2) |
| `clip_edit=True` count | 86 | 87 | — | preserved |
| `custom_path=` count | 0 | 0 | — | converter strips rect paths (test_5c invariant) |

### Why the regen LOC is ~2526 (not lower)

The remaining 2526 LOC is dominated by:
- ~78 inline TextFrames × avg 18 LOC = ~1400 LOC
- ~20 ImageFrames × avg 13 LOC = ~260 LOC (6 with inline_image_data adding ~17 LOC each)
- ~42 chain TextFrames × avg 17 LOC = ~720 LOC (chain pattern: assign + add per frame)
- 8 Polygons × avg 11 LOC = ~90 LOC
- 23 ParaStyles × 1 LOC each = 23 LOC
- 28 `link_to(...)` calls = 28 LOC
- Document constructor + 2 masters + 14 pages = ~140 LOC

### Hand-edit savings

| Lever | LOC saved | New LOC |
|---|---:|---:|
| Regen baseline | -718 | 2526 |
| **Substitute PageNumber × 12** (each frame: ~13 LOC → 1 LOC block call) | -144 | 2382 |
| **Substitute ColumnTextStory × 14** (per chain: 3 frame assigns + 3 page.adds + 2 link_to = ~6 LOC saved per chain after collapse to single block call) | ~-84 | ~2298 |
| **Final estimate** | — | **~2300 LOC** |

The block substitutions get us **comfortably under the ≤2400 LOC target** in ISSUE.md, with ~100 LOC headroom. Per user direction LOC is informational only — but if the planner wants to hit the explicit 2400 number, both block substitutions are needed.

### Residual converter quirks (not blockers)

- The 6 inline-image frames keep `xpos_pt`/`ypos_pt`/`width_pt`/`height_pt` because the converter's "drop pt-geometry" logic at sla_to_dsl.py:66-117 deliberately preserves them for inline-image precision. Acceptable — `test_5b_zeitung_inline_images_keep_xpos_pt` enforces this invariant (live-verified: 6 inline = 6 frame xpos_pt).
- The 87 rect-clip frames (12 pgno + 42 chain + 33 others) all drop `custom_path=` per `test_5c_zeitung_clip_rect_frames_omit_custom_path`. Live-verified: 0 `custom_path=` in regen.
- Master pages are emitted as empty (no items) — converter correctly handles the "geometry-only master" pattern.
- `link_to()` calls emit at the END of the file (after all `pageX.add(_chainN_M)` calls), grouped together. The block-substitution will replace this entire trailing block.

## Block-substitution plan

For each of the 5 evidence-driven blocks landed in #5:

### PageNumber — 12 substitutions (clean fit)

**Where in regen:** lines 446–459, 599–612, 691–704, 862–875, 964–977, 1236–1249, 1379–1392, 1513–1526, 1680–1693, 1970–1983, 2157–2170, 2302–2315 (12 occurrences distributed across pages 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13).

**Current pattern (~13 LOC each):**
```python
page1.add(TextFrame(
    x_mm=8.51073047881968,
    y_mm=283.69722222116576,
    w_mm=12.775464220466706,
    h_mm=9.480247708017236,
    layer=0,
    anname='Kopie von u2d45',
    clip_edit=True,
    line_width_pt=1,
    col_gap_mm=3.207461712525627,
    runs=[
        Run(text='', has_itext=False, var='pgno', separator='para', paragraph_style='Seitenzahl'),
    ],
))
```

**Proposed substitution (1 LOC each via block):**
```python
page1.add(PageNumber(x_mm=8.51, y_mm=283.70, w_mm=12.78, h_mm=9.48, anname='Kopie von u2d45', layer=0))
```

The `PageNumber` block at `tools/sla_lib/builder/blocks.py:46–81` accepts: `x_mm`, `y_mm`, `w_mm`, `h_mm`, `style` (default `'Seitenzahl'` ✓), `layer` (default 2 — Zeitung uses layer 0 — pass explicit), `anname` (default `'Seitenzahl'` — Zeitung uses `'Kopie von u2d45'` etc. — pass explicit). All Zeitung pgno frames use `paragraph_style='Seitenzahl'` so the default style works. **No block widening needed.**

Caveat 1: page12's pgno frame (line 2157) has `var_attrs={'FCOLOR': 'White', 'FSHADE': '100'}` (white pgno on dark background). The PageNumber block doesn't expose `var_attrs=`. **Two options:** (a) keep that ONE frame as primitive (acceptable; saves 11 of 12 substitutions); (b) widen `PageNumber` with `var_attrs=` passthrough (~2-line edit at blocks.py:72-78 — trivial kwarg passthrough, in scope per ISSUE.md constraint). **Recommendation: option (b).** Trivial widening, keeps all 12 substitutions clean.

Caveat 2: Zeitung pgno frames carry `clip_edit=True`, `line_width_pt=1`, `col_gap_mm=3.207461712525627`. PageNumber's emit() at `blocks.py:67-81` does NOT set these. Confirmed by reading: a substituted block call would emit a frame WITHOUT `clip_edit=True`, and the rebuilt SLA would lose `CLIPEDIT="1"` on those PAGEOBJECTs — generating 12 `attr-differs CLIPEDIT` warnings. **Two options:** (a) pass these as kwargs that the block widens to forward (4-line edit per kwarg); (b) accept attr-differ warnings IF they're below severity-warning. Inspection of `tools/sla_diff.py` shows `CLIPEDIT` and `col_gap_mm` differences are warning-severity. **Recommendation: widen `PageNumber` to forward `clip_edit`, `line_width_pt`, `col_gap_mm` (3 trivial kwarg passthroughs at blocks.py:67-81 — adds ~6 lines to blocks.py).**

LOC saved: ~12 × 12 = **~144 LOC**.

### ColumnTextStory — 14 substitutions (medium fit, saves ~6 LOC each)

**Where in regen:** 14 chains, each consisting of 3 `_chain<N>_<idx> = TextFrame(...)` assignments, 3 `pageX.add(_chain<N>_<idx>)` calls, and 2 `_chain<N>_M.link_to(_chain<N>_M+1)` wirings collected at lines ~3214-3241.

**Current pattern (per chain, ~60 LOC):**
```python
_chain1_0 = TextFrame(x_mm=20.00, y_mm=130.75, w_mm=54.67, h_mm=146.25, ..., clip_edit=True, custom_path='...', col_gap_mm=4.23, runs=[Run(...), Run(...), ..., Run(...)])  # ~25 LOC for first frame with story runs
page1.add(_chain1_0)

_chain1_1 = TextFrame(x_mm=77.67, y_mm=130.75, ..., col_gap_mm=4.23)  # ~16 LOC, no runs
page1.add(_chain1_1)

_chain1_2 = TextFrame(x_mm=135.34, y_mm=130.75, ..., col_gap_mm=4.23)  # ~16 LOC, no runs
page1.add(_chain1_2)

# Later, in the link_to block:
_chain1_0.link_to(_chain1_1)
_chain1_1.link_to(_chain1_2)
```

**Proposed substitution (per chain, ~30 LOC):**
```python
page1.add(ColumnTextStory(
    frames=[
        TextFrame(x_mm=20.00, y_mm=130.75, w_mm=54.67, h_mm=146.25, layer=0, clip_edit=True, col_gap_mm=4.23, anname='Kopie von u2f23'),
        TextFrame(x_mm=77.67, y_mm=130.75, w_mm=54.67, h_mm=146.25, layer=0, clip_edit=True, col_gap_mm=4.23, anname='Kopie von u2f23 (2)'),
        TextFrame(x_mm=135.34, y_mm=130.75, w_mm=54.67, h_mm=146.25, layer=0, clip_edit=True, col_gap_mm=4.23, anname='Kopie von u2f23 (3)'),
    ],
    runs=[
        Run(text='Perem la posseditatur ...', fontsize=12, separator='para', paragraph_style='Einleitungstext'),
        # ... rest of story runs (typically 8-12 runs per chain)
    ],
))
# (no separate link_to calls — the block emits them internally)
```

**The block (`tools/sla_lib/builder/blocks.py:298–334`) does:**
- Accepts `frames: Sequence[TextFrame]` and `runs: Sequence[Run]`
- Attaches runs to the first frame (`first.runs = list(self.runs)`)
- Calls `frames[i].link_to(frames[i+1])` for i in range(len(frames)-1)
- Yields all frames in order

**Substitution shape per chain:** ~25 LOC (3 frame definitions in a list + runs list + outer ColumnTextStory call), down from the current ~60 LOC (3 separate frame assigns + 3 page.adds + 2 link_to calls = ~36 LOC just for the chain wiring; ~24 LOC of unique runs). Net savings: ~6 LOC per chain after accounting for slight overhead of the wrapping block call.

Caveat: chains 0, 2, 12, 13 are co-located (chain0 lives on page2 alongside chain2; chain13 lives on page12 alongside chain12). The substitution is per-chain, so this isn't a problem — each chain gets its own `ColumnTextStory(...)` call on the appropriate page.

Caveat 2: chain frames carry `clip_edit=True`, `line_width_pt=1.011...` (only on chain0_0), `col_gap_mm`, `trail_style='Fließtext '` (chain0_0 only), `anname='u2d5c'` etc. All preserved by passing `frames=[TextFrame(... full kwargs)]` directly into the block. The block doesn't strip kwargs; it just wires up `link_to()`. **No block widening needed.**

Caveat 3: the link_to block at lines 3214-3241 of the regen will be entirely deleted (the block emits link_to internally). 28 LOC saved here.

LOC saved: ~6 × 14 = **~84 LOC** (after accounting for block call overhead). Plus 28 LOC saved by deleting the trailing link_to block, minus the 28 LOC absorbed into block emits = net save is ~84 LOC.

### PageBackground — 0 substitutions (no candidates)

**Why no substitution:** Live-verified — Zeitung has **0 full-bleed Polygons** that match the PageBackground pattern. The 8 Polygons in regen are all decorative inline shapes:
- page0[233-243]: 90°-rotated 148×220mm Dunkelgrün decorative box at (216, 156) — NOT a full-bleed of A4(210×297, bleed 3); a full-bleed would be (-3,-3) size 216×303.
- page0[282-293]: 36×35mm Magenta ellipse Störer at (165, 187).
- page3[821-831]: 112×102mm Dunkelgrün decorative box at (78, 175).
- page6[1106-1116]: 113×124mm Dunkelgrün decorative box at (78, 37).
- page7[1328-1338]: 170×82mm Dunkelgrün decorative box at (20, 195).
- page8[1419-1429]: 55×50mm Dunkelgrün decorative box at (135, 37).
- page9[1770-1780]: 112×102mm Dunkelgrün decorative box at (20, 175).
- page13[2434-2444]: Magenta ellipse Störer at (167, 131).

None are full-bleed. The block API expects `x_mm=-bleed, y_mm=-bleed, w_mm=page_w + 2*bleed, h_mm=page_h + 2*bleed`. None of the 8 polygons match this geometry. **Stays primitive × 8.** The blocks.py:131 corpus comment ("Titelseite Dunkelgrün background") was misleading — it referred to the rotated 90° decorative box on the Titelseite, which is NOT a full-bleed page background.

### Impressum — 0 substitutions (3-run heading idiom gap, NOT same as Plakat/Postkarte)

**Where in regen:** lines 2479–2497 (page13, the back page Impressum frame).

**Why no substitution:** the regen frame has THREE runs:
```python
runs=[
    Run(text='Impressum', separator='para', paragraph_style='Inhaltsheadline Titelseite'),
    Run(text='', has_itext=False, separator='para', paragraph_style='Inhaltsheadline Titelseite'),
    Run(text='Medieninhaber u. Herausgeber: Die Grünen Niederösterreich, Daniel Gran Straße 48, 3100 St. Pölten • Redaktion: Ortsgruppe + Anschrift • ...'),
],
trail_style='Impressum',
```

The modern `Impressum` block at `tools/sla_lib/builder/blocks.py:89–124` emits a single Run from `text=` argument; cannot carry the heading + empty-spacer + body 3-run structure. AND the heading run uses paragraph_style `Inhaltsheadline Titelseite` (different from trail_style `Impressum`), which the block can't model.

This is a **third Impressum gap** (in addition to Postkarte's bold-prefix gap and Plakat's rotation_deg gap). **Stays primitive.** Plan a P2 follow-up: widen `Impressum` to accept `runs=` override OR a `heading_text=` + `heading_style=` + `body_text=` 3-run schema. Out of this issue's scope.

### ContactBlock — 0 substitutions (no candidates)

Zeitung has no contact-info frame. Block doesn't apply.

### Net block savings summary

| Block | Substitutions | LOC saved |
|---|---:|---:|
| PageNumber | 12 | ~144 |
| ColumnTextStory | 14 | ~84 |
| PageBackground | 0 | 0 |
| Impressum | 0 | 0 |
| ContactBlock | 0 | 0 |
| **Total block savings** | **26** | **~228** |

Combined with -718 from regen: **3244 → 2526 → ~2300 LOC** final. Comfortably under the informational ≤2400 target.

## DSL gaps surfaced (P2 follow-ups, NOT in this issue)

Document these in EXECUTION.md so future researchers pick them up:

1. **`Impressum` block missing 3-run heading + body schema.** Zeitung's Impressum frame has 3 runs: heading "Impressum" in `Inhaltsheadline Titelseite` style + empty para spacer + body run with default trail_style. The modern block (single Run from `text=`) can't model this. Combined with Postkarte's bold-prefix gap (P2 #1 from #6) and Plakat's rotation_deg gap (P2 #1 from #7), this is the THIRD Impressum gap surfaced. Combined widening proposal: add `runs=Sequence[Run]` override that bypasses the default-text emit, or `heading_text=`, `heading_style=`, `body_runs=` 3-run schema, plus the previously-filed `prefix_text=`/`prefix_font=`/`rotation_deg=`. **Out of scope for issue 8.**

2. **`PageNumber` block could widen with `var_attrs=`, `clip_edit=`, `line_width_pt=`, `col_gap_mm=` kwarg passthroughs.** ISSUE.md says "Do NOT widen block APIs beyond trivial kwarg passthrough" — these ARE trivial passthroughs (each is a single dataclass field + 1 line in `emit()` to forward to the inner TextFrame). Without these, 12 PageNumber substitutions either lose attr fidelity (warning bloat) or stay primitive (saves only ~0 LOC). **Recommendation: include this trivial widening in scope for issue 8** (4 fields × ~2 LOC each = ~8 LOC added to blocks.py; preserves attr fidelity for all 12 substitutions). Justified by "trivial kwarg passthrough" carve-out in ISSUE.md.

3. **`tools/sla_diff.py --allow-brand-extras` does not cover `missing-layer` warnings.** Zeitung's original SLA carries a single layer named `Ebene 1` (German default for "Layer 1"); Brand replaces this with the 4-layer brand stack (Hintergrund/Bilder/Text/Hilfslinien), causing a `missing-layer Ebene 1` warning that the existing `--allow-brand-extras` flag does NOT filter. **Hard blocker for this issue** — see "Recommendations to the planner" task 1 below.

## Converter regressions surfaced

**None.** The converter handles all of Zeitung's complexity correctly:

- ✅ Multi-master pages emit (2 masters, both empty — geometry only); pages reference them via `master='Neue Musterseite rechts'`/`'Neue Musterseite links'` correctly.
- ✅ Master-page text chains: N/A (Zeitung has no items at master-page level — just at page level).
- ✅ Linked-story chains preserved: 14 chains × 3 frames + 28 link_to calls; round-trips byte-clean (test_chain_topology_intact passes).
- ✅ `clip_edit=True` rect-paths auto-emit: 87 frames, 0 `custom_path=` (test_5c invariant holds).
- ✅ Inline images preserve pt-geometry: 6 inline = 6 xpos_pt (test_5b invariant holds).
- ✅ Brand emission: `brand=Brand.gruene_noe()` in Document constructor; no `palette_replaces_ci=True`; no explicit `DocumentLayer` list.
- ✅ Attr hoisting: `extra_doc_attrs` 113→23, `extra_pdf_attrs` 44→11 (exact ACs).
- ✅ Facing-pages flag preserved: `facing_pages=True`.

The Codex master-page text-chain bug from #5's REVIEW.md does NOT manifest on Zeitung because Zeitung's masters are empty. **No converter fixes needed in scope for issue 8.**

## Visual-diff verification flow

The full executor flow (must run in this exact order):

```bash
# 1. Regenerate build.py from current template.sla
python3 tools/sla_to_dsl.py \
    templates/zeitung-a4-grun/template.sla \
    templates/zeitung-a4-grun/build.py \
    --template-id zeitung-a4-grun \
    --assets-dir templates/zeitung-a4-grun/assets/

# 2. Verify counts before hand-edits
python3 -c "
import re, ast
src = open('templates/zeitung-a4-grun/build.py').read()
for k in ('extra_doc_attrs','extra_pdf_attrs'):
    m = re.search(k+r'=\\s*(\\{[^}]*\\})', src, re.S)
    print(k, len(ast.literal_eval(m.group(1))))
print('LOC:', len(src.splitlines()))
print('Brand:', 'Brand.gruene_noe()' in src)
print('palette_replaces_ci:', 'palette_replaces_ci' in src)
"

# 3. Hand-edit: substitute PageNumber × 12 (+ widen blocks.py if needed)
# 4. Hand-edit: substitute ColumnTextStory × 14 (delete trailing link_to block)

# 5. Rebuild template.sla from the new build.py
cd templates/zeitung-a4-grun && python3 build.py && cd -

# 6. Visual byte-clean check (correctness gate)
python3 tools/visual_diff.py \
    templates/zeitung-a4-grun/template.sla \
    --baseline templates/zeitung-a4-grun/baseline.pdf \
    --tolerance templates/zeitung-a4-grun/diff.yml \
    --dpi 96 \
    --out build/validation/zeitung-a4-grun/
# Expected: exit 0; ~0% pixel mismatch (live-verified on raw regen WITHOUT block subs)

# 7. Structural diff (THIS is what fails until task 1 fix):
python3 tools/sla_diff.py \
    --left gruene-zeitung-vorlage-original.sla \
    --right templates/zeitung-a4-grun/template.sla \
    --strict --allow-brand-extras
# Without task 1 fix: critical=0, warning=1 (missing-layer Ebene 1) → exit 1
# With task 1 fix: critical=0, warning=0 → exit 0

# 8. CI compliance check (already passing — local-style warnings, non-blocking)
python3 tools/check_ci.py templates/zeitung-a4-grun/template.sla

# 9. Regenerate gallery previews + previews_for_sla SHA + 14 page PNGs
bin/render-gallery
git add templates/zeitung-a4-grun/{template.sla,build.py,page-*.png,preview.pdf,meta.yml}

# 10. Full validation (the criterion gate)
bin/validate --ci
```

**Diff thresholds (`templates/zeitung-a4-grun/diff.yml`):**
- `max_pixel_mismatch_pct: 1.0`
- `fuzz_pct: 5.0` (project-wide cap)
- No per-page or per-region overrides — all 14 pages must come in under 1% mismatch (live-verified: ~0% mismatch on raw regen).

**Pre-validation result (live-tested):** `visual_diff` exit 0 against baseline.pdf at 96 dpi when run on raw-regen-rebuilt SLA (before any block substitutions). Visual fidelity is intact through the converter's structural improvements alone.

**Render-time considerations:** 14-page A4 at 96 dpi is ~7-10× slower than Postkarte (2 pages A6) and Plakat (1 page A1). Visual_diff at 96 dpi takes ~30-60 seconds for Zeitung locally; bin/validate --ci end-to-end is ~2-3 min. Plan tasks should not block on faster turnaround; CI tolerates this.

## Risks specific to Zeitung

| # | Risk | Severity | Evidence | Mitigation |
|---|---|---|---|---|
| R1 | **`bin/validate --ci` will fail on Zeitung** because `--allow-brand-extras` filters `extra-style`/`extra-layer`/`extra-color` only, NOT `missing-layer`. Zeitung's rebuilt SLA produces 1 unfiltered `missing-layer Ebene 1` warning. | **HIGH** (acceptance criterion blocker) | Live-tested: `python3 tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right /tmp/zeitung-build/template.sla --strict --allow-brand-extras` returns exit=1 with `**critical: 0**, warning: 1`: `missing-layer LAYERS .NAME: left='Ebene 1' right='(absent)'`. | **Plan task 1: extend `--allow-brand-extras` to filter `missing-layer` warnings.** Two viable shapes: (a) hardcode `_LEGACY_LAYER_NAMES = ("Ebene 1",)` near `_BRAND_COLOR_NAMES` and filter `missing-layer` if `i.left in _LEGACY_LAYER_NAMES`; (b) more conservative — filter `missing-layer` only when the right SLA has the brand's 4 layers (Hintergrund/Bilder/Text/Hilfslinien) AND the left is a single non-brand layer. Recommendation: **(a)**, hardcode and document. Trivial 4-line edit at `tools/sla_diff.py:1202-1211`. Mirror Plakat's `extra-color` extension pattern. |
| R2 | LOC at 2526 raw regen is **126 LOC over the literal ≤2400 target**. After block subs, ~2300 (under target by ~100). | LOW (per user direction LOC is informational only; block subs hit the target anyway) | Measured: regen=2526; estimate after PageNumber × 12 + ColumnTextStory × 14 = ~2300. | If block subs not applied: document 2526 in EXECUTION.md as informational. If block subs applied: ~2300 hits the explicit target. Either way, ISSUE.md's "verify and document the actual number" wording covers either outcome. |
| R3 | **`ZeitungRoundTrip.test_diff_against_original_clean`** at `tools/sla_lib/tests/test_sla_to_dsl.py:170-176` will fail after rewrite. | **HIGH** (test gate blocker) | Live-tested: test currently passes against committed build.py (with `palette_replaces_ci=True`). After rewrite, `_diff_clean()` reports `summary[WARNING]={extra-style: 8 ci/* + extra-layer: 4 + missing-layer: 1 (Ebene 1)} = 13` unfiltered warnings, all of which are brand-additive or brand-replacement. Test asserts `WARNING == 0` (line 175) — fails with 13 unfiltered warnings. | **Plan task: extend ZeitungRoundTrip allowlist to filter brand-additive AND brand-replacement warnings.** Mirror Plakat's pattern at `tools/sla_lib/tests/test_sla_to_dsl.py:136-148` and add the `missing-layer` filter for `Ebene 1`. The test already follows the Plakat pattern shape; just extend the predicate to also tolerate `i.code == 'missing-layer' and i.left == 'Ebene 1'`. ~5 LOC edit. |
| R4 | **`ZeitungRoundTrip.test_chain_topology_intact`** at `tools/sla_lib/tests/test_sla_to_dsl.py:178-184` may need updating after ColumnTextStory substitution. | LOW | Live-tested: passes today. After ColumnTextStory substitution, the chains are emitted by the block's `emit()` which calls `frames[i].link_to(frames[i+1])` — same XML output. Round-trip should still produce 14 chains × 3 frames byte-identical. | None expected. Verify by running the test after substitution. |
| R5 | Stale-preview gate (`bin/check-stale-previews`) will fail after rebuild because `meta.yml::previews_for_sla` SHA256 will no longer match. | MEDIUM (preflight blocker) | Measured: current SHA `23ea1bed2afd5b4beb05ca33aefa020fba33f735dd5f95d819eac4dae4ef646d`; rebuilt SLA SHA `f8d1744d980925e9034469d59ec4e9f1a7ed4c5e788d451e071356f9f364e8a4`. Live-tested: `bin/validate --ci` halts at preflight with "stale: zeitung-a4-grun; template.sla hash mismatch" before sla_diff runs. | **Plan task (mandatory): run `bin/render-gallery` after rebuild and commit the new `previews_for_sla` SHA + page-01.png … page-14.png + preview.pdf**. Same task as Postkarte's task 6 / Plakat's task 4. Rendering 14 pages takes longer (~1 min vs Postkarte's ~10s). |
| R6 | The `templates/zeitung-a4-grun/baseline.pdf` (1.35 MB, 14 pages) is the canonical pixel oracle. If the regenerated SLA renders even a 1-pixel different glyph, visual_diff at 1% threshold absorbs it; if > 1% on any page, baseline is stale and rebaselining required. Live-tested visual_diff exit 0 on raw regen. | LOW | `bin/validate --ci` exit 0 on current main; visual_diff exit 0 on regen-without-edits build (live). | Watch the visual_diff per-page mismatch numbers; if they jump after block substitution, suspect a block-emit difference (e.g. PageNumber block missing `clip_edit=True` → CLIPEDIT="0" in rebuilt SLA → could affect frame rendering at edges). |
| R7 | **PageNumber substitution may cause `attr-differs` warnings on `CLIPEDIT`, `col_gap_mm`, `line_width_pt`** unless block widening (P2 #2 above) is applied. | MEDIUM | Inspection: PageNumber block emits TextFrame without `clip_edit=`/`col_gap_mm=`/`line_width_pt=`; original frames carry `clip_edit=True, line_width_pt=1, col_gap_mm=3.207...`. Rebuilt SLA would have CLIPEDIT="0", differing line_width, missing col_gap. | **Plan task: widen `PageNumber` with `clip_edit`, `line_width_pt`, `col_gap_mm`, `var_attrs` kwarg passthroughs (~8 LOC edit at blocks.py:46-81).** This is the "trivial kwarg passthrough" carved out in ISSUE.md. Without this, either accept warning bloat (defeats the point) or keep PageNumber as primitive (negates 144 LOC savings). |
| R8 | **ColumnTextStory substitution preserves `clip_edit`/`col_gap_mm` because frames are passed in directly** — the block doesn't strip kwargs. | LOW | Inspection: `tools/sla_lib/builder/blocks.py:298-334` accepts `frames: Sequence[TextFrame]` and emits them verbatim, only attaching runs to first and adding `link_to()` between consecutive frames. | None — chain-frame substitution is clean. |
| R9 | Render time: 14 A4 pages at 150 dpi is ~10× longer than Plakat's 1 A1 page. `bin/render-gallery` for Zeitung takes ~1-2 min; `bin/validate` (incl visual_diff) at 96 dpi takes ~2-3 min end-to-end. | LOW | Estimated from page count and rendering arithmetic. | None — CI tolerates this. Plan tasks should not gate on faster turnaround. |
| R10 | Inline image data round-trip for the 6 inline images. | LOW | sla_to_dsl.py:11-20 deliberately keeps inline images verbatim base64 to avoid PNG-encode drift. The 6 images in Zeitung are preserved as the converter copies the base64 string literally. | None needed — issue #5 + #6 + #7 already proved this is byte-clean. |
| R11 | `ZeitungConverterFreshRun` test class does NOT exist. Plakat #7 EXECUTION P3 noted Plakat has the same gap. | LOW | grep confirms only Postkarte has a `PostkarteConverterFreshRun` class. Zeitung is covered only by `ZeitungRoundTrip` + the `test_5*_zeitung_*` invariant tests. | Optional: P3 hygiene — add `ZeitungConverterFreshRun` to mirror Postkarte. Not required for this issue. |

## Test infrastructure

### Existing tests (will pass / fail post-migration)

| Test class / function | Location | Currently | Post-migration |
|---|---|---|---|
| `ZeitungRoundTrip.test_diff_against_original_clean` | tests/test_sla_to_dsl.py:170-176 | PASS (asserts WARNING==0) | **FAIL** until allowlist extended (R3) |
| `ZeitungRoundTrip.test_chain_topology_intact` | tests/test_sla_to_dsl.py:178-184 | PASS | PASS (chains preserved) |
| `test_5a_brand_emitted_in_zeitung` | tests/test_sla_to_dsl.py:542-545 | PASS | PASS (regen still emits brand) |
| `test_5b_zeitung_inline_images_keep_xpos_pt` | tests/test_sla_to_dsl.py:595-603 | PASS | PASS (6=6) |
| `test_5c_zeitung_clip_rect_frames_omit_custom_path` | tests/test_sla_to_dsl.py:607-617 | PASS | PASS (0 custom_path in regen) |
| `PostkarteRoundTrip` (all) | tests/test_sla_to_dsl.py:51-117 | PASS | PASS (no regression — Postkarte unchanged) |
| `PlakatRoundTrip` (all) | tests/test_sla_to_dsl.py:119-160 | PASS | PASS (no regression — Plakat unchanged) |
| All other tests | various | PASS (251 total) | PASS |

### Allowlist extension required (Task 5)

Update `ZeitungRoundTrip.test_diff_against_original_clean` to filter brand-additive AND brand-replacement warnings, mirroring Plakat's pattern at lines 136-148:

```python
_BRAND_COLOR_NAMES = ("Black", "White", "Registration",
                      "Dunkelgrün", "Hellgrün", "Gelb", "Magenta")
_LEGACY_LAYER_NAMES = ("Ebene 1",)  # original Zeitung layer replaced by brand stack
non_brand_warnings = [
    i for i in report.issues
    if i.severity == sla_diff.SEVERITY_WARNING
    and not (
        i.code in ("extra-style", "extra-layer")
        or (i.code == "extra-color" and i.right in _BRAND_COLOR_NAMES)
        or (i.code == "missing-layer" and i.left in _LEGACY_LAYER_NAMES)
    )
]
self.assertEqual(non_brand_warnings, [], ...)
```

Same filter shape mirrors `tools/sla_diff.py --allow-brand-extras` task 1 extension.

## Recommendations to the planner

This is the **largest** of the three migrations by LOC delta but the **second-cleanest** by hand-edit complexity (Plakat needed zero hand-edits; Zeitung needs ~26 substitutions, all mechanical). **6 tasks** (1 NEW from Zeitung-specific finding):

1. **(NEW — MUST-FIX-FIRST) Extend `--allow-brand-extras` to filter `missing-layer Ebene 1` warning.** Without this, `bin/validate --ci` strict mode fails on Zeitung. Edit `tools/sla_diff.py:1202-1211` filter predicate. Hardcode `_LEGACY_LAYER_NAMES = ("Ebene 1",)` near `_BRAND_COLOR_NAMES` (line 49). Extend filter to: `or (i.code == "missing-layer" and i.left in _LEGACY_LAYER_NAMES)`. Update `--allow-brand-extras` help text. Add 1-2 unit tests in `test_sla_diff.py` mirroring the existing extra-style/extra-layer/extra-color tests. **Acceptance: existing 3 templates' `bin/validate --ci` output unchanged (Postkarte/Plakat have `Hintergrund` original layer, no `missing-layer` warning produced); Zeitung-with-Brand validates green.**

2. **Widen `PageNumber` block with kwarg passthroughs.** Add `clip_edit: bool = False`, `line_width_pt: Optional[float] = None`, `col_gap_mm: Optional[float] = None`, `var_attrs: Optional[dict] = None` to the dataclass (4 new fields), and forward them in `emit()` to the inner TextFrame Run. ~8 LOC edit at `tools/sla_lib/builder/blocks.py:46-81`. ISSUE.md's "Do NOT widen block APIs beyond trivial kwarg passthrough" carve-out covers this — these are pure kwarg passthroughs. **Acceptance: `pytest tools/sla_lib/tests/test_blocks.py -x` passes; PageNumber substitutions can preserve attribute fidelity in task 4.**

3. **Regenerate `templates/zeitung-a4-grun/build.py` via converter.** Run `python3 tools/sla_to_dsl.py templates/zeitung-a4-grun/template.sla templates/zeitung-a4-grun/build.py --template-id zeitung-a4-grun --assets-dir templates/zeitung-a4-grun/assets/`. Verify: file is 2526 LOC (±5), parses as Python, contains `brand=Brand.gruene_noe()`, no `palette_replaces_ci=True`, `extra_doc_attrs` has 23 keys, `extra_pdf_attrs` has 11 keys, 12 `var='pgno'`, 42 `_chain<N>_<idx>` assignments, 28 `link_to()`, 0 `custom_path=`. **Acceptance: `python3 -c "import ast; ast.parse(open('templates/zeitung-a4-grun/build.py').read())"` exits 0; rebuilt template.sla is valid XML; visual_diff against baseline.pdf exits 0 (live-verified).**

4. **Substitute `PageNumber × 12`.** Replace each of the 12 `pageX.add(TextFrame(... var='pgno' ...))` blocks with `pageX.add(PageNumber(x_mm=..., y_mm=..., w_mm=..., h_mm=..., layer=0, anname='...', clip_edit=True, line_width_pt=1, col_gap_mm=3.207..., var_attrs={'FCOLOR': 'White', 'FSHADE': '100'} if applicable))`. Live coordinates per the inventory section above. **Acceptance: `python3 build.py` succeeds; `tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right templates/zeitung-a4-grun/template.sla --strict --allow-brand-extras` reports critical=0; rebuilt SLA's 12 pgno PAGEOBJECTs preserve CLIPEDIT, col_gap, line_width attributes.**

5. **Substitute `ColumnTextStory × 14`.** For each of the 14 chains: collapse the `_chainN_0 = TextFrame(...)`, `pageX.add(_chainN_0)`, `_chainN_1 = TextFrame(...)`, `pageX.add(_chainN_1)`, `_chainN_2 = TextFrame(...)`, `pageX.add(_chainN_2)` (~60 LOC) into a single `pageX.add(ColumnTextStory(frames=[TextFrame(...), TextFrame(...), TextFrame(...)], runs=[...]))` (~25-30 LOC). Delete the trailing block of 28 `link_to()` calls (lines ~3214-3241 of regen) — the block emits these internally. **Acceptance: `pytest tools/sla_lib/tests/test_sla_to_dsl.py::ZeitungRoundTrip -x` passes (chain topology intact); visual_diff exit 0; LOC ~2300.**

6. **Update `ZeitungRoundTrip` allowlist + rebuild gallery + run full validation.** (a) Edit `tools/sla_lib/tests/test_sla_to_dsl.py:170-176` to filter brand-additive AND brand-replacement warnings (`extra-style`, `extra-layer`, `extra-color` for brand colors, `missing-layer` for `Ebene 1`). Mirror Plakat's pattern at lines 136-148; add `_LEGACY_LAYER_NAMES = ("Ebene 1",)` constant. (b) `bin/render-gallery && bin/validate --ci && python3 tools/check_ci.py templates/zeitung-a4-grun/template.sla && python3 -m pytest tools/sla_lib/tests -x`. The `bin/render-gallery` regenerates `meta.yml::previews_for_sla` SHA + 14 page PNGs + preview.pdf. `bin/validate --ci` must be green for all three templates (postkarte/plakat/zeitung). (c) Write EXECUTION.md with achieved LOC, attr counts, all 6 ACs result, P2 follow-ups list. **Acceptance: `bin/validate --ci` exits 0; `pytest tools/sla_lib/tests -x` exits 0 (251+ tests).**

### Order of operations + LOC arithmetic

| Step | Net LOC change | Cumulative LOC |
|---|---:|---:|
| Start (current committed) | — | 3244 |
| Task 3: Regenerate via converter | -718 | 2526 |
| Task 4: PageNumber × 12 substitution | ~-144 | ~2382 |
| Task 5: ColumnTextStory × 14 substitution + delete trailing link_to block | ~-84 | **~2298** |
| **Final estimate** | — | **~2300** |

**Planner: target ~2300 LOC; ISSUE.md ≤2400 is hit comfortably with both block substitutions.** Per user direction LOC is informational only; record actual achieved LOC in EXECUTION.md.

### Style of rewrite

**"Regenerate then mechanical block-substitution"** — biggest payoff of the three migrations. 26 block substitutions (12 PageNumber + 14 ColumnTextStory) save ~228 LOC on top of the converter's -718 LOC delta. Hand-editing is mechanical: each PageNumber sub is a textual replace; each ColumnTextStory sub is a collapse-3-frame-defs-into-1-list operation. No DSL-level invention. The trailing `link_to()` block deletion is a bulk delete.

The only code changes outside `templates/zeitung-a4-grun/build.py`:
1. `tools/sla_diff.py` — extend allowlist for `missing-layer Ebene 1` (~5 LOC + tests)
2. `tools/sla_lib/builder/blocks.py` — widen PageNumber with 4 kwarg passthroughs (~8 LOC)
3. `tools/sla_lib/tests/test_sla_to_dsl.py::ZeitungRoundTrip` — update allowlist (~5 LOC)

This is a **6-commit migration** at the code level: (1) sla_diff allowlist extension + tests, (2) PageNumber block widening, (3) regenerate build.py + rebuild SLA, (4) PageNumber substitutions, (5) ColumnTextStory substitutions, (6) test allowlist update + render-gallery + EXECUTION.md.

### Comparison to Postkarte (#6) and Plakat (#7)

| Migration | Current LOC | Regen LOC | Block subs | Hand edits | Net final | New blockers introduced |
|---|---:|---:|---:|---:|---:|---|
| Postkarte (#6) | 437 | 383 | 2× PageBackground | 2 (substitution + explicit Hintergrund layer + ci-defaults hoist) | 369 | sla_diff `--allow-brand-extras` for extra-style/extra-layer; CompressMethod hoist; PageBackground.for_page() widening |
| Plakat (#7) | 235 | 198 | 0 | 0 (regen alone meets ACs) | 198 | sla_diff `--allow-brand-extras` extension for extra-color (Hellgrün/Magenta) |
| **Zeitung (#8) THIS ISSUE** | 3244 | 2526 | **26** (12 PN + 14 CTS) | 2 (PageNumber widening + 26 substitutions) | **~2300** | sla_diff `--allow-brand-extras` extension for `missing-layer Ebene 1`; PageNumber kwarg passthrough widening |

Zeitung is the **largest payoff** of the three migrations: -944 LOC vs Postkarte's -68 and Plakat's -37. It's also the only migration where block substitutions provide significant value (26 subs vs Postkarte's 2 vs Plakat's 0). The `--allow-brand-extras` flag has now been extended once per migration (extra-style/extra-layer in #6, extra-color in #7, missing-layer in #8) — each extension is independent and trivially testable.

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` file in the worktree root (`ls /root/workspace/.worktrees/rewrite-zeitung-onto-brand-blocks/CLAUDE.md` → not found). No `.claude/skills/` directory either. The repo carries no project-level invariants beyond what ISSUE.md and the existing tests encode. **No additional constraints to honor.**

## Sources

### HIGH confidence (measured directly)

- `templates/zeitung-a4-grun/build.py` — current 3244 LOC, all sections classified by line range; idiom counts measured live.
- `tools/sla_to_dsl.py --help` and `tools/sla_to_dsl.py templates/zeitung-a4-grun/template.sla /tmp/zeitung-regenerated.py --template-id zeitung-a4-grun --assets-dir /tmp/zeitung-research-assets/` — converter run live; produced 2526-LOC build.py.
- Live built SLA from regen: `cd /tmp/zeitung-build && PYTHONPATH=... python3 build.py` produced 538740-byte `template.sla` (smoke test passed).
- `python3 tools/sla_diff.py --left gruene-zeitung-vorlage-original.sla --right /tmp/zeitung-build/template.sla --strict` — exit code 1 with 13 warnings (4 extra-layer + 8 extra-style + 1 missing-layer Ebene 1).
- `python3 tools/sla_diff.py ... --strict --allow-brand-extras` — **exit code 1 with 1 unfiltered warning (`missing-layer LAYERS .NAME: left='Ebene 1' right='(absent)'`)**. **This is the proof of R1.**
- `python3 tools/visual_diff.py /tmp/zeitung-build/template.sla --baseline templates/zeitung-a4-grun/baseline.pdf --tolerance templates/zeitung-a4-grun/diff.yml --dpi 96 --out /tmp/zeitung-vd/` — exit 0 (live-verified).
- `tools/sla_lib/builder/blocks.py` — all 5 block APIs read; PageNumber at lines 46-81, Impressum at 89-124, PageBackground at 134-205, ContactBlock at 241-290, ColumnTextStory at 298-334.
- `tools/sla_lib/builder/brand.py` and `shared/ci.yml` — Brand.gruene_noe() injects 4 layers (Hintergrund/Bilder/Text/Hilfslinien) and 7 colors.
- `tools/sla_diff.py:1202-1211` — `--allow-brand-extras` filter predicate verified to exclude `extra-style`/`extra-layer`/brand-`extra-color` only.
- `tools/sla_diff.py:1048-1050` — `missing-layer` issue is SEVERITY_WARNING.
- `tools/sla_lib/builder/document.py:200-237` — `Document(layers=[...])` REPLACES brand layers entirely (line 236: `if not self._layers_override: self._layers_override = list(brand.layers)`). Adding explicit `layers=[DocumentLayer('Ebene 1', ...)]` would lose the brand stack.
- `tools/sla_lib/tests/test_sla_to_dsl.py:163-184` — `ZeitungRoundTrip` confirmed to assert `summary[WARNING] == 0`.
- `tools/sla_lib/tests/test_sla_to_dsl.py:136-148` — Plakat's allowlist filter pattern verified for replication.
- `bin/validate:60-69` — already passes `--allow-brand-extras` to sla_diff.
- `grep -nE "<LAYERS " gruene-zeitung-vorlage-original.sla` — confirmed single `Ebene 1` layer (no Hintergrund); contrast with Postkarte/Plakat originals which have `Hintergrund`.
- `python3 -m pytest tools/sla_lib/tests -x` — confirmed 251 tests passing on current main.
- Zeitung Polygon coordinate inspection — verified all 8 polygons are non-bleed (none match the PageBackground geometry pattern).
- Zeitung Impressum frame inspection — confirmed 3-run schema (heading + spacer + body) at /tmp/zeitung-regenerated.py:2479-2497.
- Master page inspection — confirmed both masters are empty (no items added at master level); Codex master-chain bug N/A.
- 12 pgno frames mapped to pages 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13 (no pgno on page 0/Titelseite or page 10).
- 14 chains × 3 frames = 42 chained TextFrames; 28 link_to calls (= 14 × 2 wirings per chain length 3); chain ownership: chain1 on page1, chain0+chain2 on page2 (yes, two chains on one page), chain3 on page3, chain4 on page4, chain5 on page5, chain6 on page6, chain7 on page7, chain8 on page8, chain9 on page9, chain10 on page10, chain11 on page11, chain12+chain13 on page12.
- `bin/validate --ci` simulated with rebuilt zeitung — fails at preflight stale-preview gate (proves render-gallery step is mandatory).

### MEDIUM confidence

- LOC saved per block substitution (extrapolated from frame line counts; will be measured exactly during execution).
- Final ~2300 LOC estimate (depends on block-call line-wrapping style chosen by executor).

### LOW confidence (none load-bearing)

- Whether widening `PageNumber` with 4 kwarg passthroughs is "in scope" or "out of scope" for issue 8 — judgment call for the planner. Research recommends in-scope (trivial passthrough, ISSUE.md explicitly carved out "trivial kwarg passthrough"). Without the widening, PageNumber substitutions either leak attr-differs warnings or stay as primitives.

## Metadata

- **Sub-agents used:** None — this issue's research was done end-to-end in the orchestrator agent. Reasons: (a) codebase analysis required reading 3244 LOC + 2526-LOC regen + targeted bin/validate runs that benefit from sequential context; (b) ecosystem analysis is pure stdlib + project-internal (no external libraries); (c) pitfalls analysis is internal (sla_diff `missing-layer` semantics, Brand layer-replace semantics); (d) Postkarte EXECUTION.md (#6) and Plakat RESEARCH/EXECUTION.md (#7) provided 95% of the migration pattern, so the marginal value of multi-agent fan-out was low.
- **Research date:** 2026-05-07.
- **Confidence breakdown:**
  - Codebase audit: HIGH (all 3244 LOC classified by section; 140 page items inventoried by page; chain pattern fully reverse-engineered).
  - Block fitness: HIGH (PageNumber × 12 + ColumnTextStory × 14 verified by frame-by-frame inspection; PageBackground × 0 verified by polygon coordinate analysis; Impressum × 0 verified by 3-run schema mismatch).
  - LOC arithmetic: HIGH for the regenerator delta (measured live), MEDIUM for the post-edit estimate (arithmetic).
  - Validate-strict regression: HIGH (live-reproduced; 1 unfiltered missing-layer warning confirmed under --allow-brand-extras).
  - ZeitungRoundTrip test failure prediction: HIGH (current passing, brand emission would inject 13 warnings none of which are filtered by current test allowlist).
  - LOC ≤2400 feasibility: HIGH that it IS achievable with the recommended block substitutions (estimate ~2300).
  - Converter regressions: HIGH that NONE surface (live-tested all 14 pages, 14 chains, 87 clip frames, 6 inline images round-trip cleanly; visual_diff exit 0).
- **Raw research files:** None — no sub-agents, all findings are in this RESEARCH.md.

### 6-bullet summary (for orchestrator return)

1. **Regenerated LOC: 2526** (down from 3244; -718). All 4 numeric ACs (LOC ≤2400 with hand-edits, doc-attrs ≤23, pdf-attrs ≤11, Brand uptake) achievable; raw regen meets 3 of 4 immediately, LOC needs block subs.
2. **Block substitutions identified: 26** = 12× PageNumber (clean, ~144 LOC saved) + 14× ColumnTextStory (clean, ~84 LOC saved). PageBackground × 0 (no full-bleed polygons), Impressum × 0 (3-run schema gap), ContactBlock × 0.
3. **DSL gaps flagged: 1 hard blocker** (`--allow-brand-extras` doesn't cover `missing-layer Ebene 1` — Zeitung's original layer name doesn't overlap with brand stack) + **1 in-scope widening** (PageNumber kwarg passthrough for clip_edit/line_width_pt/col_gap_mm/var_attrs — trivial passthrough, falls inside ISSUE.md's carve-out) + **1 P2** (Impressum block 3-run heading+body schema — out of scope, third Impressum gap surfaced after Postkarte's bold-prefix + Plakat's rotation_deg).
4. **Converter regressions surfaced: NONE.** Master pages (empty), linked-story chains (14 × 3 = 42 frames + 28 link_to), clip-rect auto-emission (87 frames, 0 custom_path), inline images (6 = 6 xpos_pt), Brand emission, attr hoisting all round-trip cleanly. Codex's master-chain bug from #5 doesn't apply (Zeitung masters are item-empty).
5. **Visual-diff readiness: CLEAN.** visual_diff against baseline.pdf exits 0 on the regenerated SLA (live-tested at /tmp build, dpi=96). 14 pages, ~30-60s render time.
6. **Recommended PLAN.md task count: 6 tasks** — (1) extend `--allow-brand-extras` for `missing-layer Ebene 1`, (2) widen PageNumber with 4 kwarg passthroughs, (3) regenerate build.py + rebuild SLA, (4) substitute PageNumber × 12, (5) substitute ColumnTextStory × 14 + delete trailing link_to block, (6) update ZeitungRoundTrip allowlist + rebuild gallery + full validation + EXECUTION.md.
