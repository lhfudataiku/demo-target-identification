# PrimeKG's published disease-grouping map (Harvard Dataverse datafile 6180623).
# Applies PrimeKG's exact Bio_ClinicalBERT disease grouping deterministically, without
# re-running the interactive BERT pass.
# Input:  folder raw_files (/disease_group_map_dataverse6180623_snapshot_20260814.csv)
# Output: disease_group_map
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE  (recorded 2026-08-14)
# Source        : PrimeKG's published Bio_ClinicalBERT disease grouping
# Original URL  : https://dataverse.harvard.edu/api/access/datafile/6180623   <-- PINNED id
# *** THE LIVE FETCH IS BROKEN. As of 2026-08-13 the endpoint answers HTTP 202 with a
# *** ZERO-BYTE body, so `pd.read_csv` raised "No columns to parse from file". This recipe
# *** therefore reads a SNAPSHOT from the raw_files folder instead of the network.
# Snapshot      : /disease_group_map_dataverse6180623_snapshot_20260814.csv (789.8 KB,
#                 6,392 rows) exported from KNOWLEDGE_GRAPH_PRIMEKG.disease_group_map on
#                 2026-08-14 -- i.e. the last successful fetch of datafile 6180623.
# NOTE ON SHAPE : the snapshot is the POST-PROCESSED output, not the raw Dataverse TSV. The
#                 original recipe read 7 columns (node_id, node_type, node_name, node_source,
#                 group_name_auto, group_name_bert, group_id_bert), kept 3, dropped nulls and
#                 de-duplicated on node_id. Those steps were already applied when the
#                 snapshot was taken, so this recipe is a loader with the same 3-column
#                 contract; downstream (`compute_kg`) is unchanged.
# LOAD-BEARING  : do not delete. It creates the 1,247 `MONDO_grouped` nodes -- 883 of the
#                 6,821 modelled diseases and 115 of 588 scored validation diseases
#                 (11,352 positives) in the reference project. Dropping it shifts every
#                 node_index.
# TO RESTORE THE LIVE FETCH, if Dataverse recovers:
#                 1. verify the URL returns a non-empty TSV (curl -sL <url> | head)
#                 2. replace the folder read below with:
#                      r = requests.get(URL, timeout=300,
#                                       headers={"User-Agent": "Mozilla/5.0"})
#                      r.raise_for_status()
#                      df = pd.read_csv(io.StringIO(r.text), sep="\t", dtype=str)
#                      df = df[["node_id", "group_id_bert", "group_name_bert"]] \
#                             .dropna().drop_duplicates("node_id")
#                 3. re-add the folder input removal, and confirm the row count is still
#                    6,392 (or record the new count deliberately -- it changes node_index).
# ----------------------------------------------------------------------------
import dataiku
import pandas as pd

SNAPSHOT = "/disease_group_map_dataverse6180623_snapshot_20260814.csv"

folder = dataiku.Folder("raw_files")
# get_download_stream, NOT get_path(): this recipe runs in a container, where
# "direct access to folder is not possible" and get_path() raises.
with folder.get_download_stream(SNAPSHOT) as stream:
    df = pd.read_csv(stream, dtype=str)

# Same contract the live fetch produced: 3 columns, no nulls, unique on node_id.
df = df[["node_id", "group_id_bert", "group_name_bert"]].dropna().drop_duplicates("node_id")
assert len(df) == 6392, f"expected 6,392 rows from the snapshot, got {len(df)}"

print("disease_group_map rows:", len(df),
      "| distinct groups:", df.group_id_bert.nunique())
dataiku.Dataset("disease_group_map").write_with_schema(df)
