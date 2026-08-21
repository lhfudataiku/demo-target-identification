# Documentation overhaul — proposal

> **⚠ SUPERSEDED — executed, kept for the record.** The section/number pairs in the tables below were
> the *citation targets* as of 2026-08-19 and were measured on `m3-f12`. The champion is now `m7-f14`
> and those figures have moved. Read them as "which dataset backs which section", never as current
> values; the notebooks are the live source.

Drafted 2026-08-19 after reviewing all seven markdown files, the 100 datasets and 55 recipes in
`DEMO_TARGET_IDENTIFICATION`, and the 47 mirrored scripts in `dss_recipes/`.

---

## 1. Diagnosis

`TARGET_PRIORITIZER.md` is **1,726 lines across 55 sections**. Three measurable problems:

| Problem | Evidence |
|---|---|
| **Numbers are untraceable** | Only **8 of 55 sections** name a backing artifact. §7 and §8 alone carry **~700 numeric literals** with no stated source |
| **Density is unreadable** | The decision log is **82 lines holding 312 numbers**. §8.3 packs 102 numbers into 76 lines |
| **Two audiences, one file** | The narrative material (§1, §2, §8.6, §8.9, §8.10, §8.12) and the method material are interleaved, so neither audience can skim |

**Staleness is worse than "some numbers moved."** Two findings from this review:

- **§6.2's split sizes are wrong and provably so.** Documented `2,693,788 / 561,214`; live
  `2,187,862 / 607,345`. The live values reconcile exactly to the pool
  (2,187,862 + 607,345 + 3,958,921 = 6,754,128); the documented ones do not sum to anything.
- **§3.3's thesis is refuted by §8.13, not merely dated.** It claims coarser terms surface novel
  candidates and names `breast cancer` and `obesity disorder` as the best demo diseases. The breast
  panel measured `breast cancer` as the **worst** term in its family (AUC 0.69, beaten by every
  subtype). Updating the table is not enough — the claim inverts.

**One finding produced during this review, which changes how §7 should be organised.** You asked for a
scatter and regression on *"association AUC does not predict therapeutic relevance"*. Measured over the
130 diseases carrying both metrics:

| | value |
|---|--:|
| Pearson r | **+0.024** |
| R² | **0.0006** |
| Spearman | +0.036 |
| t (128 df) | +0.27 — **not significant** |
| restricted to ≥10 validated targets (n=42) | r = **+0.006** |

**The two axes are statistically orthogonal, not "in tension."** Tension implies a negative
correlation; this is zero. Association AUC explains **0.06%** of therapeutic-AUC variance. That is a
stronger and cleaner claim than the doc currently makes, and it is the reason a three-axis framework is
necessary rather than merely thorough. It should anchor §7.

---

## 2. Target architecture — three layers

| Layer | File | Audience | Budget |
|---|---|---|---|
| **Demo** | `DEMO_NARRATIVE.md` | client-facing team prepping a demo | **5–10 min, ≤ 260 lines** |
| **Methodology** | `TARGET_PRIORITIZER.md` | technical reviewer, due diligence | ~900 lines, every number sourced |
| **Reproduction** | `notebooks/*.ipynb` | whoever challenges a number | 4 notebooks |
| **Reference** | `DECISIONS.md` | archaeology | append-only |

**`DEMO_NARRATIVE.md` already is the demo doc** — 249 lines, the six-question objection ladder, the
punch line, what-not-to-show, demo diseases, a verified numbers sheet. It needs **one addition**: a
one-page executive summary of what Part 2 *is* (deliverable, model, headline numbers) so it stands
alone without `PROJECT_CONTEXT.md`. Everything else is already there.

**Keep the filename `TARGET_PRIORITIZER.md`** rather than renaming to `METHODOLOGY.md`. It is indexed
in `PROJECT_CONTEXT.md`, mirrors the DSS project name, and is cross-linked from four files. Rename is
churn without benefit; the restructure is what matters.

---

## 3. Disposition of all 55 sections

### Moves to the demo doc

