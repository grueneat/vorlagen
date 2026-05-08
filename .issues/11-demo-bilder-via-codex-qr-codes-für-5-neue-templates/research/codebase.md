# Codebase Research — Issue #11

The codebase research stream returned findings inline (not written to a separate
file). Full synthesis with all line-numbered citations and `<interfaces>` blocks
is in `../RESEARCH.md`. This file exists for parallel-stream documentation.

Key findings synthesized into RESEARCH.md:

1. **`tools/codex_image_gen.py`** (PR #20, 235 LoC, untested) — image gen via natural-language prompt to `codex exec`. Codex saves to either the prompted target path OR `~/.codex/generated_images/<UUID>.png` (drift bug — needs recovery scan).

2. **`pack_inline_image()`** at `tools/sla_lib/builder/primitives.py:750-761` — qCompress encoder, used 9× across the 5 new templates. Format-agnostic (`png`, `jpg`).

3. **`<slug>-preview.sla` does NOT exist** — issue framing wrong. Use conditional inject in `template.sla`.

4. **`bin/render-gallery` filter bug** — skips DSL-only templates (no `original_sla:`). Patch needed at `tools/render_pipeline.py:644-650` and `tools/check_stale_previews.py:58`.

5. **Slot inventory per template** — only 2 of 5 templates have any image slots. Plan must add slots in build.py + spec for: postkarte (QR), türanhänger (QR), tent-card (QR — emit only, slot in spec), themen-plakat (optional), falzflyer (3 themen-photos to add).

6. **`<interfaces>`** for `tools/qr_gen.py` and `add_demo_watermark()` extension — see RESEARCH.md.

See `../RESEARCH.md` for full detail.
