# Webapp design — the technical companion to the demo narrative

<!-- Governed claims consumed here: TI-DATA-001 TI-MOD-001 TI-VAL-001 TI-VAL-002 TI-VAL-003 TI-VAL-004 TI-VAL-005 TI-VAL-007 TI-VAL-008 TI-VAL-009 -->

> **Lifecycle:** Canonical · **Audience:** webapp implementers and technical reviewers · **Authority:**
> Vue/FastAPI architecture, routes, state, interaction and data contracts · **Update when:** an app
> contract, route, interaction or backing-data contract changes · **Generated dependencies:**
> [`FLOW_MAP.md`](../operations/FLOW_MAP.md) for live flow lineage, the notebook assertions cited in §9 and
> [`../prioritizer/CLAIM_REGISTRY.json`](../prioritizer/CLAIM_REGISTRY.json) for governed consumers ·
> **Excludes:** hand-authored DSS-flow inventories, native-dashboard evaluation and build chronology.
> Detailed analytical rationale lives in [`../prioritizer/VALIDATION.md`](../prioritizer/VALIDATION.md);
> do not duplicate it here beyond the contract details the app must enforce.

**Read [`DEMO_NARRATIVE.md`](DEMO_NARRATIVE.md) first.** This document is derived from it and has no
independent authority. The narrative says *what we claim and in what order*; this says *what each
claim rests on, which zone and dataset serve it, and what the code must enforce.*

**The claim the app has to support.** From public knowledge alone, the model **reconstructs** the
targets a disease's field has already validated — and the test is a scientist's eyeball test on a
disease they know. It is not a discovery claim, and the app must not read as one. We are an AI
platform company demonstrating machinery, not a drug-discovery vendor proposing a research direction.

**What the demo surface is.** A single Vue SPA deployed as a DSS STANDARD webapp, built on the team's
`bs-blueprint` framework. **Four acts in the app; acts 5 and 6 are a spoken talk track**, because they
are about the platform rather than the biology.

**Status.** Built: all four acts are live views in [`../../webapp/`](../../webapp/), and the app is the
current artefact. The three mockup iterations it was derived from, including the mockup-to-app parity
check, are historical material in
[`../../archive/dashboard-mockup-iterations/`](../../archive/dashboard-mockup-iterations/).

**The redesign, built in phases on a preview webapp** (`DEC-DEMO-004`, `DEC-DEMO-005`;
[`WEBAPP_REDESIGN_SCOPE.md`](WEBAPP_REDESIGN_SCOPE.md) and
[`WEBAPP_REDESIGN_WORKPLAN.md`](WEBAPP_REDESIGN_WORKPLAN.md)). The app will open on the shortlist (Act 4)
and answer Acts 1–3 as the three sections of one page, *Why trust the list*, with one disease shared by
both pages; the shortlist gains an evidence review and an evidence assistant. The sections that state
principles (§4, §6, §8) already carry it, each change marked *planned*. The sections that describe the
app as built change with the phase that builds it. **Phases 1–7 are built on the preview webapp:** the
two-page navigation, the shared disease and *Why trust the list* (Phase 1); the shortlist split into the
list and a tabbed card for the selected candidate, with the *How do we know?* links (Phase 2); and the
candidate's HGNC identity in that card's header (Phase 3); and the drug records behind the badges
(Phase 4); the top five SHAP drivers in *Why this ranking?* (Phase 5); the Trials and Literature
tabs (Phase 6); and the evidence assistant, with a link to Agent Hub (Phase 7). §3.3
and the act tables below describe them. The deployed webapp keeps the four act routes until the Phase 8
switch-over.

**Where the rest lives.** [`FLOW_MAP.md`](../operations/FLOW_MAP.md) is the generated flow authority. Historical
native-dashboard evaluation is in [`../../archive/NATIVE_DASHBOARD_EVALUATION.md`](../../archive/NATIVE_DASHBOARD_EVALUATION.md),
and build chronology remains in [`../../archive/DASHBOARD_BUILD_LOG.md`](../../archive/DASHBOARD_BUILD_LOG.md).

---

## 1. The derivation rule

Two constraints, and the second is the one that shaped this document.

**The narrative is an interrogation, in the order a sceptical scientist asks.** So the acts run in that
order, each number traces to the dataset that produced it, and the narrative's §5 *"what not to show"*
becomes a per-act exclusion list. Not stylistic — each exclusion names a specific way the act would
mislead.

**An R&D department owns one therapeutic area, not 670 diseases.** So **one disease is the spine of the
whole deck** and every act returns to it. An earlier draft gave each question its own best example —
obesity for the filtering, non-small cell lung for MAPK3, HER2+ for clinical sanity. That hands a sceptic
a free shot: *"you picked a different disease every time you needed a win."* Holding one constant closes
it, and it is also how the audience is organised.

The general-to-specific act order (the graph, then coverage, then the area, then the disease) departs
from the narrative's page order deliberately: a team that has already scoped a POC to their own area
needs to know what evidence the model can see and how far it can be trusted **before** they will spend
attention on one gene list. The narrative's rule that survives intact is the *form* the aggregate takes —
see act 2.

---

## 2. The spine: breast oncology, HER2-positive lead

**Why a spine at all:** the eyeball test needs a disease the audience knows cold. HER2+ reconstructs at AUC 0.9365 and a breast oncologist recognises its top ranks on sight — which is the entire demo in one screen.

The only candidate area where the **entire** deck survives without leaving it. Every figure below was
computed from `dashboard_candidates` while writing this document.

**The clinical sanity check, unprompted.** HER2+ breast carcinoma scores 12,272 candidates. Top 15:

| rank | gene | | rank | gene |
|--:|---|---|--:|---|
| 1 | TP53 *known* | | 9 | **HRAS** — **novel** |
| 2 | EP300 | | 10 | KRAS |
| 3 | PIK3R1 | | 11 | EGFR |
| 4 | CREBBP | | 12 | BRCA1 |
| 5 | PIK3CA | | 13 | SMAD3 |
| 6 | CTNNB1 | | **14** | **ERBB2** — the only *approved-for-this-disease* gene in the top 15 |
| 7 | JAK2 | | 15 | MAPK1 |
| 8 | PTPN11 | | | |

The model was never told which gene this disease is named after. **ERBB2 lands at 14 of 12,272**, and the
surrounding list is the PI3K/AKT and RAS–MAPK axis — the biology that drives trastuzumab resistance. AUC
**0.9365** on 599 known targets, **19.7×** enrichment at 50. A breast oncologist validates this in about
ten seconds, which is the point of leading with it.

**The punch line gets stronger.** The narrative's thirty-second check is obesity's ADRB2 — one approved
target carrying a liability flag. On HER2+:

