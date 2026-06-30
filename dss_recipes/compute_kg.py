# Conformant PrimeKG assembly (core sources) — faithful port of build_graph.ipynb.
# Produces PrimeKG-exact primekg_nodes (node_index,node_id,node_type,node_name,
# node_source) and primekg (relation,display_relation,x_*,y_*) + primekg_edges.
#
# Reuses PrimeKG harmonization: clean_edges grounding-drop, native ids + bare-integer
# MONDO, reverse-ALL edges (undirected), disease grouping via published map,
# giant-component filter, emergent nodes + node_index.
import dataiku
import networkx as nx
import pandas as pd

EDGE_COLS = ["relation", "display_relation", "x_id", "x_type", "x_name", "x_source",
             "y_id", "y_type", "y_name", "y_source"]


def clean_edges(df):
    df = df[EDGE_COLS].dropna().drop_duplicates()
    return df[~((df.x_id == df.y_id) & (df.x_type == df.y_type)
                & (df.x_source == df.y_source) & (df.x_name == df.y_name))]


def mondo_int(s):
    """'MONDO:0013924' / 'MONDO_0013924' -> '13924' (PrimeKG bare-integer form)."""
    if not isinstance(s, str):
        return None
    try:
        return str(int(s.replace("MONDO_", "MONDO:").split(":")[-1]))
    except ValueError:
        return None


# ---- vocab maps ------------------------------------------------------------
gn = dataiku.Dataset("gene_names").get_dataframe()
ent2sym = dict(zip(gn.entrez_id.astype("int64").astype(str), gn.symbol))

mt = dataiku.Dataset("mondo_terms").get_dataframe()
mt["mint"] = mt.mondo_id.map(mondo_int)
mondo_name = dict(zip(mt.mint, mt.name))

rt = dataiku.Dataset("reactome_terms").get_dataframe()
pwy_name = dict(zip(rt.pathway_id, rt.name))


def ent_id(s):
    return s.dropna().astype("int64").astype(str)


# ---- edge dataframes (12-col, grounded) ------------------------------------
edge_frames = []

# PPI  -> protein_protein / ppi
ppi = dataiku.Dataset("protein_protein").get_dataframe().dropna()
ppi = ppi.assign(
    x_id=ent_id(ppi.proteinA_entrezid), y_id=ent_id(ppi.proteinB_entrezid),
    x_type="gene/protein", y_type="gene/protein", x_source="NCBI", y_source="NCBI",
    relation="protein_protein", display_relation="ppi")
ppi["x_name"] = ppi.x_id.map(ent2sym)
ppi["y_name"] = ppi.y_id.map(ent2sym)
edge_frames.append(clean_edges(ppi))

# Open Targets gene-disease -> disease_protein / associated with
gd = dataiku.Dataset("gene_disease").get_dataframe()
gd = gd.assign(
    x_id=gd.entrez_id.astype("int64").astype(str), x_name=gd.symbol,
    x_type="gene/protein", x_source="NCBI",
    y_id=gd.mondo_id.map(mondo_int), y_type="disease", y_source="MONDO",
    relation="disease_protein", display_relation="associated with")
gd["y_name"] = gd.y_id.map(mondo_name)
edge_frames.append(clean_edges(gd))

# Reactome gene-pathway -> pathway_protein / interacts with
rn = dataiku.Dataset("reactome_ncbi").get_dataframe()
rn = rn.assign(
    x_id=rn.entrez_id.astype("int64").astype(str), x_type="gene/protein", x_source="NCBI",
    y_id=rn.pathway_id, y_type="pathway", y_source="REACTOME",
    relation="pathway_protein", display_relation="interacts with")
rn["x_name"] = rn.x_id.map(ent2sym)
rn["y_name"] = rn.y_id.map(pwy_name)
edge_frames.append(clean_edges(rn))

# Reactome hierarchy -> pathway_pathway / parent-child
rr = dataiku.Dataset("reactome_relations").get_dataframe()
rr = rr.assign(
    x_id=rr.parent_id, y_id=rr.child_id, x_type="pathway", y_type="pathway",
    x_source="REACTOME", y_source="REACTOME",
    relation="pathway_pathway", display_relation="parent-child")
