# Research: Vorlagen — Überschriften-Zeilenabstände (Barlow/Vollkorn), Falzflyer-Social-Icons, automatisierter Abstands-Check

**Researched:** 2026-06-07
**Issue:** bx4d8
**Confidence:** HIGH (codebase mechanism fully traced); MEDIUM on social-icon root cause (two candidate causes, both source-fixable); MEDIUM on exact corrected Y/leading numbers (require a render+measure loop, not derivable statically)

<user_constraints>
## User Constraints (from CONTEXT.md)

No `CONTEXT.md` with `## Decisions` / `## Claude's Discretion` / `## Deferred Ideas` sections was found for this issue (the file present is a stub). The binding constraints therefore come from ISSUE.md and the predecessor c8bg0, treated as locked:

### Locked Decisions (from ISSUE.md + c8bg0, authoritative)
- **Fix at the SOURCE, never in the renderer.** All spacing/baseline corrections go into `templates/*/build.py` (frame Y, `LINESP`/leading, FLOP) and/or the shared emitter `tools/sla_lib/builder/primitives.py` — never patch Scribus output or the `visual_diff`/render path. (`docs/render-fidelity.md` repo principle.)
- **Font target is fixed: Barlow Semi Condensed (body/headline) + Vollkorn (accent/emphasis).** No re-litigating the font choice (decided in #42, applied in c8bg0). `pdffonts` on every rendered PDF must show ONLY Barlow + Vollkorn — no DejaVu/fallback.
- **No tool attribution** in commits, code, or comments (workspace CLAUDE.md + MEMORY).
- **No vendoring of third-party deps** EXCEPT the deliberate print-pipeline font exception (Barlow + Vollkorn TTFs live in repo / installed via `Dockerfile.claude` for fontconfig/Scribus). This is the only sanctioned vendoring here.
- **Baselines are promoted only after confirmed visual review.** New `baseline.pdf` per changed template is frozen only after multiple visual comparisons confirm balanced spacing, no clipping, `text_render_audit` ok, and `pdffonts` clean. CI does not render — baselines/previews are produced locally and committed; the stale-previews gate must stay green.

### Claude's Discretion
- Exact corrected per-line frame `y_mm` and per-style `LINESP` values (must be derived empirically via a render→pixel-measure→adjust loop).
- Whether the metric-driven correction lives as a new shared helper in `sla_lib.builder` vs. a small per-template recomputation — recommendation below favors the shared helper.
- Audit thresholds (recommended basis below), exact CLI surface of the new audit.

### Deferred Ideas (OUT OF SCOPE)
- Replacing the stacked-single-line-frame headline mechanism with a single multi-line frame (a larger refactor; not required to fix the gaps).
- Any further font substitution work.
</user_constraints>

## Summary

The four problems share one root mechanism. Multi-line "stacked" headlines (e.g. "Das ist die / **dreizeilige** / Headline") are NOT one multi-line text frame — the IDML `<Br/>`-joined line is **split into one single-line `TextFrame` per visual line**, each positioned by an absolute `y_mm`, because Scribus's per-line font-metric leading mis-places mixed-font lines when kept as one frame. Each frame uses Scribus **`FLOP=1` ("Font Ascent")**: the first (only) baseline sits **one font-ascent below the frame top**. The visible vertical gap between two stacked lines is therefore `Δy_mm` (the difference of the two frame tops) **minus** the ascent of line N **plus** the ascent of line N+1 — i.e. it is a function of each line's FONT ASCENT, not just the frame Y. The old `y_mm` values were tuned so that Gotham Narrow Ultra's ascent produced even gaps. Vollkorn Black Italic and Barlow Semi Condensed have different ascent/cap-height, so the same frame tops now yield **uneven gaps — the top gap collapses** exactly where a Barlow line sits above a Vollkorn line (the "dreizeilige" case). Concretely in `templates/flyer-a6-querformat-zweigeteilt/build.py` the `uaf8` headline frame tops are `y=58.6807 / 66.6182 / 77.7307 mm` → gaps **7.94mm (top) vs 11.11mm (bottom)** — the structural smoking gun.

The same font-ascent shift explains Problem 2 (Zeitung `Überschrift Dunkelgrün`, `linesp=35`/fontsize=40, single-line frames `h≈27.96mm`) and is why c8bg0 reportedly cut leading 35→28 to dodge clipping — a blunt fix that made some pairs too tight. The Falzflyer social icons (Problem 3) are **embedded inline RGBA PNGs** (`ImageFrame(inline_image_data=..., inline_image_ext='png')`, qCompress-encoded by `pack_inline_image`) in small ~17.8×15.6mm frames; the two source-fixable failure modes are (a) the documented **Scribus 1.6.x CMYK bug that renders white-on-transparent RGBA PNGs invisible when `SCALETYPE=1` at high downscale** (`primitives.py:866-868`), and (b) a broken/empty inline-image round-trip blob. Problem 4 (the audit) plugs naturally next to the existing `tools/line_spacing_*_audit.py` family, reusing the pixel-ink-top method and `sla_lib.reader.SLADocument` geometry.

**Primary recommendation:** Add a metric-driven baseline corrector in the shared emitter (`sla_lib.builder.primitives` / a new `headline_stack` helper) that, given per-line font + fontsize + a target inter-baseline `LINESP`, computes each stacked frame's `y_mm` from the actual Barlow/Vollkorn ascent so gaps are EVEN by construction — then regenerate the stacked-headline frames in all 12 affected flyer/falzflyer templates from that helper, re-render under xvfb, pixel-measure the gaps, promote baselines only after visual sign-off. Fix the social icons at source (force `SCALETYPE=0` fit-to-frame for the inline icon frames and/or re-pack a valid opaque-on-frame PNG). Ship a new `tools/headline_spacing_audit.py` wired into `bin/audit-alignment`/`bin/validate` + unittest.

## Codebase Analysis

### Relevant Code
| File | Purpose | Relevance |
|------|---------|-----------|
| `tools/sla_lib/builder/primitives.py` | `TextFrame`/`ImageFrame` dataclasses, FLOP emission (`:611-619`, `:706-715`), `pack_inline_image` (`:839-850`), `ImageFrame.scale_type`/`SCALETYPE` doc (`:861-869`) | **Crown jewel** — the FLOP/first-baseline and inline-image mechanisms both live here |
| `templates/flyer-a6-querformat-zweigeteilt/build.py` | The canonical "dreizeilige" case: stacked `uaf8`/`uaf8_l2`/`uaf8_l3` frames (`:271-303`) | Reference for the exact Y/LINESP/font-per-line pattern |
| `templates/zeitung-a4/build.py` | `Überschrift Dunkelgrün` ParaStyle `linesp=35, fontsize=40` (`:59`); frames at `:602/629/769/796/888/988` with `h≈27.96mm` | Problem 2 target |
| `templates/falzflyer-z-falz-6-seitig-*/build.py` (4 templates) | Social-icon `ImageFrame(inline_image_data=...)` (e.g. gruenes-cover `:193-200`, `anname='u141'`, `w=17.82 h=15.6052 mm`) | Problem 3 target |
| `tools/line_spacing_pixel_audit.py` | Rasterises PDFs, detects per-line **ink-top** per frame bbox; renderer-agnostic | Method to reuse for Problem 4 |
| `tools/line_spacing_audit.py` (E2, deprecated/informational), `line_spacing_full_audit.py` (E3 cross-source), `line_spacing_pixel_audit.py` (E4, authoritative) | Existing line-spacing audit family | The new audit extends this family — do NOT reinvent |
| `tools/sla_lib/reader.py` | `SLADocument`: `find_by_anname`, `page_objects`, `page_size_pt`, geometry | How the new audit reads SLA frame geometry |
| `tools/audit_alignment.py` + `bin/audit-alignment` (shim) | Alignment-audit entry; pattern for the new audit's CLI | Wiring target |
| `bin/validate` | Round-trip gate: `check-fontsizes` + `check-stale-previews` preflight, then `sla_diff --strict` + `visual_diff` per template | Where the new audit hooks in |
| `bin/render-gallery`, `bin/check-stale-previews`, `tools/text_render_audit.py`, `tools/font_audit.py` | Render + staleness + clipping + font gates | Render/baseline workflow |
| `shared/fonts/50-vollkorn-family-alias.conf` | fontconfig family alias (Vollkorn); Gotham→Barlow is resolved via fontconfig, NOT by rewriting build.py | Explains why build.py still says "Gotham Narrow Ultra" while renders show Barlow |

### Interfaces
<interfaces>
// From tools/sla_lib/builder/primitives.py — TextFrame (stacked-headline line frame)
@dataclass
class TextFrame(_Frame):
    x_mm: float; y_mm: float; w_mm: float; h_mm: float
    anname: str
    layer: int = 0
    style: Optional[str] = None              // <DefaultStyle PARENT=...>
    runs: list[Run] = ...                    // per-line runs (font, fontsize, fcolor)
    trail_attrs: Optional[dict] = None       // {'LINESPMode','LINESP', ...}
    default_style_attrs: Optional[dict] = None
    first_line_offset: Optional[int] = None  // -> Scribus FLOP; None => default 1 ("Font Ascent")
    rotation_deg: float = 0.0
    # FLOP semantics (primitives.py:611-619, 706-715):
    #   0=Maximum Ascent  1=Font Ascent (DEFAULT, = InDesign AscentOffset)
    #   2=Line Spacing    3=Baseline Grid
    #   With FLOP=1 the (only) baseline of a single-line frame sits one FONT ASCENT
    #   below the frame top. => visible gap between stacked lines depends on each
    #   line's font ascent, which is why Gotham-tuned y_mm break under Barlow/Vollkorn.

// From tools/sla_lib/builder/primitives.py — inline social-icon image
@dataclass
class ImageFrame(_Frame):
    src: str = ""; image: str = ""
    layer: int = 1
    local_scale: tuple[float,float] = (1.0,1.0)
    scale_type: int = 0          // SCALETYPE: 0=fit-to-frame(safe), 1=free(triggers 1.6.x white-RGBA-invisible bug)
    ratio: int = 1; pic_art: int = 1
    inline_image_data: Optional[str] = None   // qCompress base64 (from pack_inline_image)
    inline_image_ext: Optional[str] = None    // e.g. 'png'
    # primitives.py:861-869: default scale_type=0 BECAUSE Scribus 1.6.x turns
    # white-on-transparent RGBA PNGs INVISIBLE under SCALETYPE=1 + high downscale.

def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    # base64( struct.pack(">I", len(raw)) + zlib.compress(raw, 6) ), ext
    # Naive base64 of raw bytes => Scribus qUncompress Z_DATA_ERROR. (primitives.py:839-850)

// From tools/sla_lib/reader.py — geometry source for the new audit
class SLADocument:
    def __init__(self, path): ...
    def page_size_pt(self) -> tuple[float, float]
    def page_objects(self) -> list[etree._Element]
    def find_by_anname(self, anname: str) -> etree._Element | None
    def frame_text(self, frame) -> str
    # frame XPOS/YPOS/HEIGHT/WIDTH read off the PAGEOBJECT element attributes

// From templates/flyer-a6-querformat-zweigeteilt/build.py:271-303 — the canonical defect
// uaf8     : y_mm=58.6807  font='Gotham Narrow Ultra'(->Barlow) fontsize=30 LINESP=27.0
// uaf8_l2  : y_mm=66.6182  font='Vollkorn Black Italic'         fontsize=30  (gap from l1 = 7.94mm)  <-- TOP GAP TOO TIGHT
// uaf8_l3  : y_mm=77.7307  font='Gotham Narrow Ultra'(->Barlow) fontsize=30  (gap from l2 = 11.11mm) <-- BOTTOM GAP

// From templates/zeitung-a4/build.py:59 — Problem 2 style
// ParaStyle('Überschrift Dunkelgrün', font='Gotham Narrow Ultra'(->Barlow),
//           fontsize=40, linesp=35, linesp_mode=0); frames h_mm≈27.963 (≈79.3pt)
</interfaces>

### The exact mechanism / formula (Problem 1)
For two vertically adjacent single-line frames with FLOP=1:
```
baseline_N   = frame_top_N   + ascent(font_N,  size_N)
baseline_N+1 = frame_top_N+1 + ascent(font_N+1, size_N+1)
visible_inter_baseline_gap = baseline_N+1 - baseline_N
                           = (frame_top_N+1 - frame_top_N) + ascent(font_N+1) - ascent(font_N)
```
To make all inter-baseline gaps equal a single target `LINESP_target` (the design leading), solve for each frame top:
```
frame_top_{k+1} = frame_top_k + LINESP_target - ascent(font_{k+1}) + ascent(font_k)
```
i.e. **the per-line frame `y_mm` must be driven by the per-font ascent.** Today the `y_mm` are frozen Gotham-tuned constants; the per-line `LINESP=27.0` (`trail_attrs`) is uniform and largely cosmetic because each frame holds ONE line. The "per-font FLOP=1 baseline correction" the issue refers to is precisely this ascent term — currently baked into hand-tuned `y_mm` instead of computed from metrics.

**Font metrics should drive the offset** from the actual installed TTFs. Read ascent/cap-height via fontTools (`TTFont(...)['hhea'].ascent`, `['head'].unitsPerEm`, or `OS/2.sCapHeight`) for `fc-match "Barlow Semi Condensed"` and `fc-match "Vollkorn"` (Black Italic). Scale `ascent_pt = ascent_units / unitsPerEm * fontsize`. The Barlow vs Vollkorn ascent delta is the correction.

### Templates using stacked Barlow+Vollkorn headlines ("dreizeilige" class) — full list
All have stacked `*_l2`/`*_l3` single-line frames AND Vollkorn lines. Confirmed via `grep "anname='..._l[0-9]'"` + `grep Vollkorn`:

**Falzflyer (z-falz 6-seitig) — 4 templates, 4 stacked frames each:**
- `templates/falzflyer-z-falz-6-seitig-gruenes-cover/build.py`
- `templates/falzflyer-z-falz-6-seitig-gruenes-cover-2/build.py`
- `templates/falzflyer-z-falz-6-seitig-portraet/build.py`
- `templates/falzflyer-z-falz-6-seitig-zweigeteiltes-cover/build.py`

**Flyer A6 — 8 templates:**
- `templates/flyer-a6-hochformat-gruenes-cover/build.py` (2 stacked)
- `templates/flyer-a6-hochformat-portraet/build.py` (3)
- `templates/flyer-a6-hochformat-quadrat-im-bild/build.py` (3)
- `templates/flyer-a6-hochformat-zweigeteilt/build.py` (3)
- `templates/flyer-a6-querformat-gruenes-cover/build.py` (2)
- `templates/flyer-a6-querformat-portraet/build.py` (3)
- `templates/flyer-a6-querformat-quadrat-im-bild/build.py` (3)
- `templates/flyer-a6-querformat-zweigeteilt/build.py` (3) — **canonical "dreizeilige" reference**

**Also contain Vollkorn (review, may have all-Barlow stacked headlines too):** `templates/postkarte-a6-kampagne/build.py`, `templates/tischschild-a5-quer/build.py`, `templates/plakat-a1-hochformat/build.py`, `templates/zeitung-a4/build.py`. The `26-03-*` mirror templates (`templates/26-03-*`) are the IDML-named twins — check whether they are rendered/shipped or superseded by the un-prefixed set; if shipped, apply the same fix.

**All-Barlow stacked headlines** (stacked `_l2`/`_l3` frames where every line is Gotham→Barlow, no Vollkorn line, e.g. `uaf8`/`uaf8_l3` are both Barlow): these still drift because Barlow's ascent ≠ Gotham's, so even uniform-font stacks need the metric recompute — they are a subset of the same fix, just with `ascent(font_k)==ascent(font_{k+1})` so the correction reduces to a single uniform `LINESP_target`.

### Reusable components
- `pack_inline_image` (re-pack icon PNGs), `SLADocument` (geometry read), `line_spacing_pixel_audit.py` ink-top detector (copy/import the per-frame rasterise+scan), `audit_alignment.py` CLI/shim pattern, `tools/font_audit.py`/`text_render_audit.py` gates.
- fontTools is already a dependency (used by `tools/font_*`); reuse it for ascent metrics.

### Potential conflicts
- **This worktree's HEAD predates c8bg0's merge** (`git log` top = `f7yk1` archive; `zeitung-a4/build.py:59` still shows `linesp=35`, not the 28 the issue attributes to c8bg0; build.py fonts still literally say "Gotham Narrow"). **Rebase/merge c8bg0 first** or the Barlow/Vollkorn state the issue assumes will not be present. This is the single biggest setup risk.

## Standard Stack
| Library | Version | Purpose | Why Standard | Confidence |
|---------|---------|---------|--------------|------------|
| fontTools | repo dep | Read Barlow/Vollkorn ascent/cap-height/unitsPerEm to drive the baseline correction | Already used by `tools/font_*`; canonical metric source | HIGH |
| pdfplumber + pixel raster (pdftoppm/pymupdf) | repo dep | Pixel ink-top gap measurement (renderer-agnostic) | The established authoritative method (`line_spacing_pixel_audit.py`) | HIGH |
| Scribus 1.6.x (xvfb, dev container) | container | Render `.sla` → PDF | Repo's only renderer; CI does not render | HIGH |
| fontconfig (`fc-match`) | system | Resolve "Gotham Narrow *"/"Barlow"/"Vollkorn" family aliases to TTFs | How font swap is realized without editing build.py | HIGH |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Metric-driven shared helper recompute | Hand-edit each `y_mm` per template | Hand-edit = 12+ templates × N lines of fragile constants that break on the next font change; helper generalizes and is testable. **Choose helper.** |
| Keep stacked single-line frames | Collapse to one multi-line frame | Single frame re-introduces the Scribus mixed-font per-line-leading mis-placement the split was created to avoid. Out of scope. Keep stacked. |

## Don't Hand-Roll
| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Read font ascent/cap-height | Hardcode pt constants per font | fontTools on the fc-matched TTF | Survives font changes; constants are exactly what broke here |
| Inline PNG encode | Custom base64 | `pack_inline_image` | Scribus needs qCompress(len-prefix+zlib); naive b64 => Z_DATA_ERROR |
| Read SLA frame geometry | Regex/manual XML | `sla_lib.reader.SLADocument` | Already handles PAGEOBJECT attrs/anname lookup |
| Measure rendered line gaps | pdfplumber text-matrix Y | pixel ink-top (`line_spacing_pixel_audit`) | text-matrix Y lies across renderers (documented F-014/F-017) |

## Architecture Patterns
### Recommended approach
1. **Source fix Problem 1 (shared, metric-driven):** add a helper in `sla_lib.builder` (e.g. `headline_stack(lines=[(text,font,size,fcolor)], top_y_mm, x_mm, w_mm, h_mm, linesp_pt, align)`) that emits one single-line `TextFrame` per line with FLOP=1 and computes each subsequent `y_mm` via `frame_top_{k+1} = frame_top_k + linesp_pt - ascent(font_{k+1},size) + ascent(font_k,size)` (ascents from fontTools on fc-matched TTFs, mm-converted). Regenerate the stacked frames in the 12 templates from this helper. Pick `linesp_pt` per headline from the design (start at the existing IDML Leading, e.g. 27pt @ size 30; tune empirically).
2. **Source fix Problem 2 (Zeitung):** treat `Überschrift Dunkelgrün` the same way. Frames are `h≈27.96mm (≈79.3pt)`, fontsize=40 → a single 40pt line needs ascent+descent ≈ 40–48pt, so `h` is ample; clipping was from leading interacting with multi-line content, not single headlines. Set a leading that clears Barlow's ascent+descent (≈ 30–32pt is the safe window: ≥ ~1.0–1.05× cap-stack to avoid clipping, ≤ ~0.8× of the old 35 to keep pairs from touching). Verify against `text_render_audit` (no clip) and pixel gaps (even).
3. **Source fix Problem 3 (social icons):** for each falzflyer inline-icon `ImageFrame`, set `scale_type=0` (fit-to-frame) — this avoids the 1.6.x white-RGBA-invisible bug — and/or re-pack the icon PNG (composite onto an opaque/colored fill, or ensure the PNG is non-empty/valid via `pack_inline_image`). Re-render, confirm icons visible in preview, `pdffonts` unaffected.
4. **Problem 4 audit:** new `tools/headline_spacing_audit.py` (see below), wired into `bin/audit-alignment` and the `bin/validate` chain + unittest.

### Anti-patterns to avoid
- **Renderer patches / post-processing the PDF** — forbidden by `docs/render-fidelity.md`.
- **Hardcoding new Gotham-style magic `y_mm`** — re-creates the same future-break.
- **Promoting baselines before visual sign-off** — violates the locked workflow.
- **`SCALETYPE=1` on white/transparent inline icons** — triggers the invisibility bug.

## Common Pitfalls
### Stale worktree (no Barlow/Vollkorn yet)
**What goes wrong:** build.py still says "Gotham Narrow"; zeitung still `linesp=35`; fixes land on pre-c8bg0 state. **Why:** worktree HEAD predates c8bg0 merge. **Avoid:** rebase/merge c8bg0 into the issue branch FIRST; verify `fc-match "Barlow Semi Condensed"` → Barlow TTF and `pdffonts` shows Barlow+Vollkorn before measuring. **Warning sign:** renders show Gotham metrics or DejaVu fallback.

### pdfplumber text-matrix Y is misleading
**What goes wrong:** gap audit passes while renders look wrong. **Why:** text-matrix Y ≠ rendered ink; ascent differs per renderer. **Avoid:** use pixel ink-top (the `line_spacing_pixel_audit` method) for the new audit. **Warning sign:** audit green but visual review flags tight top gap.

### Clipping when tightening leading
**What goes wrong:** reducing leading clips descenders/caps. **Why:** frame `h` < line height. **Avoid:** keep `h` ≥ ascent+descent of largest line; gate with `text_render_audit`. **Warning sign:** `text_render_audit` clip report.

### Scribus 1.6.x white-RGBA invisibility
**What goes wrong:** social icon frame renders blank. **Why:** `SCALETYPE=1` + high downscale + white-on-transparent RGBA (`primitives.py:866-868`). **Avoid:** `scale_type=0`. **Warning sign:** icon frame present in SLA but absent in PNG.

## Environment Availability
| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| Scribus 1.6.x + xvfb | rendering | Dev container only | CI does not render — stale-previews gate instead |
| fontconfig / fc-match | font resolution | container | must resolve Barlow + Vollkorn after c8bg0 |
| Barlow + Vollkorn TTFs | render fidelity | repo / Dockerfile.claude | sanctioned print-pipeline vendoring exception |
| fontTools, pdfplumber, pdftoppm/pymupdf | metrics + audit | repo deps | reuse |

## Render + baseline + audit workflow (commands)
```bash
# 0. Ensure Barlow/Vollkorn present (post-c8bg0):
fc-match "Barlow Semi Condensed"; fc-match "Vollkorn"

# 1. Render a template (xvfb-wrapped Scribus) and refresh gallery previews:
bin/render-gallery                      # renders templates/*/ -> template.sla, preview.pdf, PNGs
#   (single template render path is inside render-gallery / tune-render)

# 2. Measure stacked-headline gaps (renderer-agnostic pixel ink-top):
python3 tools/line_spacing_pixel_audit.py --slug flyer-a6-querformat-zweigeteilt \
    --templates-dir templates --out-yaml build/validation/<slug>/lsp.yml
python3 tools/headline_spacing_audit.py --slug flyer-a6-querformat-zweigeteilt   # NEW

# 3. Gates: clipping + fonts:
python3 tools/text_render_audit.py ...        # must be clip-free
pdffonts templates/<slug>/preview.pdf          # ONLY Barlow + Vollkorn, no fallback

# 4. Validate chain (preflight runs check-fontsizes + check-stale-previews):
bin/validate                                   # sla_diff --strict + visual_diff per template
bin/audit-alignment                            # + new headline audit hook

# 5. Promote preview -> baseline ONLY after visual sign-off:
#    freeze preview.pdf -> baseline.pdf per changed template, update diff.yml/TOLERANCES.yml,
#    refresh preview PNGs + staleness metadata so check-stale-previews stays green, commit.
```

## The new automated headline-spacing audit (Problem 4)
**Where it lives:** `tools/headline_spacing_audit.py` (new), alongside the existing `tools/line_spacing_audit.py` (E2, deprecated/informational), `tools/line_spacing_full_audit.py` (E3 cross-source), `tools/line_spacing_pixel_audit.py` (E4, authoritative pixel method). Reuse E4's rasterise+ink-top scanner rather than duplicating it (import or refactor a shared helper).

**What it measures:** for each group of stacked single-line headline frames (frames sharing an `anname` stem `X`, `X_l2`, `X_l3`, …), the **vertical gap between consecutive line baselines/ink-tops**. Flags: (a) any gap **too tight** (< threshold), (b) **uneven** gaps within one stack (max−min beyond tolerance), and specifically (c) **top gap < other gaps** (the "dreizeilige" signature). Emit YAML + non-zero exit on violation.

**How it reads SLA geometry:** via `sla_lib.reader.SLADocument` — `page_objects()` / `find_by_anname()` to get each line frame's XPOS/YPOS/HEIGHT/WIDTH and group by `_l<n>` stem; then either (i) compute expected baselines from FLOP=1 + fontTools ascent (static, fast, no render), or (ii) measure actual ink-tops from `preview.pdf` via the E4 rasteriser (truth). Recommend BOTH: static check in CI (no render) + pixel check locally.

**Wiring:** add a `bin/audit-alignment`-style shim or a call inside `tools/audit_alignment.py`'s rollup, and invoke from the `bin/validate` chain. Add `tools/sla_lib/tests/test_headline_spacing_audit.py` (unittest, alongside `test_audit_alignment.py`) with a synthetic SLA fixture: one even stack (passes) and one with a collapsed top gap (fails).

**Threshold basis (testable):** uneven if `(max_gap - min_gap) / mean_gap > ~0.15` (15%), OR top_gap < 0.9 × mean of other gaps, OR any gap < `min_ratio × fontsize` (e.g. < 0.85 × line fontsize in pt). Derive the exact numbers from the corrected baselines so passing templates set the floor; document in `SKILL_FINDINGS.md`.

## Project Constraints (from CLAUDE.md)
- **No vendoring** of third-party deps (CDN/package manager) — EXCEPT the sanctioned Barlow+Vollkorn print-pipeline fonts.
- **No tool attribution** in commits/code/comments (no "claude", "Generated with", `Co-Authored-By`).
- Repo principle: **fix at source, not renderer** (`docs/render-fidelity.md`).

## Sources
### HIGH confidence
- Codebase: `tools/sla_lib/builder/primitives.py` (FLOP `:611-619/706-715`, `pack_inline_image` `:839-850`, SCALETYPE bug `:861-869`), `templates/flyer-a6-querformat-zweigeteilt/build.py:271-303`, `templates/zeitung-a4/build.py:59,602+`, falzflyer `build.py` inline-icon frames, `tools/line_spacing_pixel_audit.py`, `tools/sla_lib/reader.py`, `bin/validate`, `bin/audit-alignment`, `tools/audit_alignment.py`.
- ISSUE.md + c8bg0 ISSUE.md (locked constraints, font target, workflow).
### MEDIUM confidence
- Social-icon root cause: two candidate source causes (SCALETYPE=1 white-RGBA invisibility; broken inline blob). Both source-fixable; confirm which by rendering one affected falzflyer and inspecting the icon frame.
- Exact corrected `y_mm`/`LINESP`/leading values — require render→measure→adjust loop.

## Metadata
**Confidence breakdown:** Mechanism/formula HIGH; template inventory HIGH; social-icon cause MEDIUM (needs one render to disambiguate); exact numbers MEDIUM (empirical). 
**Research date:** 2026-06-07
**Sub-agents used:** none (time-boxed direct investigation, ~40 tool calls)
**Raw research files:** n/a (direct)
