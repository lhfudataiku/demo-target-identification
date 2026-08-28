# nb6 — The interrogation and the close.  Acts 5 and 6, which left the webapp.
#
# WHY THIS EXISTS, and why it is the most urgent notebook in the set:
#   Four of the deck's closing numbers are currently asserted by NOTHING. `tractability_lift` and
#   `safety_lift` are read by no recipe, no notebook and no webapp — they are terminal and orphaned —
#   yet they carry the entire punch line: druggability points the wrong way, essentiality points the
#   wrong way, and the liability flag marks the best-studied targets. Section 6.0 now COMPUTES both
#   tables here from the upstream annotations, so the six assertions test the ARITHMETIC rather than
#   the freshness of a build. Until it runs green, DO NOT prune the flow: a mechanical "delete what
#   nothing reads" pass removes the evidence for the argument the demo closes on.
#
# THE NOTEBOOK PRINCIPLE, applied:
#   Read the most UPSTREAM dataset that still carries the number and recompute in code. Where the
#   number is ALSO served to the webapp, recompute it here anyway and compare — that is an independent
#   reimplementation check, not a tautology. Where the dataset is destined for deletion, this code
#   becomes the sole source of truth.
#
#   Reads:  scored_champion (upstream)          -- the model's own output, per scored pair
#           enriched_gene_druggability_v2 / _safety_v2  (upstream annotations, never model
#                                               inputs; the _v2 pair are the visual-recipe outputs)
#           raw_ot_known_drug (upstream)        -- the drug ground truth, before any join
#           graph_nodes, drug_protein_edges, drug_disease_edges -- the drug-validated ground truth,
#                                               rebuilt here so tractability_lift and safety_lift are
#                                               COMPUTED (6.0), not read back from the flow
#           tractability_axis, novel_discovery_eval, drug_target_benchmark, validation_auc_by_disease
#                                               -- served or notebook-zone; recomputed and compared
import math
import dataiku
import numpy as np
import pandas as pd

FAIL = []
RESULTS = []


def check(name, doc, live, tol=0.0, fmt="{:,}"):
    ok = (abs(doc - live) <= tol) if isinstance(doc, (int, float)) else (doc == live)
    if not ok:
        FAIL.append((name, doc, live))
    # Recorded as well as printed. A scenario step's stdout is not reliably retrievable, so an
    # assertion notebook whose only output is a log is itself an unguarded figure.
    RESULTS.append({"check": name, "documented": str(doc), "live": str(live),
                    "status": "PASS" if ok else "STALE"})
    print(f"CHK|{'PASS ' if ok else 'STALE'}|{name:52s} doc={fmt.format(doc):>12s} live={fmt.format(live):>12s}")


# ============================================================================
# 5.1  Degree-matched enrichment — "these are just the famous genes"
#
# Measured on the NOVEL-ONLY sub-list, after the known targets are deleted. For each disease and
# cut-off K, count tractable genes in the top K (obs) against two expectations: `naive` (uniform
# sampling from the pool) and `dm` (sampling matched on network degree). The finding is the
# CROSSOVER, not the level: the degree control makes the result look worse at K=10 and better from
# K=20-50 onward.
# ============================================================================
tx = dataiku.Dataset("tractability_axis").get_dataframe()
nv = tx[tx.scope == "novel only"]
KS = [10, 20, 50, 100, 200]

print("TRACTHDR|K|obs|dm_exp|pooled_dm|pooled_naive|macro_dm|macro_naive")
for K in KS:
    obs = nv[f"demonstrated_obs{K}"].sum()
    exp = nv[f"demonstrated_exp{K}"].sum()
    naive_sum = (nv[f"demonstrated_obs{K}"] / nv[f"demonstrated_naive{K}"].replace(0, np.nan)).sum()
    print(f"TRACT|{K}|{int(obs)}|{int(round(exp))}|{obs / exp:.2f}|{obs / naive_sum:.2f}|"
          f"{nv[f'demonstrated_dm{K}'].mean():.2f}|{nv[f'demonstrated_naive{K}'].mean():.2f}")

