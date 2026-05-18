#!/usr/bin/env python3
"""tools/line_match_audit.py — strict per-line layout-match audit.

Where ``text_position_audit`` matches individual words by text and nearest
neighbour (so it cannot tell a line-wrap difference from a positional bug),
this audit is **line-structure aware**. It groups each page's words into
lines, pairs baseline lines with preview lines, and checks three things per
line:

  1. FIRST-WORD X — the x0 of the first word on the line. STRICT: zero
     tolerance beyond a small raster/anti-alias epsilon. A justified or
     left-aligned line must start at exactly the same x in both renders;
     any drift here is a real layout bug (frame offset, indent, wrap).
  2. LINE BASELINE Y — the line's text-top. STRICT, same epsilon. A line
     sitting at a different height is a leading / first-line-offset /
     overflow bug.
  3. INTER-WORD SPACING — the gaps between consecutive words on the line.
     A small tolerance is allowed here ONLY: justified text legitimately
     stretches word-spaces, and the two renderers' justification engines
     differ slightly. The tolerance is kept as tight as possible.

A line "matches" when its first word is the same text, its first-word x and
baseline y are within ``pos_tol_pt``, and every inter-word gap is within
``space_tol_pt`` of the baseline gap. Any failure is a hard finding — this
audit has NO issue cap; a single wrong line fails preflight.

Output schema (line_match_audit.yml):
    template: <slug>
    pos_tol_pt: 1.0
    space_tol_pt: 2.0
    ok: false
    issues: 3
    lines_total: 120
    lines_matched: 117
    findings:
      - page: 3
        baseline_text: "Ute voloria qui cus et ut optate vendam ilmolo"
        preview_text:  "Ute voloria qui cus et ut optate vendam"
        first_word: "Ute"
        kind: first_word_x | baseline_y | wrap | inter_word_space | unmatched
        detail: "first-word x 42.5 vs 48.1 (Δ5.6pt > 1.0)"

Lines are clustered and paired PER FRAME (not per page) — two separate
text frames at the same y on a page must not have their lines merged or
cross-paired. Frame bboxes come from build.py via the shared walker in
``line_spacing_pixel_audit``.

CLI:
    python3 tools/line_match_audit.py \\
      --preview  templates/<slug>/preview.pdf \\
      --baseline templates/<slug>/baseline.pdf \\
      --template <slug> \\
      --build-py templates/<slug>/build.py \\
      --out build/validation/<slug>/line_match_audit.yml

Exit code: 0 always (the pipeline's preflight gate consumes ok=false).
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import yaml

# Re-use the visual-order word extractor + the build.py frame walker from
# the sibling audits so all three tools see identical word boxes / frames.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from text_position_audit import extract_words_with_positions  # noqa: E402
from line_spacing_pixel_audit import parse_textframes_from_build_py  # noqa: E402
import pdfplumber  # noqa: E402

_MM_TO_PT = 2.834645669


def _page_sizes(pdf_path: Path) -> dict[int, tuple[float, float]]:
    """Return {page_idx: (width_pt, height_pt)}."""
    out: dict[int, tuple[float, float]] = {}
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            out[i] = (float(page.width), float(page.height))
    return out


def _drop_offpage(
    words: list[dict[str, Any]],
    sizes: dict[int, tuple[float, float]],
) -> list[dict[str, Any]]:
    """Drop words whose box centre lies outside the page media box.

    InDesign trims off-page design artefacts (headline frames parked
    above the page, registration marks) out of the exported PDF; Scribus
    renders them off-canvas. Such words are not part of the visible
    layout and must not be audited — comparing them produces spurious
    one-sided findings. A small margin admits bleed-edge ink."""
    margin = 6.0
    kept: list[dict[str, Any]] = []
    for w in words:
        wd, ht = sizes.get(w["page"], (0.0, 0.0))
        cx = (w["x0_pt"] + w["x1_pt"]) / 2.0
        cy = (w["y0_pt"] + w["y1_pt"]) / 2.0
        if -margin <= cx <= wd + margin and -margin <= cy <= ht + margin:
            kept.append(w)
    return kept

# Strict position tolerance: first-word x and baseline y must match within
# this many points. 1.0pt ≈ 0.35mm — covers raster rounding and font-metric
# anti-aliasing without admitting a real shift.
_DEFAULT_POS_TOL_PT = 1.0
# Inter-word-spacing tolerance: justified text stretches word-spaces and the
# two justification engines differ slightly. Kept as tight as possible — a
# single space-width of slack at 11pt body text is ~3pt, so 2.0pt admits
# only sub-space-width jitter, not a dropped/added word.
_DEFAULT_SPACE_TOL_PT = 2.0
# Words whose tops are within this many points belong to the same line.
_LINE_CLUSTER_PT = 4.0
# Frame-level vertical-position tolerance: a whole text block (headline,
# citation, body frame) rendered too high or too low shifts its entire
# word cloud uniformly. The per-line baseline_y check can MISS this when
# line pairing degrades — a wrap/first-word difference makes `_check_line`
# return before it reaches the baseline_y branch, and word suppression or
# split-frame bbox de-sync can land lines in an `unmatched`/`wrap` bucket
# so the per-line vertical delta is never measured. This frame-level check
# compares the block's vertical centroid + top + bottom independently of
# line pairing, so a mispositioned frame is caught regardless. The bar is
# the same strict ~1pt as the per-line checks plus a small raster epsilon.
_FRAME_VPOS_TOL_PT = 2.0


def _assign_words_to_frames(
    words: list[dict[str, Any]],
    frames: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Bucket word records by the build.py TextFrame they belong to.

    A word is assigned to the frame whose bbox its centre falls inside
    (with slack). When the centre is inside no frame — which happens when
    a frame's text drifts vertically out of the authored bbox — the word
    is assigned to the NEAREST same-page frame (by centre-to-bbox
    distance) so a drifted line still pairs against its own frame rather
    than landing in an unmatched bucket. Only words with no same-page
    frame at all fall through to ``"__unframed__"``."""
    buckets: dict[str, list[dict[str, Any]]] = {}
    fbox: list[tuple[str, int, float, float, float, float]] = []
    for an, fi in frames.items():
        x, y, w, h = fi.bbox_mm
        fbox.append((
            an, fi.page,
            x * _MM_TO_PT, y * _MM_TO_PT,
            (x + w) * _MM_TO_PT, (y + h) * _MM_TO_PT,
        ))

    def _dist(cx: float, cy: float, box: tuple) -> float:
        _, _, x0, y0, x1, y1 = box
        dx = max(x0 - cx, 0.0, cx - x1)
        dy = max(y0 - cy, 0.0, cy - y1)
        return (dx * dx + dy * dy) ** 0.5

    # Generous slack: a frame's first/last line can drift up to ~12pt out
    # of the authored bbox (first-line-offset, leading drift) and must
    # still land in its own frame. When several frames' (slack-expanded)
    # boxes contain the centre, pick the one whose UNEXPANDED box is
    # nearest — avoids a drifted word being claimed by a neighbour.
    SLACK = 12.0
    for rec in words:
        cx = (rec["x0_pt"] + rec["x1_pt"]) / 2.0
        cy = (rec["y0_pt"] + rec["y1_pt"]) / 2.0
        candidates = [
            b for b in fbox
            if b[1] == rec["page"]
            and b[2] - SLACK <= cx <= b[4] + SLACK
            and b[3] - SLACK <= cy <= b[5] + SLACK
        ]
        if candidates:
            hit = min(candidates, key=lambda b: _dist(cx, cy, b))[0]
        else:
            hit = "__unframed__"
        buckets.setdefault(hit, []).append(rec)
    return buckets


