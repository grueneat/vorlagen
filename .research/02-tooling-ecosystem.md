# Tooling Ecosystem for an Automated Template/Publication Pipeline

Research date: 2026-05-04
Use case: party prints physical media (newspaper, posters, postcards), templates kept in git, edited via Scribus GUI and programmatically, rendered headlessly in CI, AI-assisted content/layout fill.
Scope artifacts in repo: `Grüne Zeitung Vorlage Scribus.sla`, `Plakat A1 Hochformat_Vorlage.sla`, `Postkarte Vorlage.sla`.

---

## A. Native Scribus automation

### A.1 Headless CLI rendering

Scribus exposes a `--no-gui --python-script script.py` invocation that runs a script and exits. Variant `-g -py script.py -- args` is shown in community Docker examples. Pass-through args after `--` are visible in the script via `sys.argv`.

The catch: even with `--no-gui`, Scribus still initializes Qt, which on Linux requires an X server. Headless servers / CI runners must wrap Scribus in **Xvfb** (`Xvfb :99 -screen 0 1024x768x16 &`, then `DISPLAY=:99 scribus -g ...`). A long-standing bug (Mantis #14284, "Can't run script on commandline on server without X running") confirms this is the only reliable pattern. There is an official Scribus CI Docker image (`gitlab.com/scribus/scribus-ci-docker`) and community Dockerfiles wrap Xvfb + Scribus + Python.

Stability notes: Scribus 1.6.x is the current stable line. 1.6.4 (April 2025) added new Scripter functions (page sizing, bounding boxes, kerning min/max). 1.6.5 fixed `libpython3.13.so.1.0` loading issues. There are still occasional Qt theme-related crashes (the `--no-splash` workaround on Arch). For CI: pin a known-good Scribus version inside the Docker image, do not rely on distro packages, and don't expect a graceful exit code on every error - log and check that the PDF was actually written.

### A.2 Scripter API (embedded Python)

Scripter is a Python 3 plugin embedded in Scribus. It is the most capable automation surface: open/save SLA, walk pages and frames, replace text, swap image paths, set styles, change colors, export PDF. The PDF export object is `scribus.PDFfile()` with attributes mirroring the GUI dialog: `bleedt/b/l/r`, `Compress`, `CompressMethod`, `Quality`, `Resolution`, `Version` (1.3-1.7), `FontEmbedding` (Embed/Outline/None), `Encrypt`, `Bookmarks`, `Thumbnails`, etc. PDF/X-1a and PDF/X-3 are first-class; PDF/X-4 was added in 1.5.1. Color management must be enabled in document preferences for X-3/X-4 to be selectable.

Coverage vs GUI: Scripter covers the vast majority of layout operations but not 100%. Things that can be flaky or missing: complex master pages, render frames (LaTeX), some advanced PDF/X output intent settings (set by document preference, not all reachable from script in older versions), text style inheritance edge cases, OpenType feature toggling. For the three template types in this project (newspaper-text-heavy, poster-graphic-heavy, postcard-small) Scripter is sufficient.

### A.3 PyScribus / external SLA libraries

**PyScribus** (`pyscribus` on PyPI, source on Framagit by Etna Djakouane) is the only credible Python library that parses SLA files **without** launching Scribus. Last release: 0.3 in August 2023. Pure-XML approach using lxml + svg.path. It can read, build, and update SLA. Snyk currently flags it as inactive (94 weekly downloads). There is a fork `pyscribus-myfork` (Jak-o-Shadows) and a `pyscribus-backported` for older Pythons. There is no other live competitor on PyPI.

Practical implication: PyScribus is fine for low-risk read/edit operations (text substitution, image-path swap) on SLA versions it understands (1.5/1.6 era). It is **not** safe to rely on it as the sole rendering path because:
- It does not render PDF (no PDF code).
- It can produce SLAs that Scribus then refuses or partially renders (since SLA is an undocumented moving target).
- Maintenance is dormant.

The pragmatic split: use PyScribus (or even raw lxml on the SLA XML) for **substitution**, use Scribus headlessly for **rendering**. PyScribus is the right tool when you want to manipulate templates without forcing Scribus into the loop on every CI run.

### A.4 ScribusGenerator (berteh)

285 GitHub stars, 44 forks, last release April 2024 ("mac-friendly"). The most mature Scribus-mail-merge tool. CSV → many SLAs / PDFs.

Variable syntax: `%VAR_name%` in text frames. Special tokens: `%SG_NEXT-RECORD%` for multi-record-per-page, `%VAR_COUNT%` for row index in output filenames. Image swap: dynamic image variables like `%VAR_pic%` reference filenames, all images must live in one folder, and `<svg>`/`<pdf>` images cannot be swapped (Scribus converts them on import, so the runtime swap fails).

Multi-page handling: Works only when the template has the same number of pages as the desired output **multiple of**. Issue #111 documents that "Multiple Duplicate" interactions break the parser. Issue #17-style breakage on Scribus version bumps is recurring. Single-record-per-document is the most reliable mode; merged multi-page output is "works but error-prone" per the project's own README.

Bottom line: ScribusGenerator is great for postcards / cards / business-card-style mail merge from a fixed template. It is a poor fit for a multi-page newspaper where each page has variable content. For the newspaper case, custom Python + Scripter (or PyScribus + Scripter render) is the right path.

### A.5 Templating SLA with Jinja2

SLA is XML, so Jinja2 templating "works" mechanically: open SLA in Scribus, type `{{ headline }}` into a text frame, save, then run the file through Jinja with a context dict, then hand the result to Scribus to render PDF.

Pitfalls in practice:
- Scribus splits long text runs into multiple `<ITEXT>` elements with their own runs of formatting. A `{{ var }}` placed inside a styled run may end up split across runs after Scribus saves: `{{ va` + `r }}`. Always type the placeholder in one go and don't apply styling until after substitution; or use a simple all-caps single token like `HEADLINE_PLACEHOLDER` per frame and substitute via Scripter (which works at the frame-text level, not raw XML).
- Image frames reference files by path attribute, not text content. Substitute via Scripter (`setImageScale`, `loadImage`) or by editing the XML attribute directly in lxml.
- Scribus saves SLA with version metadata; Jinja-rendered SLAs must keep the version tag intact.
- Keep `{% ... %}` control blocks out of styled text. Better: do flow control in Python and just use `{{ var }}` for inline text, or skip Jinja entirely and substitute via lxml/PyScribus.

For this project the cleanest pattern is: **Scribus GUI to design, named frames as anchors, Python (Scripter or PyScribus) to substitute by frame name** rather than by text token. This sidesteps the run-splitting problem entirely.

---

## B. AI-assisted generation

### B.1 LLM authoring SLA from scratch

Realistic? Marginally. SLA is a verbose, undocumented XML schema with version drift and many magic numbers (`PTYPE`, `PFILE`, `LAYER`, transformation matrices, run-level `ITEXT/PARA` interleaving). A modern frontier model can produce something that looks like an SLA file but the validity rate against Scribus is poor. Token cost for a single newspaper page is also high (multi-thousand tokens of XML, much of it non-content). No public experiment shows reliable end-to-end success. Ranks behind every other approach.

### B.2 AI fills variables in a human-built template

Strongly recommended pattern. The human (or designer) builds a Scribus template with named text/image frames. The AI receives a structured spec ("4 columns, headline, subhead, lead paragraph, byline, photo caption, 3 body paragraphs") and returns a JSON object. Substitute by frame name. Constrains the AI to content; layout is deterministic and version-controlled.

This matches the wider literature on structured prompting: XML/JSON-templated outputs with schema validation are the durable pattern, not free-form structural generation. For a poster it is even cleaner (one or two frames). For the newspaper it is harder (column flow, story length matching available space) and benefits from the **vision-judge** loop (B.4).

### B.3 AI for content generation

Headlines, body copy, image prompts, captions, alt text, social teaser - this is where LLMs deliver clear value. Cost per piece is cents to low euros. Combine with brand-style system prompts and a few-shot of past published pieces. Image-prompt generation feeding into FLUX/SDXL is a clean pipeline (see E).

### B.4 Vision-LLM-as-judge

Render PDF → PNG → ask Claude/GPT-4V "does this look right; flag overflow, empty frames, broken images, unbalanced columns, illegible contrast." Patterns:
- Render each page at ~150 dpi PNG (`pdftoppm` or `pdftocairo`).
- Send to a vision-capable model with a checklist prompt (`overflow=true/false`, `empty_frames=[]`, `text_legibility=ok/poor`, `column_balance=...`).
- On any flag, either auto-shrink content / pick a smaller font ramp / re-prompt for shorter copy, or surface to a human reviewer.

Claude Opus 4.7 specifically supports high-resolution images (up to 2576px long edge), which is now adequate for catching layout issues on full pages. Research benchmarks (MLLM-as-a-Judge, WildVision) show vision LLMs are **better at pair comparison** ("which of these two layouts is better?") than at absolute scoring. Useful corollary: keep a "good" reference render and ask the model to compare new renders against it, instead of asking for an absolute quality score.

This loop is the strongest unique ROI item from AI in this pipeline.

---

## C. Alternatives and hybrid stacks

### C.1 Comparison table

| Tool | License | Multi-page | CMYK / ICC / PDF/X | Headless CI | German typography | Best fit |
|---|---|---|---|---|---|---|
| **Scribus 1.6** | GPLv2+ | Strong | Full: CMYK, spot, ICC, PDF/X-1a, X-3, X-4 | Yes (Xvfb) | Hyphenation OK, kerning manual | Newspaper, postcard, full print-ready |
| **Typst 0.14** | Apache-2 | Strong | Partial: CMYK function exists; ICC profile output broken/missing; PDF/X not supported | Excellent (single binary) | Excellent (Unicode-first, hyphenation per language) | Newsletter, technical poster, body-text-heavy |
| **Paged.js** | MIT | Good | Limited: depends on browser engine; CSS bleed/marks supported, CMYK weak | Good (Node/headless Chrome) | Good (browser i18n) | Web-first newsletter, online + print |
| **Vivliostyle** | AGPL-3 | Good | Limited | Good (Node) | Good | Books, EPUB-bridging, less for posters |
| **WeasyPrint 67+** | BSD | Good | CMYK via `device-cmyk()`, `@color-profile` rule (since v67), bleed boxes; no formal PDF/X conformance | Excellent (pure Python) | Good | Reports, simple newsletters |
| **Prince XML** | Commercial | Strong | Full: CMYK, ICC profiles, spot colors | Excellent | Excellent | When budget exists; cleanest non-Scribus print |
| **LaTeX (XeLaTeX/LuaLaTeX)** | LPPL | Strong | Full via `xcolor`, `pdfx` package | Excellent | Excellent (`babel`/`polyglossia`) | Newspaper (newspaper, modernnewspaper, papertex), text-heavy |
| **Inkscape** | GPLv3 | Weak (1 page native) | CMYK weak, ICC OK at export | OK (`--export-type=pdf --batch-process`) | OK | Single-page poster, postcard |
| **Penpot** | MPL-2 | OK (boards) | Web-color only, no print profiles | Limited (puppeteer-based exporter) | OK | Design collaboration, not print pipeline |
| **Affinity Publisher** | Commercial | Strong | Full | None (no CLI) | Good | Designer tool, not a pipeline |
| **InDesign + IDML (SimpleIDML)** | Commercial + MIT lib | Strong | Full | Partial (SimpleIDML composes; rendering needs InDesign Server $$$) | Excellent | Industrial-scale newsroom (Le Figaro) |

### C.2 Notes per option

**Typst** is the strongest "modern" alternative. Single Rust binary, fast, scriptable with first-class functions, packages on Typst Universe. 0.14 (March 2025) added accessibility, character-level justification, expanded PDF/A. Real blockers for **print-grade output**: ICC profile output is still in the issue queue (#3143), CMYK images can be miswritten (#3781), no PDF/X support. Typst is excellent for the newsletter + reports half of the workflow but you still need Scribus or a downstream CMYK-conversion step (Ghostscript with an ICC profile, or `gs -sDEVICE=pdfwrite -sColorConversionStrategy=CMYK`) for press-ready newspaper/poster output. Watch this space - Typst is moving fast.

**Paged.js / Vivliostyle** turn HTML+CSS into paginated PDF using browser engines plus the CSS Paged Media spec. Approachable for web devs, great for newsletters. CMYK and PDF/X are the weak spots: browser rendering pipelines are RGB-native; getting press-ready output usually means a post-processing step. `@page { bleed: 3mm; marks: crop cross }` works, but ICC management is essentially absent. Paged.js > Vivliostyle for popularity and CSS edge cases.

**WeasyPrint** caught up significantly in v67 (mid-2025) with `device-cmyk()` and `@color-profile`. It is now plausible for moderately demanding print, though without formal PDF/X-4 conformance you are still doing pre-flight in a separate tool.

**LaTeX (XeLaTeX/LuaLaTeX)** is the only fully open option that matches Scribus on print color fidelity. The `pdfx` package produces PDF/X-1a/X-3/X-4. The `newspaper`, `modernnewspaper` (Unicode + multilingual, current), and `papertex` packages handle multi-column newspaper layouts. Steep learning curve but proven for newspapers and unbeatable for German typography. Worth keeping as a fallback for the newspaper specifically.

**Inkscape** scriptable command line is mature: `inkscape --export-type=pdf --batch-process file.svg` and the shell protocol for batch sessions. SVG is git-friendly. Multi-page support is weak (Inkscape 1.2+ has limited multi-page, but it is not designed for a 12-page newspaper). Strong fit for **single-page poster A1 and postcard**.

**Penpot** is design-tool-class, not a pipeline tool. PDF export is a recent addition and runs through a puppeteer-driven headless browser. Not recommended for press-ready output.

**Affinity Publisher** has no CLI and no automation surface; rule it out for CI.

**InDesign + SimpleIDML**: SimpleIDML is the underrated gem here. It is the Python library Le Figaro uses to compose IDML files for `Propriétés de France` and `Belles Maisons à louer`. IDML is a zipped XML package; SimpleIDML composes templates and sub-templates, then either ships IDML (rendered later in InDesign / InDesign Server) or - via add-ons - exports PDF. Caveat: rendering to PDF still needs InDesign or InDesign Server (commercial, expensive). The IDML-composition pattern is an inspiration even if you stay in Scribus: build small, named sub-templates and compose them programmatically.

---

## D. Print-quality concerns

The party prints physical media, so this is non-negotiable. The hierarchy:

1. **CMYK + ICC**: For German offset/digital print, ISOcoatedv2_eci.icc is the canonical profile. Scribus + LaTeX (`pdfx`) + Prince fully support this. Typst, WeasyPrint, Paged.js do not yet, or only partially.

2. **PDF/X-1a vs PDF/X-4**: X-1a is the "everything flattened, CMYK only" gold standard accepted by every print shop. X-4 supports transparency and ICC-tagged content - a more modern flow but a few smaller German Druckereien still ask for X-1a. Scribus produces both.

3. **Bleed / trim / crop marks**: 3 mm bleed is standard. Scribus, LaTeX (pdfx), Prince, WeasyPrint all support; Paged.js via CSS works.

4. **Font embedding & licensing**: All open tools embed by default; ensure German-text fonts (Open Sans, Lato, Source Sans 3, Atkinson, Inter all OFL/Apache and commercial-print-OK). Avoid web-only fonts. For SLA: keep fonts in a tracked `fonts/` directory in the repo; CI image must install them so Scribus finds them.

5. **Pre-flight**: Either Scribus's built-in pre-flight verifier (callable from Scripter) or `pdfx --pdfa` style external check, or `verapdf` / `pdfcrap` / shop-side. CI should run a pre-flight gate before "approved for print" status.

6. **Pre-press conversion fallback**: For tools without first-class CMYK/PDF/X (Typst, Paged.js, WeasyPrint), Ghostscript can post-process: `gs -dPDFX -dPDFSETTINGS=/prepress -sColorConversionStrategy=CMYK -sOutputICCProfile=ISOcoatedv2_eci.icc -sDEVICE=pdfwrite -o out.pdf in.pdf`. Quality is acceptable for many jobs but does not replace native CMYK authoring for high-accuracy color (logos, brand greens for a Grüne Zeitung).

---

## E. Image generation & processing automation

**Resize/crop/format**: ImageMagick `mogrify -path resized -resize 800 *.jpg` for batch. Pillow for finer control inside Python. Both are battle-tested in CI.

**Background removal**: `rembg` (Python, U2Net-based) is the standard open option. Cloud APIs (remove.bg, Photoroom) for higher quality.

**Logo placement / watermarking**: ImageMagick composite or Pillow `Image.alpha_composite` with parameterized positioning, scaled to a fraction of the canvas.

**AI image generation**: FLUX.1 / FLUX.1.1 Pro / FLUX.2 (Black Forest Labs, Nov 2025) is the current state-of-the-art for production. SDXL still relevant for fast/cheap or fine-tuned LoRA workflows. ComfyUI orchestrates multi-step pipelines (denoise → upscale → composite). For a print pipeline:
1. AI writes image prompt from article context.
2. FLUX generates 3-5 candidates at high resolution (FLUX outputs ~2 MP natively; upscale to print DPI = 300 dpi × physical_size with Real-ESRGAN or similar).
3. Vision-LLM judge picks best candidate against rubric ("matches headline mood", "clear focal subject", "no text artifacts").
4. ImageMagick converts to CMYK + embeds ICC profile before placing in template.

DPI math: an A1 poster (594 × 841 mm) at 300 dpi = 7016 × 9933 px. Native FLUX cannot produce this in one shot; tile + upscale or accept that hero images are rendered at lower DPI for non-fine-detail use. For a postcard (105 × 148 mm) at 300 dpi = 1240 × 1748 px - well within native FLUX output.

**Color-space gotcha**: AI image gen is RGB. CMYK conversion clips out-of-gamut colors (vivid greens and oranges suffer). For a "Grüne Zeitung" the brand green needs explicit CMYK targeting; otherwise it desaturates noticeably in print. Use a fixed brand green spot color in Scribus rather than rendering it inside a generated image.

---

## Recommended architecture (ranked)

### Top recommendation: Scribus + PyScribus + Scripter, hybrid AI-fill

1. **Templates**: Designed in Scribus GUI, committed to git as `.sla` (XML, diffable). Named frames as substitution anchors. Fonts in tracked `fonts/`.
2. **Content**: AI generates structured JSON content (`headline`, `subhead`, `paragraphs[]`, `image_prompt`, `caption`).
3. **Image gen**: FLUX via API → Real-ESRGAN upscale → ImageMagick CMYK convert with ICC → write to `assets/`.
4. **Substitution**: Python script using PyScribus (or lxml) to swap text in named frames and image paths. Keeps Scribus out of the substitution step (faster iteration).
5. **Render**: Scribus headless inside Docker (Xvfb + scribus 1.6 pinned) calling a `to_pdf.py` Scripter script that opens the SLA, runs pre-flight, exports PDF/X-4 with bleed.
6. **Visual check**: `pdftoppm` → Claude Opus vision → checklist JSON. On flags, adjust copy length / re-render.
7. **Pre-press**: Optional Ghostscript step to enforce final CMYK + PDF/X compliance.

This is the most flexible, most aligned with the existing `.sla` templates already in the repo, and gives the widest design freedom.

### Second recommendation: Typst-first for newsletters, Scribus for posters/postcards

Use Typst for the newspaper/newsletter (text-heavy, where Typst shines and rebuilds in milliseconds). Render to PDF with Typst, then post-process through Ghostscript to enforce CMYK/PDF/X. Use Scribus for posters and postcards where color fidelity and graphic placement matter most. Two pipelines, but each is in the right tool for its job and Typst is a delight to work with for content-heavy iteration. Risk: Typst's CMYK story is still maturing.

### Third recommendation: LaTeX (modernnewspaper) for newspaper + Scribus for posters

Mature, fully print-compliant, German-typography-perfect, pure CLI - LaTeX is the safest choice for a genuine newspaper layout if the team can tolerate the syntax. `pdfx` package guarantees PDF/X-1a/4 conformance. Scribus for posters. Highest quality ceiling, highest learning cost.

### Honorable mention: SimpleIDML pattern (without InDesign)

Even if you stay in Scribus, steal the Le Figaro idea: split each newspaper page into named sub-templates (`masthead.sla`, `lead-story.sla`, `column-2.sla`...), compose them via Python, render via Scribus. Cleaner versioning, easier AI substitution targets, easier diff review.

---

## Risks and watch-list

- **PyScribus is dormant** since Aug 2023. Expect to fork or fall back to raw lxml manipulation.
- **Scribus headless is fragile** at the edges - always wrap in Docker with Xvfb, pin version, log thoroughly, verify PDF was actually written before reporting success.
- **ScribusGenerator multi-page is unreliable** - prefer custom substitution code for the newspaper case.
- **Typst CMYK/ICC is incomplete** as of 2025 - track issue typst/typst#3143.
- **LLMs cannot author SLA reliably** - use them for content + structured fill, not layout.
- **AI images are RGB-native** - brand green in print needs explicit spot color, not generated bitmap.
- **Vision LLM judges are better at pairwise comparison** than absolute scoring - design prompts accordingly.
