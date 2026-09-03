"""Act 4 — the list, and the eyeball test.

  GET /api/candidates/diseases   the diseases that have a ranked list
  GET /api/candidates            one disease's ranked candidates, filtered
  GET /api/candidates/gene       one candidate, against its own disease's spread

Backed by `dashboard_candidates` (zone 40, 129,253 rows over 13 diseases). One
dataset, because act 4's whole job is: open a disease you know and judge the top
of the list. Everything the act needs is already a column there.
"""

from __future__ import annotations

import functools
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from .. import feature_glossary
from ..dss_client import get_dataiku
from ..services import dataset_cache

router = APIRouter(prefix="/api/candidates")

DATASET = "dashboard_candidates"

# Sent for EVERY row of a disease's list. Narrow on purpose: the client holds the
# whole filtered pool so the view controls filter with no round-trip, and every
# column added here costs one copy per row. `prediction` is deliberately absent
# and the drug flags are badges, never filters -- see the WEBAPP guardrails.
BULK_COLS = [
    "disease_index", "disease_name", "gene_index", "gene_name",
    "rank_in_disease", "score", "rank_percentile",
    "is_target", "top_shap_drivers",
    "druggability_class", "ot_class_l1", "ot_sm_tractable", "ot_ab_tractable",
    "has_safety_liability", "safety_flag",
    "approved_for_disease", "investigational_for_disease",
]

# Fetched for ONE gene at a time by /gene, which places each value against THIS
# disease's own distribution -- "is this high for this disease", never globally.
# Shipping them in bulk cost ~2.5 MB per request in webapp v1 for data the UI
# shows one row at a time, which is why they are not in BULK_COLS.
#
# THE LIST IS THE CHAMPION'S OWN INPUTS, not a curation. webapp v1's drawer
# showed five features of which THREE -- rwr_score, ppi_common_neighbors,
# shared_pathway_count -- are not inputs to m7-f14 at all; they are columns the
# dataset happens to carry. Placing a non-feature under the heading "why this
# gene?" answers a question the model never asked, so the set is derived from
# feature_glossary.CHAMPION instead of hand-picked, and it moves when the model
# does.
#
# `prox_kernel` is the one champion input this dataset cannot show: it is
# produced by compute_enriched_prox_closest but never propagates into
# `dashboard_candidates`. The card SAYS SO rather than showing 13 of 14 as if
# that were all of them.
MISSING_FEATURES: list[str] = ["prox_kernel"]

FEATURE_COLS: list[tuple[str, str, str]] = [
    (f, feature_glossary.LABEL[f], feature_glossary.KIND[f])
    for f in feature_glossary.CHAMPION
    if f not in MISSING_FEATURES
]

# Read for the detail card only, for the same reason.
#   disease_pool_size -- the DENOMINATOR `rank_percentile` was computed against
#     (finalize_dashboard_candidates: 1000*rank/pool_size/10). Deriving the pool
#     from len(rows) instead would let the "of N" disagree with the percentile
#     beside it the moment the two ever diverge.
#   safety_events -- the free-text annotation behind `has_safety_liability`.
DETAIL_COLS = ["disease_pool_size", "safety_events"]

# What the cached frame actually loads.
COLS = BULK_COLS + DETAIL_COLS + [c for c, _, _ in FEATURE_COLS]


@functools.lru_cache(maxsize=4)
def _typed(name: str, stamp: str):
    """The frame with rank coerced to int, cached against the same build stamp as
    the underlying frame so a rebuild refreshes both."""
    df = dataset_cache.frame(name, COLS).copy()
    df["rank_in_disease"] = df["rank_in_disease"].astype(int)
    return df


