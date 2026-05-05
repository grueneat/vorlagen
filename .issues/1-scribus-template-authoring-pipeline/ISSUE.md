---
id: '1'
title: Scribus template authoring pipeline
status: done
priority: high
labels:
- foundation
- dsl
- authoring
- gallery
---

## Goal

Build the tooling and processes to **author new Scribus templates** for the Grünen NÖ. The output is well-structured **skeleton SLA files** (with example content, named slots, brand-correct styles, helper guides) that other people open in Scribus, customize, and use. The finished templates are published on a **GitHub Pages gallery** for distribution to local groups.

This issue is the **foundation kernel** for that authoring system — once it's done, adding new templates is a hours-not-days affair.

## Context (from prior research)

Three existing templates live in the repo root: `Postkarte Vorlage.sla` (A6, 2 pages), `Plakat A1 Hochformat_Vorlage.sla` (A1 single page), `Grüne Zeitung Vorlage Scribus.sla` (A4, 14 pages). All Scribus 1.6.5, share brand colors (Dunkelgrün/Gelb/Hellgrün/Magenta + Black/White), Gotham Narrow + Vollkorn Black Italic fonts.

Detailed research and architecture docs already exist:
- `.research/00-synthesis.md` — overall plan
- `.research/01-sla-format.md` — SLA XML schema deep-dive
- `.research/02-tooling-ecosystem.md` — Scribus toolchain comparison
- `.research/03-validation-distribution.md` — preflight, visual diff, gallery patterns
- `tools/sla_lib/` — already has reader, slot model, basic editor (with passing tests)
- `tools/render.py` — headless render CLI proven working on arm64
- `Dockerfile.claude` — renderer image extending claude-flow base

The render-and-fill pipeline shipped earlier is **not** the goal. The user wants templates as **editable skeletons** that designers and local chapters open and modify, not auto-filled outputs.

## Scope

This is one large coordinated piece of work. **Build it iteratively with small DSL examples to validate each step before scaling.** Don't go silent for hours — produce a working artifact every 30-60 min and check it renders.

### Phase 1 — Brand Foundation
- `shared/ci.yml`: single source of truth for brand (CMYK colors, font names, canonical paragraph style names like `ci/headline`, `ci/body-12`, `ci/impressum`)
- `tools/check_ci.py`: validator that flags brand drift (e.g. the existing RGB `Green` in two templates instead of CMYK)

