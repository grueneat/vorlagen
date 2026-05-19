#!/usr/bin/env python3
"""bin/convergence-review — classify + leverage-sort audit issues.

Reads every audit yml/json under build/validation/<slug>/ and emits a
sorted issue list with per-issue classification (converter-bug,
scribus-engine-bug, authoring-bug, human-review) and an estimated
drift-drop leverage score.

Output formats:
  --format md   (default): human-readable markdown report.
  --format json:          machine-readable for bin/idml-import.

Reads:
  build/validation/<slug>/preflight.yml           (mandatory)
  build/validation/<slug>/inventory.yml
  build/validation/<slug>/text_audit.yml
  build/validation/<slug>/image_audit.yml
  build/validation/<slug>/font_audit.yml
  build/validation/<slug>/text_render_audit.yml
  build/validation/<slug>/text_position_audit.yml
  build/validation/<slug>/run_style_audit.yml
  build/validation/<slug>/per_element_drift.yml
  build/validation/<slug>/region_color_audit.yml
  build/validation/<slug>/line_spacing_audit.yml
  build/validation/<slug>/visual_diff_regions.yml
  build/validation/<slug>/diff_bboxes.json
  build/validation/<slug>/visual_diff.json
  build/validation/<slug>/asset_audit.yml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent


_SEVERITY_RANK = {
    "scribus-engine-bug": 0,
    "converter-bug": 1,
    "authoring-bug": 2,
    "human-review": 3,
    "minor": 4,
}


# ---------------------------------------------------------------------------
# IO helpers.
# ---------------------------------------------------------------------------


def _load_yml(p: Path) -> dict | None:
    if not p.exists():
        return None
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None


def _load_json(p: Path) -> dict | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _load_all(validation_dir: Path) -> dict[str, Any]:
    """Load every known audit artifact. Missing files => None entries."""
    return {
        "preflight": _load_yml(validation_dir / "preflight.yml"),
        "inventory": _load_yml(validation_dir / "inventory.yml"),
        "text_audit": _load_yml(validation_dir / "text_audit.yml"),
        "image_audit": _load_yml(validation_dir / "image_audit.yml"),
        "font_audit": _load_yml(validation_dir / "font_audit.yml"),
        "text_render_audit": _load_yml(validation_dir / "text_render_audit.yml"),
        "text_position_audit": _load_yml(validation_dir / "text_position_audit.yml"),
        "run_style_audit": _load_yml(validation_dir / "run_style_audit.yml"),
        "per_element_drift": _load_yml(validation_dir / "per_element_drift.yml"),
        "region_color_audit": _load_yml(validation_dir / "region_color_audit.yml"),
        "line_spacing_audit": _load_yml(validation_dir / "line_spacing_audit.yml"),
        # Audit-reliability review item 4: surface the newer per-frame
        # signals (E4/E5/E6) so the convergence review's hot-issue list
        # includes pixel-level line-spacing drifts, invisible image
        # frames, and per-region regressions vs the previous run.
        "line_spacing_pixel_audit": _load_yml(
            validation_dir / "line_spacing_pixel_audit.yml"),
        "image_frame_visibility_audit": _load_yml(
            validation_dir / "image_frame_visibility_audit.yml"),
        "per_region_regression": _load_yml(
            validation_dir / "per_region_regression.yml"),
        "visual_diff_regions": _load_yml(validation_dir / "visual_diff_regions.yml"),
        "diff_bboxes": _load_json(validation_dir / "diff_bboxes.json"),
        "visual_diff": _load_json(validation_dir / "visual_diff.json"),
        "asset_audit": _load_yml(validation_dir / "asset_audit.yml"),
    }


# ---------------------------------------------------------------------------
# Issue extraction + classification.
# ---------------------------------------------------------------------------


def _idml_xpath_contains_mixed_justification(_idml_path: Path | None) -> bool:
    """Stub: would walk the IDML for mixed Justification on a single paragraph.

    Without an IDML argument, we conservatively answer 'False' so the caller
    bias toward 'human-review' rather than guessing 'converter-bug'.
    """
    return False


def _classify_text_position(issue: dict, idml_path: Path | None) -> str:
    """text_position_audit::large_deltas heuristic."""
    if idml_path is not None and _idml_xpath_contains_mixed_justification(idml_path):
        return "converter-bug"
    return "human-review"


def _classify_region_color(severity: str, delta: float | None) -> str:
    """region_color_audit::icc_likely + brand-color region => scribus-engine-bug.

    ``delta`` is the offset-compensated residual delta (the part of a
    frame's colour delta NOT explained by the document's systematic
    colour-management offset) — see tools/region_color_audit.py.
    """
    if severity == "icc_likely" and (delta is None or delta <= 5.0):
        return "scribus-engine-bug"
    if severity == "fill_likely" and (delta is None or delta > 5.0):
        return "converter-bug"
    return "human-review"


def _per_element_top_for_slot(
    per_element_drift: dict | None,
    page: int | None,
    slot: str | None,
) -> tuple[float, float]:
    """Return (sum_pct_of_page_mismatch, page_total) for the given slot/page.

    If per_element_drift is absent, returns (0.0, 0.0).
    """
    if per_element_drift is None or slot is None:
        return (0.0, 0.0)
    pages = per_element_drift.get("pages") or []
    for entry in pages:
        if page is not None and entry.get("page") != page:
            continue
        top = entry.get("top_contributors") or []
        page_total = float(entry.get("total_mismatch_pct") or 0.0)
        contributions = sum(
            float(r.get("pct_of_page_mismatch") or 0.0)
            for r in top
            if r.get("slot") == slot
        )
        return (contributions, page_total)
    return (0.0, 0.0)


def _est_drift_drop(
    issue: dict,
    per_element_drift: dict | None,
) -> float:
    """Estimate page-mismatch drop if this issue were fixed (RESEARCH.md)."""
    page = issue.get("page")
    slot = issue.get("slot")
    contrib, page_total = _per_element_top_for_slot(
        per_element_drift, page, slot
    )
    if page_total <= 0.0:
        return 0.0
    return float(min(contrib, page_total))


# ---------------------------------------------------------------------------
# Issue builders — one per audit.
# ---------------------------------------------------------------------------


def _next_id_factory():
    counter = {"n": 0}

    def _next() -> int:
        counter["n"] += 1
        return counter["n"]
    return _next


def _issues_from_region_color(rca: dict | None, next_id) -> list[dict]:
    if not rca:
        return []
    out: list[dict] = []
    frames = rca.get("frames") or []
    for frame in frames:
        severity = frame.get("severity", "ok")
        if severity == "ok":
            continue
        mean_delta = frame.get("mean_delta")
        # Classify on the offset-compensated residual when present (the
        # part of the delta NOT explained by the systematic
        # colour-management offset); fall back to mean_delta for older
        # audit YAML that predates residual_delta.
        residual_delta = frame.get("residual_delta", mean_delta)
        cls = _classify_region_color(severity, residual_delta)
        slot = frame.get("anname")
        page = frame.get("page")
        suggested = (
            "Brand-color ICC drift; track upstream as a Scribus engine bug "
            "and accept residual via --accept-residual."
            if cls == "scribus-engine-bug"
            else "Investigate converter fill-color emission for this slot; "
            "expected mean_delta < 5.0 RGB units."
        )
        path = (
            "tools/region_color_audit.py" if cls == "converter-bug" else ""
        )
        out.append(
            {
                "id": next_id(),
                "slot": slot,
                "page": page,
                "audit": "region_color_audit",
                "severity": severity,
                "classification": cls,
                "converter_path": path,
                "suggested_action": suggested,
                "regression_test_path": (
                    f"tests/unit/test_region_color_audit.py::test_{slot}"
                    if cls == "converter-bug" else ""
                ),
                "mean_delta": mean_delta,
            }
        )
    return out


def _issues_from_text_position(
    tpa: dict | None,
    next_id,
    idml_path: Path | None,
) -> list[dict]:
    if not tpa:
        return []
    out: list[dict] = []
    for delta in (tpa.get("large_deltas") or []):
        cls = _classify_text_position(delta, idml_path)
        slot = delta.get("anname") or delta.get("text")
        path = (
            "tools/idml_to_dsl.py (DefaultStyle ALIGN / paragraph_attrs)"
            if cls == "converter-bug" else ""
        )
        out.append(
            {
                "id": next_id(),
                "slot": slot,
                "page": delta.get("page"),
                "audit": "text_position_audit",
                "severity": delta.get("severity", ""),
                "classification": cls,
                "converter_path": path,
                "suggested_action": (
                    "Verify per-paragraph ALIGN emission in the converter "
                    "matches IDML Justification (Backport 11)."
                    if cls == "converter-bug"
                    else "Inspect the IDML for mixed Justification on the "
                    "affected paragraph; classify after triage."
                ),
                "regression_test_path": "",
                "dx_pt": delta.get("dx_pt"),
                "dy_pt": delta.get("dy_pt"),
            }
        )
    return out


def _issues_from_diff_bboxes(
    diff_bboxes: dict | None,
    inventory: dict | None,
    next_id,
) -> list[dict]:
    if not diff_bboxes:
        return []
    out: list[dict] = []
    known_annames: set[str] = set()
    if inventory:
        for spread in inventory.get("spreads") or []:
            for el in (spread.get("elements_emitted") or []):
                anname = el.get("anname")
                if anname:
                    known_annames.add(anname)
    for page in (diff_bboxes.get("pages") or []):
        page_num = page.get("page")
        for bbox in (page.get("bboxes") or []):
            drift_type = bbox.get("drift_type", "unknown")
            slot = bbox.get("attributed_slot")
            cls = "human-review"
            if drift_type == "missing" and (
                slot is None or slot not in known_annames
            ):
                cls = "converter-bug"
            out.append(
                {
                    "id": next_id(),
                    "slot": slot,
                    "page": page_num,
                    "audit": "diff_bboxes",
                    "severity": drift_type,
                    "classification": cls,
                    "converter_path": (
                        "tools/idml_to_dsl.py:_emit_pages"
                        if cls == "converter-bug" else ""
                    ),
                    "suggested_action": (
                        "Element appears in baseline but not in build.py; "
                        "extend the converter to emit it."
                        if cls == "converter-bug"
                        else "Drift bbox classification ambiguous; triage."
                    ),
                    "regression_test_path": "",
                }
            )
    return out


def _issues_from_font_audit(fa: dict | None, next_id) -> list[dict]:
    if not fa:
        return []
    out: list[dict] = []
    missing = fa.get("missing_in_preview") or []
    for font_name in missing:
        out.append(
            {
                "id": next_id(),
                "slot": font_name,
                "page": None,
                "audit": "font_audit",
                "severity": "missing",
                "classification": "converter-bug",
                "converter_path": "tools/idml_to_dsl.py:_emit_styles",
                "suggested_action": (
                    f"Font {font_name!r} not embedded in preview; verify "
                    f"the converter is emitting the right FontName."
                ),
                "regression_test_path": "tests/unit/test_font_audit.py",
            }
        )
    return out


def _issues_from_run_style(rsa: dict | None, next_id) -> list[dict]:
    if not rsa:
        return []
    out: list[dict] = []
    for drift in (rsa.get("style_drifts") or []):
        cls = "human-review"
        baseline = drift.get("baseline") or {}
        preview = drift.get("preview") or {}
        drift_block = drift.get("drift") or {}
        if drift_block.get("fontname"):
            cls = "converter-bug"
        out.append(
            {
                "id": next_id(),
                "slot": drift.get("text"),
                "page": drift.get("page"),
                "audit": "run_style_audit",
                "severity": drift.get("severity", ""),
                "classification": cls,
                "converter_path": (
                    "tools/idml_to_dsl.py:_emit_runs"
                    if cls == "converter-bug" else ""
                ),
                "suggested_action": (
                    "Run font name mismatches baseline; investigate font "
                    "resolution in the converter."
                    if cls == "converter-bug"
                    else "Run-style drift; triage by hand."
                ),
                "regression_test_path": "",
            }
        )
    return out


def _issues_from_line_spacing(lsa: dict | None, next_id) -> list[dict]:
    if not lsa:
        return []
    # F-017: E2 (line_spacing_audit) is informational-only. When the YAML
    # carries informational_only=true we do NOT surface its drifts here —
    # E4 (line_spacing_pixel_audit) is the canonical signal and gets its
    # own extractor below.
    if lsa.get("informational_only"):
        return []
    out: list[dict] = []
    for drift in (lsa.get("drifts") or lsa.get("line_spacing_drifts") or []):
        drift_pt = drift.get("delta_pt")
        if drift_pt is None or abs(float(drift_pt)) <= 0.5:
            continue
        out.append(
            {
                "id": next_id(),
                "slot": drift.get("anname"),
                "page": drift.get("page"),
                "audit": "line_spacing_audit",
                "severity": "drift",
                "classification": "converter-bug",
                "converter_path": "tools/idml_to_dsl.py:_emit_paragraph_styles",
                "suggested_action": (
                    "CSR Leading vs rendered line spacing mismatch; the "
                    "converter likely emitted IDML Leading verbatim without "
                    "Aki composition compensation."
                ),
                "regression_test_path": "tests/unit/test_line_spacing_audit.py",
            }
        )
    return out


def _issues_from_line_spacing_pixel(lspa: dict | None, next_id) -> list[dict]:
    """Audit-reliability review item 4: surface E4 (pixel-level line-
    spacing) drifts as canonical line-spacing signal.

    Schema: ``rows: [{anname, max_drift_pt, ...}]``. Any frame with
    ``|max_drift_pt| > 1.0`` is a real per-frame issue; below that
    threshold is sub-perceptible drift and gets dropped to ``minor`` by
    the leverage stage."""
    if not lspa:
        return []
    out: list[dict] = []
    for row in lspa.get("rows") or []:
        try:
            d = float(row.get("max_drift_pt") or 0.0)
        except (TypeError, ValueError):
            continue
        if abs(d) <= 1.0:
            continue
        out.append({
            "id": next_id(),
            "slot": row.get("anname"),
            "page": row.get("page"),
            "audit": "line_spacing_pixel_audit",
            "severity": "drift",
            "classification": "converter-bug" if abs(d) > 3.0 else "human-review",
            "converter_path": "templates/<slug>/build.py (per-Run paragraph_attrs)",
            "suggested_action": (
                f"Pixel-level drift {d:+.2f}pt — run "
                "tools/line_spacing_sim.py with the frame's anname to "
                "find a leading override that lands close to 0pt drift."
            ),
            "regression_test_path": (
                "tests/unit/test_line_spacing_pixel_audit.py"
            ),
        })
    return out


def _issues_from_image_visibility(ifv: dict | None, next_id) -> list[dict]:
    """Audit-reliability review item 4: surface E5 (image-frame
    visibility) findings — invisible frames are critical."""
    if not ifv:
        return []
    out: list[dict] = []
    # Invisible frames: visibility_ratio < 0.3 (per audit's schema).
    for row in ifv.get("invisible_frames") or []:
        if isinstance(row, str):
            anname, ratio = row, None
        else:
            anname = row.get("anname") if isinstance(row, dict) else None
            ratio = row.get("visibility_ratio") if isinstance(row, dict) else None
        if not anname:
            continue
        out.append({
            "id": next_id(),
            "slot": anname,
            "page": None,
            "audit": "image_frame_visibility_audit",
            "severity": "invisible",
            "classification": "converter-bug",
            "converter_path": "tools/sla_lib/builder/primitives.py (ImageFrame emit)",
            "suggested_action": (
                f"Frame {anname!r} is mostly background in preview "
                f"(visibility_ratio={ratio}); switch from inline_image_data "
                "to direct image= reference with scale_type=0."
            ),
            "regression_test_path": (
                "tests/unit/test_image_frame_visibility_audit.py"
            ),
        })
    return out


def _issues_from_per_region_regression(prr: dict | None, next_id) -> list[dict]:
    """Audit-reliability review item 4: surface E6 (per-region
    regression vs previous render) findings.

    These are the "did this commit silently regress a frame that was
    previously fine?" signals — high-leverage to surface in the review.
    """
    if not prr:
        return []
    # Seeded runs don't have comparison data.
    if prr.get("seeded"):
        return []
    out: list[dict] = []
    for reg in prr.get("regressions") or []:
        kind = reg.get("kind", "")
        anname = reg.get("anname")
        if not anname:
            continue
        # Brief action message per regression kind.
        if "line_spacing" in kind:
            prev = reg.get("prev_max_drift_pt")
            curr = reg.get("curr_max_drift_pt")
            action = (
                f"Frame {anname!r} drift regressed from "
                f"{prev}pt → {curr}pt since the previous render."
            )
        elif "visibility" in kind:
            prev = reg.get("prev_visibility_ratio")
            curr = reg.get("curr_visibility_ratio")
            action = (
                f"Frame {anname!r} visibility dropped from "
                f"{prev} → {curr} since the previous render."
            )
        else:
            action = f"Frame {anname!r}: {kind}"
        out.append({
            "id": next_id(),
            "slot": anname,
            "page": None,
            "audit": "per_region_regression",
            "severity": kind,
            "classification": "converter-bug",
            "converter_path": "",
            "suggested_action": action,
            "regression_test_path": (
                "tests/unit/test_per_region_regression_check.py"
            ),
        })
    return out


def _issues_from_asset_audit(aa: dict | None, next_id) -> list[dict]:
    if not aa or aa.get("ok"):
        return []
    out: list[dict] = []
    for bn in aa.get("links_missing") or []:
        out.append(
            {
                "id": next_id(),
                "slot": bn,
                "page": None,
                "audit": "asset_extraction",
                "severity": "missing_link",
                "classification": "authoring-bug",
                "converter_path": "",
                "suggested_action": (
                    f"Link {bn!r} referenced by IDML but missing from Links/. "
                    "Re-export from InDesign with Package or copy it manually."
                ),
                "regression_test_path": "",
            }
        )
    for bn in aa.get("links_unconverted") or []:
        out.append(
            {
                "id": next_id(),
                "slot": bn,
                "page": None,
                "audit": "asset_extraction",
                "severity": "unconverted",
                "classification": "converter-bug",
                "converter_path": "tools/links_export.py",
                "suggested_action": (
                    f"Link {bn!r} present in Links/ but no manifest entry; "
                    "re-run tools/links_export.py."
                ),
                "regression_test_path": "",
            }
        )
    for finding in aa.get("composite_ai_detected") or []:
        out.append(
            {
                "id": next_id(),
                "slot": finding.get("path"),
                "page": None,
                "audit": "asset_extraction",
                "severity": "composite_ai",
                "classification": "converter-bug",
                "converter_path": "tools/composite_ai_split.py",
                "suggested_action": (
                    "Composite-AI detected; run tools/composite_ai_split.py "
                    "to emit per-page PDFs, then --reimport."
                ),
                "regression_test_path": "",
            }
        )
    return out


# ---------------------------------------------------------------------------
# Review builder.
# ---------------------------------------------------------------------------


def build_review(
    slug: str,
    validation_dir: Path,
    *,
    min_drift_pp: float = 0.5,
    idml_path: Path | None = None,
) -> dict:
    """Read every audit artifact and produce the review dict."""
    audits = _load_all(validation_dir)
    next_id = _next_id_factory()

    issues: list[dict] = []
    issues.extend(_issues_from_region_color(audits["region_color_audit"], next_id))
    issues.extend(_issues_from_text_position(
        audits["text_position_audit"], next_id, idml_path
    ))
    issues.extend(_issues_from_diff_bboxes(
        audits["diff_bboxes"], audits["inventory"], next_id
    ))
    issues.extend(_issues_from_font_audit(audits["font_audit"], next_id))
    issues.extend(_issues_from_run_style(audits["run_style_audit"], next_id))
    issues.extend(_issues_from_line_spacing(
        audits["line_spacing_audit"], next_id
    ))
    # Audit-reliability review item 4: E4/E5/E6 are now first-class issue
    # sources alongside the legacy audits.
    issues.extend(_issues_from_line_spacing_pixel(
        audits["line_spacing_pixel_audit"], next_id
    ))
    issues.extend(_issues_from_image_visibility(
        audits["image_frame_visibility_audit"], next_id
    ))
    issues.extend(_issues_from_per_region_regression(
        audits["per_region_regression"], next_id
    ))
    issues.extend(_issues_from_asset_audit(audits["asset_audit"], next_id))

    # Leverage scoring.
    per_drift = audits["per_element_drift"]
    # Audit-reliability item 4: E4/E5/E6 findings are per-frame measured
    # signals, not page-mismatch derivatives. They shouldn't be silenced
    # by the page-mismatch leverage threshold the way diff_bboxes drifts
    # can be. Add them to the leverage-exempt set alongside asset_extraction
    # and font_audit.
    leverage_exempt = {
        "asset_extraction",
        "font_audit",
        "line_spacing_pixel_audit",
        "image_frame_visibility_audit",
        "per_region_regression",
    }
    for i in issues:
        drop = _est_drift_drop(i, per_drift)
        i["est_drift_drop"] = round(drop, 3)
        if drop < min_drift_pp:
            if i["audit"] not in leverage_exempt:
                i["classification"] = "minor"

    # Sort.
    def _sort_key(i: dict):
        return (
            -float(i.get("est_drift_drop") or 0.0),
            _SEVERITY_RANK.get(i.get("classification", "human-review"), 99),
            str(i.get("slot") or ""),
        )

    issues.sort(key=_sort_key)

    hot_issues_by_leverage = [
        i for i in issues if i["classification"] != "minor"
    ]

    preflight = audits["preflight"] or {}
    preflight_ok = bool(preflight.get("ok", False))
    verdict = _verdict(preflight_ok, issues)

    # Extract drift metrics from visual_diff.
    drift_p1 = drift_p2 = drift_p1_max = drift_p2_max = None
    vd = audits["visual_diff"] or {}
    for page in vd.get("pages") or []:
        mismatch = float(page.get("mismatch_pct") or 0.0)
        if page.get("page") in (1, "1"):
            drift_p1 = mismatch
        elif page.get("page") in (2, "2"):
            drift_p2 = mismatch
    vdr = audits["visual_diff_regions"] or {}
    for page in vdr.get("pages") or []:
        hot = page.get("hot_regions") or []
        max_pct = max(
            (float(r.get("mismatch_pct") or 0.0) for r in hot),
            default=0.0,
        )
        if page.get("page") in (1, "1"):
            drift_p1_max = max_pct
        elif page.get("page") in (2, "2"):
            drift_p2_max = max_pct

    audits_run = sorted(
        name for name, val in audits.items() if val is not None
    )

    return {
        "template": slug,
        "preflight_ok": preflight_ok,
        "verdict": verdict,
        "issues": issues,
        "hot_issues_by_leverage": hot_issues_by_leverage,
        "drift": {
            "p1": drift_p1,
            "p2": drift_p2,
            "p1_max_region": drift_p1_max,
            "p2_max_region": drift_p2_max,
        },
        "audits_run": audits_run,
    }


def _verdict(preflight_ok: bool, issues: list[dict]) -> str:
    if preflight_ok:
        return "PASS"
    open_issues = [i for i in issues if i.get("classification") != "minor"]
    if not open_issues:
        return "PASS"
    if all(i.get("classification") == "authoring-bug" for i in open_issues):
        return "BLOCKED_BY_AUTHORING"
    return "NEEDS_WORK"


# ---------------------------------------------------------------------------
# Output formats.
# ---------------------------------------------------------------------------


def _format_md(review: dict) -> str:
    lines: list[str] = [
        f"# Convergence Review — {review['template']}",
        "",
        f"**Verdict:** {review.get('verdict', '?')}",
        f"**Preflight OK:** {review.get('preflight_ok', False)}",
        "",
    ]
    issues = review.get("issues") or []
    open_issues = [i for i in issues if i.get("classification") != "minor"]
    minor = [i for i in issues if i.get("classification") == "minor"]
    lines.append(f"**Open issues:** {len(open_issues)} (plus {len(minor)} minor)")
    lines.append("")
    if open_issues:
        lines.append("## Hot Issues by Leverage")
        for i in open_issues:
            lines.append(
                f"- [{i.get('classification')}] {i.get('slot') or '?'} "
                f"(audit: {i.get('audit')}, "
                f"est_drift_drop: {i.get('est_drift_drop', 0.0)}pp)"
            )
            if i.get("converter_path"):
                lines.append(f"  - converter: {i['converter_path']}")
            if i.get("suggested_action"):
                lines.append(f"  - action: {i['suggested_action']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _format_json(review: dict) -> str:
    return json.dumps(review, indent=2, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="convergence-review",
        description=(
            "Classify + leverage-sort audit issues for a template slug. "
            "Reads build/validation/<slug>/* and emits a review."
        ),
    )
    parser.add_argument("slug", help="Template slug.")
    parser.add_argument(
        "--format",
        choices=("md", "json"),
        default="md",
        help="Output format (default: md).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write to this file instead of stdout.",
    )
    parser.add_argument(
        "--min-drift-pp",
        type=float,
        default=0.5,
        help="Issues below this drift-drop leverage are flagged as 'minor'.",
    )
    parser.add_argument(
        "--idml",
        type=Path,
        default=None,
        help=(
            "Optional path to the IDML; enables classification of "
            "text-position drifts that need IDML XPath introspection."
        ),
    )
    parser.add_argument(
        "--validation-dir",
        type=Path,
        default=None,
        help="Override build/validation/<slug>/ (for tests).",
    )
    args = parser.parse_args(argv)

    validation_dir = args.validation_dir or (
        ROOT / "build" / "validation" / args.slug
    )
    review = build_review(
        slug=args.slug,
        validation_dir=validation_dir,
        min_drift_pp=args.min_drift_pp,
        idml_path=args.idml,
    )
    rendered = _format_md(review) if args.format == "md" else _format_json(review)
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")
    return 0 if review.get("preflight_ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
