# Flow map

> **Lifecycle:** Generated · **Audience:** flow maintainers and reviewers considering pruning
> or changing a data contract · **Authority:** live DSS zones, datasets, producers and
> consumers · **Update when:** the DSS flow or its generation inputs change · **Generated
> dependencies:** live DSS (`dku flow zones`), `.index/dss_snapshot.json`, `notebooks/*.py`,
> `webapp/backend/**/*.py` · **Excludes:** hand-authored rationale, design policy and build
> chronology.
>
> **Never edit by hand. Regenerate:**
> ```sh
> python3 tools/build_recipe_index.py --refresh   # only if DSS changed in the UI
> python3 tools/build_flow_map.py
> ```

Live DSS: **92 datasets across 14 zones**, cross-referenced against the recipe graph (90 recipes), `notebooks/*.py` and `webapp/backend/**/*.py`.

A dataset counts as **read** only when its name appears *quoted* in reader code. A bare
mention is prose: `calibration.py` names the three DWPC feature datasets in a display
table, which is not a read.

| flag | meaning |
|---|---|
| webapp | a webapp route reads it — serving the live demo |
| notebook | a notebook reads it — it guards a documented number |
| intermediate | no reader, but a recipe consumes it — load-bearing inside the flow |
| **ORPHAN** | nothing reads it and no recipe consumes it — a pruning candidate |

The retired `serving (webapp TBD)` flag is gone: the consumer it deferred to now exists,
so zones A1-A4 are read by named routes rather than by an unbuilt UI.

## Summary

- datasets: **92**
- endpoints (read by a webapp route or a notebook): **43**
- flow intermediates (consumed by a recipe, no direct reader): **48**
- genuine orphans: **1** — `llm_hx`

> Every orphan here is a deliberate decision, not a finding. See
> `.index/_dead.json` `keep_do_not_prune` for why each one survives.

### Shared-recipe caution

A dataset may go while its producing recipe must not, when the recipe has a second output
that something reads. `pool_unreachable_targets` is unread, but `compute_pool_reachability`
also produces `pool_reachability`, which nb2 reads. The dataset may go; **the recipe must not**.

## 00 Imported from DEMO_KG_LS (synced)  (10 datasets, 13 recipes)

Foreign references in this zone (12), each feeding exactly one Sync or Merge recipe: `DEMO_KG_LS.drug_disease_edges`, `DEMO_KG_LS.drug_protein_edges`, `DEMO_KG_LS.edge_metadata`, `DEMO_KG_LS.gene_names`, `DEMO_KG_LS.graph_edges`, `DEMO_KG_LS.graph_nodes`, `DEMO_KG_LS.mondo_references`, `DEMO_KG_LS.raw_disease_disease`, `DEMO_KG_LS.raw_go_hierarchy`, `DEMO_KG_LS.raw_ot_druggability`, `DEMO_KG_LS.raw_ot_known_drug`, `DEMO_KG_LS.raw_ot_safety`

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `drug_disease_edges` | nb6 | `compute_DEMO_KG_drug_disease_edges_copy` | 7 | notebook |
| `drug_protein_edges` | nb6 | `compute_DEMO_KG_drug_protein_edges_copy` | 8 | notebook |
| `edge_metadata` | — | `compute_DEMO_KG_edge_metadata_copy` | 3 | intermediate |
| `gene_names` | — | `compute_DEMO_KG_gene_names_copy` | 2 | intermediate |
| `graph_edges` | nb5 | `compute_DEMO_KG_graph_edges_copy` | 8 | notebook |
| `graph_nodes` | nb5, nb6 | `compute_DEMO_KG_graph_nodes_copy` | 22 | notebook |
| `mondo_references` | — | `compute_DEMO_KG_mondo_references_copy` | 1 | intermediate |
| `raw_disease_disease` | nb5 | `compute_DEMO_KG_raw_disease_disease_copy` | 1 | notebook |
| `raw_go_hierarchy` | — | `compute_DEMO_KG_raw_go_hierarchy_copy` | 1 | intermediate |
| `raw_ot_known_drug` | nb4 | `compute_raw_ot_known_drug` | 1 | notebook |

