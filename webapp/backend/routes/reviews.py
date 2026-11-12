"""Recorded reviews (webapp revision W4).

  POST /api/reviews              record one review of a pair: verdict and a required comment
  GET  /api/reviews?disease=     the disease's reviews, newest first, matched to today's genes

The storage, the reviewer and why reviews are matched by name are in services/reviews.py. This module
maps failures to status codes, so a missing folder or an unidentified reviewer reaches the dialog.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..services import reviews

router = APIRouter(prefix="/api/reviews")


class ReviewIn(BaseModel):
    disease: int
    gene: int
    verdict: str
    comment: str


@router.post("")
def record(body: ReviewIn, request: Request) -> dict[str, Any]:
    try:
        return reviews.record(body.disease, body.gene, body.verdict, body.comment, dict(request.headers))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"The review was not recorded: {e}")


@router.get("")
def for_disease(disease: int = Query(..., description="disease_index")) -> dict[str, Any]:
    try:
        return reviews.for_disease(disease)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read the reviews: {e}")
