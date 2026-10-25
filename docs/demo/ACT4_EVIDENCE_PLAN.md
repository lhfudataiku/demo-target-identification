# Act 4 evidence review plan

> **Lifecycle:** Planning (draft) · **Audience:** webapp implementers and technical reviewers ·
> **Authority:** the agreed scope, decisions, phase sequence and acceptance criteria for turning Act 4
> from a ranked list into a candidate evidence review · **Update when:** a decision in §2 changes, a
> phase is accepted, or a measurement in §3 is superseded · **Generated dependencies:** none ·
> **Excludes:** current deployed behaviour, which stays governed by
> [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md), [`../../webapp/README.md`](../../webapp/README.md) and
> [`../../webapp/DEPLOYMENT.md`](../../webapp/DEPLOYMENT.md) until each phase is implemented and verified.

**Status: DRAFT — 2026-10-23. Not approved; nothing in DSS or the webapp has changed.** The revised
design review (§4) is a static page built with `bs-blueprint` and `@dataiku/ea-ui-kit` over a live
snapshot taken the same day. It is shared separately and not committed; Phase 1 builds the design in
the webapp itself, so no second copy of Act 4 lives in the repository.

## 1. Summary

Act 4 today answers *"does this list look right?"* and *"which features moved this gene?"*. The
proposal adds the question a scientist asks next: *"what does the outside evidence say about this
gene in this disease, and where does each claim come from?"*

Five sources answer it, each kept separate on screen:

| source | what it is | how it is reached |
|---|---|---|
| Model explanation | top-5 SHAP contributions and the within-disease percentile of those features | `dashboard_candidates` (after Phase 4) |
| Gene identity | HGNC approved name, aliases, location, cross-references | HGNC REST, by NCBI Gene ID |
| Drug lineage | each drug behind the approved / in-trial badges, with its stage and action | new dataset `drug_evidence_records` |
| Clinical trials | ClinicalTrials.gov passages for this pair | DSS agent tool `4I2L6YL` (Cortex) |
| Literature | PubMed open-access passages for this pair | DSS agent tool `FNxhpfF` (Cortex) |

An evidence assistant (Phase 6) answers free questions over the same sources plus the graph search
tool `b6Rpbve`.

## 2. Decisions taken

Agreed in discussion on 2026-10-23. D1, D4 and D5 reverse rules currently stated in
`WEBAPP_DESIGN.md` §8, so they need one register entry (§8 below) before any code lands.

| id | decision | consequence |
|---|---|---|
| D1 | The assistant may use the graph, CT.gov and PubMed tools and HGNC, and cite them. It may also answer from the LLM's general knowledge, **but such claims are marked "not from a retrieved source" and never rendered as citations** | reverses §8 *"No LLM anything"* for this one surface |
| D2 | *Why this ranking?* shows the **top 5 SHAP contributions**, and only those features, each with its within-disease percentile | scoring recipe change and rebuild (Phase 4) |
| D3 | Trials and literature are retrieved **on demand for the selected pair only**: direct searches, then **one LLM selection pass**. No agent loop, no batch over all pairs | Phase 5 design, §6 |
| D4 | That pass also assigns each record a **role label**, and every label must carry a quote the backend verifies against the passage. A label that fails the check is dropped; the record stays, unlabelled | first LLM-derived labels in the app |
| D5 | Results are **cached per (disease, gene) pair in a DSS managed folder** | reverses §8 *"No writes to DSS"* for this cache |
| D6 | A scenario **pre-fills the cache for the HER2+ top 20** before a demo | one scenario, run by the user |
| D7 | Drug lineage comes from a **new long dataset built with visual recipes**, not from text-to-Cypher | Phase 3; no Part 1 change |
| D8 | The approved and in-trial badges stay **separate and never filterable**; the liability badge stays | departs from the blueprint, keeps §6 |

## 3. What exists today (measured 2026-10-23)

