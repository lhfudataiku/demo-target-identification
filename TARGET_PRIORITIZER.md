# Explainable Target Prioritizer — `DEMO_TARGET_IDENTIFICATION`

> Technical documentation for the **modelling, validation and result-visualisation** project: what
> the data exploration found, why these features and this model, and how well it actually works.
>
> Companion documents: **[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)** (why / who / how the projects
> fit) · **[GRAPH_BUILDING.md](GRAPH_BUILDING.md)** (the graph this consumes) ·
> **[RESEARCH_NOTE.md](RESEARCH_NOTE.md)** (per-reference evidence base) ·
> **[DSS_CHEATSHEET.md](DSS_CHEATSHEET.md)** (platform behaviours).
>
> **Status: built and validated on the rebuilt graph (2026-08-17).** Champion **`m3-f12`** (12
> features): macro per-disease AUC **0.8197** over 670 diseases, per-split-key 0.8007, pooled
> 0.8915, per-family 0.7976, drug-target 0.6911.
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

## 1. What it delivers

For a given disease, a ranked shortlist of candidate gene/protein targets, each carrying **two
complementary explanations**: a SHAP attribution (*which evidence drove this*) and a **graph path**
to the disease module rendered on the graph webapp (*show me the mechanism*).

`target_candidates_2` — **every scored candidate per persona disease, ranked** (129,253 rows across
13 personas), so the scientist filters rather than receiving a pre-cut list (§8.10):

| disease_name | gene_name | score | druggability_class | top_shap_drivers | rank | is_target |
|---|---|--:|---|---|--:|--:|
| breast cancer | BLM | 0.986 | Enzyme | dwpc_GPGD, ppi_adamic_adar | 5 | 0 |

Top-ranked genes **not currently linked** to the disease are the novel hypotheses.

**In scope:** network-topology and functional-annotation features, on the graph we already have.
**Deferred:** safety/toxicity features; knowledge-graph-embedding features; tractability as a
*model* input (§4.3 explains why it belongs in the ranking layer instead).

## 2. Scientific basis

> Per-reference summaries and the feature→reference map are in
> [RESEARCH_NOTE.md](RESEARCH_NOTE.md).

This reproduces an industry-standard pattern rather than inventing one — deliberately. The
differentiator is reproducibility, lineage and explainability, not the algorithm.

- **Supervised target prioritisation is the Open Targets standard.** Their Locus-to-Gene model is
  **gradient-boosted trees + SHAP** on a gold-standard positive set — *not* a graph neural network.
  Directly transferable to visual ML. (Mountjoy et al., *Nat Genet* 2021.)
- **Network proximity / guilt-by-association.** Disease genes cluster in the interactome as "disease
  modules", and proximity to a module predicts association — indication classification at AUC ≈ 0.81
  (Guney et al., *Nat Commun* 2016). Menche et al. (*Science* 2015) established disease modules
  **and the incomplete-interactome caveat: ~80% of interactions are unmapped** — which turns out to
  matter a great deal here (§8.9).
- **Degree-weighted path counts (DWPC).** Typed path counts over a heterogeneous network,
  degree-damped so hubs don't dominate (Himmelstein et al., *eLife* 2017).
- **Interpretability drives adoption.** TxGNN (*Nat Med* 2024, built on PrimeKG) showed path
  explanations raised expert accuracy **+46%** and confidence **+49%**.

## 3. Data exploration — what the data forced us to do

Four exploration findings each changed the design. They are the reason the model looks as it does.

### 3.1 The label set is study-biased, and that governs every metric

**Label:** `is_target` = 1 if a disease–protein association edge exists (genetic association +
somatic mutation @ score ≥ 0.3).

Curated associations skew toward well-studied genes, which are also interactome hubs. **A model that
exploits hub-ness therefore scores *better* on AUC even when it is less useful for finding
under-studied targets.** This is why §7.2 measures hub bias explicitly as a second axis rather than
trusting AUC alone.

### 3.2 The disease ontology is redundant, and it leaks

Inspecting the disease nodes surfaced **18 separate breast-carcinoma concepts** (`breast carcinoma`,
`invasive ductal breast carcinoma`, `female breast carcinoma`, …). Confirmed live on the persona
diseases:

- **`breast cancer` ↔ `breast carcinoma`** and **`obesity disorder` ↔ `morbid obesity`** are each
  **immediate parent/child, one hop apart** — and each pair was split across the train boundary.
  **All four personas were compromised**, two by being in train outright, two by having their
  parent or child in train.

**Graph-topological family construction was tried and rejected — it collapses at every setting:**

| Approach | Largest component (of ~900–1,150 eligible diseases) |
|---|---|
| undirected transitive closure | 24,917 (the whole ontology) |
| undirected K-hop, K=1 / K=2 | 930 (81%) / 1,145 (99%) |
| directed ancestor + hub filter (9 configurations) | 759–872 (83–96%) |

Two causes: broad classificatory terms (one has 1,906 children) are themselves eligible diseases and
are *genuine* ancestors, so directionality doesn't help; and **51% of eligible diseases have more
than one direct parent** — it is a directed acyclic graph, so transitive union-find chains unrelated
branches together. **No clean global partition of the ontology exists.** §5.3 is the workaround.

### 3.3 Granularity trades novelty against confidence

The coarser, smaller-module term surfaces *novel* candidates; the larger-module term mostly
*re-identifies known* targets.

| persona | known / 50 | novel / 50 | min score | read |
|---|--:|--:|--:|---|
| breast carcinoma | **50** | 0 | 0.989 | densely annotated — a ranking sanity check, **no discovery value** |
| obesity disorder | 26 | 24 | 0.967 | **balanced — best demo disease** |
| breast cancer | 18 | 32 | 0.902 | **balanced — best demo disease** |
| morbid obesity | 0 | **50** | 0.749 | sparse module — all hypothesis, lowest confidence |

Aggregating to the family level lifts breast cancer's AUC 0.704 → 0.907 but degrades the candidate
list from mechanism-specific (DNA-repair genes) to pan-cancer drivers present in 19 of the family's
20 members.

> **Aggregation buys AUC and costs specificity. Split by family for leakage control; report and act
> at the disease level.**

### 3.4 The model cannot resolve *morphological* subtype — but it does resolve *molecular* subtype

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

