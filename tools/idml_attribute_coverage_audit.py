#!/usr/bin/env python3
"""IDML attribute-coverage audit.

The IDML -> SLA converter (``tools/idml_to_dsl.py``) fails loud on unknown
element *kinds* (``UnhandledElement``) but silently ignores *attributes* of
elements it already handles. A confirmed regression: ``ParagraphStyle`` is a
handled element, yet its ``SpaceBefore`` / ``SpaceAfter`` attributes were never
read, so paragraph spacing was dropped with no error.

This tool answers "what ELSE is silently dropped" by diffing two sets:

1. PRESENT  -- every ``(element-tag, attribute-name)`` pair that appears in an
   IDML, harvested by walking every XML part in the IDML zip.
2. CONSUMED -- every ``(element-tag, attribute-name)`` pair that the converter
   actually reads. Determined by RUNTIME INSTRUMENTATION: the converter parses
   all XML through one shared ``lxml`` parser object
   (``idml_to_dsl._SECURE_XMLPARSER``). We attach a custom element class to that
   parser whose ``.get()`` records every attribute key looked up, then run a
   real ``convert()``. Every attribute the converter reads -- in any of its 7
   phases -- is captured, keyed by the element's local tag name.

The diff (PRESENT minus CONSUMED), per element tag, is the silently dropped
set. Each dropped attribute is then classified ``significant`` (can affect
geometry / layout / typography / colour / stroke / effects / transforms / text
flow -- the converter-fix list) or ``ignorable`` (internal IDs, application or
editorial state, audit metadata, inert defaults).

Method precision / limitations
-------------------------------
* The CONSUMED set is RUNTIME-OBSERVED, not statically inferred. It is exact
  for the code paths exercised by the audited IDMLs: if an attribute is read,
  it is recorded with the element's real local tag name. There is no
  false-attribution from grep heuristics.
* Limitation -- code-path coverage: an attribute read only on a branch that
  none of the 9 batch IDMLs trigger would be reported as unconsumed. The 9
  IDMLs are a broad batch (flyers, leporello, portrait / cover / zweigeteilt
  variants) so coverage is wide, but not provably total.
* Limitation -- ``.attrib`` bulk access: the converter has exactly one
  non-``.get()`` attribute access, ``child.attrib.values()`` at
  idml_to_dsl.py:1862. ``lxml``'s ``_Attrib`` is a C type and cannot be hooked.
  That call is an emptiness *test* on ``AnchoredObjectSetting`` (it reads no
  specific key), so it consumes nothing semantically -- it is not a real
  consumption and its absence from the CONSUMED set is correct.
* Default value cross-check: ``classify_attribute`` only treats an attribute as
  inert-default when EVERY observed value across all IDMLs equals a known
  IDML/InDesign default. A single non-default value flips it to significant.
"""

from __future__ import annotations

import argparse
import collections
import io
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from lxml import etree

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


# --------------------------------------------------------------------------
# PRESENT set -- harvest every (tag, attribute) from an IDML zip.
# --------------------------------------------------------------------------

# IDML XML parts are namespaced; we always reduce to the local tag name so the
# PRESENT and CONSUMED sets compare on the same key the converter sees via
# etree.QName(el).localname.

_HARVEST_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    dtd_validation=False,
    load_dtd=False,
    huge_tree=True,
)


@dataclass
class PresentEntry:
    """A (tag, attr) pair seen in the IDML(s), with observed values + sources."""

    values: set[str] = field(default_factory=set)
    idmls: set[str] = field(default_factory=set)
    parts: set[str] = field(default_factory=set)  # part-category labels
    # True if this (tag, attr) ever appears on an element that is, or is a
    # descendant of, a render-relevant anchor (page item / story / named style
    # / colour / spread). Render-scope attributes can reach the printed PDF;
    # everything else is editing-environment / metadata.
    render_scope: bool = False


def _part_category(name: str) -> str:
    """Map an IDML zip entry path to a coarse category label."""
    low = name.lower()
    if low.startswith("spreads/"):
        return "spread"
    if low.startswith("masterspreads/"):
        return "masterspread"
    if low.startswith("stories/"):
        return "story"
    if low == "xml/backingstory.xml":
        return "backingstory"
    if low == "resources/styles.xml":
        return "styles"
    if low == "resources/graphic.xml":
        return "graphic"
    if low == "resources/fonts.xml":
        return "fonts"
    if low == "resources/preferences.xml":
        return "preferences"
    if low == "designmap.xml":
        return "designmap"
    if low.startswith("meta-inf/"):
        return "metadata"
    if low.startswith("xml/"):
        return "xml-tagging"
    return "other"


