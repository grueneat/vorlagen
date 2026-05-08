# Execution: Demo-Bilder via Codex + QR-Codes für 5 neue Templates

**Started:** 2026-05-08
**Completed:** 2026-05-08
**Status:** complete
**Branch:** issue/11-demo-bilder-via-codex-qr-codes-für-5-neue-templates

## Execution Log

### Phase 1 — Tooling and deps

- [x] Task 1: Add Dockerfile dependencies (qrcode, pyzbar, libzbar0, zbar-tools) — commit 42f1318
- [x] Task 2: Patch render-pipeline filter to include previews_for_sla templates — commit 88833c8
- [x] Task 3: Build tools/qr_gen.py with determinism + scannability tests — commit 1c7bda6
- [x] Task 4: Extend tools/codex_image_gen.py — stdin=DEVNULL fix + Symbolfoto watermark + output-path recovery — commit 254e528
- [x] Task 5: Author shared/logos/sonnenblume-circle.png — commit c493b70

### Phase 2 — Manifests + slot additions

- [x] Task 6: Manifests + build.py + spec for 2 QR-only templates (postkarte, türanhänger) — commit 4b7cf41
- [x] Task 7: Manifests + build.py + spec for 3 portrait/photo-bearing templates — commit ba4164d

### Phase 3 — Generation

- [x] Task 8: Generate all QR PNGs (6 deterministic, all decode correctly) — commit bc4848f
- [x] Task 9: Generate Codex portraits + themen-photos (6/6 first-attempt success) — commit ed85e3c

### Phase 4 — Render galleries

- [x] Task 10: Re-render galleries for 5 templates with embedded demo content — commit 7d8d7e2

### Phase 5 — Visual review pass

- [x] Task 11: Run single visual-review pass with focused prompt (D10) — commit 973108f
- [x] Task 12: Final integrity sweep + README demo notes — commit 791c7d3

### Phase 6 — Ship

- [ ] Task 13: Push branch + open PR (in progress)

## Verification Results

**QR determinism (Task 12 re-run):** all 6 QR PNGs byte-identical on re-run (qrcode 8.2 + Pillow 12.2 stable).

**Render-gallery determinism:** all 5 templates byte-identical on re-run.

**CI gates:**
- `bin/check-stale-previews`: green (all 8 templates)
- `bin/validate`: green (sla_diff + visual_diff for the 3 round-trip templates)
- `python3 tools/check_ci.py`: warnings only (template-local styles + Falz spot color, expected)
- `python3 -m pytest tools/sla_lib/tests/ templates/_smoke/`: 338 passed (was 278 baseline, added 25 qr + 13 codex tests, gained smoke coverage)

**Spec_check:** pre-existing drift on all 8 templates — unchanged in count by my changes (the new slots align between spec and SLA). Pre-existing drift falls under D11's deferred spec_check tolerance work.

**EU AI Act 3-layer disclosure:**
- Visible watermark "Symbolfoto — KI-generiert" verified on every JPEG by brightness band assertion
- `synthetic: true` flag verified in every `images:` manifest entry
- README demo-content narrative added to 3 templates with synthetic photos

**Visual review (D10, single pass):** all 5 templates "ship" verdict from Gemini Vision. Codex
returned empty for all 5 (known 0.128.0 limitation with multi-image -i flag). Aggregate review
at `reviews/visual-qa-demo-content.md`.

## Deviations from Plan

### Auto-fixed (Rules 1-3)

