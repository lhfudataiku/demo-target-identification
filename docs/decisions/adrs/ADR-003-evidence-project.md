# ADR-003 — Supporting evidence lives in its own project

> **Lifecycle:** Decision · **Status:** Proposed — becomes Accepted when the user approves the M0
> diff of [`FLOW_MIGRATION_WORKPLAN.md`](../../operations/FLOW_MIGRATION_WORKPLAN.md) · **Date:**
> 2026-10-28 · **Owner:** architecture · **Update when:** the evidence project's ownership, its
> inputs from the main project, or the way the notebooks run changes. Extends
> [ADR-001](ADR-001-project-boundary.md) from two projects to three.

## Context

The notebooks under `notebooks/` assert the project's documented numbers. They read 15 computed
datasets after zone 31 of `DEMO_TARGET_IDENTIFICATION`, eight of which the webapp also reads. A change
made for the demo can therefore move a documented number, and a change made for the evidence can
move the demo.

The `validate_notebooks` scenario that ran them in DSS has had no steps since 2026-10-05, and is
being dropped. The notebooks stay in the repository as the evidence for model development.

## Decision

- **A third DSS project, `DEMO_TI_EVIDENCE`** ("Target Identification — Supporting Evidence"), owns
  the supporting evidence for model development:
  - the notebook-only recipes, moved from `DEMO_TARGET_IDENTIFICATION`: `compute_known_drug_truth`,
    `compute_pool_reachability`, `compute_filter_three_axes` and `compute_breast_panel`;
  - copies of the recipes behind every other dataset the notebooks read;
  - a slim shortlist ranked from `scored_champion`.
- **It reads `DEMO_TARGET_IDENTIFICATION` only through objects exposed from zones 00–31**, and uses
  them as recipe inputs directly, without sync copies. It never reads a serving zone, and nothing in
  `DEMO_TARGET_IDENTIFICATION` or `DEMO_KG_LS` reads it.
- **No build crosses the boundary.** A build in either project never targets the other's datasets.
- **The notebooks run locally from the repository** with the dataiku client.
  - The evidence project is the default project for those runs.
  - Reads of zones 00–31 name `DEMO_TARGET_IDENTIFICATION` explicitly.
  - No copy of the notebooks lives in a DSS project library.
- **Evidence datasets keep the names of their main-project counterparts.** That includes
  `dashboard_candidates`, so a notebook's downstream reads keep their bare names.
- **`DEMO_TARGET_IDENTIFICATION` keeps** the imports, features, split, model and the webapp's
  serving flow. `DEMO_KG_LS` and the frozen `KNOWLEDGE_GRAPH_PRIMEKG` are unchanged.

## Alternatives rejected

- **Leaving the notebooks reading the main project's computed datasets.** It is reasonable for model
  evidence, but it keeps a computed dataset consumed by both the notebooks and the webapp, which the
  boundary rule in `DEC-DEMO-005` forbids, and it leaves notebook-only recipes in the serving project.
- **Dropping the evidence datasets with the scenario.** Future development and validation need them.
- **Sync copies of the main project's objects in the evidence project**, as Part 2 keeps of Part 1's.
  They freeze a snapshot at about 1.15 GB for the five largest objects, and they lag the model they
  are meant to check. They remain an option if a validation needs a frozen snapshot.
- **Running the notebooks in DSS** from a library copy. That keeps a second copy of each script to
  synchronise, and needs a scenario that nothing schedules.

## Consequences

- **Some logic exists in both projects.** Two identity recipes, `compute_demo_panel_config` and
  `compute_split_audit_2`, are among the copies; the governed-values check asserts that both copies
  match the one `dss_recipes/` mirror. The `demo_identity` library module and seven project
  variables are copied too, and the check asserts that both projects' variables are equal.
- **The governed build target moves.** `breast_panel_metrics` becomes the evidence project's target
  in the build-governance allowlist, which is keyed by project. The 2026-08-31 pilot artifacts stay
  as history of the main-project recipe.
- **Assertions run on demand, not on a schedule.** A serving change can move a documented number
  until the next local run.
- **Repository tools learn a second project:** the recipe index, the flow map, the governed-values
  check, the description push and build-governance capture.
- **The design and the per-script notebook revisions** are in
  [`EVIDENCE_PROJECT_DESIGN.md`](../../operations/EVIDENCE_PROJECT_DESIGN.md).
