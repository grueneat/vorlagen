# v1 anti-examples — DO NOT REPEAT

These are the 12 hypotheses from `experiments/falzflyer-p2-mein-plan/` (v1, 2026-04 run).
v1's failure mode: every variant violated the constraint envelope because the render gate only
enforced `brand:inside_page`, not the 16 BRAND_CONSTRAINTS + 22 Layer-1 thresholds. v2's
gate (T05) closes that loop. The 12 v1 hypotheses are listed below as named anti-examples;
v2's hypothesis-generation prompt threads this file in (token `{v1_anti_examples}`) so the
generator avoids re-emitting the broken implementations.

Format per entry: slug + violation + rule-id + imperative DO-NOT-REPEAT line. Three of
the 12 concepts are explicitly retained for v2 (with corrected implementations); their
anti-example entries call out the broken IMPLEMENTATION, not the idea.

---

### v1-asymmetric-editorial-rules

- **Concept:** Left-aligned items stacked under thin 0.4mm Dunkelgrün rules; items occupy left two-thirds, right third intentional whitespace.
- **Why disqualified:** `layer1:negative_space_pct` — 5 rows × 22mm = 110mm of content in a 130mm-available body, leaves only ~15% whitespace (floor 30%).
- **DO NOT REPEAT:** Do not stack 5 left-aligned rows in the body if each row consumes ≥20mm of vertical space.

_Concept retained for v2 (`dunkelgrun-rules-between-items-v2`) with envelope-respecting re-implementation per PLAN.md T13. This anti-example is about the v1 broken IMPLEMENTATION, not the idea._

### v1-cut-to-three-with-body

- **Concept:** 3 items, each with a one-sentence explanatory body.
- **Why disqualified:** `layer1:body_min_pt` likely tripped — body sub-frames at small fontsize to fit 3 items + 3 body paragraphs in 130mm panel.
- **DO NOT REPEAT:** Do not author 3-item + body layouts whose body text falls below 10pt — pick fewer items or shorter bodies.

### v1-first-person-commitments

- **Concept:** "Ich werde…" first-person bullets, voice-formality axis.
- **Why disqualified:** `layer1:type_sizes_per_panel` — peer-list 5-bullet layout uses constant body size but the eye lands nowhere (no hierarchy), and any subline differentiation pushed sizes past 3.
- **DO NOT REPEAT:** Do not convert the 5-Schlagwort list to first-person bullets while keeping all 5 at equal weight — that's a voice tweak, not a structural commitment.

### v1-handwritten-protest-aesthetic

- **Concept:** Wildcard — handwritten-style margin notes overlay the panel.
- **Why disqualified:** `brand:font_family` + `brand:text_on_green` + `brand:image_text_overlap` — non-brand font face, margin notes off green backing, text overlaps Hellgrün backing partially.
- **DO NOT REPEAT:** Do not introduce non-`shared/ci.yml::fonts` font faces. Wildcards must respect the envelope unless `relax:` is declared.

### v1-luxurious-whitespace-two-items

- **Concept:** 2 items only, generous whitespace.
- **Why disqualified:** `layer1:headline_size_jump_x` likely tripped — 2-item layout pushes each item to display-size to fill the panel, breaking the body↔headline 2.5× jump.
- **DO NOT REPEAT:** Do not propose 2-item layouts that grow body text into display-sized type to fill the panel; that conflates body with display.

### v1-manifesto-single-statement

- **Concept:** ONE 30pt Vollkorn Black manifesto sentence owns the panel.
- **Why disqualified:** `brand:font_family` — `Vollkorn Black` (non-italic) is NOT registered in `shared/ci.yml::fonts` (only `Vollkorn Black Italic` is). The variant likely rendered via Scribus fallback face.
- **DO NOT REPEAT:** Do not specify fonts that are not in `shared/ci.yml::fonts`. The available italic-Vollkorn is `Vollkorn Black Italic`.

_Concept retained for v2 (`manifesto-single-statement-v2`) with envelope-respecting re-implementation per PLAN.md T12. This anti-example is about the v1 broken IMPLEMENTATION, not the idea._

### v1-numbered-priority-list

- **Concept:** Numbered 1..5 with thin Dunkelgrün rules between rows.
- **Why disqualified:** No rank-weighted typographic scale — all 5 numerals at constant 28pt. The concept "weighted scale per rank" was promised but never delivered; the eye lands nowhere by hierarchy.
- **DO NOT REPEAT:** Do not propose numbered-list hypotheses whose numerals are uniform in size — the hierarchy lever was promised but not exercised.

_Concept retained for v2 (`numbered-priority-list-v2`) with envelope-respecting re-implementation per PLAN.md T11. This anti-example is about the v1 broken IMPLEMENTATION, not the idea._

### v1-quote-from-resident

- **Concept:** Verbatim resident quote leads; candidate reply below.
- **Why disqualified:** `layer1:type_families_per_panel` — italic-quote register + Gotham-Bold reply + caps for attribution exceeds the 2-family floor.
- **DO NOT REPEAT:** Do not use more than 2 type families per panel. Quote + reply must share a family or one must adopt the other's.

### v1-staggered-block-accent

- **Concept:** Odd-indexed slogans on small Dunkelgrün blocks (staggered).
- **Why disqualified:** `brand:image_text_overlap` — staggered blocks partially overlap adjacent slogans' text frames at the boundaries (forbidden by issue #23).
- **DO NOT REPEAT:** Do not place coloured blocks that partially overlap text frames; either fully contain text in a block or keep blocks clear of text bbox.

### v1-vollkorn-italic-cornerstone

- **Concept:** Cornerstone slogan in Vollkorn italic; rest in Gotham.
- **Why disqualified:** `layer1:headline_size_jump_x` — cornerstone slogan at 28pt + supporting list at 14pt is only 2× jump (floor 2.5×). Family mix uses 2 families correctly but jump is too small.
- **DO NOT REPEAT:** Do not propose typographic-hierarchy layouts whose size jump is below 2.5× — the lever's intent is to be visually unambiguous.

### v1-weighted-hero-lead

- **Concept:** One hero promise + four supporters in compact list.
- **Why disqualified:** `layer1:body_min_pt` — supporting list cramped to fit alongside hero, body text drops below 10pt.
- **DO NOT REPEAT:** Do not author hero+supporters layouts whose supporters end up below 10pt to fit four in the remaining panel height.

### v1-yellow-accent-privileged-item

- **Concept:** One item on Gelb backing, rest on Hellgrün.
- **Why disqualified:** `brand:text_on_green` — Gelb is not green; white-on-Gelb is a contrast hazard and `display_contrast_ratio_18pt_plus` likely below 3:1.
- **DO NOT REPEAT:** Do not place white display text on Gelb backing. Gelb is brand-accent, not a text-bearing surface; use Dunkelgrün text on Gelb if Gelb is the backing.

---

_Anti-example format: `slug + violation + rule-id + imperative` (NeQA-aware — negation-only prompts degrade at scale; each entry pairs a specific rule_id reason with a concrete forbidden pattern)._
