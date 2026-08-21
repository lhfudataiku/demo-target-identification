# Per-disease and per-split-key AUC for the set_2 model (m4, saved model 77y7OGMb).
#
# WHY: pooled AUC over a scored validation set is dominated by the largest disease modules
# and overstates performance by ~9 points (measured earlier in this project). The honest
# figure is the MEAN of per-disease AUCs, and -- because the split is now keyed on
# `disease_split_key` -- the mean of per-key AUCs, which stops a single well-annotated
# family from carrying the score.
#
# AUC via the Mann-Whitney rank-sum identity: with ASCENDING ranks,
#   AUC = (sum(ranks of positives) - n_pos*(n_pos+1)/2) / (n_pos * n_neg)
# (no `1 -`; that belongs to the descending-rank form). Diseases with zero positives or
# zero negatives have no defined AUC and are dropped, but still counted in the report.
import dataiku
import numpy as np
import pandas as pd

SCORE = "proba_1"
COLS = ["disease_index", "gene_index", "is_target", "disease_split_key",
        "split_key_name", "disease_family_id", "anchor_name", SCORE]

df = dataiku.Dataset("validation_set_2_scored").get_dataframe(columns=COLS)
print("scored rows:", len(df), "| diseases:", df.disease_index.nunique(),
      "| split keys:", df.disease_split_key.nunique())


def auc_table(frame, key):
    out = []
    for k, g in frame.groupby(key):
        n1 = int(g.is_target.sum())
        n0 = len(g) - n1
        if n1 == 0 or n0 == 0:
            out.append({key: k, "n_pos": n1, "n_neg": n0, "auc": np.nan,
                        "hits_at_50": np.nan, "recall_at_50": np.nan})
            continue
        r = g[SCORE].rank()
        auc = (r[g.is_target == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
        top = g.nlargest(50, SCORE)
        out.append({key: k, "n_pos": n1, "n_neg": n0, "auc": auc,
                    "hits_at_50": int(top.is_target.sum()),
                    "recall_at_50": top.is_target.sum() / n1})
    return pd.DataFrame(out)


by_dis = auc_table(df, "disease_index")
by_key = auc_table(df, "disease_split_key")

names = (df.drop_duplicates("disease_split_key")
           .set_index("disease_split_key").split_key_name.to_dict())
by_key["split_key_name"] = by_key.disease_split_key.map(names)

# pooled, for the record -- and to show the gap the per-disease mean corrects for
n1 = int(df.is_target.sum())
n0 = len(df) - n1
r = df[SCORE].rank()
pooled = (r[df.is_target == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

d = by_dis.dropna(subset=["auc"])
k = by_key.dropna(subset=["auc"])
print(f"\npooled AUC (all rows)        : {pooled:.4f}")
print(f"mean per-disease AUC  (n={len(d):4d}) : {d.auc.mean():.4f}  median {d.auc.median():.4f}")
print(f"mean per-split-key AUC (n={len(k):4d}) : {k.auc.mean():.4f}  median {k.auc.median():.4f}")
print(f"diseases with no defined AUC : {len(by_dis) - len(d)}")
print(f"\nper-disease AUC deciles:\n{d.auc.quantile(np.arange(0, 1.01, 0.1)).round(3).to_string()}")
print(f"\nworst 10 keys by AUC:\n"
      f"{k.nsmallest(10, 'auc')[['split_key_name', 'n_pos', 'auc']].to_string(index=False)}")
print(f"\nbest 10 keys by AUC:\n"
      f"{k.nlargest(10, 'auc')[['split_key_name', 'n_pos', 'auc']].to_string(index=False)}")

by_dis["level"] = "disease"
by_key["level"] = "split_key"
by_key = by_key.rename(columns={"disease_split_key": "disease_index"})
out = pd.concat([by_dis, by_key], ignore_index=True)
out["pooled_auc"] = pooled
dataiku.Dataset("validation_auc_by_disease_2").write_with_schema(out)
