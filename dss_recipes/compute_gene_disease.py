# Gene–disease edges from Open Targets Platform 26.06.
# Input dataset: gene_names (symbol -> entrez_id).
# Downloads OT parquet (association_overall_direct, target, disease) over HTTP,
# thresholds on score, maps ENSG->HGNC symbol->Entrez and EFO->MONDO.
# Output: gene_disease.
import os
import re
import tempfile

import dataiku
import pandas as pd
import requests

BASE = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

try:
    SCORE_MIN = float(dataiku.get_custom_variables().get("ot_score_min", 0.3))
except Exception:
    SCORE_MIN = 0.3


def read_ot(subdir, columns=None):
    html = requests.get(BASE + subdir + "/", timeout=120, headers=HEADERS).text
    files = sorted(set(re.findall(r'href="([^"]+\.parquet)"', html)))
    files = [f for f in files if "/" not in f]  # drop parent/absolute links
    frames = []
    for f in files:
        rr = requests.get(BASE + subdir + "/" + f, timeout=600, headers=HEADERS)
        rr.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
            tf.write(rr.content)
            tmp = tf.name
        try:
            frames.append(pd.read_parquet(tmp, columns=columns))
        finally:
            os.remove(tmp)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# 1. associations (target–disease, overall direct), thresholded.
# 26.06 column is `associationScore`; collapse to one max score per pair.
assoc = read_ot("association_overall_direct",
                columns=["targetId", "diseaseId", "associationScore"])
assoc = (assoc.rename(columns={"associationScore": "score"})
         .groupby(["targetId", "diseaseId"], as_index=False)["score"].max())
assoc = assoc[assoc["score"] >= SCORE_MIN].copy()

# 2. target ENSG -> HGNC approvedSymbol
tgt = (read_ot("target", columns=["id", "approvedSymbol"])
       .rename(columns={"id": "targetId", "approvedSymbol": "symbol"}))

# 3. disease EFO/MONDO id -> MONDO id (colon form)
dis = read_ot("disease", columns=["id", "dbXRefs"]).rename(columns={"id": "diseaseId"})


def to_mondo(row):
    did = row["diseaseId"]
    if isinstance(did, str) and did.startswith("MONDO_"):
        return did.replace("MONDO_", "MONDO:")
    xrefs = row["dbXRefs"]
    if xrefs is not None and len(xrefs):
        for x in xrefs:
            if isinstance(x, str) and (x.startswith("MONDO:") or x.startswith("MONDO_")):
                return x.replace("MONDO_", "MONDO:")
    return None


dis["mondo_id"] = dis.apply(to_mondo, axis=1)
dis = dis[["diseaseId", "mondo_id"]].dropna(subset=["mondo_id"])

# 4. join: assoc -> symbol -> mondo -> entrez (via gene_names)
gn = dataiku.Dataset("gene_names").get_dataframe()[["symbol", "entrez_id"]]
edges = (assoc
         .merge(tgt, on="targetId", how="inner")
         .merge(dis, on="diseaseId", how="inner")
         .merge(gn, on="symbol", how="inner"))

out = (edges[["entrez_id", "symbol", "mondo_id", "score", "targetId", "diseaseId"]]
       .dropna(subset=["entrez_id", "mondo_id"])
       .drop_duplicates())

dataiku.Dataset("gene_disease").write_with_schema(out)
