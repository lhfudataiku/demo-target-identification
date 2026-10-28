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
| **full (chosen)** | M0–M6 | 47 → 41 after M2 → 32–33 after M6 | notebooks independent of every serving zone; the serving flow organised by function, carrying only what the webapp reads; one scoring run; ranks with ties |
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
- **The notebooks also read 11 objects in zones 00–31 directly:** `scored_champion` (in six of the
  scripts), `graph_nodes`, `graph_edges`, `drug_protein_edges`, `drug_disease_edges`,
  `raw_ot_known_drug`, `raw_disease_disease`, `enriched_gene_druggability_v2`,
  `enriched_gene_safety_v2`, `enriched_graph_features_candidate_psplit` and `psplit_train_set`.
- **The recipes the evidence project takes on need about 7 more:** the other two split tables, two
  DWPC feature datasets, `gene_names`, `gene_crosswalk` and `disease_family_id`. M1 confirms the
  list.

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

**Zone 20 does three unrelated jobs:**

| job | datasets |
|---|---|
| drug annotation | `ot_drug_mapped`, `drug_joined`, `drug_classified`, `drug_evidence_pairs` |
| gene annotation | `gene_crosswalk`, `enriched_gene_druggability_v2`, `enriched_gene_localization`, `gene_safety_joined`, `enriched_gene_safety_v2` |
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

- **A successor ADR to `ADR-001` for the third project.** It records:
  - what the project owns: the notebook-only recipes and the evidence copies;
  - that it reads only exposed objects from the main project's zones 00–31;
  - that no build crosses the boundary, and nothing in the main project reads it;
  - its key and name, an open item since D13;
  - the correction to `DEC-ARCH-001`'s sync count.
- **How the notebooks run (decided 2026-10-28: locally).** They run from the repository through
  `runner.run()`, with the dataiku client set to the evidence project as the default project. This
  needs:
  - a wrapper under `tools/` and a local environment (Python 3.13 to match DSS, the dataiku client,
    `pandas`, `numpy`, `matplotlib`, `seaborn`, `IPython`);
  - and it retires the DSS library copy: `/python/nb_assertions/`, `push_assertions.py` and its
    drift check in `check_indexes.sh`.

  Nothing runs on a schedule. Assertions run when evidence work or a validation calls for it.
- **How the evidence project and the notebooks read upstream objects.**
  - *Recommended now that the notebooks may be revised:* the evidence project's recipes take the
    exposed main-project objects directly as inputs, as the main project already does with
    `DEMO_KG_LS`'s. The notebooks read zone 00–31 objects by project-qualified name
    (`DEMO_TARGET_IDENTIFICATION.scored_champion`), and evidence datasets by bare name. There are no
    copies, and the notebooks always see the current model.
  - *Alternative:* local sync copies in the evidence project, as Part 2 keeps of Part 1's. This
    freezes a snapshot for validation work and leaves the notebooks' names unchanged, at about 1.15 GB
    for `scored_champion`, the three split tables and `enriched_graph_features_candidate_psplit`.
- **Build governance (`DEC-OPS-005`).** `breast_panel_metrics` becomes the evidence project's governed
  target, under a new key in `allowed_targets`. The stale `breast_panel_overlap` entry goes. The
  2026-08-31 pilot artifacts stay as history of the main-project recipe.
- **Identity recipes (`DEC-OPS-006`).**
  - `compute_breast_panel` moves, so the check learns the evidence project.
  - `compute_demo_panel_config` and `compute_split_audit_2` will exist in both projects. The check
    should assert that both copies match the one `dss_recipes/` mirror.
  - Under the rebuild, the serving copy of `compute_demo_panel_config` reads its disease names from
    `validation_auc_by_disease` instead of `persona_enrichment`. Decide whether the evidence copy
    changes with it, so that the two copies stay identical.
- **D14 and D15 amendments.**
  - D14 names its metadata exceptions: the zone-10 metrics, the saved model and the Kuzu folder.
  - D15 places `family_panel` and `demo_panel_config` with the zone-40 core, as the panel definition
    both pages use.
  - Under the rebuild, the `dashboard_candidates` chain moves into S1 beside the scoring run it reads,
    and zone 40 keeps only the panel definition and `validation_set_personas_2`.
