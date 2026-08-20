# Feature recipe audit — §4.1 and §4.2

Every recipe producing a feature in TARGET_PRIORITIZER §4.1 (the champion's 12) and §4.2 (computed
and rejected), read for four things: **the module-size threshold**, **self-path exclusion**,
**leave-one-out module normalisation**, and **null semantics**. Audited 2026-08-20.

---

## 1. The headline: one constant gates 7 of the 12 champion features

`module_size >= 20` is not a `prox_closest` quirk. It appears in **ten recipes**, and gates **seven of
the twelve champion inputs**:

| Recipe | Form | Features it gates | In champion? |
|---|---|---|:--|
| `compute_enriched_dwpc_GGD` | Cypher `module_size >= 20` | `dwpc_GGD` | ✅ |
| `compute_enriched_dwpc_GPGD` | Cypher `module_size >= 20` | `dwpc_GPGD` | ✅ |
| `compute_dwpc_go_metapaths` | `MIN_MODULE = 20` | `dwpc_GBGD`, `dwpc_GFGD` | ✅ ✅ |
| `compute_enriched_guilt_by_association_1` | Cypher `module_size >= 20` | `ppi_adamic_adar`, `ppi_jaccard`, `ppi_common_neighbors` | ✅ ✅ |
| `compute_enriched_shared_pathway_count_1` | Cypher `module_size >= 20` | `shared_pathway_frac`, `shared_pathway_count` | ✅ |
| `compute_enriched_prox_closest` | `MIN_SEEDS = 20` | `prox_closest` | m4/m5 |
| `compute_enriched_rwr_score_1` | `MIN_SEEDS = 20` + `KFOLD = 5` | `rwr_score`, `rwr_norm` | ✗ |
| `compute_enriched_dwpc_GCD` | Cypher `module_size >= 20` | `dwpc_GCD` | ✗ (but a pool route) |
| `compute_enriched_disease_context_1` | Cypher `module_size >= 20` | `disease_context` | ✗ |
| `compute_enriched_module_size_1` | Cypher `module_size >= 20` | `module_size` | ✗ |

**Not gated** (gene-level, so no disease module involved): `compute_enriched_degree_controls_1`
(`gene_ppi_degree`, `gene_n_diseases`, `gene_n_pathways`), `compute_ppi_cn_zscore`
(`ppi_common_neighbors_z`), `compute_ppi_evidence_depth` (`ppi_evidence_depth`,
`ppi_multi_source_frac`).

### What that means for the 43 excluded diseases

Those diseases have **7 of 12 champion features NULL**, leaving only the five gene-level ones — and
§6.1 measured that `gene_ppi_degree` and `gene_n_pathways` show **0.00% variation across diseases**.

> **For 43 diseases (1.23% of pool rows) the model has no disease-specific signal at all. It is
> ranking them on gene prominence.** That is not degraded performance — it is a different, unstated
> model being served for 3.7% of the disease population.

---

## 2. Leakage handling — correct everywhere it matters

The open question from the last review — whether the GO metapath counts a gene's path to its own
disease — is **answered, and that recipe is the most careful of the set.**

| Recipe | self-path excluded (`m <> g`) | LOO module size | verdict |
|---|:--|:--|---|
| `compute_enriched_dwpc_GGD` | ✅ | ✅ `mod_raw - g_in_mod` | correct |
| `compute_enriched_dwpc_GPGD` | ✅ | ✅ | correct |
| `compute_dwpc_go_metapaths` | ✅ *removed analytically* | ✅ `mod_D_loo` | correct |
| `compute_enriched_guilt_by_association_1` | ✅ | ✅ Jaccard union drops `g` | correct |
| `compute_enriched_shared_pathway_count_1` | ✅ | n/a | correct — normalises by `n_pathways_g`, not module size, so LOO does not apply |
| `compute_enriched_dwpc_GCD` | n/a | n/a | the path is gene→compound→disease; no intermediate gene, so self-inclusion is impossible |
| `compute_enriched_disease_context_1`, `_module_size_1` | n/a | n/a | disease-level only |

