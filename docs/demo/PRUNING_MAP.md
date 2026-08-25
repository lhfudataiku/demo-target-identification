# Pruning map

Live DSS: **125 datasets across 13 zones**, cross-referenced against the recipe graph, `notebooks/*.py`, and `webapp/backend.py`.

**`downstream` counts recipes whose CODE reads the dataset**, not recipes that merely declare it as an input. Those differ: `dku recipe replace-input` rewires the declaration and leaves the code alone, which is how five recipes ended up declaring `_v2` while reading the old name.

| flag | meaning |
|---|---|
| DELETE | recomputed in a notebook and verified — safe to remove |
| KEEP | read by a notebook, or its provenance no longer exists — must survive |
| scaffold | verification harness, delete when the verify recipes are converted to scenario steps |
| serving (webapp TBD) | zone A1-A4: built for a webapp UI that does not exist yet — NOT an orphan |
| **ORPHAN** | nothing reads it, nothing consumes it, not serving — the pruning candidates |

## Summary

- endpoints (read by a notebook or the webapp): **25**
- zone A1-A4 serving datasets (consumer not built yet): **40** — excluded from pruning
- genuine orphans: **17**

> The naive rule *delete what nothing reads* flags all 40 A-zone datasets, because `webapp/backend.py` reads only three of them today. The serving layer's consumer is the unbuilt UI. Zone membership, not reference counting, is what separates them.

### Shared-recipe caution

`pool_unreachable_targets` is unread, but `compute_pool_reachability` produces it **and** `pool_reachability`, which nb2 reads. The dataset may go; **the recipe must not**.

### Scaffold — delete with the harness, not before

`nb1_verify`, `nb3_verify`, `nb6_assertion_results` and their three verify recipes exist so codifications can be verified from the CLI. Convert them to `custom_python` scenario steps (as `assert nb2` already is) and all six leave the flow together.

### The orphan list — nothing reads these, nothing consumes them

| dataset | zone | producing recipe | type |
|---|---|---|---|
| `breast_shortlist` | 90 Notebook — validation evidence | `compute_breast_shortlist` | python |
| `drug_target_benchmark_staged` | 90 Notebook — validation evidence | `compute_drug_target_benchmark_staged` | python |
| `enriched_gene_druggability` | 20 Annotations & split key | `compute_gene_druggability` | python |
| `enriched_gene_safety` | 20 Annotations & split key | `compute_gene_safety` | python |
| `family_top_genes_named` | 90 Notebook — validation evidence | `join_family_gene_name` | join |
| `llm_hx` | Default | `—` | — |
| `maturity_confound` | 90 Notebook — validation evidence | `compute_maturity_confound` | python |
| `model_comparison` | 90 Notebook — validation evidence | `compute_model_comparison` | python |
| `pool_selection_bias` | 90 Notebook — validation evidence | `compute_pool_selection_bias` | python |
| `safety_lift` | 90 Notebook — validation evidence | `compute_safety_lift` | python |
| `scored_m4` | 90 Notebook — validation evidence | `score_psplit_validation_m4` | prediction_scoring |
| `scored_m5` | 90 Notebook — validation evidence | `score_psplit_validation_m5` | prediction_scoring |
| `scored_m6` | 90 Notebook — validation evidence | `score_psplit_validation_m6` | prediction_scoring |
| `scored_m8` | 90 Notebook — validation evidence | `score_psplit_validation_m8` | prediction_scoring |
| `target_reachability` | 90 Notebook — validation evidence | `compute_target_reachability` | python |
| `tractability_lift` | 90 Notebook — validation evidence | `compute_tractability_lift` | python |
| `validation_auc_by_disease_2` | 90 Notebook — validation evidence | `compute_validation_auc_by_disease_2` | python |

## 00 Imported from DEMO_KG_LS (synced)  (10 datasets)