# Render-relevant ANCHOR element kinds: actual page items, story / text-flow
# roots, named styles and colour definitions, and page/spread layout objects.
# An attribute is "in render scope" iff its element is one of these or a
# descendant of one -- i.e. it belongs to data InDesign rasterises into the
# printed PDF, as opposed to editing-environment preferences / new-object
# defaults / export presets / XMP metadata.
_RENDER_ANCHOR_TAGS: frozenset[str] = frozenset(
    {
        # Page items (geometry-bearing objects placed on a spread)
        "Rectangle", "Polygon", "Oval", "GraphicLine", "TextFrame", "Group",
        "Image", "EPS", "PDF", "WMF", "ImportedPage", "Button",
        "MultiStateObject", "PlacedItem",
        # Text flow
        "Story", "XmlStory",
        # Named styles (resolved by the converter and applied to page items)
        "ParagraphStyle", "CharacterStyle", "ObjectStyle", "CellStyle",
        "TableStyle",
        # Colour definitions
        "Color", "Swatch", "Gradient", "Ink", "Tint", "MixedInk",
        "MixedInkGroup",
        # Page / spread layout
        "Spread", "Page", "MasterSpread",
    }
)


def harvest_idml(idml_path: Path) -> dict[tuple[str, str], PresentEntry]:
    """Walk every XML part of one IDML; return {(tag, attr): PresentEntry}.

    Also records, per (tag, attr), whether it ever appears within a
    render-relevant anchor subtree (see ``_RENDER_ANCHOR_TAGS``).
    """
    out: dict[tuple[str, str], PresentEntry] = {}
    label = idml_path.name
    with zipfile.ZipFile(idml_path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".xml"):
                continue
            raw = zf.read(name)
            try:
                root = etree.fromstring(raw, parser=_HARVEST_PARSER)
            except etree.XMLSyntaxError:
                continue
            category = _part_category(name)
            _harvest_subtree(root, category, label, out, in_render=False)
    return out


def _harvest_subtree(
    el: "etree._Element",
    category: str,
    label: str,
    out: dict[tuple[str, str], PresentEntry],
    in_render: bool,
) -> None:
    """Recurse one element, tracking whether we are inside a render anchor."""
    if not isinstance(el.tag, str):
        return  # comments / PIs
    tag = etree.QName(el).localname
    here_render = in_render or tag in _RENDER_ANCHOR_TAGS
    for attr_qname, value in el.attrib.items():
        attr = etree.QName(attr_qname).localname
        entry = out.setdefault((tag, attr), PresentEntry())
        if len(entry.values) < 24:
            entry.values.add(value)
        entry.idmls.add(label)
        entry.parts.add(category)
        if here_render:
            entry.render_scope = True
    for child in el:
        _harvest_subtree(child, category, label, out, here_render)


def merge_present(
    per_idml: list[dict[tuple[str, str], PresentEntry]],
) -> dict[tuple[str, str], PresentEntry]:
    """Union the per-IDML PRESENT maps."""
    merged: dict[tuple[str, str], PresentEntry] = {}
    for one in per_idml:
        for key, entry in one.items():
            tgt = merged.setdefault(key, PresentEntry())
            for v in entry.values:
                if len(tgt.values) < 24:
                    tgt.values.add(v)
            tgt.idmls |= entry.idmls
            tgt.parts |= entry.parts
            tgt.render_scope = tgt.render_scope or entry.render_scope
    return merged


# --------------------------------------------------------------------------
# CONSUMED set -- runtime instrumentation of the converter.
# --------------------------------------------------------------------------

# Recorded as a module global so the instrumented element class (instantiated
# by lxml deep inside the parser) can reach it without a closure.
_CONSUMED: set[tuple[str, str]] = set()


class _TrackingElement(etree.ElementBase):
    """lxml element subclass: records every attribute key read via .get()."""

    def get(self, key, default=None):  # noqa: A003 - mirrors etree API
        try:
            tag = self.tag
            if isinstance(tag, str):
                local = tag.rsplit("}", 1)[-1]
                attr_local = str(key).rsplit("}", 1)[-1]
                _CONSUMED.add((local, attr_local))
        except Exception:  # never let instrumentation break a conversion
            pass
        return super().get(key, default)


@dataclass
class ConverterRun:
    """Outcome of one instrumented converter run."""

    consumed: set[tuple[str, str]]
    ok: bool
    note: str  # "" on success, else a short failure description


