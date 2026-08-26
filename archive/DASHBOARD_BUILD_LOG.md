# Dashboard & flow build log — archived 2026-08-26

Sections 11–35 of the former `docs/demo/DASHBOARD_DESIGN.md`: the chronological record of the
webapp/native-dashboard evaluation, the flow migration, notebook codification, the pruning passes
and the incidents found along the way.

Moved out because `DASHBOARD_DESIGN.md` is now a technical supporting document to
`DEMO_NARRATIVE.md`, not a build journal. Kept rather than deleted: several entries are the only
record of traps that cost real time — the stale middle link (17), `replace-input` not touching
Python code (30.1), the frozen reference masking stale mirrors (33.3), and three separate occasions
where a "delete what nothing reads" pass pointed at the serving layer.

Durable decisions belong in `DECISIONS.md`; durable traps in the `target-id` skill.

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
| **A** | §12.2 | six Group recipes → `graph_relation_counts`, `graph_node_type_counts`, `graph_node_source_counts`, `graph_ppi_provenance`, `graph_label_evidence`, `calibration_histograms`, `shap_driver_frequency` | trivial, 3–40 rows each |
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
| **`A2 Calibration (serving)`** | `disease_eligibility` · `split_audit_2` · `validation_auc_ci` · `shap_driver_frequency` · `persona_enrichment` | 2 · 3 · 670 · 14 · 670 |
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
- ⚠ **`dku job run` returns as soon as the job is *queued*, not when it finishes.** Chaining builds by
  sleeping a guess silently produces wrong data: `compute_shap_driver_frequency` failed outright with
  *"Root path of the dataset does not exist"*, and `compute_pairwise_pairs` did something worse — it
  **succeeded with 672 rows instead of 2,882**, because its inputs were still being written. A join
  that reads a half-written input does not error; it under-joins. **Poll `dku job status` until the
  state leaves `RUNNING` before starting the next link**, or put the whole chain in one job with
  repeated `--target` and let DSS order it.


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


---

## 16. Serving layer — build log

Stage 1 of §14.1, built and verified. Every figure below was checked against an independently computed
value before being accepted.

| zone | dataset | rows | recipe | verified against |
|---|---|--:|---|---|
| **A1** | `graph_node_type_counts` | 8 | Group | sums to 113,391 |
| | `graph_node_source_counts` | 7 | Group | sums to 113,391 |
| | `graph_relation_counts` | 18 | Group | sums to 2,851,510 |
| | `graph_ppi_provenance` | 7 | Group + pre-filter | sums to **520,380** — proves the filter fired |
| | `graph_label_evidence` | 3 | Group + pre-filter | sums to **323,786** |
| **A2** | `validation_auc_ci` | 670 | **Prepare, Hanley–McNeil in GREL** | every documented `auc_se` to ≤0.0001; TNBC `hi95` = 1.0410 |
| | `persona_enrichment` | 670 | Prepare | — |
| | `disease_eligibility` | 2 | Group | **25,996 / 1,157** |
| | `shap_driver_frequency` | 14 | Prepare (split+fold) → Group | **exact match** to an independent Python aggregation, all 14 features |
| | `split_audit_2` | 3 | moved | — |
| **A3** | `family_panel` | 670 | **Join** | carries AUC, CI, family, `hop_depth` — generalises the hardcoded breast `PANEL` dict |
| | `top50_membership` | 650 | **Filter** (`rank_in_disease` already exists) | 13 × 50 |
| | `pairwise_overlap` | 156 | **self-Join → Group** | HER2+×TNBC = **14**, LumA×LumB = **22**, both matching `breast_panel_overlap` |
| | `disease_hierarchy_annotation` | 27,153 | moved | — |
| **A4** | `dashboard_candidates` | 129,253 | moved | — |
| | `dashboard_persona_trust` | 13 | moved | — |

**Every recipe is visual.** No Python was needed anywhere in the serving layer — including the two that
looked like they would need it: the Hanley–McNeil confidence interval (a GREL formula) and the SHAP
driver frequency (Prepare split + fold, then Group).

**`pool_route_counts` was dropped, not built.** The three route admissions are exactly the row counts of
`enriched_dwpc_GGD` (3,380,853), `enriched_dwpc_GPGD` (5,373,706) and `enriched_dwpc_GCD` (42,227),
which DSS already holds as `records:COUNT_RECORDS`. Under §12.2's rule those are metrics, not a dataset.
The pool union and the three splits come from `split_audit_2`. A2 therefore has **five** datasets, not
the seven originally planned.

**`Refresh_serving_layer`** now carries a build step per zone and triggers on `graph_nodes`,
`graph_edges`, `edge_metadata`, `validation_auc_by_disease` and `dashboard_candidates`. It is
**inactive** — activating it is a standing automation and needs a human decision.

**Left behind by a failed first attempt at the self-join, to delete in stage 5:**
`top50_membership_b`, `top50_pairs`, and their recipes `copy_top50_b`, `compute_top50_pairs`. They are
superseded by the `top50_slim_a` / `top50_slim_b` pair.


---

## 17. The stale-middle-link incident — read this before rebuilding anything

Found while converting the serving layer to parquet. **It is the most important finding in this
document** and it changes how §14's migration must be sequenced.

### 17.1 What happened

`dashboard_candidates` sits at the end of a three-link chain:

```
target_candidates_2   built 2026-08-21 08:15   ← current
   └── candidates_annotated   built 2026-08-19 10:09   ← TWO DAYS STALE
          └── dashboard_candidates   built 2026-08-21   ← current content, stale parent
```

The middle link had **not been rebuilt since its own input changed**. `dashboard_candidates` happened
to carry the *correct* 08-21 scores anyway. So the flow looked fine and served the right numbers, while
being one forced rebuild away from serving the wrong ones.

I then force-rebuilt `dashboard_candidates` as part of the parquet conversion. It faithfully recomputed
itself from the **stale** parent and every rank changed:

| | before | after the stale rebuild |
|---|---|---|
| #1 | TP53 | EP300 |
| #2 | EP300 | TP53 |
| **ERBB2** | **#14** | **#13** |
| also in the top 15 | EGFR, BRCA1, PTPN11, MAPK1 | AKT1, STAT3, JAK1, SMARCA4 |

Row count identical. Schema identical. Build green. **Every number the demo quotes silently wrong.**

Fixed by rebuilding `candidates_annotated` from `target_candidates_2`, then the chain. Verified
restored: ERBB2 back at #14, `pairwise_overlap` back to 156 rows with HER2+×TNBC = 14 and
LumA×LumB = 22, `shap_driver_frequency` back to 14 features with the original counts.

### 17.2 It explains the narrative's "contradiction", and I had the diagnosis wrong

§12.11 claimed `DEMO_NARRATIVE.md` §7 had *drifted* and was wrong by 19 places on AKT1. **It had not
drifted.** §7 reads *"ERBB2 #13, TP53 #2, PIK3CA #7, AKT1 #10"* — which matches the **08-19 build
exactly**. §6 reads *"ERBB2 rank 14, PIK3CA rank 5"* — which matches the **08-21 build exactly**.

**Both sections were correct when they were written.** They disagree because the flow served two
different answers two days apart, not because anyone was careless. Retract the §12.11 accusation: the
right correction is to re-derive both from a chain that has been proven consistent, and to date-stamp
the derivation.

### 17.3 What this changes

**A green build is not evidence of correct data.** Row count, schema and build status were all
unchanged. The only thing that caught it was checking one derived value — HER2+×TNBC overlap — against
a number computed independently beforehand. Without that check the wrong ranking would have shipped.

**The integrity check from §12.2 must cover the chain, not the leaf.** Comparing a serving table to its
own source proves nothing when the source is itself stale. The check has to compare against the
*most upstream* dataset that carries the number — which is exactly the notebook principle in §15,
arriving from the other direction.

**Sequencing rule, added to §14.1:** before any migration rebuild, **verify the chain is consistent
first** — for every serving dataset, confirm each link's `last_build` is not older than its parent's.
A stale middle link converts a routine rebuild into silent data corruption. Do this before stage 1, not
after.

⚠ **`candidates_annotated` was stale for six days and nothing detected it.** There is no check in the
project that would have. That is the gap to close before the demo, not after.

### 17.4 Zone integration

`60 Dashboard (serving)` is **retired** — its contents (`candidates_annotated`, `disease_pool_sizes`,
`drug_evidence_pairs` and the two recipes that build them) moved into `A4 Shortlist (serving)`, which
now holds the whole shortlist chain rather than only its output. The serving zones **replace** the old
one rather than sitting beside it; zones 40–43 and 50 follow the same way as their contents move to
`90 Notebook` in stage 4.


---

## 18. The zone overhaul — 13 zones to 10, and 40–50 deprecated

§14.3 proposed serving zones but left 30–50 alone as "pipeline". That was wrong: it grew the flow from
13 zones to 17 by stacking new structure on top of old. Zones **40, 41, 42, 43 and 50 were all
*validation* zones — and validation is now the notebook's job**, so they should not exist at all.

### 18.1 The function test

Every dataset now answers one question: **does the webapp serve it, does a notebook read it, or is it
needed to build the model?** Three answers, three groups of zones — and nothing else survives.

| group | zones | what it is for |
|---|---|---|
| **SOURCE** | `00 Imported from DEMO_KG_LS` | the cross-project contract |
| **BUILD** | `10 Features` · `20 Annotations & split key` · `30 Split & modelling table` · `31 Train & score` | everything required to produce the champion's scores |
| **SERVE** | `A1` · `A2` · `A3` · `A4` | what the webapp reads, precomputed |
| **EVIDENCE** | `90 Notebook — validation evidence` | **staging for deletion**, not a permanent home |

### 18.2 What was done

**Five zones deleted.** `40`, `41`, `42`, `43` and `50` emptied into the serving zones and `90`.

⚠ **A merge that was tried and reverted.** `11 Features - matrix` and `12 Features - assembly` were
folded into `10 Features` on the argument that the Cypher/Python/assembly split is an implementation
detail. **That was wrong on readability** — it produced a single 45-item zone, and the three-way split
tells a reader *how* a feature is computed, which is the first thing you need when one of them breaks.
Reverted to 10 / 11 / 12.

