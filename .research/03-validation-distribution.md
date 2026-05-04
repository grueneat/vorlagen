# Validation, Visual Diffing, and GitHub Pages Distribution for a Scribus Template Pipeline

Research report for: Scribus .sla templates in git, CI-rendered to PDF and PNG, compared against an InDesign-exported "golden master", and published to a GitHub Pages gallery for party local chapters and volunteers.

---

## 1. Visual regression and image diffing

### 1.1 Pixel diff vs perceptual diff — the core decision

Two algorithm families dominate:

- **Pixel diff with anti-alias detection** (pixelmatch, odiff, looks-same). These walk pixels, flag changes, and use a small neighbourhood check to ignore anti-aliasing noise. Fast, deterministic, and the right tool when you want exact-byte fidelity (logo position, brand colour squares, header layouts).
- **Perceptual / structural diff** (SSIM, DSSIM, ΔE-based, resemble.js). These score how similar two images "look" to a human. SSIM ≥ 0.99 typically means "no visible change"; teams pick a threshold around 0.01 distance for visual regression.

For a print-template pipeline rendered through Scribus, **a hybrid is the realistic answer**: pixel diff with AA-tolerance for layout regions (header, logos, CTA buttons, bleed marks) and SSIM for body-text regions where font hinting will wobble between Linux runners and macOS contributors. This matches what mature teams do and is what tools like `jest-image-snapshot` (dual-mode SSIM + pixelmatch) already implement.

### 1.2 Tool ranking (open source, headless, CI-friendly)

| Tool          | Algorithm               | Speed                 | Best for                                                  |
| ------------- | ----------------------- | --------------------- | --------------------------------------------------------- |
| **odiff**     | pixel + AA, SIMD, Zig   | Fastest at large size | Default for full-page A1 plakat renders                   |
| **pixelmatch**| pixel + perceptual ΔE   | Fastest small         | Per-region thumbnail diffs                                |
| **dssim**     | multiscale SSIM in Rust | Fast                  | Body-text "looks-like" gate                               |
| **resemble.js**| pixel, masking         | Slower                | Bounding-box masking (skip dynamic chapter name)          |
| **looks-same**| pixel + AA              | Medium                | Easy Node API, masking                                    |
| **ImageMagick `compare`** | RMSE/AE/PSNR/MAE | Slow              | Quick ad-hoc CLI diff in shell scripts                    |
| **reg-suit**  | wraps pixelmatch        | Medium                | Full workflow with S3 baseline storage and HTML report    |

`reg-suit` is the most "out-of-the-box" — it solves baseline storage by pushing snapshots to S3 or GCS so the repo stays small, and it auto-publishes a comparison HTML report. For a small team that does not want to build infrastructure, reg-suit is the closest open-source equivalent to Percy/Chromatic.

### 1.3 PDF-specific path

PDFs need to be rasterised before diffing. Three options:

- **`pdftocairo -png -r 300`** (Poppler) — Cairo-based, the most consistent renderer between platforms, handles CMYK and embedded ICC reasonably.
- **`pdftoppm -png -rx 300 -ry 300`** (Poppler) — slightly faster, uses Splash backend, occasionally diverges from Cairo on complex transparency.
- **`gs -sDEVICE=png16m -r300`** (Ghostscript) — most authoritative for print-intent rendering because it is the same engine many printers use, but slowest and largest install.

The `diff-pdf-visually` Python tool wraps `pdftocairo` + ImageMagick `compare` and is a useful reference implementation. For per-page diffing, render every page to a separate PNG with a deterministic name (`template-name_p01.png`) and run odiff against the golden master rasters.

### 1.4 Font rendering between machines

Font rendering differs visibly between Ubuntu (FreeType + Cairo, hinting on) and macOS (Quartz, no hinting, full pixel anti-aliasing). Concrete defenses:

1. **Render only on Linux in CI**, and never accept a baseline rendered on a contributor's Mac. Pin the runner image (e.g. `ubuntu-24.04`) so FreeType and fontconfig versions are stable.
2. **Containerise Scribus** (Docker image with pinned Scribus, FreeType, Cairo, Poppler, fontconfig). Render in the same container locally and in CI.
3. **Bundle fonts in repo or via Git LFS**, do not depend on system fonts.
4. Set a small SSIM tolerance (0.005-0.01) to absorb the inevitable subpixel jitter without hiding real layout breakage.

### 1.5 DPI normalisation

Always render the rendered PDF and the golden-master PDF at the **same DPI** (300 for print preview, 150 for thumbnails) using the **same tool**. A 600 vs 300 raster will show "infinite" diff. Normalise PNG colour profile to sRGB before diffing (CMYK in PNG is non-portable).

