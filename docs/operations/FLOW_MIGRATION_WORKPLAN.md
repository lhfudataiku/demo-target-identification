# Flow migration — workplan

> **Lifecycle:** Planning (draft) · **Audience:** DSS flow maintainers and technical reviewers ·
> **Authority:** the sequence, method and acceptance criteria for separating the notebooks' supporting
> evidence from the webapp's serving flow · **Update when:** a step is accepted or re-scoped, or a fact
> in §2 is superseded · **Generated dependencies:** none · **Excludes:** the boundary rule and target
> zone layout, decided in [`../demo/WEBAPP_REDESIGN_WORKPLAN.md`](../demo/WEBAPP_REDESIGN_WORKPLAN.md)
> Phase 0, and the decisions in [`../demo/WEBAPP_REDESIGN_SCOPE.md`](../demo/WEBAPP_REDESIGN_SCOPE.md)
> (D13–D15), which this plan carries out.

**Status: DRAFT — 2026-10-26. Not approved; nothing in DSS has changed.**

## 1. Purpose and timing

The notebooks under `notebooks/` assert the project's documented numbers; the webapp serves the
demo. Today they read many of the same computed datasets, so a change made for one can move the
other. This plan separates them:

- **A new DSS project for the supporting evidence** (D13). It reads `DEMO_TARGET_IDENTIFICATION`'s
  zones 00–31 through exposed, read-only objects, recomputes what it needs, and runs the notebook
  assertions. `breast_panel_metrics` moves into it.
- **The main project's flow after zone 40 is rearranged by the new webapp's functions** (D15), rebuilt
  in new zones beside the old ones, compared, and only then retired.

It runs **after the webapp redesign's Phase 8**, because its inventory reads what the released webapp
actually reads. Two parts are settled earlier, in the redesign's Phase 0: the boundary rule (D14) and
the target zone layout (D15). The redesign's Phases 4–6 put their new objects straight into the target
zones, so nothing new lands in a zone this plan retires.

Every step that changes DSS needs the user's approval at the time. The user runs builds, scenarios and
`make deploy`; Claude verifies read-only. Nothing is committed without the user's approval.

## 2. Starting point (measured 2026-10-26)

**The flow:** 91 datasets in 17 zones; the zones after 40 hold 41 of them (40: 11, A1: 5, A2: 16,
A3: 6, A4: 3).

**What each notebook reads from zone 40 or later** — 15 distinct datasets, 23 reads:

| notebook | reads from zone 40 or later |
|---|---|
| `nb1` | — |
| `nb2` | `split_audit_2` (A2); `known_drug_truth`, `pool_reachability` (A4) |
| `nb3` | `drug_target_benchmark`, `family_auc_by_family`, `validation_auc_by_disease` (A2) |
| `nb3b` | — |
| `nb4` | `novel_discovery_eval`, `persona_candidates` (A2); `family_panel_overlap` (A3); `filter_three_axes`, `known_drug_truth` (A4) |
| `nb5` | `validation_auc_by_disease` (A2) |
| `nb6` | `dashboard_candidates` (40); `drug_target_benchmark`, `novel_discovery_eval`, `validation_auc_by_disease` (A2); `family_panel_overlap` (A3) |
| `nb7` | `dashboard_candidates` (40); `persona_enrichment` (A2); `demo_panel_config`, `family_panel`, `family_panel_overlap`, `family_panel_programme` (A3) |

Eight of the 15 are also read by the webapp: `dashboard_candidates`, `validation_auc_by_disease`,
`split_audit_2`, `family_auc_by_family`, `persona_enrichment`, `demo_panel_config`,
`family_panel_overlap` and `family_panel_programme`. Their upstream reads within zones 00–31 are
`scored_champion` (six notebooks), the graph and drug-edge imports, the zone 10 DWPC features, the
zone 20 gene annotations and `disease_family_id`, and the zone 30 split tables.

**Zone 20 does three unrelated jobs:**

| job | datasets |
|---|---|
| drug annotation | `ot_drug_mapped`, `drug_joined`, `drug_classified`, `drug_evidence_pairs` |
| gene annotation | `gene_crosswalk`, `enriched_gene_druggability_v2`, `enriched_gene_localization`, `gene_safety_joined`, `enriched_gene_safety_v2` |
| disease family and split key | `hetionet_disease_slim`, `disease_family_id` |

It also carries the leakage-control split key, so it is **re-zoned, never rebuilt**: moving a recipe
between zones changes no data, while recomputing zone 20 would ripple through the split, the model and
every downstream number.

**What `breast_panel_metrics` is tied to:**

- it is the build-governance target in `docs/operations/build-governance/POLICY.json`
  (`allowed_targets`), and the 2026-08-31 pilot's three artifacts fingerprint its recipe;
- `compute_breast_panel` is one of the three identity recipes in `tools/check_governed_values.py`
  (`DEC-OPS-006`), with `compute_demo_panel_config` and `compute_split_audit_2`;
- governed claim `TI-VAL-009` takes its authority from `nb4` §8.10, so it moves with `nb4`;
- `.index/_dead.json` marks it "do not migrate", which D13 now reverses.

`notebooks/README.md` still describes a `90 Validation evidence (asserted)` zone that no longer exists.

## 3. Steps

| step | what | DSS change | done when |
|---|---|---|---|
| M0 | decisions | — | approved |
| M1 | inventory and mapping | — | table approved |
| M2 | the evidence project | new project, moved recipe | every assertion and governed claim unchanged |
| M3 | the new serving zones, built beside the old | new zones and datasets | zero unexplained differences |
| M4 | the webapp switches to the new zones | deploy | the webapp unchanged on screen |
| M5 | retire the old zones, re-zone 20 | deletions, moves | map clean, checks green |

