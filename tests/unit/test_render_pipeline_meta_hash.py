"""Unit tests for meta.yml::previews_for_sla auto-update on render (F-020).

The hash pin used to require a manual `sha256sum + edit meta.yml` step
after every render. F-020 moves it into `_orchestrate_template` so the
pin always tracks the just-emitted template.sla, even when downstream
audits/diffs flag a regression.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import render_pipeline as rp  # noqa: E402


def _make_template_dir(tmp_path, *, with_build_py=False, sla_bytes=b"<SCRIBUSUTF8NEW/>") -> Path:
    """Create a minimal template dir with meta.yml + template.sla."""
    tdir = tmp_path / "test-template"
    tdir.mkdir()
    meta = {
        "id": "test-template",
        "previews_for_sla": "stale-hash-0000000000000000000000000000000000000000000000000000000000",
    }
    (tdir / "meta.yml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    (tdir / "template.sla").write_bytes(sla_bytes)
    if with_build_py:
        # A trivial build.py that rewrites template.sla with deterministic content.
        (tdir / "build.py").write_text(
            "from pathlib import Path\n"
            "Path(__file__).parent.joinpath('template.sla').write_bytes(b'<NEW/>')\n",
            encoding="utf-8",
        )
    return tdir


def test_meta_hash_auto_updates_after_build(tmp_path, monkeypatch):
    """After _orchestrate_template runs build.py, meta.yml has the new hash."""
    tdir = _make_template_dir(tmp_path, with_build_py=True)
    # Stub out the family/single orchestration so the test doesn't need
    # Scribus, pdftoppm, etc. — we only care about the hash side-effect.
    monkeypatch.setattr(rp, "_orchestrate_single", lambda *a, **k: 0)
    monkeypatch.setattr(rp, "_orchestrate_family", lambda *a, **k: 0)
    # ROOT is used for site/public mirror dirs; the stubs don't touch them.
    monkeypatch.setattr(rp, "ROOT", tmp_path)

    args = SimpleNamespace(dry_run=False, skip_visual_diff=True)
    rc = rp._orchestrate_template(tdir, args)
    assert rc == 0

    # After the run, meta.yml should have the SHA256 of the new bytes
    # written by build.py (b"<NEW/>"), not the stale placeholder.
    expected = hashlib.sha256(b"<NEW/>").hexdigest()
    meta_after = yaml.safe_load((tdir / "meta.yml").read_text(encoding="utf-8"))
    assert meta_after["previews_for_sla"] == expected


def test_meta_hash_not_updated_in_dry_run(tmp_path, monkeypatch):
    """--dry-run must not mutate meta.yml."""
    tdir = _make_template_dir(tmp_path, with_build_py=True)
    monkeypatch.setattr(rp, "_orchestrate_single", lambda *a, **k: 0)
    monkeypatch.setattr(rp, "_orchestrate_family", lambda *a, **k: 0)
    monkeypatch.setattr(rp, "ROOT", tmp_path)

    stale = yaml.safe_load((tdir / "meta.yml").read_text())["previews_for_sla"]
    args = SimpleNamespace(dry_run=True, skip_visual_diff=True)
    rc = rp._orchestrate_template(tdir, args)
    assert rc == 0

    # meta.yml::previews_for_sla must be unchanged.
    meta_after = yaml.safe_load((tdir / "meta.yml").read_text())
    assert meta_after["previews_for_sla"] == stale


def test_meta_hash_skipped_for_family(tmp_path, monkeypatch):
    """Family templates manage per-size hashes inside _orchestrate_family —
    _orchestrate_template must NOT clobber them with a template.sla hash."""
    tdir = _make_template_dir(tmp_path, with_build_py=False)
    meta = {
        "id": "test-template",
        "type": "family",
        "previews_for_sla": {"a0": "stale-a0", "a1": "stale-a1"},
    }
    (tdir / "meta.yml").write_text(yaml.safe_dump(meta), encoding="utf-8")

    monkeypatch.setattr(rp, "_orchestrate_single", lambda *a, **k: 0)
    monkeypatch.setattr(rp, "_orchestrate_family", lambda *a, **k: 0)
    monkeypatch.setattr(rp, "ROOT", tmp_path)

    args = SimpleNamespace(dry_run=False, skip_visual_diff=True)
    rc = rp._orchestrate_template(tdir, args)
    assert rc == 0

    # The dict pin must be unchanged: _orchestrate_family owns its update.
    meta_after = yaml.safe_load((tdir / "meta.yml").read_text())
    assert meta_after["previews_for_sla"] == {"a0": "stale-a0", "a1": "stale-a1"}


def test_meta_hash_survives_build_py_absent(tmp_path, monkeypatch):
    """If build.py is absent (DSL-only template), the hash should still
    reflect the committed template.sla."""
    tdir = _make_template_dir(tmp_path, with_build_py=False)
    monkeypatch.setattr(rp, "_orchestrate_single", lambda *a, **k: 0)
    monkeypatch.setattr(rp, "_orchestrate_family", lambda *a, **k: 0)
    monkeypatch.setattr(rp, "ROOT", tmp_path)

    args = SimpleNamespace(dry_run=False, skip_visual_diff=True)
    rc = rp._orchestrate_template(tdir, args)
    assert rc == 0

    expected = hashlib.sha256(b"<SCRIBUSUTF8NEW/>").hexdigest()
    meta_after = yaml.safe_load((tdir / "meta.yml").read_text())
    assert meta_after["previews_for_sla"] == expected
