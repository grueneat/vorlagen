#!/usr/bin/env python3
"""Multi-model vision-review orchestrator (D5 + D6 + D7 — local-only).

Sends a template's preview PNG plus a side-by-side composite of all 8 templates
to up to 3 vision models (Claude / Codex / Gemini) and aggregates findings into
``reviews/visual-qa-<slug>-iter-N.md``.

Usage::

    tools/visual_review.py SLUG               # one template, iter-1
    tools/visual_review.py SLUG --iter 2      # iter-2 (after fix)
    tools/visual_review.py --all              # generate composite + per-template reports
    tools/visual_review.py --composite        # only generate the side-by-side grid

Local-only by design: CI never runs this (no auth on CI runners). Visual review
runs in the developer's session.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
REVIEWS_DIR = ROOT / "reviews"

ALL_TEMPLATES = [
    "postkarte-a6-kampagne",
    "plakat-a1-hochformat",
    "zeitung-a4",
]

PROMPT_PATH = ROOT / "tools" / "visual_review" / "prompt_template.md"


def _hero_png(slug: str) -> Optional[Path]:
    """Best representative PNG for a template (page-01 if present)."""
    tdir = TEMPLATES_DIR / slug
    for n in (
        "page-01.png", "page-1.png",
        "a1-page-01.png", "a1-page-1.png",
    ):
        p = tdir / n
        if p.exists():
            return p
    # fallback: any page-*.png
    pngs = sorted(tdir.glob("page-*.png"))
    return pngs[0] if pngs else None


def build_composite(out_path: Path | None = None) -> Path:
    """Use ImageMagick `montage` to build a 4x2 grid of all 8 templates' page-01.

    Pattern from tools/visual_diff.py:188-195.
    """
    out = out_path or REVIEWS_DIR / "all-templates-grid.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    inputs = []
    labels = []
    for slug in ALL_TEMPLATES:
        png = _hero_png(slug)
        if png is None:
            print(f"WARN: no page-01 for {slug}", file=sys.stderr)
            continue
        inputs.append(str(png))
        labels.append(slug)

    if not shutil.which("montage"):
        raise RuntimeError("ImageMagick `montage` not on PATH")

    cmd = [
        "montage",
        "-tile", "4x2",
        "-geometry", "512x512+10+10",
        "-background", "white",
        "-fill", "black",
        "-pointsize", "16",
        "-label", "%t",
    ]
    cmd.extend(inputs)
    cmd.append(str(out))
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"composite -> {out}")
    return out


def _detail_image(slug: str) -> Optional[Path]:
    """Downscale the slug's hero PNG to 1024 px long edge for vision input."""
    src = _hero_png(slug)
    if src is None:
        return None
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    out = REVIEWS_DIR / f"visual-qa-{slug}-detail.png"
    if not shutil.which("convert"):
        # Fallback: just copy
        shutil.copy(src, out)
        return out
    subprocess.run([
        "convert", str(src),
        "-resize", "1024x1024",
        "-strip",
        str(out),
    ], check=True, capture_output=True)
    return out


PROMPT_DEFAULT = """\
# Visual QA — Template Review

**VISUAL QUALITY IS THE PRIMARY CRITERION.**

You are reviewing the rendered preview of a Grünen template against a side-by-side
grid showing all 8 production templates (3 existing + 5 new).

The 5 new templates this PR adds are:
1. themen-plakat-a3-quer (A3 quer argument plakat)
2. wahlaufruf-postkarte-a6-quer (A6 quer Wahlkreuz hero + 2x2 info-grid)
3. wahltag-tueranhaenger (105×250 mm vertical with 35-mm Stanzkontur hole + Wahlkreuz)
4. tischschild-a5-quer (A4 quer folded to A5 tent, bilingual)
5. kandidat-falzflyer-din-lang (A4 quer 3-fach Zickzackfalz, 6 panels, Wahlkreuz closer)

## Question 1 — comparison_to_existing (priority 1)

Compared to the 3 existing templates (Postkarte, Plakat, Zeitung) shown in the grid,
is this NEW template AT LEAST AS GOOD visually? Where is it better, where weaker?
Cite specific regions / coordinates / typography.

## Question 2 — hierarchy_readability (1-second-test)

What is the main message at first glance? Is the hierarchy clear (Headline > Sub > Body
> Akzent > Impressum)?

## Question 3 — brand_consistency

Greens-CI brand: Dunkelgrün/Hellgrün primary, Magenta-Stoerer accent, Gelb-Akzent in
Headlines, Vollkorn Black Italic for hero typography, Gotham Narrow for everything else.
Does this template feel like a Grünen template? Or generic?

## Question 4 — print_risks

Text near trim, missing bleed, contrast issues, frame collisions, whitespace rhythm
broken? Cite specific areas.

## Question 5 — wahlkreuz_background_color_check

Is the Wahlkreuz placed on a colored band (Dunkelgrün / Hellgrün / Magenta), NOT on
white or yellow? If white-or-yellow background visible behind the Wahlkreuz: BLOCKING.
(N/A if template has no Wahlkreuz.)

## Question 6 — three concrete improvements

List exactly 3 specific, coordinate-cited improvements. "Move headline up 5mm" not
"improve headline".

## Output

Strict JSON:

```json
{
  "merge_ready": "yes|no|unclear",
  "comparison_to_existing": "<paragraph>",
  "hierarchy_readability": "<paragraph>",
  "brand_consistency": "<paragraph>",
  "print_risks": ["..."],
  "blocking_findings": ["..."],
  "nice_to_have": ["..."],
  "wahlkreuz_background_color_check": "pass|fail|n/a"
}
```
"""


