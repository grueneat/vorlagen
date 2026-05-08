# Ecosystem Research — 13-zentralisierte-demo-bild-bibliothek

**Researched:** 2026-05-08
**Issue:** Zentralisierte Demo-Bild-Bibliothek + alle Templates auffüllen
**Scope:** ecosystem-only (libraries, prompts, AI Act, JSON schema, image determinism, library taxonomies)

---

## 1. Pillow 12.2 image cropping for layout (D7)

### Finding 1.1 — `ImageOps.fit()` is the right primitive — HIGH

`PIL.ImageOps.fit(image, size, method=Resampling.BICUBIC, bleed=0.0, centering=(0.5, 0.5))`
returns a **resized AND cropped** image at the requested aspect ratio in one call.

- If source aspect < target aspect → scales to target width, crops top/bottom.
- If source aspect > target aspect → scales to target height, crops left/right.
- `centering=(0.5, 0.5)` = center crop. `(0.5, 0.3)` = bias towards upper-third
  (faces in portraits). For our use case (D7 says „center-crop reicht"), stick
  with `(0.5, 0.5)`.

**Source:** [Pillow 12.2.0 ImageOps docs](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html)

### Finding 1.2 — Recommended pattern — HIGH

```python
from PIL import Image, ImageOps
from io import BytesIO

def crop_for_frame(
    src_path: Path,
    target_w_mm: float,
    target_h_mm: float,
    *,
    dpi: int = 300,
    quality: int = 80,
) -> bytes:
    """Center-crop + scale to target frame at print DPI. Returns JPEG bytes.

    Deterministic for fixed (Pillow version, libjpeg version, source bytes,
    quality, subsampling). See Finding 1.4.
    """
    target_w_px = round(target_w_mm * dpi / 25.4)
    target_h_px = round(target_h_mm * dpi / 25.4)
    with Image.open(src_path) as im:
        rgb = im.convert("RGB")  # JPEG can't store RGBA
        fitted = ImageOps.fit(
            rgb,
            (target_w_px, target_h_px),
            method=Image.Resampling.BICUBIC,
            centering=(0.5, 0.5),
        )
        buf = BytesIO()
        fitted.save(
            buf,
            format="JPEG",
            quality=quality,
            optimize=True,
            subsampling=2,    # 4:2:0 — Pillow default; pin explicitly
            progressive=False,  # baseline — pin explicitly
        )
        return buf.getvalue()
```

Why `BICUBIC` not `LANCZOS`: Pillow 12 default for `ImageOps.fit()` is BICUBIC.
Switching to LANCZOS ~doubles encode time and the difference at 300dpi print
density is invisible. Pin BICUBIC for stability.

**Recommendation:** Implement as `library.crop_for_frame()` in
`tools/sla_lib/builder/library.py`. Take `target_w_mm, target_h_mm` as kwargs
matching `ImageFrame(w_mm=, h_mm=)` so callers can pass frame dimensions
verbatim.

### Finding 1.3 — `Image.thumbnail()` is the WRONG choice — HIGH

`Image.thumbnail()` only **shrinks** to fit inside a bounding box and **never
crops**. For a portrait source (1024×1536) and a landscape slot (e.g. 87×60mm
quer-thumbnail), `thumbnail()` would emit 1024×682 with the wrong aspect
embedded — Scribus would then either letterbox or distort. `ImageOps.fit()` is
the correct API.

### Finding 1.4 — JPEG q=80 byte-determinism — MEDIUM-HIGH

**Pillow's JPEG encoder is deterministic for a fixed (Pillow version, libjpeg-turbo
version, input bytes, all encoder kwargs).** The encoder is a thin wrapper
around libjpeg-turbo; identical inputs + identical libjpeg-turbo build → byte-identical
output. This holds within the same Docker image (we pin libjpeg-turbo via Debian
trixie packages and Pillow 12.2 explicitly).

**Caveats:**

- Across Pillow major versions: BICUBIC kernel implementation has been
  stable since Pillow 9; libjpeg-turbo encoder output is stable across
  Pillow versions, but the *resampling step* before it can produce
  different intermediate pixels if Pillow ever changes its BICUBIC kernel
  (no breaks in Pillow 9 → 12 according to release notes).
- **Mitigation:** pin Pillow exactly in Dockerfile.claude when this matters.
  Currently Dockerfile says „Do NOT pin Pillow here" — re-evaluate. **Recommend:
  add `pillow==12.2.0` pin to Dockerfile.claude in this issue's scope** so
  library regen produces identical bytes across rebuilds.
- Subsampling default changed from 4:2:0 in Pillow 9.1+ for quality≥95 (4:4:4)
  but **not for quality=80**, which uses 4:2:0 always. Pin `subsampling=2`
  defensively.
- **Always pin `progressive=False` and `optimize=True`** — defaults differ
  across host environments.

**Sources:**
- [Pillow 12.2.0 image-file-formats JPEG](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)
- [Pillow JpegPresets](https://pillow.readthedocs.io/en/stable/reference/JpegPresets.html)
- [jdhao on PIL JPEG quality](https://jdhao.github.io/2019/07/20/pil_jpeg_image_quality/)

### Finding 1.5 — Saliency-aware cropping — LOW priority

Saliency-aware crop (face/subject detection → crop centered on detected
salient region) requires extra deps (`smartcrop`, `mediapipe`, or a vision
model). Per CONTEXT.md "Claude's Discretion": **center-crop reicht zunächst.**

**Escape hatch already in design:** D7 manifest field `crop_box: [x, y, w, h]`
or `centering: [0.4, 0.3]` for per-image override. Implement when v1
center-crop produces visibly bad output for a specific image (e.g. portrait
where the head is off-center). Don't pre-implement.

**Recommendation:** Skip saliency. Add `centering: [x, y]` optional override in
manifest schema; default `(0.5, 0.5)`.

### Finding 1.6 — Performance: 8 templates × ~5 images = ~40 crop ops per render — HIGH

At 1024×1536 source → ~1000×700 px crop, BICUBIC: ~80–150ms per crop on a
modern x86 / arm64 CPU. 40 crops = ~5s overhead total per `bin/render-gallery`
run. **Negligible.** Don't pre-cache cropped variants on disk (would balloon
the library and complicate determinism guarantees).

**Recommendation:** Crop at build-time, no on-disk caching of crop variants.
The "pre-cropped variants per slot" alternative (mentioned in user prompt)
fails on DRY — every slot mm change would need a new file.

---

## 2. Codex prompt engineering for thematic political photography

### Finding 2.1 — Documentary framing pattern (validated in #11) — HIGH

The five existing per-template manifests all use a near-identical opening:

> `Documentary photograph of a Central European [subject], [framing],
> soft [time-of-day] light, [50mm/35mm/24mm] lens, slightly desaturated greens,
> warm color balance. Authentic and unposed. No watermark. No text overlays.
> No logos or trademarks.`

Issue #11 had **0 refusals across 6 generations** (Codex CLI 0.128.0,
gpt-image-2). The "documentary" frame + lens specification + neutral
description (no political slogans, no real names) keeps the prompts well
inside the content policy.