- **The shortlist ranks with ties (decided 2026-10-28).**
  - Tied scores share the lowest rank of their group, and the next rank skips (1, 2, 2, 4). This is
    the window recipe's *rank*, which the per-disease AUC window already uses.
  - It applies to the serving shortlist (M4) and the evidence-side shortlist (M2) alike, and to
    `nb6`'s own recompute, which numbers rows 1..n today.
  - The backend sorts tied rows by `gene_name`, so the table's order within a tie is stable.
  - Record it in the register, with the measured effect in §2.
- **The rebuild's switch method:** repoint the backend's constants to suffixed names, or delete the old
  datasets and rename the new ones to the old names. Check rename behaviour on one small managed
  dataset first.
- **Done when:** the user approves the ADR and register diff.

### M1 — inventory and mapping (read-only)

- Refresh the snapshot and the map: `python3 tools/build_recipe_index.py --refresh`, then
  `python3 tools/build_flow_map.py`.
- **For each notebook read** in §2, decide how the evidence project provides it from zones 00–31:
  - a recipe moved from the main project;
  - a recipe copied from the main project;
  - recomputed in notebook code, where that is lighter;
  - a synced copy of an exposed object.
  It is never a read of a serving zone.
- **For each notebook script**, list the revisions M2 makes:
  - which reads become project-qualified and which point at evidence datasets;
  - `nb6`'s rank recompute changed to ranking with ties;
  - anything that assumed the DSS library or the scenario.
- **`compute_filter_three_axes`** gets its ranked shortlist from the evidence side: `scored_champion`
  restricted to the 12 shortlist diseases, ranked with ties. Before relying on it, check
  that `scored_champion.proba_1` equals the served `score` on all 105,702 pairs. The two shortlist
  scoring runs agree with each other, but this third comparison has not been made.
- **The serving flow:** start from [`WEBAPP_DATASET_MAP.md`](WEBAPP_DATASET_MAP.md) §2–4.
  - Map every dataset after zone 31 to its zone under M3 and its fate under M4.
  - Confirm that one window recipe can give both the ordered rank and a whole-partition count. That
    decides 32 or 33 recipes.
  - Confirm that each rebuilt dataset carries every field in map §2.
- **Zone 20:** confirm the three-job split and that every recipe moves without a rebuild.
- **Done when:** the user approves one table: every dataset, its readers today and after, and its
  project, zone or fate.

### M2 — the evidence project *(DSS)*

- **Set up the local run first.** Add the wrapper and the local environment (M0).
- **Take a baseline.** Run every notebook script locally against the main project, unchanged, and
  record each script's check count and stale count. The scenario has not run since 2026-09-03, so
  this is the reference M2 is accepted against.
- **Create the project.** Expose the zone 00–31 objects M1 listed. Use them directly as recipe
  inputs, or sync them in if M0 chose copies. New datasets use managed storage and Parquet, and joins
  are visual Join recipes.
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

  This is an estimated 20–25 recipes, plus one sync per upstream object if M0 chose copies.
- **Revise the notebooks** as M1 listed. The revision changes where a script reads and how `nb6`
  ranks; it never changes an assertion's expected value. A value that moves is investigated (§4).
- **Point the tooling at the evidence project:** the runner wrapper, `POLICY.json` and
  `IDENTITY_RECIPES` as M0 decided. Retire `push_assertions.py` and its call in `check_indexes.sh`.
- **Main-project changes:**
  - edit `Refresh_serving_layer` to drop `shap_drivers_long` and `shap_driver_frequency`;
  - then delete those two recipes and datasets;
  - delete the `validate_notebooks` scenario and the `/python/nb_assertions/` library folder;
  - after acceptance, delete the four moved originals.
- **Repository changes:** `_dead.json` loses its keep entry; `dataset_descriptions.json` drops the
  entries for the moved datasets, or `push_descriptions.py` learns the second project;
  `notebooks/README.md` is rewritten.
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
- **Rewrite every zone `shortDesc`.** There is no CLI verb, so it needs a scenario using the Python
  API, run by the user.
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