The revert also exposed a mistake in how the merge was done: it moved every `enriched_*` dataset by
glob, which swept up three annotation tables from zone 20 and two feature tables from zone 30 that had
nothing to do with the merge. **Do not move flow items by name pattern** — enumerate them, or the blast
radius is whatever the prefix happens to match. All five are back where they belong.

**Renamed to their function:** `30 Modeling table & split` → `30 Split & modelling table`;
`31 Model training` → `31 Train & score` (it now holds `scored_champion`, which belongs with the model
that produced it rather than in the notebook staging zone — it is the *most upstream* dataset the
notebooks recompute from, which is precisely why it must not be staged for deletion).

**Where the old validation zones went:**

| from | to | why |
|---|---|---|
| `validation_auc_by_disease` + its 3-link chain, `persona_candidates` | **A2** | they feed `validation_auc_ci` and `persona_enrichment` |
| `target_candidates_2`, `persona2_scored(_shap)`, `validation_set_personas_2`, `top_annotated`, `top_candidates`, `filter_three_axes` | **A4** | the whole shortlist chain, from scoring to the funnel |
| `novel_discovery_eval`, `drug_target_benchmark`, `known_drug_truth`, `pool_reachability`, `pool_selection_bias`, `safety_lift`, `tractability_lift`, `tractability_axis`, `lung_granularity_check`, `breast_panel_*`, `family_auc_by_family` | **90** | notebook evidence, to be recomputed then deleted |
| `scored_m1`–`m6`, `m8`, `model_comparison`, `validation_auc_by_disease_2`, `drug_target_benchmark_staged`, `maturity_confound`, `pool_unreachable_targets`, `target_reachability`, the 6-dataset family chain, `breast_shortlist` | **90** | dead ends, staged so stage 5 has one place to look |

### 18.3 Result

**13 zones before this work, 17 at the low point, 12 now** — and the serving zones *replaced* zone 60
rather than sitting beside it. A reader opening the flow sees source → build → serve, with one clearly
labelled holding pen for what is on its way out.

`90 Notebook` holds **62 items**, which looks alarming and is the point: that is the size of the cleanup
that was invisible while it was spread across five zones with reassuring names.

> ⚠ **Nothing in `90` may be deleted until `nb6_interrogation_and_close` runs green** (§17.1). Two of
> its datasets are the only copy of the punch line's evidence.


---

## 19. Zone 20 reviewed against the visual-over-Python rule

Five Python recipes and two syncs. **Three of the five are correctly Python. Two are not, and the two
that are not share a duplicated block that should be a dataset.**

| recipe | lines | verdict |
|---|--:|---|
| `extract_hetionet_disease_slim` | 26 | ✅ **correctly Python.** An HTTP fetch of a static 137-term resource. The house rule explicitly allows this — *"Python extracts only load and parse"* |
| `compute_gene_localization` | 90 | ✅ **correctly Python.** BFS transitive closure down the GO hierarchy from `GO:0005886` / `GO:0009986` / `GO:0005576` to every descendant term. DSS has no visual recursion; there is no Join or Prepare that expresses "all descendants of" |
| `compute_disease_family_id` | 184 | ✅ **correctly Python.** `networkx` ancestor-lifting and nearest-anchor search over MONDO. Same reason, more so — and its own comment records that a naive connected-components grouping collapses the eligible population, which is exactly the kind of judgment that belongs in reviewed code |
| `compute_gene_safety` | 87 | ⚠️ **should be visual.** Two joins, two derived columns, a column selection, and ~25 lines of diagnostic `print`s |
| `compute_gene_druggability` | 98 | ⚠️ **partly.** Three joins that should be visual Joins, plus a 10-branch precedence cascade that is defensible as code |

### 19.1 The finding that matters more than the rule

`compute_gene_safety` and `compute_gene_druggability` **each rebuild the same symbol→gene_index
crosswalk, and the two blocks are byte-identical** — seven lines of entrez casting, a merge and a
`drop_duplicates("symbol")`. `gene_safety`'s own comment admits it: *"same crosswalk as the druggability
chain"*.

> **Extract it once as a visual Join into a `gene_crosswalk` dataset and have both consume it.**

That is worth more than the visual/Python conversion on its own. Two copies of an identifier crosswalk
is a drift hazard of exactly the kind §17 just demonstrated: if one is edited and the other is not,
druggability and safety silently disagree about which gene is which, and nothing in the flow would
report it. It also removes the `entrez_id.astype("int64").astype(str)` cast from two places — a cast
that is load-bearing and easy to get subtly wrong.

### 19.2 What a visual `compute_gene_safety` looks like

- **Join** `gene_names` × `graph_nodes` on entrez, pre-filtered to `node_type = 'gene/protein'` →
  `gene_crosswalk` *(shared, §19.1)*
- **Join** `raw_ot_safety` × `gene_crosswalk` on `symbol`, INNER
- **Prepare**: formula `lof_intolerant` = `if(isBlank(lof_oe_upper), null, if(lof_oe_upper < 0.35, 1, 0))`;
  formula `safety_flag` = the three-state cascade; keep-columns

Three visual recipes replacing 87 lines. ⚠ **The join keys need `--auto-cast`** — the Python casts
`node_id` to string and `entrez_id` to int64-then-string, so the two sides do not match natively. That
cast is the whole reason this looks harder than it is.

**The ~25 lines of coverage and distribution `print`s do not belong in a recipe at all.** They are
exactly the "compute it in the notebook" material of §15 — coverage percentages, the `safety_flag`
distribution, the LOEUF describe. Move them into `nb6` where they can be *asserted* rather than printed
into a job log nobody reads.

### 19.3 Where the rule should not be applied

`compute_gene_druggability`'s ten-branch `np.select` cascade assigns `druggability_class` by precedence:
OT class first, then subcellular flags, then our own localisation. Expressed in GREL that is a ten-deep
nested `if()`. **The rule says prefer visual; readability says leave it.** Convert the three joins,
leave the cascade as code, and say so in the recipe description so the next reviewer does not
re-litigate it.

The same judgment protects `compute_disease_family_id`: a rule mechanically applied would push a
networkx traversal into something DSS cannot express, and the result would be worse on every axis.


---

## 20. `gene_crosswalk` extracted and `compute_gene_safety` converted to visual

Built as a **parallel chain**, verified against the Python output, and **not yet swapped in** — §17's
lesson is that replacing something the flow depends on is the last step, not the first.

### 20.1 What was built

| recipe | type | output | rows |
|---|---|---|--:|
| `compute_graph_genes` | **Filter** | `graph_genes` | 20,861 |
| `compute_gene_crosswalk` | **Join** (`entrez_id = node_id`, auto-cast) | `gene_crosswalk` | 20,861 |
| `compute_gene_safety_join` | **Join** on `symbol` | `gene_safety_joined` | 20,837 |
| `compute_gene_safety_best` | **TopN**, 1 per `node_index` | `gene_safety_best` | 20,707 |
| `compute_gene_safety_v2` | **Prepare** — 2 formulas, rename, select | `enriched_gene_safety_v2` | 20,707 |

**Result: 0 mismatched cells across 20,707 genes × 10 columns — 207,070 cells compared.** The comparator
was sanity-checked against deliberate corruption so a false green would be visible.

87 lines of Python replaced by five visual recipes, and the crosswalk is now a dataset both
`gene_safety` and `gene_druggability` can consume instead of each rebuilding it.

### 20.2 Two things the conversion surfaced that the Python hid

**The `drop_duplicates("symbol")` never fires.** `gene_crosswalk` is 20,861 rows over 20,861 distinct
symbols — the crosswalk is already 1:1, and every gene/protein node maps. The line is dead code that
looks like a safeguard.

**But `drop_duplicates("gene_index")` fires, and it is non-deterministic.** `raw_ot_safety` has 78,691
rows over 77,084 symbols — **477 symbols carry more than one row** (2,084 rows), because one symbol can
have several ENSG entries. Of those 477, **15 disagree on `lof_oe_upper`** and **none disagree on
`has_safety_liability`**. The Python resolves them by keeping whichever row pandas happened to order
first. The visual chain replaces that with a stated rule — **keep the most constrained row** — via TopN
ranked ascending on `lof_oe_upper`.

### 20.3 The bug I introduced doing it, and why verification caught it

The first TopN ranked on `lof_oe_upper` directly. **DSS sorts nulls first**, so for a gene with one
null-constraint row and one measured row, the *null* won. Six genes lost a real LOEUF measurement — a
tie-break that systematically preferred missing data, which is worse than the arbitrary pick it
replaced.

Fixed with a computed sort key, `if(isBlank(lof_oe_upper), 9999, lof_oe_upper)`, so absent constraint
always sorts last. After the fix the two versions agree on every cell.

> This is the third time in this work that a green build produced wrong data (§14.6 the raced join, §17
> the stale middle link, and this). **The pattern is identical every time: DSS reports success, the row
> count looks plausible, and only a comparison against an independently derived value exposes it.**

### 20.4 Not done, deliberately

`enriched_gene_safety_v2` is **not wired into the flow**. Swapping it means repointing
`compute_gene_druggability` and everything downstream, then rebuilding the annotation chain — which
moves data the demo depends on. Sequence it with the §14.1 stages, verify the chain is fresh first
(§17.3), and do it in one job.

`compute_gene_druggability` still rebuilds its own copy of the crosswalk. Converting its three joins and
pointing it at `gene_crosswalk` is the same shape of change and should follow immediately, since the
duplication is the actual risk (§19.1).


### 20.5 `compute_gene_druggability` converted, and both swapped in

Same shape, verified the same way: **0 mismatched cells across 20,861 genes × 9 columns — 187,749
cells compared**, including the ten-branch `druggability_class` cascade transcribed into GREL.

| recipe | type | output |
|---|---|---|
| `compute_ot_drug_mapped` | **Join** on `symbol`, using the shared `gene_crosswalk` | `ot_drug_mapped` |
| `compute_drug_joined` | **Join** `enriched_gene_localization` LEFT `ot_drug_mapped` | `drug_joined` |
| `compute_drug_classified` | **Prepare** — 6 formulas | `drug_classified` |
| `compute_drug_best` | **TopN**, 1 per gene ranked by evidence quality | `drug_best` |
| `compute_gene_druggability_v2` | **Prepare** — column select | `enriched_gene_druggability_v2` |

