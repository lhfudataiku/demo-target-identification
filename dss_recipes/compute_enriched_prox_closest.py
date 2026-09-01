# THRESHOLD LOWERED 20 -> 5 on 2026-08-20 (Phase 1), and CAPPED to the pool population. The old value was a bare literal
# with no recorded justification; it gated 7 of the 12 champion features across 10 recipes,
# leaving 43 diseases with NO disease-specific signal at all. This recipe is NOT a pool route,
# so lowering it fills NULLs without moving the candidate pool. See docs/FEATURE_AUDIT.md.
import dataiku
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.csgraph import dijkstra


# Set to None for the complete computation after validation on a small sample.
TEST_DISEASES = None
MIN_SEEDS = 5
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


# Dataset DEMO_KG_LS.graph_edges renamed to DEMO_KG_graph_edges_copy by liheng.fu@dataiku.com on 2026-08-18 09:38:18
# Dataset DEMO_KG_graph_edges_copy renamed to graph_edges by liheng.fu@dataiku.com on 2026-08-18 09:56:56
edges = dataiku.Dataset("graph_edges").get_dataframe(
    columns=["relation", "x_index", "y_index"]
)
ppi_edges = edges.loc[
    edges.relation == "protein_protein", ["x_index", "y_index"]
].to_numpy(dtype=np.int64)
protein_ids, protein_position, ppi = make_ppi_adjacency(ppi_edges)

# Dataset DEMO_KG_LS.graph_nodes renamed to DEMO_KG_graph_nodes_copy by liheng.fu@dataiku.com on 2026-08-18 09:38:35
# Dataset DEMO_KG_graph_nodes_copy renamed to graph_nodes by liheng.fu@dataiku.com on 2026-08-18 09:56:41
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
# POOL_MIN caps the work to the population the candidate pool actually contains. The pool admits a
# disease only if it has >= 20 disease_protein seeds (the Cypher routes dwpc_GGD/GPGD/GCD, left
# untouched), so computing prox for anything below that produced rows the has-path-evidence filter
# throws away — 32M rows on the first attempt, which is what shut the Spark context down.
# MIN_SEEDS still applies, on the PPI-MAPPED count, which is a different and stricter denominator:
# 42 pool diseases have >= 20 seeds but < 20 of them mapped into the interactome, and those are
# exactly the diseases this change exists to rescue from an all-NULL prox_closest.
POOL_MIN = 20
full_module = gene_disease.groupby("disease_index")["gene_index"].nunique()
eligible_modules = [
    (disease, genes) for disease, genes in modules.items()
    if len(genes) >= MIN_SEEDS and int(full_module.get(disease, 0)) >= POOL_MIN
]
print(f"eligible diseases: {len(eligible_modules)} "
      f"(PPI-mapped seeds >= {MIN_SEEDS} AND total seeds >= {POOL_MIN})")
if TEST_DISEASES is not None:
    eligible_modules = eligible_modules[:TEST_DISEASES]


def closest_distances(module_positions):
    """Return FOUR proximity statistics per gene, all capped at MAX_HOPS.

    PHASE 2 (2026-08-20): the minimum alone saturates. Measured, 73.9% of pairs sit at hop 1 once a
    module exceeds 300 genes, and single-feature AUC falls from 0.646 (modules of 20-30) to 0.567
    (>300), Spearman -0.328 against module size. The minimum is the most saturating of the proximity
    family (Guney et al. 2016 define several); a graded statistic keeps resolving where it floors out.

      prox_closest   min distance                      -- unchanged, the existing feature
      prox_mean      mean distance over REACHED seeds  -- Guney's d_shortest
      prox_kernel    sum of exp(-d) over reached seeds -- weights near seeds, never saturates
      prox_n_reach   count of module genes within MAX_HOPS

    prox_kernel is the one expected to fix the dense regime: two genes both touching the module at
    distance 1 are identical under the minimum, but distinguishable by HOW MUCH of the module is near.

    Each source's own distance is set to infinity, reproducing `g.node_index <> m.node_index`.
    """
    n = len(protein_ids)
    nearest = np.full(n, np.inf, dtype=np.float64)
    dsum = np.zeros(n, dtype=np.float64)
    dcount = np.zeros(n, dtype=np.float64)
    kernel = np.zeros(n, dtype=np.float64)
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
        finite = np.isfinite(distances)
        dsum += np.where(finite, distances, 0.0).sum(axis=0)
        dcount += finite.sum(axis=0)
        kernel += np.where(finite, np.exp(-distances, where=finite,
                                          out=np.zeros_like(distances)), 0.0).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_d = np.where(dcount > 0, dsum / np.maximum(dcount, 1), np.inf)
    return nearest, mean_d, kernel, dcount


result_frames = []
for disease, module_genes in eligible_modules:
    module_positions = protein_position.loc[module_genes].to_numpy()
    distances, mean_d, kernel, n_reach = closest_distances(module_positions)
    reachable = np.flatnonzero(np.isfinite(distances))
    result_frames.append(
        pd.DataFrame(
            {
                "gene_index": protein_ids[reachable],
                "disease_index": disease,
                "prox_closest": distances[reachable].astype(np.int64),
                "prox_mean": mean_d[reachable],
                "prox_kernel": kernel[reachable],
                "prox_n_reach": n_reach[reachable].astype(np.int64),
            }
        )
    )

out = pd.concat(result_frames, ignore_index=True) if result_frames else pd.DataFrame(
    columns=["gene_index", "disease_index", "prox_closest",
             "prox_mean", "prox_kernel", "prox_n_reach"]
)
# Dataset enriched_prox_closest_bfs_test renamed to enriched_prox_closest by liheng.fu@dataiku.com on 2026-08-13 13:30:42
print("prox rows:", out.shape, "| diseases:", out.disease_index.nunique())
dataiku.Dataset("enriched_prox_closest").write_with_schema(out)



