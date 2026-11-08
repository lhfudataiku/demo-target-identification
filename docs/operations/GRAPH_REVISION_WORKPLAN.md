# Graph revision — workplan

> **Lifecycle:** Active plan · **Audience:** Part 1 builders, DSS flow maintainers and Part 2
> reviewers · **Authority:** the sequence, method and acceptance checks for revising the knowledge
> graph: moving data loading into its own project, correcting two wrong relations, making edge labels
> readable, and rebuilding from current sources · **Update when:** a decision is taken, a step is
> accepted or re-scoped, or a fact in §2 is superseded · **Generated dependencies:** none ·
> **Excludes:** the graph method itself, in [`GRAPH_BUILDING.md`](../graph/GRAPH_BUILDING.md); Part 2
> modelling method, in [`TARGET_PRIORITIZER.md`](../prioritizer/TARGET_PRIORITIZER.md).

**Status: IN PROGRESS — R1 revised 2026-11-06 (D7 changed); R1 step 1 (revert) done; next is R1 step 2.**
`DEMO_KG_LS` is untouched. The repository
holds the drafted code for steps R2 and R3 (`dss_recipes/attach_node_index.py`,
`dss_recipes/compute_go_terms.py`), not yet pushed. Every DSS
change and every build below needs explicit approval at the step where it happens.

## 1. What changes, and why

| # | Change | Why |
|---|---|---|
| 1 | **Data loading moves to a new project, `DEMO_KG_PREP`.** Its datasets are shared to `DEMO_KG_LS` and copied in with sync recipes. | Separates "fetch the public sources" from "build the graph", so a source refresh is a deliberate, visible act. |
| 2 | **Phenotype annotations leave `disease_disease`.** A disease→phenotype annotation whose phenotype term is also a disease gets its own relation, `disease_phenotype_disease`. Negated (`NOT`) annotations on such terms are dropped. | Today 23,623 of 64,803 `disease_disease` links (36%) are these annotations, labelled `parent-child`; 91 source rows are "does NOT have" annotations stored as positive links. |
| 3 | **Negated GO annotations are dropped** in `compute_go_terms`. | gene2go's qualifier column is ignored today, so "gene X does NOT enable Y" becomes an `enables` edge. |
| 4 | **`display_relation` becomes readable** at final assembly (`attach_node_index`). `relation` is not touched. | The Explorer shows codes such as `PHASE_1_2`, and one label, "associated with", covers germline, somatic and phenotype-derived gene–disease links. |
| 5 | **Rebuild from current sources.** | Change 3 needs a fresh gene2go; the project move is the natural point to refresh. |

**Not changing:** edges stay stored in both directions (one-way storage would change 5 of the 14
champion features and lose PrimeKG parity). The 27,713 phenotype-derived `disease_protein` links stay
in the training labels; R7 checks how much they flatter the results instead.

## 2. Starting point (measured 2026-11-06)

**Graph:** 113,391 nodes, 2,851,510 directed edge rows, 18 relations, built 2026-08-14 (R2 on 2026-11-08: 2,851,872 rows, 19 relations, snapshot `ZKGaRg`; `Mp25kL` kept as the reference).

**Flow zones in `DEMO_KG_LS`.** Four zones load data; three harmonise; two assemble and publish.

| Zone | Kind | Contents |
|---|---|---|
| Gene & interactome (HGNC, PPI) | loading | HGNC, gene names, HuRI, STRING; Menche input folder `nIhuvFJm` |
| Drugs & gene-disease (Open Targets) | loading | OT association, maps, drugs, druggability, safety, known drugs |
| Disease & phenotypes (MONDO, HPO) | loading | MONDO, HPO, disease grouping map; snapshot folder `kFQAspRA` |
| Function & pathways (GO, Reactome) | **mixed** | GO and Reactome extraction **plus** four harmonise recipes |
| 3 × … harmonisation | harmonise | per-domain grounding into edge tables |
| Graph build · Graph Snapshots | assemble / publish | stack, `compute_kg_edges`, node index, Kuzu build `Mp25kL` |

**What moves (proposal D6):** 16 recipes and their 28 outputs, and both folders. That is the 15
recipes in the loading zones plus `extract_ppi` (the Menche extract, which sits in a harmonisation
zone today) and its output `raw_menche_ppi`.

- Recipes: `extract_mondo`, `extract_hpo`, `compute_disease_group_map`, `compute_go_terms`,
  `extract_reactome`, `compute_hgnc_identity`, `compute_gene_names`, `extract_huri`,
  `extract_string`, `extract_ppi`, `extract_ot_assoc`, `extract_ot_maps`, `extract_drug_ot`,
  `compute_raw_ot_druggability`, `compute_raw_ot_safety`, `compute_raw_ot_known_drug`.
