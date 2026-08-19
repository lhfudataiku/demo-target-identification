# Two-stage evaluation: does a tractability filter (stage 2) rescue the therapeutic number?
#
# WHY: the raw drug-target benchmark (mean AUC 0.688 vs 0.782 on association labels) measures
# STAGE 1 ALONE -- the topology model ranking every gene in the graph. The intended product is
# stage 1 followed by a tractability filter, so the fair test applies the filter first and then
# asks where the drug-validated targets sit in what survives.
#
# LEAKAGE LADDER. Not every "druggability" column is admissible here, because the benchmark is
# built from approved drugs:
#   clean       - localization_class (subcellular location, GO CC / OT subcellular)
#               - ot_class_l1 protein family
#   PARTLY LEAKY- ot_sm_tractable / ot_ab_tractable: OT buckets include "Approved Drug"
#   CIRCULAR    - has_approved_drug: 780 genes vs the benchmark's 778-gene universe; this is
#                 the benchmark's own answer key, reported only to show the artifact ceiling.
#
# AUC is NOT comparable across rungs (each filter changes the negative set). The decision-
# relevant numbers are RETENTION (what fraction of validated targets the filter destroys) and
# HITS@50 in the surviving ranking.
import dataiku
import numpy as np
import pandas as pd

SCORE = "proba_1"

nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type", "node_name"], infer_with_pandas=False)
nodes["node_index"] = nodes.node_index.astype(int)
nodes["node_id"] = nodes.node_id.astype(str)
dis = nodes[nodes.node_type == "disease"]
gen = nodes[nodes.node_type == "gene/protein"]
dis_map = dict(zip(dis.node_id, dis.node_index))
gene_map = dict(zip(gen.node_id, gen.node_index))
dname = dict(zip(dis.node_index, dis.node_name))

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
tset = truth.groupby("disease_index").gene_index.apply(set).to_dict()

drg = dataiku.Dataset("enriched_gene_druggability").get_dataframe()
# Dataset validation_set_2_scored renamed to scored_m2 by liheng.fu@dataiku.com on 2026-08-13 12:19:46
sc = dataiku.Dataset("scored_m3").get_dataframe(
    columns=["disease_index", "gene_index", "is_target", SCORE])
sc = sc.merge(drg, on="gene_index", how="left")

ACCESSIBLE = {"membrane", "secreted", "membrane_and_secreted"}
FAMILIES = {"Membrane receptor", "Ion channel", "Transporter", "Enzyme",
            "Secreted protein", "Epigenetic regulator"}

FILTERS = [
    ("F0 none (stage 1 only)", "clean", lambda d: pd.Series(True, index=d.index)),
    ("F1 antibody-accessible localization", "clean",
     lambda d: d.localization_class.isin(ACCESSIBLE)),
    ("F2 druggable protein family", "clean", lambda d: d.ot_class_l1.isin(FAMILIES)),
    ("F3 F1 or F2", "clean",
     lambda d: d.localization_class.isin(ACCESSIBLE) | d.ot_class_l1.isin(FAMILIES)),
    ("F4 OT tractable (sm or ab)", "PARTLY LEAKY",
     lambda d: (d.ot_sm_tractable == 1) | (d.ot_ab_tractable == 1)),
    ("F5 has_approved_drug", "CIRCULAR", lambda d: d.has_approved_drug == 1),
]

rows = []
for label, status, fn in FILTERS:
    keep = fn(sc).fillna(False)
    sub = sc[keep]
    for d, g in sub.groupby("disease_index"):
        val = tset.get(d)
        if not val:
            continue
        n_total_val = len(val & set(sc.loc[sc.disease_index == d, "gene_index"]))
        if n_total_val == 0:
            continue
        g = g.sort_values(SCORE, ascending=False).reset_index(drop=True)
        g["rank"] = np.arange(1, len(g) + 1)
        mask = g.gene_index.isin(val)
        r = g.loc[mask, "rank"].values
        if len(r) == 0:
            rows.append({"filter": label, "status": status, "disease_index": d,
                         "pool": len(g), "n_val_kept": 0, "n_val_total": n_total_val,
                         "hits_at_50": 0, "median_pct": np.nan, "auc": np.nan})
            continue
        n1, n0 = int(mask.sum()), int((~mask).sum())
        rr = g[SCORE].rank()
        auc = (rr[mask].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n0 else np.nan
        rows.append({"filter": label, "status": status, "disease_index": d,
                     "pool": len(g), "n_val_kept": len(r), "n_val_total": n_total_val,
                     "hits_at_50": int((r <= 50).sum()),
                     "median_pct": float(np.median(r / len(g))), "auc": auc})

out = pd.DataFrame(rows)
out["disease_name"] = out.disease_index.map(dname)

print("=== filter ladder, aggregated over the benchmark diseases ===")
print(f"{'filter':38s}{'status':14s}{'pool':>7s}{'retain':>8s}{'hits@50':>9s}"
      f"{'%val@50':>9s}{'medpct':>8s}{'AUC':>7s}")
for label, status, _ in FILTERS:
    s = out[out["filter"] == label]
    if not len(s):
        continue
    kept, tot = s.n_val_kept.sum(), s.n_val_total.sum()
    print(f"{label:38s}{status:14s}{s.pool.mean():>7.0f}{kept/tot:>8.1%}"
          f"{int(s.hits_at_50.sum()):>9d}{s.hits_at_50.sum()/tot:>9.1%}"
          f"{s.median_pct.median():>8.1%}{s.auc.mean():>7.3f}")

print("\n  pool = mean genes surviving per disease")
print("  retain = share of drug-validated targets the filter KEEPS (stage-2 recall cost)")
print("  %val@50 = validated targets landing in the filtered top 50, as a share of all of them")
print("  AUC is not comparable across rungs -- the negative set changes at every rung.")

print("\n=== per-persona hits@50, clean rungs only ===")
P = [47654, 37143, 47537, 47469, 47604, 52236]
piv = (out[out.status == "clean"][out.disease_index.isin(P)]
       .pivot_table(index="disease_name", columns="filter",
                    values="hits_at_50", aggfunc="first"))
print(piv.to_string())

dataiku.Dataset("drug_target_benchmark_staged").write_with_schema(out)



