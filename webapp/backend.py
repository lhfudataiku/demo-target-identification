# Target Prioritizer dashboard -- backend.
#
# Serves three read-only endpoints over the flow's serving layer. NOTHING here re-ranks,
# re-scores or re-filters: the model's output is authoritative and the UI only presents it.
#
# The drug badges (`approved_for_disease` / `investigational_for_disease`) are the VALIDATION
# GROUND TRUTH. They are shipped to the client for display only. They must never be turned into
# a filter control -- filtering the shortlist by the labels the discovery lift is measured
# against would make that result circular.
import dataiku
import numpy as np
import pandas as pd
from flask import request, jsonify

# Columns sent to the client. Deliberately does NOT include `prediction`: at the F1-optimised
# threshold 590 of 762 known obesity targets are negative, so the column is actively misleading
# for discovery. Rank only.
# Sent for EVERY candidate row. Kept deliberately narrow: a disease pool is ~13k rows and the
# client holds the whole pool so that filtering (and the live count) is instant with no
# round-trip. Every field added here costs ~13k copies of itself.
BULK_COLS = [
    "gene_index", "gene_name", "rank_in_disease", "rank_percentile", "score",
    "druggability_class", "ot_class_l1", "top_shap_drivers", "is_target",
    "ot_sm_tractable", "ot_ab_tractable", "has_approved_drug", "has_safety_liability",
    "safety_events", "approved_for_disease", "investigational_for_disease",
]
# Fetched for ONE gene at a time by /gene, which also computes each value's percentile within
# the disease -- "is this high for THIS disease", not globally. Shipping these in bulk added
# ~2.5MB per request for data the UI shows one row at a time.
FEATURE_COLS = [
    ("dwpc_GGD", "Gene-gene-disease path weight"),
    ("rwr_score", "Random-walk proximity to the module"),
    ("ppi_common_neighbors", "Shared interaction partners"),
    ("prox_closest", "Closest hop to a module gene"),
    ("shared_pathway_count", "Shared pathways with the module"),
]
CANDIDATE_COLS = (["disease_index", "disease_pool_size"] + BULK_COLS
                  + [f[0] for f in FEATURE_COLS])
NUM_COLS = ["gene_index", "disease_index", "rank_in_disease", "rank_percentile",
            "disease_pool_size", "score", "is_target", "ot_sm_tractable", "ot_ab_tractable",
            "has_approved_drug", "has_safety_liability", "approved_for_disease",
            "investigational_for_disease", "dwpc_GGD", "rwr_score", "ppi_common_neighbors",
            "prox_closest", "shared_pathway_count"]

_CACHE = {}


def _num(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _load():
    """Lazy load on first request -- datasets may not be built at import time."""
    if _CACHE:
        return _CACHE

    # NOTE ON infer_with_pandas: the usual house rule is to disable inference, because dtypes are
    # otherwise guessed per 65,536-row chunk. That rule exists to protect JOIN KEYS. Here it is
    # actively wrong: disabling inference applies the DECLARED schema types, and a bigint column
    # holding nulls (persona_candidates has several -- a disease with no approved target to find
    # has a null lift) fails the parser outright with "Integer column has NA values".
    # Nothing in this module joins, and every numeric column is explicitly coerced below, so
    # pandas inference plus an explicit cast is both safe and the only thing that reads.
    cand = dataiku.Dataset("dashboard_candidates").get_dataframe(columns=CANDIDATE_COLS)
    cand = _num(cand, NUM_COLS)
    cand["safety_events"] = cand["safety_events"].fillna("").astype(str)
    for c in ["druggability_class", "ot_class_l1", "top_shap_drivers", "gene_name"]:
        cand[c] = cand[c].fillna("").astype(str)
    cand.loc[cand.druggability_class.isin(["", "unknown"]), "druggability_class"] = "unclassified"

    trust = dataiku.Dataset("persona_candidates").get_dataframe()
    trust = _num(trust, ["disease_index", "n_pos", "auc_disease", "rank_enrichment",
                         "auc_drug_targets", "approved_to_find", "approved_found50",
                         "approved_lift50", "investigational_to_find", "investigational_found50",
                         "investigational_lift50", "n_criteria", "module_size", "known_pct50"])
    trust["is_current"] = trust["is_current"].astype(str).str.lower().isin(["true", "1"])

    disc = dataiku.Dataset("novel_discovery_eval").get_dataframe()
    disc = _num(disc, [c for c in disc.columns if c not in ("disease", "ground_truth")])

    # CONSTRAINT: the picker scores 670 diseases, the explorer only holds candidate lists for
    # the personas that were materialised. The client must be able to tell them apart, or it
    # offers 670 diseases and dead-ends on most of them.
    with_candidates = set(cand.disease_index.dropna().astype(int).tolist())
    trust["has_candidates"] = trust.disease_index.fillna(-1).astype(int).isin(with_candidates)

    _CACHE["candidates"] = cand
    _CACHE["trust"] = trust
    _CACHE["discovery"] = disc
    _CACHE["classes"] = sorted(cand.druggability_class.unique().tolist())
    print(f"loaded {len(cand):,} candidate rows over {len(with_candidates)} diseases; "
          f"{len(trust):,} scored diseases; classes={_CACHE['classes']}")
    return _CACHE


def _scalar(v):
    """NaN is not valid JSON, and numpy scalars are not serialisable by jsonify."""
    if v is None:
        return None
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (np.floating, float)):
        v = float(v)
        return None if v != v else v
    if isinstance(v, np.str_):
        return str(v)
    return v


