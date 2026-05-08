#!/usr/bin/env python3
"""Spec-vs-Build drift detector (D3 + P-SPEC-1).

Reads a template's spec under templates/_specs/<slug>.md, parses the embedded
``slots:`` YAML block, opens templates/<slug>/template.sla, and diffs each
slot's coords against the SLA's PAGEOBJECT entries.

Usage::

    tools/spec_check.py SLUG                    # check one template
    tools/spec_check.py --all                   # check all under templates/_specs/
    tools/spec_check.py --tolerance-mm 0.1      # tighten default 0.5mm tolerance

Severity buckets (Issue #12, CONTEXT D8):
- drift < 0.05mm      : silent (sub-pixel float-precision noise; not reported)
- 0.05 <= d <= tol    : info (logged; non-blocking)
- d > tolerance       : error (logged; exit 1)

The default tolerance is 0.5mm — typography and frame placement at print
scale tolerates this comfortably. Pass --tolerance-mm 0.1 for the legacy
build-loop refinement scale.

Exit 0 on no errors (info-only is OK), 1 on any error.

Skip rules:
- Slots whose ``anname`` starts with ``internal:`` or ``_`` are ignored on the
  SLA side (DSL-internal frames).
- Retro-spec files (prefixed ``_existing-``) are skipped — they validate the
  schema, not a build.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

import yaml
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "templates" / "_specs"
TEMPLATES_DIR = ROOT / "templates"

PT_PER_MM = 72.0 / 25.4


def _extract_yaml_block(spec_md: str) -> dict:
    """Extract the embedded YAML block from a spec markdown file.

    The spec's ``slots:`` YAML lives inside a fenced ``` ```yaml ``` block
    that contains a top-level ``slots:`` key. We concatenate all such blocks
    (some specs split slots into front/back chunks) and merge.
    """
    pattern = re.compile(r"```yaml\n(.*?)```", re.DOTALL)
    merged = {"slots": []}
    for match in pattern.finditer(spec_md):
        try:
            block = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            continue
        if isinstance(block, dict):
            slots = block.get("slots")
            if isinstance(slots, list):
                merged["slots"].extend(slots)
            # Capture top-level fields too (id, format, etc.)
            for k, v in block.items():
                if k != "slots":
                    merged.setdefault(k, v)
    return merged


def _load_spec_slots(spec_path: Path) -> list[dict]:
    text = spec_path.read_text(encoding="utf-8")
    block = _extract_yaml_block(text)
    return block.get("slots") or []


def _sla_pageobjects(sla_path: Path) -> list[dict]:
    """Return [{anname, x_mm, y_mm, w_mm, h_mm, fcolor, layer}, ...] from SLA."""
    tree = etree.parse(str(sla_path))
    doc = tree.getroot().find("DOCUMENT")
    pages = doc.findall("PAGE")
    if not pages:
        return []
    page0 = pages[0]
    page_x = float(page0.attrib["PAGEXPOS"])
    page_y = float(page0.attrib["PAGEYPOS"])
    out = []
    for po in doc.findall("PAGEOBJECT"):
        anname = po.attrib.get("ANNAME", "")
        if not anname:
            continue
        if anname.startswith(("internal:", "_")):
            continue
        own = int(po.attrib.get("OwnPage", "0"))
        # Each page has its own xpos
        if own < len(pages):
            px = float(pages[own].attrib["PAGEXPOS"])
            py = float(pages[own].attrib["PAGEYPOS"])
        else:
            px, py = page_x, page_y
        x_pt = float(po.attrib["XPOS"]) - px
        y_pt = float(po.attrib["YPOS"]) - py
        w_pt = float(po.attrib["WIDTH"])
        h_pt = float(po.attrib["HEIGHT"])
        out.append({
            "anname": anname,
            "x_mm": x_pt / PT_PER_MM,
            "y_mm": y_pt / PT_PER_MM,
            "w_mm": w_pt / PT_PER_MM,
            "h_mm": h_pt / PT_PER_MM,
            "fcolor": po.attrib.get("PCOLOR", ""),
            "layer": po.attrib.get("LAYER", ""),
            "own_page": own,
        })
    return out


_SILENT_THRESHOLD_MM = 0.05


def _classify(drift_mm: float, tolerance_mm: float) -> str:
    """Bucket a drift magnitude.

    Returns "silent" | "info" | "error".
    """
    if drift_mm < _SILENT_THRESHOLD_MM:
        return "silent"
    if drift_mm <= tolerance_mm:
        return "info"
    return "error"


def check(slug: str, tolerance_mm: float = 0.5) -> tuple[int, list[str]]:
    """Compare spec slots vs SLA frames. Returns (error_count, messages).

    Severity buckets (CONTEXT D8): drift below SILENT_THRESHOLD (0.05mm)
    is silent; below tolerance is "info:"; above is "error:" and counted
    toward the returned error_count.
    """
    spec_path = SPECS_DIR / f"{slug}.md"
    sla_path = TEMPLATES_DIR / slug / "template.sla"
    if not spec_path.exists():
        return 1, [f"error: spec not found: {spec_path}"]
    if not sla_path.exists():
        return 1, [f"error: sla not found: {sla_path}"]

    spec_slots = _load_spec_slots(spec_path)
    sla_frames = _sla_pageobjects(sla_path)

    # Build anname → frame mapping (allow duplicates by listing them)
    sla_by_anname: dict[str, list[dict]] = {}
    for f in sla_frames:
        sla_by_anname.setdefault(f["anname"], []).append(f)

    spec_annames = {s.get("anname", "") for s in spec_slots if s.get("anname")}
    sla_annames = set(sla_by_anname.keys())

    msgs: list[str] = []
    errors = 0

    # Anname-missing: in spec but not SLA
    for s in spec_slots:
        an = s.get("anname")
        if not an:
            continue
        if an not in sla_by_anname:
            msgs.append(f"error: [missing-in-sla] anname '{an}' in spec but not found in SLA")
            errors += 1
            continue
        # Geometry check: take first SLA frame with this anname
        # (multiple SLA frames sharing one anname is unusual but allowed)
        sf = sla_by_anname[an][0]
        for axis in ("x_mm", "y_mm", "w_mm", "h_mm"):
            spec_v = s.get(axis)
            if spec_v is None:
                continue
            try:
                spec_v = float(spec_v)
            except (TypeError, ValueError):
                continue
            sla_v = sf[axis]
            d = abs(spec_v - sla_v)
            severity = _classify(d, tolerance_mm)
            if severity == "silent":
                continue
            line = (
                f"{severity}: [drift] '{an}' {axis}: spec={spec_v:.2f} "
                f"sla={sla_v:.2f} (diff {d:.2f} {'>' if severity == 'error' else '<='} tol {tolerance_mm})"
            )
            msgs.append(line)
            if severity == "error":
                errors += 1

    # Anname-extra: in SLA but not spec (warning, not blocker — out-of-scope SLA frames)
    extra = sla_annames - spec_annames
    for an in sorted(extra):
        msgs.append(f"warn: [extra-in-sla] anname '{an}' in SLA but not declared in spec")

    return errors, msgs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Spec-vs-Build drift detector for template SLAs.",
    )
    ap.add_argument("slug", nargs="?", help="Template slug (e.g. themen-plakat-a3-quer)")
    ap.add_argument("--all", action="store_true",
                    help="Check every spec under templates/_specs/")
    ap.add_argument("--tolerance-mm", type=float, default=0.5,
                    help=("Per-axis tolerance in mm (default 0.5). Drifts "
                          "<0.05mm are silent; 0.05<=d<=tol are info; "
                          ">tol are error. Pass 0.1 for legacy behavior."))
    args = ap.parse_args(argv)

    if args.all:
        slugs = []
        for p in sorted(SPECS_DIR.glob("*.md")):
            name = p.stem
            if name == "SCHEMA" or name.startswith("_existing-"):
                continue
            slugs.append(name)
    else:
        if not args.slug:
            ap.print_help()
            return 0
        slugs = [args.slug]

    overall_errors = 0
    for slug in slugs:
        errors, msgs = check(slug, tolerance_mm=args.tolerance_mm)
        info_count = sum(1 for m in msgs if m.startswith("info:"))
        warn_count = sum(1 for m in msgs if m.startswith("warn:"))
        if errors > 0:
            print(f"DRIFT: {slug} ({errors} errors, {info_count} info)")
            for m in msgs:
                print(m)
            overall_errors += errors
        else:
            print(f"OK:    {slug} (0 errors, {info_count} info, {warn_count} extras)")
            for m in msgs:
                if m.startswith("info:"):
                    print(m)
            for m in [x for x in msgs if x.startswith("warn:")][:3]:
                print(m)
    return 1 if overall_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