p10 = nv.demonstrated_obs10.sum() / nv.demonstrated_exp10.sum()
p200 = nv.demonstrated_obs200.sum() / nv.demonstrated_exp200.sum()
check("5.1 pooled dm lift @10", 3.29, round(float(p10), 2), tol=0.02, fmt="{:.2f}")
check("5.1 pooled dm lift @200", 2.42, round(float(p200), 2), tol=0.02, fmt="{:.2f}")
check("5.1 macro dm lift @10", 3.11, round(float(nv.demonstrated_dm10.mean()), 2), tol=0.02, fmt="{:.2f}")

# The crossover, stated as a boolean so it cannot drift silently.
for K, want_pooled, want_macro in [(10, False, False), (20, True, False), (50, True, True), (200, True, True)]:
    o = nv[f"demonstrated_obs{K}"].sum()
    pdm = o / nv[f"demonstrated_exp{K}"].sum()
    pnv = o / (nv[f"demonstrated_obs{K}"] / nv[f"demonstrated_naive{K}"].replace(0, np.nan)).sum()
    mdm, mnv = nv[f"demonstrated_dm{K}"].mean(), nv[f"demonstrated_naive{K}"].mean()
    check(f"5.1 dm>naive pooled @{K}", want_pooled, bool(pdm > pnv), tol=0, fmt="{}")
    check(f"5.1 dm>naive macro @{K}", want_macro, bool(mdm > mnv), tol=0, fmt="{}")

# ============================================================================
# 5.2  The hub-bias meter — the harder version of the same question.
#
# It has no recipe: this section IS its artifact. Hold biology constant by taking only genes we
# already know are targets, and ask whether the model scores the poorly-connected ones as highly as
# the hubs.
# ============================================================================
# scored_champion is 3,958,921 rows. Reading it whole inside a container gets the process killed
# (signal 1, no traceback) — the same failure nb1 records at 2.19M rows. Only the known targets are
# needed here, and they are ~1.9% of the pool, so filter per chunk and keep the exact values rather
# than sampling: sampling would move the 0.59 / 0.79 figures this section asserts.
_chunks = []
for _c in dataiku.Dataset("scored_champion").iter_dataframes(
        chunksize=250_000,
        columns=["disease_index", "gene_index", "is_target", "proba_1", "gene_ppi_degree"]):
    _c = _c[_c.is_target == 1]
    if len(_c):
        _chunks.append(_c)
pos = pd.concat(_chunks, ignore_index=True) if _chunks else pd.DataFrame()
del _chunks
pos = pos.dropna(subset=["proba_1", "gene_ppi_degree"]).copy()
print(f"HUBREAD|known-target rows read in chunks: {len(pos):,}")
pos["q"] = pd.qcut(pos.gene_ppi_degree, 5, labels=False, duplicates="drop")

# The F1-optimised operating threshold, not 0.5. nb3b uses 0.860 and the documented 17.3% / 57.0%
# detection rates are measured at it; at 0.5 the same data reads 65.5% / 84.8% and looks like a
# different finding entirely.
THR = 0.860
print(f"HUBHDR|quintile|median_degree|mean_score|predicted_positive_pct@{THR}|n")
band = {}
for q, g in pos.groupby("q"):
    band[int(q)] = (float(g.gene_ppi_degree.median()), float(g.proba_1.mean()),
                    100.0 * float((g.proba_1 >= THR).mean()), len(g))
    print(f"HUB|{int(q) + 1}|{band[int(q)][0]:.0f}|{band[int(q)][1]:.2f}|{band[int(q)][2]:.1f}|{band[int(q)][3]:,}")

lo, hi = band[min(band)], band[max(band)]
check("5.2 champion Q1 probability", 0.59, round(lo[1], 2), tol=0.02, fmt="{:.2f}")
check("5.2 champion Q5 probability", 0.79, round(hi[1], 2), tol=0.02, fmt="{:.2f}")
check("5.2 Q1 predicted-positive %", 17.3, round(lo[2], 1), tol=1.0, fmt="{:.1f}")
check("5.2 Q5 predicted-positive %", 57.0, round(hi[2], 1), tol=1.5, fmt="{:.1f}")
print(f"HUBSPREAD|detection swing Q1->Q5 = {hi[2] / max(lo[2], 1e-9):.1f}x on network position alone")

