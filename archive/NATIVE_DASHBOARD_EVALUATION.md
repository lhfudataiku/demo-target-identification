# Native DSS dashboard evaluation — archived 2026-08-28

> **Lifecycle:** Historical · **Audience:** maintainers investigating why the native approach was
> retired · **Authority:** the measured native-dashboard evaluation at the time of retirement ·
> **Update when:** never, except to repair a successor pointer · **Generated dependencies:** none ·
> **Excludes:** the current webapp contract and current implementation guidance. Do not load by default.

This is the historical evaluation removed from `docs/demo/WEBAPP_DESIGN.md` during Phase 2. It records
why the retired native dashboard did not meet the app contract. For the current implementation
contract, read `docs/demo/WEBAPP_DESIGN.md`; for the build journal, read `DASHBOARD_BUILD_LOG.md`.

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
