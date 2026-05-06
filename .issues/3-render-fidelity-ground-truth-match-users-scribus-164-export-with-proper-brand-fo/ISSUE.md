---
id: '3'
title: 'Render-fidelity ground truth: match user''s Scribus 1.6.4 export with proper
  brand fonts'
status: done
priority: high
labels:
- rendering
- fonts
- validation
- fidelity
source: github
source_id: '6'
source_url: https://github.com/GrueneAT/vorlagen/issues/6
---

## Goal

Make the build pipeline (local + CI) produce PDFs from the original SLAs that are byte-equivalent (or visually indistinguishable) from the user's direct Scribus-1.6.4-with-proper-brand-fonts export. The user just dropped `gruene-zeitung-vorlage-original.pdf` (1.32 MB, Scribus 1.6.4) at the repo root as ground truth. Today's headless rendering on Scribus 1.6.3 with DejaVu fallback differs by 55,257 pixels on page 1 alone (~2.2% of the page) — entire body text + logo + störer badge + headline differ in glyph rendering.

Same gap applies to plakat-a1-hochformat and postkarte-a6-kampagne — `samples-output/originals/{plakat-a1,postkarte}-original.pdf` are likely earlier user exports that should be diffed and matched too. User flagged that "Selbe problem existiert auch bei dem plakat und vielleicht der postkarte."

## Why

PRs #3, #4, #5 drove the DSL→render→baseline diff to ~3 pixels per template. But the baselines themselves were rendered headless on this machine without proper fonts, so they match each other in an internal echo chamber, not the actual production output users see and print. The Pages site at vorlagen.gruene.at thus serves preview PDFs that diverge from real Scribus output. Without a true ground truth, the entire reproduction-faithfulness story is rhetorical.

## Scope

1. Inventory user-supplied PDFs at repo root and `samples-output/originals/`. Establish the canonical ground-truth PDF for each of: zeitung-a4-grun, plakat-a1-hochformat, postkarte-a6-kampagne. (Zeitung is confirmed: `gruene-zeitung-vorlage-original.pdf` at root.)

2. Identify Scribus version delta. User exports from 1.6.4; our AppImage is 1.6.5 in the workflow but 1.6.3 was used for the committed baselines. Decide which version is the canonical render target — probably 1.6.4 to match user; investigate whether 1.6.5 is byte-equivalent to 1.6.4 for these documents.

3. Source the brand fonts the originals reference:
   - Gotham Narrow Book / Bold / Black / Ultra / Ultra Italic — proprietary (Hoefler & Co.)
   - Vollkorn Black Italic — open license (OFL)

   Vollkorn we can install unconditionally. Gotham Narrow needs the user to provide font files via a private source (private GitHub repo + PAT, S3 + creds, or local mount). Document the path; do not commit Gotham files to the public repo.

4. Wire font + ICC profile installation into:
   - Local dev container (`Dockerfile.claude`) — fetch fonts from the private source
   - CI workflow (`.github/workflows/pages.yml`) — same fetch with secret-protected creds
   - Runtime sanity check: `fc-list | grep -iE "gotham narrow|vollkorn"` should report 5 lines; fail the build loudly if not (no silent DejaVu substitution)

5. After fonts are in place, re-render `gruene-zeitung-vorlage-original.sla` headless on this pipeline and pixel-diff against the user's PDF. Iterate on environment differences (font subsetting flags, color profile, PDF version, kerning/hinting settings) until the diff is zero or near-zero.

6. Once the original SLA renders to byte-equivalent of the user's PDF: regenerate `templates/<id>/baseline.pdf` with the new pipeline; that becomes the new committed ground truth. Re-run the existing DSL→render validation (PR #5 closed at 3 pixels mismatch); confirm the DSL output also matches the new baseline (it should, since the SLA changes are identical — just better fonts).

7. Repeat for plakat and postkarte.

8. Decide what to do with old commits: the existing `templates/*/baseline.pdf` files are the artifacts of the wrong pipeline. They get replaced; document that re-baselining was a one-time correction, not a precedent for casual re-baselining.

## Acceptance Criteria

- [ ] User-supplied ground-truth PDF for each of the three templates is in the repo, in a documented location
- [ ] Brand fonts (Gotham Narrow + Vollkorn) install in local dev container and CI from a license-clean source
- [ ] `fc-list | grep -iE "gotham narrow|vollkorn"` reports the expected 5 lines after install; missing fonts fail the build with a loud error
- [ ] Headless render of each `*-original.sla` matches the user's exported PDF: pixel diff < 0.01% per page at 150 dpi
- [ ] Each `templates/<id>/baseline.pdf` is regenerated with the new pipeline and committed
- [ ] Existing DSL→render→baseline diff stays at ≤3 pixels per template (PR #5's standard) after re-baselining
- [ ] Documentation: `docs/render-fidelity.md` describes the font/ICC pipeline, where Gotham Narrow comes from, and the rebaselining procedure for future Scribus version bumps
- [ ] CI's `validate-reproductions` step exercises the full chain end-to-end; deploy blocks on any per-page mismatch > 0.01%

## Out of Scope

- Bundling Gotham Narrow into the public repo (license-blocked)
- Migrating off Scribus / replacing the rendering toolchain
- Generic gallery-image quality optimization (separate concern; covered by the dpi-reduction follow-up if pursued)

## Notes / Pointers

- User's ground-truth Zeitung PDF: `/root/workspace/gruene-zeitung-vorlage-original.pdf` (1.32 MB, Scribus 1.6.4)
- Possible older user exports: `/root/workspace/samples-output/originals/{plakat-a1,postkarte,zeitung}-original.pdf` (May 4, ~580 KB / ~475 KB / ~1.28 MB)
- Current headless render entry point: `tools/visual_diff.py::render_sla_to_pdf` and `tools/_export_pdf.py`
- Current AppImage: Scribus 1.6.5 (per `.github/workflows/pages.yml`), but the existing baselines were rendered with 1.6.3 — version drift to investigate
- Brand-font README documents the install procedure: `shared/fonts/README.md`
- Diagnostic harness command: `pdftoppm -r 96 user.pdf user && pdftoppm -r 96 ours.pdf ours && compare -metric AE -fuzz 5% user-01.png ours-01.png diff.png`
- The user explicitly asked for issue skills to drive this; expect `/issue:work` to follow.
