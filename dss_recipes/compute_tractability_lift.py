# Would tractability features help? Answer it WITHOUT training, by measuring what a model
# trained on each label would be able to learn from them.
#
# WHY: m5b showed that adding a genuinely informative gene-level signal under the `is_target`
# objective improved association AUC (+0.0005) and DAMAGED drug AUC (-0.0301). Tractability is
# also a gene-level signal, so the same trap applies. Before spending another training run,
# measure the lift of each tractability attribute against BOTH labels:
#   - if tractability predicts `is_target` weakly or negatively, a model trained on `is_target`
#     will learn to DISCOUNT it, making drug-target ranking worse -- the m5b outcome again.
#   - if it predicts drug-validated status strongly, it belongs with the label change (point 3),
#     not before it.
#
# Restricted to the 112 diseases that have >=1 drug-validated target, so both labels are
# measured on exactly the same rows.
import dataiku
import numpy as np
import pandas as pd

nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
nodes["node_index"] = nodes.node_index.astype(int)
nodes["node_id"] = nodes.node_id.astype(str)
dis_map = dict(zip(nodes[nodes.node_type == "disease"].node_id,
                   nodes[nodes.node_type == "disease"].node_index))
gene_map = dict(zip(nodes[nodes.node_type == "gene/protein"].node_id,
                    nodes[nodes.node_type == "gene/protein"].node_index))
dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
# Dataset DEMO_KG_LS.drug_protein_edges renamed to DEMO_KG_drug_protein_edges_copy by liheng.fu@dataiku.com on 2026-08-18 09:42:34
# Dataset DEMO_KG_drug_protein_edges_copy renamed to drug_protein_edges by liheng.fu@dataiku.com on 2026-08-18 09:57:33
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
truth["is_validated"] = 1

# Dataset validation_set_2_scored renamed to scored_m2 by liheng.fu@dataiku.com on 2026-08-13 12:19:46
df = dataiku.Dataset("scored_champion").get_dataframe(
    columns=["disease_index", "gene_index", "is_target"])
df = df[df.disease_index.isin(set(truth.disease_index))]
df = df.merge(truth, on=["disease_index", "gene_index"], how="left")
df["is_validated"] = df.is_validated.fillna(0).astype(int)
drg = dataiku.Dataset("enriched_gene_druggability_v2").get_dataframe()
df = df.merge(drg, on="gene_index", how="left")

base_a = df.is_target.mean()
base_d = df.is_validated.mean()
print(f"rows {len(df):,} over {df.disease_index.nunique()} diseases")
print(f"base rate  association {base_a:.4%}   drug-validated {base_d:.4%}\n")

rows = []
print(f"{'attribute = value':44s}{'n':>10s}{'assoc lift':>12s}{'drug lift':>11s}")
print("-" * 78)
for col in ["ot_ab_tractable", "ot_sm_tractable", "localization_class", "ot_class_l1"]:
    for v, g in df.groupby(df[col].fillna("(null)")):
        if len(g) < 2000:
            continue
        la = g.is_target.mean() / base_a
        ld = g.is_validated.mean() / base_d
        rows.append({"attribute": col, "value": str(v), "n": len(g),
                     "assoc_rate": g.is_target.mean(), "drug_rate": g.is_validated.mean(),
                     "assoc_lift": la, "drug_lift": ld})
        print(f"{col + ' = ' + str(v):44s}{len(g):>10,}{la:>11.2f}x{ld:>10.2f}x")
    print()

out = pd.DataFrame(rows)
print("=== the decisive comparison ===")
print("  spread = max lift / min lift across an attribute's values.")
print("  A big DRUG spread with a flat ASSOC spread means the feature is informative for the")
print("  therapeutic label but invisible to -- or misleading for -- the association label.\n")
print(f"{'attribute':24s}{'assoc spread':>14s}{'drug spread':>13s}")
for col, g in out.groupby("attribute"):
    print(f"{col:24s}{g.assoc_lift.max()/max(g.assoc_lift.min(),1e-9):>13.2f}x"
          f"{g.drug_lift.max()/max(g.drug_lift.min(),1e-9):>12.2f}x")

dataiku.Dataset("tractability_lift").write_with_schema(out)


