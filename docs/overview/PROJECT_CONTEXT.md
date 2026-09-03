# Target Identification POC — project context & index

> **Lifecycle:** Canonical · **Audience:** POC sponsors, architects and contributors · **Authority:**
> stable purpose, personas and the Part 1/Part 2 shared-object contract · **Update when:** that purpose,
> contract or its named owners change · **Generated dependencies:** none · **Excludes:** volatile build
> status, experiment chronology and implementation procedures.

<!-- Governed claims consumed here: TI-DATA-001 TI-MOD-001 TI-VAL-001 TI-VAL-004 TI-VAL-007 TI-VAL-009 -->

> **Start here.** This file explains *why* the work exists, *who* it serves, and *how the two
> projects fit together*. It carries no implementation detail — each project has its own
> technical document.
>
> | Document | Covers | DSS project |
> |---|---|---|
> | **this file** | purpose, market evidence, personas, how the pieces fit | — |
> | **[GRAPH_BUILDING.md](../graph/GRAPH_BUILDING.md)** | input sources, pipeline, graph schema, graph statistics, the graph webapp | `DEMO_KG_LS` |
> | **[TARGET_PRIORITIZER.md](../prioritizer/TARGET_PRIORITIZER.md)** | candidate population, features, split, training and model-selection method | `DEMO_TARGET_IDENTIFICATION` |
> | **[VALIDATION.md](../prioritizer/VALIDATION.md)** | governed validation evidence, negative results and limitations | `DEMO_TARGET_IDENTIFICATION` |
> | **[DEMO_NARRATIVE.md](../demo/DEMO_NARRATIVE.md)** | **what we show scientists and in what order** — the objection ladder, the punch line, what not to show | both |
> | **[DISCOVERY_LANDSCAPE.md](../reference/DISCOVERY_LANDSCAPE.md)** | the wider drug-discovery chain (stages 1–6) and where a platform belongs | — |
> | **[RESEARCH_NOTE.md](../reference/RESEARCH_NOTE.md)** | per-reference evidence base for the Part 2 method choices | — |
> | **[DECISION_REGISTER.md](../decisions/DECISION_REGISTER.md)** | current durable project decisions and consequences | both |
> | **[DSS_CHEATSHEET.md](../platform/DSS_CHEATSHEET.md)** | platform behaviours and CLI patterns, stated generically | — |
>
> Current durable decisions live in the [decision register](../decisions/DECISION_REGISTER.md).
> Experiments, incidents and reversals remain recoverable through `.index/decisions_history.tsv`.
>
> **Read [DEMO_NARRATIVE.md](../demo/DEMO_NARRATIVE.md) before designing the dashboard or pruning the flow.**
> Both should be derived from the story. We tried the reverse and it produced a plan to delete our
> strongest evidence — see [VALIDATION.md](../prioritizer/VALIDATION.md) §3–6.

## 1. Purpose

Demonstrate that the Dataiku platform can **recreate a biomedical knowledge-graph pipeline for
drug-discovery target identification**, end to end, in a governed flow — and then do something
useful with it.

Three deliverables:

