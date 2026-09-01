<div class="alert">
This is a demo-only release. It is not a statement of general availability or production support.
</div>

# Release Notes

## Version 1.0.0 — Knowledge graph reconstruction

This release marks the completed reconstruction of the Part 1 biomedical knowledge graph in
`DEMO_KG_LS`.

### New feature: Governed PrimeKG-like graph pipeline

The project rebuilds a PrimeKG-conformant graph from public biomedical sources in a governed
Dataiku flow. It integrates disease, gene/protein, phenotype, pathway, functional-annotation, and
drug evidence, resulting in 113,391 nodes and 2,851,510 undirected edges across 8 node types and
18 relation types.

The pipeline uses a deliberate hybrid pattern: Python recipes retrieve and parse source-native
data, while visual recipes harmonize and ground it. This makes key identifier and data-quality
controls visible in the flow.

### New feature: Knowledg Graph Plug-in for interactive graph construction and exploration

The assembled graph is materialized in Kuzu and made available through the Visual Graph experience
for interactive exploration and AI-assisted graph queries. Scientists can investigate connected
disease, gene, phenotype, pathway, and drug context rather than working from disconnected source
tables.

