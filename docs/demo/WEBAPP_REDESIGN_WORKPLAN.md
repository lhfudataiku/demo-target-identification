# Webapp redesign — workplan

> **Lifecycle:** Planning (draft) · **Audience:** webapp implementers and technical reviewers ·
> **Authority:** the phase sequence, the technical design of each phase, and its acceptance criteria ·
> **Update when:** a phase is accepted or re-scoped, or a budget in §8 is measured · **Generated
> dependencies:** none · **Excludes:** the decisions, measurements and target design, which are
> [`WEBAPP_REDESIGN_SCOPE.md`](WEBAPP_REDESIGN_SCOPE.md) and are referenced here by their ids (D1–D15).

**Status: DRAFT — 2026-10-25, revised 2026-10-26 (a second webapp, Phase 5 beside the old scoring
chain, the flow migration decided separately, Phase 3 preloaded from Part 1). Not approved; no phase has started.**

## 1. How the work runs

- Each phase leaves `npm run check` (from `webapp/frontend/`) printing `check: ok`, with no new
  suppression, and is reviewed before the next starts.
- **`npm run check` misses one design rule.** Its inline-colour lint matches only a static `style="…"`,
  so a colour set through a bound `:style` passes unseen. Every frontend phase therefore also runs, from
  `webapp/frontend/`:

  ```bash
  grep -rnE '(:style|style)="[^"]*(seriesVar|color|background|var\(--|#|rgb|hsl)|^\s*(background|color|fill|stroke|border-color)\s*:' --include='*.vue' src
  ```

  ```bash
  grep -rnE '<(button|input|select|textarea|table)[ >]' --include='*.vue' src
  ```

  The first finds colours in inline styles, including multi-line `:style="{ … }"` blocks and computed
  style objects; the second finds raw HTML controls where a kit part belongs. On 2026-10-25 the first
  matches ten files: `ActBar`, `ActCard`, `ActGeneGrid`, `ActIntervals`, `ActMatrix`, `ActSankey`,
  `CalibrationView`, `EvidenceView`, `ShortlistView` and `TherapeuticAreaView` (in `ActIntervals` and
  `ActSankey` only through ECharts options). The second matches nothing. Phase 1 deletes or fixes all but
  `ShortlistView` and `ActCard`; Phase 2 clears those two. This is a rule bs-blueprint's lint should own,
  so it is worth raising upstream through bs-blueprint's own upstream guide.
- Phases marked **DSS** change the live project. Each needs the user's approval at the time; the user
  runs builds, scenarios and `make deploy`, and Claude verifies read-only afterwards.
- **The redesign deploys to a second webapp in `DEMO_TARGET_IDENTIFICATION`**, so the current
  *Target Prioritizer* (`OlmPX9a`) keeps serving the demo until the switch-over in Phase 8. On the
  redesign branch `app.env` sets its own `LIB_NS` (`target_prioritizer_next`), a distinct
  `VITE_APP_NAME` (`Target Prioritizer (next)`) and an empty `WEBAPP_ID`; the first `make deploy`
  creates the webapp and writes its id back. **The separate `LIB_NS` is load-bearing:** `deploy.sh`
  mirrors the backend and frontend into `python/<LIB_NS>/` with `--delete`, so a second webapp sharing
  the namespace would replace the code the live webapp imports at its next restart. Both webapps read
  the same datasets, and no phase changes one the current webapp reads.
- Nothing is committed or pushed without the user's approval of a change summary.
- The mockup's components are the reference for Phases 1 and 2. Their source is in the git-ignored
  `docs/demo/design_review/source/` (scope §4.4; its README maps each file). They were written against
  the same kit, shell and lint, so they move into `webapp/frontend/src/` rather than being rewritten;
  their snapshot data (`design/src/data/`) is replaced by API calls, and the content written for the
  review (role labels, SHAP rows 3–5, assistant answers) is not carried over.

| phase | what | DSS change |
|---|---|---|
| 0 | decisions and documents | — |
| 1 | navigation and the evidence page | — |
| 2 | the shortlist on existing data | — |
| 3 | HGNC identity | one new Part 1 recipe, a sync, a join (D16) |
| 4 | drug lineage | a Group and a Join in S1, two datasets |
| 5 | top-5 SHAP | new recipes beside the old scoring chain |
| 6 | trials and literature | managed folder, scenario |
| 7 | evidence assistant | agent |
| 8 | verification and switch-over | deploy |

