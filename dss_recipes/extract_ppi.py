# PPI zone — EXTRACT (Python: load + parse only, native ids).
# Grounding (Entrez→symbol) is done downstream in a visual Join recipe.
# Input:  folder raw_files (DataS1_interactome.tsv)
# Output: raw_ppi (entrez_a, entrez_b)  [ids as strings]
import dataiku
import pandas as pd

folder = dataiku.Folder("raw_files")
path = folder.get_path() + "/DataS1_interactome.tsv"

df = pd.read_csv(
    path, sep="\t", comment="#", header=None,
    names=["proteinA_entrezid", "proteinB_entrezid", "data_sources"],
    dtype={"proteinA_entrezid": "Int64", "proteinB_entrezid": "Int64"},
).dropna(subset=["proteinA_entrezid", "proteinB_entrezid"])

out = pd.DataFrame({
    "entrez_a": df.proteinA_entrezid.astype("int64"),   # bigint — matches gene_names.entrez_id for the join
    "entrez_b": df.proteinB_entrezid.astype("int64"),
}).drop_duplicates()

dataiku.Dataset("raw_ppi").write_with_schema(out)
