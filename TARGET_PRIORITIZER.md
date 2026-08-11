# Explainable Target Prioritizer — Part 2

> **Companion to [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) and [PRIMEKG_MAPPING.md](PRIMEKG_MAPPING.md).**
> Those build the *substrate* (the graph) and the *explorer* (Visual Graph plugin). This doc
> is the analytical layer: features → split → model → validation → persona results.
> Evidence base: [RESEARCH_NOTE.md](RESEARCH_NOTE.md).
>
> **Status: BUILT & VALIDATED.** Current baseline model **`JONvgmkZ`** (12 features),
> macro per-disease AUC **0.8137**. Sections follow MLOps order; decisions are logged in the
> **appendix**, not inline.

## 1. Purpose & scope

Demonstrate POC value narrative **(a) discovery of novel targets**: for a disease, produce a
ranked shortlist of candidate gene/protein targets, each with a calibrated score and **two
complementary explanations** — a SHAP feature attribution ("*which evidence* drove this") and
a **graph path** to the disease module rendered on the Visual Graph ("*show me the mechanism*").

**In scope:** value-prop (a), **network-topology and functional-annotation features only**, on
the graph we already have.

**Deferred:** value-prop (b) toxicity/safety (DepMap essentiality + tissue expression); KG
embedding (PyKEEN) features; druggability/tractability features (§12).

## 2. What it delivers

`target_candidates` — per persona disease, the top-20 ranked candidates:

| disease_name | gene_name | score | top_shap_drivers | rank_in_disease | is_target |
|---|---|--:|---|--:|--:|
| breast cancer | BLM | 0.985 | dwpc_GPGD, ppi_adamic_adar | 2 | 0 |

Top-ranked genes **not currently linked** to the disease are the novel hypotheses. The
candidate and its evidence path highlight on the Visual Graph Editor (`lVWgU2m`) — §10.

## 3. Scientific basis & precedent

> Per-reference summaries and the feature→reference map are in [RESEARCH_NOTE.md](RESEARCH_NOTE.md).

This reproduces an industry-standard pattern rather than inventing one.

- **Supervised target prioritization = the Open Targets standard.** OT's Locus-to-Gene (L2G)
  is **XGBoost + SHAP** on a gold-standard positive set — *not* a GNN. Directly transferable
  to Dataiku Visual ML. (Mountjoy et al., *Nat Genet* 2021.)
- **Network proximity / guilt-by-association** — disease genes cluster in the interactome
  ("disease modules"); proximity to a module predicts association. Guney et al. (*Nat Commun*
  2016) classify indications at AUC ≈ 0.81. Menche et al. (*Science* 2015) established disease
  modules **and the incomplete-interactome caveat (~80% of interactions unmapped)** — which
  turns out to matter a great deal here (§10.3).
- **Meta-path / degree-weighted path count (DWPC)** — Himmelstein et al. (Rephetio, *eLife*
  2017): typed path counts over a heterogeneous network, degree-damped so hubs don't dominate.
- **Interpretability drives adoption.** TxGNN (*Nat Med* 2024, built on PrimeKG): path
  explanations raised expert accuracy +46% and confidence +49%.

## 4. Data — prediction unit, labels, candidate pool

**Unit of prediction:** a `(gene, disease)` pair → P(true `disease_protein` association).

**Label:** `is_target` = 1 if a `disease_protein` edge exists. Sourced from OT
`genetic_association` + `somatic_mutation` @ score ≥ 0.3.

> **The label set is itself study-biased.** Curated associations skew toward well-studied
> genes, which are also PPI hubs. A model that exploits hub-ness therefore scores *better* on
> AUC even when it is less useful for finding under-studied targets. This caveat governs how
> every result in §9 must be read.

**Disease eligibility:** diseases with **≥ 20 protein seeds** (`module_size ≥ 20`), so network
features are estimable. 1,154 of 27,153 diseases qualify.

**Candidate pool — the `has-path-evidence` restriction.** Keep only pairs where at least one
typed metapath route exists: `isNonBlank(dwpc_GGD) || isNonBlank(dwpc_GPGD) || isNonBlank(dwpc_GCD)`.
Applied to **train and test alike**.

| Stage | Rows | Positive rate |
|---|--:|--:|
| All (gene, eligible-disease) pairs | 18,396,158 | 0.90% |
| After `has-path-evidence` | **6,754,128** | **1.89%** |

This is **not** a convenience filter — it is a leakage control. Without it, features are
present for positives and absent for far negatives, and Visual ML's imputation turns "no
evidence of that type" into a label proxy (§6.1). It also scopes the deliverable honestly:
*prioritize plausible candidates **within** the disease's known molecular context*, not
"discover out-of-neighborhood targets."

**Known limits of that scope:** (a) mechanistically distant targets are unreachable — biased
toward incremental over serendipitous; (b) the ~80% incomplete interactome turns "no mapped
path" into false exclusion; (c) study bias over-weights well-annotated genes.

## 5. Feature engineering

`G`=gene, `D`=disease, `P`=pathway, `F`=GO molecular function, `B`=GO biological process,
`C`=drug. DWPC uses the standard degree-damping exponent (weight = ∏degree^−0.4), so paths
through hubs are down-weighted.

### 5.1 Features in the current model (12)

