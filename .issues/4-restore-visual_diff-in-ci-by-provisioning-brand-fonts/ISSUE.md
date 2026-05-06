---
id: '4'
title: Local render pipeline that commits gallery artifacts; CI becomes pure shipper
status: open
priority: high
labels:
- rendering
- ci
- gallery
- pipeline
---

## Goal

Move all template rendering into a deterministic local pipeline that the maintainer runs in the dev container. The pipeline produces every gallery artifact (preview PDFs, page PNGs at the right sizes, sla_diff reports, visual_diff reports) and **commits them into the repo**. CI becomes a pure shipper: it runs `sla_diff --strict` as a structural gate, then copies the committed artifacts to GitHub Pages. **CI never renders.**

This locks in **Option B** from issue #3's wrap-up discussion. Per user direction:

> "I will always review locally, so we don't actually need the SLA files to be created on github actions, we just have them created locally and then committed."
> "build up a pipeline locally that also commits the images and everything necessary so we ship fully locally"

Option A (provisioning Gotham Narrow into CI via private repo + PAT) and Option C (hybrid CI render + compare against committed) are explicitly **rejected** as scope creep. The single rendering toolchain in the dev container is the source of truth.

## Why

- **No CI font provisioning needed.** Gotham Narrow stays out of CI permanently; no PAT secrets, no private fonts repo, no fork-PR exception.
- **Single render path = no drift.** With only one rendering toolchain (the dev container), the render output that ships is the same as the render output the author saw locally. No need to compare two paths.
- **Author review is sufficient.** The maintainer already reviews renders locally before pushing; CI re-rendering would just duplicate that review robotically.
- **Faster CI.** Without xvfb-run + scribus + visual_diff, the CI step collapses to "run sla_diff + cp files" — sub-30-second runs vs the current several-minute renders.
- **Repo licensing stays clean.** No proprietary Gotham font in any private repo or secret store; fonts live only on the maintainer's local `fonts/` drop zone.

## Scope

### Local rendering pipeline (`bin/render-gallery`)

A new shell or Python script at `bin/render-gallery` that, run from the dev container:

1. Verifies brand fonts are installed (`fc-list | grep -ciE 'gotham narrow|vollkorn'` ≥ expected count) — fails loud if not (refuses to render with DejaVu fallback).
2. For each template directory under `templates/<id>/` with a `meta.yml` and `original_sla:` key:
   - Runs the template's `build.py` to regenerate `template.sla` from the DSL.
   - Renders the template SLA via the headless Scribus pipeline → `templates/<id>/preview.pdf`.
   - Rasterises preview PDF to per-page PNGs at the gallery display dpi (currently 80 dpi from `gallery_build.py`; the new pipeline standardises this — see below) → `templates/<id>/page-NN.png`.
   - Runs `sla_diff --strict` against the committed `*-original.sla` — fails loud on critical/warning diff.
   - Runs `visual_diff` against `templates/<id>/baseline.pdf` (the frozen ground truth) — fails loud on per-template threshold breach.
3. Copies the produced `preview.pdf` + `page-*.png` into `site/public/templates/<id>/` (the location Astro consumes).
4. Updates `site/src/content/templates/<id>.md` if its frontmatter referencing the artifacts changes.
5. Emits a summary: how many templates rendered, total mismatch px per template, total artifact size.

The pipeline must be **idempotent** and **fully deterministic**: running it twice on the same SLA must produce byte-identical output (modulo the verified-non-deterministic PDF metadata layer that visual_diff already ignores).

### Preview PNG dpi reduction

