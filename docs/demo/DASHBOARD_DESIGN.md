# Dashboard design — one webapp, six acts, one therapeutic area

**Read [`DEMO_NARRATIVE.md`](DEMO_NARRATIVE.md) first.** This document is derived from it and has no
independent authority. Where the two disagree the narrative wins — except on the three points in §10,
where the narrative is measurably stale and the flow is right.

**What this is.** The demo surface is a **single Vue SPA deployed as a DSS STANDARD webapp**, built from
the `bs-blueprint` template. Six acts, six routes, one sidebar. This document specifies the acts, the
data contract behind each one, the guardrails the code must enforce, and what has to be built in the
flow first.

**Status.** Mockup stage, iteration 3. [`DASHBOARD_MOCKUP_V3.html`](DASHBOARD_MOCKUP_V3.html) is the
current artefact, built to the §12 and §13 plans. Iterations 1 and 2 are kept alongside at
[`DASHBOARD_MOCKUP.html`](DASHBOARD_MOCKUP.html) and [`DASHBOARD_MOCKUP_V2.html`](DASHBOARD_MOCKUP_V2.html). The native-DSS-dashboard attempt is superseded; see §3.1 for why, and §11 for what
it left behind.

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

### 3.1 Why not the native DSS dashboard

The native attempt was built (dashboard `Cn8oSQC`, nine tiles, acts 1–2, pre-flight clean) and is being
retired. Not on taste — on five findings from building it:

| finding | consequence |
|---|---|
| **A `web_app` insight cannot be bound over the API.** DSS accepts the save and silently drops every params key — `webAppId`, `webAppSmartName`, `webapp`, `webAppName`, `smartName` all round-trip to `{}`, on both `insight create -d` and `insight set-definition`. No `webapp publish` verb, no raw-API passthrough | every webapp tile is a manual UI step, so the deck cannot be built or rebuilt reproducibly |
| **No `TEXT` tiles via the API.** `dashboard add-tile` writes only `INSIGHT` tiles, and DSS drops unknown tile fields on save | *"the point to make out loud"* had to be crammed into tile titles. A narrative deck whose narration lives in chart titles is not a narrative deck |
| **Chart sampling defaults to `maxRecords: 10000`.** On `graph_edges` (2,851,510 rows) that misreports relation counts by two orders of magnitude while looking entirely plausible | every chart needs a manual sampling patch and an independent verification, forever |
| **Filter semantics are ambiguous by default.** A filter written as `{selectedValues: {x: true}}` returns with `includeEmptyValues: true`, `excludeOtherValues: false` — configured-looking and non-filtering | act 2's `level` filter is worth 73 basis points of AUC. A silent filter failure ships a wrong number |
| **No row-level drill, and no display-only columns.** A `dataset_table` hands the viewer sort and filter over every column it exposes | the three guardrails in §6 are *unimplementable* natively. That is the disqualifying one |

That last row is the argument. Three columns must be **visible and not actionable**:

- `approved_for_disease` / `investigational_for_disease` — the labels act 5's discovery lift is measured
  against. A viewer who filters by them has made the headline circular.
- `has_safety_liability` — act 6's point is that filtering on it deletes ERBB2.
- `prediction` — at the F1-optimised threshold, 590 of 762 known obesity targets score negative.

Native DSS offers exactly one guardrail — *don't expose the column* — which also removes it from
display. In our own code, display-only is three lines.

### 3.2 The stack

Copied from `~/Documents/GitHub/bs-blueprint` via `make copy DEST=…`. Vue 3 + Vite + Tailwind 4 +
ECharts + Pinia + vue-router, with a FastAPI backend and `dss_webapp/deploy.sh`, which builds the bundle,
uploads `backend/` and `frontend_dist/` into the project library under `python/<LIB_NS>/`, and patches a
STANDARD webapp definition to serve it.

**What we get for free that the native route could not give us:** routed acts with a sidebar that builds
itself from route `meta`; real prose beside real charts; display-only columns; row-level drill; a single
deploy command; and a design system already themed to the Dataiku brand.

### 3.3 The lineage rule — non-negotiable

A custom app is opaque to lineage, and act 6 closes on *"the record of why is in the flow, not someone's
inbox."* A screenshot-grade SPA would undercut the pitch it exists to deliver. So:

> **Every card that states a number names its source dataset in a footer, and every act carries a link
> into the flow zone that produced it.**

Provenance moves *into* the UI rather than being borrowed from native tiles. This is a first-class design
requirement, not a nice-to-have: it is what lets us claim the platform while shipping custom code. The
mockup implements it as a `dataset · recipe` footer on every card.

### 3.4 Route → view → data map

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
changing any of them.

### 3.5 Mock first, then swap

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

### 3.6 Conventions that are not negotiable

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

### 3.7 Build and deploy

```bash
make copy DEST=~/Documents/GitHub/target-prioritizer-app   # seed from the blueprint
make dev                                                    # vite + backend, local
make deploy                                                 # build, upload libs, patch the webapp
```

`PROJECT_KEY=DEMO_TARGET_IDENTIFICATION` in `app.env`, plus `LIB_NS` / `APP_PREFIX` /
`VITE_APP_NAME`. First deploy creates the webapp and writes its id back to `app.env`.

---

## 4. The six acts

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
| Candidate detail | drawer | rank against pool, SHAP drivers, each feature against **this disease's own distribution**, generated Cypher |
| The mechanism, on the graph | query + link | the PI3K/AKT + RAS–MAPK axis behind the head of the list |

The three *does not do* clauses — no safety axis, no morphological subtype resolution, association
ranking does not predict therapeutic relevance — go **here, on the page that carries the deliverable**,
not held to act 6. A vendor who leads with its limits has bought the right to be believed.

**Thirty-eight is a shortlist a team clears in a week.** State the rank cut-off as part of the definition
— the count is meaningless without it, which is how the obesity version acquired two conflicting values
(§10.3).

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

### Act 5 — The interrogation

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

### Act 6 — The limits, and the punch line

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
| A number with no provenance | undercuts the platform claim the deck closes on | §3.3 — every card footers its source dataset |
| A tooltip-free "novel" or "no liability" label | *"novel"* reads as *undiscovered*, *"no liability"* reads as *safe* — both wrong | the old webapp's `TIPS` copy ports across verbatim |

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

## 9. Serving-layer gaps — what must be built first

Acts 1, 3, 4 and 6 can be built against real data today. Acts 2 and 5 have gaps; §9.1 and §9.6 block
demo-critical claims. Each is one recipe, landing in zone 60.

| # | needed for | build | where the number lives today |
|---|---|---|---|
| **9.1** | act 5 — hub-bias meter | Group over `scored_champion`: known targets only, degree quintile → mean score, predicted-positive rate, median degree | `nb3b_hub_bias_meter.py` only. The notebook says so: *"it has no recipe, so this notebook IS its artifact"* |
| **9.2** | act 5 — degree-matched enrichment | reshape `tractability_axis` (48 wide columns) to long: `disease, scope, k, control ∈ {obs, naive, dm, exp}, value` | `tractability_axis`, unusable in wide form |
| **9.3** | acts 5, 6 — discovery lift vs K | aggregate `novel_discovery_eval` to long: `ground_truth, k → mean, median, n`, **infinities dropped explicitly**; add the curated `known_drug ≥ 0.8` variant | `nb4` §8.3. The curated row has no recipe at all |
| **9.4** | act 5 — the novel head | filter `dashboard_candidates` to `is_target = 0`, `rank ≤ 15`, per panel disease | derivable, not materialised |
| **9.5** | act 5 — pair provenance | aggregate `raw_ot_known_drug` / `drug_protein_edges`: targets per drug, share of validated pairs from multi-target drugs | `nb4` computes it from raw at run time |
| **9.6** | act 5 — orthogonality scatter | **visual Join**, `validation_auc_by_disease` × `drug_target_benchmark` on `disease_index` | `nb3` §7.4, in-notebook merge |
| **9.7** | act 6 — lung overlap | the `breast_panel_overlap` shape, applied to `lung_granularity_check` | row-level; the overlap count is not materialised |
| **9.8** | act 1 — acceptance table | materialise the reference comparison (nodes, edges, per-relation exact matches) | `GRAPH_BUILDING.md` §7.2 prose and `reference_baseline.json` |

House rules: joins go in visual Join recipes (9.6), new datasets on the S3 connection.

---

## 10. Discrepancies — resolve before the demo

1. **`DEMO_NARRATIVE.md` §7's HER2+ row is stale.** It reads *"ERBB2 itself at #13, TP53 #2, PIK3CA #7,
   AKT1 #10."* Live: **ERBB2 #14, TP53 #1, PIK3CA #5, AKT1 #29.** §6 of the same document says *"ERBB2 at
   rank 14, PIK3CA at rank 5"* — which matches. §6 is current, §7 drifted, AKT1 is wrong by 19 places.
