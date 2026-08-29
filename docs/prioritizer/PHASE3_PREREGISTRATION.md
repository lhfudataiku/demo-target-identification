# Phase 3 pre-registration — lowering the pool-route seed gate 20 → 5

> **Lifecycle:** Decision · **Audience:** reviewers deciding whether to run or accept the registered
> intervention · **Authority:** the pre-committed gates, predictions and adopt/reject rule · **Update
> when:** never after execution begins; corrections require a dated successor · **Generated
> dependencies:** the cited sizing evidence and recipe classification · **Excludes:** experiment results.

**Written 2026-08-21, before the branch project exists.** Every number in it is measured on the current
project; nothing here has been fitted to a Phase 3 result, because no Phase 3 result exists yet.

> **Why pre-register at all.** This thread's record is that mechanisms get refuted, not confirmed:
> three `prox_closest` hypotheses, the hub-bias attribution, the sign of the degree correlation, `m6`'s
> rescued-disease prediction and `m7`'s module-size mechanism all failed on measurement. In every case
> the value came from having written the prediction down precisely enough to be caught out. A vague
> expectation would have been quietly retrofitted to whatever happened.

---

## 1. Hypothesis

**That 931 diseases currently absent from the candidate pool can be ranked better than gene popularity,
and that admitting them does not degrade the 1,157 diseases already there.**

Two claims, tested separately. The second is a safety condition, not a benefit.

## 2. The intervention

The gate is on distinct `disease_protein` seeds per disease. **Ten** recipes carry a threshold; they
fall into two classes, and **the distinction decides the whole design**.

> *Source: generated — `.index/recipes.tsv` and `.index/features.tsv` (`tools/build_recipe_index.py`).
> The class field is hand-recorded in `tools/recipe_classes.json` with its evidence, because it is a
> judgement about aggregate scope that a regex would get plausibly wrong; the generator **exits
> non-zero if a gated recipe has no class**, so a new gate cannot reach this experiment unclassified.
> The inventory was nine recipes when this document was first written — `compute_enriched_rwr_score_1`
> was missing because it was **not under version control** and therefore invisible to the scan.*

### Class 1 — pure NULL-fill: widening adds rows, existing values unchanged

Their per-gene normalisers are global `COUNT{}` subqueries over the whole graph, so eligibility does not
enter them. **Change all of these 20 → 5:**

| recipe | features |
|---|---|
| `compute_enriched_dwpc_GGD` | `dwpc_GGD` — **pool route** |
| `compute_enriched_dwpc_GPGD` | `dwpc_GPGD` — **pool route** |
| `compute_enriched_dwpc_GCD` | `dwpc_GCD` — **pool route** |
| `compute_enriched_guilt_by_association_1` | `ppi_adamic_adar`, `ppi_jaccard` (`deg_m`, `ppi_deg_g` are global) |
| `compute_enriched_shared_pathway_count_1` | `shared_pathway_frac` (`n_pathways_g` is global) |
| `compute_enriched_disease_context_1` | `disease_context` — **settled Class 1** from the mirrored Cypher: the gate filters the anchor `D`, but `D2` is matched via `(D)-[:disease_disease]-(D2)` with no module_size filter |
| `compute_enriched_module_size_1` | `module_size` (trivially per-disease) |
| `compute_enriched_rwr_score_1` | `rwr_score` — `MIN_SEEDS = 20 → 5`; per-disease loop, global adjacency |
| `compute_enriched_prox_closest` | already `MIN_SEEDS = 5`; raise `POOL_MIN` 20 → 5 |

The three pool routes are what actually admit a disease — `filter_has_path_evidence` keeps a row when
any of `dwpc_GGD` / `dwpc_GPGD` / `dwpc_GCD` is non-blank. The rest only fill features for rows already
admitted.

### Class 2 — recomputes an aggregate over the eligible set: **HOLD AT 20**

`compute_dwpc_go_metapaths` (`dwpc_GBGD`, `dwpc_GFGD`) computes

```python
eligible = mod_raw[mod_raw >= MIN_MODULE].index.to_numpy()
gd = gd[gd.disease_index.isin(set(eligible))]
assoc = gd.groupby("gene_index").size()      # per-gene disease degree, ELIGIBLE diseases only
```

and `assoc` enters the DWPC weight. **Widening eligibility therefore changes `dwpc_GBGD`/`dwpc_GFGD`
for existing pairs** — a different intervention, not a NULL fill.

> **This was already tried and reverted.** A 20 → 5 change to this recipe was applied and rolled back
> on 2026-08-20: on its own it added no pool pairs at all, because it counts module size the same way
> the Cypher routes do, so every disease that passed already had the features. The lesson recorded in
> its header is the reason it is held here.

**Decision: hold `MIN_MODULE = 20`.** The 931 admitted diseases will carry NULL for **exactly two of
the fourteen champion features — `dwpc_GBGD` and `dwpc_GFGD`** (confirmed against
`.index/features.tsv`: 7 of 14 are gated Class 1, 2 are gated Class 2, and 5 are ungated — that last
count independently matches the documented "five gene-level features" an excluded disease falls back
on). That is the deliberate price of keeping the 1,157 existing diseases as a clean control — with
`assoc` frozen, their features are byte-identical, so any change in their scores is attributable to the
training set alone and nothing else. Lowering both at once confounds two interventions in one rebuild,
and this project has already paid for that mistake once.

