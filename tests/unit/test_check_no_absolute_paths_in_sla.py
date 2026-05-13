"""Unit tests for tools/check_no_absolute_paths_in_sla.py (issue #39)."""
from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import check_no_absolute_paths_in_sla as cnap  # noqa: E402


_SLA_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<SCRIBUSUTF8NEW Version="1.6.5">\n'
    '  <DOCUMENT>\n'
)
_SLA_FOOTER = "  </DOCUMENT>\n</SCRIBUSUTF8NEW>\n"


def _wrap_pageobjects(pageobjects: list[str]) -> str:
    return _SLA_HEADER + "\n".join(pageobjects) + "\n" + _SLA_FOOTER


def _po(pfile: str = "", *, inline: bool = False) -> str:
    """Return a PAGEOBJECT element with the given PFILE."""
    attrs = [f'PFILE="{pfile}"']
    if inline:
        attrs.append('isInlineImage="1"')
        attrs.append('inlineImageExt="png"')
        attrs.append('ImageData="QUJD"')
    return f"    <PAGEOBJECT {' '.join(attrs)}/>"


def _write_sla(root: Path, slug: str, body: str) -> Path:
    tdir = root / "templates" / slug
    tdir.mkdir(parents=True, exist_ok=True)
    p = tdir / "template.sla"
    p.write_text(body, encoding="utf-8")
    return p


class CheckNoAbsolutePathsInSLATests(unittest.TestCase):
    def _tmp_root(self) -> Path:
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="cnap-test-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        return tmp

    # --- 1. Unix absolute → exit 1 -----------------------------------------
    def test_unix_absolute_workspace(self) -> None:
        tmp = self._tmp_root()
        _write_sla(tmp, "t1", _wrap_pageobjects([_po("/workspace/foo.png")]))
        rc = cnap.main(["--root", str(tmp)])
        self.assertEqual(rc, 1)

    # --- 2. Other Unix roots → exit 1 --------------------------------------
    def test_unix_other_roots(self) -> None:
        cases = [
            "/home/x/y.png",
            "/Users/u/p.png",
            "/var/tmp/q.png",
            "/private/var/z.png",
            "/root/a.png",
            "/tmp/b.png",
        ]
        for path in cases:
            with self.subTest(path=path):
                tmp = self._tmp_root()
                _write_sla(tmp, "t", _wrap_pageobjects([_po(path)]))
                self.assertEqual(cnap.main(["--root", str(tmp)]), 1)

    # --- 3. file:// URI → exit 1 -------------------------------------------
    def test_file_uri(self) -> None:
        tmp = self._tmp_root()
        _write_sla(tmp, "t", _wrap_pageobjects([_po("file:///workspace/foo.png")]))
        self.assertEqual(cnap.main(["--root", str(tmp)]), 1)

    # --- 4. Windows drive → exit 1 -----------------------------------------
    def test_windows_drive(self) -> None:
        for path in ("C:\\foo.png", "D:/bar.png", "z:/x.png"):
            with self.subTest(path=path):
                tmp = self._tmp_root()
                _write_sla(tmp, "t", _wrap_pageobjects([_po(path)]))
                self.assertEqual(cnap.main(["--root", str(tmp)]), 1)

    # --- 5. Empty PFILE with inline image → exit 0 -------------------------
    def test_empty_pfile_inline_ok(self) -> None:
        tmp = self._tmp_root()
        _write_sla(tmp, "t", _wrap_pageobjects([_po("", inline=True)]))
        self.assertEqual(cnap.main(["--root", str(tmp)]), 0)

    # --- 6. Relative PFILE → exit 0 ----------------------------------------
    def test_relative_paths_ok(self) -> None:
        for path in (
            "assets/foo.png",
            "../shared/x.png",
            "shared/assets/slug/y.png",
        ):
            with self.subTest(path=path):
                tmp = self._tmp_root()
                _write_sla(tmp, "t", _wrap_pageobjects([_po(path)]))
                self.assertEqual(cnap.main(["--root", str(tmp)]), 0)

    # --- 7. No SLAs anywhere → exit 0 --------------------------------------
    def test_empty_templates_dir(self) -> None:
        tmp = self._tmp_root()
        (tmp / "templates").mkdir(parents=True, exist_ok=True)
        self.assertEqual(cnap.main(["--root", str(tmp)]), 0)

    # --- 8. Multiple failures across templates → exit 1, both reported -----
    def test_multiple_failures(self) -> None:
        tmp = self._tmp_root()
        _write_sla(tmp, "t1", _wrap_pageobjects([_po("/workspace/a.png")]))
        _write_sla(tmp, "t2", _wrap_pageobjects([_po("/home/b.png")]))
        # Verify failure list directly.
        failures = cnap.find_absolute_pfiles(tmp)
        self.assertEqual(len(failures), 2)
        slas = {f[0].name for f in failures}
        self.assertEqual(slas, {"template.sla"})
        self.assertEqual(cnap.main(["--root", str(tmp)]), 1)


if __name__ == "__main__":
    unittest.main()
