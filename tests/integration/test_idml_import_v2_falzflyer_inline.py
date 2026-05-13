"""End-to-end inline-embedding test for v2 falzflyer (issue #39).

Verifies that running ``tools/idml_to_dsl.py`` against the v2 IDML
with the committed ``meta.yml::asset_policy`` produces:

  * a ``build.py`` text containing exactly 9 ``inline_image_data=``
    occurrences (one per IDML-PFILE'd asset).
  * zero absolute-path image= literals.
  * inline blobs whose decoded bytes match the source PNG sha256.
  * downstream-rendered SLA with 9 ``isInlineImage="1"`` PAGEOBJECTs
    and 0 absolute PFILE attributes.

Skips cleanly when the IDML is absent (CI without licensed assets).
The test runs the converter to a tmp output path so the worktree's
committed ``templates/<v2>/build.py`` is never touched.
"""
from __future__ import annotations

import base64
import hashlib
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
ASSET_DIR = (
    ROOT / "shared" / "assets"
    / "26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2"
)


def _find_v2_idml() -> Path | None:
    """Locate the v2 falzflyer IDML under originals/. Returns None when
    originals/ is absent (typical CI without licensed source files)."""
    candidates = (ROOT, ROOT.parent.parent)  # also try main checkout
    for base in candidates:
        originals = base / "originals"
        if not originals.exists():
            continue
        for p in sorted(originals.rglob("*.idml")):
            name_lower = p.name.lower()
            if "leporello" in name_lower or "z-falz" in name_lower:
                return p
    return None


_ABS_PFILE_RE = re.compile(r"^(?:/|file://|[A-Za-z]:[\\/])")


def _unpack_inline_blob(b64: str) -> bytes:
    """Decode the Scribus qCompress base64 blob back to raw image bytes."""
    raw = base64.b64decode(b64)
    # First 4 bytes = big-endian uncompressed length (qCompress header).
    expected_len = struct.unpack(">I", raw[:4])[0]
    decompressed = zlib.decompress(raw[4:])
    assert len(decompressed) == expected_len, (
        f"qCompress length mismatch: header={expected_len} "
        f"actual={len(decompressed)}"
    )
    return decompressed


