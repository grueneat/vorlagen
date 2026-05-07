# CONTEXT — design decisions for issue 5

## Decisions (locked — research/planner must follow)

- **`build.py` is always AI-authored, never hand-written.**
  Source inputs the AI translates from include: an existing `.sla` file (current path via `tools/sla_to_dsl.py`), a PDF reproduction of an existing template, an InDesign document, or a plain-text/structured spec brief. The `build.py` file is the **durable artifact** that defines the template — versioned, diffed, rendered. The user never edits `build.py` by hand; corrections flow back through the AI from updated inputs. Visual diff against committed gallery PDFs is the gate that validates a (re)generated `build.py` is correct.

- **DSL is optimized for LLM emission, not human reading.**
  Primitives in `tools/sla_lib/builder/{primitives,document,styles,ci}.py` should be regular, verbose, predictable, named-arg-heavy. No clever shortcuts, no positional overloads, no implicit "smart" behaviors that an LLM might miss. Verbosity is fine — humans don't read the output. The visual-diff gate catches semantic errors that an LLM might produce. Higher-level **blocks** (`blocks.py`) may be more compact, since blocks are reused across many templates and a block bug surfaces everywhere.

- **Review scope spans all input paths.**
  The review must cover not only the existing SLA→`build.py` converter and the current `sla_lib` DSL, but also design considerations for future **PDF→`build.py`**, **InDesign→`build.py`**, and **spec→`build.py`** translation paths. The DSL must be designed to comfortably receive AI translations from any of these inputs. *Implementations* of PDF/InDesign/spec converters are deferred to follow-up issues; *design decisions about the DSL surface* must account for them now.

- **Migration scope: rewrite all three existing templates onto the new constructs.**
  Postkarte A6, Plakat A1, and Zeitung A4 will all be re-authored by AI using the hardened DSL once it lands. The committed gallery PDFs remain the visual ground truth — every rewrite must produce a render that diffs clean (or visually-indistinguishable per the existing tolerance) against those PDFs. Done as separate follow-up issues, in size order: Postkarte first (smallest, highest signal-to-noise as a worked example), then Plakat, then Zeitung.

- **Review report lives at `.issues/5-review-buildpy-dsl-before-more-templates/REVIEW.md`.**
  Not at `reviews/` repo root. Co-located with CONTEXT/RESEARCH/PLAN/EXECUTION so the review ships in the PR with the rest of the issue's artifacts and is preserved when the issue is archived.

- **`extra_*_attrs` strategy: hoist common values to DSL defaults; keep escape hatch.**
  The ~70 `extra_doc_attrs` keys that appear identically across all three templates become `Document` defaults injected by `Brand` (or whatever the new construct is called). `extra_doc_attrs=` and `extra_pdf_attrs=` remain on the `Document` constructor as override mechanisms for genuinely template-specific values. No forced removal of the escape hatch.

## Claude's discretion (research / planner / executor decide)

- **Naming and shape of the brand-level construct.** `Brand`, `BrandProfile`, expanding `ci.py`'s existing helpers — pick whatever the review converges on. Must consume `shared/ci.yml` as the single source of truth (today's pattern).
- **Block API surface and file split.** `blocks.py` is 400 lines today with `Headline4Line` + `StoererBadge`. Whether new blocks (Impressum, LogoBadge, ColumnTextBlock, ContactCard, etc.) live in one file, split into `blocks/` package, or grouped by template-class is for the planner to decide based on review findings.
- **Spec-file format design.** If the review proposes a "spec → build.py" path, the spec-file schema (YAML? JSON? Markdown frontmatter?) is open. Just propose something that's both LLM-emittable and human-reviewable.
- **Granularity of follow-up issues.** Whether the migration of the three existing templates is one issue per template or a single bundled issue is for the planner to decide based on the size of each rewrite.
- **`extra_*_attrs` deduplication mechanism.** Whether defaults are injected at `Document(...)` construction, at emit time, or via a `Brand.apply(doc)` call — pick whichever gives cleaner generated output.

## Deferred (out of scope for this issue)

- **PDF → `build.py`** converter *implementation*. (Design considerations are in scope; building the converter is a separate future issue.)
- **InDesign → `build.py`** converter *implementation*. Same caveat.
- **Spec → `build.py`** translation *implementation*. Same caveat.
- **Rewrites of the three existing templates.** Done as separate follow-up issues that depend on the DSL hardening landing first. The gating policy from the issue's acceptance criteria still applies: no new templates land before agreed P1 hardening items are merged, but the existing-template rewrites are themselves the follow-ups, not blockers for new templates beyond the DSL hardening.
- **Render-pipeline changes** (`tools/render.py`, `tools/visual_diff.py`, `tools/sla_diff.py`). Out of scope unless the review surfaces a hard dependency.
- **Gallery / Pages publication changes.** Out of scope.
