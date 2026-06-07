# Plan: Vorlagen — Überschriften-Zeilenabstände (Barlow/Vollkorn), Falzflyer-Social-Icons, Abstands-Audit

<objective>
What this plan accomplishes: Fix the three layout regressions introduced by the
c8bg0 Barlow Semi Condensed + Vollkorn font swap, and add an automated
headline-spacing audit that catches them in the future.

1. Stacked multi-part headlines sit too tight at the top (Barlow line above a
   Vollkorn line — the "dreizeilige" case). The per-line frame `y_mm` were tuned
   for Gotham's ascent; Barlow/Vollkorn have different ascents so the visible
   gaps became uneven. Fix by computing each stacked frame's `y_mm` from the
   ACTUAL installed-font ascent (fontTools) in a shared emitter helper, so gaps
   are even by construction across all 12 affected templates.
2. `zeitung-a4` `Überschrift Dunkelgrün` leading was cut 35→28pt in c8bg0
   (against clipping) and is now too tight — re-justify to a safe ~30–32pt window.
3. Falzflyer inline social-media icons render wrong (blank/garbled). Fix at the
   source emitter (`scale_type=0` fit-to-frame and/or re-pack a valid PNG via
   `pack_inline_image`).
4. New `tools/headline_spacing_audit.py` wired into `bin/audit-alignment` /
   `bin/validate`, with unittest — flags too-tight, uneven, and top-gap-collapse
   headline stacks.

Why it matters: These are user-visible print-layout defects on shipped templates,
and without an automated gate the next font/layout change will silently
re-introduce them.

Scope: IN — source fixes in `tools/sla_lib/builder/primitives.py` and
`templates/*/build.py`, the new audit + its wiring + tests, re-rendering affected
templates, and (gated on human visual sign-off) baseline promotion. OUT —
replacing the stacked-single-line-frame mechanism with one multi-line frame,
any further font substitution, renderer/PDF post-processing.

No CONTEXT.md `## Decisions` block existed beyond the five Entscheidungen; the
binding decisions come from CONTEXT.md's five Entscheidungen + ISSUE.md + c8bg0,
all treated as locked (see RESEARCH `<user_constraints>`).
</objective>

<strategy>
Direction: fix the ROOT mechanism once, not 12 templates by hand. All three
spacing problems are the same bug — stacked single-line headline frames use
Scribus FLOP=1 (first baseline one font-ascent below the frame top), so the
visible inter-line gap is `Δy_mm − ascent(font_N) + ascent(font_N+1)`. The old
`y_mm` were frozen constants tuned for Gotham's ascent; Barlow and Vollkorn have
different ascents, so the top gap collapses wherever a Barlow line sits above a
Vollkorn line.

Chosen option: a metric-driven baseline corrector in the shared emitter
(`sla_lib.builder`), driven by real ascents read from the fc-matched TTFs via
fontTools. Given a target inter-baseline leading, it solves
`frame_top_{k+1} = frame_top_k + linesp − ascent(font_{k+1}) + ascent(font_k)`
so gaps are even by construction. Rejected: hand-editing each `y_mm` per template
(12+ templates × N fragile constants that re-break on the next font change) and
collapsing to a single multi-line frame (re-introduces the Scribus mixed-font
per-line-leading mis-placement the split exists to avoid).

Key decision points: (a) the helper lives in the shared emitter, not per template;
(b) zeitung-a4 is the same class of fix (leading window 30–32pt, gated by
text_render_audit); (c) social icons fixed at source via `scale_type=0`/re-pack;
(d) baselines are promoted ONLY after a focused human visual review of headline
spacing — Task 6 is a `checkpoint:human-verify`, mirroring c8bg0.

Setup risk (RESEARCH): this worktree's HEAD may predate c8bg0's merge. Task 0
verifies the Barlow/Vollkorn state before any measurement — without it, fixes
land on stale Gotham metrics.
</strategy>

<skills>
Read and follow this skill during execution:
- @.claude/skills/idml-tune/SKILL.md — per-template build.py visual polish; the
  render → measure → validate → baseline workflow, the inventory gate, and the
  set of permitted per-template edits (build.py, inject.yml, meta.yml
  brand_overrides, TOLERANCES.yml). NOTE: this plan ALSO edits the shared emitter
  `tools/sla_lib/builder/primitives.py` and adds `tools/headline_spacing_audit.py`,
  which are outside idml-tune's normal per-template box — that is intentional and
  in scope for this issue (a shared-mechanism fix), so the idml-tune "converter /
  sla_lib FORBIDDEN" rule does NOT apply to this issue's emitter task.
</skills>

