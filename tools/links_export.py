#!/usr/bin/env python3
"""Asset exporter for IDML ``Links/`` directories (issue 35, Phase 2).

One-shot bootstrap tool: walks an IDML's sibling ``Links/`` directory, converts
each linked asset to a Scribus-friendly representation under
``shared/assets/<idml-slug>/`` and writes a deterministic ``links_export.yml``
manifest that the IDML→DSL converter consumes via ``--asset-map``.

Dispatch table (locked decision in the issue prompt — no alternatives):

  ``.ai``           → ``pdftocairo -png -transp -r 600 -singlefile <in> <stem>``
  ``.psd``          → ``convert <in> -flatten <out.png>``
  ``.jpg/.jpeg``    → passthrough copy (rename to slug)
  ``.png``          → passthrough copy (rename to slug)
  anything else     → log + skip (post-processor philosophy)

The output filename is ``<slug-of-original-stem>.<output-ext>``. Slug rules
follow ``_slugify`` below; in particular the German umlaut transliterations
(ü→ue, ö→oe, ä→ae, ß→ss) match the rest of the repo's slug convention.

Usage::

    python3 tools/links_export.py \\
        "originals/<bundle>/Links" \\
        --idml-name "originals/<bundle>/<file>.idml"
    # → writes shared/assets/<idml-slug>/<asset-slug>.<ext> + links_export.yml

If ``--out-dir`` is given explicitly, it overrides the auto-derivation.

The tool is **deterministic**: same input → byte-equal output. ``pdftocairo``
and ``convert`` are both deterministic given identical inputs;
``links_export.yml`` is written via ``yaml.safe_dump(sort_keys=True)``.
"""
# License: BSD (matches repo convention).
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent

# German umlaut transliterations applied before generic NFKD stripping. The
# repo's existing slug convention (e.g. shared/assets/.../plakat-dunkel-fuer-flyer)
# expects ü→ue, not the bare 'u' that NFKD would otherwise yield.
_UMLAUT_MAP = str.maketrans(
    {
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        "Ä": "ae", "Ö": "oe", "Ü": "ue",
    }
)


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AssetEntry:
    """One row in the emitted ``links_export.yml``.

    Attributes:
        original_basename: As it appears on disk in ``Links/`` (e.g.
            ``"Plakat dunkel für Flyer.psd"``). NFC-normalised so dictionary
            lookups against macOS-NFD-emitted URI basenames stay stable.
        output_rel: Repo-relative POSIX path to the converted asset, e.g.
            ``"shared/assets/26-03-leporello/plakat-dunkel-fuer-flyer.png"``.
        kind: One of ``vector_ai``, ``raster_psd``, ``raster_jpg``,
            ``raster_png``. Surfaced for downstream tooling that may want to
            dispatch on the source kind.
        recipe: Human-readable description of the conversion command.
    """

    original_basename: str
    output_rel: str
    kind: str
    recipe: str


@dataclass(frozen=True)
class ExportResult:
    """Return value of :func:`export`. Used by tests + the converter glue."""

    out_dir: Path
    manifest_path: Path
    entries: list[AssetEntry]
    skipped: list[tuple[str, str]]  # (basename, reason)


