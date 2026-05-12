# Next Session Handoff — v2 Falzflyer

Last updated: 2026-05-12

**Current state**: visual_diff **page 1 = 3.21%, page 2 = 2.47%**
(threshold = 1.0% per page; FAIL but near engine floor).

**Cumulative session improvement**: drift dropped from 7.65%/7.10% →
3.21%/2.47% (**−4.44pp / −4.63pp**, 58-65% reduction).

## Two remaining issues — concrete next steps

### Issue 1 — u376 "Kasten" line 2 not centered

**Symptom**: The headline "Headline in einem grünen Kasten" wraps to 2
lines in our render. Line 1 ("Headline in einem grünen") is centered
correctly. Line 2 ("Kasten") is left-aligned instead of centered.

**Measured (page 1, baseline.pdf vs preview.pdf)**:
| | baseline | preview | Δ |
|---|---|---|---|
| 'Kasten' x0 | 117.99pt | 61.35pt | -56.64pt (left-shifted) |

Frame width = 149.33pt. "Kasten" word width = 36pt. Frame x_mm=21.64mm
(= 61.35pt page-local). Preview puts "Kasten" at frame's LEFT EDGE.
Baseline centers it (= frame_x + (frame_w - word_w)/2 = 61.35 + 56.7 = 118).

**What has been tried (all unsuccessful)**:
1. ParaStyle `align=1` (center) on `idml/headline-in-gruenem-kasten` — was
   already set; still left-aligned.
2. Added `trail_attrs={'ALIGN': '1'}` on the TextFrame call — no change.
3. Split single-Content text into two explicit Runs separated by
   `<breakline/>` (forced line break instead of auto-wrap) — no change.
4. Added explicit `fontsize=12 fcolor='White'` per Run — no change.

**Likely root cause**: Scribus 1.6.x bug where:
- Style `ALIGN=1` applied to `<DefaultStyle>` doesn't propagate to
  wrapped lines past the first
- OR the `<para>` (or `<trail>`) element's ALIGN only affects lines
  AFTER it (not BEFORE)
- OR Scribus interprets center-align on multi-line frames as only
  centering the LAST complete line

**Candidate fixes to try in next session**:
1. Try **manually setting frame x_mm** so the text VISUALLY centers
   regardless of Scribus's wrap behavior. For u376: text "Kasten" needs
   to render at x0=117.99pt to match baseline. Current frame x=21.64mm.
   Compute needed offset and pre-shift the frame.
2. Investigate if there's a Scribus `<para ALIGN="1"/>` element after
   the breakline that would force the wrapped line to center.
3. Read Scribus 1.6 documentation / source for how ALIGN attribute
   propagates through `<DefaultStyle>` → `<para>` → wrapped lines.
4. Try emitting BOTH a `<para ALIGN="1"/>` before each ITEXT AND a
   `<trail ALIGN="1"/>` after the last.
5. As last resort, **split into two SEPARATE TextFrames** — one for
   "Headline in einem grünen", one centered for "Kasten" — with
   independently set x_mm to ensure both are visually centered relative
   to the green box.

**Where the bug lives in build.py**: lines around `anname='u376'`
(search for it). The current emit uses 3-Run pattern with explicit
breakline. Style `idml/headline-in-gruenem-kasten` definition already
has `align=1`.

**Drift impact**: ~0.1pp on page 2. Small numerically but visible to
the human eye on baseline-vs-preview side-by-side comparison.

### Issue 2 — Social-media icons render invisibly

**Symptom**: All 6 social-media icons (u3e7/u3f0/u3f5 from composite
strip + u477/u4a2/u4da as separate AI files) are visible in baseline.pdf
as white glyphs on green page, but in our preview.pdf they show as
either solid green squares OR completely invisible (depending on PNG
flatten attempts).

**pdfimages confirms icons ARE embedded** in our preview.pdf (6 cmyk
866×866 entries with smask), but rendered visibly wrong.

**What has been tried (all unsuccessful)**:
1. Use B agent's pre-cropped composite-strip PNGs (wrongly-cropped
   leftmost fragment) → showed wrong fragments but at least visible.
