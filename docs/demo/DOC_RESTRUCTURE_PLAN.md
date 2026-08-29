# Documentation and agent-context restructure plan

> **Lifecycle:** Decision · **Audience:** maintainers executing or reviewing the migration ·
> **Authority:** the approved restructure direction, phase boundaries and acceptance criteria ·
> **Update when:** an explicit approval changes scope or phase status · **Generated dependencies:**
> none · **Excludes:** implementation logs and current project facts owned by routed documents.

**Status: APPROVED — 2026-08-28.** Implementation remains phased, and the separate approval gates
defined below still apply. This plan supersedes the narrower plan raised on 2026-08-26, preserved
verbatim in the repository archive as the dated 2026-08-26 restructure plan.

This is a repository-wide information-governance change, not only a rename or a split of Part 2
documents. It covers current documentation, validation evidence, historical records, DSS build
governance, generated indexes, and the instruction surfaces used by both **Claude Code** and
**OpenAI Codex**.

No DSS flow, dataset, recipe, model, graph, webapp deployment, commit, or push is part of approving
this plan. Those are separately authorised implementation actions.

## 1. Outcomes

The restructure should make five things true:

1. A person or agent can identify the current source of truth without reading historical material.
2. A routine DSS build produces a machine audit record but no prose edits or agent review when no
   governed claim or contract changed.
3. Claude Code and OpenAI Codex receive equivalent, compact project rules without separately
   maintained copies drifting apart.
4. `DECISIONS.md` stops acting as a turn journal; only durable decisions appear in the current
   register, while the complete historical record remains preserved.
5. Index-first retrieval remains trustworthy and returns current evidence by default, with history
   available through an explicit path.

## 2. Problems this plan addresses

### 2.1 Mixed document responsibilities

`TARGET_PRIORITIZER.md` combines method, validation and presentation. Before Phase 2, the
dashboard-design document combined webapp contracts, analytical justification, DSS topology and
build history. This makes a local change
appear to require a review of several large documents and creates multiple homes for the same fact.

### 2.2 Current truth and history share a search surface

The claims index scans current documents, `DECISIONS.md`, archived build history, harness instructions
and skills together. Historical numbers are therefore reported beside current claims even when they
are intentionally superseded.

### 2.3 Automatic instruction payload is too large

The root instructions contain volatile project status. The webapp instructions also direct a fresh
agent to read the full webapp README before acting. Ordinary webapp work can therefore consume a
large orientation payload before any affected source file is inspected.

### 2.4 Harness copies can drift

Root `AGENTS.md` and `CLAUDE.md` already disagree on the current serving-layer state. The target-ID
skill also exists under both `.codex/` and `.claude/`. Supporting both harnesses is required; separately
authoring the same rules is not.

### 2.5 The decision log records operations

The existing decision log contains durable scientific and architectural decisions, but also file
moves, index construction, documentation cleanup, builds and incident chronology. Append-only capture
preserves history but does not provide a usable current decision surface.

### 2.6 Build verification is coupled to narrative logging

Reviewing every dataset or recipe operation protects against stale values, but an LLM review and a
prose entry are not required for every successful build. Deterministic checks should first establish
whether a governed claim or contract changed.

## 3. Governing principles

- **One fact, one authority.** Other surfaces reference or generate it; they do not restate it by
  hand.
- **Current and historical are different products.** Both are valuable, but they have different
  default retrieval paths.
- **Machine facts stay structured.** Job IDs, timestamps, row counts, schema hashes and check results
  belong in a machine ledger, not a narrative decision log.
- **Prompts route; they do not teach the whole repository.** Auto-loaded instructions contain safety
  rules and pointers, not full architecture or volatile status.
- **Build is not decision.** A build becomes a documentation event only when it changes a governed
  claim, contract, interpretation or durable operating rule.
- **Evidence precedes prose.** Notebooks and checks establish values before docs, webapp copy or demo
  claims are updated.
- **Default queries return current state.** Historical searches must be explicit.
- **Harness-neutral wording.** Shared rules use “agent” and “request user confirmation,” not tool names
  or interaction primitives that exist in only one harness.

## 4. Document lifecycle

Every maintained document must declare one lifecycle role in its opening section:

| role | purpose | default agent behaviour |
|---|---|---|
| **Canonical** | Current method, contract, narrative or policy | May be consulted for a matching task |
| **Evidence** | Assertions, measured results and provenance | Query targeted evidence; do not copy wholesale |
| **Generated** | Rebuilt from DSS or repository sources | Never edit by hand |
| **Decision** | Durable accepted/rejected choices | Query current register first |
| **Historical** | Superseded designs, build journals and chronology | Do not load unless explicitly investigating history |
| **Harness** | Auto-loaded safety rules and routing | Keep deliberately small |

Each canonical document should also state its audience, authority, update trigger, generated
dependencies and material explicitly excluded from its scope.

## 5. Target information architecture

### 5.1 Current project documents

| document | role and scope | explicitly excluded |
|---|---|---|
| `docs/overview/PROJECT_CONTEXT.md` | Stable overview of Parts 1 and 2 and their shared-object contract | Volatile build status and experiment chronology |
| `docs/graph/GRAPH_BUILDING.md` | Part 1 graph method and accepted construction contract | Part 2 modelling and routine job logs |
| `docs/prioritizer/TARGET_PRIORITIZER.md` | Part 2 modelling method, features, split, training, ablation and model-selection rationale | Detailed validation results, demo copy and migration diary |
| `docs/prioritizer/VALIDATION` *(new Markdown document)* | Compact evidence map: governed claims, assertion sources, interpretation and known limitations | Repeated implementation detail and copied notebook output |
| `docs/demo/DEMO_NARRATIVE.md` | Business story, order, audience voice and stable interpretation | API design, DSS topology and build procedure |
| `docs/demo/WEBAPP_DESIGN` *(renamed Markdown document)* | Vue/FastAPI architecture, routes, state, interaction and data contracts | Analytical proof, DSS flow duplication and build history |
| `docs/demo/FLOW_MAP.md` | Generated DSS zones, datasets, producers and consumers | Hand-authored rationale |
| `docs/operations/BUILD_GOVERNANCE` *(new Markdown document)* | Build classification, audit, baseline, review-packet and escalation policy | Individual build events |
| `docs/decisions/DECISION_REGISTER` *(new Markdown document)* | Current durable decisions with stable IDs and status | Routine operations and incident chronology |

`docs/README.md` remains the current-state router. It should list canonical, evidence and generated
documents first, with planning and historical indexes clearly separated.

### 5.2 Historical material

- Preserve the current `DECISIONS.md` unchanged as a dated historical record before replacing its
  current role.
- Keep `archive/DASHBOARD_BUILD_LOG.md` as chronology, not current guidance.
- Move dashboard mockup iterations 1 and 2 under an archived-iterations path. Only the current mockup
  appears in the default demo map.
- Preserve superseded plans and designs with a date and a pointer to their successor.
- Exclude historical documents from current claim-risk summaries and default decision queries.

## 6. Cross-harness instruction architecture

Claude Code and OpenAI Codex should receive the same project policy with only the minimum
harness-specific wrapper required for discovery.

### 6.1 Root instructions

- Establish one canonical source for shared project rules.
- Generate or mechanically synchronise root `CLAUDE.md` and `AGENTS.md` from that source.
- Prefer generation plus a parity check over manually maintained copies. A symlink may be used only
  after confirming it is portable across the team's environments and both harnesses.
- Keep only: project routing, destructive-operation prohibitions, measurement rules, source-of-truth
  rules, authorisation boundaries and index-first commands.
- Move volatile status, current model identity, active work tracks and detailed platform traps into
  generated indexes or task-specific documents.

### 6.2 Nested webapp instructions

- Reduce `webapp/AGENTS.md` to a concise overlay containing only webapp-specific constraints and
  pointers.
- Maintain `webapp/CLAUDE.md` as the equivalent Claude entry point; its current symlink is acceptable
  if portability is confirmed.
- Remove the blanket requirement to read the complete `webapp/README.md` first.
- Route by task: deployment reads deployment sections; DSS embedding reads the embedding contract;
  UI changes read the design-token and component guidance.

### 6.3 Skills

