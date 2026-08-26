# Map the curated `known_drug` label onto graph indices, and calibrate its score against the
# join-based truth so a threshold can be chosen on evidence rather than by guess.
#
# OT's known_drug score rises with maximum clinical phase, so it spans approved pharmacology and
# early trial evidence in one column. Rather than pick a cutoff arbitrarily, this compares the score
# distribution of pairs that ARE in our approved join against those that are not.
#
# NODE_INDEX SAFETY: per-pair evaluation label. No nodes, no edges.
import dataiku
import numpy as np
import pandas as pd

kd = dataiku.Dataset("raw_ot_known_drug").get_dataframe()
nid = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_name", "node_type"], infer_with_pandas=False)
nid["node_index"] = nid.node_index.astype(int)
nid["node_id"] = nid.node_id.astype(str)
G = nid[nid.node_type == "gene/protein"]
D = nid[nid.node_type == "disease"]
gn = dataiku.Dataset("gene_names").get_dataframe(columns=["symbol", "entrez_id"])

# symbol -> entrez -> gene_index, the same crosswalk the druggability chain uses
gn = gn.dropna(subset=["entrez_id"]).copy()
gn["entrez"] = gn.entrez_id.astype("int64").astype(str)
sym2idx = (gn.merge(G[["node_id", "node_index"]].rename(columns={"node_id": "entrez"}), on="entrez")
           [["symbol", "node_index"]].drop_duplicates("symbol")
           .rename(columns={"node_index": "gene_index"}))

# OT diseaseId is MONDO_0005148 / EFO_xxxx; our disease node_id is bare-integer MONDO
kd["mondo_bare"] = kd.diseaseId.astype(str).str.extract(r"^MONDO_0*(\d+)$")[0]
dis2idx = D[["node_id", "node_index"]].rename(
    columns={"node_id": "mondo_bare", "node_index": "disease_index"})

t = (kd.merge(sym2idx, on="symbol", how="inner")
       .merge(dis2idx, on="mondo_bare", how="inner"))
t = t.groupby(["disease_index", "gene_index"], as_index=False).score.max()
print(f"known_drug pairs {len(kd):,} -> resolved onto the graph: {len(t):,}")
print(f"  ({t.disease_index.nunique():,} diseases, {t.gene_index.nunique():,} genes)")
print(f"  unresolved: {kd.mondo_bare.isna().sum():,} non-MONDO disease ids, "
      f"{(~kd.symbol.isin(sym2idx.symbol)).sum():,} unmapped symbols")

# ---- calibrate against the join-based truth ----------------------------------
dmap = dict(zip(D.node_id, D.node_index)); gmap = dict(zip(G.node_id, G.node_index))
dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
gc, tc = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
dp["drug"] = dp[gc].astype(str); dp["gene_index"] = dp[tc].astype(str).map(gmap)
dp = dp.dropna(subset=["gene_index"])[["drug", "gene_index"]]


def joined(rel):
    sub = dd[dd.relation.astype(str).str.fullmatch(rel, case=False, na=False)].copy()
    dc, xc = ("x_id", "y_id") if (sub.x_type == "drug").any() else ("y_id", "x_id")
    sub["drug"] = sub[dc].astype(str); sub["disease_index"] = sub[xc].astype(str).map(dmap)
    return set(map(tuple, sub.dropna(subset=["disease_index"])[["drug", "disease_index"]]
                   .merge(dp, on="drug")[["disease_index", "gene_index"]].astype(int).values))


ap, iv = joined("indication"), joined("drug_investigated_for")
keys = list(zip(t.disease_index.astype(int), t.gene_index.astype(int)))
t["in_approved_join"] = [1 if k in ap else 0 for k in keys]
t["in_investig_join"] = [1 if k in iv else 0 for k in keys]

print(f"\n=== overlap with the join-based truth ===")
print(f"  known_drug pairs also in the APPROVED join      : {int(t.in_approved_join.sum()):,} "
      f"({t.in_approved_join.mean():.1%})")
print(f"  known_drug pairs also in the INVESTIGATIONAL join: {int(t.in_investig_join.sum()):,} "
      f"({t.in_investig_join.mean():.1%})")
print(f"  APPROVED join pairs missing from known_drug      : "
      f"{len(ap - set(keys)):,} of {len(ap):,}")

print(f"\n=== score CALIBRATION: does the score separate approved from not? ===")
print(f"  {'bucket':16s}{'n':>9s}{'in approved join':>19s}{'in investig join':>19s}")
for lo, hi in [(0, .1), (.1, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)]:
    m = (t.score >= lo) & (t.score < hi)
    if not m.any():
        continue
    print(f"  [{lo:.1f},{hi:.2f})".ljust(16) + f"{int(m.sum()):>9,}"
          f"{t[m].in_approved_join.mean():>18.1%}{t[m].in_investig_join.mean():>19.1%}")
print("\n  A rising approved-share with score means the score is a usable phase proxy, so a")
print("  threshold can stand in for 'approved' without needing the join at all.")

dataiku.Dataset("known_drug_truth").write_with_schema(t)