2. **§8's MRN anchor shot is not a HER2+ story.** *"The breast-cancer top-10 contained RAD50, NBN and
   MRE11"* — on HER2+ those rank **55, 99, 401**; on TNBC **1, 5, 702**. So the anchor belongs to TNBC,
   which §6 forbids showing as a success. This design routes around it; the narrative still needs the
   correction, because as written the two sections contradict.
3. **The obesity landing count is unpinned.** Q1 says *"lands at 65"*; the one-pager says *"rank ≤ 200 ≈
   70"*. `filter_three_axes` gives `top200 PLAIN → 65` and `top200 FILTERED → 83`; `nb4` asserts none of
   them. The HER2+ equivalent is now defined and computed (**38** at rank ≤ 200) — define obesity's the
   same way and assert both.
4. **Zone `41 Validation - the three axes` says novel discovery is "11.4x at top-10".** The guarded value
   is **16.88** (`nb4` §8.3); `11.4` appears nowhere in `.index/claims.tsv`. Flow-zone prose is
   demo-facing and no index covers it, and this is the zone a technical reviewer opens first.
5. **`CLAUDE.md` Track A is stale.** *"What is missing is the UI itself"* — the old webapp is 1,086 lines,
   complete, and running. What is missing is this app and §9.
6. **`breast_shortlist` and `dashboard_candidates` disagree on rank** because the shortlist is a curated
   review form with its own block ranking. Act 6's liability card must bind to **`dashboard_candidates`**
   (9 of 15); the shortlist gives 7 of 11 for a different ranking, and the two must not be quoted
   interchangeably.

---

## 11. What the native-dashboard attempt left behind

Retired, not deleted — the datasets and the verification stand, and the numbers in acts 1 and 2 above
came out of it.

- **Dashboard `Cn8oSQC`** (*Explainable Target Prioritizer*), 2 pages, 9 tiles, pre-flight clean.
  Superseded by this app. Delete when the app's acts 1–2 are live.
- **Nine insights** — `5HO2siE` `4K3ZaXc` `yCeHFL5` `qbcUIFV` `KlU30Ds` `0geL7DP` `j5uQM0m` `hgUGndf`
  `Otf6C9B`. Same.
- **`ZZ_TMP_probe_webapp` (`lH0d8eC`)** — the probe that established §3.1's first row. Delete.
- **Nine column descriptions across four datasets, which should stay.** `split_audit_2`'s overlap and
  straddling columns, `validation_auc_by_disease_2.level` and `.pooled_auc`,
  `family_auc_by_family.auc_family`, `persona_candidates.rank_enrichment` now carry the traps in §4 act 2
  as schema documentation. They are independent of the presentation layer and are where the next person
  will hit these problems.

**DSS traps worth keeping** (they apply to any presentation layer): chart sampling defaults to 10,000
records; `dku dataset set-column-description` takes alternating positional column/description arguments;
serving datasets are S3/parquet so `dku dataset query` does not apply — use `dataset head`;
`dashboard_candidates` pulls all 129,253 rows in one `head` call, which is how every HER2+ figure here was
derived.

---

**Sources.** [`DEMO_NARRATIVE.md`](DEMO_NARRATIVE.md) governs, with the corrections in §10. Method and
provenance: [`TARGET_PRIORITIZER.md`](../prioritizer/TARGET_PRIORITIZER.md). Graph statistics:
[`GRAPH_BUILDING.md`](../graph/GRAPH_BUILDING.md) §7. Platform behaviours:
[`DSS_CHEATSHEET.md`](../platform/DSS_CHEATSHEET.md). Clinician constraints:
[`BREAST_SURGEON_BRIEFING.md`](BREAST_SURGEON_BRIEFING.md). App conventions: the `AGENTS` file at the root of
`~/Documents/GitHub/bs-blueprint`.

Every HER2+ and TNBC figure in §2, §4 and §10, and every graph and calibration figure in act 1 and act 2,
was computed from the live datasets on 2026-08-21, not copied from prose.

---

## 12. Mockup iteration 2 — decisions and revision plan

Review of [`DASHBOARD_MOCKUP.html`](DASHBOARD_MOCKUP.html) iteration 1. Everything below was checked
against the live project before being recommended. **§12.7 lists four numbers this review found wrong**
— two of them are on the current mockup and one is in the narrative's one-page summary.

### 12.1 Scope change — acts 5 and 6 leave the webapp

**Agreed, with one exception.** Acts 5 and 6 are *argument*, not *exploration*: no interaction, no
per-disease state, nothing the user drives. They also own **five of the nine flow gaps**, so moving them
out cuts webapp scope by a third and takes the five hardest recipes off the critical path.

They become a **talk track plus a figure set**, which is their natural home — `nb3` and `nb4` already
emit the figures (`nb3_orthogonality.png`, `nb3_family_auc.png`, the §8.3 lift figure).

**The exception: keep the ten-second check, and move it into act 4.** *"9 of the HER2+ top 15 carry a
liability flag, including ERBB2"* is computed from `dashboard_candidates`, which the app already holds.
As a **toggle on the ranked list** — switch on a safety-liability filter and watch ERBB2 disappear from
its own disease's shortlist — it is far stronger live than on a slide, and it costs nothing because the
column is already loaded. This is the one act-6 beat that is genuinely interactive.

**Consequence for the gap list:** webapp-blocking gaps drop from nine to six, and four of those six are
new (§12.6). Old gaps 9.1, 9.2, 9.3, 9.5, 9.6 become demo-prep, not app features.

### 12.2 Data loading — the connection question is the second question

**First question: how much data crosses the wire at all.** Every chart in acts 1–3 is an aggregate over
at most a few hundred rows *once computed*. The app must never read `graph_edges` (2,851,510 rows) to
draw 18 bars — it should read an 18-row `graph_relation_counts`. That is five orders of magnitude, and
no connection choice comes close to mattering as much.

| chart | reads today | should read | rows |
|---|---|---|--:|
| relations | `graph_edges` | `graph_relation_counts` | 18 |
| node types | `graph_nodes` | `graph_node_type_counts` | 8 |
| node sources | `graph_nodes` | `graph_node_source_counts` | 7 |
| PPI provenance | `edge_metadata` | `graph_ppi_provenance` | 7 |
| label evidence | `edge_metadata` | `graph_label_evidence` | 3 |
| AUC histograms | `validation_auc_by_disease_2` | **binned in the backend** — see the rule in §12.2 | — |
| feature drivers | `dashboard_candidates` | `shap_driver_frequency` | 14 |

**Seven Group recipes, all trivial, all landing in zone 60.** This is the single highest-leverage change
in this plan.

**Second question, and it applies to exactly one dataset.** Act 4 needs row-level data: ~12,272 rows ×
16 columns for one disease, held client-side so the filter count is instant with no round-trip. That is
the only large read left.

- Everything is currently on `dataiku-managed-storage` (S3/EC2). Most datasets are parquet — but
  **`dashboard_candidates` is CSV**, which is the worst format for the largest serving dataset
  (129,253 × 63).
- On **S3/parquet** the backend must read the whole object and filter in pandas. That works — the
  existing backend caches the frame in `_CACHE` on first request, which is why it is usable — but cold
  start reads all 13 diseases to serve one.
- On **Snowflake** (`managed-snowflake` and `bs-snowflake` both exist on this instance),
  `WHERE disease_index = 48537` is pushed to the warehouse and only 12,272 rows transfer. Cold start is
  effectively instant and backend memory is bounded by one disease, not thirteen.

> **Recommendation: move `dashboard_candidates` to Snowflake. Leave everything else on S3/parquet.**

Four reasons: it is the only dataset with a per-request `WHERE`; it is CSV today so we are already
paying to rewrite it; Snowflake unlocks `dku dataset query`, which would have let this review verify
figures in-database instead of pulling 129k rows to a laptop; and every other dataset is read once at
startup and cached, where parquet-on-S3 is both fine and cheaper.

**If the demo must not depend on a warehouse**, the fallback is nearly as good and adds nothing:
convert `dashboard_candidates` to **parquet, partitioned by `disease_index`**, so one disease is one
file read.

**On DSS dataset metrics as the aggregation layer** — revisited after a challenge, and the earlier
wording here was wrong in one respect.

*Ingestion is not the problem.* `get_last_metric_values()` is a few lines, and
`dku dataset metrics get graph_edges records:COUNT_RECORDS` returns 2,851,510 today. Reading a metric
from the backend is no harder than reading a dataset.

*And for the two headline scalars, metrics are strictly better.* 113,391 nodes and 2,851,510 edges are
already `records:COUNT_RECORDS` on `graph_nodes` and `graph_edges` — computed, free, no recipe. Building
a dataset to sum back to a number DSS already holds is redundant.

