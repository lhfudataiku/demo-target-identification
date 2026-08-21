# Chat starter — Target Identification POC (paste into a new chat)

You are my project assistant on a **Dataiku DSS proof-of-concept** that creates a **PrimeKG-like**
biomedical knowledge-graph pipeline for drug-discovery **target identification**, renders it with the
**Visual Graph** plugin, and ranks candidate targets per disease with an explainable model.

## Orient yourself first (do this before acting)

1. Read the document set — source of truth, trust it over your memory:
   - **`PROJECT_CONTEXT.md`** — start here. Purpose, the two published numbers that anchor the pitch,
     personas, and **how the two projects fit together** (§4, including the shared-object contract).
   - **`GRAPH_BUILDING.md`** — technical doc for `DEMO_KG_LS`: input sources §2, graph schema §3,
     pipeline §4, the graph webapp §6, final statistics §7.
   - **`TARGET_PRIORITIZER.md`** — technical doc for `DEMO_TARGET_IDENTIFICATION`: data exploration
     §3, features §4, splitting/leakage §5, model selection §6, validation §7, results §8,
     flow zones §9, migration status §10.
   - **`DSS_CHEATSHEET.md`** — platform behaviours and CLI patterns, generic. **Read §1 before
     trusting any output** — those failures produce plausible results rather than errors.
   - **`RESEARCH_NOTE.md`** — evidence base behind the modelling choices (**unvalidated corpus** —
     verify before client-facing use).
   - `DISCOVERY_LANDSCAPE.md` — the wider discovery chain (stages 1–6); separate framework.
2. Check my auto-memory (`MEMORY.md` + files) for standing preferences.
3. Confirm live state with the `dku` CLI. **The docs can lag the flow, and `dss_recipes/` can lag
   DSS** — pull real code with `dku recipe get-code` before reasoning about a recipe.

## Environment — three projects

| Project | Role | Scale |
|---|---|---|
| **`DEMO_KG_LS`** | data pipeline + graph-building webapp | 47 recipes, 65 datasets |
| **`DEMO_TARGET_IDENTIFICATION`** | modelling, validation, result visualisation | 68 recipes, 78 datasets, 4 models |
| **`KNOWLEDGE_GRAPH_PRIMEKG`** | **frozen reference** — the original single-project build | do not modify or rebuild |

All on `design.solutions.dataiku-dss.io` (DSS 14.7). Set `export DKU_PROJECT=…` per project.
**Code env:** `primekg_kg` (py3.11: pandas, pyarrow, requests, obonet, networkx, scipy).
**Repo:** `~/Documents/GitHub/demo-target-identification` (branch `flow-building`). Recipe code
mirrored in `dss_recipes/`; `data/` is gitignored (large / licence-restricted — never commit it).

## What's built (current — 2026-08-17)

**Part 1 — the graph. Complete.** 113,391 nodes / 2,851,510 edges / 18 relations, rebuilt from source
and accepted against the frozen reference: 7 of 9 node groups and 14 of 18 relations reproduce **to
the row**, and every delta is functional-annotation drift traced to the *reference* being stale.
`node_index` is now **deterministic** (a visual Window recipe over an explicit sort, verified by two
byte-identical builds) — it used to be positional and renumbered the whole graph on every rebuild.
Note it is **1-based** here and **0-based** in the reference.

**Part 2 — the prioritizer. Built and validated on the rebuilt graph.** Champion **`m3-f12`** (12
features): macro per-disease AUC **0.8197** over 670 diseases, per-split-key 0.8007, pooled 0.8915,
per-family 0.7976, drug-target 0.6911. Ladder: `m1-f7` 0.7593 → `m2-f10` 0.7882 → `m3-f12`.
`m7-drug-label` is a **deliberately retained negative result** — do not read its 0.9324 drug-target
AUC as a win.

**Migration status: COMPLETE and verified (2026-08-17).** The modelling project reads the graph
through **10 shared objects** (PROJECT_CONTEXT §4.3) in its `00 Shared from DEMO_KG_LS` zone; Part 1
components removed; indices remapped; flow rebuilt end to end. **Every metric landed within ±0.01 of
the frozen reference** against a ±0.02 tolerance set in advance, and the candidate pool total is
bit-identical (6,754,128). See TARGET_PRIORITIZER §10.

## Next up

1. **Retire `KNOWLEDGE_GRAPH_PRIMEKG`** — the acceptance criterion is met, so the frozen reference has
   served its purpose. Also retire the older Kuzu snapshot in `DEMO_KG_LS`.
2. **A direct safety measurement + the dashboard** — the largest remaining increment of demo value.
   The filterable table is DONE (`target_candidates_2`, 63,020 ranked rows with tractability, class
   and liability annotations), and the two *free* safety signals were measured and **rejected as
   filters** (TARGET_PRIORITIZER §10.3). What is still needed: essentiality / tissue-expression
   breadth (a new source), then the UI. **Attributes, never edges.**
