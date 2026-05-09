# RESEARCH — #21: V1 "Falz-Rhythm" for `kandidat-falzflyer-din-lang` + M-Basis fix

**Researched:** 2026-05-09
**Issue:** 21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix
**Confidence:** HIGH — every claim file:line-traced to current main; build pipeline verified live (build.py runs clean, smoke 11/11 ✓, structural_check 0 errors / 0 warnings / 6 overrides / 19 passes; M-Basis rule run live against all 5 V1 templates).
**Per-dimension report:** `research/codebase.md` (line-level evidence, ParaStyle dump, frame inventory, M-Basis live verification).

---

## Executive summary

ISSUE.md prescribes V1 "Falz-Rhythm" — universal Top-Band over all 6 panels, P1↔P6 grüne-Klammer, P4/P5 Themen sub-layout symmetry, P6 Kontakt 2-column mirror around `AXIS_P6_CENTER_X = 247.5`, plus a "M-Basis-Konflikt" resolution that the issue claims requires updating `tools/check_ci.py`. This is the **fifth and most complex** of the five V1 implementations and absorbs every pattern from #17–#20.

Live empirical verification this session resolves the M-Basis question definitively and exposes 5 ISSUE.md errata that this RESEARCH locks for the planner:

1. **M-Basis-Konflikt is not a tool change** — it's a build.py header-comment correction + 3 logo resizes. The rule `brand:logo_size_3M` in `tools/sla_lib/builder/brand_constraints.py:249–282` already implements `M = 0.06 × min(page_w_mm, page_h_mm)` (Trim-konsistent). A live run against all 5 V1 templates produces: 4 templates PASS today, only kandidat-falzflyer FAILs ×3 (P1 20mm, P2 16mm, P6 17mm vs 3M=37.8). **The "fix" the spec calls for is already in code; the only drift is a misleading code comment in `templates/kandidat-falzflyer-din-lang/build.py:195–199` ("kurze Kante=105 → 18.9 mm Logo-Soll") which contradicts the rule.** No edits needed in `tools/check_ci.py` (which only validates color/style drift).

2. **ParaStyle name drift in the spec.** improvements/05-kandidat-falzflyer.md uses `themen-*` (plural) and `falzflyer/cover-name` / `falzflyer/url` / `falzflyer/contact-label`; build.py reality is `thema-*` (singular) and `falzflyer/cand-name` / `falzflyer/closer-url`; no `contact-label` exists. Lock real names below.

3. **P3 + P6 "vollflächig" Dunkelgrün IS the top-band** — they don't get a separate small Top-Band polygon. The CONSTRAINTS list `same_size("p1_top_band", … "p6_top_band", axis="h")` proposed in ISSUE.md must be reduced to 4 explicit top-bands (P1, P2, P4, P5) plus `inside` checks anchoring the Top-Title text on P3 + P6 to their vollflächig backgrounds.

4. **`themen-wirtschaft.jpg` is NOT missing.** Already in central library at `shared/sample-images/themen/wirtschaft-handwerk.jpg` (manifest id `themen_wirtschaft_handwerk`, crop_focus [0.50, 0.55]). NO #13 dependency. P5 Thema 4 photo is buildable today.

5. **`tools/check_ci.py` is NOT touched.** It's the brand-color/style validator, contains zero logo-size or alignment logic. ISSUE.md framing on this point is wrong; the planner must NOT add an M-Basis check there.

Plus 11 layout decisions locked below (Top-Band coords, NEW polygon set, ParaStyle mutation map, CONSTRAINTS list with correct annames, geometry test plan, atomic-PR ordering).

**Primary recommendation:** Implement V1 in the 11-task atomic-PR sequence in §"Suggested PR shape" below; the M-Basis "fix" is a 1-line build.py comment change + the V1 logo resizes already planned + dropping the `brand:logo_size_3M` override; no tool/library changes anywhere. The other 4 V1 templates are already trim-konform today and stay green under the rule unchanged.

---

## User Constraints (from CONTEXT.md)

**No CONTEXT.md found** — no separate discussion artifact. ISSUE.md + improvements/05-kandidat-falzflyer.md + improvements/HANDOFF.md are the only upstream input. The user's standing directive ("fully automated, without discussion") means RESEARCH.md must lock all open questions so the planner can produce zero-ambiguity tasks. This RESEARCH does so via the locked-decisions table below.

---

## Locked decisions (planner: do NOT re-litigate)