*But the five breakdowns cannot be metrics*, for three reasons that are about correctness, not
convenience:

1. **Two of them need a filter, and a metric describes the whole dataset.** `graph_ppi_provenance` is
   `WHERE relation = 'protein_protein'`; `graph_label_evidence` is `WHERE relation = 'disease_protein'`.
   The only filtered probe type is a SQL probe, and these are S3/parquet — not SQL-backed — so that
   route does not exist here either. It is the same reason `dku dataset query` does not work on them.
2. **The categories would freeze at probe-definition time.** Expressed as metrics the breakdowns need one
   probe per value — 8 + 7 + 18 = 33 hand-defined probes. Add a 19th relation to the graph and the Group
   recipe grows a bar automatically while the probe set silently omits it. Act 1's claim is *"18
   relations, here they all are"*; a silently incomplete inventory is the one failure that card cannot
   survive.
3. **Metrics go stale without saying so, and DSS documents this itself:** *"DSS does NOT auto-refresh
   metric values on rebuild — call this after every build."* A serving dataset rebuilt in the same job as
   its source cannot drift from it. A metric can, and nothing on screen would show it.

A fourth, smaller reason: §3.3 requires every card to link to its source. A metric has no flow object to
link to.

> **The principle: metrics are for *watching* data, datasets are for *serving* it.**

**And the challenge produced a real improvement.** Use the metrics as an **integrity check on the serving
tables**: if `graph_relation_counts` does not sum to `records:COUNT_RECORDS` on `graph_edges`, the
serving copy is stale. That is a free, automatic guard, wired as a DSS check on the dataset — exactly
what metrics are good at, and it closes the one hole a precomputed serving layer has.

*Insights* remain out: they would re-couple the app to the presentation objects §11 is retiring.

**The chart-KPI route, investigated.** The proposal was to read the aggregate off a DSS chart instead:
charts recompute at render time, so they never go stale, and the chart aggregation language is more
flexible than a probe. Both halves of that are true, and it still does not work — for one hard reason
and one that dissolves.

*The hard reason: a chart's aggregated data is not readable by a backend.* The public API client exposes
`get_settings()`, `delete()` and metadata on an insight and **no data accessor at all** — there is no
`get_data()` anywhere in `dataikuapi`. The chart computes server-side for the *renderer*, and the only
way to reach that computation is an internal `/dip/api/` endpoint: undocumented, unversioned and
session-authenticated. A serving path cannot rest on it. (Semantic-model metrics are a different
mechanism again — `add-metric` takes pseudo-SQL for the natural-language query layer, it is a
*definition* consumed by a query generator rather than a stored value, and pseudo-SQL needs SQL-backed
data. Ours is parquet on S3.)

*The reason that dissolves: the formula flexibility is already here.* `recipe create-group` takes
`--pre-filter` and `--post-filter` GREL formulas and `--computed-col` expressions evaluated before
grouping. That is the same expressive power as a chart's computed columns — the two filtered A1 tables
were built with `--pre-filter` and needed nothing else.

**But the auto-update property is the right thing to want, and it belongs in the plan.** It is exactly the
weakness §12.2 pins on metrics. The answer is a **scenario**, not a different aggregation mechanism:
`scenario add-trigger-dataset` fires when a source dataset changes and `add-step-build` rebuilds the
serving zone. Then the serving tables carry the same freshness guarantee a chart has — and with one
advantage a metric never has: **if a serving table does fall behind, DSS shows the dataset as
out-of-date in the flow.** Visible staleness beats invisible staleness.

> Net: chart KPIs are blocked by the missing read path; metrics are right for scalars and for integrity
> checks; datasets plus a rebuild scenario are the serving layer.

⚠ **One cost of the dataset route that the chart route genuinely would not have, found by running the
scenario:** a `NON_RECURSIVE_FORCED_BUILD` **truncates before it writes**, so mid-rebuild every serving
table reads **zero rows**. A live chart never does that, because it queries the source. Three
mitigations, in order of preference: the backend caches at startup (the existing one already does), so
this only bites on a cold start during a rebuild; schedule the refresh outside demo hours; or drop
`FORCED` so DSS skips the rebuild when nothing upstream changed. Do not leave a demo machine cold-starting
against a rebuilding serving zone.

**The rule this settled on, after measuring rather than asserting** (`analyze-column` costs **15.9s** on
`graph_edges` and **7.5s** on `graph_nodes`; a prebuilt 43-row table reads in milliseconds):

> **Prebuild when the source is large, or when the aggregate needs a filter or join the on-demand tools
> cannot express. Use metrics for whole-dataset scalars. Compute in the backend when the source is
> already small and the transform is cheap.**

Two consequences, both applied below:

- **Act 1's stat card reads metrics, not a dataset sum.** 113,391 and 2,851,510 are already
  `records:COUNT_RECORDS` on `graph_nodes` and `graph_edges`. Summing a serving table to recover a
  number DSS already holds is redundant.
- **`calibration_histograms` is dropped from A2.** It bins 670 numbers — a millisecond in the backend —
  and bin count is a *rendering* decision that belongs to the chart. Freezing it into a dataset would
  make changing the histogram a flow rebuild.

A further caution found while measuring: `analyze-column` defaults to **top-10 values**, and
`graph_edges.relation` has 18. There is a `--top-k` flag, but the default would silently have produced a
ten-relation inventory on the one card whose claim is *"18 relations, here they all are."*

### 12.3 Linking charts back to their source

This is §3.3's lineage rule made clickable. The `src` footer becomes real links via one
`<ProvenanceFooter :dataset :recipe :zone>` component, with the DSS base URL served from a backend
`/api/system/dss-base` so it resolves in both dev and embedded mode.

| target | URL form |
|---|---|
| dataset | `/projects/{KEY}/datasets/{NAME}/explore/` |
| recipe | `/projects/{KEY}/recipes/{NAME}/` |
| flow zone | `/projects/{KEY}/flow/?zoneId={ID}` |
| saved model | `/projects/{KEY}/savedmodels/{ID}/versions/` |

> **Link to datasets and recipes, never to insights.** Insights are presentation objects and §11 retires
> them; a link into one couples the app to an artifact that may be deleted. Datasets and recipes *are*
> the lineage, and they are stable.

### 12.4 AUPRC — and a trap in the saved model

**Do not surface `hJLGoYn4`'s own metrics panel.** `dku model metrics hJLGoYn4` reports
`auc = 0.8962` and `averagePrecision = 0.3359`. Both are **pooled, on the model's internal test split**:

| | saved model panel | documented (macro) | gap |
|---|--:|--:|---|
| AUROC | 0.8962 | **0.8230** | +7.3 pts — exactly the pooled overstatement the project warns about |
| AUPRC | 0.3359 | **0.1778** | nearly 2× |

Surfacing that panel would put both forbidden numbers on screen at once.

**How to represent AUPRC so it means something: never alone, always against the base rate.** The
candidate pool is **1.89% positive**, so a random ranker scores AUPRC 0.0189. The champion's 0.1778 is
**9.4× the base rate**. Form: a horizontal bar with the base rate as a hairline at the left edge and the
achieved value as the bar, labelled *"9.4× better than chance at concentrating true targets."* Put
AUROC beside it with one line of copy — AUROC flatters an imbalanced problem, AUPRC is the honest one at
1.89% prevalence.

**Better still, lead with the unit a biologist already uses.** `rank_enrichment` is
`(hits_at_50 / 50) / base_rate` — the same intuition as AUPRC, expressed as *"the top 50 is N× richer in
real targets than the pool."* Lead with that; keep AUPRC as the technical footnote for the
computational-biology half of the room.

### 12.5 Act 1 — The evidence base

| # | change | notes |
|---|---|---|
| 1 | Replace *Accepted vs reference* with the source count | **but say "6 external sources"**, not 7. The seven `node_source` values are GO 38,092 · MONDO 25,906 · NCBI 20,861 · HPO 19,120 · DrugBank 5,282 · REACTOME 2,883 · **MONDO_grouped 1,247** — and the last is a *derived* grouping we created, not an external source. Counting it inflates the claim |
| 2 | Embed the Visual Graph Explorer below the metrics | fixed-height panel (≈540px) with an **open-full-screen** button. Do not let it size to content — this is the same clipping lesson as §3.4 |
| 3 | Node-type chart to the left of relations | agreed, and it is the right reading order: what things *are*, then how they *connect* |
| 4 | Add a node-source chart | new Group recipe, 7 rows. Pair it visually with the PPI-provenance chart — together they say *"every node and every edge knows where it came from"* |
| 5 | Drop the frozen-reference table | agreed — it also removes old gap 9.8 |

