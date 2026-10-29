"""Pre-fill the trials-and-literature cache before a demo (redesign D6).

Run by the `prefill_evidence_cache` scenario, never by the webapp. The scenario's one Python step
imports this module from the deployed project library, so it runs the same search, selection and
cache code the webapp serves (services/pair_sources.py) and writes the same files.

    run()   HER2+ ranks 1-20 as the shortlist opens (no filter), plus the narrative's two examples

A pair whose file is current is read, not re-run: a second run costs nothing unless a version in
pair_sources.VERSIONS changed. One pair failing does not stop the others; the run raises at the end
if any failed, so the scenario shows red.
"""

from __future__ import annotations

import time
from typing import Any

from . import config
from .services import dataset_cache, pair_sources

# Resolved by name, not node_index: indices renumber on a graph rebuild (DEC-OPS-006).
DISEASE = "HER2 positive breast carcinoma"
TOP = 20
EXTRA = ("ERBB2", "SMARCA2")


def pairs(disease_name: str = DISEASE, top: int = TOP, extra: tuple[str, ...] = EXTRA) -> list[tuple[int, int, str]]:
    d = dataset_cache.frame(config.SHORTLIST, ["disease_index", "disease_name", "gene_index",
                                               "gene_name", "rank_in_disease"])
    pool = d[d.disease_name == disease_name]
    if pool.empty:
        raise LookupError(f"no candidates for {disease_name!r}")
    pool = (pool.assign(rank_in_disease=pool.rank_in_disease.astype(int))
            .sort_values(["rank_in_disease", "gene_name"], kind="stable"))
    chosen = pool[(pool.rank_in_disease <= top) | pool.gene_name.isin(extra)]
    missing = sorted(set(extra) - set(chosen.gene_name))
    if missing:
        raise LookupError(f"not in {disease_name!r}'s pool: {missing}")
    return [(int(r.disease_index), int(r.gene_index), str(r.gene_name)) for r in chosen.itertuples()]


def run(disease_name: str = DISEASE, top: int = TOP, extra: tuple[str, ...] = EXTRA,
        refresh: bool = False) -> dict[str, Any]:
    todo = pairs(disease_name, top, extra)
    t0 = time.monotonic()
    done, failed = [], []
    for disease, gene, name in todo:
        t = time.monotonic()
        try:
            doc = pair_sources.search(disease, gene, refresh=refresh)
            sel = pair_sources.select(disease, gene, refresh=refresh)["selection"]
            done.append(name)
            print(f"{name:<12} {'cached' if doc['cached'] else 'searched'} · "
                  f"{len(doc['search']['trials']['records'])} trials, {len(doc['search']['papers']['records'])} papers"
                  f" · picked {len(sel['trials'])}+{len(sel['papers'])} · {time.monotonic() - t:.1f}s")
        except Exception as e:
            failed.append({"gene": name, "error": str(e)})
            print(f"{name:<12} FAILED: {e}")
    summary = {"disease": disease_name, "pairs": len(todo), "done": len(done), "failed": failed,
               "seconds": round(time.monotonic() - t0, 1)}
    print(summary)
    if failed:
        raise RuntimeError(f"{len(failed)} of {len(todo)} pairs failed: {[f['gene'] for f in failed]}")
    return summary
