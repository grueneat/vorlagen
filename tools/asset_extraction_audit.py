#!/usr/bin/env python3
"""Asset-extraction audit (Phase E, issue #38).

Walks an IDML for every <Link LinkResourceURI=...> reference, asserts the
target file is present in the sibling Links/ directory, asserts a matching
entry exists in the links_export.yml manifest, and flags AI files that
look like composite strips (multi-page AND/OR wide-aspect AND/OR multiple
ImageFrames at distinct LocalOffsets — see RESEARCH.md P0 #2).

The audit emits build/validation/<slug>/asset_audit.yml and returns a dict.

Failure modes:
  - links_missing — IDML references a link not present in Links/.
  - links_unconverted — link present but no manifest entry.
  - composite_ai_detected — AI source needs the composite_ai_split.py
    splitter to preserve vector quality.

Default behaviour: composite-AI is a hard FAIL (ok=False). Pass
allow_composite_ai=True to downgrade to a warning recorded in
asset_audit.yml::warnings.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml
from lxml import etree


# ---------------------------------------------------------------------------
# Detection thresholds (RESEARCH.md P0 #2).
# ---------------------------------------------------------------------------
_ASPECT_RATIO_THRESHOLD = 3.0
_DISTINCT_OFFSETS_THRESHOLD = 2


# ---------------------------------------------------------------------------
# Link extraction.
# ---------------------------------------------------------------------------


def _basename_from_uri(uri: str) -> str:
    """Strip file:// prefixes and return the final path component (NFC-normalised)."""
    if not uri:
        return ""
    cleaned = uri
    for prefix in ("file://", "file:"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    # The URI may use forward slashes regardless of source OS.
    name = cleaned.rsplit("/", 1)[-1]
    return unicodedata.normalize("NFC", name)


def _iter_idml_link_uris(idml_path: Path) -> list[tuple[str, str]]:
    """Walk every Stories/* and Spreads/* XML in the IDML and collect Link URIs.

    Returns: list of (link_basename, source_xml_path).
    """
    pairs: list[tuple[str, str]] = []
    with zipfile.ZipFile(str(idml_path)) as zf:
        for entry in zf.namelist():
            if not (
                entry.startswith("Stories/")
                or entry.startswith("Spreads/")
                or entry == "designmap.xml"
            ):
                continue
            try:
                raw = zf.read(entry)
            except KeyError:
                continue
            try:
                root = etree.fromstring(raw)
            except etree.XMLSyntaxError:
                continue
            # Every <Link> with a LinkResourceURI attribute is a candidate.
            for link in root.iter():
                tag = etree.QName(link).localname
                if tag != "Link":
                    continue
                uri = link.get("LinkResourceURI") or ""
                basename = _basename_from_uri(uri)
                if basename:
                    pairs.append((basename, entry))
    return pairs


# ---------------------------------------------------------------------------
# ImageFrame offset/scale extraction for composite-AI detection.
# ---------------------------------------------------------------------------


_ITEM_TRANSFORM_RE = re.compile(r"\s+")


def _parse_item_transform(s: str) -> tuple[float, float, float, float, float, float] | None:
    """Parse IDML ItemTransform="a b c d tx ty" into a 6-tuple of floats."""
    if not s:
        return None
    parts = _ITEM_TRANSFORM_RE.split(s.strip())
    if len(parts) != 6:
        return None
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def _iter_image_offsets_for_link(
    idml_path: Path,
    link_basename: str,
) -> list[tuple[float, float, float, float]]:
    """Return distinct (scale_x, scale_y, tx, ty) tuples for ImageFrames
    pointing at the named link.

    Strategy: walk every Spread + Story XML, find Rectangle/Image elements
    whose child <Link LinkResourceURI=...> basename matches. Record the
    nearest ancestor's ItemTransform (the placement of the frame, which is
    what InDesign uses to position the AI page on the spread).
    """
    seen: list[tuple[float, float, float, float]] = []
    with zipfile.ZipFile(str(idml_path)) as zf:
        for entry in zf.namelist():
            if not (
                entry.startswith("Stories/")
                or entry.startswith("Spreads/")
            ):
                continue
            try:
                root = etree.fromstring(zf.read(entry))
            except (etree.XMLSyntaxError, KeyError):
                continue
            # Find every Link element whose URI basename matches.
            for link in root.iter():
                tag = etree.QName(link).localname
                if tag != "Link":
                    continue
                if _basename_from_uri(link.get("LinkResourceURI", "")) != link_basename:
                    continue
                # Walk up looking for the FRAME's ItemTransform (Rectangle /
                # Polygon / Group / ImageFrame containing the Image). The
                # Image element's own ItemTransform is content-local placement
                # (LOCALX/LOCALY in Scribus), NOT page placement; skip it.
                node = link.getparent()
                transform: tuple[float, float, float, float, float, float] | None = None
                while node is not None:
                    parent_tag = etree.QName(node).localname
                    if parent_tag not in ("Image", "PDF", "EPS"):
                        tstr = node.get("ItemTransform")
                        if tstr:
                            parsed = _parse_item_transform(tstr)
                            if parsed:
                                transform = parsed
                                break
                    node = node.getparent()
                if transform is None:
                    # Fall back to zero transform — still record so we can
                    # detect "multiple frames at unknown positions".
                    transform = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                a, _b, _c, d, tx, ty = transform
                seen.append((a, d, tx, ty))
    # Deduplicate while preserving order.
    out: list[tuple[float, float, float, float]] = []
    for item in seen:
        if item not in out:
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# AI-page measurement.
# ---------------------------------------------------------------------------


@dataclass
class AiMeasurement:
    page_count: int
    bbox_pt: tuple[float, float]  # (width, height) of page 0
    aspect_ratio: float


def _measure_ai(ai_path: Path) -> AiMeasurement | None:
    """Measure AI/PDF page count + bbox via pdfplumber. Returns None on failure."""
    try:
        import pdfplumber
    except ImportError:
        return None
    try:
        with pdfplumber.open(str(ai_path)) as pdf:
            if not pdf.pages:
                return None
            page = pdf.pages[0]
            w = float(page.width)
            h = float(page.height)
            count = len(pdf.pages)
            ratio = max(w, h) / max(min(w, h), 1.0)
            return AiMeasurement(
                page_count=count,
                bbox_pt=(w, h),
                aspect_ratio=ratio,
            )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Manifest reading.
# ---------------------------------------------------------------------------


def _load_links_manifest(manifest_path: Path) -> dict[str, dict]:
    """Read links_export.yml and return {original_basename: entry_dict}."""
    if not manifest_path.exists():
        return {}
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    assets = raw.get("assets") or {}
    if not isinstance(assets, dict):
        return {}
    return assets


# ---------------------------------------------------------------------------
# Main audit.
# ---------------------------------------------------------------------------


def audit(
    slug: str,
    idml_path: Path,
    links_export_yml: Path,
    repo_root: Path,
    *,
    allow_composite_ai: bool = False,
    out_dir: Path | None = None,
) -> dict:
    """Run the asset-extraction audit.

    Args:
        slug: Template slug (used in the emitted yml and as the audit subject).
        idml_path: Path to the .idml file.
        links_export_yml: Path to the manifest produced by links_export.py.
        repo_root: Repo root, used to compute relative paths.
        allow_composite_ai: If True, composite-AI findings become warnings
            instead of hard failures.
        out_dir: Optional override for the build/validation/<slug>/ output
            directory. Defaults to repo_root/build/validation/<slug>.

    Returns:
        The audit dict that is also written to <out_dir>/asset_audit.yml.
    """
    if not idml_path.exists():
        raise FileNotFoundError(f"IDML not found: {idml_path}")

    # Resolve sibling Links/ directory next to the IDML.
    links_dir = idml_path.parent / "Links"

    # 1) Extract every Link URI from the IDML.
    link_uris = _iter_idml_link_uris(idml_path)
    link_basenames: list[str] = sorted({bn for bn, _src in link_uris})

    # 2) Check Links/ presence.
    links_missing: list[str] = []
    for bn in link_basenames:
        if not (links_dir / bn).exists():
            links_missing.append(bn)

    # 3) Check links_export.yml entries.
    manifest_entries = _load_links_manifest(links_export_yml)
    links_unconverted: list[str] = []
    for bn in link_basenames:
        if bn not in manifest_entries:
            links_unconverted.append(bn)

    # 4) Composite-AI detection.
    composite_ai_detected: list[dict] = []
    for bn in link_basenames:
        if not bn.lower().endswith(".ai"):
            continue
        ai_path = links_dir / bn
        if not ai_path.exists():
            # Will already be in links_missing; skip composite check.
            continue
        meas = _measure_ai(ai_path)
        offsets = _iter_image_offsets_for_link(idml_path, bn)
        is_composite = False
        signals: list[str] = []
        if meas is not None:
            if meas.page_count > 1:
                is_composite = True
                signals.append(f"page_count={meas.page_count}")
            if meas.aspect_ratio > _ASPECT_RATIO_THRESHOLD:
                is_composite = True
                signals.append(f"aspect_ratio={meas.aspect_ratio:.2f}")
        if len(offsets) >= _DISTINCT_OFFSETS_THRESHOLD:
            # Only flag if those offsets actually differ from (0,0).
            non_zero = [o for o in offsets if (o[2], o[3]) != (0.0, 0.0)]
            if non_zero:
                is_composite = True
                signals.append(f"distinct_offsets={len(offsets)}")
        if is_composite:
            composite_ai_detected.append(
                {
                    "path": str(ai_path.relative_to(repo_root)) if _is_under(ai_path, repo_root) else str(ai_path),
                    "page_count": meas.page_count if meas else None,
                    "aspect_ratio": round(meas.aspect_ratio, 2) if meas else None,
                    "distinct_offsets_count": len(offsets),
                    "signals": signals,
                }
            )

    warnings: list[str] = []
    composite_warn_only = allow_composite_ai and composite_ai_detected
    if composite_warn_only:
        for finding in composite_ai_detected:
            warnings.append(
                f"composite-AI detected: {finding['path']} "
                f"({', '.join(finding['signals'])}); --allow-composite-ai bypass active"
            )

    # 5) Compute ok.
    has_blocking_composite = bool(composite_ai_detected) and not allow_composite_ai
    ok = (
        not links_missing
        and not links_unconverted
        and not has_blocking_composite
    )

    report: dict = {
        "template": slug,
        "ok": ok,
        "links_total": len(link_basenames),
        "links_resolved": len(link_basenames) - len(links_missing),
        "links_converted": len(link_basenames) - len(links_unconverted),
        "links_missing": sorted(links_missing),
        "links_unconverted": sorted(links_unconverted),
        "composite_ai_detected": composite_ai_detected,
    }
    if warnings:
        report["warnings"] = warnings

    # 6) Write YAML.
    if out_dir is None:
        out_dir = repo_root / "build" / "validation" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "asset_audit.yml"
    out_path.write_text(
        yaml.safe_dump(report, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    return report


def _is_under(child: Path, root: Path) -> bool:
    try:
        child.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="asset_extraction_audit",
        description=(
            "Audit asset extraction completeness for an IDML template. "
            "Detects missing Links/, missing manifest entries, and "
            "composite-AI strips that need per-page splitting."
        ),
    )
    parser.add_argument("--slug", required=True, help="Template slug.")
    parser.add_argument(
        "--idml", required=True, type=Path, help="Path to the .idml file."
    )
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="Path to links_export.yml (manifest from tools/links_export.py).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repo root (default: parent of tools/).",
    )
    parser.add_argument(
        "--allow-composite-ai",
        action="store_true",
        help="Downgrade composite-AI findings to warnings instead of failing.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Override the output directory (default: build/validation/<slug>).",
    )
    args = parser.parse_args(argv)
    result = audit(
        slug=args.slug,
        idml_path=args.idml,
        links_export_yml=args.manifest,
        repo_root=args.repo_root,
        allow_composite_ai=args.allow_composite_ai,
        out_dir=args.out_dir,
    )
    if result["ok"]:
        return 0
    print(
        "asset_extraction_audit FAILED — see build/validation/<slug>/asset_audit.yml",
        file=sys.stderr,
    )
    for bn in result.get("links_missing", []):
        print(f"  missing in Links/: {bn}", file=sys.stderr)
    for bn in result.get("links_unconverted", []):
        print(f"  missing from manifest: {bn}", file=sys.stderr)
    for finding in result.get("composite_ai_detected", []):
        print(
            f"  composite-AI: {finding['path']} "
            f"({', '.join(finding.get('signals', []))}); "
            f"run tools/composite_ai_split.py or pass --allow-composite-ai "
            f"to bypass (degraded vector quality).",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
