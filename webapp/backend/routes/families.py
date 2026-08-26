"""Act 3 — the therapeutic area.

  GET /api/families         families, largest first
  GET /api/families/{id}    one family: every term in it, with its uncertainty

Most R&D groups own one therapeutic area, so a single cherry-picked disease
proves nothing. This act shows the same model against EVERY term in a family.

Two things it must convey, both of which are in the data rather than the copy:
  - per-term AUC carries a confidence interval, because a term with 8 known
    targets and one with 600 do not deserve the same visual weight;
  - `auc_trustworthy` marks the terms too thin to score at all.
"""

from __future__ import annotations

import functools
from typing import Any

from fastapi import APIRouter, HTTPException

from ..dss_client import get_dataiku

router = APIRouter(prefix="/api/families")

PANEL = "family_panel"
OVERLAP = "pairwise_overlap"
NODES = "graph_nodes"


@functools.lru_cache(maxsize=1)
def _names() -> dict[int, str]:
    """disease_index -> readable name. graph_nodes is the only place they live."""
    df = get_dataiku().Dataset(NODES).get_dataframe(
        columns=["node_index", "node_name", "node_type"])
    df = df[df.node_type == "disease"]
    return {int(r.node_index): str(r.node_name) for r in df.itertuples()}


@functools.lru_cache(maxsize=1)
def _panel():
    return get_dataiku().Dataset(PANEL).get_dataframe()


@functools.lru_cache(maxsize=1)
def _enrich() -> dict[int, float]:
    """disease_index -> rank enrichment. v3's thin-disease card plots this, not
    the known-target count; the count is only the label."""
    try:
        df = get_dataiku().Dataset("persona_enrichment").get_dataframe(
            columns=["disease_index", "rank_enrichment"])
        return {int(r.disease_index): float(r.rank_enrichment)
                for r in df.itertuples() if r.rank_enrichment == r.rank_enrichment}
    except Exception:
        return {}


@functools.lru_cache(maxsize=1)
def _overlap():
    try:
        return get_dataiku().Dataset(OVERLAP).get_dataframe()
    except Exception:
        return None


@router.get("")
def families() -> list[dict[str, Any]]:
    """Families with more than one term — a family of one proves nothing here."""
    try:
        p, names = _panel(), _names()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read {PANEL}: {e}")

    out = []
    for fid, g in p.groupby("disease_family_id"):
        if len(g) < 2:
            continue
        out.append({
            "family_id": int(fid),
            # The family takes the name of its largest member, which is the
            # anchor term in practice.
            "family_name": names.get(int(g.sort_values("n_pos", ascending=False)
                                        .disease_index.iloc[0]), f"family {int(fid)}"),
            "n_terms": int(len(g)),
            "macro_auc": round(float(g.auc_disease.mean()), 4),
            "n_trustworthy": int(g.auc_trustworthy.sum()),
        })
    return sorted(out, key=lambda r: (-r["n_terms"], r["family_name"]))


@router.get("/{family_id}")
def family(family_id: int) -> dict[str, Any]:
    """Every term in one family, with its AUC, interval and known-target count."""
    try:
        p, names = _panel(), _names()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read {PANEL}: {e}")

    g = p[p.disease_family_id == family_id]
    if g.empty:
        raise HTTPException(status_code=404, detail=f"No family {family_id}")

    enr = _enrich()
    terms = [{
        "disease_index": int(r.disease_index),
        "enrichment": round(enr[int(r.disease_index)], 2) if int(r.disease_index) in enr else None,
        "disease_name": names.get(int(r.disease_index), str(int(r.disease_index))),
        "auc": round(float(r.auc_disease), 4),
        "lo95": round(float(r.auc_lo95), 4),
        "hi95": round(float(r.auc_hi95), 4),
        # 0 means the interval is too wide to read as a score -- show the term,
        # but never quote its AUC.
        "trustworthy": bool(r.auc_trustworthy),
        "n_pos": int(r.n_pos),
        # Depth in the disease ontology, so the term list can be drawn as the
        # hierarchy it actually is rather than a flat list.
        "hop_depth": int(r.hop_depth) if r.hop_depth == r.hop_depth else 0,
    } for r in g.sort_values("n_pos", ascending=False).itertuples()]

    # Subtype overlap among this family's terms, where it was computed.
    idx = {t["disease_index"] for t in terms}
    pairs: list[dict[str, Any]] = []
    ov = _overlap()
    if ov is not None:
        m = ov[ov.disease_index.isin(idx) & ov.disease_b.isin(idx)]
        pairs = [{
            "a": names.get(int(r.disease_index), str(int(r.disease_index))),
            "b": names.get(int(r.disease_b), str(int(r.disease_b))),
            "shared": int(r["count"]),
        } for _, r in m.iterrows()]

    # The common programme: genes appearing in the top 50 of EVERY term, versus
    # those specific to one. v3 fills this card with `geneGrid`.
    genes: dict[str, int] = {}
    try:
        top = get_dataiku().Dataset("top50_membership").get_dataframe(
            columns=["gene_index", "disease_index"])
        top = top[top.disease_index.isin(idx)]
        gname = {int(r.node_index): str(r.node_name)
                 for r in get_dataiku().Dataset("graph_nodes").get_dataframe(
                     columns=["node_index", "node_name", "node_type"]).itertuples()
                 if r.node_type == "gene/protein"}
        for r in top.itertuples():
            n = gname.get(int(r.gene_index))
            if n:
                genes[n] = genes.get(n, 0) + 1
    except Exception:
        genes = {}
    n_terms_with_top = len({int(i) for i in idx})
    gene_grid = [{"name": n, "group": ("common" if c >= max(2, n_terms_with_top)
                                       else "shared" if c > 1 else "specific")}
                 for n, c in sorted(genes.items(), key=lambda kv: (-kv[1], kv[0]))]

    return {
        "gene_grid": gene_grid,
        "family_id": family_id,
        "n_terms": len(terms),
        "macro_auc": round(float(g.auc_disease.mean()), 4),
        "terms": terms,
        "overlap": sorted(pairs, key=lambda r: -r["shared"]),
    }
