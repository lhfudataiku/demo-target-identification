# WHY THE MODEL CANNOT SEE SOME APPROVED DRUG TARGETS -- diagnosis before any retraining.
#
# THE FINDING THAT PROMPTED THIS (§8.13): for triple-negative breast carcinoma, TACSTD2 (TROP2) and
# CD274/PDCD1 are absent from the candidate pool ENTIRELY, while sacituzumab govitecan and
# pembrolizumab are both approved in that disease. Unreachable, not merely low-ranked.
#
# THE MECHANISM, read off the filter (`filter_has_path_evidence`):
#     isNonBlank(dwpc_GGD) || isNonBlank(dwpc_GPGD) || isNonBlank(dwpc_GCD)
# All three routes pass THROUGH A GENE ALREADY KNOWN FOR THAT DISEASE. So the pool is the
# PPI/pathway neighbourhood of the known set, and its size scales with how well-annotated the disease
# already is. Triple-negative's known set is 8 DNA-repair genes; a cell-surface glycoprotein has no
# PPI or pathway edge to any of them. The exclusion is structural, not a ranking artifact.
#
# WHAT THIS RECIPE ANSWERS, none of which requires retraining:
#   1. THE CEILING. What fraction of curated target-disease pairs is outside the pool? That is a hard
#      cap on recall that no re-ranking can move.
#   2. WHY each one is missing, split into causes that imply DIFFERENT fixes:
#        gene absent from graph          -> ingestion problem
#        gene has no PPI edges           -> interactome coverage problem
#        reachable for a SIBLING disease -> the disease's known set is too small: borrowing the family
#                                           pool would rescue it WITHOUT retraining
#        reachable for no disease at all -> genuinely disconnected; only embeddings reach it
#   3. IS IT BIASED BY MODALITY? Hypothesis stated up front: unreachable targets should be enriched
#      for ANTIBODY-tractable cell-surface proteins, because a PPI/pathway graph under-represents
#      surface and immune biology. TROP2 and PD-L1 are both antibody targets, which is a sample of
#      two and worth nothing until measured across all diseases.
#   4. IS THE POOL ITSELF CIRCULAR? `dwpc_GCD` holds only 42,227 rows and §5.2 flags it as
#      "load-bearing and invisible". If C is Compound, then the pool admits pairs BECAUSE a drug links
#      them, and every drug-based evaluation in §8 is partly circular with the pool definition. This
#      has to be checked, not assumed.
import dataiku
import numpy as np
import pandas as pd

SCORE_MIN = 0.8   # the curated therapeutic label threshold adopted in §8.1

nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_name", "node_type"], infer_with_pandas=False)
nodes["node_index"] = nodes.node_index.astype(int)
G = nodes[nodes.node_type == "gene/protein"]
D = nodes[nodes.node_type == "disease"]
gname = dict(zip(G.node_index, G.node_name))
dname = dict(zip(D.node_index, D.node_name))
gene_nodes = set(G.node_index)

# ---- the pool, as actually used for training/scoring -----------------------------------
pool = dataiku.Dataset("enriched_graph_features_candidate_psplit").get_dataframe(
    columns=["gene_index", "disease_index", "disease_family_id"])
pool["gene_index"] = pool.gene_index.astype(int)
pool["disease_index"] = pool.disease_index.astype(int)
pool_pairs = set(map(tuple, pool[["disease_index", "gene_index"]].values))
gene_reachable_any = set(pool.gene_index.unique())
# family -> set of genes reachable for ANY member disease of that family
fam_genes = pool.groupby("disease_family_id").gene_index.apply(set).to_dict()
dis_family = dict(zip(pool.disease_index, pool.disease_family_id))
pool_size = pool.groupby("disease_index").size().to_dict()
eligible = set(pool.disease_index.unique())
print(f"pool: {len(pool):,} pairs | {len(eligible)} diseases | "
      f"{len(gene_reachable_any):,} distinct genes reachable somewhere")

# ---- PPI degree for every gene, including ones the pool never sees ---------------------
edges = dataiku.Dataset("graph_edges").get_dataframe(
    columns=["relation", "x_index", "y_index"], infer_with_pandas=False)
edges["x_index"] = edges.x_index.astype(int)
edges["y_index"] = edges.y_index.astype(int)
ppi = edges[edges.relation.astype(str).str.contains("protein_protein", case=False, na=False)]
deg = pd.concat([ppi.x_index, ppi.y_index]).value_counts().to_dict()
print(f"PPI edges: {len(ppi):,} | genes with >=1 PPI edge: {len(deg):,} of {len(gene_nodes):,}")

