#!/usr/bin/env python3
"""tools/baseline_text_audit.py — PDF baseline text vs build.py TextFrame runs.

Runs pdftotext -layout on the baseline PDF, extracts unique non-empty lines per
page, and greps each line against all TextFrame run text literals in build.py.

Lines present in the baseline PDF but not matched in build.py are surfaced as
potential dropped text content.

Matching is normalised (strip punctuation + lowercase) with difflib for
similarity scoring. A line is "matched" when any build.py run text contains it
at >= 60% similarity; the best match's anname is recorded.

Emits text_audit.yml.

CLI:
    python3 tools/baseline_text_audit.py \\
        --baseline templates/<slug>/baseline.pdf \\
        --build-py templates/<slug>/build.py \\
        --out text_audit.yml

Exit code: 0 always (informational tool).
"""
from __future__ import annotations

import argparse
import ast
import difflib
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import yaml

# Minimum similarity ratio (0..1) to record a nearest-match.
MIN_SIMILARITY = 0.60

# Minimum line length (chars after stripping) to audit. Short lines like "•"
# or single letters create noisy false positives.
MIN_LINE_LEN = 3


def _run_pdftotext(pdf_path: Path, page: int) -> str:
    """Run pdftotext -layout on a single page (1-indexed) and return stdout."""
    r = subprocess.run(
        [
            "pdftotext",
            "-layout",
            "-f", str(page),
            "-l", str(page),
            str(pdf_path),
            "-",
        ],
        capture_output=True,
        text=True,
    )
    return r.stdout