---

## 2. PDF preflight (this is the print-correctness gate)

The output is going to a press, so preflight is not optional. Open-source coverage:

| Tool             | Strengths                                                    | Weaknesses                                  |
| ---------------- | ------------------------------------------------------------ | ------------------------------------------- |
| **veraPDF**      | The reference open-source PDF/A validator; usable for many PDF/X-style structural checks via custom policy profiles. Java, dual-licensed GPLv3+ / MPLv2+. | Designed for PDF/A first; PDF/X coverage via policy checker. |
| **Ghostscript**  | Convert to PDF/X-1a or PDF/X-4, embed ICC, test rendering. | Conversion, not validation.                 |
| **pdfcpu**       | Go binary, only one that validates PDF 2.0; CLI-friendly; strict and relaxed modes. | Structural validation, not print-intent.    |
| **qpdf --check** | Structural integrity, decompression, xref check.             | Not preflight-aware.                        |
| **callas pdfToolbox / Enfocus PitStop** | Industry standard, scriptable.            | Proprietary. Mention as escape hatch.       |

**Recommended stack:** Scribus exports → `pdfcpu validate -strict` (structure) → `qpdf --check` (cross-reference health) → `veraPDF --profile <custom-pdfx-profile>` (print conformance) → custom python checks for the things none of these do well.

The project-specific checks none of the validators cover off-the-shelf:

- Every image embedded at ≥ 300 dpi at the placed size (use `pdfimages -list`).
- All colour spaces are CMYK or DeviceGray, no RGB sneak-through (parse colour spaces with `mutool info` or `pdftoppm -gray` heuristics; pdfcpu can list resources).
- All fonts are embedded and subsetted (pdfcpu lists fonts; veraPDF flags missing).
- Bleed box is ≥ 3 mm beyond trim box (`pdfinfo -box`).
- No transparency in spot-colour overprint (mutool, callas-only for full check).

Open German "Druckdatencheck" tools (check4print.com, the MPA online checker) are services, not libraries. For an internal tool, build the checks in Python on top of `pdfcpu` + `veraPDF` + `pdfimages`. There is no first-class open-source German Preflight library; Markzware FlightCheck and callas pdfToolbox are the proprietary norm.

---

## 3. Template metadata and registry

Use a **YAML frontmatter sidecar** per template, named `<template-basename>.meta.yml`, following the "sidematter" convention so a template directory contains:

```
postkarte-vorlage/
  postkarte-vorlage.sla
  postkarte-vorlage.meta.yml
  golden/postkarte-vorlage.pdf
  golden/postkarte-vorlage_p01.png
  preview/  (built artifact, ignored in git)
```

The `meta.yml` should carry: `id`, `title_de`, `title_en`, `format` (A4/A1/postcard/banner), `audience` (party-staff, local-chapter, volunteer, public), `language`, `version` (semver), `tags`, `description`, `paper`, `bleed_mm`, `colour_profile`, `fonts_required`, `last_reviewed`, `maintainer`. Link a JSON Schema via `$schema` so VS Code / IDEs validate as people edit. This same YAML drives the gallery: the static-site builder reads every `.meta.yml`, generates the gallery page, and embeds the data on each detail page.

**Asset bundling and Git LFS.** SLA files are XML-text and version well in plain git. The case for LFS:

- Bundle fonts (TTF/OTF, often 5-50 MB each): YES, LFS them. Even better: commit fontsource files (UFO/Glyphs) and let CI build TTFs, but for a comms team this is overkill — just LFS the TTFs.
- ICC profiles: small (2-4 MB), commit directly, no LFS needed.
- Reference images: yes, LFS. Plakat A1 images are commonly 20-100 MB.
- Golden-master PDFs: LFS. They are binary and updated rarely.
- Generated PNG previews and built PDFs: never commit — they are CI artifacts and Pages-published files.

LFS bandwidth costs at GitHub can sting for binary-heavy repos with many fetches. If costs grow, mirror to S3 or move to Azure DevOps git (free LFS) or a self-hosted LFS server.

---

## 4. CI/CD patterns for design assets

### 4.1 Headless Scribus in CI

Scribus has no `--to-pdf` flag. The supported headless path is `scribus -g -py export.py -- *.sla`, where `export.py` uses the Scribus Python API (`scribus.openDoc`, `scribus.savePageAsPDF` / `scribus.saveAs`). This is well documented as a workaround. In a GitHub Actions Linux runner, install Scribus (`apt-get install scribus`) plus the system fonts you need (`fonts-noto`, `fonts-liberation`, plus your bundled TTFs).

