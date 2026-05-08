# Plan: Demo-Bilder via Codex + QR-Codes für 5 neue Templates

<objective>
What this plan accomplishes:
- Generate, commit, and embed two clearly separated demo-content families across the 5 new templates from PR #20:
  - **Codex-portraits + themen-photos** via `tools/codex_image_gen.py` extended with EU-AI-Act-compliant Pillow watermark + output-recovery scan.
  - **Branded, scannable QR codes** via a new `tools/qr_gen.py` (Dunkelgrün modules, ECC=H, optional center-logo, deterministic bytes).
- Patch the render-pipeline filter (`tools/render_pipeline.py:644-650` and `tools/check_stale_previews.py:58`) to widen from `original_sla:`-only to also cover `previews_for_sla:`-tracked DSL-only templates — without this the 5 new templates skip silently in `bin/render-gallery <slug>`.
- Add the slot-level scaffolding the issue assumes but PR #20 didn't ship: ImageFrame slots in `build.py` for postkarte (QR), türanhänger (QR), falzflyer (3 themen-photos), themen-plakat (optional themen-photo + QR), tent-card (QR — emit ImageFrame, slot was spec-only). Spec slot-tables track the additions so `tools/spec_check.py` stays green.
- Enlarge the tent-card QR slot from 14 mm to ≥17 mm (D1 module-size violation) in spec + build.
- Conditional-inject pattern (NOT separate `<slug>-preview.sla`): each `build.py` checks `if (HERE / "samples" / "<file>").exists()` and embeds via `pack_inline_image()`. Empty slot otherwise — fresh checkouts (no committed samples) still produce clean templates.
- Run a single visual-review pass (D10) over the regenerated gallery PNGs comparing demo-populated vs prior placeholder versions.
- Ship via PR with side-by-side gallery before/after.

Why it matters:
- Galerie-Previews der 5 neuen Templates zeigen aktuell leere Bild-Slots und nicht-funktionale QR-Hinweise. Reviewer:innen können „funktioniert echt" nicht beurteilen.
- Demo-Bilder + scannbare QRs sind die letzte fehlende Komponente für „templates ready for showcase" — D11 aus Issue #10 wurde dort nicht aktiv ausgeführt.
- EU AI Act Art 50 (in force 2026-08-02) macht eine sichtbare KI-Markierung auf synthetic portraits zur Pflicht; wir verbauen sie heute → forward-compat.

Scope:
- IN: 1 new tool (`tools/qr_gen.py`), 2 helpers added to `tools/codex_image_gen.py` (`add_demo_watermark`, `recover_codex_output`), 2 filter patches (~3 LoC each), 5 new manifest.yml + samples directories, 5 build.py extensions (conditional inject + new slots), 5 spec.md slot-table updates, 1 Dockerfile dependency block, 1 visual-review pass at end.
- OUT (deferred per CONTEXT.md D11): logo replacement (separate issue), spec_check.py tolerance tuning (separate issue), QR/Codex generation in CI (one-shot authoring tools, never CI-invoked), animated/SVG demo content, multilingual demo URLs, real candidate photos.

CONTEXT.md fidelity (research-corrected versions):
- D2 corrected: Codex backend is `gpt-image-2`, not `dall-e-3`. Manifest `model:`/`quality:` fields kept as **informational comments only**. Watermark text: `Symbolfoto — KI-generiert` (EU AI Act forward-compat).
- D3 corrected: `noe.gruene.at/themen/klimaschutz/` returns 404 → fallback to `/themen/`. `/termine/` 301-redirects, but encode the canonical short URL (browsers/scanners follow transparently).
- D5/D6 corrected: NO `<slug>-preview.sla` separate file. Conditional inject in `template.sla` per template. The acceptance criterion "`<slug>-preview.sla` re-rendered" reads as "`template.sla` re-rendered with embedded demo content; `previews_for_sla` SHA matches in `meta.yml`".
- D1, D7, D8, D9, D10, D11 honored as locked.
- New mandatory render-pipeline filter patch (research finding) — without it, `bin/render-gallery` skips all 5 new templates.
- New mandatory tent-card slot enlargement to ≥17 mm (research finding — 14 mm violates D1 0.5 mm/module rule).
</objective>

<skills>
Read and follow these skills during execution:
- python — Python tooling (`tools/qr_gen.py`, watermark/recovery additions to `tools/codex_image_gen.py`, filter patches). Follow project conventions (snake_case, dataclasses, type hints, docstrings citing line refs).
- git-committer — One atomic commit per task with `11: type(scope): subject` convention.
- issue:review — Single-pass visual review at end (D10) using existing `tools/visual_review.py` with a focused custom prompt.
</skills>

<context>
Issue: @.issues/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates/ISSUE.md
Decisions: @.issues/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates/CONTEXT.md
Research: @.issues/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates/RESEARCH.md
Codebase research stub: @.issues/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates/research/codebase.md
Ecosystem research: @.issues/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates/research/ecosystem.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

==== EXISTING (already in codebase, do NOT re-create) ====

# tools/sla_lib/builder/primitives.py:750-761 — pack_inline_image
def pack_inline_image(image_bytes: bytes, ext: str) -> tuple[str, str]:
    """Encode raster bytes for ImageFrame.inline_image_data (qCompress format).
    Returns (qcompressed_b64, ext). Use ext='png' for QR, 'jpg' for Codex portraits."""
    blob = struct.pack(">I", len(image_bytes)) + zlib.compress(image_bytes, 6)
    return base64.b64encode(blob).decode("ascii"), ext

# tools/sla_lib/builder/primitives.py:742 — ImageFrame
@dataclass
class ImageFrame(_Frame):
    pos: Anchor
    size: tuple[float, float]                          # (width_mm, height_mm)
    inline_image_data: str | None = None               # base64 from pack_inline_image
    inline_image_ext: str | None = None                # "png" or "jpg"
    scale_type: int = 1                                # 1 = fit-to-frame
    ratio: int = 1                                     # 1 = preserve aspect
    anname: str = ""
    local_scale: tuple[float, float] = (1.0, 1.0)

# tools/codex_image_gen.py — existing module surface (PR #20, untested)
def parse_manifest(manifest_path: Path) -> dict:        # reads images: list
    """Returns {"images": [...], ...}; tolerate qr_codes: key without raising."""

def build_codex_prompt(image_spec: dict, output_path: Path) -> str:   # L97-110
    """Natural-language prompt scaffolded for codex's image_gen tool."""

def run_codex_for_image(image_spec: dict, output_dir: Path) -> Path | None:  # L116-180
    """Subprocess runs `codex exec ...`; returns output Path or None on failure."""

# tools/render_pipeline.py:644-650 — current (BUG) filter
templates_to_render = [
    t for t in all_templates
    if (t.dir / "meta.yml").exists()
    and yaml.safe_load((t.dir / "meta.yml").read_text()).get("original_sla")
]
# Patch: change `.get("original_sla")` to a helper that accepts EITHER
# `original_sla` (round-trip templates) OR `previews_for_sla` (DSL-only templates).

# tools/check_stale_previews.py:58 — same filter pattern, same patch shape

==== NEW TOOL: tools/qr_gen.py ====

# Wrapper around qrcode 8.2 + Pillow 12.2.0. ~120 LoC including manifest parser + CLI.
# DEPENDS ON: qrcode[pil]==8.2 (new pip dep, see Task 1).

from pathlib import Path
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw

DUNKELGRUEN_RGB = (28, 72, 33)              # D1: CMYK 85/35/95/10 -> sRGB approx
WHITE_RGB = (255, 255, 255)
ECC_MAP = {"L": ERROR_CORRECT_L, "M": ERROR_CORRECT_M, "Q": ERROR_CORRECT_Q, "H": ERROR_CORRECT_H}

def generate_qr_png(
    target_url: str,
    output_path: Path,
    *,
    module_color: tuple[int, int, int] = DUNKELGRUEN_RGB,
    background_color: tuple[int, int, int] = WHITE_RGB,
    embed_logo: Path | None = None,            # circular pre-masked PNG
    error_correction: str = "H",               # D1: H required for logo
    box_size: int = 10,                        # px per module
    border: int = 4,                           # quiet zone (D1 minimum)
    version: int | None = None,                # None = auto-fit
) -> Path:
    """Render a deterministic, scannable QR PNG to output_path. Returns output_path.

    Determinism: with qrcode==8.2 + Pillow==12.2.0 + optimize=True, byte-identical
    output across runs. See research/ecosystem.md section 1 for empirical SHA-256 results.

    Logo embed: pass embed_logo as a Path to a square PNG with transparent corners
    (alpha=0 outside the inscribed circle). Use circular_mask() helper if source is
    opaque-square. ECC=H required (~30% recovery) to scan despite center occlusion.
    """

def circular_mask(src_path: Path, dst_path: Path) -> Path:
    """Pre-mask a square logo to a circle (alpha=0 outside inscribed circle)."""

def parse_manifest(manifest_path: Path) -> dict:
    """Read templates/<slug>/samples/manifest.yml. Permissive: missing 'qr_codes:'
    returns {'qr_codes': []} not raise. Same shape as codex_image_gen.parse_manifest."""

def main(argv: list[str] | None = None) -> int:
    """CLI: python3 tools/qr_gen.py templates/<slug>
    Reads manifest.yml, generates each qr_codes[] entry to its output_path."""

==== NEW: tools/codex_image_gen.py extensions ====

# Add at module level alongside existing functions. ~50 LoC + tests.

def add_demo_watermark(
    image_path: Path,
    text: str = "Symbolfoto — KI-generiert",       # EU AI Act Art 50 forward-compat
    font_path: Path | None = None,                  # default: Gotham Narrow Book
    band_height_pct: float = 0.04,                  # ~4% of image height
    text_color: tuple[int, int, int, int] = (255, 255, 255, 230),
    bg_color: tuple[int, int, int, int] = (0, 0, 0, 160),
) -> Path:
    """Draw a bottom-center band with caption onto image_path (in-place).
    Uses Pillow ImageDraw.text() with TTF font. Reference snippet in
    research/ecosystem.md section 3 'Pillow caption snippet'.

    Default font: /usr/local/share/fonts/gruene/Gotham Narrow Book.otf
    Fallback: Pillow.ImageFont.load_default() if Gotham missing.

    Returns image_path (caller can chain).
    """