**Source:** existing manifests under `templates/*/samples/manifest.yml` and
`.issues/archive/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates/research/codex-pipeline-validation.md`

### Finding 2.2 — Stock-photo-aesthetic avoidance — HIGH

**Stock-photo failure modes:** glossy oversaturated colors, model-poses
(arms crossed, fake smile to camera), generic global location, brand-color
spill (forced green tint everywhere).

**Anti-patterns in prompts:**

| Avoid | Use instead |
|-------|-------------|
| `beautiful`, `stunning`, `cinematic`, `dramatic` | `documentary`, `unposed`, `candid` |
| `professional model`, `posed for camera` | `head-and-shoulders portrait`, `gaze slightly past camera` |
| `vibrant colors`, `bright saturated` | `slightly desaturated greens`, `warm color balance`, `natural skin tones` |
| `studio lighting`, `softbox` | `soft afternoon window light`, `late-afternoon golden hour`, `overcast diffused daylight` |
| `corporate`, `business setting` | `community space`, `wood and glass interior`, `neutral grey-green out-of-focus background` |

**Source:** [GPT Image 2 prompt guide 2026, PixVerse](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide), [OpenAI image-gen models prompting cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)

### Finding 2.3 — Austrian / Niederösterreich visual cues that render reliably — MEDIUM-HIGH

From #11 validation (all 6 prompts produced usable images on first attempt):

| Cue | Renders well | Notes |
|-----|--------------|-------|
| `Niederösterreich farmhouse with vineyards` | yes | golden-hour preset works |
| `Niederösterreich wind-turbine on rolling hill` | yes | mid-distance framing key |
| `Wiener Kaffeehaus interior with brass fittings` | yes | brass fittings strong anchor |
| `small-town Austrian schoolyard` | yes | Dorfstraße keyword critical |
| `Donau riverside path`, `Wienerwald edge` | LOW confidence — not yet tested |
| `Schloss landscape` | LOW — high risk of fairy-tale glamour |
| `Alpine foreland` | MEDIUM — good for backgrounds, weak for foreground subjects |

**Recommendation:** prefer concrete location + activity over generic landscape.
"Niederösterreich vineyard slope at golden hour" beats "Austrian countryside".

### Finding 2.4 — Failure-mode rate for political-context prompts — MEDIUM

#11 generated 6 images with 0 refusals. **However:** the prompts deliberately
avoided named politicians, real campaign slogans, party banners, and Nazi
symbols. Per #11 ecosystem research:

> Risk: prompt rejection → retry with adjusted prompt, count toward 5-attempt cap.

For this issue: same conventions → expect ~0 refusals. Budget assumption:
`max_attempts=5` per slot is enough headroom. **Cost estimate: ~5 new images ×
$0.08 = $0.40, plus ~3 retry attempts × $0.08 = ~$0.64 worst case** (vs. CONTEXT
D10 estimate of $0.40 — close enough).

### Finding 2.5 — gpt-image-2 vs gpt-image-1 — MEDIUM

DALL·E 3 is **deprecated and scheduled for retirement May 2026**. The current
production model when issue #11 ran was `gpt-image-2`, recommended over
`gpt-image-1.5` and `gpt-image-1`. Existing manifests pin `model: gpt-image-2,
quality: high` for portraits (see kandidat-falzflyer manifest line 15-16).

**Recommendation:** continue with `gpt-image-2 / quality: high` for portraits
where face fidelity matters; default model otherwise. The codex CLI in
`tools/codex_image_gen.py` does NOT currently pass model/quality kwargs to
the underlying call (line 282-300) — it relies on Codex picking defaults.
**Open question for plan:** is the `model:` field in the YAML actually
respected, or is it documentation-only? Plan must verify.

**Source:** [GPT Image 2 prompt guide 2026, PixVerse](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide)

---

## 3. Library taxonomies — folder vs tags

### Finding 3.1 — Industry pattern: folders for navigation, tags for cross-cutting — MEDIUM

Design systems (Untitled UI, Relume, Flowbase) consistently combine:

- **Folders/categories** for primary navigation (Buttons, Forms, Cards…)
- **Tags / variant labels** for cross-cutting facets (size, density, state)
- **Search index** built over tag union for filtering

The same pattern applies cleanly to our images:

- `portraits/`, `themen/`, `kontext/`, `qr/` — folder-as-category (D1)
- Tags for cross-cut: `gender:female`, `topic:klimaschutz`, `composition:landscape`

