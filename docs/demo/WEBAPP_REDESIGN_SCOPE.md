# Webapp redesign — scope

> **Lifecycle:** Planning (draft) · **Audience:** demo owners, webapp implementers and technical
> reviewers · **Authority:** what the redesign changes and why: the agreed decisions, the measured
> starting point, the target design and its boundaries · **Update when:** a decision in §2 changes, a
> measurement in §3 is superseded, or the design in §4 is revised · **Generated dependencies:** none ·
> **Excludes:** the phase sequence and acceptance criteria, which are
> [`WEBAPP_REDESIGN_WORKPLAN.md`](WEBAPP_REDESIGN_WORKPLAN.md); current deployed behaviour, which stays
> governed by [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md), [`../../webapp/README.md`](../../webapp/README.md)
> and [`../../webapp/DEPLOYMENT.md`](../../webapp/DEPLOYMENT.md) until each phase is implemented.

**Status: DRAFT — 2026-10-25, revised 2026-10-26 (built beside what runs today; the flow migration
decided separately). Not approved; nothing in DSS or the webapp has changed.** Supersedes
the Act 4 evidence review plan of 2026-10-23 (in git history), whose content is split between this
document and the workplan.

## 1. Summary

In a short demo the presenter goes straight to the ranked list and skips Acts 1–3. The redesign
makes that the app's own shape:

- **The shortlist is the first page.** It becomes an evidence review: for the selected gene and
  disease it shows why the model ranked it, the gene's identity, the drugs behind its badges, and the
  clinical trials and papers that mention it, each with its source attached.
- **Acts 1–3 become one page, "Why trust the list".** Three questions — what the model can see, how
  faithfully it reconstructs known biology, whether it holds across the disease family — each answered
  for the disease selected on the shortlist. Every analysis the three acts carried stays reachable
  under *Show the detail*.
- **An evidence assistant** answers free questions over the same sources.
- **It is built beside what runs today.** The redesign deploys to a second webapp in the same
  project, and its top-5 SHAP scoring runs beside the existing chain, so the live demo and the
  notebooks' numbers are untouched until the switch-over.
- **The flow migration is decided afterwards.** Whether the notebooks' supporting evidence moves into
  its own DSS project, which reads only the upstream zones 00–31, and whether the main project's flow
  after zone 40 is rebuilt around the new pages' functions, is a separate decision taken after the
  release. That migration has its own workplan,
  [`../operations/FLOW_MIGRATION_WORKPLAN.md`](../operations/FLOW_MIGRATION_WORKPLAN.md).

The agreed design is a static mockup over a 2026-10-23 snapshot, kept out of git at
`docs/demo/design_review/shortlist-and-evidence-review.html` (§4.4).

## 2. Decisions taken

Agreed in discussion between 2026-10-23 and 2026-10-26.

