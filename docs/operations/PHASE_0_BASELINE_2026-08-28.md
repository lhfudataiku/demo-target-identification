# Phase 0 baseline and preservation record — 2026-08-28

**Lifecycle role:** Historical baseline / migration evidence
**Authority:** Records the repository state captured before the documentation-restructure migration. It does not change the approved plan or any DSS state.
**Update trigger:** Do not update. Later phases should cite this dated record when comparing context, retrieval, or preservation results.

## Approval and scope

[`DOC_RESTRUCTURE_PLAN.md`](../demo/DOC_RESTRUCTURE_PLAN.md) is **approved as of 2026-08-28**. This record establishes the Phase 0 baseline only. It authorises neither DSS work nor graph recomputation, build execution, deployment, staging, commit, or push.

The approval retains the following implementation choices. The plan states recommended defaults, but Phase 0 has not selected an implementation beyond them:

| implementation choice | plan's recommended default | Phase 0 disposition |
|---|---|---|
| Harness synchronisation | Generate both root instruction files from one source and check parity; use symlinks only after portability is proven. | Not implemented or decided. |
| Validation authority | Notebooks compute truth; `VALIDATION` maps and interprets it. | Not implemented or decided. |
| Decision migration | Preserve the full old log and curate a smaller current register. | Not implemented or decided. |
| Build-audit storage | Full ledger in DSS; schemas/policy and optional accepted snapshots in Git. | Not implemented or decided. |
| Governance execution | Hybrid DSS-scenario/repository-index pilot, with no LLM in the no-change path. | Not implemented or decided. |

## Reproducibility boundary

| item | captured value |
|---|---|
| Repository branch | `feat/webapp-act4` |
| HEAD | `28d74094423e9865a5972b022539f6d7d41e9abb` (`documentation revision plan`) |
| Pre-existing worktree edits | `docs/README.md` and `docs/demo/DOC_RESTRUCTURE_PLAN.md` only; both were preserved. |
| Existing approval edit | README changes the plan label from proposed to approved; plan changes status to approved (1 addition/1 deletion in README; 3 additions/2 deletions in the plan). |
| DSS boundary | No `dku` command, DSS contact, build, deployment, graph operation, or refresh was performed. |

All measurements below are working-tree byte counts at capture time, using tracked paths. They are a baseline, not an assertion that the pre-migration files already meet their future lifecycle roles.

## Markdown inventory

| provisional lifecycle area | tracked Markdown files | bytes | boundary |
|---|---:|---:|---|
| Current documentation | 15 | 433,238 | `docs/`, excluding the restructure plan and `archive/` |
| Current planning | 1 | 19,082 | `docs/demo/DOC_RESTRUCTURE_PLAN.md` |
| Decision log | 1 | 90,542 | root `DECISIONS.md` |
| Historical archive | 2 | 147,883 | `archive/` Markdown before this Phase 0 record |
| Harness material | 8 | 70,166 | root/nested instructions plus Codex/Claude target-ID skill Markdown; symlink target content is counted |
| Evidence support | 1 | 5,690 | `notebooks/README.md` |
| Supporting webapp material | 3 | 62,965 | remaining tracked Markdown outside the areas above |
| **Total** | **31** | **829,566** | all tracked Markdown |

## Index baseline

At the capture, `.index/` held 14 regular files / 644,851 bytes: seven TSV indexes (2,984 data-plus-header rows / 405,626 bytes), six JSON support/snapshot files (227,966 bytes), and `SUMMARY.md` (11,259 bytes).

| index | rows | bytes | observed freshness |
|---|---:|---:|---|
| `assertions.tsv` | 200 | 11,497 | generated 2026-08-28 12:18:56Z |
| `claims.tsv` | 2,129 | 334,823 | generated 2026-08-28 12:18:56Z; **stale** against the pre-existing approval edits |
| `code.tsv` | 108 | 10,051 | generated 2026-08-28 12:19:07Z |
| `decisions.tsv` | 159 | 14,923 | generated 2026-08-28 12:18:56Z |
| `features.tsv` | 284 | 20,221 | generated 2026-08-28 12:19:07Z |
| `models.tsv` | 9 | 2,320 | generated 2026-08-28 12:19:07Z |
| `recipes.tsv` | 95 | 11,791 | generated 2026-08-28 12:19:07Z |

