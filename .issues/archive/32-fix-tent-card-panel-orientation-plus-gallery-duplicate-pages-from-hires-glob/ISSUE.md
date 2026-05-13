---
id: '32'
title: Fix tent card panel orientation + gallery duplicate pages from hires glob
status: done
priority: high
labels:
- bug
- templates
- visual-qa
source: github
source_id: 64
source_url: https://github.com/GrueneAT/vorlagen/issues/64
---

## Context

Two regressions surfaced during phone review of the deployed gallery on 2026-05-11:

1. **Tent card (Infostand A5 quer) panel orientation** — when printed and folded into a standing tent (fold up, panels descending to the table), content on one of the two panels reads upside-down. For a horizontally-folded A5 quer (210×148mm, fold at y=74mm), both panels need their content's **top edge at the fold**, not at the outer edges. The panel that flips when folded (call it Panel A, top half of the unfolded sheet) currently has content laid out top-at-outer-edge → upside-down in tent form.

2. **Gallery shows every page twice** — every template's gallery page (e.g., https://grueneat.github.io/vorlagen/templates/kandidat-falzflyer-din-lang/) shows duplicate page tiles. The PDF preview is unaffected. Root cause: `tools/gallery_build.py:91` does `glob("page-*.png")` which matches BOTH the regular `page-01.png` AND the hi-res `page-01-hires.png` files added in #28. No filter was added when hi-res support shipped, so every page appears as two `_previews[]` entries.

## Bug 1: Tent card panel orientation

**Template:** `templates/infostand-tent-card-a5-quer/build.py`
**Format:** A5 quer = 210×148mm landscape, single sheet folded horizontally at y=74mm
**Bug:** content layout assumes "top of page = top of content" for both halves, but the top half flips when folded
**Fix shape:** rotate the top-half content 180° around the fold line. Equivalently: top-half content's `top edge of frames` sits at y=74 (fold), descending to y=0 (table edge); use `rotation_deg=180` on each frame OR recompute y-coordinates to flip the layout.

**Expected after fix:** when printed and folded as a tent (mountain fold, fold at apex), content on both panels reads right-side-up to an observer standing at table level.

## Bug 2: Gallery duplicate pages

**File:** `tools/gallery_build.py:91`
**Bug:** `page_pngs = sorted(tdir.glob("page-*.png"))` matches `page-01.png` AND `page-01-hires.png`
**Fix:** exclude `-hires` variants from the glob:
```python
page_pngs = sorted(p for p in tdir.glob("page-*.png") if not p.stem.endswith("-hires"))
```
Or use a more specific glob pattern (e.g., regex via `glob` + filter).

**Expected after fix:** each template's gallery page shows exactly N tiles for an N-page template. Hi-res files still exist on disk + Astro public mirror for the lightbox click-through to use, just not enumerated as separate pages.

## Acceptance Criteria

- [ ] `tools/gallery_build.py:91` no longer enumerates `-hires` variants as separate pages
- [ ] Unit test for `tools/gallery_build.py` proves the dedup (synthetic template dir with regular + hi-res files → exactly N preview entries)
- [ ] `templates/infostand-tent-card-a5-quer/build.py` lays out content with top-at-fold for both halves
- [ ] Tent card render (`bin/render-gallery` or `python3 templates/infostand-tent-card-a5-quer/build.py`) succeeds; rendered PDF visually demonstrates correct orientation
- [ ] All other template renders remain byte-stable (no collateral damage)
- [ ] `python3 -m unittest discover tools/sla_lib/tests` passes
- [ ] `npm --prefix site run build` succeeds
- [ ] Verified on deployed site: tent card page shows 1 tile (not 2); falzflyer page shows 2 tiles (not 4); etc.

## Out of scope

- Reworking the tent card design beyond the orientation fix
- Adding hi-res-toggle UI to the gallery (lightbox click-through already does this)
- Multi-page tent card variants
- Reworking the gallery preview layout

## Dependencies

#28 (the source of bug #2), #29/#30/#31 (all merged; no conflict expected).

## Priority

High — bug #2 affects every template page on the live gallery; bug #1 makes the tent card unprintable.