- 24 of the outputs are read by recipes that stay in `DEMO_KG_LS` and need a sync copy there.
- 4 (`hgnc_identity`, `raw_ot_druggability`, `raw_ot_safety`, `raw_ot_known_drug`) are read only by
  Part 2, which already copies them from `DEMO_KG_LS`.
- No recipe left in `DEMO_KG_LS` reads either folder, so **no folder needs replicating** (a sync
  recipe cannot copy a folder; a merge-folder recipe would, if one is wanted for traceability).

**Source versions.** Rebuilding pulls whatever each URL serves today.

| Pinned (same data on rebuild) | Not pinned (new release on rebuild) |
|---|---|
| Open Targets 26.06, STRING v12.0, Menche (uploaded file), disease grouping map (snapshot folder) | MONDO, HPO, GO `go-basic.obo` + NCBI gene2go (rewritten daily), Reactome (`current`), HuRI (no version in URL) |

**Consequence: `node_index` will be renumbered.** It is assigned over a sort that puts
`biological_process` first, so any new or retired GO term shifts almost every number.

**What depends on `node_index` as a number:**
- **Evaluation split.** `split_by_disease_key` assigns train/validation/test by
  `mod(disease_split_key, 10)` and five hard-coded indices (46033, 45109, 47437, 47654, 45876).
  Renumbering moves every disease to an arbitrary fold. This is the case `DEC-OPS-001` covers.
- **Name-based, safe:** personas and the demo panel resolve names to indices (`DEC-OPS-006`); the
  WATCH lists use names.

**Part 2 cross-project reads (unchanged by this plan if D8 is approved):** 13 sync recipes in
`DEMO_TARGET_IDENTIFICATION` read `DEMO_KG_LS.<name>`, and `compute_ytvuniN8` merges the Kuzu folder.

## 3. Decisions

| ID | Decision | Status |
|---|---|---|
| D1 | Option A for the reclassified disease–phenotype links: new relation, `NOT` rows dropped | taken 2026-11-06 |
| D2 | Drop negated GO annotations | taken 2026-11-06 |
| D3 | Keep two-way edge storage | taken 2026-11-06 |
| D4 | Rebuild from source | taken 2026-11-06 |
| D5 | Data loading moves to `DEMO_KG_PREP`, shared and synced into `DEMO_KG_LS` | taken 2026-11-06 |
| D6 | **Boundary:** `DEMO_KG_PREP` holds the download and vocabulary recipes, including `extract_ppi`; every harmonise recipe stays in `DEMO_KG_LS`. The four GO/Reactome harmonise recipes move to a new "Function & pathways harmonisation" zone. | taken 2026-11-06 |
| D7 | **Key the evaluation split on the MONDO id of the split key**, not `node_index`, and reserve the demo families by MONDO id. The split changes once; the champion is retrained on it before R2. *(Replaces 2026-11-06 "freeze today's folds", built and reverted the same day.)* | taken 2026-11-06 |
| D8 | **Part 2 keeps reading `DEMO_KG_LS`, not `DEMO_KG_PREP`.** The LS copies keep their current names, so Part 2's 13 sync recipes need no change, and Part 2's raw data always comes from the same pull as the graph. | taken 2026-11-06 |
| D9 | **Pin every source at this pull:** each unpinned download is saved once to a `raw_files` folder in `DEMO_KG_PREP` and read from there afterwards. | taken 2026-11-06 |
| D10 | **Two-stage rebuild** (R2, then R5) so the effect of the relation fixes is measured apart from source drift. | taken 2026-11-06 |
| — | New relation name `disease_phenotype_disease`; label wording in [`GRAPH_BUILDING.md`](../graph/GRAPH_BUILDING.md) §4.4 | taken with D1 |
| D11 | **Trim the family columns that flow downstream** (§6.1). Keep `disease_index`, `disease_family_id`, `anchor_name`, `hop_depth`, `disease_split_key_mondo` and `split_key_name`. Retire `disease_split_key` after its three live readers move to the MONDO key. Keep `split_key_rule` in `disease_family_id` only, as the audit trail. Done in the R6 rebuild, since it changes schemas down to `scored_champion`. | proposed 2026-11-07 |
| D12 | **Calibrate inside the model, not in a separate recipe** (§6.2): train a new version of the champion with the training recipe's built-in **sigmoid (Platt)** calibration, fitted on the test fold (`calibrateOnTestSet`). Rank and percentile stay the primary display; the calibrated score may be shown as "chance of being a known association" next to the disease's base rate, never as the probability of being a target. *(Revised 2026-11-07 from "post-processing recipe".)* | taken 2026-11-07 (built as a new Lab-trained model, R7b) |

## 4. Steps

Each step lists who acts. "DSS" steps change the live projects and run only after approval.

### R0 — decisions *(user)* — done 2026-11-06
D6–D10 approved as proposed.

