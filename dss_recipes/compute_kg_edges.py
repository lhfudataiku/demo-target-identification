# Assembly zone — the graph-algorithm core (Python).
# Stacks per-source *_edges (8-col, name-free), attaches node names from the vocab
# tables, applies PrimeKG harmonization (clean, reverse-all, disease grouping, giant
# component), derives emergent nodes + node_index. Outputs PrimeKG-exact kg /
# graph_nodes / graph_edges.
import dataiku
import networkx as nx
import pandas as pd

EDGE_COLS = ["x_id", "x_type", "x_source", "y_id", "y_type", "y_source",
             "relation", "display_relation"]

# ---- stacked edge sources (moved out 2026-08-14) ----------------------------
# The per-source stack is now the `stack_edge_sources` Stack recipe: 12 inputs, mode=UNION,
# a post-filter dropping self-loops, and distinct. Verified equivalent -- both the old
# pd.concat path and the Stack produce exactly 1,474,753 rows.
#
# mode=UNION is load-bearing: `datatypes` (gene_disease_edges) and `ppi_sources` (ppi_edges)
# exist on only 2 of the 12 inputs, and INTERSECT would silently drop both -- taking the
# edge_metadata side table (844,166 rows) with them.
#
# The original also called .dropna(subset=EDGE_COLS), which was DEAD CODE: .astype(str) ran
# first and turned any null into the literal string "nan", so dropna never matched. Those rows
# survive the stack and are removed later by the name-grounding join instead. The Stack
# therefore omits it deliberately -- adding isNonBlank() would drop rows the original kept.
#
# infer_with_pandas=False + explicit str cast on the 8 key columns only: with inference on,
# get_dataframe() infers dtypes per 65,536-row chunk and digit-only id columns come back as
# int64 in some chunks, which silently breaks every downstream key comparison. The metadata
# columns are deliberately NOT cast -- their nulls must stay null or edge_metadata's
# dropna(how="all") keeps everything.
kg = dataiku.Dataset("kg_stacked").get_dataframe(infer_with_pandas=False)
for c in EDGE_COLS:
    kg[c] = kg[c].astype(str)

print("STACKED (post-clean, pre-reverse):", len(kg))   # expected row count for the Stack recipe

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


# ---- SPLIT (2026-08-14): node_index assignment moved out of this recipe ------
# `node_index` used to be assigned here by pandas `.reset_index()`, i.e. POSITIONALLY --
# it depended on concat row order, so every rebuild silently renumbered every node and
# broke every hardcoded index downstream (personas, disease_split_key, WATCH lists).
# It is now assigned by the `assign_node_index` Window recipe over an explicit
# ORDER BY node_type, node_source, node_id, node_name -- a total order on the node key,
# so the mapping is a pure function of the node SET and reproducible across rebuilds.
# This recipe therefore emits the node set WITHOUT indices, and the edges keyed by the
# 4-part natural key; `attach_node_index` joins the indices back on afterwards.
nodes = pd.concat([
    kg[["x_id", "x_type", "x_name", "x_source"]].rename(columns={
        "x_id": "node_id", "x_type": "node_type", "x_name": "node_name", "x_source": "node_source"}),
    kg[["y_id", "y_type", "y_name", "y_source"]].rename(columns={
        "y_id": "node_id", "y_type": "node_type", "y_name": "node_name", "y_source": "node_source"}),
]).drop_duplicates()

print("grounded edges:", len(kg), "| emergent nodes:", len(nodes))
dataiku.Dataset("graph_nodes_unindexed").write_with_schema(nodes[["node_id", "node_type", "node_name", "node_source"]])
dataiku.Dataset("kg_grounded").write_with_schema(kg.drop(columns=["xk", "yk"]))
