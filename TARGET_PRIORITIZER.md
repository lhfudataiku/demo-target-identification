# Explainable Target Prioritizer — Part 2 Flagship Design

> **Companion to [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) and [PRIMEKG_MAPPING.md](PRIMEKG_MAPPING.md).**
> Those two build the *substrate* (the PrimeKG-style graph) and the *explorer* (Visual
> Graph plugin). This doc specifies the **analytical layer on top** — the Part 2 work
> that turns "here is the graph" into "here is a ranked, explained answer to a bench
> scientist's question." It is the *design* view; recipes are not built yet.
>
> Status: **DESIGN — awaiting build sign-off.** Nothing in the flow yet.

## 1. Purpose & scope

Demonstrate POC value narrative **(a) discovery of novel targets** (PROJECT_CONTEXT §2)
by building an **Explainable Target Prioritizer**: for a disease, produce a ranked
shortlist of candidate gene/protein targets, each with a calibrated score **and two
complementary explanations** — a SHAP feature attribution ("*which evidence* drove this")
and the **graph path** to the disease module rendered on the Visual Graph ("*show me the
mechanism*").

**In scope (this pass):** value-prop **(a)** only, **network-topology features only**,
on the **graph we already have — no new data sources.**

**Deferred (follow-on, not this pass):** value-prop **(b)** off-target toxicity / safety
(DepMap essentiality + GTEx tissue expression → efficacy×safety "traffic light"; SIDER
ADR / Decagon-style off-target). Also deferred: KG-embedding (PyKEEN) features. See §11.

**Roadmap consequence:** this analytical layer is prioritized **ahead of Task 10**
(GO+HPO source ingestion) — a *more valuable* graph beats a *bigger* graph for the demo.
GO/pathway annotations can later enrich the feature set (§11).

## 2. What it delivers (the demo)

For a persona disease (breast cancer / obesity), the output dataset `target_candidates`
is a ranked table:

| candidate gene | score (0–1) | top SHAP drivers | top evidence path |
|---|---|---|---|
| e.g. *novel gene X* | 0.87 | prox_closest, shared PI3K pathway | X –PPI– AKT1 –assoc– breast cancer |

Top-ranked genes **not currently linked** to the disease are the novel target hypotheses.
The candidate + its evidence path highlight on the **Visual Graph Editor** (`lVWgU2m`).

## 3. Scientific basis & precedent

This is a well-trodden method family; we reproduce the industry-standard pattern, not
invent one.

- **Supervised target prioritization = the Open Targets standard.** Open Targets'
  Locus-to-Gene (L2G) is a **gradient-boosting (XGBoost) + SHAP** tabular model trained on
  a gold-standard positive set — *not* a GNN. It emits a calibrated 0–1 causal-gene score
  and explains predictions with per-feature SHAP attributions. Directly transferable to
  Dataiku Visual ML. (Mountjoy et al., *Nat Genet* 2021; OT Platform docs.)
- **Network proximity / guilt-by-association** (our feature backbone). Disease genes
  cluster in the interactome ("disease modules"); a gene's network proximity to a disease
  module predicts association. Guney et al. (*Nat Commun* 2016): the closest-distance
  proximity z-score classifies indications at AUC ≈ 81%, and network-proximal drugs are
  ~2× more likely to be effective (OR 2.1). Menche et al. (*Science* 2015) established
  disease modules and the incomplete-interactome caveat (~80% of interactions unmapped).
- **Meta-path / degree-weighted path count (DWPC)** (Himmelstein et al., Project Rephetio,
  *eLife* 2017): typed path counts over a heterogeneous network, fed to a regularized
  logistic model → interpretable path evidence per prediction.
- **Interpretability is the adoption driver.** TxGNN (built on PrimeKG; *Nat Med* 2024): a
  usability study with 12 domain experts found path explanations raised **accuracy +46%
  and confidence +49%**. This is why we pair SHAP with an on-graph evidence path.

## 4. ML formulation

**Supervised link-prediction framed as binary classification over gene–disease pairs**
(the L2G / Rephetio pattern), a single global model.

- **Unit of prediction:** a `(gene, disease)` pair → P(true `disease_protein` association).
- **Positives:** existing `disease_protein` edges (173,442 in the current graph),
  restricted to **training diseases** with a sufficient module (≥ ~20 protein seeds) so
  network features are estimable.
- **Negatives:** sampled non-edge `(gene, disease)` pairs, **degree-matched** to positives
  (sample negative genes with degree similar to the positive gene, not linked to that
  disease). Ratio ~1:3. This stops the model from learning the trivial "hub gene = target"
  shortcut. Node degree is *also* kept as an explicit control feature.
- **Model:** Dataiku **Visual ML** binary classifier — **XGBoost** primary (random-forest
  / logistic as comparators), nested CV, **probability calibration**, built-in **Shapley**
  for per-prediction attribution.

## 5. Feature engineering (network-topology only)

Most features are computed **not** in hand-written `networkx`, but with the **Visual Graph
plugin's own recipes** over the materialized **Kuzu** graph (folder `AGwGm7CN`, built by the
existing `build-graph-hTMbed` recipe — §7). This is a more no-code, plugin-native path that
also dogfoods POC highlight #2. Only `rwr_score` stays Python — no installed plugin offers
seeded PageRank (§11). `G`=gene/protein, `D`=disease, `P`=pathway, `C`=drug. Module
aggregations use {mean, max} unless noted.

