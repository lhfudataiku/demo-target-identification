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

Live DSS: **83 datasets across 20 zones**, cross-referenced against the recipe graph (81 recipes), `notebooks/*.py` and `webapp/backend/**/*.py`.

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

- datasets: **83**
- endpoints (read by a webapp route or a notebook): **34**
- flow intermediates (consumed by a recipe, no direct reader): **48**
- genuine orphans: **1** — `llm_hx`

> Every orphan here is a deliberate decision, not a finding. See
> `.index/_dead.json` `keep_do_not_prune` for why each one survives.

### Shared-recipe caution

A dataset may go while its producing recipe must not, when the recipe has a second output
that something reads. Deleting the recipe to remove the unread output would take the read
one with it.

**No recipe currently has this shape.** Every multi-output recipe in the flow has all
of its outputs either read or consumed, so no recipe is load-bearing for a dataset that
looks disposable.

## 00 Import · genes & interactome  (2 datasets, 2 recipes)

Foreign references in this zone (2), each feeding exactly one Sync or Merge recipe: `DEMO_KG_LS.gene_names`, `DEMO_KG_LS.hgnc_identity`

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `gene_names` | — | `compute_DEMO_KG_gene_names_copy` | 1 | intermediate |
| `hgnc_identity` | — | `compute_DEMO_KG_hgnc_identity_copy` | 1 | intermediate |

## 01 Import · diseases & phenotypes  (2 datasets, 2 recipes)

Foreign references in this zone (2), each feeding exactly one Sync or Merge recipe: `DEMO_KG_LS.mondo_references`, `DEMO_KG_LS.raw_disease_disease`

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `mondo_references` | — | `compute_DEMO_KG_mondo_references_copy` | 1 | intermediate |
| `raw_disease_disease` | nb5 | `compute_DEMO_KG_raw_disease_disease_copy` | 1 | notebook |

## 02 Import · drugs & gene-disease  (5 datasets, 5 recipes)

Foreign references in this zone (5), each feeding exactly one Sync or Merge recipe: `DEMO_KG_LS.drug_disease_edges`, `DEMO_KG_LS.drug_protein_edges`, `DEMO_KG_LS.raw_ot_druggability`, `DEMO_KG_LS.raw_ot_known_drug`, `DEMO_KG_LS.raw_ot_safety`

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `drug_disease_edges` | nb6 | `compute_DEMO_KG_drug_disease_edges_copy` | 3 | notebook |
| `drug_protein_edges` | nb6 | `compute_DEMO_KG_drug_protein_edges_copy` | 3 | notebook |
| `raw_ot_druggability` | — | `compute_DEMO_KG_raw_ot_druggability_copy` | 1 | intermediate |
| `raw_ot_known_drug` | nb4 | `compute_raw_ot_known_drug` | 0 | notebook |
| `raw_ot_safety` | — | `compute_DEMO_KG_raw_ot_safety_copy` | 1 | intermediate |

## 03 Import · function & pathways  (1 datasets, 1 recipes)

Foreign references in this zone (1), each feeding exactly one Sync or Merge recipe: `DEMO_KG_LS.raw_go_hierarchy`

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `raw_go_hierarchy` | — | `compute_DEMO_KG_raw_go_hierarchy_copy` | 1 | intermediate |

## 04 Graph backbone (imported)  (3 datasets, 4 recipes)

Foreign references in this zone (3), each feeding exactly one Sync or Merge recipe: `DEMO_KG_LS.edge_metadata`, `DEMO_KG_LS.graph_edges`, `DEMO_KG_LS.graph_nodes`

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `edge_metadata` | — | `compute_DEMO_KG_edge_metadata_copy` | 3 | intermediate |
| `graph_edges` | nb5 | `compute_DEMO_KG_graph_edges_copy` | 7 | notebook |
| `graph_nodes` | nb5, nb6 | `compute_DEMO_KG_graph_nodes_copy` | 17 | notebook |

## 10 Features - graph traversal (Cypher)  (10 datasets, 10 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `enriched_degree_controls_1` | — | `compute_enriched_degree_controls_1` | 1 | intermediate |
| `enriched_disease_context_1` | — | `compute_enriched_disease_context_1` | 2 | intermediate |
| `enriched_dwpc_GCD` | nb2, **webapp:routes/calibration** | `compute_enriched_dwpc_GCD` | 2 | webapp |
| `enriched_dwpc_GGD` | nb2, **webapp:routes/calibration** | `compute_enriched_dwpc_GGD` | 2 | webapp |
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

## 20 Gene annotation  (4 datasets, 4 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `enriched_gene_localization` | — | `compute_gene_localization` | 1 | intermediate |
| `enriched_gene_safety_v2` | nb6 | `compute_enriched_gene_safety_v2` | 1 | notebook |
| `gene_crosswalk` | — | `compute_gene_crosswalk` | 3 | intermediate |
| `gene_safety_joined` | — | `compute_gene_safety_join` | 1 | intermediate |

## 21 Druggability · drug evidence  (5 datasets, 5 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `drug_classified` | — | `compute_drug_classified` | 1 | intermediate |
| `drug_evidence_pairs` | — | `compute_drug_evidence_pairs` | 1 | intermediate |
| `drug_joined` | — | `compute_drug_joined` | 1 | intermediate |
| `enriched_gene_druggability_v2` | nb6 | `compute_enriched_gene_druggability_v2` | 1 | notebook |
| `ot_drug_mapped` | — | `compute_ot_drug_mapped` | 1 | intermediate |

