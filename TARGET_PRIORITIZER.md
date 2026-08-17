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

`target_candidates_2` — **every scored candidate per persona disease, ranked** (63,020 rows across
6 diseases), so the scientist filters rather than receiving a pre-cut list (§10.3):

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
  matter a great deal here (§8.3).
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

### 3.4 The model cannot resolve histological subtype, and the data is why

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
| `dwpc_GCD` | 99.8% null, and **circular** for target identification: "an approved drug already targets this gene for this disease" nearly restates the label. Retained as a **post-hoc evidence annotation** (§8.3). |
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
> terms in the pool restriction. Pruning it as "unused" silently changes the 21.3M → 6.75M reduction.

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
precisely backwards and is the mechanism behind the ligand-vs-receptor failure in §8.3. **Add
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

> **⚠ This experiment was NOT rebuilt** — its `psplit_*_drug` inputs were not regenerated, so the
> whole section is reference-graph numbers compared against each other. That is internally
> consistent, which is what matters here: the finding is about the *benchmark's structure*, which the
> graph does not change. Rebuilding it is logged in §10.3 as low priority.

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

### 8.1 Per-persona performance

Rebuilt, champion `m3-f12`. Macro over all 670 validation diseases is 0.8197.

| Persona disease | positives | **AUC** | *(reference)* | drug-target AUC | validated targets |
|---|--:|--:|--:|--:|--:|
| lung adenocarcinoma | 705 | 0.9339 | — | — | — |
| non-small cell lung carcinoma | 621 | 0.9313 | — | 0.6757 | 54 |
| breast carcinoma | 864 | 0.8579 | *0.8572* | 0.5986 | 25 |
| lung cancer | 53 | 0.7717 | — | 0.8267 | 6 |
| morbid obesity | 41 | 0.7550 | *0.7222* | — | — |
| chronic kidney disease | 35 | 0.7119 | — | 0.7019 | 11 |
| obesity disorder | 762 | 0.7094 | *0.7087* | **0.8334** | 34 |
| breast cancer | 138 | 0.6929 | *0.6913* | 0.6669 | 47 |
| **type 2 diabetes mellitus** | 1,081 | **0.6341** | *0.633* | **0.2556** | 68 |

**The four personas that exist in both builds reproduce to within 0.033, and three of them to within
0.002.** Breast carcinoma 0.8572 → 0.8579, obesity disorder 0.7087 → 0.7094, breast cancer
0.6913 → 0.6929. That stability across a different graph and a different split is stronger evidence
for the reconstruction than the macro average, because these are individual diseases with no
averaging to hide movement.

**Most personas sit at or below the macro average** — they are **not** cherry-picked easy diseases,
which makes for a more honest demo. The two lung subtypes are the exception at 0.93, and they are
also the two with almost no novelty left (49 and 48 of 50 candidates already known), which is the
§3.3 granularity trade-off appearing again.

**Type 2 diabetes remains the weakest case on both axes and is still the flagship** — per-disease
0.634 and drug-target **0.256** with 1 of 68 validated targets in the top 50. Obesity disorder is the
strongest therapeutically (0.833). This is unchanged from the reference and remains the strongest
argument for re-picking the persona panel (§10.3).

### 8.2 Candidate output — biological coherence

