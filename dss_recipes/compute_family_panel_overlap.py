"""Act 3 — "How much do the subtypes overlap?"

One row per pair of terms WITHIN a family, PARENTS INCLUDED. Keeping the parents in
is the point of the card: a parent term is largely a blend of its children, and the
numbers say so -- `gastric adenocarcinoma` shares 96% of its top 50 with its parent
`gastric carcinoma`, while two terms at the same depth can share only 28%
(luminal A vs luminal B).

`depth_gap` is what makes the card an argument rather than a matrix. Overlap tracks
ontology distance (Spearman -0.38 over 134 pairs, measured 2026-08-27):

    gap 0 (same depth)    55%
    gap 1 (parent-child)  50%
    gap 2                 44%
    gap 3                 28%

So order the display by `hop_depth`, not by name or by overlap -- the parent-child
blocks then sit together and the gradient is visible without being narrated.
"""

import itertools

import dataiku
import pandas as pd

NEAR_DUP = 0.6      # above this, two terms tell the same story

cfg = dataiku.Dataset("demo_panel_config").get_dataframe()
top = dataiku.Dataset("family_panel_top50").get_dataframe()

# Act 3 terms, PLUS any leaf regardless of the usable floor.
#
# `in_act3` carries n_pos >= 50, and that floor exists to stop us quoting an
# untrustworthy AUC -- it says nothing about comparing two gene LISTS. Gating this
# card on it dropped triple-negative breast (8 positives), which is the most
# separable term in the family (14-19% against everything) and the pair nb4 and nb6
# assert on. Overlap is valid wherever a top 50 exists.
a3 = cfg[cfg.act3_family.notna() & (cfg.in_act3 | (cfg.act3_role == "leaf"))]
depth = dict(zip(a3.disease, a3.hop_depth))
role = dict(zip(a3.disease, a3.act3_role))
sub = top[top.disease.isin(a3.disease)]
TOP_N = 50
# all-gene overlap uses the overall top 50 ...
sets = {d: set(g[g.rank_in_disease <= TOP_N].gene) for d, g in sub.groupby("disease")}
# Overlap restricted to NOVEL candidates. This is the measure nb4 and nb6 assert on
# ("HER2+ vs TNBC novel_overlap = 2") and it is not the same question as all-gene
# overlap: two subtypes can share most of their known targets and still disagree
# completely about what to look at next. Carried here so this dataset is a superset
# of the retired breast_panel_overlap.
# ... and novel overlap uses the top 50 of the NOVEL ranking, which is deeper.
novel = {d: set(g[g.novel_rank <= TOP_N].gene) for d, g in sub.groupby("disease")}

rows = []
for fam, grp in a3.groupby("act3_family"):
    members = sorted(d for d in grp.disease if d in sets)
    for a, b in itertools.combinations(members, 2):
        inter = len(sets[a] & sets[b])
        union = len(sets[a] | sets[b])
        rows.append({
            "act3_family": fam,
            "disease_a": a, "disease_b": b,
            "depth_a": depth[a], "depth_b": depth[b],
            "depth_gap": abs(depth[a] - depth[b]),
            "role_a": role[a], "role_b": role[b],
            "shared_genes": inter,
            "all_overlap": inter,                       # nb4/nb6 name for shared_genes
            "novel_overlap": len(novel.get(a, set()) & novel.get(b, set())),
            "jaccard_top50": round(inter / union, 4) if union else 0.0,
            "near_duplicate": (inter / union) > NEAR_DUP if union else False,
            # Depth equality, nothing more -- named here so the frontend does
            # not re-derive it. The previous "sibling" / "ancestor_descendant"
            # claimed ontology this cannot establish: two terms at different
            # depths may sit on different branches, and be neither ancestor nor
            # descendant of each other.
            "pair_kind": "same_depth" if depth[a] == depth[b] else "different_depth",
        })

out = pd.DataFrame(rows).sort_values(
    ["act3_family", "depth_a", "depth_b", "disease_a", "disease_b"])

assert not out.empty, "no overlap pairs -- is demo_panel_config populated?"
for fam in out.act3_family.unique():
    n = (out.act3_family == fam).sum()
    print(f"{fam}: {n} pairs | mean {out[out.act3_family==fam].jaccard_top50.mean():.3f} "
          f"| near-dups {int(out[out.act3_family==fam].near_duplicate.sum())}")
print(f"overlap: {len(out)} rows")
dataiku.Dataset("family_panel_overlap").write_with_schema(out)



