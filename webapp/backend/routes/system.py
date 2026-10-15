"""System endpoints: health check."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/system")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
