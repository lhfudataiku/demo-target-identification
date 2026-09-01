# Webapp design — the technical companion to the demo narrative

<!-- Governed claims consumed here: TI-DATA-001 TI-MOD-001 TI-VAL-001 TI-VAL-002 TI-VAL-003 TI-VAL-004 TI-VAL-005 TI-VAL-007 TI-VAL-008 TI-VAL-009 -->

> **Lifecycle:** Canonical · **Audience:** webapp implementers and technical reviewers · **Authority:**
> Vue/FastAPI architecture, routes, state, interaction and data contracts · **Update when:** an app
> contract, route, interaction or backing-data contract changes · **Generated dependencies:**
> [`FLOW_MAP.md`](FLOW_MAP.md) for live flow lineage, the notebook assertions cited in §9 and
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

**What the demo surface is.** A single Vue SPA deployed as a DSS STANDARD webapp, built from the
`bs-blueprint` template. **Four acts in the app; acts 5 and 6 are a spoken talk track**, because they
are about the platform rather than the biology.

**Status.** Mockup iteration 3 — [`DASHBOARD_MOCKUP_V3.html`](DASHBOARD_MOCKUP_V3.html) is the current
artefact. Earlier iterations are historical material in
[`../../archive/dashboard-mockup-iterations/`](../../archive/dashboard-mockup-iterations/).

**Where the rest lives.** [`FLOW_MAP.md`](FLOW_MAP.md) is the generated flow authority. Historical
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

Copied from `~/Documents/GitHub/bs-blueprint` via `make copy DEST=…`. Vue 3 + Vite + Tailwind 4 +
ECharts + Pinia + vue-router, with a FastAPI backend and `dss_webapp/deploy.sh`, which builds the bundle,
uploads `backend/` and `frontend_dist/` into the project library under `python/<LIB_NS>/`, and patches a
STANDARD webapp definition to serve it.

**What we get for free that the native route could not give us:** routed acts with a sidebar that builds
itself from route `meta`; real prose beside real charts; display-only columns; row-level drill; a single
deploy command; and a design system already themed to the Dataiku brand.

### 3.2 The lineage rule — non-negotiable

A custom app is opaque to lineage, and act 6 closes on *"the record of why is in the flow, not someone's
inbox."* A screenshot-grade SPA would undercut the pitch it exists to deliver. So:

> **Every card that states a number names its source dataset in a footer, and every act carries a link
> into the flow zone that produced it.**

Provenance moves *into* the UI rather than being borrowed from native tiles. This is a first-class design
requirement, not a nice-to-have: it is what lets us claim the platform while shipping custom code. The
mockup implements it as a `dataset · recipe` footer on every card.

### 3.3 Route → view → data map

Sidebar order is act order. `menu: 'primary'`, `order` = act number.

| act | route | view | data module | backing datasets |
|---|---|---|---|---|
| 1 | `/evidence-base` | `EvidenceBaseView` | `mock/graph-inventory.ts` | `graph_nodes`, `graph_edges`, `edge_metadata` |
| 2 | `/calibration` | `CalibrationView` | `mock/calibration.ts` | `validation_auc_by_disease_2` **(filter `level='disease'`)**, `family_auc_by_family`, `split_audit_2`, `persona_candidates` |
| 3 | `/therapeutic-area` | `AreaPanelView` | `mock/breast-panel.ts` | `breast_panel_metrics`, `breast_panel_overlap` |
| 4 | `/shortlist` | `ShortlistView` | `mock/her2-candidates.ts` | `dashboard_candidates` (spine disease) |
| 5 | `/interrogation` | `InterrogationView` | `mock/interrogation.ts` | `novel_discovery_eval`, `tractability_axis`, `drug_target_benchmark`, + §9 gaps |
| 6 | `/limits` | `LimitsView` | `mock/limits.ts` | `tractability_lift`, `safety_lift`, `filter_three_axes`, `breast_panel_overlap` |

Act 4 absorbs the existing hand-written webapp (`V2ZpfdV`, 1,086 lines): the disease picker, the
three-clause filter with its live count, the class lanes and the detail drawer are all ported to Vue
components rather than rewritten. Its `SECRETED` rule, its `TIPS` copy and its refusal to fetch
`prediction` are **validated behaviour** — carry them across verbatim and re-read the comments before
changing any of them. **One exception, found on the port:** the drawer's five-feature list is stale
against the current champion and must NOT be carried across — see act 4 below.

