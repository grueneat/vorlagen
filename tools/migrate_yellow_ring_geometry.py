"""One-shot migration: re-anchor mis-placed yellow-ring PolyLine elements.

The IDML→DSL converter (tools/idml_to_dsl.py) previously emitted a free-form
yellow-ring PolyLine with the *rotation baked into the sla_path* AND a
``rotation_deg`` frame rotation — a double rotation that swept the ring off
its word. The converter is now fixed (see _compute_path_pagebbox_pt and the
complex-Polygon branch of _emit_pageitem): a PolyLine frame is the upright
page-space bbox of its already-transformed path, with no frame rotation.

This script SURGICALLY patches the eight committed A6 flyer build.py files.
For each yellow PolyLine (``fill='Gelb'``) it recomputes the geometry with the
corrected converter and replaces ONLY the affected geometry kwargs
(x_mm / y_mm / w_mm / h_mm / rotation_deg / sla_path) — and ONLY for elements
that still carry the bug signature:

  * the committed element has ``rotation_deg`` (the double-rotation), OR
  * the committed ``sla_path`` differs from the corrected converter output.

Non-rotated squiggles whose only difference is an x/y shift are left
byte-identical — those shifts are deliberate ``squiggle_realign.py`` tuning,
not converter error. Everything else in build.py is untouched.

Run from the repo root:  python tools/migrate_yellow_ring_geometry.py
Add --dry-run to preview without writing.
"""

from __future__ import annotations

import argparse
import glob
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# slug -> originals/<folder> holding the source .idml
FLYERS: dict[str, str] = {
    "flyer-a6-hochformat-gruenes-cover": "26-03-Flyer A6 Hochformat gruenes Cover Ordner",
    "flyer-a6-hochformat-portraet": "26-03-Flyer A6 Hochformat Portrait Ordner",
    "flyer-a6-hochformat-quadrat-im-bild": "26-03-Flyer A6 Hochformat Quadrat in Bild Ordner",
    "flyer-a6-hochformat-zweigeteilt": "26-03-Flyer A6 Hochformat zweigeteilt Ordner",
    "flyer-a6-querformat-gruenes-cover": "26-03-Flyer A6 Querformat gruenes Cover Ordner",
    "flyer-a6-querformat-portraet": "26-03-Flyer A6 Querformat Portrait Ordner",
    "flyer-a6-querformat-quadrat-im-bild": "26-03-Flyer A6 Querformat Quadrat in Bild Ordner",
    "flyer-a6-querformat-zweigeteilt": "26-03-Flyer A6 Querformat zweigeteilt Ordner",
}

# kwargs the migration is allowed to overwrite — geometry only.
GEOM_KEYS = ("x_mm", "y_mm", "w_mm", "h_mm", "rotation_deg", "sla_path")


def _idml_path(folder: str) -> Path:
    matches = sorted(glob.glob(str(ROOT / "originals" / folder / "*.idml")))
    if not matches:
        raise FileNotFoundError(f"no .idml under originals/{folder}")
    return Path(matches[0])


def _polyline_blocks(text: str) -> list[tuple[int, int, str]]:
    """Return (start, end, block) for every ``pageN.add(PolyLine(...))`` call."""
    out: list[tuple[int, int, str]] = []
    pat = re.compile(
        r"page\d+\.add\(PolyLine\((?:(?!\)\)).)*?\)\)",
        re.DOTALL,
    )
    for m in pat.finditer(text):
        out.append((m.start(), m.end(), m.group(0)))
    return out


def _anname(block: str) -> str | None:
    m = re.search(r"anname='([^']*)'", block)
    return m.group(1) if m else None


def _is_yellow(block: str) -> bool:
    return "fill='Gelb'" in block


def _kwarg_str(block: str, key: str) -> str | None:
    """Return the verbatim ``key=...`` slice from a PolyLine block, or None."""
    if key == "sla_path":
        m = re.search(r"sla_path='[^']*'", block)
    else:
        m = re.search(rf"{key}=-?[\d.]+", block)
    return m.group(0) if m else None


