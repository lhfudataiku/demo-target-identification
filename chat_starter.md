# Chat starter — Target Identification POC (paste into a new chat)

You are my project assistant on a **Dataiku DSS proof-of-concept** that recreates the
**PrimeKG** biomedical knowledge-graph pipeline for drug-discovery **target
identification**, and renders it with the **Visual Graph** plugin.

## Orient yourself first (do this before acting)
1. Read the POC document set (source of truth — trust over your memory):
   - **`PROJECT_CONTEXT.md`** — project view: purpose/personas §1–4, sources in/out §5–6,
     build status + node/edge provenance §7, PrimeKG comparison §8. Decisions in the appendix.
   - **`PRIMEKG_MAPPING.md`** — engineering view: schema §1, MONDO-vs-UMLS §2, flow zones +
     build gotchas §4, entity→source mapping §5. Decisions in the appendix.
   - **`TARGET_PRIORITIZER.md`** — Part 2, in MLOps order: data §4, features §5, splitting §6,
     hyperparameters §7, feature/model selection §8, validation §9, persona results §10.
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
- **`m3-f13` (`L06mKJEF`) = PRODUCTION** (13 features). Pooled AUC 0.898,
  **macro per-disease AUC 0.8175**, per-family 0.7997, degree spread +0.110.
- ladder: `baseline-f8` (`oNBxtK2z`, 0.761 per-disease — pruning alone **failed**) →
  `m2-f11` (`uvUgakzg`, +PPI provenance controls) → `m3-f13` (+`dwpc_GFGD`/`dwpc_GBGD`).
- `GlVckALL` / `ciuubnE2` are pre-enrichment leftovers — safe to retire.
- **Druggability annotation** (`enriched_gene_druggability`, 92.2% coverage) joins into
  `target_candidates`, now **top-50** per persona with `druggability_class` /
  `ot_sm_tractable` / `has_approved_drug`. It annotates, it does **not** re-rank.

**Read TARGET_PRIORITIZER §7.1 before touching the model** — the mandatory feature-handling
standard. §6 is the leakage/splitting story; §8 is the ablation.

Zones: `enriched_graph features_1`, `enriched_resampling_1`, `validation`, `persona`, `druggability`,
**`family validation`** (per-family AUC + top-genes; all S3/parquet on `dataiku-managed-storage`).
Kuzu snapshot = folder **`enriched_clean-gFdnaU` (`tblWzpfx`)** — all 10 `compute_enriched_*`
Cypher/graph-feature recipes point at it.

## Next up
- **Run the §10.4 Cypher queries** in the Graph Explorer (MRN-complex demo: RAD50/MRE11 novel
  + NBN known; GLP1R sparse-neighbourhood contrast shot). Stretch: materialize
  `predicted_score` as gene-node properties so the queries stop needing pasted gene lists.
- **`m2-f11` per-disease AUC was never captured** (only pooled) — run the validation chain
  against `uvUgakzg` if the full three-rung per-disease comparison is wanted.
- **Stricter `has-path-evidence` experiment** — a ≥2-of-3 evidence variant nearly eliminates
  the missingness channel (mean |gap| 16.5 → 4.2 pp, positives 1.89% → 4.30%) at the cost of
  half the positives. Logged in TARGET_PRIORITIZER appendix; not run.
- **Ligand-vs-receptor is still unfixed in the *ranking*.** Druggability is now annotated
  (§10.5) so it's visible, but the model doesn't see it — secreted ligands still outrank
  receptors. Options: post-hoc re-sort within `druggability_class`, or add as a model feature
  (expect **no AUC gain** — druggability is orthogonal to the `is_target` label).
- **Demo diseases: breast cancer + obesity disorder.** breast carcinoma returns 50/50 known
  targets (no novelty); morbid obesity 0/50 known but scores decay to 0.749.
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
