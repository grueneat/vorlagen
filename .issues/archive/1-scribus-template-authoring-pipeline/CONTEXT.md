# CONTEXT — Scribus Template Authoring Pipeline

## Captured from interactive discussion (this session)

### What "done" looks like

A small fleet of DSL-built **Scribus 1.6 skeleton templates** + the tooling to generate more. Bezirks- and Landesgruppen visit a GitHub Pages gallery, filter by occasion or format, download a `.sla` (and any required assets), open it in Scribus, and tailor the example content. The DSL plus block library is the engine that lets future templates be created in hours rather than days.

### Key design decisions reached during discussion

1. **Authoring-first, not render-first.** The earlier render-and-fill pipeline (slot JSON → filled SLA → PDF) is a side-product, not the goal. Templates are skeletons for humans to edit in Scribus, *not* fill-targets for scripts. Render pipeline stays as a tool for **preview generation** only (gallery thumbnails, smoke tests).

2. **DSL + LLM, not raw-LLM-XML.** The LLM never emits SLA-XML directly — it emits high-level layout YAML/specs. A typed Python DSL is the only thing that writes XML. This sidesteps the ~3000 LOC of Scribus writer logic, the qHash-unstable ItemIDs, the implicit-by-absence style PARENT inheritance, the qCompress-encoded inline images, and the scratch-space coordinate quirks documented in `.research/01-sla-format.md`.

3. **Multi-page structure: ONE SLA, many master-pages, many example pages.** For newspapers/magazines/folders, a single SLA file with multiple master pages and labeled example pages is preferable to a "pack of separate SLAs." Reasoning: users open one document, navigate the Page Panel, duplicate the variant they want, edit it, delete unused examples. This mirrors how InDesign professionals work.

4. **Plakate are different.** Page size is fixed-per-SLA in Scribus, so a "Plakat-Familie" is multiple SLAs (one per size: A0/A1/A2/A3) generated from one DSL definition. Gallery shows one entry with size selector.

5. **Postkarte/Flyer/Roll-up/Sticker** are single SLAs.

6. **ANNAMEs stay** — but their semantics shift. They are now **human-readable hints** ("Headline 4-zeilig (Brand)") visible in Scribus's Object Properties panel, not pure machine slot identifiers. They still serve as stable handles for any future programmatic operation.

7. **Example content is mandatory.** Empty placeholder frames (the original templates' approach) confuse downstream users. DSL-built skeletons ship with example text like "[Headline – max 4 Zeilen]", lorem ipsum bodies, sample images from `shared/logos/`, all clearly labeled as example content.

8. **Brand is the single source of truth.** `shared/ci.yml` defines colors (CMYK), fonts, and canonical paragraph style names (`ci/headline`, `ci/body-12`, `ci/impressum`, …). Validator flags drift. The current RGB-`Green` color slipped into two of the three existing templates is the canary — Phase 1 deliverable is to flag and fix it.

9. **Iteration discipline.** User explicitly directed: "build small examples with the DSL so you can iterate quickly." Translation: write the smallest possible Document/Page builder that emits an A6 postcard skeleton, render it, verify it opens in Scribus, *then* add multi-page support, *then* add master pages, *then* the rest of the blocks. Do **not** write a 1500-line DSL before the first render works.

10. **Distribution is GitHub Pages + Astro**, per `.research/03-validation-distribution.md`. Lean: Pagefind for search, no SPA. Per-template detail page with PDF preview and download. Family-aware (one card per Plakat family with size selector). For multi-page templates, page-by-page PNG carousel.

### Constraints surfaced

- **Schriftlizenz:** Gotham Narrow & Vollkorn Black Italic are proprietary. Don't commit font binaries to git. Document setup in `shared/fonts/README.md`. The Docker renderer image and contributor machines must have them installed locally.
- **Scribus 1.6.x only.** Don't touch 1.4 / 1.7 format quirks. Emitted SLAs carry `Version="1.6.x"`.
- **Multi-arch container.** arm64 + amd64 must both work (Dockerfile.claude already handles this).
- **Brand spot-color:** Don't convert Brand-Grün to RGB downstream — print pipeline keeps it as a CMYK or spot color.
- **No raw-XML LLM emission.** DSL only.
- **Long-running autonomous session.** User wants finished version by tomorrow. Maintain end-to-end momentum: every 30-60 min should yield a render-able artifact. No long silent stretches.

### Out of scope (explicitly deferred)

- Online configurator on the gallery (web form → backend renderer). User said this is a stretch goal for "Phase D.6" much later.
- AI image generation (FLUX/SDXL) feeding into templates. Manual asset workflow for now.
- Vision-LLM-as-judge in the authoring loop. Stub OK for v0; meaningful judge loop is follow-up work.
- PDF/X-4 conformance and full preflight (veraPDF + pdfcpu + custom rules). The Dockerfile.claude has an opt-in build arg for it but execution is follow-up.
- Visual regression / golden-master diffing. Documented in research; not in the kernel scope.

### Open questions logged but not blocking

- Gotham license — needs human resolution before any public repo push. Doesn't block local development.
- "Approved baseline" PDF for the existing templates — is there an InDesign reference, or do we treat the first DSL output as the baseline? Treat first DSL output as baseline for now; user can upgrade later.
- Whether the gallery needs auth (Cloudflare Pages + Access) or is fully public. Build for public first; auth is a small swap later if needed.

## Pointers to existing material

- `.research/00-synthesis.md` — overall architecture
- `.research/01-sla-format.md` — XML schema deep-dive (every gotcha listed)
- `.research/02-tooling-ecosystem.md` — Scribus toolchain, AI patterns, top-3 recommendations
- `.research/03-validation-distribution.md` — preflight, visual diff, gallery patterns
- `tools/sla_lib/{reader,editor,slot}.py` — already-working SLA reader, editor primitives, 4 passing tests
- `tools/render.py` — proven headless render CLI on arm64
- `Dockerfile.claude` — renderer image extending claude-flow base, multi-arch
- `templates/postkarte-a6-kampagne/` — Postkarte already migrated to ANNAME slots (will be re-baselined to be DSL-built in Phase 7)
