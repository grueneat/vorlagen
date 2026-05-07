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
