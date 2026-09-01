"""Act 1 — explore the graph.

  GET  /api/graph/defaults   the pinned starter queries
  POST /api/graph/search     ask the graph, return an answer plus what to render
  POST /api/graph/mechanism  every evidence route from one gene to one disease

This module is TRANSPORT, deliberately. The behaviour -- how to write Cypher for
this graph, what to refuse, how to phrase an answer -- lives in the system prompt
of the DSS agent `graph_explorer` (LLM id in GRAPH_AGENT), not here. That is what
makes the agent a first-class, reviewable project object rather than logic buried
in a webapp: it is visible in the flow, versionable, testable with
`dku agent test`, and reusable from Agent Hub.

The agent wraps the visual-graph plugin's Graph Search tool. Two things were
measured before choosing this route:

  * The GRAPH artifact SURVIVES the agent. It arrives at exactly the path a
    direct tool call uses -- artifacts[0].parts[0].customData.graph -- so the
    renderer is unchanged.
  * Literal Cypher passes through the agent UNALTERED. The pinned starter for
    TP53's drugs returns the same 6 nodes / 5 edges either way, so routing
    everything through the agent does not cost reproducibility.

What it does cost: roughly double the latency (2.7s -> 5.5s on a pinned query)
and LLM tokens proportional to the result size, because the tool's output enters
the model's context. The prompt's LIMIT 60 guidance is what keeps that bounded --
before it, one subgraph question cost 97k tokens.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..dss_client import get_project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph")

# The DSS agent, addressed through the LLM Mesh. It owns the prompt; it wraps
# the visual-graph Graph Search tool (b6Rpbve), which in turn reads this
# project's Kuzu folder (ytvuniN8).
GRAPH_AGENT = "agent:SybkzSdu"

# The tool the agent wraps. Addressed directly for the /cypher route, which
# executes literal Cypher with NO LLM in the path -- deterministic, ~2.7s instead
# of ~8s, and zero tokens. The pinned starters and the editable Cypher panel both
# use it; only free-text questions need the agent.
GRAPH_TOOL_ID = "b6Rpbve"

# Above this, vis-network's physics stops being interactive: an unbounded
# `MATCH (p)-[e]-(n)` on a hub protein returns ~1,538 nodes. We never silently
# truncate -- the response says what was dropped.
MAX_NODES = 220

# A tabular answer is a table, not a graph -- cap it so an unbounded aggregation
# cannot flood the card. Reported, never silent.
MAX_TABLE_ROWS = 200

# Every starter query is undirected, ORDER BY'd and LIMITed, and each one is here
# because it shows a layer Act 1 or Act 2 already claims. Counts are what they
# returned when validated on 2026-08-27, twice each, identically.
#
# ORDER BY is not decoration. `LIMIT` without it is NOT deterministic in Kuzu:
# the same pinned neighbourhood query returned 50 then 34 nodes on consecutive
# runs. A card that redraws differently on every click undermines the one thing
# this demo is arguing, so the starters are pinned to a stable row order.
#
# A fifth starter was cut for exactly this reason: "everything TP53 touches"
# was meant to show all 8 node types at once, but LIMIT samples across relation
# tables non-deterministically -- it gave 8 types once and 6 the next run. The
# node-type card already states all 8 exactly from `graph_node_type_counts`;
# promising it again from a sampled query would be weaker, not stronger.
# (UNION ALL per type is not an option: Kuzu's binder rejects branches whose
# node variable binds different node tables.)
DEFAULTS: list[dict[str, Any]] = [
    {
        "id": "association",
        "label": "Breast cancer and its associated proteins",
        "shows": "the association layer — disease_protein, plus the interactions among those proteins",
        "measured": "25 nodes / 64 edges",
        "query": (
            'MATCH (d:disease)<-[e1:disease_protein]-(p1:protein)'
            '-[e2:protein_protein]-(p2:protein)-[e3:disease_protein]->(d) '
            'WHERE LOWER(d.node_name) = LOWER("breast cancer") '
            'RETURN d, e1, p1, e2, p2, e3 ORDER BY p1.node_index, p2.node_index LIMIT 40'
        ),
    },
    {
        "id": "ppi",
        "label": "TP53's protein interactions",
        "shows": "the PPI layer alone — the edges the provenance card breaks down by source",
        "measured": "21 nodes / 40 edges",
        "query": (
            'MATCH (p:protein)-[e:protein_protein]-(q:protein) '
            'WHERE LOWER(p.node_name) = LOWER("TP53") '
            'RETURN p, e, q ORDER BY q.node_index LIMIT 40'
        ),
    },
    {
        "id": "pathway",
        "label": "TP53's pathways",
        "shows": "pathway_protein — one of the 18 relations, and the first hop of Act 2's GPGD route",
        "measured": "31 nodes / 30 edges",
        "query": (
            'MATCH (p:protein)-[e:pathway_protein]-(w:pathway) '
            'WHERE LOWER(p.node_name) = LOWER("TP53") '
            'RETURN p, e, w ORDER BY w.node_index LIMIT 30'
        ),
    },
    {
        "id": "drugs",
        "label": "TP53's drugs",
        "shows": "drug_protein — the smallest layer here, and the reason tractability is a separate axis",
        "measured": "6 nodes / 5 edges",
        "query": (
            'MATCH (p:protein)-[e:drug_protein]-(dr:drug) '
            'WHERE LOWER(p.node_name) = LOWER("TP53") '
            'RETURN p, e, dr ORDER BY dr.node_index LIMIT 25'
        ),
    },
]


# NB: there is deliberately no query-rewriting here. An earlier version appended
# a constraint block to natural-language asks (LIMIT, aggregate, undirected).
# All of it now lives in the agent's system prompt, where it is reviewable and
# applies to every caller -- including Agent Hub -- instead of only to this app.
class SearchBody(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


@router.get("/defaults")
def defaults() -> dict[str, Any]:
    return {"defaults": [{k: v for k, v in d.items()} for d in DEFAULTS]}


def _find_graph(payload: dict[str, Any]) -> dict[str, Any] | None:
    """The `customData.graph` of the first artifact part of type GRAPH.

    The same scan Agent Hub performs on a tool result, and the reason a payload
    that renders in the chat renders here too. Works unchanged on an agent
    response: the agent forwards the tool's artifact untouched.
    """
    for artifact in payload.get("artifacts") or []:
        for part in artifact.get("parts") or []:
            if part.get("type") == "GRAPH":
                graph = (part.get("customData") or {}).get("graph")
                if isinstance(graph, dict):
                    return graph
    return None


def _edge_table(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    """A subgraph as a table: one row per edge, source -> relation -> target.

    Derived here rather than taken from the tool, whose own table for a graph
    answer has the Cypher return variables as columns (`p`, `e`, `dr`) and whole
    node objects as cells -- unreadable. The edge list is how a person reads a
    subgraph in rows, and it is what the graph explorer shows beside its canvas.
    """
    label = {n["id"]: (n.get("label"), n.get("group_name")) for n in nodes}
    rows = []
    for e in edges[:MAX_TABLE_ROWS]:
        s_label, s_type = label.get(e.get("src"), (e.get("src"), ""))
        t_label, t_type = label.get(e.get("dst"), (e.get("dst"), ""))
        rows.append([s_label, s_type, e.get("display_relation") or e.get("group_name"),
                     t_label, t_type])
    return {
        "columns": ["source", "source type", "relation", "target", "target type"],
        "rows": rows,
        "n_rows": len(edges),
        "truncated": len(edges) > MAX_TABLE_ROWS,
    }


def _generated_cypher(raw: dict[str, Any]) -> str | None:
    """The Cypher the agent's tool call actually ran.

    Not a key on the response: the tool's output rides along as a JSON *string*
    nested in the trace, so this walks for a string that parses and carries
    `cypher_query`. Worth the trouble -- for a natural-language question this is
    the only place the real query appears, and it is what makes the answer
    auditable and the Cypher panel editable.
    """
    found: list[str] = []

    def walk(node: Any) -> None:
        if found:
            return
        if isinstance(node, str):
            if "cypher_query" not in node:
                return
            try:
                inner = json.loads(node)
            except Exception:
                return
            if isinstance(inner, dict) and inner.get("cypher_query"):
                found.append(str(inner["cypher_query"]))
            return
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(raw)
    return found[0] if found else None


def _explain(exc: Exception) -> str:
    """Turn a DSS-side failure into something a reader can act on."""
    msg = str(exc)
    if "maxOutputSizeMB" in msg or "output size exceeds" in msg:
        return ("That question produced an unbounded query — it tried to return a large "
                "share of the graph at once. Name a specific gene or disease, or ask "
                "for a count rather than the records themselves.")
    if "timeout" in msg.lower():
        return "The query ran past the timeout. Narrow the question, or add a LIMIT."
    return f"The graph agent did not answer: {msg}"


def _shape(raw: dict[str, Any], answer: str | None, cypher: str | None) -> dict[str, Any]:
    """Turn a tool-or-agent payload into what the card renders.

    The three modes are read off the DATA, never decided by policy here: nodes
    present -> a subgraph; rows but no nodes -> a table; neither -> nothing
    matched. Both routes converge on this so the two paths cannot drift apart.
    """
    graph = _find_graph(raw)
    nodes = (graph or {}).get("nodes") or []

    if not nodes:
        table = None
        out = _output_table(raw)
        if out:
            table = out
        return {"mode": "table" if table else "empty",
                "answer": answer, "cypher": cypher, "table": table,
                "nodes": [], "edges": [], "n_nodes": 0, "n_edges": 0,
                "truncated": False, "empty": table is None,
                "graph_name": (graph or {}).get("graph_name")}

    edges = (graph or {}).get("edges") or []
    truncated = len(nodes) > MAX_NODES
    if truncated:
        kept = {n["id"] for n in nodes[:MAX_NODES]}
        nodes = [n for n in nodes if n["id"] in kept]
        edges = [e for e in edges if e.get("src") in kept and e.get("dst") in kept]

    # Only what the renderer and the table need. `properties` on every node is
    # most of the payload weight (a 6-node answer was 52 KB); display_relation is
    # the one property worth keeping -- it is the readable verb the explorer
    # shows on hover ("associated with", "INHIBITOR").
    out_nodes = [{"id": n["id"], "label": n.get("label"), "group_name": n.get("group_name")}
                 for n in nodes]
    out_edges = [{"id": e["id"], "src": e["src"], "dst": e["dst"],
                  "group_name": e.get("group_name"),
                  "display_relation": (e.get("properties") or {}).get("display_relation")}
                 for e in edges]

    return {
        "mode": "graph", "answer": answer, "cypher": cypher,
        "nodes": out_nodes, "edges": out_edges,
        "n_nodes": len(out_nodes), "n_edges": len(out_edges),
        "truncated": truncated,
        "dropped_nodes": (len((graph or {}).get("nodes") or []) - len(out_nodes)) if truncated else 0,
        "graph_name": (graph or {}).get("graph_name"),
        "table": _edge_table(out_nodes, out_edges),
        "empty": False,
    }


def _output_table(raw: dict[str, Any]) -> dict[str, Any] | None:
    """{columns, rows} when the answer was tabular rather than a subgraph.

    An aggregation ("count by node type") comes back with rows and no nodes at
    all. Treating that as "no match" was wrong -- the query succeeded, it just
    answered with a table.
    """
    blob = raw.get("output")
    if not isinstance(blob, str):
        return None
    try:
        out = json.loads(blob)
    except Exception:
        return None
    tbl = out.get("table") if isinstance(out, dict) else None
    if not isinstance(tbl, dict):
        return None
    cols = [c.get("name") for c in (tbl.get("columns") or []) if isinstance(c, dict)]
    rows = tbl.get("rows") or []
    if not cols or not rows:
        return None
    return {"columns": cols,
            "rows": [[r.get(c) for c in cols] for r in rows[:MAX_TABLE_ROWS]],
            "n_rows": len(rows),
            "truncated": len(rows) > MAX_TABLE_ROWS}


@router.post("/cypher")
def run_cypher(body: SearchBody) -> dict[str, Any]:
    """Execute literal Cypher against the graph. NO LLM anywhere in this path.

    This is what the pinned starters and the editable Cypher panel use. The tool
    accepts either English or Cypher on the same key and runs Cypher verbatim, so
    a query typed here reaches the engine unchanged: deterministic, ~2.7s rather
    than ~8s, and no tokens. Nothing here interprets the query -- if it is wrong,
    the engine's own message comes back.
    """
    try:
        raw = get_project().get_agent_tool(GRAPH_TOOL_ID).run({"query": body.query})
    except Exception as e:
        logger.warning("graph tool call failed: %s", type(e).__name__)
        raise HTTPException(status_code=502, detail=_explain(e))

    if raw.get("error"):
        raise HTTPException(status_code=400, detail=str(raw["error"]))

    # The query IS the Cypher on this route, so the panel round-trips exactly.
    return _shape(raw, answer=None, cypher=body.query)


@router.post("/search")
def search(body: SearchBody) -> dict[str, Any]:
    """Ask the agent in natural language. The agent owns how to query."""
    try:
        completion = get_project().get_llm(GRAPH_AGENT).new_completion()
        completion.with_message(body.query)
        response = completion.execute()
    except Exception as e:
        logger.warning("graph agent call failed: %s", type(e).__name__)
        raise HTTPException(status_code=502, detail=_explain(e))

    raw: dict[str, Any] = getattr(response, "_raw", None) or {}
    if not raw.get("ok", True):
        raise HTTPException(status_code=502, detail="The graph agent returned no answer.")

    return _shape(raw,
                  answer=(raw.get("text") or "").strip() or None,
                  # Recovered from the trace so the panel can be edited and re-run
                  # without the LLM. This is the whole audit trail for an NL ask.
                  cypher=_generated_cypher(raw))


# ── Act 4: the mechanism behind one candidate ────────────────────────────────
# FIVE ROUTES, FIVE QUERIES, MERGED HERE -- and the reason is not stylistic.
#
# The natural way to write this is one query with an OPTIONAL MATCH per route.
# It does not survive the engine. Consecutive OPTIONAL MATCH clauses MULTIPLY
# rows rather than adding them, so for HRAS against HER2+ breast carcinoma the
# four graph routes join to roughly 40 x 148 x 20 x 139 ~ 16M rows before
# `LIMIT 400` trims anything -- LIMIT bounds the OUTPUT, not the join. Measured:
# 173s, then `AIQueryExecutionException: Interrupted`. A UNION ALL rewrite timed
# out too (and Kuzu's binder rejects branches whose mediator binds different
# node tables anyway).
#
# Run separately each route is 2-5s, so they are issued concurrently and the
# subgraphs are merged by node and edge id. That also produces something the
# single query could not: a PER-ROUTE COUNT, which is the honest answer to "why
# this gene?" -- it says which kinds of evidence exist and which are absent.
#
# Each route carries its own LIMIT so one hub-heavy route cannot swamp the
# canvas with the others invisible underneath it.
MECHANISM_ROUTES: list[dict[str, Any]] = [
    {
        "key": "ppi", "label": "a direct interaction", "feature": "dwpc_GGD",
        "limit": 100,
        "pattern": ("MATCH (g)-[r1:protein_protein]-(m:protein)-[a:disease_protein]-(D)\n"
                    "  WHERE m.node_index <> g.node_index\n"
                    "RETURN g, D, r1, m, a"),
    },
    {
        "key": "pathway", "label": "a shared pathway", "feature": "dwpc_GPGD",
        "limit": 100,
        "pattern": ("MATCH (g)-[r1:pathway_protein]-(x:pathway)-[r2:pathway_protein]"
                    "-(m:protein)-[a:disease_protein]-(D)\n"
                    "  WHERE m.node_index <> g.node_index\n"
                    "RETURN g, D, r1, x, r2, m, a"),
    },
    {
        # The GO routes need the degree cap. Without it a top-level term like
        # "protein binding" pulls in thousands of proteins that share nothing
        # specific -- the hub is the match, not the biology.
        "key": "molfunc", "label": "a shared molecular function", "feature": "dwpc_GFGD",
        "limit": 60,
        "pattern": ("MATCH (g)-[r1:molfunc_protein]-(x:molecular_function)-[r2:molfunc_protein]"
                    "-(m:protein)-[a:disease_protein]-(D)\n"
                    "  WHERE m.node_index <> g.node_index\n"
                    "    AND COUNT { MATCH (x)-[:molfunc_protein]-() } <= 200\n"
                    "RETURN g, D, r1, x, r2, m, a"),
    },
    {
        "key": "bioprocess", "label": "a shared biological process", "feature": "dwpc_GBGD",
        "limit": 100,
        "pattern": ("MATCH (g)-[r1:bioprocess_protein]-(x:biological_process)-[r2:bioprocess_protein]"
                    "-(m:protein)-[a:disease_protein]-(D)\n"
                    "  WHERE m.node_index <> g.node_index\n"
                    "    AND COUNT { MATCH (x)-[:bioprocess_protein]-() } <= 200\n"
                    "RETURN g, D, r1, x, r2, m, a"),
    },
    {
        # NOT A MODEL FEATURE -- and the distinction matters enough that the card
        # states it. No feature traverses a drug node, so nothing here fed the
        # score. It IS one of three routes admitting a pair into the candidate
        # pool, so it shaped the scored population: "not a feature", never
        # "not used". Only the two drug_disease relations this graph actually
        # holds; contraindication was never built (GRAPH_BUILDING.md 7.3).
        "key": "drug", "label": "a drug linking both", "feature": None,
        "limit": 40,
        "pattern": ("MATCH (g)-[r1:drug_protein]-(x:drug)-[r2:drug_disease]-(D)\n"
                    "  WHERE r2.display_relation IN ['indication', 'drug_investigated_for']\n"
                    "RETURN g, D, r1, x, r2"),
    },
]


def _mechanism_cypher(route: dict[str, Any], disease: int, gene: int) -> str:
    """One route's query, with the live node indices bound in.

    Indices are snapshot-specific, so they are always generated from the current
    row rather than taken from a literal in a document.
    """
    return (f"MATCH (D:disease {{node_index: {disease}}})\n"
            f"MATCH (g:protein {{node_index: {gene}}})\n"
            f"{route['pattern']} LIMIT {route['limit']}")


# The same five routes as ONE query, for the Visual Graph Explorer.
#
# This is the form to reach for by hand, and it is the form the card offers for
# copying -- the Explorer talks to Kuzu directly and returns it in about a
# second. It is NOT what this webapp executes: the agent tool's Kuzu instance
# runs in a memory-constrained kernel, where the chained OPTIONAL MATCH product
# exhausts the buffer pool ("Buffer manager exception: the buffer pool is full",
# reproduced on three warm attempts at 68-108s). Same query, different execution
# context, and only one of them is available to a webapp backend.
EXPLORER_TEMPLATE = """// Why {gene_name}? Every evidence route to genes already
// annotated for {disease_name}.
MATCH (D:disease {{node_index: {disease}}})
MATCH (g:protein {{node_index: {gene}}})