# ---------------------------------------------------------------------------
# Slugification
# ---------------------------------------------------------------------------
def _slugify(text: str) -> str:
    """Slugify a filename stem.

    Rules (verified against the existing logo-map outputs):

    - Apply German umlaut transliteration BEFORE NFKD so ``ü`` → ``ue``,
      not ``u``.
    - NFKD-normalise the rest and drop combining marks.
    - Lowercase ASCII alnum stays; anything else (space, dot, underscore,
      slash, …) collapses to ``-``.
    - Trim leading / trailing ``-``; collapse runs.
    - Empty result raises ``ValueError`` (caller should never feed it an
      empty stem; the dispatcher always has a basename).

    Examples:
        ``BlueSky weiss`` → ``bluesky-weiss``
        ``Grüne Logo Bund weiss CMYK`` → ``gruene-logo-bund-weiss-cmyk``
        ``Plakat dunkel für Flyer`` → ``plakat-dunkel-fuer-flyer``
        ``green-pine-trees-covered-with-fog`` → ``green-pine-trees-covered-with-fog``
    """
    # 1. Translate German umlauts first.
    transliterated = text.translate(_UMLAUT_MAP)
    # 2. NFKD-normalise and drop combining marks (handles other accents).
    nfkd = unicodedata.normalize("NFKD", transliterated)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    # 3. Lowercase, replace anything non-alnum with hyphen.
    lowered = stripped.lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)
    # 4. Collapse runs + trim.
    collapsed = re.sub(r"-+", "-", hyphenated).strip("-")
    if not collapsed:
        raise ValueError(f"slugify produced empty string for {text!r}")
    return collapsed


def slugify_stem(name: str) -> str:
    """Public wrapper around :func:`_slugify`. Stable across releases."""
    return _slugify(name)


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Recipe:
    kind: str
    out_ext: str
    description: str  # human-readable; goes into links_export.yml


_DISPATCH: dict[str, _Recipe] = {
    ".ai": _Recipe(
        kind="vector_ai",
        out_ext=".png",
        description="pdftocairo -png -transp -r 600 -singlefile",
    ),
    ".psd": _Recipe(
        kind="raster_psd",
        out_ext=".png",
        description="convert -flatten",
    ),
    ".jpg": _Recipe(
        kind="raster_jpg",
        out_ext=".jpg",
        description="passthrough",
    ),
    ".jpeg": _Recipe(
        kind="raster_jpg",
        out_ext=".jpg",
        description="passthrough",
    ),
    ".png": _Recipe(
        kind="raster_png",
        out_ext=".png",
        description="passthrough",
    ),
}


def kind_for_extension(ext: str) -> Optional[str]:
    """Return the recipe kind for an extension, or ``None`` if unsupported."""
    recipe = _DISPATCH.get(ext.lower())
    return recipe.kind if recipe else None


# ---------------------------------------------------------------------------
# Conversion implementations
# ---------------------------------------------------------------------------
def _run(cmd: list[str]) -> None:
    """Run a command; raise RuntimeError on non-zero exit (captured stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed (rc={result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def _convert_ai(src: Path, out_path: Path) -> None:
    """``.ai`` → transparent PNG at 600 DPI via pdftocairo.

    AI files since CS2 are PDF-compatible; pdftocairo reads the bundled PDF
    stream and rasterises it. ``-singlefile`` writes ``<prefix>.png`` instead
    of ``<prefix>-1.png``; we pass the OUTPUT WITHOUT EXTENSION as the prefix
    per pdftocairo's CLI contract.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = out_path.with_suffix("")  # strip .png — pdftocairo appends it
    _run([
        "pdftocairo",
        "-png", "-transp", "-r", "600", "-singlefile",
        str(src), str(prefix),
    ])
    if not out_path.exists():  # pragma: no cover — defensive
        raise RuntimeError(
            f"pdftocairo did not produce {out_path} from {src}"
        )


