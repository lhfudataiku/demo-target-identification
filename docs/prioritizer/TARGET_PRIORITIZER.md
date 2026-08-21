# Explainable Target Prioritizer — `DEMO_TARGET_IDENTIFICATION`

> Technical documentation for the **modelling, validation and result-visualisation** project: what
> the data exploration found, why these features and this model, and how well it actually works.
>
> Companion documents: **[PROJECT_CONTEXT.md](../overview/PROJECT_CONTEXT.md)** (why / who / how the projects
> fit) · **[GRAPH_BUILDING.md](../graph/GRAPH_BUILDING.md)** (the graph this consumes) ·
> **[RESEARCH_NOTE.md](../reference/RESEARCH_NOTE.md)** (per-reference evidence base) ·
> **[DSS_CHEATSHEET.md](../platform/DSS_CHEATSHEET.md)** (platform behaviours).
>
> **Status: built and validated on the rebuilt graph; champion refreshed 2026-08-21.** Champion
> **`m7-f14`** (14 features): macro per-disease AUC **0.8230** over 670 diseases, per-split-key
> 0.8046, pooled 0.8932, per-family 0.8009, drug-target 0.6886.
>
> **The migration is complete and the reconstruction is confirmed.** Every metric landed within
> **±0.01** of the frozen reference — inside the ±0.02 tolerance set in advance — and the ablation
> ladder preserves its ordering. §10 records the comparison and the three index-dependent behaviours
> the rebuild exposed.
>
> **One thing to know before reading any number here:** the headline metric is *association* AUC,
> and it does **not** predict therapeutic relevance. §7.4 is a prerequisite, not an appendix.
>
> Decisions are logged in the **appendix**.

## 1. Scope, and how to read this

This is the **methodology** record: what the data forced, why these features and this model, what was
measured, and what was refuted. Every table names the dataset it comes from, or is marked
`notebook-only`.

- **The demo narrative and the executive summary are in [DEMO_NARRATIVE.md](../demo/DEMO_NARRATIVE.md)** — what
  to show a scientist, in what order, and what not to show. Read that first if you are presenting.
- **Why the project exists** is in [PROJECT_CONTEXT.md](../overview/PROJECT_CONTEXT.md).
- **Why each decision was made**, including the reversals, is in [DECISIONS.md](../../DECISIONS.md).

**Every section names its source.** A `*Source:*` line under each heading gives the flow dataset the
numbers come from and the notebook that re-derives them, or says `notebook-only` where no flow artifact
exists. Four notebooks in `DEMO_TARGET_IDENTIFICATION` (`nb1`–`nb4`, code env `primekg_kg`) assert every
quoted aggregate against live data, so drift fails loudly — see [notebooks/README.md](../../notebooks/README.md).
**If a number here has no source line, treat it as unverified.**

**One thing to know before reading any number here:** the headline metric is *association* AUC, and it
is **statistically orthogonal** to therapeutic relevance — r = +0.002, R² = 0.0000 over 130 diseases
(§7.4). Every claim in §8 is scoped to one axis. Which axis is never optional.

## 2. Scientific basis

> Per-reference summaries and the feature→reference map are in
> [RESEARCH_NOTE.md](../reference/RESEARCH_NOTE.md).

This reproduces an industry-standard pattern rather than inventing one — deliberately. The
differentiator is reproducibility, lineage and explainability, not the algorithm.

- **Supervised target prioritisation is the Open Targets standard.** Their Locus-to-Gene model is
  **gradient-boosted trees + SHAP** on a gold-standard positive set — *not* a graph neural network.
  Directly transferable to visual ML. (Mountjoy et al., *Nat Genet* 2021.)
- **Network proximity / guilt-by-association.** Disease genes cluster in the interactome as "disease
  modules", and proximity to a module predicts association — indication classification at AUC ≈ 0.81
  (Guney et al., *Nat Commun* 2016). Menche et al. (*Science* 2015) established disease modules
  **and the incomplete-interactome caveat: ~80% of interactions are unmapped** — which turns out to
  matter a great deal here (§8.8).
- **Degree-weighted path counts (DWPC).** Typed path counts over a heterogeneous network,
  degree-damped so hubs don't dominate (Himmelstein et al., *eLife* 2017).
- **Interpretability drives adoption.** TxGNN (*Nat Med* 2024, built on PrimeKG) showed path
  explanations raised expert accuracy **+46%** and confidence **+49%**.

## 3. Data exploration — what the data forced us to do

Four exploration findings each changed the design. They are the reason the model looks as it does.

### 3.1 The label set is study-biased, and that governs every metric

*Source: `graph_edges` (`disease_protein`) · `nb5`. Measured 2026-08-19; previously asserted without numbers.*

**Label:** `is_target` = 1 if a disease–protein association edge exists (genetic association +
somatic mutation @ score ≥ 0.3). **189,444 unique (disease, gene) associations.**

**The bias is severe, and it is far worse on the disease side than the gene side:**

| | diseases | genes |
|---|--:|--:|
| entities with ≥1 association | 7,039 | 13,442 |
| **median associations** | **2** | 5 |
| p90 / p99 | 49 / 616 | 27 / 165 |
| maximum | **3,245** | 622 |
| share of the label held by the top 1% | **31.2%** | 16.0% |
| share held by the top 10% | **83.9%** | 58.6% |

**The top 10% of diseases carry 84% of the label, and the median disease has two known genes.** Every
per-disease metric in §7 is therefore an average over a population where most members are almost
unannotated — which is why §7.1 reports *macro* per-disease AUC rather than pooled, and why §8.10's
triple-negative arm (8 known genes) is normal rather than exceptional.

Curated associations also skew toward well-studied genes, which are interactome hubs. **A model that
exploits hub-ness therefore scores *better* on AUC even when it is less useful for finding
under-studied targets.** That is why §7.2 measures hub bias as a separate axis rather than trusting
AUC — and §7.2 now shows the champion is *worse* on it than its predecessor.

### 3.2 The disease ontology is redundant, and it leaks

*Source: `raw_disease_disease`, `graph_nodes` · `nb5`. Re-measured 2026-08-19.*

The ontology is deeply redundant. A scan for breast concepts alone returns **225 disease nodes**
(`breast carcinoma`, `invasive ductal breast carcinoma`, `female breast carcinoma`, `HER2 positive
breast carcinoma`, …), many of them one hop apart. Left alone, parent and child land on opposite sides
of a split and every metric inflates.

**Graph-topological family construction was tried and rejected. Re-measured:**

| Property | Measured |
|---|---|
| eligible diseases (in the candidate pool) | **1,157** |
| hierarchy edges resolving onto the graph | 34,019 |
| **eligible diseases with more than one direct parent** | **52.8%** (468 of 887 that have any) |
| undirected transitive closure — largest component | **907 of 1,157 eligible (78.4%)** |

**The ontology is a DAG, not a tree.** Because **52.8%** of eligible diseases have multiple parents,
transitive union-find chains unrelated branches together — one component swallows 78% of the eligible
set. Broad classificatory terms are themselves eligible diseases *and* genuine ancestors, so
restricting to directed edges does not help either. **No clean global partition exists**, which is why
§5.3 borrows an external curated one instead.

> ⚠ The retired version of this table also quoted K-hop grouping figures (930 at K=1, 1,145 at K=2).
> Those are **not reproduced here** — `nb5` measures the largest *single* K-hop neighbourhood (10 at
> K=1, 44 at K=2), which is a different quantity from whatever the original used, and the original
> method was never written down. Do not quote either set until one is defined.

### 3.3 Granularity does *not* trade away confidence — the earlier claim was backwards

*Source: `raw_disease_disease`, `validation_auc_by_disease` · `nb5`. Rewritten 2026-08-19.*

This section previously claimed that coarser terms are the safer choice: *"aggregation buys AUC and
costs specificity."* **Tested across every parent–child pair where both terms are in validation, that
is wrong.**

| | n | mean AUC |
|---|--:|--:|
| parent (broader) terms | 259 pairs | 0.8064 |
| **child (more specific) terms** | 259 pairs | **0.8355** |

**The more specific term scores higher in 56.4% of pairs, and +0.029 on average** — 54.4% when
restricted to the 158 pairs where the parent genuinely has more positives. And module size barely
predicts ranking quality at all: **Spearman(module size, AUC) = +0.110**, Spearman(positives, AUC) =
+0.198.

**Read the effect honestly: it is directionally opposite to the old claim but modest in aggregate.**
56.4% is not far from a coin flip. What the measurement supports is *"specificity costs nothing"*, not
*"specificity is better"*.

**§8.10 supplies the strong instance.** In the breast family the generic `breast cancer` term scores
**0.7072** — the worst of twelve — while `HER2 positive breast carcinoma` reaches **0.9365** and every
subtype beats the parent. So the parent-term intuition can fail badly in a specific family even though
the population effect is mild.

> **The surviving guidance is narrower than before: split by family for leakage control (§5.3), then
> report and act at the disease level.** Aggregating to the family is a leakage device, not a way to buy
> a better number.

### 3.4 The model cannot resolve *morphological* subtype — but it does resolve *molecular* subtype

*Source: `lung_granularity_check`, `breast_panel_overlap` · reproduced in `nb4`.*

Across the **17 members of the lung-cancer family**, the top-50 candidate lists are **55% identical
on average** (136 pairwise comparisons, mean 27.3 of 50 genes shared; reference: 63% over 10
respiratory subtypes). The clearest case: **lung adenocarcinoma vs squamous cell lung carcinoma share
47 of 50** (Jaccard 0.887) — two histologies with genuinely different pathophysiology and different
standard of care, returning almost the same list.

**This limit is in the data, not the model** — the source annotations for those subtypes are
themselves ~83% identical, and two major subtypes share 602 of 724 union positives. **Do not promise
subtype resolution.**

The model does separate the genuinely distinct members: a pulmonary lymphoma shares only 9 of 50 with
lung cancer, and a mucoepidermoid carcinoma 6 of 50 — so the failure is specific to histologies that
the underlying annotations do not distinguish, not general.

**The breast panel narrows this claim further, and the narrowing matters** (§8.10, `breast_panel_*`,
2026-08-19). The lung result was generalised to "subtype", full stop. Measured on breast, **HER2-positive
and triple-negative share only 2 of their top-50 novel candidates (4%)** — the cleanest separation
anywhere in the project, against 47-of-50 for the lung pair.

| | lung adeno vs squamous | HER2+ vs triple-negative |
|---|--:|--:|
| top-50 shared | **47 / 50** | **2 / 50** |
| subtype defined by | morphology | molecular markers |
| source annotations | ~83% identical | largely disjoint |

**The distinguishing property is how the subtype is defined, not that it is a subtype.** Molecular
subtypes are named for markers that carry their own curated gene associations; histological subtypes
are named for appearance and inherit a shared annotation set. So the honest claim is *"we do not
promise **morphological** subtype resolution"* — and molecular stratification, which is what oncology
actually treats on, is a case where the model performs at its best.

> **⚠ This diagnostic had to be repointed during the rebuild.** It selected on the *split key*, and
> the lung subtypes' split key changed from `respiratory system cancer` to `thoracic cancer` — which
> also holds breast, so the comparison would have been breast-vs-lung. It now selects the
> lung-cancer **family**, which is the stable expression of "lung cancer and its histological
> subtypes" and matches the recipe's stated purpose.

## 4. Feature engineering

`G`=gene, `D`=disease, `P`=pathway, `F`=molecular function, `B`=biological process. DWPC uses the
standard degree-damping exponent (weight = ∏degree^−0.4), so paths through hubs are down-weighted.

### 4.1 The 12 features in the champion model

*Source: ML task settings on analysis `I2csfIX2` — pull them live, never hand-list · `nb1`.*

| Feature | Layer | Biological significance |
|---|---|---|
| `dwpc_GPGD` | pathway + association | Candidate sits in a **curated pathway** with known disease genes — shared mechanism at reaction level. Strongest single feature (within-disease AUC 0.641). |
| `dwpc_GGD` | interactome + association | Candidate **physically interacts** with proteins already implicated — the classic disease-module argument. |
| `dwpc_GFGD` | molecular function + association | Candidate has the **same biochemical activity** as disease genes *without requiring a mapped physical interaction*. Routes around the interactome's membrane-protein blind spot — the single biggest model improvement (§6). |
| `dwpc_GBGD` | biological process + association | Candidate **participates in the same biological process**. Broader and less mechanistic than the function axis; partially overlaps pathway evidence. |
| `ppi_adamic_adar` | interactome | Neighbour-set overlap with the module, **discounting hub neighbours** — sharing a rare interactor is more informative than sharing a promiscuous one. |
| `ppi_jaccard` | interactome | Neighbour overlap normalized by union size — the size-independent form of the same signal. |
| `ppi_common_neighbors_z` | interactome + association | **Degree-matched** overlap: observed vs hypergeometric expectation. Answers "more module contact than this gene's connectivity alone predicts?" — the control that rescues sparsely-assayed genes. |
| `ppi_evidence_depth` | interaction provenance | Mean number of independent sources backing the gene's interactions. A **measurement-confidence covariate**: lets the model discount a thin neighbourhood instead of reading thin as negative. |
| `gene_ppi_degree` | interactome | Connectivity — retained deliberately as the **single** hub control (§6.1). |
| `gene_n_pathways` | pathway | Annotation breadth — how well-characterized the gene is. Partly a study-bias proxy. |
| `shared_pathway_frac` | pathway | Fraction of the gene's pathways overlapping the module's — normalized, so it doesn't simply reward well-annotated genes. |
| `ppi_multi_source_frac` | interaction provenance | Fraction of interactions corroborated by ≥2 sources. A second **assay-breadth** covariate. |

**The design thesis, stated once:** on a study-biased graph, *measurement-confidence covariates
matter as much as topology*. Two of the three provenance features earned their place on measurement,
which supports it.

### 4.2 Computed and rejected — and why

*Source: `nb1` for the null gaps, collinearity and single-feature AUC. The rejection *rationale* is argument, not measurement.*

The rejections are more informative than the inclusions, because most encode a leakage mechanism.

| Feature | Reason rejected |
|---|---|
| `relation` | **Hard leak** — non-null iff the edge exists. A restatement of the label. |
| `rwr_score`, `rwr_norm` | **Label-derived missingness.** The recipe records held-out *seed* genes unconditionally while floor-gating non-seeds, and seeds *are* positives → null gap −75 pp. |
| `gene_n_diseases` | **Label-derived** — built from the label relation itself; alone separates the test set at AUC 0.835. |
| `disease_context` | Label-derived (counts module membership in neighbouring diseases) and 95% null. |
| `module_size` | Per-disease constant → a pure base-rate encoder with zero within-disease ranking power. |
| `dwpc_GCD` | 99.8% null, and **circular** for target identification: "an approved drug already targets this gene for this disease" nearly restates the label. Retained as a **post-hoc evidence annotation** (§8.6). |
| `prox_closest` | **Dropped after measurement**, not on suspicion. Removal cost nothing (per-disease 0.8207 → 0.8228; drug-target 0.6880 → 0.6836) — redundant with the neighbour-overlap features despite being a top SHAP driver. It is also **blind to therapeutic relevance**: drug-validated targets sit at background level on it. Kept as a diagnostic column. |
| `ppi_common_neighbors` | Redundant — ρ +0.96 with `ppi_jaccard`, +0.93 with `ppi_adamic_adar`. |
| `shared_pathway_count` | Redundant — ρ +0.90 with `gene_n_pathways`; the normalized form is better. |
| `pagerank`, `triangles`, `eigenvector_centrality`, `clustering_coefficient` | **Collinear duplicates of degree** (ρ +0.98 / +0.93 / +0.80) and **gene-only** — no disease information. Four encodings of one axis let the hub signal outvote the hub *penalty*. |
| `has_inflammatory_go_annotation` | Built as a priority-1 candidate. **88% null, single-feature AUC exactly 0.5000.** Lesson: *graded relational features beat binary gene-level flags.* |
| `disease_family_id`, `anchor_name`, `hop_depth` | Split bookkeeping (§5). The family id would be a direct leak. |

