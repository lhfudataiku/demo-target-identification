"""Act 4 — the list, and the eyeball test.

  GET /api/candidates/diseases   the diseases that have a ranked list
  GET /api/candidates            one disease's ranked candidates, filtered
  GET /api/candidates/gene       one candidate, against its own disease's spread
  GET /api/candidates/identity   one gene's HGNC identity, from the preloaded S1 dataset
  GET /api/candidates/drugs      the drug records behind one pair's drug badges (S1)
  GET /api/candidates/drivers    one pair's top-5 SHAP drivers with percentiles (S1)

Backed by `dashboard_candidates` (zone 40; one row per disease-candidate pair,
105,702 rows over 12 diseases when measured on 2026-10-23 -- /diseases serves the
live list). One dataset, because act 4's whole job is: open a disease you know and
judge the top of the list. Everything the act needs is already a column there.
"""

from __future__ import annotations

import functools
import json
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
    "is_target",
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


# The gene's HGNC identity, PRELOADED (redesign D16): `candidate_identity` (zone S1) is
# the graph's gene nodes left-joined to one dated HGNC complete-set file, which Part 1's
# compute_hgnc_identity reads and Part 2 syncs. Nothing is fetched per click, and the
# backend reads only this serving dataset -- not graph_nodes (D14).
IDENTITY = "candidate_identity"
IDENTITY_COLS = ["node_index", "node_id", "node_name", "hgnc_id", "symbol", "name", "locus_type",
                 "location", "alias_symbol", "prev_symbol", "gene_group", "date_modified",
                 "ensembl_gene_id", "uniprot_ids", "source_file"]
# HGNC ships these pipe-separated; the page shows them as lists.
LIST_COLS = ("alias_symbol", "prev_symbol", "gene_group", "uniprot_ids")


@functools.lru_cache(maxsize=2)
def _identity_at(stamp: str) -> dict[int, dict[str, Any]]:
    """gene_index -> its row. `stamp` is the cache key only."""
    df = dataset_cache.frame(IDENTITY, IDENTITY_COLS)
    out = {}
    for r in df.to_dict("records"):
        r = {k: (None if v is None or v != v or v == "" else v) for k, v in r.items()}
        out[int(r["node_index"])] = r
    return out


@router.get("/identity")
def gene_identity(gene: int = Query(..., description="gene_index")) -> dict[str, Any]:
    """The candidate's HGNC record, for the header of the selected candidate.

    `found: false` when the dated HGNC file has no record for the gene's NCBI Gene ID
    (one gene node of 20,861 on the 2026-10-06 file, PGM5P1).
    """
    try:
        ids = _identity_at(dataset_cache.build_stamp(IDENTITY))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read {IDENTITY}: {e}")
    r = ids.get(gene)
    if r is None:
        raise HTTPException(status_code=404, detail=f"gene_index {gene} is not a gene node")
    # Read back with pandas type inference, an all-digit ID arrives as a number.
    base = {"gene_index": gene, "ncbi_gene_id": str(r["node_id"]), "graph_symbol": r["node_name"],
            "source": "HGNC complete set", "source_file": r["source_file"]}
    if not r["hgnc_id"]:
        return {**base, "found": False}
    return {**base, "found": True,
            **{k: r[k] for k in ("hgnc_id", "symbol", "name", "locus_type", "location",
                                 "date_modified", "ensembl_gene_id")},
            **{k: (r[k].split("|") if r[k] else []) for k in LIST_COLS}}


# The drug records behind the two badges (redesign D7): `drug_evidence_records` (zone S1) holds one
# row per pair x drug, built with visual recipes from the same drug_disease_edges and
# drug_protein_edges that compute_drug_evidence_pairs reduces to two flags. It covers every linked
# pair (86,123 records on 2026-10-26), not only candidates, so it does not depend on the scoring
# chain. Grouping it by pair reproduces both flags for every row of dashboard_candidates.
DRUGS = "drug_evidence_records"
DRUG_COLS = ["disease_index", "gene_index", "drug_id", "drug_name", "max_stage", "relation",
             "action_type", "source_release"]
