# Assertion notebooks

> **Lifecycle:** Evidence · **Audience:** reviewers re-deriving documented numbers · **Authority:** the
> assertion scripts themselves, plus their map and execution order · **Update when:** a script, guarded
> claim or execution dependency changes · **Generated dependencies:** none — these files are the source
> · **Excludes:** modelling rationale and narrative interpretation.

**These files are the source of truth, not a mirror.** They run on the **`primekg_kg`** code env.
`tools/push_assertions.py --push` copies them into the DSS project library under
`/python/nb_assertions/`, and the `validate_notebooks` scenario executes them there through
`nb_assertions/runner.py` — one two-line step per script. `tools/check_indexes.sh` fails on any
repo/library drift, and `.index/assertions.tsv` is parsed from these files, so the index describes
exactly the code that runs.

**They are assertion-first.** Every value the documentation quotes is compared against live data and
printed `PASS` or `STALE`, so drift fails loudly instead of rotting silently. The failure contract
lives in the runner, not here: six of the seven scripts only *print* their stale count and return
normally, so run bare they would report success over stale numbers. `runner.py` inspects each
script's own `FAIL` list afterwards and raises. Do not "fix" that by editing the script tails — the
index parses their assertion text and values.

> **The DSS notebooks were retired on 2026-09-03**, archived in
> [`../archive/notebooks-dss-2026-09-03/`](../archive/notebooks-dss-2026-09-03/). They were previously
> the primary copy and `tools/pull_notebooks.py` pulled DSS → repo; both are gone. Retiring them
> removed broken code, not work: three had drifted, and every dataset read only by the DSS side
> (`pool_selection_bias`, `breast_panel_overlap`, `lung_granularity_check`, `safety_lift`,
> `tractability_lift`) has since been deleted, while every dataset read only by these scripts still
> exists, so they could no longer run.

---

## Read them in this order — the MLOps lifecycle, not the document's

The filenames follow `TARGET_PRIORITIZER.md`'s section numbers (§3–§8), which is **not** the order the
work happens in. A reviewer coming to this cold should follow the lifecycle:

| # | lifecycle stage | notebook | backs | reads from |
|--:|---|---|---|---|
| 1 | **Data understanding** | `nb5_data_exploration` | §3 | zone 00 — raw graph |
| 2 | **Feature engineering** | `nb1_features_and_config` *(first half)* | §4.1, §4.2 | zone 30 — `psplit_train_set` |
| 3 | **Split & leakage control** | `nb2_splitting_and_pool` | §5, §5.2.1, §5.4 | zone 30, A2 |
| 4 | **Model selection & config** | `nb1_features_and_config` *(second half)* | §6.1, §6.3 | zone 31 — `scored_champion` |
| 5 | **Offline evaluation** | `nb3_validation_and_plots` | §6.4, §7.1, §7.3, §7.4 | zone 31, A2 |
| 6 | **Robustness / bias audit** | `nb3b_hub_bias_meter` | §7.2 | zone 31 |
| 7 | **Impact validation** | `nb4_results_three_axes` | §8 | zone 31, A2, A4 |
| 8 | **Communication** | `nb6_interrogation_and_close` | demo acts 5–6 | zone 31, A4 |
| 9 | **Demo panel selection** | `nb7_panel_selection` | which families and diseases the demo carries | zone 31, A2, A4 |

⚠ **`nb1` spans two stages that the split sits between.** Its §4 half analyses features on the training
set (stage 2, pre-split); its §6 half chooses the operating threshold (stage 4, post-split). Reading it
as one unit invites the impression that the threshold was picked before the split. Split the file when
someone next touches it.

⚠ **Stage 6 is measured twice, on purpose.** `nb3` §7.2 asks *"does the top 50 over-sample
high-degree genes?"* — about the **ranking**. `nb3b` asks *"with biology held constant, does the model
under-score poorly-connected true targets?"* — about **detection**, and it is the source of the 0.59 →
0.79 finding. They point opposite ways and both are true. `nb6` §5.2 carries `nb3b`'s version for the
demo; `nb3b` remains the canonical artifact until acts 5–6 are signed off.

