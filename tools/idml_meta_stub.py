#!/usr/bin/env python3
"""One-shot helper: extract a ``slots:`` block from an emitted IDML→DSL
``build.py`` for paste into ``meta.yml``.

Usage:
    python3 tools/idml_meta_stub.py templates/<slug>/build.py [--paragraph-style-slugs]

The script imports the build.py, builds the Document via ``build_template()``,
walks every page item with a non-empty ``anname``, and emits a YAML slots
mapping using the item's class (TextFrame/ImageFrame/Polygon) as a hint for
the slot ``type``.

When ``--paragraph-style-slugs`` is passed, the script also prints the list of
emitted ParaStyle slugs so they can be pasted under ``ci_overrides.non_ci_styles``.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import yaml

_TYPE_HINT = {
    "TextFrame": "text",
    "ImageFrame": "image",
    "Polygon": "shape",
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Emit a slots: YAML block from an IDML-emitted build.py.")
    ap.add_argument("build_py", type=Path, help="Path to templates/<slug>/build.py")
    ap.add_argument("--paragraph-style-slugs", action="store_true",
                    help="Also print the list of ParaStyle slugs to stdout (after the slots block).")
    args = ap.parse_args(argv)

    if not args.build_py.exists():
        print(f"build.py not found: {args.build_py}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    spec = importlib.util.spec_from_file_location("_emitted_build", args.build_py)
    if spec is None or spec.loader is None:
        print(f"cannot load spec: {args.build_py}", file=sys.stderr)
        return 2
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    doc = m.build_template()

    slots: dict[str, dict[str, str]] = {}
    for page in doc.pages:
        for item in page.items:
            anname = getattr(item, "anname", "")
            if not anname:
                continue
            cls = type(item).__name__
            slot_type = _TYPE_HINT.get(cls, "shape")
            slots[anname] = {
                "type": slot_type,
                "description": "",
                "anname": anname,
            }

    out = yaml.safe_dump({"slots": slots}, allow_unicode=True, sort_keys=False)
    print(out)

    if args.paragraph_style_slugs:
        # Walk doc._extra_para_styles (dict) or doc.para_styles (list);
        # support whichever the DSL exposes.
        para_container = getattr(doc, "_extra_para_styles", None)
        if para_container is None:
            para_container = getattr(doc, "para_styles", None)
        slugs = []
        if isinstance(para_container, dict):
            for name in para_container:
                if name.startswith("idml/"):
                    slugs.append(name)
        elif para_container is not None:
            for ps in para_container:
                name = getattr(ps, "name", None)
                if name and name.startswith("idml/"):
                    slugs.append(name)
        print("\n# ParaStyle slugs (paste under ci_overrides.non_ci_styles):")
        for s in sorted(slugs):
            print(f"  - {s!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
