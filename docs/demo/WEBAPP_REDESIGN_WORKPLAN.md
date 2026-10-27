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
| 5 | top-5 SHAP | two recipes beside the old scoring chain, two datasets |
| 6 | trials and literature | managed folder, scenario |
| 7 | evidence assistant | a DSS agent and an Agent Hub webapp; the in-app assistant needs none |
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
  `CandidateHeader`, `OverviewTab`, `RankingTab` and `LineageTab`. `SourcesTab` (the Trials and
  Literature tabs) is created in Phase 6 and `AssistantSheet` (kit `Sheet`) in Phase 7, when they have
  records to show; until then the Trials and Literature tabs hold an empty state and no empty shell
  ships.
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

## 7. Phase 5 — top-5 SHAP *(DSS: two recipes beside the old chain)*

**Built 2026-10-26. Today's scoring chain is not edited.** `score_persona_candidates` writes
`persona2_scored`, then `compute_top_shap_drivers_1` → `persona2_scored_shap` → `rank_per_disease`,
which sets every rank. Its `top_shap_drivers` string reaches `dashboard_candidates`, which `nb6` and
`nb7` read. Phase 5 sits beside it, in zone `S1 Shortlist` (D15), managed storage, Parquet:

- **`score_persona_candidates_shap5`** writes `persona2_scored_shap5`: the same saved model `hJLGoYn4`
  (m7-f14, active version), the same input `validation_set_personas_2` and the same payload, with one
  difference, `nbExplanations: 5` (was 3). Created through the Python API, which named it
  `score_validation_set_personas_2` whatever name was passed; it was renamed.
- **`compute_shap_top5`** (Python, project code env) writes `candidate_shap_top5`: `disease_index`,
  `gene_index` and `shap_top5`, a JSON list, strongest |SHAP| first, of five
  `{feature, shap, value, percentile}`. The percentile is the share of the disease's pool the gene is
  stronger than, by the rule `GET /api/candidates/gene` uses (strict inequality; fewer is stronger for
  `prox_closest`), on the scored set's full-precision values. It covers `prox_kernel`, the one champion
  input `dashboard_candidates` cannot show, so `dashboard_candidates` gains no column.
  - On a sample of 720 drivers the percentiles equal `/gene`'s except one near-tie, where
    `dashboard_candidates` stores the value rounded in its last digits.
  - 9.4% of drivers have no value: the gene has no such path, and the SHAP value is the effect of
    that absence. The tab says so rather than showing an empty cell.
- **Builds**, non-recursive and one at a time, so nothing in zone 40 or upstream rebuilt:
  `persona2_scored_shap5` in **8 min 13 s** of wall time (the 3-explanation run takes 8.1–8.2 min, so
  five explanations cost almost nothing), then `candidate_shap_top5` — 105,702 rows, five explanations
  each.
- **Checks**, `python3 tools/check_shap_top5.py`, read-only (streams four datasets with `dku dataset
  download`), passed on 2026-10-26:
  1. every pair's `proba_1` and `prediction` equal `persona2_scored`'s: 105,702 of 105,702;
  2. every pair of `dashboard_candidates` has a top-5 row: no pair missing;
  3. the two strongest drivers match `top_shap_drivers` on **all 105,702 pairs**. Beyond the check,
     the SHAP values on the features both runs explain are identical, and every pair's three stored
     drivers are among its five: the Shapley background was drawn identically, so the two runs named
     the same drivers.
- **Backend.** `GET /api/candidates/drivers?disease=&gene=` reads `candidate_shap_top5` through the
  dataset cache and adds each feature's wording, kind and direction from `feature_glossary.py`. The list
  response no longer carries `top_shap_drivers` or `feature_labels`, which only the parsed drivers read.
- **Tabs.** The shortlist fetches the drivers once per selection and passes the same list to Overview
  (its strongest driver) and *Why this ranking?* (five rows: SHAP sign and value, the percentile).
- The two scoring runs compute the same predictions twice. Both stay; folding them into one is left to
  the flow migration decision (§11).
- **Done:** predictions equal on every pair; no existing recipe or dataset changed; ERBB2 × HER2+ shows
  five drivers, with SHAP and percentile within HER2+: `dwpc_GBGD` +1.30 (99.7), `dwpc_GPGD` +1.13
  (99.1), `ppi_multi_source_frac` +0.71 (70.8), `dwpc_GFGD` +0.67 (98.9), `ppi_adamic_adar` +0.60 (99.3).
  Not yet deployed.

