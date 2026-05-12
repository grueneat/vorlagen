"""Integration smoke test for the IDML to DSL converter (issue 35).

Runs the converter against the bundled target IDML and verifies:
- Zero ``UnhandledElement``.
- Emitted build.py imports clean.
- Emitted build.py exposes >=30 emitted page items across 2 pages.
- meta.yml parses, has 2 pages and bleed_mm=2.

Phase 2 (asset export): the converter is now invoked via the auto-invoke
fallback — no ``--logo-map`` or ``--assets-dir``. The sibling ``Links/``
directory triggers ``tools/links_export.py`` automatically, producing
``shared/assets/<idml-slug>/links_export.yml``. Strict mode raises if the
manifest is missing a basename.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
IDML = (
    ROOT
    / "originals"
    / "26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner"
    / "26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml"
)


pytestmark = pytest.mark.skipif(
    not IDML.exists(),
    reason="Source IDML not available (originals/ is gitignored — symlink to enable).",
)


def _run_converter(out_py: Path) -> subprocess.CompletedProcess:
    """Invoke the converter via the Phase 2 auto-invoke flow.

    No --asset-map, no --logo-map: the converter shells out to
    tools/links_export.py against the IDML's sibling Links/ directory.
    """
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "idml_to_dsl.py"),
            str(IDML),
            str(out_py),
            "--template-id",
            "kandidat-falzflyer-din-lang-gruenes-cover-v2",
        ],
        capture_output=True,
        text=True,
    )


def _import_emitted(out_py: Path):
    """Import the emitted build.py, return its module object."""
    sys.path.insert(0, str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location("_emitted_build", out_py)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_converter_runs_clean(tmp_path: Path):
    # Mirror a templates/<slug>/ depth so the emitted HERE.parents[1] resolves.
    out = tmp_path / "templates" / "k" / "build.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    r = _run_converter(out)
    assert r.returncode == 0, f"stderr:\n{r.stderr}\nstdout:\n{r.stdout}"
    assert out.exists()
    assert "UnhandledElement" not in r.stderr


def test_emitted_build_imports(tmp_path: Path):
    out = tmp_path / "templates" / "k" / "build.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    r = _run_converter(out)
    assert r.returncode == 0, r.stderr
    m = _import_emitted(out)
    doc = m.build_template()
    assert len(doc.pages) == 2
    total = sum(len(p.items) for p in doc.pages)
    # Corpus has 16 items on page 1 and 30 on page 2 = 46 total; pin a lower
    # bound to detect regressions without locking in the exact count.
    assert total >= 30, f"expected >=30 emitted items, got {total}"


def test_emitted_build_saves_sla(tmp_path: Path):
    out = tmp_path / "templates" / "k" / "build.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    r = _run_converter(out)
    assert r.returncode == 0, r.stderr
    m = _import_emitted(out)
    sla = tmp_path / "k.sla"
    m.build(sla)
    assert sla.exists()
    assert sla.stat().st_size > 10_000  # rough smoke; sibling falzflyer SLAs are ~50KB


def test_meta_yml_parses():
    import yaml

    meta_path = (
        ROOT
        / "templates"
        / "kandidat-falzflyer-din-lang-gruenes-cover-v2"
        / "meta.yml"
    )
    d = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    assert d["id"] == "kandidat-falzflyer-din-lang-gruenes-cover-v2"
    assert d["pages"] == 2
    assert d["preflight"]["bleed_mm"] == 2     # locked decision #4
    # Slot schema present.
    assert isinstance(d["slots"], dict)
    assert len(d["slots"]) >= 30