PR-prep follow-up the user flagged earlier: gallery preview PNGs are currently 80 dpi → 132 KB avg → 1.8 MB total Zeitung payload. Drop to **50 dpi** as part of this pipeline change → ~55 KB avg → ~770 KB total. Renders crisp at 2× retina up to 220 px display width (the current grid layout's max).

### gallery_build.py refactor

`tools/gallery_build.py` currently *renders* via `xvfb-run scribus`. After this issue, it becomes a pure copy + frontmatter-write step:

- Walks `templates/*/` looking for committed `preview.pdf` + `page-*.png`
- Copies them to `site/public/templates/<id>/`
- Writes/updates `site/src/content/templates/<id>.md` frontmatter with the artifact paths
- Fails fast if expected committed artifacts are missing for a template (the new pipeline must produce them)

It MUST NOT call xvfb-run, scribus, or any rendering tool. CI doesn't have those (per D7 of issue #3). If `gallery_build.py` is ever invoked in an env without rendered artifacts, it fails clearly: "run bin/render-gallery first, then commit the artifacts."

### Stale-artifact detection

The risk with committed renders: the SLA changes but the author forgets to re-render. The pipeline must catch this. Two-layer defence:

1. `bin/render-gallery` always re-renders everything (even if only one template changed) → just running the pipeline produces fresh artifacts.
2. A new check `bin/check-stale-previews`:
   - For each template, compares `templates/<id>/template.sla` content hash against a content-hash baseline embedded in `templates/<id>/meta.yml::previews_for_sla:`.
   - If the SLA hash doesn't match, exits 1 with a "previews are stale; run bin/render-gallery and commit" message.
   - `bin/render-gallery` updates the hash in meta.yml as part of its run.
   - Hooked into `bin/validate` (which CI already runs) so stale previews fail CI structurally.

### CI workflow simplification

`.github/workflows/pages.yml::validate-reproductions` step changes:

- Drop the rendering step (already gone since issue #3 PR #7).
- Keep `sla_diff --strict` per template (structural gate).
- Add `bin/check-stale-previews` invocation — fails the build if committed previews are out-of-date for the committed SLAs.
- Drop the brand-font install step entirely (was never added; not needed).
- Remove the TODO comment in pages.yml that referenced this issue (since the resolution is now "intentionally don't render in CI", not "restore visual_diff in CI").

`.github/workflows/pages.yml::deploy` step stays as-is — it consumes the Astro-built site which now references the committed previews via gallery_build.py's copy-only path.

### Documentation

`docs/render-fidelity.md` updates:

- Add a new section "Local-only rendering: why CI never renders templates" that explains the chosen architecture (Option B reasoning).
- Update the "CI font provisioning" Out-of-scope section to "Out of scope permanently" with a short justification.
- Add a "Maintainer workflow" section: edit SLA → run `bin/render-gallery` → review locally → commit → push. Include the stale-preview gotcha.

`shared/fonts/README.md` already correctly says fonts live in `fonts/` and are required for local rendering; minor wording update to clarify that this is the *only* path that produces gallery artifacts (no CI fallback).

## Acceptance Criteria

- [ ] `bin/render-gallery` exists, is documented, and produces all gallery artifacts deterministically (preview.pdf + page-*.png per template + visual_diff/sla_diff reports).
- [ ] Running `bin/render-gallery` twice produces no git diff (idempotent).
- [ ] Preview PNG dpi reduced from 80 → 50; per-page Zeitung PNG drops from ~132 KB → ~55 KB; total Zeitung gallery payload drops from ~1.8 MB → ~770 KB; visually crisp at 220 px display width.
- [ ] `tools/gallery_build.py` no longer renders; only copies + writes frontmatter. It fails clearly if expected artifacts are missing.
- [ ] `bin/check-stale-previews` exists; detects mismatched template.sla content hash; fails with a clear "run bin/render-gallery" message.
- [ ] `bin/validate` invokes `check-stale-previews` as a preflight (or post-render check).
- [ ] `.github/workflows/pages.yml::validate-reproductions` runs sla_diff + check-stale-previews only; runtime under 30 sec.
- [ ] `.github/workflows/pages.yml::deploy` continues to work and produces a working Pages deploy from the committed artifacts.
- [ ] `docs/render-fidelity.md` describes the local-only architecture; CI-fonts is permanently out-of-scope.
- [ ] One end-to-end demo: edit a template SLA (e.g. minor headline change), run `bin/render-gallery`, commit, push → CI passes → Pages deploy reflects the change visually.
- [ ] All current 17 pages still byte-equivalent to the user's reference Scribus 1.6.4 exports (regression check that the pipeline didn't break the established fidelity).

## Out of Scope (permanently)

- Installing brand fonts on GitHub Actions runners (Option A — rejected)
- Hybrid CI render + visual_diff against committed (Option C — rejected)
- Migrating to a paid private GitHub Pages tier
- Authoring contributors who don't have access to the dev container's font drop zone (single-author project)
- New SLA fixes or DSL changes — that's other issues' territory
- Replacing the rendering toolchain (Scribus stays)

## Notes / Pointers

- Predecessor: issue #3 (`Render-fidelity ground truth: match user's Scribus 1.6.4 export with proper brand fonts`). Established local fidelity, set up `Dockerfile.claude` font install, removed visual_diff from CI as a stop-gap. THIS issue replaces that stop-gap with the permanent architecture.
- `tools/gallery_build.py` current state: lines 26–39 (render_pdf), lines 75–107 (render in walk_template). All this rendering moves to `bin/render-gallery`; gallery_build.py keeps only the copy + frontmatter logic.
- `bin/validate` current state: invokes `tools/sla_diff.py --strict` + `tools/visual_diff.py` per template; the latter requires fonts (only works in dev container). Add `bin/check-stale-previews` as a preflight.
- `bin/check-fontsizes` (added in PR #7) is the existing pattern for a `bin/`-prefix preflight check; mirror its shape for `bin/check-stale-previews`.
- The fontconfig alias at `shared/fonts/50-vollkorn-family-alias.conf` stays — it's still needed for local rendering.
- `templates/<id>/baseline.pdf` (committed, frozen) stays — it's the visual_diff reference. visual_diff still runs locally; this issue doesn't change that.
- The `Dockerfile.claude` font install layers (added in PR #7) stay — they're how local rendering works. This issue is about CI not having to mirror them.

## Reasoning trail (for future reference)

The decision to make CI a pure shipper instead of a renderer was made after considering:

- **Drift detection:** Two render paths (dev + CI) require visual_diff to detect divergence. With one path, there's nothing to compare.
- **Font licensing:** Avoiding any private/secret-managed copy of Gotham Narrow.
- **CI runtime + complexity:** Removing render means dropping xvfb, scribus, fonts, conf files, several minutes of runtime, and the third-party-PR-no-secret edge case.
- **Author workflow:** The maintainer already reviews locally before pushing; auto-rendering in CI would re-do that review on every push without adding new signal.
- **Trade-off accepted:** Stale previews if the author forgets to re-render. Mitigated by `bin/check-stale-previews` as a CI gate (compares committed template.sla content hash to committed-preview-hash).