**The breast panel narrows this claim further, and the narrowing matters** (§8.13, `breast_panel_*`,
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
> also holds breast, so the comparison would have been breast-vs-lung (§10.2). It now selects the
> lung-cancer **family**, which is the stable expression of "lung cancer and its histological
> subtypes" and matches the recipe's stated purpose.

## 4. Feature engineering

`G`=gene, `D`=disease, `P`=pathway, `F`=molecular function, `B`=biological process. DWPC uses the
standard degree-damping exponent (weight = ∏degree^−0.4), so paths through hubs are down-weighted.

### 4.1 The 12 features in the champion model

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

The rejections are more informative than the inclusions, because most encode a leakage mechanism.

| Feature | Reason rejected |
|---|---|
| `relation` | **Hard leak** — non-null iff the edge exists. A restatement of the label. |
| `rwr_score`, `rwr_norm` | **Label-derived missingness.** The recipe records held-out *seed* genes unconditionally while floor-gating non-seeds, and seeds *are* positives → null gap −75 pp. |
| `gene_n_diseases` | **Label-derived** — built from the label relation itself; alone separates the test set at AUC 0.835. |
| `disease_context` | Label-derived (counts module membership in neighbouring diseases) and 95% null. |
| `module_size` | Per-disease constant → a pure base-rate encoder with zero within-disease ranking power. |
| `dwpc_GCD` | 99.8% null, and **circular** for target identification: "an approved drug already targets this gene for this disease" nearly restates the label. Retained as a **post-hoc evidence annotation** (§8.7). |
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

### 4.3 Not yet built

| Feature | Rationale | Priority |
|---|---|---|
| ~~Tractability buckets + target class~~ | **SETTLED — rejected as a model input, shipped in the ranking layer instead** (§10.3). Under this label the gain-maximising split is "membrane receptor → lower score", so the feature is actively harmful, not merely neutral. Top-N *within* druggability class recovers the benefit without touching the model. | — |
| `is_plasma_membrane` / `is_secreted` | Cheap druggability proxy, already in the graph; verified feasible. Splitting membrane from extracellular separates receptor from ligand. Superseded in practice by the class-grouped presentation (§10.3). | 4 |
| **Essentiality + tissue-expression breadth** | The real safety axis. The free proxies were measured and **rejected as filters** (§10.3) — genetic constraint runs *with* druggability, liabilities mark precedent. A direct measurement is required, and that means a new source. | 1 |
| gene-family / paralog (leave-one-out) | A paralog being a known target is evidence nothing else captures. **Blocked** — the gene vocabulary lacks family columns. **Must be leave-one-out** or it becomes a label-derived shortcut. | 3 |
| `disease_phenotype_context` | Phenotype-similarity alternative to the hierarchy view of "related diseases". | 4 |
| Cellular-component metapath | Co-localization is usually too broad to discriminate ("nucleus" spans thousands of genes). | 5 |
| Phenotype metapath | Now unblocked — the phenotype–protein edge exists. | 5 |

### 4.4 Why the metapaths are matrix code, not graph queries

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

**Unit:** a `(gene, disease)` pair → P(true association).
**Disease eligibility:** ≥ 20 protein seeds, so network features are estimable — 1,154 of 27,153
diseases qualify.

### 5.2 The candidate pool is a leakage control, not a convenience filter

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

#### 5.2.1 `dwpc_GCD` is the drug route, and it selects the population on the outcome

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
| all positives *(the documented number)* | 0.6911 |
| positives the model has route features for | **0.7337** *(+0.0426)* |
| on the 69 affected diseases only | 0.6210 → **0.6929** *(+0.0719)* |

Direct confirmation of the mechanism: GCD-only positives receive mean `proba_1` of **0.265** against
**0.540** for route-supported positives — half the score, because half their route features are absent.

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
| all positives | 0.6911 | how the model ranks approved targets among everything in its population |
| route-supported positives only | **0.7337** | how it ranks the approved targets it can actually see |

That pair dominates dropping the route, which would have bought the same number at the price of 22
diseases.

> **The reported 0.6911 is not wrong, but it answers a worse question than 0.7337 does.** Report both:
> one is "how the model ranks approved targets among everything in its population", the other is "how
> it ranks the approved targets it can actually see".

### 5.3 The family split — an external curated antichain

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
trap: when indices are renumbered, whichever keys were *incidentally* in validation can move. See
§5.5.

**As rebuilt, all five persona groups land in validation via the forced clause**, and the elevation
step merged breast and lung under `thoracic cancer` (§10.2), so the `respiratory system cancer` entry
is now redundant — retained because it costs nothing and correctly expresses the intent. Only type 1
diabetes, which is a watch-list disease rather than a persona, sits in train.

### 5.5 The index remap (2026-08-17)

Every hardcoded index in this project was resolved to `(node_id, node_type, node_source)` in the
reference graph and looked up again in the rebuilt graph. The key is unique on both sides — 0
duplicates in 113,544 / 113,391 rows — and **all 14 values resolved with identical node names**, so
the mapping is unambiguous. Recorded in [index_remap.json](index_remap.json).

| Disease | reference | rebuilt | Used in |
|---|--:|--:|---|
| obesity disorder | 16415 | **37143** | persona filter, staged benchmark, split audit |
| thoracic cancer *(split key)* | 14786 | **45109** | split expression |
| respiratory system cancer *(split key)* | 14654 | **45876** | granularity check, split expression |
| overnutrition *(split key)* | 14442 | **46033** | split expression |
| breast carcinoma | 16029 | **47415** | split audit |
| diabetes mellitus *(split key)* | 16420 | **47437** | split expression, split audit |
| lung adenocarcinoma | 14274 | **47469** | persona filter, staged benchmark |
| morbid obesity | 61925 | **47530** | split audit |
| type 2 diabetes mellitus | 16596 | **47537** | persona filter, staged benchmark, split audit |
| non-small cell lung carcinoma | 15624 | **47604** | persona filter, staged benchmark |
| chronic kidney disease | 14644 | **47654** | persona filter, staged benchmark, split expression |
| breast cancer | 15347 | **49721** | split audit |
| lung cancer | 15317 | **52236** | persona filter, staged benchmark |
| type 1 diabetes mellitus | 19569 | **54058** | split audit |

**One key had to be added, not just remapped.** `respiratory system cancer` was in validation only
*incidentally* (14654 mod 10 = 4). Its new index lands in train (45876 mod 10 = 6), and it was **not**
in the forced list — so the three lung personas would have moved to train, and because the persona
filter reads the *validation* split it would have **returned zero rows rather than erroring**. It is
now forced explicitly, which also removes the reliance on luck for the other three.

**Two properties were verified rather than assumed:**

- **Family integrity holds.** Zero split keys have members in more than one split role after
  remapping — the leakage control survives, because the key is derived from the hierarchy and the
  hierarchy is unchanged (129,606 edges in both graphs).
- **58.8% of modelled diseases change split role** (4,008 of 6,821). This is inherent: the split rule
  is a modulo over an arbitrary integer, so renumbering reshuffles it. It matters for the retrain
  acceptance check — see §10.1.

**The rebuild then found two more index-dependent behaviours that this remap did not anticipate** —
family assignment and split-key elevation. Both are in §10.2; both are the same root cause as the
split rule, which is why that section states the general lesson rather than the three instances.

## 6. Model configuration and selection

### 6.1 The audit that drove feature selection

Three measurements on a 15-feature baseline:

1. **7 of 15 inputs were gene-only** — 0.0% of genes showed more than one distinct value across the
   four persona diseases. They cannot answer "is this gene a target *for this disease*", only "is
   this gene generally prominent".
2. **The hub axis was over-represented** — degree correlated ρ +0.975 / +0.927 / +0.804 with three
   other centrality features. Four near-duplicates against DWPC's two, so the hub *penalty* was
   outnumbered.
3. **The hub-penalised features are the ones that work** — within-disease single-feature AUC:
   `dwpc_GPGD` 0.641, `dwpc_GGD` 0.601, versus ≈ 0.5 for every gene-only feature.

### 6.2 Configuration

| Setting | Value | Note |
|---|---|---|
| Algorithm | **gradient-boosted trees** | logistic regression comparator: 0.834 vs 0.895 pooled — the non-linearity is worth ~0.06 |
| `max_depth` | grid 4–6 | |
| `n_estimators` | 300, early stopping on | |
| Class handling | class weights | positives are ~1.9% |
| Seed | 1337 | also the split seed |
| Evaluation metric | ROC AUC, macro | but **report per-disease AUC** (§7.1) |
| Train/test policy | two explicit datasets | `psplit_train_set` / `psplit_test_set` (2,693,788 / 561,214) |

**Feature-handling standard (mandatory): every numeric input gets standard rescaling + mean
imputation. No exceptions.**

- **Rescaling is a no-op for trees** — it is affine and monotonic, and tree splits are invariant to
  monotonic transforms. It matters for the logistic comparator, so uniformity is cheap insurance.
- **Imputation is the one that bites.** The platform imputes *before* the model, so the algorithm's
  native sparsity handling never engages and the fill value is decisive. **Mean** puts nulls at the
  distribution centre, indistinguishable from average rows, so the tree **cannot** isolate "was
  missing". **Constant 0** puts them at a separable point, so it **can** — and with four features
  carrying **−31.6 pp null gaps by label**, that reopens leak 2 outright. For a z-score, 0 is doubly
  wrong: it is the null-model expectation, mid-distribution (real median +2.55).
- **Sentinel imputation was tested as a fix and rejected on the second metric.** A large negative
  constant gave the **best pooled AUC in the project (0.8808) and the worst drug-target AUC
  (0.6579)**. Missingness is 93–99.7% gene-level, so exposing it hands the model a real gene-level
  signal that improves association ranking and degrades therapeutic ranking.
- **A presence-flag model cannot answer "do the nulls reveal the target"** — the platform imputes
  before per-feature handling, so every flag is 1 and the model emits one constant value. Materialize
  explicit null-indicator columns instead (see DSS_CHEATSHEET §1).

### 6.3 The threshold is not the ranking

The F1-optimised threshold lands at **≈0.875** against a ~2% base rate. Consequence: **590 of 762
known obesity targets are predicted negative**, recall 22.6%.

> **The prediction column is near-meaningless for discovery. Rank by probability and take top-N** —
> which is what the persona chain does.

### 6.4 The ablation ladder

All three runs share the split, hyperparameters, handling standard and row counts, and all exclude
`prox_closest`, so they are directly comparable.

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

**Report macro per-disease AUC, not pooled.** Pooled AUC gets credit for separating genes across
*different* diseases (easy — a gene in a well-annotated disease outranks one in a sparse disease);
the deliverable is ranking genes *within* one disease. **Pooled overstates by ~7 points** (0.8915 vs
0.8197).

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

### 7.2 Hub-bias meter — the second axis

Among **known targets only** — biology held constant, every gene a true positive — bin by degree and
compare the lowest to the highest quintile. Baseline: Q1 (median degree 3) 6.8% predicted positive
vs Q5 (median 104.5) **40.8%** — a **6× detection swing on network position alone.**

| Model | Q1 probability | Q5 probability | Spread | ρ(degree, probability) |
|---|--:|--:|--:|--:|
| 15-feature predecessor | 0.5732 | 0.7611 | +0.1879 | +0.3304 |
| pruned intermediate | 0.5662 | 0.7417 | +0.1755 | +0.2953 |
| **metapath generation** | 0.6516 | 0.7615 | **+0.1099** | **+0.2424** |

The metapath generation lifts Q1 — low-degree known targets — from 0.573 to **0.652** in absolute
terms. Earlier rungs narrowed the spread only by pulling Q5 *down*. **This is the first model that
improves under-studied targets outright rather than relatively.**

> ⚠ This table is the retired 13-feature generation, which differs from the champion only by
> including `prox_closest` (measured neutral on both headline metrics). Recompute before quoting
> externally.

### 7.3 Per-family validation

Same chain grouped by family: **505 families, macro 0.7976, median 0.8116, recall@20 0.1145**
(reference: 484 / 0.8060 / 0.8214 / 0.1208). Against the 15-feature predecessor's 0.7543 / 0.7607 /
0.0982 that is **+0.043 macro** and recall@20 +17%, which matters more than AUC for a top-N
deliverable.

| Group | n | Macro AUC | *(reference)* | predecessor |
|---|--:|--:|--:|--:|
| **multi-disease families** (grouping actually applies) | 28 | **0.9023** | *0.9076* | 0.8615 |
| single-disease families (grouping is a no-op) | 477 | **0.7914** | *0.8010* | 0.7487 |

**The largest families are cancers plus two haematological groups:**

| Family | members | positives | AUC |
|---|--:|--:|--:|
| haematopoietic & lymphoid neoplasm | 29 | 4,673 | 0.9184 |
| breast cancer | 19 | 4,818 | 0.9253 |
| lung cancer | 17 | 4,706 | 0.9301 |
| sarcoma | 13 | 1,434 | 0.9334 |
| salivary gland cancer | 11 | 709 | 0.9254 |
| **anemia** | **9** | **622** | **0.8514** |
| bone cancer | 9 | 819 | 0.9254 |
| uterine cancer | 8 | 1,286 | 0.9338 |

> **⚠ This table is not comparable to the reference's family table, and the reason is instructive.**
> Family *structure* barely moved — 99.7% of diseases keep the same family, and the largest family is
> 75 members in both builds (§10.2). What changed is **which families are in validation**, because
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

The label comes from **association** edges. That is not the same population as the proteins drugs
actually hit, so association AUC alone cannot say whether the ranking is therapeutically meaningful.

**Ground truth:** approved-indication edges ⋈ drug-target edges → **4,110 (disease, gene) pairs over
416 diseases and 778 genes**; 1,507 fall in the validation split across 112 diseases. Independent of
the label by construction — only 198 of 1,507 are also association positives — and **no model feature
traverses a drug node**, which is what makes the number interpretable.

**Headline: association AUC does not predict therapeutic relevance.** Across 130 diseases,
Pearson r = **0.024** between a disease's association AUC and its drug-target AUC (reference: 0.097
over 112). For the champion: mean drug-target AUC **0.6911** vs association 0.7838 *on those same 130
diseases*, **122 of 1,538** validated targets in the top 50 (7.9%), and **30 of 130 diseases below
0.5**. The two are decoupled, not merely offset — drug AUC *beats* association AUC on **51 of 130**.

**This is the most robustly reproduced finding in the document.** Rebuilt on a different graph, a
different split and a 19% smaller training set, the correlation stayed near zero (0.024 vs 0.097 — if
anything weaker) and the hit rate reproduced to a tenth of a point (7.9% vs 7.8%).

