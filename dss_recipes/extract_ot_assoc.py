# Open Targets — EXTRACT association (Python: parquet load, per-part filter).
# Uses `genetic_association` (DisGeNET-curated analog: expert genetic/clinical evidence —
# GWAS Catalog, ClinVar, Genomics England, Gene2Phenotype, UniProt, Orphanet, ClinGen)
# + `somatic_mutation` (Cancer Gene Census, IntOGen, ClinVar somatic — added 2026-08-06,
# cancer persona only, see PRIMEKG_MAPPING.md §5: it surfaces tumor-driver genes e.g.
# PIK3CA/GATA3/MAP3K1/CDH1, complementary to genetic_association's germline-risk genes
# e.g. BRCA1/2, ATM, PALB2, CHEK2). Still EXCLUDES literature text-mining, animal-model,
# and known_drug datatypes (known_drug rejected as redundant with dwpc_GCD — see
# TARGET_PRIORITIZER.md §11).
# Output raw_ot_assoc (targetId ENSG, diseaseId EFO/MONDO, score, datatypes -- which
# datatype(s) support the max score, kept for traceability). No joins here.
#
# NOTE: widens disease_protein/is_target for cancer-type diseases -- re-check
# has-path-evidence coverage + the leakage diagnosis (TARGET_PRIORITIZER.md §6b) for
# those diseases before trusting new Part 2 results there (decision log §12).
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE  (recorded 2026-08-13)
# Source        : Open Targets Platform (parquet exports over FTP)
# URL in use    : https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/
# Version used  : platform release 26.06 -- ALREADY PINNED in the URL. Reachable 2026-08-13.
# TO FREEZE     : nothing to do; the release is in the path. Bumping Open Targets means
#                 editing this URL deliberately, and OT changes column layouts between
#                 releases, so re-verify the schema when you do.
# ----------------------------------------------------------------------------

import os
import re
import tempfile

import dataiku
import pandas as pd
import requests

BASE = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
DATATYPES = ["genetic_association", "somatic_mutation"]
try:
    SCORE_MIN = float(dataiku.get_custom_variables().get("ot_score_min", 0.3))
except Exception:
    SCORE_MIN = 0.3

sub = "association_by_datatype_direct"
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
        # by_datatype encodes the datatype in aggregationValue (aggregationType="dataType")
        p = pd.read_parquet(tmp, columns=["targetId", "diseaseId", "aggregationValue", "associationScore"])
        frames.append(p[p.aggregationValue.isin(DATATYPES) & (p.associationScore >= SCORE_MIN)])
    finally:
        os.remove(tmp)

all_rows = pd.concat(frames, ignore_index=True).rename(columns={"associationScore": "score"})
out = (all_rows.groupby(["targetId", "diseaseId"], as_index=False)
       .agg(score=("score", "max"),
            datatypes=("aggregationValue", lambda s: "+".join(sorted(set(s))))))
dataiku.Dataset("raw_ot_assoc").write_with_schema(out)


