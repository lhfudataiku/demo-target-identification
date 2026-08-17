# Attach node_index to the grounded edges and emit the three PrimeKG-exact outputs.
#
# Third of the three recipes that `compute_kg` was split into (2026-08-14):
#   1. compute_kg_edges   (Python) -- stack, clean, reverse-all, ground, group diseases,
#                                     giant-component filter -> kg_grounded + graph_nodes_unindexed
#   2. assign_node_index  (Window) -- deterministic node_index over an explicit ORDER BY
#   3. attach_node_index  (this)   -- join the indices back, write kg / graph_edges / edge_metadata
#
# WHY THE SPLIT: node_index used to come from pandas `.reset_index()` — positional, so it
# depended on concat row order and silently renumbered every node on each rebuild. Step 2 makes
# it a pure function of the node key. The relational work here stays in Python deliberately:
# it is two joins and three column selections, already validated, and DSS visual semantics have
# twice this session produced silently wrong output (FLAG_PRESENCE, a Group recipe emitting one
# row instead of 555). Converting it buys visibility at the cost of risk on the most
# load-bearing recipe in the project.
import dataiku
import pandas as pd

KEY = ["node_id", "node_type", "node_name", "node_source"]
METADATA_COLS = ["datatypes", "ppi_sources"]

# infer_with_pandas=False is MANDATORY here. With inference on, get_dataframe() reads in
# 65,536-row chunks and infers dtypes PER CHUNK -- chunks whose x_id happened to contain only
# digit strings came back as int64 while graph_nodes.node_id stayed str, so the join silently
# missed for those chunks (983,040 = 15 x 65,536 unresolved rows). Same coercion hazard the
# GO/HPO reads guard against upstream.
kg = dataiku.Dataset("kg_grounded").get_dataframe(infer_with_pandas=False)
nodes = dataiku.Dataset("graph_nodes").get_dataframe(infer_with_pandas=False)
for c in ["x_id", "x_type", "x_name", "x_source", "y_id", "y_type", "y_name", "y_source"]:
    kg[c] = kg[c].astype(str)
for c in KEY:
    nodes[c] = nodes[c].astype(str)
nodes["node_index"] = nodes.node_index.astype("int64")
print("grounded edges:", len(kg), "| indexed nodes:", len(nodes))

# node_index must be a bijection on the node key, or the joins below silently fan out
assert nodes.node_index.is_unique, "node_index is not unique"
assert not nodes.duplicated(subset=KEY).any(), "node key is not unique in graph_nodes"

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

dataiku.Dataset("kg").write_with_schema(
    kg[["relation", "display_relation", "x_index", "x_id", "x_type", "x_name", "x_source",
        "y_index", "y_id", "y_type", "y_name", "y_source"]])
dataiku.Dataset("graph_edges").write_with_schema(
    kg[["relation", "display_relation", "x_index", "y_index"]].drop_duplicates())

# ---- provenance metadata side table (kept off kg/graph_edges) ----------------
present = [c for c in METADATA_COLS if c in kg.columns]
edge_metadata = kg[["x_index", "y_index", "relation"] + present].dropna(
    subset=present, how="all").drop_duplicates()
print("kg:", len(kg), "| graph_edges:",
      len(kg[["relation", "display_relation", "x_index", "y_index"]].drop_duplicates()),
      "| edge_metadata:", len(edge_metadata))
dataiku.Dataset("edge_metadata").write_with_schema(edge_metadata)
