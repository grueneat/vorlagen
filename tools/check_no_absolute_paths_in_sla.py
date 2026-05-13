#!/usr/bin/env python3
"""Reject absolute filesystem paths in committed ``templates/*/template.sla``.

Issue #39 Phase A guard. Walks every SLA, parses its XML, and fails on any
``PAGEOBJECT`` whose ``PFILE`` attribute matches an absolute path. Targets
catch:

  * Unix absolute paths (``/workspace/...``, ``/home/...``, ``/root/...``,
    ``/tmp/...``, ``/var/...``, ``/private/var/...``, ``/Users/...``).
  * ``file://`` URIs.
  * Windows drive letters (``C:\\``, ``C:/``, ``D:\\``).

Empty ``PFILE`` is OK — inline-image frames have ``isInlineImage="1"`` and
``PFILE=""`` per ``tools/sla_lib/builder/primitives.py``.

Wired into ``.pre-commit-config.yaml`` (5th SOP hook) and the
``SOP gates`` step of ``.github/workflows/ci.yml``. Exit 1 on any failure,
exit 0 when clean.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from lxml import etree


ABSOLUTE_PFILE_RE = re.compile(r"^(?:/|file://|[A-Za-z]:[\\/])")


def find_absolute_pfiles(root: Path) -> list[tuple[Path, int, str]]:
    """Return (sla_path, sourceline, pfile_value) for every absolute PFILE
    in ``root/templates/*/template.sla``. Empty list when clean.
    """
    failures: list[tuple[Path, int, str]] = []
    for sla in sorted((root / "templates").glob("*/template.sla")):
        try:
            tree = etree.parse(str(sla))
        except (OSError, etree.XMLSyntaxError) as exc:
            failures.append((sla, 0, f"<parse error: {exc}>"))
            continue
        for el in tree.iterfind(".//PAGEOBJECT[@PFILE]"):
            pf = el.get("PFILE", "")
            if not pf:
                continue
            if ABSOLUTE_PFILE_RE.match(pf):
                failures.append((sla, el.sourceline or 0, pf))
    return failures


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_no_absolute_paths_in_sla",
        description=(
            "Reject absolute filesystem paths in committed template.sla "
            "files (issue #39 Phase A guard)."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=root if root is not None else Path(__file__).resolve().parents[1],
        help="Repo root (default: parent of tools/).",
    )
    args = parser.parse_args(argv)
    failures = find_absolute_pfiles(args.root)
    if not failures:
        return 0
    for sla, line, pf in failures:
        try:
            rel = sla.relative_to(args.root)
        except ValueError:
            rel = sla
        print(f"{rel}:{line}: absolute PFILE: {pf}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