### M0 — decisions

- A successor ADR to `ADR-001` for the third project: what it owns, the exposed objects it reads, and
  that no build crosses the boundary.
- The build-governance and identity-recipe changes for `breast_panel_metrics`: the target leaves
  `POLICY.json`'s `allowed_targets` (the pilot artifacts stay as history); `compute_breast_panel`
  leaves `IDENTITY_RECIPES`, or the check learns the evidence project; `.index/_dead.json` loses its
  keep entry. These amend `DEC-OPS-005`/`DEC-OPS-006` territory, so they are recorded in the register.
- **Done when:** the user approves the ADR and register diff.

### M1 — inventory and mapping (read-only)

- Refresh the snapshot and the map: `python3 tools/build_recipe_index.py --refresh`, then
  `python3 tools/build_flow_map.py`, so the reader flags reflect the released webapp.
- **For each notebook read in zone 40 or later**, decide how the notebook gets the number from zones
  00–31: recompute in notebook code (the default, and the notebook rule), or a recipe in the evidence
  project built from zones 00–31 when recomputing is too heavy. Never a read of a serving zone.
- **Map every dataset after zone 40** to its target zone (D15) or its fate: moves to the evidence
  project, or deleted because nothing reads it (`shap_driver_frequency` and `shap_drivers_long` are
  expected here). Intermediates follow their first served consumer.
- **Zone 20:** confirm the three-zone split in §2 and that every recipe moves without a rebuild.
- **Done when:** the user approves one table: every dataset, its readers today, its readers after, its
  target zone or fate.

### M2 — the evidence project *(DSS)*

- Create the project (key and name are an open item in the scope). Expose zones 00–31's needed
  datasets from `DEMO_TARGET_IDENTIFICATION` as read-only objects.
- Move `compute_breast_panel` and `breast_panel_metrics`; add the evidence recipes M1 approved. New
  datasets use managed storage and Parquet; joins are visual Join recipes.
- Repoint the notebooks to the evidence project and rewrite each zone-40-or-later read as M1 decided.
  Move the `validate_notebooks` scenario; point `tools/push_assertions.py` at the new project's
  library.
- **Done when:** `validate_notebooks` runs green there; `.index/assertions.tsv` is unchanged;
  `python3 tools/check_claim_registry.py --check` and `tools/check_governed_values.py` pass with every
  governed claim at the same value.

### M3 — the new serving zones, built beside the old *(DSS)*

- Create the target zones (D15) with **copies** of today's serving recipes, writing new datasets with a
  distinct suffix so old and new coexist. Build them with one job, repeated `--target`, recursive
  only within the new zones.
- Compare every new serving dataset with its old counterpart, read-only, with a script under
  `tools/` that writes nothing to DSS:
  - row count and schema (names and types) equal;
  - rows matched on the dataset's key (for example `disease_index`, `gene_index`), with no key on one
    side only;
  - values equal; floats within 1e-9 relative; differences listed per column with examples.
- Inputs are pulled into `data/` (never committed). Intermediates are not compared one by one: a
  served dataset that matches proves its chain.
- **Done when:** every served dataset matches, or each difference is explained and approved.

### M4 — switch the webapp *(DSS: deploy)*

- Point the backend's dataset names at the new zones (one constant per route); run locally against
  live DSS and compare every API response with the old one, field by field.
- The user runs `make deploy`; Claude verifies read-only.
- **Done when:** every route returns the same payload as before, and the pages look the same.

### M5 — retire and tidy *(DSS)*

- After a grace period agreed with the user: delete the old serving zones' recipes and datasets, and
  the datasets M1 marked for deletion.
- Re-zone 20 into its three zones (moves only). Rename or rewrite zone descriptions (`shortDesc`
  has no CLI verb; it changes through a scenario using the Python API).
- Teach the index and flow-map tools the second project; regenerate `FLOW_MAP.md` and `.index/`.
- **Done when:** the main project's map has no notebook reader on a serving zone, no orphan outside the
  keep list, and every check in `tools/check_indexes.sh` passes.

## 4. Risks

- **A notebook recompute that disagrees with the served value.** That is the separation working: the
  notebook becomes an independent check. Each disagreement found in M2 is investigated, not patched.
- **Fingerprints and identity checks assume one project.** M0 changes them before M2 moves anything.
- **Zone 20 rebuilt by accident.** A recursive build from a downstream zone can reach it; M3 builds only
  within the new zones.
- **Two copies drifting during M3–M4.** The comparison runs again immediately before M4's switch.

## 5. Documents

| document | change |
|---|---|
| `ADR-001` successor, [`../decisions/DECISION_REGISTER.md`](../decisions/DECISION_REGISTER.md) | M0 |
| [`../overview/PROJECT_CONTEXT.md`](../overview/PROJECT_CONTEXT.md) | §4.3 shared objects for the third project |
| [`BUILD_GOVERNANCE.md`](BUILD_GOVERNANCE.md) | the target leaves the allowlist; the pilot stays as history |
| [`../../notebooks/README.md`](../../notebooks/README.md) | the evidence project; remove the zone-90 section |
| [`FLOW_MAP.md`](FLOW_MAP.md), `.index/` | regenerated after M3 and M5 |
| agent instructions (`harness/`) | the project map gains the third project; `tools/sync_harness.py --write` |