### R1 — split by MONDO id, re-baseline on today's graph *(DSS in `DEMO_TARGET_IDENTIFICATION`)*

**Revised 2026-11-06.** The first R1, built the same day, froze today's folds in a lookup table and
replaced the split recipe with three Joins. It worked (identical split sets), but it added machinery
to preserve a split nobody needs to preserve. It is being reverted: the project is restored to
revision `228880260b` (2026-11-04, the last commit before R1) from the DSS version history. That also
removes the `baseline_2026_11_*` snapshots it took.

**How the split works today** (live, 2026-11-06):
- `compute_disease_family_id` gives each disease a `disease_split_key`: the nearest member of an
  elevated key set above it in the MONDO hierarchy, or the disease itself when no key is reachable.
- `split_by_disease_key` sets `split_role` from that key's `node_index`: `mod(key, 10)` 0–4 →
  validation, 5 → test, 6–9 → train, plus five hard-coded keys forced to validation.
- Index order also decides three tie-breaks in `compute_disease_family_id`: `lift_key`,
  `nearest_split_key` and `nearest_anchor` pick the lowest `node_index`. A renumbering has already
  flipped one of these once (lung moved from `respiratory system cancer` to `thoracic cancer`; see
  the note in `compute_lung_granularity_check`).

**Design: key the split on the MONDO id, which the source owns and does not reuse.**
- `compute_disease_family_id` adds `disease_split_key_mondo`, the split key's MONDO id (the first id
  of a grouped node), and breaks every tie by MONDO id. `disease_family_id` and `disease_split_key`
  stay `node_index` values, because the demo panel config, the hierarchy annotation, the per-key AUC
  and the webapp resolve them through `graph_nodes`; changing their meaning would fail silently.
- The split formula routes on `disease_split_key_mondo` and reserves the demo families by MONDO id:
  `if(arrayContains([3274, 5300, 5015, 3916, 21085, 2715, 376], disease_split_key_mondo), "validation",
  if(arrayContains([0,1,2,3,4], mod(disease_split_key_mondo, 10)), "validation",
  if(mod(disease_split_key_mondo, 10) == 5, "test", "train")))`.

| Reserved split key | MONDO id | Demo diseases | Fold by MONDO id alone |
|---|--:|---|---|
| thoracic cancer | 3274 | breast and lung panels | validation |
| chronic kidney disease | 5300 | CKD | validation |
| diabetes mellitus | 5015 | diabetes, type 2 diabetes | test |
| overnutrition | 3916 | obesity | train |
| gastric neoplasm | 21085 | gastric panel | test |
| uterine cancer | 2715 | uterine / endometrial panel | test |
| respiratory system cancer | 376 | already reserved today | train |