def _get_page_count(pdf_path: Path) -> int:
    """Return the number of pages in the PDF using pdfinfo."""
    r = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        capture_output=True,
        text=True,
    )
    for line in r.stdout.splitlines():
        if line.lower().startswith("pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
    # Fallback: try pdftotext on incrementing pages until empty
    for n in range(1, 50):
        if not _run_pdftotext(pdf_path, n).strip():
            return n - 1
    return 0


def _normalise(text: str) -> str:
    """Lowercase and strip punctuation for fuzzy matching."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_lines_from_page(raw_text: str) -> list[str]:
    """Return unique non-empty lines from pdftotext output, normalised whitespace.

    pdftotext -layout places text from multiple columns on the same raw line,
    separated by large whitespace gaps (3+ spaces). We split each raw line on
    multi-space gaps so that column-separated text segments are audited
    individually. This catches narrow text like attribution names that would
    otherwise be merged into a long lorem-ipsum line.
    """
    seen: set[str] = set()
    result: list[str] = []
    for raw_line in raw_text.splitlines():
        # Split on 3+ consecutive whitespace chars to separate columns
        segments = re.split(r"\s{3,}", raw_line)
        for seg in segments:
            line = seg.strip()
            if len(line) < MIN_LINE_LEN:
                continue
            if line in seen:
                continue
            seen.add(line)
            result.append(line)
    return result


def _extract_run_texts_from_build_py(build_py_path: Path) -> dict[str, list[str]]:
    """Return {anname: [run_text, ...]} from Run(text=...) in build.py.

    Uses regex to find:
      anname='uXXX'  (or "uXXX")
      runs=[Run(text='...'), ...]

    Parses literal string values only; ignores dynamic expressions.
    """
    text = build_py_path.read_text(encoding="utf-8")

    # Build a map: anname -> list of run texts.
    # Strategy: find each TextFrame block by locating anname= and then runs=[...].
    # We use a simplified AST walk by finding function calls with keyword args.
    result: dict[str, list[str]] = {}

    # Regex to find TextFrame(...) calls — captures the full argument span.
    # We'll scan character by character to find balanced parentheses.
    anname_re = re.compile(r"anname=['\"]([^'\"]+)['\"]")
    run_text_re = re.compile(r"Run\s*\(\s*text=['\"]([^'\"]*)['\"]")

    # Split by TextFrame( or ImageFrame( occurrences
    frame_re = re.compile(
        r"(TextFrame|ImageFrame)\s*\(",
        re.DOTALL,
    )

    pos = 0
    for m in frame_re.finditer(text):
        frame_type = m.group(1)
        if frame_type != "TextFrame":
            continue
        start = m.end() - 1  # position of the opening (
        # Find the matching closing )
        depth = 0
        i = start
        while i < len(text):
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        frame_text = text[start : i + 1]

        anname_m = anname_re.search(frame_text)
        if not anname_m:
            continue
        anname = anname_m.group(1)

        run_texts: list[str] = []
        for rt_m in run_text_re.finditer(frame_text):
            t = rt_m.group(1)
            # Unescape Python string escapes (basic)
            try:
                t = ast.literal_eval(f'"{t}"')
            except Exception:
                pass
            if t.strip():
                run_texts.append(t)

        if run_texts:
            result[anname] = run_texts

    return result


def _find_nearest_match(
    line: str,
    normalised_line: str,
    run_texts_by_anname: dict[str, list[str]],
) -> tuple[Optional[str], int]:
    """Return (anname, similarity_pct) for the best matching TextFrame run, or (None, 0)."""
    best_anname: Optional[str] = None
    best_ratio = 0.0

    for anname, run_texts in run_texts_by_anname.items():
        for run_text in run_texts:
            norm_run = _normalise(run_text)
            if not norm_run:
                continue
            # Check substring containment first (fast path)
            if normalised_line in norm_run or norm_run in normalised_line:
                ratio = 1.0
            else:
                ratio = difflib.SequenceMatcher(
                    None, normalised_line, norm_run, autojunk=False
                ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_anname = anname

    if best_ratio >= MIN_SIMILARITY:
        return best_anname, round(best_ratio * 100)
    return None, 0


def _is_line_matched(
    normalised_line: str,
    run_texts_by_anname: dict[str, list[str]],
) -> bool:
    """Return True if any run text matches the normalised line at >= MIN_SIMILARITY."""
    for run_texts in run_texts_by_anname.values():
        for run_text in run_texts:
            norm_run = _normalise(run_text)
            if not norm_run:
                continue
            if normalised_line in norm_run or norm_run in normalised_line:
                return True
            ratio = difflib.SequenceMatcher(
                None, normalised_line, norm_run, autojunk=False
            ).ratio()
            if ratio >= MIN_SIMILARITY:
                return True
    return False


def run_text_audit(
    baseline_pdf: Path,
    build_py_path: Path,
    template: Optional[str] = None,
) -> dict:
    """Run the text audit and return the report dict."""
    if template is None:
        template = build_py_path.parent.name

    run_texts_by_anname = _extract_run_texts_from_build_py(build_py_path)
    page_count = _get_page_count(baseline_pdf)

    pages_out: list[dict] = []
    for page_idx in range(page_count):
        page_num = page_idx + 1  # 1-indexed for pdftotext
        raw_text = _run_pdftotext(baseline_pdf, page_num)
        lines = _extract_lines_from_page(raw_text)

        matched_count = 0
        unmatched: list[dict] = []

        for line in lines:
            norm = _normalise(line)
            if not norm:
                matched_count += 1
                continue

            if _is_line_matched(norm, run_texts_by_anname):
                matched_count += 1
            else:
                # Find nearest match for the report
                nearest_anname, sim_pct = _find_nearest_match(
                    line, norm, run_texts_by_anname
                )
                entry: dict = {"line": line}
                if nearest_anname is not None:
                    entry["nearest_match"] = {
                        "anname": nearest_anname,
                        "similarity_pct": sim_pct,
                    }
                    if sim_pct == 100:
                        entry["hint"] = "matches multiple TextFrames; verify"
                    else:
                        entry["hint"] = (
                            f"partial match ({sim_pct}%) with {nearest_anname}; "
                            "may be from a multi-line merge"
                        )
                else:
                    entry["nearest_match"] = None
                    entry["hint"] = "no TextFrame run contains this text"
                unmatched.append(entry)

        page_entry: dict = {
            "page": page_idx,
            "lines_total": len(lines),
            "lines_matched": matched_count,
        }
        if unmatched:
            page_entry["lines_unmatched"] = unmatched
        pages_out.append(page_entry)

    report: dict = {
        "template": template,
        "baseline_pdf": str(baseline_pdf),
        "build_py_path": str(build_py_path),
        "pages": pages_out,
    }
    return report


def _yaml_dump(data: dict) -> str:
    return yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=True,
        width=120,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="baseline_text_audit",
        description="Audit baseline PDF text vs build.py TextFrame run text.",
    )
    parser.add_argument(
        "--baseline", required=True, type=Path, help="Baseline PDF path"
    )
    parser.add_argument(
        "--build-py", required=True, type=Path, help="build.py path"
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="Output YAML file path"
    )
    parser.add_argument(
        "--template", default=None, help="Template slug (default: parent dir of build.py)"
    )
    args = parser.parse_args(argv)

    if not args.baseline.exists():
        print(f"ERROR: baseline PDF not found: {args.baseline}", file=sys.stderr)
        return 1
    if not args.build_py.exists():
        print(f"ERROR: build.py not found: {args.build_py}", file=sys.stderr)
        return 1

    report = run_text_audit(args.baseline, args.build_py, template=args.template)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_yaml_dump(report), encoding="utf-8")
    print(f"text_audit written → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
