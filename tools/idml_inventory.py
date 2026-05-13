"""Back-compat shim — module moved to ``tools.walkers.walk_idml_inventory``.

Re-exports every public and private (single-underscore) name so existing
callers like ``from idml_inventory import _extract_annames_from_build_py``
keep working.
"""
from tools.walkers import walk_idml_inventory as _impl

# Re-export every attribute except dunders.
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)
del _name, _impl

if __name__ == "__main__":
    import sys
    sys.exit(main())  # type: ignore[name-defined]  # provided by re-export
