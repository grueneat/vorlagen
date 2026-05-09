#!/usr/bin/env python3
"""audit_alignment — alignment-audit CLI + library (Issue #22 + #23).

Per-template Markdown / JSON report listing:
  - Page-by-page primitive inventory (count + side detection).
  - Suspicious-undeclared adjacencies with ready-to-paste constraint
    skeletons (e.g. ``same_x("A", "B", name="p1_x")``) PLUS the
    geometric-outcome alternative (e.g. "OR fix geometry: A.x=N").
  - Spine-safety candidates (frames within 3mm of the spine on
    facing-page docs).
  - Tolerance-suspicion findings (Issue #23 locked decision #6):
    constraints whose ``tolerance_mm > 1.0`` or ``gap_mm > 30.0`` are
    flagged as suspicious encode-and-silence patterns.

CLI:

    python3 tools/audit_alignment.py <slug> [--json | --md FILE.md]
    python3 tools/audit_alignment.py --all [--output-dir build/audit/]
    --axis-tol-mm <float>       (default 25.0; was 5.0 pre-#23)
    --adjacency-tol-mm <float>  (default 30.0; was 12.0 pre-#23)
    --strict                    (Issue #23: exit 1 on any finding;
                                 used by Phase 3b verification gate)

Without ``--strict`` the CLI exits 0 — informational tooling. With
``--strict`` it exits 1 if any suspicious-pair OR tolerance-suspicion
finding is emitted across any template.
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

DEFAULTS = dict(axis_tol_mm=25.0, adjacency_tol_mm=30.0, min_drift_mm=0.5)
# Tolerance-suspicion thresholds (Issue #23 locked decision #6).
SUSPICIOUS_TOLERANCE_MM = 1.0
SUSPICIOUS_GAP_MM = 30.0


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
    geometric_alternative: str = ""  # Issue #23: "OR fix geometry: A.x=N..."


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
    image_extent_warnings: list = field(default_factory=list)  # Issue #24
    band_consistency_warnings: list = field(default_factory=list)  # Issue #25


@dataclass
class ToleranceSuspicion:
    """A constraint whose declared tolerance/gap exceeds the suspicious threshold.

    Issue #23 locked decision #6: encode-and-silence has two patterns —
    declaring with a widened tolerance to absorb drift, OR declaring a
    larger gap than visually intended. Both surface as suspicions here.
    """
    constraint_id: str
    constraint_name: str
    tolerance_mm: Optional[float]
    gap_mm: Optional[float]
    targets: list
    message: str


@dataclass
class TemplateAuditReport:
    slug: str
    facing_pages: bool
    pages: list = field(default_factory=list)                 # list[PageAuditReport]
    fatal_error: Optional[str] = None
    tolerance_suspicions: list = field(default_factory=list)  # list[ToleranceSuspicion]


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
               slug: str = "<doc>",
               *,
               check_image_extent: bool = True,
               check_brand_rules: bool = True) -> TemplateAuditReport:
    """Library entry point: audit a built Document with its CONSTRAINTS list.

    Args:
        doc, constraints, axis_tol_mm, adjacency_tol_mm, slug: existing
            #22/#23 surface — see file docstring.
        check_image_extent: When True (default) runs the
            ``brand:image_fills_frame`` rule (Issue #24) and distributes
            its violations into per-page ``image_extent_warnings``.
            Pass False to skip the check entirely.
        check_brand_rules: When True (default) runs the
            ``brand:band_consistency`` rule (Issue #25) and distributes
            its violations into per-page ``band_consistency_warnings``.
            Pass False to skip the check entirely.
    """
    declared = _build_declared(constraints)
    rep = TemplateAuditReport(
        slug=slug,
        facing_pages=getattr(doc, "facing_pages", False),
    )
    # Issue #23 locked decision #6: tolerance-suspicion findings.
    for c in constraints or []:
        tol = getattr(c, "tolerance_mm", None)
        gap = getattr(c, "gap_mm", None)
        suspicious = False
        notes = []
        if tol is not None and tol > SUSPICIOUS_TOLERANCE_MM:
            suspicious = True
            notes.append(f"tolerance_mm={tol:.2f} (> {SUSPICIOUS_TOLERANCE_MM:.1f})")
        if gap is not None and gap > SUSPICIOUS_GAP_MM:
            suspicious = True
            notes.append(f"gap_mm={gap:.2f} (> {SUSPICIOUS_GAP_MM:.1f})")
        if not suspicious:
            continue
        try:
            targets = list(c.referenced_annames())
        except Exception:
            targets = list(getattr(c, "targets", ()))
        cname = getattr(c, "name", "") or c.id
        rep.tolerance_suspicions.append(ToleranceSuspicion(
            constraint_id=c.id,
            constraint_name=cname,
            tolerance_mm=tol,
            gap_mm=gap,
            targets=targets,
            message=(
                f"constraint {cname!r} on {targets} declared with "
                f"{', '.join(notes)}. Was the geometry intent fuzzy or "
                f"did the spec drift to absorb misalignment? Consider "
                f"tightening to tolerance_mm=0.5 (default) or fixing "
                f"the geometry."
            ),
        ))
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

    # Issue #24: image-fills-frame check (catches INJECT_MAP target
    # drift + aspect-mismatch letterboxing). Per-page distribution
    # mirrors the spine_by_target pattern above. Lazy-import to avoid
    # circular-import risk when audit_alignment is imported from rule
    # code paths.
    image_extent_by_target: dict = {}
    if check_image_extent:
        from sla_lib.builder.brand_constraints import _ImageFillsFrameRule
        image_rule = _ImageFillsFrameRule(
            id="brand:image_fills_frame", name="", description="",
        )
        for v in image_rule.check(
            list(doc.iter_all_primitives()), doc, constraints=constraints,
        ):
            for t in v.targets:
                image_extent_by_target.setdefault(t, []).append(
                    f"[{v.severity.upper()}] {v.message}"
                )

    # Issue #25: band consistency (replaces 3 originally-planned rules).
    # Mirrors the spine_by_target / image_extent_by_target pattern above.
    # Lazy-import to avoid circular-import risk.
    band_by_target: dict = {}
    if check_brand_rules:
        from sla_lib.builder.brand_constraints import _BandConsistencyRule
        band_rule = _BandConsistencyRule(
            id="brand:band_consistency", name="", description="",
        )
        for v in band_rule.check(
            list(doc.iter_all_primitives()), doc, constraints=constraints,
        ):
            for t in v.targets:
                band_by_target.setdefault(t, []).append(
                    f"[{v.severity.upper()}] {v.message}"
                )

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
                    target_x = (px0 + qx0) / 2
                    page_rep.suspicious_pairs.append(SuspiciousPair(
                        a=pa, b=qa, kind="axis-x", delta_mm=dx,
                        suggested=(
                            f'same_x("{pa}", "{qa}", '
                            f'name="p{idx + 1}_x_{len(page_rep.suspicious_pairs) + 1}")'
                        ),
                        geometric_alternative=(
                            f"OR fix geometry: set {pa}.x_mm={target_x:.2f} "
                            f"and {qa}.x_mm={target_x:.2f} to share the axis."
                        ),
                    ))
                    continue
                if DEFAULTS["min_drift_mm"] < dy < axis_tol_mm:
                    target_y = (py0 + qy0) / 2
                    page_rep.suspicious_pairs.append(SuspiciousPair(
                        a=pa, b=qa, kind="axis-y", delta_mm=dy,
                        suggested=(
                            f'same_y("{pa}", "{qa}", '
                            f'name="p{idx + 1}_y_{len(page_rep.suspicious_pairs) + 1}")'
                        ),
                        geometric_alternative=(
                            f"OR fix geometry: set {pa}.y_mm={target_y:.2f} "
                            f"and {qa}.y_mm={target_y:.2f} to share the axis."
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
                            geometric_alternative=(
                                f"OR fix geometry: set {qa}.y_mm="
                                f"{py1:.2f} (touching {pa}.bottom)."
                            ),
                        ))
        # Attach spine-safety warnings to this page when targets match.
        for an, _, _ in spatial:
            if an in spine_by_target:
                page_rep.spine_warnings.extend(spine_by_target.pop(an))
        # Issue #24: attach image-fills-frame warnings to this page
        # when the frame's anname matches. Walk all page items (not
        # just the spatial subset, which excludes anonymous frames) so
        # rule-emitted "<unnamed y=...>" identifiers are also caught.
        for it in page.items:
            an = getattr(it, "anname", "") or ""
            if an and an in image_extent_by_target:
                page_rep.image_extent_warnings.extend(
                    image_extent_by_target.pop(an)
                )
            else:
                # Match anonymous frames by the rule's "<unnamed y=N>"
                # identifier shape so they don't get lost.
                anon_key = f"<unnamed y={getattr(it, 'y_mm', 0):.1f}>"
                if anon_key in image_extent_by_target:
                    page_rep.image_extent_warnings.extend(
                        image_extent_by_target.pop(anon_key)
                    )
        # Issue #25: attach band-consistency warnings to this page.
        # The rule emits both ``<unnamed y=N>`` (band intrusion) and
        # ``<unnamed x=N>`` (margin drift) shapes so we check both.
        for it in page.items:
            an = getattr(it, "anname", "") or ""
            if an and an in band_by_target:
                page_rep.band_consistency_warnings.extend(
                    band_by_target.pop(an)
                )
                continue
            anon_y_key = f"<unnamed y={getattr(it, 'y_mm', 0):.1f}>"
            if anon_y_key in band_by_target:
                page_rep.band_consistency_warnings.extend(
                    band_by_target.pop(anon_y_key)
                )
            anon_x_key = f"<unnamed x={getattr(it, 'x_mm', 0):.1f}>"
            if anon_x_key in band_by_target:
                page_rep.band_consistency_warnings.extend(
                    band_by_target.pop(anon_x_key)
                )
        rep.pages.append(page_rep)

    # Any spine warnings whose target wasn't matched (e.g. unnamed frames
    # or page-level "unknown master" warnings) get attached to the first
    # page so they don't get lost.
    leftover = []
    for tgts in spine_by_target.values():
        leftover.extend(tgts)
    if leftover and rep.pages:
        rep.pages[0].spine_warnings.extend(leftover)
    # Same for image-extent leftovers (unmatched anname/anon-key — should
    # be empty in practice, but defensive).
    img_leftover = []
    for tgts in image_extent_by_target.values():
        img_leftover.extend(tgts)
    if img_leftover and rep.pages:
        rep.pages[0].image_extent_warnings.extend(img_leftover)
    # Issue #25: same defensive leftover handling for band-consistency.
    band_leftover = []
    for tgts in band_by_target.values():
        band_leftover.extend(tgts)
    if band_leftover and rep.pages:
        rep.pages[0].band_consistency_warnings.extend(band_leftover)
    return rep


def audit_template(slug: str, root: Path = REPO_ROOT,
                   axis_tol_mm: float = DEFAULTS["axis_tol_mm"],
                   adjacency_tol_mm: float = DEFAULTS["adjacency_tol_mm"],
                   *,
                   check_image_extent: bool = True,
                   check_brand_rules: bool = True) \
                   -> TemplateAuditReport:
    try:
        mod = load_build_module(slug, root)
        # Issue #24: prefer build_preview() when available so the
        # image-fills-frame rule sees inline-injected state. The
        # INJECT_MAP-drift class (#24's primary bug) is invisible
        # without inline image bytes — build_doc() returns the clean
        # end-user variant where named photo frames have empty
        # inline_image_data. Falls back to build_doc() for templates
        # without a preview variant.
        if check_image_extent and hasattr(mod, "build_preview"):
            doc = mod.build_preview()
        else:
            doc = mod.build_doc()
    except Exception as e:
        return TemplateAuditReport(
            slug=slug, facing_pages=False,
            fatal_error=f"build failed: {e!r}",
        )
    constraints = getattr(mod, "CONSTRAINTS", []) or []
    return _audit_doc(doc, constraints, axis_tol_mm, adjacency_tol_mm,
                      slug=slug, check_image_extent=check_image_extent,
                      check_brand_rules=check_brand_rules)


def audit_all(root: Path = REPO_ROOT,
              *, check_image_extent: bool = True,
              check_brand_rules: bool = True) -> list:
    """Run audit_template across every discoverable slug."""
    return [audit_template(slug, root,
                           check_image_extent=check_image_extent,
                           check_brand_rules=check_brand_rules)
            for slug in discover_template_slugs(root)]


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
    if rep.tolerance_suspicions:
        lines.append(
            f"## Tolerance-suspicion findings "
            f"({len(rep.tolerance_suspicions)})"
        )
        lines.append(
            "_Constraints declared with `tolerance_mm > 1.0` or "
            "`gap_mm > 30.0` — possible encode-and-silence pattern. "
            "Issue #23 locked decision #6._"
        )
        for ts in rep.tolerance_suspicions:
            lines.append(f"- `{ts.constraint_name}` ({ts.constraint_id}): "
                         f"{ts.message}")
        lines.append("")
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
                if sp.geometric_alternative:
                    lines.append(f"    - {sp.geometric_alternative}")
        if pr.spine_warnings:
            lines.append(
                f"- spine-safety candidates ({len(pr.spine_warnings)}):"
            )
            for sw in pr.spine_warnings:
                lines.append(f"  - {sw}")
        if pr.image_extent_warnings:
            lines.append(
                f"### Image-fills-frame warnings "
                f"({len(pr.image_extent_warnings)})"
            )
            for iw in pr.image_extent_warnings:
                lines.append(f"- {iw}")
        if pr.band_consistency_warnings:
            lines.append(
                f"### Band consistency "
                f"({len(pr.band_consistency_warnings)})"
            )
            for bw in pr.band_consistency_warnings:
                lines.append(f"  - {bw}")
        lines.append("")
    return "\n".join(lines)


def report_to_json(rep: TemplateAuditReport) -> dict:
    return {
        "slug": rep.slug,
        "facing_pages": rep.facing_pages,
        "fatal_error": rep.fatal_error,
        "tolerance_suspicions": [
            {
                "constraint_id": ts.constraint_id,
                "constraint_name": ts.constraint_name,
                "tolerance_mm": ts.tolerance_mm,
                "gap_mm": ts.gap_mm,
                "targets": ts.targets,
                "message": ts.message,
            }
            for ts in rep.tolerance_suspicions
        ],
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
                        "geometric_alternative": sp.geometric_alternative,
                    }
                    for sp in pr.suspicious_pairs
                ],
                "spine_warnings": pr.spine_warnings,
                "image_extent_warnings": pr.image_extent_warnings,
                "band_consistency_warnings": pr.band_consistency_warnings,
            }
            for pr in rep.pages
        ],
    }


def _report_has_findings(rep: TemplateAuditReport) -> bool:
    """True if the report has any finding (suspicion / pair / spine /
    image / band)."""
    if rep.fatal_error:
        return True
    if rep.tolerance_suspicions:
        return True
    for pr in rep.pages:
        if (pr.suspicious_pairs or pr.spine_warnings
                or pr.image_extent_warnings
                or pr.band_consistency_warnings):
            return True
    return False


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
    ap.add_argument(
        "--axis-tol-mm", type=float,
        default=DEFAULTS["axis_tol_mm"],
        help=("Axis-alignment drift tolerance (mm). Default 25.0 matches "
              "brand:visual_adjacency_drift; was 5.0 pre-#23."),
    )
    ap.add_argument(
        "--adjacency-tol-mm", type=float,
        default=DEFAULTS["adjacency_tol_mm"],
        help="Adjacency gap tolerance (mm). Default 30.0; was 12.0 pre-#23.",
    )
    ap.add_argument(
        "--strict", action="store_true",
        help=("Exit 1 on any finding (tolerance-suspicion, "
              "suspicious-pair, spine-warning, image-extent-warning, or "
              "fatal_error). Used by Phase 3b verification gate "
              "(Issue #23) + image-fills-frame gate (Issue #24)."),
    )
    ap.add_argument(
        "--check-image-extent", dest="check_image_extent",
        action="store_true", default=True,
        help=("Run brand:image_fills_frame check (Issue #24, default on)."),
    )
    ap.add_argument(
        "--no-check-image-extent", dest="check_image_extent",
        action="store_false",
        help="Disable the brand:image_fills_frame check (Issue #24).",
    )
    ap.add_argument(
        "--check-brand-rules", dest="check_brand_rules",
        action="store_true", default=True,
        help="Run brand:band_consistency check (Issue #25, default on).",
    )
    ap.add_argument(
        "--no-check-brand-rules", dest="check_brand_rules",
        action="store_false",
        help="Disable the brand:band_consistency check (Issue #25).",
    )
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    ns = ap.parse_args(argv)
    if ns.all and ns.slug:
        ap.error("Pass either <slug> or --all, not both")
    if not ns.all and not ns.slug:
        ap.error("Pass either <slug> or --all")
    if ns.all:
        reps = audit_all(ns.root, check_image_extent=ns.check_image_extent,
                         check_brand_rules=ns.check_brand_rules)
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
        if ns.strict and any(_report_has_findings(r) for r in reps):
            return 1
        return 0
    rep = audit_template(
        ns.slug, ns.root,
        axis_tol_mm=ns.axis_tol_mm,
        adjacency_tol_mm=ns.adjacency_tol_mm,
        check_image_extent=ns.check_image_extent,
        check_brand_rules=ns.check_brand_rules,
    )
    if ns.json:
        print(json.dumps(report_to_json(rep), indent=2, ensure_ascii=False))
    elif ns.md:
        Path(ns.md).write_text(report_to_markdown(rep), encoding="utf-8")
    else:
        print(report_to_markdown(rep))
    if ns.strict and _report_has_findings(rep):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