rr["x_name"] = rr.x_id.map(pwy_name)
rr["y_name"] = rr.y_id.map(pwy_name)
edge_frames.append(clean_edges(rr))

# MONDO hierarchy -> disease_disease / parent-child
mp = dataiku.Dataset("mondo_parents").get_dataframe()
mp = mp.assign(
    x_id=mp.parent_id.map(mondo_int), y_id=mp.mondo_id.map(mondo_int),
    x_type="disease", y_type="disease", x_source="MONDO", y_source="MONDO",
    relation="disease_disease", display_relation="parent-child")
mp["x_name"] = mp.x_id.map(mondo_name)
mp["y_name"] = mp.y_id.map(mondo_name)
edge_frames.append(clean_edges(mp))

# Drug -> target (OT mechanism of action) -> drug_protein / action type
dt = dataiku.Dataset("drug_target").get_dataframe()
dt = dt.assign(
    x_id=dt.drugbank_id, x_name=dt.drug_name, x_type="drug", x_source="DrugBank",
    y_id=dt.entrez_id.astype("int64").astype(str), y_name=dt.symbol,
    y_type="gene/protein", y_source="NCBI",
    relation="drug_protein", display_relation=dt.action_type.fillna("targets"))
edge_frames.append(clean_edges(dt))

# Drug -> disease (OT clinical indication) -> indication
di = dataiku.Dataset("drug_indication").get_dataframe()
di = di.assign(
    x_id=di.drugbank_id, x_name=di.drug_name, x_type="drug", x_source="DrugBank",
    y_id=di.mondo_id.map(mondo_int), y_type="disease", y_source="MONDO",
    relation="indication", display_relation="indication")
di["y_name"] = di.y_id.map(mondo_name)
edge_frames.append(clean_edges(di))

kg = pd.concat(edge_frames, ignore_index=True)


# ---- reverse ALL edges (undirected) ----------------------------------------
def reverse_all(kg):
    kg = kg.drop_duplicates()
    rev = kg.rename(columns={
        "x_id": "y_id", "x_type": "y_type", "x_name": "y_name", "x_source": "y_source",
        "y_id": "x_id", "y_type": "x_type", "y_name": "x_name", "y_source": "x_source"})
    kg = pd.concat([kg, rev], ignore_index=True).drop_duplicates()
    return kg[~((kg.x_id == kg.y_id) & (kg.x_type == kg.y_type)
                & (kg.x_source == kg.y_source) & (kg.x_name == kg.y_name))]


kg = reverse_all(kg)

# ---- disease grouping (apply PrimeKG's published BERT map) ------------------
gmap = dataiku.Dataset("disease_group_map").get_dataframe()
g_id = dict(zip(gmap.node_id.astype(str), gmap.group_id_bert.astype(str)))
g_name = dict(zip(gmap.node_id.astype(str), gmap.group_name_bert))
for side in ("x", "y"):
    m = (kg[side + "_type"] == "disease") & (kg[side + "_source"] == "MONDO") \
        & (kg[side + "_id"].isin(g_id))
    kg.loc[m, side + "_name"] = kg.loc[m, side + "_id"].map(g_name)
    kg.loc[m, side + "_source"] = "MONDO_grouped"
    kg.loc[m, side + "_id"] = kg.loc[m, side + "_id"].map(g_id)
kg = reverse_all(kg)  # re-dedup/self-loop after grouping (PrimeKG repeats this)

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

kg_out = kg[["relation", "display_relation", "x_index", "x_id", "x_type", "x_name",
             "x_source", "y_index", "y_id", "y_type", "y_name", "y_source"]]
edges_out = kg[["relation", "display_relation", "x_index", "y_index"]].drop_duplicates()

dataiku.Dataset("primekg_nodes").write_with_schema(
    nodes[["node_index", "node_id", "node_type", "node_name", "node_source"]])
dataiku.Dataset("primekg").write_with_schema(kg_out)
dataiku.Dataset("primekg_edges").write_with_schema(edges_out)