3. **Re-pick the persona panel on evidence** — type 2 diabetes is the flagship but the weakest case on
   both metrics (per-disease 0.634, drug-target 0.256); two non-persona cancers are the strongest
   therapeutic showcases.
4. **Minor cleanups:** regenerate the demo Cypher gene literals from the rebuilt ranking; rebuild the
   drug-label chain (its `psplit_*_drug` inputs were not rebuilt); materialise the hub-bias meter as a
   recipe rather than an ad-hoc calculation.

## Sharp edges (check these first)

**Read `DSS_CHEATSHEET.md` §1 for the full set — these are the ones specific to this work:**

- **NEVER use recursive build types in `KNOWLEDGE_GRAPH_PRIMEKG`** — it walks up into the graph zone
  and renumbers every node. This hazard is *why* the projects were split.
- **`compute_kg` / the graph must never be recomputed unless I say so.**
- **A benchmark a lookup table wins is measuring the lookup.** Drug-target AUC is dominated by gene
  popularity: a no-graph lookup scores 0.9354, beating the drug-trained model. Report it as a warning
  flag; never optimise against it.
- **Report macro per-disease AUC, never pooled** — pooled overstates by ~7 points.
- **The rank-sum AUC orientation depends on rank direction**, and getting it backwards is silent (a
  plausible sub-random AUC alongside perfect precision@50). Ascending ranks → no leading `1 −`.
- **The prediction column is near-useless for discovery** — the threshold is F1-optimised against a
  ~2% base rate, so 590/762 known obesity targets are false negatives. Rank and take top-N.
- **Verify a rebuild by job history, not row count.** This has caused three rounds of wrong numbers.
- **Read dataframes with inference disabled and cast join keys to string** — dtypes are inferred per
  65,536-row chunk, so joins silently miss on some chunks.
- **The query recipe is unreliable on this graph** (opaque errors, buffer-pool exhaustion). The
  interactive explorer works; heavy graph math is all code.
- **Druggability is INVERTED under the association label** (membrane receptor: 0.78x assoc, 3.16x
  drug). Never add it as a model feature; group the presentation by class instead.
- **Safety proxies point WITH efficacy, not against it.** Genetic constraint and curated liabilities
  both favour drugged targets. Neither is a safety filter. Absence of a liability means nobody looked.
- **The candidate filter is THREE clauses: novel → tractable → not-secreted.** Validated per persona at
  1.42-1.71x enrichment on drug-validated targets with **100% recall**. Do NOT add "exclude known
  liability" — it destroys 15-70% of validated targets and takes obesity to 0.54x (worse than no
  filter). Obesity's ADRB2 is a validated target that carries a liability flag.
- **A join's MANUAL column selection can silently select nothing** — check the recipe status message,
  switch to auto. And a new output column needs a schema-updating build, which then clears downstream.
- **Rules that key on integer ORDER are not migration-safe.** Three here depended on `node_index`
  ordering rather than identity — a split modulo, a family tie-break, a parent-selection minimum.
  Remapping literals is not enough; audit anything that ranks, mods or minimises on an id.
- **The per-disease AUC code recipe emits two levels in one table** (`disease` + `split_key`). Filter
  on `level` before comparing it to the visual chain, or you manufacture a 0.16 discrepancy.
- **A container-orchestration failure looks like a recipe failure in the job list.** If the log shows
  pod/`kubectl` errors rather than a Python traceback, just retry.

## How I want you to work (my preferences)

- **Never `git commit`/`push` without asking me first.** Make changes, summarize, ask.
- **Joins go in visual Join recipes, not pandas `.merge()`.** Python extracts only load and parse to
  native identifiers; visual recipes do grounding and harmonization.
- Verify with real data (row counts, schema, sample values), not just exit 0.
- New datasets go on the **S3 connection** (`dataiku-managed-storage`, parquet).
- After a visual harmonize, force the schema to all-string then build **without** schema
  auto-update — otherwise numeric identifiers re-infer as integers and break the cross-source union.

## Useful commands

```
export DKU_PROJECT=DEMO_TARGET_IDENTIFICATION     # or DEMO_KG_LS
dku flow zones ; dku recipe list ; dku dataset list ; dku model list
dku --format json flow graph                       # full dependency map
dku dataset count kg ; dku dataset head graph_nodes --format json
dku dataset download graph_nodes ./nodes.csv       # for local comparison work
dku recipe get-code <recipe>                       # dss_recipes/ can be stale
dku job list --limit 60                            # verify WHEN something was built
dku ml settings <analysis_id> <mltask_id>          # audit per-feature config before training
```

## First message suggestion

"Read the document set (PROJECT_CONTEXT, GRAPH_BUILDING, TARGET_PRIORITIZER, DSS_CHEATSHEET),
confirm the live state of both active projects via `dku`, and summarize what's built and what's next.
Then <your task>."