def _run_converter(slug: str, idml: Path, out: Path) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "idml_to_dsl.py"),
        str(idml),
        str(out),
        "--template-id",
        slug,
    ]
    asset_map = ROOT / "shared" / "assets" / slug / "links_export.yml"
    if asset_map.exists():
        cmd += ["--asset-map", str(asset_map)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"converter failed for {slug}:\n{res.stdout}\n{res.stderr}"
        )


def _patch_block(old_block: str, new_block: str) -> str:
    """Replace the geometry kwargs of ``old_block`` with those of ``new_block``.

    Handles three kinds of geometry kwarg:
      * present in both  -> overwrite verbatim slice
      * present in new only (e.g. nothing here today)
      * present in old only -> ``rotation_deg`` must be DELETED (the corrected
        converter no longer emits a frame rotation for a PolyLine).
    """
    patched = old_block
    for key in GEOM_KEYS:
        old_kw = _kwarg_str(patched, key)
        new_kw = _kwarg_str(new_block, key)
        if old_kw is not None and new_kw is not None:
            patched = patched.replace(old_kw, new_kw, 1)
        elif old_kw is not None and new_kw is None:
            # corrected converter dropped this kwarg (rotation_deg) — remove the
            # whole indented line.
            patched = re.sub(
                rf"\n[ \t]*{re.escape(old_kw)},",
                "",
                patched,
                count=1,
            )
        # old_kw is None, new_kw set: would need to INSERT a line. Not needed
        # for this migration (every fixed ring already has x/y/w/h kwargs);
        # left unhandled deliberately so an unexpected case fails loud below.
        elif old_kw is None and new_kw is not None and key != "rotation_deg":
            raise RuntimeError(
                f"unexpected: corrected converter added kwarg {key!r} "
                f"absent from committed block"
            )
    return patched


def migrate(dry_run: bool = False) -> int:
    total_patched = 0
    for slug, folder in FLYERS.items():
        build_py = ROOT / "templates" / slug / "build.py"
        text = build_py.read_text(encoding="utf-8")

        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)
        try:
            _run_converter(slug, _idml_path(folder), tmp_path)
            new_text = tmp_path.read_text(encoding="utf-8")
        finally:
            tmp_path.unlink(missing_ok=True)

        # index corrected PolyLine blocks by anname
        new_blocks: dict[str, str] = {}
        for _s, _e, blk in _polyline_blocks(new_text):
            an = _anname(blk)
            if an and _is_yellow(blk):
                new_blocks[an] = blk

        # walk committed blocks back-to-front so byte offsets stay valid
        committed = _polyline_blocks(text)
        patched_names: list[str] = []
        for start, end, old_block in reversed(committed):
            if not _is_yellow(old_block):
                continue
            an = _anname(old_block)
            if an is None or an not in new_blocks:
                continue
            new_block = new_blocks[an]

            old_rot = _kwarg_str(old_block, "rotation_deg")
            old_path = _kwarg_str(old_block, "sla_path")
            new_path = _kwarg_str(new_block, "sla_path")
            # Bug signature: a frame rotation_deg OR a changed path. A
            # pure x/y shift with identical path is squiggle_realign tuning
            # and is intentionally left alone.
            bug_signature = (old_rot is not None) or (old_path != new_path)
            if not bug_signature:
                continue

            patched_block = _patch_block(old_block, new_block)
            if patched_block == old_block:
                continue
            text = text[:start] + patched_block + text[end:]
            patched_names.append(an)

        if patched_names:
            print(f"{slug}: patched {sorted(patched_names)}")
            total_patched += len(patched_names)
            if not dry_run:
                build_py.write_text(text, encoding="utf-8")
        else:
            print(f"{slug}: no yellow ring needed migration")

    print(f"\n{'DRY RUN — ' if dry_run else ''}total elements patched: {total_patched}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="preview only")
    args = ap.parse_args(argv)
    return migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
