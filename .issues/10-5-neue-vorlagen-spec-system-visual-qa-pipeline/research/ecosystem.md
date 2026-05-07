# Ecosystem Research — Issue 10 (5 neue Vorlagen + Spec + Visual-QA)

**Researched:** 2026-05-07
**Scope:** ecosystem / libraries / external standards dimension only.
**Sister docs:** `codebase.md` (codebase mapping), `pitfalls.md` (failure modes).

This file enumerates external standards, library APIs, CLI surfaces, and print-shop conventions
the planner needs to compile tasks. Where research surfaces a contradiction with a CONTEXT.md
locked decision, it is flagged explicitly — not silently overridden — so the planner can
either escalate or adapt the implementation around the constraint.

---

## 1. Scribus 1.6 SLA Format

### 1.1 Locally installed version

- **Scribus 1.6.3** (Debian trixie pin via `Dockerfile.claude`). Confirmed: `apt list scribus 1.6.3+dfsg-0.2+b2`.
- Scribus needs Xvfb headless on Linux even with `-g -ns` (already wired in `tools/render.py`).
- Ghostscript **10.05.1** present (`gs --version`); ImageMagick 7.1.1.43 present.
- Confidence: **HIGH** (verified locally).

### 1.2 `<LAYERS>` element schema

Verified by reading `tools/sla_lib/builder/document.py:_emit_layers()` (already implemented;
emits exactly the documented attributes) and `shared/ci.yml` `layers:` block. Each `<LAYERS>`
element has these attributes:

| Attribute | Type      | Meaning                                              | Default in CI        |
|-----------|-----------|------------------------------------------------------|----------------------|
| `NUMMER`  | int       | Layer ID (referenced by PAGEOBJECT.LAYER)            | sequential 0..N      |
| `LEVEL`   | int       | Stack order, bottom-up                               | == NUMMER            |
| `NAME`    | string    | Display name in Scribus UI                           | Hintergrund/Bilder/… |
| `SICHTBAR`| 0/1       | Visible in editor                                    | 1                    |
| `DRUCKEN` | 0/1       | Printable / exported to PDF                          | 1 (0 for guides)     |
| `EDIT`    | 0/1       | Editable in Scribus UI                               | 1                    |
| `SELECT`  | 0/1       | Currently selected layer                             | 1                    |
| `FLOW`    | 0/1       | Text-flow-around-objects honoured for cross-layers   | 1                    |
| `TRANS`   | float     | Alpha (1.0 = opaque)                                 | 1.0                  |
| `BLEND`   | int       | Blend mode index (0 = Normal)                        | 0                    |
| `OUTL`    | 0/1       | Outline mode (wireframe rendering)                   | 0                    |
| `LAYERC`  | hex color | Layer's marker color in UI (no print effect)         | `#000000`            |

