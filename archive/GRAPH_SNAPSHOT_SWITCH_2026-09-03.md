# Kuzu snapshot switch — verification record, 2026-09-03

> **Lifecycle:** Evidence · **Audience:** flow maintainers and anyone asking whether the published
> feature numbers survived the graph-snapshot change · **Authority:** the measured equivalence of
> `enriched_index_freezed-6bRVGs` and `published_kg_ls-Mp25kL` as feature inputs · **Update when:**
> never — this is a dated record of one verification · **Generated dependencies:**
> [`graph-snapshot-switch-2026-09-03/`](graph-snapshot-switch-2026-09-03/) · **Excludes:** the graph
> build method (GRAPH_BUILDING §6) and the shared-object contract (PROJECT_CONTEXT §4.3).

## What changed

The 10 Cypher feature recipes in zone 10 read the Kuzu graph folder. Until this date they read
`DEMO_KG_LS.enriched_index_freezed-6bRVGs` **directly across the project boundary** — the one
documented exception to the rule that every foreign reference passes through exactly one Sync recipe.

They now read the local managed folder **`graph` (`ytvuniN8`)**, which `compute_ytvuniN8` merges from
`DEMO_KG_LS.published_kg_ls-Mp25kL`. The exception is gone: all 13 foreign references now pass through
exactly one Sync or Merge recipe, and nothing in `DEMO_TARGET_IDENTIFICATION` reads a Kuzu folder
across the boundary.

The new snapshot is not the old one. It was rebuilt on 2026-09-03 and carries 8 saved Cypher queries
in place of the previous 2, aligned to the webapp narrative (3 Act 1 starters, 5 Act 4 presets).

## Why the numbers did not have to move

Verification ran in two stages, cheapest first, so a negative result would have cost almost nothing.

### Stage 1 — the build specification (no graph executed)

Both Kuzu builds read the same `graph_nodes` and `graph_edges`. Comparing `configuration.json`
structurally, SHA-256 over canonical JSON:

| block | match |
|---|---|
| `nodes` (8 groups) | identical |
| `nodes_view` | identical |
| `edges` (18 groups) | identical |
| `edges_view` | identical |

All 18 relation filters are therefore provably unchanged, which rules out the silent edge-dropping
failure recorded in GRAPH_BUILDING §6 — *a missing relation filter drops that relation without an
error*. Only `cypher_queries` (2 → 8), `comment`, `id` and `epoch_ms` differ. The folders are not
byte-equal — `db.kz` 87.6 MB against 88.7 MB — which is Kuzu storage overhead from a fresh load, not
graph payload. Fingerprints: [`graph-config-fingerprints.json`](graph-snapshot-switch-2026-09-03/graph-config-fingerprints.json).

### Stage 2 — the feature outputs (all 10 rebuilt)

Each dataset carries two order-independent fingerprints, computed by
[`signature.py`](graph-snapshot-switch-2026-09-03/signature.py) run as a scenario step, so no flow
object was created:

- **`row_xor`** — XOR of per-row hashes. Exact, but bit-strict: float accumulation order flips it.
- **`row_xor_round6`** — the same over values rounded to 6 dp. Distinguishes float noise from content.
- **`agg`** — count/min/max/sum per numeric column, 34 columns in total.

**Result over 18,510,084 rows: row counts unchanged, and every aggregate identical.**

| dataset | rows | verdict |
|---|--:|---|
| `enriched_degree_controls_1` | 20,861 | bit-identical |
| `enriched_disease_context_1` | 918,539 | bit-identical |
| `enriched_has_inflammatory_go_annotation_1` | 1,996 | bit-identical |
| `enriched_module_size_1` | 1,157 | bit-identical |
| `enriched_shared_pathway_count_1` | 5,373,706 | bit-identical |
| `enriched_dwpc_GCD` | 42,227 | identical to 6 dp |
| `enriched_dwpc_GGD` | 3,380,853 | identical to 6 dp |
| `enriched_dwpc_GPGD` | 5,373,706 | identical to 6 dp |
| `enriched_guilt_by_association_1` | 3,380,853 | identical to 6 dp |
| `enriched_node_centrality_1` | 16,186 | identical to 6 dp |

The split is not arbitrary. Every bit-identical output is integer- or flag-valued. Every output that
moved carries **order-dependent float aggregation** — the DWPC metapaths sum `pow(deg*deg*deg*module,
-0.4)` over paths, and centrality is iterative. Changing the order Kuzu accumulates those moves the
last mantissa bits and nothing else.

Six datasets not being rebuilt in a given round acted as controls and were bit-identical every time,
so a differing signature always meant the rebuild rather than the measurement.

The three captures, in order:

| capture | file | read from |
|---|---|---|
| before the switch | [`signature-before-switch.json`](graph-snapshot-switch-2026-09-03/signature-before-switch.json) | `enriched_index_freezed-6bRVGs`, across the boundary |
| reference, both hashes | [`signature-reference-two-hash.json`](graph-snapshot-switch-2026-09-03/signature-reference-two-hash.json) | mixed — six switched, four still on the old snapshot |
| after the switch | [`signature-after-switch.json`](graph-snapshot-switch-2026-09-03/signature-after-switch.json) | `published_kg_ls-Mp25kL`, via the local `graph` folder |

The middle capture exists because the first round recorded only the strict hash. `row_xor_round6` was
added before the heavy datasets were rebuilt, which is why their verdict is definitive.

## What was deliberately not done

**Downstream was not rebuilt, and should not be.** Zone 11/12 assembly, the feature table, the
champion's scoring and the serving layer still hold outputs derived from the old snapshot. Rebuilding
them would re-score `hJLGoYn4` against features differing in the 7th decimal: it cannot improve
anything, and it can flip near-tied ranks and shift governed numbers in their last digits. The
features are equivalent, so there is no correctness reason to.

`enriched_index_freezed-6bRVGs` is now referenced by nothing. It is retained deliberately as the
provenance record for every published feature number, not as a dependency.

## Limitation

Stage 2 proves equality to 6 decimal places, not bitwise equality, for the five float-bearing
outputs. The per-row deltas for `enriched_dwpc_GCD` and `enriched_node_centrality_1` are no longer
recoverable: the first verification round captured only the strict hash, and the forced rebuild
overwrote the inputs to any per-row comparison. The rounded hash was added before the second round,
which is why the four heavy datasets carry a definitive verdict and those two rest on identical
aggregates plus the shared mechanism.
