# HGNC gene identity, preloaded for the candidate header (webapp redesign, decision D16).
# Zero-input recipe: one DATED HGNC complete-set file -> hgnc_identity dataset.
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE
# Source   : HGNC monthly archive of the complete set, on HGNC's public download bucket.
#            A dated file never changes, so a rebuild reproduces the same rows -- unlike
#            compute_gene_names, which runs a live query.
# Snapshot : SNAPSHOT below. To move to a newer month, change it and rebuild THIS recipe
#            only; the header names the file it came from.
# Scope    : nothing in the graph build reads hgnc_identity. gene_names and
#            compute_gene_names feed compute_kg_edges and the Part 2 split key, so they are
#            deliberately not touched or reused here.
# ----------------------------------------------------------------------------
# Columns are read BY NAME from the file's header, never by position, so HGNC adding or
# reordering a column cannot shift a field silently.

import hashlib
import io

import dataiku
import pandas as pd
import requests

SNAPSHOT = "2026-10-06"
FILE = f"hgnc_complete_set_{SNAPSHOT}.txt"
URL = f"https://storage.googleapis.com/public-download-files/hgnc/archive/archive/monthly/tsv/{FILE}"

# What the candidate header shows, plus what joins it to the graph (entrez_id).
FIELDS = [
    "hgnc_id", "symbol", "name", "locus_type", "location", "alias_symbol", "prev_symbol",
    "gene_group", "date_modified", "entrez_id", "ensembl_gene_id", "uniprot_ids",
]

r = requests.get(URL, timeout=300)
r.raise_for_status()
sha256 = hashlib.sha256(r.content).hexdigest()

raw = pd.read_csv(io.StringIO(r.content.decode("utf-8")), sep="\t", dtype=str,
                  keep_default_na=False, usecols=FIELDS + ["status"])
missing = [c for c in FIELDS if c not in raw.columns]
if missing:
    raise ValueError(f"{FILE} lacks expected columns: {missing}")

df = raw[raw["status"] == "Approved"].drop(columns="status")
# The join key. Kept as a STRING: graph_nodes.node_id is a string, and a numeric
# column here would need a cast on every join.
df["entrez_id"] = df["entrez_id"].str.strip()
df = df[df["entrez_id"].str.fullmatch(r"\d+")]
# One row per NCBI Gene ID. A few IDs carry two approved HGNC records (2026-10-06: two,
# each a non-coding RNA paired with a neighbour, neither a graph gene). Such an ID is not
# an identity, so ALL its rows are dropped, never one picked; the log names them.
dup = df["entrez_id"].duplicated(keep=False)
if dup.any():
    print(f"dropped {dup.sum()} rows for {df.loc[dup, 'entrez_id'].nunique()} ambiguous NCBI Gene IDs:",
          sorted(df.loc[dup, "entrez_id"].unique()))
df = df[~dup]
print(f"{FILE}: {len(raw)} records, {len(df)} approved with a unique NCBI Gene ID")

# HGNC ships list fields pipe-separated, sometimes quoted; normalise to plain "a|b|c".
for c in ("alias_symbol", "prev_symbol", "gene_group", "uniprot_ids"):
    df[c] = df[c].str.strip('"').str.replace('"', "", regex=False)
# Empty strings become nulls, so "no alias" and "alias ''" cannot differ.
df = df.replace("", None)

df["source_file"] = FILE
df["source_sha256"] = sha256

dataiku.Dataset("hgnc_identity").write_with_schema(df[FIELDS + ["source_file", "source_sha256"]])