- **9 of the top 15 carry a documented liability flag (60%).** 23 of the top 50 (46%).
- **ERBB2 itself (#14) carries one**, with TP53, PIK3R1, PIK3CA, CTNNB1, JAK2, PTPN11, EGFR and MAPK1.

*"Exclude targets with known safety liabilities"* would delete the target this disease is named after,
and the target of its standard-of-care antibody.

**The hard case is in the same panel.** Triple-negative breast carcinoma ranks RAD50 #1, ATM #2, TP53 #3,
BRCA2 #4, NBN #5 — the homologous-recombination panel, all novel — with only **8** known associations, so
we cannot score it. `breast_panel_overlap` shows HER2+ and TNBC share **2 of 50**, so subtype resolution
becomes an argument *for* the platform to a subtype-organised team.

**What the spine costs.** Obesity's funnel and the GHSR/ADRB2/MCHR1 coherence beat leave the deck (HER2+
has its own funnel, act 4). NSCLC's *"MAPK3 at novel #3"* headline goes — on HER2+, MAPK3 is novel at
**#61** and the head-of-list novel candidate is **HRAS at #9**; enrichment is equivalent (19.7× vs 19×),
the single dramatic beat is not. The MRN complex on-graph shot is **not** a HER2+ story (RAD50 #55, NBN
#99, MRE11 #401) and moves to act 6 with TNBC; act 4's mechanism shot is the PI3K/AKT axis instead. Act
5's degree-matched and hub-bias evidence is pool-wide by construction and stays global — correct, because
those are claims about the *model*, not the disease.

**Retargeting.** Each act names its disease filter, so the deck retargets by changing the spine disease
and re-deriving four numbers: the funnel, the landing count, the liability share of the head, and the
top-15 table.

---

## 3. Architecture — one Vue SPA, deployed as a DSS webapp

### 3.1 The stack

Vue 3 + Vite + Tailwind 4 + ECharts + Pinia + vue-router on the team's
[bs-blueprint](https://github.com/dataiku/bs-blueprint) framework, pinned to a commit in
`frontend/package.json`: the `@dataiku/ea-ui-kit` theme and components, the `@dataiku/vue-icons` set,
and bs-blueprint's app shell (`AppLayout`, `PageHeader`) and composites. A FastAPI backend serves the
act data and the built bundle. `dss_webapp/deploy.sh` mirrors `backend/` and `frontend_dist/` into the
project library under `python/<LIB_NS>/` and sets the STANDARD webapp's html and js from the build
(`@dataiku/vite-plugin-dku-webapp`), so DSS renders the app directly, with no iframe.

The app was seeded from an early copy of the framework's template and realigned with the current
framework on 2026-10-15 (`DEC-DEMO-003`; the phase-by-phase record is
[`../../archive/BLUEPRINT_ALIGNMENT_PLAN.md`](../../archive/BLUEPRINT_ALIGNMENT_PLAN.md)).

**What we get for free that the native route could not give us:** routed acts with a sidebar that builds
itself from route `meta`; real prose beside real charts; display-only columns; row-level drill; a single
deploy command; and a design system already themed to the Dataiku brand.

### 3.1.1 Graph exploration — one shared handoff, not a second graph product

Acts 1 and 4 use the same `VisualGraphExplorerCard`. The card prepares context-specific Cypher but does
not execute it, and its **Open full Explorer** control is a plain link that opens the Visual Graph
Explorer in a new browser tab; nothing is embedded in this app. The card provides an explicit
copy-and-paste handoff: the query is shown with three numbered steps (copy it with **Copy query**, open the
Explorer, create a new query there, paste and run), copying happens only when the user presses **Copy
query**, and opening the link never touches the clipboard. There is no supported query deep link, private
plug-in API call, or iframe-DOM integration.

Act 1 supplies three deterministic starter queries. Act 4 supplies five independently bounded presets
for the selected disease and target gene: interaction, pathway, molecular function, biological process
and drug context. Each preset is a prepared illustration, not a claim that it exhaustively summarizes a
route. Target Prioritizer performs no graph query execution, result joining, accumulation, graph/table
rendering or graph-route API call; the Visual Graph Explorer owns execution and all exploratory display.
The Target Prioritizer backend consequently has no `/api/graph/*` surface.

### 3.2 The lineage rule — non-negotiable

A custom app is opaque to lineage, and act 6 closes on *"the record of why is in the flow, not someone's
inbox."* A screenshot-grade SPA would undercut the pitch it exists to deliver. So:

> **Every card that states a number names its source dataset in a footer, and every act carries a link
> into the flow zone that produced it.**

Provenance moves *into* the UI rather than being borrowed from native tiles. This is a first-class design
requirement, not a nice-to-have: it is what lets us claim the platform while shipping custom code. The
mockup implements it as a `dataset · recipe` footer on every card.

### 3.3 Route → view → data map

The shortlist leads (`DEC-DEMO-005`): `/shortlist` is the home route and `order` 1, *Why trust the
list* is `order` 2, and Settings sits in the footer. Built in Phase 1 of the redesign on 2026-10-26; the
deployed webapp still serves the four act routes until the Phase 8 switch-over.

Corrected 2026-09-03 against the shipped app. This table had drifted on every column: it named
routes and views from the migration plan rather than the ones that were built, and its data column
still described the mock-first phase §3.4 describes, which ended. **Acts 5 and 6 are talk track, not
routes** — the router registers two primary routes, and copy that forward-references a fifth act is
a defect (§3.7).

| act | route | view | backend route | backing datasets |
|---|---|---|---|---|
| 4 | `/shortlist` (home) | `ShortlistView` → `shortlist/CandidateTable`, `CandidateHeader`, `OverviewTab`, `RankingTab`, `LineageTab` | `GET /api/candidates{,/diseases,/gene,/identity,/drugs,/drivers}`; `GET /api/candidates/sources{,/selection}`; `POST /api/assistant` | `dashboard_candidates`; from zone S1, `candidate_identity` for `/identity`, `drug_evidence_records` for `/drugs` and `candidate_shap_top5` for `/drivers`; `/sources` searches the CT.gov and PubMed agent tools and reads and writes the folder `act4_evidence_cache`; `/assistant` reads the same sources and the folder, calls the three agent tools and stores nothing |
| 1 | `/trust?section=graph` | `TrustView` → `trust/GraphSection` | `GET /api/evidence` | `graph_node_type_counts`, `graph_relation_counts`, `graph_node_source_counts`, `graph_ppi_provenance`, `graph_label_evidence` |
| 2 | `/trust?section=reconstruction` | `TrustView` → `trust/ReconstructionSection` | `GET /api/calibration` | `validation_auc_by_disease`, `family_auc_by_family`, `split_audit_2`, `disease_eligibility`, `persona_enrichment`, `hub_bias_meter`, `orthogonality_scatter`, the `COUNT_RECORDS` metrics of `enriched_dwpc_{GGD,GPGD,GCD}`, + the live champion saved model |
| 3 | `/trust?section=family` | `TrustView` → `trust/FamilySection` | `GET /api/families`, `/api/families/{id}` | `family_panel_metrics`, `family_panel_overlap`, `family_panel_top50`, `family_panel_programme`, `persona_enrichment`, `demo_panel_config` |

**One disease drives both pages.** `stores/selection.ts` (Pinia) holds the shortlist's disease list
(`/api/candidates/diseases`, fetched once) and the selected `disease_index`; both views read and write
it, so choosing a disease on either page changes it on the other. Section 2 marks that disease using
`/api/calibration`'s `diseases` list (each scored disease's AUC, rank, enrichment and known-target
count, from `persona_enrichment`, whose `is_current` flag is not read). Section 3 opens the family
whose `disease_indexes` in `/api/families` contain it, or says there is none. The section links scroll
the content pane itself, because `scrollIntoView` also scrolls the shell's fixed-height ancestors.
`/api/calibration` no longer serves the per-disease `auc_values`, the `personas` list or the driver
frequencies, and no longer reads `shap_driver_frequency`.

One non-act route is registered as `menu: 'tertiary'`: `/settings` (`SettingsView`, per-browser
presenter notes). The **glossary is not a route**: it is an overlay (`stores/glossary.ts` +
`ActGlossaryDrawer`, mounted once in `DefaultLayout`), opened from the Glossary button that
bs-blueprint's shell places at the top right of every page, or by clicking any `ActTerm`. A route would have been
fewer files and would have followed §3.5's build-itself convention, but a reader asking *"what was
AUC again?"* is mid-card, and navigating away answers the question by losing their place.

Three datasets this table used to name are **not** what the app reads, and the difference matters:
`breast_panel_overlap` was retired on 2026-08-28 in favour of `family_panel_overlap`, which covers
all three act 3 families from one table (`compute_persona_candidates.py` records the retirement);
`persona_candidates` is the panel-selection dataset, while act 2 plots `persona_enrichment`; and
`validation_auc_by_disease_2` with a `level` filter was superseded by the unsuffixed dataset plus a
separate family table, which is why act 2's tab switches source rather than filtering one.

Act 4 absorbed the earlier hand-written webapp (`V2ZpfdV`, 1,086 lines): the disease picker, the
three-clause filter with its live count and the detail drawer were ported to Vue components rather
than rewritten. Its `SECRETED` rule, its tooltip copy and its refusal to fetch `prediction` are
**validated behaviour** — the refusal is enforced in `BULK_COLS`, not merely documented. The
drawer's five-feature list was **not** carried across: it was stale against the champion, and the
drawer now renders `feature_glossary.CHAMPION` so it cannot go stale again.

### 3.4 Mock first, then swap

> **Completed 2026-09-03.** All four act views read live backend routes and every act mock module has
> been deleted, as the rule below requires. The mock modules that remained belonged to the template's
> optional blocks, and were removed with those blocks on 2026-10-15. The section is
> kept because the swap rule still governs any new view — and because the closing warning turned out
> to be the section's most load-bearing sentence: two hard-coded figures did outlive the swap, in act
> 2's own copy rather than in a mock module, and §6 now carries a guardrail for exactly that.

Every view reads from a module in `frontend/src/data/mock/`, following the blueprint's own idiom
(`data/mock/medical-info-tickets.ts`). Numbers are the verified ones, hard-coded.

This is deliberate and it is the point of starting with the mockup:

1. **The layout argument is settled before any DSS call exists.** Iterating on a chart's form should not
   require a built dataset or a running backend.
2. **Four of six acts are blocked on flow work anyway** (§9). Mock data lets acts 3, 4 and 6 be finished
   while acts 1, 2 and 5 wait on recipes.
3. **A wrong number is visible in a diff.** A hard-coded `0.8230` in a reviewed file is safer than a
   chart tile whose filter silently stopped applying.

The swap path per view is one function: replace the mock import with `fetch(apiUrl('/api/<act>/…'))`
against a backend route that reads the dataset. **The mock module and the backend route must return the
same shape** — define the shape in `types/` first, and have both conform to it.

⚠ **Do not let mock numbers outlive the swap.** Every mock module carries a header comment naming the
dataset and the notebook assertion each figure came from, so a stale value is traceable. When a view
swaps to live data, its mock module is deleted, not commented out.

### 3.5 Conventions that are not negotiable

From bs-blueprint's rules (the managed block in `webapp/AGENTS.md`, enforced by `npm run check`, which
must print `check: ok` with no suppressions); violating them means the app stops looking like a Dataiku
product.

