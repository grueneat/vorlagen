"""JSON-Schema validation for ``templates/<slug>/meta.yml::brand_overrides``.

Each entry in ``brand_overrides`` is a ``{id, reason}`` pair. The id
must match ``^brand:[a-z_0-9.]+$`` and reason must be a non-empty
string. Schema-violations raise ``ValueError`` with a clear message.

Per CONTEXT D5 + RESEARCH §3: jsonschema is already a project
dependency, no new runtime deps.

A warning (not error) is emitted when an override id is not a known
BRAND_CONSTRAINTS rule id — this catches typos without blocking CI.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import jsonschema
import yaml


_BRAND_OVERRIDE_SCHEMA: dict = {
    "type": "array",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "reason"],
        "properties": {
            "id": {
                "type": "string",
                "pattern": r"^brand:[A-Za-z_0-9.]+$",
            },
            "reason": {
                "type": "string",
                "minLength": 1,
            },
        },
    },
}


_SLA_DIFF_STRICT_SCHEMA: dict = {"type": "boolean"}


# Issue #25: body_block_margins schema for the brand:band_consistency rule.
# Pins the OUTER STRUCTURE (header/free/footer bands + L/R margins) of every
# body-pool page. Templates without this field skip the band rule cleanly.
_BAND_SPEC_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["bands", "margins"],
    "properties": {
        "bands": {
            "type": "object",
            "additionalProperties": False,
            "required": ["header", "footer"],
            "properties": {
                "header": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["y_top_mm", "y_bottom_mm"],
                    "properties": {
                        "y_top_mm": {"type": "number"},
                        "y_bottom_mm": {"type": "number"},
                    },
                },
                "footer": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["y_top_mm", "y_bottom_mm"],
                    "properties": {
                        "y_top_mm": {"type": "number"},
                        "y_bottom_mm": {"type": "number"},
                    },
                },
            },
        },
        "margins": {
            "type": "object",
            "additionalProperties": False,
            "required": ["left", "right"],
            "properties": {
                "left": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["outer_mm", "inner_mm"],
                    "properties": {
                        "outer_mm": {"type": "number"},
                        "inner_mm": {"type": "number"},
                    },
                },
                "right": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["outer_mm", "inner_mm"],
                    "properties": {
                        "outer_mm": {"type": "number"},
                        "inner_mm": {"type": "number"},
                    },
                },
            },
        },
        "background_decoration": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "fills": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}


def _meta_path(slug: str, root: Path | None = None) -> Path:
    if root is None:
        root = Path(__file__).resolve().parents[3]
    return root / "templates" / slug / "meta.yml"


def load_brand_overrides(slug: str, root: Path | None = None) -> set[str]:
    """Return the set of brand-rule IDs to skip for ``slug``.

    Reads ``templates/<slug>/meta.yml``. Returns empty set if file is
    absent or has no ``brand_overrides`` field. Raises ValueError on
    schema violation. Warns (not raises) on unknown rule IDs.
    """
    p = _meta_path(slug, root)
    if not p.exists():
        return set()
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"meta.yml at {p} is not valid YAML: {e}") from e
    if not isinstance(data, dict):
        return set()
    overrides = data.get("brand_overrides")
    if overrides is None:
        return set()
    return _validate_and_collect_ids(overrides, p)


def load_band_spec(slug: str, root: Path | None = None) -> dict | None:
    """Return the parsed ``body_block_margins`` dict, or ``None`` if absent.

    Reads ``templates/<slug>/meta.yml``. Returns ``None`` when the file is
    absent OR has no ``body_block_margins`` field — the brand:band_consistency
    rule then silently skips the template (opt-out semantics).

    Raises ``ValueError`` on YAML parse error or schema violation. Issue #25.
    """
    p = _meta_path(slug, root)
    if not p.exists():
        return None
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"meta.yml at {p} is not valid YAML: {e}") from e
    if not isinstance(data, dict):
        return None
    spec = data.get("body_block_margins")
    if spec is None:
        return None
    try:
        jsonschema.validate(instance=spec, schema=_BAND_SPEC_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(
            f"meta.yml at {p} body_block_margins malformed: {e.message} "
            f"(at path {list(e.absolute_path)})"
        ) from e
    return spec


def load_sla_diff_strict(slug: str, root: Path | None = None) -> bool:
    """Return per-template ``sla_diff_strict`` flag (default True).

    Templates that intentionally diverge from their upstream SLA opt out
    by setting ``sla_diff_strict: false`` at the top level of meta.yml.
    Used by ``tools/render_pipeline.py::_run_sla_diff_strict`` to skip
    the strict round-trip diff for opted-out templates (issue #16).
    """
    p = _meta_path(slug, root)
    if not p.exists():
        return True
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"meta.yml at {p} is not valid YAML: {e}") from e
    if not isinstance(data, dict) or "sla_diff_strict" not in data:
        return True
    value = data["sla_diff_strict"]
    try:
        jsonschema.validate(instance=value, schema=_SLA_DIFF_STRICT_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(
            f"meta.yml sla_diff_strict at {p} must be a boolean: {e.message}"
        ) from e
    return bool(value)


def _validate_and_collect_ids(overrides: Any, path: Path) -> set[str]:
    try:
        jsonschema.validate(instance=overrides, schema=_BRAND_OVERRIDE_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(
            f"meta.yml brand_overrides at {path} is malformed: {e.message} "
            f"(at path {list(e.absolute_path)})"
        ) from e
    # Cross-check ids against known BRAND_CONSTRAINTS — warn on typos.
    from .brand_constraints import BRAND_CONSTRAINTS
    known = {r.id for r in BRAND_CONSTRAINTS}
    ids: set[str] = set()
    for entry in overrides:
        rid = entry["id"]
        if rid not in known:
            warnings.warn(
                f"meta.yml at {path}: brand_override id {rid!r} is not in "
                f"BRAND_CONSTRAINTS ({sorted(known)})",
                stacklevel=2,
            )
        ids.add(rid)
    return ids
