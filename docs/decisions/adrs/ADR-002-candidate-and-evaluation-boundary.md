# ADR-002 — Candidate and evaluation boundaries are separate

> **Lifecycle:** Decision · **Status:** Accepted · **Date:** 2026-08-19 · **Owner:** methodology ·
> **Update when:** an eligibility route, label, denominator or split contract changes.

## Context

The candidate pool must remove easy negatives without encoding labels. A feature can be rejected
while its presence or missingness still selects rows. Separately, the drug route both admits pairs
and contributes to a drug-evidence benchmark, so it can select the evaluated population on the
outcome.

## Decision

Apply one evidence-bearing candidate population to training and testing and disqualify filters whose
missingness is set by label lookup. Treat a route change as a population intervention. For the
drug-evidence sensitivity analysis, exclude route-only outcome-selected pairs from the supported
denominator and report it beside the full denominator; do not remove entire diseases to repair an
evaluation bias.

## Alternatives rejected

- Proximity-threshold-only filtering: leaves coverage leakage.
- Expanding eligibility to every available feature route: dilutes the pool and changes the task.
- Dropping the drug route: removes valid positives and still conflates candidate and evaluation logic.

## Consequences

Candidate changes require population, leakage and control-stratum checks. Therapeutic evidence stays
a secondary sensitivity axis, while association ranking remains the training objective.
