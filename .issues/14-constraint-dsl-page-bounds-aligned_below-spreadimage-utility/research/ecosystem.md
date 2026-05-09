# Ecosystem research — Issue 14 (constraint-DSL: inside_page, aligned_below, SpreadImage)

**Scope:** Internal Python library `tools/sla_lib/`. No external user-facing surface. Ecosystem questions are about *how this repo is built* (Python version, test style, lint, geometry priors) — not about library shopping.

**TL;DR:** No new dependencies. New code must match the existing zero-config, stdlib-only style. The `SpreadImage` utility emits **two `ImageFrame`s** (one per page, sharing source via `local_offset_mm`) — that's the only structurally-sound option in Scribus's SLA model and the existing primitive (`ImageFrame.local_offset_mm`) already supports it.

---

## 1. Standard Stack (HIGH confidence — direct file inspection)

| Concern | What's used | Where pinned | Notes |
|---|---|---|---|
| Python | **3.13** (system `python3`) | `Dockerfile.claude:13-15` ("trixie scribus depends on libpython3.13, which promotes the system python from 3.11 → 3.13"); CI uses `ubuntu-latest` system `python3` | No `python_requires` declared anywhere — repo is run as `python3 tools/x.py`, never installed as a package. **No `pyproject.toml`, no `setup.py`, no `setup.cfg`, no `requirements.txt`** anywhere in the repo (verified by exhaustive `find`). |
| Test runner | **stdlib `unittest`** | `.github/workflows/pages.yml:104-105` → `python3 -m unittest discover tools/sla_lib/tests` | NOT pytest. No `pytest.ini`, no `[tool.pytest]`, no `conftest.py`. |
| Test style | `class XTests(unittest.TestCase)` + `test_…` methods + `self.assert…` | `tools/sla_lib/tests/test_constraints.py:33-77`, `test_brand_constraints.py:47-…`, `test_blocks.py:43-…` | Module preamble is fixed: `from __future__ import annotations`, `sys.path.insert(0, str(ROOT / "tools"))`, then `from sla_lib.builder import …  # noqa: E402`. New tests MUST follow this preamble. |
| Lint | **None invoked.** `Dockerfile.claude:3` mentions `ruff`/`mypy` are in the base image, but no `.ruff.toml` / `[tool.ruff]` / `[tool.mypy]` exists and CI never calls them. | — | New code passes if it follows the surrounding file's conventions: 4-space indent, no trailing whitespace, line lengths ≤100ish (existing files routinely 95-110, no enforcement). Don't bring a linter to a knife fight. |
| Doc rendering | Markdown source-of-truth, **not built into a doc site.** | `site/` is an Astro site that renders only per-template `.md` under `site/src/content/templates/`. `SPEC-WRITING-GUIDE.md` and `templates/_specs/SCHEMA.md` are NOT rendered — they're viewed on GitHub. | New `inside_page` / `aligned_below` / `SpreadImage` catalogue entries just need to be valid GitHub-flavored Markdown. No mkdocs/sphinx round-trip to worry about. |
| Existing constraint conventions | `from __future__ import annotations` + `@dataclass(frozen=True)` subclasses with a `check(...)` method + module-level `def factory_name(...) -> Constraint` factories | `tools/sla_lib/builder/constraints.py:26-462` (entire file) | New `inside_page` / `aligned_below` factories must match this style verbatim. |

---

## 2. Don't Hand-Roll — what's already in the codebase

The planner should reuse, not reinvent:

