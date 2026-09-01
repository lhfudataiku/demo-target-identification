# Explainable Target Prioritizer — modelling method

> **Lifecycle:** Canonical · **Audience:** Part 2 data scientists and reviewers · **Authority:**
> modelling method, data constraints, features, split, training, ablation and model-selection
> rationale · **Update when:** one of those choices changes · **Generated dependencies:**
> `.index/features.tsv`, `.index/models.tsv` and governed IDs from
> [`CLAIM_REGISTRY.json`](CLAIM_REGISTRY.json) · **Excludes:** detailed validation results, demo copy,
> DSS topology, build history and migration chronology.

This document explains how `DEMO_TARGET_IDENTIFICATION` turns the shared graph into a ranked list.
Measured outcomes and limitations live in [VALIDATION.md](VALIDATION.md); notebooks remain their
computational authority. The complete pre-split record is preserved as
[`archive/prioritizer/TARGET_PRIORITIZER_PRE_PHASE3.md`](../../archive/prioritizer/TARGET_PRIORITIZER_PRE_PHASE3.md).

Companions: [PROJECT_CONTEXT.md](../overview/PROJECT_CONTEXT.md) for the two-project contract,
[FEATURE_AUDIT.md](FEATURE_AUDIT.md) for recipe-level review,
[PHASE3_PREREGISTRATION.md](PHASE3_PREREGISTRATION.md) for the seed-gate experiment, and
[RESEARCH_NOTE.md](../reference/RESEARCH_NOTE.md) for the literature map.

## 1. Prediction task and governing constraints

The prediction unit is a `(disease, gene)` pair. The positive label is an existing disease–protein
association in the graph. The output is a within-disease ranking, not a cross-disease calibrated
probability and not a claim of causality or therapeutic success.

Four observed properties govern the method:

1. **The label is study-biased.** A small group of well-studied diseases and genes carries a large
   share of associations. Pooled metrics therefore let large diseases dominate, and gene popularity
   can look like model quality.
2. **The disease ontology is redundant.** Parent and child terms share biology. Random row or disease
   splits leak that biology across partitions, so the split is elevated to an external family key.
3. **Candidate eligibility is part of the estimand.** A pair enters only through a graph route that
   supplies model evidence. The pool is not every disease crossed with every gene (`TI-DATA-001`).
4. **Subtype resolution follows the evidence.** Molecularly distinct breast subtypes can separate;
   morphology-only or weakly annotated subtypes often do not. The method makes no generic subtype
   promise.

The scientific pattern is intentionally conventional: gradient-boosted trees and SHAP in the style
of Open Targets Locus-to-Gene, network proximity, degree-weighted typed paths, and explicit
provenance/degree controls. The differentiator is reproducibility and inspectability, not a novel
learning algorithm.

## 2. Candidate population and leakage controls

### 2.1 Three failure modes, three controls

| failure | symptom | method control |
|---|---|---|
| random row split | the same disease module appears in both folds | group by disease, then elevate to family |
| easy-negative missingness | feature presence separates positives from distant negatives | evidence-bearing candidate pool, feature rejection and mean imputation |
| ontology overlap | parent and child terms straddle folds | external curated antichain anchors and elevated split key |

A result that is “too good” is treated as a leakage signal until these controls survive an audit.

### 2.2 Eligibility routes

A pair is admitted by the deduplicated union of three routes:

| route | method role | caution |
|---|---|---|
| gene–gene–disease (`GGD`) | interaction proximity to known disease genes | depends on an incomplete interactome |
| gene–pathway–gene–disease (`GPGD`) | shared curated pathway context | rewards annotation breadth unless degree-damped |
| gene–compound–disease (`GCD`) | compound-mediated context | outcome-selected for drug-based evaluation |

The current governed route and pool measurements are `TI-DATA-001`; they are evidence, not constants
to copy into method prose.

The pool restriction prevents imputed absence from becoming an easy-negative label proxy. It also
sets an honest scope: prioritise plausible candidates within the disease's mapped molecular context.
Mechanistically distant or unmapped targets can be excluded.

