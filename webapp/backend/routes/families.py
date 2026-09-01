"""Act 3 — does it hold across a therapeutic area?

Governed claim consumed: TI-VAL-009. Thin-disease AUC and subtype-overlap interpretation remain
governed even though this route reads the current panel datasets live.

  GET /api/families              the families the demo carries
  GET /api/families/{family_id}  one family: per-subtype scores, overlap, programme

READS, DOES NOT COMPUTE. Every figure here comes from a dataset the flow built:

  demo_panel_config       which terms belong to which family, and their role
  family_panel_metrics    per-subtype AUC, interval, known-target count
  family_panel_overlap    pairwise top-50 overlap, with the ontology gap
  family_panel_programme  common vs subtype-specific, over the leaves
  family_panel_top50      the gene x term rank matrix

An earlier version derived overlap and the gene grid here, from
`dashboard_candidates`. That only ever held the persona diseases, so a family's
remaining terms could not appear at all -- the `coverage` field existed to admit
that the matrix was a subset. `family_panel_top50` covers every term in the config,
so the subset caveat is gone and the same numbers now appear in the app, in the
notebook assertions, and in docs/demo/panel_selection/built/.

THREE THINGS THE CARDS DEPEND ON, in the data rather than in this file:

  * NON-LEAF terms stay in the score and overlap cards. An umbrella term is largely
    a blend of the terms beneath it -- `gastric adenocarcinoma` shares 0.961 of its
    top 50 with `gastric carcinoma` one level up -- and showing that is the point.
  * They are excluded from the programme card only, where a superset's "specific"
    genes would be an artefact of aggregation.
  * `act3_role` is `leaf` / `not_leaf` and records only membership of the curated
    leaf set. It is NOT an ontology claim: `metaplastic breast carcinoma` (depth 3)
    is `not_leaf` yet is nobody's ancestor. Likewise `pair_kind` is
    `same_depth` / `different_depth`, not sibling/ancestor -- two terms at different
    depths may sit on different branches.
  * Order by `hop_depth`, never by AUC or name. The parent->child AUC gradient
    (breast 0.707 -> 0.861 -> 0.936 -> 0.951) is only legible in ontology order.
"""

from __future__ import annotations

import functools
from typing import Any

from fastapi import APIRouter, HTTPException

from ..dss_client import get_dataiku
from ..services import dataset_cache

router = APIRouter(prefix="/api/families")

CONFIG = "demo_panel_config"
METRICS = "family_panel_metrics"
OVERLAP = "family_panel_overlap"
PROGRAMME = "family_panel_programme"
TOP50 = "family_panel_top50"
ENRICH = "persona_enrichment"

# The near-duplicate threshold is NOT duplicated here. `compute_family_panel_overlap`
# applies it (Jaccard > 0.6 on the top 50) and writes `near_duplicate` per pair; this
# route passes that flag through. A constant here would be a second definition that
# nothing enforces -- the previous one claimed to "match the flow's own threshold" and
# was never read.


def _ds(name: str):
    # Keyed on the dataset's build stamp, so an A3 rebuild lands without a restart.
    return dataset_cache.frame(name)


@functools.lru_cache(maxsize=4)
def _enrich_at(stamp: str) -> dict[int, float]:
    """disease_index -> rank enrichment. The thin-disease card plots this rather
    than the known-target count, because a count is the label and not a score.

    `stamp` is unused inside -- it is the build key, so a persona_enrichment
    rebuild refreshes this map without a backend restart.
    """
    try:
        df = dataset_cache.frame(ENRICH, ["disease_index", "rank_enrichment"])
        return {int(r.disease_index): float(r.rank_enrichment)
                for r in df.itertuples() if r.rank_enrichment == r.rank_enrichment}
    except Exception:
        return {}


def _enrich() -> dict[int, float]:
    return _enrich_at(dataset_cache.build_stamp(ENRICH))


def _in_a3(df):
    """Rows that belong to an Act 3 family.

    Tests for an empty string as well as null: an Act 4-only disease (lung
    adenocarcinoma, rheumatoid arthritis, ...) has no act3_family, and a null
    survives the parquet round-trip as "" rather than NaN -- so `.notna()` alone
    let a phantom family through with an empty name.
    """
    col = df.act3_family
    return df[col.notna() & (col.astype(str).str.strip() != "")]


@router.get("")
def families() -> list[dict[str, Any]]:
    """The families Act 3 carries — three, not all 505 in the validation set."""
    try:
        cfg = _ds(CONFIG)
        met = _ds(METRICS)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read the panel config: {e}")

    out = []
    for fam, g in _in_a3(cfg).groupby("act3_family"):
        scored = met[met.act3_family == fam]
        scored = scored[scored.in_act3.astype(bool)]
        out.append({
            "family": str(fam),
            "family_id": int(g.disease_family_id.dropna().iloc[0]),
            "family_name": str(fam),
            "n_terms": int(len(g)),
            "n_scored": int(len(scored)),
            # Macro over the terms with a trustworthy interval. A term below the
            # 50-positive floor carries a list, never a quotable AUC.
            "macro_auc": (round(float(scored[scored.auc_trustworthy.astype(bool)]
                                      .auc_disease.mean()), 4)
                          if len(scored) else None),
            "n_leaves": int((g.act3_role == "leaf").sum()),
            # kept under its old name too -- the frontend reads n_trustworthy
            "n_trustworthy": int(scored[scored.auc_trustworthy.astype(bool)].shape[0]),
        })
    return sorted(out, key=lambda r: -(r["n_terms"]))