**Expected effect** (simulated on today's split keys, before the tie-break change):
- 1,157 modelling-table diseases split 600 validation / 426 train / 131 test, against 670 / 383 / 104
  today; 521 keep their fold.
- All 32 demo-panel diseases in the modelling table land in validation.
- **The split is new, so the champion must be retrained before any number is quoted.** 181 of
  today's training diseases move into validation. Every documented Part 2 number belongs to the old
  split and becomes historical.

**Steps:**
1. Revert `DEMO_TARGET_IDENTIFICATION` to revision `228880260b` *(user, DSS UI)*. **Done 2026-11-06:**
   revert commit `1ed1c815`; `dku git diff` against `228880260b` shows zero changed files; the split
   sets still hold their pre-R1 data (verified by full-content hash before the revert).
2. Push `dss_recipes/compute_disease_family_id.py`. Add `disease_split_key_mondo` to the selected
   columns of `join_disease_family_id`. Replace the formula in `split_by_disease_key`.
3. In the champion's ML design, set `disease_split_key_mondo` to **reject**, so it can never become a
   feature. Propagate the new column's schema through `filter_has_path_evidence`, the split sets,
   `score_psplit_validation_m7` and `sync_scored_champion`.
4. Build the family recipe's inputs, which hold no data in this project today: `mondo_references`
   and `raw_disease_disease` (sync copies from `DEMO_KG_LS`) and `hetionet_disease_slim` (downloads
   the Hetionet node file from GitHub).
5. Rebuild non-recursively: `disease_family_id`, `enriched_graph_features_1_family`,
   `enriched_graph_features_candidate_psplit`, the three split sets, `split_audit_2`.
6. Retrain `train_m7-f14` on the new split, rescore validation, and recompute the per-disease AUC.
   Re-run the notebooks and retarget the documented numbers (the skill's number-update procedure).
   **This is the new baseline that R2–R6 are compared against.**
7. **Accept when:**
   - `split_audit_2` reports zero straddling split keys;
   - every demo-panel disease is in validation;
   - the webapp shows the demo panel;
   - no fold is empty of positives.

**Progress — steps 2–5 done 2026-11-06** (step 6, retrain and rescore, waits for approval because it
changes what the webapp shows):
- Pushed the family recipe, the join column and the split formula. `train_m7-f14` sets
  `disease_split_key_mondo` to `REJECT`; the model still has exactly the champion's 14 inputs.
- A recursive build recomputed every feature recipe from today's graph (about 15 min). The fused
  Spark stage (`compute_enriched_pair_features_index_1` + `compute_enriched_graph_features_1`) failed
  with "SparkContext was shut down"; built as two separate jobs it succeeded.
- `disease_family_id`: 6,821 diseases, no two split keys share a MONDO number. The MONDO-id
  tie-break changed the split key of 61 of the 1,157 modelling-table diseases and the family of 5;
  the largest move is 15 lung diseases from `thoracic cancer` back to `respiratory system cancer`
  (both reserved for validation).
- Schema propagated only through the modelling chain (stopped before training, scoring, the persona
  filter and the audit), so `scored_m7` / `scored_champion` are untouched.
- The modelling table has 6,754,128 rows, as in September.
- `split_audit_2`: validation 607 diseases / 3,568,682 rows / 65,929 positives; train 420 / 2,371,922 /
  44,611; test 130 / 813,524 / 16,923. Zero straddling split keys, zero key overlap between folds.
- All 32 demo-panel diseases in the modelling table are in validation.

**Progress — step 6 (retrain and rescore) done 2026-11-06/07:**
- `train_m7-f14` could not retrain: its split policy is "explicit two datasets" (train
  `psplit_train_set`, test `psplit_test_set`), but only the training set was wired as an input, a
  pre-existing fault. `psplit_test_set` was added with role `test`; training then succeeded.
- Saved model `hJLGoYn4`: new active version `1794002440246`, same 14 inputs; the September version
  `initial` is kept (`dku model set-active-version` restores it). DSS's pooled test-fold AUC is 0.907;
  it is not the project metric.
- `scored_m7` and `scored_champion` rescored; one RECURSIVE_BUILD job rebuilt the 30 downstream
  recipes (41 activities, 24 min), including `dashboard_candidates`, the family panels,
  `candidate_shap_top5`, `hub_bias_meter`, `orthogonality_scatter` and `validation_auc_by_disease`.

**New baseline (macro per-disease AUC on validation):**
- September model on the old split: 0.8230 over 670 diseases (reproduces the documented headline).
- Retrained model on the new split: **0.8162 over 607 diseases**; trustworthy-only 0.8359 over 333
  (September: 0.8359 over 378).
- On the 382 diseases in validation under both splits: 18 ties (|Δ| < 0.001), new higher on 231, old
  higher on 132; mean Δ +0.0043, median +0.0040; Wilcoxon signed-rank on non-ties p = 1.7e-6. This
  is not a model comparison: the training sets differ (new split, rebuilt features), so it measures
  how stable per-disease results are across the change, not which model is better.
- All 32 demo-panel diseases are scored in validation (type 1 diabetes is newly scored). HER2-positive
  breast carcinoma: AUC 0.938 (was 0.936), 19 of the top 20 are targets (unchanged).

**Not yet done:** re-run the notebooks and retarget the documented Part 2 numbers (the skill's
number-update procedure). Until then, documents quote the September split's numbers.

**Also done in the repository (2026-11-06):** `notebooks/nb6_interrogation_and_close.py` resolves the
HER2 spine disease and the lung family by name instead of the hard-coded indices 48537 and 52236.
`compute_lung_granularity_check` and `compute_drug_target_benchmark_staged`, which also hard-code
indices, are mirrors of recipes no longer in DSS and need no change.

### R2 — stage A: relation and label fixes on today's data *(DSS in `DEMO_KG_LS`)*
1. `harmonize_disease_phenotype`, three step edits:
   - step 6 `relation`: `if(isNonBlank(mondo_id_min), "disease_phenotype_disease", if(qualifier=="NOT", "disease_phenotype_negative", "disease_phenotype_positive"))`
   - step 7 `display_relation`: `"phenotype annotation (disease term)"` in place of `"parent-child"`
   - a new first step removing rows where `isNonBlank(mondo_id_min) && qualifier == "NOT"`
2. Push the drafted `attach_node_index.py` (readable labels).
3. Add an edge group to graph build `Mp25kL`:
   - disease → disease, read from `graph_edges`, filter `relation matches "disease_phenotype_disease"`;
   - modelled on the `disease_disease` group.
4. Rebuild from `harmonize_disease_phenotype` down (propagate schema first; one job), then the Kuzu
   graph, then `compute_ytvuniN8` in Part 2.
5. **Accept when:**
   - nodes 113,391 with identical `node_index`;
   - `disease_disease` about 82,360 directed rows and `disease_phenotype_disease` about 47,000;
   - every other relation's count unchanged;
   - 0 duplicates, 0 self-loops, every edge has its reverse.
   - Part 2: the 14 champion features are unchanged; only `disease_context` (not in the champion)
     moves.

**Done 2026-11-08.**
- **Step 1.** `harmonize_disease_phenotype` now has 11 steps. The new step 0 is
  `FilterOnCustomFormula` `isNonBlank(mondo_id_min) && qualifier == "NOT"` → remove. Steps 7 and 8
  carry the new `relation` and `display_relation` formulas.
- **Step 2.** `attach_node_index.py` pushed; DSS matches the repository.
- **Step 3: edge group, as a new snapshot.** Visual Graph keeps its saved configurations as JSON
  rows in `vg_saved_config_ds`; `dku` has no verb to edit one, so temporary scenarios with a Python
  step did it and were deleted.
  - **Rule (user, 2026-11-08): any change to the graph gets a new snapshot; earlier snapshots are
    kept as references.** The first attempt edited `Mp25kL` in place and overwrote its built graph.
    It was reverted the same day (below).
  - **Current R2 snapshot: `ZKGaRg` (`kg_ls_v0-2`)**, saved by the user from the Visual Graph editor.
    Its build recipe is `build-graph-ZKGaRg` and its folder `ouzaULiq` (`kg_ls_v0-2-ZKGaRg`), shared
    with `DEMO_TARGET_IDENTIFICATION`. Use the editor to save snapshots: rows written through the API
    do not appear in the editor's history.
  - `R2dpDs` (`kg_ls_r2`) was an equivalent snapshot made through the API: the same nodes, edge
    groups, filters and queries; only ids, the new group's colour, `graph_name` and the comment
    differed. It was deleted the same day: its saved row, `build-graph-R2dpDs`, folder `W5tPPGi2`
    and the folder's share. `dku folder delete` leaves the files on disk, so about 159 MB remain
    under `filesystem_managed` at `/DEMO_KG_LS/W5tPPGi2`.
  - **`Mp25kL` restored as the pre-R2 reference.** Its saved row is byte-identical to the pre-R2
    backup. Its graph in `UBUlwwxT` (18 groups) was rebuilt from pre-R2 `graph_edges` /
    `graph_nodes`, regenerated by temporarily restoring the pre-R2 recipe versions; both tables
    matched the pre-R2 download row for row. R2 was then re-applied, and the tables matched the
    accepted R2 build row for row.
- **Step 4: rebuild.** The chain was rebuilt from `harmonize_disease_phenotype` to `graph_edges`, then
  the snapshot builds (19 edge groups in each built `configuration.json`).
  - `compute_ytvuniN8` now reads `DEMO_KG_LS.ouzaULiq` (it read `UBUlwwxT` before R2), so Part 2's
    `ytvuniN8` holds only `/built-graphs/ZKGaRg/`.
  - The Part 2 Cypher recipes read the folder and name no snapshot. Whether they find a database
    under a new snapshot id is first exercised in R6.
  - ⚠ **A multi-target `NON_RECURSIVE_FORCED_BUILD` job does not order its activities.** All seven
    recipes started together and failed when their inputs were not ready. The live outputs were
    untouched.
  - What worked was one job per recipe, in order. A recursive build was avoided because it could
    re-pull unpinned sources, the drift that D10 keeps out of R2.
- **Acceptance**, measured on `graph_edges` / `graph_nodes` against the pre-R2 download:
  - nodes 113,391, identical `node_id`, name and `node_index`;
  - `disease_disease` **82,360** (was 129,606); `disease_phenotype_disease` **47,608**;
  - every other relation identical, by count and by pair set; total 2,851,872 (+362);
  - 0 full-row duplicates, 0 self-loops, every edge has its reverse.
  - The +362 rows: 498 directed pairs are both a MONDO link and a phenotype annotation, and now
    appear once in each relation. 136 directed pairs disappeared; all of them are `NOT` annotations.
  - The 862 duplicate `(relation, x, y)` triples are older than R2. They are drug–disease and
    drug–target pairs carrying two stages or action types; the same 862 existed before.
- **Part 2 acceptance, by construction, not by rebuild.**
  - The only Part 2 reader of the graph's `disease_disease` is
    `compute_enriched_disease_context_1`. `compute_disease_family_id`,
    `compute_disease_hierarchy_annotation` and `compute_gene_localization` read
    `raw_disease_disease`, which R2 does not touch.
  - Every Part 2 Cypher pattern names its relationship type, so the new rel table cannot enter an
    existing feature.
  - Part 2 features were not recomputed; R6 rebuilds them.
- **Not yet checked:** how the Explorer captions the new relation and labels (Risk table, §5). The
  Explorer (`wBcApLN`) still serves the `Mp25kL` reference graph.
- **R5 follows the same rule:** the fresh-pull rebuild gets its own snapshot, folder and build recipe,
  and `compute_ytvuniN8` is repointed to it.

### R3 — build `DEMO_KG_PREP` beside the current flow *(DSS)*
1. Create the project. Create zones per domain: genes & interactome, Open Targets, disease &
   phenotype, function & pathways.
2. Recreate the 16 recipes (code copied from `DEMO_KG_LS`), outputs on `dataiku-managed-storage` /
   Parquet. Copy folders `nIhuvFJm` and `kFQAspRA`.
3. Apply D9 (pin-on-first-pull) to the five unpinned extracts, and the drafted GO `NOT` filter to
   `compute_go_terms`.
4. Build `DEMO_KG_PREP`. This is the fresh pull.
5. Share the 28 outputs with `DEMO_KG_LS`. Update
   `docs/operations/build-governance/POLICY.json` if it should know the new project.
6. **Accept when:** the pinned sources reproduce today's row counts exactly (Open Targets, STRING,
   Menche, disease grouping). Unpinned sources differ, and each difference is recorded with its new
   release version.

### R4 — switch `DEMO_KG_LS` to the copies *(DSS)*
1. For each moved output, delete the producing recipe in `DEMO_KG_LS` and add a sync recipe
   `DEMO_KG_PREP.<name>` → `<name>`, same dataset name, Parquet. Name it
   `compute_DEMO_KG_PREP_<name>_copy`, following Part 2's convention.
2. Put each copy in its domain's harmonisation zone. Move the four GO/Reactome harmonise recipes to
   a new "Function & pathways harmonisation" zone, then delete the emptied loading zones.
3. **Accept when:** the flow check is clean; every `DEMO_KG_LS` recipe input resolves; Part 2's 13
   sync recipes still resolve with no edits.

### R5 — stage B: full rebuild from the fresh pull *(DSS)*
1. Sync the copies, then rebuild `DEMO_KG_LS` end to end (propagate schema first; one job), the Kuzu
   graph and Explorer, and `compute_ytvuniN8`.
2. **Accept when:**
   - integrity checks pass;
   - the GO `NOT` count dropped is logged;
   - every relation count change is explained by a source release or by D1–D2;
   - an old→new `node_index` map exists for every surviving node, with lost and new nodes listed.

### R6 — Part 2 rebuild and re-evaluation *(DSS in Part 2)*
1. Rebuild the copies, features and split (MONDO-keyed since R1), and retrain the champion's configuration.
2. Compare with the new R1 baseline per disease: report ties first, then the stratified paired test,
   macro per-disease AUC (never pooled).
3. Attribute changes:
   - R2 changed no champion feature, so any shift comes from R5's source drift or the GO fix;
   - `dwpc_GBGD` and `dwpc_GFGD` are the features expected to move.
4. Check the drug-target benchmark as a warning, not a target.
5. *(D11, if approved)* Trim the family columns in the same rebuild:
   - move `compute_split_audit_2` (straddle check and key counts), `compute_drug_target_benchmark`
     and `nb3_validation_and_plots.py` (macro AUC per split key) from `disease_split_key` to
     `disease_split_key_mondo`;
   - remove `disease_split_key` and `split_key_rule` from the selected columns of
     `join_disease_family_id`, and propagate the schema;
   - check `train_m7-f14`'s feature handling still validates once the dropped columns disappear
     from its input (both are `REJECT` today), and that it still has exactly the 14 inputs;
   - accept when the audit still reports zero straddling keys and the webapp's family and shortlist
     pages still load.

### R7 — label sensitivity *(read-only)*
Re-score the champion's per-disease AUC on Open-Targets-only positives (excluding the 27,713
phenotype-derived `disease_protein` links), to see whether those links flatter the results.

