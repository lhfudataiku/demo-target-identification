# Webapp dataset map and serving-flow options

> **Lifecycle:** Planning (draft) · **Audience:** DSS flow maintainers deciding the flow migration ·
> **Authority:** what the released webapp reads, field by field, and the recipe and dataset counts of
> re-zoning versus rebuilding the serving flow once the notebook components leave it · **Update
> when:** a backend route changes the datasets or columns it reads, or the flow after zone 31 changes ·
> **Generated dependencies:** none (measured by hand, §6) · **Excludes:** the boundary rule and target
> zones (D14, D15, in [`WEBAPP_REDESIGN_SCOPE.md`](../../archive/WEBAPP_REDESIGN_SCOPE.md)) and the
> migration's sequence, in [`FLOW_MIGRATION_WORKPLAN.md`](FLOW_MIGRATION_WORKPLAN.md), whose M1
> inventory this feeds.

**Status: DRAFT — measured 2026-10-27, read-only. Nothing in DSS or the webapp changed.**

Premise: the notebooks stay in the repository, and the `validate_notebooks` scenario is dropped. A
supporting evidence project reads this project's zones 00–31 and recomputes what the notebooks need
([`FLOW_MIGRATION_WORKPLAN.md`](FLOW_MIGRATION_WORKPLAN.md) M2). Notebook-only objects therefore
leave the main project: they move to the evidence project, or are deleted when nothing reads them.
The counts below are for the main project.

## 1. Summary

| | today | after the evidence project, **re-zoned** | after the evidence project, **rebuilt by function** |
|---|--:|--:|--:|
| recipes after zone 31, plus `compute_breast_panel` | 47 | 41 | 32 |
| datasets, same scope | 47 | 41 | 32 |
| of which served to the webapp | 21 | 21 | 20 |
| of which intermediate | 20 | 20 | 12 |
| of which notebook-only or unread | 6 | 0 | 0 |
| scoring runs of the champion over the shortlist | 2 | 2 | 1 |
| webapp code changes | — | none | two routes read one dataset instead of another |

- **The notebook-only objects leave the main project**, whichever plan is chosen (§3): 6 recipes and
  6 datasets. Four move to the evidence project and two unread ones are deleted. Everything else
  after zone 31 lies on a path to a webapp read.
- **Rebuilding removes 9 more recipes and 9 more datasets** (§4.2, settled in §6.1): one of the two identical
  scoring runs, a 297 MB pass-through copy of `scored_champion`, and a three-recipe chain that feeds
  `persona_enrichment` with columns the webapp never reads.
  - Three of the removed datasets are read by the notebooks: `novel_discovery_eval`,
    `persona_candidates` and `persona_enrichment`. Their evidence-project copies stay.
- **Re-zoning is mostly renames**: A1→S2, A2→S3, A3→S4, one recipe and dataset moved from 40 to S1,
  A4 deleted (§4.1).
- Two facts gate any rebuild or re-run of the shortlist chain: the two scoring runs agree exactly
  (max |Δ| = 0 on 105,702 pairs), and **4,514 rows have tied scores whose rank is arbitrary** (§5.1).

## 2. What the webapp reads, by function

Row counts were counted live on 2026-10-27. "Scope" is which rows exist, which is not always what the
page shows.

### 2.1 Shortlist page

The shortlist covers the **12 diseases with `demo_panel_config.in_act4`**. These are 6 oncology terms
(HER2+, triple-negative and luminal B breast; endometrium and endometrial serous adenocarcinoma; gastric
adenocarcinoma), lung adenocarcinoma, 2 autoimmune terms (rheumatoid and psoriatic arthritis) and 3
cardio-renal-metabolic terms (dilated cardiomyopathy, familial hypercholesterolemia, diabetes
mellitus). Each disease keeps its **whole eligible pool**, with no top-N cut: 2,563 genes
(triple-negative breast) to 13,445 (diabetes mellitus), 105,702 pairs and 15,018 distinct genes in
all.

