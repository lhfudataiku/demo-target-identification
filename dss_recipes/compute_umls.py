# Dataiku Python recipe — recreates PrimeKG's datasets/processing_scripts/umls.py
#
# INPUT  dataset:  MRCONSO_filtered   (the MRCONSO.filtered.RRF produced by
#                  scripts/filter_mrconso.sh, uploaded to DSS as a files-based
#                  dataset with separator "|" and NO header)
# OUTPUT dataset:  umls               (equivalent to PrimeKG's umls.csv)
#
# MRCONSO.RRF has 18 pipe-delimited fields + a trailing empty field. We name them
# per the standard UMLS layout, keep English rows, and project the columns the
# downstream MONDO mapping needs.

import dataiku
import pandas as pd

# Standard MRCONSO.RRF column layout (19 slots incl. trailing empty field).
MRCONSO_COLS = [
    "cui", "language", "term_status", "lui", "string_type", "string_identifier",
    "is_preferred", "aui", "source_aui", "source_cui", "source_descriptor_dui",
    "source", "source_term_type", "source_code", "source_name",
    "srl", "suppress", "cvf", "_trailing",
]

# Read the uploaded, pre-filtered MRCONSO as raw rows.
mrconso = dataiku.Dataset("MRCONSO_filtered")
df = mrconso.get_dataframe(infer_with_pandas=False)

# If DSS imported it with positional column names (col_0..), remap by position;
# otherwise assume it already carries the named columns above.
if list(df.columns)[:3] != ["cui", "language", "term_status"]:
    df = df.iloc[:, : len(MRCONSO_COLS)]
    df.columns = MRCONSO_COLS[: df.shape[1]]

# Pre-filter already restricted to ENG, but keep this for correctness if the
# recipe is ever run on an unfiltered upload.
df = df[df["language"] == "ENG"]

# Only these columns are consumed by the UMLS->MONDO join.
out = df[["cui", "source_cui", "source_descriptor_dui", "source", "source_code"]].copy()
out = out.drop_duplicates()

dataiku.Dataset("umls").write_with_schema(out)
