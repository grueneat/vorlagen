#!/usr/bin/env python3
"""Asset exporter for IDML ``Links/`` directories (issue 35, Phase 2).

One-shot bootstrap tool: walks an IDML's sibling ``Links/`` directory, converts
each linked asset to a Scribus-friendly representation under
``shared/assets/<idml-slug>/`` and writes a deterministic ``links_export.yml``
manifest that the IDML→DSL converter consumes via ``--asset-map``.

Dispatch table:

  ``.ai``           → ``pdftocairo -png -transp -r 600 -singlefile <in> <stem>``
  ``.psd``          → ICC-aware CMYK→sRGB PNG (RGB PSDs pass through to PNG)
  ``.jpg/.jpeg``    → passthrough copy IF the source is already RGB; CMYK
                      JPEGs are converted to an ICC-aware sRGB PNG instead
  ``.png``          → passthrough copy (rename to slug)
  anything else     → log + skip (post-processor philosophy)

CMYK colour handling — both PSD and JPEG sources arrive from print
workflows in CMYK with an embedded ICC profile (e.g. Coated FOGRA39).
Scribus 1.6.x cannot render a CMYK JPEG at all (it shows fully blank), and a
naive (non-ICC) CMYK→RGB inversion posterises the colours.  Every CMYK
raster is therefore passed through ImageMagick's ICC-aware transform
(``convert <in> -profile <sRGB.icc> -strip <out.png>``) which uses the
embedded source profile for a perceptually correct sRGB render — matching
how InDesign and Acrobat display the image.  ImageMagick (not Pillow) is
used because Pillow's PSD plugin reads the individual CMYK layer tiles
instead of the merged composite, producing channel-ghosted output on
multi-layer print PSDs.  ``-strip`` drops the ICC chunk from the PNG since
Scribus 1.6.x silently skips PNGs that carry an embedded ``iCCP`` block.
The PSD cutout alpha channel is preserved (no ``-flatten``).

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
        vector_output_rel: Repo-relative POSIX path to the PDF vector copy
            (only set for ``.ai`` sources; issue #38 Task 14). The PDF lets
            the converter emit ImageFrame(image=<pdf>) for vector preservation.
    """

    original_basename: str
    output_rel: str
    kind: str
    recipe: str
    vector_output_rel: str | None = None


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
        description="convert -profile sRGB -strip (ICC-aware)",
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


# sRGB ICC profile used as the destination for every CMYK→sRGB conversion.
# The repo's Scribus install ships this profile and its description string
# ("sRGB display profile (ICC v2.2)") is the per-frame PRFILE the SLA emitter
# writes by default, so the converted assets and the SLA agree on colour
# space. The candidate list is tried in order; the first existing path wins.
_SRGB_ICC_CANDIDATES: tuple[str, ...] = (
    "/usr/share/scribus/profiles/sRGB_icc22.icm",
    "/usr/share/color/icc/ghostscript/srgb.icc",
    "/usr/share/color/icc/sRGB.icc",
)


def _srgb_icc_path() -> Optional[str]:
    """Return the first available sRGB ICC profile path, or ``None``."""
    for candidate in _SRGB_ICC_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None


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


def _convert_ai(src: Path, out_path: Path) -> Path | None:
    """``.ai`` → transparent PNG at 600 DPI via pdftocairo AND a PDF passthrough.

    AI files since CS2 are PDF-compatible; pdftocairo reads the bundled PDF
    stream and rasterises it. ``-singlefile`` writes ``<prefix>.png`` instead
    of ``<prefix>-1.png``; we pass the OUTPUT WITHOUT EXTENSION as the prefix
    per pdftocairo's CLI contract.

    Issue #38 Task 14: in addition to the PNG raster, copy the AI verbatim to
    ``<out_path stem>.pdf``. The PDF copy preserves vector data so the
    converter can emit ImageFrame(image=<pdf>) when the
    image_frame_pdf_source_for_vectors pattern applies. Returns the PDF path
    when written, or None when the source cannot be passed through as PDF.
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
    # PDF passthrough — AI files since CS2 ARE valid PDFs. shutil.copy is
    # deterministic and cheap; the converter / downstream consumers can
    # ignore the .pdf if they prefer raster.
    pdf_out = out_path.with_suffix(".pdf")
    try:
        shutil.copy(src, pdf_out)
        return pdf_out
    except OSError:
        return None


def _is_cmyk_raster(src: Path) -> bool:
    """Return True when ``src`` is a CMYK (colour-separated) raster.

    Used to decide whether a JPEG needs the ICC-aware CMYK→sRGB transform or
    can be passed through verbatim. Reads only the header via Pillow.
    """
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:  # pragma: no cover
        return False
    try:
        with Image.open(str(src)) as img:
            return img.mode == "CMYK"
    except Exception:  # pragma: no cover — defensive; corrupt source
        return False


def _convert_cmyk_to_srgb_png(src: Path, out_path: Path) -> None:
    """Convert a CMYK raster (PSD or JPEG) to an ICC-aware sRGB PNG.

    Uses ImageMagick: ``convert <src> -profile <sRGB.icc> -strip <out.png>``.
    ImageMagick reads the embedded source ICC profile, transforms the CMYK
    pixels into the target sRGB space, and ``-strip`` removes every metadata
    chunk (including ``iCCP``) so Scribus 1.6.x — which silently drops PNGs
    carrying an ICC profile — can load the file.

    ImageMagick is used in preference to Pillow because Pillow's PSD plugin
    reads the per-channel layer tiles of a multi-layer print PSD rather than
    the merged composite, which produces channel-ghosted output. ImageMagick
    composites the PSD correctly. A multi-layer PSD's first frame ``[0]`` is
    the flattened composite.

    The PSD cutout alpha channel (transparent background of a knocked-out
    subject) is preserved — no ``-flatten`` is applied.

    Determinism: ImageMagick's PNG encoder writes no filesystem timestamps,
    so byte-equal output is expected for identical inputs + profile.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    srgb = _srgb_icc_path()
    if srgb is None:
        raise RuntimeError(
            "No sRGB ICC profile found for CMYK→sRGB conversion; looked in "
            f"{_SRGB_ICC_CANDIDATES}. Install a colour profile package "
            "(extend tools/links_export.py:_SRGB_ICC_CANDIDATES)."
        )
    # ``[0]`` selects the merged composite frame of a multi-layer PSD; for a
    # single-frame JPEG it is a harmless no-op.
    _run([
        "convert",
        f"{src}[0]",
        "-profile", srgb,
        "-strip",
        str(out_path),
    ])
    if not out_path.exists():  # pragma: no cover — defensive
        raise RuntimeError(
            f"convert did not produce {out_path} from {src}"
        )