**No leak found in any feature recipe.** The one structural exception is `prox_closest`, below.

---

## 3. Per-feature findings and recommended changes

| Feature | Recipe | Issue found | Recommended change | Theoretical impact |
|---|---|---|---|---|
| **`dwpc_GPGD`** | Cypher | gated ≥20 | **threshold → 5** | Strongest single feature (AUC **0.718**). Restores it for 43 diseases that currently have no pathway signal |
| **`dwpc_GGD`** | Cypher | gated ≥20 | **threshold → 5** | Second strongest (**0.669**). Same 43 diseases |
| **`dwpc_GBGD` / `dwpc_GFGD`** | Python | gated ≥20; `MAX_FANOUT = 500` also unjustified | **threshold → 5**; sensitivity-test the fanout cap | Worst null gaps by label in the set (**−17.8 / −22.9 pp**). Fewer NULLs shrinks the missingness channel §6.2 exists to suppress |
| **`ppi_adamic_adar` / `ppi_jaccard`** | Cypher | gated ≥20 | **threshold → 5** | Restores local-overlap signal for the 43 |
| **`shared_pathway_frac`** | Cypher | gated ≥20 | **threshold → 5** | Same |
| **`prox_closest`** | Python | gated ≥20; `MAX_HOPS = 3` saturates; **NULL is a positive indicator at k = 1** | **threshold → 5** (floor is 2–3, see below); keep `MAX_HOPS = 3`; **add `d_shortest`** | Min-distance discriminates **0.646 at 20–30 seeds vs 0.567 at >300** (Spearman −0.328) because 74% of pairs sit at hop 1 in large modules. A graded distance fixes the dense regime the minimum cannot |
| **`ppi_common_neighbors_z`** | Python | none | none | Already ungated — works for all diseases |
| **`ppi_evidence_depth` / `ppi_multi_source_frac`** | Python | none | none | Gene-level provenance; no disease dependence |
| **`gene_ppi_degree` / `gene_n_pathways`** | Cypher | **0.00% cross-disease variation** (§6.1) | keep, but stop describing the audit as having removed gene-only features | They answer *"is this gene prominent"*, never *"for this disease"*. Defensible as hub-normalisation terms; not defensible as described |
| `rwr_score` / `rwr_norm` | Python | gated ≥20 — **the only place the number is earned** (`KFOLD = 5` needs ≥4 seeds/fold) | **→ 10**, or lower `KFOLD` | Rejected features; change only if reviving them |
| `gene_n_diseases` | Cypher | label-derived; single-feature AUC **0.857**, above the champion | **keep rejected** | Reinstating it would produce a popularity table (§6.1, §7.5) |
| `degree`, `pagerank`, `triangles`, `eigenvector_centrality`, `clustering_coefficient` | plugin | collinear with `gene_ppi_degree` (ρ up to **+1.000**) | **keep rejected** | `gene_ppi_degree` ≡ `degree` exactly |
| `dwpc_GCD` | Cypher | not a feature, but **is a pool-admission route** (§5.2.1) | keep rejected as a feature; report drug metrics **stratified** by route support | Removing it from the pool costs 22 diseases their whole therapeutic evaluability |

### Why the threshold cannot simply go to zero

Three distinct floors, only one of which is about statistics:

1. **`rwr_score`** splits seeds into `KFOLD = 5` held-out folds so a seed never scores itself. Below
   ~10 seeds the folds degenerate. **This is the only recipe that earned the number.**
2. **`prox_closest`** sets each seed's own distance to infinity. In a **one-gene module that gene is
   NULL and every other gene has a value — NULL becomes a perfect positive indicator.** At k = 2 it
   degrades to a bias that shrinks with k. **Structural floor: 2–3.**
3. Everything else has **no floor at all**. `dwpc_*`, Adamic-Adar and Jaccard are sums over paths;
   with 3 seeds they are simply sparser, not invalid.

