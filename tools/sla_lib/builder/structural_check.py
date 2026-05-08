"""Structural-check orchestrator for templates (Issue #12, CONTEXT D3/D7/D11).

Imports each template's ``build_doc()`` (D13 contract), walks the
emitted primitives, and evaluates:

  - the template's optional module-level ``CONSTRAINTS`` list (free-form
    constraints from ``constraints.py``); orphan-anname references
    yield warnings (RESEARCH §10, never silent skip)
  - the global ``BRAND_CONSTRAINTS`` list, minus rule IDs listed in the
    template's ``meta.yml::brand_overrides`` (those are SKIP'd with the
    documented reason)

Outputs a markdown report (or JSON via ``--json``). Exit code 1 if any
error-severity issue surfaces; warnings alone never fail CI.

CLI:

    python3 -m sla_lib.builder.structural_check <slug>
    python3 -m sla_lib.builder.structural_check --all
    python3 -m sla_lib.builder.structural_check --all --json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

# When run as a script (`python3 -m sla_lib.builder.structural_check`),
# ensure the workspace's tools/ is on sys.path so `templates.<slug>.build`
# can import sla_lib.
_TOOLS_ROOT = Path(__file__).resolve().parents[2]
if str(_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TOOLS_ROOT))

_REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass
class CheckIssue:
    severity: str        # "error" | "warning" | "info" | "pass" | "skip"
    rule_id: str
    message: str
    location: str = ""


@dataclass
class TemplateReport:
    slug: str
    constraint_issues: list[CheckIssue] = field(default_factory=list)
    brand_issues: list[CheckIssue] = field(default_factory=list)
    skipped_brand_rules: list[tuple[str, str]] = field(default_factory=list)
    # passes recorded as severity="pass" in the issue lists for reporting
    fatal_error: Optional[str] = None  # build_doc import failure etc.

    @property
    def has_errors(self) -> bool:
        if self.fatal_error:
            return True
        for i in self.constraint_issues + self.brand_issues:
            if i.severity == "error":
                return True
        return False

    def to_markdown(self) -> str:
        lines = [f"## templates/{self.slug}"]
        if self.fatal_error:
            lines.append(f"FATAL: {self.fatal_error}")
            return "\n".join(lines)
        lines.append("### CONSTRAINTS")
        if not self.constraint_issues:
            lines.append("- (no CONSTRAINTS list, or empty)")
        for i in self.constraint_issues:
            lines.append(f"- {i.severity.upper()} {i.rule_id}: {i.message}")
        lines.append("### BRAND_CONSTRAINTS")
        for rid, reason in self.skipped_brand_rules:
            lines.append(f"- SKIP {rid} (overridden in meta.yml: {reason})")
        for i in self.brand_issues:
            lines.append(f"- {i.severity.upper()} {i.rule_id}: {i.message}")
        if not self.skipped_brand_rules and not self.brand_issues:
            lines.append("- (no brand-rule output)")
        n_err = sum(1 for i in self.constraint_issues + self.brand_issues
                    if i.severity == "error")
        n_warn = sum(1 for i in self.constraint_issues + self.brand_issues
                     if i.severity == "warning")
        n_pass = sum(1 for i in self.constraint_issues + self.brand_issues
                     if i.severity == "pass")
        lines.append(
            f"\nResult: {n_err} errors, {n_warn} warnings, "
            f"{len(self.skipped_brand_rules)} skipped, {n_pass} passes"
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Template loader
# ---------------------------------------------------------------------------
def _load_build_module(slug: str, root: Path = _REPO_ROOT):
    """Load templates/<slug>/build.py via importlib (with full package path).

    We use importlib.util.spec_from_file_location with a unique module
    name to avoid sys.modules cross-contamination when --all iterates.
    """
    p = root / "templates" / slug / "build.py"
    if not p.exists():
        raise FileNotFoundError(f"template build.py not found: {p}")
    mod_name = f"_strcheck_template_{slug.replace('-', '_')}"
    # Drop any cached module so re-imports always re-evaluate.
    sys.modules.pop(mod_name, None)
    spec = importlib.util.spec_from_file_location(mod_name, p)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"cannot create import spec for {p}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _violation_to_issue(v, default_rule_id: str) -> CheckIssue:
    return CheckIssue(
        severity=v.severity,
        rule_id=v.rule_id or default_rule_id,
        message=v.message,
        location=",".join(v.targets) if v.targets else "",
    )


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------
def check_template(slug: str, root: Path = _REPO_ROOT) -> TemplateReport:
    """Run structural + brand checks for one template slug."""
    rep = TemplateReport(slug=slug)
    try:
        mod = _load_build_module(slug, root)
    except Exception as e:
        rep.fatal_error = f"failed to import template build.py: {e}"
        return rep
    if not hasattr(mod, "build_doc"):
        rep.fatal_error = (
            f"template {slug} build.py does not expose build_doc() "
            "(see CONTEXT D13)"
        )
        return rep
    try:
        doc = mod.build_doc()
    except Exception as e:
        rep.fatal_error = f"build_doc() raised: {e!r}"
        return rep
    primitives = list(doc.iter_all_primitives())
    primitives_by_anname = {
        getattr(p, "anname", ""): p for p in primitives
        if getattr(p, "anname", "")
    }

    # CONSTRAINTS evaluation
    constraint_list = getattr(mod, "CONSTRAINTS", []) or []
    for c in constraint_list:
        ref = set(c.referenced_annames())
        present = set(primitives_by_anname)
        missing = ref - present
        if missing:
            rep.constraint_issues.append(CheckIssue(
                severity="warning",
                rule_id=c.id,
                message=f"references missing anname(s): {sorted(missing)}",
                location=",".join(sorted(missing)),
            ))
            continue
        violations = c.check(primitives_by_anname)
        if not violations:
            rep.constraint_issues.append(CheckIssue(
                severity="pass", rule_id=c.id, message="ok",
            ))
        else:
            for v in violations:
                rep.constraint_issues.append(_violation_to_issue(v, c.id))

    # BRAND_CONSTRAINTS evaluation, with override skip list
    from .brand_constraints import BRAND_CONSTRAINTS
    from .meta_schema import load_brand_overrides
    try:
        skip_ids = load_brand_overrides(slug, root)
    except ValueError as e:
        rep.fatal_error = f"meta.yml validation failed: {e}"
        return rep
    # Map rule_id -> reason (for the markdown output)
    overrides_with_reason: dict[str, str] = {}
    meta_p = root / "templates" / slug / "meta.yml"
    if meta_p.exists():
        import yaml
        data = yaml.safe_load(meta_p.read_text(encoding="utf-8")) or {}
        for entry in data.get("brand_overrides", []) or []:
            overrides_with_reason[entry["id"]] = entry.get("reason", "")

    for rule in BRAND_CONSTRAINTS:
        if rule.id in skip_ids:
            rep.skipped_brand_rules.append(
                (rule.id, overrides_with_reason.get(rule.id, ""))
            )
            continue
        try:
            violations = rule.check(primitives, doc)
        except Exception as e:
            rep.brand_issues.append(CheckIssue(
                severity="error", rule_id=rule.id,
                message=f"rule check raised: {e!r}",
            ))
            continue
        if not violations:
            rep.brand_issues.append(CheckIssue(
                severity="pass", rule_id=rule.id, message="ok",
            ))
        else:
            for v in violations:
                rep.brand_issues.append(_violation_to_issue(v, rule.id))
    return rep


# ---------------------------------------------------------------------------
# Discovery for --all
# ---------------------------------------------------------------------------
_EXCLUDED_DIRS = {"_specs", "_smoke"}


def discover_template_slugs(root: Path = _REPO_ROOT) -> list[str]:
    out: list[str] = []
    tdir = root / "templates"
    if not tdir.exists():
        return out
    for child in sorted(tdir.iterdir()):
        if not child.is_dir():
            continue
        if child.name in _EXCLUDED_DIRS:
            continue
        if not (child / "build.py").exists():
            continue
        out.append(child.name)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _report_to_dict(rep: TemplateReport) -> dict:
    def issue_dict(i: CheckIssue) -> dict:
        return {
            "severity": i.severity,
            "rule_id": i.rule_id,
            "message": i.message,
            "location": i.location,
        }

    return {
        "slug": rep.slug,
        "fatal_error": rep.fatal_error,
        "constraint_issues": [issue_dict(i) for i in rep.constraint_issues],
        "brand_issues": [issue_dict(i) for i in rep.brand_issues],
        "skipped_brand_rules": [
            {"id": rid, "reason": reason}
            for rid, reason in rep.skipped_brand_rules
        ],
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sla_lib.builder.structural_check",
        description=(
            "Structural + brand-CI check for one or more templates. "
            "Reads build_doc() (CONTEXT D13), evaluates CONSTRAINTS list "
            "and BRAND_CONSTRAINTS, honours meta.yml::brand_overrides."
        ),
    )
    parser.add_argument("slug", nargs="?",
                        help="Template slug under templates/<slug>/")
    parser.add_argument("--all", action="store_true",
                        help="Run on every template under templates/ "
                             "(excluding _specs and _smoke)")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON report to stdout")
    parser.add_argument("--root", type=Path, default=_REPO_ROOT,
                        help="Repo root (defaults to detected workspace)")
    args = parser.parse_args(argv)

    if args.all and args.slug:
        parser.error("Pass either <slug> or --all, not both")
    if not args.all and not args.slug:
        parser.error("Pass either <slug> or --all")

    if args.all:
        slugs = discover_template_slugs(args.root)
    else:
        slugs = [args.slug]

    reports = [check_template(s, args.root) for s in slugs]

    if args.json:
        print(json.dumps([_report_to_dict(r) for r in reports], indent=2))
    else:
        print("# structural_check report\n")
        for r in reports:
            print(r.to_markdown())
            print()

    return 1 if any(r.has_errors for r in reports) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
