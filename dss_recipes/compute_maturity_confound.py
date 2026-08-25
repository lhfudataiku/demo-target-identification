# Is the "metabolic excels on approved, oncology on investigational" split a real property, or an
# artifact of which label happens to be denser for each disease?
#
# WHY THIS CHECK EXISTS. TARGET_PRIORITIZER §8.2 asserts the split is "a real property, not a
# coverage artifact", reasoning that metabolic diseases have mature approved pharmacology while
# oncology target classes are still in trials. That is a plausible story told after seeing the
# numbers, and it has an obvious alternative: every disease may simply score better on whichever
# ground truth is denser for it, which would make the pattern a labelling effect and the §8.2 claim
# an over-reading. The two are distinguishable by measurement, so measure.
#
# THE DISCRIMINATING TEST. Define approval maturity for a disease as
#       maturity = approved_pairs / (approved_pairs + investigational_pairs)
# and the axis preference as
#       delta = approved_lift@50 - investigational_lift@50
# If `delta` tracks `maturity`, each disease is just scoring on its denser label and the split is an
# artifact. If it does not, the metabolic/oncology difference is about something else and the §8.2
# claim survives.
#
# A DIRECTIONAL SUBTLETY worth stating, because it cuts against the naive worry: lift is already
# normalised by base rate, so a denser label makes a given top-K precision LOOK WORSE, not better.
# The confound therefore cannot be "more evidence = higher lift" by construction. What it can be is a
# POWER effect -- sparse labels produce unmeasurable or zero lifts (§8.3) -- which biases in the
# opposite direction. Both are checked.
import dataiku
import numpy as np
import pandas as pd

MIN_POS = 3          # both labels must have enough positives for the lift to mean anything

nid = dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index", "node_id", "node_name", "node_type"], infer_with_pandas=False)
nid["node_index"] = nid.node_index.astype(int); nid["node_id"] = nid.node_id.astype(str)
D = nid[nid.node_type == "disease"]
dmap = dict(zip(D.node_id, D.node_index))
dname = dict(zip(D.node_index, D.node_name))

dd = dataiku.Dataset("drug_disease_edges").get_dataframe(infer_with_pandas=False)
dc, xc = ("x_id", "y_id") if (dd.x_type == "drug").any() else ("y_id", "x_id")
dd["drug"] = dd[dc].astype(str); dd["disease_index"] = dd[xc].astype(str).map(dmap)
dd = dd.dropna(subset=["disease_index"])
n_drugs = {}
for rel, lab in [("indication", "n_approved_drugs"), ("drug_investigated_for", "n_trial_drugs")]:
    sub = dd[dd.relation.astype(str).str.fullmatch(rel, case=False, na=False)]
    n_drugs[lab] = sub.groupby("disease_index").drug.nunique()

disc = dataiku.Dataset("novel_discovery_eval").get_dataframe()
w = disc.pivot_table(index="disease_index", columns="ground_truth",
                     values=["novel_linked_total", "lift_top50", "hits_top50"])
w.columns = [f"{a}_{b}" for a, b in w.columns]
w = w.reset_index()
w["n_approved_drugs"] = w.disease_index.map(n_drugs["n_approved_drugs"]).fillna(0)
w["n_trial_drugs"] = w.disease_index.map(n_drugs["n_trial_drugs"]).fillna(0)
w["disease"] = w.disease_index.map(dname)

ap, iv = "novel_linked_total_approved", "novel_linked_total_investigational"
w = w[(w[ap].fillna(0) >= MIN_POS) & (w[iv].fillna(0) >= MIN_POS)].copy()
w["maturity"] = w[ap] / (w[ap] + w[iv])
w["delta"] = w.lift_top50_approved - w.lift_top50_investigational
print(f"diseases with >={MIN_POS} novel positives on BOTH labels: {len(w)}")

def sp(a, b):
    return w[[a, b]].corr(method="spearman").iloc[0, 1]

print("\n=== the discriminating correlation ===")
print(f"  Spearman(maturity, delta)                      = {sp('maturity','delta'):+.3f}")
print("     ^ if strongly positive, each disease is just scoring on its denser label")
print("\n=== supporting correlations ===")
for a, b, note in [
    ("novel_linked_total_approved", "lift_top50_approved", "more approved positives -> higher approved lift?"),
    ("novel_linked_total_investigational", "lift_top50_investigational", "same on the trial label"),
    ("n_approved_drugs", "lift_top50_approved", "more approved DRUGS -> higher approved lift?"),
    ("maturity", "lift_top50_approved", "maturity -> approved lift"),
    ("maturity", "lift_top50_investigational", "maturity -> trial lift"),
]:
    print(f"  Spearman({a[:34]:34s}, {b[:28]:28s}) = {sp(a,b):+.3f}   {note}")

# ---- does the disease CLASS difference survive stratifying on maturity? ------
CANCER = r"cancer|carcinoma|neoplasm|tumor|tumour|sarcoma|lymphoma|leukemia|leukaemia|melanoma|myeloma|glioma|blastoma"
METAB = r"diabet|obes|metabol|hyperlipid|dyslipid|insulin|glycemi|lipodystroph|overnutrition"
w["cls"] = np.where(w.disease.astype(str).str.contains(CANCER, case=False, na=False), "oncology",
            np.where(w.disease.astype(str).str.contains(METAB, case=False, na=False), "metabolic", "other"))
print("\n=== the §8.2 claim, unstratified ===")
g = w.groupby("cls").agg(n=("disease", "size"), maturity=("maturity", "median"),
                         appr_lift=("lift_top50_approved", "median"),
                         trial_lift=("lift_top50_investigational", "median"),
                         delta=("delta", "median")).round(2)
print(g.to_string())

w["mat_bin"] = pd.qcut(w.maturity.rank(method="first"), 3, labels=["low", "mid", "high"])
print("\n=== stratified by maturity tercile (does the class gap survive?) ===")
t = (w[w.cls != "other"].groupby(["mat_bin", "cls"], observed=True)
     .agg(n=("disease", "size"), appr=("lift_top50_approved", "median"),
          trial=("lift_top50_investigational", "median"), delta=("delta", "median")).round(2))
print(t.to_string())
print("\n  If oncology still prefers the trial label and metabolic the approved label WITHIN each")
print("  maturity tercile, the class difference is not explained by maturity.")

print("\n=== VERDICT ===")
r = sp("maturity", "delta")
if abs(r) >= 0.5:
    print(f"  Spearman {r:+.3f} -- STRONG. The split is substantially a labelling artifact and")
    print("  TARGET_PRIORITIZER §8.2's 'real property' claim must be withdrawn.")
elif abs(r) >= 0.25:
    print(f"  Spearman {r:+.3f} -- MODERATE. Maturity explains part of the split; §8.2 needs")
    print("  qualifying rather than withdrawing.")
else:
    print(f"  Spearman {r:+.3f} -- WEAK. Maturity does not explain the split; §8.2 survives,")
    print("  but should cite this check rather than asserting it.")

dataiku.Dataset("maturity_confound").write_with_schema(
    w[["disease_index", "disease", "cls", "maturity", "delta", "n_approved_drugs", "n_trial_drugs",
       ap, iv, "lift_top50_approved", "lift_top50_investigational",
       "hits_top50_approved", "hits_top50_investigational"]])

