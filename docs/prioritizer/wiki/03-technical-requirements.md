<div class="alert">
This is a demo-only project. Confirm the target DSS instance, access controls, shared-object
permissions, code environments, and webapp dependencies before any deployment or rebuild.
</div>

# Version

`DEMO_TARGET_IDENTIFICATION` was inspected on a Dataiku DSS 15.0.0 Design node on 2026-09-03. The
live project currently contains 92 datasets, 90 recipes, one managed folder, and four inactive
scenarios. This is an observed POC state, not a formal production-support statement.

## Connections and Shared Objects

The project depends on the Part 1 graph through an explicit shared-object contract. It consumes
12 graph datasets through local synchronized copies and reads the Kuzu graph folder directly for
Cypher-based feature recipes. The graph project owns construction and provenance; this project owns
features, modelling, validation, scoring, and serving.

Before deploying or rebuilding, confirm:

- read access to the shared graph datasets and current Kuzu folder from `DEMO_KG_LS`
- managed storage for locally synchronized datasets, modelling tables, and serving outputs
- the S3-backed Parquet storage used for new managed datasets
- that node indices and dataset columns are consumed by name rather than positional assumptions

## Code Environment and Modelling

The current model is a DSS prediction model using XGBoost and SHAP, with the adopted 14-feature
champion `m7-f14`. Feature computation spans Cypher, Python, and visual DSS recipes; use the
project’s approved code environments and plugin configuration rather than substituting an
unreviewed runtime.

The local companion webapp uses Python 3.11 or later. Its backend dependencies include FastAPI,
Uvicorn, Server-Sent Events support, pandas, and the Dataiku API client. Its Vue frontend uses
Node.js, Vite, Vue, Pinia, ECharts, and Tailwind. Confirm the actual target DSS code environment
and deployment configuration before treating these local-development dependencies as a portable
installation manifest.

## Webapp and Serving

The serving experience is a Vue single-page application with a FastAPI backend deployed as a DSS
webapp. It exposes candidate, calibration, evidence, therapeutic-area, and graph hand-off views.
The graph explorer remains a shared hand-off to Part 1 rather than a second graph product in this
project.

## Operating Constraints

- Do not run builds or scenarios merely to inspect the project.
- Do not recompute or modify the frozen `KNOWLEDGE_GRAPH_PRIMEKG` reference.
- Use the supported shared-object contract; do not introduce direct dependencies on unrelated
  Part 1 outputs.
- Preserve candidate-eligibility, family-split, and seed-gate controls when changing the flow.
- A population-widening experiment is pre-registered and must run only in a duplicated Part 2
  project under its stated adopt/reject rule.
