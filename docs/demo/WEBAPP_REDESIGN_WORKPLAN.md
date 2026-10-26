# Webapp redesign — workplan

> **Lifecycle:** Planning (draft) · **Audience:** webapp implementers and technical reviewers ·
> **Authority:** the phase sequence, the technical design of each phase, and its acceptance criteria ·
> **Update when:** a phase is accepted or re-scoped, or a budget in §8 is measured · **Generated
> dependencies:** none · **Excludes:** the decisions, measurements and target design, which are
> [`WEBAPP_REDESIGN_SCOPE.md`](WEBAPP_REDESIGN_SCOPE.md) and are referenced here by their ids (D1–D15).

**Status: DRAFT — 2026-10-25. Not approved; no phase has started.**

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
| 3 | HGNC identity | — |
| 4 | drug lineage | new dataset and recipes |
| 5 | top-5 SHAP | scoring recipe, rebuild |
| 6 | trials and literature | managed folder, scenario |
| 7 | evidence assistant | agent |
| 8 | verification and release | deploy |
| 9 | flow migration, in its own workplan | see that workplan |

Phases 1–3 need no DSS change and can ship as one release. Phases 4–6 each depend only on Phase 2's
tabs; Phase 7 uses what 3–6 provide. Phase 9 starts only after Phase 8, because its inventory reads
what the released webapp actually reads.

## 2. Phase 0 — decisions and documents

- Two register entries in `DECISION_REGISTER.md`: D1/D4/D5 (assistant, role labels, cache) and
  D9–D11 (the list leads, one evidence page, one disease). The boundary rule (D14) and the target
  zone layout (D15) below are recorded with the second.
- `DEMO_NARRATIVE.md`: act order and the four-acts table.
- `WEBAPP_DESIGN.md`: §3.3 routes, §4 acts table and Acts 1–4 sections, §6 guardrail rows, §8.
- **Done when:** the user approves the doc diff.

**The boundary rule (D14).** It governs every phase from here on, and the flow migration enforces it
on what already exists:

- **Notebooks read only zones 00–31** (after the migration, through the evidence project's exposed
  objects) and recompute anything downstream in their own code. A notebook never reads a serving zone.
- **The webapp backend reads only serving zones** (`S1`–`S4` below).
- **No computed dataset is consumed by both.** Both may depend on the same inputs in zones 00–31;
  neither depends on the other's outputs.

**The target zone layout after zone 40 (D15)**, one zone per function of the new webapp. Datasets
named here exist today unless marked; the flow migration's M1 maps every remaining dataset, and places
each intermediate with its first served consumer.

| zone | serves | endpoint datasets |
|---|---|---|
| `40 Scoring & ranking` | both pages, as the shared core | `persona2_scored`, `persona2_scored_shap` (with `shap_top5`, Phase 5), `top_candidates`, `target_candidates_2`, `candidates_annotated` |
| `S1 Shortlist` | the shortlist | `dashboard_candidates`; `drug_evidence_records` (new, Phase 4); the `act4_evidence_cache` folder (new, Phase 6) |
| `S2 Evidence · graph` | section 1, what the model can see | `graph_node_type_counts`, `graph_relation_counts`, `graph_node_source_counts`, `graph_ppi_provenance`, `graph_label_evidence` |
| `S3 Evidence · reconstruction` | section 2 | `validation_auc_by_disease`, `split_audit_2`, `disease_eligibility`, `hub_bias_meter`, `orthogonality_scatter`, `family_auc_by_family`, `persona_enrichment` |
| `S4 Evidence · family panels` | section 3 | `demo_panel_config`, `family_panel`, `family_panel_metrics`, `family_panel_overlap`, `family_panel_programme`, `family_panel_top50` |

Leaving the main project: `breast_panel_metrics` and the A4 notebook-only datasets (`known_drug_truth`,
`filter_three_axes`, `pool_reachability`) move to the evidence project; `shap_driver_frequency` and
`shap_drivers_long` are expected to be deleted. Both are confirmed in the migration's M1. Zone 20 is
re-zoned into drug annotation, gene annotation, and disease family with split key, without a rebuild.

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

**Done when**

- The root URL opens the shortlist; the sidebar shows two items and Settings.
- Changing the disease on either page changes it on the other; section 2 marks that disease; section 3
  opens its family, or says there is none.
- Every analysis listed in scope §4.3 is reachable; no figure is typed into copy.
- `npm run check` prints `check: ok`; the §1 colour search matches only `ShortlistView.vue` and
  `ActCard.vue`, and the control search matches nothing.

## 4. Phase 2 — the shortlist on existing data

