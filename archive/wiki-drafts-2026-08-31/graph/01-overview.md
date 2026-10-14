<span id="version" style="color: grey; float: right">Version 1.0.0 draft</span><br/>

<div class="alert">
This is a demonstration project. It is not a clinical decision-support system and is not a
production-ready biomedical knowledge base.
</div>

# Knowledge Graph for Life Sciences Ontology

An interactive biomedical knowledge-graph experience for drug-discovery target identification.
`DEMO_KG_LS` is Part 1 of a two-project life-sciences proof of concept. It rebuilds a
PrimeKG-like graph from auditable public sources, materializes it for exploration with the Visual
Graph plug-in, and supplies a governed graph foundation to `DEMO_TARGET_IDENTIFICATION` for
explainable target prioritization.

## Industry Challenge

Drug discovery is a long, high-risk process: a therapeutic hypothesis must be supported across
fragmented genetics, disease biology, pathways, phenotypes, and drug-mechanism evidence before
significant capital is committed. The challenge is not merely collecting more data. Teams need to
connect evidence held in separate vocabularies and systems, investigate the biological context of a
candidate, and retain enough provenance to challenge each assertion.

Knowledge graphs address this data-silo problem by representing biomedical entities and their
relationships as a navigable network. They make it possible to trace multi-hop context, compare
evidence across sources, and carry a hypothesis from disease biology to a potential target without
reducing the evidence to a single opaque score.

## Golden Demo Highlights

The Knowledge Graph for Life Sciences Ontology demonstrates:

- a PrimeKG-conformant biomedical graph built from public, auditable sources in a governed Dataiku
  flow
- a hybrid engineering pattern: Python recipes retrieve and parse source-native data; visual
  recipes harmonize and ground it, making important data-quality controls inspectable
- an interactive Visual Graph experience for exploring entities, relationships, and graph context,
  including AI-assisted graph queries
- a reusable graph foundation for explainable target ranking in the downstream project

The reconstructed graph contains 113,391 nodes and 2,851,510 undirected edges across 8 node types
and 18 relation types. It has been structurally accepted against the frozen reference graph.

## Who This Demo Is For

The demo is primarily framed for early drug-discovery teams who need to understand and interrogate
biological evidence before investing in a target hypothesis. Two representative users are:

- a computational biologist investigating diabetes-related biological networks and potential
  intervention points across insulin signalling, inflammation, and metabolic regulation
- an oncology data scientist investigating signalling hubs in breast-cancer progression, including
  tumour biology and immune-response context

It also supports discussions with R&D data leaders, translational-science teams, and platform
owners who need a governed way to integrate biomedical evidence for discovery decisions.

## Demo Value Proposition

The project helps a discovery organization:

- integrate heterogeneous public biomedical evidence into one queryable and traceable graph
- explore disease-to-gene, gene-to-pathway, phenotype, and drug-mechanism relationships in context
- retain source-aware evidence rather than relying on disconnected tables or an unexplained score
- establish a reusable foundation for target identification and downstream prioritization
- demonstrate Dataiku as the platform for graph construction, lineage, exploration, and governed
  hand-off to modelling workflows

## What the Project Does

Within the current POC scope, the system:

- integrates HGNC, MONDO, Open Targets, Menche/HuRI/STRING, Reactome, Gene Ontology, NCBI gene
  annotations, and HPO onto a common identifier system
- builds graph nodes and relationships for disease, gene/protein, phenotype, drug, pathway, and
  Gene Ontology evidence
- keeps approved and investigational drug-disease evidence as separate relations
- materializes the assembled graph as a Kuzu database and exposes it through the Visual Graph
  experience
- shares the supported graph objects with `DEMO_TARGET_IDENTIFICATION`, which computes features,
  validates models, and ranks candidate targets

The project does not make clinical or therapeutic decisions. It is an evidence-integration and
exploration layer; the downstream ranking model remains a separate, validated component.

## Why Dataiku Matters In This Demo

Dataiku provides the governed platform layer for turning heterogeneous biomedical source material
into an inspectable, reusable graph asset. The flow makes extraction, harmonization, joins,
provenance, and quality controls visible. The Visual Graph plug-in makes the graph available for
interactive exploration and AI-assisted graph queries rather than leaving it as a static export.

Dataiku also preserves a deliberate operational boundary: `DEMO_KG_LS` can maintain a stable graph
on a slower refresh cadence while `DEMO_TARGET_IDENTIFICATION` iterates on features and models.
Their explicit shared-object contract makes this hand-off auditable and reusable across discovery
workflows.

## How to Use

Use the Visual Graph experience to begin with a disease, gene, pathway, phenotype, or drug entity
and explore the connected biological evidence. Use the DSS flow when the question is about the
provenance or transformation of an entity or relation. For a target-ranking discussion, continue
to the separate target-identification experience, where graph-derived features and evidence paths
are presented alongside candidate targets.
