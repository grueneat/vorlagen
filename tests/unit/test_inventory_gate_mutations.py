"""Mutation tests for the inventory gate.

Six mutations on a tmp-copy of the anchor template's build.py and template.sla:

- **M1**: drop a ``Run(text='...')`` entry → comparator reports the missing
  word under ``text_runs.missing`` and exits 2.
- **M2**: rename an ``anname='u514'`` to ``anname='u514X'`` → comparator
  reports ``u514`` missing under ``frames.image_frames`` and exits 2.
- **M3**: drop one ``add_color(...)`` call → comparator reports the color's
  missing build.py emit and exits 2.
- **M4**: drop one ``doc.add_para_style(...)`` call → comparator reports
  the dropped paragraph style under ``paragraph_styles.build_py`` and
  exits 2 (review fix F12 for F7's new gate path).
- **M5**: flip ``PFILE=`` to empty on one SLA PAGEOBJECT → comparator
  reports the affected frame anname under
  ``frames.image_frames.sla_pfile`` and exits 2.
- **M6**: drop a CharacterStyleRange text run on the IDML side via a
  synthetic IDML → ``every_idml_run_present_in_build_py: false`` triggers
  the Stage-1 gate (F9) at rc=2.

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

ANCHOR_SLUG = "falzflyer-z-falz-6-seitig-zweigeteiltes-cover"
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

    # ------- M4: drop one add_para_style(...) call (F7 → F12) -----------

    def test_m4_drop_add_para_style_is_detected(self) -> None:
        """Verify the comparator catches a dropped add_para_style() call.

        Mirrors the M3 (drop add_color) approach: find the
        ``doc.add_para_style(ParaStyle(name='idml/aufzaehlungen-...'))``
        call (a real paragraph style that maps to an IDML counterpart —
        NOT the sentinel "idml/no-paragraph-style"), extract the style
        name, and excise the entire call. The fresh inventory should
        report the dropped style under ``missing.paragraph_styles.build_py``
        and the comparator should exit 2.
        """
        # The anchor calls add_para_style for several styles; pick
        # "aufzaehlungen-auf-gruenem-hintergrund" because it maps directly to
        # the IDML "Aufzählungen auf grünem Hintergrund" entry (no sentinel
        # filtering needed). If that style isn't in build.py for some
        # reason, fall back to any non-sentinel style.
        target_name = "idml/aufzaehlungen-auf-gruenem-hintergrund"

        def transform(text: str) -> str:
            # Find the add_para_style call that has the target name. Match
            # the WHOLE STATEMENT including the leading indentation so the
            # surrounding indentation block is preserved when the call is
            # excised.
            anchor_re = re.compile(
                r"^([ \t]*)(?:doc\.)?add_para_style\(",
                re.MULTILINE,
            )
            found_start: int | None = None
            found_name: str | None = None
            for m in anchor_re.finditer(text):
                call_start = m.start()
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
                call_text = text[call_start:call_end]
                name_match = re.search(
                    r"name=['\"]([^'\"]+)['\"]|add_para_style\(\s*['\"]([^'\"]+)['\"]",
                    call_text,
                )
                if name_match is None:
                    continue
                name = name_match.group(1) or name_match.group(2)
                # Prefer the target, otherwise the first non-sentinel.
                if name == target_name:
                    found_start = call_start
                    found_name = name
                    break
                if found_start is None and name and "no-paragraph-style" not in name:
                    found_start = call_start
                    found_name = name
            if found_start is None or found_name is None:
                self.fail("no non-sentinel add_para_style(...) found")
            # Recompute end for the chosen call.
            paren_open = text.index("(", found_start)
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
            # Eat the trailing newline so we don't leave a blank line of
            # whitespace alone (build.py is Python — stray indent at top
            # level breaks the parse).
            if call_end < len(text) and text[call_end] == "\n":
                call_end += 1
            self._dropped_pstyle = found_name
            return text[:found_start] + text[call_end:]

        self._patch_build_py(transform)
        actual = self._extract_mutated()
        rc, diff = self._compare(actual)
        self.assertEqual(rc, 2, f"expected regression (rc=2), got {rc}; diff={diff}")
        missing = diff.get("missing", {}) or {}
        ps_missing = missing.get("paragraph_styles.build_py", []) or []
        # The comparator reports the IDML key (e.g. "ParagraphStyle/Aufzählungen...").
        # The dropped build.py name is e.g. "idml/aufzaehlungen-auf-...".
        # Match via the canonical slugifier so the two sides line up
        # byte-for-byte (umlauts folded the same way).
        from tools.idml_to_dsl import _idml_style_slug
        ps_slugged = [
            _idml_style_slug(p.split("/", 1)[-1]).lower()
            for p in ps_missing
        ]
        self.assertIn(
            self._dropped_pstyle.lower(), ps_slugged,
            f"dropped paragraph style {self._dropped_pstyle!r} not in "
            f"slugified diff.missing.paragraph_styles.build_py "
            f"(IDML rows: {ps_missing}, slugs: {ps_slugged})",
        )

    # ------- M5: flip PFILE='' on one SLA PAGEOBJECT (F7) ----------------

    def test_m5_drop_pfile_on_sla_image_is_detected(self) -> None:
        """Verify the comparator catches a removed PFILE on a SLA PAGEOBJECT.

        Mutates the tmp SLA: finds the first PAGEOBJECT with
        ``PFILE="..."`` and ``ANNAME="..."``, sets PFILE to an empty
        string. The fresh inventory should report
        ``sla_pfile_present: false`` for that frame, and the comparator
        should report the affected anname under
        ``missing.frames.image_frames.sla_pfile`` with rc=2.
        """
        sla_path = self.template_dir / "template.sla"
        sla_text = sla_path.read_text(encoding="utf-8")
        # Find first PAGEOBJECT with both PFILE and ANNAME set.
        m = re.search(
            r"<PAGEOBJECT\b[^>]*?ANNAME=\"([^\"]+)\"[^>]*?PFILE=\"[^\"]+\"",
            sla_text,
        )
        if m is None:
            # Try with ANNAME after PFILE.
            m = re.search(
                r"<PAGEOBJECT\b[^>]*?PFILE=\"[^\"]+\"[^>]*?ANNAME=\"([^\"]+)\"",
                sla_text,
            )
        self.assertIsNotNone(
            m, "no SLA PAGEOBJECT with both ANNAME= and PFILE= found",
        )
        anname = m.group(1)
        # Patch: erase the PFILE on JUST that pageobject.
        new_text = re.sub(
            r'(<PAGEOBJECT\b[^>]*?ANNAME="' + re.escape(anname) + r'"[^>]*?PFILE=)"[^"]+"',
            r'\1""',
            sla_text,
            count=1,
        )
        # Also handle the PFILE-before-ANNAME order.
        if new_text == sla_text:
            new_text = re.sub(
                r'(<PAGEOBJECT\b[^>]*?PFILE=)"[^"]+"([^>]*?ANNAME="' + re.escape(anname) + r'")',
                r'\1""\2',
                sla_text,
                count=1,
            )
        self.assertNotEqual(
            new_text, sla_text,
            "PFILE-flip patch produced an identical SLA — regex didn't bite",
        )
        sla_path.write_text(new_text, encoding="utf-8")
        actual = self._extract_mutated()
        rc, diff = self._compare(actual)
        self.assertEqual(rc, 2, f"expected regression (rc=2), got {rc}; diff={diff}")
        missing = diff.get("missing", {}) or {}
        pfile_missing = missing.get("frames.image_frames.sla_pfile", []) or []
        self.assertIn(
            anname, pfile_missing,
            f"flipped-PFILE anname {anname!r} not in "
            f"diff.missing.frames.image_frames.sla_pfile ({pfile_missing})",
        )

    # ------- M6: synthetic IDML CSR drop, Stage-1 gate path (F9) ---------

    def test_m6_idml_run_dropped_triggers_stage1_gate(self) -> None:
        """Verify the Stage-1 gate fires when an IDML CSR text is missing
        from build.py (the every_idml_run_present_in_build_py contract).

        Uses the real anchor as the baseline. Mutation: drop a Run() text
        on the build.py side (same as M1, but the assertion targets the
        Stage-1 gate rather than the comparator). Re-runs the in-process
        ``build_inventory + _stage1_gate_check`` pair and asserts a
        descriptive failure string.
        """
        def transform(text: str) -> str:
            # Same regex as M1: drop the first non-empty Run text.
            pattern = re.compile(
                r"(Run\(\s*text=')([^']{2,})(')",
                re.DOTALL,
            )
            return pattern.sub(lambda m: m.group(1) + m.group(3), text, count=1)
        self._patch_build_py(transform)
        # Invoke the gate function directly — no need to shell out twice.
        from tools.inventory_extract import build_inventory
        from tools.idml_import_driver import _stage1_gate_check
        inv = build_inventory(
            ANCHOR_SLUG,
            templates_dir=self.tmpdir / "templates",
            originals_dir=ORIGINALS_DIR,
            repo_root=REPO_ROOT,
        )
        result = _stage1_gate_check(inv, ANCHOR_SLUG)
        self.assertIsNotNone(
            result, "Stage-1 gate did not fire on dropped IDML run",
        )
        self.assertIn(
            "every_idml_run_present_in_build_py",
            result,
            f"Stage-1 gate failure does not name the rule: {result!r}",
        )


if __name__ == "__main__":
    unittest.main()
