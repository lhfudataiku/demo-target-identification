"""Act 2 — calibration.

  GET /api/calibration   the AUC distribution, the hub-bias meter, orthogonality

Read the AUC as RECONSTRUCTION FIDELITY, not predictive power: across 670
diseases, how reliably do already-validated targets land near the top.

Three things this act must show together, because each is dishonest alone:
  - the distribution, not a summary (usefulness is not uniform);
  - the hub-bias counter-measurement (the model under-scores under-studied
    true targets, and we say so);
  - orthogonality (a high association AUC does not buy therapeutic relevance).
"""

from __future__ import annotations

import functools
import math
from typing import Any

from fastapi import APIRouter, HTTPException

from ..dss_client import get_dataiku

router = APIRouter(prefix="/api/calibration")


@functools.lru_cache(maxsize=1)
def _ds(name: str):
    return get_dataiku().Dataset(name).get_dataframe()


def _hist(values: list[float], lo: float, hi: float, bins: int) -> list[dict[str, Any]]:
    step = (hi - lo) / bins
    out = [{"lo": round(lo + i * step, 3), "hi": round(lo + (i + 1) * step, 3), "n": 0}
           for i in range(bins)]
    for v in values:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        i = min(bins - 1, max(0, int((v - lo) / step)))
        out[i]["n"] += 1
    return out


