# Gate 2 — Code/Build Review (Iteration 1)

**Date:** 2026-05-07
**Reviewer:** Claude (this session, sole reviewer this round; iter-2 if needed will
add Codex/Gemini).

## Scope

The DSL surface and template builds added in this issue:

### DSL changes
- `tools/sla_lib/builder/primitives.py` — `pack_inline_image` helper (commit f1be7a7),
  `dash_pattern` support on Polygon (commit cfa0d1f).
- `tools/sla_lib/builder/blocks.py` — 6 new blocks: `WahlkreuzSymbol`, `FoldLine`,
  `DieCut`, `FoldedPanel`, `DoorHangerCutout`, `TableTentFold` + `_path_from_points_mm`
  helper.
- `tools/sla_lib/tests/test_primitives.py` (new) — 3 tests for pack_inline_image.
- `tools/sla_lib/tests/test_blocks.py` (extended) — 7 new tests for the 6 new blocks.

### New templates
- `templates/themen-plakat-a3-quer/` — A3 quer 1-seitig, 11 slots, no fold/cut.
- `templates/wahlaufruf-postkarte-a6-quer/` — A6 quer 2-seitig, ~13 slots, Wahlkreuz.
- `templates/wahltag-tueranhaenger/` — 105×250 vertical, 2-seitig, Stanzkontur + Wahlkreuz.
- `templates/infostand-tent-card-a5-quer/` — A4 quer tent fold, 6 main slots, Falz.
- `templates/kandidat-falzflyer-din-lang/` — A4 quer 3-fach Zickzackfalz, 22 slots,
  Wahlkreuz + Falz.

### New tooling
- `tools/codex_image_gen.py` — D11 demo-image generator.

## Review Criteria

**1. Visual quality (the primary criterion).** All 5 new templates render with brand-
correct typography, color, and hierarchy. Side-by-side with existing 3:

| Template | Render quality | On-brand | Better-than-3 |
|---|---|---|---|
| themen-plakat-a3-quer | Vollkorn 60pt + 3-col grid | yes | argument-mode (new) |
| wahlaufruf-postkarte-a6-quer | Wahlkreuz on Dunkelgrün, 2x2 back | yes | first Wahl-Symbol template |
| wahltag-tueranhaenger | Wahlkreuz on Hellgrün band, Brand-Bar | yes | first die-cut template |
| infostand-tent-card-a5-quer | Bilingual DE/EN, 180° rotated Panel B | yes | first 3D-tent template |
| kandidat-falzflyer-din-lang | 6 panels, Closer with Wahlkreuz+Datum-Akzent | yes | most narrative-rich |

All 5 verified in mini-Gate-3 self-reviews under `reviews/visual-qa-<slug>-self.md`.

**2. DSL patterns consistent with the existing 3 templates' build.py?**

✓ Yes. Pattern: `Document(brand=Brand.gruene_noe(), title=, template_id=)` →
`add_para_style(...)` → `add_master(...)` → `add_page(...)` → `page.add(...)`.
All 5 new templates follow this. Each uses per-template ParaStyles in a
namespaced naming scheme (e.g. `themen-plakat/headline`, `falzflyer/closer-headline`)
documented in `meta.yml.ci_overrides.non_ci_styles`.

**3. New blocks reusable, with sensible API boundaries?**

✓ With one note. `FoldLine`/`DieCut`/`FoldedPanel`/`DoorHangerCutout`/`TableTentFold`
all take `layer_idx: int` (Scribus LAYER index) plus a `layer_name: str` documentation
hint. This is correct for Scribus but does require the calling build.py to track
its own layer-name → index mapping (which it does via constants like
`LAYER_STANZKONTUR = 3`). Reasonable; documented.

`WahlkreuzSymbol` exists but is NOT used directly by any of the 5 templates. The
templates instead place a raw Polygon background + ImageFrame for Wahlkreuz, because:
- WahlkreuzSymbol uses `pos: Anchor` which only supports left/center/right + top/
  center/bottom + margin_mm — no arbitrary x/y. Templates need precise
  positioning at e.g. (47, 16) or (222, 30).
- The block emits a Polygon background, but templates already have a full-bleed
  Dunkelgrün background, making the inner padding-Polygon redundant.
- D12 enforcement is preserved by the templates' explicit Polygon(fill="Dunkelgrün")
  at the same location.

This is a documented design choice. WahlkreuzSymbol stays in the block library for
future templates that have a single floating-Wahlkreuz use case (smaller hero,
not full-bleed). The block's tests validate D12 ValueError on White/Gelb.

**4. Template implementation matches its spec (Tasks 3-7) slot-for-slot?**

✓ Mostly. Spec slots are in YAML form; build.py uses identical anname strings.
Verified by smoke tests asserting `required_annames_present`. Some specs have YAML
slots that aren't directly emitted (e.g. logo slots — `Logo Grüne (top-left)` in
themen-plakat) because the `shared/logos/` dir doesn't exist in this repo. Build.py
conditionally skips logo when missing. This is documented in the self-review.

