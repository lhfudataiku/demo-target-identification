# PPI evidence depth — study-bias control feature (gene-level).
#
# Motivation (TARGET_PRIORITIZER §6e / GLP1R case study): the model reads a SPARSE PPI
# neighbourhood as "not a target", but for membrane receptors (class-B GPCRs like GLP1R,
# GIPR, GCGR) sparseness is an ASSAY artifact -- Y2H/AP-MS capture transmembrane proteins
# poorly -- not a biology signal. GLP1R shares only 3 neighbours with the obesity module
# vs GCG's 13 despite comparable degree, and is scored 0.853 (false negative) vs GCG's 0.980.
#
# This feature gives the model a measurement-CONFIDENCE covariate so it can discount a
# thin neighbourhood instead of treating thin == negative. Source: edge_metadata.ppi_sources,
# the menche/huri/string provenance carried through compute_kg (METADATA_COLS).
#
# NOTE this is a GENE-ONLY feature (no disease-specific information). That block is
# otherwise the study-bias vector (§6e) -- it earns its place only because it encodes
# assay coverage rather than popularity. A pair-level extension (evidence depth of the
# SHARED neighbours specifically) is the natural follow-up if this helps.
import dataiku
import pandas as pd

# Dataset DEMO_KG_LS.edge_metadata renamed to DEMO_KG_edge_metadata_copy by liheng.fu@dataiku.com on 2026-08-18 09:37:49
# Dataset DEMO_KG_edge_metadata_copy renamed to edge_metadata by liheng.fu@dataiku.com on 2026-08-18 09:57:21
meta = dataiku.Dataset("edge_metadata").get_dataframe(
    columns=["x_index", "y_index", "relation", "ppi_sources"])
ppi = meta[(meta.relation == "protein_protein") & meta.ppi_sources.notna()].copy()

# ppi_sources is a "+"-joined set, e.g. "menche", "menche+huri", "huri+string"
ppi["n_sources"] = ppi.ppi_sources.astype(str).str.count(r"\+") + 1

# edge_metadata is built AFTER compute_kg's reverse-all, so both directions are present;
# grouping on x_index alone therefore covers every gene's full edge set.
agg = ppi.groupby("x_index").agg(
    ppi_evidence_depth=("n_sources", "mean"),
    ppi_multi_source_frac=("n_sources", lambda s: (s >= 2).mean()),
    ppi_edges_with_provenance=("n_sources", "size"),
).reset_index().rename(columns={"x_index": "gene_index"})

print("ppi_evidence_depth rows:", agg.shape)
print(agg[["ppi_evidence_depth", "ppi_multi_source_frac"]].describe().to_string())
dataiku.Dataset("enriched_ppi_evidence_depth").write_with_schema(agg)