- Treat the target-ID skill as one logical package with Claude and Codex entry points.
- Keep shared content canonical and validate both installed copies mechanically.
- Separate short default routing from longer task procedures.
- Exclude harness instructions and skills from the project claims index.

### 6.4 Context budgets

Initial acceptance targets:

- Root plus nested auto-loaded project instructions: **at most 3,000 tokens** for an ordinary webapp
  task.
- No instruction file may require reading an entire general README before the task is classified.
- Default index queries return a bounded result set rather than full TSV files.
- Historical files are never part of cold-start reading.

These are engineering budgets, not permanent product limits; revise them only with measured evidence.

## 7. Decision governance

### 7.1 Admission rule

A current decision record is created only when a choice:

1. changes product scope, methodology, measurement policy, architecture, shared contracts, safety or
   a lasting operating rule;
2. affects future work beyond the immediate operation;
3. records meaningful alternatives or a falsified assumption; and
4. cannot be reconstructed cheaply from Git history, notebook assertions or the machine build ledger.

Successful builds, file moves, document synchronisation, generated-index refreshes and ordinary bug
fixes do not qualify by themselves.

### 7.2 Record format

Each current record receives a stable ID and the fields: date, domain, status, decision, rationale,
evidence, consequences and `supersedes`/`superseded_by`. Detailed rationale may live in a short ADR
linked from the register when a single row is insufficient.

### 7.3 Migration

1. Archive the existing log without rewriting it.
2. Classify its entries as durable decision, reusable trap, experiment evidence, incident history or
   operation.
3. Promote only durable decisions to the current register.
4. Route reusable traps to the target-ID skill or DSS cheatsheet, experiment evidence to validation,
   and chronology to the archive.
5. Generate separate current and historical decision indexes.

## 8. Build governance

### 8.1 Separation of responsibilities

The DSS scenario or repository build wrapper performs deterministic detection and routing. It does
not ask an LLM to review every dataset and does not edit Git documentation directly.

Every build writes a structured machine event containing the job ID, targets, outcome, recipe/settings
fingerprints, schema fingerprints, configured metrics, assertion results and accepted-baseline ID.

### 8.2 Classification

| classification | required action |
|---|---|
| `NO_CHANGE` | Append machine audit; no agent call and no Markdown edit |
| `REFRESH_ONLY` | Refresh machine state; no prose review |
| `EXPECTED_DATA_DELTA` | Rerun mapped checks and refresh generated status |
| `CLAIM_DELTA` | Produce a compact packet naming changed claims and consumers for targeted review |
| `CONTRACT_DELTA` | Produce a compact packet naming changed schemas, recipes or APIs and consumers |
| `INCIDENT` | Fail or flag the build; preserve diagnostics; promote only a reusable lesson |

### 8.3 Claim registry

Introduce a structured registry mapping each governed claim to:

- a stable claim ID;
- authoritative notebook assertion or DSS check;
- precision or tolerance;
- current documentation consumers;
- webapp/API consumers;
- review policy.

Extend the current indexes from this registry rather than discovering every relationship by scanning
all prose. The webapp should read volatile measurements from governed data or a generated status
endpoint instead of duplicating them in source code.

### 8.4 DSS boundary

- If builds are initiated in DSS by several people or triggers, use a DSS scenario for build,
  verification, fingerprint comparison and audit routing.
- If builds are initiated mainly through the repository, use a governed command wrapper implementing
  the same contract.
- A hybrid is preferred here: DSS owns job execution and the machine ledger; repository tooling owns
  claim-to-consumer mapping and documentation checks.
- The scenario is never installed in `KNOWLEDGE_GRAPH_PRIMEKG`, cannot target `compute_kg`, and uses an
  explicit target allowlist.
- Creating or changing a live scenario requires separate user approval.

## 9. Index and verification redesign

- Replace the current “all tracked Markdown” claims scan with an explicit manifest of current
  claim-bearing documents.
- Exclude archives, decision history, agent instructions, skills and setup READMEs from current claim
  risk.
- Retain a separately named historical claims index when historical comparison is useful.
- Generate current decision, historical decision, claim, model, feature, recipe and code indexes with
  clear ownership and freshness metadata.
- Make compact checks the default. Detailed diffs go to files or bounded sections rather than
  unbounded terminal output.