@router.get("")
def calibration() -> dict[str, Any]:
    try:
        auc = _ds("validation_auc_by_disease")
        hub = _ds("hub_bias_meter")
        orth = _ds("orthogonality_scatter")
        split = _ds("split_audit_2")
        drivers = _ds("shap_driver_frequency")
        elig = _ds("disease_eligibility")
        fam = _ds("family_auc_by_family")
        personas = _ds("persona_enrichment")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read a calibration dataset: {e}")

    vals = [float(v) for v in auc.auc_disease.dropna()]
    macro = sum(vals) / len(vals) if vals else float("nan")

    o = orth.dropna(subset=["auc_disease", "auc_drug_targets"])
    x = [float(v) for v in o.auc_disease]
    y = [float(v) for v in o.auc_drug_targets]
    n = len(x)
    if n > 1:
        mx, my = sum(x) / n, sum(y) / n
        sx = math.sqrt(sum((v - mx) ** 2 for v in x))
        sy = math.sqrt(sum((v - my) ** 2 for v in y))
        r = sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else 0.0
    else:
        r = 0.0

    # Where the candidates come from, and the split's integrity. The overlap
    # columns are the load-bearing ones: they must all be zero, and showing the
    # zero is the point -- a split you cannot audit is not a split.
    splits = [{
        "split": str(r.split),
        "rows": int(r.rows),
        "positives": int(r.positives),
        "pos_rate_pct": round(float(r.pos_rate_pct), 3),
        "n_diseases": int(r.n_diseases),
        "n_split_keys": int(r.n_split_keys),
        "n_anchor_families": int(r.n_anchor_families),
    } for r in split.itertuples()]
    overlap_cols = [c for c in split.columns if c.startswith("overlap_") or c.startswith("strad")]
    leakage = {c: int(split[c].sum()) for c in overlap_cols}

    drv = drivers.sort_values("count", ascending=False)

    # v3 colours the driver bars in TWO groups, not a cycle: provenance features
    # against everything else. The grouping is a curation, not data -- it is the
    # same "kind" column the feature-glossary card renders.
    KIND = {
        "dwpc_GGD": "path", "dwpc_GPGD": "path", "dwpc_GBGD": "path", "dwpc_GFGD": "path",
        "prox_closest": "proximity", "prox_kernel": "proximity", "rwr_score": "proximity",
        "rwr_norm": "proximity", "disease_context": "proximity",
        "ppi_common_neighbors_z": "topology", "ppi_adamic_adar": "topology",
        "ppi_jaccard": "topology", "ppi_common_neighbors": "topology",
        "gene_ppi_degree": "topology", "gene_n_pathways": "topology",
        "gene_n_diseases": "topology", "module_size": "topology",
        "shared_pathway_count": "topology", "shared_pathway_frac": "topology",
        "ppi_evidence_depth": "provenance", "ppi_multi_source_frac": "provenance",
        "ppi_edges_with_provenance": "provenance",
    }
    GLOSSARY = [
        ("dwpc_GGD", "path", "degree-weighted count of paths reaching the disease through an interacting gene"),
        ("dwpc_GPGD", "path", "the same, through a shared pathway"),
        ("dwpc_GBGD", "path", "the same, through a shared biological process"),
        ("dwpc_GFGD", "path", "the same, through a shared molecular function"),
        ("prox_closest", "proximity", "hops to the nearest gene already annotated for this disease"),
        ("prox_kernel", "proximity", "diffusion proximity to the whole disease module, distance-weighted"),
        ("ppi_common_neighbors_z", "topology", "partners shared with the module, z-scored against what degree alone predicts"),
        ("ppi_adamic_adar", "topology", "shared partners, weighted so rare partners count for more"),
        ("ppi_jaccard", "topology", "shared partners as a fraction of the union"),
        ("gene_ppi_degree", "topology", "how many interaction partners the gene has at all"),
        ("gene_n_pathways", "topology", "how many pathways the gene belongs to"),
        ("module_size", "topology", "how many genes are already annotated for the disease"),
        ("ppi_evidence_depth", "provenance", "how many independent sources assert the gene's interactions"),
        ("ppi_multi_source_frac", "provenance", "the share of its interactions carrying more than one source"),
    ]

    tot_elig = int(elig["count"].sum())
    n_elig = int(elig.loc[elig.is_eligible == 1, "count"].sum())

    fam_vals = [float(v) for v in fam.auc_family.dropna()]
    persona_vals = [{"label": str(r.disease), "value": round(float(r.rank_enrichment), 2),
                     "current": bool(r.is_current)}
                    for r in personas.itertuples() if r.rank_enrichment == r.rank_enrichment]

    return {
        "eligibility": {
            "total": tot_elig, "eligible": n_elig, "excluded": tot_elig - n_elig,
            "pct_excluded": round(100.0 * (tot_elig - n_elig) / max(tot_elig, 1), 1),
            # The gate is a pipeline constant, not a served value.
            "gate": "module_size >= 20",
        },
        # Route row counts: the three ways a pair is admitted to the pool. Read
        # from the dwpc datasets' metrics rather than recomputed -- they are
        # 3.4M/5.4M rows and counting them per request would be absurd.
        "routes": [
            {"label": "GGD · gene-gene", "count": 3380853},
            {"label": "GPGD · via pathway", "count": 5373706},
            {"label": "GCD · via drug", "count": 42227},
        ],
        "glossary": [{"feature": f, "kind": k, "what": w} for f, k, w in GLOSSARY],
        "family_auc_values": [round(v, 4) for v in fam_vals],
        "personas": sorted(persona_vals, key=lambda r: -r["value"]),
        "drivers_kind": {str(r.feature): KIND.get(str(r.feature), "topology") for r in drv.itertuples()},
        "union_rows": 6754128,
        "pos_rate": 1.89,
        "n_families": len(fam_vals),
        "splits": splits,
        "leakage": leakage,
        "n_features": int(len(drivers)),
        "drivers": [{"label": str(r.feature), "count": int(r.count)} for r in drv.itertuples()],
        "n_diseases": len(vals),
        # Macro, never pooled. Pooled reads 0.8932 and overstates by ~7 points
        # because it lets large diseases carry small ones.
        "macro_auc": round(macro, 4),
        "median_auc": round(sorted(vals)[len(vals) // 2], 4) if vals else None,
        "below_chance": int(sum(1 for v in vals if v < 0.5)),
        "histogram": _hist(vals, 0.0, 1.0, 20),
        # Raw per-disease values for the beeswarm: the distribution IS the point
        # of that card, so it cannot be served pre-binned.
        "auc_values": [round(v, 4) for v in vals],
        "hub_bias": [{
            "quintile": int(r_.quintile),
            "median_degree": float(r_.median_degree),
            "mean_proba": round(float(r_.mean_proba), 4),
            "pct_predicted_positive": round(float(r_.pct_predicted_positive), 1),
            "n_genes": int(r_.n_genes),
        } for r_ in hub.sort_values("quintile").itertuples()],
        "rho_degree_proba": round(float(hub.rho_degree_proba.iloc[0]), 4),
        "threshold": float(hub.threshold.iloc[0]),
        "orthogonality": {
            "n": n,
            "pearson_r": round(r, 4),
            "r2": round(r * r, 4),
            "points": [{"assoc": round(a, 4), "drug": round(b, 4)} for a, b in zip(x, y)],
            "drug_macro_auc": round(sum(y) / n, 4) if n else None,
        },
    }
