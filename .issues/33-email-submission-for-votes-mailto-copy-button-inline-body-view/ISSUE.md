---
id: '33'
title: Email submission for votes — mailto + copy button + inline body view
status: open
priority: high
labels:
- enhancement
- templates
- visual-qa
source: github
source_id: 68
source_url: https://github.com/GrueneAT/vorlagen/issues/68
---

## Context

The voting page on https://grueneat.github.io/vorlagen/experiments/falzflyer-p2-mein-plan-v2/ currently exports vote data as a JSON file the rater downloads to disk. Per phone review of v2: **no casual voter will download a file and email it back**. We need a frictionless submission path that works on phones, requires zero infrastructure, and lets the rater choose their preferred channel (email, WhatsApp, Signal, etc.).

Three earlier candidates compared (mailto / webhook.site / Apps Script). Decision: **email-based submission via `mailto:`** — zero backend, permanent storage in your inbox, works on every device, multi-channel friendly.

## Solution

Replace the current "Export JSON" with **three submission paths sharing one body format**:

1. **"Send vote (Email)" button (primary)** — opens the rater's email client via `mailto:` with the To, Subject, and Body pre-populated. They just tap Send.
2. **"Copy vote" button (secondary)** — copies the same body to the clipboard. Rater pastes into WhatsApp / Signal / Telegram / iMessage / wherever they message you.
3. **Inline read-only display of the body (always visible after voting)** — a `<pre>` or read-only `<textarea>` showing the formatted body. Rater can screenshot, select-and-copy manually, or just verify what they're sending.

All three share one body string built once per session.

## Body format

Hybrid: human-readable list at the top, machine-readable JSON block at the bottom, separated by markers.

```
Hi Flo,

Here's my ranking for falzflyer-p2-mein-plan-v2:

 1. numbered-priority-list-v2
 2. manifesto-single-statement-v2
 3. dunkelgrun-rules-between-items-v2
 4. weighted-hero-lead
 …

— <rater>
<ISO timestamp>

──────────  machine-readable, please don't edit  ──────────
VOTE-JSON-START
{"experiment_id":"falzflyer-p2-mein-plan-v2","rater":"flo","mode":"rank","ranking":[...],"started_at":"...","exported_at":"..."}
VOTE-JSON-END
```

Subject line: `[vote] <experiment-id> — <rater>`.
To: `florian.motlik@gruene.at` (hardcoded; can be overridden per-experiment via `manifest.yml::submission.email_to` if the schema supports it).

## Tooling changes

- `site/src/pages/experiments/[id].astro` — replace the current export button with the three new paths. Reuse the existing `session.ranking[]` state model. URL-encode body via `encodeURIComponent` for the `mailto:` link. Use the modern `navigator.clipboard.writeText()` for the copy button with a graceful fallback (legacy `document.execCommand('copy')` is dead on iOS Safari; use a hidden textarea + select + execCommand as belt-and-suspenders or just feature-detect and warn). Show success toast after each action.
- `tools/experiment_results.py` — add `--from-emails <dir>` flag that ingests `.eml` or `.txt` files, extracts JSON between `VOTE-JSON-START`/`VOTE-JSON-END` markers, validates each against the results schema, computes the aggregate. Operator workflow: select votes in inbox → save bodies to a folder → run aggregator pointed at the folder.
- `experiments/_schema/results.schema.yaml` — already accepts the new shape; no change unless we add optional `submission.channel: email|whatsapp|other` for provenance tagging (deferred — keep simple).
- `.claude/skills/experiments/SKILL.md` — update the `/experiments capture` section to document the new operator workflow (select emails → save to folder → run aggregator). Remove or downplay the "JSON file download" path.

## Acceptance Criteria

- [ ] Email button opens email client with To/Subject/Body pre-populated on desktop AND mobile (iOS Safari + Android Chrome)
- [ ] Copy button copies the same body to clipboard; success toast appears
- [ ] Inline body display visible after at least one ranked item is added
- [ ] All three paths share one body-string source-of-truth in the JS
- [ ] Body contains both the human-readable list and the JSON block between markers
- [ ] `tools/experiment_results.py --from-emails <dir>` reads multiple `.eml`/`.txt` files, extracts JSON, runs Borda aggregation, produces SUMMARY.md identical in shape to the current JSON-from-file flow
- [ ] Unit tests for the email parser: valid file with one vote, valid file with multiple votes, file missing markers (rejected with clear error), file with malformed JSON (rejected)
- [ ] `.claude/skills/experiments/SKILL.md` `/experiments capture` section updated for the email workflow
- [ ] Mobile-responsive — all three controls accessible at 360px viewport
- [ ] Existing JSON download removed from primary UI (can stay as a `?dev=1` URL param fallback if useful, planner's call)
- [ ] **Flo submits a v2 vote via the email path**, the aggregator processes the saved email, the corpus update lands in `design-guide/gruene-corpus.md` with dual-section (v1 envelope necessity + v2 density+form). Closes #29 T15 + #30 T17 + #31 T-final + #33 in one commit.

## Out of scope

- Server-side email parsing / IMAP integration
- Multi-rater real-time aggregation
- WhatsApp Business API integration (clipboard paste is the manual path)
- Email service integrations (Formspree, etc.) — explicitly rejected in favor of direct `mailto:`

## Dependencies

#29 + #30 + #31 + #32 (all merged).

## Priority

High — this unblocks the dual-section corpus update that's been pending since #29 T15. Without a usable submission UX, the entire experimentation feedback loop is stuck at "Flo votes by himself."
