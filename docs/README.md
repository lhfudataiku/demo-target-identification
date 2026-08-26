# Document set

Grouped by purpose. **Read one section, not a whole file** — several are 20–40k tokens, and
`.index/` answers most factual questions without opening any of them (see `../CLAUDE.md`).

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
| [`demo/DEMO_NARRATIVE.md`](demo/DEMO_NARRATIVE.md) | The demo as a six-question interrogation (Q1 *"show me the list"* → Q6 *"what can't it do?"*), because that is the order a sceptical scientist asks in. **Derive the dashboard from this, not the reverse** |
| [`demo/DASHBOARD_DESIGN.md`](demo/DASHBOARD_DESIGN.md) | The demo surface **as one Vue webapp** built from `bs-blueprint`: six acts on a single therapeutic-area spine (breast, HER2+ lead), the route/view/data map, the guardrails the code must enforce, nine serving-layer gaps, and **six places the narrative is measurably stale** |
| [`demo/DASHBOARD_MOCKUP_V3.html`](demo/DASHBOARD_MOCKUP_V3.html) | **Current mockup.** Four interactive acts. The Sankey opens on the whole ontology and shows the 95.7% the seed gate excludes; panel and ontology tree merged; full ranked list with search, tractability and class filters |
| [`demo/DASHBOARD_MOCKUP_V2.html`](demo/DASHBOARD_MOCKUP_V2.html) | Iteration 2, kept for comparison |
| [`demo/DASHBOARD_MOCKUP.html`](demo/DASHBOARD_MOCKUP.html) | Iteration 1, six static acts |
| [`demo/BREAST_SURGEON_BRIEFING.md`](demo/BREAST_SURGEON_BRIEFING.md) | Clinician-facing validation set for the breast panel, including the defects a surgeon finds immediately |

## Platform and reference

| | |
|---|---|
| [`platform/DSS_CHEATSHEET.md`](platform/DSS_CHEATSHEET.md) | DSS behaviours and CLI patterns. **Read §1 before trusting any output** — those failures produce plausible results rather than errors |
| [`reference/RESEARCH_NOTE.md`](reference/RESEARCH_NOTE.md) | Evidence base behind the modelling choices. **Unvalidated corpus — verify before client-facing use** |
| [`reference/DISCOVERY_LANDSCAPE.md`](reference/DISCOVERY_LANDSCAPE.md) | The wider discovery chain (stages 1–6). A **separate framework** from the target-identification work above |
| [`appendix/`](appendix/) | Frozen snapshot CSVs backing the ablation-ladder sections. **`m3-f12`-era** — not the current champion |

## Not in this directory

- **`../DECISIONS.md`** — append-only decision log, including refuted hypotheses and corrections.
  Query `../.index/decisions.tsv` for a jump table rather than reading it.
- **`../CLAUDE.md`** — orientation, the three DSS projects, and the rules.
- **`../notebooks/`** — the assertion notebooks. They are the source of truth for every documented
  number here; a figure with no assertion will drift.