**§19.3 was over-cautious.** It recommended leaving the ten-branch cascade as Python on readability
grounds. In a Prepare formula it is one nested `if()` that reads in precedence order and reproduces the
Python exactly. The recommendation is withdrawn — convert it.

⚠ **`isNotBlank` does not exist in DSS GREL.** Only `isBlank`; use `!isBlank(x)`. The recipe fails at
build time with *"Unknown function 'isNotBlank' (Parsing error at offset 256)"*, which is at least loud.

**The druggability dedupe was already deterministic** and is preserved: rank by evidence source
(OT target class → OT subcellular → GO cellular component → none) and keep the best. That is a stated
rule, unlike the safety recipe's arbitrary `drop_duplicates`, and TopN expresses it directly.

**Swap done, downstream NOT rebuilt.** All seven consumers repointed —
`compute_safety_lift`, `compute_drug_target_benchmark_staged`, `compute_pool_reachability`,
`compute_tractability_axis`, `compute_tractability_lift` and `decorate_target_candidates`. The two
Python outputs are now orphaned and go to stage 5 with their recipes.

> Downstream datasets are deliberately left **out-of-date rather than rebuilt**. DSS marks them stale in
> the flow, which is the visible-staleness property §12.2 argued for — and after §17 a rebuild is a
> deliberate act with a freshness check in front of it, not a reflex.


---

## 21. Chain-freshness check — built, run, and what it found

`tools/check_freshness.py`. For every dataset it compares `last_build` against every input's, and
reports anything built **before** something it depends on. This is the check that would have caught
§17's six-day-stale middle link. Run it **before** a migration rebuild.

```bash
./tools/check_freshness.py            # whole project, exit 1 if stale
./tools/check_freshness.py --zone A4  # one serving zone
```

### 21.1 What it found: 130 datasets, 71 stale relationships — but only a handful matter

**49 of the 71 are timestamp churn from zone 00.** The aborted recursive build (§14.6) re-ran the Sync
recipes, so `graph_nodes`, `graph_edges`, `gene_names` and the `raw_ot_*` copies all carry a
2026-08-24 19:57 stamp. The *content* is unchanged — DEMO_KG_LS has not moved — but every descendant
now looks stale. **A Sync that re-copies identical data bumps the timestamp and lights up sixty
downstream datasets.** The check reports timestamp order, not content, and that limitation has to be
read with the output.

Of the 22 genuine findings:

| class | count | disposition |
|---|--:|---|
| downstream of the §20 swap | 7 | **expected** — deliberately not rebuilt |
| ablation models in zone 90 | 6 | staged for deletion, irrelevant |
| dead objects from the failed self-join | 2 | `top50_membership_b`, `top50_pairs` — stage 5 |
| genuinely worth attention | **3** | below |
| never built | 3 | below, and one is serious |

### 21.2 A false positive worth knowing about

`disease_pool_sizes` (built 08-19) is flagged against `target_candidates_2` (08-21). **Its content is
correct** — 13 personas, HER2+ at 12,272, matching the current population exactly. The timestamp is
older; the data is not stale. A timestamp check cannot tell the difference, so a flagged dataset needs
one content probe before anyone rebuilds it.

### 21.3 The serious finding: A2's serving chain cannot be rebuilt

```
validation_set_scored           built 2026-08-21 08:29   ✓
   └── validation_set_scored_windows      NEVER BUILT    ✗
          └── validation_set_scored_grouped   NEVER BUILT ✗
                 └── validation_auc_by_disease  670 rows, built 08-21 08:30  ✓
                        └── validation_auc_ci   670 rows  ← A2 SERVING
```

Both intermediate links are **empty**, while the dataset downstream of them holds correct data. The
lineage is real — confirmed against the live recipe, not just the snapshot — so
`validation_auc_by_disease` was built when the intermediates had data and they were cleared afterwards.

**The number is right and it is unreproducible.** Macro AUC 0.8230 — the figure act 2 leads with, and
the source of every confidence interval in `validation_auc_ci` — sits on a chain with a hole in it. Any
attempt to rebuild it recursively regenerates two intermediates first, from a `validation_set_scored`
that is itself two rebuild-generations downstream of the graph.

Nothing in the project reported this. It is not a wrong number today; it is a number that cannot be
recovered if anything touches it — which after §17 is the same risk with a longer fuse.

**Fix before the demo:** rebuild `validation_set_scored_windows` and `_grouped` from
`validation_set_scored`, confirm `validation_auc_by_disease` still reproduces macro **0.8230** over 668
scored diseases, then rebuild `validation_auc_ci` and re-verify the six documented `auc_se` values
(§20.1). Do it as an explicit two-step, not a recursive build.

### 21.4 Also never built

`family_gene_agg` and `family_validation_ranked` — both in zone 43's five-recipe chain that its own
description called over-built, both staged for deletion. Harmless, and further evidence the chain was
never load-bearing.

### 21.5 The A2 chain repaired — and the number did not move

Rebuilt explicitly, one link at a time, with the pre-repair state captured first so a divergence would
be visible rather than inferred.

| step | result |
|---|---|
| `validation_set_scored_windows` | rebuilt from `validation_set_scored` |
| `validation_set_scored_grouped` | rebuilt |
| `validation_auc_by_disease` | 670 rows, 668 scored, **macro 0.8230, median 0.8623** — **0 mismatched cells across 670 diseases × 7 columns** against the pre-repair copy |
| `validation_auc_ci` | 670 rows, **0 mismatched cells × 7 columns**; the six documented `auc_se` still reproduce, TNBC's `hi95` still 1.0410 |

**The chain is now reproducible and the number is unchanged.** That is the outcome worth having: the
hole is closed *and* nothing moved, so act 2's headline figure is now recoverable rather than merely
correct.

Two datasets became stale as a direct consequence and are **left that way deliberately**:
`persona_candidates` (downstream of `validation_auc_by_disease`) and `family_panel` (downstream of
`validation_auc_ci`). Their parents' content is verified byte-identical, so rebuilding them changes
nothing — it is timestamp hygiene, and `compute_persona_candidates` re-runs persona scoring, which is
not a thing to trigger casually.

### 21.6 Two bugs in the check itself

**Saved models are not datasets.** A scoring recipe takes a model id as an *input* (`hJLGoYn4`,
`Lx5Mz2hY`…), and a model has no `last_build`, so nine of them reported as permanently "never built"
parents. Both sides of the graph now filter to names DSS lists as datasets.

**And the first version reported 71 findings when 49 were noise.** The signal is only readable once
zone-00 sync churn is separated out, which the tool does not yet do for you — read the output with
§21.1 in hand, or pass `--zone` to scope it.

### 21.7 Standing state after the repair

**23 genuine findings, none of them unexpected:** 7 downstream of the §20 annotation swap, 6 ablation
models in zone 90, 2 dead self-join leftovers, 2 the propagation above, 3 in the zone-43 chain slated
for deletion, and **3 pre-existing** — `disease_hierarchy_annotation` (three days behind
`disease_family_id`, and it is an **A3 serving dataset**), `disease_pool_sizes` (timestamp only —
content verified correct, §21.2), and `maturity_confound` in zone 90.

> `disease_hierarchy_annotation` is the one to deal with before the demo: act 3's ontology indentation
> reads it, and it has been stale since 2026-08-17.



---

## 22. The notebooks mapped to the MLOps lifecycle

Prompted by a simple observation: **the notebooks are numbered by the document's sections (§3–§8), not
by the order the work happens in.** `nb5` covers data understanding — the first thing anyone does — and
is numbered last. A reviewer following the numbers reads the lifecycle backwards at both ends.

The full map now lives in [`notebooks/README.md`](../../notebooks/README.md). Two structural findings
came out of building it.

### 22.1 `nb1` spans two stages that the split sits between

Its §4 half analyses features **on the training set** — stage 2, pre-split. Its §6 half chooses the
operating threshold — stage 4, post-split. Between them, chronologically, sits `nb2`'s entire subject.

Read as one unit it invites exactly the wrong inference: that the threshold was chosen before the data
was split. It was not, but the file's shape says otherwise. **Split it when someone next touches it** —
this is a due-diligence artifact and its structure is part of the argument.

### 22.2 The bias audit is measured twice, and that is correct

`nb3` §7.2 and `nb3b` look like duplication and are not:

| | question | about |
|---|---|---|
| `nb3` §7.2 | does the top 50 **over-sample** high-degree genes? | the **ranking** |
| `nb3b` | with biology held constant, does the model **under-score** poorly-connected true targets? | **detection** — the 0.59 → 0.79 finding |

They point opposite ways and both are true, which is precisely the shape of the narrative's Q2. The real
duplication is one I introduced: `nb6` §5.2 reimplements `nb3b`. `nb3b` stays canonical until acts 5–6
are signed off, then retires.

### 22.3 Distance from the notebook rule, measured

Zone 90 is a staging area for deletion. A notebook still reading from it has not been converted.

| notebook | zone-90 reads | |
|---|--:|---|
| `nb3b`, `nb5`, `nb1` | **0** | ✅ already conform |
| `nb2` | 2 | `pool_reachability`, `pool_selection_bias` |
| `nb3` | 2 | `drug_target_benchmark`, `family_auc_by_family` |
| `nb4` | 5 | worst — `breast_panel_metrics/_overlap`, `known_drug_truth`, `novel_discovery_eval`, `tractability_axis` |
| `nb6` | 7 | by design — it **adopts** them so they are guarded before deletion |

**16 zone-90 reads stand between the current state and a clean deletion.** That is the actual size of
the zone-90 cleanup, and it is notebook work, not flow work.

### 22.4 One defect fixed now

`nb6` read `enriched_gene_druggability` — the dataset §20.5 orphaned when the visual chain was swapped
in. It would have loaded a table nothing maintains. Repointed to `enriched_gene_druggability_v2`.

Worth noting how it surfaced: not from the swap, which looked complete, but from mapping every
notebook's reads against its zone. **A swap that repoints every *recipe* still leaves *notebooks*
pointing at the old dataset** — they are not in the flow graph, so `replace-input` cannot reach them.
Add a notebook grep to any future dataset swap.

### 22.5 Deliberately not done