| id | decision | consequence |
|---|---|---|
| D1 | The assistant may use the graph, CT.gov and PubMed tools and HGNC, and cite them. It may also answer from the LLM's general knowledge, **but such claims are marked "not from a retrieved source" and never rendered as citations** | reverses `WEBAPP_DESIGN.md` §8 *"No LLM anything"* for this one surface |
| D2 | *Why this ranking?* shows the **top 5 SHAP contributions**, and only those features, each with its within-disease percentile | a second scoring recipe beside the existing chain; no existing recipe changes or rebuilds |
| D3 | Trials and literature are retrieved **on demand for the selected pair only**: direct searches, then **one LLM selection pass**. No agent loop, no batch over all pairs | retrieval design in the workplan |
| D4 | That pass also assigns each record a **role label**, and every label must carry a quote the backend verifies against the passage. A label that fails the check is dropped; the record stays, unlabelled | first LLM-derived labels in the app |
| D5 | Results are **cached per (disease, gene) pair in a DSS managed folder** | reverses §8 *"No writes to DSS"* for this cache |
| D6 | A scenario **pre-fills the cache for the HER2+ top 20** before a demo | one scenario, run by the user |
| D7 | Drug lineage comes from a **new long dataset built with visual recipes**, not from text-to-Cypher | no Part 1 change |
| D8 | The approved and in-trial badges stay **separate and never filterable**; the liability badge stays | keeps `WEBAPP_DESIGN.md` §6 |
| D9 | **The shortlist leads.** It is the home route and first navigation item; the supporting evidence follows it | changes the act order `DEMO_NARRATIVE.md` sets; `DEC-DEMO-002` (the narrative governs the dashboard) holds, so the narrative changes first |
| D10 | **Acts 1–3 become one page, "Why trust the list"**, of three sections with a headline answer each and the rest under *Show the detail*. No analysis is removed | 20 cards on three pages become 3 sections on one; three move to the shortlist (§4.3) |
| D11 | **One disease drives both pages.** Choosing it on either page changes it on the other | a shared store; the evidence page needs per-disease AUC for the shortlist's diseases |
| D12 | The evidence page's family detail keeps the **form of the live Act 3 plots**: the shared/specific chip layout, the overlap matrix with its All/Novel toggle, and the gene coverage dot grid. **Their colours come from theme tokens**, not inline styles: the matrix tints in six steps of `chart-3`, the grid's dots and gene names use `chart-3` and `chart-1` with three size and opacity steps | reuse `ActTabs` as it is; `ActMatrix` and `ActGeneGrid` move their colours to token classes, the only change to them |
| D13 | **Whether the notebooks' supporting evidence moves to its own DSS project is decided after the release**, as the flow migration's step G. If it moves, it reads `DEMO_TARGET_IDENTIFICATION`'s zones 00–31 through exposed objects, recomputes what it needs, and runs the notebook assertions; **`breast_panel_metrics` moves with it**, as supporting evidence; datasets nothing reads are deleted | none before the decision. If it moves: a third project beside the two `ADR-001` bounds; the build-governance allowlist, the identity-recipe check and the `.index/_dead.json` keep entry change with it (flow migration M0) |
| D14 | **The boundary rule.** Notebooks read only zones 00–31 and recompute anything downstream; the webapp backend reads only serving zones; no computed dataset is consumed by both | stated in workplan Phase 0, binding on every later phase; the flow migration, if it runs, enforces it on the existing flow |
| D15 | **The flow after zone 40 is organised by the new webapp's functions**: a shared scoring and ranking core (`40`), then `S1 Shortlist`, `S2 Evidence · graph`, `S3 Evidence · reconstruction`, `S4 Evidence · family panels`. New objects go in these zones from the start; re-zoning the existing flow, including zone 20 into its three jobs without a rebuild, belongs to the flow migration decision | layout in workplan Phase 0; Phases 4–6 build into `S1`; if the migration runs in full, it rebuilds the rest beside the old zones and compares before retiring them, and otherwise the existing zones stay as they are |

D1, D4 and D5 need one register entry; D9–D11 need another, because they change lasting demo scope
and order and could not be reconstructed from the code; D14 and D15 are recorded with them. If D13's
move goes ahead, it changes project ownership, so it needs a successor ADR to `ADR-001` rather than a
register line alone.

## 3. Starting point (measured 2026-10-23)

### 3.1 The shortlist's data

`dashboard_candidates` holds **105,702 rows over 12 diseases**. `candidates.py`'s docstring says
129,253 rows over 13 diseases and the Act 4 disease tooltip says 13; both are stale. HER2-positive
breast carcinoma (`disease_index` 48537) has a pool of 12,272. Its live funnel is 12,272 → novel
11,673 → tractable 7,950 → not secreted 7,273 → rank ≤ 200 → 38; the Act 4 table in
`WEBAPP_DESIGN.md` reads 7,951 and 7,274, one higher at both steps.

**SHAP.** `score_persona_candidates` computes Shapley explanations with `nbExplanations: 3` and a
background of 100. `compute_top_shap_drivers_1` keeps the top **two** as a rendered string
(`top_shap_drivers`), which Act 2's `shap_driver_frequency` folds into exactly two slots. Top 5 is not
available anywhere in the flow today.

