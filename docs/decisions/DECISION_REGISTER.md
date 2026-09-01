# Current decision register

> **Lifecycle:** Canonical · **Audience:** contributors, reviewers and build-governance tooling ·
> **Authority:** current durable choices and their consequences · **Update when:** a choice satisfying
> the admission rule is accepted, superseded or rejected · **Generated dependencies:**
> `.index/decisions.tsv` · **Excludes:** experiments, incidents, routine operations and chronology.

This register is intentionally small. Add a record only when a choice changes lasting scope,
methodology, measurement, architecture, contracts, safety or operating policy; affects future work;
captures meaningful alternatives or a falsified assumption; and cannot be reconstructed cheaply
from Git, notebook assertions or the machine build ledger. Use an ADR only when the rationale will
not fit here. The retired turn log is preserved under [`archive/decisions/`](../../archive/decisions/README.md).

## DEC-PROD-001 — Explainable prioritization is the flagship

- **Date:** 2026-07-08
- **Domain:** product
- **Status:** accepted
- **Decision:** Prioritize explainable disease-to-target ranking with SHAP and evidence paths; discovery is the primary use case and toxicity is not inferred from indirect proxies.
- **Rationale:** The POC must let a scientist inspect why a target ranks, not only receive a score.
- **Evidence:** [`PROJECT_CONTEXT.md`](../overview/PROJECT_CONTEXT.md), [`DEMO_NARRATIVE.md`](../demo/DEMO_NARRATIVE.md)
- **Consequences:** Product surfaces expose ranked candidates, evidence and limitations; they do not claim autonomous target selection or safety prediction.
- **Supersedes:** —
- **Superseded by:** —
- **Historical sources:** lines 16

## DEC-PROD-002 — The deliverable is filterable, not pre-cut

- **Date:** 2026-08-17
- **Domain:** product
- **Status:** accepted
- **Decision:** Serve a ranked candidate list with user-controlled filters and annotations rather than a single pre-filtered shortlist.
- **Rationale:** Tractability and class constraints depend on the scientist's modality and question; hard filters can hide useful evidence.
- **Evidence:** [`DEMO_NARRATIVE.md`](../demo/DEMO_NARRATIVE.md), [`WEBAPP_DESIGN.md`](../demo/WEBAPP_DESIGN.md)
- **Consequences:** Filtering changes presentation, not the underlying model score or candidate population.
- **Supersedes:** —
- **Superseded by:** —
- **Historical sources:** lines 51

## DEC-PROD-003 — The pitch separates efficacy from developability

- **Date:** 2026-08-01
- **Domain:** product
- **Status:** accepted
- **Decision:** Frame the POC around two distinct questions: genetic/biological evidence for efficacy and chemical/therapeutic evidence for developability.
- **Rationale:** Collapsing the questions encourages overclaiming; the gap between them is where governed platform work adds value.
- **Evidence:** [`PROJECT_CONTEXT.md` §2.1](../overview/PROJECT_CONTEXT.md), [`DEMO_NARRATIVE.md`](../demo/DEMO_NARRATIVE.md)
- **Consequences:** Neither evidence axis is presented as a substitute for the other.
- **Supersedes:** —
- **Superseded by:** —
- **Historical sources:** —

## DEC-GRAPH-001 — Build the graph from auditable sources

- **Date:** 2026-06-01
- **Domain:** graph
- **Status:** accepted
- **Decision:** Recreate the graph pipeline from sources, substitute unavailable licensed inputs with compatible public sources, and retain the published graph only as a frozen reference.
- **Rationale:** Pipeline recreation and source governance are the Part 1 product; loading a pre-built graph would bypass them.
- **Evidence:** [`GRAPH_BUILDING.md`](../graph/GRAPH_BUILDING.md), [`PROJECT_CONTEXT.md` §4](../overview/PROJECT_CONTEXT.md)
- **Consequences:** Source versions and freeze procedures are recorded; the frozen reference is never an ordinary build target.
- **Supersedes:** loading the published pre-built graph as the primary pipeline
- **Superseded by:** —
- **Historical sources:** —

## DEC-ARCH-001 — Graph and prioritizer remain separate DSS projects

