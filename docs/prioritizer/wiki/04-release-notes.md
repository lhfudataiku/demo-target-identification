<div class="alert">

<!-- Governed claims consumed here: TI-MOD-001 TI-VAL-001 -->
This is a demo-only release. It is not a statement of general availability or production support.
</div>

# Release Notes

## Version 1.0.0 — Explainable target prioritization

This release marks the completed modelling, validation, and serving layer for Part 2 of the target
identification POC.

### New feature: Explainable disease-specific candidate ranking

The project consumes the governed biomedical graph and ranks disease × gene candidates using the
adopted XGBoost champion, `m7-f14`. The model uses 14 graph-derived features and produces SHAP
attributions so that a scientist can see which feature signals moved an individual score.

### New feature: Leakage-aware validation

The project evaluates recovery of held-out known associations using a curated disease-family split
and reports macro per-disease AUROC. The champion’s documented reconstruction fidelity is 0.8230
macro AUROC over 670 held-out diseases. This measure is not a claim of prospective target,
therapeutic, or clinical success.

### New feature: Filterable scientific review experience

Serving tables and the webapp present a ranked candidate list with SHAP explanations, graph
evidence, tractability, target class, known-liability, novelty, and drug-evidence context. The
deliverable is intentionally filterable rather than a pre-cut shortlist.

### Reliability and governance improvements

- separated graph construction from modelling through an explicit shared-object contract
- retained `m7-f14` as champion only after association and tractability improvements survived
  paired testing
- rejected `m8-f14-pm` despite better AUPRC because its broader validation evidence did not meet
  the adoption rule
- kept druggability and target class as annotations rather than model inputs
- rejected indirect safety proxies as candidate filters; a valid safety axis needs direct measures

### Known limitations

- the model reconstructs known associations under a controlled holdout; it does not establish
  causality or validate novel targets prospectively
- macro performance varies by disease, so individual disease context must be reviewed
- safety is not solved by the available annotations and must not be inferred from them
- the seed-gate widening intervention is approved for testing but has not been executed in this
  project
