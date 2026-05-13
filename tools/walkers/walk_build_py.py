"""build.py walker for SCAFFOLD_INVENTORY (AST-based).

Parses a (reconciled) ``templates/<slug>/build.py`` with ``ast.parse`` and
harvests the structural calls the gate cares about:

- ``doc.add_para_style(ParaStyle(name=...))``
- ``doc.add_color(name, cmyk=(...))``
- ``pageN.add(TextFrame|ImageFrame|Polygon|Oval|GraphicLine|PolyLine(...))``
- Nested ``Run(text=..., font=..., fontsize=..., fcolor=..., paragraph_style=...)``
  inside ``runs=[...]`` (set-equality input for the text-run gate)

For any kwarg that ``ast.literal_eval`` cannot resolve (e.g. a name reference
or a non-literal expression) we append a ``"<file>:<line>: non-literal kwarg
<kwarg>"`` warning to ``parse_warnings`` and skip the kwarg.

``inline_image_data='<base64>'`` payloads are hashed (sha256) and stored as
``inline_image_data_sha256`` + ``inline_image_data_bytes``; the raw base64 is
discarded so the inventory stays small.

PolyLine frames carry ``source='manual'`` (the converter never emits PolyLine
for IDML elements; they're hand-added fold-line marks).
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any, Optional

import yaml


_FRAME_KINDS = (
    "TextFrame", "ImageFrame", "Polygon", "Oval",
    "GraphicLine", "PolyLine",
)


def _frame_bucket(kind: str) -> str:
    """Map a constructor name to the frames-bucket key."""
    return {
        "TextFrame": "text_frames",
        "ImageFrame": "image_frames",
        "Polygon": "polygon_frames",
        "Oval": "polygon_frames",
        "GraphicLine": "polygon_frames",
        "PolyLine": "polyline_frames",
    }[kind]


def _try_literal(node: ast.AST) -> tuple[bool, Any]:
    """``ast.literal_eval`` wrapper. Returns ``(ok, value)``."""
    try:
        return True, ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return False, None


def _kwargs(call: ast.Call, warnings: list[str], file_label: str) -> dict[str, Any]:
    """Return ``{kw: literal_value}`` for kwargs that ``ast.literal_eval``s.

    Non-literal kwargs are recorded in ``warnings`` and skipped. The kwarg
    ``runs`` is INTENTIONALLY skipped here — caller extracts it via
    :func:`_extract_runs` because each item is a ``Call`` (Run()) that
    ``ast.literal_eval`` can't evaluate.
    """
    out: dict[str, Any] = {}
    for kw in call.keywords:
        if kw.arg is None or kw.arg == "runs":
            continue
        ok, val = _try_literal(kw.value)
        if not ok:
            warnings.append(
                f"{file_label}:{kw.value.lineno}: non-literal kwarg {kw.arg}"
            )
            continue
        out[kw.arg] = val
    return out


def _extract_runs(call: ast.Call, warnings: list[str], file_label: str) -> list[dict]:
    """Pull ``runs=[Run(text=..., ...), ...]`` out of a frame call."""
    runs: list[dict] = []
    for kw in call.keywords:
        if kw.arg != "runs":
            continue
        if not isinstance(kw.value, (ast.List, ast.Tuple)):
            warnings.append(
                f"{file_label}:{kw.value.lineno}: non-list runs= kwarg"
            )
            continue
        for el in kw.value.elts:
            if not (isinstance(el, ast.Call) and isinstance(el.func, ast.Name)
                    and el.func.id == "Run"):
                continue
            run_kw: dict[str, Any] = {}
            for inner in el.keywords:
                if inner.arg is None:
                    continue
                ok, val = _try_literal(inner.value)
                if not ok:
                    warnings.append(
                        f"{file_label}:{inner.value.lineno}: "
                        f"non-literal Run kwarg {inner.arg}"
                    )
                    continue
                run_kw[inner.arg] = val
            runs.append(run_kw)
    return runs


def _position_mm(kwargs: dict[str, Any]) -> Optional[list[float]]:
    try:
        return [
            float(kwargs["x_mm"]),
            float(kwargs["y_mm"]),
            float(kwargs["w_mm"]),
            float(kwargs["h_mm"]),
        ]
    except (KeyError, TypeError, ValueError):
        return None


def _hash_inline_image(blob: str) -> tuple[str, int]:
    raw = blob.encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _load_inject_text_overrides(inject_yml: Optional[Path]) -> set[str]:
    """Return the set of text strings declared in inject.yml overrides.

    inject.yml is permitted to override any frame's ``runs`` text. We use this
    set to tag matching Run entries with ``text_source='inject_yml'``.
    Missing or malformed inject.yml yields an empty set silently.
    """
    if not inject_yml or not inject_yml.exists():
        return set()
    try:
        data = yaml.safe_load(inject_yml.read_text(encoding="utf-8")) or {}
    except Exception:
        return set()
    texts: set[str] = set()

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("text", "runs", "value") and isinstance(v, str):
                    texts.add(v)
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(data)
    return texts


def walk_build_py(build_py: Path, inject_yml: Optional[Path] = None) -> dict[str, Any]:
    """Walk a build.py AST. Return inventory-shaped dict for the orchestrator.

    Return shape::

        {
            "text_runs": [
                {text, font, fontsize, fcolor, paragraph_style, text_source}, ...
            ],
            "frames": {
                "text_frames":   [{anname, position_mm, style?, ...}, ...],
                "image_frames":  [{anname, position_mm, image?, inline_image_data_sha256?, ...}],
                "polygon_frames":[{anname?, position_mm, ...}, ...],
                "polyline_frames":[{position_mm, source: "manual", ...}, ...],
            },
            "add_para_style_names": list[str],     # values from add_para_style(ParaStyle(name=...))
            "add_color_names": list[str],          # first positional arg of add_color(...)
            "parse_warnings": list[str],
        }
    """
    file_label = str(build_py)
    text = build_py.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=file_label)
    warnings: list[str] = []
    text_runs: list[dict] = []
    frames: dict[str, list[dict]] = {
        "text_frames": [],
        "image_frames": [],
        "polygon_frames": [],
        "polyline_frames": [],
    }
    add_para_style_names: list[str] = []
    add_color_names: list[str] = []

    inject_texts = _load_inject_text_overrides(inject_yml)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func

        # add_para_style(...) / add_color(...) — bare names OR
        # attribute calls like doc.add_para_style(...) / doc.add_color(...)
        method_name = ""
        if isinstance(func, ast.Attribute):
            method_name = func.attr
        elif isinstance(func, ast.Name):
            method_name = func.id

        if method_name == "add_para_style":
            # Either add_para_style('name', ...) or add_para_style(ParaStyle(name='name'))
            name: Optional[str] = None
            if node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    name = first.value
                elif isinstance(first, ast.Call):
                    for inner in first.keywords:
                        if inner.arg == "name":
                            ok, val = _try_literal(inner.value)
                            if ok and isinstance(val, str):
                                name = val
                                break
            for kw in node.keywords:
                if kw.arg == "name":
                    ok, val = _try_literal(kw.value)
                    if ok and isinstance(val, str):
                        name = val
            if name is not None:
                add_para_style_names.append(name)
            continue

        if method_name == "add_color":
            name = None
            if node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    name = first.value
            for kw in node.keywords:
                if kw.arg == "name":
                    ok, val = _try_literal(kw.value)
                    if ok and isinstance(val, str):
                        name = val
            if name is not None:
                add_color_names.append(name)
            continue

        if method_name == "add":
            # pageN.add(<FrameKind>(...))
            if not node.args:
                continue
            inner_call = node.args[0]
            if not isinstance(inner_call, ast.Call):
                continue
            inner_func = inner_call.func
            if not isinstance(inner_func, ast.Name):
                continue
            kind = inner_func.id
            if kind not in _FRAME_KINDS:
                continue
            kw = _kwargs(inner_call, warnings, file_label)
            row: dict[str, Any] = {
                "anname": kw.get("anname"),
                "position_mm": _position_mm(kw),
            }
            # Capture optional fields we care about per frame kind.
            if "style" in kw:
                row["style"] = kw["style"]
            if "image" in kw:
                row["image"] = kw["image"]
            if "fill" in kw:
                row["fill"] = kw["fill"]
            if "inline_image_data" in kw and isinstance(kw["inline_image_data"], str):
                sha, blen = _hash_inline_image(kw["inline_image_data"])
                row["inline_image_data_sha256"] = sha
                row["inline_image_data_bytes"] = blen
                # Never carry the raw base64 in the inventory.
                kw.pop("inline_image_data", None)
            if kind == "PolyLine":
                row["source"] = "manual"

            # Harvest runs (text-runs are appended to the document-level list).
            if kind == "TextFrame":
                runs = _extract_runs(inner_call, warnings, file_label)
                for r in runs:
                    text_value = r.get("text", "") or ""
                    if not text_value:
                        # Empty text — these are separator/paragraph break Runs.
                        continue
                    text_source = "inject_yml" if text_value in inject_texts else "build_py"
                    text_runs.append({
                        "text": text_value,
                        "font": r.get("font", "") or "",
                        "fontsize": float(r.get("fontsize") or 0),
                        "fcolor": r.get("fcolor", "") or "",
                        "paragraph_style": (
                            r.get("paragraph_style") or kw.get("style") or ""
                        ),
                        "text_source": text_source,
                    })

            bucket = _frame_bucket(kind)
            frames[bucket].append(row)

    return {
        "text_runs": text_runs,
        "frames": frames,
        "add_para_style_names": add_para_style_names,
        "add_color_names": add_color_names,
        "parse_warnings": warnings,
    }
