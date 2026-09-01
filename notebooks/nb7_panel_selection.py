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
check("7.3 served diseases", 12, dash.disease_name.nunique())
check("7.3 served rows", 105702, len(dash))

# ── 7.4  separability — what the overlap card measures ──────────────────────
# Reads the BUILT dataset now, not a recomputation. The card is `family_panel_overlap`
# and if that table drifts the card drifts with it, so this is the thing to assert.
#
# These figures cover every usable term PLUS the leaves -- the card's actual basis.
# They differ from the pre-build analysis in docs/demo/panel_selection/analysis/, which
# averaged only the curated candidate subtypes (breast 0.4021 / uterine 0.4935 /
# stomach 0.4746). Same method; different set of pairs averaged. The pairs common to
# both agree to four decimal places, so a difference here is a set difference and never
# drift. Direction is family-specific: breast's extra terms are umbrella terms that
# blend their children and raise the mean, uterine's and stomach's extras are more
# distinct and lower it.
ov = dataiku.Dataset("family_panel_overlap").get_dataframe()
check("7.4 overlap pairs", 148, len(ov))
check("7.4 spearman depth_gap vs jaccard", -0.350,
      round(ov.depth_gap.rank().corr(ov.jaccard_top50.rank()), 3), tol=0.02, fmt="{:.3f}")

for fam, doc_pairs, doc_mean, doc_near in [("breast", 105, 0.4299, 22),
                                           ("uterine", 28, 0.4777, 1),
                                           ("stomach", 15, 0.4510, 3)]:
    g = ov[ov.act3_family == fam]
    check(f"7.4 {fam} overlap pairs", doc_pairs, len(g))
    check(f"7.4 {fam} mean overlap", doc_mean, round(g.jaccard_top50.mean(), 4),
          tol=0.01, fmt="{:.4f}")
    check(f"7.4 {fam} near-duplicate pairs", doc_near, int(g.near_duplicate.sum()))

# The pair nb4 and nb6 also assert on -- kept here so a change to the novel ranking
# is caught in one place rather than three.
kp = ov[(ov.disease_a.str.contains("HER2") & ov.disease_b.str.contains("triple"))
        | (ov.disease_b.str.contains("HER2") & ov.disease_a.str.contains("triple"))]
check("7.4 HER2+ vs TNBC novel overlap", 2, int(kp.novel_overlap.iloc[0]))
check("7.4 HER2+ vs TNBC all overlap", 14, int(kp.all_overlap.iloc[0]))

# ── 7.4b  the common-vs-specific card ───────────────────────────────────────
# One classification axis per family. Breast is molecular only: including the
# histology terms (ductal, lobular) left HER2+ with ONE specific gene, because
# ductal overlaps it 85% and absorbed the rest.
pg = dataiku.Dataset("family_panel_programme").get_dataframe()
for fam, doc_leaves, doc_common in [("breast", 4, 8), ("uterine", 4, 24), ("stomach", 3, 17)]:
    g = pg[pg.act3_family == fam]
    check(f"7.4b {fam} leaves", doc_leaves, g.subtype.nunique())
    check(f"7.4b {fam} common genes", doc_common,
          g[g.scope == "common"].gene.nunique())

# ── 7.4c  the config is the single source of panel membership ───────────────
cfgd = dataiku.Dataset("demo_panel_config").get_dataframe()
check("7.4c config rows", 35, len(cfgd))
check("7.4c act3 terms", 28, int(cfgd.in_act3.sum()))
check("7.4c act4 diseases", 12, int(cfgd.in_act4.sum()))

# ── 7.5  the eyeball test — the bar a scientist actually applies ─────────────
# The expectations live in docs/demo/panel_selection/eyeball_test.csv, one row per
# (disease, gene) with a `why_expected` naming the drug or the biology. That list was
# written down BEFORE the ranks were looked up; this re-derives the RANKS only, so
# the test cannot be quietly reshaped to fit the result.
#
# Only the SERVED diseases are asserted. Six diseases in that file are no longer in
# the panel (obesity, multiple sclerosis, SLE, atopic eczema, myeloma, ALL) -- their
# ranks are the evidence for rejecting them, recorded in the CSV, and there is
# nothing live left to guard. Obesity's GLP1R #526 and MS's 0-of-8 are the two that
# decided those cuts.
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else "."
ET = os.path.join(HERE, "..", "docs", "demo", "panel_selection", "analysis", "eyeball_test.csv")
expect = pd.read_csv(ET)

served = dash.rename(columns={"disease_name": "disease", "gene_name": "gene",
                              "rank_in_disease": "rank"})[["disease", "gene", "rank"]]
live = expect[["disease", "gene"]].merge(served, on=["disease", "gene"], how="left")

for dis, short, doc_20 in [("endometrium adenocarcinoma", "endometrioid", 4),
                           ("rheumatoid arthritis", "RA", 4),
                           ("dilated cardiomyopathy", "DCM", 3),
                           ("endometrial serous adenocarcinoma", "serous", 3),
                           ("familial hypercholesterolemia", "FH", 3),
                           ("gastric adenocarcinoma", "gastric", 3),
                           ("psoriatic arthritis", "PsA", 2)]:
    check(f"7.5 {short} targets in top20", doc_20,
          int((live[live.disease == dis]["rank"] <= 20).sum()))

# ── 7.6  the module bias, recorded rather than re-derived ───────────────────
# Obesity's top 50 was 9/50 Bardet-Biedl (BBSome) genes while neither diabetes term
# had one -- a dense protein complex lighting up PPI-topology features. That is why
# obesity was cut, and with it out of the panel there is no live table to re-measure
# it from; the figure lives in docs/demo/panel_selection/. What IS still checkable is
# that the diabetes contrast holds, since diabetes mellitus is still served.
BBS = r"^(BBS\d+|BBIP1|ARL6|TTC8|MKKS|LZTFL1|SDCCAG8|WDPCP|TRIM32|IFT27|IFT172)$"
g = dash[dash.disease_name == "diabetes mellitus"].nsmallest(50, "rank_in_disease")
check("7.6 diabetes BBS genes in top50", 0, int(g.gene_name.str.match(BBS).sum()))

# ── close ────────────────────────────────────────────────────────────────────
out = pd.DataFrame(RESULTS)
print(f"\n{len(out)} checks — {(out.status == 'PASS').sum()} PASS, {(out.status == 'STALE').sum()} STALE")
if FAIL:
    print("\nSTALE figures — the document and the flow disagree:")
    for name, doc, liveval in FAIL:
        print(f"  {name}: documented {doc}, live {liveval}")
    print("\nDecide which moves. Record only a durable choice in docs/decisions/DECISION_REGISTER.md;")
    print("routine refresh results belong in the build ledger, not the decision register.")
else:
    print("\nEvery figure in docs/demo/panel_selection.html still matches the flow.")