**The notebooks are not renumbered.** Lifecycle order is more useful than document order, but the
numbers appear in 344 `claims.tsv` rows, 99 assertion rows, `TARGET_PRIORITIZER.md`, the `target-id`
skill and inside `nb3`/`nb4` themselves. The generated files rebuild, but the prose does not, and the
internal `§4.1` / `§7.3` numbers — which do the real navigating — already tie to the document. The
reading order is documented instead.

**Zone 90 is not yet pruned**, and the final zone integration and rebuild are deferred until the webapp
and notebook pictures are both settled.


---

## 23. The DSS notebooks are on the retired model — do not pull them

**Yes, the CLI supports reusing them:** `dku notebook list` / `get` return full `.ipynb` JSON, and
`tools/pull_notebooks.py` (new) flattens them to diffable `.py`. Running it produced a result that
changes the plan.

### 23.1 All five have drifted, in both directions

| notebook | DSS lines | mirror lines | DSS assertions | mirror assertions | DSS figures | mirror figures |
|---|--:|--:|--:|--:|--:|--:|
| `nb1_features_and_config` | 134 | 96 | 6 | **7** | **3** | 0 |
| `nb2_splitting_and_pool` | 65 | 60 | 15 | 15 | 0 | 0 |
| `nb3_validation_and_plots` | 182 | 107 | 8 | **10** | 4 | **7** |
| `nb4_results_three_axes` | 85 | 172 | 16 | **19** | 0 | **6** |
| `nb5_data_exploration` | 110 | 109 | 0 | 0 | 0 | 0 |

**Neither side is a superset.** DSS is ahead on *structure* — the user has rebuilt all five with proper
markdown cells, so sections are navigable in Jupyter instead of buried in `# ==== ====` comments — and
on nb1's three figures. The mirrors are ahead on assertions and on nb4's two figures.

### 23.2 The finding that matters: DSS runs against `scored_m3`

`nb1` and `nb3` in DSS read **`scored_m3`** where the mirrors read **`scored_champion`**. Not as a build
stamp — as the analysis input:

- `nb1` line 98 — the §6.3 operating-threshold analysis for obesity
- `nb3` line 154 — the **entire §7.2 hub-bias meter**: quintiles, top-50 over-representation

The assertion values confirm it outright:

| | asserts drug-target macro AUC |
|---|--:|
| DSS `nb3` | **0.6911** |
| repo `nb3` | **0.6886** |

And `models.tsv`: **m3-f12 = 0.6911, m7-f14 (champion) = 0.6886.**

> **The notebooks that actually run in DSS are validating the retired `m3-f12` model** for §6.3 and
> §7.2. The mirrors were migrated to the champion and never pushed back.

This is exactly the failure the assertion notebooks exist to prevent, occurring in the notebooks
themselves. It also explains a puzzle from §22: `.index/assertions.tsv` counts 99 assertions from the
**mirrors**, so the index has been describing notebooks that are not the ones being run.

### 23.3 So: merge, do not pull

`tools/pull_notebooks.py` defaults to a **drift report and refuses to overwrite**; `--pull` is explicit,
and it prints *"the MIRROR is ahead — pulling would DISCARD assertions or figures"* on three of the
five. Pulling now would lose five assertions and eight figures, and would import the m3 contamination
into the repo.

The merge, per notebook:

| take from DSS | take from the mirror |
|---|---|
| markdown-cell structure, all five | `scored_champion` in `nb1` and `nb3` |
| `nb1`'s three figures | the assertion values pinned to the champion (0.6886, not 0.6911) |
| | `nb3`'s extra assertions and figures |
| | `nb4`'s two figures, three assertions, and its `raw_ot_known_drug` read |

Then push the merged versions **back to DSS** so the two sides converge, and re-run
`tools/build_index.py` so the assertion index describes what runs.

⚠ **`nb3b` and `nb6` do not exist in DSS at all.** `nb3b` is the canonical hub-bias artifact and `nb6`
carries acts 5–6 and the only guard on `safety_lift` / `tractability_lift`. Both are repo-only, so
neither has ever been executed against live data. **`nb6` in particular is unverified** — §17's rule
applies: it has not run green, so nothing in zone 90 can be pruned.


---

## 24. `nb6` created, run, and green — the punch line is now guarded

**33 assertions, 33 PASS.** `safety_lift` and `tractability_lift` — read by nothing until now — are
guarded. §17's precondition on pruning zone 90 is satisfied.

Results are written to `nb6_assertion_results` (33 rows: check / documented / live / status), so they
are queryable rather than buried in a log.

### 24.1 How to run a notebook's code from the CLI

There is **no `dku notebook run`**, and `dku notebook create` takes only a name — it cannot set content.
Two routes, and only one is usable:

- **`scenario add-step-python`** runs inline code, but on this build `scenario run-log` fails with
  `DSS API error: 'scenarioRun'`, so the output cannot be retrieved. The step reports SUCCESS whenever
  the script merely finishes.
- **A Python recipe** works: `dku job log` returns the container's stdout, including every `CHK|` line.
  Its constraint is the useful one — **a recipe may only read datasets declared as inputs**, which a
  notebook is not required to do. Declaring nb6's 14 inputs made its dependencies explicit in the flow.

`run_nb6_assertions` is that recipe, in zone 90, writing `nb6_assertion_results`.

### 24.2 Three defects the run found — all mine, none in the flow

**1. `scored_champion` cannot be read whole in a container.** 3,958,921 rows killed the process with
*"terminated by signal 1"* and no traceback — the same failure `nb1` records at 2.19M rows. Fixed by
iterating 250k-row chunks and keeping only `is_target == 1` (73,829 rows). **Chunking rather than
sampling was deliberate:** sampling would move the 0.59 / 0.79 figures this section asserts.

**2. The detection threshold was wrong, and it inverted the finding.** I used `proba_1 >= 0.5`; the
documented rates are measured at the F1-optimised **0.860**, which is what `nb3b` uses.

| | Q1 | Q5 |
|---|--:|--:|
| at 0.5 *(my error)* | 65.5% | 84.8% |
| at 0.860 *(correct)* | **16.8%** | **57.6%** |
| documented | 17.3% | 57.0% |

At 0.5 the same data reads as a *mild* effect. At the real threshold it is the 3.4× detection swing the
demo describes. **A threshold silently defaulted is a finding silently changed.**

**3. §5.4 was written against a schema that does not exist.** `raw_ot_known_drug` is
`targetId, symbol, diseaseId, score` — **no drug column at all**, so the multi-target inflation cannot
be measured from it. My code "worked" and returned 0% / 100%. Rewritten against `drug_protein_edges`
and `drug_disease_edges`, which do carry drug identity.

### 24.3 A number in the document with no traceable source

Computed properly, the ground-truth inflation is:

| | measured | documented |
|---|--:|--:|
| pairs manufactured by the join | **109,630** | — |
| share from multi-target drugs | **87.5%** | 82% |
| surviving a single-target demand | **12.5%** | 8% |

Also measured: 2,261 drugs carry both edge kinds, the worst hits **78 targets**, and the median drug is
approved for 4 diseases.

The shapes agree; the numbers do not. The documented 82% / 8% appear in `TARGET_PRIORITIZER`'s Q4
summary line citing §8.1 and §8.6, but **no notebook computes them and no dataset holds them** — the
difference is most likely a denominator (109,630 manufactured pairs vs the 67,748 that resolve onto the
graph, per `known_drug_truth`).

**`nb6` deliberately does not assert 82% / 8%.** Asserting a number whose derivation cannot be found is
exactly how a stale figure survives an assertion suite. It prints the measured values and says so. Pin
the assertion once the denominator is agreed — and until then, **the deck should quote 87.5%, or the
figure should be recomputed on the graph-resolved subset and quoted from there.**


---

## 25. Zone 90, mapped recipe by recipe — what codifies, what deletes, what must stay

§22.3 counted which *datasets* the notebooks read. That was not enough: a dataset cannot be dropped
without also dropping **its recipe**, and the recipe's logic has to land somewhere. This is that map.

33 datasets in zone 90, traced to their producing recipe and every consumer.

### 25.1 Three of them are serving-upstream and can never be deleted — §14.4 had this wrong

| dataset | feeds | so it belongs in |
|---|---|---|
| `known_drug_truth` | `compute_filter_three_axes` → **`filter_three_axes`**, act 4's funnel | **A4**, not 90 |
| `drug_target_benchmark` | `compute_persona_candidates` → **`persona_enrichment`**, act 2's beeswarm | **A2**, not 90 |
| `novel_discovery_eval` | same | **A2**, not 90 |

I staged all three for deletion in §14.4 on the basis that notebooks read them. They do — *and* they
feed the webapp. **Move them out of 90 before any prune runs**, or the cleanup takes the serving layer
with it.

### 25.2 Dead subtrees — delete, nothing reads them

**The ablation ladder, 7 datasets and 8 recipes.** `scored_m1`/`m2`/`m3` feed only
`compute_model_comparison`, whose output `model_comparison` has **no readers at all**. `scored_m4`,
`m5`, `m6`, `m8` have none either. Delete `model_comparison` first and the whole subtree falls.

> ⚠ **Except `scored_m3`, which the DSS notebooks read** (§23.2). `nb1` and `nb3` in DSS run their §6.3
> and §7.2 sections against it — the retired `m3-f12`. **Migrate those two to `scored_champion` first;**
> the deletion then costs nothing and removes the last way to accidentally validate the wrong model.

**Six more with no reader:** `drug_target_benchmark_staged` (131 loc), `maturity_confound` (114),
`target_reachability` (107), `pool_unreachable_targets`, `validation_auc_by_disease_2` (77),
`family_top_genes_named`.

**The family chain, 6 datasets and 6 recipes, is entirely self-contained:**
`family_validation_scored` → `family_gene_agg` / `family_validation_ranked` → `family_top_genes` /
`family_auc_grouped` → `family_top_genes_named` / `family_auc_by_family`. Only the last is read
outside it, by `nb3`. Codify that one number and all six drop — which is what zone 43's own
description meant by *"the five-recipe chain behind it is over-built."*

### 25.3 Codify into a notebook, then delete — ~910 lines of Python

