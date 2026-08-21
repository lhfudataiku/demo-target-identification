# OPTION 1 verdict: does training on the drug label beat training on the association label,
# judged on the SAME held-out therapeutic ground truth?
#
# m7-drug-label was trained on `is_drug_target_weak` (indication OR investigational) with the
# identical 12 features, split, and hyperparameters as m3-f12. Only the objective changed.
#
# Evaluation is on `is_drug_target_strict` (approved indications only) over the validation
# split -- so we train on plausibility and score on what actually got approved. The reference
# to beat is m3-f12's mean per-disease drug-target AUC of 0.6836 over 112 diseases.
#
# Also computed: m7's AUC on the ASSOCIATION label. If the drug-trained model still ranks
# association genes well, the two objectives are compatible; if it collapses, they are in
# genuine tension and the choice of label is a product decision, not an optimisation.
import dataiku
import numpy as np
import pandas as pd

SCORE = "proba_1"
df = dataiku.Dataset("scored_m7").get_dataframe(
    columns=["disease_index", "gene_index", "is_target", "is_drug_target_strict", SCORE])
print(f"scored rows {len(df):,} | diseases {df.disease_index.nunique()}")


def auc(g, mask):
    n1, n0 = int(mask.sum()), int((~mask).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
    r = g[SCORE].rank()
    return (r[mask].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


rows = []
for d, g in df.groupby("disease_index"):
    m_drug = g.is_drug_target_strict == 1
    rec = {"disease_index": d,
           "n_drug": int(m_drug.sum()),
           "n_assoc": int(g.is_target.sum()),
           "auc_drug_m7": auc(g, m_drug),
           "auc_assoc_m7": auc(g, g.is_target == 1)}
    if m_drug.any():
        top = g.nlargest(50, SCORE)
        rec["hits_at_50"] = int((top.is_drug_target_strict == 1).sum())
    rows.append(rec)

out = pd.DataFrame(rows)
d = out.dropna(subset=["auc_drug_m7"])
a = out.dropna(subset=["auc_assoc_m7"])
print(f"\n=== m7 (trained on drug label) ===")
print(f"  diseases with a strict drug target : {len(d)}")
print(f"  mean per-disease DRUG-target AUC   : {d.auc_drug_m7.mean():.4f}   median {d.auc_drug_m7.median():.4f}")
print(f"  validated targets in top 50        : {int(d.hits_at_50.sum())} of {int(d.n_drug.sum())}"
      f"  ({d.hits_at_50.sum()/max(d.n_drug.sum(),1):.1%})")
print(f"  mean per-disease ASSOCIATION AUC   : {a.auc_assoc_m7.mean():.4f}   (m3-f12 scored 0.8228)")
print(f"\n  reference — m3-f12 mean drug-target AUC: 0.6836, 117 hits@50")
print(f"  delta on the therapeutic axis          : {d.auc_drug_m7.mean() - 0.6836:+.4f}")
print(f"\n  diseases where m7 drug AUC < 0.5: {(d.auc_drug_m7 < 0.5).sum()} of {len(d)}  (m3-f12: 26 of 112)")
dataiku.Dataset("drug_label_eval").write_with_schema(out)
