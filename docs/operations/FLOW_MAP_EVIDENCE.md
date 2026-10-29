# Flow map: evidence project (`DEMO_TI_EVIDENCE`)

> **Lifecycle:** Generated · **Audience:** flow maintainers and reviewers considering pruning
> or changing a data contract · **Authority:** live DSS zones, datasets, producers and
> consumers · **Update when:** the DSS flow or its generation inputs change · **Generated
> dependencies:** live DSS (`dku flow zones`), `.index/dss_snapshot_evidence.json`, `notebooks/*.py`,
> `webapp/backend/**/*.py` · **Excludes:** hand-authored rationale, design policy and build
> chronology.
>
> **Never edit by hand. Regenerate:**
> ```sh
> python3 tools/build_recipe_index.py --refresh   # only if DSS changed in the UI
> python3 tools/build_flow_map.py --project DEMO_TI_EVIDENCE
> ```

Project `DEMO_TI_EVIDENCE`. The other Part 2 project is mapped in [`FLOW_MAP.md`](FLOW_MAP.md): the main project, whose zones 00-31 this project reads by qualified name. Those reads appear below as foreign references.

Live DSS: **25 datasets across 5 zones**, cross-referenced against the recipe graph (25 recipes), `notebooks/*.py` and `webapp/backend/**/*.py`.

A dataset counts as **read** only when its name appears *quoted* in reader code. A bare
mention is prose: `calibration.py` names the three DWPC feature datasets in a display
table, which is not a read.

| flag | meaning |
|---|---|
| webapp | a webapp route reads it — serving the live demo |
| notebook | a notebook reads it — it guards a documented number |
| intermediate | no reader, but a recipe consumes it — load-bearing inside the flow |
| **ORPHAN** | nothing reads it and no recipe consumes it — a pruning candidate |

## Summary

- datasets: **25**
- endpoints (read by a webapp route or a notebook): **16**
- flow intermediates (consumed by a recipe, no direct reader): **9**
- genuine orphans: **0**

### Shared-recipe caution

A dataset may go while its producing recipe must not, when the recipe has a second output
that something reads. Deleting the recipe to remove the unread output would take the read
one with it.

**No recipe currently has this shape.** Every multi-output recipe in the flow has all
of its outputs either read or consumed, so no recipe is load-bearing for a dataset that
looks disposable.

## Default  (0 datasets, 0 recipes)

Foreign references in this zone (18), read by name by this project's recipes, with no local copy: `DEMO_TARGET_IDENTIFICATION.disease_family_id`, `DEMO_TARGET_IDENTIFICATION.drug_disease_edges`, `DEMO_TARGET_IDENTIFICATION.drug_evidence_pairs`, `DEMO_TARGET_IDENTIFICATION.drug_protein_edges`, `DEMO_TARGET_IDENTIFICATION.enriched_dwpc_GCD`, `DEMO_TARGET_IDENTIFICATION.enriched_dwpc_GGD`, `DEMO_TARGET_IDENTIFICATION.enriched_gene_druggability_v2`, `DEMO_TARGET_IDENTIFICATION.enriched_gene_safety_v2`, `DEMO_TARGET_IDENTIFICATION.enriched_graph_features_candidate_psplit`, `DEMO_TARGET_IDENTIFICATION.gene_crosswalk`, `DEMO_TARGET_IDENTIFICATION.gene_names`, `DEMO_TARGET_IDENTIFICATION.graph_edges`, `DEMO_TARGET_IDENTIFICATION.graph_nodes`, `DEMO_TARGET_IDENTIFICATION.psplit_test_set`, `DEMO_TARGET_IDENTIFICATION.psplit_train_set`, `DEMO_TARGET_IDENTIFICATION.psplit_validation_set`, `DEMO_TARGET_IDENTIFICATION.raw_ot_known_drug`, `DEMO_TARGET_IDENTIFICATION.scored_champion`

_No datasets in this zone._

## E1 Reconstruction  (12 datasets, 12 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `drug_target_benchmark` | nb3, nb6 | `compute_drug_target_benchmark` | 1 | notebook |
| `family_auc_by_family` | nb3 | `compute_family_auc` | 0 | notebook |
| `family_auc_grouped` | — | `group_family_auc` | 1 | intermediate |
| `family_validation_ranked` | — | `window_family_rank` | 1 | intermediate |
| `novel_discovery_eval` | nb4, nb6 | `compute_novel_discovery_eval` | 1 | notebook |
| `persona_candidates` | nb4 | `compute_persona_candidates` | 1 | notebook |
| `persona_enrichment` | nb7 | `compute_persona_enrichment` | 0 | notebook |
| `split_audit_2` | nb2 | `compute_split_audit_2` | 0 | notebook |
| `validation_auc_by_disease` | nb3, nb5, nb6 | `compute_validation_auc_by_disease` | 2 | notebook |
| `validation_auc_ci` | — | `compute_validation_auc_ci` | 1 | intermediate |
| `validation_set_scored_grouped` | — | `compute_validation_set_scored_grouped` | 1 | intermediate |
| `validation_set_scored_windows` | — | `compute_validation_set_scored_windows` | 1 | intermediate |

## E2 Panels  (5 datasets, 5 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `demo_panel_config` | nb7 | `compute_demo_panel_config` | 4 | notebook |
| `family_panel` | nb7 | `compute_family_panel` | 1 | notebook |
| `family_panel_overlap` | nb4, nb6, nb7 | `compute_family_panel_overlap` | 0 | notebook |
| `family_panel_programme` | nb7 | `compute_family_panel_programme` | 0 | notebook |
| `family_panel_top50` | — | `compute_family_panel_top50` | 2 | intermediate |

## E3 Shortlist evidence  (4 datasets, 4 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `dashboard_candidates` | nb6, nb7 | `compute_dashboard_candidates` | 1 | notebook |
| `shortlist_joined` | — | `compute_shortlist_joined` | 1 | intermediate |
| `shortlist_ranked` | — | `compute_shortlist_ranked` | 1 | intermediate |
| `shortlist_scored` | — | `compute_shortlist_scored` | 1 | intermediate |

## E4 Drug truth and breast panel  (4 datasets, 4 recipes)

| dataset | read by | producing recipe | recipe consumers | flag |
|---|---|---|--:|---|
| `breast_panel_metrics` | nb4 | `compute_breast_panel` | 0 | notebook |
| `filter_three_axes` | nb4 | `compute_filter_three_axes` | 0 | notebook |
| `known_drug_truth` | nb2, nb4 | `compute_known_drug_truth` | 2 | notebook |
| `pool_reachability` | nb2 | `compute_pool_reachability` | 0 | notebook |

