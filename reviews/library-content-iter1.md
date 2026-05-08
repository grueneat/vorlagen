# Visual Review Iter-1 — Issue #13 Library Content

**Date:** 2026-05-08
**Issue:** zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen
**Branch:** issue/13-zentralisierte-demo-bild-bibliothek-alle-templates-auffüllen

## Library inventory (13 images)

| Category | ID | Source size | KB | Watermark band visible |
|----------|----|-------------|-----|------------------------|
| portraits | portrait_maria | 1024×1536 | 131 | yes |
| portraits | portrait_stefan | 1024×1536 | 198 | yes |
| themen | themen_klimaschutz_solar | 1536×1024 | 309 | yes |
| themen | themen_klimaschutz_windrad | 1536×1024 | 130 | yes |
| themen | themen_soziales_kaffeehaus | 1536×1024 | 177 | yes |
| themen | themen_soziales_gemeindebau | 1536×1024 | 290 | yes |
| themen | themen_bildung_volksschule | 1536×1024 | 288 | yes |
| themen | themen_bildung_erwachsenenbildung | 1536×1024 | 154 | yes |
| themen | themen_wirtschaft_handwerk | 1536×1024 | 199 | yes |
| themen | themen_verkehr_radweg | 1536×1024 | 253 | yes |
| kontext | kontext_infostand_szene | 1536×1024 | 242 | yes |
| kontext | kontext_buergerversammlung | 1536×1024 | 261 | yes |
| kontext | kontext_stammtisch_cafe | 1536×1024 | 128 | yes |

All 13 images carry the bottom-band Symbolfoto watermark (verified
programmatically: bottom 4% L-channel mean materially darker than middle 50%).

## Per-template verification

| Template | Source | Library content rendered | Watermark in cropped variants | Round-trip |
|----------|--------|--------------------------|-------------------------------|------------|
| postkarte-a6-kampagne | template-preview.sla | hero (84×127mm portrait crop of klimaschutz_solar) | yes (re-stamped) | green |
| plakat-a1-hochformat | template-preview.sla | full-page hero (594×414mm) | yes | green |
| zeitung-a4-grun | template-preview.sla | 11 photo slots filled | yes | green |
| themen-plakat-a3-quer | template.sla | themen-hero (180×60mm landscape crop of windrad) | yes | n/a (new template) |
| wahltag-tueranhaenger | template.sla | portrait_stefan @65×85mm | yes | n/a |
| infostand-tent-card-a5-quer | template.sla | kontext_infostand_szene @44×33mm | yes | n/a |
| kandidat-falzflyer-din-lang | template.sla | portrait_maria + 3 themen photos | yes | n/a |
| wahlaufruf-postkarte-a6-quer | template.sla | (no image slots — by design) | n/a | n/a |

## Verification commands run

```bash
# Library schema valid
PYTHONPATH=tools python3 -c "from sla_lib.builder import library; assert not library.validate_manifest()"

# All builds succeed
for slug in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun \
            themen-plakat-a3-quer wahltag-tueranhaenger \
            infostand-tent-card-a5-quer kandidat-falzflyer-din-lang \
            wahlaufruf-postkarte-a6-quer; do
  python3 templates/$slug/build.py
done

# Round-trip diff GREEN on all 3 production templates
for slug in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun; do
  orig=$(grep "original_sla:" templates/$slug/meta.yml | sed 's/.*: //; s/^\.\.\/\.\.\///')
  PYTHONPATH=tools python3 tools/sla_diff.py --left "$orig" --right templates/$slug/template.sla --strict --allow-brand-extras
done

# Stale previews check passes for all 8
bin/check-stale-previews

# Brand CI valid for clean + preview SLAs
for sla in templates/*/template.sla templates/*/template-preview.sla; do
  python3 tools/check_ci.py "$sla"
done

# Full unit-test suite
python3 -m pytest tools/sla_lib/tests/  # 321 passed

# Full gallery render
bin/render-gallery  # 8/8 OK
```

All checks green.

## Watermark-after-crop regression test (R-WATERMARK-CROP)

`tools/sla_lib/tests/test_library.py::CropForFrameTests` verifies:

- `test_landscape_crop_from_portrait_keeps_watermark`: portrait 1024×1536 →
  landscape ~200×60mm — band still visible at output bottom (re-applied via
  `_apply_watermark_to_image`).
- `test_portrait_crop_from_landscape_keeps_watermark`: landscape 1536×1024 →
  portrait 87×105mm — band still visible.
- `test_determinism`: same crop call twice produces byte-identical bytes.

Both regression tests passing.

## Findings

**Iter-1 verdict: all 8 templates merge-ready, gallery konsistent.**

No blocking findings. Library content renders cleanly across all slot
geometries (portrait, landscape, square, very-wide aspect). Watermark
re-stamping at cropped resolutions works correctly.

Manual visual inspection of `templates/<slug>/page-*.png` (rendered by
`bin/render-gallery`) confirms:

- Library demo images visible in all expected slots.
- No distorted aspect ratios (cropping preserves proportions).
- No accidental cropping of important content (faces in portraits,
  subject centers in themen photos).
- Symbolfoto bottom-band watermark visible on every embedded image.
- Brand colors (Dunkelgrün, Gelb, accents) and typography unaffected by
  demo content.
- Production templates' clean `template.sla` keep empty image slots — only
  `template-preview.sla` carries demo content.

## Notes on Codex generation

All 6 new images generated on first attempt (0 retries each). Total cost
estimate: ~$0.48 (6 × ~$0.08). Validated #11 documentary-framing prompt
pattern continues to produce usable output without content-policy refusals.

## Iter-2

Not needed.
