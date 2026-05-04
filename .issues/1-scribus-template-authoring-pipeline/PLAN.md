# PLAN — Scribus Template Authoring Pipeline

This plan is structured for incremental execution. Each task produces a render-able or testable artifact. Commit after each task. Order matters — later tasks depend on earlier ones.

## Execution rules

- **One task at a time**, atomic commit per task.
- After every task that produces SLA output: render to PDF via `tools/render.py` and confirm rendering succeeds with no errors before committing.
- Unit tests added in the same commit as the code they cover.
- All artifacts in the worktree on branch `issue/1-scribus-template-authoring-pipeline`.
- If the master-pages research agent (`./.research/04-scribus-multipage-masters.md` when ready) lands, integrate its findings into Phase 5 tasks before starting them.
- **Don't over-engineer.** Build the minimum the issue scope requires; defer anything not in scope.

---

## Phase 1 — Brand Foundation

<task id="1.1" priority="critical">
<title>Create shared/ci.yml</title>
<deliverable>shared/ci.yml as single source of truth: brand colors (CMYK + spot-flag), font names, canonical paragraph style names with parent inheritance, layer stack defaults.</deliverable>
<acceptance>
- File exists at shared/ci.yml
- Contains all brand colors found in the three existing templates: Dunkelgrün, Gelb, Hellgrün, Magenta, plus Black/White/Registration. Each has cmyk: [c,m,y,k] and spot: bool.
- Contains font name list: Gotham Narrow Book, Gotham Narrow Bold, Gotham Narrow Black, Gotham Narrow Ultra, Vollkorn Black Italic.
- Defines canonical paragraph style names (ci/headline-ultra, ci/headline-vollkorn-italic, ci/body-12, ci/body-11, ci/impressum, ci/stoerer, ci/cta) with font, size, alignment, parent.
- Defines default layer stack: Hintergrund, Bilder, Text, Hilfslinien.
</acceptance>
</task>

<task id="1.2" priority="critical">
<title>Implement tools/check_ci.py validator</title>
<deliverable>Validator CLI that loads shared/ci.yml and a target SLA, lists drift: colors not in CI, styles not in CI, missing brand colors. Exit 0 if clean, 1 if drift.</deliverable>
<acceptance>
- Run against the three existing templates flags the RGB-Green inconsistency (Postkarte and Zeitung have a Green color with SPACE="RGB" instead of CMYK).
- Drift report is structured: per-template list of issues with severity (critical: missing brand color; warning: extra style; info: name mismatch).
- Unit test covers a synthetic SLA with known drift.
- Documented in tools/sla_lib/__init__.py module docstring.
</acceptance>
</task>

---

## Phase 2 — DSL Foundation (single-page first)

<task id="2.1" priority="critical">
<title>Create tools/sla_lib/builder/ package skeleton</title>
<deliverable>builder/ subpackage of sla_lib with __init__.py exporting Document, Page, Color, Style enums. Initial implementation emits a minimal valid Scribus 1.6 SLA with one empty page.</deliverable>
<acceptance>
- Document(title="Test", template_id="smoke-empty").set_size("A6", "portrait").save("/tmp/empty.sla") produces a file that opens in Scribus 1.6 and renders to PDF without errors.
- Color and Style enums populated from shared/ci.yml at import time (lazy load).
- Module docstring documents the public surface.
- Unit test: smoke-empty rendering succeeds via tools/render.py.
</acceptance>
</task>

<task id="2.2" priority="critical">
<title>Add primitives: TextFrame, ImageFrame, Polygon, Line</title>
<deliverable>Low-level frame primitives that emit valid PAGEOBJECT XML. Coordinates accept mm, internally converted to pt and offset by page position.</deliverable>
<acceptance>
- TextFrame(x_mm, y_mm, w_mm, h_mm, story=Text("hello"), style=Style.BODY_12) renders with the text visible.
- ImageFrame(x_mm, y_mm, w_mm, h_mm, src="path/to/img.png") shows the image when src exists, placeholder otherwise.
- Polygon(points_mm=..., fill=Color.DUNKELGRUN) renders the polygon.
- Line(start_mm, end_mm, color=..., width_pt=...) renders.
- Each primitive accepts anname=str for human-readable hint.
- Each primitive lands on a configurable layer (default per type).
- Anchor resolution (top-left, top-center, ...) implemented and unit tested.
- Unit tests validate XML structure (parses back through SLADocument and checks attributes).
</acceptance>
</task>