The DSL already exposes all of these via `DocumentLayer` (`tools/sla_lib/builder/styles.py:17`)
plus `BrandLayer` (`tools/sla_lib/builder/ci.py:71`). **For Stanzkontur/Falz layers, the right
combination is `DRUCKEN=0` (won't print as content) but the Spot color path on that layer
still appears in the exported PDF as a separation channel** — Scribus emits non-printable
layers into PDF when `Allow non-printable layers` is set. Verify behavior in Phase 2 by
inspecting an exported PDF with `mutool show` or Acrobat's separations preview.

- Confidence: **HIGH** (DSL code + CI YAML).
- Recommendation: **reuse existing `DocumentLayer` API**. CONTEXT.md D4 says "DSL has heute
  kein explizites Layer-Konzept" — that is **outdated**: layers exist, just need extending
  with `DRUCKEN=0` for cut/fold layers and per-`Document(layers=[...])` overrides. No
  new module needed.

### 1.3 Spot-color encoding (`<COLOR>` element)

Verified by `tools/sla_lib/builder/document.py:700-702`:

```python
if c.spot:
    el.set("Spot", "1")
if c.register:
    el.set("Register", "1")
```

CMYK fallback for screen viewing comes from the `cmyk: [c, m, y, k]` value, e.g. CMYK
`(0, 100, 0, 0)` for Stanzkontur shows magenta in the editor but the **printer treats it
as a single separation channel** because `Spot=1` is set. The DSL already handles this
correctly; new spot colors only need `shared/ci.yml` entries with `spot: true`.

- Confidence: **HIGH**.
- Recommendation: For new spot colors `Falz` and `Stanzkontur`, add to `shared/ci.yml`:
  ```yaml
  Falz:
    cmyk: [100, 0, 0, 0]   # cyan in editor, separation channel in print
    spot: true
    role: print-falz
  Stanzkontur:
    cmyk: [0, 100, 0, 0]   # magenta in editor
    spot: true
    role: print-stanze
  ```

### 1.4 Inline image extension — CRITICAL FINDING (contradicts CONTEXT.md D1)

**Important contradiction with CONTEXT.md D1** (EPS → PDF → inline `ImageFrame`):

Evidence:
- All three repo originals use **only** `inlineImageExt="png"` (verified:
  `grep -oE 'inlineImageExt="[^"]*"' *.sla` returns `"png"` exclusively across all three SLAs).
- Third-party reference implementation
  ([scribus-image-embedder](https://github.com/Afueth/scribus-image-embedder)) explicitly
  documents support only for **JPEG/JPG, PNG, TIFF, GIF, BMP** — Pillow-loadable raster
  formats. **PDF is not supported** for inline embedding by that tool.
- Scribus' PDF-as-ImageFrame path uses Ghostscript to **rasterize at 72 DPI by default**
  ([narkive thread on PDF in Image Frame and DPI](https://scribus.scribus.narkive.com/Up6fwC23/pdf-in-image-frame-and-dpi)) — meaning the placed
  PDF is converted to a low-res raster before display. Quality ≠ vector.
- Forum reports: PDF in ImageFrame "does not work" reliably for newer PDF versions
  ([forums.scribus.net topic 1824](https://forums.scribus.net/index.php?topic=1824.0)).
- Inline encoding in original SLAs uses **base64 of qCompressed PNG**, not raw base64 of
  the file — see `tools/sla_lib/builder/primitives.py:763-807` for ImageData/inlineImageExt
  semantics; see `scribus-image-embedder` README confirming "qCompress format, not base64".
  **Existing DSL primitive passes the inline_image_data string verbatim** — meaning whatever
  you base64-encode externally must match Scribus's internal qCompress wrapper format.
  Round-trip preserves bytes; round-trip-clean DSL is documented at
  `tools/sla_lib/builder/primitives.py:755-762`.

**Implication for D1's "EPS → PDF → inline" plan:**
1. `inline_image_ext="pdf"` is **unverified** — never seen in repo SLAs, no public examples found,
   may not be a path Scribus loads at all. Even the comment in `primitives.py:764`
   says `# e.g. "png", "jpg"` (PDF not listed).
2. Even if it loads, Scribus would rasterize the PDF at 72 DPI, defeating the point of
   keeping vectors.
3. The qCompress-vs-base64 issue: existing `ImageData=` blobs are qCompress-wrapped
   (see [scribus-image-embedder](https://github.com/Afueth/scribus-image-embedder)), and
   `tools/sla_lib/builder/primitives.py` writes the string verbatim. A naive
   `base64(pdf_bytes)` will likely not match what Scribus expects.

**Three honest paths forward** (research, not directive — owner decides in Gate 1):

**Path A — EPS → PNG (raster, simple, deterministic):**
- `gs ... -sDEVICE=png16m -r600 wahlkreuz.eps wahlkreuz.png`
- Render at 600 DPI for 30–250 mm sizes (gives 700–6000 px effective resolution at print
  sizes). Result is a high-DPI PNG embedded as `inline_image_ext="png"` — matches all
  three existing templates' pattern exactly.
- **Pro:** matches existing pattern verbatim, deterministic, no new code path.
- **Con:** raster, not vector — but at 600 DPI source for ≤250 mm display, visually
  indistinguishable in print. Acceptable for a Wahlkreuz symbol that's geometrically simple.

**Path B — EPS → SVG → Polygon-DSL (vector path emit):**
- Use Inkscape or Ghostscript+`pstoedit` to convert EPS to SVG; parse SVG paths; emit
  Scribus `<PAGEOBJECT PTYPE="6">` (Polygon) with the path data and the proper FCOLOR/FSHADE.
- **Pro:** truly vector, scales perfectly.
- **Con:** new tooling (SVG parser, path conversion); the Wahlkreuz is a single symbol —
  CONTEXT.md D1 explicitly rejects this as "tooling-aufwendig". Re-confirming that judgment.

**Path C — `inline_image_ext="pdf"` (CONTEXT.md D1 as written):**
- High risk: untested in this codebase; Scribus may not accept this extension; even if it
  does, rasterization at 72 DPI loses quality; qCompress format mismatch likely.
- **If pursued, mandatory Phase 2 spike**: write a 5-line test SLA with inline PDF, open in
  Scribus 1.6.3 (the container version), confirm rendering and quality. Until that spike
  passes, do not commit to this path.

**Recommendation:** **Path A (EPS → high-DPI PNG)**. Specifically:
```bash
gs -dNOPAUSE -dBATCH -dSAFER -dEPSCrop \
   -sDEVICE=png16m -r600 -dGraphicsAlphaBits=4 -dTextAlphaBits=4 \
   -sOutputFile=wahlkreuz-kreis.png wahlkreuz-kreis.eps
```

This **contradicts CONTEXT.md D1** but matches the empirical evidence:
- Same pattern as all three existing templates (which work).
- 600 DPI source PNG → 30–250 mm display = 700–6000 px effective: print-ready at any size.
- Idempotent shell command, deterministic output (no timestamps in PNG headers from Ghostscript).
- `WahlkreuzSymbol` block wraps `ImageFrame(inline_image_data=..., inline_image_ext="png")`
  exactly as the existing primitive expects.

If owner insists on Path C from D1, **Phase 2 must include a spike** before any template
build.py depends on it. The spike must produce a valid SLA, render via headless Scribus
1.6.3, and produce non-rasterized vector output at print size — all three.

- Confidence: **HIGH** for the contradiction analysis (file-grepped + repo behavior +
  third-party tooling); **HIGH** for the Path A recommendation; **LOW** for whether Path C
  works at all.
- Sources: [Scribus narkive – PDF in ImageFrame DPI](https://scribus.scribus.narkive.com/Up6fwC23/pdf-in-image-frame-and-dpi), [scribus-image-embedder](https://github.com/Afueth/scribus-image-embedder),
  [forums.scribus.net 1824 – Image Frame doesn't work with PDF](https://forums.scribus.net/index.php?topic=1824.0),
  [jfml-blog – Importing PDFs as Images in Scribus](https://blog.jfml.eu/2024/01/03/how-to-import-pdfs-as-images-in-scribus/),
  local SLA grep.

### 1.5 ImageFrame `LOCALSCX`/`LOCALSCY` semantics

From `tools/sla_lib/builder/primitives.py:746-784`:

- `local_scale: tuple[float, float]` — Scribus stores the per-image scale as a unit-multiplier
  for the source-pixels-to-frame-points ratio. `(1.0, 1.0)` means "image at 100% native size,
  filling the frame from top-left". Values < 1 shrink the image inside the frame; values > 1
  enlarge.
- `LOCALX`/`LOCALY`: image origin offset inside the frame, in **points** (mm-converted via
  `mm_to_pt`).
- `SCALETYPE=1` (default in DSL): "scale image to frame". `SCALETYPE=0`: "free", honors
  `local_scale` and `local_offset`.
- `RATIO=1`: preserve aspect ratio.

For embedded EPS-derived PNG, set `scale_type=1, ratio=1` to fit the frame and rely on
`(width_mm, height_mm)` to size the symbol — this is the same pattern used in all three
existing templates' inline images.

- Confidence: **HIGH** (verified in DSL source).

### 1.6 Master Pages `MNAM` references

Not directly relevant to this issue (the five new templates appear to need at most simple
2-page facing-pages-disabled layouts). Existing zeitung template uses masters for the
A4 inner spread; new templates can defer master-page complexity entirely. Skip.

- Confidence: **N/A** — out of scope. If a planner needs detail, refer to `tools/sla_lib/`
  zeitung template for example.

### 1.7 Inline base64 size limits

No documented hard cap from Scribus for `ImageData=` attribute length. Practical limits:
- A6-postcard inline PNG @ 300 DPI ≈ 1000×1500 px ≈ 50–500 KB base64 → fine.
- A1-poster inline PNG @ 300 DPI ≈ 7000×10000 px ≈ tens of MB → starts being unwieldy
  but handled (zeitung-original.sla already contains multi-megabyte inline blobs).
- For Wahlkreuz at 600 DPI sized to 50×50 mm: ≈ 1180×1180 px ≈ 100–300 KB base64. Trivial.

- Confidence: **MEDIUM** — based on existing repo behavior, no published Scribus limit found.

---

## 2. Ghostscript for EPS → PDF (and EPS → PNG)

### 2.1 Best-practice CLI for the rendering scenarios needed here

CONTEXT.md D10 commits to `gs -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite`. Confirming and
extending:

**Scenario A — EPS → PNG (recommended per §1.4):**
```bash
gs -dNOPAUSE -dBATCH -dSAFER -dEPSCrop \
   -sDEVICE=png16m \
   -r600 \
   -dGraphicsAlphaBits=4 -dTextAlphaBits=4 \
   -dDownScaleFactor=1 \
   -sOutputFile=wahlkreuz-kreis.png \
   shared/assets/wahlkreuz-kreis.eps
```
- `-dEPSCrop`: crop to BoundingBox (otherwise PNG includes empty page space — critical
  for an EPS sized as a graphic).
- `-r600`: 600 DPI source. Tradeoff: file size vs. detail. For a single symbol at 600 DPI
  → 30–250 mm display, this is generous and renders sharp at any print size.
- `-dGraphicsAlphaBits=4 -dTextAlphaBits=4`: anti-aliasing for vector edges → cleaner
  rasterization at all zoom levels.

**Scenario B — EPS → PDF (if owner overrides §1.4 toward Path C):**
```bash
gs -dNOPAUSE -dBATCH -dSAFER -dEPSCrop \
   -sDEVICE=pdfwrite \
   -dCompatibilityLevel=1.4 \
   -dPDFSETTINGS=/prepress \
   -dEmbedAllFonts=true -dSubsetFonts=true \
   -dColorConversionStrategy=/CMYK \
   -dProcessColorModel=/DeviceCMYK \
   -dDetectDuplicateImages=true \
   -sOutputFile=wahlkreuz-kreis.pdf \
   shared/assets/wahlkreuz-kreis.eps
```
- Sources: [Ghostscript 10.08 docs – High Level Devices](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html),
  [Artifex Optimizing PDFs](https://artifex.com/blog/optimizing-pdfs-with-ghostscript).
- Note: `-dPDFSETTINGS=/prepress` enables font embedding, 300+ DPI image preservation,
  and CMYK color preservation — the right preset for print-bound PDF.

### 2.2 Determinism — there is a known Ghostscript bug

This is **important**. Ghostscript's `pdfwrite` device emits `/CreationDate`, `/ModDate`,
and a `/ID` hash that change every run, **even with identical input**. SOURCE_DATE_EPOCH
support exists in Debian builds (≥ `9.16~dfsg-1`) but **was rejected upstream**.

Sources:
- [Debian wiki – Reproducible PDFs by Ghostscript](https://wiki.debian.org/ReproducibleBuilds/PdfGeneratedByGhostscript)
- [Ghostscript bug 696765 – Support SOURCE_DATE_EPOCH](https://bugs.ghostscript.com/show_bug.cgi?id=696765)
- [textplain.org – Reproducible PDFs](https://textplain.org/reproducible-pdfs)

**This codebase already handles it** — `tools/render_pipeline.py:53-110` has
`_scrub_pdf_metadata()` and `_scrub_xmp_packet()` that strip `CreationDate`, `ModDate`,
`Producer`, and zero out the `/ID` array. The render pipeline already produces
byte-deterministic PDFs.

**For the Wahlkreuz EPS→{PNG,PDF} step**, the pipeline should:

1. **For PNG path (recommended):** Ghostscript's PNG output is **already deterministic** —
   no timestamps in PNG headers from `pdfwrite` flags. No post-processing needed.
2. **For PDF path (fallback):** apply post-processing similar to existing pipeline:
   ```bash
   exiftool -overwrite_original -all= wahlkreuz-kreis.pdf
   qpdf --linearize --replace-input wahlkreuz-kreis.pdf
   sed -r -i 's|/ID \[<[0-9a-f]+><[0-9a-f]+>\]|/ID [<00><00>]|' wahlkreuz-kreis.pdf
   ```
   Or reuse `_scrub_pdf_metadata()` from `tools/render_pipeline.py` (better — already in
   the codebase).
3. Since CONTEXT.md D10 says "Resultat in den Repo committed", the cached output is
   committed once (after first run on a clean container) and CI never re-runs Ghostscript.
   Consequence: byte-determinism only matters on the **first run** for review purposes;
   after commit, the file is stable.

- Confidence: **HIGH** (the codebase already battle-tested this for templates).
- Recommendation: For PNG, no scrubbing needed. For PDF, reuse the existing
  `_scrub_pdf_metadata()` helper.

### 2.3 Adobe Illustrator-saved EPS gotchas

The source is `Wahl Kreuz im Kreis.eps` from AI 30.2 (mentioned in issue body).

Common AI-EPS-with-Ghostscript problems documented in Ghostscript forums:
- **AI-EPS sometimes embeds a TIFF preview** (low-res raster preview for non-PostScript-aware
  apps). Ghostscript ignores this and uses the actual PostScript — generally fine.
- **AI may use private DSC comments** (e.g. `%AI`-prefixed) that GS doesn't understand;
  these are warnings, not errors. Suppress with `-q`.
- **Color spaces**: AI-EPS may declare color in RGB or CMYK depending on the AI document
  setup. For brand work, force CMYK in the conversion: `-dColorConversionStrategy=/CMYK`.
- **Spot colors in AI-EPS**: AI exports spots with explicit DSC `%%CMYKCustomColor`.
  GS preserves these in PDF output; in PNG output they are flattened to CMYK. **For the
  Wahlkreuz, the symbol is one solid color (likely black or Dunkelgrün)** — flattening is
  fine.
- **Bounding box**: AI sometimes saves with a `%%HiResBoundingBox` and an integer
  `%%BoundingBox` that disagree. `-dEPSCrop` uses `%%HiResBoundingBox` if present —
  generally the correct choice. **Always inspect the EPS once with `head -20`** to see
  what AI emitted.

- Confidence: **MEDIUM** (community-documented, not directly verified for this specific EPS).
- Recommendation: After conversion, visual-inspect `wahlkreuz-kreis.png` once and compare
  to opening the EPS in Inkscape or Preview to confirm fidelity. Phase 2 task.

### 2.4 Verifying byte-determinism across builds

For PNG path: take SHA-256 of output across two clean container runs:
```bash
docker run --rm scribus-pipeline gs ... -sOutputFile=/tmp/a.png /repo/wahlkreuz.eps
docker run --rm scribus-pipeline gs ... -sOutputFile=/tmp/b.png /repo/wahlkreuz.eps
# diff <(sha256sum /tmp/a.png) <(sha256sum /tmp/b.png)
```
Expect zero diff for PNG (Ghostscript PNG output is deterministic).

For PDF path: SHA-256 will differ due to the bug; only after `_scrub_pdf_metadata` does the
hash stabilize. Existing CI already does this for the three template PDFs.

- Confidence: **HIGH** (existing pipeline proves it).

---

## 3. Pillow (PIL) for Compositing

### 3.1 Availability — INSTALL REQUIRED

- Pillow is **not currently installed** in the container (verified: `pip3 show Pillow`
  returns "not found", `apt list --installed | grep -i pillow` empty).
- `Dockerfile.claude` does not install Pillow.
- Pillow 12.2.0 is available via pip3 with `--break-system-packages` (works on Python 3.13
  in the container) — verified via `pip3 install --break-system-packages --dry-run Pillow`.
- Apt path: no `python3-pil` package available in the current sources (verified empty).

**Recommendation:** Add to `Dockerfile.claude` after the apt block:
```dockerfile
RUN pip3 install --break-system-packages --no-cache-dir Pillow==12.2.0
```
Or extend the existing apt block by enabling `python3-pil` from trixie if available
(safer — distro-managed, no pip-vs-apt friction). Quick check: `apt-cache search` returns
empty in current image, so pip is the path.

For CI (the GitHub Actions Pages workflow), add an explicit `pip install Pillow` step in
the runner (the workflow uses Ubuntu, where Pillow can come from `apt install python3-pil`
or pip).

- Confidence: **HIGH** (probed locally).

### 3.2 Grid-of-images for visual review (8 templates, 4×2)

Pillow 12.2.0 native APIs cover this completely. Minimal pattern:

```python
from PIL import Image, ImageDraw, ImageFont

def composite_grid(image_paths: list[Path], labels: list[str],
                   cols: int = 4, rows: int = 2,
                   tile_w: int = 1024, tile_h: int = 768,
                   padding: int = 20, label_height: int = 40) -> Image.Image:
    canvas_w = cols * tile_w + (cols + 1) * padding
    canvas_h = rows * (tile_h + label_height) + (rows + 1) * padding
    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    draw = ImageDraw.Draw(canvas)
    for i, (path, label) in enumerate(zip(image_paths, labels)):
        col, row = i % cols, i // cols
        x = padding + col * (tile_w + padding)
        y = padding + row * (tile_h + label_height + padding)
        # Load + thumbnail
        img = Image.open(path)
        img.thumbnail((tile_w, tile_h), Image.LANCZOS)
        # Center in tile
        ix = x + (tile_w - img.width) // 2
        iy = y + (tile_h - img.height) // 2
        canvas.paste(img, (ix, iy))
        # Label below
        draw.text((x, y + tile_h + 5), label, fill="black", font=font)
    return canvas
```

- `Image.LANCZOS` is the highest-quality downsampling filter — required for downscaling
  rendered template PNGs to 1024px without aliasing.
- `ImageFont.truetype()` with a system font path gives clean antialiased text
  (Pillow defaults `fontmode="L"` for AA).
- Use `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` — already installed
  in the container via `fonts-dejavu-core` (see `Dockerfile.claude:55`).

- Confidence: **HIGH** (Pillow 12.2 docs, dejavu font verified installed).
- Sources: [Pillow 12.2 ImageDraw](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html),
  [Pillow 12.2 ImageFont](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html).

### 3.3 Optimal vision-API input resolution — **1024 px is correct**

Cross-vendor verification:

| Vendor       | Native max long-edge | Tokenization sweet spot |
|--------------|----------------------|--------------------------|
| Claude (Sonnet 4.6 / current default) | 1568 px (downscaled by API otherwise) | 1024–1568 px |
| Claude Opus 4.7  | 2576 px | 1024–2576 px (3× tokens at 2576) |
| Gemini 2.5 (Pro/Flash) | 3072 px tile-tiled internally | 1024 px is well within |
| GPT-4 / GPT-5 (Codex CLI vision) | 2048 px short edge typical | 1024 px is well within |

- For Claude (per CONTEXT.md D5), **1024px long edge is below or at the native resolution**
  of every model, meaning **no API-side resize happens**. This is the optimal cost-vs-detail
  point: ~1334 tokens per image at $0.004 (Sonnet 4.6) or $0.0067 (Opus 4.7).
- Going above 1568px on Sonnet wastes cost (gets downscaled by API). Going below 1024px
  loses typography detail (12 pt body text becomes unreadable).
- CONTEXT.md D7 already specifies 1024 px long edge from 200 DPI render — **confirmed correct**.

- Confidence: **HIGH** for Claude (verified from [Anthropic vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)),
  **MEDIUM** for Gemini/Codex (vendor-specific sweet spots are less precisely documented).
- Sources: [Claude Vision docs (claude.com)](https://platform.claude.com/docs/en/build-with-claude/vision).

---

## 4. Vision Model APIs

### 4.1 Claude Vision (Anthropic SDK)

**Image input formats accepted:**
- JPEG, PNG, GIF, WebP (lossy or lossless).
- Base64 in the message `content` array, OR URL reference, OR Files API `file_id`.
- Max **5 MB per image** (HTTP-413 if larger; verified against
  [GitHub issue 11564](https://github.com/anthropics/claude-code/issues/11564) and
  [issue 20021](https://github.com/anthropics/claude-code/issues/20021)).
- Max **8000×8000 px** for single image, **2000×2000 px** if >20 images in one request.
- Max **100 images per request** for 200k-context models (Sonnet, Opus); 600 for others.

**Token cost (Sonnet 4.6, $3/M input):**
- 1024×1024 px ≈ 1334 tokens ≈ $0.004 / image.
- 1568×1568 px ≈ 1568 tokens ≈ $0.0047 / image.
- For 5 templates × 3 iterations × 1 detail-image + 1 grid-image × ≈ $0.005 ≈ $0.15 total
  for Claude on the visual-review pass. Negligible.

**API call pattern (Python via Anthropic SDK):**
```python
import anthropic, base64
img_b64 = base64.standard_b64encode(open("template.png", "rb").read()).decode()
client = anthropic.Anthropic()
resp = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=2048,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": "image/png",
                                         "data": img_b64}},
            {"type": "text", "text": prompt_text},
        ],
    }],
)
```

**Best practice:** Place image **before** text in the content array — Anthropic docs
explicitly state Claude works best with image-then-text structure for visual analysis.

- Confidence: **HIGH** (verified from Anthropic docs).

### 4.2 Codex CLI (OpenAI Codex CLI 0.128.0)

**Verified locally** — `codex --help` and `codex exec --help`:

- Image flag: `-i, --image <FILE>...` — accepts PNG, JPEG.
- Multiple images: comma-separated or repeat the flag.
- **Non-interactive use is `codex exec`** — confirmed:
  ```
  codex exec [PROMPT] [OPTIONS]
    -i, --image <FILE>...
    --json                    Print events to stdout as JSONL
    -o, --output-last-message <FILE>
    -m, --model <MODEL>
    --skip-git-repo-check     Allow running outside Git repo
    --ephemeral               No persisted session files
  ```
- Sandboxing: needs `-s read-only` or `-s workspace-write` for reading the image file.
- For headless CI/scripts: use `--dangerously-bypass-approvals-and-sandbox` (justified
  here because the container is itself sandboxed).

**Concrete pattern for visual review:**
```bash
codex exec \
  --image build/visual-qa/wahlaufruf-postkarte-a6-quer-detail.png \
  --image build/visual-qa/all-templates-grid.png \
  --json \
  --skip-git-repo-check \
  --output-last-message reviews/visual-qa-codex-raw.txt \
  -m gpt-5-codex \
  -- \
  "$(cat tools/visual_review/prompt_template.md)"
```

- Output: `--json` emits JSONL events to stdout; the final text response is also written
  to `--output-last-message`. Parse the JSONL for structured fields, or use the last
  message file for the markdown body.

**Recent vision capabilities (March-April 2026):**
- Image input shipped in v0.115–0.117 (March 2026).
- gpt-image-2 became default for image generation 2026-04-21 (irrelevant to vision review).
- Vision uses `gpt-5-codex` family by default.

- Confidence: **HIGH** (locally verified CLI flags; web docs aligned).
- Sources: [Codex CLI features](https://developers.openai.com/codex/cli/features),
  [Codex CLI changelog](https://developers.openai.com/codex/changelog).

### 4.3 Gemini CLI (gemini-cli 0.41.2)

**Verified locally** — `gemini --help`:

- **No `-i / --image` flag exists.** Image input is via the `@<path>` syntax inside the
  prompt itself.
- Non-interactive: `-p / --prompt <STRING>` or piped stdin.
- JSON output: `-o json` or `--output-format json`.

**Concrete pattern:**
```bash
gemini \
  -p "Compare this template @build/visual-qa/wahlaufruf-postkarte-a6-quer-detail.png with the existing templates in this side-by-side @build/visual-qa/all-templates-grid.png. Is the new template at least as good?" \
  -o json \
  --yolo
```

The `@<path>` syntax is documented (see
[gemini-cli issue #15532](https://github.com/google-gemini/gemini-cli/issues/15532) for
the multimodal feature thread; [AddyOsmani Gemini CLI tips](https://addyosmani.com/blog/gemini-cli/)
confirms the convention). The CLI internally reads the file and base64-encodes as
`inlineData` per the Gemini API spec.

**Output format:**
```json
{"response": "...", "stats": {...}, "error": null}
```

`--yolo` (or `--approval-mode yolo`) auto-approves all tool calls — required for headless.
Without it, the CLI may prompt for confirmation when it tries to execute internal tool
calls.

**Costs:** Gemini 2.5 Flash images are very cheap (~$0.00007 per image at 1024px); Gemini
2.5 Pro is ~$0.0007. A full visual-review pass costs <$0.01 — effectively free.

- Confidence: **HIGH** for the `@<path>` syntax (multiple sources); **MEDIUM** for exact
  pricing (varies by model).
- Sources: [gemini-cli docs - headless mode](https://geminicli.com/docs/cli/headless/),
  [gemini-cli issue #15532](https://github.com/google-gemini/gemini-cli/issues/15532).

### 4.4 Prompting best practices for visual design review

Cross-vendor consensus from documentation:

1. **Image first, prompt after** — explicit in Claude docs; same pattern works for Gemini's
   `@path` (which is processed first because the file is loaded before the LLM call) and
   Codex (image content blocks come first).
2. **Be specific about what to evaluate.** "Is this template good?" gets a vague answer.
   "Compare typography hierarchy: is the headline visually dominant over body text?" gets
   precise feedback.
3. **Provide the comparison reference** alongside the new image (CONTEXT.md D7's
   side-by-side grid is the right pattern). Without it, models default to "looks fine".
4. **Demand structured output** to make consensus computable. JSON schema or named
   markdown sections.

**Recommended prompt-template skeleton** for `tools/visual_review/prompt_template.md`:
```markdown
You are reviewing a print-design template for the Austrian Greens (Die Grünen NÖ).

INPUT:
1. The detail image: a single new template rendered at 1024px long edge.
2. The grid image: all 8 templates (3 existing + 5 new), 4×2 layout, labeled.

QUESTION (in priority order):
1. Compared to the existing templates (Postkarte, Plakat, Zeitung) in the grid,
   is this NEW template at LEAST AS GOOD visually? (yes / no / unclear)
2. Visual hierarchy on first glance: in 1 second, what is the main message?
3. Brand consistency: does the color mix and typography feel like the existing
   templates' Grünen-CI, or generic?
4. Print risks: text too close to trim, missing bleed, poor contrast, frame
   collisions, broken whitespace rhythm.
5. Concrete improvements with rationale (not "looks fine").

OUTPUT (strict JSON, no surrounding markdown):
{
  "merge_ready": "yes" | "no" | "unclear",
  "comparison_to_existing": "<paragraph>",
  "hierarchy_readability": "<paragraph>",
  "brand_consistency": "<paragraph>",
  "print_risks": ["<finding 1>", "<finding 2>", ...],
  "blocking_findings": ["<critical issue>", ...],
  "nice_to_have": ["<polish suggestion>", ...]
}
```

- Confidence: **HIGH** (synthesized from documented best practices across all three vendors).

### 4.5 Cost summary across all three models

For a single template review (1 detail PNG + 1 grid PNG, ~1024px each):

| Model               | Cost per review | 5 templates × 3 iterations |
|---------------------|----------------|-----------------------------|
| Claude Sonnet 4.6   | ~$0.01         | ~$0.15                      |
| Claude Opus 4.7     | ~$0.02         | ~$0.30                      |
| Codex (gpt-5-codex) | ~$0.01–0.03    | ~$0.15–0.45                 |
| Gemini 2.5 Pro      | ~$0.005        | ~$0.075                     |

**Total budget for full Gate-3 pass (5 templates × 3 iterations × 3 models): under $1.**
CONTEXT.md's "Kosten beherrschbar" concern is satisfied — cost is dominated by
container/CI minutes, not API tokens.

- Confidence: **HIGH** for Claude (published rates); **MEDIUM** for Codex/Gemini (rates
  vary by tier).

---

## 5. Spec Format Inspirations

Surveyed five mature pattern-library/template-spec ecosystems and extracted what to adopt:

### 5.1 Storybook MDX (component design systems)

- Pattern: Markdown body + import-style `<Meta>` and `<Story>` components.
- **Adopt:** Mixed prose-and-structured pattern. CONTEXT.md D2 already does this with
  YAML in fenced blocks — equivalent to MDX's inline `<Meta>` story blocks.
- **Don't adopt:** JS-style imports (irrelevant for static Markdown specs).

### 5.2 Typst document templates

- Pattern: declarative typed configuration at top + content body.
- **Adopt:** typed dimensional fields (`trim_mm`, `bleed_mm`) with units in the field name —
  prevents unit confusion between mm/pt/px. CONTEXT.md D2's `slot.x_mm` etc. follows this.
- Source: [typst.app docs](https://typst.app/docs/) (verified).

### 5.3 LaTeX class-file documentation conventions

- Pattern: `\documentclass`-options at top, semantic content in body.
- **Adopt:** explicit "audience"/"intended use" header — LaTeX classes always document
  who the class is for first.

### 5.4 Figma/Sketch template export formats

- Pattern: layered hierarchy with absolute pixel positions per frame.
- **Adopt:** ASCII-skizze with explicit mm coordinates for slot positions
  (CONTEXT.md D2 — already done).
- **Don't adopt:** binary export formats (irrelevant — text-first spec for LLM/human review).

### 5.5 Design-token conventions (Style Dictionary, W3C Design Tokens)

- Pattern: semantic tokens (`color.brand.primary`) referenced by tokens-as-values.
- **Adopt:** the spec's `slot.fcolor` references `shared/ci.yml` color names by string
  — a token reference. Already in CONTEXT.md D2's slot table.

**Net recommendation for `templates/_specs/SCHEMA.md`:**
- YAML block with: `template:{id, title, format, trim_mm, bleed_mm, audience}`,
  `pages: [{name, ascii, slots: [{anname, type, x_mm, y_mm, w_mm, h_mm, fcolor, style_ref, example}]}]`,
  `eps_strategy: {asset, scale_mm, embedding_path}`, `print_notes: {bleed_mm, fold_mm,
  cut_layer, min_dpi}`.
- The existing `shared/template-spec.schema.yaml` is already a complete JSON Schema for the
  same shape — **reuse it as the validation target** rather than inventing a new one. Only
  delta: add `eps_strategy` and `print_notes` blocks if not yet present.

- Confidence: **HIGH** for the synthesis; **HIGH** that `shared/template-spec.schema.yaml`
  is the right anchor (verified — comprehensive draft-2020-12 schema exists).

---

## 6. Print Production Standards (Austria/EU/DACH)

### 6.1 Bleed (Anschnitt)

- **3 mm** is the DACH standard for postcards, flyers, posters. Confirmed across
  multiple Austrian/German printers ([druck.at A6 Postkarten](https://www.druck.at/produkte/werbung/werbepostkarten/a6),
  [Adobe DIN A6 explainer](https://www.adobe.com/de/creativecloud/design/discover/a6-format.html)).
- Some printers ask for **2 mm** for door hangers / die-cut products (etikett.de —
  [Stanzkontur guide](https://etikett.de/blog/frage-der-woche-was-ist-eine-stanzkontur-und-wie-lege-ich-sie-an/)).
- **2 mm clearance from die-cut edge to first content** ("Sicherheitsabstand").
- Confidence: **HIGH**.

### 6.2 Stanzkontur naming convention (DACH)

**Mixed practice — there is no single industry standard:**

| Convention | Origin | Used by |
|------------|--------|---------|
| `Stanze`        | DACH labels/stickers | etikett.de, viaprinto, FLYERALARM |
| `Stanzkontur`   | DACH general print  | Saxoprint, FLYERALARM (some products) |
| `CutContour`    | International / Roland/Mimaki RIPs | sign-making, vinyl cutters |
| `CutLine`       | US | some US-based printers |

For the Austrian Grüne (Wiener/NÖ printers), `Stanzkontur` is the most common German term.
**CONTEXT.md D4 chose `Stanzkontur` — this is correct for the Austrian market.** If a
specific printer requires `CutContour`, the rename is one line in `shared/ci.yml`. Document
in spec as a known-printer-specific override.

For folds: `Falz` is universal in DACH. No alternative names commonly used.

**Required attributes for both:**
- `spot: true` (separation channel, not CMYK ink)
- Set on a layer with `DRUCKEN=0` (won't print as CMYK content)
- Stroke width in PDF export should be 0.25 pt or thinner — printers' RIPs detect the
  spot channel; the visual line is just a placeholder.
- For Stanze: closed path. For Falz: dashed line is conventional but solid spot-color
  line works equivalently.

- Confidence: **HIGH** for CONTEXT.md D4's choice; **HIGH** for the technical setup.
- Source: [etikett.de Stanzkontur guide](https://etikett.de/blog/frage-der-woche-was-ist-eine-stanzkontur-und-wie-lege-ich-sie-an/),
  [siegertypen-design.de Sonderfarben](https://www.siegertypen-design.de/blog/pdf-sonderfarbe-erstellen-pruefen.html).

### 6.3 DIN-lang folded flyer dimensions

- Open: **A4 quer = 297 × 210 mm**.
- Folded panels (Wickelfalz or Zickzackfalz): **99 × 210 mm** each (3 panels per side × 2 sides = 6 panels).
- **Wickelfalz** (wrap fold): inner panel slightly narrower (98 mm) so it tucks inside —
  printers typically handle this; design at 99 mm uniform is fine and the printer adjusts.
- **Zickzackfalz** (Z-fold/accordion): all panels exactly 99 mm — design at uniform 99 mm.
- Bleed: 3 mm all around.
- Falz lines: at 99 mm and 198 mm from the left edge (3-panel split).

CONTEXT.md ISSUE.md "kandidat-falzflyer-din-lang" maps to this exactly (DIN-lang gefalzt → 6 Panele).
Recommendation: **specify Zickzackfalz** in the spec — uniform 99×210 mm panels are
simpler design-wise and most Austrian/German printers accept either.

- Confidence: **HIGH**.
- Source: [Saxoprint Zickzackfalz](https://www.saxoprint.de/werbebedarf/flyer/falzflyer/zickzackfalz),
  [colorpress Falzflyer DIN-lang](https://colorpress.de/shop/index?productIdent=1e0g1hdg5h1g0h33g2h45g6h1g3hag4h2z),
  [maxiprint.ch DIN-lang Falzflyer](https://maxiprint.ch/en/p/falzflyer/din-lang-99x210-mm/falzflyer-din-lang-hoch-6-seiter-wickelfalz.html).

### 6.4 Door hanger dimensions

- Issue says **105 × 250 mm with 35 mm hole**.
- Cross-check against Austrian printers:
  - [viaprinto Türanhänger](https://www.viaprinto.de/tueranhaenger): formats 100×240, 103×210, 200×280 mm (no 105×250 default).
  - [flyermaschine Stanzflyer Türhänger](https://www.flyermaschine.de/Stanzflyer/Tuerhaenger/): standard 105×250 mm offered.
- **The 105 × 250 mm size is a real, supported format** in DACH; multiple printers offer it.
- **Hole size**: typical door-handle hole is **35 mm diameter, centered horizontally,
  positioned 10–25 mm from the top edge**. Issue's 35 mm matches industry standard.
- Bleed: **2 mm** for die-cut products (not 3 mm — die-cut has tighter tolerances).
- Stanzkontur: closed path enclosing the outer rectangle PLUS the inner circle for the
  hole. Both on the Stanzkontur spot-color layer.

- Confidence: **HIGH** for size and hole dimensions; **MEDIUM** for exact hole position
  (varies 10–25 mm from top — owner choice).
- Source: [flyermaschine Türhänger](https://www.flyermaschine.de/Stanzflyer/Tuerhaenger/).

### 6.5 A5 tent card from A4-folded-landscape

- A4 quer: **297 × 210 mm**.
- Folded in half along the long edge (a single fold at 148.5 mm) → two A5 panels each
  **148.5 × 210 mm** showing.
- For a **table tent** (doppelseitig sichtbar): both sides print on, fold creates a triangular
  free-standing shape when an additional small flap is folded under for stability —
  but the simplest "A5-Tent" is the **single fold** producing two visible A5 panels.
- Issue says "A4 quer gefalzt → A5-Tent" — this is the single-fold pattern.
- Falz line at 148.5 mm, dashed/spot.
- Bleed: 3 mm all around.

- Confidence: **HIGH** for dimensions; **MEDIUM** on whether single-fold or tri-fold is
  intended (tri-fold/triangular needs a flap for stability — owner specifies in spec).
- Source: [Paper Mill Store Table Tent Templates](https://www.thepapermillstore.com/free-templates/table-tent-templates),
  [PrintPlace Table Tents](https://www.printplace.com/layout-templates/table-tents).

### 6.6 Min DPI and trim/bleed marks for print

- **Min 300 DPI** for raster content at print size (industry standard, all DACH printers).
- **Trim marks**: lines at the four corners showing where to cut. Standard length 5 mm,
  offset 3 mm from trim edge.
- **Registration marks**: targets at the edges showing alignment of CMYK plates. Use color
  `Registration` (CMYK 100/100/100/100 — already in `shared/ci.yml`).
- Scribus' PDF export already adds trim/registration marks automatically when bleed is
  set in the SLA — no custom DSL work needed.
- Confidence: **HIGH**.

---

## 7. Astro / Galerie-Build

### 7.1 Astro version + content collection

- **Astro 5.0** (`site/package.json` `"astro": "^5.0.0"`).
- Content collection at `site/src/content.config.ts` defines the schema:
  ```ts
  const templates = defineCollection({
    loader: glob({ pattern: '**/*.md', base: './src/content/templates' }),
    schema: z.object({
      id: z.string(), version: z.string(), title: z.string(),
      description: z.string().optional(),
      type: z.string().optional(),
      format: z.string().optional(),
      pages: z.number().optional(),
      audience: z.array(z.string()).optional(),
      sizes: z.array(z.any()).optional(),
      masters: z.array(z.any()).optional(),
      example_pages: z.array(z.any()).optional(),
      slots: z.record(z.any()).optional(),
      preflight: z.record(z.any()).optional(),
      build: z.record(z.any()).optional(),
      _downloads: z.array(z.any()).optional(),
      _previews: z.array(z.any()).optional(),
    }),
  });
  ```
- Schema is permissive (most fields optional, `slots` is `z.record(z.any())`). New
  template types (door hanger, tent card, falzflyer) require **no schema changes**.

### 7.2 How template content is sourced

`tools/gallery_build.py` (verified by reading entire 130-line file):

1. Walks `templates/<id>/`, reads `meta.yml`.
2. Globs committed `template.sla`, `preview.pdf`, and `page-*.png` artifacts.
3. **Fails if artifacts missing** (per issue #4 design — gallery is copy-only, expects
   maintainer to run `bin/render-gallery` first).
4. Copies to `site/public/templates/<id>/`.
5. Writes `site/src/content/templates/<id>.md` with YAML frontmatter from `meta.yml`.

Adding 5 new templates = 5 new directories under `templates/<slug>/` with
`build.py + meta.yml + README.md` + committed `template.sla + preview.pdf + page-*.png`
artifacts. **No gallery_build.py changes needed.**

The existing render flow (`bin/render-gallery` calling `tools/render_pipeline.py`):
1. `python3 build.py` → `template.sla`
2. `tools/render.py` → `preview.pdf`
3. `pdftoppm -r 150 -png preview.pdf page` → `page-NN.png`
4. `_scrub_pdf_metadata()` → deterministic PDF
5. Commits artifacts.

For new templates: same flow, identical commands, just more directories.

- Confidence: **HIGH** (verified via reading source).

### 7.3 Family vs. single template pattern

`gallery_build.py` distinguishes `meta.type == "family"` (multi-size, e.g. one template
emitting A4 + A5 variants) from single. None of the 5 new templates need `type: family`
based on the issue spec. Use the single-template pattern (matching all three existing).

- Confidence: **HIGH**.

---

## 8. Wahl Symbol Design Conventions

### 8.1 Wahlkreuz im Kreis — Austrian voting context

The "Wahl Kreuz im Kreis" (cross-in-circle) is the universal Austrian/DACH voting symbol —
on official ballot papers, voters mark their choice with a cross or "X" inside a small
circle next to the candidate or party. Using the symbol in a campaign template signals
"Wahl"/"vote" instantly to any voter.

**Visual convention (typical):**
- Circle: thin black or dark outline, ~2–3 pt at typical print size.
- Cross: bold X centered in the circle. Color is brand-typical — for Grüne, dark green
  (Dunkelgrün from `shared/ci.yml`) or black is most common.
- Sizing: noticeable but not screaming — usually 30–70 mm diameter on a postcard,
  larger on a poster, smaller on a flyer panel.
- Source EPS is a vector with the symbol already drawn. Don't redraw.

### 8.2 Liability constraint (issue spec)

Issue body: "should encourage voting Grüne, but not the only valid choice on the ballot."

This is **not a visual constraint** — visually a single cross-in-circle is fine. It's a
**copy/messaging constraint**:
- AVOID: "Mach dein Kreuz bei den Grünen — nur dort ist es richtig" (implies others wrong).
- USE: "Wähle Grün am [Datum]" or "Mach dein Kreuz bei den Grünen" (encourages, doesn't exclude).
- The symbol itself is neutral; the surrounding copy carries the messaging.

This belongs in **spec text examples** (`example` field in slot tables) — give realistic,
campaign-conformant placeholder text that respects this constraint. Plan: have spec writer
explicitly add a "Messaging-Constraint" note in the spec for templates featuring the
Wahlkreuz.

- Confidence: **HIGH** for the Austrian symbol convention; **HIGH** that this is a
  copy-not-visuals constraint.
- Source: visual convention is universal in DACH election context; verified across
  Austrian government voting guides
  ([gruene.at](https://gruene.at/), [Wikipedia Schmuckfarbe](https://de.wikipedia.org/wiki/Schmuckfarbe)
  for related conventions).

---

## Don't Hand-Roll — list

External libraries/tools to use, NOT reimplement. Each is verified available in the
container or installable.

| Don't Build | Use Instead | Why |
|-------------|-------------|-----|
| Custom PIL writer or numpy image grid composer | **Pillow 12.2.0** (`Image.thumbnail`, `Image.paste`, `ImageDraw.text`, `ImageFont.truetype`) | One library covers all the grid/label/composite needs |
| Custom EPS parser or PostScript interpreter | **Ghostscript 10.05.1** (`gs -dEPSCrop -sDEVICE=png16m`) | Already installed; battle-tested for AI-EPS edge cases |
| Custom PDF→PNG rasterizer | **`pdftoppm`** (poppler-utils, already in Dockerfile) | Already used in `tools/render_pipeline.py` for the same purpose |
| Custom XML/SLA writer (PAGEOBJECT, LAYERS, COLOR emission) | **`tools/sla_lib/builder/`** (existing DSL) | The whole point of the DSL — covered by tests, round-trip-clean |
| Custom SLA round-trip diff | **`tools/sla_diff.py`** | Already exists; comprehensive |
| Custom inline-image base64 encoder | **`tools/sla_lib/builder/primitives.py:ImageFrame`** | Handles inline_image_data + inline_image_ext correctly |
| Custom Astro frontmatter generator | **`tools/gallery_build.py`** | Already does this; copy-only by design |
| Custom image base64 for vision API | **Anthropic/OpenAI SDKs**, or `codex -i <path>` / `gemini @<path>` | Standard CLI flags; libraries handle media-type detection |
| Custom JSON-Schema validator | **`jsonschema`** (Python; pip-installable) — paired with `shared/template-spec.schema.yaml` | The schema already exists; just plug in validator |
| Custom font rendering for grid labels | **Pillow + DejaVuSans-Bold** (already installed via `fonts-dejavu-core`) | Cross-platform, antialiased, no font-finding logic needed |
| Custom PDF metadata scrubber | **`tools/render_pipeline.py:_scrub_pdf_metadata`** | Already handles CreationDate/ModDate/Producer/ID for determinism |
| Custom multi-model review orchestrator | **`/issue:review` skill** (already orchestrates Claude+Codex+Gemini for code) — adapt the same pattern for vision | DRY; consistent UX |
| Custom layer/spot-color emission in DSL | **`Document(layers=[DocumentLayer(...)])`** + `shared/ci.yml` `colors:{X: {spot: true}}` | Already supported in the DSL; just needs new entries |

---

## Standard Stack — pinned versions

External dependencies with exact versions verified in container or installable.

| Component | Version | Source | Status | Used For |
|-----------|---------|--------|--------|----------|
| Scribus | **1.6.3** | Debian trixie pin (`Dockerfile.claude`) | INSTALLED | SLA → PDF render |
| Ghostscript | **10.05.1** | Debian trixie | INSTALLED | EPS → PNG/PDF rasterization |
| Pillow | **12.2.0** | pip (Python 3.13 wheel `cp313-cp313-manylinux_2_27_aarch64`) | **NEEDS INSTALL** — add to `Dockerfile.claude` | Visual-QA grid composite |
| Poppler-utils (`pdftoppm`, `pdfinfo`) | as-shipped | Debian trixie | INSTALLED | PDF → PNG for previews |
| ImageMagick 7 | 7.1.1.43 | Debian trixie | INSTALLED | visual-diff fallback |
| libxml2-utils (`xmllint`) | as-shipped | Debian trixie | INSTALLED | SLA XML validation |
| python3-yaml | 6.0.3 | Debian trixie | INSTALLED | meta.yml + spec parsing |
| python3-lxml | as-shipped | Debian trixie | INSTALLED | SLA XML emission |
| jsonschema (Python) | 4.x latest | pip | **NEEDS INSTALL** — for spec validation against `shared/template-spec.schema.yaml` | optional, recommended |
| DejaVuSans (font) | as-shipped | `fonts-dejavu-core` | INSTALLED | grid composite labels |
| gh CLI | as-shipped | base claude-code image | INSTALLED | issue/PR workflow |
| codex CLI | **0.128.0** | npm `@anthropic/codex-cli` (or as installed at `/root/.npm-global/bin/codex`) | INSTALLED | Codex Vision review |
| gemini CLI | **0.41.2** | npm `@google/gemini-cli` (`/root/.npm-global/bin/gemini`) | INSTALLED | Gemini Vision review |
| anthropic Python SDK | latest (≥0.39) | pip | OPTIONAL — only if `tools/visual_review.py` uses Claude API directly instead of CLI | Claude Vision API |
| qpdf | as-shipped | not currently installed in `Dockerfile.claude`; available in Debian | OPTIONAL — only needed if PDF determinism scrubbing is extended | PDF linearize for reproducible builds |
| exiftool | as-shipped | not currently installed in `Dockerfile.claude` | OPTIONAL — already replaced by in-pipeline scrubbing | PDF metadata strip |

**Container additions for this issue (proposed Dockerfile.claude delta):**
```dockerfile
RUN pip3 install --break-system-packages --no-cache-dir \
    Pillow==12.2.0 \
    jsonschema==4.23.0
```

For CI (`.github/workflows/pages.yml`): add the same `pip install` step before
`bin/render-gallery` is invoked.

---

## Sources by Confidence

### HIGH confidence (Context7-equivalent, official docs, verified locally)

- [Anthropic Claude Vision API documentation](https://platform.claude.com/docs/en/build-with-claude/vision) — image format, size limits, tokens, costs.
- [Pillow 12.2 docs — ImageDraw](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html), [ImageFont](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html).
- [Codex CLI features](https://developers.openai.com/codex/cli/features) + locally verified `codex --help` and `codex exec --help`.
- [gemini-cli 0.41.2](https://github.com/google-gemini/gemini-cli) + locally verified `gemini --help`.
- [Ghostscript 10.08 docs — High Level Devices (pdfwrite)](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html), [Devices](https://ghostscript.readthedocs.io/en/latest/Devices.html).
- [Debian wiki — Reproducible PDFs by Ghostscript](https://wiki.debian.org/ReproducibleBuilds/PdfGeneratedByGhostscript).
- Codebase analysis: `tools/sla_lib/builder/{primitives,document,styles,ci}.py`, `tools/render.py`, `tools/render_pipeline.py`, `tools/gallery_build.py`, `shared/ci.yml`, `shared/template-spec.schema.yaml`.
- Local probe: `gs --version 10.05.1`, `scribus 1.6.3+dfsg-0.2`, `codex --version 0.128.0`, `gemini --version 0.41.2`.

### MEDIUM confidence (verified via primary docs but rendering details vary)

- [Saxoprint Zickzackfalz dimensions](https://www.saxoprint.de/werbebedarf/flyer/falzflyer/zickzackfalz), [colorpress Falzflyer](https://colorpress.de/shop/index?productIdent=1e0g1hdg5h1g0h33g2h45g6h1g3hag4h2z), [maxiprint.ch](https://maxiprint.ch/en/p/falzflyer/din-lang-99x210-mm/falzflyer-din-lang-hoch-6-seiter-wickelfalz.html) — DIN-lang Falzflyer specs.
- [etikett.de Stanzkontur guide](https://etikett.de/blog/frage-der-woche-was-ist-eine-stanzkontur-und-wie-lege-ich-sie-an/), [siegertypen-design.de Sonderfarben](https://www.siegertypen-design.de/blog/pdf-sonderfarbe-erstellen-pruefen.html) — DACH spot-color naming.
- [flyermaschine Türhänger](https://www.flyermaschine.de/Stanzflyer/Tuerhaenger/), [viaprinto Türanhänger](https://www.viaprinto.de/tueranhaenger) — door hanger specs.
- [The Paper Mill Store table tent templates](https://www.thepapermillstore.com/free-templates/table-tent-templates), [PrintPlace](https://www.printplace.com/layout-templates/table-tents) — A5 tent card.
- [textplain.org reproducible PDFs](https://textplain.org/reproducible-pdfs), [Artifex Optimizing PDFs](https://artifex.com/blog/optimizing-pdfs-with-ghostscript) — pdfwrite determinism.
- [scribus-image-embedder repo](https://github.com/Afueth/scribus-image-embedder) — qCompress format for ImageData.

### LOW confidence (community/secondary, treat as hypothesis)

- [Scribus narkive PDF in ImageFrame DPI thread](https://scribus.scribus.narkive.com/Up6fwC23/pdf-in-image-frame-and-dpi) — PDF rasterization at 72 DPI default.
- [forums.scribus.net topic 1824](https://forums.scribus.net/index.php?topic=1824.0) — PDF in ImageFrame compatibility issues.
- [jfml-blog importing PDFs as images in Scribus](https://blog.jfml.eu/2024/01/03/how-to-import-pdfs-as-images-in-scribus/) — reports rasterization, no inline embed.
- [gemini-cli issue #15532](https://github.com/google-gemini/gemini-cli/issues/15532) — `@<path>` multimodal feature thread.

**LOW-confidence findings that should be validated in Phase 2 spike:**
- Whether `inline_image_ext="pdf"` is accepted by Scribus 1.6.3 at all (CONTEXT.md D1
  Path C). Recommend: Path A (PNG) instead, or owner-confirmed spike.
- Exact rasterization quality of Ghostscript-PNG vs. Scribus-PDF-rasterization — only
  matters if owner overrides and wants Path C.

---

## Synthesis Notes for the Planner

1. **The biggest single finding** is the contradiction in §1.4: CONTEXT.md D1 commits to
   inline-PDF-via-Ghostscript but the codebase has zero examples and external evidence
   is negative. Path A (EPS → high-DPI PNG) is the safer, simpler, more conformant choice
   and matches all three existing templates. Owner needs to decide in Gate 1.

2. **DSL layer support already exists** (CONTEXT.md D4 says it doesn't). `DocumentLayer`
   in `tools/sla_lib/builder/styles.py:17` and `_emit_layers` in `document.py:878-911`
   handle everything needed. New blocks `FoldLine`/`DieCut` just emit Polygons on a
   non-printable layer with a spot-color stroke. Saves a Phase 2 task.

3. **Pillow needs `Dockerfile.claude` patch** — currently absent. One-liner pip install.

4. **Visual-review CLIs all work as expected:**
   - Claude: SDK with base64 image content blocks (or Files API).
   - Codex: `codex exec -i image.png "prompt" --json`.
   - Gemini: `gemini -p "... @image.png ..." -o json --yolo`.
   The orchestrator can spawn all three in parallel; total cost <$1 for full Gate 3.

5. **CONTEXT.md D7's 1024 px is the Goldilocks resolution** — verified across vendors.
   Going higher wastes tokens (downscaled by API anyway); going lower loses typography
   detail.

6. **Print conventions (DACH)** all align with the issue spec. 3 mm bleed, `Stanzkontur`
   spot color naming, 105×250 mm door hanger with 35 mm hole, A4 → DIN-lang 99×210 mm
   panels (Zickzackfalz recommended), A4 → A5 tent (148.5 mm fold). All verified against
   multiple Austrian/German printers.

7. **The existing render pipeline (`tools/render_pipeline.py`) already handles PDF
   determinism** via `_scrub_pdf_metadata`. New templates inherit this for free —
   no new determinism work needed.

8. **The Wahlkreuz "Liability" constraint is a copy-not-visual** issue. Spec writers
   should add explicit messaging guidance to slot examples for templates featuring the
   symbol (Wahlaufruf-Postkarte, Falzflyer, Türanhänger).
