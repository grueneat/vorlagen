---
id: '39'
title: Self-contained template downloads — brand embed + content zip
status: open
priority: high
labels:
- dsl
- templates
- tooling
- packaging
- skills
source: github
source_id: '81'
source_url: 'https://github.com/GrueneAT/vorlagen/issues/81'
---

## Context

Today's committed `templates/<slug>/template.sla` files reference assets
via **absolute worktree paths** (e.g.
`/workspace/.worktrees/35-…/shared/assets/26-03-leporello-…/gruene-logo-bund-weiss-cmyk.png`).
This is a real bug: the moment a user downloads the SLA, none of those
paths resolve. The downloadable artifact is broken.

The v2-falzflyer (issue #35 / #37) shipped this way. Every template
goes through the converter that embeds the worktree path; every
download inherits the bug. The user surfaced it during a check on
the shipped v2-falzflyer asset:

> "I want the Grüne Logo, the Social Media icons and the green background
>  image on the second page on the right third to be embedded into the SLA
>  file, so they are part of the downloadable artifact. One other option I
>  can think of is not embedding them, but creating a zipfile for each
>  downloadable SLA if it has artifacts we want to ship with it, or even
>  ship our AI generated artifacts with it as files in the zip and local
>  paths configured in the SLA file (e.g. a subfolder where we put those
>  files so they know how this works)."

After discussion, the chosen split is **hybrid**: brand-locked assets
embedded INLINE in the SLA, content (user-replaceable) assets shipped
in a sidecar ZIP with relative SLA paths.

The skill side of this is already documented as part of this issue's
prerequisite: `.claude/skills/idml-import/asset_policy.md` + P11
in SKILL.md + `shared/asset-policy.schema.yaml` + `load_asset_policy()`
in `meta_schema.py`. **This issue lands the implementation.**

## Principles

### P11 — Templates are self-contained downloads. (Mirrors SKILL.md P11)

- Brand assets (logos, social icons, decorative backgrounds, brand
  illustrations) are EMBEDDED inline in the SLA via
  `ImageFrame.inline_image_data`. The user cannot accidentally remove
  or replace them.
- Content assets (portraits, AI-generated demo images, swappable
  photos) ship in `<slug>.zip::assets/<basename>`. The SLA references
  them via REPO-RELATIVE paths (`assets/<basename>`).
- All paths in committed `template.sla` files are repo-relative. CI
  rejects PRs that introduce absolute paths.
- Every asset must be explicitly classified in
  `meta.yml::asset_policy`. The skill STOPS and asks before
  auto-classifying.

### P11.1 — Defaults but no auto-write.

The skill MAY propose a classification based on filename heuristics
(`*logo*`, `*social-media-icon*`, `wahlkreuz*`, `*-weiss.png`,
`*-cmyk.png` → embed; `portrait*`, `photo*`, `themen-*`, `kandidat-*`
→ ship). But the proposed entry is presented to the user for explicit
confirmation; never written to `meta.yml` without it.

### P11.2 — The ZIP is built by the pipeline, not by the user.

`bin/render-gallery` (and `bin/idml-import`'s final phase) produces
`templates/<slug>/<slug>.zip`. The gallery (`site/public/`) links to
the zip, not the bare SLA. The user-facing download is always the
zip.

## Scope

Six deliverables, organised by user-visible value.

### Phase A — Path canonicalisation

**Bug fix prerequisite for everything else.** Without this the
embedded-vs-shipped split doesn't matter because absolute paths still
leak.

1. `tools/idml_to_dsl.py`: emit repo-relative paths for ImageFrame
   sources (`shared/assets/<slug>/<basename>` not the absolute
   path). The converter must NOT call `Path.resolve()` or
   `Path.absolute()` on asset paths.
2. Migration: rewrite every committed `templates/*/template.sla` to
   replace absolute worktree paths with repo-relative ones. Round-trip
   test: re-emit each template's SLA, compare to existing — should
   be byte-identical after path normalization.
3. CI lint: `tools/check_no_absolute_paths_in_sla.py` grep-bans
   `/workspace/`, `/home/`, `/root/`, `/tmp/` prefixes in `PFILE=`
   attributes of any committed `template.sla`. Wire into pre-commit
   + GitHub Actions.

### Phase B — Asset classification + meta.yml plumbing

1. `tools/asset_policy_audit.py`: reads `meta.yml::asset_policy` +
   `shared/assets/<slug>/links_export.yml`; asserts (a) lists are
   disjoint (already in `load_asset_policy`), (b) every asset in
   `links_export.yml` appears in exactly one of `embedded`/`shipped`,
   (c) no unknown assets (asset listed in policy but not in
   `links_export.yml`). Wired into `_run_audit` BEFORE A1 inventory.
   Hard-fails in preflight.yml.
2. `bin/idml-import`: during Step 1 (asset extraction), invoke
   `tools/asset_policy_audit.py`. If `asset_policy:` is missing OR
   incomplete, STOP and present the heuristic-guessed classification
   to the user for confirmation. Only after explicit `yes` does the
   skill write `meta.yml::asset_policy`.

### Phase C — SLA inline-embedding emission

1. `tools/idml_to_dsl.py`: for each asset listed in
   `meta.yml::asset_policy::embedded`, emit ImageFrame with
   `inline_image_data=` + `inline_image_ext=` (existing
   `pack_inline_image()` from `primitives.py`). For assets in
   `shipped`, emit ImageFrame with `image='assets/<basename>'`
   (relative path).
2. The reconciler (`tools/reconcile_build_py.py`) preserves this
   distinction; inject overrides cannot change an asset's
   embed/ship bucket (that's a `meta.yml::asset_policy` edit).
3. Re-emission byte-identity test: every existing template's
   `build.py` re-emits to the same content after this change
   (modulo the path canonicalisation from Phase A).

### Phase D — ZIP build pipeline

1. `tools/build_template_zip.py`: takes `templates/<slug>/`,
   reads `meta.yml::asset_policy::shipped`, packages
   `template.sla` + `assets/<basename>` + a `README.txt` describing
   the convention. Output: `templates/<slug>/<slug>.zip`.
2. `bin/render-gallery` invokes the zipper after a successful
   render. Zip ends up alongside the SLA + previews in `templates/<slug>/`
   and is mirrored to `site/public/templates/<slug>/`.
3. The README.txt template:
   ```
   {{ template_title }} — {{ today }}
   ============================================================
   This zip contains:
     - template.sla    — the Scribus document. Open in Scribus 1.6+.
     - assets/         — files the template references via assets/<name>.
                         Replace these files (keep the names + extensions)
                         to substitute your own portraits / photos.
     - README.txt      — this file.

   Editing the template:
     1. Unzip somewhere.
     2. Open template.sla in Scribus.
     3. Replace files in assets/ with your own (same name + extension).
     4. Re-open template.sla; Scribus picks up the new images.

   Brand-locked assets (logos, social-media icons, decorative
   backgrounds) are embedded INSIDE template.sla and cannot be
   replaced this way. Contact the brand team for sign-off if you
   need to change them.
   ```

### Phase E — Gallery download flow

1. `site/public/templates/<slug>/` mirroring: change the download
   target from `template.sla` to `<slug>.zip`.
2. `tools/gallery_build.py` (or wherever the gallery index is
   built — TBD during research): the listing for each template
   shows the zip filename and size; the link target is the zip.
3. The bare SLA stays in the template directory for diff /
   convergence-loop debugging, but is NOT what users download.

### Phase F — v2-falzflyer migration (the proof-of-concept)

1. Author `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/
   meta.yml::asset_policy` per the split in `asset_policy.md`:
   - `embedded:` gruene-logo, 6 social icons, social-media-icons-weiss
     composite (reference), green-pine-trees-covered-with-fog-crop.
   - `shipped:` plakat-dunkel-fuer-flyer, green-pine-trees-covered-with-fog
     (.jpg + .srgb.png).
2. Re-emit `templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/`
   via `bin/idml-import --reimport`. Verify:
   - `template.sla` uses inline data for the 7 embedded assets.
   - `template.sla` uses `assets/<name>` paths for the shipped ones.
   - `template.sla` contains zero absolute paths.
   - `<slug>.zip` exists, opens in `unzip -l` showing the expected
     `template.sla` + `assets/<name>` + `README.txt`.
   - Unzipped + opened in Scribus on a clean checkout, all images
     resolve.
3. Compare the rendered preview.pdf BEFORE and AFTER the migration:
   byte-identical OR diff explained by the embed-vs-link rendering
   path (some Scribus engines render PNG-from-disk vs
   PNG-inline-base64 slightly differently — document any drift in
   EXECUTION.md).

## Acceptance Criteria

### Phase A — Path canonicalisation
- [ ] No committed `template.sla` contains an absolute filesystem path.
- [ ] `tools/check_no_absolute_paths_in_sla.py` fires in CI.
- [ ] `tools/idml_to_dsl.py` never emits absolute paths.

### Phase B — Classification
- [ ] `tools/asset_policy_audit.py` exists and wires into `_run_audit`
      BEFORE A1.
- [ ] Schema validation rejects malformed `asset_policy:` blocks
      (already partially via `load_asset_policy`).
- [ ] `bin/idml-import` STOPS on unclassified assets and asks for user
      confirmation.

### Phase C — Inline embedding
- [ ] Embedded assets land via `ImageFrame(inline_image_data=...)`.
- [ ] Shipped assets emit `image='assets/<basename>'`.
- [ ] Re-emission of an existing template is idempotent.

### Phase D — ZIP build
- [ ] `tools/build_template_zip.py` produces `<slug>.zip` with
      `template.sla` + `assets/*` + `README.txt`.
- [ ] `bin/render-gallery` invokes it after every successful render.
- [ ] `<slug>.zip` mirrored into `site/public/templates/<slug>/`.

### Phase E — Gallery
- [ ] Gallery download link points at the zip, not the bare SLA.
- [ ] Zip size + content count surfaced in the listing.

### Phase F — v2-falzflyer
- [ ] `meta.yml::asset_policy` authored correctly.
- [ ] Re-emitted SLA has 7 inline brand assets + 3 (or 2 — depending
      on the .jpg/.srgb.png decision) `assets/<name>` references.
- [ ] `<slug>.zip` exists and unzips into a working Scribus document
      on a clean checkout.
- [ ] preview.pdf diff is byte-identical OR documented.

### Cross-cutting
- [ ] All 9 existing templates pass the new audit (after a
      `meta.yml::asset_policy` block is authored for each, or via an
      `--asset-policy-skip` opt-out for non-IDML-sourced templates
      that don't have a Links/ directory).
- [ ] `bin/idml-import` end-to-end test re-imports v2-falzflyer
      and produces a working zip.

## Out of scope

- Auto-suggesting brand vs content classification for files outside
  the heuristic regex (e.g. `*.eps`, `*.tif`). The skill stops; the
  user decides.
- Inline-embedding non-image assets (fonts, ICC profiles). These
  remain shared-system resources.
- Per-asset compression tuning inside the SLA (e.g. recompressing
  PNGs as JPEG). The inline path uses the asset bytes as-is.
- Cloud-hosted asset CDN. Everything ships in the zip, period.

## References

- Issue #35 (PR #76) — converter bootstrap; introduced the
  absolute-path bug.
- Issue #37 (PR #77) — audit infrastructure.
- Issue #38 (PR #79) — `/idml-import` skill + pattern library.
- `.claude/skills/idml-import/asset_policy.md` — policy doc that
  predates this issue's landing.
- `shared/asset-policy.schema.yaml` — meta.yml::asset_policy schema.
- `tools/sla_lib/builder/meta_schema.py::load_asset_policy` — the
  loader stub already on main; this issue makes it load-bearing.

## Estimated effort

Three sub-phases:

- **Sub-phase 1** (1 day): Phase A path canonicalisation. The
  foundation. Independent of the embed/ship split — just removes
  the absolute-path bug.
- **Sub-phase 2** (2 days): Phases B + C + the asset_policy audit
  wire-up. The classification gate + SLA emission split.
- **Sub-phase 3** (1-2 days): Phases D + E + F. Zip pipeline, gallery
  flow, v2-falzflyer migration as the proof.
