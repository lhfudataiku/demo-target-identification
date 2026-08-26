# demo-target-identification

A two-part Dataiku DSS proof-of-concept for drug-discovery **target identification**.

- **Part 1 — the graph.** A PrimeKG-like biomedical knowledge graph built from source, rendered with the Visual Graph plugin. → `docs/graph/GRAPH_BUILDING.md`
- **Part 2 — the prioritizer.** An explainable model ranking candidate target genes per disease, with SHAP attributions and on-graph evidence paths. → `docs/prioritizer/TARGET_PRIORITIZER.md`

`docs/README.md` maps the whole document set; `docs/overview/PROJECT_CONTEXT.md` explains how the two parts fit together, including the shared-object contract.

## Three DSS projects

All on `design.solutions.dataiku-dss.io` (DSS 14.7), code env `primekg_kg` (py3.11). Set `export DKU_PROJECT=…` per project.

| project | role |
|---|---|
| `DEMO_KG_LS` | Part 1 — sources, graph build, graph webapp |
| `DEMO_TARGET_IDENTIFICATION` | Part 2 — features, modelling, validation, serving |
| `KNOWLEDGE_GRAPH_PRIMEKG` | **frozen reference.** Do not modify or rebuild |

Part 2 reads the graph through **13 shared objects** in its `00 Imported from DEMO_KG_LS (synced)` zone — 12 datasets as synced copies, the Kuzu folder read directly.

## Status

**Part 1 complete.** 113,391 nodes / 2,851,510 edges / 18 relations, accepted against the frozen reference. `node_index` is deterministic (a visual Window recipe over an explicit sort) and **1-based here, 0-based in the reference**.

**Part 2 built and validated.** Champion `m7-f14` (`hJLGoYn4`), macro per-disease AUC 0.8230 over 670 diseases. Query `.index/models.tsv` rather than trusting this line.

## Where the work is — two independent tracks

**Track A — the dashboard. The next build, and the demo depends on it.**
`docs/demo/DEMO_NARRATIVE.md` governs its form: **derive the dashboard from that document, not the reverse.** A pruning plan derived from a hypothetical dashboard once cut 46 of 62 validation items, including the answer to the most common objection.

Already in place: a webapp skeleton in `webapp/` (`backend.py`, `app.js`, `body.html`, `style.css`, ~1,100 lines) and the `60 Dashboard (serving)` flow zone with `dashboard_candidates`, `dashboard_persona_trust`, `drug_evidence_pairs` and `target_candidates_2` (129,253 ranked rows over 13 personas). What is missing is the UI itself.

**Track B — Phase 3. Preparation complete; the branch project is not built.**
Widening the pool-route seed gate 20 → 5 would admit 931 diseases the model cannot see today. `docs/prioritizer/PHASE3_PREREGISTRATION.md` holds the intervention, five pre-flight gates, seven falsifiable predictions and the committed adopt/reject rule; sizing is in `docs/prioritizer/FEATURE_AUDIT.md` §5.

Measured verdict: **+80% more diseases for ~+20% more pool rows** — a coverage win, not a quality win. Admitted diseases carry ~4.5 usable positives each and are 6.3× more dilute than current ones, so the honest claim if it succeeds is *"we cover 2,088 diseases instead of 1,157"*, never *"the model got better"*. Two things to know before touching it: the gate must move in a **duplicated project**, because it rewrites the candidate population; and **one of the ten gated recipes must be held at 20** (`compute_dwpc_go_metapaths` is Class 2 — it recomputes an aggregate over the eligible set). `.index/recipes.tsv` has the per-recipe class.

## Start here — do not read the large docs to answer a question

The markdown is well over 140k tokens (`TARGET_PRIORITIZER.md` alone is ~38k). **Use the `target-id` skill first** — it holds the query recipes and the accumulated traps in ~1.5k tokens.

Most factual questions are one grep over `.index/`:

| | |
|---|---|
| `models.tsv` | m1–m8: role, metrics, verdict, consumer recipes, `DECISIONS.md` refs |
| `decisions.tsv` | jump table over `DECISIONS.md` — the densest file here |
| `recipes.tsv` | 97 recipes; which 10 carry a seed gate; Class 1 / Class 2 |
| `features.tsv` | feature → producing recipe → gate → class → in-champion |
| `claims.tsv` | every documented number, and whether a notebook guards it |
| `code.tsv` | every tracked script: live, mirror, or orphaned |

`./tools/check_indexes.sh` and `tools/check_links.py` verify them — both good as pre-commit hooks. Rebuild with `tools/build_index.py` and `tools/build_recipe_index.py`; add `--refresh` only when a recipe changed in the DSS UI (~3 min).

## Rules

- **Never `git commit` or `push` without asking.** Make the change, summarise, then ask.
- **NEVER use a recursive build type in `KNOWLEDGE_GRAPH_PRIMEKG`.** It walks up into the graph zone and renumbers every node. This hazard is *why* the projects were split.
- **`compute_kg` / the graph is never recomputed** unless explicitly asked.
- **`DECISIONS.md` is append-only.** Corrections are new entries, never edits to old ones.
- **New datasets use the S3 connection** (`dataiku-managed-storage`, parquet).
- **Joins go in visual Join recipes**, not pandas `.merge()`. Python extracts only load and parse.
- **`data/` is gitignored** — large and licence-restricted (UMLS). Never commit it.
- Build many datasets in **one job with repeated `--target`** and `RECURSIVE_BUILD`. To rebuild a zone, build from its *last* dataset with update-output-schemas and stop-at-zone-boundary.
- Folder error *"Python process is running remotely, direct access to folder is not possible"* → switch that recipe to the **DSS engine**. Do not rewrite it, and do not sync the folder.
- **The docs can lag the flow, and `dss_recipes/` can lag DSS.** Confirm live state with `dku`.

## Two measurement rules that reverse conclusions

- **Report macro per-disease AUC, never pooled** — pooled overstates by ~7 points.
- **A benchmark a lookup table wins is measuring the lookup.** Drug-target AUC is dominated by gene popularity: a no-graph lookup scores 0.9354, beating a drug-trained model. Report it as a warning flag; never optimise against it.

More of these — druggability inverted under the association label, safety proxies pointing *with* efficacy, the three-clause candidate filter — are in `docs/prioritizer/TARGET_PRIORITIZER.md` §10 and in the `target-id` skill. Platform behaviours are in `docs/platform/DSS_CHEATSHEET.md` §1.

## Working style this project has earned

Report **ties before means** — m3–m6 are near-identical rankers, and every aggregate difference here has traced back to 9–15 high-leverage diseases. Prefer a stratified paired test to a macro average. `notebooks/` is the source of truth for every documented number: a figure with no assertion is an orphan and will drift. When a headline number is about to go in front of someone, re-derive it.
