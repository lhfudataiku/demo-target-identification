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

**Done 2026-11-08.** `DEMO_KG_LS` itself was not changed.
- **Project.**
  - `DEMO_KG_PREP` ("KG source preparation (Life Sciences)") uses the same project defaults as
    `DEMO_KG_LS`: code env `demo_kg-ls-ontology`, container `default`.
  - It has the four domain zones plus a fifth, **Pinned downloads**.
  - The 28 outputs are Parquet on `dataiku-managed-storage`, with the same names, schemas and column
    descriptions as the `DEMO_KG_LS` copies (28/28 identical).
- **Folders.**
  - `raw_files` (filesystem) and `upload` (S3) are copies of `nIhuvFJm` and `kFQAspRA`, verified
    byte-identical by SHA-256.
- **D9, as built.** One recipe, `compute_pinned_sources`, downloads each unversioned source once into
  folder **`pinned_sources`** (S3). It never overwrites a file already there. Six extracts read those
  files and never the URLs: `extract_mondo`, `extract_hpo`, `compute_go_terms`, `extract_reactome`,
  `extract_huri` and `compute_gene_names`.
  - Two departures from the D9 wording, both chosen deliberately:
    - the pins live in a new folder, not `raw_files`, so a rebuild can never touch the uploaded
      files and the pinning step shows in the flow lineage;
    - `compute_gene_names` (a live HGNC query) is pinned too. It is unversioned, though it was not
      in the plan's list of five.
  - `MANIFEST.json` records URL, retrieval time, size, SHA-256, `Last-Modified` and the release
    version for each file.
  - To take a new release: delete the file, then rebuild `compute_pinned_sources` and its reader.
- **Code changes in the copies (mirrored in `dss_recipes/`).**
  - the six readers above;
  - the drafted GO `NOT` filter in `compute_go_terms`;
  - `extract_ppi` reads its file with `get_download_stream`, because `get_path()` on the copied
    folder raised `PermissionError`.
  - `dss_recipes/` now holds the `DEMO_KG_PREP` versions. They differ from the `DEMO_KG_LS` live
    code until R4 deletes those recipes.
- **Code env.** `demo_kg-ls-ontology` had no `pyarrow`, which the six Open Targets recipes need to
  read the 26.06 parquet files, so they could not have rebuilt in `DEMO_KG_LS` either. With the
  user's approval `pyarrow>=18` was added (26.0.1 installed) and the env's container image rebuilt.
  Only `DEMO_KG_LS` and `DEMO_KG_PREP` use the env.
- **Shared.** All 28 outputs are exposed to `DEMO_KG_LS`.

**The pull (2026-11-08), from `MANIFEST.json`:**

| Source | Graph built from | This pull |
|---|---|---|
| MONDO | `releases/2026-08-04` | `releases/2026-11-03` |
| HPO (`hp.obo`, annotations) | `releases/2026-06-23` | `releases/2026-09-01` (files dated 2026-09-02) |
| GO `go-basic.obo` | `releases/2026-07-26` | `releases/2026-07-26`: **no new release** |
| NCBI gene2go, gene2ensembl | early Aug 2026 | dated 2026-11-08 (NCBI rewrites them daily) |
| Reactome | release 97 | release 98 |
| HuRI HI-union | file dated 2020-04-12 | same file |
| HGNC custom query | 2026-08-13 | 2026-11-08 |

**Acceptance: row counts, `DEMO_KG_PREP` against `DEMO_KG_LS`.**
- **Pinned sources reproduce exactly.**
  - All nine Open Targets outputs: `raw_ot_assoc` 517,830, `ot_target_map` 78,691,
    `ot_disease_map` 15,508, `raw_drug_protein` 7,959, `drug_vocab` 11,160, `raw_drug_indication`
    40,044, druggability / safety 78,691 each, `raw_ot_known_drug` 107,593.
  - `raw_string_ppi` 209,423, `raw_menche_ppi` 141,296, `disease_group_map` 6,392,
    `hgnc_identity` 44,477.
