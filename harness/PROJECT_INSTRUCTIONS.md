# demo-target-identification

Two linked Dataiku DSS proof-of-concepts: Part 1 is a biomedical knowledge graph and Part 2 is an
explainable target-gene prioritizer. Read `docs/overview/PROJECT_CONTEXT.md` only when the shared
object contract matters; use `docs/README.md` to route a documentation task.

## Route before reading

Classify the request, then load only its authority:

- Facts about models, metrics, recipes, features, seed gates, past decisions, or documented numbers:
  invoke the `target-id` skill first and query `.index/`; do not load large project documents by
  default. Use bounded searches, not whole TSV files.
- Webapp work: follow the nested `webapp/AGENTS.md` or `webapp/CLAUDE.md` overlay and its task route.
- DSS build, deployment, or configuration work: inspect live state with `dku` before relying on the
  repository; load the relevant task procedure before acting.
- Documentation changes: preserve each document's stated authority and update trigger. Regenerate
  indexes after an approved relevant change; use `--refresh` only when a DSS recipe changed in the UI.

## Non-negotiable boundaries

- Never commit or push without the user's explicit approval after a change summary.
- `KNOWLEDGE_GRAPH_PRIMEKG` is frozen: do not modify or rebuild it. Never recompute `compute_kg` or
  the graph unless explicitly asked.
- `DECISIONS.md` is append-only; corrections are new entries. Never commit `data/`.
- New DSS datasets use `dataiku-managed-storage` / Parquet. Use visual Join recipes rather than
  pandas `.merge()` for joins.
- Do not run a DSS build, deployment, or live scenario as a side effect of inspection or code work.
  Confirm the target project and obtain the required user approval first.

## Truth and measurement

- Notebooks compute documented numbers. A claim without its notebook assertion can drift; re-derive
  a headline before presenting it.
- Report macro per-disease AUC, never pooled AUC. Report ties before means and prefer a stratified
  paired test to a small macro-average difference.
- A drug-target lookup benchmark can measure gene popularity rather than model quality; report it as
  a warning, not an optimization target.
- Repository docs and `dss_recipes/` can lag DSS. Confirm live state with `dku` when it affects the
  answer or change.

## Project map

`DEMO_KG_LS` owns the graph and graph webapp; `DEMO_TARGET_IDENTIFICATION` owns features, modeling,
validation, and serving. Part 2 consumes shared graph objects from Part 1. Task-specific documents
own detailed methods, platform behavior, and current status; indexes are the default retrieval path.