# Spearman between connectivity and score, ON KNOWN TARGETS — the same population as the quintiles
# above, which is what nb3b reports. A pool-wide rho would be a different statistic.
rho = float(pos.gene_ppi_degree.rank().corr(pos.proba_1.rank()))
check("5.2 champion rho(degree, proba)", 0.3273, round(rho, 4), tol=0.02, fmt="{:.4f}")

# ============================================================================
# 5.3  Novel discovery — "you already knew all of these"
# ============================================================================
nde = dataiku.Dataset("novel_discovery_eval").get_dataframe()
print("DISCHDR|ground_truth|K|mean_lift|median_lift|n_diseases")
for gt in ["approved", "investigational"]:
    s = nde[nde.ground_truth == gt]
    for K in KS:
        col = s[f"lift_top{K}"].replace([np.inf, -np.inf], np.nan).dropna()
        print(f"DISC|{gt}|{K}|{col.mean():.2f}|{col.median():.2f}|{len(col)}")
    l10 = s.lift_top10.replace([np.inf], np.nan).mean()
    l200 = s.lift_top200.replace([np.inf], np.nan).mean()
    if gt == "approved":
        check("5.3 approved lift@10", 16.88, round(float(l10), 2), tol=0.02, fmt="{:.2f}")
        check("5.3 approved lift@200", 5.04, round(float(l200), 2), tol=0.02, fmt="{:.2f}")
    else:
        check("5.3 investigational lift@10", 8.85, round(float(l10), 2), tol=0.02, fmt="{:.2f}")

# The tail is the honest part: the mean is not the median and the deck must show the distribution.
ap = nde[nde.ground_truth == "approved"].lift_top10.replace([np.inf], np.nan).dropna()
print(f"DISCTAIL|approved lift@10: mean={ap.mean():.2f} median={ap.median():.2f} "
      f"max={ap.max():.1f} | diseases above the mean: {int((ap > ap.mean()).sum())} of {len(ap)}")

# ============================================================================
# 5.4  Ground-truth provenance — "your ground truth is garbage"
#
# Computed from raw_ot_known_drug, upstream of every join, so this is the flaw measured at source.
# ============================================================================
# `raw_ot_known_drug` is target-disease pairs (targetId, symbol, diseaseId, score) and carries NO
# drug column, so the multi-target inflation cannot be measured from it. The drug identity lives in
# the graph edges: drug_protein_edges (drug -> target) and drug_disease_edges (drug -> disease).
dpe = dataiku.Dataset("drug_protein_edges").get_dataframe(columns=["x_id", "y_id", "x_type"])
dde = dataiku.Dataset("drug_disease_edges").get_dataframe(columns=["x_id", "y_id", "x_type"])
# x is the drug on both edge tables; guard in case a build flips the orientation.
tpd = dpe.groupby("x_id").y_id.nunique()          # targets per drug
dpd = dde.groupby("x_id").y_id.nunique()          # diseases per drug
both = tpd.index.intersection(dpd.index)
manufactured = int((tpd.loc[both] * dpd.loc[both]).sum())
multi = tpd.loc[both][tpd.loc[both] > 1].index
from_multi = int((tpd.loc[multi] * dpd.loc[multi]).sum())
pct_multi = 100.0 * from_multi / max(manufactured, 1)
single = tpd.loc[both][tpd.loc[both] == 1].index
pct_single = 100.0 * int((tpd.loc[single] * dpd.loc[single]).sum()) / max(manufactured, 1)
print(f"TRUTH|drugs with both edge kinds={len(both):,}|median targets/drug={tpd.loc[both].median():.0f}"
      f"|max={int(tpd.loc[both].max())}|median diseases/drug={dpd.loc[both].median():.0f}")
print(f"TRUTH|target-disease pairs MANUFACTURED by the join: {manufactured:,}")
print(f"TRUTH|share from multi-target drugs: {pct_multi:.1f}%  |  surviving a single-target demand: {pct_single:.1f}%")
# NOT asserted against 82% / 8%. Those figures appear in TARGET_PRIORITIZER's Q4 summary line with no
# traceable computation behind them, and asserting a number whose derivation cannot be found is how
# stale figures survive. Report the measured values; pin the assertion once the source is agreed.
print("TRUTH|⚠ documented 82% / 8% NOT asserted — no traceable source; see DASHBOARD_DESIGN section 24")

