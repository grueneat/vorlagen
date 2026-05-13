"""Back-compat shim — module moved to ``tools.walkers.walk_idml_inventory``.

Re-exports the explicit public + private (single-underscore) surface the
existing callers depend on. Listed names are derived from grep'ing for
``from idml_inventory import`` and ``import idml_inventory``:

- ``tools/render_pipeline.py`` imports ``run_inventory`` and ``_yaml_dump``.
- ``tests/unit/test_idml_inventory.py`` imports several private helpers.

Listing names explicitly (review fix L1) avoids polluting the shim's
public surface with stdlib imports (argparse, re, sys, zipfile, yaml,
xml.etree.ElementTree, pathlib, typing) that the old ``for n in dir(_impl)``
loop swept in.
"""
from tools.walkers.walk_idml_inventory import (  # noqa: F401
    # Public surface.
    main,
    run_inventory,
    walk_idml,
    # Private helpers consumed by tools/render_pipeline.py + tests.
    _build_hint,
    _collect_spread_items,
    _extract_annames_from_build_py,
    _load_printable_layers,
    _load_spread_order,
    _yaml_dump,
)

__all__ = [
    "main",
    "run_inventory",
    "walk_idml",
    "_build_hint",
    "_collect_spread_items",
    "_extract_annames_from_build_py",
    "_load_printable_layers",
    "_load_spread_order",
    "_yaml_dump",
]


if __name__ == "__main__":
    import sys
    sys.exit(main())
