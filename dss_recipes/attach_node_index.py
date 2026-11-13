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
#     3b. Rewrite display_relation into readable labels (relation untouched; counts unchanged).
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

# ---- display-label vocabulary (used in step 3b) ------------------------------
# Wording is chosen to read correctly from the side the built graph stores cross-type edges on
# (x -> y: protein -> disease / pathway / phenotype, drug -> disease), and to stay neutral for
# same-type relations, which are stored in both directions with the same label.

# disease_protein: from the Open Targets evidence types in `datatypes`, pooled over every row of the
# same link. No type at all means the link comes only from a phenotype gene link whose phenotype term
# is also a disease (harmonize_phenotype_protein).
DP_LABELS = {
    frozenset({"genetic_association"}): "germline genetic association",
    frozenset({"somatic_mutation"}): "somatic mutation association",
    frozenset({"genetic_association", "somatic_mutation"}): "germline + somatic association",
    frozenset(): "linked via phenotype annotation",
}
# disease_disease is the MONDO hierarchy only and keeps "parent-child". Disease -> phenotype
# annotations whose phenotype term is also a disease have their own relation,
# disease_phenotype_disease, labelled at source by harmonize_disease_phenotype.
# One raw value -> one readable value.
CONSTANT_LABELS = {
    ("protein_protein", "ppi"): "interacts with",
    ("pathway_protein", "interacts with"): "member of pathway",       # Reactome membership
    ("phenotype_protein", "has phenotype"): "linked to phenotype (via disease)",
}
# indication / drug_investigated_for: display_relation holds the highest clinical stage reached.
STAGE_LABELS = {
    "APPROVAL": "approved for",
    "PREAPPROVAL": "filed for approval for",
    "PHASE_3": "in phase 3 trials for",
    "PHASE_2_3": "in phase 2/3 trials for",
    "PHASE_2": "in phase 2 trials for",
    "PHASE_1_2": "in phase 1/2 trials for",
    "PHASE_1": "in phase 1 trials for",
    "EARLY_PHASE_1": "in early phase 1 trials for",
    "IND": "IND filed for",
    "PRECLINICAL": "preclinical for",
    "UNKNOWN": "investigated for (stage unknown)",
}
LINK_COLS = ["relation", "display_relation", "x_index", "y_index"]


def relabel_display(kg):
    """Rewrite display_relation only; relation, endpoints and row count are unchanged."""
    kg = kg.copy()
    rel = kg.relation.copy()

    # disease_protein -- one label per link, from the pooled evidence types
    dp = rel == "disease_protein"
    links = [frozenset((a, b)) for a, b in zip(kg.x_index[dp], kg.y_index[dp])]
    raw = kg.datatypes[dp] if "datatypes" in kg.columns else pd.Series([None] * int(dp.sum()))
    pooled = {}
    for link, t in zip(links, raw):
        s = pooled.setdefault(link, set())
        if isinstance(t, str) and t and t != "nan":
            s.update(t.split("+"))
    unknown = {frozenset(s) for s in pooled.values()} - set(DP_LABELS)
    assert not unknown, f"unexpected disease_protein evidence types: {unknown}"
    kg.loc[dp, "display_relation"] = [DP_LABELS[frozenset(pooled[link])] for link in links]

    # fixed-text relations
    for (r, old), new in CONSTANT_LABELS.items():
        kg.loc[(rel == r) & (kg.display_relation == old), "display_relation"] = new

    # clinical stage -> readable phrase; an unmapped stage is kept as-is and reported
    st = rel.isin(["indication", "drug_investigated_for"])
    missing = sorted(set(kg.display_relation[st]) - set(STAGE_LABELS))
    if missing:
        print("WARNING: clinical stages without a readable label, left unchanged:", missing)
    kg.loc[st, "display_relation"] = kg.display_relation[st].map(lambda v: STAGE_LABELS.get(v, v))
    return kg

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

# ---- 3b. readable display labels (display_relation only) ---------------------
# display_relation is the edge label people read in the Graph Explorer. The per-source recipes
# set it to fixed or raw values; this step rewrites it once, here, so that:
#   - `relation` is never touched. Part 2 features and labels read relation + x/y index only.
#   - The per-source tables keep their raw values. Part 2's drug evidence chain reads
#     drug_protein_edges / drug_disease_edges directly (group_drug_protein_actions,
#     join_drug_evidence_records, compute_drug_target_benchmark), not kg / graph_edges.
#   - Every rule gives ONE label per (relation, link), or maps one raw value to one new value, so no
#     two rows that differ today become identical and no identical rows split. kg, graph_edges and
#     the built graph keep exactly their row and edge counts.
n_links = len(kg[LINK_COLS].drop_duplicates())
kg = relabel_display(kg)
assert len(kg[LINK_COLS].drop_duplicates()) == n_links, "relabel changed the graph_edges row count"
print("display labels:", kg.groupby(["relation", "display_relation"]).size().to_dict())

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