- **Never hardcode colors.** Tailwind utilities over the kit theme's tokens — `bg-background`,
  `text-muted-foreground`, `border-border`, `bg-primary`, `text-destructive`. No hex, no `text-[#…]`.
  A chart series names its meaning and takes its colour classes from
  `frontend/src/utils/seriesColours.ts` (`SERIES_TEXT`, `SERIES_BG`), which holds exactly this table;
  colours are classes, never inline styles, because the design lint cannot see a colour set through a
  bound `:style`. The overlap matrix and the gene coverage grid name `chart-3` and `chart-1` directly, as
  scope D12 fixed them; they carry this table's `contrast` and `highlight` meanings. Change the table here
  first, then the module.

  | Meaning | Where it appears | Kit token |
  |---|---|---|
  | `measured` — the model or pipeline result | precision, AUPRC, corroborated interactions, candidate pool, node types, AUC histogram, personas, eligible band | `chart-2` (teal) |
  | `contrast` — the series compared against it | other drivers, relations, shared terms, trustworthy intervals, overlap matrix, positive SHAP, score bar | `chart-3` (navy) |
  | `highlight` — the exception to look at | single-source interactions, genes distinct to one term | `chart-1` (orange) |
  | `approved`, `trial` | Act 4 drug badges | `success`, `warning` |
  | `baseline` — base rate or chance | base rate, grouped sources, duplicate admissions | `muted-foreground` |
  | `negative` — untrustworthy or negative | failed-trust interval, negative SHAP | `destructive` |
  | categories with no fixed meaning | Sankey routes and splits, label-evidence donut | `chart-1…5` in order |

  Canvas charts resolve colours through `seriesColor()` or `resolveColour()`, because ECharts cannot
  read CSS variables or the kit's space-separated `hsl()` values.
- **Type and spacing on the scale.** No arbitrary values (`text-[13px]`, `w-[86px]`): use the kit's
  type steps and Tailwind's numeric spacing. The one exception is chart-internal labels in the two
  dense HTML charts (gene coverage grid, subtype overlap matrix), sized in their component's scoped
  CSS and declared in `frontend/eslint.config.js`, as canvas charts size theirs in chart options.
- **Let the sidebar build itself.** Add an act by adding a route with `meta: { title, icon, menu:
  'primary', order }`. Never hand-build a menu array.
- **`apiUrl()` for every call.** A bare `fetch('/api/…')` does not reach the backend inside DSS.
- **Kit parts first** — `@dataiku/ea-ui-kit` (`Button`, `Input`, `Checkbox`, `NativeSelect`,
  `Table*`, …) and bs-blueprint's `SelectField`, `EmptyState` and `SettingsSwitchItem` — before custom
  markup; never copy a component into the app. Icons from `@dataiku/vue-icons`, the DSS icon set.
- **No binary assets.** DSS libraries are text-only — no `.png`, no logo files.
- **One view + one route + one backend route file + one service file.** Replace the example view; do not
  accrete beside it.
- Python: `from __future__ import annotations`, type hints, `routes/` parses and returns JSON while
  `services/` does the Dataiku calls, DSS access via `get_project()` from `dss_client.py`.

### 3.6 Build and deploy

```bash
eval "$(dku auth export-env)"   # DSS credentials for the local backend
make dev                         # vite + backend, local
make deploy                      # build, mirror the library, set the webapp definition
```

`app.env` holds the identity (`PROJECT_KEY=DEMO_TARGET_IDENTIFICATION`, `LIB_NS`, `APP_PREFIX`,
`VITE_APP_NAME`, `WEBAPP_ID`). The procedure, including verification, is
[`../../webapp/DEPLOYMENT.md`](../../webapp/DEPLOYMENT.md). To take a newer framework release, bump the
pinned `bs-blueprint` commit or tag in `frontend/package.json`, run `npm install` and
`npx bs-blueprint sync` (from `frontend/`), then `python3 tools/sync_harness.py --write` so the updated
rules block reaches `webapp/CLAUDE.md` as well, then `npm run check`.

### 3.7 The card copy contract

Added 2026-09-03. Two audiences read every card — the Dataiku data scientist demonstrating it, and a
client whose room spans business, engineering and science. Before this, one register served both and
neither was served well: titles carried the card's argument, subtitles carried methodology and chart
furniture at the same time, and presenter script rendered identically to audience copy.

`ActCard` now divides that work into four slots, and the division is the contract:

| slot | job | rule |
|---|---|---|
| `title` | names the card | short noun phrase. Never an argument, never led by a count |
| `desc` | the finding | **one** sentence, carrying its live number |
| `#note` | the insight that did not fit | always visible, in the footer bar |
| `#method` | methodology, caveats, formulas, internal references | **collapsed** behind a labelled disclosure; `method-label` renames it |
| `#presenter` | the line for whoever is demoing | hidden unless presenter mode is on |

The pattern is act 4's *Why this gene?* generalised — its percentile explanation was the only
methodology block in the app that read well, and the only thing wrong with it was that it was always
open.

**Presenter mode** (`stores/presenter.ts`, Settings → Presenting) is per-browser in `localStorage`,
deliberately **not** a DSS project variable: it is a property of who is standing in front of the
screen, it must not change what a colleague sees, and it must not need a backend round trip thirty
seconds before a demo. Default on — the person running it locally is usually rehearsing.

**One glossary, two halves.** `utils/glossary.ts` holds the user-facing definition of all 55
data-science and biology terms, and `<ActTerm t="key">` renders any word with that definition attached
via the existing `ActInfo` affordance. `ActStat` takes the same key as `t`, because a stat label is
four words of monospace over a big number — the densest place in the app and the likeliest to be a
term of art. Clicking any term opens the glossary drawer at its entry, so a reader who wants the
neighbouring terms gets them without navigating away. It exists for the reason `backend/feature_glossary.py` does,
and the drift it prevents had already happened: *enrichment* carried two differently-worded glosses,
*novel* was defined in act 4 and used undefined in act 3, and *top 50* was used nine times in act 3
and defined nowhere. The two files divide cleanly — **`feature_glossary.py` owns the model's
features** and reaches the frontend on the payload; **`glossary.ts` owns everything else**. Neither
restates the other.