**Data.** `dashboard_candidates` holds **105,702 rows over 12 diseases**. `candidates.py`'s docstring
says 129,253 rows over 13 diseases and the Act 4 disease tooltip says 13; both are stale and Phase 1
corrects them. HER2-positive breast carcinoma (`disease_index` 48537) has a pool of 12,272. Its live
funnel is 12,272 → novel 11,673 → tractable 7,950 → not secreted 7,273 → rank ≤ 200 → 38; the Act 4
table in `WEBAPP_DESIGN.md` reads 7,951 and 7,274, one higher at both steps.

**SHAP.** `score_persona_candidates` computes Shapley explanations with `nbExplanations: 3` and a
background of 100. `compute_top_shap_drivers_1` keeps the top **two** as a rendered string
(`top_shap_drivers`), which Act 2's `shap_driver_frequency` folds into exactly two slots. Top 5 is not
available anywhere in the flow today.

**Drug flags.** The lineage, traced through both projects:

```
Open Targets Platform 26.06 (ChEMBL drug layer)
 └ extract_drug_ot [DEMO_KG_LS, Python]
     ├ raw_drug_indication (drugbank_id, mondo_id, max_stage)
     │   └ harmonize_drug_disease [Prepare]
     │       relation = indication if max_stage ∈ {APPROVAL, PREAPPROVAL}, else drug_investigated_for
     │       display_relation = max_stage                    → drug_disease_edges (40,044 rows)
     └ raw_drug_protein (drugbank_id, ensg, action_type)
         └ join_dp_target → join_dp_genes → …              → drug_protein_edges (7,959 rows)
                                                              display_relation = action type
 ⇒ synced into DEMO_TARGET_IDENTIFICATION
 └ compute_drug_evidence_pairs [Python]  drops drug, stage and action; keeps two 0/1 flags
 └ join_dashboard_annotations [Join] → finalize_dashboard_candidates [Prepare] → dashboard_candidates
```

Everything the lineage tab needs survives upstream. Rebuilding the per-drug records locally from the
snapshot reproduces both flags **for all 12,272 HER2+ pairs with zero mismatches**.

Two facts the UI must carry:

- *In trials* is every non-approval stage: Phase 2 (35% of edges), Phase 3 (18%), Phase 1 (11%),
  **UNKNOWN (10%, 4,068 edges)**, and failed programmes.
- **The link is exact-node, not hierarchical.** ERBB2 × HER2+ has two records: tucatinib (APPROVAL)
  and poziotinib (PHASE_2). Lapatinib and neratinib target ERBB2 but their approvals are recorded on
  *breast cancer* (MONDO 7254), not on the HER2+ subtype node, so they do not count. Trastuzumab and
  pertuzumab have no drug–protein edge at all. "No link in snapshot" therefore never means "no drug".

**Tools** (`DEMO_TARGET_IDENTIFICATION`):

| id | name | config | returns |
|---|---|---|---|
| `b6Rpbve` | graph search | Kuzu folder `ytvuniN8`, LLM `openai:bs-openai:gpt-5.6-terra` | `cypher_query`, nodes, edges, table |
| `4I2L6YL` | Cortex – CTgov | 5 chunks per call | NCT_ID, title, status, phases, conditions, sponsor, URL, chunk |
| `FNxhpfF` | Cortex – Pubmed (OA commercial subset) | 10 chunks per call | PMID, DOI, title, URL, chunk |

Each Cortex call takes about **2.2 s** of tool time (trace). Graph search wrote a **directed** query
(`->`) and ignored *"at most 5"* (24 nodes returned) on its one test, so it stays out of the lineage tab.

## 4. The revised design

The design review page (`act4-design-review.html`, shared outside the repository) revises the
2026-10-22 blueprint. What changed and why:

