"""Unit tests for tools/idml_attribute_coverage_audit.py.

The audit diffs attributes PRESENT in an IDML against attributes the converter
CONSUMES, then classifies each unconsumed attribute. Tests use synthetic
minimal IDML zips so they run fully offline and fast. The runtime
instrumentation hook is tested directly against the converter's parser without
running a full conversion.
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest
from lxml import etree

# Bootstrap tools/ onto sys.path so we can import the module directly.
TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import idml_attribute_coverage_audit as audit  # noqa: E402


# ---------------------------------------------------------------------------
# Synthetic IDML fixture
# ---------------------------------------------------------------------------

# A Spread part with a Rectangle (render anchor) carrying geometry, plus a
# Properties value-wrapper with a `type` serialization annotation.
_SPREAD_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<idPkg:Spread xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging">
  <Spread Self="spr1" PageCount="1" BindingLocation="0">
    <Page Self="pg1" Name="1" AppliedMaster="m1"/>
    <Rectangle Self="r1" ItemTransform="1 0 0 1 0 0" StrokeWeight="2"
               FillColor="Color/Black" ContentType="GraphicType">
      <Properties>
        <Leading type="enumeration">Auto</Leading>
      </Properties>
    </Rectangle>
  </Spread>
</idPkg:Spread>
"""

# A Styles part: a ParagraphStyle with the known dropped SpaceBefore/SpaceAfter.
_STYLES_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<idPkg:Styles xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging">
  <RootParagraphStyleGroup Self="rpsg">
    <ParagraphStyle Self="ps1" Name="Body" PointSize="11"
                    SpaceBefore="0" SpaceAfter="4.5" Justification="LeftAlign"/>
  </RootParagraphStyleGroup>
</idPkg:Styles>
"""

# A Preferences part: editing-environment defaults, NOT inside a render anchor.
_PREFS_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<idPkg:Preferences xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging">
  <Preferences>
    <TextDefault PointSize="12" AppliedFont="Minion Pro"/>
    <AdjustLayoutPreference EnableAdjustLayout="false"/>
  </Preferences>
</idPkg:Preferences>
"""

# An XMP metadata part.
_METADATA_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about="" custom="anything"/>
  </rdf:RDF>
