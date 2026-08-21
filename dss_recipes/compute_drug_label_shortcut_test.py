# Is m7's 0.9324 drug-target AUC real disease-specific prediction, or a GENE-POPULARITY shortcut?
#
# THE CONCERN: the drug-target universe is only 778 genes of 20,861, and those genes recur across
# diseases. The split is by disease, so no evaluation PAIR was seen in training -- but the GENES
# were. A model that learns "these ~800 genes get drugged" scores well on held-out diseases while
# knowing nothing disease-specific. Same structural failure as `gene_n_diseases`, rejected earlier
# as label-derived.
#
# THE TEST: build the dumbest possible gene-level predictor -- for each gene, how many TRAIN
# diseases is it a drug target for -- and score validation diseases with it. It contains zero
# disease-specific information and zero graph topology.
#   * if it approaches 0.9324, m7 is a gene-popularity lookup and the gain is an artifact
#   * if it lands far below, m7 learned something disease-specific and the gain is real
import dataiku
import numpy as np
import pandas as pd

SCORE = "proba_1"

train = dataiku.Dataset("psplit_train_drug").get_dataframe(
    columns=["disease_index", "gene_index", "is_drug_target_weak"])
pop = (train[train.is_drug_target_weak == 1]
       .groupby("gene_index").disease_index.nunique().rename("gene_popularity"))
print(f"genes that are a drug target in >=1 TRAIN disease: {len(pop):,}")
print(f"  popularity distribution: median {pop.median():.0f}, max {pop.max()}, "
      f"share of all genes {len(pop)/20861:.1%}")

val = dataiku.Dataset("scored_m7").get_dataframe(
    columns=["disease_index", "gene_index", "is_target", "is_drug_target_strict", SCORE])
val = val.merge(pop, left_on="gene_index", right_index=True, how="left")
val["gene_popularity"] = val.gene_popularity.fillna(0)


def auc(g, mask, col):
    n1, n0 = int(mask.sum()), int((~mask).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
    r = g[col].rank()
    return (r[mask].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


rows = []
for d, g in val.groupby("disease_index"):
    m = g.is_drug_target_strict == 1
    if not m.any():
        continue
    rows.append({"disease_index": d, "n_drug": int(m.sum()),
                 "auc_m7": auc(g, m, SCORE),
                 "auc_popularity": auc(g, m, "gene_popularity")})
out = pd.DataFrame(rows).dropna()
print(f"\n=== {len(out)} diseases with a strict drug target ===")
print(f"  m7 (12 graph features, drug label) : {out.auc_m7.mean():.4f}")
print(f"  gene-popularity baseline (no graph): {out.auc_popularity.mean():.4f}")
print(f"  m3-f12 (association label)         : 0.6836")
gap = out.auc_m7.mean() - out.auc_popularity.mean()
print(f"\n  m7 advantage over the shortcut     : {gap:+.4f}")
print(f"  diseases where m7 beats popularity : {int((out.auc_m7 > out.auc_popularity).sum())} of {len(out)}")
print(f"  correlation of the two AUCs        : r = {out.auc_m7.corr(out.auc_popularity):.3f}")
if gap < 0.05:
    print("\n  VERDICT: the gain is essentially a gene-popularity artifact.")
else:
    print("\n  VERDICT: m7 carries disease-specific signal beyond gene popularity.")
dataiku.Dataset("drug_label_shortcut_test").write_with_schema(out)
