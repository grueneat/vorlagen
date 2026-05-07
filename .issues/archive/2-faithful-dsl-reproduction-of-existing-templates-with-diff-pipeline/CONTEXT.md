---
issue: 2-faithful-dsl-reproduction-of-existing-templates-with-diff-pipeline
phase: discuss
date: 2026-05-05
---

# CONTEXT — Faithful DSL reproduction with diff pipeline

## What this issue actually delivers

A round-trip-validated DSL: every existing template (Postkarte A6, Plakat A1, Grüne Zeitung A4) is rebuilt in the DSL such that the rebuilt SLA is **structurally equivalent** to the original (modulo volatile fields) and renders to a PDF that is **visually within tolerance** of a frozen baseline. Validation runs in CI and blocks deploy on drift.

The Phase-1 templates currently shipped on the gallery are layout-wise unrelated to the originals. They are placeholders. After this issue, the gallery serves the faithful reproductions, originals are removed from the gallery output (kept in repo at workspace root only as the diff baseline).

## Decisions (locked in via discuss step)

### D1 — Equivalence target: semantic, not byte-level
Diff target is "the rebuilt SLA renders to the same layout/content as the original" up to documented tolerances:

- **ItemID** is renumbered sequentially on both sides before compare.
- **XML attribute order** is meaningless; sort attributes before compare.
- **Float precision**: round to 6 decimals before compare.
- **PAGEOBJECT order** sorted by `(OwnPage, YPOS, XPOS)` for stable ordering.

Pure byte equality is impossible (Scribus rewrites attribute order on every save). The phrase "byte-equivalent" in the issue title is rhetorical; the binding spec is the structural-diff in section C of ISSUE.md.

### D2 — Converter emits typed DSL, not `raw_attrs` escape hatch
The converter (`tools/sla_to_dsl.py`) must produce `build.py` files that use **typed DSL primitives only**. No `raw_attrs={}` dictionaries leaking through.

This means:

- Every Scribus attribute the converter encounters in the three originals must have a typed counterpart in the DSL — either an existing kwarg or a new one added in Phase B.
- If the converter encounters something the DSL cannot express, the converter raises (per D6 — strict mode); we then extend the DSL and re-run.
- `raw_attrs` is **not** part of the public DSL surface introduced by this issue. It can exist internally for the converter→DSL handoff but is not the documented authoring API.

Tradeoff accepted: slower to first green run; cleaner DSL surface long-term; forces us to discover and name every Scribus concept the originals use.

### D3 — Visual baseline is committed PDFs, frozen now
For each original SLA we render its PDF **once, locally, with the current Scribus 1.6.5 toolchain**, and commit the PDF into the repo at e.g. `templates/<id>/baseline.pdf`. From that point forward:

- `visual_diff` always compares the DSL build against the committed `baseline.pdf` (not against a re-render of the original SLA).
- If a future Scribus version renders the same SLA differently, our diff fails — which is the desired signal, not a normalisation target.
- Re-baselining is an explicit human action (delete `baseline.pdf`, regenerate, commit), not an automatic process.

This is stronger than "render both at CI time": it pins the rendering toolchain itself.

### D4 — CI runtime budget
- **Local** (`make validate` or similar): 150 dpi rasters, full coverage.
- **CI**: 96 dpi rasters, runs on every push to main and on PRs touching `tools/`, `templates/`, `shared/`.
- Acceptable runtime: ~5 minutes for the full validation step.

### D5 — Gallery output: only the DSL-built reproductions
- `templates/<id>/template.sla` (DSL-built) is what the gallery offers for download.
- The originals (`*-original.sla` at workspace root) stay in the repo as the diff baseline, but are **not** copied into `site/public/` and **not** referenced from the gallery pages.
- After this issue, every download a user gets from the gallery is the DSL output; no originals leak through.

### D6 — Strict converter
The converter raises a typed exception on any unhandled element/attribute it encounters in the originals. Better to fail loudly and prompt a DSL extension than to silently emit a `build.py` that renders something subtly different.

## Constraints

- **Existing code must be extended, not rewritten.** The DSL package at `tools/sla_lib/builder/` and the reader at `tools/sla_lib/reader.py` are the load-bearing modules; this issue grows them.
- **The three originals are immutable.** No edits to `*-original.sla` files at workspace root for any reason. They are the ground truth.
- **No font/ICC changes.** Bundling fonts and color profiles is a separate, deferred issue. Reproductions assume the same fonts the originals already reference.
- **Headless rendering pipeline is fixed**: `xvfb-run -a scribus -g -ns -py tools/_export_pdf.py <sla> <pdf>`. This is what produces all baselines and all CI renders.
- **The Zeitung is the hardest.** 14 pages, 146 frames, multi-column text flow, 2 master pages, NEXTITEM/BACKITEM linked frames. If reproduction works for the Zeitung, it works for the others.

## Out of scope (carried over from ISSUE.md)

- Bundled fonts and ICC profiles
- LLM authoring tooling
- Block-extraction tools
- Visual-regression baseline-blessing UI

## Risks & mitigations

| Risk | Mitigation |
| :--- | :--- |
| DSL extensions become a long tail (each original surfaces new Scribus features) | Strict converter forces explicit completion; we count remaining gaps after each pass |
| Baseline PDF + Scribus 1.6.5 means any future Scribus upgrade breaks CI | That's the intended signal; re-baselining is explicit. Doc the procedure in README. |
| Visual diff false positives from font hinting / sub-pixel jitter | 96 dpi CI + per-template tolerance config (`templates/<id>/diff.yml`) for legitimate fuzz |
| Linked text frames (NEXTITEM/BACKITEM) get reordered or break | Converter must emit chains in original order; sla_diff verifies chain topology, not just frame presence |
| Soft-hyphens (`\xad`) get stripped by intermediate string handling | Reader and DSL both pass them through verbatim; tests assert presence in round-trip |
| CI runtime balloons past 5 min on the Zeitung | 96 dpi cap; if still too slow, parallelise per-template; last resort: visual_diff only on PRs that touch templates |

## What "done" looks like

All ISSUE.md acceptance criteria, plus:

- `templates/<id>/build.py` exists for all three IDs; running `python build.py` produces a `template.sla` whose `sla_diff` against the original is clean.
- `templates/<id>/baseline.pdf` is committed; `visual_diff` against it is < 1% per page.
- `make validate` (or equivalent) runs the full pipeline locally.
- CI's `validate-reproductions` step is green on `main`; pages-deploy depends on it.
- The DSL has typed expressions for every concept used in the originals; no `raw_attrs` escape hatches in user-visible API.
- The site at `vorlagen.gruene.at` (currently `/vorlagen/`) serves the DSL-built templates only.
