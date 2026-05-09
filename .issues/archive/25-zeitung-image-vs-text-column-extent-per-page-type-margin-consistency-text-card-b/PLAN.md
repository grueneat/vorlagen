# Plan: Zeitung band-consistency model + per-page-type margin spec + content-vs-decoration

<objective>
Goal: introduce a single `brand:band_consistency` BrandRule + `meta.yml::body_block_margins`
schema field that pins the OUTER STRUCTURE (header band y=20-49, free zone y=49-283,
footer band y=283-297, L/R margins) of every body-pool page in the Zeitung template,
while keeping the FREE ZONE flexible so Bezirksgruppen can shuffle pages freely. Apply
the rule, fix the 6 specific Zeitung drift items (pages 4, 5, 7, 9, 10, 13), pre-apply
skip-overrides on the 7 non-Zeitung templates, regenerate previews, pin the invariants
in tests, and verify pre/post-fix via Codex visual review.

Why it matters: post-#24 the user verified that some Zeitung frames are still
dimensioned incorrectly. The architectural insight (from extended user dialogue,
documented in RESEARCH.md §1) is that Zeitung must be a library of combinable parts,
not a fixed magazine: any LEFT page must be pairable with any RIGHT page. The band
model is the structural invariant that guarantees this combinability while letting
the free zone vary. This rule is the third successor in the alignment iteration chain
(#22 → #23 → #24 → #25).

Scope IN: one new BrandRule + meta.yml schema extension + 7 override pre-applies +
6 atomic geometry fixes in `templates/zeitung-a4-grun/build.py` + invariant tests +
artifact regen + 2-iteration Codex visual review (pre + post).

Scope OUT: re-authoring Zeitung's design; touching V1 templates beyond the override
pre-apply (#19/#20/#21 follow-ups own that); the logo letterbox WARNING from #19 (out
of scope per pitfalls §13); per-template band specs for the other 7 templates
(deferred per the override reason).

Source-of-truth note: per the prompt, RESEARCH.md supersedes ISSUE.md. The 3-rule
model originally proposed in ISSUE.md (`brand:image_within_text_block`,
`brand:document_margins_consistent`, `brand:text_card_size_consistent`) is DISCARDED
and replaced by the unified `brand:band_consistency` rule. Registry bumps 15 → 16
(not 15 → 18 as ISSUE.md says).

No CONTEXT.md exists for this issue — decisions are based on RESEARCH.md (which
already absorbed the user dialogue).
</objective>

<context>
Issue: @.issues/25-zeitung-image-vs-text-column-extent-per-page-type-margin-consistency-text-card-b/ISSUE.md
Research: @.issues/25-zeitung-image-vs-text-column-extent-per-page-type-margin-consistency-text-card-b/RESEARCH.md
Pitfalls: @.issues/25-zeitung-image-vs-text-column-extent-per-page-type-margin-consistency-text-card-b/research/pitfalls.md

The architecture is locked in RESEARCH.md §1-3 (band model + content vs decoration +
single rule), §4 (meta.yml schema extension), §5 (audit wire-in pattern), §6 (override
pre-apply list), §7 (Codex prompt), §8 (invariant tests), §10 (atomic 9-task ordering).
The drift fixes are in §2 (the 6-row table). The pre-fix observed coordinates are in §9.

<interfaces>
<!-- Executor: use these contracts directly. Do not explore the codebase for them. -->

From tools/sla_lib/builder/brand_constraints.py:
class BrandRule (frozen dataclass): id, name, description, severity="error";
    def check(self, primitives: list, doc, constraints=None) -> list[Violation]
class Violation: severity, rule_id, message, targets (tuple)
SIDE_RX = re.compile(r"\b(links|rechts)\b", re.IGNORECASE)
PT_TO_MM constant for unit conversion
BRAND_CONSTRAINTS: list[BrandRule] = [...]   # registry, currently 15 rules at line 1302
# Existing rule to mirror for anchor-skip pattern: _BleedCoverageRule (line 595)

From tools/sla_lib/builder/bbox.py:
def frame_bbox_mm(item, page) -> Optional[tuple[float, float, float, float]]
    # Page-local mm (x0, y0, x1, y1). None if no spatial extent.

From tools/sla_lib/builder/document.py:
@dataclass class Page:
    width_pt: float; height_pt: float; bleed_mm: float
    items: list; is_master: bool; master_name: str; own_page: int
class Document:
    pages: list[Page]; masters: list[Page]; facing_pages: bool
    template_id: str   # used by load_band_spec to find meta.yml

From tools/sla_lib/builder/primitives.py:
class _Frame: x_mm, y_mm, w_mm, h_mm, anchor, rotation_deg, anname, layer
class TextFrame(_Frame): style, fcolor, font, runs, ...
class ImageFrame(_Frame):
    src, image, fill, scale_type, ratio, local_scale, local_offset_mm,
    inline_image_data, inline_image_ext
class Polygon(_Frame): fill, line_color, line_width_pt, ...

From tools/sla_lib/builder/meta_schema.py (TO BE EXTENDED in T01):
def load_brand_overrides(slug: str, root: Path | None = None) -> set[str]
def _meta_path(slug, root) -> Path     # internal helper
# JSON-Schema validation pattern uses jsonschema.validate (already imported)

From tools/audit_alignment.py (the wire-in target):
@dataclass class PageAuditReport:
    # ... fields including image_extent_warnings at line 83 ...
def _audit_doc(doc, ..., check_image_extent=True) -> TemplateAuditReport
    # Pattern at lines 186-215 (ImageFillsFrame) — mirror for band rule
    # Per-page distribute pattern at lines 303-323 (anname + <unnamed y=...> fallback)
def _report_has_findings(rep) -> bool   # at line 494; controls --strict exit code
def report_to_markdown(rep) -> str      # at line 384; per-page sections at 416+
# CLI flags: --strict, --check-image-extent, --no-check-image-extent (mirror for band)

</interfaces>

Key files (executor reads as needed):
@tools/sla_lib/builder/brand_constraints.py — add `_BandConsistencyRule` after `_ImageFillsFrameRule`
@tools/sla_lib/builder/meta_schema.py — add `_BAND_SPEC_SCHEMA` + `load_band_spec`
@tools/sla_lib/tests/test_brand_constraints.py — `RegistryTests` at line 54 bumps 15 → 16
@tools/sla_lib/tests/test_brand_band_consistency.py — NEW (T01 unit tests)
@tools/audit_alignment.py — wire rule into `_audit_doc` (T02)
@tools/sla_lib/tests/test_audit_alignment.py — extend (T02)
@templates/zeitung-a4-grun/meta.yml — add `body_block_margins` block (T04)
@templates/zeitung-a4-grun/build.py — apply 6 drift fixes (T06)
@tools/sla_lib/tests/test_zeitung_geometry.py — add `BandConsistencyInvariantTests` (T08)
@prompts/zeitung-band-consistency-audit.md — NEW (T05)
@reviews/codex-zeitung-band-iter1.md — NEW Codex pre-fix output (T05)
@reviews/codex-zeitung-band-iter2.md — NEW Codex post-fix output (T09)
@.issues/25-…/EXECUTION.md — NEW (T09)

7 override pre-apply targets (T03):
@templates/infostand-tent-card-a5-quer/meta.yml
@templates/kandidat-falzflyer-din-lang/meta.yml
@templates/plakat-a1-hochformat/meta.yml
@templates/postkarte-a6-kampagne/meta.yml
@templates/themen-plakat-a3-quer/meta.yml
@templates/wahlaufruf-postkarte-a6-quer/meta.yml
@templates/wahltag-tueranhaenger/meta.yml
</context>

<commit_format>
Format: conventional with numeric-id prefix (per `.issues/config.yaml` and recent main history).
Pattern: `25: <type>(<scope>): <subject>`
Example (from main): `24: Zeitung remaining alignment — INJECT_MAP drift fix + brand:image_fills_frame rule`
Types in this PR: feat, chore, test, docs.
Scopes used: brand, audit, meta, zeitung, reviews.
NO "claude" / "co-authored-by Claude" / AI-attribution anywhere — strict user policy.
</commit_format>

<tasks>

<task type="auto" id="T01">
  <name>T01: feat(brand) — add brand:band_consistency rule + meta_schema.load_band_spec</name>
  <files>tools/sla_lib/builder/brand_constraints.py, tools/sla_lib/builder/meta_schema.py, tools/sla_lib/tests/test_brand_band_consistency.py, tools/sla_lib/tests/test_brand_constraints.py</files>
  <action>
  Implement the unified band-consistency rule + the new meta.yml field loader. Atomic
  commit: rule code + schema loader + unit tests + registry-count bump all together.

  1. tools/sla_lib/builder/meta_schema.py — add `_BAND_SPEC_SCHEMA` and
     `load_band_spec(slug, root=None) -> dict | None` per the EXACT JSON-Schema
     and function body in RESEARCH.md §4 (the "Schema in tools/sla_lib/builder/meta_schema.py"
     code block). Mirror `load_brand_overrides`'s style: parse YAML, validate with
     `jsonschema.validate`, raise `ValueError` with `meta.yml at {p} body_block_margins
     malformed: ...` on schema violation. Return None when the field is absent
     (opt-out semantics — templates without the field skip the rule cleanly).

  2. tools/sla_lib/builder/brand_constraints.py — add `_BandConsistencyRule`
     class + `_is_background_decoration` helper per the EXACT skeleton in RESEARCH.md §3
     (the "Rule semantics" code block). Place the class definition AFTER
     `_ImageFillsFrameRule` (existing line ~1049 onward block) and BEFORE
     `_make_rule` (~line 1298). Then append a single entry to the `BRAND_CONSTRAINTS`
     list literal (~line 1302):

         _make_rule(_BandConsistencyRule,
                    id="brand:band_consistency",
                    name="Body-pool pages confine content to header/free/footer "
                         "bands and L/R margins (Issue #25)",
                    description=(
                        "Content frames (text + content-bearing image) must stay "
                        "inside the bands and margins declared in "
                        "meta.yml::body_block_margins. Background decoration "
                        "(solid-fill polygons, image-less brand-color frames) "
                        "is exempt. Pages listed in excluded_pages are exempt. "
                        "Templates without body_block_margins are skipped."
                    )),

     Anchor-positioned skip: the rule MUST skip frames where
     `getattr(item, "is_anchor_positioned", False)` (mirror `_BleedCoverageRule`'s
     anchor skip pattern at ~line 621). This prevents false positives on inline
     icons / logos / wahlkreuz markers anchored to text runs.

     Severity: ERROR for both band-intrusion and margin-drift (per RESEARCH.md §12 #3).

     Tolerance: 0.5 mm default (matches existing rule conventions).

  3. tools/sla_lib/tests/test_brand_band_consistency.py — NEW. Unit tests
     using synthetic mini-Documents (no real templates). Cover at minimum:
     - rule emits 0 violations when `template_id=""` or `load_band_spec` returns None
     - rule emits 0 violations when the page is in `excluded_pages`
     - rule emits ERROR when a TextFrame y_top &lt; header_y_bot on a body page
       (e.g., y_top=37 simulating Zeitung page 7 drift)
     - rule emits ERROR when an ImageFrame y_bottom &gt; footer_y_top on a body page
       (e.g., y_bottom=297 simulating Zeitung page 5 P4 Foto-Spread)
     - rule emits ERROR when a content frame x_min &lt; outer margin (LEFT page)
     - rule emits ERROR when a content frame x_max exceeds the inner-margin boundary
       on a LEFT page (right edge of LEFT page = page_w - inner_mm)
     - rule emits 0 violations for a Polygon with `fill="Dunkelgrün"` extending
       full-bleed (background decoration exempt)
     - rule emits 0 violations for an image-less ImageFrame with brand-color fill
       extending full-bleed
     - rule emits 0 violations for a content ImageFrame entirely inside the free zone
     - rule emits 0 violations on `is_master=True` pages
     - rule emits 0 violations when `master_name` doesn't match SIDE_RX (silent skip
       per spec; spine_safety covers unknown sides separately)
     - rule respects `is_anchor_positioned=True` skip on frames

     Use the existing test patterns in `test_brand_constraints.py` for synthetic
     `Document` / `Page` / `TextFrame` / `ImageFrame` / `Polygon` construction. Set
     `doc.template_id` and provide a synthetic spec via patching `load_band_spec`
     (preferred — `unittest.mock.patch`) OR by writing a tiny `meta.yml` to a temp
     dir and pointing the loader at it.

  4. tools/sla_lib/tests/test_brand_constraints.py — `RegistryTests` at line 54:
     - `test_fifteen_rules_exact`: rename to `test_sixteen_rules_exact`,
       update assertion `assertEqual(len(BRAND_CONSTRAINTS), 16)`, update the comment
       block to mention "+ #25 band_consistency (the 16th, unified body-pool model)".
     - `test_ids_are_canonical`: add `"brand:band_consistency",   # Issue #25` to the
       expected set.

  Verify locally before commit: `python3 -m unittest discover tools/sla_lib/tests`
  exits 0. `python3 -m sla_lib.builder.structural_check --all` exits 0 (it should —
  templates without `body_block_margins` are silently skipped, the rule is dormant
  until T03 + T04 land).

  Commit message:
      25: feat(brand): add brand:band_consistency rule + body_block_margins schema

      Unified band-consistency model replacing the originally-proposed three-rule
      design. One rule asserts content frames stay inside header (y=20-49) /
      free / footer (y=283-297) bands and L/R margins per a new
      meta.yml::body_block_margins spec. Background decoration (solid-fill
      polygons, image-less brand-color frames) and excluded_pages are exempt.
      Templates without the spec are silently skipped.

      Registry 15 → 16. Unit tests cover band-intrusion, margin-drift,
      decoration exemption, master/excluded-page skips, anchor-positioned skip.
  </action>
  <verify>
  <automated>python3 -m unittest discover tools/sla_lib/tests &amp;&amp; python3 -m sla_lib.builder.structural_check --all</automated>
  </verify>
  <done>
  - `_BandConsistencyRule` class defined per RESEARCH.md §3 skeleton
  - `_is_background_decoration` helper handles Polygon-with-brand-fill AND image-less ImageFrame
  - Anchor-positioned skip implemented (mirrors `_BleedCoverageRule`)
  - `BRAND_CONSTRAINTS` registry has 16 entries; new id is `brand:band_consistency`
  - `_BAND_SPEC_SCHEMA` defined; `load_band_spec` returns dict | None; raises ValueError on schema violation
  - NEW `test_brand_band_consistency.py` covers ≥10 cases listed in `<action>`
  - `RegistryTests.test_fifteen_rules_exact` renamed; assertion bumped to 16; expected-id set updated
  - `python3 -m unittest discover tools/sla_lib/tests` exit 0
  - `python3 -m sla_lib.builder.structural_check --all` exit 0
  </done>
</task>

<task type="auto" id="T02">
  <name>T02: feat(audit) — wire brand:band_consistency into audit_alignment</name>
  <files>tools/audit_alignment.py, tools/sla_lib/tests/test_audit_alignment.py</files>
  <action>
  Wire the new rule into `bin/audit-alignment` so its findings flow through the
  same JSON / Markdown / `--strict` plumbing as `brand:spine_safety` and
  `brand:image_fills_frame`. Mirror the existing pattern at lines 186-215 for
  `_ImageFillsFrameRule`.

  1. tools/audit_alignment.py:

     a) `PageAuditReport` dataclass (lines 75-83): add a new field AFTER
        `image_extent_warnings` (preserve existing field order):

            band_consistency_warnings: list = field(default_factory=list)  # Issue #25

     b) `_audit_doc` signature: add a new keyword `check_brand_rules: bool = True`
        after `check_image_extent`. (Per RESEARCH.md §5 the gate name is
        `check_brand_rules`.)

     c) Inside `_audit_doc`, AFTER the `_ImageFillsFrameRule` block (~line 215),
        add the band-consistency block per RESEARCH.md §5:

            # Issue #25: band consistency (replaces 3 originally-planned rules)
            band_by_target: dict = {}
            if check_brand_rules:
                from sla_lib.builder.brand_constraints import _BandConsistencyRule
                rule = _BandConsistencyRule(
                    id="brand:band_consistency", name="", description="")
                for v in rule.check(
                    list(doc.iter_all_primitives()),
                    doc, constraints=constraints,
                ):
                    for t in v.targets:
                        band_by_target.setdefault(t, []).append(
                            f"[{v.severity.upper()}] {v.message}"
                        )

     d) Inside the per-page distribution loop (~lines 303-323, where
        `image_extent_warnings` is populated), MIRROR the same anname-or-anonymous-key
        attach pattern for `band_consistency_warnings`. Use both the named lookup
        AND the `<unnamed y=...>` / `<unnamed x=...>` fallback (the rule emits both
        shapes per its skeleton — band-intrusion uses y=, margin-drift uses x=).

     e) `_report_has_findings(rep)` (~line 494): add `pr.band_consistency_warnings`
        to the OR-chain so `--strict` exits 1 when band findings are present.

     f) `report_to_markdown(rep)` (~line 384, per-page section starting line 416):
        AFTER the `pr.image_extent_warnings` section, add:

            if pr.band_consistency_warnings:
                lines.append(
                    f"### Band consistency ({len(pr.band_consistency_warnings)})"
                )
                for w in pr.band_consistency_warnings:
                    lines.append(f"  - {w}")

     g) CLI flags (~lines 537-545): add `--check-brand-rules` /
        `--no-check-brand-rules` flag pair mirroring `--check-image-extent` /
        `--no-check-image-extent`. Wire into `audit_doc` / `audit_all` calls
        via `ns.check_brand_rules`. Default: True. Help text:
        `"Run brand:band_consistency check (Issue #25, default on)."`

     h) JSON output: `band_consistency_warnings` flows through automatically if the
        serializer dumps the dataclass via `dataclasses.asdict`. If there's an
        explicit field allowlist, extend it. Search for `image_extent_warnings`
        — wherever it appears in JSON-output code paths, `band_consistency_warnings`
        MUST appear in parallel.

  2. tools/sla_lib/tests/test_audit_alignment.py — extend with:

     a) Test that `PageAuditReport` has the new field (`hasattr` check).
     b) Test that `_audit_doc` on a synthetic doc with band drift emits a finding
        in `band_consistency_warnings` of the corresponding page.
     c) Test that `_report_has_findings` returns True when only
        `band_consistency_warnings` is populated.
     d) Test that the `--no-check-brand-rules` path produces empty
        `band_consistency_warnings` (rule disabled).
     e) Test that the Markdown formatter emits a "Band consistency" section
        when warnings exist.

  Verify locally: `python3 -m unittest discover tools/sla_lib/tests` exit 0.
  `bin/audit-alignment zeitung-a4-grun --strict` still exits 0 (Zeitung has no
  body_block_margins yet — rule is dormant).

  Commit message:
      25: feat(audit): wire brand:band_consistency into audit_alignment

      Mirrors the existing brand:spine_safety / brand:image_fills_frame
      wire-in pattern. Adds PageAuditReport.band_consistency_warnings field,
      per-page distribution by anname / anonymous-key, --strict gating,
      Markdown "Band consistency" section, --check-brand-rules CLI flag pair.
      Rule remains dormant for templates without meta.yml::body_block_margins.
  </action>
  <verify>
  <automated>python3 -m unittest discover tools/sla_lib/tests &amp;&amp; bin/audit-alignment zeitung-a4-grun --strict &amp;&amp; bin/audit-alignment --all --strict</automated>
  </verify>
  <done>
  - `PageAuditReport.band_consistency_warnings` field added (default factory list)
  - `_audit_doc` instantiates `_BandConsistencyRule` and populates `band_by_target` when `check_brand_rules=True`
  - Per-page loop attaches band warnings via anname AND `<unnamed y=...>` / `<unnamed x=...>` fallback
  - `_report_has_findings` returns True for non-empty `band_consistency_warnings`
  - Markdown formatter emits a "Band consistency" section per page
  - CLI `--check-brand-rules` / `--no-check-brand-rules` flags exist; default True
  - JSON output includes `band_consistency_warnings` per page
  - Tests (a)-(e) added; all pass
  - `python3 -m unittest discover tools/sla_lib/tests` exit 0
  - `bin/audit-alignment --all --strict` exit 0 (rule still dormant — no spec on any template)
  </done>