OPTIONAL MATCH (g)-[ppi:protein_protein]-(m1:protein)-[a1:disease_protein]-(D)
  WHERE m1.node_index <> g.node_index

OPTIONAL MATCH (g)-[pp1:pathway_protein]-(P:pathway)-[pp2:pathway_protein]-(m2:protein)-[a2:disease_protein]-(D)
  WHERE m2.node_index <> g.node_index

OPTIONAL MATCH (g)-[mf1:molfunc_protein]-(F:molecular_function)-[mf2:molfunc_protein]-(m3:protein)-[a3:disease_protein]-(D)
  WHERE m3.node_index <> g.node_index
    AND COUNT {{ MATCH (F)-[:molfunc_protein]-() }} <= 200

OPTIONAL MATCH (g)-[bp1:bioprocess_protein]-(B:biological_process)-[bp2:bioprocess_protein]-(m4:protein)-[a4:disease_protein]-(D)
  WHERE m4.node_index <> g.node_index
    AND COUNT {{ MATCH (B)-[:bioprocess_protein]-() }} <= 200

OPTIONAL MATCH (g)-[dp:drug_protein]-(DR:drug)-[dd:drug_disease]-(D)
  WHERE dd.display_relation IN ['indication', 'drug_investigated_for']

RETURN g, D,
       ppi, m1, a1,
       pp1, P, pp2, m2, a2,
       mf1, F, mf2, m3, a3,
       bp1, B, bp2, m4, a4,
       dp, DR, dd
