"""nb7 — panel selection: does the Act 3 / Act 4 evidence still hold?

Guards every number in `docs/demo/panel_selection.html` and the tables beside it in
`docs/demo/panel_selection/`. Those numbers decide which disease families Act 3 carries
and which diseases Act 4 shortlists, and they are all derived from the graph — so a graph
rebuild, a re-split, or a champion change can move them silently.

Run this after ANY of:
  * the graph is rebuilt (node_index renumbers, associations change)
  * the seed gate moves (Phase 3 — the candidate population changes)
  * the champion changes (every rank is a champion score)
  * `filter_persona_diseases` is repointed (the served panel changes)

A STALE line does not mean the selection is wrong. It means the figure in the document no
longer matches the flow, and one of the two has to move. Read the direction before editing:
if a family's subtype overlap has risen, Act 3's argument weakens; if an eyeball-test rank
has fallen out of the top 50, that disease's place in Act 4 needs re-arguing.

WHAT IS NOT COMMITTED, and why: the per-row score dumps this notebook derives from
(`scored_champion` is 3.96M rows / 478 MB; the served rankings are 70 MB). They are
regenerated here rather than stored. Only the tidy derived tables live in git.
"""

from __future__ import annotations

import itertools
import json
import os

import pandas as pd

import dataiku

RESULTS: list[dict] = []
FAIL: list[tuple] = []


def check(name, doc, live, tol=0.0, fmt="{:,}"):
    ok = (abs(doc - live) <= tol) if isinstance(doc, (int, float)) else (doc == live)
    if not ok:
        FAIL.append((name, doc, live))
    RESULTS.append({"check": name, "documented": str(doc), "live": str(live),
                    "status": "PASS" if ok else "STALE"})
    print(f"CHK|{'PASS ' if ok else 'STALE'}|{name:38s} doc={fmt.format(doc):>10s} live={fmt.format(live):>10s}")


# ── 7.1  the therapeutic-area finding ────────────────────────────────────────
# `family_panel` already carries per-disease AUC, its confidence interval and the
# family anchor, so the area split is a regex over disease names -- deliberately
# the same regexes the document used, kept here so a reviewer can argue with them.
AREAS = {
    "oncology": r"cancer|carcinom|sarcoma|leukemia|lymphoma|melanoma|myeloma|glioma|blastoma|neoplasm|tumor|tumour|adenocarcinoma",
    "autoimmune": r"arthritis|lupus|psoria|crohn|colitis|inflammatory bowel|multiple sclerosis|sclerod|sjogren|vasculitis|ankylosing|spondyl|celiac|autoimmun|thyroiditis|myasthen|uveitis|dermatitis|asthma|eczema|Behcet|sarcoidosis|type 1 diabetes|graves",
    "cvrm": r"atheroscler|coronary|myocardial|heart failure|hypertens|arrhythm|fibrillation|cardiomyopath|stroke|kidney|renal|nephro|diabet|obesity|dyslipid|cholesterol|metabolic syndrome|fatty liver|hyperlip",
}
# n_pos >= 50 is the usability floor: below it an AUC interval spans half the range
# (triple-negative breast, 8 positives, interval 0.749-1.041).
USABLE_FLOOR = 50

fp = dataiku.Dataset("family_panel").get_dataframe()
names = dataiku.Dataset("persona_enrichment").get_dataframe()[["disease_index", "disease"]]
fp = fp.merge(names, on="disease_index", how="left")

# Values are literals in the loop table so tools/build_index.py can index them --
# a check() whose expected value is a dict lookup is invisible to the claims index,
# which is the difference between "a notebook exists" and "the number is tracked".
for area, doc_n, doc_usable in [("oncology", 246, 144),
                                ("autoimmune", 23, 12),
                                ("cvrm", 32, 17)]:
    m = fp[fp.disease.fillna("").str.contains(AREAS[area], case=False, regex=True)]
    check(f"7.1 {area} diseases", doc_n, len(m))
    check(f"7.1 {area} usable", doc_usable, int((m.n_pos >= USABLE_FLOOR).sum()))

# The two that decide Act 3: autoimmune has ONE family with >=2 terms, CVRM has NONE
# with >=2 usable terms -- so neither area can supply subtypes to score.
for area, doc_fams, mode in [("autoimmune", 1, "terms"), ("cvrm", 0, "usable")]:
    m = fp[fp.disease.fillna("").str.contains(AREAS[area], case=False, regex=True)]
    fams = m.groupby("disease_family_id").agg(
        terms=("disease_index", "size"),
        usable=("n_pos", lambda s: (s >= USABLE_FLOOR).sum()))
    live = int((fams.terms >= 2).sum()) if mode == "terms" \
        else int(((fams.terms >= 2) & (fams.usable >= 2)).sum())
    check(f"7.1 {area} families 2+ {mode}", doc_fams, live)

# ── 7.2  family shapes ───────────────────────────────────────────────────────
fp["usable"] = fp.n_pos >= USABLE_FLOOR
fam = fp.groupby(["disease_family_id", "anchor_name"]).agg(
    n_terms=("disease_index", "size"), n_usable=("usable", "sum")).reset_index()
check("7.2 families with 3+ terms", 25, int((fam.n_terms >= 3).sum()))

for label, fid, doc_terms, doc_usable in [("breast", 49721, 19, 14),
                                          ("lung", 52236, 17, 14),
                                          ("uterine", 44244, 8, 8),
                                          ("heme", 43521, 29, 20),
                                          ("obesity", 37143, 2, 1)]:
    row = fam[fam.disease_family_id == fid]
    check(f"7.2 {label} terms", doc_terms, int(row.n_terms.iloc[0]))
    check(f"7.2 {label} usable", doc_usable, int(row.n_usable.iloc[0]))