| Need | Already exists at | Use it for |
|---|---|---|
| Image with offset+scaled inset (the SpreadImage primitive) | `ImageFrame.local_offset_mm: tuple[float, float]` (`tools/sla_lib/builder/primitives.py:770`), `local_scale: tuple[float, float]` (line 769), `scale_type: int` (line 772). Emits LOCALX/LOCALY/LOCALSCX/LOCALSCY (lines 806-807). | Crop one source image into left/right halves — no new primitive needed. |
| Page geometry for `inside_page` math | `Page.width_pt`, `Page.height_pt`, `Page.bleed_mm` (`document.py:108-110`). `mm_to_pt`/`PT_TO_MM` constants (`document.py:56`, used in `brand_constraints.py:241`). | `inside_page` rotation-aware bbox check is plain math (~10 lines), exactly like `_InsideConstraint.check()` (`constraints.py:202-223`) and `_TextOnGreenRule` bbox-overlap math (`brand_constraints.py:282-290`). |
| Predicate-style constraint pattern | `_InsideConstraint` (`constraints.py:198-223`), `_MirroredConstraint` (165-195), `_DistanceConstraint` (318-341). | Template for both `inside_page` and `aligned_below`. Both new constraints share the `_resolve` + `_missing_violation` helper plumbing (`constraints.py:90-108`). |
| `(primitives, doc)` rules that need page metadata | `BrandRule.check(primitives, doc)` signature in `brand_constraints.py:67`; e.g. `_LogoSize3MRule:234-263` uses `doc.pages[0].width_pt`. | **Critical signature gap:** existing `Constraint.check(primitives_by_anname)` (`constraints.py:64`) does NOT receive `doc`, so `inside_page` cannot find a frame's owning page from anname alone. Two clean options for the planner: (a) implement `inside_page` as a `BrandRule` (id `brand:inside_page`, auto-runs in `BRAND_CONSTRAINTS` sweep, already-supported by `meta.yml::brand_overrides`); (b) extend `Constraint.check` to accept an optional `doc` kwarg. **Option (a) is cheaper** — it composes with the existing `--all`-sweep + override mechanism without touching the `Constraint` base class or the `structural_check` dispatch. Use that. |
| Override / skip-with-reason mechanism | `meta.yml::brand_overrides` (`structural_check.py:185-200` + `meta_schema.load_brand_overrides`). | The two known `inside_page` errors (`P9 Spread` Zeitung p10, unnamed image Zeitung p12) become two `brand_overrides` entries with reason `"see issue #16"`, exactly per the issue's acceptance criteria. The mechanism already supports this — no DSL extension needed. |
| Block emission protocol | `dataclass`+`emit() -> Iterable` yielding primitives (`blocks.py:68-…`); blocks are auto-expanded by `Page.add()` (`document.py:124-133`). | `SpreadImage` follows the existing block pattern verbatim — yields two `ImageFrame` instances, one per page, both with `anname="<base> · left"` / `"<base> · right"`. No new infrastructure needed. |
| Geometry libraries | **None.** `grep shapely\|rtree\|kiwisolver\|cassowary\|z3 tools/` returns only docstring banners that say "no constraint solver" (`composites.py:30`, `brand_constraints.py:5`). The codebase explicitly opts out of geometry packages. | New rotation-aware bbox math: plain `import math` + `math.radians/cos/sin`, ≤15 lines. Compute the four corners of the rotated rectangle, take min/max → axis-aligned bbox. Same shape as `blocks.py:710-715` (`DoorHangerCutout` already does this for circle approximation). |

---

## 3. Scribus spread-image idiom — recommendation

**MEDIUM confidence** (forum threads are sparse and dated 2007-2014; SLA-format inspection corroborates the structural conclusion).

