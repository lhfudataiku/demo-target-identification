# Retired DSS Jupyter notebooks — 2026-09-03

> **Lifecycle:** Historical · **Audience:** anyone asking what the DSS notebooks held before the
> release · **Authority:** none — this is a byte-for-byte record, not a current document ·
> **Update when:** never · **Excludes:** the assertion logic itself, which is current and lives in
> [`../../notebooks/`](../../notebooks/).

Nine Jupyter notebooks retired from `DEMO_TARGET_IDENTIFICATION` when the project release removed
all project notebooks. Preserved intact — code cells, markdown cells and rendered figure outputs —
so nothing here had to be judged worth keeping at the moment of deletion.

## Why they were retired rather than maintained

The assertion logic existed in three places: these notebooks, the `notebooks/*.py` scripts, and
inline copies pasted into the `validate_notebooks` scenario steps. `.index/assertions.tsv` was parsed
from the **scripts**, so the index described code that was not the code being run.

**These notebooks had already stopped working.** Measured on 2026-09-03, three had drifted from the
scripts, and every dataset read only by the notebook side had since been deleted:

| read only by the notebooks | status |
|---|---|
| `pool_selection_bias`, `breast_panel_overlap`, `lung_granularity_check`, `safety_lift`, `tractability_lift` | all deleted |

Every dataset read only by the scripts still existed. `tools/pull_notebooks.py` warned on nb6 that
*"the MIRROR is ahead — pulling would DISCARD assertions or figures"*. So retiring these removed
broken code, and the scripts are the surviving working copy.

The scripts now run in DSS from the project library under `/python/nb_assertions/`, executed by
`validate_notebooks` as one step per script through `nb_assertions/runner.py`. All seven pass: 150
checks, zero stale.

## What was unique to these files

**Five rendered figures.** Three have a webapp equivalent; two do not.

| notebook | cell | figure | webapp equivalent |
|---|--:|---|---|
| `nb1_features_and_config` | 7 | Hub / network feature correlations | **none** |
| `nb3_validation_and_plots` | 5 | per-family AUC distribution + sorted rank curve | Act 2 histogram / beeswarm |
| `nb3_validation_and_plots` | 7 | per-disease AUC vs drug-target-benchmark AUC | Act 2 orthogonality scatter |
| `nb4_results_three_axes` | 6 | lift vs K by ground truth (approved / investigational) | Act 4 lift table |
| `nb4_results_three_axes` | 11 | Tractability: naive vs degree-matched, both estimators | **none** — backs the act-6 punch line |

**About 7.5 KB of markdown narrative**, most of it in `nb6_interrogation_and_close` (3,692
characters). The scripts carry the same reasoning as comments, but the cell-level structure is only
here.

Also included, with no unique figures or narrative: `cypher_test` (32 cells, a Cypher scratchpad)
and `liheng fu@dataiku com's Python notebook` (6 cells). The project now holds no notebooks at all.