---

## The notebook rule, and how far each notebook is from it

> Read the **most upstream** dataset that still carries the number and recompute in code. Reading a
> derived table and asserting its contents proves the recipe still runs, not that the number is right.

Zone `90` was framed as a **staging area for deletion**, on the reasoning that a script still reading
from it had not yet been converted. Recomputed from live DSS on 2026-09-03 — every dataset below
exists, and **no script reads a dataset that does not**:

| script | dataset reads | of which in zone 90 |
|---|--:|---|
| `nb1` | 2 | — |
| `nb3b` | 1 | — *(exemplar: it has no recipe, so this script IS its artifact)* |
| `nb5` | 5 | — |
| `nb7` | 6 | — |
| `nb2` | 5 | `pool_reachability` |
| `nb3` | 4 | `family_auc_by_family` |
| `nb6` | 12 | `tractability_axis` |
| `nb4` | 9 | `breast_panel_metrics`, `tractability_axis` |

Four zone-90 datasets are read by a script; the other three (`family_auc_grouped`,
`family_validation_ranked`, `family_validation_scored`) are recipe intermediates in the
`family_auc_by_family` chain.

**The old blocker is cleared.** `safety_lift` and `tractability_lift` were named as the acute case —
carrying the act-6 punch line, gating any pruning, and requiring `nb6` to run green first. Both
datasets have since been deleted, and `nb6` now runs green (34 checks, 0 stale). Note also that
`family_auc_by_family` is read by the **webapp** as well as `nb3`, so zone 90 is no longer
notebook-only staging and its description overstates how disposable it is.

`nb7` is the one script with a repository dependency: it compares live DSS data against frozen
expectations in `docs/demo/panel_selection/analysis/eyeball_test.csv`, and guards every figure in
`docs/demo/panel_selection.html`. Run it after any graph rebuild, gate move, champion change or
persona-filter repoint. `tools/push_assertions.py` uploads that CSV alongside the scripts so the
relative path resolves in DSS.

---

## Figures — and where they went

The plotting code is still here and still runs headless under the `Agg` backend, but **a scenario
step has nowhere to render to**, so these figures are no longer viewable anywhere. The last rendered
copies are archived in
[`../archive/notebooks-dss-2026-09-03/`](../archive/notebooks-dss-2026-09-03/):

| script | figure | still shown to the audience? |
|---|---|---|
| `nb1` | hub / network feature correlations | no equivalent |
| `nb3` | per-family AUC — distribution + ranked curve | Act 2 histogram / beeswarm |
| `nb3` | association-vs-therapeutic orthogonality scatter with regression | Act 2 orthogonality scatter |
| `nb4` | discovery lift and absolute recovery vs K | Act 4 lift table |
| `nb4` | tractability naive-vs-degree-matched, both estimators, rank-20 crossover marked | no equivalent |

Three of the five have a webapp equivalent, so the demo does not depend on them. The two that do not
are the feature-correlation heatmap and the tractability crossover — the latter backs the act-6 punch
line, so if that act is ever shown from a screen rather than a talk track it needs a home.

## Sampling note

`nb1` samples 25% of `psplit_train_set`. The full 2.19M × 31 frame plus a Spearman matrix gets
OOM-killed (exit 137). A quarter resolves null rates to ~0.1 pp, far finer than any claim.

## What the first run found (2026-08-19)

- **`split_audit_2` did not exist.** Its recipe had been failing since the migration because the code
  still named the pre-migration datasets, so the leakage guarantee behind every AUC was unverified.
- **§7.2's central claim was refuted** — the champion is *worse* on hub bias than its predecessor.
- **§6 failed on six values**, including train/test sizes that summed to nothing.
- **The gene-popularity shortcut reaches the association axis**: `gene_n_diseases` alone scores 0.8567.
- **§3.3's thesis was backwards** — over 259 parent-child pairs the more specific term wins 56.4%.

All fixed or recorded — see the
[historical decision index](../.index/decisions_history.tsv), 2026-08-19.
