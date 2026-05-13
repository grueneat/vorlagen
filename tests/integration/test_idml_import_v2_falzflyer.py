"""End-to-end integration test for bin/idml-import on v2 falzflyer.

Skips cleanly when:
  - originals/ directory is absent (CI without licensed assets), OR
  - required system tools (scribus, pdftocairo) are missing, OR
  - brand fonts cannot be loaded.

When all preconditions are met, exercises the full driver pipeline and
asserts the expected artifact + exit-code invariants.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"


pytestmark = pytest.mark.integration


def _find_v2_idml() -> Path | None:
    """Locate the v2 falzflyer IDML under originals/.

    The matcher requires "falzflyer" or "kandidat" in the basename — these
    are the v2-falzflyer-specific tokens. The previous matcher also accepted
    "leporello" / "z-falz", but those tokens match unrelated templates
    (e.g. the 26-03 Leporello family), which made the test pick the wrong
    IDML and assert the wrong slug's artifacts."""
    if not (ROOT / "originals").exists():
        return None
    for p in sorted((ROOT / "originals").rglob("*.idml")):
        name_lower = p.name.lower()
        if "falzflyer" in name_lower or "kandidat" in name_lower:
            return p
    return None


def _have_required_tools() -> bool:
    for t in ("pdftocairo", "scribus"):
        if shutil.which(t) is None:
            return False
    return True


def _skip_if_not_runnable() -> None:
    idml = _find_v2_idml()
    if idml is None:
        pytest.skip("originals/ missing; v2 falzflyer IDML not available in CI.")
    if not _have_required_tools():
        pytest.skip("scribus or pdftocairo not on PATH.")


# ---------------------------------------------------------------------------
# Test 1 — happy path: bin/idml-import end-to-end on v2 falzflyer.
# ---------------------------------------------------------------------------
def test_bin_idml_import_v2_falzflyer_end_to_end():
    _skip_if_not_runnable()
    idml = _find_v2_idml()
    assert idml is not None
    bin_path = ROOT / "bin" / "idml-import"
    result = subprocess.run(
        [
            sys.executable,
            str(bin_path),
            str(idml),
            "--max-iterations", "3",
            "--non-interactive",
            "--allow-composite-ai",
            "--accept-residual", "*",
            "--reimport",
            "--no-brand-fonts",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    # 0 = full PASS or all-residual-accepted. 2 = needs review. 3 = regression
    # or max-iter exceeded. Any of these is acceptable as a smoke test;
    # we just need invariants below.
    assert result.returncode in (0, 2, 3), (
        f"unexpected exit {result.returncode}; stderr=\n{result.stderr}"
    )
    assert (ROOT / "build" / "validation" / SLUG / "preflight.yml").exists()
    iteration_log = ROOT / "build" / SLUG / "iteration.jsonl"
    assert iteration_log.exists()
    rows = iteration_log.read_text().splitlines()
    assert len(rows) >= 1
    report = ROOT / "build" / SLUG / "import_report.md"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert any(v in text for v in ("PASS", "NEEDS_REVIEW", "BLOCKED"))
    asset_audit = ROOT / "build" / "validation" / SLUG / "asset_audit.yml"
    assert asset_audit.exists()


# ---------------------------------------------------------------------------
# Test 2 — missing IDML fails cleanly with non-zero exit.
# ---------------------------------------------------------------------------
def test_bin_idml_import_missing_idml_fails_cleanly():
    bin_path = ROOT / "bin" / "idml-import"
    result = subprocess.run(
        [sys.executable, str(bin_path), "/nonexistent/path.idml"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Test 3 — --scaffold-only halts after first audit, no convergence loop.
# ---------------------------------------------------------------------------
def test_bin_idml_import_scaffold_only_no_convergence_loop():
    _skip_if_not_runnable()
    idml = _find_v2_idml()
    assert idml is not None
    bin_path = ROOT / "bin" / "idml-import"
    result = subprocess.run(
        [
            sys.executable,
            str(bin_path),
            str(idml),
            "--scaffold-only",
            "--reimport",
            "--non-interactive",
            "--allow-composite-ai",
            "--no-brand-fonts",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode in (0, 1), (
        f"unexpected exit {result.returncode}; stderr=\n{result.stderr}"
    )
    tdir = ROOT / "templates" / SLUG
    if result.returncode == 0:
        for sub in ("build.py", "meta.yml", "diff.yml", "baseline.pdf"):
            assert (tdir / sub).exists(), f"missing {sub} in {tdir}"
        iteration_log = ROOT / "build" / SLUG / "iteration.jsonl"
        if iteration_log.exists():
            assert len(iteration_log.read_text().splitlines()) >= 1