| Feature | Layer | Computed by | Biological significance |
|---|---|---|---|
| `dwpc_GPGD` | pathway_protein + disease_protein | Python (was Cypher) | Candidate sits in a **curated pathway** with known disease genes — shared mechanism at the reaction level. Strongest single feature (within-disease AUC 0.641). |
| `dwpc_GGD` | PPI + disease_protein | Cypher | Candidate **physically interacts** with proteins already implicated in the disease — the classic disease-module argument. |
| `dwpc_GFGD` | GO molecular function + disease_protein | Python | Candidate has the **same biochemical activity** as disease genes *without requiring a mapped physical interaction*. Routes around the interactome's membrane-protein blind spot — the single biggest model improvement (§8). |
| `dwpc_GBGD` | GO biological process + disease_protein | Python | Candidate **participates in the same biological process**. A broader, less mechanistic axis than GFGD; partially overlaps pathway evidence. |
| `prox_closest` | PPI | Python (BFS/Dijkstra) | Shortest PPI hop-count to the nearest module gene (capped at 3). Direct operationalization of Guney network proximity. |
| `ppi_adamic_adar` | PPI | Cypher | Neighbour-set overlap with the module, **discounting hub neighbours** (1/log degree) — sharing a rare interactor is more informative than sharing a promiscuous one. |
| `ppi_jaccard` | PPI | Cypher | Neighbour overlap normalized by union size — size-independent version of the same signal. |
| `ppi_common_neighbors_z` | PPI + disease_protein | Python | **Degree-matched** overlap: observed vs hypergeometric expectation. Answers "more module contact than this gene's connectivity alone predicts?" — the control that rescues sparsely-assayed genes. |
| `ppi_evidence_depth` | `edge_metadata.ppi_sources` | Python | Mean number of independent sources (Menche/HuRI/STRING) backing the gene's interactions. A **measurement-confidence covariate**: lets the model discount a thin neighbourhood instead of reading thin as negative. |
| `gene_ppi_degree` | PPI | Graph Features | Interactome connectivity — retained deliberately as the **single** hub control (§8). |
| `gene_n_pathways` | pathway_protein | Cypher | Annotation breadth — how well-characterized the gene is. Partly a study-bias proxy. |
| `shared_pathway_frac` | pathway_protein | Cypher | Fraction of the gene's pathways that overlap the module's — normalized, so it doesn't simply reward well-annotated genes. |

### 5.2 Computed but rejected — and why

| Feature | Reason rejected |
|---|---|
| `relation` | **Hard leak** — non-null iff the edge exists. A restatement of the label. |
| `rwr_score`, `rwr_norm` | **Label-derived missingness.** The RWR recipe records held-out *seed* genes unconditionally while floor-gating non-seeds, and seeds *are* positives → null gap −75 pp. |
| `gene_n_diseases` | **Label-derived** — built from the `disease_protein` label relation; alone separates test at AUC 0.835. |
| `disease_context` | Label-derived (counts module membership in neighbouring diseases) and 95% null. |
| `module_size` | Per-disease constant → pure base-rate encoder, zero within-disease ranking power. |
| `dwpc_GCD` | 99.8% null. Also **circular** for target ID: "an approved drug already targets this gene for this disease" nearly restates the label. Keep as a **post-hoc evidence annotation** instead (§10.3). |
| `ppi_common_neighbors` | Redundant — ρ +0.96 with `ppi_jaccard`, +0.93 with `ppi_adamic_adar`. |
| `shared_pathway_count` | Redundant — ρ +0.90 with `gene_n_pathways`; the normalized `_frac` is the better form. |
| `pagerank`, `triangles`, `eigenvector_centrality`, `clustering_coefficient` | **Collinear duplicates of degree** (ρ +0.98 / +0.93 / +0.80 / —) and **gene-only** (no disease information). Four encodings of one axis let the hub signal outvote the hub *penalty*. |
| `degree` | Duplicate of `gene_ppi_degree`. |
| `has_inflammatory_go_annotation` | Built as a §5b priority-1 candidate. **88% null, single-feature AUC exactly 0.5000** — contributed nothing. Lesson: *graded relational features beat binary gene-level flags.* |
| `disease_family_id`, `anchor_name`, `hop_depth` | Split bookkeeping (§6). `disease_family_id` would be a direct leak. |
| `ppi_multi_source_frac`, `ppi_cn_expected`, `ppi_edges_with_provenance` | Intermediates pulled in by the join's `AUTO_NON_CONFLICTING` mode. `ppi_multi_source_frac` is a legitimate candidate — promote or drop from the join. |

### 5.3 Not yet built