</task>

<task type="auto" id="T03">
  <name>T03: chore(meta) — pre-apply brand:band_consistency override on 7 non-Zeitung templates</name>
  <files>templates/infostand-tent-card-a5-quer/meta.yml, templates/kandidat-falzflyer-din-lang/meta.yml, templates/plakat-a1-hochformat/meta.yml, templates/postkarte-a6-kampagne/meta.yml, templates/themen-plakat-a3-quer/meta.yml, templates/wahlaufruf-postkarte-a6-quer/meta.yml, templates/wahltag-tueranhaenger/meta.yml</files>
  <action>
  Append a `brand:band_consistency` skip override to each of the 7 non-Zeitung
  templates' `meta.yml::brand_overrides` list. This MUST land BEFORE T04 so
  `--all` stays green when Zeitung gets the spec.

  These 7 templates are all `facing_pages=False` single-page templates. None has
  a body-pool / spine model yet. The override is conservative: the rule auto-skips
  templates without `body_block_margins` (T01's loader returns None), so technically
  the override is redundant — but per RESEARCH.md §6 it's mandated for explicit
  documentation that the band model is "scheduled for follow-up audit per #25"
  rather than implicitly bypassed. Future per-template band-spec authoring removes
  the override at that point.

  For EACH of the 7 meta.yml files:
  - Locate the existing `brand_overrides:` list (every template already has one
    from prior issues; check by reading the file first).
  - Append a new entry with EXACTLY this shape (preserve YAML 2-space indent,
    use the literal-block-scalar `>-` for the reason to match existing entries):

        - id: brand:band_consistency
          reason: >-
            Scheduled for follow-up audit per #25 — band-consistency check
            added in #25 needs per-template body_block_margins spec authoring;
            deferred to follow-up issue. Zeitung is the only template with
            verified body-pool band model post-#25.

  - Do NOT reorder existing entries. Append only.
  - Do NOT touch any other section of the meta.yml.

  Verify: `python3 -m sla_lib.builder.structural_check --all` exit 0.
  `bin/audit-alignment --all --strict` exit 0.

  Commit message:
      25: chore(meta): pre-apply brand:band_consistency override on 7 templates

      infostand-tent-card-a5-quer, kandidat-falzflyer-din-lang,
      plakat-a1-hochformat, postkarte-a6-kampagne, themen-plakat-a3-quer,
      wahlaufruf-postkarte-a6-quer, wahltag-tueranhaenger get a skip override
      with reason "scheduled for follow-up audit per #25". Mirrors the #24 T03
      pre-apply pattern. Keeps --all green when Zeitung's body_block_margins
      spec lands in T04.
  </action>
  <verify>
  <automated>python3 -m sla_lib.builder.structural_check --all &amp;&amp; bin/audit-alignment --all --strict</automated>
  </verify>
  <done>
  - All 7 meta.yml files have a new `brand_overrides` entry with `id: brand:band_consistency`
  - Each entry's `reason` matches the RESEARCH.md §6 reason text exactly (`>-` block scalar)
  - No existing entries reordered or modified
  - `python3 -m sla_lib.builder.structural_check --all` exit 0
  - `bin/audit-alignment --all --strict` exit 0
  - Single atomic commit (all 7 files in one commit)
  </done>
</task>

<task type="auto" id="T04">
  <name>T04: chore(zeitung) — add body_block_margins spec to meta.yml (RED window opens)</name>
  <files>templates/zeitung-a4-grun/meta.yml</files>
  <action>
  Add the `body_block_margins` block to Zeitung's meta.yml. THIS IS AN INTENTIONAL
  RED COMMIT: after this commit, `structural_check zeitung-a4-grun` exits 1 because
  the rule fires on the 6 drift items (pages 4, 5, 7, 9, 10, 13). The window closes
  in T06 when the geometry fixes land.

  1. Add the EXACT block from RESEARCH.md §4 ("Zeitung's `meta.yml` addition")
     to `templates/zeitung-a4-grun/meta.yml`:

         body_block_margins:
           bands:
             header: {y_top_mm: 20.0, y_bottom_mm: 49.0}
             footer: {y_top_mm: 283.0, y_bottom_mm: 297.0}
           margins:
             left:  {outer_mm: 20.0, inner_mm: 20.0}
             right: {outer_mm: 20.0, inner_mm: 20.0}
           background_decoration:
             fills: [Dunkelgrün, Hellgrün, Magenta, Gelb, White]
           excluded_pages: [1, 2, 10, 11, 14]

     Place it as a top-level key. Recommended location: after `brand_overrides`,
     before `previews_for_sla`. Preserve any existing comment style.

     Page-numbering convention: 1-indexed for users (page 1 = cover). The rule
     converts internally (`page.own_page + 1`).

     `excluded_pages: [1, 2, 10, 11, 14]` — feature pages per RESEARCH.md §1
     ("Excluded feature pages"):
     - 1 = cover (Cover Hero full-bleed)
     - 2 = P1 Hero feature page
     - 10, 11 = P9 Spread halves (full-bleed spread photo)
     - 14 = back cover / colophon feature

     Do NOT add Dunkelgrün-bg pages (12, 13) to `excluded_pages` — those are
     body-pool pages whose Dunkelgrün polygon is decoration, exempt by
     `_is_background_decoration` matching brand-color fills, not by exclusion.

  2. VERIFY the RED window is now open and the right ERRORs surface:

         python3 -m sla_lib.builder.structural_check zeitung-a4-grun

     Expected: exit 1. Document in the commit body which pages surface ERRORs.
     Per RESEARCH.md §3 + §9 observed coordinates expected pages:
     - Page 4: body block X drift (col-3 truncated)
     - Page 5: P4 Foto-Spread y_bottom=297 > footer band top=283
     - Page 7: body text frames y_top=37 < header band bottom=49
     - Page 9: same as page 7
     - Page 10: body block X drift (currently EXCLUDED — should NOT appear; if it
       does, page 10's status as feature is wrong; resolve in T06 open question #2)
     - Page 13: same as page 7

     If the actual list differs, capture the actual ERROR list verbatim in the
     commit message — it becomes the spec the T05 Codex audit cross-checks against.

     Run `bin/audit-alignment zeitung-a4-grun --strict`. Expected: exit 1. Capture
     stdout to a temp file for use in T05.

     `bin/audit-alignment --all --strict` should ALSO exit 1 (only Zeitung has the
     spec; the 7 from T03 are skipped via override). Verify only Zeitung's report
     has band_consistency_warnings.

  3. Do NOT fix any geometry yet. This task is intentionally a RED commit.

  Commit message:
      25: chore(zeitung): add body_block_margins spec — RED window opens

      Adds the band-consistency spec to Zeitung's meta.yml: header band y=20-49,
      footer band y=283-297, L/R margins 20mm, background decoration fills
      include Dunkelgrün/Hellgrün/Magenta/Gelb/White, excluded_pages=[1,2,10,11,14]
      for cover + P1 Hero + P9 Spread halves + back.

      INTENTIONAL: bin/audit-alignment zeitung-a4-grun --strict now exits 1.
      Pre-fix ERRORs surfaced on pages: <list verbatim from running the audit>.
      Window closes in T06 once the 6 drift fixes land. Mirrors the #24
      RED-window approach.
  </action>
  <verify>
  <automated>! python3 -m sla_lib.builder.structural_check zeitung-a4-grun &amp;&amp; ! bin/audit-alignment zeitung-a4-grun --strict &amp;&amp; bin/audit-alignment zeitung-a4-grun --json | python3 -c "import json,sys; d=json.load(sys.stdin); pages=[p['page_idx']+1 for p in d['pages'] if p.get('band_consistency_warnings')]; print('band findings on pages:', pages); assert pages, 'expected RED window'"</automated>
  </verify>
  <done>
  - `templates/zeitung-a4-grun/meta.yml` has the `body_block_margins` block exactly per RESEARCH.md §4
  - `excluded_pages: [1, 2, 10, 11, 14]` (1-indexed)
  - `python3 -m sla_lib.builder.structural_check zeitung-a4-grun` EXITS 1 (intentional RED)
  - `bin/audit-alignment zeitung-a4-grun --strict` EXITS 1 (intentional RED)
  - `bin/audit-alignment zeitung-a4-grun --json` shows `band_consistency_warnings` populated on at minimum pages 4, 5, 7, 9, 13
  - The 7 non-Zeitung templates remain green (override applied in T03)
  - Commit body lists the ACTUAL pre-fix ERROR pages verbatim (so T05 Codex output has a spec to cross-check)
  </done>
</task>

<task type="auto" id="T05">
  <name>T05: docs(reviews) — Codex visual audit pre-fix baseline (verification gate iter1)</name>
  <files>prompts/zeitung-band-consistency-audit.md, reviews/codex-zeitung-band-iter1.md</files>
  <action>
  Run Codex visual review against the current (pre-fix) Zeitung previews to produce
  an independent baseline of band-consistency drift. Cross-check Codex findings
  against the audit-tool JSON output. If Codex finds something the audit-tool
  misses, STOP-and-iterate: either strengthen the rule (loop back to T01) or
  document the gap and proceed.

  1. Create `prompts/zeitung-band-consistency-audit.md` with the EXACT prompt
     skeleton from RESEARCH.md §7 (the markdown code block starting "# Zeitung A4 —
     band-consistency visual audit"). Include verbatim:
     - The band definitions (header y=20-49, footer y=283-297, margins 20mm)
     - The background-decoration carve-out (Dunkelgrün/Hellgrün polygons can extend
       past bands)
     - The feature-page exclusion list (1, 2, 10, 11, 14)
     - The body-pool page list (3, 4, 5, 6, 7, 8, 9, 12, 13)
     - The structured `<verdict value="pass|fail" body_pool_findings=N
       spread_baseline_findings=N>` block at the end
     - Reference to "Issue #25"

     Critical: tell Codex EXPLICITLY not to re-list classes from #23 (alignment) or
     #24 (INJECT_MAP / letterbox / scale_type) — pitfalls §5 warns this is a noise
     vector. Add: "Do NOT report letterboxing, full-bleed gap, scale_type mismatch,
     or INJECT_MAP issues — these are resolved in prior issues."

  2. Run Codex using the project's standard codex-CLI invocation pattern (mirror
     #24's invocation — see `reviews/codex-zeitung-all-pages-iter2.md` for the
     precedent format). The prompt feeds the rendered
     `templates/zeitung-a4-grun/page-{01..14}.png` PNGs to Codex for visual
     inspection.

     Save Codex's output verbatim to `reviews/codex-zeitung-band-iter1.md`. Include:
     - Date/time of run
     - Codex CLI version (`codex --version`)
     - The prompt file used
     - Codex's full response including the verdict block

  3. Cross-check vs audit-tool JSON:

         bin/audit-alignment zeitung-a4-grun --json > /tmp/audit-25-iter1.json

     For each page Codex flags, verify the audit JSON also has a corresponding
     `band_consistency_warnings` entry on that page. For each page the audit
     flags, verify Codex either flagged it OR it's a coordinate-precision-only
     finding humans wouldn't see (margin drift &lt; 1mm).

     Append to `reviews/codex-zeitung-band-iter1.md` a "Cross-check" section
     listing:
     - Pages flagged by BOTH Codex and audit-tool (expected: 4, 5, 7, 9, 13;
       page 10 if it surfaces)
     - Pages flagged ONLY by Codex (gap: rule is missing something — STOP)
     - Pages flagged ONLY by audit-tool (acceptable: machine-precision only)

  4. STOP-and-iterate condition: if Codex flags a page or finding class that
     `_BandConsistencyRule` does NOT catch, you must EITHER:
     - (preferred) Loop back to T01 to extend the rule, then re-run T01-T05.
     - OR document the gap explicitly in `reviews/codex-zeitung-band-iter1.md`
       under a "Deferred" section and proceed (the gap becomes a #26 candidate).
     Do NOT silently proceed to T06 with a known rule gap.

  5. Commit both files atomically. The artifacts are in-tree per
     `.issues/config.yaml::commit_artifacts: true`.

  Commit message:
      25: docs(reviews): Codex band-consistency audit iter1 (pre-fix baseline)

      NEW prompt prompts/zeitung-band-consistency-audit.md scoped tightly to
      the band-model bug class (header/footer/margin extents, decoration carve-
      out, feature-page exclusion list). Codex verdict: <pass|fail> with N
      body-pool findings. Cross-checked against bin/audit-alignment JSON;
      <gap status>. Drives the geometry fix list for T06.
  </action>
  <verify>
  <automated>test -f prompts/zeitung-band-consistency-audit.md &amp;&amp; test -f reviews/codex-zeitung-band-iter1.md &amp;&amp; grep -q "verdict" reviews/codex-zeitung-band-iter1.md &amp;&amp; grep -qi "cross-check" reviews/codex-zeitung-band-iter1.md</automated>
  </verify>
  <done>
  - NEW `prompts/zeitung-band-consistency-audit.md` matches RESEARCH.md §7 skeleton verbatim
  - Prompt includes the explicit "Do NOT re-report #23/#24 classes" sentence (per pitfalls §5)
  - NEW `reviews/codex-zeitung-band-iter1.md` contains: date/time, Codex CLI version, prompt path, full Codex output with `<verdict>` block, "Cross-check" section
  - Cross-check section enumerates which pages BOTH/CODEX-ONLY/AUDIT-ONLY surfaced
  - If a Codex-only gap exists, either (a) T01 was reopened OR (b) a "Deferred to #26" subsection documents it
  - Single atomic commit with both files
  </done>
</task>

<task type="auto" id="T06">
  <name>T06: chore(zeitung) — apply 6 geometry fixes (RED window closes)</name>
  <files>templates/zeitung-a4-grun/build.py</files>
  <action>
  Apply the 6 specific drift fixes per RESEARCH.md §2 table in a SINGLE atomic
  commit. After this commit `structural_check zeitung-a4-grun` returns to exit 0
  and the RED window from T04 closes.

  Page numbering convention: 1-indexed (matches RESEARCH.md). build.py uses
  0-indexed `page0..page13` variables (see lines 96-226). Page N (1-indexed) ==
  `page<N-1>` variable. So page 4 == page3, page 5 == page4, etc.

  The 6 fixes per RESEARCH.md §2:

  | # | Page (1-idx) | Variable | Drift | Fix |
  |---|-------------|---------|-------|-----|
  | 1 | 4 | page3 | Body-block X off-center: col-3 truncated h=39 mm | RESOLVE OPEN QUESTION (see step 1 below) |
  | 2 | 5 | page4 | P4 Foto-Spread y_bottom=297 intrudes into footer band | Crop photo to y_bottom=283; i.e. set h_mm so y_mm + h_mm == 283 |
  | 3 | 7 | page6 | Body content y_top=37 intrudes into header band | Move all body frames down to y >= 49 |
  | 4 | 9 | page8 | Body content y_top=37 (same as page 7) | Same: move body frames to y >= 49 |
  | 5 | 10 | page9 | Body-block X drift; detector saw block at x=135-185 | RESOLVE OPEN QUESTION (see step 5 below) |
  | 6 | 13 | page12 | Body content y_top=37 (same as 7, 9) | Move body frames to y >= 49 |

  Step-by-step:

  1. **Page 4 (page3) — open question #1 resolution.** Read `templates/zeitung-a4-grun/build.py`
     for all `page3.add(...)` calls. Identify the col-3 frame (likely a TextFrame at
     x≈135, w≈55, h≈39). Two options per RESEARCH.md §12 #1:
     (a) RESTORE col-3 to full height (h_mm ≈ 100mm to match cols 1+2). Choose this
         if visual review shows the page intends a 3-column body grid.
     (b) DECLARE 2-column variant: leave col-3 short OR remove it; rebalance the body
         content so the detected block extent reflects the actual 2-col layout.
     Look at the rendered `templates/zeitung-a4-grun/page-04.png` and the Codex iter1
     output (T05) to decide. Document the choice in the commit message.
     The band-consistency rule passes either way (content stays in free zone) — the
     decision is visual/design.

  2. **Page 5 (page4) — P4 Foto-Spread crop.** Locate the `page4.add(ImageFrame(...))`
     call with `anname="P4 Foto-Spread"` (or the equivalent). Current y_mm + h_mm
     reaches y=297. Reduce h_mm so y_mm + h_mm == 283. If the image was previously
     y_mm=189 h_mm=108, new h_mm=94 (189+94=283).

  3. **Page 7 (page6) — body frames y_top=37 → y_top=49.** Find every body
     frame on page6 currently at y_mm=37 (TextFrames + any ImageFrames in the body
     grid; do NOT touch the header breadcrumb at y=20-49 or the footer at y=283-297).
     Increment y_mm by 12 (37 → 49) AND reduce h_mm by 12 (so y_bottom is unchanged).
     Verify the body bottom y stays ≤ 283. If existing h_mm doesn't allow the 12mm
     shrink (rare), confirm via probe and either crop content or note as open issue.

  4. **Page 9 (page8) — same as page 7.** Same body-block y shift on page8.

  5. **Page 10 (page9) — open question #2 resolution.** Read `page9.add(...)` calls.
     Page 10 is currently in `excluded_pages: [1, 2, 10, 11, 14]` (T04). RESEARCH.md
     §12 #2 + the prompt say: confirm feature-page exclusion is correct and skip if so.
     CHECK: read the page9 declarations and ask "is page 10 a P9 Spread half (feature)
     or a body-pool page with content past the spread?" The pre-fix probe in
     RESEARCH.md §9 saw block at x=135-185 — that's a single column at x=135, which
     suggests page 10 has post-spread body content (not pure feature). Two paths:
     - If page 10 is purely the lower half of a P9 spread photo: leave it in
       `excluded_pages` (no fix). Document this conclusion.
     - If page 10 has body content under the spread photo: REMOVE 10 from
       `excluded_pages` in `meta.yml` (back to T04's spec, edited here in T06)
       AND fix the body-block X drift (likely add the missing 2 columns or restore
       a 3-column layout). The band-consistency rule will then validate.
     Either way: document the choice in the commit message. If you remove 10 from
     `excluded_pages`, this task touches BOTH `build.py` AND `meta.yml`.

  6. **Page 13 (page12) — same as page 7.** Same body-block y shift on page12.

  Cross-rule interaction (per pitfalls §12): when shrinking/moving image frames,
  re-run `bin/audit-alignment zeitung-a4-grun --strict` after each sub-fix to
  catch newly-created `brand:image_text_overlap` ERRORs. If a new overlap surfaces,
  fix it inline (typically by also shrinking the adjacent text frame's h_mm; see
  precedent in zeitung meta.yml for `Kopie von u2d5c (13)`). Do NOT ship a commit
  that closes one ERROR while opening another.

  Verify after all 6 fixes:
  - `python3 -m sla_lib.builder.structural_check zeitung-a4-grun` exit 0
  - `bin/audit-alignment zeitung-a4-grun --strict` exit 0
  - `python3 -m sla_lib.builder.structural_check --all` exit 0
  - `python3 -m unittest discover tools/sla_lib/tests` exit 0 (existing tests
    still pass — invariant tests come in T08)

  Commit message:
      25: chore(zeitung): apply 6 band-consistency drift fixes — RED closes

      Pages 4, 5, 7, 9, 10, 13 per RESEARCH.md §2 table:
      - Page 4 (page3): col-3 <restored to full height | declared 2-col variant>
      - Page 5 (page4): P4 Foto-Spread cropped y_bottom 297 → 283
      - Page 7 (page6): body frames shifted y_top 37 → 49 (height -12)
      - Page 9 (page8): same body shift as page 7
      - Page 10 (page9): <feature exclusion confirmed | body content fixed>
      - Page 13 (page12): same body shift as page 7

      bin/audit-alignment zeitung-a4-grun --strict now exits 0. RED window
      from T04 closes. Renderable artifacts (template.sla, PNGs) regenerated
      in T07. Open questions §12 #1 and #2 resolved per commit body above.
  </action>
  <verify>
  <automated>python3 -m sla_lib.builder.structural_check zeitung-a4-grun &amp;&amp; bin/audit-alignment zeitung-a4-grun --strict &amp;&amp; python3 -m sla_lib.builder.structural_check --all &amp;&amp; python3 -m unittest discover tools/sla_lib/tests</automated>
  </verify>
  <done>
  - All 6 fixes applied per RESEARCH.md §2 table
  - Page 4 col-3 decision documented (restored OR 2-col variant)
  - Page 10 status decision documented (feature stays excluded OR exclusion removed + body fixed)
  - No new `brand:image_text_overlap` ERRORs introduced (verified via audit re-run between sub-fixes)
  - `python3 -m sla_lib.builder.structural_check zeitung-a4-grun` exit 0
  - `bin/audit-alignment zeitung-a4-grun --strict` exit 0
  - `python3 -m sla_lib.builder.structural_check --all` exit 0
  - `python3 -m unittest discover tools/sla_lib/tests` exit 0
  - Single atomic commit (build.py only, OR build.py + meta.yml if page 10's exclusion changed)
  </done>
</task>

<task type="auto" id="T07">
  <name>T07: chore(zeitung) — regenerate template.sla + gallery + meta.yml SHA bump</name>
  <files>templates/zeitung-a4-grun/template.sla, templates/zeitung-a4-grun/template-preview.sla, templates/zeitung-a4-grun/page-01.png, templates/zeitung-a4-grun/page-02.png, templates/zeitung-a4-grun/page-03.png, templates/zeitung-a4-grun/page-04.png, templates/zeitung-a4-grun/page-05.png, templates/zeitung-a4-grun/page-06.png, templates/zeitung-a4-grun/page-07.png, templates/zeitung-a4-grun/page-08.png, templates/zeitung-a4-grun/page-09.png, templates/zeitung-a4-grun/page-10.png, templates/zeitung-a4-grun/page-11.png, templates/zeitung-a4-grun/page-12.png, templates/zeitung-a4-grun/page-13.png, templates/zeitung-a4-grun/page-14.png, templates/zeitung-a4-grun/preview.pdf, templates/zeitung-a4-grun/meta.yml</files>
  <action>
  Regenerate the Zeitung template's SLA + preview SLA + 14 PNGs + preview PDF, and
  bump the `meta.yml::previews_for_sla` SHA so `bin/check-stale-previews` exits 0.

  This is a single, mechanical command-driven task. Per pitfalls §11 the single
  command does all four steps atomically:

      bin/render-gallery zeitung-a4-grun --skip-visual-diff

  This re-renders:
  1. `template.sla` from `build.py` (post-T06 geometry).
  2. `template-preview.sla` (the one with INJECT_MAP populated).
  3. All 14 `page-*.png` previews.
  4. `preview.pdf`.
  5. Updates `meta.yml::previews_for_sla` SHA to the new SHA256 of `template.sla`.

  The `--skip-visual-diff` flag is REQUIRED — without it the pipeline tries to
  compare against the outdated PNG snapshot from the prior SHA and fails on byte
  diff (per pitfalls §11).

  Verify:
  - `bin/check-stale-previews` exit 0 (SHA in meta.yml == SHA256(template.sla))
  - All 14 `page-*.png` files exist and have a recent mtime
  - `template.sla` and `template-preview.sla` modified
  - `preview.pdf` modified

  This commit will have a large PNG diff (per pitfalls §9). The next reviewer
  will see ~5-6 page PNGs change visibly. Per pitfalls §9 the EXECUTION.md (T09)
  must include a "Visual baselines change" section explaining each.

  Commit message:
      25: chore(zeitung): regenerate template.sla + gallery + SHA bump

      Atomic regen via bin/render-gallery zeitung-a4-grun --skip-visual-diff.
      Re-renders template.sla, template-preview.sla, all 14 page-NN.png,
      preview.pdf, and bumps meta.yml::previews_for_sla SHA. Visible PNG
      changes on pages 4, 5, 7, 9, 10, 13 reflecting the T06 geometry fixes.
      bin/check-stale-previews exit 0.
  </action>
  <verify>
  <automated>bin/render-gallery zeitung-a4-grun --skip-visual-diff &amp;&amp; bin/check-stale-previews</automated>
  </verify>
  <done>
  - `bin/render-gallery zeitung-a4-grun --skip-visual-diff` exit 0
  - `bin/check-stale-previews` exit 0
  - `templates/zeitung-a4-grun/template.sla` regenerated
  - `templates/zeitung-a4-grun/template-preview.sla` regenerated
  - All 14 `page-NN.png` regenerated
  - `templates/zeitung-a4-grun/preview.pdf` regenerated
  - `meta.yml::previews_for_sla` SHA updated to the new SHA256(template.sla)
  - Single atomic commit containing all regenerated artifacts + SHA bump
  </done>
</task>

<task type="auto" id="T08">
  <name>T08: test(zeitung) — add BandConsistencyInvariantTests to test_zeitung_geometry.py</name>
  <files>tools/sla_lib/tests/test_zeitung_geometry.py</files>
  <action>
  Add a `BandConsistencyInvariantTests` class to `test_zeitung_geometry.py` that
  pins the band/margin invariants on the real Zeitung document. These tests
  REPLACE the originally-planned three test classes for image-within-text-block,
  margin consistency, and text-card consistency (per RESEARCH.md §8).

  Use the EXACT skeleton from RESEARCH.md §8 (`class BandConsistencyInvariantTests`).
  Per RESEARCH.md §8 the tests "fail BEFORE the geometry fixes land; pass AFTER" —
  but since T06/T07 ran before this task, they pass on entry. The point is they
  PIN the invariants so future regressions are caught.

  Required tests (≥6 per the prompt):

  1. `test_no_body_content_in_header_band` — for each body-pool page (3, 4, 5, 6,
     7, 8, 9, 12, 13), no content frame's bbox crosses y=49 from above (i.e. no
     frame with y0 < 49 < y1).

  2. `test_no_body_content_in_footer_band` — mirror: no frame with y0 < 283 < y1
     (where y0 is below 283 and y1 is above 283 — meaning the frame straddles
     the footer band top).

  3. `test_body_content_within_left_margin` — for each LEFT body page, every
     content frame has bbox x0 >= 20 - 0.5 AND x1 <= 190 + 0.5.

  4. `test_body_content_within_right_margin` — for each RIGHT body page, every
     content frame has bbox x0 >= 20 - 0.5 AND x1 <= 190 + 0.5 (Zeitung is
     symmetric 20/20; if asymmetric in future the limits differ).

  5. `test_specific_drift_fixes` — pins the specific fixes from T06:
     - Page 5: P4 Foto-Spread (or whatever its anname is post-fix) y_bottom <= 283.5
     - Pages 7, 9, 13: every body TextFrame y_top >= 48.5 (allowing 0.5mm tolerance)
     - Page 4 col-3: assert col-3 frame's h_mm matches the choice from T06
       (full-height ~100mm OR explicitly absent for 2-col variant)
     - Page 10: assert exclusion (page in excluded_pages) OR body frames within
       margins, matching the T06 decision

  6. `test_excluded_pages_match_meta_yml` — load `body_block_margins.excluded_pages`
     from meta.yml, assert it equals `[1, 2, 10, 11, 14]` (or the post-T06 value
     if page 10 was un-excluded). This test pins the feature-page list so any
     future change is deliberate.

  7. `test_background_decoration_full_bleed_OK` — pages 12 and 13 each have a
     Polygon (or image-less ImageFrame) with `fill="Dunkelgrün"` extending past
     the bands; this is intentional. Test asserts at least one such polygon
     exists on those pages and that the page itself still passes
     `_BandConsistencyRule` (no ERRORs from the polygon).

  Implementation notes:
  - Use the existing `_doc()` helper or equivalent in `test_zeitung_geometry.py`
    (read the top of the file to find it).
  - Use `frame_bbox_mm` from `sla_lib.builder.bbox` for bbox computation.
  - Use `_content_frames(page)` helper per RESEARCH.md §8 skeleton (TextFrames +
    ImageFrames with image content).

  Verify: `python3 -m unittest discover tools/sla_lib/tests` exit 0. ALL tests
  pass (T06 fixed the geometry; these tests now lock it in).

  Commit message:
      25: test(zeitung): add BandConsistencyInvariantTests pinning post-T06 geometry

      ≥6 invariant tests in test_zeitung_geometry.py::BandConsistencyInvariantTests.
      Pins: no body content in header band y=20-49, no body content in footer
      band y=283-297, L/R margins 20mm, P4 Foto-Spread y_bottom <= 283, body
      frames on pages 7/9/13 at y >= 49, page-4 col-3 height matches T06
      decision, excluded_pages == [1, 2, 10, 11, 14] (or post-T06 value),
      background-decoration polygons remain exempt. Replaces the three
      originally-planned test classes per RESEARCH.md §8. All tests pass.
  </action>
  <verify>
  <automated>python3 -m unittest discover tools/sla_lib/tests &amp;&amp; python3 -m unittest tools.sla_lib.tests.test_zeitung_geometry.BandConsistencyInvariantTests -v</automated>
  </verify>
  <done>
  - `BandConsistencyInvariantTests` class added to `test_zeitung_geometry.py`
  - ≥6 tests covering: header-band, footer-band, left-margin, right-margin, specific drift fixes, excluded_pages match, background decoration exempt
  - All tests in the new class pass (T06 already fixed the geometry)
  - `python3 -m unittest discover tools/sla_lib/tests` exit 0
  </done>
</task>

<task type="auto" id="T09">
  <name>T09: docs(reviews) — Codex post-fix verification iter2 + EXECUTION.md + status flip</name>
  <files>reviews/codex-zeitung-band-iter2.md, .issues/25-zeitung-image-vs-text-column-extent-per-page-type-margin-consistency-text-card-b/EXECUTION.md, .issues/25-zeitung-image-vs-text-column-extent-per-page-type-margin-consistency-text-card-b/ISSUE.md</files>
  <action>
  Re-run Codex visual review against the post-fix Zeitung previews to verify the
  fixes resolved the band-consistency drift, then write EXECUTION.md and flip
  ISSUE.md status to `done`.

  1. Re-run Codex with the same prompt from T05
     (`prompts/zeitung-band-consistency-audit.md`) against the post-T07 PNGs.
     Save output to `reviews/codex-zeitung-band-iter2.md` with the same metadata
     as iter1 (date/time, codex CLI version, prompt path, full response).

  2. Verdict requirement: `<verdict value="pass" body_pool_findings=0
     spread_baseline_findings=0>` OR documented residual findings.
     - If iter2 verdict is `pass` with zero band-consistency ERRORs: success path.
     - If iter2 still flags issues: per RESEARCH.md §7 + pitfalls §14, the
       2-iteration budget is exhausted — defer to #26. Document the deferred
       items explicitly in EXECUTION.md and `reviews/codex-zeitung-band-iter2.md`.
       Do NOT loop back to T06 with a third Codex iteration.

  3. Cross-check vs audit-tool JSON (mirror T05 cross-check):

         bin/audit-alignment zeitung-a4-grun --json > /tmp/audit-25-iter2.json

     Verify `band_consistency_warnings` is empty on every page. If audit JSON
     finds something Codex missed (or vice versa), document the gap in
     EXECUTION.md.

  4. Write `.issues/25-…/EXECUTION.md` covering:
     - Tasks T01-T09 with status (DONE / DEFERRED) + commit SHA per task
     - Pre-fix Codex iter1 findings summary
     - Post-fix Codex iter2 verdict
     - Visual baselines change section (per pitfalls §9): list which page-NN.png
       files changed and why, with one-line description per page (e.g.,
       "page-05.png: P4 Foto-Spread cropped to y=283")
     - Open questions resolved (§12 #1 page-4 col-3, §12 #2 page-10 status)
     - Any deferred items (with explicit "deferred to #26" note if applicable)
     - Final state of band_consistency_warnings count (should be 0 on Zeitung)

  5. Flip ISSUE.md status from `open` to `done`. Per project pattern (and the
     prompt's instruction "status flip to done"), use the issue-cli flip
     mechanism if available (`issue-cli status set 25 done` — check
     `issue-cli --help`); otherwise edit the YAML frontmatter `status: done`
     directly. Per `.issues/config.yaml::commit_artifacts: true` the EXECUTION.md
     and ISSUE.md status flip ship in this commit.

  6. Commit EXECUTION.md + iter2 review + ISSUE.md status flip atomically. The
     status flip is the LAST git change in the PR.

  Commit message:
      25: docs(reviews): Codex band-consistency iter2 (post-fix verify) + close

      Codex iter2 verdict: <pass body_pool_findings=0 | <residual>>. Audit JSON
      cross-check: zero band_consistency_warnings on Zeitung post-fix. EXECUTION.md
      summarizes T01-T09 with commit SHAs, visual baselines changed pages list,
      open questions §12 #1 / #2 resolutions, and any deferred items (→ #26).
      ISSUE.md status flipped to done.
  </action>
  <verify>
  <automated>test -f reviews/codex-zeitung-band-iter2.md &amp;&amp; test -f .issues/25-zeitung-image-vs-text-column-extent-per-page-type-margin-consistency-text-card-b/EXECUTION.md &amp;&amp; grep -q "verdict" reviews/codex-zeitung-band-iter2.md &amp;&amp; grep -q "status: done" .issues/25-zeitung-image-vs-text-column-extent-per-page-type-margin-consistency-text-card-b/ISSUE.md &amp;&amp; bin/audit-alignment zeitung-a4-grun --json | python3 -c "import json,sys; d=json.load(sys.stdin); count=sum(len(p.get('band_consistency_warnings',[])) for p in d['pages']); print('post-fix band warnings:', count); assert count == 0, f'expected zero, got {count}'"</automated>
  </verify>
  <done>
  - NEW `reviews/codex-zeitung-band-iter2.md` with date/time, codex version, prompt path, full Codex response, verdict block
  - NEW `.issues/25-…/EXECUTION.md` covering tasks T01-T09 with commit SHAs, baselines section, open-question resolutions, deferred items
  - `bin/audit-alignment zeitung-a4-grun --json` shows zero `band_consistency_warnings` on every page
  - `ISSUE.md` frontmatter `status: done`
  - Single atomic commit closing the PR
  </done>
</task>

</tasks>

<verification>
Final verification gate (run after all 9 tasks land):

1. `python3 -m unittest discover tools/sla_lib/tests` — exit 0 (registry test, band-consistency unit tests, audit-alignment tests, BandConsistencyInvariantTests all pass)
2. `python3 -m sla_lib.builder.structural_check --all` — exit 0 (Zeitung clean post-T06; 7 non-Zeitung templates skip via override)
3. `bin/audit-alignment zeitung-a4-grun --strict` — exit 0 (zero band findings post-T06)
4. `bin/audit-alignment --all --strict` — exit 0
5. `bin/check-stale-previews` — exit 0 (SHA matches post-T07)
6. `bin/audit-alignment zeitung-a4-grun --json | python3 -c "import json,sys; d=json.load(sys.stdin); count=sum(len(p.get('band_consistency_warnings',[])) for p in d['pages']); assert count == 0"` — zero band warnings

Any failure here blocks PR merge.
</verification>

<success_criteria>
Maps 1:1 to RESEARCH.md §14 acceptance criteria (which supersedes ISSUE.md):

- [ ] `brand:band_consistency` rule exists with full unit-test coverage; severity ERROR for band/margin violations; per-template skip via `meta.yml::brand_overrides` (T01)
- [ ] `meta.yml` schema extended with `body_block_margins` field (bands + margins + background_decoration + excluded_pages) (T01)
- [ ] Zeitung's `meta.yml::body_block_margins` populated per RESEARCH.md §4 (T04)
- [ ] Zeitung's 6 drift fixes applied per RESEARCH.md §2 table (T06)
- [ ] 7 non-Zeitung templates have pre-applied `brand_overrides[brand:band_consistency]` skip (T03)
- [ ] `python3 -m sla_lib.builder.structural_check --all` exit 0 (T06 verification)
- [ ] `bin/audit-alignment zeitung-a4-grun --strict` exit 0 (T06 verification)
- [ ] `python3 -m unittest discover tools/sla_lib/tests` exit 0 (T08 verification)
- [ ] Codex visual review iter1 (pre-fix) cross-checked vs audit JSON (T05)
- [ ] Codex visual review iter2 (post-fix) verdict = pass with zero band ERRORs (T09)
- [ ] Geometric invariant tests in `test_zeitung_geometry.py::BandConsistencyInvariantTests` pin all 6 fixes (T08)
- [ ] `bin/render-gallery zeitung-a4-grun --skip-visual-diff` regenerates template.sla + page-NN.png + meta.yml SHA (T07)
- [ ] `bin/check-stale-previews` exit 0 (T07 verification)
- [ ] Registry count test bumps 15 → 16 (T01)
- [ ] EXECUTION.md written; ISSUE.md status flipped to `done` (T09)
- [ ] No "claude" / AI-attribution in any commit, code, or file (every task's commit message reviewed)
</success_criteria>