| function | route | dataset | fields read | scope served |
|---|---|---|---|---|
| disease picker | `GET /api/candidates/diseases` | `dashboard_candidates` | `disease_index`, `disease_name`, `gene_index`, `is_target` | 12 diseases, grouped to a count and a known count |
| ranked list, filters, funnel | `GET /api/candidates` | `dashboard_candidates` | `disease_index`, `disease_name`, `gene_index`, `gene_name`, `rank_in_disease`, `score`, `rank_percentile`, `is_target`, `druggability_class`, `ot_class_l1`, `ot_sm_tractable`, `ot_ab_tractable`, `has_safety_liability`, `safety_flag`, `approved_for_disease`, `investigational_for_disease` | one disease's pool; filters are novel only, tractable (small molecule or antibody), not secreted, and `rank <= max_rank` (default 200, max 5,000) |
| candidate card | `GET /api/candidates/gene` | `dashboard_candidates` | `disease_pool_size`, `safety_events`, and 13 of the champion's 14 inputs: `dwpc_GBGD`, `dwpc_GFGD`, `dwpc_GGD`, `dwpc_GPGD`, `gene_n_pathways`, `gene_ppi_degree`, `ppi_adamic_adar`, `ppi_common_neighbors_z`, `ppi_evidence_depth`, `ppi_jaccard`, `ppi_multi_source_frac`, `prox_closest`, `shared_pathway_frac` (`prox_kernel` is not in the dataset and the card names it as missing) | one pair; each feature is placed as a percentile within its own disease's pool |
| gene identity header | `GET /api/candidates/identity` | `candidate_identity` | `node_index`, `node_id`, `node_name`, `hgnc_id`, `symbol`, `name`, `locus_type`, `location`, `alias_symbol`, `prev_symbol`, `gene_group`, `date_modified`, `ensembl_gene_id`, `uniprot_ids`, `source_file` | 20,861 gene nodes (all of them; 15,018 appear on the shortlist); one row per gene |
| drug records | `GET /api/candidates/drugs` | `drug_evidence_records` | `disease_index`, `gene_index`, `drug_id`, `drug_name`, `max_stage`, `relation`, `action_type`, `source_release` | 86,123 records over 1,554 diseases; **only 2,294 fall in the 12 shortlist diseases**, and they cover every pair the flags mark |
| top-5 SHAP drivers | `GET /api/candidates/drivers` | `candidate_shap_top5` | `disease_index`, `gene_index`, `shap_top5` (a JSON list of `feature`, `shap`, `value`, `percentile`) | 105,702 pairs, one per shortlist pair |
| trials and literature | `GET /api/candidates/sources`, `/sources/selection` | `dashboard_candidates`; `candidate_identity`; folder `act4_evidence_cache` | `disease_index`, `disease_name`, `anchor_name`; `node_index`, `node_name`, `symbol`, `name`, `alias_symbol`, `prev_symbol`; one JSON file per pair at `{disease_index}/{gene_index}.json` | any selected pair; the `prefill_evidence_cache` scenario fills 21 HER2+ pairs (ranks 1–20, plus ERBB2 and SMARCA2) |
| evidence assistant | `POST /api/assistant` | all of the above | the list row, the drivers, the drug records, the identity, and the cached trials and papers for the pair | one pair; tools: `graph search` (`b6Rpbve`, Kuzu folder `ytvuniN8`), Cortex CT.gov (`4I2L6YL`), Cortex PubMed (`FNxhpfF`) |

`dashboard_candidates` stores **63 columns; the webapp reads 32**. The other 31 are unread. They
include `top_shap_drivers` (superseded by `candidate_shap_top5`), the non-champion features
(`rwr_score`, `rwr_norm`, `pagerank`, `degree`, `triangles`, `eigenvector_centrality`,
`clustering_coefficient`, `ppi_common_neighbors`, `ppi_cn_expected`, `shared_pathway_count`,
`dwpc_GCD`, `disease_context`, `has_inflammatory_go_annotation`), the constraint and safety detail
(`lof_*`, `mis_oe`, `safety_dosing`, `n_safety_liabilities`), and the split and family keys.

### 2.2 *Why trust the list* page

**Section 1 — what the model can see** (`GET /api/evidence`). The whole graph is in scope; every table
is read entire as `label, count`.

| dataset | label column | rows |
|---|---|--:|
| `graph_node_type_counts` | `node_type` | 8 |
| `graph_relation_counts` | `relation` | 18 |
| `graph_node_source_counts` | `node_source` | 7 |
| `graph_ppi_provenance` | `ppi_sources` | 7 |
| `graph_label_evidence` | `datatypes` | 3 |

