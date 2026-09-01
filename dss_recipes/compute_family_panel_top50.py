"""Top-50 ranking per panel term — the shared intermediate for Act 3's cards.

Exists so the graph is scanned ONCE. `scored_champion` is 3.96M rows / 478 MB;
the overlap card and the common-vs-specific card both need the same per-term top
50, and computing it in each would mean three full scans of the same table.

Covers every term in `demo_panel_config` -- Act 3 terms and Act 4 diseases alike,
so Act 4's shortlist can reuse it rather than growing its own copy.
"""

import dataiku
import pandas as pd

TOP_N = 50

cfg = dataiku.Dataset("demo_panel_config").get_dataframe()
want = set(cfg.disease_index.astype(int))
label = dict(zip(cfg.disease_index.astype(int), cfg.disease))

# Only the four columns the ranking needs. Reading all 45 would move ~478 MB to
# rank on one of them.
scored = dataiku.Dataset("scored_champion").get_dataframe(
    columns=["disease_index", "gene_index", "is_target", "proba_1"])
scored = scored[scored.disease_index.isin(want)].copy()

genes = dataiku.Dataset("gene_crosswalk").get_dataframe(columns=["node_index", "node_name"])
scored = scored.merge(genes.rename(columns={"node_index": "gene_index", "node_name": "gene"}),
                      on="gene_index", how="left")

# Rank on the champion probability. `method="first"` makes ties deterministic --
# without it the same query can reorder between runs, and a card that redraws
# differently on every load undermines the reproducibility claim.
scored["rank_in_disease"] = scored.groupby("disease_index").proba_1.rank(
    ascending=False, method="first").astype(int)
scored["pool"] = scored.groupby("disease_index").gene_index.transform("size")

# TWO rankings, because the cards ask two different questions.
#
#   rank_in_disease -- position among ALL candidates. Answers "how well is the
#                      known biology reconstructed".
#   novel_rank      -- position among NOVEL candidates only, a separate and deeper
#                      ranking. Answers "of the 50 genes you would actually look at
#                      next, how many do two subtypes share".
#
# The second is not derivable from the first: HER2+ has only ~2 novel genes inside
# its overall top 50, so intersecting overall-top-50 novels gives ~0 and hides the
# real answer (2 shared with triple-negative out of 50). The retired
# breast_panel_overlap measured the deeper one, and it was right to.
scored["novel_rank"] = (scored[scored.is_target == 0]
                        .groupby("disease_index").proba_1
                        .rank(ascending=False, method="first"))

out = scored[(scored.rank_in_disease <= TOP_N)
             | (scored.novel_rank <= TOP_N)].copy()
out["novel_rank"] = out.novel_rank.astype("Int64")
out["disease"] = out.disease_index.map(label)
out = out[["disease_index", "disease", "gene_index", "gene", "rank_in_disease",
           "novel_rank", "is_target", "proba_1", "pool"]].sort_values(
    ["disease_index", "rank_in_disease"])

missing = want - set(out.disease_index.astype(int))
if missing:
    raise ValueError(f"no scored rows for {len(missing)} config terms: "
                     f"{[label[m] for m in sorted(missing)][:5]}")
assert (out[out.rank_in_disease <= TOP_N].groupby("disease_index").size() <= TOP_N).all()

print(f"top50: {len(out)} rows over {out.disease_index.nunique()} terms "
      f"(overall<=50: {(out.rank_in_disease<=TOP_N).sum()}, novel<=50: {(out.novel_rank<=TOP_N).sum()})")
dataiku.Dataset("family_panel_top50").write_with_schema(out)

