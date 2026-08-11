# Disease family_id (Hetionet DO-Slim anchor rollup) -- COMPUTE.
# Mitigates train/test leakage from MONDO parent/child & sibling disease
# concepts (e.g. breast cancer <-> breast carcinoma) for the enriched graph's
# resampling split. For every disease appearing in enriched_graph_features_1,
# walk up the native (directed) MONDO parent-child hierarchy (raw_disease_disease,
# pre-reversal -- graph_edges/kg lose direction via compute_kg's reverse-all step)
# and find the nearest Hetionet DO-Slim term (mapped via mondo_references' DOID
# xrefs). Ties broken by shallowest depth, then lowest node_index. Diseases with
# no reachable anchor within MAX_DEPTH fall back to their own node_index (never
# worse than the current disease_index-based split).
#
# A full graph-wide connected-components grouping over the whole MONDO hierarchy
# was tried and rejected: >50% of eligible diseases have multiple direct MONDO
# parents, so any peer-to-peer grouping (undirected hops, directed ancestor
# checks, hub-degree-filtered variants) transitively collapses ~85-96% of the
# eligible population into one dominant component regardless of parameters.
# The fixed, small (137-term), pre-curated Hetionet anchor set avoids this: each
# disease independently looks up toward a static anchor list rather than being
# unioned with its peers, so ambiguity stays local (7.4% of diseases reach >1
# anchor) instead of cascading. See decision log for the empirical comparison.
import dataiku
import networkx as nx
import pandas as pd

MAX_DEPTH = 15

hetionet = dataiku.Dataset("hetionet_disease_slim").get_dataframe(infer_with_pandas=False)
mondo_refs = dataiku.Dataset("mondo_references").get_dataframe(infer_with_pandas=False)
nodes = dataiku.Dataset("graph_nodes").get_dataframe(infer_with_pandas=False)
raw_dd = dataiku.Dataset("raw_disease_disease").get_dataframe(infer_with_pandas=False)
target_diseases = dataiku.Dataset("enriched_graph_features_1").get_dataframe(columns=["disease_index"])
target_diseases = target_diseases.disease_index.unique()

disease_nodes = nodes[(nodes.node_type == "disease") & (nodes.node_source == "MONDO")]
id_to_index = dict(zip(disease_nodes.node_id.astype(str), disease_nodes.node_index.astype(int)))

doid_to_mondo = (mondo_refs[mondo_refs.ontology == "DOID"]
                 .groupby("ontology_id").mondo_id.apply(list).to_dict())
anchor_indices, anchor_names = set(), {}
for _, row in hetionet.iterrows():
    for mid in doid_to_mondo.get(row.doid, []):
        idx = id_to_index.get(str(mid))
        if idx is not None:
            anchor_indices.add(idx)
            anchor_names[idx] = row["name"]

raw_dd["parent_idx"] = raw_dd.parent_id.map(id_to_index)
raw_dd["child_idx"] = raw_dd.child_id.map(id_to_index)
mapped = raw_dd.dropna(subset=["parent_idx", "child_idx"]).copy()
mapped["parent_idx"] = mapped.parent_idx.astype(int)
mapped["child_idx"] = mapped.child_idx.astype(int)

Gdir = nx.DiGraph()
Gdir.add_edges_from(mapped[["child_idx", "parent_idx"]].itertuples(index=False, name=None))


def nearest_anchor(d):
    if d in anchor_indices:
        return d, 0, anchor_names.get(d)
    if d not in Gdir:
        return None, None, None
    seen = {d: 0}
    frontier = [d]
    depth = 0
    found = {}
    while frontier and depth < MAX_DEPTH:
        depth += 1
        nxt = []
        for n in frontier:
            for p in Gdir.successors(n):
                if p not in seen:
                    seen[p] = depth
                    nxt.append(p)
                    if p in anchor_indices:
                        found[p] = depth
        frontier = nxt
    if not found:
        return None, None, None
    min_depth = min(found.values())
    best = min(a for a, dep in found.items() if dep == min_depth)
    return best, min_depth, anchor_names.get(best)


rows = []
for d in target_diseases:
    d = int(d)
    anchor, depth, name = nearest_anchor(d)
    family_id = anchor if anchor is not None else d
    rows.append({"disease_index": d, "disease_family_id": int(family_id),
                 "anchor_name": name, "hop_depth": depth})

out = pd.DataFrame(rows)
print("disease_family_id rows:", out.shape,
      "| covered by an anchor:", out.anchor_name.notna().sum(),
      "| self-fallback:", out.anchor_name.isna().sum())
dataiku.Dataset("disease_family_id").write_with_schema(out)
