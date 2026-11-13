# compute_kg_edges -- Assembly zone, DEMO_KG_LS.
#
# WHAT IT DOES
#   Turns the stacked raw edges into a clean, undirected, fully named graph that follows PrimeKG's
#   harmonization rules. It is step 2 of the four-recipe assembly:
#
#     stack_edge_sources (Stack)  -> kg_stacked
#     compute_kg_edges   (this)   -> kg_grounded + graph_nodes_unindexed
#     assign_node_index  (Window) -> graph_nodes            (node_index over a fixed sort)
#     attach_node_index  (Python) -> kg, graph_edges, edge_metadata
#
#   Steps, in order:
#     1. Read kg_stacked.
#     2. Make every edge two-way (store both x->y and y->x).
#     3. Attach a name to both endpoints; drop edges whose endpoints have no name.
#     4. Replace MONDO diseases with their PrimeKG disease group.
#     5. Keep only the largest connected component.
#     6. Write the edges and the distinct node set (without node_index).
#
# A node's identity everywhere in this recipe is the 4-part key (id, type, name, source). The same
# key is used by assign_node_index and attach_node_index, so it must not change here.
import dataiku
import networkx as nx
import pandas as pd

EDGE_COLS = ["x_id", "x_type", "x_source", "y_id", "y_type", "y_source",
             "relation", "display_relation"]

# ---- 1. read the stacked edges -----------------------------------------------
# kg_stacked is the union of the 12 per-source edge tables (Stack recipe, mode=UNION, self-loops
# removed, distinct).
#
# - mode=UNION is load-bearing: the provenance columns `datatypes` (gene_disease_edges) and
#   `ppi_sources` (ppi_edges) exist on only 2 of the 12 inputs. INTERSECT would silently drop both,
#   and the edge_metadata side table with them.
# - The Stack deliberately has no non-blank filter. Rows with a missing id survive it and are removed
#   in step 3 instead, because their endpoint cannot be named.
#
# infer_with_pandas=False plus a str cast on the 8 key columns is MANDATORY. With inference on,
# get_dataframe() guesses dtypes per 65,536-row chunk, so digit-only id columns come back as int64 in
# some chunks and every later key comparison silently fails. The metadata columns are deliberately
# NOT cast: their nulls must stay null, or edge_metadata's dropna(how="all") keeps every row.
kg = dataiku.Dataset("kg_stacked").get_dataframe(infer_with_pandas=False)
for c in EDGE_COLS:
    kg[c] = kg[c].astype(str)

print("STACKED (post-clean, pre-reverse):", len(kg))   # expected row count for the Stack recipe

# ---- 2. make every edge two-way ----------------------------------------------
# The graph is undirected: "drug A targets gene B" is the same link from either end. The sources do
# not agree on which end is x, and some (e.g. protein-protein) already list a pair both ways. Adding
# every reversed copy and de-duplicating gives exactly one row per direction, whatever the source did.
#
# Why store both directions:
#   - PrimeKG's published kg.csv stores each link once per direction; matching that layout keeps the
#     output comparable to PrimeKG row for row.
#   - "All neighbours of node N" is then simply x_index == N. A consumer that only filters the x side
#     still sees every neighbour.
#
# Consequences for consumers:
#   - Row counts are 2x the number of links. Count distinct neighbours, not rows, for degree.
#   - relation / display_relation are NOT flipped on the reversed copy, so a label worded from one
#     end (e.g. a drug-side action) also appears on the row read from the other end.
#   - The metadata columns (datatypes, ppi_sources) describe the edge, not an endpoint, so they are
#     copied unchanged rather than swapped.
rev = kg.rename(columns={"x_id": "y_id", "x_type": "y_type", "x_source": "y_source",
                         "y_id": "x_id", "y_type": "x_type", "y_source": "x_source"})
kg = pd.concat([kg, rev], ignore_index=True).drop_duplicates()
kg = kg[~((kg.x_id == kg.y_id) & (kg.x_type == kg.y_type) & (kg.x_source == kg.y_source))]

