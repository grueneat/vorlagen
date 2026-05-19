"""Cross-template thema-panel symmetry check.

Templates that lay out multiple parallel "Thema N" sub-sections inside a
panel name their frames `<panel-prefix> Thema <N> — <suffix>` (em-dash
U+2014; per #21 RESEARCH locked decision #4). Example annames:

    "P4 Thema 1 — Eyebrow"
    "P4 Thema 1 — Headline"
    "P4 Thema 1 — Photo"
    "P4 Thema 1 — Body"
    "P4 Thema 2 — Eyebrow"
    ...

For each panel-prefix, every Thema-N must carry the SAME set of
suffixes — otherwise the rendered layout shows asymmetric rhythm
(some themas have body text, others don't), which historically required
visual review to detect.

Issue #26: shipped after #21 left Thema 2 + Thema 4 without a Body
frame on the kandidat-falzflyer template; user spotted it visually.
This rule catches the class so any future asymmetric thema layout
fails CI before merge.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))


# Em-dash U+2014 literal; surrounding spaces are part of the convention
# (per #21 RESEARCH locked decision #4: "use real annames, NOT snake_case").
_THEMA_RX = re.compile(r"^(.+?)\s+Thema\s+(\d+)\s+—\s+(.+?)\s*$")


def _load_build_module(slug: str):
    p = ROOT / "templates" / slug / "build.py"
    spec = importlib.util.spec_from_file_location(f"build_{slug}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _collect_thema_groups(doc) -> dict[str, dict[int, set[str]]]:
    """Walk doc.pages, group frames by `<panel-prefix> Thema N — <suffix>`.

    Returns: {panel_prefix: {thema_n: {suffix_1, suffix_2, ...}}}
    """
    groups: dict[str, dict[int, set[str]]] = {}
    for page in doc.pages:
        if getattr(page, "is_master", False):
            continue
        for item in page.items:
            an = getattr(item, "anname", "") or ""
            mm = _THEMA_RX.match(an)
            if not mm:
                continue
            prefix, n_str, suffix = mm.group(1), mm.group(2), mm.group(3)
            try:
                n = int(n_str)
            except ValueError:
                continue
            groups.setdefault(prefix, {}).setdefault(n, set()).add(suffix)
    return groups


def _asymmetries(groups) -> list[tuple[str, int, set[str]]]:
    """Return [(panel_prefix, thema_n, missing_suffixes)] for every Thema
    that's missing a suffix present in any other Thema in the same panel.
    """
    issues: list[tuple[str, int, set[str]]] = []
    for prefix, themas in groups.items():
        if not themas:
            continue
        union: set[str] = set()
        for s in themas.values():
            union |= s
        for n in sorted(themas):
            missing = union - themas[n]
            if missing:
                issues.append((prefix, n, missing))
    return issues


class ThemaPanelSymmetryTests(unittest.TestCase):
    """Per-template assertions; failure pinpoints the offending panel +
    thema + missing suffixes."""

    def _check(self, slug: str) -> None:
        m = _load_build_module(slug)
        if not hasattr(m, "build_doc"):
            self.skipTest(f"{slug}: no build_doc() function")
            return
        doc = m.build_doc()
        groups = _collect_thema_groups(doc)
        if not groups:
            self.skipTest(f"{slug}: no thema-panel structure to check")
            return
        issues = _asymmetries(groups)
        self.assertEqual(
            issues, [],
            msg=(
                f"{slug}: thema-panel asymmetry. Each Thema-N inside a "
                f"panel must carry the same set of suffixes (Eyebrow / "
                f"Headline / Photo / Body / etc.). Asymmetries (panel, "
                f"thema_n, missing): {issues}"
            ),
        )

    def test_infostand_tent_card_a5_quer(self):
        self._check("tischschild-a5-quer")

    def test_plakat_a1_hochformat(self):
        self._check("plakat-a1-hochformat")

    def test_postkarte_a6_kampagne(self):
        self._check("postkarte-a6-kampagne")

    def test_zeitung_a4_grun(self):
        self._check("zeitung-a4")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
