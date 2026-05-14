"""Shared freshness gate for audit tools.

The /idml-tune skill produces multiple artifacts that must stay in sync
(template.sla, preview.pdf, page-NN.png, meta.yml hash). The canonical
re-render command is ``bin/tune-render``. Audit tools downstream
(E4 line_spacing_pixel_audit, E5 image_frame_visibility_audit,
E6 per_region_regression_check) MUST refuse to run on stale artifacts
— otherwise an LLM executor can "forget" to re-render and still see
green audit numbers from a previous render's PDFs/PNGs.

This module provides the gate. By default audits invoke ``ensure_fresh``
before reading any preview.pdf/baseline.pdf. The gate compares mtimes
of build.py → template.sla → preview.pdf → page-NN.png and the
meta.yml hash; if any drift is detected, raises ``StaleArtifactsError``
which audits surface to the caller as a non-zero exit + clear stderr
pointing to ``bin/tune-render <slug>``.

The gate can be bypassed with ``--skip-freshness`` (used internally by
render-gallery which knows it just produced the artifacts in sequence).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path


class StaleArtifactsError(RuntimeError):
    """Raised when downstream artifacts are older than their inputs."""
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_template_freshness(template_dir: Path) -> list[str]:
    """Return list of stale complaints (empty = in sync).

    Mirrors ``bin/tune-render --check``; identical complaint format.
    """
    complaints: list[str] = []
    build_py = template_dir / "build.py"
    sla = template_dir / "template.sla"
    preview = template_dir / "preview.pdf"
    if not build_py.exists():
        complaints.append(f"missing {build_py}")
        return complaints
    bp_mtime = build_py.stat().st_mtime

    def _stale(child: Path, parent_mtime: float, tag: str) -> None:
        if not child.exists():
            complaints.append(f"missing {child.name} — run `bin/tune-render <slug>`")
        elif child.stat().st_mtime < parent_mtime - 1.0:
            complaints.append(
                f"{tag}: {child.name} is older than its source — "
                "re-render with `bin/tune-render <slug>`"
            )

    _stale(sla, bp_mtime, "template.sla")
    if sla.exists():
        sla_mtime = sla.stat().st_mtime
        _stale(preview, sla_mtime, "preview.pdf")
        if preview.exists():
            preview_mtime = preview.stat().st_mtime
            for png_name in ("page-01.png", "page-02.png",
                             "page-01-hires.png", "page-02-hires.png"):
                _stale(template_dir / png_name, preview_mtime, png_name)
    meta_yml = template_dir / "meta.yml"
    if meta_yml.exists() and sla.exists():
        m = re.search(
            r"^previews_for_sla:\s*(\S+)",
            meta_yml.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if m:
            recorded = m.group(1)
            actual = _sha256(sla)
            if recorded != actual and recorded != "_pending_first_build":
                complaints.append(
                    f"meta.yml::previews_for_sla hash {recorded[:8]}… ≠ actual {actual[:8]}… "
                    "— re-render with `bin/tune-render <slug>`"
                )
    return complaints


def ensure_fresh(template_dir: Path, *, audit_name: str) -> None:
    """Raise StaleArtifactsError if artifacts are stale. No-op when fresh.

    Args:
        template_dir: ``templates/<slug>/``
        audit_name: human label for the audit (e.g. "line_spacing_pixel_audit").
            Surfaced in the error message so the user knows which audit
            refused.
    """
    complaints = check_template_freshness(template_dir)
    if complaints:
        msg = (
            f"\n{audit_name} refusing to run on stale artifacts:\n"
            + "\n".join(f"  STALE: {c}" for c in complaints)
            + f"\n\nFix: bin/tune-render {template_dir.name}\n"
            "  (this command rebuilds template.sla, preview.pdf, page-NN.png, "
            "and the meta.yml hash atomically.)\n"
        )
        raise StaleArtifactsError(msg)
