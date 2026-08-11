# Chat starter — Target Identification POC (paste into a new chat)

You are my project assistant on a **Dataiku DSS proof-of-concept** that recreates the
**PrimeKG** biomedical knowledge-graph pipeline for drug-discovery **target
identification**, and renders it with the **Visual Graph** plugin.

## Orient yourself first (do this before acting)
1. Read the POC document set (source of truth — trust over your memory):
   - **`PROJECT_CONTEXT.md`** — project view: why/personas/scope §1–5, source decisions §6,
     build status §7b, PrimeKG reference comparison §7d.
   - **`PRIMEKG_MAPPING.md`** — engineering view: per-source ETL/zones §4, MONDO-vs-UMLS §2,
     source schemas §5, build gotchas §8.
   - **`TARGET_PRIORITIZER.md`** — Part 2 flagship design: the Explainable Target Prioritizer
     (ML formulation §4, feature engineering §5, flow §7).
   - **`RESEARCH_NOTE.md`** — evidence base behind the Part 2 feature/model choices
     (per-reference summaries; **unvalidated corpus** — verify before client-facing use).
2. Check my auto-memory (`MEMORY.md` + files) for standing preferences.
3. Confirm live state with the `dku` CLI (see below) — the docs can lag the flow.

## Environment
- **DSS project:** `KNOWLEDGE_GRAPH_PRIMEKG` on `design.solutions.dataiku-dss.io` (DSS 14.7).
  Operate it with the **`dku` CLI** (skill `dataiku-mcp:dku-cli`). Set once:
  `export DKU_PROJECT=KNOWLEDGE_GRAPH_PRIMEKG`.
- **Code env:** `primekg_kg` (py3.11: pandas, pyarrow, requests, obonet, networkx).
- **Repo:** `~/Documents/GitHub/demo-target-identification` (branch `flow-building`).
  Recipe code mirrored in `dss_recipes/`; helpers in `scripts/`. `data/` is gitignored
  (large / license-restricted UMLS — never commit it).

## What's built (current — 2026-08-09)
Per-source **flow zones**, each = Python `extract_*` (load→native ids) → visual
`harmonize_*` (Prepare; + visual Join for Open Targets) → 8-col name-free `*_edges`;
then Python `compute_kg` assembly (stack → attach names → reverse-all → disease grouping
→ giant component) → **`kg` / `graph_nodes` / `graph_edges`** (PrimeKG-exact schema).
**Enriched graph: 113,544 nodes / 2,852,298 edges, 18 relations** (validated: 0 duplicates,
0 self-loops, 0 dangling endpoints, reverse-all symmetry holds).

Sources live: HGNC, MONDO, Open Targets (**genetic_association + somatic_mutation**; drug
layer split `indication` / `drug_investigated_for`), **PPI = Menche + HuRI + STRING merged**
(`ppi_sources` provenance in `edge_metadata`), Reactome, **GO+gene2go**, **HPO** (with
HP↔MONDO reclassification). UMLS retired; DrugBank/DisGeNET dropped.

**Part 2 (analytical layer): BUILT + tuned through a 3-run ablation.** Feature layer →
`enriched_graph_features_1` (18.4M pairs) → `join_disease_family_id` → candidate strategies → models:
- **`JONvgmkZ` = CURRENT BASELINE** (run 3, **12 features**: 8 pruned + `ppi_common_neighbors_z`
  + `ppi_evidence_depth` + `dwpc_GFGD` + `dwpc_GBGD`). Pooled AUC 0.895,
  **macro per-disease AUC 0.8137**, degree spread +0.105.
- superseded: `9Xr84fs9` (15 feat, per-disease 0.774) · `6EtVWdE2` (run 1, 8 feat, 0.761 — **failed**)
  · `EHsHTJTG` (run 2, 10 feat, 0.777) · `5t2ek90a` (candidate_2 filter variant)

**Read TARGET_PRIORITIZER §6f/§6g/§6h before touching the model** — the feature audit, the
ablation results, and the mandatory feature-handling standard.

Zones: `enriched_graph features_1`, `enriched_resampling_1`, `validation`, `persona`,
**`family validation`** (per-family AUC + top-genes; all S3/parquet on `dataiku-managed-storage`).
Kuzu snapshot = folder **`enriched_clean-gFdnaU` (`tblWzpfx`)** — all 10 `compute_enriched_*`
Cypher/graph-feature recipes point at it.

**Read TARGET_PRIORITIZER §6d/§6e/§8b first** — three leaks found and fixed, the granularity
finding, and the Visual Graph Cypher queries.

## Next up
- **Discuss disease-level granularity** — §6e shows family aggregation buys AUC
  (breast cancer 0.704 → 0.907) but costs specificity (mechanism-specific DNA-repair genes →
  pan-cancer drivers). Current recommendation: **split by family, report by disease.**
- **Run the §8b Cypher queries** in the Graph Explorer (MRN-complex demo: RAD50/MRE11 novel
  + NBN known). Stretch: materialize `predicted_score` as gene-node properties so the queries
  stop needing pasted gene lists.
