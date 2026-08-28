# Panel selection — the supporting analysis

The evidence behind [`../panel_selection.html`](../panel_selection.html): which disease
families Act 3 can support, and which diseases Act 4 should shortlist. Measured 2026-08-27
over all 670 validation diseases against champion `m7-f14`.

**Every number in these tables is regenerated and asserted by
[`notebooks/nb7_panel_selection.py`](../../../notebooks/nb7_panel_selection.py).** Run it after
any graph rebuild, seed-gate move, champion change, or persona-filter repoint — a `STALE`
line means the document and the flow have diverged and one of them has to move.

## The tables

| file | rows | what it settles |
|---|--:|---|
| `area_coverage.csv` | 3 | **The finding that decides Act 3.** Subtype structure exists only in oncology: autoimmune has one family with ≥2 terms, CVRM has none with ≥2 *usable* terms |
| `family_catalogue.csv` | 25 | Every family with ≥3 validation terms — term count, usable count, median/best/worst AUC |
| `family_subtypes.csv` | 82 | Per-subtype AUC with 95% intervals for the six candidate families (breast, lung, uterine, heme, stomach, obesity) |
| `subtype_overlap.csv` | 47 | Pairwise top-50 Jaccard within each candidate family — what the "how much do the subtypes overlap" card measures |
| `subtype_overlap_summary.csv` | 5 | Mean / max overlap and near-duplicate count per family. **This is the Act 3 ranking** |
| `common_programme.csv` | 105 | Genes common to *every* subtype of a family — the "common programme vs subtype-specific" split |
| `panel_current.csv` | 13 | The currently served panel on both bars: association AUC and enrichment, plus approved-drug-target hits |
| `eyeball_test.csv` | 113 | Per (disease, expected target): where the field's validated target actually ranks, and whether it was already annotated |
| `eyeball_test_summary.csv` | 13 | Targets in top 20 / top 50 per disease. **This is the Act 4 ranking** |

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
