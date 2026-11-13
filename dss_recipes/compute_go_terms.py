# GO zone -- EXTRACT (Python: parse go-basic.obo + gene2go, native ids).
# Names resolved at assembly from go_terms. No cross-dataset joins here --
# gene2go already gives Entrez ids natively (same pattern as Reactome's NCBI2Reactome).
# Outputs: go_terms (vocab, with namespace), raw_go_protein, raw_go_hierarchy
#          (both combined across the 3 GO sub-ontologies, namespace column kept --
#          split into per-relation edges at harmonize, mirroring PrimeKG's 3 distinct
#          relation strings without needing 3 separate extract outputs).
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE  (recorded 2026-08-13)
# Source        : Gene Ontology, go-basic (OBO format)
# PINNED (R3, 2026-11-08): DEMO_KG_PREP reads this file from `pinned_sources` (compute_pinned_sources);
# the URL above is where it was pulled from, recorded in the folder's MANIFEST.json.
# URL in use    : http://purl.obolibrary.org/obo/go/go-basic.obo   <-- UNPINNED, serves latest
# Version used  : releases/2026-07-26   (confirmed 2026-08-13)
# Verified      : 38,092 live terms == 38,092 rows in `go_terms`, zero null names.
# TO FREEZE     : NO WORKING DATED ARCHIVE. The dated PURL resolves to an S3 key
#                 `<date>/ontology/go-basic.obo` that returns NoSuchKey, and
#                 release.geneontology.org/<date>/ontology/go-basic.obo 404s for every date
#                 tried. To freeze, DOWNLOAD go-basic.obo ONCE, upload it to the project's
#                 raw_files folder, and read from the folder instead of the URL.
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

NS_MAP = {"biological_process": "bioprocess", "molecular_function": "molfunc",
          "cellular_component": "cellcomp"}
CAT_MAP = {"Process": "bioprocess", "Function": "molfunc", "Component": "cellcomp"}
# gene2go's Qualifier holds the GO relation, prefixed with NOT for a negated annotation
# (e.g. "NOT enables"). Matches NOT as a whole word, separated by space or "|".
NOT_RE = r"(?:^|[\s|])NOT(?:$|[\s|])"

g = obonet.read_obo(io.StringIO(pinned("go/go-basic.obo").decode("utf-8")))

terms, hier = [], []
for node_id, data in g.nodes(data=True):
    if not node_id.startswith("GO:"):
        continue
    ns = NS_MAP.get(data.get("namespace"))
    if ns is None:
        continue
    terms.append({"go_id": node_id, "name": data.get("name"), "namespace": ns})
    for p in data.get("is_a", []):
        if p.startswith("GO:"):
            hier.append({"parent_id": p, "child_id": node_id, "namespace": ns})

terms_df = pd.DataFrame(terms).dropna(subset=["go_id"]).drop_duplicates("go_id")
hier_df = pd.DataFrame(hier).drop_duplicates()

dataiku.Dataset("go_terms").write_with_schema(terms_df)
dataiku.Dataset("raw_go_hierarchy").write_with_schema(hier_df)

# gene2go (NCBI, human taxon 9606 only)
g2g = pd.read_csv(io.BytesIO(pinned("go/gene2go.gz")), sep="\t", dtype=str, compression="gzip",
                  na_values=["-"])
g2g.columns = [c.lstrip("#").strip() for c in g2g.columns]
g2g = g2g[g2g.tax_id == "9606"].copy()
g2g["entrez_id"] = pd.to_numeric(g2g.GeneID, errors="coerce")
g2g = g2g.dropna(subset=["entrez_id"]).assign(entrez_id=lambda d: d.entrez_id.astype("int64"))
g2g["namespace"] = g2g.Category.map(CAT_MAP)
g2g = g2g.dropna(subset=["namespace"])

# Drop negated annotations. Before 2026-11 the Qualifier column was ignored, so "gene X does NOT
# enable Y" became an `enables` edge. Only the NOT rows go: a gene-term pair that also has a
# positive annotation keeps its edge through that row.
assert "Qualifier" in g2g.columns, "gene2go layout changed: no Qualifier column"
neg = g2g.Qualifier.fillna("").str.contains(NOT_RE, regex=True)
print("gene2go human annotations:", len(g2g), "| NOT annotations dropped:", int(neg.sum()),
      "| qualifiers:", g2g.Qualifier.fillna("<blank>").value_counts().to_dict())
g2g = g2g[~neg]

raw_protein = g2g[["entrez_id", "GO_ID", "namespace"]].rename(
    columns={"GO_ID": "go_id"}).drop_duplicates()
dataiku.Dataset("raw_go_protein").write_with_schema(raw_protein)