</x:xmpmeta>
"""


def _make_idml(tmp_path: Path, name: str = "synthetic.idml") -> Path:
    """Build a minimal synthetic IDML zip with the fixture parts."""
    path = tmp_path / name
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/vnd.adobe.indesign-idml-package")
        zf.writestr("Spreads/Spread_spr1.xml", _SPREAD_XML)
        zf.writestr("Resources/Styles.xml", _STYLES_XML)
        zf.writestr("Resources/Preferences.xml", _PREFS_XML)
        zf.writestr("META-INF/metadata.xml", _METADATA_XML)
    path.write_bytes(buf.getvalue())
    return path


# ---------------------------------------------------------------------------
# harvest_idml
# ---------------------------------------------------------------------------

def test_harvest_enumerates_every_tag_and_attr(tmp_path: Path) -> None:
    idml = _make_idml(tmp_path)
    present = audit.harvest_idml(idml)

    # Every (tag, attr) pair in the fixture must be present.
    assert ("Rectangle", "StrokeWeight") in present
    assert ("Rectangle", "ItemTransform") in present
    assert ("ParagraphStyle", "SpaceBefore") in present
    assert ("ParagraphStyle", "SpaceAfter") in present
    assert ("Spread", "PageCount") in present
    assert ("Leading", "type") in present
    assert ("TextDefault", "PointSize") in present
    assert ("Description", "custom") in present


def test_harvest_records_observed_values(tmp_path: Path) -> None:
    present = audit.harvest_idml(_make_idml(tmp_path))
    assert present[("ParagraphStyle", "SpaceAfter")].values == {"4.5"}
    assert present[("ParagraphStyle", "SpaceBefore")].values == {"0"}


def test_harvest_marks_render_scope_correctly(tmp_path: Path) -> None:
    present = audit.harvest_idml(_make_idml(tmp_path))
    # Inside a Rectangle / ParagraphStyle render anchor -> render scope.
    assert present[("Rectangle", "StrokeWeight")].render_scope is True
    assert present[("ParagraphStyle", "SpaceAfter")].render_scope is True
    assert present[("Leading", "type")].render_scope is True  # under Rectangle
    # Editing-environment / metadata -> NOT render scope.
    assert present[("TextDefault", "PointSize")].render_scope is False
    assert present[("AdjustLayoutPreference", "EnableAdjustLayout")].render_scope is False
    assert present[("Description", "custom")].render_scope is False


def test_part_category() -> None:
    assert audit._part_category("Spreads/Spread_a.xml") == "spread"
    assert audit._part_category("Stories/Story_a.xml") == "story"
    assert audit._part_category("Resources/Styles.xml") == "styles"
    assert audit._part_category("Resources/Preferences.xml") == "preferences"
    assert audit._part_category("META-INF/metadata.xml") == "metadata"
    assert audit._part_category("designmap.xml") == "designmap"


def test_merge_present_unions_scope_and_values(tmp_path: Path) -> None:
    a = audit.harvest_idml(_make_idml(tmp_path, "a.idml"))
    # A second IDML with a different SpaceAfter value.
    b = {
        ("ParagraphStyle", "SpaceAfter"): audit.PresentEntry(
            values={"9.0"}, idmls={"b.idml"}, parts={"styles"},
            render_scope=True,
        ),
    }
    merged = audit.merge_present([a, b])
    assert merged[("ParagraphStyle", "SpaceAfter")].values == {"4.5", "9.0"}
    assert merged[("ParagraphStyle", "SpaceAfter")].idmls == {
        "a.idml", "b.idml"
    }


# ---------------------------------------------------------------------------
# classify_attribute
# ---------------------------------------------------------------------------

def _classify(tag: str, attr: str, values, render_scope, visited=False):
    return audit.classify_attribute(
        tag, attr, set(values), {"styles"}, render_scope, visited
    )


def test_space_before_after_classified_significant() -> None:
    """The known regression: ParagraphStyle SpaceBefore/SpaceAfter dropped."""
    for attr in ("SpaceBefore", "SpaceAfter"):
        c = _classify("ParagraphStyle", attr, {"0", "4.5"}, render_scope=True)
        assert c.verdict == "significant", attr


def test_internal_id_attrs_ignorable() -> None:
    for attr in ("Self", "Name", "StyleUniqueId", "DOMVersion"):
        c = _classify("ParagraphStyle", attr, {"x"}, render_scope=True)
        assert c.verdict == "ignorable", attr


def test_type_serialization_annotation_ignorable() -> None:
    c = _classify("Leading", "type", {"enumeration"}, render_scope=True)
    assert c.verdict == "ignorable"


def test_metadata_element_ignorable() -> None:
    c = _classify("Description", "custom", {"x"}, render_scope=False)
    assert c.verdict == "ignorable"


def test_out_of_render_scope_ignorable() -> None:
    """Editing-environment defaults never reach the printed PDF."""
    c = _classify(
        "AdjustLayoutPreference", "EnableAdjustLayout", {"false"},
        render_scope=False,
    )
    assert c.verdict == "ignorable"


def test_keyword_match_significant_in_render_scope() -> None:
    for tag, attr in [
        ("Rectangle", "StrokeWeight"),
        ("Rectangle", "FillColor"),
        ("Rectangle", "ItemTransform"),
        ("TextFramePreference", "VerticalJustification"),
    ]:
        c = _classify(tag, attr, {"a", "b"}, render_scope=True)
        assert c.verdict == "significant", (tag, attr)


def test_visited_tag_unconsumed_attr_significant() -> None:
    """Unconsumed attr on a converter-handled element -> significant."""
    c = _classify(
        "MarginPreference", "Top", {"0", "34"}, render_scope=True,
        visited=True,
    )
    assert c.verdict == "significant"
    assert "converter-handled" in c.reason


def test_render_scope_unknown_attr_conservative_significant() -> None:
    """No keyword, not visited, but in render scope -> conservative."""
    c = _classify(
        "Ink", "Frequency", {"70", "70.7"}, render_scope=True, visited=False
    )
    assert c.verdict == "significant"


def test_varies_flag() -> None:
    constant = audit.Classified(
        "ParagraphStyle", "SpaceBefore", "significant", "r", ["0"], [], []
    )
    varying = audit.Classified(
        "ParagraphStyle", "SpaceAfter", "significant", "r", ["0", "4.5"], [],
        [],
    )
    assert constant.varies is False
    assert varying.varies is True


# ---------------------------------------------------------------------------
# Runtime instrumentation hook
# ---------------------------------------------------------------------------

def test_tracking_element_records_get_calls() -> None:
    """The instrumented element class records every .get() attribute key."""
    audit._CONSUMED.clear()
    parser = etree.XMLParser()
    parser.set_element_class_lookup(
        etree.ElementDefaultClassLookup(element=audit._TrackingElement)
    )
    root = etree.fromstring(
        b'<Rectangle Self="r1" StrokeWeight="2" FillColor="Black"/>',
        parser=parser,
    )
    root.get("StrokeWeight")
    root.get("Self")
    # Unread attribute (FillColor) must NOT be recorded.
    assert ("Rectangle", "StrokeWeight") in audit._CONSUMED
    assert ("Rectangle", "Self") in audit._CONSUMED
    assert ("Rectangle", "FillColor") not in audit._CONSUMED


def test_tracking_element_handles_namespaced_keys() -> None:
    audit._CONSUMED.clear()
    parser = etree.XMLParser()
    parser.set_element_class_lookup(
        etree.ElementDefaultClassLookup(element=audit._TrackingElement)
    )
    root = etree.fromstring(
        b'<idPkg:Spread xmlns:idPkg="http://ns.adobe.com/x" Self="s"/>',
        parser=parser,
    )
    root.get("Self")
    assert ("Spread", "Self") in audit._CONSUMED


# ---------------------------------------------------------------------------
# audit() end-to-end on the synthetic IDML
# ---------------------------------------------------------------------------

def test_audit_diff_excludes_consumed(monkeypatch, tmp_path: Path) -> None:
    """A consumed (tag, attr) must not appear in the classified diff."""
    idml = _make_idml(tmp_path)

    # Stub the converter run: pretend it consumed ParagraphStyle/PointSize.
    def fake_run(path: Path) -> audit.ConverterRun:
        return audit.ConverterRun(
            consumed={("ParagraphStyle", "PointSize"),
                      ("ParagraphStyle", "Self")},
            ok=True,
            note="",
        )

    monkeypatch.setattr(audit, "run_converter_instrumented", fake_run)
    result = audit.audit([idml])

    classified_keys = {(c.tag, c.attr) for c in result.classified}
    # Consumed pairs are excluded from the diff.
    assert ("ParagraphStyle", "PointSize") not in classified_keys
    # Unconsumed render-relevant attrs remain and are significant.
    sig_keys = {(c.tag, c.attr) for c in result.significant}
    assert ("ParagraphStyle", "SpaceBefore") in sig_keys
    assert ("ParagraphStyle", "SpaceAfter") in sig_keys


def test_audit_render_markdown_contains_sanity_check(
    monkeypatch, tmp_path: Path
) -> None:
    idml = _make_idml(tmp_path)
    monkeypatch.setattr(
        audit,
        "run_converter_instrumented",
        lambda p: audit.ConverterRun(consumed=set(), ok=True, note=""),
    )
    result = audit.audit([idml])
    report = audit.render_markdown(result, [idml])
    assert "# IDML Attribute Coverage Audit" in report
    assert "## Sanity check" in report
    assert "Tier A -- varying value" in report
    assert "Tier B -- constant value" in report
    # The sanity check lines must report OK for the known regression.
    assert "ParagraphStyle/SpaceBefore`: present=True" in report
    assert "ParagraphStyle/SpaceAfter`: present=True" in report


def test_audit_records_failed_converter_runs(
    monkeypatch, tmp_path: Path
) -> None:
    idml = _make_idml(tmp_path)
    monkeypatch.setattr(
        audit,
        "run_converter_instrumented",
        lambda p: audit.ConverterRun(
            consumed=set(), ok=False, note="UnhandledElement: boom"
        ),
    )
    result = audit.audit([idml])
    assert result.runs[idml.name].ok is False
    report = audit.render_markdown(result, [idml])
    assert "failed conversion" in report
    assert "UnhandledElement: boom" in report


# ---------------------------------------------------------------------------
# Scaffold/import gate -- baseline + run_attribute_coverage_gate
# ---------------------------------------------------------------------------

def test_baseline_roundtrip(monkeypatch, tmp_path: Path) -> None:
    """build_baseline_doc -> write -> load_baseline returns the same sets."""
    idml = _make_idml(tmp_path)
    monkeypatch.setattr(
        audit,
        "run_converter_instrumented",
        lambda p: audit.ConverterRun(
            consumed={("ParagraphStyle", "PointSize")}, ok=True, note=""
        ),
    )
    result = audit.audit([idml])
    doc = audit.build_baseline_doc(result)
    assert doc["_schema_version"] == 2
    assert "accepted" in doc and "batch_consumed" in doc
    # SpaceBefore/SpaceAfter are significant unconsumed -> in accepted.
    assert "ParagraphStyle/SpaceBefore" in doc["accepted"]
    assert "ParagraphStyle/SpaceAfter" in doc["accepted"]
    # PointSize was consumed -> in batch_consumed.
    assert "ParagraphStyle/PointSize" in doc["batch_consumed"]

    baseline_path = tmp_path / "baseline.yml"
    baseline_path.write_text(
        __import__("yaml").safe_dump(doc), encoding="utf-8"
    )
    accepted, batch_consumed = audit.load_baseline(baseline_path)
    assert accepted == set(doc["accepted"])
    assert batch_consumed == set(doc["batch_consumed"])


def test_load_baseline_missing_returns_empty_sets(tmp_path: Path) -> None:
    accepted, batch_consumed = audit.load_baseline(tmp_path / "absent.yml")
    assert accepted == set()
    assert batch_consumed == set()


def _write_baseline(tmp_path: Path, accepted, batch_consumed=()) -> Path:
    import yaml as _yaml
    p = tmp_path / "baseline.yml"
    p.write_text(
        _yaml.safe_dump({
            "accepted": sorted(accepted),
            "batch_consumed": sorted(batch_consumed),
        }),
        encoding="utf-8",
    )
    return p


def test_gate_passes_when_all_significant_in_baseline(
    monkeypatch, tmp_path: Path
) -> None:
    """Every significant unconsumed attribute is dispositioned -> gate OK."""
    idml = _make_idml(tmp_path)
    monkeypatch.setattr(
        audit,
        "run_converter_instrumented",
        lambda p: audit.ConverterRun(consumed=set(), ok=True, note=""),
    )
    # Build the baseline FROM this IDML's own significant set.
    result = audit.audit([idml])
    baseline = _write_baseline(
        tmp_path,
        {audit._baseline_key(c.tag, c.attr) for c in result.significant},
    )
    gate = audit.run_attribute_coverage_gate(idml, baseline)
    assert gate.ok is True
    assert gate.issues == 0
    assert gate.new_attributes == []


def test_gate_flags_new_significant_attribute(
    monkeypatch, tmp_path: Path
) -> None:
    """A significant attribute NOT in the baseline fails the gate."""
    idml = _make_idml(tmp_path)
    monkeypatch.setattr(
        audit,
        "run_converter_instrumented",
        lambda p: audit.ConverterRun(consumed=set(), ok=True, note=""),
    )
    result = audit.audit([idml])
    sig_keys = {audit._baseline_key(c.tag, c.attr) for c in result.significant}
    # Baseline is missing exactly one known significant attribute.
    assert "ParagraphStyle/SpaceAfter" in sig_keys
    baseline = _write_baseline(
        tmp_path, sig_keys - {"ParagraphStyle/SpaceAfter"}
    )
    gate = audit.run_attribute_coverage_gate(idml, baseline)
    assert gate.ok is False
    assert gate.issues == 1
    assert gate.new_attributes == ["ParagraphStyle/SpaceAfter"]
    assert "ParagraphStyle/SpaceAfter" in gate.detail


def test_gate_batch_consumed_absorbs_coverage_gap(
    monkeypatch, tmp_path: Path
) -> None:
    """An attr the converter handles batch-wide is not a new drop.

    A single-IDML gate run exercises fewer converter code paths than the
    9-IDML batch. An attribute consumed only via another IDML's path would
    show as unconsumed here; batch_consumed must absorb it.
    """
    idml = _make_idml(tmp_path)
    monkeypatch.setattr(
        audit,
        "run_converter_instrumented",
        lambda p: audit.ConverterRun(consumed=set(), ok=True, note=""),
    )
    result = audit.audit([idml])
    sig_keys = {audit._baseline_key(c.tag, c.attr) for c in result.significant}
    # Pretend SpaceAfter is NOT in `accepted` but IS in `batch_consumed`.
    baseline = _write_baseline(
        tmp_path,
        accepted=sig_keys - {"ParagraphStyle/SpaceAfter"},
        batch_consumed={"ParagraphStyle/SpaceAfter"},
    )
    gate = audit.run_attribute_coverage_gate(idml, baseline)
    assert gate.ok is True
    assert gate.issues == 0


def test_gate_fails_loud_on_missing_baseline(
    monkeypatch, tmp_path: Path
) -> None:
    """No baseline file -> gate fails (never silently passes)."""
    idml = _make_idml(tmp_path)
    monkeypatch.setattr(
        audit,
        "run_converter_instrumented",
        lambda p: audit.ConverterRun(consumed=set(), ok=True, note=""),
    )
    gate = audit.run_attribute_coverage_gate(idml, tmp_path / "absent.yml")
    assert gate.ok is False
    assert "missing/empty" in gate.detail


def test_gate_report_has_preflight_contract(
    monkeypatch, tmp_path: Path
) -> None:
    """to_report() carries the canonical ok/issues/detail keys."""
    idml = _make_idml(tmp_path)
    monkeypatch.setattr(
        audit,
        "run_converter_instrumented",
        lambda p: audit.ConverterRun(consumed=set(), ok=True, note=""),
    )
    result = audit.audit([idml])
    baseline = _write_baseline(
        tmp_path,
        {audit._baseline_key(c.tag, c.attr) for c in result.significant},
    )
    report = audit.run_attribute_coverage_gate(idml, baseline).to_report()
    for key in ("ok", "issues", "detail"):
        assert key in report
    assert isinstance(report["ok"], bool)
    assert isinstance(report["issues"], int)
    assert isinstance(report["detail"], str)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
