# OPTION 1 — the decisive experiment: is the OBJECTIVE the binding constraint on the
# association-vs-therapeutic gap, or the feature set?
#
# Everything measured so far says the objective: two preprocessing interventions failed to move
# drug-target AUC; a tractability filter over the provably-drugged universe still put only 19.5%
# of validated targets in the top 50; drug-validated targets sit at PARITY with association
# positives on the pathway metapath (0.674 vs 0.672); and the 26 sub-random diseases share no
# measurable trait (drug AUC correlates with association AUC r=0.116, n_drug r=-0.026).
# That is all consistent with "the label never asked for therapeutic relevance" -- but it is an
# INFERENCE. This recipe builds the labels needed to demonstrate it.
#
# DESIGN — one variable changes, the label. Same 12 features as m3-f12, same split, same
# hyperparameters. Tractability is deliberately NOT added here: doing both at once would
# confound the result.
#
# LABELS
#   is_drug_target_strict : a drug with an `indication` edge to the disease targets the gene.
#                           4,110 pairs / 416 diseases. Too rare to TRAIN on -- the test split
#                           holds only 196 positives over 18 diseases (measured in
#                           drug_label_feasibility), which cannot support model selection.
#   is_drug_target_weak   : strict OR `drug_investigated_for` (trial-stage, not approved).
#                           13,573 train positives over 230 diseases. Reads as "someone judged
#                           this target mechanistically plausible for this disease."
#
# TRAIN on weak, EVALUATE on strict -- train on plausibility, score on what got approved. The
# disease-level split key keeps the two disjoint, so no strict pair used for evaluation comes
# from a disease the model trained on.
#
# CAVEAT: weak labels include FAILURES. A target trialled and abandoned still counts positive.
# That is the right noise for this question (it captures mechanistic plausibility, which is what
# target identification predicts) but it means the model learns "worth trying", not "works".
#
# NOTE ON THE JOIN: the project convention is visual Join recipes, not pandas merges. This is a
# labelling step where the join is a means rather than the point, and the visual route would cost
# 3 Joins + 3 Prepares (to fill unmatched rows with 0) for an experiment that may be discarded.
# If this label becomes permanent, convert it.
import dataiku
import pandas as pd

FEATURES = ["dwpc_GBGD", "dwpc_GFGD", "dwpc_GGD", "dwpc_GPGD", "gene_n_pathways",
            "gene_ppi_degree", "ppi_adamic_adar", "ppi_common_neighbors_z",
            "ppi_evidence_depth", "ppi_jaccard", "ppi_multi_source_frac",
            "shared_pathway_frac"]
KEEP = ["disease_index", "gene_index", "is_target", "disease_split_key"] + FEATURES
SETS = {"psplit_train_set": "psplit_train_drug",
        "psplit_test_set": "psplit_test_drug",
        "psplit_validation_set": "psplit_validation_drug"}

nodes = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_type"], infer_with_pandas=False)
nodes["node_index"] = nodes.node_index.astype(int)
nodes["node_id"] = nodes.node_id.astype(str)
dis = dict(zip(nodes[nodes.node_type == "disease"].node_id,
               nodes[nodes.node_type == "disease"].node_index))
gen = dict(zip(nodes[nodes.node_type == "gene/protein"].node_id,
               nodes[nodes.node_type == "gene/protein"].node_index))

dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
dp = dataiku.Dataset("drug_protein_edges").get_dataframe(infer_with_pandas=False)
gcol, tcol = ("x_id", "y_id") if (dp.x_type == "drug").any() else ("y_id", "x_id")
dp["drug"] = dp[gcol].astype(str)
dp["gene_index"] = dp[tcol].astype(str).map(gen)
dp = dp.dropna(subset=["gene_index"])


def pairs(relation_regex):
    sub = dd[dd.relation.astype(str).str.fullmatch(relation_regex, case=False, na=False)].copy()
    dcol, xcol = ("x_id", "y_id") if (sub.x_type == "drug").any() else ("y_id", "x_id")
    sub["drug"] = sub[dcol].astype(str)
    sub["disease_index"] = sub[xcol].astype(str).map(dis)
    out = (sub.dropna(subset=["disease_index"])[["drug", "disease_index"]]
           .merge(dp[["drug", "gene_index"]], on="drug")[["disease_index", "gene_index"]]
           .astype(int).drop_duplicates())
    return set(map(tuple, out.values))


strict = pairs("indication")
weak = strict | pairs("drug_investigated_for")
print(f"label universe: strict {len(strict):,} pairs, weak {len(weak):,} pairs")

for src, dst in SETS.items():
    df = dataiku.Dataset(src).get_dataframe(columns=KEEP)
    keys = list(zip(df.disease_index.astype(int), df.gene_index.astype(int)))
    df["is_drug_target_strict"] = [1 if k in strict else 0 for k in keys]
    df["is_drug_target_weak"] = [1 if k in weak else 0 for k in keys]
    s, w = int(df.is_drug_target_strict.sum()), int(df.is_drug_target_weak.sum())
    print(f"  {dst:26s} rows {len(df):>9,}  strict {s:>6,} ({100*s/len(df):.4f}%)  "
          f"weak {w:>6,} ({100*w/len(df):.4f}%)  assoc {int(df.is_target.sum()):>6,}")
    dataiku.Dataset(dst).write_with_schema(df)