| # | Decision | Reason |
|---|---|---|
| 1 | **M-Basis rule = no code change.** `tools/sla_lib/builder/brand_constraints.py:262` already uses `kurze_kante = min(page_w_mm, page_h_mm)` (Trim-min). For falzflyer the page is 297×210 so `min=210, M=12.6, 3M=37.8 mm`. Live verification confirms 4 of 5 V1 templates PASS; only kandidat-falzflyer FAILs (3 logos under-sized). **Fix:** correct `templates/kandidat-falzflyer-din-lang/build.py:195–199` header-comment (replace "kurze Kante=105 → 18.9 mm" with "Trim-kurze-Kante=210 → 3M=37.8 mm"); resize V1 logos to 38mm; drop `brand:logo_size_3M` override from meta.yml. **No edits to `tools/check_ci.py` or `tools/sla_lib/builder/brand_constraints.py`.** | Codebase §6, §7. |
| 2 | **`tools/check_ci.py` not in scope.** It only validates brand-color CMYK/RGB drift + non-CI style flagging. No logo/alignment logic. ISSUE.md framing on this point is wrong. | Codebase §10 + read of all 266 lines of file. |
| 3 | **ParaStyle MUTATION pattern for the 9 align-flips + fcolor flips** (per #19/#20 precedent). PARALLEL ParaStyles ONLY for the 2 NEW on-green variants where the white-on-light original must coexist with white-on-green (`slogan-on-green`, `quote-on-green`) and 2 NEW supporting styles (`top-title`, `themen-eyebrow`). Net change: 9 mutations + 4 new = 13 styles affected (12 → 16 in falzflyer namespace). | ISSUE.md L84 + #19 precedent. |
| 4 | **Real annames** (NOT spec-stub snake_case). Production annames preserved verbatim from current build.py: `P4 Thema 1 — Headline` (em-dash, U+2014), `P6 Logo Grüne`, `P3 Hintergrund` etc. ISSUE.md `p4_thema_a_eyebrow` are stubs to be translated. | Codebase §1.4. |
| 5 | **P3 + P6 vollflächig Dunkelgrün — no separate Top-Band polygon.** P3 keeps existing `P3 Hintergrund` polygon (already vollbleed); P6 gets a NEW `P6 Hintergrund` polygon (analogous, x=198, y=-3, w=102, h=216, fill=Dunkelgrün, layer=Hintergrund). 4 explicit Top-Band polygons added on P1/P2/P4/P5. The "uniform top-band height" constraint applies to those 4 only. | Codebase §12. |
| 6 | **Top-Band geometry locked.** All 4 Top-Bands `y_mm=-3, h_mm=31`. Outer panels P1/P4: `x_mm=-3, w_mm=105` (3mm trim-bleed left + 99mm panel + 3mm fold-overshoot right). Inner panels P2/P5: `x_mm=99 / 99, w_mm=99` flush both folds. P3 + P6 vollflächig replaces band. | Codebase §12 + ISSUE.md L26 + spec L60–61. |
| 7 | **`themen-wirtschaft.jpg` not blocking.** Library asset `themen_wirtschaft_handwerk` exists at `shared/sample-images/themen/wirtschaft-handwerk.jpg` with crop_focus [0.50, 0.55]. P5 Thema 4 photo binds to it via `_photo_inline("wirtschaft")` after extending THEMEN_LIBRARY_IDS. **NOT a #13 dependency.** | Codebase §9. |
| 8 | **`build_template + build_preview` split** (per #20 precedent). Move the body of current `build_doc()` to `build_template()`; add `INJECT_MAP` for the 4 themen photos + 1 portrait; `build_preview()` reads INJECT_MAP and calls `library.inject_into_frame(frame, img, target_w_mm=item.w_mm, target_h_mm=item.h_mm)`. Keep `build_doc = build_template` alias for structural_check + smoke. `build()` calls `build_preview()`. | Codebase §1.5 + #20 precedent (build.py L494–531). |
| 9 | **No rotation contract needed.** Unlike #20 (tent-card with apex fold), the kandidat-falzflyer is a Zickzackfalz with vertical folds at x=99/198. All 6 panels read upright. NO `rotation_deg=180` anywhere. The simpler 6-panel-on-2-pages model means `inside` constraints work for ALL pairs (including cross-page) — no rotation guard needed. | Spec source-of-truth + codebase §1 (no rotation_deg in current build.py). |
| 10 | **Atomic-PR ordering: 11 tasks T01..T11.** No "RED window" risk — the M-Basis rule is unchanged. Order: T01 build.py header-comment fix + drop `brand:logo_size_3M` override → T02 verify 4 other templates stay green (regression spot-check via geometry test or one-shot script) → T03 ParaStyles mutate+add + meta.yml ci_overrides extend → T04 INJECT_MAP scaffold + build_template/build_preview split → T05 4 Top-Band polygons + 5 Top-Title TextFrames + Logo asset swap (P1+P6 → gruene-weiss.png; P2 logo deleted) → T06 P1 Cover + P6 Kontakt grüne-Klammer (Name-Card polygon, P6 vollflächig polygon, 2-column Kontakt) → T07 P2 Mein Plan + P3 Wahltag deltas (Body-Backing Hellgrün, P3 frame y-shifts) → T08 P4 + P5 Themen deltas (photo h=44, Hellgrün-3mm-Trenner, P5 Thema 4 photo, P4 Thema 2 body delete) → T09 CONSTRAINTS list rewrite (drop the 9 V0 entries, add the V1 set) → T10 regen template.sla + render-gallery + meta.yml SHA + brand_overrides cleanup → T11 spec rewrite + smoke test additions + NEW geometry test + README update + brief §10 + EXECUTION.md + status flip. **Codex visual review SKIPPED** (#19/#20 precedent). | Synthesis. |
| 11 | **Geometry test target ≥18 invariants** in NEW `tools/sla_lib/tests/test_kandidat_falzflyer_geometry.py`. Coverage: 4 top-bands same h, P1↔P6 grüne-Klammer (same_size on P1 Hintergrund-name-card vs P6 Hintergrund vollflächig), P4↔P5 themen mirror via same_x/same_size on a/b photos+headlines+bodies, P6 col_left↔col_right `mirrored_x` at 247.5, P6 baseline sharing (`same_y(adresse, telefon)`, `same_y(email, sprechtag)`), Logo width = 37.8 ± 0.5 (P1 + P6), P2 logo absent (negative assertion), Falz layer integrity (only the 4 fold-line PAGEOBJECTs on LAYER=3, none-other), ParaStyle existence (15+ V1 styles present, `falzflyer/teaser-body` retains align=0 contract, etc.), brand:logo_size_3M green for ALL 5 V1 templates (parametric regression; tests for kandidat self + 4 others). | #20 geometry test pattern (21 invariants); ISSUE.md AC. |
| 12 | **Spec rewrite mandatory.** `templates/_specs/kandidat-falzflyer-din-lang.md` (675 lines) is heavily drifted (P1 Logo `35×10` vs reality `20×18`, contact-headline fcolor Dunkelgrün vs V1 White, no Top-Band block, no Hellgrün-Backing block, etc.). Rewrite per #19 + tueranhaenger pattern. | Codebase §1.7. |
| 13 | **Codex visual review SKIPPED.** This is a single-page-per-side multi-panel template; the V1 rollout precedent (#19, #20) is to skip Codex when `brand:image_fills_frame` + geometry-test invariants + structural_check + smoke are sufficient regression detectors. | Pitfalls + #19/#20 precedent. |

---

## Scope changes vs. ISSUE.md

| ISSUE.md item | Status | Why |
|---|---|---|
| "Update `tools/check_ci.py` to enforce M = `0.06 × min(trim_w, trim_h)`" | **DROPPED** — rule already in `brand_constraints.py` and already trim-konform (locked #1, #2). |
| "M-Basis-Konflikt resolution" | **REFRAMED** — only a build.py header-comment fix + 3 logo resizes + override drop (locked #1). |
| Asset `samples/themen-wirtschaft.jpg` "flag for #13" | **DROPPED** — asset already in library as `themen_wirtschaft_handwerk` (locked #7). |
| "9 align flips + new `falzflyer/slogan-on-green` + new `falzflyer/quote-on-green`" | **EXPANDED** to 9 mutations + 4 new ParaStyles (`slogan-on-green`, `quote-on-green`, `top-title`, `themen-eyebrow` — the latter two are required for V1 Top-Title tags + P4/P5 caps eyebrow but ISSUE.md is silent on them; locked #3). |
| `same_size("p1_top_band" … "p6_top_band")` (6 polygons) | **REVISED** to 4-way `same_size` on P1/P2/P4/P5 only; P3+P6 vollflächig (locked #5). |
| `same_y("p6_col_left_adresse", "p6_col_right_telefon")` etc. | **KEPT** with real annames (locked #4). |
| `aligned_below("p4_thema_a_photo", "p4_thema_a_headline", gap_mm=4.0)` | **KEPT** but in the V1 set the photo's x must equal the headline's x; the spec puts both at panel-left margin (x=6) so it's buildable. |
| Spec rewrite | **ADDED** in scope per locked #12 (issue silent on this). |
| NEW geometry test | **ADDED** in scope per locked #11 (issue silent on this). |
| README update | **ADDED** to document M-Basis comment fix decision. |
| HANDOFF.md update | **ADDED** to mark V1 rollout sequence (#15) complete (per ISSUE.md AC L98). |

---

## Codebase Analysis — interfaces

<interfaces>

### Constraint factories (`tools/sla_lib/builder/constraints.py`) — V1 uses

```python
# All factories take *targets as anname strings (or frame instances; .anname extracted).
# tolerance_mm default 0.5; name optional (auto-generated from kind+targets if blank).
def same_y(*targets, tolerance_mm=0.5, name="") -> Constraint     # L399
def same_x(*targets, tolerance_mm=0.5, name="") -> Constraint     # L408
def same_size(*targets, axis="both"|"w"|"h", tolerance_mm=0.5, name="") -> Constraint   # L417
def mirrored_x(left, right, axis_mm, tolerance_mm=0.5, name="") -> Constraint   # L433
def mirrored_y(top, bottom, axis_mm, tolerance_mm=0.5, name="") -> Constraint   # L443
def inside(child, parent, tolerance_mm=0.5, name="") -> Constraint   # L453 — raw bbox containment
def aligned_below(below, above, gap_mm, tolerance_mm=0.5, name="") -> Constraint   # L507 — REQUIRES same x_mm AND below.y == above.y + above.h + gap
def same_style(*targets, name="") -> Constraint   # L481
def distance_y(a, b, equals, tolerance_mm=0.5, name="") -> Constraint   # L489
def distance_x(a, b, equals, tolerance_mm=0.5, name="") -> Constraint   # L498
# Resolver matches `anname` exactly (case-sensitive).
# NO Group, NO same_y_top, NO same_x_center, NO mirrored_around_bbox-aware helpers exist.
```

### Brand rule `brand:logo_size_3M` (`tools/sla_lib/builder/brand_constraints.py:249–282`)

```python
@dataclass(frozen=True)
class _LogoSize3MRule(BrandRule):
    factor: float = 3.0
    tolerance_mm: float = 0.5
    def check(self, primitives: list, doc, constraints=None) -> list:
        page = doc.pages[0]
        page_w_mm = page.width_pt * PT_TO_MM
        page_h_mm = page.height_pt * PT_TO_MM
        kurze_kante = min(page_w_mm, page_h_mm)   # ALREADY trim-min — no edit needed
        m = 0.06 * kurze_kante
        expected = self.factor * m
        for p in primitives:
            if not isinstance(p, ImageFrame): continue
            if not re.search(r"\blogo\b", getattr(p, "anname", "") or "", re.IGNORECASE): continue
            if abs(p.w_mm - expected) > self.tolerance_mm:
                violations.append(...)
        return violations
```

### Primitive surface (`tools/sla_lib/builder/primitives.py`, used unchanged from #20)

```python
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

### Library helper (`tools/sla_lib/builder/library.py`, V1 uses INJECT_MAP idiom)

```python
def inject_into_frame(frame, img, *, target_w_mm, target_h_mm,
                       dpi=300, quality=80, apply_watermark=True) -> None
def load(id, *, optional=False) -> Optional[LibraryImage]
def crop_for_frame(img, *, target_w_mm, target_h_mm, dpi=300, quality=80,
                    apply_watermark=True) -> bytes
```

### `Document` API (used unchanged)

```python
class Document:
    def add_color(self, name, *, cmyk=None, rgb=None, spot=False) -> None
    def add_para_style(self, ps: ParaStyle) -> None
    def add_master(self, *, name, size, bleed_mm, margins_mm) -> Master
    def add_page(self, *, size, bleed_mm, margins_mm, master) -> Page
    def save(self, path) -> None
    pages: list[Page]
    _extra_para_styles: dict[str, ParaStyle]   # introspection-only
```

### Falz block (`tools/sla_lib/builder/blocks.py:559`)

```python
class FoldLine:   # used at build.py L339, L345, L564, L570
    start_mm: tuple[float, float]
    end_mm:   tuple[float, float]
    layer_idx: int = 3
    anname: str = ""
```

### Current build.py contract (`templates/kandidat-falzflyer-din-lang/build.py`)

```python
TRIM_W_MM = 297.0; TRIM_H_MM = 210.0; BLEED_MM = 3.0
PANEL_W_MM = 99.0; FOLD_X1_MM = 99.0; FOLD_X2_MM = 198.0
LAYER_HINTERGRUND = 0; LAYER_BILDER = 1; LAYER_TEXT = 2; LAYER_FALZ = 3

def _add_styles(doc): ...    # registers 12 falzflyer/* ParaStyles (V1: 16)
def _add_front(doc, page0): ...    # P1 + P2 + P3 + 2 fold lines (V1: + Top-Bands + Backings + Top-Titles)
def _add_back(doc, page1): ...    # P4 + P5 + P6 + 2 fold lines (V1: + Top-Bands + Trenner + new layout)
def build_doc() -> Document: ...   # V1: rename to build_template, add build_preview wrapper
def build(out_path=...) -> Path:   # V1: calls build_preview() internally

CONSTRAINTS = [...]   # V1: full rewrite (9 → ~22 entries)
```

### V1 frame inventory (TARGET — see `<v1_target_frames>` block below for full list)

</interfaces>

---

## V1 ParaStyle table (planner: pass verbatim to T03)

**MUTATIONS** (9 styles — change in place; no parallel sibling):

```python
# 1. cand-name (P1 Kandidat-Name on Dunkelgrün Name-Card)
ParaStyle(name="falzflyer/cand-name",
    font="Vollkorn Black Italic", fontsize=24, linesp=27, linesp_mode=0,
    align=1,                  # was 0 — center on P1 Name-Card axis
    fcolor="White",            # was Dunkelgrün — flips for on-Dunkelgrün
    language="de")

# 2. slogan (P1 — kept existing for any future white-page placement; replaced on Name-Card by slogan-on-green; align flip applies to ALL placements)
# Per ISSUE.md L84: "Add a new `falzflyer/slogan-on-green` (parallel) rather than mutating".
# So: KEEP slogan as-is for backwards-compat AND ADD parallel slogan-on-green (Gelb).
# But ALSO flip slogan.align 0→1 (V1 needs center alignment on cover; the slogan's only call-site is P1 Slogan).
# Net: MUTATE slogan.align 0→1 BUT KEEP fcolor=Black (its only V1 use is via slogan-on-green now).
# Actually — re-read spec: P1 Slogan keeps `falzflyer/slogan` but with new `fcolor: Gelb`. Recommended path: ADD slogan-on-green (Gelb, align=1) for P1, retire `falzflyer/slogan` from build.py call-sites but keep style registration for diff stability.
# DECISION: MUTATE slogan.align=0→1 to support hypothetical future reuse; keep fcolor=Black; ADD slogan-on-green parallel for P1.
ParaStyle(name="falzflyer/slogan",
    font="Gotham Narrow Bold", fontsize=14, linesp=17, linesp_mode=0,
    align=1,                  # was 0
    fcolor="Black", language="de")

# 3. closer-headline (P3 — already centered visually)
ParaStyle(name="falzflyer/closer-headline",
    font="Gotham Narrow Bold", fontsize=22, linesp=26, linesp_mode=0,
    align=1,                  # was 0
    fcolor="White", language="de")

# 4. closer-url (P3)
ParaStyle(name="falzflyer/closer-url",
    font="Gotham Narrow Bold", fontsize=11, linesp=14, linesp_mode=0,
    align=1,                  # was 0
    fcolor="White", language="de")

# 5. closer-datum (P3) — also centered
ParaStyle(name="falzflyer/closer-datum",
    font="Vollkorn Black Italic", fontsize=14, linesp=18, linesp_mode=0,
    align=1,                  # was 0
    fcolor="Gelb", language="de")

# 6. contact-headline (P6 — on Dunkelgrün vollflächig)
ParaStyle(name="falzflyer/contact-headline",
    font="Gotham Narrow Bold", fontsize=16, linesp=20, linesp_mode=0,
    align=1,                  # was 0
    fcolor="White",            # was Dunkelgrün — P6 vollflächig
    language="de")

# 7. contact-body (P6 — 2-Spalten on Dunkelgrün)
ParaStyle(name="falzflyer/contact-body",
    font="Gotham Narrow Book", fontsize=10, linesp=12, linesp_mode=0,
    align=1,                  # was 0
    fcolor="White",            # was Black — on Dunkelgrün
    language="de")

# 8. thema-body (P4/P5 — on Hellgrün-Backing per V1; align=1 per spec)
ParaStyle(name="falzflyer/thema-body",
    font="Gotham Narrow Book",
    fontsize=10,               # was 9 (V1 raises 1pt — accept content discipline)
    linesp=13,                 # was 11 (1.3× body convention)
    linesp_mode=0,
    align=1,                   # was 0
    fcolor="Black",             # stays Black (themen panels remain on white background per V1; only Hellgrün-3mm-Trenner between A and B is green)
    language="de")

# 9. impressum (P6 — on Dunkelgrün vollflächig)
ParaStyle(name="falzflyer/impressum",
    font="Gotham Narrow Book", fontsize=6, linesp=8, linesp_mode=0,
    align=1,                  # was 0 (centered under footer logo on x=247.5)
    fcolor="White",            # was Black — on Dunkelgrün
    language="de")
```

**KEPT UNCHANGED (per spec L212-216):** `falzflyer/teaser-headline` (align=0 redaktioneller Charakter), `falzflyer/teaser-body` (align=0 left-aligned redaktioneller Body — but V1 spec on L70 sets P2 Teaser-Body fcolor Black→White on Hellgrün-Backing → MUTATE fcolor only, KEEP align=0), `falzflyer/thema-headline` (align=0 redaktioneller Charakter — but V1 spec table L88 says Thema 1 Body fcolor stays Black on white background; thema-headline stays Dunkelgrün-on-Weiß).

**Refinement on `teaser-body` mutation:** spec says P2 Teaser-Body fcolor White on Hellgrün. Keep `falzflyer/teaser-body.align=0`; mutate `fcolor: Black → White`.

```python
# 10. teaser-body (P2 on Hellgrün-Backing) — only fcolor mutation; keep align=0
ParaStyle(name="falzflyer/teaser-body",
    font="Gotham Narrow Book", fontsize=11, linesp=14, linesp_mode=0,
    align=0,                  # KEEP
    fcolor="White",            # was Black — on Hellgrün
    language="de")
```

So the count is **10 mutations** (9 align flips + 1 fcolor-only on teaser-body), aligning with ISSUE.md spirit ("9 align flips" = 9 align mutations; teaser-body fcolor flip is implicit per V1 spec table).

**NEW PARALLEL STYLES** (4 new styles — register in `_add_styles`):

```python
# A. slogan-on-green (P1 Name-Card) — Gelb on Dunkelgrün
ParaStyle(name="falzflyer/slogan-on-green",
    font="Gotham Narrow Bold", fontsize=14, linesp=17, linesp_mode=0,
    align=1, fcolor="Gelb", language="de")

# B. quote-on-green (P2 Pull-Quote per spec L298–301; spec layout has Vollkorn Italic Pull-Quote on Dunkelgrün card at panel bottom)
# OPTIONAL for V1 — spec describes a Pull-Quote zone but the V1 minimum doesn't require it.
# Register the style now; only emit a frame when content is supplied. Defer Pull-Quote frame to follow-up if narrowly scoped.
ParaStyle(name="falzflyer/quote-on-green",
    font="Vollkorn Black Italic", fontsize=18, linesp=20, linesp_mode=0,
    align=1, fcolor="White", language="de")

# C. top-title (P2/P3/P4/P5 Top-Title tags inside the Top-Band — 11pt Caps Bold White)
ParaStyle(name="falzflyer/top-title",
    font="Gotham Narrow Bold", fontsize=11, linesp=14, linesp_mode=0,
    align=0,                  # left-aligned within band per spec ("links im Top-Band")
    fcolor="White", language="de")

# D. themen-eyebrow (P4/P5 Caps `THEMA 0X` per spec L321, L184)
ParaStyle(name="falzflyer/themen-eyebrow",
    font="Gotham Narrow Bold", fontsize=9, linesp=12, linesp_mode=0,
    align=0,                  # KEEP align=0 (eyebrow convention per spec L213)
    fcolor="Dunkelgrün", language="de")
```

**NET ParaStyle count:** 12 (V0) + 4 (NEW) = **16 in V1**. ci_overrides.non_ci_styles must list all 16.

**Spec note `falzflyer/contact-label` (mentioned in spec table L191):** the label-row in P6 (e.g. "ADRESSE" / "EMAIL" / "TELEFON" / "SPRECHTAG" caps tag above each value) per spec L191 uses `falzflyer/contact-label`. This is a NEW style (parallel — caps small-bold). **DEFERRED:** V1 Kontakt-data already comes via `falzflyer/contact-body` 2-Zeilen (Adresse 2 lines, Email-Tel 2 lines). Adding caps labels above each value adds 4 more text frames + a new ParaStyle for limited UX gain. **Lock:** P6 V1 uses `contact-body` only; add label rows in a follow-up if requested. (One-line rationale doc in commit body.)

---

## V1 frame inventory — TARGET state (planner: pass verbatim to T05–T08)

<v1_target_frames>

### Page 0 (Front): P1 + P2 + P3

| anname                        | type      |  x  |  y  |  w  |  h  | layer       | fill / asset / style |
|-------------------------------|-----------|-----|-----|-----|-----|-------------|----------------------|
| `P1 Top-Band`                 | Polygon   |  -3 |  -3 | 105 |  31 | HINTERGRUND | Dunkelgrün            |
| `P1 Logo Grüne (weiss)`       | ImageFrame|   6 |   4 |  38 |  22 | BILDER      | shared/logos/gruene-weiss.png |
| `P1 Kandidat-Portrait`        | ImageFrame|   6 |  34 |  87 | 100 | BILDER      | library `portrait_maria` (build_preview) |
| `P1 Name-Card`                | Polygon   |  -3 | 134 | 105 |  79 | HINTERGRUND | Dunkelgrün (extends to bleed bottom y=210+3=213; h=79) |
| `P1 Kandidat-Name`            | TextFrame |   6 | 142 |  87 |  18 | TEXT        | style=falzflyer/cand-name (V1: align=1, fcolor=White) |
| `P1 Slogan`                   | TextFrame |   6 | 164 |  87 |  20 | TEXT        | style=falzflyer/slogan-on-green (NEW: Gelb align=1) |
| `P2 Top-Band`                 | Polygon   |  99 |  -3 |  99 |  31 | HINTERGRUND | Dunkelgrün            |
| `P2 Top-Title`                | TextFrame | 105 |   8 |  87 |  14 | TEXT        | style=falzflyer/top-title text="Mein Plan" |
| `P2 Teaser-Headline`          | TextFrame | 105 |  38 |  87 |  22 | TEXT        | style=falzflyer/teaser-headline (unchanged) |
| `P2 Body-Backing`             | Polygon   |  99 |  66 |  99 | 144 | HINTERGRUND | Hellgrün              |
| `P2 Teaser-Body`              | TextFrame | 113 |  72 |  73 | 130 | TEXT        | style=falzflyer/teaser-body (V1: fcolor=White, indent x+8 for inset) |
| `P3 Hintergrund`              | Polygon   | 198 |  -3 | 102 | 216 | HINTERGRUND | Dunkelgrün (UNCHANGED — vollflächig) |
| `P3 Top-Title`                | TextFrame | 204 |   8 |  87 |  14 | TEXT        | style=falzflyer/top-title (NEW: V1 spec line 76 says Bold Gelb — but `top-title` is White; LOCK: USE `falzflyer/top-title` (White) for consistency across P2/P3/P4/P5; the Gelb option is V1-spec-suggestion which deviates from uniform Top-Title contract — White wins) text="Wahltag" |
| `P3 Wahlkreuz`                | ImageFrame| 222 |  44 |  50 |  50 | BILDER      | shared/assets/wahlkreuz.png (UNCHANGED size; y 30→44) |
| `P3 Closer-Headline`          | TextFrame | 204 | 100 |  87 |  32 | TEXT        | style=falzflyer/closer-headline (V1: align=1) |
| `P3 Datum-Akzent`             | TextFrame | 204 | 145 |  87 |  22 | TEXT        | style=falzflyer/closer-datum (V1: align=1) |
| `P3 URL`                      | TextFrame | 204 | 185 |  87 |  12 | TEXT        | style=falzflyer/closer-url (V1: align=1) |
| `Falz x=99 (Front)`           | FoldLine  |  99 |   0 |   0 | 210 | FALZ        | (UNCHANGED) |
| `Falz x=198 (Front)`          | FoldLine  | 198 |   0 |   0 | 210 | FALZ        | (UNCHANGED) |

**Note on P3 Top-Title color:** spec L76 says "Bold Gelb"; for uniformity across P2/P3/P4/P5 use a SINGLE `top-title` ParaStyle (White). To honor the Gelb on P3 specifically, use a per-frame fcolor override: `TextFrame(... style="falzflyer/top-title", fcolor="Gelb", ...)`. TextFrame.fcolor overrides ParaStyle.fcolor. **LOCK: TextFrame.fcolor="Gelb" override on P3 Top-Title only; uniform `top-title` style otherwise.**

**Note on `P2 Logo (klein)`:** DELETED in V1 (Top-Band replaces it).

### Page 1 (Back): P4 + P5 + P6

| anname                        | type      |  x  |  y  |  w  |  h  | layer       | fill / asset / style |
|-------------------------------|-----------|-----|-----|-----|-----|-------------|----------------------|
| `P4 Top-Band`                 | Polygon   |  -3 |  -3 | 105 |  31 | HINTERGRUND | Dunkelgrün            |
| `P4 Top-Title`                | TextFrame |   6 |   8 |  87 |  14 | TEXT        | style=falzflyer/top-title text="Themen 1·2" (note: align=2-right per spec L185 — use TextFrame `align` override when needed; V1 LOCK: keep ParaStyle align=0 with frame text-anchor visually; do NOT add per-frame align override unless spec requires distinct visual right-alignment in future) |
| `P4 Thema 1 — Eyebrow`        | TextFrame |   6 |  38 |  87 |   6 | TEXT        | style=falzflyer/themen-eyebrow text="THEMA 01" |
| `P4 Thema 1 — Headline`       | TextFrame |   6 |  46 |  87 |  14 | TEXT        | style=falzflyer/thema-headline (UNCHANGED style) |
| `P4 Thema 1 — Photo`          | ImageFrame|   6 |  62 |  87 |  44 | BILDER      | library `themen_klimaschutz_solar` (build_preview INJECT_MAP) |
| `P4 Thema 1·2 Trenner`        | Polygon   |  -3 | 108 | 105 |   3 | HINTERGRUND | Hellgrün (3mm strip per spec L86) |
| `P4 Thema 1 — Body`           | TextFrame |   6 | 114 |  87 |  26 | TEXT        | style=falzflyer/thema-body (V1: align=1, fontsize=10, linesp=13) |
| `P4 Thema 2 — Eyebrow`        | TextFrame |   6 | 144 |  87 |   6 | TEXT        | style=falzflyer/themen-eyebrow text="THEMA 02" |
| `P4 Thema 2 — Headline`       | TextFrame |   6 | 152 |  87 |  14 | TEXT        | style=falzflyer/thema-headline |
| `P4 Thema 2 — Photo`          | ImageFrame|   6 | 168 |  87 |  44 | BILDER      | library `themen_soziales_kaffeehaus` (V1: photo replaces body — LOCK: per spec L90 "Body wandert auf Innenseite Cover oder entfällt"; for V1 we DELETE P4 Thema 2 Body entirely; photo extends to bleed bottom is too aggressive — keep within trim, h=44 ends at y=212 which is 2mm into bleed — accept as bleed-overshoot) |
| `P5 Top-Band`                 | Polygon   |  99 |  -3 |  99 |  31 | HINTERGRUND | Dunkelgrün            |
| `P5 Top-Title`                | TextFrame | 105 |   8 |  87 |  14 | TEXT        | style=falzflyer/top-title text="Themen 3·4" |
| `P5 Thema 3 — Eyebrow`        | TextFrame | 105 |  38 |  87 |   6 | TEXT        | style=falzflyer/themen-eyebrow text="THEMA 03" |
| `P5 Thema 3 — Headline`       | TextFrame | 105 |  46 |  87 |  14 | TEXT        | style=falzflyer/thema-headline |
| `P5 Thema 3 — Photo`          | ImageFrame| 105 |  62 |  87 |  44 | BILDER      | library `themen_bildung_volksschule` |
| `P5 Thema 3·4 Trenner`        | Polygon   |  99 | 108 |  99 |   3 | HINTERGRUND | Hellgrün              |
| `P5 Thema 3 — Body`           | TextFrame | 105 | 114 |  87 |  26 | TEXT        | style=falzflyer/thema-body |
| `P5 Thema 4 — Eyebrow`        | TextFrame | 105 | 144 |  87 |   6 | TEXT        | style=falzflyer/themen-eyebrow text="THEMA 04" |
| `P5 Thema 4 — Headline`       | TextFrame | 105 | 152 |  87 |  14 | TEXT        | style=falzflyer/thema-headline |
| `P5 Thema 4 — Photo`          | ImageFrame| 105 | 168 |  87 |  44 | BILDER      | library `themen_wirtschaft_handwerk` (NEW for V1) |
| `P6 Hintergrund`              | Polygon   | 198 |  -3 | 102 | 216 | HINTERGRUND | Dunkelgrün (NEW vollflächig analog to P3) |
| `P6 Top-Title`                | TextFrame | 204 |   8 |  87 |  14 | TEXT        | style=falzflyer/top-title text="Kontakt" |
| `P6 Kontakt-Headline`         | TextFrame | 204 |  38 |  87 |  14 | TEXT        | style=falzflyer/contact-headline (V1: align=1, fcolor=White) text="Sprich mich an" |
| `P6 Adresse`                  | TextFrame | 204 |  62 |  41 |  20 | TEXT        | style=falzflyer/contact-body (V1: align=1, fcolor=White, x=204..245 = col_left); NEW anname (was P6 Kontakt-Adresse — KEEP that anname or rename? LOCK: rename to `P6 Adresse` to disambiguate from `P6 Telefon` mirror pair; ANNAME CHANGE) |
| `P6 Telefon`                  | TextFrame | 250 |  62 |  41 |  20 | TEXT        | style=falzflyer/contact-body (col_right; mirrored_x at 247.5 with `P6 Adresse`); NEW |
| `P6 Email`                    | TextFrame | 204 |  90 |  41 |  20 | TEXT        | style=falzflyer/contact-body (col_left, below adresse) |
| `P6 Sprechtag`                | TextFrame | 250 |  90 |  41 |  20 | TEXT        | style=falzflyer/contact-body (col_right, mirror of email) |
| `P6 QR-Code (mitmachen)`      | ImageFrame| 218 | 128 |  24 |  24 | BILDER      | samples/qr-mitmachen.png (V1: w 30→24, x 210→218 to center on col_left mirror axis) |
| `P6 QR-Caption (mitmachen)`   | TextFrame | 218 | 154 |  24 |   6 | TEXT        | NEW; style=falzflyer/top-title (Bold White 11pt — but spec says 9pt for caption; lock: use `falzflyer/top-title` 11pt for visual rhythm OR introduce new `falzflyer/qr-caption` 9pt Caps Bold). LOCK: use `falzflyer/themen-eyebrow` (9pt Caps Bold Dunkelgrün) BUT need fcolor=White on Dunkelgrün — frame fcolor override "White" |
| `P6 QR-Code (termine)`        | ImageFrame| 254 | 128 |  24 |  24 | BILDER      | samples/qr-termine.png |
| `P6 QR-Caption (termine)`     | TextFrame | 254 | 154 |  24 |   6 | TEXT        | NEW; mirror of mitmachen-caption |
| `P6 Logo Grüne (weiss)`       | ImageFrame| 228 | 168 |  38 |  34 | BILDER      | shared/logos/gruene-weiss.png (V1: 38×34; mirror_x=247.5 → x=228 = 247.5-38/2-0.5 ≈ 228); REVISE: x=247.5-38/2 = 228.5 → use x=228, w=38 → center=247 ≈ 247.5 within tol |
| `P6 Impressum`                | TextFrame | 204 | 200 |  87 |   8 | TEXT        | style=falzflyer/impressum (V1: align=1, fcolor=White, h 60→8) |
| `Falz x=99 (Back)`            | FoldLine  |  99 |   0 |   0 | 210 | FALZ        | (UNCHANGED) |
| `Falz x=198 (Back)`           | FoldLine  | 198 |   0 |   0 | 210 | FALZ        | (UNCHANGED) |

</v1_target_frames>

**Frame counts:** Page 0: 14 frames + 2 fold lines (V0: 11 + 2). Page 1: 27 frames + 2 fold lines (V0: 16 + 2). Total V1 named primitives: ~43 vs V0's 27 (+16). 11 NEW Polygons (4 Top-Bands, 1 P1 Name-Card, 1 P2 Body-Backing, 2 P4 Trenner-pair, 2 P5 Trenner-pair = 9 + 1 P6 vollflächig + 0 — wait: 4+1+1+1+1+1=9; let me re-count: P1 Top-Band, P2 Top-Band, P2 Body-Backing, P1 Name-Card, P4 Top-Band, P4 Thema 1·2 Trenner, P5 Top-Band, P5 Thema 3·4 Trenner, P6 Hintergrund vollflächig = **9 NEW polygons**). 5 NEW TextFrames for Top-Titles, 4 NEW themen-eyebrows, 4 NEW QR-captions, 2 split kontakt frames (Telefon + Sprechtag). 1 NEW ImageFrame for P5 Thema 4 photo.

---

## V1 CONSTRAINTS list (planner: pass verbatim to T09)

```python
CONSTRAINTS = [
    # ── Top-Band uniformity (4 explicit polygons; P3 + P6 vollflächig handled via inside) ──
    same_size("P1 Top-Band", "P2 Top-Band", "P4 Top-Band", "P5 Top-Band",
              axis="h", name="top_bands_uniform_h"),
    # P3 + P6 Top-Title is anchored via inside() instead of share-height contract:
    inside("P3 Top-Title", "P3 Hintergrund", name="p3_top_title_anchored"),
    inside("P6 Top-Title", "P6 Hintergrund", name="p6_top_title_anchored"),

    # ── P1 ↔ P6 grüne-Klammer: vollbleed Dunkelgrün on both outer panels ──
    same_size("P3 Hintergrund", "P6 Hintergrund", name="grüne_klammer_p3_p6"),
    # (P1 has Top-Band + Name-Card — full-bleed on top + bottom — not a single polygon to pair)

    # ── P4/P5 Themen sub-layout — mirror_pair structure (a/b) per panel ──
    # Panel 4
    same_x("P4 Thema 1 — Eyebrow", "P4 Thema 2 — Eyebrow", name="p4_eyebrow_x"),
    same_x("P4 Thema 1 — Headline", "P4 Thema 2 — Headline", name="p4_headline_x"),
    same_x("P4 Thema 1 — Photo", "P4 Thema 2 — Photo", name="p4_photo_x"),
    same_size("P4 Thema 1 — Photo", "P4 Thema 2 — Photo", name="p4_photos_size"),
    aligned_below("P4 Thema 1 — Photo", "P4 Thema 1 — Headline", gap_mm=2.0,
                  name="p4_t1_photo_anchored"),
    # Panel 5
    same_x("P5 Thema 3 — Eyebrow", "P5 Thema 4 — Eyebrow", name="p5_eyebrow_x"),
    same_x("P5 Thema 3 — Headline", "P5 Thema 4 — Headline", name="p5_headline_x"),
    same_x("P5 Thema 3 — Photo", "P5 Thema 4 — Photo", name="p5_photo_x"),
    same_size("P5 Thema 3 — Photo", "P5 Thema 4 — Photo", name="p5_photos_size"),
    aligned_below("P5 Thema 3 — Photo", "P5 Thema 3 — Headline", gap_mm=2.0,
                  name="p5_t3_photo_anchored"),
    # Cross-Panel: P4 ↔ P5 photo size uniform (4 themen photos same w×h)
    same_size("P4 Thema 1 — Photo", "P5 Thema 3 — Photo", name="cross_panel_themen_photos_size"),

    # ── P6 Kontakt 2-Spalten symmetric around AXIS_P6_CENTER_X = 247.5 ──
    mirrored_x("P6 Adresse", "P6 Telefon", axis_mm=247.5, name="p6_col_mirror_row1"),
    mirrored_x("P6 Email",   "P6 Sprechtag", axis_mm=247.5, name="p6_col_mirror_row2"),
    same_y("P6 Adresse", "P6 Telefon", name="p6_baseline_row1"),
    same_y("P6 Email",   "P6 Sprechtag", name="p6_baseline_row2"),
    same_size("P6 Adresse", "P6 Telefon", "P6 Email", "P6 Sprechtag", axis="both",
              name="p6_kontakt_cells_uniform"),
    mirrored_x("P6 QR-Code (mitmachen)", "P6 QR-Code (termine)", axis_mm=247.5,
               name="p6_qr_mirror"),
    same_size("P6 QR-Code (mitmachen)", "P6 QR-Code (termine)", name="p6_qrs_size"),

    # ── Logo Print-Soll consistency: P1 + P6 both at 38mm ──
    same_size("P1 Logo Grüne (weiss)", "P6 Logo Grüne (weiss)", axis="w",
              name="logos_print_soll_w_uniform"),

    # ── Style consistency across the 4 themen-headlines (V0 carries this; KEEP) ──
    same_style(
        "P4 Thema 1 — Headline", "P4 Thema 2 — Headline",
        "P5 Thema 3 — Headline", "P5 Thema 4 — Headline",
        name="thema_headline_style_consistent",
    ),
    # P4 Thema 2 has no body in V1 (deleted); thema-body style still consistent across the 3 remaining bodies
    same_style(
        "P4 Thema 1 — Body",
        "P5 Thema 3 — Body",
        # P5 Thema 4 has no body; P4 Thema 2 has no body
        name="thema_body_style_consistent",
    ),
]
```

**Constraint count:** 22 entries (compare V0's 9 entries; #20's 22 entries).

---

## Standard Stack

| Item | Value |
|---|---|
| Python | 3.13 (verified) |
| Tests (geometry + smoke) | `python3 -m unittest tools.sla_lib.tests.test_kandidat_falzflyer_geometry templates._smoke.test_kandidat_falzflyer_din_lang` |
| Build | `python3 templates/kandidat-falzflyer-din-lang/build.py` |
| Regen | `bin/render-gallery kandidat-falzflyer-din-lang --skip-visual-diff` (auto-bumps SHA in meta.yml; mirrors site/public) |
| Audit | `PYTHONPATH=tools bin/audit-alignment kandidat-falzflyer-din-lang` |
| structural_check | `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang` (and `--all`) |
| Stale check | `bin/check-stale-previews` |
| New deps | none |

---

## Don't Hand-Roll

- All Constraint factories (#14) — use them; do NOT invent `same_x_center`, `same_y_top`, `mirrored_around_bbox`, `Group`, `aspect_fill`. The factories include `mirrored_x` (used for P6 columns + P6 QR pair) and `inside`/`aligned_below` (used for P3+P6 anchoring + Themen photo placement).
- `library.inject_into_frame` — use post-#24 INJECT_MAP idiom (per #19 + #20 precedent), not the older `crop_for_frame + pack_inline_image` two-step. Lets the build re-emit cleanly with frame.w_mm/h_mm read live.
- ParaStyle MUTATION (#19/#20 precedent) for the 9 align flips and the teaser-body fcolor flip; PARALLEL only for `slogan-on-green`, `quote-on-green`, `top-title`, `themen-eyebrow` (4 NEW).
- `bin/render-gallery <slug> --skip-visual-diff` — regenerates template.sla + page-NN.png + preview.pdf + meta.yml SHA + site/public mirror in one command.
- Smoke test ADDITION pattern (#19/#20) — keep all 11 existing assertions, add V1-specific assertions; do NOT rewrite from scratch.
- The brand_overrides cleanup AT END (T10) — remove 4 (logo_size_3M, image_text_overlap, image_fills_frame, visual_adjacency_drift) once V1 is built and structural_check is clean; KEEP 2 (line_spacing_0.9, band_consistency).
- The `themen_wirtschaft_handwerk` library asset — already in manifest; just extend `THEMEN_LIBRARY_IDS` dict (don't create a new file in `samples/`).

---

## Architecture Patterns

### Recommended Approach

The 6-panel layout is structured by helper functions, mirror #20's `_panel_de`/`_panel_en` but adapted for 6 panels:

```python
def _panel_p1_cover(): -> list   # Top-Band + Logo + Portrait + Name-Card + Name + Slogan
def _panel_p2_mein_plan(): -> list   # Top-Band + Top-Title + Headline + Body-Backing + Body
def _panel_p3_wahltag(): -> list    # Hintergrund (existing) + Top-Title + Wahlkreuz + 3 text frames
def _panel_p4_themen_12(): -> list  # Top-Band + Top-Title + 2× (Eyebrow + Headline + Photo) + Trenner + 1 Body
def _panel_p5_themen_34(): -> list  # Top-Band + Top-Title + 2× (Eyebrow + Headline + Photo) + Trenner + 1 Body
def _panel_p6_kontakt(): -> list    # Hintergrund + Top-Title + Headline + 4 kontakt cells + 2 QRs + 2 captions + Logo + Impressum

def build_template():
    doc = Document(...)
    _add_styles(doc)
    page0 = doc.add_page(...)
    page1 = doc.add_page(...)
    for p in _panel_p1_cover(): page0.add(p)
    for p in _panel_p2_mein_plan(): page0.add(p)
    for p in _panel_p3_wahltag(): page0.add(p)
    page0.add(FoldLine(...))   # x=99
    page0.add(FoldLine(...))   # x=198
    for p in _panel_p4_themen_12(): page1.add(p)
    for p in _panel_p5_themen_34(): page1.add(p)
    for p in _panel_p6_kontakt(): page1.add(p)
    page1.add(FoldLine(...))   # x=99
    page1.add(FoldLine(...))   # x=198
    return doc

INJECT_MAP = {
    "P1 Kandidat-Portrait":    "portrait_maria",
    "P4 Thema 1 — Photo":      "themen_klimaschutz_solar",
    "P4 Thema 2 — Photo":      "themen_soziales_kaffeehaus",
    "P5 Thema 3 — Photo":      "themen_bildung_volksschule",
    "P5 Thema 4 — Photo":      "themen_wirtschaft_handwerk",
}

def build_preview():
    doc = build_template()
    for page in doc.pages:
        for item in page.items:
            if not isinstance(item, ImageFrame): continue
            lib_id = INJECT_MAP.get(item.anname)
            if not lib_id: continue
            img = library.load(lib_id, optional=True)
            if img is None: continue
            library.inject_into_frame(item, img, target_w_mm=item.w_mm, target_h_mm=item.h_mm)
    return doc

build_doc = build_template   # alias for structural_check / spec_check / smoke
def build(out_path=...): out=Path(out_path); build_preview().save(out); return out
```

### Anti-Patterns to Avoid

- **`Group`-style nesting** — does not exist in DSL. Use `_panel_*()` helpers that return primitive lists.
- **Cross-page `inside` with mismatched rotation** — N/A here (no rotation), but DON'T introduce rotation just for "symmetry" (P1↔P6 grüne-Klammer is achieved via 2 vollbleed Dunkelgrün polygons + same_size, not via rotation).
- **Polygons on `LAYER_TEXT`** — must be `LAYER_HINTERGRUND` (=0). Geometry test asserts.
- **Sample asset duplication** — DO NOT copy `wirtschaft-handwerk.jpg` into `templates/kandidat-falzflyer-din-lang/samples/`. Use the central library asset id (locked #7).
- **Editing `tools/check_ci.py` or `tools/sla_lib/builder/brand_constraints.py`** — out of scope (locked #1, #2).
- **Per-frame `align` overrides on Top-Title for P3 (Gelb suggestion)** — use `TextFrame.fcolor="Gelb"` override on the P3 frame only; ParaStyle stays uniform.

---

## Common Pitfalls

### Must-handle (HIGH severity)

1. **`tools/check_ci.py` / M-Basis confusion** — ISSUE.md framing is wrong; the rule is in `brand_constraints.py:262` and already trim-konform. **Prevention:** locked decision #1; no edit to either tool.
2. **`themen-wirtschaft.jpg` perceived dependency on #13** — already in central library at `themen_wirtschaft_handwerk`. **Prevention:** locked decision #7.
3. **Spec ParaStyle name drift** (`thema-` vs `themen-`, `cover-name` vs `cand-name`, etc.) — use REAL build.py names (locked #4; codebase §1.2 has the table).
4. **`aligned_below` fails if photo.x ≠ headline.x** — both must use the same x_mm. In V1 both use panel-left margin (x=6 for P4, x=105 for P5) so this works naturally; verify in T08.
5. **Frame `h=44` themen photos crossing into bleed** (ends at y=212 in P5 Thema 4 = 2mm into 3mm bleed) — INTENTIONAL bleed-overshoot for visual continuity; assert in geometry test that h=44 ± tol; brand:bleed_3mm rule is rule unaffected.
6. **`teaser-body` fcolor flip** — only `fcolor` mutates Black→White; `align=0` stays. Spec L70: "Body fcolor `Black→White`" without mentioning align change. Codify this in T03 commit.
7. **Smoke test `test_panel_content_within_safe_width`** filter — currently skips "Hintergrund" + "Wahlkreuz". V1 adds 4 Top-Bands (full-bleed w=105/99 — exceed 88.5 mm). Filter must extend to skip "Top-Band" / "Body-Backing" / "Name-Card" / "Trenner". List of skip-prefixes: `("Hintergrund", "Wahlkreuz", "Top-Band", "Body-Backing", "Name-Card", "Trenner", "Top-Title")` — Top-Title is text but content-spanning x in panel; safe to skip.

### Worth knowing (MEDIUM)

8. **Body fontsize 9pt → 10pt** raises 1pt; 1.3× linesp = 13mm. Existing P4/P5 V0 Body text won't fit at 10pt with same h=32; V1 reduces h to 26 + drops P4 Thema 2 body entirely. Content-discipline doc in commit body.
9. **Impressum on Dunkelgrün at 6pt** — ISSUE.md open Q4 flags readability. Lock: 6pt White on Dunkelgrün is V1-acceptable; flag for human review post-render via page-02.png inspection. If unreadable in print, V2 bumps to 7pt (separate PR).
10. **brand_overrides cleanup ordering** — drop AFTER V1 layout is in place (T10), not before. Otherwise structural_check fails between T01 and T09. The rule `brand:logo_size_3M` is the ONLY one whose violation goes from FAIL to PASS during V1; the others (image_text_overlap, image_fills_frame, visual_adjacency_drift) have their violations REMOVED by the V1 layout itself (Top-Bands + Backings remove text-on-white; CONSTRAINTS list removes adjacency warnings; INJECT_MAP + photo h=44 removes letterbox).
11. **P6 logo at `38×34`** (spec L95) gives aspect 1.12:1; asset gruene-weiss.png is 3.5:1; with `scale_type=0, ratio=1` Scribus auto-fits width-bound (image renders 38×10.86mm centered in 34mm frame ≈ 11.5mm padding above + below). Functionally fine; rule fires on frame.w_mm only. P1 logo at 38×22 (spec L62) renders 38×10.86 with 5.6mm padding above + below. **Same visual treatment as #20 (locked decision #1 in #20 RESEARCH).** Document in README alongside M-Basis comment fix.
12. **P3 + P6 Top-Title placement** on vollflächig backgrounds — `inside` constraint ensures the Top-Title sits in the visual top-band zone (y=4–25 within the 31mm conceptual band); since P3+P6 polygons cover the WHOLE panel, the inside check is broad. **Prevention:** add a tighter geometry test assertion `assert P3_top_title.y ≤ 28` (intra-band placement) — keeps visual rhythm with P1/P2/P4/P5.

### Informational (LOW)

13. **Logo asset `gruene-weiss.png` is the wordmark** (3.5:1, "DIE GRÜNEN" white-on-transparent). NO bund-weiss variant exists; if visual review wants the brushstroke G + tag in white, that requires a NEW asset (out of scope; defer).
14. **Codex visual review SKIPPED** (locked #13).
15. **P2 Pull-Quote frame** (spec L298–301) — register `falzflyer/quote-on-green` ParaStyle but DO NOT emit a Pull-Quote TextFrame in V1; defer the actual frame to a follow-up if narrowly scoped.
16. **`falzflyer/contact-label`** ParaStyle in spec table L191 — DEFERRED (no Caps label rows in V1; locked above).

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Python | build.py | ✓ | 3.13 | — |
| `lxml.etree` | smoke + geometry test | ✓ | (system) | — |
| `Pillow` (PIL) | library.inject_into_frame, samples QR | ✓ | (system) | — |
| `shared/sample-images/manifest.yml` | INJECT_MAP photo bindings | ✓ | with `portrait_maria` + 4 themen entries | — |
| `shared/logos/gruene-weiss.png` | P1 + P6 Logo asset | ✓ | 413×118 RGB | document fallback to `gruene-logo-bund-dunkel.png` if missing |
| `shared/assets/wahlkreuz.png` | P3 Wahlkreuz | ✓ | (used in V0) | required (build raises FileNotFoundError) |
| `templates/kandidat-falzflyer-din-lang/samples/qr-mitmachen.png` + `qr-termine.png` | P6 QRs | ✓ | (used in V0) | optional (conditional inject) |
| `bin/render-gallery` | Regen artifacts | ✓ | post-#24 | — |
| `bin/audit-alignment` | Optional audit | ✓ | post-#22/#23 | — |
| `tools/sla_lib/builder/*` | DSL | ✓ | post-#25 | — |

Live-verified at 2026-05-09: `bin/render-gallery`, `bin/audit-alignment`, `bin/check-stale-previews` all present and functional.

---

## Project Constraints (from CLAUDE.md / MEMORY.md)

**No project-level CLAUDE.md** at repo root.

The user's MEMORY.md auto-context covers unrelated projects (Austender, KEBA Wärmepumpe, Tado/HomeKit, Music Assistant, Pi infrastructure, Psychotherapie-site, Issue System tooling). Standing user directives applicable to this work:

- **No "claude" / AI attribution** in commits, code, files (per `feedback_no_claude_attribution.md`).
- **Issue artifacts preserved** (no deletes; archive when done — per `feedback_preserve_issue_artifacts.md`).
- **Reviews must read code themselves** (no diffs in prompts — per `feedback_review_no_code_in_prompt.md`). Plan tasks should not embed code snippets the executor must paste; instead reference file:line locations.
- **Working over theoretical** (per `feedback_working_over_theoretical.md`). Lock practical decisions; don't propose refactors not needed for V1.
- **`/issue:review` runs during `/issue:execute`, never as a precursor to research/plan** (per `feedback_review_in_execute_phase.md`).

---

## Sources

### HIGH confidence
- `templates/kandidat-falzflyer-din-lang/build.py` — full read of 684 lines (codebase §1)
- `templates/kandidat-falzflyer-din-lang/meta.yml` — full read of 188 lines (codebase §2)
- `templates/_smoke/test_kandidat_falzflyer_din_lang.py` — full read of 161 lines (codebase §3)
- `tools/sla_lib/builder/constraints.py:115–518` — constraint factory implementations
- `tools/sla_lib/builder/brand_constraints.py:249–282` — `brand:logo_size_3M` rule (codebase §6)
- `tools/check_ci.py` — full read confirms NO logo/alignment logic (codebase §10)
- `templates/infostand-tent-card-a5-quer/build.py` — full read of 593 lines as reference pattern
- `templates/infostand-tent-card-a5-quer/meta.yml` — V1 brand_overrides + ci_overrides reference
- `tools/sla_lib/tests/test_infostand_tent_card_geometry.py` — 21-invariant geometry test pattern (codebase §4.1)
- `tools/sla_lib/tests/test_tueranhaenger_geometry.py` — 12-invariant pattern + logo-3M assertion (codebase §4.2)
- `templates/_specs/kandidat-falzflyer-din-lang.md` — current spec (drifted; rewrite needed)
- `templates/_specs/wahltag-tueranhaenger.md` — V1 spec rewrite reference pattern
- `improvements/05-kandidat-falzflyer.md` — V1 source-of-truth (`/root/workspace/improvements/05-kandidat-falzflyer.md`, 414 lines)
- `improvements/HANDOFF.md` — broader rollout context (`/root/workspace/improvements/HANDOFF.md`, 139 lines)
- `.issues/archive/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards/RESEARCH.md` + `PLAN.md` — INJECT_MAP precedent
- `.issues/archive/18-v1-layout-for-wahltag-tueranhaenger-composed-hero/RESEARCH.md` + `PLAN.md` — V1 spec rewrite precedent
- `.issues/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band/RESEARCH.md` + `PLAN.md` + build.py — multi-panel rotation contract precedent (rotation NOT applicable to #21)
- `shared/logos/` — listing + Pillow-decoded sizes of all logo assets
- `shared/sample-images/manifest.yml` — confirmed `portrait_maria`, `themen_klimaschutz_solar`, `themen_soziales_kaffeehaus`, `themen_bildung_volksschule`, `themen_wirtschaft_handwerk` all present with crop_focus
- `shared/sample-images/themen/wirtschaft-handwerk.jpg` — file exists (codebase §9)
- **Live empirical run** of `brand:logo_size_3M.check()` against all 5 V1 templates — 4 PASS / 1 (kandidat-falzflyer ×3) FAIL (codebase §7)
- **Live build run** `python3 templates/kandidat-falzflyer-din-lang/build.py` — exits 0; smoke 11/11; structural_check 0 errors

### MEDIUM confidence
- Visual readability of `falzflyer/impressum` 6pt White on Dunkelgrün — accepted with flag for post-render human review (pitfall 9)
- Visual rendering of P1 + P6 logos at 38×22 / 38×34 frame on 3.5:1 wordmark — extrapolated from #20 acceptance (pitfall 11)
- Final P4 Thema 2 body deletion (spec L90) UX impact — accepted "Headline + Foto reicht; Tiefe via QR"

### LOW confidence (needs validation at execution-time)
- None — every critical claim verified against current main worktree state.

---

## Metadata

**Confidence breakdown:**
- Codebase: HIGH (every interface file:line traced; build pipeline executed live)
- Standard Stack: HIGH (Python 3.13 verified; all binaries present; structural_check 0 errors today)
- M-Basis-Konflikt resolution: HIGH (rule executed live against all 5 V1 templates; deterministic output)
- ParaStyle migration table: HIGH (current 12 styles dumped via `_extra_para_styles`; V1 16 styles derived from ISSUE.md + spec L196–216)
- Frame inventory: HIGH (V0 grep'd line-by-line; V1 derived from spec arithmetic + #20 pattern)
- CONSTRAINTS list: HIGH (factory semantics file:line traced; mirrored_x verified live)
- Geometry test plan: HIGH (#20 pattern adapted to 6-panel; ≥18 invariants enumerable)
- Atomic-PR ordering: HIGH (no RED window; M-Basis rule unchanged means no temporal coupling between T01 and other tasks)

**Research date:** 2026-05-09
**Sub-agents used:** synthesized inline (codebase + pitfalls dimensions; 1 raw research file `research/codebase.md` produced as line-level evidence base)
**Raw research file:** `.issues/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix/research/codebase.md`

---

## Suggested PR shape (planner: 11 tasks T01..T11)

| T# | Title | Files | Verification gate |
|---|---|---|---|
| T01 | fix(kandidat-falzflyer): correct M-Basis header-comment + drop logo_size_3M override (RED window self-clears via T05 logo resize) | `templates/kandidat-falzflyer-din-lang/build.py:195–199` (comment), `templates/kandidat-falzflyer-din-lang/meta.yml` (drop `brand:logo_size_3M` override stanza) | structural_check now flags 3 logo violations (expected — closed in T05); other 4 V1 templates remain green (verified by parametric test in T11) |
| T02 | regression(brand): verify M-Basis rule passes on the 4 other V1 templates (no code change; verification commit producing a one-shot script under .issues/<slug>/research/ if helpful, or just the verified-output noted in EXECUTION.md) | (notes only — or a tiny ad-hoc `.issues/<slug>/research/m_basis_verify.txt` log) | All 4 templates green |
| T03 | feat(kandidat-falzflyer): V1 ParaStyles — 10 mutations + 4 NEW (slogan-on-green, quote-on-green, top-title, themen-eyebrow) + meta.yml ci_overrides extend | `build.py` (`_add_styles`), `meta.yml` (`non_ci_styles`) | build runs clean; structural_check still passes (V0 layout untouched, just style table grew) |
| T04 | refactor(kandidat-falzflyer): build_template + build_preview split + INJECT_MAP scaffold + build_doc alias (per #20 pattern) | `build.py` | structural_check unchanged; build emits SLA without inline image data on INJECT_MAP frames; `build()` calls build_preview which injects |
| T05 | feat(kandidat-falzflyer): Top-Bands × 4 + Top-Titles × 5 + Logo asset swap (P1+P6 → gruene-weiss.png 38mm; P2 logo deleted) + P6 Hintergrund vollflächig polygon | `build.py` (frame additions in `_add_front`, `_add_back`) | smoke test `test_panel_content_within_safe_width` filter must be extended in T11; structural_check shows new V1 frames; logo_size_3M passes (RED window from T01 closes here) |
| T06 | feat(kandidat-falzflyer): P1 Cover layout — Portrait y/h shift + Name-Card polygon + Name fcolor flip + Slogan switches to slogan-on-green | `build.py` | smoke test `test_18_plus_slot_annames` may grow assertion; structural_check 0 errors |
| T07 | feat(kandidat-falzflyer): P2 Mein Plan + P3 Wahltag — P2 Body-Backing + Body fcolor flip + headline y-shift; P3 frame y-shifts (Wahlkreuz/Closer-HL/Datum-Akzent/URL) | `build.py` | structural_check 0 errors |
| T08 | feat(kandidat-falzflyer): P4 + P5 Themen + P6 Kontakt — themen photos h 24→44; eyebrows + photo + body chain; Hellgrün-3mm-Trenner pair; P5 Thema 4 photo via `themen_wirtschaft_handwerk`; P4 Thema 2 body deletion; P6 2-column kontakt + QRs + captions + footer Logo + Impressum | `build.py` | structural_check 0 errors; INJECT_MAP populated for 5 photos; build_preview produces page-02 with photos via library |
| T09 | feat(kandidat-falzflyer): V1 CONSTRAINTS list (22 entries — replaces V0's 9) | `build.py` | structural_check 0 errors; ALL 22 CONSTRAINTS green |
| T10 | chore(kandidat-falzflyer): regen template.sla + render-gallery + meta.yml SHA bump + brand_overrides cleanup (REMOVE 4: image_text_overlap, image_fills_frame, visual_adjacency_drift; logo_size_3M was dropped in T01) | `template.sla`, `page-01.png`, `page-02.png`, `preview.pdf`, `meta.yml`, site/public mirror | check-stale-previews PASS; structural_check 0 errors / 2 skipped (was 6) |
| T11 | test+docs(kandidat-falzflyer): smoke test additions + spec rewrite + NEW geometry test (≥18 invariants + parametric M-Basis regression on 5 V1 templates) + README update + brief §10 + EXECUTION.md + HANDOFF.md V1 rollout #15 marked complete + close issue | `_smoke/`, `_specs/`, `tools/sla_lib/tests/test_kandidat_falzflyer_geometry.py` (NEW), `README.md`, `shared/brand/DESIGN-SYSTEM-BRIEF.md`, `improvements/HANDOFF.md`, `.issues/<slug>/EXECUTION.md`, `.issues/<slug>/ISSUE.md` status | All tests pass; spec_check exits 0; HANDOFF.md V1 sequence row marked done |

**Plus artifact commits** (RESEARCH.md ✓, PLAN.md, EXECUTION.md). ~13 commits total.

**Codex iter1/iter2 SKIPPED** (locked decision #13 — single-page-per-side multi-panel template; brand:image_fills_frame + geometry test invariants + structural_check + smoke are sufficient regression detectors).

Next: `/issue:plan` turns this RESEARCH into XML-tagged tasks for the executor.

---

## Files-touched inventory (count: 14 modified + 2 new = 16; plus 4 read-only verification touches)

**Modified in worktree:**
1. `templates/kandidat-falzflyer-din-lang/build.py` (T01, T03–T09)
2. `templates/kandidat-falzflyer-din-lang/meta.yml` (T01, T03, T10)
3. `templates/kandidat-falzflyer-din-lang/template.sla` (regen T10)
4. `templates/kandidat-falzflyer-din-lang/page-01.png` (regen T10)
5. `templates/kandidat-falzflyer-din-lang/page-02.png` (regen T10)
6. `templates/kandidat-falzflyer-din-lang/preview.pdf` (regen T10)
7. `templates/kandidat-falzflyer-din-lang/README.md` (T11)
8. `templates/_specs/kandidat-falzflyer-din-lang.md` (T11 rewrite)
9. `templates/_smoke/test_kandidat_falzflyer_din_lang.py` (T11 extend)
10. `shared/brand/DESIGN-SYSTEM-BRIEF.md` (T11 §10 row)
11. `improvements/HANDOFF.md` (T11 V1 rollout #15 mark complete)
12. `site/public/kandidat-falzflyer-din-lang/` (auto-mirror via render-gallery T10)
13. `.issues/<slug>/EXECUTION.md` (T11 final close)
14. `.issues/<slug>/ISSUE.md` (T11 status flip to closed)

**New files:**
1. `tools/sla_lib/tests/test_kandidat_falzflyer_geometry.py` (T11 NEW, ≥18 invariants)
2. `.issues/<slug>/PLAN.md` (created by `/issue:plan`)

**Read-only verification (no edits — referenced for the parametric M-Basis regression test):**
- `templates/wahlaufruf-postkarte-a6-quer/` (already trim-konform)
- `templates/wahltag-tueranhaenger/` (already trim-konform)
- `templates/themen-plakat-a3-quer/` (already trim-konform)
- `templates/infostand-tent-card-a5-quer/` (already trim-konform)

**OUT of scope (locked NOT-touched):**
- `tools/check_ci.py` (no logo/alignment logic; locked #2)
- `tools/sla_lib/builder/brand_constraints.py` (rule already trim-konform; locked #1)

---

## Blockers

**None.** All open questions resolved with locked decisions:

1. M-Basis-Konflikt → comment fix + 3 logo resizes + override drop; no tool change (locked #1).
2. Slogan-on-Green ParaStyle → parallel new style alongside `slogan` mutation (locked #3).
3. `themen-wirtschaft.jpg` → already in library (locked #7).
4. Body fontsize 9pt→10pt → accept; content discipline noted (pitfall 8).
5. P6 Impressum 6pt readability → accept; flag for post-render human review (pitfall 9).

The planner can produce zero-ambiguity XML-tagged tasks from this RESEARCH.md.
