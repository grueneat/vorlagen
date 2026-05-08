# Research Synthesis — 13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen

Synthesized 2026-05-08 from two parallel research streams:
- `research/codebase.md` — DSL surface, slot inventory, migration map, render-pipeline change plan
- `research/ecosystem.md` — Pillow `ImageOps.fit`, watermark-crop bug, jsonschema, prompt drafts

**Confidence: HIGH** for foundations. Two corrections to CONTEXT.md decisions.

---

## Corrections to CONTEXT.md (research-revised)

### Correction to D7 — `crop_for_frame()` must apply watermark POST-crop

**Original D7:** Library bytes have watermark already, build.py crops at load time.

**Revised:** When library image is portrait-aspect and target frame is landscape (or vice versa), `PIL.ImageOps.fit(centering=(0.5, 0.5))` will crop off the watermark band (the 4% band at bottom of the source). Fix: `crop_for_frame()` removes the original watermark first (or starts from un-watermarked source), crops to target aspect, then re-applies the Symbolfoto-watermark on the cropped result.

**Implementation impact:**
- Library stores TWO variants per image: `<id>.jpg` (watermarked, for direct embed without crop) and `<id>-source.jpg` (un-watermarked, for crop-then-watermark flow). OR: library stores only un-watermarked source, `library.load(id)` returns watermarked-on-the-fly via cache.
- Cleanest: library stores un-watermarked source AND a watermarked native-aspect version. `library.load(id, aspect="native")` returns the watermarked native; `library.load(id, aspect=(w_mm, h_mm))` returns dynamically cropped-and-watermarked.
- Watermark text "Symbolfoto — KI-generiert" applied via Pillow `ImageDraw.text` — same pattern as `tools/codex_image_gen.py::add_demo_watermark`.

**Best Pillow primitive (ecosystem confirmed):** `PIL.ImageOps.fit(im, (w_px, h_px), method=Image.BICUBIC, centering=(0.5, 0.5))` — center-crop + resize in one call. Pin `quality=80, subsampling=2, progressive=False, optimize=True` for deterministic JPEG bytes.

### Correction to D8 — `themen-soziales.jpg` is actually a Kaffeehaus, not Gemeindebau

The existing `templates/kandidat-falzflyer-din-lang/samples/themen-soziales.jpg` was generated with a Wiener-Kaffeehaus prompt during #11 (likely intended as "Soziales = Begegnungsort"). The proposed mapping `→ themen/soziales-gemeindebau.jpg` would be misleading.

**Fix options:**
- A) Preserve bytes, rename ID to `themen_soziales_kaffeehaus` — zero byte change, accurate
- B) Regenerate with Gemeindebau prompt — new bytes, more iconic for "Soziales" theme
- C) Keep as `themen_soziales_kaffeehaus`, ALSO generate a `themen_soziales_gemeindebau` for variety

**Decision:** Go with **A** for migration (preserve bytes, accurate naming). Then **C** later in this issue: also generate `themen_soziales_gemeindebau` as second Soziales option. Library can have multiple images per topic.

### Confirmation of D3 — `<slug>-preview.sla` for production templates is correct

Codebase agent verified via `tools/sla_diff.py:783-791`: filling an empty `image=''` slot on production templates with `inline_image_data` triggers CRITICAL `inline-vs-sidecar-image` round-trip diff against the original SLA. **D3's separate `template-preview.sla` file is mandatory** for production templates. The `template.sla` (clean, no demo content) remains the round-trip-equivalent of the original.

