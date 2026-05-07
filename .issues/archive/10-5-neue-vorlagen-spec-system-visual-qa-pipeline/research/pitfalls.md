# Pitfalls / Edge-Cases / Risks — Issue 10

**Researched:** 2026-05-07
**Researcher:** pitfalls subagent (paranoia mode)
**Methodology:** Read ISSUE.md + CONTEXT.md, probed live environment, executed real Scribus + Ghostscript test cases against the actual `Wahl Kreuz im Kreis.eps`, surveyed existing DSL surface, cross-referenced upstream Scribus forum reports.

The findings below are ordered by domain. The **Top 10 Risk Ranking** at the end maps these into PLAN.md priorities. The **Environment Audit** confirms tooling availability.

---

## P-CONTENT-1. The EPS file is just an X — there is no circle

**Risk:** The asset file is named `Wahl Kreuz im Kreis.eps` ("cross in a circle") and the issue body assumes it contains the full Wahlaufruf-Symbol. When converted to PDF with `gs -dEPSCrop` and rendered, **only a yellow X appears**. There is no circle. `%%DocumentProcessColors:` declares only Cyan + Yellow; rendered output is yellow only. A second EPS render at full A4 also shows only the X.
**Likelihood:** HIGH (verified empirically: rendered to PNG via `gs -sDEVICE=pngalpha -r600 -dEPSCrop`)
**Impact:** HIGH — three new templates (Wahlaufruf-Postkarte, Falzflyer, Türanhänger) are all built around this hero asset. If the asset is just a cross, the spec needs to define how the circle is constructed:
  - Option A: Add a circle in the DSL (Polygon shape='ellipse') around the embedded cross
  - Option B: Get a corrected EPS that actually contains the circle
  - Option C: Re-design these templates around a bare cross (no circle)
**Mitigation:**
  - **Phase 1 task:** Visually verify the EPS render and decide which option above to standardize. Add to `templates/_specs/SCHEMA.md` an `eps_strategy.composition` field documenting whether the circle is in the asset, drawn separately, or absent.
  - In Spec for each Wahlkreuz-using template: explicitly diagram the composition (ASCII showing whether circle is around it or not).
  - If Option A: add `WahlkreuzSymbol` block as `Polygon(shape='ellipse', fill='Hellgrün', ...)` + `ImageFrame(...wahlkreuz pdf...)` composed with anchor — not a single image.
**Detection signal:** Visual review (Gate 3) flags "Wahlaufruf without circle" — but only if reviewers know it should have one. Best caught in Spec-Review (Gate 1) by including the rendered asset in the spec for sanity check.

**Source:** Empirical (`gs -dEPSCrop` rendering of `/root/workspace/Wahl Kreuz im Kreis.eps` produced only yellow cross, no circle component)

---

## P-EPS-1. Scribus PDF-in-ImageFrame works only with `scale_type=0` and is low-resolution

**Risk:** D1 specifies EPS → PDF → inline `ImageFrame` with `inline_image_ext="pdf"`. Empirical test shows:
  - With default `scale_type=1, ratio=1` the PDF is rendered **invisibly** (frame appears empty in exported PDF — confirmed by full Scribus render-pipeline test)
  - With `scale_type=0, ratio=1` the PDF renders, but at noticeably lower fidelity than the same PNG path (Scribus internally rasterizes embedded PDFs via Ghostscript at a fixed DPI)
  - Scribus forums document repeatedly that PDF-in-ImageFrame is flaky (PDF v1.7+ may show "missing or corrupt", platform-specific behaviour)
**Likelihood:** HIGH (verified)
**Impact:** HIGH — D1 is the locked decision. If ImageFrame.PDF rendering is unreliable, every Wahlkreuz template fails Gate 3.
**Mitigation:**
  - **Reconsider D1 in Phase 2 spike:** Convert EPS → PNG (high DPI, e.g. 600+) via Ghostscript, embed PNG. Verified path: `gs -sDEVICE=pngalpha -r600 -dEPSCrop` produces a clean 698×755 alpha-PNG (~26KB), which Scribus embeds and renders crisply at print scale. Existing templates already use `inline_image_ext='png'` exclusively.
  - If D1 is retained, every `WahlkreuzSymbol` block must hard-code `scale_type=0` — make this a default constructor argument, not a caller responsibility. Add a unit test that asserts `scale_type=0` on every emitted Wahlkreuz frame.
  - PDF input to Scribus: keep PDF version ≤ 1.5 (some forum reports) — Ghostscript default may produce 1.7. Add `gs -dCompatibilityLevel=1.5`.
  - If we keep PDF: Ghostscript output is RGB by default. Wahlkreuz must end up CMYK in the print PDF — verify Scribus's PDF/X export handles RGB-PDF-in-CMYK-output sanely (or pre-convert to CMYK with `-sColorConversionStrategy=CMYK -dProcessColorModel=/DeviceCMYK`).
**Detection signal:** A "blank frame" or "miniature cross in giant frame" in the rendered preview PNG. Smoke test C1 should explicitly check that the bbox of the Wahlkreuz frame contains non-background pixels above a threshold.

