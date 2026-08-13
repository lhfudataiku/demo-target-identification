import dataiku
import numpy as np
import pandas as pd


def pipe_join(values):
    """Return a deterministic, readable list for the audit tables."""
    values = sorted({str(value) for value in values if pd.notna(value) and str(value)})
    return " | ".join(values)


def candidate_3_role(family_id):
    """Reproduce split_graph_features_candidate_3's active split rule."""
    if pd.isna(family_id):
        return None
    family_id = int(family_id)
    if family_id in (15347, 16415) or family_id % 10 in (0, 1, 2, 3, 4):
        return "validation"
    if family_id % 10 == 5:
        return "test"
    return "train"


# Hetionet's DO-Slim list is the curated anchor definition. Map it through
# MONDO's DOID cross references; keep unmapped DOIDs in the final summary.
anchors = dataiku.Dataset("hetionet_disease_slim").get_dataframe(
    infer_with_pandas=False
).rename(columns={"doid": "anchor_doid", "name": "anchor_name"})
references = dataiku.Dataset("mondo_references").get_dataframe(
    infer_with_pandas=False
)
doid_references = (
    references.loc[references.ontology == "DOID", ["ontology_id", "mondo_id"]]
    .drop_duplicates()
    .rename(columns={"ontology_id": "anchor_doid", "mondo_id": "anchor_mondo_id"})
)
anchor_map = anchors.merge(doid_references, on="anchor_doid", how="left")

terms = (
    dataiku.Dataset("mondo_terms")
    .get_dataframe(infer_with_pandas=False)
    .drop_duplicates("mondo_id")
    .rename(columns={"name": "mondo_name"})
)
mondo_nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type", "node_source"],
    infer_with_pandas=False,
)
mondo_nodes = (
    mondo_nodes.loc[
        (mondo_nodes.node_type == "disease") & (mondo_nodes.node_source == "MONDO"),
        ["node_index", "node_id"],
    ]
    .drop_duplicates("node_id")
    .rename(columns={"node_id": "mondo_id", "node_index": "disease_index"})
)

# Add population membership and the split role actually used by candidate_3.
families = dataiku.Dataset("disease_family_id").get_dataframe(
    infer_with_pandas=False
)
families["candidate_3_split_role"] = families.disease_family_id.map(candidate_3_role)
family_details = families[
    ["disease_index", "disease_family_id", "anchor_name", "hop_depth", "candidate_3_split_role"]
].rename(columns={"anchor_name": "assigned_anchor_name"})

mondo_details = terms.merge(mondo_nodes, on="mondo_id", how="left").merge(
    family_details, on="disease_index", how="left"
)
mondo_details["in_split_population"] = mondo_details.disease_family_id.notna()

anchor_map = anchor_map.merge(
    mondo_details.rename(
        columns={
            "mondo_id": "anchor_mondo_id",
            "mondo_name": "anchor_mondo_name",
            "disease_index": "anchor_disease_index",
            "disease_family_id": "anchor_assigned_family_id",
            "assigned_anchor_name": "anchor_assigned_anchor_name",
            "hop_depth": "anchor_hop_depth",
            "candidate_3_split_role": "anchor_candidate_3_split_role",
            "in_split_population": "anchor_in_split_population",
        }
    ),
    on="anchor_mondo_id",
    how="left",
)
anchor_map["anchor_mapping_status"] = np.where(
    anchor_map.anchor_mondo_id.isna(), "no_mondo_mapping", "mapped_to_mondo"
)

# One MONDO term can be associated with more than one DO-Slim item. The labels
# make that explicit instead of silently choosing one anchor.
mapped_anchors = anchor_map.dropna(subset=["anchor_mondo_id"]).copy()
anchor_labels = (
    mapped_anchors.groupby("anchor_mondo_id", as_index=False)
    .agg(
        mondo_anchor_doids=("anchor_doid", pipe_join),
        mondo_anchor_names=("anchor_name", pipe_join),
    )
    .rename(columns={"anchor_mondo_id": "mondo_id"})
)

hierarchy = dataiku.Dataset("raw_disease_disease").get_dataframe(
    infer_with_pandas=False
).drop_duplicates(["parent_id", "child_id"])

# Each anchor is paired with every direct parent. A left join deliberately
# retains roots and anchors without a MONDO mapping for review.
anchor_parents = anchor_map.merge(
    hierarchy.rename(columns={"child_id": "anchor_mondo_id", "parent_id": "parent_mondo_id"}),
    on="anchor_mondo_id",
    how="left",
)

parent_sizes = (
    hierarchy.groupby("parent_id", as_index=False)
    .agg(parent_immediate_child_count=("child_id", "nunique"))
    .rename(columns={"parent_id": "parent_mondo_id"})
)
parent_anchor_children = hierarchy.merge(
    anchor_labels.rename(columns={"mondo_id": "child_id"}), on="child_id", how="inner"
)
parent_anchor_summary = (
    parent_anchor_children.groupby("parent_id", as_index=False)
    .agg(
        parent_anchor_child_count=("child_id", "nunique"),
        parent_anchor_child_mondo_ids=("child_id", pipe_join),
        parent_anchor_child_names=("mondo_anchor_names", pipe_join),
    )
    .rename(columns={"parent_id": "parent_mondo_id"})
)

# Detail attributes for an arbitrary MONDO term (parent or child).
term_details = mondo_details.rename(
    columns={
        "mondo_id": "detail_mondo_id",
        "mondo_name": "detail_mondo_name",
        "disease_index": "detail_disease_index",
        "disease_family_id": "detail_assigned_family_id",
        "assigned_anchor_name": "detail_assigned_anchor_name",
        "hop_depth": "detail_hop_depth",
        "candidate_3_split_role": "detail_candidate_3_split_role",
        "in_split_population": "detail_in_split_population",
    }
)


