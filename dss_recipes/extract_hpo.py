# HPO zone -- EXTRACT (Python: parse hp.obo + phenotype.hpoa + genes_to_phenotype.txt,
# native ids). Names resolved at assembly from hpo_terms. No cross-dataset joins here --
# disease_id is split into (ontology, ontology_id), the same xref shape mondo_references
# already uses (OMIM/ORPHA/DECIPHER -> MONDO), ready for a visual Join at harmonize.
# Outputs: hpo_terms (vocab), raw_phenotype_hierarchy, raw_disease_phenotype
#          (aspect=="P" only; qualifier blank=positive/"NOT"=negative, kept as-is for
#          the positive/negative split at harmonize), raw_phenotype_protein
#          (replaces PrimeKG's DisGeNET-sourced phenotype_protein edge).
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE  (recorded 2026-08-13)
# Source        : Human Phenotype Ontology (OBO format)
# PINNED (R3, 2026-11-08): DEMO_KG_PREP reads this file from `pinned_sources` (compute_pinned_sources);
# the URL above is where it was pulled from, recorded in the folder's MANIFEST.json.
# URL in use    : http://purl.obolibrary.org/obo/hp/hp.obo      <-- UNPINNED, serves latest
# Version used  : hp/releases/2026-06-23   (confirmed 2026-08-13)
# Verified      : 19,836 live terms == 19,836 rows in `hpo_terms`, zero null names.
# TO FREEZE     : swap the URL for the dated release (verified to work):
#                 http://purl.obolibrary.org/obo/hp/releases/2026-06-23/hp.obo
# ----------------------------------------------------------------------------

import io

import dataiku
import obonet
import pandas as pd

# Pinned by compute_pinned_sources (decision D9, R3 2026-11-08): this recipe reads the copy in
# the `pinned_sources` folder and never the URL, so a rebuild reproduces the same pull. The
# folder's MANIFEST.json records each file's URL, retrieval time, SHA-256 and release version.
PINNED = dataiku.Folder("pinned_sources")


def pinned(path):
    with PINNED.get_download_stream(path) as s:
        return s.read()

g = obonet.read_obo(io.StringIO(pinned("hpo/hp.obo").decode("utf-8")))

terms, hier = [], []
for node_id, data in g.nodes(data=True):
    if not node_id.startswith("HP:"):
        continue
    terms.append({"hpo_id": node_id, "name": data.get("name")})
    for p in data.get("is_a", []):
        if p.startswith("HP:"):
            hier.append({"parent_id": p, "child_id": node_id})

terms_df = pd.DataFrame(terms).dropna(subset=["hpo_id"]).drop_duplicates("hpo_id")
hier_df = pd.DataFrame(hier).drop_duplicates()

dataiku.Dataset("hpo_terms").write_with_schema(terms_df)
dataiku.Dataset("raw_phenotype_hierarchy").write_with_schema(hier_df)

# phenotype.hpoa -- disease-phenotype annotations (rare-disease scope: OMIM/ORPHA/DECIPHER)
hpoa = pd.read_csv(io.BytesIO(pinned("hpo/phenotype.hpoa")), sep="\t", comment="#", dtype=str)
hpoa = hpoa[hpoa.aspect == "P"].copy()
hpoa[["ontology", "ontology_id"]] = hpoa.database_id.str.split(":", n=1, expand=True)
raw_dp = (hpoa[["ontology", "ontology_id", "hpo_id", "qualifier"]]
          .fillna({"qualifier": ""}).drop_duplicates())
dataiku.Dataset("raw_disease_phenotype").write_with_schema(raw_dp)

# genes_to_phenotype.txt -- gene-phenotype (replaces DisGeNET-sourced phenotype_protein)
g2p = pd.read_csv(io.BytesIO(pinned("hpo/genes_to_phenotype.txt")), sep="\t", dtype=str)
g2p["entrez_id"] = pd.to_numeric(g2p.ncbi_gene_id, errors="coerce")
raw_pp = (g2p.dropna(subset=["entrez_id"])
          .assign(entrez_id=lambda d: d.entrez_id.astype("int64"))
          [["entrez_id", "hpo_id"]].drop_duplicates())
dataiku.Dataset("raw_phenotype_protein").write_with_schema(raw_pp)


