# AXIS 2 of the validation overhaul: are the model's top-ranked candidates ACTIONABLE?
#
# WHY THIS AXIS EXISTS SEPARATELY. Three different claims were being collapsed into one
# "drug-target" label (TARGET_PRIORITIZER §8.1):
#     drug_protein  -> a molecule engages this protein        GENE level, direct assertion
#     drug_disease  -> this disease has pharmacological attention   DISEASE level
#     the join      -> this protein is the mechanism for this disease  PAIR level, INFERRED
# The join is what carries the 66% Cartesian inflation. `drug_protein` alone carries NONE: it is a
# direct assertion about a gene, needs no join, and covers 1,109 of 20,861 genes (5.3%). It has
# never been used to evaluate the model -- only as a feature-lift diagnostic.
#
# TWO TRACTABILITY LABELS, deliberately kept apart because their confound profiles differ:
#   demonstrated  a drug_protein edge exists            5.3% of genes   SHARP but 6x hub-confounded
#                                                                       (Q1 1.8% -> Q5 10.8%)
#   assessed      an OT tractability bucket is set      ~67% of genes   BLUNT but degree-flat (0.07)
#
# THE CONTROL THAT MAKES THIS MEANINGFUL. Demonstrated tractability rises 6x across interactome-
# degree quintiles, and the model is known to favour hubs (§7.2). So a naive "the top-K is enriched
# for drug targets" result could be entirely hub bias. Every lift below is therefore reported twice:
#   naive lift          = observed / (global base rate x K)
#   degree-matched lift = observed / SUM over top-K genes of (tractable rate in that gene's quintile)
# The second removes the hub confound by construction. If it sits at ~1.0 the enrichment was hubs.
#
# FALSIFIABLE PREDICTION, stated before running. The ligand-vs-receptor failure (§8.7) says the
# model over-ranks secreted ligands, which are poorly tractable, above membrane receptors, which are
# highly tractable. So the degree-matched tractability lift at the head should be AT OR BELOW 1.0 --
# a measured DEFICIT. If it comes back clearly above 1.0, the ligand/receptor problem is narrower
# than the case study claims and §8.7 needs softening.
import dataiku
import numpy as np
import pandas as pd

KS = [10, 20, 50, 100, 200]

nid = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_name", "node_type"], infer_with_pandas=False)
nid["node_index"] = nid.node_index.astype(int)
nid["node_id"] = nid.node_id.astype(str)
G = nid[nid.node_type == "gene/protein"]
D = nid[nid.node_type == "disease"]
gname = dict(zip(G.node_index, G.node_name))
dname = dict(zip(D.node_index, D.node_name))
gmap = dict(zip(G.node_id, G.node_index))

# ---- demonstrated tractability: a molecule engages this protein. No join, no inflation. ----
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
gc, tc = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
demo_genes = set(dp[tc].astype(str).map(gmap).dropna().astype(int))
print(f"genes with a demonstrated drug-target edge: {len(demo_genes):,} of {len(G):,} "
      f"({len(demo_genes)/len(G):.1%})")

drg = dataiku.Dataset("enriched_gene_druggability_v2").get_dataframe()
drg["assessed"] = ((drg.ot_sm_tractable == 1) | (drg.ot_ab_tractable == 1)).astype(int)
drg["demonstrated"] = drg.gene_index.isin(demo_genes).astype(int)
print(f"genes with an assessed tractability bucket : {int(drg.assessed.sum()):,} "
      f"({drg.assessed.mean():.1%})")

sc = dataiku.Dataset("scored_champion").get_dataframe(
    columns=["disease_index", "gene_index", "is_target", "proba_1", "gene_ppi_degree"])
sc = sc.merge(drg[["gene_index", "assessed", "demonstrated", "druggability_class"]],
              on="gene_index", how="left")
for c in ["assessed", "demonstrated"]:
    sc[c] = sc[c].fillna(0).astype(int)

# degree quintile assigned ONCE over the gene universe, so it is comparable across diseases
gd = sc.drop_duplicates("gene_index")[["gene_index", "gene_ppi_degree"]].copy()
gd["dq"] = pd.qcut(gd.gene_ppi_degree.rank(method="first"), 5, labels=False)
sc = sc.merge(gd[["gene_index", "dq"]], on="gene_index", how="left")
qrate = {c: sc.drop_duplicates("gene_index").groupby("dq")[c].mean().to_dict()
         for c in ["assessed", "demonstrated"]}
