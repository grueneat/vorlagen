"""Mutation tests for the inventory gate.

Three mutations on a tmp-copy of the anchor template's build.py:

- **M1**: drop a ``Run(text='...')`` entry → comparator reports the missing
  word under ``text_runs.missing`` and exits 2.
- **M2**: rename an ``anname='u514'`` to ``anname='u514X'`` → comparator
  reports ``u514`` missing under ``frames.image_frames`` and exits 2.
- **M3**: drop one ``add_color(...)`` call → comparator reports the color's
  missing build.py emit and exits 2.

Each test compares against the committed baseline at
``templates/<slug>/SCAFFOLD_INVENTORY.yml`` (anchor path).

The tests run with BOTH ``pytest`` and ``python3 -m unittest discover``
because CI in this repo uses unittest while local dev uses pytest. To
satisfy both runners we use plain ``unittest.TestCase`` with ``setUp`` /
``tearDown`` (a pytest ``tmp_path`` fixture would break unittest).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

# Worktree root → sys.path so we can import tools.inventory_extract directly.
HERE = Path(__file__).resolve()
WORKTREE = HERE.parents[2]
if str(WORKTREE) not in sys.path:
    sys.path.insert(0, str(WORKTREE))

ANCHOR_SLUG = "26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover"
LEPORELLO_DIR = Path(
    os.environ.get("LEPORELLO_DIR", "/workspace/templates/" + ANCHOR_SLUG)
)
ORIGINALS_DIR = Path("/workspace/originals")
REPO_ROOT = Path("/workspace")
BASELINE = LEPORELLO_DIR / "SCAFFOLD_INVENTORY.yml"


@unittest.skipUnless(
    LEPORELLO_DIR.exists() and BASELINE.exists() and ORIGINALS_DIR.exists(),
    f"Anchor template or originals not present (LEPORELLO_DIR={LEPORELLO_DIR}); "
    f"set LEPORELLO_DIR to override.",
)
class InventoryGateMutationTest(unittest.TestCase):
    """Mutate a copy of the anchor build.py and assert the gate catches it."""

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="inv-mutation-"))
        # Copy the anchor's template files into <tmp>/<slug>/.
        dst = self.tmpdir / "templates" / ANCHOR_SLUG
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("build.py", "meta.yml", "template.sla", "preview.pdf", "baseline.pdf"):
            src = LEPORELLO_DIR / name
            if src.exists():
                shutil.copy2(src, dst / name)
        # meta.yml's idml_source is relative to the template dir; the copy
        # preserves the relative path, and we pass --originals-dir explicitly
        # so resolution still hits /workspace/originals/.
        self.template_dir = dst
        self.build_py = dst / "build.py"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ------- helpers ------------------------------------------------------

    def _extract_mutated(self) -> Path:
        """Run inventory_extract.py over the tmp copy. Returns the YAML path."""
        out_path = self.tmpdir / "inv-actual.yml"
        cmd = [
            sys.executable, str(WORKTREE / "tools" / "inventory_extract.py"),
            "--slug", ANCHOR_SLUG,
            "--templates-dir", str(self.tmpdir / "templates"),
            "--originals-dir", str(ORIGINALS_DIR),
            "--repo-root", str(REPO_ROOT),
            "--output", str(out_path),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            self.fail(
                f"inventory_extract failed (rc={r.returncode}):\n"
                f"stdout: {r.stdout}\nstderr: {r.stderr}"
            )
        return out_path

    def _compare(self, actual_path: Path) -> tuple[int, dict]:
        """Run inventory_compare.py. Returns (exit_code, diff_dict)."""
        diff_path = self.tmpdir / "diff.yml"
        cmd = [
            sys.executable, str(WORKTREE / "tools" / "inventory_compare.py"),
            "--expected", str(BASELINE),
            "--actual", str(actual_path),
            "--out", str(diff_path),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        diff = yaml.safe_load(diff_path.read_text(encoding="utf-8"))
        return r.returncode, diff

    def _patch_build_py(self, transform) -> None:
        text = self.build_py.read_text(encoding="utf-8")
        new_text = transform(text)
        self.assertNotEqual(
            text, new_text,
            "Mutation transform produced an identical file — "
            "test fixture is broken.",
        )
        self.build_py.write_text(new_text, encoding="utf-8")

    # ------- M1: drop a Run(text='...') -----------------------------------

    def test_m1_drop_run_text_is_detected(self) -> None:
        # Pick the FIRST non-empty Run(text='...') literal in build.py and
        # rewrite its text to empty string, simulating "the agent dropped
        # this word". We don't delete the whole Run() (would also drop a
        # paragraph-separator), just the text content.
        def transform(text: str) -> str:
            # Match Run(...text='<value>'...). text= must come at the start
            # of a kwarg so we anchor on Run( prefix.
            pattern = re.compile(
                r"(Run\(\s*text=')([^']{2,})(')",
                re.DOTALL,
            )
            replaced = {"done": False}
            def _sub(m):
                if replaced["done"]:
                    return m.group(0)
                replaced["done"] = True
                self._dropped_text = m.group(2)
                return m.group(1) + m.group(3)
            return pattern.sub(_sub, text, count=1)

        self._patch_build_py(transform)
        actual = self._extract_mutated()
        rc, diff = self._compare(actual)
        self.assertEqual(rc, 2, f"expected regression (rc=2), got {rc}; diff={diff}")
        missing = diff.get("missing", {}) or {}
        text_missing = missing.get("text_runs.missing", []) or []
        self.assertIn(
            self._dropped_text, text_missing,
            f"dropped text {self._dropped_text!r} not in diff.missing.text_runs.missing "
            f"({text_missing})",
        )

    # ------- M2: rename anname='u514' to anname='u514X' --------------------

    def test_m2_rename_image_anname_is_detected(self) -> None:
        def transform(text: str) -> str:
            # Rename the ziesel.jpg image-frame anname (u514) to u514X. The
            # original is the first ImageFrame in build.py, so the regex
            # anchors anname='u514' uniquely.
            self.assertIn("anname='u514'", text, "u514 anname not in build.py")
            return text.replace("anname='u514'", "anname='u514X'", 1)

        self._patch_build_py(transform)
        actual = self._extract_mutated()
        rc, diff = self._compare(actual)
        self.assertEqual(rc, 2, f"expected regression (rc=2), got {rc}; diff={diff}")
        missing = diff.get("missing", {}) or {}
        img_missing = missing.get("frames.image_frames", []) or []
        self.assertIn(
            "u514", img_missing,
            f"u514 not in diff.missing.frames.image_frames ({img_missing})",
        )

    # ------- M3: drop one add_color(...) call ------------------------------

    def test_m3_drop_add_color_is_detected(self) -> None:
        def transform(text: str) -> str:
            # Drop the first ``doc.add_color(...)`` call. The anchor has 3
            # add_color calls; we delete the first one and assert it
            # appears as missing under ``colors.build_py``. Build.py emits
            # these as one-liners with nested cmyk=(...), so we walk the
            # call site manually to find the matching close-paren.
            start_re = re.compile(r"^[ \t]*(?:doc\.)?add_color\(\s*['\"]",
                                  re.MULTILINE)
            m = start_re.search(text)
            if m is None:
                self.fail("no add_color(...) found in build.py")
            call_start = m.start()
            # Walk forward from the opening paren to its matching close.
            paren_open = text.index("(", call_start)
            depth = 0
            i = paren_open
            while i < len(text):
                if text[i] == "(":
                    depth += 1
                elif text[i] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            call_end = i + 1
            # Eat the trailing newline so we don't leave a blank line.
            if call_end < len(text) and text[call_end] == "\n":
                call_end += 1
            call_text = text[call_start:call_end]
            name_match = re.search(r"add_color\(\s*['\"]([^'\"]+)['\"]",
                                   call_text)
            self.assertIsNotNone(name_match, f"could not parse color name in {call_text!r}")
            self._dropped_color = name_match.group(1)
            return text[:call_start] + text[call_end:]

        self._patch_build_py(transform)
        actual = self._extract_mutated()
        rc, diff = self._compare(actual)
        self.assertEqual(rc, 2, f"expected regression (rc=2), got {rc}; diff={diff}")
        missing = diff.get("missing", {}) or {}
        color_missing = missing.get("colors.build_py", []) or []
        # The comparator uses the IDML self-id (e.g. "Color/Dunkelgrün") as
        # the missing key. The dropped name from build.py is the bare name.
        joined = " ".join(color_missing)
        self.assertIn(
            self._dropped_color, joined,
            f"dropped color {self._dropped_color!r} not in "
            f"diff.missing.colors.build_py ({color_missing})",
        )


if __name__ == "__main__":
    unittest.main()
