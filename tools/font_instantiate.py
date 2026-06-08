#!/usr/bin/env python3
"""Instantiate static per-weight TTFs from Google Fonts variable fonts.

Four of the five Gotham alternatives (Montserrat, Outfit, Urbanist, Raleway)
ship on github.com/google/fonts only as ``[wght]`` variable fonts. Scribus
exposes a variable font under a single name (its default named instance), so
referencing four distinct weights of the same VF is not possible — every
weight would collapse onto the default instance and the comparison would lose
weight differentiation.

This tool downloads each VF, pins the ``wght`` axis to the four weights the
flyer needs and rewrites the name table so each weight registers as a proper
static family ``family="<Base>"`` / ``subfamily="<Weight>"``. That is the same
shape the static Barlow Semi Condensed files already have, so Scribus exposes
each as ``"<Base> <Weight>"`` — exactly the names tools/font_variants.py
writes into the variant SLAs.

The generated static TTFs are committed under
``shared/fonts/alternatives/<slug>/``; the variable fonts are not kept. Run
this only to regenerate them (e.g. to pick up an upstream font update).

Requires ``fonttools`` (``pip install fonttools brotli``).

CLI:
  python3 tools/font_instantiate.py
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALT_DIR = ROOT / "shared" / "fonts" / "alternatives"

_RAW = "https://raw.githubusercontent.com/google/fonts/main/ofl"

# slug -> (ofl directory, VF file name, base family, {weight label: wght value})
JOBS: dict[str, tuple[str, str, str, dict[str, int]]] = {
    "montserrat": (
        "montserrat",
        "Montserrat[wght].ttf",
        "Montserrat",
        {"Regular": 400, "Bold": 700, "ExtraBold": 800, "Black": 900},
    ),
    "outfit": (
        "outfit",
        "Outfit[wght].ttf",
        "Outfit",
        {"Regular": 400, "Bold": 700, "ExtraBold": 800, "Black": 900},
    ),
    "urbanist": (
        "urbanist",
        "Urbanist[wght].ttf",
        "Urbanist",
        {"Regular": 400, "Bold": 700, "ExtraBold": 800, "Black": 900},
    ),
    "raleway": (
        "raleway",
        "Raleway[wght].ttf",
        "Raleway",
        {"Regular": 400, "Bold": 700, "ExtraBold": 800, "Black": 900},
    ),
}

# Families that github.com/google/fonts ships as STATIC per-weight TTFs rather
# than a [wght] variable font (Saira Semi Condensed lives under
# ofl/sairasemicondensed as discrete instances). They need no axis pinning —
# only the same name-table normalisation so each weight registers as
# "<Base> <Weight>" the way the instantiated families do. slug -> (ofl dir,
# base family, {weight label: source file name}).
STATIC_JOBS: dict[str, tuple[str, str, dict[str, str]]] = {
    "saira-semi-condensed": (
        "sairasemicondensed",
        "Saira SemiCondensed",
        {
            "Regular": "SairaSemiCondensed-Regular.ttf",
            "Bold": "SairaSemiCondensed-Bold.ttf",
            "ExtraBold": "SairaSemiCondensed-ExtraBold.ttf",
            "Black": "SairaSemiCondensed-Black.ttf",
        },
    ),
}

# Windows / Mac name-record IDs to overwrite so every platform reads the same
# static family and subfamily strings.
_NAME_PLATFORMS = ((3, 1, 0x409), (1, 0, 0))


def _download(ofl_dir: str, vf_name: str, dest: Path) -> None:
    """Fetch a variable font from the google/fonts repo into ``dest``."""
    url = f"{_RAW}/{ofl_dir}/{vf_name.replace('[', '%5B').replace(']', '%5D')}"
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        dest.write_bytes(resp.read())


def instantiate_family(
    slug: str, ofl_dir: str, vf_name: str, base: str, weights: dict[str, int]
) -> list[Path]:
    """Produce static per-weight TTFs for one family. Returns written paths."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    out_dir = ALT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    vf_path = out_dir / vf_name
    _download(ofl_dir, vf_name, vf_path)

    written: list[Path] = []
    for label, wght in weights.items():
        font = TTFont(str(vf_path))
        instantiateVariableFont(font, {"wght": wght}, inplace=True)

        name = font["name"]
        full = f"{base} {label}"
        for plat in _NAME_PLATFORMS:
            # IDs 1/16 family, 2/17 subfamily, 4 full, 6 postscript.
            name.setName(base, 1, *plat)
            name.setName(label, 2, *plat)
            name.setName(base, 16, *plat)
            name.setName(label, 17, *plat)
            name.setName(full, 4, *plat)
            name.setName(full.replace(" ", ""), 6, *plat)

        out = out_dir / f"{base.replace(' ', '')}-{label}.ttf"
        font.save(str(out))
        written.append(out)
        print(f"[font_instantiate] {slug}: {out.name} ({out.stat().st_size} bytes)")

    vf_path.unlink()
    return written



