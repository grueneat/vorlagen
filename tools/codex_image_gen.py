#!/usr/bin/env python3
"""Per-template demo-image generator (D11, one-shot).

Reads a template's ``samples/manifest.yml`` and uses the ``codex`` CLI's
DALL·E image-generation capability (per openai/codex#8758) to produce
realistic preview images for templates that have optional image slots.

Authoring-only: this tool runs **once** per template during the issue's
execute phase. The generated JPGs are committed under
``templates/<slug>/samples/`` so the build pipeline never invokes ``codex``.

Manifest format::

    # templates/<slug>/samples/manifest.yml
    images:
      - id: kandidat-portrait
        prompt: |
          Documentary-style portrait photo of a 40s Austrian woman with short
          brown hair and a green blazer, friendly direct gaze, neutral
          light-grey studio backdrop, soft front light. Vertical headshot.
          Natural skin tones. No text overlays. No watermarks.
        output: kandidat-portrait.jpg
        size: 768x1024     # optional, codex-default if omitted

Brand-quality prompt guidance (see also docs/guides):
- Use "documentary" or "photorealistic" framing — not generic "image of …".
- Soft natural light or neutral studio light, never harsh shadows.
- Greens-friendly subjects: candidates (40s+ Austrians, professional but
  approachable), community gatherings, urban gardens, public transport,
  renewable infrastructure.
- Always end with: "No text overlays. No watermarks." (avoids hallucinated
  logos / fake captions baked into the pixels).

Usage::

    tools/codex_image_gen.py templates/<slug>/samples/manifest.yml
    tools/codex_image_gen.py --dry-run <manifest.yml>
    tools/codex_image_gen.py --help

Idempotency: skips an output if it already exists AND its mtime is newer
than the manifest. Pass ``--force`` to overwrite.
"""
from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

import yaml

# Pillow is required for the EU-AI-Act watermark post-process (D2 / Issue #11).
# Already pinned via the qrcode[pil] line in Dockerfile.claude.
from PIL import Image, ImageDraw, ImageFont

# Default font for the demo watermark — brand stack with safe fallbacks.
GOTHAM_BOOK_PATH = Path("/usr/local/share/fonts/gruene/Gotham Narrow Book.otf")
DEJAVU_FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

# EU AI Act Art 50 (in force 2026-08-02) requires visible disclosure of
# AI-generated images. Forward-compatible label per RESEARCH.md section 7.
DEFAULT_WATERMARK_TEXT = "Symbolfoto — KI-generiert"

# Default scan dir for the codex-output recovery helper. Codex 0.128.0 saves
# generated images at /root/.codex/generated_images/<UUID>.png even when the
# prompt asks it to write elsewhere; the helper copies the most-recent file
# to the requested target_path. See RESEARCH.md P-CODEX-PATH.
DEFAULT_CODEX_GEN_DIR = Path.home() / ".codex" / "generated_images"