| Feature | Layer | Rationale | Priority |
|---|---|---|---|
| OT **tractability** buckets + **target class** (GPCR/kinase/ion-channel/NR) | Open Targets | The only thing that addresses the unresolved **ligand-vs-receptor** failure (§10.3). **Orthogonal to `is_target`, so expect no AUC gain** — likely belongs in the ranking layer, not the model. | 1 |
| `is_plasma_membrane` / `is_secreted` | GO cellular_component (**already in graph**) | Cheap druggability proxy; verified feasible (7,569/20,861 genes annotated; GLP1R=True, TP53=False). Splitting membrane from extracellular separates receptor from ligand. | 2 |
| gene-family / paralog (leave-one-out) | HGNC | GLP1R/GIPR/GCGR/GLP2R are one receptor family; a paralog being a known target is evidence nothing else captures. **Blocked** — `gene_names` lacks family columns. **Must be LOO** or it becomes a `gene_n_diseases`-style shortcut. | 3 |
| `disease_phenotype_context` | HPO | Phenotype-similarity alternative to the MONDO-hierarchy view of "related diseases". | 4 |
| `dwpc_GCcGD` | GO cellular component | Co-localization is usually too broad to discriminate ("nucleus" spans thousands of genes). | 5 |
| `dwpc_GHD` | HPO phenotype_protein | Now unblocked (the `phenotype_protein` edge exists). | 5 |

> **Do not build per-disease *count* features** (GO/HPO analogs of `module_size` or
> `disease_context`). They are base-rate encoders or label-derived shortcuts. Stick to
> gene-to-module **relational** features.

### 5.4 Implementation note — why the metapaths are Python, not Cypher

`dwpc_GFGD`/`dwpc_GBGD` OOM'd Kuzu's buffer pool as Cypher **even with a fanout guard**,
because the engine materializes every `(g, A, m)` path before aggregating. Only **12 of 11,187**
BP terms exceeded the fanout cap, so no threshold tuning would have helped.

The DWPC weight **factorizes**, so associating right-to-left never forms the gene×gene matrix:

```
S = X @ (W_A @ (X.T @ (W_m @ Z)))     X: genes×annotations,  Z: genes×diseases
    X.T @ (W_m @ Z)  ->  annotations × diseases   (~10k × 1.2k)
    X   @ (...)      ->  genes × diseases         (the answer)
```

Both metapaths then run in **~2 minutes**. The `m ≠ g` self-path and the leave-one-out module
size are handled analytically rather than by masking. Same precedent as `prox_closest` and
`rwr_score`, which were also moved to Python. See
[dss_recipes/compute_dwpc_go_metapaths.py](dss_recipes/compute_dwpc_go_metapaths.py).

## 6. Splitting strategy — leakage control

Three distinct leaks were found and fixed. Each was discovered by a result that was *too
good*, and each needed a different control.

### 6.1 The three leaks

| # | Leak | Symptom | Fix |
|---|---|---|---|
| 1 | **Random split** | AUC 0.993 — a disease's pairs land in both folds, and every feature is proximity-to-*that*-module, so the model memorizes known modules | **Disease-grouped split** |
| 2 | **Missing-data / easy-negative** | AUC 0.989 even when grouped. No feature separated by *value* (best 0.685), but the **null pattern** did — features present for positives, absent for far negatives | **`has-path-evidence` restriction** (§4) + reject label-derived features + `IMPUTE MEAN` (§7) |
| 3 | **Ontology hierarchy** | Parent/child MONDO terms share biology; a parent in validation with a child in train leaks | **Disease-family split** (§6.3) |

`prox_closest ≤ 2` is **insufficient** for leak 2 — the test set is 87% `prox=2`, so the
coverage skew survives.

### 6.2 Data exploration that motivated the family split

Inspection of `graph_nodes` surfaced 18 separate breast-carcinoma concepts (`breast carcinoma`,
`invasive ductal breast carcinoma`, `female breast carcinoma`, …). Confirmed live on the
persona diseases:

- **`breast cancer` ↔ `breast carcinoma`** and **`obesity disorder` ↔ `morbid obesity`** are
  each **immediate parent/child (1 hop)** — and each pair was split across the train boundary.
  **All four personas were compromised**, two by being in train outright, two by having their
  parent/child in train.

**Graph-topological family construction was tried and rejected.** It collapses at every setting:

| Approach | Largest component (of ~900–1,150 eligible diseases) |
|---|---|
| undirected transitive closure | 24,917 (the whole ontology) |
| undirected K-hop, K=1 / K=2 | 930 (81%) / 1,145 (99%) |
| directed ancestor + hub filter (9 configs: K=2–4 × fanout 20/50/100) | 759–872 (83–96%) |

Two causes: (a) broad classificatory terms (`hereditary disease`, fanout 1,906) are themselves
eligible and are *genuine* ancestors, so directionality doesn't help; (b) **51% of eligible
diseases (469/913) have more than one direct MONDO parent** — it is a DAG, so transitive
union-find chains unrelated branches together. **No clean global partition exists.**

### 6.3 The adopted method — Hetionet DO-Slim anchor rollup

Hetionet v1.0 curated **137 Disease Ontology terms** under an explicit **antichain constraint**
(*no DO Slim term is a subtype of another*) — exactly the property needed. We reuse that
curation as a fixed **anchor set**, not as our disease universe.

Each disease walks **up** the native directed MONDO hierarchy (`raw_disease_disease`,
pre-reversal) to its **nearest** anchor; ties break on shallowest depth then lowest index; no
anchor within 15 hops → falls back to its own index (never worse than a plain disease split).
Because anchors are a *static lookup* rather than nodes that accumulate unions, ambiguity stays
**local** (7.4% of diseases reach >1 anchor) instead of cascading.

