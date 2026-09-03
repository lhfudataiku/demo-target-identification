# Visual Graph Explorer integration scope

> **Lifecycle:** Decision · **Audience:** webapp implementers and technical reviewers · **Authority:**
> the agreed scope, target architecture, migration sequence and acceptance criteria for consolidating
> graph exploration in the Target Prioritizer · **Update when:** the agreed scope changes or an
> implementation phase is accepted · **Generated dependencies:** none · **Excludes:** current deployed
> webapp behavior, which remains governed by [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) until this migration
> is implemented and verified.

**Status: APPROVED FOR IMPLEMENTATION — 2026-09-02.** Repository implementation may proceed through
the phased rollout below. Live DSS configuration changes, deployment, commit and push remain separate
actions requiring their own approval.

## 1. Decision summary

Act 1 and Act 4 will use **one shared graph-exploration implementation** backed by the Visual Graph
Explorer webapp. They remain different narrative contexts, not different technical products:

| act | context passed to the shared implementation |
|---|---|
| Act 1 — Explore the graph | general graph exploration and deterministic starter queries |
| Act 4 — The mechanism, on the graph | the selected disease, target gene and generated mechanism query |

The Visual Graph Explorer will own Cypher execution, graph and table rendering, graph layouts, neighbor
expansion, edge inspection and other exploratory interactions. The Target Prioritizer will own the
demo narrative, candidate selection, query construction, scientific caveats and the action that opens
the Explorer.

The end state is **two uses, one implementation**. The migration must not leave a permanent Act 1
native graph path beside an Act 4 Explorer path.

## 2. Why this change is needed

### 2.1 Current Act 4 execution is disproportionately complex

The current Act 4 mechanism card cannot execute its natural combined Cypher through the graph agent
tool. Consecutive `OPTIONAL MATCH` clauses multiply rows before the final `LIMIT`, exhausting the
tool kernel for well-connected genes. It therefore:

1. constructs five route-specific Cypher queries;
2. submits five graph-tool calls concurrently;
3. extracts a graph artifact from each response;
4. merges nodes and edges by identifier;
5. calculates per-route summaries;
6. applies a second display cap; and
7. separately constructs the one-query form offered to the Visual Graph Explorer.

This logic exists only to reproduce a subset of a product already available in the Visual Graph
plug-in. The merge itself is not the main performance cost; the expensive boundary is the five graph
tool executions and their cold execution environment.

### 2.2 Act 1 and Act 4 already overlap

Both acts currently use the same local `ActGraph.vue` node-link renderer. Act 1 adds deterministic
starters, natural-language translation and editable Cypher. Act 4 adds selected-candidate state,
five-route orchestration and merging. Maintaining separate orchestration paths creates two places to
solve loading, errors, query display, graph limits and Explorer escalation.

### 2.3 The Explorer already owns the richer interaction

The configured Visual Graph Explorer provides the capabilities that would otherwise have to be
maintained locally: schema-aware Cypher editing, graph and table views, layouts, edge merging, node and
edge details, neighbor expansion, conditional styling, saved queries and an optional query generator.
The Target Prioritizer should link these capabilities into its narrative rather than reimplement them.

### 2.4 Current integration baseline

The integration target inspected on 2026-09-02 is:

| item | value |
|---|---|
| DSS project | `DEMO_TARGET_IDENTIFICATION` |
| Target Prioritizer standard webapp | `OlmPX9a` |
| Visual Graph Explorer webapp | `wBcApLN`, named *Graph Explorer* (renamed from *graph search* 2026-09-03) |
| Visual Graph plug-in | `visual-graph` 1.4.0 |
| Published graph folder | `graph` (`ytvuniN8`), merged from `DEMO_KG_LS.published_kg_ls-Mp25kL` |

The Explorer is a self-mounted Vue application with its own Flask backend. Plug-in version 1.4.0 has
no supported query deep link or parent-window `postMessage` contract for loading and executing a
supplied Cypher query. Its internal `/api/cypher/run` route is not an integration contract and must not
be called by the Target Prioritizer.

## 3. Goals

The work must:

1. Provide one reusable Explorer card and one reusable full-screen Explorer shell for Acts 1 and 4.
2. Preserve each act's narrative context while removing duplicate graph execution and rendering code.
3. Remove Act 4's five-query backend and merged-canvas path.
4. Migrate Act 1's starters and graph exploration to the same shared implementation.
5. Preserve deterministic Cypher handoff and make the query visible and copyable.
6. Keep the Explorer lazy: selecting a candidate or opening an act must not execute a graph query.
7. Preserve the current scientific caveats around model features, candidate admission and drug routes.
8. Work inside the nested DSS iframe, with a new-tab fallback if nested embedding is blocked.
9. Avoid any graph rebuild, dataset rebuild or modification to `KNOWLEDGE_GRAPH_PRIMEKG`.

## 4. Non-goals

This scope does not include:

- changing the graph schema, graph snapshot, graph folder or graph-building flow;
- modifying or forking the Visual Graph plug-in;
- calling undocumented Explorer backend endpoints;
- automatically executing a query on the user's behalf through DOM manipulation;
- reproducing Explorer layouts, neighbor expansion, conditional styling or rich table rendering;
- changing the target-prioritization model, features, candidate pool or ranked-list data contract;
- changing the Act 4 target-detail card beyond the wiring needed to launch the shared Explorer;
- introducing a new frontend component library;
- deploying, committing or pushing as part of implementation without the required separate approval.

## 5. Target architecture

```text
Act 1 card ──┐
             ├──► shared VisualGraphExplorerCard
Act 4 card ──┘              │
                            ├── builds or receives Cypher
                            ├── copies / exposes Cypher
                            └── opens shared Explorer shell
                                         │
                                         ▼
                         Visual Graph Explorer webapp wBcApLN
                         ├── query editor / saved queries
                         ├── direct Kuzu execution
                         ├── graph and table rendering
                         └── interactive graph exploration
```

### 5.1 Ownership boundary

| responsibility | owner |
|---|---|
| Act ordering and narrative | Target Prioritizer |
| Selected disease and gene | Target Prioritizer |
| Mechanism-query template | Target Prioritizer |
| Query visibility and copy handoff | shared Explorer card/shell |
| Cypher execution | Visual Graph Explorer |
| Graph/table visualization | Visual Graph Explorer |
| Layout, filtering and neighbor exploration | Visual Graph Explorer |
| Graph schema and publication | existing Visual Graph flow |

### 5.2 Shared frontend units

The implementation should introduce narrowly scoped shared units rather than one large view-specific
component:

- `frontend/src/components/graph/VisualGraphExplorerCard.vue` — shared card presentation and actions;
- `frontend/src/components/graph/VisualGraphExplorerDialog.vue` — full-screen iframe shell;
- `frontend/src/features/graph/mechanismCypher.ts` — pure Act 4 query builder;
- `frontend/src/utils/visualGraphExplorer.ts` — Explorer URL construction and environment checks;
- a small Pinia store or shared composable — open/close state, context title and optional query.

The dialog should be mounted once from the application layout. Act views pass context to it; they do
not each create and manage a separate Explorer iframe.

## 6. User experience contract

### 6.1 Shared card behavior

Both acts render the same card component with different props:

- title and act-specific explanatory copy;
- optional starter queries;
- optional selected disease and gene context;
- optional generated or currently edited Cypher;
- the primary **Open full Explorer** action;
- a secondary **Copy Cypher** action when a query exists.

No graph query runs on card mount. No query runs when an Act 4 candidate is selected.

### 6.2 Full Explorer shell

The full-screen shell should provide:

- an iframe created only when the shell opens;
- a loading state until the iframe reports `load`;
- an act-specific title such as `HRAS · HER2 positive breast carcinoma`;
- persistent `Copy Cypher`, `Open in new tab` and `Close` actions;
- Escape-to-close behavior and focus restoration;
- a retry state if the Explorer fails to load;
- no backdrop-click dismissal;
- a concise handoff message when a query was copied.

The iframe should use the DSS Visual Webapp view URL constructed from configured project and webapp
identifiers. It must not use the current app's `apiUrl()`, which targets the Target Prioritizer FastAPI
backend.

### 6.3 Query handoff

Until Visual Graph provides a supported deep-link or messaging contract, the handoff is explicit:

1. the user activates **Open full Explorer**;
2. the Target Prioritizer attempts to copy the relevant Cypher during that user gesture;
3. the full Explorer opens;
4. the shell explains: open the graph, select **New query**, paste and run;
5. if clipboard access is blocked, the query remains visible and selectable in the shell.

The implementation must not claim that the query was copied unless the Clipboard API confirms it.

### 6.4 Act 1 behavior

Act 1 passes general graph-exploration context to the shared card:

- deterministic starter queries remain available;
- selecting a starter prepares its literal Cypher for the Explorer;
- if an edited or previously generated Cypher exists during migration, that exact text is handed off;
- natural-language exploration moves to the Explorer's query generator;
- the final state has no Act 1-specific local graph renderer or graph-execution API.

### 6.5 Act 4 behavior

Act 4 passes the selected disease and target gene to the shared card. A pure frontend function generates
the approved launch query or route-specific preset immediately from their numeric node indices. The
query-design gate below decides whether the Explorer receives one bounded illustrative query or a set
of independently bounded route presets. The card keeps the distinction between:

- four graph routes corresponding to model path features; and
- the drug route, which is not a model feature but did affect candidate-pool admission.

The card must not report route presence, absence or edge counts before the Explorer query establishes
them. Those summaries currently come from the backend being removed.

## 7. Cypher contract

The Act 4 query design must preserve the reviewed mechanism semantics across its approved preset set:

- bind one disease node and one protein node by numeric `node_index`;
- traverse relationships undirected;
- bind and return relationship variables so the Explorer renders connected edges;
- cover direct protein interaction, pathway, molecular-function, biological-process and drug routes,
  without claiming that one globally limited result exhaustively represents all five;
- exclude the selected gene from the disease's annotated neighbor genes;
- cap molecular-function and biological-process mediator degree at 200;
- restrict drug-disease relations to `indication` and `drug_investigated_for`;
- retain a bounded result limit;
- include human-readable names only in sanitized comment lines, never executable clauses.