<context>
Issue: @.issues/bx4d8-vorlagen-überschriften-zeilenabstände-bei-barlowvollkorn-korrigieren-falzflyer-s/ISSUE.md
Research: @.issues/bx4d8-vorlagen-überschriften-zeilenabstände-bei-barlowvollkorn-korrigieren-falzflyer-s/RESEARCH.md
Context: @.issues/bx4d8-vorlagen-überschriften-zeilenabstände-bei-barlowvollkorn-korrigieren-falzflyer-s/CONTEXT.md

Repo root: /workspace/vorlagen
Work in this worktree: the branch is already checked out here.

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

From tools/sla_lib/builder/primitives.py — TextFrame (a stacked-headline line frame):
@dataclass
class TextFrame(_Frame):
    x_mm: float; y_mm: float; w_mm: float; h_mm: float
    anname: str
    layer: int = 0
    style: Optional[str] = None              # <DefaultStyle PARENT=...>
    runs: list[Run] = ...                    # per-line runs (font, fontsize, fcolor)
    trail_attrs: Optional[dict] = None       # {'LINESPMode','LINESP', ...}
    default_style_attrs: Optional[dict] = None
    first_line_offset: Optional[int] = None  # -> Scribus FLOP; None => builder default 1 ("Font Ascent")
    rotation_deg: float = 0.0
# FLOP semantics: 0=Maximum Ascent  1=Font Ascent (DEFAULT = InDesign AscentOffset)
#   2=Line Spacing  3=Baseline Grid. With FLOP=1 the single baseline of a
#   single-line frame sits one FONT ASCENT below the frame top — so the visible
#   gap between two stacked lines = Δy_mm − ascent(font_N) + ascent(font_N+1).

From tools/sla_lib/builder/primitives.py — inline social-icon image:
@dataclass
class ImageFrame(_Frame):
    src: str = ""; image: str = ""
    layer: int = 1
    local_scale: tuple[float,float] = (1.0,1.0)
    scale_type: int = 0          # SCALETYPE: 0=fit-to-frame (safe), 1=free (triggers 1.6.x white-RGBA-invisible bug)
    ratio: int = 1; pic_art: int = 1
    inline_image_data: Optional[str] = None   # qCompress base64 (from pack_inline_image)
    inline_image_ext: Optional[str] = None    # e.g. 'png'

def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    # returns ( base64( struct.pack(">I", len(raw)) + zlib.compress(raw, 6) ), ext )
    # Naive base64 of raw bytes => Scribus qUncompress Z_DATA_ERROR.

From tools/sla_lib/reader.py — geometry source for the new audit:
class SLADocument:
    def __init__(self, path): ...
    def page_size_pt(self) -> tuple[float, float]
    def page_objects(self) -> list[etree._Element]                 # PAGEOBJECT elements
    def find_by_anname(self, anname: str) -> etree._Element | None
    def frame_text(self, frame: etree._Element) -> str
    # frame XPOS/YPOS/HEIGHT/WIDTH are attributes on the PAGEOBJECT element.

The canonical defect — templates/flyer-a6-querformat-zweigeteilt/build.py:271-303:
# uaf8    : y_mm=58.6807  font='Gotham Narrow Ultra'(->Barlow) fontsize=30 LINESP=27.0
# uaf8_l2 : y_mm=66.6182  font='Vollkorn Black Italic'         fontsize=30   gap l1->l2 = 7.94mm  <- TOP GAP TOO TIGHT
# uaf8_l3 : y_mm=77.7307  font='Gotham Narrow Ultra'(->Barlow) fontsize=30   gap l2->l3 = 11.11mm <- BOTTOM GAP

Problem 2 — templates/zeitung-a4/build.py:59:
# ParaStyle('Überschrift Dunkelgrün', font='Gotham Narrow Ultra'(->Barlow),
#           fontsize=40, linesp=35 (was cut to 28 in c8bg0), linesp_mode=0)
# frames at :602/:629/:769/:796/:888/:988 have h_mm ≈ 27.963 (≈79.3pt) — ample for one 40pt line.

The ascent-driven correction formula (FLOP=1, two adjacent single-line frames):
  baseline_k   = frame_top_k   + ascent(font_k,  size_k)
  baseline_k+1 = frame_top_k+1 + ascent(font_k+1,size_k+1)
  gap = baseline_k+1 - baseline_k = (frame_top_k+1 - frame_top_k) + ascent(font_k+1) - ascent(font_k)
  To make every inter-baseline gap == linesp_target:
  frame_top_{k+1} = frame_top_k + linesp_target - ascent(font_{k+1}) + ascent(font_k)
  ascent_pt(font,size) = TTFont(ttf)['hhea'].ascent / TTFont(ttf)['head'].unitsPerEm * size
  ttf resolved via `fc-match -f '%{file}' "<family>"`; mm = pt / 72 * 25.4.