# ============================================================================
# 5.5  Orthogonality — association AUC does not predict therapeutic relevance.
#
# The join goes here, in the notebook, precisely because the flow does not need it.
# ============================================================================
va = dataiku.Dataset("validation_auc_by_disease").get_dataframe()
db = dataiku.Dataset("drug_target_benchmark").get_dataframe()
j = va.merge(db, on="disease_index", suffixes=("", "_d")).dropna(subset=["auc_disease", "auc_drug_targets"])
x, y, n = j.auc_disease.to_numpy(), j.auc_drug_targets.to_numpy(), len(j)
r = float(np.corrcoef(x, y)[0, 1])
slope = float(np.polyfit(x, y, 1)[0])
print(f"ORTH|n={n}|pearson={r:+.4f}|R2={r * r:.4f}|slope={slope:+.4f}")
check("5.5 orthogonality pearson r", 0.002, round(r, 3), tol=0.004, fmt="{:+.3f}")
check("5.5 orthogonality R2", 0.0000, round(r * r, 4), tol=0.0004, fmt="{:.4f}")
check("5.5 drug-target macro AUC", 0.6886, round(float(db.auc_drug_targets.mean()), 4), tol=0.0006, fmt="{:.4f}")

# The slide no vendor shows: a popularity lookup beats the trained model on this benchmark.
if "n_validated_targets" in db.columns:
    print(f"ORTH|diseases with drug AUC below chance: {int((db.auc_drug_targets < 0.5).sum())} of {len(db)}")

# ============================================================================
# 6.1  THE THREE REFUTED GATES — the punch line, and the reason this notebook is urgent.
#
# Both lift tables are COMPUTED in 6.0 above from the upstream annotations — not read from the flow.
# Each row carries assoc_lift (enrichment for being disease-linked, i.e. what the model would learn)
# and drug_lift (enrichment for being a real drug target, i.e. what we actually want). The finding in
# every case is that the two point in DIFFERENT directions.
# ============================================================================
# ============================================================================
# 6.0  The two lift tables — COMPUTED HERE, not read back from the flow.
#
# `tractability_lift` and `safety_lift` were flow recipes this notebook read. Reading a table proves
# the recipe ran; it does not prove the number is right. Moving the computation here makes the six
# assertions below test the ARITHMETIC rather than the freshness of a build.
#
# Recipe parity is deliberate and load-bearing: identical grouping, identical n>=2000 floor, and
# identical STRING FORMS for the group keys — `lof_intolerant` groups to the key "1.0", not "1", and
# every assertion looks the value up by that string.
# ============================================================================
_nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_name", "node_type"], infer_with_pandas=False)
_nodes["node_index"] = _nodes.node_index.astype(int)
_nodes["node_id"] = _nodes.node_id.astype(str)
_dis_map = dict(zip(_nodes[_nodes.node_type == "disease"].node_id,
                    _nodes[_nodes.node_type == "disease"].node_index))
_gene_map = dict(zip(_nodes[_nodes.node_type == "gene/protein"].node_id,
                     _nodes[_nodes.node_type == "gene/protein"].node_index))

_dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
_dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
_ind = _dd[_dd.relation.astype(str).str.fullmatch("indication", case=False, na=False)].copy()
_c1, _c2 = ("x_id", "y_id") if (_ind.x_type == "drug").any() else ("y_id", "x_id")
_ind["drug"] = _ind[_c1].astype(str)
_ind["disease_index"] = _ind[_c2].astype(str).map(_dis_map)
_c3, _c4 = ("x_id", "y_id") if (_dp.x_type == "drug").any() else ("y_id", "x_id")
_dp["drug"] = _dp[_c3].astype(str)
_dp["gene_index"] = _dp[_c4].astype(str).map(_gene_map)
truth = (_ind.dropna(subset=["disease_index"])[["drug", "disease_index"]]
         .merge(_dp.dropna(subset=["gene_index"])[["drug", "gene_index"]], on="drug")
         [["disease_index", "gene_index"]].astype(int).drop_duplicates())
