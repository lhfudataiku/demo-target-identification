# Which diseases make good demo personas? Evidence-based selection over all 670 validation
# diseases, on THREE axes rather than one.
#
# WHAT THE FIRST VERSION GOT WRONG, and why this one looks different: it used "share of the top 50
# that is already a known target" as a novelty-balance criterion, treating a high share as "no
# novelty left". That is a PRECISION measure, not a novelty measure. Normalised by base rate,
# NSCLC's 96% is a 19x enrichment (the best ranking in the panel) while CKD's 2% is 2.9x (the
# worst). The old criterion rewarded the worst ranking and rejected the best, and it said nothing
# at all about the novel candidates -- which by construction sit BELOW the known ones.
#
# THE THREE AXES, each independently measured:
#   1. RANKING PRECISION   known-target enrichment at top-50, normalised by base rate.
#                          Does the model put truth first?
#   2. THERAPEUTIC          drug-target AUC over the approved-indication set.
#                          Does the ranking agree with what drugs actually hit?
#   3. DISCOVERY            enrichment of drug-linked targets among the top-50 NOVEL candidates,
#                          from novel_discovery_eval. Does it surface targets nobody annotated?
#
# Axis 3 is the deliverable's actual claim and was unmeasured until now. It is reported against
# BOTH ground truths, because the choice changes the ranking of candidates:
#   approved        strict, sparse -- the metabolic diseases excel here
#   investigational looser, 13x larger, includes FAILED programmes -- rescues the oncology terms
#                   whose target classes are in development rather than approved
import dataiku
import numpy as np
import pandas as pd

CURRENT = {"lung cancer", "obesity disorder", "type 2 diabetes mellitus",
           "chronic kidney disease", "lung adenocarcinoma", "non-small cell lung carcinoma"}

nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_name", "node_type"], infer_with_pandas=False)
nodes["node_index"] = nodes.node_index.astype(int)
dname = dict(zip(nodes[nodes.node_type == "disease"].node_index,
                 nodes[nodes.node_type == "disease"].node_name))

auc = dataiku.Dataset("validation_auc_by_disease").get_dataframe(
    columns=["disease_index", "n_pos", "n_neg", "auc_disease", "hits_at_50", "recall_at_20"])
bench = dataiku.Dataset("drug_target_benchmark").get_dataframe(
    columns=["disease_index", "n_validated_targets", "auc_drug_targets", "hits_at_50"]) \
    .rename(columns={"hits_at_50": "approved_in_top50"})
disc = dataiku.Dataset("novel_discovery_eval").get_dataframe()

# axis 1: ranking precision -- known targets found in the top 50, over the base rate
auc["module_size"] = auc.n_pos + auc.n_neg
auc["base_rate"] = auc.n_pos / auc.module_size
auc["known_pct50"] = 100 * auc.hits_at_50 / 50
auc["rank_enrichment"] = (auc.hits_at_50 / 50) / auc.base_rate

# axis 3: discovery, one column pair per ground truth
d = auc.copy()
for t in ["approved", "investigational"]:
    s = disc[disc.ground_truth == t][["disease_index", "novel_linked_total",
                                     "hits_top50", "lift_top50"]]
    s = s.rename(columns={"novel_linked_total": f"{t}_to_find",
                          "hits_top50": f"{t}_found50", "lift_top50": f"{t}_lift50"})
    d = d.merge(s, on="disease_index", how="left")
d = d.merge(bench, on="disease_index", how="left")
d["disease"] = d.disease_index.map(dname)
d["is_current"] = d.disease.isin(CURRENT)

# best discovery across either ground truth -- a disease should not be penalised for having its
# target classes in trials rather than approved
d["best_lift50"] = d[["approved_lift50", "investigational_lift50"]].max(axis=1)
d["best_found50"] = d[["approved_found50", "investigational_found50"]].max(axis=1)

d["ok_size"]     = d.n_pos >= 30
d["ok_auc"]      = d.auc_disease >= 0.75
d["ok_ranking"]  = d.rank_enrichment >= 5           # truth concentrated 5x over base rate
d["ok_discovery"] = d.best_lift50 >= 3              # novel head enriched 3x for real targets
d["ok_found"]    = d.best_found50 >= 3              # at least 3 real targets actually surfaced
CRIT = ["ok_size", "ok_auc", "ok_ranking", "ok_discovery", "ok_found"]
d["n_criteria"] = d[CRIT].sum(axis=1)

print(f"=== criterion funnel over {len(d)} validation diseases ===")
for c, lbl in zip(CRIT, ["n_pos >= 30", "association AUC >= 0.75",
                         "ranking enrichment >= 5x", "discovery lift@50 >= 3x",
                         ">= 3 real targets in the top-50 novel"]):
    print(f"  {lbl:44s}{int(d[c].sum()):>5}")
print(f"  {'ALL FIVE':44s}{int((d.n_criteria == 5).sum()):>5}")

SHOW = ["disease", "n_pos", "auc_disease", "rank_enrichment", "auc_drug_targets",
        "approved_to_find", "approved_found50", "approved_lift50",
        "investigational_to_find", "investigational_found50", "investigational_lift50",
        "n_criteria"]
fmt = lambda x: f"{x:.2f}"

print("\n\n=== the CURRENT panel, all three axes ===")
print(d[d.is_current].sort_values("best_lift50", ascending=False)[SHOW]
      .to_string(index=False, float_format=fmt))

print("\n\n=== all diseases passing five criteria, best discovery first ===")
best = d[d.n_criteria == 5].sort_values("best_lift50", ascending=False)
print(best[SHOW].head(30).to_string(index=False, float_format=fmt))

print("\n\n=== strongest on APPROVED targets (the strict bar) ===")
print(d[d.approved_found50.fillna(0) >= 3].nlargest(12, "approved_lift50")[SHOW]
      .to_string(index=False, float_format=fmt))

print("\n\n=== strongest on INVESTIGATIONAL targets (the broad bar) ===")
print(d[d.investigational_found50.fillna(0) >= 5].nlargest(12, "investigational_lift50")[SHOW]
      .to_string(index=False, float_format=fmt))

dataiku.Dataset("persona_candidates").write_with_schema(
    d[SHOW + ["disease_index", "module_size", "known_pct50", "is_current",
              "best_lift50", "best_found50", "recall_at_20"] + CRIT])