Better: **build a Docker image** `scribus-render:1.6.x` once, pinned, push to GHCR, and use it as the container in the action. This is how you keep font and rendering output deterministic.

### 4.2 Matrix builds

Matrix on `template` (find every `.sla`) × `variant` (full PDF, draft PDF, web PNG, social OG image). Use unique artifact names like `${{ matrix.template }}-${{ matrix.variant }}` and merge in a final job before publishing.

### 4.3 Caching

Cache `~/.local/share/fonts`, the Docker image layers, and the rasterised golden-masters keyed by their SHA. Scribus startup is slow; if you run dozens of templates in one job, batch them inside a single Scribus invocation rather than starting Scribus per file.

### 4.4 PR preview comments

`getsentry/action-visual-snapshot` is archived (Oct 2023) but still a useful reference; it uploads snapshots as artifacts and runs odiff. For an active equivalent, combine:

- `actions/upload-artifact` for the rendered PNGs.
- `peter-evans/create-or-update-comment` to post a sticky PR comment.
- Embed images via the artifact's public-after-merge URL or push to a `preview/<pr-number>/` path on a dedicated `gh-pages-previews` branch.

`opengisch/comment-pr-with-images` is a working off-the-shelf option that posts changed images directly into PR comments.

### 4.5 Versioning

Plain semver per template, encoded in `meta.yml`. semantic-release is overkill for a template repo and assumes one project per repo; better to drive versions via Conventional Commits scoped by template directory and a small custom script that bumps only the templates that changed in a PR. Tag releases as `postkarte-vorlage@1.4.0` (npm-style scoped tags).

---

## 5. GitHub Pages gallery

### 5.1 Framework choice

| SSG       | Fit for this use case                                                                |
| --------- | ------------------------------------------------------------------------------------ |
| **Astro** | Best default. Reads YAML frontmatter as content collections out of the box, ships zero JS, produces a fast gallery, easy to build search and filters with a sprinkle of client-side JS. Strong template ecosystem in 2026. |
| **11ty**  | Smallest, simplest, no Node frameworks. Excellent if the team is JS-allergic.        |
| **Hugo**  | Fastest builds, mature gallery themes (`hugo-theme-gallery`, `gallerydeluxe`). Slightly clunkier search/filter story without third-party JS (e.g. Pagefind). |
| **Jekyll**| GitHub Pages native (no Action needed) but the slowest and least flexible of the four. |

For "gallery with search/filter by audience/format/occasion + per-template detail page with PDF embed," **Astro** is the pragmatic 2026 choice. It treats `meta.yml` as a content collection, validates against a Zod schema, and the islands let you drop in a client-side filter without shipping a 200 KB framework. Hugo is a strong runner-up if the team values simplicity over flexibility.

### 5.2 Per-template detail page

- Hero PNG (first page, web-optimised JPG/AVIF, 1200 px wide).
- PDF embed via `pdf.js` (use `pdfjs-viewer-element` or `EmbedPDF` for a drop-in component) for in-browser preview.
- Download row: print-PDF, web-PDF (smaller, RGB), `.sla` source, optional `.idml`, ZIP of fonts and assets.
- PNG carousel for each page.
- Metadata panel from `meta.yml`.
- Changelog (CHANGELOG.md per template, rendered as MDX).
- Open Graph image: auto-generate per template at build time using the hero PNG plus a templated overlay (Astro can do this with `@vercel/og` or `satori`); pin a 1200x630 PNG into `<head>`.

### 5.3 Search and filter

Pagefind for full-text search (works with any SSG, no backend), plus client-side filter buttons for audience and format driven by the YAML frontmatter. This is the same pattern themes.gohugo.io and figma.com/community use at small scale.

### 5.4 Internal-only access

GitHub Pages itself is public-only on free accounts; GitHub Pro/Team allows private Pages on private repos. For party-internal distribution, two practical paths:

- **Cloudflare Pages + Cloudflare Access**, free for up to 50 users, real SSO/email-OTP, reverse-proxied in front of a public deploy. This is the cleanest answer.
- **Static site behind Cloudflare Workers Basic Auth** — simple shared password, fine for "internal but not sensitive" lists; easy to set up with the `cloudflare-pages-auth` template.
- Avoid the "password-protected ZIP" pattern. It kills shareability and a single leak compromises forever.

### 5.5 Distribution sizing

Publish previews via Pages (small files, CDN-cached). Distribute large binaries (full bleed PDFs, font ZIPs, IDML) via **GitHub Releases** rather than `raw.githubusercontent.com` or Pages — Releases have higher bandwidth limits, generate stable URLs, and version cleanly.

