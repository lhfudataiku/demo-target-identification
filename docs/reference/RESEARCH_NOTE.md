# Research Note — evidence behind the Target Prioritizer's features & model

> **Companion to [TARGET_PRIORITIZER.md](../prioritizer/TARGET_PRIORITIZER.md).** That doc is the *design*
> (what we build). This note is the *evidence*: per-reference summaries with the methodology
> mapped to each feature and modeling choice — the "why these features" audit trail.

## Provenance & caveat (read first)

Assembled from a **deep-research** pass (2026-07-08): 5 search angles → 23 primary/secondary
sources → **109 extracted claims-with-quotes**. The **adversarial validation phase was cut
short by an org spend limit**, so — except where noted — these are **single-source,
extracted-but-unvalidated** claims, *not* independently vetted facts. Most load-bearing items
are landmark results corroborated from established knowledge; specific figures are stated
"as reported."

- **Only independently verified (3-0):** the TxGNN interpretability findings.
- **Decision (see TARGET_PRIORITIZER §12 / this session):** validation was *deliberately not*
  finished — the claims driving the design are landmark or already-verified, and the real
  proof for our purpose is the prototype's held-out edge-recovery, not literature figures.
- **Before any client/account-facing use, verify the specific claims you cite.** The raw
  109-claim corpus lives in the workflow journal
  (`…/subagents/workflows/wf_8a29720e-87a/journal.jsonl`).

---

## 1. The feature rationale (the conceptual spine)

Every feature answers one question a different way: **how is a candidate gene related to the
set of genes already known to be involved in this disease (the disease "module")?** Four
complementary, non-redundant views + controls + an explainable wrapper:

1. **How close?** → shortest-path proximity (`prox_closest`) — *Guney / Menche*
2. **How reachable by diffusion?** → random-walk-with-restart (`rwr_score`) — *MultiXrank*
3. **How many typed mechanistic paths connect them?** → degree-weighted path counts
   (`dwpc_*`) — *Rephetio / Himmelstein*
4. **How much direct neighbor / pathway overlap?** → common-neighbor & shared-pathway
   features — *Menche guilt-by-association*
5. **Controls** → degree / centrality, so the model discounts promiscuous hubs.
6. **Wrapper** → supervised ranker + SHAP (*L2G*) with graph-path evidence (*TxGNN*).

Using all of views 1–4 (not just one) is what lets the model recover targets any single lens
would miss — e.g. the obesity inflammatory genes (TNF/IL6/IL1B) sparse under `genetic_association`
but recoverable via PPI/pathway topology (TARGET_PRIORITIZER §9).

## 2. Feature-defining references