def _rotate_words_to_frame_space(
    words: list[dict[str, Any]],
    rotation_deg: float,
) -> list[dict[str, Any]]:
    """Re-express word boxes in a rotated frame's OWN reading-axis space.

    pdfplumber reports every word's bounding box axis-aligned to the PAGE
    (``x0_pt/y0_pt/x1_pt/y1_pt``). For a frame rotated by ``rotation_deg``
    the visible text runs along a rotated axis, so the page-X of a word is
    NOT its first-word position and the page-Y is NOT its baseline — those
    horizontal-text metrics are meaningless for rotated text.

    This rotates every word box by ``-rotation_deg`` (about the page
    origin) so the text reads left-to-right horizontally again. The pivot
    is irrelevant for the audit: baseline.pdf and preview.pdf get the
    SAME transform, so the *relative* drift the gate measures is exact in
    the frame's reading frame. After the transform the standard strict
    first-word-X / baseline-Y / inter-word-spacing checks apply unchanged
    — the strict tolerance is held, just measured in the right axes.

    The returned records carry the rotated coordinates under the same
    ``x0_pt/y0_pt/x1_pt/y1_pt`` keys (x0<=x1, y0<=y1 re-normalised) so the
    rest of the pipeline is rotation-agnostic. ``text``/``page`` pass
    through untouched.
    """
    if not rotation_deg:
        return words
    # Undo the frame rotation: rotate by -rotation_deg.
    a = math.radians(-rotation_deg)
    cos_a, sin_a = math.cos(a), math.sin(a)

    def _rot(px: float, py: float) -> tuple[float, float]:
        return (px * cos_a - py * sin_a, px * sin_a + py * cos_a)

    out: list[dict[str, Any]] = []
    for w in words:
        # Transform all four corners, then take the axis-aligned hull in
        # the rotated space (a 90° multiple keeps it a tight box; a
        # generic angle gives the enclosing box, which is still a stable
        # per-word measure shared by both renders).
        corners = [
            _rot(w["x0_pt"], w["y0_pt"]),
            _rot(w["x1_pt"], w["y0_pt"]),
            _rot(w["x0_pt"], w["y1_pt"]),
            _rot(w["x1_pt"], w["y1_pt"]),
        ]
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        rec = dict(w)
        rec["x0_pt"] = round(min(xs), 2)
        rec["y0_pt"] = round(min(ys), 2)
        rec["x1_pt"] = round(max(xs), 2)
        rec["y1_pt"] = round(max(ys), 2)
        out.append(rec)
    return out


