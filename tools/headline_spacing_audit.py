#!/usr/bin/env python3
"""headline_spacing_audit — catch tight/uneven stacked-headline line spacing.

Multi-part headlines are emitted as one single-line ``TextFrame`` per visual
line (``X``, ``X_l2``, ``X_l3`` …, see ``sla_lib.builder.headline``). Scribus
places each frame's single baseline one FONT ASCENT below the frame top
(``FLOP=1``), so the visible inter-baseline gap is::

    gap_k = (YPOS_{k+1} - YPOS_k) + ascent(font_{k+1}) - ascent(font_k)

This audit groups the line frames by anname stem and flags:

* ``too_tight``       — any gap below ``min_ratio * fontsize`` (absolute floor).
* ``uneven``          — ``(max_gap - min_gap) / mean_gap`` beyond ``even_tol``.
* ``top_gap_collapse`` — the "dreizeilige" signature: the top gap is materially
                        smaller than the mean of the others
                        (``top_gap < top_collapse_ratio * mean_other``).

Two measurement paths:

* STATIC (``--static-only``, CI-safe, no render): expected baselines from
  ``FLOP=1`` + fontTools ascent (the same metric reader the corrector uses),
  read straight off the SLA geometry via ``sla_lib.reader.SLADocument``.
* PIXEL (default, local truth): rendered ink-tops from ``preview.pdf`` via the
  authoritative E4 scanner (``line_spacing_pixel_audit.measure_split_headline``).

The relative checks (uneven / top-collapse) are ratio-based, so a uniformly
tight but EVEN single-font headline passes — only the absolute ``min_ratio``
floor catches a genuinely-too-tight stack.

Usage::

    python3 tools/headline_spacing_audit.py --slug <slug> [--static-only]
    python3 tools/headline_spacing_audit.py --slug <slug> --templates-dir templates \
        --out-yaml build/validation/<slug>/headline_spacing_audit.yml
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from sla_lib.builder.headline import font_ascent_pt  # noqa: E402
from sla_lib.reader import SLADocument  # noqa: E402

# ---------------------------------------------------------------------------
# Thresholds. LOCKED from the corrected Task-2/3 renders so the passing
# templates set the floor (see SKILL_FINDINGS.md). The minimum INK-TOP gap
# ratio across all 12 corrected templates is 0.832 (the canonical uaf8
# Vollkorn->Barlow gap); the STATIC path measures even baselines (0.90). A
# single 0.80 floor sits below both corrected minima yet still flags the
# pre-fix collapse (0.72 on the top gap) — confirmed against pre/post renders.
# even_tol is 0.18: even BASELINES (the corrected target) still yield mildly
# uneven INK-TOP gaps because Barlow and Vollkorn cap heights differ — the
# worst corrected 3-line stack measures 0.154 ink-top spread, so 0.18 clears
# the cap-height artifact while still flagging the pre-fix collapse (0.321).
# The relative checks (uneven / top_gap_collapse) are ratio-based, so a
# uniformly-tight EVEN single-font stack passes (no false positive); only the
# absolute floor catches a genuinely-too-tight stack.
DEFAULT_MIN_RATIO = 0.80          # too_tight: gap < min_ratio * fontsize
DEFAULT_EVEN_TOL = 0.18           # uneven: (max-min)/mean > even_tol
DEFAULT_TOP_COLLAPSE_RATIO = 0.9  # top_gap_collapse: top < ratio * mean(others)
PT_TO_MM = 25.4 / 72.0


@dataclass
class LineFrame:
    anname: str
    ypos_pt: float
    font: str
    fontsize_pt: float


@dataclass
class StackGroup:
    stem: str
    lines: list[LineFrame]

    @property
    def fontsizes(self) -> list[float]:
        return [ln.fontsize_pt for ln in self.lines]


@dataclass
class Violation:
    stem: str
    kind: str       # too_tight | uneven | top_gap_collapse
    detail: str
    gaps_pt: list[float]


@dataclass
class AuditReport:
    slug: str
    mode: str  # "static" | "pixel"
    stacks: int = 0
    violations: list[Violation] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 1 if self.violations else 0

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "mode": self.mode,
            "stacks": self.stacks,
            "ok": not self.violations,
            "violations": [
                {
                    "stem": v.stem,
                    "kind": v.kind,
                    "detail": v.detail,
                    "gaps_pt": [round(g, 3) for g in v.gaps_pt],
                }
                for v in self.violations
            ],
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Geometry: read stacked-headline groups straight from the SLA.
# ---------------------------------------------------------------------------
def _first_itext(frame) -> Optional[object]:
    for it in frame.iter("ITEXT"):
        return it
    return None


def _line_index(anname: str) -> int:
    if "_l" in anname:
        tail = anname.rpartition("_l")[2]
        if tail.isdigit():
            return int(tail)
    return 1


def collect_stacks(sla_path: Path | str) -> list[StackGroup]:
    """Group stacked single-line headline frames by anname stem.

    A stem ``X`` with at least one sibling ``X_l2``/``X_l3``/… forms a stack.
    Frames are read from the SLA so headline_stack-generated geometry (which is
    not literal in build.py) is seen.
    """
    doc = SLADocument(sla_path)
    by_anname: dict[str, LineFrame] = {}
    for obj in doc.page_objects():
        anname = obj.attrib.get("ANNAME", "")
        if not anname:
            continue
        it = _first_itext(obj)
        if it is None:
            continue  # not a text frame with runs
        font = it.attrib.get("FONT")
        size = it.attrib.get("FONTSIZE")
        if font is None or size is None:
            continue
        try:
            ypos = float(obj.attrib.get("YPOS", "0"))
            fontsize = float(size)
        except ValueError:
            continue
        by_anname[anname] = LineFrame(anname, ypos, font, fontsize)

    groups: dict[str, list[str]] = {}
    for an in by_anname:
        stem = an
        if "_l" in an:
            head, _, tail = an.rpartition("_l")
            if tail.isdigit() and int(tail) >= 2 and head:
                stem = head
        groups.setdefault(stem, []).append(an)

    out: list[StackGroup] = []
    for stem, members in groups.items():
        if len(members) < 2 or stem not in by_anname:
            continue
        ordered = sorted(members, key=_line_index)
        out.append(StackGroup(stem, [by_anname[a] for a in ordered]))
    return out


# ---------------------------------------------------------------------------
# Gap evaluation (shared by static + pixel paths).
# ---------------------------------------------------------------------------
def _evaluate_gaps(
    stem: str,
    gaps_pt: list[float],
    fontsizes: list[float],
    *,
    min_ratio: float,
    even_tol: float,
    top_collapse_ratio: float,
) -> list[Violation]:
    """Apply the three checks to a stack's inter-baseline gaps."""
    if not gaps_pt:
        return []
    violations: list[Violation] = []

    # too_tight (absolute floor, per-gap against the smaller adjacent fontsize).
    for i, g in enumerate(gaps_pt):
        size = min(fontsizes[i], fontsizes[i + 1])
        floor = min_ratio * size
        if g < floor:
            violations.append(Violation(
                stem, "too_tight",
                f"gap {i} = {g:.2f}pt < floor {floor:.2f}pt "
                f"({min_ratio:.2f}*{size:.0f})",
                gaps_pt,
            ))

    mean_gap = sum(gaps_pt) / len(gaps_pt)
    if mean_gap > 0:
        spread = (max(gaps_pt) - min(gaps_pt)) / mean_gap
        if spread > even_tol:
            violations.append(Violation(
                stem, "uneven",
                f"(max-min)/mean = {spread:.3f} > {even_tol:.2f} "
                f"(gaps {[round(g, 2) for g in gaps_pt]})",
                gaps_pt,
            ))

    # top_gap_collapse: only meaningful with >= 2 gaps.
    if len(gaps_pt) >= 2:
        top = gaps_pt[0]
        others = gaps_pt[1:]
        mean_other = sum(others) / len(others)
        if mean_other > 0 and top < top_collapse_ratio * mean_other:
            violations.append(Violation(
                stem, "top_gap_collapse",
                f"top gap {top:.2f}pt < {top_collapse_ratio:.2f} * "
                f"mean(others) {mean_other:.2f}pt",
                gaps_pt,
            ))
    return violations


