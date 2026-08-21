# PrimeKG's published disease-grouping map (Harvard Dataverse datafile 6180623).
# Lets us apply PrimeKG's exact Bio_ClinicalBERT disease grouping deterministically,
# without re-running the interactive BERT pass.
# Zero-input recipe → disease_group_map.
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE  (recorded 2026-08-13)
# Source        : PrimeKG's published Bio_ClinicalBERT disease grouping
# URL in use    : https://dataverse.harvard.edu/api/access/datafile/6180623   <-- PINNED id
# Version used  : Harvard Dataverse datafile 6180623 -> 6,392 rows in `disease_group_map`
# *** BROKEN AS OF 2026-08-13: the endpoint returns HTTP 202 with a ZERO-BYTE body, so
# *** pd.read_csv raises "No columns to parse from file". This recipe CANNOT run today.
# LOAD-BEARING  : do not delete. It creates the 1,247 `MONDO_grouped` nodes, which are 883 of
#                 the 6,821 modelled diseases and 115 of 588 scored validation diseases
#                 (11,352 positives). Deleting it shifts every node_index.
# TO FREEZE     : export the existing `disease_group_map` dataset (6,392 rows) to CSV, upload
#                 to raw_files, and read from the folder. That is also the only way to make
#                 this recipe runnable again.
# ----------------------------------------------------------------------------

import io

import dataiku
import pandas as pd
import requests

URL = "https://dataverse.harvard.edu/api/access/datafile/6180623"
r = requests.get(URL, timeout=300, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()

# Columns: node_id, node_type, node_name, node_source,
#          group_name_auto, group_name_bert, group_id_bert
df = pd.read_csv(io.StringIO(r.text), sep="\t", dtype=str)
df = df[["node_id", "group_id_bert", "group_name_bert"]].dropna().drop_duplicates("node_id")

dataiku.Dataset("disease_group_map").write_with_schema(df)