**Implementation:**
- `build.py` defines `build_template()` (clean) and `build_preview()` (with library injection)
- `if __name__ == "__main__"`: emit both files
- Zero changes to `tools/check_stale_previews.py` or `tools/sla_diff.py` — they target `template.sla`
- Render pipeline change: ~4 lines + 1 helper in `tools/render_pipeline.py::_orchestrate_single` to prefer `template-preview.sla` if present
- CI workflow change: ZERO (Pillow already installed via #11; production-template-rebuild already disabled in `pages.yml`)

---

## Summary

A small-medium issue. New file `tools/sla_lib/builder/library.py` (~150 LoC). 7 file moves + 5 new Codex generations + 8 build.py edits + render-pipeline 4-line change + jsonschema dependency. Backward-compatible — existing 5 new templates' visual output should be byte-identical (they reference the same JPG bytes, just from a different path). Production templates gain a `template-preview.sla` artifact each but `template.sla` round-trip stays green.

Biggest design risk is the watermark-crop bug (R-WATERMARK-CROP from ecosystem). Fix is in the library API design, not afterthought.

---

## Codebase Touchpoints (verified)

| File | Lines | Role |
|---|---|---|
| `tools/sla_lib/builder/primitives.py::pack_inline_image` | 750-761 | Reused as-is for byte → inline encoding |
| `tools/sla_lib/builder/library.py` | NEW (~150 LoC) | New module: LibraryImage dataclass + load/find/regenerate/crop_for_frame |
| `tools/codex_image_gen.py::add_demo_watermark` | existing | Reused for post-crop watermark application; refactor to be reusable from library.py |
| `tools/codex_image_gen.py::generate_image` | existing | Reused with `--library <manifest>` flag for library regen |
| `tools/render_pipeline.py::_orchestrate_single` | ~430-469 | **PATCH**: prefer `<slug>-preview.sla` if present |
| `tools/check_stale_previews.py` | UNCHANGED | targets `template.sla` only |
| `tools/sla_diff.py` | UNCHANGED | targets `template.sla` only |
| `templates/<slug>/build.py` (8 templates) | varies | Per-template: switch from `samples/x.jpg` reads to `library.load("x")`. Production templates split into `build_template()` + `build_preview()` |
| `templates/<slug>/samples/manifest.yml` | varies | Replace `images:` list with `uses_from_library:` references; `qr_codes:` stays |
| `shared/sample-images/manifest.yml` | NEW | Master library index |
| `shared/sample-images/portraits/*.jpg` etc. | NEW (12 files) | Library bytes |
| `Dockerfile.claude` | line ~58 | Add `jsonschema==4.26.0` |
| `.github/workflows/pages.yml` | line ~50 | Add `jsonschema==4.26.0` to pip install |
| `tools/sla_lib/tests/test_library.py` | NEW | Unit tests for library module |

### `<interfaces>` for `tools/sla_lib/builder/library.py`

```python
@dataclass(frozen=True)
class LibraryImage:
    """One image in shared/sample-images/, with metadata."""
    id: str
    path: Path                  # absolute path on disk
    bytes: bytes                # cached on first load
    meta: dict                  # tags, prompt, synthetic, license_note, size, watermark

    @property
    def aspect_ratio(self) -> float: ...
    @property
    def width_px(self) -> int: ...
    @property
    def height_px(self) -> int: ...

class LibraryError(Exception):
    """Raised on missing/invalid library entries."""

# Public API
def load(id: str, *, optional: bool = False) -> Optional[LibraryImage]:
    """Resolve image by ID. Raises LibraryError if missing+required.
    Returns LibraryImage with .bytes loaded."""

def all_images() -> dict[str, LibraryImage]:
    """Iterate every entry in the master manifest."""

def find(*, tags: Sequence[str] = (), category: Optional[str] = None) -> list[LibraryImage]:
    """Find images matching all-of tags and optional category."""

def crop_for_frame(
    img: LibraryImage,
    *,
    target_w_mm: float,
    target_h_mm: float,
    dpi: int = 300,
    apply_watermark: bool = True,
) -> bytes:
    """Center-crop+resize to target frame at given DPI. JPEG q=80 deterministic.
    
    If apply_watermark=True (default), re-applies Symbolfoto-watermark to cropped
    result — preserves D5 / EU AI Act compliance even when source watermark
    would be cropped out. Uses an un-watermarked-source variant if available
    (path-with `-source.jpg` suffix), else crops the watermarked image and
    re-stamps watermark on top.
    
    Uses PIL.ImageOps.fit(centering=(0.5, 0.5), method=BICUBIC).
    """

def regenerate(id: str, *, force: bool = False) -> bool:
    """Re-run Codex generation for one library entry. Skips if up-to-date
    unless force. Wraps tools.codex_image_gen.generate_image with manifest
    integration. Watermark applied automatically."""

def regenerate_all(*, force: bool = False) -> dict[str, bool]:
    """Regen all library images. Returns id → success map."""

def validate_manifest() -> list[str]:
    """Validate shared/sample-images/manifest.yml against JSON schema.
    Returns list of error strings (empty = valid)."""
```

### `<interfaces>` for the build.py split (production templates)

```python
# templates/postkarte-a6-kampagne/build.py
def build_template() -> Document:
    """Clean template — slot-based, no demo content. End users open this."""
    doc = Document(...)
    # ... empty image slots
    return doc

def build_preview() -> Document:
    """Gallery preview — clean template + library demo content injected."""
    doc = build_template()
    # Find ImageFrames by anname, fill with library bytes
    portrait_img = library.load("portrait_maria")
    cropped = library.crop_for_frame(portrait_img, target_w_mm=87, target_h_mm=105)
    # ... etc
    return doc

if __name__ == "__main__":
    build_template().save(HERE / "template.sla")
    build_preview().save(HERE / "template-preview.sla")
```

### `<interfaces>` for render-pipeline change

```python
# tools/render_pipeline.py — _orchestrate_single ~line 430

def _select_render_source(template_dir: Path) -> Path:
    """Prefer template-preview.sla (gallery render) over template.sla."""
    preview = template_dir / "template-preview.sla"
    if preview.exists():
        return preview
    return template_dir / "template.sla"

# In _orchestrate_single, replace:
#   sla_path = template_dir / "template.sla"
# with:
#   sla_path = _select_render_source(template_dir)
```

`tools/check_stale_previews.py` continues to hash `template.sla`. `tools/sla_diff.py` continues to compare `template.sla` against `original_sla:`. Round-trip stays green.

---

## Migration Map (corrected per ecosystem D8 finding)

| Existing Path | New Path | New Library ID |
|---|---|---|
| `templates/kandidat-falzflyer-din-lang/samples/portrait-cover.jpg` | `shared/sample-images/portraits/maria-beispiel.jpg` | `portrait_maria` |
| `templates/wahltag-tueranhaenger/samples/portrait-back.jpg` | `shared/sample-images/portraits/stefan-beispiel.jpg` | `portrait_stefan` |
| `templates/kandidat-falzflyer-din-lang/samples/themen-klimaschutz.jpg` | `shared/sample-images/themen/klimaschutz-solar.jpg` | `themen_klimaschutz_solar` |
| `templates/kandidat-falzflyer-din-lang/samples/themen-soziales.jpg` | `shared/sample-images/themen/soziales-kaffeehaus.jpg` | `themen_soziales_kaffeehaus` *(was wrong in CONTEXT D8)* |
| `templates/kandidat-falzflyer-din-lang/samples/themen-bildung.jpg` | `shared/sample-images/themen/bildung-volksschule.jpg` | `themen_bildung_volksschule` |
| `templates/themen-plakat-a3-quer/samples/themen-hero.jpg` | `shared/sample-images/themen/klimaschutz-windrad.jpg` | `themen_klimaschutz_windrad` |
| `templates/infostand-tent-card-a5-quer/samples/hintergrund-mitmachen.jpg` | `shared/sample-images/kontext/infostand-szene.jpg` | `kontext_infostand_szene` |

7 file moves via `git mv` (preserves blame).

**QR codes stay template-specific** (D9): each template's `samples/qr-*.png` remains in place, manifest stays per-template for QRs. The library covers JPG photos only.

## New Library Entries to Generate (5+)

Per CONTEXT D10 + ecosystem-delivered prompts:

| ID | Path | Status |
|---|---|---|
| `themen_soziales_gemeindebau` | `shared/sample-images/themen/soziales-gemeindebau.jpg` | NEW (different from kaffeehaus, more iconic) |
| `themen_bildung_erwachsenenbildung` | `shared/sample-images/themen/bildung-erwachsenenbildung.jpg` | NEW |
| `themen_wirtschaft_handwerk` | `shared/sample-images/themen/wirtschaft-handwerk.jpg` | NEW |
| `themen_verkehr_radweg` | `shared/sample-images/themen/verkehr-radweg.jpg` | NEW |
| `kontext_buergerversammlung` | `shared/sample-images/kontext/buergerversammlung.jpg` | NEW |
| `kontext_stammtisch_cafe` | `shared/sample-images/kontext/stammtisch-cafe.jpg` | NEW |

6 new Codex generations × $0.08 = **$0.48** total. Acceptable.

Plus optionally:
- `portrait_alex` (NEW, third portrait, gender-nonbinary or older Senior:in for diversity)

Final library count: **2 portraits + 8 themen + 3 kontext = 13 images**, plus optional alex = 14.

## Per-Template Slot Inventory (codebase-agent verified)

| Template | Image Slots | Currently Filled | Library Assignments |
|---|---|---|---|
| postkarte-a6-kampagne (production) | 1 hero (line 86 of build.py) | empty | `portrait_maria` OR `kontext_buergerversammlung` (TBD in plan) |
| plakat-a1-hochformat (production) | 1 hero (line 151, 594×414mm) | empty | `themen_klimaschutz_solar` (large landscape works) |
| zeitung-a4-grun (production) | ~10 large slots, ~20 frames total | empty | Multiple — 1 cover hero + 4 themen-thumbnails + 2 photo-spread images |
| themen-plakat-a3-quer (new) | 1 themen-hero | filled (existing themen-hero.jpg) | `themen_klimaschutz_windrad` (migrated) |
| wahlaufruf-postkarte-a6-quer (new) | 0 image slots, only QR | n/a | n/a |
| wahltag-tueranhaenger (new) | 1 portrait | filled (existing portrait-back.jpg) | `portrait_stefan` (migrated) |
| infostand-tent-card-a5-quer (new) | 1 hintergrund | filled | `kontext_infostand_szene` (migrated) |
| kandidat-falzflyer-din-lang (new) | 1 portrait + 3 themen | filled | `portrait_maria`, `themen_klimaschutz_solar`, `themen_soziales_kaffeehaus`, `themen_bildung_volksschule` (all migrated) |

Production-template empty slots will switch to library-injected via `template-preview.sla`. The 5 new templates already use conditional inject — only the source path changes.

---

## Standard Stack (verified)

| Tool | Version | Status |
|---|---|---|
| Pillow | 12.2.0 | Already installed (#11). **Pin in Dockerfile** for cross-env determinism (ecosystem R-DOCKER-PIN). |
| qrcode[pil] | 8.2 | Already installed (#11) — no change |
| pyzbar | 0.1.9 | Already installed (#11) — no change |
| jsonschema | NEW: 4.26.0 | Add to Dockerfile pip block + CI workflow pip install |
| codex CLI | 0.128.0 | Already configured |
| Python | 3.13 | unchanged |

## Don't Hand-Roll

- **Don't write a custom crop algorithm.** Use `PIL.ImageOps.fit(centering=(0.5, 0.5))`.
- **Don't write a watermark renderer.** Reuse `tools/codex_image_gen.py::add_demo_watermark` (refactor it to library.py-callable).
- **Don't write a JSON schema lib.** Use `jsonschema==4.26.0`.
- **Don't add Pillow as a NEW dep.** It's there; just pin.
- **Don't change `<slug>-preview.sla` filename**; the codebase research locked that exact name.
- **Don't restructure the existing `samples/manifest.yml` schema** for QR codes — only `images:` section migrates to `uses_from_library:`.

---

## Common Pitfalls (top 8 by impact × likelihood)

| # | ID | Risk | L | I | Mitigation |
|---|---|---|---|---|---|
| 1 | R-WATERMARK-CROP | Watermark cropped off in landscape↔portrait fits | HIGH | HIGH | Apply watermark POST-crop in `crop_for_frame()`; library stores un-watermarked source variant |
| 2 | R-LIBJPEG | Cross-env JPEG byte determinism (libjpeg-turbo version) | MED | HIGH | Library regen MUST run in container; commit bytes; reject `regenerate-on-build` paths |
| 3 | R-PROD-DIFF | Production template.sla regression if changed | LOW | CRITICAL | D3 `template-preview.sla` separation; test round-trip after migration |
| 4 | R-MIGRATION-NAMING | `themen_soziales_gemeindebau` ID for kaffeehaus image is misleading | CONFIRMED | MED | Fix in this synthesis: `themen_soziales_kaffeehaus` for the migrated bytes |
| 5 | R-PROMPT-DRIFT | New Codex generations differ from local-test attempts | MED | LOW | Cap 5 retries per image; manifest documents the exact prompt for reproducibility |
| 6 | R-DOCKER-PIN | Pillow not pinned, deterministic regen at-risk | CONFIRMED | MED | Pin Pillow==12.2.0 in Dockerfile.claude with new comment |
| 7 | R-SLOT-COUNT | Zeitung 20 frames × multiple library injections may fight existing layout | MED | MED | Plan inventories per-frame; pick conservative subset (1 cover + 4 themen + 2 spread) |
| 8 | R-MTIME-REGEN | Manifest mtime-based regen triggers full library regen on every commit | LOW | MED | Library regen uses content-hash comparison (manifest entries' prompt+id) not file mtime |

---

## Plan Inputs (what PLAN.md must absorb)

1. **One new module**: `tools/sla_lib/builder/library.py` — full `<interfaces>` above
2. **One refactor**: `tools/codex_image_gen.py::add_demo_watermark` made library-callable, plus library-mode flag
3. **One new tool**: optional `tools/check_library.py` for manifest validation (could live inside `library.py::validate_manifest`)
4. **One pipeline patch**: `tools/render_pipeline.py::_orchestrate_single` adds `_select_render_source()` helper (4 lines + 1 helper)
5. **One Dockerfile add**: `jsonschema==4.26.0` + Pillow pin
6. **CI workflow**: `jsonschema==4.26.0` to pip install line; ELSE no changes
7. **7 file migrations** (`git mv` to preserve history)
8. **5-6 new Codex generations** + watermark + commit
9. **8 build.py edits**:
   - 5 new templates: switch source from samples/ to library.load() + library.crop_for_frame() where aspect mismatch
   - 3 production templates: split into build_template() + build_preview() pattern; emit two SLAs
10. **8 meta.yml edits**: per-template manifest cleanup (only QR codes stay; image references move to library)
11. **Tests**:
    - `tools/sla_lib/tests/test_library.py` — load/find/crop_for_frame/regenerate/validate_manifest
    - Determinism test: same crop call twice produces byte-identical output
    - Watermark-after-crop test (R-WATERMARK-CROP regression)
12. **Visual review pass** at end (single iteration; constraint-DSL of #12 not yet available, manual confirmation gate)
13. **PR + merge** per user authorization

## Phase Order

1. Library module + tests (no template changes yet)
2. Migration: git mv, manifest assembly, library validates
3. New Codex generations (Codex calls in container, ~15-20 min total)
4. Template build.py refactor (5 new + 3 production) — switch to library.load()
5. Production templates: build_template/build_preview split + emit -preview.sla
6. Pipeline patch + Dockerfile/CI adds
7. Re-render all 8 templates + verify SHAs
8. Visual review + PR + merge