def recover_codex_output(
    target_path: Path,
    *,
    search_dir: Path = Path.home() / ".codex" / "generated_images",
    started_at: float | None = None,                # time.time() before codex call
) -> bool:
    """If codex saved to ~/.codex/generated_images/<UUID>.png instead of target,
    move the most-recent file there to target_path. Returns True on recovery,
    False if nothing newer than `started_at` exists. Mitigates research P-CODEX-PATH.
    """

# Wire into existing run_codex_for_image: after subprocess.run, if output not at
# target_path, call recover_codex_output(target_path, started_at=t0) before
# marking failure. Then call add_demo_watermark(target_path) on success.

==== MANIFEST SCHEMA (extend existing samples/manifest.yml from PR #20) ====

# templates/<slug>/samples/manifest.yml
slug: kandidat-falzflyer-din-lang        # template id
images:                                   # list, may be empty
  - name: portrait-cover
    output_path: samples/portrait-cover.jpg
    prompt: |
      Documentary photograph of a Central European woman in her mid-40s,
      head-and-shoulders portrait, soft afternoon window light from camera left,
      neutral grey-green out-of-focus background, 50mm lens, shallow depth of field,
      visible pores and natural skin texture, warm color balance.
      No watermark. No text overlays. No logos or trademarks. No glamorization.
    size: "1024x1536"                     # gpt-image-2 portrait
    synthetic: true
    note: "synthetic, demo-only — not a real candidate; replace with real candidate photo for campaign use"
    # informational only (codex picks model internally):
    model: gpt-image-2
    quality: high
qr_codes:                                  # list, may be empty
  - name: qr-mitmachen
    target_url: https://noe.gruene.at/mitmachen/
    output_path: samples/qr-mitmachen.png
    module_color: [28, 72, 33]            # Dunkelgrün sRGB
    background_color: [255, 255, 255]
    embed_logo: shared/logos/sonnenblume-circle.png   # optional, monochrome dunkelgrün
    error_correction: "H"
    box_size: 10
    border: 4
    note: "Demo URL — endusers replace with their Bezirks-/Listen-URL"

==== TEMPLATE SLOT INVENTORY (RESEARCH.md verified) ====

# Per-template state at start of execute:
# wahlaufruf-postkarte-a6-quer    : NO image slots -> ADD QR slot in build.py + spec
# wahltag-tueranhaenger           : portrait slot exists, NO QR -> ADD QR slot
# kandidat-falzflyer-din-lang     : 1 portrait + 1 QR exist; ADD 3 themen-photo slots + 2nd QR
# themen-plakat-a3-quer           : NO image slots beyond logo -> ADD optional themen-photo + QR
# infostand-tent-card-a5-quer     : QR slot in spec only (14 mm, TOO SMALL); ADD ImageFrame in build.py + ENLARGE to 17 mm

==== URL -> QR-VERSION TABLE (RESEARCH.md section 5) ====

| Template                          | URL to encode                          | Version | Modules |
|-----------------------------------|----------------------------------------|---------|---------|
| wahlaufruf-postkarte-a6-quer      | https://noe.gruene.at/                 | 3       | 29      |
| wahltag-tueranhaenger             | https://noe.gruene.at/themen/          | 4       | 33      |
| kandidat-falzflyer-din-lang QR1   | https://noe.gruene.at/mitmachen/       | 4       | 33      |
| kandidat-falzflyer-din-lang QR2   | https://noe.gruene.at/termine/         | 3       | 29      |
| infostand-tent-card-a5-quer       | https://noe.gruene.at/mitmachen/       | 4       | 33      |
| themen-plakat-a3-quer             | https://noe.gruene.at/themen/          | 4       | 33      |
#                                                                       (fallback from /themen/klimaschutz/ which 404s)

</interfaces>

Key files (paths relative to worktree root):
@Dockerfile.claude — add qrcode[pil]==8.2, pyzbar==0.1.9, libzbar0, zbar-tools
@tools/codex_image_gen.py — extend with watermark + recovery
@tools/qr_gen.py — NEW
@tools/sla_lib/tests/test_qr_gen.py — NEW
@tools/render_pipeline.py — patch L644-650 filter
@tools/check_stale_previews.py — patch L58 filter
@tools/visual_review/prompt_template.md — focus prompt for D10 pass
@templates/<slug>/build.py — conditional-inject + slot additions (5 templates)
@templates/<slug>/samples/manifest.yml — NEW (5 files)
@templates/_specs/<slug>.md — slot-table updates (5 files)
@reviews/visual-qa-demo-content.md — NEW review aggregate (Phase 5 output)
</context>

<commit_format>
Format: conventional with issue-id prefix (per .issues/config.yaml `commits.format: conventional, prefix: true`)
Pattern: `11: {type}({scope}): {description}`
Examples:
- `11: chore(deps): add qrcode + pyzbar to Dockerfile.claude`
- `11: fix(render): widen pipeline filter to include previews_for_sla templates`
- `11: feat(qr): add tools/qr_gen.py with deterministic branded QR rendering`
- `11: feat(codex): add Symbolfoto watermark + output-path recovery`
- `11: feat(falzflyer): wire 1 portrait + 3 themen-photos + 2 QR demo slots`
- `11: docs(specs): widen tent-card QR slot to 17 mm`
</commit_format>

<tasks>

<!-- =================================================================== -->
<!-- PHASE 1 — Tooling and deps (Tasks 1-5)                               -->
<!-- =================================================================== -->

<task type="auto">
  <id>task-1</id>
  <name>Task 1: Add Dockerfile dependencies (qrcode, pyzbar, libzbar0, zbar-tools)</name>
  <files>Dockerfile.claude</files>
  <action>
  Open `Dockerfile.claude`. Locate the existing pip-install layer (between L39-L48 per RESEARCH.md) and the existing `apt-get install` layer.

  Append to the apt-get layer (or add a new RUN layer before pip):

  ```dockerfile
  # pyzbar (QR decode for tests) needs libzbar0 at runtime; zbar-tools provides
  # the zbarimg CLI for shell-level smoke tests
  RUN apt-get update \
      && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
          libzbar0 zbar-tools \
      && apt-get clean && rm -rf /var/lib/apt/lists/*
  ```

  Append to the pip install layer:

  ```
  qrcode[pil]==8.2  pyzbar==0.1.9
  ```

  (Match existing layer style — single `pip install` line with multiple pinned packages, or extend the existing requirements list. Pillow is already pinned at 12.2.0 in the image — do NOT add it again.)

  **Container rebuild expected after PR merge** — flag this in the PR body. For the immediate execute session, the executor must run:

      pip install --break-system-packages 'qrcode[pil]==8.2' 'pyzbar==0.1.9'
      apt-get update && apt-get install -y --no-install-recommends libzbar0 zbar-tools

  Document this in the task's commit message body so the next builder knows what to do.

  Do NOT add Pillow as a new dependency — already present.
  </action>
  <verify>
    <automated>python3 -c "from importlib.metadata import version; import qrcode, pyzbar.pyzbar; print('qrcode', version('qrcode'), 'pyzbar OK')" && which zbarimg</automated>
  </verify>
  <done>
  - Dockerfile.claude includes the four new dependencies
  - In the current container session: `import qrcode` and `from pyzbar.pyzbar import decode` succeed
  - `zbarimg --version` works on the shell
  - PR body notes the rebuild requirement
  </done>
  <commit>11: chore(deps): add qrcode 8.2, pyzbar, libzbar0, zbar-tools to Dockerfile.claude</commit>
</task>

<task type="auto">
  <id>task-2</id>
  <name>Task 2: Patch render-pipeline filter to include previews_for_sla templates</name>
  <files>tools/render_pipeline.py, tools/check_stale_previews.py</files>
  <action>
  In `tools/render_pipeline.py` near L644-650, find the filter that selects which templates to round-trip / re-render. It currently reads `meta.get("original_sla")`. Widen it.

  Define (or inline) a helper:

  ```python
  def _is_renderable(meta: dict) -> bool:
      """Round-trip-against-original templates have `original_sla:`.
      DSL-only templates (no original to round-trip) have `previews_for_sla:` —
      a SHA tracking when previews were last regenerated. Either qualifies."""
      return bool(meta.get("original_sla")) or bool(meta.get("previews_for_sla"))
  ```

  Replace the filter expression with `_is_renderable(meta)`. Keep all other behavior identical.

  Apply the **same change shape** at `tools/check_stale_previews.py:58`. Either import the helper from render_pipeline.py OR duplicate the 4-line helper inline (the two scripts are independently invocable).

  Smoke-verify:
  - `bin/render-gallery themen-plakat-a3-quer` should now visit the template (vs. silently skipping). It should re-render `template.sla` + `preview.pdf` + `page-*.png` and emit a stable hash to `previews_for_sla` in `meta.yml` since `template.sla` is unchanged. Output: no diff vs committed bytes.
  - Same smoke-check for one round-trip template (e.g. `postkarte-a6-kampagne`) confirms the patch did not regress the original-sla path.

  Do NOT change `tools/spec_check.py` here — its template enumeration is independent.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates &amp;&amp; bin/render-gallery themen-plakat-a3-quer &amp;&amp; bin/render-gallery postkarte-a6-kampagne &amp;&amp; git diff --quiet templates/themen-plakat-a3-quer/template.sla templates/themen-plakat-a3-quer/preview.pdf templates/postkarte-a6-kampagne/template.sla templates/postkarte-a6-kampagne/preview.pdf</automated>
  </verify>
  <done>
  - Filter helper accepts both `original_sla:` and `previews_for_sla:`
  - `bin/render-gallery <dsl-only-template>` produces no spurious diff (template.sla unchanged -> bytes identical)
  - `bin/render-gallery <round-trip-template>` still works (no regression)
  - `bin/check-stale-previews` runs without raising
  </done>
  <commit>11: fix(render): widen pipeline filter to include previews_for_sla templates</commit>
</task>

<task type="auto" tdd="true">
  <id>task-3</id>
  <name>Task 3: Build tools/qr_gen.py with determinism + scannability tests</name>
  <files>tools/qr_gen.py, tools/sla_lib/tests/test_qr_gen.py</files>
  <behavior>
  - `generate_qr_png(url, path, **opts)` writes a PNG that `pyzbar.decode()` returns `url` for.
  - Two calls with identical inputs produce byte-identical PNGs (SHA-256 match).
  - Logo embed (ECC=H) does not break decode for any of the 6 URLs in the URL->Version table.
  - `parse_manifest()` is permissive: a manifest without `qr_codes:` returns `{"qr_codes": []}`.
  - CLI `python3 tools/qr_gen.py templates/<slug>` reads the manifest and writes every QR.
  </behavior>
  <action>
  Write `tools/qr_gen.py` per the `<interfaces>` block above. Use `qrcode[pil]==8.2`'s `StyledPilImage` + `SolidFillColorMask`. Save with `img.save(path, "PNG", optimize=True)` for byte-stable output.

  Reference snippet from research/ecosystem.md section 1:

  ```python
  qr = qrcode.QRCode(
      version=version,                                         # None = auto-fit
      error_correction=ECC_MAP[error_correction],
      box_size=box_size,
      border=border,
  )
  qr.add_data(target_url)
  qr.make(fit=True)
  kwargs = {
      "image_factory": StyledPilImage,
      "color_mask": SolidFillColorMask(
          front_color=tuple(module_color),
          back_color=tuple(background_color),
      ),
  }
  if embed_logo and embed_logo.exists():
      kwargs["embedded_image_path"] = str(embed_logo)
  img = qr.make_image(**kwargs)
  img.save(output_path, format="PNG", optimize=True)
  ```

  Implement `circular_mask(src_path, dst_path)` per the snippet in research/ecosystem.md section 4. Idempotent — call only if logo source isn't already pre-masked.

  Implement `parse_manifest(manifest_path)`:
  - Read YAML, return dict.
  - Missing `qr_codes:` key -> return `{...other keys..., "qr_codes": []}` (do NOT raise).
  - Missing `images:` key -> same treatment (so this function can be reused / share shape with codex_image_gen.parse_manifest).
  - Convert relative `output_path` to absolute against the manifest's parent dir.

  Implement `main(argv)`:
  - Accept a single positional arg: a directory containing `samples/manifest.yml` (or the manifest file itself).
  - Iterate `qr_codes:` entries; for each, call `generate_qr_png(...)` with the manifest values.
  - Print `OK <name> -> <path> (sha256=<first16>)` per generated file.
  - Return 0 on full success, 1 on any failure (collect all errors, print them all before returning).

  **Tests** in `tools/sla_lib/tests/test_qr_gen.py`:

  1. `test_generate_qr_decodes_with_pyzbar()` — for each of the 6 URLs in the table, generate a QR, decode via `pyzbar.decode()`, assert returned URL matches input.
  2. `test_qr_byte_determinism()` — generate same QR twice (different output paths), compare `hashlib.sha256(p1.read_bytes())` and `sha256(p2.read_bytes())`, assert equal.
  3. `test_qr_logo_embed_still_decodes()` — generate QR with `embed_logo=` pointing to a small synthetic green-circle PNG (build it on the fly via Pillow in the test setup), assert pyzbar still decodes correctly. ECC=H must absorb the occlusion.
  4. `test_parse_manifest_permissive()` — minimal manifest with only `slug:` parses; missing `qr_codes:` yields `{"qr_codes": []}`; missing `images:` yields `{"images": []}`.
  5. `test_cli_main_reads_manifest_and_writes_files()` — write a tmp manifest with one QR entry to a tmp dir; call `qr_gen.main([str(tmp_dir)])`; assert exit 0 and the output file exists + decodes.

  Use `tmp_path` pytest fixture. Pin `qrcode==8.2` and `Pillow==12.2.0` assumption in a module-level docstring; do NOT version-pin in test code.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates &amp;&amp; python3 -m pytest tools/sla_lib/tests/test_qr_gen.py -x -v</automated>
  </verify>
  <done>
  - `tools/qr_gen.py` exists, importable, exposes `generate_qr_png`, `circular_mask`, `parse_manifest`, `main`
  - All 5 tests pass
  - CLI: `python3 tools/qr_gen.py --help` prints usage; running on a manifest with no qr_codes is a no-op success
  - Module docstring documents pin requirements (qrcode==8.2, Pillow==12.2.0) and references RESEARCH.md
  </done>
  <commit>11: feat(qr): add tools/qr_gen.py with deterministic branded QR rendering + tests</commit>
</task>

<task type="auto" tdd="true">
  <id>task-4</id>
  <name>Task 4: Extend tools/codex_image_gen.py — stdin=DEVNULL fix + Symbolfoto watermark + output-path recovery</name>
  <files>tools/codex_image_gen.py, tools/sla_lib/tests/test_codex_image_gen.py</files>
  <behavior>
  - **CRITICAL FIRST FIX (stdin-block bug):** the existing `subprocess.run(cmd, capture_output=True, text=True, timeout=600)` call at `tools/codex_image_gen.py:124` does NOT pass `stdin=subprocess.DEVNULL`. Without it, codex blocks indefinitely on `Reading additional input from stdin...` when stdout is captured (non-tty stdin treated as "data may be coming"). Empirically validated 2026-05-08: hung 13 min before kill; reran with explicit `< /dev/null` redirect → succeeded in 2:10. **Add `stdin=subprocess.DEVNULL` to the subprocess.run call.** See `.issues/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates/research/codex-pipeline-validation.md` (commit 2e9a62e) for the validation log.
  - `add_demo_watermark(jpg_path)` overlays a bottom-center band with text `Symbolfoto — KI-generiert` onto the image (in-place re-encode). Default font Gotham Narrow Book if present, fallback to Pillow default. Band ~4% of image height, white text @ alpha 230 on black @ alpha 160 background.
  - `recover_codex_output(target_path, started_at=...)` scans `~/.codex/generated_images/` for files modified after `started_at`. If `target_path` already exists, return False (no-op). Else if a newer file exists, copy it to `target_path` and return True. Else return False.
  - `run_codex_for_image()` is updated: capture `t0 = time.time()` before subprocess, after subprocess if target missing call `recover_codex_output(target, started_at=t0)`. On success call `add_demo_watermark(target)`. PNG-source from codex is re-encoded to JPEG q=80 by Pillow before watermark (so the final committed file is `.jpg` per D6).
  - **Time budget per image (empirical, 2026-05-08):** ~2:10 (5s startup + 110s gen + 10s convert). Plan Phase 3 for ~15 min minimum on 6 images, up to 30 min with retries.
  </behavior>
  <action>
  Open `tools/codex_image_gen.py` (existing 235 LoC, untested). Add the two new module-level functions per the `<interfaces>` block above.

  **Implementation notes:**

  - `add_demo_watermark`: open with `Image.open(path).convert("RGB")`. Compute `band_h = max(40, int(H * band_height_pct))`. Draw filled rectangle on `ImageDraw.Draw(img, "RGBA")` for alpha to work. Load font: try `/usr/local/share/fonts/gruene/Gotham Narrow Book.otf` then DejaVuSans then `ImageFont.load_default()`. Font size: `H // 60` clamped to `[14, 36]`. Position via `draw.textbbox((0,0), text, font=font)`, center horizontally, vertically center inside the band (account for `bbox[1]` ascender offset per research/ecosystem.md section 3). Re-save as JPEG q=80 if path ends in `.jpg`/`.jpeg`, else preserve original format.

  - `recover_codex_output`: `started_at` defaults to `0.0` (any file). Walk `search_dir.glob("*.png")`. Filter `f.stat().st_mtime >= started_at`. Sort by mtime descending; pick the newest. `shutil.copy2(newest, target_path)`. Use `try/except FileNotFoundError` if `search_dir` doesn't exist -> return False.

  - **Wire into `run_codex_for_image`:** capture `t0 = time.time()` immediately before `subprocess.run`. After return, if `output_path.exists()` is False AND `recover_codex_output(output_path, started_at=t0)` returns True, log `"recovered from ~/.codex/generated_images/"` and proceed. After successful output:
    - If file is PNG and target ends in `.jpg`/`.jpeg`: open with Pillow, re-save as JPEG q=80 to target path, delete the original PNG.
    - Then call `add_demo_watermark(target_path)`.
    - Skip watermark if image_spec has `synthetic: false` OR `watermark: false` (escape hatch for future non-portrait themen-photos that aren't synthetic — but current scope: all our images are synthetic -> watermark always fires).

  **Tests** in `tools/sla_lib/tests/test_codex_image_gen.py`:

  1. `test_add_demo_watermark_overlays_caption()` — create a synthetic 1024x1536 grey PNG via Pillow, call `add_demo_watermark`, assert output JPEG exists, has same dimensions, mean-brightness lower in the bottom 5% rows than in the middle 50% rows (proves band rendered).
  2. `test_add_demo_watermark_uses_fallback_font_when_gotham_missing()` — monkeypatch the Gotham path to a non-existent path, assert `add_demo_watermark` still completes without raising.
  3. `test_recover_codex_output_copies_newest_file()` — create `tmp_search_dir/`, write a fake `<UUID>.png` with mtime in the future, call `recover_codex_output(tmp_target, search_dir=tmp_search_dir, started_at=0.0)`, assert returns True and `tmp_target.exists()`.
  4. `test_recover_codex_output_returns_false_when_target_already_exists()` — pre-create `tmp_target`, assert recover returns False without overwriting.
  5. `test_recover_codex_output_returns_false_when_no_newer_file()` — create file with mtime=0 in search_dir, call recover with `started_at=time.time()`, assert returns False.
  6. `test_parse_manifest_handles_qr_codes_key()` — assert that the existing `parse_manifest` (in this module) does NOT raise when `qr_codes:` is present — it should ignore unknown keys and only return the `images:` list. (This documents the cross-tool boundary.)

  Do NOT call codex itself in tests — mock subprocess in any test that touches `run_codex_for_image`.

  Acceptance criterion #2 from ISSUE.md ("end-to-end-getestet mit echtem Codex-Call (nicht mehr nur dry-run wie in #10)") is satisfied at the **execute-phase generation step** (Task 9), not in unit tests. This task delivers the test scaffolding and post-process logic.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates &amp;&amp; python3 -m pytest tools/sla_lib/tests/test_codex_image_gen.py -x -v</automated>
  </verify>
  <done>
  - `add_demo_watermark` and `recover_codex_output` exist as module-level functions
  - `run_codex_for_image` wired to call both at the right points
  - All 7 tests pass (6 above + 1 new for stdin=DEVNULL)
  - **`subprocess.run(...)` has `stdin=subprocess.DEVNULL`** — verifiable with grep
  - Watermark text is `Symbolfoto — KI-generiert` (NOT `— Demo`) for EU AI Act forward-compat
  - Defaults match `<interfaces>` (band 4%, font fallback chain, position bottom-center)

  **Additional test #7:**
  ```python
  def test_subprocess_run_passes_devnull_stdin(monkeypatch):
      """Regression: codex blocks on stdin without DEVNULL (validated 2026-05-08)."""
      from unittest import mock
      captured = {}
      def fake_run(cmd, **kw):
          captured.update(kw)
          import subprocess
          return mock.Mock(returncode=0, stdout='', stderr='')
      monkeypatch.setattr('tools.codex_image_gen.subprocess.run', fake_run)
      # Trigger generate_image / run_codex_for_image
      ...
      import subprocess
      assert captured.get('stdin') == subprocess.DEVNULL, "MUST pass stdin=DEVNULL or codex hangs"
  ```
  </done>
  <commit>11: feat(codex): stdin=DEVNULL fix + Symbolfoto watermark + output-path recovery</commit>
</task>

<task type="auto">
  <id>task-5</id>
  <name>Task 5: Author shared/logos/sonnenblume-circle.png (pre-masked logo for QR embed)</name>
  <files>shared/logos/sonnenblume-circle.png, shared/logos/README.md</files>
  <action>
  Create a circular pre-masked logo PNG for QR center-embed. Source: existing Grünen sonnenblume placeholder logo in `shared/logos/` (or wherever Issue #10 placed it — locate via `find shared/logos/ -name '*.png' -o -name '*.svg'`).

  Approach:
  - Use Pillow + the new `circular_mask()` from `tools/qr_gen.py`.
  - Output: 200x200 PNG, RGBA, monochrome Dunkelgrün (28, 72, 33) on transparent background.
  - **Monochrome, not full-color** — research/ecosystem.md section 4 ("monochrome blends into QR's color story; full-color introduces yellow that may fool naive scanners").
  - If existing source is full-color: convert to monochrome first via Pillow (`ImageOps.grayscale` then re-tint to Dunkelgrün, or threshold + flood-fill).

  One-shot script at the top of the task (or inline `python3 -c "..."` invocation) writes the file. Commit the resulting PNG.

  Update `shared/logos/README.md` (create if missing) noting:
  - `sonnenblume-circle.png` is for QR center-embed (D1)
  - 200x200, alpha=0 outside circle, monochrome Dunkelgrün
  - Used by `tools/qr_gen.py` via `embed_logo:` manifest field

  Test scannability of the embed: pick any URL from the table, generate a QR with this logo embedded via `qr_gen.generate_qr_png(...)`, decode with pyzbar, assert URL matches. Add this as a one-off manual smoke step (not a unit test — the unit-test for logo embed in Task 3 already covers the principle with a synthetic green circle).
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates &amp;&amp; python3 -c "
from PIL import Image
img = Image.open('shared/logos/sonnenblume-circle.png').convert('RGBA')
assert img.size == (200, 200), img.size
assert img.getpixel((0, 0))[3] == 0, 'top-left should be transparent'
assert img.getpixel((100, 100))[3] &gt; 200, 'center should be opaque'
print('OK')
" &amp;&amp; python3 -c "
from pathlib import Path
from tools.qr_gen import generate_qr_png
from pyzbar.pyzbar import decode
from PIL import Image
import tempfile
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / 'qr.png'
    generate_qr_png('https://noe.gruene.at/mitmachen/', out, embed_logo=Path('shared/logos/sonnenblume-circle.png'))
    decoded = decode(Image.open(out))
    assert decoded and decoded[0].data.decode() == 'https://noe.gruene.at/mitmachen/', decoded
    print('OK scannable with logo')
"</automated>
  </verify>
  <done>
  - `shared/logos/sonnenblume-circle.png` is 200x200 RGBA, transparent corners, monochrome Dunkelgrün
  - `shared/logos/README.md` documents the file
  - Smoke-decode confirms scannability with logo embedded at ECC=H
  </done>
  <commit>11: feat(assets): add sonnenblume-circle logo for QR center-embed</commit>
</task>

<!-- =================================================================== -->
<!-- PHASE 2 — Manifests + slot additions (Tasks 6-7)                     -->
<!-- =================================================================== -->

<task type="auto">
  <id>task-6</id>
  <name>Task 6: Manifests + build.py + spec for the 2 QR-only templates (postkarte, türanhänger)</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/samples/manifest.yml, templates/wahlaufruf-postkarte-a6-quer/build.py, templates/_specs/wahlaufruf-postkarte-a6-quer.md, templates/wahltag-tueranhaenger/samples/manifest.yml, templates/wahltag-tueranhaenger/build.py, templates/_specs/wahltag-tueranhaenger.md</files>
  <action>
  Two templates that need only a QR slot (no Codex-generated images).

  **For `wahlaufruf-postkarte-a6-quer`:**

  1. Create `templates/wahlaufruf-postkarte-a6-quer/samples/manifest.yml`:
     ```yaml
     slug: wahlaufruf-postkarte-a6-quer
     images: []
     qr_codes:
       - name: qr-back
         target_url: https://noe.gruene.at/
         output_path: samples/qr-back.png
         module_color: [28, 72, 33]
         background_color: [255, 255, 255]
         embed_logo: shared/logos/sonnenblume-circle.png
         error_correction: H
         box_size: 10
         border: 4
         note: "Demo URL — endusers replace with their voting-info URL"
     ```

  2. Edit `templates/wahlaufruf-postkarte-a6-quer/build.py`:
     - Add a QR `ImageFrame` slot on the back side. Position from spec (Postkarte ~25 mm slot — current spec at `templates/_specs/wahlaufruf-postkarte-a6-quer.md` may already mention placement; if not, choose a centered position on the back side, ~25x25 mm).
     - **Conditional inject:** at the top of `build()` (or just before the ImageFrame is constructed), check:
       ```python
       qr_path = HERE / "samples" / "qr-back.png"
       qr_data, qr_ext = (None, None)
       if qr_path.exists():
           with open(qr_path, "rb") as f:
               qr_data, qr_ext = pack_inline_image(f.read(), "png")
       ```
     - Pass `inline_image_data=qr_data, inline_image_ext=qr_ext` to the ImageFrame. Empty slot if no samples committed.
     - Match existing import / pattern style in this `build.py`.

  3. Update `templates/_specs/wahlaufruf-postkarte-a6-quer.md`:
     - Add a row to the slot-table for `qr-back` (size 25x25 mm, position centered-back, optional, Demo-URL `https://noe.gruene.at/`).
     - Run `python3 tools/spec_check.py templates/wahlaufruf-postkarte-a6-quer` — must be green.

  **For `wahltag-tueranhaenger`:**

  Same pattern, with these substitutions:
  - URL: `https://noe.gruene.at/themen/`
  - `note:` "Demo URL — endusers replace with their lokale Listen-URL"
  - QR slot position: back side per the existing spec (Türanhänger has a portrait slot already; QR goes near bottom of back).
  - QR slot size: ~30 mm (slightly larger because the URL needs version 4 = 33 modules; 30 mm / 33 = 0.91 mm/module, comfortably above D1's 0.5 mm).

  Do NOT generate the QR PNGs in this task — Task 8 handles generation. This task wires in the slots + manifests so that **once Task 8 commits the bytes, the conditional inject lights up automatically**.

  After the build.py edits, smoke-run `python3 templates/wahlaufruf-postkarte-a6-quer/build.py` (or whatever the project's per-template smoke command is — see existing `templates/_smoke/`). It must succeed, generating a `template.sla` with an empty QR ImageFrame slot. `bin/render-gallery wahlaufruf-postkarte-a6-quer` must succeed and produce a stable rendering with empty slot.

  Same smoke for türanhänger.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates &amp;&amp; python3 tools/spec_check.py templates/wahlaufruf-postkarte-a6-quer &amp;&amp; python3 tools/spec_check.py templates/wahltag-tueranhaenger &amp;&amp; bin/render-gallery wahlaufruf-postkarte-a6-quer &amp;&amp; bin/render-gallery wahltag-tueranhaenger &amp;&amp; python3 -m pytest templates/_smoke/ -x -v</automated>
  </verify>
  <done>
  - 2 manifests created with `qr_codes:` block
  - 2 build.py extended with conditional-inject QR ImageFrame
  - 2 spec.md slot-tables include the new QR slot
  - `tools/spec_check.py` green for both templates
  - `bin/render-gallery` succeeds for both (empty slot — generation in Task 8)
  - smoke tests pass
  </done>
  <commit>11: feat(postkarte+tueranhaenger): wire QR-back slots with conditional inject + manifests</commit>
</task>

<task type="auto">
  <id>task-7</id>
  <name>Task 7: Manifests + build.py + spec for the 3 portrait/photo-bearing templates (falzflyer, themen-plakat, tent-card)</name>
  <files>templates/kandidat-falzflyer-din-lang/samples/manifest.yml, templates/kandidat-falzflyer-din-lang/build.py, templates/_specs/kandidat-falzflyer-din-lang.md, templates/themen-plakat-a3-quer/samples/manifest.yml, templates/themen-plakat-a3-quer/build.py, templates/_specs/themen-plakat-a3-quer.md, templates/infostand-tent-card-a5-quer/samples/manifest.yml, templates/infostand-tent-card-a5-quer/build.py, templates/_specs/infostand-tent-card-a5-quer.md</files>
  <action>
  Three templates that need both Codex images AND QRs (or where slots/sizes need extending).

  **For `kandidat-falzflyer-din-lang`** (existing: 1 portrait + 1 QR; ADD: 3 themen-photos + 2nd QR):

  1. Create `templates/kandidat-falzflyer-din-lang/samples/manifest.yml`:
     ```yaml
     slug: kandidat-falzflyer-din-lang
     images:
       - name: portrait-cover
         output_path: samples/portrait-cover.jpg
         prompt: |
           Documentary photograph of a Central European woman in her mid-40s,
           head-and-shoulders portrait, soft afternoon window light from camera left,
           neutral grey-green out-of-focus background, 50mm lens, shallow depth of field,
           visible pores and natural skin texture, warm color balance, slightly desaturated greens.
           Documentary, unposed, gaze slightly past camera, half-smile.
           No watermark. No text overlays. No logos or trademarks. No glamorization. No heavy retouching.
         size: "1024x1536"
         synthetic: true
         note: "synthetic, demo-only — replace with real candidate photo"
         model: gpt-image-2          # informational
         quality: high               # informational
       - name: themen-klimaschutz
         output_path: samples/themen-klimaschutz.jpg
         prompt: |
           Documentary photograph, landscape orientation, of a rooftop solar installation
           on a Niederösterreich farmhouse with vineyards in the background, golden-hour light,
           24mm lens, natural color balance, slightly desaturated greens. Authentic and unposed.
           No watermark. No text overlays. No logos or trademarks.
         size: "1536x1024"
         synthetic: true
         note: "synthetic, demo-only — replace with real local photo"
       - name: themen-soziales
         output_path: samples/themen-soziales.jpg
         prompt: |
           Documentary photograph, landscape, of a Wiener Kaffeehaus interior with brass fittings,
           two patrons in conversation at a wooden booth (faces not toward camera), late-afternoon
           window light, 35mm lens, warm tones. Authentic and unposed.
           No watermark. No text overlays. No logos or trademarks.
         size: "1536x1024"
         synthetic: true
         note: "synthetic, demo-only"
       - name: themen-bildung
         output_path: samples/themen-bildung.jpg
         prompt: |
           Documentary photograph, landscape, of a small-town Austrian schoolyard with children
           (faces obscured / motion blur), Niederösterreich Dorfstraße in the background,
           overcast diffused daylight, 35mm lens, natural colors. Authentic, unposed.
           No watermark. No text overlays. No logos or trademarks.
         size: "1536x1024"
         synthetic: true
         note: "synthetic, demo-only"
     qr_codes:
       - name: qr-mitmachen
         target_url: https://noe.gruene.at/mitmachen/
         output_path: samples/qr-mitmachen.png
         module_color: [28, 72, 33]
         embed_logo: shared/logos/sonnenblume-circle.png
         error_correction: H
         box_size: 10
         border: 4
         note: "Demo URL — endusers replace with Bezirks-URL"
       - name: qr-termine
         target_url: https://noe.gruene.at/termine/
         output_path: samples/qr-termine.png
         module_color: [28, 72, 33]
         embed_logo: shared/logos/sonnenblume-circle.png
         error_correction: H
         box_size: 10
         border: 4
         note: "Demo URL — endusers replace with Termine-URL"
     ```

  2. Edit `templates/kandidat-falzflyer-din-lang/build.py`:
     - Existing portrait + QR1 slots: wrap their inline-image-data construction in the conditional-inject pattern (`if (HERE / "samples" / "<file>").exists()`).
     - **Add 3 new ImageFrame slots** for `themen-klimaschutz`, `themen-soziales`, `themen-bildung` on the middle spread panels (~85x60 mm landscape each per ISSUE.md). Position them per the falzflyer's 3-panel inner spread — likely in the spec already; if spec doesn't enumerate them, add them at logical positions (left-panel, mid-panel, right-panel inner spread).
     - Add a 2nd QR slot (`qr-termine`) on the closer panel near `qr-mitmachen`.
     - All inject paths conditional.

  3. Update `templates/_specs/kandidat-falzflyer-din-lang.md`:
     - Slot-table: add 3 themen-photo rows (~85x60 mm each, landscape, optional, demo-only).
     - Slot-table: add `qr-termine` row.
     - `tools/spec_check.py` green.

  **For `themen-plakat-a3-quer`** (no image slots beyond logo today; ADD optional themen-photo + QR):

  1. Manifest:
     ```yaml
     slug: themen-plakat-a3-quer
     images:
       - name: themen-hero
         output_path: samples/themen-hero.jpg
         prompt: |
           Documentary photograph, landscape orientation, of a Niederösterreich
           wind-turbine on a rolling hill at golden hour, mid-distance framing, 35mm lens,
           natural color balance, slightly desaturated greens, warm afternoon palette.
           Authentic and unposed.
           No watermark. No text overlays. No logos or trademarks.
         size: "1536x1024"
         synthetic: true
         note: "synthetic, demo-only — replace with real local Klimaschutz/Energie photo"
     qr_codes:
       - name: qr-quelle
         target_url: https://noe.gruene.at/themen/         # FALLBACK from /themen/klimaschutz/ which 404s
         output_path: samples/qr-quelle.png
         module_color: [28, 72, 33]
         embed_logo: shared/logos/sonnenblume-circle.png
         error_correction: H
         box_size: 10
         border: 4
         note: "Demo URL (fallback from /themen/klimaschutz/ which returned 404 on 2026-05-08)"
     ```

  2. Edit `build.py`:
     - Add an optional themen-hero ImageFrame slot (large landscape, ~270x180 mm — about half the plakat width).
     - Add a small QR slot (~30 mm) at a corner.
     - Both conditional-inject.

  3. Update spec slot-table.

  **For `infostand-tent-card-a5-quer`** (QR slot in spec only at 14 mm — TOO SMALL; ADD ImageFrame in build.py + ENLARGE to >=17 mm):

  1. Manifest:
     ```yaml
     slug: infostand-tent-card-a5-quer
     images:
       - name: hintergrund-mitmachen
         output_path: samples/hintergrund-mitmachen.jpg
         prompt: |
           Documentary photograph, landscape, of a Grüne Niederösterreich Infostand
           on a small-town square, group of people in mid-conversation around a table
           with leaflets (no logos or party banners visible), bright overcast daylight,
           35mm lens, authentic and candid. Faces partially obscured.
           No watermark. No text overlays. No logos or trademarks.
         size: "1536x1024"
         synthetic: true
         note: "synthetic, demo-only — optional Hintergrund auf Mitmachen-Seite"
     qr_codes:
       - name: qr-mitmachen
         target_url: https://noe.gruene.at/mitmachen/
         output_path: samples/qr-mitmachen.png
         module_color: [28, 72, 33]
         embed_logo: shared/logos/sonnenblume-circle.png
         error_correction: H
         box_size: 10
         border: 4
         note: "Demo URL — endusers replace"
     ```

  2. Edit `build.py`:
     - **Add a QR ImageFrame** (currently the QR is referenced in spec only — the build doesn't emit the slot). Position: front-back-of-tent, on the Mitmachen side.
     - **Enlarge from 14x14 mm to 17x17 mm** (research finding — 14 mm violates D1 0.5 mm/module rule; 17 mm at version 4 = 0.51 mm/module, just above threshold).
     - Add optional Hintergrund-mitmachen ImageFrame (background photo on the Mitmachen side, behind the text — `scale_type=1, ratio=1`).
     - Both conditional-inject.

  3. Update `templates/_specs/infostand-tent-card-a5-quer.md` line 197 area:
     - Change QR slot dimensions from `14x14 mm` to `17x17 mm` with a brief note: "Enlarged 2026-05-08 per Issue #11 to satisfy D1 module-size minimum (0.5 mm/module) for ECC=H QRs encoding `noe.gruene.at/mitmachen/` (33 modules)."
     - Add the Hintergrund-mitmachen slot row.

  After all three: smoke-run each `build.py` (no samples committed yet -> empty slots) and confirm `bin/render-gallery` succeeds for each. `tools/spec_check.py` green for all three.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates &amp;&amp; python3 tools/spec_check.py templates/kandidat-falzflyer-din-lang &amp;&amp; python3 tools/spec_check.py templates/themen-plakat-a3-quer &amp;&amp; python3 tools/spec_check.py templates/infostand-tent-card-a5-quer &amp;&amp; bin/render-gallery kandidat-falzflyer-din-lang &amp;&amp; bin/render-gallery themen-plakat-a3-quer &amp;&amp; bin/render-gallery infostand-tent-card-a5-quer &amp;&amp; python3 -m pytest templates/_smoke/ -x -v</automated>
  </verify>
  <done>
  - 3 manifests created with `images:` and `qr_codes:` blocks
  - 3 build.py: 7 new ImageFrame slots wired (3 themen-photos in falzflyer, 1 themen-hero + 1 QR in themen-plakat, 1 hintergrund + 1 QR ImageFrame emit in tent-card), all conditional-inject. Existing slots refactored to conditional-inject.
  - tent-card QR slot enlarged to 17 mm in build.py
  - 3 spec.md slot-tables updated; tent-card spec includes the size-change note
  - `tools/spec_check.py` green for all three templates
  - `bin/render-gallery` succeeds for all three (empty slots — generation in Tasks 8/9)
  - smoke tests pass
  </done>
  <commit>11: feat(falzflyer+themen-plakat+tent-card): wire portrait/themen/QR slots + enlarge tent-card QR to 17mm</commit>
</task>

<!-- =================================================================== -->
<!-- PHASE 3 — Generation (Tasks 8-9)                                     -->
<!-- =================================================================== -->

<task type="auto">
  <id>task-8</id>
  <name>Task 8: Generate all QR PNGs (deterministic, fast)</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/samples/qr-back.png, templates/wahltag-tueranhaenger/samples/qr-back.png, templates/kandidat-falzflyer-din-lang/samples/qr-mitmachen.png, templates/kandidat-falzflyer-din-lang/samples/qr-termine.png, templates/themen-plakat-a3-quer/samples/qr-quelle.png, templates/infostand-tent-card-a5-quer/samples/qr-mitmachen.png</files>
  <action>
  Run the QR generator across all 5 manifests (the postkarte and türanhänger were Task 6's manifests; the falzflyer/themen-plakat/tent-card were Task 7's).

  For each manifest:
  ```
  python3 tools/qr_gen.py templates/<slug>
  ```

  This reads `samples/manifest.yml` and writes each `qr_codes:` entry to its `output_path`.

  **Verify each file:**
  - Exists at the expected path
  - Decodes via pyzbar to the exact `target_url` from the manifest
  - SHA-256 stable across two re-runs (proves D9 determinism in this image)

  Inline verification command pattern:
  ```python
  from pathlib import Path; from pyzbar.pyzbar import decode; from PIL import Image; import yaml
  for slug in ["wahlaufruf-postkarte-a6-quer","wahltag-tueranhaenger","kandidat-falzflyer-din-lang","themen-plakat-a3-quer","infostand-tent-card-a5-quer"]:
      m = yaml.safe_load((Path("templates")/slug/"samples"/"manifest.yml").read_text())
      for q in m.get("qr_codes", []):
          out = Path("templates")/slug/q["output_path"]
          assert out.exists(), f"missing {out}"
          decoded = decode(Image.open(out))
          assert decoded and decoded[0].data.decode() == q["target_url"], f"{out}: {decoded}"
          print(f"OK {slug}/{q['name']} -> {q['target_url']}")
  ```

  All 6 QR PNGs commit to repo (deterministic, byte-stable, same SHA on re-run).
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates &amp;&amp; for slug in wahlaufruf-postkarte-a6-quer wahltag-tueranhaenger kandidat-falzflyer-din-lang themen-plakat-a3-quer infostand-tent-card-a5-quer; do python3 tools/qr_gen.py templates/$slug || exit 1; done &amp;&amp; python3 -c "
from pathlib import Path
from pyzbar.pyzbar import decode
from PIL import Image
import yaml
for slug in ['wahlaufruf-postkarte-a6-quer','wahltag-tueranhaenger','kandidat-falzflyer-din-lang','themen-plakat-a3-quer','infostand-tent-card-a5-quer']:
    m = yaml.safe_load((Path('templates')/slug/'samples'/'manifest.yml').read_text())
    for q in m.get('qr_codes', []):
        out = Path('templates')/slug/q['output_path']
        assert out.exists(), f'missing {out}'
        d = decode(Image.open(out))
        assert d and d[0].data.decode() == q['target_url'], f'{out}: {d}'
        print(f'OK {slug}/{q[\"name\"]} -> {q[\"target_url\"]}')
"</automated>
  </verify>
  <done>
  - 6 QR PNGs exist, all decode to the manifest's `target_url`
  - Re-running `qr_gen.py` produces byte-identical output (no diff in `git status`)
  - All PNGs committed
  </done>
  <commit>11: feat(qr): generate 6 deterministic branded QR PNGs for 5 templates</commit>
</task>

<task type="auto">
  <id>task-9</id>
  <name>Task 9: Generate Codex portraits + themen-photos (5-6 calls, cap 5 iters per slot)</name>
  <files>templates/kandidat-falzflyer-din-lang/samples/portrait-cover.jpg, templates/kandidat-falzflyer-din-lang/samples/themen-klimaschutz.jpg, templates/kandidat-falzflyer-din-lang/samples/themen-soziales.jpg, templates/kandidat-falzflyer-din-lang/samples/themen-bildung.jpg, templates/themen-plakat-a3-quer/samples/themen-hero.jpg, templates/infostand-tent-card-a5-quer/samples/hintergrund-mitmachen.jpg</files>
  <action>
  Run the Codex image-generation pipeline across the 3 image-bearing manifests.

  **Pre-flight:**
  1. `codex login status` -> "Logged in using ChatGPT" (already provisioned; no action needed if green)
  2. `codex features list | grep image_generation` -> must show `stable true`
  3. **Smoke test first** (research/ecosystem.md section 2 R4): one throwaway image-gen call to verify the `image_gen` tool fires end-to-end before iterating real prompts. Discard the output.

  **Real generation:**

  For each of the 3 templates with `images:` in their manifest:

  ```
  python3 tools/codex_image_gen.py templates/<slug>
  ```

  This iterates `images:` entries. For each: builds the prompt, runs `codex exec`, recovers from `~/.codex/generated_images/` if codex saved there instead, re-encodes PNG -> JPEG q=80, applies the `Symbolfoto — KI-generiert` watermark via Pillow, writes to `output_path`.

  **Iteration cap (D7):** max **5 attempts per slot**. If a slot fails after 5 attempts (content-policy refusal, output drift, model hang) — log it, accept the empty slot, and add a manifest entry: `note: "generation failed 2026-05-08, manual fallback needed"`.

  **Brauchbarkeitskriterien (D7):** the executor judges "good enough" per slot (not multi-model gates — D10 single-pass is at the end). Criteria:
  - Halbportrait, kein Ganzkörper, kein Pop-Art-Stil
  - Hintergrund unkonkret (kein erkennbares Logo, keine Brand-Konkurrenz)
  - Kein offensichtlich künstliches Gesicht (Uncanny Valley)
  - Kleidung neutral (kein anderes Parteilogo, keine Sport-Trikots)
  - Watermark `Symbolfoto — KI-generiert` is legibly rendered (not garbled, not in wrong position)

  **6 expected outputs (D8):**
  - falzflyer: 1 portrait + 3 themen-photos = 4 calls
  - themen-plakat: 1 themen-hero = 1 call
  - tent-card: 1 hintergrund-mitmachen = 1 call

  **Cost ceiling:** ChatGPT-account auth -> subscription quota burn, no per-image USD cost. Worst-case 5 attempts x 6 slots = 30 image-gen calls. Well under any realistic ceiling. Skip the cost-budget concern.

  **After generation:** every JPEG must be:
  - Present at the manifest's `output_path`
  - Have the bottom watermark band visible (Pillow `Image.open(...).getpixel((W//2, H-band_h//2))` returns dark/non-white)
  - Pillow can open and verify dimensions (1024x1536 portrait or 1536x1024 landscape)

  All JPEGs committed.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates &amp;&amp; for slug in kandidat-falzflyer-din-lang themen-plakat-a3-quer infostand-tent-card-a5-quer; do python3 tools/codex_image_gen.py templates/$slug || exit 1; done &amp;&amp; python3 -c "
from pathlib import Path
from PIL import Image
import yaml
expected = {'kandidat-falzflyer-din-lang': 4, 'themen-plakat-a3-quer': 1, 'infostand-tent-card-a5-quer': 1}
for slug, n in expected.items():
    m = yaml.safe_load((Path('templates')/slug/'samples'/'manifest.yml').read_text())
    images = m.get('images', [])
    assert len(images) == n, f'{slug}: expected {n} images, manifest has {len(images)}'
    for img_spec in images:
        out = Path('templates')/slug/img_spec['output_path']
        if not out.exists():
            print(f'NOTE {slug}/{img_spec[\"name\"]}: SKIPPED (5-iter cap hit, manifest should note failure)')
            continue
        with Image.open(out) as im:
            w, h = im.size
            assert (w, h) in [(1024, 1536), (1536, 1024), (1024, 1024)], f'{out}: unexpected size {(w,h)}'
            band_top = h * 95 // 100
            mid_top, mid_bot = h * 30 // 100, h * 70 // 100
            band = im.crop((0, band_top, w, h)).convert('L')
            mid = im.crop((0, mid_top, w, mid_bot)).convert('L')
            band_mean = sum(band.getdata()) / (band.width * band.height)
            mid_mean = sum(mid.getdata()) / (mid.width * mid.height)
            assert band_mean &lt; mid_mean, f'{out}: bottom band ({band_mean:.0f}) not darker than middle ({mid_mean:.0f}) — watermark missing?'
        print(f'OK {slug}/{img_spec[\"name\"]} -&gt; {out} ({w}x{h}, watermark detected)')
"</automated>
  </verify>
  <done>
  - All 6 expected JPEGs present (or manifest documents which failed at iter-cap)
  - Each JPEG has the bottom watermark band detected by brightness comparison
  - Sizes match `gpt-image-2` documented sizes (1024x1536 portrait or 1536x1024 landscape)
  - All committed
  - Any failed slots have manifest `note:` describing the failure
  </done>
  <commit>11: feat(codex): generate Symbolfoto-watermarked portrait + themen-photos for 3 templates</commit>
</task>

<!-- =================================================================== -->
<!-- PHASE 4 — Render + commit galleries (Task 10)                        -->
<!-- =================================================================== -->

<task type="auto">
  <id>task-10</id>
  <name>Task 10: Re-render galleries for 5 templates with embedded demo content</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/template.sla, templates/wahlaufruf-postkarte-a6-quer/preview.pdf, templates/wahlaufruf-postkarte-a6-quer/page-*.png, templates/wahlaufruf-postkarte-a6-quer/meta.yml, templates/wahltag-tueranhaenger/template.sla, templates/wahltag-tueranhaenger/preview.pdf, templates/wahltag-tueranhaenger/page-*.png, templates/wahltag-tueranhaenger/meta.yml, templates/kandidat-falzflyer-din-lang/template.sla, templates/kandidat-falzflyer-din-lang/preview.pdf, templates/kandidat-falzflyer-din-lang/page-*.png, templates/kandidat-falzflyer-din-lang/meta.yml, templates/themen-plakat-a3-quer/template.sla, templates/themen-plakat-a3-quer/preview.pdf, templates/themen-plakat-a3-quer/page-*.png, templates/themen-plakat-a3-quer/meta.yml, templates/infostand-tent-card-a5-quer/template.sla, templates/infostand-tent-card-a5-quer/preview.pdf, templates/infostand-tent-card-a5-quer/page-*.png, templates/infostand-tent-card-a5-quer/meta.yml</files>
  <action>
  With QR PNGs (Task 8) and Codex JPEGs (Task 9) committed, re-run the gallery render across all 5 new templates. The conditional-inject in each `build.py` now lights up because `samples/<file>` exists.

  ```
  for slug in wahlaufruf-postkarte-a6-quer wahltag-tueranhaenger kandidat-falzflyer-din-lang themen-plakat-a3-quer infostand-tent-card-a5-quer; do
      bin/render-gallery $slug
  done
  ```

  Each invocation:
  - Re-runs build.py -> fresh `template.sla` with `inline_image_data` for every populated slot
  - Re-runs Scribus -> fresh `preview.pdf` + `page-*.png`
  - Updates `meta.yml::previews_for_sla` with the new template.sla SHA

  **Sanity-check the rendered PNGs by eye (or scripted brightness/structural checks):**
  - postkarte: back side shows green QR with white logo center
  - türanhänger: back-bottom shows green QR
  - falzflyer: cover panel shows watermarked portrait; 3 inner panels show 3 different watermarked themen-photos; closer panel shows 2 QRs side-by-side
  - themen-plakat: large landscape themen-photo with watermark visible; corner QR
  - tent-card: Mitmachen side shows hintergrund-photo with watermark + QR

  **Verify check_stale_previews is green for ALL 8 templates:**
  ```
  bin/check-stale-previews
  ```

  Expected output: green/0-exit. The 5 new templates now have fresh `previews_for_sla` SHAs that match the just-rendered `template.sla`. The 3 existing round-trip templates remain green (Task 2's filter widening was additive).

  **Verify `tools/check_ci.py` is green for all 8 templates** (project's combined CI gate):
  ```
  python3 tools/check_ci.py
  ```

  Commit all rendered artifacts (template.sla, preview.pdf, page-*.png, meta.yml updates) in one atomic commit per template OR one combined commit — match the existing PR #20 commit pattern.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates &amp;&amp; for slug in wahlaufruf-postkarte-a6-quer wahltag-tueranhaenger kandidat-falzflyer-din-lang themen-plakat-a3-quer infostand-tent-card-a5-quer; do bin/render-gallery $slug || exit 1; done &amp;&amp; bin/check-stale-previews &amp;&amp; python3 tools/check_ci.py</automated>
  </verify>
  <done>
  - 5 templates re-rendered; each has fresh template.sla with inline-encoded demo bytes
  - preview.pdf + page-*.png updated visibly showing portraits/themen-photos/QRs
  - meta.yml::previews_for_sla SHA matches the fresh template.sla
  - `bin/check-stale-previews` green for all 8 templates
  - `tools/check_ci.py` green
  </done>
  <commit>11: feat(gallery): re-render 5 new templates with embedded demo content</commit>
</task>

<!-- =================================================================== -->
<!-- PHASE 5 — Single visual review pass (Tasks 11-12)                    -->
<!-- =================================================================== -->

<task type="auto">
  <id>task-11</id>
  <name>Task 11: Run single visual-review pass with focused prompt (D10)</name>
  <files>tools/visual_review/prompt_template.md, reviews/visual-qa-demo-content.md</files>
  <action>
  This is the quality gate for the demo content. **No multi-gate setup like Issue #10** — D10 specifies a single visual-review pass focused on the comparative question.

  1. **Customize the prompt template at `tools/visual_review/prompt_template.md`** (or create an issue-specific copy at `tools/visual_review/prompts/11-demo-content.md` — match the existing project convention; if the file is shared and used by other issues, copy-not-edit). Focus the prompt on:

  ```
  Vergleiche die übergebenen Galerie-Previews der 5 neuen Templates (kandidat-falzflyer-din-lang,
  themen-plakat-a3-quer, infostand-tent-card-a5-quer, wahlaufruf-postkarte-a6-quer, wahltag-tueranhaenger)
  mit der vorherigen Version (Platzhalter-Slots, leere QR-Bereiche).

  Zentrale Frage: Sehen die neuen Templates mit echten Bildern + funktionalen QRs sichtbar besser aus
  als die Platzhalter-Version? Falls ja, wo am stärksten? Falls nein, was stört?

  Spezifische Prüfpunkte:
  1. Portrait + Themen-Fotos im falzflyer:
     - Brand-konform (österreichischer Kontext, nicht US-Suburbia, nicht Stockfoto-generisch)?
     - Diversity über Themen-Fotos hinweg?
     - "Symbolfoto — KI-generiert" Watermark legibel ABER unaufdringlich?
  2. QR-Codes:
     - Visuell gut integriert in das Brand-Layout?
     - Logo-Embed funktioniert (sichtbar zentriert, nicht visuell zu stark)?
     - Größe stimmt (im finalen Druck scannbar)?
  3. Galerie-Wirkung gesamt:
     - Wirken die neuen Templates jetzt "kampagnenreif"?
     - Welches Template profitiert am meisten? Welches am wenigsten?

  Output: strukturierter Befund je Template + Gesamtempfehlung "merge / iterieren / blocker".
  ```

  2. **Run** `python3 tools/visual_review.py --all` (or `--templates kandidat-falzflyer-din-lang,themen-plakat-a3-quer,...` if `--all` covers too many — match the existing CLI from PR #20). This runs all 3 vision models (Claude, Codex/GPT, Gemini) on the new gallery PNGs.

  3. **Aggregate findings** into `reviews/visual-qa-demo-content.md`:
     - Per-template summary across the 3 models
     - Consensus blockers vs cosmetic notes
     - Explicit "ship / iterate / block" verdict per template

  4. **If iterations needed:** cap at **2 iterations per template** (smaller scope than #10's 3-cap). Iteration = adjust manifest prompt, re-generate that one image, re-render that one template, re-review just that template. Document each iteration round in `reviews/visual-qa-demo-content.md` with timestamp.

  5. **Address blockers OR document acceptance:** every blocker either gets a fix (loop back to Tasks 8/9/10 for that template) OR an explicit accepted-rationale entry in the review file. No silent skipping.

  No checkpoint here — the executor uses judgment. The PR review is the human gate.
  </action>
  <verify>
    <automated>test -f reviews/visual-qa-demo-content.md &amp;&amp; grep -E '^(##|verdict|ship|iterate|block)' reviews/visual-qa-demo-content.md | head -20</automated>
  </verify>
  <done>
  - `reviews/visual-qa-demo-content.md` exists with per-template findings from 3 vision models
  - Each of 5 templates has an explicit verdict (ship / iterate / block)
  - All blockers either fixed (additional commits in this issue) or explicitly accepted with rationale
  - Iterations capped at 2 per template; documented if used
  </done>
  <commit>11: docs(reviews): add visual QA pass for demo-content gallery refresh</commit>
</task>

<task type="auto">
  <id>task-12</id>
  <name>Task 12: Final integrity sweep before PR</name>
  <files></files>
  <action>
  Last verification pass before opening the PR. No code changes — pure check-and-confirm.

  1. **Determinism check:** re-run `python3 tools/qr_gen.py templates/<slug>` for each of the 5 templates and confirm `git status` shows NO changes (qrcode 8.2 + Pillow 12.2.0 byte-identical guarantee, D9).

  2. **Round-trip check:** re-run `bin/render-gallery <slug>` for each of the 5 templates and confirm `git status` shows NO changes to template.sla / preview.pdf / page-*.png.

  3. **CI matrix:**
     - `python3 tools/check_ci.py` -> exit 0
     - `bin/check-stale-previews` -> exit 0
     - `python3 tools/spec_check.py templates/<slug>` -> exit 0 for all 8 templates
     - `python3 -m pytest tools/sla_lib/tests/ -x` -> all green
     - `python3 -m pytest templates/_smoke/ -x` -> all green

  4. **EU AI Act 3-layer disclosure check** per RESEARCH.md section 7:
     - Visible watermark `Symbolfoto — KI-generiert` on every committed portrait/themen-photo? (script: open every `samples/*.jpg` in the 3 image-bearing templates and confirm bottom band darker than middle)
     - manifest.yml has `synthetic: true` on every image entry?
     - Each affected template's `README.md` mentions "Demo-Bilder sind synthetisch (KI-generiert) — vor Kampagnen-Einsatz durch echte Fotos ersetzen"? Add the line if missing.

  5. **Manifest sanity:**
     - Every `qr_codes:` entry has `target_url` and a manifest `note:` reminding the enduser to replace with their own URL.
     - Every `images:` entry has `synthetic: true` and a manifest `note:` reminding the enduser to replace with a real photo.

  Fix any failures locally before the PR. Goal: green PR on first push.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates &amp;&amp; for slug in wahlaufruf-postkarte-a6-quer wahltag-tueranhaenger kandidat-falzflyer-din-lang themen-plakat-a3-quer infostand-tent-card-a5-quer; do python3 tools/qr_gen.py templates/$slug &amp;&amp; bin/render-gallery $slug || exit 1; done &amp;&amp; git diff --stat &amp;&amp; test -z "$(git diff --name-only)" &amp;&amp; python3 tools/check_ci.py &amp;&amp; bin/check-stale-previews &amp;&amp; for slug in wahlaufruf-postkarte-a6-quer wahltag-tueranhaenger kandidat-falzflyer-din-lang themen-plakat-a3-quer infostand-tent-card-a5-quer plakat-a1-hochformat postkarte-a6-kampagne zeitung-a4-grun; do python3 tools/spec_check.py templates/$slug || exit 1; done &amp;&amp; python3 -m pytest tools/sla_lib/tests/ templates/_smoke/ -x</automated>
  </verify>
  <done>
  - Re-running QR + render produces no diff (determinism + round-trip stable)
  - All check_ci, check-stale-previews, spec_check, pytest gates green
  - EU AI Act 3-layer disclosure verified (watermark + manifest + README)
  - Manifest notes consistent across all entries
  </done>
  <commit>(no commit — verification-only task; if README updates land here, commit as `11: docs(templates): note synthetic demo images in 3 affected READMEs`)</commit>
</task>

<!-- =================================================================== -->
<!-- PHASE 6 — Ship (Task 13)                                             -->
<!-- =================================================================== -->

<task type="auto">
  <id>task-13</id>
  <name>Task 13: Push branch + open PR with side-by-side gallery before/after</name>
  <files></files>
  <action>
  Push the branch and open the PR.

  ```
  git push -u origin issue/post-migration-dsl-hygiene   # OR whatever the actual branch is — check `git branch --show-current`
  ```

  Wait — the branch in this worktree is `issue/post-migration-dsl-hygiene` per the gitStatus header, but issue #11's slug is `11-demo-bilder-via-codex-qr-codes-für-5-neue-templates`. The branch may need to be renamed before push, OR the push uses the existing branch name. Check `.issues/config.yaml` `naming.branch: "issue/{slug}"` — the canonical name should be `issue/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates`. If the local branch is misnamed, rename:

  ```
  git branch -m issue/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates
  git push -u origin issue/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates
  ```

  Open the PR via `gh pr create`:

  ```
  gh pr create --base main --title "11: feat: demo content (Codex portraits + QR codes) for 5 new templates" --body "$(cat <<'EOF'
  ## Summary

  Activates Issue #10's deferred demo-content layer for the 5 new templates from PR #20:

  - 6 deterministic branded QR codes (Dunkelgrün modules, ECC=H, monochrome Sonnenblume center logo) via new `tools/qr_gen.py`
  - 6 watermarked Codex portraits/themen-photos via extended `tools/codex_image_gen.py` (`Symbolfoto — KI-generiert` per EU AI Act Art 50 forward-compat)
  - Slot scaffolding added in build.py + spec.md for postkarte (QR), türanhänger (QR), falzflyer (3 themen-photos + 2nd QR), themen-plakat (themen-hero + QR), tent-card (QR ImageFrame + Hintergrund). Conditional inject — fresh checkouts without `samples/` still produce clean templates.
  - Tent-card QR slot enlarged 14 mm -> 17 mm per D1 module-size rule.
  - Render-pipeline filter widened to include DSL-only `previews_for_sla:` templates (previously skipped).

  ### Single visual-review pass (D10)

  See `reviews/visual-qa-demo-content.md` — 3 vision models (Claude, Codex, Gemini) compared the demo-populated previews against the prior placeholder version. Per-template verdicts: ship / iterate / block.

  ### Vorher / Nachher

  | Template | Before (PR #20) | After (this PR) |
  |---|---|---|
  | wahlaufruf-postkarte-a6-quer | empty back side | branded QR back |
  | wahltag-tueranhaenger | portrait slot empty | populated portrait + branded QR |
  | kandidat-falzflyer-din-lang | empty cover + spread + closer | populated portrait + 3 themen-photos + 2 QRs |
  | themen-plakat-a3-quer | text-only | optional themen-hero + corner QR |
  | infostand-tent-card-a5-quer | empty front + back | watermarked Hintergrund + branded QR |

  See gallery PNGs at `templates/<slug>/page-*.png`.

  ## Container rebuild

  Adds 4 new dependencies to `Dockerfile.claude`:
  - `qrcode[pil]==8.2`, `pyzbar==0.1.9` (pip)
  - `libzbar0`, `zbar-tools` (apt)

  Container rebuild required after merge. Local test session used `pip install --break-system-packages` + `apt-get install` to bridge the gap.

  ## Test plan

  - [ ] `python3 -m pytest tools/sla_lib/tests/test_qr_gen.py tools/sla_lib/tests/test_codex_image_gen.py templates/_smoke/ -x`
  - [ ] `python3 tools/check_ci.py` green
  - [ ] `bin/check-stale-previews` green for all 8 templates
  - [ ] `python3 tools/spec_check.py` green for all 8 templates
  - [ ] All 6 committed QR PNGs decode via pyzbar to their manifest `target_url`
  - [ ] All 6 committed JPEGs have visible Symbolfoto watermark band
  - [ ] Phone-scan test: scan the 6 QR codes from the rendered preview.pdf at 30 cm and 1 m on iOS + Android (per CONTEXT.md D1 — manual gate)

  Notes: Codex image generation runs once during issue execute; CI never invokes it. QR generation is deterministic (qrcode 8.2 + Pillow 12.2.0 byte-stable).
  EOF
  )"
  ```

  Wait for CI checks to go green. Address any unforeseen failures with follow-up commits on the same branch.

  Once green, ask the issue owner for merge approval (do not auto-merge per CONTEXT.md D7 + memory `feedback_issue_system_quality`).
  </action>
  <verify>
    <automated>git status &amp;&amp; gh pr view --json number,state,statusCheckRollup,mergeable | head -50</automated>
  </verify>
  <done>
  - Branch pushed to origin
  - PR open with side-by-side gallery before/after table linked to `reviews/visual-qa-demo-content.md`
  - CI checks green
  - PR awaits issue-owner merge approval
  </done>
  <commit>(no new commit — task is push + PR creation only)</commit>
</task>

</tasks>

<verification>
After all tasks complete, the final state must satisfy:

1. **Test suites:**
   - `python3 -m pytest tools/sla_lib/tests/test_qr_gen.py -x -v`
   - `python3 -m pytest tools/sla_lib/tests/test_codex_image_gen.py -x -v`
   - `python3 -m pytest templates/_smoke/ -x -v`

2. **CI gates:**
   - `python3 tools/check_ci.py` exit 0
   - `bin/check-stale-previews` exit 0 for all 8 templates
   - `python3 tools/spec_check.py templates/<slug>` exit 0 for all 8 templates

3. **Determinism:**
   - Re-run `python3 tools/qr_gen.py templates/<slug>` for each of 5 templates -> `git status` clean
   - Re-run `bin/render-gallery <slug>` for each of 5 templates -> `git status` clean

4. **Functional:**
   - Each of 6 committed QR PNGs decodes via pyzbar to its manifest `target_url`
   - Each of 6 committed JPEGs (or fewer if iter-cap hit) has the bottom watermark band visible
   - Each render-gallery PNG visibly shows the demo content (portraits + themen + QRs)

5. **Visual review:**
   - `reviews/visual-qa-demo-content.md` exists, has per-template verdicts from 3 vision models, blockers fixed or accepted

6. **Branch + PR:**
   - PR open against main with side-by-side gallery before/after
   - CI green
</verification>

<success_criteria>
Mapped 1:1 to ISSUE.md acceptance criteria:

- [ ] **`tools/qr_gen.py` exists, deterministisch, scannbare PNGs, Tests vorhanden** -> Task 3 (`generate_qr_png` + 5 tests including pyzbar decode + SHA-determinism)
- [ ] **`tools/codex_image_gen.py` end-to-end-getestet mit echtem Codex-Call** -> Tasks 4 (post-process scaffolding) + 9 (real codex calls generate 6 watermarked JPEGs)
- [ ] **Jedes Template mit Bild- oder QR-Slot hat ein vollständiges manifest.yml mit Prompts/URLs** -> Tasks 6 (postkarte, türanhänger) + 7 (falzflyer, themen-plakat, tent-card)
- [ ] **Demo-Portraits + Themen-Bilder generiert: kandidat-falzflyer (1 Portrait + 3 Themen), themen-plakat, tent-card** -> Task 9
- [ ] **QR-Codes generiert + committed: postkarte, türanhänger, falzflyer (1-2), tent-card, themen-plakat** -> Task 8 (6 QR PNGs)
- [ ] **`<slug>-preview.sla` für jedes betroffene Template re-rendered, Galerie-PNG aktualisiert, `meta.yml.previews_for_sla`-SHA passt (`bin/check-stale-previews` grün)** -> Task 10 (research-corrected: conditional inject in template.sla, NOT separate <slug>-preview.sla)
- [ ] **Galerie zeigt die Templates mit echten Bildern und scannbaren QRs** -> Task 10's rendered page-*.png files
- [ ] **Visual-Review-Pass über die aktualisierten Galerie-Previews mit allen drei Vision-Modellen — Konsens "mindestens so gut wie ohne Bilder, idealerweise sichtbar besser"** -> Task 11 (single pass per D10, not multi-gate like #10)
- [ ] **Keine echten Kandidat:innen-Namen oder Gesichter in den synthetischen Portraits; manifest.yml vermerkt "synthetisch, demo-only"** -> Task 7's manifest entries (every image has `synthetic: true` + `note:`)
- [ ] **PR-Beschreibung enthält Vorher/Nachher der betroffenen Galerie-Previews** -> Task 13's PR body
- [ ] **(Implicit, from Constraints) Round-trip + check_ci weiter grün auf allen 8 Templates** -> Tasks 10 + 12
- [ ] **(Implicit, EU AI Act forward-compat) "Symbolfoto — KI-generiert" watermark on every synthetic image** -> Task 4's `add_demo_watermark` + Task 9's generation step
- [ ] **(Implicit, render-pipeline correctness) `bin/render-gallery` works on DSL-only templates** -> Task 2's filter patch
- [ ] **(Implicit, D1 module-size compliance) Tent-card QR slot >= 17 mm** -> Task 7's tent-card spec + build.py update
</success_criteria>