| blueprint | revision | reason |
|---|---|---|
| one "Drug context" pill | separate *approved* and *in trials* badges, plus *liability* | §6: never OR'd, never filtered |
| fixed disease | `SelectField` of the 12 diseases | the act is "open a disease you know" |
| "30 of 30 match" | every count carries its rank cut-off | §6, §10.3 |
| three SHAP rows, illustrative | up to five SHAP rows, live percentiles | D2 |
| "Drug A" schematic | per-drug records: name, stage, relation, action, source release | D7 |
| placeholder trials and papers | real snapshot records with role, verified quote, retrieval time | D3, D4 |
| simulated assistant | grounded answers; general-knowledge lines visibly marked | D1 |
| — | Graph & lineage keeps the five Visual Graph Explorer presets | existing contract |

Role labels and assistant replies in the review page are **written for the design**, not produced by
the selection pass, and the page says so where they appear. Ranks, flags, features, HGNC fields, drug
records and retrieved trial and paper records are from the 2026-10-23 snapshot.

## 5. Phases

Each phase leaves `npm run check` printing `check: ok` and is reviewed before the next starts. Phases
marked **DSS** change the live project and need the user's approval at the time; the user runs builds,
scenarios and `make deploy`.

### Phase 0 — decisions and documents

- Register entry for D1, D4 and D5 (§8). Amend `WEBAPP_DESIGN.md` §3.3 (routes), Act 4 table, §6
  (new guardrail rows) and §8.
- **Done when:** the user approves the doc diff.

### Phase 1 — Act 4 in the new layout, existing data only

- Split `ShortlistView.vue` (741 lines) into `components/shortlist/`: `CandidateTable`,
  `CandidateHeader`, `OverviewTab`, `RankingTab`, `TrialsTab`, `LiteratureTab`, `LineageTab`,
  `EvidenceInspector` (kit `Sheet`).
- Kit parts only: `Tabs`, `Sheet`, `Collapsible`, `Pagination`, `Badge`, `StatusBadge`, `Table`,
  `Skeleton`, `Alert`, `Textarea`. Remove the inline style colours (`seriesVar`) from the moved code.
- Overview is a fixed brief from the flags; Ranking shows today's top-2 drivers until Phase 4; Trials
  and Literature show an empty state; Lineage hosts the existing Explorer card.
- Correct the stale 13-disease and 129,253-row copy.
- **Done when:** HER2+ renders live, no badge is a filter, every count shows its cut-off.

### Phase 2 — HGNC identity

- `backend/services/hgnc.py`: fetch `/fetch/entrez_id/{ncbi_id}`, fall back to symbol and previous
  symbol; 5 s timeout; in-process cache; respect HGNC's rate limit; record retrieval time.
- The NCBI Gene ID is `graph_nodes.node_id` for the gene's `node_index` (ERBB2 = 2064), read once.
- `GET /api/candidates/identity?gene=` feeds the header.
- **Risk to test first:** outbound internet from the DSS webapp backend. Fallback: a dated HGNC
  snapshot dataset.

### Phase 3 — drug lineage *(DSS)*

- New dataset `drug_evidence_records` (managed storage, Parquet), one row per pair × drug, built
  with visual Join recipes: `drug_disease_edges` ⋈ `drug_protein_edges` on the drug, `graph_nodes`
  for both indexes, restricted to pairs in `dashboard_candidates`.

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
- `GET /api/candidates/drugs?disease=&gene=` feeds the Lineage tab.
- Out of scope without a Part 1 change: ChEMBL ID, mechanism text, source references.
- **Done when:** ERBB2 × HER2+ lists tucatinib and poziotinib with their stages, and the check passes
  over every pair.

### Phase 4 — top-5 SHAP *(DSS)*

- `score_persona_candidates`: `nbExplanations` 3 → 5. `compute_top_shap_drivers_1`: add a structured
  column `shap_top5` (JSON list of `{feature, value}`); **leave `top_shap_drivers` unchanged** so Act 2
  does not move. Propagate `shap_top5` and `prox_kernel` to `dashboard_candidates`.
