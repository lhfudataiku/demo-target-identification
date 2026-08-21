# demo-target-identification

Dataiku DSS POC recreating PrimeKG as a knowledge graph for drug-discovery target identification,
plus an **Explainable Target Prioritizer** (Visual ML + SHAP) that ranks candidate genes per disease.
DSS instance: `design.solutions.dataiku-dss.io`, project `DEMO_TARGET_IDENTIFICATION`.

## Start here — do not read the large docs to answer a question

The markdown is well over 140k tokens and growing (`TARGET_PRIORITIZER.md` alone is ~38k).
**Invoke the `target-id` skill first** — it holds the query recipes and the accumulated traps in
~1.5k tokens.

Most factual questions are one grep over `.index/`:

| | |
|---|---|
| `.index/models.tsv` | m1–m8: role, metrics, verdict, consumer recipes, `DECISIONS.md` refs |
| `.index/decisions.tsv` | jump table over `DECISIONS.md` — the densest file here |
| `.index/recipes.tsv` | 97 recipes; which 10 carry a seed gate; Class 1 / Class 2 |
| `.index/features.tsv` | feature → producing recipe → gate → class → in-champion |
| `.index/claims.tsv` | every documented number, and whether a notebook guards it |

`./tools/check_indexes.sh` verifies them (good as a pre-commit hook). Rebuild with
`tools/build_index.py` and `tools/build_recipe_index.py` after editing docs or recipes; add
`--refresh` only when a recipe changed in the DSS UI (~3 min).

## Rules

- **Never `git commit` or `push` without asking.** Make the change, summarise, then ask.
- **`compute_kg` is never touched or recomputed** unless explicitly asked.
- **`DECISIONS.md` is append-only.** Corrections are new entries, never edits to old ones.
- **New datasets use the S3 connection.**
- **Joins go in visual Join recipes**, not pandas `.merge()`.
- **`data/` is gitignored** — large and licence-restricted (UMLS). Never commit it.
- Build many datasets in **one job with repeated `--target`** and `RECURSIVE_BUILD`. To rebuild a
  zone, build from its *last* dataset with update-output-schemas and stop-at-zone-boundary so
  intermediates stay virtual.
- Folder error *"Python process is running remotely, direct access to folder is not possible"* →
  switch that recipe to the **DSS engine**. Do not rewrite it, and do not try to sync the folder.

## Layout

- `TARGET_PRIORITIZER.md` — methodology, the reference document. Read one section, never the file.
- `DEMO_NARRATIVE.md` — the demo, as a six-question objection ladder. Client-facing.
- `DECISIONS.md` — append-only log, including refuted hypotheses and corrections.
- `docs/` — feature audit, Phase 3 pre-registration, clinician briefing, frozen appendix snapshots.
- `notebooks/` — assertion notebooks. **They are the source of truth for every documented number**;
  a doc figure with no assertion is an orphan and will drift.
- `dss_recipes/` — mirrored recipe source, including `cypher/` (mirrored 2026-08-21; those gates were
  previously un-versioned).
- `tools/` — index generators plus the hand-recorded `recipe_classes.json` / `model_registry.json`.

## Working style that this project has earned

Report **ties before means** — m3–m6 are near-identical rankers, and every aggregate difference here
has traced back to 9–15 high-leverage diseases. Prefer a stratified paired test to a macro average.
When a headline number is about to go in front of someone, re-derive it rather than trusting the doc.
