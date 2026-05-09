# Plan: V1 layout for `wahltag-tueranhaenger` (Composed Hero)

<objective>
What this plan accomplishes: Implement V1 "Composed Hero" layout for `templates/wahltag-tueranhaenger/` per `improvements/02-wahltag-tueranhaenger.md` §"Variante 1" — front Brand-Bar shrink + Hellgrün-Akzent + Wahlkreuz-Band reflow + Bullets-Card; back Portrait-Card + Visitenkarten-Footer + repositioned QR with white backing + Bund-Dunkel logo deletion — with 5 new `*-on-green` ParaStyles, a 15-entry CONSTRAINTS list using REAL annames, regenerated artifacts, removed stale `brand_overrides`, full spec rewrite, invariant-pinning tests, and a session-history brief row.

Why it matters: Second of five V1 implementations (#15 sequence). Reuses the `*-on-green` ParaStyle pattern landed in #17. Validates that the post-#23 alignment-rule registry (14 rules) handles non-Zeitung composition cleanly.

Scope:
- IN: build.py edits (front + back), 5 new ParaStyles, 15-entry CONSTRAINTS list, meta.yml ci_overrides update, regen via `bin/render-gallery`, meta.yml previews_for_sla SHA bump, removal of 2-3 stale brand_overrides + reason update on `brand:visual_adjacency_drift`, full spec rewrite, NEW `tools/sla_lib/tests/test_tueranhaenger_geometry.py`, brief §10 session-history row.
- OUT: V2 "Vertical Stripe" / V3 "Manifesto" (backlog), pixel-diff visual review (human PR-review), smoke-test rewrite (RESEARCH.md verified all 11 assertions pass V1 unmodified — locked decision #8), new `same_x_right`/`same_y_bottom` constraint helpers (out of #18 scope; `brand:visual_adjacency_drift` override stays per locked decision #12), opacity-on-TextFrame DSL extension (locked decision #6 — drop `opacity 85%`).

No CONTEXT.md exists for this issue — decisions follow RESEARCH.md's 15 locked decisions, which override ISSUE.md where they conflict (ISSUE.md has 6 documented errors, see "Risks and verification" section).
</objective>

<skills>
No workspace skills directory present (`.claude/skills/` not found in worktree). Executor follows project CLAUDE.md (none in repo) and the inline `<dont>` blocks per task.
</skills>

<context>
Issue: @.issues/18-v1-layout-for-wahltag-tueranhaenger-composed-hero/ISSUE.md
Research (synthesized, locked decisions): @.issues/18-v1-layout-for-wahltag-tueranhaenger-composed-hero/RESEARCH.md
Codebase evidence (line-level): @.issues/18-v1-layout-for-wahltag-tueranhaenger-composed-hero/research/codebase.md
Pitfalls (predictive verification): @.issues/18-v1-layout-for-wahltag-tueranhaenger-composed-hero/research/pitfalls.md
Design package: @improvements/02-wahltag-tueranhaenger.md (lives at workspace root, not committed; reference only)
Reference plan (V1 pattern precedent): @.issues/archive/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight/PLAN.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

### BRAND_CONSTRAINTS registry — exactly 14 rules (post-#23)
From `tools/sla_lib/builder/brand_constraints.py:1052-1170`:
```
1.  brand:color_palette
2.  brand:font_family
3.  brand:line_spacing_0.9
4.  brand:hl_sl_distance_x2     # NOT brand:hl_sub_gap_2x (ISSUE.md typo)
5.  brand:logo_size_3M
6.  brand:text_on_green
7.  brand:bleed_3mm
8.  brand:wahlkreuz_colored_bg
9.  brand:inside_page
10. brand:spine_safety
11. brand:visual_adjacency_drift   # 4-axis check + declaration-disagreement
12. brand:bleed_coverage           # facing_pages early-return → no-op here
13. brand:image_text_overlap
14. brand:cover_extent_match
```
**`brand:image_in_container_flush` and `brand:portrait_column_alignment` DO NOT EXIST.** Folded into `brand:visual_adjacency_drift` per archived #23 PLAN.md:189. Tasks must NOT reference them.

### Constraint factories (from `tools/sla_lib/builder/constraints.py`)
```python
def aligned_below(below, above, gap_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
    # ARG ORDER: below first (the frame hanging beneath), above second (the anchor).
    # Asserts below.x == above.x AND below.y == above.y + above.h + gap_mm.
def same_x(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def same_y(*targets, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def same_size(*targets, axis: str = "both", tolerance_mm: float = 0.5, name: str = "") -> Constraint  # axis ∈ {"both","w","h"}
def mirrored_x(left, right, axis_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def mirrored_y(top, bottom, axis_mm: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def inside(child, parent, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def distance_x(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def distance_y(a, b, equals: float, tolerance_mm: float = 0.5, name: str = "") -> Constraint
def same_style(*targets, name: str = "") -> Constraint
# Resolver matches on `anname` exactly (case-sensitive). Snake-case stub names
# (brand_bar_top, kandidat_name, stat_card_*) all miss → emit `_missing_violation`.
```

### Primitives (from `tools/sla_lib/builder/primitives.py`)
```python
@dataclass
class Polygon(_Frame):
    fill: Optional[str] = None      # "Dunkelgrün" | "Hellgrün" | "Magenta" | "Gelb" | "White" | ...
    layer: int = 0                  # use LAYER_HINTERGRUND=0 for V1 polygons
    anname: str = ""
    shape: str = "rect"             # default rect (V1 needs no ellipses)

@dataclass
class ImageFrame(_Frame):
    inline_image_data: Optional[str] = None
    inline_image_ext: Optional[str] = None
    local_scale: tuple[float, float] = (1.0, 1.0)  # MUST be set explicitly; #17 used (0.130, 0.130) for 18.9mm logo
    layer: int = 0
    anname: str = ""

@dataclass
class TextFrame(_Frame):
    text: str = ""
    style: str = ""                 # ParaStyle name
    fcolor: str = ""                # frame-level color override
    runs: Optional[list] = None     # list of Run instances
    layer: int = 0
    anname: str = ""
# NO `opacity` parameter exists on TextFrame — ISSUE.md's "opacity 85%" is unsupported.

@dataclass
class Run:
    text: str = ""
    fcolor: Optional[str] = None    # overrides paragraph_style.fcolor
    paragraph_style: Optional[str] = None
    separator: Optional[str] = None # "para" | None
```

### ParaStyle (from `tools/sla_lib/builder/styles.py`)
```python
@dataclass
class ParaStyle:
    name: str
    font: Optional[str] = None
    fontsize: Optional[float] = None
    linesp: Optional[float] = None       # leading in pt
    linesp_mode: int = 0                 # 0 = fixed leading
    align: Optional[int] = None          # 0=left, 1=center, 2=right
    fcolor: Optional[str] = None
    language: str = "de"
```

### Layer constants (from `templates/wahltag-tueranhaenger/build.py:44-48`)
```python
LAYER_HINTERGRUND = 0     # backgrounds (all V1 NEW polygons)
LAYER_BILDER = 1          # images (Logo, Portrait, Wahlkreuz, QR)
LAYER_TEXT = 2            # text frames
LAYER_STANZKONTUR = 3     # die-cut only — DO NOT add V1 polygons here
```

### Doc geometry constants (from build.py:40-42)
```python
TRIM_W_MM = 105.0
TRIM_H_MM = 250.0
BLEED_MM  = 2.0   # 2mm bleed (die-cut format) — `brand:bleed_3mm` permanent override
```

### Page-center math (for mirrored_x)
- Panel width 105mm → page center x = 52.5mm
- Page bleed extents: x ∈ [-2, 107], y ∈ [-2, 252]

### V1 NEW Polygons (5 add + 1 frame deletion)
```
1. Hellgrün-Akzent       (front)  Polygon  x=-2 y=14  w=109 h=4   fill=Hellgrün     layer=0
2. Bullets-Card          (front)  Polygon  x=-2 y=192 w=109 h=58  fill=Hellgrün     layer=0
3. Portrait-Card         (back)   Polygon  x=15 y=70  w=75  h=100 fill=Hellgrün     layer=0
4. Visitenkarten-Footer  (back)   Polygon  x=-2 y=178 w=109 h=72  fill=Dunkelgrün   layer=0
5. QR White-Backing      (back)   Polygon  x=68 y=208 w=30  h=30  fill=White        layer=0
DEL: ImageFrame "Logo Grüne (Bund-Dunkel, back)" (current build.py:300-309)
```

### V1 NEW ParaStyles (5; #17 parallel-style pattern)
```python
ParaStyle(name="tueranhaenger/body-on-green",
          font="Gotham Narrow Book", fontsize=11, linesp=14,
          linesp_mode=0, align=0, fcolor="White", language="de")

ParaStyle(name="tueranhaenger/url-on-green",
          font="Vollkorn Black Italic", fontsize=11, linesp=14,
          linesp_mode=0, align=0, fcolor="Gelb", language="de")

ParaStyle(name="tueranhaenger/cand-name-on-green",
          font="Gotham Narrow Bold", fontsize=18, linesp=20,
          linesp_mode=0, align=0, fcolor="White", language="de")

ParaStyle(name="tueranhaenger/cand-pos-on-green",
          font="Gotham Narrow Book Italic", fontsize=10, linesp=12,
          linesp_mode=0, align=0, fcolor="White", language="de")

ParaStyle(name="tueranhaenger/impressum-on-green",
          font="Gotham Narrow Book", fontsize=6, linesp=7,
          linesp_mode=0, align=0, fcolor="White", language="de")
```

### V1 CONSTRAINTS list (final, real annames, correct gaps — quote into build.py)
```python
CONSTRAINTS = [
    # FRONT — Hellgrün-Akzent below Brand-Bar (touching, gap 0)
    aligned_below("Hellgrün-Akzent", "Brand-Bar (Vorderseite)",
                  gap_mm=0.0, name="akzent_below_brandbar"),
    # FRONT — Hellgrün-Band absolute pin via distance_y to Akzent
    distance_y("Hellgrün-Akzent", "Hellgrün-Band (Wahlkreuz)",
               equals=45.0, name="band_below_akzent_45mm"),
    # FRONT — Wahlkreuz centered on panel (panel center x=52.5)
    mirrored_x("Hellgrün-Band (Wahlkreuz)", "Wahlkreuz (Hero)",
               axis_mm=52.5, name="wahlkreuz_panel_center"),
    # FRONT — Wahlkreuz inside Hellgrün-Band
    inside("Wahlkreuz (Hero)", "Hellgrün-Band (Wahlkreuz)",
           name="wahlkreuz_in_band"),
    # FRONT — Headline below Hellgrün-Band (small gap intentional, 11mm)
    aligned_below("Headline-Wahltag", "Hellgrün-Band (Wahlkreuz)",
                  gap_mm=11.0, name="headline_below_band"),
    # FRONT — HL→Sub distance (38mm pragmatic for 250mm format)
    distance_y("Headline-Wahltag", "Sub-Headline",
               equals=38.0, name="hl_to_sub_38mm_format_pragmatic"),
    # FRONT — Bullets-Card and Hellgrün-Akzent share full-bleed x (both x=-2)
    same_x("Bullets-Card", "Hellgrün-Akzent",
           name="bullets_card_full_bleed_x"),
    # FRONT — Bullet-Liste inside Bullets-Card
    inside("Bullet-Liste", "Bullets-Card", name="bullets_in_card"),

    # BACK — Brand-Bar mirror of front (same height, 16mm = 14 + 2 bleed)
    same_size("Brand-Bar (Vorderseite)", "Brand-Bar (Rückseite)",
              axis="h", name="brand_bar_h_pair"),
    # BACK — Portrait inside Portrait-Card (5mm uniform inset)
    inside("Kandidat-Portrait", "Portrait-Card",
           name="portrait_in_card"),
    # BACK — Kandidat-Name below Portrait (~14mm gap)
    aligned_below("Kandidat-Name", "Kandidat-Portrait",
                  gap_mm=14.0, name="name_below_portrait"),
    # BACK — Kandidat-Position below Name (~1mm gap)
    aligned_below("Kandidat-Position", "Kandidat-Name",
                  gap_mm=1.0, name="position_below_name"),
    # BACK — Kontakt-URL on Visitenkarten-Footer (containment)
    inside("Kontakt-URL", "Visitenkarten-Footer", name="url_in_footer"),
    inside("Kontakt-Info", "Visitenkarten-Footer", name="info_in_footer"),
    # BACK — QR backing fully contains QR
    inside("QR-Code (back)", "QR White-Backing", name="qr_in_backing"),
]
```

### `meta.yml::brand_overrides` post-V1 disposition
```
brand:line_spacing_0.9        KEEP — 6 of 7 styles still drift (only Headline → 25.2)
brand:hl_sl_distance_x2       KEEP — 50% formula gap chosen for 250mm format (refresh reason text to mention #18)
brand:logo_size_3M            REMOVE — both white logos = 18.9mm; Bund-Dunkel deleted
brand:text_on_green           KEEP, but TEST removability after V1 (rule looks for ^ci/h* style — V1 uses tueranhaenger/* → likely no-op)
brand:bleed_3mm               KEEP — permanent (die-cut)
brand:wahlkreuz_colored_bg    TEST removability — Hellgrün-Band overlap may now satisfy
brand:font_family             KEEP — cand-pos & cand-pos-on-green use "Gotham Narrow Book Italic"
brand:visual_adjacency_drift  KEEP — combinatorial warning floor (refresh reason text)
brand:image_text_overlap      REMOVE — V1 has zero partial overlaps (verified arithmetically)
```

### Smoke test status
Per RESEARCH.md locked decision #8 + pitfalls P2.7: all 11 assertions in `templates/_smoke/test_wahltag_tueranhaenger.py` pass V1 unmodified. **No smoke-test rewrite task in this plan.**

</interfaces>

Key files:
@templates/wahltag-tueranhaenger/build.py — primary edit target (459 lines; ParaStyles 72-141, front frames 157-260, back frames 272-411, CONSTRAINTS 431-454)
@templates/wahltag-tueranhaenger/meta.yml — ci_overrides + brand_overrides + previews_for_sla SHA (164 lines)
@templates/_specs/wahltag-tueranhaenger.md — full rewrite (currently 10-error drifted from pre-V1; ~420 lines)
@shared/brand/DESIGN-SYSTEM-BRIEF.md — append session-history row at §10 (line 153 area)
@shared/brand/SPEC-WRITING-GUIDE.md — read §11-12 (constraints expressed in PROSE only, never duplicated as YAML)
@improvements/02-wahltag-tueranhaenger.md — design source (workspace root, NOT committed); Session-History seed row at §"Session-History"
@bin/render-gallery — regenerates template.sla + page-NN.png + preview.pdf + meta.yml::previews_for_sla SHA + site/public mirror
@bin/audit-alignment — post-V1 verification gate (must report 0 ERROR-severity violations)
@bin/check-stale-previews — CI gate (must exit 0 after regen)
@tools/sla_lib/tests/test_zeitung_geometry.py — invariant-pinning test pattern to copy for T08
@.issues/archive/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight/PLAN.md — V1 pattern precedent
@.issues/archive/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight/EXECUTION.md — execution log style
</context>

<commit_format>
Format: conventional with numeric issue prefix (per `.issues/config.yaml::commits.format=conventional, prefix=true`)
Example: `18: feat(wahltag-tueranhaenger): add 5 *-on-green ParaStyles`
Pattern: `18: <type>(<scope>): <subject>` — types: feat, fix, test, refactor, docs, chore.
One commit per task. Artifact commits (PLAN.md, EXECUTION.md) use `docs(issues): ...`.
</commit_format>

<tasks>

<task id="T01" type="auto" tdd="false">
  <name>Task 1: Add 5 *-on-green ParaStyles + update meta.yml::ci_overrides.non_ci_styles</name>
  <files>templates/wahltag-tueranhaenger/build.py, templates/wahltag-tueranhaenger/meta.yml</files>
  <depends-on>none</depends-on>
  <action>
  Add 5 NEW ParaStyles to `templates/wahltag-tueranhaenger/build.py` directly after the existing `tueranhaenger/impressum` ParaStyle declaration (after line 141 — search for `name="tueranhaenger/impressum"` and append below the closing `))` of that block). Use the exact spec from `<interfaces>` above:

  ```python
  doc.add_para_style(ParaStyle(
      name="tueranhaenger/body-on-green",
      font="Gotham Narrow Book",
      fontsize=11,
      linesp=14,
      linesp_mode=0,
      align=0,
      fcolor="White",
      language="de",
  ))
  doc.add_para_style(ParaStyle(
      name="tueranhaenger/url-on-green",
      font="Vollkorn Black Italic",
      fontsize=11,
      linesp=14,
      linesp_mode=0,
      align=0,
      fcolor="Gelb",
      language="de",
  ))
  doc.add_para_style(ParaStyle(
      name="tueranhaenger/cand-name-on-green",
      font="Gotham Narrow Bold",
      fontsize=18,           # bumped from 14 per ISSUE.md V1 spec
      linesp=20,
      linesp_mode=0,
      align=0,
      fcolor="White",
      language="de",
  ))
  doc.add_para_style(ParaStyle(
      name="tueranhaenger/cand-pos-on-green",
      font="Gotham Narrow Book Italic",
      fontsize=10,
      linesp=12,
      linesp_mode=0,
      align=0,
      fcolor="White",
      language="de",
  ))
  doc.add_para_style(ParaStyle(
      name="tueranhaenger/impressum-on-green",
      font="Gotham Narrow Book",
      fontsize=6,
      linesp=7,
      linesp_mode=0,
      align=0,
      fcolor="White",
      language="de",
  ))
  ```

  Also in this commit: update `tueranhaenger/headline` ParaStyle in-place — change `linesp=30` → `linesp=25.2` (Quickguide-konform 0.9× of fontsize 28). This brings Headline into compliance with `brand:line_spacing_0.9` for that one style. Other 6 styles still drift; the override stays. (RESEARCH.md confidence HIGH; per ISSUE.md V1 spec line 30.)

  Update `templates/wahltag-tueranhaenger/meta.yml::ci_overrides.non_ci_styles` (currently lines 73-80) to APPEND the 5 new style names. Keep all existing entries; final list is 12 items in order:

  ```yaml
  ci_overrides:
    non_ci_styles:
      - "tueranhaenger/headline"
      - "tueranhaenger/sub"
      - "tueranhaenger/body"
      - "tueranhaenger/cand-name"
      - "tueranhaenger/cand-pos"
      - "tueranhaenger/url"
      - "tueranhaenger/impressum"
      - "tueranhaenger/body-on-green"
      - "tueranhaenger/url-on-green"
      - "tueranhaenger/cand-name-on-green"
      - "tueranhaenger/cand-pos-on-green"
      - "tueranhaenger/impressum-on-green"
  ```

  Build.py must still execute cleanly after this edit (the 5 new styles are unused references at this point — that is fine; T02 and T03 wire frames to them).

  Commit message: `18: feat(wahltag-tueranhaenger): add 5 *-on-green ParaStyles + headline linesp 30→25.2`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero && PYTHONPATH=tools python3 templates/wahltag-tueranhaenger/build.py && python3 tools/check_ci.py templates/wahltag-tueranhaenger/template.sla</automated>
    <manual>none</manual>
  </verify>
  <done>
  - 5 new ParaStyle declarations present in build.py after existing `tueranhaenger/impressum`
  - `tueranhaenger/headline` linesp updated to 25.2 (was 30)
  - `meta.yml::ci_overrides.non_ci_styles` contains all 12 entries (7 original + 5 new)
  - `python3 templates/wahltag-tueranhaenger/build.py` exits 0 with no exception
  - `tools/check_ci.py` returns same warning count as baseline (no new errors)
  </done>
  <dont>
  - Don't mutate fcolor on existing `tueranhaenger/body`, `cand-name`, `cand-pos`, `url`, `impressum` styles (locked decision #7 — parallel-style migration pattern from #17)
  - Don't add `opacity` to any ParaStyle — DSL has no opacity field on text (locked decision #6)
  - Don't change fonts on the new styles to anything outside `shared/ci.yml::fonts` (Gotham Narrow {Book,Bold,Black,Ultra} + Vollkorn Black Italic; "Gotham Narrow Book Italic" stays under existing `brand:font_family` override)
  - Don't reference snake_case stub names anywhere — annames are exact strings from build.py
  - Don't drop existing entries from `non_ci_styles` (cleanup of orphaned styles is out of scope; existing styles still used by current build until T02/T03 land)
  </dont>
</task>

<task id="T02" type="auto" tdd="false">
  <name>Task 2: V1 front layout — Brand-Bar shrink + Hellgrün-Akzent + Wahlkreuz-Band reflow + Headline stack + Bullets-Card</name>
  <files>templates/wahltag-tueranhaenger/build.py</files>
  <depends-on>T01</depends-on>
  <action>
  Edit `templates/wahltag-tueranhaenger/build.py` PAGE 0 frame block (lines 155-260). Apply each delta below in the order they appear in build.py. Quote the exact target before each edit; the existing values are in parentheses. All polygons go on `LAYER_HINTERGRUND` (idx 0).

  **(a) Brand-Bar (Vorderseite)** at lines 157-165 — change `h_mm=20 + BLEED_MM` → `h_mm=14 + BLEED_MM` (visible band 14mm; total with bleed 16mm). Width and x_mm unchanged.

  **(b) Logo Grüne (weiss, top)** at lines 171-178 — change frame size and `local_scale`:
  - `w_mm=35` → `w_mm=18.9`
  - `h_mm=10` → `h_mm=5.7`
  - `local_scale=(0.240, 0.240)` → `local_scale=(0.130, 0.130)`
  - `x_mm`, `y_mm` unchanged (10, 8)

  **(c) NEW Polygon "Hellgrün-Akzent"** — INSERT directly after the Logo Grüne (weiss, top) ImageFrame block (after line 178's closing `))` ). Place it BEFORE the Hellgrün-Band block:
  ```python
  page0.add(Polygon(
      x_mm=-BLEED_MM,
      y_mm=14,
      w_mm=TRIM_W_MM + 2 * BLEED_MM,
      h_mm=4,
      fill="Hellgrün",
      layer=LAYER_HINTERGRUND,
      anname="Hellgrün-Akzent",
  ))
  ```
  This creates a 4mm Hellgrün strip directly under the Brand-Bar (touches at y=14).

  **(d) Hellgrün-Band (Wahlkreuz)** at lines 190-198 — change `y_mm=65` → `y_mm=63` and `h_mm=60` → `h_mm=64`. Width and x_mm unchanged.

  **(e) Wahlkreuz (Hero)** at lines 200-208 — change `x_mm=27.5` → `x_mm=25`, `w_mm=50` → `w_mm=55`, `h_mm=50` → `h_mm=55`. `y_mm` stays 70. Result: image 25..80 × 70..125 mm, centered on x=52.5 panel center.

  **(f) Headline-Wahltag** at lines 212-223 — change `y_mm=128` → `y_mm=138`, `h_mm=28` → `h_mm=32`. (Linesp change is in T01 — ParaStyle edit, not frame edit.)

  **(g) Sub-Headline** at lines 226-233 — change `y_mm=160` → `y_mm=176`. Width/height unchanged.

  **(h) NEW Polygon "Bullets-Card"** — INSERT directly before the Bullet-Liste TextFrame (current line 236):
  ```python
  page0.add(Polygon(
      x_mm=-BLEED_MM,
      y_mm=192,
      w_mm=TRIM_W_MM + 2 * BLEED_MM,
      h_mm=58,
      fill="Hellgrün",
      layer=LAYER_HINTERGRUND,
      anname="Bullets-Card",
  ))
  ```

  **(i) Bullet-Liste TextFrame** at lines 236-247 — change `y_mm=175` → `y_mm=200`, `h_mm=60` → `h_mm=40`. Switch ParaStyle: `style="tueranhaenger/body"` → `style="tueranhaenger/body-on-green"`. In the `runs=[Run(...)]` block, switch `paragraph_style="tueranhaenger/body"` → `paragraph_style="tueranhaenger/body-on-green"`. Text content unchanged.

  **(j) Impressum (front)** at lines 250-260 — switch ParaStyle: `style="tueranhaenger/impressum"` → `style="tueranhaenger/impressum-on-green"`. Update Run's `paragraph_style` analogously. y/x/h unchanged. (RESEARCH.md notes white-on-Hellgrün has WCAG contrast concerns — surface in spec rewrite at T07 as a known issue, do not change geometry here.)

  Do NOT touch the DoorHangerCutout block (lines 263-268) — Stanzkontur layer is unchanged.

  Commit message: `18: feat(wahltag-tueranhaenger): V1 front layout — Brand-Bar shrink + Hellgrün-Akzent + Wahlkreuz-Band + Headline stack + Bullets-Card`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero && PYTHONPATH=tools python3 templates/wahltag-tueranhaenger/build.py && PYTHONPATH=tools python3 -m unittest templates._smoke.test_wahltag_tueranhaenger</automated>
    <manual>none</manual>
  </verify>
  <done>
  - Brand-Bar (Vorderseite) h_mm == 14 + BLEED_MM
  - Logo Grüne (weiss, top): w_mm=18.9, h_mm=5.7, local_scale=(0.130, 0.130)
  - NEW Polygon "Hellgrün-Akzent" present at (-2, 14, 109, 4) Hellgrün on layer 0
  - Hellgrün-Band (Wahlkreuz) at (-2, 63, 109, 64)
  - Wahlkreuz (Hero) at (25, 70, 55, 55)
  - Headline-Wahltag y=138 h=32
  - Sub-Headline y=176
  - NEW Polygon "Bullets-Card" present at (-2, 192, 109, 58) Hellgrün on layer 0
  - Bullet-Liste y=200 h=40, style=tueranhaenger/body-on-green
  - Impressum (front) style=tueranhaenger/impressum-on-green
  - `python3 templates/wahltag-tueranhaenger/build.py` exits 0
  - All 11 smoke tests still pass (locked decision #8 verified)
  </done>
  <dont>
  - Don't put any new V1 polygon on `LAYER_STANZKONTUR` (idx 3) — would silently fail printability and break `test_stanzkontur_polygons_present_on_layer`
  - Don't add a 5th polygon to the Stanzkontur layer — smoke test counts exactly 4 (outer+hole on each page)
  - Don't change the Wahlkreuz inline image data, scale_type, or ratio — only x/w/h
  - Don't add an `opacity=` kwarg anywhere — TextFrame primitive has no such field (locked decision #6)
  - Don't reference `brand:image_in_container_flush` or `brand:portrait_column_alignment` in any comment — those rules don't exist (locked decision #1)
  - Don't reuse `Hellgrün-Band (Wahlkreuz)` anname for the new Akzent — they are distinct polygons. Anname `Hellgrün-Akzent` exactly.
  - Don't widen Bullet-Liste beyond w_mm=85 (stays inside Bullets-Card 109mm-wide bleed polygon by design)
  </dont>
</task>

<task id="T03" type="auto" tdd="false">
  <name>Task 3: V1 back layout — Brand-Bar shrink + DELETE Bund-Dunkel logo + Portrait-Card + Visitenkarten-Footer + QR backing</name>
  <files>templates/wahltag-tueranhaenger/build.py</files>
  <depends-on>T01</depends-on>
  <action>
  Edit `templates/wahltag-tueranhaenger/build.py` PAGE 1 frame block (lines 270-411). Apply each delta below in the order they appear in build.py. All NEW polygons on `LAYER_HINTERGRUND` (idx 0).

  **(a) Brand-Bar (Rückseite)** at lines 272-280 — change `h_mm=20 + BLEED_MM` → `h_mm=14 + BLEED_MM` (mirrors front). Width / x_mm unchanged.

  **(b) Logo Grüne (weiss, back-band)** at lines 285-292 — change `w_mm=35` → `w_mm=18.9`, `h_mm=10` → `h_mm=5.7`, `local_scale=(0.240, 0.240)` → `local_scale=(0.130, 0.130)`. x/y unchanged (10, 8).

  **(c) DELETE the entire `Logo Grüne (Bund-Dunkel, back)` ImageFrame block** (lines 294-309 inclusive — covers the comment block + `if logo_brand_path.exists():` + `page1.add(ImageFrame(...))` for that frame). Delete the `logo_brand_path = HERE.parents[1] / "shared" / "logos" / "gruene-logo-bund-dunkel.png"` line and the entire `if`/`page1.add(...)` block. The asset file stays on disk (4 other templates still use it — verified by `grep -rln gruene-logo-bund-dunkel templates/`).

  **(d) NEW Polygon "Portrait-Card"** — INSERT directly before the Kandidat-Portrait ImageFrame (currently around line 323, but after deletion of (c) the line number shifts):
  ```python
  page1.add(Polygon(
      x_mm=15,
      y_mm=70,
      w_mm=75,
      h_mm=100,
      fill="Hellgrün",
      layer=LAYER_HINTERGRUND,
      anname="Portrait-Card",
  ))
  ```

  **(e) Kandidat-Portrait** at current line 323-330 — change `h_mm=85` → `h_mm=90`. x/y/w unchanged (20, 75, 65). Result: portrait 20..85 × 75..165 mm, sits inside Portrait-Card (15..90 × 70..170) with 5mm uniform inset on left/top/right, 5mm inset on bottom.

  **(f) Kandidat-Name TextFrame** at lines 334-341 — change `y_mm=168` → `y_mm=184`. Switch `style="tueranhaenger/cand-name"` → `style="tueranhaenger/cand-name-on-green"`. Update Run's `paragraph_style` analogously. h_mm stays 10. (The fontsize bump 14→18 is encoded in the new ParaStyle from T01, not on the frame.)

  **(g) Kandidat-Position TextFrame** at lines 344-351 — change `y_mm=178` → `y_mm=196`. Switch `style="tueranhaenger/cand-pos"` → `style="tueranhaenger/cand-pos-on-green"`. Update Run's `paragraph_style`. h/w/x unchanged. **DO NOT add any opacity parameter** (locked decision #6 — DSL doesn't support it; ISSUE.md's "opacity 85%" is dropped).

  **(h) NEW Polygon "Visitenkarten-Footer"** — INSERT directly before the Kontakt-URL TextFrame (currently around line 354):
  ```python
  page1.add(Polygon(
      x_mm=-BLEED_MM,
      y_mm=178,
      w_mm=TRIM_W_MM + 2 * BLEED_MM,
      h_mm=72,
      fill="Dunkelgrün",
      layer=LAYER_HINTERGRUND,
      anname="Visitenkarten-Footer",
  ))
  ```
  The footer extends from y=178 to y=250 (full bleed bottom). Encloses Kandidat-Name (184..195), Kandidat-Position (196..204), Kontakt-URL (210..218), Kontakt-Info (218..238), and Impressum back (242..248).

  **(i) Kontakt-URL TextFrame** at lines 354-361 — change `y_mm=200` → `y_mm=210`. Switch `style="tueranhaenger/url"` → `style="tueranhaenger/url-on-green"`. Update Run's `paragraph_style`. w_mm stays 50, x stays 10, h stays 8.

  **(j) Kontakt-Info TextFrame** at lines 364-372 — change `y_mm=210` → `y_mm=218`. Switch `style="tueranhaenger/body"` → `style="tueranhaenger/body-on-green"`. Update Run's `paragraph_style`. w/h/x unchanged.

  **(k) QR-Code (back) ImageFrame** at lines 382-389 — change `x_mm=65` → `x_mm=70`, `y_mm=200` → `y_mm=210`, `w_mm=30` → `w_mm=26`, `h_mm=30` → `h_mm=26`. Result: QR at 70..96 × 210..236.

  **(l) NEW Polygon "QR White-Backing"** — INSERT directly after the QR-Code (back) ImageFrame block (so backing renders behind QR? — both are on different layers; backing on LAYER_HINTERGRUND=0, QR on LAYER_BILDER=1; layer 0 paints first → backing IS behind QR even though listed after in code):
  ```python
  page1.add(Polygon(
      x_mm=68,
      y_mm=208,
      w_mm=30,
      h_mm=30,
      fill="White",
      layer=LAYER_HINTERGRUND,
      anname="QR White-Backing",
  ))
  ```
  Backing extends 2mm beyond QR on each side (68..98 × 208..238 vs QR 70..96 × 210..236) → QR fully inside backing. Note: White is NOT in `FILLED_POLYGON_FILLS` (Dunkelgrün/Hellgrün/Magenta/Gelb), so this polygon is excluded from `brand:image_text_overlap` checks — no rule violation.

  **(m) Impressum (back) TextFrame** at lines 392-402 — change `y_mm=240` → `y_mm=242`. Switch `style="tueranhaenger/impressum"` → `style="tueranhaenger/impressum-on-green"`. Update Run's `paragraph_style`. w/h/x unchanged.

  Do NOT touch the DoorHangerCutout block at the bottom of page1 (lines 406-411).

  Commit message: `18: feat(wahltag-tueranhaenger): V1 back layout — Portrait-Card + Visitenkarten-Footer + QR backing + Bund-Dunkel deletion`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero && PYTHONPATH=tools python3 templates/wahltag-tueranhaenger/build.py && PYTHONPATH=tools python3 -m unittest templates._smoke.test_wahltag_tueranhaenger</automated>
    <manual>none</manual>
  </verify>
  <done>
  - Brand-Bar (Rückseite) h_mm == 14 + BLEED_MM
  - Logo Grüne (weiss, back-band): w_mm=18.9, h_mm=5.7, local_scale=(0.130, 0.130)
  - `Logo Grüne (Bund-Dunkel, back)` frame DELETED from build.py (no anname, no `if logo_brand_path.exists():` block, no `logo_brand_path = ...` line)
  - NEW Polygon "Portrait-Card" at (15, 70, 75, 100) Hellgrün on layer 0
  - Kandidat-Portrait h_mm=90
  - Kandidat-Name y=184, style=tueranhaenger/cand-name-on-green
  - Kandidat-Position y=196, style=tueranhaenger/cand-pos-on-green (NO opacity kwarg)
  - NEW Polygon "Visitenkarten-Footer" at (-2, 178, 109, 72) Dunkelgrün on layer 0
  - Kontakt-URL y=210, style=tueranhaenger/url-on-green
  - Kontakt-Info y=218, style=tueranhaenger/body-on-green
  - QR-Code (back) at (70, 210, 26, 26)
  - NEW Polygon "QR White-Backing" at (68, 208, 30, 30) White on layer 0
  - Impressum (back) y=242, style=tueranhaenger/impressum-on-green
  - `python3 templates/wahltag-tueranhaenger/build.py` exits 0
  - All 11 smoke tests still pass
  - `grep -n "Bund-Dunkel" templates/wahltag-tueranhaenger/build.py` returns no matches
  </done>
  <dont>
  - Don't delete the asset file `shared/logos/gruene-logo-bund-dunkel.png` — used by 4 other templates
  - Don't add `opacity` to Kandidat-Position (locked decision #6 — DSL has no such field)
  - Don't put QR-Backing on `LAYER_BILDER` (idx 1) — keep on `LAYER_HINTERGRUND` (idx 0) so it paints behind the QR even if appearing later in code
  - Don't put any V1 polygon on `LAYER_STANZKONTUR` (idx 3)
  - Don't change the Kandidat-Name h_mm — the new fontsize 18 with linesp 20 fits comfortably in h=10mm
  - Don't reference `Logo Grüne (Bund-Dunkel, back)` in any constraint, smoke test, or doc — it no longer exists post-V1
  - Don't change the QR encoded URL or asset path; only frame geometry changes
  </dont>
</task>

<task id="T04" type="auto" tdd="false">
  <name>Task 4: V1 CONSTRAINTS list — replace with real annames + correct gaps</name>
  <files>templates/wahltag-tueranhaenger/build.py</files>
  <depends-on>T02, T03</depends-on>
  <action>
  Replace the current 4-entry `CONSTRAINTS` list at `templates/wahltag-tueranhaenger/build.py:431-454` with the V1 15-entry list below. Quote it verbatim from the `<interfaces>` block — every anname must match exactly the strings T02 and T03 used (case-sensitive, German + parenthesized).

  ```python
  CONSTRAINTS = [
      # FRONT — Hellgrün-Akzent below Brand-Bar (touching, gap 0)
      aligned_below("Hellgrün-Akzent", "Brand-Bar (Vorderseite)",
                    gap_mm=0.0, name="akzent_below_brandbar"),
      # FRONT — Hellgrün-Band absolute pin via distance_y to Akzent
      distance_y("Hellgrün-Akzent", "Hellgrün-Band (Wahlkreuz)",
                 equals=45.0, name="band_below_akzent_45mm"),
      # FRONT — Wahlkreuz centered on panel (panel center x=52.5)
      mirrored_x("Hellgrün-Band (Wahlkreuz)", "Wahlkreuz (Hero)",
                 axis_mm=52.5, name="wahlkreuz_panel_center"),
      # FRONT — Wahlkreuz inside Hellgrün-Band
      inside("Wahlkreuz (Hero)", "Hellgrün-Band (Wahlkreuz)",
             name="wahlkreuz_in_band"),
      # FRONT — Headline below Hellgrün-Band (small gap intentional, 11mm)
      aligned_below("Headline-Wahltag", "Hellgrün-Band (Wahlkreuz)",
                    gap_mm=11.0, name="headline_below_band"),
      # FRONT — HL→Sub distance (38mm pragmatic for 250mm format)
      distance_y("Headline-Wahltag", "Sub-Headline",
                 equals=38.0, name="hl_to_sub_38mm_format_pragmatic"),
      # FRONT — Bullets-Card and Hellgrün-Akzent share full-bleed x (both x=-2)
      same_x("Bullets-Card", "Hellgrün-Akzent",
             name="bullets_card_full_bleed_x"),
      # FRONT — Bullet-Liste inside Bullets-Card
      inside("Bullet-Liste", "Bullets-Card", name="bullets_in_card"),

      # BACK — Brand-Bar mirror of front (same height)
      same_size("Brand-Bar (Vorderseite)", "Brand-Bar (Rückseite)",
                axis="h", name="brand_bar_h_pair"),
      # BACK — Portrait inside Portrait-Card (5mm uniform inset)
      inside("Kandidat-Portrait", "Portrait-Card",
             name="portrait_in_card"),
      # BACK — Kandidat-Name below Portrait (~14mm gap)
      aligned_below("Kandidat-Name", "Kandidat-Portrait",
                    gap_mm=14.0, name="name_below_portrait"),
      # BACK — Kandidat-Position below Name (~1mm gap; correct order)
      aligned_below("Kandidat-Position", "Kandidat-Name",
                    gap_mm=1.0, name="position_below_name"),
      # BACK — Kontakt-URL on Visitenkarten-Footer
      inside("Kontakt-URL", "Visitenkarten-Footer", name="url_in_footer"),
      inside("Kontakt-Info", "Visitenkarten-Footer", name="info_in_footer"),
      # BACK — QR backing fully contains QR
      inside("QR-Code (back)", "QR White-Backing", name="qr_in_backing"),
  ]
  ```

  Verify the list resolves cleanly:
  ```
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger
  ```
  Expected: 0 errors, all 15 constraints `pass`.

  If any constraint fires:
  - "references missing anname(s)" → check anname spelling against build.py (case-sensitive)
  - "axis-y drift" / "below.x != above.x" / "below.y != above.y + above.h + gap_mm" beyond 0.5mm tolerance → recompute the actual gap from the geometry T02/T03 produced and adjust the `gap_mm=` value to the actual within ±0.5mm. Per RESEARCH.md the gaps shown above are the predicted-actual; if Scribus round-trip drifts them, prefer adjusting `gap_mm` to actual rather than tightening tolerance.

  Commit message: `18: feat(wahltag-tueranhaenger): V1 CONSTRAINTS list (real annames, mirrored_x for symmetry, aligned_below for stacks)`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero && PYTHONPATH=tools python3 templates/wahltag-tueranhaenger/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all</automated>
    <manual>none</manual>
  </verify>
  <done>
  - The 4-entry pre-V1 CONSTRAINTS list is fully replaced (no leftover entries from old list)
  - All 15 V1 constraints present in the order shown
  - `structural_check wahltag-tueranhaenger` reports 0 errors and all 15 constraints pass
  - `structural_check --all` reports 0 ERRORS (warnings count may differ from baseline 122 — that's acceptable; only ERRORS break green per locked decision in #22)
  - `python3 templates/wahltag-tueranhaenger/build.py` exits 0
  </done>
  <dont>
  - Don't reuse the snake_case stub names from ISSUE.md (`brand_bar_top`, `kandidat_name`, `stat_card_*`) — they all miss `_resolve()` and emit "references missing anname(s)" warnings (locked decision #2)
  - Don't include any `stat_card_*` constraint — V1 back has Portrait-Card + Visitenkarten-Footer, NOT 3 stat cards (locked decision #3)
  - Don't reverse `aligned_below(below, above, gap_mm)` argument order — `below` always comes first, hangs from `above` (locked decision #4)
  - Don't pass `gap_mm=12.0` for `(Kandidat-Position, Kandidat-Name)` — the actual gap is ~1mm (locked decision #4)
  - Don't pass `gap_mm=8.0` for `(Kontakt-Info, Kontakt-URL)` — and don't include this stack as a constraint at all if the actual gap is 0 (URL.bottom == Info.top); the recommended list omits it for that reason (use `inside` containment in Visitenkarten-Footer instead)
  - Don't add `same_x("Logo Grüne (weiss, top)", "Logo Grüne (weiss, back-band)")` — both are at x=10 already, redundant; the brand-bar mirror via `same_size` axis="h" is the meaningful symmetry pin
  - Don't tighten `tolerance_mm` below the default 0.5 — declarations whose gaps drift > 0.5mm beyond the encoded value will trigger `brand:visual_adjacency_drift` "declaration disagrees with actual geometry" warnings
  </dont>
</task>

<task id="T05" type="auto" tdd="false">
  <name>Task 5: Regenerate template.sla + gallery via bin/render-gallery + SHA bump</name>
  <files>templates/wahltag-tueranhaenger/template.sla, templates/wahltag-tueranhaenger/page-01.png, templates/wahltag-tueranhaenger/page-02.png, templates/wahltag-tueranhaenger/preview.pdf, templates/wahltag-tueranhaenger/meta.yml, site/public/templates/wahltag-tueranhaenger/* (mirrored), site/src/content/templates/wahltag-tueranhaenger.md (catalog)</files>
  <depends-on>T04</depends-on>
  <action>
  Run the gallery regenerator from worktree root:
  ```
  cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero
  bin/render-gallery wahltag-tueranhaenger --skip-visual-diff
  ```
  This invokes scribus via `xvfb-run` internally (per `tools/visual_diff.py:131-138`) and pdftoppm for PNG previews. The pipeline:
  1. Re-runs `python3 templates/wahltag-tueranhaenger/build.py` to write a fresh `template.sla`
  2. Exports `template.sla` → `preview.pdf` via headless scribus
  3. Renders `preview.pdf` → `page-01.png` and `page-02.png` via pdftoppm
  4. Updates `meta.yml::previews_for_sla` SHA to match the new `template.sla` (regex find-replace per `tools/render_pipeline.py:290-335`, idempotent)
  5. Mirrors PNG/PDF outputs to `site/public/templates/wahltag-tueranhaenger/` and refreshes `site/src/content/templates/wahltag-tueranhaenger.md` SHA

  After regen, verify the stale-check passes:
  ```
  bin/check-stale-previews
  ```
  Expected: exit 0. (Verifies SHA(template.sla) == meta.yml::previews_for_sla.)

  Commit ALL regenerated files together: `template.sla`, `preview.pdf`, `page-01.png`, `page-02.png`, modified `meta.yml`, modified `site/public/templates/wahltag-tueranhaenger/` mirror tree, modified `site/src/content/templates/wahltag-tueranhaenger.md` catalog entry.

  Commit message: `18: chore(wahltag-tueranhaenger): regenerate template.sla + gallery via bin/render-gallery + SHA bump`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero && bin/check-stale-previews && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger</automated>
    <manual>none</manual>
  </verify>
  <done>
  - `templates/wahltag-tueranhaenger/template.sla` regenerated (mtime newer than build.py edit)
  - `templates/wahltag-tueranhaenger/page-01.png`, `page-02.png`, `preview.pdf` updated
  - `meta.yml::previews_for_sla` SHA updated to match new `template.sla`
  - `site/public/templates/wahltag-tueranhaenger/` mirror updated
  - `site/src/content/templates/wahltag-tueranhaenger.md` SHA updated
  - `bin/check-stale-previews` exits 0
  - `structural_check wahltag-tueranhaenger` still 0-errors after regen
  </done>
  <dont>
  - Don't run scribus directly without `xvfb-run` wrapping — bare scribus fails with `qt.qpa.xcb: could not connect to display` (Pitfall P3.2). Always go through `bin/render-gallery`.
  - Don't drop `--skip-visual-diff` — visual_diff requires the previous-baseline pdf and is gated to humans for V1 review (per ISSUE.md "Out of scope")
  - Don't manually edit `meta.yml::previews_for_sla` — let the pipeline write it (idempotent regex)
  - Don't commit ONLY `template.sla` and skip the PNG/PDF — `bin/check-stale-previews` will still pass on SHA but human reviewers expect synchronized previews
  - Don't reorder this task before T04 — running the regen with the broken pre-V1 CONSTRAINTS list bakes warnings into the SHA's structural_check baseline
  </dont>
</task>

<task id="T06" type="auto" tdd="false">
  <name>Task 6: Remove stale brand_overrides + update reason text on visual_adjacency_drift</name>
  <files>templates/wahltag-tueranhaenger/meta.yml</files>
  <depends-on>T05</depends-on>
  <action>
  Edit `templates/wahltag-tueranhaenger/meta.yml::brand_overrides` (lines 22-71). Apply the disposition table from `<interfaces>`:

  **(a) REMOVE `brand:image_text_overlap` entry** (currently lines 67-71):
  ```yaml
    - id: brand:image_text_overlap
      reason: >-
        Scheduled for follow-up audit per #23 — caption-on-photo / decorative
        overlaps audited at time of #23, not yet reviewed for fix-vs-override
        classification.
  ```
  Justification: V1 has zero partial overlaps (RESEARCH.md §4 + Pitfalls P1.1 walked every shape×text pair; every text frame is either fully inside or fully disjoint from every filled polygon). The override was a "scheduled audit completion" placeholder — V1 completes the audit.

  **(b) REMOVE `brand:logo_size_3M` entry** (currently lines 37-42):
  ```yaml
    - id: brand:logo_size_3M
      reason: >-
        Front white logo (35mm) is the hero scale on Hellgrün-Band; the back-band
        35mm logo mirrors front for symmetry; Bund-Dunkel back logo (18mm) is
        0.9mm under 3*M = 18.90mm — well within visual tolerance, kept for
        back-content compactness.
  ```
  Justification: V1 brings both white logos to 18.9mm = 3×M = 3×6.3 = 18.9 (kurze_kante=105). Bund-Dunkel back logo is DELETED in T03. Rule passes clean.

  **(c) UPDATE `brand:visual_adjacency_drift` reason text** (currently lines 61-66) — replace the existing reason with:
  ```yaml
    - id: brand:visual_adjacency_drift
      reason: >-
        V1 layout (#18) added a 15-entry CONSTRAINTS list capturing intentional
        adjacencies. Heuristic rule still produces N false positives on
        text-inside-polygon compositions (no y-overlap gating; no
        same_x_right/same_y_bottom helpers exist). Override remains until the
        rule's detection model gates on y-overlap. See pitfalls P1.3 in #18.
  ```

  **(d) TEST `brand:wahlkreuz_colored_bg` removability** — temporarily remove the override (currently lines 48-54) and run `structural_check wahltag-tueranhaenger`. The rule looks for an OVERLAPPING green polygon (Dunkelgrün/Hellgrün/Magenta) other than the Wahlkreuz frame itself. Post-V1 `Hellgrün-Band (Wahlkreuz)` (a Hellgrün polygon, anname distinct from `Wahlkreuz (Hero)`) overlaps `Wahlkreuz (Hero)`'s bbox (25..80, 70..125) inside the band (-2..107, 63..127).
  - If structural_check reports 0 errors: REMOVE the override permanently.
  - If structural_check reports a violation on `brand:wahlkreuz_colored_bg`: KEEP the override and document in EXECUTION.md why removal failed.

  **(e) TEST `brand:text_on_green` removability** — same temporary-removal experiment. The rule looks for white-fcolor TextFrames whose `paragraph_style` matches `^ci/(h|headline)`. V1 uses `tueranhaenger/*` styles — none start with `ci/h*`, so the rule should be a no-op for this template.
  - If structural_check reports 0 errors: REMOVE the override permanently.
  - If structural_check reports a violation: KEEP the override and document.

  Final expected `brand_overrides` post-V1 (5 or 6 entries depending on (d) and (e)):
  - `brand:line_spacing_0.9` (KEEP — 6 of 7 styles still drift)
  - `brand:hl_sl_distance_x2` (KEEP — refresh reason text to mention #18)
  - `brand:bleed_3mm` (KEEP — die-cut format)
  - `brand:font_family` (KEEP — `Gotham Narrow Book Italic` not in ci.yml fonts)
  - `brand:visual_adjacency_drift` (KEEP, with updated reason from (c))
  - `brand:text_on_green` (KEEP if (e) test fails, REMOVE if passes)
  - `brand:wahlkreuz_colored_bg` (KEEP if (d) test fails, REMOVE if passes)

  **(f) Refresh `brand:hl_sl_distance_x2` reason text** to explicitly cite #18 — append " (V1 layout intentionally compresses HL→Sub gap to 6mm visual / 38mm declared = 50% of 19.8mm formula to fit two-zone composition Hero + Bullets-Card within 250mm column. See issue #18.)" to the existing reason. Acceptance criteria #6 is otherwise a no-op (the entry already correctly uses the registered id `brand:hl_sl_distance_x2`, NOT ISSUE.md's typo `brand:hl_sub_gap_2x`).

  Run final verification:
  ```
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger
  PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
  bin/audit-alignment wahltag-tueranhaenger
  ```
  All three must report 0 ERROR-severity violations.

  Commit message: `18: chore(wahltag-tueranhaenger): remove brand_overrides[image_text_overlap, logo_size_3M] + reason text update on visual_adjacency_drift`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all && bin/audit-alignment wahltag-tueranhaenger 2>&1 | tee /tmp/audit-output.txt && ! grep -E "^ERROR" /tmp/audit-output.txt</automated>
    <manual>none</manual>
  </verify>
  <done>
  - `meta.yml::brand_overrides` no longer contains `brand:image_text_overlap` entry
  - `meta.yml::brand_overrides` no longer contains `brand:logo_size_3M` entry
  - `meta.yml::brand_overrides[brand:visual_adjacency_drift].reason` updated per (c)
  - `meta.yml::brand_overrides[brand:hl_sl_distance_x2].reason` references issue #18
  - `brand:wahlkreuz_colored_bg` and `brand:text_on_green` either removed (if test passed) or kept with note in EXECUTION.md
  - `structural_check wahltag-tueranhaenger` reports 0 errors
  - `structural_check --all` reports 0 ERRORS
  - `bin/audit-alignment wahltag-tueranhaenger` reports 0 ERROR-severity violations
  </done>
  <dont>
  - Don't reintroduce `brand:hl_sub_gap_2x` as a typo'd id — the registered id is `brand:hl_sl_distance_x2` (locked decision #5; ISSUE.md AC text is wrong but the existing meta.yml entry is right)
  - Don't remove `brand:line_spacing_0.9` even though Headline now passes — 6 of 7 styles still drift
  - Don't remove `brand:bleed_3mm` (permanent format constraint)
  - Don't remove `brand:font_family` (Kandidat-Position keeps "Gotham Narrow Book Italic" in V1)
  - Don't remove `brand:visual_adjacency_drift` (combinatorial heuristic produces ~25-50 false positives on text-inside-polygon V1 composition; cannot be silenced without `same_x_right` helpers — out of scope per locked decision #12)
  - Don't remove `brand:wahlkreuz_colored_bg` or `brand:text_on_green` WITHOUT first running structural_check with the override removed and confirming 0 violations — keep + document if either fires (per RESEARCH.md "Risks and verification" guard)
  - Don't reorder this task before T05 — overrides removed before regen risks a stale-SHA mismatch in the SHA-bumped meta.yml
  </dont>
</task>

<task id="T07" type="auto" tdd="false">
  <name>Task 7: Rewrite _specs/wahltag-tueranhaenger.md for V1 layout (full rewrite, prose constraints per SCHEMA.md §11-12)</name>
  <files>templates/_specs/wahltag-tueranhaenger.md</files>
  <depends-on>T04</depends-on>
  <action>
  Full rewrite of `templates/_specs/wahltag-tueranhaenger.md` (currently ~420 lines, 10-error drifted from PRE-V1 baseline per pitfalls P2.6 — fixing pre-V1 drift AND encoding V1 changes in one pass).

  Read the existing spec to preserve sections that don't change, then rewrite the rest. Sections to preserve verbatim (per RESEARCH.md §10 Codebase): EPS strategy, Mediengesetz/NRWO compliance, Codex demo manifest, Print-Hints, Falz/Stanze.

  Sections to rewrite for V1:

  **(1) Header YAML** — keep id, version, audience as-is.

  **(2) ASCII layout block** — redraw both pages with V1 geometry. Approximate ASCII art showing Brand-Bar (now 14mm visible), Hellgrün-Akzent (4mm strip), hole zone (y=25..60), Hellgrün-Band (Wahlkreuz at y=63..127), Wahlkreuz centered, Headline at y=138..170, Sub at y=176..188, Bullets-Card (y=192..250) on front; Brand-Bar shrunk, Portrait-Card (Hellgrün) at y=70..170, Portrait inside (5mm uniform inset), Visitenkarten-Footer (Dunkelgrün) at y=178..250 enclosing Kandidat-Name/Position/URL/Info/Impressum + QR-on-white-backing in right column on back.

  **(3) Constraints (PROSE only)** — per `shared/brand/SPEC-WRITING-GUIDE.md` §11-12: describe the alignment relationships in prose. **DO NOT duplicate the Python CONSTRAINTS list as YAML.** Example prose:
  > Brand-Bar (Vorderseite) and Brand-Bar (Rückseite) share height (16mm = 14mm visible + 2mm bleed). Hellgrün-Akzent sits flush directly under Brand-Bar (front), creating a 2-band brand stripe across the hole's top approach. Hellgrün-Band (Wahlkreuz) anchors the front hero zone (y=63..127), with Wahlkreuz (Hero) centered horizontally on the panel center (x=52.5) and contained inside the band. Headline-Wahltag hangs 11mm below the band; Sub-Headline 38mm below the Headline (50% of Quickguide formula — see brand_overrides[brand:hl_sl_distance_x2]). Bullets-Card extends full-bleed at the bottom 58mm of the front, enclosing Bullet-Liste and Impressum (front).
  >
  > On the back, Portrait-Card (Hellgrün) hosts the Kandidat-Portrait with a 5mm uniform inset on left/top/right. Visitenkarten-Footer (Dunkelgrün full-bleed bottom 72mm) hosts the candidate-caption block (Name, Position) and the contact block (URL, Info) plus Impressum (back). QR-Code (back) sits in the right column at (70, 210, 26, 26) with a White polygon backing for contrast on Dunkelgrün.

  **(4) Slot tables** — regenerate front + back slot tables with V1 coordinates. Mirror the format from a recent successful spec rewrite (see `_specs/wahlaufruf-postkarte-a6-quer.md` for the post-#17 V1 spec format). Columns: anname | type | (x, y, w, h) mm | fill / style | notes.

  Front slots (in z-order):
  ```
  | Brand-Bar (Vorderseite)   | shape | (-2, -2, 109, 16)   | Dunkelgrün | full-bleed top band   |
  | Hellgrün-Akzent           | shape | (-2, 14, 109, 4)    | Hellgrün   | accent strip under brand bar |
  | Logo Grüne (weiss, top)   | image | (10, 8, 18.9, 5.7)  | local_scale=(0.130, 0.130) | 3×M Quickguide-konform |
  | Hellgrün-Band (Wahlkreuz) | shape | (-2, 63, 109, 64)   | Hellgrün   | hero band                  |
  | Wahlkreuz (Hero)          | image | (25, 70, 55, 55)    |            | centered on panel x=52.5   |
  | Headline-Wahltag          | text  | (10, 138, 85, 32)   | tueranhaenger/headline (linesp 25.2) | 2-zeilig "Heute ist / Wahltag." |
  | Sub-Headline              | text  | (10, 176, 85, 12)   | tueranhaenger/sub | "Wähle Grün."               |
  | Bullets-Card              | shape | (-2, 192, 109, 58)  | Hellgrün   | bullets backing card        |
  | Bullet-Liste              | text  | (10, 200, 85, 40)   | tueranhaenger/body-on-green | white on Hellgrün       |
  | Impressum                 | text  | (10, 240, 85, 6)    | tueranhaenger/impressum-on-green | known WCAG concern (P2.2) |
  | Stanzkontur Außen + Loch  | path  | (Stanzkontur layer) | spot color | DRUCKEN=0, top-of-stack    |
  ```

  Back slots (in z-order):
  ```
  | Brand-Bar (Rückseite)     | shape | (-2, -2, 109, 16)   | Dunkelgrün | mirrors front Brand-Bar      |
  | Logo Grüne (weiss, back-band) | image | (10, 8, 18.9, 5.7) | local_scale=(0.130, 0.130) | mirrors front logo |
  | Portrait-Card             | shape | (15, 70, 75, 100)   | Hellgrün   | NEW — backing for portrait   |
  | Kandidat-Portrait         | image | (20, 75, 65, 90)    |            | 5mm uniform inset in card    |
  | Visitenkarten-Footer      | shape | (-2, 178, 109, 72)  | Dunkelgrün | NEW — full-bleed footer      |
  | Kandidat-Name             | text  | (10, 184, 85, 10)   | tueranhaenger/cand-name-on-green (18pt White) | candidate name 18pt |
  | Kandidat-Position         | text  | (10, 196, 85, 8)    | tueranhaenger/cand-pos-on-green | role/title (no opacity — DSL gap) |
  | Kontakt-URL               | text  | (10, 210, 50, 8)    | tueranhaenger/url-on-green | Gelb on Dunkelgrün         |
  | Kontakt-Info              | text  | (10, 218, 50, 20)   | tueranhaenger/body-on-green | white email + phone        |
  | QR White-Backing          | shape | (68, 208, 30, 30)   | White      | contrast backing for QR      |
  | QR-Code (back)            | image | (70, 210, 26, 26)   |            | 26mm = 4-module density safe |
  | Impressum (back)          | text  | (10, 242, 85, 6)    | tueranhaenger/impressum-on-green |                |
  | Stanzkontur Außen + Loch  | path  | (Stanzkontur layer) | spot color |                              |
  ```

  **(5) ParaStyle hygiene list** — list all 12 ParaStyles after T01 (7 original + 5 new on-green). For each, note: font, fontsize, linesp, fcolor. Note Headline linesp 25.2 (compliant with `brand:line_spacing_0.9`); other 6 originals still drift (override stays).

  **(6) Brand-Hierarchy contract** — update to reflect V1: Logo (top) is white 18.9mm = 3×M; Brand-Bar (front+back) shrunk to 14mm visible; Hellgrün-Akzent reinforces brand-band identity; Bund-Dunkel back logo REMOVED (was iter-3 transitional artifact).

  **(7) Background-color contract** — update to enumerate all V1 fills: Hellgrün on Akzent + Band + Bullets-Card + Portrait-Card; Dunkelgrün on Brand-Bars + Visitenkarten-Footer; White on QR-Backing.

  **(8) Open issues / known concerns section** — note:
  - White-on-Hellgrün for Impressum (front) has WCAG contrast ratio ~1.7:1 (well below AA 4.5:1) — known design concern, surfaced in #18 RESEARCH.md pitfalls P2.2; brand-team review may relocate Impressum off Hellgrün in a future iteration.
  - Kandidat-Position has no opacity-85% effect (DSL doesn't support TextFrame opacity per RESEARCH.md locked decision #6); white-on-Dunkelgrün at 100% reads acceptably.
  - HL→Sub gap is intentionally compressed to 50% of Quickguide formula for the 250mm vertical format; logged as `meta.yml::brand_overrides[brand:hl_sl_distance_x2]`.

  Keep sections (8-page-spec block markers): EPS strategy (Wahlkreuz Hellgrün rendering), Mediengesetz §24 + NRWO compliance, Codex demo manifest, Print-Hints, Falz/Stanze geometry.

  After rewrite, run `PYTHONPATH=tools python3 tools/spec_check.py wahltag-tueranhaenger` to verify spec aligns with built SLA. Expected: 0 errors. (Pre-V1 had 10; V1 spec rewrite + V1 build should align.)

  Commit message: `18: docs(wahltag-tueranhaenger): rewrite _specs/ for V1 layout (Composed Hero)`
  </action>
  <verify>
    <automated>PYTHONPATH=tools python3 tools/spec_check.py wahltag-tueranhaenger</automated>
    <manual>none</manual>
  </verify>
  <done>
  - `templates/_specs/wahltag-tueranhaenger.md` rewritten for V1 (no leftover pre-V1 frame coords)
  - Front slot table lists 11 entries (10 frames + Stanzkontur path)
  - Back slot table lists 13 entries (12 frames + Stanzkontur path)
  - Constraints expressed in PROSE only (NOT duplicated as YAML)
  - ParaStyle hygiene section lists all 12 styles
  - Open issues section mentions WCAG concern + opacity DSL gap + HL→Sub override
  - `tools/spec_check.py wahltag-tueranhaenger` reports 0 errors
  </done>
  <dont>
  - Don't duplicate the Python CONSTRAINTS list as YAML in the spec — per `shared/brand/SPEC-WRITING-GUIDE.md` §11-12, constraints belong in build.py only; spec describes them in prose
  - Don't leave references to `Logo Grüne (Bund-Dunkel, back)` — that frame was deleted in T03
  - Don't reference snake_case stub annames anywhere — use the exact German + parenthesized strings from build.py
  - Don't claim Headline has `linesp 30` — V1 uses 25.2
  - Don't claim a 35mm white logo — V1 uses 18.9mm
  - Don't reference `brand:image_in_container_flush` or `brand:portrait_column_alignment` — phantom rules (locked decision #1)
  </dont>
</task>

<task id="T08" type="auto" tdd="true">
  <name>Task 8: Invariant-pinning tests — NEW tools/sla_lib/tests/test_tueranhaenger_geometry.py (≥10 invariants, relationship-pinning per #23 pattern)</name>
  <files>tools/sla_lib/tests/test_tueranhaenger_geometry.py</files>
  <depends-on>T05</depends-on>
  <behavior>
  Test class verifies V1 geometry RELATIONSHIPS, not absolute coordinates (locked decision #14; per #23 `test_zeitung_geometry.py` pattern). Each test pins one invariant. Float-imprecise SLA round-trip means coordinate equality is brittle — use `assertAlmostEqual(..., delta=0.5)` for all comparisons.

  Behaviors to cover (≥10 invariants):
  - Brand-Bar heights match across pages (symmetry pair)
  - Brand-Bar bottom touches Hellgrün-Akzent top (no gap, ±0.5mm)
  - Wahlkreuz horizontal center == panel center (52.5mm)
  - Wahlkreuz fully inside Hellgrün-Band (bbox containment)
  - Portrait fully inside Portrait-Card (bbox containment)
  - QR-Code (back) fully inside QR White-Backing
  - Visitenkarten-Footer encloses Kandidat-Name, Kandidat-Position, Kontakt-URL, Kontakt-Info, Impressum (back) — 5 containment checks
  - Bullets-Card encloses Bullet-Liste and Impressum (front) — 2 containment checks
  - Visitenkarten-Footer right edge >= page_w + bleed - 0.5 (full-bleed)
  - Bullets-Card right edge >= page_w + bleed - 0.5 (full-bleed)
  - Hellgrün-Akzent right edge >= page_w + bleed - 0.5 (full-bleed)
  - Sub-Headline.y > Headline.y + Headline.h (vertical order; never overlap)
  - Bullets-Card.y > Sub-Headline.y + Sub-Headline.h (vertical order)
  - Visitenkarten-Footer.y > Portrait-Card.y + Portrait-Card.h (vertical order)
  - Logo (weiss, top) and Logo (weiss, back-band) share x and y (mirror pair)
  - Logo (weiss, top) width ≈ 18.9mm (pins `brand:logo_size_3M` compliance)
  </behavior>
  <action>
  RED: Write the test file `tools/sla_lib/tests/test_tueranhaenger_geometry.py` first. Model verbatim on `tools/sla_lib/tests/test_zeitung_geometry.py` (already in CI). Structure:

  ```python
  """Invariant tests for wahltag-tueranhaenger V1 geometry — pin RELATIONSHIPS.

  Per Issue #18 locked decision #14 + Issue #23 pattern. Float-imprecise
  SLA round-trip makes coordinate-pinning brittle. These tests survive any
  future legitimate retuning that preserves V1 alignment intent.
  """
  from __future__ import annotations

  import importlib.util
  import sys
  import unittest
  from pathlib import Path

  ROOT = Path(__file__).resolve().parents[3]
  sys.path.insert(0, str(ROOT / "tools"))

  from sla_lib.builder.bbox import frame_bbox_mm  # noqa: E402


  def _load_doc():
      build_py = ROOT / "templates" / "wahltag-tueranhaenger" / "build.py"
      spec = importlib.util.spec_from_file_location("tueranhaenger_build", build_py)
      assert spec is not None and spec.loader is not None
      mod = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(mod)
      return mod.build_doc()


  def _frame_by_anname(doc, anname):
      for page in doc.pages:
          if page.is_master:
              continue
          for item in page.items:
              if getattr(item, "anname", "") == anname:
                  return item, page
      raise AssertionError(f"frame {anname!r} not found in tueranhaenger doc")


  _DOC = None
  def _doc():
      global _DOC
      if _DOC is None:
          _DOC = _load_doc()
      return _DOC


  class WahltagTueranhaengerGeometryTests(unittest.TestCase):
      """V1 invariant pins (relationship-based)."""

      def test_brand_bar_heights_match(self):
          front, _ = _frame_by_anname(_doc(), "Brand-Bar (Vorderseite)")
          back, _ = _frame_by_anname(_doc(), "Brand-Bar (Rückseite)")
          self.assertAlmostEqual(front.h_mm, back.h_mm, delta=0.5)

      def test_akzent_touches_brand_bar(self):
          bar, _ = _frame_by_anname(_doc(), "Brand-Bar (Vorderseite)")
          akzent, _ = _frame_by_anname(_doc(), "Hellgrün-Akzent")
          # Brand-Bar bottom y == akzent top y (gap 0)
          self.assertAlmostEqual(bar.y_mm + bar.h_mm, akzent.y_mm, delta=0.5)

      def test_wahlkreuz_horizontally_centered(self):
          wk, _ = _frame_by_anname(_doc(), "Wahlkreuz (Hero)")
          # Panel center x = TRIM_W_MM / 2 = 52.5
          self.assertAlmostEqual(wk.x_mm + wk.w_mm / 2, 52.5, delta=0.5)

      def test_wahlkreuz_inside_hellgruen_band(self):
          band, _ = _frame_by_anname(_doc(), "Hellgrün-Band (Wahlkreuz)")
          wk, _ = _frame_by_anname(_doc(), "Wahlkreuz (Hero)")
          self.assertGreaterEqual(wk.x_mm, band.x_mm - 0.5)
          self.assertGreaterEqual(wk.y_mm, band.y_mm - 0.5)
          self.assertLessEqual(wk.x_mm + wk.w_mm, band.x_mm + band.w_mm + 0.5)
          self.assertLessEqual(wk.y_mm + wk.h_mm, band.y_mm + band.h_mm + 0.5)

      def test_portrait_inside_portrait_card(self):
          card, _ = _frame_by_anname(_doc(), "Portrait-Card")
          portrait, _ = _frame_by_anname(_doc(), "Kandidat-Portrait")
          self.assertGreaterEqual(portrait.x_mm, card.x_mm - 0.5)
          self.assertGreaterEqual(portrait.y_mm, card.y_mm - 0.5)
          self.assertLessEqual(portrait.x_mm + portrait.w_mm, card.x_mm + card.w_mm + 0.5)
          self.assertLessEqual(portrait.y_mm + portrait.h_mm, card.y_mm + card.h_mm + 0.5)

      def test_qr_inside_qr_backing(self):
          backing, _ = _frame_by_anname(_doc(), "QR White-Backing")
          qr, _ = _frame_by_anname(_doc(), "QR-Code (back)")
          self.assertGreaterEqual(qr.x_mm, backing.x_mm - 0.5)
          self.assertGreaterEqual(qr.y_mm, backing.y_mm - 0.5)
          self.assertLessEqual(qr.x_mm + qr.w_mm, backing.x_mm + backing.w_mm + 0.5)
          self.assertLessEqual(qr.y_mm + qr.h_mm, backing.y_mm + backing.h_mm + 0.5)

      def test_visitenkarten_footer_encloses_back_text(self):
          footer, _ = _frame_by_anname(_doc(), "Visitenkarten-Footer")
          for anname in ("Kandidat-Name", "Kandidat-Position",
                         "Kontakt-URL", "Kontakt-Info", "Impressum (back)"):
              t, _ = _frame_by_anname(_doc(), anname)
              with self.subTest(anname=anname):
                  self.assertGreaterEqual(t.x_mm, footer.x_mm - 0.5)
                  self.assertGreaterEqual(t.y_mm, footer.y_mm - 0.5)
                  self.assertLessEqual(t.x_mm + t.w_mm, footer.x_mm + footer.w_mm + 0.5)
                  self.assertLessEqual(t.y_mm + t.h_mm, footer.y_mm + footer.h_mm + 0.5)

      def test_bullets_card_encloses_front_text(self):
          card, _ = _frame_by_anname(_doc(), "Bullets-Card")
          for anname in ("Bullet-Liste", "Impressum"):
              t, _ = _frame_by_anname(_doc(), anname)
              with self.subTest(anname=anname):
                  self.assertGreaterEqual(t.x_mm, card.x_mm - 0.5)
                  self.assertGreaterEqual(t.y_mm, card.y_mm - 0.5)
                  self.assertLessEqual(t.x_mm + t.w_mm, card.x_mm + card.w_mm + 0.5)
                  self.assertLessEqual(t.y_mm + t.h_mm, card.y_mm + card.h_mm + 0.5)

      def test_full_bleed_polygons_extend_to_outer_edge(self):
          # TRIM_W_MM=105, BLEED_MM=2 → outer right edge = 107
          for anname in ("Visitenkarten-Footer", "Bullets-Card",
                         "Hellgrün-Akzent", "Brand-Bar (Vorderseite)",
                         "Brand-Bar (Rückseite)"):
              p, _ = _frame_by_anname(_doc(), anname)
              with self.subTest(anname=anname):
                  self.assertGreaterEqual(p.x_mm + p.w_mm, 107 - 0.5)
                  self.assertLessEqual(p.x_mm, -2 + 0.5)

      def test_vertical_order_preserved(self):
          # Sub.y > HL.y + HL.h
          hl, _ = _frame_by_anname(_doc(), "Headline-Wahltag")
          sub, _ = _frame_by_anname(_doc(), "Sub-Headline")
          self.assertGreater(sub.y_mm, hl.y_mm + hl.h_mm)
          # Bullets-Card.y > Sub.y + Sub.h
          card, _ = _frame_by_anname(_doc(), "Bullets-Card")
          self.assertGreater(card.y_mm, sub.y_mm + sub.h_mm)
          # Visitenkarten-Footer.y > Portrait-Card.y + Portrait-Card.h
          pcard, _ = _frame_by_anname(_doc(), "Portrait-Card")
          footer, _ = _frame_by_anname(_doc(), "Visitenkarten-Footer")
          self.assertGreater(footer.y_mm, pcard.y_mm + pcard.h_mm)

      def test_logos_mirror_x_y(self):
          top, _ = _frame_by_anname(_doc(), "Logo Grüne (weiss, top)")
          back, _ = _frame_by_anname(_doc(), "Logo Grüne (weiss, back-band)")
          self.assertAlmostEqual(top.x_mm, back.x_mm, delta=0.5)
          self.assertAlmostEqual(top.y_mm, back.y_mm, delta=0.5)

      def test_logo_size_3m_compliance(self):
          # kurze_kante=105mm, M=6.3mm, 3M=18.9mm
          top, _ = _frame_by_anname(_doc(), "Logo Grüne (weiss, top)")
          self.assertAlmostEqual(top.w_mm, 18.9, delta=0.5)


  if __name__ == "__main__":
      unittest.main()
  ```

  GREEN: Run the test:
  ```
  cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero
  PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_tueranhaenger_geometry -v
  ```
  All 12 test methods should pass after T02/T03/T05 land. If a test fails, the test is correct — fix the geometry in build.py to satisfy the invariant, then re-run T05 to regenerate template.sla.

  REFACTOR: After tests pass, deduplicate the bbox-containment helper into a `_assert_inside(self, child, parent)` method on the test class to reduce repetition (8 inline containment blocks → 1 helper used 8 times).

  Verify it's discovered by the standard test runner:
  ```
  PYTHONPATH=tools python3 -m unittest discover tools/sla_lib/tests
  ```
  All existing tests + new 12 should pass.

  Commit message: `18: test(wahltag-tueranhaenger): invariant-pinning tests in NEW test_tueranhaenger_geometry.py`
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero && PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_tueranhaenger_geometry -v && PYTHONPATH=tools python3 -m unittest discover tools/sla_lib/tests</automated>
    <manual>none</manual>
  </verify>
  <done>
  - `tools/sla_lib/tests/test_tueranhaenger_geometry.py` exists with `WahltagTueranhaengerGeometryTests` class
  - ≥10 distinct invariant test methods (the 12 listed in `<behavior>`)
  - All invariants use `assertAlmostEqual(..., delta=0.5)` or `assertGreater[Equal]/assertLessEqual` with bleed-aware tolerance
  - Discovery via `python3 -m unittest discover tools/sla_lib/tests` includes the new file
  - All tests pass on V1 build
  - No absolute-coordinate equality assertions (e.g. `assertEqual(x_mm, 25.0)`)
  </done>
  <dont>
  - Don't pin absolute coordinates (e.g. `assertEqual(wk.x_mm, 25.0)`) — float-imprecise round-trip via Scribus emits `WIDTH="308.97637795275594"` (pt) → reads back as `109.000000…` ± last-bit drift; coordinate equality fails (locked decision #14 + Pitfall P5.1)
  - Don't import the test from inside `templates/_smoke/` — invariant-pinning tests live under `tools/sla_lib/tests/` per #23 pattern
  - Don't add a test that re-runs the build from scratch — module-level cache (`_DOC = None` + `_doc()`) ensures one build per process
  - Don't reference deleted `Logo Grüne (Bund-Dunkel, back)` anywhere
  - Don't pin Kandidat-Name/Position gap to a specific mm value — that's what CONSTRAINTS list does; geometry tests pin RELATIONSHIPS like containment + ordering
  </dont>
</task>

<task id="T09" type="auto" tdd="false">
  <name>Task 9: Append session-history row to DESIGN-SYSTEM-BRIEF.md §10 + update improvements/02 Resulting-issue link</name>
  <files>shared/brand/DESIGN-SYSTEM-BRIEF.md, improvements/02-wahltag-tueranhaenger.md</files>
  <depends-on>T07</depends-on>
  <action>
  **(a)** Append a new row to `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 "Session history" table (currently at line 153 — single existing row for #17). Use the seed row from `improvements/02-wahltag-tueranhaenger.md` §"Session-History" as base. The new row goes BEFORE the trailing prose (`When you (Claude Design) finish a session...`).

  Format (match the existing row format exactly):
  ```
  | 2026-05-08 | Pattern B · `wahltag-tueranhaenger` (Source: `improvements/02-wahltag-tueranhaenger.md`) | 3 Layout-Varianten (Composed Hero / Vertical Stripe / Manifesto) mit build.py-line-targeted Slot-Änderungen + SVG-Companion-Mocks unter `improvements/02-wahltag-tueranhaenger.html` | https://github.com/GrueneAT/vorlagen/issues/34 (V1 only; V2/V3 backlog) |
  ```

  **(b)** Update `improvements/02-wahltag-tueranhaenger.md` §"Session-History" — replace the placeholder `_(seed for /issue:new)_` in the "Resulting issue" cell with the actual GitHub URL: `https://github.com/GrueneAT/vorlagen/issues/34 (V1 only; V2/V3 backlog)`.

  Note: `improvements/02-wahltag-tueranhaenger.md` lives at workspace root and is NOT committed in this repo's tracked tree (it's a working doc in main only). Verify by checking `git status` before attempting the edit; if the file is not tracked in this worktree, skip step (b) and document the omission in EXECUTION.md (the URL update can land in a separate workspace-level edit).

  Commit message: `18: docs(brand): append session-history row to DESIGN-SYSTEM-BRIEF.md §10`

  At PR-ship time, the PR URL on GitHub PR #X (when known) can replace the issue URL in the Resulting-issue cell — add a follow-up note to EXECUTION.md about doing this once the PR exists.
  </action>
  <verify>
    <automated>cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero && grep -c "wahltag-tueranhaenger" shared/brand/DESIGN-SYSTEM-BRIEF.md</automated>
    <manual>Brief §10 row visually matches the existing #17 row format (date, session, output, resulting-issue columns)</manual>
  </verify>
  <done>
  - `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 contains a new row mentioning `wahltag-tueranhaenger` and the GitHub URL #34
  - The row sits BEFORE the trailing `When you (Claude Design) finish...` prose paragraph
  - `improvements/02-wahltag-tueranhaenger.md` "Resulting issue" cell points to GitHub URL #34 (or omission documented in EXECUTION.md)
  - `grep -c "wahltag-tueranhaenger" shared/brand/DESIGN-SYSTEM-BRIEF.md` returns ≥1
  </done>
  <dont>
  - Don't replace the existing #17 row — append to the end of the table
  - Don't reformat the table (column order, alignment); copy the existing row as a template
  - Don't add the row inside the prose paragraph; it goes between the existing row and the prose
  - Don't include "claude" attribution anywhere — per memory feedback file, never reference the tool used
  </dont>
</task>

</tasks>

<verification>
After all tasks, run final checks from worktree root:
```
cd /root/workspace/.worktrees/18-v1-layout-for-wahltag-tueranhaenger-composed-hero
PYTHONPATH=tools python3 templates/wahltag-tueranhaenger/build.py
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
PYTHONPATH=tools python3 -m unittest discover tools/sla_lib/tests
PYTHONPATH=tools python3 -m unittest templates._smoke.test_wahltag_tueranhaenger
PYTHONPATH=tools python3 tools/spec_check.py wahltag-tueranhaenger
PYTHONPATH=tools python3 tools/check_ci.py templates/wahltag-tueranhaenger/template.sla
bin/check-stale-previews
bin/audit-alignment wahltag-tueranhaenger
```

Expected outcomes:
- `build.py` exits 0
- `structural_check wahltag-tueranhaenger`: 0 errors, all 15 constraints pass
- `structural_check --all`: 0 ERRORS (warning count comparable to baseline)
- `unittest discover tools/sla_lib/tests`: all tests pass including new `test_tueranhaenger_geometry.py`
- `unittest templates._smoke.test_wahltag_tueranhaenger`: 11/11 pass (unchanged)
- `spec_check.py wahltag-tueranhaenger`: 0 errors (down from pre-V1's 10)
- `check_ci.py`: same warning count as baseline + 5 new on-green styles entries (all in non_ci_styles allow-list)
- `check-stale-previews`: exit 0
- `audit-alignment`: 0 ERROR-severity violations (warnings acceptable)
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria (with corrections per RESEARCH.md):

- [ ] V1 deltas applied in `templates/wahltag-tueranhaenger/build.py` across T01+T02+T03 commits (not "one commit" as ISSUE.md says — broken into 3 atomic commits per RESEARCH.md locked decision #13).
- [ ] `python3 templates/wahltag-tueranhaenger/build.py` regenerates `template.sla` cleanly (exit 0).
- [ ] `python3 -m sla_lib.builder.structural_check wahltag-tueranhaenger` shows 0 errors; the 15-entry CONSTRAINTS list is fully green.
- [ ] `python3 -m sla_lib.builder.structural_check --all` reports 0 ERRORS (warnings within baseline range).
- [ ] `tools/check_ci.py` passes with no new errors.
- [ ] HL→Sub gap deviation is logged as `meta.yml::brand_overrides[brand:hl_sl_distance_x2]` (CORRECT registered id; ISSUE.md's `brand:hl_sub_gap_2x` is a typo per RESEARCH.md locked decision #5) with reason text mentioning #18.
- [ ] `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 has a new Session-History row for `wahltag-tueranhaenger` linking GitHub #34.
- [ ] `improvements/02-wahltag-tueranhaenger.md` Session-History "Resulting issue" cell updated to GitHub URL (or documented omission if file is not in worktree's tracked tree).
- [ ] `bin/check-stale-previews` exits 0 (template.sla SHA matches `meta.yml::previews_for_sla`).
- [ ] `bin/audit-alignment wahltag-tueranhaenger` reports 0 ERROR-severity violations.
- [ ] `tools/sla_lib/tests/test_tueranhaenger_geometry.py` exists with ≥10 invariant tests, all passing.
- [ ] `templates/_specs/wahltag-tueranhaenger.md` rewritten for V1 (spec_check 0-errors, down from pre-V1's 10).
- [ ] 5 new `*-on-green` ParaStyles defined in build.py + listed in `meta.yml::ci_overrides.non_ci_styles`.
- [ ] `Logo Grüne (Bund-Dunkel, back)` ImageFrame deleted from build.py (asset file remains for 4 other templates).
- [ ] `meta.yml::brand_overrides` post-V1 contains 5-7 entries (image_text_overlap and logo_size_3M REMOVED; visual_adjacency_drift KEPT with updated reason; wahlkreuz_colored_bg + text_on_green REMOVED if T06 removability tests pass, else KEPT with EXECUTION.md note).
</success_criteria>

<risks_and_verification>

## 6 ISSUE.md corrections honored in this plan

1. **Phantom rules removed** — `brand:image_in_container_flush` and `brand:portrait_column_alignment` DO NOT EXIST. The orchestrator prompt and ISSUE.md mention them. RESEARCH.md locked decision #1 confirms registry is exactly 14 rules. No task references either rule. Their detection power is folded into `brand:visual_adjacency_drift`'s 4-axis logic.
2. **CONSTRAINTS list rewritten** — ISSUE.md's CONSTRAINTS list uses snake_case stub names (brand_bar_top, kandidat_name, stat_card_*) and references a non-existent 3-stat-card back design. T04 replaces with 15-entry list using REAL annames + Portrait-Card/Visitenkarten-Footer composition.
3. **Wrong rule id corrected** — ISSUE.md AC #6 says `brand:hl_sub_gap_2x`; the registered id is `brand:hl_sl_distance_x2`. T06 keeps existing meta.yml entry (which already uses correct id) and refreshes its reason text to mention #18.
4. **`opacity 85%` dropped** — ISSUE.md V1 row prescribes opacity-85 on Kandidat-Position; the DSL TextFrame primitive has no opacity field. T03 omits any opacity kwarg; spec rewrite (T07) documents the DSL gap.
5. **5+ ParaStyles, not 2** — ISSUE.md names only `body-on-green` + `url-on-green`. V1 changes fcolor on 4 more text frames (Kandidat-Name → White, Position → White, Impressum front + back → White) + bumps Kandidat-Name fontsize 14→18. T01 adds 5 styles total per #17 parallel-style pattern.
6. **Smoke test rewrite SKIPPED** — RESEARCH.md verified all 11 assertions pass V1 unmodified. No smoke-test rewrite task in this plan (saves a task per locked decision #8).

## Atomic-PR ordering (do not reorder)

```
T01 ParaStyles → T02 front layout → T03 back layout → T04 CONSTRAINTS rewrite
              → T05 regen template.sla + SHA bump → T06 brand_overrides cleanup
              → T07 spec rewrite (parallel-able with T05/T06 if executor wants)
              → T08 invariant tests → T09 brief §10 row
```

Specifically:
- T04 BEFORE T05 — running render-gallery with broken pre-V1 CONSTRAINTS bakes warnings into the SHA's structural_check baseline.
- T05 BEFORE T06 — overrides cleanup before SHA bump risks stale-SHA mismatch in meta.yml.
- T08 AFTER T05 — invariant tests need a regenerated template.sla to round-trip through.

## bin/audit-alignment as final verification gate

Post-V1, the executor MUST run `bin/audit-alignment wahltag-tueranhaenger` and verify ZERO ERROR-severity violations. Warnings are acceptable (the `brand:visual_adjacency_drift` heuristic produces false positives on text-inside-polygon V1 composition; locked decision #12 keeps the override).

## Conditional-removal guard for T06

If `brand:wahlkreuz_colored_bg` removal surfaces a violation (e.g. Hellgrün-Band overlap doesn't satisfy the rule due to anname-collision logic), KEEP the override and document why in EXECUTION.md. Same for `brand:text_on_green`. Same general principle for `brand:line_spacing_0.9` if any V1-introduced style accidentally drifts within tolerance — if removal would surface a violation, KEEP and document. This plan deliberately removes only the two overrides RESEARCH.md predictively verified are clean (`brand:image_text_overlap`, `brand:logo_size_3M`).

## Layer discipline gate

ALL 5 new V1 polygons (Hellgrün-Akzent, Bullets-Card, Portrait-Card, Visitenkarten-Footer, QR-Backing) MUST use `LAYER_HINTERGRUND` (idx 0). Adding any to `LAYER_STANZKONTUR` (idx 3) silently fails printability AND breaks `test_stanzkontur_polygons_present_on_layer` (smoke test counts exactly 4 — outer+hole on each page). Verified safe in T02/T03 explicit instructions.

## Known design concerns surfaced in spec (not blocking V1)

- **WCAG contrast** — Impressum (front) is white-on-Hellgrün (~1.7:1 vs 4.5:1 AA threshold). T07 spec documents as known concern; brand-team review may relocate Impressum off Hellgrün in a future iteration. Not blocking for #18.
- **Kandidat-Position opacity gap** — DSL has no TextFrame opacity. White-on-Dunkelgrün at 100% reads acceptably. T07 spec documents the DSL gap.
- **Bullets-Card 58mm Hellgrün ink coverage** — high CMYK ink (100% Yellow + 69% Cyan over 6322mm² ≈ 12.5% of page area). ISSUE.md open question Q3 raises Druck-Kosten-Sensibilität. Default per ISSUE.md: keep 58mm. Defer cost-reduction to follow-up if needed.

</risks_and_verification>
