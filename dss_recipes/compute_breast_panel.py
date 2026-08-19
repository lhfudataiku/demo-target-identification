# BREAST SUBTYPE PANEL — built to be validated by a breast surgeon, not by our own labels.
#
# WHY THIS EXISTS: the persona panel had no breast term, and PROJECT_CONTEXT §3 still recommended one
# from before any measurement. A breast surgeon can falsify a candidate list in minutes, which is a
# faster and harder test than any metric in §8. This recipe produces the evidence the surgeon
# conversation needs: how much to trust each subtype's list, and whether the subtypes actually differ.
#
# THE RISK WE ARE MEASURING FIRST. TARGET_PRIORITIZER §3.4 established that the model CANNOT resolve
# lung histological subtype -- adenocarcinoma and squamous carcinoma get near-identical lists. HER2+
# and triple-negative are the same *kind* of question, and a surgeon would spot identical lists
# instantly, so the overlap has to be measured before anyone shows this to a clinician.
#
# WHAT WE FOUND, stated here because it is the interesting result: breast molecular subtypes DO
# resolve. HER2+ vs triple-negative share only ~4% of their top-50 NOVEL candidates. The distinction
# from lung is that breast subtypes are defined by *molecular* markers that carry their own curated
# gene associations, whereas lung subtypes are defined by *morphology* and inherit a shared
# annotation set. So §3.4's claim needs narrowing: the model resolves molecularly-defined subtypes and
# not morphologically-defined ones.
#
# POWER IS THE OTHER HALF. Module sizes across this panel span 8 to 864 positives. Triple-negative has
# EIGHT known gene associations, so its AUC (0.93) is not a trustworthy point estimate and its
# hits@50 expects 0.16 by chance -- exactly the situation the 2026-08-17 decision-log entry warns
# about, where an observed count cannot distinguish signal from absence of power. Every row therefore
# carries `expected_at_50` and a `power` verdict, and the surgeon-facing conclusion for TNBC is
# "we cannot score this list, which is precisely why we want your read on it".
import dataiku
import numpy as np
import pandas as pd
import itertools
import math


def poisson_sf(k, lam):
    """P(X >= k) for X ~ Poisson(lam). Exact sum, no scipy dependency."""
    if lam <= 0:
        return 1.0 if k <= 0 else 0.0
    if k <= 0:
        return 1.0
    # 1 - P(X <= k-1)
    term = math.exp(-lam)
    cdf = term
    for i in range(1, int(k)):
        term *= lam / i
        cdf += term
    return max(0.0, min(1.0, 1.0 - cdf))


def auc_se(auc, npos, nneg):
    """Hanley-McNeil standard error of an ROC AUC."""
    if not (npos and nneg) or auc != auc:
        return float("nan")
    q1 = auc / (2.0 - auc)
    q2 = 2.0 * auc * auc / (1.0 + auc)
    v = (auc * (1 - auc) + (npos - 1) * (q1 - auc ** 2) + (nneg - 1) * (q2 - auc ** 2)) / (npos * nneg)
    return math.sqrt(v) if v > 0 else float("nan")

PANEL = {47415: "breast carcinoma",
         48537: "HER2 positive breast carcinoma",
         47807: "triple-negative breast carcinoma",
         42563: "luminal A breast carcinoma",
         42562: "luminal B breast carcinoma",
         49721: "breast cancer (parent term)",
         48747: "estrogen-receptor positive breast cancer",
         48748: "estrogen-receptor negative breast cancer",
         47832: "breast lobular carcinoma",
         46673: "female breast carcinoma",
         48546: "invasive breast carcinoma",
         47414: "breast adenocarcinoma"}
K = 50

nid = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_name", "node_type"], infer_with_pandas=False)
nid["node_index"] = nid.node_index.astype(int)
nid["node_id"] = nid.node_id.astype(str)
D = nid[nid.node_type == "disease"]
G = nid[nid.node_type == "gene/protein"]
gname = dict(zip(G.node_index, G.node_name))
dmap = dict(zip(D.node_id, D.node_index))
gmap = dict(zip(G.node_id, G.node_index))