Numeric node indices are snapshot-specific. The query must always be generated from the currently
selected live candidate row; examples in documentation are not runtime defaults.

## 8. Implementation phases

### Execution governance

- Work proceeds as discrete waves matching the phases below. At the end of every wave, the
  orchestrator presents evidence against that phase's exit criterion and stops for user validation.
- No later wave begins from an agent's unreviewed output.
- Delegates receive the smallest model and reasoning level sufficient for their bounded task. Higher
  reasoning is reserved for iframe/authentication behavior, Cypher semantics and scientific copy;
  mechanical cleanup and inventories use lighter delegates.
- Every delegate receives an exclusive file or read-only evidence boundary. Delegates do not commit,
  deploy, change live DSS configuration, rebuild data, or modify the graph.
- Searches remain bounded to the affected code, generated indexes and routed documents. Agents do not
  load the large documentation corpus or plug-in bundle wholesale when a targeted query answers the
  question.
- The orchestrator owns shared interfaces, cross-agent changes, final integration tests and all
  approval gates.
- If evidence suggests a deviation from this approved scope or a new implementation hypothesis, the
  orchestrator stops and asks for permission before launching an expansive investigation.

### Phase 0 — integration spike and baseline

1. Use HER2-positive breast carcinoma and HRAS as the primary reference case.
2. Record the existing Act 4 cold and warm timings.
3. Record Explorer first-paint and query-execution timings.
4. Compare route coverage for connected, sparse, drug-linked and GO-hub candidates.
5. Verify that the Explorer can render inside the Target Prioritizer's existing DSS iframe.
6. Verify the same flow with a representative non-owner user.
7. Confirm that opening in a new tab is a viable fallback.

**Approved Wave 0 outcome — 2026-09-02:** conditional go for the launcher shell. No static frame
blocker was found, but authenticated owner and representative non-owner tests remain mandatory before
either act migrates. The current combined query did not pass semantic coverage; Phase 2 owns its
redesign and validation.

### Phase 1 — shared shell and configuration

1. Add explicit build-time configuration for the Explorer project key, backend webapp ID and
   browser-navigation object ID.
2. Add the URL-construction utility.
3. Add global Explorer launch state.
4. Implement the accessible, lazy full-screen shell.
5. Add clipboard-success, clipboard-failure, load-failure and new-tab behavior.
6. Add the shared card component with no act-specific data fetching.

**Exit criterion:** a temporary launch control can open and close the Explorer reliably without
executing a graph query or disturbing normal app navigation.

### Phase 2 — Act 4 query-design gate

The current one-query Explorer template is fast but is not semantically equivalent to the five
independently bounded routes. Consecutive `OPTIONAL MATCH` clauses multiply route bindings, and the
unordered global `LIMIT 400` can omit route evidence even when every route exists.

1. Compare normalized route-level node and relationship IDs for HRAS plus connected, sparse,
   drug-linked and GO-hub candidates.
2. Compare route-presence truth separately from raw edge-set coverage.
3. Measure raw query output separately from the Explorer's renderer cap.
4. Test route-specific queries with the existing per-route bounds as the default design: 100 PPI,
   100 pathway, 60 molecular-function, 100 biological-process and 40 drug paths. Apply a stable
   `ORDER BY`, including a unique node or relationship tie-breaker, before every route's `LIMIT`;
   a limit without ordering is not deterministic.
5. Treat a one-shot combined result as viable only if Kuzu supports independently bounded isolated
   route subqueries or a uniform-schema union for the published graph.
6. Retain a combined query only if it has proven coverage and deterministic ordering, or label it
   explicitly as a bounded illustrative sample rather than “every evidence route.”
7. Present the proposed query set, card wording and evidence for explicit user validation.

**Exit criterion:** the user has approved the A4 Explorer default-query design and its claims.

**Approved Wave 2 outcome — 2026-09-02:** A4 provides all five routes as the default query set.
Each query runs independently in Visual Graph Explorer and replaces the preceding result. Target
Prioritizer does not execute the queries in sequence, union their outputs, accumulate graph state, or
join their different result shapes. Publishing from the Explorer publishes only the currently
displayed query result.

#### Wave 2 design — five independent A4 default queries

Use five default queries rather than one combined query. Each query receives the selected
`disease_index` and `gene_index`, preserves one existing evidence route, orders the complete route
binding with stable relationship offsets, and only then applies its own cap. The A4 card exposes the
complete set and lets the user select and copy one query before opening the Explorer. It does not
execute queries itself, concatenate their results, or claim that one canvas contains every route.

The interaction contract is deliberately one-query-at-a-time:

1. Selecting a candidate regenerates the five query strings locally; it does not call a graph API.
2. The user selects one of the five default queries in the A4 card.
3. The card makes that query visible and copyable, then opens Visual Graph Explorer.
4. The user pastes and executes the selected query in the Explorer.
5. The Explorer displays—and may publish—only that query's result.
6. Running another default query replaces the current Explorer result; no prior result is retained or
   merged.

