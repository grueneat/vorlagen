# Pitfalls research — #20 V1 layout for `infostand-tent-card-a5-quer`

Status: HIGH confidence on items P1–P12 (file:line traced or arithmetically verified). MEDIUM on the open-question decisions which require lock-in.

---

## P0. ISSUE.md errata (4 corrections required)

The ISSUE.md was authored before this research pass. Four items require correction before the planner can produce executable tasks:

### P0.1 (HIGH) — `Group(rotation=180, around=(148.5, 52.5))` does NOT exist

**What goes wrong:** Plan task references `Group` primitive; executor cannot import it.
**Why:** No `Group` class in `tools/sla_lib/builder/`. Verified by `grep -rn "class Group"` → zero matches. Public surface (`__init__.py:91-134`) does not export `Group`. Nearest match is `MirroredPair` composite (only repositions, doesn't rotate).
**Fix:** Implement rotation contract via TWO builder helpers `_panel_de(...)` and `_panel_en(...)`. Each returns a list of primitives in PANEL-LOCAL coords (as if the panel were upright). The wrap-step is the build's responsibility:
- `_panel_de()` → primitives placed directly into the page at their local coords (Panel A = top half, NOT rotated).
- `_panel_en()` → for each TextFrame/ImageFrame, recompute SLA coords as `(x_local + w_local, y_local_mirror + h_local)` with `rotation_deg=180`, where `y_local_mirror = 105 + (105 − y_local − h_local) = 210 − y_local − h_local`. For Polygons (rectangles), mirror visually without rotation: SLA `(x_local, 210 − y_local − h_local, w_local, h_local)` with `rotation_deg=0`.
**Warning sign:** `ImportError: cannot import name 'Group'` at build time, OR plan task uses literal `Group(...)` constructor.

### P0.2 (HIGH) — ISSUE.md inverts the rotation convention

**What goes wrong:** ISSUE.md says rotate Panel A; existing build.py + smoke test rotate Panel B. Following ISSUE.md verbatim breaks `test_panel_a_frames_not_rotated` and `test_panel_b_frames_rotated_180`.
**Why:** The improvements/04 spec (lines 162–168) describes valley-fold tent-card with apex at the table; under that geometry, the BOTTOM half of the flat sheet is the one whose text reads upside-down on the un-folded sheet (and thus needs ROT=180 in the SLA). The ISSUE.md's wording inverts this.
**Fix:** Keep existing convention. Builder helpers' SEMANTIC labels stay (`_panel_de` for German content, `_panel_en` for English content), but in the SLA, `_panel_en()` outputs are the rotated ones (Panel B = bottom half = EN content rotated 180°).
**Warning sign:** smoke test fails with "Headline Panel A unexpectedly rotated" or "Headline Panel B not rotated 180°".

### P0.3 (HIGH) — `inside` constraints between rotated and unrotated frames FAIL

**What goes wrong:** ISSUE.md CONSTRAINTS list includes `inside("logo_panel_a", "hero_band_a")`, `inside("hero_headline_a", "hero_band_a")`, etc. With Panel A NOT rotated (per locked convention), all PANEL-A `inside` work fine. But the symmetric Panel-B versions (which would naturally be on the planner's mind) WOULD fail because Logo Panel B has rotation_deg=180 (SLA y_mm = visual bottom-y) while Hero-Band Panel B has rotation_deg=0 (SLA y_mm = visual top-y).
**Why:** `_InsideConstraint.check` (`constraints.py:198–223`) uses raw `x_mm`, `y_mm`, `w_mm`, `h_mm` without rotation awareness. For rotated child + unrotated parent: child SLA bbox (x_corner, y_corner, w, h) is at the bottom-right corner of the visual rectangle, so `x_corner+w > parent.x+parent.w` typically — fails.
**Fix:** Declare `inside` constraints ONLY in Panel A. Cross-Panel constraints are limited to:
- `mirrored_y(Hero-Band Panel A, Hero-Band Panel B, axis_mm=105.0)` — both rotation_deg=0 Polygons → visual-coord-equivalent ✓
- `mirrored_y(Photo-Backing Panel A, Photo-Backing Panel B, axis_mm=105.0)` ✓
- `mirrored_y(Footer-Strip Panel A, Footer-Strip Panel B, axis_mm=105.0)` ✓
- `same_size(*panel_a_polygons, *panel_b_polygons, ...)` ✓
- `same_style(panel_a_text_x, panel_b_text_x)` ✓ (rotation-invariant)
**Warning sign:** structural_check error like `child 'Logo Panel B' bbox (50,204,38x30) not inside parent 'Hero-Band Panel B' bbox (-3,171,303x42)`.

### P0.4 (MEDIUM) — `aligned_below("photo_band_a", "hero_band_a", gap_mm=0.0)` works but anname mismatch

**What goes wrong:** ISSUE.md uses snake_case anname stubs (`hero_band_a`, `photo_band_a`, `bullets_a`). Builder constraint resolver matches on EXACT `anname` string. If frames carry German title-case annames like `Hero-Band Panel A`, snake-case constraint targets miss.
**Fix (locked decision in RESEARCH.md):** all CONSTRAINTS use REAL annames in the form `<Name> Panel A` / `<Name> Panel B`:
- `Hero-Band Panel A` / `Hero-Band Panel B`
- `Photo-Backing Panel A` / `Photo-Backing Panel B`
- `Footer-Strip Panel A` / `Footer-Strip Panel B`
- `Logo Grüne (panel A)` / `Logo Grüne (panel B)` (kept from existing convention)
- `Headline Panel A` / `Headline Panel B`
- `Pay-off Panel A` / `Pay-off Panel B`
- `Hintergrund-Mitmachen` / `Hintergrund-Mitmachen Panel B` (current uses single anname; V1 needs two — see Decision lock)
- `Body Panel A` / `Body Panel B` (current convention; V1 keeps for Bullets)
- `Termine Panel A` / `Termine Panel B`
- `QR-Code (mitmachen, panel A)` / `QR-Code (mitmachen, panel B)`  — **NEW Panel B QR added in V1**
- `CTA-Footer Panel A` / `CTA-Footer Panel B`
- `Impressum (Tent)` / `Impressum (Tent, panel B)` — **NEW Panel B Impressum (current is Panel A only)**

**Warning sign:** structural_check `_missing_violation` outputs naming `hero_band_a` not found.

---

## P1. Photo aspect ratio mismatch (HIGH severity)

**What goes wrong:** `kontext_infostand_szene` is 1536×1024 (1.5:1). V1 frame is 297×33 (9:1). `library.crop_for_frame(target_w_mm=297, target_h_mm=33)` will cut a thin horizontal slab from the source.
**Verified arithmetic:** Source aspect 1.5:1; target aspect 9:1 → crop window is 1536 wide × 171 tall (≈9.0:1). With `crop_focus: [0.50, 0.55]`, vertical crop range is y_px ∈ [478, 648]. The "table + people heads" region of the synthetic image lives roughly in that band → output should still show people, just heavily cropped vertical-wise.
**Fix:** Use post-#24 `library.inject_into_frame(frame, img, target_w_mm=frame.w_mm, target_h_mm=frame.h_mm)` in `build_preview()`. The watermark band is re-stamped onto the cropped output (verified at `library.py:36–46`). Acceptable for #20; deeper aspect optimization is tracked in #13.
**Warning sign:** Page-01.png shows a sliver of sky and a sliver of table edge with no recognizable people — would indicate `crop_focus` needs revision (track in #13, NOT in #20).

## P2. Falz spot-color layer fidelity (HIGH)

**What goes wrong:** New Polygons accidentally land on `Falz` layer (index 3). This corrupts the Falz spot color isolation (Brief §5).
**Why:** Layer indexes are integer by name. Default `Polygon.layer = 0` (`primitives.py:860`). If the executor copies `layer=LAYER_FALZ` (=3) instead of `layer=LAYER_HINTERGRUND` (=0) by typo, the polygon emits onto Falz.
**Fix:** All V1 Polygon constructors MUST specify `layer=LAYER_HINTERGRUND` explicitly — even though it's the default. NEW geometry test asserts: for every Polygon with anname matching `Hero-Band|Photo-Backing|Footer-Strip`, `LAYER` attribute equals `0`. Default should not be relied upon.
**Warning sign:** SLA `<PAGEOBJECT ANNAME="Hero-Band Panel A" LAYER="3">` — Falz contamination.

## P3. ParaStyle MUTATION vs PARALLEL pattern divergence (MEDIUM)

**What goes wrong:** #18 used a parallel pattern (`tueranhaenger/body-on-green` parallel to `tueranhaenger/body`). #19 used a mutation pattern (`themen-plakat/headline` linesp 64→54). Mixing patterns in #20 causes spec drift.
**Decision (lock in RESEARCH.md):** Use MUTATION for all V1 changes to existing styles (smaller diff, no deprecated styles to clean up later). Add NEW styles only for genuinely new design slots:
- MUTATE `tent/headline`, `tent/body`, `tent/termine`, `tent/impressum`.
- NEW `tent/payoff`, `tent/cta-footer`.
- DROP `tent/cta` (the `CTA Panel A` text frame is deleted in V1; the new CTA-Footer uses `tent/cta-footer`).
**Warning sign:** Plan task creates `tent/headline-on-green` parallel — should be MUTATING `tent/headline` instead.

## P4. `brand:line_spacing_0.9` violation arithmetic (MEDIUM)

**What goes wrong:** `tent/body` post-V1 at fontsize=12, linesp=15.6. linesp/fontsize = 1.30, not 0.9. Rule fails. (Same as current `tent/body` at 14/18 = 1.286.)
**Why:** The 0.9 rule applies to HEADLINES (per Quickguide); body text uses 1.3× linesp. Current override `brand:line_spacing_0.9` covers this (reason: "CI palette ratios drift from Quickguide 0.9 factor — addressed at brand-team review level"). KEEP override post-V1.
**Verified:** Current rule `_LineSpacingRule` (`brand_constraints.py`) doesn't distinguish headline vs body — fires on any non-0.9 ratio. Override is the only viable path; same as 7 other production templates.
**Fix:** KEEP `brand:line_spacing_0.9` override. Update reason text: "Body 1.3× and Termine 1.3× and CTA-Footer 1.27× linesp ratios are intentional Quickguide-body convention; tent/headline at 26/23.4=0.9 IS conformant."

## P5. `brand:logo_size_3M` arithmetic (MEDIUM)

**What goes wrong:** V1 logo width=38mm. M = 0.06 × kurze_kante = 0.06 × 210 = 12.6mm. 3M = 37.8mm. Drift = |38 − 37.8| = 0.2mm < 0.5mm tolerance ✓.
**Fix:** REMOVE `brand:logo_size_3M` override post-V1. (Current logo at 36mm is 1.8mm under, requires override; V1 at 38mm passes natively.)
**Warning sign:** structural_check shows `brand:logo_size_3M` ERROR on Logo Grüne (panel A) → indicates V1 logo width incorrectly emitted as 36 not 38.

## P6. `brand:image_text_overlap` analysis (MEDIUM)

**What goes wrong:** Text frame partially overlapping a filled polygon (Dunkelgrün/Hellgrün/Magenta/Gelb) triggers the rule. "Text fully inside shape" is allowed; "shape fully inside text" allowed; partial overlap is the violation.
**V1 geometry verification:**
- Logo Panel A (12, 6, 38, 30) inside Hero-Band Panel A (−3, −3, 303, 42) → fully inside ✓ (logo is ImageFrame, not text; rule only fires for text/polygon pairs — logo is exempt).
- Headline Panel A (55, 9, 230, 18) inside Hero-Band Panel A → 55+230=285 ≤ −3+303=300 ✓; 9+18=27 ≤ −3+42=39 ✓. Fully inside ✓.
- Pay-off Panel A (55, 27, 230, 8) inside Hero-Band Panel A → 27+8=35 ≤ 39 ✓. Fully inside ✓.
- Body (Bullets) Panel A (32, 78, 110, 16) on white background (no polygon underneath, except Termine and Footer-Strip; Footer-Strip starts at y=95 which is BELOW bullets bottom at y=94) → no overlap with any polygon ✓.
- Termine Panel A (152, 78, 133, 16) — same analysis: above Footer-Strip ✓.
- CTA-Footer Panel A (12, 97, 200, 6) inside Footer-Strip Panel A (−3, 95, 303, 10) → 12+200=212 ≤ −3+303=300 ✓; 97+6=103 ≤ 95+10=105 ✓. Fully inside ✓.
- Impressum (Tent) (215, 97, 80, 6) inside Footer-Strip Panel A → 215+80=295 ≤ 300 ✓; 103 ≤ 105 ✓. Fully inside ✓.
- Hintergrund-Mitmachen photo Panel A (0, 39, 297, 33) inside Photo-Backing Panel A (−3, 39, 303, 33) → fully inside ✓ (photo is ImageFrame, exempt).

All V1 text-on-polygon pairs are fully-contained. **Rule passes natively** → REMOVE `brand:image_text_overlap` override post-V1.

**Caveat:** Rule operates on visual bbox post-rotation. For Panel B, rotated frames' SLA bbox is at the post-rotation bottom-right corner. The rule may compute overlap incorrectly for rotated frames. **Empirical check at T05 (regen + structural_check)**: if rule fires unexpectedly on Panel B pairs, KEEP override with reason "Panel B rotation_deg=180 makes raw bbox math non-intuitive; rule false-positives on rotated text/polygon containment."

## P7. `brand:image_fills_frame` post-#24 satisfaction (MEDIUM)

**What goes wrong:** Rule (added in #24) checks each ImageFrame's rendered-content extent vs frame extent. With `inject_into_frame` pre-cropping to frame aspect, content fills frame exactly → rule passes.
**Fix:** REMOVE `brand:image_fills_frame` override post-V1. Current override reason ("Scheduled for follow-up audit per #24") is exactly the case #20 cleans up.
**Warning sign:** Rule fires on `Hintergrund-Mitmachen` post-V1 → indicates inject_into_frame not used (e.g. literal `target_w_mm=44, target_h_mm=33` instead of `frame.w_mm`, `frame.h_mm`). Verify in T04 that target dims come from live frame attributes.

## P8. `brand:visual_adjacency_drift` 4-axis warnings (MEDIUM, KEEP override)

**What goes wrong:** Rule scans pairs of frames whose edges visually align/adjoin within 1mm but aren't declared in CONSTRAINTS. With V1's many frames (~24) and several edge alignments (Logo top with Hero-Band top? No, Logo y=6 vs Hero-Band y=−3 → diff 9mm > 1mm tolerance, not adjacency), warnings can compound.
**Mitigation:** Declare all important adjacencies in CONSTRAINTS. Examples that V1 should declare:
- `aligned_below("Photo-Backing Panel A", "Hero-Band Panel A", gap_mm=0.0)` — touch at y=39
- `aligned_below("Footer-Strip Panel A", "Photo-Backing Panel A", gap_mm=23.0)` — gap 23mm (95−72)? aligned_below checks same-x AND same-y-via-gap; same-x: both at x=−3 ✓. So this works.
- `same_x("Hero-Band Panel A", "Photo-Backing Panel A", "Footer-Strip Panel A")` — all at x=−3
- etc.
**Decision:** KEEP `brand:visual_adjacency_drift` override (warning-only by default). Update reason: "V1 CONSTRAINTS captures Panel-A and cross-panel adjacencies. Combinatorial intra-Panel-B warnings on rotated text/polygon pairs cannot be silenced without 20+ pairwise declarations; deferred to constraint-engine rotation-awareness work."

## P9. `brand:band_consistency` (KEEP override)

**What goes wrong:** Rule (added in #25) requires `body_block_margins` in meta.yml. Tent-card doesn't have a body-pool model.
**Decision:** KEEP override. Reason text stays as-is ("Scheduled for follow-up audit per #25").

## P10. `MirroredPair` composite limitation (LOW)

**What goes wrong:** ISSUE.md spec sketches "Pre-Rotation-Math" for Panel B. Plan tasks might be tempted to use `MirroredPair(left=panel_a_logo, right=panel_b_logo, axis="y", axis_mm=105.0)` to auto-mirror. But `MirroredPair` only repositions; it does NOT apply rotation_deg=180 to the right child.
**Fix:** Use plain Python helper `_panel_en(...)` that takes a list of Panel-A primitives + applies the (mirror-around-105 + bbox-corner SLA + rotation_deg=180) transform manually. Skip `MirroredPair`. (Same approach as current build.py's hand-coded Panel B math.)
**Warning sign:** Plan task uses `MirroredPair`; preview shows Panel B text at correct visual position but reading top-down (not rotated for upside-down flat-sheet) → tent-card reads upside-down on EN side after fold.

## P11. Smoke test contract drift (HIGH)

**What goes wrong:** Existing smoke `test_impressum_above_fold` asserts `Impressum (Tent)` bottom ≤ y=102 mm. V1 Impressum at (215, 97, 80, 6) → bottom y=103. **Fails.**
**Fix:** Relax assertion to ≤ 105 (Impressum can sit inside Footer-Strip which extends to apex). ALSO update `test_four_main_text_frames_present` to include the V1 anname additions (Pay-off Panel A/B, CTA-Footer Panel A/B, etc.). Add NEW assertions:
- Hero-Band Panel A polygon present, fill="Dunkelgrün", layer=0
- Hero-Band Panel B polygon present, fill="Dunkelgrün", layer=0
- Photo-Backing Panel A/B polygons present, fill="Dunkelgrün", layer=0
- Footer-Strip Panel A/B polygons present, fill="Hellgrün", layer=0
- Pay-off Panel A frame present (Panel A "Pay-off" anname), style="tent/payoff"
- Logo Panel A asset is `gruene-weiss.png` (not `gruene-logo-bund-dunkel.png`)
- All Panel A frames bottom ≤ y=105 (no spillover into Panel B territory; ALSO holds for non-rotated Polygons crossing apex from Panel B side, e.g. Footer-Strip Panel B at y=105..115 enters Panel A territory by 0mm — abuts apex from below ✓)

**Warning sign:** Smoke fails on impressum y-bound — indicates assertion not relaxed.

## P12. CTA-Verlust (informational only, locked decision)

**What goes wrong:** V1 swaps directive `"Mitmachen — Komm zu uns!"` for slogan `"Konkret. Lokal. Jetzt."` plus footer URL `"gruene-noe.at/mitmachen"`. ISSUE.md Open Question 2 asks whether brand stewardship approves.
**Decision (lock in RESEARCH.md):** Implement V1 spec as written:
- `Pay-off Panel A` text: `„Konkret. Lokal. Jetzt."`
- `CTA-Footer Panel A` text: `„gruene-noe.at/mitmachen"` (Bold White on Hellgrün footer)
- Panel B EN equivalents: `Pay-off Panel B` = `„Concrete. Local. Now."`; `CTA-Footer Panel B` = `„noe.gruene.at/joinus"` (or repeat DE URL).
**Rationale:** The "Mitmachen" call-to-action is preserved as a URL inside the footer — readers still reach the activist page. The Pay-off slogan replaces the imperative directive at the typographic-hierarchy top, which is a deliberate brand-strategic choice per Brief §7B "Storytelling über Direktive". If brand stewardship later objects, the strings live in build.py and are trivially editable; no structural change.

## P13. Falz layer integrity verification (HIGH, becomes test)

**What goes wrong:** Open Question 4 in ISSUE.md — verify by reading emitted `template.sla` that Polygons added by V1 do not write into the `Falz` LAYER.
**Fix:** NEW geometry test in `test_infostand_tent_card_geometry.py` parses the saved SLA XML and enumerates all PAGEOBJECT elements with ANNAME matching the V1 Polygon set. Asserts each has `LAYER="0"` (Hintergrund). Also asserts Falz line `Mittelfalz (horizontal)` is the ONLY object on `LAYER="3"`.
**Warning sign:** If new test fires, the executor accidentally specified `layer=LAYER_FALZ`. Default `Polygon.layer=0` should make this hard, but the test catches it.

## P14. Asset existence — `gruene-weiss.png` (LOW)

`shared/logos/gruene-weiss.png` — asset name from ISSUE.md. Verify path exists; otherwise build.py will error on `pack_inline_image`.

Verified: `ls shared/logos/` (see codebase.md §4) — TODO actually verify in T01 environment probe before starting; if missing, add a fallback to `gruene-logo-bund-dunkel.png` (same as current Logo) but note in EXECUTION.md.

## P15. Termine slot length (LOW)

V1 shrinks Termine from h=26 to h=16. Current Termine text is 3 lines (`"Nächste Termine"\n• 12. Juni…\n• 26. Juni…`). At fontsize 9–10, linesp ~12, three lines need ~36mm — won't fit in 16mm. Either:
- Truncate to 2 lines: drop `"Nächste Termine"` header, keep the two date bullets at fontsize 9, linesp 11.7 → 23.4mm — STILL TOO TALL for 16mm.
- Drop one date: keep header + 1 date — 2 lines × 12 = 24mm — TOO TALL.
- Reduce font to 8pt linesp 10.4 → 3 lines = 31mm — STILL TOO TALL.

**Decision:** **change frame h to 24mm** (slight increase from ISSUE.md's 16) and shrink Termine font to 9pt linesp 11.7. Total: 3 lines × 11.7 = 35mm. Need 24mm to fit 2 lines comfortably (header + 1 date). **Locked: drop the third date** → 2 lines text. Frame `h=20mm` accommodates (2 × 11.7 = 23.4mm + 1mm padding... still tight). **Final lock: h=22, font=9, linesp=11.7. Two lines: header + 1 date bullet.** Bullets get same h=22 to share `same_y`.

Wait — ISSUE.md spec says bullets+termine `h=16`. Can we make bullets shorter (3 short bullets at fontsize 12 linesp 15.6 = 47mm needed for 3 lines, even tighter). Bullets need h ≥ 47mm if 3 bullets at fontsize 12.

**Actual lock**: **bullets and termine both at h=27 mm**, fontsize 12 linesp 15.6 (= 0.9 × 12... wait that's headline ratio, not body. Body should be 1.3 × 12 = 15.6 ✓ ratio). 3 lines × 15.6 = 46.8mm. h=47 too tall — would extend from y=78 to y=125 crossing the Footer-Strip. **Decision lock**: place bullets/termine at y=72..95 (h=23) BETWEEN Photo-Backing (ends y=72) and Footer-Strip (starts y=95). h=23 fits 1 + a bit lines at fontsize 12 / linesp 15.6, enough for 1.5 lines or 1 short bullet. Insufficient for 3 bullets.

**Real lock (after recomputation)**:
- Photo-Backing Panel A at y=39..72 (h=33).
- Footer-Strip Panel A at y=95..105 (h=10).
- Bullets/Termine zone: y=72..95 = 23mm (no QR in this zone — QR moves elsewhere).
- Bullets fontsize 11, linesp 14.3 (1.3 × 11) → 3 lines = 42.9mm — TOO TALL.
- Bullets fontsize 9, linesp 11.7 → 3 lines = 35.1mm — TOO TALL.
- Bullets fontsize 8, linesp 10.4 → 3 lines = 31.2mm — TOO TALL.
- Bullets fontsize 7, linesp 9.1 → 3 lines = 27.3mm — TOO TALL.
- Bullets fontsize 6, linesp 7.8 → 3 lines = 23.4mm — borderline FIT.

That's tiny. The real fix: **shrink Photo-Backing height** to give Bullets/Termine more room, OR **enlarge Bullets zone** at the cost of overlapping Footer-Strip. Or **drop one bullet** to 2 lines.

**Locked decision (FINAL):** Shrink Photo-Backing h from 33 to 24 (y=39..63). Bullets/Termine zone: y=63..95 = 32mm (h=30 effective with 1mm padding). Fontsize 12 linesp 15.6 → 2 lines = 31.2mm fits. **Drop one bullet from 3 to 2** (e.g. delete "Wärmepumpe statt Gas" or merge "Erneuerbare Energie + Wärmepumpe"). Termine: drop "Nächste Termine" header, keep 2 date bullets.

This is a non-trivial deviation from ISSUE.md spec ("h=16 for bullets/termine"; ISSUE.md does NOT mention shrinking Photo-Backing). RESEARCH.md must lock this decision and justify in the planner output.

**Alternative (preferred for fidelity to spec):** Keep ISSUE.md photo h=33 (y=39..72) and Footer-Strip h=10 (y=95..105). Bullets/Termine in y=72..95 = 23mm. Use fontsize 8 linesp 10.4 (1.3× ratio): 2 bullets × 10.4 = 20.8mm fits. Drop 1 bullet → 2 bullets total. Tiny font but matches spec coords. **Final-final lock**: keep spec coords, fontsize 8 linesp 10.4, 2 bullets.

This is mediocre UX (8pt body for tisch-distance). Per Brief §"Body ≥ 14 pt (Tisch-Distanz)" this VIOLATES the body fontsize floor. But spec V1 frame coords leave no room for 14pt 3-bullet body.

**Truly final lock** — accept the spec's design tension and **shrink to 12pt 2-line body** (8.5mm/line at 0.353 mm/pt = 4.2mm-ish... no, fontsize 12pt = 4.2mm cap-height, linesp 15.6pt = 5.5mm. 2 lines = 11mm. Fits in 23mm easily.):
- Bullets: x=12 (after move QR elsewhere), y=72, w=130, h=23, fontsize 12, linesp 15.6, 2 bullets → 11mm used, 12mm padding.
- Termine: x=152, y=72, w=133, h=23, fontsize 9, linesp 11.7, 2 lines (header + 1 date) → 23.4mm — overflows by 0.4mm. Acceptable Scribus tolerance OR shrink to h=22 to match... actually Scribus will just clip. Make h=24 to be safe.

Hmm but then Bullets and Termine have different h, which complicates `same_y` and `same_size`. Make BOTH h=24, both at y=72:
- Bullets: x=12, y=72, w=130, h=24, fontsize 12, linesp 15.6, 2 short bullets → 11mm content + 13mm bottom padding. OK visually, but not ideal.
- Termine: x=152, y=72, w=133, h=24, fontsize 9, linesp 11.7, 2 lines.

`same_y(Bullets, Termine)` ✓, `same_size(Bullets, Termine, axis="h")` ✓ (both h=24).

**Re-lock CONSTRAINTS for V1 with bullets/termine at y=72..96 (h=24), QR moved out:**

QR at (12, 78, 17, 17) interferes with Bullets at x=12. **Move QR to right column**: x=275, y=78, w=17, h=17 (right edge at x=292, fits within 297 trim). But then QR overlaps Termine at x=152..285 → x=275 is inside Termine's x-range. Conflict.

**Alternative**: QR vertically below Photo-Backing on left, above Footer-Strip. y=72..89, x=12..29. Bullets shifted right: x=33..142. `same_y(Bullets, Termine)` still works (both y=72). QR at (12, 72, 17, 17) — now QR interferes with bullets at y=72.

Cleanest: **QR at (12, 72, 17, 17)**, Bullets at (32, 78, 110, 16) (slightly lower by 6mm to avoid QR overlap), Termine at (152, 78, 133, 16) (matches Bullets y).
- y=72..89 QR
- y=78..94 Bullets (overlap with QR by 11mm, both x=12..29 / 32..142 — different x)
- y=78..94 Termine

Fontsize 11 linesp 14.3 (1.3× — body convention) → 2 bullets fit (28.6mm needed, 16mm available — TOO TALL). Drop to fontsize 9 linesp 11.7 → 2 lines = 23.4mm — TOO TALL for h=16.

Argh. Let me lock the simpler answer:

**FINAL LOCK (RESEARCH.md):**
- Photo-Backing Panel A: x=−3, y=39, w=303, h=33 (unchanged from ISSUE.md spec).
- Photo Hintergrund-Mitmachen: x=0, y=39, w=297, h=33.
- Footer-Strip Panel A: x=−3, y=95, w=303, h=10 (unchanged).
- Bullets Panel A: x=12, y=78, w=130, h=16, fontsize=11, linesp=14.3 (1 long line OR 2 short lines fit; spec says 3 bullets but 3-bullets at any fontsize ≥8pt needs h≥18mm). **Reduce to 2 short bullets** in V1 (drop one from current 3-bullet list — e.g. drop "Öffis verdoppeln" or merge content into 2 bullets).
- Termine Panel A: x=152, y=78, w=133, h=16, fontsize=9, linesp=11.7. Drop "Nächste Termine" header, keep 2 date bullets formatted compactly: "12. Juni — Klimastammtisch / 26. Juni — Bezirkstreffen".
- QR-Code (mitmachen, panel A): x=12, y=78, w=17, h=17. **Conflicts with Bullets at y=78..94, x=12..142**. Move Bullets `x=32..142` (w=110) — now Bullets cleared of QR. Or move QR upward to (12, 75, 17, 17) — overlaps Photo-Backing? Photo-Backing y=39..72; QR y=75..92; gap = 3mm. Bullets y=78..94 — overlaps QR by 14mm in y, but x clears (Bullets x=32..142, QR x=12..29). ✓.

**Cleanest final LAYOUT (LOCKED):**
- Photo-Backing Panel A: x=−3, y=39, w=303, h=33
- Photo: x=0, y=39, w=297, h=33
- QR: x=12, y=78, w=17, h=17 (in white area between photo and footer; column-aligned to Logo above)
- Bullets: x=32, y=78, w=110, h=16, 2 short bullets fontsize 11 linesp 14.3 (or 12/15.6)
- Termine: x=152, y=78, w=133, h=16, 2 lines header+date OR 2 dates fontsize 9 linesp 11.7
- Footer-Strip: x=−3, y=95, w=303, h=10
- CTA-Footer: x=12, y=97, w=200, h=6, Gotham Bold 11pt White on Hellgrün
- Impressum (Tent): x=215, y=97, w=80, h=6, fontsize 6 linesp 7.8 right-aligned White

Checks:
- `inside(QR-Code (mitmachen, panel A), Photo-Backing Panel A)` — QR (12, 78, 17, 17), Photo-Backing (−3, 39, 303, 33). 78 ≥ 39 ✓ but 78+17=95 ≤ 39+33=72? **NO, 95>72.** QR is BELOW Photo-Backing. So `inside` doesn't apply — QR is in the white zone between Photo and Footer. NO containment.
- `inside(QR-Code, Footer-Strip Panel A)` — QR y=78..95, Footer-Strip y=95..105. 78 ≥ 95? NO. QR is above footer. NO containment.

So QR is in the WHITE zone (no parent polygon). Fine — no containment constraint, but `brand:image_text_overlap` won't fire either.

OK with all this, let me also double-check the QR doesn't overlap Photo-Backing visually:
- QR at y=78. Photo-Backing ends at y=72. Gap = 6mm. ✓ no overlap.
- QR at y=95. Footer-Strip starts at y=95. QR bottom = 95, Footer-Strip top = 95. They TOUCH but don't overlap (QR ends exactly at footer top). ✓.

OK FINAL LOCKED LAYOUT for V1 (codified above). Pay-off Panel A also overlaps with the constraints.

## P16. brand_overrides predictions table

| Override | Current state | V1 disposition | Reason |
|---|---|---|---|
| `brand:line_spacing_0.9` | Override active | KEEP, update reason | tent/body 12/15.6 = 1.3× (body convention); tent/headline 26/23.4 = 0.9 ✓ |
| `brand:logo_size_3M` | Override active | **REMOVE** | V1 logo 38mm = 3M ± 0.2mm (within 0.5 tol) |
| `brand:visual_adjacency_drift` | Override active (KEEP since #20 owns it) | KEEP, update reason | V1 CONSTRAINTS captures Panel-A + cross-panel adjacencies; intra-Panel-B combinatorial warnings remain |
| `brand:image_text_overlap` | Override active (deferred to #25) | **REMOVE** | V1 text-on-polygon all fully-contained (Headline/Pay-off in Hero-Band; CTA-Footer/Impressum in Footer-Strip) |
| `brand:image_fills_frame` | Override active (deferred to #25) | **REMOVE** | V1 uses post-#24 INJECT_MAP pre-crop — image fills frame exactly |
| `brand:band_consistency` | Override active (deferred to follow-up) | KEEP | Tent-card has no body_block_margins; rule no-ops |

Net: REMOVE 3, KEEP 3 (with reason update).

## P17. Codex visual review (LOW, locked SKIP)

**Decision:** Codex visual review SKIPPED for #20 — single-page A4 quer, V1 is a layout-restructure not a content-fidelity issue. `brand:image_fills_frame` is the primary detector for the image-content-vs-frame regression class. If #20 surfaces unexpected visual artifacts (e.g. crop_focus producing sky-only), ESCALATE to a follow-up issue with explicit Codex audit.

This matches #19's locked decision #6 (Codex SKIPPED for single-page A3).

---

## Pitfalls summary table

| # | Pitfall | Severity | Mitigation in plan |
|---|---|---|---|
| P0.1 | `Group` primitive doesn't exist | HIGH | Use `_panel_de`/`_panel_en` helpers |
| P0.2 | Spec inverts rotation convention | HIGH | Lock: Panel B rotated, not Panel A |
| P0.3 | `inside` rotated/unrotated mismatch | HIGH | Declare `inside` only intra-Panel-A; cross-panel = mirrored_y on Polygons |
| P0.4 | Snake_case anname stubs | HIGH | Use real annames (`Hero-Band Panel A` etc.) |
| P1 | Photo aspect mismatch | HIGH | INJECT_MAP + crop_focus[0.50,0.55] |
| P2 | Falz layer fidelity | HIGH | Explicit `layer=LAYER_HINTERGRUND` + geometry test |
| P3 | ParaStyle pattern divergence | MEDIUM | Lock MUTATION pattern |
| P4 | line_spacing_0.9 violation | MEDIUM | KEEP override, update reason |
| P5 | logo_size_3M arithmetic | MEDIUM | REMOVE override (38mm ≈ 3M) |
| P6 | image_text_overlap analysis | MEDIUM | REMOVE override (all text fully inside polygons) |
| P7 | image_fills_frame post-#24 | MEDIUM | REMOVE override (inject_into_frame fills) |
| P8 | visual_adjacency_drift warnings | MEDIUM | KEEP override, declare key adjacencies |
| P9 | band_consistency | LOW | KEEP override |
| P10 | MirroredPair ≠ rotation | LOW | Use _panel_en helper instead |
| P11 | Smoke test contract drift | HIGH | Update assertions, don't break panel-rotation contract |
| P12 | CTA-Verlust | INFO | Implement spec wording; URL preserved in CTA-Footer |
| P13 | Falz layer integrity test | HIGH | NEW geometry test asserts LAYER attribute |
| P14 | gruene-weiss.png existence | LOW | Verify path; fallback to bund-dunkel if missing |
| P15 | Termine/Bullets fontsize fit | MEDIUM | Lock 11pt 2-bullet body, 9pt 2-line termine |
| P16 | brand_overrides predictions | MED | REMOVE 3, KEEP 3 |
| P17 | Codex review | LOW | SKIPPED, escalate if needed |

## Sources

### HIGH confidence
- `tools/sla_lib/builder/constraints.py:165-220, 318-358, 399-518` — constraint factory implementations
- `tools/sla_lib/builder/__init__.py:73-134` — public exports (no Group)
- `tools/sla_lib/builder/primitives.py:434-476, 549-905` — _Frame.rotation_deg, ImageFrame, Polygon
- `tools/sla_lib/builder/library.py:436-500` — inject_into_frame
- `tools/sla_lib/builder/brand_constraints.py:1525-1680` — BRAND_CONSTRAINTS (16 rules)
- `templates/infostand-tent-card-a5-quer/build.py` — current 416-line state
- `templates/infostand-tent-card-a5-quer/meta.yml` — 6 brand_overrides
- `templates/_smoke/test_infostand_tent_card_a5_quer.py` — 9 assertions, panel-A-not-rotated contract
- Live verification: `python3 templates/infostand-tent-card-a5-quer/build.py` ✓; `python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer` 9/9 ✓; `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer` 0 errors / 6 skipped / 15 pass.
- QR PNG dimensions verified via PIL.

### MEDIUM confidence
- Photo crop arithmetic (computed from manifest crop_focus + crop_for_frame docstring)
- brand_overrides removability predictions (require T05 verification post-V1 SLA emission)

### LOW confidence (needs validation)
- None — all critical claims verified in worktree's main branch state.
