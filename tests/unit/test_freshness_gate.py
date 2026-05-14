"""Tests for tools/_freshness_gate.py and bin/tune-render --check."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
WORKTREE = HERE.parents[2]
sys.path.insert(0, str(WORKTREE / "tools"))

from _freshness_gate import (  # noqa: E402
    StaleArtifactsError,
    check_template_freshness,
    ensure_fresh,
)


def _make_template(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a fake template_dir with files; mtimes set in order, 10s apart."""
    template_dir = tmp_path / "fake-slug"
    template_dir.mkdir()
    base_time = time.time() - 1000  # well in the past
    for i, (name, content) in enumerate(files.items()):
        (template_dir / name).write_text(content)
        # set mtime to base_time + i*10 so files later in dict are clearly newer
        os.utime(template_dir / name, (base_time + i * 10, base_time + i * 10))
    return template_dir


def test_all_in_sync_returns_empty(tmp_path: Path) -> None:
    template_dir = _make_template(tmp_path, {
        "build.py": "# bp",
        "template.sla": "<sla/>",
        "preview.pdf": "%PDF-1.4",
        "page-01.png": "png",
        "page-02.png": "png",
        "page-01-hires.png": "png",
        "page-02-hires.png": "png",
        "meta.yml": "previews_for_sla: _pending_first_build\n",
    })
    assert check_template_freshness(template_dir) == []


def test_stale_sla_flagged(tmp_path: Path) -> None:
    template_dir = _make_template(tmp_path, {
        "template.sla": "<sla/>",
        "build.py": "# bp",  # newer than sla because written second
    })
    complaints = check_template_freshness(template_dir)
    assert any("template.sla" in c and "older" in c for c in complaints)


def test_stale_preview_flagged(tmp_path: Path) -> None:
    template_dir = _make_template(tmp_path, {
        "build.py": "# bp",
        "preview.pdf": "%PDF",       # written before sla
        "template.sla": "<sla/>",    # newer than preview
    })
    complaints = check_template_freshness(template_dir)
    assert any("preview.pdf" in c and "older" in c for c in complaints)


def test_missing_pngs_flagged(tmp_path: Path) -> None:
    template_dir = _make_template(tmp_path, {
        "build.py": "# bp",
        "template.sla": "<sla/>",
        "preview.pdf": "%PDF",
        # page-NN.pngs missing
    })
    complaints = check_template_freshness(template_dir)
    missing_names = {c.split(" — ")[0].split()[-1] for c in complaints if "missing" in c}
    for expected in ("page-01.png", "page-02.png", "page-01-hires.png", "page-02-hires.png"):
        assert expected in missing_names, f"missing complaint for {expected}: {complaints}"


def test_hash_mismatch_flagged(tmp_path: Path) -> None:
    template_dir = _make_template(tmp_path, {
        "build.py": "# bp",
        "template.sla": "<sla/>",
        "preview.pdf": "%PDF",
        "page-01.png": "png",
        "page-02.png": "png",
        "page-01-hires.png": "png",
        "page-02-hires.png": "png",
        "meta.yml": "previews_for_sla: wrong_hash_value\n",
    })
    complaints = check_template_freshness(template_dir)
    assert any("hash" in c.lower() for c in complaints)


def test_ensure_fresh_raises_on_stale(tmp_path: Path) -> None:
    template_dir = _make_template(tmp_path, {
        "template.sla": "<sla/>",
        "build.py": "# bp",  # newer than sla
    })
    with pytest.raises(StaleArtifactsError) as exc:
        ensure_fresh(template_dir, audit_name="test_audit")
    assert "test_audit" in str(exc.value)
    assert "bin/tune-render" in str(exc.value)


def test_ensure_fresh_silent_when_fresh(tmp_path: Path) -> None:
    template_dir = _make_template(tmp_path, {
        "build.py": "# bp",
        "template.sla": "<sla/>",
        "preview.pdf": "%PDF",
        "page-01.png": "png",
        "page-02.png": "png",
        "page-01-hires.png": "png",
        "page-02-hires.png": "png",
        "meta.yml": "previews_for_sla: _pending_first_build\n",
    })
    # should not raise
    ensure_fresh(template_dir, audit_name="test_audit")


def test_pending_first_build_hash_accepted(tmp_path: Path) -> None:
    """meta.yml::previews_for_sla='_pending_first_build' is a sentinel
    used when the converter writes meta.yml before the first render.
    The gate must accept it without complaint."""
    template_dir = _make_template(tmp_path, {
        "build.py": "# bp",
        "template.sla": "<sla/>",
        "preview.pdf": "%PDF",
        "page-01.png": "png",
        "page-02.png": "png",
        "page-01-hires.png": "png",
        "page-02-hires.png": "png",
        "meta.yml": "previews_for_sla: _pending_first_build\n",
    })
    complaints = check_template_freshness(template_dir)
    assert complaints == [], f"unexpected complaints: {complaints}"
