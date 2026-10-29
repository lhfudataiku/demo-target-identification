# Assertion notebooks

> **Lifecycle:** Evidence · **Audience:** reviewers re-deriving documented numbers · **Authority:** the
> assertion scripts themselves, plus their map and execution order · **Update when:** a script, guarded
> claim or execution dependency changes · **Generated dependencies:** none — these files are the source
> · **Excludes:** modelling rationale and narrative interpretation.

**These files are the source of truth, not a mirror.** Each script re-derives the numbers the
documentation quotes from live DSS data and prints `PASS` or `STALE` beside each one, so a number that
drifts fails loudly instead of rotting silently. `.index/assertions.tsv` is parsed from these files,
so the index describes exactly the code that runs.

## Running them

They run on your machine, against the evidence project `DEMO_TI_EVIDENCE` (`DEC-OPS-007`,
[ADR-003](../docs/decisions/adrs/ADR-003-evidence-project.md)):

```bash
uv sync --project notebooks
eval "$(dku auth export-env)"
uv run --project notebooks python tools/run_notebooks.py --out data/assertion_runs/<date>.json
```

- **About 15 minutes for all seven.** `--only nb3_validation_and_plots` runs one script.
- **Green means every script passes.** On 2026-10-29: 7 scripts, 150 checks, 0 stale. The exit code
  is non-zero if any script has a stale check, and `--out` records the per-script counts. Keep that
  file under `data/`, which is never committed.
- **`nb5` is not in the run.** It explores the data and asserts nothing, and the runner refuses a
  script without checks. Run it directly when you want its output.
- **Nothing in DSS runs them.** There is no scenario and no DSS copy: the `validate_notebooks`
  scenario and the `/python/nb_assertions/` library folder were deleted on 2026-10-29. So a change
  to the flow can move a quoted number until someone runs them; run them after a model, graph or
  recipe change.
- **After a champion change, rebuild the evidence flow first.** Its datasets are copies, and they
  only see the new champion once rebuilt.

**Where the scripts read.** `tools/run_notebooks.py` makes the evidence project the default, so a
bare name such as `"dashboard_candidates"` reads the evidence copy. The main project's upstream
datasets — the graph, the features, the split and `scored_champion` — are read by qualified name,
such as `"DEMO_TARGET_IDENTIFICATION.scored_champion"`. No script reads a main-project serving zone.

**The failure contract lives in the runner, not in the scripts.** Six of the seven scripts only
*print* their stale count and return normally, so run bare they would report success over stale
numbers. `tools/nb_assertions/runner.py` inspects each script's own `FAIL` list afterwards and
raises. Do not "fix" that by editing the script tails: the index parses their assertion text and
values.

---

## Read them in this order — the MLOps lifecycle, not the document's

The filenames follow `TARGET_PRIORITIZER.md`'s section numbers (§3–§8), which is **not** the order the
work happens in. A reviewer coming to this cold should follow the lifecycle:

| # | lifecycle stage | notebook | backs | main project (qualified) | evidence project |
|--:|---|---|---|---|---|
| 1 | **Data understanding** | `nb5_data_exploration` | §3 | graph, features | E1 |
| 2 | **Feature engineering** | `nb1_features_and_config` *(first half)* | §4.1, §4.2 | `psplit_train_set` | — |
| 3 | **Split & leakage control** | `nb2_splitting_and_pool` | §5, §5.2.1, §5.4 | features, `scored_champion` | E1, E4 |
| 4 | **Model selection & config** | `nb1_features_and_config` *(second half)* | §6.1, §6.3 | `scored_champion` | — |
| 5 | **Offline evaluation** | `nb3_validation_and_plots` | §6.4, §7.1, §7.3, §7.4 | `scored_champion` | E1 |
| 6 | **Robustness / bias audit** | `nb3b_hub_bias_meter` | §7.2 | `scored_champion` | — |
| 7 | **Impact validation** | `nb4_results_three_axes` | §8 | `scored_champion`, drug imports | E1, E2, E4 |
| 8 | **Communication** | `nb6_interrogation_and_close` | demo acts 5–6 | graph, drugs, annotations, `scored_champion` | E1, E2, E3 |
| 9 | **Demo panel selection** | `nb7_panel_selection` | which families and diseases the demo carries | — | E1, E2, E3 |

The evidence project's zones: **E1** rebuilds the validation metrics (per-disease and per-family AUC,
the split audit, the benchmarks, the personas); **E2** the family panels; **E3** a slim shortlist, the
12 shortlist diseases ranked with ties; **E4** the drug ground truth, pool reachability, the three-axis
filter and the breast panel.
[`EVIDENCE_PROJECT_DESIGN.md`](../docs/operations/EVIDENCE_PROJECT_DESIGN.md) lists every read.

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

## The notebook rule

> Read the **most upstream** dataset that still carries the number and recompute in code. Reading a
> derived table and asserting its contents proves the recipe still runs, not that the number is right.

`nb3b` is the exemplar: it reads only `scored_champion` and has no recipe, so the script is its own
artifact. `nb4` and `nb6` get the tractability axis from `tools/nb_assertions/derive.py`, which
recomputes it from four upstream datasets; its dataset was deleted on 2026-09-03 once the two agreed.

`nb7` is the one script with a repository dependency: it compares live data against frozen
expectations in `docs/demo/panel_selection/analysis/eyeball_test.csv`, and guards every figure in
`docs/demo/panel_selection.html`. Run it after any graph rebuild, gate move, champion change or
persona-filter repoint.

---

## Figures — and where they went

The plotting code still runs, but the runner sets the `Agg` backend, so a run draws nothing on screen.
The last rendered copies are archived in
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

## History

- **2026-08-19, the first run** found that `split_audit_2` did not exist, so the leakage guarantee
  behind every AUC was unverified; that §7.2's central claim was refuted (the champion is *worse* on
  hub bias than its predecessor); that §6 failed on six values; that `gene_n_diseases` alone scores
  0.8567 on the association axis; and that §3.3's thesis was backwards. All were fixed or recorded in
  the [historical decision index](../.index/decisions_history.tsv).
- **2026-09-03, the DSS notebooks were retired** and archived in
  [`../archive/notebooks-dss-2026-09-03/`](../archive/notebooks-dss-2026-09-03/). Three had drifted,
  and the datasets only they read had been deleted. The scripts then ran in DSS through the
  `validate_notebooks` scenario.
- **2026-10-28 and 10-29, the scripts moved to a local run against the evidence project**
  ([workplan](../docs/operations/FLOW_MIGRATION_WORKPLAN.md) M2). The datasets only they read left the
  main project, and the scenario and library copy were deleted. Every script kept its checks and
  counts.