| Feature | Layer(s) | Computed by | Definition |
|---|---|---|---|
| `gene_degree`, `gene_ppi_degree`, centrality (`closeness`, `eigenvector`, `clustering`) | all / PPI | **Graph Features** recipe | one recipe → per-node metric columns; hubness controls + extra centralities for free |
| `gene_n_diseases` | disease_protein | Execute Cypher / Prepare | # diseases the gene is linked to |
| `prox_closest` | PPI | **Execute Cypher** | shortest-path length from `g` to nearest module gene (raw — z-score dropped, see below) |
| `ppi_common_neighbors`, `ppi_adamic_adar`, `ppi_jaccard` | PPI | **Execute Cypher** | neighbor-set overlap of `g` with module genes (Adamic-Adar weights by node degree in-query) |
| `dwpc_GGD` | PPI + disease_protein | **Execute Cypher** | degree-weighted path count `g –PPI– gene –assoc– D` |
| `dwpc_GPGD` | pathway_protein + disease_protein | **Execute Cypher** | `g –in– P –contains– gene –assoc– D` (shared-pathway route) |
| `dwpc_GCD` | drug_protein + indication/investigated | **Execute Cypher** | `g –targeted by– C –for– D` |
| `shared_pathway_count`, `_frac` | pathway_protein | **Execute Cypher** *or* **Projected Graph** | pathways of `g` overlapping module pathways (projection gives a ready gene–gene weight) |
| `disease_context` | disease_disease + disease_protein | **Execute Cypher** | # of `D`'s `disease_disease`-neighbors that `g` is associated with |
| `rwr_score` | PPI (+ pathway) | **Python** (`networkx`, ~5 lines) | personalized PageRank seeded on the module — *not* a plugin recipe (§11) |
| `module_size` | disease_protein | Cypher / Prepare | # of `D`'s protein seeds (feature-quality context) |

- **DWPC** uses the standard degree-damping exponent (w ≈ degree^−0.4); Kuzu-Cypher computes
  node degrees in-query for the weighting. Path queries must use **Kuzu-Cypher** syntax
  (variable-length paths differ from Neo4j — §7).
- **Proximity z-score dropped.** Because the *supervised* model already sees explicit degree
  features, we feed the **raw** Cypher shortest-path distance and let XGBoost absorb hubness —
  avoiding the Guney degree-matched randomization (the annoying Python piece). The z-score
  matters for the *unsupervised* proximity test, not inside a model that sees degree directly.
- **KGE triple-score features deferred** (§11) — pure topology, no extra code-env deps.

## 6. Correctness crux (the two things that make it honest)

1. **Leakage control — edge masking.** When computing features for a *positive* pair
   `(g, D)`, `g`'s own `disease_protein` edge to `D` **must be removed** from the graph and
   `g` excluded from the module seed set — otherwise proximity/DWPC trivially leak the
   label (distance 0, a direct path). Implement leave-one-out: the module used to score `g`
   is `D`'s genes **minus `g`**. With **Execute Cypher** this is clean — leave-one-out is a
   `WHERE NOT (g)-[:assoc]-(D)` predicate inside each feature query, so no graph copy or
   rebuild is needed (unlike `networkx`).
