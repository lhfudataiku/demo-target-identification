# ADR-001 — Separate graph and prioritizer projects

> **Lifecycle:** Decision · **Status:** Accepted · **Date:** 2026-08-17 · **Owner:** architecture ·
> **Update when:** the shared-object contract or project ownership changes.

## Context

Graph construction and target prioritization originally shared a project. A recursive model-side
build could therefore walk into graph construction, while trained models and validation artifacts
needed a stable graph interface.

## Decision

`DEMO_KG_LS` owns graph sources, construction and graph presentation. `DEMO_TARGET_IDENTIFICATION`
owns feature engineering, modeling, validation and serving, consuming the graph only through the
shared-object contract in [`PROJECT_CONTEXT.md` §4.3](../../overview/PROJECT_CONTEXT.md).
Non-graph sources used only for modeling remain in Part 2. `KNOWLEDGE_GRAPH_PRIMEKG` stays frozen.

## Alternatives rejected

- A single project: unsafe recursive-build reach and unclear ownership.
- Rebuilding a private graph in Part 2: duplicates accepted graph state and weakens comparability.
- Synchronizing the Kuzu folder: incompatible with its direct-read operating constraint.

## Consequences

The interface is explicit and graph recomputation is outside ordinary Part 2 work. Contract changes
require cross-project review; live state must be checked before relying on repository mirrors.
