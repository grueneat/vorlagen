#!/usr/bin/env python3
"""audit_alignment — alignment-audit CLI + library (Issue #22).

Per-template Markdown / JSON report listing:
  - Page-by-page primitive inventory (count + side detection).
  - Suspicious-undeclared adjacencies with ready-to-paste constraint
    skeletons (e.g. ``same_x("A", "B", name="p1_x")``).
  - Spine-safety candidates (frames within 3mm of the spine on
    facing-page docs).

CLI:

    python3 tools/audit_alignment.py <slug> [--json | --md FILE.md]
    python3 tools/audit_alignment.py --all [--output-dir build/audit/]
    --axis-tol-mm <float>       (default 5.0)
    --adjacency-tol-mm <float>  (default 12.0)

The CLI always exits 0 — this is informational tooling, not a CI gate
(locked decision #10).
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

# Self-bootstrap so `python3 tools/audit_alignment.py …` and
# `bin/audit-alignment …` both resolve sla_lib.
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))

from sla_lib.builder.bbox import frame_bbox_mm  # noqa: E402
from sla_lib.builder.brand_constraints import (  # noqa: E402
    SIDE_RX, _SpineSafetyRule,
)
from sla_lib.builder.structural_check import (  # noqa: E402
    discover_template_slugs,
)
from sla_lib.builder.template_loader import load_build_module  # noqa: E402

DEFAULTS = dict(axis_tol_mm=5.0, adjacency_tol_mm=12.0, min_drift_mm=0.5)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass
class SuspiciousPair:
    a: str
    b: str
    kind: str          # "axis-x" | "axis-y" | "adjacency-y"
    delta_mm: float
    suggested: str     # ready-to-paste 'same_x("A", "B", name="p1_x")'


@dataclass
class PageAuditReport:
    page_idx: int
    page_label: str
    master_name: str
    side: Optional[str]    # "left" | "right" | None
    n_primitives: int
    declared_pairs: list = field(default_factory=list)        # list[(a, b)]
    suspicious_pairs: list = field(default_factory=list)      # list[SuspiciousPair]
    spine_warnings: list = field(default_factory=list)        # list[str]


@dataclass
class TemplateAuditReport:
    slug: str
    facing_pages: bool
    pages: list = field(default_factory=list)                 # list[PageAuditReport]
    fatal_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Core algorithm (shared between CLI and library)
# ---------------------------------------------------------------------------
def _build_declared(constraints) -> set:
    """Collapse a constraints list into the declared-pair set
    (frozenset symmetric)."""
    declared: set = set()
    for c in constraints or []:
        try:
            names = [n for n in c.referenced_annames() if n]
        except Exception:
            # BrandRule entries (or anything without referenced_annames)
            # don't contribute pairs — skip silently.
            continue
        if len(names) < 2:
            continue
        for a, b in itertools.combinations(names, 2):
            if a != b:
                declared.add(frozenset((a, b)))
    return declared


def _audit_doc(doc, constraints, axis_tol_mm: float,
               adjacency_tol_mm: float,
               slug: str = "<doc>") -> TemplateAuditReport:
    """Library entry point: audit a built Document with its CONSTRAINTS list."""
    declared = _build_declared(constraints)
    rep = TemplateAuditReport(
        slug=slug,
        facing_pages=getattr(doc, "facing_pages", False),
    )
    # Reuse the spine-safety rule for spine warnings (single source of truth).
    spine_rule = _SpineSafetyRule(
        id="brand:spine_safety", name="", description="",
    )
    spine_violations = spine_rule.check(
        list(doc.iter_all_primitives()), doc, constraints=constraints,
    )
    spine_by_target: dict = {}
    for v in spine_violations:
        for t in v.targets:
            spine_by_target.setdefault(t, []).append(v.message)

    for idx, page in enumerate(doc.pages):
        if page.is_master:
            continue
        m = SIDE_RX.search(page.master_name or "")
        side_word = m.group(1).lower() if m else None
        side = {"links": "left", "rechts": "right"}.get(side_word or "")
        spatial = []
        for item in page.items:
            an = getattr(item, "anname", "") or ""
            if not an:
                continue
            bbox = frame_bbox_mm(item, page)
            if bbox is None:
                continue
            spatial.append((an, item, bbox))
        page_rep = PageAuditReport(
            page_idx=idx,
            page_label=page.label or page.master_name or f"page#{idx}",
            master_name=page.master_name or "",
            side=side,
            n_primitives=len(spatial),
        )
        # Declared pairs on this page.
        for i, (pa, _, _) in enumerate(spatial):
            for qa, _, _ in spatial[i + 1:]:
                if frozenset((pa, qa)) in declared:
                    page_rep.declared_pairs.append((pa, qa))
        # Suspicious pairs (same heuristic as _UndeclaredDriftRule).
        for i, (pa, p_item, p_bbox) in enumerate(spatial):
            for qa, q_item, q_bbox in spatial[i + 1:]:
                if frozenset((pa, qa)) in declared:
                    continue
                if (float(getattr(p_item, "rotation_deg", 0) or 0) != 0
                        or float(getattr(q_item, "rotation_deg", 0)
                                 or 0) != 0):
                    continue
                px0, py0, px1, py1 = p_bbox
                qx0, qy0, qx1, qy1 = q_bbox
                dx = abs(px0 - qx0)
                dy = abs(py0 - qy0)
                if DEFAULTS["min_drift_mm"] < dx < axis_tol_mm:
                    page_rep.suspicious_pairs.append(SuspiciousPair(
                        a=pa, b=qa, kind="axis-x", delta_mm=dx,
                        suggested=(
                            f'same_x("{pa}", "{qa}", '
                            f'name="p{idx + 1}_x_{len(page_rep.suspicious_pairs) + 1}")'
                        ),
                    ))
                    continue
                if DEFAULTS["min_drift_mm"] < dy < axis_tol_mm:
                    page_rep.suspicious_pairs.append(SuspiciousPair(
                        a=pa, b=qa, kind="axis-y", delta_mm=dy,
                        suggested=(
                            f'same_y("{pa}", "{qa}", '
                            f'name="p{idx + 1}_y_{len(page_rep.suspicious_pairs) + 1}")'
                        ),
                    ))
                    continue
                if py1 < qy0:
                    gap = qy0 - py1
                    if (DEFAULTS["min_drift_mm"] < gap < adjacency_tol_mm
                            and dx < axis_tol_mm):
                        page_rep.suspicious_pairs.append(SuspiciousPair(
                            a=pa, b=qa, kind="adjacency-y",
                            delta_mm=gap,
                            suggested=(
                                f'aligned_below("{qa}", "{pa}", '
                                f'gap_mm={gap:.2f}, '
                                f'name="p{idx + 1}_below_{len(page_rep.suspicious_pairs) + 1}")'
                            ),
                        ))
        # Attach spine-safety warnings to this page when targets match.
        for an, _, _ in spatial:
            if an in spine_by_target:
                page_rep.spine_warnings.extend(spine_by_target.pop(an))
        rep.pages.append(page_rep)

    # Any spine warnings whose target wasn't matched (e.g. unnamed frames
    # or page-level "unknown master" warnings) get attached to the first
    # page so they don't get lost.
    leftover = []
    for tgts in spine_by_target.values():
        leftover.extend(tgts)
    if leftover and rep.pages:
        rep.pages[0].spine_warnings.extend(leftover)
    return rep


def audit_template(slug: str, root: Path = REPO_ROOT,
                   axis_tol_mm: float = DEFAULTS["axis_tol_mm"],
                   adjacency_tol_mm: float = DEFAULTS["adjacency_tol_mm"]) \
                   -> TemplateAuditReport:
    try:
        mod = load_build_module(slug, root)
        doc = mod.build_doc()
    except Exception as e:
        return TemplateAuditReport(
            slug=slug, facing_pages=False,
            fatal_error=f"build failed: {e!r}",
        )
    constraints = getattr(mod, "CONSTRAINTS", []) or []
    return _audit_doc(doc, constraints, axis_tol_mm, adjacency_tol_mm,
                      slug=slug)


def audit_all(root: Path = REPO_ROOT) -> list:
    """Run audit_template across every discoverable slug."""
    return [audit_template(slug, root) for slug in discover_template_slugs(root)]


# ---------------------------------------------------------------------------
# Output formats
# ---------------------------------------------------------------------------
def report_to_markdown(rep: TemplateAuditReport) -> str:
    lines = [f"# audit_alignment: {rep.slug}", "",
             f"facing_pages: {rep.facing_pages}",
             f"pages: {len(rep.pages)}", ""]
    if rep.fatal_error:
        lines.append(f"FATAL: {rep.fatal_error}")
        return "\n".join(lines)
    lines += [
        "Constraint factories (paste into the template's `CONSTRAINTS = [...]`):",
        "",
        "```python",
        "from sla_lib.builder.constraints import (",
        "    same_x, same_y, aligned_below, inside, distance_x,",
        "    distance_y, equal_gap, same_size,",
        ")",
        "```",
        "",
    ]
    for pr in rep.pages:
        lines.append(
            f"## Page {pr.page_idx + 1} "
            f"(master: {pr.master_name!r}, side: {pr.side or 'n/a'})"
        )
        lines.append(f"- primitives: {pr.n_primitives}")
        lines.append(f"- declared pairs: {len(pr.declared_pairs)}")
        if pr.suspicious_pairs:
            lines.append(
                f"- suspicious-undeclared adjacencies "
                f"({len(pr.suspicious_pairs)}):"
            )
            for sp in pr.suspicious_pairs:
                lines.append(
                    f"  - {sp.kind} drift {sp.delta_mm:.2f}mm: "
                    f"`{sp.a}` ↔ `{sp.b}`"
                )
                lines.append(f"    - suggested: `{sp.suggested}`")
        if pr.spine_warnings:
            lines.append(
                f"- spine-safety candidates ({len(pr.spine_warnings)}):"
            )
            for sw in pr.spine_warnings:
                lines.append(f"  - {sw}")
        lines.append("")
    return "\n".join(lines)


def report_to_json(rep: TemplateAuditReport) -> dict:
    return {
        "slug": rep.slug,
        "facing_pages": rep.facing_pages,
        "fatal_error": rep.fatal_error,
        "pages": [
            {
                "page_idx": pr.page_idx,
                "page_label": pr.page_label,
                "master_name": pr.master_name,
                "side": pr.side,
                "n_primitives": pr.n_primitives,
                "declared_pairs": [[a, b] for a, b in pr.declared_pairs],
                "suspicious_pairs": [
                    {
                        "a": sp.a, "b": sp.b, "kind": sp.kind,
                        "delta_mm": sp.delta_mm,
                        "suggested": sp.suggested,
                    }
                    for sp in pr.suspicious_pairs
                ],
                "spine_warnings": pr.spine_warnings,
            }
            for pr in rep.pages
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="audit_alignment")
    ap.add_argument("slug", nargs="?", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", default=None,
                    help="write Markdown report to PATH instead of stdout")
    ap.add_argument("--output-dir", default=None,
                    help="--all: write per-template Markdown reports here")
    ap.add_argument("--axis-tol-mm", type=float,
                    default=DEFAULTS["axis_tol_mm"])
    ap.add_argument("--adjacency-tol-mm", type=float,
                    default=DEFAULTS["adjacency_tol_mm"])
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    ns = ap.parse_args(argv)
    if ns.all and ns.slug:
        ap.error("Pass either <slug> or --all, not both")
    if not ns.all and not ns.slug:
        ap.error("Pass either <slug> or --all")
    if ns.all:
        reps = audit_all(ns.root)
        if ns.output_dir:
            Path(ns.output_dir).mkdir(parents=True, exist_ok=True)
            for rep in reps:
                (Path(ns.output_dir) / f"{rep.slug}.md").write_text(
                    report_to_markdown(rep), encoding="utf-8")
        elif ns.json:
            print(json.dumps(
                [report_to_json(r) for r in reps],
                indent=2, ensure_ascii=False,
            ))
        else:
            for rep in reps:
                print(report_to_markdown(rep))
                print()
        return 0
    rep = audit_template(
        ns.slug, ns.root,
        axis_tol_mm=ns.axis_tol_mm,
        adjacency_tol_mm=ns.adjacency_tol_mm,
    )
    if ns.json:
        print(json.dumps(report_to_json(rep), indent=2, ensure_ascii=False))
    elif ns.md:
        Path(ns.md).write_text(report_to_markdown(rep), encoding="utf-8")
    else:
        print(report_to_markdown(rep))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
