#!/usr/bin/env python3
"""bin/idml-import driver — one-command end-to-end IDML to template pipeline.

Drives the full convergence loop:

  1. Verify required tools (pdftocairo, pdffonts, convert, scribus).
  2. Slugify the IDML filename to a template id.
  3. Refuse to overwrite an existing templates/<slug>/ without --reimport.
  4. Brand-fonts gate (bypassable with --no-brand-fonts; loud warning).
  5. Resolve baseline.pdf (sibling <stem>.pdf or --keep-baseline-from-pdf).
  6. Extract Links/ via tools/links_export.py.
  7. Run asset_extraction_audit; abort if not ok and not --allow-composite-ai.
  8. Scaffold templates/<slug>/{meta.yml,diff.yml,baseline.pdf}.
  9. Run tools/idml_to_dsl.py to emit templates/<slug>/build.py.
 10. With --scaffold-only, halt cleanly after the first audit cycle.
 11. Convergence loop: render-gallery + convergence-review +
     iteration.jsonl log + regression guard. Up to --max-iterations.
 12. Emit build/<slug>/import_report.md final summary.

Exit codes (per RESEARCH.md):
  0 — preflight.ok=true OR all-residual-accepted.
  1 — converter / asset / unknown failure (run aborted).
  2 — needs human review (NEEDS_REVIEW with unaccepted residual).
  3 — drift regression detected / max-iterations exceeded.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Module discovery — works whether installed or invoked directly.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------
REQUIRED_TOOLS: tuple[tuple[str, str], ...] = (
    ("pdftocairo", "Install poppler-utils (apt: poppler-utils, brew: poppler)."),
    ("pdffonts", "Install poppler-utils (apt: poppler-utils, brew: poppler)."),
    ("convert", "Install ImageMagick (apt: imagemagick, brew: imagemagick)."),
    ("scribus", "Install Scribus 1.6.x (apt: scribus, brew: scribus)."),
)


_HUMAN_REVIEW_CLASSIFICATIONS = frozenset({"human-review", "authoring-bug"})


# ---------------------------------------------------------------------------
# Pre-flight checks.
# ---------------------------------------------------------------------------


def _check_tool_availability(tools: tuple[tuple[str, str], ...] = REQUIRED_TOOLS) -> list[str]:
    """Return a list of missing tools (name + hint per entry)."""
    missing: list[str] = []
    for name, hint in tools:
        if shutil.which(name) is None:
            missing.append(f"{name}: not found on PATH. {hint}")
    return missing


def _verify_brand_fonts() -> bool:
    """Bridge to render_pipeline._verify_brand_fonts. Returns True on success."""
    try:
        from render_pipeline import _verify_brand_fonts as rp_verify
    except ImportError:
        return False
    try:
        rp_verify()
        return True
    except SystemExit:
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Iteration log (Task 6).
# ---------------------------------------------------------------------------


def log_iteration(
    slug: str,
    iteration: int,
    review: dict,
    changes: list[str],
    *,
    build_root: Path | None = None,
) -> dict:
    """Append one row to build/<slug>/iteration.jsonl. Returns the row."""
    if build_root is None:
        build_root = ROOT / "build"
    target_dir = build_root / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    issues = [
        i for i in (review.get("issues") or [])
        if i.get("classification") != "minor"
    ]
    drift = review.get("drift") or {}
    row = {
        "iteration": int(iteration),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "preflight_ok": bool(review.get("preflight_ok", False)),
        "issues_open": len(issues),
        "drift_p1": drift.get("p1"),
        "drift_p2": drift.get("p2"),
        "drift_p1_max_region": drift.get("p1_max_region"),
        "drift_p2_max_region": drift.get("p2_max_region"),
        "changes": list(changes),
        "audits_run": list(review.get("audits_run") or []),
        "rules_seen": int(iteration),
        "_schema_version": 1,
    }
    line = json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n"
    (target_dir / "iteration.jsonl").open("a", encoding="utf-8").write(line)
    return row


def regression_guard(
    slug: str,
    current_row: dict,
    *,
    build_root: Path | None = None,
) -> str | None:
    """Compare current_row against the penultimate row in iteration.jsonl.

    Returns an error string if BOTH page-wide drift_p1 AND drift_p1_max_region
    regressed (per RESEARCH.md 8.1); otherwise None.
    """
    if build_root is None:
        build_root = ROOT / "build"
    log_path = build_root / slug / "iteration.jsonl"
    if not log_path.exists():
        return None
    lines = log_path.read_text(encoding="utf-8").splitlines()
    # The current row is the LAST line; the prior row is the second-to-last.
    if len(lines) < 2:
        return None
    try:
        prev = json.loads(lines[-2])
    except json.JSONDecodeError:
        return None
    cur_p1 = current_row.get("drift_p1")
    prev_p1 = prev.get("drift_p1")
    cur_max = current_row.get("drift_p1_max_region")
    prev_max = prev.get("drift_p1_max_region")
    if cur_p1 is None or prev_p1 is None:
        return None
    if cur_p1 <= prev_p1 + 0.05:
        return None
    # Page-wide regressed; only halt if per-region max ALSO regressed.
    if cur_max is None or prev_max is None or cur_max <= prev_max:
        return None
    # Filter out new-audit-added situations: if the set of audits expanded,
    # the issue-count delta may legitimately come from the new audit.
    cur_audits = set(current_row.get("audits_run") or [])
    prev_audits = set(prev.get("audits_run") or [])
    if cur_audits - prev_audits:
        return None
    return (
        f"drift regression: p1 went from {prev_p1} to {cur_p1} "
        f"(p1_max_region {prev_max} -> {cur_max})"
    )


# ---------------------------------------------------------------------------
# Scaffolding.
# ---------------------------------------------------------------------------


def _scaffold_template_dir(
    slug: str,
    baseline_src: Path,
    tdir: Path,
) -> None:
    """Create templates/<slug>/{meta.yml, diff.yml, baseline.pdf}."""
    tdir.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": slug,
        "version": "0.1.0",
        "title": slug,
        "format": "A4",
        "build": {"script": "build.py", "output": "template.sla"},
    }
    (tdir / "meta.yml").write_text(
        yaml.safe_dump(meta, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    diff = {"dpi": 300, "fuzz_pct": 2.0}
    (tdir / "diff.yml").write_text(
        yaml.safe_dump(diff, sort_keys=True),
        encoding="utf-8",
    )
    shutil.copy(baseline_src, tdir / "baseline.pdf")


def _run_converter(
    slug: str,
    idml_path: Path,
    asset_map: Path,
    out_path: Path,
) -> int:
    """Invoke tools/idml_to_dsl.py. Returns exit code."""
    cmd = [
        sys.executable,
        str(_HERE / "idml_to_dsl.py"),
        str(idml_path),
        str(out_path),
        "--template-id",
        slug,
        "--asset-map",
        str(asset_map),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


# ---------------------------------------------------------------------------
# Convergence loop helpers.
# ---------------------------------------------------------------------------


def _run_render_gallery(slug: str, *, no_brand_fonts: bool = False) -> int:
    """Invoke bin/render-gallery <slug> --audit-strict."""
    cmd = [
        sys.executable,
        str(_HERE / "render_pipeline.py"),
        slug,
        "--audit-strict",
    ]
    if no_brand_fonts:
        # render_pipeline does not yet expose a --no-brand-fonts CLI flag;
        # we propagate the intent via env var which render_pipeline's
        # _verify_brand_fonts can opt into via a follow-up extension.
        os.environ.setdefault("AUSTENDER_NO_BRAND_FONTS", "1")
    result = subprocess.run(cmd)
    return result.returncode


def _run_convergence_review(slug: str) -> dict | None:
    """Invoke bin/convergence-review and parse JSON output. Returns None on failure."""
    cmd = [
        sys.executable,
        str(_HERE / "convergence_review.py"),
        slug,
        "--format",
        "json",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return None
    if result.returncode not in (0, 1, 2):
        # Genuine error (not "review reports issues"); surface stderr.
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return None
    try:
        return json.loads(result.stdout) if result.stdout else None
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Final report.
# ---------------------------------------------------------------------------


def _verdict(review: dict | None, residual_accepted: bool) -> str:
    if review is None:
        return "BLOCKED"
    if review.get("preflight_ok"):
        return "PASS"
    if residual_accepted:
        return "PASS"
    # Else inspect classifications.
    issues = review.get("issues") or []
    open_issues = [i for i in issues if i.get("classification") != "minor"]
    if not open_issues:
        return "PASS"
    if all(
        i.get("classification") == "authoring-bug" for i in open_issues
    ):
        return "BLOCKED_BY_AUTHORING"
    return "NEEDS_REVIEW"


def _write_import_report(
    slug: str,
    verdict: str,
    review: dict | None,
    iteration_count: int,
    build_root: Path | None = None,
) -> Path:
    if build_root is None:
        build_root = ROOT / "build"
    target_dir = build_root / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    report = target_dir / "import_report.md"
    lines: list[str] = [
        f"# IDML Import Report — {slug}",
        "",
        f"**Verdict:** {verdict}",
        f"**Iterations:** {iteration_count}",
        "",
    ]
    if review is None:
        lines.append("(no convergence-review output captured)")
    else:
        issues = review.get("issues") or []
        open_issues = [i for i in issues if i.get("classification") != "minor"]
        lines.append(f"**Open issues:** {len(open_issues)}")
        if open_issues:
            lines.append("")
            lines.append("## Issues")
            for i in open_issues:
                lines.append(
                    f"- **{i.get('classification', '?')}** — "
                    f"{i.get('slot', '?')} "
                    f"({i.get('audit', '?')}): "
                    f"{i.get('suggested_action', '')}"
                )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


# ---------------------------------------------------------------------------
# Slugify.
# ---------------------------------------------------------------------------


def _slugify(idml_path: Path) -> str:
    from links_export import slugify_stem
    return slugify_stem(idml_path.stem)


# ---------------------------------------------------------------------------
# Driver entry point.
# ---------------------------------------------------------------------------


def _expand_paths(paths: list[str]) -> list[Path]:
    """Expand directory arguments to all *.idml underneath."""
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(p.rglob("*.idml")))
        else:
            out.append(p)
    return out


def _process_one(
    idml_path: Path,
    args: argparse.Namespace,
    *,
    build_root: Path | None = None,
    templates_root: Path | None = None,
    assets_root: Path | None = None,
) -> int:
    if build_root is None:
        build_root = ROOT / "build"
    if templates_root is None:
        templates_root = ROOT / "templates"
    if assets_root is None:
        assets_root = ROOT / "shared" / "assets"

    if not idml_path.exists():
        print(
            f"idml-import: IDML not found: {idml_path}", file=sys.stderr
        )
        return 1
    # 1. Tool availability.
    missing = _check_tool_availability()
    if missing:
        for m in missing:
            print(f"idml-import: {m}", file=sys.stderr)
        return 1

    # 2. Slugify.
    slug = _slugify(idml_path)

    # 3. Existing-template detection.
    tdir = templates_root / slug
    if tdir.exists() and not args.reimport:
        print(
            f"idml-import: templates/{slug}/ exists; use --reimport, "
            f"or rename, or remove first",
            file=sys.stderr,
        )
        return 1

    # 4. Brand-fonts gate.
    if not args.no_brand_fonts:
        if not _verify_brand_fonts():
            print(
                "idml-import: brand fonts not available; install gruene fonts "
                "or pass --no-brand-fonts (WARNING: degraded font fidelity).",
                file=sys.stderr,
            )
            return 1
    else:
        print(
            "idml-import: WARNING — --no-brand-fonts is set; font fidelity "
            "checks will be degraded.",
            file=sys.stderr,
        )

    # 5. Baseline resolution.
    if args.keep_baseline_from_pdf is not None:
        baseline = args.keep_baseline_from_pdf
    else:
        baseline = idml_path.with_suffix(".pdf")
    if not baseline.exists():
        print(
            f"idml-import: baseline.pdf not found at {baseline}; "
            f"pass --keep-baseline-from-pdf <path> to override.",
            file=sys.stderr,
        )
        return 1

    # 6. Asset extraction (with audit hook).
    links_dir = idml_path.parent / "Links"
    out_assets = assets_root / slug
    try:
        from links_export import export as run_export
        export_result = run_export(links_dir, out_assets, quiet=True)
        manifest_path = export_result.manifest_path
    except FileNotFoundError as exc:
        print(f"idml-import: asset extraction failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"idml-import: asset extraction error: {exc}", file=sys.stderr)
        return 1

    # 7. Asset-extraction audit.
    from asset_extraction_audit import audit as run_asset_audit
    asset_report = run_asset_audit(
        slug=slug,
        idml_path=idml_path,
        links_export_yml=manifest_path,
        repo_root=ROOT,
        allow_composite_ai=args.allow_composite_ai,
    )
    if not asset_report["ok"]:
        print(
            "idml-import: asset extraction audit failed; see "
            f"build/validation/{slug}/asset_audit.yml. "
            f"Pass --allow-composite-ai to bypass composite-AI checks.",
            file=sys.stderr,
        )
        return 1

    # 7.5. Asset-policy audit (issue #39 Phase B). Hard-fails on
    # shipped:-non-empty, missing-policy-when-assets-on-disk, or
    # coverage drift. Silent-skip when no shared/assets/<slug>/ exists.
    try:
        from asset_policy_audit import run_asset_policy_audit
        policy_report = run_asset_policy_audit(slug, root=ROOT)
    except ValueError as exc:
        print(
            f"idml-import: asset_policy schema error: {exc}", file=sys.stderr
        )
        return 1
    if not policy_report.get("ok") and not policy_report.get("skipped"):
        print(
            f"idml-import: asset_policy_audit FAILED "
            f"({policy_report.get('issue')}): {policy_report.get('message', '')}",
            file=sys.stderr,
        )
        return 1

    # 8. Scaffold.
    _scaffold_template_dir(slug, baseline, tdir)

    # 9. Convert.
    build_py = tdir / "build.py"
    rc = _run_converter(slug, idml_path, manifest_path, build_py)
    if rc != 0:
        print(
            f"idml-import: converter exited {rc}; see stderr above.",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        print(f"idml-import: dry-run complete — scaffold + convert OK for {slug}.")
        return 0

    # Convergence loop.
    iteration = 0
    last_review: dict | None = None
    residual_accepted = False
    max_iter = args.max_iterations if args.max_iterations > 0 else 10

    if args.scaffold_only:
        # Run one audit cycle to produce baseline reports, then halt.
        _run_render_gallery(slug, no_brand_fonts=args.no_brand_fonts)
        # Emit templates/<slug>/SCAFFOLD_INVENTORY.yml between render-gallery
        # and convergence-review so the inventory captures the just-rendered
        # SLA + preview.pdf. Failure here is logged but NEVER fails the
        # scaffold — Stage 2 (idml-tune) is where the inventory becomes a
        # hard gate.
        if not args.no_inventory:
            try:
                from tools import inventory_extract as _ie
                inv = _ie.build_inventory(slug)
                inv_yaml = _ie.to_yaml(inv)
                inv_path = ROOT / "templates" / slug / "SCAFFOLD_INVENTORY.yml"
                inv_path.write_text(inv_yaml, encoding="utf-8")
                print(f"idml-import: wrote {inv_path}", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001 — informational tool
                print(
                    f"idml-import: SCAFFOLD_INVENTORY emission failed "
                    f"(non-fatal): {exc}",
                    file=sys.stderr,
                )
        review = _run_convergence_review(slug)
        iteration += 1
        last_review = review
        if review is not None:
            log_iteration(slug, iteration, review, changes=["scaffold-only"],
                          build_root=build_root)
        verdict = _verdict(review, residual_accepted=False)
        _write_import_report(slug, verdict, review, iteration, build_root=build_root)
        return 0

    while iteration < max_iter:
        iteration += 1
        rc_render = _run_render_gallery(
            slug, no_brand_fonts=args.no_brand_fonts
        )
        # Render-gallery exit code 0/non-zero — we record the review either way.
        review = _run_convergence_review(slug)
        last_review = review
        if review is None:
            print(
                "idml-import: convergence-review returned no output; "
                "aborting loop.",
                file=sys.stderr,
            )
            break
        row = log_iteration(
            slug,
            iteration,
            review,
            changes=[],
            build_root=build_root,
        )
        regression = regression_guard(slug, row, build_root=build_root)
        if regression is not None:
            print(f"idml-import: {regression}", file=sys.stderr)
            _write_import_report(slug, "BLOCKED", review, iteration,
                                 build_root=build_root)
            return 3

        if review.get("preflight_ok"):
            _write_import_report(slug, "PASS", review, iteration,
                                 build_root=build_root)
            return 0

        # Compute actionable issues.
        accept_set = set(args.accept_residual or [])
        wildcard = "*" in accept_set
        issues = review.get("issues") or []
        open_issues = [
            i for i in issues if i.get("classification") != "minor"
        ]
        actionable: list[dict] = []
        for i in open_issues:
            cls = i.get("classification")
            iid = str(i.get("id", ""))
            if wildcard:
                continue
            if cls in _HUMAN_REVIEW_CLASSIFICATIONS and iid in accept_set:
                continue
            actionable.append(i)
        if not actionable:
            residual_accepted = True
            _write_import_report(slug, "PASS", review, iteration,
                                 build_root=build_root)
            return 0
        # Surface actionable converter/engine bugs and halt for human triage.
        if args.non_interactive:
            verdict = _verdict(review, residual_accepted=False)
            _write_import_report(slug, verdict, review, iteration,
                                 build_root=build_root)
            return 2 if verdict == "NEEDS_REVIEW" else 1
        # Interactive — print the actionable list and stop (the driver does
        # not auto-fix converter bugs; the user is expected to extend the
        # converter and re-run --reimport).
        print(
            f"idml-import: iteration {iteration} surfaced "
            f"{len(actionable)} actionable issue(s):",
            file=sys.stderr,
        )
        for i in actionable:
            print(
                f"  - [{i.get('classification')}] {i.get('slot', '?')} — "
                f"{i.get('suggested_action', '')}",
                file=sys.stderr,
            )
        verdict = _verdict(review, residual_accepted=False)
        _write_import_report(slug, verdict, review, iteration,
                             build_root=build_root)
        return 2 if verdict == "NEEDS_REVIEW" else 1

    # Max iterations exhausted.
    verdict = _verdict(last_review, residual_accepted=residual_accepted)
    _write_import_report(slug, verdict, last_review, iteration,
                         build_root=build_root)
    return 3


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="idml-import",
        description=(
            "One-command IDML to template pipeline. Extracts assets, scaffolds "
            "templates/<slug>/, converts IDML to build.py, runs the audit "
            "convergence loop, and emits import_report.md."
        ),
    )
    parser.add_argument(
        "path",
        nargs="+",
        help=(
            "Path to an .idml file, or a directory containing .idml files. "
            "Directory arguments are walked recursively."
        ),
    )
    parser.add_argument(
        "--accept-residual",
        action="append",
        default=[],
        help=(
            "Accept residual issue id(s) classified as human-review or "
            "authoring-bug. Pass multiple times or use '*' to accept all "
            "non-actionable residuals."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Halt after scaffold + convert; skip the convergence loop.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum convergence iterations (default: 10).",
    )
    parser.add_argument(
        "--keep-baseline-from-pdf",
        type=Path,
        default=None,
        help=(
            "Override the auto-derived sibling .pdf with the given path "
            "(used when the baseline.pdf and IDML live in different folders)."
        ),
    )
    parser.add_argument(
        "--scaffold-only",
        action="store_true",
        help=(
            "Run scaffold + convert + ONE audit cycle, then halt. Useful for "
            "establishing a baseline before iterating."
        ),
    )
    parser.add_argument(
        "--reimport",
        action="store_true",
        help="Overwrite an existing templates/<slug>/ directory.",
    )
    parser.add_argument(
        "--no-brand-fonts",
        action="store_true",
        help=(
            "Skip the brand-fonts pre-flight gate. WARNING: font fidelity "
            "checks downstream will be degraded."
        ),
    )
    parser.add_argument(
        "--allow-composite-ai",
        action="store_true",
        help=(
            "Downgrade asset_extraction_audit composite-AI findings to "
            "warnings. Issue #38 Task 14 introduces a per-page splitter; "
            "this flag is the interim bypass for templates that haven't "
            "had the splitter applied yet."
        ),
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt; exit 2 on NEEDS_REVIEW with unaccepted residual.",
    )
    parser.add_argument(
        "--no-inventory",
        action="store_true",
        help=(
            "Skip the SCAFFOLD_INVENTORY.yml emission step in --scaffold-only. "
            "Use to debug the scaffold path without depending on the inventory "
            "walkers."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    paths = _expand_paths(args.path)
    if not paths:
        print("idml-import: no .idml inputs found.", file=sys.stderr)
        return 1
    worst_exit = 0
    for p in paths:
        rc = _process_one(p, args)
        # Track the most severe exit (1 > 3 > 2 > 0 in remediation terms,
        # but for the driver we propagate the highest numeric — that surfaces
        # the strictest gate first).
        if rc > worst_exit:
            worst_exit = rc
    return worst_exit


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