**Section 2 — reconstruction and calibration** (`GET /api/calibration`). The scope is the validation
split: **670 held-out diseases (668 with an AUC) in 505 disease families**.

| dataset | fields read | rows and scope |
|---|---|---|
| `validation_auc_by_disease` | `auc_disease` | 670 diseases → macro AUC, median, histogram, count below chance |
| `persona_enrichment` | `disease_index`, `disease`, `auc_disease`, `rank_enrichment`, `n_pos` | 670 → each disease's place in the distribution, and the enrichment quartiles |
| `orthogonality_scatter` | `auc_disease`, `auc_drug_targets` | 670 rows, 130 with a drug-target AUC → Pearson r |
| `family_auc_by_family` | `auc_family` | 505 families, 503 with an AUC → family macro AUC |
| `split_audit_2` | `split`, `rows`, `positives`, `pos_rate_pct`, `n_diseases`, `n_split_keys`, `n_anchor_families`, `overlap_*`, `straddling_split_keys` | 3 splits; leakage columns must sum to 0 |
| `hub_bias_meter` | `quintile`, `median_degree`, `mean_proba`, `pct_predicted_positive`, `n_genes`, `rho_degree_proba`, `threshold` | 5 degree quintiles |
| `disease_eligibility` | `is_eligible`, `count` | 2 rows (1,157 eligible of 27,153 diseases) |
| `enriched_dwpc_GGD`, `enriched_dwpc_GPGD`, `enriched_dwpc_GCD` (zone 10) | the `COUNT_RECORDS` and `BUILD_START_DATE` metrics only | the three pool-admission routes |
| saved model `hJLGoYn4` (zone 31) | the active version's precision, recall, F1, AUPRC, pooled AUC and lift | the champion card |

`persona_enrichment` carries the same 668 AUCs as `validation_auc_by_disease`, and its
`rank_enrichment` is `(hits_at_50 / 50) / (n_pos / (n_pos + n_neg))`. **Both can be computed from
`validation_auc_by_disease` alone**: recomputed that way, the difference is at most 7e-15.

**Section 3 — family panels** (`GET /api/families`, `GET /api/families/{family_id}`). The scope is
**3 families**: breast (15 terms, 14 scored, 4 leaves), stomach (6, 6, 3) and uterine (8, 8, 4).
`demo_panel_config` holds 35 rows: those 29 family terms plus the 6 shortlist diseases that belong to
no family.

| dataset | fields read | rows and scope |
|---|---|---|
| `demo_panel_config` | `act3_family`, `disease_family_id`, `disease_index`, `act3_role` | 35 rows; family membership and leaf role |
| `family_panel_metrics` | `act3_family`, `in_act3`, `in_act4`, `disease_index`, `disease`, `auc_disease`, `auc_lo95`, `auc_hi95`, `auc_trustworthy`, `n_pos`, `hop_depth`, `act3_role` | 35 rows; per-term AUC with interval, ordered by `hop_depth` |
| `family_panel_overlap` | `act3_family`, `disease_a`, `disease_b`, `all_overlap`, `novel_overlap`, `jaccard_top50`, `depth_gap`, `pair_kind`, `near_duplicate` | 148 term pairs within a family |
| `family_panel_programme` | `act3_family`, `subtype`, `gene`, `scope`, `rank_in_subtype` | 550 rows over the 11 leaf subtypes (common, partial, specific) |
| `family_panel_top50` | `disease`, `gene`, `rank_in_disease` (read where `rank <= 50`) | 2,752 rows over 35 terms; the page reads 1,750 |
| `persona_enrichment` | `disease_index`, `rank_enrichment` | the thin-disease card |

### 2.3 Dependencies that are not served datasets

- **Outside the serving zones, metadata only:** the three zone-10 DWPC metrics and the saved model's
  metrics (§2.2), and the Kuzu folder `ytvuniN8` in zone 04. The graph tool reads that folder; it is
  merged from `DEMO_KG_LS.UBUlwwxT` by `compute_ytvuniN8`. D14 says the backend reads only serving
  zones, so it should name these as exceptions.