def add_term_details(frame, id_column, prefix):
    details = term_details.rename(
        columns={column: column.replace("detail_", prefix) for column in term_details.columns}
    )
    # Keep the relationship key on the left intact. Without a distinct right
    # key, pandas retains one shared column and the cleanup drop removes it.
    right_key = f"__{prefix}detail_key"
    details = details.rename(columns={f"{prefix}mondo_id": right_key})
    return frame.merge(
        details,
        left_on=id_column,
        right_on=right_key,
        how="left",
    ).drop(columns=[right_key])


summary = add_term_details(anchor_parents, "parent_mondo_id", "parent_")
summary = summary.merge(
    anchor_labels.rename(
        columns={
            "mondo_id": "parent_mondo_id",
            "mondo_anchor_doids": "parent_anchor_doids",
            "mondo_anchor_names": "parent_anchor_names",
        }
    ),
    on="parent_mondo_id",
    how="left",
).merge(parent_sizes, on="parent_mondo_id", how="left").merge(
    parent_anchor_summary, on="parent_mondo_id", how="left"
)

summary["parent_is_anchor"] = summary.parent_anchor_names.notna()
summary["other_anchor_children_count"] = (
    summary.parent_anchor_child_count.fillna(0).astype(int) - 1
).clip(lower=0)
summary["anchor_parent_cross_split"] = np.where(
    summary.anchor_in_split_population.fillna(False)
    & summary.parent_in_split_population.fillna(False)
    & (summary.anchor_candidate_3_split_role != summary.parent_candidate_3_split_role),
    True,
    False,
)
summary["relationship_status"] = np.select(
    [
        summary.anchor_mondo_id.isna(),
        summary.parent_mondo_id.isna(),
        summary.anchor_parent_cross_split,
        summary.parent_is_anchor,
        summary.other_anchor_children_count > 0,
    ],
    [
        "anchor_has_no_mondo_mapping",
        "anchor_has_no_direct_mondo_parent",
        "direct_anchor_parent_crosses_candidate_3_split",
        "direct_parent_is_another_anchor",
        "parent_has_multiple_anchor_children",
    ],
    default="no_direct_anchor_conflict_detected",
)

# Expand every direct parent of every anchor to all of that parent's immediate
# children. This is the reviewable table requested by the user.
detail = summary.merge(
    hierarchy.rename(columns={"parent_id": "parent_mondo_id", "child_id": "parent_child_mondo_id"}),
    on="parent_mondo_id",
    how="left",
)
detail = add_term_details(detail, "parent_child_mondo_id", "parent_child_")
detail = detail.merge(
    anchor_labels.rename(
        columns={
            "mondo_id": "parent_child_mondo_id",
            "mondo_anchor_doids": "parent_child_anchor_doids",
            "mondo_anchor_names": "parent_child_anchor_names",
        }
    ),
    on="parent_child_mondo_id",
    how="left",
)
detail["parent_child_is_anchor"] = detail.parent_child_anchor_names.notna()
detail["parent_child_is_the_anchor"] = (
    detail.parent_child_mondo_id == detail.anchor_mondo_id
)
detail["anchor_child_cross_split"] = np.where(
    detail.anchor_in_split_population.fillna(False)
    & detail.parent_child_in_split_population.fillna(False)
    & detail.parent_child_is_anchor.fillna(False)
    & (detail.anchor_candidate_3_split_role != detail.parent_child_candidate_3_split_role),
    True,
    False,
)

summary_columns = [
    "anchor_doid", "anchor_name", "anchor_mondo_id", "anchor_mondo_name",
    "anchor_disease_index", "anchor_in_split_population", "anchor_assigned_family_id",
    "anchor_assigned_anchor_name", "anchor_hop_depth", "anchor_candidate_3_split_role",
    "anchor_mapping_status", "parent_mondo_id", "parent_mondo_name", "parent_disease_index",
    "parent_in_split_population", "parent_assigned_family_id", "parent_assigned_anchor_name",
    "parent_hop_depth", "parent_candidate_3_split_role", "parent_is_anchor",
    "parent_anchor_doids", "parent_anchor_names", "parent_immediate_child_count",
    "parent_anchor_child_count", "other_anchor_children_count",
    "parent_anchor_child_mondo_ids", "parent_anchor_child_names",
    "anchor_parent_cross_split", "relationship_status",
]
detail_columns = summary_columns + [
    "parent_child_mondo_id", "parent_child_mondo_name", "parent_child_disease_index",
    "parent_child_in_split_population", "parent_child_assigned_family_id",
    "parent_child_assigned_anchor_name", "parent_child_hop_depth",
    "parent_child_candidate_3_split_role", "parent_child_is_anchor",
    "parent_child_anchor_doids", "parent_child_anchor_names",
    "parent_child_is_the_anchor", "anchor_child_cross_split",
]

summary_out = summary.reindex(columns=summary_columns).sort_values(
    ["anchor_name", "parent_mondo_name"], na_position="last"
)
detail_out = detail.reindex(columns=detail_columns).sort_values(
    ["anchor_name", "parent_mondo_name", "parent_child_mondo_name"], na_position="last"
)

print(
    "anchors:", len(anchors),
    "| mapped MONDO rows:", len(mapped_anchors),
    "| anchor-parent rows:", len(summary_out),
    "| parent-child audit rows:", len(detail_out),
    "| direct anchor-parent cross-split rows:", int(summary_out.anchor_parent_cross_split.sum()),
)
dataiku.Dataset("mondo_anchor_parent_summary").write_with_schema(summary_out)
dataiku.Dataset("mondo_anchor_parent_children").write_with_schema(detail_out)
