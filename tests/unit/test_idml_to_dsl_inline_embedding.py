"""Unit tests for issue #39 inline-embedding emission in tools/idml_to_dsl.py.

These tests exercise the new ``_emit_image_or_inline`` helper directly.
Building a fully synthetic IDML that satisfies the strict 7-phase converter
is prohibitively expensive at the unit-test level; instead these tests pin
the contract that the 3 patched emit sites all route through:

  * basename ∈ embedded_set → emit ``inline_image_data=`` + ``inline_image_ext=``,
    PFILE="" at the dataclass level.
  * basename ∉ embedded_set → emit repo-relative ``image=`` path.
  * abs_path outside ROOT → RuntimeError.
  * No code path ever writes an absolute path into the emitted DSL.

The byte round-trip is checked end-to-end against ``pack_inline_image``
(stdlib zlib level 6 → deterministic) so a regression in the encoding
trips this test.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import idml_to_dsl as i2d  # noqa: E402
from sla_lib.builder.primitives import pack_inline_image  # noqa: E402


# A 1×1 PNG (8 bytes signature + minimal IHDR/IDAT/IEND). Realistic enough
# for zlib determinism checks; small enough to inline in the test file.
_TINY_PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4"
    "890000000A49444154789C6300010000000500010D0A2DB40000000049454E44"
    "AE426082"
)


def _make_ctx(embedded: set[str]) -> i2d._Ctx:
    """Build a minimal _Ctx that the helper accepts. The IDMLPackage
    is never touched; we pass ``pkg=None`` because the helper only
    reads ``ctx.embedded_set`` + ``ctx.out``.
    """
    ctx = i2d._Ctx(pkg=None, template_id="dummy", assets_dir=Path("."))
    ctx.embedded_set = embedded
    return ctx


class EmitImageOrInlineTests(unittest.TestCase):
    """Direct tests for _emit_image_or_inline."""

    def _tmp_root(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="i2d-test-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        return tmp

    # --- 1. Embedded asset emits inline ------------------------------------
    def test_embedded_asset_emits_inline_data(self) -> None:
        tmp = self._tmp_root()
        asset = tmp / "shared" / "assets" / "demo" / "logo.png"
        asset.parent.mkdir(parents=True)
        asset.write_bytes(_TINY_PNG)
        ctx = _make_ctx(embedded={"logo.png"})
        # Force the helper to treat tmp as ROOT (it calls Path.relative_to(ROOT)).
        original_root = i2d.ROOT
        i2d.ROOT = tmp
        try:
            i2d._emit_image_or_inline(
                ctx.out,
                x_mm=10.0, y_mm=20.0, w_mm=30.0, h_mm=40.0, rot=0.0,
                self_id="u1", layer_idx=0,
                abs_path=asset,
                ctx=ctx,
            )
        finally:
            i2d.ROOT = original_root
        rendered = ctx.out.render()
        self.assertIn("inline_image_data=", rendered)
        self.assertIn("inline_image_ext=", rendered)
        # Bytes-on-disk should NEVER leak through.
        self.assertNotIn(str(asset), rendered)

    # --- 2. Inline blob byte round-trip ------------------------------------
    def test_inline_blob_round_trip(self) -> None:
        tmp = self._tmp_root()
        asset = tmp / "shared" / "assets" / "demo" / "logo.png"
        asset.parent.mkdir(parents=True)
        asset.write_bytes(_TINY_PNG)
        expected_blob, expected_ext = pack_inline_image(_TINY_PNG, "png")
        ctx = _make_ctx(embedded={"logo.png"})
        i2d.ROOT_BACKUP, i2d.ROOT = i2d.ROOT, tmp
        try:
            i2d._emit_image_or_inline(
                ctx.out,
                x_mm=0.0, y_mm=0.0, w_mm=10.0, h_mm=10.0, rot=0.0,
                self_id="u1", layer_idx=0,
                abs_path=asset,
                ctx=ctx,
            )
        finally:
            i2d.ROOT = i2d.ROOT_BACKUP
        rendered = ctx.out.render()
        # The expected blob string must appear verbatim in the emitted DSL.
        self.assertIn(expected_blob, rendered)
        # PythonRepr emits string kwargs with single quotes; accept either form.
        self.assertTrue(
            f"'{expected_ext}'" in rendered or f'"{expected_ext}"' in rendered,
            f"emitted DSL missing inline_image_ext={expected_ext}: {rendered}",
        )

    # --- 3. No-policy / non-embedded → relative emit -----------------------
    def test_non_embedded_emits_relative_path(self) -> None:
        tmp = self._tmp_root()
        asset = tmp / "shared" / "assets" / "demo" / "logo.png"
        asset.parent.mkdir(parents=True)
        asset.write_bytes(_TINY_PNG)
        ctx = _make_ctx(embedded=set())
        i2d.ROOT_BACKUP, i2d.ROOT = i2d.ROOT, tmp
        try:
            i2d._emit_image_or_inline(
                ctx.out,
                x_mm=0.0, y_mm=0.0, w_mm=10.0, h_mm=10.0, rot=0.0,
                self_id="u1", layer_idx=0,
                abs_path=asset,
                ctx=ctx,
            )
        finally:
            i2d.ROOT = i2d.ROOT_BACKUP
        rendered = ctx.out.render()
        # Repo-relative path appears.
        self.assertIn("shared/assets/demo/logo.png", rendered)
        # No inline-data kwarg.
        self.assertNotIn("inline_image_data=", rendered)

    # --- 4. No absolute paths anywhere in the emitted DSL ------------------
    def test_no_absolute_paths_ever(self) -> None:
        tmp = self._tmp_root()
        asset = tmp / "shared" / "assets" / "demo" / "logo.png"
        asset.parent.mkdir(parents=True)
        asset.write_bytes(_TINY_PNG)
        ctx_embed = _make_ctx(embedded={"logo.png"})
        ctx_rel = _make_ctx(embedded=set())
        for ctx in (ctx_embed, ctx_rel):
            i2d.ROOT_BACKUP, i2d.ROOT = i2d.ROOT, tmp
            try:
                i2d._emit_image_or_inline(
                    ctx.out,
                    x_mm=0.0, y_mm=0.0, w_mm=10.0, h_mm=10.0, rot=0.0,
                    self_id="u1", layer_idx=0,
                    abs_path=asset,
                    ctx=ctx,
                )
            finally:
                i2d.ROOT = i2d.ROOT_BACKUP
            rendered = ctx.out.render()
            # The full str(tmp) absolute prefix must not appear.
            self.assertNotIn(str(tmp), rendered)
            # Defensive: scan for the kinds of patterns the Phase A lint
            # rejects.
            for needle in ("/workspace/", "/home/", "/tmp/", "/root/", "file://"):
                self.assertNotIn(
                    needle, rendered, f"absolute-path leak: {needle!r}"
                )

    # --- 5. abs_path outside ROOT → RuntimeError ---------------------------
    def test_outside_root_raises(self) -> None:
        tmp = self._tmp_root()
        outside = self._tmp_root() / "outside.png"
        outside.write_bytes(_TINY_PNG)
        ctx = _make_ctx(embedded=set())  # not in embedded → goes to rel path
        i2d.ROOT_BACKUP, i2d.ROOT = i2d.ROOT, tmp
        try:
            with self.assertRaises(RuntimeError):
                i2d._emit_image_or_inline(
                    ctx.out,
                    x_mm=0.0, y_mm=0.0, w_mm=10.0, h_mm=10.0, rot=0.0,
                    self_id="u1", layer_idx=0,
                    abs_path=outside,
                    ctx=ctx,
                )
        finally:
            i2d.ROOT = i2d.ROOT_BACKUP

    # --- 6. _Ctx default embedded_set is empty -----------------------------
    def test_ctx_default_embedded_set_empty(self) -> None:
        ctx = i2d._Ctx(pkg=None, template_id="x", assets_dir=Path("."))
        self.assertEqual(ctx.embedded_set, set())

    # --- 7. Forward-compat note ---------------------------------------------
    def test_forward_compat_unreachable_in_first_pr(self) -> None:
        """Documents (in test form) that the non-embedded relative-path
        branch is forward-compat for Phase D. For the first PR, the audit
        rejects any policy-absent template with assets on disk, so this
        branch only fires for templates WITHOUT shared/assets/<slug>/."""
        # Self-evident, but the assertion guards the documented invariant:
        # _Ctx initialises embedded_set as an empty set when no policy is
        # populated. Any later code that loads a policy with shipped:[],
        # embedded:[file] will inline that file; any code that has no
        # policy gets the empty set and (silently) emits relative paths.
        ctx = i2d._Ctx(pkg=None, template_id="x", assets_dir=Path("."))
        self.assertFalse(ctx.embedded_set)


class CtxFieldDefaultsTests(unittest.TestCase):
    """Pin the new field's default behaviour so the converter never crashes
    on templates without a policy."""

    def test_embedded_set_is_mutable_default(self) -> None:
        # Two _Ctx instances must not share state — the typical
        # field(default_factory=set) trap.
        a = i2d._Ctx(pkg=None, template_id="a", assets_dir=Path("."))
        b = i2d._Ctx(pkg=None, template_id="b", assets_dir=Path("."))
        a.embedded_set.add("only-on-a.png")
        self.assertNotIn("only-on-a.png", b.embedded_set)


if __name__ == "__main__":
    unittest.main()