`GCD` is deliberately retained in the population but rejected as a model feature. It admits some
therapeutically relevant pairs that would otherwise be invisible, while selecting on the outcome used
by the therapeutic benchmark. Validation therefore reports all-positive and route-supported
estimands together (`TI-VAL-006`) rather than deleting the route or hiding the bias.

Adding `prox_closest` as a fourth admission route was tested and rejected. It expanded the pool about
2.7-fold, reduced prevalence and admitted rows on which four champion inputs were null by
construction. Recovered curated pairs still did not enter the top 200, while mostly-imputed rows
contaminated the head of the list. The gate is not the only problem: local topology features cannot
score pathless pairs.

### 2.3 Family split

The disease ontology is a DAG, so transitive components collapse unrelated branches into one giant
family. Instead, the method borrows a published antichain of disease terms as fixed anchors. Each
disease walks upward through the native directed hierarchy to its nearest anchor; ties resolve by
hierarchy depth and then a deterministic identifier rule. Diseases without a reachable anchor fall
back to their own key.

The split uses the elevated family key, never the disease row or disease identifier. Persona families
are explicitly forced into validation; other keys use the deterministic modulo allocation. The audit
must show zero split-key overlap and zero straddling. Identifier migrations require a fresh audit of
every modulo, minimum and ordering rule because remapping literals alone is insufficient.

Family anchoring mitigates leakage; it does not solve the long tail. Most uncommon diseases do not
resolve to an external anchor and retain disease-level protection only.

## 3. Feature method

`G` is gene, `D` disease, `P` pathway, `F` molecular function and `B` biological process. Typed path
counts use standard degree damping, multiplying each path by degree to the power −0.4. Leave-one-out
and self-path guards prevent a known target from contributing to its own feature.

### 3.1 Champion feature set

The governed champion is `TI-MOD-001`. Its 14 inputs are:

| feature | family | method purpose |
|---|---|---|
| `dwpc_GPGD` | typed path | pathway similarity to the disease module |
| `dwpc_GGD` | typed path | physical-interaction proximity |
| `dwpc_GFGD` | typed path | shared molecular function, including routes around missing PPIs |
| `dwpc_GBGD` | typed path | broader shared biological process |
| `prox_closest` | proximity | nearest mapped module gene; retained with explicit null handling |
| `prox_kernel` | proximity | graded distance to the whole module |
| `ppi_adamic_adar` | topology | rare shared neighbours receive more weight |
| `ppi_jaccard` | topology | size-normalised neighbour overlap |
| `ppi_common_neighbors_z` | topology/control | overlap beyond degree-matched expectation |
| `ppi_evidence_depth` | provenance | independent-source depth behind interactions |
| `ppi_multi_source_frac` | provenance | share of interactions corroborated by multiple sources |
| `gene_ppi_degree` | gene control | one retained hub covariate |
| `gene_n_pathways` | gene control | annotation-breadth covariate |
| `shared_pathway_frac` | normalised context | fraction of the gene's pathways shared with the module |

The design thesis is that measurement-confidence covariates matter alongside topology on a
study-biased graph. Gene-only controls cannot establish disease specificity, so they are limited to
normalisation and never interpreted as disease evidence.

### 3.2 Rejected features

| feature or family | rejection reason |
|---|---|
| `relation` | direct restatement of the label |
| `rwr_score`, `rwr_norm` | label-derived missingness from unconditional seed rows and gated non-seeds |
| `gene_n_diseases` | label-derived gene-popularity shortcut; can outperform the real model for the wrong reason |
| `disease_context`, `module_size` | per-disease count/base-rate encoders |
| `dwpc_GCD` | circular for target identification; post-hoc evidence only |
| raw centralities and triangles | collinear gene-only duplicates of degree |
| `ppi_common_neighbors`, `shared_pathway_count` | redundant with normalised retained forms |
| `has_inflammatory_go_annotation` | sparse binary flag with no measured ranking value |
| family, anchor and hop fields | split bookkeeping and direct leakage |

Two reusable rules follow. Reject a feature when label lookup controls its missingness, not merely
because it correlates with the label. Avoid per-disease counts; use gene-to-module relational features.