# ---- the curated therapeutic truth ----------------------------------------------------
kd = dataiku.Dataset("known_drug_truth").get_dataframe()
kd = kd[kd.score >= SCORE_MIN].copy()
kd["disease_index"] = kd.disease_index.astype(int)
kd["gene_index"] = kd.gene_index.astype(int)
kd = kd[kd.disease_index.isin(eligible)].drop_duplicates(["disease_index", "gene_index"])
print(f"curated pairs at score>={SCORE_MIN} on eligible diseases: {len(kd):,} "
      f"over {kd.disease_index.nunique()} diseases")

# ---- 4. is the pool circular? does GCD look drug-mediated? -----------------------------
gcd = dataiku.Dataset("enriched_dwpc_GCD").get_dataframe(columns=["gene_index", "disease_index"])
gcd["gene_index"] = gcd.gene_index.astype(int)
gcd["disease_index"] = gcd.disease_index.astype(int)
gcd_pairs = set(map(tuple, gcd[["disease_index", "gene_index"]].values))
dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
gc_, tc_ = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
gid = dict(zip(G.node_name.astype(str), G.node_index))  # unused; kept for clarity
dp2 = dp.copy()
dp2["drug"] = dp2[gc_].astype(str)
nid_by_id = dict(zip(nodes.node_index, nodes.node_index))  # placeholder
# map drug->gene via node_id, mirroring the other recipes
nodes_id = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
nodes_id["node_index"] = nodes_id.node_index.astype(int)
nodes_id["node_id"] = nodes_id.node_id.astype(str)
gmap = dict(zip(nodes_id[nodes_id.node_type == "gene/protein"].node_id,
                nodes_id[nodes_id.node_type == "gene/protein"].node_index))
dmap = dict(zip(nodes_id[nodes_id.node_type == "disease"].node_id,
                nodes_id[nodes_id.node_type == "disease"].node_index))
dp2["gene_index"] = dp2[tc_].astype(str).map(gmap)
dp2 = dp2.dropna(subset=["gene_index"])[["drug", "gene_index"]]
sub = dd[dd.relation.astype(str).str.fullmatch("indication|drug_investigated_for",
                                               case=False, na=False)].copy()
dc_, xc_ = ("x_id", "y_id") if (sub.x_type == "drug").any() else ("y_id", "x_id")
sub["drug"] = sub[dc_].astype(str)
sub["disease_index"] = sub[xc_].astype(str).map(dmap)
drug_pairs = set(map(tuple, (sub.dropna(subset=["disease_index"])[["drug", "disease_index"]]
                             .merge(dp2, on="drug")[["disease_index", "gene_index"]]
                             .astype(int).drop_duplicates().values)))
inter = len(gcd_pairs & drug_pairs)
print(f"\n=== 4. IS THE POOL CIRCULAR WITH THE DRUG LABEL? ===")
print(f"  dwpc_GCD pairs: {len(gcd_pairs):,} | drug-mediated (disease,gene) pairs: {len(drug_pairs):,}")
print(f"  overlap: {inter:,} = {100*inter/max(len(gcd_pairs),1):.1f}% of GCD")
print("  If that share were near 100%, C would be Compound and every drug-based metric in section 8")
print("  would be partly circular with the pool. Read the number, do not assume it.")
gcd_only = gcd_pairs - (set(map(tuple, dataiku.Dataset("enriched_dwpc_GGD")
                               .get_dataframe(columns=["disease_index", "gene_index"])
                               .astype(int).values)))
print(f"  GCD pairs not also carried by GGD: {len(gcd_only):,}")

# ---- 1 + 2. the ceiling, and why -------------------------------------------------------
kd["in_pool"] = [(d, g) in pool_pairs for d, g in zip(kd.disease_index, kd.gene_index)]
n_tot, n_in = len(kd), int(kd.in_pool.sum())
print(f"\n=== 1. THE RECALL CEILING ===")
print(f"  curated pairs in pool : {n_in:,} / {n_tot:,} = {100*n_in/n_tot:.1f}%")
print(f"  UNREACHABLE BY DESIGN : {n_tot-n_in:,} = {100*(n_tot-n_in)/n_tot:.1f}%")
print(f"  No re-ranking, threshold or feature can recover these.")