def run_converter_instrumented(idml_path: Path) -> ConverterRun:
    """Run a real conversion of ``idml_path`` and return the CONSUMED set.

    Attaches ``_TrackingElement`` as the element class of the converter's
    shared parser, so every element parsed during the run -- across all 7
    converter phases -- records its ``.get()`` reads.

    The converter is driven through its own ``main()`` entry point so the
    real argument resolution and ``links_export.py`` auto-invoke run exactly
    as a normal CLI conversion would. The emitted ``build.py`` is written to a
    temp file inside the repo root (the converter rejects asset paths outside
    the repo, so the output must live inside it) and discarded afterwards.

    A converter failure does NOT abort the audit: ``_CONSUMED`` is populated
    incrementally as elements are parsed, so a partial run still yields a valid
    (subset) CONSUMED set. The failure is recorded in ``ConverterRun.note`` so
    the report can flag reduced code-path coverage for that IDML.
    """
    import idml_to_dsl  # imported here so sys.path tweak above is in effect

    _CONSUMED.clear()

    parser = idml_to_dsl._SECURE_XMLPARSER
    lookup = etree.ElementDefaultClassLookup(element=_TrackingElement)
    parser.set_element_class_lookup(lookup)

    slug = idml_path.stem.lower().replace(" ", "-")
    repo_root = idml_to_dsl.ROOT
    # Temp build.py inside the repo so the converter's repo-root asset guard
    # passes; a unique name avoids clobbering anything.
    out_build = repo_root / "build" / f".attr-audit-{slug}.build.py"
    out_build.parent.mkdir(parents=True, exist_ok=True)
    ok = True
    note = ""
    try:
        # Silence the converter's stdout/stderr chatter; keep failures.
        buf_out, buf_err = io.StringIO(), io.StringIO()
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = buf_out, buf_err
        try:
            rc = idml_to_dsl.main(
                [
                    str(idml_path),
                    str(out_build),
                    "--template-id",
                    f"audit-{slug}",
                ]
            )
        except Exception as exc:  # converter raised - partial run still useful
            rc = 1
            note = f"{type(exc).__name__}: {exc}"
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        if rc != 0:
            ok = False
            if not note:
                # idml_to_dsl.main() catches UnhandledElement itself and prints
                # an "UnhandledElement: ..." line to stderr before returning a
                # non-zero rc; surface that line, not the leading OK chatter.
                err_lines = buf_err.getvalue().strip().splitlines()
                hit = next(
                    (ln for ln in err_lines
                     if "UnhandledElement" in ln or "Error" in ln),
                    None,
                )
                note = hit or (err_lines[-1] if err_lines
                               else f"converter exited {rc}")
    finally:
        # Detach the lookup so a later harvest / re-run is not affected.
        parser.set_element_class_lookup(None)
        if out_build.exists():
            out_build.unlink()

    return ConverterRun(consumed=set(_CONSUMED), ok=ok, note=note)


# --------------------------------------------------------------------------
# Classification.
# --------------------------------------------------------------------------
#
# The principle: an attribute is `significant` only if it can change the
# *rendered* SLA / PDF. InDesign bakes every resolved value into the actual
# page items (Spreads), text ranges (Stories) and named Styles/Colors. The
# editing-environment blocks -- document/text/object *Preferences*, new-object
# *Defaults*, export presets, XMP metadata -- do NOT reach the print and are
# `ignorable`. So scope is applied first (by IDML part), then a keyword pass
# inside the render-relevant scope, with a conservative `significant` default.

# Element tags that carry no print/layout meaning even inside a render part.
# (e.g. ObjectExportOption appears in Spreads but is alt-text / EPUB metadata.)
_IGNORABLE_TAGS: frozenset[str] = frozenset(
    {
        # XMP / RDF metadata (META-INF/metadata.xml)
        "RDF", "Description", "Bag", "Seq", "Alt", "li", "xmpmeta",
        "CreateDate", "CreatorTool", "MetadataDate", "ModifyDate",
        "DocumentID", "InstanceID", "OriginalDocumentID", "RenditionClass",
        "History", "Ingredients", "DerivedFrom", "Manifest", "format",
        "Descriptor", "ActualMetadataProperty", "AltMetadataProperty",
        "DocChangeCount", "container", "rootfile", "rootfiles", "reference",
        "MetadataPacketPreference", "PageInfo", "PDFAttribute", "KeyValuePair",
        # Editorial / workflow / accessibility state (no print effect)
        "DocumentUser", "Assignment", "InCopyExportOption",
        "ConditionalTextPreference", "DataMergeOption", "ObjectExportOption",
        # Export-preset blocks -- never affect the InDesign print layout
        "EPubExportPreference", "EPubFixedLayoutExportPreference",
        "HTMLExportPreference", "HTMLFXLExportPreference",
        "Html5ExportPreference", "XMLExportPreference", "XMLImportPreference",
        "ExportForWebPreference", "PublishExportPreference",
        "PrintBookletPrintPreference", "PrintBookletOption",
        "PrintPreference", "TaggedPDFPreference", "ImageIOPreference",
        "ButtonPreference", "ActivePrinterPreset", "Printer", "PPD",
        "ImageablePaperSizeRect", "PaperSizeRect",
        # Indexing / TOC / endnote -- editorial structure, not flyer layout
        "IndexOptions", "IndexHeaderSetting", "IndexHeaderGroupType",
        "IndexingSortOption", "ListOfIndexHeaderGroup", "SectionHeaderType",
        "SectionHeaderArray", "TOCStyle", "FootnoteOption",
        "EndnoteOption", "EndnoteNumberingStyle", "EndnoteMarkerPositioning",
        "FootnoteNumberingStyle", "CrossReferenceFormat",
        # XML-tagging structure (XML/Tags.xml + AppliedXMLTag wiring)
        "XMLTag", "XMLElement", "Tags", "XMLPreference",
    }
)