- Change `make logs` to a bounded tail and reserve continuous following for an explicitly interactive
  command.
- Keep link checking across current docs; check archived links only for archive integrity, not current
  validity.

## 10. Migration sequence

### Phase 0 — baseline and safety

1. Approve this plan and record unresolved choices.
2. Capture current file sizes, index sizes, instruction payload and link/index status.
3. Freeze copies of the current decision log, plans and historical mockups.
4. Do not modify DSS or rebuild the graph.

### Phase 1 — harness parity and routing

1. Define the canonical shared instruction source.
2. Produce compact, equivalent `AGENTS.md` and `CLAUDE.md` entry points.
3. Slim the webapp overlay and remove unconditional README loading.
4. Canonicalise the target-ID skill and add parity/freshness checks.
5. Verify cold-start behaviour in both Claude Code and OpenAI Codex.

### Phase 2 — current versus historical documents

1. Add lifecycle metadata and scope statements to current documents.
2. Rename the technical design document to the planned `WEBAPP_DESIGN.md` and update links.
3. Move native-dashboard evaluation and build chronology to the archive, not the current decision
   register.
4. Archive older mockups and leave one current mockup in the active map.
5. Remove hand-authored flow duplication in favour of `FLOW_MAP.md`.

### Phase 3 — method and validation split

1. Reduce `TARGET_PRIORITIZER.md` to modelling method and model-selection rationale.
2. Create the planned `VALIDATION` document as the evidence map, with notebooks remaining
   computational authority.
3. Assign stable claim IDs and build the claim-to-consumer registry.
4. Reconcile abstracts, summaries, demo claims and webapp consumers against the registry.

### Phase 4 — decision migration

1. Archive the current log unchanged.
2. Triage entries using the admission rule.
3. Create the current decision register and any necessary ADRs.
4. Build separate current and historical decision indexes.

### Phase 5 — build governance

1. Specify the machine event, accepted baseline and review-packet schemas.
2. Add deterministic fingerprint and classification tooling.
3. Pilot it on a safe Part 2 leaf build only after explicit approval.
4. Confirm a no-change build produces no documentation changes or agent review.
5. Extend to additional approved build targets only after the pilot is stable.

### Phase 6 — indexes and checks

1. Add the current-doc manifest and historical exclusions.
2. Rebuild affected indexes without `--refresh` unless live DSS recipes changed.
3. Run link, harness-parity, claim-registry and index-freshness checks.
4. Measure retrieval and context cost against the Phase 0 baseline.

## 11. Acceptance criteria

The restructure is complete only when:

- Claude Code and OpenAI Codex receive semantically equivalent project rules.
- Root plus nested automatic project instructions meet the agreed context budget.
- Neither harness is told to read a whole general-purpose document before classifying the task.
- Every current document has one declared role, authority and update trigger.
- Method, validation, demo narrative, webapp design and DSS topology have non-overlapping ownership.
- One current dashboard mockup is on the default path; older iterations are historical.
- The current decision register contains durable decisions only and uses stable identifiers.
- Existing decision and build history remains recoverable and unchanged in the archive.
- Current claim-risk output excludes history and harness material.
- A no-change DSS build writes a machine audit event but causes zero Markdown edits and zero LLM review
  calls.
- A claim or contract delta identifies only its mapped consumers for review.
- Link, index, harness-parity and notebook assertion checks pass.
- No graph recomputation, frozen-reference mutation, commit or push occurs without explicit approval.

## 12. Decisions required before implementation

The recommended defaults are listed first:

1. **Harness synchronisation:** generate both root instruction files from one canonical source and
   enforce parity in checks; use symlinks only if portability is proven.
2. **Validation authority:** notebooks compute truth; the planned `VALIDATION` document maps and
   interprets it.
3. **Decision migration:** preserve the old log in full and curate a smaller current register rather
   than editing history in place.
4. **Build audit storage:** keep the full event ledger in DSS; keep only schemas, policy and optional
   accepted snapshots in Git.
5. **Governance execution:** pilot a hybrid DSS-scenario/repository-index design, with no LLM in the
   no-change path.

Approval of this document authorises planning and repository documentation work only. Live DSS
scenario creation, build execution, deployment, deletion, Git commit and push remain separate actions.
