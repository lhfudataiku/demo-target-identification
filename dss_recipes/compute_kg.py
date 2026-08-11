# Assembly zone — the graph-algorithm core (Python).
# Stacks per-source *_edges (8-col, name-free), attaches node names from the vocab
# tables, applies PrimeKG harmonization (clean, reverse-all, disease grouping, giant
# component), derives emergent nodes + node_index. Outputs PrimeKG-exact kg /
# graph_nodes / graph_edges.
import dataiku
import networkx as nx
import pandas as pd

EDGE_DATASETS = ["ppi_edges", "mondo_edges", "gene_disease_edges",
                 "reactome_gp_edges", "reactome_pp_edges",
                 "drug_protein_edges", "drug_disease_edges",
                 # Task 10 additions (2026-08-06): GO+gene2go, HPO (+HP<->MONDO
                 # reclassification already applied upstream -- see PRIMEKG_MAPPING.md §4).
                 "go_protein_edges", "go_hierarchy_edges",
                 "phenotype_hierarchy_edges", "phenotype_protein_edges_distinct",
                 "disease_phenotype_edges_distinct"]
EDGE_COLS = ["x_id", "x_type", "x_source", "y_id", "y_type", "y_source",
             "relation", "display_relation"]
# Provenance metadata (2026-08-06): datatypes on gene_disease_edges (genetic_association
# vs somatic_mutation), ppi_sources on ppi_edges (menche/huri/string). Previously silently
# dropped here (clean() selected only EDGE_COLS) -- carried through the whole pipeline now
# as an extra column so it survives reverse-all/disease-grouping/node_index correctly, then
# split into a separate edge_metadata side table at the end. kg/graph_edges stay
# PrimeKG-exact (unaffected -- their write step already selects an explicit column list).
METADATA_COLS = {"gene_disease_edges": "datatypes", "ppi_edges": "ppi_sources"}


def clean(df, extra_col=None):
    cols = EDGE_COLS + ([extra_col] if extra_col else [])
    df = df[cols].dropna(subset=EDGE_COLS).drop_duplicates()
    return df[~((df.x_id == df.y_id) & (df.x_type == df.y_type) & (df.x_source == df.y_source))]


# ---- stack per-source edges ------------------------------------------------
kg = pd.concat([clean(dataiku.Dataset(d).get_dataframe().astype(str), METADATA_COLS.get(d))
                for d in EDGE_DATASETS], ignore_index=True).drop_duplicates()

# ---- reverse ALL edges (undirected) ----------------------------------------
# metadata columns are properties of the edge, not of x/y specifically -- carried through
# unchanged on the reversed copy (not swapped).
rev = kg.rename(columns={"x_id": "y_id", "x_type": "y_type", "x_source": "y_source",
                         "y_id": "x_id", "y_type": "x_type", "y_source": "x_source"})
kg = pd.concat([kg, rev], ignore_index=True).drop_duplicates()
kg = kg[~((kg.x_id == kg.y_id) & (kg.x_type == kg.y_type) & (kg.x_source == kg.y_source))]

# ---- node-name lookup by (type, id) from the vocab tables ------------------
gn = dataiku.Dataset("gene_names").get_dataframe()
mt = dataiku.Dataset("mondo_terms").get_dataframe()
rt = dataiku.Dataset("reactome_terms").get_dataframe()
dv = dataiku.Dataset("drug_vocab").get_dataframe()
gt = dataiku.Dataset("go_terms").get_dataframe(infer_with_pandas=False)
ht = dataiku.Dataset("hpo_terms").get_dataframe(infer_with_pandas=False)
name_by_key = {}
name_by_key.update({("gene/protein", str(int(e))): s for e, s in zip(gn.entrez_id, gn.symbol)})
name_by_key.update({("disease", str(m)): n for m, n in zip(mt.mondo_id.astype(str), mt.name)})
name_by_key.update({("pathway", str(p)): n for p, n in zip(rt.pathway_id, rt.name)})
name_by_key.update({("drug", str(d)): n for d, n in zip(dv.drugbank_id, dv.drug_name)})
# Task 10 additions (2026-08-06). GO namespace -> the y_type/x_type string used by
# harmonize_go_protein/_hierarchy (must match exactly). infer_with_pandas=False on both
# reads -- go_id/hpo_id are digit-suffixed strings that pandas' own type-sniffer will
# otherwise numeric-coerce, silently stripping leading zeros (hit this bug building the
# HP<->MONDO reclassification upstream; same root cause here).
NS_TO_TYPE = {"bioprocess": "biological_process", "molfunc": "molecular_function",
              "cellcomp": "cellular_component"}
name_by_key.update({(NS_TO_TYPE[ns], g): n for g, n, ns in zip(gt.go_id, gt.name, gt.namespace)})
name_by_key.update({("effect/phenotype", h): n for h, n in zip(ht.hpo_id, ht.name)})

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

dataiku.Dataset("graph_nodes").write_with_schema(
    nodes[["node_index", "node_id", "node_type", "node_name", "node_source"]])
dataiku.Dataset("kg").write_with_schema(
    kg[["relation", "display_relation", "x_index", "x_id", "x_type", "x_name", "x_source",
        "y_index", "y_id", "y_type", "y_name", "y_source"]])
dataiku.Dataset("graph_edges").write_with_schema(
    kg[["relation", "display_relation", "x_index", "y_index"]].drop_duplicates())

# ---- provenance metadata side table (kept off kg/graph_edges, see METADATA_COLS) ------
meta_present_cols = [c for c in METADATA_COLS.values() if c in kg.columns]
edge_metadata = kg[["x_index", "y_index", "relation"] + meta_present_cols].dropna(
    subset=meta_present_cols, how="all").drop_duplicates()
dataiku.Dataset("edge_metadata").write_with_schema(edge_metadata)
