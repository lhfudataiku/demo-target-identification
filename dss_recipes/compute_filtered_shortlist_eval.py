# Does the proposed filter chain actually improve the shortlist, per persona disease?
#
# The filter (TARGET_PRIORITIZER §10.3) is: novel -> tractable -> not a secreted ligand -> no
# documented liability -> rank <= N. Each clause is defensible on its own; the question here is
# whether applying them CONCENTRATES real therapeutic targets or merely shrinks the list.
#
# GROUND TRUTH: drug-validated targets (approved-indication edge x drug-target edge), which is
# independent of the model's training label by construction and traverses no feature the model
# sees. Association positives are NOT used as the outcome -- the model was trained on them.
#
# THE CONFOUND THIS RECIPE IS BUILT TO AVOID: the first clause is `is_target == 0`, which removes
# association-known genes. Drug-validated targets that are ALSO association positives are removed
# by that clause BY DESIGN, so scoring the filter against all drug-validated targets would
# conflate "the filter is destructive" with "we deliberately dropped the known ones". The outcome
# is therefore NOVEL drug-validated targets: validated for this disease AND not an association
# positive. That is exactly the population the deliverable claims to find.
#
# Reports, per persona: the survivor count and novel-validated enrichment at each cumulative
# stage, and top-N precision with the filter versus plain top-N at the same N.
import dataiku
import numpy as np
import pandas as pd

TOPN = [20, 50, 200]

