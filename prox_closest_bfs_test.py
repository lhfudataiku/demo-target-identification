import dataiku
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.csgraph import dijkstra


# Set to None for the complete computation after validation on a small sample.
TEST_DISEASES = 5
MIN_SEEDS = 20
MAX_HOPS = 3
SOURCE_CHUNK_SIZE = 64


def make_ppi_adjacency(ppi_edges):
    """Create a simple, undirected sparse PPI graph."""
    protein_ids = np.unique(ppi_edges.reshape(-1))
    position = pd.Series(np.arange(len(protein_ids), dtype=np.int64), index=protein_ids)
    source = position.loc[ppi_edges[:, 0]].to_numpy()
    target = position.loc[ppi_edges[:, 1]].to_numpy()

    adjacency = sparse.coo_matrix(
        (np.ones(len(source), dtype=np.uint8), (source, target)),
        shape=(len(protein_ids), len(protein_ids)),
    ).tocsr()
    adjacency.sum_duplicates()
    adjacency.data.fill(1)
    return protein_ids, position, adjacency


edges = dataiku.Dataset("graph_edges").get_dataframe(
    columns=["relation", "x_index", "y_index"]
)
ppi_edges = edges.loc[
    edges.relation == "protein_protein", ["x_index", "y_index"]
].to_numpy(dtype=np.int64)
protein_ids, protein_position, ppi = make_ppi_adjacency(ppi_edges)

node_types = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_type"]
)
protein_nodes = set(
    node_types.loc[node_types.node_type == "gene/protein", "node_index"]
)
disease_protein_edges = edges.loc[edges.relation == "disease_protein"]
protein_at_x = disease_protein_edges.x_index.isin(protein_nodes)
gene_disease = pd.DataFrame(
    {
        "gene_index": np.where(
            protein_at_x, disease_protein_edges.x_index, disease_protein_edges.y_index
        ),
        "disease_index": np.where(
            protein_at_x, disease_protein_edges.y_index, disease_protein_edges.x_index
        ),
    }
).drop_duplicates()
modules = {
    disease: [gene for gene in genes if gene in protein_position.index]
    for disease, genes in gene_disease.groupby("disease_index")["gene_index"]
}
eligible_modules = [
    (disease, genes) for disease, genes in modules.items() if len(genes) >= MIN_SEEDS
]
if TEST_DISEASES is not None:
    eligible_modules = eligible_modules[:TEST_DISEASES]


def closest_distances(module_positions):
    """Return min distance to another module gene, up to MAX_HOPS.

    A chunked multi-source Dijkstra call avoids Cypher's all-path
    materialization. Setting each source's own distance to infinity reproduces
    the original `g.node_index <> m.node_index` condition.
    """
    nearest = np.full(len(protein_ids), np.inf, dtype=np.float64)
    for source_chunk in np.array_split(
        module_positions,
        max(1, int(np.ceil(len(module_positions) / SOURCE_CHUNK_SIZE))),
    ):
        distances = dijkstra(
            ppi,
            directed=False,
            indices=source_chunk,
            unweighted=True,
            limit=MAX_HOPS,
        )
        if distances.ndim == 1:
            distances = distances[np.newaxis, :]
        distances[np.arange(len(source_chunk)), source_chunk] = np.inf
        nearest = np.minimum(nearest, distances.min(axis=0))
    return nearest


result_frames = []
for disease, module_genes in eligible_modules:
    module_positions = protein_position.loc[module_genes].to_numpy()
    distances = closest_distances(module_positions)
    reachable = np.flatnonzero(np.isfinite(distances))
    result_frames.append(
        pd.DataFrame(
            {
                "gene_index": protein_ids[reachable],
                "disease_index": disease,
                "prox_closest": distances[reachable].astype(np.int64),
            }
        )
    )

out = pd.concat(result_frames, ignore_index=True) if result_frames else pd.DataFrame(
    columns=["gene_index", "disease_index", "prox_closest"]
)
print("prox rows:", out.shape, "| diseases:", out.disease_index.nunique())
dataiku.Dataset("enriched_prox_closest_bfs_test").write_with_schema(out)