## 10 Features - graph traversal (Cypher)  (10 datasets, 10 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `enriched_degree_controls_1` | — | `compute_enriched_degree_controls_1` | 1 | intermediate |
| `enriched_disease_context_1` | — | `compute_enriched_disease_context_1` | 2 | intermediate |
| `enriched_dwpc_GCD` | nb2, **webapp:routes/calibration** | `compute_enriched_dwpc_GCD` | 3 | webapp |
| `enriched_dwpc_GGD` | nb2, **webapp:routes/calibration** | `compute_enriched_dwpc_GGD` | 3 | webapp |
| `enriched_dwpc_GPGD` | nb2, **webapp:routes/calibration** | `compute_enriched_dwpc_GPGD` | 2 | webapp |
| `enriched_guilt_by_association_1` | — | `compute_enriched_guilt_by_association_1` | 2 | intermediate |
| `enriched_has_inflammatory_go_annotation_1` | — | `compute_enriched_inflammatory_go` | 1 | intermediate |
| `enriched_module_size_1` | — | `compute_enriched_module_size_1` | 2 | intermediate |
| `enriched_node_centrality_1` | — | `compute_enriched_node_centrality_1` | 1 | intermediate |
| `enriched_shared_pathway_count_1` | — | `compute_enriched_shared_pathway_count_1` | 2 | intermediate |

## 11 Features - matrix (Python)  (6 datasets, 5 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `enriched_dwpc_GBGD` | — | `compute_dwpc_go_metapaths` | 2 | intermediate |
| `enriched_dwpc_GFGD` | — | `compute_dwpc_go_metapaths` | 2 | intermediate |
| `enriched_ppi_cn_zscore` | — | `compute_ppi_cn_zscore` | 2 | intermediate |
| `enriched_ppi_evidence_depth` | — | `compute_ppi_evidence_depth` | 1 | intermediate |
| `enriched_prox_closest` | — | `compute_enriched_prox_closest` | 2 | intermediate |
| `enriched_rwr_score_1` | — | `compute_enriched_rwr_score_1` | 2 | intermediate |

## 12 Features - assembly  (2 datasets, 2 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `enriched_graph_features_1` | — | `compute_enriched_graph_features_1` | 2 | intermediate |
| `enriched_pair_features_index_1` | — | `compute_enriched_pair_features_index_1` | 1 | intermediate |

## 20 Annotations & split key  (13 datasets, 11 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `disease_family_id` | nb6, nb7 | `compute_disease_family_id` | 2 | notebook |
| `drug_classified` | — | `compute_drug_classified` | 1 | intermediate |
| `drug_evidence_pairs` | — | `compute_drug_evidence_pairs` | 1 | intermediate |
| `drug_joined` | — | `compute_drug_joined` | 1 | intermediate |
| `enriched_gene_druggability_v2` | nb6 | `compute_enriched_gene_druggability_v2` | 3 | notebook |
| `enriched_gene_localization` | — | `compute_gene_localization` | 1 | intermediate |
| `enriched_gene_safety_v2` | nb6 | `compute_enriched_gene_safety_v2` | 1 | notebook |
| `gene_crosswalk` | — | `compute_gene_crosswalk` | 3 | intermediate |
| `gene_safety_joined` | — | `compute_gene_safety_join` | 1 | intermediate |
| `hetionet_disease_slim` | — | `extract_hetionet_disease_slim` | 1 | intermediate |
| `ot_drug_mapped` | — | `compute_ot_drug_mapped` | 1 | intermediate |
| `raw_ot_druggability` | — | `compute_DEMO_KG_raw_ot_druggability_copy` | 1 | intermediate |
| `raw_ot_safety` | — | `compute_DEMO_KG_raw_ot_safety_copy` | 1 | intermediate |

## 30 Split & modelling table  (5 datasets, 3 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `enriched_graph_features_1_family` | — | `join_disease_family_id` | 1 | intermediate |
| `enriched_graph_features_candidate_psplit` | nb2, nb5 | `filter_has_path_evidence` | 2 | notebook |
| `psplit_test_set` | — | `split_by_disease_key` | 1 | intermediate |
| `psplit_train_set` | nb1 | `split_by_disease_key` | 2 | notebook |
| `psplit_validation_set` | — | `split_by_disease_key` | 3 | intermediate |

## 31 Train & score  (2 datasets, 3 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `scored_champion` | nb1, nb2, nb3, nb3b, nb4, nb6 | `sync_scored_champion` | 8 | notebook |
| `scored_m7` | — | `score_psplit_validation_m7` | 1 | intermediate |

## 40 Candidate ranking (shared by acts)  (11 datasets, 11 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `candidates_annotated` | — | `join_dashboard_annotations` | 1 | intermediate |
| `dashboard_candidates` | nb6, nb7, **webapp:routes/candidates** | `finalize_dashboard_candidates` | 1 | webapp |
| `disease_pool_sizes` | — | `count_candidates_per_disease` | 1 | intermediate |
| `persona2_scored` | — | `score_persona_candidates` | 1 | intermediate |
| `persona2_scored_shap` | — | `compute_top_shap_drivers_1` | 1 | intermediate |
| `shap_driver_frequency` | **webapp:routes/calibration** | `compute_shap_driver_frequency` | 0 | webapp |
| `shap_drivers_long` | — | `compute_shap_drivers_long` | 1 | intermediate |
| `target_candidates_2` | — | `join_disease_name` | 3 | intermediate |
| `top_annotated` | — | `decorate_target_candidates` | 1 | intermediate |
| `top_candidates` | — | `rank_per_disease` | 1 | intermediate |
| `validation_set_personas_2` | — | `filter_persona_diseases` | 1 | intermediate |

