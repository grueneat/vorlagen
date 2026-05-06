# Render-fidelity workflow

This document explains how the headless Scribus pipeline achieves byte-identical output to the user's Scribus 1.6.4 desktop export, and how to maintain that fidelity as templates and fonts evolve.

---

## Why fonts must be installed

Without the brand fonts, Scribus falls back to DejaVu Sans for every missing family. Measured impact:

| Font missing | Drift on worst page |
|---|---|
| Gotham Narrow (body, headlines, captions) | ~55,000 px / page at 96 dpi |
| Vollkorn Black Italic (störer badge, masthead) | ~7,000 px / page at 96 dpi |
| Both missing | Full layout difference — essentially unrecognisable |

Once both are installed and `fc-cache -f` is run, headless renders are **0 px different** from the user's Scribus desktop export across all 17 pages of all 3 templates (zeitung-a4-grun, plakat-a1-hochformat, postkarte-a6-kampagne).

Note: Scribus builds a per-user font cache at `~/.config/scribus/checkfonts150.xml`. This file is auto-regenerated on the first Scribus run after fonts change. In a fresh container the first render incurs a one-time ~3 sec cache rebuild; subsequent renders are fast.

---

## What's installed and where

### Font files

- **Location in container:** `/usr/local/share/fonts/gruene/`
- **What's installed:**
  - `GothamNarrow-*.otf` — 16 files covering all weights (Book, Bold, Black, Ultra, Ultra Italic, Medium, Medium Italic, Light, Light Italic, Thin, Thin Italic, Extra Light, Extra Light Italic, Black Italic, Bold Italic, Book Italic)
  - `Vollkorn-BlackItalic.ttf` — the specific static instance (see "Why static, not variable Vollkorn" below)
- **Source files:** `/root/workspace/fonts/` (gitignored; user-controlled drop zone)
  - `fonts/Gotham Narrow/<weight>/<weight>.otf` — 16 files
  - `fonts/Vollkorn/static/Vollkorn-BlackItalic.ttf` — required static instance

### Fontconfig alias

- **Location in container:** `/etc/fonts/conf.d/50-vollkorn-family-alias.conf`
- **Source in repo:** `shared/fonts/50-vollkorn-family-alias.conf`
- **What it does:** maps the `Vollkorn Black Italic` family name (as referenced in Scribus SLAs) to the actual font's `family=Vollkorn + style="Black Italic"`. Without this alias, fontconfig cannot match the lookup and Scribus falls back to DejaVu.

### Verification

```bash
# Font count (expect 17 in a dev container with both families installed)
fc-list | grep -ciE 'gotham narrow|vollkorn'

# Vollkorn alias resolution (expect: Vollkorn-BlackItalic.ttf: "Vollkorn" "Black Italic")
fc-match "Vollkorn Black Italic"

# Gotham Narrow lookup
fc-match "Gotham Narrow Book"
```

---

## Why static, not variable, Vollkorn

The Google Fonts distribution of Vollkorn ships a variable font (`Vollkorn-Italic[wght].ttf`). When instantiated at weight=black, it produces glyph metrics that differ subtly from the user's `Vollkorn-BlackItalic.ttf` static instance. That difference maps to ~7,000 px/page drift on the affected templates.

**Rule:** install only the static `Vollkorn-BlackItalic.ttf`. Do NOT place the variable `Vollkorn-Italic[wght].ttf` in `fonts/Vollkorn/static/` alongside it — fontconfig's family-name resolution is non-deterministic when multiple files provide the same style, and the wrong file will occasionally win.

---

## The "fix typos at the source, not the renderer" principle

### What happened (D1 lesson)

The Zeitung SLA originally had `FONTSIZE="11.7"` on 97 PAGEOBJECT ITEXT elements across body-text frames on pages 5, 6, 8, and 10. This was a mouse-wheel nudge in Scribus's properties panel — the author inadvertently moved the size from 12 to 11.7pt and saved.

Observed impact: the user's Scribus 1.6.4 silently rounds 11.7 → 11.0 in PDF output (a quirk of Scribus's PDF export); our Scribus 1.6.3 honored 11.7 literally. The body text rendered at slightly different sizes, causing ~233,000 px diff across 4 pages. This looked like a Scribus-version difference — but the renderer was correct. The SLA was wrong.

**Fix:** the user corrected all 97 PAGEOBJECT ITEXTs in their Scribus (FONTSIZE=12) and re-saved. The renderer was never patched.

### The lingering 42 FONTSIZE=11.7 strings

The corrected SLA still contains 42 `FONTSIZE="11.7"` strings. These live inside `<FRAMEOBJECT>` elements (orphan/pasteboard text frames, `OwnPage=-1`). They are NOT rendered onto pages, and `tools/sla_diff.py::drop_frameobjects` removes them before structural comparison. They are harmless.

Note: an earlier version of this project's documentation described these as "STYLE definitions". They are in fact FRAMEOBJECTs. The distinction matters for the regression check.

### Regression protection

`bin/check-fontsizes` (new) runs as a preflight inside `bin/validate`. It walks only PAGEOBJECT subtrees and fails with exit 1 if any ITEXT has a fractional FONTSIZE. It deliberately ignores FRAMEOBJECT and MASTEROBJECT elements (the 42 inert pasteboard items do NOT trigger it).

If the checker fires:

1. Open the flagged SLA in Scribus.
2. Locate the text frame on the page indicated by `OwnPage=N`.
3. Correct the font size to an integer in the properties panel.
4. Save and re-export (re-run the pipeline).

---

## Adding a new font to fonts/

