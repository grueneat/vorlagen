# Plan: Vorlagen auf Barlow Semi Condensed umstellen, Fremdschriften + Schriftvergleich entfernen, Baselines neu erzeugen

<objective>
Switch ALL vorlagen templates to a single font — **Barlow Semi Condensed** —
removing every non-Barlow family (Gotham Narrow Book/Bold/Black/Ultra incl. one
`Gotham Narrow Ultra Italic`, Minion Pro Regular, Times Roman, and Vollkorn
Black/Bold Italic). Provision Barlow locally for Scribus/fontconfig (vendored OFL
print-pipeline exception), remove the entire "Schriftvergleiche" feature from #42,
re-render all 16 templates headless, visually review every rendered page for
text alignment/centering (Barlow is narrower → shifted wraps), then promote the
freshly rendered PDFs to new `baseline.pdf` and re-derive `TOLERANCES.yml`.

Why it matters: Gotham Narrow is proprietary; the org wants a single free font
across all print templates. The old baselines encode Gotham-vs-InDesign wrap
deltas and are invalid after the swap, so they must be regenerated — but only
after a human/agent visual sign-off, because Barlow's narrower metric shifts
line-breaks and optical centering.

Scope IN: font-string swap across build.py + 3 `*-original.sla` + library
defaults (`brand.py` deffont, `shared/ci.yml`), Barlow Docker provisioning,
Schriftvergleiche removal, full re-render, visual review, baseline promotion,
tolerance re-derivation, doc note on the font exception.
Scope OUT: re-choosing the font (decided in #42), pulling a Barlow italic unless
visual review proves an accent essential (Risk R6 checkpoint).

Decisions source: CONTEXT.md (5 locked decisions) + RESEARCH.md (HIGH-confidence
inventory, exact Scribus font strings, removal map, exact commands).
</objective>

<strategy>
The font swap itself is mechanical and was verified end-to-end on the live
container (patched one build.py → rendered → `pdffonts` showed three Barlow
weights embedded, zero DejaVu). The risk is NOT the swap — it is the baseline
and tolerance regeneration after Barlow's narrower metric shifts every line-wrap
and centering.

Direction: foundation-first, then swap, then a hard visual gate before any
baseline is touched.
1. Provision Barlow reproducibly in `Dockerfile.claude` (sanity-check on
   `fc-match "Barlow Semi Condensed"` + face count — NOT per-weight strings,
   which fc-match resolves to DejaVu by design; Scribus reads the TTF name table
   so all four faces render regardless). No fontconfig alias (unlike Vollkorn).
2. Swap the 7 non-Barlow strings in three layers the naive grep misses: the 16
   per-template `build.py`, the 3 hand-authored `*-original.sla`, AND two
   library-level defaults — `tools/sla_lib/builder/brand.py` (`deffont`) and the
   `shared/ci.yml` brand allow-list + `ci/*` style fonts. Never edit
   `template.sla` directly — it is regenerated from build.py.
3. Remove the whole Schriftvergleiche feature incl. its unit test (else CI's
   `unittest discover` fails), and relocate the 4 Barlow TTFs to a committed
   print-font dir BEFORE deleting `shared/fonts/alternatives/`.
4. Render all 16 with `--skip-visual-diff` (the old Gotham baselines are
   meaningless now), visually review all ~72 pages in multiple passes, fix
   overflow/centering in build.py, re-render until clean.
5. Only AFTER sign-off: promote previews → baselines, re-derive `TOLERANCES.yml`
   empirically (LOW-confidence — depends on actual render drift), run
   `render-gallery` WITHOUT skip + `check-stale-previews` green.

Options considered: (a) fontconfig alias for Barlow — rejected, verified
unnecessary, Scribus resolves natively. (b) install Barlow from the gitignored
`fonts/` drop zone — rejected, not reproducible in a clean checkout; instead
COPY from a committed print-font dir. (c) keep old tolerances — rejected, they
encode the wrong (Gotham) wrap drift and would mis-classify Barlow drift.
</strategy>

<skills>
Read and follow these skills during execution if invoked; none auto-applies to a
cross-cutting font swap, but one is a useful reference for the visual-polish loop:
- @.claude/skills/idml-tune/SKILL.md — reference ONLY for the per-template
  visual-polish loop in Task 5 (permitted edits build.py / TOLERANCES.yml,
  inventory-gated re-render). NOTE: this issue is cross-cutting (all templates +
  library defaults), so do NOT constrain yourself to idml-tune's single-slug
  scope; use it for the render→inspect→fix→re-render rhythm only.
</skills>

<context>
Issue: @.issues/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s/ISSUE.md
Research: @.issues/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s/RESEARCH.md
Context: @.issues/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s/CONTEXT.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

── EXACT Scribus font names (verified via scribus.getFontNames() on the container) ──
The strings build.py / *.sla / ci.yml MUST reference. Scribus reads the TTF name
table directly; once the TTFs are in fontconfig these four resolve natively:
  "Barlow Semi Condensed Regular"     ← maps from Gotham Narrow Book, Minion Pro Regular, Times Roman
  "Barlow Semi Condensed Bold"        ← maps from Gotham Narrow Bold, Vollkorn Bold Italic
  "Barlow Semi Condensed Black"       ← maps from Gotham Narrow Black, Gotham Narrow Ultra, Gotham Narrow Ultra Italic, Vollkorn Black Italic
  "Barlow Semi Condensed ExtraBold"   ← available but UNUSED under this weight map

── fc-match behaviour (explains the Dockerfile sanity-check shape) ──
  BarlowSemiCondensed-Regular.ttf  : family="Barlow Semi Condensed"  style="Regular"
  BarlowSemiCondensed-Bold.ttf     : family="Barlow Semi Condensed"  style="Bold"
  BarlowSemiCondensed-Black.ttf    : family="Barlow Semi Condensed,Barlow Semi Condensed Black"  style="Black,Regular"
  BarlowSemiCondensed-ExtraBold.ttf: family="Barlow Semi Condensed,Barlow Semi Condensed ExtraBold" style="ExtraBold,Regular"
  Consequence: `fc-match "Barlow Semi Condensed Regular"`/`… Bold` → DejaVu (style
  suffix is not a family). `fc-match "Barlow Semi Condensed"` → Barlow Regular.
  So the Dockerfile sanity-check MUST test `fc-match "Barlow Semi Condensed"` +
  a face count, NOT per-weight strings. Trust pdffonts render audit for fallback.

── Document / Brand DSL (tools/sla_lib/builder/) ──
  document.py:152  def Document(..., deffont: str = "Gotham Narrow Book", ...)
  brand.py:74      @dataclass class Brand:  deffont: str = "Gotham Narrow Book"   ← change
  brand.py:145     Brand.gruene_noe() factory sets deffont="Gotham Narrow Book"   ← change
  styles.py:41,108 / primitives.py:322 — font carried on:
    class CharStyle: font: Optional[str]
    class ParaStyle: font: Optional[str]
    class TextFrame:  font: Optional[str]
    class Run:        font: Optional[str]   # a text-bearing Run's own font wins

── shared/ci.yml schema (the brand allow-list; verified line refs) ──
  fonts:  ["Gotham Narrow Book","Gotham Narrow Bold","Gotham Narrow Black",
           "Gotham Narrow Ultra","Vollkorn Black Italic"]   ← replace with Barlow set
  styles: ci/default(font "Gotham Narrow Book"), ci/headline-ultra("Gotham Narrow Ultra"),
          ci/headline-vollkorn-italic("Vollkorn Black Italic"), ci/body-12("Gotham Narrow Book"),
          ci/body-11("Gotham Narrow Book"), ci/impressum("Gotham Narrow Book"),
          ci/stoerer("Gotham Narrow Ultra"), ci/cta("Gotham Narrow Bold")   ← update each font:

── Headless render contract (tools/visual_diff.py) ──
  def render_sla_to_pdf(sla_path: Path, pdf_path: Path) -> None
    → xvfb-run -a --server-args="-screen 0 1024x768x24" \
        scribus -g -ns -py tools/_export_pdf.py <sla_abs> <pdf_abs>

── render-gallery CLI (tools/render_pipeline.py) ──
  bin/render-gallery [TEMPLATE_ID] [--skip-visual-diff] [--visual-diff-warning-only]
                     [--dry-run] [--audit] [--audit-strict]
    no TEMPLATE_ID → all renderable templates; auto-updates meta.yml
    build_py_sha256 + previews_for_sla after each render.

── stale gate (tools/check_stale_previews.py) ──
  bin/check-stale-previews   # FAIL if sha256(build.py)!=meta.build_py_sha256
                             #      or sha256(template.sla)!=meta.previews_for_sla
</interfaces>

<font_provisioning_note>
Dockerfile.claude:96 installs fonts by `COPY fonts/ /tmp/fonts-staging/` — but
`fonts/` is a GITIGNORED, user-supplied drop zone, NOT reproducible from a clean
checkout. The 4 Barlow TTFs currently live (committed) at
`shared/fonts/alternatives/barlow-semi-condensed/*.ttf`, which Task 3 deletes.
Therefore Task 1 RELOCATES those 4 TTFs to a committed print-font dir
(`fonts/barlow-semi-condensed/` — make it tracked via a `.gitignore` exception,
mirroring the existing `!shared/fonts/alternatives/**/*.ttf` pattern) and COPYs
from that committed path in the Dockerfile, so the build is reproducible. The
current `COPY fonts/` drop-zone block is kept for the remaining proprietary
Gotham TTFs the maintainer still drops in; add a SECOND committed COPY for Barlow.
</font_provisioning_note>

<call_sites>
Searched: the Scribus font strings ("Gotham Narrow *", "Minion Pro Regular",
"Times Roman", "Vollkorn * Italic"), the `deffont` default, the `fonts:`
allow-list, and the render/baseline/stale commands.
Surfaces grepped: templates/*/build.py, *.sla (template.sla + 3 *-original.sla),
tools/sla_lib/builder/, shared/ci.yml, Dockerfile.claude, .github/workflows/,
bin/, docs/, site/.

Font-string call sites (ALL in scope — Task 2 unless noted):
- templates/*/build.py (16 files) — font=/deffont= strings (~1100 refs) — IN SCOPE (Task 2)
- 3 hand-authored *-original.sla (postkarte-vorlage / plakat-a1-hochformat / gruene-zeitung-vorlage) — FONT=/DFONT= incl. lone `Gotham Narrow Ultra Italic` in postkarte-vorlage-original.sla — IN SCOPE (Task 2)
- tools/sla_lib/builder/brand.py:74,145 — deffont default — IN SCOPE (Task 2)
- shared/ci.yml fonts: + ci/* style font: fields — IN SCOPE (Task 2)
- templates/*/template.sla (generated) — NOT hand-edited; regenerated by render-gallery in Task 4 — OUT OF SCOPE for manual edit
- Dockerfile.claude:96-118 font install/sanity-check — IN SCOPE (Task 1)

CI/render invocation call sites:
- .github/workflows/pages.yml — runs `check-stale-previews` (SHA gate), `gallery_build.py`, Astro build, `unittest discover tools/sla_lib/tests` — CI does NOT render; baselines/previews produced LOCALLY (Tasks 4-6). The stale gate must be green before push.
- .github/workflows/ci.yml — SOP lints + `pytest tests/unit/` — no font edit needed; must stay green (Task 7).

No additional adjacent CLI flag/script call sites introduced (this issue adds no
new flag/command).
</context>

<commit_format>
Format: conventional with issue prefix (per .issues/config.yaml).
Pattern: c8bg0: {type}({scope}): {description}
Examples:
  c8bg0: feat(fonts): provision Barlow Semi Condensed for Scribus
  c8bg0: refactor(templates): swap Gotham/Minion/Times/Vollkorn to Barlow
  c8bg0: chore(site): remove Schriftvergleiche feature
Types: feat, fix, refactor, chore, docs, test.
HARD RULE: no tool attribution anywhere — no "claude", no "Generated with",
no `Co-Authored-By` (CLAUDE.md + config). Applies to every commit and comment.
</commit_format>

<tasks>

<task type="auto">
  <name>Task 1: Provision Barlow Semi Condensed for Scribus (Dockerfile + committed TTFs)</name>
  <files>fonts/barlow-semi-condensed/BarlowSemiCondensed-Regular.ttf, fonts/barlow-semi-condensed/BarlowSemiCondensed-Bold.ttf, fonts/barlow-semi-condensed/BarlowSemiCondensed-Black.ttf, fonts/barlow-semi-condensed/BarlowSemiCondensed-ExtraBold.ttf, fonts/barlow-semi-condensed/OFL.txt, .gitignore, Dockerfile.claude</files>
  <action>
  Make Barlow available to fontconfig/Scribus reproducibly. This is the deliberate
  print-pipeline vendoring exception (Barlow is SIL OFL — same justification as the
  existing Vollkorn vendoring; CONTEXT decision 2).

  1. Copy the 4 committed Barlow TTFs + OFL.txt from
     `shared/fonts/alternatives/barlow-semi-condensed/` to a NEW committed
     print-font dir `fonts/barlow-semi-condensed/` (the old `alternatives/` dir is
     deleted in Task 3, so the print fonts must live in a path that survives).
     Use `git mv` for the 4 TTFs + OFL.txt so history is preserved.
  2. `.gitignore`: `fonts/` is currently a gitignored drop zone. Add a tracked
     exception for the Barlow print fonts, mirroring the existing
     `!shared/fonts/alternatives/**/*.ttf` pattern:
        !fonts/barlow-semi-condensed/*.ttf
        !fonts/barlow-semi-condensed/OFL.txt
     Confirm `git status` then SHOWS the 4 TTFs + OFL.txt as tracked/added.
  3. Dockerfile.claude: ADD a second committed COPY for Barlow alongside the
     existing `COPY fonts/ /tmp/fonts-staging/` block (keep the drop-zone block for
     the maintainer's proprietary Gotham TTFs). E.g.:
        COPY fonts/barlow-semi-condensed/ /tmp/barlow-staging/
        RUN install -m 644 /tmp/barlow-staging/*.ttf /usr/local/share/fonts/gruene/ && \
            fc-cache -f && \
            BN=$(fc-list | grep -ci 'barlow semi condensed' || true) && \
            if [ "$BN" -lt 4 ]; then echo "BARLOW INSTALL FAILED: $BN faces (expected >=4)" >&2; exit 1; fi && \
            fc-match "Barlow Semi Condensed" | grep -qi barlow || { echo "fc-match did not resolve to Barlow" >&2; exit 1; } && \
            echo "Barlow installed: $BN faces" && rm -rf /tmp/barlow-staging
     DO NOT add a fontconfig family-alias .conf for Barlow (verified unnecessary —
     Scribus reads the TTF name table; unlike Vollkorn). DO NOT sanity-check
     per-weight strings ("Barlow Semi Condensed Regular"/"… Bold") — fc-match
     resolves those to DejaVu by design (see <interfaces>); check the bare family
     "Barlow Semi Condensed" + face count instead.
  4. The fonts are already installed on the live container from the research
     session; install them now if missing so subsequent render tasks work:
        sudo install -m 644 fonts/barlow-semi-condensed/*.ttf /usr/local/share/fonts/gruene/ 2>/dev/null \
          || install -m 644 fonts/barlow-semi-condensed/*.ttf /usr/local/share/fonts/gruene/ ; fc-cache -f
  </action>
  <verify>
  <automated>cd /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s && test -f fonts/barlow-semi-condensed/BarlowSemiCondensed-Regular.ttf && test -f fonts/barlow-semi-condensed/BarlowSemiCondensed-Black.ttf && git ls-files --error-unmatch fonts/barlow-semi-condensed/BarlowSemiCondensed-Black.ttf && [ "$(fc-list | grep -ci 'barlow semi condensed')" -ge 4 ] && fc-match "Barlow Semi Condensed" | grep -qi barlow && grep -q 'barlow-semi-condensed' Dockerfile.claude && echo PROVISION_OK</automated>
  </verify>
  <done>
  - 4 Barlow TTFs + OFL.txt committed under fonts/barlow-semi-condensed/ (git-tracked)
  - .gitignore exception makes them tracked despite the fonts/ drop-zone rule
  - Dockerfile.claude COPYs + installs Barlow from the committed path with a
    face-count + `fc-match "Barlow Semi Condensed"` sanity-check (no per-weight check, no alias)
  - fc-list shows >=4 Barlow faces; fc-match resolves to a Barlow TTF on the container
  </done>
</task>

<task type="auto">
  <name>Task 2: Swap all non-Barlow font strings to Barlow (build.py + *-original.sla + library defaults + ci.yml)</name>
  <files>templates/*/build.py, postkarte-vorlage-original.sla, plakat-a1-hochformat-original.sla, gruene-zeitung-vorlage-original.sla, tools/sla_lib/builder/brand.py, shared/ci.yml</files>
  <action>
  Replace every non-Barlow family string per the locked weight map (CONTEXT
  decision 1). Use the EXACT Barlow strings from <interfaces>. Edit source files
  only — NEVER edit `templates/*/template.sla` (generated; regenerated in Task 4).

  Weight map (apply to font= and deffont= and FONT=/DFONT= and ci.yml font:):
    Gotham Narrow Book          → Barlow Semi Condensed Regular
    Gotham Narrow Bold          → Barlow Semi Condensed Bold
    Gotham Narrow Black         → Barlow Semi Condensed Black
    Gotham Narrow Ultra         → Barlow Semi Condensed Black
    Gotham Narrow Ultra Italic  → Barlow Semi Condensed Black   (lone string in postkarte-vorlage-original.sla)
    Minion Pro Regular          → Barlow Semi Condensed Regular
    Times Roman                 → Barlow Semi Condensed Regular
    Vollkorn Black Italic       → Barlow Semi Condensed Black
    Vollkorn Bold Italic        → Barlow Semi Condensed Bold

  Order the replacements LONGEST-MATCH-FIRST so substrings don't corrupt
  ("Gotham Narrow Ultra Italic" before "Gotham Narrow Ultra"; "Gotham Narrow Black"/
  "…Bold"/"…Book" are distinct suffixes — replace the full quoted strings, not the
  bare prefix "Gotham Narrow"). Preserve surrounding quote style and Python syntax.

  Targets:
  1. templates/*/build.py (16 files) — all font=/deffont= occurrences, incl. the 3
     explicit `deffont='Gotham Narrow Black'` at postkarte-a6-kampagne:34,
     zeitung-a4:34, plakat-a1-hochformat:33 → `Barlow Semi Condensed Black`.
  2. brand.py:74 and brand.py:145 — `deffont: str = "Gotham Narrow Book"` and the
     gruene_noe() factory `deffont="Gotham Narrow Book"` → `Barlow Semi Condensed Regular`.
     (Leave document.py:152's default as-is OR change it too for consistency — it is
     overridden by Brand; changing it to Barlow Regular is preferred for hygiene.)
  3. The 3 hand-authored *-original.sla at repo top level — replace every FONT="…"
     and DFONT="…" Gotham/Vollkorn/Minion/Times string incl. the lone
     `Gotham Narrow Ultra Italic`. These are oracles; keeping them honest matters
     even though sla_diff is skipped (all 3 have sla_diff_strict: false).
  4. shared/ci.yml — replace the `fonts:` allow-list with the Barlow set
     ["Barlow Semi Condensed Regular","Barlow Semi Condensed Bold",
      "Barlow Semi Condensed Black"] (ExtraBold unused under this map — omit unless a
     style references it), and update each ci/* style `font:` field per the map
     (ci/headline-vollkorn-italic → Barlow Semi Condensed Black).

  After editing, grep-clean: NO non-Barlow family may remain in templates/ or any
  *.sla source. (template.sla still holds old strings until Task 4 re-renders — the
  grep gate below scopes to build.py + the 3 *-original.sla + brand.py + ci.yml,
  which are the SOURCE files; template.sla is excluded because it is regenerated.)
  </action>
  <verify>
  <automated>cd /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s && ! grep -rinE 'gotham|minion pro|times roman|vollkorn' templates/*/build.py *-original.sla tools/sla_lib/builder/brand.py shared/ci.yml && grep -q 'Barlow Semi Condensed Regular' tools/sla_lib/builder/brand.py && grep -q 'Barlow Semi Condensed' shared/ci.yml && python3 -c "import ast,glob; [ast.parse(open(f).read()) for f in glob.glob('templates/*/build.py')]" && echo SWAP_OK</automated>
  </verify>
  <done>
  - No "gotham"/"minion pro"/"times roman"/"vollkorn" in build.py, *-original.sla, brand.py, ci.yml
  - brand.py deffont (both sites) = Barlow Semi Condensed Regular
  - ci.yml fonts: allow-list + every ci/* style font: are Barlow
  - All 16 build.py still parse as valid Python
  - The lone `Gotham Narrow Ultra Italic` in postkarte-vorlage-original.sla is gone
  </done>
</task>

<task type="auto">
  <name>Task 3: Remove the Schriftvergleiche feature and all dangling references</name>
  <files>site/src/pages/schriften/index.astro, site/src/data/schriften.json, site/src/data/schriften-bewertung.json, tools/fonts_compare_build.py, tools/font_variants.py, tools/font_instantiate.py, tools/sla_lib/tests/test_font_variants.py, site/public/schriften/, site/public/fonts/, templates/flyer-a6-hochformat-gruenes-cover/fonts/, shared/fonts/alternatives.yml, shared/fonts/alternatives/, site/src/layouts/Base.astro, site/src/pages/index.astro, site/src/styles/app.css, site/src/components/Lightbox.astro, .gitignore</files>
  <action>
  Delete the entire #42 comparison feature. PREREQUISITE: Task 1 already relocated
  the 4 Barlow TTFs out of shared/fonts/alternatives/ — confirm
  fonts/barlow-semi-condensed/ exists before deleting alternatives/.

  Deletions (use git rm; RESEARCH "Schriftvergleiche removal" table is the source):
  - site/src/pages/schriften/index.astro
  - site/src/data/schriften.json, site/src/data/schriften-bewertung.json
  - tools/fonts_compare_build.py
  - tools/font_variants.py (used ONLY by fonts_compare — grep-confirm clean elsewhere)
  - tools/font_instantiate.py (only referenced by fonts_compare/font_variants)
  - tools/sla_lib/tests/test_font_variants.py  (MUST delete — else CI's
    `unittest discover tools/sla_lib/tests` fails on the missing import)
  - site/public/schriften/ (barlow/montserrat/original/outfit/raleway/tahoma/urbanist)
  - site/public/fonts/ (5 self-hosted alt webfont families)
  - templates/flyer-a6-hochformat-gruenes-cover/fonts/ (outfit/urbanist/barlow/montserrat/raleway/tahoma incl. *.sla/PNGs)
  - shared/fonts/alternatives.yml AND shared/fonts/alternatives/ (whole dir — Barlow
    already relocated in Task 1; tahoma/ etc. go too)

  Edits (remove only the schriften-specific parts; keep the generic component):
  - site/src/layouts/Base.astro:54 — remove the `<li><a href={url('schriften/')}>Freie Schriften</a></li>` nav item.
  - site/src/pages/index.astro:56-59 — remove the `url('schriften/')` CTA card block.
  - site/src/styles/app.css — remove the Schriften-specific blocks (~188, 243, 356,
    441, 517: Vergleichsseite / Bewertungstabelle / Font-Karten / Switcher-Tabs /
    Empfehlung-Callout). Leave all non-schriften CSS intact.
  - site/src/components/Lightbox.astro — remove the Schriften-Switcher panel hooks
    (~25, ~192); KEEP the generic Lightbox.
  - .gitignore:30-44 — prune the now-dead font-comparison exception rules
    (`!shared/fonts/alternatives/**/*.ttf`, the tahoma re-exclude lines,
    `!site/public/fonts/**/*.ttf`). DO NOT touch the new
    `!fonts/barlow-semi-condensed/*.ttf` exception added in Task 1.

  Cosmetic (optional tidy, non-blocking): stray "schriften" word in
  site/src/pages/templates/[...id].astro:62 modal comment and zeitung-a4.md:284.

  Then re-grep the whole repo for residual references and confirm ZERO (excluding
  this issue's .issues/ docs which legitimately mention the feature).
  </action>
  <verify>
  <automated>cd /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s && test -f fonts/barlow-semi-condensed/BarlowSemiCondensed-Regular.ttf && ! test -e site/src/pages/schriften && ! test -e shared/fonts/alternatives && ! test -e tools/fonts_compare_build.py && ! test -e tools/sla_lib/tests/test_font_variants.py && ! test -e templates/flyer-a6-hochformat-gruenes-cover/fonts && ! grep -rniE "schriften/|fonts_compare|font_variants|font_instantiate|alternatives\.yml" --include='*.astro' --include='*.py' --include='*.ts' --include='*.js' --include='*.css' --include='*.json' --include='*.yml' . && python3 -m unittest discover tools/sla_lib/tests && echo REMOVE_OK</automated>
  </verify>
  <done>
  - schriften page/data/build-tool/test/generated-artifacts/alt-fonts all deleted
  - nav link, homepage CTA, schriften CSS blocks, Lightbox switcher hooks removed
  - .gitignore font-comparison exceptions pruned; Barlow print-font exception kept
  - `unittest discover tools/sla_lib/tests` passes (no missing-import failure)
  - Repo grep for schriften/fonts_compare/font_variants/alternatives.yml is clean
    (outside .issues/ docs)
  </done>
</task>

<task type="auto">
  <name>Task 4: Render all 16 templates headless with Barlow (skip stale-baseline diff)</name>
  <files>templates/*/template.sla, templates/*/preview.pdf, templates/*/page-*.png, templates/*/meta.yml</files>
  <action>
  Regenerate every template.sla from the Barlow build.py, render to preview.pdf +
  page PNGs, and auto-update meta SHAs. Use `--skip-visual-diff` because the old
  Gotham baselines are now invalid (Barlow's narrower metric → different wraps);
  diffing against them is meaningless and would fail spuriously.

  1. Smoke one template end-to-end first to confirm the pipeline + fonts work:
       bin/render-gallery flyer-a6-hochformat-gruenes-cover --skip-visual-diff
       pdffonts templates/flyer-a6-hochformat-gruenes-cover/preview.pdf | grep -iE 'barlow|dejavu|gotham|vollkorn|minion'
     Expect ONLY Barlow faces embedded, ZERO DejaVu/Gotham/Vollkorn/Minion.
  2. Render ALL renderable templates (16) with the font audit:
       bin/render-gallery --skip-visual-diff --audit
     This rebuilds every template.sla, preview.pdf, page-NN.png[+-hires] and
     auto-updates each meta.yml's build_py_sha256 + previews_for_sla (do NOT
     hand-edit those — let render-gallery write them).
  3. tischschild-a5-quer has build.py but NO baseline.pdf — render it too (it is in
     the renderable set; it produces 1 page). Task 6 creates its baseline.
  4. Audit embedded fonts across ALL previews — none may show DejaVu fallback:
       for p in templates/*/preview.pdf; do echo "== $p =="; pdffonts "$p" | grep -iE 'dejavu|gotham|vollkorn|minion times' && echo "  !! FALLBACK in $p"; done
     Any DejaVu line is a hard failure → investigate (missing fontconfig install or
     a missed font string from Task 2).

  Do NOT promote any baseline.pdf in this task — that is gated behind Task 5's
  visual sign-off (CONTEXT decisions 4 & 5).
  </action>
  <verify>
  <automated>cd /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s && bin/render-gallery --skip-visual-diff --audit && ! grep -rilE 'gotham|minion pro|times roman|vollkorn' templates/*/template.sla && for p in templates/*/preview.pdf; do pdffonts "$p" | grep -qiE 'dejavu|gotham|vollkorn|minion' && { echo "FALLBACK $p"; exit 1; }; done; bin/check-stale-previews && echo RENDER_OK</automated>
  </verify>
  <done>
  - All 16 templates re-rendered; every template.sla regenerated from Barlow build.py
  - No template.sla contains gotham/minion/times/vollkorn
  - No preview.pdf shows DejaVu/Gotham/Vollkorn/Minion fallback (Barlow only)
  - meta.yml SHAs auto-updated; bin/check-stale-previews exits 0
  - tischschild-a5-quer rendered (preview.pdf + PNG present)
  </done>
</task>

<task type="checkpoint:human-verify">
  <name>Task 5: Visual review of EVERY rendered page — alignment/centering — multiple passes</name>
  <files>templates/*/page-*.png, templates/*/preview.pdf, templates/*/build.py</files>
  <action>
  This is the mandatory gate from CONTEXT decisions 4 (and prerequisite for 5).
  Barlow is NARROWER than Gotham, so line-breaks, textbox fill, and optical
  centering shift. Review EVERY rendered page of EVERY template (~72 pages across
  16 templates per RESEARCH inventory) for: text overflow, clipped/truncated text,
  mis-centered or mis-aligned text, broken line-wraps, baseline collisions.

  The AGENT performs the image review (open each page-*.png / preview.pdf and
  inspect visually), and the USER does the explicit "mehrere visuelle Vergleiche"
  sign-off. Do MULTIPLE passes.

  Per-template page counts (RESEARCH inventory — review all):
    flyer-a6-hochformat-* (gruenes-cover/portraet/quadrat-im-bild/zweigeteilt): 6 each
    flyer-a6-querformat-gruenes-cover/quadrat-im-bild/zweigeteilt: 6 each; -portraet: 4
    falzflyer-z-falz-6-seitig-* (4 templates): 2 each
    plakat-a1-hochformat: 1 ; postkarte-a6-kampagne: 2 ; zeitung-a4: 9 ; tischschild-a5-quer: 1

  Helpers (run and read their output as part of each pass):
    bin/audit-alignment --all            # Issue #22 alignment audit (informational)
    bin/check-fontsizes templates/<id>/template.sla   # fractional FONTSIZE regressions
    pdffonts templates/<id>/preview.pdf  # re-confirm Barlow-only embedding

  When a page shows overflow / mis-alignment / clipping: fix in that template's
  build.py (frame width/height, leading/linesp, fontsize, alignment) — NEVER in
  template.sla — then re-render that one template:
    bin/render-gallery <id> --skip-visual-diff
  Repeat until ALL pages are clean across multiple passes. Document the passes
  (which templates inspected, issues found + fixes) in EXECUTION.md / commit body.

  Vollkorn-italic accent checkpoint (RESEARCH Risk R6): the former
  Vollkorn-italic accents now render as UPRIGHT Barlow Black (no local Barlow
  italic). On the affected pages (e.g. headline-vollkorn-italic style usages),
  judge whether losing the slant is acceptable. CONTEXT decision 1 accepts upright
  Barlow Black. ONLY if review proves a cursive accent essential: fetch
  BarlowSemiCondensed-Italic / -BlackItalic from Google Fonts (OFL) into
  fonts/barlow-semi-condensed/, add to the Docker install + Task 2 mapping, and
  FLAG to the user — do not silently add an italic.
  </action>
  <verify>
  <human>Every page of every template visually reviewed across MULTIPLE passes;
  no overflow / clipping / mis-centering / mis-alignment remains; Vollkorn-italic
  accent decision (upright Barlow Black vs pull italic) made and recorded; user
  has signed off that the renders are correct and ready for baseline promotion.</human>
  </verify>
  <done>
  - All ~72 pages inspected over multiple visual passes (documented)
  - All overflow/alignment/centering issues fixed in build.py and re-rendered
  - bin/audit-alignment --all and bin/check-fontsizes show no unexpected regressions
  - Vollkorn-italic accent decision recorded
  - Explicit sign-off recorded that renders are ready to become baselines
  </done>
</task>

<task type="auto">
  <name>Task 6: Promote new baselines, re-derive TOLERANCES.yml, run visual_diff + stale gate green</name>
  <files>templates/*/baseline.pdf, templates/*/TOLERANCES.yml, templates/*/diff.yml, templates/*/meta.yml, postkarte-vorlage-original.sla, plakat-a1-hochformat-original.sla, gruene-zeitung-vorlage-original.sla</files>
  <action>
  ONLY after Task 5 sign-off (CONTEXT decision 5). Promote the freshly rendered
  Barlow PDFs to the new comparison target and re-derive tolerances (the old
  Gotham-vs-InDesign wrap budgets no longer apply — RESEARCH LOW-confidence item,
  must be empirical).

  1. DSL-only templates (13, incl. tischschild-a5-quer which had no baseline): the
     freshly rendered preview.pdf IS the new reference:
       cp templates/<id>/preview.pdf templates/<id>/baseline.pdf
     For tischschild-a5-quer this CREATES its first baseline.pdf (and add the
     corresponding meta/diff entry if the schema requires one).
  2. original_sla templates (postkarte-a6-kampagne / plakat-a1-hochformat /
     zeitung-a4): render the (Task-2-edited) *-original.sla straight to baseline
     per docs/render-fidelity.md:118-131:
       xvfb-run -a --server-args="-screen 0 1024x768x24" \
         scribus -g -ns -py tools/_export_pdf.py <repo>/<id>-original.sla templates/<id>/baseline.pdf
     (postkarte → postkarte-vorlage-original.sla, plakat → plakat-a1-hochformat-original.sla,
      zeitung-a4 → gruene-zeitung-vorlage-original.sla).
  3. Re-derive each templates/<id>/TOLERANCES.yml empirically: run visual_diff /
     render-gallery WITHOUT --skip-visual-diff to get the actual Barlow drift, then
     set max_issues / per-category budgets to the new measured drift (not the old
     Gotham budgets — e.g. flyer-a6-hochformat-gruenes-cover's structural budgets up
     to 260 are stale). Keep budgets as tight as the real drift allows.
  4. Run a CLEAN render (diff now runs vs the NEW baselines) and the stale gate:
       bin/render-gallery            # no --skip-visual-diff — must pass
       bin/check-stale-previews      # must exit 0
  5. Local CI mirror:
       bin/validate                  # sla_diff (skipped where strict=false) + visual_diff
       bin/ci-local                  # mirrors pages.yml build-job gates
     Iterate TOLERANCES.yml until visual_diff is green WITHOUT loosening beyond the
     real drift. Do NOT hand-edit meta SHAs — render-gallery owns them.
  </action>
  <verify>
  <automated>cd /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s && test -f templates/tischschild-a5-quer/baseline.pdf && for b in templates/*/baseline.pdf; do pdffonts "$b" | grep -qiE 'dejavu|gotham|vollkorn|minion' && { echo "FALLBACK baseline $b"; exit 1; }; done; bin/render-gallery && bin/check-stale-previews && bin/validate && echo BASELINE_OK</automated>
  </verify>
  <done>
  - Every baseline.pdf is the Barlow render (no DejaVu/Gotham/Vollkorn/Minion)
  - tischschild-a5-quer now has a baseline.pdf
  - 3 original_sla baselines rendered from the Barlow-edited *-original.sla
  - TOLERANCES.yml re-derived from actual Barlow drift (not old Gotham budgets)
  - bin/render-gallery (no skip), bin/check-stale-previews, bin/validate all green
  </done>
</task>

<task type="auto">
  <name>Task 7: Document the print-font exception, final grep-clean, full test pass</name>
  <files>docs/render-fidelity.md, README.md</files>
  <action>
  Close out acceptance criteria for documentation and a clean final state.

  1. Document the deliberate print-pipeline vendoring exception (acceptance
     criterion): add a short note in docs/render-fidelity.md (font-pipeline
     section) — and/or README — stating that Barlow Semi Condensed TTFs are
     vendored under fonts/barlow-semi-condensed/ because Barlow is SIL OFL and
     Scribus renders locally with no CDN/webfont access (same justification as the
     existing Vollkorn vendoring). NO tool attribution anywhere.
  2. Final acceptance grep — must be clean over templates/ and all *.sla
     (template.sla now regenerated, so it is in scope here):
       grep -rinE 'gotham|minion|tahoma|times roman' templates/ *.sla
     Expect zero font-usage hits. (RESEARCH: Tahoma was only a negative example in
     the now-deleted comparison feature, so it should already be absent.)
  3. Full local CI mirror, both Python runners (CI uses unittest discover; dev uses
     pytest — run both):
       pytest tests/unit/ -q
       python3 -m unittest discover tools/sla_lib/tests
       bin/ci-local
  4. Confirm no residual schriften/alternatives references anywhere (outside
     .issues/ docs) — re-run the Task 3 grep.
  </action>
  <verify>
  <automated>cd /workspace/vorlagen/.worktrees/c8bg0-vorlagen-gotham-narrow-durch-barlow-semi-condensed-ersetzen-fremdschriften-und-s && ! grep -rinE 'gotham|minion|tahoma|times roman' templates/ *.sla && grep -qi 'barlow' docs/render-fidelity.md && pytest tests/unit/ -q && python3 -m unittest discover tools/sla_lib/tests && ! grep -rniE 'fonts_compare|font_variants|alternatives\.yml|schriften/' --include='*.py' --include='*.astro' --include='*.css' --include='*.json' --include='*.yml' --include='*.ts' --include='*.js' . && echo FINAL_OK</automated>
  </verify>
  <done>
  - Print-font (Barlow OFL) vendoring exception documented (render-fidelity.md / README)
  - `grep -rinE 'gotham|minion|tahoma|times roman' templates/ *.sla` is clean
  - pytest tests/unit/ AND `unittest discover tools/sla_lib/tests` both pass
  - bin/ci-local green; no residual schriften/alternatives references
  - No tool attribution in any added comment/doc
  </done>
</task>

</tasks>

<verification>
After all tasks, run the full local CI mirror (CI never renders — local artifacts
are the contract):
- fc-list | grep -ci 'barlow semi condensed'  → >= 4 ; fc-match "Barlow Semi Condensed" → Barlow
- grep -rinE 'gotham|minion|tahoma|times roman' templates/ *.sla  → empty
- for p in templates/*/{preview,baseline}.pdf; do pdffonts "$p"; done  → Barlow only, no DejaVu
- bin/render-gallery                 → green (diffs vs NEW baselines)
- bin/check-stale-previews           → exit 0 (SHA gate; the CI-blocking one)
- bin/validate                       → green
- bin/ci-local                       → green
- pytest tests/unit/ -q              → pass
- python3 -m unittest discover tools/sla_lib/tests  → pass (schriften test removed)
- repo grep for schriften/fonts_compare/font_variants/alternatives.yml  → empty (outside .issues/)
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria:
- Default font of all templates is Barlow Semi Condensed; `grep -rin "gotham|minion|tahoma|times roman"` over templates/ + *.sla is clean (Tasks 2, 4, 7).
- Barlow provisioned locally; `fc-match "Barlow Semi Condensed"` returns a Barlow TTF; renders show Barlow, no DejaVu fallback (Tasks 1, 4, 6).
- Schriftvergleiche feature fully removed (page, data, build tool, generated artifacts, nav link, alt fonts) — no dead references/links (Task 3, re-verified Task 7).
- All templates re-rendered; EVERY page visually reviewed (multiple passes) — alignment/centering correct, no overflow/clipping (Task 5).
- New baseline PDFs as comparison target; visual_diff/tests green against new baselines; CI stale-previews gate green (Task 6).
- No tool attribution in commits/code; print-pipeline font exception documented (Task 7; enforced every commit).
</success_criteria>
