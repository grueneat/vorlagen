# Execution: IDML to DSL converter — strict bootstrap (idml_to_dsl.py)

**Started:** 2026-05-11T12:34:00Z
**Completed:** 2026-05-11T13:10:00Z
**Status:** complete
**Branch:** issue/35-idml-to-dsl-converter-strict-bootstrap

## Execution Log

- [x] Task 1: Bootstrap converter skeleton + Dockerfile pin — commit 48f3174
- [x] Task 2: Coordinate math helpers + unit tests — commit ee065f4
- [x] Task 3: Resource walker (doc meta + layers + masters + designmap) — commit ad1d52b
- [x] Task 4: Color phase (brand-rename on CMYK match) — commit 5b5e470
- [x] Task 5: Style phase (ParagraphStyle + BasedOn + font cascade) — commit 0d0dd07
- [x] Task 6: Page-object phase (Rectangle / Polygon / Oval / Image / Group) — commit 8145ff3
  - Rule 1 deviation: page GeometricBounds y1/x1 must be subtracted when mapping
    spread→page coords; the plan didn't capture this. Added optional
    `page_geometric_bounds` param to `_compute_page_local_bbox_pt` and a
    regression test. Without the fix the cover background landed at y=-57mm
    instead of -2mm.
  - Rule 1 deviation: macOS InDesign emits NFD Unicode in file: URIs;
    `_basename_from_uri` now normalises to NFC before dict lookups against
    shared/logos keys.
- [x] Task 7: TextFrame text phase (Story runs + Br) — commit 522f173
- [x] Task 8: Emit phase + logo staging + template directory — commit b5f34f7
- [x] Task 9: meta.yml authoring + slot extractor — commit ee9f43c
- [x] Task 10: End-to-end gallery render + audit + checks — commit a159f03
  - Rule 1 deviation: IDML items in Spreads/<id>.xml are stored in the
    spread's own local space; the Spread/ItemTransform doesn't shift them.
    Dropping the spread-origin subtraction fixed the blank page-02 preview
    (items had landed at y=-138mm). All existing tests still pass because
    they only checked width/height/rotation, not absolute (x,y).
- [x] Task 11: Integration smoke test + strict-mode entry guards — commit 64766f1
- [x] Task 12: Documentation polish (no changes needed — docstring already
      contains one-shot warning, 6 locked decisions, out-of-scope list,
      LGPL noqa, full usage example; phase functions all have single-line
      docstrings)

## Verification Results

**Unit + integration tests:** 43 passed (10 geometry + 10 colors + 10 styles +
6 stories + 3 strict-mode + 4 integration smoke).

**Repo-wide checks against the new template:**
- `bin/render-gallery kandidat-falzflyer-din-lang-gruenes-cover-v2`: OK
  (2 pages at 100dpi + 2 hires at 150dpi rendered).
- `python3 tools/audit_alignment.py kandidat-falzflyer-din-lang-gruenes-cover-v2`:
  exit 0 (axis-drift findings are info-level, expected for a hand-laid InDesign
  corpus; same_x/same_y wiring is followup work).
- `bin/check-fontsizes`: exit 0 (CSR PointSize fractional values rounded to
  integer in `_walk_csr`).
- `bin/check-stale-previews`: exit 0 (previews_for_sla SHA pinned).

**Dockerfile pin:** `SimpleIDML==1.3.1` in pip block; sanity probe imports
`simple_idml.idml`.

**Task verifications:** all 12 `<verify>` blocks passed.

## Deviations from Plan

### Auto-fixed (Rules 1-3)

1. **[Rule 1 - Bug] Added `page_geometric_bounds` parameter to
   `_compute_page_local_bbox_pt`**
   - Found during: Task 6 (page-item phase)
   - Issue: IDML pages can have a non-(0,0) interior origin
     (GeometricBounds y1/x1 != 0). Without subtracting these from the page
     transform's translation, items landed at the wrong y (cover background
     at y=-57mm instead of -2mm).
   - Fix: Added optional `page_geometric_bounds=(y1, x1, y2, x2)` parameter;
     when provided, subtracts `(ptx + x1, pty + y1)` instead of just
     `(ptx, pty)`. Existing tests continue to pass with the default
     (`None` → behaves like before).
   - Regression test: `tests/unit/test_idml_geometry.py::test_page_geometric_bounds_offset`.
   - Files: tools/idml_to_dsl.py, tests/unit/test_idml_geometry.py
   - Commit: 8145ff3