def _frame():
    """105k rows x 17 columns, held in memory because a DSS read per request makes
    the demo feel slow -- but keyed on the dataset's build, so a rebuild is picked
    up without restarting the backend. See services/dataset_cache.py."""
    return _typed(DATASET, dataset_cache.build_stamp(DATASET))


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

    # Every row that survives the filters, not an arbitrary head(). `max_rank`
    # is the only bound, and it is a control the scientist sets — so the table
    # can never be quietly shorter than the funnel says.
    d = d.sort_values("rank_in_disease")
    # Projected to BULK_COLS explicitly. The frame also carries the feature and
    # detail columns for /gene, and without this they would ride along on every
    # row of a five-figure list — the exact cost the two column lists exist to
    # avoid.
    d = d[BULK_COLS]
    rows = d.where(d.notna(), None).to_dict(orient="records")
    return {
        "disease_index": disease,
        "disease_name": str(df[df.disease_index == disease].disease_name.iloc[0]),
        "funnel": funnel,
        "rows": rows,
        "returned": len(rows),
        # `top_shap_drivers` is a rendered string of COLUMN names, and the table
        # was showing them raw ("dwpc_GGD (+0.21)"). The detail drawer already
        # resolves them, but only for the one selected gene. Fourteen entries,
        # sent once per disease rather than per row -- and sourced here rather
        # than restated in the frontend, because feature_glossary.py owns the
        # model's feature wording (WEBAPP_DESIGN.md 3.7).
        "feature_labels": dict(feature_glossary.LABEL),
    }


def _scalar(v: Any) -> Any:
    """A numpy cell as something JSON can carry.

    NaN is not valid JSON and numpy scalars are not serialisable, so both are
    normalised here. Ported from webapp v1, where the same two cases were the
    only ones this dataset ever produced.
    """
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (float, np.floating)):
        f = float(v)
        return None if f != f else f
    if isinstance(v, np.str_):
        return str(v)
    return v


@router.get("/gene")
def gene_detail(
    disease: int = Query(..., description="disease_index"),
    gene: int = Query(..., description="gene_index"),
) -> dict[str, Any]:
    """One candidate, with each feature placed against THIS disease's distribution.

    The percentile is the whole point of the endpoint. A raw feature value means
    nothing on its own — `dwpc_GGD = 0.004` is high for one disease and
    unremarkable for another — so every value is ranked within its own disease's
    pool. The same gene can sit at the 96th percentile here and the 40th for
    another disease on an identical raw value.

    Only the champion's features and the pool-relative facts are returned.
    Everything else the detail card renders is already in the list payload, so
    re-sending it would be a second copy of a row the client is holding.
    """
    try:
        df = _frame()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read {DATASET}: {e}")

    pool = df[df.disease_index == disease]
    if pool.empty:
        raise HTTPException(status_code=404, detail=f"No candidates for disease_index {disease}")
    hit = pool[pool.gene_index == gene]
    if hit.empty:
        raise HTTPException(status_code=404,
                            detail=f"gene_index {gene} is not in disease {disease}'s pool")
    row = hit.iloc[0]

    features = []
    for col, label, kind in FEATURE_COLS:
        v = row[col]
        # A null feature is dropped rather than shown as zero: "no path of this
        # kind exists" and "a path of weight 0" are different claims, and only
        # one of them is true.
        if v is None or v != v:
            continue
        vals = pool[col].dropna()
        # The share of this disease's pool the candidate is STRONGER than --
        # measured in whichever direction the feature counts. For hop distance
        # that is the share sitting further away, not nearer; ranking it upward
        # like the rest draws an empty bar for a gene one hop from the module,
        # which is the best value the feature can take.
        #
        # Strict inequality both ways, so ties never inflate the number. A
        # saturated feature (shared_pathway_frac = 1.0 for most of the pool)
        # therefore reads modestly rather than as a 100th percentile, which is
        # the honest reading of a tie.
        lower_wins = col in feature_glossary.LOWER_IS_STRONGER
        beaten = float((vals > v).sum()) if lower_wins else float((vals < v).sum())
        pct = round(100.0 * beaten / len(vals), 1) if len(vals) else 0.0
        features.append({"key": col, "label": label, "kind": kind,
                         "direction": "lower" if lower_wins else "higher",
                         "value": _scalar(v), "percentile": pct})

    return {
        "disease_index": disease,
        "gene_index": gene,
        # The denominator behind `rank_percentile`, not len(pool) — see DETAIL_COLS.
        "pool_size": _scalar(row["disease_pool_size"]),
        "safety_events": _scalar(row["safety_events"]),
        "features": features,
        # Named, not silently omitted -- see MISSING_FEATURES.
        "missing_features": MISSING_FEATURES,
    }