@router.get("/{family_id}")
def family(family_id: int) -> dict[str, Any]:
    try:
        cfg = _ds(CONFIG)
        met = _ds(METRICS)
        ov = _ds(OVERLAP)
        pg = _ds(PROGRAMME)
        top = _ds(TOP50)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not read a panel dataset: {e}")

    fam_rows = cfg[cfg.disease_family_id == family_id]
    if fam_rows.empty:
        raise HTTPException(status_code=404, detail=f"No family {family_id}")
    fam = str(fam_rows.act3_family.dropna().iloc[0])

    m = met[met.act3_family == fam].copy()
    m = m.sort_values(["hop_depth", "n_pos"], ascending=[True, False])
    enr = _enrich()
    terms = [{
        "disease_index": int(r.disease_index),
        "enrichment": (round(enr[int(r.disease_index)], 2)
                       if int(r.disease_index) in enr else None),
        "disease_name": str(r.disease),
        "auc": round(float(r.auc_disease), 4),
        "lo95": round(float(r.auc_lo95), 4) if r.auc_lo95 == r.auc_lo95 else None,
        "hi95": round(float(r.auc_hi95), 4) if r.auc_hi95 == r.auc_hi95 else None,
        # False means the interval is too wide to read as a score. Show the term,
        # never quote its AUC -- triple-negative breast is 0.895 on 8 positives,
        # interval 0.749-1.041.
        "trustworthy": bool(r.auc_trustworthy),
        "n_pos": int(r.n_pos),
        "hop_depth": int(r.hop_depth) if r.hop_depth == r.hop_depth else 0,
        "role": str(r.act3_role) if r.act3_role == r.act3_role else None,
        "scored": bool(r.in_act3),
        "in_shortlist": bool(r.in_act4),
    } for r in m.itertuples()]

    # ── the overlap card ────────────────────────────────────────────────────
    fo = ov[ov.act3_family == fam].sort_values("jaccard_top50", ascending=False)
    overlap = [{
        "a": str(r.disease_a), "b": str(r.disease_b),
        "shared": int(r.all_overlap),
        "shared_novel": int(r.novel_overlap),
        "jaccard": round(float(r.jaccard_top50), 4),
        "depth_gap": int(r.depth_gap),
        "kind": str(r.pair_kind),
        "near_duplicate": bool(r.near_duplicate),
    } for r in fo.itertuples()]

    # Overlap tracks ontology distance; the card says so rather than leaving the
    # reader to infer it from a matrix.
    by_gap: dict[int, list[float]] = {}
    for r in fo.itertuples():
        by_gap.setdefault(int(r.depth_gap), []).append(float(r.jaccard_top50))
    gap_profile = [{"depth_gap": k, "pairs": len(v), "mean": round(sum(v) / len(v), 4)}
                   for k, v in sorted(by_gap.items())]

    # ── the common-vs-specific card ────────────────────────────────────────
    fp = pg[pg.act3_family == fam]
    leaves = sorted(fp.subtype.unique())
    common = sorted(fp[fp.scope == "common"].gene.unique())
    specific = {
        str(sub): [str(x.gene) for x in
                   sg[sg.scope == "specific"].sort_values("rank_in_subtype").itertuples()]
        for sub, sg in fp.groupby("subtype")
    }
    programme = {
        "leaves": leaves,
        "common": common,
        "n_common": len(common),
        "specific": specific,
        # The non-leaf terms are deliberately absent here. Stated so the omission
        # reads as a decision rather than missing data.
        "excludes_non_leaves": True,
    }

    # ── the gene x term rank matrix ────────────────────────────────────────
    fam_terms = [t["disease_name"] for t in terms]
    ft = top[top.disease.isin(fam_terms) & (top.rank_in_disease <= 50)]
    cols_order = [t["disease_name"] for t in terms
                  if t["disease_name"] in set(ft.disease)]
    rank_of: dict[str, dict[str, int]] = {}
    for r in ft.itertuples():
        rank_of.setdefault(str(r.gene), {})[str(r.disease)] = int(r.rank_in_disease)
    gene_grid = [{"name": n, "ranks": rk, "n_terms": len(rk)}
                 for n, rk in sorted(rank_of.items(), key=lambda kv: (-len(kv[1]), kv[0]))]

    scored_terms = [t for t in terms if t["trustworthy"]]
    # The overlap tab switches between all-gene and novel-only. Both come from the
    # one table now, rather than two derivations that could disagree.
    overlap_all = [{"a": o["a"], "b": o["b"], "shared": o["shared"]} for o in overlap]
    overlap_novel = [{"a": o["a"], "b": o["b"], "shared": o["shared_novel"]} for o in overlap]

    return {
        "family": fam,
        "overlap_all": overlap_all,
        "overlap_novel": overlap_novel,
        "family_id": family_id,
        "n_terms": len(terms),
        "macro_auc": (round(sum(t["auc"] for t in scored_terms) / len(scored_terms), 4)
                      if scored_terms else None),
        "terms": terms,
        "overlap": overlap,
        "gap_profile": gap_profile,
        "mean_overlap": round(float(fo.jaccard_top50.mean()), 4) if len(fo) else None,
        "n_near_duplicates": int(fo.near_duplicate.sum()),
        "programme": programme,
        "gene_grid": gene_grid,
        "grid_columns": cols_order,
        "coverage": {"with_data": len(cols_order), "total": len(terms)},
    }
