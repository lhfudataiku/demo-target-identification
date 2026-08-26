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

    return {
        "n_diseases": len(vals),
        # Macro, never pooled. Pooled reads 0.8932 and overstates by ~7 points
        # because it lets large diseases carry small ones.
        "macro_auc": round(macro, 4),
        "median_auc": round(sorted(vals)[len(vals) // 2], 4) if vals else None,
        "below_chance": int(sum(1 for v in vals if v < 0.5)),
        "histogram": _hist(vals, 0.0, 1.0, 20),
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