> **Two transferable rules came out of this table.**
> 1. **Disqualify a feature when its *missingness* is set by a label lookup**, not when its values
>    correlate with the label. That is what separates `rwr_score` (rejected) from `prox_closest`
>    (acceptable): null gaps of −75 pp versus +0.43 pp.
> 2. **Never build per-disease *count* features.** They are base-rate encoders or label-derived
>    shortcuts. Stick to gene-to-module **relational** features.

### 4.3 Why the metapaths are matrix code, not graph queries

*Source: no artifact — engineering rationale.*

The two functional-similarity metapaths exhausted the graph engine's buffer pool as Cypher **even
with a fan-out guard**, because the engine materializes every intermediate path before aggregating.
Only **12 of 11,187** terms exceeded the fan-out cap, so no threshold tuning would have helped.

The DWPC weight **factorizes**, so associating right-to-left never forms the gene×gene matrix:

```
S = X @ (W_A @ (X.T @ (W_m @ Z)))     X: genes×annotations,  Z: genes×diseases
    X.T @ (W_m @ Z)  ->  annotations × diseases   (~10k × 1.2k)
    X   @ (...)      ->  genes × diseases         (the answer)
```

Both metapaths then run in **~2 minutes**. The self-path exclusion and leave-one-out module size are
handled analytically rather than by masking.

## 5. Splitting strategy — leakage control

**Three distinct leaks were found and fixed. Each was discovered by a result that was *too good*,
and each needed a different control.** This is the most transferable section of the document.

| # | Leak | Symptom | Fix |
|---|---|---|---|
| 1 | **Random split** | AUC 0.993 — a disease's pairs land in both folds, and every feature is proximity-to-*that*-module, so the model memorizes known modules | **Disease-grouped split** |
| 2 | **Missing-data / easy-negative** | AUC 0.989 even when grouped. No feature separated by *value* (best 0.685), but the **null pattern** did — features present for positives, absent for far negatives | **Candidate-pool restriction** (§5.2) + reject label-derived features + mean imputation (§6.2) |
| 3 | **Ontology hierarchy** | Parent and child disease terms share biology; a parent in validation with its child in train leaks | **Disease-family split** (§5.3) |

### 5.1 Prediction unit and eligibility

*Source: `enriched_graph_features_1_family`.*

**Unit:** a `(gene, disease)` pair → P(true association).
**Disease eligibility:** ≥ 20 protein seeds, so network features are estimable — 1,154 of 27,153
diseases qualify.

### 5.2 The candidate pool is a leakage control, not a convenience filter

*Source: `enriched_graph_features_candidate_psplit`, `enriched_dwpc_GGD` / `_GPGD` / `_GCD` · `nb2`.*

Keep only pairs where **at least one typed metapath route exists**.

| Stage | Rows | Positive rate |
|---|--:|--:|
| All (gene, eligible-disease) pairs | 18,396,158 | 0.90% |
| After the has-path-evidence restriction | **6,754,128** | **1.89%** |

Without it, features are present for positives and absent for far negatives, and imputation turns
"no evidence of that type" into a label proxy — leak 2. It also scopes the deliverable honestly:
*prioritize plausible candidates **within** the disease's known molecular context*, not "discover
out-of-neighborhood targets".

**Known limits of that scope:** mechanistically distant targets are unreachable, biasing toward
incremental over serendipitous; the ~80% incomplete interactome turns "no mapped path" into false
exclusion; and study bias over-weights well-annotated genes.

**Expanding the restriction to include the functional metapaths was measured and rejected** — it
grows the pool to 15.8M at 1.04% positives and makes coverage equalization *worse* on every original
feature, pushing the filter back toward the no-op state that produced leak 2. A stricter
≥2-of-3 variant nearly eliminates the missingness channel (mean |gap| 16.5 → 4.2 pp) but keeps only
49.8% of positives — logged as a future experiment, not adopted.

> **⚠ One of the three route features is load-bearing and invisible.** No model uses it, visual ML
> auto-rejects it for excessive nulls, and it holds only 42,227 rows — yet it is one of the three
> terms in the pool restriction.

#### 5.2.2 Adding `prox_closest` as a fourth route — tested and rejected

*Source: `enriched_graph_features_1` (pre-filter, 21,308,566 rows) scored counterfactually with `m5-f13` · `nb2`.*

The motivating case is §8.10's `TACSTD2`: a curated therapeutic pair at score 0.90 for triple-negative
breast carcinoma that the model cannot see, because it has no GGD, GPGD or GCD route. `prox_closest`
*does* reach it, so admitting pairs on a fourth route would close the gap. **Measured end to end, it
should not be done.**

| | |
|---|--:|
| pool | 6,754,128 → **18,283,793 (+170.7%)** |
| **triple-negative's own pool** | 2,563 → **15,937 (6.2×)** |
| positive rate | 1.887% → **≈0.70%** |
| recall ceiling | 98.5% → **100.0%** (all 34 pairs) |

The positive rate lands *below* the functional-metapath expansion §5.2 already measured and rejected
(15.8M at 1.04%). But the decisive objection is not size — it is that **the admitted pairs cannot be
scored.** On all 13,407 counterfactual rows:

| input | null share |
|---|--:|
| `dwpc_GGD`, `dwpc_GPGD`, `ppi_adamic_adar`, `ppi_common_neighbors_z` | **100%** |
| `dwpc_GBGD` / `dwpc_GFGD` | 64% / 69% |

**Four of thirteen inputs are null on every admitted pair, by construction** — a pair reachable only by
`prox_closest` has no GGD/GPGD route, and the shared-neighbour features require exactly that. Mean
probability of admitted pairs is **0.1426 against 0.2738** across the existing pool — **52%**, which
independently reproduces §5.2.1's GCD-only figure of 49% from a completely different direction.

**Where they would actually rank:**

| | |
|---|---|
| **`TACSTD2` for triple-negative** | **#845 of 2,564 — top 33%** |
| the 23 scoreable unreachable curated pairs | median rank **1,119**, **0 in the top 50, 0 in the top 200** |
| best case across all of them | FSHR / hypogonadism at #259 of 2,471 |
| triple-negative's 13,374 admitted genes | **21 would take top-50 slots** |

**Not one recovered pair would be findable**, in a deliverable that shows the top 20–200. And the last
row is the reason to reject rather than merely decline: 21 of the top 50 slots would go to pairs scored
on mostly-imputed inputs. **The change would contaminate the head of the list while adding nothing to
the tail anyone reads.**

> **The gate is not the problem; the feature family is.** Every topology feature here is built on local
> neighbourhood overlap, so for a pair with no shared neighbours there is nothing to compute — widening
> admission just produces unscoreable candidates. **No single feature fixes this**, `d_shortest`
> included: it would be live where GGD and GPGD are dead, but three other inputs stay null.

#### 5.2.1 `dwpc_GCD` is the drug route, and it selects the population on the outcome

*Source: `pool_reachability`, `pool_selection_bias`, `pool_unreachable_targets` · `nb2`.*

Investigated 2026-08-19 (`compute_pool_reachability`). **`C` is Compound.** The proof is an identity,
not a correlation: **100.0% of approved-join drug pairs that sit in the pool carry a GCD route.**

That makes the third term of the pool filter *"a drug exists that hits this gene and is indicated for
this disease"* — which is the label the drug-based axes in §7.4 and §8.1–8.4 are scored against.

| | share of the pool | share of approved-join positives |
|---|--:|--:|
| admitted **only** by the GCD route | **0.153%** (10,337) | **25.4%** (344) |

**A 91.8× enrichment.** One in four approved drug-target positives is in the evaluation population
*only because of the relationship being evaluated*.

**Two things make this a bias rather than a leak.** `dwpc_GCD` is `role=REJECT` — no model consumes
it — so nothing leaks into the *features*. But a GCD-only pair has, by construction, **no GGD and no
GPGD route**, so two of the twelve model inputs are null and imputed. The model is handed pairs it has
no disease-specific signal for, and then scored on them.

**Measured consequence — it depresses the drug-target metric that §7.4 reads as an objective
limitation:**

| Drug-target AUC (approved join) | value |
|---|--:|
| all positives *(the documented number)* | 0.6886 |
| positives the model has route features for | **0.7471** *(+0.0585)* |
| on the 69 affected diseases only | 0.6041 → **0.7060** *(+0.1019)* |

Direct confirmation of the mechanism: GCD-only positives receive mean `proba_1` of **0.217** against
**0.543** for route-supported positives (344 GCD-only against 1,194 route-supported) — half the score, because half their route features are absent.

**So the pool restriction trades one bias for another.** It was adopted to kill the missing-data leak
(leak 2); it introduced outcome-dependent selection on the drug axis.

**Do not fix it by dropping GCD from the pool.** ⚠ That was this section's first recommendation and it
was wrong on cost. The pool cost is genuinely trivial (10,337 rows, 0.153%; ~64 association positives),
but the *evaluation* cost is not: **22 of 206 diseases lose every curated therapeutic positive** and 77
more lose some, because those positives are exactly the GCD-only ones. Removing them from the
population makes 10.7% of the evaluable diseases go dark on the therapeutic axis.

**The correct fix changes the metric, not the population.** Keep GCD in the pool; exclude GCD-only
pairs from the *drug-based denominators* and report both numbers. Identical bias removal, no disease
lost, no re-fit, and the stratification is itself informative:

| Drug-target AUC, approved join | value | what it answers |
|---|--:|---|
| all positives | 0.6886 | how the model ranks approved targets among everything in its population |
| route-supported positives only | **0.7471** | how it ranks the approved targets it can actually see |

That pair dominates dropping the route, which would have bought the same number at the price of 22
diseases.

> **The reported 0.6886 is not wrong, but it answers a worse question than 0.7471 does.** Report both:
> one is "how the model ranks approved targets among everything in its population", the other is "how
> it ranks the approved targets it can actually see".

### 5.3 The family split — an external curated antichain

*Source: `hetionet_disease_slim`, `mondo_references`, `disease_family_id`.*

Since no clean partition of the ontology exists (§3.2), we borrow one. A curated reference network
published **137 disease-ontology terms under an explicit antichain constraint** — *no term is a
subtype of another* — exactly the property needed. We reuse that curation as a fixed **anchor set**,
not as our disease universe. It contributes **no nodes and no edges to the graph**.

Each disease walks **up** the native directed hierarchy (the pre-reversal table — assembly destroys
direction, see GRAPH_BUILDING §4.3) to its **nearest** anchor; ties break on shallowest depth then
lowest index; no anchor within 15 hops falls back to its own index (never worse than a plain disease
split). Because anchors are a *static lookup* rather than nodes that accumulate unions, ambiguity
stays **local** (7.4% of diseases reach >1 anchor) instead of cascading.

| Metric | Value |
|---|--:|
| Anchor terms mapped onto our vocabulary | 136 / 137 |
| Usable anchors in the current graph | 110 |
| Diseases resolving to an anchor | 317 / 1,157 (27.4%) |
| Families produced | **927** (from 1,157 diseases) |
| Multi-member families | 24 |

**Both persona pairs resolve automatically** — `breast cancer` *is* an anchor at depth 0 with
`breast carcinoma` at depth 1; likewise obesity.

**Honest scope: this mitigates, it does not solve.** 73% of diseases find no anchor and retain only
disease-level protection. The external curation skews to well-studied common diseases, so coverage is
best exactly where the personas live and worst in the long tail.

### 5.4 The split as implemented

*Source: `split_audit_2` · `nb2`. **The recipe was broken 2026-08-17 → 2026-08-19** — see the warning below.*

> **⚠ This section's guarantee was unverified between 2026-08-17 and 2026-08-19.** `compute_split_audit_2`
> had its declared inputs migrated to the `psplit_*` datasets but its **code still read
> `enriched_train_full_2`**, so every build failed and `split_audit_2` sat empty while this section
> quoted a pre-migration run. Fixed and rebuilt 2026-08-19; the guarantee **holds** — all three
> split-key overlaps are 0, zero keys straddle, and all 13 persona diseases land in validation. The
> lesson is in [DECISIONS.md](../../DECISIONS.md): repointing a recipe's inputs does not repoint its code.

The split key is the **elevated split key** — the anchor's most-specific parent under a fan-out cap —
**never the disease index**. Persona families are forced into validation. Roughly 41% train / 50%
validation / 9% test by row count.

```
if(arrayContains([0,1,2,3,4], mod(disease_split_key, 10))
   || disease_split_key == 46033      // overnutrition      -> obesity disorder, morbid obesity
   || disease_split_key == 45109      // thoracic cancer    -> breast cancer, breast carcinoma
   || disease_split_key == 47437      // diabetes mellitus  -> type 2 diabetes
   || disease_split_key == 47654      // chronic kidney disease
   || disease_split_key == 45876,     // respiratory system cancer -> lung cancer, adeno, NSCLC
   "validation", if(mod(disease_split_key, 10) == 5, "test", "train"))
```

**⚠ The forced clause is the only guarantee — the modulo is not.** Of the four keys originally
forced, three already fell in validation via the modulo, so only one was doing real work. That is a
trap: when indices are renumbered, whichever keys were *incidentally* in validation can move — which
is exactly what the 2026-08-17 rebuild did (see [DECISIONS.md](../../DECISIONS.md), 2026-08-17 entries, and
`index_remap.json`).

**As rebuilt, all five persona groups land in validation via the forced clause**, and the elevation
step merged breast and lung under `thoracic cancer`, so the `respiratory system cancer` entry
is now redundant — retained because it costs nothing and correctly expresses the intent. Only type 1
diabetes, which is a watch-list disease rather than a persona, sits in train.

## 6. Model configuration and selection

### 6.1 The audit that drove feature selection

*Source: `psplit_train_set` (25% sample) · `nb1`. Re-measured 2026-08-19; two claims revised, one refuted.*

Re-measured 2026-08-19 on a 547,242-row sample of `psplit_train_set` (notebook `nb1`). Two of the three
original claims hold with larger effects than recorded; the third is **refuted**.

**1. Gene-only features cannot answer disease-specificity — confirmed exactly.** Share of genes taking
more than one distinct value across the diseases they appear in:

| feature | varies across diseases | in champion model |
|---|--:|:--|
| `gene_ppi_degree` | **0.00%** | **yes** |
| `gene_n_pathways` | **0.00%** | **yes** |
| `gene_n_diseases` | 0.00% | no — rejected |
| `dwpc_GGD` | 81.94% | yes |
| `dwpc_GPGD` | 68.84% | yes |
| `module_size` | 96.04% | no |

⚠ **Two of the twelve champion features are gene-only.** The audit was described as having removed
them; `gene_ppi_degree` and `gene_n_pathways` survived. They are defensible as hub-normalisation terms,
but they answer *"is this gene generally prominent"*, never *"for this disease"*.

**2. The hub axis is over-represented — and worse than recorded.** Spearman ρ against `degree`:

| | ρ |
|---|--:|
| `gene_ppi_degree` | **+1.000** |
| `pagerank` | +0.981 |
| `triangles` | +0.934 |
| `eigenvector_centrality` | +0.841 |

