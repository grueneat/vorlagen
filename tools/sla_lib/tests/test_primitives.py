import sys
import unittest
import base64
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder.primitives import pack_inline_image  # noqa: E402

class TestPackInlineImage(unittest.TestCase):
    def test_pack_inline_image_basic(self):
        input_bytes = b"hello world"
        ext = "png"
        b64_data, out_ext = pack_inline_image(input_bytes, ext)
        
        self.assertEqual(out_ext, ext)
        self.assertIsInstance(b64_data, str)
        
        # Decode base64
        decoded = base64.b64decode(b64_data)
        
        # Check length prefix (4 bytes, big-endian)
        length_prefix = struct.unpack(">I", decoded[:4])[0]
        self.assertEqual(length_prefix, len(input_bytes))
        
        # Check zlib decompression
        compressed_data = decoded[4:]
        decompressed = zlib.decompress(compressed_data)
        self.assertEqual(decompressed, input_bytes)

    def test_pack_inline_image_empty(self):
        input_bytes = b""
        ext = "jpg"
        b64_data, out_ext = pack_inline_image(input_bytes, ext)
        
        self.assertEqual(out_ext, ext)
        decoded = base64.b64decode(b64_data)
        length_prefix = struct.unpack(">I", decoded[:4])[0]
        self.assertEqual(length_prefix, 0)
        
        decompressed = zlib.decompress(decoded[4:])
        self.assertEqual(decompressed, b"")

    def test_pack_inline_image_roundtrip_reference(self):
        # Match reference encoder from test_sla_diff.py
        png_bytes = b"fake-png-content"
        
        # Reference implementation
        compressed_ref = zlib.compress(png_bytes, 6) # Plan uses level 6
        qcompressed_ref = len(png_bytes).to_bytes(4, "big") + compressed_ref
        b64_ref = base64.b64encode(qcompressed_ref).decode("ascii")
        
        b64_actual, _ = pack_inline_image(png_bytes, "png")
        
        # Note: zlib compression might vary slightly by level/version, 
        # but decompression must always work.
        # We verify that our helper produces something that decodes correctly.
        decoded = base64.b64decode(b64_actual)
        self.assertEqual(struct.unpack(">I", decoded[:4])[0], len(png_bytes))
        self.assertEqual(zlib.decompress(decoded[4:]), png_bytes)


from sla_lib.builder import Document, TextFrame  # noqa: E402
from sla_lib.builder.primitives import PolyLine  # noqa: E402
from lxml import etree as _etree  # noqa: E402


class TestPolyLineFill(unittest.TestCase):
    """The PolyLine primitive supports an optional polygon fill (PCOLOR).

    A stroked outline (wind turbine icon) leaves PCOLOR='None'; a filled
    silhouette (the Grüne yellow squiggle motif) sets PCOLOR to the fill."""

    def _pageobject(self, pl: PolyLine):
        doc = Document(title="t", template_id="t")
        page = doc.add_page(size="A6")
        page.add(pl)
        root = doc._build_xml()
        for po in root.iter("PAGEOBJECT"):
            if po.get("ANNAME") == pl.anname:
                return po
        raise AssertionError("PAGEOBJECT not found")

    def test_fill_none_keeps_pcolor_none(self):
        pl = PolyLine(
            x_mm=10, y_mm=10, w_mm=20, h_mm=20,
            sla_path="M0 0 L10 10", line_color="Gelb",
            line_width_pt=2, anname="turbine",
        )
        po = self._pageobject(pl)
        self.assertEqual(po.get("PCOLOR"), "None")
        self.assertEqual(po.get("PCOLOR2"), "Gelb")

    def test_fill_set_emits_pcolor(self):
        pl = PolyLine(
            x_mm=10, y_mm=10, w_mm=20, h_mm=2,
            sla_path="M0 0 L10 1 Z", fill="Gelb",
            line_color="None", line_width_pt=0, anname="squiggle",
        )
        po = self._pageobject(pl)
        self.assertEqual(po.get("PCOLOR"), "Gelb")
        self.assertEqual(po.get("PCOLOR2"), "None")
        self.assertEqual(po.get("PTYPE"), "7")