---

## 4. The four acts, and the talk track

**Built in Phase 1, not yet deployed** (`DEC-DEMO-005`): the app opens on act 4, and acts 1–3 are the
three sections of *Why trust the list*, reached from the list's *How do we know?* links (Phase 2).
The act numbers stay as labels. What each act establishes does not depend on the order, so the third
column says what it answers rather than why it comes first.

| act | what it establishes | what it answers |
|---|---|---|
| **1** | **The evidence base** — the graph, and that every edge knows where it came from | the model can only see what is in here; act 4's mechanism shot pays this off |
| **2** | **Scope and calibration** — 670 diseases, the *spread*, where HER2+ sits in it | *"can I trust this for my disease"*, for the disease open on the list |
| **3** | **The therapeutic area** — the 15-term breast panel, and that the subtypes separate | the team sees itself; act 4's single disease stops looking cherry-picked |
| **4** | **The shortlist** — the list, the filter, the SHAP, the pathway | the deliverable, and the opening page |
| **5** | **The interrogation** — famous genes, novel discovery, the ground truth | every objection, answered on the spine disease *and* across 670 |
| **6** | **The limits and the punch line** — TNBC, then three refuted ideas | what makes acts 1–5 believable, and the platform close |

**Card names below are the narrative's, and several no longer match the app's.** The §3.7 rewrite
retitled 19 cards so a title names its card rather than arguing it. The claims in these tables are
unchanged and still authoritative; this table is how to find the card that carries one.

| act | narrative / mockup name | title in the app |
|---|---|---|
| 1 | Node inventory · 8 node types | **What's in the graph** |
| 1 | Relation inventory · 18 relations | **How things connect** |
| 1 | Where the nodes came from | **Where the data came from** |
| 1 | Every edge knows where it came from | **Provenance on every edge** |
| 1 | What "known target" actually means | **What counts as "known"** |
| 1 | The graph, in four numbers | **The knowledge graph** |
| 1 | Explore the graph | **Explore the graph yourself** |
| 2 | Where the candidates come from | split in two: **Which diseases qualify** + **How the candidate pool is built** |
| 2 | Precision, against the base rate it has to beat | **Precision vs. chance** |
| 2 | How well the ranking holds | **AUC, disease by disease** |
| 2 | Usefulness is not uniform | **Enrichment, disease by disease** |
| 2 | What the model actually keys on | **What drives the score** |
| 2 | What the 14 features actually are | **The model's inputs** |
| 3 | Choose a family | **The family panel** |
| 3 | AUC, with the uncertainty it actually has | **AUC with confidence intervals** |
| 3 | For the thin diseases, change the metric | **When AUC stops working** |
| 3 | How much do the subtypes overlap? | **Subtype overlap** |
| 3 | The common programme, and what is subtype-specific | **Shared vs. subtype-specific** |
| 3 | Every gene, against every term it reaches | **Gene coverage across the family** |
| 4 | The ranked list — *disease* | **The ranked list** (the disease moved into the subtitle) |
| 4 | Why this gene? | unchanged — it is the pattern the rest were rebuilt against |
| 4 | Explore the evidence graph | **See the evidence on the graph** |

---

### Act 1 — The evidence base

*Why trust the list*, section 1 (built in Phase 1). The *where* column says where each claim now
appears: up front, or under *Show the detail*. The asserted figures are unchanged.

| claim | where | asserts |
|---|---|---|
| Node inventory | detail · bars, *What's in the graph* | **113,391** nodes over 8 types: disease 27,153 · biological_process 23,974 · gene/protein 20,861 · phenotype 19,120 · molecular_function 10,041 · drug 5,282 · cellular_component 4,077 · pathway 2,883 |
| Relation inventory | detail · bars, *How things connect* | **2,851,510** edges over **18** relations. Verified live against `GRAPH_BUILDING.md` §7.1 — protein_protein 520,380 · phenotype_protein 487,054 · disease_phenotype_positive 380,280 · disease_protein 378,888 · bioprocess_protein 251,808 · cellcomp_protein 186,806 · molfunc_protein 156,246, **all seven match exactly** |
| **Every edge knows where it came from** | up front · bars, with the corroborated share in prose | of 520,380 protein interactions: menche 189,982 · string 151,254 · huri 92,536 · menche+string 54,554 · huri+menche 28,478 · all three 2,714 · huri+string 862. **86,608 (16.6%) are corroborated by more than one independent interactome, and the graph records which** |
| **What "known target" actually means** | up front · bars, with the unannotated edges named in prose | of 323,786 annotated disease–gene edges: genetic_association **171,810** · somatic_mutation **150,266** · both **1,710**. These edges *are* the training label |
| Accepted against a frozen reference | detail · one-line note; the page states the acceptance, not these figures | nodes −0.13%, edges −0.03%, **14 of 18 relations reproduce exactly**, identical relation inventory |
| Explore the graph | moved to the shortlist | the shortlist's shared Explorer card, with its five pair-specific presets; Act 1's three starter queries were retired with the act page |

**The provenance data is two disjoint stories.** `edge_metadata`'s 844,166 rows split cleanly: 520,380
protein_protein rows carry `ppi_sources` with blank `datatypes`; 323,786 disease_protein rows carry the
reverse. Two cards, two filters, and **both filters are load-bearing** — unfiltered, each chart shows the
other block as one blank category three times the size of any real one.

The second card was not in the original design and is the more valuable. *"Known target"* is the phrase
the whole deck rests on, and this says what it means: 53% genetic association, 46% somatic mutation. It
defuses part of act 5's ground-truth objection four acts early.

⚠ **`disease_protein` has 378,888 edges but only 323,786 metadata rows** — 55,102 (14.5%) carry no
evidence-type annotation. Do not describe the donut as covering all disease–gene edges.

**Explore is an explicit handoff, and it now lives on the shortlist.** The shared card opens the Visual
Graph Explorer and, when the browser permits it, copies the selected query for the user to paste and run
there. The Explorer's query generator owns natural-language exploration; the app has no local Cypher
executor, graph/table toggle or graph renderer.

> **Must not appear:** the build pipeline, recipe counts, how long it took. No model score in this
> section: it describes what the model can see, not how well it does.

---

### Act 2 — Scope and calibration

*Why trust the list*, section 2 (built in Phase 1), for the disease shared with the shortlist.

| claim | where | asserts |
|---|---|---|
| **Zero straddling keys — read this first** | up front · one line; the split table under detail | 3 rows; all four overlap/straddling columns at **zero** across train (2,187,862 rows / 383 diseases), validation (3,958,921 / 670), test (607,345 / 104) |
| The spread across 670 diseases | up front · histogram, 20 bins | macro **0.8230**, median 0.8623, range 0.1045–0.9962 over the **668** that score |
| It holds across 505 families | detail · one line | macro **0.8009** over the **503** that score |
| **Usefulness is not uniform** | up front · the quartiles in prose, beside the selected disease's own enrichment | rank enrichment median **19.2×**, quartiles **9.1–28.2×**, range **0–59.2×** across 670 diseases |
| Where your disease sits | up front · marker on the histogram, rank and share of diseases beaten | HER2+ at **0.9365**, rank 94 of 668 — upper tail, stated as a *position in a spread* |

**The framing rule.** The distribution leads; the macro number is its summary. The narrative forbids raw
AUC as an opening number — *"it is the answer to a question they did not ask"* — and the TxGNN result is
why: showing experts *why* raised their accuracy 46% and confidence 49%; accuracy alone moved neither. A
scoped-POC team's real question is **can I trust this for my disease**, which is about spread and
position, not a mean.

The audit is the section's first line, ahead of every AUC. The AUCs mean nothing until the straddling
count is zero, and the layout enforces the reading order. Precision against chance, which diseases
qualify, how the candidate pool is built and the bias toward well-connected genes sit under *Show the
detail*. *What drives the score* and *The model's inputs* moved to the shortlist's detail and the
glossary.

