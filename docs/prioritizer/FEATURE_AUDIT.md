# Feature recipe audit — method §3.1 and §3.2

<!-- Governed claims consumed here: TI-DATA-001 TI-MOD-001 TI-VAL-001 TI-VAL-005 TI-VAL-006 TI-VAL-007 TI-VAL-008 -->

> **Lifecycle:** Evidence · **Audience:** feature engineers and reviewers planning gate changes ·
> **Authority:** measured per-feature recipe and seed-gate audit · **Update when:** an audited recipe,
> feature set or gate changes · **Generated dependencies:** `.index/features.tsv`,
> `.index/recipes.tsv` and the cited live measurements · **Excludes:** model-selection rationale.

Every recipe producing the original 12-feature core now embedded in TARGET_PRIORITIZER §3.1, plus
the candidates in §3.2, read for four things: **the module-size threshold**, **self-path exclusion**,
**leave-one-out module normalisation**, and **null semantics**. Audited 2026-08-20.

---

## 1. The headline: one constant gates 7 of the 12-feature core

`module_size >= 20` is not a `prox_closest` quirk. It appears in **ten recipes**, and gates **seven of
the twelve core inputs**:

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

Those diseases have **7 of 12 core features NULL**, leaving only the five gene-level ones — and
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

### Phase 2 — `m7`: graded proximity  ▸ features built, collinearity checked 2026-08-21

