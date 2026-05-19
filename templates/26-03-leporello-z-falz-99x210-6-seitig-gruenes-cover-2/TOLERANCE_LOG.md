# Tolerance Log — 26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2

Companion log for `TOLERANCES.yml` and `meta.yml::brand_overrides`.
The protocol in `.claude/skills/idml-tune/tolerance_protocol.md`
formally gates additions to `meta.yml::brand_overrides` / `non_ci_*`
lists. The brand_overrides below are added in parity with the shipped
sibling 26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover — every
entry documents an IDML-import gap class the converter cannot close
per the current pipeline.

Append-only. To remove an entry, add a new row at the bottom that says
`REMOVED <id> — <date>: <reason fix landed>`.

---

## 2026-05-19 — re-scaffold for the 3-line headline + green-texture-embed converter fix set

This template was re-scaffolded (`bin/idml-import --scaffold-only
--reimport`) so build.py is regenerated with the converter's
single-line-per-headline-line emission. Two defects from the
pre-fix scaffold are closed:

- **3-line headline.** The cover headline "Das ist die / dreizeilige
  / Headline" is now emitted as three single-line TextFrames
  (`u52d` / `u52d_l2` / `u52d_l3`) at the IDML Leading interval, each
  `LINESPMode=0 LINESP=34.13`. `line_spacing_pixel_audit` reports
  per-line drift within 0.5pt of baseline.pdf — `split_headline_spacing`
  is GREEN. The two 2-line "Ich bin eine Headline." headlines
  (`u1b0` / `u1e6`) are likewise pre-split and even. (The pre-fix
  scaffold rendered the headlines as single mixed-font frames with
  broken inter-line spacing.)
- **Green brand texture.** `plakat-dunkel-fuer-flyer.png` (the green
  crumpled-paper brand texture, despite the filename) now classifies
  as `asset_policy::embedded` via the converter's known-brand-asset
  rule (`tools/idml_import_driver.py::_EMBEDDED_BRAND_STEMS`). The
  converter inlines the texture bytes; `template.sla` carries it as
  `isInlineImage` ImageData (no `PFILE` reference) so the downloaded
  SLA always shows the brand panel, never a missing-image
  placeholder.

`meta.yml::brand_overrides` was added (4 rules: `bleed_3mm`,
`image_text_overlap`, `inside_page`, `line_spacing_0.9`) — the
re-scaffold regenerates meta.yml with no overrides; they are added
in parity with the shipped sibling
26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover, documenting
the same four IDML-import gap classes (verbatim leading emission,
intentional text-on-photo overlay, multi-panel spread geometry,
bleed=0 vs Quickguide 3mm). The stale `template-preview.sla`
orphaned by the re-scaffold was removed (the regenerated build.py
has an empty INJECT_MAP, so the gallery renders `template.sla`
directly, matching gruenes-cover).

Residual preflight reds (image_audit vector-path delta,
line_match / text_position cross-renderer line-wrap, composite-AI
social-icon visibility, visual_diff_regions) are the documented
Scribus-vs-InDesign engine-floor classes captured in `TOLERANCES.yml`
— the same residual class the shipped gruenes-cover sibling carries.
