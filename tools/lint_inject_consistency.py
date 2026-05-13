#!/usr/bin/env python3
r"""Lint the 1:1 mapping between # P5/inject inline comments in
templates/*/build.py and entries in templates/*/inject.yml.

Issue #38 Task 18: CI gate that prevents drift between the declarative
inject.yml and the inline P5/inject comments after a reconcile step.

The convention (per tools/reconcile_build_py.py) is that the reconciler
inserts inline comments of the form:

    # P5/inject (from inject.yml line N): <reason>

Three valid states are recognised:

  A. No inject.yml AND no inline # P5/inject (from ...) comments in
     build.py => CONSISTENT (no inject mechanism in use).
  B. inject.yml present AND no inline comments in build.py => CONSISTENT
     (the inject.yml is the canonical declarative record; build.py has
     not been re-reconciled yet OR the template uses inject.yml as
     documentation-only and the converter emits the patched build.py
     directly).
  C. inject.yml present AND inline comments in build.py => STRICT:
     every comment must map to an inject.yml entry at the named line
     AND every inject.yml entry must produce a matching comment.

CLI:
    python3 tools/lint_inject_consistency.py [--template SLUG]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
COMMENT_PATTERN = re.compile(
    r"#\s*P5/inject\s*\(from\s+inject\.yml\s+line\s+(\d+)\)\s*:"
)


def _collect_comment_lines(build_py: Path) -> set[int]:
    """Return the set of inject.yml line numbers cited by build.py comments."""
    out: set[int] = set()
    if not build_py.exists():
        return out
    for line in build_py.read_text(encoding="utf-8").splitlines():
        m = COMMENT_PATTERN.search(line)
        if m:
            out.add(int(m.group(1)))
    return out


def _collect_inject_entry_lines(inject_yml: Path) -> set[int]:
    r"""Return the set of 1-indexed line numbers where hand_patches entries start.

    A 'hand_patches' entry begins with a line matching ``^\s*-\s+target\s*:``
    or ``^\s*-\s*\{?\s*target\b``.
    """
    if not inject_yml.exists():
        return set()
    lines = inject_yml.read_text(encoding="utf-8").splitlines()
    out: set[int] = set()
    for i, ln in enumerate(lines, 1):
        if re.match(r"^\s*-\s+target\s*:", ln) or re.match(
            r"^\s*-\s*\{?\s*target\b", ln
        ):
            out.add(i)
    return out


def _validate_inject_yml_schema(inject_yml: Path) -> list[str]:
    """Return list of validation errors. Empty means valid."""
    if not inject_yml.exists():
        return []
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema package required for full validation"]
    schema_path = ROOT / "shared" / "inject.schema.yaml"
    if not schema_path.exists():
        return []
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    try:
        data = yaml.safe_load(inject_yml.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return [f"YAML parse error: {exc}"]
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'/'.join(str(p) for p in err.absolute_path)}: {err.message}"
        for err in validator.iter_errors(data)
    ]


def check_template(slug: str, repo_root: Path) -> list[str]:
    """Return list of error strings for the given template. Empty means clean."""
    tdir = repo_root / "templates" / slug
    build_py = tdir / "build.py"
    inject_yml = tdir / "inject.yml"

    has_inject = inject_yml.exists()
    has_comments = bool(_collect_comment_lines(build_py))

    if not has_inject and not has_comments:
        return []  # template doesn't use the inject mechanism at all

    errors: list[str] = []

    # Schema validation.
    schema_errors = _validate_inject_yml_schema(inject_yml)
    for err in schema_errors:
        errors.append(f"templates/{slug}/inject.yml schema: {err}")

    comment_lines = _collect_comment_lines(build_py)
    entry_lines = _collect_inject_entry_lines(inject_yml)

    # Strict 1:1 mapping is enforced ONLY when build.py has at least one
    # inline P5/inject comment (state C in the module docstring). When
    # build.py has no comments and inject.yml exists, state B applies:
    # the inject.yml is the canonical record; reconcile has not been
    # applied yet (or the template uses inject.yml as documentation only).
    if not comment_lines:
        return errors  # state B — declarative-only, no inline comments

    # State C: every comment must have a matching inject.yml entry.
    for line_n in sorted(comment_lines - entry_lines):
        errors.append(
            f"templates/{slug}/build.py cites '# P5/inject (from inject.yml "
            f"line {line_n})' but inject.yml has no entry at that line"
        )
    # State C: every inject.yml entry must produce a comment.
    for line_n in sorted(entry_lines - comment_lines):
        errors.append(
            f"templates/{slug}/inject.yml has hand_patch at line {line_n} "
            f"but build.py has no matching '# P5/inject (from inject.yml "
            f"line {line_n})' comment"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lint_inject_consistency",
        description=(
            "Enforce 1:1 mapping between # P5/inject inline comments in "
            "build.py and hand_patches entries in inject.yml."
        ),
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Limit check to a single template slug.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="Repo root (for tests).",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root
    templates_dir = repo_root / "templates"
    if args.template:
        slugs = [args.template]
    else:
        slugs = sorted(
            d.name for d in templates_dir.iterdir() if d.is_dir()
        ) if templates_dir.exists() else []
    all_errors: list[str] = []
    for slug in slugs:
        all_errors.extend(check_template(slug, repo_root))
    if all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
