# Document set

> **Lifecycle:** Canonical · **Audience:** repository contributors and reviewers · **Authority:** the
> current-state document router · **Update when:** a canonical, evidence or generated document moves,
> changes role or gains a successor · **Generated dependencies:** `.index/` for bounded factual retrieval
> · **Excludes:** historical chronology and implementation detail held by the routed documents.

Grouped by purpose. **Read one section, not a whole file** — several are 20–40k tokens, and `.index/`
answers most factual questions without opening any of them (see `../CLAUDE.md`). Current canonical,
evidence and generated documents appear first; planning and historical material are separated below.

## Start

| | |
|---|---|
| [`overview/PROJECT_CONTEXT.md`](overview/PROJECT_CONTEXT.md) | What the POC is for, the numbers that anchor the pitch, the personas, and **how Parts 1 and 2 fit together** including the 13 shared objects |

## Part 1 — the graph (`DEMO_KG_LS`)

| | |
|---|---|
| [`graph/GRAPH_BUILDING.md`](graph/GRAPH_BUILDING.md) | Input sources §2, graph schema §3, pipeline §4, graph webapp §6, final statistics §7 |
| [`graph/DATA_SOURCE_LICENSE_REVIEW.md`](graph/DATA_SOURCE_LICENSE_REVIEW.md) | **Preliminary internal legal-review draft:** direct and nested source lineage, licence terms, commercial-use barriers, unresolved provenance and remediation priorities |

## Part 2 — the prioritizer (`DEMO_TARGET_IDENTIFICATION`)

| | |
|---|---|
| [`prioritizer/TARGET_PRIORITIZER.md`](prioritizer/TARGET_PRIORITIZER.md) | Canonical Part 2 modelling method: population, leakage controls, features, training and model-selection rule |
| [`prioritizer/VALIDATION.md`](prioritizer/VALIDATION.md) | Compact evidence map: governed claims, notebook assertions, historical comparisons, negative results and limitations |
| [`prioritizer/CLAIM_REGISTRY.json`](prioritizer/CLAIM_REGISTRY.json) | Machine-readable governed claim-to-consumer registry; indexed as `.index/governed_claims.tsv` |
| [`prioritizer/FEATURE_AUDIT.md`](prioritizer/FEATURE_AUDIT.md) | Per-feature recipe audit, the seed-threshold table, the Phase 1/2 rollout results, and the Phase 3 sizing |
| [`prioritizer/PHASE3_PREREGISTRATION.md`](prioritizer/PHASE3_PREREGISTRATION.md) | Written before the Phase 3 branch exists: the intervention, pre-flight gates, seven falsifiable predictions, and the committed adopt/reject rule |

## Demo and client-facing

| | |
|---|---|
| [`demo/DEMO_NARRATIVE.md`](demo/DEMO_NARRATIVE.md) | The demo as **four acts on screen and two in a talk track**, in the order a sceptical scientist asks: what can the model see → how far can it be trusted → does it hold across my area → show me the list. **Derive the app from this, not the reverse** |
| [`demo/WEBAPP_DESIGN.md`](demo/WEBAPP_DESIGN.md) | The technical companion to the narrative: Vue/FastAPI architecture, routes, interactions and data contracts. `FLOW_MAP.md` remains the generated flow authority |
| [`demo/panel_selection.html`](demo/panel_selection.html) | **Which families and diseases the demo carries.** Measured 2026-08-27 over all 670 validation diseases: subtype structure exists only in oncology, so Act 3 is breast + uterine and therapeutic-area breadth comes from Act 4's singletons. Every candidate tested by looking up where the field's validated targets actually rank. **Read before repointing the persona filter.** Supporting tables in [`demo/panel_selection/`](demo/panel_selection/), all asserted by `nb7` |
| [`demo/BREAST_SURGEON_BRIEFING.md`](demo/BREAST_SURGEON_BRIEFING.md) | Clinician-facing validation set for the breast panel, including the defects a surgeon finds immediately |

## Platform, operations and reference