### 3.2 Where the drug badges come from

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

Everything a per-drug view needs survives upstream. Rebuilding the per-drug records locally from the
snapshot reproduces both flags **for all 12,272 HER2+ pairs with zero mismatches**. Two facts the UI
must carry:

- *In trials* is every non-approval stage: Phase 2 (35% of edges), Phase 3 (18%), Phase 1 (11%),
  **UNKNOWN (10%, 4,068 edges)**, and failed programmes.
- **The link is exact-node, not hierarchical.** ERBB2 × HER2+ has two records: tucatinib (APPROVAL)
  and poziotinib (PHASE_2). Lapatinib and neratinib target ERBB2 but their approvals are recorded on
  *breast cancer* (MONDO 7254), not on the HER2+ subtype node. Trastuzumab and pertuzumab have no
  drug–protein edge at all. "No link in snapshot" therefore never means "no drug".

### 3.3 The search tools

| id | name | config | returns |
|---|---|---|---|
| `b6Rpbve` | graph search | Kuzu folder `ytvuniN8`, LLM `openai:bs-openai:gpt-5.6-terra` | `cypher_query`, nodes, edges, table |
| `4I2L6YL` | Cortex – CTgov | 5 chunks per call | NCT_ID, title, status, phases, conditions, sponsor, URL, chunk |
| `FNxhpfF` | Cortex – Pubmed (OA commercial subset) | 10 chunks per call | PMID, DOI, title, URL, chunk |

Each Cortex call takes about **2.2 s** of tool time. Graph search wrote a **directed** query (`->`)
and ignored *"at most 5"* (24 nodes returned) on its one test, so it stays out of the lineage view.

**Queries must lead with the gene.** The HER2+ disease name is itself a gene name and outweighs the
candidate:

| query | CT.gov records mentioning SMARCA2 | PubMed records mentioning SMARCA2 |
|---|--:|--:|
| `SMARCA2 HER2-positive breast carcinoma` | 0 of 5 | 0 of 8 |
| `SMARCA2 breast cancer` | 1 of 5 | 7 of 7 |
| `SMARCA2 BRM SWI/SNF ATPase breast` | 2 of 3 | 8 of 8 |

Two further retrieval facts: PubMed chunks include bibliographies (three of 24 gene-mentioning ERBB2
and SMARCA2 papers matched on a cited title alone), and CT.gov eligibility criteria are bullet lists
without full stops, so quote checks must not depend on sentence splitting.

### 3.4 Acts 1–3 today

Twenty cards over three pages, built as a sequence to walk through before the list:

| act | cards |
|---|---|
| 1 · The evidence base | The knowledge graph · Explore the graph yourself · What's in the graph · How things connect · Where the data came from · Provenance on every edge · What counts as "known" |
| 2 · Calibration | Which diseases qualify · How the candidate pool is built · Precision vs. chance · AUC, disease by disease · Enrichment, disease by disease · What drives the score · The model's inputs |
| 3 · The therapeutic area | The family panel · AUC with confidence intervals · When AUC stops working · Subtype overlap · Shared vs. subtype-specific · Gene coverage across the family |

Their endpoints (`/api/evidence`, `/api/calibration`, `/api/families/{id}`) already return everything
the evidence page shows, with one gap: per-disease AUC for the shortlist's diseases (§3.5).

### 3.5 Findings from building the evidence page

- **Act 2 highlights retired diseases.** `persona_enrichment.is_current` still marks the old persona
  set (lung cancer, non-small cell lung carcinoma, lung adenocarcinoma, obesity, type 2 diabetes,
  chronic kidney disease), not the shortlist's 12 diseases. The live enrichment chart therefore
  highlights diseases `WEBAPP_DESIGN.md` §7 says never to show by default. Nothing reads the flag after
  the redesign.
- **Per-disease AUC is not in the API.** `/api/calibration` returns the 668 AUC values unlabelled and a
  per-disease *enrichment* list. The marker on the evidence page needs each shortlist disease's AUC,
  rank and enrichment, which `persona_enrichment` carries (`auc_disease`, `rank_enrichment`, `n_pos`).