**`gene_ppi_degree` and `degree` are the same variable.** Previously recorded as +0.975 / +0.927 /
+0.804 — every value was understated, and the perfect duplicate was not noted at all. The model keeps
one of the pair, which is correct.

**3. REFUTED — "≈0.5 for every gene-only feature" is wrong, and the exception is the important one.**
Within-disease single-feature macro AUC:

| feature | AUC | |
|---|--:|---|
| **`gene_n_diseases`** | **0.8567** | **rejected as label-derived — and it alone beats the 14-feature champion's 0.8230** |
| `dwpc_GPGD` | 0.7182 | previously recorded 0.641 |
| `dwpc_GGD` | 0.6694 | previously recorded 0.601 |
| `gene_ppi_degree` | 0.5608 | |
| `module_size` | 0.5000 | |

> **The gene-popularity shortcut is not confined to the drug axis.** §7.5 found a "how many diseases is
> this gene a drug target for" lookup scoring **0.9354** on the drug benchmark. The association axis has
> the same hole: **"how many diseases is this gene associated with" scores 0.8567**, above the champion.
> Rejecting `gene_n_diseases` (§4.2) was not conservatism — it was the difference between a model and a
> popularity table.

### 6.2 Configuration

*Source: `psplit_train_set` / `_test_set` / `_validation_set` row counts · `nb1`.*

| Setting | Value | Note |
|---|---|---|
| Algorithm | **gradient-boosted trees** | logistic regression comparator: 0.834 vs 0.895 pooled — the non-linearity is worth ~0.06 |
| `max_depth` | grid 4–6 | |
| `n_estimators` | 300, early stopping on | |
| Class handling | class weights | positives are ~1.9% |
| Seed | 1337 | also the split seed |
| Evaluation metric | ROC AUC, macro | but **report per-disease AUC** (§7.1) |
| Train/test policy | two explicit datasets | `psplit_train_set` / `psplit_test_set` (**2,187,862 / 607,345**; validation 3,958,921 — the three sum to the pool exactly) |

**Feature-handling standard (mandatory): every numeric input gets standard rescaling + mean
imputation. No exceptions.**

- **Rescaling is a no-op for trees** — it is affine and monotonic, and tree splits are invariant to
  monotonic transforms. It matters for the logistic comparator, so uniformity is cheap insurance.
- **Imputation is the one that bites.** The platform imputes *before* the model, so the algorithm's
  native sparsity handling never engages and the fill value is decisive. **Mean** puts nulls at the
  distribution centre, indistinguishable from average rows, so the tree **cannot** isolate "was
  missing". **Constant 0** puts them at a separable point, so it **can** — and with four features
  carrying **−31.7 pp null gaps by label** (measured, `nb1`), that reopens leak 2 outright. For a z-score, 0 is doubly
  wrong: it is the null-model expectation, mid-distribution (real median +2.55).
- **Sentinel imputation was tested as a fix and rejected on the second metric.** A large negative
  constant gave the **best pooled AUC in the project (0.8808) and the worst drug-target AUC
  (0.6579)**. Missingness is 93–99.7% gene-level, so exposing it hands the model a real gene-level
  signal that improves association ranking and degrades therapeutic ranking.
- **A presence-flag model cannot answer "do the nulls reveal the target"** — the platform imputes
  before per-feature handling, so every flag is 1 and the model emits one constant value. Materialize
  explicit null-indicator columns instead (see DSS_CHEATSHEET §1).

### 6.3 The threshold is not the ranking

*Source: `scored_m3` · `nb1`.*

The F1-optimised threshold lands at **0.860** against a ~1.9% base rate (F1 = 0.218). Consequence:
**552 of 762 known obesity targets are predicted negative**, recall **27.6%**.

> **The prediction column is near-meaningless for discovery. Rank by probability and take top-N** —
> which is what the persona chain does.

### 6.4 Model selection — four axes, and why AUROC alone would have chosen wrong

*Source: `scored_m3` / `scored_m4` / `scored_m5` for the f12/f13 rows · `docs/appendix/model_comparison.csv` for `m1`/`m2` (that flow artifact was deleted 2026-08-19 and is not re-derivable without re-scoring 7.9M rows) · `FEATURE_AUDIT.md` §4 and the paired tests logged in `DECISIONS.md` 2026-08-20/21 for `m6`–`m8` · champion metrics re-measured in `nb3`/`nb3b`/`nb4` on 2026-08-21.*

#### The `prox_closest` question, settled on four axes

`m4` and `m5` add exactly one feature to the champion — `prox_closest`, the only input that is
degree-insensitive and able to see past two hops (§4.1). They differ only in how its NULL is handled:
NULL means *"beyond 3 hops"*, so `m4` mean-imputes it to ≈2 (label-blind but semantically wrong) and
`m5` imputes the constant 4 (semantically right, but §6.2 warns a separable constant can reopen leak 2).

| Axis | `m3-f12` | `m4` (+prox, mean) | `m5` (+prox, const 4) |
|---|--:|--:|--:|
| association — macro AUROC | 0.8197 | **0.8200** | 0.8175 |
| association — macro AUPRC | 0.1737 | **0.1762** | 0.1711 |
| association — pooled AUPRC | 0.3161 | **0.3210** | 0.3089 |
| hub-bias spread *(lower better)* | 0.1954 | 0.1932 | **0.1915** |
| therapeutic — drug AUC, all positives | 0.6911 | **0.6949** | 0.6931 |
| therapeutic — route-supported (§5.2.1) | 0.7337 | 0.7371 | **0.7384** |
| tractability — pooled dm lift@10 | 3.057 | **3.241** | 3.129 |
| tractability — pooled dm lift@50 | 2.794 | **2.841** | 2.774 |
| tractability — pooled dm lift@200 | 2.376 | **2.381** | 2.380 |
| **discovery — lift@10** | 11.40 | 13.81 | **16.09** |
| **discovery — lift@50** | 7.46 | 7.09 | **9.08** |
| **discovery — lift@200** *(the robust one)* | 4.53 | 4.83 | **5.52** |

**No model dominates, and the split is coherent rather than noisy:**

| | wins |
|---|---|
| **`m4`** | association (all three measures), therapeutic on all positives, **tractability at every K** |
| **`m5`** | **discovery at every K**, hub spread, therapeutic on route-supported positives |

**`m4` is better at ranking what is already validated** — known association targets, genes that already
carry a drug. **`m5` is better at surfacing what is not yet validated for that disease.** That is the
same tension §7.5 found when training on the drug label, appearing again from a one-feature change.

**On magnitude the discovery gain wins.** `m5` beats `m4` by **+16% / +28% / +14%** at K = 10/50/200 on
discovery; `m4` beats `m5` by **+3.6% / +2.4% / +0.04%** on tractability, converging to a dead tie by
K=200 — and §8.4 says the deep-list number is the one to quote. The association cost is −2.9% macro
AUPRC, on the metric §7.4 proved does not predict therapeutic relevance.

> **Recommendation at the time: `m5`.** It pays a modest, well-characterised price on axes that measure
> re-identification, to buy the largest single movement anywhere in this table on the axis that measures
> discovery — which is what the deliverable claims to do. **This is a product decision, not an
> optimisation; §7.4 is the reason it cannot be settled by picking the biggest number.**
>
> **⚠ SUPERSEDED 2026-08-21 — `m5` was never adopted.** Its discovery lead did not survive a paired
> test: `m5` and `m6` are the same ranker for ~90% of diseases, and the lift gap above rests on 9–15
> high-leverage diseases (**115 of 122 exact ties at K=10**). The champion is now **`m7-f14`** — see
> *The full sequence* below. The reasoning here is kept because the four-axis framing is what stopped
> `m5` being rejected on macro AUROC alone, and that framing is still the right one.

**`m5` loses 2.9% of association AUPRC and gains 14–28% of discovery lift at every K.** Since §8.3's
discovery measure *is* the deliverable's central claim and §7.4 proved association AUC does not predict
therapeutic relevance, that is the trade to take. **On macro AUROC alone `m5` looks like a regression**
(0.8197 → 0.8175) — which is exactly how a two-axis assessment would have thrown it out.

#### The leak-2 test — the concern did not materialise

§6.2 predicted a separable imputation constant would let the tree isolate *"was missing"*, and
`prox_closest`'s nullness **is** label-informative (null in 1.64% of positives vs 6.56% of negatives).
Tested by re-scoring every model on the prox-**present** rows only — if a model's advantage came from
exploiting nullness, it would vanish there:

| | gap on all rows | gap on prox-present rows only |
|---|--:|--:|
| `m4` − `m3` pooled AUPRC | +0.0049 | **+0.0049** |
| `m5` − `m4` pooled AUPRC | −0.0121 | **−0.0123** |

**Identical to four decimals.** No model's gain or deficit comes from missingness — the differences are
entirely in how each uses the *observed* distances. Leak 2 did not reopen, presumably because this
feature's −4.99 pp null gap is far below the −31.7 pp features that motivated the mean-imputation rule.

> **`m5`'s association deficit is real ranking loss, not a leak — and its discovery gain is real too.**
> The likely mechanism for both: injecting 4 for 6.5% of rows under `AVGSTD` rescaling stretches a
> feature whose observed values are only 1, 2 and 3 (64% at 2), compressing the distinctions that carry
> signal among *known* targets while sharpening far-vs-near among *novel* ones — which is where
> discovery is measured.

#### `MIN_SEEDS = 20` has no recorded justification, and the evidence argues for lowering it

*Source: `enriched_prox_closest`, `enriched_graph_features_candidate_psplit`, `graph_edges` · `nb1`.*

`compute_enriched_prox_closest` skips any disease with fewer than 20 PPI-mapped module genes, so every
pair for it is NULL. **The constant carries no comment, no doc reference and no decision-log entry** —
it is a bare literal. The likely provenance is the ≥20-gene threshold used in the disease-module
literature (Menche et al., *Science* 2015) for testing whether a disease forms a *statistically
significant module*. That is a different question from "can we measure a distance to these seeds",
which needs seeds, not a significant module.

**What it costs.** NULL `prox_closest` has two causes and only one is fixable here:

| cause | share of pool | share of all NULLs |
|---|--:|--:|
| (a) disease below `MIN_SEEDS` | 1.23% | **18.7%** |
| (b) gene beyond `MAX_HOPS = 3` | — | **81.3%** |

Lowering the threshold addresses (a) only — about a fifth of the NULL population, taking the null rate
6.57% → 5.34%. **And it is nearly free:** at `MIN_SEEDS = 10` only **one** disease is excluded and
**0.00%** of pool rows, so 42 of the 43 currently-excluded diseases have modules in the narrow 10–19
band.

**What it protects — nothing.** The threshold's implicit rationale is that few seeds make an unstable
estimate. That is true of a *mean*, and false of a *minimum*. Measured, the feature discriminates
**best** exactly where the threshold cuts:

| module size | diseases | single-feature AUC of `prox_closest` | hop 1 / 2 / 3 |
|---|--:|--:|---|
| **20–30** | 225 | **0.6459** | 37.8% / 52.8% / 9.4% |
| 31–60 | 316 | 0.5978 | 40.2% / 52.5% / 7.3% |
| 61–120 | 238 | 0.5950 | 46.5% / 48.7% / 4.8% |
| 121–300 | 193 | 0.5876 | 56.0% / 41.1% / 3.0% |
| **>300** | 139 | **0.5673** | **73.9%** / 24.7% / 1.3% |

**Spearman(module size, prox AUC) = −0.328.** The mechanism is in the last column: with a large module,
**74% of all pairs sit at hop 1** and the minimum is nearly constant. With a small module the mass
spreads across all three hops and the feature has real dynamic range.

> **`MIN_SEEDS` excludes the regime where this feature works best, to guard against instability a
> minimum does not suffer.**

**The same constant gates three recipes and four features — and only one of them needs it.**

| recipe | constant | features produced | in the champion? |
|---|---|---|:--|
| `compute_enriched_prox_closest` | `MIN_SEEDS = 20` | `prox_closest` | `m4`/`m5` only |
| `compute_dwpc_go_metapaths` | `MIN_MODULE = 20` | **`dwpc_GBGD`, `dwpc_GFGD`** | **yes, both** |
| `compute_enriched_rwr_score_1` | `MIN_SEEDS = 20` | `rwr_score`, `rwr_norm` | no — rejected |
| `compute_ppi_cn_zscore` | *(none)* | `ppi_common_neighbors_z` | yes |

So lowering it converts the same 43 diseases and ~1.2% of pool rows from NULL to real **across three
features at once**, two of which are current champion inputs — and `nb1` measured those two among the
worst null gaps by label (`dwpc_GFGD` **−22.89 pp**, `dwpc_GBGD` **−17.75 pp**), which is the very
missingness channel §6.2's imputation rule exists to suppress. **Shrinking their NULL population is
worth more than arguing about how to impute it.**

**Why not drop it to zero.** Three reasons, of which exactly one is a real constraint:

1. **RWR genuinely needs a floor.** `KFOLD = 5` — the seed set is split into five held-out folds so a
   seed never contributes to its own score. At 20 seeds that is 4 per fold; at 5 it is 1; below 5
   `np.array_split` emits empty folds. **A floor near 10 is principled *for RWR*, and this is the only
   place the number was ever earned.** The other two recipes inherited it.
2. **`prox_closest` has a structural floor at k = 1, for a different reason.** The recipe sets each
   seed's own distance to infinity. With a one-gene module that gene gets NULL while every other gene
   gets a value — **NULL becomes a perfect positive indicator for that disease.** At k = 2 it degrades
   to a bias (a positive takes the minimum over k−1 seeds, a negative over k, so positives look
   systematically farther) which vanishes as k grows. **A floor of 2–3 is necessary; 20 is not.**
3. **Below a few seeds a disease cannot be evaluated anyway** — no per-disease AUC, negligible training
   contribution. That is a question of what is worth computing, not of correctness.

> **Recommended: stop sharing one magic number across three different problems.** `prox_closest` and the
> GO metapaths → **5**; `rwr_score` → **10** (or lower `KFOLD`). The GO-metapath change is the highest
> value of the three because it improves the **current champion**, not a candidate.
>
> ✅ **CHECKED 2026-08-20 — no leak, and that recipe is the most careful of the set**
> (`FEATURE_AUDIT.md`). `compute_dwpc_go_metapaths` removes the `m == g` self-path *analytically*
> and uses a leave-one-out module size (`mod_D_loo = mod_raw − [g in module]`). The same check across
> every feature recipe came back clean: `dwpc_GGD`, `dwpc_GPGD` and `guilt_by_association` all carry
> both guards, `shared_pathway_count` normalises by the gene's own pathway count so LOO does not apply,
> and `dwpc_GCD` routes through a compound so self-inclusion is impossible.
>
> **This also sharpens the `d_shortest` case for `m6`:** min-distance is *already good* for sparse
> diseases and saturates for dense ones — which are the majority of pool rows. A mean or kernel distance
> does not saturate at 300 seeds, so it would fix precisely the regime min-distance cannot.
>
> **Status of the three changes, 2026-08-21:**
>
> | change | state |
> |---|---|
> | `prox_closest` → 5 | ✅ **done** (`m6`), capped to the pool so the population did not move |
> | graded distance instead of the minimum | ✅ **done** (`m7`, `prox_kernel`) — and the saturation mechanism predicted here was **refuted**, Spearman −0.003 |
> | GO metapaths → 5 · `rwr_score` → 10 | ⏳ **not started** — these gate the **pool routes**, so lowering them changes the candidate population and every number in this document stops being comparable. To be tested in a duplicated project, not in place |
>
> ⚠ **The claim above that the GO-metapath change is "highest value because it improves the current
> champion" was written before that consequence was understood.** It does improve the champion's
> features, but it also moves the training population, which is why it is the one change that cannot be
> made in place. Sequence agreed: size the admitted population first, then run a train-narrow /
> score-wide probe with `m7` against a gene-popularity baseline, and only branch the project if the
> probe clears it. **Pre-registered in
> [PHASE3_PREREGISTRATION.md](PHASE3_PREREGISTRATION.md)** before the branch exists.