## 8. Phase 6 — trials and literature *(DSS: cache folder, pre-fill scenario)*

**Built 2026-10-26/27 on the preview webapp; not yet deployed or pre-filled.** The code is
`backend/services/pair_sources.py` (search, selection, cache), `backend/routes/sources.py`
(`GET /api/candidates/sources` and `/sources/selection`), `backend/prefill.py` and
`frontend/src/components/shortlist/SourcesTab.vue`, which serves both the Trials and the Literature tab.
Nothing runs when a row is clicked: the search starts when one of the two tabs is first opened for the
pair (D3).

### Step 1 — search, no LLM

1. Three queries per pair: `symbol + anchor`, `symbol + disease_name` and `HGNC name + disease_name`
   (the third replaced `symbol + two safe aliases + anchor` on 2026-10-27; see the table below). The anchor is the disease's family head, the nearest of 137
   Hetionet DO-Slim terms up the MONDO hierarchy (`compute_disease_family_id`; *breast cancer* for HER2+
   and TNBC). A disease without one uses `disease_name`, so its first two queries are the same and it runs two. A safe alias, from HGNC's alias and previous
   symbols, is at least four letters or digits once hyphens are removed and not an English word, which
   excludes *NEU* and *BRM*.
2. The six calls run in parallel through the agent tools `4I2L6YL` (CT.gov, 5 results) and `FNxhpfF`
   (PubMed, 10), within 10 s together: a call still running then is reported as timed out and left to
   finish unread (until Phase 8 the search waited for it). A failing call is reported for its corpus only.
3. De-duplicated by NCT_ID or PMID, keeping the best reranker score. CT.gov chunks are JSON of study
   modules and are flattened to their text, so the model quotes and the check verifies the same text.
4. A record is kept only if the symbol or a safe alias appears in its title, or in its passage outside a
   citation (no *et al.*, DOI, PMID or journal-volume pattern within 150 characters of the mention).

**What was tested and not adopted** (search only, no LLM; 9 pairs over HER2+, TNBC and lung
adenocarcinoma; each returned record checked for the gene, the selected disease and the anchor):

| question | finding | outcome |
|---|---|---|
| Is `symbol + disease_name` the more accurate query? | most disease-specific (97% of papers name the disease) but least gene-specific (44% name the gene, against 82% for `symbol + anchor`); for HER2+ novel genes 0%, because the disease name contains a gene name. It still finds the most records naming both | all three queries kept: each finds records the others miss |
| Does the HGNC full name help (`name + disease_name`)? | as accurate as `symbol + disease_name` alone, but finds different records: swapping it for the alias query raises papers naming gene and disease from 60 to 74 at six searches | **adopted 2026-10-27** in place of the alias query (query version 2); safe aliases still count as mentions in step 4. Re-run over the 21 pre-filled pairs: papers naming the disease 172 → 194, trials kept 72 → 61, papers kept 330 → 300, picks 43 → 36 trials and 94 → 89 papers. The alias query had found trials naming a gene by an older symbol: CTNNB1 lost all 3 trial picks, TP53 kept 2 trials of 5 |
| Can Cortex filter natively? | the plugin tool exposes no filter. A Knowledge Bank over the existing service (DSS 15.0+) passes filters, but the services filter only on trial type, status, phase, sponsor, sex and bibliographic fields, all `TEXT` with no substring match | not used: nothing filters on gene or disease |
| PubMed at 5 results per call? | results 6–10 are as relevant as 1–5 (68% name the gene in both), so 5 halves the relevant papers (14.6 → 7.8 per pair) and did not speed up ERBB2's selection | kept at 10 |

### Step 2 — selection (LLM Mesh)

- **Two calls in parallel**, one for the trials and one for the papers, each over the passages trimmed to
  500 characters either side of every gene mention (excerpts joined by " … "; a record kept for a title
  mention sends its first 1,000 characters). Model `openai:bs-llm-connection:gpt-5.6-terra`, the one
  graph search uses; strict JSON schema output.
