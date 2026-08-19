# Can the model surface targets it was NEVER TOLD ABOUT? Measured against THREE ground truths.
#
# WHY THIS REPLACES THE OLD READING: "known% in the top 50" was being used as a novelty ceiling --
# a disease at 96% known was called "no novelty left". That is wrong twice over.
#   1. It is a PRECISION measure, not a novelty measure. Normalised by base rate, NSCLC's 96% is a
#      19x enrichment (the ranking is excellent) while CKD's 2% is 2.9x (the ranking is poor). The
#      old reading rewarded the worst ranking in the panel and penalised the best.
#   2. It says nothing about the novel candidates, because they sit BELOW the known ones by
#      construction. A well-ranked, densely-annotated disease puts truth first and its novel
#      hypotheses at ranks 50-200.
#
# THE MEASURE: drop the known association targets, re-rank what is left, and ask how many of the
# top-K NOVEL candidates are drug-linked for that disease. Independent of the training label -- no
# model feature traverses a drug node.
#
# THREE GROUND TRUTHS, because the choice changes the answer and the earlier version used only the
# strictest one:
#   approved        `indication`             ~9.4k edges   the drug is APPROVED for this disease
#   investigational `drug_investigated_for`  ~69.7k edges  in trials, not approved
#   any             either
#
# WHY `investigational` IS THE FAIRER BAR FOR TARGET IDENTIFICATION: the deliverable predicts
# targets worth pursuing, not drugs that already shipped. Restricting to approved indications
# penalises the model for surfacing target classes that are currently in development -- which is
# precisely what a discovery tool should surface. The cost is that trial-stage labels include
# FAILURES (a target trialled and abandoned still counts), so `investigational` measures
# "someone judged this mechanistically plausible", not "this works". Read both columns.
import dataiku
import numpy as np
import pandas as pd

KS = [10, 20, 50, 100, 200]
FOCUS = {"non-small cell lung carcinoma", "lung adenocarcinoma", "lung cancer",
         "obesity disorder", "type 2 diabetes mellitus", "chronic kidney disease",
         "diabetes mellitus", "epilepsy"}
WATCH = ["MAPK3", "PTPN6", "SMARCA2", "CRKL", "STAT5B", "STAT1", "GSK3B", "IRS1", "IRS2",
         "PIK3R2", "CDKN2B", "MRE11", "HDAC3", "ZAP70", "PLCG2", "IL6R", "PDPK1", "EGR1"]

nid = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_name", "node_type"], infer_with_pandas=False)
nid["node_index"] = nid.node_index.astype(int)
nid["node_id"] = nid.node_id.astype(str)
D = nid[nid.node_type == "disease"]
G = nid[nid.node_type == "gene/protein"]
dname = dict(zip(D.node_index, D.node_name))
gname = dict(zip(G.node_index, G.node_name))
dmap = dict(zip(D.node_id, D.node_index))
gmap = dict(zip(G.node_id, G.node_index))

# Dataset DEMO_KG_LS.drug_disease_edges renamed to DEMO_KG_drug_disease_edges_copy by liheng.fu@dataiku.com on 2026-08-18 09:42:00
# Dataset DEMO_KG_drug_disease_edges_copy renamed to drug_disease_edges by liheng.fu@dataiku.com on 2026-08-18 09:57:52
dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
gc, tc = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
dp["drug"] = dp[gc].astype(str)
dp["gene_index"] = dp[tc].astype(str).map(gmap)
dp = dp.dropna(subset=["gene_index"])[["drug", "gene_index"]]
print("drug_disease relations:", dd.relation.astype(str).value_counts().to_dict())


def pairs_for(rel_regex):
    sub = dd[dd.relation.astype(str).str.fullmatch(rel_regex, case=False, na=False)].copy()
    dc, xc = ("x_id", "y_id") if (sub.x_type == "drug").any() else ("y_id", "x_id")
    sub["drug"] = sub[dc].astype(str)
    sub["disease_index"] = sub[xc].astype(str).map(dmap)
    out = (sub.dropna(subset=["disease_index"])[["drug", "disease_index"]]
           .merge(dp, on="drug")[["disease_index", "gene_index"]]
           .astype(int).drop_duplicates())
    return set(map(tuple, out.values))