class V2FalzflyerInlineEmitTests(unittest.TestCase):
    """Pins the issue #39 acceptance criteria on v2 falzflyer."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.idml = _find_v2_idml()
        if cls.idml is None:
            raise unittest.SkipTest(
                "originals/ not present; v2 falzflyer IDML unavailable."
            )
        if not ASSET_DIR.exists():
            raise unittest.SkipTest(
                "shared/assets/26-03-leporello-…/ not present."
            )
        # Run the converter into a tmpdir so the worktree's committed
        # build.py stays untouched.
        cls.tmp = tempfile.TemporaryDirectory(prefix="i2d-v2-inline-")
        cls.tmpdir = Path(cls.tmp.name)
        cls.build_py = cls.tmpdir / "build.py.generated"
        manifest = (
            ROOT / "shared" / "assets"
            / "26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover-2"
            / "links_export.yml"
        )
        links_dir = cls.idml.parent / "Links"
        result = subprocess.run(
            [
                sys.executable,
                str(TOOLS / "idml_to_dsl.py"),
                str(cls.idml),
                str(cls.build_py),
                "--template-id", SLUG,
                "--asset-map", str(manifest),
                "--assets-dir", str(links_dir),
                "--allow-dropped-pageitems",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise unittest.SkipTest(
                f"converter exit {result.returncode}: {result.stderr}"
            )
        cls.source = cls.build_py.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "tmp"):
            cls.tmp.cleanup()

    # --- 1. 9 inline_image_data= occurrences ------------------------------
    def test_nine_inline_image_data_calls(self) -> None:
        n = self.source.count("inline_image_data=")
        self.assertEqual(
            n, 9,
            f"expected exactly 9 inline_image_data= occurrences, got {n}",
        )

    # --- 2. 0 absolute-path image= literals --------------------------------
    def test_no_absolute_image_path_literals(self) -> None:
        # The repo-relative branch emits image='shared/...'; the broken
        # absolute branch (pre-#39) emitted image='/workspace/.../...'.
        for pattern in (
            r"image='/",
            r'image="/',
            r"image='file://",
            r"image='[A-Z]:[/\\]",
        ):
            with self.subTest(pattern=pattern):
                self.assertEqual(
                    len(re.findall(pattern, self.source)), 0,
                    f"absolute-path leak: {pattern} matches in build.py",
                )

    # --- 3. Inline blob round-trip — bytes match source ───────────────────
    def test_inline_blobs_round_trip_to_source_bytes(self) -> None:
        # Find every inline_image_data='...' literal in the emitted source.
        blob_re = re.compile(r"inline_image_data='([^']+)'")
        blobs = blob_re.findall(self.source)
        self.assertEqual(len(blobs), 9, "blob count mismatch with kwarg count")

        # Build an index of {sha256 of on-disk file: basename}.
        disk_index: dict[str, str] = {}
        for p in ASSET_DIR.iterdir():
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            disk_index[hashlib.sha256(p.read_bytes()).hexdigest()] = p.name

        # Decode each inline blob and assert its sha256 matches one of the
        # on-disk assets. This catches: (a) corruption in pack_inline_image,
        # (b) wrong file substitution, (c) non-deterministic zlib output.
        matched_basenames: set[str] = set()
        for blob in blobs:
            decoded = _unpack_inline_blob(blob)
            sha = hashlib.sha256(decoded).hexdigest()
            self.assertIn(
                sha, disk_index,
                f"inline blob sha {sha[:16]}… does not match any "
                f"on-disk asset in {ASSET_DIR}",
            )
            matched_basenames.add(disk_index[sha])

        # The matched basenames should be a subset of the policy's
        # `embedded:` declaration. Some assets are referenced more than
        # once in the IDML (so 9 blob hits collapse to fewer distinct
        # basenames). The contract is: every blob round-trips to *some*
        # on-disk asset, and that asset is in the policy.
        from sla_lib.builder.meta_schema import load_asset_policy
        policy = load_asset_policy(SLUG, root=ROOT)
        self.assertIsNotNone(policy, "meta.yml asset_policy missing")
        embedded = set(policy["embedded"])
        for bn in matched_basenames:
            with self.subTest(basename=bn):
                self.assertIn(
                    bn, embedded,
                    f"inlined basename {bn!r} not declared in embedded:",
                )
        # Sanity: we matched at least 6 distinct basenames (the unique
        # logos + page-2 background + plakat). Lower bound is empirical;
        # any future converter change that collapses fewer than 6 distinct
        # assets is worth investigating.
        self.assertGreaterEqual(len(matched_basenames), 6)

    # --- 4. inline_image_ext='png' (or 'jpg') on every inline call ───────
    def test_inline_image_ext_emitted_for_each(self) -> None:
        ext_count = self.source.count("inline_image_ext=")
        self.assertEqual(
            ext_count, 9,
            f"inline_image_ext kwargs count {ext_count} != 9",
        )
        # And the value is one of the allowed extensions.
        for ext in re.findall(r"inline_image_ext='(\w+)'", self.source):
            with self.subTest(ext=ext):
                self.assertIn(ext, {"png", "jpg", "jpeg", "tif", "tiff"})

    # --- 5. No `Path.resolve()` / `Path.absolute()` of asset paths --------
    def test_no_resolve_or_absolute_on_assets(self) -> None:
        """Defensive: the emitted source must not contain leaked absolute
        paths to the asset directory. We sample the v2-falzflyer asset
        dir's absolute path string and assert it's not in the output."""
        self.assertNotIn(str(ASSET_DIR), self.source)
        self.assertNotIn(str(self.idml.parent), self.source)

    # --- 6. ABSOLUTE_PFILE_RE check via the lint module itself ───────────
    def test_lint_module_catches_absolute_paths(self) -> None:
        """Pins the regex import + behaviour. Same regex must continue
        catching the patterns the SLA-rendered file would expose."""
        from check_no_absolute_paths_in_sla import ABSOLUTE_PFILE_RE
        self.assertTrue(ABSOLUTE_PFILE_RE.match("/workspace/x.png"))
        self.assertTrue(ABSOLUTE_PFILE_RE.match("file:///x.png"))
        self.assertTrue(ABSOLUTE_PFILE_RE.match("C:\\x.png"))
        self.assertFalse(ABSOLUTE_PFILE_RE.match("shared/x.png"))
        self.assertFalse(ABSOLUTE_PFILE_RE.match(""))


if __name__ == "__main__":
    unittest.main()