- **`act4_evidence_cache`** (`CB9xqCGg`): written by the webapp and the `prefill_evidence_cache`
  scenario. No recipe touches it, and `dku flow zones` lists it in no zone.
- **Shortlist scope comes from the family panels.** `filter_persona_diseases` joins the validation
  split to `demo_panel_config` filtered on `in_act4`. So the build order is S3 → S4 → 40 → S1, not
  "shared core first" as D15 draws it (§5.4).

## 3. What leaves the main project

The rule: a recipe stays if anything the webapp reads depends on it. Otherwise it moves to the
evidence project if a notebook reads its output, and is deleted if nothing does. Under either plan:

| zone | recipe → dataset | read by | fate |
|---|---|---|---|
| A4 | `compute_known_drug_truth` → `known_drug_truth` | `nb2`, `nb4`, and the two A4 recipes below | moves |
| A4 | `compute_filter_three_axes` → `filter_three_axes` | `nb4` | moves; its `target_candidates_2` input (zone 40) is replaced on the evidence side |
| A4 | `compute_pool_reachability` → `pool_reachability` | `nb2` | moves |
| 31 | `compute_breast_panel` → `breast_panel_metrics` | a notebook only; the governed breast claim's authority is `nb4` §8.10 | moves |
| 40 | `compute_shap_drivers_long` → `shap_drivers_long` | only the next recipe | deleted |
| 40 | `compute_shap_driver_frequency` → `shap_driver_frequency` | nothing (an orphan) | deleted |

`compute_raw_ot_known_drug` → `raw_ot_known_drug` (zone 02) feeds only `compute_known_drug_truth`, and
the notebooks read it directly. It stays in the main project as an import the evidence project reads.

Three things outside the flow assume `breast_panel_metrics` is in the main project and change with
the move:

- `build-governance/POLICY.json` `allowed_targets`, which is keyed by project. Its other entry,
  `breast_panel_overlap`, was deleted on 2026-09-03.
- `IDENTITY_RECIPES` in `tools/check_governed_values.py` (`DEC-OPS-006`).
- The keep entry in `.index/_dead.json`.

**Not removable by this rule.** `drug_target_benchmark`, `novel_discovery_eval` and
`persona_candidates` look like notebook datasets, but each sits on a path to a served dataset
(`orthogonality_scatter` and `persona_enrichment`). The rebuild in §4.2 removes two of the three from
the main project, and the evidence project keeps its own copies.

## 4. Re-zone versus rebuild

### 4.1 Re-zone: move what exists, change no recipe

| target zone | contents | how it gets there |
|---|---|---|
| `40` shared core | `validation_set_personas_2`, `persona2_scored`, `persona2_scored_shap`, `top_candidates`, `top_annotated`, `target_candidates_2`, `disease_pool_sizes`, `candidates_annotated` (8 recipes, 8 datasets) | already there |
| `S1 Shortlist` | `dashboard_candidates`, `candidate_identity`, `drug_evidence_records`, `drug_protein_actions`, `persona2_scored_shap5`, `candidate_shap_top5` (6, 6) | move `finalize_dashboard_candidates` and `dashboard_candidates` from 40 |
| `S2 Evidence · graph` | the 5 A1 datasets (5, 5) | rename A1 |
| `S3 Evidence · reconstruction` | the 16 A2 datasets (16, 16) | rename A2 |
| `S4 Evidence · family panels` | the 6 A3 datasets (6, 6) | rename A3 |
| — | A4 | delete the zone once §3 empties it |

**Totals: 41 recipes and 41 datasets, 21 served and 20 intermediate.** No dataset is renamed, so the
webapp, the identity checks and the governed claims do not change. Moving a recipe between zones
changes no data, so nothing needs building. The re-zone is the workplan's M3. The rebuild's
build-beside, compare and switch (M4–M5) are needed only for §4.2.

What it leaves as it is: two scoring runs (~8 min each per full rebuild), the 297 MB
`family_validation_scored` copy, 31 unread columns on `dashboard_candidates`, and the
`persona_candidates` chain.

### 4.2 Rebuild: one chain per served dataset, from the fields in §2