| recipe | loc | dataset(s) | absorbing notebook |
|---|--:|---|---|
| `compute_pool_reachability` | 202 | `pool_reachability`, `pool_unreachable_targets` | **nb2** |
| `compute_pool_selection_bias` | 81 | `pool_selection_bias` | **nb2** |
| `compute_family_auc` *(+5 upstream)* | visual | `family_auc_by_family` | **nb3** |
| `compute_breast_panel` | 210 | `breast_panel_metrics`, `breast_panel_overlap` | **nb4**, cross-checked by nb6 |
| `compute_tractability_axis` | 136 | `tractability_axis` | **nb4** / **nb6** |
| `compute_tractability_lift` | 84 | `tractability_lift` | **nb6** ✅ already asserted |
| `compute_safety_lift` | 120 | `safety_lift` | **nb6** ✅ already asserted |
| `compute_lung_granularity_check` | 77 | `lung_granularity_check` | **nb6** ✅ already asserted |

`nb6` already **reads and asserts** the last three, so their numbers are guarded (§24) — but it does not
yet **recompute** them, so the recipes are still load-bearing. Guarded is the precondition for deletion;
codified is what makes deletion safe.

**`breast_shortlist`** is a clinician review form — a deliverable to a person, not a pipeline artifact.
Export it to a file, then delete.

### 25.4 Next steps, in dependency order

1. **Migrate the DSS `nb1` and `nb3` off `scored_m3`** onto `scored_champion`, merging with the repo
   mirrors (§23.3). This is the gate on the largest deletion and it fixes a live correctness problem —
   two sections are currently validating the retired model.
2. **Move `known_drug_truth` → A4 and `drug_target_benchmark` / `novel_discovery_eval` → A2** (§25.1),
   so a prune cannot reach them.
3. **Delete the dead subtrees** — the ablation ladder, the six orphans, the family chain once `nb3`
   absorbs `family_auc_by_family`. **~19 datasets and ~15 recipes**, with no code to write beyond that
   one number.
4. **Codify the remaining five recipes** (~700 loc) into nb2, nb3 and nb4, verifying each against the
   dataset it replaces before deleting it — the §20 pattern: build parallel, compare cell by cell, then
   swap.
5. **Then the final zone integration and rebuild**, with `tools/check_freshness.py` run first (§21).

Steps 1–3 are the cheap 80%: they remove roughly half of zone 90 and require almost no new code. Step 4
is the real work.


---

## 26. Step 1 — the DSS notebooks are m3-era throughout, not just in one line

§23.2 found `nb1` and `nb3` reading `scored_m3` and framed it as a two-line fix. **Running them against
`scored_champion` proved that wrong.** Their *documented values* are m3-f12's as well.

### 26.1 What running them on the champion actually showed

`nb3`, with only the dataset name changed — **4 of 7 assertions go STALE**:

| assertion | DSS documents | live on champion | which model is DSS quoting |
|---|--:|--:|---|
| 10.1 macro per-disease AUC | 0.8197 | **0.8230** | **m3-f12** (`models.tsv` assoc_auroc = 0.8197) |
| 7.3 per-family macro AUC | 0.7976 | **0.8009** | m3-era |
| 7.4 orthogonality pearson r | +0.024 | **+0.002** | m3-era |
| 7.4 orthogonality R² | 0.0006 | **0.0000** | m3-era |

`nb1`, same treatment — **3 STALE**:

| assertion | DSS documents | live | note |
|---|--:|--:|---|
| 6.1 dwpc_GPGD single-feature AUC | 0.641 | **0.702** | |
| 6.1 dwpc_GGD single-feature AUC | 0.601 | **0.674** | |
| 6.2 worst null gap pp | −31.6 | **−57.3** | see below |

> **So the fix is not one line per notebook. `nb3` needs the dataset plus four values; `nb1` needs the
> dataset plus three.** Every one of the DSS-documented figures is the retired champion's.

### 26.2 The mirror is ahead on correctness, not just on values

`nb1`'s null-gap assertion is the clearest case. DSS asserts the **global** worst gap; the live global
worst is −57.3, which is `rwr_score` — **a rejected feature**. The repo mirror asserts −31.7 over the
**model features only**, and carries the comment explaining exactly why:

> *"§6.2 quotes −31.7 for the FOUR MODEL features; the global minimum is rwr_score (rejected) at ~−57.
> Assert against the model-feature gap, which is what the document actually claims."*

That is a fix the mirror has and DSS does not. The merge is therefore **not symmetric**:

| take from the repo mirror | take from DSS |
|---|---|
| all code and all documented values | markdown-cell structure |
| the model-feature scoping of §6.2 | the seaborn correlation heatmap |
| `scored_champion` throughout | |

### 26.3 Done

**The heatmap is now in the repo mirror** (`nb1`, §6.1) — guarded by `try/ImportError` so it degrades to
a printed note if `seaborn` is absent from the code env, and using the `Agg` backend so it runs
headless like the project's other figures.

**Two verification recipes remain in zone 90** — `verify_nb1_on_champion` and `verify_nb3_on_champion`,
writing `nb1_verify` / `nb3_verify`. They run the DSS code with the dataset substituted, which is how
§26.1 was measured. Delete them once the DSS notebooks are corrected.

### 26.4 What has to happen in the DSS UI, and why

**`dku` is read-only for notebook content.** `notebook get` returns the `.ipynb`; `notebook create`
takes only a name; there is no set / update / import verb. So the correction cannot be scripted.

Two options, and the second is better:

1. Paste the repo mirrors over the DSS notebooks — correct, but discards the markdown structure.
2. **Edit the seven values in place**, keeping the structure: in `nb1` change the `scored_m3` read plus
   three documented values; in `nb3` change the read plus four. The exact list is §26.1. Then re-run
   `tools/pull_notebooks.py` to confirm the two sides converge.

⚠ **Until this is done, `scored_m3` cannot be deleted** — and it is the last blocker on the
seven-dataset ablation subtree (§25.2). One notebook edit unblocks the largest deletion in the cleanup.

**A recipe-context caveat, if anyone reuses these as recipes:** `nb1`'s DSS version calls Jupyter's
`display()`, which does not exist outside a notebook kernel. The verification copy shims it. That is a
sign the DSS notebook is notebook-native code, which is fine — but it means "run the notebook as a
recipe" needs a shim, not just an input list.


---

## 27. Steps 1–2 status, and the one edit still blocking the cleanup

### 27.1 Step 1 — two of three notebooks migrated and verified

| notebook | state | verified |
|---|---|---|
| `nb1_features_and_config` | ✅ migrated — reads `scored_champion`, values corrected, and it carries the **model-scoped** null-gap fix (−31.7, not the global −57.3) | **6/6 PASS**, 0 failures, run on the live DSS content |
| `nb6_interrogation_and_close` | ✅ populated in DSS, 232 code lines, reads `scored_champion` | **33/33 PASS** (§24) |
| `nb3_validation_and_plots` | ❌ **still reads `scored_m3`** | — |

### 27.2 The six edits `nb3` needs

Four cells. ⚠ **Three other occurrences of `0.0006` in this notebook are `tol=` tolerances, not
documented values — leave those alone.**

| cell | change | which argument |
|--:|---|---|
| 3 | `0.8197` → **`0.8230`** | the *documented value* in `check("10.1 macro per-disease AUC", …)`; its `tol=0.0006` stays |
| 5 | `0.7976` → **`0.8009`** | `check("7.3 per-family macro AUC", …)` |
| 7 | `0.024` → **`0.002`** | `check("7.4 orthogonality pearson r", …)` |
| 7 | `0.0006` → **`0.0000`** | `check("7.4 orthogonality R2", …)` — this one **is** a value |
| 9 | `0.6911` → **`0.6886`** | `check("7.4 drug-target macro AUC", …)`; its `tol=0.0006` stays |
| 11 | `Dataset("scored_m3")` → **`Dataset("scored_champion")`** | the §7.2 hub-bias read |

Then re-run `tools/pull_notebooks.py` to confirm convergence, and
`dku job run --target nb3_verify` to confirm green.

### 27.3 Step 2 — done

The three serving-upstream datasets are out of the deletion staging zone:

| dataset | moved to | because it feeds |
|---|---|---|
| `known_drug_truth` | **A4** | `filter_three_axes` — act 4's funnel |
| `drug_target_benchmark` | **A2** | `persona_candidates` → `persona_enrichment` |
| `novel_discovery_eval` | **A2** | same |

A prune can no longer reach them. Zone 90 is 32 datasets (33 − 3 moved out + 2 verification outputs).

### 27.4 What step 3 can and cannot do right now

**Blocked on `nb3`:** the seven-dataset ablation subtree. `scored_m3` is read by DSS `nb3`; `scored_m1`
and `m2` feed `compute_model_comparison`, which also consumes `m3`. One notebook edit releases all of
it.

**Unblocked, but not done — deletion is irreversible and needs an explicit go:**
`drug_target_benchmark_staged`, `maturity_confound`, `target_reachability`, `pool_unreachable_targets`,
`validation_auc_by_disease_2`, `family_top_genes_named`, and `scored_m4` / `m5` / `m6` / `m8`.
Ten datasets, no readers of any kind.

Also to delete once `nb3` is corrected: the three verification recipes and their outputs
(`verify_nb1_on_champion`, `verify_nb3_on_champion`, `nb1_verify`, `nb3_verify`). They exist only to
prove the migration.


---

## 28. `nb3` merged locally — 9/9 PASS

`notebooks/nb3_validation_and_plots.py` is now the **merged** version, verified green against live data.
It is the file to paste into DSS.

### 28.1 What the merge took from each side

The DSS copy and the mirror were each ahead in different places (§23.1), so neither could simply
overwrite the other. The diff was measured, not assumed:

| | DSS | mirror |
|---|--:|--:|
| assertions | 7 | 9 — the extra two are `header pooled AUC` and `header per-split-key AUC` |
| figures | 2, drawn with **seaborn** (`histplot`, `lineplot`, `scatterplot`, `despine`) | 2, raw matplotlib with `savefig` |
| documented values | **m3-f12 throughout** | champion |

**Base: DSS** — its markdown-cell structure and the seaborn figures are better. Then:

1. **The six corrections** of §27.2 — all applied, verified none of `scored_m3`, `0.8197`, `0.7976` or
   `0.6911` survives anywhere in the file. The five `tol=0.0006` tolerances are untouched.
2. **`disease_split_key` added to the §7.2 read.** The header-metrics block needs it and the DSS copy
   did not request it — a merge that only moved the assertion across would have failed at runtime.
3. **`plt.savefig` before each `plt.close()`.** DSS renders inline and closes, so a headless run left no
   artifact; the project treats figures as artifacts, so both figures now persist to `/tmp`.
4. **The two missing assertions appended**, with the mirror's own note on why they exist — *"the two
   metrics the header quotes and nothing asserted… why the status line once mixed m7's macro with m3's
   pooled."*

182 → 211 lines.

### 28.2 Verified

Run against live data through `verify_nb3_on_champion`:

```
10.1 macro per-disease AUC   0.8230   PASS      7.4 orthogonality pearson r  +0.002  PASS
10.1 validation diseases        670   PASS      7.4 orthogonality R2         0.0000  PASS
7.3  per-family macro AUC    0.8009   PASS      7.4 drug-target macro AUC    0.6886  PASS
7.3  families                   505   PASS      header pooled AUC            0.8932  PASS
                                                header per-split-key AUC     0.8046  PASS
VERIFY|failures=0
```

`HEADER|pooled=0.8932|per_split_key=0.8046|split_keys=441` — the pooled figure is **7.0 points above**
the macro 0.8230, which is the overstatement §12.2 warns about, now measured rather than asserted.

### 28.3 Still to do in the DSS UI

Paste `notebooks/nb3_validation_and_plots.py` over the DSS notebook — or apply §27.2's six edits plus
the `disease_split_key` column and the header block. Until then `scored_m3` cannot be deleted, and with
it the seven-dataset ablation subtree.


---

## 29. Step 1 complete — all seven notebooks converged on the champion

`tools/pull_notebooks.py` now reports every notebook **in sync**: same assertions, same dataset reads.

| notebook | assertions |
|---|--:|
| `nb1_features_and_config` | 7 |
| `nb2_splitting_and_pool` | 15 |
| `nb3_validation_and_plots` | 10 |
| `nb3b_hub_bias_meter` | 8 |
| `nb4_results_three_axes` | 19 |
| `nb5_data_exploration` | 0 *(descriptive)* |
| `nb6_interrogation_and_close` | 28 |

**Nothing anywhere reads `scored_m3`** — verified across all seven DSS notebooks, all seven repo
mirrors, and the recipe graph. Its only remaining consumer is `compute_model_comparison`, which has no
consumers of its own.

### 29.1 The tool reported false red until it was fixed

`pull_notebooks.py` originally compared the flattened `.ipynb` to the mirror **byte for byte**, so it
reported DRIFT on all seven forever — the mirror is a flattened notebook whose markdown cells become
comments, and it is also hand-edited, so the two can never be byte-identical.

It now compares what actually matters — **assertion count and dataset reads** — and distinguishes
`identical` / `in sync (formatting differs)` / `DRIFT`. A check that is always red teaches people to
ignore it, which is worse than not having it.

### 29.2 Ready to delete: 15 datasets, 15 recipes

| group | datasets | recipes |
|---|--:|--:|
| ablation subtree — `scored_m1`–`m6`, `m8`, `model_comparison` | 8 | 8 |
| orphans — `drug_target_benchmark_staged`, `maturity_confound`, `target_reachability`, `validation_auc_by_disease_2`, `family_top_genes_named` | 5 | 5 |
| verification scaffold — `nb1_verify`, `nb3_verify` | 2 | 2 |

⚠ **`pool_unreachable_targets` is excluded.** It shares `compute_pool_reachability` with
`pool_reachability`, which `nb2` reads. Dropping the dataset would leave a recipe writing to nothing;
it should wait for step 4, when `nb2` absorbs that recipe entirely.

That takes zone 90 from 32 datasets to ~17, and leaves step 4 — codifying ~700 lines into nb2, nb3 and
nb4 — as the only substantial work left.


## 30. Step 4, first tranche — the two lift tables codified, and a live breakage found on the way

### 30.1 A defect I introduced in §20.5: `replace-input` does not touch Python code

Repointing the seven consumers of `enriched_gene_safety` / `enriched_gene_druggability` at the `_v2`
datasets used `dku recipe replace-input`. That rewires the recipe's **declared** inputs. For a visual
recipe (`decorate_target_candidates`, a join) that is the whole story. For a **Python** recipe the
code still contains `dataiku.Dataset("enriched_gene_safety")` — the declaration and the code now
disagree, and the recipe cannot read a dataset it no longer declares.

Five recipes were left in that state:

| recipe | code read | declared input |
|---|---|---|
| `compute_safety_lift` | `enriched_gene_safety` | `enriched_gene_safety_v2` |
| `compute_tractability_lift` | `enriched_gene_druggability` | `enriched_gene_druggability_v2` |
| `compute_tractability_axis` | `enriched_gene_druggability` | `enriched_gene_druggability_v2` |
| `compute_pool_reachability` | `enriched_gene_druggability` | `enriched_gene_druggability_v2` |
| `compute_drug_target_benchmark_staged` | `enriched_gene_druggability` | `enriched_gene_druggability_v2` |

None has been run since the swap, so nothing surfaced it. **Rule: after `replace-input` on a code
recipe, patch the code too — the CLI will not, and the flow graph will look correct while the recipe
is unrunnable.** Four of the five are step-4 codify targets and will be deleted; only
`compute_drug_target_benchmark_staged` needs the fix to survive. **All five were patched and pushed**
via `dku recipe set-code`; each now reads the `_v2` dataset it declares.

A second find: `dss_recipes/*.py` is a **stale mirror**. It showed these recipes reading `scored_m3`;
live they read `scored_champion`. Trust `dku recipe get-code`, not the mirror.

### 30.2 `safety_lift` + `tractability_lift` → `nb6` §6.0

204 lines across two recipes collapse to one 83-line block, because the two shared a large prefix —
building the drug-validated `truth` table from `graph_nodes` + `drug_protein_edges` +
`drug_disease_edges`, then restricting `scored_champion` to the diseases that have one. That prefix
is now built once and both tables come from a single parameterised `lift_table()`.

The reads are gone: nb6 no longer opens `tractability_lift` or `safety_lift`. All six punch-line
assertions (membrane receptor 0.78 / 3.16, ion channel 11.89, `lof_intolerant` 2.07 / 1.37, liability
4.62) are **untouched** — which is the point. They were written against the recipe's output, so they
now test the codified arithmetic as a regression suite, with no edit to make them do it.

**The parity that had to be exact.** `lift()` looks values up by string. The two recipes group
differently and it is not cosmetic:

- `compute_safety_lift` casts `.astype("object")` before `fillna` — a float or Categorical key
  renders `"1.0"`. Confirmed against the live table: `lof_intolerant` values are `0.0` / `1.0` / `(null)`.
- `compute_tractability_lift` omits the cast — `ot_ab_tractable` is integer and renders `"0"` / `"1"`.
  Confirmed likewise.

Had `lift_table()` normalised both the same way, every assertion would have looked up a key that no
longer existed and returned `None` — and `lift()` returns `(None, None)` rather than raising, so the
failure would have been a `TypeError` on formatting, not a clear miss. The `as_object` flag
reproduces each recipe exactly.

**Population guard.** `check("6.0 lift base rows", 907246, …)` is new. It is not a documented figure:
it is derived from the retired tables themselves, where `lof_intolerant` (746,309 + 107,600 + 53,337)
and `ot_ab_tractable` (425,469 + 481,777) independently sum to 907,246. If the codified truth-table
build or the chunked read drifts, the lifts move quietly; this fails first. (`safety_flag` sums to
905,651 — 1,595 rows sit in groups under the `n>=2000` floor, dropped from the table, not the base.)
The disease count is **printed, not asserted** — the only source for "112" is a code comment.

### 30.3 Verified — 33/33 PASS, 213s

`run_nb6_assertions` gained `graph_nodes` and `enriched_gene_safety_v2` as declared inputs (the §30.1
trap, avoided this time), took the codified notebook, and ran green in 3m34s. Every assertion PASS,
zero stale.

The six punch-line figures reproduce **to the digit** from code that no longer reads the flow:

| assertion | documented | computed |
|---|---|---|
| membrane receptor `assoc_lift` | 0.78 | 0.78 |
| membrane receptor `drug_lift` | 3.16 | 3.16 |
| ion channel `drug_lift` | 11.89 | 11.89 |
| `lof_intolerant` `assoc_lift` | 2.07 | 2.07 |
| `lof_intolerant` `drug_lift` | 1.37 | 1.37 |
| liability `drug_lift` | 4.62 | 4.62 |

`6.0 lift base rows` hit 907,246 exactly, so the codified truth-table build and chunked read reproduce
the recipe's population precisely rather than landing on the same lifts by coincidence.

`safety_lift` and `tractability_lift` are now **provably redundant** — nothing reads them and their
content is reproduced from upstream. They are cleared for the stepwise delete; `compute_safety_lift`
and `compute_tractability_lift` go with them.

### 30.4 `dss_recipes/` is uniformly m3-era — 12 of the mirrors are stale

The mirror drift found in §30.1 is not local to those five files. Every mirror that reads the scored
output still names `scored_m3`; **all of them read `scored_champion` live**:

`compute_breast_panel`, `compute_drug_target_benchmark`, `compute_drug_target_benchmark_staged`,
`compute_lung_granularity_check`, `compute_novel_discovery_eval`, `compute_pool_reachability`,
`compute_pool_selection_bias`, `compute_safety_lift`, `compute_target_reachability`,
`compute_tractability_axis`, `compute_tractability_lift`, `compute_validation_auc_by_disease_2`.

The step-1 champion migration moved the live recipes and never refreshed the mirror, so `dss_recipes/`
has been describing the retired model since. Anything derived from it by grep — including a reading of
`code.tsv` — answers as of m3. The five touched here are synced; the rest need
`tools/build_recipe_index.py --refresh`.

**Rule: `dss_recipes/` is a snapshot, not a source. Confirm with `dku recipe get-code`.** CLAUDE.md
already says the mirrors can lag DSS; this is how far.