- **Date:** 2026-08-17
- **Domain:** architecture
- **Status:** accepted
- **Decision:** `DEMO_KG_LS` owns graph construction; `DEMO_TARGET_IDENTIFICATION` consumes 12 synced datasets plus one direct-read Kuzu folder through an explicit shared-object contract and owns modeling, validation and serving.
- **Rationale:** Separating graph construction protects the accepted graph from recursive model-side builds and gives the two parts a stable contract.
- **Evidence:** [ADR-001](adrs/ADR-001-project-boundary.md), [`PROJECT_CONTEXT.md` §4](../overview/PROJECT_CONTEXT.md)
- **Consequences:** Graph-derived inputs cross only through the declared shared-object interface; non-graph modeling sources stay with Part 2.
- **Supersedes:** the single-project layout
- **Superseded by:** —
- **Historical sources:** lines 39, 40

## DEC-ARCH-002 — Graph rebuild acceptance is structural

- **Date:** 2026-08-13
- **Domain:** architecture
- **Status:** accepted
- **Decision:** Accept a graph rebuild on declared structural invariants and provenance rather than byte-identical output from live public sources.
- **Rationale:** Pinning every source would trade away a reproducible public-source pipeline for an exact diff that is not biologically meaningful.
- **Evidence:** [`GRAPH_BUILDING.md`](../graph/GRAPH_BUILDING.md), [`PROJECT_CONTEXT.md` §4.5](../overview/PROJECT_CONTEXT.md)
- **Consequences:** Accepted rebuilds document source state and compare schema, counts, relations and downstream reconstruction within predeclared tolerances.
- **Supersedes:** byte-exact rebuild acceptance
- **Superseded by:** —
- **Historical sources:** —

## DEC-ARCH-003 — Flow zones are named for questions

- **Date:** 2026-08-18
- **Domain:** architecture
- **Status:** accepted
- **Decision:** Organize validation and serving zones by the question they answer, not by the DSS tool used.
- **Rationale:** Question-oriented zones support the objection-led demo and make evidence ownership visible.
- **Evidence:** [`FLOW_MAP.md`](../demo/FLOW_MAP.md), [`DEMO_NARRATIVE.md`](../demo/DEMO_NARRATIVE.md)
- **Consequences:** Tool changes do not require conceptual zone renames; generated topology remains the flow authority.
- **Supersedes:** tool-oriented zone naming
- **Superseded by:** —
- **Historical sources:** lines 73, 75

## DEC-ARCH-004 — Compute metapaths as factorized matrices

- **Date:** 2026-08-10
- **Domain:** architecture
- **Status:** accepted
- **Decision:** Implement functional metapaths as factorized right-to-left matrix operations rather than graph queries.
- **Rationale:** The query engine exhausted its buffer pool even with fan-out protection, while the factorized calculation bounds the intermediate state.
- **Evidence:** [`TARGET_PRIORITIZER.md` §3.3](../prioritizer/TARGET_PRIORITIZER.md)
- **Consequences:** Metapath feature recipes preserve the factorized matrix contract when extended.
- **Supersedes:** graph-query metapath execution
- **Superseded by:** —
- **Historical sources:** lines 28

## DEC-ARCH-005 — Random walks use sparse bounded computation

- **Date:** 2026-06-30
- **Domain:** architecture
- **Status:** accepted
- **Decision:** Implement random-walk scoring with sparse arrays and bounded parallelism rather than a monolithic in-memory graph library.
- **Rationale:** Materializing Python graph objects for the full graph is not operationally viable.
- **Evidence:** [`GRAPH_BUILDING.md`](../graph/GRAPH_BUILDING.md)
- **Consequences:** Random-walk extensions must preserve sparse representations and bounded worker counts.
- **Supersedes:** monolithic in-memory traversal
- **Superseded by:** —
- **Historical sources:** lines 164

## DEC-METH-001 — Candidate eligibility is an evidence boundary

- **Date:** 2026-08-08
- **Domain:** methodology
- **Status:** accepted
- **Decision:** Apply the evidence-bearing candidate population to train and test; reject filters whose missingness is created by label lookup, and do not widen eligibility merely because a rejected feature has broader coverage.
- **Rationale:** A feature can be removed while its label-derived presence still leaks through row selection.
- **Evidence:** [ADR-002](adrs/ADR-002-candidate-and-evaluation-boundary.md), [`TARGET_PRIORITIZER.md` §2](../prioritizer/TARGET_PRIORITIZER.md)
- **Consequences:** Candidate-route changes are population interventions requiring explicit revalidation, not ordinary feature changes.
- **Supersedes:** proximity-threshold-only eligibility
- **Superseded by:** —
- **Historical sources:** lines 22, 33

