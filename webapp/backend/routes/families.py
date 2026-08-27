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

    # One pass over dashboard_candidates gives everything acts 3 needs about
    # membership: the top-50 list per term (all and novel-only), the pairwise
    # overlap for both modes, and the gene x term RANK matrix the grid encodes.
    TOP = 50
    tops: dict[int, list[tuple[str, int]]] = {}
    tops_novel: dict[int, list[tuple[str, int]]] = {}
    try:
        cols = ["disease_index", "gene_name", "rank_in_disease", "is_target"]
        cand = get_dataiku().Dataset("dashboard_candidates").get_dataframe(columns=cols)
        cand = cand[cand.disease_index.isin(idx)]
        # NB: do not name this `g` -- the outer `g` is the family_panel slice the
        # return still needs, and shadowing it here cost a 500 on every family.
        for di, cg in cand.groupby("disease_index"):
            cg = cg.sort_values("rank_in_disease")
            tops[int(di)] = [(str(r.gene_name), int(r.rank_in_disease))
                             for r in cg.head(TOP).itertuples()]
            cgn = cg[cg.is_target == 0].head(TOP)
            tops_novel[int(di)] = [(str(r.gene_name), int(r.rank_in_disease))
                                   for r in cgn.itertuples()]
    except Exception:
        tops, tops_novel = {}, {}

    def _pairs(src: dict[int, list[tuple[str, int]]]) -> list[dict[str, Any]]:
        out = []
        ids = [i for i in _with_data if i in src and src[i]]
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                ia, ib = ids[a], ids[b]
                shared = len({n for n, _ in src[ia]} & {n for n, _ in src[ib]})
                out.append({"a": names.get(ia, str(ia)), "b": names.get(ib, str(ib)),
                            "shared": shared})
        return out

    # Gene x term rank matrix. Dot size/opacity encodes rank, so the rank has to
    # travel per cell -- membership alone is not enough.
    # Ordered by hop depth, like the term table -- not by dict insertion.
    _depth = {int(t["disease_index"]): (t["hop_depth"], -t["n_pos"]) for t in terms}
    _with_data = sorted((i for i in idx if i in tops and tops[i]),
                        key=lambda i: _depth.get(i, (99, 0)))
    cols_order = [names.get(i, str(i)) for i in _with_data]
    rank_of: dict[str, dict[str, int]] = {}
    for i in idx:
        for n, rk in tops.get(i, []):
            rank_of.setdefault(n, {})[names.get(i, str(i))] = rk
    gene_grid = [{"name": n, "ranks": r, "n_terms": len(r)}
                 for n, r in sorted(rank_of.items(), key=lambda kv: (-len(kv[1]), kv[0]))]

    return {
        "gene_grid": gene_grid,
        "grid_columns": cols_order,
        # Only the 13 personas carry ranked candidates, so a family's remaining
        # terms cannot appear in the matrix. Say how many, rather than showing a
        # silent subset.
        "coverage": {"with_data": len(_with_data), "total": len(terms)},
        "overlap_all": _pairs(tops),
        "overlap_novel": _pairs(tops_novel),
        "family_id": family_id,
        "n_terms": len(terms),
        "macro_auc": round(float(g.auc_disease.mean()), 4),
        "terms": terms,
        "overlap": sorted(pairs, key=lambda r: -r["shared"]),
    }