| Metric | Value |
|---|--:|
| Hetionet DOIDs mapped to MONDO | 136 / 137 |
| Usable anchors in the current graph | 110 |
| Diseases resolving to an anchor | 317 / 1,157 (27.4%) |
| Families produced | **927** (from 1,157 diseases) |
| Multi-member families | 24 |
| Breast-cancer family size | 20 diseases |

**Both persona pairs resolve automatically** — `breast cancer` *is* an anchor (depth 0) with
`breast carcinoma` at depth 1; likewise `obesity` / `morbid obesity`.

**Honest scope: this mitigates, it does not solve.** 73% of diseases find no anchor and retain
only disease-level protection. Hetionet's curation skews to GWAS-studied common diseases, so
coverage is best exactly where the personas live and worst in the long tail.

### 6.4 The split as implemented

Split key is `disease_family_id`, never `disease_index`:

```
if(arrayContains([0,1,2,3,4], mod(disease_family_id, 10))
   || disease_family_id == 15347 || disease_family_id == 16415,
   "validation", if(mod(disease_family_id, 10) == 5, "test", "train"))
```

Persona **families** (not individual diseases) are forced into validation.

| Set | Rows | Share |
|---|--:|--:|
| train | 2,745,929 | 40.7% |
| validation | 3,402,075 | 50.4% |
| test | 606,124 | 9.0% |

> **`node_index` is positional and unstable** — reassigned on every `compute_kg` run. The
> hardcoded persona ids above must be re-derived from `node_id` after any graph rebuild.
> Current: breast cancer **15347**, breast carcinoma **16029**, obesity disorder **16415**,
> morbid obesity **61925**.

## 7. Model configuration & hyperparameters

| Setting | Value | Note |
|---|---|---|
| Algorithm | **XGBoost** (`XGBOOST_CLASSIFICATION`) | logistic regression as comparator: AUC 0.834 vs 0.895 — the non-linearity is worth ~0.06 |
| `max_depth` | grid **4–6** (3 values, LINEAR) | |
| `n_estimators` | 300, early stopping enabled | |
| `booster` | `gbtree` | |
| Class handling | `weightMethod: CLASS_WEIGHT` | positives are ~1.9% |
| `scale_pos_weight` | 1.0 | class weighting handled by DSS, not here |
| Seed | 1337 | also the split seed |
| Evaluation metric | `ROC_AUC`, MACRO averaging | but **report per-disease AUC** (§9.1) |
| Threshold optimization | F1 | see the warning below |
| Train/test policy | `EXPLICIT_FILTERING_TWO_DATASETS` | `enriched_train_full_3` / `enriched_test_set_3` |

### 7.1 Feature-handling standard (mandatory)

**Every numeric INPUT: `rescaling: AVGSTD` + `missing_handling: IMPUTE` +
`missing_impute_with: MEAN`. No exceptions.**

- **Rescaling is a no-op for XGBoost** — AVGSTD is affine/monotonic and tree splits are
  invariant to monotonic transforms. It *does* matter for the logistic comparator, so
  uniformity is cheap insurance.
- **Imputation is the one that bites.** DSS imputes *before* XGBoost, so XGBoost's native
  sparsity-aware handling never engages and the fill value is decisive. `MEAN` puts nulls at
  the distribution centre (indistinguishable from average rows → the tree **cannot** isolate
  "was missing"); `CONSTANT 0` puts them at a separable point (the tree **can**). With
  `dwpc_GGD`/`ppi_adamic_adar`/`ppi_jaccard`/`ppi_common_neighbors_z` all carrying **−31.6 pp
  null gaps by label**, `CONSTANT` reopens leak 2 outright. For a z-score, 0 is doubly wrong —
  it is the null-model expectation, mid-distribution (real median +2.55).
- **DSS's guesses are inconsistent — audit `per_feature` after every lab deploy.** Deploying
  run 3 produced `NONE`/`CONSTANT` on **9 of 12** features; run 2's deploy was mostly correct
  on identical data.
- Measured exposure was small (≤0.0017 AUC) because the same "was this pair reachable" bit was
  already available via `ppi_adamic_adar`. Fix it for reproducibility, not the leaderboard.

### 7.2 The threshold is not the ranking

The F1-optimised threshold lands at **≈0.875** against a ~2% base rate. Consequence:
**590 of 762 known obesity targets are predicted negative**, recall 22.6%.

> **The `prediction` column is near-meaningless for discovery. Rank by `proba_1` and take
> top-N** — which is what the persona flow does.

## 8. Feature & model selection — the ablation ladder

### 8.1 The audit that motivated it

Three measurements on the 15-feature baseline:

1. **7 of 15 INPUTs were GENE-ONLY** — 0.0% of genes showed more than one distinct value
   across the four persona diseases. They cannot answer "is this gene a target *for this
   disease*", only "is this gene generally prominent."
2. **The hub axis was over-represented** — `gene_ppi_degree` ↔ `pagerank` ρ +0.975,
   ↔ `triangles` +0.927, ↔ `eigenvector_centrality` +0.804. Four near-duplicates against
   DWPC's two, so the hub *penalty* was outnumbered.
3. **The hub-penalised features are the ones that work** — within-disease single-feature AUC:
   `dwpc_GPGD` 0.641, `dwpc_GGD` 0.601, vs every gene-only feature ≈ 0.5.

### 8.2 Results