## 3. What is deliberately not done

- **No retraining in the first pass.** Score the widened pool with the existing `m7-f14` (`hJLGoYn4`).
- **No threshold below 5.** The 4,951 diseases with under five seeds stay out; 3,334 have a single seed
  and nothing to propagate from.
- **`compute_kg` is not touched or recomputed.**
- **Not done in this project.** The pool change rewrites the population, so every number in
  `TARGET_PRIORITIZER.md` would stop being comparable. Branch project only.

## 4. Pre-flight gates — must pass before any model is trained

**These are correctness checks, not hypotheses. A failure means the intervention is not what we think
it is, and the run should stop.**

| # | gate | pass condition |
|---|---|---|
| **G1** | **Bit-identity of the control stratum.** For the 1,157 diseases eligible before the change, every feature value must be unchanged. | **0 rows differ.** Any drift identifies a recipe as Class 2 that was classified Class 1 — this is the empirical test that supersedes my reading of the Cypher, including `disease_context` |
| **G2** | Pool growth is in the predicted range | see P5 |
| **G3** | Disease count | eligible 1,157 → **2,088** exactly |
| **G4** | Family split integrity | `straddling_split_keys = 0`, all three overlap counts 0 (the §5.4 audit) |
| **G5** | Existing diseases' scores under un-retrained `m7` | **bit-identical** to `scored_champion` on the shared 1,157 |

G1 and G5 together are the whole reason the control stratum is worth anything. Run them first.

## 5. Pre-registered predictions

Directions and ranges, so each can fail in both directions.

| # | prediction | falsified if |
|---|---|---|
| **P1** | **The premise.** Admitted diseases beat a gene-popularity baseline (rank by `gene_n_diseases`) by **> +0.05** macro per-disease AUC, paired per-disease, significant | margin ≤ +0.05, or not significant |
| **P2** | Admitted diseases score **well below** the existing population: macro AUC in **0.62–0.75** against 0.8230 | outside that band. ≥0.80 would be a genuine surprise; ≤0.55 makes the change worthless |
| **P3** | **Per-disease positives are the binding constraint.** Median usable positives per admitted disease **≤ 5** | median > 5 |
| **P4** | **Hub bias worsens**: spread **> 0.1935**, ρ(degree, probability) **> 0.3273**. Thin modules mean the disease-specific features carry little variance, so gene-level (hub) features dominate those rows | spread ≤ 0.1935 |
| **P5** ⚠ | ~~+9% to +15%~~ **REVISED 2026-08-21 pre-experiment: +18% to +22%**, 6,754,128 → **8.0M–8.25M** rows | outside that range |
| **P6** ⚠ | ~~1.72–1.86%~~ **REVISED 2026-08-21 pre-experiment: falls from 1.89% to 1.60–1.67%**, because admitted rows are 6.3× more dilute on the union of routes | outside that range |
| **P7** | On the control stratum, retraining produces a **small positive** shift by `m6`'s mechanism — a better training set rather than better scoring — of **+0.000 to +0.004** macro AUC | a shift outside that range, in either direction |

> **⚠ P5 and P6 were revised on 2026-08-21, BEFORE any Phase 3 run.** Both originals were sized on the
> **GGD route alone** and then compared against the **whole pool** — the same route-only-numerator error
> §8.4 had to be corrected for, made twice in one week. Measuring the union of GGD and GPGD (§9, now
> answered) gives +19.6% rows and a 1.63% positive rate. **The revision is legitimate only because no
> experiment has run**: these are better measurements of the *input*, not adjustments to fit a result.
> The originals are struck through rather than deleted so the record shows what was predicted when.
> **If a prediction needs revising after Phase 3 runs, it does not get revised — it gets reported as
> failed.**

**Basis for P2 and P4 — the headwind, stated before the fact.** `m7` made the under-20-seed bucket
**worse** (−0.0117, n = 22, not significant) while helping every larger bucket, and the 931 diseases
this change admits are all in or near that regime. Measured on the GGD route, they are **4.4× more
dilute** in positives (0.72% against 3.19%) and only **34%** of their seeds are reachable at all,
leaving ~3.3 usable positives per disease.

> **Honest prior: this is a low-expected-value change on ranking quality and a high-value change on
> coverage.** +80% more diseases for ~+12% more rows is an unusually good ratio, and the admitted terms
> are clinically real — kidney cancer, influenza, differentiated thyroid carcinoma, epithelioid sarcoma
> all sit at 19 seeds. But nothing measured so far suggests those diseases will rank *well*. **The
> defensible claim if P1 passes and P2 lands as predicted is "we now cover 2,088 diseases instead of
> 1,157, and the new ones are ranked better than popularity though worse than the core" — not "the model
> got better."**