---

## 6. Compare-against-golden-master workflow

### 6.1 Storing the golden master

Commit the InDesign-exported reference PDF to the repo (LFS) under `golden/<template>.pdf`. Pre-render the master to PNGs at the chosen DPI (e.g. 300) and **also commit those PNGs** (LFS). Reasons:

- The rasteriser version (Cairo, Ghostscript) drifts. A pre-rendered PNG is a stable reference; you only re-rasterise when the master PDF changes.
- Diffs become "Scribus PNG vs Master PNG", trivial to debug.

### 6.2 Per-region tolerance

Keep a small `regions.yml` per template:

```
regions:
  - name: header
    bbox: [0, 0, 1240, 200]
    mode: pixel
    tolerance: 0
  - name: body
    bbox: [50, 220, 1190, 1500]
    mode: ssim
    tolerance: 0.01
  - name: footer-disclaimer
    bbox: [0, 1500, 1240, 1748]
    mode: ignore
```

The CI diff job clips each region from both images, runs the chosen algorithm with its tolerance, and aggregates pass/fail. Region masks also let you ignore date stamps or chapter names that change per output.

### 6.3 Approve-new-baseline workflow

There is no perfect open-source equivalent to Chromatic for PDFs, but the pattern works:

1. CI diff fails.
2. CI uploads `actual/`, `expected/`, `diff/` to artifacts and posts a PR comment with side-by-side images.
3. Reviewer either rejects or labels the PR `accept-baseline`.
4. A workflow triggered by the label re-renders, copies `actual/` over `golden/`, commits "chore: bless new baseline for <template>" via a bot, and re-runs the diff (now green).

This matches `reg-suit`'s "approved baseline" semantics without locking you into reg-suit.

### 6.4 Diff publishing in PR comments

Build a single composite PNG per page (`expected | actual | diff`) and a one-line summary table:

```
| page | mode  | score   | result |
| 1    | pixel | 0.0003  | pass   |
| 2    | ssim  | 0.987   | fail   |
```

Post via `peter-evans/create-or-update-comment` with the artifact URL.

---

## 7. Sketched CI workflow

```yaml
name: render-validate-publish
on:
  pull_request:
    paths: ['templates/**', 'golden/**']
  push:
    branches: [main]

jobs:
  discover:
    runs-on: ubuntu-24.04
    outputs:
      matrix: ${{ steps.set.outputs.matrix }}
    steps:
      - uses: actions/checkout@v4
        with: { lfs: true }
      - id: set
        run: echo "matrix=$(ls templates/*/meta.yml | jq -R -s -c 'split("\n")[:-1]')" >> $GITHUB_OUTPUT

  render:
    needs: discover
    runs-on: ubuntu-24.04
    container: ghcr.io/<org>/scribus-render:1.6.1
    strategy:
      matrix:
        template: ${{ fromJson(needs.discover.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
        with: { lfs: true }
      - name: Render PDF
        run: scribus -g -py ci/export.py -- "${{ matrix.template }}/*.sla"
      - name: Rasterise PDF
        run: pdftocairo -png -r 300 out/${{ matrix.template }}.pdf out/${{ matrix.template }}_p
      - name: Preflight
        run: |
          pdfcpu validate -strict out/${{ matrix.template }}.pdf
          qpdf --check out/${{ matrix.template }}.pdf
          verapdf --profile profiles/pdfx-custom.xml out/${{ matrix.template }}.pdf
          python ci/check_dpi_cmyk_bleed.py out/${{ matrix.template }}.pdf
      - name: Visual diff vs golden
        run: python ci/diff.py golden/${{ matrix.template }} out/${{ matrix.template }} regions/${{ matrix.template }}.yml
      - uses: actions/upload-artifact@v4
        with:
          name: render-${{ matrix.template }}
          path: out/${{ matrix.template }}/
          retention-days: 30

  comment:
    needs: render
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/download-artifact@v4
      - name: Compose PR comment
        run: python ci/post_pr_comment.py
      - uses: peter-evans/create-or-update-comment@v4
        with: { issue-number: ${{ github.event.pull_request.number }}, body-file: comment.md }

  publish:
    needs: render
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
      - name: Build Astro gallery
        run: pnpm i && pnpm build
      - uses: actions/upload-pages-artifact@v3
      - uses: actions/deploy-pages@v4
```

This sketch is intentionally loose — production would need: separate PR-preview-pages branch for ephemeral previews, baseline-bless workflow, Release workflow for fonts/assets ZIPs, error handling in `export.py`, and Cloudflare Access in front of Pages if internal-only.
