---
issue: 4-restore-visual_diff-in-ci-by-provisioning-brand-fonts
phase: discuss
date: 2026-05-06
---

# CONTEXT — Local render pipeline, CI as pure shipper

## What this issue actually delivers

After this PR, the rendering pipeline has exactly one path: **the maintainer runs `bin/render-gallery` in the dev container, the artifacts are committed, CI ships them**. CI never invokes Scribus, never installs brand fonts, and never renders. The current `validate-reproductions` step shrinks to `sla_diff --strict` + a stale-preview check.

Note: the slug retains the original "restore visual_diff in CI" name from when this issue tracked Option A. The actual scope is now Option B (local-only render + commit). No re-slug — the file path is permanent in the issue store.

## Decisions locked in

These are settled before this issue's research/plan/execute. Do NOT re-surface them; the user explicitly asked for `/issue:work` to run end-to-end without further discussion.

### D1 — Single render path: the dev container's local pipeline
The maintainer runs renders locally in the dev container (which has brand fonts installed via `Dockerfile.claude`). The committed `templates/<id>/preview.pdf` + `page-*.png` are the gallery's source of truth. CI is a pure shipper.

### D2 — `bin/render-gallery` is the pipeline entry point
A new script (Python or bash) at `bin/render-gallery`. Behaviour:
- Verify brand fonts are installed; refuse to render with DejaVu fallback (fail-loud).
- For each `templates/<id>/` with `meta.yml::original_sla:` set:
  1. Run `templates/<id>/build.py` → regenerate `template.sla` from DSL.
  2. Render `template.sla` headless via Scribus → `templates/<id>/preview.pdf`.
  3. Rasterise `preview.pdf` to `templates/<id>/page-NN.png` at 50 dpi.
  4. Run `tools/sla_diff.py --strict` against the committed `*-original.sla`.
  5. Run `tools/visual_diff.py` against committed `templates/<id>/baseline.pdf`.
  6. Update `templates/<id>/meta.yml::previews_for_sla:` with the SLA's content hash.