**Menche et al., *Science* 2015 — disease modules & the incomplete interactome**
([PMC4435741](https://pmc.ncbi.nlm.nih.gov/articles/PMC4435741/))
- *Summary:* Built a human interactome (~141,296 interactions among ~13,460 proteins) and
  showed disease-associated genes are not scattered but form a connected **disease module**
  (statistically significant for 226 of 299 diseases). Introduced network separation **S_AB**
  between modules (correlates with comorbidity/co-expression) and quantified the interactome
  as **~80% incomplete**.
- *→ Our features:* Foundational premise — licenses treating a disease's `disease_protein`
  genes as a module. Backs the guilt-by-association features `ppi_common_neighbors`,
  `ppi_adamic_adar`, `ppi_jaccard`, and `disease_context`. The incompleteness caveat is *why*
  we don't rely on proximity alone.

**Guney, Menche, Vidal & Barabási, *Nat Commun* 2016 — network proximity**
([ncomms10331](https://www.nature.com/articles/ncomms10331))
- *Summary:* Defined **network proximity** between two node sets as the average shortest-path
  distance to the nearest module gene, **z-scored against a degree-preserving null**. The
  "closest" measure classified indications at **AUC ≈ 81%** (vs ~71% shortest-path), and
  proximal drugs were **~2× more likely** effective (OR ≈ 2.1). Ref impl `github.com/emreg00/toolbox`.
- *→ Our feature:* Defines `prox_closest`. **Adaptation:** we feed the **raw** closest distance
  + explicit degree features and let XGBoost absorb hub bias, dropping the degree-matched
  z-score (redundant inside a supervised model that already sees degree).

**Himmelstein et al. (Project Rephetio), *eLife* 2017 — meta-path / DWPC**
([eLife 26726](https://elifesciences.org/articles/26726); data: [Hetionet](https://github.com/hetio/hetionet))
- *Summary:* On a heterogeneous network, enumerated **~1,206 typed metapaths** and computed the
  **degree-weighted path count (DWPC)** — path counts down-weighted by intermediate-node
  degree (damping ≈ 0.4) — then fit a cross-validated **elastic-net logistic** (reduced to
  ~31 features) to score drug–disease edges, each decomposable into supporting **path evidence**.
- *→ Our features:* Defines `dwpc_GGD`, `dwpc_GPGD`, `dwpc_GCD` (gene→disease via PPI / shared
  pathway / shared drug) and the whole "features → interpretable model → path evidence"
  pattern. **Adaptation:** a handful of metapaths via Kuzu-Cypher, XGBoost instead of elastic-net.

**MultiXrank, *BMC Bioinformatics* 2024 — RWR on multilayer networks**
([s12859-024-05683-z](https://link.springer.com/article/10.1186/s12859-024-05683-z))
- *Summary:* Generalized **random-walk-with-restart / personalized PageRank** to multilayer
  heterogeneous networks: known disease genes seed the walk, which ranks all nodes by
  topological closeness. Showed **RWR scores used directly as features** into XGBoost/RF reach
  BA ≈ 0.85 / F1 ≈ 0.79 on held-out gene–disease associations — our exact pipeline shape.
- *→ Our feature:* Defines `rwr_score`. Direct precedent for RWR-scores-as-features; since no
  installed plugin offers *seeded* PageRank, `rwr_score` stays a small `networkx` step.

**NetMedPy, *Bioinformatics* 2025 — network-medicine toolkit**
([btaf338](https://academic.oup.com/bioinformatics/article/41/9/btaf338/8165428))
- *Summary:* MIT-licensed Python package implementing the Menche/Guney primitives —
  LCC/localization significance, **proximity** (closest/shortest/centre), **S_AB separation** —
  over a NetworkX interactome with degree-matched nulls.
- *→ Our design:* The reference/fallback implementation proving `prox_closest`-style features
  are a solved, pip-installable computation (we implement the equivalent in Cypher/Python).

## 3. Model & interpretability references

**Mountjoy et al., *Nat Genet* 2021 — Open Targets Locus-to-Gene (L2G)**
([s41588-021-00945-5](https://www.nature.com/articles/s41588-021-00945-5);
[L2G docs](https://platform-docs.opentargets.org/gentropy/locus-to-gene-l2g))
- *Summary:* Production supervised **gradient-boosting (XGBoost)** classifier, trained on ~445
  curated gold-standard loci, integrating graph/genomics features, emitting a **calibrated
  0–1 score** explained with **per-feature SHAP** attributions.
- *→ Our model:* The template for the entire ML formulation (TARGET_PRIORITIZER §4) — learn a
  ranker from graph-derived features against a positive set, calibrated score, SHAP. Why the
  flagship is XGBoost+SHAP (CPU, interpretable, Dataiku-native), not a GNN.

**Open Targets Platform — Target Prioritisation & association scoring**
([Target Prioritisation](https://platform-docs.opentargets.org/web-interface/target-prioritisation);
[associations](https://platform-docs.opentargets.org/associations);
[Platform NAR 2025](https://academic.oup.com/nar/article/53/D1/D1467/7917960);
[ML blog](https://blog.opentargets.org/machine-learning-for-drug-target-identification-and-prioritisation-at-open-targets/))
- *Summary:* Multi-factor **"traffic-light"** ranking (Precedence, Tractability, Doability,
  Safety), each independently scored (Safety uses DepMap essentiality + GTEx tissue
  specificity); plus a transparent weighted **harmonic-sum** association score that decomposes
  into per-datatype evidence.
- *→ Our design:* Confirms the design principle that a bench scientist wants a *decomposable,
  per-factor* output (our SHAP breakdown). The safety/tractability factors inform the
  **deferred value-prop (b)**.

**Huang et al. (TxGNN), *Nat Med* 2024 — clinician-centered repurposing on PrimeKG**
([s41591-024-03233-x](https://www.nature.com/articles/s41591-024-03233-x))
- *Summary:* R-GCN-style GNN trained **directly on PrimeKG** (our schema) for zero-shot
  drug–disease prediction; its Explainer surfaces **multi-hop KG paths** as rationale.
  **[Verified 3-0]** a 12-expert usability study found path explanations raised **accuracy
  +46% and confidence +49%**.
- *→ Our design:* We deliberately don't copy the GNN (heavy, less interpretable low-code). We
  take its strongest finding — **interpretability drives expert adoption** — as the
  justification for the second explanation lens, the on-graph evidence path (`target_evidence_paths`).

## 4. Feature → reference map

| Feature(s) / choice | Method | Reference |
|---|---|---|
| `prox_closest` (raw distance; z-score dropped) | network proximity | Guney 2016; Menche 2015 |
| `ppi_common_neighbors`, `_adamic_adar`, `_jaccard`, `disease_context` | disease module + guilt-by-association | Menche 2015 |
| `dwpc_GGD`, `dwpc_GPGD`, `dwpc_GCD` | degree-weighted metapath counts | Himmelstein 2017 |
| `rwr_score` | seeded random-walk-with-restart | MultiXrank 2024 |
| `gene_degree`, centralities, `module_size` | hubness controls | Guney null-model rationale |
| **model** (XGBoost + SHAP, calibrated, gold-standard positives) | supervised target prioritization | Mountjoy 2021 / L2G |
| **interpretability** (graph-path evidence lens) | multi-hop path rationale | TxGNN 2024 |

## 5. References informing *deferred* / *not-chosen* decisions

Captured so the "why not X" is documented, not lost.

- **KGE / GNN link prediction — deferred to a later feature pass.**
  *KGE gene–disease benchmark* ([arXiv 2504.08445](https://arxiv.org/abs/2504.08445)),
  *PyKEEN* ([repo](https://github.com/pykeen/pykeen)),
  *KG-enhanced tensor factorization* ([arXiv 2105.10578](https://arxiv.org/abs/2105.10578)),
  *BioPathNet* ([Nat Biomed Eng 2025](https://www.nature.com/articles/s41551-025-01598-z)).
  These embed nodes / reason over paths with neural models — more "AI," less interpretable and
  heavier than the first topology-only pass. `rwr_score` + `dwpc_*` capture much of the same
  multi-hop signal transparently. KGE (PyKEEN, CPU) is the natural next feature to add.
- **Value-prop (b) off-target toxicity / safety — deferred follow-on.**
  *DepMap* ([Cancer Cell 2023](https://www.sciencedirect.com/science/article/pii/S1535610823004440)) —
  CRISPR essentiality; *Decagon* ([Bioinformatics 2018](https://academic.oup.com/bioinformatics/article/34/13/i457/5045770)) —
  polypharmacy side-effect GNN; *Bean et al.* ([Sci Rep 2017](https://www.nature.com/articles/s41598-017-16674-x)) —
  ADR prediction from a drug-target-ADR KG (AUC 0.92). Add DepMap + GTEx (per-gene features) →
  efficacy×safety traffic light; SIDER → ADR link prediction.
- **Industry landscape (positioning).**
  *Insilico PandaOmics* ([PubMed](https://pubmed.ncbi.nlm.nih.gov/38404138/)),
  *BenevolentAI baricitinib* ([Front Pharmacol 2021](https://www.frontiersin.org/journals/pharmacology/articles/10.3389/fphar.2021.709856/full)),
  *NVIDIA BioNeMo* ([blog](https://blogs.nvidia.com/blog/drug-discovery-bionemo-generative-ai/)).
  BioNeMo/Recursion = GPU-scale generative chemistry — deliberately *not* our lane; our
  differentiation is interpretable, governed, low-code KG reasoning.

## 6. Full source index (23)

| # | Source | Quality | Role |
|--:|---|---|---|
| 1 | [TxGNN — *Nat Med* 2024](https://www.nature.com/articles/s41591-024-03233-x) | primary | model/interpretability ✅verified |
| 2 | [KGE gene–disease benchmark — arXiv 2025](https://arxiv.org/abs/2504.08445) | primary | deferred (KGE) |
| 3 | [PyKEEN](https://github.com/pykeen/pykeen) | primary | deferred (KGE tool) |
| 4 | [KG tensor factorization — arXiv 2022](https://arxiv.org/abs/2105.10578) | primary | deferred (KGE) |
| 5 | [BioPathNet — *Nat Biomed Eng* 2025](https://www.nature.com/articles/s41551-025-01598-z) | primary | deferred (path-GNN) |
| 6 | [Network proximity — *Nat Commun* 2016](https://www.nature.com/articles/ncomms10331) | primary | **feature: `prox_closest`** |
| 7 | [Rephetio — *eLife* 2017](https://elifesciences.org/articles/26726) | primary | **feature: `dwpc_*`** |
| 8 | [Disease modules — *Science* 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4435741/) | primary | **feature: guilt-by-association** |
| 9 | [NetMedPy — *Bioinformatics* 2025](https://academic.oup.com/bioinformatics/article/41/9/btaf338/8165428) | primary | feature toolkit |
| 10 | [MultiXrank — *BMC Bioinf* 2024](https://link.springer.com/article/10.1186/s12859-024-05683-z) | primary | **feature: `rwr_score`** |
| 11 | [Hetionet](https://github.com/hetio/hetionet) | primary | Rephetio data resource |
| 12 | [Open Targets ML blog](https://blog.opentargets.org/machine-learning-for-drug-target-identification-and-prioritisation-at-open-targets/) | blog | model context |
| 13 | [L2G docs](https://platform-docs.opentargets.org/gentropy/locus-to-gene-l2g) | primary | **model template** |
| 14 | [Mountjoy L2G — *Nat Genet* 2021](https://www.nature.com/articles/s41588-021-00945-5) | primary | **model template** |
| 15 | [Open Targets Platform — *NAR* 2025](https://academic.oup.com/nar/article/53/D1/D1467/7917960) | primary | platform benchmark |
| 16 | [OT Target Prioritisation](https://platform-docs.opentargets.org/web-interface/target-prioritisation) | primary | model + deferred (b) |
| 17 | [OT association scoring](https://platform-docs.opentargets.org/associations) | primary | scoring transparency |
| 18 | [Decagon — *Bioinformatics* 2018](https://academic.oup.com/bioinformatics/article/34/13/i457/5045770) | primary | deferred (b) |
| 19 | [Bean ADR KG — *Sci Rep* 2017](https://www.nature.com/articles/s41598-017-16674-x) | primary | deferred (b) |
| 20 | [DepMap — *Cancer Cell* 2023](https://www.sciencedirect.com/science/article/pii/S1535610823004440) | primary | deferred (b) |
| 21 | [Insilico PandaOmics — PubMed](https://pubmed.ncbi.nlm.nih.gov/38404138/) | primary | landscape |
| 22 | [BenevolentAI — *Front Pharmacol* 2021](https://www.frontiersin.org/journals/pharmacology/articles/10.3389/fphar.2021.709856/full) | primary | landscape |
| 23 | [NVIDIA BioNeMo](https://blogs.nvidia.com/blog/drug-discovery-bionemo-generative-ai/) | blog | landscape |

*Raw 109-claim corpus (unmapped, unvalidated): workflow journal
`…/subagents/workflows/wf_8a29720e-87a/journal.jsonl`.*