def _convert_psd(src: Path, out_path: Path) -> None:
    """``.psd`` → sRGB PNG.

    CMYK PSDs go through the ICC-aware ImageMagick transform
    (:func:`_convert_cmyk_to_srgb_png`). RGB / RGBA / Grayscale PSDs are
    converted to a plain sRGB PNG with Pillow — they need no colour
    transform, only a Scribus-readable container.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if _is_cmyk_raster(src):
        _convert_cmyk_to_srgb_png(src, out_path)
        return
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Pillow is required to convert PSD files: "
            "pip install Pillow  (extend tools/links_export.py:_convert_psd)"
        ) from e
    img = Image.open(str(src))
    if img.mode not in ("RGB", "RGBA", "L", "LA"):
        img = img.convert("RGB")
    # icc_profile=None suppresses Pillow re-embedding an ICC chunk; Scribus
    # 1.6.x silently skips PNGs that carry one.
    img.save(str(out_path), format="PNG", icc_profile=None)


def _convert_jpg(src: Path, out_path: Path) -> None:
    """``.jpg`` / ``.jpeg`` → Scribus-friendly raster.

    RGB JPEGs are passed through verbatim (``out_path`` keeps the ``.jpg``
    extension). CMYK JPEGs cannot be rendered by Scribus 1.6.x at all — they
    show fully blank — so they are converted to an ICC-aware sRGB PNG; the
    caller is responsible for having resolved ``out_path`` to a ``.png``
    extension for the CMYK case (see :func:`out_ext_for`).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if _is_cmyk_raster(src):
        _convert_cmyk_to_srgb_png(src, out_path)
        return
    shutil.copyfile(src, out_path)


def out_ext_for(src: Path) -> str:
    """Return the output extension the dispatcher should use for ``src``.

    Static for every kind except JPEG: a CMYK JPEG is converted to a PNG
    (Scribus cannot render CMYK JPEGs) so its output extension is ``.png``,
    while an RGB JPEG passes through as ``.jpg``.
    """
    ext = src.suffix.lower()
    recipe = _DISPATCH.get(ext)
    if recipe is None:
        raise ValueError(f"no recipe for extension {ext!r}")
    if ext in (".jpg", ".jpeg") and _is_cmyk_raster(src):
        return ".png"
    return recipe.out_ext


def _passthrough_copy(src: Path, out_path: Path) -> None:
    """Copy a raster source to its slugified output path (no transform).

    Used for ``.png`` sources, which Scribus reads directly.
    """
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
        row: dict[str, str] = {
            "output": entry.output_rel,
            "kind": entry.kind,
            "recipe": entry.recipe,
        }
        # Issue #38 Task 14: vector_output is emitted only for .ai sources
        # where the PDF passthrough succeeded.
        if entry.vector_output_rel:
            row["vector_output"] = entry.vector_output_rel
        assets_block[entry.original_basename] = row
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
        # CMYK JPEGs are converted to PNG (Scribus cannot render CMYK JPEGs),
        # so the output extension is resolved per-file rather than statically.
        out_ext = out_ext_for(src)
        out_name = f"{out_stem}{out_ext}"
        out_path = out_dir / out_name

        vector_output_rel: str | None = None
        recipe_description = recipe.description
        if ext == ".ai":
            pdf_path = _convert_ai(src, out_path)
            if pdf_path is not None and pdf_path.exists():
                try:
                    vector_output_rel = str(
                        pdf_path.resolve().relative_to(ROOT)
                    ).replace("\\", "/")
                except ValueError:
                    vector_output_rel = str(pdf_path.resolve())
        elif ext == ".psd":
            _convert_psd(src, out_path)
        elif ext in (".jpg", ".jpeg"):
            _convert_jpg(src, out_path)
            # A CMYK JPEG was converted (its output ext is .png); surface that
            # in the manifest recipe so downstream tooling sees the transform.
            if out_ext == ".png":
                recipe_description = "convert -profile sRGB -strip (ICC-aware)"
        else:  # passthrough raster (png)
            _passthrough_copy(src, out_path)

        try:
            output_rel = str(out_path.resolve().relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            output_rel = str(out_path.resolve())

        entries.append(AssetEntry(
            original_basename=basename_nfc,
            output_rel=output_rel,
            kind=recipe.kind,
            recipe=recipe_description,
            vector_output_rel=vector_output_rel,
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