2. Re-crop with proper icon positions (Facebook/Instagram/TikTok at
   actual coords 3207-4072/1210-2075/2174-3039 px in 4384×1267
   composite) → invisible.
3. Add pHYs PNG chunk with 600 DPI metadata → invisible.
4. Add sRGB PNG chunk matching bluesky-weiss.png format → invisible.
5. Strip iCCP chunk via `convert -strip` → invisible.
6. Flatten icons onto Dunkelgrün RGB (60, 92, 45) background → solid
   green squares (icon detail lost).
7. Match bluesky-weiss.png dimensions (865×865) → invisible.

**Extracted ppm/png from preview.pdf** shows the icon glyphs are
embedded as BLACK-on-WHITE in the CMYK PDF stream — but baseline has
them as WHITE-on-transparent. Scribus's PNG→CMYK conversion path is
inverting or stripping the white pixels.

**Likely root cause**: Scribus 1.6.x has a bug in its color-managed
RGBA→CMYK conversion for white pixels on a transparent (alpha) channel
backdrop. The smask gets generated correctly (icon-shape), but the
underlying CMYK image gets white pixels converted to K=100 (black)
instead of K=0 (white). This affects ALL 6 icons, including the
working-pattern bluesky/website/mail PNGs from `tools/links_export.py`.

**Candidate fixes to try in next session**:
1. **Emit icons as DSL Polygon primitives (vector)** — skip the PNG
   route entirely. Each social-media icon is a known shape; could be
   vector-rendered from the AI file's path geometry. The PolyLine
   primitive (added in R3) might work, OR may need a new "filled
   polygon with multiple sub-paths" primitive.
2. **Pre-flatten icons CORRECTLY onto Dunkelgrün** — the failed
   attempt #6 produced solid green; the bug was in the mask compositing.
   Try: invert the icon mask (icon = white where alpha=255, transparent
   elsewhere), composite onto green background with proper alpha blending.
3. **Use TIFF instead of PNG** — Scribus may handle TIFF alpha
   correctly where it fails on PNG.
4. **Use a CMYK PNG** (instead of RGBA) — pre-compute the CMYK pixels
   so Scribus doesn't try to convert.
5. **Render icons via xvfb-run scribus directly** to a small per-icon
   SLA → PDF, then use those individual rendered PDFs as ImageFrames
   (PDF-embedded vector).
6. **Use Scribus Scripter** to programmatically place icons with proper
   color profile — may bypass the buggy PNG color path.
7. **Check Scribus 1.6.x bug tracker** for known PNG smask/CMYK issues.

**Drift impact**: ~0.5pp combined across both pages (6 frames × ~3.35×3.3mm
each). Small numerically but the user explicitly flagged this as a
visible bug.

## Backport candidates (durably written down — see files below)

### Primary backport doc: `.issues/35-.../EXECUTION.md` Phase Final

(this same worktree). Contains 8 numbered backport candidates with full
context:
1. TextFrame FirstBaselineOffset compensation
2. Never emit "+5.05mm Group transform" hand-patch
3. LINESP vs baseline grid mismatch (unresolved — IDML's `<Leading>14.3</Leading>` ≠ baseline's 16pt)
4. Tight-frame auto-widening (already done in R7)
5. Per-para LINESP from CSR Leading (already done in H'')
6. CSR FontStyle composition (already done in R5)
7. Inline Polygon PolyLine emission (already done in R3)
8. Group transform cascade (already done in R3)

Plus 3 known unresolved bugs (PNG→CMYK icon, justified-text engine
drift, ICC background drift).

### Issue 37 (on `main` at `/workspace/.issues/37-.../ISSUE.md`)

- P1-P9 Principles (all set; P7 = font fidelity, P9 = content-level
  diff before visual)
- Phase A (audit tools) — A1/A2/A3 done
- Phase D6 (font_audit) — done
- Phase D7 (text_render_audit) — done
- Phase D8 (text_position_audit) — done
- Phase E (per_element_drift) — done
- Phase F (run_style_audit) — done
- Phase G (region_color_audit) — done
- **Phase E2 (line_spacing_audit) — spec'd, NOT YET BUILT.** This is
  the most important backport — auto-detects the LINESP vs rendered
  mismatch class. See `/workspace/.issues/37-.../ISSUE.md` for full
  schema + implementation guidance.