Counts are recipes / datasets, after §3. **S1 is the pattern.** It was built for the redesign
directly from upstream datasets with visual recipes. Its five recipes stay as they are, and the
rebuilt `dashboard_candidates` chain joins them in S1, reading S1's scoring run.

| function | today (after §3) | rebuilt | what changes |
|---|--:|--:|---|
| shortlist (40 + S1) | 14 / 14 | 9 / 9 | below |
| evidence §1 (S2) | 5 / 5 | 5 / 5 | none |
| evidence §2 (S3) | 16 / 16 | 12 / 12 | below |
| evidence §3 (S4) | 6 / 6 | 6 / 6 | inputs repointed only |
| **total** | **41 / 41** | **32 / 32** | **−9 of each** (settled in §6.1) |

**Shortlist, from 14 to 9 recipes.**

| step | today | rebuilt |
|---|---|---|
| restrict to the 12 diseases | `filter_persona_diseases` | same |
| score | `score_persona_candidates` (3 explanations) **and** `score_persona_candidates_shap5` (5 explanations), identical probabilities | the five-explanation run only |
| driver string | `compute_top_shap_drivers_1` (`top_shap_drivers`, which the webapp does not read) | removed |
| rank | `rank_per_disease` (row number by `proba_1`) | a window over the five-explanation output: the rank with ties (§5.1), and the pool size as a count over the partition |
| pool size | `count_candidates_per_disease` → `disease_pool_sizes`, then a join | folded into the window: a count over its unbounded frame (§6.1) |
| annotate | `decorate_target_candidates`, then `join_disease_name`, then `join_dashboard_annotations` (three joins) | one join: druggability, safety, gene name, disease name, drug flags |
| finalize | `finalize_dashboard_candidates` (rename, fill, `rank_percentile`) | same, without the rename |
| top-5 drivers, drug records, identity | `compute_shap_top5`; `group_drug_protein_actions` + `join_drug_evidence_records`; `join_candidate_identity` | same |

This removes `persona2_scored`, `persona2_scored_shap`, `top_annotated`, `target_candidates_2` and
`disease_pool_sizes`. `top_candidates` and `candidates_annotated` stay as the outputs of the rebuilt
window and join. One scoring run of 105,702 pairs is saved, measured at 8 min 13 s on 2026-10-26.

**Evidence §2, from 16 to 12.**

| chain | today | rebuilt |
|---|---|---|
| per-disease AUC | window → group → prepare (`validation_auc_by_disease`) → prepare (`validation_auc_ci`) | window → group → join (disease name) → one prepare with the AUC, the interval, `auc_trustworthy`, `module_size` and `rank_enrichment` |
| enrichment | `compute_novel_discovery_eval` → `compute_persona_candidates` → `compute_persona_enrichment` | removed; the fields come from the prepare above, and `persona_enrichment` is no longer served |
| per-family AUC | sync (`family_validation_scored`, a 297 MB copy of `scored_champion`) → window → group → prepare | window directly on `scored_champion` (it already carries `disease_family_id`) → group → prepare |
| orthogonality, hub bias, split audit, eligibility | 5 recipes | same |

This removes 5 recipes (`compute_validation_auc_ci`, `compute_novel_discovery_eval`,
`compute_persona_candidates`, `compute_persona_enrichment`, `compute_family_validation_scored`) and
adds 1 (the name join). `calibration.py` and `families.py` would read `disease` and
`rank_enrichment` from `validation_auc_by_disease` instead of `persona_enrichment`.

**Evidence §3.** It keeps its 6 recipes. `compute_family_panel` would read
`validation_auc_by_disease` instead of `validation_auc_ci`. `compute_demo_panel_config` would read its
disease names from `graph_nodes`, already one of its inputs, instead of `persona_enrichment`, in both
projects. That second change alters an identity recipe, so it goes through `DEC-OPS-006`
(`DEC-ARCH-007`, proposed 2026-10-28).

### 4.3 Trims that remove rows or columns but no recipes

These are not counted above, and each fits either plan:

- `dashboard_candidates`: keep the 32 read columns (63 today).
- `drug_evidence_records`: restrict to the shortlist diseases, from 86,123 rows to 2,294. Building
  the drug flags from it, rather than from zone 20's `drug_evidence_pairs`, would leave the badges and
  the records with one source. That swaps one recipe for another, net zero.
