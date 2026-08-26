# The breast-subtype shortlist, shaped as a REVIEW INSTRUMENT for a breast surgeon.
#
# This is not a report. It is a form. The clinician's job is to falsify it, so every row carries the
# evidence needed to judge it and four blank columns for their verdict. That makes the output a
# dataset we can score later -- expert agreement rate per subtype -- rather than an anecdote.
#
# WHY A CLINICIAN AND NOT ANOTHER METRIC. Two of the four arms cannot be scored against our own
# labels: triple-negative has 8 known gene associations, luminal A has 101 in a pool of 8,157. A
# surgeon can falsify those lists in twenty minutes, which is both faster and harder than anything in
# TARGET_PRIORITIZER section 8. See `breast_panel_metrics` for the per-arm trust numbers to hand over
# WITH this sheet -- never without it.
#
# THE ANCHOR MATTERS. Each arm shows its top KNOWN targets before its novel candidates. If the
# surgeon does not recognise the known block as sensible for that subtype, the novel block is not
# worth their time and the conversation should stop there. Leading with novel candidates invites them
# to judge a list they have no way to calibrate.
import dataiku
import pandas as pd

# The clinical trichotomy, plus the umbrella as a reference arm. Ordered as a surgeon thinks:
# hormone-driven, HER2-driven, triple-negative -- then the generic term for comparison.
ARMS = [(42563, "Luminal A (HR+/HER2-)"),
        (48537, "HER2-positive"),
        (47807, "Triple-negative"),
        (47415, "Breast carcinoma (umbrella, reference)")]
N_KNOWN, N_NOVEL = 10, 20

tc = dataiku.Dataset("target_candidates_2").get_dataframe(
    columns=["disease_index", "disease_name", "gene_name", "gene_index", "is_target", "score",
             "rank_in_disease", "top_shap_drivers", "druggability_class", "ot_class_l1",
             "ot_sm_tractable", "ot_ab_tractable", "has_approved_drug",
             "has_safety_liability", "safety_events"])

rows = []
for di, arm in ARMS:
    g = tc[tc.disease_index == di].sort_values("rank_in_disease")
    if not len(g):
        print(f"  !! {arm} ({di}) absent from target_candidates_2")
        continue
    known = g[g.is_target == 1].head(N_KNOWN)
    novel = g[g.is_target == 0].head(N_NOVEL)
    for block, sub in (("A. known target - sanity anchor", known),
                       ("B. NOVEL candidate - please assess", novel)):
        for i, (_, r) in enumerate(sub.iterrows(), 1):
            rows.append({
                "arm": arm,
                "block": block,
                "block_rank": i,
                "rank_in_subtype": int(r.rank_in_disease),
                "gene": r.gene_name,
                "model_score": round(float(r.score), 4),
                "target_class": r.ot_class_l1 if pd.notna(r.ot_class_l1) else "",
                "druggability": r.druggability_class if pd.notna(r.druggability_class) else "",
                "small_molecule_tractable": bool(r.ot_sm_tractable) if pd.notna(r.ot_sm_tractable) else None,
                "antibody_tractable": bool(r.ot_ab_tractable) if pd.notna(r.ot_ab_tractable) else None,
                "some_drug_already_hits_this_gene": bool(r.has_approved_drug) if pd.notna(r.has_approved_drug) else None,
                "documented_safety_liability": bool(r.has_safety_liability) if pd.notna(r.has_safety_liability) else None,
                "liability_detail": (str(r.safety_events)[:120] if pd.notna(r.safety_events) else ""),
                "why_the_model_ranked_it": (str(r.top_shap_drivers)[:160]
                                            if pd.notna(r.top_shap_drivers) else ""),
                # --- the surgeon fills these in ---
                "REVIEW_plausible_1to5": "",
                "REVIEW_already_known_to_you": "",
                "REVIEW_worth_pursuing": "",
                "REVIEW_comment": "",
            })

out = pd.DataFrame(rows)
print(f"{len(out)} review rows over {out.arm.nunique()} arms\n")
print(out.groupby(["arm", "block"]).size().to_string())

# The liability column is display-only and must be labelled as such wherever it is shown. It is
# ENRICHED for good targets (liabilities are found BY drugging), so a surgeon reading it as a warning
# would discard the best-evidenced candidates -- see TARGET_PRIORITIZER section 10.3 and ADRB2.
n_liab = int(out.documented_safety_liability.fillna(False).sum())
print(f"\n{n_liab} of {len(out)} rows carry a liability flag. NOT a safety verdict: the flag marks "
      f"well-studied\ntargets, not dangerous ones. Present it as context only.")

for _, arm in ARMS:
    sub = out[(out.arm == arm) & (out.block.str.startswith("B"))]
    if len(sub):
        print(f"\nNOVEL|{arm}|" + ", ".join(sub.gene.head(20)))

dataiku.Dataset("breast_shortlist").write_with_schema(out)