<task id="2.3" priority="critical">
<title>First DSL example: A6 postcard skeleton</title>
<deliverable>templates/_smoke/postcard-a6/build.py that uses the DSL to produce templates/_smoke/postcard-a6/template.sla — a brand-correct A6 postcard skeleton with example content.</deliverable>
<acceptance>
- build.py runs as `python3 templates/_smoke/postcard-a6/build.py` and writes template.sla.
- The SLA opens cleanly in Scribus, renders to PDF via tools/render.py.
- Visual check: green background polygon on page 1, brand-headline-style text frame, störer-style polygon + text, impressum line. Doesn't have to match the original Postkarte design pixel-perfect — just demonstrates DSL produces brand-correct output.
- File commits include the build.py and the resulting template.sla.
- README.md in the smoke dir explains: "this is a smoke test for DSL; not a production template."
</acceptance>
</task>

---

## Phase 3 — Block Primitives (compose-level)

<task id="3.1" priority="high">
<title>Block: Headline4Line</title>
<deliverable>Headline4Line(lines=[..], colors=[..], style=...) compose-block emitting a TextFrame with 4-line alternating-color headline. Default colors alternate Color.WEISS/Color.GELB.</deliverable>
<acceptance>
- Each of the 4 lines is its own ITEXT run with explicit FCOLOR (so per-line color survives Scribus reload).
- ANNAME is human-readable: "Headline 4-zeilig (Brand-Wechselfarbe)".
- Default content: ["[Zeile 1]", "[Zeile 2]", "[Zeile 3]", "[Zeile 4]"] — visible in Scribus.
- Anchor: caller passes pos=("center", y_mm) or absolute mm.
- Unit test: verify 4 ITEXT runs, alternating FCOLOR, correct PARENT style.
</acceptance>
</task>

<task id="3.2" priority="high">
<title>Block: StoererBadge</title>
<deliverable>StoererBadge(text=[..], color=Color.MAGENTA, pos=...) compose-block: pink/magenta circle polygon + 3-line text inside.</deliverable>
<acceptance>
- Polygon is a circle (24-segment approximation) with configurable diameter.
- Text frame overlays polygon, centered, with style ci/stoerer.
- Default text: ["[Zeile 1]", "[Zeile 2]", "[Zeile 3]"].
- ANNAME on polygon: "Störer-Kreis", on text: "Störer-Text 3-zeilig".
- Slight rotation default (5-10°) like the originals.
- Unit test verifies structure.
</acceptance>
</task>

<task id="3.3" priority="high">
<title>Block: ImpressumLine and ImpressumBlock</title>
<deliverable>ImpressumLine(text=...) one-liner at bottom; ImpressumBlock(text=...) multi-line block.</deliverable>
<acceptance>
- Default text uses the canonical Grünen-NÖ Impressum string.
- Style ci/impressum applied.
- Position defaults: bottom-center for line, bottom-right for block.
- Unit tests.
</acceptance>
</task>

<task id="3.4" priority="high">
<title>Block: SocialHandlesVertical</title>
<deliverable>SocialHandlesVertical(handles=[(icon, label), ...]) - icon column + text column.</deliverable>
<acceptance>
- Default handles: Facebook, Instagram, Email, Phone with placeholder labels.
- Icons referenced from shared/logos/social/{facebook,instagram,mail,phone}.png — create stub PNGs (small placeholders) if not present.
- Unit test.
</acceptance>
</task>

