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
# Option 5 -- "lift the split key one level". The split key is NOT the anchor itself but the
# anchor's most-specific parent, so an anchor and its own parent/siblings land in ONE family.
# Motivation: `diabetes mellitus` (parent) sat in validation while `type 2 diabetes mellitus`
# (child, an anchor) sat in TRAIN -- a direct MONDO parent/child pair straddling the split,
# which is leak 3 recurring. The upward-only rollup cannot fix that: a parent can never join
# its own child-anchor's family.
#
# Measured alternatives, all rejected:
#   - merging the parent INTO the child-anchor family: clinically backwards
#   - promoting siblings to anchors: makes grouping FINER (wrong direction for a split key)
#   - adding anchor-parents to the key SET: does not merge -- an anchor is already a key,
#     so it never walks up to its parent
#
# The key set is built ONCE (lift every anchor to its most-specific parent under the cap),
# then every disease finds its nearest member of THAT set. Keying directly on the elevated
# set is what broadens coverage: a disease sitting under `diabetes mellitus` but under
# neither of its anchor children (e.g. `monogenic diabetes`) now finds the key, where the
# earlier "find anchor first, then lift" order left it as a self-fallback singleton.
# Measured: coverage 27.4% -> 34.7%, families 900 -> 841, largest family 35.
#
# SPLIT_PARENT_FANOUT_CAP keeps classificatory blobs (`hereditary disease`, 1,762 children)
# from becoming split keys; above the cap we keep the anchor itself. The cap is a sharp
# threshold, not a dial: at 50 `cancer` becomes a key and absorbs 143 diseases, and the
# breast-cancer/breast-carcinoma pair SPLITS again. 20 keeps the largest family at 35 with
# anatomically coherent top groups; 30 reaches 36.6% coverage but lets `hematologic
# disorder` grow to 55.
#
# The split key carries NO clinical meaning and is never reported -- it only has to guarantee
# that biologically-related diseases land on the same side. Scoring stays at `disease_index`
# granularity (lung adenocarcinoma != small-cell lung carcinoma for target validation).
SPLIT_PARENT_FANOUT_CAP = 20

hetionet = dataiku.Dataset("hetionet_disease_slim").get_dataframe(infer_with_pandas=False)
mondo_refs = dataiku.Dataset("mondo_references").get_dataframe(infer_with_pandas=False)
nodes = dataiku.Dataset("graph_nodes").get_dataframe(infer_with_pandas=False)
raw_dd = dataiku.Dataset("raw_disease_disease").get_dataframe(infer_with_pandas=False)
target_diseases = dataiku.Dataset("enriched_graph_features_1").get_dataframe(columns=["disease_index"])
target_diseases = target_diseases.disease_index.unique()

disease_nodes = nodes[(nodes.node_type == "disease") & (nodes.node_source == "MONDO")]
id_to_index = dict(zip(disease_nodes.node_id.astype(str), disease_nodes.node_index.astype(int)))
index_to_name = dict(zip(nodes.node_index.astype(int), nodes.node_name))

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

parents_of = mapped.groupby("child_idx").parent_idx.apply(set).to_dict()
fanout = mapped.groupby("parent_idx").child_idx.nunique().to_dict()


def lift_key(anchor):
    """Most-specific parent of `anchor` under the fanout cap; the anchor itself if none."""
    cands = [p for p in parents_of.get(anchor, set())
             if fanout.get(p, 0) <= SPLIT_PARENT_FANOUT_CAP]
    if not cands:
        return anchor, "anchor (no parent under cap)"
    return min(cands, key=lambda p: (fanout.get(p, 0), p)), "lifted to parent"


# build the elevated key set once, then key every disease against it
SPLIT_KEYS, key_origin = set(), {}
for _a in anchor_indices:
    _k, _rule = lift_key(_a)
    SPLIT_KEYS.add(_k)
    key_origin.setdefault(_k, _rule)


def nearest_split_key(d):
    """Nearest member of the elevated key set at or above d."""
    if d in SPLIT_KEYS:
        return d, key_origin.get(d, "is a split key")
    if d not in Gdir:
        return None, None
    seen, frontier, depth = {d}, [d], 0
    while frontier and depth < MAX_DEPTH:
        depth += 1
        nxt, found = [], set()
        for n in frontier:
            for p in Gdir.successors(n):
                if p not in seen:
                    seen.add(p); nxt.append(p)
                    if p in SPLIT_KEYS:
                        found.add(p)
        if found:
            return min(found), "under a split key"
        frontier = nxt
    return None, None


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
    split_key, rule = nearest_split_key(d)
    if split_key is None:
        split_key, rule = d, "self (no key above)"
    rows.append({"disease_index": d, "disease_family_id": int(family_id),
                 "anchor_name": name, "hop_depth": depth,
                 "disease_split_key": int(split_key),
                 "split_key_name": index_to_name.get(int(split_key)),
                 "split_key_rule": rule})

out = pd.DataFrame(rows)
print("disease_family_id rows:", out.shape,
      "| covered by an anchor:", out.anchor_name.notna().sum(),
      "| self-fallback:", out.anchor_name.isna().sum())
print("families (old anchor key) :", out.disease_family_id.nunique())
print("families (lifted split key):", out.disease_split_key.nunique())
print(out.split_key_rule.value_counts().to_string())
dataiku.Dataset("disease_family_id").write_with_schema(out)