- **Apples-to-apples model comparison** — candidate_2's population is a strict *subset* of
  candidate_3's, so their AUCs aren't directly comparable; score `9Xr84fs9` on
  `enriched_test_set_2` to settle it.
- **Druggability / target class is the top remaining feature gap** (§5b new-candidates table).
  It's the only thing that addresses the unresolved **ligand-vs-receptor** problem — the model
  ranks non-druggable secreted peptides (GCG/GIP/IAPP) above the druggable receptors that are the
  actual known targets (GLP1R/GIPR/CALCR). Cheapest first step: `is_plasma_membrane` /
  `is_secreted` from GO cellular_component, **already in the graph** (7,569/20,861 genes).
- **§5b still unbuilt**: `disease_phenotype_context`, `dwpc_GCcGD`, `dwpc_GHD` (blocked).
  `has_inflammatory_go_annotation` was built and **rejected** (88% null, AUC exactly 0.500);
  `dwpc_GFGD`/`dwpc_GBGD` are built and are the current baseline's biggest win.
- Optional stretch, undecided: UBERON+Bgee anatomy, CTD, SIDER.

## Sharp edges (bit us repeatedly — check these first)
- **`node_index` is NOT stable** across `compute_kg` rebuilds (positional `reset_index`).
  Always re-derive via `(node_id, node_type, node_source)`. Current personas:
  breast cancer **15347**, breast carcinoma **16029**, obesity disorder **16415**,
  morbid obesity **61925**.
- **Stale schemas** on datasets whose upstream changed → rebuild with `--auto-update-schema`
  (hit on `validation_set_personas`, `persona_scored`).
- **Visual filter recipes can silently ignore the shown expression** if `uiData.$filterOptions`
  is `"rules"` with a half-configured `conditions` block — set `mode`/`$filterOptions` to
  `"CUSTOM"`. This caused a 14.79M-vs-6.75M row discrepancy that survived clean rebuilds.
- **Manually-created datasets need `"managed": true`** or builds fail with
  *"Clearing external datasets … is forbidden."*
- **Execute Cypher *recipe*** is unreliable on this graph (opaque `IndexError`; buffer-pool
  OOM on `1..3` expansion **and on the GO metapaths even with a fanout guard**). The interactive
  Explorer works; heavy graph features are all Python now
  (`compute_enriched_prox_closest_bfs_test`, `compute_enriched_rwr_score_1`,
  `compute_dwpc_go_metapaths`). For metapath DWPCs the trick is that the weight **factorizes** —
  associate right-to-left so you never form the gene×gene matrix.
- **Audit `per_feature` after EVERY lab deploy.** DSS guesses `rescaling`/`missing_impute_with`
  inconsistently — run 3's deploy came back `NONE`/`CONSTANT` on 9 of 12 features, run 2's mostly
  correct, on identical data. Standard is `AVGSTD` + `IMPUTE MEAN` everywhere (TARGET_PRIORITIZER §6h);
  `CONSTANT 0` on a high-null-gap feature re-opens the missingness leak.
- **Report macro per-disease AUC, never pooled.** Pooled overstates by ~9 pts and hid a real
  regression in ablation run 1 (pooled flat, per-disease −0.013).
- **`prediction` column is near-useless for discovery** — the threshold is F1-optimised against a
  ~2% base rate, so 590/762 known obesity targets are false negatives. Rank and take top-N.

## How I want you to work (my preferences)
- **Never `git commit`/`push` without asking me first.** Make changes, summarize, ask.
- **Joins go in visual Join recipes, not pandas `.merge()`** in Python. Python extracts
  only load + parse to native ids; visual recipes do grounding/harmonization.
- Verify with real data (row counts, schema, sample), not just exit 0.
- DSS build gotchas (see PRIMEKG_MAPPING §8): after a visual harmonize, `set-schema`
  all-string then build **without** `--auto-update-schema` (else numeric ids re-infer as
  bigint and break the cross-source stack); multi-input joins are **star** (chained
  lookups need sequential joins); **delete a stale output dataset before recreating its
  recipe**; and **`dku dataset delete` silently cascade-deletes recipes that consume it**
  (re-list recipes after any dataset delete).

## Useful commands
```
export DKU_PROJECT=KNOWLEDGE_GRAPH_PRIMEKG
dku flow zones                          # 8 source zones
dku recipe list ; dku dataset list
dku dataset count kg ; dku dataset head graph_nodes --format json
dku dataset head kg --rows 800000 --format json   # relation breakdown
dku webapp logs lVWgU2m                 # Visual Graph Editor health
dku job run --target graph_nodes --type RECURSIVE_BUILD --auto-update-schema --wait
```

## First message suggestion
"Read the POC document set (PROJECT_CONTEXT, PRIMEKG_MAPPING, TARGET_PRIORITIZER,
RESEARCH_NOTE), confirm the live flow state via `dku`, and summarize what's built and
what's next. Then <your task>."