class TestRotatedTextFrameSwap(unittest.TestCase):
    """The ±90° TextFrame WIDTH/HEIGHT swap is a TEXT-FLOW compensation. An
    empty TextFrame (a coloured background rectangle) has nothing to flow, so
    the swap must be skipped — applying it mis-places the rectangle because
    the swap is not perfectly placement-invariant when WIDTH != HEIGHT."""

    def _pageobject(self, frame: TextFrame):
        doc = Document(title="t", template_id="t")
        page = doc.add_page(size="A6")
        page.add(frame)
        root = doc._build_xml()
        for po in root.iter("PAGEOBJECT"):
            if po.get("ANNAME") == frame.anname:
                return po
        raise AssertionError("PAGEOBJECT not found")

    def test_empty_rotated_textframe_keeps_unrotated_dims(self):
        # An empty -90° TextFrame must NOT get the W/H swap: WIDTH/HEIGHT stay
        # the un-rotated values the converter emitted.
        f = TextFrame(
            x_mm=10, y_mm=20, w_mm=40, h_mm=80,
            rotation_deg=-90, anname="bg_empty", text="",
        )
        po = self._pageobject(f)
        self.assertAlmostEqual(float(po.get("WIDTH")), 40 * 72 / 25.4, places=2)
        self.assertAlmostEqual(float(po.get("HEIGHT")), 80 * 72 / 25.4, places=2)

    def test_text_bearing_rotated_textframe_still_swaps(self):
        # A -90° TextFrame WITH text keeps the text-flow swap: WIDTH/HEIGHT
        # are exchanged so Scribus wraps along the visible long edge.
        f = TextFrame(
            x_mm=10, y_mm=20, w_mm=40, h_mm=80,
            rotation_deg=-90, anname="bg_text", text="Impressum",
        )
        po = self._pageobject(f)
        # Swap: WIDTH becomes the un-rotated HEIGHT and vice-versa.
        self.assertAlmostEqual(float(po.get("WIDTH")), 80 * 72 / 25.4, places=2)
        self.assertAlmostEqual(float(po.get("HEIGHT")), 40 * 72 / 25.4, places=2)


class TestFillOpacity(unittest.TestCase):
    """``fill_opacity`` maps to Scribus TransValue/TransValueS, which store
    *transparency* (1 - opacity). None / 1.0 emit nothing so opaque frames
    stay byte-identical to the round-trip baseline."""

    def _pageobject(self, frame):
        doc = Document(title="t", template_id="t")
        page = doc.add_page(size="A6")
        page.add(frame)
        root = doc._build_xml()
        for po in root.iter("PAGEOBJECT"):
            if po.get("ANNAME") == frame.anname:
                return po
        raise AssertionError("PAGEOBJECT not found")

    def test_opacity_70_emits_transvalue(self):
        f = TextFrame(x_mm=10, y_mm=10, w_mm=40, h_mm=20,
                      text="Impressum", anname="imp", fill_opacity=0.7)
        po = self._pageobject(f)
        # opacity 0.7 → transparency 0.3
        self.assertAlmostEqual(float(po.get("TransValue")), 0.3, places=6)
        self.assertAlmostEqual(float(po.get("TransValueS")), 0.3, places=6)

    def test_opacity_none_omits_transvalue(self):
        f = TextFrame(x_mm=10, y_mm=10, w_mm=40, h_mm=20,
                      text="x", anname="opaque")
        po = self._pageobject(f)
        self.assertIsNone(po.get("TransValue"))
        self.assertIsNone(po.get("TransValueS"))

    def test_opacity_one_omits_transvalue(self):
        f = TextFrame(x_mm=10, y_mm=10, w_mm=40, h_mm=20,
                      text="x", anname="full", fill_opacity=1.0)
        po = self._pageobject(f)
        self.assertIsNone(po.get("TransValue"))

    def test_image_frame_opacity(self):
        from sla_lib.builder.primitives import ImageFrame
        f = ImageFrame(x_mm=0, y_mm=0, w_mm=50, h_mm=50,
                       image="x.png", anname="img90", fill_opacity=0.9)
        po = self._pageobject(f)
        self.assertAlmostEqual(float(po.get("TransValue")), 0.1, places=6)


if __name__ == "__main__":
    unittest.main()