### 3.4 Mock first, then swap

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

From the blueprint's agent instructions (`AGENTS` at its repo root); violating them means the app stops looking like a Dataiku product.

- **Never hardcode colors.** Tailwind utilities over the tokens in `styles/tokens.css` —
  `bg-background`, `text-muted-foreground`, `border-border`, `bg-primary`, `text-destructive`. No hex, no
  `text-[#…]`. Chart series use `--chart-1..5`.
- **Let the sidebar build itself.** Add an act by adding a route with `meta: { title, icon, menu:
  'primary', order }`. Never hand-build a menu array.
- **`apiUrl()` for every call.** A bare `fetch('/api/…')` breaks inside the DSS iframe.
- **`Ea*` primitives first** (`EaSelect`, `EaButton`, `EaEmpty`, the `table/` and `scroll-area/` sets)
  before custom markup. Icons from `lucide-vue-next`.
- **No binary assets.** DSS libraries are text-only — no `.png`, no logo files.
- **One view + one route + one backend route file + one service file.** Replace the example view; do not
  accrete beside it.
- Python: `from __future__ import annotations`, type hints, `routes/` parses and returns JSON while
  `services/` does the Dataiku calls, DSS access via `get_project()` from `dss_client.py`.

### 3.6 Build and deploy

```bash
make copy DEST=~/Documents/GitHub/target-prioritizer-app   # seed from the blueprint
make dev                                                    # vite + backend, local
make deploy                                                 # build, upload libs, patch the webapp
```

`PROJECT_KEY=DEMO_TARGET_IDENTIFICATION` in `app.env`, plus `LIB_NS` / `APP_PREFIX` /
`VITE_APP_NAME`. First deploy creates the webapp and writes its id back to `app.env`.

---

## 4. The four acts, and the talk track

| act | what it establishes | why it must precede the next |
|---|---|---|
| **1** | **The evidence base** — the graph, and that every edge knows where it came from | the model can only see what is in here; act 4's mechanism shot pays this off |
| **2** | **Scope and calibration** — 670 diseases, the *spread*, where HER2+ sits in it | *"can I trust this for my disease"* is answered before any gene is shown |
| **3** | **The therapeutic area** — the 12-term breast panel, and that the subtypes separate | the team sees itself; act 4's single disease stops looking cherry-picked |
| **4** | **The shortlist** — the list, the filter, the SHAP, the pathway | the deliverable |
| **5** | **The interrogation** — famous genes, novel discovery, the ground truth | every objection, answered on the spine disease *and* across 670 |
| **6** | **The limits and the punch line** — TNBC, then three refuted ideas | what makes acts 1–5 believable, and the platform close |

---

### Act 1 — The evidence base

| card | form | asserts |
|---|---|---|
| Node inventory | treemap | **113,391** nodes over 8 types: disease 27,153 · biological_process 23,974 · gene/protein 20,861 · phenotype 19,120 · molecular_function 10,041 · drug 5,282 · cellular_component 4,077 · pathway 2,883 |
| Relation inventory | horizontal bars | **2,851,510** edges over **18** relations. Verified live against `GRAPH_BUILDING.md` §7.1 — protein_protein 520,380 · phenotype_protein 487,054 · disease_phenotype_positive 380,280 · disease_protein 378,888 · bioprocess_protein 251,808 · cellcomp_protein 186,806 · molfunc_protein 156,246, **all seven match exactly** |
| **Every edge knows where it came from** | stacked bars | of 520,380 protein interactions: menche 189,982 · string 151,254 · huri 92,536 · menche+string 54,554 · huri+menche 28,478 · all three 2,714 · huri+string 862. **86,608 (16.6%) are corroborated by more than one independent interactome, and the graph records which** |
| **What "known target" actually means** | donut | of 323,786 annotated disease–gene edges: genetic_association **171,810** · somatic_mutation **150,266** · both **1,710**. These edges *are* the training label |
| Accepted against a frozen reference | stat row | nodes −0.13%, edges −0.03%, **14 of 18 relations reproduce exactly**, identical relation inventory |
| Explore the graph | link out | the `graph search` explorer (`wBcApLN`), which act 4 returns to |

**The provenance data is two disjoint stories.** `edge_metadata`'s 844,166 rows split cleanly: 520,380
protein_protein rows carry `ppi_sources` with blank `datatypes`; 323,786 disease_protein rows carry the
reverse. Two cards, two filters, and **both filters are load-bearing** — unfiltered, each chart shows the
other block as one blank category three times the size of any real one.