⚠ **Two corrections the build forced.**

1. **The `level` filter is load-bearing.** `validation_auc_by_disease_2` holds two populations in one
   table — 670 `disease` rows and 443 `split_key` rows. Filtered: **0.8230**, the documented champion
   figure. Unfiltered: **0.8157**. A view without the filter is off by 73 basis points and looks fine.
2. **19× is the median, not a ceiling.** The narrative and the old webapp both say *"19× on non-small
   cell lung carcinoma and 2.9× on chronic kidney disease"* — true **of the 13-persona panel**. Across
   all 670 diseases the median `rank_enrichment` is **19.2×** and the max is **59.2×**. NSCLC is the
   panel's best and the population's *typical*. Presenting 19× as the high end understates the model and
   invites correction by anyone who opens the dataset.

Also: `family_auc_by_family` carries two literal `NaN` AUCs — families `51843` and `42581`, zero positives
each, so AUC is undefined. `nb3` uses pandas, which skips them, so the documented **0.8009 is a mean over
503 families presented as 505**.

> **Must not appear:** pooled AUC anywhere near the macro one (pooled overstates by ~7 points). The
> ablation ladder. Any hyperparameter. A single number in large type with no distribution beside it.

---

### Act 3 — The therapeutic area

*Why trust the list*, section 3 (built in Phase 1): the family of the disease shared with the
shortlist, or a statement that it has none. The overlap matrix, the gene coverage grid and the
shared/specific chips keep the live Act 3 plots' form, with their colours moved to token classes.

| claim | where | asserts |
|---|---|---|
| The panel | up front · every term with its 95% interval, thin terms flagged; the rest in each row's tooltip | 15 breast terms, 14 scored (macro **0.9025** over those 14; triple-negative's 8 known targets keep it out), each with its AUC and interval, known targets and, in its tooltip, enrichment. HER2+ 0.9365 / 599 · lobular 0.9337 / 513 · TNBC 0.8949 / **8** |
| **The subtypes actually separate** | up front · novel top-50 genes the selected subtype shares with each other subtype | HER2+ vs triple-negative share **2 of 50** novel genes. The lung contrast (adenocarcinoma vs squamous, **47 of 50**) has no panel on the page, so it is spoken, not shown |
| Where the panel is trustworthy | up front · the warning mark and the known-target column on the interval rows | `n_known_targets` × `auc` — AUC is meaningless below ~50 known targets, and TNBC is the visible outlier |
| Signature of each subtype's head | detail · *Shared vs. subtype-specific* chips | luminal A → EP300, ATM, MSH2, FGFR1 · luminal B → EP300, MSH6, PIK3R1, FGFR1 · TNBC → RAD50, ATM, TP53, BRCA2, NBN |

This act is why a single-disease deck does not read as cherry-picking: same model, fifteen terms of the
same area, lists that differ in a way a breast oncologist recognises. The trustworthiness scatter puts
TNBC's 8 known targets on screen *before* act 6 claims anything about it.

> **Must not appear:** TNBC as a win. Any subtype's list called *"validated"* — this act shows coherence,
> which is what a scientist checks before they check a metric, and is not validation.

---

### Act 4 — The shortlist

*The shortlist*, the home page (built in Phase 2, not yet deployed): the ranked list, then one card for
the selected candidate with five tabs — Overview, *Why this ranking?*, Trials, Literature, and Drugs &
graph.

| claim | where | asserts |
|---|---|---|
| The contract | not a block of its own: the Overview tab's *What these sources cannot tell you* carries the therapeutic-relevance clause, and the liability tooltip and note carry the safety one. The subtype clause is not on the page | the deliverable in one sentence, and **the three things it does not do** |
| The ranked list | paged table, 15 rows a page | 12,272 rows: rank, gene, class, tractability, the association badge, the drug-evidence badges and the safety badge. The SHAP drivers moved to the candidate's *Why this ranking?* tab |
| The validated filter | three checkboxes, the rank cut-off and the live funnel | **12,272 → novel 11,673 → tractable 7,950 → not secreted 7,273 → rank ≤ 200 → 38** (re-derived 2026-10-26 through the backend's own filter; previously 7,951 and 7,274) |
| Candidate detail | the card below the list: a header, then the Overview and *Why this ranking?* tabs | rank against the pool, every flag and the gene's HGNC identity in the header; the top five SHAP drivers, each with its percentile in **this disease's own distribution** |
| The drugs behind the badges | Drugs & graph tab · table under the badges | every drug that acts on the gene **and** is recorded for exactly this disease node: name, highest stage, action on the gene, DrugBank id, release. ERBB2 × HER2+: tucatinib (approval), poziotinib (phase 2). An empty table reads *no link in snapshot* |
| Trials and papers that name the gene | Trials and Literature tabs, searched when either tab is first opened | the records the searches retrieved that name the gene, then up to five of each with a role, a subtype match, a reason and a quote found in the passage; the rest listed below. Counts say *retrieved*, never *all*; a trial's phase or status is never read as efficacy |
| The mechanism, on the graph | Drugs & graph tab · shared Explorer card with five independent bounded presets | prepared interaction, pathway, molecular-function, biological-process and drug-context queries for the selected disease and gene |
| Questions about the pair | *Ask about {gene}* under the card's header opens the assistant panel; *Explore in Agent Hub* beside it opens Agent Hub in a new tab | four starter questions and a free one, answered over the graph, CT.gov and PubMed; every sentence shows its citations or the *not from a retrieved source* mark, and every graph result its Cypher |
| *How do we know?* | the intro row (all three sections); the Overview tab's model box (section 2) and association box (section 1) | links to *Why trust the list*, landing on the section |

**Selection, not two pickers.** Clicking a row in the ranked list drives the header and every tab, and
scrolls the page to the candidate card — the act's move is *judge a row, then ask why that row*, and
separate pickers would let two panels describe different genes at once. Candidate selection prepares
the five route-specific queries but does not execute one; the user chooses a preset and opens the shared
Explorer shell when ready to inspect the graph.

**Identity is preloaded from a dated HGNC file** (`DEC-DATA-002`; scope D16). The header reads
`candidate_identity` (zone S1): the graph's gene nodes left-joined, by the NCBI Gene ID the graph
carries (`graph_nodes.node_id`), to one dated HGNC complete-set file that Part 1's
`compute_hgnc_identity` loads. Nothing is fetched per click. The source line names the file and the
NCBI Gene ID it matched on, and the header warns when HGNC's current symbol differs from the graph's.
From `hgnc_complete_set_2026-10-06.txt`, 20,860 of 20,861 gene nodes match (PGM5P1's record carries no
NCBI Gene ID), 10 graph symbols have since been renamed by HGNC, and the HER2+ top 200 agree field for
field with a live HGNC lookup. A first build looked genes up live at the HGNC REST service; it was
replaced the same day.

**Drug records are the badges, kept one row per drug** (scope D7). The tab reads
`drug_evidence_records` (zone S1), built with a visual Group and Join from the same
`drug_disease_edges` and `drug_protein_edges` that `compute_drug_evidence_pairs` reduces to two flags.
It holds every linked pair (86,123 records over 55,270 pairs), so it does not depend on the scoring
chain; grouped by pair, the 2,294 records on candidate pairs reproduce both flags for all 105,702 pairs
with zero mismatches (checked 2026-10-26), so a badge and the table under it cannot disagree. The link
is exact-node: lapatinib and neratinib act on ERBB2 but are recorded on *breast cancer*, so they are
not in HER2+'s table.

**Trials and papers are retrieved for the selected pair only** (`DEC-DEMO-004`; scope D3–D6). Opening
the Trials or Literature tab runs six Cortex searches, three queries on each corpus, each leading with the
gene, and keeps a record only if the gene or a safe alias appears outside a citation. The records show at
once; two LLM calls, one per corpus over the text around the gene's mentions, then pick up to five of each
and label them. Every label carries a quote the backend finds in the record's full passage, or it is
dropped and counted; the record stays, unlabelled. Search and selection are cached per pair in
`act4_evidence_cache`, so a second visit reads the file (0.16 s); **Refresh** re-runs it. Measured on
ERBB2 × HER2+: 3.2 s of searches and 11.4 s of selection, inside the 4 s and 15 s budgets. The
`prefill_evidence_cache` scenario fills the HER2+ top 20 and SMARCA2 before a demo.

**The assistant answers about the selected pair, and the backend checks every answer** (`DEC-DEMO-004`;
scope D1). Each question is sent with the pair's identity, its top five drivers, its drug records and its
cached trials and papers, each with a reference the model must cite. The model may search the graph,
CT.gov and PubMed itself, at most 8 times in 45 s. When the answer is complete the backend resolves every
citation to a record or a search result from this answer, removes any that resolve to nothing, marks
every uncited sentence *not from a retrieved source*, flags prescriptive phrases and attaches each graph
search's Cypher. The check verifies that a citation exists, not that the sentence is true. Conversations
live in the page and are lost on reload. Measured on ERBB2 and SMARCA2 × HER2+: 2.9–24.7 s per answer.
For open exploration, *Explore in Agent Hub* opens a separate Agent Hub webapp running the DSS agent
`target_evidence_assistant` over the same three tools; it does not know the pair, its answers are not
checked, and it keeps its own conversation history.

**Why this ranking? lists only the top five drivers** (scope D2). The tab shows the five features with
the largest SHAP values, each with its sign and size and where this gene's value sits in this disease's
pool; the champion's other nine inputs are in the glossary. They come from `candidate_shap_top5` (zone
S1), a second scoring run of the champion with five explanations beside the run that sets the rank; it
scores every pair identically, and its two strongest drivers equal the stored `top_shap_drivers` on all
105,702 pairs (2026-10-26). The Overview tab's strongest driver reads the same list. Percentiles are
computed in the flow by the rule `/gene` uses, so `prox_kernel`, which never reaches
`dashboard_candidates`, now has one. When a driver has no value — no such path for this gene — the
tab says the contribution is its absence. The feature wording comes from `backend/feature_glossary.py`,
so it moves when the champion does.
webapp v1's drawer had shown three features — `rwr_score`, `ppi_common_neighbors`,
`shared_pathway_count` — that are **not inputs to m7-f14**, which is why the set is derived, never
curated.