⚠ **Dropping the table loses a claim that was doing real work:** *accepted against a reference we did not
write*. Keep it as **one sentence in the act lede** (`−0.03% on edges, 14 of 18 relations reproduce
exactly`). One line, no recipe, claim retained.

### 12.6 Act 2 — Scope and calibration

**1 — Sankey from routes through the pool to the splits.** The numbers exist and reconcile exactly:

```
  GGD   3,380,853  ─┐
  GPGD  5,373,706  ─┼─►  pool 6,754,128  (1.89% positive)  ─┬─►  train      2,187,862
  GCD      42,227  ─┘                                       ├─►  validation 3,958,921
                                                            └─►  test         607,345
```

Two things to get right. **The three routes overlap** — they sum to 8,796,786 against a union of
6,754,128 — so a naive Sankey overstates the left side by 30%. Render the union explicitly or label the
overlap. And **the GCD ribbon is the drug route at 0.6%**: showing it is honest and preempts a
ground-truth objection, because it is the thing the narrative insists we describe as *"not a feature,
but it shapes the scored population."*

**Arrangement:** the Sankey takes the top slot. The split audit stays, but compressed from a 9-column
table to a **four-zero strip** beneath the Sankey — the zeros are the point, and they are four numbers,
not a table.

**2 — Merge the two AUC cards behind a tab.** Agreed. Same axis, same 20 bins; a tab is exactly right.
Each tab carries its own n and macro: *disease* → 668 / 0.8230, *family* → 503 / 0.8009.

**3 — Feature importance: use SHAP driver frequency, not the model object.** `hJLGoYn4` was trained with
`skipPermutationImportance: True`, so **there is no feature importance on the champion**. Retraining to
get one is not worth it, and the better artifact already exists: `top_shap_drivers` carries the top two
drivers for all 129,253 scored rows. Aggregating gives an empirical importance ranking over all 14
champion features:

| rank | feature | times a top-2 driver | | rank | feature | |
|--:|---|--:|---|--:|---|--:|
| 1 | `ppi_evidence_depth` | 76,487 | | 8 | `gene_n_pathways` | 4,666 |
| 2 | `ppi_multi_source_frac` | 46,643 | | 9 | `ppi_adamic_adar` | 3,220 |
| 3 | `dwpc_GBGD` | 46,382 | | 10 | `prox_closest` | 2,550 |
| 4 | `dwpc_GPGD` | 23,204 | | 11 | `ppi_jaccard` | 2,167 |
| 5 | `prox_kernel` | 21,802 | | 12 | `dwpc_GGD` | 1,148 |
| 6 | `dwpc_GFGD` | 19,180 | | 13 | `shared_pathway_frac` | 111 |
| 7 | `gene_ppi_degree` | 10,857 | | 14 | `ppi_common_neighbors_z` | 89 |

This is **better than a global model statistic for this demo**: it is measured on the rankings actually
delivered, it filters per disease (the same aggregation restricted to HER2+ gives *this disease's*
drivers), and it sidesteps the missing permutation importance entirely.

> **And it closes a loop.** The two strongest drivers — `ppi_evidence_depth` and
> `ppi_multi_source_frac` — are both **provenance** features. The model's best signal is *how well
> evidenced is this interaction*, which is precisely what act 1's "every edge knows where it came from"
> chart was showing. Act 1 stops being scene-setting and becomes the reason act 2 works.

**4 — Explain the enrichment quantile chart, and overlay the diseases.**

*What is ranked:* the 670 validation diseases (668 with a computable value).
*How the lift is calculated:* `rank_enrichment = (hits_at_50 / 50) / base_rate` — of the top 50
candidates the model ranks for a disease, the share that are known targets, divided by that disease's
**own** base rate of known targets in its pool. So *"the top 50 is N× richer in real targets than this
disease's pool average."* Same intuition as AUPRC, in a unit a biologist reads directly.

*Overlaying the dots:* **yes, and it is the right fix.** Render a jittered beeswarm strip of all 668
diseases beneath the box, with hover labels. Name only the demo diseases as permanent callouts; leave
the rest faint. This answers *"which disease is which"* without a legend and makes the spread concrete
rather than abstract.

### 12.7 Act 3 — The therapeutic area

**1 — Other families for the dropdown: 17 exist with ≥4 scored diseases.** Recommended list:

| family | diseases | AUC | why it earns a slot |
|---|--:|--:|---|
| hematologic cancer | 29 | 0.9188 | largest panel in the project |
| breast cancer | 19 | 0.9272 | the spine; the subtype-resolution story |
| lung cancer | 17 | 0.9312 | the morphological-subtype *failure*, in-panel |
| sarcoma | 13 | 0.9309 | a rare-disease shape |
| salivary gland cancer | 11 | 0.9233 | small, high-quality |
| **anemia** | 9 | 0.8577 | **not cancer** |
| **epilepsy syndrome** | 7 | 0.8345 | **not cancer, not oncology-adjacent** |

The last two matter most. *"Does this only work on cancer?"* is a question this deck currently cannot
answer, and two non-oncology families with respectable AUCs answer it directly.

**Cost:** `compute_breast_panel.py` carries a **hardcoded `PANEL` dict** of `disease_index → name`.
Generalising means replacing it with a join on `disease_family_id`. Same change generalises
`breast_panel_overlap`. One recipe edit each — see §12.10.

**2 — The ontology hierarchy is available, and it should drive the interaction.**
`disease_hierarchy_annotation` carries `mondo_id`, `current_hop_depth`, `is_anchor`,
`current_anchor_name`, `is_eligible`; `raw_disease_disease` carries `parent_id` / `child_id`. So a real
tree can be rendered, not a flat list.

> **Recommendation: a collapsible ontology tree beside the panel table.** Indent by
> `current_hop_depth`, mark the anchor, grey out terms that are not `is_eligible`, and let selecting a
> node filter the table. It answers the user's question directly — the panel's terms are *not* siblings,
> and the tree shows exactly how they sit.

The payoff is bigger than orientation: **siblings in that tree share a split key.** The tree is the
clearest possible explanation of act 2's leakage control — *"these two terms are the same programme, so
they never straddle the train/test divide"* — shown rather than asserted. Act 3 becomes act 2's proof.

**3 — The AUC scatter.**

*Hover labels and visible axes:* agreed, both.

*What per-disease AUC is:* a rank-based (Mann-Whitney) AUC — `(Σ ranks of known targets − n₁(n₁+1)/2) /
(n₁·n₀)`. In plain language: **pick one known target and one non-target at random from this disease's
pool; the AUC is the probability the model ranked the known one higher.**

*Why it degrades at low counts — it is variance, not definition.* The real intervals, already in
`breast_panel_metrics`:

| disease | known targets | AUC | 95% CI |
|---|--:|--:|---|
| HER2+ breast | 599 | 0.9365 | [0.923, 0.950] |
| breast adenocarcinoma | 53 | 0.9043 | [0.850, 0.959] |
| ER-negative breast | 14 | 0.8411 | [0.712, 0.971] |
| **triple-negative breast** | **8** | 0.8949 | **[0.749, 1.041]** |

**TNBC's upper bound is 1.041 — impossible for an AUC.** That single fact demonstrates the point better
than any threshold rule, and it is already computed.

⚠ **The mockup's "≈ 50 known targets" line is wrong.** The dataset already carries an
`auc_trustworthy` flag, and it reads False at n=14 and n=8 but **True from n=33 upward** — so the
boundary sits between 14 and 33, not at 50. Read the rule out of `compute_breast_panel.py` and quote it,
or drop the threshold line and let the confidence intervals speak.

*Supplementary charts for the thin diseases:* two, both already supported by existing columns.
1. **Plot the CI, not the point** — an error-bar chart instead of a scatter. The honest form, and the
   thin diseases visibly disqualify themselves.
2. **Switch metric below the threshold.** `breast_panel_metrics` already has `hits_at_50`,
   `expected_at_50`, `hits50_poisson_p` and `hits50_verdict`. Observed-versus-expected hits with a
   Poisson p-value is well-defined at n=8 where AUC is not. **Show AUC where it is trustworthy and
   hits-vs-expected where it is not** — and say why on screen.

**4 — Making the overlap card interactive.** Two forms, and the second answers the biology question.

- **Primary: a pairwise overlap matrix.** n×n heatmap over the family's diseases, cell = shared genes in
  the top 50. This is the readable form for 12–29 diseases and it carries the "2 of 50 vs 47 of 50"
  claim directly. Clicking a cell reveals the shared genes.
- **On click: a gene × disease dot grid.** Rows = the union of top-50 genes, columns = the family's
  diseases, dot present if the gene is in that disease's top 50, coloured by rank band. **This is the
  one with a biologically meaningful reading** — it separates the genes shared across the whole family
  (the common programme) from the ones unique to one subtype (the subtype-specific biology), which is
  exactly the distinction the act is claiming to make.

