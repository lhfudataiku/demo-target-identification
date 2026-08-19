# Degree-matched z-score of gene-to-module PPI overlap (PAIR-LEVEL).
#
# Motivation (TARGET_PRIORITIZER §6e): raw `ppi_common_neighbors` is confounded with degree
# (Spearman +0.663) -- a hub overlaps every module by chance. This is the degree-matched
# control the 2026-07-08 decision log dropped ("the supervised model absorbs hubness");
# the feature audit falsified that assumption (4 collinear degree encodings; 6x detection
# gap Q1 6.8% vs Q5 40.8% among equally-true targets), so it is reinstated here.
#
# Null model: hypergeometric. For gene g (PPI degree d) and disease D whose module covers
# K of the N genes in the PPI network, the observed overlap X = |N(g) & module(D)| is
# compared against draws of d neighbours from N genes:
#     E[X]   = d*K/N
#     Var[X] = d * (K/N) * (1 - K/N) * (N - d)/(N - 1)
#     z      = (X - E[X]) / sqrt(Var[X])
# Positive z = more module contact than its connectivity alone would predict -- which is
# exactly the quantity that should rescue a sparsely-assayed receptor.
#
# Coverage is deliberately restricted to X > 0 so the null pattern MATCHES the existing
# `ppi_common_neighbors` column. Emitting rows where X == 0 would hand the model a new
# missingness channel, and missingness-as-signal is the leak family already documented
# in §6b/§6e -- do not "improve" this by densifying it.
import dataiku
import numpy as np
import pandas as pd
from scipy import sparse

# Dataset DEMO_KG_LS.graph_edges renamed to DEMO_KG_graph_edges_copy by liheng.fu@dataiku.com on 2026-08-18 09:38:18
# Dataset DEMO_KG_graph_edges_copy renamed to graph_edges by liheng.fu@dataiku.com on 2026-08-18 09:56:56
edges = dataiku.Dataset("graph_edges").get_dataframe(columns=["relation", "x_index", "y_index"])
# Dataset DEMO_KG_LS.graph_nodes renamed to DEMO_KG_graph_nodes_copy by liheng.fu@dataiku.com on 2026-08-18 09:38:35
# Dataset DEMO_KG_graph_nodes_copy renamed to graph_nodes by liheng.fu@dataiku.com on 2026-08-18 09:56:41
nodes = dataiku.Dataset("graph_nodes").get_dataframe(columns=["node_index", "node_type"])
genes = set(nodes.loc[nodes.node_type == "gene/protein", "node_index"])

ppi = edges.loc[edges.relation == "protein_protein", ["x_index", "y_index"]].to_numpy(dtype=np.int64)
gene_ids = np.unique(ppi.reshape(-1))
pos = pd.Series(np.arange(len(gene_ids), dtype=np.int64), index=gene_ids)
N = len(gene_ids)

rows = pos.loc[ppi[:, 0]].to_numpy()
cols = pos.loc[ppi[:, 1]].to_numpy()
A = sparse.coo_matrix((np.ones(len(rows), dtype=np.float64), (rows, cols)), shape=(N, N)).tocsr()
A.sum_duplicates()
A.data.fill(1.0)          # graph_edges is reverse-all'd; collapse to a simple 0/1 graph
degree = np.asarray(A.sum(axis=1)).ravel()

# module membership matrix M (genes x diseases), from disease_protein
dpe = edges.loc[edges.relation == "disease_protein"]
protein_at_x = dpe.x_index.isin(genes)
gd = pd.DataFrame({
    "gene_index": np.where(protein_at_x, dpe.x_index, dpe.y_index),
    "disease_index": np.where(protein_at_x, dpe.y_index, dpe.x_index),
}).drop_duplicates()
gd = gd[gd.gene_index.isin(set(gene_ids))]          # module genes present in the PPI network

disease_ids = np.unique(gd.disease_index.to_numpy())
dpos = pd.Series(np.arange(len(disease_ids), dtype=np.int64), index=disease_ids)
M = sparse.coo_matrix(
    (np.ones(len(gd), dtype=np.float64),
     (pos.loc[gd.gene_index].to_numpy(), dpos.loc[gd.disease_index].to_numpy())),
    shape=(N, len(disease_ids))).tocsr()
M.sum_duplicates()
M.data.fill(1.0)
K = np.asarray(M.sum(axis=0)).ravel()                # module size within the PPI network

# observed overlap for every (gene, disease): X = A @ M  -- sparse, only non-zeros survive
X = (A @ M).tocoo()
gi, di, obs = X.row, X.col, X.data

d = degree[gi]
k = K[di]
p = k / N
expected = d * p
var = d * p * (1.0 - p) * (N - d) / (N - 1)
z = np.where(var > 0, (obs - expected) / np.sqrt(np.where(var > 0, var, 1.0)), 0.0)

out = pd.DataFrame({
    "gene_index": gene_ids[gi],
    "disease_index": disease_ids[di],
    "ppi_common_neighbors_z": z,
    "ppi_cn_expected": expected,
})
print("ppi_cn_zscore rows:", out.shape)
print(out.ppi_common_neighbors_z.describe().to_string())
dataiku.Dataset("enriched_ppi_cn_zscore").write_with_schema(out)