> **⚠ Drug-target AUC rests on the same inferred label** as §8.3 — two thirds of its positives come
> from drugs that are multi-target *and* multi-indication (§8.1). The *decoupling* finding is robust to
> this, because inflation adds noise and noise cannot manufacture a correlation of zero. But the
> absolute value of 0.6911 should be read as approximate.

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
precisely backwards and is the mechanism behind the ligand-vs-receptor failure in §8.9. **Add
tractability together with a label change, not before.**

The reference measured 0.76× / 3× for membrane receptors and 13× / 15.6× for ion channels and
structural proteins; the rebuild gives 0.78× / 3.16× and 11.9× / 12.3×. Same direction, same order of
magnitude, same conclusion.

> **Standing rule:** every future feature or preprocessing change reports **both** metrics.
> "Association up, drug down" is a warning flag, not a win.

### 7.5 The decisive experiment — training on the drug label (a negative result)

Everything above pointed at the *objective* as the binding constraint, but that was an inference.
`m7-drug-label` tests it directly: **identical features, split, hyperparameters and handling — only
the label changes.** Train on a weak label (approved indication OR under investigation), evaluate on
the strict approved-only label, so the model learns mechanistic plausibility and is scored on what
got approved.

Why weak-for-train / strict-for-eval: strict is too rare to train on — the test split holds **196
positives over 18 diseases**, which cannot support model selection. Weak gives 13,573 train
positives over 230 diseases. The cost is that weak labels include **failures**: a target trialled and
abandoned still counts positive.

> **⚠ The artifacts for this experiment were DELETED on 2026-08-18** — the saved model, its three
> `psplit_*_drug` splits, and the six evaluation datasets. It was never rebuilt on the shared graph,
> and a stale unreproducible chain sitting in the flow cost more in reviewer confusion than it bought.
> **Every number below therefore lives only in this document.** They remain internally consistent —
> each is a reference-graph number compared against another reference-graph number — and the finding
> is about the *benchmark's structure*, which a graph rebuild does not change. To reproduce it, the
> five recipes are in git at `97de713:dss_recipes/compute_drug_label_*.py`.

| Metric (112 reference validation diseases with a strict drug target) | `m3-f12` | `m7-drug-label` |
|---|--:|--:|
| Mean per-disease **drug-target** AUC | 0.6836 | **0.9324** |
| Validated targets in top 50 | 117 | **439** of 1,507 |
| Diseases scoring below 0.5 | 26 | **3** |
| Mean per-disease **association** AUC | **0.8228** | 0.6444 |

**So the objectives are genuinely in tension, and that part of the inference held.** Changing the
label moves drug-target AUC +0.2488 and association AUC −0.1784. There is no free lunch: which axis
to optimise is a **product decision, not an optimisation problem**.

**But the +0.2488 is not a win, and this is the more important finding.** A no-graph,
no-disease-information baseline — *"how many training diseases is this gene a drug target for"* —
scores **0.9354** on the same benchmark. **It beats the trained model**, which wins on only **44 of
112** diseases. The benchmark is dominated by **gene identity**, not disease-specific prediction: the
split is by disease, so no evaluation *pair* was seen in training, but the ~800 recurring drugged
**genes** were. This is the same structural failure that got `gene_n_diseases` rejected as
label-derived (§4.2) — it reappeared on the *evaluation* side instead of the feature side.

**Removing the shortcut leaves almost nothing to measure.** Holding out *genes* as well as diseases —
scoring only strict pairs whose gene is a drug target in **no** training disease — leaves **57
positives across 19 diseases**, down from 1,507 across 112, at AUC 0.7266. That is thin and
high-variance (per-disease values run 0.036 to 1.000 on 1–8 positives each), so it cannot carry a
headline either.

**Verdict — recorded as a negative result and not deployed.** Two independent reasons:

1. **Measured:** its apparent advantage is a gene-popularity artifact, and it pays with a 0.18
   collapse in association ranking.
2. **On principle:** the drug label encodes *historical development choices* — ion channels 13×
   enriched, structural proteins 15.6× — so a model trained on it is biased toward what the industry
   has already drugged. That is the opposite of target identification.

**Consequence for reporting.** Drug-target AUC stays a **mandatory second metric and a warning
flag**, never a headline and never an optimisation target. The champion's drug-target AUC — 0.6836 on
the reference, **0.6911 rebuilt** — should be read as *"this model deliberately declines a shortcut
that scores 0.9354"*, not as a therapeutic failing.

> **A benchmark that a lookup table wins is measuring the lookup, not the model. Before treating any
> metric as a target, check what the dumbest possible predictor scores on it.**

## 8. Results

### 8.1 Three axes, and two ground truths

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

Drop the known association targets, re-rank what remains, and ask how many of the top-K **novel**
candidates are drug-linked. Lift is against the novel base rate, so >1 means the model ranks real,
previously-unannotated targets above chance.

| top-K novel | approved: lift / hits / diseases | investigational: lift / hits / diseases |
|--:|---|---|
| 10 | **11.4×** / 21 / 12 | 7.4× / 169 / — |
| 20 | **12.6×** / 39 / 19 | 6.8× / 293 / — |
| 50 | 7.5× / 76 / 24 | 5.1× / **611** / — |
| 100 | 6.4× / 130 / 33 | 5.0× / 1,138 / — |
| 200 | 4.5× / 206 / 43 | 4.0× / **1,802** / — |
| *diseases measurable* | **122** | **298** |

**The label's construction needed testing before these numbers could be trusted, and it took two
passes to get right.** The sensitivity analysis below is the result; the two intermediate readings are
recorded in the decision log because both were wrong in instructive ways.

| Ground truth | pairs | novel in val | diseases | pos/disease | expected@10 | **lift@10** | lift@50 | lift@200 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| join, approved *(original)* | 4,110 | 1,359 | 122 | 11.1 | 1.36 | **11.40** | 7.46 | 4.53 |
| join, drugs with ≤3 targets | 1,385 | 459 | 114 | 4.0 | 0.40 | *7.40* | 4.54 | 3.38 |
| join, single-target drugs | 634 | 202 | 87 | 2.3 | **0.20** | *0.00 — unmeasurable* | *1.90* | 2.30 |
| join, single-target & ≤3 ind. | 337 | 107 | 54 | 2.0 | **0.11** | *0.00 — unmeasurable* | *2.78* | 3.88 |
| **`known_drug` ≥ 0.8 (curated)** | **3,253** | **1,173** | **114** | **10.3** | **1.17** | **17.65** | **8.86** | **4.70** |
| `known_drug` ≥ 0.6 | 8,493 | 2,916 | 174 | 16.8 | 2.92 | 8.36 | 4.69 | 3.28 |
| `known_drug`, all scores | 67,748 | 21,935 | 325 | 67.5 | 21.93 | 6.91 | 4.91 | 3.61 |

**`expected@10` is the number of hits chance alone would produce** (diseases × 10 slots × base rate).
**Below ~1, an observed zero is uninformative** — it cannot separate "no enrichment" from "enrichment
too sparse to see". The single-target restrictions expect **0.20 and 0.11** hits, so their `0.00`
measures nothing. Rows in *italics* are underpowered at that K and must not be quoted.

**Across every adequately-powered variant, head-of-list lift is 6.9–17.7× and the original 11.4× sits
in the middle.** The curated label gives the *highest* estimate, not the lowest. **Deep-list lift
converges to 2.3–4.8× across all seven variants**, which makes it the robust number.

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

| top-K novel | observed | degree-matched expected | **pooled** naive → dm | **macro** naive → dm |
|--:|--:|--:|---|---|
| 10 | 2,094 | 684 | 3.31× → **3.06×** | 2.97× → **2.86×** |
| 20 | 3,942 | 1,352 | 2.76× → **2.91×** | 2.78× → **2.77×** |
| 50 | 9,207 | 3,293 | 2.48× → **2.80×** | 2.59× → **2.69×** |
| 100 | 16,963 | 6,455 | 2.24× → **2.63×** | 2.39× → **2.57×** |
| 200 | 30,075 | 12,643 | 1.98× → **2.38×** | 2.11× → **2.36×** |

*Pooled = Σobserved / Σexpected. Macro = mean of the per-disease lift, consistent with the macro
per-disease AUC used everywhere else in this document.*

**Degree-matching strengthens the result from rank 20 onwards and weakens it at rank 10 — under both
estimators.** So the top ~10 candidates per disease *do* carry a hub component, and everything below
that is enriched for tractable genes by **more** than connectivity explains. Below rank 20 the model's
novel candidates skew slightly *lower*-degree than the pool, so the hub-corrected expectation drops
and the enrichment grows.

> **⚠ CORRECTED 2026-08-19.** An earlier revision claimed degree-matching strengthened the result
> *unconditionally*. That rested on putting a **pooled** dm lift (3.06×) next to a **macro** naive lift
> (2.97×) in the same row — two different estimators, which manufactured the crossover at rank 10.
> Computed consistently, rank 10 goes the other way in both. **The quotable range was not affected**;
> the unconditional claim was.

`assessed` tractability gives only 1.21–1.30× — expected, since 59.9% of all genes qualify, making it
a blunt instrument. **Report `demonstrated`; keep `assessed` only as a coverage-maximising secondary.**

> **This is the most robust positive claim in the document.** Unlike the discovery lift (§8.3), whose
> label is inflated and whose head-of-list estimate moved between 6.9× and 17.7× depending on
> construction, this one uses an uninflated gene-level assertion and *survives* its own confound
> control everywhere below rank 20. **~2.4–3.1× above a degree-matched null** (pooled; **2.4–2.9×**
> macro) is the number to quote — and the rank-10 exception is worth volunteering, because being able
> to say where hub bias does and does not explain the ranking is itself the differentiator (see
> [DEMO_NARRATIVE.md](DEMO_NARRATIVE.md) Q2).

### 8.5 The ligand-vs-receptor failure is real but does NOT generalise

The stated prediction for §8.4 was that the head would show a tractability **deficit** (≤1.0×),
because §8.9's case study says the model ranks secreted ligands above membrane receptors. **That was
refuted**, and the follow-up measurement scopes the original claim properly.

Secreted-protein share at top-50 minus its share of the candidate pool, across 668 diseases:

| | value |
|---|--:|
| mean excess | **−0.93 pp** |
| median excess | **−3.78 pp** |
| diseases where secreted is over-represented | **185 of 668** |

**On average the model *under*-represents secreted proteins at the head** — the opposite of what §8.9
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
best tractability enrichment in the panel.** So §8.9 describes a handful of genes in one pathway, not
obesity's ranking as a whole, and certainly not the model's general behaviour. The *mechanism* it
identifies (membrane-protein assay bias sparsifies receptor neighbourhoods) is real; its *scope* was
overstated by generalising from a single pathway.