### 30.5 `scored_champion` is CSV, and every notebook pays for it

The job log emits `CSV Emitted 3300000 lines from file, 45 columns`. `scored_champion` is **csv on
S3**, 3,958,921 rows × 45 columns. CSV has no column pruning, so `get_dataframe(columns=[...])` for
three columns still streams all forty-five — which is why nb6 takes minutes, and why the unchunked
read killed the container with `signal 1` in the first place.

Converting it to parquet would let a three-column read touch roughly 7% of the bytes. It is the same
conversion-then-swap done for `gene_crosswalk` in §20, and it is the single highest-leverage change
available to notebook runtime. **Not done here** — a format conversion without a rebuild is exactly
what corrupted `dashboard_candidates` in §17, and it should not ride along with a codification change.

## 31. Step 4 completed — three codified, three kept in the flow on purpose

### 31.1 Verification moved to a Scenario, not more recipes

`validate_notebooks` (step-based, three `build_flowitem` steps over `nb1_verify`, `nb3_verify`,
`nb6_assertion_results`, each `NON_RECURSIVE_FORCED_BUILD`, `proceed_on_failure` so one failure does
not hide the others) is now the single entry point for notebook validation, with run history in DSS.

This also settles the objection in §30: adding a verify *recipe* per notebook would have grown the
flow we are shrinking. For nb2 and nb4 the answer is `add-step-python` — a `custom_python` scenario
step runs assertion code with **no recipe and no dataset** in the flow at all. The three existing
verify recipes stay only until the pruning pass.

### 31.2 Codified — three recipes whose logic is notebook-shaped

| recipe | loc | → | why it moved cleanly |
|---|---|---|---|
| `compute_lung_granularity_check` | 77 | nb6 | self-contained; one family filter and a top-50 per disease |
| `compute_pool_selection_bias` | 55 | nb2 | nb2 already built `gcd_only`, `M` and `keys()` — only the AUC loop had to move |
| ~~`compute_family_auc`~~ | shaker | — | **attempted and reverted** — see 31.5 |

Two deliberate reductions, both recorded in the code: the selection-bias recipe also computed an
"all known_drug" label that nothing asserts or reads — dropped rather than reproduced; and the lung
recipe's own console table is dropped because nb6 builds a different table from the same frame.

### 31.3 NOT codified — three shared or heavy precomputations, and why

Mechanically completing step 4 would have made things worse in three cases:

| recipe | loc | consumed by | why it stays |
|---|---|---|---|
| `compute_tractability_axis` | 92 | nb4 §8.4 **and** nb6 §5.1 | both notebooks run the *same* block over its output; codifying means duplicating a full 3.96M-row scan in two places |
| `compute_breast_panel` | 210 | nb4 **and** nb6 §6.3 | same shared-output shape |
| `compute_pool_reachability` | 145 | nb2 | reads `graph_edges` (2.85M) **and** the 6.75M-row pool, writes two datasets, and carries dead code (`gid` "unused; kept for clarity", `nid_by_id` "placeholder") |

The notebook principle is that a number should be *traceable to code*, not that every aggregate must
be recomputed per reader. A precomputation consumed identically by two notebooks is a legitimate flow
member; duplicating it is how the two copies drift apart. These three keep their recipes, and their
datasets are **excluded from the pruning list**.

### 31.4 A cost this surfaced

`nb6` now reads `scored_champion` three times (positives, lift base, lung family). Against a 45-column
CSV with no column pruning (§30.5) that is three full-width scans of 3.96M rows. It is the direct
reason the validation scenario takes minutes rather than seconds. The parquet conversion in §30.5
would fix all of it at once and is the highest-leverage change left; it should be its own change,
with a rebuild, not a rider on a codification.

### 31.5 `family_auc_by_family` cannot be codified — its entire upstream chain is unbuilt

The shaker looked like the easiest item in step 4: three GREL columns over `family_auc_grouped`,
reproduced in three lines of pandas. It was codified, pushed, and the run failed:

```
Error while connecting to dataset DEMO_TARGET_IDENTIFICATION.family_auc_grouped,
caused by: DataStoreIOException: Root path of the dataset does not exist
```

The chain behind the 0.8009 per-family AUC:

| dataset | state |
|---|---|
| `family_validation_ranked` (from `window_family_rank`) | **never built** |
| `family_auc_grouped` (from `group_family_auc`) | **never built** |
| `family_auc_by_family` (from `compute_family_auc`) | 505 rows, built 2026-08-21 |

`family_auc_by_family` is a terminal artifact whose provenance no longer exists on disk. The
codification was **reverted** — pointing a notebook at a dataset that does not exist is strictly
worse than reading one that does — and nb3 carries a comment saying why.

Consequences, both of which matter for the pruning pass:

- **`family_auc_by_family` must NOT be deleted.** It is the only surviving copy of `7.3 per-family
  macro AUC = 0.8009` over 505 families, and nb3 asserts both.
- Re-deriving it means rebuilding a three-recipe chain that has never run in its current form. That
  is not a pre-demo change: it could move a documented number with no way to tell which value was
  right.

A second lesson, from my own error: `dku recipe add-input` had already been used to declare
`family_auc_grouped`, and **DSS connects to every declared input at job start whether the code reads
it or not**, so the recipe kept failing after the code was reverted. There is no `remove-input`; the
fix is `get-settings`, drop the item from `inputs.main.items`, `set-settings --settings @file.json`.

### 31.6 The verify tables were failure-only, which made green ambiguous

`nb1_verify` and `nb3_verify` wrote one row per **failure**, falling back to a single
`(all) | - | - | PASS` row when nothing failed. So a notebook asserting nine things and a notebook
asserting nothing produced an identical green table — the count that would distinguish them was
never written. (`nb6_assertion_results` already wrote every row, which is why it reads 33 PASS.)

`verify_nb3_on_champion` now records every check and raises `SystemExit` on failure. The scenario's
`proceed_on_failure` makes this necessary rather than optional: without a raise, a step that finishes
after a stale assertion still reports SUCCESS.

### 31.7 Revised pruning list — step 4 moved four datasets OFF it

The pruning pass was scoped before step 4 ran. Step 4 changed it in both directions:

**Cleared for deletion — redundancy proven, not assumed:**

| dataset | recipe | evidence |
|---|---|---|
| `safety_lift` | `compute_safety_lift` | recomputed in nb6 §6.0; six lifts match to the digit, base population 907,246 exact |
| `tractability_lift` | `compute_tractability_lift` | same block, same run |
| `lung_granularity_check` | `compute_lung_granularity_check` | recomputed in nb6; 33/33 PASS after the move |
| `pool_selection_bias` | `compute_pool_selection_bias` | recomputed in nb2; cleared once the scenario's nb2 step passes |

**Moved OFF the list — these must survive:**

| dataset | why |
|---|---|
| `family_auc_by_family` | only surviving copy of 0.8009 / 505 families; upstream chain never built (31.5) |
| `tractability_axis` | consumed identically by nb4 §8.4 and nb6 §5.1 |
| `breast_panel_metrics`, `breast_panel_overlap` | consumed by nb4 and nb6 §6.3 |
| `pool_reachability` | 145-line graph computation over `graph_edges` + the 6.75M pool |

`pool_unreachable_targets` was already excluded — it shares `compute_pool_reachability` with a
dataset nb2 reads. That exclusion now extends to the recipe itself.

**The general rule this earned:** a dataset is safe to delete when a notebook *recomputes* it and the
assertions still pass — not when a grep shows nothing reads it. Two of the four survivors above would
have passed a reference check and taken a documented number with them.

### 31.8 Step 4 verified end to end

`validate_notebooks` run `2026-08-25-15-25-19-734`, 811.8s, all four steps green:

| step | result |
|---|---|
| `nb1_verify` | PASS (failure-only format — 1 row; see below) |
| `nb3_verify` | **9 / 9 PASS**, now itemised |
| `nb6_assertion_results` | **34 / 34 PASS** |
| `assert nb2` (custom_python) | **19 checks, 0 failures** |

All four codifications are confirmed against the recipe outputs they replaced:

| codified | evidence |
|---|---|
| `safety_lift` → nb6 | six lifts to the digit; base population 907,246 exact |
| `tractability_lift` → nb6 | same run |
| `lung_granularity_check` → nb6 | 34/34 still green after the move |
| `pool_selection_bias` → nb2 | `SELBIAS\|computed rows=252\|labels=2`; the four AUCs match — 0.6886 / 0.7471 / 0.6833 / 0.7335 |

**Counting note.** The `rows` metric on `nb6_assertion_results` reads 33 while the table holds 34 —
DSS does not recompute dataset metrics after a build, so the metric lags by one run. Count the rows,
not the metric. (`dku dataset head` also prints a title line for some datasets and not others, which
makes any fixed `tail -n +N` offset unreliable — key off the header row instead.)

**Left open, deliberately:** `nb1_verify` still writes failures only, so its green is the ambiguous
kind described in 31.6. It is six assertions and converting it is the same four-line change made to
nb3 — worth doing, not worth blocking the pruning pass.

## 32. The validation scenario is a test harness, not the validation

Stated by the user on 2026-08-25 and worth recording, because it changes what the scenario is *for*:

> the scenario is just a workaround to test the python scripts from the local notebook. We won't use
> the scenario as part of the notebook validation

The **notebooks** are the due-diligence artifact — a human opens one and reads the computation. The
scenario exists only because `dku` cannot execute a notebook (`dku notebook` has create/get/delete/
clear-outputs/list/sessions/stop and no run; scenarios have no notebook step). Without it, every
codification would reach the user unverified.

That reframing is what justified the conversion. The harness had grown **3 recipes and 3 datasets
inside the flow**, sitting in `90 Notebook — validation evidence` where they read as validation
evidence — precisely the wrong impression, since the evidence is the notebook.

`validate_notebooks` is now four `custom_python` steps and **zero flow items**. A `custom_python` step
reads any dataset without declaring it as an input, writes nothing, and fails the run by raising.

Verified before deleting anything — run `2026-08-25-16-37-34-679`, 845.6s, **68 assertions, 0 stale**:

| step | checks | failures |
|---|---|---|
| nb1 | 6 | 0 |
| nb2 | 19 | 0 |
| nb3 | 9 | 0 |
| nb6 | 34 | 0 |

