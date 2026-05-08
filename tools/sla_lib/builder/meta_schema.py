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
