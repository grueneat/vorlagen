"""Centralized demo-image library for the template gallery (issue #13).

Holds metadata + access API for shared/sample-images/. Templates reference
images by stable IDs (``portrait_maria``, ``themen_klimaschutz_solar``) instead
of fragile per-template paths. Built on top of #11's codex+watermark pipeline.

Public surface (matches PLAN.md ``<interfaces>``):

    from sla_lib.builder import library

    img = library.load("portrait_maria")            # raise if missing
    img = library.load("portrait_maria", optional=True)  # None if missing
    cropped = library.crop_for_frame(img, target_w_mm=87, target_h_mm=24)
    data, ext = pack_inline_image(cropped, "jpg")
    # ... pass to ImageFrame(inline_image_data=data, inline_image_ext=ext, ...)

Library layout::

    shared/sample-images/
    ├── manifest.yml           # central master index
    ├── portraits/<id>.jpg
    ├── themen/<id>.jpg
    ├── kontext/<id>.jpg
    └── qr/                    # empty per D9 (QRs stay template-specific)

Manifest schema is enforced via ``LIBRARY_MANIFEST_SCHEMA`` (Draft 2020-12).
Permissive on optional fields, strict on required (``path``, ``prompt``,
``tags``, ``synthetic``).

R-WATERMARK-CROP fix:
    ``crop_for_frame()`` re-applies the Symbolfoto bottom band POST-crop. With
    portrait↔landscape aspect mismatches the source band can be cropped off
    by ``ImageOps.fit``; we always re-stamp on the cropped output instead.
    Library can optionally hold an un-watermarked source variant at
    ``<path stem>-source.jpg``; if present, that file is used as the input to
    ``ImageOps.fit`` and the watermark is freshly applied. If absent, the
    watermarked library bytes are cropped and re-stamped (band overdraw is
    cosmetically benign — pixel area covered twice is uniformly dark).

Determinism:
    Pillow==12.2.0 + libjpeg-turbo (container-pinned). JPEG kwargs pinned:
    quality=80, optimize=True, subsampling=2, progressive=False. Two
    consecutive ``crop_for_frame()`` calls with identical args produce
    byte-identical output.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, Sequence

import yaml
from PIL import Image, ImageOps

# Resolve LIBRARY_ROOT relative to this file so the module works regardless of
# the caller's CWD. parents[3] reaches workspace root from
# tools/sla_lib/builder/library.py.
LIBRARY_ROOT = Path(__file__).resolve().parents[3] / "shared" / "sample-images"
MANIFEST_PATH = LIBRARY_ROOT / "manifest.yml"


@dataclass(frozen=True)
class LibraryImage:
    """One image in shared/sample-images/, with metadata.

    Returned by ``library.load(id)``. Pass ``.bytes`` to
    ``pack_inline_image(img.bytes, "jpg")`` for ImageFrame embedding when no
    cropping is needed; otherwise call ``library.crop_for_frame(img, ...)``
    first.

    Frozen so callers cannot accidentally mutate ``.bytes`` between use sites.
    """
    id: str
    path: Path
    bytes: bytes
    meta: dict

    @property
    def crop_focus_x(self) -> float:
        """Horizontal saliency anchor in [0, 1]. Default 0.5 (image center).

        Sourced from manifest field ``crop_focus: [x, y]``; falls back to legacy
        ``centering: [x, y]`` for back-compat. Out-of-range or malformed values
        silently fall back to 0.5.
        """
        return _focus_pair(self.meta)[0]

    @property
    def crop_focus_y(self) -> float:
        """Vertical saliency anchor in [0, 1]. Default 0.5 (image center).

        See ``crop_focus_x`` for sourcing rules.
        """
        return _focus_pair(self.meta)[1]


def _focus_pair(meta: dict) -> tuple[float, float]:
    """Resolve ``[x, y]`` focus tuple from a manifest entry, with safe defaults.

    Reads ``crop_focus`` first (canonical name), falls back to ``centering``
    (legacy field name retained for back-compat). Both must be a 2-element
    list/tuple of numbers in [0, 1]; otherwise the default ``(0.5, 0.5)`` is
    returned. Out-of-range numbers are clamped, not rejected — defensive against
    minor manifest typos.
    """
    raw = meta.get("crop_focus")
    if raw is None:
        raw = meta.get("centering")
    if not (isinstance(raw, (list, tuple)) and len(raw) == 2):
        return (0.5, 0.5)
    try:
        x = float(raw[0])
        y = float(raw[1])
    except (TypeError, ValueError):
        return (0.5, 0.5)
    # Clamp to [0, 1]; values outside are usually mistakes (e.g. a percentage).
    x = max(0.0, min(1.0, x))
    y = max(0.0, min(1.0, y))
    return (x, y)


class LibraryError(Exception):
    """Raised when a required library ID is missing or the manifest is malformed."""


# JSON Schema for manifest validation (Draft 2020-12). Embedded as Python dict
# to keep schema co-located with the code that uses it.
LIBRARY_MANIFEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["images"],
    "properties": {
        "images": {
            "type": "object",
            "patternProperties": {
                "^[a-z][a-z0-9_]*$": {  # snake_case IDs
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
                        "crop_focus": {
                            # Saliency anchor [x, y] in [0, 1] used as the
                            # ``centering`` argument to PIL.ImageOps.fit when
                            # cropping for a frame's aspect ratio. Place this
                            # over the visual subject (face on portraits, main
                            # object on themen) to avoid sky-only / hair-only
                            # crops on aspect-mismatched slots.
                            "type": "array",
                            "items": {"type": "number", "minimum": 0, "maximum": 1},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                        "centering": {
                            # Legacy alias for ``crop_focus`` — accepted for
                            # back-compat. New entries should use ``crop_focus``.
                            "type": "array",
                            "items": {"type": "number", "minimum": 0, "maximum": 1},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                    },
                    # Permissive: future fields (replace_in_production, codex_version,
                    # etc.) can land without a schema bump. D4 hardening later.
                    "additionalProperties": True,
                },
            },
            # Only snake_case IDs; no other top-level keys under images:.
            "additionalProperties": False,
        },
    },
}


# ---------------------------------------------------------------------------
# Internal helpers


def _read_manifest() -> dict:
    """Parse the master manifest at MANIFEST_PATH.

    No caching — module-level cache makes monkeypatching MANIFEST_PATH in tests
    awkward, and the manifest is small (~13 entries × few hundred bytes).
    """
    if not MANIFEST_PATH.exists():
        raise LibraryError(f"library manifest missing: {MANIFEST_PATH}")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise LibraryError(
            f"{MANIFEST_PATH}: top-level YAML must be a mapping, got {type(data).__name__}"
        )
    if "images" not in data or not isinstance(data["images"], dict):
        raise LibraryError(
            f"{MANIFEST_PATH}: missing or invalid `images:` mapping"
        )
    return data


def _validate_manifest_entry(id: str, entry: dict) -> None:
    """Soft-validate a single manifest entry. Raises LibraryError on missing
    required fields (path, prompt). This is the cheap fail-fast at load() time;
    full schema validation lives in validate_manifest()."""
    if not isinstance(entry, dict):
        raise LibraryError(f"library entry {id!r}: expected mapping, got {type(entry).__name__}")
    for required in ("path", "prompt"):
        if required not in entry:
            raise LibraryError(f"library entry {id!r}: missing required field {required!r}")


def _category_from_path(path: str) -> str:
    """Derive category from the first directory segment of a manifest path.

    ``portraits/maria-beispiel.jpg`` → ``"portraits"``
    ``themen/klimaschutz-solar.jpg`` → ``"themen"``
    """
    parts = Path(path).parts
    return parts[0] if parts and parts[0] not in (".", "/") else ""


# ---------------------------------------------------------------------------
# Public API


def load(id: str, *, optional: bool = False) -> Optional[LibraryImage]:
    """Resolve a library image by ID.

    Args:
        id: Library entry ID (e.g. "portrait_maria").
        optional: When True, returns None if the entry is missing or its file
            doesn't exist. When False (default), raises LibraryError on either
            condition.

    Returns:
        LibraryImage on hit; None when optional=True and missing.

    Raises:
        LibraryError: when not optional and the ID isn't in the manifest, or
            when the manifest entry references a file that doesn't exist on
            disk.
    """
    try:
        data = _read_manifest()
    except LibraryError:
        if optional:
            return None
        raise
    images = data.get("images", {})
    if id not in images:
        if optional:
            return None
        raise LibraryError(f"unknown library ID: {id!r}")
    entry = images[id]
    _validate_manifest_entry(id, entry)
    path = (LIBRARY_ROOT / entry["path"]).resolve()
    if not path.exists():
        if optional:
            return None
        raise LibraryError(
            f"library entry {id!r}: file missing at {path} "
            f"(manifest path: {entry['path']})"
        )
    return LibraryImage(id=id, path=path, bytes=path.read_bytes(), meta=dict(entry))


def all_images() -> dict[str, LibraryImage]:
    """All known library entries keyed by ID.

    Entries with missing files have ``bytes=b""`` so the caller can decide how
    to handle them (e.g. regenerate). Validation (required-fields) still runs.
    """
    out: dict[str, LibraryImage] = {}
    data = _read_manifest()
    for id_, entry in data.get("images", {}).items():
        _validate_manifest_entry(id_, entry)
        path = (LIBRARY_ROOT / entry["path"]).resolve()
        if path.exists():
            out[id_] = LibraryImage(
                id=id_, path=path, bytes=path.read_bytes(), meta=dict(entry)
            )
        else:
            out[id_] = LibraryImage(id=id_, path=path, bytes=b"", meta=dict(entry))
    return out


def find(*, tags: Sequence[str] = (), category: Optional[str] = None) -> list[LibraryImage]:
    """Discovery helper — return library images matching ALL given tags + category.

    Permissive matching (no validation of tag namespace per CONTEXT D4
    "permissive zunächst"). Category is derived from the manifest entry's path
    first directory segment.

    Returns:
        List of LibraryImage in stable order (sorted by id).
    """
    tag_set = set(tags)
    matches: list[LibraryImage] = []
    for id_, img in all_images().items():
        img_tags = set(img.meta.get("tags", []))
        if tag_set and not tag_set.issubset(img_tags):
            continue
        if category is not None and _category_from_path(img.meta.get("path", "")) != category:
            continue
        matches.append(img)
    matches.sort(key=lambda im: im.id)
    return matches


def crop_for_frame(
    img: LibraryImage,
    *,
    target_w_mm: float,
    target_h_mm: float,
    dpi: int = 300,
    quality: int = 80,
    apply_watermark: bool = True,
) -> bytes:
    """Center-crop and re-encode a library image to fit a frame's aspect ratio.

    Algorithm:
      1. Compute target_w_px / target_h_px from mm + dpi.
      2. Pick the SOURCE bytes:
         - if ``<stem>-source.jpg`` exists alongside the watermarked file, use
           that (un-watermarked source — cropping won't double-stamp the band).
         - else use ``img.bytes`` directly.
      3. Center-crop + resize via ``ImageOps.fit(centering=(cx, cy),
         method=BICUBIC)`` where ``(cx, cy)`` is the per-image saliency anchor
         from ``meta["crop_focus"]`` (or legacy ``meta["centering"]``), default
         ``(0.5, 0.5)``.
      4. If ``apply_watermark=True``, re-stamp the Symbolfoto band on the cropped
         output (R-WATERMARK-CROP fix — band always visible at the cropped
         resolution). Watermark text comes from ``img.meta["watermark"]`` if
         present, else ``DEFAULT_WATERMARK_TEXT``.
      5. Encode JPEG with explicit ``quality=quality, optimize=True,
         subsampling=2, progressive=False`` for byte-determinism (RESEARCH §1.4).

    A per-image ``crop_focus: [x, y]`` override in the manifest biases the
    crop center toward the visual subject (e.g. ``[0.50, 0.35]`` keeps a face
    visible when an aspect-mismatched slot would otherwise crop to hair-only).
    Both values are in ``[0, 1]``; default ``(0.5, 0.5)`` = exact center.
    The legacy field name ``centering`` is still accepted as a fallback.

    Returns:
        JPEG bytes ready for ``pack_inline_image(bytes, "jpg")``.

    Raises:
        LibraryError if Pillow can't decode the source.
    """
    target_w_px = max(1, round(target_w_mm * dpi / 25.4))
    target_h_px = max(1, round(target_h_mm * dpi / 25.4))

    # 2) Pick source bytes
    source_path = img.path.with_name(img.path.stem + "-source" + img.path.suffix)
    source_bytes = source_path.read_bytes() if source_path.exists() else img.bytes

    try:
        with Image.open(BytesIO(source_bytes)) as opened:
            rgb = opened.convert("RGB")
    except Exception as exc:  # Pillow raises a variety of exceptions
        raise LibraryError(f"library entry {img.id!r}: cannot decode source image: {exc}") from exc

    # 3) center-crop + resize, biased toward the manifest's saliency anchor
    # ``crop_focus: [x, y]`` (legacy alias: ``centering``). Default is image
    # center (0.5, 0.5) when neither field is set. Out-of-range or malformed
    # values silently degrade to the default — see ``_focus_pair``.
    cx, cy = _focus_pair(img.meta)
    fitted = ImageOps.fit(
        rgb,
        (target_w_px, target_h_px),
        method=Image.Resampling.BICUBIC,
        centering=(cx, cy),
    )

    # 4) Re-apply watermark
    if apply_watermark:
        # Lazy import: codex_image_gen lives at tools/codex_image_gen.py and
        # imports yaml + Pillow + subprocess. Importing it here (not at module
        # top) avoids cycles via tools/render_pipeline.py which transitively
        # imports both library and codex_image_gen.
        from importlib import import_module

        try:
            cig = import_module("codex_image_gen")
        except ModuleNotFoundError:
            # tools/ may not be on sys.path when called from a test harness;
            # adjust and retry once.
            import sys

            tools_dir = Path(__file__).resolve().parents[2]
            if str(tools_dir) not in sys.path:
                sys.path.insert(0, str(tools_dir))
            cig = import_module("codex_image_gen")

        watermark_text = img.meta.get("watermark", cig.DEFAULT_WATERMARK_TEXT)
        fitted = cig._apply_watermark_to_image(fitted, text=watermark_text)

    # 5) Deterministic JPEG encode
    buf = BytesIO()
    fitted.save(
        buf,
        format="JPEG",
        quality=quality,
        optimize=True,
        subsampling=2,
        progressive=False,
    )
    return buf.getvalue()


def regenerate(id: str, *, force: bool = False, max_attempts: int = 5) -> bool:
    """Re-run codex generation for a library image based on its manifest prompt.

    Wraps ``tools.codex_image_gen.generate_image`` (which already invokes codex
    with ``stdin=subprocess.DEVNULL`` and applies the post-process watermark).

    Args:
        id: Library entry ID.
        force: When True, always regenerate even if the file exists and is
            newer than the manifest. When False, skips up-to-date entries.
        max_attempts: Cap on codex retries (D7 from #11). Reserved — current
            generate_image() handles its own retry.

    Returns:
        True on success (file exists post-generation), False on failure.
    """
    from importlib import import_module
    import sys

    tools_dir = Path(__file__).resolve().parents[2]
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    cig = import_module("codex_image_gen")

    data = _read_manifest()
    if id not in data.get("images", {}):
        raise LibraryError(f"unknown library ID for regenerate: {id!r}")
    entry = data["images"][id]
    _validate_manifest_entry(id, entry)
    output_path = (LIBRARY_ROOT / entry["path"]).resolve()

    # Skip if up-to-date.
    if not force and output_path.exists():
        if output_path.stat().st_mtime >= MANIFEST_PATH.stat().st_mtime:
            return True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rc = cig.generate_image(
        prompt=entry["prompt"],
        output_path=output_path,
        size=entry.get("size"),
    )
    return rc == 0 and output_path.exists()


def regenerate_all(*, force: bool = False) -> dict[str, bool]:
    """Regenerate every library image. Returns id→success map."""
    data = _read_manifest()
    return {id_: regenerate(id_, force=force) for id_ in data.get("images", {})}


def validate_manifest() -> list[str]:
    """Validate the master manifest against LIBRARY_MANIFEST_SCHEMA.

    Returns:
        List of human-readable error strings. Empty list = valid.
    """
    try:
        import jsonschema
    except ModuleNotFoundError as exc:  # pragma: no cover — Dockerfile pins jsonschema
        raise LibraryError(
            "jsonschema not installed; run "
            "`pip install jsonschema==4.26.0` (or rebuild Dockerfile.claude)"
        ) from exc

    try:
        data = _read_manifest()
    except LibraryError as exc:
        return [str(exc)]

    validator = jsonschema.Draft202012Validator(LIBRARY_MANIFEST_SCHEMA)
    errors = []
    for err in validator.iter_errors(data):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{loc}: {err.message}")
    return errors