On the dot-plot axes question: there is no natural continuous x/y for gene overlap, which is why a
symmetric matrix or a categorical gene × disease grid is the right form and a scatter is not.

**5 — Drop *The signature of each subtype's head* once families are added.** Agreed. It is static prose
that cannot survive a dropdown. Its content is absorbed by the gene × disease grid, which shows the same
thing generatively.

### 12.8 Act 4 — The shortlist

| # | change | notes |
|---|---|---|
| 1 | Curated disease selector | reuse act 3's family dropdown, scoped to diseases that *have candidate lists*. ⚠ `dashboard_candidates` covers **13 personas, not 670** — the picker must distinguish *scored* from *has a list* or it offers 670 diseases and dead-ends on most. The existing backend already computes `has_candidates`; port it |
| 2 | Interactive top 15 with attribute filters | agreed — it becomes the same table component as the full list, defaulting to `rank ≤ 15` |
| 3 | Funnel as a Sankey | ⚠ **prototype before committing.** The last stage is 38 of 12,272 — 0.3% — which renders as an invisible ribbon. A stepped funnel with proportional connectors, or a broken axis, will read better. Recommend building both and choosing on sight |
| 4 | Gene click refreshes the last two cards | agreed, and it is the strongest interaction in the app. The existing drawer already does the feature panel; extending it to drive the graph card is the improvement |
| 5 | Graph card backed by the Explorer | agreed — with a gene selected the query is pre-filled and the button becomes *"show this gene's evidence"* |
| **6** | **New: the liability toggle** (from §12.1) | switch on a safety-liability filter and ERBB2 vanishes from its own disease's shortlist. Act 6's best beat, made live, at zero data cost |

### 12.9 Acts 5–6 — how each card links back

Asked for explicitly, and it is also the test of whether they belong outside the app. Each act-5/6 card
defends an earlier act:

| card | defends | the link to make out loud |
|---|---|---|
| Degree-matched enrichment | **act 4** — the shortlist | *"the list you just filtered isn't just well-connected genes"* |
| Hub-bias meter | **act 2** — calibration | *"and here is the population where we still under-score"* |
| Delete the answer key | **act 4** — the top 15 | *"HRAS at #9 was novel; here is what that is worth at scale"* |
| Lift vs K | **act 3** — the panel | *"per-disease lift is what act 3's enrichment column was measuring"* |
| Ground-truth provenance | **act 1** — the label evidence donut | *"act 1 said 53% genetic association; here is why the other half is weaker"* |
| Orthogonality (r = +0.002) | **act 2** — the AUC spread | *"a high AUC in act 2 does not buy therapeutic relevance"* |
| The three refuted gates | **act 1 + act 4** | *"the annotations you filtered on in act 4 are deliberately not model inputs, and here is the measurement"* |
| Ten-second check | **act 4** | **stays in the app** as the liability toggle |
| The 0.9354 lookup | **act 2** | *"this is why act 2 led with a distribution and not a score"* |

**Act 5, card 1 — how the degree-matched number is calculated.** Take the **novel-only** sub-list
(`tractability_axis` where `scope = "novel only"` — this is measured after the known targets are
deleted, which the mockup does not currently say). For each disease and cut-off K, count how many of the
top K are tractable (`obs`), then compare against two expectations: `naive`, sampling K genes uniformly
from that disease's pool, and `dm`, sampling K genes **matched on network degree**. Enrichment is
`obs / expected`, reported pooled as `Σobs / Σexp`.

The finding is the *crossover*, not the level: **the degree control makes the result look worse at
K = 10 and better from K = 20–50 onward.** Deep in the list the model is finding something popularity
does not explain; at the very head it is not. Volunteering that is the whole point of the card.

### 12.10 Flow work this plan requires

Six new items; five old gaps leave the webapp with acts 5–6.

| # | for | build | size |
|---|---|---|---|
| **A** | §12.2 | seven Group recipes → `graph_relation_counts`, `graph_node_type_counts`, `graph_node_source_counts`, `graph_ppi_provenance`, `graph_label_evidence`, `calibration_histograms`, `shap_driver_frequency` | trivial, 3–40 rows each |
| **B** | §12.2 | move `dashboard_candidates` to Snowflake (or parquet + partition by `disease_index`) | one recipe output change |
| **C** | act 2 Sankey | `pool_route_counts` — GGD / GPGD / GCD admissions and the union, currently only in `nb2` §5.2 | one recipe, 4 rows |
| **D** | act 3 dropdown | replace the hardcoded `PANEL` dict in `compute_breast_panel.py` with a `disease_family_id` join; same for `breast_panel_overlap` | two recipe edits |
| **E** | act 3 tree | join `disease_hierarchy_annotation` × `raw_disease_disease` → parent/child edges within a family | one **visual Join** |
| **F** | act 3 grid | top-50 gene membership per disease, long form, for the gene × disease dot grid | one recipe |

Old gaps **9.1, 9.2, 9.3, 9.5, 9.6** are now demo-prep, not app features. Old gap **9.8** is dropped
with the frozen-reference table. Old gap **9.7** (lung overlap) is absorbed by **D**.

### 12.11 Numbers this review corrected

Four, found while checking the suggestions. Two are on the mockup now.

1. **`2.9×` degree-matched at top-10 is unguarded and matches no current estimator.** The guarded
   assertions in `nb4` §8.4 are **pooled 3.29× at K=10** and **2.42× at K=200**, with **macro 3.11× at
   K=10**. `2.4` maps to the pooled K=200 assertion; `2.9` maps to nothing. **On the mockup now — fix
   before it is shown.**
2. **The narrative's one-page summary says "12 network-topology features."** The champion `m7-f14` has
   **14**: `dwpc_GBGD`, `dwpc_GFGD`, `dwpc_GGD`, `dwpc_GPGD`, `gene_n_pathways`, `gene_ppi_degree`,
   `ppi_adamic_adar`, `ppi_common_neighbors_z`, `ppi_evidence_depth`, `ppi_jaccard`,
   `ppi_multi_source_frac`, `prox_closest`, `prox_kernel`, `shared_pathway_frac`. The `12` is an
   `m3-f12`-era number in a **demo-facing** table.
3. **The mockup's "≈ 50 known targets" threshold does not match the data.** `auc_trustworthy` is False
   at n=14 and n=8, True from n=33. **On the mockup now.**
4. **Counting seven node sources overstates the claim.** `MONDO_grouped` (1,247) is a grouping we
   derived, not an external source. Six external sources.


---

## 13. Iteration 3 — answers and revisions

Review of [`DASHBOARD_MOCKUP_V2.html`](DASHBOARD_MOCKUP_V2.html). **Two of the challenges here were
right and change the build plan** (§13.2 and §13.7). One caught a guardrail I broke in v2 (§13.9).

### 13.1 All-disease aggregates, and visual over Python

Adopted as a standing rule for the serving layer: **one dataset per statistic covering every disease,
never one per disease.** Almost all of it is visual:

| dataset | recipe | all diseases? |
|---|---|---|
| `graph_relation_counts`, `graph_node_type_counts`, `graph_node_source_counts` | **Group** | n/a — graph-wide |
| `graph_ppi_provenance`, `graph_label_evidence` | **Group** with a relation filter | n/a |
| `calibration_histograms` | **Prepare** (binning) → **Group** | 670 + 505 |
| `validation_auc_ci` | **Prepare** + Formula — see §13.7 | **670** |
| `shap_driver_frequency` | **Prepare** (split ", " → strip " (…)" → fold to rows) → **Group** | all 129,253 rows |
| `top50_membership` | **Filter** `rank_in_disease ≤ 50` — the rank column already exists | every scored disease |
| `pairwise_overlap` | **Join** `top50_membership` × itself on `gene_index` → **Group** by disease pair | **every pair, every family** |
| `family_panel` | **Join** `validation_auc_ci` × `disease_family_id` × names | every family |
| `pool_route_counts` | one small Python unless the pair spine carries a route column | n/a |

Two consequences worth stating. `pairwise_overlap` as a **self-join plus a group** replaces
`compute_breast_panel_overlap` and covers all 17 families at once — the breast-only recipe was never
necessary. And `top50_membership` is a **filter, not a computation**, because `dashboard_candidates`
already carries `rank_in_disease`.

### 13.2 The Sankey should start from the whole graph — and the excluded branch is the study's limit

Agreed, and the numbers reconcile exactly:

```
  27,153 disease nodes
      └── 1,157 eligible  (module_size ≥ 20 — the seed gate)
      └── 25,996 EXCLUDED (95.7%): fewer than 20 curated gene associations
                                    ↓
       GGD 3,380,853 ┐
       GPGD 5,373,706├─► pool 6,754,128 (1.89% positive) ─┬─► train      2,187,862  (383 diseases)
       GCD    42,227 ┘                                     ├─► validation 3,958,921  (670)
                                                           └─► test        607,345  (104)
```

