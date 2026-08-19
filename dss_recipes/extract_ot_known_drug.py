# Open Targets — EXTRACT the `known_drug` association datatype as a CURATED therapeutic label.
#
# WHY THIS EXISTS: our drug-validated ground truth was built by joining drug->disease to
# drug->target through the drug, which MANUFACTURES the (disease, gene) pair. Open Targets never
# asserts "gene G is the target for disease X"; it asserts the two edges separately. Measured on
# our own data, 82.2% of the joined triples come from multi-target drugs, 66.3% from drugs that are
# multi on both axes, and only 8.0% survives a single-target restriction. The consequence was
# severe: discovery lift@10 fell 11.40 -> 0.00 as the inflation was removed (TARGET_PRIORITIZER
# §8.3), i.e. the headline number was an artifact of the join.
#
# `known_drug` fixes it at the source. Open Targets curates the TARGET-DISEASE linkage itself from
# ChEMBL, so there is no Cartesian product to remove.
#
# WHY IT IS LEGITIMATE HERE AND NOT AS A FEATURE: `known_drug` was excluded from `raw_ot_assoc` in
# 2026-08-05 because using it to TRAIN is circular -- it restates "a drug already exists for this
# pair", which is close to the label. That argument does not apply to EVALUATION. Using it to score
# a model that never saw it is exactly what an independent ground truth is for.
#
# NO SCORE THRESHOLD is applied. OT's known_drug score encodes maximum clinical phase, so keeping
# it lets the downstream split approved-like from trial-like evidence instead of guessing a cutoff.
#
# The ENSG->symbol crosswalk is pulled from the same OT target file already downloaded for
# druggability and safety, so this needs no new shared object from the graph project.
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE
# Source      : Open Targets Platform (parquet exports over FTP)
# URL in use  : https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/
# Version     : release 26.06 -- ALREADY PINNED in the URL.
# TO FREEZE   : nothing to do. OT changes column layouts between releases; re-verify on a bump.
# ----------------------------------------------------------------------------
import os
import re
import tempfile

import dataiku
import pandas as pd
import requests

BASE = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def read_ot(sub, columns, keep=None):
    html = requests.get(BASE + sub + "/", timeout=120, headers=HEADERS).text
    files = sorted(f for f in re.findall(r'href="([^"]+\.parquet)"', html) if "/" not in f)
    frames = []
    for f in files:
        rr = requests.get(BASE + sub + "/" + f, timeout=600, headers=HEADERS)
        rr.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
            tf.write(rr.content)
            tmp = tf.name
        try:
            p = pd.read_parquet(tmp, columns=columns)
            frames.append(keep(p) if keep else p)
        finally:
            os.remove(tmp)
    return pd.concat(frames, ignore_index=True)


assoc = read_ot("association_by_datatype_direct",
                ["targetId", "diseaseId", "aggregationValue", "associationScore"],
                keep=lambda p: p[p.aggregationValue == "known_drug"])
print(f"known_drug association rows: {len(assoc):,}")
assoc = (assoc.rename(columns={"associationScore": "score"})
         .groupby(["targetId", "diseaseId"], as_index=False).score.max())
print(f"  distinct (ENSG, diseaseId) pairs: {len(assoc):,}")
print(f"  score distribution:\n{assoc.score.describe().to_string()}")

tgt = read_ot("target", ["id", "approvedSymbol"])
tgt = tgt.rename(columns={"id": "targetId", "approvedSymbol": "symbol"}).dropna()
out = assoc.merge(tgt, on="targetId", how="left")
print(f"\n  resolved to a gene symbol: {out.symbol.notna().sum():,} of {len(out):,} "
      f"({out.symbol.notna().mean():.1%})")
print(f"  distinct targets {out.targetId.nunique():,} | distinct diseases {out.diseaseId.nunique():,}")
print(f"\n  targets per disease: median {out.groupby('diseaseId').targetId.nunique().median():.0f} "
      f"| max {out.groupby('diseaseId').targetId.nunique().max()}")
print(f"  diseases per target: median {out.groupby('targetId').diseaseId.nunique().median():.0f} "
      f"| max {out.groupby('targetId').diseaseId.nunique().max()}")

dataiku.Dataset("raw_ot_known_drug").write_with_schema(
    out[["targetId", "symbol", "diseaseId", "score"]])