| Default query | Scientific role | Ordering keys | Cap |
|---|---|---|---:|
| PPI interaction | Model feature `dwpc_GGD` | mediator, PPI edge, disease edge | 100 |
| Shared pathway | Model feature `dwpc_GPGD` | pathway, mediator, both pathway edges, disease edge | 100 |
| Shared molecular function | Model feature `dwpc_GFGD`; GO term degree at most 200 | function, mediator, both function edges, disease edge | 60 |
| Shared biological process | Model feature `dwpc_GBGD`; GO term degree at most 200 | process, mediator, both process edges, disease edge | 100 |
| Drug context | Context only, not a model feature | drug, relation label, drug-target edge, drug-disease edge | 40 |

The published Explorer graph exposes drug-to-disease edges as the relationship tables `indication`
and `drug_investigated_for`. It does not expose the old `drug_disease` table used by the current
backend template. The drug query therefore binds the endpoint-constrained edge and filters with
`LABEL(r2)`. Kuzu's `OFFSET(id(r))` is the tested numeric relationship tie-breaker; `r._ID` is a
reserved name and must not be used.

```cypher
// PPI interaction
MATCH (D:disease {node_index: {disease_index}})
MATCH (g:protein {node_index: {gene_index}})
MATCH (g)-[r1:protein_protein]-(m:protein)-[a:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, D, r1, m, a
ORDER BY m.node_index, OFFSET(id(r1)), OFFSET(id(a))
LIMIT 100
```

```cypher
// Shared pathway
MATCH (D:disease {node_index: {disease_index}})
MATCH (g:protein {node_index: {gene_index}})
MATCH (g)-[r1:pathway_protein]-(x:pathway)-[r2:pathway_protein]-(m:protein)-[a:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, D, r1, x, r2, m, a
ORDER BY x.node_index, m.node_index,
         OFFSET(id(r1)), OFFSET(id(r2)), OFFSET(id(a))
LIMIT 100
```

```cypher
// Shared molecular function
MATCH (D:disease {node_index: {disease_index}})
MATCH (g:protein {node_index: {gene_index}})
MATCH (g)-[r1:molfunc_protein]-(x:molecular_function)-[r2:molfunc_protein]-(m:protein)-[a:disease_protein]-(D)
WHERE m.node_index <> g.node_index
  AND COUNT { MATCH (x)-[:molfunc_protein]-() } <= 200
RETURN g, D, r1, x, r2, m, a
ORDER BY x.node_index, m.node_index,
         OFFSET(id(r1)), OFFSET(id(r2)), OFFSET(id(a))
LIMIT 60
```

```cypher
// Shared biological process
MATCH (D:disease {node_index: {disease_index}})
MATCH (g:protein {node_index: {gene_index}})
MATCH (g)-[r1:bioprocess_protein]-(x:biological_process)-[r2:bioprocess_protein]-(m:protein)-[a:disease_protein]-(D)
WHERE m.node_index <> g.node_index
  AND COUNT { MATCH (x)-[:bioprocess_protein]-() } <= 200
RETURN g, D, r1, x, r2, m, a
ORDER BY x.node_index, m.node_index,
         OFFSET(id(r1)), OFFSET(id(r2)), OFFSET(id(a))
LIMIT 100
```

```cypher
// Drug context — additional evidence, not a model feature
MATCH (D:disease {node_index: {disease_index}})
MATCH (g:protein {node_index: {gene_index}})
MATCH (g)-[r1:drug_protein]-(x:drug)-[r2]-(D)
WHERE LABEL(r2) IN ['indication', 'drug_investigated_for']
RETURN g, D, r1, x, r2
ORDER BY x.node_index, LABEL(r2), OFFSET(id(r1)), OFFSET(id(r2))
LIMIT 40
```

The UI contract is route-level:

- zero rows means that this route found no evidence for the selected pair;
- one or more rows means that the route is present;
- fewer rows than the cap means the returned route bindings are complete under the query's filters;
- exactly the cap means **cap reached**, not automatically “truncated” and not an estimate of the
  uncapped total;
- raw query rows are reported separately from the Explorer renderer's deduplicated visible node and
  edge counts;
- feature values in the target card do not substitute for graph-route presence.

The approved card copy is:

> Choose one of five default evidence queries to run in Visual Graph Explorer. Four correspond to
> model features—PPI interaction, shared pathway, shared molecular function, and shared biological
> process. The drug query is additional context, not a model feature. Each query is independently
> ordered and capped: PPI 100, pathway 100, molecular function 60, biological process 100, and drug
> 40. The Explorer displays one query result at a time; results are not combined.

#### Wave 2 live evidence — 2026-09-02

The queries were exercised in the live Visual Graph Explorer against `enriched_index_freezed`, using
HER2-positive breast carcinoma (`node_index` 48537). The indices below are snapshot-specific test
fixtures, not durable biological identifiers.