- Output per corpus: up to 5 records, each with `id`, `role`, `subtype_match` (`exact` / `broader` /
  `other`), a reason (cut to 25 words) and `quote`. Roles as planned: trials `intended_target`,
  `selection_biomarker`, `contextual_mention`; papers `functional_evidence`, `association`,
  `conflicting_finding`, `contextual_mention`.
- Prompt rules as planned, plus: a quote comes from within one excerpt. Records are wrapped in
  `<record>` tags as data.
- Backend checks, unchanged: `id` among the records sent; enums valid; no duplicate; `quote` a
  substring of the record's **full** passage after whitespace normalisation. A failing label is dropped
  and counted on the page. A corpus whose call fails is named in `errors` and its records shown
  unlabelled; the other corpus keeps its labels.

**Why two calls, not one, and not an agent** (2026-10-27; ERBB2 and SMARCA2 × HER2+, EGFR × lung
adenocarcinoma, RAD50 × TNBC; two runs each; end-to-end time; every option's picks through the same
backend check):

| design | median | slowest | runs over 15 s | picks passing the check |
|---|--:|--:|--:|--:|
| one call over whole passages (first build) | 14.9 s | 21.0 s | 4 of 8 | 54 of 59 |
| **two calls in parallel over trimmed passages (adopted)** | **8.9 s** | **13.2 s** | **0 of 8** | 54 of 61 |
| structured agent: 6 branches of search → LLM, merged in Python | 12.4 s | 17.2 s | 1 of 8 | 50 of 67 |
| structured agent: 6 searches → Python filter → one LLM | 17.9 s | 26.4 s | 6 of 8 | 48 of 56 |

The selection step alone fell from a median 12.2 s (max 18.3 s) to 6.4 s (max 10.5 s). The
branch-per-query agent quoted raw CT.gov JSON that the check could not find, picked twice a record not
naming the gene, and ranked nothing across branches; the one-LLM agent added its own runtime to the same
call. Picks are themselves variable: the first build shared 55% of its picks with its own second run, and
the adopted design 61% with the first build's. Phase 7's assistant does not call this selection; it
reads the pair's cache (§9).

### Cache and pre-fill

- Folder `act4_evidence_cache` (`CB9xqCGg`) in zone `S1 Shortlist` (D15), managed storage, one JSON file
  per pair at `{disease_index}/{gene_index}.json`: context, queries, the records by corpus, the
  selection, `retrieved_at` and `selected_at`.
