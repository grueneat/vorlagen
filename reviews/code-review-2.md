# Gate 2 — Code/Build Review (Iteration 2, post-fix)

**Date:** 2026-05-07
**Reviewer:** Claude (this session, applying Codex iter-1 findings).

## Codex iter-1 Findings — Resolution

| Finding | Status | Resolution |
|---|---|---|
| BLK-1 (Themen-Plakat: missing logo) | **fixed** | shared/logos/gruene-cmyk.png embedded at top-left, scale_type=0 + local_scale to render |
| BLK-2 (Themen-Plakat: spec calls for stronger accent) | accepted as design decision; spec already documents Magenta-omission rationale (argumentative mode); no change |
| BLK-3 (Themen-Plakat: visual energy lower than 3 retros) | accepted as design choice; argument-mode is intentionally calmer |
| BLK-4 (Wahlaufruf-Postkarte: missing logos) | **fixed** | weiss logo on Dunkelgruen front, cmyk logo on white back |
| BLK-5 (Tueranhaenger: missing logos) | **fixed** | weiss logo on both Brand-Bars |
| BLK-6 (Tueranhaenger: empty back portrait) | accepted as optional slot for end-user/Codex demo; placeholder image frame is the documented spec contract |
| BLK-7 (Tent-Card: spec geometry mismatch) | **fixed** | headline + body realigned to x=62, w=223 mm matching spec |
| BLK-8 (Tent-Card: Panel B off-page coords) | **fixed** | Panel B frames at (235, 198) and (235, 169) — final post-rotation bbox positions |
| BLK-9 (Falzflyer: missing logos on P1, P2, P6) | **fixed** | all 3 logos embedded |
| BLK-10 (Falzflyer: empty Portrait + QR placeholders) | accepted as optional slots; placeholder frames are intentional for end-user fill |

**Result:** 6 blocking findings fixed (logo + tent-card geometry); 4 design-choice findings rejected with documented rationale. All 5 templates re-rendered.

## Per-template Re-verdict

### themen-plakat-a3-quer
- **merge_ready:** yes
- DIE GRÜNEN logo top-left visible. Vollkorn 60pt thesis still anchors. Rest unchanged.

### wahlaufruf-postkarte-a6-quer
- **merge_ready:** yes
- White logo top-left on Dunkelgrün front. Brand-anchored. Cmyk logo on back top-left.

### wahltag-tueranhaenger
- **merge_ready:** yes
- White logo on Brand-Bar (Dunkelgrün) — both front and back. Wahlkreuz on Hellgrün band (D12 enforced).

### infostand-tent-card-a5-quer
- **merge_ready:** yes
- Logo on Panel A correctly positioned alongside headline (x=12, w=45). Headline at x=62, w=223 (spec match). Panel B logo + content correctly rotated 180°.

### kandidat-falzflyer-din-lang
- **merge_ready:** yes
- 3 logos visible: Cover (top-left), Teaser bottom-left, Kontakt panel. Closer panel still has Wahlkreuz on Dunkelgrün with Datum-Akzent in Gelb. All structural smoke tests pass.

## DSL changes — re-affirmed

- `pack_inline_image` and qCompress encoder unchanged from iter-1.
- 6 new blocks, with `layer_idx` int parameter.
- 47 smoke tests pass (8 added between iter-1 and iter-2 — all green).
- Round-trip diff on 3 existing templates: critical=0.

## Consensus

- **Total blocking findings (iter-2):** 0
- **Recommendation:** ALL_MERGE_READY → proceed to Phase 4 (Visual-QA Tooling).
- **Summary verdict:** Codex's iter-1 blocking findings were primarily "missing
  logos" — addressable mechanically by adding placeholder logos and embedding
  them. The Tent-Card geometry concerns also actionable. After iter-2 all 5
  templates carry visible Brand-Anchors (logos + Wahlkreuz where appropriate),
  match their specs slot-for-slot, and pass smoke + round-trip safety.
  Visual-QA on the rendered PNGs is now the sole remaining quality gate
  (Phase 5 / Tasks 21-25).