def _static_gaps(stack: StackGroup) -> list[float]:
    """Expected FLOP=1 inter-baseline gaps from real font ascents."""
    baselines = [
        ln.ypos_pt + font_ascent_pt(ln.font, ln.fontsize_pt)
        for ln in stack.lines
    ]
    return [baselines[i + 1] - baselines[i] for i in range(len(baselines) - 1)]


# ---------------------------------------------------------------------------
# Static path (no render).
# ---------------------------------------------------------------------------
def audit_static(
    sla_path: Path | str,
    *,
    slug: str = "",
    min_ratio: float = DEFAULT_MIN_RATIO,
    even_tol: float = DEFAULT_EVEN_TOL,
    top_collapse_ratio: float = DEFAULT_TOP_COLLAPSE_RATIO,
) -> AuditReport:
    stacks = collect_stacks(sla_path)
    report = AuditReport(slug=slug, mode="static", stacks=len(stacks))
    for stack in stacks:
        gaps = _static_gaps(stack)
        report.violations.extend(_evaluate_gaps(
            stack.stem, gaps, stack.fontsizes,
            min_ratio=min_ratio, even_tol=even_tol,
            top_collapse_ratio=top_collapse_ratio,
        ))
    return report


# ---------------------------------------------------------------------------
# Pixel path (render truth) — reuses the E4 ink-top scanner.
# ---------------------------------------------------------------------------
def audit_pixel(
    slug: str,
    templates_dir: Path,
    *,
    dpi: int = 150,
    min_ratio: float = DEFAULT_MIN_RATIO,
    even_tol: float = DEFAULT_EVEN_TOL,
    top_collapse_ratio: float = DEFAULT_TOP_COLLAPSE_RATIO,
) -> AuditReport:
    """Measure rendered ink-top gaps and apply the same checks.

    Reuses ``line_spacing_pixel_audit`` (E4): its SLA frame loader + the
    colour-scanned ``measure_split_headline``. The rendered preview gives the
    absolute per-line ink-top, so gaps reflect what Scribus actually drew.
    """
    import tempfile

    import line_spacing_pixel_audit as e4

    tdir = templates_dir / slug
    sla = tdir / "template.sla"
    preview = tdir / "preview.pdf"
    report = AuditReport(slug=slug, mode="pixel")
    if not (sla.exists() and preview.exists()):
        report.notes.append(f"missing template.sla/preview.pdf in {tdir}")
        return report

    frames = e4.parse_textframes_from_sla(sla)
    groups = e4.detect_split_headline_groups(frames)
    report.stacks = len(groups)
    if not groups:
        return report

    # Per-line fontsize for the absolute-floor check (read off the SLA).
    fontsize_by_anname = {
        ln.anname: ln.fontsize_pt
        for stack in collect_stacks(sla)
        for ln in stack.lines
    }

    tmp = Path(tempfile.mkdtemp(prefix="hsa_pixel_"))
    preview_pngs = e4.render_pdf_pages_to_png(preview, dpi, tmp / "preview")
    # measure_split_headline diffs preview vs baseline; for an absolute-gap
    # check we scan the preview against itself (drift path unused here) and
    # read the per-line preview ink-tops it reports.
    for grp in groups:
        meas = e4.measure_split_headline(
            grp, frames, preview_pngs, preview_pngs, dpi
        )
        per_line = meas.get("per_line", [])
        tops = [pl.get("preview_top_pt") for pl in per_line]
        if any(t is None for t in tops) or len(tops) < 2:
            report.notes.append(f"{grp[0]}: incomplete ink-top scan; skipped")
            continue
        gaps = [tops[i + 1] - tops[i] for i in range(len(tops) - 1)]
        fontsizes = [fontsize_by_anname.get(a, 30.0) for a in grp]
        report.violations.extend(_evaluate_gaps(
            grp[0], gaps, fontsizes,
            min_ratio=min_ratio, even_tol=even_tol,
            top_collapse_ratio=top_collapse_ratio,
        ))
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="headline_spacing_audit",
                                 description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--templates-dir", default="templates")
    ap.add_argument("--out-yaml")
    ap.add_argument("--static-only", action="store_true",
                    help="Run the no-render static check only (CI-safe).")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--min-ratio", type=float, default=DEFAULT_MIN_RATIO)
    ap.add_argument("--even-tol", type=float, default=DEFAULT_EVEN_TOL)
    ap.add_argument("--top-collapse-ratio", type=float,
                    default=DEFAULT_TOP_COLLAPSE_RATIO)
    args = ap.parse_args(argv)

    templates_dir = Path(args.templates_dir)
    sla = templates_dir / args.slug / "template.sla"
    if not sla.exists():
        sys.stderr.write(f"missing {sla}\n")
        return 2

    if args.static_only:
        report = audit_static(
            sla, slug=args.slug,
            min_ratio=args.min_ratio, even_tol=args.even_tol,
            top_collapse_ratio=args.top_collapse_ratio,
        )
    else:
        report = audit_pixel(
            args.slug, templates_dir, dpi=args.dpi,
            min_ratio=args.min_ratio, even_tol=args.even_tol,
            top_collapse_ratio=args.top_collapse_ratio,
        )

    if args.out_yaml:
        import yaml
        out = Path(args.out_yaml)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump(report.to_dict(), sort_keys=False))

    if report.violations:
        sys.stderr.write(
            f"headline_spacing_audit: {args.slug} — "
            f"{len(report.violations)} violation(s) across "
            f"{report.stacks} stack(s):\n"
        )
        for v in report.violations:
            sys.stderr.write(f"  [{v.kind}] {v.stem}: {v.detail}\n")
    else:
        sys.stdout.write(
            f"headline_spacing_audit: {args.slug} OK "
            f"({report.stacks} stack(s), {report.mode})\n"
        )
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