1. Drop the font file(s) into `/root/workspace/fonts/<family>/...` (matching the existing layout: `fonts/Gotham Narrow/<weight>/<weight>.otf`).
2. Rebuild the dev container:
   ```bash
   docker build -f Dockerfile.claude /root/workspace -t scribus-pipeline-dev
   ```
3. Verify the font is registered:
   ```bash
   docker run --rm scribus-pipeline-dev fc-list | grep "<family>"
   ```
4. If Scribus references the font by a non-standard family name (full name used as family), add a fontconfig alias at `shared/fonts/<NN>-<family>-alias.conf`. The `50-` numeric prefix is standard; higher numbers take precedence over lower numbers. Mirror the structure of `shared/fonts/50-vollkorn-family-alias.conf`.

---

## Rebaselining a template's baseline.pdf (gated procedure)

### When to rebaseline

- The original SLA changes intentionally (e.g. user fixes a typo, updates a master page).
- Scribus version bumps produce a different (but correct) output.
- The font set changes (new Gotham Narrow version, etc.).

Rebaselining is NOT casual. Each baseline.pdf is the production reference: it must match the user's desktop Scribus export byte-for-byte. Rebaseline only when you can verify the new output against a fresh user-exported reference PDF.

### How to rebaseline

```bash
# Render the original SLA headless in the font-installed container
xvfb-run -a --server-args="-screen 0 1024x768x24" \
  scribus -g -ns -py tools/_export_pdf.py \
  <id>-original.sla templates/<id>/baseline.pdf

# Verify pdffonts shows brand fonts, not DejaVu
pdffonts templates/<id>/baseline.pdf | grep -iE 'gotham|vollkorn|dejavu'

# Run the full validation pipeline
bin/validate
```

### Verify against the user's reference PDF

If the user exports a new reference PDF (e.g. after an SLA correction):

1. Place the reference PDF at `/tmp/desktop.pdf`.
2. `bin/validate` must exit 0 (≤3 px per template at 150 dpi — Qt anti-aliasing floor).
3. Cross-verify at 0% fuzz (see "Verifying a new SLA render" below).

### Document the rebaseline

Include a clear reason in the commit message:

```
fix(baselines): rebaseline zeitung after FONTSIZE typo correction (D1)

User corrected FONTSIZE="11.7" → 12 on 97 PAGEOBJECT ITEXTs in Scribus.
New baseline is byte-equivalent to corrected export (0 px at 0% fuzz,
all 14 pages). bin/validate exits 0 (≤3 px worst page).
```

---

## Verifying a new SLA render matches your desktop Scribus export

Use this procedure whenever the user provides a new reference PDF and you need to confirm the headless pipeline matches it:

```bash
# 1. Place the reference PDF
cp /path/to/your-desktop-export.pdf /tmp/desktop.pdf

# 2. Render the SLA headless
xvfb-run -a --server-args="-screen 0 1024x768x24" \
  scribus -g -ns -py tools/_export_pdf.py your.sla /tmp/headless.pdf

# 3. Rasterise both at 96 dpi
pdftoppm -r 96 -png /tmp/desktop.pdf /tmp/desktop
pdftoppm -r 96 -png /tmp/headless.pdf /tmp/headless

# 4. Pixel-diff each page at strict 0% fuzz
for f in /tmp/desktop-*.png; do
  page=$(basename "$f" .png | sed 's/desktop-//')
  diff_count=$(compare -metric AE -fuzz 0% "$f" "/tmp/headless-$page.png" "/tmp/diff-$page.png" 2>&1 || true)
  echo "page $page: $diff_count px"
done
```

Expect 0 px per page. If a page drifts:

- `fc-list | grep -iE 'gotham narrow|vollkorn'` — fonts loaded?
- `pdffonts /tmp/headless.pdf` — brand fonts embedded (not DejaVu)?
- `bin/check-fontsizes` — any fractional FONTSIZE in the SLA?
- `md5sum your.sla /root/workspace/originals/<corrected>.sla` — SLA is the right version?

---

## Out of scope (tracked elsewhere)

### ECI ICC profiles

The SLAs reference `Adobe RGB (1998)` and `PSO Uncoated ISO12647 (ECI)` ICC profiles. Neither this container nor the user's macOS Scribus installation has them by default; both fall back to sRGB / ISO Coated v2. The substitution is symmetric, so no visual drift results. Installing the ECI profiles would improve PDF/X-4 technical compliance (useful if sending to a commercial printer that validates metadata) but has zero impact on visual fidelity or pixel diff.

### CI font provisioning

CI runners (GitHub Actions) do not have access to the proprietary Gotham Narrow fonts. The `validate-reproductions` step in `.github/workflows/pages.yml` runs `sla_diff --strict` (structural gate) but currently skips `visual_diff`. This is tracked in a separate follow-up issue. See the TODO comment in `pages.yml` for the issue reference.

### Bundling Gotham Narrow in the public repo

License-blocked. Gotham Narrow is proprietary (Hoefler & Co.). The gitignore blocks `*.otf`, `*.ttf`, `*.ttc` and `/fonts/` to prevent accidental commits.

---

## Cross-references

- `shared/fonts/README.md` — install dance for fonts/ (drop zone layout, container build, macOS dev note)
- `docs/diff-tolerance.md` — per-template pixel-diff thresholds, rebaselining workflow context
- `bin/check-fontsizes` — preflight regression checker for fractional FONTSIZE in PAGEOBJECT scope
- `shared/fonts/50-vollkorn-family-alias.conf` — fontconfig alias XML (canonical source, COPYed by Dockerfile.claude)
