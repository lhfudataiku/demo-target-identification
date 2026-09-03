# Demo Instructions

> **Lifecycle:** Draft · **Audience:** data scientists preparing a technical demonstration ·
> **Authority:** a preparation guide derived from the `Walkthrough` article; it does not replace the
> canonical graph-build method · **Update when:** the graph editor, explorer, graph snapshot, or
> project boundary changes.

This is a five-minute preparation read for demonstrating `DEMO_KG_LS`. It follows the progression
of the `Walkthrough` talk track: frame the evidence problem, show how the graph is built, explore a
scientific question, and close with the hand-off to target prioritization.

The purpose of the demonstration is to show an inspectable, reusable biomedical evidence graph. It
is **not** a target-ranking demonstration, and a connection in the graph is not a validation of a
therapeutic target.

## Before the demonstration

- Open `DEMO_KG_LS`, with the Flow, **Life Sciences Graph Editor**, and **Life Sciences Graph
  Explorer** ready. The editor and explorer serve distinct parts of the story.
- Pick one question and stay with it. Good prepared routes are diabetes mellitus (insulin
  signalling, inflammation, and metabolic regulation) or breast cancer (PI3K/AKT/mTOR, ESR1, and
  drug context).
- Confirm that the current published graph snapshot is available. Do not run recipes or rebuild the
  graph during a demonstration.
- Rehearse a compact evidence path: disease → gene/protein or phenotype → pathway or interaction →
  drug mechanism or indication, where available.

The most effective demonstration has one coherent biological thread. Avoid trying to enumerate all
sources, relations, or graph features.

## 1. Frame the problem

Start with the working reality of target discovery: relevant evidence is spread across genetics,
disease ontologies, phenotypes, functional biology, pathways, protein interactions, and drug data.
Those sources have different identifiers and schemas. Repeated, ad hoc reconciliation obscures
provenance and makes an evidence trail hard to reproduce or reuse.

Position `DEMO_KG_LS` as the evidence-exploration layer. It builds a governed biomedical knowledge
graph whose links can be inspected by scientists and whose outputs can be reused in analysis. The
project makes it possible to ask, “What evidence exists around this disease and its biology?”

## 2. Show the biological-domain Flow

Use the Flow to orient the audience around biological domains rather than individual recipes:

- gene and interactome;
- disease and phenotypes;
- function and pathways;
- drugs and gene–disease evidence; and
- graph build.

Explain the implementation pattern once: Python recipes retrieve and parse source-specific
material; visual recipes harmonize identifiers and shape canonical edge tables. This keeps the
grounding and table transformations most susceptible to silent data loss visible for review.

The Flow is the provenance view. It lets a data scientist trace how heterogeneous source data
becomes graph nodes and typed relationships before it is materialized for use.

## 3. Use the Graph Editor to show iterative construction

Open the **Life Sciences Graph Editor** after showing the Flow. Its role is to make graph
construction iterative and interactive: a practitioner can configure the graph from the assembled
node and edge tables, inspect and adjust the graph definition, then create a new snapshot as the
graph evolves.

Emphasize the practical benefit. Graph work need not end in a static export or require a separate
graph-engineering cycle for every change. The editor provides a controlled loop: adjust the graph
definition, materialize a snapshot, inspect the result, and refine it when the scientific or data
question changes.

Connect this loop back to the platform. A published snapshot is available in the DSS Flow, where it
can be navigated as a governed project asset and used as an input to downstream analysis. This is
the transition from graph construction to reusable analytics: the snapshot is not only a visual
artifact; it is a materialized graph asset that can support subsequent exploration and modelling.

Do not make the editor a long configuration tour. Show the iterative capability and the outcome—a
published snapshot—then move to the scientist-facing experience.

## 4. Use the Graph Explorer to answer a disease-centred question

Open the **Life Sciences Graph Explorer** and state the question aloud. For example: “What evidence
connects breast-cancer biology to PI3K/AKT/mTOR signalling, relevant phenotypes, and existing drug
context?”

Start from the disease and navigate deliberately:

1. Inspect connected genes or proteins.
2. Follow one or two meaningful links into pathways or protein interactions.
3. Add phenotype evidence where it clarifies the disease context.
4. Inspect drug-mechanism or indication evidence when it is available, including its source context.

The explorer is the efficient graph-browser phase: it lets users navigate by node and relation and
group the visible network by entity type or source. It can also be powered by an LLM for
natural-language graph queries, giving a scientist an alternative to manually formulating every
navigation step. Treat LLM-assisted results as a way to explore and interrogate the graph; verify
the resulting evidence and provenance in the graph before drawing a conclusion.

Narrate each hop as supporting context, not a recommendation. A connected gene is a lead for
investigation, not automatically a validated target. If a relationship is absent, describe that as a
coverage limitation rather than a negative scientific conclusion.

## 5. Close with the project boundary

End by distinguishing evidence exploration from candidate prioritization. `DEMO_KG_LS` answers,
“What evidence exists around this disease and its biology?” When the question becomes, “Which
candidate targets should we investigate first?”, move to `DEMO_TARGET_IDENTIFICATION`.

The downstream project uses the shared graph and synchronized evidence to create disease–gene
features, validate an XGBoost model, rank candidate targets, and present explainable supporting
evidence. In short: the editor enables iterative graph creation; the explorer makes the resulting
snapshot useful to scientists; the downstream project prioritizes candidates using that reusable
foundation.
