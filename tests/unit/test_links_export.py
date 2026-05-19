"""Unit tests for tools/links_export.py (issue 35, Phase 2).

Covers the three units the tool ships:

  1. Slugification: German umlaut transliteration + general non-ASCII handling.
  2. Dispatch table: extension → kind mapping.
  3. Passthrough copy: raster files end up at the slugified output path.

Conversion commands (``pdftocairo``, ``convert``) are intentionally NOT
mocked at this level — the integration test in ``tests/integration/``
exercises the full pipeline against the bundled corpus and is skipped when
the source assets aren't available (gitignored ``originals/``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from links_export import (  # noqa: E402
    AssetEntry,
    _DISPATCH,
    _emit_manifest,
    _is_cmyk_raster,
    _passthrough_copy,
    _slugify,
    _srgb_icc_path,
    derive_out_dir,
    export,
    kind_for_extension,
    out_ext_for,
)


# ---------------------------------------------------------------------------
# Slugification
# ---------------------------------------------------------------------------
class TestSlugify:
    def test_plain_ascii_kept(self):
        assert _slugify("BlueSky weiss") == "bluesky-weiss"

    def test_already_slugified_idempotent(self):
        assert _slugify("green-pine-trees-covered-with-fog") == (
            "green-pine-trees-covered-with-fog"
        )

    def test_umlaut_ue(self):
        # ü → ue, NOT bare u (NFKD would otherwise strip the combining diaeresis).
        assert _slugify("Plakat dunkel für Flyer") == "plakat-dunkel-fuer-flyer"

    def test_umlaut_ae_oe_ss(self):
        assert _slugify("Ärger und Ärgernisse") == "aerger-und-aergernisse"
        assert _slugify("Über böse Köche") == "ueber-boese-koeche"
        assert _slugify("weiß-grün") == "weiss-gruen"

    def test_capital_umlauts(self):
        assert _slugify("ÄRGER") == "aerger"
        assert _slugify("ÜBER") == "ueber"

    def test_gruene_logo_full(self):
        assert _slugify("Grüne Logo Bund weiss CMYK") == (
            "gruene-logo-bund-weiss-cmyk"
        )

    def test_collapses_punctuation(self):
        assert _slugify("a__b...c   d!!!e") == "a-b-c-d-e"

    def test_strips_leading_trailing_hyphens(self):
        assert _slugify("---hi---") == "hi"
        assert _slugify("...hi...") == "hi"

    def test_dotted_filename_stem_with_space(self):
        # The IDML's ``Plakat dunkel für Flyer.psd`` stem (sans extension).
        assert _slugify("Plakat dunkel für Flyer") == "plakat-dunkel-fuer-flyer"

    def test_idml_filename_stem(self):
        stem = "26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2"
        assert _slugify(stem) == (
            "falzflyer-z-falz-6-seitig-gruenes-cover-2"
        )

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _slugify("")
        with pytest.raises(ValueError):
            _slugify("---")
        with pytest.raises(ValueError):
            _slugify("   ")


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
class TestDispatch:
    def test_ai_is_vector(self):
        assert kind_for_extension(".ai") == "vector_ai"
        assert _DISPATCH[".ai"].out_ext == ".png"

    def test_psd_is_raster_psd(self):
        assert kind_for_extension(".psd") == "raster_psd"
        assert _DISPATCH[".psd"].out_ext == ".png"

    def test_jpg_and_jpeg_both_raster_jpg(self):
        assert kind_for_extension(".jpg") == "raster_jpg"
        assert kind_for_extension(".jpeg") == "raster_jpg"
        # JPG passthrough must preserve the .jpg extension (no re-encoding).
        assert _DISPATCH[".jpg"].out_ext == ".jpg"
        assert _DISPATCH[".jpeg"].out_ext == ".jpg"

    def test_png_is_raster_png(self):
        assert kind_for_extension(".png") == "raster_png"
        assert _DISPATCH[".png"].out_ext == ".png"

    def test_case_insensitive_extension(self):
        # Filenames on disk may be ``.AI`` or ``.PSD``.
        assert kind_for_extension(".AI") == "vector_ai"
        assert kind_for_extension(".PSD") == "raster_psd"
        assert kind_for_extension(".JPG") == "raster_jpg"

    def test_unsupported_returns_none(self):
        assert kind_for_extension(".tiff") is None
        assert kind_for_extension(".indd") is None
        assert kind_for_extension(".eps") is None

    def test_passthrough_recipe_marker(self):
        # The manifest description must say "passthrough" for raster sources;
        # the converter's auto-invoke fallback may want to surface this.
        assert _DISPATCH[".jpg"].description == "passthrough"
        assert _DISPATCH[".png"].description == "passthrough"
        assert "pdftocairo" in _DISPATCH[".ai"].description
        assert "convert" in _DISPATCH[".psd"].description


# ---------------------------------------------------------------------------
# Path derivation
# ---------------------------------------------------------------------------
class TestDeriveOutDir:
    def test_slugifies_idml_stem(self):
        idml = Path("/abs/path/Some Fancy IDML Name.idml")
        result = derive_out_dir(idml)
        # The base is the repo root, but we only assert the trailing segment.
        assert result.name == "some-fancy-idml-name"
        assert result.parent.name == "assets"
        assert result.parent.parent.name == "shared"

    def test_target_idml_path(self):
        idml = Path(
            "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes "
            "Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig "
            "gruenes Cover 2.idml"
        )
        result = derive_out_dir(idml)
        assert result.name == (
            "falzflyer-z-falz-6-seitig-gruenes-cover-2"
        )


# ---------------------------------------------------------------------------
# Passthrough copy + manifest emission (no external commands)
# ---------------------------------------------------------------------------
class TestPassthroughAndManifest:
    def test_copy_renames_to_slug(self, tmp_path: Path):
        src = tmp_path / "Hello World.png"
        src.write_bytes(b"\x89PNG\r\n\x1a\n fake bytes")
        out = tmp_path / "out" / "hello-world.png"
        _passthrough_copy(src, out)
        assert out.read_bytes() == src.read_bytes()

    def test_manifest_is_sorted(self, tmp_path: Path):
        entries = [
            AssetEntry(
                original_basename="zeta.jpg",
                output_rel="shared/assets/x/zeta.jpg",
                kind="raster_jpg",
                recipe="passthrough",
            ),
            AssetEntry(
                original_basename="alpha.ai",
                output_rel="shared/assets/x/alpha.png",
                kind="vector_ai",
                recipe="pdftocairo -png -transp -r 600 -singlefile",
            ),
        ]
        manifest_path = _emit_manifest(tmp_path, tmp_path, entries, [])
        text = manifest_path.read_text(encoding="utf-8")
        # Determinism: alphabetical sort means ``alpha.ai`` precedes ``zeta.jpg``.
        assert text.index("alpha.ai") < text.index("zeta.jpg")
        # Header is present.
        assert text.startswith("# links_export.yml")
        assert "Source: " in text
        assert "Run: python3 tools/links_export.py" in text

    def test_manifest_skipped_block(self, tmp_path: Path):
        manifest_path = _emit_manifest(
            tmp_path, tmp_path, [],
            [("weird.tiff", "unsupported extension '.tiff'")],
        )
        text = manifest_path.read_text(encoding="utf-8")
        assert "skipped:" in text
        assert "weird.tiff" in text

    def test_manifest_deterministic(self, tmp_path: Path):
        """Same entries written to same out_dir twice → byte-identical bytes.

        Catches dict-order leaks from ``yaml.safe_dump`` (we pin
        ``sort_keys=True`` for exactly this reason).
        """
        entries = [
            AssetEntry(
                original_basename=f"item{i}.jpg",
                output_rel=f"shared/assets/x/item{i}.jpg",
                kind="raster_jpg",
                recipe="passthrough",
            )
            for i in range(10)
        ]
        a_dir = tmp_path / "a"
        a_dir.mkdir()
        first = _emit_manifest(a_dir, tmp_path, entries, []).read_bytes()
        second = _emit_manifest(a_dir, tmp_path, entries, []).read_bytes()
        assert first == second
        # And the manifest is sorted alphabetically regardless of input order.
        text = first.decode("utf-8")
        # Reverse-shuffle the entries; emit to a fresh dir; bytes must still
        # match because sort_keys=True normalises the order.
        shuffled = list(reversed(entries))
        b_dir = tmp_path / "b"
        b_dir.mkdir()
        third = _emit_manifest(b_dir, tmp_path, shuffled, []).read_bytes()
        # Headers reference the same source dir, so the full bytes match.
        assert text == third.decode("utf-8")


# ---------------------------------------------------------------------------
# End-to-end export with only passthrough sources (no external binaries)
# ---------------------------------------------------------------------------
class TestExportPassthroughOnly:
    """Drive :func:`export` against a Links/ dir containing only raster files.

    This exercises the directory walk, dispatch routing, slug naming, and
    manifest emission without depending on ``pdftocairo`` or ``convert``
    being installed. The integration test in tests/integration/ covers the
    AI/PSD path against the real bundled corpus.
    """

    def test_full_passthrough_dir(self, tmp_path: Path):
        links = tmp_path / "Links"
        links.mkdir()
        # NFC-normalised filenames; mix cases + an unsupported extension.
        (links / "BlueSky weiss.png").write_bytes(b"\x89PNG\r\n\x1a\n a")
        (links / "Grüne Logo.jpg").write_bytes(b"\xff\xd8\xff fake jpg")
        (links / "lower.jpeg").write_bytes(b"\xff\xd8\xff fake jpeg")
        (links / "weird.tiff").write_bytes(b"II*\x00 fake tiff")
        (links / ".hidden.png").write_bytes(b"dotfile")

        out_dir = tmp_path / "out"
        result = export(links, out_dir, quiet=True)

        # 3 supported assets, 1 skipped, hidden file ignored.
        assert len(result.entries) == 3
        assert len(result.skipped) == 1
        assert result.skipped[0][0] == "weird.tiff"

        kinds = {e.original_basename: e.kind for e in result.entries}
        assert kinds["BlueSky weiss.png"] == "raster_png"
        assert kinds["Grüne Logo.jpg"] == "raster_jpg"
        assert kinds["lower.jpeg"] == "raster_jpg"

        # Slugified outputs exist with the right extension.
        assert (out_dir / "bluesky-weiss.png").exists()
        assert (out_dir / "gruene-logo.jpg").exists()
        assert (out_dir / "lower.jpeg").exists() is False  # renamed to .jpg
        assert (out_dir / "lower.jpg").exists()

        # Manifest references repo-relative paths under shared/assets/ when
        # the output dir lives under ROOT; here it's a tmp_path, so the
        # fallback is an absolute string. Either way, paths point at real files.
        for entry in result.entries:
            target = Path(entry.output_rel)
            # output_rel is either repo-relative or absolute; resolve against
            # tmp_path when it isn't absolute.
            if not target.is_absolute():
                target = result.out_dir.parent.parent / target  # not used in this test
            else:
                assert target.exists()

    def test_idempotent_rerun(self, tmp_path: Path):
        """Running export twice over the same Links/ + same out dir is stable.

        The manifest is YAML-safe-dumped sort_keys=True; the conversion
        outputs are byte-equal for passthrough sources. A re-run must
        produce byte-identical output files.
        """
        links = tmp_path / "Links"
        links.mkdir()
        (links / "a.png").write_bytes(b"first")
        (links / "b.jpg").write_bytes(b"second")

        out = tmp_path / "out"

        export(links, out, quiet=True)
        first_manifest = (out / "links_export.yml").read_bytes()
        first_a = (out / "a.png").read_bytes()
        first_b = (out / "b.jpg").read_bytes()

        # Re-run; outputs must remain byte-identical.
        export(links, out, quiet=True)
        assert (out / "links_export.yml").read_bytes() == first_manifest
        assert (out / "a.png").read_bytes() == first_a
        assert (out / "b.jpg").read_bytes() == first_b


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------
class TestErrorPaths:
    def test_missing_links_dir(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            export(tmp_path / "does-not-exist", tmp_path / "out", quiet=True)

    def test_links_dir_is_file(self, tmp_path: Path):
        fake = tmp_path / "looks-like-a-dir"
        fake.write_text("hi")
        with pytest.raises(NotADirectoryError):
            export(fake, tmp_path / "out", quiet=True)


# ---------------------------------------------------------------------------
# CMYK detection + ICC-aware conversion routing
# ---------------------------------------------------------------------------
class TestCmykHandling:
    """The CMYK→sRGB path. Scribus 1.6.x cannot render a CMYK JPEG (blank)
    and a non-ICC CMYK→RGB inversion posterises colours, so every CMYK raster
    is routed through an ICC-aware conversion (out extension becomes .png for
    JPEG sources)."""

    def test_rgb_jpeg_is_not_cmyk(self, tmp_path: Path):
        from PIL import Image

        src = tmp_path / "rgb.jpg"
        Image.new("RGB", (8, 8), (10, 120, 60)).save(src)
        assert _is_cmyk_raster(src) is False

    def test_cmyk_jpeg_detected(self, tmp_path: Path):
        from PIL import Image

        src = tmp_path / "cmyk.jpg"
        Image.new("CMYK", (8, 8), (10, 20, 30, 40)).save(src)
        assert _is_cmyk_raster(src) is True

    def test_out_ext_rgb_jpeg_passthrough(self, tmp_path: Path):
        from PIL import Image

        src = tmp_path / "rgb.jpg"
        Image.new("RGB", (8, 8), (10, 120, 60)).save(src)
        # An RGB JPEG passes through verbatim — extension stays .jpg.
        assert out_ext_for(src) == ".jpg"

    def test_out_ext_cmyk_jpeg_becomes_png(self, tmp_path: Path):
        from PIL import Image

        src = tmp_path / "cmyk.jpg"
        Image.new("CMYK", (8, 8), (10, 20, 30, 40)).save(src)
        # A CMYK JPEG is converted to PNG (Scribus cannot render CMYK JPEGs).
        assert out_ext_for(src) == ".png"

    def test_out_ext_psd_and_png_static(self, tmp_path: Path):
        # Non-JPEG kinds keep their static dispatch extension.
        assert out_ext_for(tmp_path / "x.psd") == ".png"
        assert out_ext_for(tmp_path / "x.png") == ".png"

    def test_psd_recipe_marks_icc_aware(self):
        # The dispatch description must signal the ICC-aware conversion so
        # downstream tooling no longer sees the bare "convert -flatten".
        assert "ICC" in _DISPATCH[".psd"].description

    def test_srgb_icc_profile_available(self):
        # The conversion needs an sRGB ICC profile; the dev container ships
        # one. If this fails the environment is missing a colour-profile pkg.
        assert _srgb_icc_path() is not None