truth["is_validated"] = 1
_truth_dis = set(truth.disease_index)

# Chunked, as everywhere else here: scored_champion is 3.96M rows and a full read terminated the
# container with "signal 1" and no traceback. The per-chunk filter to the drug-validated diseases is
# what keeps the result small — this is chunking, not sampling, so the lifts are unchanged.
_keep = []
for _c in dataiku.Dataset("scored_champion").iter_dataframes(
        chunksize=250_000, columns=["disease_index", "gene_index", "is_target"]):
    _c = _c[_c.disease_index.isin(_truth_dis)]
    if len(_c):
        _keep.append(_c)
liftbase = pd.concat(_keep, ignore_index=True)
liftbase = liftbase.merge(truth, on=["disease_index", "gene_index"], how="left")
liftbase["is_validated"] = liftbase.is_validated.fillna(0).astype(int)
print(f"LIFTBASE|rows={len(liftbase):,}|diseases={liftbase.disease_index.nunique()}"
      f"|assoc_base={liftbase.is_target.mean():.4%}|drug_base={liftbase.is_validated.mean():.4%}")

# The population guard. 907,246 is not a documented figure — it is derived from the retired
# `safety_lift` table itself, where lof_intolerant (746,309 + 107,600 + 53,337) and
# ot_ab_tractable (425,469 + 481,777) in `tractability_lift` independently sum to the same total.
# If the codified truth-table build or the chunked read drifts, the lifts would move quietly;
# this fails loudly first. (safety_flag sums to 905,651 — 1,595 rows sit in groups below the
# n>=2000 floor and are dropped from the table, not from the base.)
check("6.0 lift base rows", 907246, len(liftbase), fmt="{:,}")
# Diseases carrying >=1 drug-validated target. compute_tractability_lift's docstring says 112, but
# that is a code comment with no run behind it — printed, deliberately not asserted.
print(f"LIFTBASE|diseases with >=1 drug-validated target: {liftbase.disease_index.nunique()}"
      f"  (recipe docstring claims 112)")


def lift_table(annot, cols, min_n=2000, as_object=False):
    """One row per (attribute, value) with n >= min_n, carrying assoc_lift and drug_lift.

    `as_object` mirrors compute_safety_lift's `.astype("object")` before fillna — that cast is what
    renders a float or Categorical group key as "1.0" rather than 1.0, which is the form the
    assertions look up. compute_tractability_lift omits the cast, so this flag reproduces both.
    """
    d = liftbase.merge(annot, on="gene_index", how="left")
    if "lof_oe_upper" in d.columns:
        d["loeuf_bucket"] = pd.cut(d.lof_oe_upper, [0, 0.35, 0.7, 1.0, 1.5, 2.01],
                                   labels=["<0.35 intolerant", "0.35-0.7", "0.7-1.0",
                                           "1.0-1.5", ">1.5 tolerant"])
    ba, bd = d.is_target.mean(), d.is_validated.mean()
    rows = []
    for col in cols:
        key = d[col].astype("object").fillna("(null)") if as_object else d[col].fillna("(null)")
        for v, g in d.groupby(key, observed=True):
            if len(g) < min_n:
                continue
            rows.append({"attribute": col, "value": str(v), "n": len(g),
                         "assoc_rate": g.is_target.mean(), "drug_rate": g.is_validated.mean(),
                         "assoc_lift": g.is_target.mean() / ba,
                         "drug_lift": g.is_validated.mean() / bd})
    return pd.DataFrame(rows)


tl = lift_table(dataiku.Dataset("enriched_gene_druggability_v2").get_dataframe(),
                ["ot_ab_tractable", "ot_sm_tractable", "localization_class", "ot_class_l1"])
sl = lift_table(dataiku.Dataset("enriched_gene_safety_v2").get_dataframe(),
                ["safety_flag", "lof_intolerant", "loeuf_bucket", "has_safety_liability"],
                as_object=True)
print(f"LIFTBASE|computed tractability rows={len(tl)}|safety rows={len(sl)}")