#### The full sequence — `m7-f14` adopted, `m8` rejected

The `m4`/`m5` comparison settled one feature's *imputation*. Three further models settled the seed
threshold and the feature *family*, and the champion changed. **All five models on eight axes:**

| axis | `m3-f12` | `m4` | `m5` | `m6` | **`m7-f14`** | paired `m6` → `m7` |
|---|--:|--:|--:|--:|--:|---|
| association — macro AUROC | 0.8197 | 0.8200 | 0.8175 | 0.8197 | **0.8230** | **t = +3.29, 0 ties** |
| association — macro AUPRC | 0.1737 | 0.1762 | 0.1711 | 0.1749 | **0.1778** | **t = +3.18** |
| hub-bias spread *(lower better)* | 0.1954 | 0.1932 | 0.1915 | **0.1900** | 0.1935 | worse than `m6` |
| therapeutic — all positives | 0.6911 | 0.6949 | 0.6931 | 0.6949 | 0.6886 | worst of five |
| therapeutic — route-supported (§5.2.1) | 0.7337 | 0.7371 | 0.7384 | 0.7418 | **0.7471** | best of five |
| tractability — dm lift@200 | 2.376 | 2.381 | 2.380 | 2.391 | **2.418** | **t = +2.56, 0 ties** |
| discovery — lift@50 | 7.46 | 7.09 | 9.08 | 7.43 | **9.43** | t = +1.47, **90% ties — n.s.** |
| discovery — lift@200 | 4.53 | 4.83 | **5.52** | 4.78 | 5.04 | t = +0.70, **78% ties — n.s.** |

**`m6` refuted its own pre-registered prediction — and that is why it earned its place.** Lowering
`MIN_SEEDS` 20→5 on `prox_closest`, capped to the pool so the population could not move, filled NULLs
for **42 of 43** affected diseases. Predicted: those diseases improve markedly. **Measured: 64% improved
against 63% of the 646 controls, t = 1.29 — nothing.** The apparent +0.0152 macro gain was a mean
dragged by outliers (Raynaud +0.137 against rheumatic heart disease −0.114). What `m6` *did* produce was
a global gain by an unpredicted mechanism: the 646 diseases whose features are **byte-identical** between
`m5` and `m6` improved significantly (**t = 3.42**), so the benefit came from a better *training set*,
not from those diseases being scored better. **Only the stratified paired test separated those two
readings** — the macro number alone read as a clean 9×-over-control win.

**`m3` through `m6` are the same ranker for roughly 90% of diseases.** Discovery lift@10 shows **115 of
122 exact ties** between `m5` and `m6`, every median exactly 0.000; every aggregate difference in the
table above rests on 9–15 high-leverage diseases. **`m7` is the break in that pattern.** `prox_kernel`
is continuous, so unlike every earlier change it perturbs the whole population: **zero exact ties over
668 diseases, 414 better / 254 worse, median +0.0023.** The tie count is the finding, not the mean.

##### `m8` scored better on the headline metric and was rejected

`m8-f14-pm` swaps `prox_kernel` for `prox_mean` — same feature family, different aggregation. The trade
was pre-registered from the degree correlations in §4.1 and then confirmed:

| paired `m7` → `m8`, 668 diseases | result |
|---|---|
| association — macro **AUPRC** | 0.1778 → **0.1816, t = +3.42 (significant)** |
| association — macro AUROC | 0.8230 → 0.8225, **t = −0.42 (no difference)** |
| **tractability — dm lift** | @10 t = −1.26 · @50 t = +0.01 · @200 median −0.035, t = −1.34 |
| hub-bias spread | 0.1935 → **0.1968** (third consecutive worsening: 0.1900 → 0.1935 → 0.1968) |
| discovery | non-finding either way, 79–93% ties |

**The decisive reading: `m8` buys AUPRC without buying tractability.** If `prox_mean` were finding
genuinely better targets, the uninflated, degree-matched axis should move *with* the association metric.
It does not. AUPRC up, tractability flat-to-declining, hub bias worse — and the responsible feature is
the one measured at ρ = **−0.697** with `gene_ppi_degree`, against `prox_kernel`'s **+0.216** (§4.1).
**That is the signature of exploiting label bias rather than improving target-finding, which is exactly
what §8.4's degree-matched null exists to detect.** §3.1 already established the label is itself
study-biased toward hubs, so a feature that discriminates *because* it tracks degree is the thing this
project has repeatedly decided not to want.

> **Adopted: `m7-f14` (saved model `hJLGoYn4`).** Two significant gains, each with **zero ties** — on
> association *and* on tractability, the axis §8.4 calls the most robust positive claim in this
> document. `m8` offers one significant gain, on the metric §7.4 proved does not predict therapeutic
> relevance, paid for in hub fairness and tractability.
>
> **The decision rule this establishes: an association gain must be corroborated on the degree-matched
> axis, or it is not adopted.** `m8` is the case that rule was written for, and it is the most
> defensible thing in this section — a model was rejected for scoring better.
>
> **`m7`'s costs are logged, not hidden.** Hub spread worsens against `m6` (0.1900 → 0.1935), though it
> still improves on the `m3-f12` it replaced (0.1954); §7.2's refutation stands regardless, since both
> are far worse than the retired 13-feature generation's 0.1099. Therapeutic-on-all-positives is the
> **worst of the five** (0.6886) while route-supported is the **best** (0.7471) — the largest gap in the
> sequence (**0.0585**), which under §5.2.1 reads as the gain concentrating where features actually
> exist rather than on unscoreable GCD-only pairs.
>
> **And the mechanism is refuted.** `prox_kernel` was designed around module-size saturation, but
> **Spearman(module size, per-disease delta) = −0.003**; the gain is flat above size 20 and *largest in
> the smallest* modules (20–60: +0.0055; >300: +0.0025), while the <20 bucket got **worse** (−0.0117,
> n = 22, n.s.). **`m7` works and we cannot say why** — which, given this thread's record of refuted
> hypotheses, warrants less confidence than an explained gain of the same size. It also argues for
> caution on the pending seed-threshold work, whose whole point is to admit more small-module diseases.

#### The original ladder

All three `m1`–`m3` runs share the split, hyperparameters, handling standard and row counts, and all
exclude `prox_closest`, so they are directly comparable.

Rebuilt on the shared graph, 670 validation diseases (130 with a drug-validated target). Reference
values from the frozen project are shown alongside — **the ordering is preserved on both axes.**

| Model | Feat | **Macro per-disease AUC** | *(reference)* | **Drug-target AUC** | *(reference)* | hits@50 |
|---|--:|--:|--:|--:|--:|--:|
| `m1-f7` | 7 | 0.7593 | *0.7617* | 0.6787 | *0.6716* | 128 |
| `m2-f10` | 10 | 0.7882 | *0.7846* | 0.6880 | *0.6845* | 113 |
| **`m3-f12`** | **12** | **0.8197** | *0.8228* | **0.6911** | *0.6836* | 122 |

Feature sets are cumulative: **f7** = the pruned core; **f10** = f7 + the three provenance/degree
controls; **f12** = f10 + the two functional metapaths.

**One thing improved on rebuild:** drug-target AUC is now **monotonic** across the ladder
(0.6787 → 0.6880 → 0.6911), where the reference had the metapath rung fractionally *below* the
provenance rung (0.6845 → 0.6836). A 0.0009 inversion was never meaningful; it is reassuring that it
did not survive.

**Read against both metrics, the two rungs behave differently.** Paired per-disease deltas vs
`m1-f7`: the provenance rung gains **+0.0229 association and +0.0129 drug-target** — both axes
improve. The metapath rung gains **+0.0611 association but only +0.0120 drug-target**, and the
second step alone is **+0.038 association / −0.0009 drug-target**. So **the provenance controls
bought therapeutic relevance; the functional metapaths bought association ranking almost
exclusively.**

**Three earlier findings that the ladder rests on:**

- **Pruning alone FAILED.** Removing the collinear features left pooled AUC unchanged (0.8666 vs
  0.8663) while macro per-disease AUC *fell* to 0.7610, winning on only 176 of 591 diseases. A
  textbook case of **pooled AUC hiding a within-disease loss**. Pruning was directionally right but
  removed signal without replacing it.
- **The provenance controls recovered it.** The degree-corrected module-contact feature supplied
  what pruning had stripped.
- **The functional metapaths were the decisive win, and every metric improved at once.** Normally
  accuracy and bias trade off, but the degree spread fell from +0.1879 to **+0.1099** and
  ρ(degree, probability) from +0.3304 to **+0.2424** — so they bought accuracy with genuinely *new,
  degree-independent* signal. **Unanchored diseases gained most** (0.7508 → 0.7965 vs anchored
  0.8390 → 0.8773): the poorly-annotated tail benefits more from functional similarity, because those
  are the diseases whose interactome routes are sparsest. Encouraging for generalization.

## 7. Validation

### 7.1 Metric methodology

*Source: `validation_auc_by_disease`, `validation_set_scored_grouped` · `nb3`.*

**Report macro per-disease AUC, not pooled.** Pooled AUC gets credit for separating genes across
*different* diseases (easy — a gene in a well-annotated disease outranks one in a sparse disease);
the deliverable is ranking genes *within* one disease. **Pooled overstates by ~7 points** (0.8932 vs
0.8230).

Per-disease AUC uses the Mann-Whitney rank-sum identity. **⚠ The orientation depends on rank
direction, and getting it backwards is silent** — it yields a plausible sub-random AUC alongside
perfect precision@50, which is how it was caught:

```
descending ranks (rank 1 = best score):
    auc = 1 - (positive_rank_sum - n_pos*(n_pos+1)/2) / (n_pos * n_neg)
ascending ranks (the default in most rank functions):
    auc =     (positive_rank_sum - n_pos*(n_pos+1)/2) / (n_pos * n_neg)     # NO leading 1 -
```

Restricting the headline to diseases with ≥10 positives gives **0.8323** (n=604).

**The metric is cross-validated by two independent implementations** — a visual chain and a code
recipe — agreeing on mean **0.8197** with a maximum absolute difference of **1.9×10⁻⁴**, only 31 of
670 diseases differing above 1e-6, and positive counts identical throughout. The residual is tie
handling: the two rank functions split tied scores differently. Both are kept — the visual one for
reporting, the code one because it is the only source of per-split-key AUC.

> **⚠ Compare like with like.** The code recipe emits **both** disease-level and split-key-level rows
> in one table, distinguished by a `level` column (670 + 443). Joining it to the visual chain without
> filtering to `level == "disease"` mixes the two and manufactures a 0.16 maximum discrepancy out of
> nothing — which is what happened on the first attempt at this comparison.

**Why macro AUROC and not AUPRC, given a ~1.9% positive rate.** The standard advice under imbalance is
to prefer AUPRC, and for *model selection* we now do (§6.4). For *per-disease reporting* it is the wrong
choice, and the reason is measurable:

| | correlation with a disease's own positive rate |
|---|--:|
| per-disease AUROC | **+0.27** |
| per-disease AUPRC | **+0.63** |

AUPRC's baseline *is* the prevalence, and our per-disease positive rates span **21×** (p5 0.218%, p95
4.554%), so a macro-average of AUPRC largely measures **how well-annotated each disease is** rather than
how well it is ranked. AUROC's baseline is fixed at 0.5 regardless of prevalence, which is what makes it
survive macro-averaging over a heterogeneous population. Spearman(AUROC, AUPRC) across diseases is
+0.766 — correlated, not interchangeable.

**Both are rank statistics** — AUROC is the Mann-Whitney U, and neither sees calibration — so the choice
is not "ranking vs probability". It is **which part of the ranking gets weight**: AUROC weights the whole
ordering uniformly, AUPRC weights the head.

**What we therefore report:** macro AUROC as the cross-disease comparable headline; **pooled AUPRC
0.3161 against a 1.865% base rate — 17× chance** — as the imbalance-aware second number, always with its
baseline; and for anything per-disease, `AUPRC / base_rate` rather than raw AUPRC, which is the same
family as the `lift@K` tables in §8.3 and §8.4. **`lift@K` is precision@K normalised by base rate — we
were already reporting AUPRC's ingredient in its comparable form.**

### 7.2 Hub-bias meter — the second axis

*Source: `scored_m3` · `nb3b_hub_bias_meter`. **No flow recipe exists** — the notebook is this section's only artifact.*

Among **known targets only** — biology held constant, every gene a true positive — bin by degree and
compare the lowest to the highest quintile. Baseline: Q1 (median degree 3) 6.8% predicted positive
vs Q5 (median 104.5) **40.8%** — a **6× detection swing on network position alone.**

| Model | Q1 probability | Q5 probability | Spread | ρ(degree, probability) |
|---|--:|--:|--:|--:|
| 15-feature predecessor | 0.5732 | 0.7611 | +0.1879 | +0.3304 |
| pruned intermediate | 0.5662 | 0.7417 | +0.1755 | +0.2953 |
| 13-feature metapath generation *(retired)* | 0.6516 | 0.7615 | +0.1099 | +0.2424 |
| **champion `m7-f14`** *(measured 2026-08-21)* | **0.5938** | **0.7873** | **+0.1935** | **+0.3273** |

**⚠ REFUTED for the champion.** This section previously read *"the first model that improves
under-studied targets outright rather than relatively"* — and instructed the reader to recompute before
quoting. Recomputed (`nb3`, 73,829 known-target rows across 670 validation diseases): **the champion is
worse than the retired generation on every dimension of this axis.** Q1 fell **−0.058**, Q5 rose
+0.026, the spread nearly **doubled** (+0.110 → +0.194), and ρ(degree, probability) rose +0.085.

**The hypothesised cause was tested and REFUTED.** The champion differs from the retired generation by
dropping `prox_closest`, so the obvious explanation was that this feature had been carrying the
hub-fairness — it was assessed as *"neutral on both headline metrics"*, and §4.1 shows it is the only
feature in the set that is both degree-insensitive and able to see past 2 hops. **`m4-f13` restored it
on the current split. The hub meter barely moved:**

| | `m3-f12` | `m4-f13` (+`prox_closest`) | Δ |
|---|--:|--:|--:|
| Q1 mean probability | 0.5911 | 0.5915 | +0.0004 |
| Q5 mean probability | 0.7851 | 0.7833 | −0.0018 |
| **spread** | **0.1941** | **0.1917** | **−0.0024** |
| ρ(degree, probability) | 0.3276 | 0.3246 | −0.0030 |

**That recovers about 3% of the 0.0855 gap.** So the difference from the retired generation is
**population, not the feature** — the retired row was computed over 588 validation diseases against
today's 670, and the caveat that said so was right. `prox_closest` is worth keeping for other reasons
(§6.4), but it is **not** the hub-fairness lever.

> **The honest position: hub bias is an open weakness with no identified cause.** The absolute
> 0.59-vs-0.79 gap is measured on current data and stands on its own. What does **not** stand is any
> claim that this model improves under-studied targets, or that we know why it is worse than an earlier
> one. Do not replace one unverified causal story with another — the next candidate explanation needs
> the same controlled test this one got.

