# PrimeKG's published disease-grouping map (Harvard Dataverse datafile 6180623).
# Lets us apply PrimeKG's exact Bio_ClinicalBERT disease grouping deterministically,
# without re-running the interactive BERT pass.
# Zero-input recipe → disease_group_map.
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