- `validation_set_scored_windows` (284 MB) and `family_validation_ranked` (292 MB): the window
  recipes carry all of `scored_champion`'s 45 columns, but the groups need only the keys, the label
  and the rank.
- `orthogonality_scatter`: 2 of its 21 columns are read.

## 5. What either plan must handle

### 5.1 Tied scores make today's shortlist rank non-deterministic

**4,514 of 105,702 rows tie on score within their disease**, and `rank_per_disease` numbers them in
arbitrary order. Ranking `persona2_scored_shap5` again reorders 3,156 rows, all of them tied; no
untied row moves. Ties start at rank 14: 2 rows in the top 20 and 11 in the top 200, all in diabetes
mellitus and psoriatic arthritis. HER2+'s top 200 has none, so the 21 pre-filled pairs are not
affected.

**Decided 2026-10-28: the shortlist ranks with ties** (the workplan's M0). Tied scores share the
lowest rank of their group, and the next rank skips (1, 2, 2, 4).

- 3,611 rows change rank, all tied; no untied row moves. Dense ranking would shift 92,909 untied
  rows.
- `rank_percentile` changes on 2,155 rows.
- No tie group straddles rank 20, 50 or 200, so every cut-off selects the same rows.
- Every tie group holds consecutive ranks today. So the rebuild's compare can predict each new rank
  exactly: it is the lowest old rank in the group.

Until the rebuild, a run of `Refresh_serving_layer` or any build of zone 40 still reorders tied rows.

### 5.2 Scenarios

`Refresh_serving_layer` rebuilds A1, A2, A3 and 40 non-recursively. It builds `shap_drivers_long`
and `shap_driver_frequency`, and none of S1, so it has to be rewritten under either plan.
`disease_pool_sizes` currently has no stored data (its storage path does not exist), so the existing
`join_dashboard_annotations` cannot run until it is rebuilt. `prefill_evidence_cache` reads only
`dashboard_candidates` and the cache folder, and is unaffected.

### 5.3 Consumers outside the flow

Both project dashboards and their twelve dataset-reading insights were deleted on 2026-10-27, so
nothing outside recipes and the webapp reads these datasets. Two insights remain, and neither reads a
dataset: `ZZ_TMP_probe_webapp` (a leftover probe) and `published_kg_ls` (the Visual Graph plugin's
static file).

### 5.4 Zone order

The core depends on the family panels: `validation_auc_ci` (S3) → `family_panel` →
`demo_panel_config` (S4) → `filter_persona_diseases` (40) → S1. If S1–S4 are laid out after the core,
the flow draws arrows backwards from S4 into 40. Placing `family_panel` and `demo_panel_config` with
the core, as the panel definition both pages use, keeps the arrows one way. This is a D15 amendment.

## 6. M1 results: the serving side (2026-10-28)

These are the serving half of [`FLOW_MIGRATION_WORKPLAN.md`](FLOW_MIGRATION_WORKPLAN.md) M1, for
approval. The evidence half is [`EVIDENCE_PROJECT_DESIGN.md`](EVIDENCE_PROJECT_DESIGN.md). The live
flow was re-checked on 2026-10-28 and is unchanged since the 2026-10-27 measurement.

### 6.1 One window recipe gives the rank and the pool size: 32 recipes

**The flow ends at 32 recipes and 32 datasets, not 33.**

- All three window recipes in the flow have frame limits off (`enableLimits: false`) with ordering
  on. The `dku` window builder documents that setting as unbounded on both sides
  (`--frame-unbounded`).
- So in the rebuilt shortlist window, ordered by `proba_1`, *rank* gives the rank with ties, and a
  *count* aggregation over the same unbounded frame gives the whole disease partition: the pool
  size.
- `count_candidates_per_disease`, `disease_pool_sizes` and their join are not needed.
- M4's compare confirms the count against the stored `disease_pool_size`.
- The builder's `--keep-columns` option also covers the optional column trims on the AUC windows.

### 6.2 Zone 20 splits into three zones, but not along the planned job lines

Split by job name, drug annotation and gene annotation depend on each other in both directions:

- gene → drug: `gene_crosswalk` feeds `compute_ot_drug_mapped`, and `enriched_gene_localization`
  feeds `compute_drug_joined`;
- drug → gene: `drug_classified` feeds `compute_enriched_gene_druggability_v2`.

That is a zone cycle, the kind rejected on 2026-09-03. Placing the druggability output with the drug
chain that computes it makes the split one-way:

| zone | datasets | reads from zone 20 |
|---|---|---|
| gene annotation | `gene_crosswalk`, `enriched_gene_localization`, `gene_safety_joined`, `enriched_gene_safety_v2` | — |
| druggability and drug evidence | `ot_drug_mapped`, `drug_joined`, `drug_classified`, `enriched_gene_druggability_v2`, `drug_evidence_pairs` | gene annotation only |
| disease family and split key | `hetionet_disease_slim`, `disease_family_id` | — (it reads zone 12's `enriched_graph_features_1`; zone 30 reads it) |

Every move is `dku flow move`, which changes zone membership only; nothing is built.

### 6.3 Moving and describing zones

- **`dku flow move`** moves datasets, recipes, folders and models to a named zone, creating it if
  needed. M3's moves need no UI work.
- **`dku flow set-zone`** renames a zone and writes its `shortDesc` (`--short-desc`). M6's
  description rewrite no longer needs a scenario using the Python API.

### 6.4 The M1 table: every dataset after zone 31, plus `breast_panel_metrics`

"Copy" means the evidence project builds its own dataset of the same name ([`EVIDENCE_PROJECT_DESIGN.md`](EVIDENCE_PROJECT_DESIGN.md) §3).
"Rebuilt" means a new chain replaces the old one in M4, and M6 retires the old one. The rebuild also
adds one intermediate not listed here: the disease-name join in S3 (§4.2).

| dataset | zone | webapp route | notebooks | recipe consumers | evidence project (M2) | zone after M3 | after M4–M6 |
|---|---|---|---|---|---|---|---|
| `breast_panel_metrics` | 31 | — | nb4 | — | moved | — | evidence project |
| `candidates_annotated` | 40 | — | — | `finalize_dashboard_candidates` | — | 40 | rebuilt, S1 |
| `dashboard_candidates` | 40 | candidates, sources, assistant, prefill | nb6, nb7 | `compute_shap_drivers_long` | new: a slim copy of the same name | S1 | S1 (rebuilt) |
| `disease_pool_sizes` | 40 | — | — | `join_dashboard_annotations` | — | 40 | removed (M6) |
| `persona2_scored` | 40 | — | — | `compute_top_shap_drivers_1` | — | 40 | removed (M6) |
| `persona2_scored_shap` | 40 | — | — | `rank_per_disease` | — | 40 | removed (M6) |
| `shap_driver_frequency` | 40 | — | — | — | — | — | deleted (M2) |
| `shap_drivers_long` | 40 | — | — | `compute_shap_driver_frequency` | — | — | deleted (M2) |
| `target_candidates_2` | 40 | — | — | `compute_filter_three_axes`, `join_dashboard_annotations`, `count_candidates_per_disease` | — | 40 | removed (M6) |
| `top_annotated` | 40 | — | — | `join_disease_name` | — | 40 | removed (M6) |
| `top_candidates` | 40 | — | — | `decorate_target_candidates` | — | 40 | rebuilt, S1 |
| `validation_set_personas_2` | 40 | — | — | `score_persona_candidates_shap5`, `score_persona_candidates` | — | 40 | 40 |
| `candidate_identity` | S1 | candidates, sources, assistant | — | — | — | S1 | S1 |
| `candidate_shap_top5` | S1 | candidates, assistant | — | — | — | S1 | S1 |
| `drug_evidence_records` | S1 | candidates, assistant | — | — | — | S1 | S1 |
| `drug_protein_actions` | S1 | — | — | `join_drug_evidence_records` | — | S1 | S1 |
| `persona2_scored_shap5` | S1 | — | — | `compute_shap_top5` | — | S1 | S1 |
| `graph_label_evidence` | A1 | evidence | — | — | — | S2 | S2 |
| `graph_node_source_counts` | A1 | evidence | — | — | — | S2 | S2 |
| `graph_node_type_counts` | A1 | evidence | — | `compute_disease_eligibility` | — | S2 | S2 |
| `graph_ppi_provenance` | A1 | evidence | — | — | — | S2 | S2 |
| `graph_relation_counts` | A1 | evidence | — | — | — | S2 | S2 |
| `disease_eligibility` | A2 | calibration | — | — | — | S3 | S3 |
| `drug_target_benchmark` | A2 | — | nb3, nb6 | `compute_persona_candidates`, `join_orthogonality` | copy | S3 | S3 |
| `family_auc_by_family` | A2 | calibration | nb3 | — | copy | S3 | S3 |
| `family_auc_grouped` | A2 | — | — | `compute_family_auc` | copy | S3 | S3 |
| `family_validation_ranked` | A2 | — | — | `group_family_auc` | copy | S3 | S3 (rebuilt: reads scored_champion) |
| `family_validation_scored` | A2 | — | — | `window_family_rank` | — | S3 | removed (M6) |
| `hub_bias_meter` | A2 | calibration | — | — | — | S3 | S3 |
| `novel_discovery_eval` | A2 | — | nb4, nb6 | `compute_persona_candidates` | copy | S3 | removed (M6) |
| `orthogonality_scatter` | A2 | calibration | — | — | — | S3 | S3 |
| `persona_candidates` | A2 | — | nb4 | `compute_persona_enrichment` | copy | S3 | removed (M6) |
| `persona_enrichment` | A2 | calibration, families | nb7 | `compute_demo_panel_config` | copy | S3 | removed (M6) |
| `split_audit_2` | A2 | calibration | nb2 | — | copy | S3 | S3 |
| `validation_auc_by_disease` | A2 | calibration | nb3, nb5, nb6 | `compute_validation_auc_ci`, `compute_persona_candidates`, `join_orthogonality` | copy | S3 | S3 (rebuilt, wider) |
| `validation_auc_ci` | A2 | — | — | `compute_family_panel` | copy | S3 | removed (M6) |
| `validation_set_scored_grouped` | A2 | — | — | `compute_validation_auc_by_disease` | copy | S3 | S3 |
| `validation_set_scored_windows` | A2 | — | — | `compute_validation_set_scored_grouped` | copy | S3 | S3 |
| `demo_panel_config` | A3 | families | nb7 | `compute_family_panel_metrics`, `compute_family_panel_top50`, `compute_family_panel_programme`, `filter_persona_diseases`, `compute_family_panel_overlap` | copy | 40 | 40 |
| `family_panel` | A3 | — | nb7 | `compute_family_panel_metrics`, `compute_demo_panel_config` | copy | 40 | 40 |
| `family_panel_metrics` | A3 | families | — | — | — | S4 | S4 |
| `family_panel_overlap` | A3 | families | nb4, nb6, nb7 | — | copy | S4 | S4 |
| `family_panel_programme` | A3 | families | nb7 | — | copy | S4 | S4 |
| `family_panel_top50` | A3 | families | — | `compute_family_panel_programme`, `compute_family_panel_overlap` | copy | S4 | S4 |
| `filter_three_axes` | A4 | — | nb4 | — | moved | — | evidence project |
| `known_drug_truth` | A4 | — | nb2, nb4 | `compute_filter_three_axes`, `compute_pool_reachability` | moved | — | evidence project |
| `pool_reachability` | A4 | — | nb2 | — | moved | — | evidence project |

**Totals after M6:** 3 datasets in 40, 8 in S1, 5 in S2, 12 in S3 (with the new name join) and 4 in
S4, which is 32. Two are deleted in M2, four move to the evidence project, and ten are removed in M6.

## 7. Method

Read-only, 2026-10-27:

- **Webapp reads:** taken from `webapp/backend/routes/` and `services/` (column lists, filters,
  metric reads, tool IDs).
- **Lineage:** built from `dku recipe get-settings` for all 95 recipes and `dku flow zones`.
- **Row counts:** from `dku dataset count`. Several stored `COUNT_RECORDS` metrics in the info
  panels are stale.
- **Scope and equivalence checks:** run on CSV downloads of the served datasets and
  `persona2_scored_shap5`, kept in the session scratchpad and not in `data/`.
- **Consumers:** checked with `dku dataset usages` and the insight and dashboard listings.