## DEC-METH-002 — Split by curated family and report by disease

- **Date:** 2026-08-09
- **Domain:** methodology
- **Status:** accepted
- **Decision:** Assign related diseases through an external curated family antichain, split by family and report ranking metrics per disease.
- **Rationale:** Ontology-derived grouping leaks broad parents, while reporting at family level erases mechanism-specific difficulty.
- **Evidence:** [`TARGET_PRIORITIZER.md` §§2.1, 2.3](../prioritizer/TARGET_PRIORITIZER.md), [`VALIDATION.md` §3.1](../prioritizer/VALIDATION.md)
- **Consequences:** All validation splits preserve family integrity; family tables describe the validation sample rather than graph prevalence.
- **Supersedes:** graph-topological family construction
- **Superseded by:** —
- **Historical sources:** lines 21, 24

## DEC-METH-003 — Subtype diagnostics use disease family, not split-key identity

- **Date:** 2026-08-17
- **Domain:** methodology
- **Status:** accepted
- **Decision:** Select subtype-granularity comparisons by curated disease family rather than by an arbitrary split-key integer.
- **Rationale:** Split-key elevation can change when node identifiers are remapped even when family semantics are unchanged.
- **Evidence:** [`TARGET_PRIORITIZER.md` §2.3](../prioritizer/TARGET_PRIORITIZER.md), [`DSS_CHEATSHEET.md` §1](../platform/DSS_CHEATSHEET.md)
- **Consequences:** Diagnostics survive identifier remapping and continue comparing the intended disease family.
- **Supersedes:** split-key-selected subtype diagnostics
- **Superseded by:** —
- **Historical sources:** lines 45

## DEC-METH-004 — Outcome-linked routes do not define their own benchmark

- **Date:** 2026-08-19
- **Domain:** methodology
- **Status:** accepted
- **Decision:** Exclude route-only outcome-selected pairs from drug-evaluation denominators and report both the full and supported benchmarks rather than dropping whole diseases.
- **Rationale:** The drug route selects the evaluation population on the outcome; deleting the route loses valid positives while leaving the bias unresolved.
- **Evidence:** [ADR-002](adrs/ADR-002-candidate-and-evaluation-boundary.md), [`VALIDATION.md` §§3.2, 6.2](../prioritizer/VALIDATION.md)
- **Consequences:** Therapeutic metrics remain sensitivity analyses and never replace association validation.
- **Supersedes:** dropping `dwpc_GCD` from the candidate filter
- **Superseded by:** —
- **Historical sources:** lines 86, 90

## DEC-METH-005 — Numeric feature handling is explicit

- **Date:** 2026-08-10
- **Domain:** methodology
- **Status:** accepted
- **Decision:** Standard-rescale and mean-impute every numeric model input, and audit per-feature handling after each deployment.
- **Rationale:** DSS feature-handling guesses can vary between deployments and silently change the model contract.
- **Evidence:** [`TARGET_PRIORITIZER.md` §4](../prioritizer/TARGET_PRIORITIZER.md), [`DSS_CHEATSHEET.md` §1](../platform/DSS_CHEATSHEET.md)
- **Consequences:** Deployment review verifies the saved model's actual preprocessing rather than trusting defaults.
- **Supersedes:** per-deployment inferred handling
- **Superseded by:** —
- **Historical sources:** lines 29

## DEC-MEAS-001 — Headline metrics are paired and disease-level

- **Date:** 2026-08-09
- **Domain:** measurement
- **Status:** accepted
- **Decision:** Headline AUROC is macro per disease, never pooled; AUPRC supports model selection and head-of-list analysis but is not reported as an unqualified per-disease aggregate. Report tie counts before small mean differences and prefer stratified paired tests.
- **Rationale:** Pooled estimates reward cross-disease prevalence and small mean changes here are often driven by a few diseases.
- **Evidence:** [`VALIDATION.md` §3.1](../prioritizer/VALIDATION.md), [`TARGET_PRIORITIZER.md` §5](../prioritizer/TARGET_PRIORITIZER.md)
- **Consequences:** Model comparisons carry estimator, unit of analysis, ties and paired uncertainty.
- **Supersedes:** pooled-AUROC headline reporting
- **Superseded by:** —
- **Historical sources:** lines 23, 108, 127