### R7b — calibrated champion *(D12; DSS in Part 2 + webapp)*
1. In `train_m7-f14`, set calibration to **sigmoid** and keep `calibrateOnTestSet: true`. With the
   recipe's explicit two-dataset split, the calibrator is fitted on `psplit_test_set` (130 diseases,
   813,524 pairs, 16,923 positives); the base model is still trained on the full training fold.
   - Why the test fold: the alternative (`calibrateOnTestSet: false`) carves a calibration share out
     of training, which retrains the base model on less data and changes the ranking.
   - What it costs: the test fold is read only by `compute_split_audit_2` and DSS's own test metrics;
     after calibration DSS's test-fold calibration metrics are no longer clean, while every reported
     project metric comes from validation and stays clean.
   - Not isotonic: it creates ties in the top 20 (§6.2).
2. Retrain as a new saved-model version, rescore validation, sync `scored_champion`, rebuild the
   downstream tables. Record it in `tools/model_registry.json` as `m7-f14-cal`, "same ranker, calibrated
   output" *(superseded: see the outcome below)*.
3. No new recipe for the base rate: the per-disease positives and pool size already exist
   (`validation_auc_by_disease`: `n_pos`, `n_neg`; `disease_pool_sizes`).
4. Webapp: keep rank and percentile primary; show the calibrated score as "chance of being a known
   association" beside the disease's base rate (or as an enrichment over it), with a tooltip that
   negatives are unlabeled genes, so the value is a floor for novel candidates.
