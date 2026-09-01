# demo-target-identification

Two linked Dataiku DSS proof-of-concepts:

- **Part 1 — the graph.** A biomedical knowledge graph built from public sources, owned by the
  `DEMO_KG_LS` project, plus the graph webapp that browses it.
- **Part 2 — the prioritizer.** An explainable target-gene prioritizer owned by
  `DEMO_TARGET_IDENTIFICATION`, which consumes shared objects from Part 1 and serves a demo webapp.

This repository holds the documentation, the mirrored DSS recipe code, the generated indexes and the
webapp source. It does **not** hold the data: `data/` is local-only and never committed.

## Getting oriented

Start with whichever matches what you need — you should not have to read the whole document set.

| I want to | Go to |
|---|---|
| Understand what the POC is and how the two parts fit together | [docs/overview/PROJECT_CONTEXT.md](docs/overview/PROJECT_CONTEXT.md) |
| Find the right document for a topic | [docs/README.md](docs/README.md), the document router |
| Look up a model, metric, feature, recipe or past decision | `.index/` — see below |
| Work on the demo webapp | [webapp/README.md](webapp/README.md) |
| Change the instructions an AI agent follows here | [harness/README.md](harness/README.md) |

Several documents are tens of thousands of tokens. Read one section, not a whole file.

## The generated indexes

`.index/` holds ten small TSVs generated from the docs, the notebooks and a committed DSS snapshot.
They answer most factual questions — which recipe produces a feature, which decision is current,
whether a documented number is guarded by a notebook assertion — without opening a large document.
`.index/index_metadata.tsv` names each index's owner, scope and freshness command, and
`.index/SUMMARY.md` carries the risk surface of numbers that could drift.

They are generated artifacts. Regenerate rather than hand-edit them.

## Working with an AI agent here

The repository ships its own agent instructions so that Claude Code and OpenAI Codex behave the same
way. The canonical sources live in `harness/`; `AGENTS.md`, `CLAUDE.md` and the two `webapp/`
overlays are generated copies and carry a banner saying so. Edit the source, never the copy:

```bash
python3 tools/sync_harness.py --write
```

The retrieval and platform traps live in the target-ID skill at
[harness/skills/target-id/SKILL.md](harness/skills/target-id/SKILL.md). Claude Code discovers it
automatically; on a harness without a skill mechanism, read that file directly.

## Running the checks

One command verifies that every generated artifact is current, that the harness copies match their
sources, and that every documentation link and file mention resolves:

```bash
./tools/check_indexes.sh
```

The unit tests:

```bash
git ls-files 'tools/tests/test_*.py' | sed 's|/|.|g; s|\.py$||' | xargs python3 -m unittest
```

Both run offline against the committed DSS snapshot, need no credentials and need no third-party
package. GitHub Actions runs both on every pull request. To run the same gate before each commit:

```bash
ln -s ../../tools/check_indexes.sh .git/hooks/pre-commit
```

After adding or removing a tracked `.py`, `.json`, `.sh` or `.cypher` file, regenerate the code
index so the check stays green:

```bash
python3 tools/build_recipe_index.py
```

Use `--refresh` only when a recipe changed in the DSS UI: it re-snapshots DSS and is slow.

## Boundaries

A few rules are not negotiable, and the agent instructions repeat them:

- `data/` is never committed, and the `KNOWLEDGE_GRAPH_PRIMEKG` graph is frozen — never rebuilt.
- The retired decision log under `archive/decisions/` is immutable; current durable choices go in
  [docs/decisions/DECISION_REGISTER.md](docs/decisions/DECISION_REGISTER.md) under the admission rule
  stated there.
- A DSS build, deployment or scenario run is never a side effect of inspection. Confirm the target
  project first.