| | |
|---|---|
| [`platform/DSS_CHEATSHEET.md`](platform/DSS_CHEATSHEET.md) | DSS behaviours and CLI patterns. **Read §1 before trusting any output** — those failures produce plausible results rather than errors |
| [`operations/BUILD_GOVERNANCE.md`](operations/BUILD_GOVERNANCE.md) | Deterministic Part 2 build-event, accepted-baseline and targeted-review contract; read before designing or operating the approved DSS pilot |
| [`operations/FLOW_MAP.md`](operations/FLOW_MAP.md) | Every dataset by zone, its producing recipe and its consuming act or notebook — generated from live DSS. **Read before pruning anything**: a reference check alone flags the whole serving layer |
| [`operations/FLOW_MAP_EVIDENCE.md`](operations/FLOW_MAP_EVIDENCE.md) | The same map for the evidence project `DEMO_TI_EVIDENCE`, whose datasets the notebooks read; generated from live DSS. `.index/recipes_evidence.tsv` says which of its recipes are identity recipes, checked copies or evidence-only |
| [`reference/RESEARCH_NOTE.md`](reference/RESEARCH_NOTE.md) | Evidence base behind the modelling choices. **Unvalidated corpus — verify before client-facing use** |
| [`reference/DISCOVERY_LANDSCAPE.md`](reference/DISCOVERY_LANDSCAPE.md) | The wider discovery chain (stages 1–6). A **separate framework** from the target-identification work above |

## Decisions

| | |
|---|---|
| [`decisions/DECISION_REGISTER.md`](decisions/DECISION_REGISTER.md) | Current durable choices, stable IDs, rationale, evidence and consequences; query `.index/decisions.tsv` first |
| [`decisions/adrs/`](decisions/adrs/) | Short rationale records only for decisions too consequential for one register entry |

## Planning

| | |
|---|---|
| [`operations/FLOW_MIGRATION_WORKPLAN.md`](operations/FLOW_MIGRATION_WORKPLAN.md) | **Draft, revised 2026-10-28; full option chosen.** The notebooks stay in the repository and run locally, and `validate_notebooks` is dropped. Their supporting evidence moves to its own DSS project reading only zones 00–31 (M2). The serving flow is then re-zoned (M3) and rebuilt by webapp function with tied ranks (M4–M6) |
| [`operations/EVIDENCE_PROJECT_DESIGN.md`](operations/EVIDENCE_PROJECT_DESIGN.md) | **Draft, 2026-10-28.** The evidence half of the migration's M1: how the supporting evidence project provides each notebook read, its 24–25 recipes and 18 exposed inputs, and the per-script notebook revisions |
| [`operations/WEBAPP_DATASET_MAP.md`](operations/WEBAPP_DATASET_MAP.md) | **Draft, 2026-10-27.** What the released webapp reads, field by field and with row scope, and the recipe and dataset counts of re-zoning versus rebuilding the serving flow once the notebook components leave it |

Completed plans move to [`../archive/`](../archive/): the most recent is the webapp redesign, live
2026-10-27 (`DEC-DEMO-004`, `DEC-DEMO-005`; its scope and workplan are
[`WEBAPP_REDESIGN_SCOPE.md`](../archive/WEBAPP_REDESIGN_SCOPE.md) and
[`WEBAPP_REDESIGN_WORKPLAN.md`](../archive/WEBAPP_REDESIGN_WORKPLAN.md)).

## Historical material

| | |
|---|---|
| [`../archive/`](../archive/) | Superseded designs, native-dashboard evaluation, build chronology, the three dashboard mockups and their app-parity check, the retired hand-authored flow view, completed plans (the documentation restructure with its phase records, the Visual Graph Explorer integration scope, the bs-blueprint alignment, the webapp redesign scope and workplan), the 2026-09-03 graph-snapshot switch record, the `m3-f12`-era appendix snapshots and breast-annotation exports, and the unpublished DSS wiki drafts. Do not load by default; use only for an explicit history investigation |
| [`../archive/decisions/`](../archive/decisions/) | Immutable retired decision chronology and its five-way triage; query `.index/decisions_history.tsv` before opening it |

## Not in this directory

- **`../.index/index_metadata.tsv`** — owner, scope and offline freshness check for every current,
  historical, claim, model, feature, recipe and code index.
- **`../.index/claims.tsv`** — default bounded current numeric-claim surface, selected only from
  `tools/index_manifest.json`; governed Part 2 claims remain in `governed_claims.tsv`.
- **`../.index/historical_claims.tsv`** — explicit historical-comparison surface; never use it for a
  current claim-risk query.
- **`../.index/decisions.tsv`** — default bounded query over current durable decisions.
- **`../.index/decisions_history.tsv`** — explicit historical query over experiments, incidents,
  operations, reusable traps and promoted durable entries.
- **`../CLAUDE.md`** — orientation, the three DSS projects, and the rules.
- **`../notebooks/`** — the assertion notebooks. They are the source of truth for every documented
  number here; a figure with no assertion will drift.
