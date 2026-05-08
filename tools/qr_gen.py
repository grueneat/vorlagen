#!/usr/bin/env python3
"""tools/qr_gen.py — branded QR-code generator (issue #11, one-shot).

Reads a template's ``samples/manifest.yml`` and writes one PNG per
``qr_codes:`` entry. Output is byte-deterministic across runs and decodes
back to the manifest's ``target_url`` via ``pyzbar.decode()``.

Pin requirements (D9 determinism — keep in sync with Dockerfile.claude):
  - ``qrcode[pil]==8.2``
  - ``Pillow>=12.2``
Both are pinned in the container image. Two consecutive runs with identical
inputs MUST yield byte-identical PNGs (test: ``test_qr_byte_determinism``).

Authoring-only: this tool runs once per template during the issue's execute
phase. Generated PNGs are committed to ``templates/<slug>/samples/``; the
build pipeline never invokes ``qr_gen``.

Branding (D1 from CONTEXT.md):
  - Modules in ``Dunkelgrün`` sRGB (28, 72, 33) — derived from the brand
    CMYK 85/35/95/10 inside `shared/ci.yml`.
  - Optional center-logo embed (Sonnenblume, monochrome, pre-circular-masked).
  - ``error_correction='H'`` (~30% recovery) so the logo doesn't block scan.
  - Quiet zone ≥ 4 modules (``border=4``).
  - Module size in finished print stays ≥ 0.5 mm (caller responsible —
    qr_gen renders at the requested ``box_size`` px and lets layout decide
    the physical size in mm).

Manifest schema (subset relevant to this tool)::

    # templates/<slug>/samples/manifest.yml
    qr_codes:
      - name: qr-back
        target_url: https://noe.gruene.at/
        output_path: samples/qr-back.png
        module_color: [28, 72, 33]
        background_color: [255, 255, 255]
        embed_logo: shared/logos/sonnenblume-circle.png   # optional
        error_correction: H                                # L|M|Q|H
        box_size: 10
        border: 4
        version: null                                      # optional, auto-fits
        note: "Demo URL — endusers replace with their Bezirks-URL"

Usage::

    python3 tools/qr_gen.py templates/<slug>          # reads samples/manifest.yml
    python3 tools/qr_gen.py templates/<slug>/samples/manifest.yml
    python3 tools/qr_gen.py --help

See also: research/ecosystem.md section 1 (empirical SHA-256 byte-determinism
results, qrcode 8.2 + Pillow 12.2.0).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import qrcode
import yaml
from PIL import Image, ImageDraw
from qrcode.constants import (
    ERROR_CORRECT_H,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
)
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask

# D1: sRGB approximation of CMYK Dunkelgrün 85/35/95/10 — matches shared/ci.yml.
DUNKELGRUEN_RGB: tuple[int, int, int] = (28, 72, 33)
WHITE_RGB: tuple[int, int, int] = (255, 255, 255)

ECC_MAP: dict[str, int] = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


def generate_qr_png(
    target_url: str,
    output_path: Path,
    *,
    module_color: tuple[int, int, int] = DUNKELGRUEN_RGB,
    background_color: tuple[int, int, int] = WHITE_RGB,
    embed_logo: Path | None = None,
    error_correction: str = "H",
    box_size: int = 10,
    border: int = 4,
    version: int | None = None,
) -> Path:
    """Render a deterministic, scannable QR PNG to ``output_path``.

    Returns ``output_path`` for chainability.

    Args:
        target_url: URL/text to encode.
        output_path: Filesystem destination; parent dir is created if missing.
        module_color: sRGB triplet for QR modules. Default Dunkelgrün (D1).
        background_color: sRGB triplet for the QR background. Default white.
        embed_logo: Optional path to a circular pre-masked logo PNG. Pass a
            ``Path`` whose alpha is 0 outside the inscribed circle. Use
            :func:`circular_mask` first if your source is opaque-square.
            ECC=H is required to absorb the center occlusion.
        error_correction: One of ``L|M|Q|H``. Default ``H`` (D1).
        box_size: Pixel size of one QR module. Default 10.
        border: Quiet-zone width in modules. Default 4 (QR-spec minimum).
        version: Optional fixed QR version (1–40). ``None`` auto-fits.

    Determinism: with qrcode==8.2 + Pillow==12.2.0 + ``optimize=True``, two
    invocations with identical inputs yield byte-identical PNGs (verified in
    :mod:`tests.test_qr_gen`). Do NOT add timestamps or non-deterministic
    metadata to the output path.
    """
    if error_correction not in ECC_MAP:
        raise ValueError(
            f"error_correction must be one of {sorted(ECC_MAP)}, "
            f"got {error_correction!r}"
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    qr = qrcode.QRCode(
        version=version,
        error_correction=ECC_MAP[error_correction],
        box_size=box_size,
        border=border,
    )
    qr.add_data(target_url)
    qr.make(fit=True)

    kwargs: dict = {
        "image_factory": StyledPilImage,
        "color_mask": SolidFillColorMask(
            front_color=tuple(module_color),
            back_color=tuple(background_color),
        ),
    }
    if embed_logo is not None:
        embed_logo = Path(embed_logo)
        if embed_logo.exists():
            kwargs["embedded_image_path"] = str(embed_logo)

    img = qr.make_image(**kwargs)
    # ``optimize=True`` strips Pillow metadata that would otherwise drift
    # between runs. ``format="PNG"`` is explicit so the output is stable
    # regardless of the path's extension casing.
    img.save(str(output_path), format="PNG", optimize=True)
    return output_path


def circular_mask(src_path: Path, dst_path: Path) -> Path:
    """Pre-mask a square logo to a circle (alpha=0 outside the inscribed circle).

    Idempotent: if the source is already pre-masked (``alpha=0`` at the
    corners) the operation is still safe — it re-writes the same alpha
    pattern. Returns ``dst_path``.
    """
    src = Image.open(str(src_path)).convert("RGBA")
    w, h = src.size
    side = min(w, h)
    # Center-crop to a square so the inscribed circle is well-defined.
    left = (w - side) // 2
    top = (h - side) // 2
    src = src.crop((left, top, left + side, top + side))

    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, side - 1, side - 1), fill=255)

    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(src, (0, 0), mask=mask)

    dst_path = Path(dst_path)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(str(dst_path), format="PNG", optimize=True)
    return dst_path


def parse_manifest(manifest_path: Path) -> dict:
    """Read a templates/<slug>/samples/manifest.yml file.

    Permissive: missing ``qr_codes:`` key returns ``{"qr_codes": []}``;
    missing ``images:`` key returns ``{"images": []}``. This shape mirrors
    :func:`tools.codex_image_gen.parse_manifest` so the two tools can share
    manifests without coupling.

    Relative ``output_path`` and ``embed_logo`` values are NOT resolved here
    — the caller decides the base directory (typically the manifest's
    parent so paths read as ``samples/foo.png``).
    """
    manifest_path = Path(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{manifest_path}: top-level YAML must be a mapping")
    data.setdefault("qr_codes", [])
    data.setdefault("images", [])
    if not isinstance(data["qr_codes"], list):
        raise ValueError(f"{manifest_path}: 'qr_codes' must be a list")
    if not isinstance(data["images"], list):
        raise ValueError(f"{manifest_path}: 'images' must be a list")
    return data


def _resolve_manifest_path(arg: Path) -> Path:
    """Accept either ``templates/<slug>`` or the manifest file directly."""
    p = Path(arg)
    if p.is_dir():
        cand = p / "samples" / "manifest.yml"
        if cand.exists():
            return cand
        raise FileNotFoundError(f"no manifest found at {cand}")
    if p.is_file():
        return p
    raise FileNotFoundError(f"no such path: {p}")


def _generate_one(spec: dict, base_dir: Path, repo_root: Path) -> tuple[bool, str]:
    """Render a single qr_codes entry. Returns (ok, message).

    Path resolution:
      - ``output_path`` is relative to ``base_dir`` (the template root).
      - ``embed_logo`` is relative to ``repo_root`` (e.g. ``shared/logos/…``).
        Falls back to relative-to-base_dir if not found at repo root.
    """
    name = spec.get("name", "<unnamed>")
    url = spec.get("target_url")
    out_rel = spec.get("output_path")
    if not url or not out_rel:
        return False, f"FAIL {name}: missing target_url or output_path"

    out_path = base_dir / out_rel

    module_color = tuple(spec.get("module_color", DUNKELGRUEN_RGB))
    background_color = tuple(spec.get("background_color", WHITE_RGB))
    ecc = spec.get("error_correction", "H")
    box_size = int(spec.get("box_size", 10))
    border = int(spec.get("border", 4))
    version = spec.get("version")

    embed_logo_rel = spec.get("embed_logo")
    embed_logo: Path | None = None
    if embed_logo_rel:
        # Try repo-root-relative first (canonical for shared/ paths), then
        # fall back to template-relative.
        for cand in (repo_root / embed_logo_rel, base_dir / embed_logo_rel):
            if cand.exists():
                embed_logo = cand
                break
        if embed_logo is None:
            print(
                f"WARN {name}: embed_logo {embed_logo_rel} not found "
                f"(searched {repo_root} and {base_dir}); "
                f"rendering without logo",
                file=sys.stderr,
            )

    try:
        generate_qr_png(
            url,
            out_path,
            module_color=module_color,
            background_color=background_color,
            embed_logo=embed_logo,
            error_correction=ecc,
            box_size=box_size,
            border=border,
            version=version,
        )
    except Exception as exc:
        return False, f"FAIL {name}: {exc}"

    sha = hashlib.sha256(out_path.read_bytes()).hexdigest()[:16]
    return True, f"OK {name} -> {out_path} (sha256={sha})"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Usage:
        python3 tools/qr_gen.py templates/<slug>
        python3 tools/qr_gen.py templates/<slug>/samples/manifest.yml
    """
    parser = argparse.ArgumentParser(
        description=(
            "Render branded QR PNGs for a template's samples/manifest.yml. "
            "Deterministic across runs; one PNG per qr_codes[] entry."
        ),
    )
    parser.add_argument(
        "target",
        type=Path,
        nargs="?",
        help=(
            "Either a templates/<slug> directory or a manifest.yml file. "
            "When a directory is given, samples/manifest.yml is read."
        ),
    )
    args = parser.parse_args(argv)

    if args.target is None:
        parser.print_help()
        return 0

    try:
        manifest_path = _resolve_manifest_path(args.target)
    except FileNotFoundError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    base_dir = manifest_path.parent.parent  # .../templates/<slug>
    repo_root = Path(__file__).resolve().parent.parent
    try:
        manifest = parse_manifest(manifest_path)
    except (ValueError, yaml.YAMLError) as exc:
        sys.stderr.write(f"manifest parse error: {exc}\n")
        return 1

    qr_specs = manifest.get("qr_codes", [])
    if not qr_specs:
        print(f"{manifest_path}: no qr_codes entries; nothing to do.")
        return 0

    failures: list[str] = []
    for spec in qr_specs:
        if not isinstance(spec, dict):
            failures.append(f"FAIL <non-dict entry>: {spec!r}")
            continue
        ok, msg = _generate_one(spec, base_dir, repo_root)
        print(msg)
        if not ok:
            failures.append(msg)

    if failures:
        sys.stderr.write(f"\n{len(failures)} failure(s):\n")
        for msg in failures:
            sys.stderr.write(f"  {msg}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