5. **Accept when:**
   - every disease's ranking and per-disease AUC are identical to the uncalibrated version (sigmoid is
     strictly monotone and the base model is unchanged);
   - calibration error on validation is ≤ 0.003. Expect calibrated values a little high on average:
     the test fold is 2.08% positive against validation's 1.85%;
   - SHAP top-5 drivers are rechecked: Shapley values are computed on the model's output, and a
     non-linear calibration can reorder close drivers;
   - the notebook assertions that read score values (not ranks) are re-run.

**Outcome (2026-11-07) — done, with one acceptance test failed and accepted by the user.**
- **Built differently from step 1, at the user's request ("better align with lab").** The Lab task
  was realigned (`prox_kernel` in, `prox_mean` and `disease_split_key_mondo` out, sigmoid calibration
  on the test fold) and trained as session `s13`; `s13-pp2-m1` was deployed as a **new saved model
  `W8VhjZOZ` (`m7-f14-cal`)** with recipe `train_m7-f14-cal` (main `psplit_train_set`, test
  `psplit_test_set`). Both scoring recipes repointed. `m7-f14` (`hJLGoYn4`) retired: recipe
  `train_m7-f14` deleted, the in-place calibrated version `1794045416472` deleted, and the saved
  model itself deleted later the same day at the user's request.