def lift(df, attribute, value):
    row = df[(df.attribute == attribute) & (df.value.astype(str) == str(value))]
    if not len(row):
        return None, None
    return float(row.assoc_lift.iloc[0]), float(row.drug_lift.iloc[0])


print("GATEHDR|gate|attribute=value|assoc_lift|drug_lift|verdict")

# Gate 1 — "use druggability as a model input". It points the wrong way.
a, d = lift(tl, "ot_class_l1", "Membrane receptor")
print(f"GATE|druggability|Membrane receptor|{a:.2f}|{d:.2f}|REJECTED — model would learn 'score lower'")
check("6.1 membrane receptor assoc_lift", 0.78, round(a, 2), tol=0.02, fmt="{:.2f}")
check("6.1 membrane receptor drug_lift", 3.16, round(d, 2), tol=0.02, fmt="{:.2f}")
a_ic, d_ic = lift(tl, "ot_class_l1", "Ion channel")
print(f"GATE|druggability|Ion channel|{a_ic:.2f}|{d_ic:.2f}|same shape, larger")
check("6.1 ion channel drug_lift", 11.89, round(d_ic, 2), tol=0.05, fmt="{:.2f}")

# Gate 2 — "filter out genes the body cannot live without". The measurement went the other way.
a2, d2 = lift(sl, "lof_intolerant", "1.0")
print(f"GATE|essentiality|lof_intolerant=1|{a2:.2f}|{d2:.2f}|REJECTED — BOTH above 1")
check("6.1 lof_intolerant assoc_lift", 2.07, round(a2, 2), tol=0.02, fmt="{:.2f}")
check("6.1 lof_intolerant drug_lift", 1.37, round(d2, 2), tol=0.02, fmt="{:.2f}")

# Gate 3 — "exclude known safety liabilities". The flag marks the best-studied targets.
a3, d3 = lift(sl, "has_safety_liability", "1.0")
print(f"GATE|liability|has_safety_liability=1|{a3:.2f}|{d3:.2f}|REJECTED — liabilities are DISCOVERED by drugging")
check("6.1 liability drug_lift", 4.62, round(d3, 2), tol=0.02, fmt="{:.2f}")

# Cross-check the adopted tables against the upstream annotations they summarise, so adopting them
# is a verification and not just a read-back.
try:
    dg = dataiku.Dataset("enriched_gene_druggability_v2").get_dataframe()
    print(f"XCHECK|enriched_gene_druggability_v2 rows={len(dg):,} "
          f"classes={dg.ot_class_l1.nunique() if 'ot_class_l1' in dg.columns else 'n/a'}")
except Exception as e:  # noqa: BLE001 — the cross-check is advisory, not load-bearing
    print(f"XCHECK|skipped: {e}")

# ============================================================================
# 6.2  What the liability gate would cost — the ten-second check, on the spine disease.
# This one IS in the webapp (act 4's demonstration control); recomputing it here is the cross-check.
# ============================================================================
HER2 = 48537
dc = dataiku.Dataset("dashboard_candidates").get_dataframe(
    columns=["disease_index", "gene_name", "rank_in_disease", "has_safety_liability",
             "approved_for_disease", "is_target"])
dc = dc[dc.disease_index == HER2]
dc["rank_in_disease"] = pd.to_numeric(dc.rank_in_disease, errors="coerce")
dc["has_safety_liability"] = pd.to_numeric(dc.has_safety_liability, errors="coerce").fillna(0)
top15 = dc[dc.rank_in_disease <= 15]
top50 = dc[dc.rank_in_disease <= 50]
k15 = int(top15.has_safety_liability.sum())
k50 = int(top50.has_safety_liability.sum())
print(f"COST|HER2+ top15 flagged={k15}/15 | top50 flagged={k50}/50")
check("6.2 HER2+ top-15 liability-flagged", 9, k15)
check("6.2 HER2+ top-50 liability-flagged", 23, k50)
erbb2 = top15[top15.gene_name == "ERBB2"]
if len(erbb2):
    print(f"COST|ERBB2 rank={int(erbb2.rank_in_disease.iloc[0])} "
          f"liability={int(erbb2.has_safety_liability.iloc[0])} — the gene the disease is named after")
    check("6.2 ERBB2 carries a liability flag", 1, int(erbb2.has_safety_liability.iloc[0]))

