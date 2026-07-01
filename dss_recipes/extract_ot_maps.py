# Open Targets — EXTRACT reference maps (Python: parquet load + nested-array parse).
# Shared by the gene-disease and drug zones for visual joins downstream.
# Outputs: ot_target_map (ensg, symbol), ot_disease_map (diseaseId, mondo_id bare-int).
import os
import re
import tempfile

import dataiku
import pandas as pd
import requests

BASE = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def read_ot(subdir, columns=None):
    html = requests.get(BASE + subdir + "/", timeout=120, headers=HEADERS).text
    files = [f for f in re.findall(r'href="([^"]+\.parquet)"', html) if "/" not in f]
    frames = []
    for f in sorted(files):
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


target = (read_ot("target", columns=["id", "approvedSymbol"])
          .rename(columns={"id": "ensg", "approvedSymbol": "symbol"}).dropna().drop_duplicates())


def to_mondo_int(row):
    did = row["id"]
    if isinstance(did, str) and did.startswith("MONDO_"):
        return str(int(did.split("_")[-1]))
    xrefs = row["dbXRefs"]
    if xrefs is not None and len(xrefs):
        for x in xrefs:
            if isinstance(x, str) and (x.startswith("MONDO:") or x.startswith("MONDO_")):
                return str(int(x.replace("MONDO_", "MONDO:").split(":")[-1]))
    return None


dis = read_ot("disease", columns=["id", "dbXRefs"])
dis["mondo_id"] = dis.apply(to_mondo_int, axis=1)
disease = dis.rename(columns={"id": "diseaseId"})[["diseaseId", "mondo_id"]].dropna().drop_duplicates()

dataiku.Dataset("ot_target_map").write_with_schema(target)
dataiku.Dataset("ot_disease_map").write_with_schema(disease)