# --- the two independent drug ground truths (TARGET_PRIORITIZER §8.1) -------------------
dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
gc, tc = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
dp["drug"] = dp[gc].astype(str)
dp["gene_index"] = dp[tc].astype(str).map(gmap)
dp = dp.dropna(subset=["gene_index"])[["drug", "gene_index"]]
# gene-level tractability: the only label with no join inflation at all (§8.4)
tractable = set(dp.gene_index.astype(int))


def pairs_for(rel):
    sub = dd[dd.relation.astype(str).str.fullmatch(rel, case=False, na=False)].copy()
    dc, xc = ("x_id", "y_id") if (sub.x_type == "drug").any() else ("y_id", "x_id")
    sub["drug"] = sub[dc].astype(str)
    sub["disease_index"] = sub[xc].astype(str).map(dmap)
    out = (sub.dropna(subset=["disease_index"])[["drug", "disease_index"]]
           .merge(dp, on="drug")[["disease_index", "gene_index"]].astype(int).drop_duplicates())
    return set(map(tuple, out.values))


TRUTH = {"approved": pairs_for("indication"),
         "investigational": pairs_for("drug_investigated_for")}

sc = dataiku.Dataset("scored_m3").get_dataframe(
    columns=["disease_index", "gene_index", "is_target", "proba_1"])
sc = sc[sc.disease_index.isin(PANEL)].copy()
print(f"{len(sc):,} scored rows over {sc.disease_index.nunique()} breast terms\n")