| Case | Query | Raw rows | Repeat result | Observation |
|---|---|---:|---|---|
| HRAS (`88097`) | PPI | 80 | same row count and visible ordered rows | Under cap; duplicated PPI storage makes relationship tie-breakers necessary |
| HRAS (`88097`) | Pathway | 100 | same row count and visible ordered rows | Cap reached |
| HRAS (`88097`) | Molecular function | 16 | same row count and visible ordered rows | Under cap after degree filter |
| HRAS (`88097`) | Biological process | 100 | same row count and visible ordered rows | Cap reached after degree filter |
| HRAS (`88097`) | Drug context | 0 | stable absence | No drug route for this pair |
| TBX1 (`95790`) | PPI | 0 | stable absence | Sparse-case empty state is valid |
| ERBB2 (`84431`) | Drug context | 2 | same row count and visible ordered rows | One `indication` and one `drug_investigated_for` binding |
| RPS27A (`94544`) | Pathway | 100 | same row count and visible ordered rows | Hub-stress case reaches its route cap |
| RPS27A (`94544`) | Molecular function | 1 | same row count and visible ordered rows | Degree filter prevents a broad GO expansion |
| RPS27A (`94544`) | Biological process | 5 | same row count and visible ordered rows | Degree filter prevents a broad GO expansion |

For the HRAS reference case, the scalar forms used to inspect IDs completed in approximately
0.85–1.06 seconds in the Explorer. Graph-returning forms rendered successfully in approximately
1.6–2.4 seconds for PPI, pathway and molecular function. Renderer totals differed from raw row totals
because the Explorer deduplicates shared nodes while retaining route edges; this is expected and is
why the two measurements remain separate.

The combined `OPTIONAL MATCH` template is rejected for A4 migration: it multiplies independent route
bindings, applies one unordered global cap, and references a drug relationship table absent from the
published Explorer graph. Union, cross-shape joining, sequential execution and result accumulation
are all out of scope for Phase 3.

### Phase 3 — Act 4 migration

1. Implement the five approved query builders as pure frontend functions.
2. Wire the selected candidate and disease into the shared card.
3. Add the five-query selector, visible query text and copy action; do not auto-execute queries.
4. Replace **Show the mechanism** with **Open full Explorer** for the selected query.
5. Remove the inline `ActGraph` canvas, five-route loading state, route-result summaries and all
   frontend result-merging behavior.
6. Preserve the scientific caveats and state that the Explorer displays one result at a time.
7. Verify that selecting a candidate performs only the candidate-detail request and generates no
   graph request.
8. Do not carry the legacy backend aggregation into the new card. Its endpoint may remain temporarily
   as an unused rollback seam until the live handoff passes, then is deleted in Phase 6.

**Exit criterion:** Act 4 no longer calls `/api/graph/mechanism`, and the selected candidate's query can
be run successfully in the Explorer.

### Phase 4 — Act 1 default-query redesign gate

Act 1's default and starter queries must be redesigned and validated before its view is migrated. This
is a product and graph-semantics decision, not a mechanical consequence of adopting the shared card.

1. State the audience question each default or starter query answers.
2. Remove queries that duplicate one another or do not advance the Act 1 narrative.
3. Define the expected graph/table result and the evidence needed to recognize a correct result.
4. Validate directionality, node and relationship labels, bounds and deterministic ordering against
   the current published graph.
5. Measure the queries in the Visual Graph Explorer and confirm they remain suitable for a live demo.
6. Decide which queries belong as Visual Graph saved queries and which, if any, remain Target
   Prioritizer-provided launch presets.
7. Present the proposed query set, results and wording for explicit user validation.

**Approved Wave 4 outcome — 2026-09-02:** Act 1 provides the three deterministic launch presets
below. They remain Target Prioritizer-owned narrative data; they are not duplicated as Explorer saved
queries. The standalone TP53 PPI starter is removed as narrative duplication.

#### Wave 4 approved query set

Act 1 should use three deterministic launch presets. Each answers a different audience question and
introduces a distinct part of the assembled evidence graph without turning Act 1 into a candidate-
mechanism explanation.

| Preset | Audience question | Expected graph result | Recognition evidence |
|---|---|---|---|
| Breast cancer evidence neighbourhood | How does the graph connect a disease to associated proteins and the interactions among them? | One breast-cancer disease node, its associated proteins and interactions among those proteins | Only `disease`, `protein`, `disease_protein` and `protein_protein` appear; the live result has 1 disease, 24 proteins, 24 association edges and 40 PPI edges |
| TP53 pathway context | What curated pathway context can the graph show for a familiar protein? | TP53 and a bounded set of its pathways | Only `protein`, `pathway` and `pathway_protein` appear; the live result has 1 protein, 30 pathways and 30 edges |
| TP53 drug context | What tractability context does the graph contain for a familiar protein? | TP53 and its directly linked drugs | Only `protein`, `drug` and `drug_protein` appear; the live result has 1 protein, 5 drugs and 5 edges; this is descriptive context, not a safety or target claim |

The graph view is the intended result mode for all three presets. In table mode, one row represents
one matched path binding, so the query `LIMIT` is a row bound rather than a promise about unique
visible nodes or edges. The Explorer deduplicates repeated graph entities in its rendered totals.