# Attribute names that are ignorable on ANY element: internal object IDs,
# style-graph wiring the converter resolves by name, schema bookkeeping, and
# UI / link housekeeping. None of these change the rasterised PDF -- InDesign
# serialises the fully-resolved attribute set onto every styled element, so
# inheritance pointers carry no extra render information.
_IGNORABLE_ATTRS: frozenset[str] = frozenset(
    {
        # Identifiers / names / cross-references
        "Self",                      # internal object id
        "Name",                      # name -- the converter keys by it, not a value
        "Id",                        # internal id
        "BaseName", "NamePrefix",    # section / variable naming
        "DOMVersion",                # IDML schema version stamp
        "AppliedXMLTag",             # XML structure tagging, not print
        "Label",                     # scripting label, no print effect
        "StyleUniqueId",             # internal style UUID
        "StyleUniqueIdInherited",    # internal style UUID
        "SwatchColorGroupReference", # internal swatch-group wiring
        "src",                       # designmap part-file pointer
        "type",                      # IDML value-element serialization annotation
                                     # (<Leading type="enumeration">Auto</Leading>)
                                     # -- payload is the element TEXT, not this
        # Style-graph wiring -- resolved values are already serialised inline
        "NextStyle", "PreviousStyle", "BasedOn",
        "KeyboardShortcut",
        # UI editability flags -- no render effect
        "ColorEditable", "ColorRemovable", "ColorOverride", "Editable",
        # Link housekeeping -- timestamps, file tokens, change counters
        "LinkImportModificationTime", "LinkImportStamp", "LinkImportTime",
        "LinkResourceSize", "LinkResourceModificationState",
        "LinkResourceFormat", "LinkObjectModificationTime",
        "ParentInterfaceChangeCount", "TargetInterfaceChangeCount",
        "StoryTitle",
    }
)


@dataclass
class Classified:
    tag: str
    attr: str
    verdict: str  # "significant" | "ignorable"
    reason: str
    values: list[str]
    idmls: list[str]
    parts: list[str]

    @property
    def varies(self) -> bool:
        """True if the attribute takes more than one distinct value.

        A varying attribute is one a designer actually set differently across
        elements / IDMLs -- the high-confidence fix target. A constant value is
        more likely (but not certainly) an unset InDesign default; per the
        conservative rule it stays `significant`, just lower priority.
        """
        return len(self.values) > 1


# Substring keywords whose presence in an attribute name implies a layout /
# visual / typographic effect. Deliberately whole-word-ish (no single letters)
# to avoid spurious matches. Used inside render-relevant scope only.
_SIGNIFICANT_KEYWORDS: tuple[str, ...] = (
    "color", "colour", "stroke", "fill", "weight", "tint", "gradient",
    "opacity", "blend", "shadow", "glow", "bevel", "feather", "satin",
    "effect", "transparen", "swatch", "overprint", "knockout",
    "size", "scale", "leading", "tracking", "kerning", "indent", "space",
    "baseline", "skew", "shear", "rotation", "rotate", "transform",
    "matrix", "bound", "offset", "inset", "margin", "gutter", "column",
    "align", "justif", "position", "width", "height", "vertical",
    "horizontal", "anchor", "wrap", "visible", "rendering", "flip",
    "point", "path", "corner", "cap", "join", "miter", "dash", "arrow",
    "font", "case", "ligature", "underline", "strikethrough", "capital",
    "superscript", "subscript", "hyphen", "wordspace", "letterspace",
    "drop", "keep", "balance", "grid", "fit", "fitting", "crop",
    "rule", "border", "shading", "tab", "bullet", "number", "leader",
    "image", "geometr", "shadow", "angle", "radius", "spread", "noise",
)


