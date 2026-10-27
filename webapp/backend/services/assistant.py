"""The in-app evidence assistant for ONE selected pair (redesign D1, workplan Phase 7a).

A tool-calling loop in the backend, the way bs-blueprint builds assistants, over the LLM Mesh's own
tool calling (no LangChain: the project code env has none). Three DSS agent tools are the only tools:

  graph_search    b6Rpbve  text-to-Cypher over the Kuzu graph
  trials_search   4I2L6YL  Cortex search over ClinicalTrials.gov
  papers_search   FNxhpfF  Cortex search over the PubMed open-access subset

Every question carries the pair's context with an id per item the model may cite: M (the model's own
numbers), D1.. (drug records), T1.. / P1.. (the trials and papers Phase 6 cached for the pair). A
tool result adds G1.. (graph results) or an NCT / PMID id. Each tool output is TRIMMED before the
model reads it: graph search returns every node and edge (up to 191 KB measured), so the model gets
the generated Cypher, the distinct names by type and the row count; a Cortex search gets ids, titles
and the text around the gene's mentions.

The answer contract (D1) is enforced HERE, after the answer is complete, not trusted to the prompt:
a citation that resolves to nothing is removed and its sentence marked; a sentence tagged [GK] or
with no citation renders as "not from a retrieved source"; prescriptive phrasing is flagged. Nothing
is stored: the page sends the conversation with each question.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import re
import threading
import time
from collections.abc import Iterator
from typing import Any

from ..dss_client import get_project
from ..routes import candidates
from . import dataset_cache, pair_sources

MODEL = pair_sources.MODEL
MAX_ROUNDS = 6
TIME_LIMIT_S = 45
# A single tool call is abandoned after this: graph search on a compound question ran 60-110 s
# (2026-10-27), and one exceeded DSS's 50 MB tool-output limit.
TOOL_TIMEOUT_S = 25
# Tool calls per answer; one per drug for 23 drugs took 95 s.
MAX_TOOL_CALLS = 8
_pool = cf.ThreadPoolExecutor(max_workers=4)
# Graph searches run one at a time: four of eight concurrent graph searches returned no output
# (2026-10-27). Cortex searches still run in parallel.
_graph_lock = threading.Lock()
MAX_GRAPH_NAMES = 50
TOOL_IDS = {"graph_search": "b6Rpbve", "trials_search": "4I2L6YL", "papers_search": "FNxhpfF"}

TOOLS = [
    {"type": "function", "function": {
        "name": "graph_search",
        "description": "Ask the biomedical knowledge graph a question in plain English; it writes and runs Cypher. "
                       "Name genes by HGNC symbol and diseases exactly as given. Ask for counts or short lists.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "trials_search",
        "description": "Search ClinicalTrials.gov. Lead the query with the gene symbol.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "papers_search",
        "description": "Search the PubMed open-access subset. Lead the query with the gene symbol.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
]

SYSTEM = """You answer questions about ONE candidate gene for ONE disease, in a target-prioritization demo for scientists.

