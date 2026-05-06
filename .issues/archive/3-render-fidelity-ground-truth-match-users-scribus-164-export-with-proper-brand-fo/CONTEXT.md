---
issue: 3-render-fidelity-ground-truth-match-users-scribus-164-export-with-proper-brand-fo
phase: discuss
date: 2026-05-06
---

# CONTEXT — Render-fidelity ground truth

## What this issue actually delivers

The dev-container's headless Scribus pipeline now renders each of the three originals (`Grüne Zeitung Vorlage Scribus.sla`, `Plakat A1 Hochformat_Vorlage.sla`, `Postkarte Vorlage.sla`) **byte-identically** to the user's Scribus 1.6.4 desktop export, after this issue's setup work. The remaining structural work is:

1. Persist the font + ICC install into `Dockerfile.claude` so future container rebuilds reproduce this state automatically.
2. Regenerate the committed `templates/<id>/baseline.pdf` files using the now-correct rendering env so the DSL→render→baseline diff pipeline (PRs #3/#4/#5) measures against truthful baselines instead of font-substituted ones.
3. Document the rebaselining workflow in `docs/render-fidelity.md`.
4. Adopt `originals/` at workspace root as the canonical SLA + reference-PDF location, retire the duplicated `*-original.sla` paths.

## Investigation summary (already completed manually)

This was an iterative diagnostic that found four distinct causes of drift, each fixed:

### Drift cause 1: brand fonts not installed (~55,000 px/page initially)
- Original headless render used DejaVu Sans for everything (Gotham/Vollkorn missing).
- User has the proprietary `Gotham Narrow` family + open-OFL `Vollkorn`, dropped them into `/root/workspace/fonts/`.
- We installed all 16 Gotham Narrow `.otf` files + the static `Vollkorn-BlackItalic.ttf` into `/root/.local/share/fonts/gruene/`, ran `fc-cache`.
- A fontconfig alias rewrites Scribus's lookup of `Vollkorn Black Italic` (which the SLA references as a family) to the actual font's `Vollkorn / Black Italic` family+style identity.

### Drift cause 2: SLA `FONTSIZE="11.7"` typo (~233,000 px on 4 pages)
- The Zeitung SLA's body text on pages 5/6/8/10 had `FONTSIZE="11.7"`, an oversight by the original author (likely a mouse-wheel nudge in Scribus's properties panel).
- User's Scribus 1.6.4 PDF/X-4 export silently rounds `FONTSIZE="11.7"` → `Tf 11.00000` in the output PDF; our Scribus 1.6.3 honors the SLA value as-is.
- User identified it as an oversight, fixed all 55 ITEXT occurrences in their Scribus, re-exported the SLA. Drift collapsed to 0 on those pages.
- Remaining 42 `FONTSIZE="11.7"` strings in the SLA file are inside STYLE definitions, dormant (no ITEXT references them) — left as-is, no rendering impact.

### Drift cause 3: Vollkorn variable-font metric mismatch (~7,000 px on 3 pages)
- Originally we used Google Fonts variable Vollkorn (`Vollkorn-Italic[wght].ttf`) as the source for "Vollkorn Black Italic" — its glyph metrics differ from the static-instance Vollkorn the user has on macOS.
- User dropped their exact `Vollkorn-BlackItalic.ttf` into `fonts/Vollkorn/static/`. We swapped to that file. Drift collapsed.

### Drift cause 4: color-profile substitution warnings (cosmetic, no measured drift impact)
- SLA references `Adobe RGB (1998)` and `PSO Uncoated ISO12647 (ECI)` ICC profiles; this container has neither.
- Scribus substitutes with `sRGB display profile (ICC v2.2)` and `ISO Coated v2 300% (basICColor)` respectively.
- User's macOS export presumably has the same substitution warning (their Scribus also can't find these profiles by default), so the substitution is symmetric and produces byte-identical output.
- Future work (out of scope for this issue) could install ECI profiles for full PDF/X-4 compliance; not needed for visual fidelity.

