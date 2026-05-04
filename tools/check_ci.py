#!/usr/bin/env python3
"""Brand-identity drift validator for Scribus SLA files.

Loads shared/ci.yml as the canonical brand definition, walks one or more
target SLA files, and reports drift:

- critical : a brand color is missing or has a different colorspace/value
            (e.g. RGB-Green leaked in)
- warning  : a color or style appears in the SLA but not in CI
- info     : minor name or attribute mismatches

Exit code is 0 if every target is clean, 1 if any drift was found.

Usage:
    tools/check_ci.py templates/postkarte-a6-kampagne/template.sla
    tools/check_ci.py "Postkarte Vorlage.sla" "Plakat A1 Hochformat_Vorlage.sla"
    tools/check_ci.py --ci-file shared/ci.yml --json target1.sla target2.sla
"""
from __future__ import annotations
import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

import yaml
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CI = ROOT / "shared" / "ci.yml"


SEVERITY_CRITICAL = "critical"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    detail: dict = field(default_factory=dict)

    def short(self) -> str:
        return f"[{self.severity}] {self.code}: {self.message}"


@dataclass
class CIDriftReport:
    target: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        return any(i.severity == SEVERITY_CRITICAL for i in self.issues)

    @property
    def has_any(self) -> bool:
        return bool(self.issues)


def load_ci(ci_file: Path) -> dict:
    with ci_file.open() as f:
        ci = yaml.safe_load(f)
    if "colors" not in ci or "styles" not in ci:
        raise ValueError(f"{ci_file}: missing colors/styles top-level keys")
    return ci


def _expected_color_attrs(name: str, spec: dict) -> dict:
    attrs = {"NAME": name}
    cmyk = spec.get("cmyk")
    rgb = spec.get("rgb")
    if cmyk is not None:
        c, m, y, k = cmyk
        attrs.update({
            "SPACE": "CMYK",
            "C": str(c),
            "M": str(m),
            "Y": str(y),
            "K": str(k),
        })
    elif rgb is not None:
        r, g, b = rgb
        attrs.update({
            "SPACE": "RGB",
            "R": str(r),
            "G": str(g),
            "B": str(b),
        })
    if spec.get("register"):
        attrs["Register"] = "1"
    return attrs


def _color_matches(elem: etree._Element, expected: dict) -> tuple[bool, list[str]]:
    """Compare a SLA <COLOR/> against the expected CI definition.

    Returns (ok, mismatch_keys). Numeric attrs are compared as strings
    because Scribus emits exact integer strings for CMYK/RGB.
    """
    mismatched = []
    for k, v in expected.items():
        if k == "Register":
            # Register is optional in SLA emission only when set
            if elem.attrib.get(k, "0") not in (v, "1"):
                mismatched.append(k)
            continue
        actual = elem.attrib.get(k)
        if actual != v:
            mismatched.append(k)
    return (not mismatched, mismatched)


def _scan_colors(doc_elem: etree._Element, ci: dict, report: CIDriftReport) -> None:
    ci_colors = ci["colors"]
    seen_names: set[str] = set()
    for color in doc_elem.findall("COLOR"):
        name = color.attrib.get("NAME", "")
        seen_names.add(name)
        if name not in ci_colors:
            report.issues.append(Issue(
                severity=SEVERITY_WARNING,
                code="extra-color",
                message=f"color '{name}' not in CI",
                detail={"name": name, "space": color.attrib.get("SPACE", "")},
            ))
            continue
        expected = _expected_color_attrs(name, ci_colors[name])
        ok, mismatches = _color_matches(color, expected)
        if not ok:
            report.issues.append(Issue(
                severity=SEVERITY_CRITICAL,
                code="color-drift",
                message=(
                    f"color '{name}' has wrong values "
                    f"(expected {expected}, mismatched keys {mismatches})"
                ),
                detail={
                    "name": name,
                    "expected": expected,
                    "actual": dict(color.attrib),
                    "mismatched": mismatches,
                },
            ))

    for name in ci_colors:
        if name not in seen_names:
            # Missing brand colors are info, not critical — a Postkarte
            # template may legitimately not need every brand color.
            # But missing primary brand color is critical.
            severity = (
                SEVERITY_CRITICAL
                if ci_colors[name].get("role") == "brand-primary"
                else SEVERITY_INFO
            )
            report.issues.append(Issue(
                severity=severity,
                code="missing-color",
                message=f"CI color '{name}' not present",
                detail={"name": name},
            ))


def _scan_styles(doc_elem: etree._Element, ci: dict, report: CIDriftReport) -> None:
    ci_styles = ci["styles"]
    for style in doc_elem.findall("STYLE"):
        name = style.attrib.get("NAME", "")
        if name in ci_styles:
            continue
        # Default-Paragraph style is a Scribus internal — info only.
        if name.startswith("Default Paragraph Style"):
            report.issues.append(Issue(
                severity=SEVERITY_INFO,
                code="scribus-default-style",
                message=f"Scribus default style '{name}' present",
                detail={"name": name},
            ))
            continue
        report.issues.append(Issue(
            severity=SEVERITY_WARNING,
            code="extra-style",
            message=f"style '{name}' not in CI (legacy or template-local)",
            detail={
                "name": name,
                "font": style.attrib.get("FONT", ""),
                "fontsize": style.attrib.get("FONTSIZE", ""),
                "fcolor": style.attrib.get("FCOLOR", ""),
            },
        ))


def check_sla(sla_path: Path, ci: dict) -> CIDriftReport:
    report = CIDriftReport(target=str(sla_path))
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(sla_path), parser)
    doc_elem = tree.getroot().find("DOCUMENT")
    if doc_elem is None:
        report.issues.append(Issue(
            severity=SEVERITY_CRITICAL,
            code="not-an-sla",
            message="no DOCUMENT element",
        ))
        return report
    _scan_colors(doc_elem, ci, report)
    _scan_styles(doc_elem, ci, report)
    return report


def format_report_text(reports: list[CIDriftReport]) -> str:
    lines: list[str] = []
    for r in reports:
        lines.append(f"=== {r.target} ===")
        if not r.issues:
            lines.append("  clean — no CI drift")
            continue
        for issue in sorted(r.issues, key=lambda i: (
            {"critical": 0, "warning": 1, "info": 2}[i.severity], i.code,
        )):
            lines.append(f"  {issue.short()}")
    return "\n".join(lines)


def format_report_json(reports: list[CIDriftReport]) -> str:
    out = []
    for r in reports:
        out.append({
            "target": r.target,
            "clean": not r.has_any,
            "issues": [asdict(i) for i in r.issues],
        })
    return json.dumps(out, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Brand drift validator for SLAs.")
    ap.add_argument("targets", nargs="+", type=Path)
    ap.add_argument("--ci-file", type=Path, default=DEFAULT_CI)
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on warnings too (default: only on critical).",
    )
    args = ap.parse_args(argv)

    ci = load_ci(args.ci_file)
    reports = [check_sla(t, ci) for t in args.targets]
    if args.json:
        print(format_report_json(reports))
    else:
        print(format_report_text(reports))

    has_critical = any(r.has_critical for r in reports)
    has_warning = any(
        any(i.severity == SEVERITY_WARNING for i in r.issues) for r in reports
    )
    if has_critical or (args.strict and has_warning):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
