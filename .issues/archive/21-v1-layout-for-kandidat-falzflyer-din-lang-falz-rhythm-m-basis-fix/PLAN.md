# Plan: V1 layout for `kandidat-falzflyer-din-lang` (Falz-Rhythm) + M-Basis fix

<objective>
What this plan accomplishes: Implement V1 "Falz-Rhythm" layout for the `kandidat-falzflyer-din-lang` 6-panel Zickzackfalz template per `improvements/05-kandidat-falzflyer.md`, while resolving the "M-Basis-Konflikt" by correcting a misleading build.py header comment + resizing 3 violating logos (NO tool/library code change). This is the FIFTH and final V1 rollout (after #17, #18, #19, #20) and absorbs every pattern from those four predecessors.

Why it matters: Aligns kandidat-falzflyer's logo sizing with the Quickguide's Trim-konsistent 3M rule (which the brand_constraints rule already enforces correctly today — only this template is non-compliant). Lands the universal Top-Band system + P1 P6 grüne-Klammer + P4/P5 Themen mirror + P6 2-column Kontakt symmetry that completes the V1 design language across all 5 templates. Closes HANDOFF.md V1 rollout sequence (#15).

Scope:
- IN: build.py V1 layout overhaul (4 Top-Bands + 5 Top-Titles + P1 Name-Card + P2 Body-Backing + P6 vollflaechig polygon + Themen restructure + 2-column Kontakt + 22-entry CONSTRAINTS list); ParaStyle migration (10 mutations + 4 NEW); INJECT_MAP via build_template/build_preview split; spec rewrite; NEW geometry test 18+ invariants; smoke test extension; README + brief Section 10 + HANDOFF.md V1 sequence close; 3 logo resizes to 38mm; meta.yml ci_overrides extend + brand_overrides cleanup.
- OUT: edits to `tools/check_ci.py` (no logo logic — locked decision #2); edits to `tools/sla_lib/builder/brand_constraints.py` (rule already correct — locked decision #1); Codex visual review (locked decision #13); P2 Pull-Quote frame emit (style registered, frame deferred); `falzflyer/contact-label` Caps-row variants (deferred); `samples/themen-wirtschaft.jpg` import (already in central library at `themen_wirtschaft_handwerk` — locked #7); V2/V3 design variants.

No CONTEXT.md exists for this issue — RESEARCH.md locks 13 decisions and 5 ISSUE.md errata corrections. The plan honors RESEARCH.md as authoritative wherever it disagrees with ISSUE.md (ISSUE.md framing on `tools/check_ci.py` is wrong; RESEARCH wins).
</objective>

<context>
Issue: @.issues/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix/ISSUE.md
Research (AUTHORITATIVE — 13 locked decisions): @.issues/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix/RESEARCH.md
Line-level evidence: @.issues/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix/research/codebase.md
Spec source-of-truth: @improvements/05-kandidat-falzflyer.md
Cross-rollout context: @improvements/HANDOFF.md
Reference precedent (just-merged): @.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/PLAN.md and matching @templates/infostand-tent-card-a5-quer/build.py + @tools/sla_lib/tests/test_infostand_tent_card_geometry.py

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

### Constraint factories (`tools/sla_lib/builder/constraints.py`)

```
# All factories take *targets as anname strings (or frame instances; .anname extracted).
# tolerance_mm default 0.5; name optional (auto-generated from kind+targets if blank).
# Resolver matches `anname` exactly (case-sensitive).
def same_y(*targets, tolerance_mm=0.5, name="") -> Constraint     # L399
def same_x(*targets, tolerance_mm=0.5, name="") -> Constraint     # L408
def same_size(*targets, axis="both"|"w"|"h", tolerance_mm=0.5, name="") -> Constraint   # L417
def mirrored_x(left, right, axis_mm, tolerance_mm=0.5, name="") -> Constraint   # L433
def mirrored_y(top, bottom, axis_mm, tolerance_mm=0.5, name="") -> Constraint   # L443
def inside(child, parent, tolerance_mm=0.5, name="") -> Constraint   # L453 raw bbox containment
def aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="") -> Constraint   # L507
# REQUIRES same x_mm AND below.y == above.y + above.h + gap
def same_style(*targets, name="") -> Constraint   # L481
def distance_y(a, b, equals, tolerance_mm=0.5, name="") -> Constraint   # L489
def distance_x(a, b, equals, tolerance_mm=0.5, name="") -> Constraint   # L498
# NO Group, NO same_y_top, NO same_x_center, NO mirrored_around_bbox-aware helpers.
```

### Brand rule `brand:logo_size_3M` (`tools/sla_lib/builder/brand_constraints.py:249-282`) — DO NOT EDIT

```
@dataclass(frozen=True)
class _LogoSize3MRule(BrandRule):
    factor: float = 3.0
    tolerance_mm: float = 0.5
    def check(self, primitives, doc, constraints=None):
        page = doc.pages[0]
        page_w_mm = page.width_pt * PT_TO_MM
        page_h_mm = page.height_pt * PT_TO_MM
        kurze_kante = min(page_w_mm, page_h_mm)   # ALREADY trim-min — RESEARCH locked
        m = 0.06 * kurze_kante
        expected = self.factor * m
        # falzflyer: page=297x210 -> kurze_kante=210 -> M=12.6 -> 3M=37.8mm
        for p in primitives:
            if not isinstance(p, ImageFrame): continue
            if not re.search(r"\\blogo\\b", getattr(p, "anname", "") or "", re.IGNORECASE): continue
            if abs(p.w_mm - expected) > self.tolerance_mm: violations.append(...)
        return violations
```

### Primitive surface (`tools/sla_lib/builder/primitives.py`)

```
class _Frame:
    x_mm: float; y_mm: float; w_mm: float; h_mm: float
    rotation_deg: float = 0; layer: int = 2; anname: str = ""
class TextFrame(_Frame):
    style: str; runs: list[Run]; layer: int = 2
    fcolor: Optional[str]   # overrides ParaStyle fcolor when set
class ImageFrame(_Frame):
    inline_image_data: Optional[str]; inline_image_ext: Optional[str]
    scale_type: int = 0; ratio: int = 1; layer: int = 1
class Polygon(_Frame):
    fill: str = "Black"; line_color: Optional[str] = None
    layer: int = 0; shape: str = "rectangle"
def pack_inline_image(image_bytes, ext) -> tuple[str, str]
```

### Library helper (`tools/sla_lib/builder/library.py`) — INJECT_MAP idiom

```
def inject_into_frame(frame, img, *, target_w_mm, target_h_mm,
                       dpi=300, quality=80, apply_watermark=True) -> None
def load(id, *, optional=False) -> Optional[LibraryImage]
def crop_for_frame(img, *, target_w_mm, target_h_mm, dpi=300, quality=80,
                    apply_watermark=True) -> bytes
```

### Falz block (`tools/sla_lib/builder/blocks.py:559`)

```
class FoldLine:
    start_mm: tuple[float, float]
    end_mm:   tuple[float, float]
    layer_idx: int = 3
    anname: str = ""
```

### Current build.py contract (`templates/kandidat-falzflyer-din-lang/build.py`)

```
TRIM_W_MM = 297.0; TRIM_H_MM = 210.0; BLEED_MM = 3.0
PANEL_W_MM = 99.0; FOLD_X1_MM = 99.0; FOLD_X2_MM = 198.0
LAYER_HINTERGRUND = 0; LAYER_BILDER = 1; LAYER_TEXT = 2; LAYER_FALZ = 3

def _add_styles(doc): ...    # registers 12 falzflyer/* ParaStyles (V1: 16)
def _add_front(doc, page0): ...    # P1 + P2 + P3 + 2 fold lines (V1 expands)
def _add_back(doc, page1): ...    # P4 + P5 + P6 + 2 fold lines (V1 expands)
def build_doc() -> Document: ...   # V1: rename to build_template, add build_preview wrapper
def build(out_path=...) -> Path:   # V1: calls build_preview() internally
CONSTRAINTS = [...]   # V1: full rewrite (9 -> 22 entries)
```

### Existing ParaStyle dump (12 styles in V0; check via `_extra_para_styles`)

Real production names (NOT spec-stub names):
- `falzflyer/cand-name` (NOT `cover-name`)
- `falzflyer/slogan`
- `falzflyer/teaser-headline`
- `falzflyer/teaser-body`
- `falzflyer/thema-headline` (singular `thema-`, NOT `themen-`)
- `falzflyer/thema-body`
- `falzflyer/closer-headline`
- `falzflyer/closer-datum`
- `falzflyer/closer-url` (NOT `url`)
- `falzflyer/contact-headline`
- `falzflyer/contact-body`
- `falzflyer/impressum`

NO `falzflyer/contact-label` exists. Per RESEARCH locked #4 — use REAL names verbatim.

### Library asset manifest (`shared/sample-images/manifest.yml`) — confirmed present

- `portrait_maria` — for P1 Kandidat-Portrait
- `themen_klimaschutz_solar` — for P4 Thema 1
- `themen_soziales_kaffeehaus` — for P4 Thema 2
- `themen_bildung_volksschule` — for P5 Thema 3
- `themen_wirtschaft_handwerk` — for P5 Thema 4 (NEW for V1; asset at `shared/sample-images/themen/wirtschaft-handwerk.jpg`, crop_focus [0.50, 0.55] — already exists; locked #7)

### Logo asset path

- P1 + P6 use `shared/logos/gruene-weiss.png` (3.5:1 wordmark, white-on-transparent, 413x118 RGB). Verify with PIL probe in T03.
- NO `bund-weiss` variant exists; document fallback to `gruene-logo-bund-dunkel.png` if `gruene-weiss.png` missing (it isn't, but defensive).

### Live-verified bins

- `bin/render-gallery <slug> --skip-visual-diff` — regenerates template.sla + page-NN.png + preview.pdf + meta.yml SHA + site/public mirror
- `bin/audit-alignment <slug>` — optional alignment audit
- `bin/check-stale-previews` — verifies all template SHAs match emitted artifacts
- `python3 -m sla_lib.builder.structural_check <slug>` — single template
- `python3 -m sla_lib.builder.structural_check --all` — all templates
- `python3 -m unittest discover tools/sla_lib/tests` — geometry test suite
- `python3 templates/_smoke/test_kandidat_falzflyer_din_lang.py` — smoke

</interfaces>

Key files:
@templates/kandidat-falzflyer-din-lang/build.py — primary edit target (T01-T09; main edits T01, T02, T03, T04, T05, T06, T07, T08, T09)
@templates/kandidat-falzflyer-din-lang/meta.yml — overrides + ci_overrides (T01, T03, T10)
@templates/kandidat-falzflyer-din-lang/template.sla — regen artifact (T10)
@templates/kandidat-falzflyer-din-lang/page-01.png — regen artifact (T10)
@templates/kandidat-falzflyer-din-lang/page-02.png — regen artifact (T10)
@templates/kandidat-falzflyer-din-lang/preview.pdf — regen artifact (T10)
@templates/_smoke/test_kandidat_falzflyer_din_lang.py — smoke extension (T11)
@templates/_specs/kandidat-falzflyer-din-lang.md — spec rewrite (T11)
@templates/kandidat-falzflyer-din-lang/README.md — V1 deltas + M-Basis decision rationale (T11 NEW)
@tools/sla_lib/tests/test_kandidat_falzflyer_geometry.py — NEW geometry test 18+ invariants (T11)
@shared/brand/DESIGN-SYSTEM-BRIEF.md — Section 10 row 2026-05-09 (T11)
@improvements/HANDOFF.md — V1 rollout sequence #15 mark complete (T11)
@templates/infostand-tent-card-a5-quer/build.py — REFERENCE for build_template/build_preview split + INJECT_MAP idiom (read-only)
@tools/sla_lib/tests/test_infostand_tent_card_geometry.py — REFERENCE for 21-invariant geometry test pattern (read-only)
</context>

<commit_format>
Format: conventional commits with numeric issue prefix (per `.issues/config.yaml` `commits.prefix=true`).
Example: `21: fix(kandidat-falzflyer): correct M-Basis header-comment + drop logo_size_3M override`
Pattern: `21: {type}({scope}): {description}`

Scopes: `kandidat-falzflyer` for template-touching tasks, `builder` for shared library/tests, `check-ci` for the M-Basis comment task (per user prompt convention), `docs` / `test` / `chore` as appropriate.

NEVER include "claude" / "Co-Authored-By: Claude" / AI attribution in any commit message, code comment, or file (per user standing directive).
</commit_format>

<tasks>

<task type="auto">
  <name>Task 01: chore(check-ci): document M-Basis Trim-konform convention in build.py header comment + drop logo_size_3M override (RED window opens)</name>
  <files>
  templates/kandidat-falzflyer-din-lang/build.py,
  templates/kandidat-falzflyer-din-lang/meta.yml
  </files>
  <action>
  Per RESEARCH locked decision #1 + #2: the brand rule `brand:logo_size_3M` at `tools/sla_lib/builder/brand_constraints.py:262` is ALREADY trim-konform (`min(page_w_mm, page_h_mm)`). The "M-Basis-Konflikt" is purely a misleading code comment in `templates/kandidat-falzflyer-din-lang/build.py:195-199` that says "kurze Kante=105 -> 18.9 mm Logo-Soll", contradicting the actual rule.

  DO NOT edit `tools/check_ci.py` (it has zero logo/alignment logic — RESEARCH correction #1).
  DO NOT edit `tools/sla_lib/builder/brand_constraints.py` (rule already correct — RESEARCH locked #1).

  Edit 1 — `templates/kandidat-falzflyer-din-lang/build.py:195-199` header comment block. Replace the existing comment that references "kurze Kante=105 -> 18.9 mm Logo-Soll" with text clarifying:
  - The Trim-konsistente Konvention: `M = 0.06 * min(trim_w, trim_h)` per Quickguide Section "Logo-Groessen".
  - Concrete: `min(297, 210) = 210` -> `M = 12.6` -> `3M = 37.8 mm` (the Print-Soll for outer-panel logos on this DIN-lang Zickzackfalz).
  - The brand rule lives in `tools/sla_lib/builder/brand_constraints.py` (`brand:logo_size_3M`); it is already trim-konsistent — V1 logo dims (38x22 / 38x34) match this Soll.
  - Cross-reference `shared/brand/DESIGN-SYSTEM-BRIEF.md` Section "Logo Print-Soll" for the convention.

  Edit 2 — `templates/kandidat-falzflyer-din-lang/meta.yml`: REMOVE the `brand:logo_size_3M` entry from the `brand_overrides` block. (Keep all other override entries — line_spacing_0.9, band_consistency, image_text_overlap, image_fills_frame, visual_adjacency_drift; the latter four are removed in T10 once V1 layout closes their root causes.)

  After these two edits, `structural_check kandidat-falzflyer-din-lang` will surface 3 logo violations (P1 20mm x 18mm, P2 16mm, P6 17mm vs 3M=37.8mm). This is the EXPECTED RED window — closed by T02 (which resizes those 3 logos before any more V1 work proceeds, so the window is short).

  CRITICAL: The 4 OTHER V1 templates (`wahlaufruf-postkarte-a6-quer`, `wahltag-tueranhaenger`, `themen-plakat-a3-quer`, `infostand-tent-card-a5-quer`) MUST stay green under the unchanged rule (they already do per RESEARCH live verification). T01 verification commands must confirm this.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix && python3 templates/kandidat-falzflyer-din-lang/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check themen-plakat-a3-quer && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer</automated>
  </verify>
  <done>
  - build.py header comment at lines ~195-199 updated to state Trim-konsistente convention with concrete numbers (210 -> M=12.6 -> 3M=37.8) and cross-reference to brand_constraints.py + brief.
  - `brand:logo_size_3M` override entry REMOVED from `meta.yml` brand_overrides.
  - `structural_check` for the 4 other V1 templates exits 0 (no new violations introduced).
  - `structural_check kandidat-falzflyer-din-lang` reports exactly 3 `brand:logo_size_3M` violations (the expected RED window — closed in T02).
  - NO edit to `tools/check_ci.py` or `tools/sla_lib/builder/brand_constraints.py`.
  - Commit: `21: chore(check-ci): document M-Basis Trim-konform convention + drop logo_size_3M override`
  </done>
</task>

<task type="auto">
  <name>Task 02: chore(kandidat-falzflyer): resize 3 logos that violate the Trim-konform M soll (closes RED window)</name>
  <files>
  templates/kandidat-falzflyer-din-lang/build.py
  </files>
  <action>
  Per RESEARCH locked #1: 3 ImageFrames in the current V0 build.py violate the trim-konsistent 3M=37.8mm rule. Resize each to w=38mm (within rule's 0.5mm tolerance) AND adjust position/height per the V1 frame inventory below. After T02 commit, `structural_check kandidat-falzflyer-din-lang` MUST exit 0 (RED window closes here — before any more V1 work).

  Frame 1 — `P1 Logo Gruene` (currently `x~6, y~4, w=20, h=18`, asset `gruene-logo-bund-dunkel.png` or similar):
  - Change anname to `P1 Logo Gruene (weiss)`.
  - Change asset to `shared/logos/gruene-weiss.png` (3.5:1 wordmark; verify file exists with `ls shared/logos/gruene-weiss.png` before commit; if absent, abort task and report).
  - Set `x_mm=6, y_mm=4, w_mm=38, h_mm=22` (frame is 38x22; rule tests w_mm only).
  - Layer stays `LAYER_BILDER` (=1).

  Frame 2 — `P2 Logo (klein)` (currently w~16):
  - DELETE this frame entirely (V1: Top-Band replaces it — RESEARCH frame-inventory note "DELETED in V1 (Top-Band replaces it)"; the actual Top-Band Polygon is added in T05).
  - Confirm no other build.py code references this frame's anname after deletion (grep build.py for "Logo (klein)" or whatever the current anname is).

  Frame 3 — `P6 Logo Gruene` (currently `w~17`, footer of P6):
  - Change anname to `P6 Logo Gruene (weiss)`.
  - Change asset to `shared/logos/gruene-weiss.png`.
  - Set `x_mm=228, y_mm=168, w_mm=38, h_mm=34` (centered around AXIS_P6_CENTER_X=247.5; per RESEARCH frame inventory: `247.5 - 38/2 = 228.5 ~ 228`).
  - Layer stays `LAYER_BILDER`.

  These edits go INSIDE the existing `_add_front` and `_add_back` helpers; NO build_template/build_preview split yet (that's T05). The full V1 layout (Top-Bands, Name-Card, Body-Backing, vollflaechig P6) is built later (T06-T08) but the 3 logo dims must be settled NOW so the rule is green for the rest of execution.

  Verify all 5 V1 templates pass `--all`.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix && ls shared/logos/gruene-weiss.png && python3 templates/kandidat-falzflyer-din-lang/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all</automated>
  </verify>
  <done>
  - `shared/logos/gruene-weiss.png` exists.
  - P1 Logo frame: anname `P1 Logo Gruene (weiss)`, asset `gruene-weiss.png`, w=38, h=22, x=6, y=4.
  - P2 Logo (klein) frame DELETED entirely from build.py; no leftover references.
  - P6 Logo frame: anname `P6 Logo Gruene (weiss)`, asset `gruene-weiss.png`, w=38, h=34, x=228, y=168.
  - `structural_check kandidat-falzflyer-din-lang` exit 0 (RED window closed — `brand:logo_size_3M` 0 violations).
  - `structural_check --all` exit 0 (no regression on the other 4 V1 templates).
  - Commit: `21: chore(kandidat-falzflyer): resize 3 logos to Trim-konform 3M=37.8mm soll (closes RED window)`
  </done>
</task>

<task type="auto">
  <name>Task 03: feat(builder): ParaStyle migration — 10 mutations + 4 NEW + meta.yml ci_overrides extend</name>
  <files>
  templates/kandidat-falzflyer-din-lang/build.py,
  templates/kandidat-falzflyer-din-lang/meta.yml
  </files>
  <action>
  Per RESEARCH locked #3 + the V1 ParaStyle table (RESEARCH section "V1 ParaStyle table"): mutate 10 existing falzflyer/* styles in-place AND register 4 NEW parallel styles. Edit `_add_styles(doc)` in `build.py`. Use REAL build.py names (locked #4); spec uses `themen-*`/`cover-name`/`url` — those are stubs; build.py uses `thema-*`/`cand-name`/`closer-url`.

  MUTATIONS (edit the 10 ParaStyle definitions in-place — change `align` and/or `fcolor` only; preserve font/fontsize/linesp etc. unless noted):

  1. `falzflyer/cand-name`: align 0->1, fcolor Dunkelgruen->White (P1 Name on Dunkelgruen card).
  2. `falzflyer/slogan`: align 0->1 (KEEP fcolor=Black; use slogan-on-green for P1 Name-Card per spec).
  3. `falzflyer/closer-headline`: align 0->1 (already White on Dunkelgruen).
  4. `falzflyer/closer-url`: align 0->1.
  5. `falzflyer/closer-datum`: align 0->1.
  6. `falzflyer/contact-headline`: align 0->1, fcolor Dunkelgruen->White (P6 vollflaechig).
  7. `falzflyer/contact-body`: align 0->1, fcolor Black->White (P6 2-Spalten on Dunkelgruen).
  8. `falzflyer/thema-body`: align 0->1, fontsize 9->10, linesp 11->13 (1.3x body convention; fcolor stays Black — themen panels on white).
  9. `falzflyer/impressum`: align 0->1, fcolor Black->White (P6 vollflaechig).
  10. `falzflyer/teaser-body`: KEEP align=0 (redaktioneller Charakter), fcolor Black->White (P2 Hellgruen-Backing). ONLY fcolor mutation.

  KEPT UNCHANGED: `falzflyer/teaser-headline` (align=0 redaktioneller), `falzflyer/thema-headline` (align=0; fcolor stays Dunkelgruen on white).

  NEW styles (4) — register via `doc.add_para_style(ParaStyle(...))` in `_add_styles`:

  A. `falzflyer/slogan-on-green`: font=Gotham Narrow Bold, fontsize=14, linesp=17, linesp_mode=0, align=1, fcolor=Gelb, language=de (P1 Name-Card slogan).

  B. `falzflyer/quote-on-green`: font=Vollkorn Black Italic, fontsize=18, linesp=20, linesp_mode=0, align=1, fcolor=White, language=de (Pull-Quote — REGISTER ONLY; no frame in V1; deferred per RESEARCH pitfall 15).

  C. `falzflyer/top-title`: font=Gotham Narrow Bold, fontsize=11, linesp=14, linesp_mode=0, align=0 (left-aligned within Top-Band per spec L76-80), fcolor=White, language=de (P2/P3/P4/P5 + P6 Top-Title tags).

  D. `falzflyer/themen-eyebrow`: font=Gotham Narrow Bold, fontsize=9, linesp=12, linesp_mode=0, align=0, fcolor=Dunkelgruen, language=de (P4/P5 Caps `THEMA 0X` + reused with frame fcolor=White override on P6 QR-Captions).

  Net: 12 V0 styles -> 16 V1 styles in falzflyer namespace.

  meta.yml — extend `ci_overrides.non_ci_styles` to list ALL 16 falzflyer/* styles. The list must include: cand-name, slogan, slogan-on-green, teaser-headline, teaser-body, thema-headline, thema-body, themen-eyebrow, top-title, quote-on-green, closer-headline, closer-datum, closer-url, contact-headline, contact-body, impressum.

  DO NOT add `falzflyer/contact-label` style — RESEARCH locked: deferred (pitfall 16).

  After T03 commit: V0 layout still in place (T06-T08 add the V1 frame additions); structural_check still exits 0 because mutations don't break existing frames; build runs clean.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix && python3 templates/kandidat-falzflyer-din-lang/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang && PYTHONPATH=tools python3 tools/sla_lib/builder/spec_check.py kandidat-falzflyer-din-lang || true</automated>
  </verify>
  <done>
  - 10 in-place ParaStyle mutations applied per the table above (9 align flips + teaser-body fcolor flip).
  - 4 NEW styles registered: `falzflyer/slogan-on-green`, `falzflyer/quote-on-green`, `falzflyer/top-title`, `falzflyer/themen-eyebrow`.
  - `falzflyer/teaser-headline` and `falzflyer/thema-headline` UNCHANGED.
  - `meta.yml` `ci_overrides.non_ci_styles` lists all 16 falzflyer/* styles.
  - build runs clean; introspecting `build_doc()._extra_para_styles` shows exactly 16 falzflyer/* styles.
  - structural_check exit 0.
  - Commit: `21: feat(builder): V1 ParaStyles — 10 mutations + 4 NEW (slogan-on-green, quote-on-green, top-title, themen-eyebrow)`
  </done>
</task>

<task type="auto">
  <name>Task 04: feat(builder): Universal Top-Band helper</name>
  <files>
  templates/kandidat-falzflyer-din-lang/build.py
  </files>
  <action>
  Add a module-level helper that emits the 31mm Dunkelgruen Top-Band Polygon for one of the 4 panels that get one (P1, P2, P4, P5). NO frames are placed in this task — the helper is callable scaffolding only; T06 (P1+P6) and T07 (P2+P3) and T08 (P4+P5) are where the helper is actually invoked.

  Function signature:
  - `_top_band(panel_index: int) -> Polygon`

  Routing logic (RESEARCH locked #6 + correction #3):
  - panel_index=0 (P1) — outer: x=-3, w=105, anname="P1 Top-Band"
  - panel_index=1 (P2) — inner: x=99, w=99, anname="P2 Top-Band"
  - panel_index=2 (P3) — raise ValueError("P3 is vollflaechig — use P3 Hintergrund polygon instead")
  - panel_index=3 (P4) — outer: x=-3, w=105, anname="P4 Top-Band"
  - panel_index=4 (P5) — inner: x=99, w=99, anname="P5 Top-Band"
  - panel_index=5 (P6) — raise ValueError("P6 is vollflaechig — use P6 Hintergrund polygon instead")

  All bands: y_mm=-3, h_mm=31, fill="Dunkelgruen", layer=LAYER_HINTERGRUND.

  Rationale per RESEARCH correction #3: Outer panels (P1/P4) extend +3mm into bleed-left + +3mm overshoot-right because they sit at the trim edge; inner panels (P2/P5) flush both folds because they are bounded by Falz-lines. P3 + P6 are vollflaechig Dunkelgruen (the polygon IS the top-band), so they don't need this helper — their `Hintergrund` polygon is added in T06 (P6 NEW) and is already there for P3 (V0 carries it).

  IMPORTANT: T04 must NOT change visual output. The helper is dormant scaffolding. structural_check + smoke must remain green.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix && python3 templates/kandidat-falzflyer-din-lang/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang && python3 -c "import sys; sys.path.insert(0, 'templates/kandidat-falzflyer-din-lang'); from build import _top_band; b = _top_band(0); assert b.x_mm == -3 and b.w_mm == 105 and b.h_mm == 31 and b.anname == 'P1 Top-Band', f'P1: {vars(b)}'; b = _top_band(1); assert b.x_mm == 99 and b.w_mm == 99 and b.anname == 'P2 Top-Band'; b = _top_band(3); assert b.x_mm == -3 and b.w_mm == 105 and b.anname == 'P4 Top-Band'; b = _top_band(4); assert b.x_mm == 99 and b.w_mm == 99 and b.anname == 'P5 Top-Band'; import unittest; tc = unittest.TestCase(); tc.assertRaises(ValueError, _top_band, 2); tc.assertRaises(ValueError, _top_band, 5); print('OK')"</automated>
  </verify>
  <done>
  - `_top_band(panel_index)` helper exists in build.py.
  - Returns Polygon with correct x/w/anname for indices 0, 1, 3, 4.
  - Raises ValueError for indices 2 (P3) and 5 (P6) — vollflaechig panels.
  - All bands have y=-3, h=31, fill="Dunkelgruen", layer=LAYER_HINTERGRUND.
  - No frames added to `_add_front` / `_add_back` in this task (helper only).
  - structural_check exit 0; build runs clean.
  - Commit: `21: feat(builder): Universal Top-Band helper for kandidat-falzflyer`
  </done>
</task>

<task type="auto">
  <name>Task 05: feat(builder): build_template/build_preview split + INJECT_MAP</name>
  <files>
  templates/kandidat-falzflyer-din-lang/build.py
  </files>
  <action>
  Mirror #20's pattern (just-merged at `.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/`; reference build at `templates/infostand-tent-card-a5-quer/build.py`). 5 changes:

  1. Rename current `build_doc()` body to `build_template()`. The function returns a Document with the geometric layout + frame definitions BUT no inline image data on the INJECT_MAP-managed photos.

  2. Add module-level `INJECT_MAP: dict[str, str]` mapping anname → library asset id:
     - "P1 Kandidat-Portrait" → "portrait_maria"
     - "P4 Thema 1 — Photo" → "themen_klimaschutz_solar"
     - "P4 Thema 2 — Photo" → "themen_soziales_kaffeehaus"
     - "P5 Thema 3 — Photo" → "themen_bildung_volksschule"
     - "P5 Thema 4 — Photo" → "themen_wirtschaft_handwerk"
     Note: em-dash (U+2014) in Thema annames per RESEARCH locked #4 and current build.py convention. Asset `themen_wirtschaft_handwerk` is already in central library at `shared/sample-images/themen/wirtschaft-handwerk.jpg` per RESEARCH correction #2 — NO need to copy a sample asset locally.

  3. Add `build_preview() -> Document`: calls `build_template()`, then iterates `doc.pages → page.items`, for each `ImageFrame` whose `anname` is in `INJECT_MAP`, calls `library.load(lib_id, optional=True)` and `library.inject_into_frame(frame, img, target_w_mm=frame.w_mm, target_h_mm=frame.h_mm)`. CRITICAL: read `frame.w_mm` and `frame.h_mm` LIVE per call — DO NOT hardcode target dimensions; this is the post-#24 idiom (RESEARCH "Don't Hand-Roll").

  4. Add `build_doc = build_template` alias (for structural_check + smoke + spec_check, which call build_doc and must see the layout WITHOUT inline image data).

  5. Update `def build(out_path=...) -> Path:` to call `build_preview()`; save returns Path as before.

  If P1 Kandidat-Portrait is currently injected via direct `_photo_inline()` call in `_add_front`, REMOVE that direct call (move responsibility to build_preview/INJECT_MAP). Same for any other ImageFrame that overlaps INJECT_MAP keys (the 4 themen photos remain frame-only in build_template; they get inline data via build_preview). The Themen 4 photo on P5 is NEW for V1 — the V0 build.py has no `P5 Thema 4 — Photo` frame yet; that frame is added in T08 along with the rest of the P4/P5 V1 layout. For T05, INJECT_MAP simply lists it; the resolver in build_preview tolerates missing frames gracefully (the iteration only injects when the frame exists).

  IMPORTANT: T05 must NOT change visual output beyond shifting the portrait inline-image path through the library helper (which preserves crop_focus + watermark behavior). structural_check + smoke must remain green.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix && python3 templates/kandidat-falzflyer-din-lang/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang && python3 -c "import sys; sys.path.insert(0, 'templates/kandidat-falzflyer-din-lang'); from build import build_template, build_preview, build_doc, INJECT_MAP; assert build_doc is build_template; assert callable(build_preview); assert isinstance(INJECT_MAP, dict) and len(INJECT_MAP) == 5; print('INJECT_MAP keys:', list(INJECT_MAP.keys()))" && python3 templates/_smoke/test_kandidat_falzflyer_din_lang.py</automated>
  </verify>
  <done>
  - `build_doc` is an alias for `build_template`.
  - `build_preview()` exists and re-injects photos via INJECT_MAP, reading `frame.w_mm`/`frame.h_mm` LIVE.
  - `INJECT_MAP` dict has exactly 5 entries with em-dash U+2014 literal.
  - `build()` calls `build_preview()`, saves, returns Path.
  - No direct `_photo_inline()` calls remain for any frame whose anname is in INJECT_MAP.
  - structural_check exit 0; smoke pass.
  - Commit: `21: feat(builder): build_template/build_preview split + INJECT_MAP for kandidat-falzflyer`
  </done>
</task>

<task type="auto">
  <name>Task 06: feat(kandidat-falzflyer): P1 cover + P6 Kontakt grüne Klammer</name>
  <files>
  templates/kandidat-falzflyer-din-lang/build.py
  </files>
  <action>
  Per RESEARCH frame inventory (section "V1 frame inventory — TARGET state"), build out P1 + P6 — the "gruene Klammer" outer pair. Edit `_add_front` (P1) and `_add_back` (P6) — DO NOT touch P2/P3/P4/P5 in this task (those are T07/T08).

  P1 (page0) — add/modify:

  1. Polygon `P1 Top-Band` via `_top_band(0)` -> x=-3, y=-3, w=105, h=31, fill=Dunkelgruen, layer=LAYER_HINTERGRUND.
  2. ImageFrame `P1 Logo Gruene (weiss)` already at x=6, y=4, w=38, h=22 (set in T02). Keep.
  3. ImageFrame `P1 Kandidat-Portrait`: change y 28 -> 34, h 105 -> 100; keep x=6, w=87 (per RESEARCH frame inventory and ISSUE.md L31). Frame stays in INJECT_MAP for build_preview.
  4. NEW Polygon `P1 Name-Card` at x=-3, y=134, w=105, h=79, fill=Dunkelgruen, layer=LAYER_HINTERGRUND. (Extends to bottom bleed: 134+79 = 213 = 210+3mm.)
  5. TextFrame `P1 Kandidat-Name` at x=6, y=142, w=87, h=18, style=`falzflyer/cand-name` (V1 mutated style: align=1 fcolor=White). Layer LAYER_TEXT.
  6. TextFrame `P1 Slogan` at x=6, y=164, w=87, h=20, style=`falzflyer/slogan-on-green` (NEW style: Gelb, align=1). Layer LAYER_TEXT.

  P6 (page1) — add/modify:

  1. NEW Polygon `P6 Hintergrund` at x=198, y=-3, w=102, h=216, fill=Dunkelgruen, layer=LAYER_HINTERGRUND (vollflaechig analog to P3 — RESEARCH correction #3 / locked #5).
  2. NEW TextFrame `P6 Top-Title` at x=204, y=8, w=87, h=14, style=`falzflyer/top-title`, text="Kontakt", layer=LAYER_TEXT.
  3. TextFrame `P6 Kontakt-Headline`: change y 20 -> 38, h to 14; style stays `falzflyer/contact-headline` (V1 mutated: align=1 fcolor=White); text="Sprich mich an" (or current spec text).
  4. SPLIT existing P6 Kontakt-Adresse + Email + Telefon + Sprechtag into 4 cells:
     - `P6 Adresse`: x=204, y=62, w=41, h=20, style=`falzflyer/contact-body` (V1 mutated).
     - `P6 Telefon`: x=250, y=62, w=41, h=20, style=`falzflyer/contact-body`.
     - `P6 Email`:   x=204, y=90, w=41, h=20, style=`falzflyer/contact-body`.
     - `P6 Sprechtag`: x=250, y=90, w=41, h=20, style=`falzflyer/contact-body`.
     Note: anname change from V0 (rename whatever existing kontakt-text frames to these 4 new annames).
  5. ImageFrame `P6 QR-Code (mitmachen)`: keep asset `samples/qr-mitmachen.png`; resize to x=218, y=128, w=24, h=24 (RESEARCH inventory: w 30->24, x 210->218 to center on col_left mirror axis).
  6. NEW TextFrame `P6 QR-Caption (mitmachen)`: x=218, y=154, w=24, h=6, style=`falzflyer/themen-eyebrow`, fcolor="White" (per-frame override), text="MITMACHEN".
  7. ImageFrame `P6 QR-Code (termine)`: keep asset `samples/qr-termine.png`; resize to x=254, y=128, w=24, h=24.
  8. NEW TextFrame `P6 QR-Caption (termine)`: x=254, y=154, w=24, h=6, style=`falzflyer/themen-eyebrow`, fcolor="White", text="TERMINE".
  9. ImageFrame `P6 Logo Gruene (weiss)` already at x=228, y=168, w=38, h=34 (set in T02). Keep.
  10. TextFrame `P6 Impressum`: change h 60 -> 8, y -> 200 (per inventory); style stays `falzflyer/impressum` (V1 mutated: align=1 fcolor=White).

  P3 + P6 vollflaechig anchoring: P3 already has `P3 Hintergrund` polygon; ensure it's named exactly `P3 Hintergrund` (rename if needed). The CONSTRAINTS list in T10 will reference both `P3 Hintergrund` and `P6 Hintergrund` for the gruene-Klammer same_size constraint.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix && python3 templates/kandidat-falzflyer-din-lang/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang</automated>
  </verify>
  <done>
  - P1 frames: Top-Band Polygon (105x31), Logo (38x22 from T02), Portrait (87x100 at y=34), Name-Card Polygon (105x79 vollbleed bottom), Kandidat-Name (cand-name V1), Slogan (slogan-on-green NEW).
  - P6 frames: Hintergrund Polygon (102x216 vollflaechig), Top-Title (Kontakt), Kontakt-Headline (y=38), 4 cells (Adresse/Telefon/Email/Sprechtag — 2 cols mirrored), 2 QRs (24x24 each), 2 QR-Captions (themen-eyebrow with white override), Logo (38x34 from T02), Impressum (h=8 fcolor=White).
  - structural_check exit 0 (CONSTRAINTS list still has V0 entries; no new constraint violations because the V0 list doesn't reference the new annames yet).
  - Commit: `21: feat(kandidat-falzflyer): P1 cover + P6 Kontakt gruene Klammer (V1)`
  </done>
</task>

<task type="auto">
  <name>Task 07: feat(kandidat-falzflyer): P2 Mein Plan + P3 Wahltag (front)</name>
  <files>
  templates/kandidat-falzflyer-din-lang/build.py
  </files>
  <action>
  Per RESEARCH frame inventory section "Page 0 (Front)": apply V1 deltas to P2 and P3 in `_add_front`. P1 is already V1 (T06).

  P2 (Mein Plan) — modify:

  1. P2 Logo (klein) frame already DELETED in T02 — verify no leftover; if any P2 logo frame still exists, delete it.
  2. Polygon `P2 Top-Band` via `_top_band(1)` -> x=99, y=-3, w=99, h=31, fill=Dunkelgruen.
  3. NEW TextFrame `P2 Top-Title` at x=105, y=8, w=87, h=14, style=`falzflyer/top-title`, text="Mein Plan".
  4. TextFrame `P2 Teaser-Headline`: change y 20 -> 38, h=22; style stays `falzflyer/teaser-headline` (UNCHANGED V0 style; redaktioneller).
  5. NEW Polygon `P2 Body-Backing` at x=99, y=66, w=99, h=144, fill=Hellgruen, layer=LAYER_HINTERGRUND.
  6. TextFrame `P2 Teaser-Body`: change x 105 -> 113 (inset +8mm for visual breathing inside Hellgruen card), y -> 72, w 87 -> 73, h 130; style stays `falzflyer/teaser-body` (V1: fcolor=White from T03; align=0 KEEP).

  P3 (Wahltag) — modify:

  1. Polygon `P3 Hintergrund` (vollflaechig Dunkelgruen) UNCHANGED — already x=198, y=-3, w=102, h=216 in V0. If anname differs, rename to exactly `P3 Hintergrund`.
  2. NEW TextFrame `P3 Top-Title` at x=204, y=8, w=87, h=14, style=`falzflyer/top-title`, fcolor="Gelb" (per-frame override per RESEARCH inventory note + ISSUE.md L33), text="Wahltag".
  3. ImageFrame `P3 Wahlkreuz`: change y 30 -> 44 (UNCHANGED size 50x50; UNCHANGED asset `shared/assets/wahlkreuz.png`).
  4. TextFrame `P3 Closer-Headline`: change y 90 -> 100, h=32; style `falzflyer/closer-headline` (V1: align=1).
  5. TextFrame `P3 Datum-Akzent`: change y 125 -> 145, h=22; style `falzflyer/closer-datum` (V1: align=1).
  6. TextFrame `P3 URL` (or whatever V0 anname): change y 175 -> 185, h=12; style `falzflyer/closer-url` (V1: align=1). Rename anname to `P3 URL` if differs.

  Fold lines `Falz x=99 (Front)` and `Falz x=198 (Front)` UNCHANGED.

  Smoke test note: T11 must extend `test_panel_content_within_safe_width` skip-prefixes to include "Top-Band", "Body-Backing", "Top-Title" etc. — NOT this task. T06 leaves smoke as-is and accepts that the smoke filter may need updating in T11; if smoke fails on a "Top-Band" frame here, T06 verify command may need `|| true` and T11 fixes it. RESEARCH recommends: extend the smoke skip-prefixes inline in T11 — verify smoke after T11.

  HOWEVER: V1 Top-Band annames pass the existing filter (which already skips "Hintergrund" + "Wahlkreuz" prefixes — Top-Band is a different prefix). If smoke fails after T06/T07/T08 on Top-Band/Body-Backing frames, defer the fix to T11; for these tasks, run only structural_check.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix && python3 templates/kandidat-falzflyer-din-lang/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang</automated>
  </verify>
  <done>
  - P2 Logo frame absent (verified by grep).
  - P2 Top-Band Polygon (99x31 Dunkelgruen), Top-Title TextFrame ("Mein Plan"), Teaser-Headline at y=38, Body-Backing Polygon (99x144 Hellgruen), Teaser-Body inset (x=113, w=73, fcolor=White via mutated style).
  - P3 Hintergrund anname normalized to `P3 Hintergrund`. Top-Title TextFrame with fcolor="Gelb" override, text="Wahltag". Wahlkreuz at y=44. Closer-Headline at y=100. Datum-Akzent at y=145. URL at y=185.
  - structural_check exit 0.
  - Commit: `21: feat(kandidat-falzflyer): P2 Mein Plan + P3 Wahltag (V1)`
  </done>
</task>

<task type="auto">
  <name>Task 08: feat(kandidat-falzflyer): P4 + P5 Themen (back)</name>
  <files>
  templates/kandidat-falzflyer-din-lang/build.py
  </files>
  <action>
  Per RESEARCH frame inventory section "Page 1 (Back)": rebuild P4 and P5 themen sub-layouts in `_add_back`. P6 is already V1 (T06).

  P4 (Themen 1+2) — replace V0 themen frames:

  1. Polygon `P4 Top-Band` via `_top_band(3)` -> x=-3, y=-3, w=105, h=31, fill=Dunkelgruen.
  2. NEW TextFrame `P4 Top-Title` at x=6, y=8, w=87, h=14, style=`falzflyer/top-title`, text="Themen 1·2" (note: middle-dot U+00B7).
  3. NEW TextFrame `P4 Thema 1 — Eyebrow` at x=6, y=38, w=87, h=6, style=`falzflyer/themen-eyebrow`, text="THEMA 01".
  4. TextFrame `P4 Thema 1 — Headline`: x=6, y=46, w=87, h=14, style=`falzflyer/thema-headline` (UNCHANGED V0 style).
  5. ImageFrame `P4 Thema 1 — Photo`: x=6, y=62, w=87, h=44 (was h=24 — RESEARCH inventory + ISSUE.md L36: photos h 24->44 closer to native 1.5:1, fixes today's halb-leer Streifen). Frame is in INJECT_MAP -> `themen_klimaschutz_solar`.
  6. NEW Polygon `P4 Thema 1·2 Trenner` at x=-3, y=108, w=105, h=3, fill=Hellgruen, layer=LAYER_HINTERGRUND (3mm strip per ISSUE.md L36).
  7. TextFrame `P4 Thema 1 — Body`: x=6, y=114, w=87, h=26, style=`falzflyer/thema-body` (V1: align=1, fontsize=10, linesp=13).
  8. NEW TextFrame `P4 Thema 2 — Eyebrow` at x=6, y=144, w=87, h=6, style=`falzflyer/themen-eyebrow`, text="THEMA 02".
  9. TextFrame `P4 Thema 2 — Headline`: x=6, y=152, w=87, h=14, style=`falzflyer/thema-headline`.
  10. ImageFrame `P4 Thema 2 — Photo`: x=6, y=168, w=87, h=44. Frame in INJECT_MAP -> `themen_soziales_kaffeehaus`.
  11. DELETE any V0 `P4 Thema 2 — Body` frame entirely (RESEARCH locked: "Body wandert auf Innenseite Cover oder entfaellt"; for V1 we DELETE — ISSUE.md L37).

  P5 (Themen 3+4) — mirror structure:

  1. Polygon `P5 Top-Band` via `_top_band(4)` -> x=99, y=-3, w=99, h=31.
  2. NEW TextFrame `P5 Top-Title` at x=105, y=8, w=87, h=14, style=`falzflyer/top-title`, text="Themen 3·4".
  3. NEW TextFrame `P5 Thema 3 — Eyebrow` at x=105, y=38, w=87, h=6, style=`falzflyer/themen-eyebrow`, text="THEMA 03".
  4. TextFrame `P5 Thema 3 — Headline`: x=105, y=46, w=87, h=14, style=`falzflyer/thema-headline`.
  5. ImageFrame `P5 Thema 3 — Photo`: x=105, y=62, w=87, h=44. INJECT_MAP -> `themen_bildung_volksschule`.
  6. NEW Polygon `P5 Thema 3·4 Trenner` at x=99, y=108, w=99, h=3, fill=Hellgruen.
  7. TextFrame `P5 Thema 3 — Body`: x=105, y=114, w=87, h=26, style=`falzflyer/thema-body`.
  8. NEW TextFrame `P5 Thema 4 — Eyebrow` at x=105, y=144, w=87, h=6, style=`falzflyer/themen-eyebrow`, text="THEMA 04".
  9. TextFrame `P5 Thema 4 — Headline`: x=105, y=152, w=87, h=14, style=`falzflyer/thema-headline`.
  10. NEW ImageFrame `P5 Thema 4 — Photo`: x=105, y=168, w=87, h=44, layer=LAYER_BILDER. INJECT_MAP -> `themen_wirtschaft_handwerk` (asset already in central library per RESEARCH locked #7 + correction #2; NO sample copy needed). NO V0 `P5 Thema 4 — Body` (V0 had no thema 4 photo and an empty-slot conditional; V1 has photo + no body — same delete pattern as P4 Thema 2).
  11. DELETE any V0 `P5 Thema 4 — Body` if present.

  Fold lines `Falz x=99 (Back)` and `Falz x=198 (Back)` UNCHANGED.

  After T07: 4 themen photos all 87x44; P4 has 1 body (Thema 1), P5 has 1 body (Thema 3); both panels have 4 thema cells each (eyebrow+headline+photo for both, plus body for first thema only).
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix/ && python3 templates/kandidat-falzflyer-din-lang/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang</automated>
  </verify>
  <done>
  - P4: Top-Band Polygon, Top-Title TextFrame, 2x (Eyebrow + Headline + Photo h=44), Trenner Polygon Hellgruen 3mm, 1 Body (Thema 1 only). NO Thema 2 Body.
  - P5: Top-Band Polygon, Top-Title TextFrame, 2x (Eyebrow + Headline + Photo h=44 — Thema 4 photo NEW), Trenner Polygon Hellgruen 3mm, 1 Body (Thema 3 only). NO Thema 4 Body.
  - All 4 themen photos w=87, h=44 (cross-panel uniform), em-dash annames literal U+2014.
  - INJECT_MAP entries resolve and inject into all 4 themen photos via build_preview.
  - structural_check exit 0.
  - Commit: `21: feat(kandidat-falzflyer): P4 + P5 Themen sub-layouts (V1)`
  </done>
</task>

<task type="auto">
  <name>Task 09: feat(builder): V1 CONSTRAINTS list (22 entries — replaces V0's 9)</name>
  <files>
  templates/kandidat-falzflyer-din-lang/build.py
  </files>
  <action>
  Replace the existing V0 `CONSTRAINTS = [...]` block at module bottom of build.py with the V1 list per RESEARCH section "V1 CONSTRAINTS list". Use REAL annames (locked #4) — em-dash literal U+2014.

  V1 CONSTRAINTS list (22 entries):

  Top-Band uniformity (4 explicit polygons; P3 + P6 vollflaechig handled via inside):
  - same_size("P1 Top-Band", "P2 Top-Band", "P4 Top-Band", "P5 Top-Band", axis="h", name="top_bands_uniform_h")
  - inside("P3 Top-Title", "P3 Hintergrund", name="p3_top_title_anchored")
  - inside("P6 Top-Title", "P6 Hintergrund", name="p6_top_title_anchored")

  P1 P6 gruene-Klammer:
  - same_size("P3 Hintergrund", "P6 Hintergrund", name="gruene_klammer_p3_p6")

  P4 themen sub-layout mirror (Thema 1 vs 2 within panel):
  - same_x("P4 Thema 1 — Eyebrow", "P4 Thema 2 — Eyebrow", name="p4_eyebrow_x")
  - same_x("P4 Thema 1 — Headline", "P4 Thema 2 — Headline", name="p4_headline_x")
  - same_x("P4 Thema 1 — Photo", "P4 Thema 2 — Photo", name="p4_photo_x")
  - same_size("P4 Thema 1 — Photo", "P4 Thema 2 — Photo", name="p4_photos_size")
  - aligned_below("P4 Thema 1 — Photo", "P4 Thema 1 — Headline", gap_mm=2.0, name="p4_t1_photo_anchored")

  P5 themen sub-layout mirror (Thema 3 vs 4 within panel):
  - same_x("P5 Thema 3 — Eyebrow", "P5 Thema 4 — Eyebrow", name="p5_eyebrow_x")
  - same_x("P5 Thema 3 — Headline", "P5 Thema 4 — Headline", name="p5_headline_x")
  - same_x("P5 Thema 3 — Photo", "P5 Thema 4 — Photo", name="p5_photo_x")
  - same_size("P5 Thema 3 — Photo", "P5 Thema 4 — Photo", name="p5_photos_size")
  - aligned_below("P5 Thema 3 — Photo", "P5 Thema 3 — Headline", gap_mm=2.0, name="p5_t3_photo_anchored")

  Cross-panel (4 themen photos same w x h):
  - same_size("P4 Thema 1 — Photo", "P5 Thema 3 — Photo", name="cross_panel_themen_photos_size")

  P6 Kontakt 2-Spalten symmetric around AXIS_P6_CENTER_X = 247.5:
  - mirrored_x("P6 Adresse", "P6 Telefon", axis_mm=247.5, name="p6_col_mirror_row1")
  - mirrored_x("P6 Email", "P6 Sprechtag", axis_mm=247.5, name="p6_col_mirror_row2")
  - same_y("P6 Adresse", "P6 Telefon", name="p6_baseline_row1")
  - same_y("P6 Email", "P6 Sprechtag", name="p6_baseline_row2")
  - same_size("P6 Adresse", "P6 Telefon", "P6 Email", "P6 Sprechtag", axis="both", name="p6_kontakt_cells_uniform")
  - mirrored_x("P6 QR-Code (mitmachen)", "P6 QR-Code (termine)", axis_mm=247.5, name="p6_qr_mirror")
  - same_size("P6 QR-Code (mitmachen)", "P6 QR-Code (termine)", name="p6_qrs_size")

  Logo Print-Soll consistency:
  - same_size("P1 Logo Gruene (weiss)", "P6 Logo Gruene (weiss)", axis="w", name="logos_print_soll_w_uniform")

  Style consistency:
  - same_style("P4 Thema 1 — Headline", "P4 Thema 2 — Headline", "P5 Thema 3 — Headline", "P5 Thema 4 — Headline", name="thema_headline_style_consistent")
  - same_style("P4 Thema 1 — Body", "P5 Thema 3 — Body", name="thema_body_style_consistent")

  Total: 22 constraints (vs V0's 9; matches #20's 22).

  CRITICAL: All anname strings must EXACTLY match the frame annames added in T06/T07/T08 (em-dash U+2014 literal in Thema annames; case-sensitive; spaces preserved).

  After commit: `structural_check kandidat-falzflyer-din-lang` must exit 0 with all 22 CONSTRAINTS listed as PASS in the report. If ANY constraint fires a violation, the geometry in T06/T07/T08 has an inconsistency — fix the frame coordinates, NOT the constraint.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix && python3 templates/kandidat-falzflyer-din-lang/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang && python3 -c "import sys; sys.path.insert(0, 'templates/kandidat-falzflyer-din-lang'); from build import CONSTRAINTS; assert len(CONSTRAINTS) == 22, f'expected 22 constraints, got {len(CONSTRAINTS)}'; names = sorted(c.name for c in CONSTRAINTS); print('CONSTRAINTS:', len(names)); [print('  -', n) for n in names]"</automated>
  </verify>
  <done>
  - `CONSTRAINTS` list contains exactly 22 entries with the names listed above.
  - All 22 use REAL annames (em-dash U+2014, case-sensitive, exact spaces).
  - `structural_check kandidat-falzflyer-din-lang` exit 0; all 22 constraints PASS in the report.
  - Commit: `21: feat(builder): V1 CONSTRAINTS list (22 entries — top-bands + themen mirror + P6 columns + logos)`
  </done>
</task>

<task type="auto">
  <name>Task 10: chore(kandidat-falzflyer): regen template.sla + page-01..06.png + preview.pdf + brand_overrides cleanup + slots rewrite</name>
  <files>
  templates/kandidat-falzflyer-din-lang/template.sla,
  templates/kandidat-falzflyer-din-lang/page-01.png,
  templates/kandidat-falzflyer-din-lang/page-02.png,
  templates/kandidat-falzflyer-din-lang/preview.pdf,
  templates/kandidat-falzflyer-din-lang/meta.yml,
  site/public/kandidat-falzflyer-din-lang/
  </files>
  <action>
  Regenerate emitted artifacts and prune now-unnecessary brand_overrides.

  Step 1 — regen artifacts:
  Run `bin/render-gallery kandidat-falzflyer-din-lang --skip-visual-diff`. This regenerates template.sla, page-01.png, page-02.png, preview.pdf, bumps the SHA in meta.yml, and mirrors output to site/public/kandidat-falzflyer-din-lang/. Per RESEARCH "Standard Stack". Verify exit 0.

  Step 2 — verify artifacts current:
  Run `bin/check-stale-previews`. Must exit 0 (no SHA drift between meta.yml and emitted artifacts).

  Step 3 — empirical brand_overrides cleanup. Per RESEARCH locked: drop 4 entries (image_text_overlap, image_fills_frame, visual_adjacency_drift; logo_size_3M was already dropped in T01). Per the user prompt's empirical guidance: "for each existing override, run structural_check after removal; if it fires, RESTORE with updated reason". Procedure:

  For each of these 4 override stanzas in `templates/kandidat-falzflyer-din-lang/meta.yml.brand_overrides`:
  - `brand:image_text_overlap`
  - `brand:image_fills_frame`
  - `brand:visual_adjacency_drift`

  (Note: logo_size_3M already dropped in T01.)

  For each: REMOVE the stanza, run `structural_check kandidat-falzflyer-din-lang`. If exit 0 -> override successfully removed (V1 layout closes the underlying violation). If exit non-zero -> RESTORE the stanza with an updated `reason:` field documenting the V1-specific finding.

  KEEP per RESEARCH: `brand:line_spacing_0.9` (V1 still uses tight linesp on some teaser/closer styles), `brand:band_consistency` (V1 still has minor ParaStyle band drift on the eyebrow Caps).

  Expected end state: meta.yml.brand_overrides has 2 entries (`line_spacing_0.9`, `band_consistency`); structural_check report shows "0 errors / 0 warnings / 2 overrides".

  Step 4 — re-run render-gallery one more time after the cleanup (so meta.yml SHA reflects the final overrides state) IF render-gallery rebuilds anything based on overrides; otherwise skip. Verify check-stale-previews exit 0.

  Step 5 — slots manifest rewrite (if `meta.yml.slots:` exists in current build): the V1 layout has different anname set; if `meta.yml.slots:` enumerates frames, rewrite to match V1 frame inventory (per RESEARCH frame inventory). Per the user prompt: "slots rewrite". If meta.yml does NOT have a `slots:` key, this step is a no-op.

  After this task: ALL emitted artifacts reflect V1 layout; meta.yml has 2 brand overrides; structural_check + check-stale-previews + structural_check --all all exit 0.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix && bin/render-gallery kandidat-falzflyer-din-lang --skip-visual-diff && bin/check-stale-previews && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all</automated>
  </verify>
  <done>
  - template.sla, page-01.png, page-02.png, preview.pdf regenerated; meta.yml SHA updated.
  - site/public/kandidat-falzflyer-din-lang/ mirror updated.
  - meta.yml.brand_overrides: 2 entries (`line_spacing_0.9`, `band_consistency`); 4 removed (`logo_size_3M` from T01, `image_text_overlap` + `image_fills_frame` + `visual_adjacency_drift` from T10).
  - meta.yml.slots rewritten (if present) to V1 anname set; or no-op if absent.
  - bin/check-stale-previews exit 0.
  - structural_check kandidat-falzflyer-din-lang exit 0.
  - structural_check --all exit 0.
  - Commit: `21: chore(kandidat-falzflyer): regen V1 artifacts + brand_overrides cleanup`
  </done>
</task>

<task type="auto">
  <name>Task 11: test(builder): smoke + geometry tests + spec rewrite + README + brief Section 10 + HANDOFF V1 close + EXECUTION close + status flip</name>
  <files>
  templates/_smoke/test_kandidat_falzflyer_din_lang.py,
  tools/sla_lib/tests/test_kandidat_falzflyer_geometry.py,
  templates/_specs/kandidat-falzflyer-din-lang.md,
  templates/kandidat-falzflyer-din-lang/README.md,
  shared/brand/DESIGN-SYSTEM-BRIEF.md,
  improvements/HANDOFF.md,
  .issues/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix/EXECUTION.md,
  .issues/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix/ISSUE.md
  </files>
  <action>
  Final omnibus task: tests + docs + HANDOFF close + status flip. Split into commits if it improves reviewability (e.g. test commit, docs commit, status commit), but the user's prompt T11 lists this as one task — keep it one task with 3 commits is acceptable.

  PART A — Smoke test extension. Edit `templates/_smoke/test_kandidat_falzflyer_din_lang.py`:

  1. Extend the skip-prefixes filter in `test_panel_content_within_safe_width` (or whatever its current name) from the V0 `("Hintergrund", "Wahlkreuz")` to:
     `("Hintergrund", "Wahlkreuz", "Top-Band", "Body-Backing", "Name-Card", "Trenner", "Top-Title")`
     (per RESEARCH pitfall 7).
  2. ADD V1-specific assertions while preserving all 11 existing assertions (no rewrite from scratch — RESEARCH "Don't Hand-Roll"):
     - All 5 INJECT_MAP frame annames present in the doc.
     - 4 Top-Band Polygons present (P1, P2, P4, P5).
     - P3 Hintergrund + P6 Hintergrund Polygons present (vollflaechig pair).
     - Falz LAYER (=3) only contains 4 PAGEOBJECTs (the 4 fold lines), 0 spillover (lxml XPath `//PAGEOBJECT[@LAYER="3"]` count == 4).
  3. Total smoke assertions: 11 V0 + ~5 V1 -> ~16 total. Run; must pass.

  PART B — NEW geometry test file `tools/sla_lib/tests/test_kandidat_falzflyer_geometry.py`. Mirror the 21-invariant pattern at `tools/sla_lib/tests/test_infostand_tent_card_geometry.py` (read it for structure). MINIMUM 18 invariants. Mandatory coverage per the user prompt:

  1. 4-panel Top-Band uniform height (P1, P2, P4, P5 all h_mm == 31).
  2. P1 Top-Band outer-bleed extends to x=-3, w=105.
  3. P2 Top-Band inner flush x=99, w=99.
  4. P4 Top-Band x=-3, w=105.
  5. P5 Top-Band x=99, w=99.
  6. P3 Hintergrund vollflaechig (x=198, y=-3, w=102, h=216).
  7. P6 Hintergrund vollflaechig (x=198, y=-3, w=102, h=216).
  8. P1 P6 gruene-Klammer same_size on `P3 Hintergrund` vs `P6 Hintergrund` (102x216 both).
  9. P4 themen sub-layout mirror: Thema 1+2 photos same w x h (87x44 each).
  10. P5 themen sub-layout mirror: Thema 3+4 photos same w x h (87x44 each).
  11. Cross-panel themen photos: all 4 photos w=87, h=44.
  12. P6 column-symmetry mirrored_x at axis_mm=247.5 — Adresse vs Telefon, Email vs Sprechtag, QR-mitmachen vs QR-termine.
  13. P6 baseline same_y: Adresse + Telefon same y; Email + Sprechtag same y.
  14. Logo Print-Soll same_size: P1 + P6 logos w_mm=38 within 0.5mm.
  15. P2 Logo absent (negative assertion: no frame with anname matching r"P2 Logo").
  16. Falz LAYER integrity via lxml XPath: assert exactly 4 PAGEOBJECTs on LAYER=3 (2 per page) AND no LAYER=3 PAGEOBJECTs of type other than the fold-line equivalent. (Save build_preview to a tmp file then parse with lxml.etree.)
  17. ParaStyle existence: 16 falzflyer/* styles registered in build_doc()._extra_para_styles.
  18. teaser-body retains align=0 contract (mutation only on fcolor).
  19. M-Basis-rule regression: PARAMETRIC test running `brand:logo_size_3M` against ALL 5 V1 templates' `build_doc()`s — assert 0 violations on each. (Use a parametrized loop or 5 named test methods.)
  20. P3 Top-Title fcolor="Gelb" override is set (intra-band placement y <= 28).
  21. INJECT_MAP frame annames are all present in the doc with the expected library asset ids.

  Use Python `unittest.TestCase`. Test file must be discoverable by `python3 -m unittest discover tools/sla_lib/tests`. Total: at least 18 invariants; aim for 21 to match #20.

  PART C — Spec rewrite at `templates/_specs/kandidat-falzflyer-din-lang.md`. Per RESEARCH locked #12 + #18 spec-rewrite precedent at `templates/_specs/wahltag-tueranhaenger.md`. Replace the V0 spec (675 lines, drifted) with V1 spec covering:
  - 6-panel layout overview + Falz x=99/198 geometry.
  - Universal Top-Band system (4 explicit + 2 vollflaechig).
  - 16 ParaStyles (table form: name, font, fontsize, linesp, align, fcolor, language, usage panel(s)).
  - V1 frame inventory (use the table from RESEARCH section "V1 frame inventory — TARGET state").
  - 22 CONSTRAINTS listing (annames + axis + reason).
  - Brand Compliance section: M-Basis-Konflikt resolution narrative (Trim-konsistent 3M=37.8mm; rule already in brand_constraints.py; 3 logos resized in #21 T02; build.py header comment fixed in T01).
  - INJECT_MAP photo bindings (5 entries: portrait + 4 themen).
  - Print Production zones + bleed + safe-area notes.

  PART D — README at `templates/kandidat-falzflyer-din-lang/README.md` (NEW file). Document:
  - V1 deltas vs V0 (3 logo resizes; 4 Top-Bands; P1 Name-Card; P2 Body-Backing; P6 vollflaechig; 22 constraints; INJECT_MAP).
  - M-Basis decision rationale: "Per Quickguide §"Logo-Groessen": M = 0.06 * min(trim_w, trim_h). For 297x210, min=210, 3M=37.8mm. Rule already correctly implemented in tools/sla_lib/builder/brand_constraints.py:262 (trim-konsistent). V0 build.py header comment was misleading; corrected in T01. No tool/library code change."
  - Visual rendering of P1 + P6 logos (3.5:1 wordmark in 38x22 / 38x34 frames -> auto-fit width, padding above/below; same treatment as #20).
  - Asset library bindings (5 ids).
  - Spec at `templates/_specs/kandidat-falzflyer-din-lang.md`.
  - Build: `python3 templates/kandidat-falzflyer-din-lang/build.py`.
  - Regen: `bin/render-gallery kandidat-falzflyer-din-lang --skip-visual-diff`.

  PART E — Append Section 10 row to `shared/brand/DESIGN-SYSTEM-BRIEF.md` Session-History table. Use date 2026-05-09. Mark V1 rollout sequence COMPLETE (5th of 5):

  Row format (match existing rows in §10):
  - Date: 2026-05-09
  - Session: V1 rollout #21 — kandidat-falzflyer-din-lang Falz-Rhythm + M-Basis fix
  - Resulting issue: #21 (closed)
  - Outcome: 5/5 V1 templates complete; M-Basis-Konflikt resolved (no tool change — comment fix + 3 logo resizes per Trim-konsistent rule already in brand_constraints.py).

  Update the .md Session-History `Resulting issue` field in any preceding row that referenced #21 as pending.

  PART F — Update `improvements/HANDOFF.md`. Mark V1 rollout sequence (#15 tracking issue) COMPLETE. Per ISSUE.md AC L98. Find the V1 rollout checklist/section (5 items: #17, #18, #19, #20, #21) and check off #21; mark the overall sequence complete.

  PART G — Final EXECUTION.md update at `.issues/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix/EXECUTION.md`. Mark all 11 tasks (T01-T11) as `[x]` complete with completion dates + commit hashes. Add final summary section.

  PART H — ISSUE.md status flip. Edit `.issues/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix/ISSUE.md` frontmatter: change `status: open` -> `status: done`.

  Commits (suggested split):
  - `21: test(builder): smoke + geometry tests for V1 falzflyer (18+ invariants)`
  - `21: docs(kandidat-falzflyer): spec rewrite + README + brief Section 10 + HANDOFF V1 close`
  - `21: chore(issue): mark issue 21 done + EXECUTION close`
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix && python3 -m unittest discover tools/sla_lib/tests && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all && bin/check-stale-previews && python3 templates/_smoke/test_kandidat_falzflyer_din_lang.py && python3 -m unittest tools.sla_lib.tests.test_kandidat_falzflyer_geometry -v</automated>
  </verify>
  <done>
  - Smoke test: skip-prefixes extended to 7 prefixes; 5+ new V1 assertions added; all assertions pass.
  - NEW geometry test file at `tools/sla_lib/tests/test_kandidat_falzflyer_geometry.py` with at least 18 invariants (target 21 to match #20); all pass.
  - Geometry test includes: 4-panel Top-Band uniform h, P1 P6 gruene-Klammer same_size, P4/P5 themen mirror, P6 column-symmetry mirrored_x at 247.5, Falz LAYER integrity via lxml XPath, M-Basis-rule regression on all 5 V1 templates (parametric).
  - Spec rewritten at `templates/_specs/kandidat-falzflyer-din-lang.md` per V1 anname set + zones + 22 constraints + M-Basis narrative.
  - NEW README at `templates/kandidat-falzflyer-din-lang/README.md` with V1 deltas + M-Basis decision rationale.
  - Section 10 row appended to `shared/brand/DESIGN-SYSTEM-BRIEF.md` dated 2026-05-09 marking V1 rollout COMPLETE.
  - HANDOFF.md V1 rollout sequence (#15) marked complete.
  - EXECUTION.md all tasks `[x]`.
  - ISSUE.md `status: done`.
  - All verification commands exit 0.
  - Commits: `21: test(builder): smoke + geometry tests for V1 falzflyer (18+ invariants)`, `21: docs(kandidat-falzflyer): spec rewrite + README + brief Section 10 + HANDOFF V1 close`, `21: chore(issue): mark issue 21 done + EXECUTION close`.
  </done>
</task>

</tasks>

<verification>
After all 11 tasks complete (T01-T11), run final verification gate. ALL must exit 0:

```
cd /root/workspace/.worktrees/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix
python3 -m unittest discover tools/sla_lib/tests
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
bin/check-stale-previews
python3 templates/_smoke/test_kandidat_falzflyer_din_lang.py
python3 -m unittest tools.sla_lib.tests.test_kandidat_falzflyer_geometry -v
```

Plus:
- New `test_kandidat_falzflyer_geometry.py` 18+ tests pass.
- EXECUTION.md all 11 tasks `[x]`.
- ISSUE.md `status: done`.
- HANDOFF.md V1 rollout sequence (#15) marked complete.
- meta.yml.brand_overrides: 2 entries (`line_spacing_0.9`, `band_consistency`).
- Git log shows one commit per task (or per sub-commit in T11) with `21: <type>(<scope>): ...` prefix.
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria (lines 91-98), with RESEARCH corrections applied:

1. M-Basis-Konflikt is resolved — decision documented in build.py header (T01) + README + brief; `tools/check_ci.py` NOT updated (RESEARCH correction #1: it has no logo logic); brand rule in `brand_constraints.py:262` was ALREADY trim-konsistent — confirmed by parametric M-Basis test on 4 other V1 templates (T01 verify) + on falzflyer post-resize (T02 verify).
2. All V1 deltas applied in build.py in atomic commits (T01-T08 = 8 commits in build.py + meta.yml).
3. template.sla regenerates cleanly (T09).
4. structural_check zero errors; all 22 CONSTRAINTS green (T09 + T10 verify).
5. structural_check --all stays green (T01, T02, T10 verify); the four other templates' Logo-checks stay green under the unchanged M-Basis rule.
6. M-Basis rule (already in brand_constraints.py) passes on the parametric geometry test for all 5 V1 templates (T11 PART B invariant 19).
7. Brief Section 10 Session-History row added (T11 PART E); .md Session-History `Resulting issue` updated.
8. HANDOFF.md V1 rollout sequence (#15) marked complete after merge (T11 PART F).

Plus implicit (RESEARCH-locked extensions):
- Spec rewritten (T11 PART C) — RESEARCH locked #12.
- NEW geometry test ≥18 invariants (T11 PART B) — RESEARCH locked #11.
- README documenting M-Basis decision rationale (T11 PART D).
- 16 falzflyer/* ParaStyles registered (T03 + T03 verify).
- INJECT_MAP populated for 5 photos (T05, T06, T08).
- 22 CONSTRAINTS list (T09 verify).
- 4 brand_overrides cleanup (T01 + T10).
</success_criteria>

<notes_for_executor>
- The user has directed "fully automated, without discussion". RESEARCH locks 13 decisions and 5 ISSUE.md errata corrections. DO NOT re-litigate these. If a task instruction conflicts with what you find in the code, trust RESEARCH first — the codebase was live-verified on 2026-05-09 by the researcher.
- Em-dash characters (U+2014) in Thema annames are LITERAL — use the actual em-dash, not `--`. Same in CONSTRAINTS list.
- Middle-dot (U+00B7) in "Themen 1·2" / "Themen 3·4" Top-Title text is LITERAL.
- ISSUE.md framing on `tools/check_ci.py` is wrong (it has no logo logic). RESEARCH correction #1 wins — DO NOT edit `tools/check_ci.py` or `tools/sla_lib/builder/brand_constraints.py`.
- The RED window between T01 and T02 is intentional and short (one task). DO NOT skip the verify on T01 — the 3-violation report is the proof T02 has work to do.
- Smoke test `test_panel_content_within_safe_width` filter extension is in T11 PART A, not earlier. If T06/T07/T08 verify fails on a Top-Band/Body-Backing frame in smoke, defer to T10 — for those tasks run only structural_check.
- T11 is the largest task (smoke + geometry + spec + README + brief + HANDOFF + EXECUTION + status). Split into 3 commits (test / docs / status) per the action notes.
- All edits use REAL annames (locked #4): `falzflyer/cand-name` not `cover-name`; `falzflyer/closer-url` not `url`; `falzflyer/thema-*` not `themen-*`.
- NEVER include "claude" or AI attribution in any commit message, code comment, or file (per user standing directive).
- Codex visual review is SKIPPED (locked #13) — DO NOT add a Codex iteration to any task.
</notes_for_executor>