## DEC-MEAS-002 — Validation uses multiple axes and both ground truths

- **Date:** 2026-08-13
- **Domain:** measurement
- **Status:** accepted
- **Decision:** Evaluate association ranking, therapeutic evidence, tractability and discovery separately; report both association and drug-supported labels, and use expert review where labels cannot resolve plausibility.
- **Rationale:** The axes are not interchangeable, and improvement on one can hide regression or shortcut learning on another.
- **Evidence:** [`VALIDATION.md` §§3.2, 6](../prioritizer/VALIDATION.md)
- **Consequences:** No single metric establishes utility; claims state which axis and evidence source they cover.
- **Supersedes:** association-only validation
- **Superseded by:** —
- **Historical sources:** lines 35, 55, 56, 65, 85

## DEC-MEAS-003 — Drug-label training is rejected; lookup baselines are warnings

- **Date:** 2026-08-14
- **Domain:** measurement
- **Status:** accepted
- **Decision:** Keep the association objective; do not optimize the drug-target benchmark, and always compare such benchmarks with the simplest gene-popularity lookup.
- **Rationale:** Drug-label training sacrificed association quality while a lookup table beat the trained benchmark, showing that the benchmark rewards popularity.
- **Evidence:** [`VALIDATION.md` §5](../prioritizer/VALIDATION.md), [`TARGET_PRIORITIZER.md` §5](../prioritizer/TARGET_PRIORITIZER.md)
- **Consequences:** Drug-target performance is a warning and sensitivity axis, not the training objective.
- **Supersedes:** treating drug-target AUROC as a direct optimization target
- **Superseded by:** —
- **Historical sources:** lines 37, 38

## DEC-DATA-001 — Druggability and target class annotate but do not rank

- **Date:** 2026-08-11
- **Domain:** data
- **Status:** accepted
- **Decision:** Keep druggability and target-class data as per-gene annotations and filters, not model inputs or graph topology.
- **Rationale:** Their association-label direction can oppose therapeutic intuition; a presentation grouping recovers utility without corrupting the model objective.
- **Evidence:** [`TARGET_PRIORITIZER.md` §3.2](../prioritizer/TARGET_PRIORITIZER.md), [`DEMO_NARRATIVE.md` Act 4](../demo/DEMO_NARRATIVE.md)
- **Consequences:** Annotation changes do not renumber graph nodes or retrain the model.
- **Supersedes:** druggability as a candidate model feature
- **Superseded by:** —
- **Historical sources:** lines 31, 47

## DEC-SAFE-001 — Indirect safety proxies cannot filter candidates

- **Date:** 2026-08-17
- **Domain:** safety
- **Status:** accepted
- **Decision:** Do not filter targets using loss-of-function intolerance or positive-only safety-liability annotations; a safety axis requires direct measurements such as essentiality and expression breadth.
- **Rationale:** The available proxies measure biological importance or research attention and move in the wrong direction for a safety exclusion.
- **Evidence:** [`VALIDATION.md` §5](../prioritizer/VALIDATION.md), [`DEMO_NARRATIVE.md` Acts 5–6](../demo/DEMO_NARRATIVE.md)
- **Consequences:** Safety-liability data is display-only and blank values mean unknown, not safe.
- **Supersedes:** proxy-based safety filtering
- **Superseded by:** —
- **Historical sources:** lines 49, 50

## DEC-DEMO-001 — The demo is an objection ladder

- **Date:** 2026-08-19
- **Domain:** demo
- **Status:** accepted
- **Decision:** Present the POC as an ordered set of scientist objections, with leakage controls, refuted gates and limitations in the main story; the reusable platform claim is disciplined hypothesis gating, not a single model score.
- **Rationale:** Trust depends on showing what was falsified and where the system stops, not on a scorecard.
- **Evidence:** [`DEMO_NARRATIVE.md`](../demo/DEMO_NARRATIVE.md)
- **Consequences:** Confound controls and negative results remain front-of-house material.
- **Supersedes:** metric-led scorecard narrative
- **Superseded by:** —
- **Historical sources:** lines 76, 99, 101

## DEC-DEMO-002 — The narrative governs the dashboard