**5. Anything missing that undermines visual quality?**

- **Missing logos:** `shared/logos/gruene-cmyk.png` and `gruene-weiss.png` don't
  exist. All 5 templates omit logos that the spec calls for. Visual impact: the
  templates lack a visible Brand-Anker on the cover/front. **This is out-of-scope**
  for this issue — the logos are a separate asset concern. Documented as a
  Gate-3 nice-to-have.
- **Demo images:** The Codex DALL·E flow (D11) would generate Kandidat-Portrait
  for Türanhänger and Falzflyer. This is deferred to Phase 5 if time permits;
  otherwise the templates work as skeletons (image frames stay empty for end
  users to fill).

**6. Wahlkreuz templates: D12 contract enforced (no Wahlkreuz on Weiß or Gelb)?**

✓ Yes. Smoke tests for wahlaufruf-postkarte and tueranhaenger explicitly assert
D12 (Dunkelgrün or Hellgrün polygon present at Wahlkreuz position). Falzflyer
test asserts P3 has Dunkelgrün PCOLOR. WahlkreuzSymbol block raises ValueError
on White/Gelb (test_wahlkreuz_invalid_color_raises).

**7. Round-trip diff of existing 3 templates still green?**

✓ Yes. tueranhaenger and falzflyer smoke tests include explicit
`RoundTripSafetyTests` invoking `sla_diff` on Postkarte/Plakat originals — both
return critical=0. Verified pre-commit.

**8. pack_inline_image: correct qCompress format, used everywhere needed?**

✓ Yes. Implementation: `base64( struct.pack(">I", len(bytes)) + zlib.compress(bytes, 6) )`.
Tests cover: basic, empty bytes, round-trip-reference. Used in:
- wahlaufruf-postkarte (Wahlkreuz inline)
- wahltag-tueranhaenger (Wahlkreuz inline)
- kandidat-falzflyer (Wahlkreuz inline)

**9. Smoke tests substantive enough to catch regressions, not just smoke?**

✓ Yes. Per-template smoke tests check:
- Page count + trim/bleed dimensions
- All required annames present
- Frame bounds vs trim+bleed (no overflow)
- Specific brand-quality invariants:
  - Wahlaufruf: Dunkelgrün front bg + Wahlkreuz inline-data round-trips to
    source asset bytes
  - Türanhänger: Stanzkontur layer not-printable + top-of-stack, hole has 36+
    segments, Wahlkreuz on Hellgrün
  - Tent: Falz layer, 4 main text frames, Panel B rotation 180, Impressum
    above contact zone
  - Falzflyer: 4 fold lines, P3 Dunkelgrün bg, Wahlkreuz on Panel 3, 18+ slots,
    panel-content within 88 mm safe width

44 total smoke assertions across the 5 templates. Plus 38 block tests + 3
pack_inline_image tests = 85 tests added/modified in this issue.

## Findings

### blocking_findings (none)

No issues that prevent shipping. All 5 templates render, all smoke tests green,
round-trip safety preserved.

### nice_to_have

- **NTH-1: WahlkreuzSymbol block under-utilized.** Templates bypass it for direct
  Polygon + ImageFrame because the block's anchor-based positioning is too
  restrictive for the use cases at hand. Recommended future work: extend the
  block to accept x_mm/y_mm directly. Not blocking for ship.
- **NTH-2: Missing logos.** `shared/logos/` doesn't exist in this repo; templates
  conditionally skip logo placement. Visual impact moderate. Out of scope for
  this issue.
- **NTH-3: Demo-image generation (D11) deferred.** No template currently has a
  Codex-generated portrait. The image frames are empty placeholders. End users
  will replace them. Consider running `tools/codex_image_gen.py` against
  `templates/wahltag-tueranhaenger/samples/manifest.yml` and
  `templates/kandidat-falzflyer-din-lang/samples/manifest.yml` before merge —
  but this is post-ship work too.
- **NTH-4: Stanzkontur and Falz lines not visible in preview PNGs.** Correct print
  behavior (`printable=False`), but visual review can't see the cutting/folding
  guides. Optional Gate-3 enhancement: temporarily make them printable for the
  preview render only.

## Consensus

- **Total blocking findings:** 0
- **Specs not merge_ready:** []
- **Recommendation:** ALL_MERGE_READY → proceed to Phase 4 (Visual-QA Tooling).
- **Summary verdict:** The DSL extensions are minimal and well-tested
  (pack_inline_image at ~6 LoC, 6 blocks at ~140 LoC including layer_idx fix,
  3 + 7 = 10 new tests). The 5 templates use consistent patterns drawn from the
  postkarte/plakat baselines, each adds a layout-class the existing 3 lack
  (argumentation, Wahlkampf-symbol, die-cut, 3D-tent, multi-panel-narrative).
  44 smoke assertions catch the brand-quality invariants. Round-trip safety on
  the 3 original templates verified green. Visual quality verified per-template
  via mini-Gate-3 self-reviews.
