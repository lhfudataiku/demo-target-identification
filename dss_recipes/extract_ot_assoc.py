# Open Targets — EXTRACT association (Python: parquet load, per-part score filter).
# Output raw_ot_assoc (targetId ENSG, diseaseId EFO/MONDO, score). No joins here.
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

sub = "association_overall_direct"
html = requests.get(BASE + sub + "/", timeout=120, headers=HEADERS).text
files = [f for f in re.findall(r'href="([^"]+\.parquet)"', html) if "/" not in f]
frames = []
for f in sorted(files):
    rr = requests.get(BASE + sub + "/" + f, timeout=600, headers=HEADERS)
    rr.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
        tf.write(rr.content)
        tmp = tf.name
    try:
        p = pd.read_parquet(tmp, columns=["targetId", "diseaseId", "associationScore"])
        frames.append(p[p.associationScore >= SCORE_MIN])
    finally:
        os.remove(tmp)

out = (pd.concat(frames, ignore_index=True).rename(columns={"associationScore": "score"})
       .groupby(["targetId", "diseaseId"], as_index=False)["score"].max())
dataiku.Dataset("raw_ot_assoc").write_with_schema(out)
