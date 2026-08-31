# Panel selection — the supporting analysis

<!-- Governed claims consumed here: TI-MOD-001 TI-VAL-001 -->

> **Lifecycle:** Evidence · **Audience:** demo owners and reviewers selecting therapeutic areas and
> diseases · **Authority:** asserted panel-selection measurements and their interpretation · **Update
> when:** the champion, graph, seed gate, persona configuration or served panel changes · **Generated
> dependencies:** `nb7_panel_selection.py` and `built/` · **Excludes:** webapp implementation policy.

The evidence behind [`../panel_selection.html`](../panel_selection.html): which disease
families Act 3 can support, and which diseases Act 4 should shortlist. Measured 2026-08-27
over all 670 validation diseases against champion `m7-f14`.

**Every number in `built/` is regenerated and asserted by
[`notebooks/nb7_panel_selection.py`](../../../notebooks/nb7_panel_selection.py)** — 51 checks,
green as of 2026-08-28. Run it after any graph rebuild, seed-gate move, champion change, or
config edit; a `STALE` line means the flow and the document have diverged and one of them has
to move.

Six diseases in `analysis/eyeball_test.csv` are no longer served (obesity, multiple
sclerosis, SLE, atopic eczema, myeloma, ALL). Their ranks are the *evidence for rejecting
them* — obesity's GLP1R at #526, MS's 0-of-8 — so nb7 asserts only the served diseases;
there is nothing live left to guard for the rest.

## Two folders, and the difference matters

**`analysis/` — the decision record.** What was measured *before* the build, on the
curated candidate sets, to decide which families and diseases to carry. These files do
not change when the flow is rebuilt; they are the argument, and rewriting them would
erase why the panel looks the way it does.

| file | rows | what it settles |
|---|--:|---|
| `area_coverage.csv` | 3 | **The finding that decides Act 3.** Subtype structure exists only in oncology |
| `family_catalogue.csv` | 25 | Every family with ≥3 validation terms |
| `family_subtypes.csv` | 82 | Per-subtype AUC with 95% intervals for the six candidate families |
| `subtype_overlap.csv` + summary | 47 + 5 | Overlap on the **curated leaf sets** — breast 0.40 / uterine 0.49 / stomach 0.35 |
| `common_programme.csv` | 105 | The common-vs-specific split as first computed |
| `eyeball_test.csv` + summary | 113 + 13 | **The Act 4 ranking.** Where the field's validated targets rank, and why each was expected |
| `panel_before.csv` | 13 | The panel this replaced, on both bars |

**`built/` — what actually ships.** Dumped from the DSS datasets the app reads.

| file | rows | DSS dataset |
|---|--:|---|
| `demo_panel_config.csv` | 35 | `demo_panel_config` — membership as data |
| `family_metrics.csv` | 35 | `family_panel_metrics` — Act 3 cards 1–3 |
| `subtype_overlap.csv` | 148 | `family_panel_overlap` — the overlap card |
| `common_programme.csv` | 550 | `family_panel_programme` — common vs specific |
| `overlap_summary.csv` | 3 | reconciles the built figures against the analysis ones |

### Why the two overlap numbers differ, and why both are right

| family | analysis (curated leaves) | built (all usable terms + leaves) |
|---|--:|--:|
| breast | 0.402 | 0.430 |
| uterine | 0.494 | 0.478 |
| stomach | 0.350 | 0.451 |

The analysis compared only the terminal subtypes, to judge whether a family could
support a subtype-specific card. The built table includes the **parent terms**, because
showing that a parent is largely a blend of its children is the point of the card —
`gastric adenocarcinoma` shares 0.961 of its top 50 with its parent `gastric carcinoma`.
Different question, different set, both correct. Overlap tracks ontology distance either
way: Spearman −0.350 over the 148 shipped pairs.

## Two conventions worth knowing

**`n_pos >= 50` is the usability floor.** Below it an AUC interval spans half the range —
triple-negative breast has 8 positives and an interval of 0.749–1.041. A subtype under the
floor can still carry a *list*, but never a quotable AUC.

**Near-duplicate is Jaccard > 0.6 on the top 50.** Two subtypes above that tell the same
story, so a family full of them cannot support a subtype-specific card however distinct its
members are clinically. Lung is the case in point: adenocarcinoma vs squamous is 0.887.

## What is deliberately not committed

The per-row score dumps these tables derive from — `scored_champion` is 3.96M rows / 478 MB,
and the served rankings are 70 MB. `nb7` regenerates them from DSS on demand. Committing
them would put a stale copy of the flow in git, which is the failure this whole folder
exists to prevent.

## The expectations were written before the ranks

`eyeball_test.csv` carries a `why_expected` column naming the drug or the biology for every
gene — anti-TNF, dupilumab, setmelanotide, trastuzumab, and so on. That list was written
down *first*, then the ranks were looked up. `nb7` re-derives the ranks and leaves the
expectations alone, so the test cannot be quietly reshaped to fit the result.