# Most advanced first. UNKNOWN is a programme whose stage Open Targets does not record, so it
# sorts last rather than being read as early.
STAGE_ORDER = ["APPROVAL", "PREAPPROVAL", "PHASE_3", "PHASE_2_3", "PHASE_2", "PHASE_1_2", "PHASE_1",
               "EARLY_PHASE_1", "IND", "PRECLINICAL", "UNKNOWN"]


@functools.lru_cache(maxsize=2)
def _drugs_at(stamp: str) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """(disease_index, gene_index) -> its records. `stamp` is the cache key only."""
    df = dataset_cache.frame(DRUGS, DRUG_COLS)
    out: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for r in df.to_dict("records"):
        r = {k: (None if v is None or v != v or v == "" else v) for k, v in r.items()}
        r["drug_id"] = str(r["drug_id"])
        # A drug with two recorded actions on the protein carries both, pipe-separated.
        r["action_type"] = r["action_type"].split("|") if r["action_type"] else []
        out.setdefault((int(r.pop("disease_index")), int(r.pop("gene_index"))), []).append(r)
    rank = {s: i for i, s in enumerate(STAGE_ORDER)}
    for recs in out.values():
        recs.sort(key=lambda r: (rank.get(r["max_stage"], len(rank)), r["drug_name"] or ""))
    return out


@router.get("/drugs")
def pair_drugs(disease: int = Query(..., description="disease_index"),
               gene: int = Query(..., description="gene_index")) -> dict[str, Any]:
    """The drugs that act on the gene AND are approved or investigated for exactly this disease.

    An empty list means no link in the snapshot, not no drug: the link is exact-node, so a drug
    approved for a broader disease term does not appear here.
    """
    try:
        recs = _drugs_at(dataset_cache.build_stamp(DRUGS))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read {DRUGS}: {e}")
    return {"disease_index": disease, "gene_index": gene, "records": recs.get((disease, gene), [])}


# The top five SHAP drivers (redesign D2): `candidate_shap_top5` (zone S1) is a SECOND scoring run of
# the champion with nbExplanations = 5, beside the chain that writes top_shap_drivers. Each driver
# carries its value and its percentile in the disease's pool, computed in compute_shap_top5 by the
# same rule as /gene above -- including prox_kernel, which dashboard_candidates cannot show.
SHAP5 = "candidate_shap_top5"


@functools.lru_cache(maxsize=2)
def _shap5_at(stamp: str) -> dict[tuple[int, int], str]:
    """(disease_index, gene_index) -> its JSON list, parsed per request. `stamp` is the cache key only."""
    df = dataset_cache.frame(SHAP5, ["disease_index", "gene_index", "shap_top5"])
    return {(int(d), int(g)): j for d, g, j in df.itertuples(index=False)}


@router.get("/drivers")
def pair_drivers(disease: int = Query(..., description="disease_index"),
                 gene: int = Query(..., description="gene_index")) -> dict[str, Any]:
    """Up to five drivers, strongest |SHAP| first, each with its within-disease percentile."""
    try:
        rows = _shap5_at(dataset_cache.build_stamp(SHAP5))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read {SHAP5}: {e}")
    raw = rows.get((disease, gene))
    if raw is None:
        raise HTTPException(status_code=404, detail=f"No scored row for disease {disease}, gene {gene}")
    drivers = [{"key": d["feature"], "label": feature_glossary.LABEL.get(d["feature"]),
                "kind": feature_glossary.KIND.get(d["feature"]),
                "direction": "lower" if d["feature"] in feature_glossary.LOWER_IS_STRONGER else "higher",
                "shap": d["shap"], "value": d["value"], "percentile": d["percentile"]}
               for d in json.loads(raw)]
    return {"disease_index": disease, "gene_index": gene, "n_features": len(feature_glossary.CHAMPION),
            "drivers": drivers}
