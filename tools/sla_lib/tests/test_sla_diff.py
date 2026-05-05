"""Unit tests for tools/sla_diff.py.

Synthetic fixtures are built via the DSL itself plus targeted lxml mutations
on the saved SLAs. Self-diff on each of the three originals must report
``critical=0`` and ``warning=0``.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from base64 import b64encode
from pathlib import Path
import zlib

from lxml import etree

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import sla_diff as sd  # noqa: E402

ORIGINALS = [
    ROOT / "postkarte-vorlage-original.sla",
    ROOT / "plakat-a1-hochformat-original.sla",
    ROOT / "gruene-zeitung-vorlage-original.sla",
]


# ---------------------------------------------------------------------------
# Pipeline-step unit tests (one per step in the 10-step pipeline)
# ---------------------------------------------------------------------------
class NormalisationPipelineTests(unittest.TestCase):
    """One unit test per pipeline step in tools/sla_diff.py.

    Each test mutates a copy of a small original (Postkarte) and asserts the
    pipeline cleans up the mutation.
    """

    @classmethod
    def setUpClass(cls):
        cls.src = ORIGINALS[0]  # Postkarte (smallest / fastest to parse)

    # Step 1: parse with lxml
    def test_step1_parse_returns_tree(self):
        tree = sd.parse_sla(self.src)
        self.assertIsNotNone(tree.getroot().find("DOCUMENT"))

    # Step 2: strip volatile DOC attrs
    def test_step2_strip_volatile_doc_attrs(self):
        tree = sd.parse_sla(self.src)
        doc = tree.getroot().find("DOCUMENT")
        doc.set("DOCSAVED", "2024-01-01")
        doc.set("currentProfile", "Custom Profile")
        sd.strip_volatile_doc_attrs(tree)
        self.assertNotIn("DOCSAVED", doc.attrib)
        self.assertNotIn("currentProfile", doc.attrib)

    # Step 3: renumber ItemIDs and propagate refs
    def test_step3_renumbering_preserves_chain_links(self):
        # Build a fake doc with a 3-frame chain and verify renumber updates
        # NEXTITEM/BACKITEM in lockstep.
        doc = etree.Element("DOCUMENT")
        root = etree.Element("SCRIBUSUTF8NEW")
        root.append(doc)
        tree = etree.ElementTree(root)
        for i, (back, nxt) in enumerate(((-1, 200), (100, 300), (200, -1))):
            po = etree.SubElement(doc, "PAGEOBJECT")
            po.set("ItemID", str(100 + i * 100))
            po.set("BACKITEM", str(back))
            po.set("NEXTITEM", str(nxt))
        sd.renumber_item_ids(tree, start=999_000)
        ids = [int(e.attrib["ItemID"]) for e in doc.findall("PAGEOBJECT")]
        self.assertEqual(ids, [999_000, 999_001, 999_002])
        # Chain links updated
        nexts = [e.attrib["NEXTITEM"] for e in doc.findall("PAGEOBJECT")]
        backs = [e.attrib["BACKITEM"] for e in doc.findall("PAGEOBJECT")]
        self.assertEqual(nexts, ["999001", "999002", "-1"])
        self.assertEqual(backs, ["-1", "999000", "999001"])

    # Step 4: drop FRAMEOBJECTs
    def test_step4_drop_frameobjects(self):
        tree = sd.parse_sla(self.src)
        doc = tree.getroot().find("DOCUMENT")
        before = len(doc.findall("FRAMEOBJECT"))
        self.assertGreater(before, 0)  # Postkarte has 3
        n = sd.drop_frameobjects(tree)
        self.assertEqual(n, before)
        self.assertEqual(len(doc.findall("FRAMEOBJECT")), 0)

    # Step 5: sort PAGEOBJECTs
    def test_step5_sort_pageobjects_by_owner_and_position(self):
        tree = sd.parse_sla(self.src)
        sd.drop_frameobjects(tree)
        sd.sort_pageobjects(tree)
        doc = tree.getroot().find("DOCUMENT")
        keys = [
            (int(e.attrib.get("OwnPage", "0")),
             round(float(e.attrib.get("YPOS", "0")), 6),
             round(float(e.attrib.get("XPOS", "0")), 6))
            for e in doc.findall("PAGEOBJECT")
        ]
        self.assertEqual(keys, sorted(keys))

    # Step 6: round float-shaped attrs to 6 decimals
    def test_step6_path_coords_rounded(self):
        tree = sd.parse_sla(self.src)
        doc = tree.getroot().find("DOCUMENT")
        first = doc.find("PAGEOBJECT")
        # Mutate path with extra precision
        first.set("path", "M0.1234567 0.7654321 L100.123456789 0 Z")
        sd.round_floats(tree)
        self.assertEqual(first.attrib["path"], "M0.123457 0.765432 L100.123457 0 Z")

    def test_step6_simple_floats_rounded(self):
        tree = sd.parse_sla(self.src)
        doc = tree.getroot().find("DOCUMENT")
        first = doc.find("PAGEOBJECT")
        first.set("XPOS", "100.123456789")
        sd.round_floats(tree)
        self.assertEqual(first.attrib["XPOS"], "100.123457")

    # Step 7: serialise sorts attribute order
    def test_step7_serialise_sorts_attributes_alphabetically(self):
        tree = sd.parse_sla(self.src)
        doc = tree.getroot().find("DOCUMENT")
        first = doc.find("PAGEOBJECT")
        # Re-set in a wonky order (the underlying lxml dict re-orders insertion)
        attrs = dict(first.attrib)
        for k in list(first.attrib.keys()):
            del first.attrib[k]
        for k in sorted(attrs.keys(), reverse=True):
            first.set(k, attrs[k])
        out = sd.serialise_normalised(tree)
        # find the pageobject substring; verify XPOS appears before YPOS
        text = out.decode("utf-8")
        po_start = text.find("<PAGEOBJECT")
        po_end = text.find(">", po_start)
        slice_ = text[po_start:po_end]
        if "XPOS" in slice_ and "YPOS" in slice_:
            self.assertLess(slice_.index("XPOS"), slice_.index("YPOS"))

    # Step 8: drop default-equivalent attrs
    def test_step8_default_equivalents_dropped(self):
        # Build a synthetic frame whose LOCALSCX/LOCALSCY/LOCALX/LOCALY/ROT
        # are all defaults; assert they're dropped after normalise.
        root = etree.Element("SCRIBUSUTF8NEW")
        doc = etree.SubElement(root, "DOCUMENT")
        po = etree.SubElement(doc, "PAGEOBJECT")
        po.set("ItemID", "1")
        po.set("LOCALSCX", "1")
        po.set("LOCALX", "0")
        po.set("ROT", "0")
        po.set("NEXTITEM", "-1")
        po.set("LINESPMode", "2")
        po.set("XPOS", "10")
        po.set("YPOS", "20")
        tree = etree.ElementTree(root)
        sd.drop_default_equivalents(tree)
        for k in ("LOCALSCX", "LOCALX", "ROT", "NEXTITEM", "LINESPMode"):
            self.assertNotIn(k, po.attrib)
        self.assertIn("XPOS", po.attrib)

    # Step 9: rebase + strip PAGEXPOS / PAGEYPOS
    def test_step9_pagexpos_dropped_and_items_rebased(self):
        tree = sd.parse_sla(self.src)
        sd.drop_frameobjects(tree)
        sd.renumber_item_ids(tree)
        # Pick a frame whose XPOS we can verify post-normalise.
        doc = tree.getroot().find("DOCUMENT")
        page0 = doc.find("PAGE")
        page0_xpos = float(page0.attrib["PAGEXPOS"])
        page0_ypos = float(page0.attrib["PAGEYPOS"])
        items_in_page_0 = [e for e in doc.findall("PAGEOBJECT") if e.attrib.get("OwnPage") == "0"]
        self.assertGreater(len(items_in_page_0), 0)
        before_x = [float(e.attrib["XPOS"]) for e in items_in_page_0]
        sd.rebase_item_coords_to_page_local(tree)
        # PAGE no longer has PAGEXPOS/PAGEYPOS
        self.assertNotIn("PAGEXPOS", page0.attrib)
        self.assertNotIn("PAGEYPOS", page0.attrib)
        # items rebased
        for el, was in zip(items_in_page_0, before_x):
            self.assertAlmostEqual(float(el.attrib["XPOS"]), was - page0_xpos, places=2)

    # Step 10: sort palettes
    def test_step10_sort_palettes_by_name(self):
        tree = sd.parse_sla(self.src)
        sd.sort_palette_lists(tree)
        doc = tree.getroot().find("DOCUMENT")
        names = [c.attrib.get("NAME", "") for c in doc.findall("COLOR")]
        self.assertEqual(names, sorted(names))
        snames = [s.attrib.get("NAME", "") for s in doc.findall("STYLE")]
        self.assertEqual(snames, sorted(snames))

    # Determinism check: same input → same normalised output bytes.
    def test_normalise_is_deterministic(self):
        a = sd.parse_sla(self.src)
        b = sd.parse_sla(self.src)
        sd.normalise(a)
        sd.normalise(b)
        self.assertEqual(sd.serialise_normalised(a), sd.serialise_normalised(b))


# ---------------------------------------------------------------------------
# Comparator tests
# ---------------------------------------------------------------------------
class SelfDiffTests(unittest.TestCase):
    """RESEARCH.md sanity check: each original diffed against itself reports
    zero critical and zero warning.
    """

    def test_self_diff_clean_for_each_original(self):
        for p in ORIGINALS:
            with self.subTest(p.name):
                report = sd.diff(p, p)
                summary = report.summary
                self.assertEqual(summary[sd.SEVERITY_CRITICAL], 0,
                                 f"Self-diff on {p.name} produced critical: {[i.short() for i in report.issues if i.severity == sd.SEVERITY_CRITICAL]}")
                self.assertEqual(summary[sd.SEVERITY_WARNING], 0,
                                 f"Self-diff on {p.name} produced warning: {[i.short() for i in report.issues if i.severity == sd.SEVERITY_WARNING]}")


def _write_synthetic_sla(target: Path, page_count: int = 1,
                          items: list[tuple[str, dict]] | None = None) -> Path:
    """Build a tiny synthetic SLA suitable for diff comparisons. Returns target."""
    items = items or []
    root = etree.Element("SCRIBUSUTF8NEW", attrib={"Version": "1.6.5"})
    doc = etree.SubElement(root, "DOCUMENT")
    doc.set("ANZPAGES", str(page_count))
    doc.set("PAGEWIDTH", "297.638")
    doc.set("PAGEHEIGHT", "419.528")
    doc.set("BleedTop", "8.504")
    doc.set("BleedBottom", "8.504")
    doc.set("BleedLeft", "8.504")
    doc.set("BleedRight", "8.504")
    for n in range(page_count):
        page = etree.SubElement(doc, "PAGE")
        page.set("NUM", str(n))
        page.set("PAGEXPOS", "100")
        page.set("PAGEYPOS", "20")
        page.set("MNAM", "Normal")
    master = etree.SubElement(doc, "MASTERPAGE")
    master.set("NAM", "Normal")
    master.set("PAGEXPOS", "500")
    master.set("PAGEYPOS", "20")
    for itag, iattrs in items:
        el = etree.SubElement(doc, itag)
        for k, v in iattrs.items():
            el.set(k, v)
    tree = etree.ElementTree(root)
    tree.write(str(target), encoding="UTF-8", xml_declaration=True)
    return target


class SyntheticDiffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _po(self, item_id: str, ptype: str = "4", own_page: str = "0",
            xpos: str = "150", ypos: str = "100",
            width: str = "100", height: str = "50",
            frtype: str = "0", **extra) -> tuple[str, dict]:
        attrs = {
            "ItemID": item_id, "PTYPE": ptype, "OwnPage": own_page,
            "XPOS": xpos, "YPOS": ypos,
            "WIDTH": width, "HEIGHT": height,
            "FRTYPE": frtype,
        }
        attrs.update(extra)
        return ("PAGEOBJECT", attrs)

    def test_synthetic_position_drift_warning(self):
        # ±0.6 pt YPOS shift → warning
        a = _write_synthetic_sla(self.tmp / "a.sla", items=[self._po("100")])
        b = _write_synthetic_sla(self.tmp / "b.sla", items=[self._po("100", ypos="100.6")])
        report = sd.diff(a, b)
        codes = [i.code for i in report.issues]
        self.assertIn("position-drift", codes)
        self.assertEqual(report.summary[sd.SEVERITY_CRITICAL], 0)

    def test_synthetic_minor_position_drift_info(self):
        # ±0.4 pt YPOS shift → info only
        a = _write_synthetic_sla(self.tmp / "a.sla", items=[self._po("100")])
        b = _write_synthetic_sla(self.tmp / "b.sla", items=[self._po("100", ypos="100.4")])
        report = sd.diff(a, b)
        codes = [i.code for i in report.issues]
        self.assertNotIn("position-drift", codes)
        self.assertEqual(report.summary[sd.SEVERITY_WARNING], 0)
        self.assertIn("position-minor-drift", codes)

    def test_synthetic_page_count_mismatch_critical(self):
        a = _write_synthetic_sla(self.tmp / "a.sla", page_count=1)
        b = _write_synthetic_sla(self.tmp / "b.sla", page_count=2)
        report = sd.diff(a, b)
        codes = [i.code for i in report.issues]
        self.assertIn("page-count-mismatch", codes)
        self.assertGreater(report.summary[sd.SEVERITY_CRITICAL], 0)

    def test_rectangle_equivalence_FRTYPE_0_vs_3(self):
        # Same rectangle, one as FRTYPE=0 (computed path) and one as FRTYPE=3
        # (explicit path) → info, not warning.
        rect_path_ccw = "M0 0 L0 50 L100 50 L100 0 L0 0 Z"
        a = _write_synthetic_sla(self.tmp / "a.sla", items=[
            self._po("100", frtype="0", path="M0 0 L100 0 L100 50 L0 50 L0 0 Z",
                     copath="M0 0 L100 0 L100 50 L0 50 L0 0 Z"),
        ])
        b = _write_synthetic_sla(self.tmp / "b.sla", items=[
            self._po("100", frtype="3", path=rect_path_ccw, copath=rect_path_ccw),
        ])
        report = sd.diff(a, b)
        codes = [i.code for i in report.issues]
        self.assertNotIn("frtype-mismatch", codes)
        self.assertIn("frtype-rectangle-equivalent", codes)
        self.assertEqual(report.summary[sd.SEVERITY_CRITICAL], 0)

    def test_chain_topology_break_critical(self):
        # Build A→B→C on left, A→B (broken) on right.
        a = _write_synthetic_sla(self.tmp / "a.sla", items=[
            self._po("100", ypos="100", BACKITEM="-1", NEXTITEM="200"),
            self._po("200", ypos="200", BACKITEM="100", NEXTITEM="300"),
            self._po("300", ypos="300", BACKITEM="200", NEXTITEM="-1"),
        ])
        b = _write_synthetic_sla(self.tmp / "b.sla", items=[
            self._po("100", ypos="100", BACKITEM="-1", NEXTITEM="200"),
            self._po("200", ypos="200", BACKITEM="100", NEXTITEM="-1"),
            self._po("300", ypos="300", BACKITEM="-1", NEXTITEM="-1"),
        ])
        report = sd.diff(a, b)
        codes = [i.code for i in report.issues]
        # chain-count-mismatch (1 chain on left, 1 on right but lengths differ → length mismatch)
        # Either chain-count-mismatch or chain-key-mismatch is acceptable.
        self.assertTrue(
            "chain-count-mismatch" in codes or "chain-key-mismatch" in codes,
            f"Expected chain mismatch in {codes}",
        )
        self.assertGreater(report.summary[sd.SEVERITY_CRITICAL], 0)

    def test_inline_image_pfile_equivalence(self):
        # Build a 1x1 PNG, qCompress it, base64; one side uses inline, other PFILE.
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15\xc4\x89"
            b"\x00\x00\x00\rIDATx\x9cb\x00\x00\x00\x00\x05\x00\x01\x0d\n-\xb4"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        compressed = zlib.compress(png_bytes, 9)
        qcompressed = len(png_bytes).to_bytes(4, "big") + compressed
        b64 = b64encode(qcompressed).decode("ascii")
        a = _write_synthetic_sla(self.tmp / "a.sla", items=[
            self._po("100", ptype="2", isInlineImage="1", inlineImageExt="png",
                     ImageData=b64, PFILE=""),
        ])
        b = _write_synthetic_sla(self.tmp / "b.sla", items=[
            self._po("100", ptype="2", PFILE="assets/inline-1.png"),
        ])
        report = sd.diff(a, b)
        codes = [i.code for i in report.issues]
        self.assertIn("inline-vs-sidecar-image", codes)


class StoryTextParagraphDiffTests(unittest.TestCase):
    """sla_diff must catch missing per-<para>/<trail> attribute overrides
    (the ALIGN / LINESP / LINESPMode round-trip drops that PR #3 introduced).

    A missing override is critical (a meaningful round-trip drop).
    A different value is a warning (visible drift, recoverable).
    A different paragraph count is critical (text structure differs).
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _frame_with_story(self, story_xml: str) -> tuple[str, dict]:
        """Helper: build a PAGEOBJECT[PTYPE=4] item containing a StoryText.
        The StoryText XML is stored on a magic ``__inner_xml__`` key the test
        helper ``_write_synthetic_sla_with_inner`` honours."""
        return ("PAGEOBJECT", {
            "ItemID": "100", "PTYPE": "4", "OwnPage": "0",
            "XPOS": "150", "YPOS": "100", "WIDTH": "100", "HEIGHT": "50",
            "FRTYPE": "0",
            "__inner_xml__": story_xml,
        })

    def _write(self, name: str, story_xml: str) -> Path:
        """Build a 1-page synthetic SLA with one TextFrame whose StoryText is
        the given XML string. Returns the path."""
        from lxml import etree as _et
        target = self.tmp / name
        root = _et.Element("SCRIBUSUTF8NEW", attrib={"Version": "1.6.5"})
        doc = _et.SubElement(root, "DOCUMENT")
        doc.set("ANZPAGES", "1")
        doc.set("PAGEWIDTH", "297.638")
        doc.set("PAGEHEIGHT", "419.528")
        for k in ("BleedTop", "BleedBottom", "BleedLeft", "BleedRight"):
            doc.set(k, "8.504")
        page = _et.SubElement(doc, "PAGE")
        page.set("NUM", "0"); page.set("PAGEXPOS", "100")
        page.set("PAGEYPOS", "20"); page.set("MNAM", "Normal")
        m = _et.SubElement(doc, "MASTERPAGE"); m.set("NAM", "Normal")
        m.set("PAGEXPOS", "500"); m.set("PAGEYPOS", "20")
        po = _et.SubElement(doc, "PAGEOBJECT")
        po.set("ItemID", "100"); po.set("PTYPE", "4"); po.set("OwnPage", "0")
        po.set("XPOS", "150"); po.set("YPOS", "100")
        po.set("WIDTH", "100"); po.set("HEIGHT", "50"); po.set("FRTYPE", "0")
        story = _et.fromstring(story_xml)
        po.append(story)
        _et.ElementTree(root).write(str(target), encoding="UTF-8", xml_declaration=True)
        return target

    def test_missing_align_override_is_critical(self):
        """The exact bug PR #3 had: original carries <para ALIGN="0"/>, the
        rebuilt SLA dropped it. Diff must flag this critically."""
        a = self._write("a.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<para PARENT="Headline" ALIGN="0"/>'
                                 '<ITEXT CH="y"/>'
                                 '<trail PARENT="Body"/>'
                                 '</StoryText>')
        b = self._write("b.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<para PARENT="Headline"/>'
                                 '<ITEXT CH="y"/>'
                                 '<trail PARENT="Body"/>'
                                 '</StoryText>')
        report = sd.diff(a, b)
        codes = [i.code for i in report.issues]
        self.assertIn("para-attr-missing", codes)
        self.assertGreater(report.summary[sd.SEVERITY_CRITICAL], 0)

    def test_missing_trail_align_override_is_critical(self):
        a = self._write("a.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<trail PARENT="Body" ALIGN="1"/>'
                                 '</StoryText>')
        b = self._write("b.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<trail PARENT="Body"/>'
                                 '</StoryText>')
        report = sd.diff(a, b)
        critical = [i for i in report.issues
                    if i.severity == sd.SEVERITY_CRITICAL and i.code == "para-attr-missing"]
        self.assertEqual(len(critical), 1)
        self.assertEqual(critical[0].attr, "ALIGN")

    def test_missing_linespmode_override_is_critical(self):
        a = self._write("a.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<para PARENT="P" LINESPMode="1"/>'
                                 '<trail PARENT="P"/>'
                                 '</StoryText>')
        b = self._write("b.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<para PARENT="P"/>'
                                 '<trail PARENT="P"/>'
                                 '</StoryText>')
        report = sd.diff(a, b)
        codes = [(i.code, i.attr) for i in report.issues]
        self.assertIn(("para-attr-missing", "LINESPMode"), codes)
        self.assertGreater(report.summary[sd.SEVERITY_CRITICAL], 0)

    def test_para_attr_value_mismatch_is_warning(self):
        """Different value (not just presence) is warning-level: visible
        drift but the round-trip didn't lose the override entirely."""
        a = self._write("a.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<para PARENT="P" ALIGN="0"/>'
                                 '<trail PARENT="P"/>'
                                 '</StoryText>')
        b = self._write("b.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<para PARENT="P" ALIGN="1"/>'
                                 '<trail PARENT="P"/>'
                                 '</StoryText>')
        report = sd.diff(a, b)
        codes = [i.code for i in report.issues]
        self.assertIn("para-attr-value-mismatch", codes)
        # No critical from this mismatch (count and presence both match).
        self.assertEqual(
            sum(1 for i in report.issues
                if i.severity == sd.SEVERITY_CRITICAL and i.code.startswith("para-")),
            0,
        )

    def test_para_count_mismatch_is_critical(self):
        """An extra <para> on one side (e.g. phantom trailing element) is a
        structural difference flagged as critical."""
        a = self._write("a.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<para PARENT="P"/>'
                                 '<ITEXT CH="y"/>'
                                 '<para PARENT="P"/>'
                                 '</StoryText>')
        b = self._write("b.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<para PARENT="P"/>'
                                 '<ITEXT CH="y"/>'
                                 '<para PARENT="P"/>'
                                 '<trail PARENT="P"/>'
                                 '</StoryText>')
        report = sd.diff(a, b)
        codes = [i.code for i in report.issues]
        self.assertIn("para-count-mismatch", codes)
        self.assertGreater(report.summary[sd.SEVERITY_CRITICAL], 0)

    def test_identical_storytext_clean(self):
        a = self._write("a.sla", '<StoryText><DefaultStyle/>'
                                 '<ITEXT CH="x"/>'
                                 '<para PARENT="Headline" ALIGN="0"/>'
                                 '<ITEXT CH="y"/>'
                                 '<trail PARENT="Body" ALIGN="1" LINESPMode="2"/>'
                                 '</StoryText>')
        report = sd.diff(a, a)
        para_issues = [i for i in report.issues if i.code.startswith("para-")]
        self.assertEqual(para_issues, [])


class CLIIntegrationTests(unittest.TestCase):
    """Mirror the gate's manual checks: run sla_diff CLI on each original
    against itself, expect exit 0 and clean summary."""

    def test_self_diff_cli_exit_0(self):
        for p in ORIGINALS:
            with self.subTest(p.name):
                rc = sd.main(["--left", str(p), "--right", str(p)])
                self.assertEqual(rc, 0)

    def test_self_diff_strict_exit_0(self):
        for p in ORIGINALS:
            with self.subTest(p.name):
                rc = sd.main(["--left", str(p), "--right", str(p), "--strict"])
                self.assertEqual(rc, 0)

    def test_self_diff_json_emits_summary(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = sd.main(["--left", str(ORIGINALS[0]), "--right", str(ORIGINALS[0]), "--json"])
        self.assertEqual(rc, 0)
        import json
        data = json.loads(buf.getvalue())
        self.assertEqual(data["summary"]["critical"], 0)
        self.assertEqual(data["summary"]["warning"], 0)


if __name__ == "__main__":
    unittest.main()
