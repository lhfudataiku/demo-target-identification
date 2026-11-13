# STRING zone -- EXTRACT (Python: parse protein.links.detailed + aliases, ground
# ENSP->Entrez via STRING's own "Ensembl_HGNC_entrez_id" alias rows).
# Filtered to EXPERIMENTAL + DATABASE evidence channels only (excludes text-mining,
# co-expression, neighborhood, fusion, cooccurrence -- the noisy/predicted channels) --
# matches this project's precision-over-recall stance (same pattern as ot_score_min).
# Output raw_string_ppi (gene_id_1, gene_id_2, experimental, database -- both Entrez,
# scores kept for reference/threshold-tuning downstream).
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE  (recorded 2026-08-13)
# Source        : STRING protein aliases, human (9606)
# URL in use    : https://stringdb-downloads.org/download/protein.aliases.v12.0/
#                 9606.protein.aliases.v12.0.txt.gz
# Version used  : v12.0 -- ALREADY PINNED in the URL. Verified reachable 2026-08-13.
# TO FREEZE     : nothing to do; the version is in the path. Bumping STRING means editing
#                 this URL deliberately.
# ----------------------------------------------------------------------------

import gzip
import io

import dataiku
import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
try:
    SCORE_MIN = float(dataiku.get_custom_variables().get("string_score_min", 700))
except Exception:
    SCORE_MIN = 700

# ENSP -> Entrez crosswalk via STRING's own alias file
r = requests.get(
    "https://stringdb-downloads.org/download/protein.aliases.v12.0/9606.protein.aliases.v12.0.txt.gz",
    timeout=300, headers=HEADERS)
r.raise_for_status()
aliases = pd.read_csv(io.BytesIO(r.content), sep="\t", dtype=str, compression="gzip")
aliases.columns = [c.lstrip("#").strip() for c in aliases.columns]
ensp_to_entrez = dict(zip(
    aliases[aliases.source == "Ensembl_HGNC_entrez_id"].string_protein_id,
    aliases[aliases.source == "Ensembl_HGNC_entrez_id"].alias))

# links.detailed (space-separated, per-channel scores)
r = requests.get(
    "https://stringdb-downloads.org/download/protein.links.detailed.v12.0/9606.protein.links.detailed.v12.0.txt.gz",
    timeout=600, headers=HEADERS)
r.raise_for_status()
links = pd.read_csv(io.BytesIO(r.content), sep=" ", compression="gzip",
                    usecols=["protein1", "protein2", "experimental", "database"])
links = links[(links.experimental >= SCORE_MIN) | (links.database >= SCORE_MIN)].copy()

links["gene_id_1"] = links.protein1.map(ensp_to_entrez)
links["gene_id_2"] = links.protein2.map(ensp_to_entrez)
out = links.dropna(subset=["gene_id_1", "gene_id_2"])[
    ["gene_id_1", "gene_id_2", "experimental", "database"]].drop_duplicates()

dataiku.Dataset("raw_string_ppi").write_with_schema(out)


