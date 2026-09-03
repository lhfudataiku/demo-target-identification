# Demo Instructions — Knowledge Graph for Life Sciences Ontology

## Purpose

Use this guide to prepare a short technical demonstration of `DEMO_KG_LS` for data scientists. The
goal is not to explain every recipe or to claim that the graph makes a therapeutic decision. Show
how Dataiku turns fragmented public biomedical evidence into an inspectable graph foundation for
target discovery.

Aim for four minutes, with one minute available for questions. Choose **one** persona before the
demo:

- **Diabetes:** investigate biological context around insulin signalling, inflammation, and
  metabolic regulation.
- **Breast cancer:** investigate the PI3K/AKT/mTOR axis and hormone-signalling context.

## The message to land

> We have taken disparate biomedical evidence, reconciled it into a governed graph with visible
> provenance, and made it available for scientific exploration and downstream target
> prioritization.

The graph is evidence infrastructure. It helps a scientist formulate and challenge a hypothesis;
it does not validate a target, establish causality, or recommend a therapy.

## Before the demo

Prepare these screens in advance:

1. The DSS flow, positioned so the biological-domain zones are visible.
2. The Visual Graph experience, ready to search for the selected disease or a relevant gene.
3. Optionally, the Part 2 target-prioritization project or webapp to show the hand-off from graph
   evidence to explainable candidate ranking.

Check that you are using the current deterministic-index graph snapshot. Do not rebuild the graph,
run a scenario, or modify the frozen `KNOWLEDGE_GRAPH_PRIMEKG` reference as part of a demo.

## Four-minute run of show

### 0:00–0:35 — Frame the problem

Start with a scientist’s question, not an implementation diagram: *“For this disease, how do we
bring together genetics, pathways, phenotypes, protein interactions, and drug evidence without
losing where each claim came from?”*

Explain that no one source answers this question. The graph provides the connective tissue and
preserves relationships so the evidence can be explored in context.

### 0:35–1:20 — Show the governed flow

Open the flow and point to the biological-domain zones:

- Gene & interactome
- Disease & phenotypes
- Function & pathways
- Drugs & gene-disease
- Graph build

Use one source-to-graph example. MONDO provides the disease coordinate system and cross-reference
hub; Open Targets contributes gene-disease and drug evidence; the graph build zone assembles the
final node and edge surfaces. Emphasize the design choice: source-specific extraction occurs in
Python, while harmonization and grounding are visible in Dataiku visual recipes because these are
the stages where identifier mismatches can silently lose evidence.

### 1:20–2:50 — Explore a scientific question

Open the Visual Graph experience. Search for the chosen disease, then expand a small, purposeful
set of connected entities. Narrate the relationship types rather than treating graph proximity as
proof:

- for diabetes, connect disease context to genes, pathways, phenotypes, and any relevant drug
  evidence;
- for breast cancer, connect the disease to PI3K/AKT/mTOR or hormone-signalling context, then
  inspect related gene and pathway relationships.

Point out that node labels and edge types are not anonymous graph primitives. A node has a
source-native identifier, type, name, and source; edge provenance is retained in a dedicated
metadata surface. This is why a scientist can ask where a relationship came from rather than
accepting a black-box connection.

### 2:50–3:35 — Explain the hand-off

Show or describe the boundary with `DEMO_TARGET_IDENTIFICATION`. Part 1 owns graph construction and
exploration. Part 2 consumes the defined shared objects, calculates graph-derived features, and
ranks disease × gene candidates with explanations. Keeping the projects separate lets modelling
iterate without changing the graph foundation.

Be precise: the graph is not the ranking model, and the graph explorer is not a clinical tool.

### 3:35–4:00 — Close honestly

Close with the value and the limitation:

> “This gives scientists a governed, inspectable evidence map and a reusable foundation for target
> prioritization. It identifies questions worth investigating; experimental and domain review still
> decide what is true and what advances.”

## Technical questions to be ready for

- **How is identity controlled?** The node identity is the tuple of identifier, type, name, and
  source; the graph index is deterministic and 1-based.
- **Why not use the assembled graph for hierarchies?** It is undirected. Consumers that need
  parent-to-child direction use the retained raw hierarchy tables.
- **How is drug evidence represented?** Approved indication and investigational evidence are
  distinct relations; they must not be collapsed.
- **How reproducible is the graph?** The structure is accepted against the frozen reference, but
  several public sources resolve to live releases. A release that must reproduce byte-for-byte
  needs deliberate source snapshots.

## Avoid these claims

- “The graph discovered a drug target.”
- “A connection proves a biological mechanism or causal relationship.”
- “Investigational evidence means the drug is approved.”
- “The graph replaces experimental validation or scientific review.”
