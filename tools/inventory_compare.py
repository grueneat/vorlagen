#!/usr/bin/env python3
"""tools/inventory_compare.py — deterministic gate over two ``SCAFFOLD_INVENTORY.yml``.

Pure set/count diff between an ``--expected`` snapshot (committed baseline)
and an ``--actual`` snapshot (freshly extracted). Emits an
``inventory_diff.yml`` with three sections:

- ``missing``: keys present in expected but absent in actual (REGRESSION)
- ``extra``: keys present in actual but absent in expected (drift)
- ``count_deltas``: per-bucket numeric deltas with a sign and the affected key

Exit codes (per CONTEXT.md "Comparison script"):

- ``0`` — perfect match
- ``2`` — any ``missing`` entry, OR any negative ``count_delta`` (regression)
- ``3`` — no missing, but at least one ``extra`` entry (drift, not regression)

Rows whose ``source`` is ``manual`` are exempt from the ``extra`` rule —
falz/PolyLine fold-line emissions have no IDML counterpart by design.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _frame_key_set(rows: list[dict], *, include_manual: bool = True) -> set[str]:
    """Return the set of frame keys (annames) in a frames bucket.

    When ``include_manual`` is False, rows tagged ``source: manual`` are
    excluded — used on the ``actual`` side so manual PolyLines don't
    trigger spurious extras.
    """
    out: set[str] = set()
    for r in rows or []:
        if not include_manual and r.get("source") == "manual":
            continue
        anname = r.get("anname") or ""
        if anname:
            out.add(anname)
    return out


def _color_set(rows: list[dict]) -> set[str]:
    return {r.get("idml") or "" for r in (rows or []) if r.get("idml")}


def _pstyle_set(rows: list[dict]) -> set[str]:
    return {r.get("idml") or "" for r in (rows or []) if r.get("idml")}


def _asset_set(rows: list[dict]) -> set[str]:
    return {r.get("basename") or "" for r in (rows or []) if r.get("basename")}


def _bucket_count_deltas(expected: dict, actual: dict, name: str) -> list[dict]:
    """For each ``by_paragraph_style`` entry, compare the numeric counts."""
    deltas: list[dict] = []
    exp_buckets = {b.get("style"): b for b in (expected.get(name, {}).get("by_paragraph_style") or [])}
    act_buckets = {b.get("style"): b for b in (actual.get(name, {}).get("by_paragraph_style") or [])}
    for style in sorted(set(exp_buckets) | set(act_buckets)):
        e = exp_buckets.get(style, {})
        a = act_buckets.get(style, {})
        for field in ("idml_count", "build_py_count", "sla_itext_count", "pdf_word_count"):
            ev = int(e.get(field) or 0)
            av = int(a.get(field) or 0)
            if ev != av:
                deltas.append({
                    "section": f"{name}.by_paragraph_style[{style!r}].{field}",
                    "expected": ev,
                    "actual": av,
                    "delta": av - ev,
                })
    return deltas


def compare(expected: dict, actual: dict) -> dict:
    """Compute a ``inventory_diff.yml``-shaped dict."""
    missing: dict[str, list[str]] = {}
    extra: dict[str, list[str]] = {}
    count_deltas: list[dict] = []

    # Per-frame-kind set diffs. ``actual.extra`` excludes ``source==manual`` to
    # avoid false-positive PolyLine fold-lines (RESEARCH.md pitfall #3).
    frame_kinds = ("text_frames", "image_frames", "polygon_frames", "group_frames")
    for kind in frame_kinds:
        exp_rows = (expected.get("frames") or {}).get(kind) or []
        act_rows = (actual.get("frames") or {}).get(kind) or []
        exp_set = _frame_key_set(exp_rows, include_manual=True)
        act_set = _frame_key_set(act_rows, include_manual=True)
        act_set_no_manual = _frame_key_set(act_rows, include_manual=False)
        miss = sorted(exp_set - act_set)
        ext = sorted(act_set_no_manual - exp_set)
        if miss:
            missing[f"frames.{kind}"] = miss
        if ext:
            extra[f"frames.{kind}"] = ext

    # paragraph_styles set.
    exp_ps = _pstyle_set(expected.get("paragraph_styles") or [])
    act_ps = _pstyle_set(actual.get("paragraph_styles") or [])
    miss = sorted(exp_ps - act_ps)
    ext = sorted(act_ps - exp_ps)
    if miss:
        missing["paragraph_styles"] = miss
    if ext:
        extra["paragraph_styles"] = ext

    # colors set.
    exp_c = _color_set(expected.get("colors") or [])
    act_c = _color_set(actual.get("colors") or [])
    miss = sorted(exp_c - act_c)
    ext = sorted(act_c - exp_c)
    if miss:
        missing["colors"] = miss
    if ext:
        extra["colors"] = ext
    # add_color name deltas (build.py side): missing add_color call is a regression.
    # Compare via the build_py_extra_color flag set per row.
    exp_bp_colors = {r.get("idml") for r in (expected.get("colors") or [])
                     if r.get("build_py_extra_color")}
    act_bp_colors = {r.get("idml") for r in (actual.get("colors") or [])
                     if r.get("build_py_extra_color")}
    bp_miss = sorted(exp_bp_colors - act_bp_colors)
    if bp_miss:
        missing.setdefault("colors.build_py", []).extend(bp_miss)

    # assets basenames.
    exp_a = _asset_set(expected.get("assets") or [])
    act_a = _asset_set(actual.get("assets") or [])
    miss = sorted(exp_a - act_a)
    ext = sorted(act_a - exp_a)
    if miss:
        missing["assets"] = miss
    if ext:
        extra["assets"] = ext

    # text_runs: text-set equality per paragraph style is too noisy; instead
    # we surface missing/extra at the WORD level via the words block AND
    # report any text-run bucket count drop in count_deltas.
    count_deltas.extend(_bucket_count_deltas(expected, actual, "text_runs"))

    # Top-level numeric fields.
    for key in ("words.preview_pdf_count", "words.baseline_pdf_count",
                "text_runs.total_idml"):
        ev = _get(expected, key)
        av = _get(actual, key)
        try:
            ev_i = int(ev or 0)
            av_i = int(av or 0)
        except (TypeError, ValueError):
            continue
        if ev_i != av_i:
            count_deltas.append({
                "section": key,
                "expected": ev_i,
                "actual": av_i,
                "delta": av_i - ev_i,
            })

    # Words: missing_from_preview / extra_in_preview on the actual side.
    act_missing_words = list(actual.get("words", {}).get("missing_from_preview") or [])
    act_extra_words = list(actual.get("words", {}).get("extra_in_preview") or [])
    if act_missing_words:
        missing["words.missing_from_preview"] = sorted(set(act_missing_words))
    if act_extra_words:
        extra["words.extra_in_preview"] = sorted(set(act_extra_words))
    # Words present in the expected text-run pool but absent from actual's
    # build.py text-run pool (covers "drop a Run(text=...) from build.py").
    exp_words = _extract_build_py_words(expected)
    act_words = _extract_build_py_words(actual)
    word_miss = sorted(exp_words - act_words)
    if word_miss:
        missing.setdefault("text_runs.missing", []).extend(word_miss)

    # Negative count delta is a regression (treat as missing).
    has_negative = any(d.get("delta", 0) < 0 for d in count_deltas)

    if missing or has_negative:
        exit_code = 2
    elif extra:
        exit_code = 3
    else:
        exit_code = 0

    return {
        "missing": missing,
        "extra": extra,
        "count_deltas": count_deltas,
        "summary": {
            "exit_code": exit_code,
            "missing_sections": list(missing.keys()),
            "extra_sections": list(extra.keys()),
            "delta_count": len(count_deltas),
        },
    }


def _extract_build_py_words(inv: dict) -> set[str]:
    """Return the set of build.py Run() text strings for an inventory.

    Lives at ``text_runs.build_py_runs`` (list of TextRun dataclasses). Used
    by the gate to detect "build.py dropped a word" mutations.
    """
    runs = (inv.get("text_runs") or {}).get("build_py_runs") or []
    return {r.get("text", "") for r in runs if r.get("text")}


def _get(d: dict, dotted: str) -> Any:
    cur: Any = d
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="inventory_compare",
        description=(
            "Compare two SCAFFOLD_INVENTORY.yml snapshots and emit "
            "inventory_diff.yml. Exit 0 on match, 2 on regression, 3 on drift."
        ),
    )
    parser.add_argument("--expected", required=True, type=Path,
                        help="Committed baseline SCAFFOLD_INVENTORY.yml")
    parser.add_argument("--actual", required=True, type=Path,
                        help="Freshly-extracted SCAFFOLD_INVENTORY.yml")
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Where to write inventory_diff.yml. Default: stdout.",
    )
    args = parser.parse_args(argv)

    expected = _load(args.expected)
    actual = _load(args.actual)
    diff = compare(expected, actual)
    yaml_text = yaml.safe_dump(diff, sort_keys=False, allow_unicode=True,
                               default_flow_style=False)
    if args.out is None:
        sys.stdout.write(yaml_text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(yaml_text, encoding="utf-8")
    return int(diff["summary"]["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
