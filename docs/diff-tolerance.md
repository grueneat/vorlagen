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

## `region_grid` (Backport 12 — per-region visual_diff)

Optional. When present, `bin/render-gallery --audit` emits
`build/validation/<slug>/visual_diff_regions.yml` and a heatmap PNG per
page. The grid divides each page into `cols × rows` cells and computes
per-cell mismatch so localised drift (a centred headline shifted 5mm, a
visible icon swap) no longer washes out under the page-wide average.

### Schema

```yaml
visual_diff:
  max_pixel_mismatch_pct: 1.0       # page-wide default (unchanged)
  fuzz_pct: 25.0                    # page-wide default (unchanged)
  region_grid:
    cols: 6                         # grid columns per page (default 6)
    rows: 4                         # grid rows per page (default 4)
    default_max_pixel_mismatch_pct: 5.0   # optional; cell-default threshold
    default_fuzz_pct: 25.0                # optional; cell-default fuzz
    per_cell:                       # optional per-cell overrides
      - page: 0
        col: 3
        row: 2
        max_pixel_mismatch_pct: 10.0
        fuzz_pct: 30.0
      - page: 1
        col: 0
        row: 0
        max_pixel_mismatch_pct: 0.5
```

### Default grid

The default `6×4` cell grid (24 cells per page) is sized so each cell on a
DIN-A4 page is approximately a "design slot" (~35×74mm). Cell sizing is
computed via integer division with the last column/row absorbing the
modulus so the grid always covers the full image without gap or overlap.

### Tolerance resolution

For each cell, `(max_pixel_mismatch_pct, fuzz_pct)` is resolved in this
order (first match wins):

1. Matching `per_cell` entry for `(page, col, row)`.
2. `region_grid.default_max_pixel_mismatch_pct` / `default_fuzz_pct`.
3. Page-level `per_page` entry (if any).
4. Top-level `max_pixel_mismatch_pct` / `fuzz_pct`.

### Heatmap output

`build/validation/<slug>/visual_diff_heatmap-page-NN.png` is emitted per
page. Cell colors follow a two-segment ramp:

- Green (76, 175, 80) at `pct <= 0`
- Amber (255, 193, 7) at `pct == threshold`
- Red (244, 67, 54) at `pct >= 2 × threshold`

Each cell is labelled with its `mismatch_pct`. The underlying baseline is
desaturated to grayscale so the layout remains readable through the
RGBA overlay (alpha 180/255).

### Tie-in with `tools/diff_bbox_extract.py`

The bbox extractor surfaces anomaly SHAPES; the grid surfaces a stable
SPATIAL MAP. Use them together: bbox to find drift, grid to confirm
spatial concentration. The grid is more stable across iterations because
it doesn't depend on bbox attribution heuristics — useful when comparing
two consecutive renders for regression.

### Per-cell vs page-wide semantics

Per-cell mismatch is computed via Pillow's `ImageChops.difference` and
max-channel-delta thresholding. This approximates ImageMagick's
`compare -metric AE -fuzz N%` but uses max-channel instead of Euclidean
distance. Cell totals will NOT exactly sum to the page-wide AE value —
expect ~1-2 % drift, which is acceptable for the regions's job (finding
hot zones, not replacing the page-wide audit).

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
