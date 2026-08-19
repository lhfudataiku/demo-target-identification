# The filter chain, evaluated on ALL THREE validation axes -- completing the overhaul.
#
# THE FILTER: novel -> tractable -> not-secreted. (A fourth clause, "exclude known liabilities", was
# measured and REJECTED: it destroys 15-70% of validated targets because liabilities are discovered
# BY drugging a target. It is still computed below so the damage stays visible.)
#
# WHICH AXES CAN LEGITIMATELY SCORE THIS FILTER, and which cannot:
#
#   ASSOCIATION -- NOT APPLICABLE. Clause 1 removes every association positive by construction, so
#     the association axis has nothing left to measure. Reporting it would be a tautology.
#
#   TRACTABILITY -- NEAR-CIRCULAR, reported with the circularity quantified. Clause 2 filters on
#     ASSESSED tractability and clause 3 on druggability class; the outcome here is DEMONSTRATED
#     tractability. These are different columns but not independent, so a positive result is partly
#     definitional. The recipe measures P(demonstrated | assessed) against
#     P(demonstrated | not assessed) so a reader can see exactly how much of the lift is built in.
#     A number this compromised belongs in the appendix, not the headline.
#
#   THERAPEUTIC -- THE LEGITIMATE TEST. Being chemically tractable is not the same claim as being
#     the mechanism for a particular disease, so filtering on tractability and scoring on
#     disease-specific drug evidence is a real question. Three ground truths, since the choice
#     changes the answer (TARGET_PRIORITIZER §8.1):
#         known_drug >= 0.8   the curated, score-calibrated standard
#         approved join       strict but 66% Cartesian-inflated
#         investigational     13x larger, includes failed programmes
#
# EVERY table carries expected@K -- the hits chance alone would produce. Below ~1, an observed zero
# is uninformative, a lesson learned the hard way when a sparse subset's 0.00 was briefly read as a
# refutation (§8.3).
import dataiku
import numpy as np
import pandas as pd

TOPN = [20, 50, 200]

nid = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
nid["node_index"] = nid.node_index.astype(int); nid["node_id"] = nid.node_id.astype(str)
D = nid[nid.node_type == "disease"]; G = nid[nid.node_type == "gene/protein"]
dmap = dict(zip(D.node_id, D.node_index)); gmap = dict(zip(G.node_id, G.node_index))

# ---- outcome 1: demonstrated tractability (gene-level, uninflated) --------------
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
gc, tc = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
dp["drug"] = dp[gc].astype(str); dp["gene_index"] = dp[tc].astype(str).map(gmap)
dp2 = dp.dropna(subset=["gene_index"])[["drug", "gene_index"]]
demo_genes = set(dp2.gene_index.astype(int))

# ---- outcomes 2-4: therapeutic, three ground truths ----------------------------
dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)


def joined(rel):
    sub = dd[dd.relation.astype(str).str.fullmatch(rel, case=False, na=False)].copy()
    dc, xc = ("x_id", "y_id") if (sub.x_type == "drug").any() else ("y_id", "x_id")
    sub["drug"] = sub[dc].astype(str); sub["disease_index"] = sub[xc].astype(str).map(dmap)
    return set(map(tuple, sub.dropna(subset=["disease_index"])[["drug", "disease_index"]]
                   .merge(dp2, on="drug")[["disease_index", "gene_index"]].astype(int).values))


kd = dataiku.Dataset("known_drug_truth").get_dataframe()
KD08 = set(map(tuple, kd[kd.score >= 0.8][["disease_index", "gene_index"]].astype(int).values))
AP, IV = joined("indication"), joined("drug_investigated_for")
print(f"ground truths -- known_drug>=0.8 {len(KD08):,} | approved {len(AP):,} | investigational {len(IV):,}")

c = dataiku.Dataset("target_candidates_2").get_dataframe(
    columns=["disease_index", "disease_name", "gene_index", "rank_in_disease", "is_target",
             "ot_sm_tractable", "ot_ab_tractable", "druggability_class", "safety_flag"])
keys = list(zip(c.disease_index.astype(int), c.gene_index.astype(int)))
c["y_kd08"] = [1 if k in KD08 else 0 for k in keys]
c["y_appr"] = [1 if k in AP else 0 for k in keys]
c["y_inv"] = [1 if k in IV else 0 for k in keys]
c["y_tract"] = c.gene_index.astype(int).isin(demo_genes).astype(int)
c["assessed"] = ((c.ot_sm_tractable == 1) | (c.ot_ab_tractable == 1)).astype(int)
# therapeutic outcomes are scored on NOVEL candidates only, matching clause 1
for o in ["kd08", "appr", "inv"]:
    c[f"y_{o}"] = c[f"y_{o}"] * (c.is_target == 0)