- Rebuild the zone from `persona2_scored`. Scores and ranks must be identical before and after; check
  that on the rebuilt dataset.
- Ranking tab: up to five rows, SHAP sign and value, percentile for that feature in this disease.
- **Done when:** ranks unchanged, Act 2's driver-frequency card unchanged, ERBB2 shows five drivers.

### Phase 5 — trials and literature *(DSS: cache folder, pre-fill scenario)*

Detailed in §6. Endpoints `GET /api/candidates/evidence/search` and
`POST /api/candidates/evidence/select`, a managed folder `act4_evidence_cache`, the pre-fill scenario.

- **Done when:** a cold ERBB2 or SMARCA2 selection shows records within the search budget and labels
  within the selection budget; a warm one is instant; a tool failure shows inside its tab only;
  every rendered quote is a substring of its passage.

### Phase 6 — evidence assistant *(DSS: agent)*

Detailed in §7.

- **Done when:** the three starter questions answer with working citations on ERBB2 and SMARCA2,
  every general-knowledge line is marked, and every graph answer shows its Cypher.

### Phase 7 — verification and release

- `npm run check`; a local run over HER2+ ERBB2, SMARCA2 and one novel gene; cold and warm timings;
  forced tool timeouts. The user runs `make deploy`; read-only verification afterwards.
- Regenerate `.index/` and `FLOW_MAP.md` after the new datasets exist.

## 6. Retrieval design (Phase 5)

### Why queries must lead with the gene

Measured on 2026-10-23 with the gene-mention check below:

| query | CT.gov records mentioning SMARCA2 | PubMed records mentioning SMARCA2 |
|---|--:|--:|
| `SMARCA2 HER2-positive breast carcinoma` | 0 of 5 | 0 of 8 |
| `SMARCA2 breast cancer` | 1 of 5 | 7 of 7 |
| `SMARCA2 BRM SWI/SNF ATPase breast` | 2 of 3 | 8 of 8 |

The HER2+ disease name is itself a gene name, so it outweighs the candidate. Using the family anchor
(`anchor_name`, *breast cancer*) and the HGNC aliases fixes it. CT.gov is genuinely thin for SMARCA2,
which the tab must say plainly rather than pad.

### Step 1 — search (no LLM)

1. Build three queries per corpus from HGNC and the pair:
   `symbol + anchor_name`, `symbol + disease_name`, `symbol + up to two safe aliases + anchor_name`.
   Aliases shorter than four characters or matching a common word are excluded (*NEU*, *BRM*).
   When a disease has no anchor, `disease_name` is used.
2. Run all six calls in parallel through the DSS agent-tool API (`get_project()`), each with a timeout.
3. De-duplicate by NCT_ID or PMID, keeping the best-scoring chunk and the other chunk positions.
4. Keep a record only if the gene symbol or an approved alias appears in its passage or title, and
   drop it when the only mention sits in a reference list. PubMed chunks include bibliographies: three
   of the 24 gene-mentioning ERBB2 and SMARCA2 papers matched on a cited title alone.
5. Return records immediately, with `selection: pending`.

The label check is a plain substring test on the whole passage, never on a sentence split.
CT.gov eligibility criteria are bullet lists without full stops, so a sentence splitter misses
quotes such as *"exposure to SMARCA2 (BRM) inhibitor(s) and/or degrader(s)"* (NCT06561685).

### Step 2 — one selection pass (LLM Mesh)

- Input: pair context (symbol, HGNC name, aliases, disease, anchor) and the filtered records
  (id, title, passage, metadata). Passages are wrapped as data, never as instructions.
- Output, schema-validated JSON: up to 5 trials and 5 papers, each with `id`, `role`,
  `subtype_match` (`exact` / `broader` / `other`), a reason of at most 25 words, and `quote`.
- Roles. Trials: `intended_target`, `selection_biomarker`, `contextual_mention`. Papers:
  `functional_evidence`, `association`, `conflicting_finding`, `contextual_mention`.
