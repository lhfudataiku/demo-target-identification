# Dataiku Python recipe — recreates PrimeKG's
# datasets/processing_scripts/map_umls_mondo.py
#
# INPUTS  datasets:
#   umls               (from compute_umls.py: cui, source_cui,
#                        source_descriptor_dui, source, source_code)
#   mondo_references   (from PrimeKG mondo.py / mondo.obo:
#                        ontology, ontology_id, mondo_id)
# OUTPUT  dataset:
#   umls_mondo         (umls_id, mondo_id)  -- the disease-ID crosswalk
#
# Direct  : MONDO xrefs already tagged ontology=="UMLS".
# Indirect: join UMLS rows to MONDO xrefs through six bridge vocabularies,
#           matching the UMLS SAB to the MONDO xref ontology.

import dataiku
import pandas as pd

df_umls = dataiku.Dataset("umls").get_dataframe()
df_mondo_xref = dataiku.Dataset("mondo_references").get_dataframe()

# --- Direct UMLS -> MONDO -------------------------------------------------
map_direct = (
    df_mondo_xref.query('ontology == "UMLS"')[["ontology_id", "mondo_id"]]
    .rename(columns={"ontology_id": "umls_id"})
)

# --- Indirect via bridge vocabularies ------------------------------------
# (UMLS SAB  ->  MONDO xref ontology)
VOCAB_PAIRS = {
    "OMIM": "OMIM",
    "NCI": "NCIT",
    "MSH": "MESH",
    "MDR": "MedDRA",
    "ICD10": "ICD10",
    "SNOMEDCT_US": "SCTID",
}

# UMLS exposes the source code in three different fields depending on vocabulary,
# so PrimeKG attempts the join on each of them, then keeps only valid SAB/ontology
# pairs.
df_umls_join = df_umls.copy()
joins = []
for left_key in ["source_cui", "source_descriptor_dui", "source_code"]:
    m = pd.merge(
        df_umls_join,
        df_mondo_xref,
        how="inner",
        left_on=left_key,
        right_on="ontology_id",
    )
    joins.append(m)

map_all = pd.concat(joins, ignore_index=True)

# Keep rows where the UMLS source vocabulary matches the MONDO xref ontology.
valid = map_all.apply(
    lambda r: VOCAB_PAIRS.get(r["source"]) == r["ontology"], axis=1
)
map_indirect = (
    map_all[valid][["cui", "mondo_id"]].rename(columns={"cui": "umls_id"})
)

# --- Combine --------------------------------------------------------------
df_umls_mondo = (
    pd.concat([map_direct, map_indirect], ignore_index=True)
    .drop_duplicates()
    .reset_index(drop=True)
)

dataiku.Dataset("umls_mondo").write_with_schema(df_umls_mondo)