| § | Lines | Why it is narrative, not method |
|---|--:|---|
| 1 What it delivers | 19 | becomes the exec summary |
| 2 Scientific basis | 21 | duplicates PROJECT_CONTEXT §2.1/§2.3 — **merge, do not copy** |
| 8.6 Candidate output — biological coherence | 16 | a "look at this list" moment |
| 8.9 GLP1R case study | 55 | a story with a moral; no method |
| 8.10 On-graph explanation | 45 | zero tables, all demo mechanics |
| 8.12 What it delivers, concretely | 19 | duplicates §1 |
| | **175** | |

### Extracted to `DECISIONS.md`

| § | Lines | |
|---|--:|---|
| Appendix — decision log | 82 | **312 numbers.** Append-only reference, never read linearly. Biggest single density win |

### Deleted or merged

| § | Lines | Disposition |
|---|--:|---|
| **3.2** persona-leakage narrative | ~14 of 24 | **Delete.** Describes a state §5.3's family split already fixed, on the retired 4-persona panel. **Keep only the graph-topological table** — that finding is durable and load-bearing for §5.3 |
| **3.3** granularity | 19 | **Rewrite, do not update.** Thesis refuted by §8.13; the parent-vs-subtype result replaces it |
| **4.3** Not yet built | 12 | **Merge into §10.4/§10.5.** A roadmap living in a methods section, half of it already struck through |
| **5.5** index remap | 43 | **Move to a migration appendix.** 40 numbers of completed, verified one-time work |
| **7.5** m7 negative result | 62 | **Keep** — but it is prose-only since the artifacts were deleted. Must carry the `docs/appendix/model_comparison.csv` pointer in-line, not in §10.4 |

**Net: 1,726 → ~1,000 lines**, before any rewriting.

### Stays, and gets sourced + re-measured

§3.1, §3.4, §4.1, §4.2, §4.4, §5.1–5.4, §5.2.1, §6.1–6.4, §7.1–7.4, §8.1–8.5, §8.7, §8.8, §8.11,
§8.13, §9, §10.

---

## 4. Traceability map — number to artifact

The rule to adopt: **every table in the methodology doc names its source dataset in the caption, or is
marked `notebook-only`.** Current state:

| § | Claim | Backing artifact | Action |
|---|---|---|---|
| 3.1 | label study bias | — | **notebook** |
| 3.2 | ontology topology (largest component) | — | **notebook** |
| 3.4 | lung 47/50, breast 2/50 | `lung_granularity_check`, `breast_panel_overlap` | ✅ cite |
| 4.1 | the 12 inputs | ML task settings API | **notebook** (pull live, do not hand-list) |
| 4.2 | rejected features | — | **notebook** |
| 5.2 | 18.4M → 6.75M | `enriched_graph_features_candidate_psplit`; **the 18.4M side needs `enriched_graph_features_1_family`, currently unbuilt** | rebuild or notebook |
| 5.2.1 | 91.8×, 0.6911 → 0.7337 | `pool_selection_bias`, `pool_reachability` | ✅ cite |
| 5.4 | zero straddling keys | `split_audit_2` | ✅ cite |
| 6.1 | collinearity ρ, null gaps | — | **notebook** — this is your §4 request |
| 6.2 | split sizes | `psplit_*` counts | ✅ cite + **fix the stale values** |
| 6.3 | threshold, recall 22.6% | — | **notebook** |
| 6.4 | ablation ladder | `model_comparison` → **deleted from flow**, lives in `docs/appendix/model_comparison.csv` | cite the CSV |
| 7.2 | hub-bias meter | **no recipe — ad hoc, retired generation** | **notebook**, or promote to a recipe |
| 7.3 | per-family 0.7976 / 505 | `family_auc_by_family` | ✅ cite + **plot** |
| 7.4 | drug-target 0.6911 | `drug_target_benchmark` | ✅ cite + **plot** |
| 8.1–8.4 | the three axes | `known_drug_truth`, `tractability_axis`, `novel_discovery_eval` | ✅ cite |
| 8.7 | filter on three axes | `filter_three_axes` | ✅ cite |
| 8.8 | persona selection | `persona_candidates` | ✅ cite |
| 8.13 | breast panel | `breast_panel_metrics`, `breast_panel_overlap`, `breast_shortlist` | ✅ cite |
| 10.1 | reconstruction ±0.01 | `reference_baseline.json` | ✅ cite |

**Roughly 60% of the load-bearing tables already have a dataset** — the work is citation discipline,
not new computation. The genuine gaps are §3, §4/§6.1 feature analysis, §6.3, and §7.2.

