"""Unit tests for tools/line_spacing_full_audit.py::_resolve_idml_source.

The full audit's IDML resolver was previously hardcoded to the
leporello-zweigeteilt IDML, so every Flyer template was audited against the
wrong source. These tests verify the rebuilt resolver loads the RIGHT IDML
for each slug, even when meta.yml::idml_source is a stale relative path.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from line_spacing_full_audit import _resolve_idml_source  # noqa: E402


def _make_idml(path: Path) -> None:
    """Write a minimal (valid-zip) placeholder IDML at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/vnd.adobe.indesign-idml-package")


def _make_template(templates_dir: Path, slug: str, idml_source: str) -> None:
    """Create templates/<slug>/meta.yml with the given idml_source value."""
    tdir = templates_dir / slug
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "meta.yml").write_text(
        yaml.safe_dump({"id": slug, "idml_source": idml_source}),
        encoding="utf-8",
    )


@pytest.fixture()
def workspace(tmp_path: Path) -> tuple[Path, Path]:
    """A fake workspace: originals/ with two IDMLs + templates/."""
    originals = tmp_path / "originals"
    flyer = originals / "26-03-Flyer A6 Hochformat Portrait Ordner" / \
        "26-03-Flyer A6 Hochformat Portrait.idml"
    lepo = originals / "26-03-Leporello z-Falz 99x210 6-seitig zwei Ordner" / \
        "26-03-Leporello z-Falz 99x210 6-seitig zweigeteiltes Cover.idml"
    _make_idml(flyer)
    _make_idml(lepo)
    templates = tmp_path / "templates"
    templates.mkdir()
    return originals, templates


def test_resolves_flyer_via_meta_relative_path(workspace) -> None:
    """A meta.yml idml_source relative to the template dir resolves."""
    originals, templates = workspace
    slug = "flyer-a6-hochformat-portraet"
    # Relative path FROM templates/<slug>/ up to originals/.
    rel = ("../../originals/26-03-Flyer A6 Hochformat Portrait Ordner/"
           "26-03-Flyer A6 Hochformat Portrait.idml")
    _make_template(templates, slug, rel)
    resolved = _resolve_idml_source(slug, templates, originals)
    assert resolved is not None
    assert resolved.name == "26-03-Flyer A6 Hochformat Portrait.idml"


def test_stale_relative_path_falls_back_to_basename_lookup(workspace) -> None:
    """A stale idml_source still resolves via its basename under originals."""
    originals, templates = workspace
    slug = "flyer-a6-hochformat-portraet"
    # An over-deep relative path that resolves to a nonexistent location;
    # the resolver must still find the IDML by its (unique) basename.
    rel = ("../../../../../../originals/26-03-Flyer A6 Hochformat "
           "Portrait Ordner/26-03-Flyer A6 Hochformat Portrait.idml")
    _make_template(templates, slug, rel)
    resolved = _resolve_idml_source(slug, templates, originals)
    assert resolved is not None
    assert resolved.name == "26-03-Flyer A6 Hochformat Portrait.idml"


def test_flyer_slug_never_resolves_to_leporello(workspace) -> None:
    """The core regression: a Flyer slug must NOT load the leporello IDML."""
    originals, templates = workspace
    slug = "flyer-a6-hochformat-portraet"
    # No meta.yml at all -> pure glob fallback. Must still pick the flyer.
    (templates / slug).mkdir(parents=True)
    resolved = _resolve_idml_source(slug, templates, originals)
    assert resolved is not None
    assert "Flyer" in resolved.name
    assert "Leporello" not in resolved.name


def test_leporello_slug_resolves_to_leporello(workspace) -> None:
    """A leporello slug resolves to the leporello IDML via glob fallback."""
    originals, templates = workspace
    slug = "falzflyer-z-falz-6-seitig-zweigeteiltes-cover"
    (templates / slug).mkdir(parents=True)
    resolved = _resolve_idml_source(slug, templates, originals)
    assert resolved is not None
    assert "Leporello" in resolved.name


def test_absolute_idml_source_honoured(workspace) -> None:
    """An absolute idml_source path is used as-is when it exists."""
    originals, templates = workspace
    slug = "flyer-a6-hochformat-portraet"
    abs_path = (originals / "26-03-Flyer A6 Hochformat Portrait Ordner" /
                "26-03-Flyer A6 Hochformat Portrait.idml")
    _make_template(templates, slug, str(abs_path))
    resolved = _resolve_idml_source(slug, templates, originals)
    assert resolved == abs_path


def test_unresolvable_slug_returns_none(workspace) -> None:
    """A slug matching no IDML and no meta.yml resolves to None."""
    originals, templates = workspace
    slug = "99-99-nonexistent-template-xyz"
    (templates / slug).mkdir(parents=True)
    assert _resolve_idml_source(slug, templates, originals) is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