miss = kd[~kd.in_pool].copy()


def reason(d, g):
    if g not in gene_nodes:
        return "gene absent from graph"
    if deg.get(g, 0) == 0:
        return "gene has no PPI edges"
    fam = dis_family.get(d)
    if fam is not None and g in fam_genes.get(fam, set()):
        return "reachable via a SIBLING disease (family rescue possible)"
    if g in gene_reachable_any:
        return "reachable for other diseases, not this one"
    return "reachable for no disease at all"


miss["reason"] = [reason(d, g) for d, g in zip(miss.disease_index, miss.gene_index)]
print(f"\n=== 2. WHY THE {len(miss):,} UNREACHABLE PAIRS ARE UNREACHABLE ===")
rc = miss.reason.value_counts()
for k, v in rc.items():
    print(f"  {k:52s} {v:6,d}  ({100*v/len(miss):5.1f}%)")

# ---- 3. modality bias ------------------------------------------------------------------
dr = dataiku.Dataset("enriched_gene_druggability_v2").get_dataframe()
keep = [c for c in ["gene_index", "ot_sm_tractable", "ot_ab_tractable", "ot_class_l1",
                    "druggability_class"] if c in dr.columns]
dr = dr[keep].copy()
dr["gene_index"] = dr.gene_index.astype(int)
kd2 = kd.merge(dr, on="gene_index", how="left")
print(f"\n=== 3. MODALITY BIAS -- is the unreachable set different in KIND? ===")
for col in ["ot_ab_tractable", "ot_sm_tractable"]:
    if col not in kd2.columns:
        continue
    a = kd2[kd2.in_pool][col].fillna(0).astype(float).mean()
    b = kd2[~kd2.in_pool][col].fillna(0).astype(float).mean()
    print(f"  {col:18s} reachable {100*a:5.1f}%   unreachable {100*b:5.1f}%   "
          f"ratio {(b/a if a else float('nan')):.2f}x")
if "ot_class_l1" in kd2.columns:
    print("\n  target class, share of each group:")
    ca = kd2[kd2.in_pool].ot_class_l1.fillna("(none)").value_counts(normalize=True)
    cb = kd2[~kd2.in_pool].ot_class_l1.fillna("(none)").value_counts(normalize=True)
    cls = pd.DataFrame({"reachable_pct": 100 * ca, "unreachable_pct": 100 * cb}).fillna(0)
    cls["over_rep"] = cls.unreachable_pct / cls.reachable_pct.replace(0, np.nan)
    print(cls.sort_values("unreachable_pct", ascending=False).head(10)
          .to_string(float_format=lambda x: f"{x:.1f}"))

# ---- per-disease coverage: shippable as a trust indicator today ------------------------
per = (kd.groupby("disease_index")
         .agg(n_curated=("in_pool", "size"), n_reachable=("in_pool", "sum")).reset_index())
per["n_unreachable"] = per.n_curated - per.n_reachable
per["coverage_pct"] = 100 * per.n_reachable / per.n_curated
per["pool_size"] = per.disease_index.map(pool_size)
per["disease"] = per.disease_index.map(dname)
per["recall_ceiling"] = per.coverage_pct / 100
per = per.sort_values("coverage_pct")
print(f"\n=== per-disease coverage: WORST 15 (a shippable trust warning) ===")
print(per.head(15)[["disease", "pool_size", "n_curated", "n_reachable", "coverage_pct"]]
      .to_string(index=False, float_format=lambda x: f"{x:.1f}"))
print(f"\n  diseases at 100% coverage: {int((per.coverage_pct >= 99.99).sum())} of {len(per)}")
print(f"  diseases below 50% coverage: {int((per.coverage_pct < 50).sum())}")

# does pool size predict coverage? -> the "model not applicable below N" rule
if len(per) > 10:
    sp = per[["pool_size", "coverage_pct"]].dropna()
    r = np.corrcoef(sp.pool_size.rank(), sp.coverage_pct.rank())[0, 1]
    print(f"  Spearman(pool_size, coverage) = {r:+.3f}  "
          f"-> {'sparse diseases ARE the affected ones' if r > 0.3 else 'not simply a size effect'}")

dataiku.Dataset("pool_reachability").write_with_schema(per)
# `pool_unreachable_targets` dropped 2026-08-25: nothing read it. The WHY-unreachable breakdown it
# summarised is still printed above from `miss`, which is where the analysis actually lives.