- Idempotent: running twice on the same source must produce no git diff.
- The script writes the rendered preview/PNGs into both `templates/<id>/` (the source of truth) AND `site/public/templates/<id>/` (gallery's public output).

### D3 — Preview PNG dpi = 50 (down from 80)
Per the user's earlier "preview images are slow to load" feedback. 80→50 dpi gives ~2.4× smaller PNG payload while staying crisp at 220 px display width × 2 retina = 440 px (well above the 50-dpi A4 width of ~413 px).

### D4 — `tools/gallery_build.py` becomes copy-only
After this issue, `gallery_build.py`:
- Walks `templates/*/` for committed `preview.pdf` + `page-*.png`.
- Copies them to `site/public/templates/<id>/`.
- Writes/updates `site/src/content/templates/<id>.md` frontmatter.
- **MUST NOT** call `xvfb-run`, `scribus`, or any rendering tool.
- Fails clearly if expected committed artifacts are missing for a template (the new pipeline must produce them; absence = author forgot to run `bin/render-gallery`).

This is what makes CI font-less work: gallery_build.py runs in CI and only copies + writes content.

### D5 — `bin/check-stale-previews` regression check
Hash-based stale detection, mirrors the shape of `bin/check-fontsizes`:
- For each template with `meta.yml::original_sla:`:
  - Compute SHA256 of the committed `*-original.sla` (or `template.sla` — pick whichever is the upstream of the rendered preview; recommend the original SLA since previews trace back to it).
  - Compare against `templates/<id>/meta.yml::previews_for_sla:` (the hash recorded by `bin/render-gallery` at last render time).
  - If mismatched, exit 1 with: "Previews for <id> are stale. Run `bin/render-gallery` and commit the result."
- Hooked into `bin/validate` so CI's existing validate step gates on it.

### D6 — `.github/workflows/pages.yml::validate-reproductions` simplification
Final state of that step:
1. `sla_diff --strict` per template (already there from issue #3).
2. `bin/check-stale-previews` (new — added by this issue).
3. Drop the TODO comment that referenced restoring visual_diff (since the resolution is now "intentionally never").
The deploy job is unchanged — Astro builds, Pages serves.

### D7 — CI font provisioning is permanently out of scope
Out of scope. Not future work. Not a follow-up issue. **Closed**.

The reasoning is in ISSUE.md "Reasoning trail". Summary: drift between two render paths is irrelevant when there's only one render path; font licensing stays clean; CI runtime + complexity drops; the maintainer reviews locally before pushing anyway.

### D8 — `bin/validate` keeps doing visual_diff locally (no change to local behaviour)
`bin/validate` continues to run `sla_diff` + `visual_diff` for the maintainer. Visual_diff requires fonts (only works in dev container). It's the maintainer's local check before commit; it's NOT what runs in CI. CI calls a subset (sla_diff + check-stale-previews).

### D9 — `bin/render-gallery` is the user's authoring loop entry
The documented maintainer workflow becomes:
1. Edit a template SLA / build.py.
2. Run `bin/render-gallery`.
3. Review the resulting `preview.pdf` + `page-*.png` (open them locally).
4. `git add templates/ site/public/ && git commit && git push`.
5. CI passes (sla_diff + check-stale-previews); Pages deploy fires.

## Constraints

- **Never edit `originals/*.sla` or `*-original.sla` in this work.** Issue #3 established those as the canonical input. This issue is about the *output* pipeline.
- **Don't regress the `bin/validate` 0-px standard** established in PR #7. After `bin/render-gallery` runs, all 17 pages must still be byte-equivalent to the user's reference Scribus 1.6.4 exports.
- **Don't remove existing tests.** PR #7's 136 unit tests stay green. Add tests for new pipeline components.
- **`Dockerfile.claude` and `shared/fonts/50-vollkorn-family-alias.conf`** stay as-is — they're how local rendering works. This issue uses them, doesn't redesign them.
- **Don't touch `templates/<id>/baseline.pdf`** (the frozen visual_diff reference). It's still load-bearing for the local visual_diff path.
- **No AI-tool attribution** in commit messages, code, file names, anywhere (per `feedback_no_claude_attribution.md` in user memory).

## Out of scope (recap)

- Anything CI-fonts related (D7)
- Modifying SLA originals
- DSL changes
- New templates
- Authoring contributors who don't have the dev container's font drop zone

## Risks & mitigations

| Risk | Mitigation |
| :--- | :--- |
| Author forgets to re-render after editing a template SLA | `bin/check-stale-previews` is a CI gate; build fails until previews are refreshed and committed |
| `bin/render-gallery` is non-deterministic across runs | Acceptance criterion explicitly requires "twice produces no git diff"; the rendering chain is already proven deterministic at the raster layer (PR #5's verification); just need to make hash recording + file ordering stable |
| Committed preview artifacts bloat the repo over time | At 50 dpi, total preview bytes per release ~ < 5 MB across all 3 templates; acceptable. If templates count grows, revisit (e.g. git LFS) — not in this issue |
| `gallery_build.py` runs in CI and finds missing artifacts → confusing error | Clear error message: "no preview.pdf for <template-id>; run bin/render-gallery locally and commit the result" |
| Maintainer's dev container drifts from the reference container (e.g. Scribus version bump) → renders change subtly | The `Dockerfile.claude` pins Scribus from Debian trixie; rebuilds reproduce the same version. If Debian upgrades trixie, that's a known-time event; rebaselining `templates/<id>/baseline.pdf` follows the procedure documented in `docs/render-fidelity.md` |
| Idempotency check (`twice produces no git diff`) trips on PDF metadata timestamps | The pipeline must either (a) strip non-deterministic PDF metadata after render, or (b) treat such churn as expected and the check should compare structural+visual content, not raw bytes; PR #5 already established raster-equivalence as the standard. Plan should pick (a) for simplicity if feasible. |

## What "done" looks like

All ISSUE.md acceptance criteria, plus:

- The `validate-reproductions` CI step's runtime drops from "several minutes" (rendering) to "under 30 seconds" (sla_diff + stale check).
- The maintainer can edit a template SLA, run one command (`bin/render-gallery`), commit, push, and see the change reflected at vorlagen.gruene.at on next deploy.
- A subsequent CI run on a clean branch passes; a CI run on a deliberate-stale-preview branch fails with the stale-previews error.
- `docs/render-fidelity.md` is the authoritative document for the chosen architecture.

## Notes

- This issue was originally framed as "restore visual_diff in CI" (Option A). After issue #3's wrap-up dialogue with the user, the architecture pivoted to Option B ("CI as pure shipper"). The slug stays as-is to preserve issue-tracking continuity, but the title and scope are now correctly Option B.
- The work this issue introduces is mostly plumbing + scripts. It doesn't change the rendering primitives (Scribus, fontconfig, sla_diff/visual_diff) — those are battle-tested via issue #3.