### 3.3 Computation

Functional metapaths use sparse matrix multiplication rather than graph queries because graph-engine
path materialisation exhausted memory even with fan-out guards. The factorisation associates from
right to left and never forms the gene-by-gene matrix:

```text
S = X @ (W_A @ (X.T @ (W_m @ Z)))
X: genes × annotations; Z: genes × diseases
```

Self-path exclusion and leave-one-out module size are handled analytically. This is an implementation
choice that preserves the same mathematical path score.

## 4. Training and scoring

| setting | method |
|---|---|
| algorithm | gradient-boosted trees |
| depth | grid 4–6 |
| estimators | 300 with early stopping |
| class handling | class weights for the rare positive label |
| seed | 1337 |
| train/test policy | explicit family-safe train, validation and test datasets |
| explanation | SHAP on scored candidates |

Every numeric input uses standard rescaling and mean imputation. Rescaling is operationally neutral
for trees but keeps the comparator consistent. Mean imputation is load-bearing: it places nulls near
the distribution centre so a tree cannot cleanly isolate “was missing”. Constant-zero or sentinel
imputation made the missingness channel separable and improved association metrics while degrading
therapeutic agreement; those alternatives were rejected.

`prox_closest` is a semantic exception only in the sense that “unreached within the hop limit” belongs
beyond the largest observed distance. Its constant-four candidate was compared against mean
imputation, then superseded by the graded kernel path. The historical comparison is retained in
[VALIDATION.md](VALIDATION.md), not copied here.

The F1-optimised classification threshold is not the deliverable. Severe class imbalance makes the
binary prediction column discard many known targets. Candidate use is probability rank and top-N;
threshold metrics are diagnostic only.

## 5. Model-selection rule

Model choice is a four-axis review, not an AUROC leaderboard:

1. association ranking (macro per-disease AUROC and AUPRC);
2. hub-bias spread among known targets;
3. therapeutic agreement under both all-positive and route-supported estimands;
4. discovery and tractability enrichment, including a degree-matched null.

Report exact ties before means and use stratified paired tests. Small macro differences in this
project often come from a handful of high-leverage diseases while most ranks are identical.

The adoption rule is: **an association gain must be corroborated on the degree-matched axis, or it is
not adopted.** This is why `m8` was rejected despite higher AUPRC, and why `m7-f14` remains champion.
The current governed identity is `TI-MOD-001`; the full historical comparison and its negative results
are in [VALIDATION.md](VALIDATION.md#4-historical-model-evidence-preserved-for-review).

The same evidence discipline applies to mechanisms. The proposed sparse-disease rescue for `m6` and
module-size saturation explanation for `m7` were both refuted. A model may be adopted on paired,
multi-axis evidence without pretending its causal explanation was confirmed.

## 6. Seed-gate boundary

Seed floors serve different purposes and must not share one unexplained constant:

- nearest distance needs enough seeds to avoid self-exclusion becoming a label indicator;
- random walk needs enough seeds for non-empty held-out folds;
- GO metapaths need leave-one-out correctness and also affect the candidate population.

Lowering a feature-computation floor while holding the pool fixed is a model experiment. Lowering a
pool-route gate changes the population, denominators and every downstream claim. The latter must
follow [PHASE3_PREREGISTRATION.md](PHASE3_PREREGISTRATION.md) in an approved duplicated project; it is
not an in-place documentation or model refresh.

## 7. References

Per-reference summaries, the feature-to-reference map and provenance caveats are in
[RESEARCH_NOTE.md](../reference/RESEARCH_NOTE.md). Verify that unvalidated corpus before client-facing
use.

- Mountjoy et al., *Nature Genetics* (2021), Locus-to-Gene.
- Guney et al., *Nature Communications* (2016), network proximity.
- Menche et al., *Science* (2015), disease modules and incomplete interactomes.
- Himmelstein et al., *eLife* (2017), degree-weighted path counts.
- Huang et al., *Nature Medicine* (2024), path-explanation interpretability.
- Minikel et al., *Nature* (2024), genetic support and clinical success.
