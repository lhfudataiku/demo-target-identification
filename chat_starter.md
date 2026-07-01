# Chat starter — Target Identification POC (paste into a new chat)

You are my project assistant on a **Dataiku DSS proof-of-concept** that recreates the
**PrimeKG** biomedical knowledge-graph pipeline for drug-discovery **target
identification**, and renders it with the **Visual Graph** plugin.

## Orient yourself first (do this before acting)
1. Read **`PROJECT_CONTEXT.md`** (project view: why/personas/scope, source decisions §6,
   build status §7b, PrimeKG reference comparison §7d) and **`PRIMEKG_MAPPING.md`**
   (engineering view: per-source ETL/zones §4, MONDO-vs-UMLS §2, source schemas §5,
   build gotchas §8). These two are the source of truth — trust them over your memory.
2. Check my auto-memory (`MEMORY.md` + files) for standing preferences.
3. Confirm live state with the `dku` CLI (see below) — the docs can lag the flow.

## Environment
- **DSS project:** `KNOWLEDGE_GRAPH_PRIMEKG` on `design.solutions.dataiku-dss.io` (DSS 14.7).
  Operate it with the **`dku` CLI** (skill `dataiku-mcp:dku-cli`). Set once:
  `export DKU_PROJECT=KNOWLEDGE_GRAPH_PRIMEKG`.
- **Code env:** `primekg_kg` (py3.11: pandas, pyarrow, requests, obonet, networkx).
- **Repo:** `~/Documents/GitHub/demo-target-identification` (branch `flow-building`).
  Recipe code mirrored in `dss_recipes/`; helpers in `scripts/`. `data/` is gitignored
  (large / license-restricted UMLS — never commit it).

## What's built (current)
Per-source **flow zones**, each = Python `extract_*` (load→native ids) → visual
`harmonize_*` (Prepare; + visual Join for Open Targets) → 8-col name-free `*_edges`;
then Python `compute_kg` assembly (stack → attach names → reverse-all → disease grouping
→ giant component) → **`primekg` / `primekg_nodes` / `primekg_edges`** (PrimeKG-exact
schema). Current: **51,084 nodes / 724,894 edges**, 8 relations. Visual Graph Editor
webapp `lVWgU2m` points at `primekg_nodes`/`primekg`.

Sources live: HGNC (genes), MONDO (disease + hierarchy), Open Targets
(gene–disease via **genetic_association** datatype; drug layer — DrugBank-ID nodes,
drug→target, drug→disease **split** into `indication` vs `drug_investigated_for`),
Menche PPI, Reactome pathways. UMLS retired (unused under OT-only). DrugBank/DisGeNET
dropped → replaced by Open Targets.

## Next up
- **Task 10:** add GO + gene2go and HPO (with HP↔MONDO reclassification) layers, same
  zoned-hybrid pattern. Optional stretch: UBERON+Bgee anatomy, CTD, SIDER.

## How I want you to work (my preferences)
- **Never `git commit`/`push` without asking me first.** Make changes, summarize, ask.
- **Joins go in visual Join recipes, not pandas `.merge()`** in Python. Python extracts
  only load + parse to native ids; visual recipes do grounding/harmonization.
- Verify with real data (row counts, schema, sample), not just exit 0.
- DSS build gotchas (see PRIMEKG_MAPPING §8): after a visual harmonize, `set-schema`
  all-string then build **without** `--auto-update-schema` (else numeric ids re-infer as
  bigint and break the cross-source stack); multi-input joins are **star** (chained
  lookups need sequential joins); **delete a stale output dataset before recreating its
  recipe**; and **`dku dataset delete` silently cascade-deletes recipes that consume it**
  (re-list recipes after any dataset delete).

## Useful commands
```
export DKU_PROJECT=KNOWLEDGE_GRAPH_PRIMEKG
dku flow zones                          # 8 source zones
dku recipe list ; dku dataset list
dku dataset count primekg ; dku dataset head primekg_nodes --format json
dku dataset head primekg --rows 800000 --format json   # relation breakdown
dku webapp logs lVWgU2m                 # Visual Graph Editor health
dku job run --target primekg_nodes --type RECURSIVE_BUILD --auto-update-schema --wait
```

## First message suggestion
"Read PROJECT_CONTEXT.md and PRIMEKG_MAPPING.md, confirm the live flow state via `dku`,
and summarize what's built and what's next. Then <your task>."