</interfaces>

## Call-site enumeration

This plan adds ONE new CLI surface: `tools/headline_spacing_audit.py` with a
`--slug` flag (and its wiring), plus it touches the shared emitter (no CLI flag
change). Before finalizing Task 4, the executor MUST grep for adjacent invocation
sites of the audit family and the validate chain so no caller is missed:

Searched (do in Task 4): `headline_spacing_audit`, `line_spacing_pixel_audit`,
`audit-alignment`, `audit_alignment`.
Surfaces grepped: `.github/workflows/`, `Makefile`, `bin/`, `tools/`, `README*`, `docs/`.

Expected in-scope edits (confirm exact paths/lines during Task 4):
- `bin/audit-alignment` (shim) — add the new audit to the rollup — IN SCOPE (Task 4)
- `tools/audit_alignment.py` — its rollup, if `bin/audit-alignment` delegates here — IN SCOPE (Task 4)
- `bin/validate` — the validate chain (`check-fontsizes` + `check-stale-previews`
  preflight then `sla_diff --strict` + `visual_diff`) — IN SCOPE (Task 4, hook the audit in)
- `.github/workflows/*.yml` — if CI invokes `bin/validate`/`bin/audit-alignment`,
  the static (no-render) audit mode runs there automatically; confirm it does NOT
  require a render — IN SCOPE to verify, no separate edit expected.

If the grep returns additional invokers (e.g. a Makefile target, a `ci-local`
shim), fold each into Task 4 or record it as an explicit out-of-scope decision
with a one-line reason. If zero additional sites: state "No additional call sites found."

Key files:
@tools/sla_lib/builder/primitives.py — FLOP emission (~:611-619, :706-715),
  `pack_inline_image` (~:839-850), `ImageFrame.scale_type`/SCALETYPE doc (~:861-869).
@tools/sla_lib/reader.py — `SLADocument` geometry reader for the audit.
@tools/line_spacing_pixel_audit.py — authoritative pixel ink-top method to reuse.
@tools/audit_alignment.py + @bin/audit-alignment — CLI/shim pattern + wiring target.
@bin/validate — round-trip + visual gate chain.
@templates/flyer-a6-querformat-zweigeteilt/build.py — canonical stacked-headline reference.
@templates/zeitung-a4/build.py — Problem 2 target.
@tools/sla_lib/tests/test_audit_alignment.py — unittest pattern for the new test.
</context>

<commit_format>
Format: conventional with issue prefix (per .issues/config.yaml: commits.format=conventional, prefix=true).
Pattern: {issue-id}: {type}({scope}): {description}
Examples:
  bx4d8: feat(sla): metric-driven stacked-headline baseline corrector
  bx4d8: fix(templates): even Barlow/Vollkorn headline gaps across 12 flyers
  bx4d8: fix(zeitung-a4): widen Überschrift Dunkelgrün leading to safe window
  bx4d8: fix(falzflyer): force scale_type=0 so inline social icons render
  bx4d8: feat(tools): headline_spacing_audit + bin/validate wiring + tests
Types: feat, fix, test, refactor, docs, chore.
NO tool attribution anywhere (no "claude", "Generated with", Co-Authored-By).
</commit_format>

<tasks>