The linked DSS snapshot was present as `.index/dss_snapshot.json` (194,159 bytes; 2026-08-27 12:36:32Z). It was observed only; no live refresh was requested or run.

## Instruction-payload baseline

The ordinary webapp cold-start payload combines the root instruction and the nested webapp overlay. Byte, line, and whitespace-word counts are recorded because no tokenizer is bundled in this checkout. Word count is only a reproducible proxy, not a tokenizer measurement or formal lower bound. Both paths are likely above the 3,000-token target, but Phase 1 must confirm that with measured harness usage or an appropriate tokenizer.

| harness | root entry | nested entry | combined bytes | combined lines | combined words | observation |
|---|---|---|---:|---:|---:|---|
| OpenAI Codex | `AGENTS.md` (6,712 B; 79 lines; 980 words) | `webapp/AGENTS.md` (18,724 B; 329 lines; 2,478 words) | 25,436 | 408 | 3,458 | Likely above budget; exact tokens not yet measured. |
| Claude Code | `CLAUDE.md` (6,828 B; 116 lines; 1,000 words) | `webapp/CLAUDE.md` → `AGENTS.md` (18,724 B; 329 lines; 2,478 words) | 25,552 | 445 | 3,478 | Likely above budget; exact tokens not yet measured; nested entry is a symlink. |

## Initial verification state

- `python3 tools/check_links.py`: passed — 28 Markdown files checked, 0 broken links and 0 stale mentions.
- `./tools/check_indexes.sh`: reported only `claims.tsv` stale and directed an offline `python3 tools/build_index.py` rebuild. This is expected from the two pre-existing approval edits.

Final Phase 0 verification is recorded after the manifest and this document are indexed.

## Phase 0 verification result

This repository-only, offline rebuild completed without `--refresh`: `build_index.py` wrote 2,128 claims / 199 assertions / 158 decisions, and `build_recipe_index.py` wrote 94 recipes / 283 feature columns / 8 models / 107 code files. The difference from the captured index counts is itself baseline evidence of stale generated state, not a DSS change.

- `git diff --check`: passed.
- `python3 tools/check_links.py`: passed — 28 tracked Markdown files checked, 0 broken links and 0 stale mentions.
- `./tools/check_indexes.sh`: passed — claims, assertions, decisions, recipes, and features are current; its embedded link check also passed.
- `cmp -s` and SHA-256 checks: passed for both physical snapshots. The decision snapshot hash is `f1e91ab25d4c1373a754623e9218a905b0c5fb9e5704fac591f9f9b8bc96c2b2`; the approved-plan snapshot hash is `2b5132e4a63849e1fac85e815ceeb245b0f425ee223918c198119c2d390b47a7`.
- All versioned presentation artifacts listed in the preservation manifest were verified clean with `git diff --quiet`; no mockup content changed.

The freshness commands enumerate `git ls-files`, so this final result applies to the tracked working-tree set. The new, intentionally unstaged Phase 0 records are not yet inputs to those generators. When they are first staged for an approved commit, rerun both offline index builders and the checks before committing.

## Preservation method

The physical Phase 0 snapshots and the cryptographic manifest live in [`../../archive/preservation/2026-08-28/`](../../archive/preservation/2026-08-28/). The decision log and active approved plan receive byte-for-byte `.snapshot` copies because later phases may replace their active roles; the non-Markdown extension also prevents the current broad claims index from treating the frozen decision log as a second live claim source. Existing version-controlled HTML mockups are intentionally not duplicated: the manifest records their SHA-256 digests and Git blob IDs, while the active copies remain in place until Phase 2 explicitly classifies iterations. This avoids silently choosing which auxiliary mockups are historical while retaining an exact, independently verifiable record.