- **Unpinned sources differ.** Each difference follows from a release in the table above:
  - MONDO: `raw_disease_disease` +324, `mondo_terms` +35, `mondo_references` +34.
  - HPO: `hpo_terms` +58, `raw_phenotype_hierarchy` +58, `raw_disease_phenotype` +1,131,
    `raw_phenotype_protein` +909.
  - GO: `go_terms` and `raw_go_hierarchy` unchanged (same release). `raw_go_protein` −661: the
    `NOT` filter dropped **1,402** human annotation rows before deduplication (`NOT involved_in`
    584, `NOT enables` 567, `NOT located_in` 197, and rarer qualifiers), and gene2go drifted.
  - Reactome 98: `reactome_terms` +6, `raw_pathway_pathway` +6, `raw_pathway_protein` −584.
  - `gene_names` +102 (HGNC). `raw_huri_ppi` −1: same HuRI file, but newer gene2ensembl mapping.

### R4 — switch `DEMO_KG_LS` to the copies *(DSS)*
1. For each moved output, delete the producing recipe in `DEMO_KG_LS` and add a sync recipe
   `DEMO_KG_PREP.<name>` → `<name>`, same dataset name, Parquet. Name it
   `compute_DEMO_KG_PREP_<name>_copy`, following Part 2's convention.
