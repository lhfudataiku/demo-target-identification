"""Act 1 — the evidence base.

  GET /api/evidence   the graph's composition and provenance, in one payload

Five small A1 datasets (8 / 18 / 7 / 7 / 3 rows). They are tiny and always
fetched together, so one endpoint rather than five round trips.

This act is about WHAT WENT IN and where it came from. It deliberately makes no
quality claim -- faithful assembly is a lineage property, not an accuracy one.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..dss_client import get_dataiku

router = APIRouter(prefix="/api/evidence")

# dataset -> (label column, count column)
SOURCES = {
    "node_types": ("graph_node_type_counts", "node_type"),
    "relations": ("graph_relation_counts", "relation"),
    "node_sources": ("graph_node_source_counts", "node_source"),
    "ppi_provenance": ("graph_ppi_provenance", "ppi_sources"),
    "label_evidence": ("graph_label_evidence", "datatypes"),
}


def _rows(dataset: str, label_col: str) -> list[dict[str, Any]]:
    df = get_dataiku().Dataset(dataset).get_dataframe()
    df = df.sort_values("count", ascending=False)
    return [{"label": str(r[label_col]), "count": int(r["count"])} for _, r in df.iterrows()]


@router.get("")
def evidence() -> dict[str, Any]:
    """Graph composition and provenance for act 1."""
    out: dict[str, Any] = {}
    try:
        for key, (dataset, label_col) in SOURCES.items():
            out[key] = _rows(dataset, label_col)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read {dataset}: {e}")

    out["totals"] = {
        "nodes": sum(r["count"] for r in out["node_types"]),
        "edges": sum(r["count"] for r in out["relations"]),
        "relations": len(out["relations"]),
        "node_types": len(out["node_types"]),
        "sources": len(out["node_sources"]),
        # Edges carrying an explicit source, as opposed to inherited provenance.
        "edges_with_provenance": sum(r["count"] for r in out["ppi_provenance"]),
    }
    return out