Sources and citations:
- The context below gives ids you may cite: M (the model's rank, score and SHAP drivers), D1.. (drug records), T1.. (trials), P1.. (papers).
- A graph_search result is cited G1, G2.. in the order you called it. A trial or paper you retrieve yourself is cited by its id, e.g. [NCT01234567] or [PMID:12345678].
- Put citations in square brackets at the end of the sentence they support, before the full stop: "... reduces growth [P2][G1]."
- A sentence from your general knowledge, not from a cited source, must end with [GK].
- Never cite an id you were not given or did not retrieve.

Rules:
- Search only when the context does not answer the question. Prefer graph_search for structure (interactions, pathways, drugs, associations), the trial and paper tools for evidence.
- A trial's phase or status says nothing about whether it worked. Retrieved counts are what the search returned, never all that exist.
- Do not recommend what to pursue, rank, or test next. Describe; do not prescribe.
- Be brief: a few sentences or a short list.

The graph: node types protein (genes), disease, drug, pathway, biological_process, molecular_function. Protein-protein interactions are stored in both directions, so ask for DISTINCT partners. Ask graph_search for counts or named lists; it ignores "at most N".
Ask graph_search ONE relationship, or one chain of relationships, per call: "Which drugs target ERBB2?", or for a list "Which diseases are the drugs that target ERBB2 indicated for?" (one call, not one per drug). Never branch into several kinds of things in one question (drugs AND pathways AND processes): such a question builds a query too large to run. You have at most 8 searches per answer."""

CITE = re.compile(r"\[(GK|M|[TPDG]\d+|NCT\d{8}|PMID:\s?\d+)\]")
ANY_BRACKET = re.compile(r"\[([^\[\]]{1,40})\]")
PRESCRIPTIVE = re.compile(r"\b(you should|we recommend|i recommend|should be (pursued|prioriti[sz]ed|tested)|the next target|worth pursuing|must be targeted)\b", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9*\-•])")


# ── Context ────────────────────────────────────────────────────────────────────────────────────

def build_context(disease: int, gene: int) -> dict[str, Any]:
    """The pair's facts with an id per citable item, and a text block for the model."""
    df = candidates._frame()
    hit = df[(df.disease_index == disease) & (df.gene_index == gene)]
    if hit.empty:
        raise LookupError(f"gene_index {gene} is not in disease {disease}'s pool")
    row = hit.iloc[0]
    ctx = pair_sources.context(disease, gene)
    refs: dict[str, dict[str, Any]] = {}

    try:
        drivers = candidates.pair_drivers(disease=disease, gene=gene)["drivers"]
    except Exception:
        drivers = []
    refs["M"] = {"kind": "model", "label": "Model rank and drivers",
                 "text": f"rank {int(row.rank_in_disease)} of {int(row.disease_pool_size)} for {row.disease_name}; "
                         f"recorded association: {'yes' if row.is_target else 'no (novel)'}; top SHAP drivers: "
                         + "; ".join(f"{d['label'] or d['key']} {d['shap']:+.2f}"
                                     + (f" (stronger than {d['percentile']}% of the pool)" if d["percentile"] is not None else "")
                                     for d in drivers)}
    for i, d in enumerate(candidates.pair_drugs(disease=disease, gene=gene)["records"], 1):
        refs[f"D{i}"] = {"kind": "drug", "label": d["drug_name"] or d["drug_id"], "id": d["drug_id"],
                         "text": f"{d['drug_name']} ({d['drug_id']}): {d['max_stage']} for this disease; "
                                 f"acts on {row.gene_name} as {', '.join(d['action_type']) or 'unrecorded'}"}

    doc = pair_sources._read(disease, gene)
    for corpus, pre in (("trials", "T"), ("papers", "P")):
        if not doc:
            break
        picks = {p["id"]: p for p in (doc.get("selection") or {}).get(corpus, [])}
        recs = sorted(doc["search"][corpus]["records"], key=lambda r: r["id"] not in picks)
        for i, r in enumerate(recs, 1):
            p = picks.get(r["id"])
            refs[f"{pre}{i}"] = {"kind": corpus[:-1], "label": r["title"] or r["id"], "id": r["id"], "url": r.get("url"),
                                 "text": f"{r['id']}: {r['title']}"
                                         + (f" [labelled {p['role']}, {p['subtype_match']}: \"{p['quote']}\"]" if p else "")}

    ident = candidates._identity_at(dataset_cache.build_stamp(candidates.IDENTITY)).get(gene) or {}
    flags = [f for f, on in (("approved drug for this disease", row.approved_for_disease),
                             ("drug in trials for this disease", row.investigational_for_disease),
                             ("safety liability recorded", row.has_safety_liability)) if on]
    lines = [f"Gene: {row.gene_name} — {ident.get('name') or 'no HGNC name'}; HGNC {ident.get('hgnc_id') or '—'}; "
             f"aliases: {', '.join(ctx['aliases']) or 'none'}",
             f"Disease: {row.disease_name}; family anchor: {ctx['anchor_name'] or 'none'}",
             "Flags: " + (", ".join(flags) or "none"),
             ""]
    lines += [f"[{k}] {v['text']}" for k, v in refs.items()]
    if not doc:
        lines.append("(No cached trials or papers for this pair: search if the question needs them.)")
    return {"ctx": ctx, "refs": refs, "text": "\n".join(lines), "gene": str(row.gene_name),
            "disease": str(row.disease_name)}


# ── Tools: run and trim ────────────────────────────────────────────────────────────────────────

def _graph_summary(out: dict[str, Any]) -> dict[str, Any]:
    names: dict[str, set] = {}
    rows = (out.get("table") or {}).get("rows") or []
    scalars = []
    for r in rows:
        for v in r.values():
            if isinstance(v, dict) and "label" in v and "properties" in v:
                names.setdefault(v.get("name") or "node", set()).add(v["label"])
            elif not isinstance(v, dict):
                scalars.append(v)
    body = "\n".join(l for l in (out.get("cypher_query") or "").splitlines() if not l.strip().startswith("//")).strip()
    by_type = {t: sorted(s)[:MAX_GRAPH_NAMES] for t, s in names.items()}
    return {"cypher": body, "title": out.get("title"), "rows": len(rows),
            "distinct": {t: len(s) for t, s in names.items()}, "names": by_type, "values": scalars[:20],
            "truncated": any(len(s) > MAX_GRAPH_NAMES for s in names.values())}


def _call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """The DSS tool call itself: the slow part, run in parallel with the round's other calls."""
    if name not in TOOL_IDS:
        raise RuntimeError(f"unknown tool {name}")
    run = get_project().get_agent_tool(TOOL_IDS[name]).run
    if name == "graph_search":
        with _graph_lock:
            return run({"query": args.get("query", "")})
    return run({"query": args.get("query", "")})


def register(name: str, args: dict[str, Any], res: dict[str, Any], state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Trim a tool result and record what it may be cited as. Run in call order, so G1, G2.. follow
    the order the model asked. Returns (text for the model, event payload for the page)."""
    out = res.get("output")
    if out is None:
        raise RuntimeError("the tool returned no output")
    if name == "graph_search":
        out = json.loads(out) if isinstance(out, str) else out
        if not out.get("success", True):
            raise RuntimeError("the graph query failed")
        g = _graph_summary(out)
        gid = f"G{len(state['graph']) + 1}"
        state["graph"][gid] = {**g, "query": args.get("query")}
        return json.dumps({"id": gid, **{k: g[k] for k in ("rows", "distinct", "names", "values", "truncated")}}), \
            {"id": gid, "summary": f"{g['rows']} rows; " + ", ".join(f"{n} {t}" for t, n in g["distinct"].items())}
    corpus = "trials" if name == "trials_search" else "papers"
    recs = []
    for r in out:
        rec = pair_sources._record(corpus, r)
        if not rec["id"]:
            continue
        key = rec["id"] if corpus == "trials" else f"PMID:{rec['id']}"
        state["retrieved"][key] = {"kind": corpus[:-1], "label": rec["title"] or rec["id"], "id": rec["id"], "url": rec.get("url")}
        recs.append({"cite": key, "title": rec["title"], "status": rec.get("status"), "phases": rec.get("phases"),
                     "text": pair_sources._trim(state["pair"]["ctx"], rec["passage"])[:1500]})
    return json.dumps(recs), {"summary": f"{len(recs)} {corpus} retrieved"}


# ── The loop ───────────────────────────────────────────────────────────────────────────────────

def _completion(messages: list[dict[str, Any]], with_tools: bool):
    q = get_project().get_llm(MODEL).new_completion()
    if with_tools:
        q.settings["tools"] = TOOLS
    q.cq["messages"].extend(messages)
    return q


def answer(disease: int, gene: int, question: str, history: list[dict[str, str]]) -> Iterator[dict[str, Any]]:
    """Yield events: text_delta, tool_call_started, tool_call_completed, answer, error."""
    t0 = time.monotonic()
    try:
        pair = build_context(disease, gene)
    except Exception as e:
        yield {"type": "error", "message": str(e)}
        return
    state: dict[str, Any] = {"pair": pair, "graph": {}, "retrieved": {}, "tool_errors": [], "calls": 0}
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM + "\n\nCONTEXT\n" + pair["text"]}]
    for h in history[-10:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": question})

    text = ""
    for rnd in range(MAX_ROUNDS + 1):
        last = rnd == MAX_ROUNDS or time.monotonic() - t0 > TIME_LIMIT_S
        if last:
            messages.append({"role": "user", "content": "Answer now with what you have; do not call tools."})
        text, calls = "", {}
        try:
            for ch in _completion(messages, with_tools=not last).execute_streamed():
                d = getattr(ch, "data", None) or {}
                if d.get("text"):
                    text += d["text"]
                    yield {"type": "text_delta", "content": d["text"]}
                for tc in d.get("toolCalls") or []:
                    c = calls.setdefault(tc.get("index", 0), {"id": None, "name": "", "arguments": ""})
                    c["id"] = tc.get("id") or c["id"]
                    f = tc.get("function") or {}
                    c["name"] += f.get("name") or ""
                    c["arguments"] += f.get("arguments") or ""
        except Exception as e:
            yield {"type": "error", "message": f"The model call failed: {e}"}
            return
        if not calls:
            break
        tool_calls = [{"type": "function", "id": c["id"], "function": {"name": c["name"], "arguments": c["arguments"]}}
                      for _, c in sorted(calls.items())]
        messages.append({"role": "assistant", "toolCalls": tool_calls})
        # The round's calls run in parallel, each within what is left of the answer's time.
        pending = []
        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
            except ValueError:
                args = {}
            yield {"type": "tool_call_started", "id": tc["id"], "name": name, "args": args}
            if state["calls"] >= MAX_TOOL_CALLS:
                pending.append((tc, name, args, None))
                continue
            state["calls"] += 1
            pending.append((tc, name, args, _pool.submit(_call, name, args)))
        deadline = min(time.monotonic() + TOOL_TIMEOUT_S, t0 + TIME_LIMIT_S + TOOL_TIMEOUT_S)
        for tc, name, args, fut in pending:
            try:
                if fut is None:
                    raise RuntimeError(f"not run: this answer has used its {MAX_TOOL_CALLS} searches; answer with what you have")
                try:
                    res = fut.result(timeout=max(0.0, deadline - time.monotonic()))
                except cf.TimeoutError:
                    raise RuntimeError(f"no answer within {TOOL_TIMEOUT_S} s")
                output, payload = register(name, args, res, state)
                ok = True
            except Exception as e:
                output, payload, ok = f"Tool failed: {e}", {"summary": str(e)}, False
                state["tool_errors"].append({"name": name, "error": str(e)})
            messages.append({"role": "tool", "toolOutputs": [{"callId": tc["id"], "output": output}]})
            yield {"type": "tool_call_completed", "id": tc["id"], "name": name, "args": args, "ok": ok, **payload}

    yield {"type": "answer", **check(text, state), "seconds": round(time.monotonic() - t0, 1)}


# ── The contract check ─────────────────────────────────────────────────────────────────────────

def _resolve(token: str, state: dict[str, Any]) -> dict[str, Any] | None:
    refs = state["pair"]["refs"]
    if token in refs:
        return {"ref": token, **refs[token]}
    if token in state["graph"]:
        g = state["graph"][token]
        return {"ref": token, "kind": "graph", "label": g.get("title") or g.get("query")}
    key = re.sub(r"\s+", "", token)
    if key in state["retrieved"]:
        return {"ref": key, **state["retrieved"][key]}
    # an id the pair's cached records carry, cited by its own id rather than T/P
    for k, v in refs.items():
        if v.get("id") and (key == v["id"] or key == f"PMID:{v['id']}"):
            return {"ref": k, **v}
    return None


def check(text: str, state: dict[str, Any]) -> dict[str, Any]:
    sentences = []
    for line in text.splitlines():
        if not line.strip():
            continue
        for s in SENTENCE.split(line.strip()):
            tokens = ANY_BRACKET.findall(s)
            cites, unresolved, gk_tag = [], [], False
            for t in tokens:
                if not CITE.fullmatch(f"[{t}]"):
                    continue
                if t == "GK":
                    gk_tag = True
                    continue
                r = _resolve(t, state)
                (cites if r else unresolved).append(r or t)
            clean = CITE.sub("", s).strip()
            clean = re.sub(r"\s+([.,;:!?])", r"\1", clean)
            sentences.append({"text": clean, "citations": cites, "unresolved": unresolved,
                              "general_knowledge": gk_tag or not cites,
                              "prescriptive": bool(PRESCRIPTIVE.search(clean))})
    cited_graph = {c["ref"] for s in sentences for c in s["citations"] if c.get("kind") == "graph"}
    return {"sentences": sentences,
            "graph": [{"id": k, **v, "cited": k in cited_graph} for k, v in state["graph"].items()],
            "tool_errors": state["tool_errors"],
            "counts": {"sentences": len(sentences),
                       "cited": sum(1 for s in sentences if s["citations"]),
                       "general_knowledge": sum(1 for s in sentences if s["general_knowledge"]),
                       "unresolved": sum(len(s["unresolved"]) for s in sentences),
                       "prescriptive": sum(1 for s in sentences if s["prescriptive"])}}