print(f"candidates {len(c):,} over {c.disease_name.nunique()} personas")

# ---- how circular IS the tractability axis for this filter? --------------------
g1 = c[c.assessed == 1].y_tract.mean(); g0 = c[c.assessed == 0].y_tract.mean()
print(f"\n=== CIRCULARITY of the tractability axis for this filter ===")
print(f"  P(demonstrated | assessed tractable)     = {g1:.4f}")
print(f"  P(demonstrated | NOT assessed tractable) = {g0:.4f}")
print(f"  ratio = {g1/g0 if g0 else float('nan'):.2f}x  <- clause 2 alone guarantees roughly this")
print("  much tractability lift by definition. Anything near it is built in, not learned.")

STAGES = [("0 all", lambda d: pd.Series(True, index=d.index)),
          ("1 novel", lambda d: d.is_target == 0),
          ("2 +tractable", lambda d: (d.ot_sm_tractable == 1) | (d.ot_ab_tractable == 1)),
          ("3 +not secreted", lambda d: d.druggability_class != "secreted")]
NOT_APPLIED = ("4 +no liability [REJECTED]", lambda d: d.safety_flag != "known_liability")
OUT = [("kd08", "known_drug>=0.8"), ("appr", "approved join"),
       ("inv", "investigational"), ("tract", "tractability [CIRCULAR]")]

rows = []
for dz, g in c.groupby("disease_name"):
    mask = pd.Series(True, index=g.index)
    def rec(label, m):
        sub = g[m]
        r = {"disease": dz, "stage": label, "n": len(sub)}
        for o, _ in OUT:
            base = g[f"y_{o}"].mean(); tot = int(g[f"y_{o}"].sum())
            kept = int(sub[f"y_{o}"].sum())
            r[f"{o}_kept"] = kept
            r[f"{o}_lift"] = (sub[f"y_{o}"].mean()/base) if (len(sub) and base > 0) else np.nan
            r[f"{o}_recall"] = 100*kept/tot if tot else np.nan
        rows.append(r)
    for lab, fn in STAGES:
        mask = mask & fn(g); rec(lab, mask)
    rec(NOT_APPLIED[0], mask & NOT_APPLIED[1](g))
    for N in TOPN:
        for tag, sel in [("PLAIN", g), ("FILTERED", g[mask])]:
            top = sel.nsmallest(N, "rank_in_disease")
            r = {"disease": dz, "stage": f"top{N} {tag}", "n": len(top)}
            for o, _ in OUT:
                base = g[f"y_{o}"].mean()
                r[f"{o}_kept"] = int(top[f"y_{o}"].sum())
                r[f"{o}_lift"] = np.nan
                r[f"{o}_recall"] = base*len(top)          # expected@N, for power
            rows.append(r)
out = pd.DataFrame(rows)

print("\n\n=== FILTER CASCADE, all axes (lift | recall%) ===")
for dz, g in out[out.stage.str.match(r"^\d")].groupby("disease"):
    print(f"\n{dz}")
    print("  " + "stage".ljust(28) + "n".rjust(8) + "".join(f"{lab[:22]:>24s}" for _, lab in OUT))
    for _, r in g.iterrows():
        cells = "".join(f"{r[f'{o}_lift']:>14.2f} |{r[f'{o}_recall']:>7.0f}%" for o, _ in OUT)
        print(f"  {r.stage:28s}{r.n:>8,}{cells}")

print("\n\n=== TOP-N: plain -> filtered, with expected@N in brackets ===")
for o, lab in OUT:
    print(f"\n  outcome: {lab}")
    for dz, g in out[out.stage.str.contains("top")].groupby("disease"):
        cells = ""
        for N in TOPN:
            p = g[g.stage == f"top{N} PLAIN"].iloc[0]; f_ = g[g.stage == f"top{N} FILTERED"].iloc[0]
            cells += f"{int(p[f'{o}_kept'])}->{int(f_[f'{o}_kept'])} [{p[f'{o}_recall']:.1f}]".rjust(20)
        print(f"    {dz[:30]:30s}{cells}")

print("\n\n=== VERDICT ===")
casc = out[out.stage.str.match(r"^3 ")]
rej = out[out.stage.str.contains("REJECTED")]
for o, lab in OUT:
    print(f"  {lab:26s} 3-clause lift {casc[f'{o}_lift'].mean():>5.2f}x  recall "
          f"{casc[f'{o}_recall'].mean():>5.1f}%   | with clause 4: recall "
          f"{rej[f'{o}_recall'].mean():>5.1f}%")
print("\n  Read the therapeutic rows as the result. The tractability row is definitional -- clause 2")
print("  filters on a correlate of that outcome -- and is reported only so the bias is visible.")
dataiku.Dataset("filter_three_axes").write_with_schema(out)