def _cluster_lines(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group a page's word records into lines, sorted top-to-bottom then
    left-to-right within each line."""
    lines: list[list[dict[str, Any]]] = []
    for w in sorted(words, key=lambda r: (r["y0_pt"], r["x0_pt"])):
        placed = False
        for ln in lines:
            if abs(ln[0]["y0_pt"] - w["y0_pt"]) <= _LINE_CLUSTER_PT:
                ln.append(w)
                placed = True
                break
        if not placed:
            lines.append([w])
    for ln in lines:
        ln.sort(key=lambda r: r["x0_pt"])
    lines.sort(key=lambda ln: ln[0]["y0_pt"])
    return lines


def _line_text(line: list[dict[str, Any]]) -> str:
    return " ".join(w["text"] for w in line)


def _pair_lines(
    base_lines: list[list[dict[str, Any]]],
    prev_lines: list[list[dict[str, Any]]],
) -> list[tuple[list[dict] | None, list[dict] | None]]:
    """Pair baseline lines with preview lines via an LCS alignment on the
    full line text.

    A plain index walk cascades: one wrap difference shifts every later
    line and reports them all as mismatched. An LCS on line text finds
    the longest run of identically-wrapped lines and aligns to it, so a
    single wrap difference is reported as exactly one (or two) finding(s),
    not a frame-wide cascade. Lines present in only one render pair with
    ``None``.
    """
    b_txt = [_line_text(ln) for ln in base_lines]
    p_txt = [_line_text(ln) for ln in prev_lines]
    nb, npv = len(b_txt), len(p_txt)
    # LCS table.
    lcs = [[0] * (npv + 1) for _ in range(nb + 1)]
    for i in range(nb - 1, -1, -1):
        for j in range(npv - 1, -1, -1):
            if b_txt[i] == p_txt[j]:
                lcs[i][j] = lcs[i + 1][j + 1] + 1
            else:
                lcs[i][j] = max(lcs[i + 1][j], lcs[i][j + 1])
    pairs: list[tuple[list[dict] | None, list[dict] | None]] = []
    i = j = 0
    while i < nb and j < npv:
        if b_txt[i] == p_txt[j]:
            pairs.append((base_lines[i], prev_lines[j]))
            i += 1
            j += 1
        elif lcs[i + 1][j] >= lcs[i][j + 1]:
            # baseline line i has no match — but still pair it with the
            # current preview line so first-word/wrap differences surface
            # rather than being silently dropped.
            pairs.append((base_lines[i], prev_lines[j] if j < npv else None))
            i += 1
            if j < npv:
                j += 1
        else:
            pairs.append((base_lines[i] if i < nb else None, prev_lines[j]))
            j += 1
            if i < nb:
                i += 1
    while i < nb:
        pairs.append((base_lines[i], None))
        i += 1
    while j < npv:
        pairs.append((None, prev_lines[j]))
        j += 1
    return pairs


def _check_line(
    base: list[dict[str, Any]] | None,
    prev: list[dict[str, Any]] | None,
    page: int,
    pos_tol: float,
    space_tol: float,
) -> dict[str, Any] | None:
    """Return a finding dict when the line pair fails, else None."""
    if base is None or prev is None:
        present = base if base is not None else prev
        return {
            "page": page,
            "baseline_text": _line_text(base) if base else "",
            "preview_text": _line_text(prev) if prev else "",
            "first_word": present[0]["text"] if present else "",
            "kind": "unmatched",
            "detail": "line present in only one render",
        }

    b_txt, p_txt = _line_text(base), _line_text(prev)
    # First word must be the same text — otherwise the wrap diverged.
    if base[0]["text"] != prev[0]["text"]:
        return {
            "page": page,
            "baseline_text": b_txt,
            "preview_text": p_txt,
            "first_word": base[0]["text"],
            "kind": "wrap",
            "detail": (
                f"line starts with {prev[0]['text']!r}, "
                f"baseline starts with {base[0]['text']!r}"
            ),
        }

    # STRICT: first-word x.
    dx = prev[0]["x0_pt"] - base[0]["x0_pt"]
    if abs(dx) > pos_tol:
        return {
            "page": page,
            "baseline_text": b_txt,
            "preview_text": p_txt,
            "first_word": base[0]["text"],
            "kind": "first_word_x",
            "detail": (
                f"first-word x {prev[0]['x0_pt']} vs {base[0]['x0_pt']} "
                f"(Δ{round(dx, 2)}pt > {pos_tol})"
            ),
        }

    # STRICT: line baseline y.
    dy = prev[0]["y0_pt"] - base[0]["y0_pt"]
    if abs(dy) > pos_tol:
        return {
            "page": page,
            "baseline_text": b_txt,
            "preview_text": p_txt,
            "first_word": base[0]["text"],
            "kind": "baseline_y",
            "detail": (
                f"line top y {prev[0]['y0_pt']} vs {base[0]['y0_pt']} "
                f"(Δ{round(dy, 2)}pt > {pos_tol})"
            ),
        }

    # Inter-word spacing: only meaningful when the lines carry the same
    # words. If the word sequence differs the wrap check above already
    # fired; here the words match so compare consecutive gaps.
    if [w["text"] for w in base] == [w["text"] for w in prev]:
        for j in range(len(base) - 1):
            b_gap = base[j + 1]["x0_pt"] - base[j]["x1_pt"]
            p_gap = prev[j + 1]["x0_pt"] - prev[j]["x1_pt"]
            if abs(p_gap - b_gap) > space_tol:
                return {
                    "page": page,
                    "baseline_text": b_txt,
                    "preview_text": p_txt,
                    "first_word": base[0]["text"],
                    "kind": "inter_word_space",
                    "detail": (
                        f"gap after {base[j]['text']!r} "
                        f"{round(p_gap, 2)} vs {round(b_gap, 2)} "
                        f"(Δ{round(p_gap - b_gap, 2)}pt > {space_tol})"
                    ),
                }
    return None


def _block_vextent(words: list[dict[str, Any]]) -> tuple[float, float, float] | None:
    """Return ``(top, centroid, bottom)`` of a word cloud's vertical extent.

    ``top`` is the smallest word-top, ``bottom`` the largest word-bottom,
    ``centroid`` the mean of every word's vertical mid-point. Returns
    ``None`` for an empty cloud.
    """
    if not words:
        return None
    top = min(w["y0_pt"] for w in words)
    bottom = max(w["y1_pt"] for w in words)
    centroid = sum((w["y0_pt"] + w["y1_pt"]) / 2.0 for w in words) / len(words)
    return top, centroid, bottom


def _check_frame_vposition(
    base_words: list[dict[str, Any]],
    prev_words: list[dict[str, Any]],
    frame: str,
    page: int,
    tol: float,
) -> dict[str, Any] | None:
    """Catch a whole text block rendered at the wrong vertical position.

    Independent of line pairing: the per-line ``baseline_y`` check only
    runs after the ``wrap`` / ``first_word_x`` branches pass and only on
    lines the LCS paired — a mispositioned headline whose words also
    wrapped or were suppressed slips past it. This compares the block's
    vertical centroid (and, as corroboration, its top and bottom) between
    the two renders. When the centroid AND at least one edge drift the
    same way beyond ``tol``, the whole frame moved — a real vertical
    mispositioning bug. Returns a finding dict, else ``None``.

    A bare difference in word count does NOT trip this on its own: the
    centroid of a partial word cloud is stable enough that a genuine
    block shift still registers, while a few suppressed words do not.
    """
    bv = _block_vextent(base_words)
    pv = _block_vextent(prev_words)
    if bv is None or pv is None:
        return None  # one-sided: the per-line `unmatched` finding covers it
    b_top, b_cen, b_bot = bv
    p_top, p_cen, p_bot = pv
    d_top = p_top - b_top
    d_cen = p_cen - b_cen
    d_bot = p_bot - b_bot
    # The block moved when the centroid drifts AND an edge confirms the
    # same-signed shift — guards against a lone outlier word skewing the
    # centroid without the block actually moving.
    edge = d_top if abs(d_top) >= abs(d_bot) else d_bot
    if abs(d_cen) > tol and abs(edge) > tol and (d_cen > 0) == (edge > 0):
        return {
            "page": page,
            "baseline_text": _line_text(sorted(base_words, key=lambda w: (w["y0_pt"], w["x0_pt"])))[:80],
            "preview_text": _line_text(sorted(prev_words, key=lambda w: (w["y0_pt"], w["x0_pt"])))[:80],
            "first_word": "",
            "kind": "frame_vertical_position",
            "detail": (
                f"text block shifted vertically: centroid Δ{round(d_cen, 2)}pt, "
                f"top Δ{round(d_top, 2)}pt, bottom Δ{round(d_bot, 2)}pt "
                f"(tol {tol}pt)"
            ),
            "frame": frame,
        }
    return None


def run_audit(
    preview: Path,
    baseline: Path,
    template: str,
    build_py: Path | None = None,
    pos_tol: float = _DEFAULT_POS_TOL_PT,
    space_tol: float = _DEFAULT_SPACE_TOL_PT,
) -> dict[str, Any]:
    base_words = extract_words_with_positions(baseline)
    prev_words = extract_words_with_positions(preview)
    # Drop off-page artefacts (parked headline frames, registration marks)
    # — InDesign trims them, Scribus renders them off-canvas; auditing
    # them yields one-sided noise.
    base_words = _drop_offpage(base_words, _page_sizes(baseline))
    prev_words = _drop_offpage(prev_words, _page_sizes(preview))

    frames: dict[str, Any] = {}
    if build_py is not None and build_py.exists():
        frames = parse_textframes_from_build_py(build_py)

    findings: list[dict[str, Any]] = []
    lines_total = 0
    lines_matched = 0

    if frames:
        # Frame-aware: cluster + pair lines WITHIN each frame so two frames
        # at the same y on a page never cross-pair. The unframed bucket is
        # audited page-by-page as a fallback.
        base_buckets = _assign_words_to_frames(base_words, frames)
        prev_buckets = _assign_words_to_frames(prev_words, frames)
        keys = sorted(set(base_buckets) | set(prev_buckets))
        for key in keys:
            bw = base_buckets.get(key, [])
            pw = prev_buckets.get(key, [])
            if key == "__unframed__":
                # split by page so unframed words don't merge across pages
                pages = sorted({w["page"] for w in bw} | {w["page"] for w in pw})
                groups = [
                    ([w for w in bw if w["page"] == pg],
                     [w for w in pw if w["page"] == pg], pg)
                    for pg in pages
                ]
            else:
                pg = frames[key].page if key in frames else 0
                # Rotated frame: re-express both renders' word boxes in the
                # frame's own reading-axis space so the strict first-word-X
                # / baseline-Y checks measure the right axes. No carve-out,
                # no relaxed tolerance — the same strict bar, measured
                # correctly.
                rot = frames[key].rotation_deg if key in frames else 0.0
                if rot:
                    bw = _rotate_words_to_frame_space(bw, rot)
                    pw = _rotate_words_to_frame_space(pw, rot)
                groups = [(bw, pw, pg)]
            for gb, gp, pg in groups:
                base_lines = _cluster_lines(gb)
                prev_lines = _cluster_lines(gp)
                lines_total += max(len(base_lines), len(prev_lines))
                line_finding_count = 0
                for b, p in _pair_lines(base_lines, prev_lines):
                    finding = _check_line(b, p, pg, pos_tol, space_tol)
                    if finding is None:
                        lines_matched += 1
                    else:
                        finding["frame"] = key
                        findings.append(finding)
                        line_finding_count += 1
                # Frame-level vertical-position guard. Runs on every framed
                # bucket; for the unframed page bucket only when the
                # per-line checks found NOTHING — there the lack of a
                # build.py frame means a block shift would otherwise be
                # invisible, but if line checks already flagged the page we
                # avoid a duplicate page-wide finding.
                run_vpos = key != "__unframed__" or line_finding_count == 0
                if run_vpos:
                    vpos = _check_frame_vposition(
                        gb, gp, key, pg, _FRAME_VPOS_TOL_PT,
                    )
                    if vpos is not None:
                        findings.append(vpos)
    else:
        # No build.py — fall back to per-page clustering.
        pages = sorted({w["page"] for w in base_words}
                       | {w["page"] for w in prev_words})
        for pg in pages:
            base_lines = _cluster_lines([w for w in base_words if w["page"] == pg])
            prev_lines = _cluster_lines([w for w in prev_words if w["page"] == pg])
            lines_total += max(len(base_lines), len(prev_lines))
            for b, p in _pair_lines(base_lines, prev_lines):
                finding = _check_line(b, p, pg, pos_tol, space_tol)
                if finding is None:
                    lines_matched += 1
                else:
                    findings.append(finding)

    return {
        "template": template,
        "pos_tol_pt": pos_tol,
        "space_tol_pt": space_tol,
        "lines_total": lines_total,
        "lines_matched": lines_matched,
        "issues": len(findings),
        "ok": len(findings) == 0,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preview", required=True, type=Path)
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--template", required=True)
    ap.add_argument("--build-py", type=Path,
                    help="build.py for frame-aware line pairing")
    ap.add_argument("--pos-tol", type=float, default=_DEFAULT_POS_TOL_PT)
    ap.add_argument("--space-tol", type=float, default=_DEFAULT_SPACE_TOL_PT)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    report = run_audit(
        args.preview, args.baseline, args.template,
        build_py=args.build_py,
        pos_tol=args.pos_tol, space_tol=args.space_tol,
    )
    text = yaml.safe_dump(report, sort_keys=False, allow_unicode=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)

    status = "OK" if report["ok"] else "FAIL"
    sys.stderr.write(
        f"line_match_audit: {status} — {report['lines_matched']}/"
        f"{report['lines_total']} lines match, {report['issues']} finding(s)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
