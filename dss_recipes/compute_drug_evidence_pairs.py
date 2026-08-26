# The per-(disease, gene) drug ground truth, materialised as a DISPLAY BADGE for the dashboard.
#
# WHY THIS EXISTS: `has_approved_drug` on the candidate table is GENE-LEVEL across all indications
# -- it means "chemical matter exists for this gene somewhere", NOT "a drug approved for THIS
# disease hits this gene". The dashboard needs the latter, per row, and nothing produced it.
#
# THE LOGIC IS COPIED FROM compute_novel_discovery_eval.py's pairs_for() ON PURPOSE. The badge a
# scientist reads on screen must be the SAME set the discovery lift was measured against. If these
# two drift apart, the dashboard quietly contradicts the validation numbers it is built to support.
#
# TWO GROUND TRUTHS, NEVER MERGED (design constraint 6):
#   approved         `indication`             a drug APPROVED for this disease hits this gene
#   investigational  `drug_investigated_for`  in trials, not approved -- INCLUDES FAILED PROGRAMMES
# "this is a drug" and "someone is trying" are different claims. One column each, never OR'd.
#
# *** THIS IS THE VALIDATION GROUND TRUTH. DISPLAY ONLY. ***
# It must never become a filter control and must never reach the model or the ranking. Filtering
# the shortlist on it would make the 4-13x discovery result circular -- the model would be scored
# on the labels it was filtered by. Same rule as the liability flag: badge, never control.
import dataiku
import pandas as pd

nid = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
nid["node_index"] = nid.node_index.astype(int)
nid["node_id"] = nid.node_id.astype(str)
dmap = dict(zip(nid[nid.node_type == "disease"].node_id,
                nid[nid.node_type == "disease"].node_index))
gmap = dict(zip(nid[nid.node_type == "gene/protein"].node_id,
                nid[nid.node_type == "gene/protein"].node_index))

dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)

# Orientation is not guaranteed by the schema -- detect it rather than assume x_type == "drug".
gc, tc = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
dp["drug"] = dp[gc].astype(str)
dp["gene_index"] = dp[tc].astype(str).map(gmap)
dp = dp.dropna(subset=["gene_index"])[["drug", "gene_index"]]
print("drug_disease relations:", dd.relation.astype(str).value_counts().to_dict())
print(f"drug->gene edges resolved: {len(dp):,}")


def pairs_for(rel_regex):
    sub = dd[dd.relation.astype(str).str.fullmatch(rel_regex, case=False, na=False)].copy()
    dc, xc = ("x_id", "y_id") if (sub.x_type == "drug").any() else ("y_id", "x_id")
    sub["drug"] = sub[dc].astype(str)
    sub["disease_index"] = sub[xc].astype(str).map(dmap)
    return (sub.dropna(subset=["disease_index"])[["drug", "disease_index"]]
            .merge(dp, on="drug")[["disease_index", "gene_index"]]
            .astype(int).drop_duplicates())


approved = pairs_for("indication")
investig = pairs_for("drug_investigated_for")
print(f"  approved        {len(approved):>7,} (disease, gene) pairs")
print(f"  investigational {len(investig):>7,} (disease, gene) pairs")

approved["approved_for_disease"] = 1
investig["investigational_for_disease"] = 1
out = (approved.merge(investig, on=["disease_index", "gene_index"], how="outer")
       .fillna(0).astype(int).sort_values(["disease_index", "gene_index"]))

print(f"\nunion {len(out):,} pairs over {out.disease_index.nunique():,} diseases, "
      f"{out.gene_index.nunique():,} genes")
print(f"  approved only        {((out.approved_for_disease == 1) & (out.investigational_for_disease == 0)).sum():>7,}")
print(f"  investigational only {((out.approved_for_disease == 0) & (out.investigational_for_disease == 1)).sum():>7,}")
print(f"  both                 {((out.approved_for_disease == 1) & (out.investigational_for_disease == 1)).sum():>7,}")

# Keys stay INTEGER to match target_candidates_2 (gene_index / disease_index are bigint there).
# The per-chunk dtype-inference hazard applies to get_dataframe() reads, not to a visual join
# between two typed managed datasets -- so matching the existing type beats casting to string.
dataiku.Dataset("drug_evidence_pairs").write_with_schema(out)

