"""Act 3 — "The common programme, and what is subtype-specific"

One row per (family, subtype, gene) over the family's LEAF terms only, tagged with
how widely that gene is shared:

    scope = "common"    in every leaf's top 50 -- the family's shared programme
    scope = "specific"  in exactly ONE leaf's top 50 -- that subtype's own axis
    scope = "partial"   in some but not all

NON-LEAF TERMS ARE EXCLUDED HERE, and only here. An umbrella term is a superset of
the terms beneath it, so its "specific" genes are an artefact of the aggregation
rather than a biological claim -- and one such term in the set drags the common core
down to almost nothing. The score and overlap cards keep them, because there the
umbrella-to-subtype relationship IS the finding.

`act3_role = 'leaf'` is clinical terminality, curated in `demo_panel_config`, not
max(hop_depth): breast's leaves sit at depth 3 (HER2+, ductal, lobular) AND depth 4
(luminal A/B, TNBC), so a mechanical depth rule would drop HER2+.

What this produces, measured 2026-08-27:
    breast   6 leaves, 7 of 50 common   -- TNBC's DDR axis is the outlier
    uterine  4 leaves, 24 of 50 common  -- shared RTK/PI3K core, per-histology axes
    stomach  3 leaves, 17 of 50 common  -- neuroendocrine contributes 23 DDR genes
"""

import dataiku
import pandas as pd

TOP_N = 50

cfg = dataiku.Dataset("demo_panel_config").get_dataframe()
top = dataiku.Dataset("family_panel_top50").get_dataframe()

leaves = cfg[(cfg.act3_role == "leaf") & cfg.act3_family.notna()]
rows = []

for fam, grp in leaves.groupby("act3_family"):
    members = sorted(grp.disease)
    sets = {}
    ranks = {}
    for d in members:
        # The OVERALL top 50 only. family_panel_top50 also carries the novel-only
        # ranking (for the overlap card), and taking every row would silently widen
        # this card's basis from 50 genes per subtype to ~75.
        g = top[(top.disease == d) & (top.rank_in_disease <= TOP_N)]
        if g.empty:
            raise ValueError(f"leaf {d!r} has no top-50 rows")
        sets[d] = set(g.gene)
        ranks[d] = dict(zip(g.gene, g.rank_in_disease))
    n = len(members)
    # How many leaves does each gene appear in? That count IS the scope.
    freq = {}
    for d in members:
        for gene in sets[d]:
            freq[gene] = freq.get(gene, 0) + 1

    for d in members:
        for gene in sets[d]:
            k = freq[gene]
            rows.append({
                "act3_family": fam,
                "subtype": d,
                "gene": gene,
                "rank_in_subtype": int(ranks[d][gene]),
                "n_leaves_in_family": n,
                "n_leaves_sharing": k,
                "scope": "common" if k == n else ("specific" if k == 1 else "partial"),
            })

out = pd.DataFrame(rows).sort_values(
    ["act3_family", "subtype", "rank_in_subtype"])

assert not out.empty, "no programme rows -- are any terms tagged act3_role='leaf'?"
for fam, g in out.groupby("act3_family"):
    common = g[g.scope == "common"].gene.nunique()
    spec = g[g.scope == "specific"].gene.nunique()
    print(f"{fam}: {g.subtype.nunique()} leaves | common {common} | specific {spec}")
print(f"programme: {len(out)} rows")
dataiku.Dataset("family_panel_programme").write_with_schema(out)