2. Put each copy in its domain's harmonisation zone. Move the four GO/Reactome harmonise recipes to
   a new "Function & pathways harmonisation" zone, then delete the emptied loading zones.
   *(Revised the same day at the user's request: the loading zones stay, and hold the syncs.)*
3. **Accept when:** the flow check is clean; every `DEMO_KG_LS` recipe input resolves; Part 2's 13
   sync recipes still resolve with no edits.

**Done 2026-11-08.** Nothing was built: the copies point at `DEMO_KG_PREP` but still hold the old
pull until R5.
- **Recipe swap.**
  - The 16 loading recipes in `DEMO_KG_LS` were deleted after their code and settings were backed
    up. The code is also in `dss_recipes/` and `DEMO_KG_PREP`.
  - Each of the 28 outputs now has a sync recipe `compute_DEMO_KG_PREP_<name>_copy` reading
    `DEMO_KG_PREP.<name>`. Its settings are identical to Part 2's sync recipes (`STRICT_SYNC`).
  - All 28 dataset definitions (names, Parquet location, schemas and descriptions, Part 2 shares)
    are unchanged.
  - `dku recipe create-sync` refuses an existing output, and deleting the dataset would drop its
    share to Part 2. The working route is `dku recipe create <name> -t sync -i DEMO_KG_PREP.<name>
    --output-ds <name>`.
- **Zones** (final layout; the user revised it the same day, for readability).
  - Each domain keeps a loading zone: **Gene & interactome (HGNC, PPI)** (the Default zone, as
    before R4), **Drugs & gene-disease (Open Targets)**, **Disease & phenotypes (MONDO, HPO)** and
    **Function & pathways (GO, Reactome)**. Each holds its `DEMO_KG_PREP` inputs, their syncs and
    the copies: 5, 9, 8 and 6 respectively.
  - The four GO/Reactome harmonise recipes moved out of the old mixed zone into a new **Function &
    pathways harmonisation** zone, so every domain is now loading zone → harmonisation zone.
  - The three non-default loading zones were recreated with new ids (`esHALIf`, `gfUTykN`,
    `MT2nmHs`): a first pass had deleted them. The zone descriptions now say the tables are syncs
    from `DEMO_KG_PREP`; the harmonisation zones keep their pre-R4 summaries.
  - The CLI cannot move shared-in datasets between zones; the Python API can
    (`flow.get_zone(id).add_item(client.get_project("DEMO_KG_PREP").get_dataset(name))`). It
    stores them exactly as the UI stores Part 2's foreign items. `dku flow zones` still lists them
    under Default, because its derived membership matches the bare id; trust the zone's own items.
  - The folders `raw_files` (`nIhuvFJm`) and `upload` (`kFQAspRA`) were deleted at the user's
    request: nothing read them, and their files are byte-identical in `DEMO_KG_PREP`. The folder
    delete leaves the files in storage.
- **Acceptance.**
  - All 61 recipe inputs resolve. Each of the 28 `DEMO_KG_PREP` inputs feeds exactly one sync.
  - Part 2's 13 sync recipes and `compute_ytvuniN8` resolve with no edits. Six of them now read
    copies fed from `DEMO_KG_PREP`.
  - The flow check matches the pre-R4 baseline exactly. The same 14 "column description changed"
    errors remain on `join_gd_genes`, `join_dp_genes`, `filter_hp_mondo_overlap` and
    `join_disease_phenotype_mondo`; they are older than R4 and descriptions only. The same 4 nodes
    are unchecked, and the 12 extra nodes (net) pass. The R5 rebuild propagates schemas and should
    clear the description errors.

### R5 — stage B: full rebuild from the fresh pull *(DSS)*
1. Sync the copies, then rebuild `DEMO_KG_LS` end to end (propagate schema first; one job), the Kuzu
   graph and Explorer, and `compute_ytvuniN8`.
2. **Accept when:**
   - integrity checks pass;
   - the GO `NOT` count dropped is logged;
   - every relation count change is explained by a source release or by D1–D2;
   - an old→new `node_index` map exists for every surviving node, with lost and new nodes listed.

**Status 2026-11-09: tables rebuilt and accepted; the Kuzu graph is blocked on a plugin bug.**
- **Rebuild.** One `RECURSIVE_FORCED_BUILD` job (schema auto-update on) rebuilt every `DEMO_KG_LS`
  dataset, from the 28 copies of the `DEMO_KG_PREP` pull to the seven sinks (`kg`, `graph_edges`,
  `edge_metadata`, `hgnc_identity`, the three `raw_ot_*` tables Part 2 reads). It started no job in
  `DEMO_KG_PREP` and did not touch either snapshot folder. Intermediate row counts reported by DSS
  are stale metrics; the graph tables were downloaded and compared directly.
- **Acceptance**, `graph_nodes` / `graph_edges` against the R2 build:
  - **Integrity:** 0 full-row duplicates, 0 self-loops, every edge has its reverse, no unknown
    endpoint, no isolated node. The 862 duplicate `(relation, x, y)` triples are the same as before R2.
  - **Nodes** 113,391 → **113,497**: 113,325 survive, 66 lost (49 MONDO, 10 HPO, 4 Reactome, 3 genes),
    172 new (88 MONDO, 70 HPO, 10 Reactome, 4 genes). Inserts renumber later nodes, so 76,786 survivors
    changed `node_index`; the split is keyed on MONDO ids since R1, so it is unaffected. All 1,247
    grouped disease nodes are unchanged; the 88 new MONDO diseases stay ungrouped (Risk table).
  - **Edges** 2,851,872 → **2,853,534** (+1,662). Every change traces to a source release:
    - MONDO: `disease_disease` +582, `disease_phenotype_disease` +130. Open Targets did not change, so
      its edges moved only through disease grounding: OT-sourced `disease_protein` −164, and one
      `drug_investigated_for` pair (2 rows) on the grouped disease `14720_20250_16646`.
    - HPO: `phenotype_protein` +1,640, `disease_phenotype_positive` +1,124, `_negative` +12,
      `phenotype_phenotype` +112, phenotype-derived `disease_protein` +216.
    - GO (same release, hierarchies identical): gene annotations −1,234 directed rows, from gene2go
      drift and the `NOT` filter, which dropped 1,402 rows in R3 (D2).
    - Reactome 98: `pathway_protein` −742, `pathway_pathway` +12. HuRI: one `protein_protein` pair.
    - Unchanged: `drug_protein`, `indication`, the GO hierarchies.
  - **Flow check:** 11 of the 14 older description-only errors remain (`join_gd_genes`,
    `join_dp_genes`, `join_disease_phenotype_mondo`).
  - The `node_index` map and the lost and new node lists were written to the session scratchpad,
    not yet to a durable location.
- **Snapshot (user decision, 2026-11-09).** A saved snapshot holds only the graph definition and names
  its datasets; each build replaces `built-graphs/<id>/`. A source refresh with an unchanged
  definition therefore reruns the current snapshot: `build-graph-ZKGaRg` was rerun into `ouzaULiq`.
  A change to the definition still gets a new snapshot, and `Mp25kL` is never rebuilt.
- **⚠ Blocker: the Visual Graph plugin (1.5.0, Kuzu 0.11.3) silently drops nodes whose name has a
  comma.** `python-lib/graph/ingestion/kuzu/batch_insert.py` writes each 10,000-row chunk of nodes
  to CSV and loads it with `COPY … (IGNORE_ERRORS=true)`. Kuzu infers the CSV dialect from a file's
  first rows; when none is quoted it assumes no quoting, every quoted row fails, and
  `IGNORE_ERRORS` skips it and every edge to it without a log line.
  - The R5 build lost **716 nodes: 673 diseases, 15 drugs, 28 phenotypes**, which explains the
    entire edge shortfall in Kuzu. The editor's own working graph, rebuilt by the user on R5 data,
    loses the same nodes (26,519 diseases).
  - Every earlier build (`Mp25kL`, the R2 build of `ZKGaRg`) lost the same 15 drugs and 28
    phenotypes; no disease was lost before R5, because which rows fail depends on how rows fall
    into chunks.
  - Verified fix: `AUTO_DETECT=false` (or `QUOTE='"'`) on both `COPY` statements loads every row.
  - Decision (user, 2026-11-09): report the bug to the plugin's maintainers and wait for a fixed
    version; do not patch the installed plugin. `compute_ytvuniN8` is **not** rebuilt, so Part 2's
    `ytvuniN8` keeps the R2 build (27,153 diseases, all present).
- **To close R5:** install the fixed plugin, rerun `build-graph-ZKGaRg`, check Kuzu's node and
  relation counts against `graph_nodes` / `graph_edges` (same-type relations stored both ways,
  cross-type once), then rebuild `compute_ytvuniN8`. The Explorer still serves `Mp25kL`.
- **2026-11-10: the graph is fixed.** `visual-graph` 1.6.0 installed from the store (not a dev
  plugin). `build-graph-ZKGaRg` rerun (job `Build_kg_ls_v0_2_ZKGaRg__NP__2026-11-10T08-58-49.638`,
  DONE). All 27 Kuzu labels and relations match the expected counts from `graph_nodes` /
  `graph_edges` exactly: **113,497 nodes** (27,192 diseases, 5,282 drugs, 19,180 phenotypes), so
  the 15 drugs and 28 phenotypes every earlier build lost are back too. `compute_ytvuniN8` is
  **not yet rebuilt**: Part 2's synced tables still carry the pre-R5 `node_index`, so copying the
  R5 graph alone would put two numberings in Part 2. Decided (user, 2026-11-10): copy it together
  with the syncs as R6 step 1.

### R6 — Part 2 rebuild and re-evaluation *(DSS in Part 2)*
**Progress 2026-11-10: copies done.** One non-recursive job rebuilt the 13 table syncs from
`DEMO_KG_LS` and `compute_ytvuniN8` (the Kuzu folder). Every table's row count equals its source
(`graph_nodes` 113,497, `graph_edges` 2,853,534, and the other 11), and `ytvuniN8` holds the
2026-11-10 `ZKGaRg` build (`db.kz` 148.8 MB, same files as `ouzaULiq`). This closes R5.
**Until the downstream rebuild finishes, Part 2 is mixed:** the copies and the graph carry the R5
`node_index`; every feature table, the model's scores and the webapp's serving datasets still carry
the old one. The deployed webapp's *Drugs & graph* presets (`a4ExplorerQueries.ts`) look nodes up by
`node_index` in the Explorer `wBcApLN`, which reads `ytvuniN8`, so they resolve to the wrong nodes in
this window. Nothing else in the webapp reads the graph or the copies.

**Progress 2026-11-10: rebuild, retrain and rescore done** (Spark pipelines turned off by the user
first, so no intermediate dataset was skipped). D11 not applied.
- One RECURSIVE_BUILD to the three split sets and `split_audit_2` ran 22 recipes (pair index, every
  enrichment and DWPC recipe, family id, path-evidence filter, split, audit). Audit: zero straddling
  keys, zero key overlap. Validation 604 diseases / 3,523,775 rows / 65,546 positives (was 607 /
  3,568,682 / 65,929); train 420 / 2,355,742 / 44,479; test 130 / 806,169 / 16,911. Three validation
  diseases left with the source refresh: *combined hepatocellular carcinoma and cholangiocarcinoma*,
  *leprosy*, and *acute myeloid leukemia with mutated NPM1* (no longer a graph node).
- `train_m7-f14-cal` retrained: `W8VhjZOZ` version `1794305004361` active, `initial` kept
  (`dku model set-active-version` restores it). Same 14 inputs (checked from its Shapley
  importances). DSS's pooled test-fold AUC 0.908; not the project metric.
- `scored_champion` rescored (3,523,775 rows), then one RECURSIVE_BUILD of the 34 serving datasets
  of scenario `Refresh_serving_layer`.
- **Per disease against the 2026-11-07 champion** (603 diseases scored in both; baseline mapped
  through the R5 old→new index): **0 ties**, 309 higher / 294 lower; median |ΔAUC| 0.0066, 90th
  percentile 0.042, max 0.208 (all of the largest moves have 2–28 positives). Wilcoxon p = 0.28;
  van Elteren stratified by positives quartile z = +1.33, p = 0.18. Macro 0.8180 on 603 (was 0.8170
  on 606; 0.8163 vs 0.8180 on the common 603); median 0.8512 (was 0.8530). **No detectable change.**
  The step-3 attribution cannot be made from these numbers: the 2026-11-07 retrain on identical data
  moved the same way (318 / 288 / 0 ties, p = 0.27), so retraining noise is as large as anything the
  refresh did.
- **The mixed-numbering window is closed:** every `gene_index` and `disease_index` in
  `dashboard_candidates` (105,218 rows, 12 diseases) names the same node in the R5 graph, so the
  *Drugs & graph* presets resolve correctly again. The webapp's table cache keys on build time and
  needs no restart.
- **Demo consequences:** HER2+ ERBB2 is now **#29** (was #16); the HER2+ top 16 holds 15 recorded
  associations and HRAS (#6). The calibrated scores at the head are nearly flat: ranks 1–16 for HER2+
  span 0.4067–0.3994, which webapp step W2 has to show without implying a ranking within ties.
- **Found: the trials/papers cache is keyed by `node_index` and does not check its pair.**
  `act4_evidence_cache` names each file `disease_index/gene_index.json`, and `pair_sources._read`
  checks only the format version. After the renumbering all 26 cached files point at a different
  pair; one is a served pair (endometrium adenocarcinoma × RAB5C, rank 3,910, which would show the
  cached triple-negative × CCND1 records). The other 25 are orphaned, and the demo pairs, under their
  new indexes, have no file and search afresh.
- **Cache fixed 2026-11-10:** the 26 files were backed up and deleted, and `pair_sources._read` now
  uses a file only if its stored symbol and disease name match the pair (commit `b7d0651`, deployed
  to `OlmPX9a` the same day).
- **Step 4, drug-target benchmark (a warning, not a target):** macro drug-target AUROC 0.6737 →
  **0.6703**; route-supported 0.7392 → 0.7362. Association/drug correlation rose from r = +0.091 to
  **+0.167** (R² 0.0278, t = 1.85 over 122 diseases; still not significant at 0.05).
- **Step 5 done 2026-11-10: notebooks re-run and documented numbers retargeted.** The evidence project
  `DEMO_TI_EVIDENCE` was rebuilt first (25 recipes, one forced recursive job), then all seven
  assertion scripts ran. Two scripts were broken by the renumbering rather than stale: `nb1` and `nb7`
  pinned five disease `node_index` values (obesity, breast, lung, uterine, heme), so `nb1` read
  "0 known targets" with no error and `nb7` crashed. Both now resolve the disease by MONDO id and
  assert it is unique. That left **63 stale values**, all retargeted in the notebooks, in
  `VALIDATION.md` and `CLAIM_REGISTRY.json` (validator green) and in their consumers
  (`DEMO_NARRATIVE.md`, `WEBAPP_DESIGN.md`, `PROJECT_CONTEXT.md`, dated notes added to
  `BREAST_SURGEON_BRIEFING.md` and `panel_selection/README.md`). Values that still pass within their
  tolerance (pooled AUROC 0.8908, HER2+ AUROC 0.9385, the 3.06× / 2.85× / 2.30× tractability lifts)
  were left as documented. Two claims changed wording, not only value: macro degree-matched lift now
  beats the naive lift at every K, including K=10 (`TI-VAL-008`), and HER2+/TNBC share 2 novel top-50
  genes, not 1 (`TI-VAL-009`). Demo-walkthrough numbers the notebooks do not assert were re-derived
  from the served list: the HER2+ filter funnel is 12,252 → **29** in the top 200 with SMARCA2 fourth
  (#46 unfiltered), 8 of the HER2+ top 15 carry a liability flag, and ERBB2 ranks #29. The one stale
  DSS flow-zone description (zone 31 still named the deleted `m7-f14` / `hJLGoYn4`) now names
  `m7-f14-cal` / `W8VhjZOZ`; `FLOW_MAP.md` regenerated.
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
   negatives are unlabeled genes, so the value is a floor for novel candidates. *(Carried out as
   step W2 of [`WEBAPP_REVISION_WORKPLAN.md`](WEBAPP_REVISION_WORKPLAN.md), from 2026-11-09.)*
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
| The Visual Graph build silently drops comma-named nodes (found in R5) | Count Kuzu nodes and relations against `graph_nodes` / `graph_edges` after every build, before Part 2 copies the graph |

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