- **Date:** 2026-08-19
- **Domain:** demo
- **Status:** accepted
- **Decision:** Derive the dashboard and flow-facing presentation from the approved demo narrative, never prune evidence because it is absent from a hypothetical UI.
- **Rationale:** Dashboard-first pruning removed the evidence needed to answer common scientific objections.
- **Evidence:** [`DEMO_NARRATIVE.md`](../demo/DEMO_NARRATIVE.md), [`WEBAPP_DESIGN.md`](../demo/WEBAPP_DESIGN.md)
- **Consequences:** UI scope cannot redefine analytical truth or evidence retention.
- **Supersedes:** dashboard-derived evidence scope
- **Superseded by:** —
- **Historical sources:** lines 77, 100

## DEC-OPS-001 — Identifier remapping audits ordering semantics

- **Date:** 2026-08-17
- **Domain:** operations
- **Status:** accepted
- **Decision:** When graph identifiers are reassigned, audit every rule that ranks, minimizes or applies modulo to them; literal substitution alone is insufficient.
- **Rationale:** Three rules depended on integer order despite stable biological identifiers.
- **Evidence:** [`DSS_CHEATSHEET.md` §1](../platform/DSS_CHEATSHEET.md)
- **Consequences:** Migration verification includes semantic outputs for splits, family assignment and filters.
- **Supersedes:** literal-only index remapping
- **Superseded by:** —
- **Historical sources:** lines 44

## DEC-OPS-002 — Snapshot before destructive DSS changes

- **Date:** 2026-08-19
- **Domain:** operations
- **Status:** accepted
- **Decision:** Capture recoverable configuration and evidence before deleting or materially replacing DSS objects.
- **Rationale:** Saved models and experiments can be evidence even when they are no longer live consumers.
- **Evidence:** [`DSS_CHEATSHEET.md` §6](../platform/DSS_CHEATSHEET.md)
- **Consequences:** Deletion remains separately authorized and follows a verified snapshot.
- **Supersedes:** —
- **Superseded by:** —
- **Historical sources:** lines 79

## DEC-OPS-003 — Notebook assertions govern documented numbers

- **Date:** 2026-08-19
- **Domain:** operations
- **Status:** accepted
- **Decision:** Make notebooks the computational authority for every governed documented number.
- **Rationale:** Prose drifts; assertion-first review turns discrepancies into a bounded worklist.
- **Evidence:** [`VALIDATION.md` §§1, 7](../prioritizer/VALIDATION.md), [`CLAIM_REGISTRY.json`](../prioritizer/CLAIM_REGISTRY.json)
- **Consequences:** A headline without an assertion is not governed evidence; assertion failures are investigated before prose is edited.
- **Supersedes:** prose-first metric maintenance
- **Superseded by:** —
- **Historical sources:** lines 96

## DEC-OPS-004 — Population interventions use pre-registered staged rollout

- **Date:** 2026-08-20
- **Domain:** operations
- **Status:** accepted
- **Decision:** Change one population or feature-family intervention per model, declare predictions and adopt/reject rules before execution, and adopt only after the complete comparison.
- **Rationale:** Staging preserves causal interpretation and prevents a promising aggregate from rewriting the question after the result.
- **Evidence:** [`PHASE3_PREREGISTRATION.md`](../prioritizer/PHASE3_PREREGISTRATION.md)
- **Consequences:** Post-result prediction changes are failures, not revisions.
- **Supersedes:** bundled exploratory rollout
- **Superseded by:** —
- **Historical sources:** lines 121

## DEC-OPS-005 — Build review is routed by semantic delta

- **Date:** 2026-08-31
- **Domain:** operations
- **Status:** accepted
- **Decision:** Classify governed DSS builds deterministically against an explicitly accepted baseline; keep no-change and refresh-only events machine-readable, and request targeted review only for claim, contract or incident deltas.
- **Rationale:** Sending every routine dataset or recipe operation through an agent repeats unchanged context, burns tokens and recreates documentation drift without adding review value.
- **Evidence:** [`BUILD_GOVERNANCE.md`](../operations/BUILD_GOVERNANCE.md), [`DOC_RESTRUCTURE_PLAN.md` §8](../demo/DOC_RESTRUCTURE_PLAN.md)
- **Consequences:** Build events never write prose directly; live execution uses explicit target and evidence contracts, and scenario creation or a pilot build remains separately authorized.
- **Supersedes:** per-operation agent review and turn-by-turn Markdown build logging
- **Superseded by:** —
- **Historical sources:** —

## DEC-MODEL-001 — `m7-f14` is the current champion

