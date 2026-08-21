# Disease hierarchy annotation — one row per MONDO disease node, with everything needed
# to validate and redesign the family-split grouping by hand.
#
# WHY: the anchor-rollup grouping (compute_disease_family_id) is hard to audit because the
# relevant structure lives in the MONDO DAG, not in any single table. This flattens it:
# anchor status, parent/child counts, antichain relationships, eligibility, module size.
#
# NODE_INDEX SAFETY: read-only, emits a per-disease attribute table. No nodes, no edges.
#
# Direction note: reads `raw_disease_disease` (pre-reversal, explicit parent_id/child_id),
# NOT graph_edges -- compute_kg reverse-alls every relation and destroys the direction.
import dataiku
import networkx as nx
import pandas as pd

nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type", "node_name", "node_source"],
    infer_with_pandas=False)
rdd = dataiku.Dataset("raw_disease_disease").get_dataframe(infer_with_pandas=False)
het = dataiku.Dataset("hetionet_disease_slim").get_dataframe(infer_with_pandas=False)
mref = dataiku.Dataset("mondo_references").get_dataframe(infer_with_pandas=False)
mod = dataiku.Dataset("enriched_module_size_1").get_dataframe()
fam = dataiku.Dataset("disease_family_id").get_dataframe()

nodes["node_index"] = nodes.node_index.astype(int)
dis = nodes[nodes.node_type == "disease"].copy()
mondo = dis[dis.node_source == "MONDO"]
id2idx = dict(zip(mondo.node_id.astype(str), mondo.node_index))
nm = dict(zip(dis.node_index, dis.node_name))
eligible = set(mod.disease_index)
msize = dict(zip(mod.disease_index, mod.module_size))

# ---- anchors: Hetionet DOID -> MONDO -> node_index --------------------------
d2m = mref[mref.ontology == "DOID"].groupby("ontology_id").mondo_id.apply(list).to_dict()
anchor_doid, anchor_label = {}, {}
for _, r in het.iterrows():
    for mid in d2m.get(str(r.doid), []):
        i = id2idx.get(str(mid))
        if i is not None:
            anchor_doid[i] = str(r.doid)
            anchor_label[i] = r["name"]
A = set(anchor_doid)

# ---- directed hierarchy -----------------------------------------------------
rdd["p"] = rdd.parent_id.map(id2idx)
rdd["c"] = rdd.child_id.map(id2idx)
e = rdd.dropna(subset=["p", "c"]).astype({"p": int, "c": int})
UP = nx.DiGraph(); UP.add_edges_from(zip(e.c, e.p))      # child -> parent
DOWN = nx.DiGraph(); DOWN.add_edges_from(zip(e.p, e.c))  # parent -> child
kids = e.groupby("p").c.apply(set).to_dict()
pars = e.groupby("c").p.apply(set).to_dict()

famix = fam.set_index("disease_index")

rows = []
for d in sorted(dis.node_index):
    ch = kids.get(d, set())
    pa = pars.get(d, set())
    ancs = nx.descendants(UP, d) if d in UP else set()     # superclasses
    desc = nx.descendants(DOWN, d) if d in DOWN else set()  # subclasses
    anchor_desc = desc & A
    anchor_ancs = ancs & A
    f = famix.loc[d] if d in famix.index else None
    rows.append({
        "disease_index": d,
        "mondo_id": dis.loc[dis.node_index == d, "node_id"].iloc[0],
        "disease_name": nm.get(d),
        "node_source": dis.loc[dis.node_index == d, "node_source"].iloc[0],
        "module_size": msize.get(d),
        "is_eligible": int(d in eligible),
        # anchor status
        "is_anchor": int(d in A),
        "anchor_doid": anchor_doid.get(d),
        "anchor_hetionet_name": anchor_label.get(d),
        # current grouping (as built)
        "current_family_id": None if f is None else int(f.disease_family_id),
        "current_family_name": None if f is None else nm.get(int(f.disease_family_id)),
        "current_anchor_name": None if f is None else f.anchor_name,
        "current_hop_depth": None if f is None else f.hop_depth,
        # local structure
        "n_parents": len(pa),
        "n_children": len(ch),
        "n_eligible_children": len(ch & eligible),
        "n_anchor_children": len(ch & A),
        "is_parent_term": int(len(ch & eligible) >= 1),
        "parent_names": " | ".join(sorted(str(nm.get(x)) for x in pa))[:400],
        "anchor_children_names": " | ".join(sorted(str(anchor_label.get(x)) for x in (ch & A)))[:300],
        # antichain relationships (transitive)
        "n_anchor_ancestors": len(anchor_ancs),
        "n_anchor_descendants": len(anchor_desc),
        "is_ancestor_of_anchor": int(len(anchor_desc) > 0),
        "is_descendant_of_anchor": int(len(anchor_ancs) > 0),
        "antichain_ok_as_anchor": int(len(anchor_desc) == 0 and len(anchor_ancs) == 0),
        # scale of the subtree
        "n_descendants": len(desc),
        "n_eligible_descendants": len(desc & eligible),
    })

out = pd.DataFrame(rows)
print("rows:", len(out))
print("\nanchor accounting:")
print(f"  hetionet_disease_slim terms         : {len(het)}")
print(f"  resolved to a graph node_index      : {int(out.is_anchor.sum())}")
print(f"  used as nearest anchor (in family)  : {fam.anchor_name.nunique()}")
print(f"\neligible diseases                     : {int(out.is_eligible.sum())}")
print(f"  parent terms (>=1 eligible child)   : {int(out[out.is_eligible==1].is_parent_term.sum())}")
print(f"  antichain-clean (anchor-able)       : {int(out[out.is_eligible==1].antichain_ok_as_anchor.sum())}")
print("\nexisting anchors violating the antichain:")
v = out[(out.is_anchor == 1) & (out.is_ancestor_of_anchor == 1)]
for _, r in v.iterrows():
    print(f"  {r.disease_name} -> ancestor of {r.n_anchor_descendants} anchor(s)")

dataiku.Dataset("disease_hierarchy_annotation").write_with_schema(out)