All runs share the split, hyperparameters and handling standard above; row counts identical
(6,754,128 / 2,745,929 / 606,124), so the four are directly comparable.

| Run | Model | Feat | Pooled AUC | **Macro per-disease AUC** | Median | >0.8 | recall@20 | Degree spread | ρ(deg,proba) |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| baseline | `9Xr84fs9` | 15 | 0.8663 | 0.7737 | 0.7992 | 49.9% | 0.1042 | +0.1879 | +0.3304 |
| 1 pruned | `6EtVWdE2` | 8 | 0.8666 | **0.7610** ✗ | 0.7792 | 46.2% | 0.1106 | +0.1755 | +0.2953 |
| 2 +PPI control | `EHsHTJTG` | 10 | 0.8772 | 0.7767 | 0.8000 | 49.9% | 0.1157 | +0.1646 | +0.2848 |
| **3 +GO dwpc** | **`JONvgmkZ`** | **12** | **0.8951** | **0.8137** | **0.8419** | **57.9%** | **0.1270** | **+0.1046** | **+0.2391** |

**Run 1 — pruning alone FAILED.** Pooled AUC was unchanged (0.8666 vs 0.8663) but macro
per-disease AUC *fell* to 0.7610, winning on only 176/591 diseases. A textbook case of pooled
AUC hiding a within-disease loss. Pruning was directionally right but removed signal without
replacing it.

**Run 2 — the degree-matched control recovered it.** 0.7767, wins 372/591 (62.9%), lowest bias
so far. `ppi_common_neighbors_z` supplied the degree-corrected module-contact signal that
pruning had stripped.

**Run 3 — the GO metapaths are the decisive win.** **+0.0400 macro per-disease AUC over
baseline, winning 509/591 diseases (86.1%)**; +0.0370 over run 2 (499/591). **Every metric
improves at once** — normally accuracy and bias trade off, but the degree spread nearly halved.
So the GO features bought accuracy with genuinely *new, degree-independent* signal.

**Unanchored diseases gained most** (0.7508 → 0.7936 vs anchored 0.8390 → 0.8709) — the
poorly-annotated tail benefits more from functional similarity, since those are the diseases
whose PPI routes are sparsest. Encouraging for generalization beyond the personas.

## 9. Model validation

### 9.1 Metric methodology

**Report macro per-disease AUC, not pooled.** Pooled AUC gets credit for separating genes
across *different* diseases (easy — a gene in a well-annotated disease outranks one in a sparse
disease); the deliverable is ranking genes *within* one disease. **Pooled overstates by ~9
points** (0.895 vs 0.814 for the current baseline).

Per-disease AUC is computed in-flow (zone `validation`) via the Mann-Whitney rank-sum identity
on descending `proba_1` ranks:

```
auc_disease = 1 - (target_rank_sum - n_pos*(n_pos+1)/2) / (n_pos * n_neg)
```

Restrict the headline to diseases with `n_pos ≥ 10` (AUC on 2 positives is noise): **0.8278**
for the current baseline, n=517.

### 9.2 Hub-bias meter

Among **known targets only** — biology held constant, every gene a true positive — bin by PPI
degree and compare Q1 to Q5. Baseline: Q1 (median degree 3) 6.8% predicted positive vs Q5
(median 104.5) **40.8%** — a **6× detection swing on network position alone**.

| Model | Q1 proba | Q5 proba | Spread | ρ(degree, proba) |
|---|--:|--:|--:|--:|
| baseline | 0.5732 | 0.7611 | +0.1879 | +0.3304 |
| run 3 `JONvgmkZ` | 0.5735 | 0.7391 | **+0.1046** | **+0.2391** |

### 9.3 Per-family validation (zone `family validation`)

Same chain, grouped by `disease_family_id` — 480 families.

| Group | n | Macro AUC | Median |
|---|--:|--:|--:|
| **multi-disease families** (grouping actually applies) | 24 | **0.8615** | 0.9087 |
| single-disease families (grouping is a no-op) | 456 | 0.7487 | 0.7550 |

Large families are almost all cancers at ~0.90–0.92 (ovarian 0.9238, colon 0.9225, bone
0.9203, brain 0.9198, uterine 0.9176, **breast 0.9072 across 20 members / 4,839 positives**).
**Epilepsy (0.7789) is the lone non-cancer large family and the lone weak one** — its MONDO
subtypes span channelopathies, structural lesions and metabolic causes, so the family boundary
stops being mechanistically coherent.

### 9.4 Anchored vs unanchored is *not* a leak meter

Anchored (family-protected) diseases score **higher**, consistently (0.8390 vs 0.7508 baseline;
0.8709 vs 0.7936 run 3). This is **confounded**: Hetionet's DO Slim was curated toward
GWAS-studied common diseases, so anchored diseases are also the best-annotated ones. Annotation
depth dominates any residual leakage signal. Isolating leakage would require `module_size`-matched
strata.

## 10. Persona validation & results

Output chain: `enriched_validation_set_3` → `filter_persona_diseases` → `score_persona_candidates`
(SHAP on) → `compute_top_shap_drivers` → `top20_per_disease` → name joins → **`target_candidates`**.

### 10.1 Per-persona performance

