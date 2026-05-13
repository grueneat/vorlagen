"""Inventory dataclass schema for ``templates/<slug>/SCAFFOLD_INVENTORY.yml``.

Pure data — no I/O, no walking. Mirrors the YAML keys in
``.issues/40-.../ISSUE.md`` section "Inventory schema" 1:1 so that
``to_yaml(inv)`` produces a file matching the documented shape.

Round-trip contract: ``from_yaml(to_yaml(inv)) == inv`` for any well-formed
``Inventory``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from typing import Any, Optional

import yaml


# Stage source tags used by frames + text runs.
# - "idml" = walked from IDML XML
# - "build_py" = found in build.py only (no IDML counterpart — e.g. fold-lines)
# - "inject_yml" = supplied by inject.yml override
# - "manual" = manually added in build.py with no IDML counterpart (e.g. PolyLine falz)
FrameSource = Optional[str]  # one of: "idml", "build_py", "inject_yml", "manual"
TextSource = Optional[str]   # one of: "build_py", "inject_yml"


@dataclass
class TextRunByStyle:
    style: str
    idml_count: int = 0
    build_py_count: int = 0
    sla_itext_count: int = 0
    pdf_word_count: int = 0


@dataclass
class TextRun:
    """One Run() emission. Used by the gate for set-equality on (text, font, fontsize)."""
    text: str
    font: str = ""
    fontsize: float = 0.0
    fcolor: str = ""
    paragraph_style: str = ""
    text_source: TextSource = "build_py"


@dataclass
class TextRunBucket:
    total_idml: int = 0
    by_paragraph_style: list[TextRunByStyle] = field(default_factory=list)
    every_idml_run_present_in_build_py: bool = False
    # Flattened list of build.py-side Run() text-rows. Used by inventory_compare
    # to surface "dropped words" between snapshots (mutation tests M1).
    build_py_runs: list[TextRun] = field(default_factory=list)
    # Flattened list of IDML-side text-runs (every non-empty
    # ``<CharacterStyleRange>`` content tuple). Drives the real set-equality
    # check for ``every_idml_run_present_in_build_py`` per the issue contract
    # "set-equality on (text, font, fontsize)". Without this list the flag
    # collapsed to a count heuristic; see issue #40 review F3.
    idml_runs: list[TextRun] = field(default_factory=list)


@dataclass
class TextFrame:
    anname: str
    idml_self: Optional[str] = None
    idml_position_mm: Optional[list[float]] = None
    build_py_position_mm: Optional[list[float]] = None
    sla_pageobject_present: bool = False
    sla_storytext_runs: int = 0
    source: FrameSource = None


@dataclass
class ImageFrame:
    anname: str
    idml_self: Optional[str] = None
    idml_link: Optional[str] = None
    idml_position_mm: Optional[list[float]] = None
    build_py_image_ref: Optional[str] = None
    build_py_position_mm: Optional[list[float]] = None
    sla_pageobject_present: bool = False
    sla_pfile_present: bool = False
    pdf_image_present: bool = False
    source: FrameSource = None


@dataclass
class PolygonFrame:
    anname: str
    idml_self: Optional[str] = None
    idml_position_mm: Optional[list[float]] = None
    build_py_position_mm: Optional[list[float]] = None
    sla_pageobject_present: bool = False
    source: FrameSource = None


@dataclass
class GroupFrame:
    anname: str
    idml_self: Optional[str] = None
    idml_position_mm: Optional[list[float]] = None
    member_count: int = 0
    source: FrameSource = None


@dataclass
class Frames:
    text_frames: list[TextFrame] = field(default_factory=list)
    image_frames: list[ImageFrame] = field(default_factory=list)
    polygon_frames: list[PolygonFrame] = field(default_factory=list)
    group_frames: list[GroupFrame] = field(default_factory=list)


@dataclass
class ParagraphStyleEntry:
    idml: str
    build_py: Optional[str] = None
    sla_pstyle_present: bool = False
    # Mirror of ``ColorEntry.build_py_extra_color`` — True when an
    # ``add_para_style(...)`` call in build.py matched this IDML style.
    # The comparator (review fix F7) uses this boolean for the
    # ``paragraph_styles.build_py`` regression check; the field is also
    # informationally redundant with ``build_py != None`` but the explicit
    # boolean is the contract surface tested by the gate.
    build_py_extra_pstyle: bool = False


@dataclass
class ColorEntry:
    idml: str
    cmyk: Optional[list[float]] = None
    build_py_extra_color: bool = False
    sla_color_present: bool = False


@dataclass
class AssetEntry:
    basename: str
    on_disk: bool = False
    classified: str = "external"  # "external" | "embedded"
    referenced_from_frames: list[str] = field(default_factory=list)
    parent_composite: Optional[str] = None
    sha256: Optional[str] = None
    byte_length: Optional[int] = None


@dataclass
class WordsBlock:
    baseline_pdf_count: int = 0
    preview_pdf_count: int = 0
    missing_from_preview: list[str] = field(default_factory=list)
    extra_in_preview: list[str] = field(default_factory=list)


@dataclass
class Inventory:
    schema_version: int = 1
    template: str = ""
    text_runs: TextRunBucket = field(default_factory=TextRunBucket)
    frames: Frames = field(default_factory=Frames)
    paragraph_styles: list[ParagraphStyleEntry] = field(default_factory=list)
    colors: list[ColorEntry] = field(default_factory=list)
    assets: list[AssetEntry] = field(default_factory=list)
    words: WordsBlock = field(default_factory=WordsBlock)
    parse_warnings: list[str] = field(default_factory=list)


# --- YAML I/O -----------------------------------------------------------------


def _as_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return {k: _as_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_as_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _as_dict(v) for k, v in obj.items()}
    return obj


def to_yaml(inv: Inventory) -> str:
    """Serialize an Inventory to YAML preserving field order from the dataclasses."""
    return yaml.safe_dump(
        _as_dict(inv),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


_DATACLASS_FIELDS: dict[type, set[str]] = {}


def _fields(cls: type) -> set[str]:
    cached = _DATACLASS_FIELDS.get(cls)
    if cached is None:
        cached = {f.name for f in fields(cls)}
        _DATACLASS_FIELDS[cls] = cached
    return cached


def _build(cls: type, data: Any) -> Any:
    """Recursively build a dataclass from a YAML-loaded dict, ignoring unknown keys."""
    if data is None:
        return cls() if is_dataclass(cls) else None
    if not is_dataclass(cls):
        return data
    kwargs: dict[str, Any] = {}
    allowed = _fields(cls)
    for k, v in (data or {}).items():
        if k not in allowed:
            continue
        kwargs[k] = _coerce_field(cls, k, v)
    return cls(**kwargs)


def _coerce_field(cls: type, name: str, value: Any) -> Any:
    """Resolve nested dataclass / list-of-dataclass fields from raw YAML."""
    # Hardcoded type map is simpler than parsing ``typing`` annotations and
    # covers every nested-dataclass case the schema actually uses.
    NESTED = {
        ("Inventory", "text_runs"): TextRunBucket,
        ("Inventory", "frames"): Frames,
        ("Inventory", "words"): WordsBlock,
    }
    LIST_OF = {
        ("TextRunBucket", "by_paragraph_style"): TextRunByStyle,
        ("TextRunBucket", "build_py_runs"): TextRun,
        ("TextRunBucket", "idml_runs"): TextRun,
        ("Frames", "text_frames"): TextFrame,
        ("Frames", "image_frames"): ImageFrame,
        ("Frames", "polygon_frames"): PolygonFrame,
        ("Frames", "group_frames"): GroupFrame,
        ("Inventory", "paragraph_styles"): ParagraphStyleEntry,
        ("Inventory", "colors"): ColorEntry,
        ("Inventory", "assets"): AssetEntry,
    }
    key = (cls.__name__, name)
    if key in NESTED:
        return _build(NESTED[key], value)
    if key in LIST_OF:
        item_cls = LIST_OF[key]
        return [_build(item_cls, item) for item in (value or [])]
    return value


def from_yaml(text: str) -> Inventory:
    data = yaml.safe_load(text) or {}
    return _build(Inventory, data)  # type: ignore[return-value]