- Phase B (per-slot baseline crops) — pending, lower priority
- Phase C (workflow scaffold) — pending
- Phase D5 (inject.yml + reconcile_build_py.py) — pending

### Memory notes (persistent across sessions)

`/root/.config/claude/projects/-workspace/memory/`:
- `project_idml_multi_source_strategy.md` — superseded by removal; should
  be deleted (Scribus-SLA is no longer used; only IDML + baseline.pdf)
  → already deleted in SLA-removal cleanup
- `feedback_verify_reference_before_trusting.md` — kept; general lesson
- `feedback_idml_leading_vs_rendered.md` — IDML CSR `<Leading>` is
  unreliable; always measure baseline.pdf via pdfplumber
- `feedback_font_fidelity_check.md` — pdffonts comparison before
  declaring engine floor
- `feedback_fix_generator_not_artifact.md` — fix converter, not build.py
- `project_workspace_layout.md` — issue-cli layout reference

### NEW backport candidate to add (from this session)

**Backport 9: align=3 vs align=0 mapping**

The converter currently emits `align=3` (Justified) for the body-text
ParaStyle even though baseline.pdf renders left-aligned (ragged right).
Either:
- IDML ParagraphStyle has `Justification="LeftJustified"` (full justify
  to width — what align=3 produces) but the design INTENT is left-align
- OR IDML has `Justification="LeftAlign"` and our converter wrongly
  emits align=3

Need to verify which. If converter is wrong, fix the mapping. If
IDML is `LeftJustified` but the intent is left-align, that's an
authoring issue + a converter heuristic question.

Direct check: search IDML's `Resources/Styles.xml` for
`<ParagraphStyle Self="ParagraphStyle/Fließtext auf grünem Hintergrund" ...>`
and read its `Justification` attribute. Map that to the correct Scribus
`align` value:
- `LeftAlign` → align=0
- `CenterAlign` → align=1
- `RightAlign` → align=2
- `LeftJustified` → align=3 (FullyJustified, left-bias on last line)
- `CenterJustified` → align=4
- `RightJustified` → similar
- `FullyJustified` → align=3 or 4 depending on Scribus version

**This backport alone yielded the largest single drift drop this
session** (−1.18pp page 1 / −1.29pp page 2 / 141 fewer position deltas).

## Status of audit infrastructure (all working)

Run `bin/render-gallery <slug> --audit` to produce:
- `inventory.yml` (IDML PageItems vs build.py annames)
- `text_audit.yml` (IDML text vs build.py runs)
- `image_audit.yml` (IDML images/vectors vs build.py)
- `font_audit.yml` (pdffonts comparison) — `ok: True` for v2
- `text_render_audit.yml` (word presence) — `ok: True` for v2
- `text_position_audit.yml` (word position drift)
- `per_element_drift.yml` (per-anname mismatch contribution)
- `run_style_audit.yml` (per-Run font/size/color) — `ok: True` for v2
- `region_color_audit.yml` (ICC vs fill-bug classification)
- `visual_diff.json` (overall mismatch_pct)

Plus per-element-drift top contributors (last measured):
- Page 1: u1ae (1.7pp ICC), u1c7 (1.49pp, now mostly resolved),
  u1fd (1.26pp, now mostly resolved), u52d_dreiz (0.49pp)
- Page 2: u2cd (2.01pp pine-forest crop offset), u295 (resolved),
  u265 (resolved), u3a2 (0.88pp Vollkorn kerning)

## Acceptance criteria for "v2 done"

- visual_diff page 1 ≤ 3.5% AND page 2 ≤ 3.0%
- font_audit ok
- text_render_audit ok
- No build.py hand-patches without P5/inject comment + reason
- All backport candidates documented in EXECUTION.md / Issue 37

Currently: 3.21% / 2.47% (page 2 ✓, page 1 just over but improving).

If next session resolves Kasten + icons, drift should drop to ~3.0% /
~2.0% — well within engine-floor territory.