| dataset | consumed by | producing recipe | downstream | flag |
|---|---|---|---|---|
| `drug_disease_edges` | nb6 | `compute_DEMO_KG_drug_disease_edges_copy` | 15 |  |
| `drug_protein_edges` | nb6 | `compute_DEMO_KG_drug_protein_edges_copy` | 15 |  |
| `graph_edges` | nb5 | `compute_DEMO_KG_graph_edges_copy` | 9 |  |
| `graph_nodes` | nb5/nb6 | `compute_DEMO_KG_graph_nodes_copy` | 33 |  |
| `raw_disease_disease` | nb5 | `compute_DEMO_KG_raw_disease_disease_copy` | 3 |  |
| `raw_ot_known_drug` | nb4 | `compute_raw_ot_known_drug` | 2 |  |

**Read by no notebook and no webapp (4):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `edge_metadata` | `compute_DEMO_KG_edge_metadata_copy` | sync | 4 |  |
| `gene_names` | `compute_DEMO_KG_gene_names_copy` | sync | 5 |  |
| `mondo_references` | `compute_DEMO_KG_mondo_references_copy` | sync | 3 |  |
| `raw_go_hierarchy` | `compute_DEMO_KG_raw_go_hierarchy_copy` | sync | 2 |  |

## 10 Features - graph traversal (Cypher)  (10 datasets)

_Nothing in this zone is read by a notebook or the webapp._

**Read by no notebook and no webapp (10):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `enriched_degree_controls_1` | `compute_enriched_degree_controls_1` | CustomCode_visual-graph-execute-cypher | 1 |  |
| `enriched_disease_context_1` | `compute_enriched_disease_context_1` | CustomCode_visual-graph-execute-cypher | 2 |  |
| `enriched_dwpc_GCD` | `compute_enriched_dwpc_GCD` | CustomCode_visual-graph-execute-cypher | 4 |  |
| `enriched_dwpc_GGD` | `compute_enriched_dwpc_GGD` | CustomCode_visual-graph-execute-cypher | 4 |  |
| `enriched_dwpc_GPGD` | `compute_enriched_dwpc_GPGD` | CustomCode_visual-graph-execute-cypher | 3 |  |
| `enriched_guilt_by_association_1` | `compute_enriched_guilt_by_association_1` | CustomCode_visual-graph-execute-cypher | 2 |  |
| `enriched_has_inflammatory_go_annotation_1` | `compute_enriched_inflammatory_go` | CustomCode_visual-graph-execute-cypher | 1 |  |
| `enriched_module_size_1` | `compute_enriched_module_size_1` | CustomCode_visual-graph-execute-cypher | 2 |  |
| `enriched_node_centrality_1` | `compute_enriched_node_centrality_1` | CustomCode_visual-graph-graph-features | 1 |  |
| `enriched_shared_pathway_count_1` | `compute_enriched_shared_pathway_count_1` | CustomCode_visual-graph-execute-cypher | 2 |  |

## 11 Features - matrix (Python)  (6 datasets)

_Nothing in this zone is read by a notebook or the webapp._

**Read by no notebook and no webapp (6):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `enriched_dwpc_GBGD` | `compute_dwpc_go_metapaths` | python | 2 |  |
| `enriched_dwpc_GFGD` | `compute_dwpc_go_metapaths` | python | 2 |  |
| `enriched_ppi_cn_zscore` | `compute_ppi_cn_zscore` | python | 2 |  |
| `enriched_ppi_evidence_depth` | `compute_ppi_evidence_depth` | python | 1 |  |
| `enriched_prox_closest` | `compute_enriched_prox_closest` | python | 2 |  |
| `enriched_rwr_score_1` | `compute_enriched_rwr_score_1` | python | 2 |  |

## 12 Features - assembly  (2 datasets)

_Nothing in this zone is read by a notebook or the webapp._

**Read by no notebook and no webapp (2):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `enriched_graph_features_1` | `compute_enriched_graph_features_1` | join | 2 |  |
| `enriched_pair_features_index_1` | `compute_enriched_pair_features_index_1` | vstack | 1 |  |

