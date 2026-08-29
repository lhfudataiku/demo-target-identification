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

## Part 2 — the prioritizer (`DEMO_TARGET_IDENTIFICATION`)

| | |
|---|---|
| [`prioritizer/TARGET_PRIORITIZER.md`](prioritizer/TARGET_PRIORITIZER.md) | The methodology document. Data exploration §3, features §4, splitting and leakage §5, model selection §6, validation §7, results §8, flow zones §9, migration §10 |
| [`prioritizer/FEATURE_AUDIT.md`](prioritizer/FEATURE_AUDIT.md) | Per-feature recipe audit, the seed-threshold table, the Phase 1/2 rollout results, and the Phase 3 sizing |
| [`prioritizer/PHASE3_PREREGISTRATION.md`](prioritizer/PHASE3_PREREGISTRATION.md) | Written before the Phase 3 branch exists: the intervention, pre-flight gates, seven falsifiable predictions, and the committed adopt/reject rule |

## Demo and client-facing

| | |
|---|---|
| [`demo/DEMO_NARRATIVE.md`](demo/DEMO_NARRATIVE.md) | The demo as **four acts on screen and two in a talk track**, in the order a sceptical scientist asks: what can the model see → how far can it be trusted → does it hold across my area → show me the list. **Derive the app from this, not the reverse** |
| [`demo/WEBAPP_DESIGN.md`](demo/WEBAPP_DESIGN.md) | The technical companion to the narrative: Vue/FastAPI architecture, routes, interactions and data contracts. `FLOW_MAP.md` remains the generated flow authority |
| [`demo/FLOW_MAP.md`](demo/FLOW_MAP.md) | Every dataset by zone, its producing recipe and its consuming act or notebook — generated from live DSS. **Read before pruning anything**: a reference check alone flags the whole serving layer |
| [`demo/panel_selection.html`](demo/panel_selection.html) | **Which families and diseases the demo carries.** Measured 2026-08-27 over all 670 validation diseases: subtype structure exists only in oncology, so Act 3 is breast + uterine and therapeutic-area breadth comes from Act 4's singletons. Every candidate tested by looking up where the field's validated targets actually rank. **Read before repointing the persona filter.** Supporting tables in [`demo/panel_selection/`](demo/panel_selection/), all asserted by `nb7` |
| [`demo/DASHBOARD_MOCKUP_V3.html`](demo/DASHBOARD_MOCKUP_V3.html) | **Current mockup.** Four interactive acts. The Sankey opens on the whole ontology and shows the 95.7% the seed gate excludes; panel and ontology tree merged; full ranked list with search, tractability and class filters |
| [`demo/BREAST_SURGEON_BRIEFING.md`](demo/BREAST_SURGEON_BRIEFING.md) | Clinician-facing validation set for the breast panel, including the defects a surgeon finds immediately |

## Platform and reference

| | |
|---|---|
| [`platform/DSS_CHEATSHEET.md`](platform/DSS_CHEATSHEET.md) | DSS behaviours and CLI patterns. **Read §1 before trusting any output** — those failures produce plausible results rather than errors |
| [`reference/RESEARCH_NOTE.md`](reference/RESEARCH_NOTE.md) | Evidence base behind the modelling choices. **Unvalidated corpus — verify before client-facing use** |
| [`reference/DISCOVERY_LANDSCAPE.md`](reference/DISCOVERY_LANDSCAPE.md) | The wider discovery chain (stages 1–6). A **separate framework** from the target-identification work above |
| [`appendix/`](appendix/) | Frozen snapshot CSVs backing the ablation-ladder sections. **`m3-f12`-era** — not the current champion |

## Planning

| | |
|---|---|
| [`demo/DOC_RESTRUCTURE_PLAN.md`](demo/DOC_RESTRUCTURE_PLAN.md) | **Approved 2026-08-28:** repository-wide documentation, decision, build-governance and cross-harness context restructure. Not an implementation record or current project authority |

## Historical material

| | |
|---|---|
| [`../archive/`](../archive/) | Superseded designs, native-dashboard evaluation, build chronology, mockup iterations 1–2 and the retired hand-authored flow view. Do not load by default; use only for an explicit history investigation |

## Not in this directory

- **`../DECISIONS.md`** — append-only decision log, including refuted hypotheses and corrections.
  Query `../.index/decisions.tsv` for a jump table rather than reading it.
- **`../CLAUDE.md`** — orientation, the three DSS projects, and the rules.
- **`../notebooks/`** — the assertion notebooks. They are the source of truth for every documented
  number here; a figure with no assertion will drift.
