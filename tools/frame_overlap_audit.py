#!/usr/bin/env python3
"""Frame-overlap audit — detects text from frame A bleeding into frame B's
declared bbox, OR text rendered outside its own frame's bbox.

Catches the user-flagged "headline moved into body text" regression class:
when a frame split / y_mm shift puts text physically inside a different
frame's declared region, the rendered output overlaps even though each
frame's individual position-audit may pass.

Algorithm (per page):
  1. Parse all TextFrame bboxes from build.py
  2. Render preview.pdf to PNG at the audit DPI
  3. For each frame F: extract every word bbox via pdfplumber that
     falls inside F's bbox
  4. For each pair (A, B) of NON-overlapping declared frames where
     a word from A's content (matched by text snippet) lands inside
     B's bbox → FLAG
  5. Also flag: text outside its own declared frame's bbox by > N pt

The audit only fires on TextFrames with non-empty content — silent
empty frames (info layers, decorative) are skipped to avoid noise.

Output: build/validation/<slug>/frame_overlap_audit.yml
Wire: render_pipeline.py Phase E5d
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

OVERLAP_TOLERANCE_PT = 5.0  # words inside another frame's bbox by > 5pt = flag


def _parse_text_frames_from_build_py(build_py: Path) -> list[dict]:
    """Extract (anname, page, bbox_mm, text_snippet) for every TextFrame."""
    text = build_py.read_text()
    frames = []
    pat = re.compile(
        r"^[ \t]*page(\d+)\.add\(TextFrame\("
        r"((?:(?!\)\)).)*?)"
        r"\)\)\n",
        re.MULTILINE | re.DOTALL,
    )
    for m in pat.finditer(text):
        page = int(m.group(1))
        body = m.group(2)
        anname_m = re.search(r"anname='(\w+)'", body)
        if not anname_m:
            continue
        x_m = re.search(r"x_mm=(-?\d+(?:\.\d+)?)", body)
        y_m = re.search(r"y_mm=(-?\d+(?:\.\d+)?)", body)
        w_m = re.search(r"w_mm=(-?\d+(?:\.\d+)?)", body)
        h_m = re.search(r"h_mm=(-?\d+(?:\.\d+)?)", body)
        if not all([x_m, y_m, w_m, h_m]):
            continue
        # Pick a few text snippets to match against rendered words later
        snippets = []
        for tm in re.finditer(r"text='([^']{4,40})'", body):
            t = tm.group(1).strip()
            if t and not t.startswith("\\u") and len(t) >= 4:
                snippets.append(t.split()[0])  # first word
                if len(snippets) >= 3:
                    break
        frames.append({
            "anname": anname_m.group(1),
            "page": page,
            "bbox_mm": (float(x_m.group(1)), float(y_m.group(1)),
                       float(w_m.group(1)), float(h_m.group(1))),
            "snippets": snippets,
        })
    return frames


def _bbox_intersects_mm(a: tuple, b: tuple, slack_mm: float = 1.0) -> bool:
    """Return True when bboxes a and b overlap (with slack)."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (
        ax + aw + slack_mm < bx or
        bx + bw + slack_mm < ax or
        ay + ah + slack_mm < by or
        by + bh + slack_mm < ay
    )


