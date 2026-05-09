"""Smoke test for templates/wahlaufruf-postkarte-a6-quer/.

V1 (Issue #17 — "Symbol-Tight") layout invariants:

- 2 pages, A6 quer trim
- Front: Dunkelgrün full-bleed Polygon (D12 carries through V1)
- Front: Wahlkreuz frame present with inline image data + asset round-trip
- Front: wahlkreuz_halo Polygon present (Hellgrün, ellipse, layer=0,
  centers (74, 48) match Wahlkreuz centers)
- Front: headline_datum + headline_cta TextFrames at correct y stack
- Back: 6 frage_*_* TextFrames (3 W-Fragen × {headline, body}) on a single
  left axis (x=6) with body anchored 1mm below headline
- Back: logo_back ImageFrame uses gruene-weiss.png at (96, 8, 18.9, 5.7)
  with explicit local_scale=(0.130, 0.130)
- Back: qr_label / qr_code / qr_url stack at x=96, y=24/31/71
- Back: Impressum present (tightened to y=101.5, h=4 in V1)
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

PT_PER_MM = 72.0 / 25.4


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
        # page_geom maps OwnPage int → (PAGEXPOS_pt, PAGEYPOS_pt) for
        # converting absolute XPOS/YPOS attributes back to page-relative mm.
        cls.page_geom = {}
        for p in cls.doc.findall("PAGE"):
            if "NUM" in p.attrib:
                cls.page_geom[int(p.attrib["NUM"])] = {
                    "xpos_pt": float(p.attrib["PAGEXPOS"]),
                    "ypos_pt": float(p.attrib["PAGEYPOS"]),
                    "w_pt": float(p.attrib["PAGEWIDTH"]),
                    "h_pt": float(p.attrib["PAGEHEIGHT"]),
                }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _frame_by_anname(self, anname: str, own_page: int | None = None):
        """Return the PAGEOBJECT element with matching ANNAME (and optional page)."""
        for po in self.doc.findall("PAGEOBJECT"):
            if po.attrib.get("ANNAME") != anname:
                continue
            if own_page is not None and int(po.attrib.get("OwnPage", "0")) != own_page:
                continue
            return po
        return None

    def _frame_geom_mm(self, po):
        """Return page-relative (x_mm, y_mm, w_mm, h_mm) for a PAGEOBJECT."""
        own = int(po.attrib.get("OwnPage", "0"))
        g = self.page_geom[own]
        x_mm = (float(po.attrib["XPOS"]) - g["xpos_pt"]) / PT_PER_MM
        y_mm = (float(po.attrib["YPOS"]) - g["ypos_pt"]) / PT_PER_MM
        w_mm = float(po.attrib["WIDTH"]) / PT_PER_MM
        h_mm = float(po.attrib["HEIGHT"]) / PT_PER_MM
        return x_mm, y_mm, w_mm, h_mm

    # ------------------------------------------------------------------
    # Carry-over invariants (kept from pre-V1 — D12 contract still holds)
    # ------------------------------------------------------------------
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
        bgs = [po for po in front_page_objs
               if po.attrib.get("PTYPE") == "6"
               and po.attrib.get("ANNAME", "").startswith("Seitenhintergrund")]
        self.assertEqual(len(bgs), 1, "expected 1 Seitenhintergrund on front")
        self.assertEqual(bgs[0].attrib.get("PCOLOR"), "Dunkelgrün",
                         "D12 violation: front bg must be Dunkelgrün")

    def test_wahlkreuz_frame_present_with_inline_image(self):
        po = self._frame_by_anname("Wahlkreuz", own_page=0)
        self.assertIsNotNone(po, "Wahlkreuz frame not found on front")
        self.assertEqual(po.attrib.get("PTYPE"), "2", "Wahlkreuz must be ImageFrame")
        self.assertEqual(po.attrib.get("isInlineImage", "0"), "1")
        data = po.attrib.get("ImageData", "")
        self.assertTrue(len(data) > 100, "inline ImageData too small")

    def test_wahlkreuz_inline_data_roundtrips_to_asset(self):
        """qCompress decode of Wahlkreuz inline data must equal the shared asset bytes."""
        po = self._frame_by_anname("Wahlkreuz", own_page=0)
        self.assertIsNotNone(po)
        data = po.attrib["ImageData"]
        decoded = _qcompress_decode(data)
        expected = WAHLKREUZ_PATH.read_bytes()
        self.assertEqual(
            len(decoded), len(expected),
            f"decoded {len(decoded)} != asset {len(expected)}",
        )
        self.assertEqual(decoded, expected,
                         "Wahlkreuz inline bytes don't match asset")

    def test_impressum_present(self):
        annames = {po.attrib.get("ANNAME", "") for po in self.doc.findall("PAGEOBJECT")}
        self.assertIn("Impressum", annames)

    def test_no_frame_outside_trim_plus_bleed(self):
        bleed_pt = 3.0 * 72.0 / 25.4
        for po in self.doc.findall("PAGEOBJECT"):
            anname = po.attrib.get("ANNAME", "")
            # Background polys are intentionally outside trim by bleed amount.
            if (anname.startswith("Seitenhintergrund")
                    or anname == "seitenhintergrund_back_left"):
                continue
            ownp = int(po.attrib.get("OwnPage", "0"))
            if ownp not in self.page_geom:
                continue
            g = self.page_geom[ownp]
            x = float(po.attrib["XPOS"]) - g["xpos_pt"]
            y = float(po.attrib["YPOS"]) - g["ypos_pt"]
            w = float(po.attrib["WIDTH"])
            h = float(po.attrib["HEIGHT"])
            self.assertGreaterEqual(x, -bleed_pt - 0.5,
                                    f"{anname} extends left of bleed: {x}")
            self.assertGreaterEqual(y, -bleed_pt - 0.5,
                                    f"{anname} extends above bleed: {y}")
            self.assertLessEqual(x + w, g["w_pt"] + bleed_pt + 0.5,
                                 f"{anname} extends right of bleed: {x+w} (page w={g['w_pt']})")
            self.assertLessEqual(y + h, g["h_pt"] + bleed_pt + 0.5,
                                 f"{anname} extends below bleed: {y+h} (page h={g['h_pt']})")

    # ------------------------------------------------------------------
    # V1 layout invariants
    # ------------------------------------------------------------------
    def test_back_has_3_w_fragen(self):
        """V1 (Issue #17): back replaces 4-Cells grid with 3 W-Frage stacks."""
        annames = [
            "frage_was_headline", "frage_was_body",
            "frage_warum_headline", "frage_warum_body",
            "frage_wann_headline", "frage_wann_body",
        ]
        for an in annames:
            po = self._frame_by_anname(an, own_page=1)
            self.assertIsNotNone(po, f"missing W-Frage frame: {an}")
        # Stale 4-Cells frames must be gone.
        for po in self.doc.findall("PAGEOBJECT"):
            an = po.attrib.get("ANNAME", "")
            self.assertFalse(
                an.startswith("Cell "),
                f"V1 deletes the 4-Cells loop; found stale frame: {an!r}",
            )
        # All 6 frames sit on the same left axis at x=6 ±0.5.
        for an in annames:
            x_mm, _, _, _ = self._frame_geom_mm(self._frame_by_anname(an, own_page=1))
            self.assertAlmostEqual(x_mm, 6.0, delta=0.5,
                                   msg=f"{an}.x_mm should be 6.0; got {x_mm}")
        # Per-stack body anchors 1mm below its headline.
        for stem in ("was", "warum", "wann"):
            hd = self._frame_by_anname(f"frage_{stem}_headline", own_page=1)
            bd = self._frame_by_anname(f"frage_{stem}_body", own_page=1)
            _, hd_y, _, hd_h = self._frame_geom_mm(hd)
            _, bd_y, _, _ = self._frame_geom_mm(bd)
            expected = hd_y + hd_h + 1.0
            self.assertAlmostEqual(
                bd_y, expected, delta=0.5,
                msg=(f"frage_{stem}_body.y should be headline.y+h+1; "
                     f"got {bd_y}, expected {expected}"),
            )

    def test_front_has_halo_and_wahlkreuz(self):
        """V1 (Issue #17): Hellgrün ellipse halo behind the Wahlkreuz, centered (74, 48)."""
        halo = self._frame_by_anname("wahlkreuz_halo", own_page=0)
        self.assertIsNotNone(halo, "wahlkreuz_halo Polygon missing on front")
        self.assertEqual(halo.attrib.get("PTYPE"), "6",
                         "wahlkreuz_halo must be a Polygon (PTYPE=6)")
        # FRTYPE=1 == ellipse (Polygon.shape='ellipse' default emit).
        self.assertEqual(halo.attrib.get("FRTYPE"), "1",
                         "wahlkreuz_halo must be an ellipse (FRTYPE=1)")
        self.assertEqual(halo.attrib.get("PCOLOR"), "Hellgrün",
                         "wahlkreuz_halo fill must be Hellgrün")
        self.assertEqual(halo.attrib.get("LAYER"), "0",
                         "wahlkreuz_halo must be on layer 0 (background)")

        wk = self._frame_by_anname("Wahlkreuz", own_page=0)
        self.assertIsNotNone(wk, "Wahlkreuz frame missing on front")

        # Center alignment: both centers should be at (74, 48) ±0.5.
        hx, hy, hw, hh = self._frame_geom_mm(halo)
        wx, wy, ww, wh = self._frame_geom_mm(wk)
        self.assertAlmostEqual(hx + hw / 2.0, 74.0, delta=0.5,
                               msg=f"halo center_x={hx + hw / 2.0}, expected 74.0")
        self.assertAlmostEqual(wx + ww / 2.0, 74.0, delta=0.5,
                               msg=f"wahlkreuz center_x={wx + ww / 2.0}, expected 74.0")
        self.assertAlmostEqual(hy + hh / 2.0, 48.0, delta=0.5,
                               msg=f"halo center_y={hy + hh / 2.0}, expected 48.0")
        self.assertAlmostEqual(wy + wh / 2.0, 48.0, delta=0.5,
                               msg=f"wahlkreuz center_y={wy + wh / 2.0}, expected 48.0")

    def test_front_has_datum_and_cta(self):
        """V1 (Issue #17): two-line front headline stack with a 10mm vertical hierarchy."""
        datum = self._frame_by_anname("headline_datum", own_page=0)
        cta = self._frame_by_anname("headline_cta", own_page=0)
        self.assertIsNotNone(datum, "headline_datum TextFrame missing on front")
        self.assertIsNotNone(cta, "headline_cta TextFrame missing on front")
        _, dy, _, _ = self._frame_geom_mm(datum)
        _, cy, _, _ = self._frame_geom_mm(cta)
        self.assertAlmostEqual(
            cy - dy, 10.0, delta=0.5,
            msg=f"headline_cta.y - headline_datum.y should be 10.0; got {cy - dy}",
        )

    def test_back_has_qr_label_and_url(self):
        """V1 (Issue #17): QR stack at x=96, y=24/31/71 (LOCKED — not 24/30/68)."""
        for an, expected_y in (("qr_label", 24.0),
                               ("qr_code", 31.0),
                               ("qr_url", 71.0)):
            po = self._frame_by_anname(an, own_page=1)
            self.assertIsNotNone(po, f"missing QR-stack frame: {an}")
            x_mm, y_mm, _, _ = self._frame_geom_mm(po)
            self.assertAlmostEqual(x_mm, 96.0, delta=0.5,
                                   msg=f"{an}.x_mm should be 96.0; got {x_mm}")
            self.assertAlmostEqual(y_mm, expected_y, delta=0.5,
                                   msg=f"{an}.y_mm should be {expected_y}; got {y_mm}")

    def test_back_has_logo_back_white(self):
        """V1 (Issue #17): back logo migrated to gruene-weiss.png at (96, 8, 18.9, 5.7)."""
        po = self._frame_by_anname("logo_back", own_page=1)
        self.assertIsNotNone(po, "logo_back ImageFrame missing on back")
        self.assertEqual(po.attrib.get("PTYPE"), "2",
                         "logo_back must be an ImageFrame (PTYPE=2)")
        x_mm, y_mm, w_mm, h_mm = self._frame_geom_mm(po)
        self.assertAlmostEqual(x_mm, 96.0, delta=0.5)
        self.assertAlmostEqual(y_mm, 8.0, delta=0.5)
        self.assertAlmostEqual(w_mm, 18.9, delta=0.5)
        self.assertAlmostEqual(h_mm, 5.7, delta=0.5)
        # Explicit local_scale=(0.130, 0.130) — defaults to (1.0, 1.0)
        # which would render the asset at 5.5× and clip.
        self.assertAlmostEqual(float(po.attrib["LOCALSCX"]), 0.130, delta=0.001,
                               msg=f"logo_back LOCALSCX should be 0.130; "
                                   f"got {po.attrib['LOCALSCX']}")
        self.assertAlmostEqual(float(po.attrib["LOCALSCY"]), 0.130, delta=0.001,
                               msg=f"logo_back LOCALSCY should be 0.130; "
                                   f"got {po.attrib['LOCALSCY']}")
        # Asset round-trip: decoded inline bytes match shared/logos/gruene-weiss.png.
        data = po.attrib.get("ImageData", "")
        self.assertTrue(len(data) > 100, "logo_back inline ImageData too small")
        decoded = _qcompress_decode(data)
        expected = (ROOT / "shared" / "logos" / "gruene-weiss.png").read_bytes()
        self.assertEqual(
            decoded, expected,
            "logo_back inline bytes don't match shared/logos/gruene-weiss.png",
        )


if __name__ == "__main__":
    unittest.main()
