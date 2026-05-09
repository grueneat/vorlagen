---
review_of: zeitung-visual
review_type: topic
review_mode: topic
reviewed_at: 2026-05-09T14-44-21Z
tool: codex
model: gpt-5.4
duration_seconds: 129
---

# Zeitung visual alignment audit

Inspected `templates/zeitung-a4-grun/page-01.png` through `page-14.png` visually, page by page.

## Findings

- Page: 01
- Type: flush-mismatch
- Frames involved (best-effort identification by visual position): "cover hero photo at top of page; full-width dunkelgruen band directly beneath it"
- What's wrong: top cover photo stops short of both outer side edges and leaves visible white side margins, while the green band below runs wider to the page edges.
- Severity: ERROR

- Page: 02
- Type: bleed-gap
- Frames involved (best-effort identification by visual position): "top full-width photo with white headline over image"
- What's wrong: the top image on this left-hand page does not reach the left outer print edge and leaves a visible white strip.
- Severity: ERROR

- Page: 05
- Type: bleed-gap
- Frames involved (best-effort identification by visual position): "bottom full-width meeting photo"
- What's wrong: the bottom image on this left-hand page stops short of the left outer edge, leaving a visible white margin instead of bleeding out.
- Severity: ERROR

- Page: 11
- Type: bleed-gap
- Frames involved (best-effort identification by visual position): "portrait photo at bottom-right of page"
- What's wrong: the portrait image ends before the right outer print edge and leaves a visible white strip on the outside.
- Severity: ERROR

- Page: 12
- Type: bleed-gap
- Frames involved (best-effort identification by visual position): "full-page dunkelgruen content field; bottom full-width photo"
- What's wrong: on this left-hand page, both the green full-width field and the bottom photo start inset from the left outer edge, leaving visible white margin instead of outer bleed.
- Severity: ERROR

- Page: 13
- Type: bleed-gap
- Frames involved (best-effort identification by visual position): "full-page dunkelgruen content field"
- What's wrong: on this right-hand page, the green full-width field stops short of the right outer edge and leaves a visible white strip.
- Severity: ERROR

- Page: 14
- Type: bleed-gap
- Frames involved (best-effort identification by visual position): "top dunkelgruen event/imprint field; bottom full-width street-scene photo"
- What's wrong: on this right-hand page, both the upper green field and the lower photo stop short of the right outer edge, leaving visible white margin where the layout should bleed out.
- Severity: ERROR

Pages 03, 04, 06, 07, 08, 09, and 10 did not show a visible alignment defect in this visual audit. Page 08's portrait card appears visually flush to its card bounds, and page 10's body text does not visibly intrude into the lower green card.

<verdict value="fail" critical="0" high="7" medium="0">
Multiple outer-edge bleed failures remain across the set, including the known cover, left-page full-width images, and right-page photo/panel layouts.
</verdict>