<task type="auto">
  <name>Task 0: Verify post-c8bg0 font state (setup gate)</name>
  <files>(no edits — verification only)</files>
  <action>
  RESEARCH names this the single biggest setup risk: this worktree's HEAD may
  predate the c8bg0 merge, in which case build.py still resolves to Gotham and
  zeitung-a4 still shows `linesp=35`, so every later measurement would be against
  stale metrics.

  Confirm the Barlow + Vollkorn state is present BEFORE touching any spacing:
  - Run `fc-match "Barlow Semi Condensed"` and `fc-match "Vollkorn"` — both must
    resolve to the installed Barlow / Vollkorn TTFs, NOT DejaVu.
  - Inspect `templates/zeitung-a4/build.py:59`: note the current `linesp` value of
    `Überschrift Dunkelgrün` (RESEARCH saw 35 in the stale worktree; c8bg0 cut it
    to 28). Record which state you are in.
  - If the worktree is pre-c8bg0 (Gotham literals AND no Vollkorn lines rendering,
    or fc-match falls back to DejaVu): STOP and merge/rebase `c8bg0` (or `main`
    if c8bg0 is already merged there) into this branch first, then re-verify. Do
    NOT proceed on stale state.
  - Render the canonical template once and confirm fonts:
    `bin/render-gallery` (or the single-template render path inside it) for
    `flyer-a6-querformat-zweigeteilt`, then
    `pdffonts templates/flyer-a6-querformat-zweigeteilt/preview.pdf` — output must
    show ONLY Barlow + Vollkorn, no fallback.
  This task establishes the measurement baseline for Tasks 1-3.
  </action>
  <verify>
  <automated>cd /workspace/vorlagen && fc-match "Barlow Semi Condensed" && fc-match "Vollkorn" && pdffonts templates/flyer-a6-querformat-zweigeteilt/preview.pdf</automated>
  </verify>
  <done>
  - fc-match resolves Barlow Semi Condensed and Vollkorn to their TTFs (no DejaVu)
  - pdffonts on the canonical preview shows only Barlow + Vollkorn
  - The branch is confirmed on post-c8bg0 state (or c8bg0 has been merged in)
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 1: Metric-driven stacked-headline baseline corrector in the shared emitter</name>
  <files>tools/sla_lib/builder/primitives.py, tools/sla_lib/builder/__init__.py, tools/sla_lib/tests/test_headline_stack.py</files>
  <action>
  Add a shared helper in `tools/sla_lib/builder` (place it next to the
  `TextFrame` machinery in `primitives.py`, or a sibling module re-exported from
  `tools/sla_lib/builder/__init__.py`) that builds an EVEN-gap stacked headline
  from font metrics instead of hand-tuned `y_mm` constants.

  Signature (adjust names to match repo conventions, keep semantics):
    def headline_stack(
        lines: list[tuple[str, str, float, str]],  # (text, font_family, fontsize_pt, fcolor)
        top_y_mm: float, x_mm: float, w_mm: float, h_mm: float,
        linesp_pt: float, anname_stem: str,
        align: str = "left", style: str | None = None,
    ) -> list[TextFrame]: ...

  Behavior (TDD — write tests first in test_headline_stack.py):
  - Emits one single-line `TextFrame` per line, anname `{stem}`, `{stem}_l2`,
    `{stem}_l3`, … (matching the existing naming so the audit can group them).
  - Every frame uses FLOP=1 (`first_line_offset=1` or the builder default).
  - Frame `k=0` top is `top_y_mm`. Each subsequent top:
      frame_top_{k+1} = frame_top_k + linesp_pt_mm
                        - ascent_mm(font_{k+1}, size_{k+1})
                        + ascent_mm(font_k, size_k)
    where `linesp_pt_mm = linesp_pt / 72 * 25.4`.
  - Ascent comes from a small cached metric reader: resolve the family TTF via
    `fc-match -f '%{file}' "<family>"`, load with fontTools `TTFont`, compute
    `ascent_pt = ttf['hhea'].ascent / ttf['head'].unitsPerEm * size`, convert to
    mm. Cache by (family, size) to avoid repeated fc-match/TTFont. fontTools is
    already a repo dep (used by tools/font_*). DO NOT hardcode pt constants per
    font — that is exactly what broke here.
  - Resulting inter-baseline gaps must all equal `linesp_pt` (within float eps)
    by construction, regardless of per-line font.

  Tests (test_headline_stack.py, unittest, no Scribus needed):
  - GREEN: a 3-line stack [Barlow, Vollkorn, Barlow] @ size 30, linesp 27pt →
    assert all consecutive `baseline = top + ascent` differences equal 27pt
    (compute baselines from the same metric reader; mock/stub fc-match+TTFont if
    the fonts aren't loadable in the test env, asserting the SOLVE relation
    rather than absolute numbers).
  - A uniform-font stack [Barlow, Barlow] reduces to even `Δy_mm == linesp_mm`.
  - Edge: single-line list returns one frame at `top_y_mm` unchanged.

  Do NOT regenerate templates in this task — only the helper + its unit tests.
  This is the metric-driven correction CONTEXT.md decision 1 mandates (fix at
  source, generalizes across all 12 templates).
  </action>
  <verify>
  <automated>cd /workspace/vorlagen && pytest tools/sla_lib/tests/test_headline_stack.py -q && python3 -m unittest discover tools/sla_lib/tests</automated>
  </verify>
  <done>
  - `headline_stack` helper exists in tools/sla_lib/builder and is importable
  - Inter-baseline gaps are even by construction for mixed-font stacks (test proves it)
  - Ascents are read from fc-matched TTFs via fontTools, cached; no hardcoded font constants
  - Both pytest and `python3 -m unittest discover` pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Regenerate stacked headlines in all 12 templates from the helper</name>
  <files>templates/flyer-a6-querformat-zweigeteilt/build.py, templates/flyer-a6-hochformat-gruenes-cover/build.py, templates/flyer-a6-hochformat-portraet/build.py, templates/flyer-a6-hochformat-quadrat-im-bild/build.py, templates/flyer-a6-hochformat-zweigeteilt/build.py, templates/flyer-a6-querformat-gruenes-cover/build.py, templates/flyer-a6-querformat-portraet/build.py, templates/flyer-a6-querformat-quadrat-im-bild/build.py, templates/falzflyer-z-falz-6-seitig-gruenes-cover/build.py, templates/falzflyer-z-falz-6-seitig-gruenes-cover-2/build.py, templates/falzflyer-z-falz-6-seitig-portraet/build.py, templates/falzflyer-z-falz-6-seitig-zweigeteiltes-cover/build.py</files>
  <action>
  Replace each template's hand-tuned stacked-headline frame group (the
  `X` / `X_l2` / `X_l3` single-line TextFrames) with a call to the Task-1
  `headline_stack` helper, so the `y_mm` are computed from real Barlow/Vollkorn
  ascents and gaps come out even.

  Per template:
  - Locate the stacked group(s). The canonical reference is
    `templates/flyer-a6-querformat-zweigeteilt/build.py:271-303` (`uaf8`,
    `uaf8_l2`, `uaf8_l3`). Use the SAME `top_y_mm` (the first line's existing
    `y_mm`, e.g. 58.6807), `x_mm`, `w_mm`, `h_mm`, per-line fonts/sizes/fcolor,
    and `anname` stem so only the SUBSEQUENT frame tops change.
  - Pick `linesp_pt` from the existing design leading for that headline (start
    from the current IDML/`LINESP` value, e.g. 27pt @ size 30). This is the
    Claude's-discretion empirical value — start at the existing leading, then in
    Task 5 measure pixel gaps and nudge `linesp_pt` until gaps look balanced and
    nothing sits too close to the line above.
  - The 4 falzflyers and the 8 A6 flyers all qualify (enumerated in RESEARCH).
    All-Barlow stacks (no Vollkorn line, e.g. `uaf8`/`uaf8_l3` both Barlow) ALSO
    drift because Barlow's ascent ≠ Gotham's — route them through the same helper;
    the correction simply reduces to a uniform `linesp_pt` when ascents are equal.
  - Check the `26-03-*` mirror templates (`templates/26-03-*`): if they are
    rendered/shipped (have a baseline.pdf + appear in render-gallery), apply the
    same fix; if superseded by the un-prefixed set, leave them and note the
    decision in the commit body. Do not guess — grep render-gallery / the gallery
    manifest to decide.
  - Do NOT touch the renderer or any PDF. Source only.

  After editing, rebuild each template's SLA via the normal build path and run
  the round-trip diff so structure stays intact (no frame dropped, anname stems
  preserved). Defer the visual gap-balance tuning to Task 5.
  </action>
  <verify>
  <automated>cd /workspace/vorlagen && bin/validate 2>&1 | tail -40</automated>
  </verify>
  <done>
  - All 12 templates emit their stacked headlines via `headline_stack` (no
    hand-frozen `y_mm` constants left for the stacked lines)
  - `bin/validate` sla_diff --strict passes for each changed template (round-trip intact)
  - anname stems (`X`, `X_l2`, `X_l3`) preserved so the audit can group them
  - 26-03-* mirrors handled (fixed if shipped, explicitly skipped with reason if superseded)
  </done>
