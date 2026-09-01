"""Dataset frames cached per BUILD, not per process.

WHY THIS EXISTS. The act routes each held their own `@lru_cache` keyed on nothing,
so a frame loaded at webapp start was served until the backend restarted. After a
flow rebuild the app kept serving the previous generation -- the worst kind of
stale in front of an audience, because the numbers look fine and are simply out of
date. `DEPLOYMENT.md` recorded the symptom and a proposed fix.

THE PROPOSED FIX DID NOT WORK, and the correction is the point of this module.
It suggested keying on `reporting:BUILD_END` via `get_metric_by_id(...).get_value()`.
Neither half exists on this DSS: the metric list is

    reporting:BUILD_START_DATE  reporting:BUILD_DURATION  reporting:BUILD_SUCCESS
    reporting:WARNING_COUNT     reporting:METRICS_COMPUTATION_DURATION
    basic:COUNT_COLUMNS  basic:COUNT_FILES  basic:SIZE  records:COUNT_RECORDS

there is no BUILD_END, and `get_metric_by_id(...).get_value()` raises. The working
accessor is `get_last_metric_values().get_global_value("reporting:BUILD_START_DATE")`,
which returns an ISO timestamp that changes on every build. That is the cache key.

DO NOT key on `records:COUNT_RECORDS`. Record counts are written by a metrics pass
rather than by the build, so they lag: `dku dataset info` reported 129,253 rows for
`dashboard_candidates` while the live count was 105,702. A rebuild that leaves the
row count unchanged -- a relabelling, a column edit -- would also not move the key,
so the cache would never invalidate. BUILD_START_DATE moves on every build.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Iterable

from ..dss_client import get_dataiku

# Enough to hold every dataset the acts read (about a dozen) plus a generation of
# churn while a rebuild lands. Old generations fall out by LRU on their own.
_MAXSIZE = 32

# When the build stamp cannot be read, fall back to a coarse time bucket so the
# cache still self-heals within a few minutes instead of never. A fixed constant
# here would silently reinstate the exact bug this module exists to remove.
_FALLBACK_BUCKET_SECONDS = 300

_STAMP = "reporting:BUILD_START_DATE"


def build_stamp(name: str) -> str:
    """Identity of the dataset's current build.

    A metadata call, not a data read, so the per-request cost stays negligible.
    """
    try:
        values = get_dataiku().Dataset(name).get_last_metric_values()
        stamp = values.get_global_value(_STAMP)
        if stamp:
            return str(stamp)
    except Exception:
        pass
    return f"nostamp:{int(time.time() // _FALLBACK_BUCKET_SECONDS)}"


@functools.lru_cache(maxsize=_MAXSIZE)
def _frame_at(name: str, stamp: str, columns: tuple[str, ...] | None) -> Any:
    """`stamp` is unused inside -- it exists purely as part of the cache key."""
    ds = get_dataiku().Dataset(name)
    return ds.get_dataframe(columns=list(columns)) if columns else ds.get_dataframe()


def frame(name: str, columns: Iterable[str] | None = None) -> Any:
    """The dataset as a DataFrame, reloaded automatically after a rebuild.

    The returned object is SHARED between callers. Treat it as read-only: filter
    and copy, never mutate in place, or one route's edit becomes another's bug.
    """
    return _frame_at(name, build_stamp(name), tuple(columns) if columns else None)


def invalidate() -> None:
    """Drop every cached frame. For tests and for a manual refresh endpoint."""
    _frame_at.cache_clear()


def cache_info() -> dict[str, int]:
    info = _frame_at.cache_info()
    return {"hits": info.hits, "misses": info.misses,
            "size": info.currsize, "maxsize": info.maxsize or 0}