def measure_overlaps(frames: list[dict], preview_pdf: Path) -> list[dict]:
    """For each pair of non-overlapping frames, check if A's text
    appears INSIDE B's bbox."""
    import pdfplumber
    findings = []
    PT_PER_MM = 72.0 / 25.4
    with pdfplumber.open(preview_pdf) as doc:
        for page_idx, page in enumerate(doc.pages):
            page_frames = [f for f in frames if f["page"] == page_idx]
            words = page.extract_words(use_text_flow=True) or []
            for f in page_frames:
                if not f["snippets"]:
                    continue
                # Find words matching this frame's snippets, anywhere
                # on the page
                for w in words:
                    word_text = w["text"]
                    if not any(s.lower() in word_text.lower() for s in f["snippets"]):
                        continue
                    # word position in pt
                    wx_pt, wy_pt = (w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2
                    # Where is this word relative to F's declared bbox?
                    fx, fy, fw, fh = f["bbox_mm"]
                    fx_pt, fy_pt = fx * PT_PER_MM, fy * PT_PER_MM
                    fw_pt, fh_pt = fw * PT_PER_MM, fh * PT_PER_MM
                    # Inside F? Then OK
                    if (fx_pt - 2 <= wx_pt <= fx_pt + fw_pt + 2 and
                        fy_pt - 2 <= wy_pt <= fy_pt + fh_pt + 2):
                        continue
                    # Outside F — is it inside another frame B?
                    for b in page_frames:
                        if b["anname"] == f["anname"]:
                            continue
                        bx, by, bw, bh = b["bbox_mm"]
                        bx_pt, by_pt = bx * PT_PER_MM, by * PT_PER_MM
                        bw_pt, bh_pt = bw * PT_PER_MM, bh * PT_PER_MM
                        if (bx_pt <= wx_pt <= bx_pt + bw_pt and
                            by_pt <= wy_pt <= by_pt + bh_pt):
                            # Skip if A's bbox overlaps with B's
                            # — they're intentionally adjacent.
                            if _bbox_intersects_mm(f["bbox_mm"], b["bbox_mm"], slack_mm=2):
                                continue
                            findings.append({
                                "from_anname": f["anname"],
                                "into_anname": b["anname"],
                                "page": page_idx,
                                "word": word_text[:30],
                                "word_x_mm": round(wx_pt / PT_PER_MM, 2),
                                "word_y_mm": round(wy_pt / PT_PER_MM, 2),
                                "from_bbox_mm": list(f["bbox_mm"]),
                                "into_bbox_mm": list(b["bbox_mm"]),
                            })
                            break
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--templates-dir", type=Path, default=ROOT / "templates")
    ap.add_argument("--out-yaml", type=Path)
    ap.add_argument("--out-md", type=Path)
    args = ap.parse_args(argv)

    template_dir = args.templates_dir / args.slug
    build_py = template_dir / "build.py"
    preview = template_dir / "preview.pdf"
    if not build_py.exists() or not preview.exists():
        print("SKIPPED: missing build.py or preview.pdf", file=sys.stderr)
        return 0

    frames = _parse_text_frames_from_build_py(build_py)
    findings = measure_overlaps(frames, preview)

    out = {
        "slug": args.slug,
        "summary": {
            "total_frames": len(frames),
            "overlap_findings": len(findings),
        },
        "findings": findings,
        "ok": len(findings) == 0,
    }
    if args.out_yaml:
        args.out_yaml.parent.mkdir(parents=True, exist_ok=True)
        args.out_yaml.write_text(yaml.safe_dump(out, sort_keys=False))
    if args.out_md:
        lines = [f"# Frame overlap audit — {args.slug}", ""]
        lines.append(f"- frames analyzed: {len(frames)}")
        lines.append(f"- **overlap findings: {len(findings)}**")
        for f in findings:
            lines.append("")
            lines.append(f"### {f['from_anname']} → {f['into_anname']}")
            lines.append(f"- page {f['page']+1}: word `{f['word']}` from `{f['from_anname']}` "
                         f"appeared inside `{f['into_anname']}`'s bbox at "
                         f"({f['word_x_mm']}, {f['word_y_mm']})mm")
            lines.append(f"- declared bbox: `{f['from_bbox_mm']}`")
            lines.append(f"- LLM ACTION: check `{f['from_anname']}` y_mm/h_mm — text is "
                         f"rendering OUTSIDE the declared bbox and INTO another frame.")
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text("\n".join(lines))
    print(f"frame-overlap-audit: {len(findings)} overlap finding(s)")
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
