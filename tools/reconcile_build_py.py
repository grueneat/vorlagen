#!/usr/bin/env python3
"""Apply inject.yml hand_patches to a converter-emitted build.py.generated
and emit the patched build.py (issue #38 Task 16).

CLI:
    python3 tools/reconcile_build_py.py <slug> [--check] [--quiet]

Workflow:
  1. Validate templates/<slug>/inject.yml against shared/inject.schema.yaml.
  2. Read templates/<slug>/build.py.generated (verbatim converter output).
  3. Apply each hand_patch in list order (last-wins on conflict).
     - 'set:' replaces the field value entirely.
     - 'delta:' parses the current numeric value, adds the delta, writes back.
  4. Insert an inline '# P5/inject (from inject.yml line N): <reason>'
     comment immediately before the mutated kwarg.
  5. Write to templates/<slug>/build.py.
  6. Redundancy detection: when an inject 'set:' equals the value already
     in build.py.generated, emit a warning to stderr.

Flags:
  --check : do NOT write; exit 0 if build.py matches the reconciled output,
            1 otherwise. For CI consumption.
  --quiet : suppress informational stderr lines.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Validation.
# ---------------------------------------------------------------------------


def _load_schema() -> dict:
    return yaml.safe_load(
        (ROOT / "shared" / "inject.schema.yaml").read_text(encoding="utf-8")
    )


def _validate(inject_data: dict) -> list[str]:
    """Return a list of error messages. Empty list means valid."""
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema package is required to validate inject.yml"]
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'/'.join(str(p) for p in err.absolute_path)}: {err.message}"
        for err in validator.iter_errors(inject_data)
    ]


# ---------------------------------------------------------------------------
# Patching.
# ---------------------------------------------------------------------------


def _find_call_block(
    source: str,
    element: str,
    anname: str,
) -> tuple[int, int] | None:
    """Find a Python emitter call by anname literal.

    Returns (start_line_idx, end_line_idx) of the multi-line constructor call.
    For our purposes, the start is the line containing the constructor name
    (e.g. 'page0.add(TextFrame(') and the end is the line containing the
    closing ')'. We treat it as "block from element name to first ')')'
    starting at column 0 after the opening line".
    """
    lines = source.splitlines(keepends=False)
    # Locate the line containing both the element type and the anname kwarg.
    # Multi-line emitter calls put `anname='<value>'` on its own line; the
    # constructor name is several lines earlier.
    anname_pat = re.compile(rf"\banname=['\"]{re.escape(anname)}['\"]")
    elem_pat = re.compile(rf"\b{re.escape(element)}\b\s*\(")
    candidates: list[tuple[int, int]] = []
    for i, line in enumerate(lines):
        if not anname_pat.search(line):
            continue
        # Walk backwards to find the element-opening line.
        for j in range(i, max(-1, i - 50), -1):
            if elem_pat.search(lines[j]):
                # Walk forward to find the closing ')' that ends this call.
                depth = 0
                k = j
                while k < len(lines):
                    depth += lines[k].count("(") - lines[k].count(")")
                    if depth <= 0 and "(" in lines[k] or depth == 0 and k > j:
                        # Found the line containing the matched close paren.
                        if k > j or lines[k].rstrip().endswith(")"):
                            candidates.append((j, k))
                            break
                    k += 1
                break
    if not candidates:
        return None
    # Return the first candidate (deterministic).
    return candidates[0]


_NUMERIC_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*$")


def _apply_set(
    lines: list[str],
    block: tuple[int, int],
    field: str,
    new_value: Any,
    comment: str,
) -> tuple[bool, str | None]:
    """Replace 'field=<expr>' inside the block. Returns (mutated, prev_value)."""
    start, end = block
    pat = re.compile(rf"^(\s*){re.escape(field)}\s*=\s*([^,\n]+?)(,?)\s*$")
    for i in range(start, end + 1):
        m = pat.match(lines[i])
        if not m:
            continue
        indent, prev_value, trailing_comma = m.group(1), m.group(2).strip(), m.group(3)
        repr_value = _repr_value(new_value)
        lines.insert(i, f"{indent}# {comment}")
        lines[i + 1] = f"{indent}{field}={repr_value}{trailing_comma}"
        return True, prev_value
    return False, None


def _apply_delta(
    lines: list[str],
    block: tuple[int, int],
    field: str,
    delta_value: float,
    comment: str,
) -> tuple[bool, str | None]:
    """Add delta to the numeric value of 'field=<expr>'. Returns (mutated, prev_value)."""
    start, end = block
    pat = re.compile(rf"^(\s*){re.escape(field)}\s*=\s*([^,\n]+?)(,?)\s*$")
    for i in range(start, end + 1):
        m = pat.match(lines[i])
        if not m:
            continue
        indent, prev_expr, trailing_comma = m.group(1), m.group(2).strip(), m.group(3)
        num_match = _NUMERIC_RE.match(prev_expr)
        if not num_match:
            continue
        prev_num = float(num_match.group(1))
        new_num = prev_num + float(delta_value)
        # Preserve int vs float representation: if original had no '.', stay int.
        if "." not in num_match.group(1):
            new_repr = str(int(new_num)) if new_num == int(new_num) else f"{new_num}"
        else:
            new_repr = f"{new_num}"
        lines.insert(i, f"{indent}# {comment}")
        lines[i + 1] = f"{indent}{field}={new_repr}{trailing_comma}"
        return True, str(prev_num)
    return False, None


def _repr_value(value: Any) -> str:
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, bool):
        return repr(value)
    if isinstance(value, (int, float)):
        return repr(value)
    return repr(value)


# ---------------------------------------------------------------------------
# Reconcile.
# ---------------------------------------------------------------------------


def reconcile(
    slug: str,
    *,
    repo_root: Path | None = None,
    quiet: bool = False,
) -> tuple[str, list[str]]:
    """Apply inject.yml entries; return (reconciled_source, warnings)."""
    if repo_root is None:
        repo_root = ROOT
    tdir = repo_root / "templates" / slug
    generated = tdir / "build.py.generated"
    inject = tdir / "inject.yml"
    if not generated.exists():
        raise FileNotFoundError(f"missing {generated}")
    source = generated.read_text(encoding="utf-8")
    if not inject.exists():
        return source, []
    data = yaml.safe_load(inject.read_text(encoding="utf-8")) or {}
    errors = _validate(data)
    if errors:
        raise ValueError("inject.yml validation failed:\n  " + "\n  ".join(errors))
    patches = data.get("hand_patches") or []
    # Locate inject.yml line numbers per entry for the inline comment.
    inject_text = inject.read_text(encoding="utf-8").splitlines()
    entry_line_numbers: list[int] = []
    cursor = 0
    for _ in patches:
        # Find next "- target" or "- " starting a list entry.
        for i in range(cursor, len(inject_text)):
            if re.match(r"^\s*-\s+target\s*:", inject_text[i]) or re.match(
                r"^\s*-\s*\{?\s*target\b", inject_text[i]
            ):
                entry_line_numbers.append(i + 1)
                cursor = i + 1
                break
        else:
            entry_line_numbers.append(0)
    lines = source.splitlines()
    warnings: list[str] = []
    for idx, patch in enumerate(patches):
        target = patch.get("target") or {}
        element = target.get("element")
        anname = target.get("anname")
        field = patch.get("field")
        if not element or not anname or not field:
            continue
        block = _find_call_block(source, element, anname)
        if block is None:
            warnings.append(
                f"inject entry {idx} ({element}/{anname}/{field}): not found in build.py.generated"
            )
            continue
        reason = patch.get("reason", "")
        first_line_of_reason = reason.splitlines()[0] if reason else ""
        if len(first_line_of_reason) > 80:
            first_line_of_reason = first_line_of_reason[:77] + "..."
        comment = (
            f"P5/inject (from inject.yml line {entry_line_numbers[idx]}): "
            f"{first_line_of_reason}"
        )
        # Re-read lines from the in-memory state (previous inject entry may have
        # inserted lines and shifted blocks).
        block = _find_call_block("\n".join(lines), element, anname)
        if block is None:
            warnings.append(
                f"inject entry {idx} ({element}/{anname}/{field}): "
                f"lost reference after prior insertion"
            )
            continue
        if "set" in patch:
            mutated, prev_value = _apply_set(
                lines, block, field, patch["set"], comment
            )
            if mutated and prev_value is not None:
                set_repr = _repr_value(patch["set"])
                # Redundancy detection: if the kwarg's prior value is already
                # equal to the new set value (literal-equal), warn.
                if prev_value.strip() == set_repr.strip():
                    warnings.append(
                        f"inject entry at line {entry_line_numbers[idx]} is "
                        f"redundant; the converter now emits the same value. "
                        f"Consider removing it."
                    )
            elif not mutated:
                warnings.append(
                    f"inject entry {idx}: field '{field}' not found in "
                    f"{element}/{anname} block"
                )
        elif "delta" in patch:
            mutated, prev_value = _apply_delta(
                lines, block, field, patch["delta"], comment
            )
            if not mutated:
                warnings.append(
                    f"inject entry {idx}: field '{field}' not numeric in "
                    f"{element}/{anname} block"
                )
    output = "\n".join(lines)
    if not output.endswith("\n"):
        output += "\n"
    if not quiet:
        for w in warnings:
            print(f"reconcile_build_py: {w}", file=sys.stderr)
    return output, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reconcile_build_py",
        description=(
            "Apply inject.yml hand_patches to build.py.generated; emit build.py. "
            "--check mode for CI: assert build.py matches reconciled output."
        ),
    )
    parser.add_argument("slug", help="Template slug.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare reconciled output to build.py without writing; exit 1 on mismatch.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational stderr.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repo root (for tests).",
    )
    args = parser.parse_args(argv)
    try:
        output, _warnings = reconcile(
            args.slug, repo_root=args.repo_root, quiet=args.quiet
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"reconcile_build_py: {exc}", file=sys.stderr)
        return 2
    repo_root = args.repo_root or ROOT
    build_py = repo_root / "templates" / args.slug / "build.py"
    if args.check:
        existing = build_py.read_text(encoding="utf-8") if build_py.exists() else ""
        if existing == output:
            return 0
        print(
            f"reconcile_build_py --check: templates/{args.slug}/build.py "
            f"differs from reconciled output",
            file=sys.stderr,
        )
        return 1
    build_py.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
