# Benchmark the model against DRUG-VALIDATED targets, not association labels.
#
# WHY: `is_target` comes from disease-gene ASSOCIATION edges (GWAS / literature). A model can
# rank those well and still miss the proteins that drugs actually hit -- measured directly on
# CKD, where NR3C2 (finerenone) sat at 3909/5117 and SLC5A2 (SGLT2i) at 575/5117 while the
# top 50 filled up with SLC transporters. This recipe asks the harder question for every
# validation disease: where do the targets of drugs INDICATED for this disease rank?
#
# Ground truth = drug_disease_edges (indication) ⋈ drug_protein_edges (target) on drugbank id.
# Independent of `is_target`: no feature in the model traverses a drug node, and the label
# comes from a different edge type than the benchmark.
#
# NODE_INDEX SAFETY: joins on (node_id, node_type) -> node_index from the CURRENT graph_nodes,
# never on a cached index. Read-only; emits a per-disease metrics table.
import dataiku
import numpy as np
import pandas as pd

SCORE = "proba_1"

nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
nodes["node_index"] = nodes.node_index.astype(int)
nodes["node_id"] = nodes.node_id.astype(str)
dis_map = dict(zip(nodes[nodes.node_type == "disease"].node_id,
                   nodes[nodes.node_type == "disease"].node_index))
gene_map = dict(zip(nodes[nodes.node_type == "gene/protein"].node_id,
                    nodes[nodes.node_type == "gene/protein"].node_index))

# Dataset DEMO_KG_LS.drug_disease_edges renamed to DEMO_KG_drug_disease_edges_copy by liheng.fu@dataiku.com on 2026-08-18 09:42:00
# Dataset DEMO_KG_drug_disease_edges_copy renamed to drug_disease_edges by liheng.fu@dataiku.com on 2026-08-18 09:57:52
dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
print("drug_disease relations:", dd.relation.value_counts().to_dict())
print("drug_protein relations:", dp.display_relation.value_counts().to_dict())

ind = dd[dd.relation.astype(str).str.contains("indication", case=False, na=False)].copy()
ind = ind[~ind.relation.astype(str).str.contains("contra", case=False, na=False)]
# x/y orientation is not guaranteed -- pick the drug column by type
dcol, xcol = ("x_id", "y_id") if (ind.x_type == "drug").any() else ("y_id", "x_id")
ind["drug"] = ind[dcol].astype(str)
ind["disease_index"] = ind[xcol].astype(str).map(dis_map)

gcol, tcol = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
dp["drug"] = dp[gcol].astype(str)
dp["gene_index"] = dp[tcol].astype(str).map(gene_map)

ind = ind.dropna(subset=["disease_index"])
dp = dp.dropna(subset=["gene_index"])
truth = (ind[["drug", "disease_index"]].merge(dp[["drug", "gene_index"]], on="drug")
         [["disease_index", "gene_index"]].astype(int).drop_duplicates())
print(f"\nvalidated (disease, target) pairs: {len(truth)} over "
      f"{truth.disease_index.nunique()} diseases, {truth.gene_index.nunique()} genes")

# Dataset validation_set_2_scored renamed to scored_m2 by liheng.fu@dataiku.com on 2026-08-13 12:19:46
sc = dataiku.Dataset("scored_champion").get_dataframe(
    columns=["disease_index", "gene_index", "is_target", "disease_split_key", SCORE])
pairs = set(map(tuple, truth.values))

rows = []
for d, g in sc.groupby("disease_index"):
    val = truth[truth.disease_index == d].gene_index
    present = g[g.gene_index.isin(set(val))]
    if len(present) == 0:
        continue
    g = g.sort_values(SCORE, ascending=False).reset_index(drop=True)
    g["rank"] = np.arange(1, len(g) + 1)
    r = g[g.gene_index.isin(set(val))]["rank"].values
    n = len(g)
    # AUC with drug-validated targets as the positive class
    mask = g.gene_index.isin(set(val))
    n1, n0 = int(mask.sum()), int((~mask).sum())
    rr = g[SCORE].rank()
    auc_drug = (rr[mask].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 and n0 else np.nan
    # AUC on the association label, same disease, for side-by-side comparison
    a1 = int(g.is_target.sum()); a0 = n - a1
    auc_assoc = ((rr[g.is_target == 1].sum() - a1 * (a1 + 1) / 2) / (a1 * a0)
                 if a1 and a0 else np.nan)
    rows.append({"disease_index": d, "n_genes": n,
                 "n_validated_targets": len(r),
                 "median_pct": float(np.median(r / n)),
                 "best_rank": int(r.min()),
                 "hits_at_50": int((r <= 50).sum()),
                 "hits_at_top1pct": int((r <= max(1, n // 100)).sum()),
                 "hits_at_top10pct": int((r <= n // 10).sum()),
                 "auc_drug_targets": auc_drug,
                 "auc_assoc_labels": auc_assoc,
                 "n_assoc_positives": a1,
                 "validated_also_assoc": int(sum(
                     1 for gi in val if (d, gi) in pairs
                     and gi in set(g.loc[g.is_target == 1, "gene_index"])))})

out = pd.DataFrame(rows)
print(f"\ndiseases with >=1 validated target in the scored set: {len(out)}")
print(f"total validated targets evaluated                   : {int(out.n_validated_targets.sum())}")
print(f"\n=== where do drug-validated targets rank? ===")
print(f"  median percentile (median over diseases): {out.median_pct.median():.1%}")
print(f"  validated targets in top 50   : {int(out.hits_at_50.sum())} "
      f"({out.hits_at_50.sum()/out.n_validated_targets.sum():.1%})")
print(f"  validated targets in top 1%   : {int(out.hits_at_top1pct.sum())} "
      f"({out.hits_at_top1pct.sum()/out.n_validated_targets.sum():.1%})")
print(f"  validated targets in top 10%  : {int(out.hits_at_top10pct.sum())} "
      f"({out.hits_at_top10pct.sum()/out.n_validated_targets.sum():.1%})")
print(f"\n=== AUC: association labels vs drug-validated targets ===")
both = out.dropna(subset=["auc_drug_targets", "auc_assoc_labels"])
print(f"  mean AUC on association labels   : {both.auc_assoc_labels.mean():.4f}")
print(f"  mean AUC on drug-validated targets: {both.auc_drug_targets.mean():.4f}")
print(f"  diseases where drug AUC < 0.5     : {(both.auc_drug_targets < 0.5).sum()} of {len(both)}")
print(f"  overlap: validated targets that are ALSO association positives: "
      f"{int(out.validated_also_assoc.sum())} of {int(out.n_validated_targets.sum())}")
print(f"\nworst 12 diseases by drug-target AUC (>=3 validated targets):")
w = both[both.n_validated_targets >= 3].nsmallest(12, "auc_drug_targets")
nm = dict(zip(nodes[nodes.node_type == "disease"].node_index,
              dataiku.Dataset("graph_nodes").get_dataframe(
                  columns=["node_index", "node_name", "node_type"], infer_with_pandas=False)
              .query("node_type == 'disease'").node_name))
w = w.assign(disease=w.disease_index.map(nm))
print(w[["disease", "n_validated_targets", "auc_drug_targets", "auc_assoc_labels"]]
      .to_string(index=False))

out["disease_name"] = out.disease_index.map(nm)
dataiku.Dataset("drug_target_benchmark").write_with_schema(out)


