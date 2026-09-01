"""Resolve demo-panel identity by NAME, never by node index.

Lives in the DSS project library at `python/demo_identity.py`. It is a sibling of
`python/target_prioritizer/`, which the webapp deploy owns -- `deploy.sh` only ever
writes under `python/$LIB_NS/`, so it will not touch this file.

WHY THIS EXISTS. Four recipes pinned disease **node indices** as literals:

    A3_FAMILIES = {49721: "breast", 44244: "uterine", 36637: "stomach"}
    UMBRELLA    = [47415, 46673, 48546]
    P           = [47654, 37143, 47537, 47469, 47604, 52236]
    WATCH       = {37143: "obesity disorder", ...}

`node_index` is assigned when the graph is built. A rebuild renumbers it. Nothing in
DSS notices: the recipe keeps running and silently selects whichever disease now holds
that slot, so the panel would quietly become a different panel. Names are stable across
a rebuild in a way indices are not, so names are the key and the index is derived.

THE ASSERTION IS THE POINT. `name_to_index` refuses to return a partial answer: a name
that resolves to zero nodes, or to more than one, raises. That converts a graph renumber
or an ontology relabel from a silent mis-selection into a failed build.

Verified 2026-09-01 against the live graph: all 22 names used by these recipes resolve,
and each is unique among the 27,153 `disease` nodes -- so the reverse lookup is
well-defined today. The assertion exists for the day it stops being.
"""

from __future__ import annotations

import json

import dataiku

NODES = "graph_nodes"


def variables() -> dict:
    """Project variables, with JSON-string values parsed.

    DSS returns an object-valued variable as a dict, but a variable that was set as a
    JSON *string* comes back as a string. Accept both rather than assume one.
    """
    raw = dataiku.get_custom_variables()
    out = {}
    for key, value in raw.items():
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                pass
        out[key] = value
    return out


def panel() -> dict:
    """The `demo_panel` variable."""
    v = variables().get("demo_panel")
    if not isinstance(v, dict):
        raise ValueError(
            "project variable `demo_panel` is missing or not an object. Set it with "
            "`dku project set-variables` before running this recipe."
        )
    return v


#: Threshold variables are FLAT scalars, not one nested object, because a DSS visual
#: formula cannot read into a nested variable. Verified 2026-09-01 on
#: `compute_validation_auc_ci`: both `variables["thresholds"].trust_n_pos` and
#: `variables["thresholds"]["trust_n_pos"]` evaluate to nothing -- the lint passes, the
#: build succeeds, and every row silently comes out false. Flat keys are the only form
#: both Python and visual recipes can read, so they are the single definition.
THRESHOLD_KEYS = ("trust_n_pos", "panel_n_pos", "near_dup", "module_size_gate", "ks", "topn")


def thresholds() -> dict:
    """The flat threshold variables, gathered into a dict for convenience."""
    v = variables()
    missing = [k for k in THRESHOLD_KEYS if k not in v]
    if missing:
        raise ValueError(
            f"threshold project variables missing: {missing}. Set them with "
            "`dku project set-variables`; do not fall back to a literal."
        )
    return {k: v[k] for k in THRESHOLD_KEYS}


def name_to_index(names, node_type: str = "disease") -> dict:
    """{node_name: node_index} for `names`, or raise.

    Raises when a name is absent or ambiguous. Never returns a partial map -- a caller
    that got one would build a panel with a silently missing term.
    """
    wanted = list(dict.fromkeys(names))
    nodes = dataiku.Dataset(NODES).get_dataframe(
        columns=["node_index", "node_name", "node_type"])
    pool = nodes[nodes.node_type == node_type]
    hits = pool[pool.node_name.isin(wanted)]

    counts = hits.groupby("node_name").size()
    missing = [n for n in wanted if n not in counts.index]
    ambiguous = sorted(counts[counts > 1].index)
    if missing or ambiguous:
        raise ValueError(
            f"cannot resolve {node_type} names against {NODES}. "
            f"missing={missing} ambiguous={ambiguous}. "
            "The graph or the `demo_panel` variable changed; fix one of them rather "
            "than falling back to hardcoded indices."
        )
    return {str(r.node_name): int(r.node_index) for r in hits.itertuples()}


def index_to_name(mapping: dict) -> dict:
    """Invert a {name: index} map."""
    return {v: k for k, v in mapping.items()}
