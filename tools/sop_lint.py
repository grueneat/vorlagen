#!/usr/bin/env python3
"""SOP lint — bans the rendering-floor family of phrases in tracked files.

Run via pre-commit + CI. Exit 0 = clean, 1 = banned phrase found.

The banned phrases name a fail mode where executors declared a non-existent
rendering plateau against silent converter bugs. Issue #38 enforces the
ban mechanically so prose SOPs can no longer be paraphrased around.

Scopes: tools/, templates/, bin/, .claude/, docs/, top-level README*,
CHANGELOG*. Issue artifacts under .issues/ are excluded by design — they
contain historical records of the trap.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

BANNED_PATTERNS: list[str] = [
    r"engine[_ ]floor",
    r"engine[_ ]ceiling",
    r"rendering[_ ]floor",
]

SCOPE_PREFIXES: tuple[str, ...] = (
    "templates/",
    "tools/",
    "bin/",
    ".claude/",
    "docs/",
)

SCOPE_BASENAME_PREFIXES: tuple[str, ...] = (
    "README",
    "CHANGELOG",
)

# This file itself names the banned phrases as a literal corpus inside
# BANNED_PATTERNS. The lint must not flag itself; same for its unit test.
SELF_EXCLUDE: frozenset[str] = frozenset(
    {
        "tools/sop_lint.py",
        "tests/unit/test_sop_lint.py",
    }
)


def _in_scope(path: str) -> bool:
    """True iff the given repo-relative path is subject to the lint."""
    if path in SELF_EXCLUDE:
        return False
    for prefix in SCOPE_PREFIXES:
        if path.startswith(prefix):
            return True
    basename = path.rsplit("/", 1)[-1]
    for prefix in SCOPE_BASENAME_PREFIXES:
        if basename.startswith(prefix):
            # Only top-level READMEs / CHANGELOGs are in scope; nested
            # docs in non-scope trees would be miscategorised otherwise.
            if "/" not in path:
                return True
    return False


def _tracked_files(repo_root: Path | None = None) -> list[str]:
    """Return repo-tracked files (git ls-files), repo-relative."""
    cmd = ["git", "ls-files"]
    cwd = str(repo_root) if repo_root else None
    out = subprocess.check_output(cmd, cwd=cwd)
    return out.decode("utf-8").splitlines()


def find_offenders(
    repo_root: Path | None = None,
    tracked: list[str] | None = None,
) -> list[tuple[str, int, str]]:
    """Walk tracked files in scope and return (path, lineno, line) per hit."""
    if tracked is None:
        tracked = _tracked_files(repo_root)
    regex = re.compile("|".join(BANNED_PATTERNS), re.IGNORECASE)
    offenders: list[tuple[str, int, str]] = []
    base = repo_root or Path.cwd()
    for path in tracked:
        if not _in_scope(path):
            continue
        full = base / path
        try:
            with open(full, "r", encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    if regex.search(line):
                        offenders.append((path, lineno, line.rstrip()))
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            # Binary blobs, deleted-but-tracked, submodule dirs: skip.
            continue
    return offenders


def main(argv: list[str] | None = None) -> int:
    offenders = find_offenders()
    if offenders:
        print("SOP-LINT FAILED — banned phrase found:", file=sys.stderr)
        for path, lineno, line in offenders:
            print(f"  {path}:{lineno}: {line}", file=sys.stderr)
        print(
            "\nThese phrases are banned per issue #38. Rename or remove.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