## Decisions (locked in via discuss step)

### D1 — `FONTSIZE=11.7` was an oversight; SLA already corrected
**Status: resolved.** The user's Scribus session corrected all 55 ITEXT occurrences across pages 5/6/8/10 of the Zeitung SLA. All renders now byte-identical.

The committed SLA at workspace root (`gruene-zeitung-vorlage-original.sla`) is now stale (still has the typo); needs to be replaced with `originals/Grüne Zeitung Vorlage Scribus.sla` (corrected version).

### D2 — Brand fonts live in `/root/workspace/fonts/` (gitignored), installed at container-build time
- `fonts/Gotham Narrow/<weight>/<weight>.otf` — 16 .otf files across all weights
- `fonts/Vollkorn/static/Vollkorn-BlackItalic.ttf` — the specific static instance the user has
- `fonts/Vollkorn/static/Vollkorn-*.ttf` — full Vollkorn family, available in case future templates use other weights
- `.gitignore` now blocks `fonts/`, `*.otf`, `*.ttf`, `*.ttc` so the proprietary Gotham never leaks into the public repo. Vollkorn (OFL) is also gitignored for consistency, with the reference store being the user-controlled `fonts/` directory.

The Dockerfile.claude work in this issue's execute step will:
- COPY the staged fonts (when present) into `/usr/local/share/fonts/gruene/`
- Run `fc-cache -f`
- Install the fontconfig alias for `Vollkorn Black Italic → Vollkorn / Black Italic`
- Sanity-probe with `fc-list | grep -iE 'gotham narrow|vollkorn'` → fail-loud if missing
- Use a bind-mount or build-arg pattern so the build context can be either "fonts present" (local dev) or "fonts absent" (CI without the private channel) without breaking the build

### D3 — Scribus 1.6.3 (Debian arm64) is the canonical render engine for this container
Originally suspected as a version-floor issue (user has 1.6.4, no arm64 build of 1.6.4/1.6.5 exists). Turned out to be irrelevant once D1 was fixed — both Scribus versions render integer FONTSIZE values identically. No need to chase 1.6.4 on aarch64.

If a future Scribus version introduces a real text-engine difference, the rebaselining workflow (D5) handles it.

### D4 — `originals/` is the canonical SLA + reference-PDF location
The originals at workspace root (`gruene-zeitung-vorlage-original.sla`, `plakat-a1-hochformat-original.sla`, `postkarte-vorlage-original.sla`) duplicate what's now in `originals/` with the umlaut filenames (and they're stale — the SLAs in `originals/` have D1's fix). Execute step removes the duplicates and updates references in `templates/<id>/meta.yml` (the `original_sla:` keys) plus `bin/validate` to read from `originals/`.

The user's reference PDF exports (`originals/Grüne Zeitung Vorlage Scribus.pdf`, `originals/Plakat A1 Hochformat_Vorlage.pdf`, `originals/Postkarte Vorlage.pdf`) are committed alongside the SLAs as the canonical "what gallery output should look like" reference.