The second card was not in the original design and is the more valuable. *"Known target"* is the phrase
the whole deck rests on, and this says what it means: 53% genetic association, 46% somatic mutation. It
defuses part of act 5's ground-truth objection four acts early.

⚠ **`disease_protein` has 378,888 edges but only 323,786 metadata rows** — 55,102 (14.5%) carry no
evidence-type annotation. Do not describe the donut as covering all disease–gene edges.

> **Must not appear:** the build pipeline, recipe counts, how long it took. No model, no score — the model
> has not been mentioned yet.

---

### Act 2 — Scope and calibration

| card | form | asserts |
|---|---|---|
| **Zero straddling keys — read this first** | table | 3 rows; all four overlap/straddling columns at **zero** across train (2,187,862 rows / 383 diseases), validation (3,958,921 / 670), test (607,345 / 104) |
| The spread across 670 diseases | histogram, 20 bins | macro **0.8230**, median 0.8623, range 0.1045–0.9962 over the **668** that score |
| It holds across 505 families | histogram, 20 bins | macro **0.8009** over the **503** that score |
| **Usefulness is not uniform** | box plot | rank enrichment median **19.2×**, quartiles **9.1–28.2×**, range **0–59.2×** across 670 diseases |
| Where your disease sits | marker on the histogram | HER2+ at **0.9365** — upper tail, stated as a *position in a spread* |

**The framing rule.** The distribution leads; the macro number is its summary. The narrative forbids raw
AUC as an opening number — *"it is the answer to a question they did not ask"* — and the TxGNN result is
why: showing experts *why* raised their accuracy 46% and confidence 49%; accuracy alone moved neither. A
scoped-POC team's real question is **can I trust this for my disease**, which is about spread and
position, not a mean.

The audit card is placed first, full width, ahead of every AUC. The AUCs mean nothing until the straddling
count is zero, and the layout enforces the reading order.

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

| card | form | asserts |
|---|---|---|
| The panel | table | 12 breast terms: pool, known targets, AUC, hits@50, enrichment, verdict. HER2+ 0.9365 / 599 · lobular 0.9337 / 513 · TNBC 0.8949 / **8** |
| **The subtypes actually separate** | paired stat | HER2+ vs triple-negative share **2 of 50**; lung adenocarcinoma vs squamous share **47 of 50** |
| Where the panel is trustworthy | scatter | `n_known_targets` × `auc` — AUC is meaningless below ~50 known targets, and TNBC is the visible outlier |
| Signature of each subtype's head | small multiples | luminal A → EP300, ATM, MSH2, FGFR1 · luminal B → EP300, MSH6, PIK3R1, FGFR1 · TNBC → RAD50, ATM, TP53, BRCA2, NBN |

This act is why a single-disease deck does not read as cherry-picking: same model, twelve terms of the
same area, lists that differ in a way a breast oncologist recognises. The trustworthiness scatter puts
TNBC's 8 known targets on screen *before* act 6 claims anything about it.

> **Must not appear:** TNBC as a win. Any subtype's list called *"validated"* — this act shows coherence,
> which is what a scientist checks before they check a metric, and is not validation.

---

### Act 4 — The shortlist

| card | form | asserts |
|---|---|---|
| The contract | prose | the deliverable in one sentence, and **the three things it does not do** |
| The ranked list | virtualised table | 12,272 rows, rank + percentile + score + SHAP drivers + status badges |
| The validated filter | three checkboxes + live count | **12,272 → novel 11,673 → tractable 7,951 → not secreted 7,274 → rank ≤ 200 → 38** |
| Candidate detail | card, follows the selected row | rank against pool, SHAP drivers, **every champion feature** against **this disease's own distribution** |
| The mechanism, on the graph | five merged route queries + rendered subgraph | every evidence route from the selected gene to the disease's own annotated genes, counted per route |

**Selection, not two pickers.** Clicking a row in the ranked list drives BOTH cards and scrolls the
page to the detail card — the act's move is *judge a row, then ask why that row*, and separate pickers
would let the drawer and the subgraph describe different genes at once. The subgraph is the one thing
that does **not** follow automatically: it costs a DSS round-trip (~2.7 s), so it waits for its own
button rather than firing once per row while someone scans the list.

