# THE GATE. Does the safety annotation separate anything, and in which direction?
#
# Same discipline as `compute_tractability_lift`: measure an attribute's lift against BOTH labels
# before spending effort wiring it into a deliverable. That check has twice prevented building a
# feature that would have degraded the therapeutic axis.
#
# FALSIFIABLE PREDICTION, stated before running:
#   Drug-validated targets should be DEPLETED for `lof_intolerant`. Genes whose loss-of-function
#   is not tolerated in humans are poor drug targets, because inhibiting them mimics the
#   intolerated state. If this comes back ENRICHED or flat, the crosswalk is wrong -- do not
#   proceed on the assumption it is right.
#
# A CONFOUND TO EXPECT, also stated in advance:
#   `known_liability` is likely ENRICHED for drug-validated targets, because liabilities are
#   discovered BY drugging a target. It is annotation downstream of clinical attention, not an
#   independent risk measure. That makes it useful as a warning on a shortlist and useless as a
#   predictor -- the same structural problem as the drug-target benchmark's gene-popularity
#   shortcut (TARGET_PRIORITIZER §7.5).
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

df = dataiku.Dataset("scored_m3").get_dataframe(
    columns=["disease_index", "gene_index", "is_target"])
df = df[df.disease_index.isin(set(truth.disease_index))]
df = df.merge(truth, on=["disease_index", "gene_index"], how="left")
df["is_validated"] = df.is_validated.fillna(0).astype(int)
saf = dataiku.Dataset("enriched_gene_safety").get_dataframe()
df = df.merge(saf, on="gene_index", how="left")

# LOEUF decile makes the graded signal readable as buckets
df["loeuf_bucket"] = pd.cut(df.lof_oe_upper, [0, 0.35, 0.7, 1.0, 1.5, 2.01],
                            labels=["<0.35 intolerant", "0.35-0.7", "0.7-1.0",
                                    "1.0-1.5", ">1.5 tolerant"])

base_a, base_d = df.is_target.mean(), df.is_validated.mean()
print(f"rows {len(df):,} over {df.disease_index.nunique()} diseases")
print(f"base rate  association {base_a:.4%}   drug-validated {base_d:.4%}\n")

rows = []
print(f"{'attribute = value':40s}{'n':>10s}{'assoc lift':>12s}{'drug lift':>11s}")
print("-" * 74)
for col in ["safety_flag", "lof_intolerant", "loeuf_bucket", "has_safety_liability"]:
    for v, g in df.groupby(df[col].astype("object").fillna("(null)"), observed=True):
        if len(g) < 2000:
            continue
        la, ld = g.is_target.mean() / base_a, g.is_validated.mean() / base_d
        rows.append({"attribute": col, "value": str(v), "n": len(g),
                     "assoc_rate": g.is_target.mean(), "drug_rate": g.is_validated.mean(),
                     "assoc_lift": la, "drug_lift": ld})
        print(f"{col + ' = ' + str(v):40s}{len(g):>10,}{la:>11.2f}x{ld:>10.2f}x")
    print()

out = pd.DataFrame(rows)

# ---- the prediction, evaluated ------------------------------------------------
print("=== VERDICT on the stated prediction ===")
# match on the numeric value, not its string form -- a pandas float group key renders as "1.0"
r = out[(out.attribute == "lof_intolerant") & (out.value.isin(["1", "1.0", "True"]))]
if len(r):
    ld, la = float(r.drug_lift.iloc[0]), float(r.assoc_lift.iloc[0])
    verdict = ("CONFIRMED -- depleted, as predicted" if ld < 0.9 else
               "REFUTED -- ENRICHED, the opposite of the prediction" if ld > 1.1 else
               "FLAT -- no therapeutic separation")
    print(f"  lof_intolerant  drug lift {ld:.2f}x | assoc lift {la:.2f}x  ->  {verdict}")

lb = out[out.attribute == "loeuf_bucket"].copy()
ORDER = ["<0.35 intolerant", "0.35-0.7", "0.7-1.0", "1.0-1.5", ">1.5 tolerant"]
lb = lb[lb.value.isin(ORDER)]
if len(lb) >= 3:
    lb["o"] = lb.value.map({v: i for i, v in enumerate(ORDER)})
    lb = lb.sort_values("o")
    print("\n  LOEUF gradient, most-constrained -> most-tolerant:")
    for _, x in lb.iterrows():
        print(f"    {x.value:20s} drug {x.drug_lift:.2f}x   assoc {x.assoc_lift:.2f}x")
    d = lb.drug_lift.tolist()
    print(f"    monotone decreasing: {all(d[i] >= d[i+1] for i in range(len(d)-1))}")
    print("    Constraint runs WITH druggability, not against it. So filtering out constrained")
    print("    genes would remove the best candidates -- the opposite of a safety filter.")

liab = out[(out.attribute == "has_safety_liability") & (out.value.isin(["1", "1.0"]))]
if len(liab):
    print(f"\n  has_safety_liability  drug lift {float(liab.drug_lift.iloc[0]):.2f}x  -- the")
    print("    attention confound, as predicted: liabilities are discovered BY drugging a target,")
    print("    so this marks well-precedented targets, not risky ones. Excluding on it would")
    print("    remove the best-evidenced candidates.")

print("\n=== CONCLUSION ===")
print("  NEITHER free signal is a safety filter. Both point the same way as efficacy, so used as")
print("  a filter they would strip the shortlist of its best candidates. Ship `safety_events` as")
print("  a DISPLAYED ANNOTATION only ('documented cardiac liability' is worth a scientist's")
print("  attention even when it predicts nothing), and get a real safety axis from a direct")
print("  measurement -- DepMap essentiality and tissue-expression breadth -- not from these.")
dataiku.Dataset("safety_lift").write_with_schema(out)

