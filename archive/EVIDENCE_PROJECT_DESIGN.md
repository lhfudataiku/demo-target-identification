# Evidence project — design

> **Lifecycle:** Historical · **Audience:** DSS flow maintainers and reviewers of the notebook
> revision · **Authority:** how the supporting evidence project provides every dataset the notebooks
> read, which recipes it moves, copies or adds, what it reads from the main project, and the
> per-script notebook revisions (the evidence half of
> [`FLOW_MIGRATION_WORKPLAN.md`](FLOW_MIGRATION_WORKPLAN.md) M1) · **Update when:** a notebook's reads
> change, or a recipe in §3 changes in either project · **Generated dependencies:** none (measured by
> hand, §8) · **Excludes:** the serving flow and what the webapp reads, in
> [`WEBAPP_DATASET_MAP.md`](../docs/operations/WEBAPP_DATASET_MAP.md); the sequence and acceptance of the work, in the
> workplan's M2.

**Status: EXECUTED — built in M2, 2026-10-28; retired to `archive/` with the workplan on 2026-10-29.**
(Measured 2026-10-28, read-only, for approval as part of M1's table.) The evidence project holds 25
recipes. M6 then retired the main project's copies of the persona chain and `validation_auc_ci`, so
the evidence project owns them now. The current record is generated:
[`FLOW_MAP_EVIDENCE.md`](../docs/operations/FLOW_MAP_EVIDENCE.md) and `.index/recipes_evidence.tsv`.
This file is the dated design.

## 1. Summary

- **The evidence project holds 24–25 recipes and as many datasets:**
  - 4 moved from the main project, one of them with a changed input;
  - 17 copied from it, one of them with a changed input;
  - 3–4 new ones for a slim shortlist.

  It reads 18 objects exposed from the main project's zones 00–31. It needs no scoring run and no
  access to the saved model.
- **The notebooks change in where they read, not in what they assert.**
  - 29 read sites in 8 files point at zones 00–31. These are qualified with the main project's key.
  - The 24 reads of downstream datasets keep their bare names: the workplan's 23 reads from zone 40
    or later, plus `breast_panel_metrics`. They resolve in the evidence project, whose datasets keep
    the main project's names.
  - No assertion's expected value changes.
- **Two facts were verified live on 2026-10-28:**
  - `scored_champion`, restricted to the 12 shortlist diseases, holds exactly the 105,702 served pairs,
    with identical scores (maximum difference 0) and identical `is_target`. The evidence shortlist can
    therefore rank `scored_champion` directly.
  - A local run of the dataiku client reads `DEMO_TARGET_IDENTIFICATION.<dataset>` while another
    project is the default. So the qualified reads work from the repository.
- **The copies carry three things with them:** the `demo_identity` library module, seven project
  variables, and the three identity recipes. The governed-values check has to cover both projects
  (§4).

## 2. Every notebook read and how it is provided

### 2.1 Downstream reads: provided by the evidence project, bare names unchanged

| dataset | read by | zone today | provided by |
|---|---|---|---|
| `known_drug_truth` | `nb2`, `nb4` | A4 | moved |
| `pool_reachability` | `nb2` | A4 | moved |
| `filter_three_axes` | `nb4` | A4 | moved; its input changes from `target_candidates_2` to the evidence `dashboard_candidates` (§3.4) |
| `breast_panel_metrics` | `nb4` | 31 | moved |
| `split_audit_2` | `nb2` | A2 | copied |
| `validation_auc_by_disease` | `nb3`, `nb5`, `nb6` | A2 | copied, with its window and group |
| `family_auc_by_family` | `nb3` | A2 | copied, with its window and group; the window reads `scored_champion` directly |
| `drug_target_benchmark` | `nb3`, `nb6` | A2 | copied |
| `novel_discovery_eval` | `nb4`, `nb6` | A2 | copied |
| `persona_candidates` | `nb4` | A2 | copied |
| `persona_enrichment` | `nb7` | A2 | copied |
| `family_panel` | `nb7` | A3 | copied |
| `demo_panel_config` | `nb7` | A3 | copied (identity recipe) |
| `family_panel_overlap` | `nb4`, `nb6`, `nb7` | A3 | copied, with `family_panel_top50` |
| `family_panel_programme` | `nb7` | A3 | copied |
| `dashboard_candidates` | `nb6`, `nb7` | 40 | new: a slim shortlist ranked with ties (§3.4) |

`nb6` and `nb7` read 8 columns of `dashboard_candidates`: `disease_index`, `gene_index`,
`disease_name`, `gene_name`, `rank_in_disease`, `is_target`, `has_safety_liability` and
`approved_for_disease`.

### 2.2 Upstream reads: read from the main project by qualified name

| object | zone | read sites (script:line) |
|---|---|---|
| `scored_champion` | 31 | nb1:97, nb2:36, nb3:177, nb3b:7, nb4:104, nb6:99, nb6:253, nb6:400, derive:100 |
| `graph_nodes` | 04 | nb5:9, nb5:17, nb6:225, derive:77 |
| `drug_protein_edges` | 02 | nb6:165, nb6:235, derive:88 |
| `drug_disease_edges` | 02 | nb6:166, nb6:234 |
| `enriched_gene_druggability_v2` | 20 | nb6:303, nb6:343, derive:94 |
| `enriched_gene_safety_v2` | 20 | nb6:305 |
| `enriched_graph_features_candidate_psplit` | 30 | nb2:12, nb5:46 |
| `psplit_train_set` | 30 | nb1:18 |
| `raw_ot_known_drug` | 02 | nb4:18 (twice on one line) |
| `graph_edges` | 04 | nb5:22 |
| `raw_disease_disease` | 01 | nb5:41 |
| `enriched_dwpc_GGD`, `enriched_dwpc_GPGD`, `enriched_dwpc_GCD` | 10 | nb2:20, the `keys()` helper, called for all three |

That is 14 objects at 29 read sites. `derive` is `tools/nb_assertions/derive.py`, which `nb4` and
`nb6` import.

## 3. The evidence project's flow

Zone names below are proposals. Each recipe writes one dataset with the same name as its main-project
counterpart. New datasets use managed storage and Parquet, and joins are visual Join recipes.

### 3.1 Inputs: 18 objects exposed from the main project

| zone in the main project | objects |
|---|---|
| 31 | `scored_champion` |
| 30 | `psplit_train_set`, `psplit_validation_set`, `psplit_test_set`, `enriched_graph_features_candidate_psplit` |
| 20 | `disease_family_id`, `gene_crosswalk`, `enriched_gene_druggability_v2`, `enriched_gene_safety_v2`, `drug_evidence_pairs` |
| 10 | `enriched_dwpc_GCD`, `enriched_dwpc_GGD` |
| 04 | `graph_nodes`, `graph_edges` |
| 02 | `drug_disease_edges`, `drug_protein_edges`, `raw_ot_known_drug` |
| 00 | `gene_names` |

- **These are the main project's own copies.** The objects in zones 00–04 are local copies of
  `DEMO_KG_LS` objects, so the evidence project reads only the main project, as D13 requires.
- **Only recipe inputs need exposing.** The notebooks' qualified reads go through the API key, which
  does not depend on exposure.
- **Not exposed:** the saved model `hJLGoYn4`.

### 3.2 Reconstruction: 12 recipes, all copied

| recipe | inputs | output | change from the main copy |
|---|---|---|---|
| `compute_validation_set_scored_windows` (window) | `scored_champion` | `validation_set_scored_windows` | optional: retrieve only the columns the group needs. The main copy keeps all 46 columns (284 MB) |
| `compute_validation_set_scored_grouped` (group) | the above | `validation_set_scored_grouped` | — |
| `compute_validation_auc_by_disease` (prepare) | the above | `validation_auc_by_disease` | — |
| `compute_validation_auc_ci` (prepare) | the above | `validation_auc_ci` | — (reads the variable `trust_n_pos`) |
| `window_family_rank` (window) | **`scored_champion`** | `family_validation_ranked` | reads `scored_champion` instead of the 297 MB sync copy `family_validation_scored`, which is not copied; same optional column trim |
| `group_family_auc` (group) | the above | `family_auc_grouped` | — |
| `compute_family_auc` (prepare) | the above | `family_auc_by_family` | — |
| `compute_split_audit_2` (Python) | the three split tables, `graph_nodes` | `split_audit_2` | — (identity recipe; uses `demo_identity`) |
| `compute_drug_target_benchmark` (Python) | `scored_champion`, `graph_nodes`, drug edges | `drug_target_benchmark` | — |
| `compute_novel_discovery_eval` (Python) | `scored_champion`, `graph_nodes`, drug edges | `novel_discovery_eval` | — |
| `compute_persona_candidates` (Python) | `validation_auc_by_disease`, `drug_target_benchmark`, `novel_discovery_eval`, `graph_nodes` | `persona_candidates` | — (uses `demo_identity`) |
| `compute_persona_enrichment` (prepare) | the above | `persona_enrichment` | — |

### 3.3 Panels: 5 recipes, all copied

| recipe | inputs | output | note |
|---|---|---|---|
| `compute_family_panel` (join) | `validation_auc_ci`, `disease_family_id` | `family_panel` | — |
| `compute_demo_panel_config` (Python) | `family_panel`, `persona_enrichment`, `graph_nodes` | `demo_panel_config` | identity recipe; uses `demo_identity` and the `demo_panel` variable. M0 proposes taking disease names from `graph_nodes` instead of `persona_enrichment`, in both projects |
| `compute_family_panel_top50` (Python) | `demo_panel_config`, `scored_champion`, `gene_crosswalk` | `family_panel_top50` | — |
| `compute_family_panel_overlap` (Python) | `demo_panel_config`, `family_panel_top50` | `family_panel_overlap` | — |
| `compute_family_panel_programme` (Python) | `demo_panel_config`, `family_panel_top50` | `family_panel_programme` | — |

### 3.4 Shortlist evidence: 3–4 new recipes

| recipe | inputs | output |
|---|---|---|
| join, a filter | `scored_champion` ⋈ `demo_panel_config` with `in_act4` (inner, on `disease_index`), keeping `disease_index`, `gene_index`, `proba_1`, `is_target` | `shortlist_scored` |
| window | the above, partitioned by `disease_index` and ordered by `proba_1` descending: *rank*, so tied scores share the lowest rank (1, 2, 2, 4) | `shortlist_ranked` |
| join | the above ⋈ `graph_nodes` (gene name) ⋈ `graph_nodes` (disease name) ⋈ `enriched_gene_druggability_v2` ⋈ `enriched_gene_safety_v2` ⋈ `drug_evidence_pairs`, all left joins | `dashboard_candidates` |
| prepare, if the join cannot fill a missing flag with 0 | the above | `dashboard_candidates` |

The output carries the 8 columns `nb6` and `nb7` read (§2.1). It also carries the columns
`compute_filter_three_axes` reads from `target_candidates_2`: `ot_sm_tractable`, `ot_ab_tractable`,
`druggability_class` and `safety_flag`. That recipe's only change is the name of its input.

Ranking `scored_champion` reproduces today's served list apart from the tie order. 3,611 tied rows
take a different rank, and no untied row moves (workplan §2). No tie group straddles rank 15, 20, 50
or 200, so `nb6`'s top-15 and top-50 checks select the same genes.

### 3.5 Drug truth and the breast panel: 4 recipes, moved

| recipe | inputs | output | change |
|---|---|---|---|
| `compute_known_drug_truth` | `raw_ot_known_drug`, `graph_nodes`, `gene_names`, drug edges | `known_drug_truth` | — |
| `compute_pool_reachability` | `enriched_graph_features_candidate_psplit`, `known_drug_truth`, `graph_nodes`, `graph_edges`, `enriched_gene_druggability_v2`, drug edges, `enriched_dwpc_GCD`, `enriched_dwpc_GGD` | `pool_reachability` | — |
| `compute_filter_three_axes` | **`dashboard_candidates`** (evidence), `known_drug_truth`, `graph_nodes`, drug edges | `filter_three_axes` | input renamed from `target_candidates_2` |
| `compute_breast_panel` | `scored_champion`, `graph_nodes`, drug edges | `breast_panel_metrics` | — (identity recipe; uses `demo_identity`) |

### 3.6 What is not carried over

The traced closure of the notebook reads was 28 recipes. The design drops 7 of them and adds 3–4:

- **Zone 40's chain is dropped.** `filter_persona_diseases`, `score_persona_candidates`,
  `compute_top_shap_drivers_1`, `rank_per_disease`, `decorate_target_candidates` and
  `join_disease_name` are replaced by §3.4.
- **`compute_family_validation_scored`** is dropped: it is a sync that the per-family window does not
  need.
- **Not copied, because no notebook reads them:** `hub_bias_meter`, `orthogonality_scatter` and
  `disease_eligibility`. `nb3b` recomputes the hub-bias meter in its own code.

## 4. What the copies depend on

- **The library module `demo_identity.py`,** from `dss_lib/`. `compute_breast_panel`,
  `compute_demo_panel_config`, `compute_persona_candidates` and `compute_split_audit_2` import it. It
  reads `graph_nodes` and the project variables.
- **Seven project variables:** `demo_panel`, `trust_n_pos`, `panel_n_pos`, `near_dup`,
  `module_size_gate`, `ks` and `topn`, plus their two README entries. `compute_validation_auc_ci`
  also reads `trust_n_pos` directly. If the copies drift from the main project's values, the two
  projects define the panel and the trust floor differently.
- **The three identity recipes** (`DEC-OPS-006`):
  - `compute_breast_panel` exists only in the evidence project;
  - `compute_demo_panel_config` and `compute_split_audit_2` exist in both.

  `tools/check_governed_values.py` should check both projects' copies against the one `dss_recipes/`
  mirror, and both projects' variables against each other.
- **Python copies read their upstream inputs by qualified name** (found 2026-10-28, when the build
  was prepared). Inside a recipe, the dataiku client resolves `dataiku.Dataset(name)` only against
  the declared inputs, and a foreign input is declared as `DEMO_TARGET_IDENTIFICATION.<name>`.
  - `tools/build_evidence_flow.py` qualifies each copy's own upstream inputs in its code.
  - The library names `DEMO_TARGET_IDENTIFICATION.graph_nodes`, which resolves in both projects.
- **Recipe names repeat across the two projects.** `.index/recipes.tsv` and
  `tools/build_recipe_index.py` key on the recipe name alone. `tools/build_flow_map.py` matches a
  notebook read as `"<dataset>"`, so a qualified read `"DEMO_TARGET_IDENTIFICATION.<dataset>"` no
  longer matches. Both tools learn the second project in M6. Until then, the main project's map shows
  no notebook reader on zones 00–31.

## 5. Notebook revisions

| script | upstream reads to qualify | downstream reads (unchanged) | other changes |
|---|--:|--:|---|
| `nb1_features_and_config.py` | 2 | 0 | — |
| `nb2_splitting_and_pool.py` | 2 sites, plus the `keys()` helper (3 datasets) | 3 | — |
| `nb3_validation_and_plots.py` | 1 | 3 | — |
| `nb3b_hub_bias_meter.py` | 1 | 0 | — |
| `nb4_results_three_axes.py` | 2 | 6 | — |
| `nb5_data_exploration.py` | 5 | 1 | — |
| `nb6_interrogation_and_close.py` | 11 | 5 | optional: the lung-family recompute (line 410) numbers rows 1..n. It only prints and asserts nothing, so aligning it with ranking with ties changes no check |
| `nb7_panel_selection.py` | 0 | 6 | — |
| `tools/nb_assertions/derive.py` | 4 | 0 | — |

- **The form.** Write each qualified name as a literal (`"DEMO_TARGET_IDENTIFICATION.scored_champion"`),
  not as a prefix built at run time. A literal stays greppable, and the flow-map tool can learn the
  prefix.
- **What does not change.** No `check(...)` line changes. `.index/assertions.tsv`, which is parsed
  from those lines, keeps the same expected values.
- **Alternatives,** both of which avoid the 29 edits:
  - sync copies of the 14 objects into the evidence project, at about 1.15 GB for the five largest;
  - a name map in the run wrapper, which hides where a read goes.

  The workplan's M0 recommends the qualified literals.

## 6. Running the notebooks locally

- **A wrapper:** `tools/run_notebooks.py`, built 2026-10-28, which ran the baseline (workplan M2).
  It skips `nb5`, which asserts nothing. It:
  - takes credentials the way `webapp/backend/dss_client.py` does (`DKU_URL` and `DKU_API_KEY`, as
    `dku auth export-env` emits them);
  - calls `dataiku.set_remote_dss` and `dataiku.set_default_project_key(<evidence key>)`;
  - puts `tools/` on `sys.path` for `nb_assertions`;
  - calls `runner.run(name)` for each script, in `notebooks/README.md`'s order.

  A `--project` flag lets the same wrapper take M2's baseline against the main project.
- **An environment:** Python 3.13, to match the DSS environment the scripts ran on, with the dataiku
  client, `pandas`, `numpy`, `matplotlib`, `seaborn` and `IPython`. The webapp's environment has the
  client but lacks the last three.
- **Cost:** the scripts stream `scored_champion` (3,958,921 rows) several times over the API. The
  2026-10-28 check streamed four of its columns once without trouble.

## 7. Open items for approval

The workplan's M0 (drafted 2026-10-28) proposes an answer to each item below.

- **The evidence project's key and name** (D13). Every qualified read and the wrapper name the main
  project; only the wrapper names the evidence project.
- **Whether the evidence shortlist keeps the name `dashboard_candidates`.** Keeping it means `nb6` and
  `nb7` change nothing. Renaming it (for example `evidence_shortlist`) avoids two projects having a
  dataset of that name, at the cost of two notebook edits and one input change.
- **The optional column trims** on the two windows. Accept them only if the grouped outputs match the
  main project's exactly.
- **Aligning `nb6`'s lung-family ranking with ranking with ties.**
- **Keeping the variables in step:** a one-off copy plus the governed-values check, or a script that
  sets both projects from one source.
- **The build-governance target** for `breast_panel_metrics` in the evidence project.

## 8. Method

Read-only, 2026-10-27/28:

- **Notebook reads:** parsed from `notebooks/*.py` and `tools/nb_assertions/derive.py` with Python's
  `ast`. The one dynamic read (`nb2`'s `keys()`) was resolved by hand.
- **The recipe closure:** traced from `dku recipe get-settings` for all 95 recipes.
- **Library and variable use:** from `dss_recipes/*.py`, `dss_lib/demo_identity.py`, the visual
  recipe payloads and `dku project get-variables`.
- **The score equality and the qualified read:** tested with the dataiku client from the webapp's
  environment, reading live DSS. Outputs are kept in the session scratchpad, not in `data/`.