### Phase 2 — Block Library
- Extract reusable blocks from the three existing SLAs as standalone SLA fragments + metadata in `shared/blocks/<category>/<id>.sla` plus `shared/blocks/catalog.yml`
- Minimum block set (extract from Postkarte first as it's smallest):
  - `content/headline-4line-alt` (alternating white/yellow Brand-Headline)
  - `content/stoerer-badge` (pink badge with 3-line text)
  - `footer/impressum-line` (one-liner)
  - `footer/impressum-block` (multi-line)
  - `footer/social-handles-vertical`
  - `header/masthead-zeitung` (from the Zeitung)
  - `content/article-3col-grid`
- `tools/extract_block.py`: select frames by ANNAME or position from a source SLA, save as block fragment
- `tools/insert_block.py`: place a block on a target SLA at a position, remap style refs and ItemIDs

### Phase 3 — SLA DSL (the core deliverable)
Typed Python API that emits valid Scribus 1.6 SLA XML. Hides the painful stuff (ItemID generation, gXpos/gYpos consistency, style PARENT refs, scratch-space coords, soft-hyphen handling, breakline insertion).

Capabilities required:
- `Document(title, template_id)` with brand stylesheet auto-loaded from `shared/ci.yml`
- `Page(size="A4"|"A1"|"A2"|"A5"|"A6"|custom_mm, orientation, bleed_mm)`
- `add_master(name, ...)` — define master pages with column grids, header positions, etc.
- `add_page(master=..., label="Beispiel: ...", content=[...])` — example pages with human-readable labels visible in Scribus's Page Panel
- Block primitives: `LogoCorner`, `Headline4Line`, `StoererBadge`, `ImpressumLine`, `EventDetails`, `SocialHandles`, `ArticleHeadline`, `ArticleBody`, `QuoteSidebar`, `ContentTeasers`, `Masthead`, `ImageFrame`, `TextFrame`
- Each block:
  - Carries example content visible in Scribus (e.g. `[Headline – max 4 Zeilen]`)
  - Tags frames with ANNAME = human-readable hint (`"Headline 4-zeilig (Brand)"`, not just `text:headline`)
  - Applies CI paragraph styles by reference, never inlines
- `Color`, `Style`, `Layer` enums tied to `shared/ci.yml`
- Helper guides: optional Scribus guides at column edges and key element positions
- Layer organization: `Hintergrund`, `Bilder`, `Text`, `Hilfslinien` (Hilfslinien hidden by default)

**Iteration discipline:**
1. Build smallest possible DSL surface that produces a one-page A6 postcard skeleton
2. Render it, open in Scribus (or at least render to PDF and visually verify), confirm structure is sane
3. Add multi-page support, render Zeitung-style smoke
4. Add master-pages, render multi-master smoke
5. Only then scale to all blocks

### Phase 4 — Authoring Workflow Tools
- `tools/author.py briefing.md` — takes a Markdown brief, calls Claude, gets layout YAML, builds SLA via DSL, renders preview
- Brief format example saved as `templates/_briefings/example-rollup-mahnwache.md`
- Vision-judge feedback loop (optional v0 — can be a stub that just outputs the rendered preview for human review)
- `tools/new_template.py` — interactive scaffold: page size + orientation + format type, produces `templates/<id>/template.sla` skeleton ready for human polish

### Phase 5 — Multi-page Newspaper Model
- Migrate `Grüne Zeitung Vorlage Scribus.sla` to the new authoring model:
  - Define 5+ master pages (`master-rechts-3col`, `master-links-3col`, `master-titel`, `master-foto-spread`, `master-impressum`)
  - 8-10 example pages each labeled "Beispiel: <variant>" so users see options in the Page Panel
  - Single SLA file (per the user's preference for one large multi-page document)
- `templates/zeitung-a4-grun/template.sla` is the authoritative output

### Phase 6 — Plakate Family
- Migrate Plakat A1 to family pattern
- Render same design at A0/A1/A2/A3 by parameterizing on `Page(size=...)` and rerunning DSL
- `templates/plakat-event/{a0,a1,a2,a3}.sla`
- `meta.yml` describes the family, gallery shows one entry with size selector

### Phase 7 — Postkarte Migration to DSL
- Postkarte was already migrated to ANNAME slots earlier — refactor to be DSL-built so editing the DSL regenerates it
- Validate the regenerated SLA is visually identical to the existing `templates/postkarte-a6-kampagne/template.sla`

### Phase 8 — Astro Gallery on GitHub Pages
- `site/` — Astro site with Content Collections from `templates/*/meta.yml`
- Per-template detail page: PDF preview, page-by-page PNG carousel for multi-page templates, download button, brand quickstart, "how to use" instructions
- Family handling: one card per family with size selector
- Filter UI: by format (A0…A6, custom), by occasion (event/Mahnwache/Wahl/Allgemein), by language
- GitHub Action workflow `pages.yml`: on push to main, render preview PDFs+PNGs for all templates, build Astro, deploy to Pages
- Keep the gallery lean — Pagefind for search, no SPA overhead

## Acceptance Criteria

- [ ] `shared/ci.yml` exists, `tools/check_ci.py` flags the existing RGB `Green` inconsistency in the source templates
- [ ] At least 6 reusable blocks extracted to `shared/blocks/`; `shared/blocks/catalog.yml` documents them
- [ ] DSL produces a brand-correct one-page A6 postcard skeleton (`templates/_smoke/postcard-a6/template.sla`) that opens cleanly in Scribus and renders to PDF without errors
- [ ] DSL produces a brand-correct multi-page A4 newspaper skeleton with at least 3 master pages and 6 example pages
- [ ] `templates/zeitung-a4-grun/template.sla` exists as a single multi-page DSL-built SLA, replaces the original Zeitung Vorlage as the canonical newspaper authoring template
- [ ] `templates/plakat-event/` family contains A0/A1/A2/A3 SLAs from one DSL definition
- [ ] `templates/postkarte-a6-kampagne/` is regenerable from DSL (DSL+meta.yml in repo, SLA is build artifact OR committed and verified by smoke test)
- [ ] `tools/author.py` accepts a Markdown brief and produces a renderable skeleton SLA. At least one example brief and resulting SLA in repo
- [ ] Astro site builds locally with all templates listed, each detail page shows preview PDF and download link
- [ ] `.github/workflows/pages.yml` renders previews and deploys the Astro build (workflow exists; actual deploy depends on user-side GitHub repo creation, that's fine)
- [ ] Unit tests cover the DSL XML emission, block extraction/insertion, ci.yml validator. All green.
- [ ] `README.md` updated to reflect the authoring-first model. Old render-pipeline language removed/repositioned as "preview rendering".

## Constraints

- **Brand fonts** (Gotham Narrow, Vollkorn Black Italic) are proprietary. Do **not** commit font binaries to git — assume they are installed on the Docker image and on contributor machines. Document setup in `shared/fonts/README.md`.
- **Scribus 1.6.x** is the target. Keep `Version="1.6.x"` in emitted SLAs. Do not touch 1.4 or 1.7 format quirks.
- **Multi-arch container**: builds must work on arm64 and amd64.
- **No raw SLA-XML emission by LLM**: the DSL is the only XML emitter. LLM only produces YAML/JSON layout specs that the DSL consumes.
- **Iteration discipline**: small DSL examples first, render and verify each, then scale. Do not write 1000 lines of DSL before the first render works.
- **Output must be Scribus-friendly**: opens cleanly, ANNAMEs are human-readable hints, example content visible in frames, brand styles loaded even if unused, helper guides on a hidden Hilfslinien layer.

## Notes & Pointers

- Format-XML pitfalls documented in `.research/01-sla-format.md`: PAGEOBJECTs are siblings of PAGE (not children, linked via `OwnPage`), `ItemID` is qHash-unstable, `XPOS/YPOS` are scratch-space, style `PARENT` inheritance is implicit-by-absence, inline images are base64-of-qCompress.
- Tooling decisions documented in `.research/02-tooling-ecosystem.md`: Scribus + DSL + LLM-orchestration is the recommended path; Typst/LaTeX are out for now.
- Distribution patterns documented in `.research/03-validation-distribution.md`: Astro + Pagefind for the gallery, golden master + visual diff is a follow-up.
- `tools/sla_lib/` already has working reader/editor primitives — extend, don't rewrite.
- The user explicitly wants long-running autonomous work toward a finished version by tomorrow. Prioritize end-to-end momentum (render-able artifacts at each step) over polish.