**The detail card shows the champion's own inputs, not a selection.** webapp v1's drawer showed five
features, of which three — `rwr_score`, `ppi_common_neighbors`, `shared_pathway_count` — are **not
inputs to m7-f14**; they are columns `dashboard_candidates` happens to carry. A non-feature under the
heading *"why this gene?"* answers a question the model never asked, so the set is derived from
`backend/feature_glossary.py` and moves when the champion does. One champion input, `prox_kernel`,
never reaches `dashboard_candidates`, and the card says so rather than showing 13 of 14 as if that
were all of them.

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

**Five routes, and only four are features.** The mechanism card runs one query per evidence route —
interaction (`dwpc_GGD`), shared pathway (`dwpc_GPGD`), shared molecular function (`dwpc_GFGD`),
shared biological process (`dwpc_GBGD`), and the drug route — and merges the subgraphs by node and
edge id. The per-route edge counts are part of the answer: *"no pathway route"* is a fact about the
candidate, not a gap in the picture. The two GO routes cap the term's own degree at 200, or a hub like
*protein binding* matches everything and means nothing.

The drug route carries the §4 caveat **on the card**: no model feature traverses a drug node, so
nothing on it fed the score, but it is one of three routes admitting a pair into the candidate pool.
*Not a feature*, never *not used*. Only `indication` and `drug_investigated_for` exist in this graph —
contraindication was never built.

⚠ **The single-query form does not run in the webapp, and the card says so.** Written as one query with
an `OPTIONAL MATCH` per route it is the natural form, and the **Visual Graph Explorer returns it in
about a second** because it talks to Kuzu directly. The webapp's only path is the graph agent tool
(`b6Rpbve`), whose Kuzu runs in a memory-capped kernel: the chained clauses *multiply* rows rather than
adding them, `LIMIT` bounds the output and not the join, and the engine answers
`Buffer manager exception: the buffer pool is full` after 68–108s (reproduced on three warm attempts;
an earlier run reported `Interrupted` at 173s). Hence five queries here, issued concurrently, ~4s warm.
**The card renders the merged canvas and its copy button hands over the single query for the Explorer** —
the constraint is ours, so it should not be exported to the person holding the mouse.

⚠ **Cold start.** The first call after the graph tool has been idle cost **147s** against ~4s warm.
Act 1 uses the same tool, so a run-through that opens the evidence base first arrives here warm.

**The on-graph shot.** Interactive explorer, never a query recipe. Traversal is **undirected**,
relationship variables must be **bound and returned** or the canvas shows floating nodes, and the engine's
label for genes is `protein`. Node indices are snapshot-specific — the drawer generates them live, so
prefer its copy button to any literal.

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
| Open with the AUC | answers a question they did not ask | act 2 leads with the distribution; no single number stands alone |
| One "enrichment" series | approved and investigational mean different things | never OR'd, never merged, separately labelled |
| Report pooled AUC because it is bigger | pooled overstates by ~7 points | macro only, never adjacent to a pooled figure |
| Quote a filtered count without its rank cut-off | how the obesity landing count acquired two values (§10.3) | every funnel count renders its cut-off in the same component |
| A number with no provenance | undercuts the platform claim the deck closes on | §3.2 — every card footers its source dataset |
| A tooltip-free "novel" or "no liability" label | *"novel"* reads as *undiscovered*, *"no liability"* reads as *safe* — both wrong | the old webapp's `TIPS` copy ports across verbatim |
| A discovery-enrichment figure on a summary tile or opening screen | the narrative makes a **reconstruction** claim, not a discovery one; a headline number turns one into the other and the slide is not recoverable in the room | the enrichment lives below the fold in act 4, labelled as an observation, and appears on no tile |
| Language that prescribes research direction — *"you should pursue…"*, *"the next target is…"* | we are a platform company, not a domain authority. Prescribing costs the room | the app ranks and explains; every verb in the copy is about evidence, never about what to do next |

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
  (`breast_shortlist`), and it is out of scope until someone asks.
- **No LLM anything.** The blueprint ships a chat block; leave `ENABLE_CHATBOT=0`. A chatbot over a
  ranked gene list is the kind of thing that makes a careful audience stop trusting the careful parts.
- Blocks to enable: none of the blueprint's five. All six acts are new views.

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

[`FLOW_MAP.md`](FLOW_MAP.md) is the generated authority for zones, datasets, producers and consumers.
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