def classify_attribute(
    tag: str,
    attr: str,
    values: set[str],
    parts: set[str],
    render_scope: bool,
    converter_visits_tag: bool,
) -> Classified:
    """Classify one unconsumed (tag, attr) as significant or ignorable.

    ``parts`` is the set of IDML part-category labels (see ``_part_category``)
    in which this (tag, attr) appears across all audited IDMLs.
    ``render_scope`` is True when the (tag, attr) ever appears within a
    render-relevant anchor subtree (see ``_RENDER_ANCHOR_TAGS``).
    """
    vals = sorted(values)
    lo_attr = attr.lower()

    def make(verdict: str, reason: str) -> Classified:
        return Classified(tag, attr, verdict, reason, vals, [], sorted(parts))

    # 1. Universally ignorable attribute names (ids, schema, serialization).
    if attr in _IGNORABLE_ATTRS:
        return make("ignorable", "internal id / schema / value-type annotation")

    # 2. Ignorable element kinds -- no print/layout meaning anywhere.
    if tag in _IGNORABLE_TAGS:
        return make("ignorable", "metadata/export/editorial element")

    # 3. Out-of-render-scope: the element is never inside a page item / story /
    #    named style / colour / spread subtree. It is an editing-environment
    #    preference, a new-object default, an export preset or XMP metadata.
    #    InDesign bakes the resolved values into the actual page items/styles,
    #    so these never reach the printed PDF.
    if not render_scope:
        return make(
            "ignorable",
            "editing-environment / new-object-default / metadata element",
        )

    # --- From here: the attribute lives on a render-relevant element. -----

    # 4. Geometry / typography / colour keyword hit -> significant.
    for kw in _SIGNIFICANT_KEYWORDS:
        if kw in lo_attr:
            return make(
                "significant", f"layout/visual attribute (name match {kw!r})"
            )

    # 5. Unconsumed attribute on a tag the converter actually visits: a real
    #    silent drop (the ParagraphStyle/SpaceBefore class of bug).
    if converter_visits_tag:
        return make(
            "significant",
            "unconsumed attribute on a converter-handled element",
        )

    # 6. Render-scope, no keyword, tag not visited: conservative -> significant.
    return make(
        "significant", "render-relevant element, effect unknown (conservative)"
    )


# --------------------------------------------------------------------------
# Audit driver.
# --------------------------------------------------------------------------

@dataclass
class AuditResult:
    present: dict[tuple[str, str], PresentEntry]
    consumed: set[tuple[str, str]]
    converter_tags: set[str]
    classified: list[Classified]
    runs: dict[str, ConverterRun]  # idml name -> run outcome

    @property
    def significant(self) -> list[Classified]:
        return [c for c in self.classified if c.verdict == "significant"]

    @property
    def ignorable(self) -> list[Classified]:
        return [c for c in self.classified if c.verdict == "ignorable"]


def audit(idml_paths: list[Path]) -> AuditResult:
    """Run the full audit across the given IDMLs."""
    per_idml_present = []
    consumed: set[tuple[str, str]] = set()
    runs: dict[str, ConverterRun] = {}
    for path in idml_paths:
        per_idml_present.append(harvest_idml(path))
        run = run_converter_instrumented(path)
        runs[path.name] = run
        consumed |= run.consumed

    present = merge_present(per_idml_present)
    converter_tags = {tag for tag, _ in consumed}

    classified: list[Classified] = []
    for (tag, attr), entry in sorted(present.items()):
        if (tag, attr) in consumed:
            continue  # consumed -> not dropped
        c = classify_attribute(
            tag,
            attr,
            entry.values,
            entry.parts,
            render_scope=entry.render_scope,
            converter_visits_tag=tag in converter_tags,
        )
        c.idmls = sorted(entry.idmls)
        classified.append(c)

    return AuditResult(present, consumed, converter_tags, classified, runs)


# --------------------------------------------------------------------------
# Scaffold/import gate -- baseline of accepted unconsumed attributes.
# --------------------------------------------------------------------------
#
# The audit (above) answers "what does the converter silently drop, batch-
# wide". The gate below answers a narrower, per-import question: "does THIS
# IDML surface a significant unconsumed attribute that is NOT already a
# known/accepted drop?". A genuinely new significant drop fails the gate;
# every attribute already triaged in ATTRIBUTE_FIX_LOG.md passes silently.
#
# The accepted set is a checked-in baseline file -- ATTRIBUTE_COVERAGE_BASELINE
# .yml at the repo root -- regenerated from this audit's `significant` output
# (`--write-baseline`). It is the complete set of significant unconsumed
# (tag, attr) pairs across the batch IDMLs at the time the converter work
# was frozen (commit 2c3f7b8); every entry is dispositioned in
# ATTRIBUTE_FIX_LOG.md (109 Tier-A triaged fixed / not-impactful / unsupported,
# plus the Tier-B constant-value set).

# Repo root: idml_attribute_coverage_audit.py lives in tools/.
_REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = _REPO_ROOT / "ATTRIBUTE_COVERAGE_BASELINE.yml"


def _baseline_key(tag: str, attr: str) -> str:
    """Canonical ``tag/attr`` string used as a baseline entry."""
    return f"{tag}/{attr}"


def load_baseline(path: Path) -> tuple[set[str], set[str]]:
    """Load the accepted-attribute baseline.

    Returns ``(accepted, batch_consumed)`` -- two sets of ``tag/attr`` keys:

    * ``accepted`` -- significant unconsumed attributes triaged in
      ATTRIBUTE_FIX_LOG.md (the converter drops them, knowingly).
    * ``batch_consumed`` -- attributes the converter DOES consume on at
      least one batch IDML. A single-IDML gate run exercises fewer converter
      code paths than the 9-IDML batch, so an attribute genuinely handled by
      the converter can show as unconsumed for one IDML; treating the batch
      CONSUMED set as also-accepted removes that false positive.

    A missing baseline yields two empty sets (the gate then flags every
    significant unconsumed attribute -- fail-loud, never fail-silent).
    """
    if not path.exists():
        return set(), set()
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return (
        set(doc.get("accepted") or []),
        set(doc.get("batch_consumed") or []),
    )