## 20 Annotations & split key  (17 datasets)

| dataset | consumed by | producing recipe | downstream | flag |
|---|---|---|---|---|
| `enriched_gene_druggability_v2` | nb6 | `compute_gene_druggability_v2` | 6 |  |
| `enriched_gene_safety_v2` | nb6 | `compute_gene_safety_v2` | 3 |  |

**Read by no notebook and no webapp (15):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `disease_family_id` | `compute_disease_family_id` | python | 3 |  |
| `drug_best` | `compute_drug_best` | topn | 1 |  |
| `drug_classified` | `compute_drug_classified` | shaker | 1 |  |
| `drug_joined` | `compute_drug_joined` | join | 1 |  |
| `enriched_gene_druggability` | `compute_gene_druggability` | python | 0 | **ORPHAN** |
| `enriched_gene_localization` | `compute_gene_localization` | python | 2 |  |
| `enriched_gene_safety` | `compute_gene_safety` | python | 0 | **ORPHAN** |
| `gene_crosswalk` | `compute_gene_crosswalk` | join | 2 |  |
| `gene_safety_best` | `compute_gene_safety_best` | topn | 1 |  |
| `gene_safety_joined` | `compute_gene_safety_join` | join | 1 |  |
| `graph_genes` | `compute_graph_genes` | shaker | 1 |  |
| `hetionet_disease_slim` | `extract_hetionet_disease_slim` | python | 2 |  |
| `ot_drug_mapped` | `compute_ot_drug_mapped` | join | 1 |  |
| `raw_ot_druggability` | `compute_DEMO_KG_raw_ot_druggability_copy` | sync | 3 |  |
| `raw_ot_safety` | `compute_DEMO_KG_raw_ot_safety_copy` | sync | 3 |  |

## 30 Split & modelling table  (5 datasets)

| dataset | consumed by | producing recipe | downstream | flag |
|---|---|---|---|---|
| `enriched_graph_features_candidate_psplit` | nb2/nb5 | `filter_has_path_evidence` | 2 |  |
| `psplit_train_set` | nb1 | `split_by_disease_key` | 10 |  |

**Read by no notebook and no webapp (3):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `enriched_graph_features_1_family` | `join_disease_family_id` | join | 1 |  |
| `psplit_test_set` | `split_by_disease_key` | split | 8 |  |
| `psplit_validation_set` | `split_by_disease_key` | split | 10 |  |

## 31 Train & score  (2 datasets)

| dataset | consumed by | producing recipe | downstream | flag |
|---|---|---|---|---|
| `scored_champion` | nb1/nb2/nb3/nb3b/nb4/nb6 | `sync_scored_champion` | 16 |  |

**Read by no notebook and no webapp (1):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `scored_m7` | `score_psplit_validation_m7` | prediction_scoring | 1 |  |

## 90 Notebook — validation evidence  (32 datasets)

| dataset | consumed by | producing recipe | downstream | flag |
|---|---|---|---|---|
| `breast_panel_metrics` | nb4 | `compute_breast_panel` | 0 | KEEP |
| `breast_panel_overlap` | nb4/nb6 | `compute_breast_panel` | 1 | KEEP |
| `family_auc_by_family` | nb3 | `compute_family_auc` | 1 | KEEP |
| `nb6_assertion_results` | nb6 | `run_nb6_assertions` | 0 | scaffold |
| `pool_reachability` | nb2 | `compute_pool_reachability` | 0 | KEEP |
| `tractability_axis` | nb4/nb6 | `compute_tractability_axis` | 1 | KEEP |

