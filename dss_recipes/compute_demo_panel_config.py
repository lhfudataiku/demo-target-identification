"""The demo panel, as data instead of magic numbers.

ONE row per disease the demo shows, driving BOTH acts:

  * Act 3 (families) -- `act3_family` groups a term with its siblings, `hop_depth`
    orders the cards so the parent->child AUC gradient is legible, and `act3_role`
    marks which terms feed the common-vs-specific card.
  * Act 4 (shortlist) -- `act4_area` and `act4_order` give the served shortlist.

WHY THIS EXISTS. Panel membership used to be 13 hardcoded disease_index values
inside `filter_persona_diseases` (a sampling recipe whose uiData even mislabels the
column as gene_index). Adding a disease meant editing a recipe; nothing downstream
could state which diseases it covered. Now membership is a table: adding a family
or a disease is a row here, and `filter_persona_diseases` joins against it.

The curated overlay below is the DECISION; everything else is derived from
`family_panel`. Two judgment calls are recorded rather than hidden:

  * `act3_role = 'leaf'` is clinical terminality, NOT max(hop_depth). Breast's
    leaves sit at depth 3 (HER2+, ductal, lobular) AND depth 4 (luminal A/B, TNBC);
    a mechanical max-depth rule would drop HER2+, which would be wrong.
  * Parents stay in Act 3's score and overlap cards -- a parent is up to 96%
    redundant with its dominant child (gastric adenocarcinoma vs gastric carcinoma),
    and showing that IS the point. They are excluded only from the programme card,
    where a superset's "specific" genes are meaningless.
"""

import dataiku
import pandas as pd

USABLE_FLOOR = None        # set from the `thresholds` project variable below

# ── the decision, now GOVERNED ───────────────────────────────────────────────
# Membership and thresholds come from project variables, not from literals here.
# The panel is identified BY NAME; node indices are resolved from graph_nodes at
# run time by python/demo_identity.py, which raises if a name is missing or
# ambiguous. Before 2026-09-01 this recipe pinned indices --
#   A3_FAMILIES = {49721: "breast", 44244: "uterine", 36637: "stomach"}
# -- and a graph rebuild renumbers node_index, so the panel would have silently
# become a different panel with no error anywhere.
#
# The curated judgement that USED to live in these literals is preserved, because
# it is not derivable: ONE classification axis per family, or the programme card
# collapses. Breast is scored on BOTH the molecular axis (HER2+/luminal/TNBC) and
# the histology axis (ductal/lobular), and the two classify the same tumours --
# ductal overlaps HER2+ by 85%, so including it absorbed HER2+'s specific genes
# and left it with ONE (ARID1B). Molecular only: HER2+ goes 1 -> 9 own genes and
# every subtype gets a real set. Ductal and lobular stay in the score and overlap
# cards; they are simply not leaves. That reasoning now sits beside the names in
# the `demo_panel` variable -- keep the two together if either moves.
import demo_identity

_panel = demo_identity.panel()
_thr = demo_identity.thresholds()

USABLE_FLOOR = int(_thr["panel_n_pos"])

# name -> node_index, asserted unique against graph_nodes
_fam_names = list(_panel["act3_families"].values())
_idx = demo_identity.name_to_index(_fam_names)

# {node_index: short label}, the shape the rest of this recipe already expects
A3_FAMILIES = {_idx[name]: label for label, name in _panel["act3_families"].items()}
A3_LEAVES = {k: list(v) for k, v in _panel["act3_leaves"].items()}
A4 = [tuple(x) for x in _panel["act4"]]


# ── derive ───────────────────────────────────────────────────────────────────
fp = dataiku.Dataset("family_panel").get_dataframe()
names = dataiku.Dataset("persona_enrichment").get_dataframe()[["disease_index", "disease"]]
fp = fp.merge(names, on="disease_index", how="left")

rows = {}


def put(r, **kw):
    """Upsert by disease_index -- a term can be in Act 3 AND Act 4."""
    di = int(r.disease_index)
    base = rows.setdefault(di, {
        "disease_index": di, "disease": r.disease,
        "disease_family_id": int(r.disease_family_id) if pd.notna(r.disease_family_id) else None,
        "hop_depth": float(r.hop_depth) if pd.notna(r.hop_depth) else None,
        "n_pos": int(r.n_pos), "auc_disease": float(r.auc_disease),
        "auc_trustworthy": bool(r.auc_trustworthy),
        "act3_family": None, "act3_role": None, "in_act3": False,
        "act4_area": None, "act4_order": None, "in_act4": False,
    })
    base.update(kw)


# Act 3: every usable term in the three families, curated leaves and not.
for fid, fam in A3_FAMILIES.items():
    sub = fp[(fp.disease_family_id == fid) & (fp.n_pos >= USABLE_FLOOR)]
    for r in sub.itertuples():
        # "not_leaf", NOT "parent". This flag records only whether the term is in
        # the curated leaf set; it says nothing about ontology. Calling the rest
        # "parent" was wrong: `metaplastic breast carcinoma` (depth 3) and
        # `endometrial mixed adenocarcinoma` (depth 4) are sibling subtypes that
        # were simply not selected as leaves, not ancestors of anything. True
        # ancestry would need the ontology's disease_disease edges; `hop_depth`
        # carries the hierarchy for any reader who needs it.
        role = "leaf" if r.disease in A3_LEAVES[fam] else "not_leaf"
        put(r, act3_family=fam, act3_role=role, in_act3=True)

# Act 4: the shortlist. TNBC is deliberately here despite 8 positives -- it carries
# a list (RAD50 #1, ATM #2), never a quotable AUC, and the app must not print one.
for order, (name, area) in enumerate(A4, start=1):
    hit = fp[fp.disease == name]
    if hit.empty:
        raise ValueError(f"Act 4 disease not in the validation set: {name!r}")
    r = hit.iloc[0]
    fam = A3_FAMILIES.get(int(r.disease_family_id)) if pd.notna(r.disease_family_id) else None
    role = None
    if fam and r.disease in A3_LEAVES[fam]:
        role = "leaf"
    put(r, act4_area=area, act4_order=order, in_act4=True,
        **({"act3_family": fam, "act3_role": role} if fam and rows.get(int(r.disease_index), {}).get("act3_family") is None else {}))

out = pd.DataFrame(list(rows.values())).sort_values(
    ["in_act4", "act4_order", "act3_family", "hop_depth", "n_pos"],
    ascending=[False, True, True, True, False])

# Guards. A silently short config would quietly shrink the demo.
assert out.in_act3.sum() >= 25, f"Act 3 terms: {out.in_act3.sum()}"
assert out.in_act4.sum() == len(A4), f"Act 4 diseases: {out.in_act4.sum()} != {len(A4)}"
for fam, leaves in A3_LEAVES.items():
    got = set(out[(out.act3_family == fam) & (out.act3_role == "leaf")].disease)
    missing = set(leaves) - got
    # TNBC is below the usable floor, so it reaches Act 3 only via the Act 4 pass.
    assert not missing - {"triple-negative breast carcinoma"}, f"{fam} leaves missing: {missing}"

print(f"config: {len(out)} rows | act3={int(out.in_act3.sum())} act4={int(out.in_act4.sum())}")
print(out.groupby(["act3_family", "act3_role"], dropna=False).size().to_string())
dataiku.Dataset("demo_panel_config").write_with_schema(out)




