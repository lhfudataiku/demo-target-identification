import dataiku
import numpy as np
import pandas as pd
from scipy import sparse
from concurrent.futures import ThreadPoolExecutor


ALPHA = 0.85
MIN_SEEDS = 20
KFOLD = 5
MAX_ITER = 300
TOL = 1e-9
MAX_WORKERS = 4
# TEST_DISEASES = None
np.random.seed(0)


def make_transition(ppi):
    """Build the simple, undirected row-stochastic PPI transition matrix once."""
    node_ids = np.unique(ppi.reshape(-1))
    node_to_pos = pd.Series(np.arange(len(node_ids), dtype=np.int64), index=node_ids)

    src = node_to_pos.loc[ppi[:, 0]].to_numpy()
    dst = node_to_pos.loc[ppi[:, 1]].to_numpy()
    # The source data stores each PPI edge twice. Sparse accumulation therefore
    # needs to be collapsed back to a simple graph, as nx.Graph does.
    row = np.concatenate((src, dst))
    col = np.concatenate((dst, src))
    adjacency = sparse.coo_matrix(
        (np.ones(len(row), dtype=np.float64), (row, col)),
        shape=(len(node_ids), len(node_ids)),
    ).tocsr()
    adjacency.sum_duplicates()
    adjacency.data.fill(1.0)

    degrees = np.asarray(adjacency.sum(axis=1)).ravel()
    transition = sparse.diags(1.0 / degrees) @ adjacency
    return node_ids, node_to_pos, transition.tocsr()


def batched_rwr(transition, restarts):
    """Power-iterate all restart distributions for one disease together.

    NetworkX runs these walks one-by-one. Keeping the PPI matrix fixed and
    multiplying all six dense vectors together avoids rebuilding sparse graph
    structures for every PageRank call while preserving the same recurrence.
    """
    n_nodes = transition.shape[0]
    scores = np.full(restarts.shape, 1.0 / n_nodes, dtype=np.float64)
    for _ in range(MAX_ITER):
        updated = ALPHA * (transition.T @ scores.T).T + (1.0 - ALPHA) * restarts
        if np.abs(updated - scores).sum(axis=1).max() < n_nodes * TOL:
            return updated
        scores = updated
    raise RuntimeError(f"PageRank failed to converge within {MAX_ITER} iterations")


# Dataset DEMO_KG_LS.graph_edges renamed to DEMO_KG_graph_edges_copy by liheng.fu@dataiku.com on 2026-08-18 09:38:18
# Dataset DEMO_KG_graph_edges_copy renamed to graph_edges by liheng.fu@dataiku.com on 2026-08-18 09:56:56
edges = dataiku.Dataset("graph_edges").get_dataframe(
    columns=["relation", "x_index", "y_index"]
)
ppi = edges.loc[
    edges.relation == "protein_protein", ["x_index", "y_index"]
].to_numpy(dtype=np.int64)
node_ids, node_to_pos, transition = make_transition(ppi)
n_nodes = len(node_ids)
floor = 1.0 / n_nodes

# Dataset DEMO_KG_LS.graph_nodes renamed to DEMO_KG_graph_nodes_copy by liheng.fu@dataiku.com on 2026-08-18 09:38:35
# Dataset DEMO_KG_graph_nodes_copy renamed to graph_nodes by liheng.fu@dataiku.com on 2026-08-18 09:56:41
node_types = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_type"]
)
genes = set(node_types.loc[node_types.node_type == "gene/protein", "node_index"])
disease_proteins = edges.loc[edges.relation == "disease_protein"]
is_gene_at_x = disease_proteins.x_index.isin(genes)
gene_disease = pd.DataFrame(
    {
        "g": np.where(is_gene_at_x, disease_proteins.x_index, disease_proteins.y_index),
        "d": np.where(is_gene_at_x, disease_proteins.y_index, disease_proteins.x_index),
    }
).drop_duplicates()
modules = {
    disease: [gene for gene in group if gene in node_to_pos.index]
    for disease, group in gene_disease.groupby("d")["g"]
}

def score_disease(task):
    """Score one disease independently; the sparse PPI matrix is read-only."""
    disease, seeds, held_folds = task
    seed_positions = node_to_pos.loc[seeds].to_numpy()
    restart = np.zeros((KFOLD + 1, n_nodes), dtype=np.float64)
    restart[0, seed_positions] = 1.0 / len(seed_positions)

    held_positions = []
    for fold_number, held in enumerate(held_folds):
        held_positions_for_fold = node_to_pos.loc[held].to_numpy()
        train_positions = seed_positions[
            ~np.isin(seed_positions, held_positions_for_fold, assume_unique=True)
        ]
        restart[fold_number + 1, train_positions] = 1.0 / len(train_positions)
        held_positions.append(held_positions_for_fold)

    scores = batched_rwr(transition, restart)

    is_seed = np.zeros(n_nodes, dtype=bool)
    is_seed[seed_positions] = True
    candidate_positions = np.flatnonzero((scores[0] > floor) & ~is_seed)
    disease_rows = [
        (int(node_ids[position]), int(disease), float(scores[0, position]))
        for position in candidate_positions
    ]

    for fold_number, positions in enumerate(held_positions):
        disease_rows.extend(
            (int(node_ids[position]), int(disease), float(scores[fold_number + 1, position]))
            for position in positions
        )
    return disease_rows


# Generate folds before parallel work so that the seeded random split remains
# identical to the original sequential NetworkX recipe.
tasks = []
for disease, seeds in modules.items():
    if len(seeds) >= MIN_SEEDS:
        held_folds = [
            np.asarray(fold, dtype=np.int64)
            for fold in np.array_split(np.random.permutation(seeds), KFOLD)
        ]
        tasks.append((disease, seeds, held_folds))
# tasks = tasks[:TEST_DISEASES]

rows = []
with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(tasks))) as executor:
    for disease_rows in executor.map(score_disease, tasks):
        rows.extend(disease_rows)

out = pd.DataFrame(rows, columns=["gene_index", "disease_index", "rwr_score"])
print(
    "rwr rows:", out.shape,
    "| diseases:", out.disease_index.nunique(),
    "| eligible diseases:", len(tasks),
)
dataiku.Dataset("enriched_rwr_score_1").write_with_schema(out)

