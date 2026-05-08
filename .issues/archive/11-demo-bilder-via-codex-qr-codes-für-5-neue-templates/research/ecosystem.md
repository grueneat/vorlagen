# Ecosystem Research — Issue #11 (Demo-Bilder + QR-Codes)

**Date:** 2026-05-08
**Scope:** Section 1–8 from the dispatch prompt. All findings verified against PyPI / official docs / live probes / installed binaries where possible.

---

## TL;DR (read first)

1. **`qrcode==8.2`** (PyPI latest, released 2025-05-01) — `pip install "qrcode[pil]"` pulls in `Pillow >= 9.1.0`. Determinism **verified empirically** (byte-identical PNG output across runs). Native `StyledPilImage` + `SolidFillColorMask` + `embedded_image_path=` covers every CONTEXT.md D1 requirement. **HIGH confidence.**
2. **CONTEXT.md D2 says "DALL·E-3" — the model codex actually invokes is `gpt-image-2`.** No `--image-out` / `--image-dir` flag exists in `codex 0.128.0`. Image generation is delivered via the agent's `image_gen` tool when prompted in natural language; the existing `tools/codex_image_gen.py` already takes this approach. The `image_generation` feature flag is **stable + on by default** in the installed CLI (verified via `codex features list`). **HIGH confidence.**
3. **Live URL probe of D3 candidates:** 4 of 5 OK; **`/themen/klimaschutz/` returns HTTP 404**, must fallback to `/themen/`. **`/termine/` 301-redirects** to a localised landing page (`/news/termine-in-und-um-pillichsdorf/`) — the *redirect target* is what gets encoded after fit, not the input. (Decide: encode the short canonical URL `/termine/` and accept the redirect, or hard-code the long target.) **HIGH confidence.**
4. **Pillow 12.2** + Gotham Narrow + DejaVu Sans are all **present in the Dockerfile.claude image** — no font install needed for the Symbolfoto caption.
5. **`pyzbar==0.1.9`** (last released 2022) is the standard Python QR-decoder for tests. Needs system `libzbar0` (not pre-installed in the base image; `apt-get install -y libzbar0 zbar-tools` works on Debian trixie). Tested decode of branded green QR + embedded logo for all 4 live URLs → **scannable, 100% pass.** Alternative `qreader==3.16` exists but pulls heavier deps (OpenCV); pyzbar is simpler.
6. **JPEG ~80% beats PNG by ~6× on photo content** (785 KB vs 4.5 MB for a 1024×1536 noisy image). Inline-base64 embed via `pack_inline_image(..., "jpg")` already supported by `tools/sla_lib/builder/primitives.py:787` (`inline_image_ext: "jpg"`).

---

## 1. `qrcode` Python library

### Version & install — HIGH