**Source:** [Untitled UI Figma](https://www.untitledui.com/figma), [Relume Figma library](https://www.relume.io/figma-library), [Untitled UI 2026 design systems comparison](https://www.untitledui.com/blog/figma-ui-kits)

### Finding 3.2 — Tags-vs-folders trade-off — HIGH

**Folders** = slow-changing, hierarchical, mutually exclusive. Good for "is this
a portrait or a Themen-shot" — exactly one answer.

**Tags** = fast-changing, flat, multi-value, non-mutually-exclusive. Good for
"renders at golden hour", "shows a single person", "outdoor".

D1 picks folders for category (correct, low entropy) and D4 picks tags for
the rest (also correct, high entropy). **No conflict — design is right.**

### Finding 3.3 — Tag granularity — MEDIUM

Per CONTEXT discretion: "Permissive zunächst, hardening später."

Industry pattern: start with **3–5 tag dimensions, ~5 values per dimension** =
15–25 tag values total. Our D4 schema is in this range:

- Category (4 values: portrait/themen/kontext/qr) — implicit by folder
- gender (3), age (5), setting (4) for portraits
- topic (7+), subtopic (open), composition (3) for themen
- scene (5+) for kontext

Total ~25 values. Schema is appropriately sized. **Don't over-engineer
tag-validation in v1.**

### Finding 3.4 — License management for AI-generated content in template libraries — HIGH

**Industry conventions for synthetic/AI library content:**

- Per-asset metadata field stating provenance (`synthetic: true`, model name,
  prompt for reproducibility).
- License text per asset OR a single library-wide `LICENSE.md` if homogenous.
- "Replace before production use" disclaimer for demo content (Untitled UI,
  Webflow, and similar use this convention for placeholder photography).

D5 already covers this:
```yaml
synthetic: true
license_note: "AI-generated demo image; not a real person/place."
```

**Recommendation:** keep the license_note as a `string` field (not a structured
object), because the disclaimer text serves a documentation purpose, not a
contractual one. Add an optional `replace_in_production: true` flag for explicit
authoring intent (default true for synthetic, false for real photography
when we ever add some).

---

## 4. JSON Schema for manifest validation

### Finding 4.1 — `jsonschema` is NOT installed in the Docker image — HIGH

```
$ python3 -c "import jsonschema"
ModuleNotFoundError: No module named 'jsonschema'
```

Dockerfile.claude does not pip-install it. **Adding it is a one-line addition
to the existing `pip3 install --break-system-packages` block** at line 58.

**Recommendation:** add `'jsonschema==4.26.0'` to the Dockerfile pip install.
The package is small (~70 KB sdist), pure Python, supports Draft 2020-12, and
is the de-facto standard. Released 2026-01-07.

**Source:** [jsonschema 4.26.0 PyPI](https://pypi.org/project/jsonschema/), [python-jsonschema docs](https://python-jsonschema.readthedocs.io/)

### Finding 4.2 — Where to validate: at runtime in `library.load()` — MEDIUM

**Trade-off:**

| Where | Pro | Con |
|-------|-----|-----|
| Runtime in `library.load()` / `library.all_images()` | every call validates; same code path always; no separate tool to remember | small import-time cost; failure happens late (build time, not pre-commit) |
| Separate `tools/check_library.py` | explicit pre-commit / CI gate; failure happens early | another tool to maintain; if dev forgets to run it, drift |
| Both (validate-on-load + check tool wrapping it) | early + always | minimal duplication if the check tool just imports `library` |

**Recommendation:** **validate at module-import time inside
`tools/sla_lib/builder/library.py`** (cheap — happens once per build) +
expose a `library.check()` function that `tools/check_ci.py` can call as part
of the existing CI cascade. **Single code path, two entry points.** No new
dedicated `tools/check_library.py` script needed.

### Finding 4.3 — Example schema sketch — HIGH

Targeting Draft 2020-12, embedded in `tools/sla_lib/builder/library.py` as
a Python dict (keeps the schema co-located with the code that uses it; no
separate `.json` file to drift):

```python
LIBRARY_MANIFEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["images"],
    "properties": {
        "images": {
            "type": "object",
            "patternProperties": {
                "^[a-z][a-z0-9_]*$": {  # ID convention: snake_case
                    "type": "object",
                    "required": ["path", "prompt", "tags", "synthetic"],
                    "properties": {
                        "path": {"type": "string"},
                        "prompt": {"type": "string", "minLength": 20},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "synthetic": {"type": "boolean"},
                        "license_note": {"type": "string"},
                        "size": {"type": "string", "pattern": "^[0-9]+x[0-9]+$"},
                        "watermark": {"type": "string"},
                        "model": {"type": "string"},
                        "quality": {"type": "string"},
                        "centering": {  # optional override, D7 escape hatch
                            "type": "array",
                            "items": {"type": "number", "minimum": 0, "maximum": 1},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                    },
                    "additionalProperties": True,  # permissive — D4 hardening later
                },
            },
            "additionalProperties": False,  # only snake_case IDs
        },
    },
}
```

**Note:** `additionalProperties: True` at the per-image level is intentional —
D4 says "permissive zunächst, hardening später." The schema validates required
fields are present + correctly typed, doesn't ban future extension fields.

---

## 5. EU AI Act Art 50 compliance — multi-template-reuse

### Finding 5.1 — Multi-template reuse does NOT trigger additional disclosure — MEDIUM

**Article 50 obligations:** providers must mark synthetic content in
machine-readable form AND deployers must make the disclosure perceptible.
Once a synthetic image is marked + watermarked, **using it in multiple
templates does not multiply the obligation** — each rendered output (SLA →
PDF) carries the per-image watermark inherently.

**Source:** [EU AI Act Art 50 official text](https://artificialintelligenceact.eu/article/50/)

### Finding 5.2 — "Symbolfoto — KI-generiert" watermark sufficiency — MEDIUM-LOW

**The bottom-band visible watermark from #11 covers the "perceptible
disclosure" obligation when the image is viewed.**

However, the August 2026 enforcement bar requires a **multi-layered marking
strategy**: visible watermark + machine-readable metadata + (optional)
imperceptible watermark / fingerprint.

> A critical requirement is that no single marking technique is sufficient
> to meet the requirements of Article 50 of the Act on its own.
> ([Ashurst on transparency draft](https://www.ashurst.com/en/insights/transparency-of-ai-generated-content-the-eu-first-draft-code-of-practice/))

**Currently we have only the visible band.** This is the strongest single
signal but is technically below the multi-layered bar.

**Risk assessment for THIS issue:**
- Our synthetic content is marked as **demo-only / replace-before-production**
  in the manifest. End users (real campaign teams) replace these images with
  their own photography before publication. The reuse therefore is **internal
  to the template authoring workflow** — not a public-facing AI-generated-content
  output.
- If a campaign team forgets to replace and ships a flyer with our synthetic
  portrait, the visible watermark (`Symbolfoto — KI-generiert`) keeps them
  compliant on the deployer side.

**Recommendation:** keep the visible watermark as v1. Add **JPEG EXIF/XMP
metadata** (`Software: openai/gpt-image-2` + `Description: AI-generated demo image;
not a real person`) as a low-effort second layer:

```python
exif = im.getexif()
exif[0x010E] = "AI-generated demo image; not a real person."  # ImageDescription
exif[0x0131] = "openai/gpt-image-2 (synthetic)"               # Software
im.save(buf, format="JPEG", quality=80, exif=exif)
```

**Defer:** invisible watermarking (C2PA / SynthID) — separate issue, requires
substantial dependency tree and adds limited value while images stay internal.

**Source:** [EU AI Act Art 50](https://artificialintelligenceact.eu/article/50/), [Code of Practice on AI-generated content (EU)](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content), [Herbert Smith on transparency obligations](https://www.hsfkramer.com/notes/ip/2026-03/transparency-obligations-for-ai-generated-content-under-the-eu-ai-act-from-principle-to-practice)

### Finding 5.3 — Provenance preservation across re-export — MEDIUM

Article 50 requires that "existing detectable marks are retained and not
altered or removed" when AI content passes through downstream systems. Our
pipeline **embeds** the watermarked JPEG bytes into Scribus SLAs verbatim
via `inline_image_data` — the visible band passes through unchanged. **Compliant
with current draft Code of Practice** at the visible-watermark layer.

**Caveat:** when build.py runs `crop_for_frame()` it re-encodes the JPEG. The
visible band is preserved by virtue of being in the pixel data (not metadata),
**provided the band is positioned far enough from the crop boundaries**. With
`band_height_pct=0.04` (default in `add_demo_watermark`) and `centering=(0.5, 0.5)`
center crop, the band sits at the bottom-edge of the source image and **may
be cropped off** when the source is portrait but the slot is landscape (top
and bottom get cropped to fit width).

**HIGH-IMPACT EDGE CASE:** crop a portrait (1024×1536) into a landscape slot
(85×60mm = ~1004×708px). `ImageOps.fit` keeps full width, crops top + bottom
proportionally. With watermark at bottom 4% of source (rows 1474–1536),
**after fit-crop the watermark is at row 614–668 of 708 — still visible at
the bottom** because fit preserves the bottom edge proportionally with the top.

Actually verifying this: `ImageOps.fit(im, (W,H), centering=(0.5, 0.5))` for
`im_aspect > target_aspect` crops left/right; for `im_aspect < target_aspect`
crops top/bottom equally. **Source 1024×1536 (aspect 0.667) → target 1004×708
(aspect 1.418): aspect grows → crop top/bottom equally.**

```
crop_h = int(1024 / 1.418) = 722 px from source center.
center_y = 1536/2 = 768 → crop rows 407 to 1129.
Watermark at rows 1474+ is BELOW row 1129 → CROPPED OFF. BAD.
```

**Mitigation:** apply `centering=(0.5, 0.9)` for portrait→landscape crops to
preserve the bottom band, OR re-apply the watermark **after** cropping in
`crop_for_frame()`. **Recommend: re-apply watermark after crop.** The
watermark text + band height calc relies on output dimensions anyway —
applying once at library-store time AND re-applying after each crop is
correct and cheap.

**Open architectural decision for plan:** does `library.crop_for_frame()` 
return watermarked-then-cropped bytes (visible-band may be cut) or 
cropped-then-watermarked bytes (band always present at correct position)?
**Strong recommendation: cropped-then-watermarked.** Means the library JPEG
on disk has the watermark, AND every embedded variant in SLAs gets a fresh
watermark sized to the embedded variant.

---

## 6. Round-trip-diff considerations

### Finding 6.1 — Production-Templates bereits inline-image-bearing — HIGH

```
templates/postkarte-a6-kampagne/build.py: 7 inline_image_data= calls
templates/plakat-a1-hochformat/build.py:  2 inline_image_data= calls
templates/zeitung-a4-grun/build.py:       6 inline_image_data= calls
```

The 3 production templates **already commit inline image bytes verbatim
into build.py via base64 string literals**. Round-trip-diff was achieved
by capturing the original SLA's inline-image base64 once and pasting it
verbatim into build.py. The bytes are identical → SHA matches → diff green.

**Implication for D3 (`<slug>-preview.sla` separate file):** the production
templates' `template.sla` **already contains demo-quality inline images**
(the originals from the design source). Adding library images via
`build_preview()` adds DIFFERENT bytes → SHA differs → round-trip-diff would
break. **D3's separate `template-preview.sla` is the right design.**

### Finding 6.2 — `build_template()` vs `build_preview()` DRY pattern — MEDIUM-HIGH

Per CONTEXT D3:
```python
def build_template():
    """Clean — slot-based, no demo content."""
def build_preview():
    """Same as build_template() PLUS library demo content."""
    doc = build_template()
    # inject library images into empty slots
```

**The cleanest pattern:** `build_template()` returns a `Document` instance
with empty `ImageFrame`s (no `inline_image_data`). `build_preview()` calls
it, then **walks the page's frames and mutates the empty image frames to
inject library bytes**.

```python
def build_preview():
    doc = build_template()
    INJECT_MAP = {
        "P1 Hero": ("portrait_maria", LANDSCAPE_85x60),
        "P2 Themen": ("themen_klimaschutz_solar", LANDSCAPE_85x60),
    }
    for page in doc.pages:
        for frame in page.frames:
            if isinstance(frame, ImageFrame) and frame.anname in INJECT_MAP:
                lib_id, (w, h) = INJECT_MAP[frame.anname]
                cropped = library.crop_for_frame(library.load(lib_id),
                                                 target_w_mm=frame.w_mm,
                                                 target_h_mm=frame.h_mm)
                data, ext = pack_inline_image(cropped, "jpg")
                frame.inline_image_data = data
                frame.inline_image_ext = ext
    return doc
```

**Why mutation, not re-construction:** `build_template()` is the single
source of layout truth. Re-constructing in `build_preview()` would duplicate
the layout code → drift risk. Mutation keeps DRY.

**Risk to determinism:** mutating `ImageFrame` post-construction must not
change `ItemID` order or pageobject ordering. Library checked: `ItemID`
generation happens at `to_pageobject()` emit time (idgen.next()), not
at construction → mutation pre-emit is safe.

### Finding 6.3 — `<slug>-preview.sla` SHA tracking — MEDIUM

Per CONTEXT discretion: "eigenes Feld `previews_for_preview_sla:` oder gar
nicht tracken. Plan entscheidet."

**Recommendation:** **track only `template.sla` SHA in `meta.yml`** (existing
behavior). `template-preview.sla` is **derivable** from `template.sla` +
library state — no need to fingerprint it. If `tools/check_stale_previews.py`
sees `template-preview.sla` exists, it reads it for the gallery PNG render
but tracks `template.sla` SHA.

**Why:** simpler model, fewer SHA fields to keep current, no risk of mismatch
between two SHAs.

### Finding 6.4 — Library-Helper-Modul-Position — HIGH

CONTEXT discretion area. Two candidates:

| Path | Pro | Con |
|------|-----|-----|
| `tools/sla_lib/builder/library.py` | Already a well-formed package; co-located with `pack_inline_image()`, `ImageFrame`; same import root (`from sla_lib.builder import library`) | mixes "library-of-images" concept with "SLA builder primitives" |
| `tools/library.py` | top-level, easy to find | doesn't follow the existing builder-package convention; would need separate import path |

**Recommendation:** **`tools/sla_lib/builder/library.py`**, exported via
`tools/sla_lib/builder/__init__.py`:

```python
from .library import (
    LibraryImage,
    LibraryError,
    load,
    all_images,
    crop_for_frame,
    regenerate,
    check,
)
```

This matches the existing convention (see `__init__.py` lines 51-58 importing
`pack_inline_image` from `.primitives`). Templates import as:
```python
from sla_lib.builder import library, pack_inline_image, ImageFrame
portrait = library.load("portrait_maria")
```

**Rationale:** library helpers MOSTLY operate on the same types as
`pack_inline_image` and `ImageFrame`. Co-location reduces import sprawl and
matches Python convention "modules are namespace, not micro-package."

---

## 7. Aspect-ratio handling alternatives (D7)

Already covered in §1.6: build-time crop, no on-disk variants. Confirmed
recommendation.

**Additional consideration — manifest-level "native aspect" hint:**

```yaml
images:
  portrait_maria:
    path: portraits/maria-beispiel.jpg
    size: "1024x1536"      # native aspect
    composition: portrait  # tag
```

`composition: portrait|landscape|square` tag from D4 helps build.py pick
images that need minimal cropping. E.g. landscape themen-shot for a landscape
slot → crop is just trimming edges, no severe aspect change.

**Recommendation:** add `composition` tag to the schema as a soft hint;
don't enforce. Authoring guideline: "match composition tag to dominant slot
aspect to minimize crop loss."

---

## 8. Generated-image storage best practice

### Finding 8.1 — Plain git, not git-lfs — HIGH

**Current sizes (verified):**
- portrait JPGs (1024×1536, q=80): 131–198 KB each
- landscape JPGs (1536×1024, q=80): 130–309 KB each
- 12 images library = ~3 MB total

**Repo budget:** GitHub recommends warning at 50MB per file, hard limit 100MB,
recommends repo total <1GB. 3 MB across 12 files is **completely
unproblematic** for plain git.

**LFS threshold:** when image count crosses ~30–50 OR total >50 MB, revisit.
For now: **plain git, commit the bytes (D5 confirms).**

**Source:** [GitHub Pages best practices on file size](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)

### Finding 8.2 — Confirm against #11 pattern — HIGH

Issue #11 committed 6 images directly to `templates/<slug>/samples/*.jpg` in
plain git (verified: ls + file inspection). PR #22 merged with these
artifacts in-tree. **Pattern for #13 = same**: commit the bytes plain.

---

## Standard stack additions

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| Pillow | **12.2.0 (existing — recommend pinning)** | center-crop + JPEG re-encode | already installed; **add explicit pin to Dockerfile.claude line 58 block** |
| jsonschema | **4.26.0** (NEW) | manifest schema validation | NOT installed; add to Dockerfile.claude pip3 install line |
| qrcode[pil] | 8.2 (existing) | unchanged from #11 | no change |
| pyzbar | 0.1.9 (existing) | unchanged from #11 | no change |
| PyYAML | 6.0.3 (existing) | manifest parsing | no change |

**Net new deps: jsonschema only.** Pillow already there but should be pinned
to enable byte-deterministic crops.

**Dockerfile.claude diff (proposed):**
```dockerfile
# Existing block at line 58:
RUN pip3 install --break-system-packages --no-cache-dir \
        'qrcode[pil]==8.2' \
        'pyzbar==0.1.9' \
        'pillow==12.2.0' \
        'jsonschema==4.26.0'
```

---

## Risks specific to ecosystem

### R-LIBJPEG — Cross-platform JPEG byte stability — MEDIUM

If devs run `tools/codex_image_gen.py --library` on macOS (system libjpeg) and
CI runs it in the docker image (libjpeg-turbo-Debian), output bytes may
diverge. **Mitigation:** library regen MUST run inside Dockerfile.claude
container (the existing `docker run` pattern). Document this in
`docs/guides/library.md` (new file).

### R-WATERMARK-CROP — Visible band cropped off in landscape→portrait derivations — HIGH

Detailed in Finding 5.3. **Decision needed in plan:** apply watermark
post-crop in `crop_for_frame()` to guarantee band always visible.

### R-DOCKER-PIN — Pillow not currently pinned — MEDIUM

Dockerfile.claude line 57 explicitly says "Do NOT pin Pillow here."
Determinism requires pinning. **Decision needed:** override the existing
"don't pin" comment with a strong justification (byte-deterministic library
regen). Update the comment.

### R-PROMPT-DRIFT — Codex CLI image-gen behavior changes between versions — MEDIUM

#11 used Codex CLI 0.128.0. If a future Codex version changes default
parameters (e.g. quality, style), library regen could produce visibly
different images. **Mitigation:** pin Codex CLI version in Dockerfile.claude
+ note version in each manifest entry as `model:`+`codex_version:` for
reproducibility audit. Defer to plan if scope-creep.

### R-NEW-LOCATIONS-UNVALIDATED — Some D10 prompt locations untested — MEDIUM

Existing #11 tested: vineyard, wind-turbine, Wiener Kaffeehaus, Austrian
schoolyard, Infostand-Stadtplatz. NEW locations needed for #13: solar-on-house
roof, Erwachsenenbildung interior, Handwerk workshop, Radweg, Bürgerversammlung,
Stammtisch-Café. Not all are guaranteed first-shot good. **Budget: 5-attempt
cap per slot per existing pipeline.**

### R-SLA-MERGE-INLINE — Scribus inline-image merge bug — LOW (irrelevant for us)

[Scribus forum thread](https://forums.scribus.net/index.php?topic=4973.0)
notes inline images sometimes disappear when MERGING two SLAs. We don't merge
SLAs; we round-trip and emit. **Not a risk.**

---

## 5 NEW Codex prompts (per CONTEXT D10)

All prompts follow the validated #11 pattern: documentary framing, lens spec,
desaturated greens, no watermarks (added post-process), Austrian context.

### klimaschutz-solar (NEW)

```yaml
themen_klimaschutz_solar:
  path: themen/klimaschutz-solar.jpg
  prompt: |
    Documentary photograph, landscape orientation, of a rooftop photovoltaic
    array on a single-family house in Niederösterreich, late afternoon golden
    hour, mid-distance framing showing roof and partial garden, 35mm lens,
    natural color balance, slightly desaturated greens, warm afternoon palette.
    Clean modern dark-blue solar panels, terracotta tile roof beneath,
    suburban context (no urban high-rises). No people. No vehicles in foreground.
    Authentic and unposed.
    No watermark. No text overlays. No logos or trademarks. No utility-company branding.
  size: "1536x1024"
  tags: [themen, topic:klimaschutz, subtopic:solar, composition:landscape, austrian, outdoor]
  synthetic: true
  license_note: "AI-generated demo image; not a real person/place. Replace with real photography for production use."
  watermark: "Symbolfoto — KI-generiert"
  model: gpt-image-2
  quality: high
```

### bildung-erwachsenenbildung (NEW)

```yaml
themen_bildung_erwachsenenbildung:
  path: themen/bildung-erwachsenenbildung.jpg
  prompt: |
    Documentary photograph, landscape, of an adult-education evening course
    in a small Austrian community center (Volkshochschule-style room), 4-6 adult
    learners aged 30-60 around a workshop table with laptops and notebooks,
    soft warm overhead light from pendant lamps, late evening, 35mm lens,
    natural color balance, slightly desaturated greens. Faces partially turned
    away from camera or showing concentrated expressions, no direct camera gaze.
    Wood-paneled walls, modest community-space character. Authentic and unposed.
    No watermark. No text overlays. No logos or trademarks. No school/uni branding.
  size: "1536x1024"
  tags: [themen, topic:bildung, subtopic:erwachsenenbildung, composition:landscape, austrian, indoor]
  synthetic: true
  license_note: "AI-generated demo image; not a real person/place. Replace with real photography for production use."
  watermark: "Symbolfoto — KI-generiert"
  model: gpt-image-2
  quality: high
```

### wirtschaft-handwerk (NEW)

```yaml
themen_wirtschaft_handwerk:
  path: themen/wirtschaft-handwerk.jpg
  prompt: |
    Documentary photograph, landscape, of a small Austrian Tischlerei
    (carpentry workshop) interior, two craftspeople working at a workbench
    with hand tools and a partially-finished oak piece, sawdust catching the
    light, large warm afternoon window from camera left, 35mm lens, natural
    color balance, slightly desaturated greens, warm wood tones. Faces in
    profile or partial, focused on work, no direct camera gaze. Traditional
    workshop character, modest scale (not industrial). Authentic and unposed.
    No watermark. No text overlays. No logos or trademarks. No brand names on tools.
  size: "1536x1024"
  tags: [themen, topic:wirtschaft, subtopic:handwerk, composition:landscape, austrian, indoor]
  synthetic: true
  license_note: "AI-generated demo image; not a real person/place. Replace with real photography for production use."
  watermark: "Symbolfoto — KI-generiert"
  model: gpt-image-2
  quality: high
```

### verkehr-radweg (NEW)

```yaml
themen_verkehr_radweg:
  path: themen/verkehr-radweg.jpg
  prompt: |
    Documentary photograph, landscape, of a separated cycle path along the
    Donau riverside in Niederösterreich, two cyclists in mid-distance riding
    away from camera, late spring morning, soft diffuse overcast light, mature
    deciduous trees alongside the path, 35mm lens, natural color balance,
    slightly desaturated greens. Mid-life adult cyclists in everyday clothing
    (no racing gear), modest commuter or leisure character. No vehicles. No
    text on signage. Authentic and unposed.
    No watermark. No text overlays. No logos or trademarks. No bicycle-brand visible.
  size: "1536x1024"
  tags: [themen, topic:verkehr, subtopic:radweg, composition:landscape, austrian, outdoor]
  synthetic: true
  license_note: "AI-generated demo image; not a real person/place. Replace with real photography for production use."
  watermark: "Symbolfoto — KI-generiert"
  model: gpt-image-2
  quality: high
```

### buergerversammlung (NEW)

```yaml
kontext_buergerversammlung:
  path: kontext/buergerversammlung.jpg
  prompt: |
    Documentary photograph, landscape, of a Bürgerversammlung in a small
    Austrian Gemeindesaal (town hall room), 12-18 attendees seated in rows of
    folding chairs facing a low stage with speaker's table and a single
    standing speaker (back to camera), late afternoon ambient light through
    side windows, 24mm lens, natural color balance, slightly desaturated
    greens. Mixed-age audience (30s to 70s), engaged-listening posture, no
    raised hands, no party banners or political signage visible. Modest
    community-hall character (wood panels, modest stage curtain). Authentic
    and unposed.
    No watermark. No text overlays. No logos or trademarks. No party flags.
    No campaign posters in background.
  size: "1536x1024"
  tags: [kontext, scene:versammlung, composition:landscape, austrian, indoor]
  synthetic: true
  license_note: "AI-generated demo image; not a real person/place. Replace with real photography for production use."
  watermark: "Symbolfoto — KI-generiert"
  model: gpt-image-2
  quality: high
```

### stammtisch-cafe (NEW)

```yaml
kontext_stammtisch_cafe:
  path: kontext/stammtisch-cafe.jpg
  prompt: |
    Documentary photograph, landscape, of a Stammtisch in a small Austrian
    village Gasthof, round wooden table with 4-5 adults aged 40-65 in casual
    conversation, half-empty coffee cups and a folded newspaper on the table,
    warm interior light from a brass pendant lamp, late afternoon, 35mm lens,
    natural color balance, slightly desaturated greens, warm tones. Faces
    in mid-conversation (in profile or three-quarter), no direct camera gaze,
    no posed group shot character. Modest village-Gasthof character, dark
    wood interior, no chain-restaurant visual cues. Authentic and unposed.
    No watermark. No text overlays. No logos or trademarks. No newspaper
    headlines legible.
  size: "1536x1024"
  tags: [kontext, scene:stammtisch, composition:landscape, austrian, indoor]
  synthetic: true
  license_note: "AI-generated demo image; not a real person/place. Replace with real photography for production use."
  watermark: "Symbolfoto — KI-generiert"
  model: gpt-image-2
  quality: high
```

### Note on count

The user prompt asked for "5 NEW" but listed 6 NEW items above the dash
(klimaschutz-solar, bildung-erwachsenenbildung, wirtschaft-handwerk,
verkehr-radweg, buergerversammlung, stammtisch-cafe). All 6 prompts are
provided above to match CONTEXT D10's requirement of ≥12 library images
total. Plan can drop one if budget tightens.

---

## Existing prompts to migrate VERBATIM (per CONTEXT D8)

These prompts are pulled from the current per-template manifests and reproduced
**unchanged** for the central library. The migration is path-only; bytes
remain identical.

### portrait_maria (from kandidat-falzflyer-din-lang/samples/portrait-cover)

```yaml
portrait_maria:
  path: portraits/maria-beispiel.jpg
  prompt: |
    Documentary photograph of a Central European woman in her mid-40s,
    head-and-shoulders portrait, soft afternoon window light from camera left,
    neutral grey-green out-of-focus background, 50mm lens, shallow depth of field,
    visible pores and natural skin texture, warm color balance, slightly desaturated greens.
    Documentary, unposed, gaze slightly past camera, half-smile.
    No watermark. No text overlays. No logos or trademarks. No glamorization. No heavy retouching.
  size: "1024x1536"
  tags: [portrait, gender:female, age:40s, kandidatin, austrian, setting:office, composition:portrait]
  synthetic: true
  license_note: "AI-generated demo image; not a real person. Replace with real candidate photo for production use."
  watermark: "Symbolfoto — KI-generiert"
  model: gpt-image-2
  quality: high
```

### portrait_stefan (from wahltag-tueranhaenger/samples/portrait-back)

```yaml
portrait_stefan:
  path: portraits/stefan-beispiel.jpg
  prompt: |
    Documentary photograph of a Central European man in his early 50s,
    head-and-shoulders portrait, light salt-and-pepper hair, friendly direct gaze,
    soft late-afternoon window light from camera right, neutral grey-green
    out-of-focus interior background (community space, wood and glass),
    50mm lens, shallow depth of field, visible skin texture, warm color balance,
    slightly desaturated greens. Documentary, unposed, calm half-smile.
    No watermark. No text overlays. No logos or trademarks. No glamorization.
    No heavy retouching.
  size: "1024x1536"
  tags: [portrait, gender:male, age:50s, kandidat, austrian, setting:community, composition:portrait]
  synthetic: true
  license_note: "AI-generated demo image; not a real person. Replace with real candidate photo for production use."
  watermark: "Symbolfoto — KI-generiert"
  model: gpt-image-2
  quality: high
```

### themen_klimaschutz_windrad (from themen-plakat-a3-quer/samples/themen-hero)

```yaml
themen_klimaschutz_windrad:
  path: themen/klimaschutz-windrad.jpg
  prompt: |
    Documentary photograph, landscape orientation, of a Niederösterreich
    wind-turbine on a rolling hill at golden hour, mid-distance framing, 35mm lens,
    natural color balance, slightly desaturated greens, warm afternoon palette.
    Authentic and unposed.
    No watermark. No text overlays. No logos or trademarks.
  size: "1536x1024"
  tags: [themen, topic:klimaschutz, subtopic:windrad, composition:landscape, austrian, outdoor]
  synthetic: true
  license_note: "AI-generated demo image; not a real place. Replace with real local Klimaschutz/Energie photo for production use."
  watermark: "Symbolfoto — KI-generiert"
```

### themen_soziales_gemeindebau (from kandidat-falzflyer/samples/themen-soziales)

**Note:** the existing prompt is for a Wiener Kaffeehaus, NOT a Gemeindebau.
The CONTEXT D8 mapping says `themen-soziales.jpg → soziales-gemeindebau.jpg`
which implies a rename + content shift. **Two options:**

**Option A (preserve bytes):** keep the Kaffeehaus prompt, rename ID to
`themen_soziales_kaffeehaus`. Bytes unchanged. Path renamed.

**Option B (regenerate):** new prompt for Gemeindebau, regenerate. Bytes
change. License-note drops the old reference.

**Recommendation:** **Option A** for migration (zero-byte-change), then
optionally generate `themen_soziales_gemeindebau` as a NEW image in a
follow-up. Plan needs to decide; the issue text says "soziales-gemeindebau"
in D1 example, but D8 says migrate the Kaffeehaus image AS soziales-gemeindebau
which is misleading.

```yaml
themen_soziales_kaffeehaus:    # Option A: preserve bytes, rename ID
  path: themen/soziales-kaffeehaus.jpg
  prompt: |
    Documentary photograph, landscape, of a Wiener Kaffeehaus interior with brass fittings,
    two patrons in conversation at a wooden booth (faces not toward camera), late-afternoon
    window light, 35mm lens, warm tones. Authentic and unposed.
    No watermark. No text overlays. No logos or trademarks.
  size: "1536x1024"
  tags: [themen, topic:soziales, subtopic:kaffeehaus, composition:landscape, austrian, indoor]
  synthetic: true
  license_note: "AI-generated demo image; not a real place. Replace with real photography for production use."
  watermark: "Symbolfoto — KI-generiert"
```

### themen_bildung_volksschule (from kandidat-falzflyer/samples/themen-bildung)

```yaml
themen_bildung_volksschule:
  path: themen/bildung-volksschule.jpg
  prompt: |
    Documentary photograph, landscape, of a small-town Austrian schoolyard with children
    (faces obscured / motion blur), Niederösterreich Dorfstraße in the background,
    overcast diffused daylight, 35mm lens, natural colors. Authentic, unposed.
    No watermark. No text overlays. No logos or trademarks.
  size: "1536x1024"
  tags: [themen, topic:bildung, subtopic:volksschule, composition:landscape, austrian, outdoor]
  synthetic: true
  license_note: "AI-generated demo image; not a real place. Replace with real photography for production use."
  watermark: "Symbolfoto — KI-generiert"
```

### kontext_infostand_szene (from infostand-tent-card/samples/hintergrund-mitmachen)

```yaml
kontext_infostand_szene:
  path: kontext/infostand-szene.jpg
  prompt: |
    Documentary photograph, landscape, of a Grüne Niederösterreich Infostand
    on a small-town square, group of people in mid-conversation around a table
    with leaflets (no logos or party banners visible), bright overcast daylight,
    35mm lens, authentic and candid. Faces partially obscured.
    No watermark. No text overlays. No logos or trademarks.
  size: "1536x1024"
  tags: [kontext, scene:infostand, composition:landscape, austrian, outdoor]
  synthetic: true
  license_note: "AI-generated demo image; not a real place. Replace with real photography for production use."
  watermark: "Symbolfoto — KI-generiert"
```

---

## Sources

### HIGH confidence (Pillow/jsonschema/own codebase)
- [Pillow 12.2.0 ImageOps docs](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html)
- [Pillow 12.2.0 image-file-formats](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)
- [Pillow JpegPresets reference](https://pillow.readthedocs.io/en/stable/reference/JpegPresets.html)
- [jsonschema 4.26.0 PyPI](https://pypi.org/project/jsonschema/) (released 2026-01-07)
- [python-jsonschema readthedocs](https://python-jsonschema.readthedocs.io/)
- Existing per-template manifests at `templates/*/samples/manifest.yml`
- Existing `tools/codex_image_gen.py` and `tools/sla_lib/builder/`
- `Dockerfile.claude` line 56-60 (existing Pillow / qrcode pinning)
- Issue #11 archive `.issues/archive/11-…/research/ecosystem.md`

### MEDIUM confidence (web-verified via official sources)
- [EU AI Act Article 50 official](https://artificialintelligenceact.eu/article/50/)
- [Code of Practice on AI-generated content (EU Commission)](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content)
- [Ashurst on transparency draft](https://www.ashurst.com/en/insights/transparency-of-ai-generated-content-the-eu-first-draft-code-of-practice/)
- [Herbert Smith on Article 50 transparency obligations 2026-03](https://www.hsfkramer.com/notes/ip/2026-03/transparency-obligations-for-ai-generated-content-under-the-eu-ai-act-from-principle-to-practice)
- [GPT Image 2 prompt guide 2026 (PixVerse)](https://pixverse.ai/en/blog/gpt-image-2-review-and-prompt-guide)
- [OpenAI image-gen prompting cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)
- [jdhao on PIL JPEG quality details](https://jdhao.github.io/2019/07/20/pil_jpeg_image_quality/)

### LOW confidence (single source / industry-pattern observation)
- [Untitled UI Figma design system 2026](https://www.untitledui.com/figma) — folder/tag pattern observation, not authoritative on our use case
- [Relume Figma library](https://www.relume.io/figma-library) — same
- [Scribus forum — inline-image format](https://forums.scribus.net/index.php?topic=4973.0) — relevant but not authoritative spec; cross-checked with codebase
- "byte-deterministic JPEG output across Pillow patch versions" — derived from libjpeg-turbo behavior + Pillow 9→12 release-note review, but not explicitly stated in any single doc.

---

## Confidence assessment

| Area | Level | Rationale |
|------|-------|-----------|
| Pillow `ImageOps.fit` correctness | HIGH | official docs, primitive verified |
| JPEG byte-determinism | MEDIUM-HIGH | well-known property of libjpeg-turbo + same Pillow version; cross-version not guaranteed |
| Codex prompt patterns | HIGH | validated in #11 with 0 refusals across 6 prompts |
| Austrian visual cues | MEDIUM-HIGH | most validated in #11; new locations (solar, Radweg) untested |
| Library taxonomy choices | MEDIUM | industry-pattern observation, not authoritative for our domain |
| jsonschema availability | HIGH | verified missing; install path identified |
| EU AI Act compliance | MEDIUM | text well-known; multi-layered marking interpretation evolving |
| Round-trip pattern | HIGH | existing production templates verified via grep + inspection |
| `<slug>-preview.sla` design | HIGH | mutation pattern verified against `ImageFrame` source |
| Library-helper module placement | HIGH | existing builder package convention is clear |
| New Codex prompt set | MEDIUM | follows validated #11 patterns but locations untested; expect 1-2 retries |
