# Top-5 SHAP drivers per scored pair, for the shortlist's "Why this ranking?" tab (webapp redesign D2).
# persona2_scored_shap5 -> candidate_shap_top5, one row per (disease_index, gene_index).
# ----------------------------------------------------------------------------
# BESIDE THE OLD CHAIN, NOT IN IT. compute_top_shap_drivers_1 keeps the top TWO of the main scoring
# run as a rendered string (top_shap_drivers), which rank_per_disease, dashboard_candidates, nb6 and
# nb7 depend on. This recipe reads a SECOND scoring run of the same saved model with
# nbExplanations = 5 (score_persona_candidates_shap5) and changes nothing upstream.
#
# shap_top5 is a JSON list, strongest |SHAP| first, of up to five
#     {"feature", "shap", "value", "percentile"}
# where percentile is the share of THIS disease's pool the gene is STRONGER than on that feature:
# strict inequality, so ties never inflate it, and for prox_closest (hop distance) stronger means
# FEWER hops. This is the definition GET /api/candidates/gene uses (backend/routes/candidates.py);
# LOWER_IS_STRONGER mirrors backend/feature_glossary.py and must move with it.
#
# It carries prox_kernel's value and percentile, the one champion input dashboard_candidates lacks,
# so no column is added there.
# ----------------------------------------------------------------------------
import json

import dataiku
import numpy as np
import pandas as pd

LOWER_IS_STRONGER = {"prox_closest"}
N = 5

src = dataiku.Dataset("persona2_scored_shap5")
df = src.get_dataframe()
df["disease_index"] = df["disease_index"].astype("int64")
df["gene_index"] = df["gene_index"].astype("int64")

parsed = df["explanations"].map(lambda s: json.loads(s) if isinstance(s, str) and s else {})
features = sorted({f for d in parsed for f in d})
missing = [f for f in features if f not in df.columns]
if missing:
    raise ValueError(f"explained features absent from the scored set: {missing}")
print(f"{len(df):,} pairs; explanations per pair:", parsed.map(len).value_counts().to_dict())

# Percentile of every pair on every explained feature, within its disease's pool.
pct = pd.DataFrame(index=df.index, columns=features, dtype="float64")
for _, idx in df.groupby("disease_index").groups.items():
    pool = df.loc[idx]
    for f in features:
        v = pool[f].to_numpy(dtype="float64")
        ok = ~np.isnan(v)
        vals = np.sort(v[ok])
        if not len(vals):
            continue
        if f in LOWER_IS_STRONGER:
            beaten = len(vals) - np.searchsorted(vals, v[ok], side="right")
        else:
            beaten = np.searchsorted(vals, v[ok], side="left")
        pct.loc[pool.index[ok], f] = np.round(100.0 * beaten / len(vals), 1)


def num(x):
    return None if x is None or x != x else float(x)


def top(i):
    ranked = sorted(parsed[i].items(), key=lambda kv: abs(kv[1]), reverse=True)[:N]
    return json.dumps([{"feature": f, "shap": round(float(s), 6), "value": num(df.at[i, f]),
                        "percentile": num(pct.at[i, f])} for f, s in ranked])


out = df[["disease_index", "gene_index"]].copy()
out["shap_top5"] = [top(i) for i in df.index]
if out.duplicated(["disease_index", "gene_index"]).any():
    raise ValueError("more than one scored row for a pair")
dataiku.Dataset("candidate_shap_top5").write_with_schema(out)