**Read by no notebook and no webapp (26):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `breast_shortlist` | `compute_breast_shortlist` | python | 0 | **ORPHAN** |
| `drug_target_benchmark_staged` | `compute_drug_target_benchmark_staged` | python | 0 | **ORPHAN** |
| `family_auc_grouped` | `group_family_auc` | grouping | 1 |  |
| `family_gene_agg` | `group_family_gene` | grouping | 1 |  |
| `family_top_genes` | `topn_family_genes` | topn | 1 |  |
| `family_top_genes_named` | `join_family_gene_name` | join | 0 | **ORPHAN** |
| `family_validation_ranked` | `window_family_rank` | window | 1 |  |
| `family_validation_scored` | `compute_family_validation_scored` | sync | 2 |  |
| `lung_granularity_check` | `compute_lung_granularity_check` | python | 1 | DELETE |
| `maturity_confound` | `compute_maturity_confound` | python | 0 | **ORPHAN** |
| `model_comparison` | `compute_model_comparison` | python | 0 | **ORPHAN** |
| `nb1_verify` | `verify_nb1_on_champion` | python | 0 | scaffold |
| `nb3_verify` | `verify_nb3_on_champion` | python | 0 | scaffold |
| `pool_selection_bias` | `compute_pool_selection_bias` | python | 0 | DELETE |
| `pool_unreachable_targets` | `compute_pool_reachability` | python | 0 | KEEP |
| `safety_lift` | `compute_safety_lift` | python | 0 | DELETE |
| `scored_m1` | `score_psplit_validation_set` | prediction_scoring | 1 |  |
| `scored_m2` | `score_psplit_validation_set_1` | prediction_scoring | 1 |  |
| `scored_m3` | `score_psplit_validation_set_2` | prediction_scoring | 1 |  |
| `scored_m4` | `score_psplit_validation_m4` | prediction_scoring | 0 | **ORPHAN** |
| `scored_m5` | `score_psplit_validation_m5` | prediction_scoring | 0 | **ORPHAN** |
| `scored_m6` | `score_psplit_validation_m6` | prediction_scoring | 0 | **ORPHAN** |
| `scored_m8` | `score_psplit_validation_m8` | prediction_scoring | 0 | **ORPHAN** |
| `target_reachability` | `compute_target_reachability` | python | 0 | **ORPHAN** |
| `tractability_lift` | `compute_tractability_lift` | python | 0 | DELETE |
| `validation_auc_by_disease_2` | `compute_validation_auc_by_disease_2` | python | 0 | **ORPHAN** |

## A1 Evidence base (serving)  (5 datasets)

_Nothing in this zone is read by a notebook or the webapp._

**Read by no notebook and no webapp (5):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `graph_label_evidence` | `compute_graph_label_evidence` | grouping | 0 | serving (webapp TBD) |
| `graph_node_source_counts` | `compute_graph_node_source_counts` | grouping | 0 | serving (webapp TBD) |
| `graph_node_type_counts` | `compute_graph_node_type_counts` | grouping | 0 | serving (webapp TBD) |
| `graph_ppi_provenance` | `compute_graph_ppi_provenance` | grouping | 0 | serving (webapp TBD) |
| `graph_relation_counts` | `compute_graph_relation_counts` | grouping | 0 | serving (webapp TBD) |

## A2 Calibration (serving)  (13 datasets)

| dataset | consumed by | producing recipe | downstream | flag |
|---|---|---|---|---|
| `drug_target_benchmark` | nb3/nb6 | `compute_drug_target_benchmark` | 3 | serving (webapp TBD) |
| `novel_discovery_eval` | **webapp**, nb4/nb6 | `compute_novel_discovery_eval` | 3 | serving (webapp TBD) |
| `persona_candidates` | **webapp**, nb4 | `compute_persona_candidates` | 2 | serving (webapp TBD) |
| `split_audit_2` | nb2 | `compute_split_audit_2` | 0 | serving (webapp TBD) |
| `validation_auc_by_disease` | nb3/nb5/nb6 | `compute_validation_auc_by_disease` | 4 | serving (webapp TBD) |

