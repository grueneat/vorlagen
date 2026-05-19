"""squiggle_alignment_audit — does each yellow squiggle sit on its word?

The Grüne yellow squiggle motif is a free-standing filled Polygon placed at
absolute page coordinates, drawn under (or around) an emphasised word. Scribus
wraps text differently from InDesign, so the emphasised word can shift while
the squiggle does not — leaving the squiggle under empty space.

GROUND-TRUTH check
------------------
An earlier version of this audit computed the "correct" squiggle position as
``preview_word_box + recorded_offset`` — the *exact same formula*
``tools/playbooks/squiggle_realign.py`` uses to PLACE the squiggle. After the
playbook ran, the audit therefore always measured ~0 drift: it verified the
playbook had executed, not that the squiggle was visually on its word.

This audit instead measures the rendered result directly, independent of the
playbook's arithmetic:

  1. Read the squiggle's PolyLine box from ``build.py`` (its placed position).
  2. Pixel-scan the rendered ``preview.pdf`` page around that box for the
     squiggle's actual yellow ink — its real rendered position.
  3. Independently extract the rendered words from ``preview.pdf`` and find
     the word the squiggle ink underlines/overlaps: a word is "carried" by the
     squiggle when the squiggle ink horizontally overlaps the word AND sits
     within the word's vertical band (an underline sits just below the word;
     a circle squiggle overlaps it).
  4. A squiggle whose ink has NO word in its vertical band, or only a word it
     barely overlaps, is an issue — it is floating off any word. This holds
     even when the realign playbook "succeeded" by its own math.

The result is reported per squiggle as ``vgap_mm`` (vertical gap between the
squiggle ink and the nearest word — 0 when they overlap) and ``hoverlap_mm``
(horizontal overlap with that word). Neither uses ``offset_from_word_mm``.

Output: ``build/validation/<slug>/squiggle_alignment_audit.yml`` with the
canonical ``ok: bool, issues: int, detail: str`` preflight contract.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

PT_PER_MM = 72.0 / 25.4

# A squiggle must underline/overlap a word: its ink may sit at most this far
# (vertically) from the nearest horizontally-overlapping word before it counts
# as floating off the word. An underline squiggle renders a few pt below the
# word baseline, so a few mm of slack is normal.
MAX_VGAP_MM = 3.5

# The squiggle ink must horizontally overlap its word by at least this much —
# guards against a squiggle that merely grazes the edge of an adjacent word.
MIN_HOVERLAP_MM = 1.0

# Pixel-scan render resolution. 200dpi gives sub-0.15mm pixels — ample for a
# squiggle ~1-5mm tall.
SCAN_DPI = 200

# A pixel counts as squiggle ink when it is the Grüne `Gelb` swatch
# (CMYK Y=100 → RGB ~ 255,255,0). The thresholds tolerate Scribus anti-alias
# fringing without admitting the green page background or white text.
_YELLOW_R_MIN = 180
_YELLOW_G_MIN = 150
_YELLOW_B_MAX = 120

ROOT = Path(__file__).resolve().parent.parent


def _is_yellow(r: int, g: int, b: int) -> bool:
    return r >= _YELLOW_R_MIN and g >= _YELLOW_G_MIN and b <= _YELLOW_B_MAX


def _polyline_box_mm(
    text: str, anname: str
) -> tuple[float, float, float, float] | None:
    """Read a squiggle PolyLine's x/y/w/h_mm from build.py text."""
    pat = re.compile(
        r"^[ \t]*page\d+\.add\(PolyLine\("
        r"(?:(?!\)\)).)*?"
        r"anname='" + re.escape(anname) + r"'"
        r"(?:(?!\)\)).)*?\)\)",
        re.MULTILINE | re.DOTALL,
    )
    m = pat.search(text)
    if not m:
        return None
    block = m.group(0)
    vals = {}
    for key in ("x_mm", "y_mm", "w_mm", "h_mm"):
        km = re.search(key + r"=(-?\d+(?:\.\d+)?)", block)
        if not km:
            return None
        vals[key] = float(km.group(1))
    return (vals["x_mm"], vals["y_mm"], vals["w_mm"], vals["h_mm"])


