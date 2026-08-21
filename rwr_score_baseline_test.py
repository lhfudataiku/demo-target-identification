import dataiku
import numpy as np
import pandas as pd
import networkx as nx


ALPHA = 0.85
MIN_SEEDS = 20
KFOLD = 5
TEST_DISEASES = 5
np.random.seed(0)

edges = dataiku.Dataset("graph_edges").get_dataframe(
    columns=["relation", "x_index", "y_index"]
)
ppi = edges.loc[edges.relation == "protein_protein", ["x_index", "y_index"]].to_numpy()
graph = nx.Graph()
graph.add_edges_from(map(tuple, ppi))
n_nodes = graph.number_of_nodes()
floor = 1.0 / n_nodes

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
    disease: [gene for gene in group if gene in graph]
    for disease, group in gene_disease.groupby("d")["g"]
}


def rwr(seeds):
    personalization = {gene: 1.0 / len(seeds) for gene in seeds}
    return nx.pagerank(
        graph,
        alpha=ALPHA,
        personalization=personalization,
        max_iter=300,
        tol=1e-9,
    )


rows = []
eligible_diseases = 0
for disease, seeds in modules.items():
    if len(seeds) < MIN_SEEDS:
        continue
    if eligible_diseases == TEST_DISEASES:
        break
    eligible_diseases += 1

    seed_set = set(seeds)
    full = rwr(seeds)
    rows.extend(
        (gene, disease, score)
        for gene, score in full.items()
        if gene not in seed_set and score > floor
    )
    for held in np.array_split(np.random.permutation(seeds), KFOLD):
        held_set = set(int(gene) for gene in held)
        held_out_scores = rwr([gene for gene in seeds if gene not in held_set])
        rows.extend((gene, disease, held_out_scores.get(gene, 0.0)) for gene in held_set)

out = pd.DataFrame(rows, columns=["gene_index", "disease_index", "rwr_score"])
print("rwr rows:", out.shape, "| diseases:", out.disease_index.nunique())
dataiku.Dataset("rwr_score_baseline_test").write_with_schema(out)