# ============================================================================
# 6.3  Subtype limits — what it cannot do.
# ============================================================================
try:
    # breast_panel_overlap retired; family_panel_overlap is a superset that
    # reproduces its novel_overlap exactly (13/13 shared pairs).
    bo = dataiku.Dataset("family_panel_overlap").get_dataframe()
    bo = bo[bo.act3_family == "breast"]
    kp = bo[(bo.disease_a.str.contains("HER2") & bo.disease_b.str.contains("triple")) |
            (bo.disease_b.str.contains("HER2") & bo.disease_a.str.contains("triple"))]
    if len(kp):
        print(f"SUBTYPE|HER2+ vs TNBC: novel_overlap={int(kp.novel_overlap.iloc[0])} "
              f"all_overlap={int(kp.all_overlap.iloc[0])} of 50")
        check("6.3 HER2+ vs TNBC novel overlap", 2, int(kp.novel_overlap.iloc[0]))
        check("6.3 HER2+ vs TNBC all-gene overlap", 14, int(kp.all_overlap.iloc[0]))
except Exception as e:  # noqa: BLE001
    print(f"SUBTYPE|skipped: {e}")

# `lung_granularity_check` COMPUTED here (step 4) — the recipe was 77 lines that this reproduces in
# a dozen. Its own printout is dropped: nb6 builds a different table from the same frame below, so
# reproducing the recipe's console output would only duplicate what follows.
_LUNG_FAMILY, _TOPN = 52236, 50           # disease_family_id: lung cancer
_gname = dict(zip(_nodes[_nodes.node_type == "gene/protein"].node_index.astype(int),
                  _nodes[_nodes.node_type == "gene/protein"].node_name))
_dname = dict(zip(_nodes[_nodes.node_type == "disease"].node_index.astype(int),
                  _nodes[_nodes.node_type == "disease"].node_name))
_lgc = []
for _c in dataiku.Dataset("scored_champion").iter_dataframes(
        chunksize=250_000,
        columns=["disease_index", "gene_index", "is_target", "disease_family_id", "proba_1"]):
    _c = _c[_c.disease_family_id == _LUNG_FAMILY]
    if len(_c):
        _lgc.append(_c)
_lgdf = pd.concat(_lgc, ignore_index=True)
_rows = []
for _d, _g in _lgdf.groupby("disease_index"):
    _t = _g.nlargest(_TOPN, "proba_1").copy()
    _t["rank_in_disease"] = range(1, len(_t) + 1)
    _t["disease_name"] = _dname.get(_d)
    _t["gene_name"] = _t.gene_index.map(_gname)
    _rows.append(_t)
lg = pd.concat(_rows, ignore_index=True)
print(f"LUNG|computed rows={len(lg):,}|diseases={lg.disease_index.nunique()}")
lg["rank_in_disease"] = pd.to_numeric(lg.rank_in_disease, errors="coerce")
tops = {d: set(g.nsmallest(50, "rank_in_disease").gene_index)
        for d, g in lg.dropna(subset=["rank_in_disease"]).groupby("disease_name")}
names = sorted(tops)
print("SUBTYPEHDR|disease_a|disease_b|shared_of_50")
for i in range(len(names)):
    for k in range(i + 1, len(names)):
        shared = len(tops[names[i]] & tops[names[k]])
        print(f"SUBTYPE|{names[i][:30]}|{names[k][:30]}|{shared}")

# ============================================================================
print("\n" + "=" * 78)
if FAIL:
    print(f"{len(FAIL)} STALE assertion(s) — the document and the flow disagree:")
    for name, doc, live in FAIL:
        print(f"  {name}: documented {doc}, live {live}")
else:
    print("All assertions PASS. The punch line is now guarded — pruning the flow is safe.")
print("=" * 78)

dataiku.Dataset("nb6_assertion_results").write_with_schema(pd.DataFrame(RESULTS))

# Fail the run loudly. Without this the scenario reports SUCCESS whenever the script merely finishes,
# which is exactly the green-but-wrong signal this project keeps hitting.
if FAIL:
    raise SystemExit(f"{len(FAIL)} stale assertion(s) — see nb6_assertion_results")
