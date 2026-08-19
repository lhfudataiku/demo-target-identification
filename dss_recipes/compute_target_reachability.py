# Are drug-validated targets REACHABLE by the topology feature set at all?
#
# WHY: this decides where to spend next. The drug-target benchmark showed the model ranks
# validated targets poorly (mean AUC 0.688) even inside the provably-drugged universe
# (F5: 19.5% in top 50). Two very different explanations remain:
#   (a) wrong OBJECTIVE -- the targets are topologically near the disease module, the features
#       can see them, but `is_target` never rewarded ranking them highly. Fix = labels.
#   (b) wrong INSTRUMENT -- the targets are topologically far from the module, so no
#       DWPC/PPI feature distinguishes them from background. Fix = different feature classes
#       (expression, perturbation), and no amount of extra ontology helps.
#
# The discriminating group is drug_only: drug-validated targets that are NOT association
# positives (1,309 of 1,507). If their features look like `neither`, it is (b). If they look
# like the association positives, it is (a).
#
# Values are reported as WITHIN-DISEASE PERCENTILES so diseases of different module size and
# feature scale can be pooled; null rates are reported separately because these features are
# 1-or-null rather than 1-or-0, and "unreachable" shows up as a null, not a low value.
import dataiku
import numpy as np
import pandas as pd

FEATS = ["prox_closest", "dwpc_GGD", "dwpc_GPGD", "dwpc_GBGD", "dwpc_GFGD",
         "ppi_adamic_adar", "ppi_jaccard", "ppi_common_neighbors_z",
         "shared_pathway_frac", "gene_ppi_degree", "proba_1"]

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

# Dataset validation_set_2_scored renamed to scored_m2 by liheng.fu@dataiku.com on 2026-08-13 12:19:46
sc = dataiku.Dataset("scored_m3").get_dataframe(
    columns=["disease_index", "gene_index", "is_target"] + FEATS)
# keep only diseases that HAVE validated targets, so all four groups are comparable
sc = sc[sc.disease_index.isin(set(truth.disease_index))].copy()
truth["is_validated"] = 1
sc = sc.merge(truth, on=["disease_index", "gene_index"], how="left")
sc["is_validated"] = sc.is_validated.fillna(0).astype(int)

sc["group"] = np.select(
    [(sc.is_target == 1) & (sc.is_validated == 1),
     (sc.is_target == 0) & (sc.is_validated == 1),
     (sc.is_target == 1) & (sc.is_validated == 0)],
    ["both", "drug_only", "assoc_only"], default="neither")

print("=== group sizes (diseases with >=1 validated target) ===")
print(sc.group.value_counts().to_string())
print(f"diseases: {sc.disease_index.nunique()}")

# within-disease percentile of each feature (higher pct = more module-proximal,
# except prox_closest where LOW is proximal -- flagged in the output)
print("\n=== within-disease percentile by group (mean over rows) ===")
pct = sc[["disease_index", "group"]].copy()
for f in FEATS:
    pct[f] = sc.groupby("disease_index")[f].rank(pct=True)
tab = pct.groupby("group")[FEATS].mean().reindex(
    ["assoc_only", "both", "drug_only", "neither"])
print(tab.round(3).to_string())
print("  (prox_closest: LOWER percentile = closer to the disease module)")

print("\n=== null rate by group -- an unreachable gene shows up as a NULL ===")
nul = sc.groupby("group")[FEATS].apply(lambda g: g.isna().mean()).reindex(
    ["assoc_only", "both", "drug_only", "neither"])
print(nul.round(3).to_string())

print("\n=== prox_closest distribution by group (share of rows) ===")
px = (pd.crosstab(sc.group, sc.prox_closest.fillna(-1), normalize="index")
      .reindex(["assoc_only", "both", "drug_only", "neither"]))
print(px.round(3).to_string())

print("\n=== the verdict metric ===")
d = tab.loc["drug_only"]
a = tab.loc["assoc_only"]
n = tab.loc["neither"]
for f in ["prox_closest", "dwpc_GGD", "ppi_adamic_adar", "proba_1"]:
    span = a[f] - n[f]
    pos = (d[f] - n[f]) / span if span else np.nan
    print(f"  {f:24s} assoc_only {a[f]:.3f} | drug_only {d[f]:.3f} | neither {n[f]:.3f}"
          f"   -> drug_only sits {pos:.0%} of the way from background to assoc positives")

out = tab.reset_index().melt(id_vars="group", var_name="feature", value_name="mean_pct")
out = out.merge(nul.reset_index().melt(id_vars="group", var_name="feature",
                                       value_name="null_rate"),
                on=["group", "feature"])
dataiku.Dataset("target_reachability").write_with_schema(out)