Phases 1 and 2 change no dataset or recipe; Phase 3 adds three objects and changes none. Phases 1–3
ship to the second webapp as one release, once Phase 3's datasets are built. Phases 4–6
each depend only on Phase 2's tabs; Phase 7 uses what 3–6 provide. The redesign is complete at
Phase 8. The flow migration is not one of its phases: whether it runs is decided afterwards (§11).

## 2. Phase 0 — decisions and documents

- Two register entries in `DECISION_REGISTER.md`: D1/D4/D5 (assistant, role labels, cache) and
  D9–D11 (the list leads, one evidence page, one disease). The boundary rule (D14) and the target
  zone layout (D15) below are recorded with the second.
  Both enter as `approved-not-executed`.
- `DEMO_NARRATIVE.md`: act order and the four-acts table. The act names stay as labels, so the many
  references to "act 2" or "act 4" across the documents keep their meaning.
- `WEBAPP_DESIGN.md`: the status lines, the §4 acts table, the §6 guardrail rows and §8, each change
  marked *planned*; the Act 4 funnel counts re-derived. The sections that describe the app as built
  change with the phase that builds them: §3.3 and the Act 1–3 card tables in Phase 1, the Act 4 card
  table in Phase 2.
- **Done when:** the user approves the doc diff.

**The boundary rule (D14).** It governs every phase from here on, whether or not the flow migration
later runs; the migration, if it runs, enforces it on what already exists:

- **Notebooks read only zones 00–31** (after the migration, through the evidence project's exposed
  objects) and recompute anything downstream in their own code. A notebook never reads a serving zone.
- **The webapp backend reads only serving zones** (`S1`–`S4` below).
- **No computed dataset is consumed by both.** Both may depend on the same inputs in zones 00–31;
  neither depends on the other's outputs.

**The target zone layout after zone 40 (D15)**, one zone per function of the new webapp. Datasets
named here exist today unless marked. New objects go straight into these zones; if the flow migration
runs, its M1 maps every remaining dataset and places each intermediate with its first served consumer.

| zone | serves | endpoint datasets |
|---|---|---|
| `40 Scoring & ranking` | both pages, as the shared core | `persona2_scored`, `persona2_scored_shap`, `top_candidates`, `target_candidates_2`, `candidates_annotated` |
| `S1 Shortlist` | the shortlist | `dashboard_candidates`; `candidate_identity` (new, Phase 3); `drug_evidence_records` (new, Phase 4); `persona2_scored_shap5` and `candidate_shap_top5` (new, Phase 5); the `act4_evidence_cache` folder (new, Phase 6) |
| `S2 Evidence · graph` | section 1, what the model can see | `graph_node_type_counts`, `graph_relation_counts`, `graph_node_source_counts`, `graph_ppi_provenance`, `graph_label_evidence` |
| `S3 Evidence · reconstruction` | section 2 | `validation_auc_by_disease`, `split_audit_2`, `disease_eligibility`, `hub_bias_meter`, `orthogonality_scatter`, `family_auc_by_family`, `persona_enrichment` |
| `S4 Evidence · family panels` | section 3 | `demo_panel_config`, `family_panel`, `family_panel_metrics`, `family_panel_overlap`, `family_panel_programme`, `family_panel_top50` |

If the flow migration runs: `breast_panel_metrics` and the A4 notebook-only datasets
(`known_drug_truth`, `filter_three_axes`, `pool_reachability`) move to the evidence project;
`shap_driver_frequency` and `shap_drivers_long` are expected to be deleted. Both are confirmed in the
migration's M1. Zone 20 is re-zoned into drug annotation, gene annotation, and disease family with
split key, without a rebuild. If it does not run, these stay where they are and nothing in the
redesign reads them.

## 3. Phase 1 — navigation and the evidence page

**Frontend**

- `router/index.ts`: `shortlist` becomes order 1 and the home redirect target; new route `trust`
  ("Why trust the list", order 2, icon `ShieldCheck`); remove `evidence`, `calibration`,
  `therapeutic-area`. Deep links use `?section=graph|reconstruction|family`.
- `stores/selection.ts` (Pinia): the selected `disease_index`, read and written by both pages (D11).
- `views/TrustView.vue` and `components/trust/`: `GraphSection`, `ReconstructionSection`,
  `FamilySection`, `BarList`, `AucHistogram`, `FamilyIntervals`, from the mockup. The family detail
  uses the existing `ActTabs`, and `ActMatrix` and `ActGeneGrid` with their colours moved from bound
  styles to token classes, as the mockup's copies already do (D12).