- **Calibration: met.** ECE on validation 0.254 → **0.0033** (target ≤ 0.003, accepted as within
  noise); mean calibrated 0.0189 against observed 0.0185; top 20 per disease predicted 25.8%, observed
  30.5% — slightly cautious at the head.
- **Identical ranking: failed.** Lab and flow train the same settings (features, seed 1337, split,
  sampling, GPU container) to different models: median within-disease Spearman 0.959 (min 0.54),
  top-20 overlap median 80%, 97% of the old top 20 still in the new top 50, same top SHAP driver 50%,
  same five drivers 13%. Likely GPU XGBoost non-determinism amplified by early stopping (not confirmed:
  tree counts unreadable through the connector). **Quality is equivalent**: per-disease AUC 318 higher /
  288 lower / 0 ties, macro 0.8170 vs 0.8162, Wilcoxon p = 0.27. The user accepted the model.
- **Score-reading assertions: re-run and retargeted.** 86 stale values across all seven notebooks;
  `nb3b`/`nb6` (and the repo copy of `compute_hub_bias_meter`) now read the model's own threshold from
  its `prediction` column — the hard-coded 0.860 matched no row on the calibrated scale. Hub bias grew:
  ρ(degree, probability) 0.3273 → 0.3500, detection swing 3.3× → 4.4×. Demo consequence: HER2+ ERBB2
  now ranks **#16** (was #14), outside the top-15 table.
- **Phase 3 P4** (`PHASE3_PREREGISTRATION.md`) commits to "spread > 0.1935" on the raw-score scale; the
  spread is no longer comparable on calibrated probabilities, so P4 must be judged on its ρ arm.
  The preregistration is left as written.
- **Closed the same day:** `compute_hub_bias_meter` pushed and `hub_bias_meter` rebuilt (12.7% →
  55.5% predicted positive at threshold 0.225); webapp redeployed for `CHAMPION_MODEL`; `hJLGoYn4`
  deleted.

### R8 — documents and close *(repository)*
1. Update `GRAPH_BUILDING.md`: §7 statistics, 19 relations, and the 2026-11-06 log entry, marked as
   built.
2. Regenerate `FLOW_MAP.md`.
3. Add `DEMO_KG_PREP` to the project map in `CLAUDE.md` / `AGENTS.md` and `PROJECT_CONTEXT.md`.
4. Retarget documented Part 2 numbers by the skill's number-update procedure.
5. Record D6–D12 in the decision register where the admission rule is met.
6. Regenerate the indexes and move this plan to `archive/`.

## 5. Risks

