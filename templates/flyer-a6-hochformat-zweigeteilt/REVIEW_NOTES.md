# REVIEW_NOTES — flyer-a6-hochformat-zweigeteilt

## Status: BLOCKED at Stage 1 (scaffold) — missing source asset

The IDML import for this template **cannot proceed**. Stage 1 (scaffold)
halted at the asset-extraction audit, before any `build.py`, `meta.yml`,
`baseline.pdf`, or `SCAFFOLD_INVENTORY.yml` could be produced. Stage 2
(tune) was therefore never reached.

## What the template is

`26-03-Flyer A6 Hochformat zweigeteilt` — an A6 portrait ("Hochformat")
flyer with a two-part ("zweigeteilt") layout. The baseline PDF
(`26-03-Flyer A6 Hochformat zweigeteilt.pdf`, InDesign 21.2 export,
PDF/X-4) is a 6-page document at 356.646 × 496.531 pt page size.

## The blocking issue — genuinely missing asset (HARD EXCEPTION)

`build/validation/flyer-a6-hochformat-zweigeteilt/asset_audit.yml`
reports `ok: false`. The IDML references **4** linked assets; only **3**
are present on disk in the source `Links/` folder:

Present in `Links/`:
- `Grüne Logo Bund weiss CMYK.ai` — brand logo (converted OK)
- `Plakat dunkel für Flyer.psd` — background poster (converted OK)
- `green-pine-trees-covered-with-fog.jpg` — photo (passthrough OK)

Absent from `Links/` (and from the entire `/workspace` tree):
- `common-ground-squirrel-blooming-meadow-european-suslik-spermophilus-citellus.jpg`

This is **not** an orphaned/pasteboard link. The missing JPG is placed as
a real `<Image>` (`ub34`) inside a genuine content frame on a printable
layer:

- Spread: `Spread_ud0.xml`
- Frame: `Rectangle ua81`, on layer `ub18` ("Ebene 1", `Visible="true"`,
  `Printable="true"`)
- Frame bounds ≈ 314.6 × 236.5 pt, `ItemTransform = 1 0 0 1 0 0`
- `FrameFittingOption FittingOnEmptyFrame="FillProportionally"`
- `<Link Self="ua86" ... LinkResourceURI=".../Links/common-ground-squirrel-...jpg" ...>`

Because the file is absent on disk, there is nothing to render into that
frame. Per the overnight batch gate policy (HARD EXCEPTION: never
auto-accept a genuinely missing asset), the scaffold STOPS here rather
than fabricating a placeholder.

## What to do to unblock

Re-export / re-package the IDML from InDesign with the missing image
file `common-ground-squirrel-blooming-meadow-european-suslik-spermophilus-citellus.jpg`
included in the `Links/` folder, then re-run
`bin/idml-import "<idml>" --scaffold-only`. This is an authoring concern
(missing source file in the package), not a converter bug.

## Partial state committed

- `shared/assets/flyer-a6-hochformat-zweigeteilt/` — the 3
  successfully extracted/converted assets plus `links_export.yml`.
- `build/validation/flyer-a6-hochformat-zweigeteilt/asset_audit.yml`
  — the audit verdict (`ok: false`).
- This `REVIEW_NOTES.md`.

## Tolerances granted

None — the run never reached a tolerance decision point.

## Human-review / authoring-bug items

- `authoring-bug`: missing source asset
  `common-ground-squirrel-blooming-meadow-european-suslik-spermophilus-citellus.jpg`.
  The IDML package shipped without one of its four linked images.