**Percentile direction is per feature.** The bar is the share of this disease's pool the candidate is
*stronger* than — a higher value everywhere except `prox_closest`, where fewer hops is stronger.
Ranking hop distance upward like the rest put a gene one hop from the disease module at the 0th
percentile and drew it an empty bar, which reads as *no evidence* for the best value the feature can
take. Ties count toward neither side.

The three *does not do* clauses — no safety axis, no morphological subtype resolution, association
ranking does not predict therapeutic relevance — go **here, on the page that carries the deliverable**,
not held to act 6. A vendor who leads with its limits has bought the right to be believed.

**Thirty-eight is a shortlist a team clears in a week.** State the rank cut-off as part of the definition
— the count is meaningless without it, which is how the obesity version acquired two conflicting values
(§10.3).

**Five routes, and only four are features.** The mechanism card offers one independent, bounded preset
per evidence route — interaction (`dwpc_GGD`), shared pathway (`dwpc_GPGD`), shared molecular function
(`dwpc_GFGD`), shared biological process (`dwpc_GBGD`) and the drug route. It neither combines their
result shapes nor reports route presence, absence or edge counts before the Explorer executes the chosen
query. The two GO presets cap the mediator term's degree at 200, so a hub such as *protein binding* does
not dominate the displayed context.

The drug route carries the §4 caveat **on the card**: no model feature traverses a drug node, so
nothing on it fed the score, but it is one of three routes admitting a pair into the candidate pool.
*Not a feature*, never *not used*. Only `indication` and `drug_investigated_for` exist in this graph —
contraindication was never built.

**The on-graph shot.** The Visual Graph Explorer is the interactive surface, not a Target Prioritizer
query recipe or canvas. The shared card exposes the generated query and links to the Explorer in a new
tab; the user copies, pastes and runs it there. Traversal is **undirected**, relationship variables are bound
and returned, and the graph label for genes is `protein`. Node indices are snapshot-specific, so the Act 4
presets are generated from the selected live candidate row rather than copied from documentation.

```cypher
// Why the head of the HER2+ list? The PI3K/AKT + RAS-MAPK axis, and its
// interaction evidence to genes already annotated for this disease.
MATCH (D:disease {node_index: 48537})
MATCH (g:protein) WHERE g.node_index IN [91764, 91759, 88097, 89095, 84123, 84431, 93120]
MATCH (g)-[ppi:protein_protein]-(m:protein)-[assoc:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, ppi, m, assoc, D LIMIT 300
```

`91764` PIK3R1 #3 · `91759` PIK3CA #5 · `88097` **HRAS #9, novel** · `89095` KRAS #10 · `84123` EGFR #11
· `84431` **ERBB2 #14** · `93120` MAPK1 #15.

One connected module, the disease's own annotated genes in the middle of it, and a novel candidate (HRAS)
inside the same mechanism as the approved target. That is the second of the deliverable's two
explanations, and the shot the deck exists to reach.

⚠ If you also show the drug path (`gene ← drug → disease`): no model consumes it as a feature, but it
**is** one of three routes admitting pairs to the candidate pool, so it shapes the scored population. Say
*"not a feature"*, never *"not used"*.

> **Must not appear:** any AUC. The `prediction` column. Any filter control on the drug badges or the
> liability flag. The feature column list — show the *paths*.

---

### Act 5 — The interrogation *(talk track — figure set, not a route)*

Every card carries the HER2+ number **and** the across-670 number. That pairing is what stops a
single-disease deck from being a single-disease anecdote.

**"These are just the famous genes."**

| card | asserts |
|---|---|
| Fair fight, not a rigged one | **2.9× / 2.7× / 2.4×** at K=10/50/200 against **equally-connected** genes |
| The direction nobody volunteers | below rank 20 the degree control makes us look **better**; at rank 10 **worse** — and we say so |
| The harder version | known targets only, by connectivity quintile: score 0.59 → 0.79, detection 17.3% → 57.0%. **3.3× swing, biology held constant** |
| What it costs you | *"we will find you targets adjacent to biology you already know; we will not fix your neglected-gene problem"* — and that we tested the obvious cause and it was **not** the cause |

Two findings, opposite directions, both true: the *ranking* is not explained by popularity, **and** the
model still under-scores under-studied true targets. Never merge them into one number.

**"You already knew all of these."**

| card | asserts |
|---|---|
| Delete the answer key | 12,272 scored → 599 known → **11,673** re-ranked |
| The novel head | **HRAS at #9**, MAPK3 at #61 — nothing in the training label pointed at either |
| Lift vs K, by ground truth | approved 16.9× → 5.0× ; investigational 7.4× → 4.0×, decaying to a ~4× floor |
| Where the mean comes from | the per-disease distribution behind 16.9× |

**The distribution card is not optional.** 16.9× is a *mean of per-disease lifts on a heavy-tailed
distribution* — Sjögren syndrome alone is **252.4×** at top-10, and the notebook drops infinities before
averaging. A scientist who asks *"is that a median?"* and gets an evasive answer has ended the demo.

**"Your ground truth is garbage."**

| card | asserts |
|---|---|
| How the pairs are manufactured | the data says *drug treats disease* and *drug hits targets*, never *target treats disease*. A drug hitting 40 proteins approved for 13 diseases manufactures 520 "validated" pairs |
| How bad it is | **82%** of validated pairs come from multi-target drugs; **8%** survive a single-target demand |
| Re-run on a curated source | **21.3×** vs 16.9× — the finding got **stronger** |
| Association ≠ therapeutic relevance | one point per disease, association AUC × therapeutic AUC. **r = +0.002** |

The scatter is the best single visual in the deck: two axes, a visibly flat cloud, the fit line on the
horizontal. It turns an abstract caveat into something the room sees in one second. **Ship the picture,
not the *r*.**

