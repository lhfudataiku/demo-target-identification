# Does the model DISTINGUISH histological subtypes, or just re-rank the same gene list?
#
# WHY: every disease in the lung-cancer family scores AUC 0.91-0.96,
# and `lung adenocarcinoma` (0.938) vs `small cell lung carcinoma` (0.944) are within noise.
# Equal AUC is not the question that matters for target validation -- the question is whether
# the top-ranked GENES differ. If two histologies with different pathophysiology and different
# standard-of-care return the same 50 genes, the model is scoring "lung cancer" as one entity
# and the subtype granularity the persona story depends on is cosmetic.
#
# Emits the top 50 per respiratory-cancer disease plus a pairwise Jaccard matrix on those lists.
import dataiku
import pandas as pd
from itertools import combinations

# Select the LUNG CANCER FAMILY, not a split key. In the reference graph the lung subtypes
# shared the `respiratory system cancer` split key, so that key was the right selector. In the
# rebuilt graph they roll up to `thoracic cancer` instead -- the elevation step picks among a
# disease's multiple parents by lowest node_index, and renumbering flipped that choice -- which
# merges lung with BREAST. Selecting on the split key would therefore compare breast lists to
# lung lists, a different question. The anchor-level family is the stable way to say
# "lung cancer and its histological subtypes".
KEY = 52236           # disease_family_id: lung cancer
TOPN = 50
SCORE = "proba_1"

# Dataset validation_set_2_scored renamed to scored_m2 by liheng.fu@dataiku.com on 2026-08-13 12:19:46
df = dataiku.Dataset("scored_champion").get_dataframe(
    columns=["disease_index", "gene_index", "is_target", "disease_family_id", SCORE])
df = df[df.disease_family_id == KEY]

nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_name", "node_type"], infer_with_pandas=False)
nodes["node_index"] = nodes.node_index.astype(int)
gname = dict(zip(nodes[nodes.node_type == "gene/protein"].node_index,
                 nodes[nodes.node_type == "gene/protein"].node_name))
dname = dict(zip(nodes[nodes.node_type == "disease"].node_index,
                 nodes[nodes.node_type == "disease"].node_name))

tops = {}
rows = []
for d, g in df.groupby("disease_index"):
    t = g.nlargest(TOPN, SCORE).copy()
    t["rank_in_disease"] = range(1, len(t) + 1)
    t["disease_name"] = dname.get(d)
    t["gene_name"] = t.gene_index.map(gname)
    tops[d] = list(t.gene_name)
    rows.append(t)
out = pd.concat(rows, ignore_index=True)

sizes = df.groupby("disease_index").is_target.sum().to_dict()
big = sorted([d for d in tops if sizes.get(d, 0) >= 50], key=lambda d: -sizes[d])[:10]

print(f"top-{TOPN} overlap between respiratory-cancer subtypes "
      f"(shared genes out of {TOPN}):\n")
hdr = "".join(f"{str(dname.get(d))[:14]:>16s}" for d in big)
print(f"{'':34s}{hdr}")
for a in big:
    line = f"{str(dname.get(a))[:32]:34s}"
    for b in big:
        line += f"{'--' if a == b else len(set(tops[a]) & set(tops[b])):>16}"
    print(line)

print("\npairwise Jaccard on the top-50 lists:")
js = []
for a, b in combinations(big, 2):
    sa, sb = set(tops[a]), set(tops[b])
    js.append(len(sa & sb) / len(sa | sb))
    print(f"  {str(dname.get(a))[:30]:32s} vs {str(dname.get(b))[:30]:32s} "
          f"{len(sa & sb):2d}/50  J={js[-1]:.3f}")
print(f"\n  mean pairwise Jaccard: {sum(js)/len(js):.3f}   "
      f"(1.0 = identical gene lists, i.e. no subtype resolution)")

dataiku.Dataset("lung_granularity_check").write_with_schema(out)




