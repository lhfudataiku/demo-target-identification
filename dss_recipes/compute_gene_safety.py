# Per-gene safety attributes, keyed on gene_index — the filter-layer companion to
# `enriched_gene_druggability`.
#
# WHAT THE EXTRACTION REVEALED, and why the schema looks like this:
#
# 1. `safetyLiabilities` is a POSITIVE-ONLY annotation. Open Targets emits the field only for
#    targets that have a liability -- 943 of 78,691 -- and omits it entirely otherwise. There is
#    no "assessed and clean" state: 0 targets carry an empty-but-present list. So absence is
#    completely uninformative, and this column supports "exclude the flagged" but NOT
#    "select the safe". Anyone building a safety filter on it alone would be filtering on
#    literature attention, not on risk.
#
# 2. `constraint` (gnomAD) is the usable graded signal. It covers ~23% of all OT targets but
#    far more of the protein-coding genes we actually score -- measured below. `lof_oe_upper` is
#    LOEUF, the upper bound of the observed/expected loss-of-function ratio; the field's
#    conventional cutoff for "intolerant of loss of function" is < 0.35.
#
# So the presentable signal is a THREE-STATE column, not a boolean:
#    known_liability      -- a curated adverse effect exists          (hard evidence of risk)
#    lof_intolerant       -- no liability recorded, but human LoF is depleted  (inferred risk)
#    no_flag              -- neither                                 (absence of evidence)
# `no_flag` explicitly does not mean "safe". Keeping that in the value name rather than in a
# comment is deliberate -- a column called `is_safe` would be read as a guarantee.
#
# NODE_INDEX SAFETY: per-gene ATTRIBUTE table only. No nodes, no edges.
import dataiku
import numpy as np
import pandas as pd

LOEUF_CONSTRAINED = 0.35          # gnomAD convention

saf = dataiku.Dataset("raw_ot_safety").get_dataframe()
nodes = dataiku.Dataset("DEMO_KG_LS.graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
gn = dataiku.Dataset("DEMO_KG_LS.gene_names").get_dataframe(columns=["symbol", "entrez_id"])

# ENSG -> symbol -> entrez -> gene_index (same crosswalk as the druggability chain)
gp = nodes[nodes.node_type == "gene/protein"].copy()
gp["entrez"] = gp.node_id.astype(str)
gp["node_index"] = gp.node_index.astype(int)
gn = gn.dropna(subset=["entrez_id"]).copy()
gn["entrez"] = gn.entrez_id.astype("int64").astype(str)
sym2idx = gn.merge(gp[["entrez", "node_index"]], on="entrez")[["symbol", "node_index"]] \
            .drop_duplicates("symbol")
n_genes = len(gp)

df = saf.merge(sym2idx, on="symbol", how="inner").rename(columns={"node_index": "gene_index"})
df = df.drop_duplicates("gene_index")
print(f"OT safety rows {len(saf):,} -> mapped onto {len(df):,} of the graph's {n_genes:,} genes "
      f"({len(df)/n_genes:.1%})")

df["lof_intolerant"] = (df.lof_oe_upper < LOEUF_CONSTRAINED).astype("Int64")
df.loc[df.lof_oe_upper.isna(), "lof_intolerant"] = pd.NA

df["safety_flag"] = np.select(
    # np.select needs plain boolean ndarrays -- a nullable Int64 comparison yields pd.NA and
    # raises "should be boolean ndarray". Missing constraint means "not intolerant, as far as
    # we know", which is the correct default here given the column is named `no_flag`.
    [df.has_safety_liability.eq(1).to_numpy(dtype=bool),
     df.lof_intolerant.eq(1).fillna(False).to_numpy(dtype=bool)],
    ["known_liability", "lof_intolerant"],
    default="no_flag")

out = df[["gene_index", "has_safety_liability", "n_safety_liabilities", "safety_events",
          "safety_dosing", "lof_oe", "lof_oe_upper", "lof_bin6", "mis_oe",
          "lof_intolerant", "safety_flag"]].copy()

print(f"\n=== COVERAGE within the {n_genes:,} scored genes ===")
for c in ["has_safety_liability", "lof_oe_upper", "lof_intolerant"]:
    n = out[c].notna().sum()
    print(f"  {c:22s} non-null {n:6,d}  ({n/n_genes:.1%} of all genes)")
print(f"\n  ⚠ the liability column is positive-only: {int(out.has_safety_liability.sum()):,} flagged, "
      f"and a blank means UNKNOWN, not clean.")

print("\n=== safety_flag distribution (of mapped genes) ===")
vc = out.safety_flag.value_counts()
for k, v in vc.items():
    print(f"  {k:18s} {v:6,d}  ({v/len(out):.1%})")
print(f"  (genes with no OT safety row at all: {n_genes - len(out):,} -- also unknown)")

print("\n=== LOEUF distribution (lof_oe_upper) ===")
print(out.lof_oe_upper.describe().to_string())

dataiku.Dataset("enriched_gene_safety").write_with_schema(out)