nb1 now reports its six checks individually; the ambiguous single `(all) PASS` row described in 31.6
is gone as a side effect.

**Cost accepted:** `nb6_assertion_results` was the only queryable record of the 34 assertions. Results
now live in the scenario run log. For a harness rather than a deliverable, that is the right trade.

**Pending deletion** (blocked by the session's permission classifier): recipes
`verify_nb1_on_champion`, `verify_nb3_on_champion`, `run_nb6_assertions`; datasets `nb1_verify`,
`nb3_verify`, `nb6_assertion_results`.

### 32.1 Also in this pass

- `compute_pool_reachability` no longer produces `pool_unreachable_targets` — the `miss_out` build and
  its write are removed, the `miss` "why unreachable" console analysis is untouched, lint clean. The
  dataset is now producer-less and deletable on its own; the shared-recipe caveat is gone.
- `llm_hx` is flagged **Keep**, held for the Part 1 visual-graph webapp in `DEMO_KG_LS`. It is never
  built and unreferenced here, so any reference check inside this project reads it as dead.
- Dataset count corrected: `dku dataset list` returns **125**, all mapped to a zone. An earlier
  reading of 137 was wrong.

## 33. The pruning pass — executed and verified

**20 recipes and 21 datasets deleted.** 125 → 104 datasets. Verified by set membership, not by the
`dku dataset list` count, which is unreliable — it reported 137, 125, 116 and 104 for this project
within one session. Check whether specific names are present; do not trust the total.

Pre-flight before deleting: for every recipe in the set, confirm **all** its outputs are also in the
set. That is what protects a multi-output recipe like `compute_pool_reachability`, whose second output
was removed earlier the same day but which still produces `pool_reachability` for nb2.

Verified after: scenario run `2026-08-25-19-25-00-845` — **68 assertions, 0 failures** (nb1 6, nb2 19,
nb3 9, nb6 34). The notebooks still assert clean against the pruned flow.

### 33.1 The prune made the "nothing reads it" heuristic MORE dangerous

`family_auc_by_family`, `tractability_axis` and `breast_panel_overlap` now have **zero recipe
consumers**. Their real consumers are notebooks, and notebooks do not appear in the recipe graph — the
verify recipes were the only things making them look referenced, and those are gone.

So the next mechanical "delete what nothing reads" pass would flag exactly the datasets this one
decided must survive. `docs/demo/PRUNING_MAP.md` and its KEEP flags are now the only record of why.
**Read the map before pruning again.**

### 33.2 Cascade — six more items now dead, not deleted

Deleting `compute_model_comparison` orphaned `scored_m1`, `scored_m2`, `scored_m3` and their three
scoring recipes. All retired-model debris, all now genuinely unreferenced. Left in place: they were
not in the audited set, and a deletion that was not pre-flighted is how the wrong thing goes.

### 33.3 The frozen reference masks stale mirrors

After the prune, `build_recipe_index.py` flagged only 8 stale mirrors although **15** `dss_recipes/*.py`
files corresponded to deleted recipes. The other 7 were labelled `MIRROR (graph-build project)`.

The cause: `KNOWLEDGE_GRAPH_PRIMEKG` — the frozen reference — is an ancestor of this project and still
holds recipes with the same names (`compute_tractability_lift`, `compute_model_comparison`,
`compute_lung_granularity_check`, …). `mirror_status()` checks the sibling projects by **name**, so a
collision with the frozen reference makes a mirror of a *deleted local* recipe look healthy.

The 8 unambiguous files were removed (git history keeps them). The 7 masked ones were left in place:
whether `dss_recipes/` should carry mirrors of the frozen reference at all is a call about intent, not
a mechanical fix, and the tool cannot distinguish the two cases from the name alone.

| left in place |
|---|
| `compute_gene_druggability.py`, `compute_drug_target_benchmark_staged.py`, `compute_lung_granularity_check.py`, `compute_model_comparison.py`, `compute_target_reachability.py`, `compute_tractability_lift.py`, `compute_validation_auc_by_disease_2.py` |

Indexes rebuilt after the prune: **109 recipes, 98 assertions, 2,092 claims**.

## 34. Zone 90 pruned, and the serving-zone cycles removed

### 34.1 The remaining zone-90 orphans

`scored_m1`, `scored_m2`, `scored_m3`, `family_top_genes` — plus `family_gene_agg`, which the closure
pulled in because deleting `family_top_genes` orphaned it. The whole branch
`group_family_gene → family_gene_agg → topn_family_genes → family_top_genes → family_top_genes_named`
was dead once the last link went in the previous pass. **5 datasets, 5 recipes.** 104 → 99.

Pre-flight confirmed the two survivors that mattered: `family_validation_scored` keeps
`window_family_rank` (its route to `family_auc_by_family`, which nb3 asserts) and
`psplit_validation_set` keeps `score_psplit_validation_m7`, the champion scoring.

Verified: run `2026-08-25-20-18-35-759`, 846.7s, **68 assertions, 0 failures**.

Zone 90 is now 8 datasets — five read by notebooks, three forming the chain behind
`family_auc_by_family`.

### 34.2 A transitive closure would have deleted the serving layer — for the third time

Computing the *transitive* dead set (unread, and every consumer also dead) returned **26 datasets
including all of A1–A4**: `graph_node_type_counts`, `family_panel`, `shap_drivers_long`,
`dashboard_persona_trust`, the lot. Nothing reads them because the webapp UI does not exist.

**Never run an unscoped reachability prune on this project.** Scope to a zone and exclude
notebook-read datasets, as this pass did.

### 34.3 The serving zones were circular; they are not now

Two cycles existed, both through A2:

| cycle | via |
|---|---|
| A3 ↔ A2 | `disease_hierarchy_annotation` (A3→A2), `validation_auc_ci` (A2→A3) |
| A4 ↔ A2 | `dashboard_candidates` (A4→A2), `persona_candidates` (A2→A4) |

**A first attempt failed and was reverted.** Moving all four into a new "A0 shared base" zone did not
work: `dashboard_candidates` is *derived from* A4's `candidates_annotated` and `persona_candidates`
from A2's own outputs. They are downstream products, not shared upstream, so the same two cycles
re-formed around A0. The zone was deleted and the datasets restored.

What worked, after tracing each dataset's actual upstream:

- `disease_hierarchy_annotation` is an annotation built from zones 00/10/20 and consumed by A2 — it
  was simply misfiled in A3. **Moved to zone 20.**
- The ten-dataset chain ending at `dashboard_candidates` sat in A4 while A2 and A3 both read from it.
  It draws only from 00/20/30 — verified, no back-edge — so it **moved to a new zone 40, "Candidate
  ranking (shared by acts)"**, upstream of every act.

Result: **zero circular zone dependencies**, and a clean order:

```
00 → 10/11 → 12 → 20 → 30 → 31 → 40 → A1/A2 → A3/A4 → 90
```

A4 drops from 13 datasets to 3, which is the honest shape: most of what was labelled "Shortlist" was
the shared ranking base every act reads.

**The check that separated the right move from the wrong one:** before relocating a chain, ask
whether it consumes anything from the zones it feeds. The first attempt skipped that; the second
ran it.

## 35. Seven saved models dropped — the champion is the only one left in the flow

`m1-f7`, `m2-f10`, `m3-f12`, `m4-f13`, `m5-f13`, `m6-f13-new-pc`, `m8-f14-pm` deleted with their seven
`train_*` recipes. **14 items.** Only `m7-f14` (`hJLGoYn4`) remains, still wired to
`score_persona_candidates`, `score_psplit_validation_m7` and `train_m7-f14`.

They were droppable because the scoring recipes that consumed them went in the earlier passes — each
retired model's only remaining reference was its own training recipe. Cascade checked: deleting the
seven leaves `psplit_train_set` and `psplit_test_set` with `compute_split_audit_2`, so nothing
upstream orphans.

### 35.1 Recoverability was verified, not assumed

The stated reason for dropping them was that they are recoverable from the VisualML object. That is
checkable, and deletion is irreversible, so it was checked:

- Each saved model records `lastExportedFrom`, e.g. m3-f12 →
  `A-DEMO_TARGET_IDENTIFICATION-I2csfIX2-krJwswcb-s3-pp2-m1`.
- Analysis `I2csfIX2` (on `psplit_train_set`) and ML task `krJwswcb` **still exist**.
- The task retains trained models for sessions s1–s12, all `DONE` — one per saved model, no gaps.
- After the deletions the lab still lists **17 trained models**: removing a saved model does not touch
  the analysis it came from.

The mapping is written to `docs/demo/model_recovery.json` so a redeploy does not require guessing
which session produced which model:

| model | id | lab session |
|---|---|---|
| m1-f7 | `Lx5Mz2hY` | s1 |
| m2-f10 | `6hEivCx0` | s2 |
| m3-f12 | `cGPhBOGC` | s3 |
| m4-f13 | `79JOklWN` | s8 |
| m5-f13 | `r2oXoTEw` | s9 |
| m6-f13-new-pc | `DWtdaTje` | s10 |
| m7-f14 | `hJLGoYn4` | s11 |
| m8-f14-pm | `3RZ9a9kN` | s12 |

Redeploy with `dku ml deploy I2csfIX2 krJwswcb <lab_id>`.

### 35.2 The index would have dropped the ablation ladder — corrected

The claim above was first written as "the numbers remain in `.index/models.tsv`". That was **wrong**:
`build_recipe_index.py` built the model rows by iterating **live** saved models, so the next
`--refresh` would have reduced `models.tsv` to a single row and taken the ablation ladder with it —
deleting exactly the evidence the deletion was justified by.

The metrics themselves were never at risk; they are hand-recorded in `tools/model_registry.json`, not
derived from DSS. What was at risk is their presence in the queryable index, which is where the repo
says to look.

Two changes fix it:

- the registry entries now carry `name`, `lab_session` and `lab_id`, so a retired model can be named
  and recovered without consulting a separate file;
- the row loop iterates **live models UNION registry entries**, and a new `in_flow` column records
  which is which — `yes` for the champion, `no (lab s3)` for a retired model and where to get it back.

`models.tsv` still lists all eight after the refresh, with `m7-f14` the only `in_flow: yes`.
