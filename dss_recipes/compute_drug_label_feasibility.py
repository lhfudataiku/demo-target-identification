# Feasibility check for training on the drug-validated label.
#
# WHY: the pair-level label `is_drug_target(gene, disease)` is the right objective, but it is
# far rarer than `is_target` (0.19% vs 2.38% in validation) and only exists for diseases that
# have a drug indication at all. Before committing to a training run, count what is actually
# in the TRAIN split -- positives, diseases covered, and positives per disease. If the train
# split has only a few hundred positives spread over a handful of diseases, a directly-trained
# model will not generalise and the right design is multi-task or re-ranking on top of the
# association model instead.
#
# Also counts `drug_investigated_for` (35,302 edges: trial-stage, not approved) as candidate
# WEAK positives, which is the obvious way to relieve the sparsity if the strict count is small.
import dataiku
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
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
gcol, tcol = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
dp["drug"] = dp[gcol].astype(str)
dp["gene_index"] = dp[tcol].astype(str).map(gene_map)
dp = dp.dropna(subset=["gene_index"])


def pairs_for(relation_match):
    sub = dd[dd.relation.astype(str).str.fullmatch(relation_match, case=False, na=False)].copy()
    dcol, xcol = ("x_id", "y_id") if (sub.x_type == "drug").any() else ("y_id", "x_id")
    sub["drug"] = sub[dcol].astype(str)
    sub["disease_index"] = sub[xcol].astype(str).map(dis_map)
    return (sub.dropna(subset=["disease_index"])[["drug", "disease_index"]]
            .merge(dp[["drug", "gene_index"]], on="drug")[["disease_index", "gene_index"]]
            .astype(int).drop_duplicates())


strict = pairs_for("indication")
weak = pairs_for("drug_investigated_for")
print(f"strict (indication)        : {len(strict):,} pairs, "
      f"{strict.disease_index.nunique()} diseases, {strict.gene_index.nunique()} genes")
print(f"weak (drug_investigated_for): {len(weak):,} pairs, "
      f"{weak.disease_index.nunique()} diseases, {weak.gene_index.nunique()} genes")
overlap = len(strict.merge(weak, on=["disease_index", "gene_index"]))
print(f"overlap strict n weak      : {overlap:,}")

rows = []
for split, ds in [("train", "enriched_train_full_2"),
                  ("validation", "enriched_validation_set_2"),
                  ("test", "enriched_test_set_2")]:
    df = dataiku.Dataset(ds).get_dataframe(columns=["disease_index", "gene_index", "is_target"])
    key = set(map(tuple, df[["disease_index", "gene_index"]].values))
    for name, tp in [("strict", strict), ("weak", weak)]:
        hit = tp[[tuple(x) in key for x in tp[["disease_index", "gene_index"]].values]]
        per = hit.groupby("disease_index").size()
        rows.append({"split": split, "label": name, "rows_in_split": len(df),
                     "positives": len(hit), "diseases_with_pos": len(per),
                     "pos_rate_pct": round(100 * len(hit) / len(df), 4),
                     "median_pos_per_disease": int(per.median()) if len(per) else 0,
                     "diseases_with_ge5": int((per >= 5).sum()),
                     "assoc_positives": int(df.is_target.sum())})
        print(f"  {split:11s} {name:7s}: {len(hit):>6,} positives over {len(per):>3} diseases "
              f"({100*len(hit)/len(df):.4f}%)  vs {int(df.is_target.sum()):,} association positives")

out = pd.DataFrame(rows)
print("\n=== verdict inputs ===")
tr = out[(out.split == 'train')]
s = tr[tr.label == 'strict'].iloc[0]
w = tr[tr.label == 'weak'].iloc[0]
print(f"  train strict positives: {s.positives:,} over {s.diseases_with_pos} diseases "
      f"({s.diseases_with_ge5} with >=5)")
print(f"  train strict+weak     : up to {s.positives + w.positives:,} over "
      f"<= {s.diseases_with_pos + w.diseases_with_pos} diseases")
print(f"  ratio to association  : 1 : {s.assoc_positives / max(s.positives,1):.0f}")
dataiku.Dataset("drug_label_feasibility").write_with_schema(out)
