# Webapp revision — workplan

> **Lifecycle:** Active plan · **Audience:** webapp maintainers and demo reviewers · **Authority:**
> the scope, sequence and acceptance checks for the shortlist-page revision drawn from the
> 2026-11-09 review: a shorter page top, cleaner filters, the calibrated score in the table, one
> assistant, and a recorded review per candidate · **Update when:** a decision in §3 is taken, a
> step is accepted or re-scoped · **Generated dependencies:** none · **Excludes:** the webapp's
> architecture and data contracts, in [`WEBAPP_DESIGN.md`](../demo/WEBAPP_DESIGN.md) and
> [`WEBAPP_DATASET_MAP.md`](WEBAPP_DATASET_MAP.md); the graph revision, in
> [`GRAPH_REVISION_WORKPLAN.md`](../../archive/GRAPH_REVISION_WORKPLAN.md) (archived 2026-11-10).

**Status: IN PROGRESS — D1–D4 decided 2026-11-09; W1 and W3 done 2026-11-09 (`check: ok`, checked in the browser against live data) and deployed to `OlmPX9a` 2026-11-10 from commit `cdf6810`, awaiting the user's review; next is W2.** Every DSS change
and every `make deploy` below needs explicit approval at the step where it happens.

This plan did not wait on the graph revision, which finished 2026-11-10: `DEMO_TARGET_IDENTIFICATION`
now holds the R5 graph and a champion retrained on it, and the served data was rebuilt with it. Step W4
plans for future renumbering (see D3), as `DEC-MEAS-006` requires.

## 1. Feedback and what changes

| # | Feedback | Finding in the code | Change |
|---|---|---|---|
| 1 | An X (Twitter) logo appears in the app | The glossary drawer's close button imports `X` from `@dataiku/vue-icons` ([ActGlossaryDrawer.vue](../../webapp/frontend/src/components/act/ActGlossaryDrawer.vue)). In the DSS icon set that is the X logo; the close glyph is `Dismiss`. No other file uses `X`. | Use `Dismiss`. |
| 2 | The page top is too wordy and reads as hard-coded; the links to the trust page do not belong; link 3 lands in the wrong place | [ShortlistView.vue](../../webapp/frontend/src/views/ShortlistView.vue) says the same thing three times: the hero paragraph, the table's description ("Nothing is pre-filtered" twice) and a footer listing what the page does not show. | Page title plus one short line; remove the eyebrow, hero paragraph, "How do we know?" links and footer; the table description becomes a count. The link-3 landing is a bug in the trust page's scroll, which its own section links share, so it is fixed there (W5). |
| 3 | "Any tractability" and "Either" look the same | "Any" keeps every gene, including those not tractable at all; "Either" keeps genes tractable by a small molecule or an antibody, which is exactly what the **Tractable** checkbox above already does. | Drop "Either"; keep Any / Small molecule / Antibody. |
| 4 | Tractability and target class should sit in the order of their columns | The filters read Tractability, Class; the columns read Class, Tractability. | Swap the two filters. |
| 5 | Show the score next to the rank | The table already receives `score`, which is the calibrated champion's `proba_1` (`top_candidates` → `candidates_annotated` → `dashboard_candidates`, traced with `dku dataset lineage` on 2026-11-09). Three texts still call it uncalibrated. | A score column, worded as R7b step 4 of the graph workplan specifies (W2). |
| 6 | "Ask about" and "Explore in Agent Hub": the same agent? | No. **Ask about** is the in-app assistant: it knows the selected pair, uses the graph, trials and papers tools, and checks every citation ([assistant.py](../../webapp/backend/services/assistant.py)). **Agent Hub** opens DSS's own chat on its home page; it cannot be handed the pair and checks nothing. | Keep **Ask about**; the Agent Hub button per D1. |
| 7 | Let the user validate a candidate with a comment, so the investigation persists and is handed to the next stage | Nothing on the page writes anything today, except the trials/papers cache. | A **Record review** action, stored in DSS and shown back on the page (W4). |
| 8 | Drop the two source lines at the bottom of the gene card (2026-11-09, screenshot) | [CandidateHeader.vue](../../webapp/frontend/src/components/shortlist/CandidateHeader.vue) ends with the HGNC provenance line (file, match key, record date) and a "top N% of the pool · graph node_index" line. | Remove both. The rank and score stay in the card's top line. |

## 2. Guardrails kept

- The model's `prediction` column (the thresholded class) is still never fetched or shown.
- Drug and liability badges still render and are still never filters.
- Every count still carries its rank cut-off.
- No copy recommends what to pursue. A recorded review is the scientist's judgement, labelled as
  such; the app does not propose a verdict.
- The calibrated score is never called the probability of being a target (§6.2 of the graph
  workplan explains why).

## 3. Decisions

| ID | Question | Recommendation | Status |
|---|---|---|---|
| D1 | The Agent Hub button | Remove it from the candidate card. It duplicates "Ask about" with less context and no citation check. | **decided 2026-11-09: remove** |
| D2 | Review verdicts, and whether the comment is required | Three verdicts, *Advance*, *Needs more evidence*, *Reject*, and a required comment: a verdict without a reason does not hand anything off. | **decided 2026-11-09: as recommended** |
| D3 | Where reviews are stored, and how they survive a graph rebuild | One JSON file per review in a new managed folder in `DEMO_TARGET_IDENTIFICATION`, the same pattern as `act4_evidence_cache`, with a "files in folder" dataset on top so the log shows in the Flow and the next stage reads it without code. Each review stores the gene symbol, HGNC id, disease name and model id alongside `gene_index` / `disease_index`, because R5 renumbered 76,786 node indexes and R6 will bring that renumbering into Part 2. A review is matched back to the list by symbol and disease name. | **decided 2026-11-09: as recommended** |
| D4 | How the score is shown | Per R7b step 4: "chance of being a known association" as a percentage, with the disease's base rate in the tooltip, and a note that negatives are unlabeled genes, so for a novel candidate the value is a floor. Rank stays the primary column. | **decided 2026-11-09: as recommended** |