- **The breast panel has 15 terms, not 12.** Triple-negative is not scored, so the family macro AUC of
  0.9025 is over 14 terms.
- **The graph counts 7 node sources**, one of which (`MONDO_grouped`) is the graph's own grouping of
  MONDO. The page says six public sources, matching the narrative.

## 4. The design

### 4.1 Navigation

Two primary routes, built from route meta as the framework requires: **The shortlist** (home,
order 1) and **Why trust the list** (order 2), plus Settings. The three act routes go. One disease
selection is shared by both pages. Links labelled *How do we know?* on the shortlist jump to the
matching section of the evidence page: the intro row to all three, the Overview tab's model box to
section 2, its association box to section 1's "what counts as known".

### 4.2 The shortlist

Revises the 2026-10-22 blueprint:

| blueprint | revision | reason |
|---|---|---|
| one "Drug context" pill | separate *approved* and *in trials* badges, plus *liability* | D8 |
| fixed disease | `SelectField` of the 12 diseases, shared with the evidence page | D11 |
| "30 of 30 match" | every count carries its rank cut-off | `WEBAPP_DESIGN.md` §6 |
| three SHAP rows, illustrative | up to five SHAP rows with live percentiles | D2 |
| "Drug A" schematic | per-drug records: name, stage, relation, action, source release | D7 |
| placeholder trials and papers | retrieved records with role, verified quote, retrieval time | D3, D4 |
| simulated assistant | grounded answers; general-knowledge lines visibly marked; graph answers show Cypher | D1 |
| — | Drugs & graph tab keeps the five Visual Graph Explorer presets | existing contract |

### 4.3 Why trust the list

| section | shown up front | under *Show the detail* |
|---|---|---|
| 1 · What the model can see | graph totals; provenance on every interaction (the share asserted by more than one interactome); what "known target" means | node types, relations, node sources |
| 2 · How faithfully it reconstructs known biology | the leakage audit as one line; the AUC histogram with the selected disease marked, its rank and enrichment; macro AUC as the summary; reconstruction is not therapeutic value | the split table, which diseases qualify, how the candidate pool is built, precision vs. chance, family-level AUC, the bias toward well-connected genes |
| 3 · Does it hold across the disease family | every term with its 95% interval and the thin-label warning; the subtype separation check | shared vs. subtype-specific, subtype overlap, gene coverage (D12) |

Three Act 1–2 cards move to the shortlist rather than staying: *Explore the graph yourself* (the
Drugs & graph tab already hosts the Explorer), *What drives the score* and *The model's inputs* (the
*Why this ranking?* tab and the glossary). A disease with no family panel says so in section 3.

### 4.4 The design review

`docs/demo/design_review/` holds the agreed mockup, `shortlist-and-evidence-review.html`, and its
source in `source/`: the Vue components and pages (`source/design/`), the scripts that built the
snapshot fixtures (`source/scripts/`), and a README with the rebuild and regeneration steps. The folder
is git-ignored: the page is 1.4 MB and embeds retrieved passages, and the source carries the same
snapshot data. It exists only on the machine where it was made; copy it before working elsewhere.
The mockup is built with `bs-blueprint` and `@dataiku/ea-ui-kit`, passes the webapp's design lint and
typecheck, and uses the live `ActTabs` and the live `ActMatrix` and `ActGeneGrid` with their colours
moved to token classes (D12).

**Design-rule compliance, checked 2026-10-25.** The design lint cannot see a colour set through a
bound `:style`: its inline-colour rule matches only a static `style="…"`. The mockup was therefore
also searched for bound styles that set a colour and for raw HTML controls; both searches are empty.
The live app sets colours that way in `ActBar`, `ActCard`, `ActGeneGrid`, `ActMatrix`, `ShortlistView`,
`EvidenceView`, `CalibrationView` and `TherapeuticAreaView`, which is why its own check passes; the
workplan clears them by the end of Phase 2. Dark mode was not rendered; the app is light-only.

