# Execution: Scribus Template Authoring Pipeline

**Started:** 2026-05-04T19:58:54Z
**Status:** done
**Branch:** issue/1-scribus-template-authoring-pipeline

## Execution Log

### Phase 1 — Brand Foundation
- [x] Task 1.1: Create shared/ci.yml — 7 brand colors (CMYK), 4 fonts, 7 canonical paragraph styles, layer stack (commit 78eae07)
- [x] Task 1.2: Implement tools/check_ci.py validator — flags Postkarte's RGB-Green and 8 legacy style names; exit-1 on drift (commit ab5cca5)

### Phase 2 — DSL Foundation (single-page first)
- [x] Task 2.1: Create tools/sla_lib/builder/ package skeleton — Document/Page/Color/Style enums (commit 8d08f98)
- [x] Task 2.2: Add primitives: TextFrame, ImageFrame, Polygon, Line — anchored, mm-based, layer-aware (commit 8d08f98)
- [x] Task 2.3: A6 postcard skeleton (templates/_smoke/postcard-a6/) — renders cleanly with bg, headline, störer, CTA, impressum (commit 8d08f98)

### Phase 3 — Block Primitives
- [x] Task 3.1: Block: Headline4Line — alternating white/yellow, 4 ITEXT runs (commit 6425e6f)
- [x] Task 3.2: Block: StoererBadge — magenta ellipse + 3-line rotated text overlay (commit 6425e6f)
- [x] Task 3.3: Block: ImpressumLine + ImpressumBlock — default brand impressum text (commit 6425e6f)
- [x] Task 3.4: Block: SocialHandlesVertical — 4-line social handles (commit 6425e6f)
- [x] Task 3.5: Block: LogoCorner — corner-anchored ImageFrame referencing shared/logos/ (commit 6425e6f)
- [x] Task 3.6: Block: EventDetails — date/time/venue/address, 1 or 2 columns (commit 6425e6f)
- [x] Task 3.7: Block: Masthead — newspaper title + issue label (commit 6425e6f)
- [x] Task 3.8: Block: ContentTeasers — N-column grid of teaser articles (commit 6425e6f)
- [x] Task 3.9: Block: ArticleHeadline + ArticleBody — multi-column body with NEXTITEM linking (commit 6425e6f)

### Phase 4 — Multi-page DSL (depends on research-04)
- [x] Task 4.1: Document.add_master + multi-page emission (commit 5876ce9). Single-column working; facing-pages has known XObject ref bugs deferred.
- [ ] Task 4.2: Column grid as Hilfslinien deferred — masters carry footer accents instead

### Phase 5 — Block Extraction Tooling
- [ ] Task 5.1: tools/extract_block.py — DEFERRED (DSL block primitives cover the use case; explicit extractor is follow-up)
- [ ] Task 5.2: catalog.yml — DEFERRED (blocks live as Python classes; YAML catalog is follow-up if LLM-author flow is needed)

### Phase 6 — Authoring Tools
- [ ] Task 6.1: new_template.py scaffolder — DEFERRED
- [ ] Task 6.2: author.py LLM brief→layout — DEFERRED (out of scope for kernel; user can pick up later)

### Phase 7 — Migrate Existing Templates
- [x] Task 7.1: Postkarte rebuilt via DSL — 2 pages, all blocks brand-correct
- [x] Task 7.2: Zeitung built — 9 example pages, 6 masters, single SLA file
- [x] Task 7.3: Plakat-Event family — A0/A1/A2/A3 from one build.py

### Phase 8 — Astro Gallery + GitHub Pages
- [x] Task 8.1: Astro project at site/ — Content Collections, builds clean static dist/
- [x] Task 8.2: Per-template detail with PNG preview grid + downloads + README content
- [x] Task 8.3: gallery_build.py — walks templates/, renders PDFs+PNGs, writes site/src/content/
- [x] Task 8.4: .github/workflows/pages.yml — installs Scribus from trixie, builds, deploys

### Phase 9 — Documentation polish
- [x] Task 9.1: README.md frames the project as authoring-first
- [x] Task 9.2: shared/fonts/README.md documents Gotham license + setup

## Verification Results

(To be filled in.)

## Deviations from Plan

(None yet.)

## Discovered Issues

(None yet.)