2. **Validation — held-out edge recovery.** Split each validation disease's seed genes into
   *seed* (defines the module) and *held-out* (hidden positives). Report **Recall@K** and
   **AUC-ROC** on recovering held-out genes among all candidates, and require it to beat a
   **degree-only baseline** (guard against the hubness shortcut). This is the quantitative
   proof the model finds signal beyond "popular gene."
3. **Scale — candidate pruning.** All 18,002 × 24,917 pairs ≈ **449M** is infeasible and
   pointless. For a disease `D`, candidate genes = those **within ~2 hops of the module**
   over PPI ∪ genes sharing a pathway with the module (a few thousand, given modules of
   200–700 seeds). Training uses a sample of training diseases; scoring targets the two
   persona diseases (all candidates) + held-out validation diseases.

## 7. Flow design (zoned-hybrid, plugin-recipe-based)

New flow zone **"Target Prioritization (ML)"**. It **reuses the existing materialized Kuzu
graph** (`build-graph-hTMbed` → folder `AGwGm7CN`, `/built-graphs/hTMbed/db.kz`, which also
powers webapp `lVWgU2m`); feature computation is pushed into Visual Graph plugin recipes,
leaving one thin Python step.

```
graph_nodes/graph_edges ─▶ [Build Graph]* ─▶ AGwGm7CN  (Kuzu db.kz; *already built)
                                                │
     ┌─────────────────────────┬────────────────┴──────────┬───────────────────────┐
[Graph Features]        [Execute Cypher ×N]          [Projected Graph]        [PY] rwr_score
per-node metrics        pair/path features           shared-pathway sim       networkx seeded
(degree, centralities)  (prox, CN/AA/Jaccard, DWPC,  (optional)               PageRank — the
     │                   disease_context, candidate       │                    only Python left
     │                   generation, edge-masking)        │                        │
     └───────────────┬────────────┴─────────────────────────┴──────────────────────┘
                 [Join] ─▶ gd_pair_features (features + label) ─▶ [Visual ML + Shapley] ─▶ model
                                                                        │
                    [score] ─▶ gd_pair_scored ─▶ [Prepare/Join names] ─▶ target_candidates
                                                                        │
                 [Execute Cypher] ─▶ target_evidence_paths (top path per candidate → Visual Graph)
```

- **Plugin recipes do the graph math** (Graph Features + Execute Cypher over Kuzu); Python
  shrinks to the single `rwr_score` step. Name attachment / ranking are visual Prepare + Join.
- **Verified runnable here** (2026-07-08): Build Graph executed via container conf `default`
  and produced the Kuzu graph; Graph Features / Execute Cypher are the same plugin + code-env
  + container path. Engine is **Kuzu → write Kuzu-Cypher** (variable-length path syntax
  differs from Neo4j).
- **Edge-masking is a query predicate** (§6), not a graph rebuild.
- **Build gotchas apply** (PRIMEKG_MAPPING §8): keep ids string; delete a stale output before
  recreating its recipe; visual multi-input Join is a **star**. Plugin recipes need
  `params.customConfig` + `params.containerSelection` (else NPE) — mirror `build-graph-hTMbed`.
