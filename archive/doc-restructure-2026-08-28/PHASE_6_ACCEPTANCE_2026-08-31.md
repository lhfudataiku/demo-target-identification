# Phase 6 index and verification acceptance record — 2026-08-31

> **Lifecycle:** Historical · **Audience:** migration reviewers · **Authority:** records completion of
> Phase 6 of the approved documentation restructure · **Update when:** never; a later redesign needs a
> dated successor · **Generated dependencies:** offline repository indexes and checks · **Excludes:**
> volatile project measurements and DSS state.

Phase 6 adds `tools/index_manifest.json`: the reviewed, explicit current claim-bearing document set,
the separate historical comparison set, and owner/scope/freshness metadata for every navigation
index. `tools/build_index.py` rejects excluded or untracked entries, writes current claims only from
the manifest, and emits the separate historical surface. Governed Part 2 claims remain owned by the
registry rather than a second heuristic scan.

`tools/check_links.py` now checks current links and stale mentions strictly, while archive links are
checked only for recoverability of their dated targets. No archived evidence was edited. The only
Make log command found was made bounded (`make logs`, 200 lines); `make logs-follow` is explicitly
interactive.

## Measured comparison with Phase 0

| surface | Phase 0 | Phase 6 | change |
|---|---:|---:|---:|
| Codex ordinary webapp instruction bytes / words | 25,436 / 3,458 | 5,220 / 744 | -79.5% / -78.5% |
| Claude ordinary webapp instruction bytes / words | 25,552 / 3,478 | 5,220 / 744 | -79.6% / -78.6% |
| Current heuristic claim index rows / bytes | 2,129 / 334,823 | 536 / 83,175 | -74.8% / -75.2% |
| Explicit historical comparison index rows / bytes | — | 1,506 / 261,323 | new, non-default |
| Index summary bytes | 11,259 | 10,839 | -3.7% |

The Phase 6 conservative tokenizer proxy is 1,740 tokens for both harnesses, below the 3,000-token
ordinary-webapp budget. Total index storage is 694,300 bytes versus the 644,851-byte Phase 0 capture;
the 7.7% increase is the intentional separately named historical surface and ownership metadata, not
the default current retrieval path.

## Offline acceptance

- Manifest enforcement and deterministic claim ordering: passed.
- Harness parity and context budget: passed.
- Current links/stale mentions and archive integrity links: passed.
- Claim registry, notebook-assertion index, recipe/model/feature/code indexes and freshness checks: passed.
- No `--refresh`, DSS command, build, scenario, graph operation, staging, commit or push was performed.

The generators intentionally enumerate tracked files. This unstaged Phase 6 delivery is tested
directly, but its new source files will enter the code inventory only after they are staged; rerun
the two offline index builders and `./tools/check_indexes.sh` immediately before the approved commit.