- Scroll to a section by setting the content pane's `scrollTop`; `scrollIntoView` also scrolls the
  shell's fixed-height ancestors and pushes the sidebar off screen.
- Remove `EvidenceView`, `CalibrationView`, `TherapeuticAreaView`, and the components only they use:
  `ActBand`, `ActBar`, `ActBeeswarm`, `ActDonut`, `ActHistogram`, `ActIntervals`, `ActSankey`,
  `ActStat`, `utils/a1ExplorerQueries.ts`, plus the already unused `ActScatter`. Keep `ActCard`,
  `ActInfo`, `ActTerm`, the glossary drawer and `VisualGraphExplorerCard`.

**Backend**

- `/api/calibration` gains `diseases`: `{disease_index, disease, auc, auc_rank, enrichment, n_known}`
  for every scored disease, from `persona_enrichment` (`auc_disease`, `rank_enrichment`, `n_pos`). The
  unlabelled `auc_values` and the `personas` list with its stale `is_current` stop being read.
- `/api/evidence` and `/api/families/{id}` are used as they are.

**Documents**

- `WEBAPP_DESIGN.md`: the §3.3 route → view → data table for the two pages, and the Act 1–3 card
  tables for the three sections; the *planned* marks this phase fulfils are removed.

**Done when**

- The root URL opens the shortlist; the sidebar shows two items and Settings.
- Changing the disease on either page changes it on the other; section 2 marks that disease; section 3
  opens its family, or says there is none.
- Every analysis listed in scope §4.3 is reachable; no figure is typed into copy.
- `npm run check` prints `check: ok`; the §1 colour search matches only `ShortlistView.vue` and
  `ActCard.vue`, and the control search matches nothing.

## 4. Phase 2 — the shortlist on existing data

- Split `ShortlistView.vue` (741 lines) into `components/shortlist/`: `CandidateTable`,
  `CandidateHeader`, `OverviewTab`, `RankingTab` and `LineageTab`. `EvidenceTab` (trials and
  literature) and `EvidenceInspector` (kit `Sheet`) are created in Phase 6 and `AssistantSheet` in
  Phase 7, when they have records to show; until then the Trials and Literature tabs hold an empty
  state and no empty shell ships.
- Kit parts only: `Tabs`, `Sheet`, `Collapsible`, `Pagination`, `Badge`, `StatusBadge`, `Table`,
  `Skeleton`, `Alert`, `Textarea`. Remove the inline style colours (`seriesVar`) from the moved code.
- `ActCard` stays, because `VisualGraphExplorerCard` wraps it: move its accent tints from computed
  style objects to token classes.
- Overview is a fixed brief from the flags; Ranking shows today's top two drivers until Phase 5;
  Trials and Literature show an empty state until Phase 6; Drugs & graph hosts the existing Explorer
  card and the drug flags until Phase 4.
- *How do we know?* links (scope §4.1).
- Correct the stale 13-disease and 129,253-row copy.
- `WEBAPP_DESIGN.md`: the Act 4 card table for the split shortlist.
- **Done when:** HER2+ renders live; no badge is a filter; every count shows its cut-off; the links
  land on the right sections; both §1 searches print nothing, which is when the last colour set
  through an inline style leaves the app.

## 5. Phase 3 — HGNC identity *(DSS: one Part 1 recipe, a sync, a join)*

**Preloaded, not fetched per click (D16).** Phase 3's first build looked each gene up live at the HGNC
REST service (`backend/services/hgnc.py`, committed 2026-10-26). It is replaced once the dataset below
exists; the header it feeds stays as built.

- **Part 1 (`DEMO_KG_LS`).** A new zero-input Python recipe `compute_hgnc_identity` reads one dated HGNC
  complete-set file (`hgnc/archive/archive/monthly/tsv/hgnc_complete_set_<date>.txt` on HGNC's public
  download bucket; the newest on 2026-10-26 is `2026-10-06`) and writes `hgnc_identity`: `hgnc_id`,
  `symbol`, `name`, `locus_type`, `location`, `alias_symbol`, `prev_symbol`, `gene_group`,
  `date_modified`, `entrez_id`, `ensembl_gene_id`, `uniprot_ids`, and `source_file` naming the dated
  file. Approved records with an NCBI Gene ID only, one row per ID, `entrez_id` written as a string to
  match `graph_nodes.node_id`; list fields stay pipe-separated as HGNC ships them. Managed storage,
  Parquet. Nothing in the graph build reads it.