## 6. Decision rule — committed in advance

**Adopt only if all four hold:**

- **A1** P1 passes. If the admitted diseases cannot beat gene popularity, the change adds rows without
  adding signal and there is nothing to adopt.
- **A2** On the retrained model, any association gain is **corroborated on the degree-matched
  tractability axis** — or, failing a gain, there is no significant association *loss* on the control
  stratum.
- **A3** Hub spread does not worsen by more than **+0.005** (i.e. stays ≤ 0.1985). P4 predicts it
  worsens; A3 bounds how much is acceptable.
- **A4** Every reported difference carries its **tie count**, and no claim rests on fewer than 20% of
  diseases actually differing.

**Reject if:** P1 fails · an association gain is not corroborated on tractability (**the `m8`
precedent — a model was rejected for scoring better, and that rule is not negotiable per experiment**) ·
the control stratum degrades significantly · G1 or G5 fail.

**A2 is the rule `m8` was rejected under.** It is restated here so that a Phase 3 result showing
"AUPRC up, tractability flat" gets the same answer `m8` got.

## 7. Analysis plan

**Two strata, never pooled.**

| stratum | diseases | baseline available | test |
|---|--:|---|---|
| **A — control** | 1,157 eligible before | yes, `m7` on identical features | paired per-disease, with tie counts |
| **B — admitted** | 931 newly eligible | **none** — absent, not degraded | vs gene-popularity baseline, paired per-disease |

Stratum B has no `m7` baseline to pair against because these diseases have **no pool-route features at
all** today. That is why the "cheap probe before branching" idea does not work and the branch comes
first: there is nothing to score until the gate is lowered.

**Estimators.** Macro per-disease throughout, matching the rest of the document. Where a pooled figure
is also reported it must be labelled, and **a pooled and a macro number must never appear in the same
row** — §8.4 had to be corrected for exactly that.

**Reporting rules carried forward:** ties before means · report stratified, never a single macro across
A and B · state the estimator on every lift · flag any K where a count is too small to be informative.

## 8. Project-specific traps

1. **Never compare the branch's macro AUC to 0.8230.** Different population, so the comparison is
   meaningless. Cross-project comparison is restricted to the shared 1,157 diseases.
2. **`flow propagate` fully before rebuilding**, then build fused Spark stages separately — widening a
   schema upstream otherwise fails validation against a stored schema that `--auto-update-schema` never
   updated.
3. **One job, repeated `--target`, `RECURSIVE_BUILD`** with update-output-schemas and stop-at-zone-
   boundary; build from the last dataset so intermediates stay virtual.
4. **Both champion entry points** must be repointed if a new model is adopted: `sync_scored_champion`
   *and* `score_persona_candidates`. The second was missed once and sat on `m3-f12` after the champion
   had moved.
5. **`compute_model_comparison` stays on `scored_m1/m2/m3`** — it is the ablation ladder, not a champion
   consumer.

## 9. ANSWERED 2026-08-21 — `dwpc_GPGD` helps, but not enough to change the character

**Measured, like-for-like, on the union of both pool routes:**

| band | route | candidate rows | positives reached | of seeds | positive rate |
|---|---|--:|--:|--:|--:|
| **5–19 (admitted)** | GGD | 424,523 | 3,067 | 34% | 0.72% |
| | GPGD | 1,094,712 | 3,820 | 43% | 0.35% |
| | **union** | **1,326,438** | **4,229** | **47%** | **0.32%** |
| **≥20 (current)** | GGD | 355,188 *(n=120)* | 11,336 | 59% | 3.19% |
| | GPGD | 557,818 | 11,969 | 62% | 2.15% |
| | **union** | **702,407** | **14,025** | **73%** | **2.00%** |

*Method validated: the same computation predicts the current pool at 6,772,374 rows against an actual
6,754,128 — a **0.3%** error.*

**GPGD lifts admitted-disease reachability from 34% to 47%, and usable positives per disease from 3.3 to
4.5.** That is real but it does not change the shape of the problem: admitted diseases still lose **more
than half** their positives, where current diseases lose about a quarter, and on the union they are
**6.3× more dilute** (0.32% against 2.00%) — worse than the 4.4× measured on GGD alone, because pathway
co-membership is promiscuous and adds candidate rows faster than it adds positives.

**Revised bottom line: +80% more diseases for ~+20% more pool rows.** Still a favourable coverage
ratio, and the admitted terms are clinically real. But the evidence for a *ranking* win is weaker than
when this document was written, and P2's 0.62–0.75 band should now be read as optimistic rather than
central.

<details><summary>The original open question, for the record</summary>

**How much of the 34% seed-reachability does `dwpc_GPGD` recover?** It is pathway-mediated and does not
need a direct seed–seed PPI edge, so it should reach more of the admitted diseases' positives than the
GGD route does. **Not measured.** It is the single number most likely to change P1's prospects, and it
is cheap — the same computation as §5 of `FEATURE_AUDIT.md` run against `pathway_protein` instead
of `protein_protein`. Worth doing first if the branch is expensive to stand up.

</details>