`383 + 670 + 104 = 1,157` — the eligible count exactly. **The excluded branch is 95.7% of the disease
ontology**, and showing it is the most honest thing act 2 can do: it is precisely what Phase 3 exists to
widen (20 → 5 would admit 931 more diseases). A second, much smaller loss belongs beside it: of 2,341
curated targets in the audited diseases, **98.5% are reachable in the pool and 1.5% (34) are not**.

**Clicking a split branch to reveal its families: yes, and make it navigate.** The split *is* by family,
so clicking `validation` should carry the viewer into act 3 with the family list pre-filtered to that
fold. That makes the zero-straddling card and act 3's hierarchy the same story told twice, which is what
the challenge was pointing at. Needs one visual **Group** of `disease_family_id` × split.

### 13.3 Retraining for permutation importance — no, and the reason is technical

**Do not.** `nb1` §6.1 records the highest |rho| between a model feature and node degree at **0.975**.
Permutation importance is unreliable at that level of collinearity: permuting one feature leaves its
information reachable through its correlate, so the score is understated and the split between a
correlated pair is arbitrary. On 14 graph-topology features that are correlated by construction, it
would produce a confident-looking chart that does not mean what a viewer would read into it.

Retraining also risks moving `m7-f14`'s documented numbers, which the whole doc set is pinned to.

The SHAP-driver aggregation is the better artifact on the merits, not merely the cheaper one: it is
measured on the rankings actually delivered, and **it filters per disease** — the same aggregation
restricted to HER2+ gives that disease's drivers, which permutation importance can never do.

### 13.4 Why AUPRC does not travel across diseases

**Because AUPRC's floor is the base rate, and the base rate is not remotely constant.** Across the 668
scored diseases:

| | base rate (positives ÷ pool) |
|---|--:|
| minimum | 0.062% |
| 10th percentile | 0.319% |
| median | 0.774% |
| 90th percentile | 2.861% |
| maximum | 19.466% |

**A 312× spread.** A random ranker scores AUPRC ≈ the base rate, so a disease at 19% prevalence starts
from a floor 312× higher than one at 0.06%. Comparing AUPRC across that population compares prevalence
at least as much as ranking quality, and averaging it produces a number driven by which diseases happen
to be well annotated.

AUROC is **prevalence-invariant** — it is a pure ranking statistic — which is why the macro per-disease
figure is an AUROC and why it is comparable across a heterogeneous disease set.

So the rule: **AUPRC only at a single fixed prevalence** (the pooled pool at 1.89%, where 0.1778 against
a 0.0189 floor means 9.4× chance). For per-disease precision use `rank_enrichment`, which is comparable
*because* it divides by each disease's own base rate.

### 13.5 Act 2 layout, enrichment card, feature table

**Swap the aggregate card and the per-disease distribution** — agreed. Summary before detail is the
right reading order for a scanned surface, and the act lede still frames the distribution as the honest
one. Aggregate AUROC/AUPRC left, per-disease distribution right.

**Enrichment card:** add hover readouts on the box itself (min / Q1 / median / Q3 / max), drive the
highlighted diseases from the **currently selected persona** rather than a fixed list, and resolve label
collisions by laying the callouts out with a simple left-to-right sweep that pushes each label right of
the previous one's extent, dropping any that still cannot fit.

**Feature table** — the 14 champion features in the language a scientist uses:

| feature | what it measures |
|---|---|
| `dwpc_GGD` | degree-weighted count of paths reaching the disease **through an interacting gene** |
| `dwpc_GPGD` | the same, **through a shared pathway** |
| `dwpc_GBGD` | the same, **through a shared biological process** |
| `dwpc_GFGD` | the same, **through a shared molecular function** |
| `prox_closest` | hops to the **nearest** gene already annotated for this disease |
| `prox_kernel` | diffusion proximity to the **whole disease module**, all hops, distance-weighted |
| `ppi_common_neighbors_z` | interaction partners shared with the module, **z-scored against what degree alone predicts** |
| `ppi_adamic_adar` | shared partners, weighted so **rare** partners count for more |
| `ppi_jaccard` | shared partners as a fraction of the union |
| `ppi_evidence_depth` | how **deeply evidenced** this gene's interactions are |
| `ppi_multi_source_frac` | fraction of its interactions asserted by **more than one interactome** |
| `gene_ppi_degree` | raw connectivity — how many partners the gene has |
| `gene_n_pathways` | how many pathways the gene belongs to |
| `shared_pathway_frac` | fraction of the gene's pathways that also contain a module gene |

Do **not** put the Class 1 / Class 2 seed-gate column in this table. That is Phase 3 engineering, not
demo material.

### 13.6 Act 3 — merge the panel and the tree

Agreed: one table, with `└` and indentation in the first column carrying `current_hop_depth`. The
separate tree card goes. Selecting a row still filters the rest of the act, and the indentation does the
explanatory work the tree was doing.

### 13.7 Act 3 — the confidence intervals need no new Python recipe

**Verified, and the challenge was right.** Hanley–McNeil reproduces every documented `auc_se`:

| disease | n_pos | documented SE | Hanley–McNeil |
|---|--:|--:|--:|
| HER2+ | 599 | 0.0069 | 0.0070 |
| breast carcinoma | 864 | 0.0080 | 0.0081 |
| luminal A | 101 | 0.0243 | 0.0243 |
| parent term | 138 | 0.0250 | 0.0250 |
| ER-negative | 14 | 0.0660 | 0.0661 |
| triple-negative | 8 | 0.0745 | 0.0746 |

Every value agrees to ≤ 0.0001. The interval is therefore **pure arithmetic on `auc`, `n_pos` and
`n_neg`** — all three of which `validation_auc_by_disease_2` already carries, in zone 40, **for all 670
diseases**.

> **So: a visual Prepare recipe with a Formula, over the existing ranking-quality output, gives every
> disease a confidence interval.** No Python, no breast-only recipe, and it satisfies §13.1's
> all-diseases rule. `compute_breast_panel` shrinks to whatever is genuinely breast-specific
> (`hits50_poisson_p`, `top10_novel_genes`) — and those generalise the same way.

### 13.8 Act 3 — what "subtype" means is not the same in every family

Investigated. **Breast is the only family in the project whose subtypes are biomarker-defined**, which
is why its gene grid reads the way it does. The others divide on a different axis:

| family | subtype axis | largest members | reads as |
|---|---|---|---|
| **breast** | **biomarker** (receptor status) | HER2+, luminal A/B, TNBC, ER± | the common programme vs subtype-specific biology |
| **lung** | **histological** | adenocarcinoma 766, squamous 750, NSCLC 668, small cell 652 | **the negative result** — these are the subtypes the model cannot separate (47 of 50 shared) |
| **hematologic** | **lineage** | lymphoid neoplasm 733, plasma cell myeloma 731, Hodgkins 521, NK/T 486 | richest hierarchy in the project, hop 2–5 |
| **anemia** | **mechanism** | anemia 492, hemolytic 118, pernicious 102 | non-oncology, but modules 26–118 |
| **epilepsy** | **syndrome** | epilepsy 99, early-onset DEE 58, focal 27 | non-oncology, modules 26–99 |

Two consequences. The **grid generalises structurally** — it is only top-50 membership — but its
**interpretation text must be per-family**, and for lung the same chart is the honest demonstration of a
limitation rather than a strength. That is elegant: one component, two truthful readings.

And a caution: anemia's and epilepsy's modules are small enough that most of their terms will land in
the **AUC-unpinned** regime from §13.7. They still earn their place — they are the answer to *"does this
only work on cancer?"* — but the honest framing is *"it works, with much wider error bars"*, never as a
showcase.

### 13.9 Act 4 — the list, and a guardrail v2 broke

**"Drop the in-trials filter" is correct, and it is a rule violation I introduced.** §6 of this document
says the drug badges must never be filterable, because the discovery lift is measured against exactly
those labels — a viewer who filters by them has made the headline circular. v2's *In trials* button does
precisely that. **Remove it.**

Revised control set for the ranked list:

| control | verdict |
|---|---|
| gene name search | **add** — navigation, not selection bias |
| show all pairs for the disease (12,272 rows, virtualised) | **add** — replaces the top-15 slice |
| tractability, as both a status badge and a filter | **add** — it is one of the three *validated* clauses |
| druggability class filter | **add** — a validated display grouping |
| novel / known | keep |
| rank cut-off | keep |
| **in trials** | **drop — guardrail violation** |
| **safety liability** | **drop as a filter** (see below) |