print("\n=== the hub confound this controls for (tractable share by degree quintile) ===")
for c in ["demonstrated", "assessed"]:
    print(f"  {c:14s}" + "  ".join(f"Q{q+1} {100*qrate[c][q]:.1f}%" for q in sorted(qrate[c])))

rows = []
for scope, sub_all in [("all candidates", sc), ("novel only", sc[sc.is_target == 0])]:
    for (di), g in sub_all.groupby("disease_index"):
        if len(g) < 500:
            continue
        g = g.sort_values("proba_1", ascending=False)
        rec = {"disease_index": di, "disease": dname.get(di), "scope": scope, "n_cand": len(g)}
        for lab in ["demonstrated", "assessed"]:
            base = g[lab].mean()
            for K in KS:
                top = g.head(K)
                obs = int(top[lab].sum())
                exp_naive = base * K
                # degree-matched expectation: each gene contributes its own quintile's rate
                exp_dm = float(top.dq.map(qrate[lab]).sum())
                rec[f"{lab}_obs{K}"] = obs
                rec[f"{lab}_naive{K}"] = obs / exp_naive if exp_naive > 0 else np.nan
                rec[f"{lab}_dm{K}"] = obs / exp_dm if exp_dm > 0 else np.nan
                rec[f"{lab}_exp{K}"] = exp_dm
        # composition: what the head is made of
        top50 = g.head(50)
        rec["pct_secreted_top50"] = 100 * (top50.druggability_class == "secreted").mean()
        rec["pct_membrane_top50"] = 100 * top50.druggability_class.astype(str).str.contains(
            "membrane", case=False, na=False).mean()
        rec["pct_secreted_all"] = 100 * (g.druggability_class == "secreted").mean()
        rec["pct_membrane_all"] = 100 * g.druggability_class.astype(str).str.contains(
            "membrane", case=False, na=False).mean()
        rows.append(rec)
out = pd.DataFrame(rows)
print(f"\nevaluated {out.disease_index.nunique()} diseases x 2 scopes")

for scope in ["all candidates", "novel only"]:
    s = out[out.scope == scope]
    print(f"\n=== {scope.upper()} ===")
    print(f"  {'label':14s}{'K':>5s}{'obs':>8s}{'exp(dm)':>9s}{'naive lift':>12s}{'DEGREE-MATCHED':>16s}")
    for lab in ["demonstrated", "assessed"]:
        for K in KS:
            o = int(s[f"{lab}_obs{K}"].sum()); e = s[f"{lab}_exp{K}"].sum()
            print(f"  {lab:14s}{K:>5d}{o:>8,}{e:>9,.0f}"
                  f"{s[f'{lab}_naive{K}'].mean():>12.2f}{(o/e if e else np.nan):>16.2f}")

print("\n=== VERDICT on the stated prediction ===")
nov = out[out.scope == "novel only"]
dm20 = int(nov.demonstrated_obs20.sum()) / nov.demonstrated_exp20.sum()
dm50 = int(nov.demonstrated_obs50.sum()) / nov.demonstrated_exp50.sum()
print(f"  degree-matched DEMONSTRATED tractability lift, novel head: "
      f"top20 {dm20:.2f}x, top50 {dm50:.2f}x")
if dm20 <= 1.05:
    print("  CONFIRMED -- at or below parity. The model does NOT preferentially rank actionable")
    print("  genes, consistent with the ligand-vs-receptor failure being real and general.")
else:
    print("  REFUTED -- the head IS enriched for actionable genes beyond hub effects, so the")
    print("  ligand-vs-receptor problem is narrower than §8.7 claims and should be softened.")

print("\n=== composition of the top 50 vs the candidate pool (novel only) ===")
print(f"  secreted   top50 {nov.pct_secreted_top50.mean():.1f}%  vs pool {nov.pct_secreted_all.mean():.1f}%")
print(f"  membrane   top50 {nov.pct_membrane_top50.mean():.1f}%  vs pool {nov.pct_membrane_all.mean():.1f}%")
print("  Secreted over-represented at the head while membrane is under-represented is the")
print("  ligand-vs-receptor failure stated as a distribution rather than an anecdote.")

dataiku.Dataset("tractability_axis").write_with_schema(out)