1. **[Rule 3 - Blocker] qr_gen.py embed_logo path resolution**
   - Found during: Task 8 (first generation run)
   - Issue: `embed_logo: shared/logos/sonnenblume-circle.png` was resolved relative to
     `templates/<slug>/` (the manifest's parent.parent), so it didn't find
     the asset at the repo-root path.
   - Fix: `_generate_one()` now tries repo-root-relative first, then template-
     relative as fallback. Logo embedding now works as designed.
   - Files: tools/qr_gen.py
   - Commit: bc4848f

2. **[Rule 3 - Blocker] visual_review.py codex stdin=DEVNULL fix**
   - Found during: Task 11 (visual review run)
   - Issue: tools/visual_review.py had the same stdin-block hang risk as
     codex_image_gen.py — without DEVNULL the codex subprocess hangs on
     captured stdout.
   - Fix: applied stdin=subprocess.DEVNULL to its codex subprocess call.
   - Files: tools/visual_review.py
   - Commit: 973108f

3. **[Rule 1 - Bug] codex_image_gen.py recover_codex_output search_dir patching**
   - Found during: Task 4 (test_recovers_when_codex_saves_to_cache)
   - Issue: Default arg `search_dir=DEFAULT_CODEX_GEN_DIR` baked the value
     at function-definition time, making `mock.patch.object(codex_image_gen,
     "DEFAULT_CODEX_GEN_DIR", ...)` ineffective when generate_image()
     called recover_codex_output without an explicit search_dir.
   - Fix: changed default to `None` and look up `DEFAULT_CODEX_GEN_DIR`
     lazily inside the function body. Test now patches correctly.
   - Files: tools/codex_image_gen.py
   - Commit: 254e528

### Blocked (Rule 4)

None.

## Discovered Issues (out of scope, logged for future)

1. **Pre-existing spec drift across all 8 templates** — falls under D11's
   deferred "spec_check.py-Tolerance-Tuning" issue. Not addressed in this PR.

2. **Codex CLI 0.128.0 multi-image -i flag returns empty** — relevant to
   `tools/visual_review.py`. Codex worked fine for image GENERATION
   (single-task agent prompt) but not for image REVIEW (multiple
   `-i image.png` flags). Gemini and Claude provided the review; Codex
   stayed silent. Worth a follow-up issue if codex review is needed for
   multi-image workflows.

3. **PR #20's gallery PDFs were stale on this branch** — the themen-plakat
   preview.pdf had byte drift from a different machine's Scribus output.
   Re-rendered locally during Task 2 verification; included in the filter-
   patch commit (88833c8). Not a regression — committed-state matches
   current Scribus output now.

## Self-Check

- [x] All files from plan exist (cross-checked against `<files>` blocks per task)
- [x] All commits exist on branch (12 issue commits, all `11:` prefix)
- [x] Full verification suite passes (pytest 338 passed, 0 failed)
- [x] No stubs/TODOs/placeholders in new code
  ```
  $ grep -rn "TODO\|FIXME\|HACK\|XXX\|PLACEHOLDER\|coming soon\|not implemented" tools/qr_gen.py tools/codex_image_gen.py tools/sla_lib/tests/test_qr_gen.py tools/sla_lib/tests/test_codex_image_gen.py
  (no matches)
  ```
- [x] No leftover debug code in new code
  ```
  $ grep -rn "console\.log\|debugger\|binding\.pry\|breakpoint()" tools/qr_gen.py tools/codex_image_gen.py
  (no matches)
  ```
- **Result:** PASSED

## Commits (chronological)

```
42f1318 11: chore(deps): add qrcode 8.2, pyzbar, libzbar0, zbar-tools to Dockerfile.claude
88833c8 11: fix(render): widen pipeline filter to include previews_for_sla templates
1c7bda6 11: feat(qr): add tools/qr_gen.py with deterministic branded QR rendering + tests
254e528 11: feat(codex): stdin=DEVNULL fix + Symbolfoto watermark + output-path recovery
c493b70 11: feat(assets): add sonnenblume-circle logo for QR center-embed
4b7cf41 11: feat(postkarte+tueranhaenger): wire QR-back slots with conditional inject
ba4164d 11: feat(falzflyer+themen-plakat+tent-card): wire portrait/themen/QR slots + enlarge tent-card QR to 17mm
bc4848f 11: feat(qr): generate 6 deterministic branded QR PNGs for 5 templates
ed85e3c 11: feat(codex): generate Symbolfoto-watermarked portrait + themen-photos for 3 templates
7d8d7e2 11: feat(gallery): re-render 5 new templates with embedded demo content
973108f 11: docs(reviews): add visual QA pass for demo-content gallery refresh
791c7d3 11: docs(templates): note synthetic demo images in 3 affected READMEs
```