**Recommended: 5 everywhere except `rwr_score` at 10.** Stop sharing one constant across three
different problems.

---

## 4. Rollout plan

**One change per model, so every effect is attributable.** That discipline is what separated the
`m4`/`m5` results; bundling the threshold and `d_shortest` would make the outcome uninterpretable.

### Phase 0 — lock the baseline *(done)*

`m3`/`m4`/`m5` measured on six axes: association (AUROC + AUPRC, pooled and macro), hub-bias spread,
therapeutic (all + route-supported), tractability (degree-matched, 5 K values), discovery (3 K values).
Those numbers are the comparison set.

### Phase 1 — `m6`: threshold only  ✅ DONE 2026-08-20 — prediction REFUTED

**Executed on `prox_closest` alone.** The other three recipes were reverted mid-flight: measured, their
20→5 change added **no pool pairs at all** (`guilt_by_association` and `shared_pathway_count` returned
on-pool row counts identical to the row), because they count module size the same way the Cypher pool
routes do. `dwpc_go_metapaths` was worse than neutral — its `assoc_m` normaliser is computed over the
eligible set, so widening it silently changes values for existing pairs.

`prox_closest` was kept at 5 **and capped to the pool population** (`POOL_MIN = 20`), which cut it from
32.0M rows to 18.5M and fixed the Spark failure the uncapped version caused.

| | before | after |
|---|--:|--:|
| pool NULL rate | 6.57% | **5.41%** |
| pool diseases with prox coverage | 1,114 | **1,156 of 1,157** |
| null gap by label | −4.99 pp | **−3.94 pp** |
| pool rows / splits | 6,754,128 | **6,754,128 — unchanged** |

**The prediction failed.** Paired m5→m6 on the 22 rescued validation diseases: 64% improved against
**63% of controls**, medians **+0.0022 vs +0.0021**, **t = 1.29**. The macro AUROC gain (0.8171 → 0.8323)
is outlier-driven. What did happen is a small global gain via a better training set — the 646 unaffected
diseases moved significantly (t = 3.42) despite identical features.

### Phase 1 — original plan

Lower `module_size >= 20` → `5` in the **seven recipes gating champion features**, rebuild them,
retrain on the **unchanged 13-feature set**.

- **Pre-registered prediction:** aggregate metrics barely move (1.23% of rows), while the **43 affected
  diseases improve markedly**. If aggregates move a lot, something other than the threshold changed.
- **Must report stratified**, not just aggregate: the 43 affected diseases separately from the other
  1,114. A 1.23% slice cannot move a pooled number but can transform those diseases — and macro
  averages weight every disease equally, so 3.7% of the population is where to look.
- **Cost:** rebuilding four Cypher recipes over the full graph is the expensive step.

### Phase 2 — `m7`: `d_shortest`

Add the graded distance (mean distance to module genes, or a kernel Σexp(−d)) alongside `prox_closest`.

- **Pre-registered prediction:** the gain **concentrates in large-module diseases**, where the minimum
  saturates at 74% hop-1 and scores AUC 0.567. If the gain is uniform across module sizes, the
  saturation mechanism is wrong and the improvement is coming from somewhere unexamined.
- Keep `MAX_HOPS = 3` — measured at 93–99% interactome coverage already; raising it adds ≤6 points as a
  constant.

### Phase 3 — decide once, then re-run downstream once

Pick a winner on the six axes with **AUPRC as the selection metric** (§7.1: it made `m4`'s gain visible
where macro AUROC read as noise). Then re-run the persona chain, dashboard tables and breast panel, and
re-assert every §8 number with `nb1`–`nb5`.

**Do not adopt between phases.** Each adoption costs a full downstream re-run plus re-verification;
three adoptions cost that three times.

### Standing rules carried in

- **Six axes, every time.** Judging on two produced the `prox_closest` mistake; judging on four missed
  tractability.
- **State a falsifiable prediction before running.** It has produced the useful outcome repeatedly —
  including three times when the prediction was wrong.
- **Report the affected subpopulation separately** from the aggregate.