def _convert_psd(src: Path, out_path: Path) -> None:
    """``.psd`` → ICC-profile-aware flattened PNG via Pillow.

    CMYK PSD files from print workflows embed ICC profiles (e.g. Coated
    FOGRA39).  ImageMagick's ``convert -flatten`` ignores these profiles,
    producing near-white pixels where the CMYK values are close to zero ink
    (i.e. a white paper assumption).  Pillow's ``ImageCms`` transforms the
    CMYK data using the embedded source ICC profile to sRGB, matching how
    InDesign and Acrobat render the image.

    For non-CMYK PSDs (RGB, RGBA, Grayscale) the ICC correction path is
    skipped and the image is saved directly as sRGB PNG.

    Determinism: Pillow's PNG encoder does not embed filesystem timestamps,
    so byte-equal output is expected for identical inputs.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageCms  # type: ignore[import-untyped]
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Pillow is required to convert PSD files: "
            "pip install Pillow  (extend tools/links_export.py:_convert_psd)"
        ) from e

    img = Image.open(str(src))
    # Flatten all layers by converting to the base mode (Pillow flattens
    # on open for PSDs — the mode reflects the composite).
    if img.mode == "CMYK":
        # Apply the embedded ICC profile for a perceptually correct sRGB render.
        # Fall back to a naïve inversion (1 - C/255) if no profile is embedded.
        icc_bytes = img.info.get("icc_profile")
        if icc_bytes:
            src_profile = ImageCms.ImageCmsProfile(
                __import__("io").BytesIO(icc_bytes)
            )
            dst_profile = ImageCms.createProfile("sRGB")
            transform = ImageCms.buildTransformFromOpenProfiles(
                src_profile, dst_profile,
                img.mode, "RGB",
            )
            img = ImageCms.applyTransform(img, transform)
        else:
            # No embedded profile — naïve CMYK→RGB inversion.
            import numpy as np  # type: ignore[import-untyped]
            arr = np.array(img, dtype=float) / 255.0
            c, m, y, k = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
            r = (1 - c) * (1 - k)
            g = (1 - m) * (1 - k)
            b = (1 - y) * (1 - k)
            rgb = (np.stack([r, g, b], axis=-1) * 255).clip(0, 255).astype("uint8")
            img = Image.fromarray(rgb, mode="RGB")
    elif img.mode not in ("RGB", "RGBA", "L", "LA"):
        img = img.convert("RGB")

    img.save(str(out_path), format="PNG")


def _passthrough_copy(src: Path, out_path: Path) -> None:
    """Copy a raster source to its slugified output path (no transform)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out_path)


# ---------------------------------------------------------------------------
# Top-level export
# ---------------------------------------------------------------------------
def derive_out_dir(idml_path: Path) -> Path:
    """Auto-derive ``shared/assets/<idml-slug>/`` from an IDML path."""
    return ROOT / "shared" / "assets" / _slugify(idml_path.stem)


def _emit_manifest(
    out_dir: Path,
    links_dir: Path,
    entries: list[AssetEntry],
    skipped: list[tuple[str, str]],
) -> Path:
    """Write ``links_export.yml`` to ``out_dir``. Returns the path written.

    Deterministic: keys sorted via ``yaml.safe_dump(sort_keys=True)``. The
    relative `Source:` comment uses a POSIX path so the manifest is portable
    across platforms.
    """
    manifest_path = out_dir / "links_export.yml"
    # Build the assets block — original basename is the key (NFC-normalised).
    assets_block: dict[str, dict[str, str]] = {}
    for entry in entries:
        assets_block[entry.original_basename] = {
            "output": entry.output_rel,
            "kind": entry.kind,
            "recipe": entry.recipe,
        }
    skipped_block: dict[str, str] = {bn: reason for bn, reason in skipped}

    try:
        links_rel = links_dir.resolve().relative_to(ROOT)
        source_comment = str(links_rel).replace("\\", "/")
    except ValueError:
        source_comment = str(links_dir.resolve())

    header = (
        "# links_export.yml — auto-generated by tools/links_export.py\n"
        f"# Source: {source_comment}/\n"
        "# Run: python3 tools/links_export.py <links-dir> --idml-name <idml-path>\n"
    )
    body: dict[str, object] = {"assets": assets_block}
    if skipped_block:
        body["skipped"] = skipped_block
    rendered = yaml.safe_dump(body, sort_keys=True, allow_unicode=True)
    manifest_path.write_text(header + rendered, encoding="utf-8")
    return manifest_path