- **Date:** 2026-08-21
- **Domain:** model
- **Status:** accepted
- **Decision:** Use saved model `m7-f14` (`hJLGoYn4`) as the champion; retain `prox_kernel` rather than the higher-AUPRC `prox_mean` alternative.
- **Rationale:** The selected model is the first improvement supported by paired evidence across the decision axes; the alternative did not improve tractability and worsened hub spread.
- **Evidence:** [`VALIDATION.md` §§2, 4.2](../prioritizer/VALIDATION.md), [`TARGET_PRIORITIZER.md` §5](../prioritizer/TARGET_PRIORITIZER.md), `tools/model_registry.json`
- **Consequences:** Champion consumers and governed claims point to `hJLGoYn4`; a future replacement must satisfy the same multi-axis selection rule.
- **Supersedes:** `m3-f12`
- **Superseded by:** —
- **Historical sources:** lines 130, 137, 139

## DEC-PH3-001 — Phase 3 is a pre-registered coverage intervention

- **Date:** 2026-08-21
- **Domain:** methodology
- **Status:** approved-not-executed
- **Decision:** Test the seed-gate widening only in a duplicated Part 2 project; widen the nine Class 1 recipes while holding the Class 2 GO-metapath aggregate at 20, score before retraining and apply the pre-registered rule without post-result revision.
- **Rationale:** The change rewrites the candidate population and promises coverage, not intrinsic model quality; Class 2 aggregation could alter the control stratum.
- **Evidence:** [`PHASE3_PREREGISTRATION.md`](../prioritizer/PHASE3_PREREGISTRATION.md), [`TARGET_PRIORITIZER.md` §6](../prioritizer/TARGET_PRIORITIZER.md)
- **Consequences:** No live project or current model is changed by this approval; execution requires its own project and build authorization.
- **Supersedes:** widening all ten gated recipes uniformly
- **Superseded by:** —
- **Historical sources:** lines 150, 151, 171, 172

## DEC-OPS-006 — Panel identity is governed by variable; seed gates stay hardcoded

- **Date:** 2026-09-01
- **Domain:** operations
- **Status:** accepted
- **Decision:** Demo-panel identity and the reporting thresholds move to project variables — `demo_panel` (names only, with `node_index` resolved from `graph_nodes` at run time) and the flat scalars `trust_n_pos`, `panel_n_pos`, `near_dup`, `ks`, `topn`. The ten seed-gated recipes keep their gate as a literal and are deliberately excluded, even though `module_size_gate` exists as a variable.
- **Rationale:** Pinned `node_index` values fail silently — a graph rebuild renumbers them and the recipe selects a different disease with no error — so identity belongs in a variable resolved by name and asserted unique. The seed gates are the opposite case: `DEC-PH3-001` commits to changing them only inside a duplicated project with predictions declared in advance, and making the gate a one-command edit would erode that pre-registration. Convenience is the wrong property for a value whose change requires a controlled experiment.
- **Evidence:** [`PHASE3_PREREGISTRATION.md` §2](../prioritizer/PHASE3_PREREGISTRATION.md) for the Class 1 / Class 2 split, `tools/recipe_classes.json` for the hand-recorded classification, `.index/recipes.tsv` (`gate` and `class` columns) for the live inventory, and `dss_recipes/visual/` for the mirrored visual formulas.
- **Consequences:** A future seed change touches **ten** recipes and no variable. Nine are Class 1 (pure NULL-fill): `compute_enriched_disease_context_1`, `compute_enriched_dwpc_GCD`, `compute_enriched_dwpc_GGD`, `compute_enriched_dwpc_GPGD`, `compute_enriched_guilt_by_association_1`, `compute_enriched_module_size_1`, `compute_enriched_shared_pathway_count_1` (all `module_size >= 20`, Cypher via the visual-graph plugin), plus `compute_enriched_prox_closest` (`MIN_SEEDS 5; POOL_MIN 20`) and `compute_enriched_rwr_score_1` (`MIN_SEEDS 20`), both Python. The tenth, `compute_dwpc_go_metapaths` (`MIN_MODULE 20`), is Class 2 and **holds at 20**. Query the live list with `awk -F'\t' '$3!="-"' .index/recipes.tsv` rather than trusting this paragraph, which is a snapshot.
- **Supersedes:** —
- **Superseded by:** —
- **Historical sources:** —