1. **Create a PrimeKG-like pipeline** ([mims-harvard/PrimeKG](https://github.com/mims-harvard/PrimeKG#building-an-updated-primekg)) —
   ingest public biomedical sources and harmonize them into graph nodes and edges as a Dataiku flow.
2. **Materialize and explore the graph** with the Visual Graph plugin — an interactive, queryable
   knowledge graph for target exploration.
3. **Rank candidate targets per disease**, explainably — Visual ML + SHAP, with a clickable
   evidence path on the graph.

**What differentiates this from a bioinformatics script farm is reproducibility, lineage and
explainability — not the algorithm.** The method is deliberately the industry-standard one
(§2.3). Say that plainly; a scientist respects it more than a claim to novel method.

## 2. Business context

The pharmaceutical industry faces a productivity crisis: **~$2.2B and 10–15 years** per approved
therapeutic, with **~90% of clinical candidates failing** — more than half for lack of efficacy or
unmanageable toxicity. The field has shifted from phenotypic screening to a data-driven, targeted
approach, in which **target identification** is the critical go/no-go checkpoint: form a
therapeutic hypothesis backed by evidence *before* significant capital is committed.

Knowledge graphs are the central tool for the **data-silo problem** — integrating fragmented
biomedical data so models can reason over it at scale.

### 2.1 The two published numbers that anchor the pitch

Summarised from [DISCOVERY_LANDSCAPE.md](../reference/DISCOVERY_LANDSCAPE.md) §2. They point in opposite
directions, and holding both is what makes the pitch credible rather than promotional.

| | Finding | What it de-risks |
|---|---|---|
| **Genetic evidence works** | Target–disease pairs with human genetic support have **2.6× relative clinical success** (Minikel et al., *Nature* 2024); >2× in 11 of 17 therapy areas. The effect concentrates in **Phase II/III**, is weakest in Phase I, and **rises with confidence in the causal-gene assignment**. Only ~4.8% of current Phase I–III pairs have such support. | **Efficacy** — did we aim at the right thing |
| **Computational chemistry works, but elsewhere** | AI-derived molecules reach **80–90% Phase I success** (historical base rate 40–65%) but **~40% in Phase II** — industry par (*Drug Discov Today* 2024). | **Developability** — is the molecule well-behaved |

**Why the pairing matters.** Phase I asks *is this molecule safe and tolerable* — a property of
the molecule. Phase II asks *does it treat the disease* — a property of the **biological
hypothesis**. So generative chemistry is genuinely good at making better-behaved molecules and
does nothing about whether the target was right. Genetics de-risks exactly the phase chemistry
does not.

Two consequences we lean on:

- **The value sits in the gene-assignment step**, not in having a genetic signal. Knowing *which*
  gene at a locus matters more than the locus. That is a data-integration and modelling problem.
- **The unsolved problem is connective tissue** — carrying a hypothesis from "this gene matters"
  to "this molecule is worth making" to "we nominate this candidate", with evidence, uncertainty
  and human decisions preserved end to end. That is a data-platform problem, and this POC is a
  working demo of the upstream half.

### 2.2 Where this POC sits in the discovery chain

Six stages, ~10–15 years. Detail per stage in [DISCOVERY_LANDSCAPE.md](../reference/DISCOVERY_LANDSCAPE.md).

| # | Stage | Question | This POC | Platform fit |
|---|---|---|---|---|
| 1 | **Target identification** | What should we aim at? | ✅ **built** | **Strong** |
| 2 | **Target prioritisation** | Which candidate is worth money? | 🟡 partly built — ranked + filterable on tractability, class and known liabilities; a real safety axis still needs a direct measurement | **Strong** |
| 3 | Validation & assay development | Does it work; can we measure it? | ❌ | Narrow — data plumbing |
| 4 | Hit finding / lead discovery | Which molecules bind it? | ❌ *(separate story)* | Orchestration |
| 5 | Hit-to-lead & lead optimisation | Can it become a drug? | ❌ *(separate story)* | Orchestration |
| 6 | Candidate nomination | Which one do we bet on? | ❌ | **Strong** — governance |

**The pattern.** Stages 1–2 and stage 6 are evidence-integration and decision-governance problems:
many messy sources, identifier reconciliation, a ranking model, an audit trail, a dashboard a human
decides from. Stages 4–5 are computational-chemistry and laboratory problems where incumbent
software is entrenched and the real bottleneck is assay-data plumbing rather than algorithms.

### 2.3 Precedent — this reproduces an industry standard

- **Supervised target prioritisation is the Open Targets standard.** Their Locus-to-Gene (L2G)
  model is **XGBoost + SHAP** on a gold-standard positive set — *not* a graph neural network.
  Directly transferable to Dataiku Visual ML. (Mountjoy et al., *Nat Genet* 2021.)
- **Explainability drives adoption, not accuracy.** TxGNN (*Nat Med* 2024, built on PrimeKG)
  showed path explanations raised expert accuracy **+46%** and confidence **+49%**.
- **Network proximity is established.** Disease genes cluster in the interactome; proximity to a
  disease module predicts association (Guney et al., *Nat Commun* 2016, AUC ≈ 0.81; Menche et al.,
  *Science* 2015).

**Value narrative:** integrating siloed data into one governed graph enables (a) discovery of novel
targets, (b) early prediction of off-target liability, therefore (c) reduced early-stage attrition.

**Accounts of interest:** Ipsen, Boehringer, Pfizer, Astellas (Japan), Jazz.

## 3. Personas & user stories

| # | Persona | Goal |
|---|---------|------|
| 1 | Computational biologist, early R&D (metabolic diseases) | Understand obesity-related biological networks to identify key inflammatory and metabolic targets (IL6, TNF, IL1B; LEP/LEPR and insulin signalling → GLP-1 agonists) as intervention points. |
| 2 | Oncology data scientist, cancer center | Investigate signalling hubs in breast-cancer progression to validate and extend targets across tumour biology and immune response (PI3K/AKT/mTOR — PIK3CA, AKT1, MTOR, PTEN; hormone signalling — ESR1). |

Persona diseases drive both graph exploration and model validation
([VALIDATION.md](../prioritizer/VALIDATION.md) §6.3).

**Demo diseases are now chosen by measurement** — see [DEMO_NARRATIVE.md](../demo/DEMO_NARRATIVE.md) §6 and
[VALIDATION.md](../prioritizer/VALIDATION.md) §6.3. The panel is **non-small cell lung carcinoma** (the MAPK3 discovery
story), **HER2-positive breast carcinoma** (passes clinical sanity outright: ERBB2 at rank 13, AUC
0.93 on 599 known targets), **diabetes mellitus** and **obesity disorder**.

⚠ **An earlier version of this section recommended the generic `breast cancer` term on no
measurement.** It is the *worst* term in the breast panel — AUC **0.69**, beaten by its own subtypes.
The parent-term intuition was backwards here. **Triple-negative** is kept as a deliberate hard case for
clinician review rather than as a showcase, because it has only 8 known gene associations and cannot be
scored against our labels at all.

## 4. The two projects

Graph construction and modelling are **separate DSS projects**, because they change on
incompatible cadences: the graph is stable for weeks while modelling iterates several times a day.
Sharing one flow also let a feature experiment reach a graph recipe and silently renumber every
node in the graph.

```
   DEMO_KG_LS                                    DEMO_TARGET_IDENTIFICATION
   ──────────                                    ──────────────────────────
   public sources                                shared in ──┐
        ↓ extract (Python)                                    │
        ↓ harmonise (visual)                    graph features (Cypher + matrix)
        ↓ assemble (4 recipes)                              ↓
   graph_nodes · graph_edges                     modelling table + leakage-controlled split
   edge_metadata · kg                                       ↓
        ↓                                        XGBoost + SHAP  →  ranked candidates
   Kuzu snapshot + graph webapp  ───────────────→ (evidence paths render on the webapp)
```

### 4.1 `DEMO_KG_LS` — data pipeline and graph-building webapp

Ingests public biomedical sources over HTTP, harmonizes them onto a single identifier system, and
assembles a PrimeKG-conformant knowledge graph, then materializes it as a queryable Kuzu graph with
an interactive explorer webapp.

**Status: complete.** 113,391 nodes / 2,851,510 edges across 18 relation types, 8 node types.
Rebuilt from source and accepted against the frozen reference on a structural criterion.
`node_index` is now **deterministic**, which it was not before — every prior rebuild silently
renumbered all 113k nodes.

→ **[GRAPH_BUILDING.md](../graph/GRAPH_BUILDING.md)**

### 4.2 `DEMO_TARGET_IDENTIFICATION` — modelling, validation, result visualisation

Consumes the graph, derives network and functional-annotation features per (gene, disease) pair,
trains an explainable ranking model, and produces a per-disease shortlist of candidate targets with
SHAP attributions and on-graph evidence paths.

**Status: built and validated on the rebuilt graph; champion refreshed 2026-08-21.** Champion
`m7-f14` (14 features): macro per-disease AUC **0.8230** over 670 diseases. Three-rung ablation
ladder, two independent validation metrics cross-checking to 1.9×10⁻⁴, and a documented negative
result.

→ Method: **[TARGET_PRIORITIZER.md](../prioritizer/TARGET_PRIORITIZER.md)** · Evidence:
**[VALIDATION.md](../prioritizer/VALIDATION.md)**

### 4.3 The interface between them

`DEMO_KG_LS` exposes **13 objects** to `DEMO_TARGET_IDENTIFICATION`, which appear in its
`00 Imported from DEMO_KG_LS (synced)` flow zone. This list *is* the contract — anything else in the
graph project can change freely.

**Since 2026-08-18 the datasets are consumed through local synced copies, not read across the project
boundary.** Each of the 12 foreign dataset references now feeds **exactly one Sync recipe** and
nothing else; every downstream recipe reads the local copy of the same name. That makes the import
surface auditable in one place and stops a rename in the graph project breaking 26 recipes at once.

**The Kuzu folder was the exception, and is being brought into the same pattern.** A folder cannot be
Sync'd, but it can be merged: `compute_ytvuniN8` is a Merge-Folder recipe that copies
`DEMO_KG_LS.published_kg_ls-Mp25kL` into the local managed folder **`graph` (`ytvuniN8`)**. As of
2026-09-03 the Graph Explorer webapp already reads the local `graph` folder, while the **10 Cypher
feature recipes still read `DEMO_KG_LS.enriched_index_freezed-6bRVGs` directly across the boundary**.
Switching those 10 to the local folder is approved and pending verification (Phase C); until then two
Kuzu read paths coexist and this table records both.

| Shared object | Local consumers | Why the modelling project needs it |
|---|--:|---|
| `published_kg_ls` *(Kuzu folder)* | 1 | the current materialized graph — merged into the local `graph` folder by `compute_ytvuniN8`, which the Graph Explorer webapp reads |
| `enriched_index_freezed` *(Kuzu folder)* | 10 | **legacy path, pending Phase C.** The 10 Cypher feature recipes still read this snapshot across the boundary; not synced |
| `graph_nodes` | 26 | node identity, types, names; the index→entity lookup |
| `drug_disease_edges` | 11 | therapeutic-axis ground truth — `indication` and `drug_investigated_for` |
| `drug_protein_edges` | 11 | tractability-axis ground truth — the only uninflated drug label |
| `graph_edges` | 6 | matrix-form features computed outside Kuzu |
| `gene_names` | 3 | gene symbols for the candidate tables |
| `raw_disease_disease` | 2 | **pre-reversal** hierarchy — assembly makes edges undirected, so hierarchy direction only survives here |
| `mondo_references` | 2 | cross-reference hub, for the split-control anchor mapping |
| `edge_metadata` | 1 | interaction-source provenance → measurement-confidence features |
| `raw_go_hierarchy` | 1 | functional-annotation hierarchy → gene localization |
| `raw_ot_druggability` | 1 | Open Targets tractability buckets → druggability class annotation |
| `raw_ot_safety` | 1 | Open Targets safety liabilities → display-only annotation |
| `raw_ot_known_drug` | 1 | the curated `known_drug` evaluation label ([VALIDATION.md](../prioritizer/VALIDATION.md) §3.2) |

**Everything else the modelling project needs, it owns.** One source recipe stays on the modelling
side deliberately — the split-control disease vocabulary — because it contributes no nodes or edges to
the graph. **The three Open Targets extractions moved the other way**, into `DEMO_KG_LS`: they are
source ingestion, which is that project's job, even though only the modelling project consumes them.

### 4.4 `KNOWLEDGE_GRAPH_PRIMEKG` — frozen reference

The original single-project build. **Frozen read-only as the reference implementation** and kept
until the migration is verified end to end. It is the baseline both new projects were diffed
against, and it should not be modified or rebuilt.

### 4.5 Migration status — complete and verified

**The split is done.** The modelling flow was rebuilt end to end against the shared graph on
2026-08-17 and **the reconstruction is confirmed**: every metric landed within ±0.01 of the frozen
reference, against a ±0.02 tolerance set in advance (historical comparison in
[VALIDATION.md](../prioritizer/VALIDATION.md) §4.1).

| | Reference | Rebuilt |
|---|--:|--:|
| macro per-disease AUC | 0.8228 | **0.8197** |
| drug-target AUC | 0.6836 | **0.6911** |
| candidate pool | 6,754,128 | **6,754,128** *(identical)* |

Three individual personas reproduced to within **0.002**, which is stronger evidence than the macro
average because nothing averages out.

### 4.6 What remains

- **Retire `KNOWLEDGE_GRAPH_PRIMEKG`** — the acceptance criterion is now met, so the frozen reference
  has served its purpose. Also retire the older of the two Kuzu snapshots in `DEMO_KG_LS`.
- **Target prioritisation (stage 2) — the deliverable is now filterable, the safety axis is not
  solved.** `target_candidates_2` is **129,253 ranked candidates over 13 personas** carrying
  tractability, target class and known-liability annotations, so a scientist filters instead of
  receiving a pre-cut list. But the two freely-available safety signals were measured and **rejected
  as filters** — genetic constraint runs *with* druggability and curated liabilities mark drug
  precedent, not risk ([VALIDATION.md](../prioritizer/VALIDATION.md) §5). A real safety axis needs a direct measurement
  (essentiality, tissue-expression breadth), which means a new source. That plus the dashboard is the
  largest remaining increment of demo value.
- **Re-pick the persona panel on evidence.** The flagship metabolic disease is the weakest case on
  both metrics while two non-persona cancers are the strongest therapeutic showcases
  ([VALIDATION.md](../prioritizer/VALIDATION.md) §6.3).
- **Minor:** regenerate the demo query literals, rebuild the drug-label chain, and materialise the
  hub-bias meter as a recipe ([VALIDATION.md](../prioritizer/VALIDATION.md) §3.3).

---

## Decision route

Current project-level choices are in
[`DECISION_REGISTER.md`](../decisions/DECISION_REGISTER.md). Modeling methods remain in
[`TARGET_PRIORITIZER.md`](../prioritizer/TARGET_PRIORITIZER.md), measured evidence in
[`VALIDATION.md`](../prioritizer/VALIDATION.md), and the complete retired chronology in
`.index/decisions_history.tsv`.
