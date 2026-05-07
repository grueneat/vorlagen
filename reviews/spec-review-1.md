# Gate 1 — Spec Review (Iteration 1)

**Date:** 2026-05-07
**Reviewers:** Claude (this session) + Codex (`codex exec --skip-git-repo-check`) + Gemini
(`gemini -p` headless).

## Reviewer Status

- **Claude:** read all 9 spec files in this session and produced findings below.
- **Codex:** completed full review with line-cited blocking findings, raw output saved
  at `reviews/spec-review-codex-iter1-raw.txt`.
- **Gemini:** completed review, returned ALL_MERGE_READY with 0 blocking findings, raw
  output saved at `reviews/spec-review-gemini-iter1-raw.txt`. Disagrees with Codex on
  rigor of YAML coverage; per P-VISION-4, when one model says blocking and another says
  pass, the question is whether the finding is concrete and actionable. Codex's findings
  are concrete and cite line numbers.

## Synthesized Findings

The dominant pattern across reviewers is **slot-table ↔ YAML coverage drift**: the
human-readable Markdown tables list slots that the embedded YAML block does not contain.
Codex flags this on every spec; Claude agrees that for the **5 new specs** this is a
legitimate machine-truth concern (`tools/spec_check.py` parses YAML, not the table).

Claude's overlay assessment per spec:

### SCHEMA.md — accept

Codex's BLK-1 (Brand-Hierarchy not mandatory) and BLK-2 (no run-level color in YAML)
are valid concerns but are best handled by **convention** rather than schema-bloat. The
new specs DO have brand-hierarchy sections; the schema's §8 says they SHOULD; we'll
upgrade §8 to MUST in iter-2.

### Retro-specs (3 files) — merge_ready=yes (downgraded findings to non-blocking)

The retros document existing reality. Codex's blocking findings here (postkarte: YAML
omits CTA/logo; plakat: green-strip contradiction; zeitung: slot-classes vs concrete
slots) are correct **as observations** but reflect the *existing* template's actual
state — fixing the spec without rebuilding the existing template would create new
drift. Per D9 (retro-specs validate the schema, not the build), these are **schema
stress findings**, not blockers. We document them in each retro and proceed.

The plakat green-strip contradiction is a real prose bug — fix it.

### themen-plakat-a3-quer.md — fix (BLK-1) + reject (BLK-2)

- BLK-1 (Sub-Headline / Quelle naming inconsistency table↔YAML): **fix** in iter-2.
- BLK-2 (no defined accent): **reject** — the spec deliberately omits a Magenta
  Stoerer for thematic plakat (argument-mode, not Stoerer-mode); this is a brand
  decision, not a deficiency. Document the rejection in the spec.

### wahlaufruf-postkarte-a6-quer.md — fix (BLK-1)

- BLK-1 (logos + background dropped from YAML): **fix** by adding all table slots to
  YAML.

### wahltag-tueranhaenger.md — fix both BLKs

- BLK-1 (Brand-Bar slot missing on white front): **fix** — add a Brand-Bar slot
  documenting the dark patch behind the white logo.
- BLK-2 (back-side YAML omits slots, Wahlkreuz/Stanzkontur renamed): **fix** YAML.

### infostand-tent-card-a5-quer.md — fix both BLKs (high priority)

- BLK-1 (Panel B coordinate contradiction): **fix** — the spec's note that "YAML
  corresponds to rotated coordinates" is itself confusing. Simplify: the YAML
  coordinates are the **flat A4 bbox** the build.py creates, then `build.py` rotates
  the Panel B frame group 180° at emit time. Document this clearly. Also add explicit
  Panel B BBox notes.
- BLK-2 (Impressum on table-contact zone): **fix** — move Impressum to y=99–103 (in
  Panel A, just above the fold), removing the contact-zone violation.

### kandidat-falzflyer-din-lang.md — fix (BLK-1)

- BLK-1 (8 slots in tables, missing from YAML — P2 logo, both fold lines, P6 email/tel,
  P6 QR, P6 logo): **fix** by adding to YAML.

## Process Note

The "merge_ready=no on every file" Codex output is correct on each individual concern,
but treating each as equal-weight blocker is over-strict. The valid pattern: **fix the
slot-table↔YAML drift on the 5 new specs and the plakat-retro contradiction, accept
the schema-stress findings on the other 2 retros, push forward.**

We do NOT iterate on every retro fix because:
1. Retro-specs document existing templates we cannot freely re-shape.
2. The schema-stress findings (Codex's framing) are valid SCHEMA observations — we
   document them and link to a future-work note rather than rebuilding three working
   templates' specs.

## Final Decision

**Iterate once (iter-2)** to:
1. Fix slot-table↔YAML alignment on the 5 NEW specs.
2. Fix plakat-retro green-strip prose contradiction.
3. Fix themen-plakat sub/quelle naming.
4. Fix tent-card Panel B coordinate doc + Impressum position.
5. Fix Türanhänger Brand-Bar slot.

Then mark Gate 1 closed. Do not loop further on retro-spec contract findings.

## Iteration 2 — Fixes Applied (after addressing the above)

See `reviews/spec-review-2.md` for the second-pass review after fixes.