- **`gene_names` and `compute_gene_names` are not touched** (scope §3.6): `gene_names` feeds the graph
  build, and its recipe is a live query, so even a rerun would change the graph's gene input.
- **Into Part 2.** Expose `hgnc_identity` to `DEMO_TARGET_IDENTIFICATION` and sync it in zone
  `00 Import · genes & interactome` with `compute_DEMO_KG_hgnc_identity_copy`, as the other Part 1
  copies are.
- **Zone `S1 Shortlist`.** A visual Join of `graph_nodes` (gene/protein rows, a pre-filter on the join)
  with `hgnc_identity` on `node_id` = `entrez_id` writes `candidate_identity`: `gene_index`, the graph's
  symbol, and the HGNC fields. A left join, so a graph gene with no HGNC record keeps its row with the
  fields empty.
- **Builds**, run by the user: `compute_hgnc_identity`, then one job in Part 2 with
  `--target hgnc_identity --target candidate_identity`, each non-recursive, so nothing upstream rebuilds.
- **Checks**, read-only: `candidate_identity` has one row per gene node (20,861 on 2026-10-26); the
  share with an HGNC record is reported; for the HER2+ top 200 every field equals a live HGNC lookup run
  locally with the first build's service, or each difference is explained by the file's date.
- **Backend.** `GET /api/candidates/identity?gene=` reads `candidate_identity` through the dataset
  cache. `services/hgnc.py` and the `graph_nodes` read go, so the backend reads only serving zones
  (D14) and makes no outbound call. The header's source line names the dated file in place of a
  retrieval time.
- **Done when:** ERBB2 shows HGNC:3430 with the file's date; no request leaves the backend for HGNC;
  `FLOW_MAP.md` lists no webapp read of `graph_nodes`.

## 6. Phase 4 — drug lineage *(DSS: a Group and a Join in S1)*

**Built 2026-10-26** in zone `S1 Shortlist` (D15), visual recipes only, managed storage, Parquet. The
existing flags and `compute_drug_evidence_pairs` are not touched.

- **`group_drug_protein_actions`** (Group) reads `drug_protein_edges` and writes `drug_protein_actions`,
  one row per drug × gene, with the drug's recorded actions on the protein concatenated, distinct and
  pipe-separated. Without it the join repeats a drug: 45 drug–gene edges are the same drug with a second
  action (DB00480: inhibitor and modulator), which made 24 records two rows. 7,959 edges → 7,914 rows.