- Split `ShortlistView.vue` (741 lines) into `components/shortlist/`: `CandidateTable`,
  `CandidateHeader`, `OverviewTab`, `RankingTab`, `EvidenceTab` (trials and literature),
  `LineageTab`, `EvidenceInspector` (kit `Sheet`), `AssistantSheet` (hidden until Phase 7).
- Kit parts only: `Tabs`, `Sheet`, `Collapsible`, `Pagination`, `Badge`, `StatusBadge`, `Table`,
  `Skeleton`, `Alert`, `Textarea`. Remove the inline style colours (`seriesVar`) from the moved code.
- `ActCard` stays, because `VisualGraphExplorerCard` wraps it: move its accent tints from computed
  style objects to token classes.
- Overview is a fixed brief from the flags; Ranking shows today's top two drivers until Phase 5;
  Trials and Literature show an empty state until Phase 6; Drugs & graph hosts the existing Explorer
  card and the drug flags until Phase 4.
- *How do we know?* links (scope §4.1).
- Correct the stale 13-disease and 129,253-row copy.
- **Done when:** HER2+ renders live; no badge is a filter; every count shows its cut-off; the links
  land on the right sections; both §1 searches print nothing, which is when the last colour set
  through an inline style leaves the app.

## 5. Phase 3 — HGNC identity

- `backend/services/hgnc.py`: fetch `/fetch/entrez_id/{ncbi_id}`, fall back to symbol and previous
  symbol; 5 s timeout; in-process cache; respect HGNC's rate limit; record retrieval time.
- The NCBI Gene ID is `graph_nodes.node_id` for the gene's `node_index` (ERBB2 = 2064), read once.
- `GET /api/candidates/identity?gene=` feeds the header.
- **Test first:** outbound internet from the DSS webapp backend. Fallback: a dated HGNC snapshot
  dataset.

## 6. Phase 4 — drug lineage *(DSS)*

- New dataset `drug_evidence_records` in zone `S1 Shortlist` (D15; managed storage, Parquet), one
  row per pair × drug, built with visual Join recipes: `drug_disease_edges` ⋈ `drug_protein_edges` on
  the drug, `graph_nodes` for both indexes, restricted to pairs in `dashboard_candidates`.

  | field | from |
  |---|---|
  | `disease_index`, `gene_index` | `graph_nodes` |
  | `drug_id` (DrugBank) | `x_id` |
  | `drug_name` | `graph_nodes.node_name` |
  | `max_stage` | `drug_disease_edges.display_relation` |
  | `relation` | `drug_disease_edges.relation` |
  | `action_type` | `drug_protein_edges.display_relation` |
  | `source_release` | constant `Open Targets Platform 26.06` |

- A check that grouping the records by pair reproduces `approved_for_disease` and
  `investigational_for_disease` exactly. The existing flags are not touched.
- `GET /api/candidates/drugs?disease=&gene=` feeds the Drugs & graph tab.
- **Done when:** ERBB2 × HER2+ lists tucatinib and poziotinib with their stages, and the check passes
  over every pair.

## 7. Phase 5 — top-5 SHAP *(DSS)*

- `score_persona_candidates`: `nbExplanations` 3 → 5. `compute_top_shap_drivers_1`: add a structured
  column `shap_top5` (JSON list of `{feature, value}`); **leave `top_shap_drivers` unchanged**.
  Propagate `shap_top5` and `prox_kernel` to `dashboard_candidates`.
- Rebuild the zone from `persona2_scored`. Scores and ranks must be identical before and after.
- Ranking tab: up to five rows, SHAP sign and value, the feature's percentile in this disease (D2).
- **Done when:** ranks unchanged; ERBB2 shows five drivers.

## 8. Phase 6 — trials and literature *(DSS: cache folder, pre-fill scenario)*

### Step 1 — search, no LLM

1. Build three queries per corpus from HGNC and the pair: `symbol + anchor_name`,
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

## 10. Phase 8 — verification and release

- `npm run check`; a local run over HER2+ with ERBB2, SMARCA2 and one novel gene, plus a disease with
  no family panel; cold and warm timings; forced tool timeouts.
- The user runs `make deploy`; read-only verification afterwards.
- Regenerate `.index/` and `FLOW_MAP.md` once the new datasets exist.

## 11. Phase 9 — flow migration

Carried out in its own workplan, [`../operations/FLOW_MIGRATION_WORKPLAN.md`](../operations/FLOW_MIGRATION_WORKPLAN.md):
a separate evidence project for the notebooks (D13), and the main project's flow after zone 40
rebuilt in the target zones (D15), compared with the old, then retired. It starts after Phase 8.