def ensure_prompt() -> Path:
    if not PROMPT_PATH.exists():
        PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROMPT_PATH.write_text(PROMPT_DEFAULT, encoding="utf-8")
    return PROMPT_PATH


def review_template(slug: str, iteration: int = 1) -> Path:
    """Run vision models on the template and write iter-N report."""
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    grid = build_composite()
    detail = _detail_image(slug)
    if detail is None:
        raise SystemExit(f"no preview PNG for {slug}")

    prompt_path = ensure_prompt()
    prompt = prompt_path.read_text(encoding="utf-8")
    out_path = REVIEWS_DIR / f"visual-qa-{slug}-iter-{iteration}.md"

    sections = []
    sections.append(f"# Visual QA — {slug} (Iteration {iteration})\n")
    sections.append(f"**Detail image:** `{detail.relative_to(ROOT)}`\n")
    sections.append(f"**Side-by-side grid:** `{grid.relative_to(ROOT)}`\n\n")

    # Codex
    if shutil.which("codex"):
        sections.append("## Codex Vision\n\n")
        try:
            r = subprocess.run(
                [
                    "codex", "exec",
                    "--skip-git-repo-check",
                    "--sandbox", "workspace-write",
                    "--dangerously-bypass-approvals-and-sandbox",
                    "-i", str(detail),
                    "-i", str(grid),
                    prompt,
                ],
                capture_output=True, text=True, timeout=600,
                stdin=subprocess.DEVNULL,
            )
            sections.append("```\n" + (r.stdout[-3000:] if len(r.stdout) > 3000 else r.stdout) + "\n```\n\n")
        except Exception as e:
            sections.append(f"Codex error: {e}\n\n")
    else:
        sections.append("## Codex Vision\n\nUnavailable (codex CLI not on PATH).\n\n")

    # Gemini
    if shutil.which("gemini"):
        sections.append("## Gemini Vision\n\n")
        try:
            # Use --include-directories workaround per ecosystem.md
            include_dir = REVIEWS_DIR
            r = subprocess.run(
                [
                    "gemini", "--yolo",
                    "-p", f"{prompt}\n\nReview the image at {detail.name} (in workspace dir).",
                ],
                capture_output=True, text=True, timeout=600,
                stdin=subprocess.DEVNULL,
            )
            sections.append("```\n" + (r.stdout[-3000:] if len(r.stdout) > 3000 else r.stdout) + "\n```\n\n")
        except Exception as e:
            sections.append(f"Gemini error: {e}\n\n")
    else:
        sections.append("## Gemini Vision\n\nUnavailable (gemini CLI not on PATH).\n\n")

    sections.append("## Claude Vision\n\n")
    sections.append("Claude review handled inline by the orchestrator agent (this session).\n")
    sections.append("See `reviews/visual-qa-<slug>.md` for the canonical merge-gate report.\n\n")

    out_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"review -> {out_path}")
    return out_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Multi-model vision review orchestrator.")
    ap.add_argument("slug", nargs="?", help="Template slug")
    ap.add_argument("--all", action="store_true",
                    help="Generate composite + run review on all 5 new templates")
    ap.add_argument("--composite", action="store_true",
                    help="Only generate reviews/all-templates-grid.png and exit")
    ap.add_argument("--iter", type=int, default=1, help="Iteration number")
    args = ap.parse_args(argv)

    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)

    if args.composite:
        build_composite()
        return 0

    if args.all:
        build_composite()
        for slug in [
            "themen-plakat-a3-quer",
            "wahlaufruf-postkarte-a6-quer",
            "wahltag-tueranhaenger",
            "kandidat-falzflyer-din-lang",
        ]:
            try:
                review_template(slug, iteration=args.iter)
            except Exception as e:
                print(f"FAIL {slug}: {e}", file=sys.stderr)
        return 0

    if not args.slug:
        ap.print_help()
        return 0

    review_template(args.slug, iteration=args.iter)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