```cypher
// Breast cancer evidence neighbourhood
MATCH (d:disease)<-[e1:disease_protein]-(p1:protein)
      -[e2:protein_protein]-(p2:protein)-[e3:disease_protein]->(d)
WHERE LOWER(d.node_name) = LOWER("breast cancer")
RETURN d, e1, p1, e2, p2, e3
ORDER BY p1.node_index, p2.node_index,
         OFFSET(id(e1)), OFFSET(id(e2)), OFFSET(id(e3))
LIMIT 40
```

```cypher
// TP53 pathway context
MATCH (p:protein)-[e:pathway_protein]-(w:pathway)
WHERE LOWER(p.node_name) = LOWER("TP53")
RETURN p, e, w
ORDER BY w.node_index, OFFSET(id(e))
LIMIT 30
```

```cypher
// TP53 drug context
MATCH (p:protein)-[e:drug_protein]-(dr:drug)
WHERE LOWER(p.node_name) = LOWER("TP53")
RETURN p, e, dr
ORDER BY dr.node_index, OFFSET(id(e))
LIMIT 25
```

The standalone **TP53 protein interactions** starter is removed. Its PPI layer is already visible in
the breast-cancer neighbourhood, while the adjacent Act 1 provenance card explains PPI sources more
directly. The previously rejected “everything TP53 touches” query remains excluded because a global
limit samples across relationship tables non-deterministically and duplicates the exact node- and
relationship-type summary cards.

The Target Prioritizer should own these three launch presets in source control because their names,
order and explanatory copy are part of the Act 1 story. The Visual Graph Explorer owns execution,
rendering and free exploration. The presets should not also be created as Explorer saved queries:
without a supported deep-link contract, duplication would introduce configuration drift and the
handoff still needs the exact visible/copyable Cypher in the Target Prioritizer.

The proposed Act 1 card copy is:

> Choose one of three evidence views, then open Visual Graph Explorer to run it. The presets show how
> the graph connects a disease to proteins, a familiar protein to pathways, and a familiar protein to
> drug context. Each query is ordered and bounded for a repeatable demonstration. For open-ended
> questions, use the Explorer's query generator.

##### Wave 4 live evidence — 2026-09-02

All three queries were run twice in the published Visual Graph Explorer against
`enriched_index_freezed`. Each repeat produced the same visible node- and edge-group counts listed
above, with no parser or execution error. The relationships are deliberately traversed undirected,
matching the published source/target orientations shown by the Explorer, and every relationship is
returned so the graph remains connected and renderable. Relationship offsets break ordering ties
before each row limit.

The graph canvas reached a stable rendered state in roughly 1–4.5 seconds in this browser session,
including editor interaction, UI response and graph-layout stabilization. This is a conservative
end-to-end demo measurement, not the underlying Kuzu execution time; it therefore does not conflict
with the sub-second query-engine response observed independently. No saved query, graph, dataset,
recipe or live webapp configuration was changed during validation.

**Exit criterion:** the user has approved the Act 1 default query set and its intended narrative role.
No `EvidenceView.vue` migration begins before this gate passes.

### Phase 5 — Act 1 migration

1. Replace the Act 1 graph card with the same shared card.
2. Pass its deterministic starters into the shared component.
3. Move natural-language exploration to the Explorer query generator.
4. Remove Act 1's local result canvas, graph/table toggle and local Cypher execution controls.
5. Confirm the narrative still supports a concise, reproducible starter-query demonstration.

**Exit criterion:** Acts 1 and 4 instantiate the same component and differ only through supplied
context, copy and query data.

#### Wave 5 approved and deployed — 2026-09-02

Act 1 now instantiates the same `VisualGraphExplorerCard` as Act 4 and supplies the approved three
queries from a static frontend definition. Selecting a preset changes only the visible Cypher. The
card no longer fetches graph defaults, sends Cypher or natural-language prompts, renders a local
graph/table result, or exposes local Cypher editing and re-execution. Open-ended exploration is
directed to the Explorer query generator.

The legacy graph backend remained unchanged through the Wave 5 validation and deployment as the
Phase 6 rollback seam. Repository search found no remaining frontend consumer of
`/api/graph/defaults`, `/api/graph/cypher`, `/api/graph/search` or `/api/graph/mechanism`; Act 1
continues to load its non-graph evidence cards from `/api/evidence`.

The production frontend build passes. Local UI validation confirmed exactly three starters, stable
first-starter selection, query-preview replacement on selection, shared-dialog launch, confirmed
clipboard status, selectable fallback Cypher and focus restoration on close. Local development did
not configure a DSS Explorer origin, so the shell correctly showed its configured-environment
fallback instead of creating an iframe. Frontend type checking reports only the pre-existing ECharts
option-callback diagnostics in the chart components; the Wave 5 files have no reported diagnostic.

### Phase 6 — backend and dependency cleanup

After both acts pass acceptance:

1. delete `POST /api/graph/mechanism` and its models, route templates and executor pool;
2. delete Act 1's `/api/graph/cypher` and `/api/graph/search` routes if no other consumer remains;
3. delete graph artifact shaping helpers that have no remaining caller;
4. remove the `ActGraph.vue` renderer if repository search confirms no remaining use;
5. remove `vis-network` and `vis-data` if they are then unused;
6. retain graph defaults only if the frontend still sources starter metadata from the backend;
7. update module documentation and remove stale latency explanations.

