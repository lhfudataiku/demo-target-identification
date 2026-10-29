# Flow migration — workplan

> **Lifecycle:** Planning (draft) · **Audience:** DSS flow maintainers and technical reviewers ·
> **Authority:** the sequence, method and acceptance criteria for moving the notebooks' supporting
> evidence into its own DSS project and reorganising the webapp's serving flow by function · **Update
> when:** a step is accepted or re-scoped, or a fact in §2 is superseded · **Generated dependencies:**
> none · **Excludes:** what the webapp reads and the serving-flow counts, in
> [`WEBAPP_DATASET_MAP.md`](WEBAPP_DATASET_MAP.md); the boundary rule and target zone layout (D14,
> D15) and the evidence project's mandate (D13), in
> [`WEBAPP_REDESIGN_SCOPE.md`](../../archive/WEBAPP_REDESIGN_SCOPE.md) and
> [`WEBAPP_REDESIGN_WORKPLAN.md`](../../archive/WEBAPP_REDESIGN_WORKPLAN.md) Phase 0, which M0 amends.

**Status: DRAFT — revised 2026-10-28. Step G is decided: the full option (M0–M6), chosen by the
user on 2026-10-28. Two M0 decisions are also taken: the notebooks run locally from the repository,
and the shortlist ranks with ties. The rest of M0 is not approved, and nothing in DSS has changed.**

## 1. Purpose and premise

**The premise.** The notebooks are the supporting evidence for model development. They stay in the
repository (`notebooks/*.py`), remain the source of truth for the documented numbers, and are **kept
locally**: they run from the repository, and no copy lives in a DSS project library. The
`validate_notebooks` scenario is dropped.

A notebook reading zone 40 or later is reasonable for model evidence. The project clean-up still
prefers a clean separation (D14), so a **supporting evidence project** (D13) is required for future
development and validation:

- it reads `DEMO_TARGET_IDENTIFICATION`'s zones 00–31 through exposed objects, and nothing after
  zone 31;
- it recomputes everything the notebooks read from zone 40 or later;
- it holds the notebook-only recipes;
- it is the project the notebooks' downstream reads resolve to when they run locally.

`DEMO_TARGET_IDENTIFICATION` keeps the imports, the model build and the webapp's serving flow.

**The serving path is re-zone, then rebuild.** The rebuild uses zone `S1 Shortlist` as its
reference. S1 was built for the redesign (Phases 3–6) directly from upstream datasets, using visual
recipes, managed storage and Parquet. It stays as it is.

| step | what | DSS change |
|---|---|---|
| G | how far to go: **decided 2026-10-28, full** | — |
| M0 | decisions | — |
| M1 | inventory and mapping | — |
| M2 | the evidence project | new project; recipes moved and copied; scenario deleted |
| M3 | re-zone the serving flow | zone renames and moves (metadata only) |
| M4 | rebuild the serving flow beside the old | new recipes and datasets |
| M5 | switch the webapp to the rebuilt datasets | deploy |
| M6 | retire and tidy | deletions, zone 20 moves, descriptions, scenario |

**The options at G**, with counts for the main project's flow after zone 31 (plus
`compute_breast_panel`) taken from [`WEBAPP_DATASET_MAP.md`](WEBAPP_DATASET_MAP.md). The full option
was chosen; the other two are kept for the record.

| option | steps | main-project recipes / datasets | leaves |
|---|---|--:|---|
| **full (chosen)** | M0–M6 | 47 → 41 after M2 → 32 after M6 | notebooks independent of every serving zone; the serving flow organised by function, carrying only what the webapp reads; one scoring run; ranks with ties |
| evidence project and re-zone | M0–M3, the M6 tidy | 47 → 41 | as above, but the serving flow keeps both scoring runs and the intermediates the notebooks still need. These are duplicated in the evidence project |
| evidence project only | M0–M2 | 47 → 41 | the notebooks independent; serving zones still named A1–A3 and 40 |

**Why the steps run in this order:**

- **The evidence project depends on nothing in the serving flow.** It reads only zones 00–31, so M2
  and M3 can run in either order or side by side.
- **Re-zoning is free.** Moving a recipe or dataset between zones and renaming a zone are metadata:
  nothing is built and no dataset is renamed, so the webapp is untouched.
- **The rebuild waits on work the re-zone does not need:** an identity-recipe change, repoint
  versus rename, and a compare script.
- **The rebuild comes after M2.** Three of the datasets it drops from the serving flow are ones the
  notebooks read: `novel_discovery_eval`, `persona_candidates` and `persona_enrichment`. After M2 they
  live in the evidence project, so the rebuild can drop them without affecting any notebook.

Every step that changes DSS needs the user's approval at the time. The user runs builds, scenarios,
deletions and `make deploy`; Claude verifies read-only. Nothing is committed without the user's
approval.

## 2. Starting point (measured 2026-10-27)

**The flow.** 110 datasets (97 local and 13 imported from `DEMO_KG_LS`) in 18 zones. The Default zone,
labelled "Agent" in `dku flow zones`, holds the 14 shared `DEMO_KG_LS` objects: 13 datasets and the
Kuzu source folder.

After zone 31 there are 46 recipes and 46 datasets: 40 (11), S1 (5), A1 (5), A2 (16), A3 (6),
A4 (3). The `act4_evidence_cache` folder (`CB9xqCGg`) is in no zone. S1's recipes read only zones
00–31 (`graph_nodes`, `hgnc_identity`, `drug_protein_edges`, `drug_disease_edges` and the saved
model `hJLGoYn4`), except that `score_persona_candidates_shap5` reads `validation_set_personas_2`
from zone 40.

