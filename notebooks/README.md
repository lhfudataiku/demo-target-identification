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

> **The direction reversed on 2026-09-03.** These were previously mirrors of DSS-hosted Jupyter
> notebooks, and `tools/pull_notebooks.py` pulled DSS → repo. That is now deprecated and would destroy
> the working copy: three DSS notebooks had drifted, and every dataset read only by the DSS side
> (`pool_selection_bias`, `breast_panel_overlap`, `lung_granularity_check`, `safety_lift`,
> `tractability_lift`) has since been deleted, while every dataset read only by these scripts still
> exists. The DSS notebooks cannot run.

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

Zone `90 Notebook — validation evidence` is a **staging area for deletion**, not a home. A notebook
still reading from it has not yet been converted.

| notebook | upstream reads | still reading zone 90 | status |
|---|--:|---|---|
| `nb3b` | 1 | — | ✅ exemplar — *"it has no recipe, so this notebook IS its artifact"* |
| `nb5` | 4 | — | ✅ counts associations from raw edges |
| `nb1` | 2 | — | ✅ structurally clean *(but see §15.3 — its feature list is stale)* |
| `nb2` | 2 | `pool_reachability`, `pool_selection_bias` | ⚠️ 2 to convert |
| `nb3` | 2 | `drug_target_benchmark`, `family_auc_by_family` | ⚠️ 2 to convert |
| `nb6` | 4 | `novel_discovery_eval`, `drug_target_benchmark`, `tractability_axis`, `tractability_lift`, `safety_lift`, `lung_granularity_check`, `breast_panel_overlap` | ⚠️ 7 — adopts them so they are guarded before deletion |
| `nb7` | 30 | `family_panel`, `persona_enrichment`, `dashboard_candidates`, `scored_champion`, `gene_crosswalk` — guards every figure in `docs/demo/panel_selection.html` and the tables in `docs/demo/panel_selection/`. Run after any graph rebuild, gate move, champion change or persona-filter repoint |
| `nb4` | 3 | `breast_panel_metrics`, `breast_panel_overlap`, `known_drug_truth`, `novel_discovery_eval`, `tractability_axis` | ⚠️ 5 to convert — worst |

**Nothing in zone 90 can be deleted while a notebook still reads it.** `safety_lift` and
`tractability_lift` are the acute case: no recipe, no webapp and no other notebook touches them, and
they carry the entire act-6 punch line. `nb6` must run green first.

---

## Figures

`nb3` fig. 1 per-family AUC (distribution + ranked curve), fig. 2 the association-vs-therapeutic
orthogonality scatter with regression. `nb4` fig. 1 discovery lift and absolute recovery vs K, fig. 2
tractability naive-vs-degree-matched under both estimators with the rank-20 crossover marked. They
render inline; the `Agg` backend means the same code runs headless.

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