def export(
    links_dir: Path,
    out_dir: Path,
    *,
    quiet: bool = False,
) -> ExportResult:
    """Walk ``links_dir`` and produce converted assets + a manifest.

    Args:
        links_dir: The IDML's sibling ``Links/`` directory to walk.
        out_dir: Where to write converted assets + ``links_export.yml``.
        quiet: If True, suppress informational prints. Errors still raise.

    Returns:
        :class:`ExportResult` summarising what was emitted + skipped.

    Raises:
        FileNotFoundError: ``links_dir`` does not exist.
        RuntimeError: an underlying ``pdftocairo`` / ``convert`` command failed.
    """
    if not links_dir.exists():
        raise FileNotFoundError(f"Links directory not found: {links_dir}")
    if not links_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {links_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)

    entries: list[AssetEntry] = []
    skipped: list[tuple[str, str]] = []

    # Deterministic walk — sorted by NFC-normalised filename.
    files = sorted(
        (p for p in links_dir.iterdir() if p.is_file() and not p.name.startswith(".")),
        key=lambda p: unicodedata.normalize("NFC", p.name),
    )

    for src in files:
        basename_nfc = unicodedata.normalize("NFC", src.name)
        ext = src.suffix.lower()
        recipe = _DISPATCH.get(ext)
        if recipe is None:
            reason = f"unsupported extension {ext!r}"
            skipped.append((basename_nfc, reason))
            if not quiet:
                print(f"SKIP: {basename_nfc} — {reason}", file=sys.stderr)
            continue

        out_stem = _slugify(src.stem)
        out_name = f"{out_stem}{recipe.out_ext}"
        out_path = out_dir / out_name

        if ext == ".ai":
            _convert_ai(src, out_path)
        elif ext == ".psd":
            _convert_psd(src, out_path)
        else:  # passthrough raster (jpg/jpeg/png)
            _passthrough_copy(src, out_path)

        try:
            output_rel = str(out_path.resolve().relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            output_rel = str(out_path.resolve())

        entries.append(AssetEntry(
            original_basename=basename_nfc,
            output_rel=output_rel,
            kind=recipe.kind,
            recipe=recipe.description,
        ))
        if not quiet:
            print(f"OK: {basename_nfc} → {output_rel}", file=sys.stderr)

    manifest_path = _emit_manifest(out_dir, links_dir, entries, skipped)
    if not quiet:
        print(
            f"OK: wrote {manifest_path} "
            f"({len(entries)} converted, {len(skipped)} skipped)",
            file=sys.stderr,
        )

    return ExportResult(
        out_dir=out_dir,
        manifest_path=manifest_path,
        entries=entries,
        skipped=skipped,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Export an IDML Links/ directory to shared/assets/<slug>/ "
            "(one-shot bootstrap; see tools/idml_to_dsl.py --asset-map)."
        ),
    )
    ap.add_argument(
        "links_dir", type=Path,
        help="The IDML's sibling Links/ directory.",
    )
    ap.add_argument(
        "--out-dir", type=Path, default=None,
        help=(
            "Destination directory for converted assets + links_export.yml. "
            "If omitted, derived from --idml-name as "
            "shared/assets/<idml-slug>/."
        ),
    )
    ap.add_argument(
        "--idml-name", type=Path, default=None,
        help=(
            "Path or filename of the source IDML; its slugified stem "
            "becomes the <idml-slug> for the default --out-dir."
        ),
    )
    ap.add_argument(
        "--quiet", action="store_true",
        help="Suppress informational stderr output.",
    )
    args = ap.parse_args(argv)

    if args.out_dir is None:
        if args.idml_name is None:
            ap.error("either --out-dir or --idml-name must be provided")
        out_dir = derive_out_dir(args.idml_name)
    else:
        out_dir = args.out_dir

    try:
        export(args.links_dir, out_dir, quiet=args.quiet)
    except (FileNotFoundError, NotADirectoryError, RuntimeError, ValueError) as e:
        print(f"links_export: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
