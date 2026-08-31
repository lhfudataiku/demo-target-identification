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
- `tools/check_harness.py` verifies routing shape, both cold-start budgets and the skill's
  magnitude claims.

The generated files deliberately use copies rather than symlinks: both harnesses discover ordinary
files reliably across team machines. The synchroniser is deterministic and adds no timestamp.

Run, after an approved instruction change:

```bash
python3 tools/sync_harness.py --write
python3 tools/sync_harness.py --check
python3 tools/check_harness.py
```

`check_harness.py` gates on a conservative byte proxy — UTF-8 bytes divided by three — and never on
an installed tokenizer, so the same commit cannot pass on a laptop and fail in CI because one
machine happens to have `tiktoken` for an unrelated project. When `tiktoken` is present its count is
printed alongside, labelled as an OpenAI encoding and informational: neither harness's real
tokenizer is available here, so no exact token guarantee is claimed.

Beyond parity it checks four properties. Entry points must contain no unconditional read, matched by
the shape of the directive rather than by one phrasing, while an overlay stays free to forbid the
same read. Every routing bullet must state the condition it routes on, because a bullet with no
trigger is an instruction that always fires. The entry points must name the skill path, and both
they and the skill must stay inside their budgets. Finally the skill's magnitude claims — how large
the docs, the recipes and the retired chronology are — are re-measured against the tracked files.
Those claims justify "do not read the docs", no claim index guards them because harness material is
excluded from the claim manifest by design, and three of the four had drifted by up to 36% before
this check existed. `tools/tests/test_check_harness.py` pins the behaviour, including the
filename-dot case that a literal blocklist and a naive pattern both miss.

## Reaching the skill from any harness

Claude Code discovers `.claude/skills/target-id/`. A harness without a skill mechanism cannot, so the
root instructions name `harness/skills/target-id/SKILL.md` as the equivalent read and
`check_harness.py` fails if that path stops being named. Without it the routing rule "load the
target-ID skill first" would dead-end on those harnesses, and the skill is where the load-bearing
traps live — the retrieval and `dku` failures that return plausible values rather than errors. Keep
the traps in the skill and the pointer in the instructions; do not copy the traps into the entry
files, which are budgeted for cold start.

## Enforcement

`.github/workflows/checks.yml` runs the full gate on every push to `main` and every pull request, so
generated artifacts cannot drift into `main` on the strength of someone remembering:

```bash
./tools/check_indexes.sh
git ls-files 'tools/tests/test_*.py' | sed 's|/|.|g; s|\.py$||' | xargs python3 -m unittest
```

Both are offline: the checks read the committed DSS snapshot, and no tool needs a third-party
package. The test line is enumerated from git because `tools/` carries no package marker, so
`unittest discover` cannot import the start directory; naming the modules by hand would let a new
test file be skipped in silence. Do not name the marker file here: the code index matches references
by basename, so writing it out invents references from four unrelated webapp packages. Optionally
run the same gate before each commit:

```bash
ln -s ../../tools/check_indexes.sh .git/hooks/pre-commit
```

## Permissions

`.claude/settings.json` is tracked and shared: it allowlists the read-only retrieval and check
commands this harness runs constantly, so a new contributor does not re-approve them one by one.
`.claude/settings.local.json` is the per-developer override and is now ignored by this repository's
own `.gitignore`.

Two exclusions are deliberate. Commit and push stay absent from the allowlist, because the boundary
is approval per change rather than a blanket grant, and `dku` is allowlisted only for read-only
verbs, never as a prefix. Codex has no tracked per-repository equivalent to add here; its approval
settings are user-level, so a Codex contributor configures them once locally.