| Persona disease | module_size | n_pos | AUC (baseline) | AUC (run 3) |
|---|--:|--:|--:|--:|
| breast carcinoma | 973 | 864 | 0.8401 | **0.8572** |
| morbid obesity | 108 | 41 | 0.7000 | **0.7222** |
| obesity disorder | 1,027 | 762 | 0.6682 | **0.7087** |
| breast cancer | 232 | 138 | 0.7035 | 0.6913 ✗ |

All four sit at or below the macro average — the personas are **not** cherry-picked easy
diseases, which makes for a more honest demo. Breast cancer is the one persistent regression
across the whole ladder.

### 10.2 Candidate output — biological coherence

| Persona | known targets in top 20 | Notable novel calls |
|---|--:|---|
| **breast cancer** | 11 / 20 | **BLM** (#2), **RAD50** (#4), **MLH1** (#6), **MRE11** (#10) |
| breast carcinoma | 19 / 20 | — |
| obesity disorder | 17 / 20 | — |
| **morbid obesity** | 0 / 20 | **GNAS, GCG, GIP, IAPP, RAMP1/2** |

- **Breast cancer** surfaces BLM (Bloom helicase), RAD50 + MRE11 (MRN complex, alongside
  already-known NBN), MLH1 (mismatch repair) — all homologous-recombination / DNA-damage-repair
  genes, the right neighbourhood for BRCA-adjacent susceptibility.
- **Morbid obesity** surfaces the incretin/metabolic axis — GCG (glucagon), GIP, IAPP (amylin),
  RAMP1/2 — the pathway GLP-1 agonists act on.

**Disease-granularity finding.** The coarser/smaller-module term surfaces *novel* candidates;
the larger-module term mostly *re-identifies known* targets (breast cancer 11/20 vs breast
carcinoma 19/20; morbid obesity 0/20 vs obesity disorder 17/20). Family aggregation lifts
breast cancer's AUC 0.704 → 0.907 but degrades the candidate list from mechanism-specific
(BLM/RAD50/MLH1/MRE11) to pan-cancer drivers (TP53 known in 19 of the family's 20 members,
CTNNB1, PIK3CA, KRAS).

> **Aggregation buys AUC and costs specificity. Split by family (leakage control); report and
> act at the disease level.**

### 10.3 Case study — GLP1R, and the limits of a PPI-based model

GLP1R (Entrez 2740) is the semaglutide/liraglutide target and `is_target = 1` for obesity
disorder. The model scored it **0.8531 → rank 1,472 / 13,126 (top 11.2%)** and predicted
**negative** — a false negative, one of 590.

**Why the rank was low — neighbour overlap, not degree:**

| Gene | PPI partners | shared with module | `dwpc_GGD` | proba | is_target |
|---|--:|--:|--:|--:|--:|
| GCG (ligand) | 37 | **13** | 0.0205 | 0.980 | 0 |
| IAPP (ligand) | **16** | **7** | 0.0180 | 0.978 | 0 |
| GLP1R (receptor) | **28** | **3** | 0.0039 | 0.853 | **1** |

GLP1R has *more* PPI partners than IAPP yet scores far lower. The discriminator is **overlap
with the module**, which drives `ppi_common_neighbors`/`adamic_adar`/`dwpc_GGD`. Mechanistically
this is the **membrane-protein assay bias**: transmembrane GPCRs resist Y2H/AP-MS, so their
mapped neighbourhoods are sparse. The model penalizes GLP1R for an *assay artifact*, not
biology — a live instance of Menche's incomplete-interactome caveat (§3).

**The unresolved failure: ligands outrank their own receptors.** Every secreted peptide ligand
is predicted positive despite *not* being a known target; every membrane receptor that *is* a
known target is predicted negative. The model finds the right *pathway* but not the right
*druggable node*. The ablation improved receptors (GLP1R 1,472 → 535; GIPR 1,489 → 634) without
fixing the discrimination — it needs **target-class/druggability** signal (§5.3), not more
network similarity.

**The evidence the model is not allowed to use.** `dwpc_GCD = 0.0855` for GLP1R traces to
exactly one compound — **DANUGLIPRON**, an oral GLP-1 agonist. `dwpc_GCD` is rejected as
circular (§5.2), which is defensible, but it means the most decisive evidence is computed and
discarded. **Use it as a post-hoc annotation on the ranked list** ("this candidate already has
drug-level validation"), not as a training feature.

### 10.4 On-graph explanation — Cypher for the Visual Graph

Anchor demo: the breast-cancer top-10 contains **RAD50 (#4), NBN (#8), MRE11 (#10)** — all
three members of the **MRN double-strand-break repair complex**, with RAD50 and MRE11 *novel*.
The prediction explains itself on the canvas.

Conventions: undirected traversal `-[:rel]-`; `//` comments not `--`; **relationship variables
must be bound AND returned** or the canvas shows floating nodes. Kuzu label for genes is
`protein`. Indices are snapshot-specific — re-derive from `node_id` after any rebuild.

```cypher
// 1. Why these genes? Top-10 predictions + PPI evidence to a KNOWN module gene.
MATCH (D:disease {node_index: 15347})                       // breast cancer
MATCH (g:protein)
WHERE g.node_index IN [7634, 10878, 11397, 227, 11700, 7338, 11424, 7597, 6086, 7396]
MATCH (g)-[ppi:protein_protein]-(m:protein)-[assoc:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, ppi, m, assoc, D
LIMIT 300
```

```cypher
// 2. The MRN story — two NOVEL genes, their PPI to known targets, and the disease.
MATCH (D:disease {node_index: 15347})
MATCH (novel:protein) WHERE novel.node_index IN [227, 7396]          // RAD50, MRE11
MATCH (known:protein) WHERE known.node_index IN [7597, 7634, 11397]  // NBN, ATM, BRCA1
MATCH (novel)-[ppi:protein_protein]-(known)
MATCH (known)-[assoc:disease_protein]-(D)
RETURN novel, ppi, known, assoc, D
```

```cypher
// 3. GLP1R vs the obesity module — the SPARSE picture (only 3 shared neighbours).
MATCH (D:disease {node_index: 16415})
MATCH (g:protein {node_index: 5224})                        // GLP1R
MATCH (g)-[ppi:protein_protein]-(m:protein)-[assoc:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, ppi, m, assoc, D
```

```cypher
// 4. THE CONTRAST SHOT — ligands (dense) vs receptors (sparse), same disease.
//    Makes the assay bias visible: the druggable half is thin purely because
//    membrane receptors resist the assays that built the interactome.
MATCH (D:disease {node_index: 16415})
MATCH (g:protein)
WHERE g.node_index IN [4918, 5020, 6176,        // ligands:   GCG, GIP, IAPP
                       5224, 5025, 4919, 12379] // receptors: GLP1R, GIPR, GCGR, CALCR
MATCH (g)-[ppi:protein_protein]-(m:protein)-[assoc:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, ppi, m, assoc, D
LIMIT 400
```

```cypher
// 5. The evidence the model is NOT allowed to use: GLP1R <- DANUGLIPRON -> obesity.
MATCH (D:disease {node_index: 16415})
MATCH (g:protein {node_index: 5224})
MATCH (g)-[dt:drug_protein]-(C:drug)-[ind:indication|drug_investigated_for]-(D)
RETURN g, dt, C, ind, D
```

**Run these in the interactive Graph Explorer, not the Execute Cypher recipe** — the recipe
path is unreliable on this graph (unexplained `IndexError` inside the plugin's generated
script; Kuzu buffer-pool OOM on variable-length expansion).

**Improvement:** the gene lists are pasted literals because the Kuzu graph carries no model
output. Materializing `predicted_score`/`predicted_rank` as gene-node properties would turn
these into `WHERE g.pred_rank_15347 <= 10`.

## 11. Flow design

| Zone | Contents |
|---|---|
| `enriched_graph features_1` | per-feature recipes (Cypher + Python) → 16-input star join → `enriched_graph_features_1` (18.4M pairs) |
| — | `compute_disease_family_id` → `join_disease_family_id` → `enriched_graph_features_1_family` |
| `enriched_resampling_1` | `compute_graph_features_sampled_*` (has-path-evidence filter) → `split_graph_features_candidate_*` → train/validation/test |
| Modeling | `train_is_target_*` → saved models |
| `validation` | score → window rank → group → per-disease AUC |
| `family validation` | same, keyed on `disease_family_id`, + gene-level top-20 per family |
| `persona` | persona filter → SHAP scoring → top-20 → name joins → `target_candidates` |

**Heavy graph math is Python, not plugin recipes** — `compute_enriched_prox_closest_bfs_test`,
`compute_enriched_rwr_score_1`, `compute_dwpc_go_metapaths`, `compute_ppi_cn_zscore`,
`compute_ppi_evidence_depth`. The Execute Cypher *recipe* path repeatedly failed at this scale.

**Kuzu Build Graph caveats:** non-`node_index` node PKs silently drop that type's edges; every
relation needs its own edge group with a `relation matches …` filter (a missing filter silently
drops it — hit on `pathway_protein` and `drug_investigated_for`).

## 12. Open decisions & deferrals

- **Druggability / target class** — the top remaining feature gap; the only thing that
  addresses ligand-vs-receptor (§10.3). Note it is orthogonal to the label, so it may belong in
  the ranking layer rather than the model. If the *model* should predict druggable targets, the
  **label** has to change — a scope decision, not feature engineering.
- **Value-prop (b) toxicity/safety** — DepMap essentiality + GTEx/Bgee expression as per-gene
  features → efficacy×safety traffic light (mirrors OT Target Prioritisation).
- **KGE features** — PyKEEN TransE/ComplEx triple score; the one family that can score
  *pathless* pairs, i.e. reach past the has-path-evidence boundary (§4).
- **Degree-matched negative sampling** — currently class weights only. A cheaper diagnostic:
  evaluate the existing model on a degree-matched validation subset.
- **Permutation baseline** — a degree-preserving permuted-graph null (Rephetio/XSwap) would
  quantify signal beyond degree. Controls the degree confound, *not* the coverage leak.
- **Model housekeeping** — four saved models now exist (`9Xr84fs9`, `6EtVWdE2`, `EHsHTJTG`,
  `JONvgmkZ`) plus superseded `5t2ek90a`/`GlVckALL`/`ciuubnE2`. Prune or label clearly.

---

## Appendix — decision log

| Date | Decision |
|---|---|
| 2026-07-08 | Part 2 flagship = **Explainable Target Prioritizer** (Visual ML + SHAP, L2G-analog). Discovery (a) first; toxicity (b) deferred. Network-topology features only; no KGE. |
| 2026-07-08 | Feature engineering pushed into **Visual Graph plugin recipes** over Kuzu rather than monolithic `networkx`. *(Substantially reversed 2026-08 — see below.)* |
| 2026-07-08 | **Proximity z-score dropped** — "the supervised model already sees degree and will absorb hubness." *(Falsified 2026-08-09 and reversed.)* |
| 2026-07-28 | **Leaks 1 & 2 diagnosed** (§6.1). Correct setup = disease-grouped split + `has-path-evidence` on train AND test + reject label-derived features. `prox ≤ 2` is insufficient. |
| 2026-08-05 | **§5b feature candidates drafted** contingent on Task 10 (GO/HPO). `has_inflammatory_go_annotation` ranked priority 1, `dwpc_GFGD`/`GBGD` priority 2. *(Priorities inverted by results — see 2026-08-10.)* |
| 2026-08-05 | **`drug_investigated_for` added to the Kuzu graph** as its own edge group (not merged with `indication`), and `dwpc_GCD`'s Cypher updated to `-[:indication\|drug_investigated_for]-`. **Rejected:** OT `known_drug` datatype — redundant with the metapath. |
| 2026-08-08 | **Leak 3 found: ontology hierarchy** (§6.2). All four personas compromised. **Rejected:** graph-topological family construction (collapses 83–96% of diseases; 51% have >1 direct MONDO parent). **Adopted:** Hetionet DO-Slim anchor rollup → `disease_family_id`; split keys on `mod(disease_family_id, 10)`. |
| 2026-08-08 | **A candidate filter can leak even when the feature is REJECTed.** An `isNonBlank(rwr_score)` filter scored AUC 0.946 and was withdrawn — the RWR recipe records seeds unconditionally, so non-null is label-derived (null gap −75 pp vs +0.43 pp for `prox_closest`). Replaced with `prox_closest ≤ 2`. **Rule: disqualify a filter when its *missingness* is set by a label lookup, not when its values correlate with the label.** |
| 2026-08-09 | **Report per-disease AUC, never pooled** — pooled overstates by ~9 points and hid a real regression in ablation run 1. |
| 2026-08-09 | **Granularity: split by family, report by disease** (§10.2). Family aggregation lifts breast cancer 0.704 → 0.907 but degrades candidates from mechanism-specific to pan-cancer. Family coherence is mechanism-dependent (cancers ~0.90–0.92, epilepsy 0.78). |
| 2026-08-09 | **GLP1R case study** (§10.3): the `prediction` column is near-useless for discovery (590/762 known targets are false negatives at the F1 threshold). Root cause of low rank is *neighbour overlap*, not degree — membrane-protein assay bias. `dwpc_GCD`/DANUGLIPRON kept as a post-hoc annotation, not a feature. |
| 2026-08-09 | **Feature audit** (§8.1): 7 of 15 INPUTs were gene-only, hub axis had 4 collinear encodings, every gene-only feature ≈0.5 AUC. Bias meter established (6× detection swing Q1→Q5). |
| 2026-08-10 | **Ablation ladder complete** (§8.2). Run 1 (prune) **failed** on per-disease AUC despite flat pooled AUC. Run 2 (+`ppi_common_neighbors_z`, `ppi_evidence_depth`) recovered. **Run 3 (+`dwpc_GFGD`, `dwpc_GBGD`) wins decisively** — per-disease AUC 0.8137, degree spread nearly halved. **New baseline `JONvgmkZ`.** Reverses the 2026-07-08 z-score decision. |
| 2026-08-10 | **GO metapaths implemented in Python, not Cypher** (§5.4) — Cypher OOM'd even with a fanout guard; the factorized right-to-left formulation runs both in ~2 min. |
| 2026-08-10 | **Feature-handling standard mandatory** (§7.1): all numeric INPUTs `AVGSTD` + `IMPUTE MEAN`. DSS's lab-deploy guesses are inconsistent — audit `per_feature` after every deploy. |
| 2026-08-10 | **§5b priorities inverted by results**: the priority-1 binary flag scored exactly 0.5000 and was rejected; the priority-2 GO metapaths were the biggest win. *Graded relational features beat binary gene-level flags.* |

## References

> Per-reference summaries, the feature→reference map, and provenance caveats are in
> **[RESEARCH_NOTE.md](RESEARCH_NOTE.md)** (unvalidated corpus — verify before client-facing use).

- Open Targets L2G — Mountjoy et al., *Nat Genet* 2021
- Open Targets Target Prioritisation — https://platform-docs.opentargets.org/web-interface/target-prioritisation
- Network proximity — Guney, Menche, Vidal, Barabási, *Nat Commun* 2016
- Disease modules / incomplete interactome — Menche et al., *Science* 2015
- Meta-path / DWPC — Himmelstein et al. (Rephetio), *eLife* 2017
- TxGNN (interpretability) — Huang et al., *Nat Med* 2024
- HuRI (unbiased interactome) — Luck et al., *Nature* 2020
- STRING — Szklarczyk et al., *NAR* 2023
