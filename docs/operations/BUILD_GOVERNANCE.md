# Build governance

> **Lifecycle:** Canonical · **Audience:** DSS operators, repository contributors and reviewers ·
> **Authority:** repository-side build classification contract · **Update when:** an event schema,
> classification, approved target boundary or claim/consumer mapping changes · **Generated
> dependencies:** none · **Excludes:** live DSS scenario configuration and the DSS event ledger.

This contract prevents a routine DSS build from becoming an unbounded documentation review. DSS
will eventually own execution and its append-only machine ledger; repository tooling owns stable
fingerprinting, classification, governed-claim mapping and compact consumer routing. No build event
creates a Markdown log.

## Artifacts

- [`machine-event.schema.json`](build-governance/machine-event.schema.json) records job identity,
  approved targets, outcome, semantic fingerprints, configured metrics, governed values, assertion
  results and the accepted baseline ID.
- [`accepted-baseline.schema.json`](build-governance/accepted-baseline.schema.json) is an explicitly
  accepted semantic snapshot, including who accepted it, why, and the checks every later event must
  report. A successful event never promotes itself automatically.
- [`review-packet.schema.json`](build-governance/review-packet.schema.json) is the bounded output. It
  names changed claims or contracts and only their registered consumers.
- [`POLICY.json`](build-governance/POLICY.json) is an explicit Part 2 leaf-target allowlist,
  target-specific capture contract and contract-to-consumer map. Each target declares the exact
  recipe, schema, data, refresh, metric, claim and assertion evidence an event must carry. Listing a
  target is eligibility for a future pilot, not build approval.

Fingerprints are SHA-256 over UTF-8 canonical JSON: object keys sorted, no insignificant whitespace,
Unicode preserved and non-finite numbers rejected. Dataset content fingerprints must be computed in
DSS from a deterministic, order-stable representation; volatile job IDs and timestamps are never
part of semantic comparison. `refresh_state` is deliberately separate.

## Classification and routing

Precedence is `INCIDENT` → `CONTRACT_DELTA` → `CLAIM_DELTA` → `EXPECTED_DATA_DELTA` →
`REFRESH_ONLY` → `NO_CHANGE`. A packet retains all detected changes even when a higher-precedence
class wins.

| Classification | Deterministic condition | Route |
|---|---|---|
| `NO_CHANGE` | Accepted fingerprints, metrics and governed values match | Append machine event only; no agent or prose edit |
| `REFRESH_ONLY` | Only refresh-state fingerprints differ | Refresh machine state; no agent or prose edit |
| `EXPECTED_DATA_DELTA` | Data/non-claim metrics differ and every mapped assertion passes | Rerun mapped checks and generated status; no prose review |
| `CLAIM_DELTA` | A governed value moves beyond its registry tolerance | Review only the claim registry's named consumers |
| `CONTRACT_DELTA` | Recipe settings or a schema fingerprint changes | Review only the policy's named contract consumers |
| `INCIDENT` | Build fails/aborts, an assertion fails/errors, evidence is missing, or a changed contract is unmapped | Fail or flag and retain diagnostics; promote only a reusable lesson |

The hard denials for project/target `KNOWLEDGE_GRAPH_PRIMEKG` and recipe `compute_kg` exist in both
policy and code. Any target not explicitly allowed is refused before classification. A live scenario,
scenario change or build still requires separate explicit user approval.

The repository classifier operates on a captured event; it is not a build launcher or an
authorization mechanism. Before any future job starts, the approved DSS pilot must apply the same
project/target policy as a preflight and use only the producing Part 2 leaf recipe. Recursive builds,
upstream propagation and policy expansion remain unapproved. Missing or extra capture fields are an
incident, never evidence of `NO_CHANGE`.

## Offline use

```sh
python3 tools/build_governance.py fingerprint observation.json
python3 tools/build_governance.py classify \
  --event event.json --baseline accepted-baseline.json
python3 -m unittest discover -s tools/tests -p 'test_build_governance.py'
```

The classifier reads JSON and writes one packet to standard output unless `--output` is explicitly
given. It has no DSS dependency, invokes no agent and edits no documentation. The fixture suite proves
all six routes, canonical fingerprint stability, target denials, fail-closed evidence capture and the
zero-review/no-Markdown-write no-change path. Metric keys are target-qualified (for example,
`breast_panel_metrics.row_count`) so a future multi-target event cannot collapse two measurements.
Live event capture, ledger append, baseline acceptance and the leaf-build pilot remain deferred until
separately approved.
