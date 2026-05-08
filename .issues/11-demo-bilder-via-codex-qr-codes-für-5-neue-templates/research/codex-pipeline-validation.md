# Codex Pipeline Validation — 2026-05-08 04:38 UTC

## Test result: ✓ working

Generated a full photorealistic portrait via `codex exec` using the natural-language
image-gen tool path, end-to-end in 2 minutes 10 seconds, written to disk as 319 KB JPG.

Test invocation (the working form):

```bash
codex exec \
  --sandbox workspace-write \
  --skip-git-repo-check \
  --add-dir /tmp/codex-image-test \
  --cd /tmp/codex-image-test \
  --dangerously-bypass-approvals-and-sandbox \
  "$PROMPT" < /dev/null > codex.log 2>&1
```

## Critical finding: must close stdin

Without `< /dev/null`, codex blocks on `Reading additional input from stdin...`
because piping its output (e.g. `| tail -40`) creates a non-tty stdin that codex
treats as "data may be coming". Existing `tools/codex_image_gen.py` does NOT pass
`stdin=DEVNULL` to `subprocess.run` — must be patched.

**Fix in `tools/codex_image_gen.py::generate_image()` around line 124:**

```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=600,
    stdin=subprocess.DEVNULL,   # NEW — required to avoid stdin-block hang
)
```

## Codex internal behavior (observed)

When prompted to "save to /absolute/path.jpg":
1. Codex calls its built-in image-generation tool, output lands at
   `/root/.codex/generated_images/<UUID>/<hash>.png` (PNG, not JPG).
2. Codex then runs `convert <generated.png> <target.jpg>` (ImageMagick) inside
   its sandboxed shell to produce the requested format at the requested path.
3. Codex reports back with the file size from `ls -la`.

**Implication for `tools/codex_image_gen.py`:**
- The `recover_codex_output()` helper proposed in RESEARCH.md remains useful
  defense-in-depth — if codex's `convert` step fails (e.g. ImageMagick missing,
  permission issue), we recover from the PNG cache directly.
- Adding the helper still recommended.

## Time budget (empirical)

| Phase | Time |
|---|---|
| Codex agent startup + auth | ~5 s |
| Image generation (gpt-image-2) | ~110 s |
| PNG→JPG convert + ls reporting | ~10 s |
| Total | **~2:10 per image** |

For the issue's ~6 portraits/photos: ~13 min minimum, ~30 min with retries.

## Sample output

`/tmp/codex-image-test/test-portrait.jpg` — 319 KB, 1024×1536-ish JPG of a
woman in early 40s with shoulder-length brown hair, dark green blazer, white
blouse, in a wood-and-greenery community space. Photorealistic, natural skin
texture, warm soft daylight. Quality target: met.

(Test artifact is in /tmp; not committed. The learning informs PLAN.md.)
