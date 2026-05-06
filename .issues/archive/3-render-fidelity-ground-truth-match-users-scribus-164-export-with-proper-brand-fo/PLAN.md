---
issue: 3-render-fidelity-ground-truth-match-users-scribus-164-export-with-proper-brand-fo
phase: plan
generated: 2026-05-06
---

# PLAN — Render-fidelity ground truth

## Executor briefing

You are persisting the render-fidelity state that the discuss step verified manually (0-pixel diff between headless render and the user's Scribus 1.6.4 desktop export, all 17 pages, all 3 templates) into the repo so future container rebuilds and CI runs reproduce it automatically.

**Three things change concretely:**

1. The committed `*-original.sla` files at workspace root get replaced with the corrected versions the user re-saved into `/root/workspace/originals/` (D1 — `FONTSIZE="11.7"` typo fixed in Zeitung). Filenames stay the same (ASCII; no umlauts) so test fixtures and `meta.yml::original_sla` references don't move.
2. `templates/zeitung-a4-grun/build.py` is regenerated via `tools/sla_to_dsl.py` from the corrected SLA so its 97 hardcoded `fontsize=11.7` Run(...) parameters become `fontsize=12`. Plakat and Postkarte build.py are re-checked but likely unchanged.
3. `templates/<id>/baseline.pdf` for all three templates is regenerated in this container's font-installed env (fonts at `/root/.local/share/fonts/gruene/`, Vollkorn alias active). The new baselines are byte-equivalent to the user's reference PDFs.

Plus the durable plumbing:

- `Dockerfile.claude` learns to install brand fonts from `/root/workspace/fonts/` (gitignored) when the build context contains them; sanity-probes loudly; no-ops gracefully when fonts/ is absent (CI / public clones).
- `shared/fonts/50-vollkorn-family-alias.conf` (committed) becomes the canonical alias source; Dockerfile COPYs it into `/etc/fonts/conf.d/`.
- `bin/check-fontsizes` (new) regression-checks for fractional `FONTSIZE` inside PAGEOBJECT subtrees only; hooked into `bin/validate` as a pre-flight.
- `.github/workflows/pages.yml` drops the `visual_diff` invocation from `validate-reproductions` (CI doesn't have brand fonts; `sla_diff --strict` stays as the structural gate).
- `docs/render-fidelity.md` (new) documents the chain.
- `shared/fonts/README.md` is updated to point at `fonts/` and the new install path.

**Read first, in order:**

1. `.issues/3-render-fidelity-ground-truth-match-users-scribus-164-export-with-proper-brand-fo/ISSUE.md` — eight acceptance criteria.
2. `.issues/3-render-fidelity-ground-truth-match-users-scribus-164-export-with-proper-brand-fo/CONTEXT.md` — D1–D7 locked decisions (non-negotiable).
3. `.issues/3-render-fidelity-ground-truth-match-users-scribus-164-export-with-proper-brand-fo/RESEARCH.md` — 623 lines, exhaustive codebase trace; authoritative for paths/line numbers.

**Load-bearing source (do not rewrite, only edit listed fields):**

- Workspace-root committed SLAs: `gruene-zeitung-vorlage-original.sla`, `plakat-a1-hochformat-original.sla`, `postkarte-vorlage-original.sla` (replace contents from corrected versions in `/root/workspace/originals/`).
- User's drop zone: `/root/workspace/originals/` — three corrected SLAs (umlaut-named) plus three reference PDFs. Out of git; **do not commit umlaut filenames or the reference PDFs**.
- Brand fonts: `/root/workspace/fonts/` (gitignored). 16 Gotham Narrow .otf + Vollkorn-BlackItalic.ttf + full Vollkorn family.
- Live fontconfig alias: `~/.config/fontconfig/conf.d/50-vollkorn-family-alias.conf` (16 lines — copy verbatim into the repo).
- `Dockerfile.claude` (currently 112 lines) — extend, don't rewrite.
- `bin/validate` (73 lines) — extend with one preflight invocation, no other changes.
- `tools/sla_to_dsl.py`, `tools/sla_diff.py`, `tools/visual_diff.py`, `tools/_export_pdf.py` — invoke unchanged.
- `templates/<id>/meta.yml`, `templates/<id>/build.py`, `templates/<id>/baseline.pdf` for the three real templates.
- `.github/workflows/pages.yml` — surgically remove only the `visual_diff` invocation block (lines 115–121); keep everything else.

**Resolutions for RESEARCH.md's 8 open questions** (do not re-surface — bake in):

- **Filename strategy:** corrected SLAs from `originals/` overwrite the *existing* workspace-root `*-original.sla` files (path unchanged, content fresh). Umlaut originals stay in `/root/workspace/originals/` as the user's drop zone, out of git. **No new paths in the worktree.**
- **Reference PDFs:** do NOT commit `originals/*.pdf`. The regenerated `templates/<id>/baseline.pdf` files in Phase 2 serve the same role for `bin/validate`.
- **Zeitung build.py regeneration:** mandatory (97 fontsize=11.7 → 12 changes). Plakat + Postkarte: re-run the converter; commit only if the diff is non-empty.
- **CI visual_diff:** outright remove from the workflow; keep sla_diff. Add `# TODO` comment with reference to a follow-up CI-fonts issue.
- **Per-template `diff.yml` thresholds:** untouched in this PR (PR #5 already set Zeitung to 1.0%/5.0%, the spec value).
- **`samples-output/originals/*.pdf`:** out of scope, leave alone.
- **Regression check:** include the PAGEOBJECT-scoped `bin/check-fontsizes` per RESEARCH.md §"bin/validate change required". Hook into `bin/validate` as a preflight. Not a pre-commit hook.
- **Fontconfig alias commit location:** `shared/fonts/50-vollkorn-family-alias.conf` (consistent with `shared/fonts/README.md`).

**Honour without restating:**

- D1 — SLAs already corrected (no SLA edits in this PR; just adopt).
- D2 — fonts at `/root/workspace/fonts/`, gitignored, install at container build.
- D3 — Scribus 1.6.3 (Debian arm64) is the canonical render engine.
- D4 — `originals/` is the user's drop zone; workspace-root `*-original.sla` are the git-tracked canonical copies.
- D5 — regenerate `templates/<id>/baseline.pdf` from corrected SLAs in font-installed env.
- D6 — write `docs/render-fidelity.md`.
- D7 — CI font provisioning is OUT of scope; tracked in a separate follow-up issue.

**Constraints (CONTEXT.md):**

- DO NOT edit `originals/*.sla` files — the user's drop zone, immutable from this side.
- DO NOT bundle Gotham Narrow into the public repo at any path. `.gitignore` blocks `*.otf`/`*.ttf`/`*.ttc`/`fonts/`; verify nothing slips in.
- Keep PR #5's `bin/validate` standard: DSL→baseline ≤3 px per template at 150 dpi (Qt anti-aliasing floor).
- The DSL side is unchanged in this issue except for the FONTSIZE-typo fix that flows from the corrected SLA.

**Commit format:** Conventional commits, no issue prefix (no `.issues/config.yaml` exists). Examples: `feat(fonts): wire brand fonts into dev container`, `fix(zeitung): regenerate build.py from corrected SLA`, `docs(render): document fidelity pipeline`. **No "claude" attribution** in commits, code, or filenames (per user memory `feedback_no_claude_attribution.md`).

## Reusable verification helpers

These bash snippets are referenced by name from individual tasks. The executor copies them inline.

<helper id="render_and_pixeldiff">
Render each `<workspace-root sla>` headless and 0-fuzz pixel-diff against the user's matching `originals/<umlaut>.pdf` reference. Used by Phase 0.2, 2.4, 9.1.

```bash
mkdir -p "$OUT_DIR"
for pair in \
    "gruene-zeitung-vorlage-original.sla:/root/workspace/originals/Grüne Zeitung Vorlage Scribus.pdf:zeitung" \
    "plakat-a1-hochformat-original.sla:/root/workspace/originals/Plakat A1 Hochformat_Vorlage.pdf:plakat" \
    "postkarte-vorlage-original.sla:/root/workspace/originals/Postkarte Vorlage.pdf:postkarte"; do
  IFS=":" read -r sla refpdf tag <<< "$pair"
  out="$OUT_DIR/$tag"; mkdir -p "$out"
  xvfb-run -a --server-args="-screen 0 1024x768x24" \
    scribus -g -ns -py tools/_export_pdf.py "$(realpath "$sla")" "$out/headless.pdf"
  pdftoppm -r 96 -png "$out/headless.pdf" "$out/headless"
  pdftoppm -r 96 -png "$refpdf" "$out/ref"
  worst=0
  for f in "$out"/ref-*.png; do
    page=$(basename "$f" .png)
    diff_count=$(compare -metric AE -fuzz 0% "$f" "$out/headless-${page#ref-}.png" "$out/diff-${page#ref-}.png" 2>&1 || true)
    echo "$tag $page: $diff_count px"
    [ "$diff_count" -gt "$worst" ] 2>/dev/null && worst=$diff_count
  done
  echo "$tag worst-page mismatch: $worst px"
done
```

Set `OUT_DIR` per phase (`build/phase0-verify`, `build/phase2-cross-verify`, `build/phase9-final`). Render serially — `xvfb-run -a` parallelism is best-effort (RESEARCH.md §Risks #5).
</helper>

<helper id="sla_diff_strict">
Structural diff each template's DSL output against its corrected original, exit non-zero on critical OR warning. Used by Phase 1.1, 1.2, and Phase 9 (transitively via `bin/validate`).

```bash
python3 tools/sla_diff.py \
  --left "$ORIGINAL_SLA" \
  --right "$DSL_TEMPLATE_SLA" \
  --strict
```

Where `$ORIGINAL_SLA` is the workspace-root `<id>-original.sla` and `$DSL_TEMPLATE_SLA` is `templates/<id>/template.sla`.
</helper>

## Phase gates summary

| Phase | Goal | Gate (must be GREEN to advance) |
|---|---|---|
| 0 | Adopt corrected SLAs into worktree + verify | `git diff` on the three SLAs shows expected deltas (Zeitung: 97 FONTSIZE 11.7→12 in PAGEOBJECT ITEXTs; Plakat/Postkarte: byte-identical or trivial); helper `render_and_pixeldiff` reports 0 px on all 17 pages. |
| 1 | Regenerate Zeitung build.py + assets via converter; verify Plakat + Postkarte | helper `sla_diff_strict` exits 0 for all three templates; the regenerated Zeitung `build.py` has zero `fontsize=11.7` literals. |
| 2 | Regenerate `templates/<id>/baseline.pdf` for all three | `bin/validate` (default 150 dpi) exits 0 for all three templates; per-template visual_diff worst-page ≤3 px; `pdffonts <baseline>` shows Gotham/Vollkorn embedded (no DejaVu). |
| 3 | Wire fonts + fontconfig alias into `Dockerfile.claude` | Image rebuilds successfully both with and without `fonts/` in build context; with-fonts image has `fc-list \| grep -ciE 'gotham narrow\|vollkorn'` ≥ 5 and `fc-match "Vollkorn Black Italic"` resolves to `Vollkorn-BlackItalic.ttf`. |
| 4 | SLA path references review (post-Phase 0 sanity) | Every `git grep` reference to `*-original.sla` resolves to an existing file; `bin/validate` still exits 0. |
| 5 | `bin/check-fontsizes` regression checker | New script exits 0 against the corrected workspace-root SLAs; exits 1 against a synthetic SLA with PAGEOBJECT FONTSIZE="11.5"; `bin/validate` invokes it as a preflight. |
| 6 | `docs/render-fidelity.md` | File exists, covers all D6 topics, cross-links to `shared/fonts/README.md`. |
| 7 | `.github/workflows/pages.yml` — drop visual_diff CI step | Workflow YAML still parses; `validate-reproductions` step now runs sla_diff only; TODO comment present; orphan `Upload visual-diff composites` step removed. |
| 8 | `shared/fonts/README.md` — update for new layout | README points at `fonts/` (not the historical install paths); install path matches `Dockerfile.claude` reality; cross-links `docs/render-fidelity.md`. |
| 9 | Final verification | `bin/validate`, `bin/validate --ci`, `bin/check-fontsizes`, full unit-test discovery, and `render_and_pixeldiff` all exit 0; 0-px mismatch on every page. |

Each phase's tasks are below. **Do not advance past a phase whose gate is red.** `risk="high"` tasks need explicit verification before marking done.

## Phases

<phase id="0" name="Adopt corrected SLAs into worktree">

The user re-saved the corrected SLAs into `/root/workspace/originals/` (umlaut-named). The committed workspace-root files are stale (Zeitung) or byte-identical (Plakat, Postkarte). This phase swaps in the corrected content while preserving filenames so the test suite, `meta.yml::original_sla`, and `bin/validate` references all keep working unchanged.

**RESEARCH.md anchors:** §Codebase Analysis (table at lines 56–64), §Risks #1 (NFC/NFD ASCII rename rationale), §Risks #8 (FRAMEOBJECT vs STYLE precision).

<task id="0.1" name="Copy corrected SLAs from /root/workspace/originals/ → workspace root with ASCII names">
**Files:** `gruene-zeitung-vorlage-original.sla`, `plakat-a1-hochformat-original.sla`, `postkarte-vorlage-original.sla` (overwrite in place).

**Action:**

```bash
cp "/root/workspace/originals/Grüne Zeitung Vorlage Scribus.sla" gruene-zeitung-vorlage-original.sla
cp "/root/workspace/originals/Plakat A1 Hochformat_Vorlage.sla" plakat-a1-hochformat-original.sla
cp "/root/workspace/originals/Postkarte Vorlage.sla" postkarte-vorlage-original.sla
```

Strict resolution-1 path: `originals/` stays out of git. Do NOT copy reference PDFs (`originals/*.pdf`) into the worktree (resolution 3 — they're build artifacts).

**Verify:**
- `git status` shows three modified SLAs (no untracked, no new dirs).
- `git diff --stat gruene-zeitung-vorlage-original.sla` reports a non-zero diff.
- Plakat/Postkarte diff may be empty (CONTEXT.md + RESEARCH.md indicate they never had the typo).
- Zeitung PAGEOBJECT-scope `FONTSIZE="11.7"` count = 0 (was 97):
  ```bash
  python3 -c "
  from lxml import etree
  t = etree.parse('gruene-zeitung-vorlage-original.sla')
  doc = t.getroot().find('DOCUMENT')
  print('PAGEOBJECT FONTSIZE=11.7:', sum(1 for po in doc.findall('PAGEOBJECT') for it in po.iter('ITEXT') if it.get('FONTSIZE','') == '11.7'))
  print('FRAMEOBJECT FONTSIZE=11.7:', sum(1 for fo in doc.findall('FRAMEOBJECT') for it in fo.iter('ITEXT') if it.get('FONTSIZE','') == '11.7'))
  "
  ```
  Expect PAGEOBJECT=0, FRAMEOBJECT=42 (or whatever the corrected file has — RESEARCH.md §Risks #8: these are inert pasteboard items).

**Done:**
- Three workspace-root SLAs are byte-identical to the corrected SLAs in `originals/` (modulo filename).
- Zeitung PAGEOBJECT FONTSIZE=11.7 count is 0.
- No new files added to git tracking; no `originals/` directory created in the worktree.
</task>

<task id="0.2" name="Pixel-diff each new SLA's headless render against the user's reference PDF">
**Files:** none modified (verification only). Output goes under `build/phase0-verify/`.

**Action:** Run helper `render_and_pixeldiff` with `OUT_DIR=build/phase0-verify`. Re-verifies in-band of the pipeline what was confirmed manually during discuss: 0 px mismatch on all 17 pages × 3 templates against the user's reference PDFs.

If any page reports >0 px, STOP. Do not advance to Phase 1. Diagnose:
- `fc-list | grep -iE 'gotham narrow|vollkorn'` — fonts loaded?
- Re-check that the SLA copy was clean (`md5sum <root>/<id>-original.sla "/root/workspace/originals/<umlaut>.sla"`).
- Re-check that the reference PDF in `/root/workspace/originals/` matches what the user provided.

**Verify:** All pages report 0 px mismatch.

**Done:**
- 0-px mismatch confirmed across 17 pages × 3 templates.
- `build/phase0-verify/` contains per-page diffs (gitignored under `build/`).
</task>

<gate>
- `git status` shows three modified `*-original.sla` files at workspace root and nothing else.
- Zeitung `*-original.sla` has 0 PAGEOBJECT-scope `FONTSIZE="11.7"`.
- Headless render vs user's reference PDF: 0-px mismatch on all 17 pages.
- Phase 0 must be GREEN before regenerating any artifacts in Phase 1+.
</gate>

</phase>

<phase id="1" name="Regenerate templates/<id>/build.py via converter">

The Zeitung `build.py` was generated when the SLA had FONTSIZE=11.7 typos (RESEARCH.md §Risks #2). It hardcodes 97 `fontsize=11.7` Run(...) parameters across line 1146 onward. Until regenerated, `bin/validate`'s `sla_diff --strict` step reports 14 critical + 97 warning issues.

Plakat and Postkarte SLAs were unchanged content-wise (Phase 0's diff confirms); their build.py files are likely already clean. Re-run the converter on each to be certain; commit only if the regenerated output differs.

**RESEARCH.md anchors:** §Risks #2, §Open question #6 (converter wins).

<task id="1.1" name="Regenerate Zeitung build.py via tools/sla_to_dsl.py" risk="high">
**Files:** `templates/zeitung-a4-grun/build.py` (overwrite); `templates/zeitung-a4-grun/assets/*` (potentially refreshed); `templates/zeitung-a4-grun/template.sla` (rebuilt).

**Action:**

```bash
# Confirm CLI flags first; the names below match RESEARCH.md §Interfaces and
# the working invocation pattern from issue #2.
python3 tools/sla_to_dsl.py --help

python3 tools/sla_to_dsl.py \
  gruene-zeitung-vorlage-original.sla \
  templates/zeitung-a4-grun/build.py \
  --template-id zeitung-a4-grun \
  --assets-dir templates/zeitung-a4-grun/assets/

python3 templates/zeitung-a4-grun/build.py
```

**Verify:**
- `grep -c "fontsize=11.7" templates/zeitung-a4-grun/build.py` → must be 0 (was 97 across lines 1146+).
- `git diff templates/zeitung-a4-grun/build.py | grep -c '^-.*fontsize=11.7'` ≈ 97.
- helper `sla_diff_strict` with `ORIGINAL_SLA=gruene-zeitung-vorlage-original.sla DSL_TEMPLATE_SLA=templates/zeitung-a4-grun/template.sla` exits 0.
- `git diff --stat templates/zeitung-a4-grun/assets/` — image assets *should* be unchanged (text-only correction). Document any non-trivial asset bytes diff in the commit message.

**Done:**
- `build.py` no longer contains `fontsize=11.7` literals.
- `template.sla` byte-equivalent (modulo `sla_diff` normalisation) to the corrected `gruene-zeitung-vorlage-original.sla`.
- `sla_diff --strict` clean.
</task>

<task id="1.2" name="Re-run converter on Plakat + Postkarte; commit only if non-empty diff">
**Files:** `templates/plakat-a1-hochformat/build.py`, `templates/postkarte-a6-kampagne/build.py` (potentially overwritten).

**Action:** Generate to a `.regen` sidecar first to preserve the existing version for diffing:

```bash
for tid_pair in \
    "plakat-a1-hochformat:plakat-a1-hochformat-original.sla" \
    "postkarte-a6-kampagne:postkarte-vorlage-original.sla"; do
  IFS=":" read -r tid sla <<< "$tid_pair"
  python3 tools/sla_to_dsl.py "$sla" "templates/$tid/build.py.regen" \
    --template-id "$tid" --assets-dir "templates/$tid/assets/"
  if diff -q --ignore-matching-lines='^# generated' \
       "templates/$tid/build.py" "templates/$tid/build.py.regen" > /dev/null; then
    echo "$tid: build.py unchanged, removing .regen"
    rm "templates/$tid/build.py.regen"
  else
    echo "$tid: build.py CHANGED, replacing"
    mv "templates/$tid/build.py.regen" "templates/$tid/build.py"
  fi
  python3 "templates/$tid/build.py"
done
```

(`--ignore-matching-lines='^# generated'` skips the auto-gen header timestamp; adjust the regex if the converter emits a different header pattern.)

**Verify:** For each of Plakat and Postkarte, helper `sla_diff_strict` with the matching `ORIGINAL_SLA`/`DSL_TEMPLATE_SLA` pair exits 0. No `*.regen` sidecars left behind. `git status` shows whichever `build.py` files actually changed.

**Done:**
- Both Plakat and Postkarte `template.sla` regenerated cleanly via build.py.
- `sla_diff --strict` clean for both.
- `build.py` files committed only if their content actually changed.
</task>

<gate>
- helper `sla_diff_strict` exits 0 for all three (`zeitung`, `plakat`, `postkarte`) original→template pairs.
- Zeitung `build.py` has 0 occurrences of `fontsize=11.7`.
</gate>

</phase>

<phase id="2" name="Regenerate templates/<id>/baseline.pdf in font-installed env">

The currently-committed baselines were rendered before the brand fonts were installed (Apr/May, DejaVu fallback). They get replaced with fresh renders of the corrected SLAs in this container's font-installed env (`/root/.local/share/fonts/gruene/` populated, fontconfig alias active). Each new `templates/<id>/baseline.pdf` is byte-equivalent to the user's reference PDF in `/root/workspace/originals/<id>.pdf`.

**RESEARCH.md anchors:** `tools/visual_diff.py::render_sla_to_pdf`, §CI Workflow Impact (asymmetry table line 416).

<task id="2.1" name="Sanity-check the running container's font state">
**Files:** none.

**Action:**
```bash
fc-list | grep -ciE 'gotham narrow|vollkorn'   # expect ≥ 5
fc-match "Vollkorn Black Italic"               # expect: …Vollkorn-BlackItalic.ttf…
fc-match "Gotham Narrow Book"                  # expect: …GothamNarrow-Book.otf…
```

If any check fails, the running container is missing fonts. Re-install per CONTEXT.md drift cause 1: copy from `/root/workspace/fonts/` into `/root/.local/share/fonts/gruene/`, run `fc-cache -f`, install the alias at `~/.config/fontconfig/conf.d/50-vollkorn-family-alias.conf`. (Runtime fix-up; the durable Dockerfile install is Phase 3.)

**Verify:** all three commands report the expected family.

**Done:** Brand fonts confirmed loaded in the live environment.
</task>

<task id="2.2" name="Regenerate templates/<id>/baseline.pdf via headless Scribus" risk="high">
**Files:** `templates/zeitung-a4-grun/baseline.pdf`, `templates/plakat-a1-hochformat/baseline.pdf`, `templates/postkarte-a6-kampagne/baseline.pdf` (overwrite).

**Action:**

```bash
for pair in \
    "gruene-zeitung-vorlage-original.sla:templates/zeitung-a4-grun/baseline.pdf" \
    "plakat-a1-hochformat-original.sla:templates/plakat-a1-hochformat/baseline.pdf" \
    "postkarte-vorlage-original.sla:templates/postkarte-a6-kampagne/baseline.pdf"; do
  IFS=":" read -r sla pdf <<< "$pair"
  xvfb-run -a --server-args="-screen 0 1024x768x24" \
    scribus -g -ns -py tools/_export_pdf.py "$(realpath "$sla")" "$(realpath "$pdf")"
  echo "Rendered: $pdf ($(stat -c%s "$pdf") bytes)"
done
```

Render serially (RESEARCH.md §Risks #5).

**Verify:**
- Three `baseline.pdf` files exist with non-zero sizes.
- `git diff --stat` shows them modified.
- `pdffonts templates/<id>/baseline.pdf` lists `Gotham Narrow*` and `Vollkorn` faces, NOT DejaVu (the previous baseline was DejaVu; if the new file lists DejaVu the renderer didn't see the fonts → Task 2.1 must be re-checked).

**Done:**
- Three regenerated `baseline.pdf` files staged.
- `pdffonts` on each shows brand fonts embedded.
</task>

<task id="2.3" name="Verify new baselines via bin/validate at 150 dpi" risk="high">
**Files:** none modified. Output under `build/validation/`.

**Action:** `bin/validate`. Invokes `sla_diff --strict` (Phase 1 already verified) plus `visual_diff` at default 150 dpi for each template. Per CONTEXT.md "What done looks like" #3 and PR #5: worst-page mismatch ≤3 px per template at 150 dpi (Qt anti-aliasing floor).

If any template fails: do NOT loosen `diff.yml` thresholds (resolution 6). Inspect `build/validation/<tid>/composite-page-N.png` and `delta-page-N.png`. Likely culprits: (a) SLA references a font weight not in the install (re-check `fc-list`); (b) Vollkorn variable file lingering alongside the static (RESEARCH.md §Risks #3); (c) a residual fractional FONTSIZE somewhere `bin/check-fontsizes` would flag (introduced in Phase 5; can be run manually now if needed).

**Verify:**
- `bin/validate` exits 0.
- Per-template log lines show `sla_diff: PASS` and `visual_diff (150dpi): PASS` for all three.
- `build/validation/*-sla_diff.json` show no critical/warning entries.

**Done:** `bin/validate` green at 150 dpi for all three templates.
</task>

<task id="2.4" name="Cross-verify new baseline.pdf vs user's reference PDF (byte-equivalence claim)">
**Files:** none modified. Output under `build/phase2-cross-verify/`.

**Action:** Confirm CONTEXT.md "What done looks like" #1 + D5: each `templates/<id>/baseline.pdf` is byte-equivalent (rasterised at 0% fuzz) to the user's reference PDF.

```bash
mkdir -p build/phase2-cross-verify
for pair in \
    "templates/zeitung-a4-grun/baseline.pdf:/root/workspace/originals/Grüne Zeitung Vorlage Scribus.pdf:zeitung" \
    "templates/plakat-a1-hochformat/baseline.pdf:/root/workspace/originals/Plakat A1 Hochformat_Vorlage.pdf:plakat" \
    "templates/postkarte-a6-kampagne/baseline.pdf:/root/workspace/originals/Postkarte Vorlage.pdf:postkarte"; do
  IFS=":" read -r ours theirs tag <<< "$pair"
  out="build/phase2-cross-verify/$tag"; mkdir -p "$out"
  pdftoppm -r 96 -png "$ours" "$out/ours"
  pdftoppm -r 96 -png "$theirs" "$out/theirs"
  for f in "$out"/theirs-*.png; do
    page=${f##*/theirs-}
    diff_count=$(compare -metric AE -fuzz 0% "$f" "$out/ours-$page" "$out/diff-$page" 2>&1 || true)
    echo "$tag page-$page: $diff_count px"
  done
done
```

Expect 0 px on every page.

**Verify:** every page reports 0 px mismatch.

**Done:** Byte-equivalence of regenerated baselines vs user's reference PDFs proven across all 17 pages.
</task>

<gate>
- `bin/validate` exits 0 (sla_diff + visual_diff at 150 dpi green).
- Worst-page mismatch ≤3 px per template.
- `pdffonts` on each `baseline.pdf` lists Gotham Narrow + Vollkorn.
- 0-px mismatch between each `templates/<id>/baseline.pdf` and the user's matching `originals/<id>.pdf` reference.
</gate>

</phase>

<phase id="3" name="Wire fonts + fontconfig alias into Dockerfile.claude">

Persist runtime font-install state into `Dockerfile.claude`. Use the conditional-COPY pattern (RESEARCH.md §Dockerfile font-install mechanics, Option A) — works without BuildKit, no-ops gracefully when `fonts/` is absent (CI / public clones).

**RESEARCH.md anchors:** §Dockerfile font-install mechanics (lines 236–334), §Risks #6 (CI build context).

<task id="3.1" name="Commit fontconfig alias source to shared/fonts/">
**Files:** `shared/fonts/50-vollkorn-family-alias.conf` (new).

**Action:** Mirror `~/.config/fontconfig/conf.d/50-vollkorn-family-alias.conf` (RESEARCH.md lines 242–254) verbatim:

```xml
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <match target="pattern">
    <test name="family"><string>Vollkorn Black Italic</string></test>
    <edit name="family" mode="assign"><string>Vollkorn</string></edit>
    <edit name="style"  mode="assign"><string>Black Italic</string></edit>
    <edit name="weight" mode="assign"><const>black</const></edit>
    <edit name="slant"  mode="assign"><const>italic</const></edit>
  </match>
</fontconfig>
```

Lead with an XML comment explaining: why the alias exists (Scribus references "Vollkorn Black Italic" as a family name; the static font registers as family=Vollkorn + style="Black Italic"), where it gets installed by the Dockerfile (`/etc/fonts/conf.d/50-vollkorn-family-alias.conf`), and what to verify (`fc-match "Vollkorn Black Italic"` resolves to `Vollkorn-BlackItalic.ttf`).

**Verify:**
- `xmllint --noout shared/fonts/50-vollkorn-family-alias.conf` exits 0.

**Done:** File committed at `shared/fonts/50-vollkorn-family-alias.conf`.
</task>

<task id="3.2" name="Add font-install layer to Dockerfile.claude" risk="high">
**Files:** `Dockerfile.claude`.

**Action:** Insert two new layers between the current line 50 (`apt-get clean ...`) and line 53 (the ImageMagick policy patch). Layer 1 conditionally COPYs `fonts/` into staging and installs into `/usr/local/share/fonts/gruene/`; Layer 2 installs the fontconfig alias.

```dockerfile
# Brand fonts (proprietary Gotham Narrow, OFL Vollkorn). Source files at
# /root/workspace/fonts/ are gitignored; this layer only fires when the build
# context contains a fonts/ directory (local dev). When fonts/ is absent
# (CI, public clones), the staging dir is empty and we no-op gracefully.
#
# Sanity probe at the end fails LOUD if fonts/ was present but the install
# didn't register the expected font count — protects against silent DejaVu
# fallback in the dev container.
COPY fonts* /tmp/fonts-staging/
RUN set -e; \
    if [ -d /tmp/fonts-staging ] && [ -n "$(ls -A /tmp/fonts-staging 2>/dev/null)" ]; then \
        mkdir -p /usr/local/share/fonts/gruene; \
        find /tmp/fonts-staging -type f \( -iname '*.otf' -o -iname '*.ttf' \) \
            -exec install -m 644 {} /usr/local/share/fonts/gruene/ \; ; \
        fc-cache -f; \
        N=$(fc-list | grep -ciE 'gotham narrow|vollkorn' || true); \
        if [ "$N" -lt 5 ]; then \
            echo "FONT INSTALL FAILED: only $N font faces registered (expected ≥ 5)" >&2; \
            exit 1; \
        fi; \
        echo "Brand fonts installed: $N faces"; \
    else \
        echo "No fonts/ in build context — DejaVu-only image (CI / public clone path)"; \
    fi; \
    rm -rf /tmp/fonts-staging

# Fontconfig family-name alias. Scribus references Vollkorn Black Italic as a
# family; the static font ships with family=Vollkorn + style="Black Italic".
COPY shared/fonts/50-vollkorn-family-alias.conf /etc/fonts/conf.d/50-vollkorn-family-alias.conf
RUN fc-cache -f && \
    if fc-list | grep -qiE 'vollkorn'; then \
        fc-match "Vollkorn Black Italic" | grep -qi 'Vollkorn-BlackItalic' || \
            { echo "Vollkorn alias not resolving to Vollkorn-BlackItalic.ttf" >&2; exit 1; }; \
    else \
        echo "Vollkorn not installed — skipping alias resolution check"; \
    fi
```

Notes:
- `COPY fonts* /tmp/fonts-staging/` uses a wildcard so the build doesn't fail when `fonts/` is absent (the `*` matches zero or more). Validate this works in your Docker version during build; if it errors with "no source files were specified", fall back to keeping a `fonts/.gitkeep` placeholder.
- The alias-resolution check is gated on Vollkorn being installed so the layer doesn't fail in font-less CI builds.
- Do NOT pre-populate `~/.config/scribus/checkfonts150.xml` (RESEARCH.md §Scribus font cache caveat).

**Verify:**

```bash
# Build with fonts present (build context = parent workspace where fonts/ lives):
docker build -f Dockerfile.claude -t scribus-pipeline-dev /root/workspace
docker run --rm scribus-pipeline-dev fc-list | grep -ciE 'gotham narrow|vollkorn'   # expect ≥ 5
docker run --rm scribus-pipeline-dev fc-match "Vollkorn Black Italic"               # expect: …Vollkorn-BlackItalic.ttf…

# Build with fonts absent (build context = worktree alone, fonts/ gitignored at root):
docker build -f Dockerfile.claude -t scribus-pipeline-nofonts \
  /root/workspace/.worktrees/3-render-fidelity-ground-truth-match-users-scribus-164-export-with-proper-brand-fo
docker run --rm scribus-pipeline-nofonts fc-list | grep -ciE 'gotham narrow|vollkorn'   # expect 0
```

Both builds must succeed.

**Done:**
- `Dockerfile.claude` extended with two new layers.
- Build succeeds both with and without `fonts/` in context.
- With-fonts image's `fc-list` reports ≥ 5 brand faces; alias resolves correctly.
</task>

<gate>
- Two image rebuilds tested (with-fonts + without-fonts) both succeed.
- With-fonts image's font checks all pass.
- Without-fonts image is functional but DejaVu-only.
</gate>

</phase>

<phase id="4" name="SLA path references review (post-Phase 0 sanity)">

Phase 0 preserved all filenames so this phase is mostly verification. Confirm every reference still resolves and `bin/validate` still exits 0.

**RESEARCH.md anchors:** §Codebase Analysis "Files that hardcode the old workspace-root SLA paths" table (lines 67–89).

<task id="4.1" name="Walk every reference enumerated in RESEARCH.md and verify">
**Files:** none modified (verification + spot fixes only).

**Action:**

```bash
# Test fixtures resolve:
python3 -c "
from pathlib import Path
ROOT = Path('.')
for f in ['gruene-zeitung-vorlage-original.sla', 'plakat-a1-hochformat-original.sla', 'postkarte-vorlage-original.sla']:
    assert (ROOT / f).exists(), f'missing: {f}'
    print(f'ok: {f}')
"

# meta.yml original_sla resolves (mirrors bin/validate logic):
for tid in postkarte-a6-kampagne plakat-a1-hochformat zeitung-a4-grun; do
  python3 -c "
import os, yaml
m = yaml.safe_load(open('templates/$tid/meta.yml'))
rel = m.get('original_sla', '')
p = os.path.normpath(os.path.join('templates/$tid', rel))
print('$tid →', p, '→', 'OK' if os.path.exists(p) else 'MISSING')
"
done

bin/validate
```

If any reference is broken, fix it now (typically: `templates/<id>/meta.yml::original_sla`). Spot-edits only — Phase 0's filename-preservation strategy means no edits should be needed.

**Verify:**
- `ls -1 *-original.sla` → 3 files.
- All three meta.yml `original_sla` resolutions succeed.
- `bin/validate` exits 0.

**Done:**
- All workspace-root SLA references audit clean.
- `bin/validate` re-confirms green.
</task>

<gate>
- All file references resolve to existing files.
- `bin/validate` still exits 0.
</gate>

</phase>

<phase id="5" name="bin/check-fontsizes regression checker">

Per resolution 8 / RESEARCH.md §"bin/validate change required": add a PAGEOBJECT-scoped fractional-FONTSIZE checker so a future SLA edit re-introducing the typo is caught loudly. Hook into `bin/validate` as a preflight.

**RESEARCH.md anchors:** §"bin/validate change required" (lines 338–375), §Risks #8 (must scope to PAGEOBJECT only).

<task id="5.1" name="Implement bin/check-fontsizes">
**Files:** `bin/check-fontsizes` (new, executable).

**Action:** Create a Python script (POSIX-shell-callable) that walks PAGEOBJECT subtrees only, ignoring FRAMEOBJECT and MASTEROBJECT.

```python
#!/usr/bin/env python3
"""bin/check-fontsizes — fail-loud regression check for fractional ITEXT FONTSIZE
inside PAGEOBJECT subtrees of any SLA file.

Scope: PAGEOBJECT only. FRAMEOBJECT (orphan/pasteboard, OwnPage=-1) and
MASTEROBJECT are ignored — those are dropped by tools/sla_diff.py:drop_frameobjects
and aren't rendered onto pages.

Usage:
    bin/check-fontsizes [<sla>...]      # default: all *-original.sla at repo root
Exit:
    0 — clean
    1 — at least one fractional FONTSIZE in a PAGEOBJECT
"""
import sys
from pathlib import Path
from lxml import etree


def check(paths: list[Path]) -> int:
    bad: list[str] = []
    for p in paths:
        if not p.exists():
            print(f"warning: {p} does not exist; skipping", file=sys.stderr)
            continue
        tree = etree.parse(str(p))
        doc = tree.getroot().find("DOCUMENT")
        if doc is None:
            print(f"warning: {p} has no DOCUMENT; skipping", file=sys.stderr)
            continue
        for po in doc.findall("PAGEOBJECT"):
            for it in po.iter("ITEXT"):
                fs = it.get("FONTSIZE", "")
                if "." in fs:
                    bad.append(f"{p}: PAGEOBJECT[OwnPage={po.get('OwnPage','?')}] ITEXT FONTSIZE={fs!r}")
    if bad:
        print("Fractional FONTSIZE in rendered text (PAGEOBJECT scope):", file=sys.stderr)
        for b in bad:
            print(f"  {b}", file=sys.stderr)
        print(
            '\nFix at the source: open the SLA in Scribus, correct the FONTSIZE on the\n'
            'flagged frames to an integer point size, and re-save. See docs/render-fidelity.md\n'
            '"The fix-typos-at-the-source principle" for context.',
            file=sys.stderr,
        )
        return 1
    return 0


def main() -> int:
    args = [Path(p) for p in sys.argv[1:]]
    if not args:
        repo = Path(__file__).resolve().parent.parent
        args = sorted(repo.glob("*-original.sla"))
        if not args:
            print("no *-original.sla files found at repo root", file=sys.stderr)
            return 1
    return check(args)


if __name__ == "__main__":
    sys.exit(main())
```

`chmod +x bin/check-fontsizes`.

**Verify:**

- `bin/check-fontsizes` (no args) exits 0 against the corrected workspace-root SLAs.
- Synthetic regression: copy a corrected SLA, set one PAGEOBJECT ITEXT FONTSIZE to "11.5", confirm the checker exits 1 against it. Then delete the fixture.
  ```bash
  cp gruene-zeitung-vorlage-original.sla /tmp/regression-fixture.sla
  python3 -c "
  from lxml import etree
  t = etree.parse('/tmp/regression-fixture.sla')
  it = next(t.getroot().find('DOCUMENT').find('PAGEOBJECT').iter('ITEXT'))
  it.set('FONTSIZE', '11.5')
  t.write('/tmp/regression-fixture.sla', xml_declaration=True, encoding='UTF-8')
  "
  bin/check-fontsizes /tmp/regression-fixture.sla   # must exit 1
  rm /tmp/regression-fixture.sla
  ```
- Confirm the 42 FRAMEOBJECT-scope FONTSIZE=11.7 strings (RESEARCH.md §Risks #8) do NOT trigger the checker (default invocation is clean even though `grep -c 'FONTSIZE="11.7"' gruene-zeitung-vorlage-original.sla` returns 42).

**Done:**
- `bin/check-fontsizes` executable and behaves as specified.
- Synthetic regression caught (exit 1).
- Default invocation against current corrected SLAs is clean.
</task>

<task id="5.2" name="Hook bin/check-fontsizes into bin/validate as a preflight">
**Files:** `bin/validate` (modify).

**Action:** Insert a preflight invocation immediately after `mkdir -p "$OUT_BASE"` (current line 22) and before the `for tdir in templates/*/;` loop (current line 25):

```bash
echo "=== preflight: bin/check-fontsizes ==="
if ! "$ROOT/bin/check-fontsizes"; then
    echo "preflight FAILED — fix fractional FONTSIZE in SLA before continuing" >&2
    exit 1
fi
echo "preflight: PASS"
echo
```

This makes `bin/validate` exit 1 immediately if any workspace-root `*-original.sla` has a PAGEOBJECT-scope fractional FONTSIZE.

**Verify:**
- `bin/validate` still exits 0 against the current corrected SLAs.
- Synthetic regression: temporarily corrupt one workspace-root SLA in a sandbox copy and confirm `bin/validate` exits 1 at the preflight step before reaching the per-template loop. Restore.

**Done:**
- `bin/validate` invokes `bin/check-fontsizes` as a preflight.
- Validation pipeline gates on the regression check.
</task>

<gate>
- `bin/check-fontsizes` exists, is executable, PAGEOBJECT-scoped only.
- Default invocation exits 0; synthetic regression exits 1.
- `bin/validate` runs the preflight first.
</gate>

</phase>

<phase id="6" name="docs/render-fidelity.md">

Document the chain so a future contributor (or future-you) can reproduce the state, debug drift, and rebaseline without rediscovering the four drift causes.

**RESEARCH.md anchors:** §"docs/render-fidelity.md structure recommendation" (lines 494–543).

<task id="6.1" name="Write docs/render-fidelity.md">
**Files:** `docs/render-fidelity.md` (new).

**Action:** Cover all D6 topics. Use the structure RESEARCH.md proposes (lines 498–543) as a starting skeleton; expand to flow naturally. Required sections:

1. **Why fonts must be installed** — DejaVu fallback drifts ~55,000 px/page; brand fonts collapse to 0 px. Mention the `~/.config/scribus/checkfonts150.xml` per-user cache regeneration on first scribus run after font changes (RESEARCH.md §Scribus font cache caveat).
2. **What's installed and where** —
   - `/usr/local/share/fonts/gruene/`: 16 Gotham Narrow .otf + Vollkorn-BlackItalic.ttf
   - `/etc/fonts/conf.d/50-vollkorn-family-alias.conf`: maps `Vollkorn Black Italic` family → `Vollkorn / Black Italic`
   - Source files: `/root/workspace/fonts/` (gitignored; user-controlled drop zone)
   - Verification: `fc-list | grep -ciE 'gotham narrow|vollkorn'` → ≥ 5
3. **Why static, not variable, Vollkorn** — RESEARCH.md §Risks #3. Static `Vollkorn-BlackItalic.ttf` glyph metrics differ from Google Fonts variable `Vollkorn-Italic[wght].ttf` instantiated at weight=black. Don't install both.
4. **The "fix typos at the source, not the renderer" principle (D1 lesson)** —
   - Zeitung had FONTSIZE="11.7" on 97 PAGEOBJECT body-text ITEXTs (mouse-wheel nudge in Scribus's properties panel).
   - User's Scribus 1.6.4 silently rounds 11.7 → 11.0 in PDF output; our 1.6.3 honors 11.7 literally. Renderer-version difference was a *symptom*, not the cause.
   - Fix: user corrected the SLA in their Scribus (FONTSIZE=12). The renderer was never wrong.
   - 42 lingering FONTSIZE=11.7 strings remain inside `<FRAMEOBJECT>` pasteboard frames — irrelevant (not rendered, dropped by `tools/sla_diff.py::drop_frameobjects`). RESEARCH.md §Risks #8 — note that CONTEXT.md mis-described these as STYLE definitions; clarify here they are FRAMEOBJECTs.
   - Regression check: `bin/check-fontsizes` (PAGEOBJECT-scoped) runs as a preflight inside `bin/validate`.
5. **Adding a new font to fonts/** —
   1. Drop the file at `/root/workspace/fonts/<family>/...`
   2. Rebuild dev container (`docker build -f Dockerfile.claude /root/workspace -t scribus-pipeline-dev`).
   3. `docker run --rm scribus-pipeline-dev fc-list | grep "<family>"` to verify.
   4. If Scribus references the font by a non-standard family name, add a fontconfig alias at `shared/fonts/<NN>-<family>-alias.conf` (numeric prefix `50-` is standard).
6. **Rebaselining a template's baseline.pdf (gated procedure)** —
   - WHEN: original SLA changes intentionally, Scribus version bumps, or fonts change.
   - HOW: render via the headless pipeline:
     ```
     xvfb-run -a --server-args="-screen 0 1024x768x24" \
       scribus -g -ns -py tools/_export_pdf.py \
       <id>-original.sla templates/<id>/baseline.pdf
     ```
   - VERIFY: `bin/validate` exits 0 (≤3 px per template at 150 dpi).
   - DOCUMENT: a short note in the rebaseline commit message describing what changed and why.
   - NOT CASUAL: don't rebaseline to "make tests pass" without understanding the underlying drift.
7. **Verifying a new SLA render matches your desktop Scribus export** —
   1. Drop your reference PDF at `/tmp/desktop.pdf`.
   2. `xvfb-run -a scribus -g -ns -py tools/_export_pdf.py your.sla /tmp/headless.pdf`.
   3. `pdftoppm -r 96 -png /tmp/desktop.pdf desktop && pdftoppm -r 96 -png /tmp/headless.pdf headless`.
   4. `for f in desktop-*.png; do compare -metric AE -fuzz 0% "$f" "${f/desktop/headless}" diff-$f 2>&1; done`.
   5. Expect 0 px per page (or document the drift root-cause).
8. **Out of scope (tracked elsewhere)** —
   - ECI ICC profile install — cosmetic; substitutes are symmetric across desktop/container.
   - CI font provisioning — separate follow-up issue (D7 + RESEARCH.md §Open question 4); CI currently runs structural sla_diff only.
   - Bundling Gotham Narrow into the public repo — license-blocked.
9. **Cross-links** — link to `shared/fonts/README.md` (install dance for direct contributors) and to `docs/diff-tolerance.md` (rebaselining workflow already partly there from issue #2).

**Verify:**
- `cat docs/render-fidelity.md | wc -l` → reasonably-sized doc (target 150–250 lines).
- All section headers present (`grep -c '^##' docs/render-fidelity.md` matches the section count).
- Cross-links resolve (`grep -E 'shared/fonts/README.md|docs/diff-tolerance.md' docs/render-fidelity.md`).
- No "claude" attribution (`grep -ci claude docs/render-fidelity.md` → 0).

**Done:**
- `docs/render-fidelity.md` covers all 9 sections.
- Cross-links present.
- No tool-attribution leakage.
</task>

<gate>
- `docs/render-fidelity.md` exists with all required sections.
- Manual read confirms it explains the chain end-to-end.
</gate>

</phase>

<phase id="7" name=".github/workflows/pages.yml — drop visual_diff CI step">

CI doesn't have brand fonts (D7). With Phase 2's font-bundled baselines, CI-side font-less DSL render diffs catastrophically against committed baseline (RESEARCH.md §CI Workflow Impact, asymmetry table line 416). Drop visual_diff from `validate-reproductions`; keep `sla_diff --strict`. A follow-up CI-fonts issue restores visual_diff.

**RESEARCH.md anchors:** §CI Workflow Impact (lines 408–442), §Open question 4 (resolution: outright remove).

<task id="7.1" name="Surgically remove visual_diff invocation from validate-reproductions step" risk="high">
**Files:** `.github/workflows/pages.yml`.

**Action:** Edit the `Validate reproductions` step (currently lines 93–122). Remove the visual_diff invocation block (lines 115–121, the `echo "=== visual_diff $tid (96 dpi) ===" ... --out "build/validation/$tid/"`). Keep:

- `set -euo pipefail`
- `mkdir -p build/validation`
- The for-loop over the three template dirs
- The `original=$(python3 ...)` heredoc
- `mkdir -p "build/validation/$tid"`
- `echo "=== sla_diff $tid ==="` + the `python3 tools/sla_diff.py --strict` invocation

Add a TODO comment block immediately above the deleted visual_diff position:

```yaml
            # NOTE: visual_diff is intentionally NOT run in CI. CI lacks the
            # proprietary Gotham Narrow brand fonts; rendering DSL output
            # without them and comparing against font-bundled baseline.pdf
            # would fail catastrophically. Structural sla_diff above is the
            # gate. See docs/render-fidelity.md "Out of scope" for context.
            # TODO: restore visual_diff in CI once brand fonts are
            # provisioned (follow-up issue tracking CI font provisioning).
```

Also remove the now-orphan `Upload visual-diff composites on failure` step (currently lines 124–130).

**Verify:**
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml'))"` exits 0 (well-formed YAML).
- `grep -c "visual_diff.py" .github/workflows/pages.yml` → 0.
- `grep -c "sla_diff.py" .github/workflows/pages.yml` → 1 (still present in `validate-reproductions`).
- TODO comment is present.
- `grep -c "visual-diff-composites" .github/workflows/pages.yml` → 0.

**Done:**
- `validate-reproductions` step now runs sla_diff only.
- Workflow YAML still parses.
- TODO comment in place.
- Orphan visual-diff upload step removed.
</task>

<task id="7.2" name="Create follow-up issue tracking CI visual_diff restoration" risk="high">
**Files:** writes a new issue under `.issues/` via the issue-cli; this PR commits its scaffold.

**Why this is in this PR:** the user explicitly said visual_diff in CI is non-negotiable going forward — it must be restored, not silently deferred. The TODO comment in 7.1 is too easy to lose. An issue file is a load-bearing tracker.

**Action:** invoke `issue-cli` to scaffold a new issue with the title and body below. Use the same pipeline that issue #3 used: `issue-cli store next-id` → `issue-cli slugify` → `issue-cli store create --slug <slug> --id <id> --title <title> --body-file <body.md> --priority high --labels rendering,fonts,validation,ci`.

**Title:** `Restore visual_diff in CI by provisioning brand fonts`

**Body content (write to a tempfile and pass via `--body-file`):**

```markdown
## Goal

CI currently runs only `sla_diff --strict` (the structural gate). Visual rendering fidelity in CI requires the brand fonts (Gotham Narrow proprietary + Vollkorn OFL) to be installed in the runner. Without them, DSL-rendered output uses DejaVu fallback and diverges catastrophically from the font-bundled `templates/<id>/baseline.pdf` committed in PR for issue #3.

This issue: restore the `visual_diff` invocation in `.github/workflows/pages.yml`'s `validate-reproductions` step, gated on a CI-side font-install step that obtains Gotham Narrow from a license-clean private channel.

## Why

- Visual fidelity is the user-facing quality bar; structural diff alone misses entire classes of rendering regression.
- Issue #3 established that with the right fonts the dev-container renders byte-identical to the user's Scribus 1.6.4 export. CI should match.
- The TODO comment in `pages.yml` (added in #3) is not enough — it'll rot.

## Scope

1. Decide CI font-source mechanism: private GitHub repo + PAT secret; S3 + AWS creds; encrypted artifact attached to the workflow. Pick one based on user authorisation pattern.
2. Add a `Install brand fonts (CI)` step to `pages.yml` before `Validate reproductions`. Mirror the local Dockerfile.claude pattern: copy fonts into `/usr/local/share/fonts/gruene/` + `fc-cache -f` + sanity-probe `fc-list | grep -iE 'gotham narrow|vollkorn'` (fail-loud on missing).
3. Install the fontconfig alias from `shared/fonts/50-vollkorn-family-alias.conf`.
4. Restore the `visual_diff` invocation (currently removed) inside the `Validate reproductions` step.
5. Restore the `Upload visual-diff composites on failure` step.
6. Verify on a deliberate-drift PR that visual_diff fails the build and uploads composites; on a clean PR it passes.
7. Update `docs/render-fidelity.md` "Out of scope" and "CI font provisioning" sections to reflect the new state.

## Acceptance Criteria

- [ ] CI workflow installs brand fonts from a license-clean private channel
- [ ] `fc-list | grep -iE 'gotham narrow|vollkorn'` reports the expected count in CI; missing fonts fail the build
- [ ] `validate-reproductions` runs both `sla_diff --strict` AND `visual_diff` per template
- [ ] `Upload visual-diff composites on failure` step is restored
- [ ] Deliberate-drift CI run uploads composites and fails; clean CI run passes
- [ ] `docs/render-fidelity.md` updated to remove the "CI is font-less" caveat
- [ ] Issue #3's `pages.yml` TODO comment is removed (workflow comments now reflect restored state)

## Out of Scope

- Local dev-container font work (already done in issue #3)
- New SLA fixes or DSL changes (separate concerns)

## Notes / Pointers

- Predecessor: issue #3 (`Render-fidelity ground truth: match user's Scribus 1.6.4 export with proper brand fonts`) — establishes local fidelity, sets up `Dockerfile.claude` font install, removes visual_diff from CI as a stop-gap
- Reference for the local pattern: `shared/fonts/50-vollkorn-family-alias.conf` + `Dockerfile.claude`'s font-install RUN block
- The TODO comment to remove lives at `.github/workflows/pages.yml`'s `validate-reproductions` step, just above where visual_diff was invoked
- Researcher's note (issue #3 RESEARCH.md §CI Workflow Impact, line 408+): visual_diff invocation block is currently lines 115–121 of `pages.yml` — restore in same position with the new font-availability precondition
```

**Verify:**
- `ls .issues/<new-slug>/ISSUE.md` exists in the worktree (committed alongside Phase 7.1's workflow change)
- `issue-cli store load <new-slug> --json` parses cleanly
- The issue's body matches the spec above (no AI-tool attribution; per-line accurate)
- The TODO comment in `pages.yml` (added by 7.1) references this issue's slug or numeric id

**Done:**
- New issue scaffold committed with the create-issue commit format `<id>: docs(issues): create issue <slug>`
- The Phase 7.1 TODO comment now points at this concrete tracker, not a hypothetical
</task>

<gate>
- Workflow YAML is well-formed.
- visual_diff is gone from CI; sla_diff stays as the structural gate.
- TODO comment present **and references the new follow-up issue by slug or numeric id**.
- Follow-up issue file exists, parses, and contains the body specified above.
</gate>

</phase>

<phase id="8" name="shared/fonts/README.md — update for new layout">

Current `shared/fonts/README.md` (37 lines) documents an install procedure pointing at `/usr/share/fonts/truetype/gruene/` (Linux). The Linux path no longer matches reality — the Dockerfile installs to `/usr/local/share/fonts/gruene/` and the source dir is `/root/workspace/fonts/`. Update for accuracy.

<task id="8.1" name="Update shared/fonts/README.md to reflect /root/workspace/fonts/ layout">
**Files:** `shared/fonts/README.md`.

**Action:** Rewrite while preserving the German-language voice. Required content:

- Same intro (which fonts are used, license note about Gotham being proprietary).
- **Drop zone:** `/root/workspace/fonts/` is the user's font drop zone (gitignored). Install tree:
  - `fonts/Gotham Narrow/<weight>/<weight>.otf` (16 files, all weights)
  - `fonts/Vollkorn/static/Vollkorn-BlackItalic.ttf` (the static instance — RESEARCH.md §Risks #3, do not use the variable file)
  - Optionally `fonts/Vollkorn/static/Vollkorn-*.ttf` for future templates
- **Container install:** `Dockerfile.claude` COPYs `fonts*` into staging and installs at `/usr/local/share/fonts/gruene/` plus the alias at `/etc/fonts/conf.d/50-vollkorn-family-alias.conf` (mirror of `shared/fonts/50-vollkorn-family-alias.conf`).
- **Verification (matches Dockerfile sanity probe):** `fc-list | grep -ciE 'gotham narrow|vollkorn'` ≥ 5; `fc-match "Vollkorn Black Italic"` resolves to `Vollkorn-BlackItalic.ttf`.
- **macOS dev:** drop files into `~/Library/Fonts/` if you want desktop Scribus to see them too. Not required for the headless container path.
- **Cross-link:** `Siehe `docs/render-fidelity.md` für die vollständige Render-Fidelity-Pipeline (Schriften + ICC-Profile + Re-Baselining).`

Keep concise; this is a pointer doc, not the canonical reference.

**Verify:**
- `grep -E '/root/workspace/fonts/|/usr/local/share/fonts/gruene' shared/fonts/README.md` → at least one match each.
- `grep render-fidelity.md shared/fonts/README.md` → at least one match.
- `grep -ci claude shared/fonts/README.md` → 0.

**Done:**
- README points at the actual install layout.
- Cross-links the new render-fidelity doc.
</task>

<gate>
- `shared/fonts/README.md` documents reality.
- Cross-link present.
</gate>

</phase>

<phase id="9" name="Final verification">

Run the complete validation chain end to end, exactly the way a fresh executor would after pulling main.

<task id="9.1" name="Run the full validation chain">
**Files:** none modified.

**Action:**

```bash
# 1) Preflight regression check
bin/check-fontsizes

# 2) Full structural + visual round-trip at default 150 dpi
bin/validate

# 3) CI-mode (96 dpi)
bin/validate --ci

# 4) Unit tests (RESEARCH.md §Test impact assessment confirmed these pass once
#    Phase 1's Zeitung build.py regeneration is committed)
python3 -m unittest discover tools/sla_lib/tests

# 5) Final byte-equivalence proof: helper render_and_pixeldiff with
#    OUT_DIR=build/phase9-final. Each new workspace-root SLA's headless render
#    must match the user's reference PDF at 0 px on every page.

# 6) Workflow YAML still parses
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml'))"

# 7) No "claude" attribution leaked
grep -ricE 'claude' docs/render-fidelity.md shared/fonts/README.md \
  bin/check-fontsizes shared/fonts/50-vollkorn-family-alias.conf || true
```

All commands 1–6 must exit 0. Command 7 must produce no matches (empty output). Document any non-zero outcome in EXECUTION.md before deciding the issue is shippable.

**Verify:** all six checks green; command 7 silent.

**Done:**
- All five checks green.
- Issue is shippable.
</task>

<gate>
- All five final-verification commands exit 0.
- 0-px mismatch on every page (helper `render_and_pixeldiff`).
- **Issue is done when this gate passes.**
</gate>

</phase>

## Files touched (manifest)

**New files:**
- `bin/check-fontsizes` (Phase 5.1; executable Python script, ~50 lines)
- `shared/fonts/50-vollkorn-family-alias.conf` (Phase 3.1; ~20 lines XML incl. comment header)
- `docs/render-fidelity.md` (Phase 6.1; ~150–250 lines)

**Modified files:**
- `gruene-zeitung-vorlage-original.sla` (Phase 0.1: replaced with corrected content; FONTSIZE 11.7→12 across 97 PAGEOBJECT ITEXTs)
- `plakat-a1-hochformat-original.sla` (Phase 0.1: replaced with corrected content; likely byte-identical)
- `postkarte-vorlage-original.sla` (Phase 0.1: replaced with corrected content; likely byte-identical)
- `templates/zeitung-a4-grun/build.py` (Phase 1.1: regenerated via `tools/sla_to_dsl.py`; 97 fontsize=11.7 → fontsize=12)
- `templates/zeitung-a4-grun/template.sla` (Phase 1.1 side-effect: fresh build output)
- `templates/zeitung-a4-grun/baseline.pdf` (Phase 2.2: regenerated headless in font-installed env)
- `templates/plakat-a1-hochformat/build.py` (Phase 1.2: regenerated **only if non-empty diff**)
- `templates/plakat-a1-hochformat/template.sla` (Phase 1.2 side-effect: fresh build output if build.py changed)
- `templates/plakat-a1-hochformat/baseline.pdf` (Phase 2.2: regenerated)
- `templates/postkarte-a6-kampagne/build.py` (Phase 1.2: regenerated **only if non-empty diff**)
- `templates/postkarte-a6-kampagne/template.sla` (Phase 1.2 side-effect: fresh build output if build.py changed)
- `templates/postkarte-a6-kampagne/baseline.pdf` (Phase 2.2: regenerated)
- `Dockerfile.claude` (Phase 3.2: two new layers between current line 50 and 53 — font-install conditional COPY + alias install)
- `bin/validate` (Phase 5.2: preflight invocation of `bin/check-fontsizes`)
- `.github/workflows/pages.yml` (Phase 7.1: visual_diff invocation removed from `validate-reproductions`; orphan upload step removed; TODO comment added)
- `shared/fonts/README.md` (Phase 8.1: rewrite to reflect `/root/workspace/fonts/` + `/usr/local/share/fonts/gruene/` layout; cross-link `docs/render-fidelity.md`)

**Asset files (potentially refreshed; commit only if bytes change):**
- `templates/zeitung-a4-grun/assets/*` (Phase 1.1: converter may re-extract; in practice text-only correction shouldn't change image assets)
- `templates/plakat-a1-hochformat/assets/*` (Phase 1.2: same caveat)
- `templates/postkarte-a6-kampagne/assets/*` (Phase 1.2: same caveat)

**Untouched (constraint reminder):**
- `/root/workspace/originals/` — user's drop zone, never enters git from this PR.
- `/root/workspace/fonts/` — gitignored, never committed.
- `tools/sla_to_dsl.py`, `tools/sla_diff.py`, `tools/visual_diff.py`, `tools/_export_pdf.py`, `tools/render.py` — invoked, not modified.
- `templates/<id>/meta.yml` — `original_sla:` paths preserved by Phase 0's filename-preservation strategy.
- `templates/<id>/diff.yml` — thresholds untouched (resolution 6).
- `samples-output/originals/*.pdf` — out of scope (resolution 7).
- `tools/sla_lib/tests/test_*.py` — fixtures unchanged because filenames preserved (RESEARCH.md §Test impact assessment).
- `site/src/content/templates/*.md` — auto-regenerated by `tools/gallery_build.py`; no manual edit needed.
- `.gitignore` — already blocks `fonts/`, `*.otf`, `*.ttf`, `*.ttc`.

**Out of git tracking (build artifacts):**
- `build/phase0-verify/`, `build/phase2-cross-verify/`, `build/phase9-final/`, `build/validation/` (under `build/`, gitignored).

## Out of scope (preserved from CONTEXT.md + this issue)

- Bundling Gotham Narrow into the public repo (license-blocked; D2 + ISSUE.md "Out of scope").
- CI font provisioning (D7; deferred to a follow-up issue; this PR drops `visual_diff` from CI as the stop-gap).
- ECI ISO Coated v2 / PSO Uncoated ICC profile install (cosmetic; substitutes are symmetric).
- Migrating off Scribus / replacing the rendering toolchain (ISSUE.md "Out of scope").
- Generic gallery-image quality optimization.
- Building Scribus 1.6.4 from source on arm64 (no longer needed since D1 was fixed).
- Editing `originals/<umlaut>.sla` files in `/root/workspace/originals/` — user's drop zone (D4).
- Pre-commit hook infrastructure (resolution 8: `bin/check-fontsizes` is a `bin/validate` preflight, not a hook).
- Cleanup of `samples-output/originals/*.pdf` (resolution 7).
- Touching per-template `diff.yml` thresholds (resolution 6).
- Committing `originals/<id>.pdf` reference exports into the worktree (resolution 3).

## Acceptance crosswalk

Maps each ISSUE.md acceptance criterion to the phase/task that delivers it.

| ISSUE.md acceptance criterion | Delivered by |
|---|---|
| User-supplied ground-truth PDF for each of the three templates is in the repo, in a documented location | Phase 2 Tasks 2.2 + 2.4 (regenerated `templates/<id>/baseline.pdf` is byte-equivalent to the user's reference PDF; documented in Phase 6.1's `docs/render-fidelity.md`). Per resolution 3, the user's umlaut-named reference PDFs in `/root/workspace/originals/` stay out of git — the regenerated baselines are the in-repo ground truth. |
| Brand fonts (Gotham Narrow + Vollkorn) install in local dev container and CI from a license-clean source | Phase 3 (local dev container via `Dockerfile.claude` + `shared/fonts/50-vollkorn-family-alias.conf` + `/root/workspace/fonts/` gitignored drop zone). **CI portion is explicitly deferred per D7** — covered by Phase 7's TODO + the follow-up CI-fonts issue. The acceptance criterion as written assumes both; CONTEXT.md D7 narrows it to local dev only for this PR. |
| `fc-list \| grep -iE "gotham narrow\|vollkorn"` reports the expected 5 lines after install; missing fonts fail the build with a loud error | Phase 3.2 (Dockerfile font-install layer's sanity probe — fails build with `FONT INSTALL FAILED: only N font faces registered` when `fonts/` was present but install registered <5 faces). |
| Headless render of each `*-original.sla` matches the user's exported PDF: pixel diff < 0.01% per page at 150 dpi | Phase 0.2 + Phase 2.4 + Phase 9.1 (target is in fact 0 px at 0% fuzz, well under 0.01% at any resolution; CONTEXT.md "What done looks like" #1). |
| Each `templates/<id>/baseline.pdf` is regenerated with the new pipeline and committed | Phase 2.2. |
| Existing DSL→render→baseline diff stays at ≤3 pixels per template (PR #5's standard) after re-baselining | Phase 2.3 (`bin/validate` at 150 dpi exits 0; visual_diff worst-page ≤3 px verified). |
| Documentation: `docs/render-fidelity.md` describes the font/ICC pipeline, where Gotham Narrow comes from, and the rebaselining procedure for future Scribus version bumps | Phase 6.1. |
| CI's `validate-reproductions` step exercises the full chain end-to-end; deploy blocks on any per-page mismatch > 0.01% | **Partially deferred per D7.** Phase 7 retains `sla_diff --strict` as the structural gate (deploy still blocks on structural drift). The visual-mismatch deploy-blocker is restored in the follow-up CI-fonts issue once CI has the brand fonts. The TODO comment in Phase 7.1 makes this explicit. |

CONTEXT.md "What done looks like" extras (mapped to phases for completeness):

| CONTEXT.md "What done looks like" extra | Delivered by |
|---|---|
| Verified: `originals/<>.sla → headless render = originals/<>.pdf` byte-identical at strict 0% fuzz, all 17 pages, all 3 templates | Phase 0.2 + Phase 2.4 + Phase 9.1. |
| `Dockerfile.claude` builds and the resulting image has Gotham Narrow + Vollkorn correctly installed | Phase 3.2. |
| `templates/<id>/baseline.pdf` regenerated; `bin/validate` exits 0 with worst-page mismatch ≤3 px | Phase 2.3. |
| `docs/render-fidelity.md` exists | Phase 6.1. |
| Workspace-root duplicate `*-original.sla` files removed; `templates/<id>/meta.yml` and `bin/validate` reference `originals/<>.sla` | **Reinterpreted per resolutions 1–4.** Workspace-root files are *retained* with corrected content and ASCII filenames; `originals/` stays out of git as the user's drop zone. The CONTEXT.md "remove duplicates + repoint" plan was superseded by the simpler "preserve filenames, swap content" approach in resolution 1, sparing the ~24 path references RESEARCH.md enumerated. |
| `.gitignore` correctly blocks `fonts/` and font-extension globs | Already in place (verified in research). |
| Issue branch ships as a single PR; merge brings the corrected ground truth onto main | Outside the plan's scope (executor commits per phase; PR creation is a separate human action). |

## Final verification (run after Phase 9 closes)

```bash
# 1) Preflight regression check
bin/check-fontsizes

# 2) Full structural + visual round-trip at 150 dpi
bin/validate

# 3) CI-mode (96 dpi)
bin/validate --ci

# 4) Unit tests
python3 -m unittest discover tools/sla_lib/tests

# 5) Final byte-equivalence proof (helper render_and_pixeldiff with
#    OUT_DIR=build/phase9-final). 0 px mismatch on every page across all
#    three templates. See "Reusable verification helpers" at top.

# 6) Workflow YAML still parses
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml'))"

# 7) No "claude" attribution leaked into commits, code, or files
grep -ricE 'claude' docs/render-fidelity.md shared/fonts/README.md \
  bin/check-fontsizes shared/fonts/50-vollkorn-family-alias.conf || true
```

All commands 1–6 must exit 0. Command 7 must produce no matches.
