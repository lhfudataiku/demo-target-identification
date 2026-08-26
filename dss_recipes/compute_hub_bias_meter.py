# Hub-bias meter -- act 2's counter-measurement.
#
# Holds biology constant (KNOWN TARGETS ONLY) and asks whether the model scores
# poorly-connected true targets as highly as hubs. It does not: the least-
# connected fifth scores ~0.59 against ~0.79 for the most-connected.
#
# This existed only inside nb3b, whose own comment said "it has no recipe, so
# this notebook IS its artifact". Act 2 needs it served, and an aggregate over
# 3.96M rows cannot be computed per request.
import dataiku
import numpy as np
import pandas as pd

# The F1-optimised operating point, NOT 0.5. At 0.5 the same table reads
# 65.5% / 84.8% and the finding looks like the opposite of what it is.
THR = 0.860

# scored_champion is a 45-column CSV: a column-pruned read still streams all 45,
# so chunk it. Chunking, not sampling -- sampling would move the asserted values.
_chunks = []
for _c in dataiku.Dataset("scored_champion").iter_dataframes(
        chunksize=250_000,
        columns=["gene_index", "is_target", "proba_1", "gene_ppi_degree"]):
    _c = _c[_c.is_target == 1]
    if len(_c):
        _chunks.append(_c)
pos = pd.concat(_chunks, ignore_index=True)

# Quintiles exactly as nb6 section 5.2 computes them -- raw degree over the
# positive ROWS, duplicates dropped:
#
#     pos["q"] = pd.qcut(pos.gene_ppi_degree, 5, labels=False, duplicates="drop")
#
# NOTE the methodological quirk, deliberately preserved: rows are disease-gene
# pairs, so a gene that is a known target for 50 diseases contributes 50 rows and
# pulls the boundaries toward its degree. Deduplicating to distinct genes first
# is arguably the better statistic -- it gives Q1 0.5675 / Q5 0.7744 instead of
# 0.59 / 0.79. It is NOT used here: nb6 is the asserted source and the narrative
# quotes its figures, and a serving dataset that silently disagrees with the
# notebook is how a demo contradicts itself in the room. Change both together or
# neither.
pos["dq"] = pd.qcut(pos.gene_ppi_degree, 5, labels=False, duplicates="drop")

rows = []
for q, g in pos.groupby("dq"):
    rows.append({
        "quintile": int(q) + 1,
        "n_rows": int(len(g)),
        "n_genes": int(g.gene_index.nunique()),
        "median_degree": float(g.gene_ppi_degree.median()),
        "mean_proba": float(g.proba_1.mean()),
        "pct_predicted_positive": float(100.0 * (g.proba_1 >= THR).mean()),
    })
out = pd.DataFrame(rows).sort_values("quintile")

# Spearman between degree and score, on the same population.
rho = float(pd.Series(pos.gene_ppi_degree).rank().corr(pd.Series(pos.proba_1).rank()))
out["rho_degree_proba"] = round(rho, 4)
out["threshold"] = THR

print(out.to_string(index=False))
print(f"\nQ1 mean_proba {out.mean_proba.iloc[0]:.4f} | Q5 {out.mean_proba.iloc[-1]:.4f} | rho {rho:+.4f}")

dataiku.Dataset("hub_bias_meter").write_with_schema(out)

