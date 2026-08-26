"""Act 4 — the list, and the eyeball test.

  GET /api/candidates/diseases   the diseases that have a ranked list
  GET /api/candidates            one disease's ranked candidates, filtered

Backed by `dashboard_candidates` (zone 40, 129,253 rows over 13 diseases). One
dataset, because act 4's whole job is: open a disease you know and judge the top
of the list. Everything the act needs is already a column there.
"""

from __future__ import annotations

import functools
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..dss_client import get_dataiku

router = APIRouter(prefix="/api/candidates")

DATASET = "dashboard_candidates"

# Only what act 4 renders. The dataset carries 63 columns, most of them model
# features that the UI must never surface -- see WEBAPP guardrails: `prediction`
# is deliberately absent, and the drug flags are badges, never filters.
COLS = [
    "disease_index", "disease_name", "gene_index", "gene_name",
    "rank_in_disease", "score", "rank_percentile",
    "is_target", "top_shap_drivers",
    "druggability_class", "ot_class_l1", "ot_sm_tractable", "ot_ab_tractable",
    "has_safety_liability", "safety_flag",
    "approved_for_disease", "investigational_for_disease",
]


@functools.lru_cache(maxsize=1)
def _frame():
    """Load once per process. 129k rows x 17 columns is small enough to hold, and
    the alternative -- a DSS read per request -- makes the demo feel slow."""
    df = get_dataiku().Dataset(DATASET).get_dataframe(columns=COLS)
    df["rank_in_disease"] = df["rank_in_disease"].astype(int)
    return df


@router.get("/diseases")
def diseases() -> list[dict[str, Any]]:
    """Diseases with a ranked list, largest pool first."""
    try:
        df = _frame()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read {DATASET}: {e}")
    g = (df.groupby(["disease_index", "disease_name"])
           .agg(n=("gene_index", "size"), known=("is_target", "sum"))
           .reset_index().sort_values("n", ascending=False))
    return [{"disease_index": int(r.disease_index), "disease_name": str(r.disease_name),
             "n_candidates": int(r.n), "n_known": int(r.known)} for r in g.itertuples()]


@router.get("")
def candidates(
    disease: int = Query(..., description="disease_index"),
    novel_only: bool = Query(False, description="drop genes already known for this disease"),
    tractable_only: bool = Query(False, description="small-molecule or antibody tractable"),
    exclude_secreted: bool = Query(False),
    max_rank: int = Query(200, ge=1, le=5000),
    limit: int = Query(100, ge=1, le=1000),
) -> dict[str, Any]:
    """One disease's ranked list, after the scientist's own filters.

    Returns the funnel alongside the rows: act 4 shows how a five-figure list
    narrows, and a filtered count without its cut-off is how a number acquires
    two values. The cut-off travels with the count.
    """
    try:
        df = _frame()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read {DATASET}: {e}")

    d = df[df.disease_index == disease]
    if d.empty:
        raise HTTPException(status_code=404, detail=f"No candidates for disease_index {disease}")

    funnel = [{"step": "all candidates", "n": int(len(d))}]
    if novel_only:
        d = d[d.is_target == 0]
        funnel.append({"step": "novel only", "n": int(len(d))})
    if tractable_only:
        d = d[(d.ot_sm_tractable == 1) | (d.ot_ab_tractable == 1)]
        funnel.append({"step": "+ tractable", "n": int(len(d))})
    if exclude_secreted:
        d = d[d.druggability_class.astype(str) != "secreted"]
        funnel.append({"step": "+ not secreted", "n": int(len(d))})
    d = d[d.rank_in_disease <= max_rank]
    funnel.append({"step": f"+ rank <= {max_rank}", "n": int(len(d))})

    d = d.sort_values("rank_in_disease").head(limit)
    rows = d.where(d.notna(), None).to_dict(orient="records")
    return {
        "disease_index": disease,
        "disease_name": str(df[df.disease_index == disease].disease_name.iloc[0]),
        "funnel": funnel,
        "rows": rows,
        "returned": len(rows),
    }