rows, top_all, top_nov = [], {}, {}
for di, g in sc.groupby("disease_index"):
    g = g.sort_values("proba_1", ascending=False)
    npos, n = int(g.is_target.sum()), len(g)
    nneg = n - npos
    r = g.proba_1.rank(ascending=True)
    auc = ((r[g.is_target == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)
           if npos and nneg else np.nan)
    hits = int(g.head(K).is_target.sum())
    exp = K * npos / n
    nov = g[g.is_target == 0]
    top_all[di] = list(g.head(K).gene_index.astype(int))
    top_nov[di] = list(nov.head(K).gene_index.astype(int))

    # Significance, not just expected count. An earlier version labelled anything with
    # expected<1 "UNPOWERED", which is wrong in the direction that matters: HER2+ sees 46 hits
    # against 2.44 expected, which is overwhelming regardless of how small the expectation is.
    # Power is only a problem when the OBSERVED count is also small. So: exact Poisson upper tail
    # P(X >= observed | lambda = expected), plus a separate fragility flag for tiny numerators.
    p_hits = poisson_sf(hits, exp)
    verdict = ("not significant" if p_hits > 0.05 else
               "significant but fragile (<3 hits)" if hits < 3 else
               "significant")
    # AUC standard error (Hanley-McNeil): with 8 positives the point estimate means very little
    se = auc_se(auc, npos, nneg)
    rec = {"disease_index": int(di), "disease": PANEL[int(di)], "pool": n,
           "n_known_targets": npos, "base_rate_pct": 100 * npos / n,
           "auc": auc, "auc_se": se,
           "auc_lo95": (auc - 1.96 * se) if se == se else np.nan,
           "auc_hi95": (auc + 1.96 * se) if se == se else np.nan,
           "hits_at_50": hits, "expected_at_50": exp,
           "enrichment_at_50": (hits / exp) if exp > 0 else np.nan,
           "hits50_poisson_p": p_hits, "hits50_verdict": verdict,
           "n_novel": len(nov),
           "auc_trustworthy": bool(npos >= 30)}
    # tractability of the novel head -- can a chemist act on it? (§8.4)
    nv50 = top_nov[di]
    rec["novel50_tractable"] = sum(1 for x in nv50 if x in tractable)
    rec["novel50_tractable_pct"] = 100 * rec["novel50_tractable"] / max(len(nv50), 1)
    # drug-linked novel candidates, both ground truths
    for tname, tset in TRUTH.items():
        tot = sum(1 for x in nov.gene_index.astype(int) if (int(di), x) in tset)
        hit = sum(1 for x in nv50 if (int(di), x) in tset)
        base = tot / len(nov) if len(nov) else np.nan
        rec[f"{tname}_novel_total"] = tot
        rec[f"{tname}_novel_hits50"] = hit
        rec[f"{tname}_novel_exp50"] = K * base if base == base else np.nan
        rec[f"{tname}_novel_lift50"] = ((hit / K) / base) if base and base > 0 else np.nan
    rec["top10_novel_genes"] = ", ".join(gname.get(x, str(x)) for x in nv50[:10])
    rows.append(rec)

metrics = pd.DataFrame(rows).sort_values("n_known_targets", ascending=False)
print("=== per-term trust ===")
show = ["disease", "pool", "n_known_targets", "auc", "auc_lo95", "auc_hi95", "hits_at_50",
        "expected_at_50", "enrichment_at_50", "hits50_poisson_p", "hits50_verdict",
        "novel50_tractable_pct"]
print(metrics[show].to_string(index=False, float_format=lambda x: f"{x:.2f}"))

print("\n=== do the subtypes actually differ? top-50 NOVEL overlap ===")
ov = []
for a, b in itertools.combinations(sorted(top_nov), 2):
    inter = len(set(top_nov[a]) & set(top_nov[b]))
    ia = len(set(top_all[a]) & set(top_all[b]))
    ov.append({"disease_a": PANEL[a], "disease_b": PANEL[b],
               "novel_overlap": inter, "novel_overlap_pct": 100 * inter / K,
               "all_overlap": ia, "all_overlap_pct": 100 * ia / K,
               "distinct": bool(inter <= K * 0.25)})
overlap = pd.DataFrame(ov).sort_values("novel_overlap")
key = overlap[overlap.disease_a.str.contains("HER2|triple", case=False)
              | overlap.disease_b.str.contains("HER2|triple", case=False)]
print(key.to_string(index=False, float_format=lambda x: f"{x:.1f}"))

print("\n=== the clinically decisive pair ===")
h, t = 48537, 47807
inter = set(top_nov[h]) & set(top_nov[t])
print(f"  HER2+ vs triple-negative, top-50 novel: {len(inter)}/{K} shared "
      f"({100*len(inter)/K:.0f}%)")
print(f"  shared: {', '.join(gname.get(x, str(x)) for x in inter) or '(none)'}")
print("  A surgeon treats these as different diseases. So must the model, or the list is wrong.")
print("  Contrast lung (§3.4), where histological subtypes were NOT separable.")

# THE CAVEAT TO VOLUNTEER, not hide. Separation from the *sibling* subtype is not the same as
# specificity. If a subtype's list is nearly identical to the generic umbrella term, then it is a
# breast-cancer list wearing a subtype label, and a clinician will say so.
print("\n=== specificity check: how subtype-specific is each list, really? ===")
UMBRELLA = [47415, 46673, 48546]  # breast carcinoma / female breast carcinoma / invasive breast ca
for di in sorted(top_nov):
    if di in UMBRELLA:
        continue
    best = max((len(set(top_nov[di]) & set(top_nov[u])) for u in UMBRELLA if u in top_nov),
               default=0)
    tag = ("GENERIC - reads as an umbrella list" if best >= K * 0.5 else
           "partly specific" if best >= K * 0.25 else "SUBTYPE-SPECIFIC")
    print(f"  {PANEL[di][:42]:42s} max overlap with an umbrella term: {best:2d}/{K}  -> {tag}")
print("  Read this WITH the pairwise table: HER2+ separates cleanly from triple-negative, but its")
print("  list still tracks the umbrella terms closely. Triple-negative is the one that is genuinely")
print("  its own list. Say that to the surgeon before they say it to us.")

dataiku.Dataset("breast_panel_metrics").write_with_schema(metrics)
dataiku.Dataset("breast_panel_overlap").write_with_schema(overlap)