# ── 7.3  the served panel ────────────────────────────────────────────────────
dash = dataiku.Dataset("dashboard_candidates").get_dataframe(
    columns=["gene_index", "disease_index", "disease_name", "gene_name",
             "rank_in_disease", "is_target"])
check("7.3 served diseases", 13, dash.disease_name.nunique())
check("7.3 served rows", 129253, len(dash))

# ── 7.4  separability — what the overlap card measures ───────────────────────
# Read the curated membership from the committed table rather than restating it,
# so the notebook and the document cannot disagree about WHICH subtypes are compared.
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else "."
OV = os.path.join(HERE, "..", "docs", "demo", "panel_selection", "subtype_overlap.csv")
members: dict[str, set] = {}
for _, r in pd.read_csv(OV).iterrows():
    members.setdefault(r.family, set()).update([r.subtype_a, r.subtype_b])

NEAR_DUP = 0.6          # above this, two subtypes tell the same story
need = sorted({d for v in members.values() for d in v})
scored = dataiku.Dataset("scored_champion").get_dataframe(
    columns=["disease_index", "gene_index", "proba_1"])
idx = dict(zip(fp.disease_index, fp.disease))
scored["disease"] = scored.disease_index.map(idx)
scored = scored[scored.disease.isin(need)]
genes = dataiku.Dataset("gene_crosswalk").get_dataframe(columns=["node_index", "node_name"])
scored = scored.merge(genes.rename(columns={"node_index": "gene_index", "node_name": "gene"}),
                      on="gene_index", how="left")
scored["rank"] = scored.groupby("disease_index").proba_1.rank(ascending=False, method="first")
top50 = {d: set(g.nsmallest(50, "rank").gene) for d, g in scored.groupby("disease")}

for label, doc_dups, doc_mean in [("breast", 3, 0.4021), ("uterine", 0, 0.4935),
                                  ("stomach", 1, 0.4746), ("heme", 5, 0.5911),
                                  ("lung", 4, 0.7076)]:
    subs = [s for s in members.get(label, ()) if s in top50]
    js = [len(top50[a] & top50[b]) / len(top50[a] | top50[b])
          for a, b in itertools.combinations(sorted(subs), 2)]
    if not js:
        continue
    check(f"7.4 {label} near-duplicate pairs", doc_dups, sum(1 for j in js if j > NEAR_DUP))
    check(f"7.4 {label} mean overlap", doc_mean, round(sum(js) / len(js), 4),
          tol=0.01, fmt="{:.4f}")

# ── 7.5  the eyeball test — the bar a scientist actually applies ─────────────
# The expectations are committed in eyeball_test.csv (gene + why it is expected),
# written down BEFORE the ranks were looked up. Re-derive the ranks, not the list.
ET = os.path.join(HERE, "..", "docs", "demo", "panel_selection", "eyeball_test.csv")
expect = pd.read_csv(ET)
pool = pd.concat([
    scored[["disease", "gene", "rank"]],
    dash.rename(columns={"disease_name": "disease", "gene_name": "gene",
                         "rank_in_disease": "rank"})[["disease", "gene", "rank"]],
]).drop_duplicates(subset=["disease", "gene"])
live = expect[["disease", "gene"]].merge(pool, on=["disease", "gene"], how="left")

# The Act 4 ranking. Obesity's 0 and MS's 0 are the two rejections that rest on
# this test rather than on an aggregate, so they are asserted like any other figure.
for dis, short, doc_20 in [("rheumatoid arthritis", "RA", 4),
                           ("psoriatic arthritis", "PsA", 2),
                           ("atopic eczema", "eczema", 3),
                           ("dilated cardiomyopathy", "DCM", 3),
                           ("familial hypercholesterolemia", "FH", 3),
                           ("endometrium adenocarcinoma", "endometrioid", 4),
                           ("obesity disorder", "obesity", 0)]:
    check(f"7.5 {short} targets in top20", doc_20,
          int((live[live.disease == dis]["rank"] <= 20).sum()))
check("7.5 MS targets in top50", 0,
      int((live[live.disease == "multiple sclerosis"]["rank"] <= 50).sum()))

# ── 7.6  the module bias, stated as a number ─────────────────────────────────
# Obesity's top 50 is dominated by the BBSome -- a dense protein complex, which is
# exactly what PPI-topology features reward. Neither diabetes term shows it, so this
# is specific rather than a general artefact. If that stops being true, the reason
# obesity was cut stops being true with it.
BBS = r"^(BBS\d+|BBIP1|ARL6|TTC8|MKKS|LZTFL1|SDCCAG8|WDPCP|TRIM32|IFT27|IFT172)$"
for dis, doc_bbs in [("obesity disorder", 9), ("diabetes mellitus", 0)]:
    g = dash[dash.disease_name == dis].nsmallest(50, "rank_in_disease")
    check(f"7.6 {dis} BBS genes in top50", doc_bbs, int(g.gene_name.str.match(BBS).sum()))

# ── close ────────────────────────────────────────────────────────────────────
out = pd.DataFrame(RESULTS)
print(f"\n{len(out)} checks — {(out.status == 'PASS').sum()} PASS, {(out.status == 'STALE').sum()} STALE")
if FAIL:
    print("\nSTALE figures — the document and the flow disagree:")
    for name, doc, liveval in FAIL:
        print(f"  {name}: documented {doc}, live {liveval}")
    print("\nDecide which moves. Do not edit DECISIONS.md in place — append a correction.")
else:
    print("\nEvery figure in docs/demo/panel_selection.html still matches the flow.")