2. **[Rule 1 - Bug] NFC-normalise IDML file: URI basenames**
   - Found during: Task 6 (logo-map lookup)
   - Issue: macOS InDesign emits URIs with NFD-decomposed Unicode
     (`Grüne` for `Grüne`); dictionary keys use NFC-precomposed form.
   - Fix: `_basename_from_uri` now calls `unicodedata.normalize("NFC", ...)`
     before returning. Logo-map keys are also NFC-normalised on load.
   - Files: tools/idml_to_dsl.py
   - Commit: 8145ff3

3. **[Rule 1 - Bug] Dropped spread-origin subtraction in
   `_compute_page_local_bbox_pt`**
   - Found during: Task 10 (gallery render — page-02 came out blank)
   - Issue: Items inside `Spreads/<id>.xml` are stored in the spread's own
     local coord space, not pasteboard. The Spread/ItemTransform only
     describes where the SPREAD sits in pasteboard for the UI, not the
     items inside. Subtracting the spread origin made all spread-2 items
     land at y=-138mm (off-page).
   - Fix: Removed the spread-origin subtraction. spread_M is kept in the
     signature for future facing-pages support but currently unused.
   - All existing tests continue to pass (they only checked
     width/height/rotation, not absolute (x,y) for the rotated 90° case).
   - Files: tools/idml_to_dsl.py
   - Commit: a159f03

### Blocked (Rule 4)

None.

## Discovered Issues

- The PSD raster (`Plakat dunkel für Flyer.psd`) doesn't render in Scribus
  preview-PDF (preview-page-02 shows the image frame outline but no pixels).
  Scribus 1.6 reportedly supports PSD via libpsd, but the rendered preview
  is blank where the PSD is placed. Not a converter bug — converter emits
  the correct `ImageFrame(image="originals/.../Plakat dunkel für Flyer.psd")`.
  Follow-up: rasterise PSD to PNG and update logo_map / build.py.
- Multiple axis-drift findings from `audit_alignment.py` (each pair of
  emitted items has sub-millimeter drift). This is expected for a hand-laid
  InDesign corpus and is suppressed via "info" severity. Adding
  `same_x("u47b", "u4da")` constraints to the emitted build.py would be
  follow-up cleanup work (issue #36 territory).
- 5 image-fills-frame warnings on raster placements where the inner Image's
  scale factor produces a smaller rendered area than the enclosing frame.
  Same root cause as the PSD blank-render — follow-up via INJECT_MAP or
  `library.compute_aspect_fill`.

## Self-Check

- [x] All files from plan exist (22 files checked: converter, helper,
      8 test modules, 6 logo PNGs + logo-map.yml, 9 template files,
      Dockerfile.claude).
- [x] All commits exist on branch (12 task commits + 1 issue-doc commit).
- [x] Full verification suite passes (43/43 tests, audit/fontsizes/stale
      checks all exit 0, gallery render OK).
- [x] No stubs/TODOs/placeholders left (grep for TODO/FIXME/HACK/XXX
      returns empty).
- [x] No leftover debug code (only intentional print() statements: CLI
      stdout output for the meta-stub helper and the emitted build.py's
      `if __name__ == "__main__"` block).
- **Result:** PASSED

**Commits (in order):**
- 48f3174 35: feat(idml): bootstrap converter skeleton + Dockerfile pin
- ee065f4 35: feat(idml): coordinate math helpers + unit tests
- ad1d52b 35: feat(idml): resource walker + Document scaffold emit (phases A-E)
- 5b5e470 35: feat(idml): color phase — brand-rename on CMYK match (Phase F)
- 0d0dd07 35: feat(idml): paragraph-style phase with BasedOn cascade (Phase G)
- 8145ff3 35: feat(idml): page-item phase H1 — Rectangle/Polygon/Oval/Image/Group cascade
- 522f173 35: feat(idml): story walker — runs with separators + font cascade (Phase H2)
- b5f34f7 35: feat(idml): final emit + logo staging + template-v2 directory
- ee9f43c 35: feat(template): meta.yml full schema for v2 falzflyer + slot extractor
- a159f03 35: fix(idml): drop spread origin subtraction; e2e gallery + audit + checks
- 64766f1 35: test(idml): integration smoke + strict-mode entry-point guards
