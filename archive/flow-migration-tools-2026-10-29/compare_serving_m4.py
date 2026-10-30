"""Compare M4's rebuilt served datasets with the ones the webapp reads today (workplan M4).

READ-ONLY: it reads DEMO_TARGET_IDENTIFICATION and writes nothing to DSS. Each dataset is pulled
once into data/serving_m4/ (never committed); --refresh pulls again.

    uv run --project notebooks python tools/compare_serving_m4.py [--refresh]

Three comparisons, each keyed and checked for rows, keys, columns, types and values (floats within
1e-9 relative, NaN equal to NaN):
  - dashboard_candidates_m4 against dashboard_candidates, on the 32 served columns. The other 31
    old columns are dropped on purpose (map §2.1). Ranks are checked against the prediction
    instead of for equality (DEC-MEAS-005): the new rank is the lowest old rank in its tie group
    (disease, score), and rank_percentile is recomputed from that rank. disease_pool_size must
    equal the stored one.
  - validation_auc_by_disease_m4 against validation_auc_ci, plus persona_enrichment's `disease`,
    `module_size` and `rank_enrichment`.
  - family_auc_by_family_m4 against family_auc_by_family.
Exit 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_evidence_project import MAIN  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "serving_m4"
RTOL = 1e-9


def pull(name: str, refresh: bool) -> pd.DataFrame:
    path = CACHE / (name + ".pkl")
    if refresh or not path.exists():
        import os

        import dataiku
        dataiku.set_remote_dss(os.environ["DKU_URL"].rstrip("/"), os.environ["DKU_API_KEY"])
        CACHE.mkdir(parents=True, exist_ok=True)
        dataiku.Dataset("%s.%s" % (MAIN, name)).get_dataframe().to_pickle(path)
    return pd.read_pickle(path)


def equal(a: pd.Series, b: pd.Series) -> pd.Series:
    """Element-wise equality: numbers within RTOL, NaN equal to NaN, else exact."""
    an, bn = pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")
    # Numeric when every non-empty value on both sides parses as a number. Requiring a value on
    # every row sent a column with any NaN to the string comparison, where last-digit float noise
    # (1e-16 relative) showed as differences.
    if (a.notna() == an.notna()).all() and (b.notna() == bn.notna()).all():
        both_nan = an.isna() & bn.isna()
        close = np.isclose(an.astype(float), bn.astype(float), rtol=RTOL, atol=0, equal_nan=True)
        return pd.Series(close, index=a.index) | both_nan
    return (a.astype(str) == b.astype(str)) | (a.isna() & b.isna())


def compare(label, new, old, keys, columns, report, skip=()):
    print("\n== %s" % label)
    ok = True
    if len(new) != len(old):
        print("  rows %d new vs %d old" % (len(new), len(old)))
        ok = False
    for side, df in (("new", new), ("old", old)):
        if df.duplicated(keys).any():
            print("  duplicate keys in %s: %d" % (side, df.duplicated(keys).sum()))
            ok = False
    j = new.merge(old, on=keys, how="outer", suffixes=("_new", "_old"), indicator=True)
    only = j._merge.value_counts().to_dict()
    if only.get("left_only", 0) or only.get("right_only", 0):
        print("  keys only in new %d, only in old %d" % (only.get("left_only", 0), only.get("right_only", 0)))
        ok = False
    j = j[j._merge == "both"]
    missing = [c for c in columns if c not in new.columns]
    if missing:
        print("  columns missing from new: %s" % missing)
        ok = False
    for c in columns:
        if c in keys or c in skip or c in missing:
            continue
        a, b = j[c + "_new"] if c + "_new" in j else j[c], j[c + "_old"] if c + "_old" in j else j[c]
        bad = ~equal(a.reset_index(drop=True), b.reset_index(drop=True))
        if bad.any():
            print("  %-28s %d rows differ, e.g. %s" % (c, bad.sum(),
                  list(zip(a.reset_index(drop=True)[bad].head(3), b.reset_index(drop=True)[bad].head(3)))))
            ok = False
        if str(new[c].dtype) != str(old[c].dtype):
            report.append("%s.%s: %s -> %s" % (label, c, old[c].dtype, new[c].dtype))
    print("  rows %d, %s" % (len(new), "values equal" if ok else "DIFFERENCES above"))
    return ok, j


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--refresh", action="store_true", help="pull every dataset again")
    args = ap.parse_args()
    from build_serving_m4 import SERVED
    types = []
    results = []

    # Shortlist.
    new, old = pull("dashboard_candidates_m4", args.refresh), pull("dashboard_candidates", args.refresh)
    keys = ["disease_index", "gene_index"]
    ok, j = compare("dashboard_candidates", new, old, keys, SERVED, types,
                    skip=("rank_in_disease", "rank_percentile"))
    tie_low = j.groupby(["disease_index", "score_old"]).rank_in_disease_old.transform("min")
    predicted = tie_low.astype(int)
    rank_ok = (j.rank_in_disease_new.astype(int) == predicted)
    moved = (j.rank_in_disease_new != j.rank_in_disease_old)
    tied = j.duplicated(["disease_index", "score_old"], keep=False)
    # Half up, as GREL's round() does; numpy's round goes to even and missed 4 exact halves.
    pct = np.floor(1000.0 * predicted / j.disease_pool_size_old + 0.5) / 10.0
    pct_ok = np.isclose(j.rank_percentile_new.astype(float), pct, rtol=RTOL, atol=0)
    print("  rank_in_disease: %d of %d as predicted; %d changed, %d of them untied" % (
        rank_ok.sum(), len(j), moved.sum(), (moved & ~tied).sum()))
    print("  rank_percentile: %d of %d equal the prediction; %d changed" % (
        pct_ok.sum(), len(j), (~np.isclose(j.rank_percentile_new.astype(float),
                                            j.rank_percentile_old.astype(float), rtol=RTOL, atol=0)).sum()))
    results.append(ok and rank_ok.all() and pct_ok.all())

    # Per-disease AUC.
    new = pull("validation_auc_by_disease_m4", args.refresh)
    ci = pull("validation_auc_ci", args.refresh)
    pe = pull("persona_enrichment", args.refresh)[["disease_index", "disease", "module_size", "rank_enrichment"]]
    old = ci.merge(pe, on="disease_index", how="left")
    ok, _ = compare("validation_auc_by_disease", new, old, ["disease_index"], list(old.columns), types)
    results.append(ok)

    # Per-family AUC.
    new, old = pull("family_auc_by_family_m4", args.refresh), pull("family_auc_by_family", args.refresh)
    ok, _ = compare("family_auc_by_family", new, old, ["disease_family_id"], list(old.columns), types)
    results.append(ok)

    if types:
        print("\ntype changes (values compared numerically):\n  " + "\n  ".join(types))
    print("\n%s" % ("ALL MATCH" if all(results) else "DIFFERENCES: see above"))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