**Exit criterion:** repository search finds one Explorer card implementation, one Explorer shell and no
dead native graph execution or rendering path.

#### Wave 6 accepted — 2026-09-02

The unused native graph path has been removed. The FastAPI application no longer imports or
registers the graph router, and the deleted route module contained the complete retired surface:
starter defaults, Cypher and natural-language execution, the five-route mechanism executor, result
accumulation and graph/table shaping. The evidence payload used by Act 1 is unaffected.

The unused `ActGraph.vue` canvas renderer has also been deleted. With no remaining caller,
`vis-network` and `vis-data` and their orphaned lockfile entries have been removed. The graph colour
tokens remain available as a neutral integration palette rather than being documented as inputs to
the retired canvas renderer.

Repository search now finds exactly one shared `VisualGraphExplorerCard` implementation and one
global `VisualGraphExplorerDialog` shell, with both Acts 1 and 4 as consumers. It finds no runtime
reference to `ActGraph`, `vis-network`, `vis-data`, the graph router or any `/api/graph/*` endpoint.
The backend imports with no graph routes registered, and the production frontend build passes.
Frontend type checking continues to report only the pre-existing ECharts option-callback diagnostics
in unrelated chart components; Wave 6 adds no type diagnostic.

The user accepted this cleanup, and Wave 7 subsequently deployed it after the release gates passed.
Normal Git history remains the rollback path; no graph or dataset rollback is involved.

### Phase 7 — documentation and release verification

1. Update `WEBAPP_DESIGN.md` to make the implemented architecture canonical.
2. Update the webapp README with the integration configuration.
3. Update `DEPLOYMENT.md` with iframe, permissions and new-tab fallback checks.
4. Rebuild repository indexes without refreshing DSS recipe snapshots.
5. Run frontend type checking and production build.
6. Validate backend startup and the remaining API surface.
7. With explicit approval, deploy and verify the built bundle and live webapp logs.

**Exit criterion:** the deployed behavior, canonical design document and repository source agree.

#### Wave 7 completed — 2026-09-02

The canonical design and webapp operations documentation now describe the shared Explorer card and global
shell, the explicit copy-and-paste handoff, the Act 1 three-starter and Act 4 five-preset contracts, and
the removal of Target Prioritizer graph execution and `/api/graph/*` routes. The deployment procedure
also records the nested-frame permission and new-tab checks, plus the explicit remote-file pruning step
that is necessary because deployment uploads files but does not remove previously deployed ones.

Frontend type checking and the production build pass. Backend validation finds 17 registered paths,
including `/api/evidence`, and no `/api/graph/*` route. Repository indexes were rebuilt without a DSS
recipe refresh; governance, link and index checks pass. The final diff review found no release blocker.

The release was deployed to `DEMO_TARGET_IDENTIFICATION` webapp `OlmPX9a` with code environment
`primekg_kg`. The deployed bundle contains the Explorer navigation object and **Open full Explorer**,
with no `/api/graph/`, `ActGraph` or `vis-network` marker. The upload-only deployment left the retired
remote `backend/routes/graph.py` in place, so that exact file was deleted non-recursively and its absence
verified. The restarted backend reports `running: true`, `crashCount: 0`, and successful `GET /__ping`
responses.

Live browser verification confirmed three Act 1 starters and five Act 4 presets after selecting TP53.
Both acts open one shared dialog, keep the chosen Cypher visible, report a confirmed copy and load the
authorized Visual Graph Explorer. **Open in new tab** reached the configured
`wBcApLN_graph-search` route. This session used the authorized project owner; the representative
non-owner permissions check remains an operational rehearsal item rather than a code or deployment
failure. No graph, dataset, recipe or frozen reference was changed.

> The `wBcApLN_graph-search` slug above is the **historical record of what Wave 7 verified on
> 2026-09-02** and is correct as written. The Explorer was renamed on 2026-09-03; the current object
> ID is `wBcApLN_graph-explorer`, per §9.

## 9. Configuration contract

The implemented build-time settings are:

```text
VITE_VISUAL_GRAPH_PROJECT_KEY=DEMO_TARGET_IDENTIFICATION
VITE_VISUAL_GRAPH_WEBAPP_ID=wBcApLN
VITE_VISUAL_GRAPH_OBJECT_ID=wBcApLN_graph-explorer
VITE_DSS_ORIGIN=  # optional local-development override; production is same-origin
```

They belong in `webapp/app.env`, are exposed through `frontend/src/config.ts`, and are baked into the
single Vite bundle. They are not secrets.

The two IDs serve different DSS surfaces. The live definition, status and log APIs identify the
underlying webapp as `wBcApLN`. Browser navigation requires the object ID `wBcApLN_graph-explorer`, so
the canonical launch route is
`/projects/DEMO_TARGET_IDENTIFICATION/webapps/wBcApLN_graph-explorer/view`. Both are explicit to prevent
the navigation slug from being mistaken for the backend webapp identifier.

