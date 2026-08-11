# Gene localization flags — druggability proxy from GO cellular_component.
#
# WHY: the model ranks non-druggable secreted peptide ligands (GCG/GIP/IAPP) ABOVE the
# membrane receptors that are the actual known targets (GLP1R/GIPR/CALCR) — see
# TARGET_PRIORITIZER §10.3. Network similarity cannot fix this; it needs a target-class
# signal. GO cellular_component is already in the graph, so this costs no new data source.
#
# NODE_INDEX SAFETY: this recipe only READS the graph and emits a per-gene attribute table
# keyed on gene_index. It adds no nodes and no edges, so `compute_kg`'s positional
# node_index assignment is untouched. Never model these as edges -- that would reshuffle
# every node_index and invalidate the feature tables, the Kuzu snapshot and every model.
#
# HIERARCHY DIRECTION: `cellcomp_cellcomp` in graph_edges is reverse-all'd, so parent->child
# direction is gone. We read `raw_go_hierarchy` (pre-reversal, explicit parent_id/child_id)
# instead -- the same reason `compute_disease_family_id` reads `raw_disease_disease`.
# Propagation is DOWNWARD from each anchor: a gene annotated to "integral component of
# plasma membrane" must count as plasma-membrane.
import dataiku
import numpy as np
import pandas as pd

# GO ids are stored WITH the "GO:" prefix in node_id.
MEMBRANE_ANCHORS = ["GO:0005886",   # plasma membrane
                    "GO:0009986"]   # cell surface
SECRETED_ANCHORS = ["GO:0005576"]   # extracellular region

nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
edges = dataiku.Dataset("graph_edges").get_dataframe(columns=["relation", "x_index", "y_index"])
hier = dataiku.Dataset("raw_go_hierarchy").get_dataframe(infer_with_pandas=False)

nodes["node_index"] = nodes.node_index.astype(int)
genes = set(nodes.loc[nodes.node_type == "gene/protein", "node_index"])
cc = nodes[nodes.node_type == "cellular_component"]
cc_id_to_idx = dict(zip(cc.node_id.astype(str), cc.node_index))

# ---- descendant closure over the DIRECTED cellcomp hierarchy -------------------
cc_hier = hier[hier.namespace == "cellcomp"]
children = cc_hier.groupby("parent_id").child_id.apply(list).to_dict()


def descendants(anchor_ids):
    """All GO ids at or below the anchors (BFS down parent->child)."""
    seen, frontier = set(anchor_ids), list(anchor_ids)
    while frontier:
        nxt = []
        for term in frontier:
            for c in children.get(term, []):
                if c not in seen:
                    seen.add(c)
                    nxt.append(c)
        frontier = nxt
    return seen


mem_terms = descendants(MEMBRANE_ANCHORS)
sec_terms = descendants(SECRETED_ANCHORS)
print(f"membrane term closure: {len(mem_terms)} GO terms (from {len(MEMBRANE_ANCHORS)} anchors)")
print(f"secreted term closure: {len(sec_terms)} GO terms (from {len(SECRETED_ANCHORS)} anchors)")

ccp = edges[edges.relation == "cellcomp_protein"]


def genes_annotated_to(go_ids):
    idx = {cc_id_to_idx[g] for g in go_ids if g in cc_id_to_idx}
    hit = set(ccp.loc[ccp.x_index.isin(idx), "y_index"]) | set(ccp.loc[ccp.y_index.isin(idx), "x_index"])
    return hit & genes


mem = genes_annotated_to(mem_terms)
sec = genes_annotated_to(sec_terms)

all_genes = sorted(genes)
out = pd.DataFrame({"gene_index": all_genes})
out["is_plasma_membrane"] = np.where(out.gene_index.isin(mem), 1, 0)
out["is_secreted"] = np.where(out.gene_index.isin(sec), 1, 0)
# the discriminating signal: receptors are membrane WITHOUT being secreted
out["is_membrane_only"] = ((out.is_plasma_membrane == 1) & (out.is_secreted == 0)).astype(int)
out["localization_class"] = np.select(
    [(out.is_plasma_membrane == 1) & (out.is_secreted == 0),
     (out.is_secreted == 1) & (out.is_plasma_membrane == 0),
     (out.is_plasma_membrane == 1) & (out.is_secreted == 1)],
    ["membrane", "secreted", "membrane_and_secreted"], default="intracellular_or_unannotated")

print(f"\ngenes: {len(out):,}")
print(out.localization_class.value_counts().to_string())
dataiku.Dataset("enriched_gene_localization").write_with_schema(out)
