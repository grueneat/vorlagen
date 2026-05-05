# Visual-diff tolerance configuration

`tools/visual_diff.py` rasterises the DSL-built `template.sla` and the frozen
`baseline.pdf`, then runs `compare -metric AE -fuzz <fuzz_pct>%` per page to
count mismatched pixels. A per-template `templates/<id>/diff.yml` controls the
acceptance thresholds.

## Schema

```yaml
visual_diff:
  max_pixel_mismatch_pct: 1.0    # global default (% of page pixels allowed to differ)
  fuzz_pct: 25                   # ImageMagick -fuzz (per-pixel color tolerance)
  per_page:
    - page: 0                    # index, 0-based
      max_pixel_mismatch_pct: 0.5
      fuzz_pct: 30               # optional: tighten or loosen for this page
  per_region:                    # optional rectangular sub-regions in mm
    - page: 1
      bbox_mm: { x: 10, y: 100, w: 50, h: 60 }
      max_pixel_mismatch_pct: 5.0
      fuzz_pct: 30
```

`fuzz_pct` is the per-channel color tolerance ImageMagick applies before
declaring a pixel "different". A value of 25% absorbs the anti-aliased
edge noise that font hinting produces between two equivalent renders;
lower values produce false positives on text-heavy pages.

`max_pixel_mismatch_pct` is the cap on (mismatched_pixels / total_pixels) per
page or per region. If neither is set, the default is `1.0` (1% of pixels).

## Why the Zeitung allows up to 65% mismatch

Without bundled fonts (deferred issue), Scribus substitutes DejaVu Sans for
Gotham Narrow / Vollkorn. The substitute glyph metrics differ at the
sub-pixel level on every line of body text. A 14-page A4 newspaper with
multi-column small text sums those per-glyph differences to a high fraction
of total pixels per page — even though the layout, color choices, line
breaks, and column allocations are byte-equivalent.

The threshold tracks the **substitution noise**, not the round-trip fidelity.
`tools/sla_diff.py` is the structural ground truth: if it reports
critical=0, warning=0, the round-trip is faithful regardless of pixel-level
visual_diff numbers.

When fonts are bundled in a future issue, lower `max_pixel_mismatch_pct`
substantially (1-5% should be achievable across all pages).

## Rebaselining workflow

When the original SLA, Scribus version, or fonts change intentionally:

```bash
rm templates/<id>/baseline.pdf
xvfb-run -a scribus -g -ns -py tools/_export_pdf.py \
    <original-or-updated>.sla \
    templates/<id>/baseline.pdf
# Visually verify the regenerated baseline.pdf in a PDF viewer.
git add templates/<id>/baseline.pdf
git commit -m "rebaseline <id>: <reason>"
```

Mark `*.pdf` as binary in `.gitattributes` to keep diff noise low (already
done).
