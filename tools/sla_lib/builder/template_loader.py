"""Public template-loader for structural_check + audit_alignment (Issue #22).

Extracted from structural_check.py L104-122. The ``sys.modules.pop()``
pattern is critical — it prevents cross-template cache contamination
when ``--all`` iterates (P-9 in research/pitfalls.md).

Backwards compatibility: ``structural_check.py`` re-exports
``load_build_module`` as ``_load_build_module`` so tests (e.g.
``test_structural_check.py``) continue importing it from the original
module path.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def load_build_module(slug: str, root: Path = _REPO_ROOT):
    """Load ``templates/<slug>/build.py`` via importlib (with full package path).

    We use ``importlib.util.spec_from_file_location`` with a unique module
    name to avoid sys.modules cross-contamination when ``--all`` iterates.
    """
    p = root / "templates" / slug / "build.py"
    if not p.exists():
        raise FileNotFoundError(f"template build.py not found: {p}")
    mod_name = f"_strcheck_template_{slug.replace('-', '_')}"
    # Drop any cached module so re-imports always re-evaluate.
    sys.modules.pop(mod_name, None)
    spec = importlib.util.spec_from_file_location(mod_name, p)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"cannot create import spec for {p}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod
