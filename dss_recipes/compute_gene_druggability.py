# Combined druggability annotation — OT (primary) + GO localization (fallback).
#
# PURPOSE: give the ranked candidate list a human-readable target-class label so a scientist
# can tell a druggable membrane receptor from a non-druggable secreted ligand at a glance.
# This is the readability fix for TARGET_PRIORITIZER §10.3, where the model ranks GCG/GIP/IAPP
# (ligands, not targets) above GLP1R/GIPR/CALCR (receptors, known targets).
#
# PRECEDENCE (measured coverage within the graph's 20,861 genes):
#   1. ot_class_l1        ChEMBL protein family, authoritative but sparse   ~28%
#   2. ot_subcell_*       UniProt/HPA localization, accurate + broad        ~90%
#   3. GO cellcomp flags  already in the graph, fills OT gaps               ~36%
#   4. "unknown"
# A vs B agree 88.2% on membrane / 95.6% on secreted; where they disagree OT is generally
# right (BRCA1 carries a real-but-misleading GO membrane annotation; OT calls it Enzyme).
#
# NODE_INDEX SAFETY: per-gene ATTRIBUTE table only -- no nodes, no edges, so `compute_kg`'s
# positional node_index assignment is untouched.
import dataiku
import numpy as np
import pandas as pd

ot = dataiku.Dataset("raw_ot_druggability").get_dataframe()
loc = dataiku.Dataset("enriched_gene_localization").get_dataframe()
nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
gn = dataiku.Dataset("gene_names").get_dataframe(columns=["symbol", "entrez_id"])

# ENSG -> symbol -> entrez -> gene_index
gp = nodes[nodes.node_type == "gene/protein"].copy()
gp["entrez"] = gp.node_id.astype(str)
gp["node_index"] = gp.node_index.astype(int)
gn = gn.dropna(subset=["entrez_id"]).copy()
gn["entrez"] = gn.entrez_id.astype("int64").astype(str)
sym2idx = gn.merge(gp[["entrez", "node_index"]], on="entrez")[["symbol", "node_index"]] \
            .drop_duplicates("symbol")

ot = ot.merge(sym2idx, on="symbol", how="inner").rename(columns={"node_index": "gene_index"})
df = loc.merge(ot.drop(columns=["ensg", "symbol"]), on="gene_index", how="left")

# ---- combined class, by precedence -------------------------------------------
LIGAND_CLASSES = {"Secreted protein"}
MEMBRANE_CLASSES = {"Membrane receptor", "Ion channel", "Transporter", "Adhesion",
                    "Surface antigen", "Other membrane protein", "Auxiliary transport protein"}

cond = [
    df.ot_class_l1.isin(MEMBRANE_CLASSES),
    df.ot_class_l1.isin(LIGAND_CLASSES),
    df.ot_class_l1.notna(),
    (df.ot_subcell_membrane == 1) & (df.ot_subcell_secreted == 0),
    (df.ot_subcell_secreted == 1) & (df.ot_subcell_membrane == 0),
    (df.ot_subcell_membrane == 1) & (df.ot_subcell_secreted == 1),
    df.ot_subcell_membrane.notna(),
    df.localization_class == "membrane",
    df.localization_class == "secreted",
    df.localization_class == "membrane_and_secreted",
]
choice = [
    "membrane / cell-surface", "secreted", df.ot_class_l1,
    "membrane / cell-surface", "secreted", "membrane + secreted", "intracellular",
    "membrane / cell-surface", "secreted", "membrane + secreted",
]
df["druggability_class"] = np.select(cond, choice, default="unknown")

df["druggability_evidence"] = np.select(
    [df.ot_class_l1.notna(), df.ot_subcell_membrane.notna(),
     df.localization_class != "intracellular_or_unannotated"],
    ["OT target class", "OT subcellular", "GO cellular component"], default="none")

# is this plausibly a small-molecule / antibody target?
df["ot_sm_tractable"] = df.ot_sm_tractable.fillna(0).astype(int)
df["ot_ab_tractable"] = df.ot_ab_tractable.fillna(0).astype(int)
df["has_approved_drug"] = df.ot_sm_buckets.fillna("").str.contains("Approved Drug").astype(int)

out = df[["gene_index", "druggability_class", "druggability_evidence", "ot_class_l1",
          "ot_class_l2", "ot_sm_tractable", "ot_ab_tractable", "has_approved_drug",
          "ot_sm_buckets", "localization_class"]].copy()

# Several OT Ensembl ids can collapse onto one approvedSymbol -> one gene_index. Keep the
# best-evidence row per gene so the downstream join can never multiply candidate rows.
EVIDENCE_RANK = {"OT target class": 0, "OT subcellular": 1, "GO cellular component": 2, "none": 3}
out["_rank"] = out.druggability_evidence.map(EVIDENCE_RANK).fillna(9)
before = len(out)
out = (out.sort_values(["gene_index", "_rank"])
          .drop_duplicates("gene_index", keep="first")
          .drop(columns=["_rank"]))
print(f"deduplicated {before:,} -> {len(out):,} rows (one per gene_index)")
assert out.gene_index.is_unique, "gene_index must be unique before the downstream join"

print(f"genes: {len(out):,}")
print("\n=== druggability_class ===")
print(out.druggability_class.value_counts().to_string())
print("\n=== evidence source ===")
print(out.druggability_evidence.value_counts().to_string())
print(f"\ncoverage (class != unknown): {(out.druggability_class != 'unknown').mean():.1%}")
dataiku.Dataset("enriched_gene_druggability").write_with_schema(out)