## 4. Steps

### W1 — quick fixes *(frontend only)*
1. Glossary close icon: `X` → `Dismiss`.
2. Tractability filter: remove the "Either" option and its tooltip sentence.
3. Swap the Class and Tractability filters.
4. Page top: keep the page title, add one line ("Pick a disease, narrow the list, select a gene to
   review its evidence."); remove the eyebrow, hero paragraph, "How do we know?" links and footer.
   `TRUST_LINKS` goes if nothing else uses it.
5. Table description: replace the two sentences with a count (*"200 of 12,272 candidates ·
   rank ≤ 200"*).
6. Gene card: remove the HGNC provenance line and the percentile / `node_index` line.

**Accept when:** `npm run check` prints `check: ok`; in the browser the glossary closes with the new
icon, the filters sit above their columns, and the page shows the table without scrolling past
prose.

### W2 — the calibrated score *(frontend, one backend field)*
1. Before writing any copy, re-derive what calibration guarantees from the notebook assertion that
   carries it, not from §6.2's prose: the CLAUDE.md truth rule. Today's figures are ECE 0.0033 on
   validation, and slightly cautious at the head (top 20 per disease: predicted 25.8%, observed
   30.5%).
2. Backend: add the disease's base rate (recorded associations ÷ pool size) to `/api/candidates`,
   computed from the cached frame.
3. Table: a **Score** column right of **Rank**, shown as a percentage with one decimal below 10%.
   Tooltip: what it is, the disease's base rate, and that it is a floor for novel genes.
4. Gene card: add the score to the top line (*"rank 46 of 12,272 · N% chance of a known
   association"*).
5. Correct the texts that still say "uncalibrated": the Rank tooltip, the "How genes are ranked"
   section, the glossary entry `uncalibrated` (reworded or replaced by a `calibrated-score` entry).
6. Update `WEBAPP_DESIGN.md` where it describes the shortlist table and its guardrails, and
   `WEBAPP_DATASET_MAP.md` §2 for the new base-rate field.

**Accept when:** for one disease the displayed values match `dashboard_candidates.score` for the
same rows; no text on the page or glossary calls the score uncalibrated; `npm run check` clean.

### W3 — one assistant *(frontend)*
1. Remove the Agent Hub button (D1), `agentHubUrl()` and its two `VITE_AGENT_HUB_*` values from
   `app.env` and `config.ts` when nothing else reads them.
2. Update `WEBAPP_DESIGN.md` where it describes Phase 7b.

**Accept when:** the candidate card shows one assistant action; `npm run check` clean.

### W4 — recorded reviews *(DSS + backend + frontend)*
1. **DSS (approval required):** create the managed folder `shortlist_reviews` on
   `dataiku-managed-storage` in zone S1, and a "files in folder" dataset `shortlist_reviews_log`
   reading it (JSON lines).
2. Backend: `POST /api/reviews` writes one file per review: verdict, comment, gene symbol, HGNC id,
   `gene_index`, disease name, `disease_index`, rank, score, champion model id, reviewer (the DSS
   login from the browser headers) and a UTC timestamp. `GET /api/reviews?disease=` returns that
   disease's reviews. Reviews are append-only: a new review supersedes the earlier one for the
   same pair on display, but both are kept.
3. Frontend: a **Record review** button on the candidate card opens a dialog (verdict, comment);
   the card lists earlier reviews of the pair; the table shows a *Reviewed* badge on reviewed rows,
   which is a badge, not a filter, like the other badges.
4. Update `WEBAPP_DATASET_MAP.md` §2 (a route that writes) and `WEBAPP_DESIGN.md`.

**Accept when:** a review recorded in the browser appears as a file in the folder, a row in
`shortlist_reviews_log`, and on the card after a page reload; the reviewer field holds the real DSS
login; `npm run check` clean.

### W5 — trust page *(frontend)*
1. Reproduce the link-3 landing fault in the browser. The likely cause: the page scrolls once the
   three payloads arrive, but the family panel loads after that (its own request) and charts
   resize, so the offset lands short; or the last section cannot reach the top because the page
   ends below it. Fix by revealing again once the panel has loaded, or by bottom padding.
2. Readable relation labels on the graph section, if the R2 `display_relation` is served to Part 2
   by then (it reaches Part 2 only with R6).

**Accept when:** each of the three section links lands on its section's heading.

### W6 — deploy and close *(user runs the deploy)*
1. Show the change summary; commit only on approval.
2. The user runs `make deploy`; then a read-only check of the live webapp.
3. Check whether D2–D3 meet the decision register's admission rule; move this plan to `archive/`.

## 5. Risks

| Risk | Mitigation |
|---|---|
| A percentage is read as "chance this is a good target" | The column name and tooltip say *known association*; the base rate sits beside it; §2 guardrail. |
| Reviews keyed only by node index point at the wrong gene after R6 | D3: store symbol, HGNC id and disease name; match by them. |
| Two people review at once and overwrite each other | One file per review, never an update in place. |
| A webapp backend restart loses an in-flight write | The POST returns only after the file is written; the dialog shows the error otherwise. |