**Detection swing at the F1 threshold (0.860):** low-degree known targets are predicted positive
**17.3%** of the time, high-degree **57.0%** — a **3.3× swing on network position alone**, with biology
held constant.

### 7.3 Per-family validation

*Source: `family_auc_by_family` · `nb3`, figure 1 (distribution + ranked curve).*

Same chain grouped by family: **505 families, macro 0.8009, median 0.8118, recall@20 0.1189.**
Against the 15-feature predecessor that is **+0.043 macro** and **recall@20 +17%** — which matters more
than AUC for a top-N deliverable. **`nb3` figure 1** plots the full distribution and the ranked curve,
so the worst-case tail is visible rather than summarised.

| Group | n | Macro AUC | predecessor |
|---|--:|--:|--:|
| **multi-disease families** (grouping actually applies) | 28 | **0.9023** | 0.8615 |
| single-disease families (grouping is a no-op) | 477 | **0.7914** | 0.7487 |

**Across the eight largest families the spread is narrow and one member is the outlier** — cancers run
**0.918–0.934**, and `anemia` sits at **0.8514** on 9 members and 622 positives. Full per-family table in
`family_auc_by_family`; the distribution is `nb3` figure 1.

> **⚠ This table is not comparable to the reference's family table, and the reason is instructive.**
> Family *structure* barely moved — 99.7% of diseases keep the same family, and the largest family is
> 75 members in both builds. What changed is **which families are in validation**, because
> the split reshuffled. The reference's report was headed by breast cancer at 20 members; this one is
> headed by a haematological family that was previously in train. **Family-level tables are a view of
> the validation sample, not a property of the graph** — read them that way.

**The coherence finding survives, on a different family.** `anemia` is now the weak large family at
0.8514, ~0.08 behind the cancers, exactly as epilepsy was in the reference (0.8269, ~0.11 behind).
Both are mechanistically **heterogeneous** groupings — anaemia spans haemolytic, nutritional,
aplastic and haemoglobinopathy causes — and both have far fewer positives than the comparably-sized
cancer families. So annotation depth and mechanistic coherence remain confounded and cannot be
separated from this table alone. The reference generation's evidence for *why* the functional
metapaths work still stands: epilepsy gained most of any large family (+0.0528, roughly double the
cancers'), because functional similarity transfers across heterogeneous subtypes where module
proximity does not.

**Anchored vs unanchored is *not* a leak meter.** Anchored diseases score consistently higher
(0.8390 vs 0.7508), but this is **confounded**: the external curation skews toward well-studied
diseases, so anchored diseases are also the best-annotated. Annotation depth dominates any residual
leakage signal; isolating leakage would need module-size-matched strata.

### 7.4 Second metric — drug-validated targets

*Source: `drug_target_benchmark`, `pool_selection_bias` · `nb3`, figure 2 (the orthogonality scatter).*

The label comes from **association** edges. That is not the same population as the proteins drugs
actually hit, so association AUC alone cannot say whether the ranking is therapeutically meaningful.

**Ground truth:** approved-indication edges ⋈ drug-target edges → **4,110 (disease, gene) pairs over
416 diseases and 778 genes**; 1,507 fall in the validation split across 112 diseases. Independent of
the label by construction — only 198 of 1,507 are also association positives — and **no model feature
traverses a drug node**, which is what makes the number interpretable.

**Headline: association AUC does not predict therapeutic relevance.** Across 130 diseases,
Pearson r = **0.002** between a disease's association AUC and its drug-target AUC (reference: 0.097
over 112). For the champion: mean drug-target AUC **0.6886** vs association 0.7868 *on those same 130
diseases*, **128 of 1,538** validated targets in the top 50 (8.3%), and **32 of 130 diseases below
0.5**. The two are decoupled, not merely offset — drug AUC *beats* association AUC on **50 of 130**.

**This is the most robustly reproduced finding in the document.** Rebuilt on a different graph, a
different split and a 19% smaller training set — and now re-measured on a new champion — the
correlation stayed near zero (0.002 vs 0.097 — if anything weaker; R² is 0.0000) and the hit rate
reproduced within half a point (8.3% vs 7.8%).

> **⚠ Drug-target AUC rests on the same inferred label** as §8.3 — two thirds of its positives come
> from drugs that are multi-target *and* multi-indication (§8.1). The *decoupling* finding is robust to
> this, because inflation adds noise and noise cannot manufacture a correlation of zero. But the
> absolute value of 0.6886 should be read as approximate.

**Why the gap is not a preprocessing artifact.** Two targeted interventions failed to move it:
sentinel imputation (best pooled AUC in the project, drug AUC *fell*) and dropping `prox_closest`
(neutral both ways). And a tractability *filter* cannot rescue it — the staged benchmark, rebuilt:

| Filter | candidate pool | validated kept | in top 50 | hit rate |
|---|--:|--:|--:|--:|
| none (stage 1 only) | 6,979 | 1,538 | 122 | 7.9% |
| antibody-accessible localization | 3,015 | 971 | 119 | 12.3% |
| **druggable protein family** | **1,829** | **1,019** | **168** | **16.5%** |
| either of the two | 3,791 | 1,244 | 124 | 10.0% |

Even the best filter — cutting the pool by 74%, i.e. handing the model something close to the answer
key's own universe — leaves **83.5% of validated targets outside the top 50** (reference: 19.5% hit
rate under the equivalent filter). **The ordering is the problem, not the candidate pool.**

**Why the features are nevertheless the right instrument.** Drug-validated targets with no
association evidence sit at **parity with association positives on the pathway metapath**
(within-disease percentile 0.674 vs 0.672; background 0.495) and at 90% on neighbour overlap, with
functional-annotation null rates indistinguishable from association positives (5.8% vs 6.2%;
background 20.7%). **So the signal exists in the graph; the objective is what doesn't ask for it.**

**Consequence for feature work — the asymmetry reproduced almost exactly.** Tractability is worth
adding but **not under this label** (`tractability_lift`, rebuilt):

| Attribute | Association lift | Drug-target lift |
|---|--:|--:|
| antibody-tractable | 1.40 | — |
| antibody-tractable *(as a separator)* | **0.98** — i.e. no signal | **1.39** |
| small-molecule tractable | 1.23 | **2.21** |
| **`Membrane receptor`** class | **0.78** — *depleted* | **3.16** — 3× enriched |
| `Ion channel` class | 1.60 | **11.9** |
| `Structural protein` class | 1.45 | **12.3** |
| `Secreted protein` class | 0.90 | 0.26 |

Under the current label the gain-maximising split is **"membrane receptor → lower score"**, which is
precisely backwards and is the mechanism behind the ligand-vs-receptor failure in §8.8. **Add
tractability together with a label change, not before.**

The reference measured 0.76× / 3× for membrane receptors and 13× / 15.6× for ion channels and
structural proteins; the rebuild gives 0.78× / 3.16× and 11.9× / 12.3×. Same direction, same order of
magnitude, same conclusion.

> **Standing rule:** every future feature or preprocessing change reports **both** metrics.
> "Association up, drug down" is a warning flag, not a win.

### 7.5 The decisive experiment — training on the drug label (a negative result)

*Source: **prose-only** — every artifact was deleted 2026-08-18. `docs/appendix/model_comparison.csv` retains the ablation side only.*

> **⚠ Renamed 2026-08-21.** This experiment was originally labelled `m7-drug-label`, which now
> collides with the champion **`m7-f14`** — a different model entirely. `DECISIONS.md` is append-only
> and still carries the old name; they are the same retired probe.

`drug-label-probe` tested the objective directly: **identical features, split, hyperparameters and
handling — only the label changes.** Train on a weak label (approved OR under investigation, 13,573
positives over 230 diseases), evaluate on the strict approved-only label. Strict is too rare to train
on — 196 positives over 18 diseases.

| Metric (112 reference validation diseases with a strict drug target) | `m3-f12` | `drug-label-probe` |
|---|--:|--:|
| Mean per-disease **drug-target** AUC | 0.6836 | **0.9324** |
| Validated targets in top 50 | 117 | **439** of 1,507 |
| Mean per-disease **association** AUC | **0.8228** | 0.6444 |

**The objectives are genuinely in tension** — +0.2488 drug, −0.1784 association. Which axis to optimise
is a product decision, not an optimisation problem.

**But the +0.2488 is not a win, and that is the finding.** A no-graph, no-disease-information baseline
— *"how many training diseases is this gene a drug target for"* — scores **0.9354** on the same
benchmark and **beats the trained model**, which wins on only 44 of 112 diseases. Holding out *genes* as
well as diseases leaves **57 positives across 19 diseases** at AUC 0.7266 — too thin to carry a
headline either. The benchmark is dominated by **gene identity**: the split is by disease, so no
evaluation *pair* was seen in training, but the ~800 recurring drugged **genes** were. Same structural
failure that got `gene_n_diseases` rejected (§4.2), reappearing on the *evaluation* side — and §6.1 has
since found it on the association axis too, at 0.8567.

**Recorded as a negative result and not deployed**, for two independent reasons: its advantage is a
gene-popularity artifact, and the drug label encodes *historical development choices* (ion channels 13×
enriched, structural proteins 15.6×), so a model trained on it is biased toward what industry has
already drugged — the opposite of target identification.

**Consequence for reporting.** Drug-target AUC is a **mandatory second metric and a warning flag**,
never a headline and never an optimisation target. Read the champion's 0.6886 as *"this model
deliberately declines a shortcut that scores 0.9354"* — and see §5.2.1, which shows ~0.04 of that gap
is a pool-construction artifact rather than a modelling one.

> **A benchmark that a lookup table wins is measuring the lookup, not the model. Before treating any
> metric as a target, check what the dumbest possible predictor scores on it.**

## 8. Results

### 8.1 Three axes, and two ground truths

*Source: `known_drug_truth`, `drug_disease_edges`, `drug_protein_edges` · `nb4`.*

A ranked list can be good or bad in three independent ways. Reporting one and inferring the others
produced a wrong conclusion once already (§8.6), so all three are measured separately.

| Axis | Question | Measure |
|---|---|---|
| **Ranking precision** | does the model put known truth first? | known targets in the top 50, over the disease's base rate |
| **Therapeutic agreement** | does the ranking agree with what drugs hit? | drug-target AUC (§7.4) |
| **Discovery** | does it surface targets nobody annotated? | drug-linked share of the top-50 **novel** candidates, over the novel base rate |

**Discovery is the deliverable's actual claim and was unmeasured until 2026-08-17.** It is the only
axis that speaks to "novel hypotheses", and it cannot be inferred from the other two.

> **⚠ Read this before any number below. The (disease, gene) pair is INFERRED, not asserted.**
> Open Targets states two things — *drug → disease* (indication or trial) and *drug → target*
> (mechanism of action). It does **not** state "gene G is the therapeutic target for disease X". Our
> ground truth manufactures that pair by joining through the drug, so a drug with 40 targets approved
> for 13 diseases contributes **520 pairs**, of which at most a handful are the real mechanism.
> Measured on our own data: **82.2% of the joined triples come from drugs with more than one target,
> 81.4% from drugs with more than one indication, and 66.3% from drugs that are multi on both.** Only
> **8.0%** of the ground truth survives a single-target restriction. §8.3 quantifies what this does to
> the headline numbers — it is not small.

**Two ground truths, and the choice changes the answer.** Both come from the drug layer, which no
model feature traverses:

| | Relation | Pairs | Reading |
|---|---|--:|---|
| **approved** | `indication` | 4,110 | a drug approved for this disease hits this gene |
| **investigational** | `drug_investigated_for` | 52,734 | in trials, not approved |

Approved is the strict bar. **Investigational is the fairer bar for target identification** — the
deliverable predicts targets worth pursuing, not drugs that already shipped, and restricting to
approvals penalises the model for surfacing target classes currently in development. Its cost is
that trial-stage labels include **failures**: a target trialled and abandoned still counts, so it
measures "someone judged this plausible", not "this works. **Report both columns, never only the
favourable one.**

### 8.2 Per-persona performance — all three axes

*Source: `persona_candidates`, `maturity_confound` · `nb4`.*

Seven personas, rebuilt 2026-08-17. `diabetes mellitus` was added after this analysis identified it
as the strongest approved-target discoverer in the entire validation set.

| Persona | pos | assoc AUC | ranking enrichment | drug AUC | approved: to find / found@50 / lift | investigational: to find / found@50 / lift |
|---|--:|--:|--:|--:|---|---|
| lung adenocarcinoma | 705 | **0.934** | 17.6× | — | — | 146 / **5** / **8.2×** |
| non-small cell lung carcinoma | 621 | **0.931** | **19.0×** | 0.676 | 33 / 0 / 0 | 379 / **11** / **6.8×** |
| lung cancer | 53 | 0.772 | **21.2×** | 0.827 | 4 / 0 / 0 | 258 / **12** / **5.8×** |
| **diabetes mellitus** | 968 | 0.679 | 9.2× | **0.874** | 48 / **8** / **41.6×** | 125 / 1 / 2.0× |
| obesity disorder | 762 | 0.709 | 9.3× | 0.833 | 30 / **5** / **41.2×** | 128 / 2 / 3.9× |
| type 2 diabetes mellitus | 1,081 | 0.634 | 4.3× | **0.256** | 62 / 0 / 0 | 202 / 1 / 1.2× |
| chronic kidney disease | 35 | 0.712 | 2.9× | 0.702 | 11 / 0 / 0 | 244 / 1 / **0.4×** |

**The panel splits cleanly into three groups.** The lung terms have the best *ranking* and real
discovery on the investigational bar. The metabolic pair (diabetes mellitus, obesity) are
outstanding on *approved* targets — 41× — and mediocre on investigational. Type 2 diabetes and CKD
are weak on every axis; CKD is **below chance** on discovery.

> **⚠ CORRECTED 2026-08-18. An earlier revision called the metabolic/oncology split "a real property,
> not a coverage artifact". It tested out much weaker than that** (`compute_maturity_confound`).
>
> The confound originally suspected — that each disease simply scores better on whichever label is
> denser for it — is **not** the explanation: Spearman(maturity, axis-preference) = **+0.110**, weak.
> Maturity is exonerated.
>
> What the check actually exposed is **sample size**. Restricting to diseases with ≥3 novel positives
> on *both* labels leaves 60, of which only **4 are metabolic** — and just **2 of those 4 show the
> pattern**:
>
> | metabolic disease | approved lift@50 | trial lift@50 | prefers |
> |---|--:|--:|---|
> | diabetes mellitus | **41.59** | 2.00 | approved |
> | obesity disorder | **41.21** | 3.86 | approved |
> | type 2 diabetes | **0.00** | 1.24 | trial |
> | diabetic neuropathy | 0.00 | 0.00 | neither |
>
> The group "median 20.61" is simply the midpoint between two ~41s and two 0s. **The defensible
> statement is "obesity disorder and diabetes mellitus score exceptionally on the approved label",
> not "metabolic diseases do".**
>
> The oncology direction is better supported but not uniform: **13 of 20 prefer the trial label, 7
> prefer approved**, median approved lift 0.00 (zero in 12 of 20 — partly the power problem of §8.3)
> against median trial lift 5.11. And the largest group, the 36 diseases that are neither, shows **no
> preference at all** (16 trial, 9 approved, 11 tied, median delta 0.00).
>
> **So: report both bars per disease, and do not attach a disease-class story to it.** A panel with one
> metabolic and one oncology disease is still the right choice — but because those two *individual*
> diseases demonstrate the two bars, not because the classes behave differently.