**Read by no notebook and no webapp (8):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `disease_eligibility` | `compute_disease_eligibility` | grouping | 0 | serving (webapp TBD) |
| `persona_enrichment` | `compute_persona_enrichment` | shaker | 0 | serving (webapp TBD) |
| `shap_driver_frequency` | `compute_shap_driver_frequency` | grouping | 0 | serving (webapp TBD) |
| `shap_drivers_long` | `compute_shap_drivers_long` | shaker | 1 | serving (webapp TBD) |
| `validation_auc_ci` | `compute_validation_auc_ci` | shaker | 1 | serving (webapp TBD) |
| `validation_set_scored` | `compute_validation_set_scored` | sync | 1 | serving (webapp TBD) |
| `validation_set_scored_grouped` | `compute_validation_set_scored_grouped` | grouping | 1 | serving (webapp TBD) |
| `validation_set_scored_windows` | `compute_validation_set_scored_windows` | window | 1 | serving (webapp TBD) |

## A3 Therapeutic area (serving)  (9 datasets)

_Nothing in this zone is read by a notebook or the webapp._

**Read by no notebook and no webapp (9):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `disease_hierarchy_annotation` | `compute_disease_hierarchy_annotation` | python | 1 | serving (webapp TBD) |
| `family_panel` | `compute_family_panel` | join | 0 | serving (webapp TBD) |
| `pairwise_overlap` | `compute_pairwise_overlap` | grouping | 0 | serving (webapp TBD) |
| `pairwise_pairs` | `compute_pairwise_pairs` | join | 1 | serving (webapp TBD) |
| `top50_membership` | `compute_top50_membership` | shaker | 4 | serving (webapp TBD) |
| `top50_membership_b` | `copy_top50_b` | sync | 1 | serving (webapp TBD) |
| `top50_pairs` | `compute_top50_pairs` | join | 0 | serving (webapp TBD) |
| `top50_slim_a` | `compute_top50_slim_a` | shaker | 1 | serving (webapp TBD) |
| `top50_slim_b` | `compute_top50_slim_b` | shaker | 1 | serving (webapp TBD) |

## A4 Shortlist (serving)  (13 datasets)

| dataset | consumed by | producing recipe | downstream | flag |
|---|---|---|---|---|
| `dashboard_candidates` | **webapp**, nb6 | `finalize_dashboard_candidates` | 3 | serving (webapp TBD) |
| `filter_three_axes` | nb4 | `compute_filter_three_axes` | 0 | serving (webapp TBD) |
| `known_drug_truth` | nb2/nb4 | `compute_known_drug_truth` | 3 | serving (webapp TBD) |

**Read by no notebook and no webapp (10):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `candidates_annotated` | `join_dashboard_annotations` | join | 1 | serving (webapp TBD) |
| `dashboard_persona_trust` | `join_trust_for_personas` | join | 0 | serving (webapp TBD) |
| `disease_pool_sizes` | `count_candidates_per_disease` | grouping | 2 | serving (webapp TBD) |
| `drug_evidence_pairs` | `compute_drug_evidence_pairs` | python | 1 | serving (webapp TBD) |
| `persona2_scored` | `score_persona_candidates` | prediction_scoring | 1 | serving (webapp TBD) |
| `persona2_scored_shap` | `compute_top_shap_drivers_1` | python | 1 | serving (webapp TBD) |
| `target_candidates_2` | `join_disease_name` | join | 4 | serving (webapp TBD) |
| `top_annotated` | `decorate_target_candidates` | join | 1 | serving (webapp TBD) |
| `top_candidates` | `rank_per_disease` | window | 1 | serving (webapp TBD) |
| `validation_set_personas_2` | `filter_persona_diseases` | sampling | 1 | serving (webapp TBD) |

## Default  (1 datasets)

_Nothing in this zone is read by a notebook or the webapp._

**Read by no notebook and no webapp (1):**

| dataset | producing recipe | type | downstream | flag |
|---|---|---|---|---|
| `llm_hx` | `—` | — | 0 | **ORPHAN** |