<task id="3.5" priority="high">
<title>Block: LogoCorner</title>
<deliverable>LogoCorner(corner="top-left"|"top-right"|..., variant="weiss"|"farbig", size_mm=...) places brand logo.</deliverable>
<acceptance>
- Logo source: shared/logos/gruene-{weiss,farbig}.png — create simple SVG/PNG stubs if not present (text "GRÜNE" placeholder).
- Default size proportional to page size.
- Unit test.
</acceptance>
</task>

<task id="3.6" priority="medium">
<title>Block: EventDetails</title>
<deliverable>EventDetails(date, time, venue, address, anchor=...) — multi-line event info block, used by Plakat-Event templates.</deliverable>
<acceptance>
- 4 lines: date, time, venue, address. Style ci/body-12.
- ANNAME: "Veranstaltungs-Details".
- Default content: "[Datum]", "[Zeit]", "[Veranstaltungsort]", "[Adresse]".
- Unit test.
</acceptance>
</task>

<task id="3.7" priority="medium">
<title>Block: Masthead (Zeitung)</title>
<deliverable>Masthead(zeitungsname, ausgabe_label) - newspaper masthead with logo + name + issue label.</deliverable>
<acceptance>
- Used on Zeitung Titelseite.
- Default content: "Zeitungsname", "Monat / Ausgabe".
- Unit test.
</acceptance>
</task>

<task id="3.8" priority="medium">
<title>Block: ContentTeasers (3-column grid for Titelseite)</title>
<deliverable>ContentTeasers(count=3, items=[(headline, body), ...]) — 3-column grid of teaser articles for Titelseite.</deliverable>
<acceptance>
- Default 3 columns, each with placeholder headline + 4-5 lines of body lorem ipsum.
- Style: ci/headline for teaser titles, ci/body-11 for body.
- Unit test.
</acceptance>
</task>

<task id="3.9" priority="medium">
<title>Block: ArticleHeadline + ArticleBody (multi-column)</title>
<deliverable>ArticleHeadline(text, ...) and ArticleBody(text, cols=3, ...) for inside-newspaper articles.</deliverable>
<acceptance>
- ArticleBody supports 1, 2, 3 columns.
- Linked text frames (NEXTITEM/BACKITEM) when cols > 1 so text flows.
- Default content lorem ipsum.
- Unit test verifies link chain.
</acceptance>
</task>

---

## Phase 4 — Multi-page DSL (depends on Phase 5 research)

<task id="4.1" priority="high" depends_on="04-scribus-multipage-masters.md">
<title>Add Document.add_master() and Document.add_page()</title>
<deliverable>Multi-page support in DSL: define master pages, add example pages referencing masters, page labels visible in Scribus Page Panel.</deliverable>
<acceptance>
- Document with 2 masters and 4 pages renders correctly.
- Each page references its master via correct attribute (per the research agent findings).
- Page labels visible in Scribus Page Panel as "Beispiel: Doppelseite Hauptartikel".
- Facing-pages support (left/right) via PageSets configuration.
- Unit test: 2 masters × 4 pages document opens, renders all pages, master page elements appear on all referencing pages.
</acceptance>
</task>

<task id="4.2" priority="high">
<title>Add column grid + helper guides on master pages</title>
<deliverable>Master pages can declare column grids that show as Scribus guides (Hilfslinien) but don't render in PDF.</deliverable>
<acceptance>
- ColumnGrid(cols=3, gutter_mm=4) on a master shows 3 columns in Scribus.
- Guides on Hilfslinien layer (hidden by default).
- Layer toggling works in Scribus GUI.
- PDF render does NOT show guides.
- Unit test.
</acceptance>
</task>

---

## Phase 5 — Block Extraction Tooling

<task id="5.1" priority="medium">
<title>tools/extract_block.py</title>
<deliverable>CLI to extract a region from a source SLA: copy selected PAGEOBJECTs + their referenced styles + colors into a self-contained block fragment.</deliverable>
<acceptance>
- Usage: extract_block --source X.sla --frames "comma,separated,annames" --out shared/blocks/category/id.sla
- Output is a valid SLA that opens in Scribus on its own.
- Output includes only the styles/colors actually referenced by the extracted frames.
- Coordinates normalized to top-left of bbox = (0,0).
- Unit test using one of the existing 3 templates.
</acceptance>
</task>

