"""squiggle_alignment_audit — does each yellow squiggle sit on its word?

The Grüne yellow squiggle motif is a free-standing Polygon placed at absolute
page coordinates. Scribus wraps text differently from InDesign, so the
emphasised word can shift while the squiggle does not — leaving the squiggle
under the wrong word.

This audit reads ``templates/<slug>/squiggle_anchors.yml`` (the converter's
squiggle-to-word binding) and, for each squiggle:

  1. locates the anchor word in the rendered ``preview.pdf``;
  2. computes where the squiggle SHOULD be (preview word box + the recorded
     baseline offset);
  3. compares that against where the squiggle ACTUALLY is in build.py.

A squiggle whose drift exceeds ``DRIFT_TOL_MM`` is an issue. The matching
remediation is ``tools/playbooks/squiggle_realign.py``, dispatched by
``bin/tune-fix``.

Output: ``build/validation/<slug>/squiggle_alignment_audit.yml`` with the
canonical ``ok: bool, issues: int, detail: str`` preflight contract.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

PT_PER_MM = 72.0 / 25.4

# A squiggle within this distance of its word is "on" the word — covers
# cross-renderer sub-mm jitter without flagging it.
DRIFT_TOL_MM = 1.5

ROOT = Path(__file__).resolve().parent.parent


def _polyline_xy_mm(text: str, anname: str) -> tuple[float, float] | None:
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
    xm = re.search(r"x_mm=(-?\d+(?:\.\d+)?)", block)
    ym = re.search(r"y_mm=(-?\d+(?:\.\d+)?)", block)
    if not xm or not ym:
        return None
    return float(xm.group(1)), float(ym.group(1))


def _frame_box_mm(text: str, anname: str) -> tuple[float, float, float, float] | None:
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


def _words_in_box(page_words, box_pt):
    x0, top, x1, bottom = box_pt
    out = []
    for w in page_words:
        cx = (w["x0"] + w["x1"]) / 2.0
        cy = (w["top"] + w["bottom"]) / 2.0
        if x0 - 2.0 <= cx <= x1 + 2.0 and top - 2.0 <= cy <= bottom + 2.0:
            out.append(w)
    return out


def _find_word(page_words, frame_box_pt, word, word_index):
    fw = _words_in_box(page_words, frame_box_pt)
    if not fw:
        return None
    if 0 <= word_index < len(fw) and fw[word_index]["text"] == word:
        return fw[word_index]
    same = [(i, w) for i, w in enumerate(fw) if w["text"] == word]
    if not same:
        return None
    return min(same, key=lambda iw: abs(iw[0] - word_index))[1]


def run_squiggle_alignment_audit(slug: str, repo: Path | None = None) -> dict:
    """Return the audit report dict for ``slug``."""
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

    build_text = build_path.read_text()
    squiggles = []
    n_issues = 0
    with pdfplumber.open(str(preview_pdf)) as pdf:
        n_pages = len(pdf.pages)
        word_cache: dict[int, list] = {}
        for a in anchors:
            anname = a["anname"]
            page_idx = a["page"]
            row = {"anname": anname, "page": page_idx, "word": a["word"]}
            if page_idx >= n_pages:
                row.update(status="skip", reason="page beyond preview", drift_mm=None)
                squiggles.append(row)
                continue
            cur = _polyline_xy_mm(build_text, anname)
            frame_box = _frame_box_mm(build_text, a["target_frame"])
            if cur is None or frame_box is None:
                row.update(status="skip", reason="squiggle/frame not in build.py",
                           drift_mm=None)
                squiggles.append(row)
                continue
            fb_pt = (
                frame_box[0] * PT_PER_MM,
                frame_box[1] * PT_PER_MM,
                (frame_box[0] + frame_box[2]) * PT_PER_MM,
                (frame_box[1] + frame_box[3]) * PT_PER_MM,
            )
            if page_idx not in word_cache:
                word_cache[page_idx] = pdf.pages[page_idx].extract_words()
            pw = _find_word(word_cache[page_idx], fb_pt, a["word"], a["word_index"])
            if pw is None:
                row.update(status="skip", reason="word not located in preview",
                           drift_mm=None)
                squiggles.append(row)
                continue
            off = a["offset_from_word_mm"]
            target_x = pw["x0"] / PT_PER_MM + off["dx_mm"]
            target_y = pw["top"] / PT_PER_MM + off["dy_mm"]
            dx = target_x - cur[0]
            dy = target_y - cur[1]
            drift = (dx * dx + dy * dy) ** 0.5
            row["drift_mm"] = round(drift, 3)
            if drift > DRIFT_TOL_MM:
                row["status"] = "drift"
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
        "tolerance_mm": DRIFT_TOL_MM,
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