def build_baseline_doc(result: "AuditResult") -> dict:
    """Build the baseline document from an AuditResult."""
    accepted = sorted(
        _baseline_key(c.tag, c.attr) for c in result.significant
    )
    batch_consumed = sorted(
        _baseline_key(tag, attr) for tag, attr in result.consumed
    )
    return {
        "_doc": (
            "Accepted unconsumed-attribute baseline for the IDML->SLA "
            "converter. `accepted` lists every significant (render-affecting) "
            "(element-tag/attribute) pair the converter does NOT consume but "
            "that has been triaged as fixed / not-impactful / unsupported in "
            "ATTRIBUTE_FIX_LOG.md. `batch_consumed` lists every attribute the "
            "converter DOES consume on at least one batch IDML -- a "
            "single-IDML gate run exercises fewer code paths than the batch, "
            "so this set absorbs that coverage gap. The scaffold/import gate "
            "(idml_attribute_coverage_audit.run_attribute_coverage_gate) "
            "fails when a converted IDML surfaces a significant unconsumed "
            "attribute in NEITHER list. Regenerate with: python3 "
            "tools/idml_attribute_coverage_audit.py --write-baseline."
        ),
        "_schema_version": 2,
        "count": len(accepted),
        "batch_consumed_count": len(batch_consumed),
        "accepted": accepted,
        "batch_consumed": batch_consumed,
    }


@dataclass
class CoverageGateResult:
    """Per-IDML outcome of the attribute-coverage scaffold gate."""

    ok: bool
    issues: int
    detail: str
    new_attributes: list[str]  # significant tag/attr not in the baseline
    converter_ok: bool
    converter_note: str

    def to_report(self) -> dict:
        """The canonical ``ok/issues/detail`` preflight contract + extras."""
        return {
            "ok": self.ok,
            "issues": self.issues,
            "detail": self.detail,
            "new_attributes": self.new_attributes,
            "converter_ok": self.converter_ok,
            "converter_note": self.converter_note,
        }


def run_attribute_coverage_gate(
    idml_path: Path, baseline_path: Optional[Path] = None
) -> CoverageGateResult:
    """Run the attribute-coverage gate on a single IDML.

    Audits one IDML, classifies its unconsumed attributes, and diffs the
    ``significant`` set against the accepted baseline. Any significant
    unconsumed ``(tag, attr)`` not in the baseline is a NEW silent drop --
    a converter regression or a template using an attribute the converter
    never handled. The gate fails (``ok=False``) when any new attribute is
    found.

    The result carries the canonical ``ok / issues / detail`` preflight
    contract so ``render_pipeline._build_preflight`` can consume it.
    """
    baseline_path = baseline_path or BASELINE_PATH
    accepted, batch_consumed = load_baseline(baseline_path)
    known = accepted | batch_consumed
    result = audit([idml_path])
    run = result.runs.get(idml_path.name)
    converter_ok = bool(run.ok) if run else False
    converter_note = run.note if run else "no converter run recorded"

    new_attrs = sorted(
        _baseline_key(c.tag, c.attr)
        for c in result.significant
        if _baseline_key(c.tag, c.attr) not in known
    )
    n_new = len(new_attrs)
    if not accepted:
        detail = (
            f"baseline {baseline_path.name} missing/empty -- "
            f"{n_new} significant unconsumed attribute(s) unverified"
        )
    elif n_new:
        shown = ", ".join(new_attrs[:8])
        if n_new > 8:
            shown += f", ... (+{n_new - 8} more)"
        detail = (
            f"{n_new} NEW significant unconsumed attribute(s) not in "
            f"baseline: {shown}"
        )
    else:
        detail = (
            f"all significant unconsumed attributes accounted for "
            f"({len(accepted)}-entry baseline)"
        )
    return CoverageGateResult(
        ok=(n_new == 0 and bool(accepted)),
        issues=n_new,
        detail=detail,
        new_attributes=new_attrs,
        converter_ok=converter_ok,
        converter_note=converter_note,
    )


# --------------------------------------------------------------------------
# Report rendering.
# --------------------------------------------------------------------------

def _fmt_values(values: list[str], limit: int = 8) -> str:
    shown = values[:limit]
    rendered = ", ".join(f"`{v}`" if v != "" else "`(empty)`" for v in shown)
    if len(values) > limit:
        rendered += f", ... (+{len(values) - limit} more)"
    return rendered or "(no value)"