<task id="5.2" priority="medium">
<title>shared/blocks/catalog.yml + initial library</title>
<deliverable>Catalog metadata + at least 6 extracted blocks from the existing 3 templates.</deliverable>
<acceptance>
- catalog.yml lists ≥ 6 blocks with id, fragment path, bbox_mm, slots, suitable_for tags.
- Blocks include: content/headline-4line-alt, content/stoerer-badge, footer/impressum-line, footer/social-handles-vertical, header/masthead-zeitung, content/three-column-teasers (Titelseite of Zeitung).
- Each block fragment renders standalone via tools/render.py.
</acceptance>
</task>

---

## Phase 6 — Authoring Tools

<task id="6.1" priority="medium">
<title>tools/new_template.py — interactive scaffolder</title>
<deliverable>CLI that prompts for page-size + format + occasion, scaffolds templates/&lt;id&gt;/{build.py, meta.yml, README.md}.</deliverable>
<acceptance>
- Output directory structure correct.
- build.py is a runnable Python file with a starter Document() call.
- meta.yml has placeholders for description, audience, slots.
- Smoke test: scaffold a "flyer-a5" template, run its build.py, confirm template.sla generates and renders.
</acceptance>
</task>

<task id="6.2" priority="low">
<title>tools/author.py — Markdown-brief → Layout-YAML → DSL</title>
<deliverable>Wrapper that takes a Markdown brief, calls Claude (anthropic SDK) with the brief + catalog.yml + brand context, gets layout YAML, builds SLA via DSL.</deliverable>
<acceptance>
- Example brief committed at templates/_briefings/example-rollup-mahnwache.md.
- author.py reads the brief, emits layout.yml, builds template.sla, renders preview.pdf.
- Stub the LLM call if no API key available — read a pre-committed layout.yml as fallback so the pipeline still works for tests.
- Unit test uses the stubbed path.
</acceptance>
</task>

---

## Phase 7 — Migrate Existing Templates

<task id="7.1" priority="high">
<title>Re-build Postkarte via DSL</title>
<deliverable>templates/postkarte-a6-kampagne/build.py reproduces the Postkarte design via the DSL. Output replaces or sits alongside the existing template.sla.</deliverable>
<acceptance>
- build.py emits template.sla with all the slots from the existing migrated version.
- Visual: rendered PDF is recognisably the same kampagne-postkarte (green bg, headline, störer, impressum, social, QR placeholder).
- Existing samples/{klimaschutz,wohnen}.json still work — slot ANNAMEs preserved.
- README.md updated to point at build.py.
</acceptance>
</task>

<task id="7.2" priority="critical">
<title>Build Zeitung as multi-page DSL skeleton</title>
<deliverable>templates/zeitung-a4-grun/build.py emits one multi-page SLA with 5+ master pages and 8-10 example pages, each labeled. Replaces "Grüne Zeitung Vorlage Scribus.sla" as the canonical authoring template.</deliverable>
<acceptance>
- ≥ 5 master pages: rechts-3col, links-3col, titelseite, foto-spread, impressum.
- ≥ 8 example pages, each label visible in Page Panel: Titelseite, Doppelseite-Hauptartikel-links, Doppelseite-Hauptartikel-rechts, Drei-Artikel-Spalten, Foto-Doppelseite-links, Foto-Doppelseite-rechts, Veranstaltungskalender, Interview, Kommentar, Impressum-Postvermerk (any subset of these ≥ 8 OK).
- Each example page populated with placeholder headlines + lorem ipsum body via the article blocks.
- Renders to a multi-page PDF that opens cleanly.
- Existing Grüne Zeitung Vorlage Scribus.sla remains in repo as the original reference but the README points to the new templates/zeitung-a4-grun/.
</acceptance>
</task>

