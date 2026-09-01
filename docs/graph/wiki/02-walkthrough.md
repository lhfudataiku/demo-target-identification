# Case Study

Drug-discovery teams need to make early target hypotheses from evidence that is distributed across
genetics, disease ontologies, functional biology, phenotypes, pathways, protein interactions, and
drug data. In a conventional workflow, analysts reconcile those sources repeatedly, often across
incompatible identifiers and disconnected tables, before a scientist can assess whether a
candidate has coherent biological support.

## Project Background

This POC demonstrates how Dataiku can recreate a biomedical knowledge-graph pipeline for target
identification and make the resulting graph useful to a scientific user. `DEMO_KG_LS` is the graph
construction and exploration project; `DEMO_TARGET_IDENTIFICATION` is the separate downstream
project that derives features and produces explainable target rankings.

The purpose is not to claim a novel target-identification algorithm. It is to demonstrate
reproducibility, lineage, exploration, and explainability around an industry-standard approach to
integrating biomedical evidence.

## Initial Situation

Biomedical evidence needed for target discovery is fragmented by source, data model, and
identifier system. A disease may be represented differently in an ontology, a genetics resource,
and a clinical evidence source; gene and drug references need similar reconciliation. Without a
common graph foundation, it is difficult to inspect how evidence connects, assess provenance, or
reuse the integration work in a downstream modelling workflow.

**Goals:**

- build a governed, source-auditable biomedical graph from publicly available data
- let scientists explore connected disease, gene, pathway, phenotype, and drug evidence
- preserve important distinctions in source evidence and provenance
- provide a stable, reusable graph contract for explainable target prioritization

## Knowledge-Graph Flow

The project is organized as a biological-evidence flow rather than a generic ETL pipeline:

- **Gene & interactome:** HGNC vocabulary and Menche, HuRI, and STRING protein interactions
- **Disease & phenotypes:** MONDO disease backbone, cross-references, and HPO evidence
- **Function & pathways:** Gene Ontology and Reactome
- **Drugs & gene-disease:** Open Targets association, mechanism, and clinical-indication evidence
- **Graph build:** assembly, deterministic node indexing, Kuzu materialization, and graph-explorer
  support

Each source follows a consistent pattern: a Python recipe retrieves and parses it into
source-native identifiers; visual recipes harmonize, ground, and shape the data into canonical edge
tables; the graph-build flow assembles the final nodes, edges, and provenance surface.

This division is intentional. The source-specific work remains in code, while the identifier
grounding and table transformations most susceptible to silent data loss remain inspectable in the
Dataiku flow.

## Exploring the Graph

The final graph is materialized in Kuzu and opened through the Visual Graph plug-in. The explorer
supports interactive navigation by node and relation, grouping by entity type and source, and
AI-assisted graph queries. It is the scientist-facing entry point for turning a question about a
disease or target into a visible network of supporting context.

For example, a user can begin with a disease term, inspect connected genes and phenotypes, follow
links into pathways or protein interactions, and then examine drug-mechanism or indication evidence
where it exists. The graph helps users interrogate evidence; it does not imply that every connected
node is a validated therapeutic target.

## User Journey

### Computational biologist: diabetes

The user begins with diabetes mellitus and asks how insulin signalling, inflammatory mechanisms,
and metabolic regulation connect to potential intervention points. They explore diabetes-related
disease, gene/protein, pathway, phenotype, and drug context to understand the biological network
before making a target hypothesis—not to receive an automated recommendation.

### Oncology data scientist: breast cancer

The user begins with breast-cancer biology and investigates signalling hubs relevant to tumour
progression and immune response. They explore the PI3K/AKT/mTOR axis—PIK3CA, AKT1, MTOR, and
PTEN—and hormone-signalling context including ESR1. The graph provides a way to trace evidence
across the related diseases, genes, pathways, and existing drug relationships.

### From graph exploration to target prioritization

When the scientific question becomes *which candidate warrants further investment*, the user moves
to `DEMO_TARGET_IDENTIFICATION`. The Kuzu graph is the primary shared graph deliverable, and a
defined set of synchronized datasets supplies the rest of the integration surface. The downstream
project performs its own feature construction, leakage-controlled validation, ranking, and evidence
presentation.

## Suggested Demo Talk Track

1. Start with the data-silo problem in target discovery and the need to preserve scientific
   provenance.
2. Show the biological-domain flow, emphasizing the visible hand-off from extraction to
   harmonization.
3. Open the Visual Graph experience and trace a disease-centred question into connected genes,
   pathways, phenotypes, and drug evidence.
4. Use one of the two persona journeys to keep the graph exploration anchored in a real scientific
   question.
5. Finish by explaining the boundary between evidence exploration in `DEMO_KG_LS` and explainable
   candidate ranking in `DEMO_TARGET_IDENTIFICATION`.
