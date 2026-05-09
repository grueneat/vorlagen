# Plan: V1 layout for `wahlaufruf-postkarte-a6-quer` (Symbol-Tight)

<objective>
What this plan accomplishes: Implement V1 "Symbol-Tight" layout for `templates/wahlaufruf-postkarte-a6-quer/` per `improvements/01-wahlaufruf-postkarte.md` §"Variante 1" — front halo+symbol+datum/cta, back split-half + 3 W-Fragen + repositioned QR stack + white logo — with a complete CONSTRAINTS list, regenerated artifacts, rewritten smoke test + spec, removed stale brand_overrides, and a session-history brief row.

Why it matters: First of five V1 implementations (#15 sequence). Establishes the `*-on-green` ParaStyle migration pattern for #18-#21 and the halo+symbol mirrored-axis constraint pattern.

Scope:
- IN: build.py edits (front + back), 4 new ParaStyles, 13-entry CONSTRAINTS list, meta.yml ci_overrides update, regen via `bin/render-gallery`, meta.yml previews_for_sla SHA bump, removal of 3 stale brand_overrides, smoke test rewrite, `_specs/wahlaufruf-postkarte-a6-quer.md` rewrite, brief §10 session-history row.
- OUT: V2 "Datum-Banner" / V3 "Asymmetric Hero" (backlog), sample/photo curation (#13), pixel-diff visual review (human PR-review), removal of `brand:line_spacing_0.9` if it surfaces violations (keep + document).

No CONTEXT.md exists — decisions follow RESEARCH.md locked decisions (which override ISSUE.md where they conflict; ISSUE.md has 4 documented errors).
</objective>

<context>
Issue: @.issues/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight/ISSUE.md
Research (synthesized, locked decisions): @.issues/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight/RESEARCH.md
Pitfalls (per-line evidence): @.issues/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight/research/pitfalls.md
Design package: @improvements/01-wahlaufruf-postkarte.md

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

From `tools/sla_lib/builder/constraints.py`:
```
mirrored_x(left: str, right: str, axis_mm: float, tolerance_mm: float = 0.5, name: str = "")
    → averages center-x of both frames; checks midpoint ≈ axis_mm.
mirrored_y(top: str, bottom: str, axis_mm: float, tolerance_mm: float = 0.5, name: str = "")
    → analogous for y centers.
aligned_below(below: str, above: str, gap_mm: float, tolerance_mm: float = 0.5, name: str = "")
    → asserts below.x == above.x AND below.y == above.y + above.h + gap_mm.
same_x(*targets: str, tolerance_mm: float = 0.5, name: str = "")
    → asserts all targets share the same x_mm (top-left corner, NOT center).
inside(child: str, parent: str, tolerance_mm: float = 0.5, name: str = "")
    → child bbox ⊆ parent bbox + tolerance.
distance_y(a: str, b: str, equals: float, tolerance_mm: float = 0.5, name: str = "")
    → |b.y - a.y| ≈ equals.
```

From `tools/sla_lib/builder/primitives.py`:
```
Polygon(x_mm, y_mm, w_mm, h_mm, fill: str, layer: int = 0,
        anname: str = "", shape: str = "rectangle", ...)
    → shape="ellipse" required for circles/ovals (default is rectangle).
ImageFrame(x_mm, y_mm, w_mm, h_mm, image_path, scale_type: int = 0, ratio: int = 1,
           local_scale: tuple[float, float] = (1.0, 1.0), layer: int = 1,
           anname: str = "", ...)
    → local_scale defaults to (1.0, 1.0); MUST be set explicitly for raster sizing.
TextFrame(x_mm, y_mm, w_mm, h_mm, paragraph_style: str, layer: int = 2, anname: str = "", ...)
ParaStyle(name: str, font: str, fontsize: int, linesp: float,
          fcolor: str, language: str = "de", align: int = 0, kern: float = 0.0)
    → kern is per-glyph expansion in pt; align: 0=left, 1=center.
```

From `tools/sla_lib/builder/brand_constraints.py`:
- `brand:wahlkreuz_colored_bg` matches case-sensitive substring `"Wahlkreuz"` → keep capitalized.
- `brand:undeclared_alignment_drift` flags pair gaps in (0.5, 12.0)mm with dx<5mm — MUST be silenced by declaring all stack-style adjacencies.
- `brand:logo_size_3M` checks `\bLogo\b` case-insensitive; V1 makes both logos = 3*M = 18.9mm so override becomes stale.

From `meta.yml` shape:
- `previews_for_sla: <sha256-hex>` — bumped automatically by `bin/render-gallery`; gates `bin/check-stale-previews`.
- `brand_overrides: [{id: "...", reason: "..."}]` — entries to remove.
- `ci_overrides.non_ci_styles: ["..."]` — list of allowed non-CI ParaStyle names.

V1 CONSTRAINTS list (final form — quote into build.py):
```python
CONSTRAINTS = [
    # Front: halo + symbol share centers (both axes), and halo contains symbol
    mirrored_x("wahlkreuz_halo", "Wahlkreuz", axis_mm=74.0, name="halo_x_centered"),
    mirrored_y("wahlkreuz_halo", "Wahlkreuz", axis_mm=48.0, name="halo_y_centered"),
    inside("Wahlkreuz", "wahlkreuz_halo", name="halo_contains_symbol"),
    # Front: headline stack vertical hierarchy (datum -> cta gap = 10mm)
    distance_y("headline_datum", "headline_cta", equals=10.0, name="datum_to_cta"),
    # Back: 3 W-Fragen share x-axis (left edge x=6) for headlines and bodies
    same_x("frage_was_headline", "frage_warum_headline", "frage_wann_headline",
           name="fragen_left_axis"),
    same_x("frage_was_body", "frage_warum_body", "frage_wann_body",
           name="bodies_left_axis"),
    # Back: per-W-Frage stack (body hangs from headline, gap=1mm, same x)
    aligned_below("frage_was_body",   "frage_was_headline",   gap_mm=1.0, name="was_stack"),
    aligned_below("frage_warum_body", "frage_warum_headline", gap_mm=1.0, name="warum_stack"),
    aligned_below("frage_wann_body",  "frage_wann_headline",  gap_mm=1.0, name="wann_stack"),
    # Back: QR block right-axis + label-above + url-below
    same_x("qr_label", "qr_code", "qr_url", name="qr_axis"),
    aligned_below("qr_code", "qr_label", gap_mm=2.0, name="qr_label_anchors_code"),
    aligned_below("qr_url",  "qr_code",  gap_mm=4.0, name="qr_url_below_code"),
    # Back: qr_label hangs from logo_back (right column stacking)
    aligned_below("qr_label", "logo_back", gap_mm=10.3, name="logo_back_anchors_qr"),
]
```

V1 ParaStyle additions (quote into build.py):
```python
ParaStyle(name="wahlaufruf/headline-emphasis",
          font="Vollkorn Black Italic", fontsize=26, linesp=23,
          fcolor="Gelb", language="de", align=1)
ParaStyle(name="wahlaufruf/headline-cta",
          font="Gotham Narrow Bold", fontsize=14, linesp=13,
          fcolor="White", language="de", align=1, kern=2.1)  # 0.15em → 2.1pt
ParaStyle(name="wahlaufruf/cell-headline-yellow",
          font="Vollkorn Black Italic", fontsize=18, linesp=16,
          fcolor="Gelb", language="de", align=0)
ParaStyle(name="wahlaufruf/cell-body-on-green",
          font="Gotham Narrow Book", fontsize=9, linesp=11,
          fcolor="White", language="de", align=0)
```
</interfaces>

Key files:
@templates/wahlaufruf-postkarte-a6-quer/build.py — primary edit target
@templates/wahlaufruf-postkarte-a6-quer/meta.yml — ci_overrides + brand_overrides + previews_for_sla SHA
@templates/_smoke/test_wahlaufruf_postkarte_a6_quer.py — rewrite `test_back_has_2x2_grid`
@templates/_specs/wahlaufruf-postkarte-a6-quer.md — rewrite for V1 layout
@shared/brand/DESIGN-SYSTEM-BRIEF.md — append session-history row
@improvements/01-wahlaufruf-postkarte.md — design source; §"Session-History" seed row + Resulting-issue link
@bin/render-gallery — regenerates template.sla + page-NN.png + preview.pdf + meta.yml::previews_for_sla SHA + site/public mirror
@bin/audit-alignment — post-V1 verification gate (must report 0 suspicious)
@bin/check-stale-previews — CI gate (must exit 0 after regen)
@tools/sla_lib/builder/constraints.py — factory definitions
@tools/sla_lib/builder/primitives.py — Polygon/ImageFrame/TextFrame/ParaStyle dataclasses
@tools/sla_lib/builder/brand_constraints.py — brand-rule semantics (case-sensitivity, undeclared-drift)
@tools/sla_lib/builder/structural_check.py — primary verification CLI
@tools/check_ci.py — flags ParaStyle name drift unless listed in ci_overrides.non_ci_styles
</context>

<commit_format>
Format: conventional with numeric issue prefix (per `.issues/config.yaml`)
Example: `17: feat(wahlaufruf-postkarte): add 4 V1 ParaStyles (headline-emphasis, headline-cta, cell-headline-yellow, cell-body-on-green)`
Pattern: `17: <type>(<scope>): <subject>` — types: feat, fix, test, refactor, docs, chore.
One commit per task.
</commit_format>

<tasks>

<task id="T01" type="auto" tdd="false">
  <name>Task 1: Add 4 new V1 ParaStyles + update meta.yml::ci_overrides.non_ci_styles</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/build.py, templates/wahlaufruf-postkarte-a6-quer/meta.yml</files>
  <depends-on>none</depends-on>
  <action>
  Add 4 NEW ParaStyles to `templates/wahlaufruf-postkarte-a6-quer/build.py` in the existing ParaStyle declaration block. Use the exact spec from `<interfaces>` above.

  ```python
  ParaStyle(name="wahlaufruf/headline-emphasis",
            font="Vollkorn Black Italic", fontsize=26, linesp=23,
            fcolor="Gelb", language="de", align=1)
  ParaStyle(name="wahlaufruf/headline-cta",
            font="Gotham Narrow Bold", fontsize=14, linesp=13,
            fcolor="White", language="de", align=1, kern=2.1)
  ParaStyle(name="wahlaufruf/cell-headline-yellow",
            font="Vollkorn Black Italic", fontsize=18, linesp=16,
            fcolor="Gelb", language="de", align=0)
  ParaStyle(name="wahlaufruf/cell-body-on-green",
            font="Gotham Narrow Book", fontsize=9, linesp=11,
            fcolor="White", language="de", align=0)
  ```

  Leave existing `wahlaufruf/cell-body` (Black) UNCHANGED — locked decision #5 (parallel-style migration pattern). Existing `wahlaufruf/headline` and `wahlaufruf/cell-headline` also unchanged in this task (orphan removal handled by tooling).

  Also: in the same build.py edit, change `wahlaufruf/impressum` `fontsize=6 → 5` AND `linesp=7 → 4.5` (defensive — keeps the style passing if `brand:line_spacing_0.9` ever loses its override; cost-free).

  Update `templates/wahlaufruf-postkarte-a6-quer/meta.yml::ci_overrides.non_ci_styles` to ADD the 4 new style names. Keep existing entries (`wahlaufruf/cell-body`, `wahlaufruf/impressum`) for now. Do NOT yet remove orphaned `wahlaufruf/headline` / `wahlaufruf/cell-headline` — those become orphans only after T02 deletes the frames; cleanup belongs in T07.

  Final non_ci_styles list (order: keep existing first, then new):
  ```yaml
  ci_overrides:
    non_ci_styles:
      - "wahlaufruf/cell-body"
      - "wahlaufruf/impressum"
      - "wahlaufruf/headline-emphasis"
      - "wahlaufruf/headline-cta"
      - "wahlaufruf/cell-headline-yellow"
      - "wahlaufruf/cell-body-on-green"
  ```

  Build.py must still import + execute cleanly after this edit (no frames yet wired to the new styles — they are unused references at this point, which is fine).
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight && PYTHONPATH=tools python3 templates/wahlaufruf-postkarte-a6-quer/build.py && python3 tools/check_ci.py templates/wahlaufruf-postkarte-a6-quer/template.sla</automated>
  </verify>
  <done>
  - 4 new ParaStyle declarations present in build.py
  - `wahlaufruf/impressum` fontsize=5 linesp=4.5
  - `meta.yml::ci_overrides.non_ci_styles` contains all 4 new style names
  - `python3 templates/wahlaufruf-postkarte-a6-quer/build.py` exits 0 with no exception
  - `tools/check_ci.py` passes (no new style-drift errors)
  </done>
  <dont>
  - Don't mutate `wahlaufruf/cell-body` fcolor (locked decision #5 — parallel style)
  - Don't remove `wahlaufruf/headline` / `wahlaufruf/cell-headline` yet (frames still reference them until T02)
  - Don't use `letter-spacing` or em units — DSL has neither; use `kern=2.1`
  - Don't change `align=` values from spec (1=center, 0=left)
  </dont>
</task>

<task id="T02" type="auto" tdd="false">
  <name>Task 2: V1 front layout — logo resize, halo polygon (ellipse), Wahlkreuz reposition, datum/cta stack</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/build.py</files>
  <depends-on>T01</depends-on>
  <action>
  Edit the page 0 (front) frame additions in `templates/wahlaufruf-postkarte-a6-quer/build.py`:

  1. **Front logo resize**: locate `Logo Grüne (weiss)` ImageFrame on page 0. Change `w_mm=35 → 18.9, h_mm=10 → 5.7, local_scale=(0.240, 0.240) → (0.130, 0.130)`. Keep anname capitalization as-is (existing).

  2. **Add halo Polygon BEFORE the Wahlkreuz frame** (emit-order matters for z-order within layer 0):
     ```python
     Polygon(x_mm=43, y_mm=17, w_mm=62, h_mm=62,
             fill="Hellgrün",
             shape="ellipse",       # MUST set; default is "rectangle"
             layer=0,
             anname="wahlkreuz_halo")
     ```

  3. **Reposition Wahlkreuz** ImageFrame: `x_mm=46.5 → 44, y_mm=16 → 18, w_mm=55 → 60, h_mm=55 → 60`. KEEP anname `Wahlkreuz` capitalized (locked decision #4 — `brand:wahlkreuz_colored_bg` is case-sensitive). Layer stays at 1.

  4. **Delete** the `Headline-Wahlaufruf` TextFrame from page 0.

  5. **Add two new TextFrames** to page 0 (below the Wahlkreuz, before any closing of the page block):
     ```python
     TextFrame(x_mm=10, y_mm=82, w_mm=128, h_mm=10,
               paragraph_style="wahlaufruf/headline-emphasis",
               layer=2, anname="headline_datum",
               text="SONNTAG, 26. JÄNNER 2026")  # demo string; final text per design
     TextFrame(x_mm=10, y_mm=92, w_mm=128, h_mm=10,
               paragraph_style="wahlaufruf/headline-cta",
               layer=2, anname="headline_cta",
               text="GIB DEINE STIMME DEN GRÜNEN")  # demo string
     ```
     Use the existing TextFrame text-passing convention in this codebase (the existing `Headline-Wahlaufruf` you just deleted shows the pattern; copy it). If the existing pattern uses a different keyword (e.g. `body`, `runs`), match it — do not invent a new field.

  Verify front-side center-axis math: halo center = (43+31, 17+31) = (74, 48). Wahlkreuz center = (44+30, 18+30) = (74, 48). Both axes match the CONSTRAINTS in T04. ✓
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight && PYTHONPATH=tools python3 templates/wahlaufruf-postkarte-a6-quer/build.py</automated>
  </verify>
  <done>
  - Front logo dims = 18.9×5.7 with local_scale=(0.130, 0.130)
  - `wahlkreuz_halo` Polygon present with shape="ellipse" fill="Hellgrün" layer=0
  - `Wahlkreuz` ImageFrame at (44, 18, 60, 60), anname kept capitalized
  - `Headline-Wahlaufruf` deleted
  - `headline_datum` + `headline_cta` TextFrames added at specified coords with new ParaStyles
  - build.py exits 0
  </done>
  <dont>
  - Don't lowercase `Wahlkreuz` anname (breaks `brand:wahlkreuz_colored_bg` case-sensitive match)
  - Don't omit `shape="ellipse"` on the halo (defaults to rectangle)
  - Don't omit `local_scale=(0.130, 0.130)` on the resized front logo (renders 5.5× over-scale otherwise)
  - Don't emit halo AFTER Wahlkreuz on the same layer (z-order would put halo on top)
  </dont>
</task>

<task id="T03" type="auto" tdd="false">
  <name>Task 3: V1 back layout — split-half bg, white logo, 3 W-Fragen blocks, QR stack reposition, Impressum tweak</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/build.py</files>
  <depends-on>T02</depends-on>
  <action>
  Edit the page 1 (back) frame additions in `templates/wahlaufruf-postkarte-a6-quer/build.py`:

  1. **Add 2 background Polygons** at the START of page 1 frames (so they sit below everything):
     ```python
     Polygon(x_mm=-3, y_mm=-3, w_mm=93, h_mm=111,
             fill="Dunkelgrün", layer=0,
             anname="seitenhintergrund_back_left")
     Polygon(x_mm=0, y_mm=96, w_mm=148, h_mm=9,
             fill="White", layer=0,
             anname="impressum_strip_bg")
     ```

  2. **Replace the back-side logo asset and reposition**: locate the existing `Logo Grüne (Bund-Dunkel)` ImageFrame on page 1. Change `image_path` to `shared/logos/gruene-weiss.png` (verify exact path matches the file used by the front logo). Reposition: `x_mm=96, y_mm=8, w_mm=18.9, h_mm=5.7`. Set `local_scale=(0.130, 0.130)` EXPLICITLY (default 1.0 renders 5.5× over-scale, clipped). Rename anname to `logo_back` (lowercase — locked decision #4: case-insensitive `\bLogo\b` rule still matches; new annames use snake_case).

  3. **Delete the entire 4-Cells loop** (the `for i in range(1, 5):` or AlignedRow wrapper that emits `Cell N — Headline` + `Cell N — Body` — 8 frames + 4 wrapper rows). Per RESEARCH.md frames-touched inventory.

  4. **Add 3 W-Frage TextFrame pairs** (each = headline at y=Y, body at y=Y+9 with gap=1mm):
     ```python
     # Was?
     TextFrame(x_mm=6, y_mm=12, w_mm=84, h_mm=8,
               paragraph_style="wahlaufruf/cell-headline-yellow",
               layer=2, anname="frage_was_headline",
               text="WAS?")
     TextFrame(x_mm=6, y_mm=21, w_mm=84, h_mm=20,
               paragraph_style="wahlaufruf/cell-body-on-green",
               layer=2, anname="frage_was_body",
               text="…demo body string for Was…")
     # Warum?
     TextFrame(x_mm=6, y_mm=40, w_mm=84, h_mm=8,
               paragraph_style="wahlaufruf/cell-headline-yellow",
               layer=2, anname="frage_warum_headline",
               text="WARUM?")
     TextFrame(x_mm=6, y_mm=49, w_mm=84, h_mm=20,
               paragraph_style="wahlaufruf/cell-body-on-green",
               layer=2, anname="frage_warum_body",
               text="…demo body string for Warum…")
     # Wann?
     TextFrame(x_mm=6, y_mm=68, w_mm=84, h_mm=8,
               paragraph_style="wahlaufruf/cell-headline-yellow",
               layer=2, anname="frage_wann_headline",
               text="WANN?")
     TextFrame(x_mm=6, y_mm=77, w_mm=84, h_mm=20,
               paragraph_style="wahlaufruf/cell-body-on-green",
               layer=2, anname="frage_wann_body",
               text="…demo body string for Wann…")
     ```
     Match the codebase's existing TextFrame text-passing convention (see existing back frames for the field name).

  5. **Reposition QR ImageFrame and add label/url** (LOCKED: y values are 24/31/71, NOT ISSUE.md's 24/30/68 — see ship-blocker B2/B3 in pitfalls.md):
     ```python
     TextFrame(x_mm=96, y_mm=24, w_mm=36, h_mm=5,
               paragraph_style="wahlaufruf/headline-cta",  # or appropriate label style — see note below
               layer=2, anname="qr_label",
               text="WO INFORMIEREN")
     # Existing QR ImageFrame: rename anname → "qr_code", reposition + resize
     ImageFrame(x_mm=96, y_mm=31, w_mm=36, h_mm=36,
                image_path=<existing qr_code asset>,
                scale_type=0, ratio=1,  # KEEP existing scale_type pattern (M5)
                layer=1, anname="qr_code")
     TextFrame(x_mm=96, y_mm=71, w_mm=36, h_mm=5,
               paragraph_style="wahlaufruf/headline-cta",  # or appropriate URL style
               layer=2, anname="qr_url",
               text="gruene-noe.at")
     ```
     **Note on qr_label/qr_url ParaStyles**: ISSUE.md prescribes "12pt Gotham Bold Dunkelgrün" for label and "11pt Gotham Bold Dunkelgrün" for URL. These styles do NOT exist in the new ParaStyle set. Either (a) inline-add two more ParaStyles in this task with `fcolor="Dunkelgrün"` (e.g. `wahlaufruf/qr-label` 12pt and `wahlaufruf/qr-url` 11pt — both Gotham Narrow Bold, align=1) AND extend `meta.yml::ci_overrides.non_ci_styles` accordingly, OR (b) reuse `wahlaufruf/headline-cta` (white) if visual is acceptable on the white impressum strip / dunkelgrün bg behind label. **Preferred: option (a)** — add the 2 styles inline; quote them into the spec rewrite (T08) too. Use this exact addition:
     ```python
     ParaStyle(name="wahlaufruf/qr-label",
               font="Gotham Narrow Bold", fontsize=12, linesp=11,
               fcolor="Dunkelgrün", language="de", align=1)
     ParaStyle(name="wahlaufruf/qr-url",
               font="Gotham Narrow Bold", fontsize=11, linesp=10,
               fcolor="Dunkelgrün", language="de", align=1)
     ```
     and update `meta.yml::ci_overrides.non_ci_styles` to include them (extend the list from T01).

  6. **Update Impressum TextFrame**: `y_mm=96 → 101.5, h_mm=6 → 4`. Style ref now points to the already-modified `wahlaufruf/impressum` (fontsize 5, linesp 4.5 from T01).

  Verify QR-stack arithmetic:
  - `aligned_below(qr_code, qr_label, gap=2)`: qr_label.y+h = 24+5 = 29; required qr_code.y = 29+2 = 31 ✓
  - `aligned_below(qr_url, qr_code, gap=4)`: qr_code.y+h = 31+36 = 67; required qr_url.y = 67+4 = 71 ✓
  - `aligned_below(qr_label, logo_back, gap=10.3)`: logo_back.y+h = 8+5.7 = 13.7; required qr_label.y = 13.7+10.3 = 24 ✓
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight && PYTHONPATH=tools python3 templates/wahlaufruf-postkarte-a6-quer/build.py</automated>
  </verify>
  <done>
  - Both new background polygons emitted FIRST on page 1
  - `logo_back` ImageFrame uses gruene-weiss.png at (96, 8, 18.9, 5.7) with explicit local_scale=(0.130, 0.130)
  - 4-Cells loop deleted; AlignedRow wrappers gone
  - 6 frage_*_* TextFrames present at the specified coords with new ParaStyles
  - QR stack at y=24/31/71 (NOT 24/30/68)
  - `wahlaufruf/qr-label` + `wahlaufruf/qr-url` added (option a) and listed in ci_overrides.non_ci_styles
  - Impressum at y=101.5 h=4
  - build.py exits 0
  </done>
  <dont>
  - Don't use ISSUE.md's qr y values 24/30/68 — they FAIL the aligned_below constraints (locked decision #2 / ship-blocker B2/B3)
  - Don't omit `local_scale=(0.130, 0.130)` on logo_back (defaults to 1.0 → 5.5× clipped render)
  - Don't preserve any "Cell N — *" annames (smoke test in T05 asserts their absence)
  - Don't rename `Wahlkreuz` anname (case-sensitive brand rule)
  - Don't change qr_code's `scale_type=0, ratio=1` pattern — pre-existing, defer per pitfalls M5
  </dont>
</task>

<task id="T04" type="auto" tdd="false">
  <name>Task 4: V1 CONSTRAINTS list — replace existing 8 with 13-entry locked list</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/build.py</files>
  <depends-on>T03</depends-on>
  <action>
  Replace the current `CONSTRAINTS = [...]` list in `templates/wahlaufruf-postkarte-a6-quer/build.py` (the 8 entries about back-row1/row2/col1/col2 of the deleted 4-Cells grid) with the 13-entry V1 list. The frame annames referenced by the OLD constraints no longer exist, so structural_check would explode if you skip this.

  Ensure the relevant constraint factories are imported at the top of build.py:
  ```python
  from sla_lib.builder.constraints import (
      mirrored_x, mirrored_y, aligned_below, same_x, inside, distance_y,
  )
  ```
  (Adjust import path to match the existing pattern — likely already imports `same_x` etc.)

  Then replace the CONSTRAINTS list with the exact final form (verbatim — locked decisions #1, #2, #7):

  ```python
  CONSTRAINTS = [
      # Front: halo + symbol share centers (both axes), and halo contains symbol
      mirrored_x("wahlkreuz_halo", "Wahlkreuz", axis_mm=74.0, name="halo_x_centered"),
      mirrored_y("wahlkreuz_halo", "Wahlkreuz", axis_mm=48.0, name="halo_y_centered"),
      inside("Wahlkreuz", "wahlkreuz_halo", name="halo_contains_symbol"),
      # Front: headline stack vertical hierarchy (datum -> cta gap = 10mm)
      distance_y("headline_datum", "headline_cta", equals=10.0, name="datum_to_cta"),
      # Back: 3 W-Fragen share x-axis (left edge x=6) for headlines and bodies
      same_x("frage_was_headline", "frage_warum_headline", "frage_wann_headline",
             name="fragen_left_axis"),
      same_x("frage_was_body", "frage_warum_body", "frage_wann_body",
             name="bodies_left_axis"),
      # Back: per-W-Frage stack (body hangs from headline, gap=1mm, same x)
      aligned_below("frage_was_body",   "frage_was_headline",   gap_mm=1.0, name="was_stack"),
      aligned_below("frage_warum_body", "frage_warum_headline", gap_mm=1.0, name="warum_stack"),
      aligned_below("frage_wann_body",  "frage_wann_headline",  gap_mm=1.0, name="wann_stack"),
      # Back: QR block right-axis + label-above + url-below
      same_x("qr_label", "qr_code", "qr_url", name="qr_axis"),
      aligned_below("qr_code", "qr_label", gap_mm=2.0, name="qr_label_anchors_code"),
      aligned_below("qr_url",  "qr_code",  gap_mm=4.0, name="qr_url_below_code"),
      # Back: qr_label hangs from logo_back (right column stacking)
      aligned_below("qr_label", "logo_back", gap_mm=10.3, name="logo_back_anchors_qr"),
  ]
  ```

  After saving, run structural_check on this template and fix any drift before proceeding. Common failures and fixes:
  - "expected center 74.0, got X" → check halo or Wahlkreuz x_mm in T02; correct geometry not constraint
  - "below.y mismatch: expected N, got M" → check qr_*/frage_*_body y values in T03; correct geometry
  - "anname not found: X" → ensure T02/T03 spelled the anname exactly (case-sensitive, snake_case for new frames)
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight && PYTHONPATH=tools python3 templates/wahlaufruf-postkarte-a6-quer/build.py && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer</automated>
  </verify>
  <done>
  - CONSTRAINTS list has 13 entries matching the locked spec verbatim
  - Required factory imports present
  - `structural_check wahlaufruf-postkarte-a6-quer` reports 0 errors, 0 warnings (skipped count: still 3 — overrides not yet removed; that's T07)
  - All 13 CONSTRAINTS show PASS
  </done>
  <dont>
  - Don't use `same_x`/`same_y` on halo+symbol — corner-mode, will fail (locked decision #1, ship-blocker B1)
  - Don't keep any of the deleted 4-Cells constraints (annames no longer exist)
  - Don't add `inside_page` per-template — runs globally via #14
  </dont>
</task>

<task id="T05" type="auto" tdd="false">
  <name>Task 5: Rewrite smoke test — replace test_back_has_2x2_grid with W-Fragen + halo + datum/cta + qr assertions</name>
  <files>templates/_smoke/test_wahlaufruf_postkarte_a6_quer.py</files>
  <depends-on>T04</depends-on>
  <action>
  Open `templates/_smoke/test_wahlaufruf_postkarte_a6_quer.py`. Read the existing test patterns (especially how it loads the SLA and queries by anname). Then:

  1. **Delete** `test_back_has_2x2_grid` entirely (it hard-pins deleted "Cell N — *" annames).

  2. **Add** these new tests (each as a separate method, mirroring existing test patterns):

     - `test_back_has_3_w_fragen`: assert all 6 anname strings exist on page 1 — `frage_was_headline`, `frage_was_body`, `frage_warum_headline`, `frage_warum_body`, `frage_wann_headline`, `frage_wann_body`. Assert each headline is at x=6 and each body is at x=6 (same column). Assert each body's y == headline.y + headline.h + 1.0 (within 0.5mm).

     - `test_front_has_halo_and_wahlkreuz`: assert `wahlkreuz_halo` Polygon exists on page 0 with shape="ellipse" and fill="Hellgrün". Assert `Wahlkreuz` ImageFrame exists on page 0. Assert center alignment: halo center_x = Wahlkreuz center_x = 74.0 ±0.5; same for center_y = 48.0.

     - `test_front_has_datum_and_cta`: assert `headline_datum` + `headline_cta` TextFrames exist on page 0. Assert `headline_cta.y - headline_datum.y == 10.0` ±0.5.

     - `test_back_has_qr_label_and_url`: assert `qr_label`, `qr_code`, `qr_url` exist on page 1. Assert all three at x=96. Assert qr_label.y=24, qr_code.y=31, qr_url.y=71 (±0.5).

     - `test_back_has_logo_back_white`: assert `logo_back` ImageFrame exists on page 1 at (96, 8, 18.9, 5.7) with image path containing `gruene-weiss`. Assert `local_scale ≈ (0.130, 0.130)` (±0.001).

  3. Use `unittest.TestCase` style (existing convention). Lookup helpers: probe the SLA via the same loading pattern the existing tests use (likely `parse_sla(...)` from `sla_lib` or direct lxml — match the existing import block).

  4. Tests must NOT regenerate `template.sla`; they read the file as committed (T03/T04 left it in the right shape; T06 will re-render via bin/render-gallery, but T05 can run against the build.py-generated SLA from T04's verify).

  Naming: smoke test method names use `snake_case` per `unittest` convention (matches existing).
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight && PYTHONPATH=tools python3 -m unittest templates._smoke.test_wahlaufruf_postkarte_a6_quer -v</automated>
  </verify>
  <done>
  - `test_back_has_2x2_grid` removed
  - 5 new test methods added, each asserting the specified V1 anname/coord invariants
  - All tests pass
  - Smoke test discoverable via `python3 -m unittest templates._smoke.test_wahlaufruf_postkarte_a6_quer`
  </done>
  <dont>
  - Don't reference any "Cell N — *" annames
  - Don't assert exact center-pixel values; use coord-and-tolerance assertions in mm space
  - Don't import from `tests/` (wrong directory) or duplicate fixtures the existing test already declares
  </dont>
</task>

<task id="T06" type="auto" tdd="false">
  <name>Task 6: Regenerate template.sla, page-NN.png, preview.pdf, and meta.yml::previews_for_sla SHA via bin/render-gallery</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/template.sla, templates/wahlaufruf-postkarte-a6-quer/page-01.png, templates/wahlaufruf-postkarte-a6-quer/page-02.png, templates/wahlaufruf-postkarte-a6-quer/preview.pdf, templates/wahlaufruf-postkarte-a6-quer/meta.yml, site/public/templates/wahlaufruf-postkarte-a6-quer/**</files>
  <depends-on>T05</depends-on>
  <action>
  Run the gallery-regen pipeline:
  ```bash
  bin/render-gallery wahlaufruf-postkarte-a6-quer --skip-visual-diff
  ```
  This regenerates `template.sla`, both page PNGs, the preview PDF, updates `meta.yml::previews_for_sla` to the new sha256(template.sla), and copies artifacts to `site/public/templates/wahlaufruf-postkarte-a6-quer/`.

  If `bin/render-gallery` does not accept this template (no shim) or errors, fallback path:
  1. `PYTHONPATH=tools python3 templates/wahlaufruf-postkarte-a6-quer/build.py` — regen template.sla
  2. `xvfb-run -a scribus -g -ns -py /path/to/render_pdf_script.py templates/wahlaufruf-postkarte-a6-quer/template.sla` (consult `tools/render_pipeline.py:631-720` for the exact invocation pattern)
  3. `pdftoppm -r 144 templates/wahlaufruf-postkarte-a6-quer/preview.pdf templates/wahlaufruf-postkarte-a6-quer/page` to regen PNGs
  4. Manually update `meta.yml::previews_for_sla` to new `sha256sum templates/wahlaufruf-postkarte-a6-quer/template.sla | awk '{print $1}'`
  5. Mirror to `site/public/templates/wahlaufruf-postkarte-a6-quer/` (cp the files)

  Prefer the shim — fallback only if it errors.

  Verify the staleness gate passes after regen:
  ```bash
  bin/check-stale-previews
  ```

  This task does NOT remove any brand_overrides yet — that's T07.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight && bin/check-stale-previews</automated>
  </verify>
  <done>
  - `templates/wahlaufruf-postkarte-a6-quer/template.sla` regenerated (mtime newer)
  - `page-01.png`, `page-02.png`, `preview.pdf` regenerated
  - `meta.yml::previews_for_sla` SHA updated to match new template.sla
  - `site/public/templates/wahlaufruf-postkarte-a6-quer/` artifacts mirror updated
  - `bin/check-stale-previews` exits 0
  </done>
  <dont>
  - Don't manually edit the SHA in meta.yml without first regenerating template.sla
  - Don't skip the site/public mirror — CI checks it
  - Don't run with `--strict` flag if not currently default — pitfalls M5 notes the QR may render unexpectedly; visual review is human, not gating
  </dont>
</task>

<task id="T07" type="auto" tdd="false">
  <name>Task 7: Remove 3 stale meta.yml::brand_overrides + final --all + audit-alignment 0-suspicious gate</name>
  <files>templates/wahlaufruf-postkarte-a6-quer/meta.yml</files>
  <depends-on>T06</depends-on>
  <action>
  This task is the post-V1 "tightening". Execute in this exact order:

  1. **Verify `brand:line_spacing_0.9` is safe to remove**: re-run structural_check FIRST and inspect output. The new ParaStyles' linesp values:
     - headline-emphasis: fontsize=26, linesp=23 → expected 23.4 → 0.4 drift (within 0.5 tol) ✓
     - headline-cta: 14, 13 → expected 12.6 → 0.4 drift ✓
     - cell-headline-yellow: 18, 16 → expected 16.2 → 0.2 drift ✓
     - cell-body-on-green: 9, 11 → expected 8.1 → 2.9 drift ✗ (FAILS rule)
     - impressum (after T01): 5, 4.5 → expected 4.5 → 0 drift ✓

     The `cell-body-on-green` style WILL FAIL `brand:line_spacing_0.9` (linesp=11 is intentionally airy for readability on dunkelgrün — not a 0.9 multiple of fontsize). This means **KEEP `brand:line_spacing_0.9` override**. Document this in the commit body when it lands.

  2. **Remove `brand:logo_size_3M` override**: V1 makes both logos exactly 3*M = 18.9 mm. Override is now stale. Delete the entry from `meta.yml::brand_overrides`.

  3. **Remove `brand:undeclared_alignment_drift` override**: V1's CONSTRAINTS list (T04) declares all 4 stack-style adjacencies. Delete the entry. (This is the load-bearing removal — must come after T04 + T06 succeed.)

  4. After both removals, re-run structural_check on this template AND `--all`:
     ```bash
     PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer
     PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all
     ```
     Both must report 0 errors. The single template should report 0 warnings.

  5. **Run the audit gate** (THE definitive post-V1 check):
     ```bash
     PYTHONPATH=tools python3 tools/audit_alignment.py wahlaufruf-postkarte-a6-quer
     # OR via shim:
     bin/audit-alignment wahlaufruf-postkarte-a6-quer
     ```
     Required output: `suspicious-undeclared adjacencies (0):` for BOTH pages. If non-zero, add the missing pair as a CONSTRAINTS entry in build.py (back to T04), regen via T06, retry.

  6. If T07 step 1 finds `cell-body-on-green` does NOT actually trip the rule (e.g. tolerance is wider than expected or rule has additional grace), proceed to remove `brand:line_spacing_0.9` too — but **only if structural_check shows zero errors and zero warnings** with the override removed.

  Final `meta.yml::brand_overrides` shape:
  ```yaml
  brand_overrides:
    - id: brand:line_spacing_0.9
      reason: "wahlaufruf/cell-body-on-green uses airy 11pt linesp on 9pt body for readability over Dunkelgrün"
  ```
  (Two entries removed; one kept with updated reason.)
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight && PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all && bin/audit-alignment wahlaufruf-postkarte-a6-quer</automated>
  </verify>
  <done>
  - `brand:logo_size_3M` removed from meta.yml::brand_overrides
  - `brand:undeclared_alignment_drift` removed from meta.yml::brand_overrides
  - `brand:line_spacing_0.9` decision documented in commit body (kept or removed per actual rule output)
  - `structural_check wahlaufruf-postkarte-a6-quer` reports 0 errors, 0 warnings
  - `structural_check --all` stays green (no other-template regressions)
  - `bin/audit-alignment wahlaufruf-postkarte-a6-quer` reports 0 suspicious adjacencies on both pages
  </done>
  <dont>
  - Don't remove overrides BEFORE T04+T06 succeed (would cascade-fail)
  - Don't force-remove `brand:line_spacing_0.9` if it surfaces violations (locked decision: keep + document)
  - Don't proceed to T08+ if `bin/audit-alignment` is non-zero — fix CONSTRAINTS, regen, retry
  </dont>
</task>

<task id="T08" type="auto" tdd="false">
  <name>Task 8: Rewrite templates/_specs/wahlaufruf-postkarte-a6-quer.md for V1 layout</name>
  <files>templates/_specs/wahlaufruf-postkarte-a6-quer.md</files>
  <depends-on>T07</depends-on>
  <action>
  Read `templates/_specs/SCHEMA.md` §11-12 first to understand the spec format conventions (the planner directive: prose only for constraints, never duplicate the CONSTRAINTS list as YAML).

  Then rewrite `templates/_specs/wahlaufruf-postkarte-a6-quer.md` for V1:

  1. **Slot tables**: Replace the OLD layout slot inventory (12 slots: `headline_wahlaufruf`, `cell_1_*` … `cell_4_*`) with the V1 inventory:
     - Page 0 (front): `Logo Grüne (weiss)`, `wahlkreuz_halo`, `Wahlkreuz`, `headline_datum`, `headline_cta`
     - Page 1 (back): `seitenhintergrund_back_left`, `impressum_strip_bg`, `logo_back`, 6× `frage_*_*`, `qr_label`, `qr_code`, `qr_url`, `Impressum`

     For each slot row include: anname, type (Polygon/ImageFrame/TextFrame), x_mm/y_mm/w_mm/h_mm, ParaStyle (text only), notes.

  2. **ParaStyle hygiene list**: Update the section that enumerates the template's ParaStyles. New set (post-V1):
     - Existing kept: `wahlaufruf/cell-body` (Black; orphan after V1 — keep listed, mark "orphan, kept for ParaStyle migration parity"), `wahlaufruf/headline` + `wahlaufruf/cell-headline` (orphan after V1 — note for follow-up cleanup if not removed in T07's ci_overrides update)
     - Existing modified: `wahlaufruf/impressum` (fontsize 6→5, linesp 7→4.5)
     - New: `wahlaufruf/headline-emphasis`, `wahlaufruf/headline-cta` (kern=2.1), `wahlaufruf/cell-headline-yellow`, `wahlaufruf/cell-body-on-green`, `wahlaufruf/qr-label`, `wahlaufruf/qr-url` (if added in T03 step 5 option a)

  3. **Constraints section** (PROSE per SCHEMA.md §11-12): describe each of the 13 CONSTRAINTS in plain-language English (or German — match existing spec language). Cover: halo center alignment (74, 48), halo containment of symbol, datum→cta gap=10mm, fragen left axis (x=6), per-frage stack gap=1mm, QR right axis (x=96), QR label/code/url stack gaps (2mm/4mm), logo_back→qr_label stack (10.3mm). DO NOT paste Python code; describe relationships in prose.

  4. **Brand-rule notes**: document that `brand:line_spacing_0.9` is intentionally suppressed (keep override) for `cell-body-on-green`'s airy linesp; `brand:logo_size_3M` no longer suppressed (V1 enforces 3*M); `brand:undeclared_alignment_drift` no longer suppressed (V1 declares all stacks).

  5. Match the existing spec MD's section structure (front/back, slot table, ParaStyle table, constraints, notes) — read `templates/_specs/wahltag-tueranhaenger.md` as a recent V1-style reference if structure is unclear.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight && python3 -c "import pathlib; t=pathlib.Path('templates/_specs/wahlaufruf-postkarte-a6-quer.md').read_text(); assert 'Cell 1' not in t and 'frage_was_headline' in t and 'wahlkreuz_halo' in t and 'qr_label' in t, 'spec rewrite incomplete'; print('OK')"</automated>
  </verify>
  <done>
  - All "Cell N — *" references gone from spec MD
  - V1 slot inventory documented (front + back)
  - All 4-6 new ParaStyles listed
  - 13 constraints described in prose (no embedded Python)
  - Brand-rule override status documented
  </done>
  <dont>
  - Don't paste the CONSTRAINTS Python list into the spec — prose only (SCHEMA.md §11-12)
  - Don't omit the kept-orphan `wahlaufruf/cell-body` style (visibility helps #18-#21 reuse the migration pattern)
  - Don't reference V2/V3 layouts in this spec (they're backlog; keep this spec focused on V1)
  </dont>
</task>

<task id="T09" type="auto" tdd="false">
  <name>Task 9: Append session-history row to DESIGN-SYSTEM-BRIEF §10 + update improvements/01 Resulting-issue link</name>
  <files>shared/brand/DESIGN-SYSTEM-BRIEF.md, improvements/01-wahlaufruf-postkarte.md</files>
  <depends-on>T08</depends-on>
  <action>
  1. Open `improvements/01-wahlaufruf-postkarte.md` and locate §"Session-History". Read the seed row (around lines 299-301 per pitfalls.md). Use it verbatim as the seed for the brief's §10 row.

  2. Open `shared/brand/DESIGN-SYSTEM-BRIEF.md` and locate §10 (session-history table). Replace the "_empty_ | _start of history_" stub row (or add a new row after the most recent if stub already replaced) with the row from improvements/01:
     - date: 2026-05-08 (per the design package authorship)
     - design package: `improvements/01-wahlaufruf-postkarte.md`
     - resulting issue: GitHub URL `https://github.com/GrueneAT/vorlagen/issues/33` (per ISSUE.md frontmatter `source_url`)
     - PR URL: leave a placeholder marker or fill at ship-time per the prompt's "filed PR URL added at ship time"

  3. In `improvements/01-wahlaufruf-postkarte.md` §"Session-History", update the `Resulting issue` cell to the same GitHub URL.

  Match the existing table column structure; do not invent new columns.
  </action>
  <verify>
  <automated>cd /root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight && grep -F "improvements/01-wahlaufruf-postkarte.md" shared/brand/DESIGN-SYSTEM-BRIEF.md && grep -F "github.com/GrueneAT/vorlagen/issues/33" improvements/01-wahlaufruf-postkarte.md</automated>
  </verify>
  <done>
  - §10 in DESIGN-SYSTEM-BRIEF.md contains a row referencing `improvements/01-wahlaufruf-postkarte.md` and issue #33
  - improvements/01-wahlaufruf-postkarte.md §Session-History `Resulting issue` cell points to the GitHub URL
  - Existing table structure preserved (no new columns)
  </done>
  <dont>
  - Don't fabricate a PR URL — leave the placeholder until ship time
  - Don't reformat the entire §10 table; append/replace the single row
  - Don't reference V2 or V3 in the row — this is V1's history
  </dont>
</task>

</tasks>

<verification>
After all 9 tasks, run final integration checks (the executor may also run these between tasks for early signal):

```bash
cd /root/workspace/.worktrees/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight

# 1. Build regenerates cleanly
PYTHONPATH=tools python3 templates/wahlaufruf-postkarte-a6-quer/build.py

# 2. Per-template structural check — 0 errors, 0 warnings
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer

# 3. Cross-template structural check stays green
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all

# 4. CI style check passes
python3 tools/check_ci.py templates/wahlaufruf-postkarte-a6-quer/template.sla

# 5. Stale-previews gate passes (post-T06 SHA bump)
bin/check-stale-previews

# 6. THE definitive post-V1 gate — 0 suspicious adjacencies on both pages
bin/audit-alignment wahlaufruf-postkarte-a6-quer

# 7. Smoke test passes
PYTHONPATH=tools python3 -m unittest templates._smoke.test_wahlaufruf_postkarte_a6_quer -v

# 8. Stdlib unittest discovery passes
PYTHONPATH=tools python3 -m unittest discover tools/sla_lib/tests
```

All 8 must exit 0 / report all-green.
</verification>

<success_criteria>
Maps 1:1 to ISSUE.md acceptance criteria (with the 2 RESEARCH.md corrections — locked decisions #8 + #11):

- [x] All build.py edits land in commits prefixed `17:`. (T01-T04 commits — one per task; consolidation acceptable per atomic-PR-ordering.)
- [x] `python3 templates/wahlaufruf-postkarte-a6-quer/build.py` regenerates `template.sla` cleanly. (T02-T04 verify steps.)
- [x] `python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer` reports zero errors, all 13 CONSTRAINTS green. (T04 + T07 verify.)
- [x] `python3 -m sla_lib.builder.structural_check --all` stays green (no regressions on other templates). (T07 verify.)
- [x] `tools/check_ci.py` passes (no brand-color or style drift; new ParaStyles allowlisted via ci_overrides.non_ci_styles). (T01 + T03 update; final verification step 4.)
- [x] **CORRECTED** (locked decision #8): No `meta.yml::original_sla` field present (verified absent — layout changes are free of pixel-diff gating). The `previews_for_sla` SHA IS present and IS bumped via T06.
- [x] `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 row appended with seed from `improvements/01-…`. (T09.)
- [x] `improvements/01-wahlaufruf-postkarte.md` §Session-History `Resulting issue` cell points to GitHub #33 URL. (T09.)
- [x] **ADDED** (locked decisions #7, #9, #10, #13): `bin/audit-alignment wahlaufruf-postkarte-a6-quer` reports 0 suspicious adjacencies on both pages; smoke test rewritten; spec MD rewritten; 2 of 3 stale brand_overrides removed (`logo_size_3M`, `undeclared_alignment_drift`); `line_spacing_0.9` kept with documented reason.
</success_criteria>

<risks_and_verification>

## The 3 ship-blockers (RESEARCH.md / pitfalls.md) and how this plan avoids them

| Ship-blocker | Avoidance in plan |
|---|---|
| **B1**: `same_x/same_y(halo, Wahlkreuz)` checks corner; halo+symbol corners differ by 1mm → FAIL | T04 uses `mirrored_x("wahlkreuz_halo", "Wahlkreuz", axis_mm=74.0)` + `mirrored_y(..., axis_mm=48.0)` (locked decision #1). T02 places frames so centers match (74, 48). T05 smoke test asserts center alignment in mm space. |
| **B2**: `aligned_below(qr_code, qr_label, gap=2)` with ISSUE.md y=24/30 → required y=31, drift 1mm > 0.5 tol → FAIL | T03 uses qr_label.y=24, qr_code.y=**31** (locked decision #2). T04 declares the constraint with gap=2. T05 smoke test asserts qr_code.y=31. |
| **B3**: `aligned_below(qr_url, qr_code, gap=4)` cascading from B2 — ISSUE.md y=68 → required 71 → FAIL | T03 uses qr_url.y=**71** (locked decision #2). T04 declares the constraint with gap=4. T05 smoke test asserts qr_url.y=71. |

## Atomic-PR ordering reminder

Tasks execute strictly in order T01 → T09 because each depends on the previous:
- build.py edits (T01-T04) before regen (T06) — otherwise SHA mismatches
- regen (T06) before brand_overrides removal (T07) — otherwise audit reads stale SLA
- brand_overrides removal (T07) before spec rewrite (T08) — spec documents post-removal status
- spec (T08) before brief (T09) — brief references the design package, not the spec

The `bin/audit-alignment wahlaufruf-postkarte-a6-quer` 0-suspicious gate (T07 step 5) is **non-negotiable**. If non-zero post-T07, return to T04 (add missing CONSTRAINTS), re-T06 (regen), re-T07 (remove + audit). Do NOT proceed to T08/T09 with a non-zero audit.

## Conditional outcomes documented in commit bodies

- **T07 + `brand:line_spacing_0.9`**: if removal surfaces violations on `cell-body-on-green` (linesp=11 vs expected 0.9 × 9 = 8.1 → 2.9 drift), KEEP the override and document in T07's commit body: "Override retained: `wahlaufruf/cell-body-on-green` uses 11pt linesp on 9pt body for readability on Dunkelgrün; intentional brand exception."
- **T03 step 5 option (a) vs (b)**: chose (a) — adding `wahlaufruf/qr-label` + `wahlaufruf/qr-url` for ISSUE.md's Dunkelgrün label/URL color spec. Document in T03 commit body: "Inline-added 2 ParaStyles for QR label + URL (Gotham Narrow Bold 12/11pt Dunkelgrün, align=1) per ISSUE.md spec; ci_overrides extended."

## Out-of-scope reminders (do NOT do these in this plan)

- V2 "Datum-Banner" / V3 "Asymmetric Hero" — backlog issues
- Sample/photo curation — covered by #13
- Pixel-diff visual review — human PR-review, not agent
- `wahlaufruf/cell-body` mutation — locked decision #5: parallel new style `cell-body-on-green` instead
- `meta.yml::slots` rename — H4 in pitfalls.md flags as documentation-only drift (no CI gate); deferred
- INJECT_MAP — locked decision #12: not needed (all V1 frames are hardcoded text or pack_inline_image)

</risks_and_verification>