- `VERSIONS` in the file (each tool's `max_documents`, query rules, filter, prompt, model); any
  difference is a miss. `max_documents` is set in DSS, so the stamp must change by hand when it does.
- A per-pair lock stops two requests running the same pair (one uvicorn worker). **Refresh** re-runs the
  search and the selection and overwrites the file.
- Scenario `prefill_evidence_cache`, inactive, no trigger: one Python step that imports
  `backend/prefill.py` from the **preview** webapp's library code (`target_prioritizer_next`) and fills
  HER2+ ranks 1–20 as the shortlist opens, plus SMARCA2 (ERBB2 is rank 14): 21 pairs. A pair with a
  current file is read, not re-run; a failure is reported per pair and turns the run red. It runs only
  after a deploy that carries `prefill.py`, and at the Phase 8 switch-over its `LIB_NS` and `APP_PREFIX`
  must follow the live webapp's.

### Budgets, measured

| step | budget | measured |
|---|--:|---|
| searches (6 in parallel) | ≤ 4 s | 2.4–3.9 s over 26 runs; one cold run 8.4 s |
| selection | ≤ 15 s | ERBB2 6.3, 8.1, 11.4 s; SMARCA2 5.0, 5.5 s; slowest of the 8 comparison runs 10.5 s |
| warm read | ≤ 0.5 s | 0.12–0.16 s from the folder |

**Done when:** a cold ERBB2 or SMARCA2 selection meets both budgets — **met** (ERBB2 3.2 s + 11.4 s,
2026-10-27); a warm one is instant — **met** (0.16 s); a tool failure shows inside its tab only — **by
design**, not exercised live; every rendered quote is a substring of its passage — **met** (10 of 10 for
ERBB2). Deployed and pre-filled 2026-10-27, and pre-filled again after the name query replaced the alias
query (4 min 26 s for 21 pairs; search ≤ 2.7 s and selection ≤ 11.6 s per pair).

## 9. Phase 7 — evidence assistant *(DSS: an agent and an Agent Hub webapp)*

**Revised 2026-10-27.** Two surfaces over the same three tools — graph search `b6Rpbve`, CT.gov `4I2L6YL`
and PubMed `FNxhpfF` — for two jobs:

| | in-app assistant (7a) | Agent Hub (7b) |
|---|---|---|
| job | answer questions about **the selected pair**, with every answer checked | open exploration of the graph and the literature |
| where | a panel on the shortlist's candidate card | Agent Hub's own webapp, opened from the card in a new tab |
| runs | a tool-calling loop in the webapp backend (bs-blueprint's `agent_loop.py` pattern) | a DSS tool-using agent, chatted with through Agent Hub |
| knows the pair | yes: the backend sends it with every question | no: the user names the gene and disease |
| answer contract (D1) | enforced by the backend after each answer | asked for in the agent's prompt only |
| graph results | names and counts, with the generated Cypher | Agent Hub's graph view, if the installed version renders it |

**Why not one DSS agent for both** (findings, 2026-10-27):
- **Agent Hub cannot be embedded with the pair.** Its routes are its home page, the agent library,
  `/conversations/:id`, its dashboard and its admin pages; nothing in the URL selects an agent, fills in a
  question or passes context. Its "allowed embed origins" setting controls which links render *inside*
  its answers, not who may embed it. Agent Hub renders its own answers, so the backend cannot check them.
- **A DSS agent called from the backend** may not pass its tools' outputs (the generated Cypher, the
  records it retrieved) through to the caller, and its tools' outputs cannot be trimmed: graph search
  returned up to 191 KB per answer. A loop in the backend sees and trims every tool output.
- **bs-blueprint builds assistants this way**: its starter's chat and Case manager blocks run the loop
  in the backend over the LLM Mesh and have no Agent Hub integration.

### Graph search, tested (ten fixed questions, 2026-10-27)

Asked of `b6Rpbve` about ERBB2, SMARCA2 and HER2+, and checked against `graph_edges`: **all ten answers
correct**, nothing extra or missing (counts, lists and a yes/no). Four behaviours shape both surfaces:
- **No requested limit reaches the query** (0 of 4): "at most 5" returned 107 proteins.
- **Interaction edges come back twice**, because they are stored both ways (214 rows for 107 partners).
- **Seven of ten queries used `->`**, always in the direction the edge is stored, so they were correct; a
  query against the stored direction would return no rows, which a yes/no question reads as "no".
- Answers took 2.0–7.4 s and returned up to **191 KB** of nodes and edges. The tool's description is
  "no description provided", so a model calling it learns nothing about the graph from the tool itself.

### 7a — the in-app assistant

- **`POST /api/assistant`**, streamed as server-sent events by FastAPI's own `StreamingResponse`
  (`backend/routes/assistant.py`), so no SSE library is added: the body carries the pair, the question
  and the conversation so far. **Nothing is stored**: the page holds the history and loses it on reload
  or when another pair is selected.
- **The loop** (`backend/services/assistant.py`): the LLM Mesh model `gpt-5.6-terra` through the LLM
  Mesh's native tool calling (`dataiku` completion with `tools` set, streamed), calling the three DSS
  agent tools directly; no LangChain. Each round's tool calls run in parallel. Limits, set after the
  tests below:
  - at most 6 tool rounds and 8 searches per answer; a search past the budget returns an error the
    model reads;
  - 25 s per search and 45 s per answer, after which the model answers with what it has, without tools;
  - graph searches run one at a time, because concurrent calls to `b6Rpbve` returned no output;
  - the prompt asks for one relationship, or one chain, per graph search, and never one search per
    item of an earlier result;
  - a search repeated unchanged within an answer reuses the first result and does not count (Phase 8).
  The graph, search and wording rules live in `backend/services/agent_rules.py`, which builds both this
  prompt and the Agent Hub agent's (7b), so the two cannot drift apart.
  Every tool output is trimmed before the model reads it: graph search to its Cypher plus the distinct
  nodes by type and the row count (at most 50 names per type); a Cortex search to id, title and the text
  around the gene's mentions, as Phase 6 sends. A tool that returns no output counts as a failed call.
- **What the model is told with every question**: the pair, its HGNC identity, its top-5 SHAP drivers
  (`M`), its drug records (`D1…`), the Phase 6 trials and papers from the cache (`T1…`, `P1…`; none if the
  pair is not cached), a short graph schema (node labels, edge tables, which are stored both ways), and
  the answer contract.
- **The answer contract, checked by the backend when the answer is complete:**
  - a sourced sentence cites `T…`, `P…`, `D…`, `M`, a graph result `G1…` from this answer, or an NCT or
    PubMed id retrieved during this answer;
  - a citation that resolves to nothing is removed and its sentence marked;
  - a sentence tagged `[GK]`, or with no citation, renders as *not from a retrieved source* (D1);
  - every graph result shows its Cypher;
  - prescriptive phrases (*"you should"*, *"we recommend"*, *"the next target"*) are flagged.
- **Events**: text as it arrives, each tool call as it starts and ends, then one checked answer that
  replaces the streamed text.
- **Panel** (`AssistantSheet`, a kit `Sheet` opened from the candidate card): four starter questions
  built from the pair — what is known about the gene in this disease; which drugs act on it and for which
  diseases; how it connects in the graph to the genes already linked to the disease; which trials select
  patients by it — and a free question box. Each sentence shows its citations (trials and papers link
  out), the *not from a retrieved source* mark, or an unresolved or prescriptive flag; each graph result
  opens to its names and its Cypher.
- No new dependency: the loop uses the `dataiku` client and FastAPI already in the code env.

**Measured, 2026-10-27** (the four starter questions on ERBB2 and SMARCA2 × HER2+, run through the
service, four runs as the limits were set):

| run | change before it | slowest answer | what went wrong |
|---|---|---|---|
| 1 | first build | 111 s | compound graph queries: one returned 609 rows and exceeded the tool's output limit |
| 2 | one relationship per graph search | 95 s | one answer made 24 searches, one per drug, in sequence |
| 3 | parallel calls, 8-search budget, time limits | 28.8 s | 20 of those 24 calls refused by the budget, answer still completed; concurrent graph searches returned no output |
| 4 | graph searches one at a time | **24.7 s** | none |

Run 4: answers took 2.9–24.7 s, with 0 to 4 searches each; 0 tool failures, 0 unresolved citations and
0 prescriptive flags over 25 sentences, of which 4 were marked general knowledge. Two answers needed
no search: they answered from the pair's context (drivers, drug records, cached trials and papers).
**The check verifies citations, not truth.** Three cases from run 4:
- In the ERBB2 drug answer, "the graph identifies six ERBB2-targeting drugs" read a query that kept only
  drugs with a recorded indication, so it left out poziotinib, which the next sentence names from the
  drug records. The sentence cited nothing, so it was marked general knowledge although it came from the
  graph.
- In the SMARCA2 trials answer, a trial written as a list item with its NCT id in bold, not in brackets,
  was marked general knowledge: the check reads bracketed citations only.
- The same answer that miscounted also ran one graph search twice, unchanged; searches are not
  deduplicated within an answer (they are since Phase 8).

The assistant does not call Phase 6's selection pass as a tool; it reads the pair's cache, so an
uncached pair gets no `T…` or `P…` references and searches CT.gov and PubMed itself.

### 7b — the DSS agent and Agent Hub

- **Agent** `target_evidence_agent` (`QvUvQbzB`) in `DEMO_TARGET_IDENTIFICATION`: a visual agent
  (`TOOLS_USING_AGENT`) with the three tools and `gpt-5.6-terra`, interaction logging off. Its prompt is
  `agent_rules.agent_prompt()` — the in-app assistant's graph, search and wording rules, with NCT, PMID
  and `[Graph]` citations — set with `python -m backend.services.agent_rules` and `dku agent
  set-prompt`. Tested in DSS on 2026-10-27: a graph question in 14 s (one search, Cypher shown, every line
  cited), a literature question in 19 s (3 PMIDs, and it said no HER2+-specific paper was found), and a
  question naming no gene in 1.5 s (it asked for one). It replaced `target_evidence_assistant`
  (`fPXQIUJr`), a structured agent whose one loop block added nothing to a visual agent, deleted the
  same day.
- **Agent Hub webapp** `bFyW6D2` in `DEMO_TARGET_IDENTIFICATION`, created from the `agent-hub` plugin.
  Inside a container Agent Hub refuses SQLite, so it stores its data, **conversations included**, in the
  PostgreSQL connection `local_dku_pg` under the table prefix `agenthub_`. The instance's plugin is now
  **1.7.2**, which carries the graph view (`GraphArtifactDisplay`) found in the source; whether it shows
  graph search results as a graph is checked in the browser. The user enables the agent in Agent Hub's
  admin settings.
- **Link**: *Explore in Agent Hub* on the candidate card opens the Agent Hub webapp in a new tab, at its
  home page; its address comes from `app.env` (`VITE_AGENT_HUB_PROJECT_KEY`, `VITE_AGENT_HUB_OBJECT_ID`
  = `bFyW6D2_agent-hub`), built as the Graph Explorer's is. Empty values hide the link.

**Done when:**
- 7a: the four starter questions on ERBB2 and SMARCA2 × HER2+ answer with citations that all resolve;
  every uncited sentence is marked; every graph result shows its Cypher; a tool failure shows in the
  panel and the answer still completes; answers stay under 30 s. *Met in the service test (run 4, and
  run 3 for tool failures); deployed to the preview webapp 2026-10-27, not yet tried in the browser.*
- 7b: the agent answers a graph question and a literature question in Agent Hub, and the card's link
  opens it; whether graph results render as a graph is recorded for 1.7.2. *The agent answers both in
  DSS and Agent Hub uses it; the link and the graph view await the browser check.*

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

### Verification, 2026-10-27

A local run against the preview's datasets over four pairs: ERBB2 and SMARCA2 × HER2+ (pre-filled),
NRAS × HER2+ (a novel gene at rank 21, outside the pre-fill) and JAK2 × rheumatoid arthritis (no family
panel). Every route answered without error, and `npm run check` was clean.

| pair | Trials and Literature, first visit | second visit | drug question (final run) |
|---|---|---|---|
| ERBB2 | pre-filled, 0.16 s | 0.13 s | 36.7 s, 2 searches |
| SMARCA2 | pre-filled, 0.16 s | 0.14 s | 9.3 s, 1 search |
| NRAS | 3.2 s search + 6.4 s selection | 0.16 s | 8.8 s, 1 search |
| JAK2 × rheumatoid arthritis | 2.8 s + 9.2 s | 0.16 s | 10.0 s, 1 search |

*Why trust the list* answered in under 6 s per route once the backend was warm; `/api/calibration`
takes 17.5 s on a cold backend and 0.3 s after, and `/api/evidence` 5.7 s every time.

**Forced failures:** one corpus's selection failing shows its error in its own tab and keeps the other's
picks; every assistant search timing out (forced to 1 s) still completes the answer (32.9 s, 5 failed
searches shown, the answer saying the graph could not be read).

**Two defects found and fixed:**
- **The search timeout did not bound the wait.** Leaving the thread pool's `with` block waited for every
  call, so a forced 1 s timeout returned after 2.7 s and a hung search would have held the tab. The pool
  now shuts down without waiting: 1.0 s against 1 s.
- **Drug questions took 44–46 s** (ERBB2, JAK2): the model repeated its first graph search, then searched
  once per drug until the 8-search budget ran out and the 45 s limit forced an answer. With repeats
  reused and the per-item rule in the prompt, the same questions took 10–27 s with one or two searches.
  The ERBB2 answer still varies (11.3, 11.7 and 48.2 s in three runs): in the slow run the model spent
  17.5 s before its first search, then searched again for all 23 drugs because the drug-and-indication
  chain returns only the 6 with an indication. The variance is the model's own reasoning time.

**Still open before the switch-over:** the browser checks of the Agent Hub link and graph view.

## 11. After the redesign — the flow migration decision

The flow migration is not part of the redesign, and no phase above depends on it. After Phase 8 the
user decides whether it runs, in full, in part or not at all, from what the release has shown. Its
plan, and the options that decision weighs, are in
[`../operations/FLOW_MIGRATION_WORKPLAN.md`](../operations/FLOW_MIGRATION_WORKPLAN.md) §1. Whatever
is decided, two things from Phase 0 hold: the boundary rule (D14) governs every new object, and new
objects go in the target zones (D15).