| Persona | known in top 20 | Notable novel calls |
|---|--:|---|
| **breast cancer** | 11 / 20 | **BLM** (#2), **RAD50** (#4), **MLH1** (#6), **MRE11** (#10) |
| breast carcinoma | 19 / 20 | — |
| obesity disorder | 17 / 20 | — |
| **morbid obesity** | 0 / 20 | **GNAS, GCG, GIP, IAPP, RAMP1/2** |

- **Breast cancer** surfaces BLM (Bloom helicase), RAD50 + MRE11 (the MRN complex, alongside
  already-known NBN), and MLH1 (mismatch repair) — all homologous-recombination / DNA-damage-repair
  genes, the right neighbourhood for BRCA-adjacent susceptibility.
- **Morbid obesity** surfaces the incretin/metabolic axis — glucagon, GIP, amylin, RAMP1/2 — the
  pathway GLP-1 agonists act on.

**Ranking quality holds monotonically across the whole top-50**, pooled over the six personas:

| Rank band | 1–10 | 11–20 | 21–30 | 31–40 | 41–50 |
|---|--:|--:|--:|--:|--:|
| known-target density | **60.0%** | 55.0% | 46.7% | 46.7% | **43.3%** |
| mean score | 0.966 | 0.952 | 0.937 | 0.926 | 0.916 |
| *reference* | *65.0%* | *60.0%* | *40.0%* | *37.5%* | *32.5%* |

Density falls with rank and mean score tracks it — out-of-sample evidence that the *ordering* is
meaningful across the whole range, not just at the head. The tail is denser than in the reference
because the persona mix now includes two lung subtypes that are 48–49/50 already-known; the curve is
a property of the sample, not only of the model.

**The repurposing filter — novel candidates that already have chemical matter — returns 32 at top-50**
(reference: 15), including ERBB3, ERBB4, FGFR1/2/4, DDR2, ADRB2, GRIN2A, GHSR and a cholinergic
receptor cluster (CHRNA1/B1/B2/B4/D/E). At top-20 the reference returned only 2, so **the extended
rank range is where the actionable slice lives** — that conclusion strengthens on rebuild.

### 8.3 Case study — the limits of an interactome-based model

The canonical obesity receptor (the semaglutide target) is a known target for obesity disorder. The
model scored it **0.8531 → rank 1,472 of 13,126 (top 11.2%)** and predicted **negative** — one of 590
false negatives.

**Why the rank was low — neighbour overlap, not degree:**

| Gene | interaction partners | shared with module | `dwpc_GGD` | probability | is_target |
|---|--:|--:|--:|--:|--:|
| glucagon (ligand) | 37 | **13** | 0.0205 | 0.980 | 0 |
| amylin (ligand) | **16** | **7** | 0.0180 | 0.978 | 0 |
| the receptor | **28** | **3** | 0.0039 | 0.853 | **1** |

The receptor has *more* partners than the amylin ligand yet scores far lower. The discriminator is
**overlap with the module**. Mechanistically this is the **membrane-protein assay bias**:
transmembrane receptors resist the assay technologies that built the interactome, so their mapped
neighbourhoods are sparse. **The model penalizes the receptor for an assay artifact, not biology** —
a live instance of the incomplete-interactome caveat (§2).

**The unresolved failure: ligands outrank their own receptors.** Every secreted peptide ligand is
predicted positive despite *not* being a known target; every membrane receptor that *is* a known
target is predicted negative. **The model finds the right pathway but not the right druggable node.**
The ablation improved receptors (rank 1,472 → 535, and a paralog 1,489 → 634) without fixing the
discrimination — it needs **target-class/druggability** signal (§4.3), not more network similarity.

**The evidence the model is not allowed to use.** The drug-metapath feature traces to exactly one
compound — an oral agonist for that receptor. The feature is rejected as circular (§4.2), which is
defensible, but it means the most decisive evidence is computed and discarded. **Use it as a post-hoc
annotation on the ranked list** ("this candidate already has drug-level validation"), not as a
training feature.

### 8.4 On-graph explanation

Anchor demo: the breast-cancer top-10 contains **RAD50 (#4), NBN (#8), MRE11 (#10)** — all three
members of the **MRN double-strand-break repair complex**, with RAD50 and MRE11 *novel*. **The
prediction explains itself on the canvas.**

Query conventions: undirected traversal; **relationship variables must be bound AND returned** or the
canvas shows floating nodes; the graph engine's label for genes is `protein`. Indices are
snapshot-specific — re-derive after any rebuild.

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

### 8.5 Druggability annotation on the ranked list

Built to make the §8.3 ligand-vs-receptor failure *visible* to a reader without touching the model.
Two independent sources combined by precedence into one per-gene table (20,861 rows — exactly one per
gene, **92.2% classified**):

| Source | Signal | Coverage | Verdict |
|---|---|--:|---|
| Subcellular location (curated + atlas) | membrane / secreted flags | **18,873 (90%)** | primary workhorse |
| Target class (chemical-biology family) | `Membrane receptor`, `Enzyme`, `Ion channel`… | 5,874 (28%) | authoritative but sparse; **human-readable** |
| Tractability buckets | small-molecule / antibody, has-approved-drug | 6,131 (29%) | modality routing |
| Cellular-component annotation *(already in graph)* | membrane / secreted flags | 7,580 (36%) | fallback; fills 343 genes the primary source misses entirely |

**The two independent sources agree 88.2% on membrane, 95.6% on secreted.** Where they disagree the
curated source is generally right — the in-graph annotation flags a DNA-repair enzyme as `membrane`
on a real-but-misleading annotation, while the curated source correctly classes it `Enzyme`.

Both are **per-gene attribute tables joined on the gene index** — no nodes, no edges, so the graph
and its indices are untouched. **Never model these as edges.** This is the pattern for every future
annotation layer including the deferred safety work: an attribute table costs one join, whereas an
edge forces a graph rebuild, a re-index and a full feature recomputation.

Filters that work on the output:

| Goal | Filter |
|---|---|
| core discovery | not a known target AND not secreted AND (small-molecule OR antibody tractable) |
| small-molecule programme | class in (Enzyme, Ion channel, Transporter, cell-surface) AND small-molecule tractable |
| antibody / biologic | class in (cell-surface, membrane + secreted) AND antibody tractable |
| **repurposing** | not a known target AND has an approved drug |

At top-50 the repurposing filter returns **32 candidates** (§8.2) — up from 15 in the reference, on a
different persona mix. In the reference it surfaced the canonical HER2-targeted breast-cancer target
at rank 46, flagged novel because that disease term's association edges omit it: a clean illustration
that "novel" here means *novel to this disease's annotations*, not novel to medicine. **At top-20 it
returned only 2, so the extended rank range is where the actionable slice lives.**

> **This annotates, it does not re-rank.** The model never sees these columns, so secreted ligands
> still outrank receptors *globally*. The fix is presentational — top-N **within** each class, which
> puts the druggable receptors at the head of their own column (§10.3). And has-approved-drug is
> **gene-level across all indications**: it means "chemical matter exists", not "this drug works in
> this disease".

## 9. Flow zones

Eleven zones, downstream of the shared graph. 149 items.

| Zone | Items | Contents |
|---|--:|---|
| `00 Shared from DEMO_KG_LS` | 10 | the cross-project interface — 9 datasets + the materialized graph folder (PROJECT_CONTEXT §4.3). **Read-only; produced by the other project** |
| `Features - graph traversal (Cypher)` | 20 | 9 graph-query recipes + the centrality plugin, reading the materialized graph |
| `Features - matrix (Python)` | 11 | the functional metapaths, proximity, random-walk, degree-corrected overlap, provenance depth |
| `Features - assembly` | 4 | pair spine → 18-input join → the feature table (21,308,578 rows) |
| `Annotations & split key` | 14 | family id from the anchor rollup; gene localization → druggability; **gene safety** (§10.3); the source recipes this project owns |
| `Modeling table & split` | 8 | join family id → candidate-pool restriction → split by family key |
| `Model training` | 6 | the three ladder models and their saved artifacts |
| `Results - model performance` | 18 | 3 scoring recipes, the per-disease AUC chain, the ablation ladder |
| `Results - disease families` | 14 | per-family AUC and top genes per family |
| `Results - target candidates` | 12 | persona filter → SHAP scoring → **`rank_per_disease`** (Window) → **2 decoration joins** → `target_candidates_2`, 63,020 filterable rows |
| `Diagnostics (optimisation)` | 34 | reachability, tractability lift, **safety lift**, **filtered-shortlist evaluation**, staged benchmark, granularity check, split audit, hierarchy annotation, per-split-key AUC, and the whole drug-label negative result |

**Recipes are named for actions, not outputs.** An earlier pass renamed them after finding recipes
called things like `compute_graph_features_sampled_2` (now `filter_has_path_evidence`) and
`compute_test` (which, despite the name, produces a production feature).

### 9.1 The candidate-decoration tail, collapsed 5 recipes → 2

The persona chain ends by attaching names and annotations to the ranked candidates. That had grown
into alternating joins and prepares — gene-name join, rename/drop, disease-name join, druggability
join, rename/drop/reorder — 5 recipes and 4 intermediate datasets. **All of it is left-joining a
lookup and then selecting, renaming and ordering columns, which a join recipe can do by itself.**

| | Recipe | Inputs | Does |
|---|---|--:|---|
| 1 | `decorate_target_candidates` | 4 | ⋈ node names on `gene_index`, ⋈ druggability, ⋈ safety → `top_annotated` |
| 2 | `join_disease_name` | 2 | ⋈ node names on `disease_index`, plus the final column selection, renames and order → `target_candidates_2` |

Zone item count 18 → **12**; the tail itself 9 items → 3.

**Verified as a pure refactor**: 63,020 rows, identical key set, and **zero of the 59 columns differ in
value**. One cosmetic change — `disease_name` now sits last rather than at position 49, because DSS
emits each input's columns as a block and the output order cannot interleave across inputs.

**Three mechanics decide whether this collapse is possible at all** (all three in DSS_CHEATSHEET,
because none is discoverable from the payload):

- **A join renames via `computedColumns` on the input, not via `rename` in `selectedColumns`.** The
  latter round-trips in the payload and is then ignored at execution. So `gene_name`, `disease_name`,
  `score` and `rank_in_disease` are GREL passthrough computed columns.
- **Dropping columns requires the per-input `MANUAL` selection.** The top-level `selectedColumns` sets
  output *order* but restricts nothing — relying on it alone silently leaked 9 columns back in.
- **The same lookup table cannot be joined twice in one recipe.** Listing `graph_nodes` twice is
  accepted and round-trips cleanly, then fails validation with *"Dataset appears several times in
  inputs"*. That is the only reason this is two recipes rather than one.

**Heavy graph math lives in code, not plugin recipes** — the metapaths, proximity, random-walk and
degree-corrected overlap. The query-recipe path repeatedly failed at this scale (§8.4); the
interactive explorer works.

**Everything in the zones above was rebuilt on 2026-08-17** against the shared graph, so all reported
numbers now come from one generation — the staleness that previously affected three diagnostics is
resolved. Two exceptions, both flagged where they appear: the drug-label chain (§7.5) and the hub-bias
meter (§7.2). `target_reachability` predates the rebuild but is unaffected, because it compares
*feature* distributions rather than model scores.

> **One infrastructure note.** The final diagnostics batch failed on its first run with a container
> orchestration error (pod creation, `kubectl` exit 1) — nothing to do with the data. A plain retry
> of the same targets succeeded. Worth recognising the signature, because a scheduler failure and a
> recipe failure look similar in the job list and only one of them is worth debugging.

## 10. The migration and its acceptance test

### 10.1 Result — reconstruction confirmed

The flow was rebuilt end to end on the shared graph on 2026-08-17: features → split → retrain the
three-rung ladder → score → validate → persona candidates. **The tolerance was set in advance at
±0.02 macro per-disease AUC; every metric came in inside ±0.01.**

| Metric | Reference | Rebuilt | Δ |
|---|--:|--:|--:|
| **macro per-disease AUC** | 0.8228 *(n=588)* | **0.8197** *(n=670)* | **−0.0031** |
| per-disease, positives ≥ 10 | 0.8278 *(n=517)* | 0.8323 *(n=604)* | +0.0045 |
| per-split-key AUC | 0.8041 | 0.8007 *(443 keys)* | −0.0034 |
| pooled AUC | 0.8968 | 0.8915 | −0.0053 |
| per-family macro | 0.8060 *(484)* | 0.7976 *(505)* | −0.0084 |
| drug-target AUC | 0.6836 *(112)* | 0.6911 *(130)* | +0.0075 |
| validated targets in top 50 | 117 / 1,507 (7.8%) | 122 / 1,538 (7.9%) | +0.1 pp |

**Two independent sources of movement were separated in advance, and both behaved as predicted.**
Graph drift is 0.03% of edges, all functional-annotation — the axis to watch, because the two
functional metapaths produced most of the champion's gain (§6.4). The split reshuffle is much larger
— 58.8% of diseases changed split role — and was estimated at **+0.0049** by restricting the
reference's own per-disease AUCs to the diseases that stay in validation. The observed total move
(−0.0031) is smaller than that estimate, i.e. the two effects partly cancel.

**The candidate pool is bit-identical, which isolates the comparison.** Row counts:

| Split | Reference | Rebuilt | Share |
|---|--:|--:|--:|
| train | 2,693,788 | 2,187,862 | 39.9% → **32.4%** |
| validation | 3,499,126 | 3,958,921 | 51.8% → **58.6%** |
| test | 561,214 | 607,345 | 8.3% → **9.0%** |
| **total** | **6,754,128** | **6,754,128** | identical |

The totals match exactly, so the has-path-evidence restriction reproduces to the row and only the
*allocation* changed. Note the training set shrank by **18.8%** — the champion held its accuracy on
a fifth less training data.

**The metric cross-validation still holds.** The visual chain and the code recipe both give
**0.8197**, maximum absolute difference **1.9×10⁻⁴**, 31 of 670 diseases differing above 1e-6, and
positive counts identical throughout — the same agreement as on the reference (3.5×10⁻⁴, 33 of 588).

### 10.2 What the rebuild exposed — three index-dependent behaviours

The remap (§5.5) anticipated one. The rebuild found two more. **All three are the same root cause:
a rule that breaks ties or selects by lowest `node_index` behaves differently when the graph is
renumbered.** None is a defect — the tie was arbitrary either way — but each changes results.

1. **The split rule** (anticipated). A modulo over an arbitrary integer, so renumbering reshuffles
   58.8% of diseases across splits. Handled by forcing the persona split keys explicitly.
2. **Family assignment.** 6,801 of 6,821 diseases (99.7%) keep the same family; **20 changed anchor**,
   every one at *identical hop depth* — so the walk found a tie and broke it on the lowest index.
   Examples: brain cancer → malignant glioma, atherosclerosis → coronary artery disease, muscle
   cancer → sarcoma. Overall family sizes barely move (largest 75 in both builds; only `sarcoma`
   changed materially, 34 → 38).
3. **Split-key elevation — the consequential one.** The lung personas' split key moved from
   `respiratory system cancer` to `thoracic cancer`, because a disease with multiple parents picks
   among them by lowest index and renumbering flipped that choice. Counts: respiratory system cancer
   45 → 13 diseases, thoracic cancer 22 → 42. **Breast and lung now share one split key**, so they
   sit in the same leakage-control group — *more* conservative, not less, and both were already in
   validation, so nothing leaked. But it did break a diagnostic (§3.4) that selected on that key.

> **The transferable lesson:** an arbitrary tie-break is stable only as long as the thing it keys on
> is stable. Three separate rules here silently depended on integer ordering. When identifiers are
> reassigned, audit every rule that *ranks, mods, or minimises* on them — not just the literals.

### 10.3 Target prioritisation — the two decisions, settled on measurement

Both questions in this section were answered by measuring rather than by training, which is why they
cost three recipes instead of three model runs.

#### Druggability / target class as a model input — **rejected**

Not merely "no expected gain" — **actively harmful under this label.** The label is "an association
edge exists", and against it (§7.4) `Membrane receptor` scores an association lift of **0.78 —
depleted** while scoring **3.16×** on drug-validated targets. A loss-minimising tree therefore learns
**"membrane receptor → lower score"**, which is precisely the ligand-vs-receptor failure in §8.3,
except explicit and reinforced. Antibody-tractability is worse than useless: 0.98 association lift is
*no signal at all*, so the model either ignores it or finds the inverted use.

The label route out of this is closed on evidence, not principle — §7.5 tested it end to end.

**What was done instead — presentation, and it works.** With a rank column and a druggability class on
every candidate, showing **top-N within each class** surfaces the druggable node without the model
ever seeing the column. Obesity disorder, top 3 novel candidates per class:

| class | top novel candidates *(global rank)* |
|---|---|
| **`membrane / cell-surface`** | **GHSR (#8)**, **ADRB2 (#17)**, **MCHR1 (#23)** |
| `secreted` | IAPP (#5), GCG (#36), ADIPOQ (#40) |
| `Transcription factor` | SMAD3 (#16), STAT3 (#18), ARNT (#42) |
| `Enzyme` | JAK2 (#45), NTRK1 (#46), HIPK2 (#55) |

The secreted ligands still outrank globally — the model is unchanged — but the receptor column now
leads with the ghrelin receptor and MCHR1, both clinically-pursued anti-obesity targets. **A one-line
grouping change recovers most of what folding the feature into the model was supposed to buy.**

#### Safety / toxicity as a filter — **the gate refused it**

Both signals available for free (they are already inside a source we ingest, so this cost one
extraction recipe rather than a new dependency) were measured against both labels before being wired
into anything. **The prediction stated in advance was refuted.**

Predicted: drug-validated targets would be *depleted* for loss-of-function intolerance, because
inhibiting a gene whose loss humans do not tolerate should be toxic. Measured, over 130 diseases:

| LOEUF band (most → least constrained) | drug lift | assoc lift |
|---|--:|--:|
| < 0.35 *(intolerant)* | **1.37×** | 2.07× |
| 0.35 – 0.7 | 1.33× | 1.36× |
| 0.7 – 1.0 | 0.94× | 0.87× |
| 1.0 – 1.5 | 0.80× | 0.60× |
| > 1.5 *(tolerant)* | **0.62×** | 0.40× |

**Monotone, and pointing the opposite way to the prediction.** Constraint runs *with* druggability.
The reasoning was wrong in a way that is obvious in hindsight: constraint measures that a gene is
functionally consequential, which is a *prerequisite* for being worth drugging — and a drug is not a
germline knockout, it is partial, reversible and dose-controlled.

The liability column fails differently and worse: **`has_safety_liability` is 4.62× enriched for
drug-validated targets**, because liabilities are discovered *by* drugging a target. It marks
well-precedented targets, not risky ones — the same attention-artifact structure as the
gene-popularity shortcut in §7.5.

**So neither free signal is a safety filter.** Used as one, both would strip the shortlist of its best
candidates. What shipped instead:

- **`safety_events` as a displayed annotation.** "This target has a documented cardiac liability" is
  worth a scientist's attention even when it predicts nothing. 4,486 of 63,020 candidates carry one.
- **The constraint columns are on the shortlist, which was not the intent.** An earlier revision of
  this document claimed they had been excluded; they had not — automatic column selection carried
  `lof_oe`, `lof_oe_upper`, `lof_bin6`, `mis_oe` and `lof_intolerant` through. They are harmless as
  reference values but they are exactly the filter the gate ruled out, so **treat them as
  informational and do not expose them as a filter control in the dashboard.** Dropping them is a
  one-line change to `decorate_target_candidates`'s safety input selection if that is preferred.
- **A real safety axis still requires a direct measurement** — essentiality (does knocking this out
  kill cells) and tissue-expression breadth. The gate's result is now the argument for spending that
  effort rather than settling for the free proxies.

> **⚠ Absence of a liability is not evidence of safety.** Open Targets emits the field *only* for the
> 943 targets that have one and omits it otherwise — there is no "assessed and clean" state, so a
> blank means nobody looked. Anything that filters on blank is filtering on literature attention,
> which is the study bias the whole feature set exists to control.

#### The deliverable is now filterable, not pre-cut

`target_candidates_2` went from **300 pre-cut rows to 63,020 ranked ones** — the top-N truncation was
replaced by a Window rank, so every scored candidate keeps its position.

#### The filter, validated per persona against drug-validated targets

`filtered_shortlist_eval` tests whether the filter chain **concentrates real therapeutic targets** or
merely shrinks the list. Outcome measure: **novel drug-validated targets** — validated by an approved
indication for that disease *and* absent from the association layer. That is the population the
deliverable claims to find, and it is independent of the training label. 140 such pairs exist across
the 63,020 candidates.

**The confound this avoids:** the first clause removes association-known genes *by design*, so
scoring against all drug-validated targets would conflate "the filter is destructive" with "we
deliberately dropped the known ones".

**Result — the first three clauses are strictly beneficial. The fourth is destructive.**

| Stage | CKD | lung cancer | NSCLC | obesity | T2D |
|---|--:|--:|--:|--:|--:|
| novel-validated in scope | 11 | 4 | 33 | 30 | 62 |
| **lift after novel + tractable + not-secreted** | **1.42×** | **1.47×** | **1.68×** | **1.67×** | **1.71×** |
| recall at that point | **100%** | **100%** | **100%** | **100%** | **100%** |
| lift if "exclude known liability" is added | 1.19× | 1.25× | 1.55× | **0.54×** | 1.70× |
| recall if added | 72.7% | 75.0% | 84.8% | **30.0%** | 91.9% |

Clauses 1–3 cut the pool by ~40% and lose **nothing** — every novel-validated target survives, at
1.4–1.7× enrichment, in every disease that has any. **Clause 4 destroys 15–70% of them and pushes
obesity below baseline (0.54×, i.e. worse than not filtering).**

**So the recommended filter is three clauses, and known liabilities are display-only.** This is the
§10.3 gate result reappearing as a concrete cost: liabilities are 4.62× enriched for drug-validated
status because they are discovered *by* drugging a target, so excluding them excludes the best
candidates. The recipe deliberately still computes and prints clause 4 so the damage stays visible.

**The single clearest illustration:** obesity's **ADRB2** is *itself* a drug-validated target for
obesity, at rank #17 — and it carries a liability flag. Clause 4 would have deleted a confirmed hit.

**Top-N precision, plain ranking vs the 3-clause filter** (novel-validated found / N):

| Disease | top 20 | top 50 | top 200 |
|---|---|---|---|
| obesity disorder | 1 → **2** | 2 → **6** | 7 → **8** |
| non-small cell lung carcinoma | 0 → 0 | 0 → 0 | 0 → **2** |
| chronic kidney disease | 0 → 0 | 0 → 0 | 0 → **1** |
| type 2 diabetes mellitus | 0 → 0 | 0 → 0 | 0 → **1** |
| lung cancer / lung adenocarcinoma | 0 → 0 | 0 → 0 | 0 → 0 |

The filter helps four of six diseases and never hurts. Obesity triples at top-50. **But the absolute
yield stays low, and that is the honest headline:** at top-20 only obesity finds anything. Filtering
improves the *ordering's* usefulness; it cannot fix the fact that the model does not place
drug-validated targets at the very head of the list. That is the objective limitation of §7.4, and no
downstream filter addresses it.

**A caveat on the liability annotation itself.** Its `event` values mix three incompatible things:
genuine adverse events (`cardiac arrhythmia`, `neutropenia`), bare mechanism descriptors
(`regulation of catalytic activity`), and risk-factor biology — lung cancer's top nicotinic-receptor
candidates are flagged `nicotine dependence`, which is the *disease's own risk mechanism*, not a drug
toxicity. Present it, but do not present it as a safety verdict.

#### Biological coherence of the surviving lists

Each persona's survivors read correctly for its biology, which is the qualitative half of the
validation:

| Persona | Signature of the top 20 |
|---|---|
| **chronic kidney disease** | **12 of 20 are SLC solute carriers** (SLC13A2/A3, SLC22A3, SLC47A1, SLC7A2/A3/A6/A7, SLC3A1, SLC26A5, SLC2A6, SLC38A4) — the proximal-tubule transport machinery, and SLC22A3/SLC47A1 are actual renal drug-handling transporters. Plus DDR2 and FGFR2, both fibrosis-relevant with approved drugs. |
| **lung cancer** | **7 of 20 are CHRN nicotinic-receptor subunits** (CHRNA6/A7/A9, CHRNB1/B3, CHRND, CHRNE) — the 15q25 locus is the best-replicated lung-cancer GWAS signal. Alongside ERBB3/ERBB4, PIK3CB/CD, NRAS, HRAS, EP300, MSH2. |
| **lung adenocarcinoma / NSCLC** | JAK-STAT and chromatin: STAT1, STAT5A/B, SMARCA2, BRD7, HDAC5, plus MRE11 and TOPBP1 from DNA-damage response. Ranks start at #30–50 because the head of the list is known targets, removed by the novel clause. |
| **obesity disorder** | GHSR (#8, ghrelin receptor), ADRB2 (#17, validated), MCHR1 (#23) and GRM1 (#24) — a coherent neuroendocrine receptor cluster, with MCHR1 and GHSR both clinically pursued for obesity. |
| **type 2 diabetes mellitus** | β-cell and insulin-signalling biology: ADCY2/ADCY3, ITPR3, ATP2A2 (SERCA2 calcium handling), NOTCH1, RUNX1, CREBBP, PIK3CB. ADCY3 is an established obesity/T2D locus. |

### 10.4 Remaining after the rebuild

- **Re-derive the Cypher literals in §8.4.** These are *gene* indices for the demo queries, taken
  from the ranked output — now regenerable, but not yet done. Presentation-layer only; nothing
  depends on them.
- **Rebuild the drug-label chain** (`m7`, §7.5). Its `psplit_*_drug` inputs were not rebuilt, so the
  negative result still rests on reference-graph numbers. Low priority — the finding is about the
  benchmark's structure, which the graph does not change.
- **The hub-bias meter (§7.2) has no recipe** — it was computed ad hoc and remains on the retired
  generation. Worth materialising as a recipe if it is going to be quoted.
- **A direct safety measurement** — essentiality and tissue-expression breadth. Now the top feature
  priority, because §10.3 established that the free proxies cannot do this job.
- **The dashboard.** The data layer is ready: 63,020 ranked rows with tractability, class and safety
  annotations. What is missing is the UI with rank / class / safety controls.

### 10.5 Still open

- **⚠ The training lab cannot be retrained as-is.** Verified 2026-08-14: all 10 of its input features
  are still set to presence-flag handling with constant imputation, left over from the null-signal
  experiment — which is **degenerate** (§6.2). Reset to standard rescaling + mean imputation, or the
  next model silently inherits it.
- ~~Druggability / target class as a model input~~ — **SETTLED, rejected** (§10.3). Shipped as
  class-grouped presentation instead.
- ~~Safety / toxicity as a filter~~ — **the free signals were measured and rejected** (§10.3). The
  liability annotation shipped as display-only; the filterable table shipped. **Still open: a direct
  safety measurement** (essentiality, tissue-expression breadth), which needs a new source, and the
  dashboard on top of the now-ready data layer.
- **Embedding features** — the one family that can score *pathless* pairs, reaching past the
  candidate-pool boundary (§5.2).
- **Degree-matched negative sampling** — currently class weights only. A cheaper diagnostic first:
  evaluate the existing model on a degree-matched validation subset.
- **Permutation baseline** — a degree-preserving permuted-graph null would quantify signal beyond
  degree. Controls the degree confound, *not* the coverage leak.
- **Re-pick the persona panel on evidence.** The current six are not independent (§3.4), and the
  flagship metabolic disease is the weakest case on both metrics while two non-persona cancers are
  the strongest therapeutic showcases (§8.1).
- **The mirrored recipe code in this repo is a snapshot, not a mirror.** Two files checked at random
  both differed from what runs. Pull live code before reasoning about behaviour.

---

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
| 2026-08-09 | **Case study accepted as a known limitation, not a bug** (§8.3): the model finds the right pathway but not the right druggable node, because membrane receptors resist the assays that built the interactome. The prediction column is near-useless for discovery (590/762 known targets are false negatives at the F1 threshold). |
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
| 2026-08-17 | **Deliverable changed from pre-cut to filterable** — the top-50 truncation replaced by a Window rank, so `target_candidates_2` is **63,020 ranked rows** carrying tractability, class and safety annotations. Progressive filtering on obesity reaches a 65-candidate shortlist from the scientist's own thresholds. The data layer for the dashboard is now complete. |
| 2026-08-17 | **Filter validated per persona against drug-validated targets** (§10.3, `filtered_shortlist_eval`). Clauses 1–3 (novel → tractable → not-secreted) give **1.42–1.71× enrichment at 100% recall** in every disease that has validated targets — they cut the pool ~40% and lose nothing. **Clause 4 (exclude known liability) destroys 15–70% of them** and pushes obesity to **0.54× — worse than not filtering.** So the recommended filter is **three clauses**, with liabilities display-only. Outcome measured on *novel* drug-validated targets to avoid conflating the deliberate removal of known targets with filter damage. |
| 2026-08-17 | **Clearest single piece of evidence for dropping clause 4:** obesity's **ADRB2** is itself a drug-validated obesity target at rank #17 *and* carries a liability flag — the clause would have deleted a confirmed hit. Also recorded: the liability `event` field mixes real adverse events, bare mechanism descriptors (`regulation of catalytic activity`) and risk-factor biology (lung cancer's nicotinic candidates are flagged `nicotine dependence`, the disease's own risk mechanism). **Present it; never present it as a safety verdict.** |
| 2026-08-17 | **Filtering improves the ranking's usefulness but cannot fix its head.** With the 3-clause filter, top-N precision improves in 4 of 6 personas and never degrades (obesity 2→6 at top-50), yet **at top-20 only obesity finds anything at all**. That is §7.4's objective limitation reappearing downstream: no filter compensates for the model not placing drug-validated targets at the very top. |
| 2026-08-17 | **Candidate-decoration tail collapsed 5 recipes → 2** (§9.1), zone 18 items → 12. The chain was alternating joins and prepares doing nothing but left-joining lookups and then selecting, renaming and ordering columns — all of which a join recipe does itself. **Verified as a pure refactor:** same 63,020 rows, same key set, zero of 59 columns differing in value; only `disease_name`'s position moved, because DSS emits each input's columns as a block. |
| 2026-08-17 | **Recorded three join mechanics that are not discoverable from the payload** (DSS_CHEATSHEET): renames work via input `computedColumns`, **not** `rename` in `selectedColumns` (which round-trips then is ignored); dropping columns needs the per-input `MANUAL` list, since top-level `selectedColumns` sets order only; and the same dataset cannot be joined twice — accepted by the API, rejected at validation. The last one is the sole reason this is 2 recipes rather than 1. |
| 2026-08-17 | **Correction:** an earlier revision claimed the genetic-constraint columns had been kept off the shortlist. They had not — automatic column selection carried all five through. They are harmless as reference values but must **not** be surfaced as a dashboard filter, since that is precisely the filter the gate ruled out. |
| 2026-08-17 | **Two decisions reached by measurement rather than training**, at a cost of three recipes instead of three model runs. That is the second and third time the lift-gate pattern has prevented shipping a change that would have degraded the therapeutic axis. **Keep the gate as standing practice: state a falsifiable prediction, measure both labels, and be willing to be wrong** — here the prediction was refuted and that was the useful outcome. |

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