def _clean(recs):
    return [{k: _scalar(v) for k, v in r.items()} for r in recs]


@app.route("/diseases")  # noqa: F821 -- `app` is injected by DSS
def diseases():
    d = _load()
    t = d["trust"].sort_values("disease")
    return jsonify({"diseases": _clean(t.to_dict(orient="records")),
                    "classes": d["classes"]})


def _disease_rows(d, di):
    return d["candidates"][d["candidates"].disease_index == di]


@app.route("/candidates")  # noqa: F821
def candidates():
    """Columnar, not records. Repeating 16 key names across 13k rows was ~55% of the payload."""
    d = _load()
    try:
        di = int(request.args.get("disease_index"))
    except (TypeError, ValueError):
        return jsonify({"error": "disease_index required"}), 400
    sub = _disease_rows(d, di).sort_values("rank_in_disease")
    out = sub[BULK_COLS].copy()
    out["score"] = out["score"].round(4)
    out["rank_percentile"] = out["rank_percentile"].round(2)
    data = [[_scalar(v) for v in row] for row in out.itertuples(index=False, name=None)]
    return jsonify({
        "disease_index": di, "n": len(sub),
        "pool_size": int(sub["disease_pool_size"].iloc[0]) if len(sub) else 0,
        "columns": BULK_COLS, "data": data,
    })


@app.route("/gene")  # noqa: F821
def gene():
    """One candidate, with each feature placed against THIS disease's distribution."""
    d = _load()
    try:
        di = int(request.args.get("disease_index"))
        gi = int(request.args.get("gene_index"))
    except (TypeError, ValueError):
        return jsonify({"error": "disease_index and gene_index required"}), 400
    pool = _disease_rows(d, di)
    row = pool[pool.gene_index == gi]
    if not len(row):
        return jsonify({"error": "not found"}), 404
    row = row.iloc[0]
    feats = []
    for col, label in FEATURE_COLS:
        v = row[col]
        if v is None or v != v:
            continue
        vals = pool[col].dropna()
        pct = round(100.0 * float((vals < v).sum()) / len(vals), 1) if len(vals) else 0.0
        feats.append({"key": col, "label": label, "value": _scalar(v), "percentile": pct})
    return jsonify({"features": feats})


@app.route("/discovery")  # noqa: F821
def discovery():
    d = _load()
    try:
        di = int(request.args.get("disease_index"))
    except (TypeError, ValueError):
        return jsonify({"error": "disease_index required"}), 400
    sub = d["discovery"][d["discovery"].disease_index == di]
    return jsonify({"rows": _clean(sub.to_dict(orient="records"))})


@app.route("/reload")  # noqa: F821
def reload_data():
    _CACHE.clear()
    _load()
    return jsonify({"ok": True, "rows": len(_CACHE["candidates"])})
