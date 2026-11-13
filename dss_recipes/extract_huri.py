# HuRI/HI-union zone -- EXTRACT (Python: parse HI-union.tsv, ground ENSG->Entrez via
# NCBI gene2ensembl -- the same trusted source family as gene2go, used elsewhere in
# this project). Systematic Y2H screen (CCSB/Vidal lab), not literature-curated --
# the point of adding it is that it does NOT carry Menche/BioGRID/STRING's hub bias.
# Output raw_huri_ppi (gene_id_1, gene_id_2, both Entrez). No comparison to Menche here
# -- that's a separate decision-support step, not part of the extract.
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE  (recorded 2026-08-13)
# Source        : HuRI / HI-union interactome + NCBI gene2ensembl id mapping
# PINNED (R3, 2026-11-08): DEMO_KG_PREP reads this file from `pinned_sources` (compute_pinned_sources);
# the URL above is where it was pulled from, recorded in the folder's MANIFEST.json.
# URLs in use   : http://interactome-atlas.org/data/HI-union.tsv       <-- UNVERSIONED
#                 https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2ensembl.gz  <-- CURRENT ONLY
# Version used  : HuRI HI-union -- the URL carries no version at all.
#                 gene2ensembl.gz Last-Modified 2026-08-13 11:49 GMT, 279,498,104 bytes.
#                 *** THIS FILE ALREADY DRIFTED: NCBI rewrites it continuously, so the copy
#                 *** that built the current graph (early Aug 2026) NO LONGER EXISTS.
# TO FREEZE     : both must be SNAPSHOTTED to raw_files. NCBI keeps no dated archive of
#                 gene2ensembl.gz, and interactome-atlas serves only the latest HI-union.
#                 This is the single least reproducible source in the flow.
# ----------------------------------------------------------------------------

import io

import dataiku
import pandas as pd

# Pinned by compute_pinned_sources (decision D9, R3 2026-11-08): this recipe reads the copy in
# the `pinned_sources` folder and never the URL, so a rebuild reproduces the same pull. The
# folder's MANIFEST.json records each file's URL, retrieval time, SHA-256 and release version.
PINNED = dataiku.Folder("pinned_sources")


def pinned(path):
    with PINNED.get_download_stream(path) as s:
        return s.read()

# ENSG -> Entrez crosswalk (human only)
g2e = pd.read_csv(io.BytesIO(pinned("ncbi/gene2ensembl.gz")), sep="\t", dtype=str, compression="gzip")
g2e.columns = [c.lstrip("#").strip() for c in g2e.columns]
g2e = g2e[g2e.tax_id == "9606"][["GeneID", "Ensembl_gene_identifier"]].drop_duplicates()
ensg_to_entrez = dict(zip(g2e.Ensembl_gene_identifier, g2e.GeneID))

# HI-union pairs (ENSG, no header)
pairs = pd.read_csv(io.BytesIO(pinned("huri/HI-union.tsv")), sep="\t", header=None,
                    names=["ensg_1", "ensg_2"], dtype=str)

pairs["gene_id_1"] = pairs.ensg_1.map(ensg_to_entrez)
pairs["gene_id_2"] = pairs.ensg_2.map(ensg_to_entrez)
out = pairs.dropna(subset=["gene_id_1", "gene_id_2"])[["gene_id_1", "gene_id_2"]].drop_duplicates()

dataiku.Dataset("raw_huri_ppi").write_with_schema(out)


