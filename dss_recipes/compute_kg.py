# Assembly zone — the graph-algorithm core (Python).
# Stacks per-source *_edges (8-col, name-free), attaches node names from the vocab
# tables, applies PrimeKG harmonization (clean, reverse-all, disease grouping, giant
# component), derives emergent nodes + node_index. Outputs PrimeKG-exact primekg /
# primekg_nodes / primekg_edges.
import dataiku
import networkx as nx
import pandas as pd

EDGE_DATASETS = ["ppi_edges", "mondo_edges", "gene_disease_edges",
                 "reactome_gp_edges", "reactome_pp_edges",
                 "drug_protein_edges", "drug_disease_edges"]
EDGE_COLS = ["x_id", "x_type", "x_source", "y_id", "y_type", "y_source",
             "relation", "display_relation"]


def clean(df):
    df = df[EDGE_COLS].dropna().drop_duplicates()
    return df[~((df.x_id == df.y_id) & (df.x_type == df.y_type) & (df.x_source == df.y_source))]


# ---- stack per-source edges ------------------------------------------------
kg = pd.concat([clean(dataiku.Dataset(d).get_dataframe().astype(str)) for d in EDGE_DATASETS],
               ignore_index=True).drop_duplicates()

# ---- reverse ALL edges (undirected) ----------------------------------------
rev = kg.rename(columns={"x_id": "y_id", "x_type": "y_type", "x_source": "y_source",
                         "y_id": "x_id", "y_type": "x_type", "y_source": "x_source"})
kg = pd.concat([kg, rev], ignore_index=True).drop_duplicates()
kg = kg[~((kg.x_id == kg.y_id) & (kg.x_type == kg.y_type) & (kg.x_source == kg.y_source))]

# ---- node-name lookup by (type, id) from the vocab tables ------------------
gn = dataiku.Dataset("gene_names").get_dataframe()
mt = dataiku.Dataset("mondo_terms").get_dataframe()
rt = dataiku.Dataset("reactome_terms").get_dataframe()
dv = dataiku.Dataset("drug_vocab").get_dataframe()
name_by_key = {}
name_by_key.update({("gene/protein", str(int(e))): s for e, s in zip(gn.entrez_id, gn.symbol)})
name_by_key.update({("disease", str(m)): n for m, n in zip(mt.mondo_id.astype(str), mt.name)})
name_by_key.update({("pathway", str(p)): n for p, n in zip(rt.pathway_id, rt.name)})
name_by_key.update({("drug", str(d)): n for d, n in zip(dv.drugbank_id, dv.drug_name)})

kg["x_name"] = [name_by_key.get((t, i)) for t, i in zip(kg.x_type, kg.x_id)]
kg["y_name"] = [name_by_key.get((t, i)) for t, i in zip(kg.y_type, kg.y_id)]
kg = kg.dropna(subset=["x_name", "y_name"])  # grounding-drop: endpoints must resolve to a node

# ---- disease grouping (PrimeKG published map) ------------------------------
gmap = dataiku.Dataset("disease_group_map").get_dataframe()
g_id = dict(zip(gmap.node_id.astype(str), gmap.group_id_bert.astype(str)))
g_name = dict(zip(gmap.node_id.astype(str), gmap.group_name_bert))
for s in ("x", "y"):
    m = (kg[s + "_type"] == "disease") & (kg[s + "_source"] == "MONDO") & (kg[s + "_id"].isin(g_id))
    kg.loc[m, s + "_name"] = kg.loc[m, s + "_id"].map(g_name)
    kg.loc[m, s + "_source"] = "MONDO_grouped"
    kg.loc[m, s + "_id"] = kg.loc[m, s + "_id"].map(g_id)
kg = kg.drop_duplicates()
kg = kg[~((kg.x_id == kg.y_id) & (kg.x_type == kg.y_type) & (kg.x_source == kg.y_source) & (kg.x_name == kg.y_name))]

# ---- giant connected component ---------------------------------------------
kg["xk"] = list(zip(kg.x_id, kg.x_type, kg.x_name, kg.x_source))
kg["yk"] = list(zip(kg.y_id, kg.y_type, kg.y_name, kg.y_source))
G = nx.Graph()
G.add_edges_from(zip(kg.xk, kg.yk))
giant = set(max(nx.connected_components(G), key=len))
kg = kg[kg.xk.isin(giant) & kg.yk.isin(giant)].copy()

# ---- emergent nodes + node_index -------------------------------------------
nodes = pd.concat([
    kg[["x_id", "x_type", "x_name", "x_source"]].rename(columns={
        "x_id": "node_id", "x_type": "node_type", "x_name": "node_name", "x_source": "node_source"}),
    kg[["y_id", "y_type", "y_name", "y_source"]].rename(columns={
        "y_id": "node_id", "y_type": "node_type", "y_name": "node_name", "y_source": "node_source"}),
]).drop_duplicates().reset_index(drop=True).reset_index().rename(columns={"index": "node_index"})

xi = nodes.rename(columns={"node_index": "x_index", "node_id": "x_id",
                           "node_type": "x_type", "node_name": "x_name", "node_source": "x_source"})
yi = nodes.rename(columns={"node_index": "y_index", "node_id": "y_id",
                           "node_type": "y_type", "node_name": "y_name", "node_source": "y_source"})
kg = kg.merge(xi, on=["x_id", "x_type", "x_name", "x_source"], how="left") \
       .merge(yi, on=["y_id", "y_type", "y_name", "y_source"], how="left")

dataiku.Dataset("primekg_nodes").write_with_schema(
    nodes[["node_index", "node_id", "node_type", "node_name", "node_source"]])
dataiku.Dataset("primekg").write_with_schema(
    kg[["relation", "display_relation", "x_index", "x_id", "x_type", "x_name", "x_source",
        "y_index", "y_id", "y_type", "y_name", "y_source"]])
dataiku.Dataset("primekg_edges").write_with_schema(
    kg[["relation", "display_relation", "x_index", "y_index"]].drop_duplicates())