nodes = dataiku.Dataset("DEMO_KG_LS.graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
nodes["node_index"] = nodes.node_index.astype(int)
nodes["node_id"] = nodes.node_id.astype(str)
dis_map = dict(zip(nodes[nodes.node_type == "disease"].node_id,
                   nodes[nodes.node_type == "disease"].node_index))
gene_map = dict(zip(nodes[nodes.node_type == "gene/protein"].node_id,
                    nodes[nodes.node_type == "gene/protein"].node_index))

dd = dataiku.Dataset("DEMO_KG_LS.drug_disease_edges").get_dataframe(infer_with_pandas=False)
dp = dataiku.Dataset("DEMO_KG_LS.drug_protein_edges").get_dataframe(infer_with_pandas=False)
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

c = dataiku.Dataset("target_candidates_2").get_dataframe(
    columns=["disease_index", "disease_name", "gene_index", "gene_name", "score",
             "rank_in_disease", "is_target", "ot_sm_tractable", "ot_ab_tractable",
             "druggability_class", "safety_flag", "safety_events", "has_approved_drug"])
c = c.merge(truth, on=["disease_index", "gene_index"], how="left")
c["is_validated"] = c.is_validated.fillna(0).astype(int)
# the outcome: validated for this disease AND unknown to the association layer
c["novel_validated"] = ((c.is_validated == 1) & (c.is_target == 0)).astype(int)

print(f"candidates {len(c):,} over {c.disease_name.nunique()} persona diseases")
print(f"drug-validated pairs present : {int(c.is_validated.sum()):,}")
print(f"  of which NOVEL (not an association positive): {int(c.novel_validated.sum()):,}"
      f"  <- the outcome being predicted\n")

# Stages 1-3 are the RECOMMENDED filter. Stage 4 is measured and reported but NOT applied to the
# shortlist: excluding targets with a curated liability destroys novel-validated targets, because
# liabilities are discovered BY drugging a target (compute_safety_lift measured 4.62x enrichment
# for drug-validated status). Keeping it in the cascade below is deliberate -- the damage should be
# visible in the artifact rather than asserted in a document.
STAGES = [
    ("0 all candidates",        lambda d: pd.Series(True, index=d.index)),
    ("1 novel only",            lambda d: d.is_target == 0),
    ("2 + tractable",           lambda d: (d.ot_sm_tractable == 1) | (d.ot_ab_tractable == 1)),
    ("3 + not secreted",        lambda d: d.druggability_class != "secreted"),
]
NOT_RECOMMENDED = ("4 + no known liability [NOT APPLIED]",
                   lambda d: d.safety_flag != "known_liability")

rows = []
for dz, g in c.groupby("disease_name"):
    base = g.novel_validated.mean()
    n_nv_total = int(g.novel_validated.sum())
    mask = pd.Series(True, index=g.index)
    def record(label, m):
        sub = g[m]; nv = int(sub.novel_validated.sum())
        rate = sub.novel_validated.mean() if len(sub) else np.nan
        rows.append({"disease": dz, "stage": label, "n": len(sub), "novel_validated": nv,
                     "rate_pct": 100 * rate if len(sub) else np.nan,
                     "lift": (rate / base) if (len(sub) and base > 0) else np.nan,
                     "recall_pct": 100 * nv / n_nv_total if n_nv_total else np.nan})
    for label, fn in STAGES:
        mask = mask & fn(g)
        record(label, mask)
    record(NOT_RECOMMENDED[0], mask & NOT_RECOMMENDED[1](g))   # measured, not adopted
    # top-N: filtered vs plain, same N
    for N in TOPN:
        plain = g.nsmallest(N, "rank_in_disease")
        filt = g[mask].nsmallest(N, "rank_in_disease")
        rows.append({"disease": dz, "stage": f"top{N} PLAIN", "n": len(plain),
                     "novel_validated": int(plain.novel_validated.sum()),
                     "rate_pct": 100 * plain.novel_validated.mean() if len(plain) else np.nan,
                     "lift": np.nan, "recall_pct": np.nan})
        rows.append({"disease": dz, "stage": f"top{N} FILTERED", "n": len(filt),
                     "novel_validated": int(filt.novel_validated.sum()),
                     "rate_pct": 100 * filt.novel_validated.mean() if len(filt) else np.nan,
                     "lift": np.nan, "recall_pct": np.nan})

out = pd.DataFrame(rows)

print("=== filter cascade: survivors, novel-validated retained, enrichment ===")
for dz, g in out[out.stage.str.match(r"^\d")].groupby("disease"):
    tot = int(g.iloc[0].novel_validated)
    print(f"\n{dz}   ({tot} novel-validated targets in scope)")
    print(f"  {'stage':24s}{'n':>8s}{'kept':>6s}{'rate%':>8s}{'lift':>7s}{'recall%':>9s}")
    for _, r in g.iterrows():
        print(f"  {r.stage:24s}{r.n:>8,}{r.novel_validated:>6}{r.rate_pct:>8.3f}"
              f"{r.lift:>7.2f}{r.recall_pct:>9.1f}")

print("\n\n=== top-N precision: plain ranking vs filtered ranking ===")
print(f"  {'disease':32s}" + "".join(f"{'top'+str(N):>22s}" for N in TOPN))
print(f"  {'':32s}" + "".join(f"{'plain -> filtered':>22s}" for _ in TOPN))
for dz, g in out[out.stage.str.contains("top")].groupby("disease"):
    cells = ""
    for N in TOPN:
        p = g[g.stage == f"top{N} PLAIN"].iloc[0]
        f = g[g.stage == f"top{N} FILTERED"].iloc[0]
        cells += f"{int(p.novel_validated)}/{int(p.n)} -> {int(f.novel_validated)}/{int(f.n)}".rjust(22)
    print(f"  {dz[:32]:32s}{cells}")

print("\n\n=== the surviving top-20 per persona (for biological review) ===")
for dz, g in c.groupby("disease_name"):
    mask = pd.Series(True, index=g.index)
    for _, fn in STAGES:
        mask = mask & fn(g)
    top = g[mask].nsmallest(20, "rank_in_disease")
    print(f"\n{dz}")
    for _, r in top.iterrows():
        tag = " *VALIDATED*" if r.novel_validated else (" (approved drug exists)" if r.has_approved_drug == 1 else "")
        liab = "  [liability: " + str(r.safety_events)[:34] + "]" if r.safety_flag == "known_liability" else ""
        print(f"  #{int(r.rank_in_disease):<6d} {r.gene_name:<12s} {r.score:.3f}  "
              f"{str(r.druggability_class)[:24]:24s}{tag}{liab}")

dataiku.Dataset("filtered_shortlist_eval").write_with_schema(out)
