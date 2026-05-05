# Execution: Scribus Template Authoring Pipeline

**Started:** 2026-05-04T19:58:54Z
**Status:** in_progress
**Branch:** issue/1-scribus-template-authoring-pipeline

## Execution Log

### Phase 1 — Brand Foundation
- [x] Task 1.1: Create shared/ci.yml — 7 brand colors (CMYK), 4 fonts, 7 canonical paragraph styles, layer stack (commit 78eae07)
- [x] Task 1.2: Implement tools/check_ci.py validator — flags Postkarte's RGB-Green and 8 legacy style names; exit-1 on drift (commit ab5cca5)

### Phase 2 — DSL Foundation (single-page first)
- [ ] Task 2.1: Create tools/sla_lib/builder/ package skeleton
- [ ] Task 2.2: Add primitives: TextFrame, ImageFrame, Polygon, Line
- [ ] Task 2.3: First DSL example: A6 postcard skeleton

### Phase 3 — Block Primitives
- [ ] Task 3.1: Block: Headline4Line
- [ ] Task 3.2: Block: StoererBadge
- [ ] Task 3.3: Block: ImpressumLine and ImpressumBlock
- [ ] Task 3.4: Block: SocialHandlesVertical
- [ ] Task 3.5: Block: LogoCorner
- [ ] Task 3.6: Block: EventDetails
- [ ] Task 3.7: Block: Masthead (Zeitung)
- [ ] Task 3.8: Block: ContentTeasers
- [ ] Task 3.9: Block: ArticleHeadline + ArticleBody (multi-column)

### Phase 4 — Multi-page DSL (depends on research-04)
- [ ] Task 4.1: Add Document.add_master() and Document.add_page()
- [ ] Task 4.2: Add column grid + helper guides on master pages

### Phase 5 — Block Extraction Tooling
- [ ] Task 5.1: tools/extract_block.py
- [ ] Task 5.2: shared/blocks/catalog.yml + initial library

### Phase 6 — Authoring Tools
- [ ] Task 6.1: tools/new_template.py
- [ ] Task 6.2: tools/author.py — Markdown brief → Layout-YAML → DSL

### Phase 7 — Migrate Existing Templates
- [ ] Task 7.1: Re-build Postkarte via DSL
- [ ] Task 7.2: Build Zeitung as multi-page DSL skeleton
- [ ] Task 7.3: Plakat family from one DSL

### Phase 8 — Astro Gallery + GitHub Pages
- [ ] Task 8.1: Set up site/ Astro project
- [ ] Task 8.2: Per-template detail page
- [ ] Task 8.3: tools/gallery_build.py
- [ ] Task 8.4: .github/workflows/pages.yml

### Phase 9 — Documentation polish
- [ ] Task 9.1: Update top-level README.md
- [ ] Task 9.2: shared/fonts/README.md

## Verification Results

(To be filled in.)

## Deviations from Plan

(None yet.)

## Discovered Issues

(None yet.)