---

## 5. Notebooks — four, not six

Each notebook reads live DSS datasets, recomputes, and **asserts** the value the doc quotes, so a stale
number fails loudly instead of rotting silently.

| Notebook | Backs | Must produce |
|---|---|---|
| `nb1_exploration_and_features.ipynb` | §3, §4, §6.1 | label-bias distribution; ontology largest-component table; granularity rewritten on the 13-persona panel; **feature null-rate by label class**; **collinearity matrix**; single-feature within-disease AUC |
| `nb2_splitting_and_pool.ipynb` | §5 | pool funnel with both stages; family antichain check; split audit; the GCD route decomposition and the 0.6911 / 0.7337 stratification |
| `nb3_model_and_validation.ipynb` | §6, §7 | config pulled from the ML task; threshold/recall curve; ablation on **both axes**; hub-bias meter; per-family plots; **the orthogonality scatter** |
| `nb4_results_and_axes.ipynb` | §8 | three-axis tables; discovery lift vs K; tractability naive-vs-degree-matched; filter clauses; persona panel; breast panel |

**Convention:** first cell prints `scored_m3` row count and the graph generation stamp, so every output
is dated against a build. This is the staleness detector the docs currently lack.

---

## 6. Plots

| Plot | Section | Data | Why |
|---|---|---|---|
| **Scatter + regression, association vs therapeutic AUC** | 7.4 | `validation_auc_by_disease` ⋈ `drug_target_benchmark` | **r = +0.024, R² = 0.0006.** The single most economical way to justify three axes |
| Per-family AUC: ranked bar + distribution | 7.3 | `family_auc_by_family` | replaces a 45-number table |
| Feature null-rate by label class | 4.1/4.2 | `psplit_train_set` | your explicit request; the −31.6 pp gap becomes visible |
| Collinearity heatmap | 4.2/6.1 | `psplit_train_set` | your explicit request; shows the hub cluster in one glance |
| Discovery lift vs K, by ground truth | 8.3 | `novel_discovery_eval` | collapses 102 numbers |
| Tractability: naive vs degree-matched vs K | 8.4 | `tractability_axis` | makes the rank-20 crossover visible |
| Ablation on both axes | 6.4 | `docs/appendix/model_comparison.csv` | **your point about §6.4's highlight** — the two-axis trade *is* the finding, the ladder is the setup |

---

## 7. On §6.4

You asked whether the association-vs-drug-target comparison is the highlight of that section. **It
should be, and currently it is not** — the section leads with the m1→m2→m3 ladder, which
`DEMO_NARRATIVE.md` already lists under "what not to show" because it invites a hyperparameter
conversation. Restructure so §6.4 opens with the two-axis result per model and treats the ladder as
the mechanism that produced it.

---

## 8. Sequencing

| Step | Work | Depends on |
|---|---|---|
| 1 | Extract `DECISIONS.md`; move the six narrative sections into `DEMO_NARRATIVE.md`; add its exec summary | — |
| 2 | Delete/merge §3.2 narrative, §3.3, §4.3, §5.5 | 1 |
| 3 | Build `nb1`–`nb4` with assertions against current doc values | 2 |
| 4 | **Fix everything the assertions fail on** — §6.2 split sizes are known already; expect more | 3 |
| 5 | Add the seven plots; replace the tables they subsume | 3 |
| 6 | Citation pass: every table names its dataset or is marked `notebook-only` | 3 |
| 7 | Rewrite §3.3 on the parent-vs-subtype result; restructure §6.4 around the two axes | 4 |

**Step 3 before step 4 is deliberate** — write the assertions before fixing the numbers, so the
notebook tells us what is stale instead of us guessing. §6.2 was found that way.

---

## 9. Open questions for you

1. **Notebook execution environment** — the DSS code env (`primekg_kg`) via a DSS-hosted notebook, or
   local against the API? DSS-hosted keeps the datasets one call away; local is easier to diff in git.
2. **Committed outputs?** Notebooks with stored outputs are readable in a PR but noisy in diffs.
   Recommendation: commit them, since the point is a citable rendered number.
3. **§5.5 and §10.2 migration history** — keep as a `MIGRATION.md` appendix, or drop now that the
   rebuild is verified and `index_remap.json` exists?