⚠ **The liability control is the one open question.** It arrived as the act-6 migration, and its whole
purpose is to demonstrate *once* that the filter everybody wants would delete ERBB2. Recommendation:
**keep the demonstration, drop the filter** — render it as a separate, clearly-labelled
*"show what a safety filter would cost"* control that strikes rows through in place rather than removing
them, sitting outside the filter row. If that still reads as a filter, make the card static instead.

**How the feature percentile is calculated** (currently marked `mock` in the mockup): for one gene and
one feature, it is `100 × (candidates for this disease with a lower value) ÷ (candidates with a
non-null value)` — the percentile rank of this gene's feature value **within this disease's own pool**,
which is why the drawer says *"higher than 96% of candidates for this disease"* and not a global figure.
The existing webapp backend computes it per request in its `/gene` endpoint; the mockup's numbers are
placeholders until that endpoint is ported.


---

## 14. Flow migration — serving zones, the notebook zone, and when to prune

Audited against the live project. 93 datasets across 13 zones; the lineage below comes from the recipe
graph, notebook `Dataset(...)` calls and the webapp backend, not from the zone names.

### 14.1 When to clean up — neither before nor after, but in three stages

> **Build the serving layer before the backend. Build the notebook before the prune. Delete last.**

Three reasons, in order of force.

**The serving datasets are the backend's API.** If the backend is written against today's flow it gets
written twice — once against `persona_candidates` and `novel_discovery_eval` in zone 41, and again
against whatever replaces them. Creating the ~15 precomputed datasets first is **purely additive**:
nothing is deleted, nothing breaks, and the backend is then written once against a contract that will
not move.

**Deletion is the only irreversible step, and it is the least valuable one.** An unread dataset costs
storage, not correctness. Nothing about a messy flow blocks the webapp. So deletion earns last place on
both counts — it has the highest risk and the lowest return.

**And there is a specific trap in pruning early.** `safety_lift` and `tractability_lift` are read by
**nothing today** — not a recipe, not a notebook, not the app — so a mechanical "delete what nothing
reads" pass would remove them. They carry the **entire act 6 punch line**: membrane receptor 3.16× vs
0.78×, LoF-intolerant 2.07× / 1.37×, liability 4.62×. Those numbers appear in the deck and **nothing
guards them**. Prune before the act 5/6 notebook adopts them and you delete the evidence for the
closing argument.

| stage | what | risk | blocks the webapp? |
|---|---|---|---|
| **1** | Create the four serving zones and their datasets | none — additive | **yes, do first** |
| **2** | Build the backend against them | none | — |
| **3** | Write the act 5/6 notebook; it adopts `safety_lift`, `tractability_lift`, `lung_granularity_check` | none — additive | no, **parallel with 1–2** |
| **4** | Move validation datasets into the notebook zone | low — a move, not a delete | no |
| **5** | Delete, only what stage 3 proved unneeded | **irreversible** | no, **do last** |

Stages 1 and 3 are independent and should run in parallel — the notebook has no dependency on the app.

### 14.2 What the audit found

| | count |
|---|--:|
| datasets | 93 |
| **terminal** — nothing downstream in the flow | 27 |
| read by a notebook | 20 |
| read by the webapp backend | **3** |
| **terminal AND read by neither** | **18** |

Four of those 18 are not dead, and the distinction matters:

- **`safety_lift`, `tractability_lift`** — the act 6 punch line, unguarded. **Adopt into the notebook
  before touching them.**
- **`lung_granularity_check`** — act 6's morphological-subtype limit. Same.
- **`disease_hierarchy_annotation`** — reads as dead, but act 3's ontology indentation needs it.
  **Promote to serving.**
- **`dashboard_persona_trust`** — reads as dead because the backend reads `persona_candidates` from
  zone 41 instead. That is the §3.3 containment defect. **Fix the reader, keep the dataset.**
- **`breast_shortlist`** — a clinician review form, a deliverable to a person rather than a pipeline
  artifact. **Archive, do not delete.**

⚠ **A correction to §12 and the v3 mockup.** I specified act 2's AUC charts against
`validation_auc_by_disease_2` and made much of its `level` filter being load-bearing. **That was the
wrong table.** `validation_auc_by_disease` — no suffix — is 670 rows, one level, `auc_disease`, macro
**0.8230** (NaN-skipping over the 668 that score), it is produced by a **visual Prepare recipe**, and it
already feeds `compute_persona_candidates`. The `_2` variant is a 1,113-row two-level Python output that
**nothing reads at all**. Point the serving layer at v1: the filter trap disappears because it was an
artifact of picking the wrong source, and v1 also carries `hits_at_10/20/50` and `recall_at_20`, which
act 3 wants.

### 14.3 Target zone structure

**Four serving zones, one per act.** Everything in them is precomputed, small, and read whole — no
streaming, no per-request computation.

| zone | datasets | rows |
|---|---|--:|
| **`A1 Evidence base (serving)`** | `graph_node_type_counts` · `graph_node_source_counts` · `graph_relation_counts` · `graph_ppi_provenance` · `graph_label_evidence` | 8 · 7 · 18 · 7 · 3 |
| **`A2 Calibration (serving)`** | `disease_eligibility` · `pool_route_counts` · `split_audit_2` · `validation_auc_ci` · `shap_driver_frequency` · `persona_enrichment` | 3 · 4 · 3 · 670 · 14 · 670 |
| **`A3 Therapeutic area (serving)`** | `family_panel` · `top50_membership` · `pairwise_overlap` · `disease_hierarchy_annotation` | ~1.1k · ~650 · ~1.5k · 27k |
| **`A4 Shortlist (serving)`** | `dashboard_candidates` · `dashboard_persona_trust` | 129k · 13 |

Every one is a **whole-table read at startup and cache**, except `dashboard_candidates`, which is the
only dataset with a per-request `WHERE` and the only candidate for Snowflake (§12.2).

**One notebook zone**, holding evidence that is *computed in code* rather than served:
`90 Notebook — validation evidence`.

**Unchanged pipeline zones:** `00` synced, `10`/`11`/`12` features, `20` annotations, `30` modelling and
split, `31` training. These are how the model gets built; none of it is demo material and none of it
moves.

**Zones that empty out and are then retired:** `40`, `41`, `42`, `43`, `50`, `60`.

### 14.4 Per-dataset disposition

**→ A1–A4 serving (build new, all visual, all-disease per §13.1)**

`graph_relation_counts` `graph_node_type_counts` `graph_node_source_counts` `graph_ppi_provenance`
`graph_label_evidence` `disease_eligibility` `pool_route_counts` `validation_auc_ci`
`shap_driver_frequency` `persona_enrichment` `family_panel` `top50_membership` `pairwise_overlap`

**→ A1–A4 serving (move existing)**

| dataset | from | note |
|---|---|---|
| `dashboard_candidates` | 60 | convert to parquet or Snowflake (§12.2) — it is CSV today |
| `dashboard_persona_trust` | 60 | and **repoint the backend to it** |
| `split_audit_2` | 42 | 3 rows, read as-is |
| `disease_hierarchy_annotation` | 42 | act 3's indentation |
| `filter_three_axes` | 41 | act 4's funnel |
| `tractability_axis` | 41 | act 4's membrane depletion; also notebook-read |

**→ 90 Notebook (move; the notebook recomputes or reads them)**

`novel_discovery_eval` `drug_target_benchmark` `known_drug_truth` `persona_candidates`
`pool_selection_bias` `pool_reachability` `breast_panel_metrics` `breast_panel_overlap`
`family_auc_by_family` `validation_auc_by_disease` `scored_champion`

**→ 90 Notebook (adopt FIRST — currently unguarded)**

`safety_lift` `tractability_lift` `lung_granularity_check` `maturity_confound`

**→ Delete, at stage 5 only**

| dataset | why |
|---|---|
| `scored_m4` `scored_m5` `scored_m6` `scored_m8` | ablation ladder outputs; explicitly not demo material, and the ladder is reconstructable from `31 Model training` |
| `model_comparison` | the ladder's comparison table, same |
| `validation_auc_by_disease_2` | superseded by v1, read by nothing (§14.2) |
| `drug_target_benchmark_staged` | staging intermediate |
| `pool_unreachable_targets` `target_reachability` | subsumed by `pool_reachability`, which the notebook reads |
| `family_top_genes_named` `family_auc_grouped` `family_gene_agg` `family_top_genes` `family_validation_ranked` `family_validation_scored` | zone 43's own description calls the five-recipe chain **over-built**; the deliverable is `family_auc_by_family` |
| `llm_hx` | stray in Default, unreferenced |

**→ Archive, not delete**

`breast_shortlist` — a clinician review form. Export it and drop the dataset only once a copy exists
outside the flow.

### 14.5 The act 5 / 6 notebook