GUI users in Scribus place a spread image as **one frame straddling both pages** ([Scribus Forums topic 819](https://forums.scribus.net/index.php?topic=819.0) is the canonical reference). However, in the SLA file format every `PAGEOBJECT` carries a single `OwnPage` integer (`tools/sla_to_dsl.py:364, 399, 1219`) — there is no "spans-multiple-pages" flag. The GUI-straddling frame ends up structurally bound to **one** page and overflows the other, which is exactly the `P9 Spread` bug at `x=210, w=210` on Zeitung print page 10.

The structurally clean idiom — and the one this issue prescribes — is **one image source, split via `ImageFrame.local_offset_mm` into two frames, each owned by its own page**:

```python
# Left page: full-spread image, shifted so only left half shows in the frame.
ImageFrame(x_mm=0, y_mm=0, w_mm=page_w, h_mm=page_h,
           src=src, local_offset_mm=(0, 0),
           local_scale=(scale, scale), scale_type=1,
           anname=f"{base} · left")
# Right page: same image, shifted left by page_w so right half shows.
ImageFrame(x_mm=0, y_mm=0, w_mm=page_w, h_mm=page_h,
           src=src, local_offset_mm=(-page_w, 0),
           local_scale=(scale, scale), scale_type=1,
           anname=f"{base} · right")
```

Both halves render byte-identical to a Scribus GUI-authored straddling frame in the exported PDF, but each is `inside_page`-clean and each survives the SLA round-trip independently. This is exactly what `ImageFrame.local_offset_mm` (already in the codebase, `primitives.py:770`) is for.

**Do NOT recommend** any of: (a) keeping a single straddling frame and special-casing `inside_page`; (b) introducing a `MultiPageFrame` primitive; (c) pre-cropping the source image into two PNGs at build time. The `local_offset_mm` route is dependency-free, round-trip-stable, and matches an existing primitive's documented purpose.

---

## 4. New dependencies — none

No new dependencies are needed or justified.

- `inside_page` rotation math: plain `math.radians/cos/sin` (~10 lines).
- `aligned_below`: two scalar comparisons, follows `_DistanceConstraint` template exactly.
- `SpreadImage` block: emits two existing `ImageFrame` primitives.

The CI install line (`pages.yml:57-58`) installs `Pillow`, `qrcode`, `pyzbar`, `jsonschema` only. Adding to that list would slow CI cold-start and is unwarranted for predicate math.

---

## 5. Confidence summary

| Area | Confidence | Why |
|---|---|---|
| Python 3.13 + unittest + no lint config | **HIGH** | Direct inspection of `Dockerfile.claude`, `.github/workflows/pages.yml`, exhaustive `find` for project-config files, sample test files. |
| `local_offset_mm` is the spread-image substrate | **HIGH** | Direct inspection of `primitives.py:769-807` confirms LOCALX/LOCALY emission. |
| `inside_page` should be a `BrandRule` (not a free-form `Constraint`) | **HIGH** | The free-form `Constraint.check` signature has no access to `doc`/page geometry; `BrandRule.check(primitives, doc)` does. The issue's "auto-runs on every template" requirement maps 1:1 onto the `BRAND_CONSTRAINTS` sweep + `meta.yml::brand_overrides` mechanism that already exists. |
| Scribus spread-image-as-two-frames idiom | **MEDIUM** | Forum sources are sparse and dated; SLA-format structural argument (single `OwnPage` per PAGEOBJECT) is the dispositive evidence and is **HIGH** on its own. |
| No new deps needed | **HIGH** | Math is ~10 lines; ImageFrame already supports the offset model. |

## Sources

### HIGH confidence (direct codebase inspection)
- `tools/sla_lib/builder/constraints.py` — full constraint-DSL implementation
- `tools/sla_lib/builder/brand_constraints.py` — `BrandRule.check(primitives, doc)` signature, override mechanism
- `tools/sla_lib/builder/primitives.py:764-829` — `ImageFrame.local_offset_mm` / `local_scale` / `scale_type`
- `tools/sla_lib/builder/document.py:106-134` — `Page.width_pt/height_pt/bleed_mm`, `Page.add()` block-expansion
- `tools/sla_lib/builder/structural_check.py:140-200` — orchestrator dispatch + override application
- `tools/sla_lib/tests/test_constraints.py`, `tests/test_brand_constraints.py`, `tests/test_blocks.py` — test pattern (stdlib unittest)
- `.github/workflows/pages.yml:104-147` — CI test invocation, `structural_check --all`
- `Dockerfile.claude:3,13-15` — Python 3.13, ruff/mypy available but unconfigured
- `tools/sla_to_dsl.py:364,399,1219` — `OwnPage` is per-PAGEOBJECT singular

### MEDIUM confidence (web-verified)
- [Page layout: Apply image frame to two pages — Scribus Forums](https://forums.scribus.net/index.php?topic=819.0) — GUI workflow for spread images
- [Moving two page photo spreads within a book — Scribus Forums](https://forums.scribus.net/index.php?topic=2678.0) — community pattern (does not contradict above)
- [Working with image frames — Scribus Wiki](https://wiki.scribus.net/canvas/Working_with_image_frames) — image-frame fundamentals

### LOW confidence
- (none — all claims above are either from the codebase or cross-referenced)