> **⚠ Type 2 diabetes is the flagship and the weakest disease in the panel** — 4.3× ranking
> enrichment, 0.256 drug AUC, and no discovery on either bar. Its **parent term, `diabetes mellitus`,
> is the single best approved-target discoverer of all 670 validation diseases.** If the metabolic
> story needs one disease, it should be the parent.

### 8.3 Discovery capability — the central claim, tested

*Source: `novel_discovery_eval` · `nb4`, figure 1 (lift vs K by ground truth).*

Drop the known association targets, re-rank what remains, and ask how many of the top-K **novel**
candidates are drug-linked. Lift is against the novel base rate, so >1 means the model ranks real,
previously-unannotated targets above chance.

| top-K novel | approved: lift / hits | investigational: lift / hits |
|--:|---|---|
| 10 | **16.9×** / 25 | 8.9× / 181 |
| 50 | 9.4× / 83 | 5.8× / 648 |
| 200 | 5.0× / **192** | 4.1× / **1,801** |
| *diseases measurable* | **122** | **298** |

**The shape is the finding, and a table hides it:** lift decays monotonically toward a ~4× floor while
absolute recovery keeps climbing. **`nb4` figure 1** plots both, all five K values, all three ground
truths.

**The label's construction needed testing before these numbers could be trusted, and it took two
passes to get right.** The sensitivity analysis below is the result; the two intermediate readings are
recorded in the decision log because both were wrong in instructive ways.

Seven label variants were tested. Three carry the argument; the full grid is in **`nb4`**.

| Ground truth | pairs | expected@10 | **lift@10** | lift@200 |
|---|--:|--:|--:|--:|
| join, approved *(original)* | 4,110 | 1.36 | **16.88** | 5.04 |
| join, single-target drugs *(the cautionary row)* | 634 | **0.20** | *0.00 — unmeasurable* | 2.30 |
| **`known_drug` ≥ 0.8 (curated, adopted)** | **3,253** | **1.61** | **21.32** | **5.23** |

**`expected@10` is the number of hits chance alone would produce** (diseases × 10 slots × base rate).
**Below ~1, an observed zero is uninformative** — it cannot separate "no enrichment" from "enrichment
too sparse to see". The single-target restrictions expect **0.20 and 0.11** hits, so their `0.00`
measures nothing. Rows in *italics* are underpowered at that K and must not be quoted.

**Across every adequately-powered variant, head-of-list lift is 6.9–21.3×, with the approved join at
16.9×.** The curated label gives the *highest* estimate, not the lowest. **Deep-list lift is the robust
number**: the three carried variants land at 4.1–5.2× on the champion.

> ⚠ The four underpowered variants in the full grid were measured on `m3-f12` and have **not** been
> recomputed on the champion, so the wider seven-variant range quoted before (2.3–4.8× deep-list) no
> longer describes one model. The three rows in the table above are the sourced ones (`nb4`).

**Why the curated label is now the standard for this measurement.** Open Targets' `known_drug` datatype
asserts the target–disease pair itself rather than leaving us to infer it. It is a strict superset of
our approved join — **all 4,110 join pairs appear in it** — so OT builds from the same
drug→target→indication chains and does *not* independently remove the multi-target inflation. What
does the work is its **score, which is a clean phase proxy**: 0% of pairs below 0.6 are approved,
31.9% in [0.6, 0.8), and **74.9% above 0.8**. Thresholding at 0.8 selects pairs with strong clinical
evidence, keeps 114 diseases and 1,173 novel positives — enough to estimate the head of the list,
which the single-target subset never was.

> **The construction limitation is real and unfixed.** The pair is still inferred through a drug, so a
> promiscuous drug still contributes several pairs. The score threshold mitigates it; nothing here
> eliminates it. Treat per-disease counts as approximate and audit individual candidates (MAPK3,
> §8.3) rather than leaning on the aggregate.

Investigational trades lift for coverage: 2.4× more diseases become measurable and 8× more hits — but
it is subject to the *same* construction flaw, and being 13× larger it is likely inflated at least as
much. It has not been re-tested under the restriction.

**Worked example — NSCLC, where the strict bar was misleading.** Under approved-only it finds 0 of
33 in the top-50 novel and looks like a discovery failure. Under investigational it finds **11 of
379 at 6.8×**. The top novel candidates, with their status:

| Novel rank | List rank | Gene | Status |
|--:|--:|---|---|
| 1 | 30 | STAT5B | — |
| 2 | 42 | STAT1 | — |
| **3** | **61** | **MAPK3** *(ERK1, terminal kinase of the KRAS→MEK→ERK cascade)* | **investigational** |
| 4 | 63 | PTPN6 | — |
| 6 | 74 | GSK3B | **investigational** |
| 9 | 83 | PIK3R2 | **investigational** |
| 10 | 86 | SMARCA2 | — |
| 15 | 105 | HDAC3 | **investigational** |

Four of the top fifteen novel candidates are trial-stage drug targets for NSCLC. **MAPK3 at list
rank #61 is the cleanest example of the deliverable working:** a real in-development target, ranked
highly, with nothing in the training label pointing at it. PTPN6 and SMARCA2 remain unvalidated
hypotheses on both bars.

### 8.4 Tractability axis — are the candidates actionable?

*Source: `tractability_axis` · `nb4`, figure 2 (naive vs degree-matched, both estimators).*

The third axis, and the only one whose label carries **no inflation at all**. `drug_protein` is a
direct assertion that a molecule engages a protein: gene-level, no join, 1,109 of 20,861 genes
(5.3%). It had never been used to evaluate the model.

**Two labels, because their confound profiles differ:**

| | definition | coverage | degree confound Q1→Q5 |
|---|---|--:|---|
| **demonstrated** | a `drug_protein` edge exists | 5.3% | **2.2% → 14.0%** — strong |
| **assessed** | an OT tractability bucket is set | 59.9% | 62.4% → 72.9% — mild |

**The control that makes this meaningful.** Demonstrated tractability rises ~6× across
interactome-degree quintiles and the model favours hubs (§7.2), so a naive enrichment could be pure
hub bias. Every lift is therefore reported against a **degree-matched null**: each top-K gene
contributes its *own quintile's* tractable rate to the expectation.

**Result — the model's head is genuinely enriched for actionable genes** (novel candidates only, 668
diseases). Reported under **both estimators**, because they disagree at the very head and an earlier
revision of this section mixed them:

The two endpoints carry the whole result; **`nb4` figure 2** plots all five K values for both
estimators, with the crossover marked.

| top-K novel | observed | dm expected | **pooled** naive → dm | **macro** naive → dm |
|--:|--:|--:|---|---|
| **10** | 2,285 | 693 | 3.54× → **3.29×** *(dm lower)* | 3.23× → **3.11×** *(dm lower)* |
| **200** | 31,475 | 13,003 | 2.08× → **2.42×** *(dm higher)* | 2.20× → **2.40×** *(dm higher)* |

*Pooled = Σobserved / Σexpected. Macro = mean of the per-disease lift, consistent with the macro
per-disease AUC used everywhere else in this document.*

**Degree-matching weakens the result at rank 10 under both estimators, and strengthens it further
down — but the crossover sits at a different K for each.** Pooled turns positive at rank 20, macro not
until rank 50. So the top ~10 candidates per disease *do* carry a hub component, and the deeper list is
enriched for tractable genes by **more** than connectivity explains. Below the crossover the model's
novel candidates skew slightly *lower*-degree than the pool, so the hub-corrected expectation drops
and the enrichment grows. **`nb4` asserts the sign of `dm − naive` at all five K values**, so a future
champion that moves either crossover trips the notebook instead of silently invalidating this
paragraph.

> **⚠ CORRECTED 2026-08-19.** An earlier revision claimed degree-matching strengthened the result
> *unconditionally*. That rested on putting a **pooled** dm lift (3.06×) next to a **macro** naive lift
> (2.97×) in the same row — two different estimators, which manufactured the crossover at rank 10.
> Computed consistently, rank 10 goes the other way in both. **The quotable range was not affected**;
> the unconditional claim was.

`assessed` tractability gives only 1.21–1.30× — expected, since 59.9% of all genes qualify, making it
a blunt instrument. **Report `demonstrated`; keep `assessed` only as a coverage-maximising secondary.**

> **This is the most robust positive claim in the document.** Unlike the discovery lift (§8.3), whose
> label is inflated and whose head-of-list estimate moved between 6.9× and 21.3× depending on
> construction, this one uses an uninflated gene-level assertion and *survives* its own confound
> control at every K — the degree-matched lift never drops below 2.4×. **~2.4–3.1× above a
> degree-matched null** (pooled; **2.4–2.9×** macro) is the number to quote — and the rank-10
> exception is worth volunteering, because being able
> to say where hub bias does and does not explain the ranking is itself the differentiator (see
> [DEMO_NARRATIVE.md](../demo/DEMO_NARRATIVE.md) Q2).

### 8.5 The ligand-vs-receptor failure is real but does NOT generalise

*Source: `tractability_axis`, `enriched_gene_localization`.*

The stated prediction for §8.4 was that the head would show a tractability **deficit** (≤1.0×),
because §8.8's case study says the model ranks secreted ligands above membrane receptors. **That was
refuted**, and the follow-up measurement scopes the original claim properly.

Secreted-protein share at top-50 minus its share of the candidate pool, across 668 diseases:

| | value |
|---|--:|
| mean excess | **−0.93 pp** |
| median excess | **−3.78 pp** |
| diseases where secreted is over-represented | **185 of 668** |

**On average the model *under*-represents secreted proteins at the head** — the opposite of what §8.8
implies in general.

**Where the over-representation does occur, it tracks the disease's own biology, not a model defect.**
The twelve worst cases are structural and inflammatory conditions — ulna fracture, tooth agenesis,
vaginal atresia, ectopia pupillae, prolapse (collagen and extracellular matrix) and rheumatoid
arthritis, Behçet disease, CINCA syndrome, fasciitis, IgA glomerulonephritis, rheumatic heart disease
(cytokines). For those diseases the real biology *is* extracellular, so ranking secreted proteins
highly is arguably correct. Their demonstrated-tractability lift is correspondingly low (0.0–2.8×),
which is a property of the disease rather than a ranking error: **their true targets are not
small-molecule tractable.**

**In the persona panel, including the disease the case study came from:**

| Persona | secreted excess | demonstrated lift@50 (degree-matched) |
|---|--:|--:|
| chronic kidney disease | +2.19 pp | 3.19× |
| type 2 diabetes | +2.13 pp | 1.96× |
| diabetes mellitus | +1.71 pp | 2.78× |
| **obesity disorder** | **−0.16 pp** | **3.53×** |
| lung adenocarcinoma | −3.91 pp | 1.92× |
| non-small cell lung carcinoma | −3.93 pp | 1.95× |
| lung cancer | **−6.40 pp** | **4.18×** |

**Obesity — the source of the GLP1R case study — has essentially no secreted excess and the second
best tractability enrichment in the panel.** So §8.8 describes a handful of genes in one pathway, not
obesity's ranking as a whole, and certainly not the model's general behaviour. The *mechanism* it
identifies (membrane-protein assay bias sparsifies receptor neighbourhoods) is real; its *scope* was
overstated by generalising from a single pathway.

### 8.6 The filter, validated on all three axes

*Source: `filter_three_axes`.*

The filter is **three clauses: novel → tractable → not-secreted.** A fourth, "exclude known
liabilities", was measured and rejected (§10.2) and is still computed so the damage stays visible.

**Which axes can legitimately score it — and one that cannot:**

| Axis | Verdict | Why |
|---|---|---|
| **Association** | **not applicable** | clause 1 removes every association positive by construction; scoring it would be a tautology |
| **Tractability** | **near-circular, appendix only** | clause 2 filters on a correlate of the outcome — quantified below |
| **Therapeutic** | **the legitimate test** | being chemically tractable is a different claim from being *this disease's* mechanism |

**How circular the tractability axis is, measured rather than asserted:**

| | |
|---|--:|
| P(demonstrated tractable \| assessed tractable) | **0.1253** |
| P(demonstrated tractable \| **not** assessed tractable) | **0.0007** |
| ratio | **177×** |

Clause 2 is effectively a **superset** of the outcome — almost no gene with a demonstrated drug-target
edge lacks an assessed tractability bucket. So the filter's 91% recall on that axis is *guaranteed by
construction*, not evidence of anything. **Do not quote the tractability row for this filter.**

**The therapeutic result, and it is consistent across all three ground truths:**

| Outcome | 3-clause lift | recall retained | recall with clause 4 |
|---|--:|--:|--:|
| **`known_drug ≥ 0.8` (curated standard)** | **1.60×** | **99.5%** | 72.6% |
| approved join | 1.61× | 100.0% | 73.0% |
| investigational | 1.61× | 99.6% | 66.4% |
| *tractability [circular]* | *1.47×* | *91.0%* | *62.8%* |

**Two things this settles.** First, the filter's conclusion is **robust to the label problem that
undermined the discovery numbers** — the curated label gives 1.60× / 99.5%, statistically identical to
the inflated join's 1.61% / 100%. That is expected: the filter is judged on recall across the whole
retained set, not on the head of a ranking, so it is far less sensitive to Cartesian inflation than
§8.3's lift. Second, **clause 4's damage reproduces on the curated label** (recall 99.5% → 72.6%), so
its rejection no longer rests on the inflated ground truth.

**Top-N on the curated label, plain → filtered** (expected-at-N in brackets, so a zero can be read
correctly):

| Persona | top 20 | top 50 | top 200 |
|---|---|---|---|
| **diabetes mellitus** | 1 → **5** [0.0] | 4 → **8** [0.1] | 11 → **15** [0.5] |
| non-small cell lung carcinoma | 0 → 0 [0.1] | 0 → 0 [0.1] | 0 → **2** [0.6] |
| obesity disorder | 0 → 0 [0.0] | 0 → **1** [0.0] | 1 → 1 [0.1] |
| chronic kidney disease | 0 → 0 [0.0] | 0 → 0 [0.1] | 0 → **1** [0.4] |
| type 2 diabetes | 0 → 0 [0.1] | 0 → 0 [0.2] | 0 → **1** [0.9] |
| lung cancer / lung adenocarcinoma | 0 → 0 | 0 → 0 | 0 → 0 |

**Diabetes mellitus reaching 5 curated approved targets in a filtered top-20 against an expectation of
0.0 is the single most demonstrable result in the deliverable.** Everywhere else the expectations are
below 1, so those zeros are uninformative rather than negative — the §8.3 lesson applied.

### 8.7 Persona selection — the criterion that was wrong, and the corrected panel

*Source: `persona_candidates`, `validation_auc_by_disease`, `drug_target_benchmark`, `novel_discovery_eval`.*

**The error, recorded because it changed a recommendation.** "Share of the top 50 already known" was
used as a novelty-balance criterion, treating a high share as "no novelty left". It is a *precision*
measure. Normalised by base rate, NSCLC's 96% is a **19× enrichment** — the best ranking in the panel
— and CKD's 2% is **2.9×**, the worst. The criterion rewarded the worst ranking, rejected the best,
and said nothing about novel candidates, which by construction sit *below* the known ones. It briefly
produced a recommendation to drop all three lung personas. **Corrected criteria: ranking enrichment
plus measured discovery on either bar.**

| Criterion | Diseases passing (of 670) |
|---|--:|
| ≥30 positives | 386 |
| association AUC ≥ 0.75 | 483 |
| ranking enrichment ≥ 5× | 557 |
| **discovery lift@50 ≥ 3× (either bar)** | **115** |
| **≥3 real targets surfaced in the top-50 novel** | **91** |
| **all five** | **62** |

