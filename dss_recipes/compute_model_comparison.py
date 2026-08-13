# Side-by-side evaluation of the ablation ladder on BOTH benchmarks.
#
# WHY: the project has been ranked on association-label AUC, which is uncorrelated with
# therapeutic relevance (Pearson r = 0.097 across 112 diseases). Every model from here on
# has to report both numbers, or an improvement on one can hide a regression on the other.
#
# Models compared (all trained on enriched_train_full_2 / enriched_test_set_2, identical
# hyperparameters, seed 1337, EXPLICIT_FILTERING_TWO_DATASETS):
#   m4  77y7OGMb  13 features, IMPUTE MEAN            -- the incumbent
#   m5  8SbUo8PU  FLAG_PRESENCE (values replaced)     -- missingness signal ALONE
#   m5b hsLcZJir  13 features, sentinel imputation    -- value + learnable missingness
#   m6  cr38dN8N  12 features, prox_closest dropped   -- removes the channel that is
#                                                        blind to drug targets (12% of the
#                                                        way from background vs 90% for
#                                                        ppi_adamic_adar)
import dataiku
import numpy as np
import pandas as pd

MODELS = [("m4  13f impute-mean", "validation_set_2_scored"),
          ("m5  flags only", "validation_set_2_scored_m5"),
          ("m5b 13f sentinel", "validation_set_2_scored_m5b"),
          ("m6  12f no prox", "validation_set_2_scored_m6")]
SCORE = "proba_1"

nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
nodes["node_index"] = nodes.node_index.astype(int)
nodes["node_id"] = nodes.node_id.astype(str)
dis_map = dict(zip(nodes[nodes.node_type == "disease"].node_id,
                   nodes[nodes.node_type == "disease"].node_index))
gene_map = dict(zip(nodes[nodes.node_type == "gene/protein"].node_id,
                    nodes[nodes.node_type == "gene/protein"].node_index))
dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
ind = dd[dd.relation.astype(str).str.fullmatch("indication", case=False, na=False)].copy()
dcol, xcol = ("x_id", "y_id") if (ind.x_type == "drug").any() else ("y_id", "x_id")
ind["drug"] = ind[dcol].astype(str)
ind["disease_index"] = ind[xcol].astype(str).map(dis_map)
gcol, tcol = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
dp["drug"] = dp[gcol].astype(str)
dp["gene_index"] = dp[tcol].astype(str).map(gene_map)
truth = (ind.dropna(subset=["disease_index"])[["drug", "disease_index"]]
         .merge(dp.dropna(subset=["gene_index"])[["drug", "gene_index"]], on="drug")
         [["disease_index", "gene_index"]].astype(int).drop_duplicates())
tset = truth.groupby("disease_index").gene_index.apply(set).to_dict()


def auc_of(g, mask):
    n1, n0 = int(mask.sum()), int((~mask).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
    r = g[SCORE].rank()
    return (r[mask].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


rows = []
for label, ds in MODELS:
    df = dataiku.Dataset(ds).get_dataframe(
        columns=["disease_index", "gene_index", "is_target", SCORE])
    for d, g in df.groupby("disease_index"):
        val = tset.get(d)
        rec = {"model": label, "disease_index": d,
               "auc_assoc": auc_of(g, g.is_target == 1),
               "n_assoc": int(g.is_target.sum())}
        if val:
            m = g.gene_index.isin(val)
            if m.any():
                gg = g.sort_values(SCORE, ascending=False).reset_index(drop=True)
                mm = gg.gene_index.isin(val)
                rec["auc_drug"] = auc_of(g, m)
                rec["n_drug"] = int(m.sum())
                rec["hits_at_50"] = int(mm.head(50).sum())
        rows.append(rec)

out = pd.DataFrame(rows)
print("=== ablation ladder, both benchmarks ===")
print(f"{'model':22s}{'assoc AUC':>11s}{'drug AUC':>10s}{'hits@50':>9s}"
      f"{'n_dis':>7s}{'n_drug_dis':>11s}")
for label, _ in MODELS:
    s = out[out.model == label]
    a = s.auc_assoc.dropna()
    dr = s.auc_drug.dropna()
    print(f"{label:22s}{a.mean():>11.4f}{dr.mean():>10.4f}"
          f"{int(s.hits_at_50.sum()):>9d}{len(a):>7d}{len(dr):>11d}")

print("\n=== paired deltas vs m4 (same diseases only) ===")
base = out[out.model == MODELS[0][0]].set_index("disease_index")
for label, _ in MODELS[1:]:
    s = out[out.model == label].set_index("disease_index")
    ja = base.auc_assoc.dropna().index.intersection(s.auc_assoc.dropna().index)
    jd = base.auc_drug.dropna().index.intersection(s.auc_drug.dropna().index)
    da = (s.loc[ja].auc_assoc - base.loc[ja].auc_assoc)
    dd_ = (s.loc[jd].auc_drug - base.loc[jd].auc_drug)
    print(f"{label:22s} assoc {da.mean():+.4f} (better on {int((da > 0).sum())}/{len(da)})"
          f"   drug {dd_.mean():+.4f} (better on {int((dd_ > 0).sum())}/{len(dd_)})")

dataiku.Dataset("model_comparison").write_with_schema(out)