</task>

<task type="auto">
  <name>Task 3: Re-justify zeitung-a4 leading + fix falzflyer social icons</name>
  <files>templates/zeitung-a4/build.py, tools/sla_lib/builder/primitives.py, templates/falzflyer-z-falz-6-seitig-gruenes-cover/build.py, templates/falzflyer-z-falz-6-seitig-gruenes-cover-2/build.py, templates/falzflyer-z-falz-6-seitig-portraet/build.py, templates/falzflyer-z-falz-6-seitig-zweigeteiltes-cover/build.py</files>
  <action>
  TWO source fixes (keep them as two separate commits).

  Problem 2 — zeitung-a4 leading (`templates/zeitung-a4/build.py:59`):
  - `Überschrift Dunkelgrün` is `fontsize=40`; c8bg0 cut `linesp` 35→28 against
    clipping, which made some headline pairs too tight. The frames are
    `h_mm ≈ 27.963 (≈79.3pt)`, ample for a single 40pt line (ascent+descent
    ≈ 40–48pt), so clipping came from leading interacting with multi-line content,
    not single headlines.
  - Set `linesp` into the SAFE WINDOW ≈ 30–32pt: ≥ ~1.0–1.05× the Barlow
    cap-stack (clears ascent+descent → no clipping) and < the old 35 (keeps pairs
    from touching). Start at 31pt; confirm in Task 5 via pixel gaps + text_render_audit.
  - `linesp_mode=0` stays. Do NOT change `h_mm` or `fontsize`.

  Problem 3 — falzflyer inline social icons (the 4 z-falz templates):
  - Each has small inline-icon `ImageFrame(inline_image_data=..., inline_image_ext='png')`
    (~17.82 × 15.6052 mm, e.g. gruenes-cover anname `u141` ~:193-200). RESEARCH
    gives two source-fixable causes: (a) Scribus 1.6.x renders white-on-transparent
    RGBA PNGs INVISIBLE under `SCALETYPE=1` + high downscale (primitives.py ~:861-869),
    (b) a broken/empty inline blob.
  - FIRST disambiguate: render one affected falzflyer (Task 0 render path) and
    inspect whether the icon frame is present in the SLA but blank in the PNG
    (→ cause a) vs. garbled/error (→ cause b).
  - Fix (a): ensure these inline-icon frames use `scale_type=0` (fit-to-frame).
    If the frames currently pass `scale_type=1`, change the build.py call to
    `scale_type=0`; if the default already is 0, confirm nothing overrides it.
    The `ImageFrame.scale_type` default is already 0 in primitives.py — do NOT
    weaken that default.
  - Fix (b) if needed: re-pack the icon PNG through `pack_inline_image(bytes, 'png')`
    (qCompress len-prefix+zlib — naive base64 → Z_DATA_ERROR), optionally
    compositing the white glyph onto an opaque/colored fill so it is not
    white-on-transparent. Never hand-roll the base64.
  - Confirm icons visible in the re-rendered preview and `pdffonts` unaffected
    (still Barlow + Vollkorn only).
  - Source only — no renderer patch.
  </action>
  <verify>
  <automated>cd /workspace/vorlagen && python3 tools/text_render_audit.py --slug zeitung-a4 2>&1 | tail -20 && pdffonts templates/falzflyer-z-falz-6-seitig-gruenes-cover/preview.pdf</automated>
  </verify>
  <done>
  - zeitung-a4 `Überschrift Dunkelgrün` leading in the 30–32pt window; text_render_audit clip-free
  - Each of the 4 falzflyers' social icons render visibly (scale_type=0 and/or re-packed PNG)
  - The root cause was disambiguated (cause a vs b) and noted in the commit body
  - pdffonts on changed templates still shows only Barlow + Vollkorn
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: headline_spacing_audit.py + wiring + unittest</name>
  <files>tools/headline_spacing_audit.py, bin/audit-alignment, tools/audit_alignment.py, bin/validate, tools/sla_lib/tests/test_headline_spacing_audit.py</files>
  <action>
  New automated audit that catches the regressions this issue fixes. Lives in
  `tools/headline_spacing_audit.py`, alongside the existing
  `tools/line_spacing_audit.py` (E2, deprecated), `line_spacing_full_audit.py`
  (E3), `line_spacing_pixel_audit.py` (E4, authoritative). REUSE E4's
  rasterise + ink-top scanner (import it or refactor a shared helper); do NOT
  reinvent it.

  CLI: `python3 tools/headline_spacing_audit.py --slug <slug> [--templates-dir templates] [--out-yaml PATH] [--static-only]`
  Mirror the `tools/audit_alignment.py` / `bin/audit-alignment` shim pattern.

  What it does:
  - Read SLA geometry via `sla_lib.reader.SLADocument` — `page_objects()` /
    `find_by_anname()` — and GROUP frames by stacked-headline stem: a stem `X`
    plus `X_l2`, `X_l3`, … (the naming Task 1/2 preserve). XPOS/YPOS/HEIGHT/WIDTH
    are PAGEOBJECT attributes.
  - For each stack compute the inter-line gaps two ways:
      (i) STATIC (no render, CI-safe): expected baselines from FLOP=1 + fontTools
          ascent (reuse the Task-1 metric reader) → gap_k.
      (ii) PIXEL (local, truth): ink-top per frame from `preview.pdf` via the E4
          rasteriser → gap_k.
    `--static-only` runs (i) alone so CI (which does not render) can gate.
  - FLAGS (a violation → emit YAML + non-zero exit):
      * too tight: any gap < `min_ratio × fontsize_pt` (min_ratio default 0.85).
      * uneven: `(max_gap - min_gap) / mean_gap > 0.15` within one stack.
      * top-gap collapse (the "dreizeilige" signature): top gap < 0.9 × mean of
        the other gaps.
  - MUST NOT false-positive on intentionally tight SINGLE-FONT headlines that are
    nonetheless EVEN: the uneven + top-collapse checks are relative (ratio-based),
    so a uniformly-tight even stack passes; only the absolute `min_ratio × fontsize`
    floor catches genuinely-too-tight. Set `min_ratio` from the CORRECTED
    Task-2/3 baselines so passing templates set the floor (derive the number after
    Task 5, then lock it). Document the chosen thresholds in SKILL_FINDINGS.md (or
    the repo's audit-findings doc).

  Wiring (see Call-site enumeration above — grep first, then edit):
  - Add the audit to the `bin/audit-alignment` rollup (or `tools/audit_alignment.py`
    if the shim delegates there).
  - Invoke it from the `bin/validate` chain (the `--static-only` mode, so CI stays
    render-free and the stale-previews gate is unaffected).

  TDD — write `tools/sla_lib/tests/test_headline_spacing_audit.py` (unittest,
  alongside `test_audit_alignment.py`) FIRST, using synthetic SLA fixtures:
  - an EVEN 3-line stack → audit passes (exit 0, no violations).
  - a stack with a COLLAPSED top gap (the "dreizeilige" reproduction) → audit
    flags top-gap-collapse (exit non-zero).
  - a uniformly-tight-but-EVEN single-font stack above the floor → passes (proves
    no false positive on intentional tightness).
  Build fixtures with the Task-1 helper / SLADocument so they are self-contained
  (no Scribus render needed for the static path).
  </action>
  <verify>
  <automated>cd /workspace/vorlagen && pytest tools/sla_lib/tests/test_headline_spacing_audit.py -q && python3 -m unittest discover tools/sla_lib/tests && python3 tools/headline_spacing_audit.py --slug flyer-a6-querformat-zweigeteilt --static-only</automated>
  </verify>
  <done>
  - `tools/headline_spacing_audit.py` exists with `--slug` + `--static-only`,
    reusing the E4 ink-top scanner and the Task-1 metric reader
  - Flags too-tight / uneven / top-gap-collapse; emits YAML + non-zero exit on violation
  - Wired into bin/audit-alignment (or tools/audit_alignment.py) AND bin/validate (static mode)
  - No false positive on a uniformly-tight even single-font stack (test proves it)
  - Both pytest and `python3 -m unittest discover` pass; thresholds documented
  </done>
</task>

<task type="auto">
  <name>Task 5: Re-render affected templates + measure + tune linesp (NO baseline promotion)</name>
  <files>(re-render outputs + iterative tuning of templates/*/build.py linesp_pt and zeitung-a4 linesp from Tasks 2-3)</files>
  <action>
  Render every changed template headless (xvfb Scribus) and measure the corrected
  gaps, iterating `linesp_pt` (stacked headlines) and the zeitung leading until
  gaps are balanced. This produces fresh preview.pdf + PNGs but DOES NOT promote
  baselines — promotion is gated on the Task-6 human visual review (mirroring c8bg0).

  Steps:
  - Re-render: `bin/render-gallery` (or the single-template render path) for all
    12 stacked-headline templates + zeitung-a4 + the 4 falzflyers → preview.pdf + PNGs.
  - Measure pixel gaps per stacked headline:
    `python3 tools/line_spacing_pixel_audit.py --slug <slug> --templates-dir templates --out-yaml build/validation/<slug>/lsp.yml`
    and `python3 tools/headline_spacing_audit.py --slug <slug>` (the NEW audit).
  - Tune: if a stack still shows top-gap-collapse or uneven gaps, adjust that
    template's `linesp_pt` (Task 2) / zeitung `linesp` (Task 3) and re-render.
    The metric helper guarantees EVEN gaps for a given `linesp_pt`, so tuning is
    only choosing the target leading per headline, not re-deriving per-line `y_mm`.
  - Gate each render: `python3 tools/text_render_audit.py --slug <slug>` clip-free,
    `pdffonts templates/<slug>/preview.pdf` shows ONLY Barlow + Vollkorn.
  - Confirm the 4 falzflyer social icons are now VISIBLE in the rendered PNGs.
  - Lock the audit `min_ratio` floor (Task 4) from these corrected gaps so the
    passing templates set the threshold; re-run the audit to confirm all pass.

  Do NOT freeze baseline.pdf, do NOT touch diff.yml/TOLERANCES.yml here. Leave
  preview.pdf/PNGs fresh for the human to review in Task 6.
  </action>
  <verify>
  <automated>cd /workspace/vorlagen && for s in flyer-a6-querformat-zweigeteilt zeitung-a4 falzflyer-z-falz-6-seitig-gruenes-cover; do python3 tools/text_render_audit.py --slug $s 2>&1 | tail -3; pdffonts templates/$s/preview.pdf; python3 tools/headline_spacing_audit.py --slug $s; done</automated>
  </verify>
  <done>
  - All changed templates re-rendered; preview.pdf + PNGs fresh
  - headline_spacing_audit passes on every changed stacked-headline template (even, no top collapse)
  - text_render_audit clip-free; pdffonts only Barlow + Vollkorn on every changed template
  - Falzflyer social icons visible in the rendered PNGs
  - Audit min_ratio floor locked from the corrected gaps; NO baselines promoted yet
  </done>
</task>

<task type="checkpoint:human-verify">
  <name>Task 6: Human visual sign-off, then promote baselines + final gates</name>
  <files>(baseline.pdf / preview PNGs / diff.yml / TOLERANCES.yml / staleness metadata for each changed template)</files>
  <action>
  CHECKPOINT — the main agent performs a FOCUSED visual review of headline spacing
  across ALL affected templates with multiple comparisons BEFORE any baseline is
  promoted (this mirrors the c8bg0 workflow and is required by CONTEXT.md
  decision 5). Baselines are promoted ONLY after sign-off.

  Visual review (must be documented — multiple comparisons):
  - For each of the 12 stacked-headline templates: view the rendered headline and
    confirm gaps are even and NOTHING sits too close to the line above (the
    "dreizeilige" Vollkorn line in particular). Compare top-vs-bottom gap visually.
  - zeitung-a4: confirm headlines are not too tight and not clipped.
  - 4 falzflyers: confirm social icons render correctly (right icon, aligned, visible).
  - If any spacing still looks off, return to Task 5, adjust `linesp_pt`, re-render.

  After sign-off — promote and run the full gate set:
  - Freeze each changed template's preview.pdf → baseline.pdf; update
    diff.yml / TOLERANCES.yml as the repo's promote path requires; refresh preview
    PNGs + staleness metadata so `bin/check-stale-previews` stays green.
  - Run the full gate chain: `bin/validate` (sla_diff --strict + visual_diff),
    `bin/audit-alignment` (incl. the new headline audit), `bin/check-stale-previews`,
    `python3 tools/text_render_audit.py` (clip-free), `pdffonts` (Barlow + Vollkorn
    only) on every changed template, and the full unittest suite
    (`python3 -m unittest discover tools/sla_lib/tests` + `pytest`).
  - Commit baselines + metadata with the `bx4d8:` prefix, no tool attribution.
  </action>
  <verify>
  <automated>cd /workspace/vorlagen && bin/validate && bin/audit-alignment && bin/check-stale-previews && pytest tools/sla_lib/tests -q && python3 -m unittest discover tools/sla_lib/tests</automated>
  </verify>
  <done>
  - Human visual sign-off recorded (multiple comparisons documented) for stacked
    headlines, zeitung-a4, and falzflyer icons
  - New baselines promoted for every changed template; diff.yml/TOLERANCES.yml +
    staleness metadata updated
  - bin/validate + bin/audit-alignment + bin/check-stale-previews green; visual_diff passes
  - text_render_audit clip-free and pdffonts shows only Barlow + Vollkorn on all changed templates
  - Full unittest + pytest suites pass
  </done>
</task>

</tasks>

<verification>
After all tasks, the full gate set (run from /workspace/vorlagen):
- `pytest tools/sla_lib/tests -q && python3 -m unittest discover tools/sla_lib/tests` — unit tests (both runners)
- `bin/validate` — sla_diff --strict + visual_diff per template, with check-fontsizes + check-stale-previews preflight
- `bin/audit-alignment` — alignment rollup incl. the new headline_spacing_audit
- `bin/check-stale-previews` — staleness gate green (baselines/previews committed)
- `python3 tools/text_render_audit.py --slug <each changed slug>` — clip-free
- `pdffonts templates/<each changed slug>/preview.pdf` — ONLY Barlow + Vollkorn, no fallback
- `python3 tools/headline_spacing_audit.py --slug <each changed slug>` — even gaps, no top collapse
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria:
- Multi-part headlines have even, balanced line spacing (nothing too close to the
  line above); the "dreizeilige" case fixed — verified visually across all affected
  templates (multiple comparisons documented) [Tasks 1,2,5,6]
- zeitung-a4 Barlow headlines have clean spacing (not too tight, not clipped) [Tasks 3,5,6]
- Falzflyer social icons display correctly in all affected templates [Tasks 3,5,6]
- Automated headline-spacing audit exists (in `tools/` + the `bin/validate` chain),
  with tests; catches too-tight / uneven headline spacing without false-positiving
  on intentionally tight even single-font headlines [Task 4]
- New baselines produced; visual_diff / tests green; `pdffonts` only Barlow +
  Vollkorn; no clipping (`text_render_audit` ok) [Task 6]
- No tool attribution in commits/code [all tasks — commit_format]
</success_criteria>
