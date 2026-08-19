# Assertion notebooks

Four DSS-hosted Jupyter notebooks on the **`primekg_kg`** code env, one per documentation area. The
`.py` files here mirror the notebook cell sources so they are diffable in git; the notebooks themselves
live in `DEMO_TARGET_IDENTIFICATION` and are the ones to run.

| Notebook | Backs | Checks |
|---|---|--:|
| `nb1_features_and_config` | §4.1, §4.2, §6.1, §6.2, §6.3 | 6 |
| `nb2_splitting_and_pool` | §5, §5.2.1, §5.4 | 18 |
| `nb3_validation_and_plots` | §6.4, §7 | 7 + 2 figures |
| `nb4_results_three_axes` | §8 | 13 + 2 figures |
| `nb5_data_exploration` | §3 — which had **no artifact at all** before this | label bias, ontology topology, parent-vs-child AUC |
| `nb3b_hub_bias_meter` | §7.2 | recomputes the meter, which has no recipe |

**Figures.** `nb3` fig. 1 per-family AUC (distribution + ranked curve), fig. 2 the
association-vs-therapeutic orthogonality scatter with regression. `nb4` fig. 1 discovery lift and
absolute recovery vs K, fig. 2 tractability naive-vs-degree-matched under both estimators with the
rank-20 crossover marked. They render inline in the notebook; the `Agg` backend means the same code also
runs headless.

**They are assertion-first.** Every value the documentation quotes is compared against live data and
printed `PASS` or `STALE`, so drift fails loudly instead of rotting silently. Each notebook stamps
`scored_m3`'s row count first, so its output is dated to a build.

**What the first run found (2026-08-19).** §5 and §8 were clean — the only failure there was a
mis-specified assertion, not a stale document. Everything else it turned up:

- **`split_audit_2` did not exist.** Its recipe had been failing since the migration because the code
  still named the pre-migration datasets, so the leakage guarantee behind every AUC was unverified.
- **§7.2's central claim was refuted** — the champion is *worse* on hub bias than its predecessor, and
  the cause is a feature dropped as "neutral" on two axes while being load-bearing on a third.
- **§6 failed on six values**, including train/test sizes that summed to nothing.
- **The gene-popularity shortcut reaches the association axis**: `gene_n_diseases` alone scores 0.8567,
  above the 12-feature champion.
- **§3.3's thesis was backwards** — specificity does not cost AUC; measured over 259 parent-child pairs
  the more specific term wins 56.4% of the time.

All now fixed or recorded. See [DECISIONS.md](../DECISIONS.md), 2026-08-19.

**Sampling note.** `nb1` samples 25% of `psplit_train_set`. The full 2.19M × 31 frame plus a Spearman
matrix gets OOM-killed (exit 137). A quarter resolves null rates to ~0.1 pp, far finer than any claim.
