# Research Synthesis — 11-demo-bilder-via-codex-qr-codes-für-5-neue-templates

Synthesized 2026-05-08 from two parallel research streams:
- `research/codebase.md` — DSL + tooling surface from PR #20, slot inventory, render-pipeline filters
- `research/ecosystem.md` — qrcode 8.2, gpt-image-2 (NOT dall-e-3), Pillow, pyzbar, URL probe, EU AI Act

**Confidence: HIGH** for foundational findings. Several CONTEXT.md decisions need correction before plan locks.

---

## User Constraints — corrections to CONTEXT.md surfaced by research

### Correction to D2 — Model name is `gpt-image-2`, not `dall-e-3`

**Original D2:** "DALL·E-3 Modell, hohe Qualität."

**Corrected:** Codex CLI 0.128.0 uses **gpt-image-2** internally; there is NO `--model dall-e-3` flag. Image generation is invoked via natural-language prompt (the codex agent's built-in image-generation tool fires when asked).

**Implementation impact:**
- Manifest `model: dall-e-3` and `quality: hd` fields become **informational only** — codex doesn't accept them as flags. Drop them from the schema, OR keep them as documentation comments.
- Existing `tools/codex_image_gen.py` already uses the natural-language pattern (`build_codex_prompt(...)` at L97-110) — no code change needed for model selection.
- Watermark text per EU AI Act Art 50 (in force 2026-08-02): use "**Symbolfoto — KI-generiert**" not "— Demo" for forward-compat.

### Correction to D5 — `<slug>-preview.sla` does NOT EXIST

**Original D6/D5 framing:** "`<slug>-preview.sla`-Build referenziert diese Bilder (Build-Logik existiert bereits)."

**Reality:** PR #20 did NOT create a `<slug>-preview.sla` mechanism. No `build_preview.py`, no separate render path. Issue's premise is wrong.

**Corrected approach (Option A from codebase agent):** **Conditional inject in `template.sla`.**
- Each template's `build.py` checks if `samples/<file>` exists.
- If yes: embed via `pack_inline_image()` into the relevant `ImageFrame`.
- If no: keep slot empty (current behavior).
- The slot-based contract holds because lookups are conditional, not hardcoded — end users opening fresh checkouts (without committing samples) still get clean templates.
- After demo content is committed: run `bin/render-gallery <slug>` to regenerate `template.sla` + `preview.pdf` + `page-*.png` + `previews_for_sla` SHA in `meta.yml`.

This is dramatically simpler than the proposed `<slug>-preview.sla` separate-file approach (~30 LoC/template vs ~150 LoC of new pipeline code). The acceptance criterion "`<slug>-preview.sla` re-rendered" re-reads as "`template.sla` re-rendered with embedded demo content; `previews_for_sla` matches".

### Correction to D3 — URL probe results

URLs probed with `curl -sIL`:

| URL | Status | Action |
|---|---|---|
| `https://noe.gruene.at/` | 200 OK | Use as-is |
| `https://noe.gruene.at/themen/` | 200 OK | Use as-is |
| `https://noe.gruene.at/mitmachen/` | 200 OK | Use as-is |
| `https://noe.gruene.at/termine/` | **301 → localized landing** | Encode the short canonical URL (browsers/scanners follow the redirect transparently) |
| `https://noe.gruene.at/themen/klimaschutz/` | **404** | **Fallback to `https://noe.gruene.at/themen/`** for Themen-Plakat QR |

### New: Render-pipeline filter bug — must patch

`tools/render_pipeline.py:644-650` and `tools/check_stale_previews.py:58` filter to templates with `meta.yml::original_sla`. The 5 new templates (DSL-only, no original to round-trip against) **do NOT have `original_sla:`** set. So `bin/render-gallery <slug>` SKIPS them — issue #11 cannot make progress without patching.

**Patch (~3 LoC):** Change filter from "`original_sla` set" to "`original_sla` OR `previews_for_sla` set". Same in both files.

### Tent-card QR slot — must enlarge

Spec for `infostand-tent-card-a5-quer.md` line 197 places the QR at 14×14 mm. With `noe.gruene.at/mitmachen/` (31 chars) at ECC=H + center logo, that needs version 4-5 (33-37 modules). 14 mm / 33 ≈ 0.42 mm/module — **violates D1's 0.5 mm minimum**. Plan must enlarge to **≥17 mm** (gives 0.51 mm/module at version 4) and update the spec.

### Slots that don't exist yet — plan must add

Issue assumes slots that aren't in build.py / spec:

| Template | Issue assumes | Reality |
|---|---|---|
| `wahltag-tueranhaenger` | QR on back | Has portrait slot, NO QR slot |
| `wahlaufruf-postkarte-a6-quer` | QR on back | NO image slots at all |
| `kandidat-falzflyer-din-lang` | 1 portrait + 3 themen-photos + QRs | Has 1 portrait + 1 QR; **no themen-photo slots** |
| `themen-plakat-a3-quer` | Optional themen-photo + QR | NO image slots beyond logo |
| `infostand-tent-card-a5-quer` | QR on Mitmachen page | QR in spec but NOT in build.py |

**Plan must add the missing ImageFrame slots in build.py AND update the corresponding `templates/_specs/<slug>.md` slot tables.** `tools/spec_check.py` enforces drift, so spec must keep pace.

---

## Summary

This is a small-to-medium issue. Two new tools (`tools/qr_gen.py`, watermark post-process in `codex_image_gen.py`), one schema extension (manifest `qr_codes:` list + per-image `synthetic`/`note` fields), one render-pipeline filter patch, and per-template additions to fill or extend image slots. Pillow already installed; `qrcode[pil]` is the only new pip dep. `pyzbar` for tests.

The framing of `<slug>-preview.sla` in CONTEXT.md is wrong but the spirit is preserved by the conditional-inject pattern. End users still get clean templates; gallery previews show populated demo content.

Risks centered on:
- Codex output-path drift (codex may save to `~/.codex/generated_images/<UUID>.png` instead of target) — needs post-call recovery scan
- Codex generation latency + occasional content-policy refusals for political-portrait prompts — Cap-5-iter (D7) should handle, plus prompt phrasing must avoid trigger words
- Determinism: Pillow 12.2 + qrcode 8.2 stripped of metadata gives byte-identical output
- Tent-card QR slot too small at 14 mm — enlarge to 17 mm
- 1 of 5 candidate URLs returns 404 — fallback documented

---

## Codebase Touchpoints (verified)

| File | Lines | Role for #11 |
|---|---|---|
| `tools/codex_image_gen.py` | 1-235 | Existing, untested. Activate via real run + add Pillow watermark post-process + add output-path recovery scan |
| `tools/sla_lib/builder/primitives.py::pack_inline_image` | 750-761 | Used as-is to embed demo bytes; format-agnostic, supports `jpg` and `png` |
| `tools/render_pipeline.py` | 644-650 | **PATCH**: filter must include `previews_for_sla`-tracked templates (currently skips DSL-only) |
| `tools/check_stale_previews.py` | 58 | **PATCH**: same filter logic |
| `tools/visual_review.py` | 1-300 | Reuse for D10 single-pass review with custom prompt |
| `tools/spec_check.py` | 1-213 | Will catch slot-table drift when build.py grows new slots |
| `templates/<slug>/build.py` | varies | Per-template: conditional inject + new slots where missing |
| `templates/_specs/<slug>.md` | varies | Per-template: slot-table updates for new image/QR slots |
| `templates/<slug>/samples/manifest.yml` | NEW | Per-template manifest; both `images:` and `qr_codes:` |
| `templates/<slug>/samples/<images>.{jpg,png}` | NEW | Generated bytes (committed) |
| `shared/ci.yml` | NO CHANGE | Brand color reference; QR module color comes from here at runtime |
| `Dockerfile.claude` | between L39-L48 | Add `qrcode[pil]==8.2`, `pyzbar==0.1.9`, `libzbar0`, `zbar-tools` |

### `<interfaces>` — new tools

```python
# tools/qr_gen.py — NEW
def generate_qr_png(
    target_url: str,
    output_path: Path,
    *,
    module_color: tuple[int, int, int] = (28, 72, 33),  # Dunkelgrün sRGB
    background_color: tuple[int, int, int] = (255, 255, 255),
    embed_logo: Path | None = None,
    error_correction: str = "H",                        # L|M|Q|H per D1
    pixel_size: int = 600,
    border: int = 4,                                    # quiet zone (D1)
    version: int | None = None,
) -> Path
def parse_manifest(path: Path) -> dict          # reads qr_codes: list
def main(argv: list[str] | None = None) -> int  # CLI

# tools/codex_image_gen.py — EXTEND (add at module level)
def add_demo_watermark(
    image_path: Path,
    text: str = "Symbolfoto — KI-generiert",
    font_path: Path | None = None,                     # default: Gotham Narrow Book
    position: str = "bottom-right",
    text_color: tuple[int, int, int, int] = (255, 255, 255, 230),
    bg_color: tuple[int, int, int, int] = (0, 0, 0, 130),
    padding_px: int = 12,
    font_size_px: int = 18,
) -> Path

def recover_codex_output(target_path: Path, search_dir: Path = HOME / ".codex/generated_images") -> bool
    """If codex saved to ~/.codex/generated_images/<UUID>.png instead of target,
    move/copy the most recent file there to target_path."""
```

---

## Standard Stack (verified versions)

| Tool | Version | Path | Status |
|---|---|---|---|
| `qrcode[pil]` | 8.2 | NEW pip | Add to Dockerfile.claude |
| `Pillow` | 12.2.0 | already installed | byte-deterministic with metadata stripped |
| `pyzbar` | 0.1.9 | NEW pip | Test deps; needs `libzbar0` |
| `libzbar0` + `zbar-tools` | apt | NOT installed | Add to Dockerfile.claude |
| `codex` (CLI) | 0.128.0 | `/root/.npm-global/bin/codex` | OAuth at `/root/.codex/auth.json` |
| `gemini` (CLI) | latest | `/root/.npm-global/bin/gemini` | OAuth (auto-refresh) |
| Python | 3.13 | `/usr/bin/python3` | |
| Scribus | 1.6.3 (local), 1.6.5 (CI) | | |
| `montage` (ImageMagick) | 7.x | already installed | reused for visual_review composite |

---

## Don't Hand-Roll

- **Don't write a custom QR generator.** Use `qrcode[pil]` 8.2 with `StyledPilImage` + `SolidFillColorMask` + ECC=H + `embedded_image_path`. ~15 LoC of wrapper.
- **Don't write a custom image-decoder for tests.** Use `pyzbar.decode()` for round-trip URL verification.
- **Don't write a custom watermark renderer.** Pillow `ImageDraw.text` with TTF.
- **Don't extend the manifest schema with parallel parsers.** Both tools share `parse_manifest()` (in `codex_image_gen.py` already; `qr_gen.py` reuses or copies the function).
- **Don't reimplement codex image-gen.** It's a natural-language prompt; `tools/codex_image_gen.py` already does it correctly.
- **Don't add `<slug>-preview.sla` separate-file pipeline.** Conditional inject in `build.py` is the right shape.

---

## Architecture Patterns (locked from PR #20)

1. **Per-template `samples/` directory** — manifest + generated bytes + (eventually) human-edited replacements all co-located.
2. **Slot-based contract** — `template.sla` slots stay empty for end users; demo bytes are loaded conditionally if `samples/<file>` exists. End users see no broken refs.
3. **Authoring tools, not build tools** — `codex_image_gen.py` and `qr_gen.py` run once at issue-execute time; CI never invokes them.
4. **Deterministic asset commit** — generated bytes committed to repo; subsequent builds byte-stable.
5. **Drift-detection** — `spec_check.py` enforces spec ↔ build agreement; new slots in build.py demand spec updates.

---

## Common Pitfalls (top 10, ranked by likelihood × impact)

| # | ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| 1 | P-CODEX-PATH | Codex saves to `~/.codex/generated_images/<UUID>.png` not target | HIGH | HIGH | Post-call recovery scan; helper `recover_codex_output()` |
| 2 | P-FILTER | render-pipeline skips DSL-only templates | CONFIRMED | CRITICAL | Patch filter in render_pipeline.py + check_stale_previews.py |
| 3 | P-SLOTS | Issue assumes slots that don't exist | CONFIRMED | HIGH | Add ImageFrame slots in build.py + spec for 4 templates |
| 4 | P-TENT-SIZE | 14mm QR slot too small for ≥0.5mm modules | CONFIRMED | HIGH | Enlarge to 17mm; spec update |
| 5 | P-URL-404 | `noe.gruene.at/themen/klimaschutz/` 404 | CONFIRMED | LOW | Fallback to `/themen/` |
| 6 | P-CONTENT-POLICY | DALL·E refuses political-portrait prompts | MEDIUM | MEDIUM | Phrase prompts neutrally; D7's 5-iteration cap absorbs |
| 7 | P-DETERMINISM | qrcode/Pillow output drift across versions | LOW | HIGH | Pin Pillow=12.2.0, qrcode=8.2 exact |
| 8 | P-EU-AI-ACT | "Demo" watermark insufficient for EU AI Act Art 50 | LOW now, CERTAIN by 2026-08 | LOW | Use "Symbolfoto — KI-generiert" (forward-compat) |
| 9 | P-MANIFEST-MIGRATION | parse_manifest raises on manifests without `images:` | MEDIUM | MEDIUM | Loosen to permissive (warn instead of raise) |
| 10 | P-FALZFLYER-SCOPE | "3 themen-fotos" stretches scope; no spec slots exist | MEDIUM | MEDIUM | Plan adds 3 slots + spec updates; or accepts as scope inflation. CONTEXT D8 locks: must add. |

---

## Sources (HIGH confidence)

- Codebase agent (line-numbered citations against `tools/`, `templates/`, `Dockerfile.claude`)
- Ecosystem agent empirical tests (`pip install qrcode[pil]==8.2`, `pyzbar.decode()` on real generated PNGs, `curl -sIL` URL probes, codex 0.128.0 `--help` exhaustive)
- Existing PR #20 source: `tools/codex_image_gen.py`, `tools/visual_review.py`, `tools/spec_check.py`
- OpenAI Codex CLI docs (verified: no `--image-out` flag exists; image-gen is prompt-driven)
- EU AI Act Art 50 enforcement timeline (2026-08-02)

## Plan Inputs (what PLAN.md must absorb)

1. **One new tool**: `tools/qr_gen.py` (~120 LoC including manifest parser + tests)
2. **One tool extension**: `tools/codex_image_gen.py` — add `add_demo_watermark()` post-process + `recover_codex_output()` recovery
3. **Two pipeline patches**: `tools/render_pipeline.py:644-650` + `tools/check_stale_previews.py:58` — filter widening
4. **Five manifest files**: `templates/<slug>/samples/manifest.yml` per template with `images:` and `qr_codes:`
5. **Five build.py modifications**: conditional inject + slot additions where missing (postkarte, türanhänger, falzflyer-themen, themen-plakat optional, tent-card)
6. **Five spec.md updates**: slot tables for new ImageFrames; `tools/spec_check.py` validates
7. **One Dockerfile addition**: `qrcode[pil]==8.2`, `pyzbar==0.1.9`, `libzbar0`, `zbar-tools`
8. **Tests**: `tools/sla_lib/tests/test_qr_gen.py` (determinism + scannability)
9. **Single visual review pass** (D10): `tools/visual_review.py --all` with focused prompt; document Vorher/Nachher
10. **PR + merge** per user authorization