## 90 Notebook — validation evidence  (7 datasets, 7 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `breast_panel_metrics` | nb4 | `compute_breast_panel` | 0 | notebook |
| `family_auc_by_family` | nb3, **webapp:routes/calibration** | `compute_family_auc` | 0 | webapp |
| `family_auc_grouped` | — | `group_family_auc` | 1 | intermediate |
| `family_validation_ranked` | — | `window_family_rank` | 1 | intermediate |
| `family_validation_scored` | — | `compute_family_validation_scored` | 1 | intermediate |
| `pool_reachability` | nb2 | `compute_pool_reachability` | 0 | notebook |
| `tractability_axis` | nb4, nb6 | `compute_tractability_axis` | 0 | notebook |

## A1 Evidence base (serving)  (5 datasets, 5 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `graph_label_evidence` | **webapp:routes/evidence** | `compute_graph_label_evidence` | 0 | webapp |
| `graph_node_source_counts` | **webapp:routes/evidence** | `compute_graph_node_source_counts` | 0 | webapp |
| `graph_node_type_counts` | **webapp:routes/evidence** | `compute_graph_node_type_counts` | 1 | webapp |
| `graph_ppi_provenance` | **webapp:routes/evidence** | `compute_graph_ppi_provenance` | 0 | webapp |
| `graph_relation_counts` | **webapp:routes/evidence** | `compute_graph_relation_counts` | 0 | webapp |

## A2 Calibration (serving)  (12 datasets, 12 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `disease_eligibility` | **webapp:routes/calibration** | `compute_disease_eligibility` | 0 | webapp |
| `drug_target_benchmark` | nb3, nb6 | `compute_drug_target_benchmark` | 2 | notebook |
| `hub_bias_meter` | **webapp:routes/calibration** | `compute_hub_bias_meter` | 0 | webapp |
| `novel_discovery_eval` | nb4, nb6 | `compute_novel_discovery_eval` | 1 | notebook |
| `orthogonality_scatter` | **webapp:routes/calibration** | `join_orthogonality` | 0 | webapp |
| `persona_candidates` | nb4 | `compute_persona_candidates` | 1 | notebook |
| `persona_enrichment` | nb7, **webapp:routes/calibration**, **webapp:routes/families** | `compute_persona_enrichment` | 1 | webapp |
| `split_audit_2` | nb2, **webapp:routes/calibration** | `compute_split_audit_2` | 0 | webapp |
| `validation_auc_by_disease` | nb3, nb5, nb6, **webapp:routes/calibration** | `compute_validation_auc_by_disease` | 3 | webapp |
| `validation_auc_ci` | — | `compute_validation_auc_ci` | 1 | intermediate |
| `validation_set_scored_grouped` | — | `compute_validation_set_scored_grouped` | 1 | intermediate |
| `validation_set_scored_windows` | — | `compute_validation_set_scored_windows` | 1 | intermediate |

## A3 Therapeutic area (serving)  (6 datasets, 6 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `demo_panel_config` | nb7, **webapp:routes/families** | `compute_demo_panel_config` | 5 | webapp |
| `family_panel` | nb7 | `compute_family_panel` | 2 | notebook |
| `family_panel_metrics` | **webapp:routes/families** | `compute_family_panel_metrics` | 0 | webapp |
| `family_panel_overlap` | nb4, nb6, nb7, **webapp:routes/families** | `compute_family_panel_overlap` | 0 | webapp |
| `family_panel_programme` | nb7, **webapp:routes/families** | `compute_family_panel_programme` | 0 | webapp |
| `family_panel_top50` | **webapp:routes/families** | `compute_family_panel_top50` | 2 | webapp |

## A4 Shortlist (serving)  (2 datasets, 2 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `filter_three_axes` | nb4 | `compute_filter_three_axes` | 0 | notebook |
| `known_drug_truth` | nb2, nb4 | `compute_known_drug_truth` | 2 | notebook |

## Default  (1 datasets, 0 recipes)

Foreign references in this zone (1), each feeding exactly one Sync or Merge recipe: `DEMO_KG_LS.UBUlwwxT`

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `llm_hx` | — | — *(source)* | 0 | **ORPHAN** |

