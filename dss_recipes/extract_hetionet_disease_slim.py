# Hetionet DO Slim — EXTRACT (Python: fetch + filter to Disease nodes).
# Static v1.0 resource (137 hand-curated Disease Ontology terms, antichain-checked
# by the original authors -- no DO Slim disease is a subtype of another). Used as
# a small set of "safe" rollup anchors for disease_family_id: mitigates train/test
# leakage from MONDO parent-child/sibling disease concepts (e.g. breast cancer vs
# breast carcinoma) without collapsing the eligible-disease population the way a
# raw connected-components grouping over the full MONDO hierarchy does (see
# decision log). Outputs: hetionet_disease_slim (doid, name).
import io

import dataiku
import pandas as pd
import requests

URL = "https://raw.githubusercontent.com/hetio/hetionet/main/hetnet/tsv/hetionet-v1.0-nodes.tsv"
HEADERS = {"User-Agent": "Mozilla/5.0"}

r = requests.get(URL, timeout=120, headers=HEADERS)
r.raise_for_status()
nodes = pd.read_csv(io.StringIO(r.text), sep="\t")
diseases = nodes[nodes.kind == "Disease"].copy()
diseases["doid"] = diseases["id"].str.replace("Disease::DOID:", "", regex=False)
out = diseases[["doid", "name"]].drop_duplicates()

dataiku.Dataset("hetionet_disease_slim").write_with_schema(out)
