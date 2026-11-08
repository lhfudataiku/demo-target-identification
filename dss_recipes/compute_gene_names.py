# Gene/protein identity table from HGNC (genenames.org custom download).
# Zero-input recipe: downloads + parses → gene_names dataset.
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE  (recorded 2026-08-13)
# Source        : HGNC custom download (live CGI query, not a versioned file)
# PINNED (R3, 2026-11-08): DEMO_KG_PREP reads this file from `pinned_sources` (compute_pinned_sources);
# the URL above is where it was pulled from, recorded in the folder's MANIFEST.json.
# URL in use    : https://www.genenames.org/cgi-bin/download/custom?...   <-- LIVE QUERY
# Retrieved     : 2026-08-13 (verified HTTP 200, 3,152,612 bytes) -> 44,406 rows in `gene_names`
# TO FREEZE     : HGNC publishes no dated archive for this endpoint. Download the response
#                 ONCE, upload to raw_files, and read from the folder. Note the column order
#                 is positional per the `col=` parameters -- if you re-issue the query with a
#                 different col list, the downstream positional parsing breaks silently.
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

URL = (
    "https://www.genenames.org/cgi-bin/download/custom"
    "?col=gd_app_sym&col=gd_app_name&col=gd_pub_eg_id&col=md_eg_id"
    "&col=md_prot_id&col=md_mim_id&col=gd_pub_refseq_ids"
    "&status=Approved&hgnc_dbtag=on&order_by=gd_app_sym_sort"
    "&format=text&submit=submit"
)

# URL above documents the query; the response is read from the pinned copy.
df = pd.read_csv(io.BytesIO(pinned("hgnc/gene_names_custom.tsv")), sep="\t", dtype=str)
# Columns are positional per the URL's col= order.
df.columns = [
    "symbol", "name", "entrez_supplied", "entrez_ncbi",
    "uniprot_id", "omim_id", "refseq_ids",
][: len(df.columns)]

# Prefer the curated NCBI Entrez id, fall back to the supplied one.
df["entrez_id"] = pd.to_numeric(
    df["entrez_ncbi"].fillna(df["entrez_supplied"]), errors="coerce"
)
out = (
    df.dropna(subset=["entrez_id"])
      .assign(entrez_id=lambda d: d["entrez_id"].astype("int64"))
      [["symbol", "name", "entrez_id", "uniprot_id", "omim_id", "refseq_ids"]]
      .drop_duplicates()
)

dataiku.Dataset("gene_names").write_with_schema(out)


