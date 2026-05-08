# Plan: Zentralisierte Demo-Bild-Bibliothek + alle Templates auffüllen

<objective>
Goal: Build a centralized demo-image library (`shared/sample-images/`) accessed via a new
`tools/sla_lib/builder/library.py` module, migrate 7 existing images into it, generate
6 new Codex images, and fill demo content into all 8 templates — including the 3
production templates (postkarte / plakat / zeitung) via a new `template-preview.sla`
artifact that keeps `template.sla` round-trip-stable.

Why: The gallery is currently inconsistent — 5 of 8 templates have demo bilder, 3 don't.
Per-template `samples/` folders also don't scale (5 templates × 6 images × Codex cost
explodes). A library + cross-template reuse fixes both. The library becomes the single
visual source of truth going forward (issue #12 builds on it).

Scope IN: new library module + manifest + migration + 6 new Codex generations +
build.py edits across all 8 templates + production-template `build_template/build_preview`
split + render pipeline patch + Dockerfile / CI dep additions + tests + visual review
+ PR open.

Scope OUT (explicitly deferred per CONTEXT): tag-strict-validation hardening,
saliency-aware crop, library-versioning, real candidate photos, image-search UI,
brand-constraint-DSL coupling (issue #12), C2PA/SynthID watermarking. Don't merge
the PR — orchestrator merges.
</objective>

<context>
Issue: @.issues/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen/ISSUE.md
Decisions: @.issues/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen/CONTEXT.md
Research: @.issues/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen/RESEARCH.md
Codebase research: @.issues/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen/research/codebase.md
Ecosystem research: @.issues/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen/research/ecosystem.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

# ---------------------------------------------------------------------------
# NEW MODULE: tools/sla_lib/builder/library.py
# ---------------------------------------------------------------------------

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

LIBRARY_ROOT = Path(__file__).resolve().parents[3] / "shared" / "sample-images"
MANIFEST_PATH = LIBRARY_ROOT / "manifest.yml"

@dataclass(frozen=True)
class LibraryImage:
    """One image in shared/sample-images/, with metadata.
    Returned by library.load(id). Pass .bytes to pack_inline_image(img.bytes, "jpg")."""
    id: str
    path: Path                 # absolute path on disk
    bytes: bytes               # raw image bytes (read on load)
    meta: dict                 # full manifest entry

class LibraryError(Exception):
    """Raised when a required library ID is missing or the manifest is malformed."""

def load(id: str, *, optional: bool = False) -> Optional[LibraryImage]:
    """Resolve image by ID. Raises LibraryError if missing+required. Returns None
    if optional=True and missing. Bytes are read fresh on every call (library is
    small, ~3MB total)."""

def all_images() -> dict[str, LibraryImage]:
    """All known library entries keyed by ID."""

def find(*, tags: Sequence[str] = (), category: Optional[str] = None) -> list[LibraryImage]:
    """Discovery helper — return library images matching ALL given tags. Permissive."""

def crop_for_frame(
    img: LibraryImage,
    *,
    target_w_mm: float,
    target_h_mm: float,
    dpi: int = 300,
    quality: int = 80,
    apply_watermark: bool = True,
) -> bytes:
    """Center-crop+resize to target frame dimensions. Returns JPEG bytes (q=80,
    optimize=True, subsampling=2, progressive=False).

    CRITICAL — D7 corrected, R-WATERMARK-CROP fix: when apply_watermark=True
    (default), starts from un-watermarked source variant if available
    (`<id>-source.jpg`), crops via PIL.ImageOps.fit(centering=(0.5,0.5),
    method=BICUBIC), THEN re-applies Symbolfoto-watermark. Guarantees the
    band is always visible on the cropped output. EU AI Act Art 50 compliance.

    Determinism: pin Pillow==12.2.0 + libjpeg-turbo container build → byte-identical
    across runs. quality=80, optimize=True, subsampling=2, progressive=False
    pinned explicitly."""

def regenerate(id: str, *, force: bool = False, max_attempts: int = 5) -> bool:
    """Re-run Codex generation for one library entry based on manifest prompt.
    Skips if up-to-date unless force. Wraps tools.codex_image_gen.generate_image
    with manifest integration. Watermark applied automatically post-generation."""

def regenerate_all(*, force: bool = False) -> dict[str, bool]:
    """Regen all library images. Returns id→success map."""

def validate_manifest() -> list[str]:
    """Validate shared/sample-images/manifest.yml against LIBRARY_MANIFEST_SCHEMA
    (jsonschema Draft 2020-12). Returns list of error strings (empty=valid)."""

# Internal:
def _read_manifest() -> dict: ...
def _validate_manifest_entry(id: str, entry: dict) -> None: ...

# JSON Schema embedded as Python dict (per ecosystem 4.3):
LIBRARY_MANIFEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["images"],
    "properties": {
        "images": {
            "type": "object",
            "patternProperties": {
                "^[a-z][a-z0-9_]*$": {
                    "type": "object",
                    "required": ["path", "prompt", "tags", "synthetic"],
                    "properties": {
                        "path": {"type": "string"},
                        "prompt": {"type": "string", "minLength": 20},
                        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        "synthetic": {"type": "boolean"},
                        "license_note": {"type": "string"},
                        "size": {"type": "string", "pattern": "^[0-9]+x[0-9]+$"},
                        "watermark": {"type": "string"},
                        "model": {"type": "string"},
                        "quality": {"type": "string"},
                        "centering": {
                            "type": "array",
                            "items": {"type": "number", "minimum": 0, "maximum": 1},
                            "minItems": 2, "maxItems": 2,
                        },
                    },
                    "additionalProperties": True,  # permissive; D4
                },
            },
            "additionalProperties": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Existing helpers reused verbatim (DO NOT re-implement):
# ---------------------------------------------------------------------------

# tools/sla_lib/builder/primitives.py:750-761
def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """qCompress base64 + ext for ImageFrame.inline_image_data / inline_image_ext."""

# tools/codex_image_gen.py:145-198 — refactor to be importable from library.py
# Currently a top-level function add_demo_watermark(image_path, text=...). After
# refactor: extract a _apply_watermark_to_image(im: PIL.Image, text: str) -> PIL.Image
# core helper, keep add_demo_watermark(image_path, text) as a thin wrapper that
# opens/saves around it. library.crop_for_frame can then call the core helper
# directly on the in-memory cropped Image.
def add_demo_watermark(image_path: Path, text: str = DEFAULT_WATERMARK_TEXT) -> None: ...
def _apply_watermark_to_image(im, text: str): ...  # NEW factored core

# tools/codex_image_gen.py:272-338 (existing)
def generate_image(prompt: str, output_path: Path, size: str) -> int:
    """Codex exec → recover → JPEG re-encode → watermark. CRITICAL: must call
    subprocess with stdin=subprocess.DEVNULL — codex 0.128.0 hangs without it
    (carry-over from #11)."""

# ---------------------------------------------------------------------------
# Existing ImageFrame contract (used in build.py):
# tools/sla_lib/builder/primitives.py — supports inline_image_data=None for empty slots
# ---------------------------------------------------------------------------
ImageFrame(
    x_mm: float, y_mm: float, w_mm: float, h_mm: float,
    inline_image_data: Optional[str] = None,  # qCompress b64 from pack_inline_image
    inline_image_ext: Optional[str] = None,   # "jpg" / "png"
    scale_type: int = 0, ratio: float = 1, layer: int = LAYER_BILDER,
    anname: str = "",
)

# ---------------------------------------------------------------------------
# Production-template build.py shape (D3, RESEARCH §"<interfaces> for the build.py split"):
# ---------------------------------------------------------------------------
def build_template() -> Document:
    """Clean — slot-based, no demo content. End users open this. Round-trip-stable."""

def build_preview() -> Document:
    """Gallery preview — clean template + library demo content injected via mutation
    of empty ImageFrame.inline_image_data (per ecosystem Finding 6.2 — DRY mutation,
    no layout duplication)."""
    doc = build_template()
    INJECT_MAP = {"<anname>": ("<library_id>", w_mm, h_mm), ...}
    for page in doc.pages:
        for frame in page.frames:
            if isinstance(frame, ImageFrame) and frame.anname in INJECT_MAP:
                lib_id, w, h = INJECT_MAP[frame.anname]
                cropped = library.crop_for_frame(library.load(lib_id), target_w_mm=w, target_h_mm=h)
                data, ext = pack_inline_image(cropped, "jpg")
                frame.inline_image_data = data
                frame.inline_image_ext = ext
    return doc

if __name__ == "__main__":
    build_template().save(HERE / "template.sla")
    build_preview().save(HERE / "template-preview.sla")

# ---------------------------------------------------------------------------
# Render pipeline patch (tools/render_pipeline.py, ~line 458):
# ---------------------------------------------------------------------------
def _select_render_source(template_dir: Path) -> Path:
    """Prefer template-preview.sla (gallery render) over template.sla."""
    preview = template_dir / "template-preview.sla"
    if preview.exists():
        return preview
    return template_dir / "template.sla"

# In _orchestrate_single (~line 458), replace:
#   sla_path = tdir / "template.sla"
#   render_sla_to_pdf(sla_path, preview_pdf)
# with:
#   render_source = _select_render_source(tdir)
#   render_sla_to_pdf(render_source, preview_pdf)
#
# SHA pin still tracks template.sla (the clean one), NOT template-preview.sla.
# tools/check_stale_previews.py and tools/sla_diff.py: ZERO changes — they
# already target template.sla.
</interfaces>

Migration map (corrected per RESEARCH §"Migration Map" — D8 fix):

| Source path | New path | Library ID |
|---|---|---|
| `templates/kandidat-falzflyer-din-lang/samples/portrait-cover.jpg` | `shared/sample-images/portraits/maria-beispiel.jpg` | `portrait_maria` |
| `templates/wahltag-tueranhaenger/samples/portrait-back.jpg` | `shared/sample-images/portraits/stefan-beispiel.jpg` | `portrait_stefan` |
| `templates/kandidat-falzflyer-din-lang/samples/themen-klimaschutz.jpg` | `shared/sample-images/themen/klimaschutz-solar.jpg` | `themen_klimaschutz_solar` |
| `templates/kandidat-falzflyer-din-lang/samples/themen-soziales.jpg` | `shared/sample-images/themen/soziales-kaffeehaus.jpg` | `themen_soziales_kaffeehaus` *(D8 corrected — bytes are kaffeehaus, not gemeindebau)* |
| `templates/kandidat-falzflyer-din-lang/samples/themen-bildung.jpg` | `shared/sample-images/themen/bildung-volksschule.jpg` | `themen_bildung_volksschule` |
| `templates/themen-plakat-a3-quer/samples/themen-hero.jpg` | `shared/sample-images/themen/klimaschutz-windrad.jpg` | `themen_klimaschutz_windrad` |
| `templates/infostand-tent-card-a5-quer/samples/hintergrund-mitmachen.jpg` | `shared/sample-images/kontext/infostand-szene.jpg` | `kontext_infostand_szene` |

Six new images to generate (prompts verbatim from `research/ecosystem.md` §"5 NEW Codex prompts"):
`themen_soziales_gemeindebau`, `themen_bildung_erwachsenenbildung`, `themen_wirtschaft_handwerk`,
`themen_verkehr_radweg`, `kontext_buergerversammlung`, `kontext_stammtisch_cafe`.

QR codes stay template-specific (D9) — no migration. Each template's `samples/qr-*.png` and the `qr_codes:` block in its manifest stays put.

Per-template slot inventory (verified in `research/codebase.md` §2):

| Template | Slots to fill | Source IDs |
|---|---|---|
| postkarte-a6-kampagne (production) | 1 hero (line 86, 84×127mm portrait) | `themen_klimaschutz_solar` cropped to 84×127mm portrait |
| plakat-a1-hochformat (production) | 1 hero (line 151, 594×414mm landscape) | `themen_klimaschutz_solar` (large landscape) |
| zeitung-a4-grun (production) | ~10 demo slots conservative subset (cover hero + 4 themen-thumbnails + 2 photo-spread + 2 portraits + 1 bottom strip + 1 page-13 hero) | cover=`themen_klimaschutz_windrad`, p1=`themen_soziales_gemeindebau`, p2=`themen_bildung_volksschule`, p3=`themen_wirtschaft_handwerk`, p4-spread=`kontext_buergerversammlung`, p5=`themen_verkehr_radweg`, p7-portrait=`portrait_maria`, p9-spread=`themen_klimaschutz_solar`, p10-portrait=`portrait_stefan`, p11-bottom=`kontext_stammtisch_cafe`, p13=`kontext_infostand_szene` (skip background `fill='Dunkelgrün'` polygon-frames and small icons per codebase.md §2.3) |
| themen-plakat-a3-quer (new) | 1 themen-hero (180×60mm) | `themen_klimaschutz_windrad` (migrated) |
| wahlaufruf-postkarte-a6-quer (new) | 0 image slots | n/a |
| wahltag-tueranhaenger (new) | 1 portrait (65×85mm) | `portrait_stefan` (migrated) |
| infostand-tent-card-a5-quer (new) | 1 hintergrund (44×33mm) | `kontext_infostand_szene` (migrated) |
| kandidat-falzflyer-din-lang (new) | 1 portrait (87×105mm) + 3 themen (87×24mm) | `portrait_maria`, `themen_klimaschutz_solar`, `themen_soziales_kaffeehaus`, `themen_bildung_volksschule` (all migrated) |

Key files (read these before editing):

@tools/sla_lib/builder/primitives.py — `pack_inline_image` at lines 750-761, `ImageFrame` lines ~770-840
@tools/sla_lib/builder/__init__.py — module exports; add `library` import here
@tools/codex_image_gen.py — `generate_image`, `add_demo_watermark`, manifest parser; refactor watermark for in-memory use, add `--library` flag
@tools/render_pipeline.py — `_orchestrate_single` ~line 447-486 is the patch site; add `_select_render_source` helper
@tools/check_stale_previews.py — UNCHANGED but verify still hashes `template.sla`
@tools/sla_diff.py — UNCHANGED
@Dockerfile.claude — pip install block ~line 53-58; pin Pillow + add jsonschema
@.github/workflows/pages.yml — pip install line ~50; add jsonschema
@templates/postkarte-a6-kampagne/build.py — production, refactor into build_template/build_preview
@templates/plakat-a1-hochformat/build.py — production, same
@templates/zeitung-a4-grun/build.py — production, same (largest)
@templates/themen-plakat-a3-quer/build.py — new template, switch to library.load
@templates/wahltag-tueranhaenger/build.py — new template, same
@templates/infostand-tent-card-a5-quer/build.py — new template, same
@templates/kandidat-falzflyer-din-lang/build.py — new template, biggest migration
@templates/wahlaufruf-postkarte-a6-quer/build.py — new, no image slots; verify untouched
</context>

<commit_format>
Format: conventional with issue prefix (per `.issues/config.yaml`)
Example: `13: feat(library): add image library module + JSON schema validation`
Pattern: `13: {type}({scope}): {description}`
Types: feat, fix, test, refactor, docs, chore. NEVER include "claude" in commit messages or code (memory: `feedback_no_claude_attribution`).
</commit_format>

<tasks>

<task type="auto">
  <name>Task 1: Pin Pillow + add jsonschema in Dockerfile and CI workflow</name>
  <files>Dockerfile.claude, .github/workflows/pages.yml</files>
  <action>
  Two surgical edits — foundational for the library module.

  1. `Dockerfile.claude`: locate the `pip3 install --break-system-packages --no-cache-dir`
     block (~line 53-58, currently lists `qrcode[pil]==8.2`, `pyzbar==0.1.9`). Add explicit
     pins so the block reads:
     ```
     RUN pip3 install --break-system-packages --no-cache-dir \
             'qrcode[pil]==8.2' \
             'pyzbar==0.1.9' \
             'pillow==12.2.0' \
             'jsonschema==4.26.0'
     ```
     There is currently a comment near this block saying "Do NOT pin Pillow here." —
     REPLACE that comment with: `# Pillow pinned to 12.2.0 for byte-deterministic
     library regen (issue #13 — see RESEARCH.md R-DOCKER-PIN).`

  2. `.github/workflows/pages.yml`: locate the pip install line (~line 50, currently
     `pip install Pillow==12.2.0 qrcode[pil]==8.2 pyzbar==0.1.9` per RESEARCH §6).
     Add `jsonschema==4.26.0` so it reads `pip install Pillow==12.2.0 qrcode[pil]==8.2
     pyzbar==0.1.9 jsonschema==4.26.0`. Keep the leading `pip install` shape as-is.

  Do NOT change anything else in pages.yml — RESEARCH confirmed CI workflow needs zero
  other changes for the preview-SLA pattern (production-template-rebuild already disabled
  in #11; brand validator wildcard already accepts both SLAs).
  </action>
  <verify>
    <automated>
    docker build -f Dockerfile.claude -t austender-claude:13 . > /tmp/dockerbuild.log 2>&1 && \
    docker run --rm austender-claude:13 python3 -c "import jsonschema, PIL; print('jsonschema', jsonschema.__version__); print('Pillow', PIL.__version__)" | tee /tmp/depcheck.log && \
    grep -q "jsonschema 4.26.0" /tmp/depcheck.log && grep -q "Pillow 12.2.0" /tmp/depcheck.log
    </automated>
  </verify>
  <done>
  - Dockerfile.claude installs `pillow==12.2.0` and `jsonschema==4.26.0` (verified by docker build)
  - The "Do NOT pin Pillow" comment is replaced with the pinning rationale
  - .github/workflows/pages.yml pip install line includes `jsonschema==4.26.0`
  - `docker run austender-claude:13 python3 -c "import jsonschema, PIL"` succeeds
  </done>
  <commit>13: chore(deps): pin Pillow==12.2.0 and add jsonschema==4.26.0 for library validation</commit>
</task>

<task type="auto">
  <name>Task 2: Refactor add_demo_watermark to be importable from library module</name>
  <files>tools/codex_image_gen.py, tools/sla_lib/tests/test_codex_image_gen.py</files>
  <action>
  Refactor `tools/codex_image_gen.py::add_demo_watermark` (lines 145-198) so its core
  watermark-drawing logic can run on an in-memory PIL.Image (not just on a file path).

  Concrete shape:
  ```python
  def _apply_watermark_to_image(im, text: str = DEFAULT_WATERMARK_TEXT) -> "PIL.Image.Image":
      """Stamp the bottom 4% Symbolfoto-band onto a PIL.Image. Returns a new Image
      (does not mutate input). Reusable from library.crop_for_frame()."""
      # Lift the body of add_demo_watermark here; band geometry, font load,
      # text drawing — all on the in-memory Image object.
      ...
      return new_im

  def add_demo_watermark(image_path: Path, text: str = DEFAULT_WATERMARK_TEXT) -> None:
      """File-path wrapper: open → _apply_watermark_to_image → save JPEG q=80 optimize=True."""
      with Image.open(image_path) as im:
          watermarked = _apply_watermark_to_image(im, text=text)
      watermarked.save(image_path, format="JPEG", quality=80, optimize=True,
                        subsampling=2, progressive=False)
  ```

  Pin save kwargs explicitly (subsampling=2, progressive=False) — required for
  byte-determinism per RESEARCH §1.4. Existing call sites of `add_demo_watermark()`
  keep working unchanged (the wrapper's signature is preserved).

  CRITICAL — codex stdin DEVNULL: do NOT touch `generate_image` (lines 272-338) or
  the subprocess invocation that uses `stdin=subprocess.DEVNULL`. That fix from #11
  must be preserved as-is.

  Update existing tests in `tools/sla_lib/tests/test_codex_image_gen.py` if any
  test relies on the old internal structure of `add_demo_watermark`. Add one new
  test asserting `_apply_watermark_to_image(im)` returns a new image with the band
  drawn (check pixel at bottom-center is dark, pixel at top-center is original color).
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    python3 -m pytest tools/sla_lib/tests/test_codex_image_gen.py -x -v
    </automated>
  </verify>
  <done>
  - `_apply_watermark_to_image(im, text)` is a module-level function in tools/codex_image_gen.py
  - `add_demo_watermark(image_path, text)` retains its old signature, internally delegates to the new helper
  - Save kwargs `subsampling=2, progressive=False` pinned in the file-path wrapper
  - New test verifies the helper draws the bottom band on an in-memory image
  - Existing codex_image_gen tests pass
  - generate_image's stdin=DEVNULL invocation untouched
  </done>
  <commit>13: refactor(codex_image_gen): extract _apply_watermark_to_image core for library reuse</commit>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Implement library module + JSON schema + tests (foundation)</name>
  <files>tools/sla_lib/builder/library.py, tools/sla_lib/builder/__init__.py, tools/sla_lib/tests/test_library.py</files>
  <behavior>
  - load("missing_id") with optional=False → raises LibraryError
  - load("missing_id", optional=True) → returns None
  - load("portrait_maria") → returns LibraryImage with .id, .path (absolute), .bytes (>0), .meta dict
  - all_images() → dict keyed by id, contains every manifest entry
  - find(tags=["portrait"]) → returns only portrait-tagged images, sorted by id
  - find(category="themen") → returns only themen-folder images
  - crop_for_frame(img, target_w_mm=87, target_h_mm=24) → JPEG bytes; called twice with same args yields byte-identical output (determinism)
  - crop_for_frame(landscape_source, target_w_mm=87, target_h_mm=105) (portrait crop): output has visible Symbolfoto-watermark band at bottom (regression test for R-WATERMARK-CROP)
  - crop_for_frame(portrait_source, target_w_mm=200, target_h_mm=60) (landscape crop from portrait): output has visible Symbolfoto-watermark band at bottom — band re-applied POST-crop, NOT cropped off
  - validate_manifest() on a valid manifest → returns []
  - validate_manifest() on a manifest missing required field "prompt" in an entry → returns non-empty error list
  - regenerate(id) (mocked codex generate_image) → returns True; calls into generate_image with the right prompt+output_path
  </behavior>
  <action>
  RED: write `tools/sla_lib/tests/test_library.py` covering every behavior above.
  Use a tiny fixture manifest under `tools/sla_lib/tests/fixtures/library/` with 2-3
  small generated test JPGs (you can synthesize 200×300 and 300×200 solid-color JPGs
  on the fly in the test setup — no need to commit fixtures). Mock
  `tools.codex_image_gen.generate_image` for the `regenerate` test.

  GREEN: implement `tools/sla_lib/builder/library.py` per `<interfaces>` exactly:
  - `LibraryImage` frozen dataclass
  - `LibraryError` exception
  - `LIBRARY_MANIFEST_SCHEMA` Python dict (full Draft 2020-12 schema from interfaces)
  - `_read_manifest()` — reads `LIBRARY_ROOT / "manifest.yml"` via `yaml.safe_load`,
    caches at module-load time (module-level dict cache; idempotent)
  - `_validate_manifest_entry(id, entry)` — soft validation, raises LibraryError
    for missing required fields
  - `load(id, *, optional=False)` — looks up entry, reads bytes from
    `LIBRARY_ROOT / entry["path"]`, returns LibraryImage or None
  - `all_images()` — iterates manifest, returns dict keyed by id
  - `find(*, tags=(), category=None)` — filters all_images by ALL-tags-match and
    category (category derived from the path's first directory segment:
    `portraits` → "portraits", `themen/foo.jpg` → "themen", etc.)
  - `crop_for_frame(img, *, target_w_mm, target_h_mm, dpi=300, quality=80, apply_watermark=True)`:
    1. Compute `target_w_px = round(target_w_mm * dpi / 25.4)`, same for h
    2. Open `img.bytes` via `Image.open(BytesIO(img.bytes))`, convert to RGB
    3. Watermark-after-crop fix (R-WATERMARK-CROP): If `apply_watermark=True`,
       check whether a `<id>-source.jpg` exists at
       `LIBRARY_ROOT / entry["path"].replace(".jpg", "-source.jpg")`. If yes, use
       it as the source (un-watermarked). If no, use the watermarked library
       image directly (fresh stamp will overlay; document in a code comment).
    4. `fitted = ImageOps.fit(rgb, (target_w_px, target_h_px), method=Image.Resampling.BICUBIC, centering=(0.5, 0.5))`
    5. If `apply_watermark=True`: `fitted = _apply_watermark_to_image(fitted, text=img.meta.get("watermark", DEFAULT_WATERMARK_TEXT))` — imports from `tools.codex_image_gen`
    6. Save to `BytesIO` with `format="JPEG", quality=80, optimize=True, subsampling=2, progressive=False`
    7. Return bytes
  - `regenerate(id, *, force=False, max_attempts=5)` — read manifest entry, call
    `tools.codex_image_gen.generate_image(prompt, output_path, size)` with
    output_path absolute (`LIBRARY_ROOT / entry["path"]`). Watermark is applied
    inside generate_image. Return True/False on success/failure.
  - `regenerate_all(*, force=False)` — iterate all_images(), call regenerate per id
  - `validate_manifest()` — `import jsonschema`; instantiate
    `jsonschema.Draft202012Validator(LIBRARY_MANIFEST_SCHEMA)`; collect errors
    via `validator.iter_errors(_read_manifest())`; return list of message strings.

  REFACTOR: clean up imports, ensure no circular deps (`library.py` imports `Path`,
  `yaml`, `dataclasses`, `PIL`, `jsonschema`, and lazily imports
  `tools.codex_image_gen` inside `regenerate` to avoid cycles).

  Update `tools/sla_lib/builder/__init__.py`: add `from . import library` after the
  existing `from . import blocks` (per codebase research §8.9). Do NOT re-export
  individual symbols at the top level — keep `library.load(...)` namespace.

  IMPORTANT: this task does NOT yet create the manifest.yml or any library JPGs.
  Tests use a fixture manifest under `tools/sla_lib/tests/fixtures/library/` with
  `manifest.yml` + tiny synthesized JPGs. Use
  `monkeypatch.setattr(library, "LIBRARY_ROOT", fixture_root)` +
  `monkeypatch.setattr(library, "MANIFEST_PATH", fixture_root / "manifest.yml")`
  (and clear the module-level cache) to point library.py at the fixture.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    python3 -m pytest tools/sla_lib/tests/test_library.py -x -v
    </automated>
  </verify>
  <done>
  - `tools/sla_lib/builder/library.py` implements every public symbol in `<interfaces>` exactly
  - `LIBRARY_MANIFEST_SCHEMA` Draft 2020-12 dict embedded in module
  - `__init__.py` exposes `library` as `sla_lib.builder.library`
  - All tests in `test_library.py` pass — including watermark-after-crop regression test for both portrait→landscape AND landscape→portrait
  - Determinism test: two consecutive `crop_for_frame` calls with same args produce byte-identical output
  - validate_manifest catches missing-required-field error
  - No circular imports
  </done>
  <commit>13: feat(library): add image library module with JSON schema + watermark-after-crop</commit>
</task>

<task type="auto">
  <name>Task 4: Add --library flag to codex_image_gen.py + library-mode manifest parser</name>
  <files>tools/codex_image_gen.py, tools/sla_lib/tests/test_codex_image_gen.py</files>
  <action>
  Extend `tools/codex_image_gen.py` with a library-aware mode (CONTEXT D6).

  1. Add `parse_library_manifest(path: Path) -> dict[str, dict]` — reads the
     master library manifest (where `images:` is a dict keyed by ID), returns
     `dict[id] -> entry`. **Different from the existing per-template
     `parse_manifest` which expects `images: [list]`.** Per codebase research
     §8.7 — implement as a separate function, not a generalisation.

  2. Add `regen_library(manifest_path: Path, *, ids: Optional[list[str]] = None,
     force: bool = False, max_attempts: int = 5) -> int`:
     - Reads manifest via `parse_library_manifest`
     - For each ID (or all if ids=None): resolves output_path =
       `manifest_path.parent / entry["path"]`
     - Skips if `image_needs_regen` says skip and not force (mtime check vs
       manifest)
     - Calls `generate_image(entry["prompt"], output_path, entry["size"])`
       (which already invokes codex with `stdin=subprocess.DEVNULL` and applies
       watermark post-generation — preserved unchanged)
     - Tracks per-image attempt cap; returns 0 on full success, non-zero on any
       failure

  3. Extend `main(argv)` (lines 378-511) with new flags:
     - `--library <manifest_path>` — switches to library mode (calls regen_library)
     - `--single <id>` — when in library mode, only regenerate that ID
     - `--force` flag already exists and is reused (skip mtime check)
     - When `--library` is given, the positional `<target>` argument is OPTIONAL
       (manifest path is the input)
     - When `--library` is NOT given, existing per-template behavior is unchanged

  4. Add tests in `test_codex_image_gen.py`:
     - `parse_library_manifest` reads valid library manifest correctly
     - `regen_library` (with `generate_image` mocked) iterates entries
     - `regen_library --single` only regenerates the requested ID
     - `--force` bypasses mtime skip

  Do NOT change the existing per-template `parse_manifest` or main()'s
  per-template path. Library mode is additive.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    python3 -m pytest tools/sla_lib/tests/test_codex_image_gen.py -x -v && \
    python3 tools/codex_image_gen.py --library /tmp/nonexistent-manifest.yml 2>&1 | grep -q "not found\|missing\|No such file"
    </automated>
  </verify>
  <done>
  - `parse_library_manifest()` and `regen_library()` exist as module functions
  - `python3 tools/codex_image_gen.py --library <path> [--single <id>] [--force]` CLI works
  - generate_image's stdin=DEVNULL preserved
  - Old per-template CLI mode unchanged
  - New tests pass
  </done>
  <commit>13: feat(codex_image_gen): add --library mode for centralized image regen</commit>
</task>

<task type="auto">
  <name>Task 5: Migrate 7 existing images via git mv + assemble shared/sample-images/manifest.yml</name>
  <files>shared/sample-images/manifest.yml, shared/sample-images/portraits/maria-beispiel.jpg, shared/sample-images/portraits/stefan-beispiel.jpg, shared/sample-images/themen/klimaschutz-solar.jpg, shared/sample-images/themen/soziales-kaffeehaus.jpg, shared/sample-images/themen/bildung-volksschule.jpg, shared/sample-images/themen/klimaschutz-windrad.jpg, shared/sample-images/kontext/infostand-szene.jpg, templates/kandidat-falzflyer-din-lang/samples/manifest.yml, templates/wahltag-tueranhaenger/samples/manifest.yml, templates/themen-plakat-a3-quer/samples/manifest.yml, templates/infostand-tent-card-a5-quer/samples/manifest.yml</files>
  <action>
  Pure file moves + manifest assembly. No code changes in this task. Round-trip
  diff on the 5 new templates (which currently use these images via
  `(HERE / "samples" / "x.jpg").exists()`) MUST stay byte-identical because the
  bytes themselves don't change — only their path. Build.py edits to point at
  the library happen in later tasks.

  1. Create the directory layout:
     ```
     shared/sample-images/
     ├── manifest.yml
     ├── portraits/
     ├── themen/
     ├── kontext/
     └── qr/        # empty per D9; QRs stay template-specific
     ```

  2. `git mv` 7 files per the migration map in `<context>` above. Use `git mv`
     (not cp+rm) to preserve blame. Concrete commands:
     ```
     mkdir -p shared/sample-images/{portraits,themen,kontext,qr}
     git mv templates/kandidat-falzflyer-din-lang/samples/portrait-cover.jpg \
            shared/sample-images/portraits/maria-beispiel.jpg
     git mv templates/wahltag-tueranhaenger/samples/portrait-back.jpg \
            shared/sample-images/portraits/stefan-beispiel.jpg
     git mv templates/kandidat-falzflyer-din-lang/samples/themen-klimaschutz.jpg \
            shared/sample-images/themen/klimaschutz-solar.jpg
     git mv templates/kandidat-falzflyer-din-lang/samples/themen-soziales.jpg \
            shared/sample-images/themen/soziales-kaffeehaus.jpg   # D8 fix
     git mv templates/kandidat-falzflyer-din-lang/samples/themen-bildung.jpg \
            shared/sample-images/themen/bildung-volksschule.jpg
     git mv templates/themen-plakat-a3-quer/samples/themen-hero.jpg \
            shared/sample-images/themen/klimaschutz-windrad.jpg
     git mv templates/infostand-tent-card-a5-quer/samples/hintergrund-mitmachen.jpg \
            shared/sample-images/kontext/infostand-szene.jpg
     ```

  3. Build `shared/sample-images/manifest.yml` with all 7 entries. Copy the
     prompts VERBATIM from `research/ecosystem.md` §"Existing prompts to
     migrate VERBATIM (per CONTEXT D8)" — for each of: portrait_maria,
     portrait_stefan, themen_klimaschutz_windrad, themen_soziales_kaffeehaus,
     themen_bildung_volksschule, kontext_infostand_szene. For
     themen_klimaschutz_solar, the existing bytes are the falzflyer
     `themen-klimaschutz.jpg`. The original prompt for that file is in
     `templates/kandidat-falzflyer-din-lang/samples/manifest.yml` — copy the
     exact prompt verbatim. (If the original prompt is missing or unclear, use
     the new "klimaschutz-solar" prompt from `research/ecosystem.md` §"5 NEW
     Codex prompts" with a comment in the manifest:
     `# original prompt for migrated bytes; see research/ecosystem.md`.)

     Schema per CONTEXT D1 + ecosystem 4.3 — every entry MUST include:
     `path`, `prompt`, `tags` (≥1), `synthetic: true`, `license_note`,
     `size` (`WxH` format), `watermark`. Optional: `model`, `quality`,
     `centering`.

  4. Update each affected template's `samples/manifest.yml` to remove the
     `images:` section and replace with a `uses_from_library:` block listing
     IDs used (per codebase research §3 example). `qr_codes:` stays unchanged.
     Affected templates:
     - `templates/kandidat-falzflyer-din-lang/samples/manifest.yml`:
       remove `images:` (4 entries: portrait-cover, themen-klimaschutz, themen-soziales,
       themen-bildung); add `uses_from_library: - id: portrait_maria` etc.
     - `templates/wahltag-tueranhaenger/samples/manifest.yml`: remove
       `images:` (1 entry); add `uses_from_library: - id: portrait_stefan`
     - `templates/themen-plakat-a3-quer/samples/manifest.yml`: remove
       `images:` (1 entry); add `uses_from_library: - id: themen_klimaschutz_windrad`
     - `templates/infostand-tent-card-a5-quer/samples/manifest.yml`: remove
       `images:` (1 entry); add `uses_from_library: - id: kontext_infostand_szene`
     - `templates/wahlaufruf-postkarte-a6-quer/samples/manifest.yml`: had no
       `images:` — leave untouched
     - The 3 production templates have no `samples/manifest.yml` — they create
       it in later tasks if needed (Task 9-11 will add `uses_from_library:` to
       their own samples dirs).

  5. Run `python3 -c "from sla_lib.builder import library; errs = library.validate_manifest(); print('OK' if not errs else errs); assert not errs"` to confirm the new master manifest validates.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    test -f shared/sample-images/manifest.yml && \
    test -f shared/sample-images/portraits/maria-beispiel.jpg && \
    test -f shared/sample-images/portraits/stefan-beispiel.jpg && \
    test -f shared/sample-images/themen/klimaschutz-solar.jpg && \
    test -f shared/sample-images/themen/soziales-kaffeehaus.jpg && \
    test -f shared/sample-images/themen/bildung-volksschule.jpg && \
    test -f shared/sample-images/themen/klimaschutz-windrad.jpg && \
    test -f shared/sample-images/kontext/infostand-szene.jpg && \
    PYTHONPATH=tools python3 -c "from sla_lib.builder import library; errs = library.validate_manifest(); assert not errs, errs; print('OK')" && \
    git log --diff-filter=R --name-only -1 -- "shared/sample-images/" | grep -q "renamed\|->" || true
    </automated>
  </verify>
  <done>
  - 7 files moved via `git mv` (verified by `git status` showing renames, not adds+deletes)
  - `shared/sample-images/manifest.yml` exists with 7 entries, each containing all required fields
  - `library.validate_manifest()` returns empty error list
  - Per-template `samples/manifest.yml` files have `images:` removed and `uses_from_library:` added; `qr_codes:` unchanged
  - `wahlaufruf-postkarte-a6-quer/samples/manifest.yml` untouched
  - Build.py files NOT yet edited (next tasks)
  </done>
  <commit>13: feat(library): migrate 7 existing demo images to shared/sample-images/ + master manifest</commit>
</task>

<task type="auto">
  <name>Task 6: Generate 6 new Codex images for library</name>
  <files>shared/sample-images/manifest.yml, shared/sample-images/themen/soziales-gemeindebau.jpg, shared/sample-images/themen/bildung-erwachsenenbildung.jpg, shared/sample-images/themen/wirtschaft-handwerk.jpg, shared/sample-images/themen/verkehr-radweg.jpg, shared/sample-images/kontext/buergerversammlung.jpg, shared/sample-images/kontext/stammtisch-cafe.jpg</files>
  <action>
  Add 6 new Codex-generated images to the library. Run inside the Docker
  container (R-LIBJPEG — JPEG bytes diverge across libjpeg versions; container
  pin enforces determinism).

  1. Append 6 new entries to `shared/sample-images/manifest.yml`. Use the EXACT
     prompts from `research/ecosystem.md` §"5 NEW Codex prompts" (which
     actually contains 6 NEW + 1 redundant — use them all 6 NEW):
     - `themen_soziales_gemeindebau` (kept distinct from kaffeehaus)
     - `themen_bildung_erwachsenenbildung`
     - `themen_wirtschaft_handwerk`
     - `themen_verkehr_radweg`
     - `kontext_buergerversammlung`
     - `kontext_stammtisch_cafe`

     Each entry MUST include the FULL prompt block (including
     "No watermark. No text overlays. No logos or trademarks." trailer),
     `path`, `tags`, `synthetic: true`, `license_note`, `size: "1536x1024"`,
     `watermark: "Symbolfoto — KI-generiert"`, `model: gpt-image-2`,
     `quality: high`. Copy verbatim from ecosystem.md.

  2. Run library regen:
     ```
     python3 tools/codex_image_gen.py --library shared/sample-images/manifest.yml
     ```
     Expected: ~2:10 per generation × 6 = ~13 minutes minimum. Allow up to 30
     minutes with retries (max_attempts=5 default). Codex must run with
     `stdin=subprocess.DEVNULL` (preserved from #11; do NOT touch).

  3. Each generated JPEG should be:
     - 1536×1024 (landscape) or as specified in `size:`
     - JPEG q=80, optimize=True
     - Bottom 4% Symbolfoto-band watermarked (verify visually with `file` and
       Pillow inspection)

  4. After all 6 images generate successfully, verify:
     ```
     ls -la shared/sample-images/themen/{soziales-gemeindebau,bildung-erwachsenenbildung,wirtschaft-handwerk,verkehr-radweg}.jpg
     ls -la shared/sample-images/kontext/{buergerversammlung,stammtisch-cafe}.jpg
     PYTHONPATH=tools python3 -c "
     from sla_lib.builder import library
     for img_id in ['themen_soziales_gemeindebau','themen_bildung_erwachsenenbildung',
                    'themen_wirtschaft_handwerk','themen_verkehr_radweg',
                    'kontext_buergerversammlung','kontext_stammtisch_cafe']:
         img = library.load(img_id)
         assert len(img.bytes) > 50000, f'{img_id} too small ({len(img.bytes)} bytes)'
         print(f'{img_id}: {len(img.bytes)} bytes OK')
     errs = library.validate_manifest()
     assert not errs, errs
     "
     ```

  5. If any image fails generation after 5 attempts, document the failure in
     EXECUTION.md and either: (a) skip that image and remove its manifest entry
     for now, or (b) try a slightly tweaked prompt (still aligned with
     CONTEXT D10 description). Don't ship a manifest entry without a
     corresponding file.

  6. After all 13 images (7 migrated + 6 new) are committed, the library has:
     2 portraits + 8 themen (klimaschutz_solar, klimaschutz_windrad,
     soziales_kaffeehaus, soziales_gemeindebau, bildung_volksschule,
     bildung_erwachsenenbildung, wirtschaft_handwerk, verkehr_radweg) +
     3 kontext (infostand_szene, buergerversammlung, stammtisch_cafe) = 13.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    PYTHONPATH=tools python3 -c "
    from sla_lib.builder import library
    imgs = library.all_images()
    assert len(imgs) >= 13, f'expected >=13 library images, got {len(imgs)}'
    for img_id in ['themen_soziales_gemeindebau','themen_bildung_erwachsenenbildung',
                   'themen_wirtschaft_handwerk','themen_verkehr_radweg',
                   'kontext_buergerversammlung','kontext_stammtisch_cafe']:
        img = library.load(img_id)
        assert len(img.bytes) > 50000, f'{img_id} too small'
    errs = library.validate_manifest()
    assert not errs, errs
    print('library OK:', len(imgs), 'images')
    "
    </automated>
  </verify>
  <done>
  - 6 new JPEG files exist under `shared/sample-images/themen/` and `shared/sample-images/kontext/`
  - Each is >50KB (sanity check; actual size 130-310KB per ecosystem 8.1)
  - All 6 carry the Symbolfoto bottom-band watermark
  - Manifest has 13 total entries; `library.validate_manifest()` returns []
  - Generation log captured in EXECUTION.md (cost, retry count per image)
  </done>
  <commit>13: feat(library): add 6 new demo images (gemeindebau, erwachsenenbildung, handwerk, radweg, versammlung, stammtisch)</commit>
</task>

<task type="auto">
  <name>Task 7: Refactor 5 new templates' build.py to use library.load()</name>
  <files>templates/kandidat-falzflyer-din-lang/build.py, templates/wahltag-tueranhaenger/build.py, templates/themen-plakat-a3-quer/build.py, templates/infostand-tent-card-a5-quer/build.py</files>
  <action>
  Switch the 5 new templates from `(HERE / "samples" / "x.jpg").exists()` reads
  to `library.load("x", optional=True)`. Per codebase research §4.3 the
  conditional-inject pattern is preserved — fresh checkouts without the
  library file emit empty slots; once library is in place, slots fill.

  Per slot:

  **kandidat-falzflyer-din-lang/build.py** (lines ~213, 369, 396, 424):
  - L213 Portrait (87×105mm) → `library.load("portrait_maria", optional=True)` +
    `library.crop_for_frame(img, target_w_mm=87, target_h_mm=105)`
  - L369 Thema-1 (87×24mm) → `library.load("themen_klimaschutz_solar", optional=True)`
    + `library.crop_for_frame(img, target_w_mm=87, target_h_mm=24)`
  - L396 Thema-2 (87×24mm) → `library.load("themen_soziales_kaffeehaus", optional=True)`
    + `library.crop_for_frame(img, target_w_mm=87, target_h_mm=24)`
  - L424 Thema-3 (87×24mm) → `library.load("themen_bildung_volksschule", optional=True)`
    + `library.crop_for_frame(img, target_w_mm=87, target_h_mm=24)`

  **wahltag-tueranhaenger/build.py** (line ~309):
  - L309 Kandidat-Portrait (65×85mm) → `library.load("portrait_stefan", optional=True)`
    + `library.crop_for_frame(img, target_w_mm=65, target_h_mm=85)`

  **themen-plakat-a3-quer/build.py** (line ~239):
  - L239 Themen-Hero (180×60mm) → `library.load("themen_klimaschutz_windrad", optional=True)`
    + `library.crop_for_frame(img, target_w_mm=180, target_h_mm=60)`

  **infostand-tent-card-a5-quer/build.py** (line ~221):
  - L221 Hintergrund (44×33mm) → `library.load("kontext_infostand_szene", optional=True)`
    + `library.crop_for_frame(img, target_w_mm=44, target_h_mm=33)`

  **wahlaufruf-postkarte-a6-quer/build.py** — UNCHANGED (no library images,
  only QR + brand assets per codebase research §2.5).

  Per-template pattern:
  ```python
  from sla_lib.builder import library, pack_inline_image, ImageFrame, ...

  # Before (existing #11 conditional-inject):
  portrait_path = HERE / "samples" / "portrait-cover.jpg"
  portrait_data = portrait_ext = None
  if portrait_path.exists():
      portrait_bytes = portrait_path.read_bytes()
      portrait_data, portrait_ext = pack_inline_image(portrait_bytes, "jpg")

  # After:
  portrait_data = portrait_ext = None
  if (img := library.load("portrait_maria", optional=True)) is not None:
      cropped = library.crop_for_frame(img, target_w_mm=87, target_h_mm=105)
      portrait_data, portrait_ext = pack_inline_image(cropped, "jpg")
  # rest of ImageFrame(...) call unchanged
  ```

  After each build.py edit, re-render the gallery for that template:
  ```
  bin/render-gallery <slug>
  ```
  This regenerates `template.sla` (with library bytes embedded), `preview.pdf`,
  `page-*.png`, and updates `meta.yml::previews_for_sla` SHA. Verify visually
  that the rendered gallery PNG looks the same or better than before
  migration (crop may improve composition; visible Symbolfoto-band still
  present at the bottom of every embedded image).

  Run `bin/check-stale-previews` for these 5 templates after each edit.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    for slug in kandidat-falzflyer-din-lang wahltag-tueranhaenger themen-plakat-a3-quer infostand-tent-card-a5-quer wahlaufruf-postkarte-a6-quer; do
      python3 templates/$slug/build.py || exit 1
      bin/render-gallery $slug || exit 1
    done && \
    bin/check-stale-previews
    </automated>
  </verify>
  <done>
  - 4 build.py files (kandidat-falzflyer, wahltag, themen-plakat, infostand) switch from `samples/x.jpg` reads to `library.load("x", optional=True)` + `library.crop_for_frame`
  - wahlaufruf-postkarte-a6-quer build.py untouched
  - `bin/render-gallery <slug>` succeeds for all 5 new templates
  - Preview PDFs show the migrated demo content with watermarks intact
  - `bin/check-stale-previews` green for all 5
  - meta.yml `previews_for_sla:` SHA updated for each
  </done>
  <commit>13: refactor(templates): switch 5 new templates to library.load() + crop_for_frame</commit>
</task>

<task type="auto">
  <name>Task 8: Patch render_pipeline.py to prefer template-preview.sla</name>
  <files>tools/render_pipeline.py, tools/sla_lib/tests/test_render_pipeline.py</files>
  <action>
  Add the 4-line pipeline patch + 1 helper for the production-template
  `template-preview.sla` flow (per RESEARCH §"<interfaces> for render-pipeline
  change" + codebase research §5.2).

  1. In `tools/render_pipeline.py`, add a helper above `_orchestrate_single`
     (which is around line 447):
     ```python
     def _select_render_source(template_dir: Path) -> Path:
         """Prefer template-preview.sla (gallery render) over template.sla.

         Production templates emit a separate preview-SLA so the round-trip-stable
         template.sla stays clean. Gallery renders use the preview when present.
         """
         preview = template_dir / "template-preview.sla"
         if preview.exists():
             return preview
         return template_dir / "template.sla"
     ```

  2. In `_orchestrate_single`, find the line that reads the SLA path (around
     line 458 — `sla_path = tdir / "template.sla"` or
     `template_sla = tdir / "template.sla"` depending on existing code shape):
     - Keep the original `template_sla = tdir / "template.sla"` for the
       SHA-pin path (later in the function — `_sha256_of(template_sla)`,
       `_run_sla_diff_strict`, `_update_meta_hash`).
     - Add `render_source = _select_render_source(tdir)` immediately after.
     - Change the `render_sla_to_pdf(...)` call to use `render_source`
       instead of `template_sla`/`sla_path`.
     - Update the `print(f"[{tid}] rendering ... → preview.pdf …")` log to
       show `render_source.name`.

     Critical invariants (do NOT change):
     - `_sha256_of(template_sla)` STILL hashes `template.sla` (the clean one)
     - `_run_sla_diff_strict` STILL diffs `template.sla` against `original_sla`
     - `_update_meta_hash` STILL writes the SHA of `template.sla`
     - `_mirror_to_site_public` STILL only copies `template.sla` + `preview.pdf`
       (NOT `template-preview.sla`) — the preview-SLA stays in the repo, never
       reaches `site/public/`. The hardcoded list is `("template.sla",
       "preview.pdf")` per codebase research §5.5; verify it stays that way.

  3. Add a test in `tools/sla_lib/tests/test_render_pipeline.py` (create file if
     not present):
     - Build a mock template dir with both `template.sla` and `template-preview.sla`
       → `_select_render_source` returns the preview path
     - Build a mock template dir with only `template.sla` → `_select_render_source`
       returns the clean path

  4. Sanity-check: re-run `bin/render-gallery` for one of the 5 new templates
     (which do NOT have `template-preview.sla`) — should still work and render
     from `template.sla` as before.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    python3 -m pytest tools/sla_lib/tests/test_render_pipeline.py -x -v && \
    bin/render-gallery kandidat-falzflyer-din-lang
    </automated>
  </verify>
  <done>
  - `_select_render_source` helper exists in `tools/render_pipeline.py`
  - `_orchestrate_single` uses it to pick the render source
  - `_sha256_of`, `_run_sla_diff_strict`, `_update_meta_hash`, `_mirror_to_site_public` all still target `template.sla`
  - Test verifies preference + fallback
  - Re-rendering one of the 5 new templates still works (no `template-preview.sla` exists for them yet)
  - tools/check_stale_previews.py and tools/sla_diff.py UNCHANGED
  </done>
  <commit>13: feat(render_pipeline): prefer template-preview.sla for gallery render when present</commit>
</task>

<task type="auto">
  <name>Task 9: Refactor postkarte-a6-kampagne build.py with build_template/build_preview split</name>
  <files>templates/postkarte-a6-kampagne/build.py, templates/postkarte-a6-kampagne/template-preview.sla, templates/postkarte-a6-kampagne/samples/manifest.yml</files>
  <action>
  Implement D3 split for postkarte. Round-trip diff on `template.sla` MUST stay
  green after this task.

  1. Refactor module-level build code into a `build_template() -> Document`
     function. The flat module-level script becomes:
     ```python
     def build_template():
         """Clean — slot-based, no demo content. End users open this."""
         doc = Document(...)
         # ... all the existing module-level code that creates pages, slots,
         # ImageFrames with empty inline_image_data on slots like the hero
         # at line 86 (84×127mm)
         return doc
     ```

  2. Add `build_preview()`:
     ```python
     def build_preview():
         """Gallery preview — clean template + library demo content injected."""
         from sla_lib.builder import library, pack_inline_image
         from sla_lib.builder.primitives import ImageFrame
         doc = build_template()

         # Mutate empty ImageFrames by anname per ecosystem Finding 6.2
         INJECT_MAP = {
             # anname → (library_id, target_w_mm, target_h_mm)
             "<hero anname>": ("themen_klimaschutz_solar", 84, 127),
         }
         for page in doc.pages:
             for frame in page.items:  # adapt to actual page-frames API
                 if isinstance(frame, ImageFrame) and frame.anname in INJECT_MAP:
                     lib_id, w, h = INJECT_MAP[frame.anname]
                     img = library.load(lib_id)  # required, fail-fast
                     cropped = library.crop_for_frame(img, target_w_mm=w, target_h_mm=h)
                     data, ext = pack_inline_image(cropped, "jpg")
                     frame.inline_image_data = data
                     frame.inline_image_ext = ext
         return doc
     ```

     Note: discover the real `anname` for the L86 hero by reading the existing
     build.py (it's whatever string is passed to `ImageFrame(... anname="...")`
     for the 84×127mm slot). If the hero has no anname, ADD one in
     `build_template()` (e.g. `anname="P1 Hero"`) — but check round-trip
     stays green afterwards (annames may or may not affect the round-trip
     diff; `tools/sla_diff.py` may ignore them).

  3. Add `__main__` emit:
     ```python
     if __name__ == "__main__":
         build_template().save(HERE / "template.sla")
         build_preview().save(HERE / "template-preview.sla")
     ```

  4. Run `python3 templates/postkarte-a6-kampagne/build.py` — emits both SLAs.

  5. **Critical round-trip check** — verify `template.sla` is byte-identical to
     pre-task version (no drift introduced by the build_template extraction):
     ```
     PYTHONPATH=tools python3 tools/sla_diff.py templates/postkarte-a6-kampagne/template.sla \
        $(grep '^original_sla:' templates/postkarte-a6-kampagne/meta.yml | cut -d':' -f2 | xargs)
     ```
     Round-trip MUST be green. If not, the build_template refactor introduced
     a non-determinism — debug and fix before continuing.

  6. Run `bin/render-gallery postkarte-a6-kampagne` — the renderer picks
     `template-preview.sla` (per Task 8) and the gallery PNGs show the demo hero.

  7. Add `templates/postkarte-a6-kampagne/samples/manifest.yml` with a
     `uses_from_library:` block listing `themen_klimaschutz_solar`. Postkarte
     has no `samples/` JPGs but may have `klimaschutz.json`/`wohnen.json` —
     leave those untouched.

  8. **DO NOT mirror `template-preview.sla` to `site/public/`** — verify
     `_mirror_to_site_public` does not copy it (the hardcoded list per
     codebase research §5.5).
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    python3 templates/postkarte-a6-kampagne/build.py && \
    test -f templates/postkarte-a6-kampagne/template.sla && \
    test -f templates/postkarte-a6-kampagne/template-preview.sla && \
    PYTHONPATH=tools python3 tools/sla_diff.py templates/postkarte-a6-kampagne/template.sla \
       $(python3 -c "import yaml; print(yaml.safe_load(open('templates/postkarte-a6-kampagne/meta.yml'))['original_sla'])") && \
    bin/render-gallery postkarte-a6-kampagne && \
    bin/check-stale-previews postkarte-a6-kampagne
    </automated>
  </verify>
  <done>
  - `build_template()` and `build_preview()` exist as module functions in postkarte build.py
  - `__main__` saves both `template.sla` and `template-preview.sla`
  - `tools/sla_diff.py` round-trip vs `original_sla` GREEN on `template.sla`
  - `bin/render-gallery postkarte-a6-kampagne` renders the preview SLA → demo content visible
  - `bin/check-stale-previews postkarte-a6-kampagne` green
  - `template-preview.sla` not mirrored to `site/public/`
  - `samples/manifest.yml` has `uses_from_library:` block
  </done>
  <commit>13: feat(postkarte): build_template/build_preview split + library hero in preview SLA</commit>
</task>

<task type="auto">
  <name>Task 10: Refactor plakat-a1-hochformat build.py with build_template/build_preview split</name>
  <files>templates/plakat-a1-hochformat/build.py, templates/plakat-a1-hochformat/template-preview.sla, templates/plakat-a1-hochformat/samples/manifest.yml</files>
  <action>
  Same pattern as Task 9 for plakat. Round-trip diff on `template.sla` MUST
  stay green.

  1. Refactor module-level into `build_template()`.

  2. Add `build_preview()` with INJECT_MAP for the 1 hero slot at line 151
     (594×414mm landscape):
     ```python
     INJECT_MAP = {
         "<hero anname>": ("themen_klimaschutz_solar", 594, 414),
     }
     ```
     Pick `themen_klimaschutz_solar` (large landscape source, fits the 594×414
     ≈ 1.43:1 frame after center-crop) per codebase research §2.2.
     Alternative would be `themen_klimaschutz_windrad` — pick whichever has the
     more striking hero composition for an A1 plakat. Document the choice in
     a code comment.

  3. `__main__` emits both SLAs.

  4. Verify round-trip green on `template.sla` against `original_sla`.

  5. `bin/render-gallery plakat-a1-hochformat` → preview shows the library hero.

  6. Add `templates/plakat-a1-hochformat/samples/manifest.yml` with
     `uses_from_library: - id: themen_klimaschutz_solar`.

  7. Skip the logo bar (line 161, brand asset) and Sonnenblume (line 179,
     brand asset) — leave them as-is per codebase research §2.2.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    python3 templates/plakat-a1-hochformat/build.py && \
    test -f templates/plakat-a1-hochformat/template-preview.sla && \
    PYTHONPATH=tools python3 tools/sla_diff.py templates/plakat-a1-hochformat/template.sla \
       $(python3 -c "import yaml; print(yaml.safe_load(open('templates/plakat-a1-hochformat/meta.yml'))['original_sla'])") && \
    bin/render-gallery plakat-a1-hochformat && \
    bin/check-stale-previews plakat-a1-hochformat
    </automated>
  </verify>
  <done>
  - plakat build.py has build_template/build_preview split
  - Both `template.sla` and `template-preview.sla` exist
  - Round-trip GREEN
  - Gallery PNG shows library hero
  - `samples/manifest.yml` has uses_from_library block
  </done>
  <commit>13: feat(plakat): build_template/build_preview split + library hero in preview SLA</commit>
</task>

<task type="auto">
  <name>Task 11: Refactor zeitung-a4-grun build.py with build_template/build_preview split</name>
  <files>templates/zeitung-a4-grun/build.py, templates/zeitung-a4-grun/template-preview.sla, templates/zeitung-a4-grun/samples/manifest.yml</files>
  <action>
  Same pattern as Tasks 9-10 for zeitung — the largest production template.
  ~10 demo image injects per RESEARCH "be conservative" guidance (NOT all 20
  frames; skip background `fill='Dunkelgrün'` polygon-frames and small icons
  per codebase research §2.3).

  1. Refactor module-level into `build_template()`.

  2. Add `build_preview()` with INJECT_MAP per codebase research §2.3 — the
     conservative subset:
     ```python
     INJECT_MAP = {
         # page → anname → (library_id, target_w_mm, target_h_mm)
         # Cover (page 0)
         "<cover-hero anname>":  ("themen_klimaschutz_windrad", 210, 155.6),
         # Page 1
         "<p1-hero anname>":     ("themen_soziales_gemeindebau", 210, 130.2),
         # Page 2
         "<p2-mid anname>":      ("themen_bildung_volksschule", 112.3, 58),
         # Page 3
         "<p3-hero anname>":     ("themen_wirtschaft_handwerk", 74.7, 58.2),
         # Page 4 foto-spread
         "<p4-spread anname>":   ("kontext_buergerversammlung", 210, 108.1),
         # Page 5
         "<p5-hero anname>":     ("themen_verkehr_radweg", 112.3, 84.1),
         # Page 7 column
         "<p7-portrait anname>": ("portrait_maria", 51.3, 76.4),
         # Page 9 spread
         "<p9-spread anname>":   ("themen_klimaschutz_solar", 210, 126.1),
         # Page 10 column
         "<p10-portrait anname>":("portrait_stefan", 66.6, 94.4),
         # Page 11 bottom strip
         "<p11-bottom anname>":  ("kontext_stammtisch_cafe", 210, 83.3),
         # Page 13 hero
         "<p13-hero anname>":    ("kontext_infostand_szene", 210, 147.4),
     }
     ```
     Discover the actual `anname` strings by reading the existing build.py at
     each line (224, 437, 675, 762, 942, 1042, 1351, 1784, 1875, 2030, 2248).
     If a frame has no anname, add one in `build_template()` first — verify
     round-trip stays green.

     **DO NOT inject into**:
     - `fill='Dunkelgrün'` polygon-frames (lines 1932, 2040, 2258 — these are
       background polygons, not photo slots)
     - Small icons (<30×30mm, lines 311, 1591, 1638, 1914, 2230, 2427)
     - Slots that already have inline_image_data (anything not `image=''`)

  3. `__main__` emits both SLAs.

  4. Verify round-trip GREEN on `template.sla` against `original_sla` — this is
     the highest-risk template for round-trip drift due to its size. Take
     extra care during the build_template extraction.

  5. `bin/render-gallery zeitung-a4-grun` → preview shows demo content across
     14 pages.

  6. Add `templates/zeitung-a4-grun/samples/manifest.yml` with
     `uses_from_library:` block listing all ~10 IDs used.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    python3 templates/zeitung-a4-grun/build.py && \
    test -f templates/zeitung-a4-grun/template-preview.sla && \
    PYTHONPATH=tools python3 tools/sla_diff.py templates/zeitung-a4-grun/template.sla \
       $(python3 -c "import yaml; print(yaml.safe_load(open('templates/zeitung-a4-grun/meta.yml'))['original_sla'])") && \
    bin/render-gallery zeitung-a4-grun && \
    bin/check-stale-previews zeitung-a4-grun
    </automated>
  </verify>
  <done>
  - zeitung build.py has build_template/build_preview split
  - Both `template.sla` and `template-preview.sla` exist
  - Round-trip GREEN on `template.sla` (CRITICAL — largest template, most risk)
  - INJECT_MAP fills 10 photo slots; skips backgrounds + small icons
  - Gallery preview PNGs across 14 pages show demo content
  - `samples/manifest.yml` has uses_from_library block listing all 10 IDs
  </done>
  <commit>13: feat(zeitung): build_template/build_preview split + 10 library injects in preview SLA</commit>
</task>

<task type="auto">
  <name>Task 12: Final cross-cutting verification — all 8 templates green</name>
  <files>(verification only — no edits expected)</files>
  <action>
  Run the full verification suite across all 8 templates. No source changes
  unless a check fails — in which case, the failure goes back to the relevant
  task above for fix.

  1. **Library validation**:
     ```
     PYTHONPATH=tools python3 -c "
     from sla_lib.builder import library
     errs = library.validate_manifest()
     assert not errs, errs
     imgs = library.all_images()
     print(f'Library: {len(imgs)} images')
     assert len(imgs) >= 13
     "
     ```

  2. **All builds**:
     ```
     for slug in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun \
                 themen-plakat-a3-quer wahltag-tueranhaenger \
                 infostand-tent-card-a5-quer kandidat-falzflyer-din-lang \
                 wahlaufruf-postkarte-a6-quer; do
       python3 templates/$slug/build.py || { echo "FAIL: $slug build"; exit 1; }
     done
     ```

  3. **Round-trip diff on 3 production templates** (CRITICAL):
     ```
     for slug in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun; do
       orig=$(python3 -c "import yaml; print(yaml.safe_load(open('templates/$slug/meta.yml'))['original_sla'])")
       PYTHONPATH=tools python3 tools/sla_diff.py templates/$slug/template.sla "$orig" \
         || { echo "FAIL: $slug round-trip"; exit 1; }
     done
     ```

  4. **Stale previews check**:
     ```
     bin/check-stale-previews
     ```

  5. **Brand CI check**:
     ```
     for sla in templates/*/template.sla templates/*/template-preview.sla; do
       [ -f "$sla" ] && python3 tools/check_ci.py "$sla" || true
     done
     ```

  6. **All tests**:
     ```
     python3 -m pytest tools/sla_lib/tests/ -x -v
     ```

  7. **Gallery render full pass** (final visual sanity):
     ```
     bin/render-gallery
     ```
     Verify gallery shows demo content for all 8 templates (production via
     `template-preview.sla`, new via direct conditional inject).

  If any check fails, identify which task introduced the regression, document
  in EXECUTION.md, fix in that task's scope, and re-run from step 1.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    PYTHONPATH=tools python3 -c "from sla_lib.builder import library; assert not library.validate_manifest()" && \
    for slug in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun themen-plakat-a3-quer wahltag-tueranhaenger infostand-tent-card-a5-quer kandidat-falzflyer-din-lang wahlaufruf-postkarte-a6-quer; do
      python3 templates/$slug/build.py || { echo "FAIL build: $slug"; exit 1; }
    done && \
    for slug in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun; do
      orig=$(python3 -c "import yaml; print(yaml.safe_load(open('templates/$slug/meta.yml'))['original_sla'])");
      PYTHONPATH=tools python3 tools/sla_diff.py templates/$slug/template.sla "$orig" || { echo "FAIL diff: $slug"; exit 1; };
    done && \
    bin/check-stale-previews && \
    python3 -m pytest tools/sla_lib/tests/ -x -v && \
    bin/render-gallery
    </automated>
  </verify>
  <done>
  - `library.validate_manifest()` returns []
  - All 8 templates' build.py runs without error
  - Round-trip diff GREEN on all 3 production templates
  - `bin/check-stale-previews` green for all 8
  - `tools/check_ci.py` green for all SLAs (clean + preview)
  - All pytest tests pass (test_library, test_codex_image_gen, test_render_pipeline, plus existing)
  - `bin/render-gallery` (full pass) emits demo-content gallery PNGs for all 8 templates
  </done>
  <commit>13: chore(verify): final cross-cutting verification — 8 templates all green</commit>
</task>

<task type="checkpoint:human-verify">
  <name>Task 13: Visual review pass via tools/visual_review.py</name>
  <files>reviews/library-content-iter1.md</files>
  <action>
  Run the existing `tools/visual_review.py --all` (or per-template if --all
  not present) — captures a per-template visual judgment of the gallery PNG
  against brand expectations. Aggregate findings into
  `reviews/library-content-iter1.md`.

  For each of the 8 templates, the review checks:
  - Library demo content visible in the gallery preview
  - Symbolfoto bottom-band watermark visible on every embedded image
  - Composition matches the slot's aspect (no distorted images)
  - No accidental cropping of important content (faces, key subjects)
  - Brand colors / typography unaffected by demo content
  - Production templates: `template.sla` (clean) is empty-slot; only
    `template-preview.sla` carries demo content

  If iter-1 has blocking findings (e.g. cropped face on a portrait, watermark
  cut off, demo content visually wrong), do an iter-2 fix:
  - Add `centering: [x, y]` override in the manifest entry to bias the crop
  - Or regenerate the offending library image with a tweaked prompt
  - Or swap the library ID for a more-suitable image (within current 13)

  Cap at 2 iterations. If iter-2 still has blocking findings, report in
  EXECUTION.md and stop — escalate to user before opening PR.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    test -f reviews/library-content-iter1.md && \
    grep -q "merge-ready\|no blocking findings\|all 8 templates" reviews/library-content-iter1.md
    </automated>
  </verify>
  <done>
  - `reviews/library-content-iter1.md` exists with per-template assessment
  - Either iter-1 says "all 8 templates merge-ready" OR an iter-2 fix landed and a follow-up review confirms it
  - No blocking findings remain unresolved
  </done>
  <commit>13: docs(review): visual review pass — library content gallery iter1</commit>
</task>

<task type="auto">
  <name>Task 14: Push branch and open PR</name>
  <files>(no source changes)</files>
  <action>
  Push the branch and open the PR — orchestrator merges, NOT this task.

  1. `git push -u origin issue/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen`

  2. Open PR:
     ```
     gh pr create --base main \
       --title "13: feat: centralized demo image library + fill all 8 templates" \
       --body "$(cat <<'EOF'
     ## Summary

     - Centralized demo-image library at `shared/sample-images/` with master `manifest.yml` (13 entries)
     - New `tools/sla_lib/builder/library.py` module with `LibraryImage`, `load`, `crop_for_frame` (watermark-after-crop fix), `regenerate`, JSON-schema validation
     - 7 existing demo images migrated from per-template `samples/` folders
     - 6 new Codex-generated images: gemeindebau, erwachsenenbildung, handwerk, radweg, buergerversammlung, stammtisch_cafe
     - All 8 templates filled: 5 new templates use `library.load()` directly; 3 production templates split into `build_template()`/`build_preview()` emitting `template.sla` (clean, round-trip stable) + `template-preview.sla` (gallery render)
     - Render pipeline patched to prefer `template-preview.sla` when present (4 lines + 1 helper)
     - Pillow pinned to 12.2.0 + jsonschema 4.26.0 added
     - Round-trip diff GREEN on all 3 production templates' clean SLAs

     ## Library inventory (13 images)

     | Category | IDs |
     |----------|-----|
     | portraits (2) | portrait_maria, portrait_stefan |
     | themen (8) | klimaschutz_solar, klimaschutz_windrad, soziales_kaffeehaus, soziales_gemeindebau, bildung_volksschule, bildung_erwachsenenbildung, wirtschaft_handwerk, verkehr_radweg |
     | kontext (3) | infostand_szene, buergerversammlung, stammtisch_cafe |

     ## Test plan

     - [x] `python3 -m pytest tools/sla_lib/tests/` green
     - [x] `library.validate_manifest()` returns []
     - [x] `bin/render-gallery` green for all 8 templates
     - [x] `bin/check-stale-previews` green for all 8
     - [x] `tools/sla_diff.py` round-trip GREEN on postkarte / plakat / zeitung against original SLAs
     - [x] `tools/check_ci.py` green for all `template.sla` AND `template-preview.sla` files
     - [x] Visual review pass — all 8 templates merge-ready (`reviews/library-content-iter1.md`)
     - [x] Symbolfoto bottom-band watermark visible on every embedded image (incl. cropped variants)
     EOF
     )"
     ```

  3. Capture the PR URL in the final report.

  4. **Stop. DO NOT merge.** Orchestrator merges per `feedback_review_in_execute_phase`.
  </action>
  <verify>
    <automated>
    cd /root/workspace/.worktrees/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen && \
    git rev-parse --abbrev-ref HEAD | grep -q "issue/13-zentralisierte" && \
    git ls-remote --heads origin | grep -q "issue/13-zentralisierte" && \
    gh pr list --head $(git rev-parse --abbrev-ref HEAD) --json url --jq '.[0].url' | grep -q "github.com"
    </automated>
  </verify>
  <done>
  - Branch pushed to origin
  - PR opened against main with the title/body above
  - PR URL captured in EXECUTION.md
  - PR is NOT merged (orchestrator merges)
  </done>
  <commit>(no commit — task only pushes + opens PR)</commit>
</task>

</tasks>

<verification>
After all tasks complete, the following must all be green:

```
# 1. Library foundation
PYTHONPATH=tools python3 -c "from sla_lib.builder import library; assert not library.validate_manifest()"

# 2. All template builds
for slug in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun \
            themen-plakat-a3-quer wahltag-tueranhaenger \
            infostand-tent-card-a5-quer kandidat-falzflyer-din-lang \
            wahlaufruf-postkarte-a6-quer; do
  python3 templates/$slug/build.py
done

# 3. Round-trip stability on 3 production templates
for slug in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun; do
  orig=$(python3 -c "import yaml; print(yaml.safe_load(open('templates/$slug/meta.yml'))['original_sla'])")
  PYTHONPATH=tools python3 tools/sla_diff.py templates/$slug/template.sla "$orig"
done

# 4. Stale previews + brand CI
bin/check-stale-previews
for sla in templates/*/template.sla templates/*/template-preview.sla; do
  [ -f "$sla" ] && python3 tools/check_ci.py "$sla" || true
done

# 5. Test suite
python3 -m pytest tools/sla_lib/tests/ -x -v

# 6. Final gallery render
bin/render-gallery

# 7. Visual review
test -f reviews/library-content-iter1.md
```
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria:

- [x] `shared/sample-images/` exists with `portraits/`, `themen/`, `kontext/`, `qr/` subdirs and central `manifest.yml` (Task 5+6)
- [x] At least 2 portraits + 6 themen images (klimaschutz_solar, klimaschutz_windrad, soziales_kaffeehaus, soziales_gemeindebau, bildung_volksschule, bildung_erwachsenenbildung, wirtschaft_handwerk, verkehr_radweg = 8 themen) + 3 kontext images (infostand_szene, buergerversammlung, stammtisch_cafe) — total 13 (Task 5+6)
- [x] All images Symbolfoto-watermarked, JPEG q=80, 1024–2048px long edge (Task 6 + library.crop_for_frame post-watermark guarantee)
- [x] `tools/codex_image_gen.py --library shared/sample-images/manifest.yml` regenerates the library (Task 4)
- [x] Existing template-specific JPGs migrated to `shared/sample-images/`; old `samples/` folders contain only QR codes + `uses_from_library:` manifests (Task 5)
- [x] All 8 templates have empty image slots filled with library references OR explicitly empty per spec (wahlaufruf has no image slots) (Tasks 7+9+10+11)
- [x] `bin/render-gallery <slug>` renders all 8 templates with demo bilder; production templates' `template.sla` round-trip-stable via separate `template-preview.sla` (Task 8+9+10+11)
- [x] `tools/check_ci.py` + `tools/sla_diff.py` round-trip + `bin/check-stale-previews` green on all 8 (Task 12)
- [x] Galerie shows all 8 templates with consistent demo-content atmosphere (Task 12+13)
- [x] Visual review (single pass) confirms "all 8 templates merge-ready, gallery konsistent" (Task 13)
- [x] Library manifest documents per-image: Codex prompt, tags, license note (synthetic demo-only) — schema enforced via JSON Schema (Task 3)
- [x] No "claude" attribution in commits/code/manifests (memory: feedback_no_claude_attribution; enforced in commit_format)
- [x] Watermark-after-crop regression test passes (R-WATERMARK-CROP fix for D7-revised; Task 3)
- [x] codex stdin=DEVNULL preserved (carry-over from #11; Task 2 explicitly does not touch generate_image)
- [x] PR opened (Task 14); orchestrator merges
</success_criteria>
