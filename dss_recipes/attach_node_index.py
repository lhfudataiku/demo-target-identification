# attach_node_index -- Assembly zone, DEMO_KG_LS.
#
# WHAT IT DOES
#   Joins the node numbers back onto the grounded edges and writes the three final graph tables.
#   It is the last step of the four-recipe assembly:
#
#     stack_edge_sources (Stack)  -> kg_stacked
#     compute_kg_edges   (Python) -> kg_grounded + graph_nodes_unindexed
#     assign_node_index  (Window) -> graph_nodes            (node_index over a fixed sort)
#     attach_node_index  (this)   -> kg, graph_edges, edge_metadata
#
#   Steps:
#     1. Read kg_grounded and graph_nodes with type guessing off.
#     2. Check node_index and the node key are both unique, so the joins cannot multiply rows.
#     3. Join node_index onto the x end (x_index) and the y end (y_index); fail loudly, with
#        examples, if the row count changes or any endpoint has no number.
#     4. Write:
#        - kg            full edge table: relation, display_relation, x/y index, id, type, name,
#                        source (PrimeKG layout)
#        - graph_edges   slim table: relation, display_relation, x_index, y_index, de-duplicated
#        - edge_metadata side table: x_index, y_index, relation + provenance columns
#                        (datatypes, ppi_sources), only rows where at least one is filled in
#
#   Provenance stays in the side table so kg / graph_edges keep exactly PrimeKG's columns.
#   Both directions of every edge are present (see compute_kg_edges step 2), here and in all three
#   outputs.
#
# WHY PANDAS .merge() HERE (an exception to the "visual Join recipes" rule)
#   This is the most load-bearing recipe in the project: two joins and three column selections,
#   already validated. Visual recipes have twice produced silently wrong output on this project
#   (FLAG_PRESENCE; a Group recipe emitting one row instead of 555), and the asserts below are what
#   make a wrong join fail instead of pass. Converting it buys visibility at the cost of that risk.
import dataiku
import pandas as pd

KEY = ["node_id", "node_type", "node_name", "node_source"]
METADATA_COLS = ["datatypes", "ppi_sources"]

# ---- 1. read inputs ----------------------------------------------------------
# infer_with_pandas=False is MANDATORY. With inference on, get_dataframe() guesses dtypes per
# 65,536-row chunk: chunks whose x_id held only digits came back as int64 while graph_nodes.node_id
# stayed str, and the join silently missed those chunks (983,040 = 15 x 65,536 unresolved rows).
kg = dataiku.Dataset("kg_grounded").get_dataframe(infer_with_pandas=False)
nodes = dataiku.Dataset("graph_nodes").get_dataframe(infer_with_pandas=False)
for c in ["x_id", "x_type", "x_name", "x_source", "y_id", "y_type", "y_name", "y_source"]:
    kg[c] = kg[c].astype(str)
for c in KEY:
    nodes[c] = nodes[c].astype(str)
nodes["node_index"] = nodes.node_index.astype("int64")
print("grounded edges:", len(kg), "| indexed nodes:", len(nodes))

# ---- 2. node_index must be a one-to-one map of the node key ------------------
# Otherwise the joins below silently fan out (one edge -> several rows).
assert nodes.node_index.is_unique, "node_index is not unique"
assert not nodes.duplicated(subset=KEY).any(), "node key is not unique in graph_nodes"

# ---- 3. attach x_index and y_index -------------------------------------------
xi = nodes.rename(columns={"node_index": "x_index", "node_id": "x_id",
                           "node_type": "x_type", "node_name": "x_name", "node_source": "x_source"})
yi = nodes.rename(columns={"node_index": "y_index", "node_id": "y_id",
                           "node_type": "y_type", "node_name": "y_name", "node_source": "y_source"})
before = len(kg)
kg = kg.merge(xi, on=["x_id", "x_type", "x_name", "x_source"], how="left") \
       .merge(yi, on=["y_id", "y_type", "y_name", "y_source"], how="left")
assert len(kg) == before, f"index join changed row count: {before} -> {len(kg)}"
bad_x = kg[kg.x_index.isna()]
bad_y = kg[kg.y_index.isna()]
if len(bad_x) or len(bad_y):
    print(f"UNRESOLVED x: {len(bad_x)} rows, y: {len(bad_y)} rows")
    for lab, b, cols in [("x", bad_x, ["x_id", "x_type", "x_name", "x_source"]),
                         ("y", bad_y, ["y_id", "y_type", "y_name", "y_source"])]:
        if len(b):
            print(f"  {lab} examples:")
            print(b[cols].drop_duplicates().head(5).to_string(index=False))
            for c in cols:
                nn = int(b[c].isna().sum())
                if nn:
                    print(f"    {c}: {nn} nulls")
    raise AssertionError("some endpoints did not resolve to a node_index")
kg["x_index"] = kg.x_index.astype("int64")
kg["y_index"] = kg.y_index.astype("int64")

# ---- 4. write kg and graph_edges (PrimeKG columns only) ----------------------
# graph_edges is de-duplicated on (relation, display_relation, x_index, y_index), so it can have
# fewer rows than kg where the same link arrived with different provenance metadata.
dataiku.Dataset("kg").write_with_schema(
    kg[["relation", "display_relation", "x_index", "x_id", "x_type", "x_name", "x_source",
        "y_index", "y_id", "y_type", "y_name", "y_source"]])
dataiku.Dataset("graph_edges").write_with_schema(
    kg[["relation", "display_relation", "x_index", "y_index"]].drop_duplicates())

# ---- 4b. provenance side table -----------------------------------------------
# datatypes: Open Targets evidence behind a disease_protein edge -- "genetic_association"
#   (germline: inherited variants change disease risk), "somatic_mutation" (mutations found in
#   tumours), or both joined with "+". It is empty for disease_protein edges that come from
#   phenotype gene links reclassified to a disease, so those edges have no row here.
# ppi_sources: which interactome(s) reported a protein_protein edge.
# The relation label itself is the same for every disease_protein edge; this table is the only
# place the evidence type survives.
present = [c for c in METADATA_COLS if c in kg.columns]
edge_metadata = kg[["x_index", "y_index", "relation"] + present].dropna(
    subset=present, how="all").drop_duplicates()
print("kg:", len(kg), "| graph_edges:",
      len(kg[["relation", "display_relation", "x_index", "y_index"]].drop_duplicates()),
      "| edge_metadata:", len(edge_metadata))
dataiku.Dataset("edge_metadata").write_with_schema(edge_metadata)