## 22 Disease family · split key  (2 datasets, 2 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `disease_family_id` | — | `compute_disease_family_id` | 2 | intermediate |
| `hetionet_disease_slim` | — | `extract_hetionet_disease_slim` | 1 | intermediate |

## 30 Split & modelling table  (5 datasets, 3 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `enriched_graph_features_1_family` | — | `join_disease_family_id` | 1 | intermediate |
| `enriched_graph_features_candidate_psplit` | nb2, nb5 | `filter_has_path_evidence` | 1 | notebook |
| `psplit_test_set` | — | `split_by_disease_key` | 1 | intermediate |
| `psplit_train_set` | nb1 | `split_by_disease_key` | 2 | notebook |
| `psplit_validation_set` | — | `split_by_disease_key` | 3 | intermediate |

## 31 Train & score  (2 datasets, 3 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `scored_champion` | nb1, nb2, nb3, nb3b, nb4, nb6 | `sync_scored_champion` | 5 | notebook |
| `scored_m7` | — | `score_psplit_validation_m7` | 1 | intermediate |

## 40 Candidate ranking (shared by acts)  (3 datasets, 3 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `demo_panel_config` | **webapp:routes/families** | `compute_demo_panel_config` | 5 | webapp |
| `family_panel` | — | `compute_family_panel` | 2 | intermediate |
| `validation_set_personas_2` | — | `filter_persona_diseases` | 1 | intermediate |

## Agent  (1 datasets, 0 recipes)

Foreign references in this zone (1), each feeding exactly one Sync or Merge recipe: `DEMO_KG_LS.UBUlwwxT`

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `llm_hx` | — | — *(source)* | 0 | **ORPHAN** |

## S1 Shortlist  (9 datasets, 9 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `candidate_identity` | **webapp:routes/candidates**, **webapp:services/pair_sources** | `join_candidate_identity` | 0 | webapp |
| `candidate_shap_top5` | **webapp:routes/candidates** | `compute_shap_top5` | 0 | webapp |
| `candidates_annotated` | — | `compute_candidates_annotated` | 1 | intermediate |
| `dashboard_candidates` | **webapp:config** | `finalize_dashboard_candidates` | 0 | webapp |
| `disease_pool_sizes` | — | `compute_disease_pool_sizes` | 1 | intermediate |
| `drug_evidence_records` | **webapp:routes/candidates** | `join_drug_evidence_records` | 0 | webapp |
| `drug_protein_actions` | — | `group_drug_protein_actions` | 1 | intermediate |
| `persona2_scored_shap5` | — | `score_persona_candidates_shap5` | 3 | intermediate |
| `top_candidates` | — | `compute_top_candidates` | 1 | intermediate |

## S2 Evidence · graph  (5 datasets, 5 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `graph_label_evidence` | **webapp:routes/evidence** | `compute_graph_label_evidence` | 0 | webapp |
| `graph_node_source_counts` | **webapp:routes/evidence** | `compute_graph_node_source_counts` | 0 | webapp |
| `graph_node_type_counts` | **webapp:routes/evidence** | `compute_graph_node_type_counts` | 1 | webapp |
| `graph_ppi_provenance` | **webapp:routes/evidence** | `compute_graph_ppi_provenance` | 0 | webapp |
| `graph_relation_counts` | **webapp:routes/evidence** | `compute_graph_relation_counts` | 0 | webapp |

## S3 Evidence · reconstruction  (9 datasets, 9 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `drug_target_benchmark` | — | `compute_drug_target_benchmark` | 1 | intermediate |
| `family_auc_by_family` | **webapp:config** | `compute_family_auc` | 0 | webapp |
| `family_auc_grouped` | — | `group_family_auc` | 1 | intermediate |
| `family_validation_ranked` | — | `window_family_rank` | 1 | intermediate |
| `orthogonality_scatter` | **webapp:routes/calibration** | `join_orthogonality` | 0 | webapp |
| `validation_auc_by_disease` | **webapp:config** | `compute_validation_auc_by_disease` | 2 | webapp |
| `validation_set_scored_grouped` | — | `compute_validation_set_scored_grouped` | 1 | intermediate |
| `validation_set_scored_named` | — | `compute_validation_set_scored_named` | 1 | intermediate |
| `validation_set_scored_windows` | — | `compute_validation_set_scored_windows` | 1 | intermediate |

## S4 Evidence · family panels  (4 datasets, 4 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `family_panel_metrics` | **webapp:routes/families** | `compute_family_panel_metrics` | 0 | webapp |
| `family_panel_overlap` | **webapp:routes/families** | `compute_family_panel_overlap` | 0 | webapp |
| `family_panel_programme` | **webapp:routes/families** | `compute_family_panel_programme` | 0 | webapp |
| `family_panel_top50` | **webapp:routes/families** | `compute_family_panel_top50` | 2 | webapp |

## S5 Evidence · audits  (3 datasets, 3 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `disease_eligibility` | **webapp:routes/calibration** | `compute_disease_eligibility` | 0 | webapp |
| `hub_bias_meter` | **webapp:routes/calibration** | `compute_hub_bias_meter` | 0 | webapp |
| `split_audit_2` | **webapp:routes/calibration** | `compute_split_audit_2` | 0 | webapp |

