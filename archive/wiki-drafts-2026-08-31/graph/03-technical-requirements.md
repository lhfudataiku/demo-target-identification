<div class="alert">
This is a demo-only project. Confirm the target DSS instance, access controls, plug-in availability,
and code environment before attempting a deployment or graph rebuild.
</div>

# Version

`DEMO_KG_LS` was inspected on a Dataiku DSS 15.0.0 Design node on 2026-08-31. This records the
current POC environment; it is not a formal minimum-version or production-support statement.

## Connections and Storage

The graph pipeline retrieves its public biomedical sources over HTTP(S). New managed datasets use
S3-backed Parquet storage so the flow can use the distributed engine. The assembled graph is
materialized as a Kuzu database in a managed folder.

Before rebuilding from source, confirm that the target environment provides:

- outbound HTTPS access to the documented public source endpoints
- managed S3/Parquet storage for graph outputs and the Kuzu folder
- access to the Menche interactome upload and the disease-grouping snapshot, both of which are
  required local project inputs

Several upstream sources resolve to current releases rather than immutable artifacts. A
reproducible release needs deliberate source snapshots, especially for the continuously rewritten
gene-to-Ensembl mapping.

## Code Environment

The project uses Python recipes for source retrieval, parsing, graph assembly, and Kuzu
materialization. It also uses Dataiku visual recipes for the harmonization, join, stack, window,
sampling, and distinct steps.

This repository does not declare a portable code-environment manifest for the graph project.
Before copying or deploying the POC, verify the required Python libraries and the Kuzu runtime in
the target DSS environment rather than assuming the source-project environment is available.

## Plug-ins and Webapp

The POC uses the Visual Graph plug-in to materialize and interactively explore the graph. The
current Kuzu folder is `published_kg_ls-Mp25kL`, with `enriched_index_freezed-6bRVGs` retained as the
snapshot the published feature numbers were derived from; the explorer webapp reads the assembled
graph tables and runs as a local process rather than in a container.

Verify that the Visual Graph plug-in and its graph runtime are installed and supported in the
target instance before deployment. The current project has graph-explorer support datasets such as
`graph`, `graph_nodes`, `graph_edges`, `saved_graph`, `query_hx`, and `vg_*`.

## Project Integration

`DEMO_TARGET_IDENTIFICATION` consumes a defined graph contract: 12 datasets through local
synchronized copies and the Kuzu folder directly. Do not substitute similarly named datasets or
rely on positional columns. The graph project uses 1-based deterministic node indices, and the
shared-object contract defines the supported integration surface.

`KNOWLEDGE_GRAPH_PRIMEKG` is a frozen comparison reference and must not be rebuilt.