| Risk | Mitigation |
|---|---|
| Renumbering silently reshuffles the evaluation split | R1 keys the split on MONDO ids and re-baselines the champion before any graph change |
| Source drift is mistaken for the effect of the fixes | Two stages (D10): R2 on today's data, R5 for the fresh pull |
| New MONDO ids are missing from the PrimeKG grouping snapshot | Count newly ungrouped diseases in R5; they stay ungrouped, as today |
| A moved dataset changes name, breaking Part 2 | D8 keeps every name; R4 checks Part 2's sync recipes resolve unchanged |
| Schema validation fails on rebuild | Propagate schema fully before each rebuild; build fused stages separately |
| The fresh pull cannot be reproduced later | D9 pins every source at this pull |
| The Explorer captions edges with `relation`, not `display_relation` | Check once after R2; if so, the new labels show only in edge details |

## 6. Findings during the revision

### 6.1 Which family columns are still needed (2026-11-07)

Every reader was checked in `DEMO_TARGET_IDENTIFICATION`, `DEMO_TI_EVIDENCE`, the notebooks and the
webapp. `compute_validation_auc_by_disease_2`, `compute_disease_hierarchy_annotation` and
`compute_lung_granularity_check` are mirrors of recipes no longer in DSS and do not count.

| Column | Live readers | Verdict |
|---|---|---|
| `disease_index` | every join | keep: the key |
| `disease_family_id` | `compute_family_panel` (visual join), `compute_demo_panel_config` (Act 3 families), webapp families route, `compute_pool_reachability`, `compute_split_audit_2`, nb6, nb7 | keep: the Act 3 family grouping, a different concept from the split key |
| `anchor_name`, `hop_depth` | webapp shortlist and families (ordered by `hop_depth`), panel recipes, nb7 | keep: shown in the demo |
| `disease_split_key_mondo` | `split_by_disease_key` | keep: decides the folds |
| `disease_split_key` | `compute_split_audit_2`, `compute_drug_target_benchmark`, nb3 | retire after those three move to the MONDO key; the audit should check the key the split routes on (1:1 today, so results are unchanged) |
| `split_key_name` | `compute_split_audit_2` (readable output; finds the diabetes pair by name) | keep: cheap, makes the audit readable |
| `split_key_rule` | none | keep in `disease_family_id` as the audit trail; stop passing it downstream |

### 6.2 Calibration and showing a probability (2026-11-07)

Measured on the retrained champion's validation scores (3,568,682 pairs, 607 diseases, 1.85%
positives). Calibrators were fitted on half the diseases and tested on the other half, grouped by
disease as the project's split is. Offline analysis; nothing was changed in DSS.

**The raw score is not a probability.** `train_m7-f14` uses `CLASS_WEIGHT` (balanced classes) and
`NO_CALIBRATION`. The raw score averages 0.272 against a true rate of 0.0185, about 15× too high;
expected calibration error 0.254. The top decile scores 0.779 on average and is 12.4% positive.

**Calibration and the ranking:**

| Method | Per-disease ranking | Macro AUC (304 test diseases) |
|---|---|--:|
| Raw | — | 0.8199 |
| Platt (sigmoid) | identical on every disease | 0.8199 |
| Isotonic | adds ties at the top: a median of 12 distinct values among the top 20, and 3 genes share the 20th gene's value; one disease's AUC moves by −0.019 | 0.8199 |

Both calibrators bring calibration error to 0.001. Platt changes nothing about the order; isotonic
creates ties exactly where the shortlist is read, so it is the wrong choice here. The one way
calibration would change the ranking is through DSS's built-in option, which either spends the test
fold or retrains the model on less data (R7b, step 1).

**What a calibrated value means.** One Platt curve tracks each disease's own base rate well:
correlation +0.985 between a disease's observed positive rate and its mean calibrated value; by
base-rate quartile, observed 0.31% / 0.60% / 1.02% / 3.20% against calibrated 0.37% / 0.56% /
0.99% / 3.22%. Among each disease's top 20 genes the calibrated value has a median of 0.27 (10th–90th
percentile 0.06–0.80); the observed hit rate there is 31.8% against a mean prediction of 35.2%.

The limit is the label. A calibrated 0.27 is the chance that the pair is **already recorded** as an
association (Open Targets genetic or somatic evidence ≥ 0.3, or a phenotype-derived link), not the
chance of being a good target. Negatives are unlabeled genes, so for the novel candidates the demo
exists to surface, the value is a floor: the 4,135 top-20 genes without a recorded association have
a median of 0.16.

**Nothing depends on the score's absolute value.** The only score thresholds in the recipes,
notebooks and webapp (`score >= 0.8`) apply to the Open Targets known-drug score, not the model's.
So a monotone calibration changes no shortlist, rank or ranking metric; only numbers quoted as score
values move.

**Recommendation (D12, revised 2026-11-07):** build the calibration into a new version of the
champion, using the training recipe's sigmoid calibration fitted on the test fold, rather than a
separate post-processing recipe (R7b). Keep rank and percentile as the primary display. If the
score is shown, call it "chance of being a known association", put it next to the disease's base
rate or express it as an enrichment over it, and never present it as the probability of being a
target.