### 8.6 Candidate output — biological coherence

Each persona's list reads correctly for its biology, which is the qualitative half of validation:

| Persona | Signature of the top candidates |
|---|---|
| **chronic kidney disease** | **12 of the top 20 novel are SLC solute carriers** (SLC13A2/A3, SLC22A3, SLC47A1, SLC7A2/A3/A6/A7, SLC3A1, SLC26A5, SLC2A6, SLC38A4) — proximal-tubule transport machinery, and SLC22A3/SLC47A1 are genuine renal drug-handling transporters. Plus DDR2 and FGFR2, both fibrosis-relevant with approved drugs. |
| **lung cancer** | **7 of 20 are CHRN nicotinic-receptor subunits** (CHRNA6/A7/A9, CHRNB1/B3, CHRND, CHRNE) — 15q25 is the best-replicated lung-cancer GWAS locus. Alongside ERBB3/ERBB4, PIK3CB/CD, NRAS, HRAS, EP300, MSH2. |
| **NSCLC / lung adenocarcinoma** | JAK-STAT and chromatin: STAT1, STAT5A/B, SMARCA2, BRD7, HDAC3; the PI3K axis (IRS1/2, PIK3R2, PDPK1, GSK3B); DDR (MRE11, TOPBP1); and CRKL, an amplified 22q11 driver. |
| **obesity disorder** | GHSR (#8, ghrelin receptor), ADRB2 (#17, approved-validated), MCHR1 (#23), GRM1 (#24) — a coherent neuroendocrine receptor cluster, GHSR and MCHR1 both clinically pursued for obesity. |
| **type 2 diabetes** | β-cell and insulin signalling: ADCY2/ADCY3, ITPR3, ATP2A2 (SERCA2), NOTCH1, RUNX1, CREBBP, PIK3CB. ADCY3 is an established T2D/obesity locus. |

**Ranking quality falls monotonically with rank**, pooled over the personas: known-target density
60.0% (ranks 1–10) → 55.0% → 46.7% → 46.7% → 43.3% (41–50), with mean score tracking it. **Read this
as calibration evidence, not as a novelty ceiling** — see §8.6.

### 8.7 The filter, validated on all three axes

The filter is **three clauses: novel → tractable → not-secreted.** A fourth, "exclude known
liabilities", was measured and rejected (§10.3) and is still computed so the damage stays visible.

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

### 8.8 Persona selection — the criterion that was wrong, and the corrected panel

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

### 8.9 Case study — GLP1R, and the limits of an interactome-based model

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
population changes (58.8% of diseases moved split, §5.5). One consequence for the demo: the
ligand-vs-receptor gap **widened**, so the contrast in §8.8 is more striking than when it was written.

**The evidence the model is not allowed to use.** The drug metapath for GLP1R traces to a single
compound. It is rejected as circular (§4.2) — defensible, but it means the most decisive evidence is
computed and discarded. **Use it as a post-hoc annotation, not a feature.**

**The honest lever is presentation, not the model.** In the `membrane / cell-surface` column GLP1R
sits behind GHSR (#8), MCHR1 (#23), MC4R (#47) and GIPR (#365) — all defensible obesity receptors.
That reads better than a single gene's absolute rank without pretending 699 is good.

### 8.10 On-graph explanation

Anchor demo: the breast-cancer top-10 contained **RAD50, NBN, MRE11** — all three members of the MRN
double-strand-break repair complex, two of them novel. **The prediction explains itself on the canvas.**

Conventions: undirected traversal; **relationship variables must be bound AND returned** or the canvas
shows floating nodes; the graph engine's label for genes is `protein`. **Indices are
snapshot-specific — re-derive before running** (§10.4).

```cypher
// 1. Why these genes? Top-10 predictions + interaction evidence to a KNOWN module gene.
MATCH (D:disease {node_index: $disease})
MATCH (g:protein) WHERE g.node_index IN $top10
MATCH (g)-[ppi:protein_protein]-(m:protein)-[assoc:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, ppi, m, assoc, D LIMIT 300
```

```cypher
// 2. THE CONTRAST SHOT — ligands (dense) vs receptors (sparse), same disease.
//    Makes the assay bias visible: the druggable half is thin purely because
//    membrane receptors resist the assays that built the interactome.
MATCH (D:disease {node_index: $disease})
MATCH (g:protein) WHERE g.node_index IN $ligands + $receptors
MATCH (g)-[ppi:protein_protein]-(m:protein)-[assoc:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, ppi, m, assoc, D LIMIT 400
```

```cypher
// 3. The evidence the model is NOT allowed to use: receptor <- compound -> disease.
MATCH (D:disease {node_index: $disease})
MATCH (g:protein {node_index: $receptor})
MATCH (g)-[dt:drug_protein]-(C:drug)-[ind:indication|drug_investigated_for]-(D)
RETURN g, dt, C, ind, D
```

**Run these in the interactive explorer, not the query recipe** — the recipe path is unreliable on
this graph (opaque errors inside the plugin's generated script; buffer-pool exhaustion on
variable-length expansion).

**Improvement worth making:** the gene lists are pasted literals because the materialized graph
carries no model output. Writing predicted score and rank as gene-node properties would turn these
into `WHERE g.pred_rank <= 10`.

### 8.11 Druggability and safety annotation on the ranked list

Built to make the §8.9 failure *visible* without touching the model. Per-gene attribute tables joined
on `gene_index` — **no nodes, no edges**, so the graph and its indices are untouched. This is the
pattern for every future annotation layer: an attribute table costs one join, an edge forces a graph
rebuild, a re-index and full feature recomputation.

| Source | Signal | Coverage | Verdict |
|---|---|--:|---|
| Subcellular location (curated + atlas) | membrane / secreted | **90%** | primary workhorse |
| Target class (chemical-biology family) | `Membrane receptor`, `Enzyme`, `Ion channel`… | 28% | authoritative but sparse; **human-readable** |
| Tractability buckets | small-molecule / antibody, has-approved-drug | 29% | modality routing |
| Cellular-component annotation *(in graph)* | membrane / secreted | 36% | gap-fill; covers 343 genes the primary source misses |
| **Curated safety liabilities** | adverse events, dose dependence | **4.5% flagged** | **display only** (§10.3) |
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
> still outrank receptors *globally*; the fix is class-grouped presentation (§10.3). And
> has-approved-drug is **gene-level across all indications** — "chemical matter exists", not "this
> drug works in this disease".
>
> **⚠ Two columns must not become filter controls.** Genetic constraint runs *with* druggability, and
> liabilities mark drug precedent rather than risk (§10.3). Both are present in the deliverable —
> the constraint columns unintentionally, via automatic column selection — and both would strip the
> best candidates if filtered on. The liability `event` field also mixes real adverse events with
> bare mechanism descriptors (`regulation of catalytic activity`) and risk-factor biology (lung
> cancer's nicotinic candidates are flagged `nicotine dependence`, the disease's own risk mechanism).

### 8.12 What it delivers, concretely

`target_candidates_2` — **129,253 rows over 13 personas**, every scored candidate ranked, carrying
score, SHAP drivers, rank, known-target status, druggability class, tractability and safety
annotation. The scientist filters; nothing is pre-cut.

Progressive filtering, obesity disorder:

| filter | candidates |
|---|--:|
| all | 13,126 |
| novel only | 12,364 |
| + tractable | 8,615 |
| + not secreted | 7,877 |
| + rank ≤ 200 | **~70** |

A working shortlist — GHSR (#8), ADRB2 (#17), STAT3 (#18), MCHR1 (#23), GRM1 (#24) — reached by the
scientist's own thresholds.

### 8.13 The breast panel — built to be falsified by a clinician

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
   **1.04%** of diseases. See §5.2.1 and §10.5 for the corrected scope of this problem.

Also: **TP53 ranks 2 for triple-negative but is labelled *novel*, while being a *known* target for
HER2+ and for the umbrella term.** "Novel" here means *not annotated for this particular subtype*, not
unknown to science. Unexplained, it makes the model look naive.

**The deliverable is a form, not a report.** `breast_shortlist` is 118 rows over 4 arms; each arm leads
with its top known targets as a calibration anchor, then 20 novel candidates, then four blank columns
for the clinician's verdict. **If the surgeon rejects an arm's known block, the novel block is not worth
their time** — and that disagreement is the more valuable finding. Full briefing in
[BREAST_SURGEON_BRIEFING.md](docs/annotation/BREAST_SURGEON_BRIEFING.md).

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
| `42 Validation - leakage & granularity` | 9 | **Q5, Q6** | split audit, disease-hierarchy annotation, lung granularity check, **breast subtype separability** (§8.13) |
| `43 Validation - disease families` | 14 | **Q5** | per-family AUC and top genes per family |
| `50 Results - target candidates` | 14 | **Q1** | persona filter → SHAP scoring → `rank_per_disease` (Window) → 2 decoration joins → `target_candidates_2`, plus the **clinician review form** `breast_shortlist` |
| `60 Dashboard (serving)` | 10 | serves **Q1** | the flattened serving tables — `dashboard_candidates`, `dashboard_persona_trust`, `drug_evidence_pairs`, disease pool sizes |
| `Default` | 0 | — | empty; DSS will not let it be deleted |

**Every zone carries its rationale as a Flow description in DSS**, and since 2026-08-19 each one leads
with **the demo question it answers** — the Q1–Q6 numbering from
[DEMO_NARRATIVE.md](DEMO_NARRATIVE.md) §2. Zones that are deliberately *not* demo material say so
outright (`10`–`12`, and the ablation ladder in `31`). A reviewer opening the flow gets the argument,
and a presenter gets the running order, without either of these documents.

**Recipes are named for actions, not outputs.** An earlier pass renamed them after finding recipes
called things like `compute_graph_features_sampled_2` (now `filter_has_path_evidence`).

**Heavy graph math lives in code, not plugin recipes** — the metapaths, proximity, random walk and
degree-corrected overlap. The query-recipe path repeatedly failed at this scale (§4.4).

**Everything in zones 10–60 was rebuilt on 2026-08-17** against the shared graph, so every reported
number comes from one generation. One exception, flagged where it appears: the hub-bias meter (§7.2)
has no recipe and is still on the retired generation.

### 9.1 Why four validation zones — and which objection each one kills

The previous layout had one `Results - model performance` zone and one `Diagnostics (optimisation)`
zone that had swollen to **40 items** — it was where everything went that was not scoring, and by the
end it held the three-axis overhaul, the leakage audits, the persona selection and a dead experiment
in one undifferentiated pile. **The flow no longer showed which findings the deliverable rests on.**

The split now follows the **demo objection ladder** ([DEMO_NARRATIVE.md](DEMO_NARRATIVE.md) §2) rather
than our own metric taxonomy, because that is the order a sceptical scientist actually asks in:

| Demo Q | What they say | Zone | The evidence |
|:--|---|:--|---|
| **Q1** | *"Show me the list."* | `50`, `60` | 129,253 ranked rows; obesity → 65 candidates on the scientist's own thresholds |
| **Q2** | *"These are just the famous genes."* | `41` | degree-matched tractability **2.4–2.9×**; strengthens below rank 20, weakens at rank 10 (§8.4) |
| **Q3** | *"You already knew all of these."* | `41` | novel-discovery **11.4×** at top-10 approved; **MAPK3 novel #3 / list #61** for NSCLC (§8.3) |
| **Q4** | *"Your ground truth is garbage."* | `41` | 82% inflation measured, then re-run on curated `known_drug` — result got *stronger* (§8.1, §8.7) |
| **Q5** | *"Would this work on a disease you had not tuned?"* | `40`, `42`, `43`, and `30` | macro AUC **0.8197**/670 diseases; per-family **0.7976**/505; zero straddling split keys |
| **Q6** | *"What can't it do?"* | `42`, `41` | subtype irresolvable (§3.4); ligand-vs-receptor scope (§8.5); no safety axis, and we say so |
| **punch** | — | `41`, `20` | the three refuted gates: druggability inverted, LoF backwards, liability filter deletes ADRB2 (§10.3) |

**Zone 41 is the one to open in a technical review** — it alone answers Q2, Q3, Q4 and carries the
punch line, including both corrections. Zones `50`/`60` are the demo surface; `40`–`43` are the
evidence for it. The old `Diagnostics (optimisation)` name was itself misleading: none of that work
was optimisation, it was the evidence base — which is precisely why it must not be pruned to whatever
a not-yet-designed dashboard happens to read (§10.4).

### 9.2 The candidate-decoration tail, collapsed 5 recipes → 2

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

## 10. Migration, and the decisions settled by measurement

### 10.1 Reconstruction confirmed

Rebuilt end to end on the shared graph 2026-08-17. **Tolerance was set in advance at ±0.02 macro
per-disease AUC; every metric came in inside ±0.01.**

| Metric | Reference | Rebuilt | Δ |
|---|--:|--:|--:|
| **macro per-disease AUC** | 0.8228 *(n=588)* | **0.8197** *(n=670)* | **−0.0031** |
| per-disease, positives ≥ 10 | 0.8278 | 0.8323 | +0.0045 |
| per-split-key AUC | 0.8041 | 0.8007 | −0.0034 |
| pooled AUC | 0.8968 | 0.8915 | −0.0053 |
| per-family macro | 0.8060 *(484)* | 0.7976 *(505)* | −0.0084 |
| drug-target AUC | 0.6836 *(112)* | 0.6911 *(130)* | +0.0075 |

**The candidate pool is bit-identical** (6,754,128 both sides), so only the split *allocation*
changed — train shrank 18.8% and the champion held its accuracy. Two sources of movement were
separated in advance: graph drift is 0.03% of edges, all functional-annotation; the split reshuffle
moved 58.8% of diseases and was estimated at **+0.0049**. The observed −0.0031 is smaller than that
estimate, i.e. the two partly cancel. **Metric cross-validation still holds** — visual chain and code
recipe both give 0.8197, max difference 1.9×10⁻⁴.

### 10.2 What the rebuild exposed — three index-dependent behaviours

All three share one root cause: **a rule that breaks ties or selects by lowest `node_index` behaves
differently when the graph is renumbered.** None is a defect; each changes results.

1. **The split rule** (anticipated) — a modulo over an arbitrary integer, so renumbering reshuffled
   58.8% of diseases. Handled by forcing the persona split keys explicitly.
2. **Family assignment** — 6,801 of 6,821 diseases (99.7%) keep the same family; **20 changed anchor**,
   every one at *identical hop depth*, so the walk hit a tie and broke it on lowest index. Overall
   family sizes barely move (largest 75 in both builds).
3. **Split-key elevation** — the lung personas' key moved from `respiratory system cancer` to
   `thoracic cancer`, because a disease with multiple parents picks among them by lowest index.
   **Breast and lung now share one split key** — *more* conservative, and both already in validation,
   so nothing leaked. But it silently broke a diagnostic that selected on that key (§3.4).

> **The transferable lesson:** an arbitrary tie-break is stable only while the thing it keys on is
> stable. When identifiers are reassigned, audit every rule that **ranks, mods or minimises** on
> them — not just the literals.

### 10.3 Target prioritisation — two design decisions, settled on measurement

Both were answered by measuring rather than training: three recipes instead of three model runs.

**Druggability / target class as a model input — rejected.** Not merely "no expected gain" —
**actively harmful under this label.** Against `is_target`, `Membrane receptor` has an association
lift of **0.78 (depleted)** and a drug-target lift of **3.16×**; antibody-tractability's 0.98
association lift is *no signal at all*. A loss-minimising tree therefore learns **"membrane receptor →
lower score"**, reinforcing the §8.7 failure. The label route out is closed on evidence (§7.5).

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

### 10.4 Remaining

- **Report drug-target AUC stratified by route support** (§5.2.1) — 0.6911 all positives / **0.7337**
  route-supported. Removes the 91.8× outcome-selection bias from the *metric* without touching the
  pool, so no disease is lost and nothing is re-fit. **Supersedes the earlier "drop `dwpc_GCD` from the
  filter" recommendation, which bought the same number at the cost of 22 diseases' entire therapeutic
  evaluability.**
- **Execute the scoped prune — 16 items, snapshots already taken.** The ablation chain
  (`scored_m1`/`scored_m2`, 7.9M rows serving a 2,010-row table), `validation_auc_by_disease_2`,
  `drug_target_benchmark_staged`, `target_reachability`, `disease_hierarchy_annotation` and
  `maturity_confound`, with their recipes. All six results are frozen in
  [`docs/appendix/`](docs/appendix/) with a manifest; the saved models stay. **Plus a refactor, not a
  prune: zone `43` collapses 14 items → 2** (one Python recipe `scored_m3` → `family_auc_by_family`),
  keeping Q5's 505-family answer live and dropping a ~4M-row visual chain.
- **Re-derive the Cypher literals in §8.8** — *gene* indices for the demo queries, regenerable from
  the rebuilt ranking but not yet done. Presentation-layer only.
- **§7.5's numbers are documentation-only.** The `m7-drug-label` chain was deleted 2026-08-18 —
  model, 3 splits, 6 evaluation datasets — so **0.9324 / 0.6444, 439-of-1,507 hits@50, the 0.9354
  gene-popularity baseline, the 57-positive gene-holdout and the 196-positive strict test set now
  exist nowhere but this document.** The five recipes are recoverable from git
  (`97de713:dss_recipes/`). Re-run only if someone disputes the negative result.
- **The hub-bias meter (§7.2) has no recipe** — computed ad hoc, still on the retired generation.
- **A direct safety measurement** — now the top feature priority, because §10.3 established the free
  proxies cannot do the job.
- **The dashboard.** Data layer is ready: 129,253 ranked rows with tractability, class and safety
  annotation. What is missing is the UI with rank / class / safety controls.
- **Act on the persona recommendations in §8.8** — retire type 2 diabetes and CKD as headline
  personas, keep one lung term, add an immunology or neurology disease.

### 10.5 Still open

- ~~Druggability as a model input~~ — **settled, rejected** (§10.3); shipped as class-grouped
  presentation.
- ~~Safety as a filter~~ — **settled, rejected** (§10.3); liability annotation shipped display-only.
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

| Date | Decision |
|---|---|
| 2026-07-08 | **Flagship = explainable target prioritizer** (visual ML + SHAP, mirroring the Open Targets L2G pattern). Discovery first; toxicity deferred. Network-topology features only; no embeddings. |
| 2026-07-08 | Feature engineering pushed into graph-plugin recipes over the materialized graph rather than a monolithic graph library. *(Substantially reversed 2026-08 — see §4.4.)* |
| 2026-07-08 | **Degree-corrected proximity dropped** on the reasoning that "the supervised model already sees degree and will absorb hubness". *(Falsified 2026-08-09 and reversed — it was the feature that recovered the failed pruning run.)* |
| 2026-07-28 | **Leaks 1 & 2 diagnosed** (§5). Correct setup = disease-grouped split + the candidate-pool restriction on train AND test + reject label-derived features. A proximity threshold is insufficient — the test set is 87% at the threshold value, so the coverage skew survives. |
| 2026-08-05 | **Feature candidates drafted** contingent on the new annotation layers. A binary inflammatory flag was ranked priority 1 and the functional metapaths priority 2. *(Priorities inverted by results — see 2026-08-10.)* |
| 2026-08-08 | **Leak 3 found: ontology hierarchy** (§3.2). All four personas compromised. **Rejected:** graph-topological family construction — it collapses 83–96% of diseases, because broad classificatory terms are themselves eligible and 51% of diseases have >1 direct parent. **Adopted:** rollup to an external curated antichain of 137 terms. |
| 2026-08-08 | **A candidate filter can leak even when the feature is rejected.** A filter on a random-walk feature's non-nullness scored AUC 0.946 and was withdrawn — the recipe records seeds unconditionally, so non-null is label-derived (null gap −75 pp vs +0.43 pp for the proximity feature). **Rule: disqualify a filter when its *missingness* is set by a label lookup, not when its values correlate with the label.** |
| 2026-08-09 | **Report per-disease AUC, never pooled** — pooled overstates by ~7–9 points and hid a real regression in the first ablation run. |
| 2026-08-09 | **Granularity: split by family, report by disease** (§3.3). Family aggregation lifts the weakest persona 0.704 → 0.907 but degrades candidates from mechanism-specific to pan-cancer. |
| 2026-08-09 | **Case study accepted as a known limitation, not a bug** (§8.11): the model finds the right pathway but not the right druggable node, because membrane receptors resist the assays that built the interactome. The prediction column is near-useless for discovery (590/762 known targets are false negatives at the F1 threshold). |
| 2026-08-09 | **Feature audit** (§6.1): 7 of 15 inputs were gene-only, the hub axis had 4 collinear encodings, every gene-only feature scored ≈0.5. Hub-bias meter established (6× detection swing across degree quintiles). |
| 2026-08-10 | **Ablation ladder complete** (§6.4). Pruning alone **failed** on per-disease AUC despite flat pooled AUC; the provenance controls recovered it; the functional metapaths won decisively with every metric improving at once. Reverses the 2026-07-08 proximity decision. |
| 2026-08-10 | **Metapaths implemented as matrix code, not graph queries** (§4.4) — the query engine exhausted its buffer pool even with a fan-out guard, and only 12 of 11,187 terms exceeded the cap, so no tuning would have helped. The factorized right-to-left form runs both in ~2 min. |
| 2026-08-10 | **Feature-handling standard made mandatory** (§6.2): all numeric inputs standard-rescaled + mean-imputed. The platform's per-deploy guesses are inconsistent, so audit after every deploy. |
| 2026-08-10 | **Priorities inverted by results**: the priority-1 binary flag scored exactly 0.5000 and was rejected; the priority-2 functional metapaths were the biggest win. **Graded relational features beat binary gene-level flags.** |
| 2026-08-11 | **Druggability annotation added** (§8.5) — curated source primary, in-graph annotation as gap-fill, 92.2% coverage. Implemented as **per-gene attribute tables**: no nodes, no edges, indices untouched. **Annotates rather than re-ranks.** |
| 2026-08-11 | **Candidate list extended to top-50.** Known-target density falls monotonically 65% → 32.5%, evidencing calibration across the range. Repurposing candidates 2 → **15**. **Recommended demo diseases: breast cancer and obesity disorder.** |
| 2026-08-11 | **The candidate-pool restriction NOT expanded to the functional metapaths.** Measured: it would grow the pool to 15.8M at 1.04% positives and make coverage equalization *worse* on every original feature, pushing the filter toward the no-op state that produced leak 2. A stricter ≥2-of-3 variant is logged as a future experiment. |
| 2026-08-13 | **Flow restructured into zones by function**, one at a time with a row-count anchor at each step (§9). Three staleness traps found: every diagnostic had been computed on deleted models; two reconnected chains held old row counts; and the persona chain rebuilt once on stale scores before job history was checked. **Lesson: verify by job history, not row count.** |
| 2026-08-13 | **Drug-validated targets adopted as a mandatory second metric** (§7.4), not as a training objective. The two axes are decoupled (r = 0.097). Two preprocessing interventions and a tractability filter all failed to close the gap, while feature distributions show the signal *is* present — so the limit is the objective, not the features. |
| 2026-08-13 | **`prox_closest` dropped on measurement** (§4.2): a top SHAP driver whose removal costs nothing on either metric and which cannot separate drug-validated targets from background. Kept as a diagnostic column. |
| 2026-08-14 | **Training on the drug label tested and rejected — a documented negative result** (§7.5). Drug-target AUC 0.6836 → **0.9324**, association AUC 0.8228 → **0.6444**. The objectives are genuinely in tension, so the label is a **product decision, not an optimisation**. The model is kept in the flow precisely so nobody reruns the experiment and reads 0.9324 as a win. |
| 2026-08-14 | **The drug-target benchmark is itself a gene-popularity shortcut** — the finding that reframes §7.4. A no-graph lookup scores **0.9354**, *beating* the drug-trained model, which wins on only 44 of 112 diseases. Holding out genes leaves 57 positives over 19 diseases — too thin for a headline. **Correction:** the earlier framing of 0.6836 as "mediocre therapeutically" was wrong; it is the score of a model declining a shortcut. **Rule: before treating a metric as a target, check what the dumbest possible predictor scores on it.** |
| 2026-08-17 | **Migrated into a dedicated project** consuming the graph as 10 shared objects (PROJECT_CONTEXT §4.3). Branched rather than rebuilt, to preserve the three trained models, the persona chain and the diagnostic suite — which are the evidence base for every decision above. **Flow left unbuilt deliberately** until the hardcoded indices are re-derived (§10.1). |
| 2026-08-17 | **The two source recipes that feed no graph edge stay on this side** — the split-control disease vocabulary and the druggability annotation. Neither contributes nodes or edges, so neither belongs in the graph project. |
| 2026-08-17 | **All 14 hardcoded node indices remapped** to the rebuilt graph via `(node_id, node_type, node_source)` (§5.5, [index_remap.json](index_remap.json)). All resolved with identical node names; a sweep of all 67 recipes confirms zero stale values. **One key had to be *added*, not just remapped:** `respiratory system cancer` was in the validation split only incidentally, and its new index falls in train — the three lung personas would have silently returned **zero rows** rather than erroring, because the persona filter reads the validation split. **Rule: when a rule keys on an arbitrary integer, remapping the integer can change the rule's outcome — check the semantics, not just the substitution.** |
| 2026-08-17 | **Retrain tolerance widened to ±0.02** on macro per-disease AUC. The remap reshuffles 58.8% of diseases across splits, because the split rule is a modulo over an arbitrary integer. Measured effect **+0.0049**, within one standard error — so the reconstruction is still checkable, but not to 3 decimal places. Family integrity verified intact: zero split keys span more than one split role. |
| 2026-08-17 | **Rebuilt end to end on the shared graph — reconstruction CONFIRMED** (§10.1). Champion macro per-disease AUC **0.8197** vs 0.8228; every metric within **±0.01**, inside the tolerance set in advance. Ladder ordering preserved on both axes, and drug-target AUC became monotonic. The candidate pool total is **bit-identical** (6,754,128), so only the split allocation changed — and the champion held its accuracy on **18.8% less training data**. Three individual personas reproduced to within 0.002, which is stronger evidence than the macro average because nothing averages out. |
| 2026-08-17 | **Three rules were found to depend on integer ordering, not one** (§10.2). The split modulo was anticipated; **family assignment** (20 diseases changed anchor at identical hop depth) and **split-key elevation** (lung moved from `respiratory system cancer` to `thoracic cancer`, merging with breast) were not. All three break ties or select by lowest `node_index`. **Rule: an arbitrary tie-break is stable only as long as the thing it keys on is stable — when identifiers are reassigned, audit every rule that ranks, mods or minimises on them, not just the literals.** |
| 2026-08-17 | **Subtype-granularity diagnostic repointed from the split key to the disease family** (§3.4). The split-key elevation flip meant it had begun measuring larynx subtypes, and selecting on the new key would have compared breast lists to lung lists. The family is the stable expression of "lung cancer and its histological subtypes" and matches the recipe's own stated purpose. Finding survives: **55% of the top-50 identical on average** across 17 subtypes (reference 63%), with adenocarcinoma vs squamous cell at 47/50. |
| 2026-08-17 | **Per-family tables reclassified as a view of the validation sample, not a property of the graph** (§7.3). Family structure barely moved (99.7% identical assignment, largest family 75 in both builds), but the report is headed by a different family because the split reshuffled. Stated explicitly to stop a future reader reading structural change into it. |
| 2026-08-17 | **Druggability / target class REJECTED as a model input** (§10.3) — and not for the reason previously recorded. It is not merely orthogonal to the label, it is **inverted**: `Membrane receptor` has an association lift of **0.78** against a drug lift of 3.16, so the gain-maximising split is "membrane receptor → lower score". Adding it would reinforce the ligand-vs-receptor failure rather than fix it. Antibody-tractability's 0.98 association lift is literally no signal. |
| 2026-08-17 | **Shipped the presentational fix instead: top-N within druggability class.** Obesity's `membrane / cell-surface` column now leads with GHSR (#8), ADRB2 (#17), MCHR1 (#23) — two of them clinically-pursued anti-obesity targets — while the secreted ligands still lead globally. **A grouping change recovered most of what a model change was meant to buy, at no risk to the model.** |
| 2026-08-17 | **Safety/toxicity: the lift gate REFUTED the stated prediction and blocked the filter** (§10.3). Predicted drug targets would be depleted for loss-of-function intolerance; measured a **monotone gradient the other way** (1.37× → 0.62× across LOEUF bands). Constraint measures that a gene *matters*, which is a prerequisite for being drugged — and a drug is not a germline knockout. Separately, `has_safety_liability` is **4.62× enriched** for drug targets, because liabilities are discovered *by* drugging: attention artifact, not risk. **Neither free signal is a safety filter; used as one they would strip the shortlist of its best candidates.** Shipped the liability list as display-only annotation. |
| 2026-08-17 | **A real safety axis requires a direct measurement**, not the free proxies — essentiality and tissue-expression breadth. The gate result is the justification for that ingest cost. Also recorded: Open Targets' liability field is **positive-only** (943 targets, no "assessed and clean" state), so blank means unknown and anything filtering on blank filters on literature attention. |
| 2026-08-17 | **Deliverable changed from pre-cut to filterable** — the top-50 truncation replaced by a Window rank, so `target_candidates_2` is **63,020 ranked rows** *(reference generation; **76,465** after the 2026-08-17 rebuild)* carrying tractability, class and safety annotations. Progressive filtering on obesity reaches a 65-candidate shortlist from the scientist's own thresholds. The data layer for the dashboard is now complete. |
| 2026-08-17 | **Filter validated per persona** (§8.7; measured in `filtered_shortlist_eval`, since deleted and superseded by `filter_three_axes`). Clauses 1–3 (novel → tractable → not-secreted) give **1.42–1.71× enrichment at 100% recall** in every disease that has validated targets — they cut the pool ~40% and lose nothing. **Clause 4 (exclude known liability) destroys 15–70% of them** and pushes obesity to **0.54× — worse than not filtering.** So the recommended filter is **three clauses**, with liabilities display-only. Outcome measured on *novel* drug-validated targets to avoid conflating the deliberate removal of known targets with filter damage. |
| 2026-08-17 | **Clearest single piece of evidence for dropping clause 4:** obesity's **ADRB2** is itself a drug-validated obesity target at rank #17 *and* carries a liability flag — the clause would have deleted a confirmed hit. Also recorded: the liability `event` field mixes real adverse events, bare mechanism descriptors (`regulation of catalytic activity`) and risk-factor biology (lung cancer's nicotinic candidates are flagged `nicotine dependence`, the disease's own risk mechanism). **Present it; never present it as a safety verdict.** |
| 2026-08-17 | **Filtering improves the ranking's usefulness but cannot fix its head.** With the 3-clause filter, top-N precision improves in five of seven personas and never degrades — **diabetes mellitus reaches 5 approved targets in a filtered top-20** — yet most personas find nothing at top-20 on the strict bar. §7.4's objective limitation reappearing downstream. |
| 2026-08-17 | **DISCOVERY adopted as a third reported axis** (§8.1, §8.3, `novel_discovery_eval`). Ranking precision and therapeutic agreement say nothing about whether the model surfaces *unannotated* targets, which is the deliverable's actual claim. Measured by dropping known targets, re-ranking, and testing the novel head against the drug layer: **4–13× above chance on both ground truths**, 206 approved and 1,802 investigational targets recovered in top-200 novel. The strongest evidence in the document, and it was unmeasured for the whole project until now. |
| 2026-08-17 | **Both ground truths reported, never one.** `indication` (4,110 pairs, approved) is strict; `drug_investigated_for` (52,734, in-trial) is 13× larger, includes failed programmes, and is the fairer bar for target *identification* since it rewards surfacing target classes still in development. The choice reverses conclusions: NSCLC scores 0/33 approved and **11/379 at 6.8× investigational**. Metabolic diseases are genuinely better on approved (41×), oncology on investigational — a real property, not a coverage artifact. |
| 2026-08-17 | **CORRECTION — the persona criterion was inverted, and it changed a recommendation** (§8.8). "Share of the top 50 already known" was used as a novelty ceiling; it is a *precision* measure. Normalised by base rate, NSCLC's 96% is **19× enrichment (best in the panel)** and CKD's 2% is **2.9× (worst)**. The criterion rewarded the worst ranking, rejected the best, and briefly produced a recommendation to drop all three lung personas. **Replaced by ranking enrichment + measured discovery on either bar; 62 of 670 diseases now pass, and four of the seven current personas do.** |
| 2026-08-17 | **MAPK3 verified as the worked example of the deliverable working** (§8.3). Ranked #61 for NSCLC, novel#3, with nothing in the training label pointing at it — and it is a **trial-stage drug target** for that disease (ERK1, terminal kinase of the KRAS→MEK→ERK cascade). Three more of the top-15 novel candidates are also trial-stage. Confirmed from project data, not recollection. PTPN6 and SMARCA2 remain unvalidated on both bars. |
| 2026-08-17 | **The drug ground truth is an INFERRED pair, and it needed a sensitivity analysis** (§8.1, §8.3). Open Targets asserts *drug→disease* and *drug→target*, never *target→disease*; our truth set joins through the drug, so a 40-target drug approved for 13 indications manufactures **520 pairs**. Measured: **82.2% of triples come from multi-target drugs, 66.3% from drugs multi on both axes, only 8.0% survives a single-target restriction.** The limitation is real and is not eliminated by anything below. |
| 2026-08-17 | **First reading — WRONG, and withdrawn the same day.** Restricting to single-target drugs dropped lift@10 from 11.40 to **0.00**, which I read as "the head-of-list claim is an artifact". It is not: that subset expects **0.20 hits at chance**, so an observed zero cannot distinguish absence of signal from absence of power. **Lesson: before reading a zero as a refutation, compute what chance alone would have produced.** A sparse high-precision subset can be too small to test the very thing it was built to test. |
| 2026-08-18 | **Second reading — settled, using a curated label.** Extracted Open Targets' **`known_drug`** datatype (`extract_ot_known_drug` → `compute_known_drug_truth`, 107,593 pairs, 67,748 resolving onto the graph). It asserts the target–disease pair directly, and its score is a clean phase proxy: **0% of pairs below 0.6 are approved, 74.9% above 0.8.** At ≥0.8 it keeps 114 diseases and 1,173 novel positives — adequately powered where the single-target subset was not. **Result: lift@10 = 17.65×, ABOVE the original 11.40×.** Across every adequately-powered variant head-of-list lift is **6.9–17.7×**, and deep-list lift converges to **2.3–4.8×** across all seven. The discovery finding stands; the robust number to quote is the deep-list one. |
| 2026-08-18 | **Validation overhaul COMPLETE — the filter re-evaluated on all three axes** (§8.7, `compute_filter_three_axes`). Two findings. (a) **The tractability axis cannot score this filter:** P(demonstrated \| assessed) = 0.1253 against P(demonstrated \| not assessed) = 0.0007, a **177× ratio** — clause 2 is effectively a superset of the outcome, so its 91% recall there is definitional. Reported in the appendix, never quoted. (b) **On the therapeutic axis the filter's conclusion is robust to the label problem:** the curated `known_drug ≥ 0.8` gives **1.60× lift at 99.5% recall**, statistically identical to the inflated join's 1.61×/100%. Expected, since the filter is judged on recall over the retained set rather than on the head of a ranking. **Clause 4's damage also reproduces on the curated label** (99.5% → 72.6%), so its rejection no longer rests on inflated evidence. |
| 2026-08-18 | **CORRECTION — the metabolic/oncology split is not a class property** (§8.2, `compute_maturity_confound`). The suspected confound was exonerated: Spearman(maturity, axis-preference) = **+0.110**. But the check exposed sample size instead — of 60 diseases measurable on both labels only **4 are metabolic, and only 2 show the pattern** (diabetes mellitus 41.59×, obesity 41.21×; type 2 diabetes 0.00×, diabetic neuropathy 0.00×). The oncology direction holds 13-of-20, and the 36-disease majority shows no preference. **Claim narrowed from a class property to two named diseases.** |
| 2026-08-18 | **A recurring error pattern in my own analysis, named so it stops repeating: over-generalising from a small favourable subset.** Three instances this week — the persona criterion inverted on one metric (§8.8), the ligand-vs-receptor failure generalised from one pathway (§8.5), the metabolic/oncology split generalised from two diseases (§8.2). **Mitigation now standing practice: state n, state what chance alone would produce, and stratify before calling anything a property.** |
| 2026-08-18 | **TRACTABILITY adopted as a third evaluation axis, and it is now the most robust positive claim in the document** (§8.4, `compute_tractability_axis`). It is the only label with **no inflation**: `drug_protein` asserts directly that a molecule engages a gene — 1,109 of 20,861 genes, no join. Because demonstrated tractability rises ~6× across degree quintiles and the model favours hubs, every lift is reported against a **degree-matched null**. Result on novel candidates: **2.38–3.06× degree-matched**, and the degree-matched lift is *higher* than the naive one from rank 20 down — controlling for hub-ness strengthens the result rather than explaining it. Unlike the discovery lift, this survives its own confound control. **Amended 2026-08-19: the rank-10 cutoff is the exception, and the original unconditional claim came from an estimator mismatch — see §8.4.** |
| 2026-08-18 | **CORRECTION — the ligand-vs-receptor failure does NOT generalise, and I had been repeating that it did** (§8.5). Prediction stated in advance: the head should show a tractability *deficit* because the model over-ranks secreted ligands. **Refuted.** Across 668 diseases secreted proteins are on average **under**-represented at the top-50 (mean −0.93 pp, median −3.78 pp; over-represented in only 185 of 668). **Obesity — the very disease the case study is drawn from — shows −0.16 pp excess and 3.53× tractability enrichment, second best in the panel.** Where secreted over-representation does occur it tracks structural and inflammatory diseases (collagen, cytokines) whose real biology *is* extracellular, so ranking them highly is arguably correct; their low tractability lift is a property of the disease, not a ranking error. §8.9's mechanism stands; its scope was overstated by generalising from one pathway. |
| 2026-08-18 | **`known_drug` is a strict SUPERSET of our approved join** — all 4,110 join pairs appear in it — so OT builds from the same drug→target→indication chains and does **not** independently de-confound multi-target attribution. **The score threshold, not the change of source, is what does the work.** Adopted `known_drug ≥ 0.8` as the standard therapeutic evaluation label. Legitimate as an *evaluation* label though it was correctly rejected as a *feature* in 2026-08-05 (circular for training). |
| 2026-08-17 | **Persona panel: keep one lung term, retire type 2 diabetes, drop CKD** (§8.8). T2D passes one of five criteria (4.3× ranking, 0.256 drug AUC, no discovery on either bar) while its **parent `diabetes mellitus` is the best approved-target discoverer of all 670 validation diseases** (41.6× lift, 8 found at top-50) — added to the panel. CKD is **below chance** on discovery. The three lung terms all pass but share ~63% of their lists, so keep NSCLC only. |
| 2026-08-17 | **Candidate-decoration tail collapsed 5 recipes → 2** (§9.2), zone 18 items → 12. The chain was alternating joins and prepares doing nothing but left-joining lookups and then selecting, renaming and ordering columns — all of which a join recipe does itself. **Verified as a pure refactor:** same 63,020 rows *(the count at the time; 76,465 rebuilt)*, same key set, zero of 59 columns differing in value; only `disease_name`'s position moved, because DSS emits each input's columns as a block. |
| 2026-08-17 | **Recorded three join mechanics that are not discoverable from the payload** (DSS_CHEATSHEET): renames work via input `computedColumns`, **not** `rename` in `selectedColumns` (which round-trips then is ignored); dropping columns needs the per-input `MANUAL` list, since top-level `selectedColumns` sets order only; and the same dataset cannot be joined twice — accepted by the API, rejected at validation. The last one is the sole reason this is 2 recipes rather than 1. |
| 2026-08-17 | **Correction:** an earlier revision claimed the genetic-constraint columns had been kept off the shortlist. They had not — automatic column selection carried all five through. They are harmless as reference values but must **not** be surfaced as a dashboard filter, since that is precisely the filter the gate ruled out. |
| 2026-08-17 | **Two decisions reached by measurement rather than training**, at a cost of three recipes instead of three model runs. That is the second and third time the lift-gate pattern has prevented shipping a change that would have degraded the therapeutic axis. **Keep the gate as standing practice: state a falsifiable prediction, measure both labels, and be willing to be wrong** — here the prediction was refuted and that was the useful outcome. |
| 2026-08-18 | **Flow restructured to four validation zones, numerically prefixed** (§9, §9.1). The 40-item `Diagnostics (optimisation)` zone was deleted and its contents split by the *question each artifact answers*: `40` ranking quality, `41` the three axes, `42` leakage & granularity, `43` disease families. **The prefixes are functional, not cosmetic** — DSS sorts zones alphabetically, so the unprefixed flow put `Results` before `Features`. Also renamed `00 Shared` → `00 Imported … (synced)`, which is what it now holds: 12 foreign refs + folder, 11 Sync recipes, 9 local copies. 32 items moved, 0 failures; 178 items across 14 zones, `flow check` clean, no dangling inputs. |
| 2026-08-18 | **The `m7-drug-label` experiment was DELETED rather than rebuilt** — model, 3 splits, 6 evaluation datasets, 8 recipes, 2 orphaned analyses. It had never been rebuilt on the shared graph, so it was an unreproducible chain occupying a fifth of the diagnostics zone. **Accepted cost, recorded deliberately: §7.5's numbers now live only in this document** (0.9324 drug AUC / 0.6444 association, 439 of 1,507 hits@50, the **0.9354 lookup-table baseline that beats the model**, 57 positives over 19 diseases on gene-holdout, 196 strict positives over 18 diseases). Recipes recoverable at `97de713:dss_recipes/`. **The lookup-table baseline is the single most reusable finding in the document and it now has no artifact — that is the reason this entry is verbose.** |
| 2026-08-18 | **Zone naming rule adopted: a zone is named for the question it answers, not the tool it uses.** `Diagnostics (optimisation)` was wrong on both counts — none of that work was optimisation, and calling the evidence base "diagnostics" is what let it grow to 40 undifferentiated items. Applies to the presentation too: zones `40`–`43` are the evidence, `50`–`60` are the demo. |
| 2026-08-19 | **The demo is an objection ladder, and the flow zones now say so** (§9, §9.1). Zone *names* unchanged; every zone description in DSS now leads with the demo question it answers (Q1–Q6, [DEMO_NARRATIVE.md](DEMO_NARRATIVE.md) §2), and the zones that are deliberately not demo material say so outright. A presenter gets the running order from the flow itself. |
| 2026-08-19 | **A pruning plan derived from the dashboard was rejected as circular, and it was dangerous.** The criterion "does this feed `dashboard_persona_trust`?" cut **46 of 62** validation items — deleting the degree-matched tractability control (the answer to the single most common objection), the entire leakage audit, and the per-family generalisation evidence. The dashboard does not exist yet, so the criterion was derived from an artifact that would in turn have been derived from the survivors. **Replaced with: does a scientist ask this out loud in the room?** Same exercise, **16 items** instead of 46. |
| 2026-08-19 | **CORRECTION to §8.4 — the degree-matched claim rested on an estimator mismatch.** The table put a **pooled** dm lift (3.06×) beside a **macro** naive lift (2.97×) in the same row, manufacturing the conclusion that hub-correction strengthens the result *unconditionally*. Recomputed consistently, both estimators agree that it strengthens from rank 20 down and **weakens at rank 10** (pooled 3.06 vs 3.31; macro 2.86 vs 2.97). The quotable range is unaffected. **Found by re-verifying every headline number against live data before writing a customer-facing document — one of six checks failed, which is the argument for doing it.** Fourth instance of the over-claiming pattern named in the 2026-08-18 entry; the mitigation now extends to *state which estimator*. |
| 2026-08-19 | **Snapshot-before-delete adopted as standing practice.** Every artifact leaving the flow is first frozen to `docs/appendix/*.csv` with a manifest recording the graph generation, row counts and the live inputs it is re-derivable from. Direct response to the m7 deletion one day earlier, which left the 0.9354 lookup-table baseline with no artifact at all. Cost: ~4.3 MB in git. |
| 2026-08-19 | **Breast cancer and its molecular subtypes added to the persona panel** (§8.13). Six terms joined the persona filter; `target_candidates_2` went 76,465 rows over 7 diseases → **129,253 over 13**. All twelve breast terms were already in the validation split under family 49721, so nothing needed re-splitting. New artifacts: `breast_panel_metrics`/`breast_panel_overlap` (zone 42, since subtype separability is a granularity question) and `breast_shortlist` (zone 50). |
| 2026-08-19 | **§3.4 NARROWED — the model resolves molecular subtype, just not morphological subtype.** The lung finding (adeno vs squamous share 47/50) had been generalised to "subtype". HER2-positive vs triple-negative share **2 of 50** novel candidates — the cleanest separation in the project. The property that decides it is **how the subtype is defined**: molecular markers carry their own curated gene associations, morphology inherits a shared annotation set. Since oncology stratifies on molecular subtype, this moves a stated limitation into a strength. |
| 2026-08-19 | **The parent-term intuition is backwards for breast.** §3.3 held that coarser terms are the safer choice. In the breast panel the generic `breast cancer` term has the **worst AUC in the panel (0.69)**, beaten by every one of its own subtypes, while HER2-positive reaches 0.93. PROJECT_CONTEXT §3 had recommended the generic term on no measurement; corrected to HER2-positive. |
| 2026-08-19 | **A "power" verdict was replaced with an exact test, because the first version was wrong in the dangerous direction.** The draft labelled any arm with expected-hits < 1 "UNPOWERED", which would have discarded HER2-positive's **46 hits against 2.44 expected** — overwhelming regardless of how small the expectation is. Replaced with an exact Poisson upper tail plus a separate fragility flag for numerators under 3, and Hanley–McNeil intervals on AUC. Triple-negative's interval is **0.81–1.05**: crossing 1.0 is the approximation failing at 8 positives, and reporting that is the point. |
| 2026-08-19 | **Four defects found in the triple-negative list before any clinician saw it** (§8.13): ESR1 at rank 14 in a disease defined as ER-negative; PARP1 at 331 while its substrate pathway holds the top 20; BRCA1 at 252 as a *known* association while BRCA2 sits at 5; and TROP2/PD-L1 absent from the candidate pool despite both having approved drugs in the disease. **Recorded as the reason to arrive at an expert review with your own defect list** — it is what makes the arms that do survive credible. |
| 2026-08-19 | **Expert review adopted as a validation axis where labels cannot reach.** Two breast arms cannot be scored against our own labels (triple-negative has 8 known associations; luminal A has 101 in a pool of 8,157). `breast_shortlist` is therefore a **form, not a report** — known-target anchor block first, then novel candidates, then four blank clinician columns — so the output is a scoreable dataset (expert agreement rate per arm) rather than an anecdote. Stop rule: if the surgeon rejects an arm's anchor block, the novel block is not worth their time. |
| 2026-08-19 | **`dwpc_GCD` identified as the DRUG route, and it selects the evaluation population on the outcome** (§5.2.1, `compute_pool_reachability`). **100.0%** of approved-join pairs in the pool carry a GCD route — an identity, so C is Compound. GCD-only pairs are **0.153%** of the pool but **25.4%** of approved positives: **91.8× enrichment**. No feature leak (`role=REJECT`), but those pairs have no GGD/GPGD route by construction, so the model is scored on pairs whose route features are absent — mean `proba_1` **0.265** vs **0.540**. **Drug-target AUC rises 0.6911 → 0.7337 when they are excluded** (+0.072 on the 69 affected diseases), so part of §7.4's "objectives in tension" is an artifact of pool construction. The fix is a one-line GREL edit costing 0.153% of the pool. |
| 2026-08-19 | **CORRECTION — I over-promoted the reachability problem to "top modelling priority" on a single disease** (§10.5). Measured: the pool holds **98.5%** of curated target–disease pairs, so the ceiling costs 1.5%. Three supporting sub-claims also failed: it is **not** a sparse-disease effect (Spearman **+0.081**), family-pool borrowing rescues **2 of 34**, and `CD274`/`PDCD1` are reachable for 53%/62% of diseases rather than being structurally excluded. **Sixth instance of the named over-generalising pattern, and the first where I promoted a priority rather than a finding** — the mitigation now has to fire before a recommendation, not just before a claim. |
| 2026-08-19 | **REFUTED — the "graph under-represents surface biology" hypothesis.** Stated in advance and tested on all 20,861 genes via reachability breadth. Antibody-tractable genes reach **more** diseases than non-antibody ones (median 23.3% vs 15.0%), `Secreted protein` (65.3%) and `Membrane receptor` (55.4%) sit near the **top**, and the narrowest classes are `Transporter` (18.5%), `Ion channel` (34.5%) and `Enzyme` (38.2%). The n=34 unreachable-target sample had pointed the opposite way. **A percentage on 34 rows is an anecdote; the same question on 20,861 reversed the sign.** |
| 2026-08-19 | **What the reachability work did establish, net of the corrections:** **18.8% of genes (3,919 of 20,861) are reachable for no disease at all**; 94.1% of unreachable curated pairs involve genes reachable for *other* diseases, so the limit is the disease's known-gene set rather than graph coverage; **181 of 207 diseases are at 100% coverage** and only 2 below 50%, which makes a per-disease coverage warning cheap to ship and honest; and `TACSTD2` at **1.04%** breadth is a real, hard case worth naming. |
| 2026-08-19 | **CORRECTION to §5.2.1's own recommendation, within the hour.** "Drop `dwpc_GCD` from the pool filter" was costed on pool rows (0.153%) and called close to free. Checked the evaluation side: **22 of 206 diseases lose every curated therapeutic positive** and 77 lose some, because the GCD-only pairs *are* those positives. **Superseded by a strictly better fix — exclude GCD-only pairs from the drug-based denominators and report both numbers.** Same bias removal, no disease lost, no re-fit. Lesson: a filter change has two cost surfaces, population and evaluation, and I costed only the first. |
| 2026-08-19 | **Dropping GCD would NOT have helped the triple-negative/TACSTD2 case, and the two findings were never connected** — I made them look linked by narrating them together. The pool filter is a **union**, so removing a term can only shrink it; TACSTD2 for triple-negative has **no route at all** (GGD, GPGD, GCD all false), so the change is a no-op for it. Triple-negative's one reachable positive (TOP1) is GGD-supported and survives; its pool would shrink 2,563 → 2,463 with negligible effect on the head of the list. |
| 2026-08-19 | **No route-set expansion reaches TACSTD2 either — the constraint is the graph.** All five metapaths fail for that pair, including GBGD (12.1M rows, 997 TACSTD2 pairs, 7,456 triple-negative pairs, empty intersection). Root cause measured: **84 edges total, PPI degree 10 at the 25.7th percentile**, predominantly annotation edges, and **zero shared edges with any of the disease's 8 known genes**. Two compounding sparsities. **This reclassifies the flagship reachability case from a modelling problem to a graph-ingestion problem**, owned by `DEMO_KG_LS`. |

## References

> Per-reference summaries, the feature→reference map, and provenance caveats are in
> **[RESEARCH_NOTE.md](RESEARCH_NOTE.md)** (unvalidated corpus — verify before client-facing use).

- Locus-to-Gene (the pattern this reproduces) — Mountjoy et al., *Nat Genet* 2021
- Target prioritisation reference implementation — https://platform-docs.opentargets.org/web-interface/target-prioritisation
- Network proximity — Guney, Menche, Vidal, Barabási, *Nat Commun* 2016
- Disease modules / incomplete interactome — Menche et al., *Science* 2015
- Degree-weighted path counts — Himmelstein et al., *eLife* 2017
- Path-explanation interpretability study — Huang et al., *Nat Med* 2024
- Genetic support and clinical success — Minikel et al., *Nature* 2024