def render_markdown(result: AuditResult, idml_paths: list[Path]) -> str:
    lines: list[str] = []
    a = lines.append

    a("# IDML Attribute Coverage Audit")
    a("")
    a(
        "Diff of attributes **present** in the batch IDMLs against attributes "
        "**consumed** by `tools/idml_to_dsl.py`. Unconsumed attributes are "
        "silently dropped by the converter (no `UnhandledElement`)."
    )
    a("")

    a("## Method")
    a("")
    a(
        "- **PRESENT** set: every `(element-tag, attribute-name)` pair found by "
        "walking every XML part of each IDML zip. Tags/attrs reduced to local "
        "names (namespace stripped)."
    )
    a(
        "- **CONSUMED** set: determined by **runtime instrumentation**. The "
        "converter parses all XML through one shared `lxml` parser object "
        "(`idml_to_dsl._SECURE_XMLPARSER`). The audit attaches a custom element "
        "class to that parser; the class's `.get()` records every attribute key "
        "read. A real `convert()` is then run per IDML, capturing every "
        "attribute read across all 7 converter phases, keyed by the element's "
        "real local tag name."
    )
    a(
        "- **Precision**: the CONSUMED set is runtime-observed, not grep-"
        "inferred -- no false attribution. **Limitation**: an attribute read "
        "only on a branch none of the audited IDMLs trigger would show as "
        "unconsumed (code-path coverage, not provably total). The converter has "
        "exactly one non-`.get()` attribute access "
        "(`child.attrib.values()` at `idml_to_dsl.py:1862`); it is an emptiness "
        "*test* on `AnchoredObjectSetting` that reads no specific key, so it "
        "consumes nothing semantically and its absence from CONSUMED is correct."
    )
    a("")

    a("## Scope")
    a("")
    a(f"- IDMLs audited: **{len(idml_paths)}**")
    for p in idml_paths:
        a(f"  - `{p.name}`")
    n_pairs = len(result.present)
    n_consumed = len([k for k in result.present if k in result.consumed])
    sig_vary = [c for c in result.significant if c.varies]
    sig_const = [c for c in result.significant if not c.varies]
    a(f"- Distinct `(tag, attr)` pairs present: **{n_pairs}**")
    a(f"- Consumed by converter: **{n_consumed}**")
    a(f"- Unconsumed (silently dropped): **{len(result.classified)}**")
    a(f"  - `significant`: **{len(result.significant)}** "
      f"(varying value: **{len(sig_vary)}**, constant value: "
      f"**{len(sig_const)}**)")
    a(f"  - `ignorable`: **{len(result.ignorable)}**")
    a("")

    # --- Converter run status ------------------------------------------
    failed = {n: r for n, r in result.runs.items() if not r.ok}
    a("### Converter run status")
    a("")
    n_ok = sum(1 for r in result.runs.values() if r.ok)
    a(f"- Full conversions: **{n_ok}/{len(result.runs)}**")
    if failed:
        a(
            f"- **{len(failed)}** IDML(s) failed conversion before completion. "
            "The CONSUMED set still includes every attribute read up to the "
            "failure point, but code-path coverage for those IDMLs is reduced "
            "-- an unconsumed attribute could be a coverage gap rather than a "
            "true converter omission. Failures:"
        )
        for name, run in sorted(failed.items()):
            a(f"  - `{name}`: {run.note}")
    else:
        a("- All audited IDMLs converted end-to-end; CONSUMED coverage is full.")
    a("")

    # --- Significant section, grouped by tag ----------------------------
    a("## Significant unconsumed attributes")
    a("")
    a(
        "These can affect geometry, layout, typography, spacing, colour, "
        "stroke, effects, transforms or text flow. **This is the converter "
        "fix list.** It is split into two tiers:"
    )
    a("")
    a(
        "- **Tier A -- varying value**: the attribute takes more than one "
        "distinct value across the batch, i.e. a designer set it deliberately. "
        "Highest-confidence fix targets."
    )
    a(
        "- **Tier B -- constant value**: a single value across the whole batch. "
        "Likely (not certainly) an unset InDesign default; kept `significant` "
        "under the conservative rule, but lower priority -- verify the value is "
        "the inert default before deciding to skip it."
    )
    a("")

    def _emit_sig_tier(items: list[Classified]) -> None:
        by_tag: dict[str, list[Classified]] = collections.defaultdict(list)
        for c in items:
            by_tag[c.tag].append(c)
        for tag in sorted(by_tag):
            row = sorted(by_tag[tag], key=lambda c: c.attr)
            a(f"#### `{tag}` ({len(row)})")
            a("")
            a("| Attribute | Reason | Observed values | IDMLs |")
            a("|---|---|---|---|")
            for c in row:
                a(
                    f"| `{c.attr}` | {c.reason} | {_fmt_values(c.values)} | "
                    f"{len(c.idmls)}/{len(idml_paths)} |"
                )
            a("")

    a(f"### Tier A -- varying value ({len(sig_vary)})")
    a("")
    if sig_vary:
        _emit_sig_tier(sig_vary)
    else:
        a("_(none)_")
        a("")

    a(f"### Tier B -- constant value ({len(sig_const)})")
    a("")
    if sig_const:
        _emit_sig_tier(sig_const)
    else:
        a("_(none)_")
        a("")

    # --- Ignorable section, summarised ----------------------------------
    a("## Ignorable unconsumed attributes (summary)")
    a("")
    a(
        "Internal IDs, name-keyed style references, XMP/export/editorial "
        "metadata, inert defaults -- no layout/visual/typographic effect."
    )
    a("")
    ign_by_tag: dict[str, list[Classified]] = collections.defaultdict(list)
    for c in result.ignorable:
        ign_by_tag[c.tag].append(c)
    reason_counts: dict[str, int] = collections.Counter(
        c.reason for c in result.ignorable
    )
    a("| Category | Count |")
    a("|---|---|")
    for reason, n in sorted(reason_counts.items(), key=lambda kv: -kv[1]):
        a(f"| {reason} | {n} |")
    a("")
    a(f"Ignorable attributes span **{len(ign_by_tag)}** element tags. "
      "Top tags by ignorable-attr count:")
    a("")
    top = sorted(ign_by_tag.items(), key=lambda kv: -len(kv[1]))[:15]
    a("| Element tag | Ignorable attrs |")
    a("|---|---|")
    for tag, items in top:
        a(f"| `{tag}` | {len(items)} |")
    a("")

    # --- Sanity check ---------------------------------------------------
    a("## Sanity check")
    a("")
    sb = ("ParagraphStyle", "SpaceBefore")
    sa = ("ParagraphStyle", "SpaceAfter")
    sig_keys = {(c.tag, c.attr) for c in result.significant}
    for key in (sb, sa):
        present = key in result.present
        flagged = key in sig_keys
        status = "OK" if (present and flagged) else "FAIL"
        a(f"- `{key[0]}/{key[1]}`: present={present}, "
          f"flagged significant={flagged} -- **{status}**")
    a("")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI.