# ---- 3. name both endpoints (grounding) --------------------------------------
# Lookup (type, id) -> name from the six vocabulary tables. An edge with an endpoint that has no
# name is dropped: every edge must resolve to two real nodes.
gn = dataiku.Dataset("gene_names").get_dataframe()
mt = dataiku.Dataset("mondo_terms").get_dataframe()
rt = dataiku.Dataset("reactome_terms").get_dataframe()
dv = dataiku.Dataset("drug_vocab").get_dataframe()
# GO and HPO ids are digit-suffixed strings; pandas' type guessing would turn them into numbers and
# strip leading zeros, so both are read with inference off.
gt = dataiku.Dataset("go_terms").get_dataframe(infer_with_pandas=False)
ht = dataiku.Dataset("hpo_terms").get_dataframe(infer_with_pandas=False)
name_by_key = {}
name_by_key.update({("gene/protein", str(int(e))): s for e, s in zip(gn.entrez_id, gn.symbol)})
name_by_key.update({("disease", str(m)): n for m, n in zip(mt.mondo_id.astype(str), mt.name)})
name_by_key.update({("pathway", str(p)): n for p, n in zip(rt.pathway_id, rt.name)})
name_by_key.update({("drug", str(d)): n for d, n in zip(dv.drugbank_id, dv.drug_name)})
# GO namespace -> node type. These strings must match exactly the types written by
# harmonize_go_protein / harmonize_go_hierarchy.
NS_TO_TYPE = {"bioprocess": "biological_process", "molfunc": "molecular_function",
              "cellcomp": "cellular_component"}
name_by_key.update({(NS_TO_TYPE[ns], g): n for g, n, ns in zip(gt.go_id, gt.name, gt.namespace)})
name_by_key.update({("effect/phenotype", h): n for h, n in zip(ht.hpo_id, ht.name)})

kg["x_name"] = [name_by_key.get((t, i)) for t, i in zip(kg.x_type, kg.x_id)]
kg["y_name"] = [name_by_key.get((t, i)) for t, i in zip(kg.y_type, kg.y_id)]
kg = kg.dropna(subset=["x_name", "y_name"])  # grounding-drop: endpoints must resolve to a node

# ---- 4. group diseases (PrimeKG's published grouping map) --------------------
# A MONDO disease that belongs to a PrimeKG group takes the group's id and name, and its source
# becomes "MONDO_grouped". Grouping can merge two endpoints or two edges into one, so duplicates and
# self-loops are removed again afterwards.
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

# ---- 5. keep only the largest connected component ----------------------------
# After grounding and grouping, a few small islands can be cut off from the main graph (e.g. two
# nodes linked only to each other, or a cluster whose only bridge was dropped in step 3).
# Build an undirected graph on the 4-part node key, find the biggest connected piece, and keep only
# edges inside it. Both ends of an edge are always in the same piece, so whole edges are kept or
# dropped. PrimeKG applies the same rule.
#
# Why: path-based features (e.g. DWPC) count chains of edges from a gene to a disease; a node on an
# island has no path to the rest of the graph and would only add zero-value rows. Nodes on islands
# disappear entirely, because step 6 builds the node list from the surviving edges.
kg["xk"] = list(zip(kg.x_id, kg.x_type, kg.x_name, kg.x_source))
kg["yk"] = list(zip(kg.y_id, kg.y_type, kg.y_name, kg.y_source))
G = nx.Graph()
G.add_edges_from(zip(kg.xk, kg.yk))
giant = set(max(nx.connected_components(G), key=len))
kg = kg[kg.xk.isin(giant) & kg.yk.isin(giant)].copy()


# ---- 6. write edges and the node set (no node_index here) --------------------
# node_index is NOT assigned here. Numbering by row position (the old .reset_index()) depended on
# concat order, so every rebuild silently renumbered nodes and broke hard-coded indices downstream
# (personas, disease_split_key, WATCH lists). assign_node_index numbers nodes over an explicit sort
# (node_type, node_source, node_id, node_name), so the numbering depends only on which nodes exist;
# attach_node_index then joins the numbers back onto these edges by the 4-part key.
nodes = pd.concat([
    kg[["x_id", "x_type", "x_name", "x_source"]].rename(columns={
        "x_id": "node_id", "x_type": "node_type", "x_name": "node_name", "x_source": "node_source"}),
    kg[["y_id", "y_type", "y_name", "y_source"]].rename(columns={
        "y_id": "node_id", "y_type": "node_type", "y_name": "node_name", "y_source": "node_source"}),
]).drop_duplicates()

print("grounded edges:", len(kg), "| emergent nodes:", len(nodes))
dataiku.Dataset("graph_nodes_unindexed").write_with_schema(nodes[["node_id", "node_type", "node_name", "node_source"]])
dataiku.Dataset("kg_grounded").write_with_schema(kg.drop(columns=["xk", "yk"]))