- **Remaining build-time unknown:** each plugin recipe's exact `customConfig` keys and
  input-role names (learned by inspecting the plugin's `recipe.json` or first-run iteration);
  recipe *execution* itself is verified.
- Code env `primekg_kg` already has `networkx` — no new dependency for the `rwr_score` step.

## 8. Interpretability (two lenses, matching the TxGNN finding)

- **SHAP** (native in Dataiku Visual ML): per-candidate feature attribution — "this gene
  scored high because of proximity to the module *and* shared PI3K pathway."
- **Graph path** (`target_evidence_paths` → Visual Graph, produced by an **Execute Cypher**
  recipe): the shortest path / top-DWPC path from candidate to the disease module,
  highlighted on webapp `lVWgU2m`. The mechanistic chain a wet-lab scientist can act on.

## 9. Demo narrative per persona

- **Obesity / metabolic (persona 1).** Mask known obesity genes → model recovers
  LEP/LEPR/PPARG; the network layer then **surfaces inflammatory genes (IL6/TNF/IL1B)**
  that our `genetic_association`-only `disease_protein` edges under-represent (see
  PRIMEKG_MAPPING §5 — TNF 34→1 under genetic-only). PPI/pathway topology *recovers*
  targets the genetic layer alone misses → a concrete "the graph adds value" story.
- **Breast cancer (persona 2).** Recovers PIK3CA/AKT1/MTOR/PTEN/ESR1; surfaces novel
  candidates in the PI3K/AKT/mTOR neighborhood.

## 10. Feasibility grounding (live graph, checked 2026-07-08)

- Graph: **51,084 nodes** (24,917 disease · 18,002 gene/protein · 5,282 drug · 2,883
  pathway) / **724,894 undirected edges** (protein_protein 275,726 · disease_protein
  173,442 · pathway_protein 97,618 · disease_disease 77,292 · drug_investigated_for 69,682
  · drug_protein 15,918 · indication 9,418 · pathway_pathway 5,798).
- **All 20 persona anchor genes present & well-connected** (TP53 deg 583, ESR1 401, BRCA1
  334, AKT1 281, ERBB2 198, PIK3CA 166; PPARG 140, INSR 137, INS 53, IL6 45, GLP1R 33,
  LEPR 32).
- **Large disease modules** (protein seed-sets): obesity disorder 744, breast carcinoma
  284, breast cancer 233, morbid obesity 108, ER+ breast cancer 76. Ample signal for
  proximity/RWR/supervised methods with zero new data.

## 11. Open decisions & deferrals

- **Value-prop (b) toxicity/safety** — deferred. When resumed: DepMap CRISPR essentiality
  + GTEx/Bgee tissue-restricted expression as **per-gene node features** → efficacy×safety
  traffic light (mirrors OT Target Prioritisation). SIDER → ADR/off-target link prediction
  (Bean et al. 2017 template; Decagon). All free adds; per-gene feature layer, not new
  graph topology.
- **KGE features** — deferred. PyKEEN (CPU-fine at 725k triples) TransE/ComplEx triple
  score as one more feature; needs `pykeen` in the code env.
- **GO annotations** (from Task 10) would add molecular-function / biological-process
  features to §5.
- Negative-sampling ratio and DWPC metapath set to be tuned during the feature prototype.
- **Plugin recipe schemas** — the exact `customConfig`/input-role structure for the Graph
  Features and Execute Cypher recipes is the only remaining build-time unknown; recipe
  *execution* on this instance is verified (§7). Mirror `build-graph-hTMbed`'s params shape.

## 12. Decision log

- 2026-07-08 — Part 2 flagship = **Explainable Target Prioritizer** (Visual ML + SHAP,
  L2G-analog). Scope = **discovery (a) first**; toxicity (b) deferred.
- 2026-07-08 — First model = **network-topology features only** (no KGE).
- 2026-07-08 — **Design doc first** before any build (this doc).
- 2026-07-08 — Feature engineering pushed into **Visual Graph plugin recipes** (Graph
  Features + Execute Cypher over the existing Kuzu graph `AGwGm7CN`) instead of monolithic
  `networkx`; only `rwr_score` stays Python. **Verified:** plugin recipes run here (Build
  Graph executed via container conf `default`; engine is **Kuzu**).
- 2026-07-08 — Confirmed **neither `visual-graph` nor `graph-analytics` exposes
  seeded/personalized PageRank** → RWR remains a Python step.
- 2026-07-08 — Proximity uses **raw Cypher shortest-path + degree features** (Guney
  degree-matched z-score dropped) — the supervised model absorbs hubness.

## References

- Open Targets L2G — Mountjoy et al., *Nat Genet* 2021; https://platform-docs.opentargets.org/gentropy/locus-to-gene-l2g
- Open Targets Target Prioritisation — https://platform-docs.opentargets.org/web-interface/target-prioritisation
- Network proximity — Guney, Menche, Vidal, Barabási, *Nat Commun* 2016; https://www.nature.com/articles/ncomms10331
- Disease modules / incomplete interactome — Menche et al., *Science* 2015; https://pmc.ncbi.nlm.nih.gov/articles/PMC4435741/
- Meta-path / DWPC — Himmelstein et al. (Rephetio), *eLife* 2017; https://elifesciences.org/articles/26726
- TxGNN (interpretability) — Huang et al., *Nat Med* 2024; https://www.nature.com/articles/s41591-024-03233-x
- NetMedPy (proximity/separation toolkit) — *Bioinformatics* 2025
- MultiXrank (RWR multilayer) — *BMC Bioinformatics* 2024