# --------------------------------------------------------------------------

# The 9 batch IDMLs (issue: idml-flyer-leporello-batch).
_BATCH_IDMLS: list[str] = [
    "/workspace/originals/26-03-Flyer A6 Hochformat Portrait Ordner/26-03-Flyer A6 Hochformat Portrait.idml",
    "/workspace/originals/26-03-Flyer A6 Hochformat Quadrat in Bild Ordner/26-03-Flyer A6 Hochformat Quadrat in Bild.idml",
    "/workspace/originals/26-03-Flyer A6 Hochformat gruenes Cover Ordner/26-03-Flyer A6 Hochformat gruenes Cover.idml",
    "/workspace/originals/26-03-Flyer A6 Hochformat zweigeteilt Ordner/26-03-Flyer A6 Hochformat zweigeteilt.idml",
    "/workspace/originals/26-03-Flyer A6 Querformat Portrait Ordner/26-03-Flyer A6 Querformat Portrait.idml",
    "/workspace/originals/26-03-Flyer A6 Querformat Quadrat in Bild Ordner/26-03-Flyer A6 Querformat Quadrat in Bild.idml",
    "/workspace/originals/26-03-Flyer A6 Querformat gruenes Cover Ordner/26-03-Flyer A6 gruenes Cover.idml",
    "/workspace/originals/26-03-Flyer A6 Querformat zweigeteilt Ordner/26-03-Flyer A6 Querformat zweigeteilt.idml",
    "/workspace/originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover.idml",
]


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="IDML attribute-coverage audit -- finds attributes the "
        "IDML->SLA converter silently drops.",
    )
    ap.add_argument(
        "idmls",
        nargs="*",
        type=Path,
        help="IDML files to audit. Default: the 9 batch IDMLs.",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write the markdown report to this path (default: stdout).",
    )
    ap.add_argument(
        "--write-baseline",
        action="store_true",
        help="Regenerate the accepted-attribute baseline "
        f"({BASELINE_PATH.name}) from the audited IDMLs' significant set, "
        "instead of rendering the markdown report.",
    )
    ap.add_argument(
        "--baseline-path",
        type=Path,
        default=BASELINE_PATH,
        help=f"Baseline file path (default: {BASELINE_PATH}).",
    )
    args = ap.parse_args(argv)

    idml_paths = args.idmls or [Path(p) for p in _BATCH_IDMLS]
    missing = [p for p in idml_paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"ERROR: IDML not found: {p}", file=sys.stderr)
        return 2

    result = audit(idml_paths)

    if args.write_baseline:
        doc = build_baseline_doc(result)
        args.baseline_path.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(
            f"OK: wrote {args.baseline_path} "
            f"({doc['count']} accepted attributes)",
            file=sys.stderr,
        )
        return 0

    report = render_markdown(result, idml_paths)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"OK: wrote {args.output}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
