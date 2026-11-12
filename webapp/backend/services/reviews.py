"""Recorded reviews of a candidate (webapp revision W4, decisions D2 and D3).

One JSON file per review in the managed folder `shortlist_reviews` (zone S1), at
`{YYYY-MM}/{UTC timestamp}_{id}.json`, holding one JSON object on one line so the "files in folder"
dataset `shortlist_reviews_log` reads every review as a row. Reviews are append-only: a newer review
of the same pair supersedes the older one on screen, and both files stay.

WHY A REVIEW STORES NAMES, NOT ONLY INDEXES (D3). `gene_index` / `disease_index` are graph node
indexes, and a graph rebuild renumbers them (R5 renumbered 76,786 nodes). A review keyed on them would
silently attach to another gene after the next rebuild, as the evidence cache once did. So each review
stores the graph symbol, HGNC symbol and id, and the disease name beside the indexes, and is matched
back to today's list by graph symbol and disease name. The indexes are kept as a record of what they
were when the review was written.

The reviewer is the DSS login of the browser that sent the request, resolved by DSS from the
request's headers. Inside DSS a review whose login cannot be resolved is refused rather than
recorded anonymously. In local development there is no DSS browser session, so the reviewer is the
owner of the API key, marked as such.
"""

from __future__ import annotations

import datetime as dt
import json
import threading
import time
import uuid
from typing import Any

from .. import config
from ..dss_client import get_dataiku, get_project
from . import dataset_cache

FOLDER = "shortlist_reviews"
VERDICTS = {"advance": "Advance", "more_evidence": "Needs more evidence", "reject": "Reject"}
MAX_COMMENT = 4000
CHAMPION = {"name": "m7-f14-cal", "saved_model": "W8VhjZOZ"}

_folder_id: str | None = None
_cache: dict[str, Any] = {"at": 0.0, "reviews": None}
_cache_lock = threading.Lock()
CACHE_S = 60  # picks up files written elsewhere (another backend, a DSS user) within a minute


def _folder():
    global _folder_id
    p = get_project()
    if _folder_id is None:
        hit = [f["id"] for f in p.list_managed_folders() if f.get("name") == FOLDER]
        if not hit:
            raise RuntimeError(f"managed folder {FOLDER} not found in {config.PROJECT_KEY or 'this project'}")
        _folder_id = hit[0]
    return p.get_managed_folder(_folder_id)


def reviewer(headers: dict[str, str]) -> str:
    """The DSS login behind the request."""
    if config.DSS_MODE:
        auth = get_dataiku().api_client().get_auth_info_from_browser_headers(headers)
        login = auth.get("authIdentifier")
        if not login:
            raise PermissionError("DSS could not identify the reviewer from this browser session")
        return str(login)
    from ..dss_client import _local_client
    return f"{_local_client().get_auth_info().get('authIdentifier', 'unknown')} (local dev)"


def _pair(disease: int, gene: int) -> dict[str, Any]:
    """What the list says about the pair today: names, rank and score."""
    df = dataset_cache.frame(config.SHORTLIST, ["disease_index", "disease_name", "gene_index", "gene_name",
                                                "rank_in_disease", "score"])
    row = df[(df.disease_index == disease) & (df.gene_index == gene)].head(1)
    if row.empty:
        raise LookupError(f"gene_index {gene} is not in disease {disease}'s list")
    r = row.iloc[0]
    ids = dataset_cache.frame("candidate_identity", ["node_index", "hgnc_id", "symbol"])
    hit = ids[ids.node_index == gene].head(1)
    ident = {} if hit.empty else {k: (None if v is None or v != v or v == "" else v)
                                  for k, v in hit.iloc[0].to_dict().items()}
    return {"disease_index": disease, "disease_name": str(r.disease_name),
            "gene_index": gene, "graph_symbol": str(r.gene_name),
            "hgnc_symbol": ident.get("symbol"), "hgnc_id": ident.get("hgnc_id"),
            "rank": int(r.rank_in_disease), "score": float(r.score)}


def record(disease: int, gene: int, verdict: str, comment: str, headers: dict[str, str]) -> dict[str, Any]:
    """Write one review and return it. Returns only after the file is written."""
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {', '.join(VERDICTS)}")
    comment = (comment or "").strip()
    if not comment:
        raise ValueError("a comment is required: a verdict without a reason hands nothing off")
    if len(comment) > MAX_COMMENT:
        raise ValueError(f"the comment is longer than {MAX_COMMENT} characters")
    from ..routes.calibration import _champion  # the live saved-model version, cached there
    now = dt.datetime.now(dt.timezone.utc)
    review = {
        "review_id": uuid.uuid4().hex[:12],
        "reviewed_at": now.isoformat(timespec="seconds"),
        "reviewer": reviewer(headers),
        "verdict": verdict,
        "comment": comment,
        **_pair(disease, gene),
        "model_name": CHAMPION["name"], "saved_model": CHAMPION["saved_model"],
        "model_version": _champion().get("version"),
    }
    path = f"{now:%Y-%m}/{now:%Y%m%dT%H%M%SZ}_{review['review_id']}.json"
    _folder().put_file(path, (json.dumps(review) + "\n").encode("utf-8"))
    with _cache_lock:
        if _cache["reviews"] is not None:
            _cache["reviews"].append(review)
    return review


def _all() -> list[dict[str, Any]]:
    with _cache_lock:
        if _cache["reviews"] is not None and time.time() - _cache["at"] < CACHE_S:
            return list(_cache["reviews"])
    f = _folder()
    out = []
    for item in f.list_contents().get("items", []):
        path = item.get("path", "")
        if not path.endswith(".json"):
            continue
        try:
            with f.get_file(path) as r:
                out.append(json.loads(r.content))
        except Exception:  # noqa: BLE001 -- one unreadable file must not hide the others
            continue
    with _cache_lock:
        _cache.update(at=time.time(), reviews=out)
    return list(out)


def for_disease(disease: int) -> dict[str, Any]:
    """The disease's reviews, newest first, each matched to TODAY's gene by graph symbol.

    `gene_index_now` is null when the reviewed symbol is no longer in this disease's list.
    """
    df = dataset_cache.frame(config.SHORTLIST, ["disease_index", "disease_name", "gene_index", "gene_name"])
    pool = df[df.disease_index == disease]
    if pool.empty:
        raise LookupError(f"No candidates for disease_index {disease}")
    name = str(pool.disease_name.iloc[0])
    by_symbol = dict(zip(pool.gene_name.astype(str), pool.gene_index.astype(int)))
    revs = [dict(r, gene_index_now=by_symbol.get(r.get("graph_symbol")), verdict_label=VERDICTS.get(r.get("verdict")))
            for r in _all() if r.get("disease_name") == name]
    revs.sort(key=lambda r: r.get("reviewed_at", ""), reverse=True)
    return {"disease_index": disease, "disease_name": name, "reviews": revs}