<task id="7.3" priority="medium">
<title>Plakat family: A0/A1/A2/A3 from one DSL</title>
<deliverable>templates/plakat-event/build.py parameterizes on size and emits 4 SLAs (a0, a1, a2, a3) plus a meta.yml.</deliverable>
<acceptance>
- build.py loop produces all 4 SLAs.
- All 4 render correctly. Layout scales appropriately (font sizes, margins).
- meta.yml describes the family with size variants.
</acceptance>
</task>

---

## Phase 8 — Astro Gallery + GitHub Pages

<task id="8.1" priority="high">
<title>Set up site/ Astro project</title>
<deliverable>Astro 5+ project under site/ with content collection schema for templates/*/meta.yml.</deliverable>
<acceptance>
- npm install + npm run build produces a static site under site/dist/.
- Content collection schema validates meta.yml.
- Index page lists all templates from templates/ folder.
- npm run dev shows the site locally.
</acceptance>
</task>

<task id="8.2" priority="high">
<title>Per-template detail page</title>
<deliverable>Astro dynamic route [...slug].astro that renders detail page per template: PDF preview embed, page-by-page PNG carousel, download buttons, "How to use" section.</deliverable>
<acceptance>
- For postkarte-a6-kampagne: shows preview PDF, single-page thumbnail, download SLA + assets zip.
- For zeitung-a4-grun: shows multi-page PNG carousel, download SLA + assets zip.
- For plakat-event family: shows size selector A0/A1/A2/A3 with respective PDF previews.
- "How to use" section explains: open in Scribus, duplicate example pages (for newspapers), edit content, brand quickstart link.
</acceptance>
</task>

<task id="8.3" priority="medium">
<title>tools/gallery_build.py — bridge templates to site/src/content/</title>
<deliverable>Python script that walks templates/, generates page-PNG previews via tools/render.py + pdftoppm, copies meta.yml + previews into site/src/content/templates/.</deliverable>
<acceptance>
- Run as: python3 tools/gallery_build.py — populates site/src/content/templates/ from templates/ source.
- Idempotent. Skips up-to-date items.
- Unit test on a synthetic template.
</acceptance>
</task>

<task id="8.4" priority="medium">
<title>.github/workflows/pages.yml</title>
<deliverable>GitHub Action: on push to main, run gallery_build.py inside the renderer container, npm build site/, deploy to Pages.</deliverable>
<acceptance>
- workflow yaml is syntactically valid (gh workflow lint).
- Uses the docker/renderer image.
- Caches node_modules and renderer image.
- Deploys to gh-pages branch (or actions/deploy-pages action).
</acceptance>
</task>

---

## Phase 9 — Documentation polish

<task id="9.1" priority="medium">
<title>Update top-level README.md to reflect authoring-first model</title>
<deliverable>README.md frames the project as a template authoring system; render pipeline mentioned only as "preview generation".</deliverable>
<acceptance>
- "Was ist das?" / "What is this?" sections at top.
- Clear quickstart for: (a) downloading a template, (b) authoring a new template, (c) contributing a new block.
- Links to .research/ docs, gallery URL placeholder, contribution guide.
</acceptance>
</task>

<task id="9.2" priority="low">
<title>shared/fonts/README.md — Schriftlizenz-Hinweise</title>
<deliverable>Documentation that Gotham Narrow & Vollkorn fonts must be installed locally; not committed to git for license reasons.</deliverable>
<acceptance>
- README explains: how to verify fonts are installed (fc-list | grep), what fallback fonts the renderer uses, how to add fonts to the Docker image build.
</acceptance>
</task>

---

## Iteration / smoke discipline

After **every phase** the executor runs:
```bash
# All-templates smoke render
for t in templates/_smoke/* templates/*/; do
    [ -f "$t/build.py" ] && python3 "$t/build.py"
    [ -f "$t/template.sla" ] && python3 tools/render.py "$t" --out "build/$(basename $t).pdf"
done
# All tests
python3 -m unittest discover tools/sla_lib/tests -v
```
Commit only if both clean. If a smoke render breaks, fix before moving on.

## Out-of-scope reminder

Online configurator, AI image gen, vision-LLM judge with iteration, PDF/X-4 conformance, visual regression — all explicitly out for this issue. Don't drift into them.
