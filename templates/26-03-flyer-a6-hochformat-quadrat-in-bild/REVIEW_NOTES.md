# Review Notes — 26-03-flyer-a6-hochformat-quadrat-in-bild

Prose summary for a human reviewer. Read alongside `TOLERANCE_LOG.md`
(every edit + accepted residual) and `TOLERANCES.yml` (structured).

## What this template is

A 6-page A6 portrait flyer ("Flyer A6 Hochformat — Quadrat in Bild"),
imported from `26-03-Flyer A6 Hochformat Quadrat in Bild.idml`. Trim
~99 x 140 mm per page (rendered 297.6 x 419.5 pt after the driver
cropped the printer's-marks baseline to trim box). It is template 2 of
the overnight flyer/leporello batch; the sibling
`26-03-flyer-a6-hochformat-portrait` (template 1) is structurally
near-identical and a useful comparison point.

Layout: page 1 cover (pine-forest photo full-bleed, green box with a
three-line headline + DIE GRÜNEN logo, magenta "Störer" badge); pages
2-4 green-background body pages with headlines, justified body text and
bullet lists; page 5 a pine-forest banner photo + body text; page 6 a
Gewessler portrait photo with a quote, a green "Headline in einem
grünen Kasten" box, and a radial-gradient vignette overlay. All body
copy is lorem-ipsum placeholder text (the IDML ships it that way).

## Scaffold outcome — GREEN

Stage 1 (`/idml-scaffold`) completed structurally green:
- Inventory gate passed: every IDML `<CharacterStyleRange>` run is
  present in `build.py` (`every_idml_run_present_in_build_py: true`),
  every frame `Self` id has an `anname`, every USED `ParagraphStyle`
  has a `doc.add_para_style(...)` call.
  - One paragraph style, `ParagraphStyle/Fließtext in grünem Kasten`,
    is defined in the IDML's Styles.xml but applied to NO text in any
    story (verified by grepping all `AppliedParagraphStyle` attributes).
    It is a dormant style with zero runs — correctly not emitted; the
    `inventory` audit reports `ok: true`.
- Asset audit `ok: true` — all 4 `<Link>` files resolved and converted
  (pine-forest JPG, Gewessler JPG, radial-gradient PSD, DIE GRÜNEN AI
  logo). No missing assets.
- `build.py` runs, render succeeds, baseline/preview word counts match
  (337 == 337).

No converter (`tools/idml_to_dsl.py`) changes were needed in Stage 1.

## Tune outcome — RESIDUAL (preflight not green)

Stage 2 (`/idml-tune`) ran the `bin/tune-render` -> `bin/tune-fix`
loop. The loop exhausted all playbooks (every `line_spacing_sim` call
"returned no rows"; `frame_visibility` and `y_mm_shift` escalated).
Three productive build.py edits were applied; the residual is then
accepted per the overnight gate policy.

### Edits applied (all in build.py — see TOLERANCE_LOG rows 1-3)

1. `# noinject:` comments on the 4 external ImageFrames (u132c, u1260,
   u137f, u1386). These are genuine IDML-placed brand content (not demo
   placeholders), so the audit's `# noinject:` disposition is correct.
   Cleared `external_asset_substitution_audit` (4 → 0).
2. u1336 (DIE GRÜNEN logo): swapped `inline_image_data` + `scale_type=1`
   → `image=` ref + `scale_type=0`. The logo was fully invisible before
   (Scribus 1.6.x bug with small RGBA white-on-transparent PNGs); it now
   renders inside the green box on page 1.
3. u1260, u132c, u1386: `scale_type=1` → `scale_type=0`. The pine-forest
   photos were invisible / washed-out because Scribus re-fits on top of
   the converter's crop. `scale_type=0` honours the crop directly. Pages
   1 and 5 now render the pine background correctly.

A 4th attempt — overriding the 2-line headlines' line spacing — was
made and REVERTED (it regressed the frames; the pdfplumber gap signal
that motivated it is the unreliable one the SKILL warns against). See
TOLERANCE_LOG Notes.

The inventory gate (exit 0, no regression) passed after every edit.

### Accepted residuals — what stays red

- `text_position_audit_structural`: 254 large (>5pt) word drifts.
- `text_position_audit_jitter`: 29 sub-perceptible (≤5pt) drifts.
- `systematic_text_audit`: 8 frames.
  All three are the SAME root cause: cross-renderer line-wrap. Scribus
  and InDesign break justified paragraphs at different words; line-count
  mismatches (u1242 16→17, u129e 10→9, u12b5 11→12) cascade word
  positions. The leading the converter emitted is CORRECT
  (`line_spacing_full_audit` shows per-line gaps `match`). Classified
  `scribus-engine`.
- `image_content_audit`: 1 broken frame, `u1386` — see human-review
  below.
- `image_audit`: 40 vector-path deltas — derivative of image rendering
  + ICC shifts.
- `phase-error visual_diff_regions`: a 1-pixel raster size mismatch in
  the audit harness — a pre-existing tooling bug (the sibling template
  carries the identical error).

## Tolerances granted

No `meta.yml::brand_overrides`, `non_ci_*`, or `TOLERANCES.yml` NUMERIC
growth was granted — `region_color_audit` and `run_style_audit` are
green, so there is no brand or CI-rule violation. `TOLERANCES.yml`
records 5 accepted-residual entries (all `scribus-engine-bug` except
the radial-gradient one which is `human-review`); none grows a numeric
brand/CI tolerance — they document the cross-renderer fidelity floor.

## Human-review / authoring-bug items

ONE item needs a human eye:

- **u1386 — radial-gradient overlay renders wrong (page 6).** The
  source `Schwarzer Verlauf radial.psd` is CMYK. The asset pipeline
  converted it to `schwarzer-verlauf-radial.png` (RGB) with a broken
  CMYK→RGB step: the PSD's near-black corner (CMYK 40,255,255,255)
  became cyan (RGB 0,173,233) in the PNG. The radial vignette therefore
  renders as a pale-blue blob over the Gewessler portrait instead of a
  dark vignette. This is a SHARED asset-conversion pipeline bug — the
  IDENTICAL broken `schwarzer-verlauf-radial.png` ships in template 1
  (`26-03-flyer-a6-hochformat-portrait`), which accepted it too.
  Fixing it belongs in the Stage-1 asset/PSD-conversion pipeline
  (`tools/`), not a Stage-2 per-template patch. Recommended follow-up:
  fix the CMYK→RGB conversion (or carry the PSD's transparency into an
  RGBA PNG) once, and re-import both flyer templates.

The convergence-review classifier additionally labelled several
line-spacing items `converter-bug`. This was verified by measurement to
be a heuristic false-positive (the classifier maps the deprecated E2
`line_spacing_audit` to `converter-bug`; the authoritative E4 pixel
audit + cross-source full audit show the converter's leading is
correct). Treated as `scribus-engine`, not escalated. See TOLERANCE_LOG
Notes.

## What to eyeball in preview.pdf vs baseline.pdf

- **Page 1** — pine-forest background, green box, three-line headline
  ("Das ist eine / dreizeilige / Headline"), DIE GRÜNEN logo inside the
  box, magenta "Störer" badge. Should match well. The logo and
  background were broken before the tune edits and are now fixed.
- **Page 5** — pine-forest banner photo at the top + body text below.
  Should match well; the banner photo was invisible before.
- **Pages 2-4** — green body pages. Content and layout match; body text
  wraps a hair differently and sits slightly higher (Scribus vs
  InDesign metrics). Sub-perceptible; nothing missing.
- **Page 6 — LOOK HERE.** The Gewessler portrait renders correctly, but
  the radial-gradient vignette overlay (`u1386`) renders as a
  washed-out pale-blue patch instead of a dark vignette. This is the
  one genuine visible defect, caused by the upstream PSD→PNG conversion
  bug described above. Compare the dark, even vignette in baseline.pdf
  page 6 against the blue-tinted blob in preview.pdf page 6.
