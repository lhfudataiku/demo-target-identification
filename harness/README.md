# Harness instruction sources

**Lifecycle role:** Canonical source and maintenance guide for the project instructions loaded by
OpenAI Codex and Claude Code.

**Authority:** The files in this directory are the shared policy. Generated entry points must not
be edited directly.

**Update trigger:** Change a shared instruction or the target-ID skill, then synchronise and check
the generated copies before review.

## Layout

- `PROJECT_INSTRUCTIONS.md` is the canonical root instruction body.
- `WEBAPP_OVERLAY.md` is the canonical nested instruction body for ordinary work in `webapp/`.
- `skills/target-id/` is the canonical target-ID skill package, including its task procedure.
- `tools/sync_harness.py --write` copies these sources to the Codex and Claude discovery paths.
- `tools/sync_harness.py --check` verifies byte-for-byte parity and is safe for hooks or CI.
- `tools/check_harness.py` verifies routing rules and reports the reproducible cold-start budget.

The generated files deliberately use copies rather than symlinks: both harnesses discover ordinary
files reliably across team machines. The synchroniser is deterministic and adds no timestamp.

Run, after an approved instruction change:

```bash
python3 tools/sync_harness.py --write
python3 tools/sync_harness.py --check
python3 tools/check_harness.py
```

`check_harness.py` uses an installed tokenizer when one is available. This checkout has no shared
Claude/Codex tokenizer, so its fallback is explicitly labelled as a conservative, reproducible
byte-based proxy rather than an exact harness-token measurement.