def rename_static_family(
    slug: str, ofl_dir: str, base: str, files: dict[str, str]
) -> list[Path]:
    """Normalise the name tables of ready-made static per-weight TTFs.

    Google Fonts ships some families (e.g. Saira Semi Condensed) as discrete
    static instances whose name tables use the RIBBI-overflow grouping
    (``family="Saira SemiCondensed,Saira SemiCondensed ExtraBold"``). Scribus
    then cannot address the weights cleanly. This downloads each weight and
    rewrites its name records to ``family="<Base>"`` / ``subfamily="<Weight>"``
    — the same shape instantiate_family() produces — so Scribus exposes each as
    ``"<Base> <Weight>"``. Returns written paths.
    """
    from fontTools.ttLib import TTFont

    out_dir = ALT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for label, src_name in files.items():
        src = out_dir / src_name
        if not src.exists():
            _download(ofl_dir, src_name, src)
        font = TTFont(str(src))
        name = font["name"]
        full = f"{base} {label}"
        for plat in _NAME_PLATFORMS:
            name.setName(base, 1, *plat)
            name.setName(label, 2, *plat)
            name.setName(base, 16, *plat)
            name.setName(label, 17, *plat)
            name.setName(full, 4, *plat)
            name.setName(full.replace(" ", ""), 6, *plat)
        # Normalise vertical metrics. Some Google Fonts static instances (Saira
        # Semi Condensed: hhea 1135/-439 → 1.57x line height) carry oversized
        # vertical metrics that make Scribus' automatic leading explode and
        # overflow fixed text frames. Pin the leading metrics to a 1.2x line
        # height (matching the other bundled alternatives, e.g. Barlow) while
        # keeping usWin* wide enough to cover the real glyph bbox so accents
        # (German umlauts) are never clipped. USE_TYPO_METRICS makes renderers
        # prefer the typo line metrics. Letterforms are untouched.
        head = font["head"]
        os2 = font["OS/2"]
        hhea = font["hhea"]
        hhea.ascent = 1000
        hhea.descent = -200
        hhea.lineGap = 0
        os2.sTypoAscender = 1000
        os2.sTypoDescender = -200
        os2.sTypoLineGap = 0
        os2.usWinAscent = max(head.yMax, 1000)
        os2.usWinDescent = max(-head.yMin, 200)
        os2.fsSelection |= 0x80  # USE_TYPO_METRICS
        out = out_dir / f"{base.replace(' ', '')}-{label}.ttf"
        font.save(str(out))
        written.append(out)
        print(f"[font_instantiate] {slug}: {out.name} ({out.stat().st_size} bytes)")
    return written


def main(argv: list[str] | None = None) -> int:
    try:
        import fontTools  # noqa: F401
    except ImportError:
        print(
            "FATAL: fonttools is required — pip install fonttools brotli",
            file=sys.stderr,
        )
        return 1

    for slug, (ofl_dir, vf_name, base, weights) in JOBS.items():
        instantiate_family(slug, ofl_dir, vf_name, base, weights)
    print(f"[font_instantiate] {len(JOBS)} family/families instantiated")

    for slug, (ofl_dir, base, files) in STATIC_JOBS.items():
        rename_static_family(slug, ofl_dir, base, files)
    if STATIC_JOBS:
        print(f"[font_instantiate] {len(STATIC_JOBS)} static family/families normalised")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
