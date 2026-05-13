"""Unit tests for tools.walkers.walk_sla.

Regression tests covering issue #40 review fix F1: the walker must read
``PARENT`` (on ``<trail>`` / ``<para>`` elements) rather than ``PSTYLE``,
because Scribus stores paragraph-style references on trail elements while
the IDML side uses PSTYLE elsewhere. The anchor SLA has zero ``PSTYLE=``
attributes and 92 ``PARENT=`` attributes, so the old PSTYLE lookup produced
``itext_by_pstyle == {}`` (silent failure that erodes gate coverage on the
SLA side).
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
WORKTREE = HERE.parents[2]
if str(WORKTREE) not in sys.path:
    sys.path.insert(0, str(WORKTREE))

ANCHOR_SLUG = "26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover"
LEPORELLO_SLA = Path(
    os.environ.get(
        "LEPORELLO_DIR",
        "/workspace/templates/" + ANCHOR_SLUG,
    )
) / "template.sla"


@unittest.skipUnless(LEPORELLO_SLA.exists(), f"Anchor SLA missing: {LEPORELLO_SLA}")
class WalkSLAParagraphStyleTest(unittest.TestCase):
    """Verify walk_sla picks up Scribus paragraph-style refs via PARENT."""

    @classmethod
    def setUpClass(cls) -> None:
        from tools.walkers.walk_sla import walk_sla
        cls.out = walk_sla(LEPORELLO_SLA)

    def test_itext_by_pstyle_is_non_empty(self) -> None:
        # Before F1: itext_by_pstyle was always {} because the walker read
        # PSTYLE while Scribus uses PARENT. After F1: anchor has 5+ paragraph
        # styles referenced via PARENT.
        self.assertGreater(
            len(self.out["itext_by_pstyle"]),
            0,
            "walk_sla returned an empty itext_by_pstyle — the walker is "
            "reading the wrong SLA attribute. See issue #40 review F1.",
        )

    def test_expected_paragraph_styles_present(self) -> None:
        # The anchor's template.sla references these style names via
        # ``<trail PARENT="...">``. The set membership check is intentional:
        # exact counts can shift if the SLA is reflowed, but the names should
        # remain stable.
        styles = set(self.out["itext_by_pstyle"].keys())
        expected_subset = {
            "idml/normalparagraphstyle",
            "idml/fliesstext-auf-gruenem-hintergrund",
            "idml/aufzaehlungen-auf-gruenem-hintergrund",
            "idml/headline-in-gruenem-kasten",
            "idml/absatzformat-1",
        }
        missing = expected_subset - styles
        self.assertFalse(
            missing,
            f"walk_sla missed expected SLA paragraph styles: {sorted(missing)}; "
            f"got: {sorted(styles)}",
        )

    def test_counts_are_positive(self) -> None:
        # Every populated bucket must have a positive ITEXT count.
        for style, count in self.out["itext_by_pstyle"].items():
            self.assertGreater(
                count, 0,
                f"style {style!r} reports zero ITEXTs — buffer bookkeeping bug",
            )


if __name__ == "__main__":
    unittest.main()
