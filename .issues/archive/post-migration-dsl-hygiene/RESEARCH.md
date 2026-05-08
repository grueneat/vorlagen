# RESEARCH — Post-migration DSL hygiene

**Researched:** 2026-05-07
**Issue:** post-migration-dsl-hygiene (#9 / GH #17)
**Confidence:** HIGH
**Mode:** standalone (no CONTEXT.md; autonomous)

## Summary

Three hygiene items deferred during migrations #6/#7/#8. **A) Impressum widening:** the three "gaps" are not three independent kwargs — they are one **2-or-3-Run schema** plus one **TextFrame-passthrough** kwarg (`rotation_deg`). All three corpus sites already exist as primitives in the rebuilt templates and can be substituted by the widened block 1-for-1. **B) ZeitungConverterFreshRun:** straight mirror of `PostkarteConverterFreshRun` against `gruene-zeitung-vorlage-original.sla`, reusing the existing `extra-style`/`extra-layer`/`extra-color`/`missing-layer Ebene 1` allowlist. **C) extras audit:** verified empirically — **0 hoist candidates remain** (`set(postkarte) ∩ set(plakat) ∩ set(zeitung)` produces 23 doc-attrs and 11 pdf-attrs as keys, but **0 of them have identical values across all three** templates). The existing `ci-defaults.yml` already absorbs every truly-shared key. `_LEGACY_LAYER_NAMES = ("Ebene 1",)` is **complete-as-is** — Postkarte and Plakat originals only carry `Hintergrund`, which the brand stack supplies (no extra legacy name to add).

**Primary recommendation:** Land Impressum widening as a **unified `runs=` override** + 3 narrow kwargs (`prefix_text`, `prefix_font`, `heading_text`, `heading_font`, `heading_paragraph_style`, `rotation_deg`, `line_width_pt`, `col_gap_mm`); add `ZeitungConverterFreshRun`; document the extras audit as **complete with no hoists possible**; document `_LEGACY_LAYER_NAMES` as complete; do NOT touch `ci-defaults.yml`. Estimated 5 PLAN.md tasks.

---

## A. Impressum widening

### Current API (lines 117-151 of `tools/sla_lib/builder/blocks.py`)

```python
@dataclass
class Impressum:
    text: str = DEFAULT_IMPRESSUM
    x_mm: float = 5
    y_mm: float = 142
    w_mm: float = 95
    h_mm: float = 6
    fcolor: Optional[str] = None
    layer: int = 2
    anname: str = "Impressum"

    def emit(self) -> Iterable:
        yield TextFrame(
            x_mm=..., y_mm=..., w_mm=..., h_mm=...,
            trail_style="Impressum",
            runs=[Run(text=self.text, paragraph_style=None)],
            fcolor=..., layer=..., anname=...,
        )
```

The block emits exactly one `TextFrame` with one `Run`. None of the three corpus sites can substitute today.

### A1. Bold-prefix Run (Postkarte gap)

**Corpus:** `templates/postkarte-a6-kampagne/build.py:223-236` (page1, after the `Kontaktmöglichkeiten` frame).

```python
page1.add(TextFrame(
    x_mm=61.661363401048646,
    y_mm=135.4351365188583,
    w_mm=41.944954128440244,
    h_mm=10.619582059123314,
    layer=0,
    line_width_pt=1,
    trail_style='Impressum',
    col_gap_mm=0,
    runs=[
        Run(text='Impressum:', font='Gotham Narrow Bold', fcolor='White', features='inherit', fshade=100),
        Run(text=' Medieninhaber und Herausgeber: Die Grünen Niederösterreich, Daniel-GranStraße 48, 3100 St. Pölten. ·  Druck: Druckerei mit Postanschrift · Evtl. Hinweis auf Umweltzeichens wenn zutreffend', fcolor='White', fshade=100),
    ],
))
```

**Schema:** 2 Runs in one frame, no separator between them (no para break → same line, font switch mid-line).

- Run 0: prefix `'Impressum:'` with **Bold** font + explicit `fcolor`/`features`/`fshade`.
- Run 1: body text leading with a single space, same `fcolor`/`fshade`, default font (inherits from `trail_style='Impressum'`).
- Frame extras: `layer=0`, `line_width_pt=1`, `col_gap_mm=0`.

### A2. Rotation (Plakat gap)

**Corpus:** `templates/plakat-a1-hochformat/build.py:91-105` (page0).

```python
page0.add(TextFrame(
    x_mm=563.6934545616729,
    y_mm=832.6888888888903,
    w_mm=377.37598988277136,
    h_mm=21.023500433233103,
    layer=0,
    rotation_deg=270,
    line_width_pt=1,
    trail_style='Impressum',
    col_gap_mm=0,
    runs=[
        Run(text='Impressum:', font='Gotham Narrow Bold', fcolor='White', fshade=100),
        Run(text=' Medieninhaber und Herausgeber: Die Grünen Niederösterreich, Daniel-GranStraße 48, 3100 St. Pölten. ·  Druck: Druckerei mit Postanschrift · Evtl. Hinweis auf Umweltzeichens wenn zutreffend', fcolor='White', fshade=100),
    ],
))
```

**Schema:** identical to Postkarte's 2-Run prefix idiom plus **`rotation_deg=270`**. (The Postkarte Run 0 carries `features='inherit'`; Plakat does not. This is a per-site nuance — preserve as a kwarg on the prefix Run, default `None`.)

### A3. Heading + spacer + body 3-Run schema (Zeitung gap)

**Corpus:** `templates/zeitung-a4-grun/build.py:2445-2459` (page13).

```python
page13.add(TextFrame(
    x_mm=54.8648134556576,
    y_mm=118.88680122647573,
    w_mm=103.46422018348632,
    h_mm=30.471532106858525,
    layer=0,
    line_width_pt=1,
    trail_style='Impressum',
    col_gap_mm=0,
    runs=[
        Run(text='Impressum', separator='para', paragraph_style='Inhaltsheadline Titelseite'),
        Run(text='', has_itext=False, separator='para', paragraph_style='Inhaltsheadline Titelseite'),
        Run(text='Medieninhaber u. Herausgeber: Die Grünen Niederösterreich, Daniel Gran Straße 48, 3100 St. Pölten • Redaktion: Ortsgruppe + Anschrift •  Verteilt durch Firma/Post • Erscheinungstermin: April 2026 • Druck: Druckerei + Postanschrift • Fotos:wenn nicht anders angegeben: Name'),
    ],
))
```

**Schema:** 3 Runs.

- Run 0: heading `'Impressum'` with `separator='para'` and `paragraph_style='Inhaltsheadline Titelseite'`.
- Run 1: an **empty para spacer** — `text=''`, `has_itext=False`, `separator='para'`, `paragraph_style='Inhaltsheadline Titelseite'` (the empty paragraph carries the heading style so the gap height matches the heading line height).
- Run 2: body text, no separator (last unterminated paragraph picks up `trail_style='Impressum'`).

Note: the heading `paragraph_style` is `Inhaltsheadline Titelseite`, **different** from `trail_style='Impressum'`. The spacer must replicate the heading style (this is the load-bearing detail — without it the empty paragraph collapses).

### A4. Recommended API shape

**Recommendation: hybrid — keep the existing default-text emission, add narrow optional kwargs for the three gaps, and a `runs=` escape hatch.**

Rationale:
- Three independent kwargs (`prefix_text`, `heading_text`, `rotation_deg`) covers exactly the three corpus shapes with no abstraction overhead.
- A unified `headers: list[ImpressumHeader]` form is overkill — there is **one** prefix idiom and **one** heading idiom in the entire corpus, never both at once.
- Keep an `runs=Sequence[Run] | None = None` escape so future templates with a fourth idiom don't require another block edit.

**Proposed dataclass (replaces lines 116-151 of `blocks.py`):**

```python
@dataclass
class Impressum:
    """Bottom-of-page legal text block with trail_style='Impressum'.

    Three substitutable shapes (>=1 corpus site each):
    - 1-Run body (default; 0 corpus sites today, but the documented baseline)
    - 2-Run with bold prefix (Postkarte page1, Plakat page0)
    - 3-Run with heading + para-spacer + body (Zeitung page13)
    Plus rotation passthrough (Plakat) and frame-attr passthroughs.
    """
    text: str = DEFAULT_IMPRESSUM
    x_mm: float = 5
    y_mm: float = 142
    w_mm: float = 95
    h_mm: float = 6
    fcolor: Optional[str] = None
    layer: int = 2
    anname: str = "Impressum"

    # A1. Bold-prefix Run (Postkarte, Plakat). When prefix_text is set the
    # block emits TWO Runs in the body paragraph: prefix in prefix_font then
    # `text` in the trail_style font. Both runs share fcolor and fshade.
    prefix_text: Optional[str] = None
    prefix_font: str = "Gotham Narrow Bold"
    prefix_features: Optional[str] = None    # Postkarte: 'inherit'; Plakat: omit
    prefix_fshade: Optional[int] = 100       # both corpus sites: 100

    # A2. Rotation passthrough (Plakat). 270 = vertical right-margin.
    rotation_deg: float = 0

    # A3. Heading + spacer + body (Zeitung). When heading_text is set the
    # block emits THREE Runs: heading (with separator='para'), empty spacer
    # (separator='para', has_itext=False), then body.
    heading_text: Optional[str] = None
    heading_font: Optional[str] = None        # default: inherit from heading_paragraph_style
    heading_paragraph_style: Optional[str] = None  # e.g. 'Inhaltsheadline Titelseite'

    # Frame-attr passthroughs (all three corpus sites carry these explicitly).
    line_width_pt: Optional[float] = None
    col_gap_mm: Optional[float] = None

    # Escape hatch for future idioms outside the three above.
    runs: Optional[Sequence[Run]] = None      # if set, overrides everything else

    # Run-attr passthroughs that match all three corpus body Runs.
    body_fshade: Optional[int] = None
```

**`emit()` body (sketch):**

```python
def emit(self) -> Iterable:
    if self.runs is not None:
        body_runs = list(self.runs)                          # full override
    elif self.heading_text is not None:
        # 3-Run heading + spacer + body
        body_runs = [
            Run(text=self.heading_text, separator='para',
                paragraph_style=self.heading_paragraph_style,
                font=self.heading_font),
            Run(text='', has_itext=False, separator='para',
                paragraph_style=self.heading_paragraph_style),
            Run(text=self.text, fcolor=self.fcolor, fshade=self.body_fshade),
        ]
    elif self.prefix_text is not None:
        # 2-Run bold-prefix idiom
        body_runs = [
            Run(text=self.prefix_text, font=self.prefix_font,
                fcolor=self.fcolor, features=self.prefix_features,
                fshade=self.prefix_fshade),
            Run(text=self.text, fcolor=self.fcolor, fshade=self.body_fshade),
        ]
    else:
        # 1-Run default (existing behaviour)
        body_runs = [Run(text=self.text, paragraph_style=None)]

    tf_kwargs = dict(
        x_mm=self.x_mm, y_mm=self.y_mm, w_mm=self.w_mm, h_mm=self.h_mm,
        trail_style="Impressum",
        runs=body_runs,
        fcolor=self.fcolor, layer=self.layer, anname=self.anname,
    )
    if self.rotation_deg:
        tf_kwargs["rotation_deg"] = self.rotation_deg
    if self.line_width_pt is not None:
        tf_kwargs["line_width_pt"] = self.line_width_pt
    if self.col_gap_mm is not None:
        tf_kwargs["col_gap_mm"] = self.col_gap_mm
    yield TextFrame(**tf_kwargs)
```

**Backward compatibility:** verified by inspection. With all new kwargs at default (None / 0), the if/elif/else falls through to the original `[Run(text=self.text, paragraph_style=None)]` and the only TextFrame kwargs that ship are the existing ones. Existing `ImpressumTests` (5 tests at `test_blocks.py:140-184`) continue to pass without modification.

**Verification gate:** run `python3 -m unittest discover tools/sla_lib/tests` AND `pytest tools/sla_lib/tests -q` — both must be green.

---

## B. ZeitungConverterFreshRun test class

`test_sla_to_dsl.py` has `PostkarteConverterFreshRun` (lines 81-116) but no Zeitung counterpart. Mirror its structure 1-for-1 against `gruene-zeitung-vorlage-original.sla`, with the warning allowlist already used by `ZeitungRoundTrip` (lines 163-198).

### Proposed class

Append after `ZeitungRoundTrip` (after line 206):

```python
class ZeitungConverterFreshRun(unittest.TestCase):
    """Run the converter from scratch in a tempdir against the Zeitung
    original and verify the diff stays clean. Mirror of
    PostkarteConverterFreshRun adapted for Zeitung's 14-page facing-pages
    layout, 84 linked-story chains, and Ebene 1 legacy layer."""

    ORIGINAL = ROOT / "gruene-zeitung-vorlage-original.sla"

    def test_fresh_convert_is_clean(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            spec = importlib.util.spec_from_file_location(
                "sla_to_dsl", str(ROOT / "tools" / "sla_to_dsl.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.convert(self.ORIGINAL, tmp / "build.py",
                         "zeitung-a4-grun", tmp / "assets")
            sla = _run_build(tmp / "build.py")
            report = _diff_clean(self.ORIGINAL, sla)
            self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0,
                             msg=f"critical issues: "
                                 f"{[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_CRITICAL]}")
            _BRAND_COLOR_NAMES = (
                "Black", "White", "Registration",
                "Dunkelgrün", "Hellgrün", "Gelb", "Magenta",
            )
            _LEGACY_LAYER_NAMES = ("Ebene 1",)
            non_brand_warnings = [
                i for i in report.issues
                if i.severity == sla_diff.SEVERITY_WARNING
                and not (
                    i.code in ("extra-style", "extra-layer")
                    or (i.code == "extra-color" and i.right in _BRAND_COLOR_NAMES)
                    or (i.code == "missing-layer" and i.left in _LEGACY_LAYER_NAMES)
                )
            ]
            self.assertEqual(non_brand_warnings, [],
                             msg=f"unexpected warning issues: "
                                 f"{[i.short() for i in non_brand_warnings]}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
```

**Acceptance:** `python3 -m unittest tools.sla_lib.tests.test_sla_to_dsl.ZeitungConverterFreshRun` exits 0 in <30s. (Note: this run will rebuild Zeitung's full 2463-LOC build.py; expected duration ~10-20s on local hardware.)

**Risk:** the fresh-run path may surface a converter-side bug that the committed build.py masks (someone hand-edits the committed build.py to fix a converter quirk → fresh run regenerates the quirk). If the test fails, it MUST surface as a converter fix or a deliberate hand-edit-to-builder migration, not as an allowlist widening.

---

## C. Extras audit

### C1. `extra_doc_attrs` / `extra_pdf_attrs` cross-template

**Method:** programmatically computed `set ∩ set ∩ set` over the three template `Document(...)` calls (Postkarte build.py:29-30, Plakat build.py:28-29, Zeitung build.py:29-30).

**Hard counts:**

| Layer | Postkarte keys | Plakat keys | Zeitung keys | Common keys (set intersection) | Hoist candidates (identical VALUES across all 3) |
|---|---|---|---|---|---|
| `extra_doc_attrs` | 23 | 23 | 23 | 23 | **0** |
| `extra_pdf_attrs` | 11 | 11 | 11 | 11 | **0** |

**The post-migration extras blobs already match what `ci-defaults.yml` predicts.** The header comment of `ci-defaults.yml` lines 11-21 lists the exact 23 doc-attr names and 11 pdf-attr names that "differ between templates" — they are the same 23 + 11 keys we see in each `build.py`. Every truly-shared key was already absorbed by `default_doc_attrs` and `default_pdf_attrs` during issues #6/#7/#8. **No hoist work remains.**

**Why no hoists are possible:**
- `AUTOCHECK`, `GROUPC`, `SHOWBASE`, `SHOWGRID`, `SHOWGUIDES`, `SHOWMARGIN`, `calligraphicPenAngle`, `renderStack` — Scribus user-preference state, varies by who saved the file.
- `DPIn3`/`DPInCMYK`/`DPPr` and PDF `ImageP`/`PrintP`/`SolidP` — color-profile names: Postkarte/Plakat use ECI Uncoated (commercial ad-hoc print), Zeitung uses ISO Coated v2 (newspaper print). Different print stocks, must stay per-template.
- `PAGESIZE` (`A6`/`Custom`/`A4`), `PicRes` (300/600), `Version` (14/10) — directly template-defining; cannot hoist.
- `GapVertical`, `MAJGRID`, `MINGRID`, `POLYF`, `Scratch*`, `dispX`/`dispY` — values are *almost* identical between Postkarte and Plakat (e.g. `'40'` vs `'40'`) but Zeitung is `'39.9996850393701'`. The Zeitung values came from the original Scribus-1.5 export's higher-precision float serialization. These look like rounding noise but `sla_diff` treats them as different strings; rewriting Zeitung's values to match Postkarte/Plakat would fail visual_diff for Zeitung. **Cannot 3-way-hoist.**

**Two-way Postkarte=Plakat shared values (15 doc-attrs + 7 pdf-attrs):** these are share-able as a `gruene_noe_kleinformat` (small-format) preset, but a 2-way preset adds API surface for one-off LOC savings (~15 lines × 2 templates = 30 LOC). **Recommendation: do NOT introduce a 2-way preset.** The work is not worth the maintenance cost; flag for a future issue if a 4th small-format template lands.

**Brand-default-conflict check:** none. Each template's extras blob contains exactly the keys NOT in `default_doc_attrs` / `default_pdf_attrs`. No re-emission.

**Action item for PLAN.md:** record the audit result in EXECUTION.md as "audit complete — 0 hoist candidates; extras blobs and ci-defaults.yml are correctly partitioned." Do **not** modify `ci-defaults.yml` or any `build.py` for this audit.

### C2. `_LEGACY_LAYER_NAMES`

**Current value** (`tools/sla_diff.py:57-59`):
```python
_LEGACY_LAYER_NAMES = (
    "Ebene 1",  # Scribus German default; replaced by Brand.gruene_noe()'s 4-layer stack.
)
```

**Method:** grepped `<LAYERS NAME=...>` in the three originals (workspace root):

| Original | Layer NAME values |
|---|---|
| `postkarte-vorlage-original.sla` | `Hintergrund` (1 layer) |
| `plakat-a1-hochformat-original.sla` | `Hintergrund` (1 layer) |
| `gruene-zeitung-vorlage-original.sla` | `Ebene 1` (1 layer) |

`Hintergrund` is one of the four brand-stack layer names supplied by `Brand.gruene_noe()` (alongside `Bilder`, `Text`, `Hilfslinien`), so it produces no `missing-layer` warning at all. Only Zeitung's `Ebene 1` (German default for new Scribus docs) is non-brand and needs to stay in `_LEGACY_LAYER_NAMES`.

**Result: `_LEGACY_LAYER_NAMES = ("Ebene 1",)` is complete-as-is.** No additions needed for the three current templates. The existing source comment ("Add new legacy names if future templates surface them") is already correct.

**Action item:** no code change. Document the audit outcome in EXECUTION.md.

---

## D. Test runner discipline

CI uses `python3 -m unittest discover tools/sla_lib/tests` (verified at `.github/workflows/pages.yml:91`). Local development typically uses `pytest tools/sla_lib/tests -q`. **Both must pass** before any commit on this branch.

Concrete rules for the executor:
- All new test classes MUST inherit from `unittest.TestCase`.
- **No `import pytest`** anywhere in `tools/sla_lib/tests/*.py` — pytest is not installed in CI. (Verified clean across all 13 test files in this repo at research time.)
- **No `@pytest.fixture`, `@pytest.mark.*`, parametrize decorators, or `pytest.raises`.** Use `unittest`'s `setUp`/`tearDown`, `subTest()`, and `assertRaises`.
- The verify gate for this issue MUST run BOTH commands:
  ```bash
  pytest tools/sla_lib/tests -q
  python3 -m unittest discover tools/sla_lib/tests
  ```
  The `pytest` command catches local lint-class issues that unittest tolerates; the `unittest` command catches CI-only failures (the #16 / Zeitung executor merged a stray `import pytest` that local pytest happily ignored but CI failed on).
- The `bin/validate --ci` gate (and visual_diff against committed gallery PDFs) is the FINAL gate after tests are green. See `bin/validate` for the exact sla_diff + visual_diff invocation.

---

## E. Risks and unknowns

**E1. Backward compatibility of Impressum widening (LOW risk, HIGH confidence).** Existing `ImpressumTests` (5 tests) construct the block with no new kwargs; the proposed `emit()` falls through to the existing 1-Run shape via the final `else` branch. Verified by static reading of `test_blocks.py:140-184`: no test sets `prefix_text`/`heading_text`/`runs`/`rotation_deg`. Run both unittest and pytest after edit to confirm.

**E2. Impressum substitution drift in committed build.py (MEDIUM risk).** ISSUE.md acceptance criteria do NOT require swapping the three primitive `TextFrame(trail_style='Impressum', ...)` corpus sites for `Impressum(...)` block calls. Per ISSUE.md "verify by either re-running the converter [...] OR by adding a unit test per gap in `test_blocks.py`": **the safer path is to add tests in `test_blocks.py`**, not to substitute. Substituting in build.py would require regenerating + visual_diff for each template — extra LOC churn and test-coverage risk for a hygiene-only issue. **Recommendation: add tests, do NOT swap the corpus sites.** This keeps the committed build.py round-trip-clean. Note: this contradicts a literal reading of ISSUE.md's "OR" but follows ISSUE.md's "Hygiene only — no behavioural changes" framing for B and C; A's "behavioural change" is the API widening, not a corpus rewrite.

**E3. ZeitungConverterFreshRun runtime (LOW risk).** Zeitung's converter run + build + diff is the slowest in the suite — expected ~10-20s. CI tolerance: this brings unittest discover total runtime up by ~15s. Acceptable. No timeout knob needed.

**E4. ZeitungConverterFreshRun surfaces latent bugs (MEDIUM risk).** A genuine fresh-run failure means the committed `templates/zeitung-a4-grun/build.py` has been hand-edited away from what the converter emits. Resolution path: read the diff carefully — either fix the converter (preferred) or roll the hand edit back into the converter. Do NOT widen the warning allowlist to make the test pass.

**E5. Brand-default-conflict invisible in audit (LOW risk).** The C1 audit only checks for keys present in extras blobs. A key that's present in `ci-defaults.yml` AND in an `extra_*_attrs` blob would be a re-emission bug. Spot-checked: no key in any template's `extra_doc_attrs` or `extra_pdf_attrs` overlaps with `default_doc_attrs` or `default_pdf_attrs` keys in `ci-defaults.yml`. Confidence HIGH.

**E6. Hoist-candidate revisited if a 4th small-format template lands.** If a future template uses Postkarte/Plakat-style attributes (commercial print with ECI uncoated, short-run, A4-or-smaller), the 15-doc + 7-pdf 2-way preset becomes worth reconsidering. Out of scope here.

---

## Project Constraints (from ./CLAUDE.md)

No workspace `./CLAUDE.md` file at `/root/workspace/CLAUDE.md` (verified). Repo conventions captured implicitly via the existing test files and the `bin/validate` pipeline.

---

## Recommendations to the planner

Estimated 5 PLAN.md tasks, ordered:

1. **Task 1 — Widen `Impressum` dataclass.** Edit `tools/sla_lib/builder/blocks.py:116-151` per the A4 sketch above. Add the 8 new optional kwargs (`prefix_text`, `prefix_font`, `prefix_features`, `prefix_fshade`, `rotation_deg`, `heading_text`, `heading_font`, `heading_paragraph_style`, `line_width_pt`, `col_gap_mm`, `body_fshade`, `runs`). Replace `emit()` with the 3-branch if/elif/else body. **Verify:**
   ```bash
   python3 -m unittest tools.sla_lib.tests.test_blocks
   pytest tools/sla_lib/tests/test_blocks.py -q
   ```
   Both must be green; existing `ImpressumTests` must pass unchanged.

2. **Task 2 — Add 3 Impressum unit tests in `test_blocks.py`.** Inside `ImpressumTests` (lines 140-184) add three methods:
   - `test_impressum_prefix_emits_two_runs_no_separator` — construct with `prefix_text='Impressum:'`, parse the saved SLA, assert exactly 2 ITEXT children of StoryText, first has `FONT='Gotham Narrow Bold'`, second does not.
   - `test_impressum_rotation_passes_through` — construct with `rotation_deg=270`, parse, assert PAGEOBJECT carries `ROT='270'`.
   - `test_impressum_heading_emits_three_runs_with_para_separator` — construct with `heading_text='Impressum'`, `heading_paragraph_style='Inhaltsheadline Titelseite'`, parse, assert StoryText has heading ITEXT + para + (empty/no ITEXT) + para + body ITEXT pattern. Use only `unittest.TestCase` idioms. **Verify:**
   ```bash
   python3 -m unittest tools.sla_lib.tests.test_blocks.ImpressumTests
   pytest tools/sla_lib/tests/test_blocks.py::ImpressumTests -q
   ```

3. **Task 3 — Add `ZeitungConverterFreshRun`.** Append the class shown in section B to `test_sla_to_dsl.py` after line 206 (after `ZeitungRoundTrip`). Use the exact warning allowlist from `ZeitungRoundTrip`. **Verify:**
   ```bash
   python3 -m unittest tools.sla_lib.tests.test_sla_to_dsl.ZeitungConverterFreshRun
   pytest tools/sla_lib/tests/test_sla_to_dsl.py::ZeitungConverterFreshRun -q
   ```
   Expected duration ~15s. If it fails: do NOT widen the allowlist — read the failing diff and decide between converter fix vs. hand-edit rollback.

4. **Task 4 — Document the C1 + C2 audit outcomes.** Write a short note in `EXECUTION.md` recording the hard counts (0 doc-attr hoist candidates, 0 pdf-attr hoist candidates, `_LEGACY_LAYER_NAMES` complete-as-is). No code or YAML changes. **Verify:** EXECUTION.md exists and contains the audit outcome paragraph.

5. **Task 5 — Final gate.** Run all of the following from the worktree root:
   ```bash
   pytest tools/sla_lib/tests -q
   python3 -m unittest discover tools/sla_lib/tests
   bin/validate --ci
   ```
   All three must exit 0. `bin/validate --ci` validates all three templates' `sla_diff --strict` + `visual_diff` against committed gallery PDFs. **Acceptance:** all three exit 0; ISSUE.md's 7 acceptance criteria checked off in EXECUTION.md.

**Out of scope** (do not do these in this issue):
- Substituting the three Impressum corpus sites in `templates/*/build.py` for block calls (E2).
- Hoisting any `extra_*_attrs` keys to `ci-defaults.yml` (C1: 0 candidates).
- Adding a 2-way `gruene_noe_kleinformat` preset (E6).
- Touching `tools/sla_to_dsl.py` (converter behavioural changes are explicitly excluded by ISSUE.md "Non-goals").
