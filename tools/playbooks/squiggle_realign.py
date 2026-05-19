"""Defined remediation playbook for yellow-squiggle re-anchoring.

The Grüne templates carry a yellow squiggle emphasis motif — a free-standing
filled Polygon placed at absolute page coordinates, drawn behind a word. Scribus
wraps text differently from InDesign, so the emphasised WORD shifts while the
squiggle does not — the squiggle ends up under the wrong word.

This playbook reads ``templates/<slug>/squiggle_anchors.yml`` (written by the
converter, ``tools/idml_to_dsl.py:_emit_squiggle_anchors``). Each anchor binds a
squiggle Polygon to the word it underlines, recorded as:

  * ``target_frame`` + ``word`` + ``word_index`` — the word, disambiguated by
    its reading-order ordinal within the target text frame (a bare word string
    repeats; the ordinal does not).
  * ``baseline_word_box_pt`` — where that word sits in baseline.pdf.
  * ``baseline_squiggle_box_mm`` — where the squiggle sits in the InDesign
    baseline.
  * ``offset_from_word_mm`` — the squiggle's origin offset from the word box;
    held constant when the squiggle is moved.

``apply()`` locates the same word in the freshly rendered ``preview.pdf``,
measures how far it drifted from its baseline position, and shifts the squiggle
PolyLine's ``x_mm`` / ``y_mm`` in build.py by that delta so the squiggle tracks
its word. The fix is deterministic — same audit input, same shift.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

PT_PER_MM = 72.0 / 25.4

# Below this drift the squiggle already tracks its word — no edit needed.
MIN_SHIFT_MM = 0.15
# Refuse a shift larger than this — almost certainly a mis-association, not a
# real wrap drift. Surfaces for human review instead of moving the squiggle
# clear off its word.
MAX_SHIFT_MM = 40.0


def _load_anchors(slug: str, repo: Path) -> list[dict]:
    p = repo / "templates" / slug / "squiggle_anchors.yml"
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("anchors") or []


def _polyline_block(text: str, anname: str) -> re.Match | None:
    """Match the ``pageN.add(PolyLine(...))`` block for ``anname``."""
    pat = re.compile(
        r"(^[ \t]*page\d+\.add\(PolyLine\("
        r"(?:(?!\)\)).)*?"
        r"anname='" + re.escape(anname) + r"'"
        r"(?:(?!\)\)).)*?"
        r"\)\)\n)",
        re.MULTILINE | re.DOTALL,
    )
    return pat.search(text)


def _frame_box_mm(text: str, anname: str) -> tuple[float, float, float, float] | None:
    """Read a TextFrame's x/y/w/h_mm from build.py text."""
    pat = re.compile(
        r"^[ \t]*page\d+\.add\(TextFrame\("
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


def _words_in_box(page_words: list[dict], box_pt: tuple[float, float, float, float]) -> list[dict]:
    """Words whose center lies inside ``box_pt`` (x0, top, x1, bottom)."""
    x0, top, x1, bottom = box_pt
    out = []
    for w in page_words:
        cx = (w["x0"] + w["x1"]) / 2.0
        cy = (w["top"] + w["bottom"]) / 2.0
        if x0 - 2.0 <= cx <= x1 + 2.0 and top - 2.0 <= cy <= bottom + 2.0:
            out.append(w)
    return out


def _find_preview_word(
    page_words: list[dict],
    frame_box_pt: tuple[float, float, float, float],
    word: str,
    word_index: int,
    squiggle_box_pt: tuple[float, float, float, float] | None = None,
) -> dict | None:
    """Locate the anchor word in preview.pdf.

    A reading-order ordinal is NOT a reliable key when the target frame
    holds more than one column: pdfplumber interleaves the columns line by
    line, so a tighter wrap in one column shifts every later ordinal. The
    reliable key is geometry — the squiggle is placed next to the word it
    decorates, so the correct preview word is the same-text word nearest
    the squiggle's own box.

    Resolution order:
      1. If ``squiggle_box_pt`` is given, pick the same-text word whose box
         origin is closest to the squiggle box origin.
      2. Otherwise fall back to the reading-order ordinal, then to the
         same-text word with the closest ordinal.
    """
    frame_words = _words_in_box(page_words, frame_box_pt)
    if not frame_words:
        return None
    same = [(i, w) for i, w in enumerate(frame_words) if w["text"] == word]
    if same and squiggle_box_pt is not None:
        sx0, st = squiggle_box_pt[0], squiggle_box_pt[1]
        _, w = min(
            same,
            key=lambda iw: (iw[1]["x0"] - sx0) ** 2 + (iw[1]["top"] - st) ** 2,
        )
        return w
    if 0 <= word_index < len(frame_words):
        cand = frame_words[word_index]
        if cand["text"] == word:
            return cand
    if not same:
        return None
    i, w = min(same, key=lambda iw: abs(iw[0] - word_index))
    return w


def _shift_squiggle(
    build_path: Path,
    anname: str,
    dx_mm: float,
    dy_mm: float,
    reason: str,
) -> tuple[bool, str]:
    """Shift a squiggle PolyLine's x_mm / y_mm in build.py."""
    text = build_path.read_text()
    m = _polyline_block(text, anname)
    if not m:
        return False, f"squiggle {anname} PolyLine not found in build.py"
    block = m.group(1)
    xm = re.search(r"x_mm=(-?\d+(?:\.\d+)?)", block)
    ym = re.search(r"y_mm=(-?\d+(?:\.\d+)?)", block)
    if not xm or not ym:
        return False, f"squiggle {anname} has no x_mm/y_mm"
    cur_x, cur_y = float(xm.group(1)), float(ym.group(1))
    new_x = round(cur_x + dx_mm, 4)
    new_y = round(cur_y + dy_mm, 4)
    new_block = block.replace(f"x_mm={xm.group(1)}", f"x_mm={new_x}", 1)
    new_block = new_block.replace(f"y_mm={ym.group(1)}", f"y_mm={new_y}", 1)
    if new_block == block:
        return False, f"squiggle {anname} already at target"
    marker = (
        f"    # playbook squiggle_realign.py: "
        f"x_mm {cur_x}->{new_x}, y_mm {cur_y}->{new_y} ({reason})\n"
    )
    build_path.write_text(text.replace(block, marker + new_block, 1))
    return True, (
        f"squiggle {anname}: x_mm {cur_x}->{new_x}, y_mm {cur_y}->{new_y} ({reason})"
    )


def apply(slug: str, repo: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    """Re-anchor every squiggle to its word. Returns (n_changes, log)."""
    log: list[str] = []
    anchors = _load_anchors(slug, repo)
    if not anchors:
        return 0, ["no squiggle_anchors.yml — nothing to re-anchor"]

    build_path = repo / "templates" / slug / "build.py"
    preview_pdf = repo / "templates" / slug / "preview.pdf"
    if not build_path.exists():
        return 0, [f"build.py not found at {build_path}"]
    if not preview_pdf.exists():
        return 0, [f"preview.pdf not found at {preview_pdf} — render first"]

    try:
        import pdfplumber  # type: ignore[import-not-found]
    except ImportError:
        return 0, ["pdfplumber not available — cannot measure preview words"]

    build_text = build_path.read_text()
    n_changes = 0
    with pdfplumber.open(str(preview_pdf)) as pdf:
        n_pages = len(pdf.pages)
        page_words_cache: dict[int, list[dict]] = {}
        for a in anchors:
            anname = a["anname"]
            page_idx = a["page"]
            if page_idx >= n_pages:
                log.append(f"  {anname}: page {page_idx} beyond preview — skipped")
                continue
            frame_box = _frame_box_mm(build_text, a["target_frame"])
            if frame_box is None:
                log.append(
                    f"  {anname}: target frame {a['target_frame']} "
                    f"not found in build.py — skipped"
                )
                continue
            fb_pt = (
                frame_box[0] * PT_PER_MM,
                frame_box[1] * PT_PER_MM,
                (frame_box[0] + frame_box[2]) * PT_PER_MM,
                (frame_box[1] + frame_box[3]) * PT_PER_MM,
            )
            if page_idx not in page_words_cache:
                page_words_cache[page_idx] = pdf.pages[page_idx].extract_words()
            # Where the squiggle currently is in build.py — read first so it
            # can disambiguate a repeated anchor word by geometric proximity.
            m = _polyline_block(build_text, anname)
            if not m:
                log.append(f"  {anname}: PolyLine not found in build.py — skipped")
                continue
            block = m.group(1)
            cur_x = float(re.search(r"x_mm=(-?\d+(?:\.\d+)?)", block).group(1))
            cur_y = float(re.search(r"y_mm=(-?\d+(?:\.\d+)?)", block).group(1))
            sq_box_pt = (cur_x * PT_PER_MM, cur_y * PT_PER_MM)
            pw = _find_preview_word(
                page_words_cache[page_idx], fb_pt, a["word"], a["word_index"],
                squiggle_box_pt=sq_box_pt,
            )
            if pw is None:
                log.append(
                    f"  {anname}: word {a['word']!r} not located in "
                    f"preview frame {a['target_frame']} — skipped"
                )
                continue
            # Where the squiggle SHOULD be: preview word box + recorded offset.
            off = a["offset_from_word_mm"]
            target_x = pw["x0"] / PT_PER_MM + off["dx_mm"]
            target_y = pw["top"] / PT_PER_MM + off["dy_mm"]
            dx = target_x - cur_x
            dy = target_y - cur_y
            if abs(dx) < MIN_SHIFT_MM and abs(dy) < MIN_SHIFT_MM:
                log.append(
                    f"  {anname}: on word {a['word']!r} "
                    f"(drift {dx:+.2f},{dy:+.2f}mm < {MIN_SHIFT_MM}mm) — ok"
                )
                continue
            if abs(dx) > MAX_SHIFT_MM or abs(dy) > MAX_SHIFT_MM:
                log.append(
                    f"  {anname}: shift ({dx:+.2f},{dy:+.2f}mm) exceeds "
                    f"MAX_SHIFT_MM ({MAX_SHIFT_MM}mm) — likely mis-association. "
                    f"ESCALATE."
                )
                continue
            if dry_run:
                log.append(
                    f"  {anname}: would shift ({dx:+.4f},{dy:+.4f}mm) "
                    f"to track word {a['word']!r}"
                )
                n_changes += 1
                continue
            wrote, msg = _shift_squiggle(
                build_path, anname, dx, dy,
                f"track word {a['word']!r}",
            )
            log.append(f"  {msg}")
            if wrote:
                n_changes += 1
                build_text = build_path.read_text()
    if dry_run and n_changes:
        log.append(f"dry-run: {n_changes} squiggle(s) would be re-anchored")
    return n_changes, log
