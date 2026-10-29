"""Act 4 — the trials and papers for the selected pair (redesign D3-D6).

  GET /api/candidates/sources            the pair's retrieved records (no LLM), cached
  GET /api/candidates/sources/selection  one LLM selection pass over them, cached

Both take `disease`, `gene` and `refresh` (re-run and overwrite the cached file). The work and the
cache are in services/pair_sources.py; this module only maps failures to status codes, so a tool
or LLM failure reaches the Trials and Literature tabs and nothing else.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..services import pair_sources

router = APIRouter(prefix="/api/candidates/sources")


@router.get("")
def sources(disease: int = Query(..., description="disease_index"),
            gene: int = Query(..., description="gene_index"),
            refresh: bool = Query(False)) -> dict[str, Any]:
    try:
        doc = pair_sources.search(disease, gene, refresh=refresh)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search failed: {e}")
    return doc


@router.get("/selection")
def selection(disease: int = Query(..., description="disease_index"),
              gene: int = Query(..., description="gene_index"),
              refresh: bool = Query(False)) -> dict[str, Any]:
    try:
        return pair_sources.select(disease, gene, refresh=refresh)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Selection failed: {e}")
