# Pathways zone — EXTRACT (Python: load + parse only, native ids).
# Names resolved at assembly from reactome_terms. No cross-dataset joins here.
# Outputs: reactome_terms (vocab), raw_pathway_protein, raw_pathway_pathway.
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE  (recorded 2026-08-13)
# Source        : Reactome pathway hierarchy + protein mappings
# URL in use    : https://reactome.org/download/current/          <-- UNPINNED, literally "current"
# Version used  : release 97 (from https://reactome.org/ContentService/data/database/version,
#                 queried 2026-08-13) -> 2,883 rows in `reactome_terms`
# TO FREEZE     : Reactome keeps per-release archives; the documented pattern is
#                 https://reactome.org/download/archive/<release>/ -- VERIFY the exact path
#                 before relying on it (not tested here). Otherwise snapshot to raw_files.
# ----------------------------------------------------------------------------

import io

import dataiku
import pandas as pd
import requests

BASE = "https://reactome.org/download/current/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get(name):
    r = requests.get(BASE + name, timeout=180, headers=HEADERS)
    r.raise_for_status()
    return r.text


terms = pd.read_csv(io.StringIO(get("ReactomePathways.txt")), sep="\t", header=None,
                    names=["pathway_id", "name", "species"], dtype=str)
terms = terms[terms.species == "Homo sapiens"][["pathway_id", "name"]].drop_duplicates()
human = set(terms.pathway_id)

# gene–pathway (native: entrez, pathway_id)
g2p = pd.read_csv(io.StringIO(get("NCBI2Reactome.txt")), sep="\t", header=None,
                  names=["ncbi_id", "pathway_id", "url", "event", "evidence", "species"],
                  dtype=str)
g2p = g2p[g2p.species == "Homo sapiens"].copy()
g2p["entrez_id"] = pd.to_numeric(g2p.ncbi_id, errors="coerce")
raw_gp = (g2p.dropna(subset=["entrez_id"])
          .assign(entrez_id=lambda d: d.entrez_id.astype("int64"))
          [["entrez_id", "pathway_id"]].drop_duplicates())

# pathway hierarchy (native: parent_id, child_id; human only)
rels = pd.read_csv(io.StringIO(get("ReactomePathwaysRelation.txt")), sep="\t",
                   header=None, names=["parent_id", "child_id"], dtype=str)
raw_pp = rels[rels.parent_id.isin(human) & rels.child_id.isin(human)].drop_duplicates()

dataiku.Dataset("reactome_terms").write_with_schema(terms)
dataiku.Dataset("raw_pathway_protein").write_with_schema(raw_gp)
dataiku.Dataset("raw_pathway_pathway").write_with_schema(raw_pp)