> **Must not appear:** the two ground truths merged into one "enrichment" series. The drug-target
> benchmark as a score — it belongs in act 6.

---

### Act 6 — The limits, and the punch line *(talk track — figure set, not a route)*

**Part one: the limits.**

| card | asserts |
|---|---|
| Molecular subtype: **resolvable** | HER2+ vs TNBC share **2 of 50** |
| Morphological subtype: **not** | lung adenocarcinoma vs squamous share **47 of 50** |
| The hard case | TNBC: RAD50 #1, ATM #2, TP53 #3, BRCA2 #4, NBN #5 — coherent HR panel, **all novel**, **8** known associations, so unscoreable |
| The secreted lean | `pct_secreted_top50` vs `pct_secreted_all` — where it happens and where it does not |
| No safety axis | we do not have one and are not pretending to |

The two overlap cards must sit **side by side**. Separated, the act reads *"it cannot tell subtypes
apart"*; adjacent, *"we know which kind of subtype it resolves and which it does not"* — a stronger
statement and the true one.

TNBC is also where the MRN complex lands (RAD50 #1, NBN #5). A graph shot here is the double-strand-break
repair module, framed as *"a coherent list we cannot validate"*, never as a second success.

> **Must not appear:** TNBC as a success story. **Read [`BREAST_SURGEON_BRIEFING.md`](BREAST_SURGEON_BRIEFING.md)
> before this act goes in front of a clinician.** Any safety or toxicity claim of any kind.

**Part two: the punch line.** Every value read off the live dataset.

| card | asserts |
|---|---|
| "Use druggability as a model input" | two bars per class, **pointing opposite ways**. Membrane receptor: `drug_lift` **3.16**, `assoc_lift` **0.78** — 3.2× more likely to be a real drug target, 1.3× *less* likely to be disease-linked. The model would have learned *"membrane receptor → score lower"* |
| "Filter out genes the body cannot live without" | intolerant genes: `assoc_lift` **2.07**, `drug_lift` **1.37** — **both above 1**. We predicted drug targets would avoid them; the measurement went cleanly the other way |
| "Exclude known safety liabilities" | flagged genes carry `drug_lift` **4.62** — liabilities are discovered *by* drugging something, so the flag marks the best-studied targets |
| **The ten-second check** | **9 of the HER2+ top 15 carry a liability flag — including ERBB2 at #14.** That filter deletes the target this disease is named after |
| What it costs across the funnel | `filter_three_axes`, stage by stage, per disease |
| The slide no vendor shows you | a lookup table — *"how many diseases is this gene already a drug target for"* — scores **0.9354** and **beats our trained model**, so we refused to headline that benchmark |

The lookup-table card is **deliberately prose, not a chart**. We decline to compete on that benchmark;
giving it an axis promotes it to a scoreboard.

**The close.** Three ideas every biologist would have approved, each killed by one recipe, each still in
the flow with its verdict attached. *"You do not need a better algorithm. You need somewhere your
biologists' hypotheses get tested in an afternoon instead of argued about for a quarter."* Then where
their own knowledge enters: failed internal programmes (trial-stage evidence is **13×** larger than
approved-drug evidence and is the fairer test — and nobody publishes their failures), internal assay
data, their own disease definitions, expert thresholds. The public data buys the genetic-evidence effect —
genetically supported targets are 2.6× more likely to survive the clinic *(Minikel et al., Nature 2024)*.
**Their own graph is the only place the rest of their institutional knowledge can enter the ranking.**

> **Must not appear:** any of the three framed as a modelling subtlety. Each is *"a plausible idea,
> measured, refuted, recorded"* — that shape is the argument. No roadmap implying the four plug-ins are
> built.

---

## 5. Where the customer's own knowledge already enters

The strongest thing in the deck that is not a number: **the train/test divide comes from a curated
medical ontology, not an algorithm.** A biologist's judgment — *"type 2 diabetes and diabetes mellitus are
the same programme, do not let them straddle"* — became a rule in the pipeline and **lowered** the honest
score. Domain expertise compiled into a control, already built, and the template for everything the
customer would plug in. It belongs in act 2 beside the split audit, and is called back in act 6's close.

---

## 6. Guardrails the code must enforce

Native DSS could implement none of the first three. In our own components they are trivial — which is why
the pivot matters more than it looks.

| the default move | why it breaks | what the app does |
|---|---|---|
| Expose `prediction` beside `score` | 590 of 762 known obesity targets are negative at the F1 threshold | never fetched; not in the API response |
| Let the drug badges be filterable | the discovery lift is measured *against those labels* — filtering makes it circular | rendered as badges; no filter control, and a tooltip saying why |
| Let the liability flag be filterable | it would delete ERBB2 from its own disease's list | same, plus act 6 shows the cost |
| `AVG(lift_top10)` in a chart | Sjögren is 252.4× and the notebook drops infinities first | the aggregate carries mean, **median** and **n**, inf-drop explicit, distribution shown beside it |
| Open with the AUC | answers a question they did not ask | act 2 leads with the distribution; no single number stands alone. **Planned** (`DEC-DEMO-005`): the app opens on the list, which shows no AUC |
| One "enrichment" series | approved and investigational mean different things | never OR'd, never merged, separately labelled |
| Report pooled AUC because it is bigger | pooled overstates by ~7 points | macro only, never adjacent to a pooled figure |
| Quote a filtered count without its rank cut-off | how the obesity landing count acquired two values (§10.3) | every funnel count renders its cut-off in the same component |
| A number with no provenance | undercuts the platform claim the deck closes on | §3.2 — every card footers its source dataset |
| A tooltip-free "novel" or "no liability" label | *"novel"* reads as *undiscovered*, *"no liability"* reads as *safe* — both wrong | the old webapp's `TIPS` copy ports across verbatim |
| A discovery-enrichment figure on a summary tile or opening screen | the narrative makes a **reconstruction** claim, not a discovery one; a headline number turns one into the other and the slide is not recoverable in the room | the enrichment lives below the fold in act 4, labelled as an observation, and appears on no tile |
| A headline number typed into card copy | act 2 carried a literal `1.9%` positive rate and a literal `0.9776` accuracy while their neighbours read live from `data.champion`, so a retrain made one card contradict itself on screen. Two proposed subtitles asserted *"most PPIs are corroborated"* (16.6% are) and *"provenance features dominate"* (path features are collectively larger) — both written from intuition, both false, both plausible enough to survive an eyeball review | every figure in a title, subtitle or note is derived from the payload; a claim that cannot be derived is not made. Where a card figure has a canonical value here, the card matches this document's precision, not its own rounding |
| Language that prescribes research direction — *"you should pursue…"*, *"the next target is…"* | we are a platform company, not a domain authority. Prescribing costs the room | the app ranks and explains; every verb in the copy is about evidence, never about what to do next |
| *Built, preview webapp* (`DEC-DEMO-004`): an assistant sentence from general knowledge rendered like a sourced one | the LLM's background knowledge reads as retrieved evidence, and the careful parts of the demo stop being trusted with it | every sourced sentence cites a record; a general-knowledge sentence is marked *not from a retrieved source* and is never a citation; a graph answer shows its Cypher |
| *Built, preview webapp* (`DEC-DEMO-004`): an LLM role label taken on trust | a label with no checkable basis is an unreviewed claim about a paper or trial | every label carries a quote the backend finds in the passage after whitespace normalisation; a label that fails is dropped and the record stays, unlabelled |
| *Planned*: "no drug" inferred from a missing drug link | drug links are exact-node: lapatinib's and neratinib's approvals sit on *breast cancer*, not on the HER2+ subtype | the copy says *no link in snapshot*, never *no drug* |

---

## 7. What is deliberately absent

- **The ablation ladder** (7 → 10 → 12 → 14 features). No card. A modelling decision that invites a
  hyperparameter conversation.
- **Feature engineering internals.** No feature-list card anywhere. Show the *paths*.
- **The drug-target benchmark as a score.** Act 6 prose only.
- **Any safety or toxicity claim.** Saying we have none is worth more than faking one.
- **Retired diseases.** Type 2 diabetes and two of the three lung terms never appear in a default
  selection. Chronic kidney disease appears **once**, as act 2's honest low end.

---

## 8. Chrome, and what the app is not

- **No login, no user management, no persistence.** This is a demo surface over read-only flow output.
- **No writes to DSS.** The one exception worth considering later is act 3's clinician review form
  (`breast_shortlist`), and it is out of scope until someone asks. **Exception, built on the preview
  webapp** (`DEC-DEMO-004`): retrieved trials and papers, with their selection, are cached per (disease,
  gene) pair in the managed folder `act4_evidence_cache`. The in-app assistant's conversations are never stored; Agent Hub, a separate
  webapp linked from the card, stores its own (`DEC-DEMO-004`).
- **No LLM anything.** A chatbot over a ranked gene list is the kind of thing that makes a careful
  audience stop trusting the careful parts. The template's chat block, like its other optional blocks
  (wizard, charts, flow, documents), was never enabled and was deleted on 2026-10-15, together with the
  `ENABLE_*` flags ([`BLUEPRINT_ALIGNMENT_PLAN.md`](../../archive/BLUEPRINT_ALIGNMENT_PLAN.md), Phase 0). Every routed
  view is an act or Settings. **Exception** (`DEC-DEMO-004`): on the shortlist only, one LLM selection
  step (two calls, one per corpus) picks and labels retrieved trials and papers — built on the preview
  webapp — and an evidence assistant, also built there, answers over the same sources, both on the terms §6
  enforces. The reasoning above still holds everywhere else: no other
  surface uses an LLM.

---

---

## 9. The analytic reasoning behind each claim

The narrative makes claims. This is what each one rests on — the measurement, why it was designed that
way, and where it is re-derived. **Anything not in this table is not defensible in the room.**

### 9.1 Act 2 — "it is not just the famous genes"

**The problem.** Well-studied genes carry more edges in every biology database, so any graph model
drifts towards them. A raw enrichment figure measures the drift, not the model.

**The design.** Compare each top-ranked gene against genes with the **same network degree**, not
against the pool average. Degree quintiles are computed once over distinct genes, and the expected
count at rank K is the sum of the quintile rates the top K actually occupy — so a head full of hubs
is scored against hubs.

**Why both a pooled and a macro figure.** Pooled sums observed and expected across all diseases;
macro averages per-disease lifts. They disagree at small K because a handful of large diseases
dominate the pooled sum. Reporting one alone hides the disagreement, which is itself the finding —
the crossover point (pooled at K=20, macro at K=50) is where controlling for degree starts to make
the result look *better*.

| claim | value | re-derived in |
|---|--:|---|
| pooled degree-matched lift @10 | 3.29× | `nb6` §5.1, `nb4` §8.4 |
| pooled degree-matched lift @200 | 2.42× | same |
| macro degree-matched lift @10 | 3.11× | same |
| crossover: dm > naive | pooled K=20, macro K=50 | asserted as booleans, so it cannot drift silently |

**The counter-measurement, and why it belongs next to it.** Hold biology constant — known targets
only — and the model still scores the lowest degree quintile 0.59 against 0.79 for the highest. The
ranking is not explained by popularity *and* the model under-scores under-studied true targets. Both
are true; a claim that omits the second is the one that gets caught.

### 9.2 Act 2 — "macro, never pooled"

Pooled per-disease AUC reads **0.8932**; macro reads **0.8230**. The gap is ~7 points and it is not
noise: pooled lets one large disease carry many small ones. **The macro figure is the honest one and
the only one that goes in front of anybody.** Both are asserted in `nb3` so the gap itself is guarded.

### 9.3 Act 3 — the family split

The train/test divide is by **disease family from a curated ontology**, not by random assignment.
Random splitting puts "diabetes" and "type 2 diabetes" on opposite sides — same programme, different
label — and inflates the score. Family-level macro AUC across 505 families is **0.8009**, and zero
split keys straddle.

This is also the concrete example of customer knowledge entering the pipeline: a biologist's judgment
about which terms are the same programme became a rule that *changed the honest score downwards*.

### 9.4 Act 4 — the eyeball test, and the footnote beneath it

**The primary measurement is reconstruction fidelity, and it is per-disease.** HER2+ reconstructs its
known targets at AUC **0.9365**; that is the number Act 4 is built to make visible, because a
clinician recognising the top of the list is worth more than any aggregate.

**The secondary measurement — kept, demoted, and fenced.** Remove every known target for a disease,
re-rank the remainder, and the novel head is enriched for genes that later prove to be real targets:

| ground truth | @10 | @200 |
|---|--:|--:|
| approved drugs | 16.88× | 5.04× |
| drugs in trials | 8.85× | — |
| curated target–disease | 21.32× | 5.23× |

**The UI must not let this become the headline.** It is the one number that can turn a reconstruction
pitch into a discovery pitch, and the narrative explicitly does not make a discovery claim. Present it
where it cannot be mistaken for the main result — below the fold of Act 4, labelled as an observation,
never on a summary tile or an opening screen.

The curated row is the interesting one for a different reason: it answers *"your ground truth is
manufactured"* by re-running on a source that asserts the target–disease link directly, and the result
gets stronger rather than weaker.

### 9.5 Acts 5–6 — three hypotheses, settled by measurement

**What this demonstrates is turnaround, not insight.** Each hypothesis was settled by one recipe, and
the record of why sits in the flow. Whether a given hypothesis is worth testing is the customer's
call — the platform claim is only that testing it costs an afternoon.

Each was tested by measuring enrichment against **two labels on the same rows**: `is_target`
(disease-linked — what a model trained on association learns) and drug-validated (what a programme
actually wants). In every case the two point in different directions.

| gate | association lift | therapeutic lift | verdict |
|---|--:|--:|---|
| membrane receptor as a feature | 0.78× | 3.16× | REJECTED — the model would learn "score lower" |
| ion channel *(same shape, larger)* | — | 11.89× | — |
| filter out LoF-intolerant genes | 2.07× | 1.37× | REJECTED — enriched on **both** |
| exclude safety liabilities | — | 4.62× | REJECTED — the flag marks the best-studied targets |

**The restriction that makes this valid:** both labels are measured on exactly the same rows — the
907,246 scored pairs belonging to diseases with at least one drug-validated target. Measuring them on
different populations would make the comparison meaningless, so the row count is itself asserted.

**The ten-second version for the room:** 9 of the HER2+ top 15 carry a liability flag, and one of them
is ERBB2 — the target of trastuzumab.

### 9.6 The orthogonality result, and why it is a warning not a score

Association AUC and drug-target AUC are uncorrelated across diseases: r = **+0.002**, R² = **0.0000**.
A disease the model ranks well on association tells you nothing about whether it ranks drug targets
well.

This is why the drug-target benchmark is never a headline: a no-graph popularity lookup beats a
trained model on it. **A benchmark a lookup table wins is measuring the lookup.** Report it as a
warning flag; never optimise against it.

---

## 10. Flow lineage

[`FLOW_MAP.md`](../operations/FLOW_MAP.md) is the generated authority for zones, datasets, producers and consumers.
Read it before pruning or changing a backing contract; do not duplicate it here. In particular, use its
notebook-provenance and zone-membership rules rather than reference counts to judge whether a serving
dataset is safe to remove.

---

## 11. Known corrections carried into the narrative

- **The MRN anchor shot is a TNBC observation, not a HER2+ one.** RAD50 / NBN / MRE11 rank 55, 99, 401
  on HER2+ and 1, 5, 702 on TNBC. The narrative now says to re-derive the cluster on the disease being
  demoed rather than quoting the remembered version.
- **Do not quote 82% / 8% for ground-truth inflation.** Measured at source it is ~87.5% / ~12.5%, on a
  different denominator. `nb6` deliberately does not assert the older pair.
- **`scored_champion` is a 45-column CSV**, so column-pruned reads still stream all 45. It is why the
  validation scenario takes ~14 minutes. Converting it to parquet is the highest-leverage remaining
  change, and it needs its own rebuild rather than riding along with something else.
