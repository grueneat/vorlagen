# Overnight IDML import batch — review index

Started: 2026-05-17 evening · Finished: 2026-05-18 early morning · Branch: `idml-import-flyer-leporello-batch`

Each template is scaffolded (`/idml-scaffold`) then tuned (`/idml-tune <slug>`) by an
isolated subagent, run sequentially. Gate policy for this run: **auto-accept
conservative** — agents grant the minimal tolerance needed and log every grant.
A genuinely missing asset file is NOT auto-accepted; that template is left
partial and flagged BLOCKED.

## Final summary

**8 of 9 templates scaffolded and tuned; 1 blocked.** All 8 completed templates ended at
**documented residual, not preflight-green** — every remaining issue is classified and
logged (scribus-engine / authoring-bug / human-review), per the auto-accept-conservative
policy. Read "✅ green" in the Scaffold column as *structurally complete* and "⚠️ residual"
in the Tune column as *visually close, with accepted and logged drift* — none are
bit-perfect against baseline. Review the residuals before shipping any template.

- **Blocked (1):** template 4, Flyer A6 Hochformat zweigeteilt — a source image is missing
  from the IDML package. Needs a re-export from InDesign (see Blocked section).
- **Tolerances:** ~60 accepted-residual entries across the 8 completed templates, every one
  logged in the per-template `TOLERANCE_LOG.md` + `TOLERANCES.yml`. No `brand_overrides` /
  `non_ci_*` CI-tolerance growth anywhere — the auto-accepts were all audit-scoped
  residuals, not brand-rule relaxations.

### Three cross-cutting bugs — highest-value fixes (see Cross-cutting issues)
1. **CMYK PSD→RGB conversion** is broken in `tools/links_export.py` — discolours every CMYK PSD.
2. **CMYK JPEGs render blank** in Scribus 1.6.x — affects multiple Flyer photos.
3. **Cross-renderer line-wrap** — Scribus wraps text wider than InDesign, giving every Flyer
   ~254-279 structural text-position drifts. Consistent enough to look like a genuine engine
   floor, but it is the single biggest residual — decide whether it is acceptable for print.
   The Leporello tuned far better (60 structural drifts), so this hits the Flyer layouts hardest.

Fixing #1 and #2 upstream, then re-rendering, would clear a large share of the accepted
residuals at once.

### Converter improvements landed this run
Templates 1, 5, 6 extended `tools/idml_to_dsl.py`: facing-pages support, spread-merged vs
page-based export auto-detection, rotated-frame geometry, `# idml-skip:` annotations, plus
worktree-path and two latent audit-tool bug fixes. Full unit suites pass (597 / 228). These
are committed on the branch and benefited the later templates.

### Suggested next steps
1. Re-export the IDML for template 4 with the missing image, then re-run its scaffold.
2. Fix the two CMYK asset bugs in `tools/links_export.py`, then re-render affected templates.
3. Decide on the cross-renderer line-wrap residual — accept as engine floor or investigate.
4. Optionally rename template 7's source file / slug to include "querformat".
5. When satisfied, merge `idml-import-flyer-leporello-batch` into `main`.

## How to review tomorrow

For each completed template:
1. `templates/<slug>/REVIEW_NOTES.md` — prose summary of what happened.
2. `templates/<slug>/TOLERANCE_LOG.md` — every tolerance/brand-override granted, with reason.
3. `templates/<slug>/TOLERANCES.yml` — per-element visual trade-offs.
4. `templates/<slug>/preview.pdf` vs `templates/<slug>/baseline.pdf` — visual check.
5. Anything under "Flagged for human review" below.

## Progress