**What the webapp reads** is in [`WEBAPP_DATASET_MAP.md`](WEBAPP_DATASET_MAP.md) §2, route by route,
with fields and row scope. Two kinds of read already break D14's "serving zones only":

- `dashboard_candidates`, which is still in zone 40;
- three metadata-only reads: the `COUNT_RECORDS` metric of the zone-10 DWPC datasets, the saved
  model's metrics, and the Kuzu folder `ytvuniN8` (zone 04) behind the graph tool.

**What the notebooks read from zone 40 or later:** 15 distinct datasets, in 23 reads.

| notebook | reads from zone 40 or later |
|---|---|
| `nb1`, `nb3b` | — |
| `nb2` | `split_audit_2` (A2); `known_drug_truth`, `pool_reachability` (A4) |
| `nb3` | `drug_target_benchmark`, `family_auc_by_family`, `validation_auc_by_disease` (A2) |
| `nb4` | `novel_discovery_eval`, `persona_candidates` (A2); `family_panel_overlap` (A3); `filter_three_axes`, `known_drug_truth` (A4) |
| `nb5` | `validation_auc_by_disease` (A2) |
| `nb6` | `dashboard_candidates` (40); `drug_target_benchmark`, `novel_discovery_eval`, `validation_auc_by_disease` (A2); `family_panel_overlap` (A3) |
| `nb7` | `dashboard_candidates` (40); `persona_enrichment` (A2); `demo_panel_config`, `family_panel`, `family_panel_overlap`, `family_panel_programme` (A3) |

- **Eight of these are also read by the webapp:** `dashboard_candidates`, `validation_auc_by_disease`,
  `split_audit_2`, `family_auc_by_family`, `persona_enrichment`, `demo_panel_config`,
  `family_panel_overlap` and `family_panel_programme`.
- **From `dashboard_candidates`, the notebooks read 8 columns:** `disease_index`, `gene_index`,
  `disease_name`, `gene_name`, `rank_in_disease`, `is_target`, `has_safety_liability`,
  `approved_for_disease`.
- **The notebooks also read 14 objects in zones 00–31 directly**, at 29 read sites:
  `scored_champion` (in six of the scripts), `graph_nodes`, `graph_edges`, `drug_protein_edges`,
  `drug_disease_edges`, `raw_ot_known_drug`, `raw_disease_disease`,
  `enriched_gene_druggability_v2`, `enriched_gene_safety_v2`,
  `enriched_graph_features_candidate_psplit`, `psplit_train_set`, and the three DWPC feature
  datasets.
- **The evidence project's recipes read 18 exposed objects in all.**
  [`EVIDENCE_PROJECT_DESIGN.md`](EVIDENCE_PROJECT_DESIGN.md) §3.1 lists them.

**Notebook-only objects in the main project**, which nothing the webapp reads depends on:

| zone | recipe → dataset | fate |
|---|---|---|
| A4 | `compute_known_drug_truth` → `known_drug_truth`; `compute_filter_three_axes` → `filter_three_axes`; `compute_pool_reachability` → `pool_reachability` | move to the evidence project. `compute_filter_three_axes` reads `target_candidates_2` (zone 40), so its input changes (M1) |
| 31 | `compute_breast_panel` → `breast_panel_metrics` | move to the evidence project |
| 02 | `compute_raw_ot_known_drug` → `raw_ot_known_drug` | stays: an import, which the evidence project reads |
| 40 | `compute_shap_drivers_long` → `shap_drivers_long`; `compute_shap_driver_frequency` → `shap_driver_frequency` | delete: read by no notebook and nothing else |

`drug_target_benchmark`, `novel_discovery_eval` and `persona_candidates` are notebook datasets on the
path to served `orthogonality_scatter` and `persona_enrichment`. So they stay in the serving flow
until the rebuild (M4) removes the last two, and the evidence project carries its own copies.

**What else assumes the notebooks or a single project:**

- **The `validate_notebooks` scenario:** has had no steps since 2026-10-05, and its last green run was
  2026-09-03. There is no current live baseline for the assertions.
- **The library folder** `/python/nb_assertions/`; `tools/push_assertions.py`, which targets
  `DEMO_TARGET_IDENTIFICATION`; and its drift check in `tools/check_indexes.sh`.
- **The notebook runner, `tools/nb_assertions/runner.py`:** executes a script and raises on any stale
  check.
  - The scripts read datasets by bare name, so they resolve in whichever project is the default. The
    webapp's local client (`set_remote_dss` with `set_default_project_key`) can make any project the
    default.
  - The scripts read only datasets: no project variables and no folders.
  - Beyond `dataiku`, `pandas` and `numpy`, they import `matplotlib`, `seaborn`, `IPython` and
    `nb_assertions.derive` (under `tools/`). The webapp's environment lacks the first three, and in
    DSS the scripts ran on Python 3.13.
- **`build-governance/POLICY.json` `allowed_targets`:** keyed by project. Under
  `DEMO_TARGET_IDENTIFICATION` it lists `breast_panel_metrics` and `breast_panel_overlap`, which was
  deleted on 2026-09-03.
- **`IDENTITY_RECIPES`** in `tools/check_governed_values.py` (`DEC-OPS-006`):
  `compute_demo_panel_config`, `compute_breast_panel` and `compute_split_audit_2`.
- **`.index/_dead.json`:** marks `breast_panel_metrics` "do not migrate". D13 reverses that.
- **`tools/dataset_descriptions.json`:** describes the datasets that move. `push_descriptions.py
  --check` fails when a described dataset is absent from the main project.
- **Hardcoded project keys:** `build_flow_map.py`, `build_recipe_index.py`, `check_freshness.py`,
  `capture_build_governance.py`, `check_shap_top5.py` and `push_descriptions.py` name
  `DEMO_TARGET_IDENTIFICATION`.

