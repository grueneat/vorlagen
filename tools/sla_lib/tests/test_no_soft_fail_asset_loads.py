"""Forbid soft-fail asset loads in template build.py files.

Issue #27: the user mandated that asset loads in templates must be
hard-required — `if asset.exists(): load(...)` patterns silently
produce inconsistent renders if the asset file is missing in a
checkout. The build must fail loud instead.

This test scans every `templates/*/build.py` for `if X.exists():`
patterns (positive guard, NOT `if not X.exists(): raise`) and fails
if any are found. Hard-required loads use `if not X.exists(): raise
FileNotFoundError(...)` instead — those are accepted.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


# Match `if <expr>.exists():` — the soft-fail pattern.
# Whitelist `if not X.exists():` — the hard-fail guard.
_SOFT_FAIL_RX = re.compile(r"^(\s*)if\s+(?!not\s)[^=]+\.exists\(\)\s*:")


class NoSoftFailAssetLoadsTests(unittest.TestCase):
    def test_no_template_build_py_uses_soft_fail_exists_check(self) -> None:
        offenders: list[tuple[str, int, str]] = []
        for build_py in sorted((ROOT / "templates").glob("*/build.py")):
            text = build_py.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), start=1):
                if _SOFT_FAIL_RX.match(line):
                    rel = build_py.relative_to(ROOT)
                    offenders.append((str(rel), i, line.strip()))
        self.assertEqual(
            offenders, [],
            msg=(
                "Template build.py files must not contain soft-fail "
                "`if X.exists():` patterns — these silently skip asset "
                "binding when files are missing, producing inconsistent "
                "renders across checkouts. Use `if not X.exists(): raise "
                "FileNotFoundError(...)` instead so missing assets fail "
                "the build loud. Offenders:\n  "
                + "\n  ".join(f"{f}:{ln}: {src}" for f, ln, src in offenders)
            ),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
