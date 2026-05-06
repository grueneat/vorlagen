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

- Visual fidelity is the user-facing quality bar; structural diff alone misses entire classes of rendering regression.
- Issue #3 established that with the right fonts the dev-container renders byte-identical to the user's Scribus 1.6.4 export. CI should match.
- The TODO comment in `pages.yml` (added in #3) is not enough — it'll rot.

## Scope

1. Decide CI font-source mechanism: private GitHub repo + PAT secret; S3 + AWS creds; encrypted artifact attached to the workflow. Pick one based on user authorisation pattern.
2. Add a `Install brand fonts (CI)` step to `pages.yml` before `Validate reproductions`. Mirror the local Dockerfile.claude pattern: copy fonts into `/usr/local/share/fonts/gruene/` + `fc-cache -f` + sanity-probe `fc-list | grep -iE 'gotham narrow|vollkorn'` (fail-loud on missing).
3. Install the fontconfig alias from `shared/fonts/50-vollkorn-family-alias.conf`.
4. Restore the `visual_diff` invocation (currently removed) inside the `Validate reproductions` step.
5. Restore the `Upload visual-diff composites on failure` step.
6. Verify on a deliberate-drift PR that visual_diff fails the build and uploads composites; on a clean PR it passes.
7. Update `docs/render-fidelity.md` "Out of scope" and "CI font provisioning" sections to reflect the new state.

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