**Four of the seven current personas pass all five** (both lung subtypes, lung cancer at 5;
diabetes mellitus and obesity at 4, each failing only the AUC threshold marginally). **Type 2
diabetes and CKD pass one.**

Strongest alternatives, by bar:

| On approved targets | On investigational targets |
|---|---|
| diabetes mellitus 41.6× · obesity 41.2× · psoriatic arthritis 40.7× · acute lymphoblastic leukemia 28.6× · **epilepsy 20.1× (15 found — largest absolute yield)** · medullary thyroid carcinoma 17.0× · breast cancer 16.6× | dedifferentiated chondrosarcoma 38.5× · acral lentiginous melanoma 34.4× · **meningioma 30.6×** · **autism 27.5× (13 found)** · uterine carcinosarcoma 28.1× · poorly differentiated thyroid carcinoma 22.3× |

Also outstanding on *both*: **myelofibrosis** (ranking 29.0×, drug AUC 0.96, approved 67.0×, JAK2 at
#6 and **JAK1 at #9 flagged novel** — JAK1 being half of ruxolitinib's mechanism), **acquired
polycythemia vera** (JAK2 at #3), **GIST** (drug AUC 0.99), **anaplastic large cell lymphoma** (drug
AUC 1.00).

**Recommended changes to the panel:**

1. **Keep NSCLC**, drop `lung adenocarcinoma` and `lung cancer` — all three pass, but they share
   ~63% of their candidate lists (§3.4) and NSCLC has the most to find (379) with the best ranking.
2. **Keep `diabetes mellitus`; retire `type 2 diabetes`** as a headline persona. The parent is 10×
   better on every axis. Keep T2D only as the deliberate "here is where the method struggles" case.
3. **Drop CKD** — below chance on discovery, 2.9× ranking. Its SLC-transporter list is biologically
   attractive and evidentially unsupported.
4. **Add one immunology/neurology disease** — epilepsy (largest absolute yield, strong on both bars)
   or psoriatic arthritis (40.7× approved). Both break an all-oncology-plus-metabolic panel.
5. **Consider myelofibrosis** as the precision-oncology showcase, for the JAK1/JAK2 result.

### 8.8 Case study — GLP1R, and the limits of an interactome-based model

*Source: notebook-only — `scored_m3`, `graph_edges`.*

GLP1R is the semaglutide target and a known association target for obesity disorder. It ranks
**699 of 13,126** (5.33 percentile, score 0.889) and is predicted negative at the F1 threshold.

**Why the rank is low — neighbour overlap, not degree:**

| Gene | interaction partners | shared with module | `dwpc_GGD` | is_target |
|---|--:|--:|--:|--:|
| GCG (ligand) | 37 | **13** | 0.0205 | 0 |
| IAPP (ligand) | **16** | **7** | 0.0180 | 0 |
| GLP1R (receptor) | **28** | **3** | 0.0039 | **1** |

The receptor has *more* partners than the amylin ligand yet scores far lower. The discriminator is
**overlap with the module**. Mechanistically this is **membrane-protein assay bias**: transmembrane
receptors resist the assays that built the interactome, so their mapped neighbourhoods are sparse.
**The model penalises the receptor for an assay artifact, not biology** — a live instance of the
incomplete-interactome caveat (§2).

**The failure, correctly scoped.** In the current build the incretin axis reads IAPP #5, GHSR #8,
MCHR1 #23, GCG #36, MC4R #47, GIP #99 · GIPR #365, LEPR #401, **GLP1R #699**, GCGR #976,
CALCR #1,113. For *this pathway* the model finds the right mechanism and not the right druggable node.

> **⚠ Do not generalise this.** §8.5 measured it across 668 diseases: secreted proteins are on
> average **under**-represented at the head (median −3.78 pp), obesity itself shows **no** secreted
> excess (−0.16 pp), and obesity's degree-matched tractability enrichment is **3.53×** — second best
> in the panel. The mechanism below is real; the earlier claim that it describes the model's general
> behaviour was an over-generalisation from one pathway.

**Movement across the rebuild, and how to read it.** Same model generation, same 13,126 pool:

| Gene | reference | rebuilt |
|---|--:|--:|
| IAPP (ligand) | 9 | **5** |
| GHSR | 21 | **8** |
| MC4R | 39 | 47 |
| MCHR1 | 50 | **23** |
| GCG (ligand) | 175 | **36** |
| **GLP1R** | **386** | **699** |
| GIPR | 517 | **365** |

GLP1R is the only one of seven that moved materially the wrong way; five improved. **Not a class-wide
receptor regression** — GIPR and MCHR1 would show it too. GLP1R's score rests on three shared
neighbours, so it is exactly the kind of thinly-supported prediction that swings when the training
population changes (58.8% of diseases moved split in the 2026-08-17 rebuild). One consequence for the demo: the
ligand-vs-receptor gap **widened**, so the contrast in §8.7 is more striking than when it was written.

**The evidence the model is not allowed to use.** The drug metapath for GLP1R traces to a single
compound. It is rejected as circular (§4.2) — defensible, but it means the most decisive evidence is
computed and discarded. **Use it as a post-hoc annotation, not a feature.**

**The honest lever is presentation, not the model.** In the `membrane / cell-surface` column GLP1R
sits behind GHSR (#8), MCHR1 (#23), MC4R (#47) and GIPR (#365) — all defensible obesity receptors.
That reads better than a single gene's absolute rank without pretending 699 is good.

### 8.9 Druggability and safety annotation on the ranked list

*Source: `enriched_gene_druggability`, `enriched_gene_safety`, `safety_lift`, `tractability_lift`.*

Built to make the §8.8 failure *visible* without touching the model. Per-gene attribute tables joined
on `gene_index` — **no nodes, no edges**, so the graph and its indices are untouched. This is the
pattern for every future annotation layer: an attribute table costs one join, an edge forces a graph
rebuild, a re-index and full feature recomputation.

| Source | Signal | Coverage | Verdict |
|---|---|--:|---|
| Subcellular location (curated + atlas) | membrane / secreted | **90%** | primary workhorse |
| Target class (chemical-biology family) | `Membrane receptor`, `Enzyme`, `Ion channel`… | 28% | authoritative but sparse; **human-readable** |
| Tractability buckets | small-molecule / antibody, has-approved-drug | 29% | modality routing |
| Cellular-component annotation *(in graph)* | membrane / secreted | 36% | gap-fill; covers 343 genes the primary source misses |
| **Curated safety liabilities** | adverse events, dose dependence | **4.5% flagged** | **display only** (§10.2) |
| **Genetic constraint** (LOEUF) | loss-of-function intolerance | 85% | **informational; not a filter** |

The two independent localization sources agree 88.2% on membrane and 95.6% on secreted; where they
disagree the curated source is generally right.

Filters that work on the output:

| Goal | Filter |
|---|---|
| core discovery | not a known target AND not secreted AND (small-molecule OR antibody tractable) |
| small-molecule programme | class in (Enzyme, Ion channel, Transporter, cell-surface) AND small-molecule tractable |
| antibody / biologic | class in (cell-surface, membrane + secreted) AND antibody tractable |
| **repurposing** | not a known target AND has an approved drug |

The repurposing filter returns **32 candidates** at top-50 across the panel, including ERBB3, ERBB4,
FGFR1/2/4, DDR2, ADRB2, GRIN2A and a cholinergic cluster.

> **This annotates, it does not re-rank.** The model never sees these columns, so secreted ligands
> still outrank receptors *globally*; the fix is class-grouped presentation (§10.2). And
> has-approved-drug is **gene-level across all indications** — "chemical matter exists", not "this
> drug works in this disease".
>
> **⚠ Two columns must not become filter controls.** Genetic constraint runs *with* druggability, and
> liabilities mark drug precedent rather than risk (§10.2). Both are present in the deliverable —
> the constraint columns unintentionally, via automatic column selection — and both would strip the
> best candidates if filtered on. The liability `event` field also mixes real adverse events with
> bare mechanism descriptors (`regulation of catalytic activity`) and risk-factor biology (lung
> cancer's nicotinic candidates are flagged `nicotine dependence`, the disease's own risk mechanism).

### 8.10 The breast panel — built to be falsified by a clinician

*Source: `breast_panel_metrics`, `breast_panel_overlap`, `breast_shortlist` · `nb4`.*

Added 2026-08-19 (`compute_breast_panel`, `compute_breast_shortlist`). **The purpose is not another
metric.** Two of the arms cannot be scored against our own labels at all, and a breast surgeon can
falsify a candidate list in twenty minutes — faster and harder than anything above.

All twelve breast terms already sat in the **validation** split, all in disease family 49721, so there
is no leakage to control for. Six were added to the persona filter, taking `target_candidates_2` from
76,465 rows over 7 diseases to **129,253 over 13**.

**Per-arm trust.** Significance is an exact Poisson upper tail on hits@50, not a rule of thumb about
expected counts — an earlier draft labelled anything with expectation < 1 "unpowered", which is wrong
in the direction that matters: HER2+ sees 46 hits against 2.44 expected, overwhelming regardless of how
small the expectation is. AUC intervals are Hanley–McNeil.

| Arm | pool | known | AUC (95% CI) | hits@50 vs exp | verdict |
|---|--:|--:|---|---|---|
| HER2 positive breast carcinoma | 12,272 | 599 | **0.93 (0.92–0.95)** | 46 vs 2.44 | significant |
| breast carcinoma *(umbrella)* | 13,290 | 864 | 0.86 (0.84–0.87) | 49 vs 3.25 | significant |
| luminal A breast carcinoma | 8,157 | 101 | 0.85 (0.81–0.90) | 12 vs 0.62 | significant |
| triple-negative breast carcinoma | 2,563 | **8** | 0.93 (0.81–**1.05**) | 2 vs 0.16 | **significant but fragile** |
| breast cancer *(parent term)* | 9,067 | 138 | **0.69** (0.64–0.74) | 20 vs 0.76 | significant |

Two things to read off it. **The parent term is the worst in the panel** — beaten by its own children,
which inverts the §3.3 expectation that coarser terms are safer. And **triple-negative's interval
crosses 1.0**, which is the approximation failing at 8 positives: the point estimate carries no
information, and saying so is the reason a clinician is being asked.

**Specificity is not the same as separation, and only one arm has both.** HER2+ separates cleanly from
triple-negative (2/50) yet overlaps the umbrella term `female breast carcinoma` by **38/50 (76%)** — an
excellent breast-cancer list wearing a subtype label. Triple-negative overlaps every umbrella term by
≤ 8/50. **It is the only genuinely subtype-specific list in the panel, and the only one we cannot
score.**

**HER2+ passes the clinical sanity check outright.** ERBB2 itself at rank 13, TP53 at 2, PIK3CA 7,
AKT1 10, EGFR 17, ERBB3 26, CDK4/6 at 53/118 — the PI3K/AKT axis that actually drives trastuzumab
resistance sits in the top ten. The novel block is RAS/MAPK downstream of HER2.

**Triple-negative has four defects, recorded because finding them ourselves is the point:**

1. **ESR1 at rank 14.** Triple-negative is ER-negative *by definition*. Not a judgement call — it is
   direct evidence of breast-generic signal leaking into a subtype defined by a receptor's *absence*.
2. **PARP1 at rank 331 of 2,563**, while its substrate pathway occupies the top 20. PARP inhibition is
   the defining targeted therapy in this disease. Internally inconsistent.
3. **BRCA1 at rank 252 — and it is a *known* association — while BRCA2 is at rank 5.** Two paralogues
   treated oppositely with no biological justification.
4. **`TACSTD2` (TROP2) is not in the candidate pool at all** — and it carries a curated `known_drug`
   score of **0.90** for this disease, i.e. it is one of only two pairs the therapeutic label asserts
   for triple-negative, and the model cannot score it. Sacituzumab govitecan is approved here.
   **Corrected 2026-08-19:** I originally listed `PDCD1`/`CD274` alongside it as structurally
   unreachable. They are not — they are reachable for **62%** and **53%** of all diseases respectively,
   so their absence is specific to this disease's known-gene set, and their curated score for
   triple-negative sits below the 0.8 threshold. `TACSTD2` is the genuine case: reachable for just
   **1.04%** of diseases. See §5.2.1 and §10.4 for the corrected scope of this problem.

Also: **TP53 ranks 2 for triple-negative but is labelled *novel*, while being a *known* target for
HER2+ and for the umbrella term.** "Novel" here means *not annotated for this particular subtype*, not
unknown to science. Unexplained, it makes the model look naive.

**The deliverable is a form, not a report.** `breast_shortlist` is 118 rows over 4 arms; each arm leads
with its top known targets as a calibration anchor, then 20 novel candidates, then four blank columns
for the clinician's verdict. **If the surgeon rejects an arm's known block, the novel block is not worth
their time** — and that disagreement is the more valuable finding. Full briefing in
[BREAST_SURGEON_BRIEFING.md](../demo/BREAST_SURGEON_BRIEFING.md).

## 9. Flow zones

**Fourteen zones, 183 flow items**, restructured on 2026-08-18 so the zone list reads in the order
the presentation runs. **The numeric prefixes are load-bearing** — DSS sorts zones alphabetically, so
without them the flow opened with `Annotations` and put `Results` before `Features`.

| Zone | Items | Demo Q | Contents |
|---|--:|:--|---|
| `00 Imported from DEMO_KG_LS (synced)` | 35 | — | the cross-project interface: 12 foreign references + the Kuzu folder (PROJECT_CONTEXT §4.3), the 12 Sync recipes, and the 10 local copies they write. **Downstream recipes read the local copies, never the foreign refs** |
| `10 Features - graph traversal (Cypher)` | 20 | *not shown* | 10 graph-query recipes (incl. the centrality plugin) → 10 feature datasets |
| `11 Features - matrix (Python)` | 11 | *not shown* | functional metapaths, proximity, random walk, degree-corrected overlap, provenance depth |
| `12 Features - assembly` | 4 | *not shown* | pair spine → 18-input join → feature table (21,308,578 rows) |
| `20 Annotations & split key` | 12 | feeds **Q1** + punch line | family id from the anchor rollup; gene localization → druggability; gene safety |
| `30 Modeling table & split` | 8 | backs **Q5** | join family id → candidate-pool restriction → split by family key |
| `31 Model training` | 6 | *ladder not shown* | the three ladder models and their saved artifacts |
| `40 Validation - ranking quality` | 18 | **Q5** | 3 scoring recipes, per-disease and per-split-key AUC, the ablation ladder |
| `41 Validation - the three axes` | 22 | **Q2, Q3, Q4** + punch line | tractability axis + lift, drug-target benchmark (plain + staged), curated `known_drug` truth, novel-discovery eval, three-axis filter, maturity confound, safety lift, persona candidates, reachability |
| `42 Validation - leakage & granularity` | 9 | **Q5, Q6** | split audit, disease-hierarchy annotation, lung granularity check, **breast subtype separability** (§8.10) |
| `43 Validation - disease families` | 14 | **Q5** | per-family AUC and top genes per family |
| `50 Results - target candidates` | 14 | **Q1** | persona filter → SHAP scoring → `rank_per_disease` (Window) → 2 decoration joins → `target_candidates_2`, plus the **clinician review form** `breast_shortlist` |
| `60 Dashboard (serving)` | 10 | serves **Q1** | the flattened serving tables — `dashboard_candidates`, `dashboard_persona_trust`, `drug_evidence_pairs`, disease pool sizes |
| `Default` | 0 | — | empty; DSS will not let it be deleted |

**Every zone carries its rationale as a Flow description in DSS**, and since 2026-08-19 each one leads
with **the demo question it answers** — the Q1–Q6 numbering from
[DEMO_NARRATIVE.md](../demo/DEMO_NARRATIVE.md) §2. Zones that are deliberately *not* demo material say so
outright (`10`–`12`, and the ablation ladder in `31`). A reviewer opening the flow gets the argument,
and a presenter gets the running order, without either of these documents.

**Recipes are named for actions, not outputs.** An earlier pass renamed them after finding recipes
called things like `compute_graph_features_sampled_2` (now `filter_has_path_evidence`).

**Heavy graph math lives in code, not plugin recipes** — the metapaths, proximity, random walk and
degree-corrected overlap. The query-recipe path repeatedly failed at this scale (§4.3).

**Everything in zones 10–60 was rebuilt on 2026-08-17** against the shared graph, so every reported
number comes from one generation. One exception, flagged where it appears: the hub-bias meter (§7.2)
has no recipe and is still on the retired generation.

### 9.1 Why four validation zones — and which objection each one kills

*Source: no artifact — cross-references only.*

The previous layout had one `Results - model performance` zone and one `Diagnostics (optimisation)`
zone that had swollen to **40 items** — it was where everything went that was not scoring, and by the
end it held the three-axis overhaul, the leakage audits, the persona selection and a dead experiment
in one undifferentiated pile. **The flow no longer showed which findings the deliverable rests on.**

The split now follows the **demo objection ladder** ([DEMO_NARRATIVE.md](../demo/DEMO_NARRATIVE.md) §2) rather
than our own metric taxonomy, because that is the order a sceptical scientist actually asks in:

| Demo Q | What they say | Zone | The evidence |
|:--|---|:--|---|
| **Q1** | *"Show me the list."* | `50`, `60` | 129,253 ranked rows; obesity → 65 candidates on the scientist's own thresholds |
| **Q2** | *"These are just the famous genes."* | `41` | degree-matched tractability **2.4–2.9×**; strengthens below rank 20, weakens at rank 10 (§8.4) |
| **Q3** | *"You already knew all of these."* | `41` | novel-discovery **16.9×** at top-10 approved; **MAPK3 novel #4 / list #66** for NSCLC (§8.3) |
| **Q4** | *"Your ground truth is garbage."* | `41` | 82% inflation measured, then re-run on curated `known_drug` — result got *stronger* (§8.1, §8.6) |
| **Q5** | *"Would this work on a disease you had not tuned?"* | `40`, `42`, `43`, and `30` | macro AUC **0.8230**/670 diseases; per-family **0.8009**/505; zero straddling split keys |
| **Q6** | *"What can't it do?"* | `42`, `41` | subtype irresolvable (§3.4); ligand-vs-receptor scope (§8.5); no safety axis, and we say so |
| **punch** | — | `41`, `20` | the three refuted gates: druggability inverted, LoF backwards, liability filter deletes ADRB2 (§10.2) |

**Zone 41 is the one to open in a technical review** — it alone answers Q2, Q3, Q4 and carries the
punch line, including both corrections. Zones `50`/`60` are the demo surface; `40`–`43` are the
evidence for it. The old `Diagnostics (optimisation)` name was itself misleading: none of that work
was optimisation, it was the evidence base — which is precisely why it must not be pruned to whatever
a not-yet-designed dashboard happens to read (§10.3).

### 9.2 The candidate-decoration tail, collapsed 5 recipes → 2

*Source: `target_candidates_2` — verified as a pure refactor at the time; see the note below.*

The persona chain ends by attaching names and annotations. That had grown into alternating joins and
prepares — gene-name join, rename/drop, disease-name join, druggability join, rename/drop/reorder —
5 recipes and 4 intermediates. **All of it is left-joining a lookup then selecting, renaming and
ordering columns, which a join recipe does by itself.**

| | Recipe | Inputs | Does |
|---|---|--:|---|
| 1 | `decorate_target_candidates` | 4 | ⋈ node names on `gene_index`, ⋈ druggability, ⋈ safety → `top_annotated` |
| 2 | `join_disease_name` | 2 | ⋈ node names on `disease_index`, plus final selection, renames and order |

Zone 18 items → **12**. **Verified as a pure refactor**: identical row count and key set, zero of the
59 columns differing in value; only `disease_name`'s position moved, because DSS emits each input's
columns as a block.

**Three mechanics decide whether this is possible** (all in DSS_CHEATSHEET, none discoverable from the
payload): a join renames via **`computedColumns`**, not via `rename` in `selectedColumns` (which
round-trips then is ignored); dropping columns needs the **per-input `MANUAL`** list, since top-level
`selectedColumns` sets order only; and **the same lookup table cannot be joined twice** — accepted by
the API, rejected at validation. The last is the only reason this is two recipes rather than one.

## 10. What is settled, and what is open

### 10.1 The rebuild is verified

*Source: `reference_baseline.json`.*

Rebuilt end to end on the shared graph 2026-08-17 against a **±0.02** tolerance set in advance.
**Every one of six metrics landed inside ±0.01** — largest movement −0.0084 (per-family), headline
macro per-disease AUC **0.8228 → 0.8197**. The full grid is in `reference_baseline.json`.

**The candidate pool is bit-identical** (6,754,128 both sides), so only the split *allocation* changed:
train shrank 18.8% and the champion held its accuracy. Two movement sources were separated in advance —
graph drift is 0.03% of edges, all functional-annotation; the split reshuffle moved 58.8% of diseases
and was estimated at +0.0049. The observed −0.0031 is *smaller* than that estimate, so the two partly
cancel. **Metric cross-validation holds:** visual chain and code recipe both give 0.8197, max
difference 1.9×10⁻⁴.

**The acceptance criterion is met.** This section is retained as the audit trail; nothing downstream
depends on the reference generation any more.

### 10.2 Two design decisions, settled on measurement

*Source: `tractability_lift`, `safety_lift`, `filter_three_axes`.*

Both were answered by measuring rather than training: three recipes instead of three model runs.

**Druggability / target class as a model input — rejected.** Not merely "no expected gain" —
**actively harmful under this label.** Against `is_target`, `Membrane receptor` has an association
lift of **0.78 (depleted)** and a drug-target lift of **3.16×**; antibody-tractability's 0.98
association lift is *no signal at all*. A loss-minimising tree therefore learns **"membrane receptor →
lower score"**, reinforcing the §8.6 failure. The label route out is closed on evidence (§7.5).

| Attribute | Association lift | Drug-target lift |
|---|--:|--:|
| antibody-tractable | 0.98 — no signal | 1.39× |
| small-molecule tractable | 1.23 | 2.21× |
| **`Membrane receptor`** | **0.78 — depleted** | **3.16×** |
| `Ion channel` | 1.60 | 11.9× |
| `Structural protein` | 1.45 | 12.3× |
| `Secreted protein` | 0.90 | 0.26× |

**Shipped instead: top-N within druggability class.** Obesity's `membrane / cell-surface` column leads
with GHSR (#8), ADRB2 (#17), MCHR1 (#23) — two clinically-pursued anti-obesity targets — while the
secreted ligands still lead globally. **A grouping change recovered most of what a model change was
meant to buy, at no risk to the model.**

**Safety / toxicity as a filter — the gate refused it, and the stated prediction was refuted.**
Predicted: drug targets would be *depleted* for loss-of-function intolerance. Measured over 130
diseases, the opposite, monotonically:

| LOEUF band (most → least constrained) | drug lift | assoc lift |
|---|--:|--:|
| < 0.35 *(intolerant)* | **1.37×** | 2.07× |
| 0.35 – 0.7 | 1.33× | 1.36× |
| 0.7 – 1.0 | 0.94× | 0.87× |
| 1.0 – 1.5 | 0.80× | 0.60× |
| > 1.5 *(tolerant)* | **0.62×** | 0.40× |

Constraint measures that a gene is functionally consequential — a *prerequisite* for being worth
drugging — and a drug is not a germline knockout. Separately, **`has_safety_liability` is 4.62×
enriched** for drug-validated status, because liabilities are discovered *by* drugging a target.

**Neither free signal is a safety filter**; used as one they strip the shortlist of its best
candidates (§8.5). What shipped: liabilities as **displayed annotation**; constraint columns
**informational only**; and **a real safety axis still requires a direct measurement** —
essentiality, tissue-expression breadth — which needs a new source. The gate's result is the
justification for that ingest cost.

> **⚠ Absence of a liability is not evidence of safety.** Open Targets emits the field only for the
> 943 targets that have one. There is no "assessed and clean" state, so a blank means nobody looked —
> anything filtering on blank filters on literature attention, the study bias the feature set exists
> to control.

### 10.3 Remaining

*Source: forward-looking — no artifact.*

- **Report drug-target AUC stratified by route support** (§5.2.1) — 0.6886 all positives / **0.7471**
  route-supported. Removes the 91.8× outcome-selection bias from the *metric* without touching the
  pool, so no disease is lost and nothing is re-fit. **Supersedes the earlier "drop `dwpc_GCD` from the
  filter" recommendation, which bought the same number at the cost of 22 diseases' entire therapeutic
  evaluability.**
- **Execute the scoped prune — 16 items, snapshots already taken.** The ablation chain
  (`scored_m1`/`scored_m2`, 7.9M rows serving a 2,010-row table), `validation_auc_by_disease_2`,
  `drug_target_benchmark_staged`, `target_reachability`, `disease_hierarchy_annotation` and
  `maturity_confound`, with their recipes. All six results are frozen in
  [`docs/appendix/`](../appendix/) with a manifest; the saved models stay. **Plus a refactor, not a
  prune: zone `43` collapses 14 items → 2** (one Python recipe `scored_m3` → `family_auc_by_family`),
  keeping Q5's 505-family answer live and dropping a ~4M-row visual chain.
- **Re-derive the Cypher literals in §8.7** — *gene* indices for the demo queries, regenerable from
  the rebuilt ranking but not yet done. Presentation-layer only.
- **§7.5's numbers are documentation-only.** The `drug-label-probe` chain was deleted 2026-08-18 —
  model, 3 splits, 6 evaluation datasets — so **0.9324 / 0.6444, 439-of-1,507 hits@50, the 0.9354
  gene-popularity baseline, the 57-positive gene-holdout and the 196-positive strict test set now
  exist nowhere but this document.** The five recipes are recoverable from git
  (`97de713:dss_recipes/`). Re-run only if someone disputes the negative result.
- **The hub-bias meter (§7.2) has no recipe** — computed ad hoc, still on the retired generation.
- **A direct safety measurement** — now the top feature priority, because §10.2 established the free
  proxies cannot do the job.
- **The dashboard.** Data layer is ready: 129,253 ranked rows with tractability, class and safety
  annotation. What is missing is the UI with rank / class / safety controls.
- **Act on the persona recommendations in §8.7** — retire type 2 diabetes and CKD as headline
  personas, keep one lung term, add an immunology or neurology disease.

### 10.4 Still open

*Source: forward-looking — no artifact.*

- ~~Druggability as a model input~~ — **settled, rejected** (§10.2); shipped as class-grouped
  presentation.
- ~~Safety as a filter~~ — **settled, rejected** (§10.2); liability annotation shipped display-only.
- **Feature ideas not yet built** *(folded in from the old §4.3)*: `is_plasma_membrane` /
  `is_secreted` — cheap and verified feasible, but superseded in practice by the class-grouped
  presentation (§10.2); **gene-family / paralog leave-one-out** — a paralog being a known target is
  evidence nothing else captures, currently **blocked** because the gene vocabulary carries no family
  column, and it *must* be leave-one-out or it becomes another label-derived shortcut;
  `disease_phenotype_context`, and the cellular-component and phenotype metapaths — all low priority,
  the first two because co-localization terms like "nucleus" span thousands of genes.
- **Embedding features** — the one family that can score *pathless* pairs, reaching past the
  candidate-pool boundary (§5.2). ⚠ **I promoted this to "top modelling priority" on 2026-08-19 on the
  strength of one disease, and measurement does not support that.** Across all 207 evaluable diseases
  the pool contains **98.5%** of curated target–disease pairs, so the reachability ceiling costs
  **1.5%**, not a category of biology. Three sub-claims were also wrong:
  **(a)** it is not a sparse-disease effect — Spearman(pool size, coverage) = **+0.081**;
  **(b)** borrowing the family pool would rescue only **2 of 34** misses;
  **(c)** `CD274` and `PDCD1` are reachable for **53%** and **62%** of all diseases, so their absence is
  specific to triple-negative, not structural. Only `TACSTD2` is a genuinely narrow gene
  (**1.04%** of diseases), and **18.8% of all genes (3,919) are reachable for no disease at all** — that
  is the real scope, and it is a fair argument for embeddings, just a much smaller one than I claimed.
  **The pool problem worth fixing first is §5.2.1, not this.**
  **§5.2.2 supplies a much stronger argument for embeddings than the ceiling ever did.** The
  reachability ceiling is only 1.5%, so it was never a big number. But the counterfactual shows the
  *whole topology feature family is undefined beyond two hops* — admit those pairs and 4 of 13 inputs
  are null, they score at 52% of the pool mean, and `TACSTD2` lands at #845 of 2,564. **Embeddings are
  the one family that produces a real value for a pathless pair**, so they are not a way to widen the
  gate — they are the only way to make anything past the gate scoreable.
  ⚠ **And no route-set change rescues the flagship case.** Tested all five metapaths for
  (triple-negative, `TACSTD2`): GGD, GPGD, GCD, **GBGD and GFGD all fail**, including the 12.1M-row
  GBGD where TACSTD2 has 997 pairs and triple-negative has 7,456 — the intersection is still empty. The
  cause is two compounding sparsities in the **graph**, not the filter: TACSTD2 carries **84 edges total
  at PPI degree 10 (25.7th percentile, median 26)**, mostly annotation rather than interaction edges,
  and it **shares no edge with any of triple-negative's 8 known genes** (BRCA1, MDM4, TCF7L2, CHEK2,
  PALB2, TERT, MRE11, CDKN2A). So the fixes are upstream in `DEMO_KG_LS` — a richer interaction source,
  or drug–target edges promoted to first-class graph edges — or embeddings, which are the only
  model-side option because they need no path at all.
- **Degree-matched negative sampling** — currently class weights only. A cheaper diagnostic first:
  evaluate the existing model on a degree-matched validation subset.
- **Permutation baseline** — a degree-preserving permuted-graph null would quantify signal beyond
  degree. Controls the degree confound, *not* the coverage leak.
- **The mirrored recipe code in this repo is a snapshot, not a mirror.** Pull live code before
  reasoning about behaviour.

## Appendix — decision log

**Moved to [DECISIONS.md](../../DECISIONS.md)** on 2026-08-19 — 82 lines and 312 numbers of
append-only reference, including every correction and reversal. It is the record of *why*;
this document is the record of *what*.

## References

> Per-reference summaries, the feature→reference map, and provenance caveats are in
> **[RESEARCH_NOTE.md](../reference/RESEARCH_NOTE.md)** (unvalidated corpus — verify before client-facing use).

- Locus-to-Gene (the pattern this reproduces) — Mountjoy et al., *Nat Genet* 2021
- Target prioritisation reference implementation — https://platform-docs.opentargets.org/web-interface/target-prioritisation
- Network proximity — Guney, Menche, Vidal, Barabási, *Nat Commun* 2016
- Disease modules / incomplete interactome — Menche et al., *Science* 2015
- Degree-weighted path counts — Himmelstein et al., *eLife* 2017
- Path-explanation interpretability study — Huang et al., *Nat Med* 2024
- Genetic support and clinical success — Minikel et al., *Nature* 2024
