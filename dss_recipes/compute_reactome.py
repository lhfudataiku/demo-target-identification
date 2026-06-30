# Pathway nodes + hierarchy + gene–pathway edges from Reactome (human only).
# Zero-input recipe → reactome_terms, reactome_relations, reactome_ncbi.
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


# 1. Pathway nodes — ReactomePathways.txt: pathway_id, name, species
terms = pd.read_csv(io.StringIO(get("ReactomePathways.txt")), sep="\t",
                    header=None, names=["pathway_id", "name", "species"], dtype=str)
terms = (terms[terms["species"] == "Homo sapiens"][["pathway_id", "name"]]
         .drop_duplicates())

# 2. Pathway hierarchy — ReactomePathwaysRelation.txt: parent_id, child_id
rels = pd.read_csv(io.StringIO(get("ReactomePathwaysRelation.txt")), sep="\t",
                   header=None, names=["parent_id", "child_id"], dtype=str)
rels = rels[rels["parent_id"].str.startswith("R-HSA-")
            & rels["child_id"].str.startswith("R-HSA-")].drop_duplicates()

# 3. Gene–pathway — NCBI2Reactome.txt: ncbi_id, pathway_id, url, name, evidence, species
g2p = pd.read_csv(io.StringIO(get("NCBI2Reactome.txt")), sep="\t", header=None,
                  names=["ncbi_id", "pathway_id", "url", "event_name",
                         "evidence_code", "species"], dtype=str)
g2p = g2p[g2p["species"] == "Homo sapiens"].copy()
g2p["entrez_id"] = pd.to_numeric(g2p["ncbi_id"], errors="coerce")
g2p = (g2p.dropna(subset=["entrez_id"])
       .assign(entrez_id=lambda d: d["entrez_id"].astype("int64"))
       [["entrez_id", "pathway_id"]].drop_duplicates())

dataiku.Dataset("reactome_terms").write_with_schema(terms)
dataiku.Dataset("reactome_relations").write_with_schema(rels)
dataiku.Dataset("reactome_ncbi").write_with_schema(g2p)