| real, from the 2026-10-23 snapshot | written for the review, and marked on the page |
|---|---|
| ranks, flags, funnel counts, percentiles, drug records, HGNC fields, retrieved trials and papers, and every figure on the evidence page (from the app's own Act 1–3 responses and `persona_enrichment`) | role labels and their reasons, SHAP rows 3–5, the assistant's answers |

## 5. Boundaries

**Kept from the current design.** No AUC on the shortlist; no `prediction` column; no filter on drug
or liability badges; no pooled AUC beside the macro one; no ablation ladder or hyperparameters; no
headline number without its spread; no language that prescribes research direction.

**If the migration runs (D13–D15).** `llm_hx` stays where it is (held for Part 1). Every governed
claim must resolve to the same value after the move, including the breast-panel claim whose authority
is `nb4` §8.10 (HER2+ reconstruction and subtype separation), which follows `nb4` and
`breast_panel_metrics` into the evidence project. No serving dataset is retired before its rebuilt
copy matches it.

**Not in scope.** Changes to `KNOWLEDGE_GRAPH_PRIMEKG` or Part 1 recipes; ChEMBL IDs, mechanism text or
source references for drugs (they need a Part 1 change); disease-hierarchy matching for drug links;
any safety or toxicity claim; storing assistant conversations.

## 6. Documentation impact

| document | change |
|---|---|
| [`DEMO_NARRATIVE.md`](DEMO_NARRATIVE.md) | act order and the four-acts table: the list first, the evidence on demand |
| [`../decisions/DECISION_REGISTER.md`](../decisions/DECISION_REGISTER.md) | two entries: the evidence assistant, LLM role labels and DSS cache (D1, D4, D5); the list leads, one evidence page, one disease (D9–D11) |
| [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) | §3.3 routes, §4 acts table and Acts 1–4 sections, §6 guardrail rows, §8 |
| [`../../webapp/README.md`](../../webapp/README.md), [`../../webapp/DEPLOYMENT.md`](../../webapp/DEPLOYMENT.md) | the two-page structure; new settings (tool, agent, folder, model ids) and the pre-fill step |
| [`../operations/FLOW_MAP.md`](../operations/FLOW_MAP.md), `.index/` | regenerate after the new datasets exist |
| [`../operations/FLOW_MIGRATION_WORKPLAN.md`](../operations/FLOW_MIGRATION_WORKPLAN.md) | the migration's own document changes (successor ADR, `PROJECT_CONTEXT.md` §4.3, build governance, notebooks README, agent instructions), listed in its §5 |
| [`../README.md`](../README.md) | Planning section points to both documents while the work is open |

## 7. Risks

- **No internet from the DSS backend** blocks HGNC; fall back to a snapshot dataset.
- **Passages are untrusted text** going into an LLM. The selection pass returns only ids, enums and
  verified quotes, which bounds what an injected passage can do.
- **PubMed is the open-access subset**; counts say "retrieved", never "all".
- **Drug coverage gaps** (§3.2) can read as "no drug". Copy says "no link in snapshot".
- **Rescoring cost** for top-5 SHAP is unmeasured.
- **Text-to-Cypher reliability** limits the assistant's graph answers.
- **Moving recipes breaks what fingerprints them.** Build governance's allowlist and pilot, the
  identity-recipe check and `tools/push_assertions.py` each assume one project. The flow migration's M0
  changes them before anything moves, and M2's acceptance (assertions unchanged) is the guard.
- **A short demo loses the narrative's order.** The *How do we know?* links are what carry the
  supporting evidence into it; if they are hard to find, the evidence is skipped entirely.

## 8. Open items

- LLM for the selection pass and for the agent (LLM Mesh ids).
- Whether the pre-fill should later widen beyond HER2+.
- Whether lapatinib and neratinib should appear as "approved for a broader disease"; that needs the
  disease hierarchy.
- Whether to clear `persona_enrichment.is_current` in DSS or leave it unread.
- The page name: "Why trust the list" is the working title.
- The evidence project's key and name (D13).
