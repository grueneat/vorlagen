# Claude Design — Kickoff Prompt Skeleton

Copy-paste this into a new Claude Design conversation on [claude.ai](https://claude.ai). Replace `<…>` placeholders with your actual task.

---

## Universal kickoff (always start with this)

```
Repository: https://github.com/GrueneAT/vorlagen (public, open-source)

START by reading shared/brand/DESIGN-SYSTEM-BRIEF.md — it is the
authoritative entry-point for any design task in this repo and tells
you what to read next based on the task type.

Brand rules of last resort: shared/brand/QUICKGUIDE-NOTES.md (always
binding). Brand colors / fonts: shared/ci.yml. Brand assets:
shared/logos/ and shared/brand/.

Task: <PASTE ONE OF THE PROMPT PATTERNS BELOW, OR YOUR OWN ASK>

Output format (always):
- Markdown report
- Per-finding/per-variation: title, rationale tied to Quickguide rule,
  concrete changes (file:line where possible), severity tag
  (blocking | recommended | optional)
- Append a session-history row to DESIGN-SYSTEM-BRIEF.md §10 in your
  output (so I can copy it back when committing your output as a new
  issue)
```

---

## Prompt-Pattern A — Brand-Consistency-Audit

```
Run pattern A from DESIGN-SYSTEM-BRIEF.md §7. Check all 8 templates
in §3 for compliance against §4 brand rules. Severity-sort the
violations. Identify the single highest-priority fix.
```

## Prompt-Pattern B — Layout-Variation für ein einzelnes Template

```
Run pattern B from DESIGN-SYSTEM-BRIEF.md §7 for template
templates/<slug>/. Improve <specific aspect — e.g. headline-subline-
hierarchy, eye-flow on the 1-second-test, photo-text-balance,
whitespace-rhythm>.

Constraints recap (from §4): only Quickguide colors/fonts, M margins,
"Typografie immer auf Grün", logo 3×M, Wahlkreuz on colored bg,
no off-palette colors, no third-party fonts.

Propose 3 variations. Render each as an Artifact (mock at the
template's actual aspect ratio) so I can compare visually. Plus the
markdown report with concrete change-list per variation.
```

## Prompt-Pattern C — Hierarchy-Refinement

```
Run pattern C from DESIGN-SYSTEM-BRIEF.md §7 for template
templates/<slug>/. The visual hierarchy currently feels weak in
<describe — e.g. "headline and subline read at similar intensity",
"body text dominates the headline because of line-count mismatch">.

Propose 2-3 hierarchy refinements respecting line-spacing × 0.9 and
HL/SL × 2-baseline spacing rules. Concrete changes only.
```

## Prompt-Pattern D — Cross-Template-Harmonization

```
Run pattern D from DESIGN-SYSTEM-BRIEF.md §7. Look at page-01.png of
all 8 templates listed in §3. Find spacing / grid / typography / 
color-use inconsistencies across the set. List with severity tags.
End with "if I could only fix one thing first" priority pick.
```

## Prompt-Pattern E — Neues Template-Vorschlag

```
Run pattern E from DESIGN-SYSTEM-BRIEF.md §7. We need a NEW template
with these constraints:

Audience: <describe — e.g. "Studierende-Initiativen an österreichischen
Universitäten">
Use-case: <describe — e.g. "Mobilisierung für Klimastreiks; Aushang
auf Schwarzen Brettern, Online-Sharing, Print-Format A3 hochformat">
Distinctive feature: <e.g. "QR + minimal copy, foto-stark">

Propose: layout philosophy (one-liner), trim+bleed+falz in mm,
slot inventory (≥10 slots), 1-second-test answer, ASCII layout sketch,
brand-rule applications. NO build.py code — just the spec.
```

## Prompt-Pattern F — Sample-Inhalts-Audit (after #13 merge)

```
Run pattern F from DESIGN-SYSTEM-BRIEF.md §7. Read
shared/sample-images/manifest.yml (post-#13). Check whether each
template's gallery render looks like authentic Grünen-NÖ campaign
material, not generic stock. Propose better library entries (new
Codex prompts, brand-relevant subjects) where needed. Specifically
flag any image that violates Quickguide §4 rule 7 ("Typografie auf
Grün").
```

---

## After receiving Claude Design's output

1. Save the Markdown report somewhere (download as file or copy to clipboard).
2. In your local terminal:
   ```bash
   /issue:new <descriptive title>
   ```
3. Paste the report as the issue description seed.
4. Run `/issue:work <slug>` to drive the implementation pipeline (discuss → research → plan → execute) on the design changes.
5. Once merged, append the session-history entry from the report to `shared/brand/DESIGN-SYSTEM-BRIEF.md` §10 (small commit).