approved = pairs_for("indication")
investig = pairs_for("drug_investigated_for")
TRUTHS = {"approved": approved, "investigational": investig, "any": approved | investig}
for k, v in TRUTHS.items():
    print(f"  {k:16s} {len(v):>7,} (disease, gene) pairs")

sc = dataiku.Dataset("scored_m3").get_dataframe(
    columns=["disease_index", "gene_index", "is_target", "proba_1"])
sc["disease"] = sc.disease_index.map(dname)
keys = list(zip(sc.disease_index.astype(int), sc.gene_index.astype(int)))
for name, tset in TRUTHS.items():
    sc[name] = [1 if k in tset else 0 for k in keys]
print(f"\nscored {len(sc):,} rows over {sc.disease_index.nunique()} validation diseases")

rows = []
for (di, dz), g in sc.groupby(["disease_index", "disease"]):
    nov = g[g.is_target == 0]
    if len(nov) < 200:
        continue
    nov = nov.sort_values("proba_1", ascending=False)
    for tname in TRUTHS:
        tot = int(nov[tname].sum())
        if tot == 0:
            continue
        base = nov[tname].mean()
        rec = {"disease_index": di, "disease": dz, "ground_truth": tname,
               "n_known": int((g.is_target == 1).sum()), "n_novel": len(nov),
               "novel_linked_total": tot, "novel_base_rate_pct": 100 * base}
        for K in KS:
            hit = int(nov.head(K)[tname].sum())
            rec[f"hits_top{K}"] = hit
            rec[f"lift_top{K}"] = (hit / K) / base if base > 0 else np.nan
        rows.append(rec)
out = pd.DataFrame(rows)

print("\n=== DISCOVERY PRECISION on the novel sub-list, by ground truth ===")
print(f"  {'ground truth':16s}{'diseases':>10s}" + "".join(f"{'lift@'+str(K):>10s}" for K in KS)
      + "".join(f"{'hits@'+str(K):>10s}" for K in KS))
for tname in TRUTHS:
    s = out[out.ground_truth == tname]
    lifts = "".join(f"{s[f'lift_top{K}'].replace([np.inf],np.nan).mean():>10.2f}" for K in KS)
    hits = "".join(f"{int(s[f'hits_top{K}'].sum()):>10d}" for K in KS)
    print(f"  {tname:16s}{len(s):>10d}{lifts}{hits}")

print("\n\n=== the focus diseases: approved vs investigational ===")
for dz in sorted(FOCUS):
    sub = out[out.disease == dz]
    if not len(sub):
        continue
    print(f"\n  {dz}")
    for _, r in sub.iterrows():
        print(f"    {r.ground_truth:16s} to-find {int(r.novel_linked_total):>4d}   "
              f"top20 {int(r.hits_top20):>3d} ({r.lift_top20:>6.1f}x)   "
              f"top50 {int(r.hits_top50):>3d} ({r.lift_top50:>6.1f}x)   "
              f"top200 {int(r.hits_top200):>3d} ({r.lift_top200:>6.1f}x)")

print("\n\n=== the specific NSCLC / lung-adeno candidates under review ===")
gi = {v: k for k, v in gname.items()}
for dz in ["non-small cell lung carcinoma", "lung adenocarcinoma"]:
    g = sc[sc.disease == dz]
    if not len(g):
        continue
    g = g.copy()
    g["full_rank"] = g.proba_1.rank(ascending=False, method="first").astype(int)
    nov = g[g.is_target == 0].sort_values("proba_1", ascending=False).copy()
    nov["novel_rank"] = range(1, len(nov) + 1)
    print(f"\n  {dz}")
    print(f"    {'gene':<10s}{'novel#':>7s}{'list#':>7s}   approved  investigational")
    for gn in WATCH:
        idx = gi.get(gn)
        r = nov[nov.gene_index == idx]
        if not len(r):
            continue
        r = r.iloc[0]
        print(f"    {gn:<10s}{int(r.novel_rank):>7d}{int(r.full_rank):>7d}"
              f"{'      YES' if r.approved else '       --':>11s}"
              f"{'          YES' if r.investigational else '           --':>15s}")

dataiku.Dataset("novel_discovery_eval").write_with_schema(out)

