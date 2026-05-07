"""Smoke test for templates/wahlaufruf-postkarte-a6-quer/.

Verifies:
- 2 pages, A6 quer trim
- Front has Dunkelgrün full-bleed Polygon (D12)
- Wahlkreuz frame present with inline image data
- Wahlkreuz inline_image_data round-trips to shared/assets/wahlkreuz.png
- Back has 4 cell-headline + 4 cell-body frames (2×2 grid)
- Impressum present
- No frame outside trim+bleed
"""
from __future__ import annotations
import base64
import importlib.util
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from lxml import etree  # noqa: E402

TEMPLATE_DIR = ROOT / "templates" / "wahlaufruf-postkarte-a6-quer"
WAHLKREUZ_PATH = ROOT / "shared" / "assets" / "wahlkreuz.png"


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "wahlaufruf_build", TEMPLATE_DIR / "build.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _qcompress_decode(b64: str) -> bytes:
    """Inverse of pack_inline_image: returns the original raster bytes."""
    blob = base64.b64decode(b64)
    length = struct.unpack(">I", blob[:4])[0]
    raw = zlib.decompress(blob[4:])
    assert len(raw) == length, f"qCompress length mismatch: {len(raw)} != {length}"
    return raw


class WahlaufrufPostkarteA6QuerSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
        cls.tmp.close()
        mod = _load_build_module()
        mod.build(out_path=cls.tmp.name)
        cls.tree = etree.parse(cls.tmp.name)
        cls.root = cls.tree.getroot()
        cls.doc = cls.root.find("DOCUMENT")

    def test_page_count(self):
        pages = self.doc.findall("PAGE")
        self.assertEqual(len(pages), 2, f"expected 2 pages, found {len(pages)}")

    def test_trim_dimensions(self):
        for page in self.doc.findall("PAGE"):
            w = float(page.attrib["PAGEWIDTH"])
            h = float(page.attrib["PAGEHEIGHT"])
            # 148 mm = 419.5 pt; 105 mm = 297.6 pt
            self.assertAlmostEqual(w, 148.0 * 72.0 / 25.4, places=1)
            self.assertAlmostEqual(h, 105.0 * 72.0 / 25.4, places=1)

    def test_d12_dunkelgruen_background_on_front(self):
        """D12: Wahlkreuz must be on a colored brand background."""
        front_page_objs = [
            po for po in self.doc.findall("PAGEOBJECT")
            if po.attrib.get("OwnPage") == "0"
        ]
        # Find background polygon (PTYPE=6)
        bgs = [po for po in front_page_objs
               if po.attrib.get("PTYPE") == "6"
               and po.attrib.get("ANNAME", "").startswith("Seitenhintergrund")]
        self.assertEqual(len(bgs), 1, "expected 1 Seitenhintergrund on front")
        self.assertEqual(bgs[0].attrib.get("PCOLOR"), "Dunkelgrün",
                         "D12 violation: front bg must be Dunkelgrün")

    def test_wahlkreuz_frame_present_with_inline_image(self):
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == "Wahlkreuz":
                self.assertEqual(po.attrib.get("PTYPE"), "2", "Wahlkreuz must be ImageFrame")
                self.assertEqual(po.attrib.get("isInlineImage", "0"), "1")
                data = po.attrib.get("ImageData", "")
                self.assertTrue(len(data) > 100, "inline ImageData too small")
                return
        self.fail("Wahlkreuz frame not found")

    def test_wahlkreuz_inline_data_roundtrips_to_asset(self):
        """qCompress decode of Wahlkreuz inline data must equal the shared asset bytes."""
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") == "Wahlkreuz":
                data = po.attrib["ImageData"]
                decoded = _qcompress_decode(data)
                expected = WAHLKREUZ_PATH.read_bytes()
                self.assertEqual(
                    len(decoded), len(expected),
                    f"decoded {len(decoded)} != asset {len(expected)}",
                )
                self.assertEqual(decoded, expected,
                                 "Wahlkreuz inline bytes don't match asset")
                return
        self.fail("Wahlkreuz frame not found")

    def test_back_has_2x2_grid(self):
        back_objs = [
            po for po in self.doc.findall("PAGEOBJECT")
            if po.attrib.get("OwnPage") == "1"
        ]
        cell_hd = [po for po in back_objs
                   if po.attrib.get("ANNAME", "").startswith("Cell ")
                   and po.attrib.get("ANNAME", "").endswith("— Headline")]
        cell_body = [po for po in back_objs
                     if po.attrib.get("ANNAME", "").startswith("Cell ")
                     and po.attrib.get("ANNAME", "").endswith("— Body")]
        self.assertEqual(len(cell_hd), 4, f"expected 4 cell headlines, got {len(cell_hd)}")
        self.assertEqual(len(cell_body), 4, f"expected 4 cell bodies, got {len(cell_body)}")

    def test_impressum_present(self):
        annames = {po.attrib.get("ANNAME", "") for po in self.doc.findall("PAGEOBJECT")}
        self.assertIn("Impressum", annames)

    def test_no_frame_outside_trim_plus_bleed(self):
        bleed_pt = 3.0 * 72.0 / 25.4
        pages = self.doc.findall("PAGE")
        # Each PAGE has its own xpos, so bind frames to their OwnPage
        page_geom = {
            int(p.attrib["NUM"]): {
                "x": float(p.attrib["PAGEXPOS"]),
                "y": float(p.attrib["PAGEYPOS"]),
                "w": float(p.attrib["PAGEWIDTH"]),
                "h": float(p.attrib["PAGEHEIGHT"]),
            }
            for p in pages if "NUM" in p.attrib
        }
        for po in self.doc.findall("PAGEOBJECT"):
            anname = po.attrib.get("ANNAME", "")
            if anname.startswith("Seitenhintergrund"):
                continue  # bg is intentionally outside trim by bleed amount
            ownp = int(po.attrib.get("OwnPage", "0"))
            if ownp not in page_geom:
                continue
            g = page_geom[ownp]
            x = float(po.attrib["XPOS"]) - g["x"]
            y = float(po.attrib["YPOS"]) - g["y"]
            w = float(po.attrib["WIDTH"])
            h = float(po.attrib["HEIGHT"])
            self.assertGreaterEqual(x, -bleed_pt - 0.5,
                                    f"{anname} extends left of bleed: {x}")
            self.assertGreaterEqual(y, -bleed_pt - 0.5,
                                    f"{anname} extends above bleed: {y}")
            self.assertLessEqual(x + w, g["w"] + bleed_pt + 0.5,
                                 f"{anname} extends right of bleed: {x+w} (page w={g['w']})")
            self.assertLessEqual(y + h, g["h"] + bleed_pt + 0.5,
                                 f"{anname} extends below bleed: {y+h} (page h={g['h']})")


if __name__ == "__main__":
    unittest.main()