Four statistics now come from one Dijkstra pass: `prox_closest` (min, unchanged), `prox_mean`
(Guney's d_shortest), `prox_kernel` (Σexp(−d)), `prox_n_reach` (count within 3 hops). Pool held at
6,754,128; splits unchanged.

| | ρ with `gene_ppi_degree` | max ρ vs the 13 | single-feature AUC | verdict |
|---|--:|--:|--:|---|
| `prox_closest` | −0.378 | −0.378 | 0.5956 | incumbent |
| `prox_mean` | **−0.697** | −0.697 | **0.6499** | best discriminator, **most hub-entangled** — deferred |
| **`prox_kernel`** | **+0.216** | −0.452 | 0.6094 | **chosen for m7** |
| `prox_n_reach` | +0.104 | −0.534 | 0.4864 | **dropped** — ρ = +0.982 with kernel, below the 0.5 floor |

**The prediction that a kernel sum would be a hub proxy was wrong, and backwards.** Reach saturates
(mean 184 seeds reached), so the count reflects module size rather than gene degree — while a *mean
distance* shortens systematically for hubs. Averaging imports the bias; summing does not.

### Phase 2 — original plan

Add the graded distance (mean distance to module genes, or a kernel Σexp(−d)) alongside `prox_closest`.

- **Pre-registered prediction:** the gain **concentrates in large-module diseases**, where the minimum
  saturates at 74% hop-1 and scores AUC 0.567. If the gain is uniform across module sizes, the
  saturation mechanism is wrong and the improvement is coming from somewhere unexamined.
- Keep `MAX_HOPS = 3` — measured at 93–99% interactome coverage already; raising it adds ≤6 points as a
  constant.

### Phase 2 result — `m7-f14` recommended for adoption

| axis | m3 | m4 | m5 | m6 | **m7** | paired m6→m7 |
|---|--:|--:|--:|--:|--:|---|
| association macro AUROC | 0.8197 | 0.8200 | 0.8175 | 0.8197 | **0.8230** | **t = +3.29, 0 ties** |
| association macro AUPRC | 0.1737 | 0.1762 | 0.1711 | 0.1749 | **0.1778** | **t = +3.18** |
| hub spread *(lower better)* | 0.1954 | 0.1932 | 0.1915 | **0.1900** | 0.1935 | worse |
| therapeutic, all | 0.6911 | 0.6949 | 0.6931 | 0.6949 | 0.6886 | worst of five |
| therapeutic, route-supported | 0.7337 | 0.7371 | 0.7384 | 0.7418 | **0.7471** | best |
| tractability dm@200 | 2.376 | 2.381 | 2.380 | 2.391 | **2.418** | **t = +2.56, 0 ties** |
| discovery lift@50 | 7.46 | 7.09 | 9.08 | 7.43 | **9.43** | t = +1.47, **90% ties — n.s.** |
| discovery lift@200 | 4.53 | 4.83 | **5.52** | 4.78 | 5.04 | t = +0.70, **78% ties — n.s.** |

**Two significant gains, both on axes that matter: association (the headline) and tractability ([VALIDATION.md](VALIDATION.md) §3.2's
"most robust positive claim", uninflated label, degree-matched null).** Discovery is a non-finding in
both directions. Two costs: hub spread worsens slightly, and therapeutic-on-all-positives is the worst
of the five — though route-supported is the best, which under §5.2.1 is the more meaningful of the pair.

**The mechanism is unexplained.** `Spearman(module size, delta) = −0.003` refutes the saturation story
the feature was designed around.

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

---

## 5. Phase 3 sizing — what lowering the POOL-ROUTE gate would admit

*Source: `graph_edges` (`disease_protein`, `protein_protein`) and `graph_nodes`, measured 2026-08-21.
The gate is in the Cypher of `compute_enriched_dwpc_GGD` / `_GPGD` / `_GCD`:
`WHERE module_size >= 20` on distinct `disease_protein` seeds.*

**This is the number that was owed before any Phase 3 work.** `enriched_module_size_1` cannot answer it
— that dataset is itself gated, so its minimum *is* 20.

| module size | diseases | status |
|---|--:|---|
| 1 seed | 3,334 | correctly excluded — nothing to propagate from |
| 2–4 | 1,617 | correctly excluded |
| **5–9** | **547** | **the gap** — thin but usable |
| **10–19** | **384** | **the gap** — solidly evaluable |
| 20–49 | 454 | currently eligible |
| ≥50 | 703 | currently eligible |

**Lowering the gate 20 → 5 takes eligible diseases from 1,157 to 2,088 — a +80% increase — and
*none* of the 931 admitted diseases is in the scored population today.** They are absent, not degraded:
with all three pool routes gated off they never enter the candidate pool at all.

**The cost is far smaller than the gain**, because a small module reaches far fewer candidate genes:

| | diseases | GGD candidate rows | mean per disease |
|---|--:|--:|--:|
| currently eligible (≥20) | 1,157 | ~3.42M *(sampled n=120)* | 2,960 |
| **the 5–19 gap** | **931** | **424,523** | **456** |

**+80% more diseases for ~+12% more pool rows.** The sampled estimate implies 3,424,604 rows for the
current gate against the 3,380,853 actually in `enriched_dwpc_GGD` — a 1.3% error, which is what
validates the method.

> **⚠ CORRECTED before use.** This section first claimed the admitted rows were *denser* in positives
> — 2.10% against the pool's 1.89%. **That compared the gap's GGD-route-only row count against the
> full pool's rate: two different denominators.** It is the same estimator mismatch
> [VALIDATION.md](VALIDATION.md) §3.2 warns against.
> Measured like-for-like on the GGD route, the conclusion reverses.

**The admitted rows are substantially more dilute, and this is the finding that should temper the
+80%:**

| GGD route, like-for-like | diseases | rows | positives | rate |
|---|--:|--:|--:|--:|
| currently eligible (≥20) | 120 *(sample)* | 355,188 | 11,336 | **3.19%** |
| **the 5–19 gap** | 931 | 424,523 | 3,067 | **0.72%** |

**The gap is 0.23× as dense — 4.4× more dilute.** Worse, **only 3,067 of the gap's 8,919 seeds are
GGD-reachable at all (34%)**: in a nine-gene module most seeds have no PPI edge to *another* seed, so
they never enter the route. That leaves roughly **3.3 usable positives per admitted disease**, and a
per-disease AUC on three positives is very noisy.

**MEASURED 2026-08-21 — the union of both routes, which is what pool membership actually is:**

| band | candidate rows | positives reached | of seeds | positive rate |
|---|--:|--:|--:|--:|
| **5–19 (admitted)** | 1,326,438 | 4,229 | **47%** | **0.32%** |
| **≥20 (current)** | 702,407 *(n=120 scaled)* | 14,025 | **73%** | **2.00%** |

`dwpc_GPGD` lifts admitted reachability 34% → **47%** and usable positives per disease 3.3 → **4.5**.
Real, but not character-changing: admitted diseases still lose over half their positives against about
a quarter for current ones, and on the union they are **6.3× more dilute** — worse than the 4.4× on GGD
alone, because pathway co-membership adds candidate rows faster than positives.

> **This corrects the +12% figure above.** That was GGD-only. On the union the pool grows
> **+19.6%** (6,754,128 → 8,080,566) and the positive rate falls to **1.63%**. So the trade is
> **+80% diseases for ~+20% rows** — still favourable on coverage, weaker on quality than first stated.
> Method validated at **0.3%** error against the real pool size. See
> `PHASE3_PREREGISTRATION.md` §9.

> **⚠ CORRECTION to the rollout sequence.** The plan recorded earlier was "size the population, then run
> a cheap train-narrow / score-wide probe with `m7`, and branch the project only if the probe clears".
> **The probe cannot run before the branch.** The 931 diseases have *no pool-route features at all*, so
> there is nothing for `m7` to score until the gate is lowered and those features are computed — and
> lowering it rewrites the pool. The only branch-free alternative is to score them on the five
> gene-level features, which have ~0% cross-disease variation, so the model would rank purely on gene
> prominence — that *is* the popularity baseline, making the comparison degenerate.
>
> **Revised sequence: duplicate the project first**, lower the gate there, compute features, then score
> with the *existing* `m7` (no retraining) and compare against gene popularity. Retrain only if that
> clears. The duplication is now the first step, not the last.

**The pre-registration is written: [PHASE3_PREREGISTRATION.md](PHASE3_PREREGISTRATION.md)** — recipe
inventory split by whether widening changes existing values, pre-flight gates, seven falsifiable
predictions, and the committed adopt/reject rule.

**Headwind to state in the pre-registration.** `m7` made the <20-seed bucket *worse* (−0.0117, n = 22,
not significant) while helping every larger bucket — and the 931 diseases this change admits are all in
or near that regime. The pre-registered prediction should say so, and the decision rule stays the one
that rejected `m8`: an association gain must be corroborated on the degree-matched tractability axis.