- Prompt rules: choose only from the given records; quote verbatim; prefer the selected subtype, then
  the anchor disease; never infer efficacy from phase or status; never recommend research direction.
- Backend checks: `id` in the candidate set, enums valid, `quote` a substring of the passage after
  whitespace normalisation. A failing label is dropped and the record shown unlabelled.

### Cache

- Folder `act4_evidence_cache`, one JSON file per pair: `{disease_index}/{gene_index}.json`.
- Key versions inside the file: tool config version, query-builder version, prompt version, model id.
  Any mismatch is a miss.
- Contents: queries sent, raw records, filtered records, selection, `retrieved_at`, `selected_at`.
- One uvicorn worker (bs-blueprint rule), so a per-pair in-process lock prevents duplicate runs.
- A **Refresh** control re-runs the pair and overwrites the file.

### Runtime budget

| step | budget | basis |
|---|--:|---|
| searches (6 in parallel) | ≤ 4 s | 2.2 s tool time each, measured |
| selection pass | ≤ 15 s | not yet measured; Phase 5 measures it |
| warm read | ≤ 0.5 s | not yet measured |

Records appear after the search step; labels fill in when selection returns.

### Pre-fill

A Python scenario step calls the same service for the HER2+ top 20: 120 Cortex calls (six per pair)
and 20 selection calls. The user runs it before a demo.

## 7. Evidence assistant (Phase 6)

- A DSS agent with tools `b6Rpbve`, `4I2L6YL` and `FNxhpfF`. The webapp calls it through the LLM
  Mesh (`agent:<id>`) from `POST /api/assistant`, streaming.
- Every call carries the selected pair, its HGNC identity, top-5 SHAP, drug records and the cached
  evidence records, so most answers need no new search.
- Answer contract: every sourced sentence cites a record (`T1`, `P2`, `D1`, `G1`, `H`); a sentence
  from general knowledge is prefixed and rendered as *not from a retrieved source*; graph answers
  show the generated Cypher; no prescriptive language.
- Before Phase 6 is accepted, run a fixed set of ten graph questions and record where text-to-Cypher
  is directed, ignores limits or returns implausible edges.
- No conversation is stored.

## 8. Documentation impact

| document | change |
|---|---|
| [`../decisions/DECISION_REGISTER.md`](../decisions/DECISION_REGISTER.md) | one entry: an evidence-grounded assistant and LLM role labels in Act 4, with a DSS cache (D1, D4, D5) |
| [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) | §3.3 routes, Act 4 card table, §6 guardrail rows, §8 |
| [`../../webapp/README.md`](../../webapp/README.md), [`../../webapp/DEPLOYMENT.md`](../../webapp/DEPLOYMENT.md) | new settings (tool, agent, folder, model ids) and the pre-fill step |
| [`../operations/FLOW_MAP.md`](../operations/FLOW_MAP.md), `.index/` | regenerate after Phases 3 and 4 |
| [`../README.md`](../README.md) | Planning section points here while the plan is open |

## 9. Risks

- **No internet from the DSS backend** blocks HGNC; fall back to a snapshot dataset.
- **Passages are untrusted text** going into an LLM. The selection pass returns only ids, enums and
  verified quotes, which bounds what an injected passage can do.
- **PubMed is the open-access subset**; counts say "retrieved", never "all".
- **Drug coverage gaps** (§3) can read as "no drug". Copy says "no link in snapshot".
- **Rescoring cost** of Phase 4 is unmeasured.
- **Text-to-Cypher reliability** limits the assistant's graph answers (§7).

## 10. Open items

- LLM for the selection pass and for the agent (LLM Mesh ids).
- Whether the pre-fill should later widen beyond HER2+.
- Whether lapatinib and neratinib (approved on the parent *breast cancer* node) should be shown as
  "approved for a broader disease"; that needs the disease hierarchy and is not in this plan.