### D5 — Regenerate `templates/<id>/baseline.pdf` from the corrected SLAs in this container's font-installed env
The current committed baselines were rendered without fonts (Apr/May before this issue). They need to be replaced with fresh renders from the canonical `originals/<>.sla` files using the new font setup. After regeneration:
- Each `templates/<id>/baseline.pdf` = render of the original SLA with proper fonts
- `bin/validate` measures DSL `template.sla` output against this new baseline (PR #5's standard: ≤3 px Qt-internal anti-aliasing floor)
- The new baseline is also byte-equivalent to the user's reference PDF in `originals/<id>.pdf` (proven: 0 px on all 17 pages today)

### D6 — Document the rebaselining workflow in `docs/render-fidelity.md`
Topics:
- Why fonts must be installed before rendering (DejaVu fallback drift)
- The fontconfig alias for Vollkorn Black Italic family-name resolution
- The "fix typos at the SLA source, not the renderer" principle (D1 lesson)
- How to add a new font to `fonts/` (drop file → rebuild container → render works)
- How to rebaseline `templates/<id>/baseline.pdf` (manual, gated procedure — not casual)
- How to verify a new SLA render matches your desktop Scribus export
- Out-of-scope items (ECI ICC profiles, CI font provisioning) and where they're tracked

### D7 — CI font provisioning is OUT of scope for this issue
Per user direction ("for now I only care about the local rendering and fixing"). CI's `validate-reproductions` step (added in PR #5) currently runs without fonts → DSL→baseline diff still works (both sides identically font-less), but the rendered output is DejaVu. Acceptable for measuring DSL→baseline equality; not acceptable for what's served at vorlagen.gruene.at.

A separate follow-up issue will tackle private-source font provisioning for CI (private GitHub repo + secret, S3 + creds, or similar). Tracked in the issue's "Out of Scope" section.

## Constraints

- **DO NOT edit `originals/*.sla` files in this issue's execute work.** D1's fix was made by the user in their Scribus desktop. Future SLA fixes follow the same pattern (user edits + commits). The render pipeline never mutates source SLAs.
- **DO NOT bundle Gotham Narrow into the repo at any path.** Gitignore blocks it; commits should be reviewed for `*.otf`/`*.ttf` slip-ins.
- **Keep PR #5's `bin/validate` standard.** DSL→baseline ≤3 px per template at 150 dpi (Qt anti-aliasing floor verified deterministic).
- **Honour the existing `templates/<id>/build.py` + `template.sla` — DSL outputs are unchanged in this issue.** This issue corrects the *baseline* side of the comparison, not the DSL side.

## Out of scope (recap)

- Bundling Gotham Narrow into the public repo (license-blocked)
- CI font provisioning (separate follow-up issue)
- ECI ISO Coated v2 / PSO Uncoated ICC profile install (cosmetic — substitutes are symmetric across desktop and container)
- Migrating off Scribus / replacing the rendering toolchain
- Generic gallery-image quality optimization (separate concern)
- Building Scribus 1.6.4 from source on arm64 (no longer needed since D1 was fixed)

## Risks & mitigations

| Risk | Mitigation |
| :--- | :--- |
| Future SLA edits reintroduce fractional FONTSIZE (regressing D1) | Add a sanity check to `bin/validate` or a pre-commit hook: `grep 'FONTSIZE="[0-9]*\.[0-9]\+"' originals/*.sla` and warn |
| Dockerfile font install silently no-ops in builds without fonts/ in context | Keep `fc-list` sanity probe loud; document that font-less builds produce DejaVu renders |
| Vollkorn variable vs static distinction trips up future contributors | Document in `docs/render-fidelity.md` why static `Vollkorn-BlackItalic.ttf` is required (Scribus's family-name matching), with the fontconfig alias snippet |
| Re-baselined PDFs differ from currently-committed baselines, breaking the DSL→baseline diff in PR #5's CI step temporarily | Single atomic commit replaces all three `baseline.pdf` files together; CI validates against the new triplet |
| User re-exports SLAs with future Scribus versions and rendering drifts | Documented rebaselining procedure (D6) makes the user-driven correction explicit |

## What "done" looks like

All ISSUE.md acceptance criteria, plus:

- Verified: `originals/<>.sla → headless render = originals/<>.pdf` byte-identical at strict 0% fuzz for all 17 pages of all 3 templates ✓ (already passing — established during discuss)
- `Dockerfile.claude` builds and the resulting image has Gotham Narrow + Vollkorn correctly installed (`fc-list | grep` shows expected count)
- `templates/<id>/baseline.pdf` files regenerated; `bin/validate` exits 0 with worst-page mismatch ≤3 px per template
- `docs/render-fidelity.md` exists and documents the chain
- Workspace-root duplicate `*-original.sla` files removed; `templates/<id>/meta.yml` and `bin/validate` reference `originals/<>.sla`
- `.gitignore` correctly blocks `fonts/` and font-extension globs
- Issue branch ships as a single PR; merge brings the corrected ground truth onto main