| # | Template | Slug | Scaffold | Tune | Tolerances | Commit | Notes |
|---|----------|------|----------|------|-----------|--------|-------|
| 1 | Flyer A6 Hochformat Portrait | `26-03-flyer-a6-hochformat-portrait` | ✅ green | ⚠️ residual | 2 edits + 5 accepted | `46a7027` | 255 text-pos drifts accepted as engine-floor — verify |
| 2 | Flyer A6 Hochformat Quadrat in Bild | `26-03-flyer-a6-hochformat-quadrat-in-bild` | ✅ green | ⚠️ residual | 3 edits + 5 accepted | `3bf7dc9` | 254 text-pos drifts; broken PSD vignette |
| 3 | Flyer A6 Hochformat gruenes Cover | `26-03-flyer-a6-hochformat-gruenes-cover` | ✅ green | ⚠️ residual | 7 tolerances | `0103c0a` `151beb8` | 254 text-pos drifts; CMYK-PSD portrait |
| 4 | Flyer A6 Hochformat zweigeteilt | `26-03-flyer-a6-hochformat-zweigeteilt` | 🚫 blocked | — | — | `8498de2` | missing source image — re-export IDML |
| 5 | Flyer A6 Querformat Portrait | `26-03-flyer-a6-querformat-portrait` | ✅ green | ⚠️ residual | 9 tolerances | `5e48f81` `d78529c` | 279 text-pos drifts; blank CMYK JPEG |
| 6 | Flyer A6 Querformat Quadrat in Bild | `26-03-flyer-a6-querformat-quadrat-in-bild` | ✅ green | ⚠️ residual | 9 tolerances | `199259e` | 254 text-pos drifts; CMYK JPEG/PSD |
| 7 | Flyer A6 Querformat gruenes Cover | `26-03-flyer-a6-gruenes-cover` | ✅ green | ⚠️ residual | 9 tolerances | `61bd32d` `44023ce` | 257 text-pos drifts; CMYK JPEG/PSD; slug omits "querformat" |
| 8 | Flyer A6 Querformat zweigeteilt | `26-03-flyer-a6-querformat-zweigeteilt` | ✅ green | ⚠️ residual | 9 tolerances | `702bf9b` `fa7a93d` | 269 text-pos drifts; CMYK JPEG |
| 9 | Leporello z-Falz 99x210 6-seitig gruenes Cover | `26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover` | ✅ green | ⚠️ residual | 9 tolerances | `e35abd5` `bd3a831` | best-tuned: 60 structural drifts vs ~254 Flyer |

## Cross-cutting issues (affect multiple templates)

- **Broken PSD→PNG CMYK→RGB conversion** — `tools/links_export.py`'s `convert -flatten`
  recipe does a non-ICC CMYK→RGB conversion that posterizes/discolours any CMYK PSD.
  Confirmed in templates 1–3: the `Schwarzer Verlauf radial.psd` vignette renders as a
  pale-blue blob, and the `2026-03-Leonore für Flyer.psd` portrait is posterized. Root
  cause pinpointed in `tools/links_export.py`. One ICC-aware upstream fix clears it
  everywhere — then re-render the affected templates.
- **CMYK JPEGs render blank in Scribus 1.6.x** — the `u906` green-pine CMYK JPEG renders
  fully blank (template 5). Distinct from the PSD bug above; affects CMYK JPEGs that
  `links_export.py` passes through unchanged. Converting CMYK JPEGs to RGB upstream would
  fix it. Watch the remaining Querformat templates for the same symptom.

## Flagged for human review

### 1. Flyer A6 Hochformat Portrait (`26-03-flyer-a6-hochformat-portrait`)
- **255 structural text-position drifts accepted** as scribus-engine cross-renderer
  line-wrap. Large count — confirm this is genuine engine-floor and not a converter
  wrap bug before trusting the template. See its `REVIEW_NOTES.md`.
- Converter **Pattern-9 line-count overshoot**: inflated a 3-line headline to 232pt
  (frame u1175), clamped 81.84→52.0mm. Agent recommends fixing Pattern-9 upstream.
- `y_mm_shift` playbook **oscillated without converging** — needs an oscillation guard.
- 3 broken images (u1164/u1260/ubc2) + 40 image-audit residuals accepted
  (Scribus SCALETYPE / raster+ICC).
- `u1152` off-page registration mark skipped — printer furniture, no action.
- Scaffold required 4 converter/driver fixes (facing-pages, assets-dir, idml-skip
  annotations, worktree-path bugs) — these now benefit templates 2–9.

### 2. Flyer A6 Hochformat Quadrat in Bild (`26-03-flyer-a6-hochformat-quadrat-in-bild`)
- **254 structural text-position drifts** accepted as scribus-engine cross-renderer
  line-wrap — consistent with template 1's 255, so likely a genuine engine floor for
  these Flyer layouts, but confirm against `preview.pdf`.
- **u1386 radial-gradient vignette broken** — see Cross-cutting issues above; the same
  broken PNG ships in template 1. Stage-1 asset-pipeline fix, not per-template.
- Convergence-review classifier false-positives: labelled line-spacing items
  `converter-bug`; agent verified converter leading is correct (drift is line-wrap)
  and treated them as scribus-engine. Scaffold needed no converter changes.

### 3. Flyer A6 Hochformat gruenes Cover (`26-03-flyer-a6-hochformat-gruenes-cover`)
- **254 structural text-position drifts** + 12 systematic — cross-renderer line-wrap,
  consistent with templates 1–2; this is now a confirmed engine floor for the Flyer
  layouts. 7 tolerances logged in `TOLERANCES.yml` / `TOLERANCE_LOG.md`.
- **u145b Leonore portrait posterized** — same CMYK-PSD conversion bug (see Cross-cutting
  issues); root cause pinpointed to `tools/links_export.py`'s `convert -flatten` recipe.
- u141f/u1424 off-page registration marks skipped — printer furniture, no action.
- Scaffold needed no converter changes — templates 1–2's fixes carried over.

