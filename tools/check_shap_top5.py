#!/usr/bin/env python3
"""Check the top-5 SHAP scoring run against the chain it sits beside. Read-only.

Webapp redesign Phase 5 (scope D2) scores the champion a second time with nbExplanations = 5
(`score_persona_candidates_shap5` -> `persona2_scored_shap5` -> `candidate_shap_top5`, zone S1),
beside `score_persona_candidates` -> `persona2_scored`, which sets every rank and is not edited.
Two runs of one saved model must agree on the score; only the explanations may differ.

    python3 tools/check_shap_top5.py

  1. PREDICTIONS  every pair's proba_1 and prediction in persona2_scored_shap5 equal
                  persona2_scored's. Fails on any difference.
  2. COVERAGE     every pair of dashboard_candidates has a row in candidate_shap_top5.
                  Fails on any missing pair.
  3. AGREEMENT    the share of pairs whose two strongest drivers are the same features, in the same
                  order, as top_shap_drivers. Reported, never failed: Shapley values are estimated
                  against a sampled background, so a second run need not reproduce the first's top
                  two. A low share is investigated, not patched.

Streams the four datasets with `dku dataset download` and writes nothing to DSS.
"""
import csv
import io
import json
import re
import subprocess
import sys

PROJECT = "DEMO_TARGET_IDENTIFICATION"
# compute_top_shap_drivers_1 renders "dwpc_GGD (+0.21), rwr_score (-0.04)".
DRIVER = re.compile(r"^\s*(.*?)\s*\([+-][\d.]+\)\s*$")

csv.field_size_limit(sys.maxsize)


def rows(dataset):
    out = subprocess.run(["dku", "dataset", "download", dataset, "-", "-P", PROJECT],
                         capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"could not read {dataset}: {out.stderr.strip()}")
    return list(csv.DictReader(io.StringIO(out.stdout)))


def key(r):
    return int(float(r["disease_index"])), int(float(r["gene_index"]))


def main():
    fail = []

    old = {key(r): r for r in rows("persona2_scored")}
    new = {key(r): r for r in rows("persona2_scored_shap5")}
    diff = [k for k in old if k not in new
            or old[k]["prediction"] != new[k]["prediction"]
            or abs(float(old[k]["proba_1"]) - float(new[k]["proba_1"])) > 1e-12]
    extra = len(set(new) - set(old))
    print(f"1. predictions: {len(old):,} pairs in persona2_scored, {len(new):,} in persona2_scored_shap5; "
          f"{len(diff):,} differ or missing, {extra:,} extra")
    if diff or extra:
        fail.append("predictions")
        print("   e.g.", diff[:5])

    top5 = {key(r): json.loads(r["shap_top5"]) for r in rows("candidate_shap_top5")}
    dash = {key(r): r for r in rows("dashboard_candidates")}
    missing = [k for k in dash if k not in top5]
    print(f"2. coverage: {len(dash):,} pairs in dashboard_candidates, {len(missing):,} without a top-5 row")
    if missing:
        fail.append("coverage")
        print("   e.g.", missing[:5])

    same, differ = 0, []
    for k, r in dash.items():
        if k not in top5:
            continue
        two = [m.group(1) for m in map(DRIVER.match, (r["top_shap_drivers"] or "").split(",")) if m]
        if two == [d["feature"] for d in top5[k][:2]]:
            same += 1
        else:
            differ.append((k, r.get("gene_name"), two, [d["feature"] for d in top5[k][:2]]))
    n = same + len(differ)
    print(f"3. agreement: the two strongest drivers match top_shap_drivers for {same:,} of {n:,} pairs "
          f"({100.0 * same / n:.1f}%)" if n else "3. agreement: no pairs compared")
    for k, gene, a, b in differ[:5]:
        print(f"   {gene} {k}: stored {a} -> top-5 run {b}")

    if fail:
        sys.exit("FAIL: " + ", ".join(fail))
    print("ok")


if __name__ == "__main__":
    main()