LIMIT 400"""


class MechanismBody(BaseModel):
    disease: int
    gene: int
    # Only for the copyable Explorer query's comment header; never interpolated
    # into anything executed here.
    disease_name: str = Field(default="this disease", max_length=200)
    gene_name: str = Field(default="this gene", max_length=100)


@router.post("/mechanism")
def mechanism(body: MechanismBody) -> dict[str, Any]:
    """Every evidence route from one candidate to one disease, as one subgraph.

    Literal Cypher throughout -- no LLM, so the picture is deterministic and the
    queries below it are exactly what ran.
    """
    def fetch(route: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
        cypher = _mechanism_cypher(route, body.disease, body.gene)
        try:
            raw = get_project().get_agent_tool(GRAPH_TOOL_ID).run({"query": cypher})
        except Exception as e:
            logger.warning("mechanism route %s failed: %s", route["key"], type(e).__name__)
            return route, None, _explain(e)
        if raw.get("error"):
            return route, None, str(raw["error"])
        return route, _find_graph(raw) or {"nodes": [], "edges": []}, None

    # Concurrent because sequential is 5 x 2-5s and this sits behind a click
    # someone makes in front of an audience.
    with ThreadPoolExecutor(max_workers=len(MECHANISM_ROUTES)) as pool:
        results = list(pool.map(fetch, MECHANISM_ROUTES))

    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    routes_out: list[dict[str, Any]] = []

    for route, graph, err in results:
        r_nodes = (graph or {}).get("nodes") or []
        r_edges = (graph or {}).get("edges") or []
        # g and D come back on every route; they are context, not evidence, so
        # the per-route count reports the edges -- the thing that is actually
        # this route's finding.
        # NO "capped" BOOLEAN HERE. The LIMIT bounds ROWS and this counts EDGES,
        # and the two are not comparable: one pathway row returns three edges
        # (gene->term, term->neighbour, neighbour->disease), one PPI row returns
        # two. Comparing 161 edges against a limit of 100 would have flagged
        # "capped" on routes that returned everything they had. The limit is
        # reported as what it is -- the per-route bound -- and the card states
        # it rather than inferring truncation it cannot actually observe.
        routes_out.append({
            "key": route["key"], "label": route["label"], "feature": route["feature"],
            "n_edges": len(r_edges), "row_limit": route["limit"], "error": err,
        })
        for n in r_nodes:
            nodes.setdefault(n["id"], {"id": n["id"], "label": n.get("label"),
                                       "group_name": n.get("group_name")})
        for e in r_edges:
            edges.setdefault(e["id"], {
                "id": e["id"], "src": e["src"], "dst": e["dst"],
                "group_name": e.get("group_name"),
                "display_relation": (e.get("properties") or {}).get("display_relation"),
            })

    out_nodes = list(nodes.values())
    out_edges = list(edges.values())
    truncated = len(out_nodes) > MAX_NODES
    dropped = 0
    if truncated:
        kept = {n["id"] for n in out_nodes[:MAX_NODES]}
        dropped = len(out_nodes) - len(kept)
        out_nodes = [n for n in out_nodes if n["id"] in kept]
        out_edges = [e for e in out_edges if e["src"] in kept and e["dst"] in kept]

    return {
        "mode": "graph" if out_nodes else "empty",
        "nodes": out_nodes, "edges": out_edges,
        "n_nodes": len(out_nodes), "n_edges": len(out_edges),
        "truncated": truncated, "dropped_nodes": dropped,
        "table": _edge_table(out_nodes, out_edges) if out_edges else None,
        "routes": routes_out,
        # What actually ran, so the card can show and copy it.
        "queries": [{"key": r["key"], "label": r["label"],
                     "cypher": _mechanism_cypher(r, body.disease, body.gene)}
                    for r in MECHANISM_ROUTES],
        # The one-query form, for the Explorer rather than for here.
        "explorer_cypher": EXPLORER_TEMPLATE.format(
            disease=body.disease, gene=body.gene,
            disease_name=body.disease_name, gene_name=body.gene_name),
    }
