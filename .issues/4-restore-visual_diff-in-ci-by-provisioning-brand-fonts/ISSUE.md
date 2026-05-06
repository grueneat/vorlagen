---
id: '4'
title: Restore visual_diff in CI by provisioning brand fonts
status: open
priority: high
labels:
- rendering
- fonts
- validation
- ci
---

## Goal

CI currently runs only `sla_diff --strict` (the structural gate). Visual rendering fidelity in CI requires the brand fonts (Gotham Narrow proprietary + Vollkorn OFL) to be installed in the runner. Without them, DSL-rendered output uses DejaVu fallback and diverges catastrophically from the font-bundled `templates/<id>/baseline.pdf` committed in the PR for issue #3.

This issue: restore the `visual_diff` invocation in `.github/workflows/pages.yml`'s `validate-reproductions` step, gated on a CI-side font-install step that obtains Gotham Narrow from a license-clean private channel.

## Why

**Visual fidelity is the user-facing quality bar; structural diff alone misses entire classes of rendering regression.** Per user direction: drift between what authors see locally and what the gallery serves at vorlagen.gruene.at must be either *detected* (via CI visual_diff) or *prevented* (by single-source-of-truth rendering). Doing neither — letting CI render with DejaVu fallback while authors use brand fonts — silently produces wrong output on the public gallery.

Issue #3 established that with the right fonts the dev-container renders byte-identical to the user's Scribus 1.6.4 export. This issue extends that fidelity to the production rendering path.

## Two viable approaches — discuss step picks one

This issue's first discuss-step decision is choosing between:

### Option A — Install brand fonts in CI; CI renders + visual_diff
- Create a private repo (e.g. `GrueneAT/brand-fonts-private`) with the Gotham Narrow + Vollkorn font tree matching the local `fonts/` layout
- Add a fine-grained read-only PAT as the `BRAND_FONTS_PAT` secret on `GrueneAT/vorlagen`
- Workflow clones the private repo into `fonts/` before rendering, then mirrors the local Dockerfile.claude install pattern
- Restore visual_diff in `validate-reproductions` step; CI catches drift on every push
- **Tradeoffs:**
  - More CI moving parts (PAT rotation, private-repo maintenance)
  - Third-party PRs (forks) don't get the secret → visual_diff must gracefully skip on fork PRs and run sla_diff only
  - Two render paths (dev container + CI) that *should* produce the same output but theoretically can drift
  - Pro: every push automatically validated; renders are always fresh

### Option B — Full local rendering; CI never renders, only ships
- Author renders templates locally in the dev-container (which already has fonts after issue #3) → produces preview PDFs / PNGs
- Commit the rendered artifacts into the repo (or a separate releases/artifacts repo)
- CI's job becomes: run `sla_diff --strict` (structural gate) + ship the *committed* preview artifacts to Pages
- gallery_build.py becomes a copy step instead of a render step
- **Tradeoffs:**
  - Simpler CI: no fonts in CI ever, no PAT, no fork-PR exception
  - Single rendering toolchain (dev container) → no drift possible because there's only one render path
  - Pro: works the same for any contributor as long as they have the dev container
  - Con: every visual change requires a local render+commit cycle (no auto-render on push)
  - Con: PRs that change templates need the author to commit BOTH the SLA/build.py changes AND the freshly-rendered preview artifacts; CI can structurally check the SLA but can't visually verify the previews themselves are up-to-date with the SLA → adds a "renders are stale" failure mode that needs a check (e.g. compare commit timestamps, or a `make-previews` step that fails if its output diff is non-empty)

### Option C (hybrid, only if needed) — Local rendering + CI render-and-compare-to-committed
- Author renders + commits locally (Option B's flow)
- CI also renders (with fonts) and compares its render against the committed artifacts via visual_diff
- Catches both "author forgot to commit fresh previews" AND "CI/dev container drift"
- Most thorough; also most CI infrastructure to maintain — gets back to Option A's complexity plus Option B's commit cycle

## Scope

The scope below assumes whichever option is picked in the discuss step. Adapt:

1. **(A only)** Set up private font source + PAT secret. Add `Install brand fonts (CI)` step to `.github/workflows/pages.yml` before `Validate reproductions`. Install fontconfig alias from `shared/fonts/50-vollkorn-family-alias.conf`. Restore `visual_diff` invocation + `Upload visual-diff composites on failure` step. Handle the fork-PR-no-secret case (skip visual_diff, run sla_diff only, status comment).
2. **(B only)** Add `bin/render-previews` (or similar) to the dev-container workflow that produces all gallery artifacts deterministically. Update `gallery_build.py` to consume committed renders rather than render itself. Add a CI check that detects stale previews (e.g. SLA committed without re-rendered preview).
3. **(both)** Update `docs/render-fidelity.md` to document the chosen flow.
4. **(both)** Remove the TODO comment in `pages.yml` (added in #3) once the workflow is updated.

## Acceptance Criteria

- [ ] CI workflow installs brand fonts from a license-clean private channel
- [ ] `fc-list | grep -iE 'gotham narrow|vollkorn'` reports the expected count in CI; missing fonts fail the build
- [ ] `validate-reproductions` runs both `sla_diff --strict` AND `visual_diff` per template
- [ ] `Upload visual-diff composites on failure` step is restored
- [ ] Deliberate-drift CI run uploads composites and fails; clean CI run passes
- [ ] `docs/render-fidelity.md` updated to remove the "CI is font-less" caveat
- [ ] Issue #3's `pages.yml` TODO comment is removed (workflow comments now reflect restored state)

## Out of Scope

- Local dev-container font work (already done in issue #3)
- New SLA fixes or DSL changes (separate concerns)

## Notes / Pointers

- Predecessor: issue #3 (`Render-fidelity ground truth: match user's Scribus 1.6.4 export with proper brand fonts`) — establishes local fidelity, sets up Dockerfile.claude font install, removes visual_diff from CI as a stop-gap
- Reference for the local pattern: `shared/fonts/50-vollkorn-family-alias.conf` + Dockerfile.claude's font-install RUN block
- The TODO comment to remove lives at `.github/workflows/pages.yml`'s `validate-reproductions` step, just above where visual_diff was invoked
- The visual_diff invocation block was at lines 115-121 of `pages.yml` before issue #3 removed it — restore in same position with the new font-availability precondition
