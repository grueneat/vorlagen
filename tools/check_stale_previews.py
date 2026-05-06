#!/usr/bin/env python3
"""tools/check_stale_previews.py — gallery preview staleness gate (issue #4).

For each template under templates/<id>/ that has both a meta.yml and an
original_sla: key, this script checks whether the committed gallery previews
(preview.pdf + page-*.png, or per-size PDFs for family templates) match the
committed template SLA bytes.

The check works by comparing the SHA256 hash of each template's committed
template.sla (or per-size <code>.sla for family) against the hash recorded
in meta.yml::previews_for_sla. If the SLA has changed since the last pipeline
run (bin/render-gallery) without the previews being regenerated, the hashes
will differ and this script exits 1 with a clear "run bin/render-gallery" error.

This is the staleness gate that bin/validate runs as a preflight and that CI
runs inside the validate-reproductions step.

Usage:
    bin/check-stale-previews     # check all templates with original_sla
Exit:
    0 -- all templates' previews are current
    1 -- one or more templates have stale or missing previews
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"


def _sha256_of(p: Path) -> str:
    """Return SHA256 hex digest of the raw bytes of file p."""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _check_template(tdir: Path) -> list[str]:
    """Return a list of error strings for the given template directory.

    An empty list means the template's previews are current.
    Returns [] for directories without meta.yml or without original_sla (skip).
    """
    meta_path = tdir / "meta.yml"
    if not meta_path.exists():
        return []

    try:
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"error reading {meta_path}: {exc}"]

    if not isinstance(meta, dict):
        return []
    if not meta.get("original_sla"):
        return []  # No original_sla → skip (smoke templates, etc.)

    tid = meta.get("id", tdir.name)
    is_family = meta.get("type") == "family"
    recorded = meta.get("previews_for_sla")

    if recorded is None:
        return [
            f"stale: {tid}; previews_for_sla missing in meta.yml — "
            "run bin/render-gallery and commit the result."
        ]

    errors: list[str] = []

    if is_family:
        # Family: recorded must be a dict mapping size code → hash.
        if not isinstance(recorded, dict):
            return [
                f"stale: {tid}; previews_for_sla has unexpected type "
                f"{type(recorded).__name__!r} (expected dict for family template) — "
                "run bin/render-gallery and commit the result."
            ]
        for size in meta.get("sizes", []):
            code = size["code"]
            sla_path = tdir / f"{code}.sla"
            if not sla_path.exists():
                errors.append(
                    f"stale: {tid}/{code}; {code}.sla not found — "
                    "run bin/render-gallery and commit the result."
                )
                continue
            actual = _sha256_of(sla_path)
            expected = recorded.get(code)
            if actual != expected:
                errors.append(
                    f"stale: {tid}/{code}; SLA hash mismatch "
                    f"(recorded={str(expected)[:16]}... actual={actual[:16]}...) — "
                    "Run bin/render-gallery and commit the result."
                )
    else:
        # Non-family: recorded must be a 64-char hex string.
        if not isinstance(recorded, str):
            return [
                f"stale: {tid}; previews_for_sla has unexpected type "
                f"{type(recorded).__name__!r} (expected str for single-template) — "
                "run bin/render-gallery and commit the result."
            ]
        sla_path = tdir / "template.sla"
        if not sla_path.exists():
            return [
                f"stale: {tid}; template.sla not found — "
                "run bin/render-gallery and commit the result."
            ]
        actual = _sha256_of(sla_path)
        if actual != recorded:
            errors.append(
                f"stale: {tid}; template.sla hash mismatch "
                f"(recorded={recorded[:16]}... actual={actual[:16]}...) — "
                "Run bin/render-gallery and commit the result."
            )

    return errors


def main(argv=None) -> int:
    """Entry point for bin/check-stale-previews."""
    # argv is accepted for interface symmetry with render_pipeline.main() but unused.
    all_errors: list[str] = []

    for tdir in sorted(TEMPLATES_DIR.iterdir()):
        if not tdir.is_dir():
            continue
        if tdir.name.startswith("_"):
            continue  # skip _smoke and similar
        errors = _check_template(tdir)
        all_errors.extend(errors)

    if all_errors:
        print("Gallery previews are stale — commit is not in sync with template SLAs:", file=sys.stderr)
        for err in all_errors:
            print(f"  {err}", file=sys.stderr)
        print(
            "\nFix by running locally:\n"
            "  bin/render-gallery && git add templates/ site/public/ && git commit",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
