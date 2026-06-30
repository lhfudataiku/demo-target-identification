# Dataiku Python recipe — produces PrimeKG's ppi/protein_protein.csv
#
# Source: Menche et al. 2015, "Uncovering Disease-Disease Relationships Through
#         The Human Interactome" (Science) — supplementary DataS1_interactome.tsv.
#         This is the PPI base PrimeKG used. Columns 1 & 2 are NCBI Entrez Gene IDs.
#
# INPUT  folder:  ppi_raw   (a DSS managed folder containing DataS1_interactome.tsv)
# OUTPUT dataset: protein_protein   (proteinA_entrezid, proteinB_entrezid)
#
# The file has a ~23-line "#" comment header (including the column-name line, which
# also starts with "#"), so we strip all "#" lines and supply names explicitly.
# build_graph.ipynb only consumes the two entrez-id columns; data_sources is kept
# for optional edge-evidence filtering.

import dataiku
import pandas as pd

folder = dataiku.Folder("raw_files")
path = folder.get_path() + "/DataS1_interactome.tsv"

df = pd.read_csv(
    path,
    sep="\t",
    comment="#",
    header=None,
    names=["proteinA_entrezid", "proteinB_entrezid", "data_sources"],
    dtype={"proteinA_entrezid": "Int64", "proteinB_entrezid": "Int64"},
)

# build_graph.ipynb requires exactly these two columns (it .dropna()s the frame).
out = df[["proteinA_entrezid", "proteinB_entrezid"]].dropna().drop_duplicates()

dataiku.Dataset("protein_protein").write_with_schema(out)