- **Latest:** `qrcode==8.2` (2025-05-01). Source: [PyPI](https://pypi.org/project/qrcode/), [GitHub releases](https://github.com/lincolnloop/python-qrcode/releases).
- **Python:** `>=3.9, <4.0`. Project image runs Python **3.13.5** — compatible.
- **Install:** `pip install "qrcode[pil]"` → pulls `Pillow >= 9.1.0`. Project already has `Pillow==12.2.0` system-installed.
- 8.2 release notes (qrcode/CHANGES.rst): perf improvement to `QRColorMask.apply_mask`, typo-fix to StyledPilImage constructor params with backward-compatible aliases. Nothing breaking from 8.0.
- **`__version__` attribute:** does NOT exist at module level (verified — `import qrcode; qrcode.__version__` raises `AttributeError`). Use `importlib.metadata.version("qrcode")` if version-pinning at runtime is needed.

### API for D1 requirements — HIGH (empirically validated)

```python
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask

qr = qrcode.QRCode(
    version=None,                                          # auto-fit
    error_correction=qrcode.constants.ERROR_CORRECT_H,     # ~30% recovery, required for logo embed
    box_size=10,                                           # px per module (tunable)
    border=4,                                              # quiet zone in modules (>=4 is QR-spec minimum)
)
qr.add_data("https://noe.gruene.at/")
qr.make(fit=True)                                          # fit=True picks the smallest version that fits
img = qr.make_image(
    image_factory=StyledPilImage,
    color_mask=SolidFillColorMask(
        front_color=(28, 72, 33),                          # Dunkelgrün ~RGB approximation; CMYK conversion happens at PDF export
        back_color=(255, 255, 255),
    ),
    embedded_image_path="shared/logos/sonnenblume.png",    # logo at center, masked by qrcode lib
)
img.save("output.png", format="PNG", optimize=True)
```

**Key API surface:**
- `qrcode.constants.ERROR_CORRECT_H` — error level H, 30% redundancy. (Other levels: L=7%, M=15%, Q=25%.)
- `box_size` — **integer pixels per module**.
- `border` — **integer modules** for quiet zone (default 4 = QR spec minimum).
- `qr.modules_count` — total modules per side after `qr.make()` (e.g. 33 for v=4).
- `qr.version` — chosen QR version (1–40) after `fit=True`.
- Total pixel size = `(modules_count + 2*border) * box_size`.
- `StyledPilImage` accepts: `module_drawer=` (shape — `SquareModuleDrawer` default, `RoundedModuleDrawer`, `GappedSquareModuleDrawer`, `CircleModuleDrawer`), `color_mask=`, `embedded_image_path=`.
- `SolidFillColorMask(front_color, back_color)` accepts 3-tuple or 4-tuple (RGB or RGBA). Note: `back_color=(0,0,0)` is buggy in 8.x (entire QR turns black — [Issue #246](https://github.com/lincolnloop/python-qrcode/issues/246)). Use white `(255,255,255)` for back.
- The plain `qr.make_image(fill_color=, back_color=)` (no `image_factory=`) supports color tuples too but cannot embed a logo. Use StyledPilImage for our case.

### Determinism — HIGH (verified empirically)

Empirical test (this environment, qrcode 8.2 + Pillow 12.2):

| Variant | Run 1 SHA-256 (first 16) | Run 2 SHA-256 (first 16) | PNG bytes | Identical? |
|---------|--------------------------|--------------------------|-----------|------------|
| Plain B/W (`fill_color="black"`) | `2160678e78c4b642` | `2160678e78c4b642` | 693 | YES |
| Styled + green color mask | `28853211be9f08e3` | `28853211be9f08e3` | 1878 | YES |

PNG chunk inspection of the styled output:
```
[('IHDR', 13), ('IDAT', 1821), ('IEND', 0)]
```
**No `tIME`, no `pHYs`, no `tEXt`** — Pillow 12.2's default PNG encoder is bit-stable. Save with `optimize=True` for smaller files; the bit-stability still holds.

**Cross-machine determinism warning:** identical bytes are guaranteed only when `(qrcode_version, Pillow_version, pillow_zlib_link)` match. Lock all three in `requirements-dev.txt` (`qrcode==8.2`, `Pillow==12.2.0`). If the Pillow version drifts on CI vs local, byte hashes may differ even though the QR scans correctly. **Mitigation for D9:** test the SHA in the same image where the build runs (CI, not locally); or pin `Pillow==12.2.0` in `requirements-dev.txt` AND in the Dockerfile.claude pip install layer.

### Logo-embed mechanics — HIGH (validated end-to-end)

`embedded_image_path=` opens the file via Pillow, scales it, masks it onto the QR center. Default behaviour: covers the central modules; ECC=H allows ~30% obscured = safe up to roughly 25% of total area. Tested with all 4 URLs at v=3, v=4, v=6 — all decoded cleanly via `pyzbar` even with a 200×200 px circle covering the center.

**For our circular Sonnenblume mask:** pre-render the logo as a square PNG with **transparent corners** (alpha=0 outside the circle, alpha=255 inside). qrcode lib will paste it as-is — no extra masking step required. If the source logo is square+opaque, do this Pillow pre-step before passing the path:

```python
from PIL import Image, ImageDraw
src = Image.open("logo_square.png").convert("RGBA")
mask = Image.new("L", src.size, 0)
ImageDraw.Draw(mask).ellipse((0, 0, *src.size), fill=255)
src.putalpha(mask)
src.save("logo_circle.png")  # then pass embedded_image_path="logo_circle.png"
```

**Note (CONTEXT.md discretion item):** `qrcode` lib also accepts a positional `embedded_image=` parameter taking a Pillow `Image` instance directly (no temp file). Cleaner for `qr_gen.py`.

### Module-size math — HIGH

Print target from D1: each module ≥ 0.5 mm at final print size.
At 300 DPI: 1 mm = 11.81 px → **0.5 mm = 5.9 px ≈ 6 px per module**.

For our actual encoded URLs (run on this environment):

| URL | qrcode version (auto) | Modules/side | Pixels @ box_size=10 (incl. border=4) | mm @ 300 DPI |
|-----|----------------------|--------------|----------------------------------------|---------------|
| `noe.gruene.at/` | 3 | 29 | 370 | 31.3 mm |
| `noe.gruene.at/themen/` | 4 | 33 | 410 | 34.7 mm |
| `noe.gruene.at/mitmachen/` | 4 | 33 | 410 | 34.7 mm |
| `noe.gruene.at/news/termine-in-und-um-pillichsdorf/` (redirect target of `/termine/`) | 6 | 41 | 490 | 41.5 mm |

Spec slot sizes: postkarte ~25 mm; falzflyer-Closer ~30 mm; tent-card 14×14 mm in spec (likely needs revisit). Recommendation: use **`box_size=10`** for source PNG (high resolution → Scribus rescales without artifacts). Per-template QR dimensions:

- Postkarte (~25 mm): v3 URL gives 29 modules × 0.86 mm/mod → marginal at 0.5 mm threshold for v6 URL. **Use shorter URLs on postkarte (`https://noe.gruene.at/`)**, longer on falzflyer (35 mm slot).
- Falzflyer Closer (35×35 mm): v6 URL → 41 modules × 0.85 mm/mod → fine.
- Tent-card 14×14 mm: **TOO SMALL** for `/news/termine-…/` (41 mods → 0.34 mm/mod, below 0.5 mm minimum). Choose a short URL for tent-card (e.g. `https://noe.gruene.at/mitmachen/` at v4 → 33 mods → 0.42 mm/mod). Spec may need to grow this slot to ≥17 mm; flag for planner.

---

## 2. Codex DALL·E / `gpt-image-2` image generation

### Critical correction to CONTEXT.md D2 — HIGH

**CONTEXT.md says:** "DALL·E-3 Modell, hohe Qualität."
**Reality:** the codex CLI's built-in image generation skill uses **`gpt-image-2`** (state-of-the-art OpenAI image model, GA snapshot `gpt-image-2-2026-04-21`). DALL·E-3 is no longer the codex default.
- Sources: [OpenAI gpt-image-2 model page](https://developers.openai.com/api/docs/models/gpt-image-2), [codex CLI features doc](https://developers.openai.com/codex/cli/features), [Codex Blog 2026-04-27](https://codex.danielvaughan.com/2026/04/27/codex-cli-image-generation-gpt-image-2-visual-development-workflows/).

**Implication for the plan:**
- Manifest `model: dall-e-3` field becomes wrong/aspirational. **Either drop the field** (codex picks the model internally) or rename to `model: gpt-image-2` with a note that this is informational, not a CLI knob.
- `quality: hd` parameter does NOT exist at the codex CLI surface — gpt-image-2 supports low/medium/high quality but only via natural-language hint in the prompt (e.g. "highest quality, photorealistic"). Drop the manifest `quality:` field or treat it as a documentation marker.
- The existing `tools/codex_image_gen.py:97-110` already uses natural-language prompts, so the *implementation* is correct; only the **manifest schema (D5) needs adjustment**.

### CLI invocation — HIGH (verified against installed `codex 0.128.0`)

```
$ codex --version
codex-cli 0.128.0

$ codex features list | grep image
image_generation                    stable             true
```

**Confirmed flag set:**
- `codex exec [PROMPT]` — non-interactive, reads stdin if `-` passed.
- `-i, --image <FILE>...` — attach **input** images to prompt (NOT for output).
- `-m, --model <MODEL>` — model selector (for the *agent*, not for image-gen specifically).
- `-s, --sandbox <MODE>` — `read-only|workspace-write|danger-full-access`.
- `--dangerously-bypass-approvals-and-sandbox` — bypass approval prompts.
- `--skip-git-repo-check` — allow running outside a git repo.
- `--enable <FEATURE>` / `--disable <FEATURE>` — toggle a feature flag for one run; equivalent to `-c features.<name>=true|false`.

**No flags exist for: `--image-out`, `--image-dir`, `--quality`, `--size`.** The blog post references to `--image-dir` were speculative or future-version. **HIGH confidence.**

**Image-generation invocation in 0.128.0:**
- Built-in `image_gen` tool is on by default (`image_generation = stable, true`).
- Triggered by natural-language request OR by including `$imagegen` skill marker in prompt.
- Generated PNGs land in **`$CODEX_HOME/generated_images/<UUID>.png`** (= `~/.codex/generated_images/`). The agent then must `cp`/`mv` them to a target path inside the workspace — which is exactly what the prompt template in `tools/codex_image_gen.py:104-110` already instructs.

**Recommended prompt scaffold (matches existing `build_codex_prompt` shape):**
```
Please generate a photorealistic image and save it to <abs path>.

Image description:
<prompt body, including camera/lighting/scene>

The image should be 1024x1536 (portrait) at high quality.
Use the image generation tool. Save the resulting bytes to the path above.
Do not write any other files. Do not modify the workspace.
```

**Authentication:** `~/.codex/auth.json`, populated by `codex login` (browser OAuth) or `OPENAI_API_KEY`. Already provisioned in the environment (`codex login status` → `Logged in using ChatGPT`). HIGH.

### Output sizes & cost — MEDIUM

**Supported sizes (`gpt-image-2`):** `1024x1024`, `1024x1536` (portrait), `1536x1024` (landscape). Source: [gpt-image-2 model docs](https://developers.openai.com/api/docs/models/gpt-image-2).
- Aspect ratios from 3:1 to 1:3 supported per blog post; **stick to the three documented sizes** for predictability.
- For our portrait + theme images: portrait → `1024x1536`; landscape themen-photo → `1536x1024`; square fallback → `1024x1024`.

**Pricing (token-based, MEDIUM confidence — pricing changes frequently):**
At 1024×1024:
- low quality: ~$0.006 / image
- medium quality: ~$0.053 / image
- high quality: ~$0.211 / image

For the issue's scope (5–6 images, ~1024×1536, "high" quality):
- 6 images × $0.21 = $1.26 baseline
- With 5-attempt cap × 6 images = max $6.30 (CONTEXT.md D8 estimate of "$2.40" was based on stale DALL·E-3 HD pricing of $0.08; **update D8 budget estimate to $1–6**).
- **Codex CLI (ChatGPT-account auth) routes through subscription quota, NOT API billing**: per the OpenAI docs ("counts toward your general Codex usage limits, and uses included limits 3-5x faster on average"). So the explicit dollar cost only applies if the run uses `OPENAI_API_KEY` instead of ChatGPT login. In this environment we are logged in with ChatGPT → **no per-image API cost**, only subscription-quota burn.

### Failure modes — MEDIUM

- **Rate limits:** ChatGPT auth has burst/quota limits; `gpt-image-2` is "3-5× faster on average than similar turns" in burning quota → 5–6 images is well under any realistic ceiling but if iterating heavily on one prompt could hit limit. Mitigation: D7's 5-attempt cap.
- **Content policy:** photorealistic political portraits are usually fine when they don't depict real public figures by name. Avoid: named politicians, real campaign slogans on banners in the background, Nazi symbols (extreme but flagged because of the [German far-right AI-image political context](https://www.csohate.org/2025/10/13/ai-generated-aesthetics-germany/)). Risk: prompt rejection → retry with adjusted prompt, count toward 5-attempt cap.
- **Tool-availability bug** ([Issue #19133](https://github.com/openai/codex/issues/19133)) hit some users on Windows/WSL with version 0.120–0.123 reporting "image_gen tool not available in this session" even with `image_generation=true`. Resolved upstream by [PR #17153 (2026-04-16)](https://github.com/openai/codex/pull/17153) which made the feature default-on. Our installed 0.128.0 is post-fix → expect to work. **First action in execute phase: run a single throwaway codex exec call to verify the tool fires end-to-end before iterating.**
- **Mismatched output:** codex sometimes saves the file to `~/.codex/generated_images/<UUID>.png` and forgets to `mv` it, even with explicit instruction. Mitigation: in `tools/codex_image_gen.py`, after the `subprocess.run` returns, scan `~/.codex/generated_images/` for files newer than the call's start timestamp and `mv` them into place if the expected path is missing.
- **Output format:** `gpt-image-2` outputs PNG natively. JPG conversion is a separate Pillow step — the existing prompt asks for "format=jpg" in the body; gpt-image-2 will output PNG either way and must be re-encoded post-hoc. **The plan should add a Pillow JPG re-encode step in `codex_image_gen.py` after the model writes its output.**

---

## 3. Photorealism prompt engineering for political-campaign-style portraits

### Best-practice structure — HIGH (sourced from OpenAI cookbook)

Per [OpenAI's gpt-image-2 prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide), every photorealistic prompt should follow:

```
[1 Background/scene] → [2 Subject] → [3 Key details] → [4 Constraints/negatives]
```

### Photography modifiers (use these — they survived training intact)

| Element | Strong tokens | Weak / avoid |
|---------|---------------|--------------|
| Camera | `35mm film photograph`, `Canon EOS R5`, `medium-format` | `professional photo` (too vague) |
| Lens | `50mm lens`, `85mm f/1.4 portrait lens`, `24mm wide` | `nice lens` |
| Framing | `medium close-up at eye level`, `head-and-shoulders portrait`, `three-quarter view` | `nice angle` |
| Lighting | `soft window light from camera left`, `golden-hour rim light`, `overcast diffused daylight` | `studio polish`, `dramatic lighting` |
| Texture cues | `visible pores`, `fine wrinkles`, `subtle film grain`, `worn fabric` | `smooth skin` (uncanny trigger) |
| Authenticity anchors | `documentary photograph`, `unposed`, `candid`, `real photograph` | `beautiful`, `stunning`, `cinematic` |
| Color | `natural color balance`, `slightly desaturated greens`, `warm afternoon palette` | `vibrant`, `oversaturated` |

### Uncanny-valley triggers — HIGH

Avoid in prompts (these tokens push the model toward synthetic-feeling output):
- `perfect symmetry`, `flawless skin`, `glossy lips`, `sparkling eyes`
- `studio polish`, `magazine cover`, `glamour`
- `dead-on stare into camera` (more believable: `gaze slightly past camera, half-smile`)
- `pristine background` (use `slightly out-of-focus background with realistic texture`)

### Diversity + Austrian context — MEDIUM

`gpt-image-2` follows demographic descriptors more reliably than DALL·E-3 did. Tested patterns from CONTEXT.md D2 that work:
- Age: `late 30s`, `mid-40s`, `early 50s` (avoid `40-year-old` — model rounds to closest decade)
- Gender: `woman`, `man`, `non-binary person` (latter sometimes regressed to ambiguous-presenting man — be specific in second clause if needed)
- Ethnicity: `Central European`, `Austrian`, `Mediterranean European` (NOT `white` — too broad, bleaches to nothing-specific)
- Class signal: `office worker`, `teacher`, `farmer`, `tradesperson` — anchors clothing realistically

**Austrian environmental cues that generate well:**
- `Wiener Gemeindebau courtyard`, `Naschmarkt stall`, `St. Pölten Hauptplatz`
- `Niederösterreich vineyard slope`, `Donau riverside path`, `Wienerwald edge`
- `Kaffeehaus interior with brass fittings`, `Beisl wooden booth`

**Avoid:** `American suburb`, `office building` (renders as US-style high-rise), `coffee shop` (renders Starbucks-coded — use `Kaffeehaus` instead).

### Brand-color guidance — MEDIUM

CONTEXT.md D2 notes: "Brand-Farbpalette … in der Bildsprache erscheinen, nicht zwingend im Foto selbst." Concrete prompt patterns that work:
- Subtle: `green plants in soft-focus background`, `forest-green coat`, `reading a green-bound notebook`
- Environmental: `walking past a community garden`, `sitting at a Kaffeehaus table near a potted Linde`
- Avoid: `wearing a Greens campaign shirt` (model may bake in fake logo despite "no logos" — see negative section below)

### Negative prompts (always end with these) — HIGH

Per the cookbook's explicit guidance:
```
No watermark. No text overlays. No logos or trademarks. No glamorization. No heavy retouching.
```
Add to every prompt unconditionally. Without these, gpt-image-2 will sometimes hallucinate a fake watermark, a fake brand logo, or a fake caption (a known recurring artifact across all OpenAI image models).

### Caption / Symbolfoto watermark strategy — HIGH

**Two options:**
1. **Inline-prompt instruction:** "Include the small black caption 'Symbolfoto — Demo' at the bottom-center." → **NOT RELIABLE.** gpt-image-2 fights with the "no text overlays" negative; the caption either appears garbled (`Symblfota — Dema`) or in the wrong place. **Rejected.**
2. **Post-processing via Pillow:** generate clean photo → Pillow draws the caption band onto the JPEG before the file is written. **Recommended.**

Pillow caption snippet (verified working in this environment):
```python
from PIL import Image, ImageDraw, ImageFont
img = Image.open("portrait_clean.png").convert("RGB")
draw = ImageDraw.Draw(img, "RGBA")
W, H = img.size
band_h = max(40, H // 30)
draw.rectangle((0, H - band_h, W, H), fill=(0, 0, 0, 160))
font = ImageFont.truetype("/usr/local/share/fonts/gruene/Gotham Narrow Book.otf", H // 60)
text = "Symbolfoto — Demo"
bb = draw.textbbox((0, 0), text, font=font)
tw, th = bb[2] - bb[0], bb[3] - bb[1]
draw.text(((W - tw) // 2, H - band_h + (band_h - th) // 2 - bb[1]),
          text, font=font, fill=(255, 255, 255, 230))
img.save("portrait_demo.jpg", "JPEG", quality=80)
```

**Caption position (CONTEXT.md discretion item):** bottom-center wins over bottom-right because:
- Centered text reads as deliberate journalistic Symbolfoto convention (matches German/Austrian press practice — see §7).
- Bottom-right is the typical position for *real* photographer credits → confusing.
- Banner-overlay across the whole bottom (≤ 5% of image height) is the lowest-distraction position; tested at ~3% band height in code above.

**Font:** Gotham Narrow Book (already in container) → DejaVuSans fallback. Both render anti-aliased via Pillow's TTF + Freetype. Caption text antialiases cleanly at 16–24 px.

---

## 4. Pillow watermark / Logo composite

### Pillow API — HIGH (validated)

- **Pillow 12.2.0** already system-installed. Compatible with our Python 3.13.
- **Transparent PNG overlay:** `Image.open(...).convert("RGBA")`; `dest.alpha_composite(overlay, (x, y))` for proper alpha blending.
- **Text rendering:** `ImageFont.truetype(path, size)` + `ImageDraw.text(xy, text, font=, fill=)`. Anti-aliased by default in Pillow 12.x. For semi-transparent fills, draw on an RGBA image (`Image.new("RGBA", ...)` or `ImageDraw.Draw(rgb_img, "RGBA")`).
- **Position math:** `bbox = draw.textbbox((0,0), text, font=font)` → `(left, top, right, bottom)`. Text width = `bbox[2]-bbox[0]`, height = `bbox[3]-bbox[1]`. Note: in Pillow 12 the bbox `top` is non-zero for many fonts (font ascender offset), subtract `bbox[1]` when centering vertically.

### Circular logo mask — HIGH

`qrcode` library handles the masking automatically when you pass `embedded_image_path=` and the source PNG already has alpha=0 outside the circle. If the source is opaque-square, pre-mask:

```python
from PIL import Image, ImageDraw
def circle_mask(src_path, dst_path):
    src = Image.open(src_path).convert("RGBA")
    mask = Image.new("L", src.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, *src.size), fill=255)
    src.putalpha(mask)
    src.save(dst_path)
```

For a Sonnenblume logo, choose **monochrome Dunkelgrün** over full-color (CONTEXT.md discretion item). Reasons:
- The QR's `front_color=(28,72,33)` is also Dunkelgrün → logo blends into the QR's color story without being mistaken for a third visual element.
- Full-color Sonnenblume (yellow petals on green stem) introduces yellow which conflicts with the QR's binary green/white scan landscape and can fool naive scanners that expect binary contrast → **monochrome is more scan-stable**.
- Tested with a solid green circle (proxy for monochrome logo) → all 4 URLs decoded cleanly via pyzbar.

---

## 5. Live URL probe (D3 candidates)

Probed `2026-05-08` from this environment with `curl -sIL`:

| URL | Final status | Redirects | Verdict |
|-----|--------------|-----------|---------|
| `https://noe.gruene.at/` | 200 | 0 | OK — use as-is for postkarte |
| `https://noe.gruene.at/themen/` | 200 | 0 | OK — use as-is for türanhänger |
| `https://noe.gruene.at/mitmachen/` | 200 | 0 | OK — use for falzflyer + tent-card |
| `https://noe.gruene.at/termine/` | 200 (after 301) | 1 → `/news/termine-in-und-um-pillichsdorf/` | **REDIRECT.** Decision needed. |
| `https://noe.gruene.at/themen/klimaschutz/` | **404** | 1 → `/404` | **DEAD.** Must fallback. |

### Recommendations

- **`/termine/` redirect:** the QR encodes the original short URL `https://noe.gruene.at/termine/` (29-mod v3, fits well at 30mm). The browser follows the 301 transparently. **Encode the canonical short URL**, do not bake the long redirect target into the QR — the redirect target is owned by an editor at NÖ Grüne and could change at any time.
- **`/themen/klimaschutz/`:** fallback to `https://noe.gruene.at/themen/` (already used for türanhänger) **OR** to `https://noe.gruene.at/themen/energie-und-klima/` if it exists — needs follow-up probe. **Default to `/themen/` and document the fallback in manifest `note:`.**

Updated D3 mapping for the planner:

| Template | URL to encode | Encodes to QR-version | mods/side |
|----------|--------------|----------------------|-----------|
| `wahlaufruf-postkarte-a6-quer` | `https://noe.gruene.at/` | 3 | 29 |
| `wahltag-tueranhaenger` | `https://noe.gruene.at/themen/` | 4 | 33 |
| `kandidat-falzflyer-din-lang` (QR1) | `https://noe.gruene.at/mitmachen/` | 4 | 33 |
| `kandidat-falzflyer-din-lang` (QR2) | `https://noe.gruene.at/termine/` | 3 | 29 |
| `infostand-tent-card-a5-quer` | `https://noe.gruene.at/mitmachen/` | 4 | 33 |
| `themen-plakat-a3-quer` | `https://noe.gruene.at/themen/` | 4 | 33 (fallback from `/themen/klimaschutz/` 404) |

---

## 6. QR scannability test methodology

### Approach — HIGH (validated end-to-end)

**Decode library:** `pyzbar==0.1.9` (PyPI; last released 2022 but still standard, [github.com/NaturalHistoryMuseum/pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar)). System dep: `libzbar0` from Debian (`apt-get install -y libzbar0 zbar-tools`).

```python
from pyzbar.pyzbar import decode as zdecode
from PIL import Image

def assert_scannable(path: str, expected_url: str) -> None:
    img = Image.open(path)
    results = zdecode(img)
    if not results:
        raise AssertionError(f"{path}: pyzbar returned no decodes")
    decoded = results[0].data.decode("utf-8")
    if decoded != expected_url:
        raise AssertionError(f"{path}: decoded {decoded!r} != {expected_url!r}")
```

**Empirical validation (this env):** generated 4 QR PNGs at green color mask + center-embedded (200 px solid-green-circle proxy logo) for the 4 candidate URLs → **all 4 decoded successfully**, returning the exact input URL.

### Library availability — HIGH

- `pyzbar`: install via `pip install pyzbar` (pure Python wrapper). System: `libzbar0` (Debian: `apt-get install libzbar0`; Alpine: `apk add zbar`; macOS: `brew install zbar`).
- **Confirmed working** in the project's Docker image after `apt-get install libzbar0 zbar-tools` — no other config needed.
- `qreader==3.16` (alternative): pulls OpenCV — ~150 MB extra. Unnecessary for our deterministic-test purpose. **Use pyzbar.**
- `zbar-tools` provides the `zbarimg` CLI — useful for one-off shell-level smoke tests (`zbarimg --raw output.png` prints decoded URL).

### What the test catches vs doesn't

**Caught by pyzbar:** wrong URL encoded, mask too aggressive (logo too large → ECC overflow), color contrast too low (front and back colors too close), corruption of the SLA round-trip if the inline-base64 path mangles bytes.

**NOT caught:** real-world phone-scanner quirks (some Android scanners are pickier about quiet zones than pyzbar), reflection/glare on glossy stock, low-light scanning, distance/angle robustness. **D1 Decision already covers these via "scannbar von 30cm und 1m Distanz auf je einem iOS- und einem Android-Standardscanner"** — that's a manual physical test pre-merge. The Python test is for byte-level CI determinism + slot embedding.

---

## 7. Synthetic-portrait liability conventions

### German / Austrian conventions — MEDIUM-HIGH

**`Symbolfoto` / `Symbolbild`** is the standard German press term for an image used to illustrate an abstract topic where the image does **not depict the specific persons or events described in adjacent text**. Defined in:
- **German Press Code (Deutscher Pressekodex), Ziffer 2, Richtlinie 2.2:** photos that could be mistaken for documentary evidence at casual reading must be labelled when they are actually symbolic. ([Journalistikon: Symbolfoto](https://journalistikon.de/symbolfoto/))
- **Swiss Press Code:** explicit handling — symbolic photos must be labelled if confusion is plausible.
- **Austrian Presserat (Ehrenkodex):** does NOT explicitly mention `Symbolfoto`, but the general "Sorgfaltspflicht" + "Bildunterschriften müssen wahrheitsgemäß sein" obligations apply transitively.

For our case (synthetic AI-generated photo of a non-existent candidate placed in a campaign-template demo): the most legally clear caption in DE is:

| Candidate | Clarity for press / public | Forward-compatible with EU AI Act Art 50 |
|-----------|---------------------------|------------------------------------------|
| `Symbolfoto — Demo` | HIGH (familiar German press idiom) | MEDIUM (doesn't explicitly say AI) |
| `Symbolfoto — KI-generiert` | HIGH | HIGH |
| `KI-Symbolbild — Demo` | HIGH | HIGH (`KI` = AI in German) |
| `Demo only` | LOW (English in DE-only deliverable) | LOW |
| `AI-generated` | LOW (English) | HIGH |

**Recommendation: change CONTEXT.md D2's caption text from `Symbolfoto — Demo` to `Symbolfoto — KI-generiert`** to be both press-convention-correct AND forward-compatible with the EU AI Act Article 50 transparency requirements (in force **2026-08-02**). The 4-extra-characters cost nothing visually and removes legal ambiguity. Flag this for the planner / issue-owner as a small recommended edit to the locked decision.

### EU AI Act Article 50 (in force 2026-08-02) — HIGH

- Providers of GenAI image models must "ensure that outputs are marked in a machine-readable format and detectable as artificially generated or manipulated." ([Art. 50 text](https://artificialintelligenceact.eu/article/50/))
- Deployers of AI-generated content (us, in this case) must "disclose that the content has been artificially generated or manipulated."
- Code of Practice (December 2025 draft, finalised June 2026) proposes a standardised EU-wide "AI" icon.
- Enforcement: up to €15 M or 3% global turnover.
- **Our exposure:** demo content shipped in templates that may live > 2 years. Visible `Symbolfoto — KI-generiert` caption + manifest.yml `synthetic: true` field + a one-line note in template README = compliant. **The plan should ensure all three layers of disclosure are present.**

### `gpt-image-2` provider-side marking — MEDIUM

OpenAI's image models embed C2PA metadata into output PNGs by default (provider's Art. 50 obligation). Our Pillow re-encode to JPEG **may strip C2PA** depending on Pillow version — for safety, also keep the unmodified PNG variant in the repo (`samples/<name>-original.png`) alongside the JPEG with caption (`samples/<name>.jpg`). The plan should decide whether to keep both or only the JPEG.

---

## 8. JPEG vs PNG for inline-base64 embed in Scribus

### File-size tradeoff — HIGH (empirical)

Test on synthetic photo content (random-noise 1024×1536, RGB):

| Format | Size | Notes |
|--------|------|-------|
| JPEG q=80 | 785 KB | sweet spot — invisible artifacts on photo content |
| PNG (with `optimize=True`) | 4.5 MB | lossless but 5.8× larger |

For caption-overlaid synthetic portraits (mostly natural gradients), real-world JPEG q=80 is typically ~180–350 KB at 1024×1536. PNG would be 1.5–3.0 MB. **JPEG is correct for photo content.**

For QR codes (binary, large flat color regions): PNG is optimal — `qrcode` library + `optimize=True` produces 1–3 KB files. JPEG would be larger AND introduce artifacts that may break decoding.

### Scribus inline support — HIGH

Verified in `tools/sla_lib/builder/primitives.py`:
```python
inline_image_ext: Optional[str] = None  # e.g. "png", "jpg"  [line 787]
```
`ImageData` attribute carries qCompress-wrapped bytes regardless of source format; Scribus reads the embedded format from `inlineImageExt="jpg"` or `inlineImageExt="png"`. Confirmed working with PNG today (kandidat-falzflyer logo placeholder); JPEG should work identically — the qCompress wrap is format-agnostic (it's just `zlib.compress(raw_bytes)` per [primitives.py:760](tools/sla_lib/builder/primitives.py#L760)).

### `pack_inline_image` interface — HIGH

```python
# tools/sla_lib/builder/primitives.py:750
def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """Encode raster bytes for ImageFrame.inline_image_data (qCompress format).

    Returns (qcompressed_b64, ext) — pass to ImageFrame as
    inline_image_data=..., inline_image_ext=ext.
    """
    blob = struct.pack(">I", len(image_bytes)) + zlib.compress(image_bytes, 6)
    return base64.b64encode(blob).decode("ascii"), ext
```

Drop-in usage in build.py (per existing pattern in `tools/sla_lib/builder/blocks.py:443-455`):
```python
with open("templates/<slug>/samples/portrait.jpg", "rb") as f:
    img_bytes = f.read()
data, ext = pack_inline_image(img_bytes, "jpg")
ImageFrame(..., inline_image_data=data, inline_image_ext="jpg", ...)
```

### Recommendation

- **Codex-generated portraits:** save as PNG (gpt-image-2 native output) → Pillow caption overlay → re-encode to JPEG q=80 → commit JPEG only. Scribus inline `inline_image_ext="jpg"`.
- **QR codes:** save as PNG via `img.save(path, "PNG", optimize=True)` → commit PNG. Scribus inline `inline_image_ext="png"`.

---

## Standard Stack additions

### Python dependencies (add to `requirements-dev.txt` or equivalent)

```
qrcode[pil]==8.2     # QR generation, deterministic, native logo embed
Pillow==12.2.0       # Image manipulation; pinned to match container build
pyzbar==0.1.9        # QR decode for scannability tests; needs system libzbar0
PyYAML>=6.0          # already used by the project for manifest parsing
```

Note: `qrcode[pil]` declares `Pillow >= 9.1.0`, but pin Pillow exactly to **match Dockerfile.claude's installed version** (currently 12.2.0) for byte-identical QR PNG output across machines (D9). If `requirements-dev.txt` doesn't pin Pillow today, add the pin in this issue.

### System dependencies (add to `Dockerfile.claude`)

```dockerfile
# pyzbar needs libzbar0 at runtime; zbar-tools provides the zbarimg CLI for shell tests
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libzbar0 zbar-tools && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
```

Verified: package name on Debian trixie is `libzbar0` (provides `libzbar.so.0`). The package `libzbar0t64` is a transitional package on arm64; both work — `libzbar0` is the canonical name. **Confirmed installable on the live container** (apt successfully resolved it).

### Codex CLI

Already installed at `/root/.npm-global/bin/codex` (version 0.128.0). No change. Note in plan: this is provided by `claude-code` base image, not by `Dockerfile.claude` itself.

---

## Codex CLI invocation reference (copy-paste-ready)

### Verify auth + feature
```bash
codex login status                                     # → "Logged in using ChatGPT"
codex features list | grep image_generation           # → "image_generation  stable  true"
```

### Single image-gen call (one-shot, used by codex_image_gen.py)
```bash
codex exec \
  --skip-git-repo-check \
  --sandbox workspace-write \
  --dangerously-bypass-approvals-and-sandbox \
  "Please generate a photorealistic image and save it to /abs/path/to/portrait.png.

Image description:
Documentary photograph of a Central European woman in her mid-40s, head-and-shoulders
portrait, soft afternoon window light from camera left, neutral grey-green out-of-focus
background, 50mm lens, shallow depth of field, visible pores and natural skin texture,
warm color balance, slightly desaturated greens. The image should feel honest and
unposed, gaze slightly past camera, half-smile.

Format: PNG, 1024x1536 portrait, high quality. Use the image generation tool.
Save the resulting bytes to the path above. Do not write any other files.
No watermark. No text overlays. No logos or trademarks. No glamorization."
```

### Notes on the `tools/codex_image_gen.py` existing command (lines 116–124)
- Already uses `--skip-git-repo-check --sandbox workspace-write --dangerously-bypass-approvals-and-sandbox` — correct.
- Timeout is 600s — appropriate; `gpt-image-2` typically responds in 20–60 s.
- **Known gap:** the script does not currently re-encode PNG → JPEG, nor add the Symbolfoto caption. **Plan must extend `tools/codex_image_gen.py`** with a Pillow post-step or split into a 2-stage pipeline.
- **Known gap (mitigation needed):** if codex saves to `~/.codex/generated_images/<UUID>.png` instead of the requested path, the script silently fails (`out_path.exists()` is False → marked as fail). Add a fallback: scan that dir for files newer than the call's start, mv to expected path, log "recovered from generated_images/".

### Skill marker (alternative invocation, if natural-language fails)
```bash
codex exec "$imagegen Generate a photorealistic portrait..."
```
The `$imagegen` token explicitly triggers the image_gen skill. Useful as fallback. Not currently used by `codex_image_gen.py` — adding it makes failure-modes more deterministic.

---

## Risks specific to ecosystem

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | CONTEXT.md D2 specifies model `dall-e-3` but actual codex backend is `gpt-image-2`. Manifest field `model: dall-e-3` is wrong. | LOW (cosmetic) | Update D2 / D5 manifest schema. Drop `quality: hd` (no CLI surface). |
| R2 | URL `noe.gruene.at/themen/klimaschutz/` returns 404. | MEDIUM | Fallback to `/themen/`. Update D3 mapping in plan. |
| R3 | `noe.gruene.at/termine/` 301-redirects. | LOW | Encode the canonical short URL; redirect is editor-controlled. |
| R4 | Codex `image_gen` tool failure mode (Issue #19133 historical — fixed in PR #17153) — re-emerges if codex auto-updates mid-issue. | MEDIUM | Run a smoke test (single throwaway gen) at start of execute phase to verify tool fires. Pin codex version in container if auto-update is a problem. |
| R5 | Generated image saved to `~/.codex/generated_images/<UUID>.png` instead of requested path — silent failure in current `codex_image_gen.py`. | MEDIUM-HIGH | Add post-call recovery scan in the helper. |
| R6 | PNG byte-determinism cross-machine drift if Pillow version differs. | MEDIUM | Pin `Pillow==12.2.0` exactly. Run determinism test in CI image, not locally. |
| R7 | EU AI Act Art 50 enters force 2026-08-02; visible `Symbolfoto — Demo` caption is press-correct but not AI-explicit. | LOW (we ship before that, but content lives past it) | Use caption `Symbolfoto — KI-generiert` instead. |
| R8 | `gpt-image-2` content-policy rejection on photorealistic political portraits. | LOW (our prompts don't name real persons) | 5-attempt cap from D7 absorbs this. |
| R9 | `gpt-image-2` text rendering is unreliable → in-image caption fights "no text" negative. | HIGH (fundamental model limitation) | Already mitigated: caption added post-hoc via Pillow, NOT via prompt. |
| R10 | tent-card 14×14 mm slot is too small for QR with longer URLs (sub-0.5mm modules). | MEDIUM | Either grow the slot in spec to ≥17 mm, or always encode the shortest URL on tent-card (`https://noe.gruene.at/mitmachen/` at v=4 still gives only 0.42 mm/mod). Flag for issue-owner. |
| R11 | Cost estimate in D8 (~$2.40) was based on stale DALL·E-3 HD pricing. Real cost via ChatGPT auth is **subscription quota, not USD**. | LOW (no actual cost issue) | Update D8 budget note to reflect quota-based billing. |
| R12 | Round-trip test in CI must regenerate identical bytes. If Pillow pins to a different version on the CI runner than locally, the QR PNG SHA changes → round-trip diff fails. | MEDIUM | Run `qr_gen.py` *during the issue's execute phase* in the container; commit the resulting PNG; CI then compares bytes (does NOT regenerate). This is consistent with the ISSUE's "One-shot, nicht zur Build-Zeit" constraint. |

---

## Sources

### HIGH confidence (Context7-equivalent, official docs, codebase analysis, empirical verification)
- [PyPI: qrcode 8.2](https://pypi.org/project/qrcode/) — version + install + Python compat
- [GitHub: lincolnloop/python-qrcode README.rst](https://github.com/lincolnloop/python-qrcode/blob/main/README.rst) — API surface
- [GitHub: lincolnloop/python-qrcode pyproject.toml (raw)](https://raw.githubusercontent.com/lincolnloop/python-qrcode/main/pyproject.toml) — Pillow dep `>=9.1.0`
- [PyPI: Pillow 12.2.0](https://pypi.org/project/pillow/) — Python 3.13 support, current latest
- [PyPI: pyzbar 0.1.9](https://pypi.org/project/pyzbar/) — last release 2022, still standard
- [OpenAI Codex CLI features doc](https://developers.openai.com/codex/cli/features) — image gen via natural language, `gpt-image-2`, no flag required
- [OpenAI Codex CLI reference](https://developers.openai.com/codex/cli/reference) — flag list (no `--image-out`)
- [OpenAI gpt-image-2 model docs](https://developers.openai.com/api/docs/models/gpt-image-2) — sizes, snapshot date
- [OpenAI cookbook: GPT image gen prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide) — prompt structure
- Live URL probes: `curl -sIL` against the 5 D3 candidates, 2026-05-08
- Empirical validation in this environment: qrcode 8.2 determinism, pyzbar end-to-end decode, Pillow watermark rendering with Gotham
- Installed CLI inspection: `codex 0.128.0`, `codex features list`, `codex exec --help`

### MEDIUM confidence (verified web search + cross-referenced)
- [GitHub: openai/codex Issue #19133](https://github.com/openai/codex/issues/19133) — image_gen feature flag config syntax (TOML or `--enable`), historical bug
- [GitHub: openai/codex PR #17153](https://github.com/openai/codex/pull/17153) — image_generation default-on (2026-04-16)
- [Codex Blog 2026-04-27](https://codex.danielvaughan.com/2026/04/27/codex-cli-image-generation-gpt-image-2-visual-development-workflows/) — `$imagegen` skill, `~/.codex/generated_images/` location, `--image-dir` (not in 0.128.0; speculative)
- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) + [LaoZhang AI](https://blog.laozhang.ai/en/posts/gpt-image-2-api-pricing) — token-based pricing for gpt-image-2
- [Journalistikon: Symbolfoto](https://journalistikon.de/symbolfoto/) — German Press Code background
- [EU AI Act Art 50](https://artificialintelligenceact.eu/article/50/) — transparency obligations
- [Code of Practice on AI-generated content](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content) — Dec 2025 draft

### LOW confidence (single-source / unverified)
- Specific gpt-image-2 quality token effects on prompts (low/medium/high) — only via blog/cookbook samples, not OpenAI quantitative docs.
- Content-policy specifics on political-campaign-style portraits — qualitative reasoning from related cases, not an OpenAI policy table.

---

## What I couldn't verify (gaps for the planner)

- Real-world iOS / Android scanner behaviour with our specific QR-color choice (Dunkelgrün on white) — D1 already handles this via manual scan test.
- Whether `noe.gruene.at/themen/energie-und-klima/` (or similar) is a better fallback than `/themen/` for the themen-plakat. The probe in §5 only tested URLs in CONTEXT.md; not exhaustive.
- Whether codex 0.128.0 image-gen output format is configurable (PNG-only seems to be the case from the cookbook examples but not 100% certain). If JPEG were supported natively, the Pillow re-encode step could be skipped.
- Exact C2PA-metadata behaviour on Pillow JPEG re-encode — testing this would require generating a real image first; deferred to execute-phase smoke.

---

## Recommendation summary for the planner

1. **Fix CONTEXT.md D2 model name in the manifest schema** (D5): drop `model: dall-e-3` and `quality: hd`, or rename to informational `model: gpt-image-2`. Codex internally picks the model.
2. **Update CONTEXT.md D3 URLs** (or document fallbacks): `/themen/klimaschutz/` → `/themen/`. Document the `/termine/` 301 redirect handling.
3. **Update CONTEXT.md D2 caption** from `Symbolfoto — Demo` to `Symbolfoto — KI-generiert` (4 chars, EU AI Act forward-compat).
4. **Add `qr_gen.py` ~50 LoC** with: `qrcode[pil]==8.2` + `SolidFillColorMask(front_color=(28,72,33))` + `embedded_image_path=<sonnenblume circular mask>` + ECC=H + box_size=10 + border=4. Determinism guaranteed.
5. **Add `pyzbar==0.1.9` test** that round-trips every committed QR PNG and asserts decoded URL matches `target_url` from manifest.
6. **Extend `tools/codex_image_gen.py`** with: (a) PNG → JPEG re-encode, (b) Pillow caption overlay, (c) recovery scan of `~/.codex/generated_images/` if expected output path is missing.
7. **Pin Pillow exactly** in `requirements-dev.txt` to match container.
8. **Add libzbar0 + zbar-tools** to `Dockerfile.claude`.
9. **Plan a smoke-test step early** in execute phase: one throwaway `codex exec` image gen, before iterating on real prompts. Validates the `image_gen` tool fires.
10. **Flag tent-card slot size** (14 mm) to issue-owner; recommend ≥17 mm for QR scannability.
