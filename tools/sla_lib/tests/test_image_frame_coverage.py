"""Cross-template coverage check: every ImageFrame in build_preview() must
have image content (image / src / inline_image_data set) OR be background
decoration (brand-color fill).

This catches regressions where a template adds an ImageFrame slot but
forgets to bind it via inline_image_data, INJECT_MAP, or a brand fill.
The rendered preview PNG would otherwise show an empty rectangle —
the kind of silent regression that historically required visual review
to detect.

Issue #26: introduced after issue #21 shipped V1 layouts with
visually-empty image slots (logos bound but no INJECT_MAP entry, etc.)
that weren't caught by structural_check or smoke tests because they
all run on build_doc() (the clean template) where INJECT_MAP slots
are intentionally empty.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder.primitives import ImageFrame  # noqa: E402

# Mirrors the rule's `_DEFAULT_BG_DECORATION_FILLS` plus the cover/back
# Hellgrün-3-mm-strip and Magenta störer fills that show up on the V1
# templates.
BG_FILLS = {"Dunkelgrün", "Hellgrün", "Magenta", "Gelb", "White"}


def _load_build_module(slug: str):
    """Import templates/<slug>/build.py and return the module."""
    p = ROOT / "templates" / slug / "build.py"
    spec = importlib.util.spec_from_file_location(f"build_{slug}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _empty_image_frames(doc) -> list[tuple[int, str]]:
    """Return [(page_idx_1based, anname)] for every ImageFrame whose
    rendered preview state would be empty: no image content AND no
    background-decoration fill."""
    empty: list[tuple[int, str]] = []
    for i, page in enumerate(doc.pages):
        if getattr(page, "is_master", False):
            continue
        for item in page.items:
            if not isinstance(item, ImageFrame):
                continue
            has_img = bool(
                item.image or item.src
                or getattr(item, "inline_image_data", None)
            )
            is_decor = item.fill in BG_FILLS
            # Anchor-positioned inline icons share the IconBlock contract
            # (positioned relative to a text run); they self-bind via
            # inline_image_data inside the block emitter.
            anchor = getattr(item, "anchor", None)
            if has_img or is_decor:
                continue
            if anchor is not None:
                continue
            ident = (item.anname or "").strip() or "<unnamed>"
            empty.append((i + 1, ident))
    return empty


class ImageFrameCoverageTests(unittest.TestCase):
    """Each test exercises ONE template's build_preview() so the assertion
    failure points at the offending slug + page + frame anname."""

    def _check(self, slug: str) -> None:
        m = _load_build_module(slug)
        if not hasattr(m, "build_preview"):
            self.skipTest(f"{slug}: no build_preview() function")
            return
        doc = m.build_preview()
        empty = _empty_image_frames(doc)
        self.assertEqual(
            empty, [],
            msg=(
                f"{slug}: build_preview() left ImageFrames empty. Each "
                f"frame must bind image content via inline_image_data, "
                f"INJECT_MAP (in build_preview), or set a brand-color "
                f"fill to mark it as background decoration. Empty: "
                f"{empty}"
            ),
        )

    def test_plakat_a1_hochformat(self):
        self._check("plakat-a1-hochformat")

    def test_postkarte_a6_kampagne(self):
        self._check("postkarte-a6-kampagne")

    def test_zeitung_a4_grun(self):
        self._check("zeitung-a4")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
