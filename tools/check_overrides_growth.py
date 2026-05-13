#!/usr/bin/env python3
"""Gate brand_overrides / non_ci_* growth against TOLERANCE_LOG / inject.yml.

Issue #38 P1 mechanism for "no silent tolerance growth". Issue #35 added
five brand_overrides silently masking real converter bugs; this hook
prevents recurrence.

Behaviour:
  1. For every templates/<slug>/meta.yml that differs between --base-ref
     and HEAD (or whose status is "added"), diff the four tolerance lists:
       - brand_overrides
       - non_ci_styles
       - non_ci_colors
       - non_ci_layers
  2. For each ADDED entry, require ONE of:
       (a) The same commit (HEAD-vs-base diff) added a row in
           templates/<slug>/TOLERANCE_LOG.md mentioning the entry id, OR
       (b) templates/<slug>/inject.yml has a hand_patches entry whose
           reason references the entry id (or the field being overridden).
  3. If neither, exit 1 with a clear error citing the file + missing
     justification.
  4. Removals are always permitted (no justification required).

Exit codes:
  0 — no growth, or all growth justified.
  1 — at least one ADDED entry lacks a TOLERANCE_LOG row or inject entry.
  2 — invocation error (missing git, etc.).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


_TOLERANCE_KEYS = (
    "brand_overrides",
    "non_ci_styles",
    "non_ci_colors",
    "non_ci_layers",
)


# ---------------------------------------------------------------------------
# Git helpers.
# ---------------------------------------------------------------------------


def _git_show(ref: str, path: str, repo_root: Path) -> str | None:
    """Return the contents of `path` at `ref`, or None if absent."""
    try:
        return subprocess.check_output(
            ["git", "show", f"{ref}:{path}"],
            cwd=str(repo_root),
            stderr=subprocess.PIPE,
        ).decode("utf-8")
    except subprocess.CalledProcessError:
        return None


def _list_changed_files(
    base_ref: str,
    repo_root: Path,
) -> list[str]:
    """Return repo-relative paths of templates/*/meta.yml that changed."""
    try:
        diff = subprocess.check_output(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=str(repo_root),
            stderr=subprocess.PIPE,
        ).decode("utf-8")
    except subprocess.CalledProcessError:
        # Fall back to a full scan if the diff fails.
        return [
            str(p.relative_to(repo_root))
            for p in (repo_root / "templates").rglob("meta.yml")
        ]
    return [
        line
        for line in diff.splitlines()
        if line.startswith("templates/") and line.endswith("/meta.yml")
    ]


# ---------------------------------------------------------------------------
# Tolerance-list normalisation.
# ---------------------------------------------------------------------------


def _entry_id(entry: Any) -> str | None:
    """Return the canonical id for a tolerance-list entry.

    Two shapes are tolerated:
      - {"id": "brand:line_spacing_0.9", "reason": "..."}
      - "brand:line_spacing_0.9"
    """
    if isinstance(entry, dict):
        for key in ("id", "name"):
            v = entry.get(key)
            if isinstance(v, str) and v:
                return v
        return None
    if isinstance(entry, str):
        return entry
    return None


def _tolerance_ids(meta_yaml_text: str | None) -> dict[str, set[str]]:
    """Parse meta.yml text and return {key: {entry_ids}} for each tolerance list.

    Missing or empty meta.yml => all four lists are empty sets.
    """
    out: dict[str, set[str]] = {key: set() for key in _TOLERANCE_KEYS}
    if not meta_yaml_text:
        return out
    try:
        data = yaml.safe_load(meta_yaml_text) or {}
    except yaml.YAMLError:
        return out
    if not isinstance(data, dict):
        return out
    for key in _TOLERANCE_KEYS:
        entries = data.get(key) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            eid = _entry_id(entry)
            if eid is not None:
                out[key].add(eid)
    return out


# ---------------------------------------------------------------------------
# Justification lookup.
# ---------------------------------------------------------------------------


def _tolerance_log_has(slug_dir: Path, entry_id: str) -> bool:
    """True if templates/<slug>/TOLERANCE_LOG.md contains the entry id."""
    log = slug_dir / "TOLERANCE_LOG.md"
    if not log.exists():
        return False
    try:
        text = log.read_text(encoding="utf-8")
    except OSError:
        return False
    return entry_id in text


def _inject_yml_references(slug_dir: Path, entry_id: str) -> bool:
    """True if inject.yml has a hand_patches entry whose reason references the id."""
    inject = slug_dir / "inject.yml"
    if not inject.exists():
        return False
    try:
        data = yaml.safe_load(inject.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return False
    if not isinstance(data, dict):
        return False
    patches = data.get("hand_patches") or []
    if not isinstance(patches, list):
        return False
    for patch in patches:
        if not isinstance(patch, dict):
            continue
        reason = patch.get("reason") or ""
        if not isinstance(reason, str) or len(reason.strip()) < 1:
            continue
        # Substring match: the reason text may quote the id directly OR
        # reference the field name the override touches (e.g. "ALIGN" for
        # brand:default_align, "LINESP" for brand:line_spacing).
        if entry_id in reason:
            return True
        # Field-name match: strip "brand:" / "non_ci_" prefix and check.
        bare = entry_id.split(":", 1)[-1].split(".", 1)[0]
        if bare and bare in reason:
            return True
    return False


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------


def check_growth(
    base_ref: str,
    repo_root: Path,
    *,
    changed_files: list[str] | None = None,
) -> list[tuple[str, str, str]]:
    """Return list of (template_slug, key, entry_id) for unjustified additions.

    Empty list means "no growth or all growth justified".
    """
    if changed_files is None:
        changed_files = _list_changed_files(base_ref, repo_root)
    violations: list[tuple[str, str, str]] = []
    for rel in changed_files:
        slug = rel.split("/")[1]
        slug_dir = repo_root / "templates" / slug
        base_text = _git_show(base_ref, rel, repo_root)
        head_path = repo_root / rel
        head_text = head_path.read_text(encoding="utf-8") if head_path.exists() else None
        base_ids = _tolerance_ids(base_text)
        head_ids = _tolerance_ids(head_text)
        for key in _TOLERANCE_KEYS:
            added = head_ids[key] - base_ids[key]
            for entry_id in sorted(added):
                if _tolerance_log_has(slug_dir, entry_id):
                    continue
                if _inject_yml_references(slug_dir, entry_id):
                    continue
                violations.append((slug, key, entry_id))
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_overrides_growth",
        description=(
            "Gate templates/<slug>/meta.yml tolerance-list growth against "
            "TOLERANCE_LOG.md rows and inject.yml entries. Run via "
            "pre-commit + CI per issue #38."
        ),
    )
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help="Git ref to diff against (default: origin/main).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repo root (default: parent of tools/).",
    )
    args = parser.parse_args(argv)
    try:
        violations = check_growth(args.base_ref, args.repo_root)
    except FileNotFoundError as exc:
        print(f"check_overrides_growth: {exc}", file=sys.stderr)
        return 2
    if not violations:
        return 0
    for slug, key, entry_id in violations:
        print(
            f"meta.yml::{key} added '{entry_id}' in templates/{slug}/ "
            f"without TOLERANCE_LOG.md row or inject.yml entry. "
            f"Add one explaining the rationale.",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
