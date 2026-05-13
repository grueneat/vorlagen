#!/usr/bin/env python3
"""Asset-policy audit (issue #39 Phase B).

Cross-checks ``templates/<slug>/meta.yml::asset_policy`` against the actual
files on disk at ``shared/assets/<slug>/`` (with a dual-lookup fallback to
``shared/assets/<idml-stem-slug>/`` for historical templates whose asset
directory was named after the source IDML rather than the template slug).

Sibling of ``tools/asset_extraction_audit.py`` — different inputs, different
failure semantics, different invocation timing. Per RESEARCH.md §7 the two
audits stay independent.

Hard-fail conditions (returns ``ok=False`` with ``issue`` set):

  * ``shipped_non_empty`` — the ``shipped:`` list contains entries.
    First-PR rule (issue #39): every asset goes in ``embedded:``; the
    brand-team has not yet decided on the zip flow that ``shipped:`` would
    drive. Schema (``shared/asset-policy.schema.yaml``) intentionally stays
    permissive; only this audit rejects.
  * ``missing`` — the asset directory exists but ``meta.yml::asset_policy``
    is absent (templates with assets MUST declare a policy).
  * ``coverage`` — basenames on disk differ from ``embedded:``:
      - ``unclassified`` files (on disk, not in ``embedded:``).
      - ``stale`` entries (in ``embedded:``, not on disk).

Silent skip (returns ``ok=True, skipped=True``): the template has no
``shared/assets/<slug>/`` directory. Eight of nine templates today fall in
this branch; only v2-falzflyer has an asset directory.

The audit walks the filesystem as truth: every ``*.png/*.jpg/*.jpeg/*.psd/
*.eps/*.svg/*.tif/*.tiff/*.ai/*.pdf`` is an asset; ``links_export.yml`` and
other ``*.yml/*.md`` are metadata and excluded. This matches pitfalls.md §5
(composite-AI per-icon PNGs land on disk without manifest rows).

CLI: ``python3 tools/asset_policy_audit.py --slug <template_slug>``
Exit codes:
  0  ok or skipped.
  2  user-fixable issue (``missing`` / ``coverage``).
  3  policy-broken (``shipped_non_empty``).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

import yaml


# ---------------------------------------------------------------------------
# Module discovery — works whether run from repo root or via subprocess.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


from sla_lib.builder.meta_schema import load_asset_policy  # noqa: E402


# ---------------------------------------------------------------------------
# Constants — error messages live at module level so tests can assert
# verbatim text and so the audit emits a uniform UX across CLI / driver / pipeline.
# ---------------------------------------------------------------------------
_SHIPPED_REJECTED_MSG = (
    "Shipped assets are pending brand-team review. The first PR "
    "for issue #39 only supports `embedded:`. Move the asset to "
    "`embedded:` (it will be inlined in the SLA) or remove it from "
    "the template until the brand team decides on the zip flow."
)

_MISSING_POLICY_MSG = (
    "meta.yml::asset_policy is required when shared/assets/<slug>/ exists. "
    "Add an `asset_policy:` block listing every file in shared/assets/<slug>/ "
    "under `embedded:`. See .claude/skills/idml-import/asset_policy.md."
)

_UNCLASSIFIED_MSG = (
    "Assets on disk at shared/assets/<slug>/ are missing from "
    "meta.yml::asset_policy::embedded. First-PR rule (issue #39): every "
    "asset goes in `embedded:`. Add the missing basenames or remove the "
    "files from disk."
)

_STALE_MSG = (
    "meta.yml::asset_policy::embedded references basenames that do not "
    "exist on disk at shared/assets/<slug>/. Either restore the files or "
    "remove the entries from `embedded:`."
)


# Filesystem-truth: which file extensions count as assets.
_ASSET_EXTS: frozenset[str] = frozenset({
    ".png",
    ".jpg",
    ".jpeg",
    ".psd",
    ".eps",
    ".svg",
    ".tif",
    ".tiff",
    ".ai",
    ".pdf",
})


# ---------------------------------------------------------------------------
# Asset-dir resolution (dual lookup — render_pipeline.py:698 pattern).
# ---------------------------------------------------------------------------
def _find_asset_dir(template_slug: str, root: Path) -> Path | None:
    """Locate the asset directory for ``template_slug``.

    Preferred convention: ``shared/assets/<template_slug>/``.
    Historical fallback: ``shared/assets/<idml_stem_slug>/`` — derived
    from ``templates/<slug>/meta.yml::idml_source`` (or the legacy
    ``original_idml`` key), with the basename stripped of its ``.idml``
    suffix and slugified.

    Returns the first directory that exists, or ``None`` when neither
    candidate exists.
    """
    primary = root / "shared" / "assets" / template_slug
    if primary.is_dir():
        return primary

    # Try the IDML-stem-slug fallback. v2-falzflyer is the canonical case:
    # template slug "kandidat-falzflyer-din-lang-gruenes-cover-v2" but its
    # assets live at shared/assets/26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2/.
    meta_path = root / "templates" / template_slug / "meta.yml"
    if not meta_path.exists():
        return None
    try:
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None
    for key in ("idml_source", "original_idml", "source"):
        value = meta.get(key, "")
        if not value:
            build_meta = meta.get("build")
            if isinstance(build_meta, dict):
                value = build_meta.get("source", "")
        if not value:
            continue
        stem = Path(str(value)).stem
        if not stem:
            continue
        candidate = root / "shared" / "assets" / _slugify(stem)
        if candidate.is_dir():
            return candidate

    # Final scan: walk shared/assets/<dir>/links_export.yml and look for an
    # ``output:`` path that references templates/<template_slug>/ — covers
    # templates whose IDML source predates the meta.yml::idml_source field.
    # Cheap fallback so historical templates (v2-falzflyer) resolve cleanly
    # without re-authoring meta.yml.
    assets_root = root / "shared" / "assets"
    if not assets_root.is_dir():
        return None
    for child in sorted(assets_root.iterdir()):
        if not child.is_dir():
            continue
        manifest = child / "links_export.yml"
        if not manifest.exists():
            continue
        try:
            raw = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(raw, dict):
            continue
        template_in_manifest = raw.get("template") or raw.get("template_slug")
        if template_in_manifest == template_slug:
            return child
    # Last-resort guess: a single asset dir whose name shares the IDML's stem
    # convention. Look for templates/<slug>/build.py and grep an asset_map
    # reference (links_export.yml lookup happens in idml_to_dsl); but
    # simpler — if templates/<slug>/ exists, look for any asset dir whose
    # name appears in templates/<slug>/build.py asset paths.
    build_py = root / "templates" / template_slug / "build.py"
    if build_py.exists():
        try:
            text = build_py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        for child in sorted(assets_root.iterdir()):
            if not child.is_dir():
                continue
            needle = f"shared/assets/{child.name}/"
            if needle in text:
                return child
            # Absolute-path form (the very bug Phase A fixes).
            if str(child) in text:
                return child
    return None


def _slugify(stem: str) -> str:
    """Lowercase, replace non-alphanumeric runs with dashes, strip edges.

    Mirrors the shape produced by ``tools/idml_import_driver.py::_slugify``
    well enough to match historical asset-dir names (26-03-leporello-...).
    """
    import re
    out = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()
    return out


# ---------------------------------------------------------------------------
# Asset listing — filesystem as truth.
# ---------------------------------------------------------------------------
def _list_disk_assets(asset_dir: Path) -> list[str]:
    """Return the sorted basenames of files in ``asset_dir`` whose suffix
    is in ``_ASSET_EXTS``. Subdirectories and metadata files (``*.yml``,
    ``*.md``) are excluded.
    """
    items: list[str] = []
    for child in sorted(asset_dir.iterdir()):
        if not child.is_file():
            continue
        if child.suffix.lower() not in _ASSET_EXTS:
            continue
        items.append(child.name)
    return items


# ---------------------------------------------------------------------------
# Audit entry point.
# ---------------------------------------------------------------------------
def run_asset_policy_audit(
    template_slug: str,
    root: Path,
    *,
    out_dir: Path | None = None,
) -> dict:
    """Audit ``meta.yml::asset_policy`` against ``shared/assets/<slug>/``.

    Args:
        template_slug: Template slug (e.g. ``kandidat-falzflyer-…-v2``).
        root: Repo root. Used to resolve ``templates/<slug>/meta.yml`` and
            ``shared/assets/<slug>/``. Pass the worktree root; the function
            never reaches outside ``root``.
        out_dir: Optional directory for ``asset_policy_audit.yml``. When
            given, the audit writes the report dict to
            ``<out_dir>/asset_policy_audit.yml``.

    Returns a dict with keys:
        ok          (bool)  — overall verdict.
        skipped     (bool)  — True when there is no asset directory.
        reason      (str)   — human-readable status (skip cases).
        issue       (str)   — one of "shipped_non_empty", "missing",
                              "coverage" when ok is False.
        message     (str)   — issue-specific message text.
        asset_dir   (str)   — repo-relative path to the asset directory,
                              or None when no directory was found.
        embedded    (list[str]) — entries declared in the policy.
        shipped     (list[str]) — entries declared in the policy.
        on_disk     (list[str]) — basenames found on disk.
        unclassified (list[str]) — on disk but not in embedded:.
        stale       (list[str]) — in embedded: but not on disk.

    Raises:
        ValueError — re-raised from ``load_asset_policy`` when meta.yml's
        ``asset_policy:`` block fails schema or disjoint validation. The
        caller treats this as a hard fail.
    """
    asset_dir = _find_asset_dir(template_slug, root)
    rel_asset_dir: str | None = None
    if asset_dir is not None:
        try:
            rel_asset_dir = str(asset_dir.relative_to(root))
        except ValueError:
            rel_asset_dir = str(asset_dir)

    if asset_dir is None:
        report: dict = {
            "template": template_slug,
            "ok": True,
            "skipped": True,
            "reason": "no shared/assets/<slug>/ directory",
            "asset_dir": None,
            "embedded": [],
            "shipped": [],
            "on_disk": [],
            "unclassified": [],
            "stale": [],
        }
        _maybe_write(report, out_dir)
        return report

    on_disk = _list_disk_assets(asset_dir)

    # Loader raises ValueError on schema/disjoint problems; let it propagate
    # so the caller surfaces the precise schema error.
    policy = load_asset_policy(template_slug, root=root)

    if policy is None:
        report = {
            "template": template_slug,
            "ok": False,
            "skipped": False,
            "issue": "missing",
            "message": _MISSING_POLICY_MSG,
            "asset_dir": rel_asset_dir,
            "embedded": [],
            "shipped": [],
            "on_disk": on_disk,
            "unclassified": list(on_disk),
            "stale": [],
        }
        _maybe_write(report, out_dir)
        return report

    embedded: list[str] = sorted(policy.get("embedded", []) or [])
    shipped: list[str] = sorted(policy.get("shipped", []) or [])

    if shipped:
        report = {
            "template": template_slug,
            "ok": False,
            "skipped": False,
            "issue": "shipped_non_empty",
            "message": _SHIPPED_REJECTED_MSG,
            "asset_dir": rel_asset_dir,
            "embedded": embedded,
            "shipped": shipped,
            "on_disk": on_disk,
            "unclassified": [],
            "stale": [],
        }
        _maybe_write(report, out_dir)
        return report

    embedded_set = set(embedded)
    disk_set = set(on_disk)
    unclassified = sorted(disk_set - embedded_set)
    stale = sorted(embedded_set - disk_set)

    if unclassified or stale:
        parts: list[str] = []
        if unclassified:
            parts.append(_UNCLASSIFIED_MSG + " Missing: " + ", ".join(unclassified))
        if stale:
            parts.append(_STALE_MSG + " Stale: " + ", ".join(stale))
        report = {
            "template": template_slug,
            "ok": False,
            "skipped": False,
            "issue": "coverage",
            "message": "; ".join(parts),
            "asset_dir": rel_asset_dir,
            "embedded": embedded,
            "shipped": shipped,
            "on_disk": on_disk,
            "unclassified": unclassified,
            "stale": stale,
        }
        _maybe_write(report, out_dir)
        return report

    report = {
        "template": template_slug,
        "ok": True,
        "skipped": False,
        "asset_dir": rel_asset_dir,
        "embedded": embedded,
        "shipped": shipped,
        "on_disk": on_disk,
        "unclassified": [],
        "stale": [],
    }
    _maybe_write(report, out_dir)
    return report


def _maybe_write(report: dict, out_dir: Path | None) -> None:
    """Write ``asset_policy_audit.yml`` when an output directory is given."""
    if out_dir is None:
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "asset_policy_audit.yml"
    out_path.write_text(
        yaml.safe_dump(report, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------
def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="asset_policy_audit",
        description=(
            "Audit meta.yml::asset_policy against shared/assets/<slug>/. "
            "Hard-fail on shipped:-non-empty, missing policy, or coverage drift."
        ),
    )
    parser.add_argument(
        "--slug",
        required=True,
        help="Template slug (e.g. kandidat-falzflyer-din-lang-gruenes-cover-v2).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_REPO_ROOT,
        help="Repo root (default: parent of tools/).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help=(
            "Optional output directory for asset_policy_audit.yml "
            "(default: do not write a report file)."
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        report = run_asset_policy_audit(
            template_slug=args.slug,
            root=args.root,
            out_dir=args.out_dir,
        )
    except ValueError as exc:
        print(f"asset_policy_audit: schema error: {exc}", file=sys.stderr)
        return 2

    if report.get("ok"):
        if report.get("skipped"):
            print(
                f"[{args.slug}] asset_policy_audit: skipped "
                f"({report.get('reason', 'no asset dir')})"
            )
        else:
            print(f"[{args.slug}] asset_policy_audit: OK")
        return 0

    issue = report.get("issue", "unknown")
    message = report.get("message", "")
    print(f"[{args.slug}] asset_policy_audit: FAIL ({issue})", file=sys.stderr)
    print(f"  {message}", file=sys.stderr)
    if report.get("unclassified"):
        print(
            f"  unclassified: {', '.join(report['unclassified'])}",
            file=sys.stderr,
        )
    if report.get("stale"):
        print(f"  stale: {', '.join(report['stale'])}", file=sys.stderr)
    if issue == "shipped_non_empty":
        return 3
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