**Sources:**
- Empirical: `/tmp/scribus-pdf-test/test-pdf-st0-out-1.png` shows successful render only with `scale_type=0`
- [Image Frame does not work with PDF files - Scribus Forums](https://forums.scribus.net/index.php?topic=1824.0)
- [Unable to inport PDF into image frame - Scribus Forums](https://forums.scribus.net/index.php?topic=3210.0)

---

## P-EPS-2. Inline `ImageData` requires qCompress format, NOT raw base64

**Risk:** Scribus's SLA `ImageData=` attribute is **qCompress-encoded**: 4-byte big-endian uncompressed-length prefix + zlib-compressed payload, then base64-encoded. CONTEXT.md D1 says "result per `ImageFrame.inline_image_data` (base64) in jedes Template eingebettet" without specifying qCompress wrapping. If a naïve implementation does `base64.b64encode(pdf_bytes)`, **Scribus aborts with `qUncompress: Z_DATA_ERROR`** and the file fails to open (verified empirically).
**Likelihood:** CERTAIN if implementer reads only D1 (the existing DSL `ImageFrame.inline_image_data` is documented as "verbatim round-trip channel" — caller must provide already-qCompressed bytes; this contract is implicit and undocumented in D1)
**Impact:** CRITICAL — every Wahlkreuz template build fails to open in Scribus
**Mitigation:**
  - **Add a helper in builder/blocks.py:** `def encode_inline_image(raw_bytes: bytes) -> str` that does `base64.b64encode(struct.pack('>I', len(raw)) + zlib.compress(raw, 6)).decode('ascii')` — and **use it in `WahlkreuzSymbol`**. Caller never touches qCompress directly.
  - Update CONTEXT.md note + SCHEMA.md to mention this requirement explicitly.
  - Add a unit test that builds a tiny `WahlkreuzSymbol(...)` frame, opens the SLA in Scribus headless, verifies no `qUncompress` error in stderr.
**Detection signal:** Scribus prints `qUncompress: Z_DATA_ERROR: Input data is corrupted` AND `PoDoFo error while reading page count!` to stderr when opening the SLA. Build smoke (C1) must capture stderr and fail the test on these strings.

**Source:** Empirical — `/tmp/scribus-pdf-test/test.sla` with raw base64 fails; with qCompress wrap (`struct.pack('>I', len(pdf)) + zlib.compress(pdf, 6)` then base64) succeeds. Reference implementation: `tools/sla_diff.py:_decode_inline_image_sha` (line 500-515) shows the exact decode steps.

---

## P-EPS-3. Ghostscript EPS→PDF output is non-deterministic (random `/ID`)

**Risk:** D10 says "EPS → PDF via `gs -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite`, deterministic output committed to repo." Tested: two consecutive `gs` runs of the same EPS produce **byte-different PDFs** because Ghostscript writes a random `/ID` element in the trailer. `SOURCE_DATE_EPOCH` fixes `CreationDate`/`ModDate` but **not** `/ID`. The diff is a single 32-character hex string at byte ~199014 of an ~205KB file.
**Likelihood:** CERTAIN (verified — two runs differ at one location)
**Impact:** MEDIUM — the embedded PDF in each template SLA varies bytewise, breaking byte-equivalence of `template.sla` across rebuilds, breaking `tools/check_stale_previews.py` SHA pin (`previews_for_sla:`).
**Mitigation:**
  - Pre-compute the PDF once, commit `shared/assets/derived/wahlkreuz-kreis.pdf` to repo (D10 already says this; **enforce** by gitignoring nothing under `shared/assets/derived/` and adding a CI assertion that the PDF SHA is stable).
  - **OR** post-process the gs output: strip `/ID` with a fixed value (e.g. zero-bytes ID) using a small Python script that rewrites the trailer. Reference: `pikepdf` library has `pdf.trailer['/ID'] = ['', '']` API.
  - **OR** prefer the PNG path (P-EPS-1 mitigation), which removes Ghostscript determinism from the runtime equation entirely — Ghostscript runs once at asset-prep time, PNG bytes are stable.
  - **Safer default:** commit the derived asset (PNG or PDF) as the source of truth; provide `tools/eps_to_*.py` only as a **regenerate** tool that's run when the EPS changes, not at every build.
**Detection signal:** `git diff` after a clean rebuild shows changed bytes in `template.sla` for Wahlkreuz-using templates. CI's `tools/sla_diff.py` round-trip will fail.

**Source:** Empirical — `gs -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite` of `/tmp/wahl.eps` twice produces hashes `a248087...` and `3d05559...`; `cmp -l` shows diff at byte 199014 (the `/ID` field). Adding `SOURCE_DATE_EPOCH` does not fix this.

---

## P-EPS-4. Embedded PDF size cascades into SLA filesize blow-up

**Risk:** Per-template SLA filesize budget. Current Postkarte SLA is 191KB; Plakat is 235KB; Zeitung is 570KB. The Wahlkreuz PDF is ~12KB raw → ~14KB qCompress-base64 (in our test) — small. **However**, three templates × inline-embedding × multiple pages with the symbol could approach 50-100KB/template extra. Trivial today, but if asset list grows (other Grünen symbols, photos), easy to hit 5MB/SLA territory where Scribus performance degrades on save and editing.
**Likelihood:** LOW (with current asset)
**Impact:** LOW now, MEDIUM if more inline assets are added later
**Mitigation:**
  - Set a soft cap in `tools/check_ci.py`: warn if a single template SLA exceeds 1MB.
  - Don't embed the same asset multiple times per page if it appears multiple times — share via a single `ImageFrame` (Scribus supports this via `Pagenumber=0` reference but this DSL doesn't expose that pattern).
  - As a long-term hedge: don't embed in templates the user opens for casual editing. The DSL output is large *and* the user clicking Save will preserve embedding. Document this constraint.
**Detection signal:** SLA size grows >25% relative to baseline after the new templates land. `bin/check-stale-previews` may show timing degradation.

---

## P-EPS-5. EPS uses fonts (system or embedded?) — unverified

**Risk:** Adobe Illustrator EPS may reference fonts not on the system. `Wahl Kreuz im Kreis.eps` is mostly outline/path-based but the EPS prologue references `Adobe_AGM_Image` procset — typical Illustrator. The EPS uses Cyan/Yellow process colors but is otherwise "image" not text. Spot-check confirms the rendering succeeds without font warnings.
**Likelihood:** LOW for this asset
**Impact:** MEDIUM (would fail to convert if real fonts referenced)
**Mitigation:**
  - As part of `tools/eps_to_*.py`, do a one-time check: `gs ... 2>&1 | grep -i "missing font"` — fail the asset prep if any.
  - **Best practice:** in Illustrator, "Convert to Outlines" before EPS export. If the asset was generated by a non-technical user, instruct them in `shared/assets/README.md` to do this.
**Detection signal:** Ghostscript output contains "Substituting font" or "Can't find (or can't open) font file".

---

## P-CONFIG-1. Color space mismatch: EPS RGB-rendered → CMYK print expected

**Risk:** Ghostscript's default `pdfwrite` produces **RGB** PDFs. The Wahlkreuz templates target print → must end up in CMYK in the final exported PDF. Scribus *can* convert RGB-content-in-CMYK-document during export, but the conversion path goes through ICC profiles that may shift the yellow's chroma. If the EPS's yellow was originally a Pantone-yellow-equivalent CMYK `(0,0,100,0)` but goes through RGB intermediate → CMYK conversion, you can lose 5-10% saturation and shift to `(2,3,95,0)`-ish.
**Likelihood:** MEDIUM (especially given the EPS already uses spot-color machinery internally)
**Impact:** MEDIUM (print-quality degradation, not a functional failure)
**Mitigation:**
  - Convert EPS → PDF with CMYK strategy: `gs -sColorConversionStrategy=CMYK -dProcessColorModel=/DeviceCMYK ...`
  - Verify the rendered Wahlkreuz yellow matches the brand `Gelb` color (CMYK `0/0/100/0` per `shared/ci.yml`). If not, swap to PNG path with explicit CMYK colorspace.
  - **OR** manually replace the yellow in the embedded asset by re-coloring via DSL (only feasible with PNG and an alpha-mask — easier with vector paths via SVG-to-Polygon, which is in the deferred set).
**Detection signal:** `tools/check_ci.py` color drift on the Wahlkreuz frame. Or visual review (Gate 3) flagging "yellow looks slightly off" in side-by-side.

---

## P-DSL-1. DSL `add_layer` API exists but spot-color-on-layer integration unverified

**Risk:** D4 mandates Falz/Stanz spot colors on dedicated layers. The DSL has:
  - `Document(layers=[DocumentLayer(...)])` for layer override (verified — used in Postkarte template)
  - `doc.add_color(name, cmyk=..., spot=True, register=False)` for spot colors (verified — `BrandColor.spot` field exists)
  - `Polygon(custom_path=..., fill=<spot_color_name>, line_color=<spot_color_name>)` for emitting paths in spot color (untested)

But **no existing test exercises**: spot color used by a Polygon's stroke, on a non-default layer, with `printable=False, exportable=True`. The combination "stanzkontur path on its own non-printing layer" is a new code path.
**Likelihood:** MEDIUM
**Impact:** HIGH if it doesn't work — Türanhänger can't be production-ready without functioning Stanzkontur
**Mitigation:**
  - **Phase 2 spike:** add a unit test in `test_blocks.py` that builds a 1-page SLA with: spot color `Stanzkontur` registered, layer "Stanze" with `printable=False, exportable=True`, a `Polygon` with custom rectangular path on that layer, line_color=Stanzkontur. Then assert `<COLOR Spot="1">` is emitted, `<LAYERS DRUCKEN="0">` is emitted, and the Polygon's `LAYER=` matches.
  - Test that `xvfb-run scribus --no-gui` opens the result without warnings.
  - Test that exporting to PDF shows the Stanzkontur path **as a spot color separation** (verifiable via `pdfinfo -box` or `gs -sDEVICE=inkcov`).
**Detection signal:** Spot color absent from `inkcov` output of exported PDF; Scribus on open shows "Color Stanzkontur not found" or "Layer attribute mismatch" in stderr.

---

## P-DSL-2. New blocks risk DSL API drift vs Issue #9's parallel changes

**Risk:** Issue #9 (post-migration-dsl-hygiene) is open and modifies:
  - `tools/sla_lib/builder/blocks.py` — extends `Impressum` block with `prefix_text`, `rotation_deg`, heading-schema (3 new params)
  - `tools/sla_lib/tests/test_blocks.py` — new tests
  - `tools/sla_diff.py` — `_LEGACY_LAYER_NAMES` audit
  - `shared/ci-defaults.yml` — possibly hoisted attrs
  - `tools/sla_lib/tests/test_sla_to_dsl.py` — `ZeitungConverterFreshRun`

This issue (#10) adds new blocks to the SAME `blocks.py`, new tests in `test_blocks.py`, and may need to extend `_LEGACY_LAYER_NAMES` if the new templates use new layer names like "Falz" / "Stanze" that need allowlisting in the round-trip diff.
**Likelihood:** HIGH for merge conflict
**Impact:** MEDIUM (resolved by rebase; loss of 30-60min)
**Mitigation:**
  - **Coordination strategy:** issue #9 is smaller and should land first. Plan the work order accordingly (reflect in plan): wait for #9 PR merge before opening #10 PR, OR rebase #10 onto #9's branch as soon as #9 lands.
  - When adding new blocks, use clearly-distinct line ranges (append to bottom of `blocks.py`) rather than inserting in the middle, to ease rebase.
  - For `_LEGACY_LAYER_NAMES` audit overlap: document the new layer names this issue adds (Falz, Stanze, etc.) and add them to the constant in a separate commit on top of #9's audit.
**Detection signal:** `git rebase` shows conflicts in `blocks.py` line ranges or `test_blocks.py`.

---

## P-DSL-3. `flow_text_around` semantics on new layers may surprise the user

**Risk:** New layers (Falz, Stanze) default to `flow=True` per DSL `DocumentLayer` dataclass, meaning text frames flow around content on lower layers. If a Stanzkontur path on layer 5 is below a text frame on layer 4, the text may unintentionally wrap around the cutout outline.
**Likelihood:** MEDIUM (only manifests if user adds long text near cutout)
**Impact:** LOW-MEDIUM (visual artifact, easy fix once spotted)
**Mitigation:**
  - Set `flow=False` on Falz and Stanze layers. Document in SCHEMA.md.
  - Spec for Türanhänger should explicitly diagram text-frame layout to keep clear of the cutout zone.
**Detection signal:** Text in the Türanhänger preview wraps in unexpected places. Catch via Gate 3 visual review.

---

## P-DSL-4. Layer ordering matters for print

**Risk:** Scribus emits layers in the order they're declared in `<LAYERS>`. Print order is bottom-up. If `Stanze` layer is declared BEFORE `Hintergrund`, the cut-line would print under the background.
**Likelihood:** LOW (DSL preserves declared order)
**Impact:** HIGH (would render templates unusable for print)
**Mitigation:**
  - Document the canonical layer stack in SCHEMA.md: `[Hintergrund, Bilder, Text, Falz, Stanze, Hilfslinien]` — Stanze on top so it's always visible to the print operator.
  - Unit test: build a Türanhänger and assert `LAYERS[Stanze].LEVEL > LAYERS[Hintergrund].LEVEL`.
**Detection signal:** Test failure on layer-level assertion. Otherwise visible only in print-shop output.

---

## P-PRINT-1. Print-shop spot-color naming convention varies

**Risk:** D4 names the cut-color `Stanzkontur` (German). Adobe's convention is `CutContour`. Some print shops (e.g. Resch) accept either; some (e.g. Druckerei Bösmüller) require `CutContour` capitalized exactly. ÖGB-Druckerei (Vienna, common Grünen vendor) accepts German names per their style guide.
**Likelihood:** MEDIUM (varies by vendor)
**Impact:** MEDIUM (template might be rejected at print-shop and require relabeling)
**Mitigation:**
  - In `Türanhänger` spec, list 2-3 acceptable naming variants in a "Druckhinweise" section: `Stanzkontur` (default), `CutContour` (English/Adobe), `Stanze`.
  - Make the spot-color name a `meta.yml` parameter so a Bezirksgruppe can re-label without editing build.py.
  - Document that German naming is acceptable for AT print shops; English for international.
**Detection signal:** Print-shop bounces a quote-request asking "what's Stanzkontur?". Cannot be auto-detected.

---

## P-PRINT-2. Falz markings: positions must align with paper sub-sizes exactly

**Risk:** `kandidat-falzflyer-din-lang` is A4 quer (297×210 mm) folded into 3 panels of 99×210 mm. Print shops fold at exactly 99 and 198 mm. If the spec says "Falz at 99mm" but build.py emits `FoldLine(start_mm=99.0)` and the Document's coordinate origin includes 3mm bleed, the actual position becomes 102mm in the PDF. Off by 3mm = unusable.
**Likelihood:** MEDIUM (coordinate origin confusion)
**Impact:** HIGH (template misaligned with print expectation)
**Mitigation:**
  - Standardize on coordinate origin = trim corner (NOT bleed corner). `FoldLine(at_mm=99.0)` in spec means 99mm from trim-edge.
  - Validate in CI: `tools/check_ci.py` reads the spec's `dimensions.fold_lines` and asserts the actual emitted Polygon path coordinate matches (within 0.1mm tolerance).
  - For tent-card: the fold is at the **center** (148.5 mm for A4 quer halved). Whether that's the long or short axis matters; spec must show in ASCII.
**Detection signal:** Fold-line position visible in render PNG is offset from the spec ASCII sketch. Manual reviewer comparison.

---

## P-PRINT-3. Türanhänger: the keyhole cutout has a standard, but multiple variants exist

**Risk:** Türklinken-Loch (door-handle hole) standard sizes:
  - Round: 30 mm diameter (typical for European door handles)
  - Slot/keyhole shape: 40×20 mm with rounded ends (some printers)
  - Position: 25-30 mm from top edge, centered horizontally
  Different print shops have different defaults. The cutout shape is a `DieCut` Polygon path.
**Likelihood:** MEDIUM
**Impact:** MEDIUM (door hanger doesn't fit on actual door handles)
**Mitigation:**
  - Spec: define a "standard variant" (recommend 30mm round, 25mm from top) with explicit ASCII diagram.
  - DSL: `DoorHangerCutout(shape='round'|'keyhole', diameter_mm=30, top_offset_mm=25)` with sensible defaults but parametric.
  - Spec lists alternative configurations + when to use them.
**Detection signal:** Template has placeholder cutout that doesn't fit a real door handle; only catchable in physical print test or by knowing the standard.

---

## P-PRINT-4. Tent-card: fold gives bottom-edge contact with table — small bleed risk

**Risk:** A5 tent-card folded from A4 quer: when standing as a tent on a table, the bottom edge (the un-folded edge) sits on the table. Standard 3mm bleed normally protects against trim cuts, but a tent's bottom edge is not trimmed — it's the original paper edge. Print expectations: leave 3mm safety from bottom.
**Likelihood:** MEDIUM
**Impact:** LOW (visual only, design space)
**Mitigation:**
  - Spec for `infostand-tent-card-a5-quer`: explicitly mark "bottom-3mm = table-contact, do not place text".
  - DSL: TextFrames in the bottom-most slot have `y_min = h - 3 - text_height`.
**Detection signal:** Reviewer notes "text touches table-bottom in tent rendering". Hard to spot without 3D-tent simulation.

---

## P-PRINT-5. A6 quer Wahlaufruf-Postkarte: "wählen!" must be readable at postcard distance

**Risk:** A6 quer = 148×105 mm. Hand-held distance ~30 cm. Headline "Am 28. September wählen!" needs to be readable. Industry rules: minimum 12pt for body, 18pt+ for headlines. If the postcard's design crams in too many slots, the headline shrinks below readable.
**Likelihood:** MEDIUM
**Impact:** HIGH (poor visual quality = fails Gate 3 "mindestens auf Augenhöhe")
**Mitigation:**
  - Spec: minimum headline fontsize for A6 quer = 22pt (matches Postkarte Hochformat's 27pt scaled to width ratio).
  - Don't put more than 5-6 slots on a 148×105mm page.
  - In Visual-QA Gate 3, explicitly compare headline size against existing Postkarte.
**Detection signal:** Vision review or human review notes "headline looks small". Catchable in Gate 1 spec review (slot table sizing) and Gate 3.

---

## P-PRINT-6. Impressum requirement: every printed Grünen artifact in AT needs Impressum

**Risk:** Austrian media law (Mediengesetz §24) requires Impressum on every distributed printed artifact: Medieninhaber, Verleger, Hersteller. Failure = up to €2,180 fine. If a template ships without Impressum slot, the user might forget to add one.
**Likelihood:** HIGH (these are templates for distribution material)
**Impact:** MEDIUM (legal, recoverable)
**Mitigation:**
  - All 5 new specs MUST include an `impressum` slot (mandatory, can't be empty), with placeholder text matching `shared/ci.yml` brand identity.
  - SCHEMA.md: list `impressum` as a required slot for any template with `audience` not = "internal".
  - `tools/check_ci.py` (or new `tools/spec_check.py`): fails if a public-facing template's slot list doesn't include `impressum` (or `impressum_*`).
**Detection signal:** Spec validation; spec-review (Gate 1).

---

## P-PRINT-7. Wahlkreuz misuse: "kreuze hier!" instructions = Winkelschreiberei

**Risk:** Austrian electoral law forbids "Anleitung zur Stimmabgabe" specifically; templates that embed a Wahlkreuz with text "Kreuze hier!" or "Mach dein X bei den Grünen!" can be challenged in court (Wahlanfechtung). Generic "Grün wählen!" or "Am 28. September Grüne wählen" is safe (= statement of preference).
**Likelihood:** LOW for this issue (placeholder text, real campaigns review later)
**Impact:** HIGH (legal, costly)
**Mitigation:**
  - Specs: example placeholder text MUST be generic ("Wähle Grün am 28. September"). Add a comment in the spec: "Achtung: keine Anleitung zur Stimmabgabe; siehe NRWO §53".
  - Document this in SCHEMA.md as a `legal_constraint` field for political-action templates.
**Detection signal:** Reviewer in Gate 1 must catch problematic placeholder text. Add to Gate-1 prompt: "Are placeholder texts legally safe (no Wahlanleitung)?"

---

## P-VISION-1. Multi-model vision review cost runaway

**Risk:** D5 + D6 + D7: 5 templates × 3 models × ~3 iterations × 2 images (template + composite) = 90 model calls/full-pass. With Claude Vision @ ~$0.005/img, GPT-4V @ ~$0.01/img, Gemini @ ~$0.0007/img, conservatively ~$1/full-pass total. Cheap. But re-runs (per CI push) blow up. CONTEXT.md `Kosten beherrschbar durch Bild-Downscaling` is correct; main risk is uncontrolled triggering.
**Likelihood:** MEDIUM (only if pipeline runs on every push)
**Impact:** LOW (cost) / HIGH (developer feedback loop slowness)
**Mitigation:**
  - Visual review only on `workflow_dispatch` or label `visual-qa-please`, NOT on every push.
  - Cache results by composite-image-SHA + prompt-SHA. Don't re-call models if both inputs identical to a prior run.
  - Cap iterations at 3 (D6 already says this).
**Detection signal:** `gh run list` shows visual-qa workflow consuming 10+ minutes per merge attempt; check API spend dashboard.

---

## P-VISION-2. Vision API auth state in this container

**Risk:** Verified probes:
  - **codex CLI** (`/root/.npm-global/bin/codex` v0.128.0): logged in via ChatGPT — `codex login status` returns "Logged in using ChatGPT". OAuth-based, no env var needed.
  - **gemini CLI** (v0.41.2): OAuth credentials in `/root/.gemini/oauth_creds.json`. **Token currently expired** (`expiry_date < now`); refresh_token present so it should auto-refresh on next call. Untested in worktree.
  - **Claude Vision** (this agent): native, no auth call needed.
  - **No env vars** for `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, or `GEMINI_API_KEY` in current shell. Pure-CLI-OAuth setup.
  - **CI runner (GitHub Actions)** does NOT inherit local OAuth; if visual review runs in CI, secrets must be configured at repo level, OR visual review only runs locally (developer's machine). Recommend the latter — Gate 3 is a manual ship-readiness step.
**Likelihood:** HIGH on CI (no creds)
**Impact:** HIGH (CI fails with auth error)
**Mitigation:**
  - Decide explicitly: Gate 3 is local-only. CI runs build + smoke (C1) but skips C2 (`tools/visual_review.py`).
  - `tools/visual_review.py` checks for either env var OR CLI auth state at startup; clear error message if missing.
  - Document in `tools/visual_review/README.md`: "requires local OAuth via `codex login` and `gemini` first run".
**Detection signal:** CI fails with "401 Unauthorized" or "OAuth token expired". `gemini --prompt "test"` returns auth error.

---

## P-VISION-3. Vision-model image-format quirks

**Risk:** Claude Vision, GPT-4V, Gemini accept different image formats:
  - All three accept PNG, JPEG.
  - Claude Vision: hard cap 5 MB per image, 8000×8000 max. Auto-resizes.
  - GPT-4V: hard cap 20 MB, 2048×2048 best (auto-downscales).
  - Gemini: 4 MB (per call), 2048×2048 best.
  - Alpha channels: PNG with alpha → some models render alpha as black background (interferes with white-background composite). Best: flatten to opaque RGB before send.
  - EXIF rotation: Pillow's default `Image.open()` doesn't rotate per EXIF; some models DO. Mismatch = wrong orientation in review.
**Likelihood:** MEDIUM
**Impact:** MEDIUM (false positives from models)
**Mitigation:**
  - `tools/visual_review.py` standardizes: PNG, max 1024 px long edge (D7), opaque white background, no EXIF, sRGB only.
  - Reject animated PNGs / paletted PNGs.
  - For composite: render templates onto a 4×2 grid with explicit labels above each tile so models know which is which.
**Detection signal:** Models comment on "rotation" or "transparency" issues that aren't in the source. Easy to QA the input PNG manually.

---

## P-VISION-4. Hallucinated findings & disagreement spirals

**Risk:** Vision models often invent issues:
  - "Text overlaps with image" when it doesn't
  - "Color seems off" when colors match exactly
  - "Headline is too small" with no quantitative basis
  Fix-attempt may introduce real problems, leading to "iter 2" finding new issues that "iter 3" can't reconcile across 3 models.
**Likelihood:** HIGH (well-documented vision-model failure mode)
**Impact:** MEDIUM (wastes iteration budget; blocks merge)
**Mitigation:**
  - Prompt-template requires models to **cite specific coordinates / regions** for findings: "There is overlap at approximately x=120mm y=80mm" instead of "there is overlap somewhere". Easy to verify automatically with bounding-box checks.
  - Findings classified as "blocking" only if 2/3 models converge on the same finding, even when D6 requires 3/3 final approval. Single-model "blocking" finding becomes "advisory" only.
  - Keep a `known-false-positives.yml` per template — if iter N finds X and reviewer dismisses it, iter N+1 doesn't re-flag it.
**Detection signal:** Same finding bounces back-and-forth across iterations 1, 2, 3 with different fixes each time.

---

## P-VISION-5. Stylistic biases in vision models

**Risk:** Empirical bias documented:
  - GPT-4V tends to favor centered, symmetric layouts; flags asymmetry as "imbalanced".
  - Gemini favors flat, minimal aesthetic; flags rich visual hierarchies as "busy".
  - Claude Vision is more neutral but skews toward "professional" / safe.
  Grünen brand has a deliberately **asymmetric, vibrant, multi-color** aesthetic (Hellgrün/Dunkelgrün/Gelb/Magenta block layouts in Postkarte). Vision-model "consensus" may bias toward generic / flat / symmetric, losing brand personality.
**Likelihood:** HIGH
**Impact:** MEDIUM (drives toward generic; defeats issue's "brand auf Augenhöhe" goal)
**Mitigation:**
  - Prompt-template Gate 3 explicitly references **the existing 3 templates as the brand baseline**. Question framed as "is this consistent with these 3 reference images?" not "is this well-designed?". Brand-relative not absolute.
  - Reject "this looks generic / professional" as a non-finding (it's not actionable to grünen brand).
  - Calibrate: include Postkarte/Plakat/Zeitung in the side-by-side composite so models see the brand visually, not just in name.
**Detection signal:** Findings consistently push toward "less color", "more centered", "remove magenta störer" — these are bias signals.

---

## P-VISION-6. Model-version drift / pin

**Risk:** Models update silently:
  - Claude: "Opus 4.7" today is `claude-opus-4-7` (this agent's model name); identifier may change.
  - Codex CLI: routes to OpenAI's GPT-4V or successor; CLI accepts `-m <model>` but default is implicit.
  - Gemini: routes to Gemini-2.5 Pro Vision today (gemini CLI default); may bump to 3.x silently.
  When models update, prior visual-review reports become non-reproducible — Gate 3's "this passed last week" is meaningless if today's model disagrees.
**Likelihood:** HIGH (over time)
**Impact:** MEDIUM (audit-trail issue)
**Mitigation:**
  - `tools/visual_review.py` records the model identifier (whatever the CLI returns in stdout/JSON) into each report.
  - Pin where possible: `gemini -m gemini-2.5-flash` explicitly; `codex -m o4-mini-2025-XX`.
  - Reports include the date for clarity.
**Detection signal:** Model identifier line in review reports varies between identical re-runs.

---

## P-CI-1. CI runner image differs from local container

**Risk:** Local container (Dockerfile.claude) installs Scribus 1.6.3 from Debian trixie. CI uses Ubuntu Latest + Scribus 1.6.5 AppImage. Both are 1.6.x SLA-compatible but rendering subtle differences exist:
  - Existing `tools/check_stale_previews.py` only validates that committed PNG matches committed SLA-rendered PNG (CI doesn't render — it checks pre-rendered).
  - The new templates' baseline PNGs need to be committed; `bin/check-stale-previews` currently drives this.
  - If the local-rendered PNGs use Scribus 1.6.3 but a future user runs 1.6.5, the visual diff in Gate 3 would re-flag.
**Likelihood:** LOW (current pipeline already handles this — local renders, commits, CI validates)
**Impact:** MEDIUM (extra-iteration friction)
**Mitigation:**
  - All preview PNGs rendered locally on Dockerfile.claude (Scribus 1.6.3); commit and pin.
  - `bin/check-stale-previews` already validates SHA of SLA matches PNG.
  - For visual review: also render locally (1.6.3); CI doesn't re-render.
**Detection signal:** `bin/check-stale-previews` in CI fails on PR. Already handled.

---

## P-CI-2. CI Action's `pages.yml` lacks Pillow / vision-review tooling

**Risk:** Current `.github/workflows/pages.yml` installs only `xvfb poppler-utils ghostscript imagemagick python3-lxml python3-yaml`. No Pillow. No `codex`/`gemini` CLIs. The CI cannot run `tools/visual_review.py` at all today.
**Likelihood:** CERTAIN (verified in workflow YAML)
**Impact:** LOW (visual review is local-only — and that's the right call per P-VISION-2)
**Mitigation:**
  - **Don't add vision review to CI.** Make it a manual `workflow_dispatch` separate workflow `vision-review.yml` that's optional.
  - For composite-grid generation (Pillow): if it's used in the gallery build, install Pillow there. But for visual-review composite, it can be local-only.
  - `make build` and `make check` (no Makefile exists today — issue may need to add one) cover the always-on CI path.
**Detection signal:** CI never runs visual review; Gate 3 is local-only. Document this clearly.

---

## P-CI-3. No Makefile exists yet — `make build`, `make check` referenced but missing

**Risk:** Issue body Constraint says "make check und make build grün". Repository has no Makefile (`ls Makefile` → not found). The new spec/build/check pipeline either needs a Makefile or `bin/` shell wrappers (current convention — `bin/check-stale-previews`, `bin/validate`).
**Likelihood:** CERTAIN
**Impact:** LOW (small infra fix)
**Mitigation:**
  - Either add a thin Makefile with `make build`, `make check`, `make smoke`, `make visual-review` targets dispatching to existing scripts. OR adjust the issue's language to use `bin/` wrappers.
  - Recommend Makefile for discoverability — it's a common touchpoint and easier than memorizing 5 `bin/*` scripts.
**Detection signal:** PR review: "the issue references `make build` but there's no Makefile."

---

## P-CI-4. Round-trip diff regression risk for new layers / spot colors

**Risk:** `tools/sla_diff.py` round-trip for the 3 existing templates must remain green per acceptance criteria. The diff has `_LEGACY_LAYER_NAMES` allowlist + per-template overrides. Adding global emit of new spot colors (Falz, Stanzkontur) to `shared/ci.yml` means **every** template that uses `Brand.gruene_noe()` will emit those colors → existing templates that didn't have them before would now have extras → diff fails.
**Likelihood:** HIGH if Falz/Stanzkontur added to `shared/ci.yml`
**Impact:** HIGH (regression of acceptance criteria)
**Mitigation:**
  - **Add new spot colors to `shared/ci.yml`** (single source of truth for brand identity)
  - Update `_brand_additive` filter in `sla_diff` to allowlist these new spot colors as "brand-extra" (i.e., diff won't flag them as missing in the original).
  - Update existing templates' `meta.yml.ci_overrides.non_ci_colors` if needed (unlikely — original SLAs don't use Falz/Stanzkontur, the diff just won't flag their absence in the original).
  - **OR:** Make new spot colors document-local (`doc.add_color('Falz', spot=True, cmyk=(100,0,0,0))`) — only emitted in templates that use them. No CI drift.
  - Decision: document-local is safer and matches existing pattern (`doc.add_color('Green')` in Postkarte). Recommend document-local.
**Detection signal:** `python3 tools/sla_diff.py originals/<template>.sla templates/<template>/template.sla` shows new color drift.

---

## P-CI-5. New layer names in `_LEGACY_LAYER_NAMES`

**Risk:** Same logic as P-CI-4 but for layers. If `shared/ci.yml.layers` adds `Falz`, `Stanze`, every existing template now emits those layers → originals don't have them → diff fails.
**Likelihood:** HIGH if added to shared
**Impact:** HIGH
**Mitigation:**
  - Use `Document(layers=[...])` per-template override (already supported, used by Postkarte). Falz/Stanze layers added only in templates that need them.
  - Don't extend `shared/ci.yml.layers` defaults.
**Detection signal:** Same as P-CI-4.

---

## P-DETERMINISM-1. SLA byte-equivalence post-build

**Risk:** Rebuilding Postkarte/Plakat/Zeitung must produce byte-identical SLAs (existing acceptance criterion). Adding new code paths to blocks.py (e.g., new `_emit_inline_pdf` helper) might accidentally change the order of attribute emission or the rounding of coordinates for existing templates.
**Likelihood:** MEDIUM
**Impact:** HIGH (round-trip regression = blocking)
**Mitigation:**
  - Run `python3 tools/sla_diff.py` for each existing template after every block-library change in Phase 2.
  - Add a CI check: `bin/check-stale-previews` already does this; run also `tools/sla_diff.py` against the original.
  - When adding new methods, append (don't insert in the middle of existing class definitions).
**Detection signal:** Direct test failure.

---

## P-SPEC-1. Spec drift between specs and implementations

**Risk:** D3 says "Spec ist Vertrag — gelockt nach Gate 1". But humans (and LLMs) routinely drift: spec says "headline at y=12mm", build.py implements y=11.7mm, Gate 2 reviewer doesn't notice. By Gate 3, the actual rendered output is several mm off-spec on multiple dimensions.
**Likelihood:** HIGH (pattern in any spec-driven workflow)
**Impact:** MEDIUM (defeats the purpose of D3)
**Mitigation:**
  - **Mandatory: build a `tools/spec_check.py` that mechanically diffs spec slot positions vs. emitted SLA frame positions (within 0.1mm tolerance).** Not optional. CI must run this and fail on drift.
  - Spec→build.py mapping is mostly mechanical: each slot has `x_mm, y_mm, w_mm, h_mm, anname`. The DSL emits PAGEOBJECT XPOS, YPOS, WIDTH, HEIGHT, ANNAME. Direct compare.
  - Where intentional drift exists (e.g., Scribus baseline grid forces slight repositioning), spec MUST be updated with a `spec_implementation_note: "y adjusted to 11.7mm to align with baseline grid"` and the diff tool reads this exception.
**Detection signal:** Drift between spec yaml `slots:` and meta.yml `slots:` and SLA `<PAGEOBJECT ANNAME=>`.

---

## P-SPEC-2. Spec language: German prose vs English keys

**Risk:** Specs mix German prose (audience description, layout philosophy, print notes) with the structured YAML which would benefit from English snake_case keys (matches sla_lib DSL). Mixing freely creates inconsistency: one spec uses `slots: {kandidat_portrait: ...}`, another uses `slots: {portrait_kandidat: ...}`, a third uses German `kandidatenfoto`.
**Likelihood:** MEDIUM
**Impact:** LOW (cosmetic / authoring friction)
**Mitigation:**
  - SCHEMA.md prescribes: prose = German (audience), keys = English snake_case (machine).
  - JSON Schema validation (already exists in `shared/template-spec.schema.yaml`) catches typos and bad key names.
  - Slot ANNAMEs (visible to users in Scribus): German is fine and matches existing convention (e.g., "Headline-vorne" in postkarte).
**Detection signal:** Schema validation fails; or reviewer notes inconsistency.

---

## P-SPEC-3. Slot count creep ("12 in spec, 13 in build")

**Risk:** Spec lists 12 slots; build.py adds an unstated 13th for visual balance (e.g., a hairline divider, a hidden anchor frame). Drift detection fires.
**Likelihood:** MEDIUM
**Impact:** LOW (drift caught by tooling)
**Mitigation:**
  - SCHEMA.md: "every emitted PAGEOBJECT with ANNAME must appear in spec slots OR be marked with `dsl_internal: true` ANNAME prefix". Then `spec_check.py` ignores `internal:*`.
  - Discourage "balance" frames; if needed, add to spec.
**Detection signal:** spec_check.py reports extra ANNAMEs.

---

## P-A6QUER-1. Wahlaufruf-Postkarte: A6 quer is small for grid layouts

**Risk:** A6 quer = 148×105 mm. Issue lists it as "Symbol-zentriert, Info-Grid hinten". Front (Symbol-zentriert): generous space. Back (Info-Grid): 148×105 mm minus 6mm bleed = 142×99 mm usable; 4-cell grid means each cell is ~70×48 mm — tight for headline + 2 lines body + Impressum.
**Likelihood:** MEDIUM (design pressure on info-grid back)
**Impact:** MEDIUM (visual quality — will Gate 3 pass?)
**Mitigation:**
  - Spec: explicitly bound info-grid to 2×2 (not 3×2 or 2×3) cells.
  - Use Gotham Narrow Book at 9pt minimum for body, 14pt+ for cell-headlines.
  - Test: build the back side with realistic 4-cell content (e.g., 4 candidates), render, eye-check.
**Detection signal:** Gate 3 vision review on back side flags "tight" / "cramped".

---

## P-FALZ-1. Falzflyer DIN-lang panels: print-shop expectation

**Risk:** A4 quer 3-fold has 6 panels (3 front + 3 back). Falz layout patterns:
  - **Wickelfalz** (roll fold): outer panel folds inside, inner panel folds inside → outer-leftmost = "Cover", reads naturally.
  - **Zickzack-Falz** (Z-fold / accordion): each panel alternates fold direction.
  - **Altarfalz** (gate fold): two outer panels fold inward to meet center.
  Most common for political flyers: Wickelfalz. The spec MUST specify which type, AND which panel is the cover; otherwise the print shop guesses.
**Likelihood:** MEDIUM
**Impact:** MEDIUM (mis-folded flyer = unreadable narrative)
**Mitigation:**
  - Spec: declare `fold_type: wickelfalz | zickzack | altar` explicitly. Default to `wickelfalz`.
  - ASCII layout shows the panel order in the FLAT layout AND the assembled-fold-state — show both views.
  - DSL: `FoldedPanel(panel_index=0..5, fold_type='wickelfalz', cover_panel=0)` validates panel mathematics.
**Detection signal:** Gate-1 reviewer asks "which panel is the cover?". Gate 3 visual flags wrong panel sequence.

---

## P-A3-1. A3 Themen-Plakat: column-gutter math

**Risk:** A3 quer = 420×297 mm. Argumentation layout (1 thesis → 3 evidence). 3-column grid:
  - Column width = (420 - margins(2×15) - 2×gutter(8)) / 3 = (420 - 30 - 16) / 3 = 124.7 mm/column
  - Real Scribus column-gap default is 11pt (~3.9mm) — different from typographer's 8mm. If spec says `gutter: 8mm` but build.py uses Scribus default 11pt, the math breaks.
**Likelihood:** MEDIUM
**Impact:** MEDIUM (column boundaries off, text crowds)
**Mitigation:**
  - Spec: gutter explicit in mm, NOT typographer's "ems" or "pt".
  - DSL: `ColumnTextStory(gutter_mm=8)` translates to pt internally; never use Scribus default.
**Detection signal:** Visual review notices uneven column widths.

---

## P-COMPOSITE-1. Side-by-side composite distortion

**Risk:** D7: 4×2 grid composite of 8 templates. Templates have radically different aspect ratios:
  - A6 portrait (0.71:1)
  - A1 portrait (0.71:1)
  - A4 newspaper (0.71:1)
  - A6 quer (1.41:1)
  - A4 quer 3-fold (1.41:1, but 3 panels = 4.24:1 if shown unfolded)
  - A3 quer (1.41:1)
  - 105×250 mm (0.42:1) — door hanger
  - A5 quer (1.41:1)
  Tiling these into a uniform-cell grid distorts the door hanger heavily and may not preserve readability. Vision models compare side-by-side; if the door-hanger thumbnail is too small, models mis-flag.
**Likelihood:** MEDIUM
**Impact:** MEDIUM (vision review noise)
**Mitigation:**
  - Composite uses **uniform area, varying aspect** — each tile gets ~equal pixels but its aspect ratio is preserved (whitespace pads to grid cell).
  - Pillow ImageOps.contain() does this: `tile.thumbnail((cell_w, cell_h), Image.LANCZOS)` keeps aspect.
  - Each tile labelled with template name and trim dimension below.
  - For Falzflyer: show flat OR composite as 2 sub-tiles (cover + interior).
**Detection signal:** Vision review comments "this looks tiny" or "this is squished".

---

## P-COMPOSITE-2. Pillow not in current Python env (or CI workflow)

**Risk:** Pillow not pre-installed (verified: `import PIL` raises ModuleNotFoundError). Installable via `uv pip install --system --break-system-packages pillow` (took ~5 sec; produces Pillow 12.2.0). Not in `.github/workflows/pages.yml`. Not in Dockerfile.claude.
**Likelihood:** CERTAIN
**Impact:** LOW (small install)
**Mitigation:**
  - Add `python3-pil` (or `pillow` via pip) to Dockerfile.claude. Add to CI `apt-get install`. Or `uv pip install pillow` step.
  - Alternative: use ImageMagick `montage` for composite (already installed).
**Detection signal:** ImportError at first run of `tools/visual_review.py`.

---

## P-RENDER-1. PNG render artifacts at low DPI

**Risk:** Default `preview_dpi: 100` in existing templates. D7 says "primäres Render: 200 DPI". Mixing means some templates render at 100 dpi, some at 200, side-by-side comparison shows quality discrepancy. A 100-dpi A1 (594×841 mm) is 2340×3308 px → big, but 100-dpi A6 (105×148 mm) is 413×583 px → small, font hinting visible.
**Likelihood:** HIGH if not standardized
**Impact:** MEDIUM (visual artifacts in review)
**Mitigation:**
  - Standardize on `preview_dpi: 150` for all templates (good for ≤A1, file sizes manageable).
  - For Visual-QA composite: re-render at 200 dpi for the composite generation, but display as 1024-px-long-edge tiles.
  - Document in render-fidelity.md.
**Detection signal:** Vision models comment on "low-quality rendering" / "pixelated text".

---

## P-RENDER-2. AA / hinting / color profile differences in render

**Risk:** Scribus PDF export uses internal anti-aliasing & ICC profiles. `pdftoppm` rasterization uses Cairo's AA. The two AA pipelines produce subtly different pixel-level output for the same source PDF — mostly invisible but creates spurious visual_diff failures in tight tolerance modes.
**Likelihood:** LOW (existing pipeline handles)
**Impact:** LOW
**Mitigation:**
  - Existing `tools/visual_diff.py` uses `compare -fuzz` for tolerance — already absorbs this.
  - For Gate 3 vision review, downscale to 1024 px (D7) — averages out hinting noise.
**Detection signal:** Already handled.

---

## P-WORKTREE-1. `feedback_worktree_prune_corrupts_others` — worktree cleanup risk

**Risk:** Memory says: "issue-cli worktree prune corrupts unrelated worktrees' git registry; avoid when other worktrees active". Issue #9 has its own worktree; #10 has this one. Running cleanup on either could break the other.
**Likelihood:** LOW (only triggered manually)
**Impact:** HIGH (loss of work)
**Mitigation:**
  - Don't run `worktree prune` while either issue is open. Mark in plan.
  - Use `git worktree remove <path>` with the explicit path — never `prune`.
**Detection signal:** Other worktree's `git status` reports "fatal: this operation must be run in a work tree".

---

## Top 10 Risks Ranked by Likelihood × Impact

Higher rank = more urgent in the plan. **L** = Likelihood, **I** = Impact, both 1-3.

| Rank | Risk | L | I | L×I | Plan-Phase | Concrete Mitigation Task |
|------|------|---|---|-----|------------|--------------------------|
| 1 | **P-EPS-2** Inline `ImageData` requires qCompress, not raw base64 | 3 | 3 | 9 | Phase 2 | Add `encode_inline_image()` helper in `blocks.py`; route through `WahlkreuzSymbol`. Add unit test that opens SLA in headless Scribus and asserts no `qUncompress` error. |
| 2 | **P-CONTENT-1** EPS file is just an X — no circle | 3 | 3 | 9 | Phase 1 | Visually verify the asset; decide composition strategy (DSL-drawn circle around EPS-X, or get a fixed EPS, or accept bare X). Document in spec for each Wahlkreuz template. |
| 3 | **P-EPS-1** Scribus PDF-in-ImageFrame requires `scale_type=0`, low-fidelity | 3 | 3 | 9 | Phase 2 | **Spike:** prefer EPS→PNG@600dpi path. Embed as PNG (proven), not PDF (flaky). Update D1 if PNG path validated. |
| 4 | **P-CI-4** New spot colors in `shared/ci.yml` regress round-trip diff | 3 | 3 | 9 | Phase 2 | Use `doc.add_color('Falz', spot=True, ...)` document-local, NOT in `shared/ci.yml`. Same for `Stanzkontur`. |
| 5 | **P-DSL-2** Merge conflict with parallel issue #9 | 3 | 2 | 6 | Phase 2/3 | Wait for #9 to land first OR rebase often. Append new blocks to bottom of `blocks.py`, no insertions. |
| 6 | **P-VISION-2** Vision API auth not in CI environment | 3 | 3 | 9 | Phase 4 | Decide: Gate 3 is local-only. CI runs build + smoke, not visual review. Document explicitly in plan. |
| 7 | **P-SPEC-1** Spec drift between yaml and build.py implementation | 3 | 2 | 6 | Phase 1+3 | Build `tools/spec_check.py` (mechanical slot-position diff). Required in CI gate. |
| 8 | **P-EPS-3** Ghostscript `/ID` non-determinism breaks SLA bytes | 3 | 2 | 6 | Phase 2 | Pre-compute and commit derived asset (PNG or PDF) once. Don't run `gs` in build.py. |
| 9 | **P-VISION-4** Hallucinated findings + disagreement spirals | 3 | 2 | 6 | Phase 4 | Prompt-template requires coordinate-cited findings. `known-false-positives.yml` per template. Single-model "blocking" → "advisory". |
| 10 | **P-PRINT-2** Falz position coordinate-origin confusion | 2 | 3 | 6 | Phase 1+3 | Standardize: coordinate origin = trim corner (NOT bleed). `spec_check.py` validates fold-line positions match spec. |

**Tier-2 (rank 11-20, address in plan but not blockers):**
- P-CONFIG-1 (color space mismatch RGB→CMYK)
- P-DSL-1 (spot-color-on-layer integration unverified)
- P-DSL-4 (layer ordering)
- P-PRINT-3 (door-handle hole standard variance)
- P-PRINT-5 (A6 quer headline readability)
- P-PRINT-6 (Impressum legal requirement)
- P-VISION-5 (model brand-bias)
- P-A6QUER-1 (info-grid space)
- P-FALZ-1 (fold-type ambiguity)
- P-COMPOSITE-1 (composite aspect-ratio distortion)

---

## Environment Audit Results

Probed in this worktree shell on 2026-05-07. All tooling verified by direct invocation.

| Tool | Status | Version | Path | Notes |
|------|--------|---------|------|-------|
| `gs` (Ghostscript) | ✓ | 10.05.1 (2025-04-29) | /usr/bin/gs | EPS→PDF works; non-deterministic `/ID` (P-EPS-3) |
| `pdftoppm` (Poppler) | ✓ | 25.03.0 | /usr/bin/pdftoppm | Used by render pipeline |
| `scribus` | ✓ | 1.6.3 | /usr/bin/scribus | Trixie native; opens SLAs via `xvfb-run`; CI uses 1.6.5 AppImage |
| `xvfb-run` / `Xvfb` | ✓ | (Debian default) | /usr/bin/xvfb-run | Required wrapper for Scribus headless |
| `convert` (ImageMagick) | ✓ | 7.1.1-43 Q16 aarch64 | /usr/bin/convert | Composite-grid alternative to Pillow |
| `compare` (ImageMagick) | ✓ | 7.1.1-43 | /usr/bin/compare | Used by `tools/visual_diff.py` |
| `odiff` | ✓ | 3.2.1 | /root/.npm-global/bin/odiff | Visual diff alternative |
| `make` | ✓ | GNU 4.4.1 | /usr/bin/make | But no Makefile in repo (P-CI-3) |
| `python3` | ✓ | 3.13.5 | /usr/bin/python3 | System Python |
| `python3-lxml` | ✓ | 5.4.0 | system | Required for sla_lib |
| `python3-yaml` (PyYAML) | ✓ | 6.0.3 | system | Required |
| `Pillow` (PIL) | ✗ | (not installed) | — | Installable via `uv pip install --system --break-system-packages pillow` (P-COMPOSITE-2) |
| `gh` (GitHub CLI) | ✓ | 2.92.0 | /usr/bin/gh | |
| `git` | ✓ | (system) | /usr/bin/git | |
| `codex` (CLI) | ✓ | codex-cli 0.128.0 | /root/.npm-global/bin/codex | Logged in via ChatGPT (verified `codex login status`); supports `-i, --image` for vision |
| `gemini` (CLI) | ✓ | 0.41.2 | /root/.npm-global/bin/gemini | OAuth in `~/.gemini/oauth_creds.json`; **token expired** but refresh_token present (auto-refresh on next call); supports `-p, --prompt` and stdin attachments |
| `verapdf` | ✗ | (not in this container path) | — | In Dockerfile.claude but not currently on PATH |
| `pdfcpu` | ✗ | (not in this container path) | — | In Dockerfile.claude but not currently on PATH |
| `inkscape` | ✗ | (not installed) | — | Could be used as EPS→SVG fallback; not required given Ghostscript works |
| `uv` (Python pkg mgr) | ✓ | 0.11.11 | /root/.local/bin/uv | Used by base image |

**Environment-derived blockers / actions:**

1. **Pillow** must be installed — add to Dockerfile.claude `apt-get install python3-pil` OR install via `uv pip install --system --break-system-packages pillow` in `tools/visual_review.py` setup step. Alternatively, drop Pillow dependency and use `convert` (ImageMagick) for composite — already installed.
2. **No vision API env vars** in shell (`ANTHROPIC_API_KEY` etc not set). Vision review uses CLI OAuth state, which only exists locally. CI runners cannot call vision models without secrets being added — recommend Gate 3 stays local-only (P-VISION-2).
3. **gemini token currently expired** but refresh_token exists. First call after worktree start may take ~2 sec to refresh.
4. **No Makefile** exists. Either add one with `make build`, `make check`, `make smoke`, `make visual-review` targets, or the issue's language must reference `bin/*` wrappers.
5. **CI workflow `.github/workflows/pages.yml`** does not install Pillow / codex / gemini — confirms Gate 3 is local-only.
6. **Scribus version mismatch** local 1.6.3 vs CI 1.6.5 is handled by existing `bin/check-stale-previews` (CI never re-renders templates; only validates committed PNG matches committed SLA).

---

## Sources

### HIGH confidence (empirical / official)

- Empirical Scribus tests in `/tmp/scribus-pdf-test/` (this research session): `test.sla` with raw base64 PDF fails with `qUncompress: Z_DATA_ERROR`; `test-png2.sla` with qCompress-wrapped PNG and `scale_type=0` renders correctly; `test-pdf-st0.sla` with PDF and `scale_type=0` renders but at lower resolution
- Empirical Ghostscript determinism test: two runs of `gs ... /tmp/wahl.eps` produce different `/ID` at byte ~199014
- Empirical EPS rendering: `gs -dEPSCrop -sDEVICE=pngalpha` of `/root/workspace/Wahl Kreuz im Kreis.eps` shows only yellow X, no circle
- Codebase analysis: `tools/sla_lib/builder/primitives.py:741-820` (ImageFrame), `tools/sla_lib/builder/document.py:247-263` (add_color spot=True), `tools/sla_lib/builder/styles.py:14-29` (DocumentLayer)
- Codebase analysis: `tools/sla_diff.py:500-515` (`_decode_inline_image_sha` documents qCompress format)
- Codebase analysis: existing template `templates/postkarte-a6-kampagne/build.py` uses `inline_image_ext='png'` exclusively, with `scale_type=0`
- `.github/workflows/pages.yml` (no Pillow/vision tooling in CI)
- `Dockerfile.claude` (current container's installed tools)
- Issue #9 ISSUE.md (`.issues/post-migration-dsl-hygiene/ISSUE.md`) confirms parallel changes to `blocks.py`, `test_blocks.py`, `sla_diff.py`

### MEDIUM confidence (forum reports cross-referenced with empirical)

- [Image Frame does not work with PDF files - Scribus Forums](https://forums.scribus.net/index.php?topic=1824.0) — confirms Scribus PDF-in-ImageFrame flakiness, ghostscript dependency, PDF-version sensitivity
- [Unable to inport PDF into image frame - Scribus Forums](https://forums.scribus.net/index.php?topic=3210.0) — same issue, workarounds via PDF-version downgrade
- [Imagedata format in SLA file - Scribus Forums](https://forums.scribus.net/index.php?topic=4973.0) — qCompress format confirmation

### LOW confidence (industry knowledge, would benefit from validation)

- Austrian Mediengesetz §24 Impressum requirement (P-PRINT-6): widely known but specific fine amount may differ between editions
- NRWO §53 Wahlanleitung restriction (P-PRINT-7): general principle is documented; specific risk threshold for templates is judgment
- Print-shop spot-color naming variance (P-PRINT-1): based on industry practice; specific Austrian print shop conventions not verified against current published style guides
- Door-hanger keyhole standard sizes (P-PRINT-3): based on industry common knowledge; specific Austrian/German print-shop standard not consulted directly

---

## Cross-references

- **CONTEXT.md D1** (EPS → PDF → inline ImageFrame): challenged by P-EPS-1, P-EPS-2, P-EPS-3. Recommend pivot to PNG path.
- **CONTEXT.md D4** (Spot-color layers): challenged by P-DSL-1, P-CI-4, P-CI-5. Recommend document-local additions, not `shared/ci.yml`.
- **CONTEXT.md D5/D6** (Multi-model vision review): challenged by P-VISION-2 (no CI auth), P-VISION-4 (hallucinations), P-VISION-5 (brand bias). Recommend local-only execution + brand-relative prompting.
- **Memory `feedback_worktree_prune_corrupts_others`**: noted in P-WORKTREE-1.
- **Memory `feedback_no_claude_attribution`**: respected in this research; no Claude branding referenced for tooling/templates.