**Scenarios:**

- **`Refresh_serving_layer`** (last run 2026-08-25) rebuilds A1, A2, A3 and 40 non-recursively. Its
  steps name `shap_drivers_long` and `shap_driver_frequency`, and nothing in S1 or A4.
- **`prefill_evidence_cache`** reads only `dashboard_candidates` and the cache folder.

**Dashboards.** Both project dashboards and their twelve dataset-reading insights were deleted on
2026-10-27. Two insights remain, and neither reads a dataset: `ZZ_TMP_probe_webapp` and the Visual
Graph plugin's `published_kg_ls`.

**Zone 20 does three unrelated jobs.** Split by name, drug and gene annotation would depend on each
other in both directions, a zone cycle. M1 (map §6.2) places the druggability output with the drug
chain that computes it, which makes the split one-way:

| zone | datasets |
|---|---|
| gene annotation | `gene_crosswalk`, `enriched_gene_localization`, `gene_safety_joined`, `enriched_gene_safety_v2` |
| druggability and drug evidence (reads gene annotation) | `ot_drug_mapped`, `drug_joined`, `drug_classified`, `enriched_gene_druggability_v2`, `drug_evidence_pairs` |
| disease family and split key | `hetionet_disease_slim`, `disease_family_id` |

It carries the leakage-control split key, so it is **re-zoned, never rebuilt**. Recomputing it would
ripple through the split, the model and every downstream number.

**The build order runs through the family panels.** `filter_persona_diseases` takes the 12 shortlist
diseases from `demo_panel_config.in_act4`. So the order is `validation_auc_ci` (A2) → `family_panel`
→ `demo_panel_config` (A3) → zone 40 → S1, not "shared core first" as D15 draws it.

**Facts that govern any rebuild, re-run or evidence-side recompute of the shortlist:**

- `score_persona_candidates` and `score_persona_candidates_shap5` give identical probabilities: the
  maximum difference over 105,702 pairs is 0.
- 4,514 rows, in 903 tie groups of up to 160 rows, tie on score within their disease.
  `rank_per_disease` numbers them in arbitrary order; re-ranking reorders 3,156 of them, all tied.
  Ties start at rank 14: 2 rows in the top 20 and 11 in the top 200, all in diabetes mellitus and
  psoriatic arthritis. HER2+'s top 200 has none.
- **Ranking with ties (decided)** gives tied scores the lowest rank of their group, and the next rank
  skips (1, 2, 2, 4). On today's list:
  - 3,611 rows change rank, every one of them tied; no untied row moves. Dense ranking (1, 2, 2, 3)
    would instead shift 92,909 untied rows, so it is not used.
  - Every tie group holds consecutive ranks today (903 of 903), so a tied row's new rank is the
    lowest rank its group holds now.
  - `rank_percentile` changes on 2,155 rows.
  - No tie group straddles rank 20, 50 or 200 in any disease, so the backend's and the notebooks'
    cut-offs select the same rows. HER2+, and the 21 pre-filled pairs, do not change.

**Stale state that M6 fixes:**

- **Zone `shortDesc` texts still describe acts.** Zone 40 says it is "consumed by A2, A3 and A4";
  only A4 and S1 read it.
- **`disease_pool_sizes` has no stored data.** Its storage path does not exist.
- **`notebooks/README.md`** still describes the dissolved zone 90 and the scenario.
- **`DEC-ARCH-001`** says Part 2 syncs 12 datasets; it syncs 13 since `hgnc_identity`.

## 3. Steps

| step | done when |
|---|---|
| G | the user picks an option in §1 |
| M0 | the user approves the ADR and register diff |
| M1 | the user approves one table |
| M2 | every notebook runs green locally against the evidence project; governed claims unchanged; the webapp unchanged |
| M3 | no build ran; the webapp reads only S1–S4 and the named exceptions |
| M4 | zero unexplained differences between old and new served datasets |
| M5 | every route returns the same payload, apart from the predicted tied ranks |
| M6 | the map is clean and `tools/check_indexes.sh` passes for both projects |

### M0 — decisions

**Drafted 2026-10-28, awaiting approval.** The draft is an uncommitted diff:

- [ADR-003](../decisions/adrs/ADR-003-evidence-project.md), which extends `ADR-001` to three projects;
- four new register entries, `DEC-ARCH-006`, `DEC-OPS-007`, `DEC-MEAS-005` and `DEC-ARCH-007`, each
  `approved-not-executed`, a status that takes effect on approval;
- dated consequence notes on `DEC-ARCH-001` (whose sync count is corrected from 12 to 13),
  `DEC-OPS-003`, `DEC-OPS-005`, `DEC-OPS-006` and `DEC-DEMO-005`;
- a pointer to ADR-003 in `ADR-001`'s header.