def _render_pages(pdf: Path, dpi: int, dest: Path) -> list[Path]:
    """Render every PDF page to PNG via pdftoppm. Returns sorted PNG paths."""
    prefix = dest / "page"
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(prefix)],
        check=True,
        capture_output=True,
    )
    return sorted(dest.glob("page*.png"))


def _scan_squiggle_ink(
    img, box_mm: tuple[float, float, float, float], dpi: int
) -> tuple[float, float, float, float] | None:
    """Find the squiggle's actual yellow ink near its placed build.py box.

    Scans the rendered page within ``box_mm`` expanded by a margin, returns
    the bounding box (mm) of the yellow pixels. ``None`` when no ink is found
    — the squiggle did not render where build.py placed it.
    """
    px = img.load()
    w_px, h_px = img.size
    mm_px = dpi / 25.4
    bx, by, bw, bh = box_mm
    # Margin: enough to catch the squiggle if it rendered a touch outside the
    # nominal PolyLine box, but tight enough not to pick up a neighbour.
    margin_x = 2.0 * mm_px
    margin_y = 3.0 * mm_px
    x0 = max(0, int(bx * mm_px - margin_x))
    x1 = min(w_px, int((bx + bw) * mm_px + margin_x))
    y0 = max(0, int(by * mm_px - margin_y))
    y1 = min(h_px, int((by + bh) * mm_px + margin_y))
    xs: list[int] = []
    ys: list[int] = []
    for yy in range(y0, y1):
        for xx in range(x0, x1):
            r, g, b = px[xx, yy][:3]
            if _is_yellow(r, g, b):
                xs.append(xx)
                ys.append(yy)
    if not xs:
        return None
    return (
        min(xs) / mm_px,
        min(ys) / mm_px,
        max(xs) / mm_px,
        max(ys) / mm_px,
    )


def _carried_word(
    page_words, ink_mm: tuple[float, float, float, float]
) -> tuple[str, float, float] | None:
    """Find the rendered word the squiggle ink underlines / overlaps.

    Returns ``(text, hoverlap_mm, vgap_mm)`` for the best-matching word —
    largest horizontal overlap, smallest vertical gap — or ``None`` when no
    word horizontally overlaps the squiggle ink at all.

    ``vgap_mm`` is 0 when the squiggle ink's vertical span overlaps the word
    box (a circle squiggle, or an underline tucked against the baseline) and
    grows with the gap when the squiggle floats above/below all words.
    """
    sx0, sy0, sx1, sy1 = ink_mm
    best: tuple[float, float, str] | None = None  # (vgap, -hoverlap, text)
    for w in page_words:
        wx0 = w["x0"] / PT_PER_MM
        wx1 = w["x1"] / PT_PER_MM
        wt = w["top"] / PT_PER_MM
        wb = w["bottom"] / PT_PER_MM
        hoverlap = min(sx1, wx1) - max(sx0, wx0)
        if hoverlap <= 0:
            continue
        # Vertical gap: 0 when the squiggle-ink span and the word box overlap.
        vgap = max(0.0, wt - sy1, sy0 - wb)
        key = (vgap, -hoverlap, w["text"])
        if best is None or key < best:
            best = key
    if best is None:
        return None
    vgap, neg_hoverlap, text = best
    return (text, -neg_hoverlap, vgap)