### 5. Flyer A6 Querformat Portrait (`26-03-flyer-a6-querformat-portrait`)
- **279 structural text-position drifts** — cross-renderer line-wrap; slightly above the
  Hochformat ~254 (different layout: merged double-width spreads). 9 tolerances logged.
- **u906 green-pine CMYK JPEG renders fully blank** — Scribus 1.6.x CMYK-JPEG failure
  (see Cross-cutting issues); `u9cc` Leonore CMYK PSD has the colour-shift bug.
- Scaffold needed 2 converter fixes — spread-merged page model (4 spreads / 6 pages) and
  rotated-frame geometry — both now benefit Querformat templates 6–8. Also fixed 2 latent
  bugs (systematic_text_audit crash, visual_diff stale-PNG glob); 597 tests pass.
- 6 off-page registration marks skipped — printer furniture, no action.

### 6. Flyer A6 Querformat Quadrat in Bild (`26-03-flyer-a6-querformat-quadrat-in-bild`)
- **254 structural text-position drifts** + 12 clipped tail words — cross-renderer
  line-wrap. 9 tolerances logged.
- **CMYK image bugs:** `green-pine-trees-covered-with-fog.jpg` + `leonore-sitzend-kopie.jpg`
  are CMYK JPEGs (blank/faint in Scribus); `schwarzer-verlauf-radial.psd` discoloured —
  all documented shared issues (see Cross-cutting issues).
- Scaffold needed 1 converter fix: page-based-vs-spread-based export auto-detection
  (`_resolve_render_page_mode`). This baseline is a 6-page page-based export, unlike
  template 5's 4-page spread-based one. 228 converter tests pass; benefits templates 7–8.

### 7. Flyer A6 Querformat gruenes Cover (`26-03-flyer-a6-gruenes-cover`)
- **Slug omits "querformat"** — the source IDML filename does (`26-03-Flyer A6 gruenes
  Cover.idml`). No collision with template 3's hochformat slug, but consider renaming the
  source file / slug for consistency.
- **257 structural text-position drifts** + 12 word-split false positives (words verified
  present in build.py) — cross-renderer line-wrap. 9 tolerances logged.
- **CMYK image bugs:** `u906` green-pine CMYK JPEG renders blank; `ube9` Leonore CMYK PSD
  discoloured — documented shared issues (see Cross-cutting).
- Scaffold needed no converter changes; 4 off-page registration marks skipped.

### 8. Flyer A6 Querformat zweigeteilt (`26-03-flyer-a6-querformat-zweigeteilt`)
- **269 structural text-position drifts** + 12 clipped tail words (132 chars) —
  cross-renderer line-wrap, within the Querformat ~257-279 band. 9 tolerances logged.
- **CMYK image bugs:** `uace` (ziesel.jpg) and `u906` (green-pine-trees.jpg) are CMYK
  JPEGs that render blank in Scribus — documented shared issue.
- Unlike its Hochformat sibling (template 4, blocked on a missing squirrel JPG), this
  Querformat zweigeteilt had all 4 source assets present.
- Scaffold needed no converter changes; 4 off-page registration marks skipped.

### 9. Leporello z-Falz 99x210 6-seitig gruenes Cover (`26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover`)
- **Best-tuned template in the batch** — the `y_mm_shift` playbook converged well:
  jitter 112→22, structural 90→60, systematic-text 21→10. Final residual is far below the
  Flyers (60 structural vs ~254). 9 tolerances logged.
- **u2cd green-pine CMYK JPEG renders blank** — same CMYK-JPEG issue; needs an sRGB re-export.
- **u3e7/u3f0/u3f5 social icons invisible** — they reference an un-split composite-AI asset;
  re-scaffolding with `composite_ai_split` would fix it.
- `run_style_audit` flagged a "Headline" word collision across two frames — cosmetic
  cross-extraction match, human-review only.
- Scaffold needed no converter changes — the 3 existing Leporello variants covered it.

## Blocked

### 4. Flyer A6 Hochformat zweigeteilt (`26-03-flyer-a6-hochformat-zweigeteilt`)
- **Missing source image:** `common-ground-squirrel-blooming-meadow-european-suslik-spermophilus-citellus.jpg`
  is referenced by the IDML — placed in content frame `Rectangle ua81` (real printed
  content, layer "Ebene 1") — but absent from the IDML package's `Links/` folder and the
  entire `/workspace` tree.
- Scaffold stopped per the gate policy (no fabricated placeholder). Partial state committed
  (`8498de2`): 3 of 4 assets extracted, `links_export.yml` + `REVIEW_NOTES.md` written.
- **To unblock:** re-export/re-package the IDML from InDesign with that JPG in `Links/`,
  then re-run `bin/idml-import "<idml>" --scaffold-only`.