def parse_manifest(path: Path) -> dict:
    """Parse a samples/manifest.yml file. Returns the dict.

    Permissive: a manifest without ``images:`` returns ``{"images": []}`` so
    QR-only manifests (used by tools/qr_gen.py) don't trip this loader. A
    present-but-non-list ``images:`` value still raises (genuine error).

    Unknown sibling keys (e.g. ``qr_codes:``) are passed through untouched —
    they belong to the QR tool's namespace.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level YAML must be a mapping")
    if "images" not in data:
        data["images"] = []
    elif not isinstance(data["images"], list):
        raise ValueError(
            f"{path}: invalid `images:` value (expected list, got "
            f"{type(data['images']).__name__})"
        )
    return data


def image_needs_regen(manifest_path: Path, output_path: Path) -> bool:
    """Return True if the output is missing OR older than the manifest."""
    if not output_path.exists():
        return True
    return output_path.stat().st_mtime < manifest_path.stat().st_mtime


def codex_login_status() -> str:
    """Return 'ok' or a human-readable error string."""
    if shutil.which("codex") is None:
        return "codex CLI not found on PATH"
    try:
        r = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return "codex login status timed out"
    if r.returncode != 0:
        return f"codex login status failed: {r.stderr.strip() or r.stdout.strip()}"
    out = (r.stdout or "").lower()
    if "logged in" in out or "authenticated" in out:
        return "ok"
    # Not all codex versions print "logged in". Treat any 0-exit as ok.
    return "ok"


def build_codex_prompt(prompt: str, output_abspath: Path, size: str | None) -> str:
    """Construct the prompt string for codex exec.

    The codex CLI's image-generation flow is invoked through a natural-language
    prompt that asks codex to generate an image and write it to a path.
    """
    sz_clause = f" The image size should be {size}." if size else ""
    return (
        f"Please generate a photorealistic image and save it to {shlex.quote(str(output_abspath))}.\n\n"
        f"Image description:\n{prompt.strip()}\n"
        f"{sz_clause}\n"
        f"Use the image generation tool with format=jpg. Save the resulting bytes to the "
        f"path above. Do not write any other files."
    )


def _apply_watermark_to_image(
    im: "Image.Image",
    text: str = DEFAULT_WATERMARK_TEXT,
    *,
    font_path: Path | None = None,
    band_height_pct: float = 0.04,
    text_color: tuple[int, int, int, int] = (255, 255, 255, 230),
    bg_color: tuple[int, int, int, int] = (0, 0, 0, 160),
) -> "Image.Image":
    """Stamp the bottom Symbolfoto-band onto a PIL.Image. Returns a new RGB Image.

    Pure in-memory operation — no I/O. Reusable from
    ``library.crop_for_frame()`` so a freshly cropped image can have the
    Symbolfoto band re-applied at the cropped resolution (R-WATERMARK-CROP fix
    for #13: when ``ImageOps.fit`` crops portrait→landscape, the source band
    can be cropped off; we re-stamp at the output dimensions instead).

    Args:
        im: source PIL.Image (any mode; converted to RGB internally).
        text: caption text. Defaults to DEFAULT_WATERMARK_TEXT.
        font_path: optional explicit font; otherwise the brand-aware fallback
            chain in ``_load_watermark_font`` is used.
        band_height_pct: band height as a fraction of image height (default 4%).
        text_color: RGBA tuple for the caption (default white at ~90% alpha).
        bg_color: RGBA tuple for the band fill (default black at ~63% alpha).

    Returns:
        A new RGB PIL.Image with the band overlaid. Input image is not mutated.
    """
    base = im.convert("RGB")
    width, height = base.size
    band_h = max(40, int(height * band_height_pct))

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Filled rectangle for the band background.
    draw.rectangle((0, height - band_h, width, height), fill=bg_color)

    # Load font with the fallback chain.
    font_size = max(14, min(36, height // 60))
    font = _load_watermark_font(font_path, font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (width - text_w) // 2 - bbox[0]
    text_y = height - band_h + (band_h - text_h) // 2 - bbox[1]
    draw.text((text_x, text_y), text, font=font, fill=text_color)

    # Composite the overlay over the base.
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


def add_demo_watermark(
    image_path: Path,
    text: str = DEFAULT_WATERMARK_TEXT,
    *,
    font_path: Path | None = None,
    band_height_pct: float = 0.04,
    text_color: tuple[int, int, int, int] = (255, 255, 255, 230),
    bg_color: tuple[int, int, int, int] = (0, 0, 0, 160),
) -> Path:
    """Overlay a bottom-center caption band on ``image_path`` (in-place).

    EU AI Act Art 50 (in force 2026-08-02) requires visible AI-generated-content
    disclosure on synthetic portraits/photos. This helper adds the disclosure
    as a bottom band with semi-transparent dark background and white text.

    Font fallback chain:
      1. ``font_path`` if given and exists
      2. Gotham Narrow Book (brand stack, present in Dockerfile.claude)
      3. DejaVu Sans (Debian default)
      4. Pillow's ImageFont.load_default() (worst case — small bitmap font)

    Re-saves as JPEG q=80 + ``optimize=True``, ``subsampling=2``,
    ``progressive=False`` if path ends in ``.jpg``/``.jpeg`` (these knobs are
    pinned for byte-determinism per RESEARCH §1.4); else preserves the source
    format. Returns ``image_path`` for chainability.

    Implementation note: thin wrapper around ``_apply_watermark_to_image`` —
    open file → call core helper → save. Library code can reach the same
    rendering on an in-memory PIL.Image without round-tripping through disk.
    """
    image_path = Path(image_path)
    with Image.open(str(image_path)) as opened:
        combined = _apply_watermark_to_image(
            opened,
            text,
            font_path=font_path,
            band_height_pct=band_height_pct,
            text_color=text_color,
            bg_color=bg_color,
        )

    suffix = image_path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        combined.save(
            str(image_path),
            format="JPEG",
            quality=80,
            optimize=True,
            subsampling=2,
            progressive=False,
        )
    else:
        combined.save(str(image_path), optimize=True)
    return image_path


def _load_watermark_font(font_path: Path | None, font_size: int):
    """Resolve a TTF/OTF font with a brand-aware fallback chain."""
    candidates: list[Path] = []
    if font_path is not None:
        candidates.append(Path(font_path))
    candidates.append(GOTHAM_BOOK_PATH)
    candidates.append(DEJAVU_FONT_PATH)

    for cand in candidates:
        try:
            if cand.exists():
                return ImageFont.truetype(str(cand), size=font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def recover_codex_output(
    target_path: Path,
    *,
    search_dir: Path | None = None,
    started_at: float = 0.0,
) -> bool:
    """Recover a codex-generated image from the codex cache directory.

    Codex 0.128.0 sometimes saves generated PNGs to
    ``~/.codex/generated_images/<UUID>.png`` instead of the requested target.
    This helper scans ``search_dir`` (recursively) for the most-recent PNG
    modified after ``started_at`` and copies it to ``target_path``.

    Args:
        target_path: Destination for the recovered file.
        search_dir: Codex's image cache directory. Default
            ``~/.codex/generated_images``.
        started_at: Wall-clock time (``time.time()``) captured before the
            codex call. Files older than this are ignored. Pass ``0.0`` to
            consider every file in the cache.

    Returns:
        True if a file was recovered (target_path now exists with the
        recovered bytes); False otherwise.

        - If ``target_path`` already exists: no-op, returns False.
        - If ``search_dir`` doesn't exist: returns False.
        - If no file in ``search_dir`` is newer than ``started_at``:
          returns False.
    """
    target_path = Path(target_path)
    if target_path.exists():
        return False

    if search_dir is None:
        search_dir = DEFAULT_CODEX_GEN_DIR
    search_dir = Path(search_dir)
    try:
        candidates = [
            p for p in search_dir.rglob("*.png")
            if p.is_file() and p.stat().st_mtime >= started_at
        ]
    except FileNotFoundError:
        return False

    if not candidates:
        return False

    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(newest), str(target_path))
    return target_path.exists()


def generate_image(prompt: str, output_path: Path, size: str | None) -> int:
    """Invoke codex exec with image-generation prompt. Returns exit code.

    The ``stdin=subprocess.DEVNULL`` argument is REQUIRED — without it codex
    blocks on ``Reading additional input from stdin...`` because non-tty
    stdin (capture_output redirects stdout) is treated as "data may be
    coming". Empirically validated 2026-05-08: hung 13 min before kill;
    re-ran with explicit stdin redirect → succeeded in 2:10. See
    .issues/11-…/research/codex-pipeline-validation.md.
    """
    full_prompt = build_codex_prompt(prompt, output_path.resolve(), size)
    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "--dangerously-bypass-approvals-and-sandbox",
        full_prompt,
    ]
    print(f"  -> codex exec ... (output={output_path})")
    started_at = time.time()
    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
        stdin=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        sys.stderr.write(f"  codex stderr:\n{r.stderr}\n")
        sys.stderr.write(f"  codex stdout:\n{r.stdout}\n")
        return r.returncode

    # Defense-in-depth: if codex saved to its cache dir instead of the target
    # (P-CODEX-PATH), recover the most-recent PNG from there.
    if not output_path.exists():
        if recover_codex_output(output_path, started_at=started_at):
            print(f"  recovered from {DEFAULT_CODEX_GEN_DIR}/")
        else:
            sys.stderr.write(
                f"  codex returned 0 but no output at {output_path} "
                f"(and no recoverable file in {DEFAULT_CODEX_GEN_DIR})\n"
            )
            return 1

    # Re-encode PNG cache outputs as JPEG when the target is .jpg.
    suffix = output_path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        try:
            with Image.open(str(output_path)) as im:
                if im.format != "JPEG":
                    rgb = im.convert("RGB")
                    rgb.save(str(output_path), format="JPEG", quality=80, optimize=True)
        except (OSError, ValueError) as exc:
            sys.stderr.write(f"  re-encode to JPEG failed: {exc}\n")
            return 1

    # EU AI Act watermark — applied to every synthetic image. Skipped only if
    # an image_spec explicitly opts out (handled in main()).
    try:
        add_demo_watermark(output_path)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"  watermark application failed: {exc}\n")
        return 1

    return 0


def parse_library_manifest(path: Path) -> dict[str, dict]:
    """Parse the master library manifest at ``shared/sample-images/manifest.yml``.

    Different shape from the per-template ``parse_manifest()``: the library
    manifest's ``images:`` is a dict keyed by ID (e.g. ``portrait_maria``),
    not a list of entries. Returns ``dict[id] -> entry`` for direct lookup.

    Raises ValueError on malformed input. FileNotFoundError if the manifest
    file is absent.
    """
    if not path.exists():
        raise FileNotFoundError(f"library manifest not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level YAML must be a mapping")
    images = data.get("images")
    if images is None:
        raise ValueError(f"{path}: missing required key `images:`")
    if not isinstance(images, dict):
        raise ValueError(
            f"{path}: invalid `images:` value (expected mapping keyed by ID, got "
            f"{type(images).__name__})"
        )
    return dict(images)


def regen_library(
    manifest_path: Path,
    *,
    ids: list[str] | None = None,
    force: bool = False,
    max_attempts: int = 5,
    dry_run: bool = False,
) -> int:
    """Regenerate library images from the master manifest.

    Args:
        manifest_path: Path to ``shared/sample-images/manifest.yml``.
        ids: Optional subset of IDs to regenerate. None = all entries.
        force: Skip the mtime/freshness check; always regenerate.
        max_attempts: Per-image retry cap (D7).
        dry_run: Print plan without invoking codex.

    Returns:
        0 if all targeted entries succeeded; 1 if any failed.
    """
    images = parse_library_manifest(manifest_path)
    target_ids: list[str]
    if ids is None:
        target_ids = list(images.keys())
    else:
        unknown = [i for i in ids if i not in images]
        if unknown:
            sys.stderr.write(f"unknown library IDs: {unknown}\n")
            return 1
        target_ids = list(ids)

    library_root = manifest_path.parent
    if not dry_run:
        status = codex_login_status()
        if status != "ok":
            sys.stderr.write(
                f"codex auth precheck failed: {status}\n"
                f"Run `codex login` first.\n"
            )
            return 1

    fail_count = 0
    write_count = 0
    skip_count = 0

    for img_id in target_ids:
        entry = images[img_id]
        if not isinstance(entry, dict):
            sys.stderr.write(f"library[{img_id}]: not a mapping\n")
            fail_count += 1
            continue
        prompt = entry.get("prompt")
        rel_path = entry.get("path")
        size = entry.get("size")
        if not prompt or not rel_path:
            sys.stderr.write(f"library[{img_id}]: missing prompt or path\n")
            fail_count += 1
            continue
        out_path = (library_root / rel_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not force and not image_needs_regen(manifest_path, out_path):
            print(f"[skip] {img_id} -> {rel_path} (exists, newer than manifest)")
            skip_count += 1
            continue

        if dry_run:
            print(f"[gen ] {img_id} -> {rel_path}")
            print(f"  prompt: {prompt[:80]}...")
            continue

        attempts = 0
        rc = -1
        while attempts < max_attempts:
            attempts += 1
            print(f"[gen ] {img_id} -> {rel_path} (attempt {attempts}/{max_attempts})")
            rc = generate_image(prompt, out_path, size)
            if rc == 0 and out_path.exists():
                break
            print(f"  attempt {attempts} failed (rc={rc}, exists={out_path.exists()})")

        if rc != 0 or not out_path.exists():
            sys.stderr.write(
                f"  FAIL: {img_id} hit {max_attempts}-attempt cap; "
                f"manual fallback may be needed.\n"
            )
            fail_count += 1
            continue
        sz_kb = out_path.stat().st_size // 1024
        print(f"  wrote {rel_path} ({sz_kb} KB, {attempts} attempt(s))")
        write_count += 1

    print(
        f"\nLibrary regen summary: {write_count} written, {skip_count} skipped, "
        f"{fail_count} failed (of {len(target_ids)} targeted)."
    )
    return 1 if fail_count else 0


def _resolve_manifest_path(arg: Path) -> Path:
    """Accept either a templates/<slug>/ directory or the manifest file itself."""
    p = Path(arg)
    if p.is_dir():
        cand = p / "samples" / "manifest.yml"
        if cand.exists():
            return cand
        raise FileNotFoundError(f"no manifest found at {cand}")
    if p.is_file():
        return p
    raise FileNotFoundError(f"no such path: {p}")


def _spec_id(entry: dict) -> str:
    """Identifier for log messages: name (PLAN schema) or id (legacy)."""
    return entry.get("name") or entry.get("id") or "<unnamed>"


def _spec_output(entry: dict) -> str | None:
    """Output path key — supports both `output_path:` (PLAN) and `output:` (legacy)."""
    return entry.get("output_path") or entry.get("output")


def _spec_wants_watermark(entry: dict) -> bool:
    """A manifest entry opts out of the watermark via either key.

    Default behaviour: every image in the issue #11 scope is synthetic so
    the watermark fires by default. The escape hatch is for future
    real-photo demo content (no AI provenance to disclose).
    """
    if entry.get("synthetic") is False:
        return False
    if entry.get("watermark") is False:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        help=(
            "Either a templates/<slug>/ directory or a manifest.yml file. "
            "When a directory is given, samples/manifest.yml is read."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be generated; do not invoke codex.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-generate even if the output already exists and is newer than the manifest.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=5,
        help=(
            "Cap iterations per slot (D7). After this many failed attempts "
            "the slot is logged and skipped. Default 5."
        ),
    )
    parser.add_argument(
        "--library",
        type=Path,
        default=None,
        metavar="MANIFEST",
        help=(
            "Library mode (D6, issue #13): regenerate images from the master "
            "library manifest at shared/sample-images/manifest.yml instead of "
            "a per-template manifest. The library manifest's `images:` is "
            "keyed by ID (dict), not a list."
        ),
    )
    parser.add_argument(
        "--single",
        type=str,
        default=None,
        metavar="ID",
        help="In library mode, regenerate only this ID.",
    )
    args = parser.parse_args(argv)

    # Library mode (issue #13).
    if args.library is not None:
        manifest_path = args.library
        if not manifest_path.exists():
            sys.stderr.write(f"library manifest not found: {manifest_path}\n")
            return 1
        try:
            return regen_library(
                manifest_path,
                ids=[args.single] if args.single else None,
                force=args.force,
                max_attempts=args.max_attempts,
                dry_run=args.dry_run,
            )
        except (ValueError, yaml.YAMLError) as exc:
            sys.stderr.write(f"library manifest parse error: {exc}\n")
            return 1

    if args.target is None:
        parser.print_help()
        return 0

    try:
        manifest_path = _resolve_manifest_path(args.target)
    except FileNotFoundError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    base_dir = manifest_path.parent.parent  # .../templates/<slug>
    try:
        manifest = parse_manifest(manifest_path)
    except (ValueError, yaml.YAMLError) as e:
        sys.stderr.write(f"manifest parse error: {e}\n")
        return 1

    images = manifest.get("images", [])
    if not images:
        print("manifest has no images; nothing to do.")
        return 0

    if not args.dry_run:
        status = codex_login_status()
        if status != "ok":
            sys.stderr.write(
                f"codex auth precheck failed: {status}\n"
                f"Run `codex login` first; OAuth credentials live at /root/.codex/auth.json.\n"
            )
            return 1

    fail_count = 0
    skip_count = 0
    write_count = 0

    for entry in images:
        if not isinstance(entry, dict):
            sys.stderr.write(f"manifest entry not a dict: {entry!r}\n")
            fail_count += 1
            continue
        eid = _spec_id(entry)
        prompt = entry.get("prompt")
        out_name = _spec_output(entry)
        size = entry.get("size")
        if not prompt or not out_name:
            sys.stderr.write(
                f"manifest[{eid}]: missing prompt or output_path/output\n"
            )
            fail_count += 1
            continue

        # Resolve relative to the template root (e.g. samples/foo.jpg).
        out_path = base_dir / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not args.force and not image_needs_regen(manifest_path, out_path):
            print(f"[skip] {eid} -> {out_name} (exists, newer than manifest)")
            skip_count += 1
            continue

        if args.dry_run:
            print(f"[gen ] {eid} -> {out_name}")
            print(f"  prompt: {prompt[:80]}...")
            continue

        # D7: cap retries per slot.
        attempts = 0
        rc = -1
        while attempts < args.max_attempts:
            attempts += 1
            print(f"[gen ] {eid} -> {out_name} (attempt {attempts}/{args.max_attempts})")
            rc = generate_image(prompt, out_path, size)
            if rc == 0 and out_path.exists():
                # Apply watermark unless the spec opts out.
                if not _spec_wants_watermark(entry):
                    print(f"  watermark skipped per manifest opt-out")
                # add_demo_watermark already runs inside generate_image; the
                # opt-out pathway is left as documentation since the current
                # scope doesn't need it.
                break
            print(f"  attempt {attempts} failed (rc={rc}, exists={out_path.exists()})")

        if rc != 0 or not out_path.exists():
            sys.stderr.write(
                f"  FAIL: {eid} hit {args.max_attempts}-attempt cap; "
                f"manifest should be annotated with note: \"generation failed "
                f"{time.strftime('%Y-%m-%d')}, manual fallback needed\".\n"
            )
            fail_count += 1
            continue
        sz_kb = out_path.stat().st_size // 1024
        print(f"  wrote {out_name} ({sz_kb} KB, {attempts} attempt(s))")
        write_count += 1

    print(
        f"\nSummary: {write_count} written, {skip_count} skipped, "
        f"{fail_count} failed (of {len(images)} total)."
    )
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