**The object ID is not stable across a rename.** It is the webapp ID plus the current name slug, so
renaming the Explorer in DSS invalidates it while the webapp ID stays put. On 2026-09-03 the webapp was
renamed from *graph search* to **Graph Explorer**, moving the object ID from `wBcApLN_graph-search` to
`wBcApLN_graph-explorer`. Since the value is baked into the Vite bundle at build time, the Act 1 and
Act 4 cards continue to launch the stale slug until the frontend is rebuilt and redeployed. Treat any
future Explorer rename as a required rebuild, not a configuration-only change.

The graph snapshot ID must not be part of this contract. The Explorer remains responsible for listing
the currently published graphs and their freshness.

## 10. Acceptance criteria

The migration is complete only when all of the following are true:

### Architecture

- Acts 1 and 4 use the same shared Explorer card component.
- One global Explorer shell serves both acts.
- No act embeds the Explorer's three-panel interface inside a half-width dashboard card.
- No Target Prioritizer code calls a private Visual Graph plug-in endpoint.
- No code reaches into the Explorer iframe DOM.
- No graph query executes on act load or candidate selection.

### Act 1

- Starter queries remain deterministic and visible.
- A starter can be copied and run in the Explorer.
- Natural-language exploration is available through the Explorer query generator.
- The Act 1 narrative no longer depends on a local graph renderer.

### Act 4

- Selecting a row still updates the existing target-detail card.
- The shared graph card follows the same selected disease and gene.
- The generated query contains the correct numeric node indices.
- Clipboard success and failure are both handled honestly.
- No request reaches `/api/graph/mechanism`.
- No route-presence or edge-count claim is displayed before query execution.
- The drug-route caveat remains visible.

### Explorer shell

- It loads inside DSS for an authorized user.
- Loading, retry, close, Escape and focus restoration work.
- `Open in new tab` works as a fallback.
- Closing and reopening does not leave an unusable overlay or duplicate iframe.
- An access-denied response gives actionable guidance rather than a blank panel.

### Correctness and performance

- The approved A4 query or preset set is tested on connected, sparse, drug-linked and GO-hub
  candidates.
- The reference case preserves the required route families and key biological connections.
- Explorer execution remains materially faster than the current five-tool-call path.
- Performance is measured separately for iframe cold start and warm query execution.
- A fast but route-biased `LIMIT` result does not pass semantic acceptance.

### Repository and operations

- `npm run typecheck` passes.
- `npm run build` passes with the existing single-bundle contract.
- The backend starts with the reduced route set.
- Repository search finds no stale `/api/graph/mechanism` consumer.
- `vis-network` and `vis-data` are removed if unused.
- No graph, dataset, recipe, model or frozen reference is modified.
- Deployment, commit and push occur only after their separate approvals.

## 11. Risks and mitigations

| risk | mitigation |
|---|---|
| DSS prevents a nested webapp iframe through security headers | Make new-tab launch a first-class fallback and keep the launcher contract independent of presentation mode. |
| Clipboard access is blocked inside the parent iframe | Keep the query visible and selectable; report copy success only after confirmation. |
| The Explorer does not accept a query through a supported deep link | Use explicit copy-and-paste handoff; do not use private APIs or DOM manipulation. |
| The combined query is fast but its shared limit biases route coverage | Keep A4 behind its query-design gate; prefer independently bounded route presets and use illustrative wording for any globally limited combined result. |
| Explorer backend cold start obscures the query-speed improvement | Measure first paint separately from warm query time and rehearse the same operational state used for the demo. |
| A user can access Target Prioritizer but not Explorer | Test with a representative non-owner and show a clear permissions error plus new-tab option. |
| Plug-in upgrade changes view routing | Centralize URL construction and cover it with a live smoke test after plug-in upgrades. |
| Removing Act 1's inline canvas weakens presentation pacing | Validate the Act 1 talk track before cleanup; retain concise starter controls in the shared card. |
| Old scientific claims survive after route summaries are removed | Remove route-presence and edge-count copy with the backend and update `WEBAPP_DESIGN.md` in the same implementation. |

## 12. Rollout and rollback

The migration should be reviewed in separable changes:

1. shared configuration, launcher state and Explorer shell;
2. Act 4 query/preset redesign and explicit validation;
3. Act 4 cutover with the legacy route still available for comparison;
4. Act 1 default-query redesign and explicit validation;
5. Act 1 cutover to the same shared card;
6. removal of legacy endpoints, renderer and dependencies;
7. canonical documentation update and approved deployment.

The rollback boundary is the frontend cutover. Until Phase 6 cleanup, the legacy APIs remain available
for comparison. After cleanup, normal Git history is the rollback mechanism; no DSS data rollback is
needed because this migration changes neither graph data nor its publication.

## 13. Deferred enhancement

Automatic query loading and execution in the Explorer is deferred until Visual Graph provides a
supported integration contract, preferably either:

- a documented URL containing graph and query state; or
- a strict-origin `postMessage` API accepting graph ID, query text and an explicit execution choice.

If that capability becomes available, it should be implemented inside the shared shell without
changing either act. It must not be approximated through a private plug-in endpoint or iframe DOM
automation.