| decision | where | content |
|---|---|---|
| the evidence project | ADR-003, `DEC-ARCH-006` | key `DEMO_TI_EVIDENCE`, name "Target Identification — Supporting Evidence"; it owns the notebook-only recipes and the evidence copies; it reads exposed zone 00–31 objects directly, with no sync copies; nothing reads it, and no build crosses the boundary; its datasets keep their main-project names |
| how the notebooks run | `DEC-OPS-007` | locally, through `runner.run()` and a wrapper, with qualified literal reads of zones 00–31; the scenario, the library copy and `push_assertions.py` are retired |
| ranking with ties | `DEC-MEAS-005` | lowest rank of the tie group, the next rank skipping (1, 2, 2, 4); `gene_name` sets the display order within a tie |
| the serving flow | `DEC-ARCH-007` | re-zone, then rebuild with S1 as the pattern; amends D14 (the backend's metadata reads outside the serving zones) and D15 (the panel definition sits in the zone-40 core) |
| build governance | `DEC-OPS-005` note | `breast_panel_metrics` allowlisted under `DEMO_TI_EVIDENCE`; `breast_panel_overlap` removed; the pilot artifacts stay as history |
| identity recipes and variables | `DEC-OPS-006` note | both copies of `compute_demo_panel_config` and `compute_split_audit_2` are checked against one mirror, and both projects' variables against each other |

**Proposed answers to the open items** in
[`EVIDENCE_PROJECT_DESIGN.md`](EVIDENCE_PROJECT_DESIGN.md) §7 and earlier in this plan:

- **Project key and name:** `DEMO_TI_EVIDENCE`, "Target Identification — Supporting Evidence".
- **The evidence shortlist keeps the name `dashboard_candidates`.** The project boundary
  disambiguates it, and `nb6` and `nb7` change nothing.
- **The window column trims are accepted** on one condition: the grouped outputs match the main
  project's exactly (M2 compare).
- **Variables are copied once at creation.** The governed-values check then asserts the two projects
  are equal. The variables change rarely (`DEC-OPS-006`), so no sync script is needed.
- **`compute_demo_panel_config` takes its disease names from `graph_nodes`**, already one of its
  inputs, instead of `persona_enrichment`, in both projects. The two copies stay identical, and the
  panel no longer depends on the persona chain. Its output is unchanged, because both name sources
  are the graph's disease node names.
- **`nb6`'s lung-family ranking stays as it is.** It prints, asserts nothing, and is not the
  shortlist. `DEC-MEAS-005` covers the two shortlists only.
- **The rebuild's switch method:** repoint the backend's one constant per dataset in M5. In M4,
  try renaming one small managed dataset. If the rename keeps its data and recipe links, M6 renames
  the new datasets back to the original names with a second deploy; otherwise the new names stay.

**Done when:** the user approves this diff.
- **The rebuild's switch method:** repoint the backend's constants to suffixed names, or delete the old
  datasets and rename the new ones to the old names. Check rename behaviour on one small managed
  dataset first.
- **Done when:** the user approves the ADR and register diff.

### M1 — inventory and mapping (read-only)

- Refresh the snapshot and the map: `python3 tools/build_recipe_index.py --refresh`, then
  `python3 tools/build_flow_map.py`.
- **The evidence half is drafted** in [`EVIDENCE_PROJECT_DESIGN.md`](EVIDENCE_PROJECT_DESIGN.md)
  (2026-10-28): every notebook read, the 24–25 recipes, the 18 exposed inputs, and the per-script
  revisions.
- **For each notebook read** in §2, decide how the evidence project provides it from zones 00–31:
  - a recipe moved from the main project;
  - a recipe copied from the main project;
  - recomputed in notebook code, where that is lighter;
  - a synced copy of an exposed object.
  It is never a read of a serving zone.
- **For each notebook script**, list the revisions M2 makes:
  - which reads become project-qualified and which point at evidence datasets;
  - anything that assumed the DSS library or the scenario.
- **`compute_filter_three_axes`** gets its ranked shortlist from the evidence side: `scored_champion`
  restricted to the 12 shortlist diseases, ranked with ties. **Checked 2026-10-28:** that
  restriction holds exactly the 105,702 served pairs, with `proba_1` equal to the served `score`
  (maximum difference 0) and the same `is_target`.
- **The serving flow, drafted 2026-10-28** in [`WEBAPP_DATASET_MAP.md`](WEBAPP_DATASET_MAP.md) §6:
  - every dataset after zone 31 mapped to its zone under M3 and its fate under M4–M6 (§6.4);
  - one window recipe gives both the rank with ties and the pool size, so the rebuild ends at 32
    recipes (§6.1);
  - each rebuilt dataset's fields are taken from map §2.
- **Zone 20, drafted 2026-10-28** (map §6.2): every move is `dku flow move`, which builds nothing.
  The planned job split was corrected, because it made a zone cycle.
- **Done when:** the user approves the two tables, map §6.4 and the evidence design's §2–3.

### M2 — the evidence project *(DSS)*

- **Set up the local run first. Done 2026-10-28.**
  - `tools/run_notebooks.py` runs each assertion script through `runner.run()` with a chosen
    default project, and reports every script even when one fails.
  - `notebooks/pyproject.toml` pins the environment to the DSS code env `demo_kg-drug-discovery`:
    Python 3.13, pandas 2.3.3, numpy 2.3.5, scipy 1.16.3, matplotlib 3.11.2, seaborn 0.13.2,
    IPython 8.12.3, and the instance's dataiku client.
  - `nb5_data_exploration` is not run, as `push_assertions.py` never ran it: it defines no check.
- **Take a baseline. Done 2026-10-28** against `DEMO_TARGET_IDENTIFICATION`, with the scripts
  unchanged: **all 7 pass, 150 checks executed, 0 stale**, in about 15 minutes.

  | script | checks executed | stale |
  |---|--:|--:|
  | `nb1_features_and_config` | 6 | 0 |
  | `nb2_splitting_and_pool` | 19 | 0 |
  | `nb3_validation_and_plots` | 9 | 0 |
  | `nb3b_hub_bias_meter` | 7 | 0 |
  | `nb4_results_three_axes` | 24 | 0 |
  | `nb6_interrogation_and_close` | 34 | 0 |
  | `nb7_panel_selection` | 51 | 0 |

  The run's record is in `data/assertion_runs/2026-10-28_baseline_main.json`, which is not
  committed. M2 is accepted against these executed counts. They differ from the per-script entry
  counts in `.index/assertions.tsv`, which counts parsed expectations, not executed calls.
- **Create the project.** Expose the zone 00–31 objects M1 listed. Use them directly as recipe
  inputs, or sync them in if M0 chose copies. New datasets use managed storage and Parquet, and joins
  are visual Join recipes.
  - **Prepared 2026-10-28: `tools/setup_evidence_project.py`.** It is a dry run unless given
    `--apply`. In order, it:
    1. creates `DEMO_TI_EVIDENCE`;
    2. sets its default Python env to `demo_kg-drug-discovery`;
    3. copies the main project's 8 standard variables verbatim;
    4. writes `/python/demo_identity.py` from `dss_lib/` (checked equal to the main project's copy);
    5. adds the 18 exposure rules to `DEMO_TARGET_IDENTIFICATION`'s settings.

    It then reads everything back. Each step is idempotent, so a re-run resumes.
  - **The dry run of 2026-10-28 showed:** the key is free, all 18 inputs exist, and no exposure is
    present yet.
  - **Applied 2026-10-28 by the user (`--apply`, read back OK).** A separate read-only check
    confirmed:
    - the project label and the code env;
    - variables equal to the main project's;
    - the library file identical to `dss_lib/demo_identity.py`;
    - 18 exposures, the main project's only exposed objects;
    - 0 datasets and 0 recipes in the evidence project;
    - a qualified read of `DEMO_TARGET_IDENTIFICATION.disease_family_id` working with
      `DEMO_TI_EVIDENCE` as the default project.
  - **The one change to the main project is the exposure rules, and they are additive.** Nothing is
    built, moved or removed.
  - **The instance-wide dataset defaults list CSV formats first,** so each evidence recipe sets
    managed storage and Parquet on its output explicitly.
- **Build the evidence flow: prepared 2026-10-28 as `tools/build_evidence_flow.py`.** It covers the
  two bullets below and the shortlist. It is a dry run unless given a flag. No flag builds anything.
  - **What `--apply` does.** It writes only to `DEMO_TI_EVIDENCE`. It creates 25 recipes and 25
    empty Parquet datasets on managed storage, in zones E1–E4:
    - 21 recipes are recreated from the main project's live definitions. DSS cannot copy a recipe
      into another project from the API.
    - 4 recipes make up the slim shortlist: join and filter, window *rank*, decorating join, and a
      prepare. The prepare fills `approved_for_disease` with 0, as the served table does.
  - **A design gap it closes.** A Python recipe reads a foreign input only by its qualified name. The
    dataiku client matches `dataiku.Dataset(name)` against the declared inputs, and a foreign input
    is declared as `DEMO_TARGET_IDENTIFICATION.<name>`.
    - Each copy's code is therefore the main project's live code with its own upstream inputs
      qualified. Each diff was checked line by line against `dss_recipes/`.
    - `dss_lib/demo_identity.py` now names `DEMO_TARGET_IDENTIFICATION.graph_nodes`. That name
      also resolves in the main project.
    - `setup_evidence_project.py`'s check that the library equals the main project's copy fails
      until `--main-identity` runs.
  - **What `--main-identity` does.** It aligns the main project, without building:
    - it writes the same library file;
    - it sets `compute_split_audit_2` and `compute_demo_panel_config` to the evidence code;
    - it drops `persona_enrichment` from the panel recipe's inputs (M0).

    `build_recipe_index.py --refresh` then mirrors these changes into `dss_recipes/`.
  - **Checked read-only before writing.**
    - On all 670 `family_panel` diseases, `graph_nodes` names equal `persona_enrichment`'s, and
      every config name matches.
    - Every join key in the shortlist is unique.
    - The graph names equal the served `gene_name` and `disease_name` on all 105,702 rows.
    - The 126 approved pairs reproduce.
    - `target_candidates_2` and `dashboard_candidates` hold the same 105,702 pairs and ranks, so
      `compute_filter_three_axes` loses nothing by switching inputs.
    - `family_validation_scored` has `scored_champion`'s schema exactly.
  - **Applied 2026-10-28 by the user (`--apply`, in three runs; read back OK).** Two faults were
    fixed between runs:
    - DSS reads a Prepare recipe's input files when creating it, and nothing was built yet, so
      Prepare recipes are now created in raw mode;
    - a new join writes the output columns DSS generated when the recipe was created, not the
      per-input selection, so the script now sets that list itself.

    A separate read-only check confirmed:
    - 25 recipes and 25 datasets, in zones E1 12, E2 5, E3 4 and E4 4;
    - every visual copy's payload equal to the main project's;
    - `dashboard_candidates` carrying the 12 required columns;
    - the shortlist: the `in_act4` pre-filter, an inner join, *rank* (not dense) partitioned by
      disease and ordered by `proba_1` descending, and the fill step;
    - the main project unchanged: 95 recipes and 18 exposures.

  - **Built 2026-10-28 by the user, and compared read-only with the main project.** Three faults
    surfaced in the build:
    - The main project's `gene_crosswalk` had no files. It is *virtualizable*, so recursive builds
      passed it in memory and never wrote it, while its cached metrics still showed 20,861 rows.
      The user rebuilt it on its own. Its 17 sibling shared datasets keep the flag, so a later
      recursive main-project build can drop one again.
    - This instance marks every new dataset virtualizable, so the shortlist chain was never written
      either. `--apply` now clears the flag on each evidence output, and read-back checks it.
    - Raw creation left the new Prepare recipe without engine settings (an NPE on `engineType`), so
      it now takes the copied Prepare recipes' settings.

    A non-recursive job with several targets runs them side by side, not in dependency order, so
    the outputs with no files were built in four ordered jobs.

    Compare (canonical sort, floats to 9 places; the two ~4M-row window outputs on keys, `proba_1`
    and `rank` only):
    - all 21 copies are identical to the main project's, `filter_three_axes` included, although it
      now reads the slim shortlist;
    - `dashboard_candidates` has the served table's 105,702 pairs, and every value column and the
      score are equal;
    - 3,611 ranks changed, all on tied scores and none on untied ones, and every rank is the
      competition rank (1, 2, 2, 4).

  - **`--main-identity` applied 2026-10-28 by the user (read back OK), with no build.** The main
    project's library and its `compute_split_audit_2` and `compute_demo_panel_config` code now equal
    the evidence copies, which built to identical outputs. `compute_demo_panel_config` reads
    `family_panel` and `graph_nodes` only. A read-only check found 95 recipes and 18 exposures, as
    before. `build_recipe_index.py --refresh` mirrored the two recipes; the refresh also first saw
    the `target_evidence_agent` LLM agent, now recorded in `tools/model_registry.json` as not a
    prioritizer model.
  - **The window column trims, applied and accepted 2026-10-29** (the user ran `--apply` and the
    rebuild; read back OK). Only the evidence copies are trimmed; the main project's keep all 46
    columns.
    - `compute_validation_set_scored_windows` retrieves `disease_index`, `gene_index`, `is_target`
      and `proba_1`, and `window_family_rank` also `disease_family_id`; both add `rank`. The
      per-disease group lost its inactive entries for the dropped columns, and kept its six
      aggregates. `group_family_auc` needed no change.
    - The builder holds the trims as data (`WINDOW_TRIMS`). Read-back fails if a window's output has
      any other column.
    - The four-stage non-recursive rebuild of the evidence AUC chain was compared read-only with the
      main project: both windows (3,958,921 rows, on the kept columns), both groups, and
      `validation_auc_by_disease`, `family_auc_by_family` and `validation_auc_ci` are identical. M0's
      condition holds.
- **Move the four notebook-only recipes and their datasets** (§2).
  - DSS cannot move a recipe between projects, so copy it (copy subflow to another project, or
    recreate it), then delete the main-project original once M2 is accepted.
  - `compute_filter_three_axes` takes the input M1 decided.
- **Copy the recipes behind the notebooks' other reads**, following M1's table:
  - the per-disease and per-family AUC chains, with the interval;
  - `compute_split_audit_2`, `compute_drug_target_benchmark`, `compute_novel_discovery_eval`,
    `compute_persona_candidates` and `compute_persona_enrichment`;
  - `compute_family_panel` and `compute_demo_panel_config`, with the `demo_identity` library module
    and the `demo_panel` and `thresholds` project variables;
  - the three family-panel scripts;
  - an evidence-side shortlist carrying the 8 columns `nb6` and `nb7` read, ranked with ties.

  This is 24–25 recipes ([`EVIDENCE_PROJECT_DESIGN.md`](EVIDENCE_PROJECT_DESIGN.md) §3), plus one
  sync per upstream object if M0 chose copies.
- **Revise the notebooks** as M1 listed. The revision changes where a script reads; it never changes
  an assertion's expected value. A value that moves is investigated (§4).
  - **Done 2026-10-28.** The 14 main-project inputs are read by their qualified names: 32 reads in
    the eight scripts and `tools/nb_assertions/derive.py` (the design's 29 sites, counting
    `raw_ot_known_drug` twice and the `keys()` helper's three calls). The evidence datasets keep
    their bare names. No `check(...)` line changed.
  - **Run locally against `DEMO_TI_EVIDENCE`:** all 7 pass, with the baseline's 150 checks
    executed and 0 stale, in about 15 minutes. The per-script counts equal the baseline's. `nb5`,
    which asserts nothing, also ran through. The record is in
    `data/assertion_runs/2026-10-28_evidence.json`, which is not committed.
  - `tools/build_flow_map.py` accepts the project prefix, so the map still lists these notebook
    readers. `check_indexes.sh` now fails on `push_assertions.py --check`: the main project's
    `/python/nb_assertions/` copies predate the revision. That check retires with the tooling step
    below; nothing is pushed to the library in the meantime.
- **Point the tooling at the evidence project:** the runner wrapper, `POLICY.json` and
  `IDENTITY_RECIPES` as M0 decided. Retire `push_assertions.py` and its call in `check_indexes.sh`.
  - **Done 2026-10-28, repository only.**
    - `push_assertions.py` is deleted, along with its `--check` in `check_indexes.sh`. The runner,
      `notebooks/README.md` and the target-id skill's number-update reference now describe the
      local run; nothing tells a reader to push.
    - `build_recipe_index.py --refresh` also snapshots the evidence project's identity recipes and
      variables. `check_governed_values.py` gains a fourth rule: the shared identity recipes
      (`compute_demo_panel_config`, `compute_split_audit_2`) equal the one mirror in both projects,
      every evidence copy holds no bare `node_index`, and the two projects' variables are equal. It
      passes, and a tampered snapshot trips all four failure kinds. The evidence
      `compute_breast_panel` differs from its main mirror only by its four qualified reads.
    - `POLICY.json` allowlists `breast_panel_metrics` under `DEMO_TI_EVIDENCE` and drops
      `breast_panel_overlap`. The main-project entry stays until the original is deleted: the
      governance tests replay the 2026-08-31 pilot, which ran there. The 11 tests pass.
    - **Left for the deletions:** once `compute_breast_panel` leaves the main project, its
      `dss_recipes/` mirror must come from the evidence copy, and the main `POLICY.json` entry,
      the pilot-based tests and `capture_build_governance.py`'s project key move with it.
- **Main-project changes:**
  - edit `Refresh_serving_layer` to drop `shap_drivers_long` and `shap_driver_frequency`;
  - then delete those two recipes and datasets;
  - delete the `validate_notebooks` scenario and the `/python/nb_assertions/` library folder;
  - after acceptance, delete the four moved originals.

  `tools/clean_main_project.py` does both stages (dry run by default). Before writing, it refuses
  any delete whose dataset has a reader outside the set, is exposed, or is named by a scenario; stage
  2 (`--originals`) also requires each evidence copy to hold stored rows.
  - **Stage 1 applied 2026-10-29 by the user (read back OK).** `Refresh_serving_layer`'s zone-40
    step went from 11 builds to 9; the two SHAP recipes and datasets, `validate_notebooks` and the
    library folder are gone. The main project has 93 recipes, 95 datasets and 18 exposures. The
    refresh removed the `compute_shap_drivers_long` mirror; `_dead.json` lists the pair as deleted,
    and `dataset_descriptions.json` no longer describes it. `check_harness.py` now skips a tracked
    file deleted in the working tree, which the removed mirror had crashed.
  - **Stage 2 applied 2026-10-29 by the user (read back OK).** The four originals are gone; the main
    project has 89 recipes and 91 datasets, and zone A4 is empty (M3 deletes it). Repository
    follow-ups:
    - `build_recipe_index.py` mirrors the four moved Python recipes from their evidence copies
      (`EVIDENCE_OWNED`) and reports them as evidence mirrors, not stale ones. The mirrors changed
      only in their qualified reads, and `compute_filter_three_axes` in its input.
    - `check_governed_values.py` checks every identity recipe's evidence copy against its mirror;
      `compute_breast_panel` now has one source, like the other two.
    - Build governance moved to `DEMO_TI_EVIDENCE`: `POLICY.json` allows only that project;
      `capture_build_governance.py` captures there and accepts inputs qualified by the main
      project's key (checked read-only against the live recipe); the test fixtures' project key
      moved with it, and the 11 tests pass. The 2026-08-31 pilot artifacts stay as history.
    - `dataset_descriptions.json` gives the four datasets `"project": "DEMO_TI_EVIDENCE"`, and
      `push_descriptions.py` checks and pushes each dataset in its own project. The user ran
      `--push` 2026-10-29 (47 datasets, 567 column descriptions), and the check is clean.
    - `_dead.json` lists the four under `moved_to_evidence_project`, and `breast_panel_metrics`
      leaves `keep_do_not_prune`.
  - **Checked after both stages, 2026-10-29:**
    - **Notebooks:** a local run against `DEMO_TI_EVIDENCE` passes all 7 scripts with 150 checks
      executed and 0 stale, the same per-script counts as 2026-10-28. The record is in
      `data/assertion_runs/2026-10-29_evidence.json`, not committed.
    - **Webapp:** every read route handler, called locally against the main project, returns
      without error: 163 calls over 3 families, 12 diseases and 23 genes. The sources routes (an
      external search and a cache write on a miss) and the assistant were left out. No dataset
      the backend reads was built after 2026-10-26, before M2 began, so M2 cannot have changed a
      payload. The payloads are in `data/webapp_payloads/2026-10-29.json`, not committed, as M5's
      "before".
    - **The map:** `build_flow_map.py` now counts only a notebook's qualified reads against the
      main project; a bare name reads the evidence copy. The main map's notebook readers are the 14
      upstream datasets in zones 00–31, none in a serving zone. Endpoints fell from 40 to 35, and
      `disease_family_id`, which nb6 and nb7 quote only as a column, is no longer miscounted.
- **Repository changes:** `_dead.json` loses its keep entry; `dataset_descriptions.json` drops the
  entries for the moved datasets, or `push_descriptions.py` learns the second project;
  `notebooks/README.md` is rewritten.
  - **Done 2026-10-29.** `_dead.json` and the descriptions are recorded with stage 2 above.
    `notebooks/README.md` is rewritten for the local run: how to run it, where each script reads in
    each project, and the history, with the zone-90 tables dropped. `run_notebooks.py`'s docstring no
    longer suggests `--project DEMO_TARGET_IDENTIFICATION`, which stopped working when the
    originals were deleted.
- **Done when:**
  - every script runs green locally against the evidence project, with the baseline's check counts,
    and `.index/assertions.tsv` lists the same expected values;
  - `python3 tools/check_claim_registry.py --check` and `tools/check_governed_values.py` pass with
    every governed claim at the same value;
  - every webapp route returns the same payload as before;
  - the main project's map shows no notebook reader.

### M3 — re-zone the serving flow *(DSS: metadata only)*

- Rename zones A1 → `S2 Evidence · graph`, A2 → `S3 Evidence · reconstruction` and
  A3 → `S4 Evidence · family panels`. Zone ids do not change.
- Move `finalize_dashboard_candidates` and `dashboard_candidates` from 40 to S1, and put the
  `act4_evidence_cache` folder in S1.
- If M0 approved it, move `compute_family_panel`, `family_panel`, `compute_demo_panel_config` and
  `demo_panel_config` to 40.
- Delete the empty A4 zone. Trigger no build.
- **Done when:**
  - the map shows the webapp reading only S1–S4 plus the exceptions M0 named;
  - every dataset's last build date is unchanged;
  - the routes return the same payloads.

### M4 — rebuild the serving flow beside the old *(DSS)*

- **S1 is the pattern, and its five recipes are neither rebuilt nor compared.** Each new chain reads
  zones 00–31 and the panel definition, never another serving zone's output. It uses visual recipes,
  managed storage and Parquet.
- **Build the chains in map §4.2**, writing new datasets with a distinct suffix so old and new
  coexist.
  - **Shortlist, in S1:** S1's existing scoring run (`persona2_scored_shap5`) → a window giving the
    rank with ties and the pool size → one annotation join (druggability, safety, gene and disease
    names, drug flags) → the finalize prepare. This replaces zone 40's own scoring run and its
    six-step chain.
  - **Section 2:** the per-disease chain ends in one prepare that carries the AUC, the interval,
    `auc_trustworthy`, `module_size`, `rank_enrichment` and the disease name. The per-family window
    reads `scored_champion` directly.
  - **Section 3:** the family-panel recipes, repointed to that prepare's output.
- Build with one job, repeated `--target`, recursive only within the new chains. Zone 20 and zones
  00–31 are never rebuilt.
- **Compare** every new served dataset with its old counterpart. A script under `tools/` writes
  nothing to DSS, and the inputs are pulled into `data/`, which is never committed. It checks:
  - row count, and the keys on both sides;
  - the schema, apart from the columns the rebuild drops on purpose (map §2 lists the read ones);
  - values, with floats within 1e-9 relative;
  - ranks exactly as predicted: equal on untied rows, and on tied rows the lowest old rank in the
    tie group. `rank_percentile` is recomputed from the predicted rank and must equal the new one.
    The 3,611 changed ranks (§2) are therefore expected, not differences to explain.
- **Done when:** every served dataset matches, or each difference is explained and approved.

### M5 — switch the webapp *(DSS: deploy)*

- Point the backend at the new datasets by the M0 method.
  - `calibration.py` and `families.py` read `disease` and `rank_enrichment` from
    `validation_auc_by_disease` instead of `persona_enrichment`.
  - `candidates.py` and `prefill.py` sort by `rank_in_disease`, then `gene_name`.
- Run locally against live DSS and compare every API response with the old one, field by field.
- Re-run M4's comparison immediately before the switch.
- The user runs `make deploy`; Claude verifies read-only.
- **Done when:** every route returns the same payload as before, apart from the predicted tied ranks
  and their percentiles, and the pages look the same.

### M6 — retire and tidy *(DSS)*

- **After a grace period agreed with the user,** delete the old chains M4 replaced: the 8–9 recipes
  and datasets of map §4.2, plus the old copies of the rebuilt ones.
  - This includes the serving copies of `novel_discovery_eval`, `persona_candidates`,
    `persona_enrichment` and `validation_auc_ci`. Their evidence-project copies stay.
- **Re-zone zone 20** into its three zones, moves only.
- **Rewrite `Refresh_serving_layer`** around the final zones, S1 included. Do not run it.
- **Rewrite every zone `shortDesc`** with `dku flow set-zone --short-desc`, which the CLI now
  supports (map §6.3).
- **Teach the index and flow-map tools the second project**, then regenerate `FLOW_MAP.md` and
  `.index/`.
- **Done when:**
  - the main project's map has no notebook reader and no orphan outside the keep list;
  - the webapp reads only S1–S4 plus the named exceptions;
  - `tools/check_indexes.sh` passes for both projects.

## 4. Risks

- **A notebook recompute that disagrees with the served value.** That is the separation working: the
  notebook becomes an independent check. Each disagreement found in M2 is investigated, not patched.
- **Assertions no longer run on a schedule.** With the scenario dropped, a change to the serving flow
  can move a number the docs quote until the next local run. M2's baseline and the wrapper make that
  run one command.
- **A local run depends on one machine's setup.** The wrapper pins the environment, so a run elsewhere
  reproduces it.
- **Two copies of the same logic drift.** `compute_demo_panel_config` and `compute_split_audit_2`
  live in both projects. The identity check asserts both copies match one mirror.
- **Fingerprints and identity checks assume one project.** M0 changes them before M2 moves anything.
- **A scenario names a deleted dataset.** M2 edits `Refresh_serving_layer` before deleting anything.
- **Repository checks fail after a move.** `push_descriptions.py --check`, `check_governed_values.py`
  and `push_assertions.py --check` each name objects that M2 moves or retires. M2 changes them in the
  same step.
- **Tied ranks read as a regression.** Ranking with ties changes 3,611 ranks and 2,155 percentiles
  once, all on tied rows. M4 predicts each one exactly, and after that the rank no longer depends on
  row order.
- **Zone 20 rebuilt by accident.** A recursive build from a downstream zone can reach it, so M4
  builds only within the new chains.
- **Two copies drifting during M4–M5.** The comparison runs again immediately before the switch.

## 5. Documents

| document | change |
|---|---|
| `ADR-001` successor, [`../decisions/DECISION_REGISTER.md`](../decisions/DECISION_REGISTER.md) | M0: the third project; build governance and identity recipes; D14/D15 amendments; `DEC-ARCH-001`'s sync count |
| [`../overview/PROJECT_CONTEXT.md`](../overview/PROJECT_CONTEXT.md) | §4.3: the objects the evidence project reads from the main project |
| [`BUILD_GOVERNANCE.md`](BUILD_GOVERNANCE.md) | the governed target moves to the evidence project; the pilot stays as history |
| [`../../notebooks/README.md`](../../notebooks/README.md) | M2: the scripts run locally against the evidence project (the wrapper, the environment, the revised reads); the library copy and the scenario retired; the zone-90 section removed |
| [`WEBAPP_DESIGN.md`](../demo/WEBAPP_DESIGN.md) | M5: shortlist ranks share a value when scores tie |
| [`WEBAPP_DATASET_MAP.md`](WEBAPP_DATASET_MAP.md) | re-measured in M1; retired with this plan once M6 is accepted |
| [`FLOW_MAP.md`](FLOW_MAP.md), `.index/` | regenerated after M2, M3 and M6 |
| agent instructions (`harness/`) | the project map gains the third project; `tools/sync_harness.py --write` |