`nb5_interrogation_and_close.py`, following the house pattern: read the most upstream dataset that still
carries the number, compute in code, and **assert every figure**. It replaces acts 5 and 6 as flow
objects and becomes the guard for numbers that currently have none.

| section | reads | asserts |
|---|---|---|
| degree-matched enrichment | `tractability_axis` | pooled 3.29× @10, 2.42× @200; macro 3.11× @10; the estimator crossover |
| hub-bias meter | `scored_champion` | 0.59 → 0.79 by degree quintile, 17.3% → 57.0% |
| novel discovery | `novel_discovery_eval` | approved 16.88× @10, 5.04× @200; investigational 8.85× @10 |
| ground-truth provenance | `raw_ot_known_drug`, `known_drug_truth` | 82% multi-target, 8% single-target survival; curated 21.32× |
| orthogonality | `validation_auc_by_disease` × `drug_target_benchmark` | r = +0.002, R² = 0.0000 |
| **the three refuted gates** | **`tractability_lift`, `safety_lift`** | **3.16× / 0.78×, 2.07× / 1.37×, 4.62× — currently unguarded** |
| subtype limits | `lung_granularity_check`, `breast_panel_overlap` | 47/50 lung, 2/50 breast novel-only |
| the lookup-table slide | `drug_target_benchmark` | 0.9354 vs the trained model |

The last-but-one row is why this notebook is worth writing on its own merits, independent of the flow
cleanup: **four of the deck's closing numbers are currently asserted by nothing.**

### 14.6 Rules for the migration itself

- **Never touch `compute_kg` or the graph zone**, and never use a recursive build type in
  `KNOWLEDGE_GRAPH_PRIMEKG` — it walks up and renumbers every node.
- Zone moves are metadata only and safe. **Do them in one pass, verify, then stop** — do not combine a
  move with a delete.
- Rebuild a zone from its **last** dataset with update-output-schemas and stop-at-zone-boundary; one job
  with repeated `--target`.
- After the moves, **rewrite every zone `shortDesc`.** They are demo-facing prose no index covers, three
  of them still quote pre-champion numbers, and zone 41's still says *"11.4x at top-10"* and
  *"2.4-2.9x"* — both wrong (§10.4, §12.11).
- Re-run `tools/build_recipe_index.py --refresh` after the moves; the zone map is snapshotted there.
- ⚠ **Never use `RECURSIVE_FORCED_BUILD` to build a serving table.** Targeting
  `shap_driver_frequency` recursively queued **41 activities** — the whole feature pipeline, including
  `compute_dwpc_go_metapaths` (the Class 2 recipe Phase 3 is sensitive to) and
  `compute_enriched_rwr_score_1`. Aborted before damage; the two recipes that had started kept their
  original build dates. Serving tables sit at the end of long chains, so build them
  **`NON_RECURSIVE_FORCED_BUILD`, one link at a time**, or recursively with
  `--stop-at-zone-boundary`. The CLAUDE.md warning about recursive builds is about the graph project;
  this is a second, separate reason to distrust them.
- `dku dataset count` scans the file — on `scored_champion` (478 MB CSV) it exceeds a two-minute
  timeout. Use `dku dataset info`, which reads the cached row count and the last-build stamp.


---

## 15. Notebook review — nb1 to nb5 against the notebook principle

**The principle:** a notebook reads the **most upstream** dataset that still carries the number and
recomputes it in code. Reading a derived table and asserting its contents proves only that the recipe
still runs — not that the number is right. That is due diligence in name only.

### 15.1 The audit

20 distinct datasets are read across the five notebooks. **Seven are upstream; thirteen are derived.**

| notebook | upstream reads | derived reads | verdict |
|---|---|---|---|
| **nb3b** hub-bias meter | `scored_champion` | — | **exemplar.** Its own comment says it best: *"it has no recipe, so this notebook IS its artifact"* |
| **nb5** data exploration | `graph_nodes`, `graph_edges`, `raw_disease_disease`, `enriched_graph_features_candidate_psplit` | `validation_auc_by_disease` | **near-exemplar.** Counts associations from raw edges rather than reading a summary |
| **nb1** features & config | `psplit_train_set`, `scored_champion` | — | structurally clean, but **factually stale** — see §15.3 |
| **nb2** splitting & pool | `enriched_graph_features_candidate_psplit` | `pool_reachability`, `pool_selection_bias`, `split_audit_2` | three of four reads are answers |
| **nb3** validation | `scored_champion` | `validation_auc_by_disease`, `family_auc_by_family`, `drug_target_benchmark` | asserts three numbers it did not compute |
| **nb4** results | `raw_ot_known_drug`, `scored_champion` | `breast_panel_metrics`, `breast_panel_overlap`, `filter_three_axes`, `known_drug_truth`, `novel_discovery_eval`, `persona_candidates`, `tractability_axis` | **worst offender** — seven derived reads, mostly read-and-assert |

### 15.2 The refinement the migration forces

A blanket "always recompute" is wrong once some of these tables are **served to the webapp**. The rule
splits on destination:

| the dataset is… | what the notebook does | what the assertion proves |
|---|---|---|
| **deleted** by the migration | compute from upstream; this code becomes the sole source of truth | the number is right |
| **served to the webapp** | compute from upstream **and compare to the served table** | the number is right **and** the serving layer agrees — an independent reimplementation check |
| an upstream input | read directly | n/a |

The second row is the valuable one and it is currently absent everywhere. `validation_auc_ci`,
`filter_three_axes`, `persona_enrichment`, `family_panel` and `top50_membership` will all be read by
the app; a notebook that recomputes them from `scored_champion` and diffs against the served copy is
the only thing standing between a broken recipe and a wrong number on screen in front of a customer.

### 15.3 nb1 is pinned to the retired champion

`nb1` declares `FEATS12` — twelve features — and a `REJ` list of rejected ones. **`prox_closest` and
`prox_kernel` are in the champion's fourteen, and `nb1` has `prox_closest` in `REJ`.** The notebook is
still describing `m3-f12`, two champions ago, and its null-rate and correlation sections therefore
report on the wrong feature set.

This is the same drift as the narrative's *"12 network-topology features"* (§12.11 item 2). Both trace
to the same stale source. **Fix `nb1` first** — it is a four-line change and every claim in §4 of
`TARGET_PRIORITIZER` rests on it.

### 15.4 Per-notebook revision

**nb1 — features & config.** Replace `FEATS12` with the champion's fourteen sourced from
`tools/model_registry.json`, and move `prox_closest` / `prox_kernel` out of `REJ`. Re-derive the null
gaps and correlations. Keep the 25% sampling — the comment explaining the OOM is correct and earned.

**nb2 — splitting & pool.** Compute the split audit, reachability and selection bias from
`enriched_graph_features_candidate_psplit` and the psplit sets rather than reading three summaries.
`split_audit_2` stays as a serving dataset, so add the comparison. `pool_reachability` and
`pool_selection_bias` are then deletable.

**nb3 — validation.** Compute per-disease and per-family AUC directly from `scored_champion` — the
Mann-Whitney form is eight lines and is already written in `compute_validation_auc_by_disease_2`. Then
compare against the served `validation_auc_ci`. This turns three read-and-assert sections into three
genuine checks, and it is what lets `validation_auc_by_disease_2` be deleted.

**nb3b — hub-bias meter.** No change. It is the model the others should follow. Its content moves into
`nb6` §5.2, and this file is retired once that lands.

**nb4 — results.** The big one. Recompute the novel-discovery lift, the three-axis filter and the
tractability axis from `scored_champion` plus the annotation tables, and keep only
`raw_ot_known_drug` as an upstream read. `breast_panel_metrics` and `breast_panel_overlap` become
comparisons against the generalised `family_panel` / `pairwise_overlap`, not sources. Acts 5 and 6
leave for `nb6`, which removes roughly half of nb4's current body.

**nb5 — data exploration.** Repoint its one derived read (`validation_auc_by_disease`) at the served
`validation_auc_ci`, or compute it. Otherwise leave it alone.

**nb6 — the interrogation and the close.** New, written (§14.5). It adopts `tractability_lift`,
`safety_lift` and `lung_granularity_check`, which nothing currently reads, and asserts the three
refuted gates. **Until it runs green the flow must not be pruned.**

### 15.5 What the revision unlocks

Once nb2, nb3 and nb4 compute rather than read, these become deletable without losing a guarantee:
`pool_reachability`, `pool_selection_bias`, `validation_auc_by_disease_2`, `breast_panel_metrics`,
`breast_panel_overlap`, `known_drug_truth`, `drug_target_benchmark`, and zone 43's five-recipe family
chain. That is the cleanup in §14.4 made safe — **the notebooks stop depending on the datasets the
migration wants to delete.**