def run_squiggle_alignment_audit(slug: str, repo: Path | None = None) -> dict:
    """Return the ground-truth squiggle-alignment report dict for ``slug``."""
    repo = repo or ROOT
    tdir = repo / "templates" / slug
    anchors_path = tdir / "squiggle_anchors.yml"
    if not anchors_path.exists():
        return {"ok": True, "issues": 0, "detail": "no squiggle_anchors.yml",
                "squiggles": []}
    anchors = (yaml.safe_load(anchors_path.read_text(encoding="utf-8")) or {}).get(
        "anchors"
    ) or []
    if not anchors:
        return {"ok": True, "issues": 0, "detail": "no squiggle anchors",
                "squiggles": []}

    build_path = tdir / "build.py"
    preview_pdf = tdir / "preview.pdf"
    if not build_path.exists() or not preview_pdf.exists():
        return {"ok": True, "issues": 0,
                "detail": "build.py or preview.pdf missing — audit skipped",
                "squiggles": []}
    try:
        import pdfplumber  # type: ignore[import-not-found]
    except ImportError:
        return {"ok": True, "issues": 0,
                "detail": "pdfplumber not available — audit skipped",
                "squiggles": []}
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError:
        return {"ok": True, "issues": 0,
                "detail": "Pillow not available — audit skipped",
                "squiggles": []}

    build_text = build_path.read_text()
    squiggles: list[dict] = []
    n_issues = 0

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        try:
            pngs = _render_pages(preview_pdf, SCAN_DPI, tmp)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            return {"ok": True, "issues": 0,
                    "detail": f"pdftoppm unavailable — audit skipped ({exc})",
                    "squiggles": []}

        with pdfplumber.open(str(preview_pdf)) as pdf:
            n_pages = len(pdf.pages)
            word_cache: dict[int, list] = {}
            img_cache: dict[int, object] = {}
            for a in anchors:
                anname = a["anname"]
                page_idx = a["page"]
                row: dict = {
                    "anname": anname,
                    "page": page_idx,
                    "word": a.get("word", ""),
                }
                if page_idx >= n_pages or page_idx >= len(pngs):
                    row.update(status="skip", reason="page beyond preview",
                               vgap_mm=None, hoverlap_mm=None)
                    squiggles.append(row)
                    continue
                box = _polyline_box_mm(build_text, anname)
                if box is None:
                    row.update(status="skip",
                               reason="squiggle not in build.py",
                               vgap_mm=None, hoverlap_mm=None)
                    squiggles.append(row)
                    continue
                if page_idx not in img_cache:
                    img_cache[page_idx] = Image.open(
                        str(pngs[page_idx])
                    ).convert("RGB")
                ink = _scan_squiggle_ink(
                    img_cache[page_idx], box, SCAN_DPI
                )
                if ink is None:
                    # No yellow ink near the squiggle's placed box: it did not
                    # render where build.py put it — a genuine, visible fault.
                    row.update(status="drift",
                               reason="no squiggle ink rendered at placed box",
                               vgap_mm=None, hoverlap_mm=None)
                    squiggles.append(row)
                    n_issues += 1
                    continue
                if page_idx not in word_cache:
                    word_cache[page_idx] = pdf.pages[page_idx].extract_words()
                carried = _carried_word(word_cache[page_idx], ink)
                if carried is None:
                    row.update(
                        status="drift",
                        reason="squiggle ink overlaps no word",
                        vgap_mm=None, hoverlap_mm=0.0,
                    )
                    squiggles.append(row)
                    n_issues += 1
                    continue
                text, hoverlap, vgap = carried
                row["carried_word"] = text
                row["vgap_mm"] = round(vgap, 3)
                row["hoverlap_mm"] = round(hoverlap, 3)
                row["ink_box_mm"] = [round(v, 3) for v in ink]
                if vgap > MAX_VGAP_MM or hoverlap < MIN_HOVERLAP_MM:
                    row["status"] = "drift"
                    row["reason"] = (
                        f"squiggle ink floats off word "
                        f"(vgap {vgap:.2f}mm, hoverlap {hoverlap:.2f}mm)"
                    )
                    n_issues += 1
                else:
                    row["status"] = "ok"
                squiggles.append(row)

    detail = ""
    if n_issues:
        bad = [s["anname"] for s in squiggles if s.get("status") == "drift"]
        detail = f"{n_issues} squiggle(s) off their word: {bad}"
    return {
        "ok": n_issues == 0,
        "issues": n_issues,
        "detail": detail,
        "max_vgap_mm": MAX_VGAP_MM,
        "min_hoverlap_mm": MIN_HOVERLAP_MM,
        "squiggles": squiggles,
    }


def _yaml_dump(report: dict) -> str:
    return yaml.dump(report, sort_keys=False, allow_unicode=True,
                     default_flow_style=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug")
    ap.add_argument("--out-yaml", type=Path, default=None)
    args = ap.parse_args(argv)
    report = run_squiggle_alignment_audit(args.slug)
    text = _yaml_dump(report)
    if args.out_yaml:
        args.out_yaml.parent.mkdir(parents=True, exist_ok=True)
        args.out_yaml.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if report.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
