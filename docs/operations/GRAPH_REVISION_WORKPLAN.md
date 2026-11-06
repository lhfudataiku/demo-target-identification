# Graph revision — workplan

> **Lifecycle:** Active plan · **Audience:** Part 1 builders, DSS flow maintainers and Part 2
> reviewers · **Authority:** the sequence, method and acceptance checks for revising the knowledge
> graph: moving data loading into its own project, correcting two wrong relations, making edge labels
> readable, and rebuilding from current sources · **Update when:** a decision is taken, a step is
> accepted or re-scoped, or a fact in §2 is superseded · **Generated dependencies:** none ·
> **Excludes:** the graph method itself, in [`GRAPH_BUILDING.md`](../graph/GRAPH_BUILDING.md); Part 2
> modelling method, in [`TARGET_PRIORITIZER.md`](../prioritizer/TARGET_PRIORITIZER.md).

**Status: APPROVED — 2026-11-06.** All decisions D1–D10 are taken; next is R1.
Nothing in DSS has changed for this plan. The repository holds the drafted code for steps R2 and R5
(`dss_recipes/attach_node_index.py`, `dss_recipes/compute_go_terms.py`), not yet pushed. Every DSS
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

**Graph:** 113,391 nodes, 2,851,510 directed edge rows, 18 relations, built 2026-08-14.

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
| D7 | **Freeze the evaluation split by disease identity** before renumbering: record each disease's fold against its stable id (`node_id`, `node_source`); new diseases get a fold from a hash of that id. | taken 2026-11-06 |
| D8 | **Part 2 keeps reading `DEMO_KG_LS`, not `DEMO_KG_PREP`.** The LS copies keep their current names, so Part 2's 13 sync recipes need no change, and Part 2's raw data always comes from the same pull as the graph. | taken 2026-11-06 |
| D9 | **Pin every source at this pull:** each unpinned download is saved once to a `raw_files` folder in `DEMO_KG_PREP` and read from there afterwards. | taken 2026-11-06 |
| D10 | **Two-stage rebuild** (R2, then R5) so the effect of the relation fixes is measured apart from source drift. | taken 2026-11-06 |
| — | New relation name `disease_phenotype_disease`; label wording in [`GRAPH_BUILDING.md`](../graph/GRAPH_BUILDING.md) §4.4 | taken with D1 |

## 4. Steps

Each step lists who acts. "DSS" steps change the live projects and run only after approval.

### R0 — decisions *(user)* — done 2026-11-06
D6–D10 approved as proposed.

### R1 — baseline and split freeze *(DSS in `DEMO_TARGET_IDENTIFICATION`)*

**How the split works today** (live, 2026-11-06):
- `compute_disease_family_id` gives each disease a `disease_split_key`: the nearest member of an
  elevated key set above it in the MONDO hierarchy, or the disease itself when no key is reachable.
- `split_by_disease_key` then sets `split_role` from that key's `node_index`: `mod(key, 10)` 0–4 →
  validation, 5 → test, 6–9 → train, plus five hard-coded keys forced to validation.

**Three places depend on index order or value:**
- the modulo;
- the five constants;
- the tie-break `min(found)` when a disease reaches two keys at the same depth (`DEC-OPS-001`).

**Design: freeze the outcome, not the rule.** Record today's fold for every disease by stable
identity, so existing diseases keep their fold whatever the renumbering, and only genuinely new
diseases need a rule.

1. **Baseline snapshot.** Copy these to write-protected `baseline_2026_11_*` datasets:
   - `graph_nodes` (for the old→new index map by `node_id`, `node_type`, `node_source`, as in
     `index_remap.json`);
   - `enriched_graph_features_candidate_psplit` (6,754,128 rows: every feature, label and split key);
   - `psplit_train_set` / `psplit_validation_set` / `psplit_test_set`;
   - `scored_m7`;
   - `validation_auc_by_disease`;
   - the graph relation counts.
2. **Frozen fold table** `disease_fold_frozen` (built once, then write-protected). One row per
   disease in today's candidate table, with these columns:
   - disease `node_id` and `node_source`;
   - its split key's `node_id` and `node_source`;
   - today's `split_role`.
3. **Fold lookup** `disease_fold_current`, rebuilt with every graph build:
   - a visual Join maps the frozen identities to the current `node_index` through `graph_nodes`;
   - a disease not in the frozen table takes its split key's frozen fold if that key is known;
   - otherwise it takes a fold from a stable hash of the key's MONDO id, with the same 50/10/40
     proportions.
4. **Split reads the lookup.** `split_by_disease_key` stops computing `split_role` from the index:
   - a visual Join attaches `split_role` from `disease_fold_current`;
   - the split runs on that column's values;
   - the GREL with the modulo and the five constants is retired.
5. **Accept when:**
   - rebuilding the split on today's graph gives **row-for-row identical** train, validation and test
     sets;
   - `compute_split_audit_2` still reports zero straddling keys.

**Known limit:** if a MONDO release moves a disease into a different family, its frozen fold stays.
`compute_split_audit_2` runs in R6 to catch any family that now straddles folds; any it finds are
reported, not silently fixed.

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
1. Rebuild the copies, features, split (frozen by R1), and retrain the champion's configuration.
2. Compare with the R1 baseline per disease: report ties first, then the stratified paired test,
   macro per-disease AUC (never pooled).
3. Attribute changes:
   - R2 changed no champion feature, so any shift comes from R5's source drift or the GO fix;
   - `dwpc_GBGD` and `dwpc_GFGD` are the features expected to move.
4. Check the drug-target benchmark as a warning, not a target.

### R7 — label sensitivity *(read-only)*
Re-score the champion's per-disease AUC on Open-Targets-only positives (excluding the 27,713
phenotype-derived `disease_protein` links), to see whether those links flatter the results.

### R8 — documents and close *(repository)*
1. Update `GRAPH_BUILDING.md`: §7 statistics, 19 relations, and the 2026-11-06 log entry, marked as
   built.
2. Regenerate `FLOW_MAP.md`.
3. Add `DEMO_KG_PREP` to the project map in `CLAUDE.md` / `AGENTS.md` and `PROJECT_CONTEXT.md`.
4. Retarget documented Part 2 numbers by the skill's number-update procedure.
5. Record D6–D10 in the decision register where the admission rule is met.
6. Regenerate the indexes and move this plan to `archive/`.

## 5. Risks

| Risk | Mitigation |
|---|---|
| Renumbering silently reshuffles the evaluation split | R1 freezes it before anything is rebuilt; verified identical before moving on |
| Source drift is mistaken for the effect of the fixes | Two stages (D10): R2 on today's data, R5 for the fresh pull |
| New MONDO ids are missing from the PrimeKG grouping snapshot | Count newly ungrouped diseases in R5; they stay ungrouped, as today |
| A moved dataset changes name, breaking Part 2 | D8 keeps every name; R4 checks Part 2's sync recipes resolve unchanged |
| Schema validation fails on rebuild | Propagate schema fully before each rebuild; build fused stages separately |
| The fresh pull cannot be reproduced later | D9 pins every source at this pull |
| The Explorer captions edges with `relation`, not `display_relation` | Check once after R2; if so, the new labels show only in edge details |