- **`join_drug_evidence_records`** (Join) writes `drug_evidence_records`, one row per pair × drug:
  `drug_disease_edges` ⋈ `drug_protein_actions` on the drug; `graph_nodes` three times, each pre-filtered
  to one node type (disease, gene/protein, drug) because disease ids and NCBI Gene ids are both bare
  integers. **It covers every linked pair, not only candidates:** an inner join to
  `dashboard_candidates` was built first and dropped the same day, so the dataset does not depend on
  the scoring chain and a rebuild of zone 40 (or Phase 5's chain) never reaches it.

  | field | from |
  |---|---|
  | `disease_index`, `gene_index` | `graph_nodes.node_index` (disease, gene/protein) |
  | `drug_id` (DrugBank) | `drug_disease_edges.x_id` |
  | `drug_name` | `graph_nodes.node_name` (drug) |
  | `max_stage` | `drug_disease_edges.display_relation` |
  | `relation` | `drug_disease_edges.relation` |
  | `action_type` | `drug_protein_actions`, pipe-separated |
  | `source_release` | constant `Open Targets Platform 26.06`, a post-join computed column |

  Renames are aliases in the join's top-level column selection; a join condition cannot use a column
  computed on its input, so conditions name the source columns.
- **Builds**, non-recursive and one at a time, so nothing upstream rebuilt: `drug_protein_actions`, then
  `drug_evidence_records` — **86,123 records over 55,270 pairs**, the same pairs as
  `drug_evidence_pairs`; no pair × drug repeated, every drug named. 2,294 records over 1,378 pairs fall
  on candidate pairs.
- **Check**, run read-only on 2026-10-26: grouping the records by pair reproduces `approved_for_disease`
  and `investigational_for_disease` for **all 105,702 pairs of `dashboard_candidates`, zero
  mismatches**. It is not yet an assertion script; adding it to
  `nb6_interrogation_and_close.py` waits on the nb3 library drift, because `push_assertions.py --push`
  overwrites the whole library.
- **Backend.** `GET /api/candidates/drugs?disease=&gene=` reads `drug_evidence_records` through the
  dataset cache and returns the pair's records, most advanced stage first and *stage not recorded* last.
- **Tab.** Drugs & graph lists drug, highest stage for this disease, action on the gene and DrugBank id,
  under the badges; its request is its own, so a failure leaves the badges and the Explorer working.
- **Done:** ERBB2 × HER2+ lists tucatinib (approval, inhibitor) and poziotinib (phase 2, inhibitor),
  read through the route against the live dataset; the check passes over every pair. Not yet deployed.

## 7. Phase 5 — top-5 SHAP *(DSS: new recipes beside the old chain)*

**Today's scoring chain is not edited.** `score_persona_candidates` writes `persona2_scored`, then
`compute_top_shap_drivers_1` → `persona2_scored_shap` → `rank_per_disease`, which sets every rank. Its
`top_shap_drivers` string reaches `dashboard_candidates`, which `nb6` and `nb7` read and the current
webapp serves. Phase 5 builds beside it, in zone `S1 Shortlist` (D15):

- `score_persona_candidates_shap5`: a copy of `score_persona_candidates` (the same saved model
  `hJLGoYn4` and active version, the same input `validation_set_personas_2`, the same background of
  100) with `nbExplanations: 5`, writing `persona2_scored_shap5`.
- `compute_shap_top5` (Python): one row per scored pair, `disease_index`, `gene_index` and
  `shap_top5`, a JSON list of up to five `{feature, shap, value, percentile}`, the percentile taken
  within the disease's pool. It carries `prox_kernel`'s value, the one champion input
  `dashboard_candidates` cannot show (`MISSING_FEATURES` in `backend/routes/candidates.py`), so
  `dashboard_candidates` gains no column. Writes `candidate_shap_top5`.
- Build only these two: one job, `--target persona2_scored_shap5 --target candidate_shap_top5`, each
  non-recursive, so nothing in zone 40 or upstream rebuilds. Record the scoring time (scope §7).
- Checks, read-only, with a script under `tools/` that writes nothing to DSS: every pair's prediction
  in `persona2_scored_shap5` equals `persona2_scored`'s; every pair in `dashboard_candidates` has a
  row in `candidate_shap_top5`; and the share of pairs whose first two drivers match
  `top_shap_drivers` is reported, with examples where they differ. A difference is investigated, not
  patched: a second run need not reproduce the same top two if its background sample differs.
- `GET /api/candidates/drivers?disease=&gene=` feeds the Ranking tab: up to five rows, SHAP sign and
  value, the feature's percentile in this disease (D2).
- The two scoring runs then compute the same predictions twice. Both stay; folding them into one is
  left to the flow migration decision (§11).
- **Done when:** predictions are equal on every pair; no existing recipe or dataset has changed;
  ERBB2 × HER2+ shows five drivers with their percentiles.

## 8. Phase 6 — trials and literature *(DSS: cache folder, pre-fill scenario)*

### Step 1 — search, no LLM

1. Build three queries per corpus from `candidate_identity` (Phase 3) and the pair: `symbol + anchor_name`,
   `symbol + disease_name`, `symbol + up to two safe aliases + anchor_name`. Aliases shorter than four
   characters or matching a common word are excluded (*NEU*, *BRM*). A disease without an anchor uses
   `disease_name`.
2. Run the six calls in parallel through the DSS agent-tool API (`get_project()`), each with a timeout.
3. De-duplicate by NCT_ID or PMID, keeping the best-scoring chunk.
4. Keep a record only if the symbol or an approved alias appears in its passage or title, and drop it
   when the only mention is in a reference list.
5. Return records at once, with `selection: pending`.

### Step 2 — one selection pass (LLM Mesh)

- Input: pair context (symbol, HGNC name, aliases, disease, anchor) and the filtered records (id,
  title, passage, metadata). Passages are wrapped as data, never as instructions.
- Output, schema-validated JSON: up to 5 trials and 5 papers, each with `id`, `role`, `subtype_match`
  (`exact` / `broader` / `other`), a reason of at most 25 words, and `quote`.
- Roles. Trials: `intended_target`, `selection_biomarker`, `contextual_mention`. Papers:
  `functional_evidence`, `association`, `conflicting_finding`, `contextual_mention`.
- Prompt rules: choose only from the given records; quote verbatim; prefer the selected subtype, then
  the anchor disease; never infer efficacy from phase or status; never recommend research direction.
- Backend checks: `id` in the candidate set; enums valid; `quote` a substring of the whole passage
  after whitespace normalisation, never of a sentence split. A failing label is dropped (D4).

### Cache and pre-fill

- Folder `act4_evidence_cache` in zone `S1 Shortlist` (D15), one JSON file per pair:
  `{disease_index}/{gene_index}.json`, holding the queries, raw and filtered records, the selection,
  `retrieved_at` and `selected_at`.
- Versions inside the file (tool config, query builder, prompt, model id); any mismatch is a miss.
- One uvicorn worker (bs-blueprint rule), so a per-pair in-process lock prevents duplicate runs.
- A **Refresh** control re-runs the pair.
- Pre-fill scenario for the HER2+ top 20: 120 Cortex calls (six per pair) and 20 selection calls.

### Budgets

| step | budget | basis |
|---|--:|---|
| searches (6 in parallel) | ≤ 4 s | 2.2 s tool time each, measured |
| selection pass | ≤ 15 s | not yet measured; this phase measures it |
| warm read | ≤ 0.5 s | not yet measured |

**Done when:** a cold ERBB2 or SMARCA2 selection meets both budgets; a warm one is instant; a tool
failure shows inside its tab only; every rendered quote is a substring of its passage.

## 9. Phase 7 — evidence assistant *(DSS: agent)*

- A DSS agent with tools `b6Rpbve`, `4I2L6YL` and `FNxhpfF`, called through the LLM Mesh
  (`agent:<id>`) from `POST /api/assistant`, streaming.
- Every call carries the selected pair, its HGNC identity, top-5 SHAP, drug records and the cached
  evidence records, so most answers need no new search.
- Answer contract: every sourced sentence cites a record (`T1`, `P2`, `D1`, `G`, `M`); a sentence from
  general knowledge is rendered as *not from a retrieved source* (D1); graph answers show the generated
  Cypher; no prescriptive language. No conversation is stored.
- Before acceptance, run ten fixed graph questions and record where text-to-Cypher is directed, ignores
  limits or returns implausible edges.
- **Done when:** the starter questions answer with working citations on ERBB2 and SMARCA2, every
  general-knowledge line is marked, and every graph answer shows its Cypher.

## 10. Phase 8 — verification and switch-over *(DSS: deploy)*

- `npm run check`; a local run over HER2+ with ERBB2, SMARCA2 and one novel gene, plus a disease with
  no family panel; cold and warm timings; forced tool timeouts.
- The user runs `make deploy` from the redesign branch to the second webapp; read-only verification
  there while the current webapp still serves the demo.
- **Switch-over**, when the user chooses: the redesign moves into the original webapp, so its URL and
  any links to it are kept. `app.env` returns to `LIB_NS=target_prioritizer`, `WEBAPP_ID=OlmPX9a` and
  the original display name, and the user runs `make deploy`. No dataset changes. Rollback is a
  `make deploy` from `main`.
- After a grace period agreed with the user, the user deletes the second webapp and its
  `python/target_prioritizer_next/` library folder.
- Regenerate `.index/` and `FLOW_MAP.md` once the new datasets exist.
- `DEC-DEMO-004` and `DEC-DEMO-005` move to `accepted`; `WEBAPP_DESIGN.md` loses its remaining
  *planned* marks.
- **Done when:** the original webapp serves the redesign, and the second webapp and its library
  folder are gone.

## 11. After the redesign — the flow migration decision

The flow migration is not part of the redesign, and no phase above depends on it. After Phase 8 the
user decides whether it runs, in full, in part or not at all, from what the release has shown. Its
plan, and the options that decision weighs, are in
[`../operations/FLOW_MIGRATION_WORKPLAN.md`](../operations/FLOW_MIGRATION_WORKPLAN.md) §1. Whatever
is decided, two things from Phase 0 hold: the boundary rule (D14) governs every new object, and new
objects go in the target zones (D15).
